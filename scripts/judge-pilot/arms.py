"""Arm registry: which checkpoint each arm serves, at which pinned revision, and how.

Every arm is served by its project's own Jev-compatible server and queried over HTTP.
Revisions are full commit SHAs observed on the Hub on 2026-09-28.
"""

from pathlib import Path

PILOT = Path(__file__).resolve().parent
CACHE = PILOT / ".cache"
RUNS = CACHE / "runs"
KEV_SRC = CACHE / "src" / "kev"
LAYA_SRC = CACHE / "src" / "laya"
KEV_PY = KEV_SRC / ".venv" / "bin" / "python"
LAYA_PY = CACHE / "laya-venv" / "bin" / "python"

KEV_COMMIT = "3e1cd3bb588a388a06827443380befece23e68c7"
LAYA_COMMIT = "9d955671415fc19f069b9cc998928075c1f255ec"

LAYA_REVS = {
    "convaiinnovations/laya": "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851",
    "convaiinnovations/laya-multilingual": "e4e9ddf21a7b1903b7acffd8814ad4307bf63a67",
    "convaiinnovations/laya-typed-decisions": "1a793eb568e6718f15941d08f85432581df534e3",
}
KEV_REVS = {
    "jaredpalmer/kev-0.8b": "9a45d25eb2ab761841196625383fa1dff0e56c1e",
    "jaredpalmer/kev-4b": "139fdd94f1b6a6ad80cc15e08fcb99cac885a101",
    "jaredpalmer/kev-9b": "2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c",
}
# Base revisions pinned by each Kev checkpoint's training_config.json.
QWEN_REVS = {
    "Qwen/Qwen3.5-0.8B-Base": "dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68",
    "Qwen/Qwen3.5-4B-Base": "1001bb4d826a52d1f399e183466143f4da7b741b",
    "Qwen/Qwen3.5-9B-Base": "68c46c4b3498877f3ef123c856ecfde50c39f404",
}


def _laya(repo, checkpoint, local=None):
    return {
        "family": "laya",
        "model": checkpoint,  # the `model` field Laya's server honours
        "repo": repo,
        "revision": LAYA_REVS[repo],
        "checkpoint": checkpoint,
        "local": local,
        "downloads": [(repo, LAYA_REVS[repo])],
        "upstream_commit": LAYA_COMMIT,
    }


def _kev(repo, base, local=None):
    return {
        "family": "kev",
        "model": "kev-latest",
        "repo": repo,
        "revision": KEV_REVS[repo],
        "base": base,
        "base_revision": QWEN_REVS[base],
        "local": local,
        "downloads": [(repo, KEV_REVS[repo]), (base, QWEN_REVS[base])],
        "upstream_commit": KEV_COMMIT,
    }


ARMS = {
    "laya-english": _laya("convaiinnovations/laya", "english"),
    "laya-multilingual": _laya("convaiinnovations/laya-multilingual", "multilingual"),
    "laya-typed-decisions": _laya(
        "convaiinnovations/laya-typed-decisions", "typed-decisions"
    ),
    "kev-0.8b": _kev("jaredpalmer/kev-0.8b", "Qwen/Qwen3.5-0.8B-Base"),
    "kev-4b": _kev("jaredpalmer/kev-4b", "Qwen/Qwen3.5-4B-Base"),
    "kev-9b": _kev("jaredpalmer/kev-9b", "Qwen/Qwen3.5-9B-Base"),
}
# Post-trained arms: one per (base arm, training seed). finetune_*.py writes the run directory
# .cache/runs/ft-<base>-s<seed>/ (finetune.json, logs) with the servable weights in model/ (Laya)
# or checkpoint/ (Kev).
FT_BASES = {
    "laya-typed-decisions": "model",
    "kev-0.8b": "checkpoint",
    "kev-4b": "checkpoint",
}
FT_SEEDS = (17, 18, 19)


def ft_run(base, seed):
    return RUNS / f"ft-{base}-s{seed}"


for _base, _sub in FT_BASES.items():
    for _seed in FT_SEEDS:
        _src = ARMS[_base]
        _ft = (_laya if _src["family"] == "laya" else _kev)(
            _src["repo"],
            _src["checkpoint"] if _src["family"] == "laya" else _src["base"],
            local=str(ft_run(_base, _seed) / _sub),
        )
        _ft.update(ft_base=_base, ft_seed=_seed, ft_run=str(ft_run(_base, _seed)))
        ARMS[f"{_base}-ft-s{_seed}"] = _ft
for _arm in ARMS.values():
    if _arm["local"]:
        _arm["downloads"] = []
