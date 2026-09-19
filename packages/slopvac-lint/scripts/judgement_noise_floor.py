#!/usr/bin/env python3
"""Prepare and analyse three-repeat judgement noise-floor runs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from slopvac.judgement.driver import _response_payload
from slopvac.judgement.eval.runner import validate_result_set
from slopvac.judgement.schema import validate_model_output

THRESHOLD = 0.10
REPEATS = (1, 2, 3)


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
    if args.subsample.exists():
        registration = json.loads(args.subsample.read_text(encoding="utf-8"))
    else:
        registration = registered_subsample(args.prompts, args.subsample)
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
            copy["call_id"] = f"{original}#r{repeat}"
            copy["repeat_of"] = original
            copy["repeat_index"] = repeat
            copy["prompt_bytes_sha256"] = hashlib.sha256(prompt_bytes).hexdigest()
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


def valid_verdicts(
    response: dict[str, Any] | None, expected: list[dict[str, Any]]
) -> dict[str, str]:
    """Parse one response exactly like finish and return only valid result rows."""
    if not response or "response" not in response:
        return {}
    try:
        payload = _response_payload(response["response"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    rows = (
        payload.get("results")
        if isinstance(payload, dict) and "results" in payload
        else ([payload] if len(expected) == 1 else None)
    )
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return {}
    if validate_result_set(expected, rows) is not None:
        return {}
    if any(validate_model_output(row) for row in rows):
        return {}
    return {
        str(row["unit_id"]): (
            str(row.get("verdict", "abstain")).upper()
            if str(row.get("verdict", "abstain")).upper() in {"CONFIRM", "REJECT"}
            else "ABSTAIN"
        )
        for row in rows
    }


def flip_rate(values: list[str]) -> float:
    """Fraction of valid repeats that disagree with the modal verdict."""
    if not values:
        return 0.0
    counts = {value: values.count(value) for value in set(values)}
    return (len(values) - max(counts.values())) / len(values)


def analyse(args: argparse.Namespace) -> None:
    prompts = read_jsonl(args.prompts)
    responses = {str(row.get("call_id")): row for row in read_jsonl(args.responses)}
    by_unit: dict[str, dict[str, Any]] = {}
    for row in prompts:
        original = str(row.get("repeat_of", row["call_id"]))
        for unit_id, rule_id in zip(
            row.get("unit_ids", []), row.get("rule_ids", []), strict=False
        ):
            unit_key = str(unit_id)
            item = by_unit.setdefault(
                unit_key, {"unit_id": unit_key, "rule_id": str(rule_id), "repeats": {}}
            )
            repeat = int(row.get("repeat_index", 1))
            verdict = valid_verdicts(
                responses.get(str(row["call_id"])),
                [{"unit_id": unit_key, "kind": row.get("kind")}],
            ).get(unit_key)
            if verdict is not None:
                item["repeats"][repeat] = verdict
            item["call_id"] = original

    units: list[dict[str, Any]] = []
    by_rule: dict[str, list[float]] = defaultdict(list)
    for item in by_unit.values():
        valid = [
            item["repeats"][repeat] for repeat in REPEATS if repeat in item["repeats"]
        ]
        complete = len(valid) == len(REPEATS)
        unit: dict[str, Any] = {
            "unit_id": item["unit_id"],
            "rule_id": item["rule_id"],
            "verdicts": [item["repeats"].get(repeat) for repeat in REPEATS],
            "valid_repeat_count": len(valid),
            "complete": complete,
        }
        if complete:
            rate = flip_rate(valid)
            unit["flip_rate"] = rate
            by_rule[item["rule_id"]].append(rate)
        units.append(unit)

    rules = []
    for rule_id in sorted(by_rule):
        rates = by_rule[rule_id]
        rate = sum(rates) / len(rates)
        rules.append(
            {
                "rule_id": rule_id,
                "unit_count": len(rates),
                "flip_rate": rate,
                "decision": "majority-of-3" if rate > THRESHOLD else "single-call",
            }
        )
    complete_units = sum(unit["complete"] for unit in units)
    incomplete_units = len(units) - complete_units
    overall = (
        sum(unit["flip_rate"] for unit in units if unit["complete"]) / complete_units
        if complete_units
        else 0.0
    )
    payload = {
        "threshold": THRESHOLD,
        "repeat_count": 3,
        "unit_count": len(units),
        "complete_units": complete_units,
        "incomplete_units": incomplete_units,
        "overall_flip_rate": overall,
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
        f"- Threshold: > {THRESHOLD:.0%} flip rate => majority-of-3; exactly {THRESHOLD:.0%} remains single-call",
        f"- Complete units: {complete_units}",
        f"- Incomplete units: {incomplete_units}",
        f"- Overall flip rate: {overall:.2%}",
        "",
        "## Per rule",
        "",
        "| Rule | Complete units | Flip rate | Decision |",
        "| --- | ---: | ---: | --- |",
    ]
    lines.extend(
        f"| {rule['rule_id']} | {rule['unit_count']} | {rule['flip_rate']:.2%} | {rule['decision']} |"
        for rule in rules
    )
    (args.out_dir / "noise-floor.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "complete_units": complete_units,
                "incomplete_units": incomplete_units,
                "overall_flip_rate": overall,
                "rules": len(rules),
            }
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--prompts", type=Path, required=True)
    prepare_parser.add_argument("--responses", type=Path)
    prepare_parser.add_argument("--subsample", type=Path, required=True)
    prepare_parser.add_argument("--out", type=Path, required=True)
    prepare_parser.set_defaults(func=prepare)
    analyse_parser = sub.add_parser("analyse")
    analyse_parser.add_argument("--prompts", type=Path, required=True)
    analyse_parser.add_argument("--responses", type=Path, required=True)
    analyse_parser.add_argument("--out-dir", type=Path, required=True)
    analyse_parser.set_defaults(func=analyse)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
