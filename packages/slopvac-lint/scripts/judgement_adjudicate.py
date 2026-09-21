#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3", "click", "jsonschema", "markdown-it-py", "pathspec", "pydantic", "pyyaml", "regex", "rich"]
# ///
"""Adjudicate judgement CONFIRMs with an independent Bedrock model.

The command intentionally keeps transport here rather than in the judgement driver:
``finish`` remains deterministic, while this script provides a standing post-finish
review step and a network-free report regeneration path.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import unquote

try:
    import boto3
except ModuleNotFoundError:  # tests and report mode do not require transport
    boto3 = None

try:
    from slopvac.rules import load_ruleset
except ModuleNotFoundError:  # direct invocation from a source checkout
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from slopvac.rules import load_ruleset


MODEL_DEFAULT = "global.openai.gpt-5.6-sol"
EFFORT_DEFAULT = "high"
MAX_COMPLETION_TOKENS = 16_000
MAX_BATCH = 3
FP_PATTERNS = (
    "attributed-claim",
    "finite-set",
    "quoted-speech",
    "heading",
    "code-or-list",
    "genre-convention",
    "bounded-guidance",
    "fragment-anaphora",
    "other",
)
VERDICTS = ("TP", "FP", "borderline")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSONL rows, preserving malformed rows as a useful error."""
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: expected a JSON object")
            rows.append(value)
    return rows


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _rows_from_confirms(path: Path) -> list[dict[str, Any]]:
    value = _read_json(path, [])
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        for key in ("confirms", "findings", "rows", "results"):
            rows = value.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    raise ValueError(f"{path}: expected a list or an object containing confirms")


def load_confirms(run_dir: Path, class_name: str | None = None) -> list[dict[str, Any]]:
    """Read confirms.json, falling back to finish's findings.jsonl.

    The v2 evaluation predates ``confirms.json`` and therefore exercises the
    fallback. New finish output may provide the smaller explicit confirms file.
    """
    source_dir = (
        run_dir / class_name
        if class_name and (run_dir / class_name).is_dir()
        else run_dir
    )
    path = source_dir / "confirms.json"
    rows = (
        _rows_from_confirms(path)
        if path.exists()
        else load_jsonl(source_dir / "findings.jsonl")
    )
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if str(row.get("outcome", "")).upper() != "CONFIRM":
            continue
        row_class = row.get("class") or row.get("source_class")
        if class_name and row_class and str(row_class).lower() != class_name.lower():
            continue
        unit_id = str(row.get("unit_id", ""))
        if not unit_id or unit_id in seen:
            continue
        seen.add(unit_id)
        result.append(row)
    return result


def _unit_path(unit: Mapping[str, Any]) -> str | None:
    for key in ("path", "document", "document_path", "document_ref"):
        value = unit.get(key)
        if value:
            return unquote(str(value))
    return None


def resolve_document(unit: Mapping[str, Any], corpus_root: Path) -> Path | None:
    """Resolve an evaluation unit's document without trusting its stored cwd."""
    raw = _unit_path(unit)
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    choices = [candidate] if candidate.is_absolute() else []
    choices.extend((corpus_root / candidate, corpus_root / candidate.name))
    for item in choices:
        if item.is_file():
            return item
    return None


def _sentence_ranges(text: str) -> list[tuple[int, int]]:
    """Return simple sentence ranges suitable for context, not linguistic parsing."""
    ranges: list[tuple[int, int]] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])(?:[\"'”’)]*)\s+|\n\s*\n+", text):
        end = match.start() + 1
        if text[start:end].strip():
            ranges.append((start, end))
        start = match.end()
    if text[start:].strip():
        ranges.append((start, len(text)))
    return ranges or [(0, len(text))]


def resolve_passage(
    unit: Mapping[str, Any], corpus_root: Path, context_sentences: int = 2
) -> tuple[str, bool]:
    """Resolve a unit and include up to two sentences on either side."""
    document = resolve_document(unit, corpus_root)
    if document is None:
        return str(unit.get("context") or unit.get("model_context") or ""), False
    try:
        text = document.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return str(unit.get("context") or unit.get("model_context") or ""), False
    raw_range = unit.get("source_range") or unit.get("doc_range") or [-1, -1]
    try:
        start, end = max(0, int(raw_range[0])), max(0, int(raw_range[1]))
    except (TypeError, ValueError, IndexError):
        start, end = 0, 0
    if start > len(text):
        return str(unit.get("context") or ""), False
    end = min(len(text), max(start, end))
    ranges = _sentence_ranges(text)
    selected = [
        index
        for index, (left, right) in enumerate(ranges)
        if left < end and right > start
    ]
    if not selected:
        selected = [min(range(len(ranges)), key=lambda i: abs(ranges[i][0] - start))]
    left = max(0, selected[0] - context_sentences)
    right = min(len(ranges), selected[-1] + context_sentences + 1)
    return text[ranges[left][0] : ranges[right - 1][1]].strip(), True


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return {
            key: _plain(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def rule_metadata(rules: Iterable[Any] | None = None) -> dict[str, dict[str, Any]]:
    """Build a qualified-id lookup containing each question and its examples."""
    loaded = (
        list(rules)
        if rules is not None
        else load_ruleset([], verify=False).judgement_rules()
    )
    result: dict[str, dict[str, Any]] = {}
    for rule in loaded:
        rid = str(getattr(rule, "qualified_id", getattr(rule, "id", "")))
        if not rid:
            continue
        examples = _plain(getattr(rule, "examples", ())) or []
        question = getattr(rule, "judgement_question", None)
        if question is None:
            judgement = getattr(rule, "judgement", None)
            question = getattr(judgement, "question", None) if judgement else None
        result[rid] = {"question": str(question or ""), "examples": examples}
        # Historical findings sometimes store only the rule suffix.
        suffix = rid.rsplit(".", 1)[-1]
        result.setdefault(suffix, result[rid])
    return result


def build_prompt(
    rule_id: str,
    items: Sequence[Mapping[str, Any]],
    rules: Mapping[str, Mapping[str, Any]],
) -> str:
    """Construct the strict, self-contained Sol adjudication prompt."""
    metadata = rules.get(rule_id) or rules.get(rule_id.rsplit(".", 1)[-1], {})
    question = str(metadata.get("question", ""))
    examples = metadata.get("examples", [])
    body: list[str] = []
    for item in items:
        body.append(
            "UNIT {unit_id}\nQUOTE: {quote}\nPASSAGE: {passage}\nJUDGE NOTE: {note}".format(
                unit_id=item.get("unit_id", ""),
                quote=item.get("quote", ""),
                passage=item.get("passage", ""),
                note=item.get("judge_note", ""),
            )
        )
    return (
        f"Rule: {rule_id}\nJudgement question: {question}\n"
        f"Examples: {json.dumps(examples, ensure_ascii=False, default=str)}\n"
        "Assumption: Pre-2022 human text carries no AI tells; a human confirm is "
        "a candidate FP unless the passage genuinely exhibits the tell.\n"
        f"Classify each as TP, FP, or borderline. fp_pattern must be one of {list(FP_PATTERNS)}. "
        "Reason in at most 40 words. Respond with ONLY one JSON object: "
        '{"results":[{"unit_id":"...","verdict":"TP|FP|borderline",'
        '"reason":"...","fp_pattern":"..."}]}\n\n' + "\n\n".join(body)
    )


def build_messages(
    rule_id: str,
    items: Sequence[Mapping[str, Any]],
    rules: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": "You are an independent adjudicator. Follow the requested JSON contract exactly.",
        },
        {"role": "user", "content": build_prompt(rule_id, items, rules)},
    ]


def parse_json_response(text: str) -> dict[str, Any]:
    """Parse an object from plain, fenced, or surrounding-garbage model output."""
    if not isinstance(text, str):
        raise ValueError("response is not text")
    first, last = text.find("{"), text.rfind("}")
    if first < 0 or last < first:
        raise ValueError("no JSON object")
    value = json.loads(text[first : last + 1])
    if not isinstance(value, dict):
        raise ValueError("JSON response is not an object")
    return value


def validate_rows(
    value: Mapping[str, Any], ids: Sequence[str]
) -> tuple[list[dict[str, Any]] | None, str | None]:
    rows = value.get("results")
    if not isinstance(rows, list):
        return None, "not-object-results"
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            return None, "schema"
        if str(row.get("unit_id")) not in ids or row.get("verdict") not in VERDICTS:
            return None, "schema"
        if row.get("fp_pattern") not in FP_PATTERNS:
            return None, "schema"
        if len(str(row.get("reason", "")).split()) > 40:
            return None, "schema"
        result.append(row)
    if {row["unit_id"] for row in result} != set(ids):
        return None, "missing-unit"
    return result, None


def _response_text(response: Mapping[str, Any]) -> str:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def call_sol(
    client: Any,
    rule_id: str,
    items: Sequence[Mapping[str, Any]],
    rules: Mapping[str, Mapping[str, Any]],
    *,
    model_id: str = MODEL_DEFAULT,
    reasoning_effort: str = EFFORT_DEFAULT,
) -> dict[str, Any]:
    """Call Sol once, retrying a length stop with doubled completion budget."""
    ids = [str(item["unit_id"]) for item in items]
    messages = build_messages(rule_id, items, rules)
    errors: list[str] = []
    response: Mapping[str, Any] | None = None
    max_tokens = MAX_COMPLETION_TOKENS
    for attempt in range(2):
        request = {
            "messages": messages,
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": max_tokens,
        }
        started = time.monotonic()
        try:
            raw = client.invoke_model(
                modelId=model_id,
                body=json.dumps(request, ensure_ascii=False).encode(),
                contentType="application/json",
                accept="application/json",
            )
            body = (
                raw["body"].read()
                if hasattr(raw.get("body"), "read")
                else raw.get("body", raw)
            )
            response = (
                json.loads(body) if isinstance(body, (str, bytes, bytearray)) else body
            )
            finish_reason = (response.get("choices") or [{}])[0].get("finish_reason")
            if finish_reason == "length":
                errors.append("finish_reason=length")
                max_tokens *= 2
                continue
            if finish_reason not in (None, "stop"):
                raise ValueError(f"finish_reason={finish_reason}")
            parsed = parse_json_response(_response_text(response))
            rows, why = validate_rows(parsed, ids)
            if rows is not None:
                return {
                    "model_id": model_id,
                    "reasoning_effort": reasoning_effort,
                    "rule_id": rule_id,
                    "unit_ids": ids,
                    "request": request,
                    "response": response,
                    "valid_json": True,
                    "rows": rows,
                    "attempt": attempt,
                    "elapsed_s": time.monotonic() - started,
                }
            errors.append(str(why))
        except Exception as exc:  # retain transport/parser errors for report inspection
            errors.append(repr(exc))
    return {
        "model_id": model_id,
        "reasoning_effort": reasoning_effort,
        "rule_id": rule_id,
        "unit_ids": ids,
        "request": {
            "messages": messages,
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
        },
        "response": response,
        "valid_json": False,
        "parse_error": errors or ["parse_error"],
        "rows": [],
    }


def _unit_records(
    run_dir: Path, confirms: Sequence[Mapping[str, Any]], corpus_root: Path
) -> list[dict[str, Any]]:
    ids = {str(row.get("unit_id")) for row in confirms}
    units_path = run_dir / "units.jsonl"
    units: dict[str, dict[str, Any]] = {}
    if units_path.exists():
        with units_path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                unit = json.loads(line)
                if str(unit.get("unit_id")) in ids:
                    units[str(unit["unit_id"])] = unit
    result: list[dict[str, Any]] = []
    for confirm in confirms:
        unit_id = str(confirm.get("unit_id"))
        unit = {**units.get(unit_id, {}), **confirm}
        passage, resolved = resolve_passage(unit, corpus_root)
        evidence = unit.get("evidence") or confirm.get("evidence") or []
        quote = next(
            (
                entry.get("quote")
                for entry in evidence
                if isinstance(entry, dict) and entry.get("quote")
            ),
            None,
        )
        result.append(
            {
                "unit_id": unit_id,
                "rule_id": str(confirm.get("rule_id") or unit.get("rule_id") or ""),
                "document": _unit_path(unit) or "",
                "quote": quote
                or unit.get("model_text")
                or unit.get("text")
                or unit.get("context")
                or "",
                "passage": passage,
                "resolved": resolved,
                "judge_note": confirm.get("preservation_reason")
                or confirm.get("attempted_rewrite")
                or "",
                "source": unit,
            }
        )
    return result


def _attempted_by_rule(run_dir: Path) -> dict[str, int]:
    report = _read_json(run_dir / "report.json", {}) or {}
    result: dict[str, int] = {}
    coverage = report.get("coverage") or {}
    for key in ("rules", "per_rule"):
        mapping = coverage.get(key) if isinstance(coverage, dict) else None
        if not isinstance(mapping, dict):
            mapping = report.get(key)
        if isinstance(mapping, dict):
            for rid, value in mapping.items():
                if isinstance(value, Mapping) and value.get("attempted") is not None:
                    result[str(rid)] = int(value["attempted"])
    return result


def _saved_calls(out_dir: Path) -> list[dict[str, Any]]:
    calls = out_dir / "calls"
    result: list[dict[str, Any]] = []
    for path in sorted(calls.glob("*.json")):
        if path.name == "probe.json":
            continue
        value = _read_json(path)
        if isinstance(value, dict):
            result.append(value)
    return result


def consistency_report(
    out_dir: Path, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Summarise repeated calls as per-unit tuples, flips, and majorities."""
    calls = _saved_calls(out_dir)
    by_unit: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for call in calls:
        repeat = int(call.get("repeat", 1))
        for row in call.get("rows", []):
            by_unit[str(row.get("unit_id"))][repeat] = row
    record_by_id = {str(record["unit_id"]): record for record in records}
    units: list[dict[str, Any]] = []
    for unit_id in sorted(record_by_id):
        answers = by_unit.get(unit_id, {})
        repeats = sorted(answers)
        verdicts = [
            str(answers[index].get("verdict", "parse_error")) for index in repeats
        ]
        counts = Counter(verdicts)
        majority = counts.most_common(1)[0][0] if counts else "parse_error"
        majority_rows = [
            answers[index]
            for index in repeats
            if answers[index].get("verdict") == majority
        ]
        units.append(
            {
                "unit_id": unit_id,
                "rule_id": str(record_by_id[unit_id]["rule_id"]),
                "repeats": repeats,
                "verdicts": verdicts,
                "majority": majority,
                "majority_fp_pattern": (
                    majority_rows[0].get("fp_pattern", "other")
                    if majority_rows
                    else "other"
                ),
                "flipped": len(set(verdicts)) > 1,
            }
        )
    denominator = len(units)
    per_rule: dict[str, dict[str, Any]] = {}
    for rule_id in sorted({unit["rule_id"] for unit in units}):
        selected = [unit for unit in units if unit["rule_id"] == rule_id]
        flips = sum(bool(unit["flipped"]) for unit in selected)
        per_rule[rule_id] = {
            "units": len(selected),
            "flips": flips,
            "flip_rate": flips / len(selected) if selected else None,
            "majority": Counter(unit["majority"] for unit in selected),
        }
        per_rule[rule_id]["majority"] = dict(per_rule[rule_id]["majority"])
    payload = {
        "repeats": sorted({repeat for unit in units for repeat in unit["repeats"]}),
        "units": units,
        "flip_rate": sum(bool(unit["flipped"]) for unit in units) / denominator
        if denominator
        else None,
        "flips": sum(bool(unit["flipped"]) for unit in units),
        "unit_count": denominator,
        "per_rule": per_rule,
    }
    (out_dir / "consistency.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Adjudicator consistency",
        "",
        f"Repeats: {payload['repeats']}; units: {denominator}; flips: {payload['flips']}; overall flip rate: {_format_rate(payload['flip_rate'])}",
        "",
        "| rule | units | flips | flip rate | majority TP | majority FP | majority borderline | parse_error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rule_id, stat in sorted(per_rule.items()):
        majority = stat["majority"]
        lines.append(
            f"| {rule_id} | {stat['units']} | {stat['flips']} | {_format_rate(stat['flip_rate'])} | {majority.get('TP', 0)} | {majority.get('FP', 0)} | {majority.get('borderline', 0)} | {majority.get('parse_error', 0)} |"
        )
    lines.extend(
        (
            "",
            "| unit | rule | verdict tuple | majority | flipped |",
            "|---|---|---|---|---|",
        )
    )
    for unit in units:
        lines.append(
            f"| {unit['unit_id']} | {unit['rule_id']} | {', '.join(unit['verdicts'])} | {unit['majority']} | {unit['flipped']} |"
        )
    (out_dir / "CONSISTENCY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def table_math(
    rows: Sequence[Mapping[str, Any]], attempted: int | None
) -> dict[str, Any]:
    counts = Counter(str(row.get("verdict", "parse_error")) for row in rows)
    adjudicated = counts["TP"] + counts["FP"] + counts["borderline"]
    fp_share = counts["FP"] / adjudicated if adjudicated else None
    fp_incidence = counts["FP"] / attempted if attempted else None
    return {
        "confirms": len(rows),
        "TP": counts["TP"],
        "FP": counts["FP"],
        "borderline": counts["borderline"],
        "parse_error": counts["parse_error"],
        "adjudicated": adjudicated,
        "fp_share_of_adjudicated_confirms": fp_share,
        "attempted_units": attempted,
        "fp_incidence_per_attempted_unit": fp_incidence,
        "dominant_fp_pattern": Counter(
            row.get("fp_pattern", "other") for row in rows if row.get("verdict") == "FP"
        ).most_common(1)[0][0]
        if any(row.get("verdict") == "FP" for row in rows)
        else "none",
    }


def write_reports(
    out_dir: Path, run_dir: Path, records: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    attempted = _attempted_by_rule(run_dir)
    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    saved = _saved_calls(out_dir)
    consistency = _read_json(out_dir / "consistency.json", {}) or {}
    if isinstance(consistency.get("units"), list):
        answers = {
            str(row["unit_id"]): {
                "verdict": row.get("majority", "parse_error"),
                "fp_pattern": row.get("majority_fp_pattern", "other"),
                "reason": "majority of repeated Sol calls",
            }
            for row in consistency["units"]
        }
    else:
        answers = {
            str(row["unit_id"]): row for call in saved for row in call.get("rows", [])
        }
    for record in records:
        answer = answers.get(
            str(record["unit_id"]),
            {"verdict": "parse_error", "reason": "parse_error", "fp_pattern": "other"},
        )
        by_rule[str(record["rule_id"])].append({**record, **answer})
    stats: dict[str, dict[str, Any]] = {}
    for rule_id, rows in sorted(by_rule.items()):
        stats[rule_id] = table_math(rows, attempted.get(rule_id))
        path = out_dir / f"{rule_id}.md"
        lines = [
            f"# {rule_id}",
            "",
            f"Human confirms: {stats[rule_id]['confirms']} (TP {stats[rule_id]['TP']}, FP {stats[rule_id]['FP']}, borderline {stats[rule_id]['borderline']}, parse_error {stats[rule_id]['parse_error']})",
            f"FP share of adjudicated confirms: {_format_rate(stats[rule_id]['fp_share_of_adjudicated_confirms'])}",
            f"FP incidence per attempted unit: {_format_rate(stats[rule_id]['fp_incidence_per_attempted_unit'])} (attempted {stats[rule_id]['attempted_units'] if stats[rule_id]['attempted_units'] is not None else 'unknown'})",
            "",
            "| unit | document | quote | verdict | fp_pattern | Sol reason |",
            "|---|---|---|---|---|---|",
        ]
        for row in rows:
            lines.append(
                "| "
                + " | ".join(
                    _md(str(row.get(key, "")), limit)
                    for key, limit in (
                        ("unit_id", 20),
                        ("document", 40),
                        ("quote", 120),
                        ("verdict", 20),
                        ("fp_pattern", 24),
                        ("reason", 80),
                    )
                )
                + " |"
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_lines = [
        "# Sol adjudication summary",
        "",
        "| rule | confirms | TP | FP | borderline | parse_error | FP share (adjudicated) | attempted | FP incidence (attempted) | dominant fp_pattern |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rid, stat in sorted(stats.items(), key=lambda item: (-item[1]["FP"], item[0])):
        summary_lines.append(
            "| "
            + " | ".join(
                str(value)
                for value in (
                    rid,
                    stat["confirms"],
                    stat["TP"],
                    stat["FP"],
                    stat["borderline"],
                    stat["parse_error"],
                    _format_rate(stat["fp_share_of_adjudicated_confirms"]),
                    stat["attempted_units"]
                    if stat["attempted_units"] is not None
                    else "unknown",
                    _format_rate(stat["fp_incidence_per_attempted_unit"]),
                    stat["dominant_fp_pattern"],
                )
            )
            + " |"
        )
    (out_dir / "SUMMARY.md").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8"
    )
    with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["rule", *next(iter(stats.values()), {"confirms": 0}).keys()],
        )
        writer.writeheader()
        for rid, stat in sorted(stats.items()):
            writer.writerow({"rule": rid, **stat})
    (out_dir / "summary.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return stats


def _format_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _md(value: str, limit: int) -> str:
    return re.sub(r"\s+", " ", value).strip()[:limit].replace("|", "\\|")


def run(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = args.run_dir.resolve()
    out_dir = args.out.resolve()
    confirms = load_confirms(run_dir, args.class_name)
    records = _unit_records(run_dir, confirms, args.corpus_root.resolve())
    if args.rule_id:
        records = [record for record in records if record["rule_id"] == args.rule_id]
    rules = rule_metadata()
    if boto3 is None:
        raise RuntimeError("boto3 is required for run; use PEP 723 uv invocation")
    client = boto3.client("bedrock-runtime", region_name="eu-west-1")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "calls").mkdir(exist_ok=True)
    raw_count = 0
    adjudicated_records: list[dict[str, Any]] = []
    for repeat in range(1, args.repeats + 1):
        for rule_id in sorted({str(row["rule_id"]) for row in records}):
            selected = [row for row in records if row["rule_id"] == rule_id]
            if args.sample_per_rule is not None:
                selected = selected[: args.sample_per_rule]
            if repeat == 1:
                adjudicated_records.extend(selected)
            for offset in range(0, len(selected), MAX_BATCH):
                batch = selected[offset : offset + MAX_BATCH]
                call = call_sol(
                    client,
                    rule_id,
                    batch,
                    rules,
                    model_id=args.model_id,
                    reasoning_effort=args.reasoning_effort,
                )
                call["repeat"] = repeat
                raw_count += 1
                (
                    out_dir / "calls" / f"{repeat:02d}-{raw_count:04d}-{rule_id}.json"
                ).write_text(
                    json.dumps(call, indent=2, ensure_ascii=False, default=str) + "\n",
                    encoding="utf-8",
                )
    if args.repeats > 1:
        consistency_report(out_dir, adjudicated_records)
    stats = write_reports(out_dir, run_dir, adjudicated_records)
    metadata = {
        "model_id": args.model_id,
        "reasoning_effort": args.reasoning_effort,
        "run_dir": str(run_dir),
        "confirm_count": len(adjudicated_records),
        "repeats": args.repeats,
        "calls": raw_count,
    }
    (out_dir / "run.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return metadata | {"rules": stats}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="call Sol and write adjudication reports")
    report_parser = sub.add_parser("report", help="regenerate reports from saved calls")
    consistency_parser = sub.add_parser(
        "consistency", help="regenerate repeated-call consistency"
    )
    for command in (run_parser, report_parser, consistency_parser):
        command.add_argument("--run-dir", type=Path, required=True)
        command.add_argument("--corpus-root", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--class", dest="class_name", choices=("human", "llm"))
    run_parser.add_argument("--model-id", default=MODEL_DEFAULT)
    run_parser.add_argument("--reasoning-effort", default=EFFORT_DEFAULT)
    run_parser.add_argument("--repeats", type=int, default=1)
    run_parser.add_argument("--sample-per-rule", type=int)
    run_parser.add_argument(
        "--rule-id", help="restrict a bounded smoke run to one rule"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        result = run(args)
    elif args.command == "consistency":
        confirms = load_confirms(args.run_dir.resolve(), args.class_name)
        records = _unit_records(
            args.run_dir.resolve(), confirms, args.corpus_root.resolve()
        )
        result = consistency_report(args.out.resolve(), records)
    else:
        confirms = load_confirms(args.run_dir.resolve(), args.class_name)
        records = _unit_records(
            args.run_dir.resolve(), confirms, args.corpus_root.resolve()
        )
        result = {
            "rules": write_reports(args.out.resolve(), args.run_dir.resolve(), records)
        }
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
