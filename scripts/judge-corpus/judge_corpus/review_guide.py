"""Plain-language reviewer guidance per rule, for the review sheets.

The rule definitions carry maintainer notes (provenance, tiers, catalog
references) that a reviewer does not need. For every lint and judgement rule
this asks Sonnet 5, once, to restate only what is in the definition as two short
fields:

- `catches`: what the rule flags and why it is a problem;
- `fine_when`: when text that matches the rule is acceptable (the known
  false-positive cases), or "" if the definition names none.

The model may only restate the definition; the prompt forbids new claims. The
result, items/review-guide.json, is committed so it can be read and corrected
by hand. label_sheets.py reads it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .batch import parse_output
from .common import read_jsonl, write_jsonl
from .items import _rules_current, _rules_judgement
from .ondemand import run_ondemand
from .panel import MODELS, _panel_body

GUIDE = "items/review-guide.json"
PROMPT = """You write guidance for a person reviewing whether a prose-lint rule fired correctly.
Restate ONLY facts in the rule definition below. Do not add examples, rules, or claims that are not in it.
Leave out maintainer details: tiers, severities, catalog or file references, provenance, measurement notes.
Plain English, second person, no jargon.

Return JSON with exactly two keys:
"catches": at most 2 sentences: what the rule flags and why that is a problem for a reader.
"fine_when": at most 2 sentences: when text that matches the rule is acceptable (a false positive), taken only from the definition; "" if the definition names no such case.
Rule definition:
{definition}"""


def _definition(rule: dict) -> str:
    provenance = rule.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    fields = {
        "name": rule.get("name"),
        "message": rule.get("message"),
        "question": rule.get("judgement_question"),
        "fix": rule.get("fix"),
        "examples": rule.get("examples"),
        "note": provenance.get("note"),
    }
    return json.dumps(
        {k: v for k, v in fields.items() if v}, ensure_ascii=False, indent=1
    )


def build_guide(root: Path, max_usd: float) -> dict:
    rules = {r["id"]: r for r in [*_rules_current(), *_rules_judgement()]}
    model = MODELS["anthropic"]
    inputs = root / ".cache/review-guide/input.jsonl"
    output = root / ".cache/review-guide/output.jsonl"
    inputs.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(
        inputs,
        [
            {
                "recordId": rule_id,
                "modelInput": _panel_body(
                    model, PROMPT.format(definition=_definition(r))
                ),
            }
            for rule_id, r in sorted(rules.items())
        ],
    )
    run = run_ondemand(
        root,
        inputs,
        model,
        output,
        stage="review-guide",
        concurrency=8,
        expected_output_tokens=150,
        max_usd=max_usd,
    )
    guide, failed = {}, []
    for record in read_jsonl(output):
        text = parse_output(record) or ""
        match = re.search(r"\{.*\}", text, flags=re.S)
        try:
            value = json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            value = None
        if not isinstance(value, dict) or not isinstance(value.get("catches"), str):
            failed.append(record.get("recordId"))
            continue
        guide[record["recordId"]] = {
            "catches": value["catches"].strip(),
            "fine_when": str(value.get("fine_when") or "").strip(),
        }
    (root / GUIDE).write_text(
        json.dumps(guide, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "rules": len(rules),
        "written": len(guide),
        "failed": failed,
        "cost": run.get("estimate_usd"),
    }
