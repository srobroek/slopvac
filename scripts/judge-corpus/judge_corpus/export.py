"""Training exports: corpus items in the judge-pilot source format.

The SageMaker trainers and the GPU evaluation harness read the judge-pilot item
format (one JSON object per line with id, kind, state, label and question); see
scripts/judge-sagemaker/src/judge_sagemaker/convert.py. This module writes the
labelled corpus items in that format, one file per split. It adds fields for
slicing metrics: role, rule_id, rule_held_out, granularity, genre, label_origin
and provenance.

Only labelled items are exported: train holds teacher-panel labels (Dawid-Skene
posteriors, see panel.py) and constructions; dev, calibration and test hold
constructions and, once people have filled in the adjudication sheets, human
labels. State is rendered as one string, since the pilot state is plain text.
For finding confirmation, the corpus label false-positive becomes the pilot's
no-defect slot, which has the same meaning, and the instructions add the rule
guidance the review sheets show (what the rule catches, when the rule is
wrong; items.guidance_variants). For semantic detection, the state
marks the item's region [[like this]] and the instructions are the rule's
plain yes/no question (items/semantic-questions.yml) with its Yes and No
examples.

Each export is a variant under items/export/<variant>/. `min_confidence` drops
teacher-panel labels below that posterior confidence. `train_drop_origins`
leaves train rows of those label origins unlabelled, so they are not exported;
dev, calibration and test keep them. `balance="oversample"`
repeats minority-class labelled rows in train until each role's classes
are level (at most MAX_OVERSAMPLE copies of a row); for finding confirmation,
real-defect and no-defect are levelled within the teacher-panel rows, from
teacher-panel rows only. Copies get the id `<id>~<n>` and `oversample_of`.
`origin_weights` then repeats every train row of a label origin N times in
all; the copies get the id `<id>~w<n>` and `weight_of`. Constructions, which
are built 50/50, and the dev, calibration and test splits keep their
distributions.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .common import read_jsonl, write_jsonl
from .items import SPLITS, _state_of, digest, mark_span, seed

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
MAX_OVERSAMPLE = 8
# The finding-confirmation verdicts `balance="oversample"` levels within the
# teacher-panel rows.
PANEL_LEVELLED = ("real-defect", "no-defect")


def render_state(state: dict, region: dict | None = None) -> str:
    """The state as one string. A semantic item's region is marked [[like this]]."""
    text = state["text"]
    if region:
        text = mark_span(text, region["start"], region["end"])
    parts = [f"Genre: {state.get('genre', 'unknown')}"]
    if state.get("heading"):
        parts.append(f"Heading: {state['heading']}")
    if state.get("context"):
        parts.append(f"Context:\n{state['context']}")
    parts.append(f"Text:\n{text}")
    return "\n\n".join(parts)


def _choice_instructions(question: dict) -> str:
    finding = question.get("finding") or {}
    name = finding.get("rule_name") or question.get("rule_name") or question["rule_id"]
    message = finding.get("lint_message") or question.get("lint_message") or ""
    flagged = finding.get("matched_text") or question.get("matched_text") or ""
    lines = [
        (
            f"Is this lint finding valid? Rule: {name}. Message: {message}. "
            f'Flagged text: "{flagged}".'
        )
    ]
    if question.get("what_the_rule_catches"):
        lines.append(f"What the rule catches: {question['what_the_rule_catches']}")
    if question.get("when_the_rule_is_wrong"):
        lines.append(f"When the rule is wrong: {question['when_the_rule_is_wrong']}")
    return "\n".join(lines)


def _noul_instructions(question: dict) -> str:
    lines = [question["prompt"]]
    if question.get("region"):
        lines.append("The highlighted text is marked [[like this]].")
    if question.get("yes_example"):
        lines.append(f"Yes example: {question['yes_example']}")
    if question.get("no_example"):
        lines.append(f"No example: {question['no_example']}")
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
        "state": render_state(state, question.get("region")),
        "label": out_label,
        "question": out_question,
        "split": item["split"],
        "role": item["role"],
        "rule_id": item["rule_id"],
        "rule_held_out": bool(item.get("rule_held_out")),
        "granularity": item.get("granularity"),
        "genre": item.get("genre"),
        "label_origin": item.get("label_origin"),
        "label_confidence": item.get("label_confidence"),
        "provenance": "generated" if item.get("source_vendor") else "human",
    }


def _copies(pool: list[dict], wanted: int) -> list[dict]:
    """Up to `wanted` copies of `pool`'s rows in seeded order, at most
    MAX_OVERSAMPLE - 1 of any row; copy n of a row gets the id `<id>~<n>`."""
    pool = sorted(pool, key=lambda r: (seed(f"17:oversample:{r['id']}"), r["id"]))
    extra = min(wanted, len(pool) * (MAX_OVERSAMPLE - 1)) if pool else 0
    return [
        {**src, "id": f"{src['id']}~{k // len(pool) + 1}", "oversample_of": src["id"]}
        for k in range(extra)
        for src in (pool[k % len(pool)],)
    ]


def _oversample(rows: list[dict]) -> tuple[list[dict], dict]:
    """Level each role's classes in train by repeating labelled rows of the
    smaller classes; constructions count toward the totals but are never
    repeated. Finding confirmation's real-defect and no-defect are levelled
    within the teacher-panel rows instead, by repeating teacher-panel rows
    only, so the panel's two verdicts carry equal weight: constructions are
    built 50/50, and human and LLM-review labels keep their mix."""
    out = list(rows)
    weights: dict = {}
    for role in sorted({r["role"] for r in rows}):
        mine = [r for r in rows if r["role"] == role]
        panel = {
            json.dumps(label): [
                r
                for r in mine
                if r["label"] == label and r["label_origin"] == "teacher-panel"
            ]
            for label in (PANEL_LEVELLED if role == "finding-confirmation" else ())
        }
        panel_top = max((len(pool) for pool in panel.values()), default=0)
        panel_copies = {
            label: _copies(pool, panel_top - len(pool)) for label, pool in panel.items()
        }
        counts = Counter(json.dumps(r["label"]) for r in mine)
        top = max(n + len(panel_copies.get(label, [])) for label, n in counts.items())
        weights[role] = {}
        for label, n in sorted(counts.items()):
            levelled = {}
            if label in panel:
                pool, extra = panel[label], panel_copies[label]
                levelled = {
                    "levelled_within": "teacher-panel",
                    "teacher_panel_exported": len(pool) + len(extra),
                }
            else:
                pool = [
                    r
                    for r in mine
                    if json.dumps(r["label"]) == label
                    and r["label_origin"] != "construction"
                ]
                extra = _copies(pool, top - n)
            out += extra
            weights[role][label] = {
                "items": n,
                "teacher_panel_items": len(pool),
                "exported": n + len(extra),
                "weight": round((n + len(extra)) / n, 4),
                **levelled,
            }
    return out, weights


def _weight_origins(
    rows: list[dict], origin_weights: dict[str, int]
) -> tuple[list[dict], dict]:
    """Repeat each train row of a weighted label origin N times in all: N - 1
    copies with the ids `<id>~w1` ... `<id>~w<N-1>` and `weight_of`."""
    copies = [
        {**r, "id": f"{r['id']}~w{n}", "weight_of": r["id"]}
        for r in rows
        for n in range(1, origin_weights.get(r["label_origin"], 1))
    ]
    added = Counter(f"{r['role']}|{r['label_origin']}|{r['label']}" for r in copies)
    return rows + copies, dict(added)


def export_items(
    root: Path,
    *,
    variant: str = "full",
    min_confidence: float | None = None,
    balance: str = "none",
    train_drop_origins: tuple[str, ...] = (),
    origin_weights: dict[str, int] | None = None,
) -> dict:
    origin_weights = {k: v for k, v in (origin_weights or {}).items() if v != 1}
    if any(v < 1 for v in origin_weights.values()):
        raise ValueError(f"origin weights must be at least 1: {origin_weights}")
    out = root / "items/export" / variant
    out.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "variant": variant,
        "min_confidence": min_confidence,
        "balance": balance,
        "files": {},
        "counts": {},
        "dropped_below_confidence": {},
        "per_rule": defaultdict(lambda: defaultdict(Counter)),
    }
    if train_drop_origins:
        report["train_dropped_origins"] = sorted(train_drop_origins)
    if origin_weights:
        report["origin_weights"] = dict(sorted(origin_weights.items()))
    dropped_by_origin: Counter = Counter()
    for split in SPLITS:
        rows, dropped = [], Counter()
        for x in read_jsonl(root / f"items/{split}.jsonl"):
            row = export_item(root, x)
            if row is None:
                continue
            if split == "train" and row["label_origin"] in train_drop_origins:
                dropped_by_origin[
                    f"{row['role']}|{row['label_origin']}|{row['label']}"
                ] += 1
                continue
            if (
                min_confidence is not None
                and row["label_origin"] == "teacher-panel"
                and (row["label_confidence"] or 0.0) < min_confidence
            ):
                dropped[f"{row['role']}|{row['label']}"] += 1
                continue
            rows.append(row)
            report["per_rule"][row["rule_id"]][split][str(row["label"])] += 1
        if split == "train" and balance == "oversample":
            rows, report["sampling_weights"] = _oversample(rows)
        if split == "train" and origin_weights:
            rows, report["origin_weight_copies"] = _weight_origins(rows, origin_weights)
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
        report["dropped_below_confidence"][split] = dict(dropped)
    if train_drop_origins:
        report["train_dropped_by_origin"] = dict(dropped_by_origin)
    (out / "export-manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {k: v for k, v in report.items() if k != "per_rule"}


def publish_export(
    root: Path, build_id: str, variant: str, prefix: str = "review"
) -> dict:
    """Upload items/export/<variant> to s3://<corpus bucket>/exports/<build_id>/
    <variant>/ and the adjudication sheets to .../<build_id>/adjudication/, and
    record the objects in items/export-index.json (committed), one entry per
    build. Builds recorded as frozen are never written again."""
    from .bedrock import upload

    src = root / "items/export" / variant
    manifest = json.loads((src / "export-manifest.json").read_text(encoding="utf-8"))
    items_manifest = json.loads(
        (root / "items/manifest.json").read_text(encoding="utf-8")
    )
    index_path = root / "items/export-index.json"
    index = (
        json.loads(index_path.read_text(encoding="utf-8"))
        if index_path.is_file()
        else {}
    )
    if index.get("schema_version") == 1:
        # The single-build index of v2: kept as a frozen build entry.
        legacy = {k: v for k, v in index.items() if k != "schema_version"}
        index = {
            "schema_version": 2,
            "builds": {legacy["build_id"]: {**legacy, "frozen": True}},
        }
    index.setdefault("schema_version", 2)
    builds = index.setdefault("builds", {})
    if builds.get(build_id, {}).get("frozen"):
        raise RuntimeError(
            f"{build_id} is a frozen build; publish under a new build id"
        )

    def put(path: Path, name: str) -> dict:
        return {
            "path": name,
            "sha256": digest(path.read_bytes()),
            "uri": upload(root, path, f"exports/{build_id}/{name}"),
        }

    objects = [put(src / f"{s}.jsonl", f"{variant}/{s}.jsonl") for s in SPLITS] + [
        put(src / "export-manifest.json", f"{variant}/export-manifest.json")
    ]
    # Reviewer-facing sheets of this build only (label_sheets.py --prefix);
    # the build's raw *-sheet.* dumps stay local.
    sheets = sorted(
        p
        for task in ("lint-findings", "semantic")
        for p in (root / "items/adjudication").glob(f"{prefix}-{task}-*.csv")
    )
    entry = builds.setdefault(build_id, {"build_id": build_id, "variants": {}})
    entry.update(
        {
            "format": "judge-pilot source items (scripts/judge-sagemaker convert.py)",
            "item_split_digests": items_manifest.get("split_digests", {}),
            "held_out_lint_rules": items_manifest.get("held_out_lint_rules", []),
            "held_out_judgement_rules": items_manifest.get(
                "held_out_judgement_rules", []
            ),
            "adjudication": [put(p, f"adjudication/{p.name}") for p in sheets],
        }
    )
    entry["variants"][variant] = {
        "min_confidence": manifest["min_confidence"],
        "balance": manifest["balance"],
        "counts": manifest["counts"],
        "sampling_weights": manifest.get("sampling_weights"),
        "objects": objects,
    }
    if manifest.get("train_dropped_origins"):
        entry["variants"][variant]["train_dropped_origins"] = manifest[
            "train_dropped_origins"
        ]
        entry["variants"][variant]["train_dropped_by_origin"] = manifest[
            "train_dropped_by_origin"
        ]
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return entry
