"""The machine-readable output contracts.

These payloads were hand-built dicts, which is why they are tested here as a
SHAPE rather than as strings. A dict literal cannot state that `level` is one of a
closed set, that `partialFingerprints` is required for stable alert identity, or
that a key the documentation promises is the key the tool emits -- and every one
of those went wrong at least once.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from slopvac.config import Severity
from slopvac.model import CategoryScore, DocumentScore, Finding
from slopvac.report import (
    LintReport,
    SarifLog,
    SarifResult,
    build_sarif,
    finding_fingerprint,
    summarize,
)
from slopvac.rules import load_ruleset


def _finding(**overrides) -> Finding:
    base = dict(
        path="doc.md",
        line=3,
        column=5,
        rule_id="orwell.stale-figure",
        category="orwell",
        severity=Severity.ERROR,
        message="stale figure: paradigm shift",
    )
    base.update(overrides)
    return Finding(**base)


def _score(findings=None, **overrides) -> DocumentScore:
    findings = findings if findings is not None else [_finding()]
    base = dict(
        path="doc.md",
        profile="normal",
        words=200,
        sentences=10,
        paragraphs=3,
        findings=findings,
        categories=[
            CategoryScore(
                category="orwell",
                findings=len(findings),
                errors=sum(1 for f in findings if f.severity is Severity.ERROR),
                warnings=sum(1 for f in findings if f.severity is Severity.WARNING),
                suggestions=sum(
                    1 for f in findings if f.severity is Severity.SUGGESTION
                ),
                per_100_words=len(findings) / 200 * 100,
                score=80.0,
            )
        ],
        total_findings=len(findings),
        errors=sum(1 for f in findings if f.severity is Severity.ERROR),
        warnings=sum(1 for f in findings if f.severity is Severity.WARNING),
        suggestions=sum(1 for f in findings if f.severity is Severity.SUGGESTION),
        score=80.0,
        passed=False,
    )
    base.update(overrides)
    return DocumentScore(**base)


# --- summarize ----------------------------------------------------------------


def test_density_is_recomputed_over_total_words_not_averaged():
    """Averaging per-document densities lets a stub outweigh a long document.

    One finding in a 20-word file is 5.0 per 100 words; the same finding in a
    2,000-word file is 0.05. Averaging those two reports 2.5 for a repository whose
    real density is 0.099, which misstates the whole run.
    """
    stub = _score(words=20, findings=[_finding(path="stub.md")])
    long = _score(words=2000, findings=[_finding(path="long.md")])
    summary = summarize([stub, long])

    assert summary.words == 2020
    assert summary.findings == 2
    assert summary.per_100_words == pytest.approx(2 / 2020 * 100, abs=1e-3)


def test_an_empty_run_summarizes_as_a_clean_pass():
    summary = summarize([])
    assert summary.documents == 0
    assert summary.score == 100.0
    assert summary.passed is True
    assert summary.categories == []


def test_the_json_payload_round_trips_through_its_own_model():
    """The emitted keys are the model's keys, which is the point of the model.

    Re-validating the serialised payload is what makes the documentation a
    description rather than a claim: a renamed field fails here.
    """
    report = LintReport(version="1.2.3", summary=summarize([_score()]), documents=[_score()])
    payload = json.loads(report.emit())

    assert payload["version"] == "1.2.3"
    assert payload["schema_version"] == 1
    assert payload["summary"]["findings"] == 1
    assert payload["documents"][0]["findings"][0]["rule_id"] == "orwell.stale-figure"
    # A consumer can validate against the same definition the tool serialises from.
    assert LintReport.model_validate(payload) == report


def test_a_path_or_enum_cannot_leak_into_the_payload_as_a_repr():
    """`json.dumps(..., default=str)` used to hide this.

    A `Path` or an `Enum` reaching the encoder serialised as whatever `str()` gave,
    so a field that should have been a string carried a `PosixPath` repr in some
    runs and not others.
    """
    payload = json.loads(LintReport(version="1", summary=summarize([]), documents=[]).emit())
    assert "PosixPath" not in json.dumps(payload)


# --- SARIF --------------------------------------------------------------------


def test_the_fingerprint_excludes_the_line_but_not_the_message():
    """Code scanning falls back to the LINE when there is no fingerprint.

    Editing one paragraph would then close and re-open every alert below it as new.
    The message stays in, because one rule fires on a file for different reasons.
    """
    same_line_moved = finding_fingerprint(_finding(line=3), 1) == finding_fingerprint(
        _finding(line=99), 1
    )
    assert same_line_moved

    assert finding_fingerprint(_finding(message="a"), 1) != finding_fingerprint(
        _finding(message="b"), 1
    )


def test_repeated_identical_findings_get_distinct_fingerprints():
    """One rule fires for the SAME reason more than once.

    Two alerts sharing a fingerprint collapse into one, so an occurrence ordinal is
    what makes the identity stable AND unique.
    """
    assert finding_fingerprint(_finding(), 1) != finding_fingerprint(_finding(), 2)


def test_sarif_is_emitted_in_camel_case_with_no_nulls():
    ruleset = load_ruleset()
    log = build_sarif(
        [_score()], ruleset.rules, version="1.0.0", tool_uri="https://example.invalid"
    )
    payload = json.loads(log.emit())

    assert payload["version"] == "2.1.0"
    assert payload["$schema"].endswith("sarif-2.1.0.json")
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == "slopvac"
    assert run["columnKind"] == "utf16CodeUnits"
    result = run["results"][0]
    assert result["ruleId"] == "orwell.stale-figure"
    assert result["partialFingerprints"]["slopvacFindingV1"]
    assert result["locations"][0]["physicalLocation"]["region"]["startLine"] == 3
    # A reference a rule does not carry is ABSENT, not null: a null renders as an
    # empty row in the alert detail pane.
    assert "null" not in json.dumps(payload)
    # And the emitted document validates as its own model.
    assert SarifLog.model_validate(payload)


def test_one_profile_names_the_run_and_two_read_as_mixed():
    """Without a category GitHub treats a second upload as a REPLACEMENT.

    It silently closes the first upload's alerts, so a repo linting at two profiles
    would see half its findings disappear on every run.
    """
    ruleset = load_ruleset()
    single = build_sarif(
        [_score()], ruleset.rules, version="1", tool_uri="https://example.invalid"
    )
    assert single.runs[0].automation_details.id == "slopvac/normal"

    both = build_sarif(
        [_score(), _score(profile="strict", path="other.md")],
        ruleset.rules,
        version="1",
        tool_uri="https://example.invalid",
    )
    assert both.runs[0].automation_details.id == "slopvac/mixed"


def test_a_result_without_a_fingerprint_is_rejected_at_construction():
    """Typed as required, so a future result cannot be built without one."""
    with pytest.raises(ValidationError):
        SarifResult(
            ruleId="orwell.stale-figure",
            level="error",
            message={"text": "x"},
            partialFingerprints={},
            locations=[],
        )


def test_an_off_specification_level_is_rejected():
    """`level` is a closed set, which a dict literal could not state."""
    with pytest.raises(ValidationError):
        SarifResult(
            ruleId="orwell.stale-figure",
            level="critical",
            message={"text": "x"},
            partialFingerprints={"slopvacFindingV1": "abc"},
            locations=[
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "doc.md"},
                        "region": {"startLine": 1, "startColumn": 1},
                    }
                }
            ],
        )


def test_judgement_rules_are_not_shipped_as_descriptors():
    """A rule no linter can check has no result to attach.

    Shipping it as a descriptor with zero results makes the alert list claim
    coverage the run does not have.
    """
    from slopvac.model import RuleKind

    ruleset = load_ruleset()
    judgement = {
        rule.qualified_id for rule in ruleset.rules if rule.kind is RuleKind.JUDGEMENT
    }
    assert judgement, "no judgement rules ship; the test proves nothing"

    log = build_sarif(
        [_score()], ruleset.rules, version="1", tool_uri="https://example.invalid"
    )
    emitted = {descriptor.id for descriptor in log.runs[0].tool.driver.rules}
    assert not (emitted & judgement)
