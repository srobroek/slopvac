"""Prepare, submit, and collect three-vendor teacher-panel votes."""

from __future__ import annotations

import json
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
MAX_SPEND = 60.0
OUTPUT_TOKENS = 180


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
    instruction = "Answer the typed question from the supplied text and criteria only. Return JSON with one key, answer. Do not quote or rewrite the text."
    return (
        instruction
        + "\n"
        + json.dumps(
            {
                "state": state,
                "question": item["question"],
                "finding": item.get("finding"),
            },
            ensure_ascii=False,
        )
    )


def _sample(items: list[dict], limit: int) -> tuple[list[dict], dict]:
    strata: dict[tuple[str, ...], list[dict]] = defaultdict(list)
    for item in items:
        provenance = str(item.get("source_family") or "unknown")
        strata[
            (
                item["role"],
                item["rule_id"],
                item["genre"],
                item["granularity"],
                provenance,
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
                    x.get("source_family") or "unknown",
                )
                for x in selected
            }
        ),
    }


def _estimate(root: Path, items: list[dict]) -> tuple[dict, float]:
    result = {}
    total = 0.0
    for vendor, model in MODELS.items():
        prices = pricing_for(model)
        if prices is None:
            raise ValueError(f"no verified Bedrock price for {model}")
        records = []
        input_tokens = 0
        for item in items:
            prompt = _prompt(root, item)
            body = model_body(model, prompt, max_tokens=OUTPUT_TOKENS)
            input_tokens += token_estimate(json.dumps(body, ensure_ascii=False))
            records.append({"recordId": f"{item['id']}:{vendor}", "modelInput": body})
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
        "model_ids": MODELS,
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
        "sampling_fields": ["role", "rule_id", "genre", "granularity", "source_family"],
        "excluded_self_labelled_votes": [],
    }
    (root / "items/panel-plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {k: v for k, v in plan.items() if k != "sample_ids"}


def submit_panel(root: Path) -> dict:
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
        if len(records) < 100:
            raise ValueError(f"{vendor} batch has fewer than 100 records")
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
                concurrency=4,
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


def _answer(record: dict) -> str | None:
    if record.get("error"):
        return None
    text = parse_output(record)
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None
    answer = value.get("answer") if isinstance(value, dict) else None
    if isinstance(answer, dict):
        answer = answer.get("label") or answer.get("value")
    return str(answer).strip().lower() if answer is not None else None


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
            if item_id in sample_ids and record_vendor == vendor:
                votes[item_id][vendor] = _answer(record)
    train = list(read_jsonl(root / "items/train.jsonl"))
    by_id = {x["id"]: x for x in train}
    vote_rows = []
    for item_id in sorted(sample_ids):
        if item_id not in by_id:
            continue
        item = by_id[item_id]
        item_votes = votes.get(item_id, {})
        counts = Counter(x for x in item_votes.values() if x)
        label = (
            counts.most_common(1)[0][0]
            if counts and counts.most_common(1)[0][1] >= 2
            else None
        )
        item["panel_votes"] = item_votes
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
    vendor_names = list(plan["model_ids"])
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
