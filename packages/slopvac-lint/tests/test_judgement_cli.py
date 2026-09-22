"""Behavioural tests for `slopvac judgement validate` and `slopvac judgement brief`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from slopvac.cli import main

FIRED_DOC = """# Notes

In today's fast-paced digital landscape, observability isn't just a nice-to-have.
It's a game-changer that empowers teams to leverage synergies.

In conclusion, embracing observability is a strategic imperative.
"""

CLEAN_DOC = """# Cache

Each entry stays cached for 60 seconds.

Run the migration.
"""


def _brief(tmp_path: Path, text: str, *args: str) -> tuple[Path, Result]:
    doc = tmp_path / "doc.md"
    doc.write_text(text, encoding="utf-8")
    out = tmp_path / "run"
    result = CliRunner().invoke(
        main, ["judgement", "brief", str(doc), "--out", str(out), *args]
    )
    return out, result


def _reject_row(unit: dict, kind: str) -> dict:
    return {
        "unit_id": unit["unit_id"],
        "rule_id": unit["rule_id"],
        "kind": kind,
        "admissible": True,
        "note": "no defect in this unit",
        "rewrite_status": "not_applicable",
        "occurrences_truncated": False,
        "scores": {
            "fit": "absent",
            "harm": "none",
            "repair": "inapplicable",
            "warrant": "quote_only",
        },
        "verdict": "reject",
        "abstain_reason": None,
        "preservation_reason": None,
        "rewrite": None,
        "evidence": [],
        "occurrences": None,
    }


def _valid_response(out: Path) -> tuple[str, dict]:
    prompts = [
        json.loads(line)
        for line in (out / "prompts.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    units = {
        u["unit_id"]: u
        for u in (
            json.loads(line)
            for line in (out / "units.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }
    call = prompts[0]
    rows = [_reject_row(units[uid], call["kind"]) for uid in call["unit_ids"]]
    return call["call_id"], {"results": rows}


def _validate(out: Path, payload: object, *args: str) -> tuple[int, dict, str]:
    result = CliRunner().invoke(
        main,
        ["judgement", "validate", "--run", str(out), *args],
        input=json.dumps(payload),
    )
    return result.exit_code, json.loads(result.stdout), result.stderr


@pytest.fixture(scope="module")
def fired_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out, result = _brief(tmp_path_factory.mktemp("fired"), FIRED_DOC)
    assert result.exit_code == 0, result.output
    return out


def test_brief_fired_selects_only_packs_whose_category_fired(fired_run: Path) -> None:
    brief = json.loads((fired_run / "brief.json").read_text(encoding="utf-8"))
    deterministic = json.loads(
        next((fired_run / "deterministic").glob("*.json")).read_text(encoding="utf-8")
    )
    fired = {f["category"] for f in deterministic["findings"]}
    assert brief["packs"], "a document with findings selects at least one pack"
    for pack_id in brief["packs"]:
        category = pack_id.removeprefix("SPAN-").rsplit("-", 1)[0]
        assert category in fired, pack_id
    prompts = (fired_run / "prompts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(brief["calls"]) == len(prompts)
    text = (fired_run / "brief.md").read_text(encoding="utf-8")
    assert text.count("### call ") == len(prompts)
    assert text.count("## Response schema") == 1
    assert text.rstrip().endswith("Respond with the JSON object only.")


def test_brief_clean_document_falls_back_to_every_pack_with_warning(
    tmp_path: Path,
) -> None:
    out, result = _brief(tmp_path, CLEAN_DOC)
    assert result.exit_code == 0, result.output
    assert "every pack was kept" in result.stderr
    brief = json.loads((out / "brief.json").read_text(encoding="utf-8"))
    assert len(brief["packs"]) > 7, brief["packs"]


def test_validate_accepts_a_valid_response_and_infers_the_call(fired_run: Path) -> None:
    call_id, payload = _valid_response(fired_run)
    code, report, _ = _validate(fired_run, payload)
    assert (code, report["ok"], report["call_id"], report["errors"]) == (
        0,
        True,
        call_id,
        [],
    )


def test_validate_rejects_schema_drift_with_exit_2_and_hook_instruction(
    fired_run: Path,
) -> None:
    call_id, payload = _valid_response(fired_run)
    payload["results"][0]["scores"]["repair"] = "safe deletion"
    payload["results"][0]["evidence"] = [
        {"quote": "x", "offsets": [0, 1], "role": "defect"}
    ]
    code, report, stderr = _validate(
        fired_run, {"call_id": call_id, "response": payload}, "--hook"
    )
    assert code == 2
    assert report["ok"] is False and report["call_id"] == call_id
    assert any("safe deletion" in e or "safe_deletion" in e for e in report["errors"])
    assert any("offsets" in e for e in report["errors"])
    assert "rejected" in stderr and "offsets" in stderr


def test_validate_unwraps_a_subagent_stop_payload_with_a_fenced_object(
    fired_run: Path,
) -> None:
    call_id, payload = _valid_response(fired_run)
    hook_payload = {
        "hook_event_name": "SubagentStop",
        "agent_type": "slopvac-judge",
        "stop_hook_active": False,
        "last_assistant_message": "Done.\n```json\n" + json.dumps(payload) + "\n```\n",
    }
    code, report, _ = _validate(fired_run, hook_payload, "--hook")
    assert (code, report["ok"], report["call_id"]) == (0, True, call_id)


def test_validate_never_blocks_twice_when_stop_hook_active(fired_run: Path) -> None:
    _, payload = _valid_response(fired_run)
    payload["results"][0]["verdict"] = "maybe"
    hook_payload = {
        "stop_hook_active": True,
        "last_assistant_message": json.dumps(payload),
    }
    code, report, stderr = _validate(fired_run, hook_payload, "--hook")
    assert code == 0 and report["ok"] is False and report["errors"]
    assert "stop_hook_active" in stderr


def test_validate_unknown_call_id_is_reported(fired_run: Path) -> None:
    _, payload = _valid_response(fired_run)
    code, report, _ = _validate(fired_run, payload, "--call-id", "nope")
    assert code == 2 and report["errors"] == ["unknown call_id: nope"]
