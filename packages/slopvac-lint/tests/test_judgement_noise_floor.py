from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "judgement_noise_floor.py"
spec = importlib.util.spec_from_file_location("judgement_noise_floor", SCRIPT)
assert spec and spec.loader
noise = importlib.util.module_from_spec(spec)
spec.loader.exec_module(noise)


def _model_row(unit_id: str, rule_id: str, verdict: str) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "rule_id": rule_id,
        "kind": "SPAN_CANDIDATE",
        "note": "valid",
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
        "abstain_reason": None,
        "rewrite": None,
        "rewrite_status": "not_applicable",
        "verdict": verdict.lower(),
    }


def _fixture(
    tmp_path: Path, responses: list[dict[str, object]] | None = None
) -> tuple[Path, Path, Path]:
    prompts, response_path, out = (
        tmp_path / "prompts.jsonl",
        tmp_path / "responses.jsonl",
        tmp_path / "out",
    )
    rows = [
        {
            "call_id": f"c#r{i}",
            "repeat_of": "c",
            "repeat_index": i,
            "unit_ids": ["u"],
            "rule_ids": ["R"],
            "kind": "SPAN_CANDIDATE",
            "prompt": {"user": "same"},
            "model_id": "model",
            "inference_config": {"maxTokens": 10},
        }
        for i in (1, 2, 3)
    ]
    prompts.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    response_rows = responses or [
        {
            "call_id": row["call_id"],
            "response": {
                "results": [
                    _model_row(
                        "u", "R", "reject" if row["repeat_index"] != 1 else "confirm"
                    )
                ]
            },
        }
        for row in rows
    ]
    response_path.write_text(
        "\n".join(json.dumps(row) for row in response_rows) + "\n", encoding="utf-8"
    )
    return prompts, response_path, out


def test_flip_rate_counts_modal_disagreement() -> None:
    assert noise.flip_rate(["CONFIRM", "CONFIRM", "CONFIRM"]) == 0
    assert noise.flip_rate(["CONFIRM", "REJECT", "REJECT"]) == 1 / 3
    assert noise.flip_rate(["CONFIRM", "REJECT", "ABSTAIN"]) == 2 / 3


def test_fingerprint_changes_when_prompt_bytes_differ() -> None:
    row = {
        "model_id": "model",
        "inference_config": {"maxTokens": 10},
        "prompt_bytes_sha256": "a" * 64,
        "response_schema": {"type": "object"},
    }
    changed = {**row, "prompt_bytes_sha256": "b" * 64}
    assert noise._fingerprint(row, None) != noise._fingerprint(changed, None)


def test_failure_unit_repeats_differ_from_incomplete_units(tmp_path: Path) -> None:
    prompts, responses, out = _fixture(
        tmp_path,
        [
            {"call_id": "c#r1", "error": "throttled"},
            {"call_id": "c#r2", "error": "throttled"},
            {
                "call_id": "c#r3",
                "response": {"results": [_model_row("u", "R", "reject")]},
            },
        ],
    )
    noise.analyse(
        type(
            "Args",
            (),
            {
                "prompts": prompts,
                "responses": responses,
                "out_dir": out,
                "run_config": None,
            },
        )()
    )
    report = json.loads((out / "noise-floor.json").read_text(encoding="utf-8"))
    assert report["failure_unit_repeats"]["provider_error"] == 2
    assert report["incomplete_units"]["provider_error"] == 1
    assert report["failure_unit_repeat_denominator"] == 3
    assert report["incomplete_unit_denominator"] == 1


def test_prepare_persists_model_and_inference_config(tmp_path: Path) -> None:
    prompts, _, _ = _fixture(tmp_path)
    registration, out = tmp_path / "subsample.json", tmp_path / "repeat-prompts.jsonl"
    registration.write_text(json.dumps({"call_ids": ["c#r1"]}), encoding="utf-8")
    noise.prepare(
        type(
            "Args",
            (),
            {
                "prompts": prompts,
                "subsample": registration,
                "out": out,
                "model_id": "model-x",
                "max_tokens": 32000,
            },
        )()
    )
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert {row["model_id"] for row in rows} == {"model-x"}
    assert all(row["inference_config"] == {"maxTokens": 32000} for row in rows)


def test_analyse_reports_measurement_without_decision(tmp_path: Path) -> None:
    prompts, responses, out = _fixture(tmp_path)
    noise.analyse(
        type(
            "Args",
            (),
            {
                "prompts": prompts,
                "responses": responses,
                "out_dir": out,
                "run_config": None,
            },
        )()
    )
    report = json.loads((out / "noise-floor.json").read_text(encoding="utf-8"))
    assert report["complete_units"] == 1
    assert report["overall_flip_rate"] == 1 / 3
    assert all("decision" not in rule for rule in report["rules"])


def test_analyse_excludes_incomplete_units_and_counts_failures(tmp_path: Path) -> None:
    prompts, responses, out = _fixture(
        tmp_path,
        [
            {"call_id": "c#r1", "error": "throttled"},
            {"call_id": "c#r2", "response": {"bad": True}},
            {
                "call_id": "c#r3",
                "response": {"results": [_model_row("u", "R", "reject")]},
            },
        ],
    )
    noise.analyse(
        type(
            "Args",
            (),
            {
                "prompts": prompts,
                "responses": responses,
                "out_dir": out,
                "run_config": None,
            },
        )()
    )
    report = json.loads((out / "noise-floor.json").read_text(encoding="utf-8"))
    assert report["complete_units"] == 0
    assert report["failure_classes"]["provider_error"] == 1
    assert report["failure_classes"]["unknown_unit"] == 1
    assert report["failure_unit_repeats"] == report["failure_classes"]
    assert report["incomplete_units"] == {"provider_error": 1, "unknown_unit": 1}
    assert report["rules"][0]["failure_classes"] == {
        "provider_error": 1,
        "unknown_unit": 1,
    }
    assert report["rules"][0]["incomplete_units"] == {
        "provider_error": 1,
        "unknown_unit": 1,
    }


def test_analyse_requires_model_config(tmp_path: Path) -> None:
    prompts, responses, out = _fixture(tmp_path)
    rows = [json.loads(line) for line in prompts.read_text().splitlines()]
    for row in rows:
        row.pop("model_id")
        row.pop("inference_config")
    prompts.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="missing required fingerprint fields"):
        noise.analyse(
            type(
                "Args",
                (),
                {
                    "prompts": prompts,
                    "responses": responses,
                    "out_dir": out,
                    "run_config": None,
                },
            )()
        )


def test_analyse_accepts_legacy_rows_with_run_config(tmp_path: Path) -> None:
    prompts, responses, out = _fixture(tmp_path)
    rows = [json.loads(line) for line in prompts.read_text().splitlines()]
    for row in rows:
        row.pop("model_id")
        row.pop("inference_config")
    prompts.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    sidecar = tmp_path / "run-config.json"
    sidecar.write_text(
        json.dumps(
            {
                "model_id": "model",
                "inference_config": {"maxTokens": 10},
                "source": "supervisor",
            }
        ),
        encoding="utf-8",
    )
    noise.analyse(
        type(
            "Args",
            (),
            {
                "prompts": prompts,
                "responses": responses,
                "out_dir": out,
                "run_config": sidecar,
            },
        )()
    )
    report = json.loads((out / "noise-floor.json").read_text(encoding="utf-8"))
    assert report["config_provenance"] == ["supervisor"]


def test_decide_threshold_and_min_units_boundaries(tmp_path: Path) -> None:
    report = tmp_path / "noise-floor.json"
    out = tmp_path / "variance-policy.json"
    report.write_text(
        json.dumps(
            {
                "overall_flip_rate": 0.1,
                "complete_units": 30,
                "rules": [{"rule_id": "R", "flip_rate": 0.1, "complete_units": 30}],
            }
        ),
        encoding="utf-8",
    )
    noise.decide(
        type(
            "Args",
            (),
            {"noise_floor": report, "threshold": 0.1, "min_units": 30, "out": out},
        )()
    )
    policy = json.loads(out.read_text())
    assert policy["decision"] == "single-call"
    assert policy["applies_to"] == "CONFIRM"
    report.write_text(
        json.dumps(
            {
                "overall_flip_rate": 0.11,
                "complete_units": 29,
                "rules": [{"rule_id": "R", "flip_rate": 0.11, "complete_units": 29}],
            }
        ),
        encoding="utf-8",
    )
    noise.decide(
        type(
            "Args",
            (),
            {"noise_floor": report, "threshold": 0.1, "min_units": 30, "out": out},
        )()
    )
    assert json.loads(out.read_text())["decision"] == "single-call"
