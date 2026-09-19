"""Prepare, finish, and compare judgement-layer evaluation runs.

The driver deliberately keeps provider transport outside this package. ``prepare``
creates deterministic request records, a caller fills ``responses.jsonl`` with its
model responses, and ``finish`` performs schema validation, host adjudication, and
aggregation. ``compare`` presents the resulting report and can write a checked
rewrite preview.
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from importlib import resources
from pathlib import Path
from typing import Any

from ..analyze import (
    IMPERATIVE_MARKERS,
    REMEMBER_TO,
    TO_VERB,
    BlockKind,
    Document,
    PassageProbe,
    SpanCandidate,
    TextType,
    classify_text_type,
    parse,
)
from ..config import Config, Profile, resolve_for
from ..model import Finding, RuleKind
from ..pipeline import load_run_context, run_lint
from ..projection import ProjectionMap, Segment, project
from ..rules import load_ruleset
from ..score import score_document
from .adjudicate import FindingRecord, adjudicate
from .aggregate import (
    cluster_gate,
    components,
    coverage,
    load_dependence_table,
    preserve_rates,
)
from .eval.runner import validate_result_set
from .packs import (
    Pack,
    build_packs,
    instrument_id,
    judgement_cache_key,
    pack_id,
    render_pack,
    rubric_revision,
)
from .schema import validate_model_output

_SCHEMA = json.loads(
    resources.files("slopvac.judgement")
    .joinpath("model_output_schema.json")
    .read_text(encoding="utf-8")
)
_SPINE = resources.files("slopvac.judgement").joinpath("spine.md").read_text(encoding="utf-8")
_DEPENDENCE_TABLE = load_dependence_table(Path(__file__).with_name("dependence_table.json"))


def _json_line(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _write_jsonl(path: Path, values: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _plain(value: Any) -> Any:
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _safe_name(path: Path, root: Path | None = None) -> str:
    try:
        value = str(path.resolve().relative_to((root or Path.cwd()).resolve()))
    except ValueError:
        # Paths outside the configured root still need a stable, unique name.
        # Falling back to ``path.name`` makes sibling documents collide.
        value = str(path.resolve())
    value = value.replace("\\", "/").strip("/")
    # Escape every character that participates in the flattening scheme.  Escaping
    # ``%`` first keeps the encoding injective even when the source contains a
    # sequence that looks like an escape.
    value = value.replace("%", "%25").replace("_", "%5F").replace("/", "%2F")
    return value or path.name



def _paragraph_ranges(raw: str, projection: ProjectionMap | None = None) -> list[tuple[int, int]]:
    """Return blank-line paragraph boundaries in raw or projected coordinates."""
    ranges: list[tuple[int, int]] = []
    start = 0
    separators = re.finditer(r"(?:\r?\n)[ \t]*(?:\r?\n)+", raw)
    for separator in separators:
        block = raw[start : separator.start()]
        left = len(block) - len(block.lstrip())
        right = len(block.rstrip())
        if left < right:
            ranges.append((start + left, start + right))
        start = separator.end()
    block = raw[start:]
    left = len(block) - len(block.lstrip())
    right = len(block.rstrip())
    if left < right:
        ranges.append((start + left, start + right))
    if projection is None:
        return ranges
    # ProjectionMap raw offsets are UTF-8 byte positions, while the parser
    # and regex above operate on Python character indices.
    byte_offsets = [0]
    for char in raw:
        byte_offsets.append(byte_offsets[-1] + len(char.encode("utf-8")))
    projected_ranges: list[tuple[int, int]] = []
    for char_start, char_end in ranges:
        raw_start, raw_end = byte_offsets[char_start], byte_offsets[char_end]
        selected = [segment for segment in projection.segments if segment.raw_end > raw_start and segment.raw_start < raw_end]
        if selected:
            projected_ranges.append((selected[0].proj_start, selected[-1].proj_end))
    return projected_ranges


def _schema_wrapper(units: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    if kind == "PASSAGE_PROBE" and len(units) == 1:
        return _SCHEMA
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "results": {
                "type": "array",
                "items": _SCHEMA,
                "minItems": len(units),
                "maxItems": len(units),
            }
        },
        "required": ["results"],
    }
def _projection_dict(projection: ProjectionMap) -> dict[str, Any]:
    raw = getattr(projection, "_raw", b"")
    if not raw:
        raw = projection.slice_raw(0, projection.projected_length)
    return {
        "segments": [asdict(segment) for segment in projection.segments],
        "raw_b64": base64.b64encode(raw).decode("ascii"),
    }


def _projection_from_dict(value: dict[str, Any]) -> ProjectionMap:
    segments = tuple(Segment(**item) for item in value.get("segments", ()))
    raw = base64.b64decode(value.get("raw_b64", ""))
    return ProjectionMap(segments, raw)


def _identity_projection(raw_text: str, raw_start: int, raw_bytes: bytes) -> ProjectionMap:
    offsets = [0]
    for char in raw_text:
        offsets.append(offsets[-1] + len(char.encode("utf-8")))
    segments = tuple(
        Segment(index, index + 1, raw_start + offsets[index], raw_start + offsets[index + 1])
        for index in range(len(raw_text))
    )
    return ProjectionMap(segments, raw_bytes)

def _unit_dict(
    unit: Any,
    *,
    document_ref: str,
    passage_id: str,
    gold_ids: Sequence[str] = (),
    gold_control: bool = False,
) -> dict[str, Any]:
    """Serialize only unit-local data; document-wide data lives under documents/."""
    projection_segments = tuple(getattr(unit.projection, "segments", ()))
    source_range = (
        [projection_segments[0].raw_start, projection_segments[-1].raw_end]
        if projection_segments
        else [0, 0]
    )
    item = {
        "unit_id": unit.unit_id,
        "kind": unit.kind,
        "rule_id": unit.rule_id,
        "rule_ids": [unit.rule_id],
        "pack_id": getattr(unit, "pack_id", ""),
        "path": unit.path,
        "document_ref": document_ref,
        "passage_id": passage_id,
        "text": unit.text,
        "model_text": unit.text,
        "context": getattr(unit, "context", ""),
        "model_context": getattr(unit, "context", ""),
        "doc_range": list(unit.doc_range),
        "source_range": source_range,
        "origin": unit.origin,
        "region_class": unit.region_class,
        "status": getattr(unit, "status", ""),
        "admission": getattr(unit, "admission", "eligible"),
        "admission_reason": getattr(unit, "admission_reason", None),
        "preservation_reason": getattr(unit, "preservation_reason", None),
        "truncated": bool(getattr(unit, "truncated", False)),
    }
    if gold_ids:
        item["gold_ids"] = list(gold_ids)
        if len(gold_ids) == 1:
            item["gold_id"] = gold_ids[0]
        if gold_control:
            item["gold_control"] = True
    return item


def _gold_path_key(path: str | Path) -> str:
    """Normalize path spelling for matching gold rows to input documents."""
    return str(Path(path).expanduser().resolve()).replace("\\", "/")


def _gold_row_path_matches(row_path: str, document_path: Path, gold_path: Path | None) -> bool:
    candidate = Path(row_path).expanduser()
    document_key = _gold_path_key(document_path)
    options = {_gold_path_key(candidate)}
    if not candidate.is_absolute():
        options.add(_gold_path_key(Path.cwd() / candidate))
        if gold_path is not None:
            options.add(_gold_path_key(gold_path.parent / candidate))
    if document_key in options:
        return True
    return candidate.name == document_path.name and not candidate.parent.parts


def _gold_range(row: dict[str, Any], raw: str, *, gold_id: str) -> tuple[int, int]:
    """Resolve a seeded span's UTF-8 byte range from a row."""
    raw_bytes = raw.encode("utf-8")
    value = row.get("byte_range", row.get("source_range", row.get("range")))
    start: Any = None
    end: Any = None
    if isinstance(value, dict):
        start, end = value.get("start"), value.get("end")
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        start, end = value
    if start is None or end is None:
        start, end = row.get("start"), row.get("end")
    if start is not None or end is not None:
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start <= end <= len(raw_bytes):
            raise ValueError(f"gold span {gold_id} has an invalid byte range")
        return start, end
    quote = row.get("exact_text", row.get("quote"))
    if quote is None and "defect_span" in row:
        quote = row["defect_span"]
    if quote is None:
        quote = row.get("text")
    if not isinstance(quote, str) or not quote:
        raise ValueError(f"gold span {gold_id} needs byte range or exact text")
    needle = quote.encode("utf-8")
    first = raw_bytes.find(needle)
    second = raw_bytes.find(needle, first + 1) if first >= 0 else -1
    if first < 0 or second >= 0:
        raise ValueError(f"gold span {gold_id} exact text must occur exactly once")
    return first, first + len(needle)


def _load_gold_rows(
    gold: Path | None,
    paths: Sequence[str | Path],
) -> tuple[Path | None, list[dict[str, Any]]]:
    """Load v1 gold rows, including the shipped text-only schema."""
    source = gold
    if source is None:
        parents = {Path(path).expanduser().resolve().parent for path in paths}
        candidates = [parent / "gold.jsonl" for parent in sorted(parents, key=str)]
        source = next((candidate for candidate in candidates if candidate.exists()), None)
    if source is None:
        return None, []
    if not source.exists():
        raise ValueError(f"gold manifest not found: {source}")
    rows: list[dict[str, Any]] = []
    input_documents = [Path(path).expanduser().resolve() for path in paths]
    document_text = {
        document: document.read_text(encoding="utf-8") for document in input_documents
    }
    ordinals: Counter[tuple[str, str, str]] = Counter()
    for index, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        raw_row = json.loads(line)
        if not isinstance(raw_row, dict):
            raise ValueError(f"gold manifest line {index} must be an object")
        if set(raw_row) == {"version"}:
            continue
        row_path = raw_row.get("path")
        if row_path is not None and (not isinstance(row_path, str) or not row_path):
            raise ValueError(f"gold manifest line {index} has invalid path")
        if isinstance(row_path, str):
            matches = [
                document
                for document in input_documents
                if _gold_row_path_matches(row_path, document, source)
            ]
        else:
            row_text = raw_row.get("text")
            if not isinstance(row_text, str) or not row_text:
                raise ValueError(f"gold manifest line {index} needs path or text")
            matches = [document for document, text in document_text.items() if row_text in text]
        unattached_reason: str | None = None
        if len(matches) != 1:
            if isinstance(row_path, str):
                raise ValueError(f"gold manifest line {index} path does not identify one input: {row_path}")
            unattached_reason = "no_unique_document"
        kind = raw_row.get("kind")
        if kind is None:
            kind = "control" if bool(raw_row.get("control", False)) else "seeded"
        if kind not in {"seeded", "control"}:
            raise ValueError(f"gold manifest line {index} kind must be seeded or control")
        control = kind == "control"
        rule_id = raw_row.get("rule_id")
        if rule_id is not None and (not isinstance(rule_id, str) or not rule_id):
            raise ValueError(f"gold manifest line {index} has invalid rule_id")
        if not control and not isinstance(rule_id, str):
            raise ValueError(f"gold manifest line {index} needs rule_id")
        document = matches[0] if matches else None
        identity = str(rule_id) if rule_id is not None else kind
        key = (identity, str(raw_row.get("text", "")), str(raw_row.get("defect_span", "")))
        ordinals[key] += 1
        gold_id = raw_row.get("gold_id")
        if not isinstance(gold_id, str) or not gold_id:
            gold_id = f"{identity}#{ordinals[key]}"
        if document is None:
            start, end = 0, 0
        else:
            try:
                start, end = _gold_range(raw_row, document_text[document], gold_id=gold_id)
            except ValueError:
                if isinstance(row_path, str):
                    raise
                document = None
                start, end = 0, 0
                unattached_reason = "span_not_unique"
        row = {
            "gold_id": gold_id,
            "path": str(document) if document is not None else "",
            "start": start,
            "end": end,
            "rule_id": rule_id,
            "kind": kind,
            "control": control,
        }
        if unattached_reason is not None:
            row["unattached_reason"] = unattached_reason
        rows.append(row)
    return source, rows


def _gold_rows_for_unit(
    gold_rows: Sequence[dict[str, Any]],
    path: str,
    source_range: Sequence[int],
    rule_id: str,
) -> list[dict[str, Any]]:
    if len(source_range) != 2:
        return []
    start, end = int(source_range[0]), int(source_range[1])
    if end <= start:
        return []
    return [
        row
        for row in gold_rows
        if _gold_path_key(row["path"]) == _gold_path_key(path)
        and int(row["start"]) < end
        and start < int(row["end"])
        and (row.get("rule_id") is None or str(row.get("rule_id")) == rule_id)
    ]


def _gold_for_unit(
    gold_rows: Sequence[dict[str, Any]],
    path: str,
    source_range: Sequence[int],
    rule_id: str,
) -> tuple[str | None, bool]:
    """Return the first overlapping gold row for legacy callers."""
    matches = _gold_rows_for_unit(gold_rows, path, source_range, rule_id)
    if not matches:
        return None, False
    return str(matches[0]["gold_id"]), bool(matches[0].get("control"))


def _unit_from_dict(item: dict[str, Any], documents: dict[str, dict[str, Any]]) -> Any:
    cls = PassageProbe if item.get("kind") == "PASSAGE_PROBE" else SpanCandidate
    document = documents.get(str(item.get("document_ref", "")), {})
    legacy_projection = item.get("projection")
    raw_document = str(document.get("text", ""))
    raw_bytes = raw_document.encode("utf-8")
    source_range = item.get("source_range")
    if (
        isinstance(source_range, list)
        and len(source_range) == 2
        and all(isinstance(value, int) for value in source_range)
        and 0 <= source_range[0] <= source_range[1] <= len(raw_bytes)
    ):
        raw_text = raw_bytes[source_range[0] : source_range[1]].decode("utf-8", errors="replace")
        projection = _identity_projection(raw_text, source_range[0], raw_bytes)
    else:
        projection_data = document.get("projection", {})
        if isinstance(legacy_projection, dict) and "segments" in legacy_projection:
            projection_data = legacy_projection
        projection = _projection_from_dict(projection_data)
        raw_text = str(item.get("model_text", item.get("text", "")))
    text = str(item.get("model_text", item.get("text", raw_text)))
    unit = cls(
        rule_id=str(item.get("rule_id", "")),
        path=str(item.get("path", "")),
        text=text,
        range=tuple(item.get("range", (0, len(text)))),
        doc_range=tuple(item.get("doc_range", (0, len(text)))),
        projection=projection,
        origin=str(item.get("origin", "authored")),
        region_class=str(item.get("region_class", "authored")),
        source_sha256=str(item.get("source_sha256", document.get("source_sha256", ""))),
        unit_id=str(item.get("unit_id", "")),
    )
    unit.rule_ids = (str(item.get("rule_id", "")),)
    unit.pack_id = str(item.get("pack_id", ""))
    unit.context = str(item.get("model_context", item.get("context", "")))
    unit.document_text = raw_document or text
    unit.status = str(item.get("status", ""))
    unit.admission = str(item.get("admission", "eligible"))
    unit.admission_reason = item.get("admission_reason")
    unit.preservation_reason = item.get("preservation_reason")
    unit.truncated = bool(item.get("truncated", False))
    return unit

def _passage_id(document: Document, doc_range: tuple[int, int]) -> str:
    return f"{document.path}:{doc_range[0]}:{doc_range[1]}"


def _next_ordinal(counter: Counter[tuple[str, str, str]], kind: str, rule_id: str, text: str) -> int:
    key = (kind, rule_id, text)
    ordinal = counter[key]
    counter[key] += 1
    return ordinal



def _document_range_for_local(
    document: Document,
    local_projection: ProjectionMap,
    start: int,
    end: int,
) -> tuple[int, int]:
    selected = [
        segment
        for segment in local_projection.segments
        if segment.proj_end > start and segment.proj_start < end
    ]
    if not selected:
        return (0, 0)
    raw_start = min(segment.raw_start for segment in selected)
    raw_end = max(segment.raw_end for segment in selected)
    document_segments = [
        segment
        for segment in document.projection.segments
        if segment.raw_end > raw_start and segment.raw_start < raw_end
    ]
    if not document_segments:
        before = [segment for segment in document.projection.segments if segment.raw_end <= raw_start and segment.raw_end > 0]
        after = [segment for segment in document.projection.segments if segment.raw_start >= raw_end and segment.raw_end > segment.raw_start]
        if before and after:
            return (max(before, key=lambda segment: segment.proj_end).proj_end, min(after, key=lambda segment: segment.proj_start).proj_start)
        return (0, 0)
    return (document_segments[0].proj_start, document_segments[-1].proj_end)


def _raw_unit_projection(
    document: Document,
    doc_range: tuple[int, int],
    source_projection: ProjectionMap | None = None,
) -> tuple[str, ProjectionMap]:
    """Return source text and a map whose coordinates match that source text."""
    full = source_projection or getattr(document, "_judgement_projection", None) or document.projection
    raw_bytes = document.raw.encode("utf-8")
    if full is None:
        return "", ProjectionMap((), raw_bytes)
    if source_projection is None and doc_range[1] > full.projected_length:
        raw_text, raw_start = document.raw, 0
    elif source_projection is None and doc_range == (0, full.projected_length):
        raw_text, raw_start = document.raw, 0
    else:
        selected = [
            segment
            for segment in full.segments
            if segment.proj_end > doc_range[0] and segment.proj_start < doc_range[1]
        ]
        if not selected:
            return "", ProjectionMap((), raw_bytes)
        raw_start = selected[0].raw_start
        raw_text = full.slice_raw(*doc_range).decode("utf-8")
    offsets = [0]
    for char in raw_text:
        offsets.append(offsets[-1] + len(char.encode("utf-8")))
    segments = tuple(
        Segment(index, index + 1, raw_start + offsets[index], raw_start + offsets[index + 1])
        for index in range(len(raw_text))
    )
    return raw_text, ProjectionMap(segments, raw_bytes)


def _neighbor_context(document: Document, block: Any) -> str:
    """Return adjacent raw source blocks, never the entire document."""
    index = document.blocks.index(block)
    neighbors: list[str] = []
    for candidate in document.blocks[max(0, index - 1) : index + 2]:
        if candidate is block or not candidate.text:
            continue
        if candidate.kind in {BlockKind.CODE, BlockKind.FRONT_MATTER}:
            continue
        text, _ = _raw_unit_projection(document, candidate.doc_range)
        neighbors.append(text)
    return "\n\n".join(neighbors)


def _unit_from_sentence(
    document: Document,
    block: Any,
    sentence: Any,
    index: int,
    rule_id: str,
    pack: Pack,
    ordinal_counter: Counter[tuple[str, str, str]] | None = None,
) -> Any:
    if ordinal_counter is None:
        ordinal_counter = Counter()
    start = block.text.find(sentence.text, index)
    if start < 0:
        start = index
    end = start + len(sentence.text)
    if block.projection is None:
        raise ValueError("parsed block has no projection")
    doc_range = _document_range_for_local(document, block.projection, start, end)
    if doc_range == (0, 0):
        doc_range = (block.doc_range[0] + start, block.doc_range[0] + end)
    raw_text, raw_projection = _raw_unit_projection(document, doc_range)
    unit = SpanCandidate(
        ordinal=_next_ordinal(ordinal_counter, "SPAN_CANDIDATE", rule_id, raw_text),
        rule_id=rule_id,
        path=document.path,
        text=raw_text,
        range=doc_range,
        doc_range=doc_range,
        projection=raw_projection,
        origin=block.origin,
        region_class=block.region_class,
        source_sha256=document.source_sha256,
    )
    unit.pack_id = pack.id
    unit.rule_ids = (rule_id,)
    unit.context = _neighbor_context(document, block)
    unit.document_text = document.raw
    unit.passage_id = _passage_id(document, doc_range)
    return unit


def _table_units(
    document: Document,
    block: Any,
    rule_id: str,
    pack: Pack,
    ordinal_counter: Counter[tuple[str, str, str]] | None = None,
) -> list[Any]:
    if ordinal_counter is None:
        ordinal_counter = Counter()
    raw = document.raw
    raw_bytes = raw.encode("utf-8")
    cursor = 0
    units: list[Any] = []
    document_projection = document.projection
    if document_projection is None:
        return units
    for line_number in range(block.lines[0], len(document.raw_lines) + 1):
        line = document.raw_lines[line_number - 1]
        if not line.strip().startswith("|"):
            break
        line_start = raw.find(line, cursor)
        if line_start < 0:
            continue
        cursor = line_start + len(line) + 1
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        content = stripped[1:-1] if stripped.endswith("|") else stripped[1:]
        parts = content.split("|")
        if parts and all(re.fullmatch(r"\s*:?-{1,}:?\s*", part) for part in parts):
            continue
        content_start = line_start + line.index(stripped) + 1
        part_cursor = 0
        for part in parts:
            value = part.strip()
            part_start = content.find(part, part_cursor)
            if part_start < 0:
                continue
            part_cursor = part_start + len(part)
            if not value:
                continue
            if not any(character.isalpha() for character in value):
                document._a2_no_prose_count = getattr(document, "_a2_no_prose_count", 0) + 1
                continue
            start_cp = content_start + part_start + (len(part) - len(part.lstrip()))
            end_cp = start_cp + len(value)
            start_byte = len(raw[:start_cp].encode("utf-8"))
            end_byte = len(raw[:end_cp].encode("utf-8"))
            selected = [
                segment
                for segment in document_projection.segments
                if segment.raw_end > start_byte and segment.raw_start < end_byte
            ]
            if not selected:
                continue
            doc_range = (selected[0].proj_start, selected[-1].proj_end)
            projection = _identity_projection(value, start_byte, raw_bytes)
            unit = SpanCandidate(
                ordinal=_next_ordinal(ordinal_counter, "SPAN_CANDIDATE", rule_id, value),
                rule_id=rule_id,
                path=document.path,
                text=value,
                range=doc_range,
                doc_range=doc_range,
                projection=projection,
                origin=block.origin,
                region_class=block.region_class,
                source_sha256=document.source_sha256,
            )
            unit.pack_id = pack.id
            unit.rule_ids = (rule_id,)
            unit.context = _neighbor_context(document, block)
            unit.document_text = document.raw
            unit.passage_id = _passage_id(document, doc_range)
            units.append(unit)
    return units


def _unit_from_block(
    document: Document,
    block: Any,
    rule_id: str,
    pack: Pack,
    ordinal_counter: Counter[tuple[str, str, str]] | None = None,
) -> list[Any]:
    if ordinal_counter is None:
        ordinal_counter = Counter()
    # Sentence units preserve exact evidence coordinates while retaining one unit
    # for a paragraph with no sentence segmentation (tables and unusual Markdown).
    if block.kind not in {BlockKind.PARAGRAPH, BlockKind.QUOTE, BlockKind.LIST_ITEM, BlockKind.TABLE, BlockKind.HEADING}:
        return []
    if not block.text or block.projection is None:
        return []
    sentences = list(block.sentences)
    if block.kind is BlockKind.TABLE:
        return _table_units(document, block, rule_id, pack, ordinal_counter)
    if not sentences:
        raw_text, raw_projection = _raw_unit_projection(document, block.doc_range)
        unit = SpanCandidate(
            ordinal=_next_ordinal(ordinal_counter, "SPAN_CANDIDATE", rule_id, raw_text),
            rule_id=rule_id,
            path=document.path,
            text=raw_text,
            range=block.doc_range,
            doc_range=block.doc_range,
            projection=raw_projection,
            origin=block.origin,
            region_class=block.region_class,
            source_sha256=document.source_sha256,
        )
        unit.pack_id = pack.id
        unit.rule_ids = (rule_id,)
        unit.context = _neighbor_context(document, block)
        unit.document_text = document.raw
        unit.passage_id = _passage_id(document, block.doc_range)
        return [unit]
    units: list[Any] = []
    cursor = 0
    for sentence in sentences:
        units.append(_unit_from_sentence(document, block, sentence, cursor, rule_id, pack, ordinal_counter))
        cursor = max(cursor, block.text.find(sentence.text, cursor) + len(sentence.text))
    return units



_NORMATIVE_START = re.compile(
    r"^(?:MUST(?:\s+NOT)?|SHOULD|SHALL|MAY|NEVER|NOT|DEFAULT|AVOID|REQUIRED|PROHIBITED|GOTCHA|ALWAYS)\b"
)
_IMPERATIVE_STEERING_START = IMPERATIVE_MARKERS


def _is_list_marker_unit(unit: Any) -> bool:
    source_line, offset = _source_line(unit)
    if offset <= 0 or not source_line:
        return False
    return bool(re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", source_line))


def _imperative_directive(text: str) -> bool:
    """Recognize direct imperative paragraphs without promoting prose subjects."""
    stripped = text.strip()
    if "?" in stripped or re.match(r"^(?:i|we|me|us|my|our|ours|let's)\b", stripped, re.I):
        return False
    if not _IMPERATIVE_STEERING_START.match(stripped):
        return False
    return classify_text_type(stripped) is TextType.PROCEDURAL


def _is_normative_register(unit: Any) -> bool:
    text = str(getattr(unit, "text", "")).strip()
    if _NORMATIVE_START.match(text):
        return True
    # List items retain the historical direct-marker path.  In particular,
    # question-marked direct steps are preserved, while ``remember/to`` list
    # prose remains eligible as it was before paragraph recognition changed.
    if _is_list_marker_unit(unit):
        return bool(
            _IMPERATIVE_STEERING_START.match(text)
            and not TO_VERB.match(text)
            and not REMEMBER_TO.match(text)
        )
    return _imperative_directive(text)


def _source_start(unit: Any) -> int | None:
    segments = tuple(getattr(getattr(unit, "projection", None), "segments", ()))
    return min((int(segment.raw_start) for segment in segments), default=None)


def _source_line(unit: Any) -> tuple[str, int]:
    raw = str(getattr(unit, "document_text", ""))
    start = _source_start(unit)
    if start is None or not raw:
        return "", 0
    prefix = raw.encode("utf-8")[:start].decode("utf-8", errors="ignore")
    line_start = raw.rfind("\n", 0, len(prefix)) + 1
    line_end = raw.find("\n", len(prefix))
    if line_end < 0:
        line_end = len(raw)
    return raw[line_start:line_end], len(prefix) - line_start


def _is_fragment_unit(unit: Any) -> bool:
    text = str(getattr(unit, "text", "")).strip()
    if len(re.findall(r"[^\W\d_]+", text, flags=re.UNICODE)) < 3:
        return True
    source_line, offset = _source_line(unit)
    if source_line and offset > 0 and source_line[offset - 1].isalnum():
        return True
    return bool(re.match(r"^\s{0,3}#{1,6}(?:\s|$)", source_line))



def _admission(unit: Any, pack: Pack) -> tuple[str, str | None]:
    if not str(unit.text).strip():
        return "DROP", "a2_text_unavailable"
    if _is_fragment_unit(unit):
        return "DROP", "a2_fragment_unit"
    if unit.origin in {"generated", "vendored", "template"}:
        return "DROP", None
    if unit.region_class in {"quoted", "example"} and "quoted_specimen" in pack.protects:
        return "PRESERVE", "quoted_specimen"
    if _is_normative_register(unit) and "normative_obligation" in pack.protects:
        return "PRESERVE", "normative_obligation"
    return "ELIGIBLE", None


def _call_id(pack: Pack, units: list[dict[str, Any]]) -> str:
    payload = json.dumps([pack.id, [u["unit_id"] for u in units]], sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()[:20]


def _prompt_for(pack: Pack, units: list[dict[str, Any]], spine: str, instrument: str) -> dict[str, Any]:
    system = render_pack(pack, spine)
    passages: dict[str, dict[str, Any]] = {}
    pairs: list[dict[str, Any]] = []
    for unit in units:
        passage_id = str(unit.get("passage_id", unit["unit_id"]))
        if passage_id not in passages:
            passages[passage_id] = {
                "text": unit.get("model_text", unit["text"]),
                "context": unit.get("model_context", unit.get("context", "")),
                "doc_range": unit["doc_range"],
            }
        pairs.append({
            "unit_id": unit["unit_id"],
            "passage_id": passage_id,
            "rule_id": unit["rule_id"],
            "kind": unit["kind"],
        })
    user = json.dumps(
        {"instrument_id": instrument, "pack_id": pack.id, "passages": passages, "pairs": pairs},
        ensure_ascii=False,
    )
    return {"system": system, "user": user}




def _valid_placeholder(unit: Any, *, preserve: bool = False) -> dict[str, Any]:
    if unit.kind == "PASSAGE_PROBE":
        return {
            "unit_id": unit.unit_id,
            "rule_id": unit.rule_id,
            "kind": unit.kind,
            "note": "Admission preset.",
            "admissible": True,
            "evidence": None,
            "occurrences": [],
            "occurrences_truncated": False,
            "scores": None,
            "preservation_reason": "quoted_specimen" if preserve else None,
            "abstain_reason": None,
            "rewrite": None,
            "rewrite_status": "not_applicable",
            "verdict": "preserve" if preserve else "reject",
        }
    return {
        "unit_id": unit.unit_id,
        "rule_id": unit.rule_id,
        "kind": unit.kind,
        "note": "Admission preset.",
        "admissible": True,
        "evidence": [],
        "occurrences": None,
        "occurrences_truncated": False,
        "scores": {"fit": "absent", "harm": "none", "repair": "inapplicable", "warrant": "none"},
        "preservation_reason": "quoted_specimen" if preserve else None,
        "abstain_reason": None,
        "rewrite": None,
        "rewrite_status": "not_applicable",
        "verdict": "preserve" if preserve else "reject",
    }


def _rule_map(ruleset: Any) -> dict[str, Any]:
    return {rule.qualified_id: rule for rule in ruleset.rules}


def _pack_selection(packs: Sequence[Pack], selected: str | None) -> list[Pack]:
    if not selected or selected.strip().lower() == "all":
        return [pack for pack in packs if pack.rules]
    wanted = {part.strip() for part in selected.split(",") if part.strip()}
    available = {pack.id for pack in packs}
    unknown = wanted - available
    if unknown:
        raise ValueError("unknown judgement pack(s): " + ", ".join(sorted(unknown)))
    return [pack for pack in packs if pack.id in wanted and pack.rules]


def prepare(
    *,
    config: Path,
    out: Path,
    paths: Sequence[str | Path],
    profile: str | None = None,
    packs: str | None = "all",
    categories: Sequence[str] = (),
    max_calls: int = 300,
    yes: bool = False,
    gold: Path | None = None,
) -> dict[str, Any]:
    """Run deterministic linting and emit compact, model-ready request artifacts."""
    if max_calls < 0:
        raise ValueError("max_calls must be non-negative")
    gold_source, gold_rows = _load_gold_rows(gold, paths)
    out.mkdir(parents=True, exist_ok=True)
    context = load_run_context(
        tuple(str(path) for path in paths),
        profile=profile,
        config_path=config,
        rules_dir=(),
        only_categories=tuple(categories),
        disabled=(),
        min_score=None,
        max_per_100_words=None,
        locale_tag=None,
    )
    scores = run_lint(context, no_vale=False)
    root = next(iter(context.configs.values())).root if context.configs else config.parent
    deterministic_dir = out / "deterministic"
    deterministic_dir.mkdir(parents=True, exist_ok=True)
    score_by_path = {str(score.path): score for score in scores}
    all_pack_hashes: list[str] = []
    per_doc: list[dict[str, Any]] = []
    all_units: list[dict[str, Any]] = []
    all_prompts: list[dict[str, Any]] = []
    document_data: dict[str, dict[str, Any]] = {}
    gold_attachment_counts: Counter[str] = Counter()
    pack_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"units": 0, "calls": 0, "passages": set()}
    )
    spine_revision = rubric_revision(_SPINE)
    a2_no_prose_total = 0
    a2_fragment_unit_total = 0
    for path in context.paths:
        path = Path(path)
        config_for_path = context.configs[path]
        ruleset = context.rulesets[path]
        resolved = resolve_for(config_for_path, path)
        active = []
        selected_categories = {str(category).strip() for category in categories if str(category).strip()}
        for rule in ruleset.rules:
            if selected_categories and rule.category not in selected_categories:
                continue
            if rule.kind is not RuleKind.JUDGEMENT or rule.judgement is None:
                continue
            if rule.tier_for(resolved.profile.value).value == "excluded":
                continue
            category = resolved.categories.get(rule.category)
            override = resolved.rules.get(rule.qualified_id)
            if category is not None and getattr(category.severity, "value", category.severity) == "off":
                continue
            if override is not None and getattr(override.severity, "value", override.severity) == "off":
                continue
            active.append(rule)
        selected_packs = _pack_selection(build_packs(active), packs)
        pack_hashes = [pack_id(pack) for pack in selected_packs]
        all_pack_hashes.extend(pack_hashes)
        instrument = instrument_id(spine_revision, pack_hashes)
        raw = path.read_text(encoding="utf-8")
        document = parse(str(path), raw)
        judgement_text, judgement_projection = project(raw)
        document._judgement_projection = judgement_projection  # type: ignore[attr-defined]
        document_ref = _safe_name(path, root)
        document_data[document_ref] = {
            "path": str(path),
            "text": raw,
            "projected_text": judgement_text,
            "source_sha256": document.source_sha256,
            "projection": _projection_dict(judgement_projection),
            "gold_spans": [row for row in gold_rows if _gold_path_key(row["path"]) == _gold_path_key(path)],
        }
        score = score_by_path.get(str(path))
        if score is not None:
            (deterministic_dir / f"{document_ref}.json").write_text(
                json.dumps(score.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8"
            )
        doc_units: list[dict[str, Any]] = []
        ordinal_counter: Counter[tuple[str, str, str]] = Counter()
        seen_unit_ids: set[str] = set()
        doc_calls: list[dict[str, Any]] = []
        for pack in selected_packs:
            candidates: list[Any] = []
            if pack.scope_class == "probe":
                for rule_id in pack.rules:
                    raw_probe_text, raw_probe_projection = _raw_unit_projection(
                        document, (0, len(judgement_text))
                    )
                    unit = PassageProbe(
                        ordinal=_next_ordinal(ordinal_counter, "PASSAGE_PROBE", rule_id, raw_probe_text),
                        rule_id=rule_id,
                        path=str(path),
                        text=raw_probe_text,
                        range=(0, len(raw_probe_text)),
                        doc_range=(0, len(judgement_text)),
                        projection=raw_probe_projection,
                        origin=document.origin,
                        region_class="authored",
                        source_sha256=document.source_sha256,
                    )
                    unit.pack_id = pack.id
                    unit.rule_ids = (rule_id,)
                    unit.context = ""
                    unit.document_text = document.raw
                    unit.passage_id = _passage_id(document, unit.doc_range)
                    candidates.append(unit)
            else:
                for rule_id in pack.rules:
                    for block in document.blocks:
                        candidates.extend(_unit_from_block(document, block, rule_id, pack, ordinal_counter))

            admissible: list[dict[str, Any]] = []
            for unit in candidates:
                if unit.unit_id in seen_unit_ids:
                    continue
                seen_unit_ids.add(unit.unit_id)
                admission, reason = _admission(unit, pack)
                unit.admission = admission
                unit.admission_reason = reason
                if reason == "a2_fragment_unit":
                    a2_fragment_unit_total += 1
                unit.preservation_reason = reason if admission == "PRESERVE" else None
                if unit.kind == "SPAN_CANDIDATE" and admission == "ELIGIBLE":
                    try:
                        source_text = unit.projection.slice_raw(0, len(unit.text)).decode("utf-8")
                    except (UnicodeDecodeError, ValueError) as exc:
                        raise AssertionError(f"eligible span source map is invalid: {unit.unit_id}") from exc
                    if not unit.text.strip() or "\x00" in unit.text or source_text != unit.text:
                        raise AssertionError(f"eligible span has invalid source text: {unit.unit_id}")
                unit.status = "not_run" if admission == "DROP" else ""
                source_item = _unit_dict(
                    unit,
                    document_ref=document_ref,
                    passage_id=str(getattr(unit, "passage_id", _passage_id(document, unit.doc_range))),
                )
                gold_matches = _gold_rows_for_unit(
                    gold_rows, str(path), source_item["source_range"], str(unit.rule_id)
                )
                gold_ids = [str(row["gold_id"]) for row in gold_matches]
                for gold_id in gold_ids:
                    gold_attachment_counts[gold_id] += 1
                item = _unit_dict(
                    unit,
                    document_ref=document_ref,
                    passage_id=str(getattr(unit, "passage_id", _passage_id(document, unit.doc_range))),
                    gold_ids=gold_ids,
                    gold_control=any(bool(row.get("control")) for row in gold_matches),
                )
                if gold_ids:
                    kinds = {str(row.get("kind", "seeded")) for row in gold_matches}
                    item["gold_kind"] = next(iter(kinds)) if len(kinds) == 1 else "mixed"
                    if len(kinds) > 1:
                        item["gold_kinds"] = sorted(kinds)
                item["document"] = str(path)
                item["pack_hash"] = pack_id(pack)
                doc_units.append(item)
                all_units.append(item)
                stat = pack_stats[pack.id]
                stat["units"] += 1
                stat["passages"].add(item["passage_id"])
                if admission == "ELIGIBLE":
                    admissible.append(item)

            passage_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in admissible:
                passage_groups[item["passage_id"]].append(item)
            ordered_passages = list(passage_groups)
            group_limit = 5 if pack.scope_class != "probe" else max(1, len(ordered_passages))
            for start in range(0, len(ordered_passages), group_limit):
                passage_ids = ordered_passages[start : start + group_limit]
                batch: list[dict[str, Any]] = []
                for passage_id in passage_ids:
                    by_rule = {item["rule_id"]: item for item in passage_groups[passage_id]}
                    batch.extend(by_rule[rule_id] for rule_id in pack.rules if rule_id in by_rule)
                if not batch:
                    continue
                kind = "PASSAGE_PROBE" if pack.scope_class == "probe" else "SPAN_CANDIDATE"
                call_id = _call_id(pack, batch)
                prompt = _prompt_for(pack, batch, _SPINE, instrument)
                request_digest = hashlib.sha256(
                    json.dumps(prompt, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()
                cache_keys = [
                    judgement_cache_key(
                        instrument_id=instrument,
                        unit_id=item["unit_id"],
                        context_hash=hashlib.sha256(str(item.get("context", "")).encode()).hexdigest(),
                        provider="parent",
                        model_id_and_revision="external",
                        full_rendered_request_digest=request_digest,
                        system_prompt=prompt["system"],
                        decoding_config={},
                        seed=None,
                        repeat_index=0,
                        evaluator_runner_revision="driver-1",
                    )
                    for item in batch
                ]
                call = {
                    "call_id": call_id,
                    "document": str(path),
                    "pack_id": pack.id,
                    "pack_hash": pack_id(pack),
                    "rule_ids": list(pack.rules),
                    "kind": kind,
                    "unit_ids": [item["unit_id"] for item in batch],
                    "instrument_id": instrument,
                    "cache_keys": cache_keys,
                    "prompt": prompt,
                    "response_schema": _schema_wrapper(batch, kind),
                }
                doc_calls.append(call)
                all_prompts.append(call)
                pack_stats[pack.id]["calls"] += 1
        a2_no_prose_total += int(getattr(document, "_a2_no_prose_count", 0))
        per_doc.append(
            {
                "path": str(path),
                "deterministic": f"deterministic/{document_ref}.json",
                "document_ref": document_ref,
                "profile": resolved.profile.value,
                "instrument_id": instrument,
                "pack_ids": [pack.id for pack in selected_packs],
                "unit_count": len(doc_units),
                "call_count": len(doc_calls),
            }
        )

    if len(all_prompts) > max_calls and not yes:
        print(f"refusing to write {len(all_prompts)} calls (maximum {max_calls}); use --yes to continue")
        for pack_id_value in sorted(pack_stats):
            stat = pack_stats[pack_id_value]
            print(f"{pack_id_value}: units={stat['units']} calls={stat['calls']} passages={len(stat['passages'])}")
        raise ValueError(f"call limit exceeded: {len(all_prompts)} > {max_calls}")

    manifest = {
        "version": 1,
        "config": str(config.resolve()),
        "profile": profile,
        "documents": per_doc,
        "pack_ids": sorted({call["pack_id"] for call in all_prompts}),
        "pack_hashes": sorted(set(all_pack_hashes)),
        "rubric_revision": spine_revision,
        "instrument_id": per_doc[0]["instrument_id"] if len({doc["instrument_id"] for doc in per_doc}) == 1 and per_doc else None,
        "gold": {
            "path": str(gold_source) if gold_source is not None else None,
            "spans": gold_rows,
            "attachment_counts": dict(gold_attachment_counts),
            "multi_unit_attachments": sum(count > 1 for count in gold_attachment_counts.values()),
            "unattached": [
                str(row["gold_id"])
                for row in gold_rows
                if not gold_attachment_counts.get(str(row["gold_id"]), 0)
            ],
        },
        "counts": {
            "documents": len(per_doc),
            "units": len(all_units),
            "calls": len(all_prompts),
            "passages": len({(item["document_ref"], item["passage_id"]) for item in all_units}),
            "admissible_units": sum(item["admission"] == "ELIGIBLE" for item in all_units),
            "a2_text_unavailable": sum(item.get("admission_reason") == "a2_text_unavailable" for item in all_units),
            "a2_no_prose": a2_no_prose_total,
            "a2_fragment_unit": a2_fragment_unit_total,
        },
        "response_schema": "Calls with multiple units wrap outputs as {\"results\": [model_output...]}; a single probe may return one model_output object.",
        "pack_counts": {
            pack_id_value: {
                "units": stat["units"],
                "calls": stat["calls"],
                "passages": len(stat["passages"]),
            }
            for pack_id_value, stat in sorted(pack_stats.items())
        },
    }
    documents_dir = out / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    for document_ref, data in document_data.items():
        (documents_dir / f"{document_ref}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    _write_jsonl(out / "units.jsonl", all_units)
    _write_jsonl(out / "prompts.jsonl", all_prompts)
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _records_json(records: Iterable[FindingRecord]) -> list[dict[str, Any]]:
    result = []
    for record in records:
        item = asdict(record)
        item["evidence"] = [asdict(span) for span in record.evidence]
        result.append(item)
    return result


def _load_rules_for_manifest(manifest: dict[str, Any], units: list[dict[str, Any]]) -> tuple[dict[str, Any], Any, dict[str, float]]:
    config_path = Path(str(manifest.get("config", "")))
    try:
        config = Config.model_validate_json(config_path.read_text(encoding="utf-8")) if config_path.suffix == ".json" else None
    except (OSError, ValueError):
        config = None
    if config is None:
        try:
            from ..config import load_config
            config = load_config(config_path)
        except Exception:
            config = Config(profile=Profile(str(manifest.get("profile") or "normal")))
    ruleset = load_ruleset([])
    rule_map = _rule_map(ruleset)
    weights = {category.id: category.weight for category in ruleset.categories.values()}
    return rule_map, config, weights


def _record_for_admission(unit: Any, rule: Any, instrument: str, cache: str) -> FindingRecord:
    preserve = unit.admission == "PRESERVE"
    return adjudicate(
        unit,
        rule,
        _valid_placeholder(unit, preserve=preserve),
        instrument_id=instrument,
        cache_key=cache,
    )


def _response_payload(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _find_call_prompts(out: Path) -> dict[str, dict[str, Any]]:
    return {str(item["call_id"]): item for item in (_read_jsonl(out / "prompts.jsonl"))}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            values.append(json.loads(line))
    return values


def _serialize_coverage(value: Any) -> Any:
    return value.as_dict() if hasattr(value, "as_dict") else value


def _score_with_judgement(
    deterministic: dict[str, Any], records: list[FindingRecord], manifest: dict[str, Any], config: Config, rule_map: dict[str, Any], weights: dict[str, float], path: str,
) -> Any:
    try:
        resolved = resolve_for(config, Path(path))
    except Exception:
        resolved = resolve_for(Config(profile=Profile(str(deterministic.get("profile", "normal")))), Path(path))
    mechanical = [Finding.model_validate(item) for item in deterministic.get("findings", [])]
    return score_document(
        path,
        mechanical,
        int(deterministic.get("words", 0)),
        int(deterministic.get("sentences", 0)),
        int(deterministic.get("paragraphs", 0)),
        resolved,
        weights,
        deterministic.get("unchecked", []),
        judgement_findings=records,
        judgement_weights=weights,
    )


def _markdown_report(
    documents: list[dict[str, Any]],
    units: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
    evidence_offset_mismatch: int = 0,
) -> str:
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        unit = units.get(str(finding["unit_id"]))
        by_doc[str(unit.get("path", "<unknown>")) if unit else "<unknown>"].append(finding)
    lines = ["# Judgement comparison", "", f"evidence_offset_mismatch: {evidence_offset_mismatch}", ""]
    for doc in documents:
        path = str(doc["path"])
        lines.extend([f"## {path}", "", "| measure | deterministic | judgement |", "| --- | ---: | ---: |"])
        lines.append(f"| score | {doc.get('deterministic_score', 0):.1f} | {doc.get('adjusted_score', 0):.1f} |")
        lines.append(f"| findings | {doc.get('deterministic_findings', 0)} | {doc.get('confirmed', 0)} confirms |")
        lines.append("")
        for finding in by_doc.get(path, []):
            if finding.get("outcome") != "CONFIRM":
                continue
            evidence = finding.get("evidence") or []
            quote = evidence[0].get("quote", "") if evidence else ""
            lines.extend([
                f"### CONFIRM `{finding['rule_id']}` ({finding.get('severity') or 'none'})",
                "",
                f"> {quote}",
                "",
                f"Rewrite: {finding.get('rewrite_status', 'not_applicable')}",
            ])
            unit = units.get(str(finding["unit_id"]))
            if unit and finding.get("rewrite") is not None:
                diff = difflib.unified_diff(
                    str(unit.get("text", "")).splitlines(keepends=True),
                    str(finding["rewrite"]).splitlines(keepends=True),
                    fromfile="unit",
                    tofile="rewrite",
                    lineterm="",
                )
                lines.extend(["", "```diff", *diff, "```"])
            lines.append("")
        preserve = Counter(
            f.get("preservation_reason") or "unknown"
            for f in by_doc.get(path, [])
            if f.get("outcome") == "PRESERVE"
        )
        abstain = Counter(
            f.get("abstain_reason") or "unknown"
            for f in by_doc.get(path, [])
            if f.get("outcome") == "ABSTAIN"
        )
        lines.append("PRESERVE: " + (", ".join(f"{key}={value}" for key, value in sorted(preserve.items())) or "0"))

        lines.append("ABSTAIN: " + (", ".join(f"{key}={value}" for key, value in sorted(abstain.items())) or "0"))
        lines.append("")
    return "\n".join(lines)
def _evidence_offset_mismatches(unit: dict[str, Any], output: dict[str, Any]) -> int:
    verdict = str(output.get("verdict", "")).upper()
    if verdict != "CONFIRM" and output.get("preservation_reason") is None:
        return 0
    text = str(unit.get("model_text", unit.get("text", "")))
    mismatches = 0
    for evidence in output.get("evidence") or ():
        quote = evidence.get("quote")
        start = evidence.get("start")
        end = evidence.get("end")
        if isinstance(quote, str) and quote and quote in text and isinstance(start, int) and isinstance(end, int):
            if text[start:end] != quote:
                mismatches += 1
    return mismatches
def _salvage_unique_quotes(unit: dict[str, Any], output: dict[str, Any]) -> None:
    """Repair offsets only for unique quotes located in the unit."""
    text = str(unit.get("model_text", unit.get("text", "")))
    for evidence in output.get("evidence") or ():
        if evidence.get("source") != "unit":
            continue
        quote = evidence.get("quote")
        if not isinstance(quote, str) or not quote:
            continue
        first = text.find(quote)
        second = text.find(quote, first + 1) if first >= 0 else -1
        if first >= 0 and second < 0:
            evidence["start"] = first
            evidence["end"] = first + len(quote)


def _unit_gold_ids(unit: dict[str, Any]) -> tuple[str, ...]:
    values = unit.get("gold_ids")
    if isinstance(values, (list, tuple)):
        return tuple(str(value) for value in values if isinstance(value, str) and value)
    value = unit.get("gold_id")
    return (value,) if isinstance(value, str) and value else ()


def _evidence_document_range(
    unit: dict[str, Any], evidence: dict[str, Any]
) -> tuple[int, int] | None:
    if evidence.get("source") != "unit":
        return None
    start, end = evidence.get("start"), evidence.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
        return None
    text = str(unit.get("model_text", unit.get("text", "")))
    if end > len(text):
        return None
    source_range = unit.get("source_range")
    if isinstance(source_range, (list, tuple)) and len(source_range) == 2 and all(
        isinstance(value, int) for value in source_range
    ):
        base = int(source_range[0])
        return base + len(text[:start].encode("utf-8")), base + len(text[:end].encode("utf-8"))
    doc_start, doc_end = evidence.get("doc_start"), evidence.get("doc_end")
    if isinstance(doc_start, int) and isinstance(doc_end, int):
        return doc_start, doc_end
    return start, end


def _evidence_overlaps_gold(
    unit: dict[str, Any], finding: dict[str, Any], gold_row: dict[str, Any]
) -> bool:
    start, end = gold_row.get("start"), gold_row.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or end <= start:
        return False
    return any(
        (located := _evidence_document_range(unit, evidence)) is not None
        and located[0] < end
        and start < located[1]
        for evidence in finding.get("evidence") or ()
        if isinstance(evidence, dict)
    )


def _gold_recall(
    gold_rows: Sequence[dict[str, Any]],
    units: dict[str, dict[str, Any]],
    findings: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    seeded = [row for row in gold_rows if row.get("kind", "seeded") == "seeded" and not row.get("control")]
    controls = [row for row in gold_rows if row.get("kind") == "control" or row.get("control")]
    seeded_by_id = {str(row["gold_id"]): row for row in seeded}
    control_ids = {str(row["gold_id"]) for row in controls}
    confirmed_seeded: set[str] = set()
    confirmed_controls: set[str] = set()
    for finding in findings:
        if finding.get("outcome") != "CONFIRM":
            continue
        unit = units.get(str(finding.get("unit_id")), {})
        for gold_id in _unit_gold_ids(unit):
            seeded_row = seeded_by_id.get(gold_id)
            if seeded_row is not None and (
                seeded_row.get("rule_id") is None or str(finding.get("rule_id")) == str(seeded_row.get("rule_id"))
            ) and _evidence_overlaps_gold(unit, finding, seeded_row):
                confirmed_seeded.add(gold_id)
            if gold_id in control_ids:
                confirmed_controls.add(gold_id)
    per_rule: dict[str, float | None] = {}
    for rule_id in sorted({str(row.get("rule_id")) for row in seeded if row.get("rule_id") is not None}):
        rows = [row for row in seeded if str(row.get("rule_id")) == rule_id]
        confirmed = sum(str(row["gold_id"]) in confirmed_seeded for row in rows)
        per_rule[rule_id] = confirmed / len(rows) if rows else None
    seeded_total = len(seeded)
    recall: dict[str, Any] = {
        "overall": len(confirmed_seeded) / seeded_total if seeded_total else None,
        "per_rule": per_rule,
    }
    attachment_counts = Counter(
        gold_id
        for unit in units.values()
        for gold_id in _unit_gold_ids(unit)
    )
    multi_unit = sum(count > 1 for count in attachment_counts.values())
    if multi_unit:
        recall["multi_unit_attachments"] = multi_unit
    return recall, {"count": len(confirmed_controls), "total": len(controls)}


# Row verdicts. Summary blocks may carry diagnostic subset counters such as
# `FP_fragment_units` (a subset of FP, not extra adjudications); those keys are
# deliberately absent so they never enter a denominator.
_ADJUDICATION_LABELS: dict[str, str] = {
    "TP": "TP",
    "B": "B",
    "BORDERLINE": "B",
    "FP": "FP",
    "FP-PRESERVE-MISS": "FP",
    "FP_PRESERVE_MISS": "FP",
    "FP-FRAGMENT-UNIT": "FP",
    "FP_FRAGMENT_UNIT": "FP",
}


def _adjudication_rows(value: Any) -> list[str]:
    """Collect per-confirm verdict labels; summary count blocks are ignored."""
    labels: list[str] = []
    if isinstance(value, dict):
        verdict = value.get("verdict", value.get("adjudication"))
        if isinstance(verdict, str):
            labels.append(verdict.upper())
        for child in value.values():
            labels.extend(_adjudication_rows(child))
    elif isinstance(value, list):
        for child in value:
            labels.extend(_adjudication_rows(child))
    return labels


def _adjudication_summary(value: Any) -> Counter[str]:
    """Fallback: the first `adjudication` count block found, when no rows exist."""
    if isinstance(value, dict):
        nested = value.get("adjudication")
        if isinstance(nested, dict):
            counts: Counter[str] = Counter()
            for label, count in nested.items():
                if isinstance(count, (int, float)) and not isinstance(count, bool):
                    counts[str(label).upper()] += int(count)
            return counts
        for child in value.values():
            found = _adjudication_summary(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _adjudication_summary(child)
            if found:
                return found
    return Counter()


def _adjudication_precision(path: Path | None) -> tuple[float | None, float | None]:
    """Return strict/lenient precision when an adjudication file is supplied.

    Each adjudicated confirm is counted once, from its row; summary blocks are
    used only when a file carries no rows. Labels outside the explicit map
    (diagnostic subsets such as FP_FRAGMENT_UNITS) never enter the denominator.
    """
    if path is None:
        return None, None
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    rows = _adjudication_rows(payload)
    if rows:
        for label in rows:
            mapped = _ADJUDICATION_LABELS.get(label)
            if mapped:
                counts[mapped] += 1
    else:
        for label, count in _adjudication_summary(payload).items():
            mapped = _ADJUDICATION_LABELS.get(label)
            if mapped:
                counts[mapped] += count
    tp = counts["TP"]
    fp = counts["FP"]
    borderline = counts["B"]
    denominator = tp + fp + borderline
    if not denominator:
        return None, None
    return tp / denominator, (tp + borderline) / denominator


def finish(*, out: Path, responses: Path, offset_salvage: str = "unique-quote", adjudication: Path | None = None) -> dict[str, Any]:
    """Validate response JSONL, adjudicate records, and write reports."""
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    unit_items = _read_jsonl(out / "units.jsonl")
    units = {str(item["unit_id"]): item for item in unit_items}
    documents: dict[str, dict[str, Any]] = {}
    for doc in manifest.get("documents", []):
        document_ref = str(doc.get("document_ref", ""))
        if document_ref:
            path = out / "documents" / f"{document_ref}.json"
            if path.exists():
                documents[document_ref] = json.loads(path.read_text(encoding="utf-8"))
    prompt_calls = _find_call_prompts(out)
    response_items = {str(item.get("call_id")): item for item in _read_jsonl(responses)}
    rule_map, config, weights = _load_rules_for_manifest(manifest, unit_items)
    records: list[FindingRecord] = []
    failed: list[dict[str, Any]] = []
    evidence_offset_mismatch = 0
    model_confirms = 0
    evidence_gate_discards = 0
    unit_objects = {unit_id: _unit_from_dict(item, documents) for unit_id, item in units.items()}

    for item in unit_items:
        if item.get("admission") in {"DROP", "PRESERVE"}:
            rule = rule_map.get(str(item.get("rule_id", "")))
            if rule is not None:
                record = _record_for_admission(unit_objects[item["unit_id"]], rule, "", "")
                records.extend(record if isinstance(record, tuple) else (record,))
            continue
        item["status"] = "not_run"

    for call_id, call in prompt_calls.items():
        target_units = [units[unit_id] for unit_id in call.get("unit_ids", ()) if unit_id in units]
        response_item = response_items.get(call_id)
        if response_item is None:
            for unit in target_units:
                unit["status"] = "failed"
            failed.append(
                {
                    "call_id": call_id,
                    "unit_ids": call.get("unit_ids", []),
                    "reason": "response_missing",
                    "errors": ["response_missing"],
                }
            )
            continue
        try:
            payload = _response_payload(response_item.get("response"))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            error = f"response_json: {exc}"
            failed.append({"call_id": call_id, "unit_ids": call.get("unit_ids", []), "errors": [error]})
            for unit in target_units:
                unit["status"] = "failed"
            continue
        if isinstance(payload, dict) and "results" in payload:
            rows = payload.get("results")
        elif len(target_units) == 1:
            rows = [payload]
        else:
            rows = None
        missing_ids: list[str] = []
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
            actual_ids = [str(row.get("unit_id")) for row in rows]
            missing_ids = [unit_id for unit_id in call.get("unit_ids", ()) if unit_id not in actual_ids]
        elif rows is None:
            missing_ids = [str(unit_id) for unit_id in call.get("unit_ids", ())]
        validation_error = validate_result_set(target_units, rows)
        missing_payload = rows is None or (validation_error is not None and validation_error.startswith("missing unit_id:"))
        if validation_error is not None and missing_ids and missing_payload:
            for unit_id in missing_ids:
                units[unit_id]["status"] = "failed"
            failed.append(
                {
                    "call_id": call_id,
                    "unit_ids": missing_ids,
                    "reason": "row_missing",
                    "errors": ["row_missing"],
                }
            )
            row_values = [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        else:
            row_values = rows if validation_error is None else []
        if validation_error is not None and not missing_payload:
            failed.append({"call_id": call_id, "unit_ids": call.get("unit_ids", []), "errors": [validation_error]})
            for unit in target_units:
                unit["status"] = "failed"
            continue
        row_values = [dict(row) for row in row_values]
        for row in row_values:
            row.pop("passage_id", None)
        row_errors: list[str] = []
        for row in row_values:
            row_errors.extend(validate_model_output(row))
        if row_errors:
            failed.append({"call_id": call_id, "unit_ids": call.get("unit_ids", []), "errors": row_errors})
            for unit in target_units:
                unit["status"] = "failed"
            continue
        for row in row_values:
            unit_id = str(row["unit_id"])
            unit_item = units[unit_id]
            unit_item["status"] = "attempted"
            unit = unit_objects[unit_id]
            rule = rule_map.get(str(unit_item.get("rule_id", "")))
            if rule is None:
                continue
            output = dict(row)
            output["unit_id"] = unit_id
            output["rule_id"] = str(unit_item["rule_id"])
            output["kind"] = unit.kind
            if offset_salvage == "unique-quote":
                _salvage_unique_quotes(unit_item, output)
            if str(output.get("verdict", "")).upper() == "CONFIRM":
                model_confirms += 1
            evidence_offset_mismatch += _evidence_offset_mismatches(unit_item, output)
            cache_keys = call.get("cache_keys", [""])
            index = call.get("unit_ids", []).index(unit_id)
            result = adjudicate(
                unit,
                rule,
                output,
                instrument_id=str(call.get("instrument_id", "")),
                cache_key=str(cache_keys[index] if index < len(cache_keys) else ""),
            )
            result_records = result if isinstance(result, tuple) else (result,)
            if str(output.get("verdict", "")).upper() == "CONFIRM" and any(
                record.outcome == "ABSTAIN"
                and record.abstain_reason == "no_exact_evidence"
                for record in result_records
            ):
                evidence_gate_discards += 1
            records.extend(result_records)

    _write_jsonl(out / "failed.jsonl", failed)
    finding_items = _records_json(records)
    _write_jsonl(out / "findings.jsonl", finding_items)
    eligible = [
        {
            "unit_id": item["unit_id"],
            "path": item.get("path", ""),
            "pack_id": item.get("pack_id", ""),
            "rule_id": item.get("rule_id", ""),
            "status": item.get("status", "not_run"),
            "truncated": item.get("truncated", False),
        }
        for item in unit_items
    ]
    coverage_result = coverage(records, eligible)
    coverage_dict = coverage_result.as_dict()
    report_documents: list[dict[str, Any]] = []
    by_path: dict[str, list[FindingRecord]] = defaultdict(list)
    for record in records:
        by_path[record.path].append(record)
    for doc in manifest.get("documents", []):
        path = str(doc["path"])
        deterministic_path = out / str(doc["deterministic"])
        deterministic = json.loads(deterministic_path.read_text(encoding="utf-8"))
        doc_records = by_path.get(path, [])
        score = _score_with_judgement(deterministic, doc_records, manifest, config, rule_map, weights, path)
        document_data_for_components = documents.get(str(doc.get("document_ref", "")), {})
        raw_text = str(document_data_for_components.get("text", ""))
        _, projection = project(raw_text)
        paragraph_boundaries = _paragraph_ranges(raw_text, projection)
        doc_components = components(doc_records, paragraph_boundaries, _DEPENDENCE_TABLE)
        gate = cluster_gate(doc_components, doc_records, config)
        outcomes = Counter(record.outcome for record in doc_records)
        severities = Counter(record.severity for record in doc_records if record.severity)
        report_documents.append(
            {
                "path": path,
                "deterministic_score": deterministic.get("score", score.score),
                "deterministic_findings": deterministic.get("total_findings", len(deterministic.get("findings", []))),
                "deterministic_passed": deterministic.get("passed", True),
                "judgement_findings": dict(outcomes),
                "judgement_severity": dict(severities),
                "confirmed": outcomes.get("CONFIRM", 0),
                "adjusted_score": score.judgement_adjusted_score,
                "judgement_penalty": score.judgement_penalty,
                "passed": score.passed,
                "cluster_gate": gate,
                "coverage": coverage_dict.get("documents", {}).get(path, {}),
                "abstention_reasons": dict(Counter(record.abstain_reason or "unknown" for record in doc_records if record.outcome == "ABSTAIN")),
                "preserve_reasons": dict(Counter(record.preservation_reason or "unknown" for record in doc_records if record.outcome == "PRESERVE")),
            }
        )
    gold_config = manifest.get("gold", {})
    gold_rows = gold_config.get("spans", []) if isinstance(gold_config, dict) else []
    gold_recall, control_false_confirms = _gold_recall(gold_rows, units, finding_items)
    gold_attachment = gold_config.get("attachment_counts", {}) if isinstance(gold_config, dict) else {}
    strict_precision, lenient_precision = _adjudication_precision(adjudication)
    report = {
        "version": 1,
        "offset_salvage": offset_salvage,
        **({"strict_precision": strict_precision, "lenient_precision": lenient_precision} if adjudication is not None else {}),
        "documents": report_documents,
        "coverage": coverage_dict,
        "preserve_rates": preserve_rates(records),
        "failed": failed,
        "gold_recall": gold_recall,
        "control_false_confirms": control_false_confirms,
        "gold_multi_unit_attachments": sum(int(count) > 1 for count in gold_attachment.values()),
        "gold_unattached": list(gold_config.get("unattached", [])) if isinstance(gold_config, dict) else [],
        "evidence_gate_discards": evidence_gate_discards,
        "evidence_offset_mismatch": evidence_offset_mismatch,
        "counts": {"findings": len(finding_items), "failed_calls": len(failed), "evidence_offset_mismatch": evidence_offset_mismatch},
    }
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "report.md").write_text(_markdown_report(report_documents, units, finding_items, evidence_offset_mismatch), encoding="utf-8")
    return report


def _preview_document(
    out: Path,
    doc: str,
    findings: list[dict[str, Any]],
    units: dict[str, dict[str, Any]],
    skipped: list[str] | None = None,
) -> Path:
    source = Path(doc)
    raw = source.read_text(encoding="utf-8")
    raw_bytes = raw.encode("utf-8")
    skipped = skipped if skipped is not None else []
    replacements: list[tuple[int, int, str, str]] = []
    for finding in findings:
        if finding.get("rewrite_status") != "proposed" or not finding.get("rewrite"):
            continue
        unit_id = str(finding.get("unit_id", ""))
        unit = units.get(unit_id)
        if unit is None:
            skipped.append(f"{unit_id}: unit not found")
            continue
        source_range = unit.get("source_range")
        if (
            not isinstance(source_range, list)
            or len(source_range) != 2
            or not all(isinstance(value, int) for value in source_range)
            or source_range[0] < 0
            or source_range[0] > source_range[1]
            or source_range[1] > len(raw_bytes)
        ):
            skipped.append(f"{unit_id}: invalid source range")
            continue
        start, end = source_range
        try:
            source_text = raw_bytes[start:end].decode("utf-8")
        except UnicodeDecodeError:
            skipped.append(f"{unit_id}: source range is not valid UTF-8")
            continue
        if source_text != str(unit.get("text", "")):
            skipped.append(f"{unit_id}: source text mismatch")
            continue
        replacements.append((start, end, str(finding["rewrite"]), unit_id))

    accepted: list[tuple[int, int, str, str]] = []
    for candidate in sorted(replacements, key=lambda value: (value[0], value[1], value[3])):
        start, end, _, unit_id = candidate
        conflict = next((item for item in accepted if start < item[1] and item[0] < end), None)
        if conflict is not None:
            reason = "duplicate span" if (start, end) == conflict[:2] else "overlapping span"
            skipped.append(f"{unit_id}: {reason} ({start}:{end})")
            continue
        accepted.append(candidate)

    data = raw_bytes
    for start, end, replacement, _ in sorted(accepted, key=lambda value: value[0], reverse=True):
        data = data[:start] + replacement.encode("utf-8") + data[end:]
    target = out.resolve() / "preview" / _safe_name(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def compare(*, out: Path, doc: Path | None = None, apply_preview: bool = False) -> str:
    """Print old/new judgement results and optionally write a rewrite preview."""
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    findings = _read_jsonl(out / "findings.jsonl")
    units = {str(item["unit_id"]): item for item in _read_jsonl(out / "units.jsonl")}
    selected = [item for item in report.get("documents", []) if doc is None or str(item.get("path")) == str(doc)]
    if not selected:
        raise ValueError(f"document not found in report: {doc}") if doc else ValueError("report has no documents")
    lines: list[str] = []
    for item in selected:
        lines.extend(
            [
                str(item["path"]),
                f"deterministic (old): score={item.get('deterministic_score', 0):.1f}, findings={item.get('deterministic_findings', 0)}, pass={item.get('deterministic_passed', True)}",
                f"judgement (new): score={item.get('adjusted_score', 0):.1f}, confirms={item.get('confirmed', 0)}, pass={item.get('passed', True)}, gate={item.get('cluster_gate') or 'none'}",
            ]
        )
        for finding in findings:
            unit = units.get(str(finding.get("unit_id")))
            if finding.get("outcome") == "CONFIRM" and unit and unit.get("path") == item["path"]:
                lines.append(f"  CONFIRM {finding['rule_id']} [{finding.get('severity')}] rewrite={finding.get('rewrite')!r}")
        if apply_preview:
            skipped: list[str] = []
            preview = _preview_document(
                out,
                str(item["path"]),
                [f for f in findings if units.get(str(f.get("unit_id")), {}).get("path") == item["path"]],
                units,
                skipped,
            )
            lines.append(f"preview: {preview}")
            lines.extend(f"preview skipped: {reason}" for reason in skipped)
    return "\n".join(lines)


__all__ = ["compare", "finish", "prepare"]
