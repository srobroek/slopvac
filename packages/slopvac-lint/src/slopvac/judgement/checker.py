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
    attempted_rewrite: str = ""

    @property
    def rewrite(self) -> str:
        """Compatibility alias for hosts that call the proposal ``rewrite``."""
        return self.attempted_rewrite


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
    "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand", "million", "billion", "trillion",
)
_NUM_WORD_RE = "|".join(_NUMBER_WORDS)
_NUMBER_VALUES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# A prefix is a polarity marker only when the whole form is known to be a
# negated lexical item, or when its stem is explicitly present in the paired
# unit.  This keeps ordinary words such as ``unit``, ``under``, and ``none``
# out of the polarity class.
_NEGATED_FORMS = frozenset({
    "unambiguous", "unavailable", "uncertain", "unclear", "unconfirmed",
    "undefined", "unchecked", "unintended", "unknown", "unmaintained",
    "unnecessary", "unprotected", "unreadable", "unreliable", "unresolved",
    "unsafe", "unsupported", "untested", "untrusted", "untrue", "unusual",
    "unverified", "unmodified", "unapproved", "noncompliant", "nonconforming",
    "nonexistent", "nonnegative", "nonstandard", "nondeterministic", "nonempty",
    "nonzero",
})
_NEGATION_WORDS = frozenset({"not", "no", "never", "without", "unless", "except"})

_KNOWN_UNITS = (
    "ms", "s", "sec", "secs", "second", "seconds", "min", "mins", "minute",
    "minutes", "hour", "hours", "day", "days", "px", "KB", "MB", "GB",
)
_KNOWN_UNIT_RE = "|".join(sorted(_KNOWN_UNITS, key=len, reverse=True))


def _word_values(text: str) -> set[str]:
    return {
        match.group(0).casefold()
        for match in re.finditer(r"(?<!\w)[A-Za-z]+(?:[-'][A-Za-z]+)*(?!\w)", text)
    }


def _paired_negated_stems(unit_text: str, rewrite: str) -> set[str]:
    """Return prefix stems proven by the paired unit, plus known lexical forms."""
    unit_words = _word_values(unit_text)
    rewrite_words = _word_values(rewrite)
    stems: set[str] = set()
    for word in unit_words | rewrite_words:
        for prefix in ("un", "non"):
            if not word.startswith(prefix):
                continue
            stem = word[len(prefix):].lstrip("-")
            if len(stem) >= 3 and stem in (unit_words | rewrite_words):
                stems.add(stem)
    return stems


def _tokens(pattern: str, text: str, *, flags: int = re.I) -> list[_Token]:
    return [_Token(m.group(0), m.start(), m.end()) for m in re.finditer(pattern, text, flags)]


def _extract(
    text: str,
    defined_terms: Sequence[str],
    *,
    negated_stems: set[str] = frozenset(),
) -> dict[str, list[_Token]]:
    result = {name: [] for name in _CLASSES}
    occupied: list[tuple[int, int]] = []

    def add(
        name: str,
        pattern: str,
        *,
        flags: int = re.I,
        allow_overlap: bool = False,
    ) -> None:
        for m in re.finditer(pattern, text, flags):
            key = (m.start(), m.end())
            if not allow_overlap and any(
                key[0] < end and key[1] > start for start, end in occupied
            ):
                continue
            result[name].append(_Token(m.group(0), m.start(), m.end()))
            if not allow_overlap:
                occupied.append(key)

    # A code span is one indivisible specimen. The remaining forms cover the
    # common non-span forms emitted by documentation and command examples.
    add("code_and_identifiers", r"`[^`\n]+`")
    add("code_and_identifiers", r"https?://[^\s)\]}>]+")
    add("code_and_identifiers", r"\{\{[^{}\n]+\}\}|\$\{[^{}\n]+\}|<[A-Z][A-Z0-9_ -]+>")
    add("code_and_identifiers", r"(?<!\w)--?[A-Za-z][A-Za-z0-9_-]*")
    add("code_and_identifiers", r"(?<!\w)(?:/[A-Za-z0-9_.~-]+)+(?:/[A-Za-z0-9_.~-]*)?")
    add("code_and_identifiers", r"(?<!\w)\$[A-Za-z_][A-Za-z0-9_]*")

    # A reference is kept as one fact; its embedded numeral must not become a
    # second, independently paired occurrence.
    add(
        "cross_reference_target",
        r"(?i:\b(?:section|chapter|figure|fig\.?|table)\s+\d+[A-Za-z]?(?:\.\d+)*|#[A-Za-z][\w-]*)",
    )

    # Dates and versions take precedence over the broad numeral matcher below.
    add(
        "numerals_units_versions_dates",
        r"(?<!\w)(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|v?\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.-]+)?)(?!\w)",
    )
    add(
        "numerals_units_versions_dates",
        rf"(?<!\w)\d+(?:[.,]\d+)?\s*(?:%|percent|{_KNOWN_UNIT_RE})(?!\w)",
    )
    add(
        "numerals_units_versions_dates",
        rf"(?<!\w)(?:{_NUM_WORD_RE})(?:[ -]+(?:{_NUM_WORD_RE}))*(?:\s+(?:percent|{_KNOWN_UNIT_RE}))?(?!\w)",
    )
    # Every remaining digit token is protected, including an unadorned ``42``
    # and a percentage (where a trailing ``\b`` would fail after ``%``).
    add("numerals_units_versions_dates", r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)")

    # Uppercase-only matching is intentional; lowercase prose "note" is not
    # an RFC/STE modality marker.
    modality_pattern = r"\b(?:MUST\s+NOT|SHOULD\s+NOT|SHALL\s+NOT|MUST|SHALL|SHOULD|MAY|OPTIONAL|REQUIRED|DEFAULT|NOT|NEVER|AVOID|DANGER|WARNING|CAUTION|NOTE)\b"
    add("modality", modality_pattern, flags=0)

    add("negation_polarity", r"(?<!\w)(?:not|no|never|without|unless|except)(?!\w)")
    for token in _tokens(r"(?<!\w)[A-Za-z]+(?:-[A-Za-z]+)*(?!\w)", text):
        value = token.text.casefold()
        if value in _NEGATED_FORMS:
            result["negation_polarity"].append(token)
            continue
        if value.startswith(("un", "non")):
            stem = value[2:].lstrip("-")
            if len(stem) >= 3 and stem in negated_stems:
                result["negation_polarity"].append(token)

    # Explicit configured terms are the only vocabulary treated as defined.
    for term in sorted(set(defined_terms), key=len, reverse=True):
        if term:
            add("defined_terms", rf"(?<!\w){re.escape(term)}(?!\w)")

    # Capitalised multi-word names are a deliberately conservative heuristic.
    add("named_entities", r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", flags=0)
    # Product/API names are often one token (for example ``OpenAI``). They are
    # configured rather than guessed, so protect them even without title case.
    for term in sorted(set(defined_terms), key=len, reverse=True):
        if term and not re.search(r"\s", term):
            add("named_entities", rf"(?<!\w){re.escape(term)}(?!\w)")

    # Procedure facts are deliberately located by sentence. The order marker
    # is a single fact, while each condition retains the command it governs;
    # class occurrence indexes alone cannot express either relationship.
    step_matches = list(re.finditer(r"\bStep\s+(\d+[A-Za-z]?)", text, re.I))
    if step_matches:
        order = ">".join(match.group(1).casefold() for match in step_matches)
        result["procedure_dependency"].append(
            _Token(f"step-order:{order}", step_matches[0].start(), step_matches[-1].end())
        )
    for sentence in re.finditer(r"[^.!?\n]+(?:[.!?]|$)", text):
        source = sentence.group(0)
        condition = re.search(
            r"\b(if|when|unless|provided\s+that|before|after)\b\s+([^,;:.!?]+)",
            source,
            re.I,
        )
        if condition is None:
            continue
        command = source[condition.end():].strip(" ,:-\t.!?")
        if not command:
            command = source[:condition.start()].strip(" ,:-\t.!?")
        if not command:
            continue
        start = sentence.start() + condition.start()
        result["procedure_dependency"].append(
            _Token(
                f"{condition.group(1).casefold()}:{condition.group(2).strip()}->{command.strip()}",
                start,
                sentence.end(),
            )
        )

    for values in result.values():
        values.sort(key=lambda token: token.start)
    return result


def _number_words_to_int(words: str) -> int | None:
    values = re.split(r"[ -]+", words.casefold())
    if not values or any(value not in _NUMBER_WORDS for value in values):
        return None
    total = 0
    current = 0
    for value in values:
        if value in _NUMBER_VALUES:
            current += _NUMBER_VALUES[value]
        elif value == "hundred":
            current = max(current, 1) * 100
        else:
            scale = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000, "trillion": 1_000_000_000_000}[value]
            total += current * scale
            current = 0
    return total + current


def _normalise_number_words(value: str) -> str:
    pattern = rf"(?<!\w)(?:{_NUM_WORD_RE})(?:[ -]+(?:{_NUM_WORD_RE}))*(?!\w)"

    def replace(match: re.Match[str]) -> str:
        parsed = _number_words_to_int(match.group(0))
        return str(parsed) if parsed is not None else match.group(0)

    return re.sub(pattern, replace, value, flags=re.I)


def _normalise_date_formats(value: str) -> str:
    pattern = re.compile(
        r"(?<!\w)(?:(\d{4})[-/](\d{1,2})[-/](\d{1,2})|(\d{1,2})[-/](\d{1,2})[-/](\d{4}))(?!\w)"
    )

    def replace(match: re.Match[str]) -> str:
        if match.group(1) is not None:
            year, month, day = match.group(1), match.group(2), match.group(3)
        else:
            day, month, year = match.group(4), match.group(5), match.group(6)
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"

    return pattern.sub(replace, value)

def _normalise(token: str, token_class: str) -> str:
    value = token.strip().strip("`\"'“”‘’")
    if token_class == "numerals_units_versions_dates":
        value = _normalise_number_words(value)
        value = _normalise_date_formats(value)
        value = re.sub(r"(?i)^v(?=\d)", "", value)
        value = value.replace(",", ".").replace("%", " percent")
        value = re.sub(r"\s+", " ", value)
        return value
    if token_class == "code_and_identifiers":
        return value
    # Unicode punctuation and ordinary case are typed normalisations, not
    # factual changes, for every protected textual occurrence.
    value = value.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "‐": "-", "‑": "-", "–": "-", "—": "-"}))
    return value.casefold()


def _authorised_quote(token: str, referent_quotes: Sequence[str]) -> bool:
    value = token.strip().strip("`\"'“”‘’")
    if not value:
        return False
    pattern = rf"(?<!\w){re.escape(value)}(?!\w)"
    return any(re.search(pattern, quote, re.I) is not None for quote in referent_quotes)


def _transition_allowed(
    token_class: str,
    before: str,
    after: str,
    allowed_transitions: Sequence[Mapping[str, str]],
) -> bool:
    return any(
        row.get("class", row.get("token_class")) == token_class
        and row.get("from", row.get("src")) == before
        and row.get("to", row.get("dst")) == after
        for row in allowed_transitions
    )


def _pair_tokens(
    old: Sequence[_Token],
    new: Sequence[_Token],
    token_class: str,
    allowed_transitions: Sequence[Mapping[str, str]],
) -> tuple[list[tuple[_Token, _Token]], list[_Token], list[_Token]]:
    """Align unchanged/allowed occurrences before classifying edits."""
    pairs: list[tuple[_Token, _Token]] = []
    unmatched_old: list[_Token] = []
    unmatched_new: list[_Token] = []
    cursor = 0
    for left in old:
        candidate_index = next(
            (
                index
                for index in range(cursor, len(new))
                if _normalise(left.text, token_class) == _normalise(new[index].text, token_class)
                or _transition_allowed(token_class, left.text, new[index].text, allowed_transitions)
            ),
            None,
        )
        if candidate_index is None:
            unmatched_old.append(left)
            continue
        unmatched_new.extend(new[cursor:candidate_index])
        pairs.append((left, new[candidate_index]))
        cursor = candidate_index + 1
    unmatched_new.extend(new[cursor:])
    return pairs, unmatched_old, unmatched_new


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

    ``document_text`` and ``rule_id`` are accepted for interface compatibility;
    presence elsewhere in a document is deliberately not authorisation. Only a
    source occurrence, an exact referent quote, or an exact rule transition can
    authorise a protected rewrite.
    """
    del document_text, rule_id
    negated_stems = _paired_negated_stems(unit_text, rewrite)
    before = _extract(unit_text, defined_terms, negated_stems=negated_stems)
    after = _extract(rewrite, defined_terms, negated_stems=negated_stems)
    violations: list[Violation] = []

    for token_class in _CLASSES:
        old = before[token_class]
        new = after[token_class]
        pairs, unmatched_old, unmatched_new = _pair_tokens(
            old, new, token_class, allowed_transitions
        )
        for left, right in pairs:
            if _normalise(left.text, token_class) == _normalise(right.text, token_class):
                continue
            if _transition_allowed(token_class, left.text, right.text, allowed_transitions):
                continue
            violations.append(Violation(token_class, "altered", left.text, right.text, right.start))
        for left, right in zip(unmatched_old, unmatched_new, strict=False):
            if _normalise(left.text, token_class) == _normalise(right.text, token_class):
                continue
            if _transition_allowed(token_class, left.text, right.text, allowed_transitions):
                continue
            violations.append(Violation(token_class, "altered", left.text, right.text, right.start))
        for left in unmatched_old[len(unmatched_new):]:
            violations.append(Violation(token_class, "removed", left.text, None, left.start))
        for right in unmatched_new[len(unmatched_old):]:
            if not _authorised_quote(right.text, referent_quotes):
                violations.append(Violation(token_class, "added_unauthorised", None, right.text, right.start))

    return CheckerResult(not violations, tuple(violations), rewrite)
