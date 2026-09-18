"""Normalize judgement evaluation records without inventing missing measurements."""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TARGETS = {
    "local-corpus-run.json",
    "sibling-full-run.json",
    "sibling-full-run-adjudication.json",
    "heldout-baseline.json",
    "heldout-baseline-adjudication.json",
    "heldout-v2.json",
    "heldout-v2-adjudication.json",
}
_LABEL_MAP = {"TP": "TP", "FP": "FP", "FP-PRESERVE-MISS": "FP", "B": "B", "BORDERLINE": "B"}


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _counts(record: Any, key: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for value in _walk(record):
        if not isinstance(value, dict) or not isinstance(value.get(key), dict):
            continue
        for label, count in value[key].items():
            if isinstance(count, (int, float)) and not isinstance(count, bool):
                result[str(label).upper()] += count
    return result


def _canonical_label(label: Any) -> str | None:
    if not isinstance(label, str):
        return None
    return _LABEL_MAP.get(label.upper().replace("_", "-"))


def _adjudication_counts(record: Any) -> tuple[Counter[str], str, set[str]]:
    rows = [
        value for value in _walk(record)
        if isinstance(value, dict)
        and "rule" in value
        and isinstance(value.get("verdict", value.get("adjudication")), str)
    ]
    unknown: set[str] = set()
    if rows:
        result: Counter[str] = Counter()
        for value in rows:
            raw_label = value.get("verdict", value.get("adjudication"))
            label = _canonical_label(raw_label)
            if label is None:
                unknown.add(str(raw_label).upper())
            else:
                result[label] += 1
        return result, "per-confirm adjudication rows", unknown

    result = Counter()
    for value in _walk(record):
        if not isinstance(value, dict) or not isinstance(value.get("adjudication"), dict):
            continue
        for raw_label, count in value["adjudication"].items():
            if not isinstance(count, (int, float)) or isinstance(count, bool):
                continue
            label = _canonical_label(raw_label)
            if label is None:
                unknown.add(str(raw_label).upper())
            else:
                result[label] += count
    return result, "summary adjudication counts (no per-confirm rows available)", unknown


def _rule_table(record: Any) -> list[dict[str, Any]]:
    rows: dict[str, Counter[str]] = defaultdict(Counter)
    for value in _walk(record):
        if isinstance(value, dict) and isinstance(value.get("adjudication_by_rule"), dict):
            for rule, counts in value["adjudication_by_rule"].items():
                if isinstance(counts, dict):
                    for raw_label, count in counts.items():
                        if isinstance(count, (int, float)) and not isinstance(count, bool):
                            label = _canonical_label(raw_label)
                            if label is not None:
                                rows[str(rule)][label] += count
        if isinstance(value, dict):
            rule = value.get("rule") or value.get("rule_id")
            label = _canonical_label(value.get("verdict", value.get("adjudication")))
            if rule is not None and label is not None:
                rows[str(rule)][label] += 1
    table = []
    for rule in sorted(rows):
        counts = rows[rule]
        tp = counts.get("TP", 0)
        fp = counts.get("FP", 0)
        borderline = counts.get("B", 0)
        den = tp + fp + borderline
        table.append({
            "rule_id": rule,
            "tp": tp,
            "fp": fp,
            "borderline": borderline,
            "strict_precision": tp / den if den else None,
            "lenient_precision": (tp + borderline) / den if den else None,
        })
    return table


def _first_number(record: Any, *keys: str) -> int | float | None:
    for value in _walk(record):
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                    return candidate
    return None


def _host_confirms(record: Any) -> int | float | None:
    values = [
        value["host_confirms"] for value in _walk(record)
        if isinstance(value, dict)
        and isinstance(value.get("host_confirms"), (int, float))
        and not isinstance(value.get("host_confirms"), bool)
    ]
    return sum(values) if values else None


def _model_confirms_before_gate(record: Any) -> int | float | None:
    for value in _walk(record):
        if isinstance(value, dict) and isinstance(value.get("model_raw_verdicts_before_host_gate"), dict):
            candidate = value["model_raw_verdicts_before_host_gate"].get("confirm")
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return candidate
    return None


def normalize(path: Path) -> Path:
    raw = json.loads(path.read_text(encoding="utf-8"))
    outcomes = _counts(raw, "outcomes")
    outcomes.update({k: v for k, v in _counts(raw, "host_outcomes").items()})
    adjudication, adjudication_derivation, unknown_labels = _adjudication_counts(raw)
    tp = adjudication.get("TP", 0)
    fp = adjudication.get("FP", 0)
    borderline = adjudication.get("B", 0)
    precision_den = tp + fp + borderline
    distinct_ids = {str(value["unit_id"]) for value in _walk(raw) if isinstance(value, dict) and "unit_id" in value}
    response_rows = sum(1 for value in _walk(raw) if isinstance(value, dict) and "verdict" in value and "unit_id" in value)
    all_units = len(distinct_ids) or None
    abstains = outcomes.get("ABSTAIN")
    evidence_pass = _host_confirms(raw)
    model_confirms = _model_confirms_before_gate(raw)
    not_derivable: list[str] = []
    if all_units is None:
        not_derivable.append("denominators.all_units.distinct_unit_ids")
    if abstains is None or all_units is None:
        not_derivable.append("metrics.abstention_rate")
    if evidence_pass is None or model_confirms is None or not model_confirms:
        not_derivable.append("metrics.evidence_validity")
    if unknown_labels:
        not_derivable.append("raw_adjudication.unknown_labels")
    normalized = {
        "schema_version": 1,
        "source": path.name,
        "derivation": {
            "adjudication": adjudication_derivation,
            "evidence_validity": "host_confirms_after_gate / model_confirms_before_gate",
        },
        "raw_record": copy.deepcopy(raw),
        "raw_outcomes": dict(sorted(outcomes.items())),
        "raw_adjudication": dict(sorted(adjudication.items())),
        "metrics": {
            "strict_precision": tp / precision_den if precision_den else None,
            "lenient_precision": (tp + borderline) / precision_den if precision_den else None,
            "abstention_rate": abstains / all_units if abstains is not None and all_units else None,
            "evidence_validity": evidence_pass / model_confirms if evidence_pass is not None and model_confirms else None,
        },
        "denominators": {
            "all_units": {"value": all_units, "definition": "distinct unit_ids; failed/truncated/not-run are counted as not-run"},
            "response_rows": {"value": response_rows or None, "definition": "response rows, not units; duplicate rows are not additional units"},
            "precision": {"value": precision_den or None, "definition": "TP + FP + borderline; strict treats borderline as FP, lenient treats borderline as TP"},
            "abstention": {"value": all_units, "definition": "ABSTAIN / all distinct units"},
            "evidence_validity": {"value": model_confirms, "definition": "model confirms before the host evidence gate; numerator sums host confirms after the gate"},
            "failed": _first_number(raw, "failed", "calls_failed"),
            "truncated": _first_number(raw, "truncated"),
            "not_run": _first_number(raw, "not_run"),
        },
        "per_rule": _rule_table(raw),
        "not_derivable": sorted(set(not_derivable)),
    }
    if unknown_labels:
        normalized["unknown_adjudication_labels"] = sorted(unknown_labels)
    target = path.with_name(path.stem + ".normalized.json")
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    if args.paths:
        paths = []
        for path in args.paths:
            paths.extend(
                sorted(path.glob("*.json"), key=lambda item: item.name)
                if path.is_dir()
                else [path]
            )
        paths = [item for item in paths if not item.name.endswith(".normalized.json")]
    else:
        paths = [Path(__file__).parent.parent / "evaluation" / name for name in sorted(TARGETS)]
    for path in paths:
        print(normalize(path))


if __name__ == "__main__":
    main()
