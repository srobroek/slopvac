from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from slopvac.analyze import Unit
from slopvac.judgement.adjudicate import _heading_echo_material_redundancy, adjudicate
from slopvac.judgement.schema import validate_model_output
from slopvac.judgement.types import (
    EvidenceSpec,
    JudgementContract,
    Transition,
    TransitionTable,
)
from slopvac.projection import project
from slopvac.rules import load_ruleset


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


# --- heading-echo material redundancy (root decision omp-plugins-q4bb.10) ----

_HEADING_ECHO_FIXTURE = Path(__file__).resolve().parent / "fixtures/judgement/heading-echo-material-redundancy.md"
_HEADING_ECHO_CONTROLS = [
    ("Install the plugin", "This section covers installing the plugin."),
    ("Authentication", "Authentication covers access control."),
    ("Deployment", "Deployment is the act of releasing software."),
    ("History", "We first developed these guidelines in the mid-90s."),
    ("History", "We continue to revise them every few years to provide updated advice on clear communication."),
    ("History", "We've broadened our coverage, but the information still bears the stamp of its origin."),
    ("Example", "This example uses several of the techniques discussed above to cut a 54 word sentence down to 22 words, with no loss of meaning."),
]


def _heading_echo_pairs() -> list[tuple[str, str]]:
    """The fixture's `## heading` and first-unit pairs, in file order."""
    pairs: list[tuple[str, str]] = []
    heading: str | None = None
    for line in _HEADING_ECHO_FIXTURE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:]
        elif stripped and heading is not None:
            pairs.append((heading, stripped))
            heading = None
    return pairs


def _heading_echo_rule(*, gated: bool = True) -> SimpleNamespace:
    return _rule(
        min_arity=2,
        roles=("defect", "antecedent"),
        warrant_min=2,
        ceiling="suggestion",
        protects=("accessibility_consistency", "factual_polarity_or_contrast", "normative_obligation", "quoted_specimen"),
        host_predicates=("heading_echo_material_redundancy",) if gated else (),
    )


def _heading_echo_record(heading: str, sentence: str, *, gated: bool = True):
    unit = _unit(sentence)
    unit.context = heading
    output = _output(
        unit,
        warrant="quote_plus_particular",
        evidence=[_evidence(unit), _evidence(unit, quote=heading, source="context", role="antecedent")],
    )
    return _adjudicate(unit, _heading_echo_rule(gated=gated), output)


def test_heading_echo_fixture_holds_the_decided_controls() -> None:
    assert _heading_echo_pairs() == _HEADING_ECHO_CONTROLS


@pytest.mark.parametrize(
    ("heading", "sentence", "expected"),
    [
        ("Install the plugin", "Run apm install slopvac.", "heading_echo_unit_adds_material"),
        ("Authentication", "Every request sends a bearer token.", "heading_echo_no_lexical_echo"),
        ("Overview", "This section gives an overview.", None),
        ("Retention policy", "The retention policy is described below.", None),
        ("Limits", "Limits apply.", None),
        ("Limits", "Requests are capped at 100 per minute.", "heading_echo_no_lexical_echo"),
        ("Configuration", "Configuration is covered here.", None),
        ("Configuration", "Set `SLOPVAC_PROFILE` to choose a profile.", "heading_echo_no_lexical_echo"),
        ("Why", "Because latency matters.", "heading_echo_no_lexical_echo"),
        ("Examples", "Examples follow.", None),
        ("Install", "Installation.", None),
        ("Configure", "Configuration.", None),
        ("Authenticate", "Authentication.", None),
    ],
    ids=["install-run-apm", "authentication-bearer-token", "overview", "retention-policy", "limits-apply", "limits-capped", "configuration-covered", "configuration-profile", "why-latency", "examples-follow", "install-installation", "configure-configuration", "authenticate-authentication"],
)
def test_heading_echo_review_acceptance_pairs(heading: str, sentence: str, expected: str | None) -> None:
    assert _heading_echo_material_redundancy(heading, sentence) == expected


@pytest.mark.parametrize(
    ("index", "outcome"),
    [(0, "CONFIRM"), (1, "CONFIRM"), (2, "CONFIRM"), (3, "REJECT"), (4, "REJECT"), (5, "REJECT"), (6, "REJECT")],
    ids=[
        "install-the-plugin-confirms",
        "authentication-confirms",
        "deployment-confirms",
        "history-mid-90s-rejects",
        "history-revise-rejects",
        "history-coverage-rejects",
        "example-54-words-rejects",
    ],
)
def test_heading_echo_control_outcome(index: int, outcome: str) -> None:
    heading, sentence = _heading_echo_pairs()[index]
    record = _heading_echo_record(heading, sentence)
    assert record.outcome == outcome
    assert record.severity == ("suggestion" if outcome == "CONFIRM" else None)


@pytest.mark.parametrize(
    ("heading", "sentence", "reason"),
    [
        ("Install the plugin", "This section covers installing the plugin.", None),
        ("Task", "Read", "heading_echo_unit_not_a_sentence"),
        ("Task", "Claim it first.", "heading_echo_no_lexical_echo"),
        ("Task", "Read the brief\nand claim the bead.", "heading_echo_unit_not_a_sentence"),
        ("History", "We first developed these guidelines in the mid-90s.", "heading_echo_no_lexical_echo"),
        ("Example", "This example uses 54 words of prose.", "heading_echo_unit_adds_material"),
        ("Checks", "Every check MUST name its evidence.", "heading_echo_unit_adds_material"),
        ("Tools", "Tools live in [the reference](docs/tools.md).", "heading_echo_unit_adds_material"),
        ("Tools", "Tools are declared in `tools.toml`.", "heading_echo_unit_adds_material"),
    ],
    ids=[
        "all-clauses-hold",
        "no-terminal-punctuation",
        "three-words",
        "embedded-newline",
        "no-shared-content-word",
        "adds-a-figure",
        "adds-a-normative-word",
        "adds-a-markdown-link",
        "adds-a-code-span",
    ],
)
def test_heading_echo_clause_attribution(heading: str, sentence: str, reason: str | None) -> None:
    assert _heading_echo_material_redundancy(heading, sentence) == reason


def test_heading_echo_abstains_without_an_antecedent_span() -> None:
    unit = _unit("Deployment is the act of releasing software.")
    record = _adjudicate(unit, _rule(host_predicates=("heading_echo_material_redundancy",)), _output(unit, evidence=[_evidence(unit)]))
    assert record.outcome == "ABSTAIN"
    assert record.abstain_reason == "heading_echo_no_antecedent"


def test_heading_echo_abstains_on_a_blank_antecedent_quote() -> None:
    record = _heading_echo_record(" ", "Deployment is the act of releasing software.")
    assert record.outcome == "ABSTAIN"
    assert record.abstain_reason == "heading_echo_no_antecedent"


def test_heading_echo_gate_changes_nothing_for_a_rule_without_the_predicate() -> None:
    heading, sentence = _heading_echo_pairs()[3]
    assert _heading_echo_record(heading, sentence).outcome == "REJECT"
    assert _heading_echo_record(heading, sentence, gated=False).outcome == "CONFIRM"


def test_shipped_heading_echo_contract_gains_only_the_host_predicate() -> None:
    rules = {rule.qualified_id: rule for rule in load_ruleset([], verify=False).judgement_rules()}
    rule = rules["ai-tells-structure.heading-echo"]
    contract = rule.judgement
    assert tuple(predicate.id for predicate in contract.host_predicates) == ("heading_echo_material_redundancy",)
    assert contract.protects == ("accessibility_consistency", "factual_polarity_or_contrast", "normative_obligation", "quoted_specimen")
    assert contract.judgement_ceiling == "suggestion"
    assert contract.warrant_min == 2
    assert contract.dims == {"fit": "ask", "harm": "ask", "repair": "ask", "warrant": "ask"}
    assert (contract.evidence.min_arity, tuple(contract.evidence.roles)) == (2, ("defect", "antecedent"))
    assert contract.scope_class == "local"
    assert contract.adjudicates is None
    assert contract.allowed_transitions is None
    assert rule.scope == "paragraph"
    assert rule.severity == "suggestion"
    assert rule.tiers == {"strict": "enforced", "normal": "enforced", "relaxed": "advisory"}
    assert rule.judgement_question == (
        "Given the heading alone, does the first sentence repeat its proposition with no new "
        "operation, constraint, path, metric, or scope? Same topic is not enough to flag."
    )
    assert {
        qualified_id: tuple(predicate.id for predicate in loaded.judgement.host_predicates)
        for qualified_id, loaded in rules.items()
        if loaded.judgement.host_predicates
    } == {
        "ai-tells-structure.heading-echo": ("heading_echo_material_redundancy",),
        "prose-discipline.bare-quantifier-with-figure-available": ("figure_available",),
        "prose-scope.code-change-prose-scope": ("code_diff_available",),
        "ste-nouns.long-domain-term-without-short-form": ("no_short_form_in_document",),
    }
