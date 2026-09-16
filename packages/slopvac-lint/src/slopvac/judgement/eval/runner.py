"""Deterministic judgement evaluation runner and result aggregation.

The runner deliberately keeps provider transport small: providers return a response
object, while this module owns parsing, validation, cache identity, and coverage.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

TOKEN_FIELDS = {
    "promptTokens": "prompt_tokens", "completionTokens": "completion_tokens",
    "cachedPromptTokens": "cached_prompt_tokens", "reasoningTokens": "reasoning_tokens",
}
ABSTAIN_REASONS = {
    "ambiguous_unit", "conflicting_context", "missing_context", "needs_external_fact",
    "needs_repository_fact", "no_exact_evidence", "unit_out_of_scope",
}
COVERAGE_COUNTS = ("eligible", "attempted", "confirmed", "rejected", "preserved", "abstained", "failed", "truncated", "not_run")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def judgement_cache_key(*, instrument_id: str, unit_id: str, context_hash: str = "", provider: str,
                        model_id_and_revision: str, full_rendered_request_digest: str,
                        system_prompt: str, decoding_config: dict[str, Any], seed: int | None,
                        repeat_index: int, evaluator_runner_revision: str) -> str:
    fields = {"instrument_id": instrument_id, "unit_id": unit_id + context_hash,
              "provider": provider, "model_id_and_revision": model_id_and_revision,
              "full_rendered_request_digest": full_rendered_request_digest,
              "system_prompt": system_prompt, "decoding_config": decoding_config,
              "seed": seed, "repeat_index": repeat_index,
              "evaluator_runner_revision": evaluator_runner_revision}
    return hashlib.sha256(canonical_bytes(fields)).hexdigest()


def outer_payloads(text: str) -> list[dict[str, Any]]:
    """Extract top-level ``results`` objects from prose, fenced, or plain JSON."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text, flags=re.I).replace("```", "")
    decoder, found, position = json.JSONDecoder(), [], 0
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


def message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str))
    # OpenAI-compatible responses sometimes put text in output_text.
    if isinstance(message.get("output_text"), str):
        return message["output_text"]
    return ""


def parse_provider_response(response: Any) -> list[dict[str, Any]]:
    """Parse plain text, assistant messages, or event transcripts."""
    if isinstance(response, str):
        text = response
    elif isinstance(response, dict):
        if isinstance(response.get("results"), list):
            return [response]
        if isinstance(response.get("choices"), list):
            text = message_text(response["choices"][-1].get("message", {})) if response["choices"] else ""
        else:
            text = message_text(response)
    elif isinstance(response, list):
        messages = stream_messages(response, "assistant")
        text = message_text(messages[-1]) if messages else ""
    else:
        raise ValueError("malformed provider response")
    payloads = outer_payloads(text)
    if not payloads:
        raise ValueError("malformed provider result payload")
    return payloads


def _fingerprint(message: dict[str, Any]) -> str:
    return json.dumps(message, sort_keys=True, default=str, separators=(",", ":"))


def stream_messages(events: list[Any], role: str = "assistant") -> list[dict[str, Any]]:
    settled = [e["message"] for e in events if isinstance(e, dict) and e.get("type") == "message_end" and isinstance(e.get("message"), dict) and e["message"].get("role") == role]
    source = settled or [m for e in events if isinstance(e, dict) and e.get("type") == "agent_end" for m in (e.get("messages") or []) if isinstance(m, dict) and m.get("role") == role]
    seen: set[str] = set()
    return [m for m in source if not (_fingerprint(m) in seen or seen.add(_fingerprint(m)))]


def usage(messages: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    if not messages:
        return None, "usage_error: no assistant message carried usage"
    totals = {name: 0 for name in TOKEN_FIELDS.values()} | {"cost_usd": 0.0, "request_count": 0}
    for message in messages:
        block = message.get("usage")
        if not isinstance(block, dict):
            return None, "usage_error: assistant message has no usage object"
        for raw, name in TOKEN_FIELDS.items():
            value = block.get(raw)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return None, f"usage_error: usage.{raw} is not a non-negative integer"
            totals[name] += value
        cost = block.get("cost", {}).get("total") if isinstance(block.get("cost"), dict) else None
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            return None, "usage_error: usage.cost.total is not a non-negative number"
        totals["cost_usd"] += float(cost)
        totals["request_count"] += 1
    return totals, ""


def validate_result_set(units: list[dict[str, Any]], rows: Any) -> str | None:
    expected = [str(u["unit_id"]) for u in units]
    if not isinstance(rows, list):
        return "results is not a list"
    actual = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("unit_id"), str):
            return "result row missing unit_id"
        actual.append(row["unit_id"])
    duplicates = sorted({x for x in actual if actual.count(x) > 1})
    if duplicates:
        return "duplicate unit_id: " + ",".join(duplicates)
    unknown = sorted(set(actual) - set(expected))
    if unknown:
        return "unknown unit_id: " + ",".join(unknown)
    missing = [x for x in expected if x not in actual]
    if missing:
        return "missing unit_id: " + ",".join(missing)
    if actual != expected:
        return "result unit_ids are not in expected order"
    return None

def select_units(units: list[dict[str, Any]], *, partition: str | None = None,
                 unit: str | None = None) -> list[dict[str, Any]]:
    """Apply stable partition and unit selectors without changing source order."""
    selected = units
    if partition is not None:
        selected = [item for item in selected if item.get("partition") == partition]
    if unit is not None:
        selected = [item for item in selected if str(item.get("unit_id")) == unit]
    return selected


def select_repeats(repeat_count: int, repeats: str | None = None) -> list[int]:
    """Return zero-based repeat indexes from a comma-separated selector."""
    if repeats is None:
        return list(range(repeat_count))
    values = {int(part) for part in repeats.split(",") if part.strip()}
    if any(value < 0 or value >= repeat_count for value in values):
        raise ValueError("repeat selector is outside the arm repeat range")
    return sorted(values)


@dataclass(frozen=True)
class Arm:
    id: str
    provider: str
    model_id_and_revision: str
    decoding_config: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    repeats: int = 1


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    independent_variable: str
    frozen_fields: dict[str, Any]
    arms: tuple[Arm, ...] = ()


@dataclass
class HostRecord:
    instrument_id: str
    unit_id: str
    repeat_index: int
    judgement_cache_key: str
    model_output: dict[str, Any] | None
    status: str
    abstain_reason: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    full_rendered_request_digest: str = ""
    frozen_fields: dict[str, Any] = field(default_factory=dict)

def aggregate(records: list[HostRecord], *, eligible: int | None = None) -> dict[str, Any]:
    if not records:
        return {"coverage": {key: 0 for key in COVERAGE_COUNTS}, "abstentions": {}}
    baseline = records[0].frozen_fields
    if any(record.frozen_fields != baseline for record in records):
        raise ValueError("cannot aggregate rows with differing frozen fields")
    counts = {key: 0 for key in COVERAGE_COUNTS}
    counts["eligible"] = eligible if eligible is not None else len(records)
    reasons: dict[str, int] = {}
    for record in records:
        status = "abstained" if record.status == "abstain" else record.status
        counts["attempted"] += status != "not_run"
        if status in counts and status not in {"eligible", "attempted"}:
            counts[status] += 1
        if status == "abstained":
            reason = record.abstain_reason or "unknown"
            reasons[reason] = reasons.get(reason, 0) + 1
    return {"coverage": counts, "abstentions": reasons}




class ReplayProvider:
    """Serve deterministic provider responses from a JSONL fixture."""
    def __init__(self, path: str | Path):
        self._responses = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
        self._index = 0

    def request(self, request: Any = None) -> Any:
        if self._index >= len(self._responses):
            raise LookupError("replay fixture exhausted")
        response = self._responses[self._index]
        self._index += 1
        return response.get("response", response) if isinstance(response, dict) else response

    __call__ = request


class Provider(Protocol):
    def request(self, request: Any = None) -> Any: ...
