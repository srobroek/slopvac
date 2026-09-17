from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from slopvac.analyze import parse
from slopvac.judgement.driver import (
    _admission,
    _preview_document,
    _unit_from_block,
    _unit_from_sentence,
    compare,
    finish,
    prepare,
)
from slopvac.judgement.packs import Pack
from slopvac.judgement.schema import validate_model_output
from slopvac.projection import project

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "slopvac.toml"


def test_prepare_writes_units_and_bounded_json_prompts(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text(
        "First authored paragraph.\n\n> Quoted specimen.\n\n```python\nprint('code')\n```\n\nFinal paragraph.",
        encoding="utf-8",
    )
    out = tmp_path / "run"
    manifest = prepare(config=CONFIG, out=out, paths=(document,), packs="all")
    prompts = [json.loads(line) for line in (out / "prompts.jsonl").read_text().splitlines() if line]
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    assert manifest["counts"]["documents"] == 1
    assert prompts and all(len(prompt["unit_ids"]) <= 20 for prompt in prompts)
    assert all(isinstance(prompt["prompt"], dict) for prompt in prompts)
    assert all(prompt["response_schema"] for prompt in prompts)
    assert all("projection" not in unit for unit in units)
    assert (out / "deterministic").is_dir()


def test_finish_records_missing_calls_and_compare_shows_both_scores(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text("A useful paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(document,), packs="all")
    responses = tmp_path / "responses.jsonl"
    responses.write_text("", encoding="utf-8")
    report = finish(out=out, responses=responses)
    assert report["documents"][0]["deterministic_score"] >= 0
    assert "coverage" in report
    text = compare(out=out, doc=document)
    assert "deterministic (old): score=" in text
    assert "judgement (new): score=" in text


def test_finish_counts_failed_responses_in_coverage(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text("A useful authored paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(
        config=CONFIG,
        out=out,
        paths=(document,),
        packs="PROBE-4",
        categories=("ai-tells-register", "ai-tells-structure"),
    )
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    call = json.loads((out / "prompts.jsonl").read_text().splitlines()[0])
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": call["call_id"], "response": "{bad"}) + "\n", encoding="utf-8")
    report = finish(out=out, responses=responses)
    coverage = report["coverage"]["documents"][str(document)]
    assert coverage["failed"] == len(units)
    assert coverage["not_run"] == 0

def test_span_calls_group_passages_and_rules(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text("One authored paragraph.\n\nTwo authored paragraph.\n\nThree authored paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    manifest = prepare(config=CONFIG, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1")
    prompts = [json.loads(line) for line in (out / "prompts.jsonl").read_text().splitlines() if line]
    assert manifest["counts"]["calls"] == 1
    assert len(prompts[0]["unit_ids"]) == 12
    payload = json.loads(prompts[0]["prompt"]["user"])
    assert len(payload["passages"]) == 3
    assert len(payload["pairs"]) == 12
    assert [pair["unit_id"] for pair in payload["pairs"]] == prompts[0]["unit_ids"]


def test_probe_units_have_rule_identity_and_finish_coverage(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text("A useful paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(
        config=CONFIG,
        out=out,
        paths=(document,),
        packs="PROBE-4",
        categories=("ai-tells-register", "ai-tells-structure"),
    )
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    assert len(units) == 2
    assert len({unit["unit_id"] for unit in units}) == 2
    assert len({unit["rule_id"] for unit in units}) == 2
    call = json.loads((out / "prompts.jsonl").read_text().splitlines()[0])
    assert "results" in call["response_schema"]["properties"]
    rows = []
    for unit in units:
        rows.append(
            {
                "unit_id": unit["unit_id"],
                "rule_id": unit["rule_id"],
                "kind": "PASSAGE_PROBE",
                "note": "No occurrence.",
                "admissible": True,
                "evidence": None,
                "occurrences": [],
                "occurrences_truncated": False,
                "scores": None,
                "preservation_reason": None,
                "abstain_reason": None,
                "rewrite": None,
                "rewrite_status": "not_applicable",
                "verdict": "reject",
            }
        )
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": call["call_id"], "response": {"results": rows}}) + "\n", encoding="utf-8")
    report = finish(out=out, responses=responses)
    assert set(report["coverage"]["rules"]) == {unit["rule_id"] for unit in units}


def test_units_keep_raw_code_spans_for_evidence(tmp_path: Path) -> None:
    document_path = tmp_path / "fixture.md"
    raw = "A paragraph with `code` span."
    document_path.write_text(raw, encoding="utf-8")
    document = parse(str(document_path), raw)
    projected, projection = project(raw)
    document._judgement_text = projected  # type: ignore[attr-defined]
    document._judgement_projection = projection  # type: ignore[attr-defined]
    block = document.blocks[0]
    pack = Pack("demo", (), 1, "local", (), ("demo.rule",))
    unit = _unit_from_sentence(document, block, block.sentences[0], 0, "demo.rule", pack)
    assert "`code`" in unit.text
    assert "\x00" not in unit.text
    quote = "`code`"
    start = unit.text.index(quote)
    output = {
        "unit_id": unit.unit_id,
        "rule_id": unit.rule_id,
        "kind": unit.kind,
        "note": "Code span evidence.",
        "admissible": True,
        "evidence": [{"quote": quote, "start": start, "end": start + len(quote), "role": "defect", "source": "unit", "source_ref": unit.unit_id}],
        "occurrences": None,
        "occurrences_truncated": False,
        "scores": {"fit": "unambiguous_match", "harm": "none", "repair": "inapplicable", "warrant": "quote_only"},
        "preservation_reason": None,
        "abstain_reason": None,
        "rewrite": None,
        "rewrite_status": "not_applicable",
        "verdict": "reject",
    }
    assert validate_model_output(output) == []


def test_heading_and_nonzero_offset_units_keep_source_text(tmp_path: Path) -> None:
    raw = "# Intro\n\nA paragraph with `code` span."
    document_path = tmp_path / "fixture.md"
    document_path.write_text(raw, encoding="utf-8")
    document = parse(str(document_path), raw)
    projected, projection = project(raw)
    document._judgement_text = projected  # type: ignore[attr-defined]
    document._judgement_projection = projection  # type: ignore[attr-defined]
    pack = Pack("demo", (), 1, "local", (), ("demo.rule",))
    heading_unit = _unit_from_block(document, document.blocks[0], "demo.rule", pack)[0]
    paragraph = document.blocks[1]
    paragraph_unit = _unit_from_sentence(document, paragraph, paragraph.sentences[0], 0, "demo.rule", pack)
    assert heading_unit.text.strip() == "Intro"
    assert paragraph_unit.doc_range[0] > 0
    assert paragraph_unit.text == "A paragraph with `code` span."
    assert "\x00" not in paragraph_unit.text


def test_finish_records_malformed_response_call(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text("A useful paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1")
    call = json.loads((out / "prompts.jsonl").read_text().splitlines()[0])
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": call["call_id"], "response": "{bad"}) + "\n", encoding="utf-8")
    report = finish(out=out, responses=responses)
    assert report["failed"]
    assert report["failed"][0]["call_id"] == call["call_id"]
    assert "response_json" in report["failed"][0]["errors"][0]


def test_fenced_block_followed_by_paragraph_maps_source(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    document.write_text(
        "Intro.\n\n```sh\nuvx slopvac lint README.md\n```\n\nAfter the fence.\n\n| A | B |\n|---|---|\n| one | two |\n",
        encoding="utf-8",
    )
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1")
    rows = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    after = [row for row in rows if "After the fence." in row["text"]]
    assert after
    assert all("\x00" not in row["text"] for row in after)
    assert all(row["doc_range"][0] > 0 for row in after)


def test_readme_units_match_document_source_ranges(tmp_path: Path) -> None:
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(ROOT / "README.md",), packs="SPAN-ai-tells-structure-1", yes=True)
    manifest = json.loads((out / "manifest.json").read_text())
    document_ref = manifest["documents"][0]["document_ref"]
    document = json.loads((out / "documents" / f"{document_ref}.json").read_text())
    raw = document["text"].encode("utf-8")
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    for unit in units:
        source = raw[unit["source_range"][0] : unit["source_range"][1]].decode("utf-8")
        if unit.get("admission_reason") == "a2_text_unavailable":
            assert unit["kind"] == "SPAN_CANDIDATE"
            assert source.strip() == ""
        else:
            assert unit["text"]
            assert source == unit["text"]
            previous = raw[: unit["source_range"][0]].decode("utf-8")[-1:]
            if unit["text"][0].isalpha():
                assert not previous.isalnum()


def test_table_block_yields_cell_units_only(tmp_path: Path) -> None:
    raw = "| A | B |\n|---|---|\n| C | D |\n| E | F |\n"
    document_path = tmp_path / "table.md"
    document_path.write_text(raw, encoding="utf-8")
    document = parse(str(document_path), raw)
    projected, projection = project(raw)
    document._judgement_text = projected  # type: ignore[attr-defined]
    document._judgement_projection = projection  # type: ignore[attr-defined]
    table = next(block for block in document.blocks if block.kind.value == "table")
    pack = Pack("demo", (), 1, "local", (), ("demo.rule",))
    units = _unit_from_block(document, table, "demo.rule", pack)
    assert [unit.text for unit in units] == ["A", "B", "C", "D", "E", "F"]
    assert all("|" not in unit.text for unit in units)
    cell = units[2]
    quote = "C"
    assert cell.text == quote
    assert cell.projection.slice_raw(0, len(quote)).decode("utf-8") == quote


def test_numeric_table_cells_are_not_units(tmp_path: Path) -> None:
    raw = "| 0 | 5 |\n|---|---|\n| 70 | ! |\n"
    document_path = tmp_path / "numeric.md"
    document_path.write_text(raw, encoding="utf-8")
    document = parse(str(document_path), raw)
    projected, projection = project(raw)
    document._judgement_text = projected  # type: ignore[attr-defined]
    document._judgement_projection = projection  # type: ignore[attr-defined]
    table = next(block for block in document.blocks if block.kind.value == "table")
    pack = Pack("demo", (), 1, "local", (), ("demo.rule",))
    assert _unit_from_block(document, table, "demo.rule", pack) == []


def _admission_unit(text: str, *, document_text: str | None = None, raw_start: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        origin="authored",
        region_class="authored",
        document_text=document_text or text,
        projection=SimpleNamespace(segments=(SimpleNamespace(raw_start=raw_start),)),
    )


def test_admission_drops_fragment_units_but_keeps_three_words() -> None:
    pack = Pack("demo", (), 1, "local", ("normative_obligation",), ("demo.rule",))
    fragments = (
        _admission_unit("MUST At"),
        _admission_unit("A"),
        _admission_unit("A B"),
        _admission_unit("# Alpha beta gamma"),
        _admission_unit("alpha beta gamma", document_text="prefixalpha beta gamma", raw_start=6),
    )
    assert [_admission(unit, pack) for unit in fragments] == [
        ("DROP", "a2_fragment_unit"),
        ("DROP", "a2_fragment_unit"),
        ("DROP", "a2_fragment_unit"),
        ("DROP", "a2_fragment_unit"),
        ("DROP", "a2_fragment_unit"),
    ]
    assert _admission(_admission_unit("One useful sentence"), pack) == ("ELIGIBLE", None)


def test_admission_preserves_normative_register() -> None:
    pack = Pack("demo", (), 1, "local", ("normative_obligation",), ("demo.rule",))
    assert _admission(_admission_unit("MUST reject malformed input"), pack) == (
        "PRESERVE",
        "normative_obligation",
    )
    assert _admission(_admission_unit("The parser rejects input"), pack) == ("ELIGIBLE", None)


def _result_row(unit: dict[str, object]) -> dict[str, object]:
    kind = str(unit["kind"])
    return {
        "unit_id": unit["unit_id"],
        "rule_id": unit["rule_id"],
        "kind": kind,
        "note": "No occurrence.",
        "admissible": True,
        "evidence": None,
        "occurrences": [] if kind == "PASSAGE_PROBE" else None,
        "occurrences_truncated": False,
        "scores": None,
        "preservation_reason": None,
        "abstain_reason": None,
        "rewrite": None,
        "rewrite_status": "not_applicable",
        "verdict": "reject",
    }


def test_preview_replaces_one_span_and_keeps_absolute_source_inside_output(tmp_path: Path) -> None:
    source = tmp_path / "nested" / "README.md"
    source.parent.mkdir()
    source.write_text("before old after\n", encoding="utf-8")
    out = tmp_path / "run"
    unit = {"unit_id": "unit-1", "text": "old", "source_range": [7, 10], "path": str(source)}
    finding = {"unit_id": "unit-1", "rewrite_status": "proposed", "rewrite": "new"}
    skipped: list[str] = []
    target = _preview_document(out, str(source), [finding], {"unit-1": unit}, skipped)
    assert target.read_text(encoding="utf-8") == "before new after\n"
    assert target != source
    assert target.resolve().is_relative_to(out.resolve())
    assert skipped == []


def test_preview_skips_duplicate_span_and_reports_it(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    source.write_text("before old after\n", encoding="utf-8")
    out = tmp_path / "run"
    units = {
        "unit-1": {"unit_id": "unit-1", "text": "old", "source_range": [7, 10], "path": str(source)},
        "unit-2": {"unit_id": "unit-2", "text": "old", "source_range": [7, 10], "path": str(source)},
    }
    findings = [
        {"unit_id": "unit-1", "rewrite_status": "proposed", "rewrite": "first"},
        {"unit_id": "unit-2", "rewrite_status": "proposed", "rewrite": "second"},
    ]
    skipped: list[str] = []
    target = _preview_document(out, str(source), findings, units, skipped)
    assert target.read_text(encoding="utf-8") == "before first after\n"
    assert any("duplicate span" in item for item in skipped)


@pytest.mark.parametrize(
    ("packs", "kind"),
    [("PROBE-4", "PASSAGE_PROBE"), ("SPAN-ai-tells-structure-1", "SPAN_CANDIDATE")],
)
def test_finish_flags_omitted_probe_or_span_rows(tmp_path: Path, packs: str, kind: str) -> None:
    document = tmp_path / "fixture.md"
    document.write_text("First authored paragraph.\n\nSecond authored paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(document,), packs=packs)
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    matching = [unit for unit in units if unit["kind"] == kind]
    assert len(matching) >= 2
    call = json.loads((out / "prompts.jsonl").read_text().splitlines()[0])
    omitted = matching[1]
    rows = [_result_row(matching[0])]
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": call["call_id"], "response": {"results": rows}}) + "\n", encoding="utf-8")
    report = finish(out=out, responses=responses)
    missing = [item for item in report["failed"] if item.get("reason") == "row_missing"]
    call_missing = [item for item in missing if item["call_id"] == call["call_id"]]
    assert len(call_missing) == 1
    assert len(call_missing[0]["unit_ids"]) == len(call["unit_ids"]) - 1
    assert any(omitted["unit_id"] in item["unit_ids"] for item in call_missing)

def test_finish_uses_projected_paragraph_boundaries_for_cluster_gate(tmp_path: Path) -> None:
    document = tmp_path / "fixture.md"
    prefix = "[prefix](https://" + "x" * 200 + ")"
    document.write_text(
        prefix + "\n\nFirst target sentence.\n\nSecond target sentence.\n\nThird target sentence.",
        encoding="utf-8",
    )
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(document,), packs="SPAN-ai-tells-structure-1")
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    call = json.loads((out / "prompts.jsonl").read_text().splitlines()[0])
    selected_rule = "ai-tells-structure.absolute-assertion-remainder"
    targets = {"First target sentence.", "Second target sentence.", "Third target sentence."}
    rows = []
    units_by_id = {unit["unit_id"]: unit for unit in units}
    for unit_id in call["unit_ids"]:
        unit = units_by_id[unit_id]
        row = _result_row(unit)
        if unit["rule_id"] == selected_rule and unit["text"] in targets:
            quote = str(unit["text"])
            row.update(
                {
                    "evidence": [{"quote": quote, "start": 0, "end": len(quote), "role": "defect", "source": "unit", "source_ref": unit["unit_id"]}],
                    "occurrences": None,
                    "scores": {"fit": "unambiguous_match", "harm": "misleads_or_blocks", "repair": "local_substitution", "warrant": "quote_plus_particular"},
                    "verdict": "confirm",
                }
            )
        else:
            row.update(
                {
                    "evidence": [],
                    "occurrences": None,
                    "scores": {"fit": "absent", "harm": "none", "repair": "inapplicable", "warrant": "none"},
                }
            )
        rows.append(row)
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": call["call_id"], "response": {"results": rows}}) + "\n", encoding="utf-8")
    report = finish(out=out, responses=responses)
    assert report["documents"][0]["confirmed"] == 3
    assert report["documents"][0]["cluster_gate"] is None


def test_prepare_uses_path_unique_document_store_files(tmp_path: Path) -> None:
    first = tmp_path / "a" / "b__c.md"
    second = tmp_path / "a__b" / "c.md"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("First document paragraph.", encoding="utf-8")
    second.write_text("Second document paragraph.", encoding="utf-8")
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(first, second), packs="SPAN-ai-tells-structure-1")
    manifest = json.loads((out / "manifest.json").read_text())
    refs = [str(doc["document_ref"]) for doc in manifest["documents"]]
    assert len(refs) == 2
    assert len(set(refs)) == 2
    stores = [json.loads((out / "documents" / f"{ref}.json").read_text()) for ref in refs]
    assert {store["text"] for store in stores} == {first.read_text(), second.read_text()}
    units = [json.loads(line) for line in (out / "units.jsonl").read_text().splitlines() if line]
    for unit in units:
        store = json.loads((out / "documents" / f"{unit['document_ref']}.json").read_text())
        raw = store["text"].encode("utf-8")
        assert raw[unit["source_range"][0] : unit["source_range"][1]].decode("utf-8") == unit["text"]
    finish(out=out, responses=tmp_path / "responses.jsonl")
