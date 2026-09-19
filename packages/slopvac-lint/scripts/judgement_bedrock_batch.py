#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3"]
# ///
"""Repeatable Bedrock batch/invoke runner for judgement evaluation prompts."""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MIN_BATCH_RECORDS = 100


def make_prompt(row: dict[str, Any]) -> str:
    return (
        row["prompt"]["user"]
        + "\n\nRespond with ONLY one JSON object (no prose, no code fence) that validates against this JSON Schema:\n"
        + json.dumps(row["response_schema"])
    )


def parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def successful_ids(paths: list[Path]) -> set[str]:
    done: set[str] = set()
    for path in paths:
        if path.exists():
            done.update(row["call_id"] for row in read_jsonl(path) if "response" in row)
    return done


def todo(args: argparse.Namespace) -> None:
    prompts = read_jsonl(Path(args.prompts))
    done = successful_ids([Path(p) for p in args.responses])
    rows = [row for row in prompts if row["call_id"] not in done]
    with Path(args.out).open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    print(f"{len(rows)} outstanding rows")


def inference_body(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": args.max_tokens,
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": make_prompt(row)}]}
        ],
    }
    body["system"] = row["prompt"]["system"]
    if args.temperature is not None:
        body["temperature"] = args.temperature
    return body


def load_boto3():
    import boto3

    return boto3


def submit(args: argparse.Namespace) -> None:
    rows = read_jsonl(Path(args.todo))
    if len(rows) < MIN_BATCH_RECORDS:
        print(
            f"Only {len(rows)} rows; Bedrock batch requires at least {MIN_BATCH_RECORDS}. Falling back to invoke mode."
        )
        invoke(
            argparse.Namespace(
                todo=args.todo,
                model_id=args.model_id,
                out=str(Path(args.out_dir) / "responses.jsonl"),
                concurrency=4,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
        )
        return
    boto3 = load_boto3()
    s3 = boto3.client("s3")
    bedrock = boto3.client("bedrock")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    input_key = f"{args.job_name}/input.jsonl"
    output_prefix = f"{args.job_name}/output/"
    payload = "".join(
        json.dumps({"recordId": r["call_id"], "modelInput": inference_body(r, args)})
        + "\n"
        for r in rows
    )
    s3.put_object(Bucket=args.bucket, Key=input_key, Body=payload.encode())
    cfg = {"max_tokens": args.max_tokens}
    kwargs = {
        "jobName": args.job_name,
        "roleArn": args.role_arn,
        "modelId": args.model_id,
        "inputDataConfig": {
            "s3InputDataConfig": {"s3Uri": f"s3://{args.bucket}/{input_key}"}
        },
        "outputDataConfig": {
            "s3OutputDataConfig": {"s3Uri": f"s3://{args.bucket}/{output_prefix}"}
        },
    }
    result = bedrock.create_model_invocation_job(**kwargs)
    metadata = {
        "job_arn": result["jobArn"],
        "model_id": args.model_id,
        "inference_config": cfg,
        "bucket": args.bucket,
        "role_arn": args.role_arn,
        "input_key": input_key,
        "output_prefix": output_prefix,
        "submitted_at": datetime.now(UTC).isoformat(),
        "record_count": len(rows),
        "source_of_truth": "session model field",
        "caveat": "earlier arm sampling parameters were harness defaults; this job uses maxTokens=32000",
    }
    (out_dir / "job.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


def response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        content = value.get("output", {}).get("message", {}).get("content", [])
        return "".join(
            x.get("text", "") for x in content if isinstance(x, dict)
        ) or json.dumps(value)
    return json.dumps(value)


def append_rows(out: Path, rows: list[dict[str, Any]]) -> None:
    existing = successful_ids([out])
    with out.open("a") as fh:
        for row in rows:
            if row["call_id"] not in existing:
                fh.write(json.dumps(row) + "\n")


def invoke(args: argparse.Namespace) -> None:
    rows = read_jsonl(Path(args.todo))
    out = Path(args.out)
    boto3 = load_boto3()
    try:
        from botocore.config import Config

        config = Config(
            read_timeout=600,
            connect_timeout=10,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
    except ImportError:
        config = None
    client = boto3.client("bedrock-runtime", **({"config": config} if config else {}))
    pending = [r for r in rows if r["call_id"] not in successful_ids([out])]
    results: list[dict[str, Any]] = []
    for row in pending:
        err = None
        raw_text = ""
        stop_reason = None
        for attempt in range(3):
            try:
                kwargs = {
                    "modelId": args.model_id,
                    "messages": [
                        {"role": "user", "content": [{"text": make_prompt(row)}]}
                    ],
                    "inferenceConfig": {"maxTokens": args.max_tokens},
                }
                kwargs["system"] = [{"text": row["prompt"]["system"]}]
                result = client.converse(**kwargs)
                raw_text = response_text(result)
                stop_reason = result.get("stopReason")
                if stop_reason != "end_turn":
                    raise ValueError(f"stop_reason={stop_reason}")
                parsed = parse_json(raw_text)
                results.append({"call_id": row["call_id"], "response": parsed})
                err = None
                break
            except Exception as exc:
                err = exc
                if attempt < 2:
                    time.sleep((2**attempt) + random.random())
        if err is not None:
            results.append(
                {
                    "call_id": row["call_id"],
                    "error": str(err)[:300],
                    "raw": raw_text[:4000],
                    "stop_reason": stop_reason,
                }
            )
        append_rows(out, results[-1:])


def collect(args: argparse.Namespace) -> None:
    boto3 = load_boto3()
    bedrock = boto3.client("bedrock")
    s3 = boto3.client("s3")
    job_dir = Path(args.job_dir)
    job = json.loads((job_dir / "job.json").read_text())
    while True:
        status = bedrock.get_model_invocation_job(jobIdentifier=job["job_arn"])
        state = status.get("status")
        if state in {"Completed", "Failed", "Stopped", "PartiallyCompleted"}:
            break
        time.sleep(args.poll_seconds)
    if state != "Completed":
        raise RuntimeError(f"Bedrock job ended in {state}")
    bucket = job["input_key"].split("/", 1)[0] if "bucket" not in job else job["bucket"]
    prefix = job["output_prefix"]
    listing = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = [
        o["Key"] for o in listing.get("Contents", []) if o["Key"].endswith(".jsonl.out")
    ]
    if not objects:
        raise RuntimeError("No .jsonl.out object found")
    prompts = {r["call_id"]: r for r in read_jsonl(Path(args.todo))} if args.todo else {}
    mapped = []
    for key in objects:
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode()
        for raw in body.splitlines():
            record = json.loads(raw)
            cid = record.get("recordId") or record.get("callId")
            if not cid:
                continue
            try:
                value = response_text(
                    record.get("modelOutput", record.get("output", record))
                )
                stop_reason = (
                    record.get("modelOutput", {}).get("stopReason")
                    if isinstance(record.get("modelOutput"), dict)
                    else record.get("stopReason")
                )
                if "error" in record:
                    raise ValueError(record["error"])
                if stop_reason != "end_turn":
                    raise ValueError(f"stop_reason={stop_reason}")
                mapped.append({"call_id": cid, "response": parse_json(value)})
            except Exception as exc:
                mapped.append(
                    {
                        "call_id": cid,
                        "error": str(exc)[:300],
                        "raw": value if "value" in locals() else "",
                        "stop_reason": stop_reason if "stop_reason" in locals() else None,
                    }
                )
    append_rows(Path(args.out), mapped)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    t = sub.add_parser("todo")
    t.add_argument("--prompts", required=True)
    t.add_argument("--responses", action="append", required=True)
    t.add_argument("--out", required=True)
    t.set_defaults(func=todo)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--max-tokens", type=int, default=32000)
    common.add_argument("--temperature", type=float)
    s = sub.add_parser("submit", parents=[common])
    s.add_argument("--todo", required=True)
    s.add_argument("--model-id", required=True)
    s.add_argument("--bucket", required=True)
    s.add_argument("--role-arn", required=True)
    s.add_argument("--job-name", required=True)
    s.add_argument("--out-dir", required=True)
    s.set_defaults(func=submit)
    c = sub.add_parser("collect")
    c.add_argument("--job-dir", required=True)
    c.add_argument("--todo")
    c.add_argument("--out", required=True)
    c.add_argument("--poll-seconds", type=int, default=30)
    c.set_defaults(func=collect)
    i = sub.add_parser("invoke", parents=[common])
    i.add_argument("--todo", required=True)
    i.add_argument("--model-id", required=True)
    i.add_argument("--out", required=True)
    i.add_argument("--concurrency", type=int, default=4)
    i.set_defaults(func=invoke)
    return p


if __name__ == "__main__":
    parsed = parser().parse_args()
    parsed.func(parsed)
