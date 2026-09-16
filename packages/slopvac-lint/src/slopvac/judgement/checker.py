"""Mechanical fact-preservation checks for judgement rewrites."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

ViolationKind = Literal["removed", "altered", "added_unauthorised"]


@dataclass(frozen=True)
class Violation:
    token_class: str
    kind: ViolationKind
    before: str | None
    after: str | None
    position: int | None


@dataclass(frozen=True)
class CheckerResult:
    ok: bool
    violations: tuple[Violation, ...]


@dataclass(frozen=True)
class _Token:
    text: str
    start: int
    end: int


_CLASSES = (
    "code_and_identifiers",
    "cross_reference_target",
    "defined_terms",
    "modality",
    "named_entities",
    "negation_polarity",
    "numerals_units_versions_dates",
    "procedure_dependency",
)

# Deliberately small and explicit: these are the repository's steering words,
# RFC 2119 words, and the safety signals used by its rules.
_MODALITY = {
    "MUST", "MUST NOT", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT",
    "MAY", "OPTIONAL", "REQUIRED", "DEFAULT", "NOT", "NEVER", "AVOID",
    "DANGER", "WARNING", "CAUTION", "NOTE",
}
_NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
)
_NUM_WORD_RE = "|".join(_NUMBER_WORDS)


def _tokens(pattern: str, text: str) -> list[_Token]:
    return [_Token(m.group(0), m.start(), m.end()) for m in re.finditer(pattern, text, re.I)]


def _extract(text: str, defined_terms: Sequence[str]) -> dict[str, list[_Token]]:
    result = {name: [] for name in _CLASSES}
    occupied: set[tuple[int, int]] = set()

    def add(name: str, pattern: str, *, flags: int = re.I) -> None:
        for m in re.finditer(pattern, text, flags):
            key = (m.start(), m.end())
            if key in occupied:
                continue
            result[name].append(_Token(m.group(0), m.start(), m.end()))
            occupied.add(key)

    # A code span is one indivisible specimen. The remaining forms cover the
    # common non-span forms emitted by documentation and command examples.
    add("code_and_identifiers", r"`[^`\n]+`")
    add("code_and_identifiers", r"https?://[^\s)\]}>]+")
    add("code_and_identifiers", r"\{\{[^{}\n]+\}\}|\$\{[^{}\n]+\}|<[A-Z][A-Z0-9_ -]+>")
    add("code_and_identifiers", r"(?<!\w)--?[A-Za-z][A-Za-z0-9_-]*")
    add("code_and_identifiers", r"(?<!\w)(?:/[A-Za-z0-9_.~-]+)+(?:/[A-Za-z0-9_.~-]*)?")
    add("code_and_identifiers", r"(?<!\w)\$[A-Za-z_][A-Za-z0-9_]*")

    # Dates, versions, numbers and their immediately attached units are kept
    # as occurrences so a unit cannot silently disappear during rewriting.
    add(
        "numerals_units_versions_dates",
        rf"\b(?:\d{{4}}[-/]\d{{1,2}}[-/]\d{{1,2}}|\d{{1,2}}[-/]\d{{1,2}}[-/]\d{{2,4}}|v?\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.-]+)?|\d+(?:\.\d+)?\s*(?:%|percent|ms|s|sec|seconds?|minutes?|hours?|days?|px|MB|GB|KB)|(?:{_NUM_WORD_RE})(?:\s+(?:percent|ms|s|sec|seconds?|minutes?|hours?|days?))?|\d+(?:\.\d+)?%)\b"
    )

    # Uppercase-only matching is intentional; lowercase prose "note" is not
    # an RFC/ste modality marker.
    modality_pattern = r"\b(?:MUST\s+NOT|SHOULD\s+NOT|SHALL\s+NOT|MUST|SHALL|SHOULD|MAY|OPTIONAL|REQUIRED|DEFAULT|NOT|NEVER|AVOID|DANGER|WARNING|CAUTION|NOTE)\b"
    add("modality", modality_pattern, flags=0)

    add("negation_polarity", r"\b(?:not|no|never|without|unless|except)\b")
    add("negation_polarity", r"\b(?:un|non)-?[A-Za-z][A-Za-z0-9-]*\b")

    # Explicit configured terms are the only vocabulary treated as defined.
    for term in sorted(set(defined_terms), key=len, reverse=True):
        if term:
            add("defined_terms", rf"(?<!\w){re.escape(term)}(?!\w)")

    # Capitalised multi-word names are a deliberately conservative heuristic.
    add("named_entities", r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", flags=0)

    add("cross_reference_target", r"(?i:\b(?:section|chapter|figure|fig\.?|table)\s+\d+[A-Za-z]?(?:\.\d+)*|#[A-Za-z][\w-]*)")
    # An explicit Step marker is a procedure occurrence; lowercase references
    # above remain cross-reference targets.
    add("procedure_dependency", r"\bStep\s+\d+[A-Za-z]?(?:\s*[:.)-])?", flags=re.I)
    add("procedure_dependency", r"\b(?:if|when|before|after)\s+[^,.;:\n]+", flags=re.I)

    for values in result.values():
        values.sort(key=lambda token: token.start)
    return result


def _normalise(token: str, token_class: str) -> str:
    value = token.strip().strip("`\"'“”‘’")
    if token_class == "numerals_units_versions_dates":
        words = {word: str(index) for index, word in enumerate(_NUMBER_WORDS)}
        value = re.sub(rf"\b({'|'.join(words)})\b", lambda m: words[m.group(1).lower()], value, flags=re.I)
    if token_class == "code_and_identifiers":
        return value
    # Unicode punctuation and ordinary case are typed normalisations, not
    # factual changes, for every protected textual occurrence.
    value = value.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "‐": "-", "‑": "-", "–": "-", "—": "-"}))
    return value.casefold()


def _authorised_quote(token: str, referent_quotes: Sequence[str]) -> bool:
    return any(token in quote for quote in referent_quotes)


def check_rewrite(
    unit_text: str,
    rewrite: str,
    *,
    document_text: str,
    referent_quotes: Sequence[str] = (),
    allowed_transitions: Sequence[Mapping[str, str]] = (),
    rule_id: str,
    defined_terms: Sequence[str] = (),
) -> CheckerResult:
    """Compare protected occurrences, refusing omissions and unauthorised additions.

    ``document_text`` is intentionally accepted for interface compatibility but
    never consulted for authorisation: only source normalisation, referent
    quotes, and exact rule transitions can authorise a new occurrence.
    """
    del document_text, rule_id
    before = _extract(unit_text, defined_terms)
    after = _extract(rewrite, defined_terms)
    violations: list[Violation] = []

    for token_class in _CLASSES:
        old = before[token_class]
        new = after[token_class]
        shared = min(len(old), len(new))
        for index in range(shared):
            left, right = old[index], new[index]
            if left.text == right.text or _normalise(left.text, token_class) == _normalise(right.text, token_class):
                continue
            if any(
                row.get("class", row.get("token_class")) == token_class
                and row.get("from") == left.text
                and row.get("to") == right.text
                for row in allowed_transitions
            ):
                continue
            violations.append(Violation(token_class, "altered", left.text, right.text, right.start))

        for left in old[shared:]:
            violations.append(Violation(token_class, "removed", left.text, None, left.start))
        for right in new[shared:]:
            if not _authorised_quote(right.text, referent_quotes):
                violations.append(Violation(token_class, "added_unauthorised", None, right.text, right.start))

    return CheckerResult(not violations, tuple(violations))
