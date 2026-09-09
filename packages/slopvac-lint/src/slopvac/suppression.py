"""The annotation contract: allow, disable-next-line, and disable/enable blocks.

Vale has no notion of these comments. A suppression must name an exception from
the named rule's own closed list; an unknown rule id is reported, a real-but-inactive
rule is silent, and a missing or unlisted reason is reported rather than honoured.
This lives apart from the engine so the scan and the honouring predicate can be
tested and reused without pulling in rule execution.
"""

from __future__ import annotations

from dataclasses import dataclass

import regex as re

from .analyze import Document
from .config import Severity
from .model import Finding, Rule

SUPPRESSION = re.compile(
    r"<!--\s*slopvac-allow:\s*rule=(?P<rule>[\w.-]+)(?:\s+reason=(?P<reason>[\w-]+))?\s*-->"
)
DISABLE_LINE = re.compile(r"<!--\s*slopvac-disable-next-line\s*-->")
DISABLE_START = re.compile(r"<!--\s*slopvac-disable\s*-->")
DISABLE_END = re.compile(r"<!--\s*slopvac-enable\s*-->")


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


def scan_suppressions(
    document: Document,
    rules_by_id: dict[str, Rule],
    active: set[str] | None = None,
) -> tuple[dict[int, list[Suppression]], set[int], list[Finding]]:
    """Collect annotations from the RAW lines.

    Raw, not prose: the parser blanks HTML comments so they are not linted,
    which means the annotations are only visible here.

    `rules_by_id` is the full catalog. `active` is the qualified ids that run in
    this profile; a real-but-inactive rule is accepted silently. An empty
    exception list accepts nothing.
    """
    by_line: dict[int, list[Suppression]] = {}
    disabled: set[int] = set()
    invalid: list[Finding] = []
    block_disabled = False
    live = active if active is not None else set(rules_by_id)

    for index, line in enumerate(document.raw_lines):
        number = index + 1
        if DISABLE_START.search(line):
            block_disabled = True
        if DISABLE_END.search(line):
            block_disabled = False
        if block_disabled:
            disabled.add(number)
        if DISABLE_LINE.search(line):
            disabled.update(annotation_targets(document.raw_lines, number))

        for match in SUPPRESSION.finditer(line):
            rule_id = match.group("rule")
            reason = match.group("reason")
            # An annotation applies to the following line, matching the
            # disable-next-line convention readers already expect. "Following"
            # is the next line with content, not literally the next line: an
            # annotation is normally separated from a table or a fenced block
            # by a blank line, and targeting the blank one suppressed nothing.
            #
            # A TABLE IS ONE TARGET. CommonMark ends a table at any HTML block,
            # so an annotation cannot be put on the row it applies to -- the
            # comment splits the table and every row below it reports as one
            # paragraph instead. An annotation above the table therefore covers
            # the whole table, which is also the only granularity a writer can
            # express.
            for target in annotation_targets(document.raw_lines, number):
                by_line.setdefault(target, []).append(
                    Suppression(rule=rule_id, reason=reason, line=number)
                )

            rule = rules_by_id.get(rule_id)
            if rule is None:
                invalid.append(
                    Finding(
                        path=document.path,
                        line=number,
                        rule_id="meta.invalid-suppression",
                        category="meta",
                        severity=Severity.ERROR,
                        message=f"suppression names unknown rule {rule_id}.",
                    )
                )
                continue
            if rule.qualified_id not in live:
                continue  # real rule, off in this profile; nothing to validate
            if reason is None:
                invalid.append(
                    Finding(
                        path=document.path,
                        line=number,
                        rule_id="meta.invalid-suppression",
                        category="meta",
                        severity=Severity.ERROR,
                        message=(
                            f"suppression of {rule_id} names no reason. "
                            f"Add reason=<one of: {', '.join(rule.exceptions) or 'none defined'}>."
                        ),
                    )
                )
            elif reason not in rule.exceptions:
                invalid.append(
                    Finding(
                        path=document.path,
                        line=number,
                        rule_id="meta.invalid-suppression",
                        category="meta",
                        severity=Severity.ERROR,
                        message=(
                            f'reason "{reason}" is not an exception of {rule_id}. '
                            f"Valid: {', '.join(rule.exceptions) or 'none defined'}."
                        ),
                    )
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
