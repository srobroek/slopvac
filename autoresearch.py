#!/usr/bin/env python3
"""Run the fixed Phase 1 slopvac baseline and emit machine metrics only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "autoresearch-fixture.json"
PACKAGE_SRC = ROOT / "packages" / "slopvac-lint" / "src"


def fail(message: str) -> int:
    print(f"autoresearch: {message}", file=sys.stderr)
    return 1


def run_case(case: dict[str, object], directory: Path) -> set[str]:
    case_id = str(case["id"])
    path = directory / f"{case_id}.md"
    path.write_text(str(case["text"]), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PACKAGE_SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    command = [
        sys.executable,
        "-m",
        "slopvac.cli",
        "lint",
        str(path),
        "--no-vale",
        "--format",
        "json",
        "--profile",
        "normal",
        "--no-color",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    # --no-vale intentionally reports unchecked and exits 2. A valid JSON report
    # is still the production result; all other nonzero exits are execution errors.
    if result.returncode not in (0, 2):
        raise RuntimeError(f"{case_id}: CLI exited {result.returncode}: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{case_id}: invalid JSON output: {exc}") from exc
    documents = payload.get("documents")
    if not isinstance(documents, list) or len(documents) != 1:
        raise RuntimeError(f"{case_id}: report must contain exactly one document")
    findings = documents[0].get("findings")
    if not isinstance(findings, list):
        raise RuntimeError(f"{case_id}: report findings are missing or malformed")
    rule_ids: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("rule_id"), str):
            raise RuntimeError(f"{case_id}: malformed finding")
        rule_ids.add(finding["rule_id"])
    return rule_ids


def metric(name: str, value: int | float) -> None:
    if isinstance(value, float):
        print(f"METRIC {name}={value:.6f}")
    else:
        print(f"METRIC {name}={value}")


def main() -> int:
    try:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cases = fixture["cases"]
        if fixture.get("schema_version") != 1 or not isinstance(cases, list) or not cases:
            return fail("fixture is malformed or empty")
        ids = [case.get("id") for case in cases if isinstance(case, dict)]
        if len(ids) != len(cases) or len(set(ids)) != len(ids):
            return fail("fixture case IDs are missing or duplicated")
        with tempfile.TemporaryDirectory(prefix="slopvac-autoresearch-") as tmp:
            outcomes: dict[str, set[str]] = {
                str(case["id"]): run_case(case, Path(tmp)) for case in cases
            }
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        return fail(str(exc))

    tp = fp = fn = tn = unexpected = 0
    for case in cases:
        expected = set(case.get("expected_rule_families", []))
        found = outcomes[str(case["id"])]
        if not isinstance(expected, set):
            return fail(f"{case['id']}: expected_rule_families must be a list")
        if case.get("kind") == "bad":
            if found & expected:
                tp += 1
            else:
                fn += 1
            unexpected += len(found - expected)
        elif case.get("kind") == "control":
            if found:
                fp += 1
            else:
                tn += 1
        else:
            return fail(f"{case['id']}: unknown case kind")

    case_count = len(cases)
    if tp + fn == 0 or fp + tn == 0:
        return fail("fixture must contain both bad and control cases")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    specificity = tn / (tn + fp)
    balanced_accuracy = (recall + specificity) / 2
    quality_score = 100 * balanced_accuracy
    metric("quality_score", quality_score)
    metric("TP", tp)
    metric("FP", fp)
    metric("FN", fn)
    metric("TN", tn)
    metric("precision", precision)
    metric("recall", recall)
    metric("balanced_accuracy", balanced_accuracy)
    metric("case_count", case_count)
    metric("unexpected_findings", unexpected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
