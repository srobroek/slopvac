#!/usr/bin/env bash
# Container start for a judge-sagemaker training job on the stock AWS PyTorch training DLC.
# Checks out Kev at the pinned commit, installs its locked dependencies on top of the DLC's
# torch, then runs the entry point. Runs as `bash <code channel>/judge_sagemaker/container/bootstrap.sh`.
set -euo pipefail

CODE=/opt/ml/input/data/code
KEV_COMMIT="$(python -c 'import json; print(json.load(open("/opt/ml/input/config/hyperparameters.json"))["kev_commit"])')"
KEV_LOCK_SHA256=a9922dbb89acdef78299fd2b4a8c3f7f0fa1b2bc08b55595b6926fa785a9c466
export KEV_ROOT=/opt/kev
export HF_HOME="${HF_HOME:-/tmp/hf}"
export TRITON_CACHE_DIR="$HF_HOME/triton-cache"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p "$HF_HOME"

echo "bootstrap: kev ${KEV_COMMIT} into ${KEV_ROOT}; HF_HOME=${HF_HOME}"
git init --quiet "$KEV_ROOT"
git -C "$KEV_ROOT" fetch --quiet --depth 1 https://github.com/jaredpalmer/kev "$KEV_COMMIT"
git -C "$KEV_ROOT" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$KEV_ROOT" rev-parse HEAD)" = "$KEV_COMMIT"
echo "${KEV_LOCK_SHA256}  ${KEV_ROOT}/uv.lock" | sha256sum --check --status ||
  {
    echo "bootstrap: Kev uv.lock digest differs from requirements-kev.txt's source" >&2
    exit 1
  }

python - <<'EOF'
import sys, torch
if sys.version_info < (3, 12) or sys.version_info >= (3, 14):
    raise SystemExit(f"Kev needs Python >=3.12,<3.14; the image has {sys.version.split()[0]}")
if torch.__version__.split("+")[0] != "2.8.0":
    raise SystemExit(f"Kev's uv.lock pins torch 2.8.0; the image has {torch.__version__}")
print(f"bootstrap: python {sys.version.split()[0]}, torch {torch.__version__}, cuda {torch.version.cuda}", flush=True)
EOF

python -m pip install --quiet --no-deps --require-hashes --only-binary=:all: \
  -r "$CODE/judge_sagemaker/container/requirements-kev.txt" \
  -r "$CODE/judge_sagemaker/container/requirements-fla.txt"

export PYTHONPATH="$CODE${PYTHONPATH:+:$PYTHONPATH}"
exec python -m judge_sagemaker.container.entry
