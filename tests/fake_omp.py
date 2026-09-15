#!/usr/bin/env python3
"""Stand-in for `omp --mode json`, shaped after a recorded real invocation.

`FAKE_OMP_MODE` selects the failure being simulated. `FAKE_OMP_RECORD` receives
the argv and stdin the runner actually used, which is how the tests prove the
prompt travels on stdin instead of argv.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REAL_USAGE = {
    "input": 1200,
    "output": 64,
    "cacheRead": 0,
    "cacheWrite": 900,
    "totalTokens": 2164,
    "cost": {
        "input": 0.000132,
        "output": 0.0000845,
        "cacheRead": 0.0,
        "cacheWrite": 0.000247,
        "total": 0.0004635,
    },
}
ZERO_USAGE = {
    "input": 0,
    "output": 0,
    "cacheRead": 0,
    "cacheWrite": 0,
    "totalTokens": 0,
    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
}


def option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def main() -> int:
    argv = sys.argv[1:]
    stdin = sys.stdin.read()
    mode = os.environ.get("FAKE_OMP_MODE", "ok")
    record = os.environ.get("FAKE_OMP_RECORD")
    if record:
        Path(record).write_text(json.dumps({"argv": argv, "stdin": stdin}), encoding="utf-8")

    if mode == "boom":
        print(
            "Error: unknown flags: --no-slop, --no-memory (api_key=sk-abcdefghijklmnopqrs)",
            file=sys.stderr,
        )
        return 3

    nonce_match = re.search(r'value "([0-9a-f]{16})"', stdin)
    nonce = nonce_match.group(1) if nonce_match else ""
    cases = []
    payload = re.search(r"Evaluation cases:\n(\[.*?\])\n", stdin, re.S)
    if payload:
        cases = json.loads(payload.group(1))
    results = [
        {
            "case_id": case["id"],
            "verdict": "reject",
            "quote": case["text"],
            "reason": "formulaic construction",
        }
        for case in cases
    ]
    answer: dict[str, object] = {"results": results}
    if mode != "no_nonce":
        answer["run_nonce"] = nonce

    user = {
        "role": "user",
        "content": [
            {"type": "text", "text": "slopvac-online-" if mode == "ignore_stdin" else stdin}
        ],
        "attribution": "user",
        "timestamp": 0,
    }
    assistant = {
        "role": "assistant",
        "content": [
            {"type": "thinking", "text": "private scratchpad that is not the answer"},
            {"type": "text", "text": json.dumps(answer)},
        ],
        "api": "bedrock-converse-stream",
        "provider": "fake",
        "model": option(argv, "--model"),
        "usage": REAL_USAGE,
        "stopReason": "stop",
        "timestamp": 1,
    }

    if mode == "stream_error":
        # A rejected model selector: omp exits 0 and reports the fault in-stream.
        assistant = {
            **assistant,
            "content": [],
            "usage": ZERO_USAGE,
            "stopReason": "error",
            "errorStatus": 400,
            "errorId": 400,
            "errorMessage": 'Bedrock HTTP 400: {"message":"The provided model identifier is invalid."}',
        }

    events: list[dict] = [
        {"type": "session", "version": 3, "id": "fake"},
        {"type": "turn_start"},
        {"type": "message_start", "message": user},
        {"type": "message_end", "message": user},
        {"type": "message_start", "message": {**assistant, "usage": ZERO_USAGE}},
        {"type": "message_end", "message": assistant},
        # A duplicated settled event: usage must not double.
        {"type": "message_end", "message": assistant},
        {"type": "turn_end", "message": assistant, "toolResults": []},
        {"type": "agent_end", "messages": [user, assistant], "isTerminal": True},
    ]
    if mode == "tool":
        events.insert(4, {"type": "tool_call", "name": "bash", "id": "t1"})
    for event in events:
        print(json.dumps(event))

    session_dir = option(argv, "--session-dir")
    if session_dir:
        target = Path(session_dir)
        target.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "promptTokens": 2100,
            "nonMessageTokens": 99999 if mode == "fat_context" else 9000,
            "compactionEpoch": 0,
        }
        lines = [
            {"type": "session", "version": 3, "id": "fake"},
            {"type": "message", "id": "a", "message": user},
            {"type": "message", "id": "b", "message": {**assistant, "contextSnapshot": snapshot}},
        ]
        target.joinpath("fake.jsonl").write_text(
            "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
