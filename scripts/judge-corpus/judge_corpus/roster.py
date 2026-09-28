"""Enumerate text models and select balanced, batch-capable candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .bedrock import clients, now, pricing_for

# The roster intentionally names several tiers and vendors. The selected IDs are
# resolved against the live us-east-1 model catalogue; unavailable entries remain
# recorded with a skip reason instead of being silently replaced.
CANDIDATES = {
    "anthropic": [
        ("anthropic.claude-haiku-4-5-20251001-v1:0", "small"),
        ("anthropic.claude-sonnet-4-6", "mid"),
        ("anthropic.claude-opus-4-6-v1", "frontier"),
    ],
    "amazon": [
        ("amazon.nova-micro-v1:0", "small"),
        ("amazon.nova-lite-v1:0", "mid"),
        ("amazon.nova-pro-v1:0", "frontier"),
    ],
    "meta": [
        ("meta.llama3-1-8b-instruct-v1:0", "small"),
        ("meta.llama3-1-70b-instruct-v1:0", "frontier"),
    ],
    "mistral": [
        ("mistral.ministral-3-8b-instruct", "small"),
        ("mistral.ministral-3-14b-instruct", "mid"),
        ("mistral.mistral-large-3-675b-instruct", "frontier"),
    ],
    "openai": [
        ("openai.gpt-oss-20b-1:0", "small"),
        ("openai.gpt-oss-120b-1:0", "frontier"),
    ],
    "qwen": [("qwen.qwen3-32b-v1:0", "mid"), ("qwen.qwen3-next-80b-a3b", "frontier")],
    "deepseek": [("deepseek.v3.2", "frontier")],
    "google": [("google.gemma-3-4b-it", "small"), ("google.gemma-3-12b-it", "mid")],
    "moonshot": [("moonshotai.kimi-k3", "frontier")],
    "zai": [("zai.glm-4.7-flash", "small"), ("zai.glm-4.7", "frontier")],
    "minimax": [("minimax.minimax-m2.1", "mid"), ("minimax.minimax-m2", "frontier")],
    "nvidia": [
        ("nvidia.nemotron-nano-12b-v2", "small"),
        ("nvidia.nemotron-super-3-120b", "frontier"),
    ],
    "ai21": [
        ("ai21.jamba-1-5-mini-v1:0", "small"),
        ("ai21.jamba-1-5-large-v1:0", "mid"),
    ],
}


def _provider(model_id: str) -> str:
    return model_id.split(".", 1)[0]


def build_roster(root: Path) -> dict:
    _, _, bedrock = clients()
    summaries: dict[str, dict] = {}
    page = bedrock.list_foundation_models(byOutputModality="TEXT")
    for model in page.get("modelSummaries", []):
        summaries[model["modelId"]] = model
    profiles: dict[str, dict] = {}
    token = None
    while True:
        args = {"maxResults": 100}
        if token:
            args["nextToken"] = token
        page = bedrock.list_inference_profiles(**args)
        for profile in page.get("inferenceProfileSummaries", []):
            if profile.get("inferenceProfileArn", "").startswith(
                "arn:aws:bedrock:us-east-1:"
            ):
                for model in profile.get("models", []):
                    model_id = model.get("modelArn", "").rsplit("/", 1)[-1]
                    profiles.setdefault(model_id, profile)
        token = page.get("nextToken")
        if not token:
            break
    records: list[dict] = []
    for vendor, candidates in CANDIDATES.items():
        for model_id, tier in candidates:
            summary = summaries.get(model_id)
            profile = profiles.get(model_id)
            if not summary:
                records.append(
                    {
                        "model_id": model_id,
                        "vendor": vendor,
                        "tier": tier,
                        "batch_supported": False,
                        "skip_reason": "not listed in us-east-1 text foundation models",
                    }
                )
                continue
            # AWS does not expose a batch-support bit in list-foundation-models.
            # Keep this auditable and require a smoke batch before marking verified.
            selected_id = profile.get("inferenceProfileArn") if profile else model_id
            records.append(
                {
                    "model_id": selected_id,
                    "foundation_model_id": model_id,
                    "vendor": vendor,
                    "provider_name": summary.get("providerName"),
                    "tier": tier,
                    "input_modalities": summary.get("inputModalities", []),
                    "output_modalities": summary.get("outputModalities", []),
                    "batch_supported": True,
                    "batch_verification": "catalogue-candidate",
                    "inference_profile_arn": profile.get("inferenceProfileArn")
                    if profile
                    else None,
                    "pricing_usd_per_million_on_demand": pricing_for(model_id),
                    "pricing_source": "https://aws.amazon.com/bedrock/pricing/",
                }
            )
    data = {
        "generated_at": now(),
        "region": "us-east-1",
        "batch_support_method": [
            "bedrock:list-foundation-models",
            "bedrock:list-inference-profiles",
            "AWS Bedrock batch inference documentation",
        ],
        "models": records,
    }
    path = root / "models" / "roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data
