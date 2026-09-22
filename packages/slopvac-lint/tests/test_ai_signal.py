from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopvac.analyze import parse
from slopvac.config import Config, Profile, Severity, resolve_for
from slopvac.engine import Engine
from slopvac.judgement.driver import _markdown_report
from slopvac.model import Finding, Provenance, Rule, RuleKind, Tier
from slopvac.report import LintReport, RunSummary, summarize
from slopvac.rules import RuleLoadError, load_ruleset
from slopvac.score import score_document


def _config() -> object:
    config = Config(profile=Profile.NORMAL)
    object.__setattr__(config, "root", Path("/repo"))
    return resolve_for(config, Path("/repo/a.md"))


def _rule(signal: str = "none") -> Rule:
    return Rule(
        id="probe",
        name="probe",
        kind=RuleKind.PATTERN,
        pattern=r"\bslop\b",
        message="replace {match}",
        provenance=Provenance(source="test"),
        category="fixture",
        ai_signal=signal,
        tiers={
            "strict": Tier.ENFORCED,
            "normal": Tier.ENFORCED,
            "relaxed": Tier.ENFORCED,
        },
    )


def _finding(signal: str = "none", severity: Severity = Severity.WARNING) -> Finding:
    return Finding(
        path="a.md",
        line=1,
        rule_id="fixture.probe",
        category="fixture",
        severity=severity,
        message="replace",
        ai_signal=signal,
    )


def test_strong_rule_finding_carries_signal() -> None:
    finding = Engine([_rule("strong")], _config()).run(parse("a.md", "slop here."))[0]
    assert finding.ai_signal == "strong"


def test_register_partition_counts_every_finding_once() -> None:
    findings = [_finding("strong"), _finding("weak"), _finding("none")]
    score = score_document("a.md", findings, 100, 1, 1, _config(), {"fixture": 1.0})
    assert (
        score.ai_register["strong"].findings
        + score.ai_register["weak"].findings
        + score.prose.findings
        == score.total_findings
    )
    summary = summarize([score])
    assert (
        summary.ai_register["strong"].findings
        + summary.ai_register["weak"].findings
        + summary.prose.findings
        == summary.findings
    )


def test_json_contains_ai_register_block() -> None:
    score = score_document(
        "a.md", [_finding("strong")], 100, 1, 1, _config(), {"fixture": 1.0}
    )
    payload = json.loads(
        LintReport(version="1", summary=summarize([score]), documents=[score]).emit()
    )
    assert set(payload["summary"]["ai_register"]) == {"strong", "weak"}
    assert set(payload["documents"][0]["ai_register"]) == {"strong", "weak"}


def test_judgement_report_splits_confirms() -> None:
    text = _markdown_report(
        [
            {
                "path": "a.md",
                "deterministic_score": 100,
                "adjusted_score": 90,
                "deterministic_findings": 0,
                "confirmed": 2,
                "ai_register_confirms": {"strong": 1, "weak": 1},
            }
        ],
        {},
        [],
    )
    assert "strong=1" in text and "weak=1" in text


def test_invalid_ai_signal_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "bad.yml").write_text(
        "id: bad\ntitle: bad\ndescription: bad\nrules:\n  - id: probe\n    name: probe\n    kind: pattern\n    pattern: bad\n    message: bad\n    ai_signal: impossible\n    provenance:\n      source: test\n",
        encoding="utf-8",
    )
    with pytest.raises(RuleLoadError):
        load_ruleset(extra_dirs=[tmp_path], verify=False)


def test_rule_signal_annotations_follow_catalog_boundaries() -> None:
    rules = load_ruleset(verify=False).rules
    assert all(
        not (r.ai_signal == "none" and r.ai_signal_source == "unmeasured")
        for r in rules
        if r.category.startswith("ai-tells-")
    )
    assert all(
        r.ai_signal_source != "catalog"
        for r in rules
        if not r.category.startswith("ai-tells-")
    )


def test_scoring_is_unchanged_by_signal_fields() -> None:
    plain = score_document(
        "a.md", [_finding("none")], 100, 1, 1, _config(), {"fixture": 1.0}
    )
    marked = score_document(
        "a.md", [_finding("strong")], 100, 1, 1, _config(), {"fixture": 1.0}
    )
    assert (plain.score, plain.passed, plain.failure_reasons) == (
        marked.score,
        marked.passed,
        marked.failure_reasons,
    )
