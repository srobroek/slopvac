"""On-demand InvokeModel runner for models that Bedrock batch inference rejects.

It reads a batch-format input file ({recordId, modelInput} per line) and writes
batch-format output lines ({recordId, modelInput, modelOutput} or {recordId,
error}), so the existing collect commands consume both paths unchanged. Runs
resume: record IDs already present in the output file are skipped.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .bedrock import PROFILE, REGION, ensure_budget, now, pricing_for, record_cost
from .common import read_jsonl, token_estimate

RETRYABLE = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelTimeoutException",
    "InternalServerException",
}


def _invoke(client, model_id: str, record: dict) -> dict:
    body = json.dumps(record["modelInput"]).encode("utf-8")
    for attempt in range(8):
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            output = json.loads(response["body"].read())
            return {"recordId": record["recordId"], "modelOutput": output}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in RETRYABLE or attempt == 7:
                return {
                    "recordId": record["recordId"],
                    "error": {"code": code, "message": str(exc)},
                }
            time.sleep(min(60, 2**attempt))
    raise AssertionError("unreachable")


def _usage(output: dict) -> tuple[int, int]:
    usage = output.get("usage") or {}
    return (
        int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


def run_ondemand(
    root: Path,
    input_path: Path,
    model_id: str,
    output_path: Path,
    *,
    stage: str,
    concurrency: int = 16,
    expected_output_tokens: int = 800,
) -> dict:
    records = list(read_jsonl(input_path))
    done: set[str] = set()
    if output_path.exists():
        done = {
            line["recordId"]
            for line in read_jsonl(output_path)
            if "modelOutput" in line
        }
    todo = [r for r in records if r["recordId"] not in done]
    prices = pricing_for(model_id)
    if prices is None:
        raise ValueError(f"no verified price for {model_id}; add it to PRICES first")
    input_tokens = sum(token_estimate(json.dumps(r["modelInput"])) for r in todo)
    estimate = (
        input_tokens * prices[0] + len(todo) * expected_output_tokens * prices[1]
    ) / 1_000_000
    ensure_budget(root, estimate)

    client = boto3.Session(profile_name=PROFILE, region_name=REGION).client(
        "bedrock-runtime",
        config=Config(
            read_timeout=300, retries={"max_attempts": 2, "mode": "standard"}
        ),
    )
    lock = threading.Lock()
    used_in = used_out = errors = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        output_path.open("a", encoding="utf-8") as out,
        ThreadPoolExecutor(concurrency) as pool,
    ):
        futures = [pool.submit(_invoke, client, model_id, r) for r in todo]
        for future in as_completed(futures):
            line = future.result()
            with lock:
                out.write(json.dumps(line, ensure_ascii=False) + "\n")
                out.flush()
                if "modelOutput" in line:
                    tin, tout = _usage(line["modelOutput"])
                    used_in += tin
                    used_out += tout
                else:
                    errors += 1
    actual = (used_in * prices[0] + used_out * prices[1]) / 1_000_000
    job = {
        "mode": "on-demand",
        "stage": stage,
        "model_id": model_id,
        "records": len(todo),
        "errors": errors,
        "input_tokens": used_in,
        "output_tokens": used_out,
        "estimate_usd": round(actual, 6),
        "pre_run_estimate_usd": round(estimate, 6),
        "completed_at": now(),
    }
    record_cost(root, job)
    return job
