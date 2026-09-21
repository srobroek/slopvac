from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).parents[1] / "scripts" / "judgement_adjudicate.py"
spec = importlib.util.spec_from_file_location("judgement_adjudicate", SCRIPT)
assert spec and spec.loader
adjudicate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adjudicate)


def test_resolve_passage_includes_two_sentences_each_side(tmp_path: Path) -> None:
    document = tmp_path / "doc.md"
    document.write_text("One. Two. Target sentence. Four. Five. Six.", encoding="utf-8")
    target_start = document.read_text().index("Target")
    passage, resolved = adjudicate.resolve_passage(
        {"path": "doc.md", "source_range": [target_start, target_start + 15]}, tmp_path
    )
    assert resolved
    assert passage == "One. Two. Target sentence. Four. Five."


def test_prompt_includes_question_and_examples() -> None:
    messages = adjudicate.build_messages(
        "demo.rule",
        [{"unit_id": "u1", "quote": "A quote", "passage": "A passage"}],
        {
            "demo.rule": {
                "question": "Does this trigger?",
                "examples": [{"bad": "bad", "good": "good"}],
            }
        },
    )
    rendered = messages[1]["content"]
    assert "Does this trigger?" in rendered
    assert '"bad": "bad"' in rendered
    assert "u1" in rendered


def test_parse_json_response_accepts_fenced_and_surrounded_text() -> None:
    value = adjudicate.parse_json_response('prefix ```json\n{"results": []}\n``` suffix')
    assert value == {"results": []}


def test_parse_json_response_rejects_missing_or_non_object() -> None:
    for value in ("not JSON", "[]"):
        try:
            adjudicate.parse_json_response(value)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid JSON response was accepted")


def test_call_sol_retries_length_with_doubled_budget() -> None:
    payloads = [
        {"choices": [{"finish_reason": "length", "message": {"content": ""}}]},
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"results":[{"unit_id":"u1","verdict":"TP","reason":"sound","fp_pattern":"other"}]}'
                    },
                }
            ]
        },
    ]

    class Client:
        def __init__(self) -> None:
            self.requests: list[dict] = []

        def invoke_model(self, **kwargs):
            self.requests.append(json.loads(kwargs["body"]))
            return {"body": SimpleNamespace(read=lambda: json.dumps(payloads.pop(0)))}

    client = Client()
    result = adjudicate.call_sol(
        client,
        "demo.rule",
        [{"unit_id": "u1", "quote": "q", "passage": "p"}],
        {"demo.rule": {"question": "q", "examples": []}},
    )
    assert result["valid_json"] is True
    assert len(client.requests) == 2
    assert (
        client.requests[1]["max_completion_tokens"]
        == adjudicate.MAX_COMPLETION_TOKENS * 2
    )


def test_spine_states_exact_result_shape() -> None:
    spine = (SCRIPT.parents[1] / "src/slopvac/judgement/spine.md").read_text()
    assert "exactly these keys" in spine
    assert "no other keys" in spine
    assert "`note`" in spine


def test_consistency_report_writes_majority_and_flip_rate(tmp_path: Path) -> None:
    calls = tmp_path / "calls"
    calls.mkdir()
    for repeat, verdict in ((1, "FP"), (2, "TP"), (3, "TP")):
        (calls / f"{repeat:02d}-0001-demo.json").write_text(
            json.dumps(
                {
                    "repeat": repeat,
                    "rows": [
                        {
                            "unit_id": "u1",
                            "verdict": verdict,
                            "fp_pattern": "heading",
                        }
                    ],
                }
            )
        )
    result = adjudicate.consistency_report(
        tmp_path, [{"unit_id": "u1", "rule_id": "demo.rule"}]
    )
    assert result["flip_rate"] == 1.0
    assert result["units"][0]["majority"] == "TP"
    assert (tmp_path / "CONSISTENCY.md").exists()


def test_table_math_reports_both_false_positive_denominators() -> None:
    rows = [
        {"verdict": "FP", "fp_pattern": "heading"},
        {"verdict": "TP", "fp_pattern": "other"},
        {"verdict": "borderline", "fp_pattern": "other"},
        {"verdict": "parse_error", "fp_pattern": "other"},
    ]
    result = adjudicate.table_math(rows, attempted=20)
    assert result["adjudicated"] == 3
    assert result["fp_share_of_adjudicated_confirms"] == 1 / 3
    assert result["fp_incidence_per_attempted_unit"] == 1 / 20
    assert result["dominant_fp_pattern"] == "heading"
