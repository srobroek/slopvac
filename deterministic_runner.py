#!/usr/bin/env python3
"""Run the fixed offline slopvac benchmark and emit machine metrics only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "autoresearch-fixture.json"
PACKAGE_SRC = ROOT / "packages" / "slopvac-lint" / "src"
CONTRACT = ROOT / "benchmark_contract.json"
sys.path.insert(0, str(PACKAGE_SRC))

from slopvac.model import RuleKind
from slopvac.rules import RuleLoadError, load_ruleset


def _raw_rule_metadata() -> dict[str, dict[str, Any]]:
    """Read taxonomy fields not yet represented by the shipped Rule model."""
    rules_dir = PACKAGE_SRC / "slopvac" / "rules"
    metadata: dict[str, dict[str, Any]] = {}
    for path in sorted(rules_dir.glob("*.y*ml")):
        try:
            documents = yaml.safe_load_all(path.read_text(encoding="utf-8"))
            for category in documents:
                if not isinstance(category, dict):
                    raise ValueError(f"{path}: category must be an object")
                category_id = category.get("id")
                rules = category.get("rules")
                if not isinstance(category_id, str) or not isinstance(rules, list):
                    raise ValueError(f"{path}: malformed category")
                for raw in rules:
                    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
                        raise ValueError(f"{path}: malformed rule")
                    qualified_id = f"{category_id}.{raw['id']}"
                    if qualified_id in metadata:
                        raise ValueError(f"duplicate rule id: {qualified_id}")
                    metadata[qualified_id] = raw
        except yaml.YAMLError as exc:
            raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    return metadata


def _taxonomy_metrics() -> dict[str, int | float]:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        ruleset = load_ruleset()
        raw = _raw_rule_metadata()
    except (OSError, TypeError, ValueError, RuleLoadError) as exc:
        raise RuntimeError(f"taxonomy registry is invalid: {exc}") from exc
    if not isinstance(contract, dict):
        raise RuntimeError("benchmark contract must be an object")
    dimensions = contract.get("dimensions")
    owners = contract.get("ownership")
    dims = contract.get("judgement_dims")
    required = contract.get("required_rule_fields")
    judgement_required = contract.get("judgement_contract_fields")
    if not all(isinstance(value, list) and value for value in (dimensions, owners, dims)):
        raise RuntimeError("benchmark contract enum lists are malformed")
    if not isinstance(required, list) or not isinstance(judgement_required, list):
        raise RuntimeError("benchmark contract required fields are malformed")
    registry = {rule.qualified_id: rule for rule in ruleset.rules}
    if set(raw) != set(registry):
        raise RuntimeError("raw registry and loaded registry disagree")
    total = len(registry)
    if not total:
        raise RuntimeError("taxonomy registry has an empty denominator")
    valid_dimensions = sum(
        isinstance(declaration.get("dimension"), str)
        and declaration["dimension"] in dimensions
        for declaration in raw.values()
    )
    valid_owners = sum(
        isinstance(declaration.get("ownership"), str)
        and declaration["ownership"] in owners
        and all(field in declaration for field in required)
        for declaration in raw.values()
    )
    deterministic_ids = {
        rule_id for rule_id in registry
        if raw[rule_id].get("ownership") == "deterministic"
    }
    seeded = [
        (rule_id, raw[rule_id]) for rule_id in registry
        if raw[rule_id].get("ownership") == "seeded_adjudication"
    ]
    if not seeded:
        raise RuntimeError("taxonomy registry has an empty seeded-adjudication denominator")
    valid_seeds = 0
    for rule_id, declaration in seeded:
        seeds = declaration.get("seed_rule_ids")
        if isinstance(seeds, list) and seeds and all(
            isinstance(seed, str) and seed in deterministic_ids and seed != rule_id
            for seed in seeds
        ):
            valid_seeds += 1
    judgement = [rule_id for rule_id, rule in registry.items() if rule.kind is RuleKind.JUDGEMENT]
    if not judgement:
        raise RuntimeError("taxonomy registry has an empty judgement denominator")
    contract_count = 0
    for rule_id in judgement:
        value = raw[rule_id].get("judgement_contract")
        if not isinstance(value, dict) or not all(field in value for field in judgement_required):
            continue
        if (
            isinstance(value["dims"], list) and value["dims"]
            and all(isinstance(item, str) and item in dims for item in value["dims"])
            and isinstance(value["evidence_arity"], int) and value["evidence_arity"] > 0
            and isinstance(value["rewrite_exempt"], bool)
            and isinstance(value["admission"], str) and value["admission"].strip()
            and isinstance(value["protects"], str) and value["protects"].strip()
            and isinstance(value["judgement_ceiling"], str)
            and value["judgement_ceiling"].strip()
        ):
            contract_count += 1
    return {
        "dimension_coverage": 100 * valid_dimensions / total,
        "ownership_coverage": 100 * valid_owners / total,
        "seed_validity": 100 * valid_seeds / len(seeded),
        "judgement_contract_coverage": 100 * contract_count / len(judgement),
        "structured_rule_count": contract_count,
    }


def fail(message: str) -> int:
    print(f"autoresearch: {message}", file=sys.stderr)
    return 1


def run_case(case: dict[str, Any], directory: Path) -> set[str]:
    case_id = str(case["id"])
    path = directory / f"{case_id}.md"
    path.write_text(case["text"], encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PACKAGE_SRC), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    result = subprocess.run(
        [
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
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    # --no-vale intentionally reports unchecked and exits 2. A valid JSON
    # report is still the production result; all other nonzero exits fail closed.
    if result.returncode not in (0, 2):
        raise RuntimeError(
            f"{case_id}: CLI exited {result.returncode}: {result.stderr.strip()}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{case_id}: invalid JSON output: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{case_id}: report must be an object")
    documents = payload.get("documents")
    if not isinstance(documents, list) or len(documents) != 1:
        raise RuntimeError(f"{case_id}: report must contain exactly one document")
    document = documents[0]
    if not isinstance(document, dict):
        raise RuntimeError(f"{case_id}: report document is malformed")
    findings = document.get("findings")
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
def main(argv: list[str] | None = None) -> int:
    if argv and argv in (["-h"], ["--help"]):
        print("usage: autoresearch.sh [--online ONLINE_ARGS...]\n\nRun the offline deterministic benchmark by default.")
        return 0
    if argv:
        return fail(f"offline benchmark does not accept arguments: {' '.join(argv)}")
    try:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        if not isinstance(fixture, dict) or fixture.get("schema_version") != 1:
            return fail("fixture is malformed or empty")
        cases = fixture.get("cases")
        if not isinstance(cases, list) or not cases:
            return fail("fixture is malformed or empty")
        ids: list[str] = []
        for case in cases:
            if not isinstance(case, dict):
                return fail("fixture contains a malformed case")
            case_id = case.get("id")
            if not isinstance(case_id, str) or not case_id:
                return fail("fixture case IDs are missing or duplicated")
            if not isinstance(case.get("text"), str):
                return fail(f"{case_id}: case text must be a string")
            expected = case.get("expected_rule_families")
            if not isinstance(expected, list) or not all(
                isinstance(rule_id, str) for rule_id in expected
            ):
                return fail(f"{case_id}: expected_rule_families must be a list of strings")
            if case.get("kind") not in ("bad", "control"):
                return fail(f"{case_id}: unknown case kind")
            ids.append(case_id)
        if len(set(ids)) != len(ids):
            return fail("fixture case IDs are missing or duplicated")
        with tempfile.TemporaryDirectory(prefix="slopvac-autoresearch-") as tmp:
            outcomes = {case["id"]: run_case(case, Path(tmp)) for case in cases}
        taxonomy = _taxonomy_metrics()
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        return fail(str(exc))

    tp = fp = fn = tn = unexpected = 0
    for case in cases:
        expected = set(case["expected_rule_families"])
        found = outcomes[case["id"]]
        if case["kind"] == "bad":
            if found & expected:
                tp += 1
            else:
                fn += 1
            unexpected += len(found - expected)
        elif found:
            fp += 1
        else:
            tn += 1

    case_count = len(cases)
    if tp + fn == 0 or fp + tn == 0:
        return fail("fixture must contain both bad and control cases")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    specificity = tn / (tn + fp)
    behavior_score = 100 * balanced_accuracy
    metric(
        "quality_score",
        min(
            behavior_score,
            taxonomy["dimension_coverage"],
            taxonomy["ownership_coverage"],
            taxonomy["seed_validity"],
            taxonomy["judgement_contract_coverage"],
        ),
    )
    metric("behavior_score", behavior_score)
    metric("TP", tp)
    metric("FP", fp)
    metric("FN", fn)
    metric("TN", tn)
    metric("precision", precision)
    metric("recall", recall)
    metric("balanced_accuracy", balanced_accuracy)
    metric("case_count", case_count)
    for name, value in taxonomy.items():
        metric(name, value)
    metric("unexpected_findings", unexpected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
