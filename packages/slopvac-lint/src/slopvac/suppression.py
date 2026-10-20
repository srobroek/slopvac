"""The annotation contract: allow, disable-next-line, and disable/enable blocks.

Vale has no notion of these comments. A suppression must name an exception from
the named rule's own closed list; an unknown rule id is reported, a real-but-inactive
rule is silent, and a missing or unlisted reason is reported rather than honoured.
This lives apart from the engine so the scan and the honouring predicate can be
tested and reused without pulling in rule execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import regex as re

from .enums import Severity
from .model import Finding, Rule

if TYPE_CHECKING:
    from .analyze import Document

SUPPRESSION = re.compile(
    r"<!--\s*slopvac-allow:\s*rule=(?P<rule>[\w.-]+)(?:\s+reason=(?P<reason>[\w-]+))?\s*-->"
)
SUPPRESSION_ATTEMPT = re.compile(r"<!--\s*slopvac-allow\b")
DISABLE_LINE = re.compile(r"<!--\s*slopvac-disable-next-line\s*-->")
DISABLE_START = re.compile(r"<!--\s*slopvac-disable\s*-->")
DISABLE_END = re.compile(r"<!--\s*slopvac-enable\s*-->")

# The written forms the patterns above parse. `explain`, the prime guides, and the
# rules reference print these, so the documented grammar is the parsed grammar.
DISABLE_NEXT_LINE_COMMENT = "<!-- slopvac-disable-next-line -->"
DISABLE_COMMENT = "<!-- slopvac-disable -->"
ENABLE_COMMENT = "<!-- slopvac-enable -->"


def allow_comment(rule_id: str, reason: str) -> str:
    """The allow annotation for one rule and one of its named exceptions."""
    return f"<!-- slopvac-allow: rule={rule_id} reason={reason} -->"


# A directive quoted in a code span is documentation of the directive, not a
# directive: the README and the skills show the grammar in backticks, and treating
# those as written made the project's own docs fail their gate, while a quoted
# `<!-- slopvac-disable -->` silenced the rest of the file. A span may close on a
# later source line, so the open backtick runs are carried from line to line within
# a block (a blank line or a code block ends every span).
_BACKTICK_RUN = re.compile(r"`+")


def _runs_toggled(open_runs: set[int], text: str, end: int | None = None) -> set[int]:
    """The open backtick runs after reading `text` up to `end`."""
    state = set(open_runs)
    for run in _BACKTICK_RUN.finditer(text, 0, len(text) if end is None else end):
        state ^= {len(run.group(0))}
    return state


def _written(open_runs: set[int], line: str, match) -> bool:
    """Is this directive written in prose, rather than quoted inside a code span?"""
    return not _runs_toggled(open_runs, line, match.start())


@dataclass
class Suppression:
    rule: str
    reason: str | None
    line: int


def annotation_targets(raw_lines: list[str], annotation_line: int) -> list[int]:
    """The line numbers one annotation on `annotation_line` applies to.

    Blank lines and further annotations are skipped, so an annotation reaches
    the next line that can carry a finding. When that line opens a markdown
    table, every row of the table is a target.
    """
    index = annotation_line  # 0-based index of the line AFTER the annotation
    while index < len(raw_lines):
        stripped = raw_lines[index].strip()
        if stripped and not stripped.startswith("<!--"):
            break
        index += 1
    else:
        return []

    first = index + 1
    if not raw_lines[index].lstrip().startswith("|"):
        return [first]

    last = index
    while last + 1 < len(raw_lines) and raw_lines[last + 1].lstrip().startswith("|"):
        last += 1
    return list(range(first, last + 2))


def _expand_block_targets(
    document: Document, targets: list[int], annotation_line: int
) -> list[int]:
    """Apply one annotation to every physical line in its following block."""
    same_line = [
        block
        for block in document.blocks
        if block.lines[0] == annotation_line
        and block.kind.value not in {"code", "front_matter"}
    ]
    if same_line:
        return sorted(
            line
            for block in same_line
            for line in range(block.lines[0], block.lines[1] + 1)
        )
    expanded = set(targets)
    for block in document.blocks:
        if block.kind.value in {"code", "front_matter"}:
            continue
        if block.lines[0] in expanded:
            expanded.update(range(block.lines[0], block.lines[1] + 1))
    return sorted(expanded)


# In code-comment mode the document is a projection that keeps only the comments,
# and its markdown blocks are not what a reader sees: a `#` comment parses as a
# heading and an indented comment as a code block, so a directive covered its own
# line, or was read as quoted text. A directive there scopes to comment blocks: runs
# of consecutive lines that carry comment text. A blank line, a code line, an empty
# comment line, and a comment line that holds only directives end a run, as a blank
# line or an HTML comment ends a paragraph.
_INLINE_HTML_COMMENT = re.compile(r"<!--.*?-->")
_WORD = re.compile(r"\w")


def comment_blocks(raw_lines: list[str]) -> list[tuple[int, int]]:
    """The first and last line number of each comment block in a comment projection."""
    blocks: list[tuple[int, int]] = []
    first: int | None = None
    for number, line in enumerate(raw_lines, 1):
        if _WORD.search(_INLINE_HTML_COMMENT.sub("", line)):
            if first is None:
                first = number
        elif first is not None:
            blocks.append((first, number - 1))
            first = None
    if first is not None:
        blocks.append((first, len(raw_lines)))
    return blocks


def _comment_block_targets(
    blocks: list[tuple[int, int]], annotation_line: int
) -> list[int]:
    """The comment block one directive covers, by the rule a paragraph follows.

    The block that starts on the directive's line, else the block that holds the
    next line with comment text.
    """
    for first, last in blocks:
        if first == annotation_line or last > annotation_line:
            return list(range(first, last + 1))
    return []


def scan_suppressions(
    document: Document,
    rules_by_id: dict[str, Rule],
    active: set[str] | None = None,
    *,
    comments: bool = False,
) -> tuple[dict[int, list[Suppression]], set[int], list[Finding]]:
    """Collect annotations from the RAW lines.

    Raw, not prose: the parser blanks HTML comments so they are not linted,
    which means the annotations are only visible here. A valid annotation on the
    line before a block (or on its first line) covers that whole block, so a
    finding on a wrapped later line remains suppressible. With `comments`, the
    document is a comment projection and the blocks are its comment blocks.

    `active` names the rules whose reasons are checked: every rule the run's config
    turns on, whichever engine runs it. Left as None, every rule in `rules_by_id`.
    """
    by_line: dict[int, list[Suppression]] = {}
    disabled: set[int] = set()
    invalid: list[Finding] = []
    block_disabled = False
    live = active if active is not None else set(rules_by_id)

    def invalid_finding(line: int, column: int, directive: str, message: str) -> None:
        # Located like any finding, so a diff scope can place it on its line.
        invalid.append(
            Finding(
                path=document.path,
                line=line,
                column=column + 1,
                end_column=column + 1 + len(directive),
                rule_id="meta.invalid-suppression",
                category="meta",
                severity=Severity.ERROR,
                message=message,
                matched_text=directive,
            )
        )

    # A marker inside a fenced block or front matter is quoted, not written: it
    # must neither disable the prose after the fence nor report as malformed.
    quoted_lines: set[int] = set()
    if comments:
        blocks = comment_blocks(document.raw_lines)

        def targets_for(number: int) -> list[int]:
            return _comment_block_targets(blocks, number)

    else:
        for block in document.blocks:
            if block.kind.value in ("code", "front_matter"):
                quoted_lines.update(range(block.lines[0], block.lines[1] + 1))

        def targets_for(number: int) -> list[int]:
            return _expand_block_targets(
                document, annotation_targets(document.raw_lines, number), number
            )

    open_runs: set[int] = set()
    for index, line in enumerate(document.raw_lines):
        number = index + 1
        if number in quoted_lines or not line.strip():
            open_runs = set()
            if block_disabled:
                disabled.add(number)
            continue
        start = DISABLE_START.search(line)
        if start and _written(open_runs, line, start):
            block_disabled = True
        end = DISABLE_END.search(line)
        if end and _written(open_runs, line, end):
            block_disabled = False
        if block_disabled:
            disabled.add(number)
        next_line = DISABLE_LINE.search(line)
        if next_line and _written(open_runs, line, next_line):
            disabled.update(targets_for(number))

        attempts = [
            attempt
            for attempt in SUPPRESSION_ATTEMPT.finditer(line)
            if _written(open_runs, line, attempt)
        ]
        open_runs = _runs_toggled(open_runs, line)
        for attempt in attempts:
            close = line.find("-->", attempt.start())
            raw_annotation = line[
                attempt.start() : close + 3 if close >= 0 else None
            ].strip()
            match = SUPPRESSION.fullmatch(raw_annotation)
            if match is None:
                invalid_finding(
                    number,
                    attempt.start(),
                    raw_annotation,
                    "invalid suppression; expected "
                    "<!-- slopvac-allow: rule=<rule-id> reason=<reason> -->.",
                )
                continue

            rule_id = match.group("rule")
            reason = match.group("reason")
            for target in targets_for(number):
                by_line.setdefault(target, []).append(
                    Suppression(rule=rule_id, reason=reason, line=number)
                )

            rule = rules_by_id.get(rule_id)
            if rule is None:
                invalid_finding(
                    number,
                    attempt.start(),
                    raw_annotation,
                    f"suppression names unknown rule {rule_id}.",
                )
                continue
            if rule.qualified_id not in live:
                continue
            if reason is None:
                invalid_finding(
                    number,
                    attempt.start(),
                    raw_annotation,
                    f"suppression of {rule_id} names no reason. "
                    f"Add reason=<one of: {', '.join(rule.exceptions) or 'none defined'}>.",
                )
            elif reason not in rule.exceptions:
                invalid_finding(
                    number,
                    attempt.start(),
                    raw_annotation,
                    f'reason "{reason}" is not an exception of {rule_id}. '
                    f"Valid: {', '.join(rule.exceptions) or 'none defined'}.",
                )
    return by_line, disabled, invalid


def is_suppressed(
    rule: Rule,
    line: int,
    suppressions: dict[int, list[Suppression]],
    disabled: set[int],
) -> bool:
    """Whether a finding on `line` for `rule` is covered by an annotation."""
    if line in disabled:
        return True
    for entry in suppressions.get(line, []):
        if entry.rule != rule.qualified_id:
            continue
        if entry.reason is None:
            continue  # malformed; already reported, does not suppress
        if entry.reason not in rule.exceptions:
            continue  # invalid; already reported, does not suppress
        return True
    return False
