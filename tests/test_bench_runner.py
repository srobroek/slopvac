from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bench import runner

ROOT = Path(__file__).resolve().parents[1]
FAKE_OMP = Path(__file__).resolve().parent / "fake_omp.py"

# Verbatim from one recorded `omp -p --mode json` run: the settled turn is
# emitted four times, only the camelCase integers and the nested float cost are
# real, and `message_start` carries a zeroed placeholder.
RECORDED_ASSISTANT = {
    "role": "assistant",
    "content": [{"type": "text", "text": "NONCEPROBE7Q2"}],
    "api": "bedrock-converse-stream",
    "provider": "amazon-bedrock",
    "model": "us.openai.gpt-5.6-luna",
    "usage": {
        "input": 2,
        "output": 11,
        "cacheRead": 0,
        "cacheWrite": 8554,
        "totalTokens": 8567,
        "cost": {
            "input": 4.4e-07,
            "output": 1.452e-05,
            "cacheRead": 0,
            "cacheWrite": 0.00235235,
            "total": 0.00236731,
        },
    },
    "stopReason": "stop",
    "timestamp": 1789504332651,
}
RECORDED_EVENTS = [
    {"type": "session", "version": 3, "id": "01a0a6c5"},
    {"type": "turn_start"},
    {
        "type": "message_start",
        "message": {
            **RECORDED_ASSISTANT,
            "usage": {
                "input": 0,
                "output": 0,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 0,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
            },
        },
    },
    {"type": "message_end", "message": RECORDED_ASSISTANT},
    {"type": "turn_end", "message": RECORDED_ASSISTANT, "toolResults": []},
    {"type": "agent_end", "messages": [RECORDED_ASSISTANT], "isTerminal": True},
]


def assistant(text: str, **overrides: object) -> dict:
    message = {
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "usage": RECORDED_ASSISTANT["usage"],
        "timestamp": 7,
    }
    message.update(overrides)
    return message


def stream(*messages: dict) -> list[dict]:
    return [{"type": "message_end", "message": message} for message in messages]


def test_usage_reads_the_camel_case_schema_once_per_request() -> None:
    totals, error = runner.usage(runner.stream_messages(RECORDED_EVENTS, "assistant"))

    assert error == ""
    assert totals == {
        "input_tokens": 2,
        "output_tokens": 11,
        "cache_read_tokens": 0,
        "cache_write_tokens": 8554,
        "total_tokens": 8567,
        "cost_usd": 0.00236731,
        "request_count": 1,
    }


def test_duplicated_settled_events_do_not_multiply_usage() -> None:
    duplicated = RECORDED_EVENTS + [{"type": "message_end", "message": RECORDED_ASSISTANT}]

    totals, error = runner.usage(runner.stream_messages(duplicated, "assistant"))

    assert error == ""
    assert totals["request_count"] == 1
    assert totals["total_tokens"] == 8567


def test_two_real_turns_are_counted_separately() -> None:
    second = dict(RECORDED_ASSISTANT, timestamp=1789504339999)

    totals, error = runner.usage(runner.stream_messages(RECORDED_EVENTS + stream(second), "assistant"))

    assert error == ""
    assert totals["request_count"] == 2
    assert totals["total_tokens"] == 8567 * 2


@pytest.mark.parametrize(
    "usage_block, expected",
    [
        (
            {"input_tokens": 5, "output_tokens": 6, "total_tokens": 11},
            "usage_error: usage.input is not a non-negative integer",
        ),
        (
            {"input": 5, "output": 6, "cacheRead": 0, "cacheWrite": 0, "totalTokens": 11},
            "usage_error: usage.cost is not an object",
        ),
        (
            {
                "input": 5,
                "output": 6,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 11,
                "cost": {"total": "0.01"},
            },
            "usage_error: usage.cost.total is not a non-negative number",
        ),
        (
            {
                "input": True,
                "output": 6,
                "cacheRead": 0,
                "cacheWrite": 0,
                "totalTokens": 11,
                "cost": {"total": 0.01},
            },
            "usage_error: usage.input is not a non-negative integer",
        ),
    ],
)
def test_wrong_usage_schema_is_a_typed_usage_error(usage_block: dict, expected: str) -> None:
    totals, error = runner.usage([assistant("{}", usage=usage_block)])

    assert totals is None
    assert error == expected


def test_missing_assistant_message_is_a_typed_usage_error() -> None:
    assert runner.usage([]) == (None, "usage_error: no assistant message carried usage")


def test_thinking_parts_are_not_answer_text() -> None:
    message = {
        "role": "assistant",
        "content": [
            {"type": "thinking", "text": "weigh the rubric"},
            {"type": "text", "text": '{"results":'},
            {"type": "thinking", "thinking": "more private reasoning"},
            {"type": "text", "text": "[]}"},
        ],
    }

    assert runner.message_text(message) == '{"results":[]}'


def test_last_assistant_message_is_the_answer() -> None:
    messages = runner.stream_messages(
        stream(assistant("draft"), assistant("final", timestamp=8)), "assistant"
    )

    assert runner.message_text(messages[-1]) == "final"


@pytest.mark.parametrize(
    "text",
    [
        '```json\n{"results": [{"case_id": "a"}]}\n```',
        'Sure, here is the review:\n{"results": [{"case_id": "a"}]}\nHope that helps.',
        '```\n{"results": [{"case_id": "a"}]}```',
        '{"results": [{"case_id": "a"}]}',
    ],
)
def test_fenced_and_prose_wrapped_answers_are_parsed(text: str) -> None:
    payloads = runner.outer_payloads(text)

    assert [payload["results"] for payload in payloads] == [[{"case_id": "a"}]]


def test_nested_results_are_not_an_answer() -> None:
    assert runner.outer_payloads('{"data": {"results": [{"case_id": "a"}]}}') == []


def test_last_top_level_payload_wins() -> None:
    text = '{"results": [{"case_id": "example"}]} then really: {"results": [{"case_id": "a"}]}'

    assert runner.outer_payloads(text)[-1]["results"] == [{"case_id": "a"}]


CASES = [{"id": "a", "text": "alpha", "label": "defect"}, {"id": "b", "text": "beta", "label": "control"}]


@pytest.mark.parametrize(
    "rows, expected",
    [
        ([], "missing case_id: a,b"),
        ([{"case_id": "a"}], "missing case_id: b"),
        ([{"case_id": "a"}, {"case_id": "a"}], "duplicate case_id: a"),
        ([{"case_id": "a"}, {"case_id": "b"}, {"case_id": "c"}], "unknown case_id: c"),
        ([{"case_id": "b"}, {"case_id": "a"}], "result case_ids are not in expected order"),
        ([{"case_id": "a"}, "b"], "result row is not an object"),
        ([{"case_id": "a"}, {"verdict": "preserve"}], "result row missing case_id"),
        ("results", "results is not a list"),
    ],
)
def test_row_sets_get_precise_complaints(rows: object, expected: str) -> None:
    assert runner.validate_rows(CASES, rows) == expected


def test_valid_row_set_passes() -> None:
    assert runner.validate_rows(CASES, [{"case_id": "a"}, {"case_id": "b"}]) is None


def session(user_text: str, non_message_tokens: int = 9000) -> list[dict]:
    return [
        {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": user_text}]}},
        {
            "type": "message",
            "message": {
                **RECORDED_ASSISTANT,
                "contextSnapshot": {"promptTokens": 30, "nonMessageTokens": non_message_tokens},
            },
        },
    ]


def user_stream(text: str) -> list[dict]:
    message = {"role": "user", "content": [{"type": "text", "text": text}], "timestamp": 0}
    return [{"type": "message_start", "message": message}, {"type": "message_end", "message": message}]


def test_verified_request_records_non_message_context() -> None:
    prompt = "declared prompt with nonce deadbeefdeadbeef"

    facts, error = runner.verify_request(
        prompt, user_stream(prompt), session(prompt), "deadbeefdeadbeef"
    )

    assert error == ""
    assert facts == {"non_message_tokens": 9000}


def test_tool_traffic_is_a_contamination_error() -> None:
    prompt = "declared prompt with nonce deadbeefdeadbeef"
    events = user_stream(prompt) + [{"type": "tool_call", "name": "bash"}]

    _, error = runner.verify_request(prompt, events, session(prompt), "deadbeefdeadbeef")

    assert error == "contamination_error: tool event tool_call"


def test_extra_request_content_is_a_contamination_error() -> None:
    prompt = "declared prompt with nonce deadbeefdeadbeef"
    injected = prompt + "\n<system-reminder>be nice</system-reminder>"

    _, error = runner.verify_request(
        prompt, user_stream(injected), session(injected), "deadbeefdeadbeef"
    )

    assert error.startswith("contamination_error: recorded request differs from the declared prompt")


def test_request_without_the_nonce_is_a_transmission_error() -> None:
    prompt = "declared prompt with nonce deadbeefdeadbeef"

    _, error = runner.verify_request(
        prompt, user_stream("slopvac-online-"), session("slopvac-online-"), "deadbeefdeadbeef"
    )

    assert error == "transmission_error: recorded request does not carry the nonce"


def test_missing_context_snapshot_fails_closed() -> None:
    prompt = "declared prompt with nonce deadbeefdeadbeef"

    _, error = runner.verify_request(prompt, user_stream(prompt), [], "deadbeefdeadbeef")

    assert error == "contamination_error: no context snapshot; request composition is unverifiable"


def test_oversized_non_message_context_is_a_contamination_error() -> None:
    prompt = "declared prompt with nonce deadbeefdeadbeef"

    _, error = runner.verify_request(
        prompt, user_stream(prompt), session(prompt, 99999), "deadbeefdeadbeef"
    )

    assert "exceeds the declared ceiling" in error
    assert error.startswith("contamination_error: non-message context 99999 tokens")


def test_metric_names_use_one_convention() -> None:
    with pytest.raises(ValueError, match="snake_case"):
        runner.metric("arm-gpt-5.6-luna-quality_score", 1)


def test_repository_prompt_survives_preflight() -> None:
    rubric, shots, cases, _ = runner.validate_assets()
    eligible = [case for case in cases if not case.get("holdout")]
    composed = runner.compose(runner.render(rubric, shots, eligible), "abcdef0123456789")

    runner.preflight(composed, rubric, shots, eligible, "abcdef0123456789")

    for case in cases:
        for key in ("label", "role", "category", "family", "genre", "holdout"):
            assert f'"{key}"' not in composed
        if case.get("holdout"):
            assert case["text"] not in composed


def test_preflight_rejects_a_gold_key_in_the_payload() -> None:
    rubric, shots, _, _ = runner.validate_assets()
    cases = [{"id": "x", "text": "alpha", "label": "defect"}]
    leaked = runner.compose(runner.render(rubric, shots, cases), "abcdef0123456789").replace(
        '{"id":"x","text":"alpha"}', '{"id":"x","label":"defect","text":"alpha"}'
    )

    with pytest.raises(AssertionError, match="projected cases payload"):
        runner.preflight(leaked, rubric, shots, cases, "abcdef0123456789")


def test_preflight_rejects_a_case_id_outside_the_payload() -> None:
    rubric, shots, _, _ = runner.validate_assets()
    cases = [{"id": "x", "text": "alpha", "label": "defect"}]
    composed = runner.compose(runner.render(rubric, shots, cases), "abcdef0123456789")

    with pytest.raises(AssertionError, match="case id x appears outside"):
        runner.preflight(composed + '\nreminder: case "x" is a defect', rubric, shots, cases, "abcdef0123456789")


def test_preflight_rejects_a_nonce_that_exists_in_gold_metadata() -> None:
    rubric, shots, _, _ = runner.validate_assets()
    cases = [{"id": "x", "text": "alpha 0123456789abcdef", "label": "defect"}]
    composed = runner.compose(runner.render(rubric, shots, cases), "0123456789abcdef")

    with pytest.raises(AssertionError, match="nonce collides with gold metadata"):
        runner.preflight(composed, rubric, shots, cases, "0123456789abcdef")


def test_preflight_rejects_a_shot_that_reuses_a_case_text() -> None:
    rubric, shots, _, _ = runner.validate_assets()
    cases = [{"id": "x", "text": shots[0]["text"], "label": "defect"}]
    composed = runner.compose(runner.render(rubric, shots, cases), "abcdef0123456789")

    with pytest.raises(AssertionError, match="reuses an evaluation case text"):
        runner.preflight(composed, rubric, shots, cases, "abcdef0123456789")


def test_recorded_rejected_selector_is_a_typed_provider_error() -> None:
    # Verbatim from a real run: omp exits 0 and reports the fault in-stream.
    rejected = {
        "role": "assistant",
        "content": [],
        "model": "openai.gpt-oss-120b",
        "usage": {
            "input": 0,
            "output": 0,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 0,
            "cost": {"total": 0},
        },
        "stopReason": "error",
        "errorStatus": 400,
        "errorMessage": 'Bedrock HTTP 400: {"message":"The provided model identifier is invalid."}',
    }

    assert runner.provider_failure([rejected]) == (
        'provider_error: openai.gpt-oss-120b status 400: Bedrock HTTP 400: '
        '{"message":"The provided model identifier is invalid."}'
    )
    assert runner.provider_failure([RECORDED_ASSISTANT]) is None


@pytest.fixture(autouse=True)
def no_real_provider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may reach the paid provider; `fake_omp` opts back into a stand-in."""
    empty = tmp_path / "no-provider"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))


@pytest.fixture
def fake_omp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_real_provider: None) -> Path:
    """Put a recorded-shape `omp` on PATH and hand back the argv/stdin record."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "omp"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_OMP}" "$@"\n', encoding="utf-8")
    shim.chmod(0o755)
    record = tmp_path / "record.json"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    monkeypatch.setenv("FAKE_OMP_RECORD", str(record))
    monkeypatch.setenv("FAKE_OMP_MODE", "ok")
    return record


def one_case_prompt() -> tuple[str, str, list[dict]]:
    rubric, shots, cases, _ = runner.validate_assets()
    eligible = [case for case in cases if not case.get("holdout")][:1]
    nonce = "0f1e2d3c4b5a6978"
    return runner.compose(runner.render(rubric, shots, eligible), nonce), nonce, eligible


def test_invoke_sends_the_prompt_on_stdin_and_no_message_argument(fake_omp: Path, tmp_path: Path) -> None:
    prompt, nonce, cases = one_case_prompt()

    rows, stats, error = runner.invoke("fake/model", prompt, nonce, tmp_path / "run", "t", cases)

    assert error == ""
    record = json.loads(fake_omp.read_text())
    assert record["stdin"] == prompt
    assert record["argv"].count("-p") == 1
    assert record["argv"][record["argv"].index("-p") + 1].startswith("--")
    assert not [
        argument
        for index, argument in enumerate(record["argv"])
        if not argument.startswith("--")
        and argument != "-p"
        and not record["argv"][index - 1].startswith("--")
    ]
    assert rows == [{"case_id": cases[0]["id"], "verdict": "reject", "quote": cases[0]["text"], "reason": "formulaic construction"}]
    assert stats["total_tokens"] == 2164
    assert stats["cost_usd"] == pytest.approx(0.0004635)
    assert stats["request_count"] == 1
    assert stats["cache_write_tokens"] == 900
    assert stats["non_message_tokens"] == 9000


def test_invoke_retains_redacted_evidence(fake_omp: Path, tmp_path: Path) -> None:
    prompt, nonce, cases = one_case_prompt()
    run_dir = tmp_path / "run"

    runner.invoke("fake/model", prompt, nonce, run_dir, "t", cases)

    evidence = run_dir / "t"
    assert nonce in (evidence / "request.json").read_text()
    assert nonce in (evidence / "stdout.jsonl").read_text()
    assert nonce in (evidence / "session" / "fake.jsonl").read_text()
    assert (evidence / "stderr.txt").is_file()
    assert json.loads((evidence / "command.json").read_text())[0] == "omp"


def test_provider_failure_is_typed_and_its_stderr_is_retained_redacted(
    fake_omp: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_OMP_MODE", "boom")
    prompt, nonce, cases = one_case_prompt()
    run_dir = tmp_path / "run"

    rows, stats, error = runner.invoke("fake/model", prompt, nonce, run_dir, "t", cases)

    assert rows is None
    assert error.startswith("provider_error: omp exit 3: Error: unknown flags")
    assert "sk-abcdefghijklmnopqrs" not in error
    assert "api_key=<redacted>" in error
    retained = (run_dir / "t" / "stderr.txt").read_text()
    assert "sk-abcdefghijklmnopqrs" not in retained
    assert "api_key=<redacted>" in retained
    assert stats["latency_ms"] > 0


@pytest.mark.parametrize(
    "mode, expected",
    [
        ("ignore_stdin", "transmission_error: recorded request does not carry the nonce"),
        (
            "stream_error",
            'provider_error: fake/model status 400: Bedrock HTTP 400: {"message":"The provided '
            'model identifier is invalid."}',
        ),
        ("no_nonce", "transmission_error: answer does not echo the request nonce"),
        ("tool", "contamination_error: tool event tool_call"),
        ("fat_context", "contamination_error: non-message context 99999 tokens exceeds the declared ceiling 16000"),
    ],
)
def test_request_defects_are_typed_arm_outcomes(
    fake_omp: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, expected: str
) -> None:
    monkeypatch.setenv("FAKE_OMP_MODE", mode)
    prompt, nonce, cases = one_case_prompt()

    rows, _, error = runner.invoke("fake/model", prompt, nonce, tmp_path / "run", "t", cases)

    assert rows is None
    assert error == expected


def test_missing_provider_binary_is_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    prompt, nonce, cases = one_case_prompt()

    rows, _, error = runner.invoke("fake/model", prompt, nonce, tmp_path / "run", "t", cases)

    assert rows is None
    assert error == "provider_error: omp not found"
    assert (tmp_path / "run" / "t" / "request.json").is_file()


def run_main(arguments: list[str], run_dir: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, dict[str, str]]:
    code = runner.main([*arguments, "--run-dir", str(run_dir)])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("METRIC ")]
    metrics = dict(line[len("METRIC ") :].split("=", 1) for line in lines)
    for name in metrics:
        assert runner.METRIC_NAME.match(name), name
    return code, metrics


def test_smoke_uses_the_named_arm_one_case_and_one_request(
    fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, metrics = run_main(["--smoke", "--smoke-arm", "gpt-5.6-luna"], tmp_path / "run", capsys)

    assert code == 0
    assert metrics["case_count"] == "1"
    assert metrics["repeats"] == "1"
    assert metrics["arm_gpt_5_6_luna_repeat_1_outcome"] == "ok"
    assert metrics["arm_gpt_5_6_luna_repeat_1_request_count"] == "1"
    assert float(metrics["arm_gpt_5_6_luna_repeat_1_total_tokens"]) > 0
    assert float(metrics["arm_gpt_5_6_luna_repeat_1_cost_usd"]) > 0
    assert "arm_gpt_oss_120b_quality_score" not in metrics
    record = json.loads(fake_omp.read_text())
    assert "amazon-bedrock/us.openai.gpt-5.6-luna" in record["argv"]


def test_smoke_defaults_to_luna_not_the_first_arm(
    fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, metrics = run_main(["--smoke"], tmp_path / "run", capsys)

    assert code == 0
    assert "arm_gpt_5_6_luna_quality_score" in metrics
    record = json.loads(fake_omp.read_text())
    assert "amazon-bedrock/us.openai.gpt-5.6-luna" in record["argv"]


def test_unknown_smoke_arm_fails_before_any_request(
    fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = runner.main(["--smoke", "--smoke-arm", "gpt-oss-120b-typo", "--run-dir", str(tmp_path / "run")])

    assert code == 2
    assert "unknown smoke arm" in capsys.readouterr().err
    assert not fake_omp.exists()


def test_smoke_arm_without_smoke_is_rejected(fake_omp: Path) -> None:
    with pytest.raises(SystemExit):
        runner.main(["--smoke-arm", "gpt-5.6-luna"])
    assert not fake_omp.exists()


def test_scored_run_keeps_the_committed_arm_order(
    fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, metrics = run_main([], tmp_path / "run", capsys)
    order = [name for name in metrics if name.endswith("_quality_score") and "_repeat_" not in name]

    assert code == 0
    assert order == [
        "arm_gpt_oss_120b_quality_score",
        "arm_gpt_5_6_luna_quality_score",
        "arm_claude_haiku_quality_score",
        "arm_gpt_5_6_sol_quality_score",
    ]
    assert metrics["case_count"] == "34"
    assert metrics["repeats"] == "2"


def test_unmeasured_run_exits_nonzero_and_scores_no_cases(
    fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_OMP_MODE", "boom")

    code, metrics = run_main(["--smoke"], tmp_path / "run", capsys)

    assert code == 1
    assert metrics["arm_gpt_5_6_luna_quality_score"] == "unmeasured"
    assert metrics["arm_gpt_5_6_luna_repeat_1_outcome"] == "provider_error"
    assert "arm_gpt_5_6_luna_repeat_1_failures" not in metrics
    assert "arm_gpt_5_6_luna_repeat_1_quality_score" not in metrics


def test_entry_point_forwards_smoke_arm_selection() -> None:
    proc = subprocess.run(
        ["/bin/sh", "autoresearch.sh", "--smoke", "--smoke-arm", "nope"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": "/usr/bin:/bin", "PYTHON": sys.executable},
    )

    assert proc.returncode == 2
    assert "unknown smoke arm 'nope'" in proc.stderr
