# Corpus evaluation report: `corpus-v3-confident`

## Status

- Pre-v4 baseline. v4 rebuilds the judge items against the merged lint rules (main 7544c168e0: curly-quotes and uniform-paragraph-mass retired, about 13 rules narrowed) and the human-labelled rows, then re-tests every arm on the rebuilt items; v4 scores are not comparable with this test export.
- The v3 full and confident variants differ only in training data: confident drops teacher-panel labels below 0.85 posterior confidence (12,185 train rows vs 14,449; see each variant's export-manifest.json).

## Dataset and coverage

- Campaign: `corpus-20260930-s17-v3/confident`. Round 2 on the v3 export (confident). Base arms are evaluated in the full campaign only: both variants share test and calibration. Laya fine-tunes are left out until round 1 shows Laya fine-tuning beats its base.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 9 of 9 required (`kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 29 of 47 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1674 examples; SHA-256 `fca2452aa1e15bb80bc10514699e3495cbed42a690626cc5aaf4f7534293d8a9`.
- Test: 3326 examples; SHA-256 `f973edaa3b5feda1ee549f8be3df661fdd49e25f8ed2c53db7b45cdbd4c892e7`.
- Test composition: label origins `construction`=3326; choice labels no-defect=643, real-defect=643; yes/no labels False=1020, True=1020.

## Headline by role

Each arm's numbers come from `results/corpus-v3-confident/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1286 (real-defect=643, no-defect=643).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.774 | 0.713–0.831 | 0.848 | 0.700 | 0.077 | 0.073 | NVIDIA A10G | 17.554 | $0.5300 |
| kev-0.8b-ft-s18 | 0.763 | 0.706–0.818 | 0.806 | 0.720 | 0.077 | 0.071 | NVIDIA A10G | 17.518 | $0.6956 |
| kev-0.8b-ft-s19 | 0.806 | 0.759–0.847 | 0.832 | 0.779 | 0.043 | 0.053 | NVIDIA A10G | 17.426 | $0.7000 |
| kev-0.8b FT mean ± SD [range] | 0.781 ± 0.022 [0.763–0.806] | — | 0.828 ± 0.021 [0.806–0.848] | 0.733 ± 0.041 [0.700–0.779] | 0.066 ± 0.019 [0.043–0.077] | 0.066 ± 0.011 [0.053–0.073] | — | — | — |
| kev-4b-ft-s17 | 0.854 | 0.803–0.902 | 0.938 | 0.770 | 0.087 | 0.066 | NVIDIA A10G | 65.058 | $2.6325 |
| kev-4b-ft-s18 | 0.849 | 0.800–0.899 | 0.932 | 0.767 | 0.086 | 0.061 | NVIDIA A10G | 65.358 | $0.9100 |
| kev-4b-ft-s19 | 0.840 | 0.782–0.897 | 0.930 | 0.750 | 0.095 | 0.067 | NVIDIA A10G | 65.088 | $1.1867 |
| kev-4b FT mean ± SD [range] | 0.848 ± 0.007 [0.840–0.854] | — | 0.933 ± 0.004 [0.930–0.938] | 0.762 ± 0.011 [0.750–0.770] | 0.089 ± 0.005 [0.086–0.095] | 0.065 ± 0.004 [0.061–0.067] | — | — | — |
| kev-9b-ft-s17 | 0.868 | 0.820–0.914 | 0.936 | 0.799 | 0.054 | 0.054 | NVIDIA L40S | 62.236 | $1.1089 |
| kev-9b-ft-s18 | 0.883 | 0.835–0.929 | 0.944 | 0.823 | 0.056 | 0.033 | NVIDIA L40S | 62.308 | $1.2792 |
| kev-9b-ft-s19 | 0.881 | 0.838–0.920 | 0.938 | 0.824 | 0.050 | 0.034 | NVIDIA L40S | 62.441 | $1.2875 |
| kev-9b FT mean ± SD [range] | 0.877 ± 0.008 [0.868–0.883] | — | 0.939 ± 0.004 [0.936–0.944] | 0.815 ± 0.014 [0.799–0.824] | 0.053 ± 0.003 [0.050–0.056] | 0.040 ± 0.012 [0.033–0.054] | — | — | — |

- Best single arm: `kev-9b-ft-s18` (balanced accuracy 0.883).
- Best fine-tuned family by seed mean: `kev-9b` (0.877 ± 0.008 [0.868–0.883]).

### semantic-detection (`noul`)

Test items: 2040 (True=1020, False=1020).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.758 | 0.705–0.802 | 0.675 | 0.841 | 0.083 | 0.044 | NVIDIA A10G | 17.554 | $0.5300 |
| kev-0.8b-ft-s18 | 0.744 | 0.692–0.791 | 0.643 | 0.845 | 0.088 | 0.054 | NVIDIA A10G | 17.518 | $0.6956 |
| kev-0.8b-ft-s19 | 0.758 | 0.705–0.804 | 0.669 | 0.847 | 0.069 | 0.040 | NVIDIA A10G | 17.426 | $0.7000 |
| kev-0.8b FT mean ± SD [range] | 0.753 ± 0.008 [0.744–0.758] | — | 0.662 ± 0.017 [0.643–0.675] | 0.844 ± 0.003 [0.841–0.847] | 0.080 ± 0.010 [0.069–0.088] | 0.046 ± 0.007 [0.040–0.054] | — | — | — |
| kev-4b-ft-s17 | 0.883 | 0.826–0.920 | 0.851 | 0.916 | 0.040 | 0.022 | NVIDIA A10G | 65.058 | $2.6325 |
| kev-4b-ft-s18 | 0.867 | 0.819–0.906 | 0.812 | 0.922 | 0.048 | 0.034 | NVIDIA A10G | 65.358 | $0.9100 |
| kev-4b-ft-s19 | 0.867 | 0.817–0.905 | 0.815 | 0.919 | 0.038 | 0.032 | NVIDIA A10G | 65.088 | $1.1867 |
| kev-4b FT mean ± SD [range] | 0.872 ± 0.010 [0.867–0.883] | — | 0.826 ± 0.022 [0.812–0.851] | 0.919 ± 0.003 [0.916–0.922] | 0.042 ± 0.006 [0.038–0.048] | 0.029 ± 0.006 [0.022–0.034] | — | — | — |
| kev-9b-ft-s17 | 0.880 | 0.824–0.925 | 0.817 | 0.943 | 0.035 | 0.033 | NVIDIA L40S | 62.236 | $1.1089 |
| kev-9b-ft-s18 | 0.883 | 0.826–0.920 | 0.837 | 0.928 | 0.062 | 0.024 | NVIDIA L40S | 62.308 | $1.2792 |
| kev-9b-ft-s19 | 0.876 | 0.822–0.915 | 0.817 | 0.935 | 0.060 | 0.030 | NVIDIA L40S | 62.441 | $1.2875 |
| kev-9b FT mean ± SD [range] | 0.880 ± 0.003 [0.876–0.883] | — | 0.824 ± 0.012 [0.817–0.837] | 0.936 ± 0.007 [0.928–0.943] | 0.052 ± 0.015 [0.035–0.062] | 0.029 ± 0.004 [0.024–0.033] | — | — | — |

- Best single arm: `kev-4b-ft-s17` (balanced accuracy 0.883).
- Best fine-tuned family by seed mean: `kev-9b` (0.880 ± 0.003 [0.876–0.883]).

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | corpus-v3-full | 0.191 | 0.781 | +0.589 | 3/3 | +0.684 | +0.495 | -0.167 | -0.078 |
| kev-4b | corpus-v3-full | 0.295 | 0.848 | +0.553 | 3/3 | +0.442 | +0.664 | -0.034 | +0.002 |
| kev-9b | corpus-v3-full | 0.489 | 0.877 | +0.388 | 3/3 | +0.131 | +0.646 | -0.048 | -0.056 |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | corpus-v3-full | 0.521 | 0.753 | +0.232 | 3/3 | +0.576 | -0.111 | -0.078 | +0.038 |
| kev-4b | corpus-v3-full | 0.561 | 0.872 | +0.311 | 3/3 | +0.607 | +0.016 | -0.048 | -0.020 |
| kev-9b | corpus-v3-full | 0.609 | 0.880 | +0.271 | 3/3 | +0.367 | +0.175 | -0.037 | -0.015 |

## Comparison with `corpus-v3-full`

Both campaigns score the same test and calibration export (hashes verified). Δ is `corpus-v3-confident` minus `corpus-v3-full` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.

### finding-confirmation (`choice`)

| Family | corpus-v3-confident bal. acc. | corpus-v3-full bal. acc. | Δ bal. acc. | Seeds better | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.781 ± 0.022 [0.763–0.806] | 0.780 ± 0.016 [0.770–0.799] | +0.001 | 2/3 | -0.009 | +0.010 | +0.012 | -0.000 |
| kev-4b | 0.848 ± 0.007 [0.840–0.854] | 0.825 ± 0.003 [0.821–0.827] | +0.023 | 3/3 | -0.011 | +0.057 | -0.007 | -0.019 |
| kev-9b | 0.877 ± 0.008 [0.868–0.883] | 0.868 ± 0.012 [0.858–0.881] | +0.009 | 3/3 | -0.018 | +0.037 | -0.005 | -0.001 |

### semantic-detection (`noul`)

| Family | corpus-v3-confident bal. acc. | corpus-v3-full bal. acc. | Δ bal. acc. | Seeds better | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.753 ± 0.008 [0.744–0.758] | 0.746 ± 0.004 [0.741–0.750] | +0.007 | 3/3 | -0.020 | +0.035 | +0.024 | +0.013 |
| kev-4b | 0.872 ± 0.010 [0.867–0.883] | 0.859 ± 0.013 [0.847–0.873] | +0.013 | 2/3 | +0.022 | +0.004 | -0.008 | -0.002 |
| kev-9b | 0.880 ± 0.003 [0.876–0.883] | 0.874 ± 0.004 [0.869–0.878] | +0.006 | 3/3 | -0.009 | +0.020 | -0.008 | +0.006 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1 / 0 / 0 | $9.08 | slopvac-judge-kev-08b-s17-20260929214258 | $9.08 | 1 / 0 / 0 | $0.53 | $9.61 |
| kev-0.8b-ft-s18 | 1 / 0 / 0 | $9.16 | slopvac-judge-kev-08b-s18-20260930012603 | $9.16 | 1 / 0 / 0 | $0.70 | $9.86 |
| kev-0.8b-ft-s19 | 1 / 16 / 0 | $7.42 | slopvac-judge-kev-08b-s19-20260930024231 | $7.29 | 1 / 0 / 0 | $0.70 | $8.12 |
| kev-4b-ft-s17 | 1 / 0 / 0 | $22.60 | slopvac-judge-kev-4b-s17-20260930022622 | $22.60 | 1 / 0 / 0 | $2.63 | $25.23 |
| kev-4b-ft-s18 | 1 / 0 / 0 | $22.72 | slopvac-judge-kev-4b-s18-20260930090318 | $22.72 | 1 / 0 / 0 | $0.91 | $23.63 |
| kev-4b-ft-s19 | 1 / 0 / 0 | $35.55 | slopvac-judge-kev-4b-s19-20260930090332 | $35.55 | 1 / 0 / 0 | $1.19 | $36.74 |
| kev-9b-ft-s17 | 1 / 3 / 0 | $28.53 | slopvac-judge-kev-9b-s17-20260930114216 | $28.53 | 1 / 0 / 0 | $1.11 | $29.64 |
| kev-9b-ft-s18 | 1 / 3 / 0 | $45.69 | slopvac-judge-kev-9b-s18-20260930114303 | $45.69 | 1 / 0 / 3 | $1.28 | $46.97 |
| kev-9b-ft-s19 | 1 / 4 / 0 | $20.49 | slopvac-judge-kev-9b-s19-20260930120747 | $20.49 | 1 / 0 / 0 | $1.29 | $21.78 |

Campaign total: **$211.58 USD** (training $201.25, evaluation $10.33) over 35 training and 12 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s19 | training | Failed | 1 | $0.13 | AlgorithmError: , exit code: 2 |
| kev-0.8b-ft-s19 | training | Failed | 15 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6.2xlarge for training job usage' is 1… |
| kev-9b-ft-s17 | training | Failed | 3 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.8xlarge for training job usage' is … |
| kev-9b-ft-s18 | evaluation | Stopped | 3 | $0.00 | scheduler marker `capacity_rotation` |
| kev-9b-ft-s18 | training | Failed | 3 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.8xlarge for training job usage' is … |
| kev-9b-ft-s19 | training | Failed | 4 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.8xlarge for training job usage' is … |

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
| kev-0.8b-ft-s17 | 2040 | 0.758 | 0.758 | 0.832 | 0.176 | 0.539 | 0.083 | 0.172 | 0.517 | 0.044 | 0.705–0.802 | 0.048–0.136 | 0.023–0.099 | 0.675 | 0.841 | — | — | — | 17.554 | 58.594 |
| kev-0.8b-ft-s18 | 2040 | 0.744 | 0.744 | 0.838 | 0.176 | 0.544 | 0.088 | 0.171 | 0.516 | 0.054 | 0.692–0.791 | 0.049–0.142 | 0.027–0.105 | 0.643 | 0.845 | — | — | — | 17.518 | 58.025 |
| kev-0.8b-ft-s19 | 2040 | 0.758 | 0.758 | 0.846 | 0.170 | 0.518 | 0.069 | 0.167 | 0.503 | 0.040 | 0.705–0.804 | 0.037–0.115 | 0.023–0.086 | 0.669 | 0.847 | — | — | — | 17.426 | 57.816 |
| FT mean ± SD [range] | — | 0.753 ± 0.008 [0.744–0.758] | 0.753 ± 0.008 [0.744–0.758] | 0.839 ± 0.007 [0.832–0.846] | 0.174 ± 0.004 [0.170–0.176] | 0.534 ± 0.014 [0.518–0.544] | 0.080 ± 0.010 [0.069–0.088] | 0.170 ± 0.003 [0.167–0.172] | 0.512 ± 0.008 [0.503–0.517] | 0.046 ± 0.007 [0.040–0.054] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1286 | 0.774 | 0.774 | 0.854 | 0.326 | 0.511 | 0.077 | 0.324 | 0.506 | 0.073 | 0.713–0.831 | 0.036–0.140 | 0.034–0.135 | — | — | 0.000 | 0.924 | 0.077 | 17.554 | 58.594 |
| kev-0.8b-ft-s18 | 1286 | 0.763 | 0.763 | 0.854 | 0.323 | 0.496 | 0.077 | 0.321 | 0.493 | 0.071 | 0.706–0.818 | 0.036–0.128 | 0.030–0.121 | — | — | 0.000 | 0.902 | 0.100 | 17.518 | 58.025 |
| kev-0.8b-ft-s19 | 1286 | 0.806 | 0.806 | 0.886 | 0.277 | 0.435 | 0.043 | 0.280 | 0.441 | 0.053 | 0.759–0.847 | 0.023–0.082 | 0.030–0.090 | — | — | 0.000 | 0.932 | 0.072 | 17.426 | 57.816 |
| FT mean ± SD [range] | — | 0.781 ± 0.022 [0.763–0.806] | 0.781 ± 0.022 [0.763–0.806] | 0.864 ± 0.018 [0.854–0.886] | 0.309 ± 0.027 [0.277–0.326] | 0.481 ± 0.041 [0.435–0.511] | 0.066 ± 0.019 [0.043–0.077] | 0.308 ± 0.025 [0.280–0.324] | 0.480 ± 0.034 [0.441–0.506] | 0.066 ± 0.011 [0.053–0.073] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.919 ± 0.015 [0.902–0.932] | 0.083 ± 0.015 [0.072–0.100] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 2040 | 0.883 | 0.883 | 0.947 | 0.089 | 0.306 | 0.040 | 0.088 | 0.296 | 0.022 | 0.826–0.920 | 0.015–0.091 | 0.010–0.073 | 0.851 | 0.916 | — | — | — | 65.058 | 166.127 |
| kev-4b-ft-s18 | 2040 | 0.867 | 0.867 | 0.944 | 0.098 | 0.328 | 0.048 | 0.096 | 0.319 | 0.034 | 0.819–0.906 | 0.022–0.092 | 0.018–0.079 | 0.812 | 0.922 | — | — | — | 65.358 | 166.681 |
| kev-4b-ft-s19 | 2040 | 0.867 | 0.867 | 0.939 | 0.099 | 0.334 | 0.038 | 0.099 | 0.329 | 0.032 | 0.817–0.905 | 0.015–0.086 | 0.014–0.080 | 0.815 | 0.919 | — | — | — | 65.088 | 166.438 |
| FT mean ± SD [range] | — | 0.872 ± 0.010 [0.867–0.883] | 0.872 ± 0.010 [0.867–0.883] | 0.943 ± 0.004 [0.939–0.947] | 0.095 ± 0.005 [0.089–0.099] | 0.322 ± 0.015 [0.306–0.334] | 0.042 ± 0.006 [0.038–0.048] | 0.094 ± 0.006 [0.088–0.099] | 0.315 ± 0.017 [0.296–0.329] | 0.029 ± 0.006 [0.022–0.034] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 1286 | 0.854 | 0.854 | 0.928 | 0.238 | 0.426 | 0.087 | 0.230 | 0.396 | 0.066 | 0.803–0.902 | 0.045–0.137 | 0.031–0.116 | — | — | 0.000 | 0.953 | 0.046 | 65.058 | 166.127 |
| kev-4b-ft-s18 | 1286 | 0.849 | 0.849 | 0.924 | 0.238 | 0.435 | 0.086 | 0.229 | 0.396 | 0.061 | 0.800–0.899 | 0.045–0.132 | 0.029–0.107 | — | — | 0.000 | 0.956 | 0.054 | 65.358 | 166.681 |
| kev-4b-ft-s19 | 1286 | 0.840 | 0.840 | 0.920 | 0.259 | 0.465 | 0.095 | 0.247 | 0.422 | 0.067 | 0.782–0.897 | 0.047–0.154 | 0.027–0.123 | — | — | 0.000 | 0.966 | 0.039 | 65.088 | 166.438 |
| FT mean ± SD [range] | — | 0.848 ± 0.007 [0.840–0.854] | 0.848 ± 0.007 [0.840–0.854] | 0.924 ± 0.004 [0.920–0.928] | 0.245 ± 0.012 [0.238–0.259] | 0.442 ± 0.021 [0.426–0.465] | 0.089 ± 0.005 [0.086–0.095] | 0.235 ± 0.010 [0.229–0.247] | 0.404 ± 0.015 [0.396–0.422] | 0.065 ± 0.004 [0.061–0.067] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.959 ± 0.006 [0.953–0.966] | 0.046 ± 0.008 [0.039–0.054] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 2040 | 0.880 | 0.880 | 0.949 | 0.093 | 0.314 | 0.035 | 0.093 | 0.313 | 0.033 | 0.824–0.925 | 0.013–0.089 | 0.013–0.087 | 0.817 | 0.943 | — | — | — | 62.236 | 106.519 |
| kev-9b-ft-s18 | 2040 | 0.883 | 0.883 | 0.953 | 0.090 | 0.344 | 0.062 | 0.086 | 0.295 | 0.024 | 0.826–0.920 | 0.033–0.114 | 0.012–0.076 | 0.837 | 0.928 | — | — | — | 62.308 | 108.901 |
| kev-9b-ft-s19 | 2040 | 0.876 | 0.876 | 0.948 | 0.094 | 0.331 | 0.060 | 0.090 | 0.302 | 0.030 | 0.822–0.915 | 0.032–0.110 | 0.017–0.079 | 0.817 | 0.935 | — | — | — | 62.441 | 106.705 |
| FT mean ± SD [range] | — | 0.880 ± 0.003 [0.876–0.883] | 0.880 ± 0.003 [0.876–0.883] | 0.950 ± 0.003 [0.948–0.953] | 0.093 ± 0.002 [0.090–0.094] | 0.330 ± 0.015 [0.314–0.344] | 0.052 ± 0.015 [0.035–0.062] | 0.090 ± 0.004 [0.086–0.093] | 0.303 ± 0.009 [0.295–0.313] | 0.029 ± 0.004 [0.024–0.033] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 1286 | 0.868 | 0.868 | 0.961 | 0.190 | 0.316 | 0.054 | 0.190 | 0.316 | 0.054 | 0.820–0.914 | 0.029–0.088 | 0.030–0.087 | — | — | 0.000 | 0.971 | 0.031 | 62.236 | 106.519 |
| kev-9b-ft-s18 | 1286 | 0.883 | 0.883 | 0.959 | 0.179 | 0.306 | 0.056 | 0.172 | 0.291 | 0.033 | 0.835–0.929 | 0.023–0.101 | 0.018–0.077 | — | — | 0.000 | 0.964 | 0.047 | 62.308 | 108.901 |
| kev-9b-ft-s19 | 1286 | 0.881 | 0.881 | 0.963 | 0.176 | 0.295 | 0.050 | 0.171 | 0.285 | 0.034 | 0.838–0.920 | 0.022–0.089 | 0.017–0.071 | — | — | 0.001 | 0.971 | 0.034 | 62.441 | 106.705 |
| FT mean ± SD [range] | — | 0.877 ± 0.008 [0.868–0.883] | 0.877 ± 0.008 [0.868–0.883] | 0.961 ± 0.002 [0.959–0.963] | 0.181 ± 0.008 [0.176–0.190] | 0.306 ± 0.010 [0.295–0.316] | 0.053 ± 0.003 [0.050–0.056] | 0.178 ± 0.010 [0.171–0.190] | 0.297 ± 0.016 [0.285–0.316] | 0.040 ± 0.012 [0.033–0.054] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.001] | 0.969 ± 0.004 [0.964–0.971] | 0.037 ± 0.009 [0.031–0.047] | — | — |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 17.554 | 58.594 | 636 | $0.5300 | sv-eval-kev-08b-ft-s17-260930012615473600 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.518 | 58.025 | 626 | $0.6956 | sv-eval-kev-08b-ft-s18-260930090347579860 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 17.426 | 57.816 | 630 | $0.7000 | sv-eval-kev-08b-ft-s19-260930090411728637 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.12xlarge | us-east-1 | 65.058 | 166.127 | 1053 | $2.6325 | sv-eval-kev-4b-ft-s17-260930090442691447 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 65.358 | 166.681 | 1092 | $0.9100 | sv-eval-kev-4b-ft-s18-260930123650786198 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 65.088 | 166.438 | 1068 | $1.1867 | sv-eval-kev-4b-ft-s19-260930123715363227 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.2xlarge | us-east-1 | 62.236 | 106.519 | 998 | $1.1089 | sv-eval-kev-9b-ft-s17-261001110558567089 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.4xlarge | us-east-1 | 62.308 | 108.901 | 921 | $1.2792 | sv-eval-kev-9b-ft-s18-261001203654647432 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.4xlarge | us-east-1 | 62.441 | 106.705 | 927 | $1.2875 | sv-eval-kev-9b-ft-s19-261001110637467703 |

Total billed evaluation cost for the reported arms: **$10.3304 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | noul | granularity | document | 990 | 0.761 | 0.760 | 0.071 | 0.700 | 0.819 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 733 | 0.752 | 0.752 | 0.094 | 0.673 | 0.832 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 317 | 0.763 | 0.768 | 0.093 | 0.601 | 0.935 |
| kev-0.8b-ft-s17 | noul | provenance | human | 2040 | 0.758 | 0.758 | 0.083 | 0.675 | 0.841 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2040 | 0.758 | 0.758 | 0.083 | 0.675 | 0.841 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1208 | 0.786 | 0.770 | 0.067 | 0.692 | 0.847 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 832 | 0.718 | 0.743 | 0.105 | 0.659 | 0.828 |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 2040 | 0.758 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 615 | 0.780 | 0.774 | 0.064 | 0.691 | 0.858 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 451 | 0.783 | 0.775 | 0.085 | 0.684 | 0.865 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 220 | 0.736 | 0.736 | 0.126 | 0.737 | 0.735 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1286 | 0.774 | 0.774 | 0.077 | 0.700 | 0.848 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1286 | 0.774 | 0.774 | 0.077 | 0.700 | 0.848 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 693 | 0.837 | 0.828 | 0.047 | 0.807 | 0.848 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 593 | 0.700 | 0.751 | 0.143 | 0.656 | 0.847 |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1286 | 0.774 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 990 | 0.736 | 0.735 | 0.094 | 0.649 | 0.821 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 733 | 0.745 | 0.746 | 0.089 | 0.654 | 0.837 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 317 | 0.767 | 0.771 | 0.070 | 0.601 | 0.942 |
| kev-0.8b-ft-s18 | noul | provenance | human | 2040 | 0.744 | 0.744 | 0.088 | 0.643 | 0.845 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2040 | 0.744 | 0.744 | 0.088 | 0.643 | 0.845 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1208 | 0.781 | 0.760 | 0.071 | 0.659 | 0.862 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 832 | 0.690 | 0.716 | 0.113 | 0.629 | 0.803 |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 2040 | 0.744 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 615 | 0.759 | 0.756 | 0.074 | 0.712 | 0.800 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 451 | 0.783 | 0.777 | 0.055 | 0.709 | 0.845 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 220 | 0.732 | 0.721 | 0.131 | 0.750 | 0.691 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1286 | 0.763 | 0.763 | 0.077 | 0.720 | 0.806 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1286 | 0.763 | 0.763 | 0.077 | 0.720 | 0.806 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 693 | 0.801 | 0.791 | 0.042 | 0.770 | 0.812 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 593 | 0.718 | 0.740 | 0.120 | 0.700 | 0.781 |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1286 | 0.763 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 990 | 0.748 | 0.747 | 0.076 | 0.678 | 0.817 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 733 | 0.761 | 0.762 | 0.083 | 0.670 | 0.854 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 317 | 0.779 | 0.783 | 0.070 | 0.638 | 0.929 |
| kev-0.8b-ft-s19 | noul | provenance | human | 2040 | 0.758 | 0.758 | 0.069 | 0.669 | 0.847 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2040 | 0.758 | 0.758 | 0.069 | 0.669 | 0.847 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1208 | 0.800 | 0.782 | 0.056 | 0.692 | 0.871 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 832 | 0.696 | 0.717 | 0.095 | 0.648 | 0.786 |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 2040 | 0.758 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 615 | 0.815 | 0.813 | 0.029 | 0.793 | 0.833 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 451 | 0.823 | 0.818 | 0.038 | 0.767 | 0.869 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 220 | 0.745 | 0.730 | 0.118 | 0.770 | 0.691 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1286 | 0.806 | 0.806 | 0.043 | 0.779 | 0.832 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1286 | 0.806 | 0.806 | 0.043 | 0.779 | 0.832 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 693 | 0.833 | 0.826 | 0.044 | 0.813 | 0.840 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 593 | 0.774 | 0.784 | 0.061 | 0.765 | 0.803 |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1286 | 0.806 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 990 | 0.879 | 0.878 | 0.046 | 0.854 | 0.903 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 733 | 0.884 | 0.884 | 0.039 | 0.851 | 0.917 |
| kev-4b-ft-s17 | noul | granularity | sentence | 317 | 0.896 | 0.898 | 0.029 | 0.840 | 0.955 |
| kev-4b-ft-s17 | noul | provenance | human | 2040 | 0.883 | 0.883 | 0.040 | 0.851 | 0.916 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2040 | 0.883 | 0.883 | 0.040 | 0.851 | 0.916 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1208 | 0.897 | 0.890 | 0.032 | 0.856 | 0.925 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 832 | 0.863 | 0.870 | 0.052 | 0.847 | 0.893 |
| kev-4b-ft-s17 | noul | source accuracy | human | 2040 | 0.883 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 615 | 0.839 | 0.832 | 0.095 | 0.730 | 0.933 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 451 | 0.878 | 0.871 | 0.068 | 0.791 | 0.951 |
| kev-4b-ft-s17 | choice | granularity | sentence | 220 | 0.845 | 0.864 | 0.109 | 0.816 | 0.912 |
| kev-4b-ft-s17 | choice | provenance | human | 1286 | 0.854 | 0.854 | 0.087 | 0.770 | 0.938 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1286 | 0.854 | 0.854 | 0.087 | 0.770 | 0.938 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 693 | 0.908 | 0.874 | 0.051 | 0.802 | 0.947 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 593 | 0.791 | 0.831 | 0.132 | 0.757 | 0.905 |
| kev-4b-ft-s17 | choice | source accuracy | human | 1286 | 0.854 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 990 | 0.865 | 0.864 | 0.058 | 0.821 | 0.907 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 733 | 0.869 | 0.870 | 0.048 | 0.816 | 0.923 |
| kev-4b-ft-s18 | noul | granularity | sentence | 317 | 0.868 | 0.870 | 0.057 | 0.773 | 0.968 |
| kev-4b-ft-s18 | noul | provenance | human | 2040 | 0.867 | 0.867 | 0.048 | 0.812 | 0.922 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2040 | 0.867 | 0.867 | 0.048 | 0.812 | 0.922 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1208 | 0.897 | 0.890 | 0.028 | 0.856 | 0.925 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 832 | 0.822 | 0.843 | 0.079 | 0.773 | 0.914 |
| kev-4b-ft-s18 | noul | source accuracy | human | 2040 | 0.867 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 615 | 0.846 | 0.839 | 0.091 | 0.747 | 0.930 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 451 | 0.860 | 0.852 | 0.073 | 0.757 | 0.947 |
| kev-4b-ft-s18 | choice | granularity | sentence | 220 | 0.836 | 0.849 | 0.108 | 0.816 | 0.882 |
| kev-4b-ft-s18 | choice | provenance | human | 1286 | 0.849 | 0.849 | 0.086 | 0.767 | 0.932 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1286 | 0.849 | 0.849 | 0.086 | 0.767 | 0.932 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 693 | 0.906 | 0.884 | 0.048 | 0.834 | 0.933 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 593 | 0.782 | 0.833 | 0.134 | 0.739 | 0.927 |
| kev-4b-ft-s18 | choice | source accuracy | human | 1286 | 0.849 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 990 | 0.862 | 0.861 | 0.039 | 0.813 | 0.909 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 733 | 0.866 | 0.867 | 0.049 | 0.824 | 0.909 |
| kev-4b-ft-s19 | noul | granularity | sentence | 317 | 0.883 | 0.886 | 0.036 | 0.798 | 0.974 |
| kev-4b-ft-s19 | noul | provenance | human | 2040 | 0.867 | 0.867 | 0.038 | 0.815 | 0.919 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2040 | 0.867 | 0.867 | 0.038 | 0.815 | 0.919 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1208 | 0.898 | 0.892 | 0.025 | 0.862 | 0.922 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 832 | 0.821 | 0.842 | 0.068 | 0.773 | 0.910 |
| kev-4b-ft-s19 | noul | source accuracy | human | 2040 | 0.867 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 615 | 0.841 | 0.834 | 0.103 | 0.737 | 0.930 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 451 | 0.847 | 0.839 | 0.091 | 0.743 | 0.935 |
| kev-4b-ft-s19 | choice | granularity | sentence | 220 | 0.823 | 0.847 | 0.121 | 0.783 | 0.912 |
| kev-4b-ft-s19 | choice | provenance | human | 1286 | 0.840 | 0.840 | 0.095 | 0.750 | 0.930 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1286 | 0.840 | 0.840 | 0.095 | 0.750 | 0.930 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 693 | 0.906 | 0.875 | 0.039 | 0.807 | 0.943 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 593 | 0.762 | 0.805 | 0.166 | 0.726 | 0.883 |
| kev-4b-ft-s19 | choice | source accuracy | human | 1286 | 0.840 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 990 | 0.872 | 0.871 | 0.036 | 0.811 | 0.930 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 733 | 0.894 | 0.894 | 0.045 | 0.846 | 0.942 |
| kev-9b-ft-s17 | noul | granularity | sentence | 317 | 0.874 | 0.877 | 0.049 | 0.767 | 0.987 |
| kev-9b-ft-s17 | noul | provenance | human | 2040 | 0.880 | 0.880 | 0.035 | 0.817 | 0.943 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2040 | 0.880 | 0.880 | 0.035 | 0.817 | 0.943 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1208 | 0.913 | 0.903 | 0.020 | 0.854 | 0.952 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 832 | 0.832 | 0.852 | 0.065 | 0.784 | 0.921 |
| kev-9b-ft-s17 | noul | source accuracy | human | 2040 | 0.880 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 615 | 0.870 | 0.865 | 0.054 | 0.804 | 0.927 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 451 | 0.880 | 0.873 | 0.046 | 0.791 | 0.955 |
| kev-9b-ft-s17 | choice | granularity | sentence | 220 | 0.836 | 0.857 | 0.104 | 0.803 | 0.912 |
| kev-9b-ft-s17 | choice | provenance | human | 1286 | 0.868 | 0.868 | 0.054 | 0.799 | 0.936 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1286 | 0.868 | 0.868 | 0.054 | 0.799 | 0.936 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 693 | 0.919 | 0.892 | 0.034 | 0.834 | 0.951 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 593 | 0.808 | 0.834 | 0.094 | 0.785 | 0.883 |
| kev-9b-ft-s17 | choice | source accuracy | human | 1286 | 0.868 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 990 | 0.883 | 0.882 | 0.061 | 0.846 | 0.918 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 733 | 0.885 | 0.886 | 0.062 | 0.849 | 0.923 |
| kev-9b-ft-s18 | noul | granularity | sentence | 317 | 0.877 | 0.880 | 0.068 | 0.785 | 0.974 |
| kev-9b-ft-s18 | noul | provenance | human | 2040 | 0.883 | 0.883 | 0.062 | 0.837 | 0.928 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2040 | 0.883 | 0.883 | 0.062 | 0.837 | 0.928 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1208 | 0.911 | 0.901 | 0.041 | 0.854 | 0.948 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 832 | 0.843 | 0.851 | 0.095 | 0.823 | 0.879 |
| kev-9b-ft-s18 | noul | source accuracy | human | 2040 | 0.883 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 615 | 0.885 | 0.880 | 0.054 | 0.825 | 0.936 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 451 | 0.900 | 0.895 | 0.055 | 0.830 | 0.959 |
| kev-9b-ft-s18 | choice | granularity | sentence | 220 | 0.845 | 0.868 | 0.095 | 0.809 | 0.926 |
| kev-9b-ft-s18 | choice | provenance | human | 1286 | 0.883 | 0.883 | 0.056 | 0.823 | 0.944 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1286 | 0.883 | 0.883 | 0.056 | 0.823 | 0.944 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 693 | 0.934 | 0.916 | 0.032 | 0.877 | 0.955 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 593 | 0.825 | 0.853 | 0.100 | 0.800 | 0.905 |
| kev-9b-ft-s18 | choice | source accuracy | human | 1286 | 0.883 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 990 | 0.869 | 0.868 | 0.063 | 0.811 | 0.924 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 733 | 0.880 | 0.880 | 0.060 | 0.830 | 0.931 |
| kev-9b-ft-s19 | noul | granularity | sentence | 317 | 0.890 | 0.892 | 0.061 | 0.804 | 0.981 |
| kev-9b-ft-s19 | noul | provenance | human | 2040 | 0.876 | 0.876 | 0.060 | 0.817 | 0.935 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2040 | 0.876 | 0.876 | 0.060 | 0.817 | 0.935 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1208 | 0.900 | 0.888 | 0.042 | 0.828 | 0.947 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 832 | 0.841 | 0.857 | 0.088 | 0.806 | 0.907 |
| kev-9b-ft-s19 | noul | source accuracy | human | 2040 | 0.876 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 615 | 0.893 | 0.889 | 0.041 | 0.846 | 0.933 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 451 | 0.882 | 0.876 | 0.055 | 0.796 | 0.955 |
| kev-9b-ft-s19 | choice | granularity | sentence | 220 | 0.845 | 0.860 | 0.087 | 0.822 | 0.897 |
| kev-9b-ft-s19 | choice | provenance | human | 1286 | 0.881 | 0.881 | 0.050 | 0.824 | 0.938 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1286 | 0.881 | 0.881 | 0.050 | 0.824 | 0.938 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 693 | 0.922 | 0.898 | 0.031 | 0.845 | 0.951 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 593 | 0.833 | 0.853 | 0.082 | 0.816 | 0.891 |
| kev-9b-ft-s19 | choice | source accuracy | human | 1286 | 0.881 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1118 | 0.507 | 35 | 0.758 | 0.759 | 0.740 |
| kev-0.8b-ft-s18 | 1118 | 0.382 | 35 | 0.744 | 0.759 | 0.748 |
| kev-0.8b-ft-s19 | 1118 | 0.550 | 35 | 0.758 | 0.744 | 0.734 |
| kev-4b-ft-s17 | 1118 | 0.678 | 35 | 0.883 | 0.870 | 0.864 |
| kev-4b-ft-s18 | 1118 | 0.560 | 35 | 0.867 | 0.864 | 0.856 |
| kev-4b-ft-s19 | 1118 | 0.382 | 35 | 0.867 | 0.868 | 0.862 |
| kev-9b-ft-s17 | 1118 | 0.334 | 35 | 0.880 | 0.886 | 0.878 |
| kev-9b-ft-s18 | 1118 | 0.469 | 35 | 0.883 | 0.883 | 0.881 |
| kev-9b-ft-s19 | 1118 | 0.602 | 35 | 0.876 | 0.872 | 0.864 |

## Interpretation and caveats

- Test label origins: construction (3326). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice no-defect=643, real-defect=643; yes/no False=1020, True=1020. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.32 finding-confirmation, κ=0.42 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
