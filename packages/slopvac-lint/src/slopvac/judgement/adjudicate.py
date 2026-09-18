"""Host-side reconciliation of model judgements with deterministic gates."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .checker import Violation, check_rewrite
from .schema import validate_model_output

Outcome = Literal["DROP", "PRESERVE", "ABSTAIN", "REJECT", "CONFIRM"]
Severity = Literal["error", "warning", "suggestion"]
RewriteStatus = Literal[
    "not_applicable",
    "proposed",
    "withheld_needs_fact",
    "withheld_checker_veto",
]


@dataclass(frozen=True)
class EvidenceSpan:
    quote: str
    start: int
    end: int
    role: str
    source: str
    source_ref: str | None
    doc_start: int | None
    doc_end: int | None


@dataclass(frozen=True)
class FindingRecord:
    unit_id: str
    rule_id: str
    kind: Literal["SPAN_CANDIDATE", "PASSAGE_PROBE"]
    outcome: Outcome
    severity: Severity | None
    scores: dict[str, Any] | None
    evidence: tuple[EvidenceSpan, ...]
    preservation_reason: str | None
    abstain_reason: str | None
    rewrite: str | None
    rewrite_status: RewriteStatus
    core_fired: bool
    component_id: str | None
    source_sha256: str
    path: str
    instrument_id: str
    judgement_cache_key: str
    occurrence_index: int | None
    occurrences_truncated: bool = False
    attempted_rewrite: str | None = None
    checker_violations: tuple[Violation, ...] = ()


_WARRANT_CODES = {
    "none": 0,
    "quote_only": 1,
    "quote_plus_particular": 2,
    "two_locators": 3,
}
_SEVERITY_CODES = {"suggestion": 0, "warning": 1, "error": 2}
_SEVERITIES: tuple[Severity, ...] = ("suggestion", "warning", "error")


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _plain(value: Any) -> Any:
    return getattr(value, "value", value)


def _rule_contract(rule: Any) -> Any:
    contract = _value(rule, "judgement")
    if contract is None:
        raise ValueError("adjudicate requires a rule with a judgement contract")
    return contract


def _rule_id(rule: Any) -> str:
    return str(_value(rule, "qualified_id", _value(rule, "id", "")))


def _unit_kind(unit: Any) -> Literal["SPAN_CANDIDATE", "PASSAGE_PROBE"]:
    kind = str(_plain(_value(unit, "kind", "SPAN_CANDIDATE")))
    if kind not in {"SPAN_CANDIDATE", "PASSAGE_PROBE"}:
        raise ValueError(f"unknown judgement unit kind: {kind}")
    return kind  # type: ignore[return-value]


def _unit_id(unit: Any) -> str:
    return str(_value(unit, "unit_id", ""))


def _document_text(unit: Any) -> str:
    explicit = _value(unit, "document_text")
    if isinstance(explicit, str):
        return explicit
    projection = _value(unit, "projection")
    raw = _value(projection, "_raw")
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    if isinstance(raw, str):
        return raw
    return str(_value(unit, "text", ""))


def _context_candidates(unit: Any) -> list[Any]:
    values: list[Any] = []
    for name in ("context_blocks", "contexts", "context_units"):
        candidate = _value(unit, name)
        if candidate:
            values.extend(candidate if isinstance(candidate, (list, tuple)) else [candidate])
    context = _value(unit, "context")
    if context:
        values.extend(context if isinstance(context, (list, tuple)) else [context])
    return values


def _source_for_context(unit: Any, source_ref: str | None) -> tuple[str, Any, int, str] | None:
    candidates = _context_candidates(unit)
    if not candidates and isinstance(_value(unit, "context_text"), str):
        candidates = [unit]
    for candidate in candidates:
        if isinstance(candidate, str):
            base = _value(unit, "context_doc_range", (0, 0))
            base_start = int(base[0]) if isinstance(base, (tuple, list)) and base else 0
            return candidate, _value(unit, "context_projection"), base_start, str(source_ref or "")
        candidate_id = _value(candidate, "unit_id", _value(candidate, "id", None))
        if source_ref is not None and candidate_id is not None and str(candidate_id) != source_ref:
            continue
        text = _value(candidate, "text")
        if not isinstance(text, str) and candidate is unit:
            text = _value(unit, "context_text")
        if not isinstance(text, str):
            continue
        projection = _value(candidate, "projection", _value(unit, "context_projection"))
        base = _value(candidate, "doc_range", _value(unit, "context_doc_range", (0, 0)))
        base_start = int(base[0]) if isinstance(base, (tuple, list)) and base else 0
        return text, projection, base_start, str(candidate_id or source_ref or "")
    return None


def _repository_source(
    item: Mapping[str, Any], repository_lookup: Any,
) -> tuple[str, Any, int, str] | None:
    source_ref = item.get("source_ref")
    if not isinstance(source_ref, str) or "@" not in source_ref or repository_lookup is None:
        return None
    path, blob_sha = source_ref.rsplit("@", 1)
    try:
        text = repository_lookup(path, blob_sha)
    except (OSError, KeyError, LookupError):
        return None
    if not isinstance(text, str):
        return None
    return text, None, 0, source_ref


def _source_for_item(
    unit: Any, item: Mapping[str, Any], repository_lookup: Any,
) -> tuple[str, Any, int, str] | None:
    source = item.get("source")
    source_ref = item.get("source_ref")
    if source == "unit":
        text = _value(unit, "text", "")
        return (text, _value(unit, "projection"), int(_value(unit, "doc_range", (0, 0))[0]), _unit_id(unit))
    if source == "context":
        return _source_for_context(unit, str(source_ref) if source_ref is not None else None)
    if source == "repository":
        return _repository_source(item, repository_lookup)
    return None


def _validate_evidence(
    unit: Any, contract: Any, items: Any, repository_lookup: Any,
) -> tuple[bool, tuple[EvidenceSpan, ...], str | None]:
    if not isinstance(items, list):
        return False, (), "no_exact_evidence"
    evidence: list[EvidenceSpan] = []
    for raw in items:
        if not isinstance(raw, Mapping):
            return False, (), "no_exact_evidence"
        try:
            start = int(raw["start"])
            end = int(raw["end"])
            quote = raw["quote"]
            role = str(raw["role"])
            source = str(raw["source"])
        except (KeyError, TypeError, ValueError):
            return False, (), "no_exact_evidence"
        if start < 0 or end < start or not isinstance(quote, str) or not quote:
            return False, (), "no_exact_evidence"
        if role == "defect" and source != "unit":
            return False, (), "no_exact_evidence"
        resolved = _source_for_item(unit, raw, repository_lookup)
        if resolved is None:
            return False, (), "no_exact_evidence"
        text, projection, base_start, resolved_ref = resolved
        if end > len(text) or text[start:end] != quote:
            return False, (), "no_exact_evidence"
        if projection is not None:
            try:
                projection.to_raw(start)
                projection.to_raw(end)
            except (AttributeError, ValueError, TypeError):
                return False, (), "no_exact_evidence"
        doc_start = base_start + start if source != "repository" else None
        doc_end = base_start + end if source != "repository" else None
        evidence.append(EvidenceSpan(quote, start, end, role, source, raw.get("source_ref", resolved_ref), doc_start, doc_end))
    required = tuple(str(role) for role in _value(_value(contract, "evidence"), "roles", ()))
    min_arity = int(_value(_value(contract, "evidence"), "min_arity", 0))
    roles = {span.role for span in evidence}
    if len(evidence) < min_arity or not set(required).issubset(roles):
        return False, tuple(evidence), "no_exact_evidence"
    return True, tuple(evidence), None


def _record(
    unit: Any, rule: Any, *, outcome: Outcome, severity: Severity | None,
    scores: dict[str, Any] | None, evidence: tuple[EvidenceSpan, ...],
    preservation_reason: str | None, abstain_reason: str | None, rewrite: str | None,
    rewrite_status: RewriteStatus, instrument_id: str, cache_key: str,
    occurrence_index: int | None, occurrences_truncated: bool,
    attempted_rewrite: str | None = None,
    checker_violations: tuple[Violation, ...] = (),
) -> FindingRecord:
    return FindingRecord(
        unit_id=_unit_id(unit), rule_id=_rule_id(rule), kind=_unit_kind(unit),
        outcome=outcome, severity=severity, scores=scores, evidence=evidence,
        preservation_reason=preservation_reason, abstain_reason=abstain_reason,
        rewrite=rewrite, rewrite_status=rewrite_status,
        core_fired=bool(_value(unit, "core_fired", False)), component_id=None,
        source_sha256=str(_value(unit, "source_sha256", "")), path=str(_value(unit, "path", "")),
        instrument_id=instrument_id, judgement_cache_key=cache_key,
        occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated,
        attempted_rewrite=attempted_rewrite, checker_violations=checker_violations,
    )


def _demote(severity: Severity) -> Severity:
    return _SEVERITIES[max(0, _SEVERITY_CODES[severity] - 1)]


def _ceiling(contract: Any, rule: Any) -> Severity:
    names = [str(_plain(_value(contract, "judgement_ceiling", "suggestion")))]
    category = _value(rule, "category_ceiling", _value(rule, "severity"))
    if category is not None:
        names.append(str(_plain(category)))
    return min((name for name in names if name in _SEVERITY_CODES), key=_SEVERITY_CODES.__getitem__)  # type: ignore[return-value]


def _transition_rows(contract: Any) -> tuple[dict[str, str], ...]:
    table = _value(contract, "allowed_transitions")
    rows = _value(table, "rows", ()) if table is not None else ()
    return tuple({"class": str(_plain(_value(row, "token_class", _value(row, "class", "")))), "from": str(_plain(_value(row, "src", _value(row, "from", "")))), "to": str(_plain(_value(row, "dst", _value(row, "to", ""))))} for row in rows)


# Heading-echo material redundancy (root decision omp-plugins-q4bb.10). The rule fires on
# a heading whose first sentence only restates it; the measured false positives were plain
# section titles followed by a table cell or a list fragment. The three clauses below are
# that decision's, read over the antecedent heading and the defect sentence alone.
#
# Two readings the decision leaves to the implementation, both recorded here: the stop-word
# list is closed but unenumerated, so it is the function-word set below and is applied
# before stemming, in the decision's stated order; and the character tests for material
# ("contains a backtick, a `/`, or a `--flag`") read the raw token, because stripping token
# edges first would erase the very backtick they test for, while the file-name and normative
# tests read the edge-stripped form so a sentence-final `report.md.` still counts.
_HEADING_ECHO_STOP_WORDS = frozenset({
    "a", "about", "an", "and", "any", "are", "as", "at", "be", "been", "being", "both",
    "but", "by", "can", "do", "does", "each", "either", "for", "from", "had", "has",
    "have", "how", "if", "in", "into", "is", "it", "its", "may", "of", "on", "onto",
    "or", "our", "out", "over", "own", "same", "should", "so", "some", "such", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this", "those",
    "through", "to", "under", "up", "upon", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whose", "why", "will", "with", "within",
    "would", "you", "your",
})
_HEADING_ECHO_NORMATIVE = frozenset({
    "always", "cannot", "forbidden", "must", "neither", "never", "no", "none", "nor",
    "not", "only", "prohibited", "required", "shall",
})
_HEADING_ECHO_FILE_SUFFIXES = (
    ".py", ".md", ".json", ".jsonl", ".yml", ".yaml", ".toml", ".txt", ".sh", ".rs", ".ts", ".js",
)
_HEADING_ECHO_EDGES = "`./-"
_HEADING_ECHO_LINK = re.compile(r"\[[^\]]*\]\([^)]*\)")
_HEADING_ECHO_CODE_SPAN = re.compile(r"`[^`]+`")


def _heading_echo_fold(token: str) -> str:
    """Case-fold one whitespace token and strip the edge characters the decision names."""
    return token.casefold().strip(_HEADING_ECHO_EDGES)


def _heading_echo_stem(word: str) -> str:
    """Reduce a trailing `ing` on words longer than 4 and a trailing `s` on words longer than 3."""
    if len(word) > 4 and word.endswith("ing"):
        return word[:-3]
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _heading_echo_content_words(text: str) -> frozenset[str]:
    """Fold, strip edges, drop stop words, then stem -- the decision's order."""
    words = []
    for raw in text.split():
        token = _heading_echo_fold(raw)
        if not token or token in _HEADING_ECHO_STOP_WORDS:
            continue
        words.append(_heading_echo_stem(token))
    return frozenset(words)


def _heading_echo_material(text: str) -> frozenset[str]:
    """The decision's closed material set: figures, code, paths, flags, file names, links, normative words."""
    folded = text.casefold()
    material = set(_HEADING_ECHO_LINK.findall(folded))
    material.update(_HEADING_ECHO_CODE_SPAN.findall(folded))
    for raw in text.split():
        token = _heading_echo_fold(raw)
        if not token:
            continue
        if any(character.isdigit() for character in raw) or "`" in raw or "/" in raw or "--" in raw:
            material.add(token)
        elif token.endswith(_HEADING_ECHO_FILE_SUFFIXES) or token in _HEADING_ECHO_NORMATIVE:
            material.add(token)
    return frozenset(material)


def _heading_echo_is_sentence(sentence: str) -> bool:
    """Clause 1: one line, terminal punctuation, at least four whitespace-separated words."""
    stripped = sentence.strip()
    if not stripped or "\n" in stripped or not stripped.endswith((".", "!", "?")):
        return False
    return len(stripped.split()) >= 4


def _heading_echo_echoes(heading: str, sentence: str) -> bool:
    """Clause 2: the sentence repeats at least one normalised content word of the heading."""
    return bool(_heading_echo_content_words(heading) & _heading_echo_content_words(sentence))


def _heading_echo_adds_material(heading: str, sentence: str) -> bool:
    """Clause 3: the sentence carries a material token or span the heading does not."""
    return bool(_heading_echo_material(sentence) - _heading_echo_material(heading))


def _heading_echo_material_redundancy(heading: str, sentence: str) -> str | None:
    """Name the clause the pair fails, or None when all three hold and the finding is admitted."""
    if not _heading_echo_is_sentence(sentence):
        return "heading_echo_unit_not_a_sentence"
    if not _heading_echo_echoes(heading, sentence):
        return "heading_echo_no_lexical_echo"
    if _heading_echo_adds_material(heading, sentence):
        return "heading_echo_unit_adds_material"
    return None


def _host_predicate_outcome(unit: Any, predicate: Any, evidence: tuple[EvidenceSpan, ...], document_text: str) -> tuple[Outcome, str | None] | None:
    predicate_id = str(_plain(_value(predicate, "id", predicate)))
    referents = [span.quote for span in evidence if span.role == "referent"]
    if predicate_id == "no_short_form_in_document":
        if any(quote and quote in document_text for quote in referents):
            return "REJECT", None
    elif predicate_id == "figure_available" and not referents:
        return "ABSTAIN", "needs_repository_fact"
    elif predicate_id == "code_diff_available" and not any(span.source == "repository" for span in evidence):
        return "ABSTAIN", "needs_repository_fact"
    elif predicate_id == "heading_echo_material_redundancy":
        heading = next((span.quote for span in evidence if span.role == "antecedent" and span.quote.strip()), "")
        if not heading:
            return "ABSTAIN", "heading_echo_no_antecedent"
        sentence = next((span.quote for span in evidence if span.role == "defect"), "")
        # The caller's REJECT record carries no reason field, so the failing clause is named
        # by the helper alone; the tests assert the attribution on it directly.
        if _heading_echo_material_redundancy(heading, sentence) is not None:
            return "REJECT", None
    return None


def _defined_terms(unit: Any, rule: Any, contract: Any, explicit: Sequence[str] | None) -> tuple[str, ...]:
    """Resolve configured vocabulary, falling back to the contract's protected classes."""
    values: list[str] = []

    def collect(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            values.append(value)
            return
        if isinstance(value, Mapping):
            nested = value.get("defined_terms", value.get("terms", value.get("glossary")))
            if nested is not None:
                collect(nested)
                return
            values.extend(str(key) for key in value if isinstance(key, str))
            return
        if hasattr(value, "terms"):
            collect(value.terms)
            return
        if hasattr(value, "blocked") and callable(value.blocked):
            collect(value.blocked())
            return
        if isinstance(value, Sequence):
            for item in value:
                if isinstance(item, str):
                    values.append(item)
                else:
                    word = _value(item, "word")
                    if isinstance(word, str):
                        values.append(word)

    if explicit is not None:
        collect(explicit)
    for owner in (unit, rule, contract):
        for name in ("defined_terms", "glossary", "vocabulary"):
            collect(_value(owner, name))
    if not values:
        collect(_value(contract, "protects", ()))
    return tuple(dict.fromkeys(values))

def _one(
    unit: Any, rule: Any, model_output: Mapping[str, Any], *, instrument_id: str,
    cache_key: str, repository_lookup: Any, occurrence_index: int | None,
    occurrences_truncated: bool, defined_terms: Sequence[str],
) -> FindingRecord:
    contract = _rule_contract(rule)
    scores_raw = model_output.get("scores")
    scores = dict(scores_raw) if isinstance(scores_raw, Mapping) else None
    evidence_ok, evidence, evidence_reason = _validate_evidence(unit, contract, model_output.get("evidence"), repository_lookup)
    rewrite_status = str(model_output.get("rewrite_status", "not_applicable"))
    rewrite = model_output.get("rewrite") if isinstance(model_output.get("rewrite"), str) else None
    preservation_reason = model_output.get("preservation_reason")
    if preservation_reason is not None:
        preservation_reason = str(preservation_reason)
    abstain_reason = model_output.get("abstain_reason")
    if abstain_reason is not None:
        abstain_reason = str(abstain_reason)
    protected = {str(_plain(value)) for value in _value(contract, "protects", ())}
    adjudicates = _value(contract, "adjudicates")
    adjudicates = str(_plain(adjudicates)) if adjudicates is not None else None

    # Admission gates run in the contract's order. These are host facts, never model choices.
    origin = str(_value(unit, "origin", "authored"))
    if origin in {"generated", "vendored", "template"}:
        return _record(unit, rule, outcome="DROP", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
    scope = str(_plain(_value(rule, "scope", ""))).lower()
    if scope in {"document", "document_scope"} and _unit_kind(unit) == "SPAN_CANDIDATE":
        return _record(unit, rule, outcome="DROP", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
    text = _value(unit, "text", "")
    projection = _value(unit, "projection")
    if not isinstance(text, str) or not text or projection is None:
        return _record(unit, rule, outcome="DROP", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
    for name in ("admissible", "genre_admissible", "tier_eligible"):
        if _value(unit, name) is False:
            return _record(unit, rule, outcome="DROP", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)

    if _value(unit, "region_class") in {"quoted", "example"} and "quoted_specimen" in protected:
        preservation_reason = "quoted_specimen"

    fit = scores.get("fit") if scores else None
    harm = scores.get("harm") if scores else None
    repair = scores.get("repair") if scores else None
    warrant = scores.get("warrant") if scores else None
    model_verdict = str(model_output.get("verdict", "")).upper()
    reject_without_evidence = model_verdict == "REJECT" and fit in {"absent", "partial"}
    if preservation_reason in protected and preservation_reason != adjudicates:
        if not evidence_ok:
            return _record(unit, rule, outcome="ABSTAIN", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=evidence_reason or "no_exact_evidence", rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
        return _record(unit, rule, outcome="PRESERVE", severity=None, scores=scores, evidence=evidence, preservation_reason=preservation_reason, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)

    if (abstain_reason or evidence_reason or not evidence_ok) and not reject_without_evidence:
        return _record(unit, rule, outcome="ABSTAIN", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=abstain_reason or evidence_reason or "no_exact_evidence", rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
    if fit in {"absent", "partial"}:
        derived: Outcome = "REJECT"
    elif warrant not in _WARRANT_CODES or _WARRANT_CODES[warrant] < int(_value(contract, "warrant_min", 0)):
        derived = "REJECT"
    elif harm == "none" and repair != "safe_deletion" and _value(_value(contract, "dims"), "harm") != "inapplicable":
        derived = "REJECT"
    else:
        derived = "CONFIRM"
    if derived == "REJECT":
        model_verdict = str(model_output.get("verdict", "")).upper()
        if model_verdict != "REJECT":
            return _record(unit, rule, outcome="ABSTAIN", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason="inconsistent_output", rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
        return _record(unit, rule, outcome="REJECT", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)

    if _value(_value(contract, "dims"), "repair") == "inapplicable":
        rewrite_status = "not_applicable"
        rewrite = None
    severity: Severity = "error" if harm == "unsafe_or_normative" and fit == "unambiguous_match" else "warning" if harm == "misleads_or_blocks" and fit == "unambiguous_match" else "suggestion"
    if _value(_value(contract, "dims"), "harm") == "inapplicable":
        severity = "suggestion"
    severity = min((severity, _ceiling(contract, rule)), key=_SEVERITY_CODES.__getitem__)  # type: ignore[assignment]
    document_text = _document_text(unit)
    for predicate in _value(contract, "host_predicates", ()):
        host_result = _host_predicate_outcome(unit, predicate, evidence, document_text)
        if host_result is not None:
            host_outcome, host_reason = host_result
            if host_outcome == "ABSTAIN":
                return _record(unit, rule, outcome="ABSTAIN", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=host_reason, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
            return _record(unit, rule, outcome="REJECT", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)

    if rewrite_status == "proposed" and rewrite is not None:
        checker = check_rewrite(unit.text, rewrite, document_text=document_text, referent_quotes=[span.quote for span in evidence if span.role == "referent"], allowed_transitions=_transition_rows(contract), rule_id=_rule_id(rule), defined_terms=defined_terms)
        if not checker.ok:
            return _record(unit, rule, outcome="CONFIRM", severity=_demote(severity), scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=None, rewrite_status="withheld_checker_veto", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated, attempted_rewrite=rewrite, checker_violations=checker.violations)
    model_verdict = str(model_output.get("verdict", "")).upper()
    if model_verdict != "CONFIRM":
        return _record(unit, rule, outcome="ABSTAIN", severity=None, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason="inconsistent_output", rewrite=None, rewrite_status="not_applicable", instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)
    return _record(unit, rule, outcome="CONFIRM", severity=severity, scores=scores, evidence=evidence, preservation_reason=None, abstain_reason=None, rewrite=rewrite, rewrite_status=rewrite_status, instrument_id=instrument_id, cache_key=cache_key, occurrence_index=occurrence_index, occurrences_truncated=occurrences_truncated)


def adjudicate(
    unit: Any,
    rule: Any,
    model_output: dict[str, Any],
    *,
    instrument_id: str,
    cache_key: str,
    repository_lookup: Any = None,
    defined_terms: Sequence[str] | None = None,
) -> FindingRecord | tuple[FindingRecord, ...]:
    """Reconcile one model output with admission, evidence, and repair policy."""
    errors = validate_model_output(model_output)
    if errors:
        raise ValueError("invalid model output: " + "; ".join(errors))
    contract = _rule_contract(rule)
    terms = _defined_terms(unit, rule, contract, defined_terms)
    kind = _unit_kind(unit)
    if kind == "PASSAGE_PROBE":
        occurrences = model_output.get("occurrences") or []
        return tuple(
            _one(
                unit,
                rule,
                {**model_output, **occurrence, "kind": "PASSAGE_PROBE"},
                instrument_id=instrument_id,
                cache_key=cache_key,
                repository_lookup=repository_lookup,
                occurrence_index=index,
                occurrences_truncated=bool(model_output.get("occurrences_truncated", False)),
                defined_terms=terms,
            )
            for index, occurrence in enumerate(occurrences)
        )
    return _one(
        unit,
        rule,
        model_output,
        instrument_id=instrument_id,
        cache_key=cache_key,
        repository_lookup=repository_lookup,
        occurrence_index=None,
        occurrences_truncated=False,
        defined_terms=terms,
    )


__all__ = ["EvidenceSpan", "FindingRecord", "adjudicate"]
