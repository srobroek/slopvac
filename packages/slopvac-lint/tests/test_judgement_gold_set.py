"""Structural checks for the judgement recall gold set."""

import json
from pathlib import Path

from slopvac.rules import load_ruleset

GOLD = Path(__file__).parent / "fixtures" / "judgement" / "gold" / "gold-v1.jsonl"


def _rows():
    with GOLD.open(encoding="utf-8") as stream:
        records = [json.loads(line) for line in stream if line.strip()]
    assert records and records[0] == {"version": 1}
    return records[1:]


def test_gold_set_schema_counts_and_spans():
    rows = _rows()
    seeded = [row for row in rows if not row.get("control", False)]
    controls = [row for row in rows if row.get("control", False)]
    assert len(seeded) == 100
    assert len(controls) == 100
    for row in seeded:
        assert set(row) == {"rule_id", "text", "defect_span", "rationale"}
        assert isinstance(row["rule_id"], str)
        assert isinstance(row["text"], str) and 40 <= len(row["text"].split()) <= 120
        assert isinstance(row["defect_span"], str)
        assert row["text"].count(row["defect_span"]) == 1
        assert isinstance(row["rationale"], str) and row["rationale"]
    for row in controls:
        assert row == {"control": True, "text": row["text"]}
        assert isinstance(row["text"], str) and 40 <= len(row["text"].split()) <= 120
        assert "defect_span" not in row


def test_every_judgement_rule_family_is_seeded():
    seeded = [row for row in _rows() if not row.get("control", False)]
    shipped = {rule.qualified_id for rule in load_ruleset([], verify=False).judgement_rules()}
    assert {row["rule_id"] for row in seeded} == shipped
