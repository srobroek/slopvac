"""Prepare model-specific JSONL, parse outputs, and enforce leak checks."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from .common import (
    leak_scores,
    normalise,
    read_jsonl,
    sha256_text,
    token_estimate,
    write_jsonl,
)


STAGE1_MODEL_HINT = "amazon.nova-lite-v1:0"
BRIEF_SYSTEM = """You create a provenance-safe abstract brief. The source is private evidence, not output text. Never quote it, reproduce its headings, or retain distinctive names. Return JSON only with keys genre, audience, purpose, requirements (array), outline (array of abstract section purposes), target_length_words, and generic_entities (array)."""


def _source_text(root: Path, row: dict) -> str:
    path = root / row["cache_path"]
    if not path.exists():
        raise FileNotFoundError(f"missing cached source text: {path}")
    return path.read_text(encoding="utf-8")


def brief_prompt(row: dict, text: str) -> str:
    return f"""{BRIEF_SYSTEM}\n\nGenre: {row["genre"]}\nSource document follows between private delimiters.\n<private-source>\n{text}\n</private-source>\n\nDescribe the document abstractly without any source quotation."""


def generation_prompt(brief: dict) -> str:
    payload = json.dumps(
        {
            k: brief[k]
            for k in (
                "genre",
                "audience",
                "purpose",
                "requirements",
                "outline",
                "target_length_words",
                "generic_entities",
            )
            if k in brief
        },
        ensure_ascii=False,
    )
    return f"""Write a complete {brief.get("genre", "document")} for the stated audience using only this abstract brief. Do not mention the brief, source, provenance, or authorship. Do not add citations or invented product-specific facts. Follow the outline and requirements. Return document text only.\n\nABSTRACT BRIEF:\n{payload}"""


def model_body(model_id: str, prompt: str, *, max_tokens: int = 1000) -> dict:
    model = model_id.rsplit("/", 1)[-1]
    if model.startswith("anthropic."):
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ],
        }
    if model.startswith("amazon.nova"):
        return {
            "schemaVersion": "messages-v1",
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.2},
        }
    if model.startswith("google."):
        return {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        }
    if model.startswith("meta."):
        return {"prompt": prompt, "max_gen_len": max_tokens, "temperature": 0.2}
    if model.startswith("mistral."):
        return {"prompt": prompt, "max_tokens": max_tokens, "temperature": 0.2}
    return {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }


def prepare_briefs(
    root: Path, *, limit: int | None, model_id: str = STAGE1_MODEL_HINT
) -> tuple[Path, int, int]:
    rows = list(read_jsonl(root / "sources" / "human.jsonl"))
    if limit:
        rows = rows[:limit]
    out = root / "briefs" / "input.jsonl"
    entries = []
    input_tokens = 0
    for row in rows:
        text = _source_text(root, row)
        prompt = brief_prompt(row, text)
        input_tokens += token_estimate(prompt)
        entries.append(
            {
                "recordId": row["id"],
                "modelInput": model_body(model_id, prompt, max_tokens=800),
            }
        )
    write_jsonl(out, entries)
    return out, input_tokens, len(entries) * 800


def _deep_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := _deep_text(item)))
    if isinstance(value, dict):
        for key in (
            "outputText",
            "generation",
            "text",
            "content",
            "completion",
            "answer",
        ):
            if key in value:
                result = _deep_text(value[key])
                if result:
                    return result
        for child in value.values():
            result = _deep_text(child)
            if result:
                return result
    return ""


def parse_output(line: dict) -> str:
    if line.get("error"):
        return ""
    value = line.get("modelOutput", line.get("output", line))
    return normalise(_deep_text(value))


def parse_json_object(text: str) -> dict | None:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def collect_briefs(
    root: Path, output_lines: Iterable[dict], *, model_id: str
) -> tuple[list[dict], list[dict]]:
    source_map = {
        row["id"]: row for row in read_jsonl(root / "sources" / "human.jsonl")
    }
    accepted, rejected = [], []
    for line in output_lines:
        source_id = line.get("recordId") or line.get("source_id")
        source = source_map.get(source_id)
        raw = parse_output(line)
        brief = parse_json_object(raw)
        reason = None
        overlap = (0.0, 0.0)
        if not source:
            reason = "unknown_source_id"
        elif not brief:
            reason = "invalid_json"
        else:
            overlap = leak_scores(_source_text(root, source), raw)
            if overlap[0] > 0.0 or overlap[1] >= 0.6:
                reason = "brief_source_overlap"
            required = {
                "genre",
                "audience",
                "purpose",
                "requirements",
                "outline",
                "target_length_words",
                "generic_entities",
            }
            if not required.issubset(brief):
                reason = "missing_brief_keys"
        if reason:
            rejected.append(
                {
                    "source_id": source_id,
                    "model": model_id,
                    "reason": reason,
                    "overlap_8gram": overlap[0],
                    "overlap_sentence": overlap[1],
                    "raw_digest": sha256_text(raw),
                }
            )
        else:
            accepted.append(
                {
                    "id": f"brief-{source_id}",
                    "source_id": source_id,
                    "model": model_id,
                    "brief": brief,
                    "digest": sha256_text(
                        json.dumps(brief, sort_keys=True, ensure_ascii=False)
                    ),
                    "overlap_score": overlap[0],
                }
            )
    write_jsonl(root / "briefs" / "manifest.jsonl", accepted)
    write_jsonl(root / "briefs" / "rejections.jsonl", rejected)
    return accepted, rejected


def prepare_generation(
    root: Path, *, limit: int | None
) -> dict[str, tuple[Path, int, int]]:
    briefs = list(read_jsonl(root / "briefs" / "manifest.jsonl"))
    if limit:
        briefs = briefs[:limit]
    roster = json.loads((root / "models" / "roster.json").read_text())
    models = [
        m
        for m in roster["models"]
        if m.get("batch_supported") and m.get("pricing_usd_per_million_on_demand")
    ]
    if len(models) < 2:
        raise RuntimeError("at least two priced batch-capable models are required")
    assignments = []
    by_model: dict[str, list[dict]] = {m["model_id"]: [] for m in models}
    # Two disjoint rotations make vendor/tier coverage deterministic. The same
    # model receives at most ceil(2/n) of rows, below 12% for n >= 17.
    for index, brief in enumerate(briefs):
        for offset in (0, 1):
            model = models[(index * 2 + offset) % len(models)]
            record_id = (
                f"gen-{brief['source_id']}-{model['model_id'].replace(':', '_')}"
            )
            batch_item = {
                "recordId": record_id,
                "modelInput": model_body(
                    model["model_id"],
                    generation_prompt(brief["brief"]),
                    max_tokens=1200,
                ),
            }
            by_model[model["model_id"]].append(batch_item)
            assignments.append(
                {
                    "recordId": record_id,
                    "brief_id": brief["id"],
                    "source_id": brief["source_id"],
                    "model": model["model_id"],
                    "vendor": model["vendor"],
                    "tier": model["tier"],
                }
            )
    write_jsonl(root / "generated" / "assignments.jsonl", assignments)
    result = {}
    for model, items in by_model.items():
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
        path = root / "generated" / "inputs" / f"{safe}.jsonl"
        write_jsonl(path, items)
        result[model] = (
            path,
            sum(token_estimate(json.dumps(item["modelInput"])) for item in items),
            len(items) * 1200,
        )
    return result


def collect_generated(
    root: Path, output_lines: Iterable[dict], *, model_id: str
) -> tuple[list[dict], list[dict]]:
    source_map = {
        row["id"]: row for row in read_jsonl(root / "sources" / "human.jsonl")
    }
    assignments = {
        row["recordId"]: row
        for row in read_jsonl(root / "generated" / "assignments.jsonl")
        if row["model"] == model_id
    }
    accepted, rejected = [], []
    for line in output_lines:
        record_id = line.get("recordId")
        assignment = assignments.get(record_id)
        text = parse_output(line)
        reason = None
        overlap = (0.0, 0.0)
        if assignment is None:
            reason = "unknown_record_id"
        elif not text:
            reason = "empty_or_failed_output"
        else:
            source = source_map.get(assignment["source_id"])
            if source is None:
                reason = "unknown_source_id"
            else:
                overlap = leak_scores(_source_text(root, source), text)
                if overlap[0] > 0.0 or overlap[1] >= 0.6:
                    reason = "generated_source_overlap"
        if reason:
            rejected.append(
                {
                    "record_id": record_id,
                    "source_id": assignment.get("source_id") if assignment else None,
                    "model": model_id,
                    "reason": reason,
                    "overlap_8gram": overlap[0],
                    "overlap_sentence": overlap[1],
                    "output_digest": sha256_text(text),
                }
            )
        else:
            accepted.append(
                {
                    "id": record_id,
                    "brief_id": assignment["brief_id"],
                    "source_id": assignment["source_id"],
                    "model": model_id,
                    "vendor": assignment["vendor"],
                    "tier": assignment["tier"],
                    "inference_params": {"temperature": 0.2, "max_tokens": 1200},
                    "output_tokens": token_estimate(text),
                    "s3_key": f"generated/{record_id}.txt",
                    "sha256": sha256_text(text),
                    "leak_score": overlap[0],
                }
            )
    path = root / "generated" / "manifest.jsonl"
    prior = [row for row in read_jsonl(path) if row.get("model") != model_id]
    write_jsonl(path, prior + accepted)
    rejected_path = root / "generated" / "rejections.jsonl"
    prior_rejected = [
        row for row in read_jsonl(rejected_path) if row.get("model") != model_id
    ]
    write_jsonl(rejected_path, prior_rejected + rejected)
    return accepted, rejected
