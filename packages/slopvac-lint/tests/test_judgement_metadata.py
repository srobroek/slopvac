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


def _contract_record(record: dict) -> dict:
    expected = {
        key: record[key]
        for key in (
            "dims",
            "evidence",
            "warrant_min",
            "protects",
            "judgement_ceiling",
            "adjudicates",
            "scope_class",
        )
        if key in record
    }
    expected.setdefault("adjudicates", None)
    transitions = record.get("allowed_transitions")
    if transitions is not None:
        expected["allowed_transitions"] = {
            "status": transitions["status"],
            "requires": transitions["requires"],
            "rows": tuple(
                {
                    "token_class": row["class"],
                    "src": row["from"],
                    "dst": row["to"],
                }
                for row in transitions["table"]
            ),
        }
    else:
        expected["allowed_transitions"] = None
    expected["evidence"] = {
        **expected["evidence"],
        "roles": tuple(expected["evidence"]["roles"]),
    }
    expected["protects"] = tuple(expected["protects"])
    expected.setdefault("scope_class", "local")
    expected["host_predicates"] = tuple(record.get("host_predicates", ()))
    return expected


def _loaded_contract(rule) -> dict:
    contract = asdict(rule.judgement)
    table = contract["allowed_transitions"]
    if table is not None:
        table["rows"] = tuple(table["rows"])
    contract["host_predicates"] = tuple(contract["host_predicates"])
    return contract


def test_shipped_rules_load_and_contract_records_match() -> None:
    ruleset = load_ruleset([], verify=False)
    records = json.loads(CONTRACT.read_text(encoding="utf-8"))["rule_records"]
    by_id = {record["id"]: record for record in records}
    rules = ruleset.judgement_rules()
    assert len(ruleset.rules) == 231
    assert len(rules) == 66
    assert {rule.qualified_id for rule in rules} == set(by_id)
    for rule in rules:
        assert _loaded_contract(rule) == _contract_record(by_id[rule.qualified_id])

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

def test_loader_rejects_unknown_transition_token_class(tmp_path: Path) -> None:
    raw = _rule(
        allowed_transitions={
            "status": "provisional",
            "requires": "an invariant",
            "rows": [{"class": "modality_typo", "from": "A", "to": "B"}],
        }
    )
    category = {"id": "custom", "title": "Custom", "description": "x", "rules": [raw]}
    (tmp_path / "category.yml").write_text(json.dumps(category), encoding="utf-8")
    with pytest.raises(RuleLoadError, match="modality_typo"):
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
