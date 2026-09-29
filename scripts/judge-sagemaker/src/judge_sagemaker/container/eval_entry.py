"""SageMaker training-job entry point: evaluate one judge-pilot arm on a GPU with the pilot harness.

Runs in the harness venv after eval_bootstrap.sh has built the arm family's pinned environment.
Sequence, one server at a time:
  1. stage the data channel (test.jsonl, calibration.jsonl, dataset-manifest.json) and check each
     split's SHA-256 against the dataset manifest;
  2. for a fine-tuned arm, unpack the checkpoint channel into JUDGE_FT_ROOT/ft-<base>-s<seed>/:
     a pilot run archive (finetune.json + checkpoint/ or model/) as is, or a `judge-sagemaker
     submit` model.tar.gz, whose manifest.json is mapped to the pilot's finetune.json;
  3. download the arm's pinned Hub revisions (download_models.py), then record its inventory
     (inventory.py) offline;
  4. start the arm's own server on localhost (serve_arm.py, HF_HUB_OFFLINE=1), wait for
     readiness, run `run_arm.py <arm> --port P --skip-throughput`, stop the server;
  5. score with `metrics.py <arm>` and write manifest.json.
Outputs in /opt/ml/model (uploaded as model.tar.gz): data/, results/{<arm>.json, predictions/,
dataset-manifest.json, inventory.json}, runs/<arm>/ (server.json, run.json, finetune.json for a
fine-tuned arm), logs/ and manifest.json. A failure writes /opt/ml/output/failure.
"""

import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import traceback
from pathlib import Path

from judge_sagemaker.convert import sha256_file

ML = Path("/opt/ml")
HYPERPARAMETERS = ML / "input/config/hyperparameters.json"
CHANNELS = ML / "input/data"
FAILURE = ML / "output/failure"
PILOT = Path(__file__).resolve().parents[1] / "pilot"
sys.path.insert(0, str(PILOT))

from arms import ARMS, DATA, KEV_PY, LAYA_PY, OUT, RESULTS, RUNS

HARNESS_PY = Path(os.environ.get("HARNESS_PY", sys.executable))
LOGS = OUT / "logs"
SPLITS = ("test", "calibration")
READY_TIMEOUT_S = 3600
CHOICE_ORDER = ["real-defect", "no-defect", "insufficient-context"]


def family_python(arm):
    return LAYA_PY if arm["family"] == "laya" else KEV_PY


def run_logged(cmd, log_name, cwd=PILOT, env=None):
    """Run to completion, teeing output to logs/<log_name> and the job's CloudWatch stream."""
    LOGS.mkdir(parents=True, exist_ok=True)
    print("run:", " ".join(map(str, cmd)), flush=True)
    t0 = time.time()
    with (
        (LOGS / log_name).open("w", encoding="utf-8") as log,
        subprocess.Popen(
            [str(c) for c in cmd],
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ) as proc,
    ):
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
    if proc.returncode:
        raise SystemExit(f"{cmd[1]} failed ({proc.returncode}); see logs/{log_name}")
    return round(time.time() - t0, 1)


def stage_data():
    src = CHANNELS / "data"
    manifest_path = src / "export-manifest.json"
    raw_manifest = json.loads(manifest_path.read_text())
    manifest = {"builder": "corpus-export", "files": {}}
    DATA.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        info = raw_manifest["files"][split]
        actual = sha256_file(src / f"{split}.jsonl")
        if actual != info["sha256"]:
            raise SystemExit(
                f"{split}.jsonl sha256 {actual} differs from export manifest {info['sha256']}"
            )
        shutil.copyfile(src / f"{split}.jsonl", DATA / f"{split}.jsonl")
        manifest["files"][split] = {"sha256": actual, "items": info["records"]}
    (RESULTS / "dataset-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return manifest, {split: manifest["files"][split]["sha256"] for split in SPLITS}


def calibration_eval(rows, T):
    """judge-pilot finetune_kev.calibration_eval: harness metrics over kev.benchmark rows (raw
    logits), tempered by T."""
    import numpy as np
    from metrics import summarize

    out = {}
    for kind, order in (("noul", ["false", "true"]), ("choice", CHOICE_ORDER)):
        sel = [r for r in rows if r["type"] == kind]
        z = (
            np.array([[r["logits"][r["keys"].index(k)] for k in order] for r in sel])
            / T
        )
        e = np.exp(z - z.max(axis=1, keepdims=True))
        P = e / e.sum(axis=1, keepdims=True)
        y = np.array([order.index(r["keys"][r["label"]]) for r in sel])
        out[kind] = summarize(P, y, kind)
    return out


def finetune_from_training_manifest(run, arm, dataset):
    """Map a `judge-sagemaker submit` job's manifest.json onto the pilot's finetune.json fields."""
    m = json.loads((run / "manifest.json").read_text())
    base = ARMS[arm["ft_base"]]
    checks = {
        "init_from": (m["init_from"], f"{base['repo']}@{base['revision']}"),
        "base_revision": (m["base_revision"], base["base_revision"]),
        "seed": (m["seed"], arm["ft_seed"]),
        "kev_commit": (m["kev_commit"], arm["upstream_commit"]),
        "train sha256": (
            m["input_data_sha256"].get("train"),
            dataset["files"]["train"]["sha256"],
        ),
        "calibration sha256": (
            m["input_data_sha256"].get("calibration"),
            dataset["files"]["calibration"]["sha256"],
        ),
    }
    wrong = {k: v for k, v in checks.items() if v[0] != v[1]}
    if wrong:
        raise SystemExit(
            f"training job {m['job_name']} does not match {arm['ft_base']}: {wrong}"
        )
    T = m.get("temperature_fit_on_calibration")
    rows_path = run / "calibration-eval" / "rows.json"
    rows = (
        json.loads(rows_path.read_text())
        if T is not None and rows_path.is_file()
        else []
    )
    return {
        "recipe": m["recipe"],
        "upstream_commit": m["kev_commit"],
        "init_from": m["init_from"],
        "base": m["base"],
        "base_revision": m["base_revision"],
        "hyperparameters": m["hyperparameters"],
        "command": m["command"],
        "temperature_fit_on_calibration": T,
        "calibration_eval": calibration_eval(rows, T) if rows else None,
        "train_wall_time_s": m.get("train_wall_time_s"),
        # The training job records its whole container wall time, not the calibration fit alone,
        # and samples no process memory; those pilot fields stay null.
        "calibration_fit_wall_time_s": None,
        "peak_rss_bytes_sampled": None,
        "lifetime_max_phys_footprint_bytes": None,
        "sagemaker_training_job": {
            k: m.get(k)
            for k in (
                "job_name",
                "training_job_arn",
                "model",
                "seed",
                "data",
                "input_data_sha256",
                "training_metrics",
                "hardware",
                "packages",
                "fla_active",
                "image_uri",
                "job_wall_time_s",
                "cost_estimate",
            )
        },
    }


def finetune_from_checkpoint_config(arm):
    """Recover fine-tune provenance from a Kev checkpoint-only SageMaker artifact."""
    config_path = Path(arm["local"]) / "training_config.json"
    config = json.loads(config_path.read_text())
    args = config["args"]
    base = ARMS[arm["ft_base"]]
    init_from = config.get("init_source", {}).get("init_from")
    expected_init = f"{base['repo']}@{base['revision']}"
    checks = {
        "init_from": (init_from, expected_init),
        "base": (args.get("base"), base["base"]),
        "base_revision": (config.get("base_revision"), base["base_revision"]),
        "seed": (args.get("seed"), arm["ft_seed"]),
    }
    wrong = {key: pair for key, pair in checks.items() if pair[0] != pair[1]}
    if wrong:
        raise SystemExit(
            f"checkpoint training config does not match {arm['ft_base']}: {wrong}"
        )
    if not config.get("init_source", {}).get("weights_sha256"):
        raise SystemExit(
            "Kev checkpoint training_config.json lacks initialization digest"
        )
    return {
        "recipe": "Kev skills/kev-finetune run_train (Kev checkpoint training_config.json), SageMaker",
        "upstream_commit": arm["upstream_commit"],
        "init_from": init_from,
        "base": args["base"],
        "base_revision": config["base_revision"],
        "hyperparameters": {
            key: args.get(key)
            for key in (
                "lr",
                "batch",
                "accum",
                "checkpointing",
                "epochs",
                "seed",
                "replay",
                "p_none_pair",
                "max_state",
                "device",
                "dtype",
                "weights_dtype",
                "lora",
                "head_dim",
                "lora_targets",
            )
        },
        "trainer_arguments": args,
        "temperature_fit_on_calibration": None,
        "calibration_eval": None,
        "train_wall_time_s": None,
        "calibration_fit_wall_time_s": None,
        "peak_rss_bytes_sampled": None,
        "lifetime_max_phys_footprint_bytes": None,
    }


def stage_checkpoint(arm, source, dataset):
    """Unpack the checkpoint channel's one archive into the arm's ft_run directory."""
    archives = sorted((CHANNELS / "checkpoint").rglob("*.tar.gz"))
    if len(archives) != 1:
        raise SystemExit(
            f"checkpoint channel holds {len(archives)} .tar.gz files; expected one"
        )
    run = Path(arm["ft_run"])
    run.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archives[0]) as tar:
        tar.extractall(run, filter="data")
    # A successful training artifact has a full manifest; a calibration-context failure can
    # still retain the trained Kev checkpoint and its training_config.json.
    if (run / "manifest.json").is_file():
        metadata = finetune_from_training_manifest(run, arm, dataset)
    elif (
        arm["family"] == "kev"
        and (Path(arm["local"]) / "training_config.json").is_file()
    ):
        metadata = finetune_from_checkpoint_config(arm)
    else:
        metadata = None
    if metadata is not None:
        (run / "finetune.json").write_text(json.dumps(metadata, indent=2))
    marker = "head.pt" if arm["family"] == "kev" else "model.safetensors"
    if not (Path(arm["local"]) / marker).is_file():
        raise SystemExit(f"{archives[0].name} has no {marker} under {arm['local']}")
    if not (run / "finetune.json").is_file():
        raise SystemExit(
            f"{archives[0].name} has no usable training manifest or checkpoint config"
        )
    RUNS.joinpath(arm["name"]).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(run / "finetune.json", RUNS / arm["name"] / "finetune.json")
    return {
        "archive": archives[0].name,
        "archive_sha256": sha256_file(archives[0]),
        "files": digests(Path(arm["local"])),
    }


def serve_and_run(name, arm, port):
    env = {**os.environ, "HF_HUB_OFFLINE": "1"}
    if arm["family"] == "laya":
        env["LAYA_DEVICE"] = "cuda"
    server_json = RUNS / name / "server.json"
    LOGS.mkdir(parents=True, exist_ok=True)
    server_log = (LOGS / "server.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [str(HARNESS_PY), "serve_arm.py", name, str(port)],
        cwd=PILOT,
        env=env,
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        t0 = time.time()
        while "load_time_s" not in (
            json.loads(server_json.read_text()) if server_json.exists() else {}
        ):
            if server.poll() is not None:
                raise SystemExit(
                    f"server exited ({server.returncode}); see logs/server.log"
                )
            if time.time() - t0 > READY_TIMEOUT_S:
                raise SystemExit("server not ready within an hour; see logs/server.log")
            time.sleep(0.5)
        harness_s = run_logged(
            [HARNESS_PY, "run_arm.py", name, "--port", port, "--skip-throughput"],
            "run_arm.log",
        )
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGTERM)
            try:
                server.wait(timeout=120)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        server_log.close()
        print((LOGS / "server.log").read_text(errors="replace")[-20000:], flush=True)
    return harness_s


def pip_freeze(py):
    return subprocess.run(
        [str(py), "-m", "pip", "freeze", "--all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()


def digests(root):
    return {
        str(p.relative_to(root)): sha256_file(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def load_hyperparameters():
    hp = json.loads(
        HYPERPARAMETERS.read_text()
    )  # SageMaker passes every value as a string
    return {
        "arm": hp["arm"],
        "family": hp["family"],
        "checkpoint_source": hp["checkpoint_source"],
        "checkpoint_ref": hp.get("checkpoint_ref") or None,
        "port": int(hp["port"]),
        "kev_commit": hp["kev_commit"],
        "data_uri_test": hp.get("data_uri_test"),
        "data_uri_calibration": hp.get("data_uri_calibration"),
        "data_manifest_uri": hp.get("data_manifest_uri"),
    }


def main():
    started = time.time()
    hp = load_hyperparameters()
    name = hp["arm"]
    arm = {**ARMS[name], "name": name}
    commit_key = f"{arm['family']}_commit"
    if arm["family"] != hp["family"] or arm["upstream_commit"] != hp.get(commit_key):
        raise SystemExit(f"hyperparameters do not match arms.py for {name}")
    timings = {}
    dataset, data_digests = stage_data()
    checkpoint = None
    if arm["local"]:
        checkpoint = stage_checkpoint(arm, hp["checkpoint_source"], dataset)
    py = family_python(arm)
    timings["download_s"] = run_logged([py, "download_models.py", name], "download.log")
    offline = {**os.environ, "HF_HUB_OFFLINE": "1"}
    timings["inventory_s"] = run_logged(
        [py, "inventory.py", name], "inventory.log", env=offline
    )
    timings["serve_and_harness_s"] = serve_and_run(name, arm, hp["port"])
    timings["metrics_s"] = run_logged(
        [HARNESS_PY, "metrics.py", name], "metrics.log", env=offline
    )
    result = json.loads((RESULTS / f"{name}.json").read_text())
    wall = round(time.time() - started, 1)
    hourly = float(os.environ["JUDGE_HOURLY_USD"])
    manifest = {
        "recipe": "judge-pilot run_arm.py --skip-throughput + metrics.py on one arm, SageMaker",
        "job_name": os.environ.get("TRAINING_JOB_NAME"),
        "training_job_arn": os.environ.get("TRAINING_JOB_ARN"),
        "arm": name,
        "arm_config": {k: v for k, v in ARMS[name].items() if k != "downloads"},
        "downloads": ARMS[name]["downloads"],
        "checkpoint_source": hp["checkpoint_source"],
        "checkpoint_ref": hp["checkpoint_ref"],
        "checkpoint": checkpoint,
        "upstream_commit": arm["upstream_commit"],
        "port": hp["port"],
        "dataset": {
            "sha256": data_digests,
            "manifest_sha256": sha256_file(RESULTS / "dataset-manifest.json"),
        },
        "laya_torch": {
            "requirement": os.environ.get("JUDGE_LAYA_TORCH"),
            "index": os.environ.get("JUDGE_LAYA_TORCH_INDEX"),
            "note": "pilot requirements-laya.txt locks torch 2.14.0; download.pytorch.org has no "
            "2.14.0+cu129 build, so the job installs 2.14.0+cu126",
        }
        if arm["family"] == "laya"
        else None,
        "hardware": result["hardware"],
        "runtime": result["runtime"],
        "python": platform.python_version(),
        "packages": {"family": pip_freeze(py), "harness": pip_freeze(HARNESS_PY)},
        "image_uri": os.environ.get("JUDGE_IMAGE_URI"),
        "timings_s": timings,
        "job_wall_time_s": wall,
        # Container wall time x hourly price; `judge-sagemaker fetch-eval` records the billed cost.
        "cost_estimate": {
            "hourly_usd": hourly,
            "container_wall_s": wall,
            "usd": round(wall * hourly / 3600, 4),
        },
    }
    manifest["files"] = digests(OUT)
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n"
    )
    print(
        json.dumps({k: manifest[k] for k in ("arm", "timings_s", "job_wall_time_s")}),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        FAILURE.parent.mkdir(parents=True, exist_ok=True)
        FAILURE.write_text(
            f"{type(error).__name__}: {error}\n{traceback.format_exc()}"[-1000:]
        )
        raise
