#!/usr/bin/env bash
set -euo pipefail
CODE=/opt/ml/input/data/code
HP=/opt/ml/input/config/hyperparameters.json
FAMILY="$(python -c 'import json; print(json.load(open("/opt/ml/input/config/hyperparameters.json"))["family"])')"
KEV_COMMIT="$(python -c 'import json; print(json.load(open("/opt/ml/input/config/hyperparameters.json"))["kev_commit"])')"
LAYA_COMMIT="$(python -c 'import json; print(json.load(open("/opt/ml/input/config/hyperparameters.json")).get("laya_commit", "9d955671415fc19f069b9cc998928075c1f255ec"))')"
KEV_LOCK_SHA256=a9922dbb89acdef78299fd2b4a8c3f7f0fa1b2bc08b55595b6926fa785a9c466
export HF_HOME="${HF_HOME:-/tmp/hf}" TRITON_CACHE_DIR="${HF_HOME:-/tmp/hf}/triton-cache"
export HF_HUB_DISABLE_PROGRESS_BARS=1 TOKENIZERS_PARALLELISM=false PYTHONUNBUFFERED=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True PIP_DISABLE_PIP_VERSION_CHECK=1
mkdir -p "$HF_HOME"

checkout() {
  git init --quiet "$2"
  git -C "$2" fetch --quiet --depth 1 "$1" "$3"
  git -C "$2" checkout --quiet --detach FETCH_HEAD
  test "$(git -C "$2" rev-parse HEAD)" = "$3"
}

case "$FAMILY" in
kev)
  export KEV_ROOT=/opt/kev
  checkout https://github.com/jaredpalmer/kev "$KEV_ROOT" "$KEV_COMMIT"
  echo "${KEV_LOCK_SHA256}  ${KEV_ROOT}/uv.lock" | sha256sum --check --status || {
    echo "bootstrap: Kev uv.lock digest differs from requirements-kev.txt's source" >&2
    exit 1
  }
  python - <<'EOF'
import sys, torch
if sys.version_info < (3, 12) or sys.version_info >= (3, 14):
    raise SystemExit(f"Kev needs Python >=3.12,<3.14; image has {sys.version.split()[0]}")
if torch.__version__.split("+")[0] != "2.8.0":
    raise SystemExit(f"Kev uv.lock pins torch 2.8.0; image has {torch.__version__}")
if not torch.cuda.is_available():
    raise SystemExit("no CUDA device visible to training container")
EOF
  python -m pip install --quiet --no-deps --require-hashes --only-binary=:all: \
    -r "$CODE/judge_sagemaker/container/requirements-kev.txt" \
    -r "$CODE/judge_sagemaker/container/requirements-fla.txt"
  exec env KEV_ROOT="$KEV_ROOT" PYTHONPATH="$CODE${PYTHONPATH:+:$PYTHONPATH}" \
    python -m judge_sagemaker.container.entry
  ;;
laya)
  export LAYA_ROOT=/opt/laya LAYA_BASE=/opt/laya-base LAYA_PY=/opt/laya-venv/bin/python
  checkout https://github.com/NandhaKishorM/laya "$LAYA_ROOT" "$LAYA_COMMIT"
  mkdir -p "$LAYA_BASE"
  cp -a /opt/ml/input/data/model/. "$LAYA_BASE/"
  python -m venv /opt/laya-venv
  "$LAYA_PY" -m pip install --quiet --only-binary=:all: \
    --extra-index-url https://download.pytorch.org/whl/cu126 \
    -r "$CODE/judge_sagemaker/pilot/requirements-laya.txt" "torch==2.14.0+cu126"
  "$LAYA_PY" -m pip install --quiet --no-deps --no-build-isolation -e "$LAYA_ROOT"
  "$LAYA_PY" -m pip check
  exec env PYTHONPATH="$CODE${PYTHONPATH:+:$PYTHONPATH}" \
    "$LAYA_PY" "$CODE/judge_sagemaker/container/laya_train.py"
  ;;
*)
  echo "bootstrap: unknown family $FAMILY" >&2
  exit 1
  ;;
esac
