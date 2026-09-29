"""Rule example bank: short generated passages per rule, verified before use.

Sonnet 5 writes, on demand, bad, good, tricky and near-miss passages for every
current lint rule and every judgement rule, spread over the corpus genres.
Verification (`bank verify`):

- Lint rules. `slopvac lint` runs on every passage. A bad passage is kept when
  the rule fires and gpt-oss and Sonnet both confirm the finding as a
  real-defect. A tricky passage (acceptable prose that trips the rule) is kept
  when the rule fires and both teachers call the finding a false-positive: a
  known false positive. Good and near-miss passages (acceptable prose close to
  the rule's triggers) are kept when the rule does not fire and both teachers
  judge the text acceptable under the rule.
- Judgement rules. Bad passages are kept when both teachers answer true to the
  rule's judgement question; good and near-miss passages when both answer
  false.

The bank text stays private: .cache/bank/bank.jsonl and s3://<bucket>/bank/.
items/bank-manifest.json (committed) records the rule descriptions the panel
prompt uses, per-rule generated/kept/rejected counts, and the bank digest.
Every row records its provenance: generator model, prompt digest, rule id.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

from .batch import model_body, parse_json_object, parse_output
from .bedrock import upload
from .common import read_jsonl, write_jsonl
from .items import (
    BANK_PATH,
    CANONICAL,
    _lint_text,
    _offset,
    _rules_current,
    _rules_judgement,
    _run_lint,
    bank_split,
    digest,
    held_out,
    question_for,
    seed,
    sentences,
)
from .ondemand import run_ondemand

GENERATOR = "us.anthropic.claude-sonnet-5"
# Passages requested per rule and kind; verification rejects some.
REQUEST = {
    "finding-confirmation": {"bad": 22, "good": 22, "tricky": 16, "near": 10},
    "semantic-detection": {"bad": 22, "good": 22, "near": 12},
}
GENRES = {
    "reference": "technical reference documentation",
    "informal": "forum or Q&A answers",
    "consumer": "end-user help and product guidance",
    "internal": "internal engineering notes, design docs and runbooks",
    "change-comms": "release notes, changelogs and announcements",
}
GENERATION_TOKENS = 6000
MANIFEST = Path("items/bank-manifest.json")
BANK_DIR = BANK_PATH.parent
# Verdict each kind must receive from both judges.
EXPECTED = {
    ("finding-confirmation", "bad"): "real-defect",
    ("finding-confirmation", "tricky"): "false-positive",
    ("finding-confirmation", "good"): "false",
    ("finding-confirmation", "near"): "false",
    ("semantic-detection", "bad"): "true",
    ("semantic-detection", "good"): "false",
    ("semantic-detection", "near"): "false",
}
# Whether the lint rule must fire on a kept passage of each kind.
MUST_FIRE = {"bad": True, "tricky": True, "good": False, "near": False}


def bank_rules() -> list[dict]:
    return [{**r, "role": "finding-confirmation"} for r in _rules_current()] + [
        {**r, "role": "semantic-detection"} for r in _rules_judgement()
    ]


def _describe(message: str) -> str:
    return re.sub(r"\{(match|replacement|lemma)\}", "…", message or "").strip()


def rule_guide_entry(rule: dict) -> dict:
    return {
        "role": rule["role"],
        "name": rule.get("name", rule["id"]),
        "description": _describe(rule.get("message", "")),
        "fix": rule.get("fix", ""),
    }


def _long_form(rule: dict) -> bool:
    """Rules that inspect paragraphs, documents, headings or raw Markdown need
    multi-paragraph or formatted passages to fire."""
    return (
        rule.get("scope") in ("document", "heading", "raw")
        or (
            rule.get("scope") == "paragraph"
            and rule.get("kind") in ("metric", "structure")
        )
        or rule.get("category") in ("ai-tells-formatting", "prose-format")
    )


def _detector(rule: dict) -> str:
    lines = [f"Detector kind: {rule.get('kind')}, scope: {rule.get('scope')}."]
    if rule.get("pattern"):
        case = " (case-insensitive)" if rule.get("ignore_case") else ""
        lines.append(f"Regular expression{case}: {rule['pattern'][:900]}")
    if rule.get("tokens"):
        lines.append("Trigger phrases: " + "; ".join(rule["tokens"][:60]))
    if rule.get("substitutions"):
        pairs = list(rule["substitutions"].items())[:40]
        lines.append(
            "Trigger patterns and suggested replacements: "
            + "; ".join(f"{k} -> {v}" for k, v in pairs)
        )
    if rule.get("metric"):
        lines.append(
            f"Metric: {rule['metric']} {rule.get('comparison', 'gt')} "
            f"{rule.get('threshold')} per {rule.get('scope')}."
        )
    if rule.get("exceptions"):
        lines.append(
            "Text inside these contexts never triggers the rule: "
            + ", ".join(rule["exceptions"])
            + "."
        )
    if rule.get("text_type") not in (None, "any"):
        lines.append(f"The rule only checks {rule['text_type']} text.")
    return "\n".join(lines)


def _pinned(rule: dict) -> str:
    rows = []
    for e in rule.get("examples") or []:
        if str(e.get("note") or "").startswith("preserve") and not e.get("good"):
            # A preserve note marks the "bad" text as acceptable after all.
            rows.append(f"- acceptable: {e.get('bad')} ({e['note']})")
            continue
        parts = [f"{k}: {e[k]}" for k in ("bad", "good", "note") if e.get(k)]
        if parts:
            rows.append("- " + " | ".join(parts))
    return "\n".join(rows[:6])


def _task(rule: dict, kind: str, n: int) -> str:
    lint = rule["role"] == "finding-confirmation"
    if lint:
        return {
            "bad": f"Write {n} passages that each contain a clear instance of the "
            "defect this rule targets, phrased so its detector fires, and bad enough "
            "that a careful editor would change the text under this rule.",
            "good": f"Write {n} passages on similar subjects that a careful editor "
            "would accept under this rule. Avoid the defect and every trigger above.",
            "tricky": f"Write {n} passages of acceptable, well-edited prose that "
            "still contain one of the rule's triggers, used legitimately: a literal "
            "or technical sense, a proper noun or product name, a term the domain "
            "requires, or a construction that only resembles the defect. The "
            "detector must fire, yet a careful editor would keep the passage as is.",
            "near": f"Write {n} passages of acceptable prose that come close to the "
            "rule's triggers without matching them: related words, near variants, "
            "or similar sentence shapes the detector does not match. A careful "
            "editor would keep each passage as is.",
        }[kind]
    return {
        "bad": f"Write {n} passages that each clearly exhibit the defect: the "
        "answer to the judgement question is yes.",
        "good": f"Write {n} passages on similar subjects where the answer to the "
        "judgement question is clearly no.",
        "near": f"Write {n} passages that carry the surface cues a quick reader "
        "associates with this defect, but where the answer to the judgement "
        "question is still no (for example the preserve cases noted above).",
    }[kind]


def generation_prompt(rule: dict, kind: str) -> str:
    n = REQUEST[rule["role"]][kind]
    lint = rule["role"] == "finding-confirmation"
    per_genre = max(1, n // len(GENRES))
    length = (
        "Each passage is 2 to 4 short paragraphs separated by blank lines, at most "
        "150 words; use Markdown only where the rule inspects formatting or headings."
        if _long_form(rule)
        else "Each passage is one to three sentences, at most 60 words, plain prose "
        "without headings or lists."
    )
    header = [
        "You write test passages for a prose-quality checker.",
        f"Rule id: {rule['id']}",
        f"Rule name: {rule.get('name', rule['id'])}",
        f"What it flags: {_describe(rule.get('message', ''))}",
        f"How to fix: {rule.get('fix') or 'see the judgement question'}",
    ]
    if lint:
        header.append(_detector(rule))
    else:
        header.append(f"Judgement question: {rule.get('judgement_question', '')}")
    pinned = _pinned(rule)
    if pinned:
        header.append("Pinned rule examples (do not copy them):\n" + pinned)
    genres = "; ".join(f"{g} ({d})" for g, d in GENRES.items())
    return "\n".join(
        header
        + [
            "",
            _task(rule, kind, n),
            f"Spread them evenly over these genres, about {per_genre} each: {genres}.",
            length,
            "Vary subjects, vocabulary and sentence shape. Every passage stands alone.",
            'Reply with only JSON: {"examples": [{"genre": "<genre>", "text": "<passage>"}]}',
        ]
    )


def _paths(root: Path) -> dict[str, Path]:
    d = root / BANK_DIR
    return {
        "generate_in": d / "generate-in.jsonl",
        "generate_out": d / "generate-out.jsonl",
        "candidates": d / "candidates.jsonl",
        "bank": root / BANK_PATH,
    }


def _write_manifest(root: Path, rules: list[dict], rows: list[dict], extra: dict):
    held = held_out([r for r in rules if r["role"] == "finding-confirmation"]) | (
        held_out([r for r in rules if r["role"] == "semantic-detection"])
    )
    per_rule: dict[str, dict] = {}
    for rule in rules:
        entry = {**rule_guide_entry(rule), "held_out": rule["id"] in held}
        for kind in REQUEST[rule["role"]]:
            mine = [r for r in rows if r["rule_id"] == rule["id"] and r["kind"] == kind]
            counts: dict = {"generated": len(mine)}
            if any("kept" in r for r in mine):
                counts["kept"] = sum(r["kept"] for r in mine)
                counts["rejected"] = dict(
                    Counter(r["reject_reason"] for r in mine if not r["kept"])
                )
            entry[kind] = counts
        per_rule[rule["id"]] = entry
    manifest = {
        "schema_version": 1,
        "seed": 17,
        "generator": GENERATOR,
        "request_per_rule": REQUEST,
        "rules": per_rule,
        **extra,
    }
    (root / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def generate_bank(root: Path, *, max_usd: float) -> dict:
    rules = bank_rules()
    paths = _paths(root)
    records, meta = [], {}
    for rule in rules:
        for kind in REQUEST[rule["role"]]:
            prompt = generation_prompt(rule, kind)
            body = model_body(GENERATOR, prompt, max_tokens=GENERATION_TOKENS)
            body["thinking"] = {"type": "disabled"}
            record_id = f"{rule['id']}|{kind}"
            records.append({"recordId": record_id, "modelInput": body})
            meta[record_id] = (rule, kind, digest(prompt.encode("utf-8")))
    write_jsonl(paths["generate_in"], records)
    job = run_ondemand(
        root,
        paths["generate_in"],
        GENERATOR,
        paths["generate_out"],
        stage="bank-generate",
        concurrency=8,
        expected_output_tokens=2200,
        max_usd=max_usd,
    )
    candidates, seen, parse_failures = [], set(), []
    for line in read_jsonl(paths["generate_out"]):
        if "modelOutput" not in line or line["recordId"] not in meta:
            continue
        rule, kind, prompt_digest = meta[line["recordId"]]
        parsed = parse_json_object(parse_output(line)) or {}
        examples = parsed.get("examples")
        if not isinstance(examples, list):
            parse_failures.append(line["recordId"])
            continue
        for index, example in enumerate(examples):
            if not isinstance(example, dict):
                continue
            text = str(example.get("text") or "").strip()
            genre = example.get("genre")
            key = (rule["id"], " ".join(text.lower().split()))
            if not text or genre not in GENRES or len(text) > 1500 or key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "id": digest(f"{rule['id']}|{kind}|{text}".encode())[:20],
                    "rule_id": rule["id"],
                    "role": rule["role"],
                    "kind": kind,
                    "genre": genre,
                    "text": text,
                    "provenance": {
                        "model": GENERATOR,
                        "prompt_sha256": prompt_digest,
                        "record_id": line["recordId"],
                        "index": index,
                        "rule_id": rule["id"],
                    },
                }
            )
    write_jsonl(paths["candidates"], candidates)
    _write_manifest(
        root,
        rules,
        candidates,
        {"generation_job": job, "parse_failures": parse_failures},
    )
    return {
        "job": job,
        "candidates": len(candidates),
        "by_kind": dict(Counter(f"{c['role']}|{c['kind']}" for c in candidates)),
        "parse_failures": parse_failures,
    }


def _lint_question(rule: dict) -> dict:
    """A yes/no question about a lint rule, for passages it does not fire on."""
    return {
        "type": "noul",
        "rule_id": rule["id"],
        "prompt": (
            f'Does the text contain the defect that the lint rule "{rule.get("name", rule["id"])}" '
            f"targets ({_describe(rule.get('message', ''))})? Answer true only if a "
            "careful editor would change the text under this rule."
        ),
        "criteria": [
            {k: e.get(k) for k in ("bad", "good", "note") if e.get(k) is not None}
            for e in rule.get("examples", [])
        ],
    }


def _granularity_of(text: str) -> str:
    if "\n" in text.strip():
        return "document"
    return "sentence" if len(sentences(text, 0, len(text))) == 1 else "paragraph"


def judge_item(rule: dict, row: dict) -> dict:
    """The panel-shaped item a judge sees for one bank passage."""
    text = row["text"]
    state = {
        "text": text,
        "context": "",
        "heading": "",
        "genre": row["genre"],
        "granularity": _granularity_of(text),
    }
    if row["role"] == "semantic-detection":
        question = question_for("semantic-detection", rule)
    elif row["kind"] in ("bad", "tricky"):
        f = row["finding"]
        base = {
            "rule_id": rule["id"],
            "rule_name": rule.get("name", rule["id"]),
            "rule_message": rule.get("message", ""),
            "message": f["message"],
            "matched_text": f["matched_text"],
        }
        question = question_for("finding-confirmation", rule, base)
        question["finding"] = {
            "rule_id": rule["id"],
            "rule_name": rule.get("name", rule["id"]),
            "rule_message": rule.get("message", ""),
            "lint_message": f["message"],
            "matched_text": f["matched_text"],
            "start": f["start"],
            "end": f["end"],
        }
    else:
        question = _lint_question(rule)
    return {
        "id": row["id"],
        "role": row["role"],
        "rule_id": rule["id"],
        "genre": row["genre"],
        "granularity": state["granularity"],
        "state": state,
        "question": question,
    }


def _lint_candidates(root: Path, rows: list[dict]) -> None:
    work = root / BANK_DIR / "lint"
    work.mkdir(parents=True, exist_ok=True)
    files = []
    for row in rows:
        path = work / f"{row['id']}.md"
        path.write_text(_lint_text(row["text"]) + "\n", encoding="utf-8")
        files.append((row["id"], path))
    found = _run_lint(files, workers=6)
    for row in rows:
        hits = [
            f
            for f in found.get(f"{row['id']}.md", [])
            if f["rule_id"] == row["rule_id"]
        ]
        row["lint_fired"] = bool(hits)
        if hits:
            f = hits[0]
            start = _offset(row["text"], f.get("line", 1), f.get("column", 1))
            matched = f.get("matched_text") or ""
            if matched and row["text"][start : start + len(matched)] != matched:
                pos = row["text"].find(matched)
                start = pos if pos >= 0 else start
            row["finding"] = {
                "message": f.get("message", ""),
                "matched_text": matched,
                "start": start,
                "end": start + len(matched),
                "line": f.get("line"),
                "column": f.get("column"),
            }


def verify_bank(root: Path, *, max_usd: float) -> dict:
    from .panel import MODELS, _allowed_labels, _answer, _panel_body, _prompt

    judges = {v: MODELS[v] for v in ("anthropic", "openai")}
    rules = {r["id"]: r for r in bank_rules()}
    paths = _paths(root)
    rows = [r for r in read_jsonl(paths["candidates"]) if r["rule_id"] in rules]
    lint_rows = [r for r in rows if r["role"] == "finding-confirmation"]
    _lint_candidates(root, lint_rows)
    for row in lint_rows:
        if row["lint_fired"] != MUST_FIRE[row["kind"]]:
            row["kept"] = False
            row["reject_reason"] = "lint-fired" if row["lint_fired"] else "lint-silent"
    to_judge = [r for r in rows if "kept" not in r]
    items = {r["id"]: judge_item(rules[r["rule_id"]], r) for r in to_judge}
    votes: dict[str, dict] = defaultdict(dict)
    jobs = {}
    budget = max_usd
    for vendor, model in judges.items():
        records = [
            {
                "recordId": f"{r['id']}:{vendor}",
                "modelInput": _panel_body(
                    model, _prompt(root, items[r["id"]], examples=[])
                ),
            }
            for r in to_judge
        ]
        inp = root / BANK_DIR / f"judge-{vendor}-in.jsonl"
        out = root / BANK_DIR / f"judge-{vendor}-out.jsonl"
        write_jsonl(inp, records)
        jobs[vendor] = run_ondemand(
            root,
            inp,
            model,
            out,
            stage=f"bank-verify-{vendor}",
            concurrency=12,
            expected_output_tokens=80,
            max_usd=budget,
        )
        budget -= jobs[vendor]["estimate_usd"]
        for record in read_jsonl(out):
            row_id, voter = record["recordId"].rsplit(":", 1)
            if row_id in items and voter == vendor:
                answer = _answer(record)
                allowed = _allowed_labels(items[row_id])
                votes[row_id][vendor] = answer if answer in allowed else None
    for row in to_judge:
        expected = EXPECTED[(row["role"], row["kind"])]
        row["votes"] = {v: votes[row["id"]].get(v) for v in judges}
        missing = [v for v, a in row["votes"].items() if a is None]
        wrong = [v for v, a in row["votes"].items() if a is not None and a != expected]
        row["kept"] = not missing and not wrong
        if missing:
            row["reject_reason"] = "judge-invalid"
        elif wrong:
            row["reject_reason"] = "judge-disagree:" + "+".join(sorted(wrong))
    held = held_out(
        [r for r in rules.values() if r["role"] == "finding-confirmation"]
    ) | held_out([r for r in rules.values() if r["role"] == "semantic-detection"])
    kept = [r for r in rows if r["kept"]]
    splits = bank_split(kept, held)
    for row in rows:
        row["split"] = splits.get(row["id"])
    write_jsonl(paths["bank"], rows)
    bank_sha = digest(paths["bank"].read_bytes())
    uri = upload(root, paths["bank"], f"bank/bank-{bank_sha[:12]}.jsonl")
    manifest = _write_manifest(
        root,
        list(rules.values()),
        rows,
        {
            "judges": judges,
            "verify_jobs": jobs,
            "bank_sha256": bank_sha,
            "bank_uri": uri,
            "lint_source": str(CANONICAL / "packages/slopvac-lint"),
            "kept_by_kind": dict(Counter(f"{r['role']}|{r['kind']}" for r in kept)),
            "kept_by_split": dict(
                Counter(f"{r['role']}|{r['kind']}|{r['split']}" for r in kept)
            ),
            "passed_lint_failed_teachers": dict(
                Counter(
                    f"{r['rule_id']}|{r['kind']}"
                    for r in lint_rows
                    if r.get("reject_reason", "").startswith("judge")
                )
            ),
        },
    )
    return {
        "candidates": len(rows),
        "kept": len(kept),
        "kept_by_kind": manifest["kept_by_kind"],
        "bank_uri": uri,
        "jobs": jobs,
    }


@lru_cache(maxsize=4)
def _guide(root: Path) -> dict:
    path = root / MANIFEST
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("rules", {})


@lru_cache(maxsize=4)
def _kept(root: Path) -> dict[str, dict[str, list[dict]]]:
    out: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in read_jsonl(root / BANK_PATH):
        if row.get("kept"):
            out[row["rule_id"]][row["kind"]].append(row)
    return out


def rule_guide(root: Path, rule_id: str) -> dict | None:
    entry = _guide(root).get(rule_id)
    if not entry:
        return None
    return {
        "id": rule_id,
        "name": entry["name"],
        "description": entry["description"],
        "fix": entry["fix"],
    }


# Prompt examples per role: (kind, count). Finding confirmation shows real
# defects, known false positives, and acceptable text the rule leaves alone.
PROMPT_MIX = {
    "finding-confirmation": (("bad", 2), ("tricky", 2), ("good", 1), ("near", 1)),
    "semantic-detection": (("bad", 3), ("good", 2), ("near", 1)),
}


def prompt_examples(root: Path, item: dict, text: str) -> list[dict]:
    """Four to six kept bank passages for the item's rule, never the item's own
    passage or one contained in its text. Train-split passages come first."""
    bank = _kept(root).get(item["rule_id"], {})
    own = (item.get("construction") or {}).get("bank_id")
    fc = item["role"] == "finding-confirmation"

    def pool(kind: str) -> list[dict]:
        rows = [
            r for r in bank.get(kind, []) if r["id"] != own and r["text"] not in text
        ]
        return sorted(
            rows,
            key=lambda r: (
                r.get("split") != "train",
                seed(f"17:prompt:{item['id']}:{r['id']}"),
            ),
        )

    pools = {kind: pool(kind) for kind, _ in PROMPT_MIX[item["role"]]}
    chosen: list[dict] = []
    for kind, count in PROMPT_MIX[item["role"]]:
        chosen += pools[kind][:count]
    # Fill from the other kinds when one kind has too few kept passages.
    spare = [
        r
        for kind, _ in PROMPT_MIX[item["role"]]
        for r in pools[kind]
        if r not in chosen
    ]
    while len(chosen) < 6 and spare:
        chosen.append(spare.pop(0))
    out = []
    for r in chosen[:6]:
        if fc and r["kind"] in ("bad", "tricky"):
            out.append(
                {
                    "text": r["text"],
                    "flagged": r["finding"]["matched_text"],
                    "answer": EXPECTED[(r["role"], r["kind"])],
                }
            )
        elif fc:
            out.append(
                {"text": r["text"], "answer": "acceptable; the rule does not fire"}
            )
        else:
            out.append({"text": r["text"], "answer": r["kind"] == "bad"})
    return out
