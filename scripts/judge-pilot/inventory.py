"""Record on-disk size and parameter counts per arm from the downloaded/fine-tuned files.

    .cache/src/kev/.venv/bin/python inventory.py      # needs torch for Kev's head.pt

Writes results/inventory.json. Parameter counts come from safetensors headers (shapes, no weights
loaded) and head.pt tensors. Kev counts split the Qwen3.5 base into the language model that Kev
runs and the unused vision tower / MTP head that ship in the same checkpoint.
"""

import json
import math
import struct
from pathlib import Path

import torch
from huggingface_hub import snapshot_download

from arms import ARMS, PILOT


# The convaiinnovations/laya repo bundles the other two checkpoints and docs assets in subfolders;
# the English arm serves only the root checkpoint, so only its files count.
LAYA_CHECKPOINT_PARTS = (
    "model.safetensors",
    "encoder",
    "tokenizer",
    "rl_agent_config.json",
)


def files_of(path, laya=False):
    files = [p for p in Path(path).rglob("*") if p.is_file()]
    if laya:
        files = [
            p for p in files if p.relative_to(path).parts[0] in LAYA_CHECKPOINT_PARTS
        ]
    return files


def dir_bytes(path, laya=False):
    return sum(p.stat().st_size for p in files_of(path, laya))


def safetensors_params(path, laya=False):
    counts = {}
    for f in sorted(p for p in files_of(path, laya) if p.suffix == ".safetensors"):
        with open(f, "rb") as fh:
            n = struct.unpack("<Q", fh.read(8))[0]
            header = json.loads(fh.read(n))
        header.pop("__metadata__", None)
        for key, meta in header.items():
            part = key.split(".")[1] if key.startswith("model.") else key.split(".")[0]
            counts[part] = counts.get(part, 0) + math.prod(meta["shape"])
    return counts


def head_params(path):
    obj = torch.load(Path(path) / "head.pt", map_location="cpu", weights_only=True)
    state = obj["head"]
    return sum(v.numel() for v in state.values() if torch.is_tensor(v))


def main():
    inv = {}
    for name, arm in ARMS.items():
        if arm["local"] and not Path(arm["local"]).exists():
            continue
        if arm["family"] == "laya":
            path = arm["local"] or snapshot_download(
                arm["repo"], revision=arm["revision"]
            )
            counts = safetensors_params(path, laya=True)
            inv[name] = {
                "disk_bytes": dir_bytes(path, laya=True),
                "params_total": sum(counts.values()),
                "params_by_part": counts,
            }
        else:
            adapter = arm["local"] or snapshot_download(
                arm["repo"], revision=arm["revision"]
            )
            base = snapshot_download(arm["base"], revision=arm["base_revision"])
            base_counts = safetensors_params(base)
            adapter_counts = safetensors_params(adapter)
            lm = base_counts.get("language_model", 0)
            hp = head_params(adapter)
            inv[name] = {
                "disk_bytes": dir_bytes(adapter) + dir_bytes(base),
                "disk_bytes_adapter": dir_bytes(adapter),
                "disk_bytes_base": dir_bytes(base),
                "params_language_model": lm,
                "params_lora": sum(adapter_counts.values()),
                "params_head": hp,
                "params_total_served": lm + sum(adapter_counts.values()) + hp,
                "params_base_unused": {
                    k: v for k, v in base_counts.items() if k != "language_model"
                },
            }
        print(name, json.dumps(inv[name]))
    (PILOT / "results" / "inventory.json").write_text(json.dumps(inv, indent=2) + "\n")


if __name__ == "__main__":
    main()
