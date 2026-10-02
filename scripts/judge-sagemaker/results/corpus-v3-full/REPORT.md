# Corpus evaluation report: `corpus-v3-full`

## Status

- Pre-v4 baseline. v4 rebuilds the judge items against the merged lint rules (main 7544c168e0: curly-quotes and uniform-paragraph-mass retired, about 13 rules narrowed) and the human-labelled rows, then re-tests every arm on the rebuilt items; v4 scores are not comparable with this test export.
- The v3 full and confident variants differ only in training data: confident drops teacher-panel labels below 0.85 posterior confidence (12,185 train rows vs 14,449; see each variant's export-manifest.json).

## Dataset and coverage

- Campaign: `corpus-20260930-s17-v3/full`. Round 2 on the v3 export (full). Base arms are evaluated in the full campaign only: both variants share test and calibration. Laya fine-tunes are left out until round 1 shows Laya fine-tuning beats its base.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 15 of 15 required (`kev-0.8b`, `kev-4b`, `kev-9b`, `laya-english`, `laya-multilingual`, `laya-typed-decisions`, `kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 1 of 25 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1674 examples; SHA-256 `fca2452aa1e15bb80bc10514699e3495cbed42a690626cc5aaf4f7534293d8a9`.
- Test: 3326 examples; SHA-256 `f973edaa3b5feda1ee549f8be3df661fdd49e25f8ed2c53db7b45cdbd4c892e7`.
- Test composition: label origins `construction`=3326; choice labels no-defect=643, real-defect=643; yes/no labels False=1020, True=1020.

## Headline by role

Each arm's numbers come from `results/corpus-v3-full/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1286 (real-defect=643, no-defect=643).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.191 | 0.160–0.223 | 0.145 | 0.238 | 0.233 | 0.144 | NVIDIA A10G | 17.530 | $0.5425 |
| kev-0.8b-ft-s17 | 0.770 | 0.706–0.830 | 0.815 | 0.725 | 0.059 | 0.075 | NVIDIA A10G | 17.535 | $0.7056 |
| kev-0.8b-ft-s18 | 0.799 | 0.743–0.847 | 0.854 | 0.743 | 0.065 | 0.065 | NVIDIA A10G | 17.494 | $0.5425 |
| kev-0.8b-ft-s19 | 0.772 | 0.708–0.832 | 0.843 | 0.701 | 0.036 | 0.058 | NVIDIA A10G | 17.398 | $0.7111 |
| kev-0.8b FT mean ± SD [range] | 0.780 ± 0.016 [0.770–0.799] | — | 0.837 ± 0.020 [0.815–0.854] | 0.723 ± 0.021 [0.701–0.743] | 0.053 ± 0.015 [0.036–0.065] | 0.066 ± 0.008 [0.058–0.075] | — | — | — |
| kev-4b | 0.295 | 0.254–0.335 | 0.491 | 0.098 | 0.123 | 0.063 | NVIDIA A10G | 65.032 | $1.1700 |
| kev-4b-ft-s17 | 0.827 | 0.771–0.880 | 0.942 | 0.711 | 0.097 | 0.075 | NVIDIA A10G | 65.081 | $1.1789 |
| kev-4b-ft-s18 | 0.826 | 0.772–0.878 | 0.944 | 0.708 | 0.087 | 0.082 | NVIDIA A10G | 65.355 | $0.9092 |
| kev-4b-ft-s19 | 0.821 | 0.768–0.872 | 0.946 | 0.697 | 0.103 | 0.095 | NVIDIA A10G | 65.159 | $1.1700 |
| kev-4b FT mean ± SD [range] | 0.825 ± 0.003 [0.821–0.827] | — | 0.944 ± 0.002 [0.942–0.946] | 0.705 ± 0.007 [0.697–0.711] | 0.096 ± 0.008 [0.087–0.103] | 0.084 ± 0.010 [0.075–0.095] | — | — | — |
| kev-9b | 0.489 | 0.457–0.524 | 0.809 | 0.170 | 0.102 | 0.096 | NVIDIA L40S | 62.488 | $1.8317 |
| kev-9b-ft-s17 | 0.858 | 0.807–0.909 | 0.953 | 0.764 | 0.071 | 0.054 | NVIDIA L40S | 62.322 | $1.2944 |
| kev-9b-ft-s18 | 0.881 | 0.833–0.927 | 0.953 | 0.809 | 0.042 | 0.023 | NVIDIA L40S | 62.431 | $1.3014 |
| kev-9b-ft-s19 | 0.865 | 0.813–0.915 | 0.966 | 0.764 | 0.060 | 0.044 | NVIDIA L40S | 62.230 | $1.3014 |
| kev-9b FT mean ± SD [range] | 0.868 ± 0.012 [0.858–0.881] | — | 0.957 ± 0.007 [0.953–0.966] | 0.779 ± 0.026 [0.764–0.809] | 0.058 ± 0.015 [0.042–0.071] | 0.041 ± 0.016 [0.023–0.054] | — | — | — |
| laya-english | 0.441 | 0.409–0.471 | 0.289 | 0.593 | 0.030 | 0.029 | NVIDIA A10G | 28.069 | $0.6756 |
| laya-multilingual | 0.364 | 0.339–0.390 | 0.132 | 0.596 | 0.250 | 0.025 | NVIDIA A10G | 23.252 | $1.4775 |
| laya-typed-decisions | 0.371 | 0.341–0.401 | 0.345 | 0.397 | 0.052 | 0.037 | NVIDIA A10G | 27.972 | $1.5900 |

- Best single arm: `kev-9b-ft-s18` (balanced accuracy 0.881).
- Best fine-tuned family by seed mean: `kev-9b` (0.868 ± 0.012 [0.858–0.881]).

### semantic-detection (`noul`)

Test items: 2040 (True=1020, False=1020).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.521 | 0.499–0.550 | 0.086 | 0.956 | 0.158 | 0.008 | NVIDIA A10G | 17.530 | $0.5425 |
| kev-0.8b-ft-s17 | 0.747 | 0.692–0.794 | 0.678 | 0.815 | 0.052 | 0.032 | NVIDIA A10G | 17.535 | $0.7056 |
| kev-0.8b-ft-s18 | 0.741 | 0.687–0.785 | 0.685 | 0.797 | 0.057 | 0.027 | NVIDIA A10G | 17.494 | $0.5425 |
| kev-0.8b-ft-s19 | 0.750 | 0.697–0.795 | 0.682 | 0.818 | 0.057 | 0.039 | NVIDIA A10G | 17.398 | $0.7111 |
| kev-0.8b FT mean ± SD [range] | 0.746 ± 0.004 [0.741–0.750] | — | 0.682 ± 0.003 [0.678–0.685] | 0.810 ± 0.011 [0.797–0.818] | 0.056 ± 0.003 [0.052–0.057] | 0.033 ± 0.006 [0.027–0.039] | — | — | — |
| kev-4b | 0.561 | 0.524–0.600 | 0.219 | 0.903 | 0.090 | 0.049 | NVIDIA A10G | 65.032 | $1.1700 |
| kev-4b-ft-s17 | 0.847 | 0.791–0.890 | 0.787 | 0.907 | 0.057 | 0.036 | NVIDIA A10G | 65.081 | $1.1789 |
| kev-4b-ft-s18 | 0.873 | 0.822–0.909 | 0.832 | 0.913 | 0.041 | 0.028 | NVIDIA A10G | 65.355 | $0.9092 |
| kev-4b-ft-s19 | 0.858 | 0.807–0.896 | 0.793 | 0.924 | 0.052 | 0.029 | NVIDIA A10G | 65.159 | $1.1700 |
| kev-4b FT mean ± SD [range] | 0.859 ± 0.013 [0.847–0.873] | — | 0.804 ± 0.025 [0.787–0.832] | 0.914 ± 0.008 [0.907–0.924] | 0.050 ± 0.008 [0.041–0.057] | 0.031 ± 0.004 [0.028–0.036] | — | — | — |
| kev-9b | 0.609 | 0.549–0.660 | 0.457 | 0.761 | 0.089 | 0.044 | NVIDIA L40S | 62.488 | $1.8317 |
| kev-9b-ft-s17 | 0.878 | 0.831–0.911 | 0.837 | 0.919 | 0.057 | 0.026 | NVIDIA L40S | 62.322 | $1.2944 |
| kev-9b-ft-s18 | 0.875 | 0.826–0.913 | 0.834 | 0.916 | 0.054 | 0.019 | NVIDIA L40S | 62.431 | $1.3014 |
| kev-9b-ft-s19 | 0.869 | 0.816–0.908 | 0.825 | 0.913 | 0.070 | 0.025 | NVIDIA L40S | 62.230 | $1.3014 |
| kev-9b FT mean ± SD [range] | 0.874 ± 0.004 [0.869–0.878] | — | 0.832 ± 0.006 [0.825–0.837] | 0.916 ± 0.003 [0.913–0.919] | 0.060 ± 0.008 [0.054–0.070] | 0.023 ± 0.004 [0.019–0.026] | — | — | — |
| laya-english | 0.501 | 0.452–0.548 | 0.516 | 0.486 | 0.233 | 0.006 | NVIDIA A10G | 28.069 | $0.6756 |
| laya-multilingual | 0.547 | 0.522–0.574 | 0.758 | 0.335 | 0.296 | 0.036 | NVIDIA A10G | 23.252 | $1.4775 |
| laya-typed-decisions | 0.563 | 0.522–0.600 | 0.536 | 0.589 | 0.044 | 0.061 | NVIDIA A10G | 27.972 | $1.5900 |

- Best single arm: `kev-9b-ft-s17` (balanced accuracy 0.878).
- Best fine-tuned family by seed mean: `kev-9b` (0.874 ± 0.004 [0.869–0.878]).

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | this campaign | 0.191 | 0.780 | +0.589 | 3/3 | +0.693 | +0.485 | -0.180 | -0.078 |
| kev-4b | this campaign | 0.295 | 0.825 | +0.530 | 3/3 | +0.453 | +0.607 | -0.027 | +0.021 |
| kev-9b | this campaign | 0.489 | 0.868 | +0.379 | 3/3 | +0.149 | +0.609 | -0.044 | -0.056 |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | this campaign | 0.521 | 0.746 | +0.225 | 3/3 | +0.596 | -0.146 | -0.102 | +0.025 |
| kev-4b | this campaign | 0.561 | 0.859 | +0.299 | 3/3 | +0.586 | +0.011 | -0.040 | -0.018 |
| kev-9b | this campaign | 0.609 | 0.874 | +0.265 | 3/3 | +0.375 | +0.155 | -0.029 | -0.020 |

## Comparison with `corpus-v3-confident`

Both campaigns score the same test and calibration export (hashes verified). Δ is `corpus-v3-full` minus `corpus-v3-confident` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.

### finding-confirmation (`choice`)

| Family | corpus-v3-full bal. acc. | corpus-v3-confident bal. acc. | Δ bal. acc. | Seeds better | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.780 ± 0.016 [0.770–0.799] | 0.781 ± 0.022 [0.763–0.806] | -0.001 | 1/3 | +0.009 | -0.010 | -0.012 | +0.000 |
| kev-4b | 0.825 ± 0.003 [0.821–0.827] | 0.848 ± 0.007 [0.840–0.854] | -0.023 | 0/3 | +0.011 | -0.057 | +0.007 | +0.019 |
| kev-9b | 0.868 ± 0.012 [0.858–0.881] | 0.877 ± 0.008 [0.868–0.883] | -0.009 | 0/3 | +0.018 | -0.037 | +0.005 | +0.001 |

### semantic-detection (`noul`)

| Family | corpus-v3-full bal. acc. | corpus-v3-confident bal. acc. | Δ bal. acc. | Seeds better | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.746 ± 0.004 [0.741–0.750] | 0.753 ± 0.008 [0.744–0.758] | -0.007 | 0/3 | +0.020 | -0.035 | -0.024 | -0.013 |
| kev-4b | 0.859 ± 0.013 [0.847–0.873] | 0.872 ± 0.010 [0.867–0.883] | -0.013 | 1/3 | -0.022 | -0.004 | +0.008 | +0.002 |
| kev-9b | 0.874 ± 0.004 [0.869–0.878] | 0.880 ± 0.003 [0.876–0.883] | -0.006 | 0/3 | +0.009 | -0.020 | +0.008 | -0.006 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | — | — | — | — | 1 / 0 / 0 | $0.54 | $0.54 |
| kev-4b | — | — | — | — | 1 / 0 / 0 | $1.17 | $1.17 |
| kev-9b | — | — | — | — | 1 / 0 / 0 | $1.83 | $1.83 |
| laya-english | — | — | — | — | 1 / 0 / 0 | $0.68 | $0.68 |
| laya-multilingual | — | — | — | — | 1 / 0 / 0 | $1.48 | $1.48 |
| laya-typed-decisions | — | — | — | — | 1 / 0 / 0 | $1.59 | $1.59 |
| kev-0.8b-ft-s17 | 1 / 0 / 0 | $9.82 | slopvac-judge-kev-08b-s17-20260929214043 | $9.82 | 1 / 0 / 0 | $0.71 | $10.52 |
| kev-0.8b-ft-s18 | 1 / 0 / 0 | $9.75 | slopvac-judge-kev-08b-s18-20260929214053 | $9.75 | 1 / 0 / 0 | $0.54 | $10.29 |
| kev-0.8b-ft-s19 | 1 / 0 / 0 | $12.38 | slopvac-judge-kev-08b-s19-20260929214105 | $12.38 | 1 / 0 / 0 | $0.71 | $13.09 |
| kev-4b-ft-s17 | 1 / 0 / 0 | $29.08 | slopvac-judge-kev-4b-s17-20260929214114 | $29.08 | 1 / 0 / 0 | $1.18 | $30.25 |
| kev-4b-ft-s18 | 1 / 0 / 0 | $28.94 | slopvac-judge-kev-4b-s18-20260929214124 | $28.94 | 1 / 0 / 0 | $0.91 | $29.85 |
| kev-4b-ft-s19 | 1 / 0 / 0 | $45.36 | slopvac-judge-kev-4b-s19-20260929214135 | $45.36 | 1 / 0 / 0 | $1.17 | $46.53 |
| kev-9b-ft-s17 | 1 / 0 / 0 | $57.14 | slopvac-judge-kev-9b-s17-20260929214144 | $57.14 | 1 / 0 / 0 | $1.29 | $58.43 |
| kev-9b-ft-s18 | 1 / 0 / 0 | $25.04 | slopvac-judge-kev-9b-s18-20260930001932 | $25.04 | 1 / 0 / 1 | $1.30 | $26.34 |
| kev-9b-ft-s19 | 1 / 0 / 0 | $56.30 | slopvac-judge-kev-9b-s19-20260930015505 | $56.30 | 1 / 0 / 0 | $1.30 | $57.60 |

Campaign total: **$290.20 USD** (training $273.80, evaluation $16.40) over 9 training and 16 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s18 | evaluation | Stopped | 1 | $0.00 | scheduler marker `capacity_rotation` |

## Panel agreement caveat

Independent corpus panel agreement (source: `/Users/sjors/tmp/worktrees/slopvac/exp-judge-corpus/scripts/judge-corpus/items/panel-agreement.json`):
- finding-confirmation: Fleiss κ=0.32 (3829 three-vote items).
- semantic-detection: Fleiss κ=0.42 (1987 three-vote items).
- Scores on panel-labelled rows measure agreement with the panel. Only constructions and human-adjudicated rows have independent ground truth.

## Per-arm training recipes

| Family / arm | Seeds | Epochs | Batch × accumulation | LR | Max state / max length | Dtype / weights |
| --- | --- | --- | --- | --- | --- | --- |
| Kev-0.8B | 17, 18, 19 | 2 | 4 × 2 | 2e-5 | 4096 / 4096 | bf16 autocast / fp32 weights |
| Kev-4B | 17, 18, 19 | 2 | 2 × 4 | 2e-5 | 4096 / 4096 | bf16 autocast / fp32 weights |
| Kev-9B | 17, 18, 19 | 2 | 1 × 8 | 2e-5 | 4096 / 4096 | bf16 autocast / fp32 weights; LoRA/head fp32 |
| Laya typed decisions | 17, 18, 19 | 4 | micro-batch 8 × grad accum 8 | 2.5e-5 encoder / 1e-4 head | 4096 / head 1024 | fp32 training; fp16 saved |

Kev uses CUDA bf16 autocast, fp32 frozen backbone weights and gradient checkpointing; 9B uses micro-batch 1 × accumulation 8 to preserve effective batch 8. Laya uses its 4-epoch pilot recipe; its encoder sequence max_len is raised to 4096 for this corpus.

## Per-arm evaluation tables

Model results include checkpoints from failed fine-tuning jobs only when calibration failed after training and the archived adapter/head were validated; their evaluation job—not the training job—fits calibration to the test/calibration export.

### kev-0.8b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 2040 | 0.521 | 0.521 | 0.620 | 0.269 | 0.743 | 0.158 | 0.248 | 0.689 | 0.008 | 0.499–0.550 | 0.108–0.205 | 0.004–0.064 | 0.086 | 0.956 | — | — | — | 17.530 | 57.918 |
| kev-0.8b-ft-s17 | 2040 | 0.747 | 0.747 | 0.832 | 0.174 | 0.523 | 0.052 | 0.172 | 0.514 | 0.032 | 0.692–0.794 | 0.023–0.113 | 0.018–0.094 | 0.678 | 0.815 | — | — | — | 17.535 | 57.775 |
| kev-0.8b-ft-s18 | 2040 | 0.741 | 0.741 | 0.834 | 0.171 | 0.514 | 0.057 | 0.168 | 0.503 | 0.027 | 0.687–0.785 | 0.025–0.110 | 0.020–0.079 | 0.685 | 0.797 | — | — | — | 17.494 | 57.804 |
| kev-0.8b-ft-s19 | 2040 | 0.750 | 0.750 | 0.832 | 0.175 | 0.528 | 0.057 | 0.173 | 0.518 | 0.039 | 0.697–0.795 | 0.027–0.112 | 0.020–0.092 | 0.682 | 0.818 | — | — | — | 17.398 | 57.386 |
| FT mean ± SD [range] | — | 0.746 ± 0.004 [0.741–0.750] | 0.746 ± 0.004 [0.741–0.750] | 0.833 ± 0.002 [0.832–0.834] | 0.173 ± 0.002 [0.171–0.175] | 0.521 ± 0.007 [0.514–0.528] | 0.056 ± 0.003 [0.052–0.057] | 0.171 ± 0.002 [0.168–0.173] | 0.512 ± 0.008 [0.503–0.518] | 0.033 ± 0.006 [0.027–0.039] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 1286 | 0.191 | 0.191 | 0.395 | 0.758 | 1.247 | 0.233 | 0.668 | 1.101 | 0.144 | 0.160–0.223 | 0.206–0.263 | 0.116–0.173 | — | — | 0.499 | 0.722 | 0.037 | 17.530 | 57.918 |
| kev-0.8b-ft-s17 | 1286 | 0.770 | 0.770 | 0.857 | 0.315 | 0.481 | 0.059 | 0.320 | 0.491 | 0.075 | 0.706–0.830 | 0.026–0.116 | 0.036–0.133 | — | — | 0.001 | 0.904 | 0.097 | 17.535 | 57.775 |
| kev-0.8b-ft-s18 | 1286 | 0.799 | 0.799 | 0.868 | 0.303 | 0.473 | 0.065 | 0.303 | 0.472 | 0.065 | 0.743–0.847 | 0.031–0.111 | 0.031–0.111 | — | — | 0.000 | 0.922 | 0.075 | 17.494 | 57.804 |
| kev-0.8b-ft-s19 | 1286 | 0.772 | 0.772 | 0.858 | 0.310 | 0.473 | 0.036 | 0.317 | 0.484 | 0.058 | 0.708–0.832 | 0.027–0.089 | 0.025–0.122 | — | — | 0.000 | 0.911 | 0.082 | 17.398 | 57.386 |
| FT mean ± SD [range] | — | 0.780 ± 0.016 [0.770–0.799] | 0.780 ± 0.016 [0.770–0.799] | 0.861 ± 0.006 [0.857–0.868] | 0.309 ± 0.006 [0.303–0.315] | 0.476 ± 0.004 [0.473–0.481] | 0.053 ± 0.015 [0.036–0.065] | 0.313 ± 0.009 [0.303–0.320] | 0.482 ± 0.009 [0.472–0.491] | 0.066 ± 0.008 [0.058–0.075] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.001] | 0.913 ± 0.009 [0.904–0.922] | 0.085 ± 0.011 [0.075–0.097] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b | 2040 | 0.561 | 0.561 | 0.663 | 0.244 | 0.681 | 0.090 | 0.239 | 0.671 | 0.049 | 0.524–0.600 | 0.049–0.144 | 0.026–0.089 | 0.219 | 0.903 | — | — | — | 65.032 | 166.113 |
| kev-4b-ft-s17 | 2040 | 0.847 | 0.847 | 0.926 | 0.113 | 0.378 | 0.057 | 0.111 | 0.363 | 0.036 | 0.791–0.890 | 0.028–0.111 | 0.019–0.089 | 0.787 | 0.907 | — | — | — | 65.081 | 166.114 |
| kev-4b-ft-s18 | 2040 | 0.873 | 0.873 | 0.941 | 0.098 | 0.331 | 0.041 | 0.097 | 0.324 | 0.028 | 0.822–0.909 | 0.015–0.088 | 0.012–0.075 | 0.832 | 0.913 | — | — | — | 65.355 | 166.616 |
| kev-4b-ft-s19 | 2040 | 0.858 | 0.858 | 0.936 | 0.109 | 0.362 | 0.052 | 0.107 | 0.346 | 0.029 | 0.807–0.896 | 0.026–0.096 | 0.017–0.073 | 0.793 | 0.924 | — | — | — | 65.159 | 166.395 |
| FT mean ± SD [range] | — | 0.859 ± 0.013 [0.847–0.873] | 0.859 ± 0.013 [0.847–0.873] | 0.934 ± 0.008 [0.926–0.941] | 0.107 ± 0.008 [0.098–0.113] | 0.357 ± 0.024 [0.331–0.378] | 0.050 ± 0.008 [0.041–0.057] | 0.105 ± 0.007 [0.097–0.111] | 0.344 ± 0.020 [0.324–0.363] | 0.031 ± 0.004 [0.028–0.036] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b | 1286 | 0.295 | 0.295 | 0.553 | 0.698 | 1.147 | 0.123 | 0.672 | 1.107 | 0.063 | 0.254–0.335 | 0.072–0.171 | 0.015–0.112 | — | — | 0.428 | 0.794 | 0.041 | 65.032 | 166.113 |
| kev-4b-ft-s17 | 1286 | 0.827 | 0.827 | 0.912 | 0.271 | 0.483 | 0.097 | 0.262 | 0.443 | 0.075 | 0.771–0.880 | 0.051–0.156 | 0.030–0.134 | — | — | 0.000 | 0.956 | 0.049 | 65.081 | 166.114 |
| kev-4b-ft-s18 | 1286 | 0.826 | 0.826 | 0.925 | 0.261 | 0.436 | 0.087 | 0.259 | 0.429 | 0.082 | 0.772–0.878 | 0.041–0.140 | 0.038–0.135 | — | — | 0.000 | 0.956 | 0.046 | 65.355 | 166.616 |
| kev-4b-ft-s19 | 1286 | 0.821 | 0.821 | 0.922 | 0.274 | 0.461 | 0.103 | 0.269 | 0.444 | 0.095 | 0.768–0.872 | 0.054–0.157 | 0.046–0.149 | — | — | 0.000 | 0.970 | 0.033 | 65.159 | 166.395 |
| FT mean ± SD [range] | — | 0.825 ± 0.003 [0.821–0.827] | 0.825 ± 0.003 [0.821–0.827] | 0.920 ± 0.007 [0.912–0.925] | 0.269 ± 0.007 [0.261–0.274] | 0.460 ± 0.024 [0.436–0.483] | 0.096 ± 0.008 [0.087–0.103] | 0.263 ± 0.005 [0.259–0.269] | 0.439 ± 0.009 [0.429–0.444] | 0.084 ± 0.010 [0.075–0.095] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.961 ± 0.008 [0.956–0.970] | 0.043 ± 0.009 [0.033–0.049] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b | 2040 | 0.609 | 0.609 | 0.647 | 0.246 | 0.694 | 0.089 | 0.237 | 0.666 | 0.044 | 0.549–0.660 | 0.054–0.157 | 0.017–0.099 | 0.457 | 0.761 | — | — | — | 62.488 | 105.338 |
| kev-9b-ft-s17 | 2040 | 0.878 | 0.878 | 0.950 | 0.093 | 0.324 | 0.057 | 0.089 | 0.297 | 0.026 | 0.831–0.911 | 0.033–0.093 | 0.015–0.063 | 0.837 | 0.919 | — | — | — | 62.322 | 105.869 |
| kev-9b-ft-s18 | 2040 | 0.875 | 0.875 | 0.948 | 0.093 | 0.325 | 0.054 | 0.089 | 0.297 | 0.019 | 0.826–0.913 | 0.030–0.093 | 0.012–0.057 | 0.834 | 0.916 | — | — | — | 62.431 | 108.825 |
| kev-9b-ft-s19 | 2040 | 0.869 | 0.869 | 0.943 | 0.103 | 0.360 | 0.070 | 0.097 | 0.320 | 0.025 | 0.816–0.908 | 0.038–0.122 | 0.012–0.077 | 0.825 | 0.913 | — | — | — | 62.230 | 107.900 |
| FT mean ± SD [range] | — | 0.874 ± 0.004 [0.869–0.878] | 0.874 ± 0.004 [0.869–0.878] | 0.947 ± 0.004 [0.943–0.950] | 0.096 ± 0.006 [0.093–0.103] | 0.336 ± 0.020 [0.324–0.360] | 0.060 ± 0.008 [0.054–0.070] | 0.092 ± 0.005 [0.089–0.097] | 0.305 ± 0.013 [0.297–0.320] | 0.023 ± 0.004 [0.019–0.026] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b | 1286 | 0.489 | 0.489 | 0.561 | 0.631 | 1.037 | 0.102 | 0.626 | 1.028 | 0.096 | 0.457–0.524 | 0.061–0.168 | 0.053–0.157 | — | — | 0.030 | 0.841 | 0.064 | 62.488 | 105.338 |
| kev-9b-ft-s17 | 1286 | 0.858 | 0.858 | 0.954 | 0.209 | 0.340 | 0.071 | 0.202 | 0.325 | 0.054 | 0.807–0.909 | 0.030–0.119 | 0.029–0.101 | — | — | 0.001 | 0.973 | 0.040 | 62.322 | 105.869 |
| kev-9b-ft-s18 | 1286 | 0.881 | 0.881 | 0.965 | 0.173 | 0.290 | 0.042 | 0.169 | 0.282 | 0.023 | 0.833–0.927 | 0.016–0.090 | 0.014–0.072 | — | — | 0.000 | 0.969 | 0.033 | 62.431 | 108.825 |
| kev-9b-ft-s19 | 1286 | 0.865 | 0.865 | 0.964 | 0.206 | 0.331 | 0.060 | 0.201 | 0.320 | 0.044 | 0.813–0.915 | 0.023–0.110 | 0.025–0.094 | — | — | 0.000 | 0.978 | 0.030 | 62.230 | 107.900 |
| FT mean ± SD [range] | — | 0.868 ± 0.012 [0.858–0.881] | 0.868 ± 0.012 [0.858–0.881] | 0.961 ± 0.006 [0.954–0.965] | 0.196 ± 0.020 [0.173–0.209] | 0.320 ± 0.026 [0.290–0.340] | 0.058 ± 0.015 [0.042–0.071] | 0.191 ± 0.019 [0.169–0.202] | 0.309 ± 0.024 [0.282–0.325] | 0.041 ± 0.016 [0.023–0.054] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.001] | 0.973 ± 0.005 [0.969–0.978] | 0.034 ± 0.005 [0.030–0.040] | — | — |

### laya-english

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-english | 2040 | 0.501 | 0.501 | 0.507 | 0.316 | 0.880 | 0.233 | 0.250 | 0.693 | 0.006 | 0.452–0.548 | 0.185–0.286 | 0.001–0.058 | 0.516 | 0.486 | — | — | — | 28.069 | 29.831 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-english | 1286 | 0.441 | 0.441 | 0.530 | 0.659 | 1.097 | 0.030 | 0.653 | 1.082 | 0.029 | 0.409–0.471 | 0.024–0.075 | 0.016–0.068 | — | — | 0.144 | 0.712 | 0.062 | 28.069 | 29.831 |

### laya-multilingual

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-multilingual | 2040 | 0.547 | 0.547 | 0.556 | 0.348 | 1.120 | 0.296 | 0.249 | 0.691 | 0.036 | 0.522–0.574 | 0.256–0.337 | 0.004–0.075 | 0.758 | 0.335 | — | — | — | 23.252 | 24.889 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-multilingual | 1286 | 0.364 | 0.364 | 0.502 | 0.790 | 1.318 | 0.250 | 0.665 | 1.094 | 0.025 | 0.339–0.390 | 0.209–0.299 | 0.018–0.074 | — | — | 0.233 | 0.790 | 0.098 | 23.252 | 24.889 |

### laya-typed-decisions

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-typed-decisions | 2040 | 0.563 | 0.563 | 0.575 | 0.250 | 0.695 | 0.044 | 0.250 | 0.692 | 0.061 | 0.522–0.600 | 0.028–0.082 | 0.021–0.098 | 0.536 | 0.589 | — | — | — | 27.972 | 39.438 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-typed-decisions | 1286 | 0.371 | 0.371 | 0.565 | 0.674 | 1.116 | 0.052 | 0.668 | 1.102 | 0.037 | 0.341–0.401 | 0.032–0.085 | 0.013–0.067 | — | — | 0.313 | 0.755 | 0.031 | 27.972 | 39.438 |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 17.530 | 57.918 | 651 | $0.5425 | sv-eval-kev-08b-260929214156506493 |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.535 | 57.775 | 635 | $0.7056 | sv-eval-kev-08b-ft-s17-260930024131835577 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 17.494 | 57.804 | 651 | $0.5425 | sv-eval-kev-08b-ft-s18-260930023604766903 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 17.398 | 57.386 | 640 | $0.7111 | sv-eval-kev-08b-ft-s19-260930024144958986 |
| kev-4b | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 65.032 | 166.113 | 1053 | $1.1700 | sv-eval-kev-4b-260929214210011584 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 65.081 | 166.114 | 1061 | $1.1789 | sv-eval-kev-4b-ft-s17-260930020528014557 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 65.355 | 166.616 | 1091 | $0.9092 | sv-eval-kev-4b-ft-s18-260930113948720556 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 65.159 | 166.395 | 1053 | $1.1700 | sv-eval-kev-4b-ft-s19-260930015516499752 |
| kev-9b | NVIDIA L40S | ml.g6e.8xlarge | us-east-1 | 62.488 | 105.338 | 942 | $1.8317 | sv-eval-kev-9b-260930020516276225 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.4xlarge | us-east-1 | 62.322 | 105.869 | 932 | $1.2944 | sv-eval-kev-9b-ft-s17-260930114008587751 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.4xlarge | us-west-2 | 62.431 | 108.825 | 937 | $1.3014 | sv-eval-kev-9b-ft-s18-260930121927588463 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.4xlarge | us-east-1 | 62.230 | 107.900 | 937 | $1.3014 | sv-eval-kev-9b-ft-s19-260930085708505137 |
| laya-english | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 28.069 | 29.831 | 608 | $0.6756 | sv-eval-laya-english-260929214221062080 |
| laya-multilingual | NVIDIA A10G | ml.g5.12xlarge | us-east-1 | 23.252 | 24.889 | 591 | $1.4775 | sv-eval-laya-multilingual-260929214234433839 |
| laya-typed-decisions | NVIDIA A10G | ml.g5.12xlarge | us-west-2 | 27.972 | 39.438 | 636 | $1.5900 | sv-eval-laya-typed-decisions-260929214245341426 |

Total billed evaluation cost for the reported arms: **$16.4018 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | noul | granularity | document | 990 | 0.527 | 0.520 | 0.153 | 0.088 | 0.952 |
| kev-0.8b | noul | granularity | paragraph | 733 | 0.502 | 0.506 | 0.187 | 0.057 | 0.956 |
| kev-0.8b | noul | granularity | sentence | 317 | 0.546 | 0.557 | 0.144 | 0.147 | 0.968 |
| kev-0.8b | noul | provenance | human | 2040 | 0.521 | 0.521 | 0.158 | 0.086 | 0.956 |
| kev-0.8b | noul | role | semantic-detection | 2040 | 0.521 | 0.521 | 0.158 | 0.086 | 0.956 |
| kev-0.8b | noul | rule_held_out | False | 1208 | 0.604 | 0.511 | 0.091 | 0.065 | 0.958 |
| kev-0.8b | noul | rule_held_out | True | 832 | 0.400 | 0.528 | 0.254 | 0.105 | 0.952 |
| kev-0.8b | noul | source accuracy | human | 2040 | 0.521 | — | — | — | — |
| kev-0.8b | choice | granularity | document | 615 | 0.185 | 0.186 | 0.237 | 0.193 | 0.179 |
| kev-0.8b | choice | granularity | paragraph | 451 | 0.151 | 0.156 | 0.279 | 0.214 | 0.098 |
| kev-0.8b | choice | granularity | sentence | 220 | 0.291 | 0.251 | 0.133 | 0.355 | 0.147 |
| kev-0.8b | choice | provenance | human | 1286 | 0.191 | 0.191 | 0.233 | 0.238 | 0.145 |
| kev-0.8b | choice | role | finding-confirmation | 1286 | 0.191 | 0.191 | 0.233 | 0.238 | 0.145 |
| kev-0.8b | choice | rule_held_out | False | 693 | 0.186 | 0.213 | 0.243 | 0.273 | 0.154 |
| kev-0.8b | choice | rule_held_out | True | 593 | 0.197 | 0.167 | 0.222 | 0.224 | 0.109 |
| kev-0.8b | choice | source accuracy | human | 1286 | 0.191 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | granularity | document | 990 | 0.740 | 0.739 | 0.057 | 0.663 | 0.815 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 733 | 0.746 | 0.747 | 0.059 | 0.697 | 0.796 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 317 | 0.767 | 0.769 | 0.084 | 0.681 | 0.857 |
| kev-0.8b-ft-s17 | noul | provenance | human | 2040 | 0.747 | 0.747 | 0.052 | 0.678 | 0.815 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2040 | 0.747 | 0.747 | 0.052 | 0.678 | 0.815 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1208 | 0.766 | 0.747 | 0.056 | 0.655 | 0.838 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 832 | 0.719 | 0.727 | 0.067 | 0.699 | 0.755 |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 2040 | 0.747 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 615 | 0.780 | 0.776 | 0.055 | 0.716 | 0.836 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 451 | 0.776 | 0.771 | 0.064 | 0.709 | 0.833 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 220 | 0.727 | 0.705 | 0.112 | 0.763 | 0.647 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1286 | 0.770 | 0.770 | 0.059 | 0.725 | 0.815 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1286 | 0.770 | 0.770 | 0.059 | 0.725 | 0.815 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 693 | 0.807 | 0.807 | 0.035 | 0.807 | 0.806 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 593 | 0.727 | 0.769 | 0.091 | 0.691 | 0.847 |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1286 | 0.770 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 990 | 0.727 | 0.727 | 0.069 | 0.680 | 0.773 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 733 | 0.745 | 0.745 | 0.056 | 0.697 | 0.793 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 317 | 0.776 | 0.779 | 0.047 | 0.675 | 0.883 |
| kev-0.8b-ft-s18 | noul | provenance | human | 2040 | 0.741 | 0.741 | 0.057 | 0.685 | 0.797 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2040 | 0.741 | 0.741 | 0.057 | 0.685 | 0.797 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1208 | 0.764 | 0.750 | 0.058 | 0.680 | 0.819 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 832 | 0.708 | 0.716 | 0.064 | 0.690 | 0.741 |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 2040 | 0.741 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 615 | 0.810 | 0.805 | 0.063 | 0.744 | 0.867 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 451 | 0.805 | 0.799 | 0.052 | 0.728 | 0.869 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 220 | 0.755 | 0.749 | 0.132 | 0.763 | 0.735 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1286 | 0.799 | 0.799 | 0.065 | 0.743 | 0.854 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1286 | 0.799 | 0.799 | 0.065 | 0.743 | 0.854 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 693 | 0.835 | 0.815 | 0.040 | 0.770 | 0.860 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 593 | 0.755 | 0.782 | 0.110 | 0.732 | 0.832 |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1286 | 0.799 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 990 | 0.742 | 0.741 | 0.057 | 0.680 | 0.803 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 733 | 0.749 | 0.750 | 0.065 | 0.686 | 0.813 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 317 | 0.776 | 0.779 | 0.067 | 0.681 | 0.877 |
| kev-0.8b-ft-s19 | noul | provenance | human | 2040 | 0.750 | 0.750 | 0.057 | 0.682 | 0.818 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2040 | 0.750 | 0.750 | 0.057 | 0.682 | 0.818 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1208 | 0.769 | 0.754 | 0.056 | 0.682 | 0.826 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 832 | 0.722 | 0.740 | 0.061 | 0.683 | 0.797 |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 2040 | 0.750 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 615 | 0.790 | 0.785 | 0.042 | 0.712 | 0.858 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 451 | 0.765 | 0.758 | 0.032 | 0.675 | 0.841 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 220 | 0.736 | 0.748 | 0.116 | 0.717 | 0.779 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1286 | 0.772 | 0.772 | 0.036 | 0.701 | 0.843 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1286 | 0.772 | 0.772 | 0.036 | 0.701 | 0.843 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 693 | 0.831 | 0.814 | 0.036 | 0.775 | 0.852 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 593 | 0.703 | 0.741 | 0.089 | 0.671 | 0.810 |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1286 | 0.772 | — | — | — | — |
| kev-4b | noul | granularity | document | 990 | 0.555 | 0.549 | 0.105 | 0.209 | 0.889 |
| kev-4b | noul | granularity | paragraph | 733 | 0.547 | 0.550 | 0.104 | 0.192 | 0.909 |
| kev-4b | noul | granularity | sentence | 317 | 0.612 | 0.621 | 0.075 | 0.307 | 0.935 |
| kev-4b | noul | provenance | human | 2040 | 0.561 | 0.561 | 0.090 | 0.219 | 0.903 |
| kev-4b | noul | role | semantic-detection | 2040 | 0.561 | 0.561 | 0.090 | 0.219 | 0.903 |
| kev-4b | noul | rule_held_out | False | 1208 | 0.638 | 0.566 | 0.028 | 0.222 | 0.911 |
| kev-4b | noul | rule_held_out | True | 832 | 0.448 | 0.549 | 0.216 | 0.216 | 0.883 |
| kev-4b | noul | source accuracy | human | 2040 | 0.561 | — | — | — | — |
| kev-4b | choice | granularity | document | 615 | 0.361 | 0.348 | 0.059 | 0.165 | 0.530 |
| kev-4b | choice | granularity | paragraph | 451 | 0.275 | 0.257 | 0.156 | 0.049 | 0.465 |
| kev-4b | choice | granularity | sentence | 220 | 0.150 | 0.218 | 0.291 | 0.039 | 0.397 |
| kev-4b | choice | provenance | human | 1286 | 0.295 | 0.295 | 0.123 | 0.098 | 0.491 |
| kev-4b | choice | role | finding-confirmation | 1286 | 0.295 | 0.295 | 0.123 | 0.098 | 0.491 |
| kev-4b | choice | rule_held_out | False | 693 | 0.394 | 0.314 | 0.045 | 0.139 | 0.488 |
| kev-4b | choice | rule_held_out | True | 593 | 0.179 | 0.292 | 0.239 | 0.081 | 0.504 |
| kev-4b | choice | source accuracy | human | 1286 | 0.295 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 990 | 0.847 | 0.846 | 0.056 | 0.784 | 0.909 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 733 | 0.849 | 0.849 | 0.065 | 0.814 | 0.884 |
| kev-4b-ft-s17 | noul | granularity | sentence | 317 | 0.842 | 0.845 | 0.075 | 0.736 | 0.955 |
| kev-4b-ft-s17 | noul | provenance | human | 2040 | 0.847 | 0.847 | 0.057 | 0.787 | 0.907 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2040 | 0.847 | 0.847 | 0.057 | 0.787 | 0.907 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1208 | 0.873 | 0.863 | 0.040 | 0.812 | 0.914 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 832 | 0.809 | 0.828 | 0.084 | 0.766 | 0.890 |
| kev-4b-ft-s17 | noul | source accuracy | human | 2040 | 0.847 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 615 | 0.826 | 0.817 | 0.095 | 0.688 | 0.945 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 451 | 0.838 | 0.827 | 0.095 | 0.704 | 0.951 |
| kev-4b-ft-s17 | choice | granularity | sentence | 220 | 0.805 | 0.830 | 0.122 | 0.763 | 0.897 |
| kev-4b-ft-s17 | choice | provenance | human | 1286 | 0.827 | 0.827 | 0.097 | 0.711 | 0.942 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1286 | 0.827 | 0.827 | 0.097 | 0.711 | 0.942 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 693 | 0.906 | 0.870 | 0.040 | 0.791 | 0.949 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 593 | 0.734 | 0.799 | 0.169 | 0.678 | 0.920 |
| kev-4b-ft-s17 | choice | source accuracy | human | 1286 | 0.827 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 990 | 0.874 | 0.873 | 0.039 | 0.832 | 0.915 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 733 | 0.858 | 0.858 | 0.055 | 0.827 | 0.890 |
| kev-4b-ft-s18 | noul | granularity | sentence | 317 | 0.902 | 0.904 | 0.043 | 0.847 | 0.961 |
| kev-4b-ft-s18 | noul | provenance | human | 2040 | 0.873 | 0.873 | 0.041 | 0.832 | 0.913 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2040 | 0.873 | 0.873 | 0.041 | 0.832 | 0.913 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1208 | 0.888 | 0.880 | 0.033 | 0.839 | 0.921 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 832 | 0.850 | 0.860 | 0.055 | 0.827 | 0.893 |
| kev-4b-ft-s18 | noul | source accuracy | human | 2040 | 0.873 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 615 | 0.831 | 0.822 | 0.080 | 0.695 | 0.948 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 451 | 0.843 | 0.831 | 0.083 | 0.694 | 0.967 |
| kev-4b-ft-s18 | choice | granularity | sentence | 220 | 0.777 | 0.794 | 0.128 | 0.750 | 0.838 |
| kev-4b-ft-s18 | choice | provenance | human | 1286 | 0.826 | 0.826 | 0.087 | 0.708 | 0.944 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1286 | 0.826 | 0.826 | 0.087 | 0.708 | 0.944 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 693 | 0.899 | 0.863 | 0.032 | 0.786 | 0.941 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 593 | 0.740 | 0.816 | 0.154 | 0.675 | 0.956 |
| kev-4b-ft-s18 | choice | source accuracy | human | 1286 | 0.826 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 990 | 0.857 | 0.856 | 0.059 | 0.795 | 0.917 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 733 | 0.855 | 0.856 | 0.057 | 0.803 | 0.909 |
| kev-4b-ft-s19 | noul | granularity | sentence | 317 | 0.871 | 0.874 | 0.049 | 0.767 | 0.981 |
| kev-4b-ft-s19 | noul | provenance | human | 2040 | 0.858 | 0.858 | 0.052 | 0.793 | 0.924 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2040 | 0.858 | 0.858 | 0.052 | 0.793 | 0.924 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1208 | 0.894 | 0.885 | 0.036 | 0.843 | 0.927 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 832 | 0.806 | 0.831 | 0.087 | 0.749 | 0.914 |
| kev-4b-ft-s19 | noul | source accuracy | human | 2040 | 0.858 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 615 | 0.823 | 0.813 | 0.099 | 0.681 | 0.945 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 451 | 0.823 | 0.810 | 0.103 | 0.670 | 0.951 |
| kev-4b-ft-s19 | choice | granularity | sentence | 220 | 0.814 | 0.845 | 0.120 | 0.763 | 0.926 |
| kev-4b-ft-s19 | choice | provenance | human | 1286 | 0.821 | 0.821 | 0.103 | 0.697 | 0.946 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1286 | 0.821 | 0.821 | 0.103 | 0.697 | 0.946 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 693 | 0.902 | 0.864 | 0.042 | 0.781 | 0.947 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 593 | 0.727 | 0.802 | 0.176 | 0.662 | 0.942 |
| kev-4b-ft-s19 | choice | source accuracy | human | 1286 | 0.821 | — | — | — | — |
| kev-9b | noul | granularity | document | 990 | 0.582 | 0.579 | 0.111 | 0.402 | 0.755 |
| kev-9b | noul | granularity | paragraph | 733 | 0.619 | 0.621 | 0.088 | 0.481 | 0.760 |
| kev-9b | noul | granularity | sentence | 317 | 0.669 | 0.672 | 0.165 | 0.564 | 0.779 |
| kev-9b | noul | provenance | human | 2040 | 0.609 | 0.609 | 0.089 | 0.457 | 0.761 |
| kev-9b | noul | role | semantic-detection | 2040 | 0.609 | 0.609 | 0.089 | 0.457 | 0.761 |
| kev-9b | noul | rule_held_out | False | 1208 | 0.623 | 0.580 | 0.097 | 0.374 | 0.786 |
| kev-9b | noul | rule_held_out | True | 832 | 0.588 | 0.613 | 0.096 | 0.530 | 0.697 |
| kev-9b | noul | source accuracy | human | 2040 | 0.609 | — | — | — | — |
| kev-9b | choice | granularity | document | 615 | 0.524 | 0.501 | 0.090 | 0.193 | 0.809 |
| kev-9b | choice | granularity | paragraph | 451 | 0.508 | 0.479 | 0.099 | 0.150 | 0.808 |
| kev-9b | choice | granularity | sentence | 220 | 0.355 | 0.480 | 0.227 | 0.151 | 0.809 |
| kev-9b | choice | provenance | human | 1286 | 0.489 | 0.489 | 0.102 | 0.170 | 0.809 |
| kev-9b | choice | role | finding-confirmation | 1286 | 0.489 | 0.489 | 0.102 | 0.170 | 0.809 |
| kev-9b | choice | rule_held_out | False | 693 | 0.631 | 0.489 | 0.069 | 0.182 | 0.796 |
| kev-9b | choice | rule_held_out | True | 593 | 0.324 | 0.509 | 0.278 | 0.164 | 0.854 |
| kev-9b | choice | source accuracy | human | 1286 | 0.489 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 990 | 0.870 | 0.869 | 0.067 | 0.823 | 0.915 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 733 | 0.880 | 0.880 | 0.055 | 0.857 | 0.904 |
| kev-9b-ft-s17 | noul | granularity | sentence | 317 | 0.899 | 0.901 | 0.045 | 0.834 | 0.968 |
| kev-9b-ft-s17 | noul | provenance | human | 2040 | 0.878 | 0.878 | 0.057 | 0.837 | 0.919 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2040 | 0.878 | 0.878 | 0.057 | 0.837 | 0.919 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1208 | 0.896 | 0.888 | 0.049 | 0.854 | 0.923 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 832 | 0.852 | 0.865 | 0.069 | 0.823 | 0.907 |
| kev-9b-ft-s17 | noul | source accuracy | human | 2040 | 0.878 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 615 | 0.863 | 0.857 | 0.060 | 0.768 | 0.945 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 451 | 0.871 | 0.863 | 0.073 | 0.762 | 0.963 |
| kev-9b-ft-s17 | choice | granularity | sentence | 220 | 0.818 | 0.856 | 0.126 | 0.757 | 0.956 |
| kev-9b-ft-s17 | choice | provenance | human | 1286 | 0.858 | 0.858 | 0.071 | 0.764 | 0.953 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1286 | 0.858 | 0.858 | 0.071 | 0.764 | 0.953 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 693 | 0.926 | 0.901 | 0.018 | 0.845 | 0.957 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 593 | 0.779 | 0.836 | 0.135 | 0.730 | 0.942 |
| kev-9b-ft-s17 | choice | source accuracy | human | 1286 | 0.858 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 990 | 0.861 | 0.860 | 0.066 | 0.813 | 0.907 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 733 | 0.885 | 0.886 | 0.046 | 0.859 | 0.912 |
| kev-9b-ft-s18 | noul | granularity | sentence | 317 | 0.896 | 0.898 | 0.046 | 0.840 | 0.955 |
| kev-9b-ft-s18 | noul | provenance | human | 2040 | 0.875 | 0.875 | 0.054 | 0.834 | 0.916 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2040 | 0.875 | 0.875 | 0.054 | 0.834 | 0.916 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1208 | 0.897 | 0.889 | 0.045 | 0.854 | 0.925 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 832 | 0.844 | 0.855 | 0.069 | 0.817 | 0.893 |
| kev-9b-ft-s18 | noul | source accuracy | human | 2040 | 0.875 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 615 | 0.886 | 0.881 | 0.038 | 0.811 | 0.952 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 451 | 0.887 | 0.880 | 0.046 | 0.806 | 0.955 |
| kev-9b-ft-s18 | choice | granularity | sentence | 220 | 0.855 | 0.883 | 0.056 | 0.809 | 0.956 |
| kev-9b-ft-s18 | choice | provenance | human | 1286 | 0.881 | 0.881 | 0.042 | 0.809 | 0.953 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1286 | 0.881 | 0.881 | 0.042 | 0.809 | 0.953 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 693 | 0.939 | 0.920 | 0.023 | 0.877 | 0.962 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 593 | 0.813 | 0.850 | 0.086 | 0.781 | 0.920 |
| kev-9b-ft-s18 | choice | source accuracy | human | 1286 | 0.881 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 990 | 0.858 | 0.857 | 0.076 | 0.803 | 0.911 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 733 | 0.880 | 0.880 | 0.067 | 0.865 | 0.895 |
| kev-9b-ft-s19 | noul | granularity | sentence | 317 | 0.880 | 0.882 | 0.066 | 0.804 | 0.961 |
| kev-9b-ft-s19 | noul | provenance | human | 2040 | 0.869 | 0.869 | 0.070 | 0.825 | 0.913 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2040 | 0.869 | 0.869 | 0.070 | 0.825 | 0.913 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1208 | 0.890 | 0.882 | 0.054 | 0.843 | 0.921 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 832 | 0.839 | 0.852 | 0.095 | 0.810 | 0.893 |
| kev-9b-ft-s19 | noul | source accuracy | human | 2040 | 0.869 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 615 | 0.867 | 0.860 | 0.055 | 0.765 | 0.955 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 451 | 0.876 | 0.866 | 0.058 | 0.757 | 0.976 |
| kev-9b-ft-s19 | choice | granularity | sentence | 220 | 0.836 | 0.878 | 0.081 | 0.770 | 0.985 |
| kev-9b-ft-s19 | choice | provenance | human | 1286 | 0.865 | 0.865 | 0.060 | 0.764 | 0.966 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1286 | 0.865 | 0.865 | 0.060 | 0.764 | 0.966 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 693 | 0.931 | 0.902 | 0.021 | 0.840 | 0.964 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 593 | 0.788 | 0.852 | 0.114 | 0.732 | 0.971 |
| kev-9b-ft-s19 | choice | source accuracy | human | 1286 | 0.865 | — | — | — | — |
| laya-english | noul | granularity | document | 990 | 0.498 | 0.498 | 0.229 | 0.526 | 0.471 |
| laya-english | noul | granularity | paragraph | 733 | 0.510 | 0.510 | 0.229 | 0.546 | 0.474 |
| laya-english | noul | granularity | sentence | 317 | 0.489 | 0.491 | 0.258 | 0.417 | 0.565 |
| laya-english | noul | provenance | human | 2040 | 0.501 | 0.501 | 0.233 | 0.516 | 0.486 |
| laya-english | noul | role | semantic-detection | 2040 | 0.501 | 0.501 | 0.233 | 0.516 | 0.486 |
| laya-english | noul | rule_held_out | False | 1208 | 0.498 | 0.506 | 0.226 | 0.542 | 0.470 |
| laya-english | noul | rule_held_out | True | 832 | 0.505 | 0.510 | 0.242 | 0.493 | 0.528 |
| laya-english | noul | source accuracy | human | 2040 | 0.501 | — | — | — | — |
| laya-english | choice | granularity | document | 615 | 0.429 | 0.440 | 0.048 | 0.593 | 0.288 |
| laya-english | choice | granularity | paragraph | 451 | 0.441 | 0.457 | 0.039 | 0.636 | 0.278 |
| laya-english | choice | granularity | sentence | 220 | 0.473 | 0.436 | 0.086 | 0.533 | 0.338 |
| laya-english | choice | provenance | human | 1286 | 0.441 | 0.441 | 0.030 | 0.593 | 0.289 |
| laya-english | choice | role | finding-confirmation | 1286 | 0.441 | 0.441 | 0.030 | 0.593 | 0.289 |
| laya-english | choice | rule_held_out | False | 693 | 0.358 | 0.415 | 0.112 | 0.540 | 0.291 |
| laya-english | choice | rule_held_out | True | 593 | 0.538 | 0.449 | 0.105 | 0.614 | 0.285 |
| laya-english | choice | source accuracy | human | 1286 | 0.441 | — | — | — | — |
| laya-multilingual | noul | granularity | document | 990 | 0.514 | 0.519 | 0.336 | 0.801 | 0.237 |
| laya-multilingual | noul | granularity | paragraph | 733 | 0.546 | 0.544 | 0.289 | 0.762 | 0.325 |
| laya-multilingual | noul | granularity | sentence | 317 | 0.650 | 0.651 | 0.207 | 0.620 | 0.682 |
| laya-multilingual | noul | provenance | human | 2040 | 0.547 | 0.547 | 0.296 | 0.758 | 0.335 |
| laya-multilingual | noul | role | semantic-detection | 2040 | 0.547 | 0.547 | 0.296 | 0.758 | 0.335 |
| laya-multilingual | noul | rule_held_out | False | 1208 | 0.520 | 0.556 | 0.322 | 0.730 | 0.382 |
| laya-multilingual | noul | rule_held_out | True | 832 | 0.585 | 0.500 | 0.261 | 0.782 | 0.217 |
| laya-multilingual | noul | source accuracy | human | 2040 | 0.547 | — | — | — | — |
| laya-multilingual | choice | granularity | document | 615 | 0.454 | 0.479 | 0.170 | 0.832 | 0.127 |
| laya-multilingual | choice | granularity | paragraph | 451 | 0.282 | 0.298 | 0.319 | 0.485 | 0.110 |
| laya-multilingual | choice | granularity | sentence | 220 | 0.282 | 0.269 | 0.337 | 0.303 | 0.235 |
| laya-multilingual | choice | provenance | human | 1286 | 0.364 | 0.364 | 0.250 | 0.596 | 0.132 |
| laya-multilingual | choice | role | finding-confirmation | 1286 | 0.364 | 0.364 | 0.250 | 0.596 | 0.132 |
| laya-multilingual | choice | rule_held_out | False | 693 | 0.241 | 0.337 | 0.370 | 0.545 | 0.128 |
| laya-multilingual | choice | rule_held_out | True | 593 | 0.508 | 0.381 | 0.128 | 0.616 | 0.146 |
| laya-multilingual | choice | source accuracy | human | 1286 | 0.364 | — | — | — | — |
| laya-typed-decisions | noul | granularity | document | 990 | 0.554 | 0.554 | 0.056 | 0.593 | 0.515 |
| laya-typed-decisions | noul | granularity | paragraph | 733 | 0.569 | 0.569 | 0.038 | 0.527 | 0.612 |
| laya-typed-decisions | noul | granularity | sentence | 317 | 0.577 | 0.583 | 0.086 | 0.387 | 0.779 |
| laya-typed-decisions | noul | provenance | human | 2040 | 0.563 | 0.563 | 0.044 | 0.536 | 0.589 |
| laya-typed-decisions | noul | role | semantic-detection | 2040 | 0.563 | 0.563 | 0.044 | 0.536 | 0.589 |
| laya-typed-decisions | noul | rule_held_out | False | 1208 | 0.565 | 0.539 | 0.047 | 0.414 | 0.664 |
| laya-typed-decisions | noul | rule_held_out | True | 832 | 0.559 | 0.522 | 0.051 | 0.644 | 0.400 |
| laya-typed-decisions | noul | source accuracy | human | 2040 | 0.563 | — | — | — | — |
| laya-typed-decisions | choice | granularity | document | 615 | 0.398 | 0.395 | 0.026 | 0.351 | 0.439 |
| laya-typed-decisions | choice | granularity | paragraph | 451 | 0.359 | 0.367 | 0.081 | 0.456 | 0.278 |
| laya-typed-decisions | choice | granularity | sentence | 220 | 0.318 | 0.267 | 0.110 | 0.401 | 0.132 |
| laya-typed-decisions | choice | provenance | human | 1286 | 0.371 | 0.371 | 0.052 | 0.397 | 0.345 |
| laya-typed-decisions | choice | role | finding-confirmation | 1286 | 0.371 | 0.371 | 0.052 | 0.397 | 0.345 |
| laya-typed-decisions | choice | rule_held_out | False | 693 | 0.381 | 0.397 | 0.069 | 0.433 | 0.362 |
| laya-typed-decisions | choice | rule_held_out | True | 593 | 0.359 | 0.333 | 0.051 | 0.382 | 0.285 |
| laya-typed-decisions | choice | source accuracy | human | 1286 | 0.371 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 1118 | 0.461 | 35 | 0.521 | 0.545 | 0.541 |
| kev-0.8b-ft-s17 | 1118 | 0.564 | 35 | 0.747 | 0.741 | 0.727 |
| kev-0.8b-ft-s18 | 1118 | 0.488 | 35 | 0.741 | 0.743 | 0.719 |
| kev-0.8b-ft-s19 | 1118 | 0.411 | 35 | 0.750 | 0.746 | 0.742 |
| kev-4b | 1118 | 0.411 | 35 | 0.561 | 0.600 | 0.600 |
| kev-4b-ft-s17 | 1118 | 0.474 | 35 | 0.847 | 0.851 | 0.847 |
| kev-4b-ft-s18 | 1118 | 0.325 | 35 | 0.873 | 0.880 | 0.875 |
| kev-4b-ft-s19 | 1118 | 0.450 | 35 | 0.858 | 0.861 | 0.850 |
| kev-9b | 1118 | 0.511 | 35 | 0.609 | 0.610 | 0.595 |
| kev-9b-ft-s17 | 1118 | 0.487 | 35 | 0.878 | 0.878 | 0.868 |
| kev-9b-ft-s18 | 1118 | 0.488 | 35 | 0.875 | 0.874 | 0.861 |
| kev-9b-ft-s19 | 1118 | 0.265 | 35 | 0.869 | 0.874 | 0.870 |
| laya-english | 1118 | 0.125 | 35 | 0.500 | 0.500 | 0.529 |
| laya-multilingual | 1118 | 0.979 | 35 | 0.547 | 0.503 | 0.499 |
| laya-typed-decisions | 1118 | 0.471 | 35 | 0.563 | 0.563 | 0.572 |

## Interpretation and caveats

- Test label origins: construction (3326). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice no-defect=643, real-defect=643; yes/no False=1020, True=1020. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.32 finding-confirmation, κ=0.42 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
