"""SageMaker training-job entry point for corpus Kev delta fine-tunes."""

import json
import os
import platform
import subprocess
import sys
import time
import traceback
from importlib import metadata
from pathlib import Path

from judge_sagemaker.convert import convert_file, sha256_file

ML = Path("/opt/ml")
HYPERPARAMETERS = ML / "input/config/hyperparameters.json"
CHANNELS = ML / "input/data"
MODEL = ML / "model"
FAILURE = ML / "output/failure"
MAX_DELTA_LR = 5e-5
PACKAGES = (
    "torch",
    "transformers",
    "peft",
    "accelerate",
    "numpy",
    "safetensors",
    "tokenizers",
    "huggingface-hub",
    "fla-core",
    "flash-linear-attention",
    "triton",
)


def channel_file(name, required):
    directory = CHANNELS / name
    files = sorted(directory.rglob("*.jsonl")) if directory.is_dir() else []
    if len(files) > 1:
        raise SystemExit(
            f"channel {name} holds {len(files)} .jsonl files; expected one"
        )
    if not files and required:
        raise SystemExit(f"channel {name} holds no .jsonl file")
    return files[0] if files else None


def load_hyperparameters():
    hp = json.loads(HYPERPARAMETERS.read_text())
    return {
        "model": hp["model"],
        "family": hp["family"],
        "init_from": hp["init_from"],
        "base_revision": hp["base_revision"],
        "kev_commit": hp["kev_commit"],
        "epochs": int(hp["epochs"]),
        "seed": int(hp["seed"]),
        "lr": float(hp["lr"]),
        "replay": int(hp["replay"]),
        "p_none_pair": float(hp["p_none_pair"]),
        "max_state": int(hp["max_state"]),
    }


def tee(cmd, log_path, cwd):
    with (
        log_path.open("w", encoding="utf-8") as log,
        subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        ) as proc,
    ):
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
    return proc.returncode


def versions():
    out = {}
    for name in PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            out[name] = None
    return out


def digests(root):
    return {
        str(p.relative_to(root)): sha256_file(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def main():
    started = time.time()
    hp = load_hyperparameters()
    if hp["family"] != "kev":
        raise SystemExit(f"entry.py only runs Kev training; family={hp['family']}")
    kev_root = Path(os.environ["KEV_ROOT"])
    sys.path.insert(0, str(kev_root))
    import torch
    from kev.checkpoint import Checkpoint

    if not torch.cuda.is_available():
        raise SystemExit("no CUDA device visible to the training container")
    data = MODEL / "data"
    splits = {"train": convert_file(channel_file("train", True), data / "train.jsonl")}
    calibration_src = channel_file("calibration", True)
    splits["calibration"] = convert_file(calibration_src, data / "calibration.jsonl")
    print("data:", json.dumps(splits), flush=True)

    init = Checkpoint(hp["init_from"])
    meta, args = init.meta, init.meta.extra["args"]
    if meta.base_revision != hp["base_revision"]:
        raise SystemExit(
            f"{hp['init_from']} records base revision {meta.base_revision}, expected {hp['base_revision']}"
        )
    cfg = {
        "lr": hp["lr"] or min(args["lr"], MAX_DELTA_LR),
        **{k: args[k] for k in ("batch", "accum", "checkpointing")},
        **{k: hp[k] for k in ("epochs", "seed", "replay", "p_none_pair")},
    }
    ckpt = MODEL / "checkpoint"
    cmd = [
        sys.executable,
        "-m",
        "kev.train",
        "--data",
        data / "train.jsonl",
        "--init_from",
        hp["init_from"],
        "--out",
        ckpt,
        "--device",
        "cuda",
        "--dtype",
        "bf16",
        "--base",
        meta.base,
        "--lora",
        meta.lora,
        "--head_dim",
        meta.head_dim,
        "--lora_targets",
        args["lora_targets"],
        "--option_isolation",
        int(meta.option_isolation),
        "--special_embeddings",
        int(meta.special_embeddings),
        "--weights_dtype",
        meta.weights_dtype,
        "--epochs",
        cfg["epochs"],
        "--lr",
        cfg["lr"],
        "--batch",
        cfg["batch"],
        "--accum",
        cfg["accum"],
        "--checkpointing",
        cfg["checkpointing"],
        "--seed",
        cfg["seed"],
        "--p_none_pair",
        cfg["p_none_pair"],
    ]
    if meta.base_revision:
        cmd += ["--base_revision", meta.base_revision]
    if cfg["replay"]:
        cmd += ["--suite", kev_root / "evals/v7/decision-v7", "--replay", cfg["replay"]]
    if hp["max_state"]:
        cmd += ["--max_state", hp["max_state"]]
    elif hp["model"] == "kev-0.8b":
        cmd += ["--max_state", 4096]
    cmd = [str(c) for c in cmd]
    print("training:", " ".join(cmd[2:]), flush=True)
    t0 = time.time()
    rc = tee(cmd, MODEL / "train.log", kev_root)
    train_wall = time.time() - t0
    if rc:
        raise SystemExit(f"kev.train failed ({rc}); see train.log")

    temperature = None
    if calibration_src:
        from kev.benchmark import evaluate_records
        from kev.checkpoint import LoadOptions, read_meta, write_meta
        from kev.data import load_records
        from kev.metrics import fit_temperature
        from kev.predictors import LocalPredictor

        records = load_records(data / "calibration.jsonl")
        predictor = LocalPredictor(str(ckpt), "cuda", LoadOptions(temperature=1.0))
        _, rows = evaluate_records(records, predictor, MODEL / "calibration-eval")
        temperature = fit_temperature(rows, aggregation="micro")
        m = read_meta(str(ckpt))
        m.temperature = temperature
        m.extra["temperature_fit"] = {
            "rows": "calibration channel",
            "n": len(records),
            "method": "min NLL, micro, kev.metrics.fit_temperature",
            "value": temperature,
        }
        write_meta(str(ckpt), m)

    metrics_path = ckpt / "training_metrics.json"
    manifest = {
        "recipe": "Kev skills/kev-finetune run_train (kev.train delta fine-tune + optional calibration temperature), SageMaker",
        "job_name": os.environ.get("TRAINING_JOB_NAME"),
        "training_job_arn": os.environ.get("TRAINING_JOB_ARN"),
        "model": hp["model"],
        "kev_commit": hp["kev_commit"],
        "init_from": hp["init_from"],
        "base": meta.base,
        "base_revision": meta.base_revision,
        "hyperparameters": {
            **cfg,
            "max_state": hp["max_state"]
            or (4096 if hp["model"] == "kev-0.8b" else None),
            "device": "cuda",
            "dtype": "bf16",
            "lora": meta.lora,
            "head_dim": meta.head_dim,
            "lora_targets": args["lora_targets"],
            "weights_dtype": meta.weights_dtype,
        },
        "seed": cfg["seed"],
        "command": cmd[2:],
        "data": splits,
        "input_data_sha256": {k: v["input"]["sha256"] for k, v in splits.items()},
        "temperature_fit_on_calibration": temperature,
        "training_metrics": json.loads(metrics_path.read_text())
        if metrics_path.exists()
        else None,
        "hardware": {
            "gpu": torch.cuda.get_device_name(0),
            "gpu_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
            "cuda": torch.version.cuda,
            "instance_type": os.environ.get("JUDGE_INSTANCE_TYPE"),
        },
        "python": platform.python_version(),
        "packages": versions(),
        "fla_active": versions()["fla-core"] is not None,
        "image_uri": os.environ.get("JUDGE_IMAGE_URI"),
        "train_wall_time_s": round(train_wall, 1),
        "job_wall_time_s": round(time.time() - started, 1),
        # Container wall time x hourly price; billed time also covers instance start and image pull,
        # so `judge-sagemaker fetch` records the billed cost from BillableTimeInSeconds.
        "cost_estimate": {
            "hourly_usd": float(os.environ["JUDGE_HOURLY_USD"]),
            "container_wall_s": round(time.time() - started, 1),
            "usd": round(
                (time.time() - started) * float(os.environ["JUDGE_HOURLY_USD"]) / 3600,
                4,
            ),
        },
        "files": digests(MODEL),
    }
    (MODEL / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in (
                    "model",
                    "init_from",
                    "hyperparameters",
                    "temperature_fit_on_calibration",
                    "train_wall_time_s",
                )
            },
            indent=1,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        FAILURE.parent.mkdir(parents=True, exist_ok=True)
        FAILURE.write_text(
            f"{type(error).__name__}: {error}\n{traceback.format_exc()[-2000:]}"
        )
        raise
