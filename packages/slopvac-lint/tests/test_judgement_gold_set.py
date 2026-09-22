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
    assert len(seeded) == 98
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

def test_shipped_gold_loads_through_prepare_and_reports_attachments(tmp_path: Path) -> None:
    from slopvac.judgement.driver import prepare

    config = Path(__file__).resolve().parents[3] / "slopvac.toml"
    document = tmp_path / "gold-fixtures.md"
    document.write_text("\n\n".join(dict.fromkeys(row["text"] for row in _rows())), encoding="utf-8")
    out = tmp_path / "run"
    manifest = prepare(config=config, out=out, paths=(document,), packs="all", max_calls=0, yes=True, gold=GOLD)
    gold = manifest["gold"]
    attachment_counts = gold["attachment_counts"]
    assert len(attachment_counts) == len(_rows())
    assert all(count >= 1 for count in attachment_counts.values())
    assert gold["unattached"] == []



def test_pathless_unmatched_gold_row_is_reported(tmp_path: Path) -> None:
    from slopvac.judgement.driver import _load_gold_rows

    document = tmp_path / "fixture.md"
    document.write_text("A different document.", encoding="utf-8")
    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        json.dumps({"rule_id": "rule.one", "text": "Missing gold text.", "defect_span": "Missing gold text."}) + "\n",
        encoding="utf-8",
    )
    _, rows = _load_gold_rows(gold, (document,))
    assert rows[0]["path"] == ""
    assert rows[0]["unattached_reason"] == "no_unique_document"
def test_every_judgement_rule_family_is_seeded():
    seeded = [row for row in _rows() if not row.get("control", False)]
    shipped = {rule.qualified_id for rule in load_ruleset([], verify=False).judgement_rules()}
    assert {row["rule_id"] for row in seeded} == shipped


def test_gold_recall_counts_confirmed_seeded_and_controls() -> None:
    from slopvac.judgement.driver import _gold_recall

    gold = [
        {"gold_id": "seed-1", "kind": "seeded", "rule_id": "rule.one", "start": 0, "end": 3},
        {"gold_id": "seed-2", "kind": "seeded", "rule_id": "rule.two", "start": 0, "end": 3},
        {"gold_id": "control-1", "kind": "control", "rule_id": "rule.one", "start": 0, "end": 3},
    ]
    units = {
        "unit-1": {"gold_id": "seed-1", "text": "one unit"},
        "unit-2": {"gold_id": "seed-2", "text": "two unit"},
        "unit-3": {"gold_id": "control-1", "gold_control": True, "text": "three unit"},
    }
    findings = [
        {"unit_id": "unit-1", "rule_id": "rule.one", "outcome": "CONFIRM", "evidence": [{"quote": "one", "start": 0, "end": 3, "source": "unit", "role": "defect"}]},
        {"unit_id": "unit-2", "rule_id": "rule.two", "outcome": "REJECT"},
        {"unit_id": "unit-3", "rule_id": "rule.one", "outcome": "REJECT"},
    ]
    recall, controls = _gold_recall(gold, units, findings)
    assert recall == {"overall": 0.5, "per_rule": {"rule.one": 1.0, "rule.two": 0.0}}
    assert controls == {"count": 0, "total": 1}


def test_gold_recall_evidence_gate_discard_is_counted() -> None:
    from slopvac.judgement.driver import _gold_recall

    gold = [{"gold_id": "seed-1", "kind": "seeded", "rule_id": "rule.one"}]
    units = {"unit-1": {"gold_id": "seed-1"}}
    findings = [{"unit_id": "unit-1", "rule_id": "rule.one", "outcome": "ABSTAIN"}]
    recall, controls = _gold_recall(gold, units, findings)
    assert recall["overall"] == 0.0
    assert controls == {"count": 0, "total": 0}

def test_gold_recall_requires_overlapping_evidence() -> None:
    from slopvac.judgement.driver import _gold_recall

    gold = [{"gold_id": "seed-1", "kind": "seeded", "rule_id": "rule.one", "start": 10, "end": 15}]
    units = {"unit-1": {"gold_id": "seed-1", "text": "wrong evidence"}}
    findings = [{
        "unit_id": "unit-1",
        "rule_id": "rule.one",
        "outcome": "CONFIRM",
        "evidence": [{"quote": "wrong", "start": 0, "end": 5, "source": "unit", "role": "defect"}],
    }]
    recall, _ = _gold_recall(gold, units, findings)
    assert recall["overall"] == 0.0


def test_gold_span_overlapping_two_units_counts_both_attachments() -> None:
    from slopvac.judgement.driver import _gold_recall

    gold = [{"gold_id": "seed-1", "kind": "seeded", "rule_id": "rule.one", "start": 6, "end": 18}]
    units = {
        "unit-1": {"gold_ids": ["seed-1"], "text": "First words."},
        "unit-2": {"gold_ids": ["seed-1"], "text": "Second sentence."},
    }
    findings = [
        {"unit_id": "unit-1", "rule_id": "rule.one", "outcome": "CONFIRM", "evidence": [{"quote": "words", "start": 6, "end": 11, "source": "unit", "role": "defect"}]},
        {"unit_id": "unit-2", "rule_id": "rule.one", "outcome": "REJECT", "evidence": []},
    ]
    recall, _ = _gold_recall(gold, units, findings)
    assert recall["overall"] == 1.0
    assert recall["multi_unit_attachments"] == 1


def test_unique_quote_salvage_is_opt_in_and_rejects_duplicates() -> None:
    from slopvac.judgement.driver import _salvage_unique_quotes

    unit = {"text": "prefix unique suffix"}
    output = {"evidence": [{"quote": "unique", "start": 0, "end": 0, "role": "defect", "source": "unit"}]}
    unchanged = {
        "evidence": [
            {"quote": "unique", "start": 0, "end": 0, "role": "antecedent", "source": "context"},
            {"quote": "unique", "start": 1, "end": 2, "role": "referent", "source": "repository"},
        ]
    }

    _salvage_unique_quotes(unit, output)
    _salvage_unique_quotes(unit, unchanged)
    assert output["evidence"][0]["start"] == 7
    assert output["evidence"][0]["end"] == 13
    assert unchanged["evidence"][0]["start"] == 0
    assert unchanged["evidence"][0]["end"] == 0
    assert unchanged["evidence"][1]["start"] == 1
    assert unchanged["evidence"][1]["end"] == 2

    duplicate = {"text": "repeat repeat"}
    duplicate_output = {"evidence": [{"quote": "repeat", "start": 1, "end": 2, "role": "defect", "source": "unit"}]}
    _salvage_unique_quotes(duplicate, duplicate_output)
    assert duplicate_output["evidence"][0]["start"] == 1
    assert duplicate_output["evidence"][0]["end"] == 2

def test_finish_defaults_to_unique_quote_and_records_none_mode(tmp_path: Path) -> None:
    from slopvac.judgement.driver import finish, prepare

    config = Path(__file__).resolve().parents[3] / "slopvac.toml"
    document = tmp_path / "fixture.md"
    document.write_text("A useful paragraph with enough words.", encoding="utf-8")

    def run(mode: str | None, out: Path) -> dict:
        prepare(config=config, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1")
        units = [json.loads(line) for line in (out / "units.jsonl").read_text(encoding="utf-8").splitlines() if line]
        calls = [json.loads(line) for line in (out / "prompts.jsonl").read_text(encoding="utf-8").splitlines() if line]
        first_unit_id = units[0]["unit_id"]
        by_id = {unit["unit_id"]: unit for unit in units}
        response_rows = []
        for call in calls:
            rows = []
            for unit_id in call["unit_ids"]:
                unit = by_id[unit_id]
                confirm = unit_id == first_unit_id
                rows.append({
                    "unit_id": unit_id, "rule_id": unit["rule_id"], "kind": unit["kind"],
                    "note": "Synthetic response.", "admissible": True,
                    "evidence": ([{"quote": unit["text"], "start": 1, "end": 1, "role": "defect", "source": "unit", "source_ref": unit_id}] if confirm else []),
                    "occurrences": None, "occurrences_truncated": False,
                    "scores": {"fit": "unambiguous_match" if confirm else "absent", "harm": "misleads_or_blocks" if confirm else "none", "repair": "local_substitution" if confirm else "inapplicable", "warrant": "quote_plus_particular" if confirm else "none"},
                    "preservation_reason": None, "abstain_reason": None,
                    "rewrite": "A revised paragraph." if confirm else None,
                    "rewrite_status": "proposed" if confirm else "not_applicable",
                    "verdict": "confirm" if confirm else "reject",
                })
            response_rows.append(json.dumps({"call_id": call["call_id"], "response": {"results": rows}}))
        response_path = out.parent / f"responses-{out.name}.jsonl"
        response_path.write_text("\n".join(response_rows) + "\n", encoding="utf-8")
        return finish(out=out, responses=response_path, **({"offset_salvage": mode} if mode is not None else {}))

    default_report = run(None, tmp_path / "default")
    none_report = run("none", tmp_path / "none")
    assert default_report["offset_salvage"] == "unique-quote"
    assert default_report["evidence_offset_mismatch"] == 0
    assert default_report["documents"][0]["coverage"]["attempted"] >= 1
    assert default_report["documents"][0]["confirmed"] == 1
    assert none_report["offset_salvage"] == "none"
    assert none_report["documents"][0]["confirmed"] == 0
    assert none_report["evidence_gate_discards"] == 1


def test_finish_counts_confirm_without_evidence_as_gate_discard(tmp_path: Path) -> None:
    from slopvac.judgement.driver import finish, prepare

    config = Path(__file__).resolve().parents[3] / "slopvac.toml"
    document = tmp_path / "fixture.md"
    document.write_text("A useful paragraph with enough words.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(config=config, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1")
    call = json.loads((out / "prompts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    units = [json.loads(line) for line in (out / "units.jsonl").read_text(encoding="utf-8").splitlines() if line]
    results = []
    for index, unit in enumerate(units):
        confirm = index == 0
        results.append(
            {
                "unit_id": unit["unit_id"],
                "rule_id": unit["rule_id"],
                "kind": unit["kind"],
                "note": "Synthetic response.",
                "admissible": True,
                "evidence": [],
                "occurrences": None,
                "occurrences_truncated": False,
                "scores": {
                    "fit": "unambiguous_match" if confirm else "absent",
                    "harm": "reader_effort" if confirm else "none",
                    "repair": "local_substitution" if confirm else "inapplicable",
                    "warrant": "quote_only" if confirm else "none",
                },
                "preservation_reason": None,
                "abstain_reason": None,
                "rewrite": "A revised paragraph." if confirm else None,
                "rewrite_status": "proposed" if confirm else "not_applicable",
                "verdict": "confirm" if confirm else "reject",
            }
        )
    responses = tmp_path / "responses.jsonl"
    responses.write_text(
        json.dumps({"call_id": call["call_id"], "response": {"results": results}}) + "\n",
        encoding="utf-8",
    )
    report = finish(out=out, responses=responses)
    assert report["evidence_gate_discards"] == 1


def test_prepare_and_finish_report_gold_recall(tmp_path: Path) -> None:
    from slopvac.judgement.driver import finish, prepare

    config = Path(__file__).resolve().parents[3] / "slopvac.toml"
    document = tmp_path / "fixture.md"
    paragraphs = (
        "First seeded paragraph has enough useful words.",
        "Second seeded paragraph has enough useful words.",
        "Control paragraph has enough useful words.",
    )
    document.write_text("\n\n".join(paragraphs), encoding="utf-8")
    gold = tmp_path / "gold.jsonl"
    gold.write_text(
        "\n".join(
            json.dumps(
                {
                    "path": str(document),
                    "text": text,
                    "rule_id": "ai-tells-structure.absolute-assertion-remainder",
                    "gold_id": gold_id,
                    "kind": kind,
                }
            )
            for text, gold_id, kind in (
                (paragraphs[0], "seed-1", "seeded"),
                (paragraphs[1], "seed-2", "seeded"),
                (paragraphs[2], "control-1", "control"),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "run"
    prepare(config=config, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1", gold=gold)
    units = [json.loads(line) for line in (out / "units.jsonl").read_text(encoding="utf-8").splitlines() if line]
    gold_units = {unit["gold_id"]: unit for unit in units if "gold_id" in unit}
    assert set(gold_units) == {"seed-1", "seed-2", "control-1"}
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    document_ref = manifest["documents"][0]["document_ref"]
    document_artifact = json.loads((out / "documents" / f"{document_ref}.json").read_text(encoding="utf-8"))
    assert {row["gold_id"] for row in document_artifact["gold_spans"]} == set(gold_units)

    def response(unit: dict[str, object]) -> dict[str, object]:
        confirm = unit.get("gold_id") == "seed-1"
        return {
            "unit_id": unit["unit_id"],
            "rule_id": unit["rule_id"],
            "kind": unit["kind"],
            "note": "Synthetic response.",
            "admissible": True,
            "evidence": (
                [{"quote": unit["text"], "start": 0, "end": len(unit["text"]), "role": "defect", "source": "unit", "source_ref": unit["unit_id"]}]
                if confirm
                else []
            ),
            "occurrences": None,
            "occurrences_truncated": False,
            "scores": {"fit": "unambiguous_match" if confirm else "absent", "harm": "reader_effort" if confirm else "none", "repair": "local_substitution" if confirm else "inapplicable", "warrant": "quote_plus_particular" if confirm else "none"},
            "preservation_reason": None,
            "abstain_reason": None,
            "rewrite": "A revised paragraph." if confirm else None,
            "rewrite_status": "proposed" if confirm else "not_applicable",
            "verdict": "confirm" if confirm else "reject",
        }

    call = json.loads((out / "prompts.jsonl").read_text(encoding="utf-8").splitlines()[0])
    response_by_id = {str(unit["unit_id"]): response(unit) for unit in units}
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": call["call_id"], "response": {"results": [response_by_id[unit_id] for unit_id in call["unit_ids"]]}}) + "\n", encoding="utf-8")
    report = finish(out=out, responses=responses)
    assert report["gold_recall"] == {"overall": 0.5, "per_rule": {"ai-tells-structure.absolute-assertion-remainder": 0.5}}
    assert report["control_false_confirms"] == {"count": 0, "total": 1}
