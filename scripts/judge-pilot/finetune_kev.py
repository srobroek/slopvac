"""Delta fine-tune a released Kev checkpoint on the pilot train split with Kev's shipped recipe.

    .cache/src/kev/.venv/bin/python finetune_kev.py kev-0.8b|kev-4b

Local port of `run_train` in Kev's skills/kev-finetune/scripts/kev_modal.py (commit 3e1cd3b): the
kev.train command is built the same way from the init checkpoint's own recorded args (lr capped at
5e-5, batch / accum / checkpointing from the checkpoint, LoRA rank, head dim, targets, isolation,
special embeddings, weights dtype, base revision), with the skill's defaults epochs=1,
replay=2000 records of the public decision-v7 training partition, p_none_pair=0.25. Then a
temperature is fitted on the pilot calibration split from raw logits (kev.metrics.fit_temperature,
micro, as the skill does) and written into head.pt so the server returns calibrated probabilities.
Changed for this host: --device mps and --dtype fp32 (kev.train's bf16 autocast is CUDA-only);
seed 17 instead of the skill's 0.
Writes .cache/runs/ft-<arm>/ (checkpoint) and .cache/runs/ft-<arm>/finetune.json.
"""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

from arms import ARMS, KEV_SRC, RUNS
from memory import rusage_footprint

PILOT = Path(__file__).resolve().parent
CHOICE_ORDER = ["real-defect", "no-defect", "insufficient-context"]
SKILL = {
    "epochs": 1,
    "replay": 2000,
    "p_none_pair": 0.25,
    "seed": 17,
    "max_delta_lr": 5e-5,
}


def to_kev(item):
    q = {
        "type": item["question"]["type"],
        "instructions": item["question"]["instructions"],
        "label": item["label"],
    }
    if item["kind"] == "choice":
        q["criteria"] = {k: item["question"]["criteria"][k] for k in CHOICE_ORDER}
    return {"state": item["state"], "questions": {"q": q}, "id": item["id"]}


def write_kev_data(out):
    data = out / "data"
    data.mkdir(parents=True, exist_ok=True)
    for split in ("train", "calibration"):
        rows = [
            json.loads(line)
            for line in (PILOT / "data" / f"{split}.jsonl").read_text().splitlines()
        ]
        (data / f"{split}.jsonl").write_text(
            "".join(json.dumps(to_kev(r)) + "\n" for r in rows)
        )
    return data


def peak_tree(proc, stop, box):
    while not stop.is_set():
        try:
            box["rss"] = max(box.get("rss", 0), proc.memory_info().rss)
            box["footprint"] = max(
                box.get("footprint", 0),
                (rusage_footprint(proc.pid) or {}).get(
                    "lifetime_max_phys_footprint_bytes", 0
                ),
            )
        except psutil.Error:
            break
        time.sleep(1.0)


def main():
    name = sys.argv[1]
    arm = ARMS[name]
    sys.path.insert(0, str(KEV_SRC))
    from kev.checkpoint import Checkpoint

    out = RUNS / f"ft-{name}"
    init_from = f"{arm['repo']}@{arm['revision']}"
    init = Checkpoint(init_from)
    meta, args = init.meta, init.meta.extra["args"]
    cfg = {
        "lr": min(args["lr"], SKILL["max_delta_lr"]),
        **{k: args[k] for k in ("batch", "accum", "checkpointing")},
        **{k: SKILL[k] for k in ("epochs", "seed", "replay", "p_none_pair")},
    }
    data = write_kev_data(out)
    cmd = [
        sys.executable,
        "-m",
        "kev.train",
        "--data",
        str(data / "train.jsonl"),
        "--init_from",
        init_from,
        "--out",
        str(out),
        "--device",
        "mps",
        "--dtype",
        "fp32",
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
        cmd += [
            "--suite",
            str(KEV_SRC / "evals/v7/decision-v7"),
            "--replay",
            cfg["replay"],
        ]
    cmd = [str(c) for c in cmd]
    print("training:", " ".join(cmd[2:]), flush=True)
    t0 = time.time()
    box, stop = {}, threading.Event()
    with (out / "train.log").open("w") as log:
        proc = subprocess.Popen(
            cmd,
            cwd=KEV_SRC,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        watcher = threading.Thread(
            target=peak_tree, args=(psutil.Process(proc.pid), stop, box), daemon=True
        )
        watcher.start()
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        rc = proc.wait()
        stop.set()
    train_wall = time.time() - t0
    if rc:
        raise SystemExit(f"kev.train failed ({rc}); see {out / 'train.log'}")

    from kev.benchmark import evaluate_records
    from kev.checkpoint import LoadOptions, read_meta, write_meta
    from kev.data import load_records
    from kev.metrics import fit_temperature
    from kev.predictors import LocalPredictor

    t1 = time.time()
    calibration = load_records(data / "calibration.jsonl")
    predictor = LocalPredictor(str(out), "mps", LoadOptions(temperature=1.0))
    _, cal_rows = evaluate_records(calibration, predictor, out / "calibration-eval")
    T = fit_temperature(cal_rows, aggregation="micro")
    m = read_meta(str(out))
    m.temperature = T
    m.extra["temperature_fit"] = {
        "rows": "pilot calibration split",
        "n": len(calibration),
        "method": "min NLL, micro, kev.metrics.fit_temperature",
        "value": T,
    }
    write_meta(str(out), m)
    result = {
        "recipe": "Kev skills/kev-finetune run_train (kev.train delta fine-tune + calibration temperature), local",
        "upstream_commit": arm["upstream_commit"],
        "init_from": init_from,
        "base": meta.base,
        "base_revision": meta.base_revision,
        "hyperparameters": {
            **cfg,
            "device": "mps",
            "dtype": "fp32",
            "lora": meta.lora,
            "head_dim": meta.head_dim,
            "lora_targets": args["lora_targets"],
            "weights_dtype": meta.weights_dtype,
        },
        "command": cmd[2:],
        "temperature_fit_on_calibration": T,
        "train_wall_time_s": round(train_wall, 1),
        "calibration_fit_wall_time_s": round(time.time() - t1, 1),
        "peak_rss_bytes_sampled": box.get("rss"),
        "lifetime_max_phys_footprint_bytes": box.get("footprint"),
    }
    (out / "finetune.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
