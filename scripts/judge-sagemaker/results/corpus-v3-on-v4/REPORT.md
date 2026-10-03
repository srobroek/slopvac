# Corpus evaluation report: `corpus-v3-on-v4`

## Status

- v3-full fine-tune checkpoints (trained on corpus-20260930-s17-v3/full) evaluated on the v4 test and calibration splits, which were rebuilt against the lint rules at main 7544c168e0 with human labels. Semantic-detection items in v4 still have the design flaws fixed in v5 (unmarked targets, leaked exception codes, fragment spans), so read the semantic role with caution.

## Dataset and coverage

- Campaign: `corpus-20261002-s17-v4/v3-checkpoints`. The v3-full fine-tune checkpoints (no retraining) evaluated on the v4 full test and calibration splits. Base arms are not repeated: v4-full evaluates them on the same splits.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 9 of 9 required (`kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 13 of 22 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1659 examples; SHA-256 `842e8de6734b0d60330c2274359a0b19525b4c68263a60bc1d2d9d43ba4f60cf`.
- Test: 3424 examples; SHA-256 `080f183aba8eb64e5cca4bb333fc8f3f59d8198964520a79d0030fb3a0d22c65`.
- Test composition: label origins `construction`=3362, `human-adjudication`=62; choice labels no-defect=684, real-defect=690; yes/no labels False=1025, True=1025.

## Headline by role

Each arm's numbers come from `results/corpus-v3-on-v4/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1374 (real-defect=690, no-defect=684).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.768 | 0.705–0.822 | 0.809 | 0.728 | 0.061 | 0.054 | NVIDIA A10G | 17.691 | $0.3694 |
| kev-0.8b-ft-s18 | 0.792 | 0.731–0.844 | 0.855 | 0.728 | 0.074 | 0.054 | NVIDIA A10G | 17.340 | $0.7011 |
| kev-0.8b-ft-s19 | 0.770 | 0.707–0.824 | 0.842 | 0.697 | 0.026 | 0.040 | NVIDIA A10G | 17.461 | $0.7067 |
| kev-0.8b FT mean ± SD [range] | 0.777 ± 0.013 [0.768–0.792] | — | 0.835 ± 0.024 [0.809–0.855] | 0.718 ± 0.018 [0.697–0.728] | 0.054 ± 0.025 [0.026–0.074] | 0.049 ± 0.008 [0.040–0.054] | — | — | — |
| kev-4b-ft-s17 | 0.825 | 0.767–0.877 | 0.938 | 0.712 | 0.104 | 0.062 | NVIDIA A10G | 88.159 | $2.8700 |
| kev-4b-ft-s18 | 0.825 | 0.769–0.875 | 0.946 | 0.703 | 0.093 | 0.065 | NVIDIA A10G | 88.165 | $1.3033 |
| kev-4b-ft-s19 | 0.816 | 0.757–0.869 | 0.948 | 0.684 | 0.108 | 0.081 | NVIDIA A10G | 88.112 | $2.2244 |
| kev-4b FT mean ± SD [range] | 0.822 ± 0.005 [0.816–0.825] | — | 0.944 ± 0.005 [0.938–0.948] | 0.700 ± 0.014 [0.684–0.712] | 0.102 ± 0.008 [0.093–0.108] | 0.069 ± 0.010 [0.062–0.081] | — | — | — |
| kev-9b-ft-s17 | 0.850 | 0.793–0.901 | 0.952 | 0.747 | 0.082 | 0.056 | NVIDIA L40S | 62.782 | $2.9364 |
| kev-9b-ft-s18 | 0.868 | 0.813–0.915 | 0.952 | 0.784 | 0.058 | 0.024 | NVIDIA L40S | 62.861 | $2.8753 |
| kev-9b-ft-s19 | 0.850 | 0.790–0.904 | 0.962 | 0.737 | 0.079 | 0.056 | NVIDIA L40S | 62.685 | $2.9394 |
| kev-9b FT mean ± SD [range] | 0.856 ± 0.011 [0.850–0.868] | — | 0.956 ± 0.006 [0.952–0.962] | 0.756 ± 0.025 [0.737–0.784] | 0.073 ± 0.013 [0.058–0.082] | 0.045 ± 0.018 [0.024–0.056] | — | — | — |

- Best single arm: `kev-9b-ft-s18` (balanced accuracy 0.868).
- Best fine-tuned family by seed mean: `kev-9b` (0.856 ± 0.011 [0.850–0.868]).

### semantic-detection (`noul`)

Test items: 2050 (True=1025, False=1025).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.746 | 0.692–0.792 | 0.678 | 0.815 | 0.053 | 0.029 | NVIDIA A10G | 17.691 | $0.3694 |
| kev-0.8b-ft-s18 | 0.739 | 0.685–0.783 | 0.682 | 0.795 | 0.060 | 0.025 | NVIDIA A10G | 17.340 | $0.7011 |
| kev-0.8b-ft-s19 | 0.747 | 0.695–0.792 | 0.679 | 0.816 | 0.062 | 0.035 | NVIDIA A10G | 17.461 | $0.7067 |
| kev-0.8b FT mean ± SD [range] | 0.744 ± 0.005 [0.739–0.747] | — | 0.680 ± 0.002 [0.678–0.682] | 0.808 ± 0.012 [0.795–0.816] | 0.058 ± 0.005 [0.053–0.062] | 0.030 ± 0.005 [0.025–0.035] | — | — | — |
| kev-4b-ft-s17 | 0.845 | 0.790–0.887 | 0.783 | 0.906 | 0.060 | 0.033 | NVIDIA A10G | 88.159 | $2.8700 |
| kev-4b-ft-s18 | 0.871 | 0.820–0.906 | 0.828 | 0.913 | 0.043 | 0.024 | NVIDIA A10G | 88.165 | $1.3033 |
| kev-4b-ft-s19 | 0.858 | 0.807–0.895 | 0.790 | 0.925 | 0.053 | 0.028 | NVIDIA A10G | 88.112 | $2.2244 |
| kev-4b FT mean ± SD [range] | 0.858 ± 0.013 [0.845–0.871] | — | 0.801 ± 0.024 [0.783–0.828] | 0.915 ± 0.009 [0.906–0.925] | 0.052 ± 0.009 [0.043–0.060] | 0.028 ± 0.004 [0.024–0.033] | — | — | — |
| kev-9b-ft-s17 | 0.876 | 0.831–0.910 | 0.833 | 0.919 | 0.059 | 0.024 | NVIDIA L40S | 62.782 | $2.9364 |
| kev-9b-ft-s18 | 0.873 | 0.823–0.911 | 0.830 | 0.915 | 0.057 | 0.018 | NVIDIA L40S | 62.861 | $2.8753 |
| kev-9b-ft-s19 | 0.867 | 0.814–0.905 | 0.820 | 0.913 | 0.071 | 0.023 | NVIDIA L40S | 62.685 | $2.9394 |
| kev-9b FT mean ± SD [range] | 0.872 ± 0.005 [0.867–0.876] | — | 0.828 ± 0.007 [0.820–0.833] | 0.916 ± 0.003 [0.913–0.919] | 0.062 ± 0.008 [0.057–0.071] | 0.022 ± 0.003 [0.018–0.024] | — | — | — |

- Best single arm: `kev-9b-ft-s17` (balanced accuracy 0.876).
- Best fine-tuned family by seed mean: `kev-9b` (0.872 ± 0.005 [0.867–0.876]).

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | not evaluated | — | 0.777 | — | — | — | — | — | — |
| kev-4b | not evaluated | — | 0.822 | — | — | — | — | — | — |
| kev-9b | not evaluated | — | 0.856 | — | — | — | — | — | — |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | not evaluated | — | 0.744 | — | — | — | — | — | — |
| kev-4b | not evaluated | — | 0.858 | — | — | — | — | — | — |
| kev-9b | not evaluated | — | 0.872 | — | — | — | — | — | — |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-08b-s17-20260929214043 | not in ledger | 1 / 1 / 1 | $0.54 | $0.54 |
| kev-0.8b-ft-s18 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-08b-s18-20260929214053 | not in ledger | 1 / 2 / 0 | $1.35 | $1.35 |
| kev-0.8b-ft-s19 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-08b-s19-20260929214105 | not in ledger | 1 / 1 / 0 | $1.03 | $1.03 |
| kev-4b-ft-s17 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-4b-s17-20260929214114 | not in ledger | 1 / 1 / 0 | $3.60 | $3.60 |
| kev-4b-ft-s18 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-4b-s18-20260929214124 | not in ledger | 1 / 0 / 1 | $1.30 | $1.30 |
| kev-4b-ft-s19 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-4b-s19-20260929214135 | not in ledger | 1 / 2 / 0 | $3.35 | $3.35 |
| kev-9b-ft-s17 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-9b-s17-20260929214144 | not in ledger | 1 / 2 / 0 | $4.71 | $4.71 |
| kev-9b-ft-s18 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-9b-s18-20260930001932 | not in ledger | 1 / 2 / 0 | $4.65 | $4.65 |
| kev-9b-ft-s19 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-9b-s19-20260930015505 | not in ledger | 1 / 0 / 0 | $2.94 | $2.94 |

Campaign total: **$23.47 USD** (training $0.00, evaluation $23.47) over 0 training and 22 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | evaluation | Failed | 1 | $0.17 | AlgorithmError: /data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |
| kev-0.8b-ft-s17 | evaluation | Stopped | 1 | $0.00 | no reason recorded |
| kev-0.8b-ft-s18 | evaluation | Failed | 2 | $0.65 | AlgorithmError: /data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |
| kev-0.8b-ft-s19 | evaluation | Failed | 1 | $0.33 | AlgorithmError: /data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |
| kev-4b-ft-s17 | evaluation | Failed | 1 | $0.72 | AlgorithmError: put/data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |
| kev-4b-ft-s18 | evaluation | Stopped | 1 | $0.00 | no reason recorded |
| kev-4b-ft-s19 | evaluation | Failed | 2 | $1.13 | AlgorithmError: put/data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |
| kev-9b-ft-s17 | evaluation | Failed | 2 | $1.77 | AlgorithmError: put/data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |
| kev-9b-ft-s18 | evaluation | Failed | 2 | $1.77 | AlgorithmError: put/data/code/judge_sagemaker/container/eval_entry.py", line 426, in main |

## Panel agreement caveat

Independent corpus panel agreement (source: `/Users/sjors/tmp/worktrees/slopvac/exp-judge-corpus/scripts/judge-corpus/items/panel-agreement.json`):
- finding-confirmation: Fleiss κ=0.32 (4099 three-vote items).
- semantic-detection: Fleiss κ=0.30 (1747 three-vote items).
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
| kev-0.8b-ft-s17 | 2050 | 0.746 | 0.746 | 0.830 | 0.175 | 0.526 | 0.053 | 0.172 | 0.516 | 0.029 | 0.692–0.792 | 0.026–0.114 | 0.017–0.091 | 0.678 | 0.815 | — | — | — | 17.691 | 58.540 |
| kev-0.8b-ft-s18 | 2050 | 0.739 | 0.739 | 0.833 | 0.172 | 0.517 | 0.060 | 0.169 | 0.506 | 0.025 | 0.685–0.783 | 0.028–0.112 | 0.020–0.078 | 0.682 | 0.795 | — | — | — | 17.340 | 56.734 |
| kev-0.8b-ft-s19 | 2050 | 0.747 | 0.747 | 0.830 | 0.176 | 0.532 | 0.062 | 0.173 | 0.519 | 0.035 | 0.695–0.792 | 0.030–0.115 | 0.019–0.088 | 0.679 | 0.816 | — | — | — | 17.461 | 56.949 |
| FT mean ± SD [range] | — | 0.744 ± 0.005 [0.739–0.747] | 0.744 ± 0.005 [0.739–0.747] | 0.831 ± 0.002 [0.830–0.833] | 0.174 ± 0.002 [0.172–0.176] | 0.525 ± 0.008 [0.517–0.532] | 0.058 ± 0.005 [0.053–0.062] | 0.171 ± 0.002 [0.169–0.173] | 0.514 ± 0.007 [0.506–0.519] | 0.030 ± 0.005 [0.025–0.035] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1374 | 0.769 | 0.768 | 0.843 | 0.326 | 0.505 | 0.061 | 0.324 | 0.500 | 0.054 | 0.705–0.822 | 0.029–0.122 | 0.024–0.116 | — | — | 0.001 | 0.905 | 0.096 | 17.691 | 58.540 |
| kev-0.8b-ft-s18 | 1374 | 0.792 | 0.792 | 0.855 | 0.315 | 0.500 | 0.074 | 0.310 | 0.486 | 0.054 | 0.731–0.844 | 0.038–0.121 | 0.027–0.101 | — | — | 0.000 | 0.929 | 0.074 | 17.340 | 56.734 |
| kev-0.8b-ft-s19 | 1374 | 0.770 | 0.770 | 0.847 | 0.316 | 0.488 | 0.026 | 0.319 | 0.491 | 0.040 | 0.707–0.824 | 0.020–0.087 | 0.021–0.105 | — | — | 0.000 | 0.913 | 0.079 | 17.461 | 56.949 |
| FT mean ± SD [range] | — | 0.777 ± 0.013 [0.769–0.792] | 0.777 ± 0.013 [0.768–0.792] | 0.848 ± 0.006 [0.843–0.855] | 0.319 ± 0.006 [0.315–0.326] | 0.498 ± 0.009 [0.488–0.505] | 0.054 ± 0.025 [0.026–0.074] | 0.318 ± 0.007 [0.310–0.324] | 0.493 ± 0.007 [0.486–0.500] | 0.049 ± 0.008 [0.040–0.054] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.001] | 0.916 ± 0.012 [0.905–0.929] | 0.083 ± 0.011 [0.074–0.096] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 2050 | 0.845 | 0.845 | 0.924 | 0.115 | 0.384 | 0.060 | 0.112 | 0.365 | 0.033 | 0.790–0.887 | 0.029–0.112 | 0.022–0.085 | 0.783 | 0.906 | — | — | — | 88.159 | 167.307 |
| kev-4b-ft-s18 | 2050 | 0.871 | 0.871 | 0.939 | 0.100 | 0.337 | 0.043 | 0.098 | 0.327 | 0.024 | 0.820–0.906 | 0.017–0.089 | 0.011–0.073 | 0.828 | 0.913 | — | — | — | 88.165 | 167.812 |
| kev-4b-ft-s19 | 2050 | 0.858 | 0.858 | 0.936 | 0.110 | 0.365 | 0.053 | 0.107 | 0.348 | 0.028 | 0.807–0.895 | 0.029–0.097 | 0.019–0.068 | 0.790 | 0.925 | — | — | — | 88.112 | 167.263 |
| FT mean ± SD [range] | — | 0.858 ± 0.013 [0.845–0.871] | 0.858 ± 0.013 [0.845–0.871] | 0.933 ± 0.008 [0.924–0.939] | 0.108 ± 0.008 [0.100–0.115] | 0.362 ± 0.024 [0.337–0.384] | 0.052 ± 0.009 [0.043–0.060] | 0.106 ± 0.007 [0.098–0.112] | 0.347 ± 0.019 [0.327–0.365] | 0.028 ± 0.004 [0.024–0.033] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 1374 | 0.825 | 0.825 | 0.906 | 0.278 | 0.499 | 0.104 | 0.262 | 0.437 | 0.062 | 0.767–0.877 | 0.060–0.160 | 0.027–0.117 | — | — | 0.001 | 0.958 | 0.044 | 88.159 | 167.307 |
| kev-4b-ft-s18 | 1374 | 0.825 | 0.825 | 0.921 | 0.265 | 0.444 | 0.093 | 0.255 | 0.419 | 0.065 | 0.769–0.875 | 0.051–0.149 | 0.036–0.122 | — | — | 0.001 | 0.964 | 0.042 | 88.165 | 167.812 |
| kev-4b-ft-s19 | 1374 | 0.817 | 0.816 | 0.915 | 0.286 | 0.486 | 0.108 | 0.271 | 0.440 | 0.081 | 0.757–0.869 | 0.062–0.166 | 0.042–0.137 | — | — | 0.001 | 0.975 | 0.029 | 88.112 | 167.263 |
| FT mean ± SD [range] | — | 0.822 ± 0.005 [0.817–0.825] | 0.822 ± 0.005 [0.816–0.825] | 0.914 ± 0.008 [0.906–0.921] | 0.276 ± 0.011 [0.265–0.286] | 0.477 ± 0.029 [0.444–0.499] | 0.102 ± 0.008 [0.093–0.108] | 0.263 ± 0.008 [0.255–0.271] | 0.432 ± 0.011 [0.419–0.440] | 0.069 ± 0.010 [0.062–0.081] | — | — | — | — | — | 0.001 ± 0.000 [0.001–0.001] | 0.966 ± 0.009 [0.958–0.975] | 0.039 ± 0.008 [0.029–0.044] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 2050 | 0.876 | 0.876 | 0.949 | 0.095 | 0.330 | 0.059 | 0.090 | 0.300 | 0.024 | 0.831–0.910 | 0.036–0.094 | 0.014–0.060 | 0.833 | 0.919 | — | — | — | 62.782 | 108.960 |
| kev-9b-ft-s18 | 2050 | 0.873 | 0.873 | 0.947 | 0.094 | 0.331 | 0.057 | 0.090 | 0.300 | 0.018 | 0.823–0.911 | 0.033–0.096 | 0.014–0.056 | 0.830 | 0.915 | — | — | — | 62.861 | 108.915 |
| kev-9b-ft-s19 | 2050 | 0.867 | 0.867 | 0.942 | 0.104 | 0.364 | 0.071 | 0.098 | 0.321 | 0.023 | 0.814–0.905 | 0.040–0.122 | 0.012–0.074 | 0.820 | 0.913 | — | — | — | 62.685 | 109.034 |
| FT mean ± SD [range] | — | 0.872 ± 0.005 [0.867–0.876] | 0.872 ± 0.005 [0.867–0.876] | 0.946 ± 0.003 [0.942–0.949] | 0.098 ± 0.005 [0.094–0.104] | 0.342 ± 0.019 [0.330–0.364] | 0.062 ± 0.008 [0.057–0.071] | 0.093 ± 0.004 [0.090–0.098] | 0.307 ± 0.012 [0.300–0.321] | 0.022 ± 0.003 [0.018–0.024] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 1374 | 0.850 | 0.850 | 0.943 | 0.226 | 0.376 | 0.082 | 0.215 | 0.348 | 0.056 | 0.793–0.901 | 0.038–0.134 | 0.028–0.104 | — | — | 0.001 | 0.975 | 0.038 | 62.782 | 108.960 |
| kev-9b-ft-s18 | 1374 | 0.868 | 0.868 | 0.954 | 0.198 | 0.340 | 0.058 | 0.190 | 0.317 | 0.024 | 0.813–0.915 | 0.024–0.110 | 0.016–0.075 | — | — | 0.001 | 0.972 | 0.031 | 62.861 | 108.915 |
| kev-9b-ft-s19 | 1374 | 0.850 | 0.850 | 0.953 | 0.228 | 0.372 | 0.079 | 0.217 | 0.346 | 0.056 | 0.790–0.904 | 0.033–0.134 | 0.026–0.100 | — | — | 0.001 | 0.980 | 0.029 | 62.685 | 109.034 |
| FT mean ± SD [range] | — | 0.856 ± 0.011 [0.850–0.868] | 0.856 ± 0.011 [0.850–0.868] | 0.950 ± 0.006 [0.943–0.954] | 0.218 ± 0.017 [0.198–0.228] | 0.362 ± 0.020 [0.340–0.376] | 0.073 ± 0.013 [0.058–0.082] | 0.207 ± 0.015 [0.190–0.217] | 0.337 ± 0.017 [0.317–0.348] | 0.045 ± 0.018 [0.024–0.056] | — | — | — | — | — | 0.001 ± 0.000 [0.001–0.001] | 0.975 ± 0.004 [0.972–0.980] | 0.033 ± 0.005 [0.029–0.038] | — | — |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.2xlarge | us-west-2 | 17.691 | 58.540 | 665 | $0.3694 | sv-eval-kev-08b-ft-s17-261002130422466034 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.340 | 56.734 | 631 | $0.7011 | sv-eval-kev-08b-ft-s18-261002124832012304 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 17.461 | 56.949 | 636 | $0.7067 | sv-eval-kev-08b-ft-s19-261002125303825122 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.12xlarge | us-east-1 | 88.159 | 167.307 | 1148 | $2.8700 | sv-eval-kev-4b-ft-s17-261002124849829426 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 88.165 | 167.812 | 1173 | $1.3033 | sv-eval-kev-4b-ft-s18-261002130441730445 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.16xlarge | us-east-1 | 88.112 | 167.263 | 1144 | $2.2244 | sv-eval-kev-4b-ft-s19-261002124904218548 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.16xlarge | us-west-2 | 62.782 | 108.960 | 961 | $2.9364 | sv-eval-kev-9b-ft-s17-261002125322754047 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.16xlarge | us-east-1 | 62.861 | 108.915 | 941 | $2.8753 | sv-eval-kev-9b-ft-s18-261002124918487523 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.16xlarge | us-east-1 | 62.685 | 109.034 | 962 | $2.9394 | sv-eval-kev-9b-ft-s19-261002130846641006 |

Total billed evaluation cost for the reported arms: **$16.9260 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | noul | granularity | document | 991 | 0.740 | 0.739 | 0.055 | 0.664 | 0.813 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 738 | 0.743 | 0.743 | 0.063 | 0.693 | 0.794 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 321 | 0.776 | 0.777 | 0.076 | 0.687 | 0.867 |
| kev-0.8b-ft-s17 | noul | provenance | generated | 8 | 0.500 | 0.600 | 0.481 | 0.200 | 1.000 |
| kev-0.8b-ft-s17 | noul | provenance | human | 2042 | 0.747 | 0.747 | 0.051 | 0.680 | 0.814 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2050 | 0.746 | 0.746 | 0.053 | 0.678 | 0.815 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1215 | 0.765 | 0.747 | 0.060 | 0.657 | 0.837 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 835 | 0.719 | 0.728 | 0.070 | 0.697 | 0.759 |
| kev-0.8b-ft-s17 | noul | source accuracy | generated | 8 | 0.500 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 2042 | 0.747 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 658 | 0.784 | 0.783 | 0.053 | 0.741 | 0.825 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 476 | 0.773 | 0.764 | 0.067 | 0.691 | 0.836 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 240 | 0.717 | 0.702 | 0.124 | 0.750 | 0.655 |
| kev-0.8b-ft-s17 | choice | provenance | generated | 36 | 0.583 | 0.571 | 0.282 | 0.353 | 0.789 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1338 | 0.774 | 0.773 | 0.057 | 0.738 | 0.809 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1374 | 0.769 | 0.768 | 0.061 | 0.728 | 0.809 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 738 | 0.795 | 0.788 | 0.042 | 0.773 | 0.804 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 636 | 0.737 | 0.768 | 0.091 | 0.710 | 0.827 |
| kev-0.8b-ft-s17 | choice | source accuracy | generated | 36 | 0.583 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1338 | 0.774 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 991 | 0.724 | 0.723 | 0.073 | 0.676 | 0.769 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 738 | 0.740 | 0.741 | 0.058 | 0.690 | 0.791 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 321 | 0.782 | 0.784 | 0.040 | 0.681 | 0.886 |
| kev-0.8b-ft-s18 | noul | provenance | generated | 8 | 0.500 | 0.600 | 0.516 | 0.200 | 1.000 |
| kev-0.8b-ft-s18 | noul | provenance | human | 2042 | 0.739 | 0.739 | 0.059 | 0.684 | 0.795 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2050 | 0.739 | 0.739 | 0.060 | 0.682 | 0.795 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1215 | 0.762 | 0.748 | 0.059 | 0.678 | 0.817 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 835 | 0.704 | 0.712 | 0.069 | 0.686 | 0.739 |
| kev-0.8b-ft-s18 | noul | source accuracy | generated | 8 | 0.500 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 2042 | 0.739 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 658 | 0.807 | 0.805 | 0.063 | 0.741 | 0.869 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 476 | 0.798 | 0.788 | 0.066 | 0.705 | 0.870 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 240 | 0.738 | 0.740 | 0.124 | 0.731 | 0.750 |
| kev-0.8b-ft-s18 | choice | provenance | generated | 36 | 0.556 | 0.536 | 0.317 | 0.176 | 0.895 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1338 | 0.798 | 0.798 | 0.069 | 0.742 | 0.854 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1374 | 0.792 | 0.792 | 0.074 | 0.728 | 0.855 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 738 | 0.821 | 0.785 | 0.043 | 0.707 | 0.863 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 636 | 0.758 | 0.782 | 0.112 | 0.737 | 0.827 |
| kev-0.8b-ft-s18 | choice | source accuracy | generated | 36 | 0.556 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1338 | 0.798 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 991 | 0.741 | 0.740 | 0.061 | 0.682 | 0.797 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 738 | 0.743 | 0.743 | 0.079 | 0.674 | 0.813 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 321 | 0.779 | 0.780 | 0.063 | 0.681 | 0.880 |
| kev-0.8b-ft-s19 | noul | provenance | generated | 8 | 0.500 | 0.600 | 0.453 | 0.200 | 1.000 |
| kev-0.8b-ft-s19 | noul | provenance | human | 2042 | 0.748 | 0.748 | 0.060 | 0.681 | 0.815 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2050 | 0.747 | 0.747 | 0.062 | 0.679 | 0.816 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1215 | 0.769 | 0.754 | 0.061 | 0.684 | 0.824 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 835 | 0.716 | 0.734 | 0.062 | 0.675 | 0.794 |
| kev-0.8b-ft-s19 | noul | source accuracy | generated | 8 | 0.500 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 2042 | 0.748 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 658 | 0.787 | 0.786 | 0.015 | 0.723 | 0.849 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 476 | 0.767 | 0.755 | 0.042 | 0.662 | 0.848 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 240 | 0.729 | 0.745 | 0.098 | 0.692 | 0.798 |
| kev-0.8b-ft-s19 | choice | provenance | generated | 36 | 0.556 | 0.536 | 0.345 | 0.176 | 0.895 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1338 | 0.776 | 0.776 | 0.022 | 0.711 | 0.841 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1374 | 0.770 | 0.770 | 0.026 | 0.697 | 0.842 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 738 | 0.810 | 0.778 | 0.028 | 0.707 | 0.848 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 636 | 0.723 | 0.757 | 0.071 | 0.693 | 0.820 |
| kev-0.8b-ft-s19 | choice | source accuracy | generated | 36 | 0.556 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1338 | 0.776 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 991 | 0.845 | 0.844 | 0.058 | 0.779 | 0.909 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 738 | 0.844 | 0.845 | 0.064 | 0.807 | 0.882 |
| kev-4b-ft-s17 | noul | granularity | sentence | 321 | 0.847 | 0.849 | 0.072 | 0.742 | 0.956 |
| kev-4b-ft-s17 | noul | provenance | generated | 8 | 0.375 | 0.500 | 0.576 | 0.000 | 1.000 |
| kev-4b-ft-s17 | noul | provenance | human | 2042 | 0.847 | 0.847 | 0.058 | 0.787 | 0.906 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2050 | 0.845 | 0.845 | 0.060 | 0.783 | 0.906 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1215 | 0.871 | 0.859 | 0.045 | 0.805 | 0.914 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 835 | 0.807 | 0.826 | 0.086 | 0.765 | 0.887 |
| kev-4b-ft-s17 | noul | source accuracy | generated | 8 | 0.375 | — | — | — | — |
| kev-4b-ft-s17 | noul | source accuracy | human | 2042 | 0.847 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 658 | 0.837 | 0.835 | 0.096 | 0.723 | 0.947 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 476 | 0.832 | 0.815 | 0.102 | 0.686 | 0.944 |
| kev-4b-ft-s17 | choice | granularity | sentence | 240 | 0.779 | 0.803 | 0.149 | 0.724 | 0.881 |
| kev-4b-ft-s17 | choice | provenance | generated | 36 | 0.556 | 0.529 | 0.377 | 0.059 | 1.000 |
| kev-4b-ft-s17 | choice | provenance | human | 1338 | 0.833 | 0.832 | 0.098 | 0.729 | 0.936 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1374 | 0.825 | 0.825 | 0.104 | 0.712 | 0.938 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 738 | 0.882 | 0.830 | 0.056 | 0.717 | 0.943 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 636 | 0.759 | 0.815 | 0.161 | 0.710 | 0.920 |
| kev-4b-ft-s17 | choice | source accuracy | generated | 36 | 0.556 | — | — | — | — |
| kev-4b-ft-s17 | choice | source accuracy | human | 1338 | 0.833 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 991 | 0.872 | 0.871 | 0.042 | 0.830 | 0.913 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 738 | 0.855 | 0.856 | 0.058 | 0.818 | 0.893 |
| kev-4b-ft-s18 | noul | granularity | sentence | 321 | 0.903 | 0.904 | 0.042 | 0.847 | 0.962 |
| kev-4b-ft-s18 | noul | provenance | generated | 8 | 0.375 | 0.500 | 0.576 | 0.000 | 1.000 |
| kev-4b-ft-s18 | noul | provenance | human | 2042 | 0.873 | 0.873 | 0.041 | 0.832 | 0.913 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2050 | 0.871 | 0.871 | 0.043 | 0.828 | 0.913 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1215 | 0.887 | 0.878 | 0.034 | 0.834 | 0.922 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 835 | 0.847 | 0.857 | 0.058 | 0.824 | 0.890 |
| kev-4b-ft-s18 | noul | source accuracy | generated | 8 | 0.375 | — | — | — | — |
| kev-4b-ft-s18 | noul | source accuracy | human | 2042 | 0.873 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 658 | 0.836 | 0.833 | 0.082 | 0.717 | 0.950 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 476 | 0.838 | 0.819 | 0.097 | 0.671 | 0.967 |
| kev-4b-ft-s18 | choice | granularity | sentence | 240 | 0.771 | 0.793 | 0.144 | 0.718 | 0.869 |
| kev-4b-ft-s18 | choice | provenance | generated | 36 | 0.583 | 0.559 | 0.354 | 0.118 | 1.000 |
| kev-4b-ft-s18 | choice | provenance | human | 1338 | 0.832 | 0.831 | 0.088 | 0.718 | 0.945 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1374 | 0.825 | 0.825 | 0.093 | 0.703 | 0.946 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 738 | 0.883 | 0.831 | 0.049 | 0.717 | 0.944 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 636 | 0.758 | 0.825 | 0.148 | 0.698 | 0.953 |
| kev-4b-ft-s18 | choice | source accuracy | generated | 36 | 0.583 | — | — | — | — |
| kev-4b-ft-s18 | choice | source accuracy | human | 1338 | 0.832 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 991 | 0.858 | 0.857 | 0.060 | 0.795 | 0.918 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 738 | 0.851 | 0.852 | 0.059 | 0.794 | 0.909 |
| kev-4b-ft-s19 | noul | granularity | sentence | 321 | 0.872 | 0.874 | 0.048 | 0.767 | 0.981 |
| kev-4b-ft-s19 | noul | provenance | generated | 8 | 0.500 | 0.600 | 0.482 | 0.200 | 1.000 |
| kev-4b-ft-s19 | noul | provenance | human | 2042 | 0.859 | 0.859 | 0.052 | 0.793 | 0.925 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2050 | 0.858 | 0.858 | 0.053 | 0.790 | 0.925 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1215 | 0.893 | 0.883 | 0.041 | 0.838 | 0.929 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 835 | 0.806 | 0.831 | 0.092 | 0.748 | 0.914 |
| kev-4b-ft-s19 | noul | source accuracy | generated | 8 | 0.500 | — | — | — | — |
| kev-4b-ft-s19 | noul | source accuracy | human | 2042 | 0.859 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 658 | 0.828 | 0.825 | 0.099 | 0.701 | 0.950 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 476 | 0.811 | 0.790 | 0.116 | 0.628 | 0.952 |
| kev-4b-ft-s19 | choice | granularity | sentence | 240 | 0.796 | 0.826 | 0.142 | 0.724 | 0.929 |
| kev-4b-ft-s19 | choice | provenance | generated | 36 | 0.583 | 0.559 | 0.356 | 0.118 | 1.000 |
| kev-4b-ft-s19 | choice | provenance | human | 1338 | 0.823 | 0.822 | 0.101 | 0.699 | 0.946 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1374 | 0.817 | 0.816 | 0.108 | 0.684 | 0.948 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 738 | 0.885 | 0.832 | 0.057 | 0.717 | 0.946 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 636 | 0.737 | 0.812 | 0.174 | 0.671 | 0.953 |
| kev-4b-ft-s19 | choice | source accuracy | generated | 36 | 0.583 | — | — | — | — |
| kev-4b-ft-s19 | choice | source accuracy | human | 1338 | 0.823 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 991 | 0.869 | 0.868 | 0.067 | 0.822 | 0.915 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 738 | 0.875 | 0.876 | 0.060 | 0.848 | 0.904 |
| kev-9b-ft-s17 | noul | granularity | sentence | 321 | 0.900 | 0.901 | 0.044 | 0.834 | 0.968 |
| kev-9b-ft-s17 | noul | provenance | generated | 8 | 0.375 | 0.500 | 0.592 | 0.000 | 1.000 |
| kev-9b-ft-s17 | noul | provenance | human | 2042 | 0.878 | 0.878 | 0.057 | 0.837 | 0.919 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2050 | 0.876 | 0.876 | 0.059 | 0.833 | 0.919 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1215 | 0.894 | 0.886 | 0.051 | 0.848 | 0.924 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 835 | 0.850 | 0.864 | 0.071 | 0.820 | 0.907 |
| kev-9b-ft-s17 | noul | source accuracy | generated | 8 | 0.375 | — | — | — | — |
| kev-9b-ft-s17 | noul | source accuracy | human | 2042 | 0.878 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 658 | 0.863 | 0.861 | 0.064 | 0.776 | 0.947 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 476 | 0.855 | 0.839 | 0.086 | 0.720 | 0.959 |
| kev-9b-ft-s17 | choice | granularity | sentence | 240 | 0.804 | 0.838 | 0.143 | 0.724 | 0.952 |
| kev-9b-ft-s17 | choice | provenance | generated | 36 | 0.556 | 0.529 | 0.391 | 0.059 | 1.000 |
| kev-9b-ft-s17 | choice | provenance | human | 1338 | 0.858 | 0.858 | 0.074 | 0.765 | 0.951 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1374 | 0.850 | 0.850 | 0.082 | 0.747 | 0.952 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 738 | 0.905 | 0.863 | 0.037 | 0.773 | 0.954 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 636 | 0.786 | 0.842 | 0.137 | 0.737 | 0.947 |
| kev-9b-ft-s17 | choice | source accuracy | generated | 36 | 0.556 | — | — | — | — |
| kev-9b-ft-s17 | choice | source accuracy | human | 1338 | 0.858 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 991 | 0.861 | 0.860 | 0.066 | 0.811 | 0.909 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 738 | 0.877 | 0.877 | 0.054 | 0.848 | 0.907 |
| kev-9b-ft-s18 | noul | granularity | sentence | 321 | 0.900 | 0.901 | 0.051 | 0.847 | 0.956 |
| kev-9b-ft-s18 | noul | provenance | generated | 8 | 0.375 | 0.500 | 0.577 | 0.000 | 1.000 |
| kev-9b-ft-s18 | noul | provenance | human | 2042 | 0.875 | 0.875 | 0.055 | 0.834 | 0.915 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2050 | 0.873 | 0.873 | 0.057 | 0.830 | 0.915 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1215 | 0.894 | 0.886 | 0.055 | 0.846 | 0.925 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 835 | 0.842 | 0.853 | 0.072 | 0.816 | 0.890 |
| kev-9b-ft-s18 | noul | source accuracy | generated | 8 | 0.375 | — | — | — | — |
| kev-9b-ft-s18 | noul | source accuracy | human | 2042 | 0.875 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 658 | 0.877 | 0.875 | 0.050 | 0.801 | 0.950 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 476 | 0.876 | 0.864 | 0.064 | 0.773 | 0.955 |
| kev-9b-ft-s18 | choice | granularity | sentence | 240 | 0.829 | 0.858 | 0.095 | 0.763 | 0.952 |
| kev-9b-ft-s18 | choice | provenance | generated | 36 | 0.583 | 0.559 | 0.365 | 0.118 | 1.000 |
| kev-9b-ft-s18 | choice | provenance | human | 1338 | 0.876 | 0.876 | 0.051 | 0.801 | 0.951 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1374 | 0.868 | 0.868 | 0.058 | 0.784 | 0.952 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 738 | 0.919 | 0.884 | 0.034 | 0.808 | 0.959 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 636 | 0.810 | 0.850 | 0.101 | 0.774 | 0.927 |
| kev-9b-ft-s18 | choice | source accuracy | generated | 36 | 0.583 | — | — | — | — |
| kev-9b-ft-s18 | choice | source accuracy | human | 1338 | 0.876 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 991 | 0.855 | 0.854 | 0.076 | 0.797 | 0.911 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 738 | 0.877 | 0.877 | 0.073 | 0.858 | 0.896 |
| kev-9b-ft-s19 | noul | granularity | sentence | 321 | 0.882 | 0.883 | 0.065 | 0.804 | 0.962 |
| kev-9b-ft-s19 | noul | provenance | generated | 8 | 0.375 | 0.500 | 0.483 | 0.000 | 1.000 |
| kev-9b-ft-s19 | noul | provenance | human | 2042 | 0.869 | 0.869 | 0.070 | 0.825 | 0.913 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2050 | 0.867 | 0.867 | 0.071 | 0.820 | 0.913 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1215 | 0.887 | 0.878 | 0.057 | 0.836 | 0.921 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 835 | 0.837 | 0.850 | 0.095 | 0.807 | 0.893 |
| kev-9b-ft-s19 | noul | source accuracy | generated | 8 | 0.375 | — | — | — | — |
| kev-9b-ft-s19 | noul | source accuracy | human | 2042 | 0.869 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 658 | 0.856 | 0.853 | 0.071 | 0.754 | 0.953 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 476 | 0.859 | 0.843 | 0.075 | 0.715 | 0.970 |
| kev-9b-ft-s19 | choice | granularity | sentence | 240 | 0.817 | 0.853 | 0.115 | 0.731 | 0.976 |
| kev-9b-ft-s19 | choice | provenance | generated | 36 | 0.556 | 0.533 | 0.360 | 0.118 | 0.947 |
| kev-9b-ft-s19 | choice | provenance | human | 1338 | 0.858 | 0.858 | 0.072 | 0.753 | 0.963 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1374 | 0.850 | 0.850 | 0.079 | 0.737 | 0.962 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 738 | 0.911 | 0.867 | 0.036 | 0.773 | 0.961 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 636 | 0.780 | 0.844 | 0.129 | 0.722 | 0.967 |
| kev-9b-ft-s19 | choice | source accuracy | generated | 36 | 0.556 | — | — | — | — |
| kev-9b-ft-s19 | choice | source accuracy | human | 1338 | 0.858 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1126 | 0.567 | 35 | 0.746 | 0.741 | 0.733 |
| kev-0.8b-ft-s18 | 1126 | 0.514 | 35 | 0.739 | 0.740 | 0.713 |
| kev-0.8b-ft-s19 | 1126 | 0.422 | 35 | 0.747 | 0.745 | 0.743 |
| kev-4b-ft-s17 | 1126 | 0.465 | 35 | 0.845 | 0.851 | 0.843 |
| kev-4b-ft-s18 | 1126 | 0.557 | 35 | 0.871 | 0.869 | 0.865 |
| kev-4b-ft-s19 | 1126 | 0.475 | 35 | 0.858 | 0.857 | 0.843 |
| kev-9b-ft-s17 | 1126 | 0.527 | 35 | 0.876 | 0.878 | 0.864 |
| kev-9b-ft-s18 | 1126 | 0.481 | 35 | 0.873 | 0.874 | 0.862 |
| kev-9b-ft-s19 | 1126 | 0.287 | 35 | 0.867 | 0.873 | 0.868 |

## Interpretation and caveats

- Test label origins: construction (3362), human-adjudication (62). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice no-defect=684, real-defect=690; yes/no False=1025, True=1025. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.32 finding-confirmation, κ=0.30 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
