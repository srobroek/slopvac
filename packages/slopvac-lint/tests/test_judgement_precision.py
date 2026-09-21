"""Regression fixtures for the v2 judgement precision adjudication."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopvac.judgement.driver import finish, prepare

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "slopvac.toml"

_CASES = (
    pytest.param(
        "ai-tells-content-shape.one-point-dilution",
        "PROBE-2",
        "When the cache is stale, re-run the sync before reading generated files.",
        False,
        id="one-point-bounded-guidance-fp",
    ),
    pytest.param(
        "ai-tells-content-shape.one-point-dilution",
        "PROBE-2",
        "Determinism matters. Put another way, the same input gives the same output. Think of it as a pure function.",
        True,
        id="one-point-restatement-tp",
    ),
)


def _row(unit: dict[str, object], *, confirm: bool, quote: str) -> dict[str, object]:
    kind = str(unit["kind"])
    is_probe = kind == "PASSAGE_PROBE"
    absent_scores = {
        "fit": "absent",
        "harm": "none",
        "repair": "inapplicable",
        "warrant": "none",
    }
    result: dict[str, object] = {
        "unit_id": unit["unit_id"],
        "rule_id": unit["rule_id"],
        "kind": kind,
        "note": "Precision fixture.",
        "admissible": True,
        "evidence": None if is_probe else [],
        "occurrences": [] if is_probe else None,
        "occurrences_truncated": False,
        "scores": None if is_probe else absent_scores,
        "preservation_reason": None,
        "abstain_reason": None,
        "rewrite": None,
        "rewrite_status": "not_applicable",
        "verdict": "reject",
    }
    if confirm:
        text = str(unit["text"])
        start = text.index(quote)
        evidence = {
            "quote": quote,
            "start": start,
            "end": start + len(quote),
            "role": "defect",
            "source": "unit",
            "source_ref": unit["unit_id"],
        }
        evidence_items = [evidence]
        if unit["rule_id"] == "prose-discipline.competing-actor-terms":
            first_quote, second_quote = quote.split(". ", 1)
            first_quote += "."
            evidence_items = [
                {**evidence, "quote": first_quote, "end": start + len(first_quote)},
                {
                    **evidence,
                    "quote": second_quote,
                    "start": start + len(first_quote) + 1,
                    "end": start + len(quote),
                    "role": "contrast",
                },
            ]
        scores = {
            "fit": "unambiguous_match",
            "harm": "misleads_or_blocks",
            "repair": "local_substitution",
            "warrant": "quote_plus_particular",
        }
        if is_probe:
            result["occurrences"] = [
                {
                    "evidence": evidence_items,
                    "preservation_reason": None,
                    "abstain_reason": None,
                    "rewrite": None,
                    "rewrite_status": "not_applicable",
                    "scores": scores,
                    "verdict": "confirm",
                }
            ]
        else:
            result.update(
                {
                    "evidence": evidence_items,
                    "scores": scores,
                    "verdict": "confirm",
                }
            )
    return result


@pytest.mark.parametrize("rule_id,pack_id,quote,should_confirm", _CASES)
def test_v2_precision_fixtures_keep_sol_labels(
    tmp_path: Path,
    rule_id: str,
    pack_id: str,
    quote: str,
    should_confirm: bool,
) -> None:
    """The adjudicated bounded/code-or-list FPs stay rejected beside TPs."""
    document = tmp_path / "fixture.md"
    document.write_text(quote, encoding="utf-8")
    out = tmp_path / "run"
    prepare(config=CONFIG, out=out, paths=(document,), packs=pack_id)

    units = [
        json.loads(line)
        for line in (out / "units.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    target_units = [
        unit
        for unit in units
        if unit["rule_id"] == rule_id and quote in str(unit["text"])
    ]
    assert target_units, f"fixture quote was not admitted for {rule_id}"
    target_ids = {unit["unit_id"] for unit in target_units}
    by_id = {unit["unit_id"]: unit for unit in units}

    response_rows = []
    for prompt_line in (out / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
        if not prompt_line:
            continue
        prompt = json.loads(prompt_line)
        rows = []
        for unit_id in prompt["unit_ids"]:
            unit = by_id[unit_id]
            rows.append(
                _row(
                    unit,
                    confirm=should_confirm and unit_id in target_ids,
                    quote=quote,
                )
            )
        response_rows.append(
            {"call_id": prompt["call_id"], "response": {"results": rows}}
        )

    responses = tmp_path / "responses.jsonl"
    responses.write_text(
        "".join(json.dumps(row) + "\n" for row in response_rows),
        encoding="utf-8",
    )
    report = finish(out=out, responses=responses)
    assert report["documents"][0]["confirmed"] == (1 if should_confirm else 0)
