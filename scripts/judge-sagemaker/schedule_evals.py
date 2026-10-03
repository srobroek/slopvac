"""Run the corpus fine-tune and evaluation campaign in the foreground.

The scheduler submits the 12 corpus fine-tunes, evaluates the six base arms and
then each successful fine-tune, and fetches every terminal SageMaker job so the
shared cost ledger records billed cost. Capacity-related create failures are
retried up to three submissions per target. A campaign with "spot": "fallback"
submits a managed spot job when every on-demand slot for a target is taken or
rejected. It is deliberately not a daemon.

From this directory:
    uv run python schedule_evals.py --help
    uv run python schedule_evals.py --dry-run   # request and budget planning; no AWS calls
    uv run python schedule_evals.py --once      # one live poll/submit pass
    uv run python schedule_evals.py --run       # foreground until finished/exhausted

Press Ctrl-C to stop the foreground scheduler. Already submitted SageMaker jobs
continue running; stop an individual one with judge-sagemaker stop <job-name>.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent
REGION_FILE = {
    "us-east-1": "resources.json",
    "us-west-2": "resources-us-west-2.json",
    "us-east-2": "resources-us-east-2.json",
}
REGIONS = tuple(REGION_FILE)
FINAL = {"Completed", "Failed", "Stopped"}
MAX_ATTEMPTS = 3
DEFAULT_INTERVAL = 60
DEFAULT_BASE_ARMS = (
    "kev-0.8b",
    "kev-4b",
    "kev-9b",
    "laya-english",
    "laya-multilingual",
    "laya-typed-decisions",
)
SEEDS = (17, 18, 19)
DEFAULT_TRAIN_MODELS = ("kev-0.8b", "kev-4b", "kev-9b", "laya-typed-decisions")
# Rebound by set_campaign(); these are the default campaign's arms.
BASE_ARMS = DEFAULT_BASE_ARMS
TRAIN_MODELS = DEFAULT_TRAIN_MODELS
EVAL_ARMS = BASE_ARMS + tuple(
    f"{model}-ft-s{seed}" for model in TRAIN_MODELS for seed in SEEDS
)
TRAIN_CANDIDATES = {
    "kev-0.8b": (
        ("us-east-1", "ml.g6.xlarge"),
        ("us-west-2", "ml.g6.xlarge"),
        ("us-east-2", "ml.g6.xlarge"),
        ("us-east-1", "ml.g6.2xlarge"),
        ("us-west-2", "ml.g6.2xlarge"),
        ("us-east-2", "ml.g6.2xlarge"),
        ("us-east-1", "ml.g5.2xlarge"),
        ("us-west-2", "ml.g5.2xlarge"),
        ("us-east-2", "ml.g5.2xlarge"),
    ),
    # ml.g6e.12xlarge (4 L40S, one used, 384 GiB host) costs more per hour than
    # the 16xlarge (1 L40S, 512 GiB host), so it is the last on-demand resort.
    "kev-4b": tuple(
        (region, instance)
        for instance in (
            "ml.g6e.2xlarge",
            "ml.g6e.4xlarge",
            "ml.g6e.8xlarge",
            "ml.g6e.16xlarge",
            "ml.g6e.12xlarge",
        )
        for region in REGIONS
    ),
    "kev-9b": tuple(
        (region, instance)
        for instance in (
            "ml.g6e.4xlarge",
            "ml.g6e.8xlarge",
            "ml.g6e.16xlarge",
            "ml.g6e.12xlarge",
        )
        for region in REGIONS
    ),
    "laya-typed-decisions": tuple(
        (region, instance)
        for instance in (
            "ml.g5.2xlarge",
            "ml.g5.4xlarge",
            "ml.g5.8xlarge",
            "ml.g5.12xlarge",
            "ml.g5.16xlarge",
        )
        for region in REGIONS
    ),
}
EVAL_CANDIDATES = {
    "small": tuple(
        (region, instance)
        for instance in (
            "ml.g5.2xlarge",
            "ml.g5.4xlarge",
            "ml.g5.8xlarge",
            "ml.g5.12xlarge",
            "ml.g5.16xlarge",
        )
        for region in REGIONS
    ),
    "large": tuple(
        (region, instance)
        for instance in (
            "ml.g6e.2xlarge",
            "ml.g6e.4xlarge",
            "ml.g6e.8xlarge",
            "ml.g6e.16xlarge",
        )
        for region in ("us-west-2", "us-east-1", "us-east-2")
    ),
}
ON_DEMAND, SPOT = "on-demand", "spot"
# A spot job that ended this way lost its capacity or ran out of time. It has no
# resume and reran from the start, so the target is retried, not exhausted.
SPOT_RETRY_STATUSES = {"Interrupted", "MaxWaitTimeExceeded", "MaxRuntimeExceeded"}
CAPACITY_MARKERS = (
    "capacity",
    "resourcelimitexceeded",
    "resource limit",
    "quota exceeded",
    "limit exceeded",
    "insufficientinstancecapacity",
    "instance capacity",
    "not available in the requested availability zone",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_ledger(value: dict[str, Any]) -> None:
    path = ROOT / "cost-ledger.json"
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def resources() -> dict[str, dict[str, Any]]:
    return {
        region: load_json(ROOT / filename) for region, filename in REGION_FILE.items()
    }


def ledger() -> dict[str, Any]:
    return load_json(ROOT / "cost-ledger.json")


def parse_s3(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"not an S3 URI: {uri}")
    bucket, separator, key = uri[5:].partition("/")
    if not separator or not bucket or not key:
        raise ValueError(f"S3 URI must name an object: {uri}")
    return bucket, key


def committed_usd(value: dict[str, Any]) -> float:
    total = 0.0
    for job in value["jobs"]:
        if job.get("status") in FINAL and job.get("cost_usd") is not None:
            total += float(job["cost_usd"])
        else:
            total += float(job.get("max_cost_usd", 0.0))
    return round(total, 4)


# The campaign the scheduler is currently working on. None means the default
# campaign: the corpus export named in resources.json (round 1, v2). Set with
# set_campaign(); one process can serve several campaigns in turn, so one
# ledger writer covers all of them.
CAMPAIGN: dict[str, Any] | None = None


def load_campaign(path: Path) -> dict[str, Any]:
    """A campaign file: id (exports/<id>/train.jsonl identifies its training
    jobs), results (directory under results/), train_models, base_arms, seeds,
    per-region data URIs (train, calibration, test, manifest; the campaign runs
    only in the regions it lists), and the expected test and calibration SHA-256
    digests. An optional checkpoints_from names another campaign id: the campaign
    then submits no training and evaluates its fine-tune arms on that campaign's
    checkpoints. An optional "spot": "fallback" submits a managed spot job when
    every on-demand slot for a target is taken or rejected."""
    c = load_json(path)
    for key in ("id", "results", "train_models", "base_arms", "data", "expected"):
        if key not in c:
            raise SystemExit(f"{path}: campaign lacks {key}")
    regions = [region for region in REGIONS if region in c["data"]]
    if not regions:
        raise SystemExit(f"{path}: campaign has data for none of {list(REGIONS)}")
    for region in regions:
        missing = {"train", "calibration", "test", "manifest"} - set(c["data"][region])
        if missing:
            raise SystemExit(f"{path}: {region} data lacks {sorted(missing)}")
    if c.get("spot", "fallback") != "fallback":
        raise SystemExit(f'{path}: spot must be "fallback" when set')
    return c


def set_campaign(c: dict[str, Any] | None) -> None:
    global CAMPAIGN, TRAIN_MODELS, BASE_ARMS, EVAL_ARMS
    CAMPAIGN = c
    if c is None:
        TRAIN_MODELS, BASE_ARMS = DEFAULT_TRAIN_MODELS, DEFAULT_BASE_ARMS
    else:
        TRAIN_MODELS, BASE_ARMS = tuple(c["train_models"]), tuple(c["base_arms"])
    EVAL_ARMS = BASE_ARMS + tuple(
        f"{model}-ft-s{seed}" for model in TRAIN_MODELS for seed in SEEDS
    )


def data_args(region: str, kind: str) -> list[str]:
    """CLI data flags for this campaign; the default campaign uses resources.json."""
    if CAMPAIGN is None:
        return []
    d = CAMPAIGN["data"][region]
    if kind == "training":
        return [
            "--data",
            d["train"],
            "--calibration",
            d["calibration"],
            "--manifest",
            d["manifest"],
        ]
    return [
        "--test",
        d["test"],
        "--calibration",
        d["calibration"],
        "--manifest",
        d["manifest"],
    ]


def corpus_build_id(config: dict[str, Any]) -> str:
    if CAMPAIGN is not None:
        return CAMPAIGN["id"]
    return config["corpus_export"]["build_id"]


def checkpoint_build_id(build_id: str) -> str:
    """The campaign whose training jobs supply this campaign's fine-tune checkpoints."""
    if CAMPAIGN is not None and CAMPAIGN.get("checkpoints_from"):
        return str(CAMPAIGN["checkpoints_from"])
    return build_id


def trains(build_id: str) -> bool:
    """False for an eval-only campaign (checkpoints_from)."""
    return checkpoint_build_id(build_id) == build_id


def usable_trained_artifact(job: dict[str, Any]) -> bool:
    """A target completes only with the fine-tuned artifact from its accepted recipe."""
    hp = job.get("hyperparameters", {})
    if job.get("model") == "laya-typed-decisions":
        return (
            job.get("status") == "Completed"
            and str(hp.get("epochs")) == "4"
            and str(hp.get("max_len")) == "4096"
        )
    recipe_ok = str(hp.get("max_state")) == "4096" and str(hp.get("epochs")) == "2"
    if job.get("status") == "Completed":
        return recipe_ok
    marker = job.get("scheduler", {}).get("implementation_defect")
    return (
        recipe_ok
        and job.get("status") == "Failed"
        and marker
        in {
            "calibration_context_failure_artifact_ok",
            "kev_container_post_training_ckpt_nameerror_artifact_ok",
        }
    )


def has_usable_training(
    value: dict[str, Any], build_id: str, model: str, seed: int
) -> bool:
    return any(
        usable_trained_artifact(job)
        for job in train_entries(value, build_id, model, seed)
    )


def corpus_train_job(job: dict[str, Any], build_id: str) -> bool:
    source = job.get("data", {}).get("train", {}).get("source", "")
    is_train = (
        job.get("model") in TRAIN_MODELS
        and f"/exports/{build_id}/train.jsonl" in source
    )
    retry_implementation_defect = job.get("scheduler", {}).get("implementation_defect")
    return bool(
        is_train
        and retry_implementation_defect
        not in {
            "trainer_not_called",
            "kev_calibration_context_default",
            "kev_max_state_default",
        }
    )


def seed_of(job: dict[str, Any]) -> int | None:
    seed = job.get("hyperparameters", {}).get("seed")
    try:
        return int(seed)
    except (TypeError, ValueError):
        return None


def train_entries(
    value: dict[str, Any], build_id: str, model: str, seed: int
) -> list[dict[str, Any]]:
    return [
        job
        for job in value["jobs"]
        if corpus_train_job(job, build_id)
        and job.get("model") == model
        and seed_of(job) == seed
    ]


def campaign_started(value: dict[str, Any], build_id: str) -> str | None:
    times = [
        job["submitted_at"]
        for job in value["jobs"]
        if corpus_train_job(job, build_id) and job.get("submitted_at")
    ]
    return min(times) if times else None


def current_eval_entries(
    value: dict[str, Any], build_id: str, campaign_start: str | None, arm: str
) -> list[dict[str, Any]]:
    run_id = f"corpus-{build_id}"
    found = []
    for job in value["jobs"]:
        if job.get("kind") != "evaluation" or job.get("arm") != arm:
            continue
        marked = job.get("scheduler", {}).get("campaign")
        # A job marked for another campaign never counts here. Unmarked jobs
        # (submitted by hand in round 1) belong to the default campaign by time.
        if marked == run_id or (
            marked is None
            and CAMPAIGN is None
            and campaign_start
            and job.get("submitted_at", "") >= campaign_start
        ):
            found.append(job)
    return found


def results_dir() -> str:
    return CAMPAIGN["results"] if CAMPAIGN is not None else "corpus"


def result_path(arm: str) -> Path:
    return ROOT / "results" / results_dir() / arm


def expected_dataset() -> dict[str, str]:
    if CAMPAIGN is not None:
        return {split: CAMPAIGN["expected"][split] for split in ("test", "calibration")}
    path = result_path("kev-0.8b") / "results" / "dataset-manifest.json"
    if not path.is_file():
        raise RuntimeError(f"missing verified corpus baseline dataset manifest: {path}")
    manifest = load_json(path)
    files = manifest.get("files", {})
    if manifest.get("builder") != "corpus-export" or not all(
        files.get(split, {}).get("sha256") for split in ("test", "calibration")
    ):
        raise RuntimeError(f"not a valid corpus-export baseline manifest: {path}")
    return {split: files[split]["sha256"] for split in ("test", "calibration")}


def result_is_current(arm: str, expected: dict[str, str]) -> bool:
    path = result_path(arm) / "results" / f"{arm}.json"
    if not path.is_file():
        return False
    try:
        result = load_json(path)
        actual = result.get("dataset", {})
        return result.get("arm") == arm and all(
            actual.get(split, {}).get("sha256") == digest
            for split, digest in expected.items()
        )
    except (OSError, json.JSONDecodeError):
        return False


def ft_identity(arm: str) -> tuple[str, int] | None:
    if "-ft-s" not in arm:
        return None
    model, seed = arm.rsplit("-ft-s", 1)
    try:
        return model, int(seed)
    except ValueError:
        return None


def is_large(arm: str) -> bool:
    return arm.startswith("kev-9b")


def parse_region(job: dict[str, Any]) -> str | None:
    arn = job.get("arn", "")
    if isinstance(arn, str) and arn.startswith("arn:"):
        pieces = arn.split(":", 4)
        if len(pieces) > 3 and pieces[3] in REGIONS:
            return pieces[3]
    return job.get("scheduler", {}).get("region")


def cli_command(args: list[str], region: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "JUDGE_SAGEMAKER_RESOURCES": REGION_FILE[region]}
    return subprocess.run(
        ["uv", "run", "judge-sagemaker", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def error_text(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(
        part.rstrip() for part in (result.stdout, result.stderr) if part.strip()
    )


def is_capacity_error(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in CAPACITY_MARKERS)


def stamp_job(
    name: str,
    *,
    campaign: str,
    task: str,
    target: str,
    attempt: int,
    region: str,
    instance: str,
    market: str = ON_DEMAND,
    error: str | None = None,
) -> None:
    value = ledger()
    entry = next((job for job in value["jobs"] if job.get("job_name") == name), None)
    if entry is None:
        return
    mark = entry.setdefault("scheduler", {})
    mark.update(
        campaign=campaign,
        task=task,
        target=target,
        attempt=attempt,
        region=region,
        instance_type=instance,
        market=market,
    )
    if error:
        mark.setdefault("submission_errors", []).append(
            {"at": datetime.now(timezone.utc).isoformat(), "error": error}
        )
    save_ledger(value)


def record_job_error(name: str, task: str, error: str) -> None:
    value = ledger()
    entry = next((job for job in value["jobs"] if job.get("job_name") == name), None)
    if entry is None:
        return
    entry.setdefault("scheduler_errors", []).append(
        {"task": task, "at": datetime.now(timezone.utc).isoformat(), "error": error}
    )
    save_ledger(value)


FIXED_CODE_MARKERS = {
    "approved_epoch_alignment",
    "approved_runtime_resize",
    "calibration_context_failure_artifact_ok",
    "capacity_rotation",
    "laya_calibration_oom",
    "kev_calibration_context_default",
    "kev_container_dtype_keyerror",
    "kev_container_laya_commit_keyerror",
    "kev_container_post_training_ckpt_nameerror_artifact_ok",
    "laya_eval_identity_commit",
    "laya_eval_model_channel",
    # A ledger entry left "Submitting" by a crash before CreateTrainingJob ran.
    "orphaned_submission",
    "trainer_not_called",
    # us-east-2 CreateTrainingJob refused before the role trusted us-east-2 jobs.
    "use2_role_trust",
}


FIXED_CODE_SIGNATURES = (
    "KeyError: 'dtype'",
    "KeyError: 'laya_commit'",
    "NameError: name 'ckpt' is not defined",
    "hyperparameters do not match arms.py for laya",
    "KeyError: 'train'",
)


def spot_retry(job: dict[str, Any]) -> bool:
    """A spot job that ended by interruption or timeout; it reran from the start."""
    if not job.get("spot") or job.get("status") not in {"Failed", "Stopped"}:
        return False
    reason = str(job.get("failure_reason") or "").lower()
    return (
        job.get("secondary_status") in SPOT_RETRY_STATUSES
        or "spot" in reason
        or "interrupt" in reason
    )


def markets_for(entries: list[dict[str, Any]]) -> tuple[str, ...]:
    """On-demand first, then spot in a "spot": "fallback" campaign. Spot
    interruptions and timeouts are free retries, so a target that has had
    MAX_ATTEMPTS of them waits for on-demand capacity instead."""
    if CAMPAIGN is None or CAMPAIGN.get("spot") != "fallback":
        return (ON_DEMAND,)
    if sum(map(spot_retry, entries)) >= MAX_ATTEMPTS:
        return (ON_DEMAND,)
    return (ON_DEMAND, SPOT)


def attempt_budget_exempt(job: dict[str, Any]) -> bool:
    """Only fixed code failures, capacity/quota refusals and spot interruptions
    or timeouts are free retries."""
    if job.get("status") in {"Completed", "InProgress", "Submitting", "Stopping"}:
        return False
    if spot_retry(job):
        return True
    scheduler = job.get("scheduler", {})
    marker = scheduler.get("implementation_defect") or scheduler.get(
        "retry_implementation_defect"
    )
    if marker in FIXED_CODE_MARKERS:
        return True
    reason = str(job.get("failure_reason") or "")
    if any(signature in reason for signature in FIXED_CODE_SIGNATURES):
        return True
    # Evals submitted before --cross-export-checkpoint existed rejected the other
    # export's checkpoint; flagged evals skip that check, so this cannot recur.
    if (
        CAMPAIGN is not None
        and CAMPAIGN.get("checkpoints_from")
        and "does not match" in reason
        and "{'train sha256': (" in reason
    ):
        return True
    text = "\n".join(
        (
            reason,
            str(job.get("submission_error") or ""),
            json.dumps(scheduler.get("submission_errors", [])),
            json.dumps(job.get("scheduler_errors", [])),
        )
    )
    if is_capacity_error(text):
        return True
    return (
        not job.get("arn")
        and job.get("note") == "create_training_job raised"
        and "ValidationException" in text
        and "trainingJobName" in text
    )


def attempt_count(entries: list[dict[str, Any]]) -> int:
    return sum(
        (
            job.get("status") == "Failed"
            or job.get("secondary_status") == "MaxRuntimeExceeded"
        )
        and not attempt_budget_exempt(job)
        for job in entries
    )


def retryable(entries: list[dict[str, Any]]) -> bool:
    return attempt_count(entries) < MAX_ATTEMPTS


def mark_laya_eval_retries() -> None:
    value = ledger()
    names = {"laya-english", "laya-multilingual", "laya-typed-decisions"}
    updated = False
    for job in value["jobs"]:
        if (
            job.get("kind") == "evaluation"
            and job.get("arm") in names
            and job.get("scheduler", {}).get("campaign")
            == "corpus-corpus-20260929-s17-v2"
            and job.get("status") == "Failed"
        ):
            job.setdefault("scheduler", {})["retry_implementation_defect"] = (
                "laya_eval_identity_commit"
            )
            updated = True
    if updated:
        save_ledger(value)


def live_entries(value: dict[str, Any]) -> list[dict[str, Any]]:
    return [job for job in value["jobs"] if job.get("status") not in FINAL]


Slot = tuple[str, str, str]  # (region, instance type, ON_DEMAND or SPOT)


def slot_of(job: dict[str, Any]) -> Slot | None:
    """Spot and on-demand quotas are separate, so the market is part of a slot."""
    if not (region := parse_region(job)) or not job.get("instance_type"):
        return None
    return region, str(job["instance_type"]), SPOT if job.get("spot") else ON_DEMAND


def occupied_from_ledger(value: dict[str, Any]) -> set[Slot]:
    return {slot for job in live_entries(value) if (slot := slot_of(job))}


def campaign_regions() -> tuple[str, ...]:
    if CAMPAIGN is None:
        return REGIONS
    return tuple(region for region in REGIONS if region in CAMPAIGN["data"])


def priced_candidates(
    options: tuple[tuple[str, str], ...],
    configs: dict[str, dict[str, Any]],
    markets: tuple[str, ...] = (ON_DEMAND,),
) -> list[Slot]:
    """Priced slots in the campaign's regions: every on-demand slot, then every
    spot slot whose instance type has a spot quota in that region."""
    return [
        (region, instance, market)
        for market in markets
        for region, instance in options
        if region in campaign_regions()
        and instance in configs[region]["instance_prices_usd_per_hour"]
        and (
            market == ON_DEMAND
            or instance in configs[region].get("spot_instance_types", ())
        )
    ]


def candidates_for_eval(arm: str) -> tuple[tuple[str, str], ...]:
    return EVAL_CANDIDATES["large" if is_large(arm) else "small"]


def first_free(
    options: tuple[tuple[str, str], ...],
    occupied: set[Slot],
    configs: dict[str, dict[str, Any]],
    markets: tuple[str, ...],
) -> Slot | None:
    return next(
        (
            slot
            for slot in priced_candidates(options, configs, markets)
            if slot not in occupied
        ),
        None,
    )


def max_cost(
    configs: dict[str, dict[str, Any]], region: str, instance: str, runtime: int
) -> float:
    price = configs[region]["instance_prices_usd_per_hour"][instance]
    return round(float(price) * runtime / 3600, 2)


# Billed training seconds measured in round 1 (v2 export, 5,420 train rows).
MEASURED_TRAIN_S = {
    "kev-0.8b": 9300,
    "kev-4b": 7400,
    "kev-9b": 8000,
    "laya-typed-decisions": 28800,
}
RUNTIME_HEADROOM = 1.4


def training_runtime(config: dict[str, Any], model: str) -> int:
    if CAMPAIGN is not None:
        # Training time scales with rows; runtime_scale is train rows / 5,420.
        return int(
            MEASURED_TRAIN_S[model]
            * float(CAMPAIGN["runtime_scale"])
            * RUNTIME_HEADROOM
        )
    if model == "kev-0.8b":
        return 14400
    if model == "kev-4b":
        return 20040
    if model == "kev-9b":
        return 18300
    if model == "laya-typed-decisions":
        # Measured on an A10G: 2 of 4 epochs in 14,400 s, so the full run is
        # about 28,800 s; 36,000 s leaves 25% headroom.
        return 36000
    return int(config["models"][model]["max_runtime_s"])


def eval_runtime() -> int:
    return int(CAMPAIGN.get("eval_runtime", 3600)) if CAMPAIGN is not None else 3600


def training_args(
    model: str, seed: int, instance: str, runtime: int, region: str
) -> list[str]:
    args = [
        "submit",
        "--model",
        model,
        "--seed",
        str(seed),
        "--instance-type",
        instance,
        "--max-runtime",
        str(runtime),
        "--replay",
        "0",
    ]
    if model == "kev-9b":
        args += ["--max-state", "4096", "--batch", "1", "--accum", "8"]
        args += ["--checkpointing", "1", "--dtype", "bf16", "--weights-dtype", "bf16"]
    if model.startswith("kev-"):
        args += ["--max-state", "4096"]
    return args + data_args(region, "training")


def evaluation_args(
    arm: str, instance: str, region: str, checkpoint: str | None
) -> list[str]:
    args = [
        "evaluate",
        "--arm",
        arm,
        "--instance-type",
        instance,
        "--resources",
        REGION_FILE[region],
        "--max-runtime",
        str(eval_runtime()),
    ]
    if checkpoint:
        args += ["--checkpoint", checkpoint]
        if CAMPAIGN is not None and CAMPAIGN.get("checkpoints_from"):
            args.append("--cross-export-checkpoint")
    return args + data_args(region, "evaluation")


def checkpoint_by_success(
    sm: dict[str, Any], value: dict[str, Any], build_id: str, arm: str
) -> tuple[dict[str, Any], str] | None:
    identity = ft_identity(arm)
    if identity is None:
        return None
    model, seed = identity
    successes = [
        job
        for job in train_entries(value, build_id, model, seed)
        if usable_trained_artifact(job)
    ]
    for job in sorted(
        successes, key=lambda item: item.get("submitted_at", ""), reverse=True
    ):
        region = parse_region(job)
        if not region:
            region, _ = describe(sm, job["job_name"])
        if not region:
            continue
        try:
            detail = sm[region].describe_training_job(TrainingJobName=job["job_name"])
        except ClientError:
            continue
        uri = detail.get("ModelArtifacts", {}).get("S3ModelArtifacts")
        if not uri:
            continue
        if (
            job.get("scheduler", {}).get("implementation_defect")
            == "calibration_context_failure_artifact_ok"
        ):
            try:
                bucket, key = parse_s3(uri)
                with tempfile.NamedTemporaryFile(suffix=".tar.gz") as archive_file:
                    boto3.Session(
                        profile_name=resources()[region]["profile"], region_name=region
                    ).client("s3").download_file(bucket, key, archive_file.name)
                    with tarfile.open(archive_file.name, "r:gz") as archive:
                        names = set(archive.getnames())
                if not {
                    "checkpoint/adapter_model.safetensors",
                    "checkpoint/head.pt",
                }.issubset(names):
                    record_job_error(
                        job["job_name"],
                        "artifact-validation",
                        "archive lacks trained adapter/head",
                    )
                    continue
            except (ClientError, OSError, tarfile.TarError) as error:
                record_job_error(
                    job["job_name"],
                    "artifact-validation",
                    f"{type(error).__name__}: {error}",
                )
                continue
        return job, uri
    return None


def _not_found(error: ClientError) -> bool:
    response = error.response.get("Error", {})
    code, message = response.get("Code", ""), response.get("Message", "")
    return code in {
        "ValidationException",
        "ResourceNotFound",
        "ResourceNotFoundException",
    } and ("not found" in message.casefold() or "could not find" in message.casefold())


def describe(sm: dict[str, Any], name: str) -> tuple[str | None, dict[str, Any] | None]:
    for region, client in sm.items():
        try:
            return region, client.describe_training_job(TrainingJobName=name)
        except ClientError as error:
            if _not_found(error):
                continue
            validation = (
                error.response.get("Error", {}).get("Code") == "ValidationException"
            )
            if validation and not name.replace("-", "").isalnum():
                return None, {
                    "TrainingJobStatus": "InvalidName",
                    "FailureReason": str(error),
                }
            raise
    return None, None


def mark_calibration_artifact(
    entry: dict[str, Any], detail: dict[str, Any], region: str | None
) -> None:
    """Verify a failed calibration-only run's model artifact before marking it usable."""
    reason = str(detail.get("FailureReason") or "")
    if (
        detail.get("TrainingJobStatus") != "Failed"
        or "ContextOverflow" not in reason
        or "calibration-eval" not in reason
        or not region
    ):
        return
    uri = detail.get("ModelArtifacts", {}).get("S3ModelArtifacts")
    if not uri:
        return
    try:
        bucket, key = parse_s3(uri)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as archive_file:
            boto3.Session(
                profile_name=resources()[region]["profile"], region_name=region
            ).client("s3").download_file(bucket, key, archive_file.name)
            with tarfile.open(archive_file.name, "r:gz") as archive:
                names = set(archive.getnames())
        if not {
            "checkpoint/adapter_model.safetensors",
            "checkpoint/head.pt",
        }.issubset(names):
            return
    except (ClientError, OSError, tarfile.TarError, ValueError) as error:
        record_job_error(
            entry["job_name"],
            "artifact-validation",
            f"{type(error).__name__}: {error}",
        )
        return
    value = ledger()
    current = next(
        (job for job in value["jobs"] if job.get("job_name") == entry["job_name"]),
        None,
    )
    if current is not None:
        current["status"] = "Failed"
        current["failure_reason"] = reason
        current["secondary_status"] = detail.get("SecondaryStatus")
        current.setdefault("scheduler", {})["implementation_defect"] = (
            "calibration_context_failure_artifact_ok"
        )
        save_ledger(value)


def campaign_jobs(
    value: dict[str, Any], build_id: str, campaign_start: str | None
) -> list[dict[str, Any]]:
    result = [job for job in value["jobs"] if corpus_train_job(job, build_id)]
    for arm in EVAL_ARMS:
        result.extend(current_eval_entries(value, build_id, campaign_start, arm))
    unique = {job["job_name"]: job for job in result}
    return list(unique.values())


# A job that has waited this long for instance capacity is stopped and
# resubmitted on another region or instance type (round 1: several g6e jobs
# waited 5-21 h for capacity that never came).
CAPACITY_WAIT_S = 3 * 3600


def rotate_if_starved(
    entry: dict[str, Any], detail: dict[str, Any], region: str | None
) -> bool:
    if detail["TrainingJobStatus"] != "InProgress" or detail.get("TrainingStartTime"):
        return False
    message = " ".join(
        t.get("StatusMessage", "") for t in detail.get("SecondaryStatusTransitions", [])
    ).lower()
    created = detail["CreationTime"]
    waited = (datetime.now(created.tzinfo) - created).total_seconds()
    if "capacity" not in message or waited < CAPACITY_WAIT_S or not region:
        return False
    result = cli_command(["stop", entry["job_name"]], region)
    value = ledger()
    current = next(j for j in value["jobs"] if j.get("job_name") == entry["job_name"])
    current.setdefault("scheduler", {})["implementation_defect"] = "capacity_rotation"
    save_ledger(value)
    print(
        f"stop capacity-starved {entry['job_name']} ({region} {entry.get('instance_type')}, waited {waited / 3600:.1f} h) rc={result.returncode}",
        flush=True,
    )
    return True


def starved_slots(entries: list[dict[str, Any]]) -> set[Slot]:
    """Slots a target already waited out; try elsewhere first."""
    return {
        slot
        for job in entries
        if job.get("scheduler", {}).get("implementation_defect") == "capacity_rotation"
        and (slot := slot_of(job))
    }


def slot_order(slots: list[Slot], starved: set[Slot]) -> list[Slot]:
    """On-demand before spot; within each, slots not yet waited out first."""
    return sorted(slots, key=lambda slot: (slot[2] == SPOT, slot in starved))


def fetch_terminal_jobs(
    sm: dict[str, Any],
    value: dict[str, Any],
    build_id: str,
    campaign_start: str | None,
    expected: dict[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    observed: dict[str, str] = {}
    for entry in campaign_jobs(value, build_id, campaign_start):
        name = entry["job_name"]
        region, detail = describe(sm, name)
        if detail is None:
            observed[name] = entry.get("status", "Unknown")
            continue
        status = detail["TrainingJobStatus"]
        observed[name] = status
        if rotate_if_starved(entry, detail, region):
            continue
        if status == "InvalidName":
            record_job_error(name, "describe", detail["FailureReason"])
            continue
        if status == "Failed":
            mark_calibration_artifact(entry, detail, region)
        needs_fetch = (
            entry.get("status") not in FINAL
            # A job stopped before it started never gets billable seconds, but
            # fetch records cost_usd (0.0) for it; fetch each terminal job once.
            or entry.get("cost_usd") is None
            or (
                entry.get("kind") == "evaluation"
                and status == "Completed"
                and not result_is_current(entry.get("arm", ""), expected)
            )
        )
        if status not in FINAL or not needs_fetch:
            continue
        fetch = "fetch-eval" if entry.get("kind") == "evaluation" else "fetch"
        fetch_args = [fetch, name]
        if fetch == "fetch-eval":
            fetch_args += ["--results", results_dir()]
        result = cli_command(fetch_args, region or parse_region(entry))
        if result.returncode:
            exact = error_text(result)
            record_job_error(name, fetch, exact)
            print(f"fetch {name} failed rc={result.returncode}:\n{exact}", flush=True)
        else:
            print(f"fetch {name} -> {status}\n{result.stdout.strip()}", flush=True)
    return ledger(), observed


def _new_ledger_jobs(before: set[str]) -> list[dict[str, Any]]:
    return [job for job in ledger()["jobs"] if job.get("job_name") not in before]


def submit_one(
    *,
    args: list[str],
    slot: Slot,
    target: str,
    task: str,
    attempt: int,
    campaign: str,
) -> tuple[bool, bool, dict[str, Any] | None, str]:
    region, instance, market = slot
    before = {job.get("job_name") for job in ledger()["jobs"]}
    result = cli_command(args + (["--spot"] if market == SPOT else []), region)
    exact = error_text(result)
    created = _new_ledger_jobs(before)
    entry = created[-1] if created else None
    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            name = response.get("job_name") or response.get("plan", {}).get("job_name")
            if entry is None and name:
                entry = next(
                    (job for job in ledger()["jobs"] if job.get("job_name") == name),
                    None,
                )
        except json.JSONDecodeError:
            name = entry.get("job_name") if entry else None
        if entry:
            stamp_job(
                entry["job_name"],
                campaign=campaign,
                task=task,
                target=target,
                attempt=attempt,
                region=region,
                instance=instance,
                market=market,
            )
        print(
            f"submit {target} {region} {instance} {market}:\n{result.stdout.strip()}",
            flush=True,
        )
        return True, False, entry, ""
    if entry:
        stamp_job(
            entry["job_name"],
            campaign=campaign,
            task=task,
            target=target,
            attempt=attempt,
            region=region,
            instance=instance,
            market=market,
            error=exact,
        )
    print(
        f"submit {target} {region} {instance} {market} rc={result.returncode}:\n{exact}",
        flush=True,
    )
    return False, is_capacity_error(exact), entry, exact


def schedule_training(
    value: dict[str, Any],
    configs: dict[str, dict[str, Any]],
    build_id: str,
    occupied: set[Slot],
    campaign: str,
) -> None:
    for model in TRAIN_MODELS if trains(build_id) else ():
        for seed in SEEDS:
            entries = train_entries(value, build_id, model, seed)
            if any(usable_trained_artifact(job) for job in entries):
                continue
            if (
                any(job.get("status") not in FINAL for job in entries)
                or attempt_count(entries) >= MAX_ATTEMPTS
            ):
                continue
            options = priced_candidates(
                TRAIN_CANDIDATES[model], configs, markets_for(entries)
            )
            for slot in slot_order(options, starved_slots(entries)):
                if slot in occupied:
                    continue
                region, instance, _ = slot
                while attempt_count(entries) < MAX_ATTEMPTS:
                    ok, capacity, created, error = submit_one(
                        args=training_args(
                            model,
                            seed,
                            instance,
                            training_runtime(configs[region], model),
                            region,
                        ),
                        slot=slot,
                        target=f"{model}-ft-s{seed}",
                        task="training",
                        attempt=len(entries) + 1,
                        campaign=campaign,
                    )
                    if ok:
                        occupied.add(slot)
                        break
                    value = ledger()
                    entries = train_entries(value, build_id, model, seed)
                    if not capacity or len(entries) >= MAX_ATTEMPTS:
                        break
                if ok or not capacity:
                    break


def schedule_evaluations(
    sm: dict[str, Any],
    value: dict[str, Any],
    configs: dict[str, dict[str, Any]],
    build_id: str,
    campaign_start: str | None,
    expected: dict[str, str],
    occupied: set[Slot],
    campaign: str,
) -> None:
    value = ledger()
    for arm in EVAL_ARMS:
        if result_is_current(arm, expected):
            continue
        entries = current_eval_entries(value, build_id, campaign_start, arm)
        if (
            any(job.get("status") not in FINAL for job in entries)
            or attempt_count(entries) >= MAX_ATTEMPTS
            or (entries and not retryable(entries))
        ):
            continue
        checkpoint = None
        if ft_identity(arm):
            trained = checkpoint_by_success(
                sm, value, checkpoint_build_id(build_id), arm
            )
            if not trained:
                continue
            _, checkpoint = trained
        options = priced_candidates(
            candidates_for_eval(arm), configs, markets_for(entries)
        )
        for slot in slot_order(options, starved_slots(entries)):
            if slot in occupied:
                continue
            region, instance, _ = slot
            while attempt_count(entries) < MAX_ATTEMPTS:
                ok, capacity, created, error = submit_one(
                    args=evaluation_args(arm, instance, region, checkpoint),
                    slot=slot,
                    target=arm,
                    task="evaluation",
                    attempt=len(entries) + 1,
                    campaign=campaign,
                )
                if ok:
                    occupied.add(slot)
                    value = ledger()
                    break
                value = ledger()
                entries = current_eval_entries(value, build_id, campaign_start, arm)
                if not capacity or len(entries) >= MAX_ATTEMPTS:
                    break
            if ok or not capacity:
                break


def status_by_target(
    value: dict[str, Any],
    build_id: str,
    campaign_start: str | None,
    expected: dict[str, str],
) -> dict[str, int]:
    trained = succeeded = waiting = exhausted = 0
    for model in TRAIN_MODELS:
        for seed in SEEDS:
            entries = train_entries(value, checkpoint_build_id(build_id), model, seed)
            if any(usable_trained_artifact(job) for job in entries):
                trained += 1
            elif any(job.get("status") not in FINAL for job in entries):
                waiting += 1
            elif attempt_count(entries) >= MAX_ATTEMPTS or (
                entries and not retryable(entries)
            ):
                exhausted += 1
            else:
                waiting += 1  # not yet submitted, or retryable after a free failure
    for arm in EVAL_ARMS:
        if result_is_current(arm, expected):
            succeeded += 1
        else:
            entries = current_eval_entries(value, build_id, campaign_start, arm)
            if any(job.get("status") not in FINAL for job in entries):
                waiting += 1
            elif attempt_count(entries) >= MAX_ATTEMPTS or (
                entries and not retryable(entries)
            ):
                exhausted += 1
            else:
                waiting += 1  # not yet submitted, or waiting for its checkpoint
    return {
        "training_ready": trained,
        "evaluation_done": succeeded,
        "waiting": waiting,
        "exhausted": exhausted,
    }


def plan(
    value: dict[str, Any],
    configs: dict[str, dict[str, Any]],
    build_id: str,
    campaign_start: str | None,
    expected: dict[str, str],
) -> tuple[list[dict[str, Any]], float]:
    occupied = occupied_from_ledger(value)
    tasks: list[dict[str, Any]] = []
    for model in TRAIN_MODELS if trains(build_id) else ():
        runtime = training_runtime(configs["us-east-1"], model)
        for seed in SEEDS:
            entries = train_entries(value, build_id, model, seed)
            if (
                any(usable_trained_artifact(job) for job in entries)
                or any(job.get("status") not in FINAL for job in entries)
                or attempt_count(entries) >= MAX_ATTEMPTS
                or not retryable(entries)
            ):
                continue
            slot = first_free(
                TRAIN_CANDIDATES[model], occupied, configs, markets_for(entries)
            )
            cost_slot = slot or next(
                iter(priced_candidates(TRAIN_CANDIDATES[model], configs)), None
            )
            if not cost_slot:
                continue
            region, instance, market = cost_slot
            tasks.append(
                {
                    "task": "training",
                    "target": f"{model}-ft-s{seed}",
                    "model": model,
                    "seed": seed,
                    "region": region,
                    "instance": instance,
                    "market": market,
                    "max_cost_usd": max_cost(configs, region, instance, runtime),
                    "available_now": slot is not None,
                }
            )
            if slot:
                occupied.add(slot)
    for arm in EVAL_ARMS:
        if result_is_current(arm, expected):
            continue
        entries = current_eval_entries(value, build_id, campaign_start, arm)
        if (
            any(job.get("status") not in FINAL for job in entries)
            or attempt_count(entries) >= MAX_ATTEMPTS
            or (entries and not retryable(entries))
        ):
            continue
        slot = first_free(
            candidates_for_eval(arm), occupied, configs, markets_for(entries)
        )
        cost_slot = slot or next(
            iter(priced_candidates(candidates_for_eval(arm), configs)), None
        )
        if not cost_slot:
            continue
        region, instance, market = cost_slot
        tasks.append(
            {
                "task": "evaluation",
                "target": arm,
                "region": region,
                "instance": instance,
                "market": market,
                "max_cost_usd": max_cost(configs, region, instance, eval_runtime()),
                "available_now": slot is not None,
                "waiting_for_training": bool(
                    ft_identity(arm)
                    and not any(
                        j.get("status") == "Completed"
                        for j in train_entries(
                            value, checkpoint_build_id(build_id), *ft_identity(arm)
                        )
                    )
                ),
            }
        )
        if slot:
            occupied.add(slot)
    return tasks, round(
        committed_usd(value) + sum(item["max_cost_usd"] for item in tasks), 2
    )


def dry_run(
    tasks: list[dict[str, Any]],
    configs: dict[str, dict[str, Any]],
    cap: float,
    committed: float,
    projected: float,
) -> int:
    label = CAMPAIGN["id"] if CAMPAIGN is not None else "default"
    print(
        f"Corpus campaign {label}: {len(TRAIN_MODELS) * len(SEEDS)} fine-tune targets, {len(EVAL_ARMS)} evaluation targets"
    )
    print(
        f"Ledger: ${committed:.2f} committed; reserve ${projected - committed:.2f}; projected ${projected:.2f} / ${cap:.2f} cap"
    )
    failed = 0
    for item in tasks:
        if not item["available_now"]:
            continue
        if item["task"] == "training":
            args = training_args(
                item["model"],
                item["seed"],
                item["instance"],
                training_runtime(configs[item["region"]], item["model"]),
                item["region"],
            )
        else:
            args = evaluation_args(
                item["target"],
                item["instance"],
                item["region"],
                f"s3://{configs[item['region']]['bucket']}/training/dry-run-placeholder/model.tar.gz"
                if ft_identity(item["target"])
                else None,
            )
        if item["market"] == SPOT:
            args.append("--spot")
        result = cli_command([*args, "--dry-run"], item["region"])
        if result.returncode:
            failed += 1
            print(f"{item['target']}: {error_text(result)}", flush=True)
        else:
            print(
                f"CLI dry-run OK {item['target']} {item['region']} {item['instance']} {item['market']}",
                flush=True,
            )
    if projected > cap:
        failed += 1
        print(f"ERROR projected cap ${projected:.2f} > ${cap:.2f}", flush=True)
    return 1 if failed else 0


def one_pass(
    sm: dict[str, Any],
    configs: dict[str, dict[str, Any]],
    build_id: str,
    expected: dict[str, str],
    campaign: str,
) -> bool:
    value = ledger()
    start = campaign_started(value, build_id)
    value = ledger()
    value, observed = fetch_terminal_jobs(sm, value, build_id, start, expected)
    # A slot is taken by any job still live after this pass's fetch. A finished
    # job of this campaign must not free a slot another live job now holds.
    occupied = {
        slot
        for entry in live_entries(value)
        if observed.get(entry["job_name"]) not in FINAL and (slot := slot_of(entry))
    }
    tasks, projected = plan(value, configs, build_id, start, expected)
    if projected > float(value["cap_usd"]):
        print(
            f"campaign paused projected ${projected:.2f} > cap ${value['cap_usd']:.2f}",
            flush=True,
        )
        return False  # paused, not finished: poll again once reservations settle
    schedule_training(value, configs, build_id, occupied, campaign)
    value = ledger()
    occupied = occupied_from_ledger(value)
    schedule_evaluations(
        sm, value, configs, build_id, start, expected, occupied, campaign
    )
    counts = status_by_target(ledger(), build_id, start, expected)
    print(
        f"[{CAMPAIGN['id'] if CAMPAIGN is not None else 'default'}] training ready {counts['training_ready']}/{len(TRAIN_MODELS) * len(SEEDS)} eval done {counts['evaluation_done']}/{len(EVAL_ARMS)} waiting={counts['waiting']} exhausted={counts['exhausted']}",
        flush=True,
    )
    # Finished when nothing is left to wait for; exhausted targets set the exit code.
    return counts["waiting"] == 0


def acquire_lock() -> Path:
    directory = ROOT / ".cache"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "schedule-evals.lock"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            + "\n"
        )
    return path


def mark_default_state_defects(build_id: str) -> None:
    """Stop and mark round-1 Kev jobs submitted without max_state=4096."""
    current = ledger()
    for job in current["jobs"]:
        if (
            str(job.get("model", "")).startswith("kev-")
            and job.get("data", {})
            .get("train", {})
            .get("source", "")
            .find(f"/exports/{build_id}/train.jsonl")
            >= 0
            and job.get("scheduler", {}).get("implementation_defect") is None
            and job.get("hyperparameters", {}).get("max_state") in (0, "0", None, "")
        ):
            job.setdefault("scheduler", {})["implementation_defect"] = (
                "kev_max_state_default"
            )
            if job.get("status") not in FINAL:
                region = parse_region(job)
                if region:
                    result = cli_command(["stop", job["job_name"]], region)
                    print(
                        f"stop invalid-state job {job['job_name']} rc={result.returncode}: {error_text(result)}",
                        flush=True,
                    )
    save_ledger(current)


def run_live(campaigns: list[dict[str, Any] | None], once: bool, interval: int) -> int:
    configs = resources()
    mark_laya_eval_retries()
    set_campaign(None)
    mark_default_state_defects(corpus_build_id(configs["us-east-1"]))
    sessions = {
        region: boto3.Session(
            profile_name=configs[region]["profile"], region_name=region
        )
        for region in REGIONS
    }
    sm = {region: s.client("sagemaker") for region, s in sessions.items()}
    lock = acquire_lock()
    try:
        while True:
            done, exhausted = [], 0
            for c in campaigns:
                set_campaign(c)
                build_id = corpus_build_id(configs["us-east-1"])
                expected = expected_dataset()
                done.append(
                    one_pass(sm, configs, build_id, expected, f"corpus-{build_id}")
                )
                exhausted += status_by_target(
                    ledger(), build_id, campaign_started(ledger(), build_id), expected
                )["exhausted"]
            if once:
                return 0
            if all(done):
                return 0 if exhausted == 0 else 2
            time.sleep(interval)
    except KeyboardInterrupt:
        return 130
    finally:
        lock.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--once", action="store_true")
    action.add_argument("--run", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=DEFAULT_INTERVAL)
    parser.add_argument(
        "--campaign",
        action="append",
        default=[],
        help="campaign JSON file, or 'default' for the resources.json export; repeatable (default: default)",
    )
    args = parser.parse_args(argv)
    campaigns = [
        None if name == "default" else load_campaign(Path(name))
        for name in (args.campaign or ["default"])
    ]
    if not args.dry_run:
        return run_live(campaigns, args.once, args.interval_seconds)
    configs = resources()
    rc = 0
    for c in campaigns:
        set_campaign(c)
        build_id = corpus_build_id(configs["us-east-1"])
        value = ledger()
        tasks, projected = plan(
            value,
            configs,
            build_id,
            campaign_started(value, build_id),
            expected_dataset(),
        )
        rc |= dry_run(
            tasks, configs, float(value["cap_usd"]), committed_usd(value), projected
        )
    return rc


if __name__ == "__main__":
    sys.exit(main())
