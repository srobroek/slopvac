"""Behavioral coverage for judgement aggregation and reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from slopvac.config import Config, Profile, resolve_for
from slopvac.judgement.aggregate import (
    Component,
    cluster_gate,
    components,
    coverage,
    load_dependence_table,
)
from slopvac.score import score_document


@dataclass(frozen=True)
class Evidence:
    quote: str
    start: int
    end: int
    role: str = "defect"
    source: str = "unit"
    source_ref: str | None = None
    doc_start: int | None = None
    doc_end: int | None = None


@dataclass(frozen=True)
class Finding:
    unit_id: str
    rule_id: str
    outcome: str = "CONFIRM"
    severity: str | None = "suggestion"
    scores: dict | None = None
    evidence: tuple[Evidence, ...] = ()
    preservation_reason: str | None = None
    abstain_reason: str | None = None
    rewrite: str | None = None
    rewrite_status: str = "not_applicable"
    core_fired: bool = True
    component_id: str | None = None
    source_sha256: str = "source"
    path: str = "doc.md"
    instrument_id: str = "instrument"
    judgement_cache_key: str = "cache"
    occurrence_index: int | None = None
    kind: str = "SPAN_CANDIDATE"


def finding(
    unit_id: str,
    rule_id: str,
    start: int,
    end: int,
    *,
    outcome: str = "CONFIRM",
    severity: str | None = "suggestion",
    harm: str = "none",
) -> Finding:
    return Finding(
        unit_id=unit_id,
        rule_id=rule_id,
        outcome=outcome,
        severity=severity,
        scores={"harm": harm},
        evidence=(Evidence("text", start, end, doc_start=start, doc_end=end),),
    )


def cfg(profile: Profile = Profile.NORMAL):
    config = Config(profile=profile)
    object.__setattr__(config, "root", Path("/repo"))
    return resolve_for(config, Path("/repo/doc.md"))


def test_components_merge_overlaps_and_dependence_pairs_only():
    records = [
        finding("one", "a.first", 0, 5),
        finding("two", "b.second", 4, 9),
        finding("three", "c.third", 20, 25),
        finding("four", "d.fourth", 30, 35),
    ]
    grouped = components(records, [(0, 40)], {"pairs": [["c.third", "d.fourth"]]})
    assert sorted(len(component.findings) for component in grouped) == [2, 2]
    assert {record.rule_id for component in grouped for record in component.findings} == {
        "a.first",
        "b.second",
        "c.third",
        "d.fourth",
    }


def test_judgement_defaults_are_provisional_and_disabled_by_default():
    settings = cfg().judgement
    assert settings.max_penalty == 15
    assert settings.cluster_min_components == 3
    assert settings.probe_occurrences_max == 12
    assert not settings.preserve_review_trigger


def test_cluster_gate_requires_the_configured_number_of_non_overlapping_components():
    records = [finding(str(i), f"rule.{i}", i * 4, i * 4 + 1) for i in range(3)]
    assert cluster_gate(components(records, [(0, 20)], {}), records, cfg()) == "REVISE"
    fewer = records[:2]
    assert cluster_gate(components(fewer, [(0, 20)], {}), fewer, cfg()) is None


def test_unsafe_or_normative_confirmation_trips_cluster_gate_alone():
    record = finding("one", "safety.risk", 0, 5, harm="unsafe_or_normative")
    assert cluster_gate(components([record], [(0, 10)], {}), [record], cfg()) == "REVISE"


def test_judgement_penalty_is_reported_without_gating_clean_scores():
    records = [finding(str(i), "cat.rule", i, i + 1) for i in range(300)]
    for profile in (Profile.STRICT, Profile.NORMAL):
        result = score_document(
            "doc.md",
            [],
            100,
            1,
            1,
            cfg(profile),
            {"cat": 1.0},
            judgement_findings=records,
            judgement_weights={"cat": 1.0},
        )
        assert result.passed
        assert result.score == 100.0
        assert result.judgement_penalty_uncapped == 30.0
        assert result.judgement_penalty == 15.0
        assert result.judgement_adjusted_score == 85.0


def test_only_error_ceiling_judgement_confirms_count_as_errors():
    record = finding("one", "safety.risk", 0, 5, severity="error")
    result = score_document(
        "doc.md",
        [],
        100,
        1,
        1,
        cfg(),
        {},
        judgement_findings=[record],
        judgement_rule_ceilings={"safety.risk": "error"},
    )
    assert not result.passed
    assert "1 error(s), limit 0" in result.failure_reasons


def test_judgement_warning_does_not_enter_warning_gate():
    record = finding("one", "cat.rule", 0, 5, severity="warning")
    config = cfg()
    object.__setattr__(config, "thresholds", config.thresholds.model_copy(update={"max_warnings": 0}))
    result = score_document(
        "doc.md",
        [],
        100,
        1,
        1,
        config,
        {},
        judgement_findings=[record],
        judgement_rule_ceilings={"cat.rule": "warning"},
    )
    assert result.passed
    assert not any("warning(s)" in reason for reason in result.failure_reasons)


def test_coverage_separates_abstention_from_failure_and_marks_not_run_partial():
    eligible = [
        {"unit_id": "one", "path": "doc.md", "pack_id": "pack", "rule_id": "rule.one"},
        {"unit_id": "two", "path": "doc.md", "pack_id": "pack", "rule_id": "rule.two"},
        {"unit_id": "three", "path": "doc.md", "pack_id": "pack", "rule_id": "rule.three"},
    ]
    records = [
        finding("one", "rule.one", 0, 1, outcome="ABSTAIN"),
        replace(finding("two", "rule.two", 2, 3), outcome="FAILED"),
    ]
    result = coverage(records, eligible)
    document = result.documents["doc.md"]
    assert document.abstained == 1
    assert document.failed == 1
    assert document.not_run == 1
    assert result.status == "PARTIAL"
    assert document.abstention_reasons["unknown"] == 1


def test_dependence_table_rejects_a_digest_mismatch(tmp_path: Path):
    table = tmp_path / "dependence.json"
    table.write_text(json.dumps({"dependence_table_sha": "bad", "pairs": []}))
    with pytest.raises(ValueError, match="sha mismatch"):
        load_dependence_table(table)


def test_cluster_component_primary_span_is_available_for_precomputed_components():
    record = finding("one", "rule.one", 0, 5)
    component = Component("component-1", (record,), "paragraph", ((0, 5),))
    assert component.primary_span == (0, 5)
