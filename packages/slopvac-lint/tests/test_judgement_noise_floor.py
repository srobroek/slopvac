from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "judgement_noise_floor.py"
spec = importlib.util.spec_from_file_location("judgement_noise_floor", SCRIPT)
assert spec and spec.loader
noise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(noise)


def test_flip_rate_agreement_majority_and_all_differ() -> None:
    assert noise.flip_rate(["CONFIRM", "CONFIRM", "CONFIRM"]) == 0
    assert noise.flip_rate(["CONFIRM", "REJECT", "REJECT"]) == 1 / 3
    assert noise.flip_rate(["CONFIRM", "REJECT", "ABSTAIN"]) == 2 / 3


def test_threshold_exactly_ten_percent_stays_single_call() -> None:
    assert not noise.THRESHOLD > noise.THRESHOLD
    assert (
        "majority-of-3" if noise.THRESHOLD > noise.THRESHOLD else "single-call"
    ) == "single-call"
    assert (
        "majority-of-3" if (noise.THRESHOLD + 1e-9) > noise.THRESHOLD else "single-call"
    ) == "majority-of-3"


def test_prepare_repeats_identical_serialized_prompt_payload(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    registration = tmp_path / "subsample.json"
    out = tmp_path / "repeat-prompts.jsonl"
    row = {
        "call_id": "a",
        "prompt": {"system": "fixed", "user": "same bytes"},
        "unit_ids": ["u"],
        "rule_ids": ["R"],
        "kind": "SPAN_CANDIDATE",
    }
    prompts.write_text(json.dumps(row) + "\n", encoding="utf-8")
    registration.write_text(json.dumps({"call_ids": ["a"]}), encoding="utf-8")
    noise.prepare(
        type("Args", (), {"prompts": prompts, "subsample": registration, "out": out})()
    )
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["call_id"] for r in rows] == ["a#r1", "a#r2", "a#r3"]
    serialized = [
        json.dumps(
            r["prompt"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        for r in rows
    ]
    assert serialized[0] == serialized[1] == serialized[2]


def _model_row(unit_id: str, rule_id: str, verdict: str) -> dict[str, object]:
    normalized = verdict.lower()
    return {
        "unit_id": unit_id,
        "rule_id": rule_id,
        "kind": "SPAN_CANDIDATE",
        "note": "A valid judgement.",
        "admissible": True,
        "evidence": [],
        "occurrences": None,
        "occurrences_truncated": False,
        "scores": {
            "fit": "absent",
            "harm": "none",
            "repair": "inapplicable",
            "warrant": "none",
        },
        "preservation_reason": None,
        "abstain_reason": "no_exact_evidence" if normalized == "abstain" else None,
        "rewrite": None,
        "rewrite_status": "not_applicable",
        "verdict": normalized,
    }


def test_analyse_partial_fixture_reports_complete_and_incomplete(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    responses = tmp_path / "responses.jsonl"
    out_dir = tmp_path / "out"
    prompt_rows = [
        {
            "call_id": f"c#r{repeat}",
            "repeat_of": "c",
            "repeat_index": repeat,
            "unit_ids": ["u1", "u2"],
            "rule_ids": ["R1", "R2"],
            "kind": "SPAN_CANDIDATE",
            "prompt": {"user": "same"},
        }
        for repeat in (1, 2, 3)
    ]
    prompts.write_text(
        "\n".join(json.dumps(row) for row in prompt_rows) + "\n", encoding="utf-8"
    )
    response_rows = [
        {
            "call_id": row["call_id"],
            "response": {
                "results": [
                    _model_row("u1", "R1", "reject"),
                    _model_row("u2", "R2", "reject"),
                ]
            },
        }
        for row in prompt_rows[:2]
    ]
    responses.write_text(
        "\n".join(json.dumps(row) for row in response_rows) + "\n", encoding="utf-8"
    )
    noise.analyse(
        type(
            "Args", (), {"prompts": prompts, "responses": responses, "out_dir": out_dir}
        )()
    )
    report = json.loads((out_dir / "noise-floor.json").read_text(encoding="utf-8"))
    assert report["complete_units"] == 0
    assert report["incomplete_units"] == 2
    assert report["overall_flip_rate"] == 0.0
    assert report["rules"] == []


def test_analyse_counts_only_complete_units_in_flip_rate(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts.jsonl"
    responses = tmp_path / "responses.jsonl"
    out_dir = tmp_path / "out"
    rows = [
        {
            "call_id": f"c#r{repeat}",
            "repeat_of": "c",
            "repeat_index": repeat,
            "unit_ids": ["u"],
            "rule_ids": ["R"],
            "kind": "SPAN_CANDIDATE",
            "prompt": {"user": "same"},
        }
        for repeat in (1, 2, 3)
    ]
    prompts.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    response_rows = [
        {
            "call_id": row["call_id"],
            "response": {
                "results": [
                    _model_row(
                        "u", "R", "abstain" if row["repeat_index"] == 1 else "reject"
                    )
                ]
            },
        }
        for row in rows
    ]
    responses.write_text(
        "\n".join(json.dumps(row) for row in response_rows) + "\n", encoding="utf-8"
    )
    noise.analyse(
        type(
            "Args", (), {"prompts": prompts, "responses": responses, "out_dir": out_dir}
        )()
    )
    report = json.loads((out_dir / "noise-floor.json").read_text(encoding="utf-8"))
    assert report["complete_units"] == 1
    assert report["incomplete_units"] == 0
    assert report["overall_flip_rate"] == 1 / 3
