"""Merge human labels from the adjudication sheets into the item splits.

Reads label sheets written by label_sheets.py (label-test.csv,
label-calibration.csv, label-disagreement.csv) and sets each labelled item's
`label` in items/{train,dev,calibration,test}.jsonl:

- One rater: that rater's label.
- Two raters who agree: the shared label.
- Two raters who disagree: no label; the item is recorded as a disagreement
  and keeps whatever label it had (none for test and calibration rows).

Every merged item gets `label_origin=human-adjudication`, `label_confidence=1.0`
and `human_labels` holding each rater's answer, so a human label replaces a
teacher-panel label. Labels are validated against the item's question: finding
confirmation takes real-defect | false-positive | insufficient-context, yes/no
questions take true | false (also yes | no), written as JSON booleans. An
invalid label stops the import and lists the offending rows; nothing is written.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from .common import read_jsonl, write_jsonl
from .items import SPLITS

CHOICE = {"real-defect", "false-positive", "insufficient-context"}
YES_NO = {"true": True, "yes": True, "false": False, "no": False}
RATERS = ("label_rater1", "label_rater2")


def _normalise(raw: str, kind: str):
    value = raw.strip().lower()
    if not value:
        return None
    if kind == "choice":
        if value not in CHOICE:
            raise ValueError(f"{raw!r} is not one of {sorted(CHOICE)}")
        return value
    if value not in YES_NO:
        raise ValueError(f"{raw!r} is not true or false")
    return YES_NO[value]


def _cohen_kappa(pairs: list[tuple]) -> float | None:
    if not pairs:
        return None
    labels = sorted({str(x) for p in pairs for x in p})
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    first = Counter(str(a) for a, _ in pairs)
    second = Counter(str(b) for _, b in pairs)
    expected = sum(first[k] * second[k] for k in labels) / (n * n)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


def import_labels(root: Path, sheets: list[Path]) -> dict:
    items = {s: list(read_jsonl(root / f"items/{s}.jsonl")) for s in SPLITS}
    by_id = {x["id"]: (s, x) for s, rows in items.items() for x in rows}
    decided, disagreements, errors = {}, [], []
    pairs: dict[str, list[tuple]] = {
        "finding-confirmation": [],
        "semantic-detection": [],
    }
    rows_read = 0
    for sheet in sheets:
        with sheet.open(newline="", encoding="utf-8") as fh:
            for line_no, row in enumerate(csv.DictReader(fh), start=2):
                rows_read += 1
                hit = by_id.get(row["item_id"])
                if hit is None:
                    errors.append(
                        f"{sheet.name}:{line_no}: unknown item_id {row['item_id']}"
                    )
                    continue
                _, item = hit
                kind = item["question"]["type"]
                answers = {}
                for rater in RATERS:
                    try:
                        answers[rater] = _normalise(row.get(rater, ""), kind)
                    except ValueError as exc:
                        errors.append(f"{sheet.name}:{line_no} {rater}: {exc}")
                given = {r: a for r, a in answers.items() if a is not None}
                if not given:
                    continue
                if len(given) == 2:
                    pairs[item["role"]].append(tuple(given.values()))
                    if len(set(given.values())) > 1:
                        disagreements.append(item["id"])
                        continue
                decided[item["id"]] = (
                    next(iter(given.values())),
                    given,
                    row.get("rater_notes", ""),
                )
    if errors:
        raise ValueError("labels not imported:\n- " + "\n- ".join(errors))
    changed = Counter()
    for item_id, (label, given, notes) in decided.items():
        split, item = by_id[item_id]
        item["label"] = label
        item["label_origin"] = "human-adjudication"
        item["label_confidence"] = 1.0
        item["human_labels"] = {**given, **({"notes": notes} if notes else {})}
        changed[(split, item["role"], str(label))] += 1
    for split in {by_id[i][0] for i in decided}:
        write_jsonl(root / f"items/{split}.jsonl", items[split])
    return {
        "rows_read": rows_read,
        "labelled_items": len(decided),
        "rater_disagreements": len(disagreements),
        "cohen_kappa_double_labelled": {
            role: _cohen_kappa(p) for role, p in pairs.items()
        },
        "double_labelled_items": {role: len(p) for role, p in pairs.items()},
        "by_split_role_label": {"|".join(k): v for k, v in sorted(changed.items())},
    }
