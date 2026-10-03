"""Four-model LLM review of the reviewer sheets, with disagreement flags.

Each model gets the same question a human reviewer sees in
items/adjudication/<prefix>-<task>-<sheet>.csv (the question, flagged or
highlighted text, passage, surrounding text and rule guidance or Yes/No
examples) and returns an answer code, whether the row is ambiguous, and a
one-sentence reason. The results are written next to the sheets as
llm-<prefix>-<task>-<sheet>.csv with every model's answer and reason, the
majority, and flags:

- `unanimous`: all valid answers agree;
- `disagreement`: the answers split;
- `ambiguous`: any model flagged the row ambiguous or answered "-";
- `needs_human`: the row is not settled: fewer than len(MODELS) x rounds -
  SETTLE_MISSES votes (11 of 12) give the same definite answer (1 or 0), or a
  run flagged it ambiguous or answered "-".

A run first drops cached answers that could not be parsed (truncated
reasoning, malformed JSON) so they are asked again; refusals are kept, since
the same prompt is refused again.

These are LLM labels. They are kept apart from human labels: nothing here
writes to the item splits.

The label queues (write_label_queue, write_relabel_queue) are HTML pages for
the rows a person answers, as items/adjudication/label-queue-NAME.html. Each
row shows the full passage with the flagged span or the semantic region
highlighted, the full surrounding text, and a rule card: what the rule
catches and when it is wrong (lint) or the question with its Yes and No
examples (semantic), plus one verified bank passage that is a real defect and
one that is acceptable. No earlier answer, human or model, is shown.
apply_label_queue copies the answers back into the sheets.
"""

from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from .bank import _kept
from .batch import model_body, parse_output
from .common import read_jsonl, write_jsonl
from .items import SPLITS, _state_of, seed, semantic_questions
from .ondemand import run_ondemand

MODELS = {
    "opus": "global.anthropic.claude-opus-5-5",
    "sol": "global.openai.gpt-6-sol",
    "deepseek": "deepseek.v3.2",
    "grok": "global.xai.grok-4.6",
}
# Medium reasoning for the models that take a reasoning setting; the budget
# leaves room for hidden reasoning tokens plus the short JSON answer. Grok
# spent all of 4000 tokens reasoning on about 1% of rows.
OUTPUT_TOKENS = 8000
EXPECTED_OUTPUT_TOKENS = 1000
MIN_VALID = 3
SHEET_DIR = "items/adjudication"

PROMPT = """You are reviewing one row of a prose-lint evaluation sheet, exactly as a human reviewer would.

Question: {question}

{fields}

Reply with only a JSON object:
{{"answer": {codes}, "ambiguous": true or false, "reason": "one sentence"}}
Set "ambiguous" to true when the question, the rule guidance, or the text shown does not let a careful reviewer decide with confidence, or when reasonable reviewers could answer differently."""

LINT_FIELDS = (
    ("flagged_text", "Flagged text"),
    ("passage", "Passage (flag marked [[like this]])"),
    ("surrounding_text", "Surrounding text"),
    ("what_the_rule_catches", "What the rule catches"),
    ("when_the_rule_is_wrong", "When the rule is wrong"),
)
SEMANTIC_FIELDS = (
    ("yes_example", "Yes example"),
    ("no_example", "No example"),
    ("passage", "Passage (the highlighted text is marked [[like this]])"),
    ("surrounding_text", "Surrounding text"),
)
CODES = {"lint": {"1", "0", "-"}, "semantic": {"1", "0"}}
TASKS = ("lint-findings", "semantic")
SHEETS = ("test", "calibration", "disagreement", "train", "dev")


def _kind(sheet: Path) -> str:
    return "lint" if "lint-findings-" in sheet.name else "semantic"


def _sheets(root: Path, prefix: str, llm: bool = False) -> list[Path]:
    """The review sheets PREFIX-<task>-<sheet>.csv that exist, or with `llm`
    their llm-PREFIX-... review results."""
    lead = f"llm-{prefix}" if llm else prefix
    paths = [
        root / SHEET_DIR / f"{lead}-{task}-{name}.csv"
        for task in TASKS
        for name in SHEETS
    ]
    return [p for p in paths if p.is_file()]


def _prompt(row: dict, kind: str) -> str:
    fields = LINT_FIELDS if kind == "lint" else SEMANTIC_FIELDS
    body = "\n\n".join(f"{label}:\n{row[key]}" for key, label in fields if row.get(key))
    codes = '"1", "0" or "-"' if kind == "lint" else '"1" or "0"'
    return PROMPT.format(question=row["question"], fields=body, codes=codes)


def _body(model_id: str, prompt: str) -> dict:
    body = model_body(model_id, prompt, max_tokens=OUTPUT_TOKENS)
    if "claude-opus-5-5" in model_id:
        # Opus 5.5 rejects thinking disabled; it takes adaptive thinking and an
        # effort level instead.
        body["thinking"] = {"type": "adaptive"}
        body["output_config"] = {"effort": "medium"}
    elif "openai.gpt-6" in model_id or model_id.endswith("xai.grok-4.6"):
        body["reasoning_effort"] = "medium"
    return body


def _parse(record: dict, kind: str) -> tuple[str | None, bool, str]:
    if (record.get("modelOutput") or {}).get("stop_reason") == "refusal":
        return None, False, "refused"
    text = parse_output(record) or ""
    text = re.sub(r"<(reasoning|think)>.*?</\1>", " ", text, flags=re.DOTALL)
    for block in reversed(re.findall(r"\{.*?\}", text, flags=re.DOTALL)):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "answer" in value:
            answer = str(value["answer"]).strip()
            if answer in CODES[kind]:
                return (
                    answer,
                    bool(value.get("ambiguous")),
                    str(value.get("reason", "")).strip(),
                )
            return None, False, f"invalid answer {answer!r}"
    return None, False, "no parseable answer"


def _output(work: Path, name: str, round_no: int) -> Path:
    # Round 1 keeps the original file name, so the first full pass is reused.
    return work / (
        f"{name}-output.jsonl" if round_no == 1 else f"{name}-r{round_no}-output.jsonl"
    )


def _drop_unparsed(path: Path, kinds: dict[str, str]) -> int:
    """Remove cached records with no parseable answer, so they are retried."""
    records = list(read_jsonl(path))

    def answered(r: dict) -> bool:
        if r.get("recordId") not in kinds or "error" in r:
            return True
        answer, _, reason = _parse(r, kinds[r["recordId"]])
        return answer is not None or reason == "refused"

    keep = [r for r in records if answered(r)]
    if len(keep) != len(records):
        write_jsonl(path, keep)
    return len(records) - len(keep)


def run_review(
    root: Path, rounds: int = 3, prefix: str = "review", concurrency: int = 4
) -> dict:
    """Every model answers every row of the PREFIX sheets `rounds` times.
    Model x round jobs run concurrently in one process, so the cost ledger
    has a single writer; each job sends `concurrency` requests at a time.
    Answers are cached under .cache/llm-PREFIX."""
    from concurrent.futures import ThreadPoolExecutor

    rows: dict[str, tuple[Path, dict]] = {}
    for sheet in _sheets(root, prefix):
        with sheet.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rows[f"{sheet.stem}|{row['item_id']}"] = (sheet, row)
    work = root / ".cache" / f"llm-{prefix}"
    work.mkdir(parents=True, exist_ok=True)
    for name, model_id in MODELS.items():
        write_jsonl(
            work / f"{name}-input.jsonl",
            [
                {
                    "recordId": key,
                    "modelInput": _body(model_id, _prompt(row, _kind(sheet))),
                }
                for key, (sheet, row) in rows.items()
            ],
        )
    jobs = [(name, r) for name in MODELS for r in range(1, rounds + 1)]
    kinds = {key: _kind(sheet) for key, (sheet, _) in rows.items()}
    retried = {f"{n}-r{r}": _drop_unparsed(_output(work, n, r), kinds) for n, r in jobs}

    def run(job):
        name, round_no = job
        return job, run_ondemand(
            root,
            work / f"{name}-input.jsonl",
            MODELS[name],
            _output(work, name, round_no),
            stage=f"llm-review-{name}-r{round_no}",
            concurrency=concurrency,
            expected_output_tokens=EXPECTED_OUTPUT_TOKENS,
        )

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        runs = {f"{n}-r{r}": result for (n, r), result in pool.map(run, jobs)}
    answers: dict[str, dict[str, list[tuple]]] = {
        key: {name: [] for name in MODELS} for key in rows
    }
    for name, round_no in jobs:
        for record in read_jsonl(_output(work, name, round_no)):
            key = record.get("recordId")
            if key in rows:
                answers[key][name].append(_parse(record, _kind(rows[key][0])))
    return {
        "runs": runs,
        "retried": retried,
        **_write(root, rows, answers, rounds, prefix),
    }


def _fleiss(tables: list[Counter], raters: int) -> float | None:
    tables = [t for t in tables if sum(t.values()) == raters]
    if not tables:
        return None
    cats = sorted({c for t in tables for c in t})
    n = len(tables)
    p_j = {c: sum(t[c] for t in tables) / (n * raters) for c in cats}
    p_i = [
        (sum(v * v for v in t.values()) - raters) / (raters * (raters - 1))
        for t in tables
    ]
    p_bar, p_e = sum(p_i) / n, sum(v * v for v in p_j.values())
    return 1.0 if p_e == 1 else (p_bar - p_e) / (1 - p_e)


def _write(root: Path, rows: dict, answers: dict, rounds: int, prefix: str) -> dict:
    """Per model: its answer across rounds (majority) and whether the rounds
    agreed. Across models: consensus share over all model-round votes, the
    model-level majority, and flags."""
    out_rows: dict[Path, list[dict]] = {}
    summary: dict[str, dict] = {}
    tables: dict[str, list[Counter]] = {}
    for key, (sheet, row) in rows.items():
        per_model = {}
        unstable_models, ambiguous = [], False
        all_votes = Counter()
        for name, results in answers[key].items():
            valid = [a for a, _, _ in results if a is not None]
            all_votes.update(valid)
            ambiguous |= any(amb for _, amb, _ in results) or "-" in valid
            counts = Counter(valid)
            if len(counts) > 1:
                unstable_models.append(name)
            top = counts.most_common(1)[0] if counts else (None, 0)
            per_model[name] = top[0] if top[1] > len(valid) / 2 else None
        model_votes = Counter(a for a in per_model.values() if a is not None)
        top = model_votes.most_common(1)[0] if model_votes else (None, 0)
        n_models = sum(model_votes.values())
        consensus = top[0] if top[1] > n_models / 2 else ""
        total = sum(all_votes.values())
        disagreement = len(model_votes) > 1
        record = {
            "row": row.get("row"),
            "priority": row.get("priority"),
            "question": row.get("question"),
            "flagged_text": row.get("flagged_text", ""),
            "passage": row.get("passage"),
            "consensus": consensus,
            "consensus_share": f"{all_votes[consensus] / total:.2f}"
            if consensus and total
            else "",
            "model_votes": ", ".join(
                f"{a}={n}" for a, n in sorted(model_votes.items())
            ),
            "all_votes": ", ".join(f"{a}={n}" for a, n in sorted(all_votes.items())),
            "unanimous": "yes" if len(all_votes) == 1 else "",
            "models_disagree": "yes" if disagreement else "",
            "unstable_across_rounds": ", ".join(unstable_models),
            "ambiguous": "yes" if ambiguous else "",
            "needs_human": "",
        }
        for name, results in answers[key].items():
            record[f"{name}_answers"] = ",".join(a or "?" for a, _, _ in results)
            reasons = [
                ("[ambiguous] " if amb else "") + reason for _, amb, reason in results
            ]
            record[f"{name}_reasons"] = " || ".join(reasons)
        record["needs_human"] = "" if _settled(record, rounds) else "yes"
        record["item_id"] = row["item_id"]
        out_rows.setdefault(sheet, []).append(record)
        tables.setdefault(sheet.name, []).append(model_votes)
    for sheet, records in out_rows.items():
        path = sheet.with_name(f"llm-{sheet.name}")
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
        summary[path.name] = {
            "rows": len(records),
            "unanimous_all_rounds": sum(r["unanimous"] == "yes" for r in records),
            "models_disagree": sum(r["models_disagree"] == "yes" for r in records),
            "unstable_across_rounds": sum(
                bool(r["unstable_across_rounds"]) for r in records
            ),
            "ambiguous": sum(r["ambiguous"] == "yes" for r in records),
            "needs_human": sum(r["needs_human"] == "yes" for r in records),
            "fleiss_kappa_models": _fleiss(tables[sheet.name], len(MODELS)),
            "consensus": dict(Counter(r["consensus"] or "none" for r in records)),
        }
    per_model = {}
    for name in MODELS:
        results = [answers[k][name] for k in rows]
        stable = [len({a for a, _, _ in res if a is not None}) <= 1 for res in results]
        per_model[name] = {
            "rounds_answered": sum(len(res) for res in results),
            "invalid": sum(
                a is None and why != "refused" for res in results for a, _, why in res
            ),
            "refused": sum(why == "refused" for res in results for _, _, why in res),
            "stable_rows": sum(stable),
            "answers": dict(
                Counter(a or "invalid" for res in results for a, _, _ in res)
            ),
        }
    report = {"rounds": rounds, "sheets": summary, "models": per_model}
    (root / SHEET_DIR / f"llm-{prefix}-summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


# A row is settled, and kept out of the human queue, when at least
# len(MODELS) x rounds - SETTLE_MISSES votes give the same definite answer and
# no run flagged it ambiguous (or answered "-").
SETTLE_MISSES = 1
# Queue keys and the sheet codes they write. q means the question itself is
# unclear: a blank answer with a note, as is a semantic "unsure".
QUEUE_CODES = {
    "lint": {"y": "1", "n": "0", "u": "-", "q": ""},
    "semantic": {"y": "1", "n": "0", "u": "", "q": ""},
}
QUEUE_NOTES = {
    ("semantic", "u"): "unsure",
    ("lint", "q"): "question-unclear",
    ("semantic", "q"): "question-unclear",
}
# The relabel queue: rows a person answered on these sheets, by prefix and
# kind, first source first. An item is queued once.
RELABEL_SOURCES = (("review-v5", ("lint", "semantic")), ("review", ("lint",)))
# Acceptable bank passages a rule card shows, best first. For lint, a known
# false positive (tricky) shows when the rule is wrong.
CARD_ACCEPTABLE = {"lint": ("tricky", "near", "good"), "semantic": ("near", "good")}


def _settled(record: dict, rounds: int) -> bool:
    votes = Counter(a for name in MODELS for a in record[f"{name}_answers"].split(","))
    agree = max((votes[a] for a in ("0", "1")), default=0)
    return (
        agree >= len(MODELS) * rounds - SETTLE_MISSES and record["ambiguous"] != "yes"
    )


def _human_answered(row: dict) -> bool:
    """A person answered the row: a code in `answer` or `second_answer`, or a
    blank answer with the note a queue answer leaves (semantic unsure, or the
    question unclear)."""
    notes = row.get("notes", "").split()
    return bool(
        row.get("answer", "").strip()
        or row.get("second_answer", "").strip()
        or "unsure" in notes
        or "question-unclear" in notes
    )


def _items(root: Path, ids: set[str]) -> dict[str, dict]:
    """The items in items/*.jsonl with these ids."""
    found = {}
    for split in SPLITS:
        for item in read_jsonl(root / "items" / f"{split}.jsonl"):
            if item["id"] in ids:
                found[item["id"]] = item
    return found


def _item_id(key: str) -> str:
    return key.split("|", 1)[1]


def _split_of(key: str) -> str:
    return key.split("|", 1)[0].rsplit("-", 1)[1]


def _parts(text: str, start: int, end: int) -> list[str]:
    """`text` as [before, span, after]; all of it before when the offsets do
    not fit. The page joins the three, so it shows every character."""
    if 0 <= start < end <= len(text):
        return [text[:start], text[start:end], text[end:]]
    return [text, "", ""]


def _queue_row(root: Path, key: str, item: dict) -> dict:
    state = _state_of(root, item)
    question = item["question"]
    if item["role"] == "finding-confirmation":
        finding = question["finding"]
        start, end = finding["start"], finding["end"]
        ask = (
            f"The lint rule \u201c{finding['rule_name']}\u201d flagged the highlighted "
            "text. Would following the rule's fix make this text better?"
        )
    else:
        start, end = question["region"]["start"], question["region"]["end"]
        ask = question["prompt"]
    return {
        "key": key,
        "kind": "lint" if item["role"] == "finding-confirmation" else "semantic",
        "split": _split_of(key),
        "rule_id": item["rule_id"],
        "granularity": item.get("granularity", ""),
        "question": ask,
        "passage": _parts(state["text"], start, end),
        "heading": state.get("heading") or "",
        "context": state.get("context") or "",
    }


def _bank_pick(bank: dict, rule_id: str, kinds: tuple[str, ...]) -> dict | None:
    """One verified bank passage of the first kind the rule has, the same one
    for every row of the rule: train-split passages first, then a seeded order."""
    for kind in kinds:
        rows = sorted(
            bank.get(rule_id, {}).get(kind, []),
            key=lambda r: (
                r.get("split") != "train",
                seed(f"17:card:{rule_id}:{r['id']}"),
            ),
        )
        if rows:
            finding = rows[0].get("finding") or {}
            return {
                "kind": kind,
                "parts": _parts(
                    rows[0]["text"], finding.get("start", 0), finding.get("end", 0)
                ),
            }
    return None


def _rule_card(item: dict, guide: dict, questions: dict, bank: dict) -> dict:
    rule_id = item["rule_id"]
    if item["role"] == "finding-confirmation":
        kind = "lint"
        card = {
            "name": item["question"]["finding"]["rule_name"],
            "catches": guide[rule_id]["catches"],
            "fix": (item.get("finding") or {}).get("fix", ""),
            "fine_when": guide[rule_id]["fine_when"],
        }
    else:
        kind = "semantic"
        asked = questions[rule_id]
        card = {
            "question": asked["question"],
            "yes_example": asked["yes_example"],
            "no_example": asked["no_example"],
        }
    return {
        "kind": kind,
        **card,
        "defect": _bank_pick(bank, rule_id, ("bad",)),
        "acceptable": _bank_pick(bank, rule_id, CARD_ACCEPTABLE[kind]),
    }


def _stratified(
    keys: list[str], rule_of: dict[str, str], limit: int, salt: str
) -> list[str]:
    """Up to `limit` keys, round-robin over rules in a seeded order."""
    pools: dict[str, list[str]] = defaultdict(list)
    for key in sorted(keys, key=lambda k: seed(f"17:{salt}:{k}")):
        pools[rule_of[key]].append(key)
    rules = sorted(pools, key=lambda r: seed(f"17:{salt}:{r}"))
    picked: list[str] = []
    while len(picked) < limit and any(pools.values()):
        for rule in rules:
            if pools[rule] and len(picked) < limit:
                picked.append(pools[rule].pop(0))
    return picked


def _script_json(value) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def _write_queue(
    root: Path, name: str, keys: list[str], items: dict[str, dict]
) -> dict:
    """label-queue-NAME.csv and label-queue-NAME.html for these sheet keys,
    grouped by kind and rule. The page keeps its answers in localStorage
    under a key of its own."""
    guide = json.loads((root / "items/review-guide.json").read_text(encoding="utf-8"))
    questions, bank = semantic_questions(), _kept(root)
    queue, cards = [], {}
    for key in keys:
        item = items[_item_id(key)]
        queue.append(_queue_row(root, key, item))
        if item["rule_id"] not in cards:
            cards[item["rule_id"]] = _rule_card(item, guide, questions, bank)
    queue.sort(
        key=lambda q: (q["kind"], q["rule_id"], seed(f"17:queue:{name}:{q['key']}"))
    )
    out = root / SHEET_DIR
    with (out / f"label-queue-{name}.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["n", "answer", "kind", "split", "rule_id", "question", "flagged"]
            + ["passage", "surrounding_text", "key"]
        )
        for n, q in enumerate(queue, 1):
            before, span, after = q["passage"]
            marked = f"{before}[[{span}]]{after}" if span else before
            surrounding = "\n\n".join(
                x
                for x in (q["heading"] and f"Heading: {q['heading']}", q["context"])
                if x
            )
            writer.writerow(
                [n, "", q["kind"], q["split"], q["rule_id"], q["question"], span]
                + [marked, surrounding, q["key"]]
            )
    values = {
        "DATA": _script_json(queue),
        "RULES": _script_json(cards),
        "STORE": json.dumps(f"slopvac-label-queue-v2:{name}"),
        "FILE": json.dumps(f"label-answers-{name}.csv"),
        "NAME": html.escape(name),
    }
    # One pass, so placeholder text inside the data is never substituted.
    page = re.sub(
        r"__(DATA|RULES|STORE|FILE|NAME)__", lambda m: values[m[1]], _QUEUE_HTML
    )
    (out / f"label-queue-{name}.html").write_text(page, encoding="utf-8")
    return {
        "rows": len(queue),
        "rules": len(cards),
        "by_kind_split": dict(Counter(f"{q['kind']}-{q['split']}" for q in queue)),
    }


def write_label_queue(
    root: Path,
    name: str,
    *,
    rounds: int = 3,
    prefix: str = "review",
    retired_rules: frozenset[str] = frozenset(),
    per_split: int | None = None,
) -> dict:
    """Write label-queue-NAME.csv and label-queue-NAME.html with the rows of
    the PREFIX sheets that are neither settled nor answered by a person.

    Model answers are left out so the reviewer is not anchored on them. Rows
    whose rule id is in `retired_rules` are left out too: the rule no longer
    ships, so its findings need no label. So are rows whose item is no longer
    in items/*.jsonl. With `per_split`, at most that many rows per sheet split
    (train, dev, test, ...), round-robin over rules."""
    keys = []
    for path in _sheets(root, prefix, llm=True):
        sheet = path.with_name(path.name.removeprefix("llm-"))
        with sheet.open(newline="", encoding="utf-8") as fh:
            answered = {
                r["item_id"]
                for r in csv.DictReader(fh)
                if r.get("answer", "").strip() or r.get("second_answer", "").strip()
            }
        with path.open(newline="", encoding="utf-8") as fh:
            keys += [
                f"{sheet.stem}|{record['item_id']}"
                for record in csv.DictReader(fh)
                if record["item_id"] not in answered and not _settled(record, rounds)
            ]
    items = _items(root, {_item_id(k) for k in keys})
    open_rows = len(keys)
    keys = [k for k in keys if _item_id(k) in items]
    missing = open_rows - len(keys)
    keys = [k for k in keys if items[_item_id(k)]["rule_id"] not in retired_rules]
    by_split = Counter(_split_of(k) for k in keys)
    if per_split is not None:
        rule_of = {k: items[_item_id(k)]["rule_id"] for k in keys}
        keys = [
            k
            for split in sorted(by_split)
            for k in _stratified(
                [k for k in keys if _split_of(k) == split],
                rule_of,
                per_split,
                f"{name}:{split}",
            )
        ]
    return {
        "open_rows": open_rows,
        "missing_items": missing,
        "open_by_split": dict(by_split),
        **_write_queue(root, name, keys, items),
    }


def write_relabel_queue(root: Path, name: str = "relabel") -> dict:
    """Write label-queue-NAME.csv and label-queue-NAME.html for a blind
    relabel: every review-v5 row a person answered, then every older review
    lint-findings row a person answered whose item is not queued already.
    Rows whose item is no longer in items/*.jsonl are left out. The page and
    the CSV show no earlier answer; apply the answers with
    apply_label_queue(column="relabel_answer")."""
    keys, seen = [], set()
    for prefix, kinds in RELABEL_SOURCES:
        for sheet in _sheets(root, prefix):
            if _kind(sheet) not in kinds:
                continue
            with sheet.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    if _human_answered(row) and row["item_id"] not in seen:
                        seen.add(row["item_id"])
                        keys.append(f"{sheet.stem}|{row['item_id']}")
    items = _items(root, seen)
    kept = [k for k in keys if _item_id(k) in items]
    return {
        "answered_rows": len(keys),
        "missing_items": len(keys) - len(kept),
        "by_sheet": dict(Counter(k.split("|", 1)[0] for k in kept)),
        **_write_queue(root, name, kept, items),
    }


def apply_label_queue(root: Path, answers: Path, column: str = "answer") -> dict:
    """Copy y/n/u/q answers (label-queue-NAME.csv, or the CSV the HTML page
    downloads) into `column` of the sheet each key names, as the sheet codes
    import-labels reads. A missing column is added before item_id.

    q (question unclear) and a semantic u write a blank answer and a note,
    `question-unclear` or `unsure`: appended to `notes` for column `answer`,
    otherwise set in COLUMN_notes, so a relabel never touches the notes of the
    first answer. Every key must name an existing sheet row."""
    with answers.open(newline="", encoding="utf-8") as fh:
        given = {r["key"]: r["answer"].strip().lower() for r in csv.DictReader(fh)}
    given = {k: v for k, v in given.items() if v}
    bad = {k: v for k, v in given.items() if v not in {"y", "n", "u", "q"}}
    if bad:
        raise ValueError(f"answers must be y, n, u or q: {sorted(bad.items())[:5]}")
    by_sheet: dict[str, dict[str, str]] = defaultdict(dict)
    for key, value in given.items():
        stem, item_id = key.split("|", 1)
        by_sheet[stem][item_id] = value
    notes_column = "notes" if column == "answer" else f"{column}_notes"
    updates = []
    for stem, values in sorted(by_sheet.items()):
        sheet = root / SHEET_DIR / f"{stem}.csv"
        if not sheet.is_file():
            raise ValueError(
                f"{len(values)} answers name {sheet.name}, which does not exist"
            )
        with sheet.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields, rows = list(reader.fieldnames or []), list(reader)
        unknown = set(values) - {r["item_id"] for r in rows}
        if unknown:
            raise ValueError(f"{sheet.name} has no rows for {sorted(unknown)[:5]}")
        for col in (column, notes_column):
            if col not in fields:
                fields.insert(fields.index("item_id"), col)
        updates.append((sheet, _kind(sheet), fields, rows, values))
    written: Counter = Counter()
    for sheet, kind, fields, rows, values in updates:
        for row in rows:
            value = values.get(row["item_id"])
            if value is None:
                continue
            row[column] = QUEUE_CODES[kind][value]
            note = QUEUE_NOTES.get((kind, value), "")
            if notes_column != "notes":
                row[notes_column] = note
            elif note and note not in row.get("notes", "").split():
                row["notes"] = f"{row.get('notes', '')} {note}".strip()
            written[sheet.name] += 1
        with sheet.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return {
        "answers": len(given),
        "by_answer": dict(Counter(given.values())),
        "written": dict(written),
    }


_QUEUE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>slopvac label queue: __NAME__</title>
<style>
:root{--ink:#1b1b1b;--muted:#565656;--line:#d4d4d0;--paper:#f6f6f3;--card:#fff;--hl:#ffe066;--hl-edge:#9a7400;--focus:#1f5fd6;--bar:3.5rem}
*{box-sizing:border-box}
body{margin:0;font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--ink);background:var(--paper)}
.bar{position:sticky;top:0;z-index:1;display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1rem;padding:.6rem 1.25rem;background:var(--card);border-bottom:1px solid var(--line)}
.bar h1{font-size:1rem;margin:0 auto 0 0}
.answers,.nav{display:flex;flex-wrap:wrap;gap:.4rem}
button{font:inherit;min-height:2.25rem;padding:.3rem .75rem;border:1px solid #8a8a8a;border-radius:6px;background:#fff;color:inherit;cursor:pointer}
button:hover{background:#efefec}
button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:#fff}
button:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
kbd{font:600 .85em ui-monospace,SFMono-Regular,Menlo,monospace;padding:0 .3em;border:1px solid #b5b5b5;border-bottom-width:2px;border-radius:4px;background:#f7f7f7;color:var(--ink)}
main{max-width:90rem;margin:0 auto;padding:1rem 1.25rem 4rem}
.help,.meta{color:var(--muted)}
.intro{display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:.5rem 1.5rem;margin:0 0 1rem}
.help{margin:0;max-width:80ch}
.meta{font-size:.9rem;margin:0}
.question{font-size:1.15rem;line-height:1.4;margin:.25rem 0 1rem;max-width:70ch}
.question:focus{outline:none}
.layout{display:grid;gap:1.25rem;grid-template-columns:minmax(0,1fr);align-items:start}
@media (min-width:68rem){.layout{grid-template-columns:minmax(0,3fr) minmax(0,2fr)}}
.panel{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:1rem 1.25rem}
.panel h2{font-size:1rem;margin:1.25rem 0 .4rem}
.panel h2:first-child{margin-top:0}
.panel h3{font-size:.95rem;margin:1rem 0 .25rem}
.panel p{margin:.25rem 0 .5rem;max-width:75ch}
.text{white-space:pre-wrap;overflow-wrap:anywhere;max-width:80ch}
.context{color:#333;border-left:3px solid var(--line);padding-left:.75rem}
.example{margin:.25rem 0 .75rem;padding:.5rem .75rem;border:1px solid var(--line);border-radius:6px;background:#f8f8f6}
mark{background:var(--hl);color:inherit;box-shadow:0 0 0 2px var(--hl-edge);border-radius:2px;scroll-margin:calc(var(--bar) + 2rem) 0 2rem}
.none{color:var(--muted);font-style:italic}
.rule.stick{position:sticky;top:calc(var(--bar) + 1rem)}
#jump{margin:0 0 .5rem}
@media (max-width:40rem){.bar{padding:.5rem .75rem}main{padding:.75rem .75rem 4rem}.panel{padding:.75rem}}
</style></head>
<body>
<header class="bar">
<h1>Label queue: __NAME__</h1>
<span id="progress" class="meta" role="status"></span>
<div class="answers" id="answers" role="group" aria-label="Answer"></div>
<div class="nav"><button type="button" data-nav="-1" aria-label="Previous row"><kbd>\u2190</kbd></button><button type="button" data-nav="1" aria-label="Next row"><kbd>\u2192</kbd></button></div>
</header>
<main>
<div class="intro">
<p class="help">Press <kbd>y</kbd>, <kbd>n</kbd> or <kbd>u</kbd> to answer and go to the next row, or <kbd>q</kbd> when the question itself is unclear. <kbd>\u2190</kbd> and <kbd>\u2192</kbd> move between rows; <kbd>j</kbd> jumps to the next unanswered row. Answers are saved in this browser as you go. Download them when you finish.</p>
<button type="button" id="dl">Download answers</button>
</div>
<article id="row" aria-labelledby="question"></article>
</main>
<script>
const DATA = __DATA__;
const RULES = __RULES__;
const STORE = __STORE__;
const FILE = __FILE__;
const KEYS = ["y", "n", "u", "q"];
const LABELS = {
  lint: {y: "Real defect", n: "Rule misfired", u: "Can't tell", q: "Question unclear"},
  semantic: {y: "Yes", n: "No", u: "Unsure", q: "Question unclear"},
};
const EXAMPLE = {
  lint: {
    bad: "Real defect: the rule fires, and following its fix makes the text better.",
    tricky: "Acceptable: the rule fires, but the text is fine as written.",
    near: "Acceptable: close to what the rule catches; the rule does not fire.",
    good: "Acceptable: the rule does not fire, and the text is fine.",
  },
  semantic: {
    bad: "Yes: the passage has the defect.",
    near: "No: close to the defect, but the passage is fine.",
    good: "No: the passage is fine.",
  },
};
const answers = JSON.parse(localStorage.getItem(STORE) || "{}");
let i = Math.max(0, DATA.findIndex(q => !answers[q.key]));
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const marked = (p, id) => p[1] ? `${esc(p[0])}<mark${id ? ` id="${id}"` : ""}>${esc(p[1])}</mark>${esc(p[2])}` : esc(p[0]);
function example(kind, ex, what) {
  if (!ex) return `<p class="none">The verified bank has no ${what} passage for this rule.</p>`;
  return `<p>${esc(EXAMPLE[kind][ex.kind])}</p><div class="text example">${marked(ex.parts)}</div>`;
}
function card(q, r) {
  if (r.kind === "lint") return `<h2>Rule: ${esc(r.name)}</h2><p class="meta">${esc(q.rule_id)}</p>
<h3>What the rule catches</h3><p>${esc(r.catches)}</p>
${r.fix ? `<h3>Suggested fix</h3><p>${esc(r.fix)}</p>` : ""}
<h3>When the rule is wrong</h3>${r.fine_when ? `<p>${esc(r.fine_when)}</p>` : `<p class="none">The guide records no common misfire for this rule. Judge whether following the fix would make this text better.</p>`}
<h3>Verified examples</h3>${example("lint", r.defect, "real-defect")}${example("lint", r.acceptable, "acceptable")}`;
  return `<h2>Rule</h2><p class="meta">${esc(q.rule_id)}</p>
<h3>Question</h3><p>${esc(r.question)}</p>
<h3>Yes example</h3><div class="text example">${esc(r.yes_example)}</div>
<h3>No example</h3><div class="text example">${esc(r.no_example)}</div>
<h3>Verified passages</h3>${example("semantic", r.defect, "defect")}${example("semantic", r.acceptable, "acceptable")}`;
}
function render() {
  const row = document.getElementById("row");
  if (!DATA.length) { row.innerHTML = `<p id="question" tabindex="-1">This queue is empty.</p>`; return; }
  const q = DATA[i], a = answers[q.key] || "";
  const what = q.kind === "lint" ? "the flagged text is highlighted" : "the region the question asks about is highlighted";
  row.innerHTML = `<p class="meta">Row ${i + 1} of ${DATA.length} \u00b7 ${q.kind === "lint" ? "Lint finding" : "Semantic question"} \u00b7 ${esc(q.split)} \u00b7 ${esc(q.granularity)}${a ? ` \u00b7 your answer: ${esc(LABELS[q.kind][a])}` : ""}</p>
<h2 class="question" id="question" tabindex="-1">${esc(q.question)}</h2>
<div class="layout">
<section class="panel" aria-label="Text to judge">
<h2>Passage${q.passage[1] ? ` (${what})` : ""}</h2>
<button type="button" id="jump" hidden>Jump to the highlight</button>
<div class="text" id="passage">${marked(q.passage, "hl")}</div>
<h2>Surrounding text</h2>
${q.heading ? `<p class="meta">Section heading: ${esc(q.heading)}</p>` : ""}
${q.context ? `<div class="text context" id="context">${esc(q.context)}</div>` : `<p class="none">None: the passage stands on its own.</p>`}
</section>
<aside class="panel rule" id="rule" aria-label="Rule card">${card(q, RULES[q.rule_id])}</aside>
</div>`;
  document.getElementById("answers").innerHTML = KEYS.map(k =>
    `<button type="button" data-k="${k}" aria-pressed="${a === k}"><kbd>${k}</kbd> ${esc(LABELS[q.kind][k])}</button>`).join("");
  const done = DATA.filter(x => answers[x.key]).length;
  document.getElementById("progress").textContent = `${done} of ${DATA.length} answered`;
  layout();
}
function layout() {
  const bar = document.querySelector(".bar").offsetHeight;
  document.documentElement.style.setProperty("--bar", `${bar}px`);
  const rule = document.getElementById("rule"), hl = document.getElementById("hl"), jump = document.getElementById("jump");
  if (rule) {
    rule.classList.remove("stick");
    rule.classList.toggle("stick", matchMedia("(min-width: 68rem)").matches && rule.offsetHeight + bar + 32 <= innerHeight);
  }
  if (jump) jump.hidden = !hl || hl.getBoundingClientRect().top < innerHeight - 48;
}
function show() {
  render();
  window.scrollTo(0, 0);
  layout();
  document.getElementById("question").focus({preventScroll: true});
}
function answer(k) {
  if (!DATA.length) return;
  answers[DATA[i].key] = k;
  localStorage.setItem(STORE, JSON.stringify(answers));
  if (i < DATA.length - 1) i++;
  show();
}
function move(d) { i = Math.max(0, Math.min(DATA.length - 1, i + d)); show(); }
function nextOpen() {
  const after = DATA.findIndex((x, j) => j > i && !answers[x.key]);
  const n = after >= 0 ? after : DATA.findIndex(x => !answers[x.key]);
  if (n >= 0) { i = n; show(); }
}
function download() {
  const rows = [["key", "answer"], ...DATA.map(q => [q.key, answers[q.key] || ""])];
  const text = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",")).join("\\n") + "\\n";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], {type: "text/csv"}));
  a.download = FILE;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
document.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.k) answer(b.dataset.k);
  else if (b.dataset.nav) move(+b.dataset.nav);
  else if (b.id === "jump") document.getElementById("hl").scrollIntoView({block: "center"});
  else if (b.id === "dl") download();
});
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  if (KEYS.includes(k)) { e.preventDefault(); answer(k); }
  else if (k === "ArrowLeft") move(-1);
  else if (k === "ArrowRight") move(1);
  else if (k === "j") nextOpen();
});
window.addEventListener("resize", layout);
show();
</script></body></html>
"""
