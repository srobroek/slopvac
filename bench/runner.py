#!/usr/bin/env python3
"""Fixed online structured-prose benchmark.

Every knob is repository data: `rubric.json`, `shots.json`, `cases.json` and
`arms.json` are hash-pinned by `manifest.json`. The runner renders the pinned
prompt, calls `omp` once per repeat, and turns the provider's own event stream
into metrics.

Two contracts keep the numbers honest.

Transmission: each invocation carries an opaque nonce that exists only in the
model-facing prompt. The nonce must appear in the retained request artifact, in
the request the provider recorded, and in the model's own answer. Nothing is
scored until all three hold.

Outcome typing: provider, transmission, contamination, usage, parse and schema
problems are arm outcomes and leave the arm *unmeasured*. They are never counted
as case failures, because a request that never reached the model says nothing
about the model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUBRIC = ROOT / "rubric.json"
TEMPLATE = ROOT / "prompt_template.txt"
SHOTS = ROOT / "shots.json"
CASES = ROOT / "cases.json"
ARMS = ROOT / "arms.json"
MANIFEST = ROOT / "manifest.json"

ALLOWED = {"confirm", "preserve", "reject", "abstain"}
# Gold fields that must never reach the model, directly or as an answer mapping.
GOLD_KEYS = frozenset({"label", "role", "category", "family", "genre", "holdout"})
AUTH = re.compile(
    r"\b(?:AI|artificial intelligence|model-generated|machine-generated|"
    r"human-written|authorship|written by a (?:person|human|model))\b",
    re.I,
)

# One metric-name convention: lowercase words joined by underscores. Arm ids are
# slugged into it, so `METRIC` lines stay parseable with a single rule.
METRIC_NAME = re.compile(r"[a-z0-9]+(?:_[a-z0-9]+)*\Z")

DEFAULT_SMOKE_ARM = "gpt-5.6-luna"
DEFAULT_TIMEOUT = 300
# Grace so `omp --max-time` fires before the subprocess is killed from outside.
KILL_GRACE = 30

# Declared request composition. `omp` always adds its own base context; the
# ceiling below is the measured budget for it, and it is recorded per invocation
# so drift is visible rather than silent.
DECLARED_SYSTEM_PROMPT = (
    "You are a strict structured-prose reviewer. Follow the supplied rubric and "
    "output contract exactly. Use only the supplied JSON. Never discuss "
    "authorship or how any text was produced."
)
HERMETIC_FLAGS = (
    "--no-extensions",
    "--no-skills",
    "--no-rules",
    "--no-tools",
    "--no-lsp",
    "--no-title",
)
MAX_NON_MESSAGE_TOKENS = 16000

ARTIFACT_BYTES = 512 * 1024
TRUNCATED = "\n<<truncated: retained artifact is bounded>>\n"

# `omp` assistant usage is camelCase integers plus a nested float cost object.
TOKEN_FIELDS = {
    "input": "input_tokens",
    "output": "output_tokens",
    "cacheRead": "cache_read_tokens",
    "cacheWrite": "cache_write_tokens",
    "totalTokens": "total_tokens",
}
TOOL_EVENTS = frozenset(
    {"tool_call", "tool_start", "tool_end", "tool_result", "tool_use", "tool_error"}
)
TOOL_PARTS = frozenset(
    {"tool_use", "tool_call", "tool_result", "tool-call", "tool-result"}
)

TRANSMISSION_BLOCK = (
    "\n\nTransmission check, which amends the output shape above: the returned "
    'JSON object must also carry the top-level key "run_nonce" with the exact '
    'value "{nonce}". Every result object keeps exactly the keys listed above.\n'
)

REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}"), "Bearer <redacted>"),
    (re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_\-]{12,}"), "<redacted-key>"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}\b"), "<redacted-access-key-id>"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]+"), "<redacted-jwt>"),
    (
        re.compile(
            r"(?i)(\"?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|"
            r"secret[_-]?access[_-]?key|session[_-]?token|password|credential)\"?\s*[:=]\s*)"
            r"\"?[^\"\s,}]{6,}\"?"
        ),
        r"\1<redacted>",
    ),
)


def metric(name: str, value: Any) -> None:
    """Emit one `METRIC name=value` line under the single naming convention."""
    if not METRIC_NAME.match(name):
        raise ValueError(f"metric name is not snake_case: {name!r}")
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, float):
        text = format(value, ".9g")
    else:
        text = str(value).replace("\n", " ").replace("\r", " ")
    print(f"METRIC {name}={text}", flush=True)


def slug(text: str) -> str:
    """Map an arm id onto the metric-name grammar, deterministically."""
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected object")
    return value


def validate_assets() -> tuple[dict, list, list, dict]:
    manifest = load(MANIFEST)
    for name, expected in manifest.get("sha256", {}).items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"asset changed: {name}")
    rubric, shot_doc, case_doc, arm_doc = load(RUBRIC), load(SHOTS), load(CASES), load(ARMS)
    shots, cases, arms = shot_doc.get("shots"), case_doc.get("cases"), arm_doc.get("arms")
    if set(rubric.get("verdicts", [])) != ALLOWED or not all(
        isinstance(x, list) for x in (shots, cases, arms)
    ):
        raise ValueError("assets are malformed")
    if len({x.get("id") for x in cases}) != len(cases) or any(
        not isinstance(x.get("text"), str) for x in cases
    ):
        raise ValueError("case IDs/text must be present and unique")
    families: dict[str, list] = {}
    for case in cases:
        families.setdefault(str(case.get("family")), []).append(case)
    if any(sum(bool(x.get("holdout")) for x in group) != 1 for group in families.values()):
        raise ValueError("each near-neighbour family must have exactly one holdout")
    for shot in shots:
        if (
            shot.get("verdict") not in ALLOWED
            or not isinstance(shot.get("quote"), str)
            or shot["quote"] not in shot.get("text", "")
            or AUTH.search(json.dumps(shot))
        ):
            raise ValueError(f'invalid shot: {shot.get("id")}')
    if not arms or any(not x.get("id") or not x.get("model") for x in arms):
        raise ValueError("model arm manifest is malformed")
    slugs = [slug(x["id"]) for x in arms]
    if "" in slugs or len(set(slugs)) != len(slugs):
        raise ValueError("arm ids do not slug to unique metric names")
    return rubric, shots, cases, arm_doc


def project_cases(cases: list[dict]) -> list[dict[str, str]]:
    projected = [{"id": str(c["id"]), "text": str(c["text"])} for c in cases]
    if any(set(c) != {"id", "text"} for c in projected):
        raise AssertionError("model projection contains private metadata")
    return projected


def pinned_json(value: Any) -> str:
    """The one serialization the prompt and its preflight both depend on."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def render(rubric: dict, shots: list, cases: list[dict]) -> str:
    """Render the pinned prompt body; the nonce is added by `compose`."""
    prompt = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{RUBRIC_JSON}}", pinned_json(rubric))
        .replace("{{SHOTS_JSON}}", pinned_json(shots))
        .replace("{{CASES_JSON}}", pinned_json(project_cases(cases)))
    )
    if "{{" in prompt or "}}" in prompt:
        raise ValueError("prompt template has unresolved placeholders")
    return prompt


def compose(prompt: str, nonce: str) -> str:
    return prompt + TRANSMISSION_BLOCK.format(nonce=nonce)


def preflight(prompt: str, rubric: dict, shots: list, cases: list[dict], nonce: str) -> None:
    """Prove no gold field, no answer mapping and no nonce leak reaches the model.

    The projection is proven structurally (`id`/`text` only), so the remaining
    risk is an id-to-gold association elsewhere in the prompt. Each case id is
    therefore required to occur exactly once, inside the cases payload.
    """
    payload = pinned_json(project_cases(cases))
    if any(re.search(rf'"{key}"\s*:', payload) for key in GOLD_KEYS):
        raise AssertionError("gold metadata key leaked into the eval payload")
    if re.search(r'"(?:defect|control)"', payload):
        raise AssertionError("answer mapping leaked into the eval payload")
    if payload not in prompt:
        raise AssertionError("prompt does not carry the projected cases payload")
    outside = prompt.replace(payload, "", 1)
    for case in cases:
        case_id = str(case["id"])
        if f'"{case_id}"' in outside:
            raise AssertionError(f"case id {case_id} appears outside the eval payload")
    case_texts = {str(c["text"]) for c in cases}
    for shot in shots:
        if str(shot.get("text", "")) in case_texts:
            raise AssertionError(f'shot {shot.get("id")} reuses an evaluation case text')
    gold_metadata = json.dumps({"rubric": rubric, "shots": shots, "cases": cases})
    if nonce in gold_metadata:
        raise AssertionError("nonce collides with gold metadata")
    if nonce not in prompt:
        raise AssertionError("composed prompt does not carry the transmission nonce")


def _fingerprint(message: dict) -> str:
    """Stable identity for one assistant/user turn across duplicated events."""
    return json.dumps(
        {
            "role": message.get("role"),
            "timestamp": message.get("timestamp"),
            "model": message.get("model"),
            "content": message.get("content"),
            "usage": message.get("usage"),
        },
        sort_keys=True,
        default=str,
    )


def _dedupe(messages: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for message in messages:
        key = _fingerprint(message)
        if key in seen:
            continue
        seen.add(key)
        out.append(message)
    return out


def stream_messages(events: list[Any], role: str) -> list[dict]:
    """Canonical turns from `omp --mode json` stdout.

    `message_end` carries the settled turn exactly once. `message_start`,
    `turn_end` and `agent_end` repeat the same object with partial or duplicate
    usage, so they are ignored unless no `message_end` exists at all.
    """
    settled = [
        event["message"]
        for event in events
        if isinstance(event, dict)
        and event.get("type") == "message_end"
        and isinstance(event.get("message"), dict)
        and event["message"].get("role") == role
    ]
    if settled:
        return _dedupe(settled)
    tail: list[dict] = []
    for event in events:
        if isinstance(event, dict) and event.get("type") == "agent_end":
            for message in event.get("messages") or []:
                if isinstance(message, dict) and message.get("role") == role:
                    tail.append(message)
    return _dedupe(tail)


def session_messages(events: list[Any], role: str) -> list[dict]:
    """Canonical turns from a session JSONL transcript."""
    return _dedupe(
        [
            event["message"]
            for event in events
            if isinstance(event, dict)
            and event.get("type") == "message"
            and isinstance(event.get("message"), dict)
            and event["message"].get("role") == role
        ]
    )


def message_text(message: dict) -> str:
    """Concatenate text parts only; thinking and tool parts are not answer text."""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        part["text"]
        for part in content
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    )


def usage(messages: list[dict]) -> tuple[dict[str, Any] | None, str]:
    """Sum the real `omp` usage schema over one turn per provider request."""
    if not messages:
        return None, "usage_error: no assistant message carried usage"
    totals: dict[str, Any] = {name: 0 for name in TOKEN_FIELDS.values()}
    totals["cost_usd"] = 0.0
    totals["request_count"] = 0
    for message in messages:
        block = message.get("usage")
        if not isinstance(block, dict):
            return None, "usage_error: assistant message has no usage object"
        for raw, name in TOKEN_FIELDS.items():
            value = block.get(raw)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return None, f"usage_error: usage.{raw} is not a non-negative integer"
            totals[name] += value
        cost = block.get("cost")
        if not isinstance(cost, dict):
            return None, "usage_error: usage.cost is not an object"
        total = cost.get("total")
        if isinstance(total, bool) or not isinstance(total, (int, float)) or total < 0:
            return None, "usage_error: usage.cost.total is not a non-negative number"
        totals["cost_usd"] += float(total)
        totals["request_count"] += 1
    return totals, ""


def outer_payloads(text: str) -> list[dict]:
    """Top-level JSON objects owning a `results` list, fences and prose removed.

    Only top-level decodes are considered, so `{"data":{"results":[...]}}` is not
    a payload: a nested list is not the declared answer shape.
    """
    cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.I).replace("```", "")
    decoder = json.JSONDecoder()
    found: list[dict] = []
    position = 0
    while True:
        match = re.search(r"[\[{]", cleaned[position:])
        if match is None:
            return found
        start = position + match.start()
        try:
            value, end = decoder.raw_decode(cleaned[start:])
        except json.JSONDecodeError:
            position = start + 1
            continue
        position = start + end
        if isinstance(value, dict) and isinstance(value.get("results"), list):
            found.append(value)


def provider_failure(messages: list[dict]) -> str | None:
    """Typed complaint for a turn `omp` finished with a provider error.

    A rejected model selector or a transport fault ends the turn with
    `stopReason: "error"`, an empty content list and zeroed usage, while `omp`
    itself exits 0. Without this check a provider fault reads as an unparseable
    answer and slanders the model.
    """
    for message in messages:
        status = message.get("errorStatus")
        detail = message.get("errorMessage")
        if message.get("stopReason") != "error" and status is None and detail is None:
            continue
        text = " ".join(str(detail or "provider reported an error").split())[:200]
        return f'provider_error: {message.get("model") or "model"} status {status}: {text}'
    return None


def validate_rows(cases: list[dict], rows: Any) -> str | None:
    """Precise, typed complaint about a result set, or None when it is usable."""
    expected = [str(case.get("id")) for case in cases]
    if not isinstance(rows, list):
        return "results is not a list"
    actual: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            return "result row is not an object"
        case_id = row.get("case_id")
        if not isinstance(case_id, str):
            return "result row missing case_id"
        actual.append(case_id)
    duplicates = sorted({x for x in actual if actual.count(x) > 1})
    if duplicates:
        return f'duplicate case_id: {",".join(duplicates)}'
    unknown = [x for x in actual if x not in expected]
    if unknown:
        return f'unknown case_id: {",".join(sorted(set(unknown)))}'
    missing = [x for x in expected if x not in actual]
    if missing:
        return f'missing case_id: {",".join(missing)}'
    if len(actual) != len(expected):
        return f"expected {len(expected)} results, got {len(actual)}"
    if actual != expected:
        return "result case_ids are not in expected order"
    return None


def _env_secrets() -> list[str]:
    pattern = re.compile(r"(?i)(key|token|secret|password|credential|session)")
    return sorted(
        (value for name, value in os.environ.items() if pattern.search(name) and len(value) >= 12),
        key=len,
        reverse=True,
    )


def redact(text: str) -> str:
    for value in _env_secrets():
        text = text.replace(value, "<redacted-env-value>")
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def retain(path: Path, text: str) -> Path:
    """Write one bounded, redacted evidence artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = redact(text)
    if len(cleaned) > ARTIFACT_BYTES:
        cleaned = cleaned[:ARTIFACT_BYTES] + TRUNCATED
    path.write_text(cleaned, encoding="utf-8")
    return path


def read_events(text: str) -> list[Any]:
    events: list[Any] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _tool_traffic(events: list[Any]) -> str | None:
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("type") in TOOL_EVENTS:
            return f'tool event {event["type"]}'
        if event.get("toolResults"):
            return "tool results attached to a turn"
        message = event.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), list):
            for part in message["content"]:
                if isinstance(part, dict) and part.get("type") in TOOL_PARTS:
                    return f'tool content part {part["type"]}'
    return None


def verify_request(
    prompt: str,
    stdout_events: list[Any],
    session_events: list[Any],
    nonce: str,
) -> tuple[dict[str, Any], str]:
    """Check that the request the provider saw is exactly the declared prompt."""
    facts: dict[str, Any] = {}
    problem = _tool_traffic(stdout_events) or _tool_traffic(session_events)
    if problem:
        return facts, f"contamination_error: {problem}"

    users = stream_messages(stdout_events, "user") or session_messages(session_events, "user")
    if len(users) != 1:
        return facts, f"transmission_error: expected 1 user turn, recorded {len(users)}"
    sent = message_text(users[0])
    if sent != prompt:
        if nonce not in sent:
            return facts, "transmission_error: recorded request does not carry the nonce"
        return facts, (
            f"contamination_error: recorded request differs from the declared prompt "
            f"({len(sent)} chars sent, {len(prompt)} declared)"
        )

    recorded = session_messages(session_events, "user")
    if recorded and message_text(recorded[0]) != prompt:
        return facts, "contamination_error: session transcript request differs from the declared prompt"

    snapshots = [
        message["contextSnapshot"]["nonMessageTokens"]
        for message in session_messages(session_events, "assistant")
        if isinstance(message.get("contextSnapshot"), dict)
        and isinstance(message["contextSnapshot"].get("nonMessageTokens"), int)
    ]
    if not snapshots:
        return facts, "contamination_error: no context snapshot; request composition is unverifiable"
    facts["non_message_tokens"] = max(snapshots)
    if facts["non_message_tokens"] > MAX_NON_MESSAGE_TOKENS:
        return facts, (
            f"contamination_error: non-message context {facts['non_message_tokens']} tokens "
            f"exceeds the declared ceiling {MAX_NON_MESSAGE_TOKENS}"
        )
    return facts, ""


def invoke(
    model: str,
    prompt: str,
    nonce: str,
    run_dir: Path,
    tag: str,
    cases: list[dict],
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[dict] | None, dict[str, Any], str]:
    """One provider request. Returns (rows, stats, typed_error)."""
    evidence = run_dir / tag
    request = {
        "model": model,
        "nonce": nonce,
        "system_prompt": DECLARED_SYSTEM_PROMPT,
        "hermetic_flags": list(HERMETIC_FLAGS),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt": prompt,
    }
    retain(evidence / "request.json", json.dumps(request, indent=1, sort_keys=True))

    if shutil.which("omp") is None:
        return None, {}, "provider_error: omp not found"

    stats: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="slopvac-online-") as scratch:
        session_dir = Path(scratch) / "sessions"
        work_dir = Path(scratch) / "cwd"
        work_dir.mkdir()
        cmd = [
            "omp",
            "-p",
            "--mode",
            "json",
            "--model",
            model,
            "--thinking",
            "low",
            "--max-time",
            str(timeout),
            "--cwd",
            str(work_dir),
            "--session-dir",
            str(session_dir),
            "--system-prompt",
            DECLARED_SYSTEM_PROMPT,
            *HERMETIC_FLAGS,
        ]
        retain(evidence / "command.json", json.dumps(cmd, indent=1))
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=timeout + KILL_GRACE,
                check=False,
            )
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
            expired = False
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            code, expired = None, True
        stats["latency_ms"] = (time.monotonic() - start) * 1000
        retain(evidence / "stdout.jsonl", stdout)
        retain(evidence / "stderr.txt", stderr)
        session_text = ""
        for source in sorted(session_dir.glob("*.jsonl")) if session_dir.is_dir() else []:
            body = source.read_text(encoding="utf-8", errors="replace")
            retain(evidence / "session" / source.name, body)
            session_text += body
        for source in sorted(session_dir.glob("*/*.jsonl")) if session_dir.is_dir() else []:
            retain(
                evidence / "session" / source.parent.name / source.name,
                source.read_text(encoding="utf-8", errors="replace"),
            )

    if expired:
        return None, stats, "provider_error: timeout"
    if code != 0:
        detail = redact(" ".join(stderr.split()))[:200] or "no stderr"
        return None, stats, f"provider_error: omp exit {code}: {detail}"

    stdout_events = read_events(stdout)
    session_events = read_events(session_text)
    if nonce not in (evidence / "request.json").read_text(encoding="utf-8"):
        return None, stats, "transmission_error: nonce absent from the retained request artifact"
    if session_text and nonce not in session_text:
        return None, stats, "transmission_error: nonce absent from the retained session artifact"

    facts, error = verify_request(prompt, stdout_events, session_events, nonce)
    stats.update(facts)
    if error:
        return None, stats, error

    replies = stream_messages(stdout_events, "assistant") or session_messages(
        session_events, "assistant"
    )
    failure = provider_failure(replies)
    if failure:
        return None, stats, failure
    totals, error = usage(replies)
    if error:
        return None, stats, error
    stats.update(totals or {})

    payloads = outer_payloads(message_text(replies[-1]))
    stats["payload_candidates"] = len(payloads)
    if not payloads:
        return None, stats, "parse_error: no top-level JSON object with a results list"
    outer = payloads[-1]
    problem = validate_rows(cases, outer["results"])
    if problem:
        return None, stats, f"schema_invalid: {problem}"
    if outer.get("run_nonce") != nonce:
        return None, stats, "transmission_error: answer does not echo the request nonce"
    return outer["results"], stats, ""


def score(cases: list[dict], results: list[dict]) -> dict[str, Any]:
    """Score a validated result set. Only model content can fail here."""
    problem = validate_rows(cases, results)
    if problem:
        raise AssertionError(f"score received an unvalidated result set: {problem}")
    by_id = {row.get("case_id"): row for row in results}
    out = {
        "failures": 0,
        "false_positives": 0,
        "false_confirms": 0,
        "misses": 0,
        "correct": 0,
        "abstains": 0,
        "missing": 0,
    }
    for case in cases:
        row = by_id.get(str(case.get("id")))
        if row is None:
            out["missing"] += 1
            continue
        if (
            row.get("verdict") not in ALLOWED
            or not isinstance(row.get("quote"), str)
            or not row["quote"]
            or row["quote"] not in case.get("text", "")
            or AUTH.search(json.dumps(row))
        ):
            out["failures"] += 1
            continue
        expected = "reject" if case.get("label") == "defect" else "preserve"
        if row["verdict"] == "abstain":
            out["abstains"] += 1
        if row["verdict"] == expected:
            out["correct"] += 1
        elif case.get("label") == "control" and row["verdict"] == "reject":
            out["false_positives"] += 1
        elif case.get("label") == "defect" and row["verdict"] == "preserve":
            out["false_confirms"] += 1
        else:
            out["misses"] += 1
    count = max(1, len(cases))
    penalty = (
        100
        * (
            3 * out["failures"]
            + 4 * out["false_positives"]
            + 5 * out["false_confirms"]
            + 4 * out["misses"]
            + 4 * out["missing"]
        )
        / count
    )
    out["quality_score"] = max(0.0, 100.0 - penalty)
    return out


def default_run_dir() -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    return ROOT.parent / ".bench-runs" / f"{stamp}_{os.getpid()}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--smoke", action="store_true", help="one arm, one non-holdout case, one request")
    parser.add_argument(
        "--smoke-arm",
        help=f"exact arm id for --smoke (default {DEFAULT_SMOKE_ARM}); scored arm order never changes",
    )
    parser.add_argument("--run-dir", help="directory for retained redacted evidence")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-request seconds")
    args = parser.parse_args(argv)
    if args.smoke_arm is not None and not args.smoke:
        parser.error("--smoke-arm selects the --smoke arm; it does not change scored arm order")
    smoke_arm = args.smoke_arm or DEFAULT_SMOKE_ARM

    try:
        rubric, shots, cases, arm_doc = validate_assets()
        eligible = [case for case in cases if not case.get("holdout")]
        if args.smoke:
            arms = [arm for arm in arm_doc["arms"] if str(arm["id"]) == smoke_arm]
            if not arms:
                known = ", ".join(str(arm["id"]) for arm in arm_doc["arms"])
                raise ValueError(f"unknown smoke arm {smoke_arm!r}; known arms: {known}")
            eligible = eligible[:1]
        else:
            arms = list(arm_doc["arms"])
        if not eligible:
            raise ValueError("no non-holdout evaluation cases")
        prompt = render(rubric, shots, eligible)
    except (OSError, ValueError, AssertionError, json.JSONDecodeError) as exc:
        print(f"autoresearch: asset validation failure: {exc}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir).expanduser() if args.run_dir else default_run_dir()
    run_dir.mkdir(parents=True, exist_ok=True)
    repeats = 1 if args.smoke else int(arm_doc.get("fixed", {}).get("repeats", 2))

    metric("run_dir", run_dir)
    metric("case_count", len(eligible))
    metric("holdout_count", sum(bool(case.get("holdout")) for case in cases))
    metric("prompt_sha256", hashlib.sha256(prompt.encode()).hexdigest())
    metric("system_prompt_sha256", hashlib.sha256(DECLARED_SYSTEM_PROMPT.encode()).hexdigest())
    metric("repeats", repeats)

    measured = 0
    for arm in arms:
        name = f'arm_{slug(arm["id"])}'
        scores: list[float] = []
        for index in range(1, repeats + 1):
            nonce = secrets.token_hex(8)
            tag = f"{name}_repeat_{index}"
            try:
                composed = compose(prompt, nonce)
                preflight(composed, rubric, shots, eligible, nonce)
            except AssertionError as exc:
                print(f"autoresearch: prompt preflight failure: {exc}", file=sys.stderr)
                return 2
            rows, stats, error = invoke(
                str(arm["model"]), composed, nonce, run_dir, tag, eligible, args.timeout
            )
            metric(f"{tag}_nonce", nonce)
            metric(f"{tag}_outcome", "ok" if not error else error.split(":", 1)[0])
            for key, value in sorted(stats.items()):
                metric(f"{tag}_{key}", value)
            if error:
                metric(f"{tag}_error", error)
                continue
            result = score(eligible, rows or [])
            for key, value in sorted(result.items()):
                metric(f"{tag}_{key}", value)
            scores.append(float(result["quality_score"]))
        if scores:
            measured += 1
            metric(f"{name}_quality_score", min(scores))
        else:
            metric(f"{name}_quality_score", "unmeasured")
    return 0 if measured else 1


if __name__ == "__main__":
    raise SystemExit(main())
