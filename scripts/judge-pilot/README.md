# Local judging pilot: Laya and Kev on slopvac rule examples

This directory holds a pilot benchmark for slopvac's local judging default model
(`packages/slopvac-lint/docs/design/local-judging.md`). It serves every published Laya checkpoint
and every Kev size that fits this host through the project's own Jev-compatible server. It
queries each server over `POST /v1/systemone` and scores the answers.

The pilot set is made of minimal pairs built from rule examples. It is not the spec's
adjudicated corpus. Its numbers do not show prose-judging quality, and no arm should be
chosen on them alone.

## Layout

| File | Role |
|---|---|
| `build_dataset.py` | Builds `data/{train,calibration,test}.jsonl` from rule `examples` and writes `results/dataset-manifest.json` (SHA-256 digests, portable-profile check) |
| `arms.py` | Arm registry: Hub repo and full revision SHA of every checkpoint and Qwen base |
| `download_models.py` | Downloads every checkpoint at its pinned revision into `~/.cache/huggingface` |
| `serve_arm.py` | Starts one arm's server. Records its pid and load time (process start to first HTTP 200) |
| `laya_server.py` | `laya.serve.create_app` over a Router that holds one checkpoint |
| `run_arm.py`, `compat.py`, `memory.py` | HTTP harness, Jev wire probe, and peak-memory capture (sampled RSS plus macOS `phys_footprint`) |
| `metrics.py` | Computes metrics and temperature scaling and writes `results/<arm>.json` |
| `inventory.py` | Records disk size and parameter counts in `results/inventory.json` |
| `finetune_laya.py`, `finetune_kev.py` | Local ports of each project's shipped fine-tuning recipe (not executed yet, see below) |
| `requirements-*.txt` | Pinned dependencies for the harness and the Laya environment. Kev uses its own `uv.lock` at the pinned commit |

Upstream code is pinned to Laya `9d955671415fc19f069b9cc998928075c1f255ec` and Kev
`3e1cd3bb588a388a06827443380befece23e68c7`.

## Reproduce

Run these commands from this directory. Nothing is installed into the slopvac package.

```bash
mkdir -p .cache/src
git clone https://github.com/NandhaKishorM/laya .cache/src/laya && git -C .cache/src/laya checkout 9d955671415fc19f069b9cc998928075c1f255ec
git clone https://github.com/jaredpalmer/kev .cache/src/kev && git -C .cache/src/kev checkout 3e1cd3bb588a388a06827443380befece23e68c7
uv sync --extra serve --project .cache/src/kev
uv venv --python 3.12 .cache/laya-venv
uv pip install --python .cache/laya-venv/bin/python -r requirements-laya.txt
uv pip install --python .cache/laya-venv/bin/python --no-deps -e .cache/src/laya

H="uv run --no-project --with-requirements requirements-harness.txt python"
$H build_dataset.py
.cache/src/kev/.venv/bin/python download_models.py
HF_HUB_OFFLINE=1 .cache/src/kev/.venv/bin/python inventory.py

# Per arm: start the server in one terminal and stop it (Ctrl-C) when the run finishes.
HF_HUB_OFFLINE=1 python3 serve_arm.py kev-0.8b 8104
# In a second terminal:
$H run_arm.py kev-0.8b --port 8104 && $H metrics.py kev-0.8b
```

The arm names are `laya-english`, `laya-multilingual`, `laya-typed-decisions`, `kev-0.8b`,
`kev-4b`, and `kev-9b`. Fine-tuned arms (`laya-typed-decisions-ft`, `kev-0.8b-ft`, `kev-4b-ft`)
are served from `.cache/runs/ft-*` after these commands:

```bash
.cache/laya-venv/bin/python finetune_laya.py
.cache/src/kev/.venv/bin/python finetune_kev.py kev-0.8b
```

## Method

- **Items:** each rule example pair yields a `noul` item for each sentence (bad is true, good
  is false). It also yields a three-option `choice` item for each sentence (`real-defect`,
  `no-defect`, `insufficient-context`). Each bad sentence is also asked about one unrelated
  rule, which gives a hard negative. That rule comes from a different category in the same
  split, and its regex does not match the sentence. Positives to negatives in `noul` are 1:2.
- **Splits:** grouped by rule id with seed 17: 60% train, 15% calibration, 25% test.
- **Requests:** each request carries one question. The order of all requests is shuffled with
  seed 17. Each choice item is sent twice, once with the options in forward order and once
  reversed, to measure order-swap agreement. Latency is measured once per request by the
  client, after three warm-up requests. Throughput is measured with 16 concurrent clients over
  the test requests.
- **Calibration:** "raw" is the distribution as the server returns it, with each project's
  shipped temperature applied. "cal" applies one temperature per question type, fitted by NLL
  on the calibration split. ECE uses top-label confidence over 15 bins. The 95% intervals come
  from a bootstrap over test rules.
