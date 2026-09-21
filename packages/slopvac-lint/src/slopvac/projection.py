"""Lossless projection of rendered prose back to UTF-8 source bytes.

The linter matches a normalized prose view rather than Markdown syntax.  A
:class:`ProjectionMap` keeps that view useful for exact evidence: each projected
code point records the source byte range that supplied it, and synthetic output
(such as a joined-line space) records an empty source range.
"""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Literal


@dataclass(frozen=True)
class Segment:
    """One projected range and its corresponding raw UTF-8 byte range."""

    proj_start: int
    proj_end: int
    raw_start: int
    raw_end: int


class ProjectionMap:
    """Map projected code-point offsets to raw UTF-8 byte offsets.

    ``raw`` is optional only for callers constructing a map by hand.  Maps
    returned by :func:`project` always retain the original bytes, which makes
    :meth:`slice_raw` self-contained.
    """

    def __init__(self, segments: tuple[Segment, ...], raw: bytes = b"") -> None:
        self.segments = tuple(segments)
        self._raw = raw
        self._starts = tuple(segment.proj_start for segment in self.segments)
        self._ends = tuple(segment.proj_end for segment in self.segments)
        self._length = max((segment.proj_end for segment in self.segments), default=0)
        self._validate()

    def _validate(self) -> None:
        previous_end = 0
        for segment in self.segments:
            if segment.proj_start < previous_end:
                raise ValueError("projection segments must be ordered")
            if segment.proj_start > segment.proj_end:
                raise ValueError("projection segment has a negative range")
            if segment.raw_start < 0 or segment.raw_end < segment.raw_start:
                raise ValueError("projection segment has a negative raw range")
            previous_end = segment.proj_end

    @property
    def projected_length(self) -> int:
        return self._length

    def to_raw(self, cp: int) -> int:
        """Return the raw byte boundary corresponding to projected ``cp``.

        The maps produced here have one segment per projected code point.  The
        bisect lookup also handles hand-built multi-code-point segments by
        returning their nearest boundary, which is the only lossless choice
        without a per-code-point subdivision.
        """

        if cp < 0 or cp > self._length:
            raise ValueError(f"projected offset out of range: {cp}")
        if not self.segments:
            return 0
        index = bisect_right(self._starts, cp) - 1
        if index < 0:
            return self.segments[0].raw_start
        segment = self.segments[index]
        if cp >= segment.proj_end:
            if index + 1 < len(self.segments):
                next_segment = self.segments[index + 1]
                if cp <= next_segment.proj_start:
                    return next_segment.raw_start
            return segment.raw_end
        if segment.proj_end - segment.proj_start == 1:
            return segment.raw_start
        # This branch is for manually supplied compact segments.  Projected
        # maps use one-code-point segments, so no produced map depends on an
        # assumption about UTF-8 byte width.
        span = segment.proj_end - segment.proj_start
        raw_span = segment.raw_end - segment.raw_start
        return segment.raw_start + (cp - segment.proj_start) * raw_span // span

    def slice_raw(self, start_cp: int, end_cp: int) -> bytes:
        """Return the source bytes covered by projected ``[start_cp:end_cp]``.

        Segment endpoints are authoritative here.  At a boundary followed by
        stripped markup, ``to_raw`` must point at the next real character for
        finding starts, while this method must stop at the preceding segment's
        raw end for an exact quote.
        """

        if start_cp < 0 or end_cp < start_cp or end_cp > self._length:
            raise ValueError("invalid projected slice")
        if start_cp == end_cp:
            return b""
        first = bisect_right(self._ends, start_cp)
        last = bisect_left(self._starts, end_cp)
        if first >= last:
            return b""
        return self._raw[self.segments[first].raw_start : self.segments[last - 1].raw_end]

    @property
    def raw(self) -> bytes:
        """Return the original UTF-8 source bytes retained by this map."""

        return self._raw

    def source_spans(self, start_cp: int = 0, end_cp: int | None = None) -> tuple[tuple[int, int], ...]:
        """Return ordered, merged non-empty source byte spans for a projection slice."""

        if end_cp is None:
            end_cp = self._length
        if start_cp < 0 or end_cp < start_cp or end_cp > self._length:
            raise ValueError("invalid projected slice")
        spans = [
            (segment.raw_start, segment.raw_end)
            for segment in self.segments
            if segment.proj_end > start_cp
            and segment.proj_start < end_cp
            and segment.raw_start < segment.raw_end
        ]
        merged: list[tuple[int, int]] = []
        for span_start, span_end in spans:
            if merged and span_start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], span_end))
            else:
                merged.append((span_start, span_end))
        return tuple(merged)

    def submap(self, start_cp: int, end_cp: int) -> ProjectionMap:
        """Return a projection whose coordinates begin at ``start_cp``."""

        if start_cp < 0 or end_cp < start_cp or end_cp > self._length:
            raise ValueError("invalid projected slice")
        segments: list[Segment] = []
        for segment in self.segments:
            if segment.proj_end <= start_cp or segment.proj_start >= end_cp:
                continue
            clipped_start = max(segment.proj_start, start_cp)
            clipped_end = min(segment.proj_end, end_cp)
            segments.append(
                Segment(
                    clipped_start - start_cp,
                    clipped_end - start_cp,
                    segment.raw_start,
                    segment.raw_end,
                )
            )
        return ProjectionMap(tuple(segments), self._raw)


_LINE_RE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n|$)")
_CODE_SPAN_RE = re.compile(r"(?P<ticks>`+)(?P<body>[^`\r\n]*?)(?P=ticks)")
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);?")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_FENCE_RE = re.compile(r"^\s{0,3}(?P<marker>`{3,}|~{3,})")
_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>|<![A-Z][^>]*>")
_LINK_RE = re.compile(r"!?\[(?P<label>[^\]]*)\]\([^)]*\)")


def _byte_offsets(text: str) -> list[int]:
    offsets = [0]
    for char in text:
        offsets.append(offsets[-1] + len(char.encode("utf-8")))
    return offsets


def _line_ranges(raw: str) -> list[tuple[int, int, int, int]]:
    """Return ``(body_start, body_end, line_end, newline_end)`` code-point ranges."""

    ranges: list[tuple[int, int, int, int]] = []
    for match in _LINE_RE.finditer(raw):
        if match.start() == match.end() and match.start() == len(raw):
            break
        value = match.group(0)
        newline_length = len(value) - len(value.rstrip("\r\n"))
        body_end = match.end() - newline_length
        ranges.append((match.start(), body_end, body_end, match.end()))
    return ranges


def _strip_prefix(line: str) -> tuple[str, int]:
    """Remove Markdown block/list markers and return content plus char offset."""

    prefix = 0
    # A blockquote may contain a list marker, so strip the prefix repeatedly.
    while True:
        match = re.match(r"\s{0,3}(?:>\s*|(?:[-+*]|\d+[.)])\s+|#{1,6}\s+)", line[prefix:])
        if not match:
            break
        prefix += match.end()
    content = line[prefix:]
    if content.startswith("|"):
        content = content[1:]
        prefix += 1
    if content.endswith("|"):
        content = content[:-1]
    return content, prefix


def project(raw: str) -> tuple[str, ProjectionMap]:
    """Render a Markdown-ish source into prose and retain a byte projection map.

    This intentionally mirrors the transformations used by ``analyze.py``:
    fenced/indented code is omitted, inline code is masked by a NUL sentinel,
    soft line breaks become synthetic spaces, entities are decoded, and markup
    (links, tags, and emphasis delimiters) is removed.
    """

    raw_offsets = _byte_offsets(raw)
    output: list[str] = []
    segments: list[Segment] = []
    previous_content = False
    in_fence: tuple[str, int] | None = None
    in_front_matter = False

    def emit(value: str, raw_start_cp: int, raw_end_cp: int, *, synthetic: bool = False) -> None:
        if not value:
            return
        raw_start = raw_offsets[raw_start_cp]
        raw_end = raw_offsets[raw_end_cp]
        if synthetic:
            raw_end = raw_start
        for char in value:
            position = len(output)
            output.append(char)
            segments.append(Segment(position, position + 1, raw_start, raw_end))

    def emit_line(start: int, end: int, content: str, content_offset: int) -> bool:
        nonlocal previous_content
        if not content.strip():
            return False
        if previous_content and output and not output[-1].isspace():
            # Anchor the synthetic space at the end of the preceding real
            # segment. The newline bytes remain between this boundary and the
            # next real segment, so a real span ending before the insertion
            # still slices only its own bytes.
            raw_boundary = segments[-1].raw_end if segments else raw_offsets[start]
            position = len(output)
            output.append(" ")
            segments.append(Segment(position, position + 1, raw_boundary, raw_boundary))
        cursor = 0
        while cursor < len(content):
            absolute = start + content_offset + cursor
            comment = _COMMENT_RE.match(content, cursor)
            if comment:
                cursor = comment.end()
                continue
            code = _CODE_SPAN_RE.match(content, cursor)
            if code:
                # Keep one non-word sentinel slot, just as _inline_prose does.
                emit(" \x00 ", absolute, absolute, synthetic=True)
                cursor = code.end()
                continue
            link = _LINK_RE.match(content, cursor)
            if link:
                label = link.group("label")
                label_start = absolute + (link.start("label") - cursor)
                # Re-run the small scanner on the visible label.  A recursive
                # link is invalid CommonMark, so a one-level pass is enough.
                for index, char in enumerate(label):
                    emit(char, label_start + index, label_start + index + 1)
                cursor = link.end()
                continue
            entity = _ENTITY_RE.match(content, cursor)
            if entity:
                decoded = unescape(entity.group(0))
                if decoded != entity.group(0):
                    emit(decoded, absolute, absolute, synthetic=True)
                    cursor = entity.end()
                    continue
            tag = _TAG_RE.match(content, cursor)
            if tag:
                cursor = tag.end()
                continue
            if content.startswith("**", cursor) or content.startswith("__", cursor):
                cursor += 2
                continue
            if content.startswith("~~", cursor):
                cursor += 2
                continue
            emit(content[cursor], absolute, absolute + 1)
            cursor += 1
        previous_content = bool(output)
        return True

    for body_start, body_end, _line_end, line_end in _line_ranges(raw):
        line = raw[body_start:body_end]
        if body_start == 0 and line.strip() == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            if line.strip() == "---":
                in_front_matter = False
            continue
        fence = _FENCE_RE.match(line)
        if in_fence is not None:
            marker, count = in_fence
            if re.match(rf"^\s{{0,3}}{re.escape(marker[0])}{{{count},}}\s*$", line):
                in_fence = None
            continue
        if fence:
            marker = fence.group("marker")
            in_fence = (marker, len(marker))
            continue
        if re.match(r"^\s{4}", line):
            continue
        content, content_offset = _strip_prefix(line)
        emitted = emit_line(body_start, body_end, content, content_offset)
        if emitted:
            previous_content = True
        elif line_end > body_end and output and output[-1].isspace():
            previous_content = bool(output)

    return "".join(output), ProjectionMap(tuple(segments), raw.encode("utf-8"))


Origin = Literal["authored", "generated", "vendored", "template"]
Region = Literal["prose", "quoted", "code", "example"]

# Keep precedence and all path/header signals in one table.  The content
# predicates are intentionally conservative: only a first-line generated marker
# is treated as generated, never arbitrary prose mentioning generation.
_ORIGIN_RULES: dict[Origin, tuple[str, ...]] = {
    "vendored": (".agents", ".beads", "node_modules"),
    "template": ("templates", "fixtures"),
    "generated": ("CHANGELOG.md", "<!-- generated", "slopvac reference"),
}


def _content_from_config(config: Any) -> str:
    if isinstance(config, str):
        return config
    if isinstance(config, dict):
        for name in ("raw", "content", "text", "header"):
            value = config.get(name)
            if isinstance(value, str):
                return value
    for name in ("raw", "content", "text", "header"):
        value = getattr(config, name, None)
        if isinstance(value, str):
            return value
    return ""


def classify_origin(path: str, config: Any = None) -> Origin:
    """Classify a source path using deterministic path and header signals."""

    normalized = path.replace("\\", "/")
    parts = {part.lower() for part in normalized.split("/")}
    basename = normalized.rsplit("/", 1)[-1].lower()
    content = _content_from_config(config)
    if not content and Path(path).is_file():
        content = Path(path).read_text(encoding="utf-8")
    first_line = content.splitlines()[0].strip().lower() if content.splitlines() else ""
    reference_header = first_line.lstrip("# ").startswith("slopvac reference")
    signals = {
        "vendored": bool(parts & set(_ORIGIN_RULES["vendored"])),
        "template": bool(parts & set(_ORIGIN_RULES["template"])),
        "generated": (
            basename == "changelog.md"
            or first_line.startswith("<!-- generated")
            or reference_header
        ),
    }
    for origin in ("vendored", "template", "generated"):
        if signals[origin]:
            return origin  # type: ignore[return-value]
    return "authored"


def classify_region(block: Any) -> Region:
    """Classify a parsed block or a block-like test object."""

    kind = getattr(getattr(block, "kind", None), "value", getattr(block, "kind", ""))
    kind = str(kind).lower()
    if kind in {"code", "fenced", "indented", "code_block"} or getattr(
        block, "is_code", False
    ):
        return "code"
    if kind in {"quote", "blockquote"}:
        return "quoted"
    if getattr(block, "under_examples", False) or getattr(block, "in_examples", False):
        return "example"
    heading = str(getattr(block, "heading", "")).strip().lower()
    if heading == "examples":
        return "example"
    if kind in {"list_item", "table", "table_row"}:
        examples = getattr(block, "examples", None)
        if examples is None:
            examples = getattr(block, "rule_examples", None)
        if examples:
            values = {
                item.get("bad", "")
                if isinstance(item, dict)
                else getattr(item, "bad", item)
                for item in examples
            }
            if str(getattr(block, "text", "")) in values:
                return "example"
    return "prose"


def source_sha256(raw: bytes) -> str:
    """Return the source digest used by judgement unit identities."""

    return hashlib.sha256(raw).hexdigest()
