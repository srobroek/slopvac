#!/usr/bin/env bash
# Container start for a judge-sagemaker evaluation job on the stock AWS PyTorch training DLC.
# Builds the evaluated family's pinned environment, then runs eval_entry.py, which serves the arm on
# localhost and runs the pilot harness against it. Runs as
# `bash <code channel>/judge_sagemaker/container/eval_bootstrap.sh`.
#   Kev:  Kev at KEV_COMMIT; its uv.lock closure with the serve extra (requirements-kev-serve.txt,
#         --require-hashes) and flash-linear-attention on the DLC's torch 2.8.0, which the lock pins.
#   Laya: Laya at LAYA_COMMIT in its own Python 3.12 venv with the pilot's requirements-laya.txt.
#         torch is 2.14.0 as the pilot locked, from the CUDA 12.6 wheel index: download.pytorch.org
#         has no 2.14.0+cu129 build (cu129 stops at 2.13.0), and the cu126 runtime runs on the
#         driver the cu12.9 DLC needs.
#   Clef: no checkout (joint_schema_model.py ships in the pinned Hub revision); transformers 5.10.2,
#         the release's tested version, with requirements-clef.txt (--require-hashes) and
#         flash-linear-attention on the DLC's torch 2.8.0. The model card tested torch 2.11;
#         transformers 5.10.2 needs torch>=2.4, so the job keeps the image's torch.
#   Harness: its own venv with the pilot's requirements-harness.txt (run_arm.py, metrics.py).
set -euo pipefail

CODE=/opt/ml/input/data/code
HP=/opt/ml/input/config/hyperparameters.json
hp() { python -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$HP" "$1"; }
FAMILY="$(hp family)"
KEV_COMMIT="$(hp kev_commit)"
LAYA_COMMIT="$(hp laya_commit)"
KEV_LOCK_SHA256=a9922dbb89acdef78299fd2b4a8c3f7f0fa1b2bc08b55595b6926fa785a9c466
LAYA_TORCH="torch==2.14.0+cu126"
LAYA_TORCH_INDEX=https://download.pytorch.org/whl/cu126

export JUDGE_EVAL_OUT=/opt/ml/model JUDGE_FT_ROOT=/opt/judge/ft
export KEV_ROOT=/opt/kev LAYA_ROOT=/opt/laya
export KEV_PY="$(command -v python)" LAYA_PY=/opt/laya-venv/bin/python HARNESS_PY=/opt/harness-venv/bin/python
export CLEF_PY="$(command -v python)"
export JUDGE_LAYA_TORCH="$LAYA_TORCH" JUDGE_LAYA_TORCH_INDEX="$LAYA_TORCH_INDEX"
export HF_HOME="${HF_HOME:-/tmp/hf}"
export TRITON_CACHE_DIR="$HF_HOME/triton-cache"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
mkdir -p "$HF_HOME" "$JUDGE_FT_ROOT"

checkout() { # repo commit dir
  git init --quiet "$3"
  git -C "$3" fetch --quiet --depth 1 "$1" "$2"
  git -C "$3" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$3" rev-parse HEAD)" = "$2"
}

echo "eval-bootstrap: family ${FAMILY}; HF_HOME=${HF_HOME}"
python -m venv /opt/harness-venv
"$HARNESS_PY" -m pip install --quiet --no-deps --only-binary=:all: \
  -r "$CODE/judge_sagemaker/pilot/requirements-harness.txt"

case "$FAMILY" in
kev)
  checkout https://github.com/jaredpalmer/kev "$KEV_COMMIT" "$KEV_ROOT"
  echo "${KEV_LOCK_SHA256}  ${KEV_ROOT}/uv.lock" | sha256sum --check --status ||
    {
      echo "eval-bootstrap: Kev uv.lock digest differs from requirements-kev-serve.txt's source" >&2
      exit 1
    }
  python - <<'EOF'
import sys, torch
if sys.version_info < (3, 12) or sys.version_info >= (3, 14):
    raise SystemExit(f"Kev needs Python >=3.12,<3.14; the image has {sys.version.split()[0]}")
if torch.__version__.split("+")[0] != "2.8.0":
    raise SystemExit(f"Kev's uv.lock pins torch 2.8.0; the image has {torch.__version__}")
if not torch.cuda.is_available():
    raise SystemExit("no CUDA device visible to the DLC torch")
EOF
  python -m pip install --quiet --no-deps --require-hashes --only-binary=:all: \
    -r "$CODE/judge_sagemaker/container/requirements-kev-serve.txt" \
    -r "$CODE/judge_sagemaker/container/requirements-fla.txt"
  ;;
laya)
  checkout https://github.com/NandhaKishorM/laya "$LAYA_COMMIT" "$LAYA_ROOT"
  python -m venv /opt/laya-venv
  "$LAYA_PY" -m pip install --quiet --only-binary=:all: --extra-index-url "$LAYA_TORCH_INDEX" \
    -r "$CODE/judge_sagemaker/pilot/requirements-laya.txt" "$LAYA_TORCH"
  "$LAYA_PY" -m pip install --quiet --no-deps --no-build-isolation -e "$LAYA_ROOT"
  "$LAYA_PY" -m pip check
  "$LAYA_PY" - <<'EOF'
import torch
if not torch.cuda.is_available():
    raise SystemExit(f"torch {torch.__version__} in the Laya venv sees no CUDA device")
print(f"eval-bootstrap: laya venv torch {torch.__version__}, cuda {torch.version.cuda}", flush=True)
EOF
  ;;
clef)
  python - <<'EOF'
import sys, torch, torchvision, PIL
if sys.version_info[:2] != (3, 12):
    raise SystemExit(f"requirements-clef.txt targets Python 3.12; the image has {sys.version.split()[0]}")
if torch.__version__.split("+")[0] != "2.8.0":
    raise SystemExit(f"requirements-clef.txt resolves against torch 2.8.0; the image has {torch.__version__}")
if not torch.cuda.is_available():
    raise SystemExit("no CUDA device visible to the DLC torch")
EOF
  python -m pip install --quiet --no-deps --require-hashes --only-binary=:all: \
    -r "$CODE/judge_sagemaker/container/requirements-clef.txt" \
    -r "$CODE/judge_sagemaker/container/requirements-fla.txt"
  python - <<'EOF'
import accelerate, torch, torchvision, transformers
from transformers.utils.import_utils import is_flash_linear_attention_available
if transformers.__version__ != "5.10.2":
    raise SystemExit(f"Clef needs transformers 5.10.2; installed {transformers.__version__}")
print(f"eval-bootstrap: clef on torch {torch.__version__} (cuda {torch.version.cuda}), "
      f"torchvision {torchvision.__version__}, transformers {transformers.__version__}, "
      f"accelerate {accelerate.__version__}, {torch.cuda.device_count()} GPU(s), "
      f"fla kernels {is_flash_linear_attention_available()}", flush=True)
EOF
  ;;
*)
  echo "eval-bootstrap: unknown family ${FAMILY}" >&2
  exit 1
  ;;
esac

export PYTHONPATH="$CODE${PYTHONPATH:+:$PYTHONPATH}"
exec "$HARNESS_PY" -m judge_sagemaker.container.eval_entry
