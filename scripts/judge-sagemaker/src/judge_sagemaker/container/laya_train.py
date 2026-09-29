"""One-GPU port of judge-pilot finetune_laya.py for SageMaker training jobs."""

import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
from laya.agent import Agent, _fix_tokenizer_config
from laya.common import (
    QTYPES,
    build_model,
    build_sequence,
    proper_reward,
    render_options,
)
from safetensors.torch import load_file, save_file
from transformers import AutoTokenizer

from judge_sagemaker.convert import sha256_file

ML = Path("/opt/ml")
CHANNELS = ML / "input/data"
MODEL = ML / "model"
CHOICE_ORDER = ["real-defect", "no-defect", "insufficient-context"]
HP = {
    "epochs": 4,
    "micro_batch": 8,
    "grad_accum": 8,
    "lr_encoder": 2.5e-5,
    "lr_head": 1e-4,
    "weight_decay": 0.01,
    "group_size": 4,
    "sigma_start": 0.4,
    "sigma_end": 0.1,
    "w_sph": 0.75,
    "w_rps": 1.0,
    "ce_weight": 1.0,
    "clip": 1.0,
    "eta_min": 1e-6,
    "max_len": 4096,
    "head_max_len": 1024,
}


def channel_file(name):
    files = sorted((CHANNELS / name).rglob("*.jsonl"))
    if len(files) != 1:
        raise SystemExit(f"channel {name} has {len(files)} JSONL files; expected one")
    return files[0]


def load_source(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def api_question(item):
    question = {
        "type": item["question"]["type"],
        "instructions": item["question"]["instructions"],
    }
    if item["kind"] == "choice":
        question["criteria"] = {
            key: item["question"]["criteria"][key] for key in CHOICE_ORDER
        }
    return question


def build_item(tok, item):
    question = Agent._to_internal(api_question(item))
    count = len(render_options(question))
    if item["kind"] == "noul":
        target = [0.0, 1.0] if item["label"] else [1.0, 0.0]
    else:
        target = [float(key == item["label"]) for key in CHOICE_ORDER]
    sequence, markers = build_sequence(
        tok, item["state"], question, HP["max_len"], HP["head_max_len"]
    )[:2]
    if len(markers) != count:
        raise SystemExit(
            f"{item['id']}: built {len(markers)} markers for {count} options"
        )
    return {
        "ids": sequence,
        "markers": markers,
        "qtype": QTYPES[question["t"]],
        "target": target,
        "label": target.index(1.0),
    }


def collate(items, pad_id):
    n, length, max_options = (
        len(items),
        max(len(item["ids"]) for item in items),
        max(len(item["markers"]) for item in items),
    )
    ids = torch.full((n, length), pad_id, dtype=torch.long)
    attention = torch.zeros((n, length), dtype=torch.long)
    positions = torch.zeros((n, max_options), dtype=torch.long)
    mask = torch.zeros((n, max_options), dtype=torch.bool)
    target = torch.zeros((n, max_options), dtype=torch.float32)
    for index, item in enumerate(items):
        ids[index, : len(item["ids"])] = torch.tensor(item["ids"])
        attention[index, : len(item["ids"])] = 1
        width = len(item["markers"])
        positions[index, :width] = torch.tensor(item["markers"])
        mask[index, :width] = True
        target[index, :width] = torch.tensor(item["target"])
    return {
        "input_ids": ids,
        "attention_mask": attention,
        "marker_pos": positions,
        "marker_mask": mask,
        "target": target,
        "qtype": torch.tensor([item["qtype"] for item in items]),
    }


def fit_one_temp(rows):
    if len(rows) < 10:
        return 1.0
    width = max(len(logits) for logits, _ in rows)
    logits = torch.full((len(rows), width), -1e4)
    targets = torch.zeros((len(rows), width))
    for index, (z, target) in enumerate(rows):
        logits[index, : len(z)] = torch.tensor(z)
        targets[index, : len(target)] = torch.tensor(target, dtype=torch.float32)
    log_temp = torch.zeros(1, requires_grad=True)
    optimizer = torch.optim.LBFGS([log_temp], lr=0.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        loss = (
            -(targets * torch.log_softmax(logits / log_temp.exp(), -1)).sum(-1).mean()
        )
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(torch.clamp(log_temp.exp(), 0.1, 10.0).item())


def main():
    hp = json.loads((ML / "input/config/hyperparameters.json").read_text())
    seed = int(hp["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if not torch.cuda.is_available():
        raise SystemExit("no CUDA device visible to the training container")
    device = torch.device("cuda")
    started = time.time()
    train_path, calib_path = channel_file("train"), channel_file("calibration")
    train_raw, calib_raw = load_source(train_path), load_source(calib_path)
    base_dir = Path(os.environ.get("LAYA_BASE", "/opt/ml/input/data/model"))
    if not (base_dir / "rl_agent_config.json").is_file():
        raise SystemExit(f"staged Laya checkpoint missing: {base_dir}")
    _fix_tokenizer_config(str(base_dir))
    cfg = json.loads((base_dir / "rl_agent_config.json").read_text())
    cfg["max_len"], cfg["head_max_len"] = HP["max_len"], HP["head_max_len"]
    tok = AutoTokenizer.from_pretrained(str(base_dir / "tokenizer"))
    model = build_model(cfg, encoder_dir=str(base_dir / "encoder"))
    model.load_state_dict(load_file(str(base_dir / "model.safetensors")), strict=True)
    model.encoder.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    model.head_checkpointing = True
    model.to(device).float().train()
    train = [build_item(tok, item) for item in train_raw]
    calib = [build_item(tok, item) for item in calib_raw]
    encoder_params = [
        p for name, p in model.named_parameters() if name.startswith("encoder.")
    ]
    head_params = [
        p for name, p in model.named_parameters() if not name.startswith("encoder.")
    ]
    optimizer = torch.optim.AdamW(
        [
            {"params": encoder_params, "lr": HP["lr_encoder"]},
            {"params": head_params, "lr": HP["lr_head"]},
        ],
        weight_decay=HP["weight_decay"],
    )
    total_updates = (
        math.ceil(len(train) / (HP["micro_batch"] * HP["grad_accum"])) * HP["epochs"]
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, total_updates), eta_min=HP["eta_min"]
    )
    log, step = [], 0
    for epoch in range(HP["epochs"]):
        random.Random(seed + epoch).shuffle(train)
        progress = epoch / max(1, HP["epochs"] - 1)
        sigma = HP["sigma_start"] + (HP["sigma_end"] - HP["sigma_start"]) * progress
        optimizer.zero_grad(set_to_none=True)
        epoch_loss, batches, accumulated = 0.0, 0, 0
        for start in range(0, len(train), HP["micro_batch"]):
            chunk = train[start : start + HP["micro_batch"]]
            batch = {
                key: value.to(device)
                for key, value in collate(chunk, tok.pad_token_id).items()
            }
            logits, act = model(
                batch["input_ids"],
                batch["attention_mask"],
                batch["marker_pos"],
                batch["marker_mask"],
                batch["qtype"],
            )
            logits = logits.float()
            mask = batch["marker_mask"]
            count = mask.sum(-1, keepdim=True).float()
            target = batch["target"]
            noise = (
                torch.randn((HP["group_size"],) + logits.shape, device=device)
                * sigma
                * mask
            )
            noise = (noise - noise.sum(-1, keepdim=True) / count) * mask
            z = logits.detach().unsqueeze(0) + noise
            probabilities = torch.softmax(z.masked_fill(~mask, -1e4), -1)
            with torch.no_grad():
                reward = proper_reward(
                    probabilities,
                    target.unsqueeze(0),
                    batch["qtype"],
                    mask,
                    w_sph=HP["w_sph"],
                    w_rps=HP["w_rps"],
                )
                advantage = reward - reward.mean(0, keepdim=True)
                advantage = advantage / (advantage.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sigma**2)
            loss_rl = -(advantage * logp).mean()
            loss_ce = (
                -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1))
                .sum(-1)
                .mean()
            )
            loss = (loss_rl + HP["ce_weight"] * loss_ce) / HP[
                "grad_accum"
            ] + 0.0 * act.sum()
            loss.backward()
            accumulated += 1
            if accumulated % HP["grad_accum"] == 0 or start + HP["micro_batch"] >= len(
                train
            ):
                torch.nn.utils.clip_grad_norm_(model.parameters(), HP["clip"])
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                step += 1
            epoch_loss += loss.item() * HP["grad_accum"]
            batches += 1
        record = {
            "epoch": epoch + 1,
            "avg_loss": epoch_loss / max(1, batches),
            "sigma": sigma,
            "optimizer_steps": step,
        }
        log.append(record)
        print(json.dumps(record), flush=True)
    wall = time.time() - started
    model.eval()
    by_type = {kind: [] for kind in range(3)}
    truncation = {"train": 0, "calibration": 0}
    for split_name, raw, built in (
        ("train", train_raw, train),
        ("calibration", calib_raw, calib),
    ):
        truncation[split_name] = sum(len(b["ids"]) >= HP["max_len"] for b in built)
    with torch.no_grad():
        for start in range(0, len(calib), 16):
            chunk = calib[start : start + 16]
            batch = {
                key: value.to(device)
                for key, value in collate(chunk, tok.pad_token_id).items()
            }
            logits, _ = model(
                batch["input_ids"],
                batch["attention_mask"],
                batch["marker_pos"],
                batch["marker_mask"],
                batch["qtype"],
            )
            logits = logits.float().cpu().numpy()
            for index, item in enumerate(chunk):
                by_type[item["qtype"]].append(
                    (logits[index, : len(item["markers"])].tolist(), item["target"])
                )
    temperatures = [1.0, 1.0, 1.0]
    for kind, rows in by_type.items():
        if rows:
            temperatures[kind] = fit_one_temp(rows)
    out = MODEL / "model"
    out.mkdir(parents=True, exist_ok=True)
    save_file(
        {
            key: value.half().contiguous().cpu()
            for key, value in model.state_dict().items()
        },
        str(out / "model.safetensors"),
    )
    model.encoder.config.save_pretrained(str(out / "encoder"))
    tok.save_pretrained(str(out / "tokenizer"))
    cfg["fine_tuned"] = True
    cfg["model_name"] = "laya-typed-decisions-slopvac-corpus"
    cfg["temperature"] = temperatures
    cfg.pop("temperature_by_options", None)
    cfg.pop("gradient_checkpointing", None)
    (out / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    manifest = {
        "recipe": "Laya laya_finetune_typed_decisions_2xT4_kaggle RLCD one-GPU port, SageMaker",
        "job_name": os.environ.get("TRAINING_JOB_NAME"),
        "training_job_arn": os.environ.get("TRAINING_JOB_ARN"),
        "model": "laya-typed-decisions",
        "seed": seed,
        "upstream_commit": hp["upstream_commit"],
        "init_from": f"{hp['repo']}@{hp['revision']}",
        "train_sha256": sha256_file(train_path),
        "calibration_sha256": sha256_file(calib_path),
        "hyperparameters": HP,
        "temperature_fit_on_calibration": dict(
            zip(["choice", "score", "noul"], temperatures)
        ),
        "temperature_samples": {
            "choice": len(by_type[0]),
            "score": len(by_type[1]),
            "noul": len(by_type[2]),
        },
        "optimizer_steps": step,
        "epochs_log": log,
        "truncated_records": truncation,
        "hardware": {
            "gpu": torch.cuda.get_device_name(0),
            "gpu_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
            "instance_type": os.environ.get("JUDGE_INSTANCE_TYPE"),
            "cuda": torch.version.cuda,
        },
        "train_wall_time_s": round(wall, 1),
        "input_data_sha256": {
            "train": sha256_file(train_path),
            "calibration": sha256_file(calib_path),
        },
        "files": {
            str(path.relative_to(MODEL)): sha256_file(path)
            for path in sorted(MODEL.rglob("*"))
            if path.is_file()
        },
    }
    (MODEL / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in (
                    "seed",
                    "temperature_fit_on_calibration",
                    "optimizer_steps",
                    "truncated_records",
                )
            },
            indent=2,
        ),
        flush=True,
    )
