"""Training exports: corpus items in the judge-pilot source format.

The SageMaker trainers and the GPU evaluation harness read the judge-pilot item
format (one JSON object per line with id, kind, state, label and question); see
scripts/judge-sagemaker/src/judge_sagemaker/convert.py. This module writes the
labelled corpus items in that format, one file per split. It adds fields for
slicing metrics: role, rule_id, rule_held_out, granularity, genre, label_origin
and provenance.

Only labelled items are exported: train holds teacher-panel majority labels and
constructions; dev, calibration and test hold constructions and, once people
have filled in the adjudication sheets, human labels. State is rendered as one
string, since the pilot state is plain text. For finding confirmation, the
corpus label false-positive becomes the pilot's no-defect slot, which has the
same meaning.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .common import read_jsonl, write_jsonl
from .items import SPLITS, _state_of, digest

CHOICE_LABELS = {
    "real-defect": "real-defect",
    "false-positive": "no-defect",
    "insufficient-context": "insufficient-context",
}
CHOICE_CRITERIA = {
    "real-defect": "The flagged text is a real prose defect under this lint rule.",
    "no-defect": "The rule fired on acceptable prose.",
    "insufficient-context": "The text and context do not decide the finding.",
}
MAX_EXAMPLES = 2


def render_state(state: dict) -> str:
    parts = [f"Genre: {state.get('genre', 'unknown')}"]
    if state.get("heading"):
        parts.append(f"Heading: {state['heading']}")
    if state.get("context"):
        parts.append(f"Context:\n{state['context']}")
    parts.append(f"Text:\n{state['text']}")
    return "\n\n".join(parts)


def _choice_instructions(question: dict) -> str:
    finding = question.get("finding") or {}
    name = finding.get("rule_name") or question.get("rule_name") or question["rule_id"]
    message = finding.get("lint_message") or question.get("lint_message") or ""
    flagged = finding.get("matched_text") or question.get("matched_text") or ""
    return (
        f"Is this lint finding valid? Rule: {name}. Message: {message}. "
        f'Flagged text: "{flagged}".'
    )


def _noul_instructions(question: dict) -> str:
    lines = [question["prompt"]]
    for example in (question.get("criteria") or [])[:MAX_EXAMPLES]:
        if example.get("bad"):
            lines.append(f"Defect example: {example['bad']}")
        if example.get("good"):
            lines.append(f"Acceptable example: {example['good']}")
    return "\n".join(lines)


def export_item(root: Path, item: dict) -> dict | None:
    label = item.get("label")
    if label is None:
        return None
    question = item["question"]
    state = _state_of(root, item)
    if state is None:
        raise ValueError(f"{item['id']}: no state")
    if question["type"] == "choice":
        if label not in CHOICE_LABELS:
            raise ValueError(f"{item['id']}: choice label {label!r}")
        kind, out_label = "choice", CHOICE_LABELS[label]
        out_question = {
            "type": "choice",
            "instructions": _choice_instructions(question),
            "criteria": dict(CHOICE_CRITERIA),
        }
    elif question["type"] == "noul":
        if not isinstance(label, bool):
            raise ValueError(f"{item['id']}: yes/no label {label!r} is not a boolean")
        kind, out_label = "noul", label
        out_question = {"type": "noul", "instructions": _noul_instructions(question)}
    else:
        raise ValueError(f"{item['id']}: question type {question['type']!r}")
    return {
        "id": item["id"],
        "kind": kind,
        "state": render_state(state),
        "label": out_label,
        "question": out_question,
        "split": item["split"],
        "role": item["role"],
        "rule_id": item["rule_id"],
        "rule_held_out": bool(item.get("rule_held_out")),
        "granularity": item.get("granularity"),
        "genre": item.get("genre"),
        "label_origin": item.get("label_origin"),
        "provenance": "generated" if item.get("source_vendor") else "human",
    }


def export_items(root: Path) -> dict:
    out = root / "items/export"
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {"files": {}, "counts": {}}
    for split in SPLITS:
        rows = [
            row
            for row in (
                export_item(root, x) for x in read_jsonl(root / f"items/{split}.jsonl")
            )
            if row is not None
        ]
        path = out / f"{split}.jsonl"
        write_jsonl(path, rows)
        report["files"][split] = {
            "path": str(path.relative_to(root)),
            "records": len(rows),
            "sha256": digest(path.read_bytes()),
        }
        report["counts"][split] = dict(
            Counter(f"{r['role']}|{r['label_origin']}|{r['label']}" for r in rows)
        )
    (out / "export-manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def publish_export(root: Path, build_id: str) -> dict:
    """Upload items/export and the adjudication sheets to
    s3://<corpus bucket>/exports/<build_id>/ and record the objects in
    items/export-index.json, which is committed."""
    from .bedrock import upload

    src = root / "items/export"
    manifest = json.loads((src / "export-manifest.json").read_text(encoding="utf-8"))
    items_manifest = json.loads(
        (root / "items/manifest.json").read_text(encoding="utf-8")
    )
    objects = []
    files = [src / f"{s}.jsonl" for s in SPLITS] + [src / "export-manifest.json"]
    files += sorted((root / "items/adjudication").glob("*-sheet.*"))
    for path in files:
        name = str(path.relative_to(src if path.parent == src else root / "items"))
        objects.append(
            {
                "path": name,
                "sha256": digest(path.read_bytes()),
                "uri": upload(root, path, f"exports/{build_id}/{name}"),
            }
        )
    index = {
        "schema_version": 1,
        "build_id": build_id,
        "format": "judge-pilot source items (scripts/judge-sagemaker convert.py)",
        "item_split_digests": items_manifest.get("split_digests", {}),
        "held_out_lint_rules": items_manifest.get("held_out_lint_rules", []),
        "held_out_judgement_rules": items_manifest.get("held_out_judgement_rules", []),
        "counts": manifest["counts"],
        "objects": objects,
    }
    (root / "items/export-index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return index
