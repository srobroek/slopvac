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
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

from .batch import model_body, parse_output
from .common import read_jsonl, write_jsonl
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
SHEETS = ("test", "calibration", "disagreement")


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


def run_review(root: Path, rounds: int = 3, prefix: str = "review") -> dict:
    """Every model answers every row of the PREFIX sheets `rounds` times.
    Model x round jobs run concurrently in one process, so the cost ledger
    has a single writer. Answers are cached under .cache/llm-PREFIX."""
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
            concurrency=4,
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
QUEUE_CODES = {
    "lint": {"y": "1", "n": "0", "u": "-"},
    "semantic": {"y": "1", "n": "0", "u": ""},
}


def _settled(record: dict, rounds: int) -> bool:
    votes = Counter(a for name in MODELS for a in record[f"{name}_answers"].split(","))
    agree = max((votes[a] for a in ("0", "1")), default=0)
    return (
        agree >= len(MODELS) * rounds - SETTLE_MISSES and record["ambiguous"] != "yes"
    )


def write_label_queue(
    root: Path,
    rounds: int = 3,
    prefix: str = "review",
    retired_rules: frozenset[str] = frozenset(),
) -> dict:
    """Write the rows of the PREFIX sheets that are neither settled nor
    answered by a person as label-queue.csv and label-queue.html.

    Both carry one y/n/u question per row, with the Yes and No examples for
    semantic rows. Model answers are left out so the reviewer is not anchored
    on them. Rows whose rule id is in `retired_rules` are left out too: the
    rule no longer ships, so its findings need no label."""
    rule_of = {}
    if retired_rules:
        for split in ("train", "dev", "calibration", "test"):
            for item in read_jsonl(root / "items" / f"{split}.jsonl"):
                rule_of[item["id"]] = (item.get("question") or {}).get("rule_id")
    queue = []
    for path in _sheets(root, prefix, llm=True):
        sheet = path.with_name(path.name.removeprefix("llm-"))
        kind = _kind(sheet)
        with sheet.open(newline="", encoding="utf-8") as fh:
            source = {r["item_id"]: r for r in csv.DictReader(fh)}
        with path.open(newline="", encoding="utf-8") as fh:
            for record in csv.DictReader(fh):
                row = source[record["item_id"]]
                answered = (
                    row.get("answer", "").strip()
                    or row.get("second_answer", "").strip()
                )
                # Settled, person-answered and retired-rule rows stay out.
                if (
                    answered
                    or _settled(record, rounds)
                    or rule_of.get(record["item_id"]) in retired_rules
                ):
                    continue
                question = re.sub(
                    r"\s*Answer 1 = .*$", "", row["question"], flags=re.DOTALL
                )
                if kind == "lint":
                    legend = "y = real defect · n = rule misfired · u = can't tell"
                else:
                    legend = "y = yes · n = no · u = unsure"
                guidance = "\n\n".join(
                    f"{label}: {row[key]}"
                    for key, label in (
                        LINT_FIELDS if kind == "lint" else SEMANTIC_FIELDS
                    )
                    if key not in {"flagged_text", "highlighted_text", "passage"}
                    and key not in {"yes_example", "no_example"}
                    and row.get(key)
                )
                queue.append(
                    {
                        "key": f"{sheet.stem}|{row['item_id']}",
                        "kind": kind,
                        "split": sheet.stem.rsplit("-", 1)[1],
                        "question": question,
                        "legend": legend,
                        "yes_example": row.get("yes_example", ""),
                        "no_example": row.get("no_example", ""),
                        "flag_label": "Flagged" if kind == "lint" else "Highlighted",
                        "flagged": row.get("flagged_text")
                        or row.get("highlighted_text", ""),
                        "passage": row.get("passage", ""),
                        "guidance": guidance,
                    }
                )
    order = {"test": 0, "calibration": 1, "disagreement": 2}
    queue.sort(
        key=lambda q: (q["kind"], q["question"].split("(")[0][:80], order[q["split"]])
    )
    out = root / SHEET_DIR
    with (out / "label-queue.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["n", "answer", "question", "yes_example", "no_example", "flagged"]
            + ["passage", "key"]
        )
        for n, q in enumerate(queue, 1):
            writer.writerow(
                [n, "", q["question"], q["yes_example"], q["no_example"]]
                + [q["flagged"], q["passage"], q["key"]]
            )
    html = _QUEUE_HTML.replace(
        "__DATA__", json.dumps(queue).replace("</", "<\\/")
    ).replace("__STORE__", json.dumps(f"slopvac-label-queue:{prefix}"))
    (out / "label-queue.html").write_text(html, encoding="utf-8")
    return {
        "rows": len(queue),
        "by_kind": dict(Counter(q["kind"] for q in queue)),
        "by_split": dict(Counter(f"{q['kind']}-{q['split']}" for q in queue)),
    }


def apply_label_queue(
    root: Path, answers: Path, column: str = "answer", prefix: str = "review"
) -> dict:
    """Copy y/n/u answers (label-queue.csv, or the CSV the HTML page downloads)
    into the `column` of the review sheets, as the sheet codes import-labels reads."""
    with answers.open(newline="", encoding="utf-8") as fh:
        given = {r["key"]: r["answer"].strip().lower() for r in csv.DictReader(fh)}
    given = {k: v for k, v in given.items() if v}
    bad = {k: v for k, v in given.items() if v not in {"y", "n", "u"}}
    if bad:
        raise ValueError(f"answers must be y, n or u: {sorted(bad.items())[:5]}")
    written = Counter()
    for sheet in _sheets(root, prefix):
        kind = _kind(sheet)
        with sheet.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fields, rows = list(reader.fieldnames or []), list(reader)
        changed = False
        for row in rows:
            value = given.get(f"{sheet.stem}|{row['item_id']}")
            if value is None:
                continue
            row[column] = QUEUE_CODES[kind][value]
            if kind == "semantic" and value == "u":
                row["notes"] = (row.get("notes", "") + " unsure").strip()
            written[sheet.name] += 1
            changed = True
        if changed:
            with sheet.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
    return {"answers": len(given), "written": dict(written)}


_QUEUE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>slopvac label queue</title>
<style>
body{font:16px/1.5 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;color:#1a1a1a;background:#fafafa}
header{display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap}
.meta{color:#555;font-size:.9rem}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:1.25rem 1.5rem;margin:1rem 0}
.q{font-weight:600;font-size:1.1rem}
.legend{color:#444;margin:.5rem 0 1rem}
.ex{margin:.25rem 0;color:#333}
.flag{background:#fff3c4;padding:0 .2rem;border-radius:3px}
pre{white-space:pre-wrap;font:15px/1.5 ui-monospace,monospace;background:#f4f4f4;padding:.75rem;border-radius:6px;max-height:24rem;overflow:auto}
mark{background:#ffd54a}
.buttons{display:flex;gap:.5rem;margin-top:1rem}
button{font:inherit;padding:.5rem 1rem;border:1px solid #888;border-radius:6px;background:#fff;cursor:pointer}
button.on{background:#1a1a1a;color:#fff;border-color:#1a1a1a}
button:focus-visible{outline:3px solid #2a6ef0;outline-offset:2px}
details{margin-top:.75rem;color:#333}
</style></head><body>
<header><h1>Label queue</h1>
<div><span id="progress" class="meta"></span> <button id="dl">Download answers</button></div></header>
<p class="meta">Keys: <b>y</b> / <b>n</b> / <b>u</b> answer and advance · <b>←</b>/<b>→</b> move · <b>j</b> jump to next unanswered. Answers are saved in this browser as you go.</p>
<div class="card" id="card" aria-live="polite"></div>
<script>
const DATA = __DATA__;
const STORE = __STORE__;
const answers = JSON.parse(localStorage.getItem(STORE) || "{}");
let i = DATA.findIndex(q => !answers[q.key]); if (i < 0) i = 0;
const esc = s => s.replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render(){
  const q = DATA[i], a = answers[q.key] || "";
  const passage = esc(q.passage).replace(/\\[\\[(.*?)\\]\\]/gs, "<mark>$1</mark>");
  document.getElementById("card").innerHTML =
    `<div class="meta">#${i+1} of ${DATA.length} · ${q.kind} · ${q.split}</div>
     <p class="q">${esc(q.question)}</p>
     ${q.yes_example ? `<p class="ex"><b>Yes example:</b> ${esc(q.yes_example)}</p>` : ""}
     ${q.no_example ? `<p class="ex"><b>No example:</b> ${esc(q.no_example)}</p>` : ""}
     <p class="legend">${esc(q.legend)}</p>
     ${q.flagged ? `<p>${q.flag_label}: <span class="flag">${esc(q.flagged)}</span></p>` : ""}
     ${q.passage ? `<pre id="passage">${passage}</pre>` : ""}
     ${q.guidance ? `<details><summary>Rule guidance and surrounding text</summary><pre>${esc(q.guidance)}</pre></details>` : ""}
     <div class="buttons">${["y","n","u"].map(k => `<button data-k="${k}" class="${a===k?"on":""}">${k}</button>`).join("")}
     <button data-nav="-1">← back</button><button data-nav="1">next →</button></div>`;
  const pre = document.getElementById("passage"), m = pre && pre.querySelector("mark");
  if (m) pre.scrollTop = Math.max(0, m.offsetTop - pre.offsetTop - 48);
  const done = DATA.filter(x => answers[x.key]).length;
  document.getElementById("progress").textContent = `${done} / ${DATA.length} answered`;
}
function answer(k){ answers[DATA[i].key] = k; localStorage.setItem(STORE, JSON.stringify(answers)); if (i < DATA.length-1) i++; render(); }
function move(d){ i = Math.max(0, Math.min(DATA.length-1, i+d)); render(); }
document.addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.k) answer(b.dataset.k); else if (b.dataset.nav) move(+b.dataset.nav); });
document.addEventListener("keydown", e => { if (e.metaKey || e.ctrlKey || e.altKey) return;
  if ("ynu".includes(e.key) && e.key.length === 1) answer(e.key);
  else if (e.key === "ArrowLeft") move(-1); else if (e.key === "ArrowRight") move(1);
  else if (e.key === "j") { const n = DATA.findIndex((q, k) => k > i && !answers[q.key]); if (n >= 0) { i = n; render(); } } });
document.getElementById("dl").onclick = () => {
  const rows = [["key","answer"], ...DATA.map(q => [q.key, answers[q.key] || ""])];
  const csv = rows.map(r => r.map(v => `"${v.replace(/"/g,'""')}"`).join(",")).join("\\n") + "\\n";
  const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv], {type:"text/csv"}));
  a.download = "label-answers.csv"; a.click();
};
render();
</script></body></html>
"""
