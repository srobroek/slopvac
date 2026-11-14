"""Run every per-model generation input: batch where Bedrock supports it,
otherwise the on-demand runner, then collect all outputs.

State lives in `generated/routes.json`, so an interrupted run resumes: a model
with a recorded batch job is not resubmitted, and on-demand runs skip records
already in their output file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from botocore.exceptions import ClientError

from .batch import collect_generated, parse_output
from .bedrock import download_outputs, submit, upload, upload_text, wait
from .common import read_jsonl, token_estimate
from .ondemand import run_ondemand

# Typical generated document length in tokens; the cap per record is larger.
TYPICAL_OUTPUT_TOKENS = 1800


def _safe(model_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model_id)


def _routes_path(root: Path) -> Path:
    return root / "generated" / "routes.json"


def _load_routes(root: Path) -> dict:
    path = _routes_path(root)
    return json.loads(path.read_text()) if path.exists() else {}


def _save_routes(root: Path, routes: dict) -> None:
    _routes_path(root).write_text(json.dumps(routes, indent=2, sort_keys=True) + "\n")


def models_in_assignments(root: Path) -> list[str]:
    seen: dict[str, None] = {}
    for row in read_jsonl(root / "generated" / "assignments.jsonl"):
        seen.setdefault(row["model"], None)
    return list(seen)


def dispatch(root: Path) -> dict:
    """Submit a batch job for every model. Models that reject batch are marked
    `ondemand-pending` for `run_pending`, so one slow on-demand model never holds
    up the batch submissions behind it."""
    routes = _load_routes(root)
    for model in models_in_assignments(root):
        if routes.get(model, {}).get("route"):
            continue
        input_path = root / "generated" / "inputs" / f"{_safe(model)}.jsonl"
        records = list(read_jsonl(input_path))
        input_tokens = sum(token_estimate(json.dumps(r["modelInput"])) for r in records)
        try:
            uri = upload(root, input_path, f"inputs/generation/{input_path.name}")
            job = submit(
                root,
                stage=f"generation-{model.rsplit('/', 1)[-1]}",
                model_id=model,
                input_s3_uri=uri,
                input_tokens=input_tokens,
                output_tokens=len(records) * TYPICAL_OUTPUT_TOKENS,
                output_key=f"outputs/generation/{input_path.stem}/",
            )
            routes[model] = {
                "state": "submitted",
                "route": "batch",
                "job_arn": job["job_arn"],
                "prefix": f"outputs/generation/{input_path.stem}/",
            }
        except ClientError as exc:
            # Fall back only when Bedrock says the model has no batch support;
            # any other validation error is a bug to fix, not a route choice.
            if "not supported" not in str(exc).lower():
                raise
            routes[model] = {
                "state": "ondemand-pending",
                "route": "on-demand",
                "batch_rejection": str(exc),
            }
        _save_routes(root, routes)
        print(json.dumps({"model": model, **routes[model]}), flush=True)
    return routes


def _run_one(root: Path, model: str) -> dict:
    input_path = root / "generated" / "inputs" / f"{_safe(model)}.jsonl"
    local = root / ".cache" / "ondemand" / "generation" / f"{input_path.stem}.jsonl.out"
    job = run_ondemand(
        root,
        input_path,
        model,
        local,
        stage=f"generation-{model.rsplit('/', 1)[-1]}",
        concurrency=4,
        expected_output_tokens=TYPICAL_OUTPUT_TOKENS,
    )
    prefix = f"outputs/generation/{input_path.stem}/ondemand/"
    upload(root, local, prefix + local.name)
    return {"prefix": prefix, "errors": job["errors"]}


def run_pending(root: Path) -> dict:
    """Run every `ondemand-pending` model, one model at a time."""
    routes = _load_routes(root)
    pending = [
        m
        for m, r in routes.items()
        if r.get("state") in {"ondemand-pending", "ondemand-running"}
    ]
    for model in pending:
        routes = _load_routes(root)
        routes[model] = {**routes[model], "state": "ondemand-running"}
        _save_routes(root, routes)
        result = _run_one(root, model)
        routes = _load_routes(root)
        routes[model] = {**routes[model], "state": "ondemand-done", **result}
        _save_routes(root, routes)
        print(json.dumps({"model": model, **routes[model]}), flush=True)
    return routes


def collect_all(root: Path) -> dict:
    """Collect every finished model's outputs once. Batch jobs that are still
    running are skipped, so rerun this until every route is collected."""
    from .bedrock import clients

    _, _, bedrock = clients()
    routes = _load_routes(root)
    for model, route in routes.items():
        if route.get("collected") or route.get("state") not in {
            "submitted",
            "ondemand-done",
        }:
            continue
        if route.get("route") == "batch":
            status = bedrock.get_model_invocation_job(jobIdentifier=route["job_arn"])[
                "status"
            ]
            if status not in {
                "Completed",
                "PartiallyCompleted",
                "Failed",
                "Stopped",
                "Expired",
            }:
                print(
                    json.dumps(
                        {"model": model, "batch_status": status, "collected": False}
                    ),
                    flush=True,
                )
                continue
            route["batch_status"] = status
        raw = root / "generated" / "raw" / f"{_safe(model.rsplit('/', 1)[-1])}.jsonl"
        lines = download_outputs(root, route["prefix"], raw)
        accepted, rejected = collect_generated(root, lines, model_id=model)
        by_id = {row["id"]: row for row in accepted}
        for line in lines:
            row = by_id.get(line.get("recordId"))
            # A rerun leaves the failed first attempt's error line under the same
            # prefix; only a successful output may write the stored text.
            text = parse_output(line) if "modelOutput" in line else ""
            if row and text:
                upload_text(root, text, row["s3_key"])
        route.update(
            {"collected": True, "accepted": len(accepted), "rejected": len(rejected)}
        )
        _save_routes(root, routes)
        print(
            json.dumps(
                {"model": model, "accepted": len(accepted), "rejected": len(rejected)}
            ),
            flush=True,
        )
    return routes
