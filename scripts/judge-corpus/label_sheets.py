"""Human labelling sheets for the unlabelled test and calibration items.

Reads items/{test,calibration}.jsonl, keeps the items that still have no label
(the human-adjudication sample), and writes items/adjudication/label-<split>.csv
(private; gitignored). One row per item: what to judge, the allowed labels, the
flagged text, and the span with the flagged text marked [[like this]]. The
`priority` column marks a rule-stratified first pass (up to 120 rows per role)
as 1 and the rest as 2. Fill in `label` with one of `allowed_labels`.
"""

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
FIELDS = [
    "priority",
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
    "label",
    "notes",
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


def first_pass(items: list[dict]) -> set[str]:
    rng = random.Random(17)
    by_role = defaultdict(lambda: defaultdict(list))
    for item in items:
        by_role[item["role"]][item["rule_id"]].append(item["id"])
    chosen = set()
    for rules in by_role.values():
        pools = {r: rng.sample(ids, len(ids)) for r, ids in sorted(rules.items())}
        picked = []
        while len(picked) < FIRST_PASS and any(pools.values()):
            for r in sorted(pools):
                if pools[r] and len(picked) < FIRST_PASS:
                    picked.append(pools[r].pop())
        chosen.update(picked)
    return chosen


def build(split: str) -> tuple[int, int]:
    items = [
        x
        for x in (json.loads(line) for line in (ROOT / f"items/{split}.jsonl").open())
        if x.get("label") is None
    ]
    first = first_pass(items)
    rows = []
    for item in items:
        state = _state_of(ROOT, item)
        rows.append(
            {
                "priority": 1 if item["id"] in first else 2,
                "item_id": item["id"],
                "role": item["role"],
                "granularity": item["granularity"],
                "genre": item["genre"],
                **describe(item["question"], state),
                "heading": state.get("heading", ""),
                "context": state.get("context", ""),
                "label": "",
                "notes": "",
            }
        )
    rows.sort(key=lambda r: (r["priority"], r["role"], r["rule"], r["item_id"]))
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / f"label-{split}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows), len(first)


if __name__ == "__main__":
    for split in ("test", "calibration"):
        total, priority = build(split)
        print(f"{split}: {total} rows, {priority} priority-1")
