"""Decision thresholds for yes/no (noul) predictions, global and per rule.

The model's P(defect) is compared with a threshold. 0.5 is the default; a
threshold fit on the calibration split can trade recall between classes, and
rules differ in how their scores are distributed. For each arm this module fits:

- a global threshold that maximises balanced accuracy on calibration, and
- a per-rule threshold for every rule with at least MIN_PER_CLASS calibration
  items in each class (other rules fall back to the global threshold),

then scores the test split at 0.5, at the global threshold, and at the per-rule
thresholds. Thresholds are fit on calibration only and never on test.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

MIN_PER_CLASS = 5


def _rows(predictions: Path) -> list[dict]:
    out = []
    for line in predictions.read_text().splitlines():
        r = json.loads(line)
        if (
            r.get("kind") != "noul"
            or r.get("error")
            or not isinstance(r.get("answer"), dict)
        ):
            continue
        p = r["answer"].get("noul")
        if p is None or not isinstance(r.get("label"), bool):
            continue
        out.append(
            {
                "split": r["split"],
                "rule": r.get("asked_rule"),
                "p": float(p),
                "y": r["label"],
            }
        )
    return out


def _balanced_accuracy(rows: list[dict], threshold_for) -> float | None:
    pos = [r for r in rows if r["y"]]
    neg = [r for r in rows if not r["y"]]
    if not pos or not neg:
        return None
    tpr = sum(r["p"] >= threshold_for(r) for r in pos) / len(pos)
    tnr = sum(r["p"] < threshold_for(r) for r in neg) / len(neg)
    return (tpr + tnr) / 2


def _fit(rows: list[dict]) -> float:
    candidates = sorted({0.5, *(r["p"] for r in rows)})
    best, best_score = 0.5, -1.0
    for t in candidates:
        score = _balanced_accuracy(rows, lambda _r, t=t: t)
        if score is not None and score > best_score:
            best, best_score = t, score
    return best


def analyse(predictions: Path) -> dict:
    rows = _rows(predictions)
    cal = [r for r in rows if r["split"] == "calibration"]
    test = [r for r in rows if r["split"] == "test"]
    global_t = _fit(cal) if cal else 0.5
    by_rule = defaultdict(list)
    for r in cal:
        by_rule[r["rule"]].append(r)
    per_rule = {
        rule: _fit(items)
        for rule, items in by_rule.items()
        if sum(i["y"] for i in items) >= MIN_PER_CLASS
        and sum(not i["y"] for i in items) >= MIN_PER_CLASS
    }
    return {
        "calibration_n": len(cal),
        "test_n": len(test),
        "global_threshold": global_t,
        "rules_with_own_threshold": len(per_rule),
        "min_per_class": MIN_PER_CLASS,
        "test_balanced_accuracy": {
            "at_0.5": _balanced_accuracy(test, lambda _r: 0.5),
            "at_global": _balanced_accuracy(test, lambda _r: global_t),
            "at_per_rule": _balanced_accuracy(
                test, lambda r: per_rule.get(r["rule"], global_t)
            ),
        },
    }
