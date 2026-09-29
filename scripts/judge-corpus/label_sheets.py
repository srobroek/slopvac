"""Human labelling sheets.

`label-test.csv` and `label-calibration.csv` hold the test and calibration
items that still have no label (the human-adjudication sample).
`label-disagreement.csv` holds DISAGREEMENT_ROWS train items from the teacher
panel where the teachers split or the Dawid-Skene posterior confidence is
below `--low-confidence`, stratified by rule.

All sheets go to items/adjudication/ (private; gitignored). One row per item:
what to judge, the allowed labels, the flagged text, and the span with the
flagged text marked [[like this]]. The `priority` column marks a
rule-stratified first pass (up to 120 rows per role) as 1 and the rest as 2.
The first rater fills in `label_rater1` with one of `allowed_labels`; rows with
`double_label` = 1 (a rule-stratified subset of the first pass, up to 40 per
role) also get `label_rater2` from a second rater. `rater_notes` is free text.
"""

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from judge_corpus.items import _state_of  # noqa: E402

OUT = ROOT / "items/adjudication"
FIRST_PASS = 120
DOUBLE_LABEL = 40
DISAGREEMENT_ROWS = 300
FIELDS = [
    "priority",
    "double_label",
    "item_id",
    "role",
    "granularity",
    "genre",
    "task",
    "rule",
    "rule_detail",
    "flagged_text",
    "allowed_labels",
    "heading",
    "text_with_flag",
    "context",
    "label_rater1",
    "label_rater2",
    "rater_notes",
]


def marked(text: str, start: int, end: int) -> str:
    if 0 <= start < end <= len(text):
        return text[:start] + "[[" + text[start:end] + "]]" + text[end:]
    return text


def describe(question: dict, state: dict) -> dict:
    if question["type"] == "choice":
        f = question["finding"]
        return {
            "task": "Is this lint finding valid?",
            "rule": f"{f['rule_name']} ({f['rule_id']})",
            "rule_detail": f["lint_message"],
            "flagged_text": f["matched_text"],
            "allowed_labels": "real-defect | false-positive | insufficient-context",
            "text_with_flag": marked(state["text"], f["start"], f["end"]),
        }
    examples = "; ".join(
        f"defect: {e['bad']} / fine: {e.get('good', '')}"
        for e in question.get("criteria", [])[:2]
    )
    return {
        "task": question["prompt"],
        "rule": question["rule_id"],
        "rule_detail": examples,
        "flagged_text": "",
        "allowed_labels": "true (defect present) | false",
        "text_with_flag": state["text"],
    }


def stratified(items: list[dict], per_role: int, salt: str) -> list[str]:
    """Up to `per_role` item ids per role, round-robin over rules in seeded
    order, so rare rules are represented."""
    rng = random.Random(f"17:{salt}")
    by_role = defaultdict(lambda: defaultdict(list))
    for item in items:
        by_role[item["role"]][item["rule_id"]].append(item["id"])
    chosen = []
    for role in sorted(by_role):
        rules = by_role[role]
        pools = {r: rng.sample(ids, len(ids)) for r, ids in sorted(rules.items())}
        picked = []
        while len(picked) < per_role and any(pools.values()):
            for r in sorted(pools):
                if pools[r] and len(picked) < per_role:
                    picked.append(pools[r].pop())
        chosen += picked
    return chosen


def write_sheet(name: str, items: list[dict]) -> tuple[int, int, int]:
    first = set(stratified(items, FIRST_PASS, "first-pass"))
    double = set(
        stratified([x for x in items if x["id"] in first], DOUBLE_LABEL, "double")
    )
    rows = []
    for item in items:
        state = _state_of(ROOT, item)
        rows.append(
            {
                "priority": 1 if item["id"] in first else 2,
                "double_label": 1 if item["id"] in double else 0,
                "item_id": item["id"],
                "role": item["role"],
                "granularity": item["granularity"],
                "genre": item["genre"],
                **describe(item["question"], state),
                "heading": state.get("heading", ""),
                "context": state.get("context", ""),
                "label_rater1": "",
                "label_rater2": "",
                "rater_notes": "",
            }
        )
    rows.sort(key=lambda r: (r["priority"], r["role"], r["rule"], r["item_id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"label-{name}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), len(first), len(double)


def read_split(split: str) -> list[dict]:
    with (ROOT / f"items/{split}.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def disagreement_items(low_confidence: float) -> tuple[list[dict], dict]:
    """Panel-labelled train items where the valid votes split or the
    posterior is below `low_confidence`, DISAGREEMENT_ROWS of them, split
    evenly by role and round-robin over rules within a role."""
    candidates = []
    for item in read_split("train"):
        if item.get("label_origin") != "teacher-panel":
            continue
        votes = [v for v in (item.get("panel_votes") or {}).values() if v]
        split = len(set(votes)) > 1
        low = (item.get("label_confidence") or 0.0) < low_confidence
        if split or low:
            item["_reason"] = (
                "split+low" if split and low else ("split" if split else "low")
            )
            candidates.append(item)
    roles = sorted({x["role"] for x in candidates})
    ids = []
    for i, role in enumerate(roles):
        share = DISAGREEMENT_ROWS // len(roles) + (
            1 if i < DISAGREEMENT_ROWS % len(roles) else 0
        )
        ids += stratified(
            [x for x in candidates if x["role"] == role], share, "disagree"
        )
    if len(ids) < DISAGREEMENT_ROWS:
        # One role ran short: fill from the other role's remaining candidates.
        rest = [x for x in candidates if x["id"] not in set(ids)]
        ids += stratified(rest, DISAGREEMENT_ROWS - len(ids), "disagree-fill")
    chosen = set(ids[:DISAGREEMENT_ROWS])
    items = [x for x in candidates if x["id"] in chosen]
    composition = defaultdict(int)
    for x in items:
        composition[f"{x['role']}|{x['_reason']}"] += 1
    return items, {
        "candidates": len(candidates),
        "rows": len(items),
        "rules": len({x["rule_id"] for x in items}),
        "by_role_reason": dict(composition),
        "by_panel_label": dict(
            (k, sum(1 for x in items if f"{x['role']}|{x['label']}" == k))
            for k in sorted({f"{x['role']}|{x['label']}" for x in items})
        ),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--low-confidence",
        type=float,
        required=True,
        help="posterior confidence below which a panel label goes to the disagreement sheet",
    )
    args = p.parse_args()
    summary = {}
    for split in ("test", "calibration"):
        items = [x for x in read_split(split) if x.get("label") is None]
        total, priority, double = write_sheet(split, items)
        summary[split] = {
            "rows": total,
            "priority_1": priority,
            "double_label": double,
            "by_role": dict(
                (r, sum(1 for x in items if x["role"] == r))
                for r in sorted({x["role"] for x in items})
            ),
        }
    items, composition = disagreement_items(args.low_confidence)
    total, priority, double = write_sheet("disagreement", items)
    summary["disagreement"] = {
        **composition,
        "priority_1": priority,
        "double_label": double,
    }
    (OUT / "sheets-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
