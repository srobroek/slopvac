"""AWS resource, batch job, and budget helpers.

All mutating AWS calls are explicit CLI commands. The pipeline records their ARN
immediately so an interrupted run can be audited and resumed without guessing.
"""

from __future__ import annotations

import functools
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import boto3

from .common import append_jsonl, read_jsonl, token_estimate, write_jsonl

ACCOUNT = "536697262379"
REGION = "us-east-1"
PROFILE = "sjors+ig-genai-Admin"
# Default for a new ledger only; an existing ledger's cap_usd is authoritative.
CAP_USD = 300.0
BATCH_DISCOUNT = 0.5

# USD/M-token on-demand list prices. Unknown models are not submitted until a
# caller supplies an explicit price; this prevents a false-safe budget estimate.
PRICES = {
    "amazon.nova-micro": (0.035, 0.14),
    "amazon.nova-lite": (0.06, 0.24),
    "amazon.nova-pro": (0.80, 3.20),
    "anthropic.claude-haiku": (1.00, 5.00),
    "anthropic.claude-sonnet-5": (2.00, 10.00),
    "anthropic.claude-opus-5-5": (4.00, 20.00),
    "anthropic.claude-sonnet": (3.00, 15.00),
    "anthropic.claude-opus": (15.00, 75.00),
    "meta.llama3-1-8b": (0.22, 0.22),
    "meta.llama3-3-70b": (0.72, 0.72),
    "meta.llama4-maverick": (0.24, 0.97),
    "mistral.ministral": (0.10, 0.30),
    "mistral.mistral-large": (2.00, 6.00),
    "openai.gpt-6-luna": (0.10, 0.50),
    "openai.gpt-6-sol": (2.00, 10.00),
    "openai.gpt-6-astra": (10.00, 50.00),
    "openai.gpt-oss-20b": (0.07, 0.30),
    "openai.gpt-oss-120b": (0.15, 0.60),
    "qwen.qwen3-32b": (0.20, 0.60),
    # Unverified Bedrock price; set high so the budget guard errs safe.
    "qwen.qwen3-next": (0.50, 2.00),
    "deepseek.v3": (0.14, 0.28),
    "google.gemma-3": (0.10, 0.40),
    "moonshotai.kimi": (0.50, 2.00),
    "zai.glm": (0.50, 2.00),
    "minimax.minimax": (0.30, 1.20),
    "nvidia.nemotron": (0.20, 0.80),
    "ai21.jamba": (0.50, 1.50),
}


def now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


@functools.cache
def clients():
    # One session per process: building a session and three clients costs
    # seconds, and collect loops call this once per uploaded object.
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    return session.client("s3"), session.client("iam"), session.client("bedrock")


def pricing_for(model_id: str) -> tuple[float, float] | None:
    foundation_id = model_id.rsplit("/", 1)[-1]
    # Batch jobs often use an inference-profile ARN whose final component is
    # prefixed with a geography (global., us., eu.). Pricing is published for
    # the provider model ID, so normalize that routing prefix before lookup.
    for region_prefix in ("global.", "us.", "eu.", "apac."):
        if foundation_id.startswith(region_prefix):
            foundation_id = foundation_id[len(region_prefix) :]
            break
    return next(
        (
            prices
            for prefix, prices in PRICES.items()
            if foundation_id.startswith(prefix)
        ),
        None,
    )


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    prices = pricing_for(model_id)
    if prices is None:
        raise ValueError(
            f"no verified price for {model_id}; add it to PRICES before submitting"
        )
    input_price, output_price = prices
    return BATCH_DISCOUNT * (
        (input_tokens * input_price + output_tokens * output_price) / 1_000_000
    )


def ensure_budget(root: Path, estimate: float) -> None:
    ledger_path = root / "ledgers" / "cost-ledger.json"
    data = (
        json.loads(ledger_path.read_text())
        if ledger_path.exists()
        else {"cap_usd": CAP_USD, "jobs": [], "total_estimate_usd": 0.0}
    )
    total = float(data.get("total_estimate_usd", 0.0)) + estimate
    cap = float(data.get("cap_usd", CAP_USD))
    if total > cap:
        raise RuntimeError(
            f"budget cap exceeded: ${total:.4f} > ${cap:.2f}; job not submitted"
        )


_LEDGER_LOCK = threading.Lock()


def record_cost(root: Path, job: dict) -> None:
    # Parallel on-demand runs share one ledger file.
    with _LEDGER_LOCK:
        _record_cost(root, job)


def _record_cost(root: Path, job: dict) -> None:
    path = root / "ledgers" / "cost-ledger.json"
    data = (
        json.loads(path.read_text())
        if path.exists()
        else {"cap_usd": CAP_USD, "jobs": [], "total_estimate_usd": 0.0}
    )
    data.setdefault("jobs", []).append(job)
    data["total_estimate_usd"] = round(
        sum(float(j.get("estimate_usd", 0.0)) for j in data["jobs"]), 6
    )
    data["updated_at"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def provision(root: Path) -> dict:
    s3, iam, _ = clients()
    existing = (
        json.loads((root / "ledgers" / "resources.json").read_text())
        if (root / "ledgers" / "resources.json").exists()
        else {}
    )
    if existing.get("bucket_arn") and existing.get("role_arn"):
        return existing
    suffix = secrets.token_hex(5)
    bucket = f"slopvac-judge-{ACCOUNT}-{suffix}"
    s3.create_bucket(Bucket=bucket)
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
    )
    s3.put_bucket_tagging(
        Bucket=bucket,
        Tagging={"TagSet": [{"Key": "project", "Value": "slopvac-judge"}]},
    )
    role_name = f"slopvac-judge-bedrock-{suffix}"
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    role = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust),
        Description="Batch inference role for slopvac private judge corpus",
    )
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{bucket}",
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"],
                "Resource": f"arn:aws:s3:::{bucket}/*",
            },
        ],
    }
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="slopvac-judge-s3",
        PolicyDocument=json.dumps(policy),
    )
    # Batch jobs on cross-region inference profiles invoke the model as this
    # role; without it they fail with "Customer doesn't have permissions to
    # invokeModel".
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="slopvac-judge-invoke",
        PolicyDocument=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["bedrock:InvokeModel"],
                        "Resource": [
                            "arn:aws:bedrock:*::foundation-model/*",
                            f"arn:aws:bedrock:{REGION}:{ACCOUNT}:inference-profile/*",
                        ],
                    }
                ],
            }
        ),
    )
    resources = {
        "created_at": now(),
        "account": ACCOUNT,
        "region": REGION,
        "bucket": bucket,
        "bucket_arn": f"arn:aws:s3:::{bucket}",
        "role_name": role_name,
        "role_arn": role["Role"]["Arn"],
        "jobs": [],
    }
    path = root / "ledgers" / "resources.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(resources, indent=2, sort_keys=True) + "\n")
    time.sleep(12)  # IAM eventual consistency before Bedrock assumes the role.
    return resources


def upload(root: Path, local_path: Path, key: str) -> str:
    resources = json.loads((root / "ledgers" / "resources.json").read_text())
    s3, _, _ = clients()
    s3.upload_file(
        str(local_path),
        resources["bucket"],
        key,
        ExtraArgs={"ServerSideEncryption": "AES256"},
    )
    return f"s3://{resources['bucket']}/{key}"


def upload_text(root: Path, text: str, key: str) -> str:
    resources = json.loads((root / "ledgers" / "resources.json").read_text())
    s3, _, _ = clients()
    s3.put_object(
        Bucket=resources["bucket"],
        Key=key,
        Body=text.encode("utf-8"),
        ServerSideEncryption="AES256",
        ContentType="text/plain; charset=utf-8",
    )
    return f"s3://{resources['bucket']}/{key}"


def submit(
    root: Path,
    *,
    stage: str,
    model_id: str,
    input_s3_uri: str,
    input_tokens: int,
    output_tokens: int,
    output_key: str,
) -> dict:
    resources = json.loads((root / "ledgers" / "resources.json").read_text())
    estimate = estimate_cost(model_id, input_tokens, output_tokens)
    ensure_budget(root, estimate)
    _, _, bedrock = clients()
    # Bedrock job names: at most 63 characters, alphanumerics and hyphens.
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stage).strip("-")[:40]
    job_name = f"sj-{slug}-{secrets.token_hex(5)}"
    response = bedrock.create_model_invocation_job(
        jobName=job_name,
        roleArn=resources["role_arn"],
        modelId=model_id,
        inputDataConfig={
            "s3InputDataConfig": {
                "s3InputFormat": "JSONL",
                "s3Uri": input_s3_uri,
                "s3BucketOwner": ACCOUNT,
            }
        },
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{resources['bucket']}/{output_key}",
                "s3BucketOwner": ACCOUNT,
            }
        },
        timeoutDurationInHours=24,
        tags=[
            {"key": "project", "value": "slopvac-judge"},
            {"key": "stage", "value": stage},
        ],
    )
    job = {
        "stage": stage,
        "job_name": job_name,
        "job_arn": response["jobArn"],
        "model_id": model_id,
        "input_s3_uri": input_s3_uri,
        "output_s3_uri": f"s3://{resources['bucket']}/{output_key}",
        "input_tokens_estimate": input_tokens,
        "output_tokens_estimate": output_tokens,
        "estimate_usd": round(estimate, 6),
        "batch_discount": BATCH_DISCOUNT,
        "submitted_at": now(),
        "status": "SUBMITTED",
    }
    resources.setdefault("jobs", []).append(job)
    (root / "ledgers" / "resources.json").write_text(
        json.dumps(resources, indent=2, sort_keys=True) + "\n"
    )
    record_cost(root, job)
    return job


def wait(root: Path, job_arn: str, poll_seconds: float = 30.0) -> dict:
    _, _, bedrock = clients()
    while True:
        detail = bedrock.get_model_invocation_job(jobIdentifier=job_arn)
        status = detail.get("status")
        if status in {"Completed", "Failed", "Stopped", "PartiallyCompleted"}:
            resources_path = root / "ledgers" / "resources.json"
            resources = json.loads(resources_path.read_text())
            for job in resources.get("jobs", []):
                if job.get("job_arn") == job_arn:
                    job["status"] = status
                    job["completed_at"] = now()
            resources_path.write_text(
                json.dumps(resources, indent=2, sort_keys=True) + "\n"
            )
            ledger_path = root / "ledgers" / "cost-ledger.json"
            if ledger_path.exists():
                ledger = json.loads(ledger_path.read_text())
                for job in ledger.get("jobs", []):
                    if job.get("job_arn") == job_arn:
                        job["status"] = status
                        job["completed_at"] = now()
                ledger_path.write_text(
                    json.dumps(ledger, indent=2, sort_keys=True) + "\n"
                )
            return detail
        time.sleep(poll_seconds)


def download_outputs(root: Path, output_prefix: str, destination: Path) -> list[dict]:
    resources = json.loads((root / "ledgers" / "resources.json").read_text())
    s3, _, _ = clients()
    bucket = resources["bucket"]
    paginator = s3.get_paginator("list_objects_v2")
    lines: list[dict] = []
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as out:
        for page in paginator.paginate(Bucket=bucket, Prefix=output_prefix):
            for item in page.get("Contents", []):
                key = item["Key"]
                if key.endswith("/"):
                    continue
                body = (
                    s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
                )
                for line in body.splitlines():
                    if line.strip():
                        parsed = json.loads(line)
                        lines.append(parsed)
                        out.write(json.dumps(parsed, ensure_ascii=False) + "\n")
    return lines
