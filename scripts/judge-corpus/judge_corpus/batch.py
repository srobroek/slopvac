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
    for region_prefix in ("global.", "us.", "eu.", "apac."):
        if model.startswith(region_prefix):
            model = model[len(region_prefix) :]
            break
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
    if model.startswith("openai.gpt-") and not model.startswith("openai.gpt-oss"):
        # GPT-5.x and GPT-6 reject `max_tokens` and a custom temperature. Low
        # reasoning effort keeps hidden reasoning tokens (billed as output) small;
        # the budget still leaves headroom for them.
        return {
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": max_tokens * 2,
            "reasoning_effort": "low",
        }
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
    # OpenAI chat-completion shape. Generic descent would return the first
    # string child, which is `finish_reason`.
    if isinstance(value, dict) and value.get("choices"):
        message = value["choices"][0].get("message") or {}
        return normalise(_deep_text(message.get("content") or ""))
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
            if overlap[0] > 0.0:  # any shared 8-gram; sentence overlap is recorded only
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
            brief_cache_path = Path(".cache") / "briefs" / f"{source_id}.json"
            cache_file = root / brief_cache_path
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(brief, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            accepted.append(
                {
                    "id": f"brief-{source_id}",
                    "source_id": source_id,
                    "model": model_id,
                    "brief": brief,
                    "brief_cache_path": str(brief_cache_path),
                    "digest": sha256_text(
                        json.dumps(brief, sort_keys=True, ensure_ascii=False)
                    ),
                    "overlap_score": overlap[0],
                }
            )
    manifest = [
        {key: value for key, value in row.items() if key != "brief"} for row in accepted
    ]
    write_jsonl(root / "briefs" / "manifest.jsonl", manifest)
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
        brief_payload = brief.get("brief")
        if brief_payload is None:
            cache_path = root / brief["brief_cache_path"]
            brief_payload = json.loads(cache_path.read_text(encoding="utf-8"))
        # Budget from the brief's target length (about 1.3 tokens per word plus
        # headroom), so long documents are not cut off.
        try:
            target_words = int(brief_payload.get("target_length_words") or 800)
        except (TypeError, ValueError):
            target_words = 800
        max_tokens = min(4000, max(600, int(target_words * 1.6)))
        for offset in (0, len(models) // 2):
            # The second model sits half the roster away, so one brief's two
            # generations come from different vendors.
            model = models[(index + offset) % len(models)]
            record_id = (
                f"gen-{brief['source_id']}-{model['model_id'].replace(':', '_')}"
            )
            batch_item = {
                "recordId": record_id,
                "modelInput": model_body(
                    model["model_id"],
                    generation_prompt(brief_payload),
                    max_tokens=max_tokens,
                ),
                "max_tokens": max_tokens,
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
        output_budget = sum(item.pop("max_tokens") for item in items)
        write_jsonl(path, items)
        result[model] = (
            path,
            sum(token_estimate(json.dumps(item["modelInput"])) for item in items),
            output_budget,
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
                if (
                    overlap[0] > 0.0
                ):  # any shared 8-gram; sentence overlap is recorded only
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
                    "genre": source_map[assignment["source_id"]]["genre"],
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
