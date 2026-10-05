"""Blind-set rows (label_origin "blind-unlabelled") carry placeholder labels and are never scored.

Run: uv run --no-project --with numpy --with psutil --with pytest pytest tests/test_metrics_unlabelled.py
"""

import random
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parents[1] / "src/judge_sagemaker/pilot"
sys.path.insert(0, str(PILOT))

import metrics  # noqa: E402

CHOICES = metrics.CHOICE_ORDER
# The label_origin judge-corpus blind items carry (judge_corpus/blind.py).
UNLABELLED = "blind-unlabelled"


def _row(item_id, kind, split, label, origin, rng, order="forward"):
    if kind == "noul":
        answer = {"type": "noul", "noul": round(rng.random(), 4)}
    else:
        weights = [rng.random() + 0.01 for _ in CHOICES]
        probs = {k: w / sum(weights) for k, w in zip(CHOICES, weights)}
        answer = {
            "type": "choice",
            "choice": max(probs, key=probs.get),
            "probabilities": probs,
        }
    return {
        "id": item_id,
        "kind": kind,
        "order": order,
        "status": 200,
        "answer": answer,
        "error": None,
        "split": split,
        "label": label,
        "label_origin": origin,
        "state_rule": f"rule-{rng.randrange(6)}",
        "source": "human",
        "role": "semantic-detection" if kind == "noul" else "finding-confirmation",
        "rule_held_out": False,
        "granularity": "sentence",
        "provenance": "human",
    }


def _records(kind, split, n, origin, seed, start=0):
    rng = random.Random(seed)
    rows = []
    for i in range(start, start + n):
        label = rng.random() < 0.5 if kind == "noul" else rng.choice(CHOICES)
        rows.append(_row(f"{split}-{i}", kind, split, label, origin, rng))
        if kind == "choice":
            rows.append(
                _row(f"{split}-{i}", kind, split, label, origin, rng, "reversed")
            )
    return rows


def _blind(kind, n, seed):
    """Placeholder labels the eval needs: choice no-defect, noul false."""
    placeholder = False if kind == "noul" else "no-defect"
    rows = _records(kind, "test", n, UNLABELLED, seed, start=10_000)
    for row in rows:
        row["label"] = placeholder
    return rows


def test_only_unlabelled_test_rows_leave_test_metrics_absent():
    for kind in ("noul", "choice"):
        records = _records(kind, "calibration", 60, "human-adjudication", 1)
        records += _blind(kind, 40, 2)
        res = metrics.score_kind(records, kind)
        assert res["test_unscored_unlabelled"] == 40
        for key in (
            "test_raw",
            "test_cal",
            "test_raw_ci95",
            "test_cal_ci95",
            "test_slices",
            "test_accuracy_by_source",
            *metrics.TEST_KEYS[kind],
        ):
            assert res[key] is None, (kind, key)
        assert res["_test_ids"] == []
        # Calibration is still scored, so the temperature for blind predictions is real.
        assert res["calibration_raw"]["n"] == 60
        assert res["temperature_fit_on_calibration"] > 0


def test_unlabelled_rows_never_change_labelled_test_scores():
    for kind in ("noul", "choice"):
        labelled = _records(kind, "calibration", 60, "human-adjudication", 3)
        labelled += _records(kind, "test", 50, "construction", 4)
        alone = metrics.score_kind(labelled, kind)
        mixed = metrics.score_kind(labelled + _blind(kind, 80, 5), kind)
        assert mixed["test_unscored_unlabelled"] == 80
        assert "test_unscored_unlabelled" not in alone
        assert mixed["_test_ids"] == alone["_test_ids"]
        for key in ("test_raw", "test_cal", "test_slices", *metrics.TEST_KEYS[kind]):
            assert mixed[key] == alone[key], (kind, key)
