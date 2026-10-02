# judge-sagemaker: Kev 4B and 9B fine-tunes as SageMaker training jobs

This package submits one Kev delta fine-tune at a time as a SageMaker training job and fetches
its outputs. It implements the Compute section of
`packages/slopvac-lint/docs/design/local-judging.md` for Kev 4B and 9B: `ml.g6e` with one
48 GB L40S, `us-east-1`, a maximum runtime per job, outputs in the corpus bucket, and one job at
a time. It creates training jobs only: no endpoints, notebooks, or EC2 instances. Nothing trains
or runs inference on the local machine.

The training recipe is judge-pilot's `finetune_kev.py`, itself a port of `run_train` in Kev's
`skills/kev-finetune/scripts/kev_modal.py` at Kev commit
`3e1cd3bb588a388a06827443380befece23e68c7`. The job builds the same `kev.train` command from the
init checkpoint's recorded arguments, with `--device cuda --dtype bf16` as Kev's GPU recipe runs it.

## Layout

| Path | Role |
|---|---|
| `src/judge_sagemaker/cli.py` | `judge-sagemaker` command: `submit`, `fetch`, `stop`, `convert` |
| `src/judge_sagemaker/convert.py` | Deterministic JSONL conversion (the pilot's `to_kev`); runs locally and in the job |
| `src/judge_sagemaker/container/bootstrap.sh` | Container start: checks out Kev, installs its locked dependencies, runs `entry.py` |
| `src/judge_sagemaker/container/entry.py` | Converts the data, runs `kev.train`, fits the calibration temperature, writes `manifest.json` |
| `src/judge_sagemaker/container/requirements-kev.txt` | Kev's `uv.lock` closure with hashes, minus the torch stack the image provides |
| `src/judge_sagemaker/container/requirements-fla.txt` | `flash-linear-attention` 0.5.2, the version Kev's Modal images pin |
| `resources.json` | Account, profile, region, bucket, role, image, instance types, prices, runtimes, tags |
| `cost-ledger.json` | Every submitted job and its maximum and billed cost against the USD cap |
| `pyproject.toml`, `uv.lock` | The local CLI's pinned dependencies (`boto3`) |

## Commands

Run from this directory. `uv run` installs the pinned CLI environment.

```bash
uv run judge-sagemaker submit --model kev-4b --data ../../path/to/train.jsonl --epochs 1 --seed 17 --dry-run
uv run judge-sagemaker submit --model kev-4b --data s3://<bucket>/<key>.jsonl --epochs 1 --seed 17
uv run judge-sagemaker fetch <job> [--logs 200]
uv run judge-sagemaker stop <job>
uv run judge-sagemaker convert --data train.jsonl --out train.kev.jsonl
```

`submit` options: `--calibration <s3 uri | local jsonl>` fits the temperature on that split in
the job and writes it into `head.pt`. `--lr` (0 uses the checkpoint's rate capped at 5e-5),
`--replay` (default 2000 records of Kev's decision-v7 training partition; 0 disables it),
`--p-none-pair` (default 0.25), `--max-state` (passes `kev.train --max_state`), and
`--batch`, `--accum`, `--checkpointing`, `--dtype`, and `--weights-dtype` override the saved
checkpoint training recipe; omit these to keep its batch and precision settings. `--max-runtime`
seconds (default from `resources.json`), `--instance-type`, and `--profile` select the job
resources. `--dry-run` prints the plan and `CreateTrainingJob` request without AWS calls.
### GPU evaluation

`evaluate` runs the judge-pilot harness on a SageMaker training GPU. It starts one Jev-compatible server inside the job, probes the local API, runs single-client sequential calibration/test requests, then stops the server. It skips concurrent throughput.

```sh
JUDGE_SAGEMAKER_RESOURCES=resources.json uv run judge-sagemaker evaluate --arm kev-0.8b --dry-run
JUDGE_SAGEMAKER_RESOURCES=resources.json uv run judge-sagemaker evaluate --arm kev-0.8b
JUDGE_SAGEMAKER_RESOURCES=resources.json uv run judge-sagemaker fetch-eval <job>
JUDGE_SAGEMAKER_RESOURCES=resources.json uv run judge-sagemaker evaluate --arm kev-9b
```

`--checkpoint` selects a local fine-tuned pilot run directory or an S3 `model.tar.gz` for an `*-ft-sN` arm. Fine-tuned Kev 4B/9B arms otherwise use a completed SageMaker training job recorded in the shared cost ledger. Laya and Kev 0.8B fine-tuned arms use local pilot caches and upload dereferenced checkpoint contents to S3.

`evaluate` uploads the test and calibration splits, dataset manifest, pilot runner, pinned dependencies, and an optional checkpoint into a job-specific `training/<job>/` prefix. It checks the shared cost ledger before submission and sets `MaxRuntimeInSeconds` to at most 7200 seconds. `fetch-eval` records billed instance time and cost, then downloads metrics, predictions, server logs, inventory, manifest, and compatibility probe beneath `results/<arm>/`.

Choose resources by region with `JUDGE_SAGEMAKER_RESOURCES`. The task account has AWS-published quotas for `ml.g6.xlarge`, `ml.g6.2xlarge`, and `ml.g6.4xlarge` in `us-east-1`, and for g6e instances in `us-west-2`. Their on-demand SageMaker Training prices are estimates in the resource files, not verified public Training SKU rates. Use the report manifest to identify the GPU used for each arm.

### Campaign reports

`scripts/corpus_eval_report.py` renders `results/<campaign results>/REPORT.md` once every arm of a campaign has fetched results. It leads with per-role (finding-confirmation, semantic-detection) balanced accuracy, class recalls, ECE, GPU, latency and cost per arm and seed mean ± SD, then fine-tune-vs-base deltas, a comparison with `--compare` (a campaign on the same test export; it also supplies base arms the campaign does not evaluate), and every ledger job the campaign submitted with failed and stopped attempts. It refuses to render while an arm is missing. `--note` adds a status line. The committed reports were generated with:

```sh
V4="Pre-v4 baseline. v4 rebuilds the judge items against the merged lint rules (main 7544c168e0: curly-quotes and uniform-paragraph-mass retired, about 13 rules narrowed) and the human-labelled rows, then re-tests every arm on the rebuilt items; v4 scores are not comparable with this test export."
V3="The v3 full and confident variants differ only in training data: confident drops teacher-panel labels below 0.85 posterior confidence (12,185 train rows vs 14,449; see each variant's export-manifest.json)."
uv run --frozen python scripts/corpus_eval_report.py --note "$V4"
uv run --frozen python scripts/corpus_eval_report.py --campaign campaigns/v3-full.json --compare campaigns/v3-confident.json --note "$V4" --note "$V3"
uv run --frozen python scripts/corpus_eval_report.py --campaign campaigns/v3-confident.json --compare campaigns/v3-full.json --note "$V4" --note "$V3"
```

### What `submit` does

1. It validates the input. A local file is converted in full, so a malformed row fails before any
   spend. An S3 object is checked in the job.
2. It checks the budget. The job's maximum cost is the hourly price times the maximum runtime. The
   ledger must hold no job that has not been fetched in a final state. The committed spend plus
   this job's maximum must stay within `cap_usd`.
3. It checks that the profile resolves to the account in `resources.json`. It checks that no
   `slopvac-judge` job is `InProgress` or `Stopping`.
4. It uploads the code files to `s3://<bucket>/training/<job>/input/code/`. It uploads or copies
   the data (server-side copy for S3) to `input/train/` and `input/calibration/`.
5. It records the job in `cost-ledger.json` and then calls `CreateTrainingJob`. The call uses the
   stock DLC image, `ContainerEntrypoint` `bash .../bootstrap.sh`, `MaxRuntimeInSeconds`, and
   network isolation off, because the job fetches Kev, PyPI wheels, and Hugging Face weights.

`fetch` records the status, `BillableTimeInSeconds`, and billed cost (billable seconds times the
same hourly price) in the ledger. When the job has completed, it downloads `model.tar.gz` to
`.cache/jobs/<job>/` and extracts it there.

## Data

`--data` and `--calibration` each name one JSONL file in one of two formats:

- **source:** judge-pilot items from `build_dataset.py`, with `id`, `kind` (`noul` or `choice`),
  `state`, `label`, and `question`. Each item becomes one Kev request through the pilot's
  `to_kev`: choice criteria are kept in the order `real-defect`, `no-defect`,
  `insufficient-context`.
- **kev:** rows already in Kev's labelled request schema (`state` and `questions`). They pass
  through unchanged.

A file that mixes formats, holds an unknown row, or lacks a choice criterion is rejected. The
output is written in input order with `json.dumps` defaults. A pilot split converts to the same
bytes the pilot's `write_kev_data` wrote.

## Job outputs

`model.tar.gz` holds:

- `checkpoint/`: the servable Kev run, with `adapter_model.safetensors`, `adapter_config.json`,
  `head.pt`, tokenizer files, `training_config.json`, and `training_metrics.json`
- `data/`: the converted splits
- `train.log`
- `calibration-eval/`: raw-logit predictions on the calibration split, when one was given
- `manifest.json`: job name and ARN, model, Kev commit, `init_from`, base and base revision,
  hyperparameters, seed, the `kev.train` command, input and converted data digests, fitted
  temperature, Kev's training metrics, GPU, CUDA, Python and package versions, wall times, a cost
  estimate (container wall time times the hourly price), and the SHA-256 of every output file

When the job fails, `/opt/ml/output/failure` carries the error, which appears as the
`FailureReason` that `fetch` prints.

## Container dependencies

`bootstrap.sh` fetches Kev at the pinned commit from GitHub. It checks the `uv.lock` digest and
that the image's torch is Kev's locked 2.8.0. It then installs both requirement files with
`pip --no-deps --require-hashes --only-binary=:all:`. Kev requires torch `<2.9`, so the image
stays on the PyTorch 2.8 DLC. To regenerate `requirements-kev.txt` from a Kev checkout at the
pinned commit, run:

```bash
uv export --frozen --no-dev --no-emit-project --no-header --format requirements-txt \
  --project <kev checkout> --no-emit-package torch --no-emit-package triton \
  $(for p in cublas cuda-cupti cuda-nvrtc cuda-runtime cudnn cufft cufile curand cusolver cusparse \
    cusparselt nccl nvjitlink nvtx; do printf -- '--no-emit-package nvidia-%s-cu12 ' "$p"; done) \
  -o src/judge_sagemaker/container/requirements-kev.txt
```

Then restore the provenance header and update the digest in `bootstrap.sh`.

## Limits

- **Hourly price:** the `resources.json` price is an estimate. See its `price_source`.
  Reconcile the ledger against Cost Explorer. Only SageMaker instance time is tracked; S3 and
  CloudWatch costs are not.
- **GPU memory:** Kev-4B's released training run peaked at 47.7 GB on an 80 GB GPU with long
  replay records. That is at the L40S limit. For a first run, use `--replay 0` or `--max-state`.
  Kev-9B's run peaked at 38 GB of GPU memory and 60.5 GB of host memory, against 64 GiB on
  `ml.g6e.2xlarge`.
- **Network:** the job needs outbound access to GitHub, PyPI, and the Hugging Face Hub. Kev-9B
  downloads about 18 GB of base weights at start.
- **Service quota:** the account needs `ml.g6e.2xlarge for training job usage` quota of at least 1.
