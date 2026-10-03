"""Human review sheets, one file per task and sheet.

Writes items/adjudication/<prefix>-<task>-<sheet>.csv (private; gitignored;
`--prefix` defaults to `review`):

- task: `lint-findings` (is this lint finding a real defect?) or `semantic`
  (does the highlighted text have this defect?);
- sheet: `test` and `calibration` (items with no label yet: the human sample)
  or `disagreement` (DISAGREEMENT_ROWS teacher-panel train items where the
  teachers split or the Dawid-Skene posterior is below `--low-confidence`).

Each row asks one direct question and shows only what a reviewer needs. A
lint row shows the flagged text, the passage with the flag marked [[like
this]], the surrounding text, what the rule catches, and when the rule is
known to misfire. A semantic row shows the rule's plain yes/no question with
its Yes and No examples (items/semantic-questions.yml), the highlighted text,
the passage with that region marked [[like this]], and the surrounding text.
The reviewer writes `answer` (lint findings: 1 = real defect, 0 = false
positive, - = can't tell; semantic: 1 = yes, 0 = no). Rows with
`second_rater` = yes (a rule-stratified subset of the first pass, up to 40 per
task) also take `second_answer` from a different person. `priority` 1 marks a
rule-stratified first pass (up to 120 rows per task). `item_id` is for
import-labels only.

`--prefill SHEET...` copies `answer`, `second_answer` and `notes` from earlier
lint-findings sheets into lint rows with the same item id, so answers a person
already gave are kept. Run it before import-labels: the sampler only offers
items whose label is not yet a human one.

`--unlabelled SPLIT:LINT:SEMANTIC...` writes one sheet per SPLIT instead
(PREFIX-<task>-<split>.csv), mining more rows for the LLM review: up to LINT
finding-confirmation and SEMANTIC semantic-detection items of that split with
no label, round-robin over rules with the same sampler. Items whose rule is
retired (not in the current rules), off by default (`effective_severity` off)
or an excluded judgement rule are left out, and so are items already on
another review sheet (items/adjudication/review-*.csv).
"""

import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from judge_corpus.items import (  # noqa: E402
    EXCLUDED_JUDGEMENT_RULES,
    _state_of,
    mark_span,
)

OUT = ROOT / "items/adjudication"
FIRST_PASS = 120
DOUBLE_LABEL = 40
DISAGREEMENT_ROWS = 300
# One file per task and sheet: review-<task>-<sheet>.csv. Only what a reviewer
# needs; item_id is last and is what import-labels keys on.
LINT_FIELDS = [
    "row",
    "priority",
    "second_rater",
    "question",
    "flagged_text",
    "passage",
    "surrounding_text",
    "what_the_rule_catches",
    "when_the_rule_is_wrong",
    "answer",
    "second_answer",
    "notes",
    "item_id",
]
SEMANTIC_FIELDS = [
    "row",
    "priority",
    "second_rater",
    "question",
    "yes_example",
    "no_example",
    "highlighted_text",
    "passage",
    "surrounding_text",
    "answer",
    "second_answer",
    "notes",
    "item_id",
]
TASK_FILE = {"finding-confirmation": "lint-findings", "semantic-detection": "semantic"}
PREFILL = ("answer", "second_answer", "notes")


def _rules() -> dict[str, dict]:
    """Rule definitions merged with the plain-language reviewer guide
    (items/review-guide.json, from judge_corpus.review_guide)."""
    from judge_corpus.items import _rules_current, _rules_judgement

    guide = json.loads((ROOT / "items/review-guide.json").read_text(encoding="utf-8"))
    rules = {r["id"]: r for r in [*_rules_current(), *_rules_judgement()]}
    missing = sorted(set(rules) - set(guide))
    if missing:
        raise SystemExit(f"review-guide.json lacks {len(missing)} rules: {missing[:5]}")
    return {rule_id: {**r, "guide": guide[rule_id]} for rule_id, r in rules.items()}


def _examples(rule: dict) -> str:
    return " | ".join(
        f"Defect: \u201c{e['bad']}\u201d \u2192 fine: \u201c{e.get('good', '')}\u201d"
        for e in (rule.get("examples") or [])[:3]
        if e.get("bad")
    )


def surrounding(state: dict) -> str:
    parts = []
    if state.get("heading"):
        parts.append(f"Heading: {state['heading']}")
    if state.get("context"):
        parts.append(state["context"])
    return "\n\n".join(parts)


def lint_row(question: dict, state: dict, rule: dict) -> dict:
    f = question["finding"]
    return {
        "question": (
            f"The lint rule \u201c{f['rule_name']}\u201d flagged \u201c{f['matched_text']}\u201d "
            "(marked [[like this]] in the passage). Would following the rule's fix make "
            "this text better? Answer 1 = yes, it is a real defect; 0 = no, the rule "
            "misfired here (false positive); - = cannot tell from the text shown."
        ),
        "flagged_text": f["matched_text"],
        "passage": mark_span(state["text"], f["start"], f["end"]),
        "surrounding_text": surrounding(state),
        "what_the_rule_catches": " ".join(
            x
            for x in (
                rule["guide"]["catches"],
                f"Suggested fix: {rule['fix']}" if rule.get("fix") else "",
                _examples(rule),
            )
            if x
        ),
        "when_the_rule_is_wrong": rule["guide"]["fine_when"],
    }


def semantic_row(question: dict, state: dict, rule: dict) -> dict:
    region = question["region"]
    return {
        "question": f"{question['prompt']} Answer 1 = yes; 0 = no.",
        "yes_example": question["yes_example"],
        "no_example": question["no_example"],
        "highlighted_text": state["text"][region["start"] : region["end"]],
        "passage": mark_span(state["text"], region["start"], region["end"]),
        "surrounding_text": surrounding(state),
    }


def read_prefill(paths: list[Path]) -> dict[str, dict]:
    """Answers already given on earlier lint-findings sheets, by item id."""
    given = {}
    for path in paths:
        if "lint-findings-" not in path.name:
            continue
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["answer"].strip() or row["second_answer"].strip():
                    given[row["item_id"]] = {k: row.get(k, "") for k in PREFILL}
    return given


def write_sheet(
    name: str,
    items: list[dict],
    rules: dict[str, dict],
    prefix: str,
    prefill: dict[str, dict],
) -> dict:
    first = set(stratified(items, FIRST_PASS, "first-pass"))
    double = set(
        stratified([x for x in items if x["id"] in first], DOUBLE_LABEL, "double")
    )
    by_task = defaultdict(list)
    for item in items:
        state = _state_of(ROOT, item)
        rule = rules.get(item["rule_id"], {})
        lint = item["role"] == "finding-confirmation"
        describe = lint_row if lint else semantic_row
        given = prefill.get(item["id"], {}) if lint else {}
        by_task[item["role"]].append(
            {
                "priority": 1 if item["id"] in first else 2,
                "second_rater": "yes" if item["id"] in double else "",
                **describe(item["question"], state, rule),
                **{k: given.get(k, "") for k in PREFILL},
                "item_id": item["id"],
                "_rule": item["rule_id"],
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for role, rows in by_task.items():
        rows.sort(key=lambda r: (r["priority"], r["_rule"], r["item_id"]))
        for n, row in enumerate(rows, start=1):
            row["row"] = n
            row.pop("_rule")
        fields = LINT_FIELDS if role == "finding-confirmation" else SEMANTIC_FIELDS
        path = OUT / f"{prefix}-{TASK_FILE[role]}-{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        summary[path.name] = {
            "rows": len(rows),
            "priority_1": sum(r["priority"] == 1 for r in rows),
            "second_rater": sum(r["second_rater"] == "yes" for r in rows),
            "prefilled": sum(bool(r["answer"] or r["second_answer"]) for r in rows),
        }
    return summary


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


def read_split(split: str) -> list[dict]:
    with (ROOT / f"items/{split}.jsonl").open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def disagreement_items(low_confidence: float) -> tuple[list[dict], dict]:
    """Panel-labelled train items where the valid votes split or the
    posterior is below `low_confidence`, DISAGREEMENT_ROWS of them, split
    evenly by role and round-robin over rules within a role."""
    candidates = []
    for item in read_split("train"):
        # Only items the panel voted on; the rest of train has no panel label.
        if item.get("label_origin") != "teacher-panel" or item.get("label") is None:
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


def on_review_sheets(prefix: str) -> set[str]:
    """Item ids on any review sheet (items/adjudication/review-*.csv) other
    than the PREFIX sheets themselves, so a re-run draws the same rows."""
    ids = set()
    for path in OUT.glob("review-*.csv"):
        rest = path.name.removeprefix(f"{prefix}-")
        if rest != path.name and rest.startswith(
            tuple(f"{task}-" for task in TASK_FILE.values())
        ):
            continue
        with path.open(newline="", encoding="utf-8") as fh:
            ids |= {row["item_id"] for row in csv.DictReader(fh)}
    return ids


def live_rule(rules: dict[str, dict], rule_id: str) -> bool:
    """The rule still ships (it is in the current rules), is on by default,
    and is not an excluded judgement rule."""
    rule = rules.get(rule_id)
    return (
        rule is not None
        and rule.get("effective_severity") != "off"
        and rule_id not in EXCLUDED_JUDGEMENT_RULES
    )


def unlabelled_items(
    split: str, counts: dict[str, int], rules: dict[str, dict], taken: set[str]
) -> tuple[list[dict], dict]:
    """Up to counts[role] unlabelled items of `split` per role, round-robin
    over rules, leaving out retired and off-by-default rules and the item ids
    in `taken`. Two passes over the split keep only ids in memory while
    sampling."""
    pool, dropped = [], Counter()
    path = ROOT / f"items/{split}.jsonl"
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            item = json.loads(line)
            if item.get("label") is not None or item["role"] not in counts:
                continue
            if item["id"] in taken:
                dropped["on-a-review-sheet"] += 1
            elif not live_rule(rules, item["rule_id"]):
                dropped["rule-retired-or-off"] += 1
            else:
                pool.append(
                    {"id": item["id"], "role": item["role"], "rule_id": item["rule_id"]}
                )
    chosen = set()
    for role, n in counts.items():
        mine = [x for x in pool if x["role"] == role]
        chosen.update(stratified(mine, n, f"unlabelled-{split}"))
    with path.open(encoding="utf-8") as fh:
        items = [x for x in map(json.loads, fh) if x["id"] in chosen]
    return items, {
        "pool": dict(Counter(x["role"] for x in pool)),
        "dropped": dict(dropped),
        "rows": dict(Counter(x["role"] for x in items)),
        "rules": {
            role: len({x["rule_id"] for x in items if x["role"] == role})
            for role in counts
        },
    }


def unlabelled_spec(value: str) -> tuple[str, dict[str, int]]:
    split, lint, semantic = value.split(":")
    return split, {
        "finding-confirmation": int(lint),
        "semantic-detection": int(semantic),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--low-confidence",
        type=float,
        help="posterior confidence below which a panel label goes to the "
        "disagreement sheet (required unless --unlabelled)",
    )
    p.add_argument(
        "--unlabelled",
        nargs="+",
        default=[],
        type=unlabelled_spec,
        metavar="SPLIT:LINT:SEMANTIC",
        help="write one sheet per SPLIT with up to LINT lint-finding and SEMANTIC "
        "semantic unlabelled items, instead of the test, calibration and "
        "disagreement sheets",
    )
    p.add_argument(
        "--prefix",
        default="review",
        help="sheet file prefix: PREFIX-<task>-<sheet>.csv",
    )
    p.add_argument(
        "--prefill",
        nargs="*",
        default=[],
        type=Path,
        help="earlier lint-findings sheets whose answers carry over by item id",
    )
    args = p.parse_args()
    if not args.unlabelled and args.low_confidence is None:
        p.error("--low-confidence is required unless --unlabelled is given")
    rules = _rules()
    prefill = read_prefill(args.prefill)
    summary = {}
    if args.unlabelled:
        taken = on_review_sheets(args.prefix)
        summary["items_on_other_review_sheets"] = len(taken)
        for split, counts in args.unlabelled:
            items, composition = unlabelled_items(split, counts, rules, taken)
            summary.update(write_sheet(split, items, rules, args.prefix, prefill))
            summary[f"{split}_composition"] = composition
    else:
        for split in ("test", "calibration"):
            items = [x for x in read_split(split) if x.get("label") is None]
            summary.update(write_sheet(split, items, rules, args.prefix, prefill))
        items, composition = disagreement_items(args.low_confidence)
        summary.update(write_sheet("disagreement", items, rules, args.prefix, prefill))
        summary["disagreement_composition"] = composition
    summary["prefill_answers_offered"] = len(prefill)
    (OUT / f"{args.prefix}-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
