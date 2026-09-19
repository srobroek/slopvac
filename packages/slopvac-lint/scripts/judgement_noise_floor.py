#!/usr/bin/env python3
"""Prepare, measure, and decide three-repeat judgement noise floors."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from slopvac.judgement.driver import _response_payload
from slopvac.judgement.eval.runner import validate_result_set
from slopvac.judgement.schema import validate_model_output

THRESHOLD = 0.10
DEFAULT_MIN_UNITS = 30
REPEATS = (1, 2, 3)
FAILURE_CLASSES = (
    "missing_response",
    "provider_error",
    "parse_error",
    "schema_invalid",
    "unknown_unit",
)


def _fingerprint(row: dict[str, Any], response: dict[str, Any] | None) -> str:
    """Hash prompt and required model/inference/schema metadata."""
    response = response or {}
    missing = [
        key
        for key in ("model_id", "inference_config")
        if key not in row and key not in response
    ]
    if missing:
        raise ValueError(f"missing required fingerprint fields: {', '.join(missing)}")
    payload = {
        key: row[key] if key in row else response[key]
        for key in ("prompt", "response_schema", "inference_config", "model_id")
        if key in row or key in response
    }
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def registered_subsample(prompts: Path, registration: Path) -> dict[str, Any]:
    call_ids = {str(row["call_id"]) for row in read_jsonl(prompts) if "call_id" in row}
    selected = sorted(
        call_id
        for call_id in call_ids
        if int.from_bytes(hashlib.sha256(call_id.encode()).digest(), "big") % 5 == 0
    )
    result = {
        "call_ids": selected,
        "rule": "sha256(call_id) interpreted as big-endian integer modulo 5 == 0",
        "denominator": 5,
        "selected_remainder": 0,
        "source": str(prompts),
        "prompt_call_count": len(call_ids),
        "count": len(selected),
        "registered_at_runtime": True,
        "preregistration_deviation": "No registered subsample was present; selected at prepare time.",
    }
    registration.parent.mkdir(parents=True, exist_ok=True)
    registration.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def prepare(args: argparse.Namespace) -> None:
    prompts = read_jsonl(args.prompts)
    registration = (
        json.loads(args.subsample.read_text(encoding="utf-8"))
        if args.subsample.exists()
        else registered_subsample(args.prompts, args.subsample)
    )
    selected = set(registration["call_ids"])
    source = [row for row in prompts if str(row.get("call_id")) in selected]
    missing = selected - {str(row.get("call_id")) for row in source}
    if missing:
        raise ValueError(f"subsample call_ids absent from prompts: {sorted(missing)[:3]}")
    repeated: list[dict[str, Any]] = []
    for row in source:
        original = str(row["call_id"])
        prompt_bytes = json.dumps(
            row["prompt"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        for repeat in REPEATS:
            copy = dict(row)
            copy.update(
                {
                    "call_id": f"{original}#r{repeat}",
                    "repeat_of": original,
                    "repeat_index": repeat,
                    "prompt_bytes_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
                    "model_id": args.model_id,
                    "inference_config": {"maxTokens": args.max_tokens},
                }
            )
            repeated.append(copy)
    write_jsonl(args.out, repeated)
    print(
        json.dumps(
            {
                "selected": len(source),
                "repeated": len(repeated),
                "subsample": str(args.subsample),
            }
        )
    )


def _classify_response(
    response: dict[str, Any] | None, expected: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, str]]:
    expected_ids = {str(row["unit_id"]) for row in expected}
    if not response:
        return {}, {unit: "missing_response" for unit in expected_ids}
    if response.get("error") is not None or response.get("error_type") is not None:
        return {}, {unit: "provider_error" for unit in expected_ids}
    if "response" not in response:
        return {}, {unit: "missing_response" for unit in expected_ids}
    try:
        payload = _response_payload(response["response"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}, {unit: "parse_error" for unit in expected_ids}
    rows = (
        payload.get("results")
        if isinstance(payload, dict) and "results" in payload
        else ([payload] if len(expected) == 1 else None)
    )
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return {}, {unit: "parse_error" for unit in expected_ids}
    returned_ids = {str(row.get("unit_id")) for row in rows}
    unknown = returned_ids - expected_ids
    if unknown:
        return {}, {unit: "unknown_unit" for unit in expected_ids}
    if validate_result_set(expected, rows) is not None:
        return {}, {unit: "schema_invalid" for unit in expected_ids}
    if any(validate_model_output(row) for row in rows):
        return {}, {unit: "schema_invalid" for unit in expected_ids}
    verdicts = {
        str(row["unit_id"]): str(row.get("verdict", "abstain")).upper()
        if str(row.get("verdict", "abstain")).upper() in {"CONFIRM", "REJECT"}
        else "ABSTAIN"
        for row in rows
    }
    return verdicts, {unit: "" for unit in expected_ids if unit not in verdicts}


def flip_rate(values: list[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    return (len(values) - max(counts.values())) / len(values)


def analyse(args: argparse.Namespace) -> None:
    prompts = read_jsonl(args.prompts)
    sidecar = (
        json.loads(args.run_config.read_text(encoding="utf-8"))
        if args.run_config
        else None
    )
    responses = {str(row.get("call_id")): row for row in read_jsonl(args.responses)}
    fingerprints: dict[str, str] = {}
    config_sources: set[str] = set()
    by_unit: dict[str, dict[str, Any]] = {}
    failure_counts: Counter[str] = Counter()
    for row in prompts:
        if sidecar:
            row.setdefault("model_id", sidecar["model_id"])
            row.setdefault("inference_config", sidecar["inference_config"])
            config_sources.add(str(sidecar.get("source", args.run_config)))
        original = str(row.get("repeat_of", row["call_id"]))
        response = responses.get(str(row["call_id"]))
        fingerprint = _fingerprint(row, response)
        previous = fingerprints.setdefault(original, fingerprint)
        if fingerprint != previous:
            raise ValueError(
                f"fingerprint mismatch across repeats for call {original}: {previous} != {fingerprint}"
            )
        expected = [
            {"unit_id": str(unit_id), "kind": row.get("kind")}
            for unit_id in row.get("unit_ids", [])
        ]
        verdicts, statuses = _classify_response(response, expected)
        for _unit_id, status in statuses.items():
            if status:
                failure_counts[status] += 1
        for unit_id, rule_id in zip(
            row.get("unit_ids", []), row.get("rule_ids", []), strict=False
        ):
            unit_key = str(unit_id)
            item = by_unit.setdefault(
                unit_key,
                {
                    "unit_id": unit_key,
                    "rule_id": str(rule_id),
                    "repeats": {},
                    "failures": {},
                },
            )
            repeat = int(row.get("repeat_index", 1))
            if unit_key in verdicts:
                item["repeats"][repeat] = verdicts[unit_key]
            elif statuses.get(unit_key):
                item["failures"][repeat] = statuses[unit_key]
            item["call_id"] = original
    units: list[dict[str, Any]] = []
    by_rule: dict[str, list[float]] = defaultdict(list)
    rule_failures: dict[str, Counter[str]] = defaultdict(Counter)
    for item in by_unit.values():
        valid = [
            item["repeats"][repeat] for repeat in REPEATS if repeat in item["repeats"]
        ]
        complete = len(valid) == len(REPEATS)
        unit = {
            "unit_id": item["unit_id"],
            "rule_id": item["rule_id"],
            "verdicts": [item["repeats"].get(repeat) for repeat in REPEATS],
            "valid_repeat_count": len(valid),
            "complete": complete,
            "failure_classes": dict(Counter(item["failures"].values())),
        }
        if complete:
            rate = flip_rate(valid)
            unit["flip_rate"] = rate
            by_rule[item["rule_id"]].append(rate)
        else:
            for failure in item["failures"].values():
                rule_failures[item["rule_id"]][failure] += 1
        units.append(unit)
    rules = [
        {
            "rule_id": rule_id,
            "complete_units": len(rates),
            "flip_rate": sum(rates) / len(rates),
            "failure_classes": dict(rule_failures[rule_id]),
        }
        for rule_id, rates in sorted(by_rule.items())
    ]
    for rule_id in sorted(rule_failures):
        if rule_id not in {rule["rule_id"] for rule in rules}:
            rules.append(
                {
                    "rule_id": rule_id,
                    "complete_units": 0,
                    "flip_rate": 0.0,
                    "failure_classes": dict(rule_failures[rule_id]),
                }
            )
    complete_units = sum(unit["complete"] for unit in units)
    overall = (
        sum(unit["flip_rate"] for unit in units if unit["complete"]) / complete_units
        if complete_units
        else 0.0
    )
    payload = {
        "repeat_count": 3,
        "unit_count": len(units),
        "complete_units": complete_units,
        "incomplete_units": len(units) - complete_units,
        "overall_flip_rate": overall,
        "config_provenance": sorted(config_sources),
        "failure_classes": dict(failure_counts),
        "fingerprints": fingerprints,
        "rules": rules,
        "units": units,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "noise-floor.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Noise floor",
        "",
        "- Repeats: 3",
        f"- Complete units: {complete_units}",
        f"- Incomplete units: {len(units) - complete_units}",
        f"- Overall flip rate: {overall:.2%}",
        f"- Config provenance: {', '.join(sorted(config_sources)) or 'prompt rows'}",
        "",
        "## Failure classes",
        "",
        "| Class | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {key} | {failure_counts.get(key, 0)} |" for key in FAILURE_CLASSES)
    lines += [
        "",
        "## Per rule",
        "",
        "| Rule | Complete units | Flip rate | Failure classes |",
        "| --- | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| {rule['rule_id']} | {rule['complete_units']} | {rule['flip_rate']:.2%} | {json.dumps(rule['failure_classes'], sort_keys=True)} |"
        for rule in rules
    )
    (args.out_dir / "noise-floor.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def decide(args: argparse.Namespace) -> None:
    report = json.loads(args.noise_floor.read_text(encoding="utf-8"))
    rules = []
    for rule in report["rules"]:
        measured = rule["flip_rate"] > args.threshold
        enough = rule["complete_units"] >= args.min_units
        decision = "majority-of-3" if measured and enough else "single-call"
        basis = (
            "measured"
            if measured and enough
            else "insufficient-units"
            if measured
            else "measured"
        )
        rules.append({**rule, "decision": decision, "decision_basis": basis})
    decision = (
        "majority-of-3"
        if report["overall_flip_rate"] > args.threshold
        and report["complete_units"] >= args.min_units
        else "single-call"
    )
    payload = {
        "decision": decision,
        "decision_basis": "measured"
        if decision == "majority-of-3"
        else "insufficient-units"
        if report["overall_flip_rate"] > args.threshold
        else "measured",
        "applies_to": "CONFIRM",
        "threshold": args.threshold,
        "min_units": args.min_units,
        "rules": rules,
    }
    out = args.out or args.noise_floor.with_name("variance-policy.json")
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = out.with_suffix(".md")
    lines = [
        "# Variance policy",
        "",
        "- Applies to: CONFIRM",
        f"- Threshold: > {args.threshold:.0%}",
        f"- Minimum complete units: {args.min_units}",
        f"- Overall decision: {decision} ({payload['decision_basis']})",
        "",
        "| Rule | Complete units | Flip rate | Decision | Basis |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    lines.extend(
        f"| {r['rule_id']} | {r['complete_units']} | {r['flip_rate']:.2%} | {r['decision']} | {r['decision_basis']} |"
        for r in rules
    )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--prompts", type=Path, required=True)
    p.add_argument("--subsample", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model-id", required=True)
    p.add_argument("--max-tokens", type=int, required=True)
    p.set_defaults(func=prepare)
    a = sub.add_parser("analyse")
    a.add_argument("--prompts", type=Path, required=True)
    a.add_argument("--responses", type=Path, required=True)
    a.add_argument("--out-dir", type=Path, required=True)
    a.add_argument("--run-config", type=Path)
    a.set_defaults(func=analyse)
    d = sub.add_parser("decide")
    d.add_argument("--noise-floor", type=Path, required=True)
    d.add_argument("--threshold", type=float, default=THRESHOLD)
    d.add_argument("--min-units", type=int, default=DEFAULT_MIN_UNITS)
    d.add_argument("--out", type=Path)
    d.set_defaults(func=decide)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
