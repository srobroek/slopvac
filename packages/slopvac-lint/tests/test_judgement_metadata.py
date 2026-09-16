import json
from dataclasses import asdict
from pathlib import Path

import pytest

from slopvac.model import Rule
from slopvac.rules import RuleLoadError, load_ruleset


def _repo_root() -> Path:
    for directory in (Path(__file__).resolve().parent, *Path(__file__).resolve().parents):
        if (directory / "slopvac.toml").is_file():
            return directory
    raise RuntimeError("Could not locate repository root containing slopvac.toml")


CONTRACT = _repo_root() / "packages/slopvac-lint/docs/research/rubric-2026-09-15/rubric-contract.json"


def _rule(**judgement):
    return {
        "id": "demo",
        "name": "Demo",
        "kind": "judgement",
        "message": "Check it.",
        "judgement_question": "Is it clear?",
        "provenance": {"source": "test"},
        "judgement": {
            "dims": {"fit": "ask", "harm": "ask", "repair": "ask", "warrant": "ask"},
            "evidence": {"min_arity": 1, "roles": ["defect"]},
            "warrant_min": 2,
            "protects": ["normative_obligation"],
            "judgement_ceiling": "warning",
            **judgement,
        },
    }


def test_shipped_rules_load_and_contract_records_match() -> None:
    ruleset = load_ruleset([], verify=False)
    records = json.loads(CONTRACT.read_text())['rule_records']
    by_id = {record['id']: record for record in records}
    assert len(ruleset.rules) == 231
    assert len(ruleset.judgement_rules()) == 66
    for rule in ruleset.judgement_rules():
        contract = asdict(rule.judgement)
        if rule.qualified_id == 'prose-scope.code-change-prose-scope':
            assert contract == {
                'dims': {'fit': 'ask', 'harm': 'ask', 'repair': 'ask', 'warrant': 'ask'},
                'evidence': {'min_arity': 2, 'roles': ('defect', 'referent')},
                'warrant_min': 2, 'protects': (), 'judgement_ceiling': 'error',
                'adjudicates': None, 'allowed_transitions': None,
                'host_predicates': ({'id': 'code_diff_available', 'definition': 'the host provides the applicable code diff for the document'},),
                'scope_class': 'probe',
            }
        else:
            expected = by_id[rule.qualified_id]
            assert contract['dims'] == expected['dims']
            assert contract['evidence']['min_arity'] == expected['evidence']['min_arity']
            assert tuple(contract['evidence']['roles']) == tuple(expected['evidence']['roles'])
            for key in ('warrant_min', 'protects', 'judgement_ceiling', 'scope_class'):
                assert contract[key] == expected[key] if key != 'protects' else tuple(contract[key]) == tuple(expected[key])


def test_loader_rejects_missing_or_mismatched_contract(tmp_path: Path) -> None:
    valid = _rule()
    category = {"id": "custom", "title": "Custom", "description": "x", "rules": [valid]}
    (tmp_path / "category.yml").write_text(json.dumps(category), encoding="utf-8")
    assert load_ruleset([tmp_path], verify=False).by_id("custom.demo") is not None
    for bad in ({**valid, "judgement": None}, {**valid, "kind": "pattern"}):
        bad_category = {**category, "rules": [bad]}
        (tmp_path / "category.yml").write_text(json.dumps(bad_category), encoding="utf-8")
        with pytest.raises(RuleLoadError):
            load_ruleset([tmp_path], verify=False)


@pytest.mark.parametrize("change", [
    {"protects": ["unknown"]},
    {"evidence": {"min_arity": 1, "roles": ["antecedent"]}},
    {"evidence": {"min_arity": 2, "roles": ["defect"]}},
    {"adjudicates": "quoted_specimen"},
])
def test_loader_rejects_invalid_contract_fields(tmp_path: Path, change: dict) -> None:
    raw = _rule(**change)
    category = {"id": "custom", "title": "Custom", "description": "x", "rules": [raw]}
    (tmp_path / "category.yml").write_text(json.dumps(category), encoding="utf-8")
    with pytest.raises(RuleLoadError, match="demo"):
        load_ruleset([tmp_path], verify=False)


def test_transition_rows_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="rows"):
        Rule.model_validate(_rule(allowed_transitions={"status": "provisional", "requires": "x", "rows": []}))
