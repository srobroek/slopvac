"""Prepare, submit, and collect three-vendor teacher-panel votes."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from botocore.exceptions import ClientError
from .bedrock import download_outputs, ensure_budget, now, pricing_for, submit, upload
from .batch import model_body, parse_output
from .common import read_jsonl, token_estimate, write_jsonl
from .ondemand import run_ondemand

MODELS = {
    "anthropic": "us.anthropic.claude-sonnet-5",
    "openai": "openai.gpt-oss-120b-1:0",
    "mistral": "mistral.mistral-large-3-675b-instruct",
}
# A panel model never labels a document it generated. Its vote on those items
# goes to this substitute instead.
SUBSTITUTE = ("deepseek", "deepseek.v3.2")
# Substrings of a generated document id that identify each panel model.
SELF_MARKERS = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-oss-120b",
    "mistral": "mistral-large-3",
}


def provenance(item: dict) -> str:
    return "generated" if item.get("source_vendor") else "human"


def _self_labelled(vendor: str, item: dict) -> bool:
    return SELF_MARKERS[vendor] in str(item.get("source_id", ""))


MAX_SPEND = 60.0
OUTPUT_TOKENS = 400


def _panel_body(model: str, prompt: str) -> dict:
    """A vote needs a label, not a reasoning trace. Sonnet 5's default adaptive
    thinking and gpt-oss's default reasoning spent the whole output budget in
    the first panel pass and returned no answer, so both are turned down."""
    body = model_body(model, prompt, max_tokens=OUTPUT_TOKENS)
    if "anthropic.claude-sonnet-5" in model:
        body["thinking"] = {"type": "disabled"}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"
    return body


def _train(root: Path) -> tuple[list[dict], dict]:
    manifest = json.loads((root / "items/manifest.json").read_text(encoding="utf-8"))
    rows = list(read_jsonl(root / "items/train.jsonl"))
    if not rows:
        raise ValueError("train item manifest is empty")
    return rows, manifest


def _prompt(root: Path, item: dict) -> str:
    state = item.get("state")
    if state is None and item.get("state_path"):
        state = json.loads((root / item["state_path"]).read_text(encoding="utf-8"))
    if state is None:
        text = (root / item["text_path"]).read_text(encoding="utf-8")
        state = {
            "text": text,
            "context": item.get("context", ""),
            "genre": item["genre"],
            "granularity": item["granularity"],
        }
    question = item["question"]
    if question.get("type") == "choice":
        labels = " or ".join(f'"{k}"' for k in question["options"])
        target = (
            "Judge the lint finding in question.finding: the flagged text is "
            "state.text[finding.start:finding.end]. Pick the option that fits."
        )
    else:
        labels = '"true" or "false"'
        target = (
            'Answer question.prompt about state.text: "true" means the text '
            'has the defect, "false" means it does not. question.criteria '
            "gives bad and good examples of the defect."
        )
    instruction = (
        "You are labelling prose for a writing-quality checker. Use only the "
        f"supplied state and question. {target} Reply with only a JSON object "
        f'of the form {{"answer": LABEL}}, where LABEL is exactly {labels}. '
        "Do not explain, and do not answer questions the text itself asks."
    )
    return (
        instruction
        + "\n"
        # question.finding carries offsets into state.text. The item's own
        # finding holds document offsets and a private path, so it stays out.
        + json.dumps({"state": state, "question": question}, ensure_ascii=False)
    )


def _sample(items: list[dict], limit: int) -> tuple[list[dict], dict]:
    strata: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for item in items:
        strata[
            (
                item["role"],
                item["rule_id"],
                item["genre"],
                item["granularity"],
                provenance(item),
            )
        ].append(item)
    selected = []
    # Round-robin through deterministic stratum order; this preserves rare-rule coverage.
    queues = []
    for key, rows in sorted(strata.items()):
        rows.sort(key=lambda x: (x["id"],))
        queues.append((key, rows))
    while len(selected) < limit and any(rows for _, rows in queues):
        for _, rows in queues:
            if rows and len(selected) < limit:
                selected.append(rows.pop(0))
    return selected, {
        "strata": len(strata),
        "candidate_count": len(items),
        "sample_count": len(selected),
        "sampled_strata": len(
            {
                (
                    x["role"],
                    x["rule_id"],
                    x["genre"],
                    x["granularity"],
                    provenance(x),
                )
                for x in selected
            }
        ),
    }


def _estimate(root: Path, items: list[dict]) -> tuple[dict, float]:
    result = {}
    total = 0.0
    plan = {
        vendor: (model, [x for x in items if not _self_labelled(vendor, x)])
        for vendor, model in MODELS.items()
    }
    swapped = [
        (vendor, x) for vendor in MODELS for x in items if _self_labelled(vendor, x)
    ]
    if swapped:
        plan[SUBSTITUTE[0]] = (SUBSTITUTE[1], [x for _, x in swapped])
    for vendor, (model, vendor_items) in plan.items():
        prices = pricing_for(model)
        if prices is None:
            raise ValueError(f"no verified Bedrock price for {model}")
        records = []
        input_tokens = 0
        for item in vendor_items:
            prompt = _prompt(root, item)
            body = _panel_body(model, prompt)
            input_tokens += token_estimate(json.dumps(body, ensure_ascii=False))
            voter = (
                next((v for v, x in swapped if x is item), vendor)
                if vendor == SUBSTITUTE[0]
                else vendor
            )
            records.append({"recordId": f"{item['id']}:{voter}", "modelInput": body})
        estimate = (
            input_tokens * prices[0] + len(records) * OUTPUT_TOKENS * prices[1]
        ) / 1_000_000
        result[vendor] = {
            "model_id": model,
            "records": records,
            "input_tokens": input_tokens,
            "output_tokens": len(records) * OUTPUT_TOKENS,
            "estimate_usd": estimate,
            "prices": prices,
        }
        total += estimate
    return result, total


def prepare_panel(root: Path) -> dict:
    train, manifest = _train(root)
    candidates = [x for x in train if x.get("label_origin") == "teacher-panel"]
    if not candidates:
        raise ValueError("no train candidates marked for teacher-panel labels")
    # Bound to $60 using authoritative price data before writing any panel input.
    limit = min(len(candidates), 8000)
    while limit >= 100:
        selected, strata = _sample(candidates, limit)
        models, total = _estimate(root, selected)
        if total <= MAX_SPEND:
            break
        limit = int(limit * MAX_SPEND / total * 0.92)
    else:
        raise RuntimeError(
            "cannot fit at least 100 stratified items under the $60 panel cap"
        )
    files = {}
    for vendor, model in models.items():
        path = root / "items" / "panel-input" / f"{vendor}.jsonl"
        write_jsonl(path, model["records"])
        files[vendor] = str(path.relative_to(root))
    plan = {
        "schema_version": 1,
        "created_at": now(),
        "model_ids": {v: m["model_id"] for v, m in models.items()},
        "files": files,
        "sample_ids": [x["id"] for x in selected],
        "sample_count": len(selected),
        "candidate_count": len(candidates),
        "strata": strata,
        "estimated_total_usd": round(total, 6),
        "estimated_by_model": {
            k: round(v["estimate_usd"], 6) for k, v in models.items()
        },
        "item_manifest_digests": manifest.get("split_digests", {}),
        "sampling_fields": ["role", "rule_id", "genre", "granularity", "provenance"],
        "provenance_counts": dict(Counter(provenance(x) for x in selected)),
        "self_labelled_votes_substituted": {
            vendor: sum(_self_labelled(vendor, x) for x in selected)
            for vendor in MODELS
        },
        "substitute_model": SUBSTITUTE[1],
    }
    (root / "items/panel-plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {k: v for k, v in plan.items() if k != "sample_ids"}


def submit_panel(root: Path, *, on_demand: bool = False) -> dict:
    path = root / "items/panel-plan.json"
    if not path.is_file():
        prepare_panel(root)
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan["estimated_total_usd"] > MAX_SPEND:
        raise RuntimeError("panel plan exceeds the $60 cap")
    jobs = {}
    for vendor, model_id in plan["model_ids"].items():
        input_path = root / plan["files"][vendor]
        records = list(read_jsonl(input_path))
        input_tokens = sum(
            token_estimate(json.dumps(r["modelInput"], ensure_ascii=False))
            for r in records
        )
        output_tokens = len(records) * OUTPUT_TOKENS
        price = pricing_for(model_id)
        if price is None:
            raise ValueError(f"no verified price for {model_id}")
        estimate = (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000
        ensure_budget(root, estimate)
        uri = upload(root, input_path, f"inputs/panel/{vendor}.jsonl")
        try:
            if on_demand or len(records) < 100:
                # Bedrock batch needs at least 100 records; smaller sets, and
                # runs that cannot wait hours in the batch queue, go on demand.
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ValidationException",
                            "Message": "batch inference is not supported below 100 records",
                        }
                    },
                    "CreateModelInvocationJob",
                )
            jobs[vendor] = {
                "mode": "batch",
                **submit(
                    root,
                    stage=f"panel-{vendor}",
                    model_id=model_id,
                    input_s3_uri=uri,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    output_key=f"outputs/panel/{vendor}/",
                ),
            }
        except ClientError as exc:
            if "batch inference is not supported" not in str(exc).lower():
                raise
            output_path = root / "items" / f"panel-{vendor}-ondemand.jsonl"
            run = run_ondemand(
                root,
                input_path,
                model_id,
                output_path,
                stage=f"panel-{vendor}",
                concurrency=8,
                expected_output_tokens=OUTPUT_TOKENS,
            )
            jobs[vendor] = {
                "mode": "on-demand",
                "output_path": str(output_path.relative_to(root)),
                **run,
            }
    plan["jobs"] = jobs
    plan["submitted_at"] = now()
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return jobs


_ANSWER_RE = re.compile(
    r'"answer"\s*:\s*("(?:[^"\\]|\\.)*"|true|false|-?\d+(?:\.\d+)?)', re.I
)
_YES_NO = {"yes": "true", "no": "false"}


def _answer(record: dict) -> str | None:
    """The panel model's answer, or None. Models wrap the requested JSON
    differently (a ```json fence, a <reasoning> block before it, a sentence
    around it); take the last object with an "answer" key. Only a string or
    boolean answer counts: nested shapes such as {"answer": {"options": "x"}}
    and cut-off output are no vote. yes/no become true/false; collect_panel
    then rejects any label outside the item's answer space."""
    if record.get("error"):
        return None
    text = parse_output(record) or ""
    text = re.sub(r"<reasoning>.*?</reasoning>", " ", text, flags=re.S)
    answer = None
    for block in reversed(re.findall(r"\{.*\}", text, flags=re.S)):
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "answer" in value:
            answer = value["answer"]
            break
    if answer is None:
        matches = _ANSWER_RE.findall(text)
        if not matches:
            return None
        raw = matches[-1]
        try:
            answer = json.loads(raw, strict=False) if raw.startswith('"') else raw
        except json.JSONDecodeError:
            return None
    if isinstance(answer, bool):
        answer = "true" if answer else "false"
    if not isinstance(answer, str):
        return None
    label = answer.strip().lower()
    return _YES_NO.get(label, label) or None


def _fleiss(rows: list[dict], vendors: list[str]) -> float | None:
    usable = [[r["votes"].get(v) for v in vendors] for r in rows]
    usable = [v for v in usable if all(x is not None for x in v)]
    if not usable:
        return None
    n = len(vendors)
    labels = {x for row in usable for x in row}
    p_i = [sum(Counter(row)[label] ** 2 for label in labels) - n for row in usable]
    p_i = [x / (n * (n - 1)) for x in p_i]
    p_bar = sum(p_i) / len(p_i)
    totals = Counter(x for row in usable for x in row)
    p_e = sum((v / (len(usable) * n)) ** 2 for v in totals.values())
    return (p_bar - p_e) / (1 - p_e) if p_e < 1 else 1.0


def _allowed_labels(item: dict) -> set[str]:
    q = item.get("question") or {}
    if q.get("type") == "choice":
        return set(q.get("options") or {})
    if q.get("type") == "noul":
        return {"true", "false"}
    return set()


def collect_panel(root: Path, prefixes: dict[str, str] | None = None) -> dict:
    plan_path = root / "items/panel-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    votes: dict[str, dict[str, str | None]] = defaultdict(dict)
    sample_ids = set(plan["sample_ids"])
    for vendor in plan["model_ids"]:
        if prefixes and vendor in prefixes:
            raw_path = root / "items" / f"panel-{vendor}-raw.jsonl"
            records = download_outputs(root, prefixes[vendor], raw_path)
        elif plan.get("jobs", {}).get(vendor, {}).get("mode") == "on-demand":
            records = list(read_jsonl(root / plan["jobs"][vendor]["output_path"]))
        else:
            raise ValueError(f"supply --prefix {vendor}=S3_PREFIX for this batch job")
        for record in records:
            record_id = record.get("recordId", "")
            if ":" not in record_id:
                continue
            item_id, record_vendor = record_id.rsplit(":", 1)
            # Substitute records carry the voter they stand in for.
            if item_id in sample_ids and (
                record_vendor == vendor or vendor == SUBSTITUTE[0]
            ):
                votes[item_id][record_vendor] = _answer(record)
    train = list(read_jsonl(root / "items/train.jsonl"))
    by_id = {x["id"]: x for x in train}
    vote_rows = []
    for item_id in sorted(sample_ids):
        if item_id not in by_id:
            continue
        item = by_id[item_id]
        allowed = _allowed_labels(item)
        # A vote outside the question's answer space (or unparseable, or cut off)
        # counts as no vote. It never becomes a label.
        item_votes = {
            v: (a if a in allowed else None) for v, a in votes.get(item_id, {}).items()
        }
        counts = Counter(x for x in item_votes.values() if x)
        label = (
            counts.most_common(1)[0][0]
            if counts and counts.most_common(1)[0][1] >= 2
            else None
        )
        item["panel_votes"] = item_votes
        # Construction labels for yes/no questions are JSON booleans; panel
        # labels match them.
        if label is not None and item["question"].get("type") == "noul":
            label = label == "true"
        item["label"] = label
        item["label_origin"] = (
            "teacher-panel" if label is not None else "teacher-panel-disagreement"
        )
        vote_rows.append(
            {
                "item_id": item_id,
                "role": item["role"],
                "rule_id": item["rule_id"],
                "genre": item["genre"],
                "granularity": item["granularity"],
                "source_family": item.get("source_family"),
                "votes": item_votes,
                "label": label,
            }
        )
    write_jsonl(root / "items/train.jsonl", train)
    write_jsonl(root / "items/panel-votes.jsonl", vote_rows)
    vendor_names = list(MODELS)
    valid = [
        r for r in vote_rows if all(r["votes"].get(v) is not None for v in vendor_names)
    ]
    report = {
        "sampled_items": len(vote_rows),
        "complete_three_vote_items": len(valid),
        "fleiss_kappa": _fleiss(valid, vendor_names),
        "per_role": {},
        "per_rule": {},
    }
    for key in sorted({r["role"] for r in vote_rows}):
        group = [r for r in vote_rows if r["role"] == key]
        report["per_role"][key] = {
            "items": len(group),
            "fleiss_kappa": _fleiss(group, vendor_names),
        }
    for key in sorted({r["rule_id"] for r in vote_rows}):
        group = [r for r in vote_rows if r["rule_id"] == key]
        report["per_rule"][key] = {
            "items": len(group),
            "fleiss_kappa": _fleiss(group, vendor_names),
        }
    (root / "items/panel-agreement.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
