"""SageMaker training-job launcher for the judge-pilot evaluation harness."""

from __future__ import annotations

import argparse
import json
import os
import tarfile
import tempfile
from pathlib import Path

from judge_sagemaker import cli

PILOT = Path("/Users/sjors/tmp/worktrees/slopvac/exp-judge-pilot/scripts/judge-pilot")
EVAL_FILES = (
    "__init__.py",
    "arms.py",
    "compat.py",
    "download_models.py",
    "inventory.py",
    "laya_server.py",
    "memory.py",
    "metrics.py",
    "run_arm.py",
    "serve_arm.py",
)
ARMS = (
    "kev-0.8b",
    "kev-4b",
    "kev-9b",
    "kev-0.8b-ft-s17",
    "kev-0.8b-ft-s18",
    "kev-0.8b-ft-s19",
    "kev-4b-ft-s17",
    "kev-4b-ft-s18",
    "kev-4b-ft-s19",
    "kev-9b-ft-s17",
    "kev-9b-ft-s18",
    "kev-9b-ft-s19",
    "laya-english",
    "laya-multilingual",
    "laya-typed-decisions",
    "laya-typed-decisions-ft-s17",
    "laya-typed-decisions-ft-s18",
    "laya-typed-decisions-ft-s19",
)


def _resource_file_for_arm(arm: str) -> str:
    if arm in ("kev-9b", "kev-9b-ft-s17", "kev-9b-ft-s18", "kev-9b-ft-s19"):
        return "resources-us-west-2.json"
    return "resources.json"


def _source(arm: str, checkpoint: str | None) -> tuple[str, str | None]:

    if not arm.endswith(("-ft-s17", "-ft-s18", "-ft-s19")):
        if checkpoint:
            raise SystemExit("--checkpoint is only valid for fine-tuned arms")
        return "hub", None
    base, seed = arm.rsplit("-ft-s", 1)
    if checkpoint:
        if checkpoint.startswith("s3://"):
            return "s3", checkpoint
        path = Path(checkpoint).expanduser().resolve()
        if not path.exists():
            raise SystemExit(f"checkpoint does not exist: {path}")
        if path.is_dir() and path.name in ("checkpoint", "model"):
            run = path.parent
        elif path.is_dir():
            run = path
        else:
            raise SystemExit(
                "--checkpoint must be an S3 archive or a local run/checkpoint directory"
            )
        if base.startswith("kev-") and not (run / "checkpoint").is_dir():
            run = path.parent if path.name == "checkpoint" else run
        if base.startswith("laya-") and not (run / "model").is_dir():
            run = path.parent if path.name == "model" else run
        if not (run / "finetune.json").is_file():
            raise SystemExit(f"fine-tune metadata not found in {run}/finetune.json")
        fd, archive = tempfile.mkstemp(prefix=f"judge-eval-{arm}-", suffix=".tar.gz")
        os.close(fd)
        with tarfile.open(archive, "w:gz", dereference=True) as tar:
            tar.add(run, arcname=".")
        return "local", archive
    if base in ("kev-4b", "kev-9b"):
        ledger = cli.load_json(cli.LEDGER)
        name = f"slopvac-judge-{base}-s{seed}-"
        candidates = [j for j in ledger["jobs"] if j["job_name"].startswith(name)]
        if not candidates:
            raise SystemExit(
                f"no SageMaker training job recorded for {arm}; pass --checkpoint <S3 model.tar.gz>"
            )
        entry = sorted(candidates, key=lambda j: j["submitted_at"])[-1]
        artifact_ok = (
            entry.get("scheduler", {}).get("implementation_defect")
            == "calibration_context_failure_artifact_ok"
        )
        if entry.get("status") != "Completed" and not artifact_ok:
            raise SystemExit(
                f"source training job {entry['job_name']} is {entry.get('status')}; wait for it to complete"
            )
        model = (
            cli.session(cli.load_json(cli.RESOURCES), None)
            .client("sagemaker")
            .describe_training_job(TrainingJobName=entry["job_name"])
        )
        uri = model.get("ModelArtifacts", {}).get("S3ModelArtifacts")
        if not uri:
            raise SystemExit(
                f"source training job {entry['job_name']} has no model artifact"
            )
        if entry.get("status") != "Completed" and artifact_ok:
            output_bucket, output_key = cli.parse_s3(uri)
            fd, local_archive = tempfile.mkstemp(
                prefix=f"judge-{arm}-", suffix=".tar.gz"
            )
            os.close(fd)
            try:
                source_res = cli.load_json(
                    cli.ROOT
                    / (
                        "resources-us-west-2.json"
                        if uri.startswith("s3://slopvac-judge-536697262379-usw2/")
                        else "resources.json"
                    )
                )
                cli.session(source_res, None).client("s3").download_file(
                    output_bucket, output_key, local_archive
                )
                with tarfile.open(local_archive, "r:gz") as archive:
                    names = set(archive.getnames())
                if not {
                    "checkpoint/adapter_model.safetensors",
                    "checkpoint/head.pt",
                }.issubset(names):
                    raise SystemExit(
                        f"source training job {entry['job_name']} artifact lacks a trained checkpoint"
                    )
            finally:
                Path(local_archive).unlink(missing_ok=True)
        return "training-job", uri
    default = PILOT / ".cache" / "runs" / f"ft-{base}-s{seed}"
    if not default.is_dir():
        raise SystemExit(
            f"local fine-tune run missing: {default}; pass --checkpoint <run-dir>"
        )
    return "local", str(default)


def _package_local_checkpoint(run: str) -> str:
    path = Path(run).expanduser().resolve()
    if path.is_file():
        return str(path)
    fd, archive = tempfile.mkstemp(prefix="judge-eval-checkpoint-", suffix=".tar.gz")
    os.close(fd)
    with tarfile.open(archive, "w:gz", dereference=True) as tar:
        tar.add(path, arcname=".")
    return archive


def _job_request(res, arm, source, checkpoint, name, instance, runtime, price, data):
    job_root = f"s3://{res['bucket']}/{res['s3_prefix']}/{name}"
    channels = ["code", "data"] + (["checkpoint"] if checkpoint else [])
    model_family = "laya" if arm.startswith("laya-") else "kev"
    return {
        "TrainingJobName": name,
        "RoleArn": res["role_arn"],
        "AlgorithmSpecification": {
            "TrainingImage": res["image_uri"],
            "TrainingInputMode": "File",
            "ContainerEntrypoint": [
                "bash",
                "/opt/ml/input/data/code/judge_sagemaker/container/eval_bootstrap.sh",
            ],
        },
        "HyperParameters": {
            "arm": arm,
            "family": model_family,
            "checkpoint_source": source,
            "checkpoint_ref": checkpoint or "",
            "kev_commit": "3e1cd3bb588a388a06827443380befece23e68c7",
            "laya_commit": "9d955671415fc19f069b9cc998928075c1f255ec",
            "port": "8100",
            "data_uri_test": data["test"],
            "data_uri_calibration": data["calibration"],
            "data_manifest_uri": data["manifest"],
        },
        "InputDataConfig": [
            {
                "ChannelName": ch,
                "InputMode": "File",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"{job_root}/input/{ch}/",
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
            }
            for ch in channels
        ],
        "OutputDataConfig": {"S3OutputPath": f"{job_root}/output"},
        "ResourceConfig": {
            "InstanceType": instance,
            "InstanceCount": 1,
            "VolumeSizeInGB": res["volume_size_gb"],
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": runtime},
        "EnableNetworkIsolation": False,
        "Environment": {
            "HF_HOME": res["hf_home"],
            "JUDGE_IMAGE_URI": res["image_uri"],
            "JUDGE_HOURLY_USD": str(price),
            "JUDGE_EVAL_OUT": "/opt/ml/model",
            "JUDGE_FT_ROOT": "/opt/judge/ft",
            "JUDGE_INSTANCE_TYPE": instance,
        },
        "Tags": [
            {"Key": "project", "Value": res["tags"]["project"]},
            {"Key": "arm", "Value": arm},
            {"Key": "component", "Value": "judge-evaluation"},
        ],
    }


def cmd_evaluate(a):
    resource_file = (
        Path(a.resources) if a.resources else Path(_resource_file_for_arm(a.arm))
    )
    cli.RESOURCES = (
        resource_file if resource_file.is_absolute() else cli.ROOT / resource_file
    )
    res = cli.load_json(cli.RESOURCES)
    from judge_sagemaker.pilot.arms import ARMS as pilot_arms

    if a.arm not in pilot_arms:
        raise SystemExit(f"unknown arm {a.arm}")
    source, checkpoint = _source(a.arm, a.checkpoint)
    local_archive = (
        _package_local_checkpoint(checkpoint)
        if source == "local" and checkpoint
        else None
    )
    checkpoint_uri = checkpoint
    if a.instance_type:
        instance = a.instance_type
    elif a.arm.startswith("kev-9b"):
        instance = "ml.g6e.2xlarge"
    elif a.arm.startswith("laya-") or a.arm.startswith("kev-4b"):
        instance = "ml.g5.4xlarge"
    else:
        instance = "ml.g6.xlarge"
    price = res["instance_prices_usd_per_hour"].get(instance)
    runtime = a.max_runtime or 7200
    if not 60 <= runtime <= 21600:
        raise SystemExit("evaluation max runtime must be in [60,21600] seconds")
    short_arm = a.arm.replace(".", "")
    job = f"sv-eval-{short_arm}-{cli.utcnow():%y%m%d%H%M%S%f}"
    job_root = f"s3://{res['bucket']}/{res['s3_prefix']}/{job}"
    max_cost = round(price * runtime / 3600, 2)
    ledger = cli.load_json(cli.LEDGER)
    spent = cli.check_budget(ledger, max_cost)
    data = {
        "test": a.test or res["corpus_export"]["test"],
        "calibration": a.calibration or res["corpus_export"]["calibration"],
        "manifest": a.manifest or res["corpus_export"]["manifest"],
    }
    for field in ("test", "calibration", "manifest"):
        value = data[field]
        if value.startswith("s3://"):
            cli.parse_s3(value)
        elif not Path(value).expanduser().is_file():
            raise SystemExit(f"--{field}: no such file: {value}")
    request = _job_request(
        res, a.arm, source, checkpoint_uri, job, instance, runtime, price, data
    )
    plan = {
        "job_name": job,
        "arm": a.arm,
        "source": source,
        "checkpoint": checkpoint_uri,
        "hourly_estimate_usd": price,
        "max_cost_usd": max_cost,
        "committed_usd": round(spent, 2),
        "cap_usd": ledger["cap_usd"],
        "input_root": f"{job_root}/input/",
        "output_root": f"{job_root}/output/",
        "request": request,
    }
    if a.dry_run:
        print(json.dumps(plan, indent=2))
        if local_archive:
            Path(local_archive).unlink(missing_ok=True)
        return
    s = cli.session(res, a.profile)
    s3, sm = s.client("s3"), s.client("sagemaker")
    key = f"{res['s3_prefix']}/{job}"
    code_files = [
        "__init__.py",
        "convert.py",
        "pilot/__init__.py",
        *[
            f"pilot/{x}"
            for x in (
                "arms.py",
                "compat.py",
                "download_models.py",
                "inventory.py",
                "laya_server.py",
                "memory.py",
                "metrics.py",
                "run_arm.py",
                "serve_arm.py",
            )
        ],
        *[
            f"container/{x}"
            for x in (
                "eval_bootstrap.sh",
                "eval_entry.py",
                "requirements-kev-serve.txt",
                "requirements-fla.txt",
            )
        ],
        *[f"pilot/{x}" for x in ("requirements-harness.txt", "requirements-laya.txt")],
    ]
    for rel in code_files:
        path = cli.PACKAGE / rel
        if path.exists():
            s3.upload_file(
                str(path), res["bucket"], f"{key}/input/code/judge_sagemaker/{rel}"
            )
    for rel, field in (
        ("test.jsonl", "test"),
        ("calibration.jsonl", "calibration"),
        ("export-manifest.json", "manifest"),
    ):
        value = data[field]
        destination = f"{key}/input/data/{rel}"
        if value.startswith("s3://"):
            bucket, obj = cli.parse_s3(value)
            s3.copy({"Bucket": bucket, "Key": obj}, res["bucket"], destination)
        else:
            s3.upload_file(
                str(Path(value).expanduser().resolve()), res["bucket"], destination
            )
    if local_archive:
        s3.upload_file(
            str(local_archive),
            res["bucket"],
            f"{key}/input/checkpoint/checkpoint.tar.gz",
        )
        Path(local_archive).unlink(missing_ok=True)
    elif checkpoint_uri:
        bucket, obj = cli.parse_s3(checkpoint_uri)
        s3.copy(
            {"Bucket": bucket, "Key": obj},
            res["bucket"],
            f"{key}/input/checkpoint/{Path(obj).name}",
        )
    entry = {
        "job_name": job,
        "kind": "evaluation",
        "arm": a.arm,
        "instance_type": instance,
        "hourly_usd": price,
        "max_runtime_s": runtime,
        "max_cost_usd": max_cost,
        "status": "Submitting",
        "billable_seconds": None,
        "cost_usd": None,
        "submitted_at": cli.utcnow().isoformat(),
    }
    ledger["jobs"].append(entry)
    cli.save_json(cli.LEDGER, ledger)
    try:
        arn = sm.create_training_job(**request)["TrainingJobArn"]
    except Exception:
        entry.update(status="Failed", billable_seconds=0, cost_usd=0)
        cli.save_json(cli.LEDGER, ledger)
        raise
    entry.update(status="InProgress", arn=arn)
    cli.save_json(cli.LEDGER, ledger)
    print(
        json.dumps(
            {
                **plan,
                "arn": arn,
                "output": f"{job_root}/output/{job}/output/model.tar.gz",
            },
            indent=2,
        )
    )
    return


def cmd_fetch_eval(a):
    res = cli.load_json(cli.RESOURCES)
    s = cli.session(res, a.profile)
    sm = s.client("sagemaker")
    d = sm.describe_training_job(TrainingJobName=a.job)
    status = d["TrainingJobStatus"]
    ledger = cli.load_json(cli.LEDGER)
    entry = next((j for j in ledger["jobs"] if j["job_name"] == a.job), None)
    if entry is None:
        raise SystemExit(f"job {a.job} not in cost ledger")
    billable = d.get("BillableTimeInSeconds")
    entry.update(
        status=status,
        billable_seconds=billable,
        failure_reason=d.get("FailureReason"),
        arn=d["TrainingJobArn"],
    )
    if status in cli.FINAL:
        entry["cost_usd"] = round((billable or 0) * entry["hourly_usd"] / 3600, 4)
    cli.save_json(cli.LEDGER, ledger)
    result = {
        "job_name": a.job,
        "status": status,
        "cost_usd": entry.get("cost_usd"),
        "failure_reason": d.get("FailureReason"),
    }
    uri = d.get("ModelArtifacts", {}).get("S3ModelArtifacts")
    if status == "Completed" and uri:
        out = cli.ROOT / "results" / "corpus" / entry["arm"]
        out.mkdir(parents=True, exist_ok=True)
        b, k = cli.parse_s3(uri)
        tarpath = out / "model.tar.gz"
        s.client("s3").download_file(b, k, str(tarpath))
        with tarfile.open(tarpath) as t:
            t.extractall(out, filter="data")
        result.update(
            artifact=uri, local=str(out), model_tar_sha256=cli.sha256_file(tarpath)
        )
    print(json.dumps(result, indent=2))


def add_parsers(sub):
    p = sub.add_parser(
        "evaluate", help="run one pilot arm on a SageMaker GPU training job"
    )
    p.add_argument("--arm", required=True, choices=ARMS)
    p.add_argument(
        "--checkpoint",
        help="S3 model.tar.gz or local fine-tune run/checkpoint directory",
    )
    p.add_argument(
        "--test", help="corpus test S3 URI or local JSONL; defaults to published export"
    )
    p.add_argument(
        "--calibration",
        help="corpus calibration S3 URI or local JSONL; defaults to published export",
    )
    p.add_argument(
        "--manifest",
        help="corpus export manifest S3 URI or local JSON file; defaults to published export",
    )
    p.add_argument(
        "--instance-type",
        default=None,
        help="override auto-selected L4/A10G/L40S GPU class",
    )
    p.add_argument(
        "--resources", choices=["resources.json", "resources-us-west-2.json"]
    )
    p.add_argument("--max-runtime", type=int, default=7200)
    p.add_argument("--profile")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_evaluate)
    p = sub.add_parser("fetch-eval", help="record evaluation status and fetch results")
    p.add_argument("job")
    p.add_argument("--profile")
    p.set_defaults(func=cmd_fetch_eval)
