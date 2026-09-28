"""Fine-tune Laya typed-decisions on the pilot train split with Laya's shipped RLCD recipe.

    .cache/laya-venv/bin/python finetune_laya.py

Port of the training script in Laya's notebook
notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb (commit 9d95567, cells 6/8) to one
Apple-silicon device. Kept from the recipe: RLCD loss (4 zero-mean noisy logit samples, proper
scoring reward with w_sph=0.75, w_rps=1.0, advantage-normalised policy gradient + 1.0 soft CE),
AdamW with encoder lr 2.5e-5 / head lr 1e-4 / weight decay 0.01, cosine schedule to 1e-6,
sigma 0.4 -> 0.1, 4 epochs, micro-batch 8, gradient clip 1.0, encoder + head gradient
checkpointing, per-type temperature fit (LBFGS on NLL) and removal of inherited
temperature_by_options. Changed for this host and pilot: one device instead of 2xT4 DDP, so
grad-accum 8 keeps the recipe's effective batch of 64; fp32 instead of CUDA fp16 autocast; the
temperatures are fitted on the pilot calibration split, not on a slice of training items; seed 17.
Training items are built with the same internal question form the server uses (Agent._to_internal).
Writes .cache/runs/ft-laya-typed-decisions/{model/, finetune.json}.
"""

import json
import math
import os
import random
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from huggingface_hub import snapshot_download
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

from arms import ARMS, RUNS
from memory import rusage_footprint

PILOT = Path(__file__).resolve().parent
OUT = RUNS / "ft-laya-typed-decisions"
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
    "max_len": 1024,
    "head_max_len": 256,
    "seed": 17,
    "dtype": "fp32",
    "gradient_checkpointing": True,
}


def api_question(item):
    q = {
        "type": item["question"]["type"],
        "instructions": item["question"]["instructions"],
    }
    if item["kind"] == "choice":
        q["criteria"] = {k: item["question"]["criteria"][k] for k in CHOICE_ORDER}
    return q


def build_item(tok, item):
    q = Agent._to_internal(api_question(item))
    k = len(render_options(q))
    if item["kind"] == "noul":
        target = [0.0, 1.0] if item["label"] else [1.0, 0.0]
    else:
        target = [1.0 if key == item["label"] else 0.0 for key in CHOICE_ORDER]
    seq, markers = build_sequence(
        tok, item["state"], q, HP["max_len"], HP["head_max_len"]
    )[:2]
    assert len(markers) == k
    return {
        "ids": seq,
        "markers": markers,
        "qtype": QTYPES[q["t"]],
        "target": target,
        "label": target.index(1.0),
    }


def collate(items, pad_id):
    n, L, kmax = (
        len(items),
        max(len(i["ids"]) for i in items),
        max(len(i["markers"]) for i in items),
    )
    ids = torch.full((n, L), pad_id, dtype=torch.long)
    att = torch.zeros((n, L), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    target = torch.zeros((n, kmax), dtype=torch.float32)
    for i, it in enumerate(items):
        ids[i, : len(it["ids"])] = torch.tensor(it["ids"])
        att[i, : len(it["ids"])] = 1
        k = len(it["markers"])
        mpos[i, :k] = torch.tensor(it["markers"])
        mmask[i, :k] = True
        target[i, :k] = torch.tensor(it["target"])
    return {
        "input_ids": ids,
        "attention_mask": att,
        "marker_pos": mpos,
        "marker_mask": mmask,
        "target": target,
        "qtype": torch.tensor([it["qtype"] for it in items]),
    }


def fit_one_temp(sel):
    """Laya notebook's per-type temperature fit (LBFGS on NLL), clamped to [0.1, 10]."""
    if len(sel) < 10:
        return 1.0
    kmax = max(len(z) for z, _ in sel)
    Z = torch.full((len(sel), kmax), -1e4)
    T = torch.zeros((len(sel), kmax))
    for i, (z, t) in enumerate(sel):
        Z[i, : len(z)] = torch.tensor(z)
        T[i, : len(t)] = torch.tensor(t, dtype=torch.float32)
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = -(T * torch.log_softmax(Z / log_t.exp(), -1)).sum(-1).mean()
        loss.backward()
        return loss

    opt.step(closure)
    return float(torch.clamp(log_t.exp(), 0.1, 10.0).item())


def load_split(name):
    return [
        json.loads(line)
        for line in (PILOT / "data" / f"{name}.jsonl").read_text().splitlines()
    ]


def main():
    arm = ARMS["laya-typed-decisions"]
    random.seed(HP["seed"])
    np.random.seed(HP["seed"])
    torch.manual_seed(HP["seed"])
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    base_dir = OUT / "base"
    if not base_dir.exists():
        shutil.copytree(
            snapshot_download(arm["repo"], revision=arm["revision"]),
            base_dir,
            symlinks=False,
        )
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

    train = [build_item(tok, it) for it in load_split("train")]
    calib = [build_item(tok, it) for it in load_split("calibration")]
    enc_params = [p for n, p in model.named_parameters() if n.startswith("encoder.")]
    head_params = [
        p for n, p in model.named_parameters() if not n.startswith("encoder.")
    ]
    opt = torch.optim.AdamW(
        [
            {"params": enc_params, "lr": HP["lr_encoder"]},
            {"params": head_params, "lr": HP["lr_head"]},
        ],
        weight_decay=HP["weight_decay"],
    )
    total_updates = (
        math.ceil(len(train) / (HP["micro_batch"] * HP["grad_accum"])) * HP["epochs"]
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=max(1, total_updates), eta_min=HP["eta_min"]
    )
    log, t0, step = [], time.time(), 0
    proc = psutil.Process()
    peak_rss = 0
    for epoch in range(HP["epochs"]):
        random.Random(HP["seed"] + epoch).shuffle(train)
        progress = epoch / max(1, HP["epochs"] - 1)
        sigma = HP["sigma_start"] + (HP["sigma_end"] - HP["sigma_start"]) * progress
        opt.zero_grad(set_to_none=True)
        ep_loss, n_batches, accum = 0.0, 0, 0
        for b in range(0, len(train), HP["micro_batch"]):
            batch = {
                k: v.to(device)
                for k, v in collate(
                    train[b : b + HP["micro_batch"]], tok.pad_token_id
                ).items()
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
            k = mask.sum(-1, keepdim=True).float()
            target = batch["target"]
            eps = (
                torch.randn((HP["group_size"],) + logits.shape, device=device)
                * sigma
                * mask
            )
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mask
            z = logits.detach().unsqueeze(0) + eps
            q = torch.softmax(z.masked_fill(~mask, -1e4), -1)
            with torch.no_grad():
                r = proper_reward(
                    q,
                    target.unsqueeze(0),
                    batch["qtype"],
                    mask,
                    w_sph=HP["w_sph"],
                    w_rps=HP["w_rps"],
                )
                adv = r - r.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mask).sum(-1) / (2 * sigma**2)
            loss_rl = -(adv * logp).mean()
            loss_ce = (
                -(target * torch.log_softmax(logits.masked_fill(~mask, -1e4), -1))
                .sum(-1)
                .mean()
            )
            loss = (loss_rl + HP["ce_weight"] * loss_ce) / HP[
                "grad_accum"
            ] + 0.0 * act.sum()
            loss.backward()
            accum += 1
            if accum % HP["grad_accum"] == 0 or b + HP["micro_batch"] >= len(train):
                torch.nn.utils.clip_grad_norm_(model.parameters(), HP["clip"])
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
            ep_loss += loss.item() * HP["grad_accum"]
            n_batches += 1
            peak_rss = max(peak_rss, proc.memory_info().rss)
        log.append(
            {
                "epoch": epoch + 1,
                "avg_loss": ep_loss / max(1, n_batches),
                "sigma": sigma,
                "elapsed_s": round(time.time() - t0, 1),
                "optimizer_steps": step,
            }
        )
        print(json.dumps(log[-1]), flush=True)
    train_wall = time.time() - t0

    model.eval()
    by_type = {t: [] for t in range(3)}
    with torch.no_grad():
        for b in range(0, len(calib), 16):
            chunk = calib[b : b + 16]
            batch = {
                k: v.to(device) for k, v in collate(chunk, tok.pad_token_id).items()
            }
            z, _ = model(
                batch["input_ids"],
                batch["attention_mask"],
                batch["marker_pos"],
                batch["marker_mask"],
                batch["qtype"],
            )
            z = z.float().cpu().numpy()
            for i, it in enumerate(chunk):
                by_type[it["qtype"]].append(
                    (z[i, : len(it["markers"])].tolist(), it["target"])
                )
    temps = [1.0, 1.0, 1.0]  # [choice, score, noul], the order laya.common.QTYPES uses
    for t, sel in by_type.items():
        if sel:
            temps[t] = fit_one_temp(sel)
    out = OUT / "model"
    out.mkdir(parents=True, exist_ok=True)
    save_file(
        {k: v.half().contiguous().cpu() for k, v in model.state_dict().items()},
        str(out / "model.safetensors"),
    )
    model.encoder.config.save_pretrained(str(out / "encoder"))
    tok.save_pretrained(str(out / "tokenizer"))
    cfg["fine_tuned"] = True
    cfg["model_name"] = "laya-typed-decisions-slopvac-pilot"
    cfg["temperature"] = temps
    cfg.pop("temperature_by_options", None)
    cfg.pop("gradient_checkpointing", None)
    (out / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    meta = {
        "recipe": "Laya notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb (RLCD), ported to one device",
        "upstream_commit": arm["upstream_commit"],
        "init_from": f"{arm['repo']}@{arm['revision']}",
        "hyperparameters": HP,
        "train_items": len(train),
        "calibration_items": len(calib),
        "optimizer_steps": step,
        "epochs_log": log,
        "temperatures_fit_on_calibration": dict(
            zip(["choice", "score", "noul"], temps)
        ),
        "wall_time_s": round(train_wall, 1),
        "device": str(device),
        "peak_rss_bytes_sampled": peak_rss,
        **(rusage_footprint(os.getpid()) or {}),
        "torch": torch.__version__,
    }
    (OUT / "finetune.json").write_text(json.dumps(meta, indent=2))
    print(
        json.dumps(
            {
                k: meta[k]
                for k in (
                    "wall_time_s",
                    "temperatures_fit_on_calibration",
                    "optimizer_steps",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
