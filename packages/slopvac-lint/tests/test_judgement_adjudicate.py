from __future__ import annotations

from types import SimpleNamespace

from slopvac.projection import project

from slopvac.analyze import Unit
from slopvac.judgement.adjudicate import adjudicate
from slopvac.judgement.schema import validate_model_output
from slopvac.judgement.types import (
    EvidenceSpec,
    JudgementContract,
    Transition,
    TransitionTable,
)


def _unit(text: str = "The shape is here.", *, kind: str = "SPAN_CANDIDATE", origin: str = "authored") -> Unit:
    _, projection = project(text)
    return Unit(
        kind=kind,
        rule_id="demo.rule",
        path="guide.md",
        text=text,
        range=(0, len(text)),
        doc_range=(10, 10 + len(text)),
        projection=projection,
        origin=origin,
        region_class="prose",
        source_sha256="sha",
        unit_id="unit",
    )


def _rule(
    *,
    min_arity: int = 1,
    roles: tuple[str, ...] = ("defect",),
    warrant_min: int = 1,
    protects: tuple[str, ...] = (),
    ceiling: str = "error",
    adjudicates: str | None = None,
    host_predicates: tuple[str, ...] = (),
    transitions: tuple[Transition, ...] = (),
) -> SimpleNamespace:
    table = (
        TransitionTable("provisional", transitions, "test") if transitions else None
    )
    return SimpleNamespace(
        qualified_id="demo.rule",
        severity="error",
        scope="paragraph",
        judgement=JudgementContract(
            dims={"fit": "ask", "harm": "ask", "repair": "ask", "warrant": "ask"},
            evidence=EvidenceSpec(min_arity, roles),
            warrant_min=warrant_min,
            protects=protects,
            judgement_ceiling=ceiling,
            adjudicates=adjudicates,
            allowed_transitions=table,
            host_predicates=tuple(SimpleNamespace(id=value, definition="test") for value in host_predicates),
        ),
    )


def _output(
    unit: Unit,
    *,
    verdict: str = "confirm",
    fit: str = "unambiguous_match",
    harm: str = "misleads_or_blocks",
    repair: str = "local_substitution",
    warrant: str = "quote_only",
    evidence: list[dict] | None = None,
    preservation_reason: str | None = None,
    abstain_reason: str | None = None,
    rewrite: str | None = None,
    rewrite_status: str = "not_applicable",
    kind: str | None = None,
    occurrences: list[dict] | None = None,
    occurrences_truncated: bool = False,
) -> dict:
    return {
        "abstain_reason": abstain_reason,
        "admissible": True,
        "evidence": evidence if kind != "PASSAGE_PROBE" else None,
        "kind": kind or unit.kind,
        "note": "test",
        "occurrences": occurrences if kind == "PASSAGE_PROBE" else None,
        "occurrences_truncated": occurrences_truncated,
        "preservation_reason": preservation_reason,
        "rewrite": rewrite if kind != "PASSAGE_PROBE" else None,
        "rewrite_status": rewrite_status if kind != "PASSAGE_PROBE" else "not_applicable",
        "rule_id": "demo.rule",
        "scores": None if kind == "PASSAGE_PROBE" else {"fit": fit, "harm": harm, "repair": repair, "warrant": warrant},
        "unit_id": unit.unit_id,
        "verdict": verdict,
    }


def _evidence(unit: Unit, *, quote: str | None = None, role: str = "defect", source: str = "unit", start: int = 0, source_ref: str | None = None) -> dict:
    quote = unit.text if quote is None else quote
    return {"quote": quote, "start": start, "end": start + len(quote), "role": role, "source": source, "source_ref": source_ref}


def _adjudicate(unit: Unit, rule: SimpleNamespace, output: dict):
    return adjudicate(unit, rule, output, instrument_id="instrument", cache_key="cache")


def test_schema_accepts_span_and_probe_and_rejects_shape_errors() -> None:
    unit = _unit("x")
    span = _output(unit, evidence=[_evidence(unit)], fit="unambiguous_match")
    assert validate_model_output(span) == []
    occurrence = {key: span[key] for key in ("abstain_reason", "evidence", "preservation_reason", "rewrite", "rewrite_status", "scores", "verdict")}
    probe = _output(unit, kind="PASSAGE_PROBE", occurrences=[occurrence])
    assert validate_model_output(probe) == []
    assert validate_model_output({**span, "scores": {**span["scores"], "fit": "bad"}})
    assert validate_model_output({**span, "kind": "PASSAGE_PROBE", "scores": span["scores"], "occurrences": [_output(unit)["evidence"]]})


def test_generated_origin_is_dropped() -> None:
    unit = _unit(origin="generated")
    record = _adjudicate(unit, _rule(), _output(unit, evidence=[_evidence(unit)]))
    assert record.outcome == "DROP"


def test_authored_quoted_region_is_preserved() -> None:
    unit = _unit()
    unit.region_class = "quoted"
    record = _adjudicate(unit, _rule(protects=("quoted_specimen",)), _output(unit, evidence=[_evidence(unit)], preservation_reason=None))
    assert record.outcome == "PRESERVE"
    assert record.preservation_reason == "quoted_specimen"



def test_preserve_requires_exact_evidence() -> None:
    unit = _unit()
    unit.region_class = "quoted"
    output = _output(unit, evidence=[_evidence(unit, quote="not present")], preservation_reason=None)
    record = _adjudicate(unit, _rule(protects=("quoted_specimen",)), output)
    assert record.outcome == "ABSTAIN"
    assert record.abstain_reason == "no_exact_evidence"


def test_reject_absent_fit_precedes_missing_evidence() -> None:
    unit = _unit()
    output = _output(unit, fit="absent", verdict="reject", evidence=[])
    record = _adjudicate(unit, _rule(), output)
    assert record.outcome == "REJECT"

def test_exact_slice_mismatch_abstains() -> None:
    unit = _unit("actual")
    record = _adjudicate(unit, _rule(), _output(unit, evidence=[_evidence(unit, quote="other")]))
    assert record.outcome == "ABSTAIN"
    assert record.abstain_reason == "no_exact_evidence"


def test_defect_evidence_from_context_abstains() -> None:
    unit = _unit()
    unit.context = "context"
    record = _adjudicate(unit, _rule(), _output(unit, evidence=[_evidence(unit, quote="context", source="context", role="defect")]))
    assert record.outcome == "ABSTAIN"


def test_two_role_arity_can_use_context_antecedent() -> None:
    unit = _unit("defect")
    unit.context = "antecedent"
    evidence = [_evidence(unit), _evidence(unit, quote="antecedent", source="context", role="antecedent")]
    record = _adjudicate(unit, _rule(min_arity=2, roles=("defect", "antecedent")), _output(unit, evidence=evidence, warrant="quote_plus_particular"))
    assert record.outcome == "CONFIRM"


def test_partial_fit_and_insufficient_warrant_reject() -> None:
    unit = _unit()
    partial = _adjudicate(unit, _rule(), _output(unit, fit="partial", evidence=[_evidence(unit)], verdict="reject"))
    assert partial.outcome == "REJECT"
    weak = _adjudicate(unit, _rule(warrant_min=2), _output(unit, evidence=[_evidence(unit)], verdict="reject"))
    assert weak.outcome == "REJECT"


def test_model_reject_with_absent_fit_does_not_need_evidence() -> None:
    unit = _unit()
    record = _adjudicate(unit, _rule(), _output(unit, verdict="reject", fit="absent", evidence=[]))
    assert record.outcome == "REJECT"


def test_model_confirm_with_unambiguous_fit_and_empty_evidence_abstains() -> None:
    unit = _unit()
    record = _adjudicate(unit, _rule(), _output(unit, verdict="confirm", fit="unambiguous_match", evidence=[]))
    assert record.outcome == "ABSTAIN"
    assert record.abstain_reason == "no_exact_evidence"

def test_harm_none_requires_safe_deletion() -> None:
    unit = _unit()
    substitution = _adjudicate(unit, _rule(), _output(unit, harm="none", repair="local_substitution", evidence=[_evidence(unit)], verdict="reject"))
    assert substitution.outcome == "REJECT"
    deletion = _adjudicate(unit, _rule(), _output(unit, harm="none", repair="safe_deletion", evidence=[_evidence(unit)]))
    assert deletion.outcome == "CONFIRM"
    assert deletion.severity == "suggestion"


def test_unsafe_severity_is_capped_by_rule_ceiling() -> None:
    unit = _unit()
    record = _adjudicate(unit, _rule(ceiling="suggestion"), _output(unit, harm="unsafe_or_normative", evidence=[_evidence(unit)]))
    assert record.outcome == "CONFIRM"
    assert record.severity == "suggestion"


def test_checker_veto_withholds_rewrite_and_demotes() -> None:
    unit = _unit("MUST use the command")
    output = _output(unit, harm="unsafe_or_normative", evidence=[_evidence(unit)], rewrite="MAY use the command", rewrite_status="proposed")
    record = _adjudicate(unit, _rule(), output)
    assert record.outcome == "CONFIRM"
    assert record.rewrite is None
    assert record.rewrite_status == "withheld_checker_veto"
    assert record.attempted_rewrite == "MAY use the command"
    assert record.checker_violations
    assert record.severity == "warning"


def test_withheld_fact_does_not_demote() -> None:
    unit = _unit()
    output = _output(unit, evidence=[_evidence(unit)], rewrite_status="withheld_needs_fact", rewrite=None)
    record = _adjudicate(unit, _rule(), output)
    assert record.severity == "warning"


def test_model_confirm_with_absent_fit_is_inconsistent() -> None:
    unit = _unit()
    output = _output(unit, fit="absent", evidence=[_evidence(unit)], verdict="confirm")
    record = _adjudicate(unit, _rule(), output)
    assert record.outcome == "ABSTAIN"
    assert record.abstain_reason == "inconsistent_output"


def test_probe_occurrences_expand_to_records() -> None:
    unit = _unit(kind="PASSAGE_PROBE")
    occurrence = {key: _output(_unit("x"), evidence=[_evidence(_unit("x"))])[key] for key in ()}
    occurrence = {"abstain_reason": None, "evidence": [_evidence(unit)], "preservation_reason": None, "rewrite": None, "rewrite_status": "not_applicable", "scores": {"fit": "unambiguous_match", "harm": "misleads_or_blocks", "repair": "local_substitution", "warrant": "quote_only"}, "verdict": "confirm"}
    records = _adjudicate(unit, _rule(), _output(unit, kind="PASSAGE_PROBE", occurrences=[occurrence, occurrence], occurrences_truncated=True))
    assert isinstance(records, tuple)
    assert [record.occurrence_index for record in records] == [0, 1]
    assert all(record.occurrences_truncated for record in records)


def test_transition_table_allows_safety_change_but_vetoes_unauthorised_note_change() -> None:
    unit = _unit("CAUTION: use the command")
    transitions = (Transition("modality", "CAUTION", "WARNING"),)
    allowed = _rule(transitions=transitions)
    passing = _adjudicate(unit, allowed, _output(unit, harm="unsafe_or_normative", evidence=[_evidence(unit)], rewrite="WARNING: use the command", rewrite_status="proposed"))
    assert passing.rewrite_status == "proposed"
    note_unit = _unit("NOTE: use the command")
    failing = _adjudicate(note_unit, allowed, _output(note_unit, harm="unsafe_or_normative", evidence=[_evidence(note_unit)], rewrite="CAUTION: use the command", rewrite_status="proposed"))
    assert failing.rewrite_status == "withheld_checker_veto"

def test_heading_echo_preserves_material_first_sentence() -> None:
    unit = _unit("Run the migration for production.")
    unit.document_text = "## Migration\n\nRun the migration for production."
    unit.doc_range = (15, 49)
    rule = _rule(host_predicates=("heading_echo_material_redundancy",))
    record = _adjudicate(unit, rule, _output(unit, evidence=[_evidence(unit)]))
    assert record.outcome == "PRESERVE"
    assert record.preservation_reason == "material_content"


def test_heading_echo_confirms_literal_restatement() -> None:
    unit = _unit("Migration")
    unit.document_text = "## Migration\n\nMigration."
    unit.doc_range = (15, 24)
    rule = _rule(host_predicates=("heading_echo_material_redundancy",))
    record = _adjudicate(unit, rule, _output(unit, evidence=[_evidence(unit)]))
    assert record.outcome == "CONFIRM"
