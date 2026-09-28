"""Keep every pilot arm's GPU evaluation moving on SageMaker until each has a result.

Runs in a loop: fetch finished jobs (training and evaluation) so the ledger turns
reservations into billed cost, then submit the next waiting arm to any instance
slot that has no live job. One live evaluation per arm; at most three attempts.

    uv run python schedule_evals.py            # loop until done
    uv run python schedule_evals.py --once     # one pass
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent
PROFILE = "sjors+ig-genai-Admin"
PILOT = Path(
    "/Users/sjors/tmp/worktrees/slopvac/exp-judge-pilot/scripts/judge-pilot/.cache/runs"
)
REGION_FILE = {"us-east-1": "resources.json", "us-west-2": "resources-us-west-2.json"}
FINAL = {"Completed", "Failed", "Stopped"}
MAX_ATTEMPTS = 3

SMALL_SLOTS = [
    ("us-east-1", "ml.g5.2xlarge"),
    ("us-east-1", "ml.g5.12xlarge"),
    ("us-east-1", "ml.g6.xlarge"),
    ("us-east-1", "ml.g6.2xlarge"),
    ("us-west-2", "ml.g5.4xlarge"),
    ("us-west-2", "ml.g5.8xlarge"),
    ("us-west-2", "ml.g5.12xlarge"),
    ("us-west-2", "ml.g5.16xlarge"),
]
# 9B needs more than 24 GB, so only L40S (48 GB) slots that training does not use.
LARGE_SLOTS = [
    ("us-east-1", "ml.g6e.8xlarge"),
    ("us-east-1", "ml.g6e.16xlarge"),
    ("us-west-2", "ml.g6e.2xlarge"),
    ("us-west-2", "ml.g6e.16xlarge"),
]

SEEDS = (17, 18, 19)
ARMS = (
    ["kev-0.8b", "kev-4b", "laya-english", "laya-multilingual", "laya-typed-decisions"]
    + [f"laya-typed-decisions-ft-s{s}" for s in SEEDS]
    + [f"kev-0.8b-ft-s{s}" for s in SEEDS]
    + [f"kev-4b-ft-s{s}" for s in SEEDS]
    + ["kev-9b"]
    + [f"kev-9b-ft-s{s}" for s in SEEDS]
)


def is_large(arm: str) -> bool:
    return arm.startswith("kev-9b")


def ledger() -> dict:
    return json.loads((ROOT / "cost-ledger.json").read_text())


def clients() -> dict:
    s = {r: boto3.Session(profile_name=PROFILE, region_name=r) for r in REGION_FILE}
    return {r: sess.client("sagemaker") for r, sess in s.items()}


def describe(sm: dict, name: str) -> tuple[str, dict] | tuple[None, None]:
    for region, client in sm.items():
        try:
            return region, client.describe_training_job(TrainingJobName=name)
        except ClientError:
            continue
    return None, None


def run(args: list[str], region: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "JUDGE_SAGEMAKER_RESOURCES": REGION_FILE[region]}
    return subprocess.run(
        ["uv", "run", "judge-sagemaker", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def done(arm: str) -> bool:
    return (ROOT / "results" / arm / "results" / f"{arm}.json").exists()


def checkpoint_for(arm: str, sm: dict, jobs: list[dict]) -> str | None:
    """Local run dir for laptop-trained arms, S3 artefact for SageMaker-trained ones."""
    if "-ft-s" not in arm:
        return ""
    base, seed = arm.split("-ft-s")
    if base == "laya-typed-decisions":
        return str((PILOT / f"ft-{base}-s{seed}").resolve() / "model")
    if base == "kev-0.8b":
        return str((PILOT / f"ft-{base}-s{seed}").resolve() / "checkpoint")
    prefix = f"slopvac-judge-{base}-s{seed}-"
    for job in reversed(jobs):
        if job.get("kind") != "evaluation" and job["job_name"].startswith(prefix):
            _, d = describe(sm, job["job_name"])
            if d and d["TrainingJobStatus"] == "Completed":
                return d["ModelArtifacts"]["S3ModelArtifacts"]
    return None  # training not finished yet


def one_pass(sm: dict) -> bool:
    jobs = ledger()["jobs"]
    live_slots, live_arms, attempts = set(), set(), {}
    for job in jobs:
        region, d = describe(sm, job["job_name"])
        status = d["TrainingJobStatus"] if d else job["status"]
        if job.get("kind") == "evaluation":
            arm = job.get("arm")
            attempts[arm] = attempts.get(arm, 0) + (status == "Failed")
        if d is None:
            continue
        if status not in FINAL:
            live_slots.add((region, d["ResourceConfig"]["InstanceType"]))
            if job.get("kind") == "evaluation":
                live_arms.add(job.get("arm"))
        elif job["status"] not in FINAL:
            cmd = [
                "fetch-eval" if job.get("kind") == "evaluation" else "fetch",
                job["job_name"],
            ]
            r = run(cmd, region)
            print(f"fetch {job['job_name']} -> {status} rc={r.returncode}", flush=True)
        elif (
            job.get("kind") == "evaluation"
            and status == "Completed"
            and not done(job.get("arm"))
        ):
            r = run(["fetch-eval", job["job_name"]], region)
            print(f"refetch {job['job_name']} rc={r.returncode}", flush=True)
    remaining = [a for a in ARMS if not done(a)]
    for arm in remaining:
        if arm in live_arms or attempts.get(arm, 0) >= MAX_ATTEMPTS:
            continue
        ckpt = checkpoint_for(arm, sm, jobs)
        if ckpt is None:
            continue
        for slot in LARGE_SLOTS if is_large(arm) else SMALL_SLOTS:
            if slot in live_slots:
                continue
            region, instance = slot
            args = [
                "evaluate",
                "--arm",
                arm,
                "--instance-type",
                instance,
                "--resources",
                REGION_FILE[region],
            ]
            if ckpt:
                args += ["--checkpoint", ckpt]
            r = run(args, region)
            ok = r.returncode == 0
            print(
                f"submit {arm} {region} {instance} rc={r.returncode} {'' if ok else r.stderr.strip().splitlines()[-1][:200]}",
                flush=True,
            )
            if ok:
                live_slots.add(slot)
                live_arms.add(arm)
                break
    left = [a for a in ARMS if not done(a) and attempts.get(a, 0) < MAX_ATTEMPTS]
    print(
        f"pass: done={sum(done(a) for a in ARMS)}/{len(ARMS)} live={sorted(live_arms)} left={len(left)}",
        flush=True,
    )
    return not left


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    sm = clients()
    while True:
        if one_pass(sm) or a.once:
            return
        time.sleep(180)


if __name__ == "__main__":
    sys.exit(main())
