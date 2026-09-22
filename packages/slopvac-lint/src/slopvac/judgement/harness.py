"""Harness-facing judgement helpers: per-call response validation and agent briefs.

`prepare` writes provider-neutral `prompts.jsonl`; any runner answers those rows.
This module gives such runners two things the batch path never needed:

- `validate_call`: the per-call checks `finish` applies, runnable on one response
  before it is appended to `responses.jsonl`. A Claude Code `SubagentStop` hook, an
  OMP strict-schema subagent, or a plain script can all use it.
- `brief`: `prepare` with pack selection plus one Markdown bundle an agent can read
  end to end, so a judge is dispatched from a file rather than from JSONL rows.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from ..config import find_config
from ..templates import STARTER_CONFIG
from . import driver
from .eval.runner import validate_result_set
from .packs import _PROBE_PACKS
from .schema import validate_model_output

_FENCE = re.compile(r"```(?:json)?\s*|```", re.IGNORECASE)


def first_json_object(text: str) -> dict[str, Any] | None:
    """Return the first top-level JSON object embedded in `text`, fences tolerated."""
    cleaned = _FENCE.sub("", text)
    decoder = json.JSONDecoder()
    position = 0
    while True:
        start = cleaned.find("{", position)
        if start < 0:
            return None
        try:
            value, _ = decoder.raw_decode(cleaned[start:])
        except json.JSONDecodeError:
            position = start + 1
            continue
        return value if isinstance(value, dict) else None


def _message_text(message: Any) -> str | None:
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
    return None


def unwrap_response(source: Any) -> tuple[Any, str | None, bool, list[str]]:
    """Accept a bare response, a `{call_id, response}` row, or a SubagentStop payload.

    Returns `(payload, call_id, stop_hook_active, errors)`.
    """
    if not isinstance(source, dict):
        return source, None, False, []
    if "last_assistant_message" in source:
        text = _message_text(source.get("last_assistant_message"))
        payload = first_json_object(text) if text is not None else None
        errors = (
            []
            if payload is not None
            else ["response_json: last_assistant_message has no top-level JSON object"]
        )
        call_id = source.get("call_id")
        return (
            payload,
            (str(call_id) if isinstance(call_id, str) else None),
            bool(source.get("stop_hook_active")),
            errors,
        )
    if "response" in source and "results" not in source:
        call_id = source.get("call_id")
        try:
            payload = driver._response_payload(source.get("response"))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return (
                None,
                (str(call_id) if isinstance(call_id, str) else None),
                False,
                [f"response_json: {exc}"],
            )
        return payload, (str(call_id) if isinstance(call_id, str) else None), False, []
    return source, None, False, []


def _resolve_call(
    out: Path, payload: Any, call_id: str | None
) -> tuple[str | None, list[str]]:
    calls = driver._find_call_prompts(out)
    if call_id is not None:
        if call_id not in calls:
            return call_id, [f"unknown call_id: {call_id}"]
        return call_id, []
    if not isinstance(payload, dict):
        return None, []
    rows = payload.get("results") if "results" in payload else [payload]
    if not isinstance(rows, list):
        return None, []
    row_ids = {str(row.get("unit_id")) for row in rows if isinstance(row, dict)}
    matches = [
        cid
        for cid, call in calls.items()
        if row_ids and row_ids <= set(map(str, call.get("unit_ids", ())))
    ]
    if len(matches) == 1:
        return matches[0], []
    return None, []


def validate_call(
    *, out: Path, payload: Any, call_id: str | None = None
) -> tuple[str | None, list[str]]:
    """Apply `finish`'s per-call checks to one response payload.

    Returns `(call_id, errors)`; an empty list means the row would be accepted.
    """
    call_id, errors = _resolve_call(out, payload, call_id)
    if errors:
        return call_id, errors
    units = {
        str(item["unit_id"]): item for item in driver._read_jsonl(out / "units.jsonl")
    }
    target_units: list[dict[str, Any]] = []
    if call_id is not None:
        call = driver._find_call_prompts(out)[call_id]
        target_units = [units[uid] for uid in call.get("unit_ids", ()) if uid in units]
    if isinstance(payload, dict) and "results" in payload:
        rows = payload.get("results")
    elif isinstance(payload, dict) and len(target_units) <= 1:
        rows = [payload]
    else:
        rows = None
    if (
        rows is None
        or not isinstance(rows, list)
        or not all(isinstance(row, dict) for row in rows)
    ):
        return call_id, ["response shape: expected an object with a results array"]
    if target_units:
        failure = validate_result_set(target_units, rows)
        if failure is not None:
            return call_id, [failure]
    row_errors: list[str] = []
    for row in rows:
        row = {key: value for key, value in row.items() if key != "passage_id"}
        row_errors.extend(validate_model_output(row))
    return call_id, row_errors


_SPAN_ID = re.compile(r"^SPAN-(.+)-\d+$")
_PROBE_CATEGORIES = {
    f"PROBE-{chunk}": tuple(categories) for chunk, categories, _, _ in _PROBE_PACKS
}


def _fired_pack_ids(out: Path, all_pack_ids: list[str]) -> list[str]:
    fired: set[str] = set()
    for report in (out / "deterministic").glob("*.json"):
        data = json.loads(report.read_text(encoding="utf-8"))
        fired.update(
            str(finding.get("category", "")) for finding in data.get("findings", [])
        )
    fired.discard("")
    return [pid for pid in all_pack_ids if set(_pack_categories(pid)) & fired]


def _pack_categories(pack_id: str) -> tuple[str, ...]:
    match = _SPAN_ID.match(pack_id)
    if match:
        return (match.group(1),)
    return _PROBE_CATEGORIES.get(pack_id, ())


def _pack_index(manifest: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for doc in manifest.get("documents", []):
        for pid in doc.get("pack_ids", []):
            if pid not in ids:
                ids.append(pid)
    return ids


def brief(
    *,
    paths: tuple[Path, ...],
    out: Path,
    packs: str = "fired",
    profile: str | None = None,
    max_calls: int = 300,
    config: Path | None = None,
) -> dict[str, Any]:
    """Run `prepare` with pack selection and write an agent-readable brief.

    `packs="fired"` keeps only packs whose category produced a deterministic finding
    on the target; a clean target falls back to every pack with a warning.
    """
    warning: str | None = None
    config_path = config or find_config(Path.cwd())
    scratch: tempfile.TemporaryDirectory[str] | None = None
    if config_path is None:
        scratch = tempfile.TemporaryDirectory(prefix="slopvac-brief-")
        config_path = Path(scratch.name) / "slopvac.toml"
        config_path.write_text(
            STARTER_CONFIG.format(profile=profile or "normal"), encoding="utf-8"
        )
    try:
        selection = packs
        if packs.strip().lower() == "fired":
            # A first prepare over every pack yields the deterministic reports and
            # the pack index; the second run narrows to the fired categories.
            manifest = driver.prepare(
                config=config_path,
                out=out,
                paths=paths,
                profile=profile,
                packs="all",
                max_calls=max_calls,
                yes=True,
            )
            selected = _fired_pack_ids(out, _pack_index(manifest))
            if selected:
                selection = ",".join(selected)
            else:
                selection = "all"
                warning = "no deterministic finding on the target; every pack was kept"
        manifest = driver.prepare(
            config=config_path,
            out=out,
            paths=paths,
            profile=profile,
            packs=selection,
            max_calls=max_calls,
            yes=True,
        )
    finally:
        if scratch is not None:
            scratch.cleanup()
    prompts = driver._read_jsonl(out / "prompts.jsonl")
    calls = [
        {
            "call_id": str(row["call_id"]),
            "pack_id": str(row.get("pack_id", "")),
            "unit_ids": list(row.get("unit_ids", [])),
        }
        for row in prompts
    ]
    schema_path = out / "response_schema.json"
    schema = prompts[0]["response_schema"] if prompts else {}
    schema_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pack_ids = sorted({call["pack_id"] for call in calls})
    (out / "brief.json").write_text(
        json.dumps(
            {"calls": calls, "packs": pack_ids, "schema_path": str(schema_path)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out / "brief.md").write_text(
        _render_brief(paths, out, prompts, pack_ids, selection, warning, schema),
        encoding="utf-8",
    )
    return {
        "calls": calls,
        "packs": pack_ids,
        "path": out / "brief.md",
        "warning": warning,
        "manifest": manifest,
    }


def _render_brief(
    paths: tuple[Path, ...],
    out: Path,
    prompts: list[dict[str, Any]],
    pack_ids: list[str],
    selection: str,
    warning: str | None,
    schema: dict[str, Any],
) -> str:
    lines = ["# slopvac judgement brief", ""]
    lines.append("Files: " + ", ".join(f"`{path}`" for path in paths))
    reason = (
        "every pack"
        if selection == "all"
        else "packs whose category fired in the deterministic gate"
    )
    lines.append(
        f"Packs ({reason}): " + (", ".join(f"`{pid}`" for pid in pack_ids) or "none")
    )
    if warning:
        lines.append(f"Warning: {warning}")
    lines.append(f"Calls: {len(prompts)}")
    lines.append("")
    lines.append(
        'Answer every call below. Write one `{"call_id": ..., "response": ...}` JSON row per call to'
    )
    lines.append(f"`{out / 'responses.jsonl'}`, then run:")
    lines.append("")
    lines.append("```sh")
    lines.append(
        f"slopvac judgement validate --run {out} --call-id <call_id> --file <response.json>"
    )
    lines.append(
        f"slopvac judgement finish --out {out} --responses {out / 'responses.jsonl'}"
    )
    lines.append(f"slopvac judgement compare --out {out} --apply-preview")
    lines.append("```")
    lines.append("")
    if prompts:
        lines.append("## System text (shared by every call)")
        lines.append("")
        lines.append(prompts[0]["prompt"]["system"].rstrip())
        lines.append("")
    for row in prompts:
        lines.append(f"### call {row['call_id']}")
        lines.append("")
        lines.append(
            f"Pack `{row.get('pack_id', '')}`; units: "
            + ", ".join(map(str, row.get("unit_ids", [])))
        )
        lines.append("")
        lines.append("```json")
        lines.append(row["prompt"]["user"].rstrip())
        lines.append("```")
        lines.append("")
    lines.append("## Response schema")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(schema, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("Respond with the JSON object only.")
    lines.append("")
    return "\n".join(lines)
