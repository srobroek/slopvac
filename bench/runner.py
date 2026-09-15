#!/usr/bin/env python3
"""Fixed online structured-prose benchmark; all configuration is repository data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
ALLOWED = {"confirm", "preserve", "reject", "abstain"}
AUTH = re.compile(r"\b(?:AI|artificial intelligence|model-generated|machine-generated|human-written|authorship|written by a (?:person|human|model))\b", re.I)


def metric(name: str, value: Any) -> None:
    if isinstance(value, float):
        print(f"METRIC {name}={value:.6f}")
    else:
        print(f"METRIC {name}={value}")


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: expected object")
    return value


def validate_assets() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifest = load(ROOT / "manifest.json")
    for name, expected in manifest.get("sha256", {}).items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"asset hash mismatch: {name}")
    rubric, shots, case_doc, arms_doc = load(RUBRIC), load(SHOTS), load(CASES), load(ARMS)
    if rubric.get("schema_version") != 1 or set(rubric.get("verdicts", [])) != ALLOWED:
        raise ValueError("rubric schema or verdict set is invalid")
    shots_list = shots.get("shots")
    cases = case_doc.get("cases")
    arms = arms_doc.get("arms")
    if shots.get("schema_version") != 1 or not isinstance(shots_list, list) or not isinstance(cases, list) or not isinstance(arms, list):
        raise ValueError("shots, cases, or arms are malformed")
    if len(cases) < 40:
        raise ValueError("at least 40 evaluation cases are required")
    ids = [x.get("id") for x in cases if isinstance(x, dict)]
    if len(ids) != len(cases) or len(set(ids)) != len(ids) or any(not isinstance(x.get("text"), str) or not x["text"] for x in cases):
        raise ValueError("case IDs/text must be present and unique")
    if sum(x.get("label") == "defect" for x in cases) < 20 or sum(x.get("label") == "control" for x in cases) < 20:
        raise ValueError("case balance requires at least 20 defects and 20 controls")
    families: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        if case.get("label") not in {"defect", "control"} or not case.get("family") or not case.get("category") or AUTH.search(str(case.get("text", ""))):
            raise ValueError(f"malformed case metadata: {case.get('id')}")
        families.setdefault(str(case["family"]), []).append(case)
    for shot in shots_list:
        if shot.get("verdict") not in ALLOWED or not isinstance(shot.get("quote"), str) or not shot["quote"] or shot["quote"] not in shot.get("text", "") or AUTH.search(json.dumps(shot, ensure_ascii=False)):
            raise ValueError(f"invalid shot: {shot.get('id')}")
    if any(sum(bool(c.get("holdout")) for c in group) != 1 for group in families.values()):
        raise ValueError("each near-neighbour family must have exactly one holdout")
    shot_ids = {x.get("id") for x in shots_list}
    if len(shot_ids) != len(shots_list) or shot_ids & set(ids):
        raise ValueError("shots and evaluation cases must be disjoint")
    if not all(isinstance(x.get("text"), str) and x["text"] for x in shots_list):
        raise ValueError("shots are malformed")
    if not arms or len({x.get("id") for x in arms}) != len(arms) or any(not x.get("model") for x in arms):
        raise ValueError("model arm manifest is malformed")
    return rubric, shots_list, cases, arms_doc


def render(rubric: dict[str, Any], shots: list[dict[str, Any]], cases: list[dict[str, Any]]) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    prompt = template.replace("{{RUBRIC_JSON}}", json.dumps(rubric, sort_keys=True, separators=(",", ":")))
    prompt = prompt.replace("{{SHOTS_JSON}}", json.dumps(shots, sort_keys=True, separators=(",", ":")))
    prompt = prompt.replace("{{CASES_JSON}}", json.dumps(cases, sort_keys=True, separators=(",", ":")))
    if "{{" in prompt or "}}" in prompt:
        raise ValueError("prompt template has unresolved placeholders")
    return prompt


def find_results(value: Any) -> tuple[list[Any] | None, dict[str, Any] | None]:
    if isinstance(value, dict):
        if isinstance(value.get("results"), list):
            return value["results"], value
        for child in value.values():
            found = find_results(child)
            if found[0] is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_results(child)
            if found[0] is not None:
                return found
    return None, None


def usage(value: Any) -> dict[str, float]:
    total: dict[str, float] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, (int, float)) and key.lower() in {"cost", "input_tokens", "output_tokens", "total_tokens", "latency_ms", "wall_ms"}:
                total[key.lower()] = total.get(key.lower(), 0.0) + float(child)
            elif isinstance(child, (dict, list)):
                for name, number in usage(child).items():
                    total[name] = total.get(name, 0.0) + number
    elif isinstance(value, list):
        for child in value:
            for name, number in usage(child).items():
                total[name] = total.get(name, 0.0) + number
    return total


def invoke(model: str, prompt: str, timeout: int = 300) -> tuple[list[dict[str, Any]] | None, dict[str, float], str]:
    if shutil.which("omp") is None:
        return None, {}, "missing omp"
    with tempfile.TemporaryDirectory(prefix="slopvac-online-") as session:
        command = ["omp", "-p", "--mode", "json", "--model", model, "--thinking", "low", "--temperature", "0", "--max-output-tokens", "2048", "--max-retries", "1", "--session-dir", session, "--no-extensions", "--no-skills", "--no-rules", "--no-tools", "--no-lsp", "--no-pty", "--no-title"]
        started = time.monotonic()
        try:
            proc = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=timeout, check=False, env=os.environ.copy())
        except (OSError, subprocess.TimeoutExpired) as exc:
            return None, {"latency_ms": (time.monotonic() - started) * 1000}, type(exc).__name__
        wall = (time.monotonic() - started) * 1000
        parsed: Any = None
        for line in proc.stdout.splitlines():
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
        if parsed is None:
            try:
                parsed = json.loads(proc.stdout)
            except json.JSONDecodeError:
                return None, {"latency_ms": wall}, "malformed json"
        results, _ = find_results(parsed)
        stats = {**usage(parsed), "latency_ms": wall}
        if results is None:
            return None, stats, "missing results"
        if any(not isinstance(x, dict) for x in results):
            return [x for x in results if isinstance(x, dict)], stats, "malformed result"
        if not any(key in stats for key in ("cost", "total_tokens", "input_tokens", "output_tokens")):
            return [x for x in results if isinstance(x, dict)], stats, "absent usage"
        return [x for x in results if isinstance(x, dict)], stats, ""


def score(cases: list[dict[str, Any]], results: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = results or []
    by_id = {x.get("case_id"): x for x in rows}
    counts = {"failures": max(0, len(rows) - len(cases)), "false_positives": 0, "false_confirms": 0, "misses": 0, "correct": 0, "abstains": 0}
    if [x.get("case_id") for x in rows] != [x["id"] for x in cases]:
        counts["failures"] += 1
    if len(by_id) != len(rows):
        counts["failures"] += 1
    for case in cases:
        row = by_id.get(case["id"])
        if row is None or not isinstance(row.get("verdict"), str) or row["verdict"] not in ALLOWED or not isinstance(row.get("quote"), str) or not row["quote"] or row["quote"] not in case["text"] or AUTH.search(json.dumps(row, ensure_ascii=False)):
            counts["failures"] += 1
            continue
        verdict, label = row["verdict"], case["label"]
        if verdict == "abstain":
            counts["abstains"] += 1
        expected = "reject" if label == "defect" else "preserve"
        if verdict == expected:
            counts["correct"] += 1
        elif label == "control":
            counts["false_positives"] += 1
            if verdict == "confirm":
                counts["false_confirms"] += 1
        else:
            counts["misses"] += 1
    n = len(cases)
    penalty = 100 * (3 * counts["failures"] + 4 * counts["false_positives"] + 5 * counts["false_confirms"] + 4 * counts["misses"]) / max(1, n * 6)
    counts["quality_score"] = max(0.0, min(100.0, 100.0 - penalty))
    counts["case_count"] = n
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="run one arm and one case without changing benchmark files")
    args = parser.parse_args(argv)
    try:
        rubric, shots, cases, arms_doc = validate_assets()
        prompt_hash = hashlib.sha256(TEMPLATE.read_bytes() + RUBRIC.read_bytes() + SHOTS.read_bytes() + CASES.read_bytes()).hexdigest()
        prompt = render(rubric, shots, cases)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"autoresearch: asset validation failure: {exc}", file=sys.stderr)
        metric("aggregate_quality_score", 0.0)
        metric("validation_failure", 1)
        return 1
    arms = arms_doc["arms"][:1] if args.smoke else arms_doc["arms"]
    eval_cases = cases[:1] if args.smoke else cases
    if args.smoke:
        prompt = render(rubric, shots, eval_cases)
    metric("case_count", len(eval_cases))
    metric("prompt_sha256", prompt_hash)
    scores: list[float] = []
    for arm in arms:
        repeats = 2 if not args.smoke else 1
        arm_scores: list[float] = []
        for repeat in range(repeats):
            results, stats, error = invoke(str(arm["model"]), prompt)
            result = score(eval_cases, results)
            if error:
                result["failures"] += 1
                result["quality_score"] = 0.0
            arm_scores.append(float(result["quality_score"]))
            scores.append(float(result["quality_score"]))
            prefix = f"arm_{arm['id']}_r{repeat + 1}"
            for key, value in result.items():
                metric(f"{prefix}_{key}", value)
            for key, value in stats.items():
                metric(f"{prefix}_{key}", value)
            if error:
                print(f"METRIC {prefix}_error={json.dumps(error)}")
        metric(f"arm_{arm['id']}_quality_score", min(arm_scores))
    metric("aggregate_quality_score", min(scores) if scores else 0.0)
    metric("aggregate_definition", "worst-survivor=min(per-arm repeated quality scores)")
    metric("exploratory_batched_screen", 1 if not args.smoke else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
