"""Plain yes/no questions for the semantic-detection rules.

A judgement rule's own question (`judgement_question`) is long, often asks
several things at once, and reads as instructions for a maintainer. Every
semantic-detection item instead shows a passage with one region marked
[[like this]] and asks one question about it. This module asks Opus 5.5, once
per rule, to restate the rule as:

- `question`: one plain yes/no question about the highlighted text, at most
  about 25 words, where yes means the highlighted text has the defect;
- `yes_example`: one line of new text that has the defect;
- `no_example`: one line of new text that does not.

The drafts go to items/semantic-questions.yml (committed). They are checked by
hand against each rule's original question and examples and corrected there;
`draft_questions` only drafts rules the file does not have yet, so a re-run
keeps the corrections. items.question_for reads the file, so the training
exports, the teacher panel and the review sheets all ask the same question.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .batch import parse_output
from .common import read_jsonl, write_jsonl
from .items import QUESTIONS_PATH, semantic_questions, semantic_rules
from .llm_review import MODELS, _body
from .ondemand import run_ondemand

HEADER = """\
# One plain yes/no question per semantic-detection rule, about the text an item
# highlights [[like this]]. Yes means the highlighted text has the defect.
# Drafted by Opus 5.5 (judge-corpus items draft-questions), then checked by hand
# against each rule's original question and examples. Edit here; a re-draft
# only adds rules that are missing.
"""
PROMPT = """You are rewriting the review question of one prose-quality rule.

Reviewers, and a small classifier, see a passage of software documentation with one part highlighted [[like this]]. The highlighted part is a sentence, a few sentences, a paragraph, or a short section. They answer one yes/no question about the highlighted text.

Write three fields:
- "question": one plain yes/no question about the highlighted text, at most 25 words. "Yes" must mean the highlighted text has the defect this rule targets, and "no" that it does not. Keep the rule's meaning: the same defect and, if there is room, its most important exception. Mention the rest of the passage only when the rule needs it, for example the heading above the text. Use plain words: no jargon, no rule names or codes, no lists of options, no instructions to the reader.
- "yes_example": one line (one or two sentences) of new text that has the defect, so the answer is yes.
- "no_example": one line of new text without the defect, so the answer is no. Prefer a near miss, such as a case the rule's exceptions protect.
Do not copy or paraphrase the rule's own examples: write new text on another topic, in the register of software documentation.

Reply with only a JSON object with exactly the keys "question", "yes_example" and "no_example".

Rule definition:
{definition}"""
MODEL = MODELS["opus"]


def _definition(rule: dict) -> str:
    provenance = rule.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    fields = {
        "name": rule.get("name"),
        "scope": rule.get("scope"),
        "message": rule.get("message"),
        "question": rule.get("judgement_question"),
        "not_defects": rule.get("judgement_exceptions"),
        "fix": rule.get("fix"),
        "examples": rule.get("examples"),
        "note": provenance.get("note"),
    }
    return json.dumps(
        {k: v for k, v in fields.items() if v}, ensure_ascii=False, indent=1
    )


def _parse(record: dict) -> dict[str, str] | None:
    text = parse_output(record) or ""
    for block in reversed(re.findall(r"\{.*?\}", text, flags=re.S)):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        keys = ("question", "yes_example", "no_example")
        if isinstance(value, dict) and all(isinstance(value.get(k), str) for k in keys):
            return {k: " ".join(value[k].split()) for k in keys}
    return None


def write_questions(questions: dict[str, dict[str, str]]) -> None:
    body = yaml.safe_dump(
        dict(sorted(questions.items())),
        sort_keys=False,
        allow_unicode=True,
        width=1000,
    )
    QUESTIONS_PATH.write_text(HEADER + body, encoding="utf-8")
    semantic_questions.cache_clear()


def draft_questions(root: Path, max_usd: float) -> dict:
    rules, _ = semantic_rules()
    known = dict(semantic_questions())
    todo = {r["id"]: r for r in rules if r["id"] not in known}
    work = root / ".cache/semantic-questions"
    inputs, output = work / "input.jsonl", work / "output.jsonl"
    work.mkdir(parents=True, exist_ok=True)
    write_jsonl(
        inputs,
        [
            {
                "recordId": rule_id,
                "modelInput": _body(MODEL, PROMPT.format(definition=_definition(r))),
            }
            for rule_id, r in sorted(todo.items())
        ],
    )
    run = run_ondemand(
        root,
        inputs,
        MODEL,
        output,
        stage="semantic-questions",
        concurrency=8,
        expected_output_tokens=2000,
        max_usd=max_usd,
    )
    drafted, failed = {}, []
    for record in read_jsonl(output):
        rule_id = record.get("recordId")
        if rule_id not in todo:
            continue
        value = _parse(record)
        if value is None:
            failed.append(rule_id)
        else:
            drafted[rule_id] = value
    write_questions({**known, **drafted})
    return {
        "rules": len(rules),
        "kept": len(known),
        "drafted": len(drafted),
        "failed": failed,
        "cost": run.get("estimate_usd"),
    }
