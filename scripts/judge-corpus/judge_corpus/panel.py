"""Prepare, submit, and collect three-vendor teacher-panel votes."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from botocore.exceptions import ClientError
from .bank import prompt_examples, rule_guide
from .bedrock import download_outputs, ensure_budget, now, pricing_for, submit, upload
from .batch import model_body, parse_output
from .common import read_jsonl, token_estimate, write_jsonl
from .items import _draw
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
# Output tokens per vote for spend estimates. A vote is a short JSON object;
# the re-run averaged 13 (Sonnet, Mistral) to 71 (gpt-oss, reasoning) tokens.
EXPECTED_OUTPUT_TOKENS = 80
# Construction items with known labels in the panel sample. They anchor each
# teacher's per-role confusion in the Dawid-Skene aggregation.
ANCHORS = 800


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


def _prompt(root: Path, item: dict, examples: list[dict] | None = None) -> str:
    """The panel prompt: the rule's description and, unless `examples` is
    given, four to six labelled bank passages for the rule (never the item's
    own passage), then the item's state and question."""
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
    if examples is None:
        examples = prompt_examples(
            root, item, state.get("text", "") + "\n" + (state.get("context") or "")
        )
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
    rule = rule_guide(root, item["rule_id"])
    parts = [name for name, value in (("rule", rule), ("examples", examples)) if value]
    guide = []
    if rule:
        guide.append("rule describes what the rule targets and how to fix it.")
    if examples:
        guide.append(
            "examples are other passages for the same rule, each with the answer "
            "it gets; they are reference, not the text to judge."
        )
    instruction = " ".join(
        [
            "You are labelling prose for a writing-quality checker. Use only the "
            f"supplied {', '.join(parts + ['state'])} and question.",
            target,
            *guide,
            f'Reply with only a JSON object of the form {{"answer": LABEL}}, where '
            f"LABEL is exactly {labels}. Do not explain, and do not answer questions "
            "the text itself asks.",
        ]
    )
    payload = {"rule": rule, "examples": examples, "state": state, "question": question}
    return (
        instruction
        + "\n"
        # question.finding carries offsets into state.text. The item's own
        # finding holds document offsets and a private path, so it stays out.
        + json.dumps({k: v for k, v in payload.items() if v}, ensure_ascii=False)
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
            input_tokens * prices[0] + len(records) * EXPECTED_OUTPUT_TOKENS * prices[1]
        ) / 1_000_000
        result[vendor] = {
            "model_id": model,
            "records": records,
            "input_tokens": input_tokens,
            "output_tokens": len(records) * EXPECTED_OUTPUT_TOKENS,
            "estimate_usd": estimate,
            "prices": prices,
        }
        total += estimate
    return result, total


def _anchor_sample(train: list[dict], limit: int) -> list[dict]:
    """Train constructions with known labels, the same number per role and
    per label within a role, spread over construction kinds and rules."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for x in train:
        if x.get("label_origin") == "construction" and x.get("label") is not None:
            groups[(x["role"], json.dumps(x["label"]))].append(x)
    roles = sorted({role for role, _ in groups})
    chosen: set[str] = set()
    for role in roles:
        labels = [k for k in groups if k[0] == role]
        for key in labels:
            chosen |= _draw(groups[key], limit // len(roles) // len(labels))
    return [x for x in train if x["id"] in chosen]


def prepare_panel(
    root: Path, *, max_spend: float = MAX_SPEND, anchors: int = ANCHORS
) -> dict:
    train, manifest = _train(root)
    candidates = [x for x in train if x.get("label_origin") == "teacher-panel"]
    if not candidates:
        raise ValueError("no train candidates marked for teacher-panel labels")
    anchor_items = _anchor_sample(train, anchors)
    # Bound the spend using authoritative price data before writing any panel input.
    limit = min(len(candidates), 8000)
    while limit >= 100:
        selected, strata = _sample(candidates, limit)
        models, total = _estimate(root, selected + anchor_items)
        if total <= max_spend:
            break
        limit = int(limit * max_spend / total * 0.92)
    else:
        raise RuntimeError(
            f"cannot fit at least 100 stratified items under the ${max_spend} cap"
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
        "sample_ids": [x["id"] for x in selected + anchor_items],
        "anchor_ids": [x["id"] for x in anchor_items],
        "sample_count": len(selected),
        "anchor_count": len(anchor_items),
        "anchor_labels": dict(
            Counter(f"{x['role']}|{x['label']}" for x in anchor_items)
        ),
        "candidate_count": len(candidates),
        "strata": strata,
        "max_spend_usd": max_spend,
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
    max_spend = plan.get("max_spend_usd", MAX_SPEND)
    if plan["estimated_total_usd"] > max_spend:
        raise RuntimeError(f"panel plan exceeds the ${max_spend} cap")
    jobs = {}
    for vendor, model_id in plan["model_ids"].items():
        input_path = root / plan["files"][vendor]
        records = list(read_jsonl(input_path))
        input_tokens = sum(
            token_estimate(json.dumps(r["modelInput"], ensure_ascii=False))
            for r in records
        )
        output_tokens = len(records) * EXPECTED_OUTPUT_TOKENS
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
            # Keyed by the input digest: a resumed run skips only records of
            # this plan, never votes left over from an earlier prompt.
            tag = hashlib.sha256(input_path.read_bytes()).hexdigest()[:12]
            output_path = root / "items" / f"panel-{vendor}-{tag}-ondemand.jsonl"
            run = run_ondemand(
                root,
                input_path,
                model_id,
                output_path,
                stage=f"panel-{vendor}",
                concurrency=8,
                expected_output_tokens=EXPECTED_OUTPUT_TOKENS,
                max_usd=max_spend,
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


def _vote_value(label) -> str:
    """Labels as vote strings: yes/no construction labels are booleans."""
    return ("true" if label else "false") if isinstance(label, bool) else label


def dawid_skene(
    rows: list[tuple[str, dict[str, str | None]]],
    classes: list[str],
    anchors: dict[str, str],
    vendors: list[str],
    *,
    iterations: int = 200,
    smoothing: float = 1.0,
) -> tuple[dict[str, dict[str, float]], dict, dict[str, float]]:
    """Semi-supervised Dawid-Skene. Anchor items (known labels) keep one-hot
    posteriors and so pin each teacher's confusion matrix; the class prior
    comes from the other items only, since constructions are balanced by
    design. Returns posteriors, confusion[vendor][true][vote] and the prior."""
    k = len(classes)
    post: dict[str, dict[str, float]] = {}
    for item_id, votes in rows:
        if item_id in anchors:
            post[item_id] = {c: float(c == anchors[item_id]) for c in classes}
        else:
            counts = Counter(v for v in votes.values() if v in classes)
            total = sum(counts.values())
            post[item_id] = {c: (counts[c] + 0.1) / (total + 0.1 * k) for c in classes}
    free = [(i, v) for i, v in rows if i not in anchors]
    prior = {c: 1.0 / k for c in classes}
    conf: dict = {}
    for _ in range(iterations):
        prior = {
            c: (sum(post[i][c] for i, _ in free) + smoothing)
            / (len(free) + smoothing * k)
            for c in classes
        }
        conf = {}
        for v in vendors:
            conf[v] = {}
            for t in classes:
                num = {c: smoothing for c in classes}
                for i, votes in rows:
                    vote = votes.get(v)
                    if vote in num:
                        num[vote] += post[i][t]
                total = sum(num.values())
                conf[v][t] = {c: n / total for c, n in num.items()}
        change = 0.0
        for i, votes in free:
            logp = {}
            for t in classes:
                lp = math.log(prior[t])
                for v in vendors:
                    vote = votes.get(v)
                    if vote in classes:
                        lp += math.log(conf[v][t][vote])
                logp[t] = lp
            top = max(logp.values())
            z = sum(math.exp(x - top) for x in logp.values())
            new = {t: math.exp(logp[t] - top) / z for t in classes}
            change = max(change, max(abs(new[t] - post[i][t]) for t in classes))
            post[i] = new
        if change < 1e-6:
            break
    return post, conf, prior


CONFIDENCE_BINS = [round(0.5 + 0.05 * i, 2) for i in range(11)]


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
    anchor_ids = set(plan.get("anchor_ids", []))
    vendor_names = list(MODELS)
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
        item["panel_votes"] = item_votes
        vote_rows.append(
            {
                "item_id": item_id,
                "role": item["role"],
                "rule_id": item["rule_id"],
                "genre": item["genre"],
                "granularity": item["granularity"],
                "source_family": item.get("source_family"),
                "anchor": item_id in anchor_ids,
                "known_label": _vote_value(item["label"])
                if item_id in anchor_ids
                else None,
                "votes": item_votes,
            }
        )
    report: dict = {
        "aggregation": "semi-supervised Dawid-Skene, per role, anchored on constructions",
        "sampled_items": len(vote_rows),
        "anchor_items": sum(r["anchor"] for r in vote_rows),
        "complete_three_vote_items": sum(
            all(r["votes"].get(v) is not None for v in vendor_names) for r in vote_rows
        ),
        "per_role": {},
        "per_rule": {},
    }
    for role in sorted({r["role"] for r in vote_rows}):
        group = [r for r in vote_rows if r["role"] == role]
        classes = sorted(_allowed_labels(by_id[group[0]["item_id"]]))
        anchors = {r["item_id"]: r["known_label"] for r in group if r["anchor"]}
        post, conf, prior = dawid_skene(
            [(r["item_id"], r["votes"]) for r in group], classes, anchors, vendor_names
        )
        natural = [r for r in group if not r["anchor"]]
        for r in natural:
            item = by_id[r["item_id"]]
            p = post[r["item_id"]]
            best = max(classes, key=lambda c: (p[c], c))
            voted = any(r["votes"].get(v) for v in vendor_names)
            label = best if voted else None
            if label is not None and item["question"].get("type") == "noul":
                label = label == "true"
            item["label"] = label
            item["label_confidence"] = round(p[best], 6) if voted else None
            item["label_posterior"] = {c: round(p[c], 6) for c in classes}
            item["label_origin"] = "teacher-panel" if voted else "teacher-panel-no-vote"
            r["label"] = label
            r["label_confidence"] = item["label_confidence"]
            r["posterior"] = item["label_posterior"]
            counts = Counter(x for x in r["votes"].values() if x)
            r["unanimous"] = len(counts) == 1 and sum(counts.values()) == len(
                vendor_names
            )
            r["majority"] = (
                counts.most_common(1)[0][0]
                if counts and counts.most_common(1)[0][1] >= 2
                else None
            )
        teachers = {}
        for v in vendor_names:
            scored = [r for r in group if r["anchor"] and r["votes"].get(v)]
            teachers[v] = {
                # Expected accuracy under the natural-item class prior.
                "estimated_accuracy": round(
                    sum(prior[c] * conf[v][c][c] for c in classes), 4
                ),
                "estimated_recall": {c: round(conf[v][c][c], 4) for c in classes},
                "anchor_accuracy": round(
                    sum(r["votes"][v] == r["known_label"] for r in scored)
                    / len(scored),
                    4,
                )
                if scored
                else None,
                "anchor_votes": len(scored),
            }
        confidences = [r["label_confidence"] for r in natural if r["label"] is not None]
        report["per_role"][role] = {
            "items": len(group),
            "anchors": len(anchors),
            "anchor_labels": dict(Counter(anchors.values())),
            "fleiss_kappa": _fleiss(group, vendor_names),
            "class_prior": {c: round(prior[c], 4) for c in classes},
            "teachers": teachers,
            "labels": dict(Counter(str(r["label"]) for r in natural)),
            "unanimous": sum(r["unanimous"] for r in natural),
            "agrees_with_majority": sum(
                r["majority"] is not None and _vote_value(r["label"]) == r["majority"]
                for r in natural
            ),
            "confidence_at_least": {
                str(b): sum(c >= b for c in confidences) for b in CONFIDENCE_BINS
            },
        }
    for key in sorted({r["rule_id"] for r in vote_rows}):
        group = [r for r in vote_rows if r["rule_id"] == key]
        report["per_rule"][key] = {
            "items": len(group),
            "fleiss_kappa": _fleiss(group, vendor_names),
        }
    write_jsonl(root / "items/train.jsonl", train)
    write_jsonl(root / "items/panel-votes.jsonl", vote_rows)
    (root / "items/panel-agreement.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
