"""judge-sagemaker: submit and fetch Kev 4B/9B delta fine-tunes as SageMaker training jobs.

    judge-sagemaker submit --model kev-4b|kev-9b --data <s3 uri | local jsonl> --epochs N --seed S [--dry-run]
    judge-sagemaker fetch <job> [--out DIR] [--logs N]
    judge-sagemaker stop <job>
    judge-sagemaker convert --data <local jsonl> --out <kev jsonl>

Account, region, bucket, role, image and prices come from resources.json; spend is tracked
against the cap in cost-ledger.json. Only SageMaker training jobs are created.
"""

import argparse
import datetime
import json
import sys
import tarfile
from pathlib import Path

from judge_sagemaker.convert import (
    ConversionError,
    convert_file,
    convert_lines,
    sha256_file,
)

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
RESOURCES = ROOT / "resources.json"
LEDGER = ROOT / "cost-ledger.json"
JOBS = ROOT / ".cache" / "jobs"
CODE_FILES = (
    "__init__.py",
    "convert.py",
    "container/__init__.py",
    "container/entry.py",
    "container/bootstrap.sh",
    "container/requirements-kev.txt",
    "container/requirements-fla.txt",
)
CODE_DIR = "/opt/ml/input/data/code"
FINAL = ("Completed", "Failed", "Stopped")
RECIPE = {"epochs": 1, "seed": 17, "replay": 2000, "p_none_pair": 0.25}
# The Kev commit requirements-kev.txt was exported from; bootstrap.sh checks out this commit and its uv.lock digest.
KEV_COMMIT = "3e1cd3bb588a388a06827443380befece23e68c7"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_s3(uri):
    if not uri.startswith("s3://"):
        raise SystemExit(f"not an s3:// URI: {uri}")
    bucket, _, key = uri[5:].partition("/")
    if not bucket or not key or key.endswith("/"):
        raise SystemExit(
            f"--data/--calibration must name one S3 object, not a prefix: {uri}"
        )
    return bucket, key


# --- cost ledger ------------------------------------------------------------------------------------------------------


def committed_usd(ledger):
    """Final jobs count at their billed cost, every other job at its maximum cost."""
    return sum(
        j["cost_usd"]
        if j["status"] in FINAL and j.get("cost_usd") is not None
        else j["max_cost_usd"]
        for j in ledger["jobs"]
    )


def check_budget(ledger, max_cost):
    open_jobs = [j["job_name"] for j in ledger["jobs"] if j["status"] not in FINAL]
    if open_jobs:
        raise SystemExit(
            f"jobs run one at a time: fetch {', '.join(open_jobs)} in a final state first"
        )
    spent = committed_usd(ledger)
    if spent + max_cost > ledger["cap_usd"]:
        raise SystemExit(
            f"cost cap: {spent:.2f} committed + {max_cost:.2f} for this job exceeds "
            f"USD {ledger['cap_usd']:.2f}; lower --max-runtime or raise cap_usd"
        )
    return spent


# --- request ----------------------------------------------------------------------------------------------------------


def job_request(res, a, job, model, instance_type, price, has_calibration):
    base = f"s3://{res['bucket']}/{res['s3_prefix']}/{job}"
    channels = ["code", "train"] + (["calibration"] if has_calibration else [])
    return {
        "TrainingJobName": job,
        "RoleArn": res["role_arn"],
        "AlgorithmSpecification": {
            "TrainingImage": res["image_uri"],
            "TrainingInputMode": "File",
            "ContainerEntrypoint": [
                "bash",
                f"{CODE_DIR}/judge_sagemaker/container/bootstrap.sh",
            ],
        },
        "HyperParameters": {
            "model": a.model,
            "init_from": model["init_from"],
            "base_revision": model["base_revision"],
            "kev_commit": KEV_COMMIT,
            "epochs": str(a.epochs),
            "seed": str(a.seed),
            "lr": repr(a.lr),
            "replay": str(a.replay),
            "p_none_pair": repr(a.p_none_pair),
            "max_state": str(a.max_state),
        },
        "InputDataConfig": [
            {
                "ChannelName": c,
                "InputMode": "File",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"{base}/input/{c}/",
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
            }
            for c in channels
        ],
        "OutputDataConfig": {"S3OutputPath": f"{base}/output"},
        "ResourceConfig": {
            "InstanceType": instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": res["volume_size_gb"],
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": a.max_runtime},
        "EnableNetworkIsolation": False,
        "Environment": {
            "HF_HOME": res["hf_home"],
            "JUDGE_INSTANCE_TYPE": instance_type,
            "JUDGE_IMAGE_URI": res["image_uri"],
            "JUDGE_HOURLY_USD": repr(price),
        },
        "Tags": [{"Key": k, "Value": v} for k, v in res["tags"].items()]
        + [{"Key": "model", "Value": a.model}],
    }


def describe_data(value, name):
    """Validate a local file by converting it (the job converts it again); an S3 object is checked in the job."""
    if value.startswith("s3://"):
        parse_s3(value)
        return {"source": value}
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"--{name}: no such file: {path}")
    try:
        _, report = convert_lines(
            path.read_text(encoding="utf-8").splitlines(), path.name
        )
    except ConversionError as e:
        raise SystemExit(f"--{name}: {e}") from None
    return {
        "source": str(path),
        "sha256": sha256_file(path),
        "format": report["format"],
        "rows": report["rows"],
        "converted_sha256": report["sha256"],
    }


def session(res, profile):
    import boto3

    s = boto3.Session(profile_name=profile or res["profile"], region_name=res["region"])
    account = s.client("sts").get_caller_identity()["Account"]
    if account != res["account_id"]:
        raise SystemExit(
            f"profile resolves to account {account}, resources.json names {res['account_id']}"
        )
    return s


def cmd_submit(a):
    res = load_json(RESOURCES)
    model = res["models"][a.model]
    instance_type = a.instance_type or model["instance_type"]
    price = res["instance_prices_usd_per_hour"].get(instance_type)
    if price is None:
        raise SystemExit(f"no hourly price for {instance_type} in resources.json")
    if a.max_runtime is None:
        a.max_runtime = model["max_runtime_s"]
    if a.epochs < 1 or a.max_runtime < 600:
        raise SystemExit("--epochs must be >= 1 and --max-runtime >= 600 seconds")
    job = f"{res['job_name_prefix']}-{a.model}-s{a.seed}-{utcnow():%Y%m%d%H%M%S}"
    data = {"train": describe_data(a.data, "data")}
    if a.calibration:
        data["calibration"] = describe_data(a.calibration, "calibration")
    max_cost = round(price * a.max_runtime / 3600, 2)
    ledger = load_json(LEDGER)
    spent = check_budget(ledger, max_cost)
    request = job_request(res, a, job, model, instance_type, price, bool(a.calibration))
    plan = {
        "job_name": job,
        "data": data,
        "hourly_usd": price,
        "max_cost_usd": max_cost,
        "committed_usd": round(spent, 2),
        "cap_usd": ledger["cap_usd"],
    }
    if a.dry_run:
        print(json.dumps({"plan": plan, "create_training_job": request}, indent=2))
        return

    s = session(res, a.profile)
    sm, s3 = s.client("sagemaker"), s.client("s3")
    for status in ("InProgress", "Stopping"):
        busy = sm.list_training_jobs(
            StatusEquals=status, NameContains=res["job_name_prefix"]
        )["TrainingJobSummaries"]
        if busy:
            raise SystemExit(
                f"jobs run one at a time: {busy[0]['TrainingJobName']} is {status}"
            )
    key = f"{res['s3_prefix']}/{job}"
    for rel in CODE_FILES:
        s3.upload_file(
            str(PACKAGE / rel), res["bucket"], f"{key}/input/code/judge_sagemaker/{rel}"
        )
    for channel, d in data.items():
        if d["source"].startswith("s3://"):
            src_bucket, src_key = parse_s3(d["source"])
            head = s3.head_object(Bucket=src_bucket, Key=src_key)
            d["etag"], d["version_id"] = head["ETag"], head.get("VersionId")
            s3.copy(
                {"Bucket": src_bucket, "Key": src_key},
                res["bucket"],
                f"{key}/input/{channel}/{Path(src_key).name}",
            )
        else:
            s3.upload_file(
                d["source"],
                res["bucket"],
                f"{key}/input/{channel}/{Path(d['source']).name}",
            )
    entry = {
        "job_name": job,
        "model": a.model,
        "instance_type": instance_type,
        "hourly_usd": price,
        "max_runtime_s": a.max_runtime,
        "max_cost_usd": max_cost,
        "submitted_at": utcnow().isoformat(),
        "status": "Submitting",
        "billable_seconds": None,
        "cost_usd": None,
        "hyperparameters": request["HyperParameters"],
        "data": data,
    }
    ledger["jobs"].append(entry)
    save_json(
        LEDGER, ledger
    )  # recorded before the job exists, so a crash below still counts against the cap
    try:
        arn = sm.create_training_job(**request)["TrainingJobArn"]
    except Exception:
        entry.update(
            status="Failed",
            billable_seconds=0,
            cost_usd=0.0,
            note="create_training_job raised",
        )
        save_json(LEDGER, ledger)
        raise
    entry.update(status="InProgress", arn=arn)
    save_json(LEDGER, ledger)
    print(
        json.dumps(
            {
                **plan,
                "arn": arn,
                "output": f"s3://{res['bucket']}/{key}/output/{job}/output/model.tar.gz",
                "console": f"https://{res['region']}.console.aws.amazon.com/sagemaker/home?region={res['region']}"
                f"#/jobs/{job}",
            },
            indent=2,
        )
    )


def cmd_fetch(a):
    res = load_json(RESOURCES)
    s = session(res, a.profile)
    sm = s.client("sagemaker")
    d = sm.describe_training_job(TrainingJobName=a.job)
    status = d["TrainingJobStatus"]
    billable = d.get("BillableTimeInSeconds")
    ledger = load_json(LEDGER)
    entry = next((j for j in ledger["jobs"] if j["job_name"] == a.job), None)
    if entry is None:
        print(f"warning: {a.job} is not in cost-ledger.json", file=sys.stderr)
    else:
        entry.update(
            status=status,
            billable_seconds=billable,
            arn=d["TrainingJobArn"],
            secondary_status=d.get("SecondaryStatus"),
            failure_reason=d.get("FailureReason"),
        )
        if status in FINAL:
            entry["cost_usd"] = round((billable or 0) * entry["hourly_usd"] / 3600, 4)
        save_json(LEDGER, ledger)
    summary = {
        "job_name": a.job,
        "status": status,
        "secondary_status": d.get("SecondaryStatus"),
        "failure_reason": d.get("FailureReason"),
        "billable_seconds": billable,
        "training_seconds": d.get("TrainingTimeInSeconds"),
        "cost_usd": entry.get("cost_usd") if entry else None,
        "committed_usd": round(committed_usd(ledger), 2),
        "cap_usd": ledger["cap_usd"],
    }
    artifact = d.get("ModelArtifacts", {}).get("S3ModelArtifacts")
    if status == "Completed" and artifact:
        out = Path(a.out).resolve() if a.out else JOBS / a.job
        out.mkdir(parents=True, exist_ok=True)
        tar_path = out / "model.tar.gz"
        bucket, key = parse_s3(artifact)
        s.client("s3").download_file(bucket, key, str(tar_path))
        with tarfile.open(tar_path) as tar:
            tar.extractall(out, filter="data")
        summary.update(
            artifact=artifact, local=str(out), model_tar_sha256=sha256_file(tar_path)
        )
        manifest = out / "manifest.json"
        if manifest.exists():
            m = load_json(manifest)
            summary["manifest"] = {
                k: m.get(k)
                for k in (
                    "init_from",
                    "hyperparameters",
                    "temperature_fit_on_calibration",
                    "train_wall_time_s",
                    "hardware",
                )
            }
    print(json.dumps(summary, indent=2))
    if a.logs:
        logs = s.client("logs")
        events = []
        for stream in logs.describe_log_streams(
            logGroupName="/aws/sagemaker/TrainingJobs", logStreamNamePrefix=f"{a.job}/"
        )["logStreams"]:
            events += logs.get_log_events(
                logGroupName="/aws/sagemaker/TrainingJobs",
                logStreamName=stream["logStreamName"],
                limit=a.logs,
                startFromHead=False,
            )["events"]
        for e in sorted(events, key=lambda e: e["timestamp"])[-a.logs :]:
            print(e["message"])


def cmd_stop(a):
    res = load_json(RESOURCES)
    session(res, a.profile).client("sagemaker").stop_training_job(TrainingJobName=a.job)
    print(
        f"stop requested for {a.job}; run `judge-sagemaker fetch {a.job}` to record its final cost"
    )


def cmd_convert(a):
    try:
        print(json.dumps(convert_file(a.data, a.out), indent=2))
    except ConversionError as e:
        raise SystemExit(str(e)) from None


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="judge-sagemaker", description=__doc__.split("\n\n")[0]
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("submit", help="submit one training job")
    p.add_argument("--model", required=True, choices=["kev-4b", "kev-9b"])
    p.add_argument(
        "--data",
        required=True,
        help="train split: s3://bucket/key.jsonl or a local .jsonl",
    )
    p.add_argument(
        "--calibration",
        help="optional calibration split (same forms); fits the temperature in the job",
    )
    p.add_argument("--epochs", type=int, default=RECIPE["epochs"])
    p.add_argument("--seed", type=int, default=RECIPE["seed"])
    p.add_argument(
        "--lr", type=float, default=0.0, help="0 = the checkpoint's lr capped at 5e-5"
    )
    p.add_argument(
        "--replay",
        type=int,
        default=RECIPE["replay"],
        help="records replayed from Kev's decision-v7 training partition (0 = none)",
    )
    p.add_argument("--p-none-pair", type=float, default=RECIPE["p_none_pair"])
    p.add_argument(
        "--max-state",
        type=int,
        default=0,
        help="kev.train --max_state (0 = Kev's default)",
    )
    p.add_argument(
        "--max-runtime", type=int, help="seconds; default from resources.json per model"
    )
    p.add_argument(
        "--instance-type", help="override resources.json (needs a price there)"
    )
    p.add_argument("--profile", help="AWS profile; default from resources.json")
    p.add_argument(
        "--dry-run", action="store_true", help="print the request; no AWS calls"
    )
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser(
        "fetch",
        help="record a job's status and cost; download its outputs when completed",
    )
    p.add_argument("job")
    p.add_argument("--out", help="download directory; default .cache/jobs/<job>")
    p.add_argument(
        "--logs", type=int, default=0, help="also print the last N CloudWatch log lines"
    )
    p.add_argument("--profile")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("stop", help="stop a running job")
    p.add_argument("job")
    p.add_argument("--profile")
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser(
        "convert", help="convert a local JSONL to Kev requests, as the job does"
    )
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_convert)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
