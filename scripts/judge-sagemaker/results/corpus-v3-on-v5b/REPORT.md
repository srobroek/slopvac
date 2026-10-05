# Corpus evaluation report: `corpus-v3-on-v5b`

## Status

- v3-full fine-tune checkpoints evaluated on the v5b test set (lint rules at main ca941af16a; human, LLM-consensus and construction labels; redesigned semantic items).

## Dataset and coverage

- Campaign: `corpus-20261003-s17-v5b/v3-checkpoints`. The v3-full fine-tune checkpoints (no retraining) evaluated on the v5b full test and calibration splits. Base arms are not repeated: v5b-full evaluates them on the same splits.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 9 of 9 required (`kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 0 of 9 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1720 examples; SHA-256 `8534bee7b935ae80b47d35e1e96a4a288ab3ba86c6bfe851ff01e8dcf3300b1b`.
- Test: 3671 examples; SHA-256 `a77f6f64b85b81a13330df57b8cd3973edd2b295ae30efdf4ddc12a4a8bb0b31`.
- Test composition: label origins `construction`=3092, `human-adjudication`=258, `llm-review-consensus`=321; choice labels insufficient-context=2, no-defect=821, real-defect=774; yes/no labels False=1151, True=923.

## Headline by role

Each arm's numbers come from `results/corpus-v3-on-v5b/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1597 (real-defect=774, no-defect=821).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.746 | 0.691–0.792 | 0.801 | 0.691 | 0.081 | 0.023 | NVIDIA A10G | 17.155 | $1.2542 |
| kev-0.8b-ft-s18 | 0.775 | 0.724–0.819 | 0.846 | 0.703 | 0.094 | 0.041 | NVIDIA A10G | 17.388 | $0.7178 |
| kev-0.8b-ft-s19 | 0.753 | 0.699–0.800 | 0.835 | 0.671 | 0.043 | 0.015 | NVIDIA A10G | 17.169 | $1.6275 |
| kev-0.8b FT mean ± SD [range] | 0.758 ± 0.015 [0.746–0.775] | — | 0.827 ± 0.023 [0.801–0.846] | 0.688 ± 0.016 [0.671–0.703] | 0.073 ± 0.027 [0.043–0.094] | 0.027 ± 0.013 [0.015–0.041] | — | — | — |
| kev-4b-ft-s17 | 0.794 | 0.743–0.839 | 0.915 | 0.672 | 0.134 | 0.036 | NVIDIA A10G | 64.828 | $2.2303 |
| kev-4b-ft-s18 | 0.793 | 0.745–0.838 | 0.924 | 0.663 | 0.120 | 0.051 | NVIDIA A10G | 64.942 | $2.2303 |
| kev-4b-ft-s19 | 0.789 | 0.738–0.837 | 0.928 | 0.650 | 0.133 | 0.052 | NVIDIA A10G | 64.918 | $1.2967 |
| kev-4b FT mean ± SD [range] | 0.792 ± 0.003 [0.789–0.794] | — | 0.922 ± 0.007 [0.915–0.928] | 0.662 ± 0.011 [0.650–0.672] | 0.129 ± 0.008 [0.120–0.134] | 0.047 ± 0.009 [0.036–0.052] | — | — | — |
| kev-9b-ft-s17 | 0.822 | 0.777–0.865 | 0.943 | 0.700 | 0.104 | 0.044 | NVIDIA L40S | 62.502 | $1.1867 |
| kev-9b-ft-s18 | 0.836 | 0.790–0.877 | 0.942 | 0.730 | 0.087 | 0.018 | NVIDIA L40S | 61.951 | $1.3750 |
| kev-9b-ft-s19 | 0.817 | 0.768–0.863 | 0.951 | 0.683 | 0.107 | 0.049 | NVIDIA L40S | 62.130 | $1.9192 |
| kev-9b FT mean ± SD [range] | 0.825 ± 0.010 [0.817–0.836] | — | 0.945 ± 0.005 [0.942–0.951] | 0.704 ± 0.023 [0.683–0.730] | 0.099 ± 0.011 [0.087–0.107] | 0.037 ± 0.017 [0.018–0.049] | — | — | — |

- Best single arm: `kev-9b-ft-s18` (balanced accuracy 0.836).
- Best fine-tuned family by seed mean: `kev-9b` (0.825 ± 0.010 [0.817–0.836]).

### semantic-detection (`noul`)

Test items: 2074 (True=923, False=1151).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.738 | 0.699–0.773 | 0.678 | 0.798 | 0.078 | 0.046 | NVIDIA A10G | 17.155 | $1.2542 |
| kev-0.8b-ft-s18 | 0.711 | 0.663–0.753 | 0.571 | 0.851 | 0.101 | 0.028 | NVIDIA A10G | 17.388 | $0.7178 |
| kev-0.8b-ft-s19 | 0.741 | 0.687–0.781 | 0.666 | 0.816 | 0.090 | 0.032 | NVIDIA A10G | 17.169 | $1.6275 |
| kev-0.8b FT mean ± SD [range] | 0.730 ± 0.017 [0.711–0.741] | — | 0.638 ± 0.059 [0.571–0.678] | 0.821 ± 0.027 [0.798–0.851] | 0.090 ± 0.012 [0.078–0.101] | 0.035 ± 0.009 [0.028–0.046] | — | — | — |
| kev-4b-ft-s17 | 0.839 | 0.781–0.884 | 0.733 | 0.945 | 0.066 | 0.025 | NVIDIA A10G | 64.828 | $2.2303 |
| kev-4b-ft-s18 | 0.862 | 0.821–0.894 | 0.788 | 0.936 | 0.052 | 0.016 | NVIDIA A10G | 64.942 | $2.2303 |
| kev-4b-ft-s19 | 0.831 | 0.781–0.874 | 0.714 | 0.949 | 0.080 | 0.032 | NVIDIA A10G | 64.918 | $1.2967 |
| kev-4b FT mean ± SD [range] | 0.844 ± 0.016 [0.831–0.862] | — | 0.745 ± 0.038 [0.714–0.788] | 0.943 ± 0.007 [0.936–0.949] | 0.066 ± 0.014 [0.052–0.080] | 0.025 ± 0.008 [0.016–0.032] | — | — | — |
| kev-9b-ft-s17 | 0.880 | 0.836–0.909 | 0.845 | 0.914 | 0.046 | 0.024 | NVIDIA L40S | 62.502 | $1.1867 |
| kev-9b-ft-s18 | 0.883 | 0.845–0.909 | 0.850 | 0.915 | 0.035 | 0.023 | NVIDIA L40S | 61.951 | $1.3750 |
| kev-9b-ft-s19 | 0.886 | 0.857–0.908 | 0.843 | 0.930 | 0.038 | 0.017 | NVIDIA L40S | 62.130 | $1.9192 |
| kev-9b FT mean ± SD [range] | 0.883 ± 0.003 [0.880–0.886] | — | 0.846 ± 0.004 [0.843–0.850] | 0.919 ± 0.009 [0.914–0.930] | 0.040 ± 0.006 [0.035–0.046] | 0.021 ± 0.004 [0.017–0.024] | — | — | — |

- Best single arm: `kev-9b-ft-s19` (balanced accuracy 0.886).
- Best fine-tuned family by seed mean: `kev-9b` (0.883 ± 0.003 [0.880–0.886]).

## Balanced accuracy by test label origin

Computed by this generator from each arm's forward-order test predictions (`results/corpus-v3-on-v5b/<arm>/results/predictions/<arm>.jsonl`) joined by item id to the arm's hash-checked test split (`<arm>/data/test.jsonl`), which supplies `label` and `label_origin`. Balanced accuracy is the headline's (`test_raw`): the mean recall of real-defect and no-defect for finding confirmation, where insufficient-context items count in n only, and of True and False for semantic detection. The *All* column reproduces each arm's headline; the generator refuses to render when it does not. A slice that holds one class reduces to that class's recall, and small slices are noisy. Fine-tune family rows give the seed mean ± sample SD over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items by origin: `human-adjudication` 173 (real-defect=96, no-defect=75, insufficient-context=2); `llm-review-consensus` 114 (real-defect=23, no-defect=91); `construction` 1310 (real-defect=655, no-defect=655).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.746 | 0.519 | 0.781 | 0.771 |
| kev-0.8b-ft-s18 | 0.775 | 0.557 | 0.716 | 0.802 |
| kev-0.8b-ft-s19 | 0.753 | 0.518 | 0.754 | 0.779 |
| kev-0.8b FT mean ± SD | 0.758 ± 0.015 | 0.531 ± 0.022 | 0.750 ± 0.033 | 0.784 ± 0.016 |
| kev-4b-ft-s17 | 0.794 | 0.482 | 0.715 | 0.835 |
| kev-4b-ft-s18 | 0.793 | 0.508 | 0.731 | 0.834 |
| kev-4b-ft-s19 | 0.789 | 0.510 | 0.737 | 0.827 |
| kev-4b FT mean ± SD | 0.792 ± 0.003 | 0.500 ± 0.015 | 0.728 ± 0.011 | 0.832 ± 0.004 |
| kev-9b-ft-s17 | 0.822 | 0.504 | 0.813 | 0.863 |
| kev-9b-ft-s18 | 0.836 | 0.502 | 0.813 | 0.882 |
| kev-9b-ft-s19 | 0.817 | 0.500 | 0.797 | 0.860 |
| kev-9b FT mean ± SD | 0.825 ± 0.010 | 0.502 ± 0.002 | 0.808 ± 0.010 | 0.868 ± 0.012 |

### semantic-detection (`noul`)

Test items by origin: `human-adjudication` 85 (False=57, True=28); `llm-review-consensus` 207 (False=203, True=4); `construction` 1782 (False=891, True=891).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.738 | 0.509 | 0.615 | 0.722 |
| kev-0.8b-ft-s18 | 0.711 | 0.500 | 0.625 | 0.699 |
| kev-0.8b-ft-s19 | 0.741 | 0.500 | 0.495 | 0.728 |
| kev-0.8b FT mean ± SD | 0.730 ± 0.017 | 0.503 ± 0.005 | 0.578 ± 0.072 | 0.716 ± 0.015 |
| kev-4b-ft-s17 | 0.839 | 0.527 | 0.745 | 0.844 |
| kev-4b-ft-s18 | 0.862 | 0.500 | 0.615 | 0.869 |
| kev-4b-ft-s19 | 0.831 | 0.491 | 0.623 | 0.837 |
| kev-4b FT mean ± SD | 0.844 ± 0.016 | 0.506 ± 0.019 | 0.661 ± 0.073 | 0.850 ± 0.017 |
| kev-9b-ft-s17 | 0.880 | 0.466 | 0.993 | 0.886 |
| kev-9b-ft-s18 | 0.883 | 0.430 | 0.868 | 0.890 |
| kev-9b-ft-s19 | 0.886 | 0.465 | 0.868 | 0.894 |
| kev-9b FT mean ± SD | 0.883 ± 0.003 | 0.454 ± 0.021 | 0.909 ± 0.072 | 0.890 ± 0.004 |

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | not evaluated | — | 0.758 | — | — | — | — | — | — |
| kev-4b | not evaluated | — | 0.792 | — | — | — | — | — | — |
| kev-9b | not evaluated | — | 0.825 | — | — | — | — | — | — |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | not evaluated | — | 0.730 | — | — | — | — | — | — |
| kev-4b | not evaluated | — | 0.844 | — | — | — | — | — | — |
| kev-9b | not evaluated | — | 0.883 | — | — | — | — | — | — |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-08b-s17-20260929214043 | not in ledger | 1 / 0 / 0 | $1.25 | $1.25 |
| kev-0.8b-ft-s18 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-08b-s18-20260929214053 | not in ledger | 1 / 0 / 0 | $0.72 | $0.72 |
| kev-0.8b-ft-s19 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-08b-s19-20260929214105 | not in ledger | 1 / 0 / 0 | $1.63 | $1.63 |
| kev-4b-ft-s17 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-4b-s17-20260929214114 | not in ledger | 1 / 0 / 0 | $2.23 | $2.23 |
| kev-4b-ft-s18 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-4b-s18-20260929214124 | not in ledger | 1 / 0 / 0 | $2.23 | $2.23 |
| kev-4b-ft-s19 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-4b-s19-20260929214135 | not in ledger | 1 / 0 / 0 | $1.30 | $1.30 |
| kev-9b-ft-s17 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-9b-s17-20260929214144 | not in ledger | 1 / 0 / 0 | $1.19 | $1.19 |
| kev-9b-ft-s18 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-9b-s18-20260930001932 | not in ledger | 1 / 0 / 0 | $1.38 | $1.38 |
| kev-9b-ft-s19 | 0 / 0 / 0 | $0.00 | slopvac-judge-kev-9b-s19-20260930015505 | not in ledger | 1 / 0 / 0 | $1.92 | $1.92 |

Campaign total: **$13.84 USD** (training $0.00, evaluation $13.84) over 0 training and 9 evaluation jobs.

### Failed and stopped attempts

None.

## Panel agreement caveat

Independent corpus panel agreement (source: `/Users/sjors/tmp/worktrees/slopvac/exp-judge-corpus/scripts/judge-corpus/items/panel-agreement.json`):
- finding-confirmation: Fleiss κ=0.30 (4097 three-vote items).
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
| kev-0.8b-ft-s17 | 2074 | 0.744 | 0.738 | 0.825 | 0.176 | 0.542 | 0.078 | 0.172 | 0.523 | 0.046 | 0.699–0.773 | 0.053–0.109 | 0.037–0.072 | 0.678 | 0.798 | — | — | — | 17.155 | 64.840 |
| kev-0.8b-ft-s18 | 2074 | 0.726 | 0.711 | 0.815 | 0.190 | 0.582 | 0.101 | 0.179 | 0.536 | 0.028 | 0.663–0.753 | 0.065–0.147 | 0.022–0.064 | 0.571 | 0.851 | — | — | — | 17.388 | 66.210 |
| kev-0.8b-ft-s19 | 2074 | 0.749 | 0.741 | 0.826 | 0.179 | 0.559 | 0.090 | 0.171 | 0.517 | 0.032 | 0.687–0.781 | 0.059–0.135 | 0.024–0.065 | 0.666 | 0.816 | — | — | — | 17.169 | 65.849 |
| FT mean ± SD [range] | — | 0.740 ± 0.012 [0.726–0.749] | 0.730 ± 0.017 [0.711–0.741] | 0.822 ± 0.006 [0.815–0.826] | 0.182 ± 0.007 [0.176–0.190] | 0.561 ± 0.020 [0.542–0.582] | 0.090 ± 0.012 [0.078–0.101] | 0.174 ± 0.004 [0.171–0.179] | 0.525 ± 0.010 [0.517–0.536] | 0.035 ± 0.009 [0.028–0.046] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1597 | 0.744 | 0.746 | 0.819 | 0.358 | 0.561 | 0.081 | 0.345 | 0.535 | 0.023 | 0.691–0.792 | 0.045–0.133 | 0.020–0.072 | — | — | 0.003 | 0.903 | 0.095 | 17.155 | 64.840 |
| kev-0.8b-ft-s18 | 1597 | 0.772 | 0.775 | 0.832 | 0.351 | 0.569 | 0.094 | 0.338 | 0.534 | 0.041 | 0.724–0.819 | 0.059–0.135 | 0.032–0.076 | — | — | 0.003 | 0.926 | 0.073 | 17.388 | 66.210 |
| kev-0.8b-ft-s19 | 1597 | 0.750 | 0.753 | 0.820 | 0.350 | 0.544 | 0.043 | 0.347 | 0.540 | 0.015 | 0.699–0.800 | 0.022–0.096 | 0.018–0.067 | — | — | 0.003 | 0.908 | 0.079 | 17.169 | 65.849 |
| FT mean ± SD [range] | — | 0.755 ± 0.015 [0.744–0.772] | 0.758 ± 0.015 [0.746–0.775] | 0.824 ± 0.007 [0.819–0.832] | 0.353 ± 0.004 [0.350–0.358] | 0.558 ± 0.013 [0.544–0.569] | 0.073 ± 0.027 [0.043–0.094] | 0.343 ± 0.004 [0.338–0.347] | 0.536 ± 0.003 [0.534–0.540] | 0.027 ± 0.013 [0.015–0.041] | — | — | — | — | — | 0.003 ± 0.000 [0.003–0.003] | 0.912 ± 0.012 [0.903–0.926] | 0.082 ± 0.011 [0.073–0.095] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 2074 | 0.851 | 0.839 | 0.929 | 0.115 | 0.385 | 0.066 | 0.110 | 0.358 | 0.025 | 0.781–0.884 | 0.034–0.114 | 0.014–0.072 | 0.733 | 0.945 | — | — | — | 64.828 | 204.398 |
| kev-4b-ft-s18 | 2074 | 0.870 | 0.862 | 0.933 | 0.105 | 0.357 | 0.052 | 0.102 | 0.339 | 0.016 | 0.821–0.894 | 0.030–0.086 | 0.011–0.050 | 0.788 | 0.936 | — | — | — | 64.942 | 203.296 |
| kev-4b-ft-s19 | 2074 | 0.844 | 0.831 | 0.933 | 0.120 | 0.408 | 0.080 | 0.112 | 0.363 | 0.032 | 0.781–0.874 | 0.049–0.121 | 0.019–0.067 | 0.714 | 0.949 | — | — | — | 64.918 | 201.655 |
| FT mean ± SD [range] | — | 0.855 ± 0.013 [0.844–0.870] | 0.844 ± 0.016 [0.831–0.862] | 0.932 ± 0.002 [0.929–0.933] | 0.113 ± 0.008 [0.105–0.120] | 0.384 ± 0.025 [0.357–0.408] | 0.066 ± 0.014 [0.052–0.080] | 0.108 ± 0.006 [0.102–0.112] | 0.353 ± 0.013 [0.339–0.363] | 0.025 ± 0.008 [0.016–0.032] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 1597 | 0.790 | 0.794 | 0.883 | 0.337 | 0.603 | 0.134 | 0.302 | 0.495 | 0.036 | 0.743–0.839 | 0.092–0.180 | 0.022–0.083 | — | — | 0.002 | 0.955 | 0.044 | 64.828 | 204.398 |
| kev-4b-ft-s18 | 1597 | 0.788 | 0.793 | 0.897 | 0.322 | 0.539 | 0.120 | 0.295 | 0.483 | 0.051 | 0.745–0.838 | 0.080–0.164 | 0.035–0.090 | — | — | 0.002 | 0.964 | 0.044 | 64.942 | 203.296 |
| kev-4b-ft-s19 | 1597 | 0.784 | 0.789 | 0.890 | 0.338 | 0.580 | 0.133 | 0.303 | 0.487 | 0.052 | 0.738–0.837 | 0.089–0.181 | 0.032–0.096 | — | — | 0.002 | 0.974 | 0.030 | 64.918 | 201.655 |
| FT mean ± SD [range] | — | 0.787 ± 0.003 [0.784–0.790] | 0.792 ± 0.003 [0.789–0.794] | 0.890 ± 0.007 [0.883–0.897] | 0.333 ± 0.009 [0.322–0.338] | 0.574 ± 0.033 [0.539–0.603] | 0.129 ± 0.008 [0.120–0.134] | 0.300 ± 0.004 [0.295–0.303] | 0.488 ± 0.006 [0.483–0.495] | 0.047 ± 0.009 [0.036–0.052] | — | — | — | — | — | 0.002 ± 0.000 [0.002–0.002] | 0.964 ± 0.009 [0.955–0.974] | 0.040 ± 0.008 [0.030–0.044] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 2074 | 0.883 | 0.880 | 0.946 | 0.091 | 0.315 | 0.046 | 0.088 | 0.297 | 0.024 | 0.836–0.909 | 0.029–0.077 | 0.018–0.044 | 0.845 | 0.914 | — | — | — | 62.502 | 129.922 |
| kev-9b-ft-s18 | 2074 | 0.886 | 0.883 | 0.947 | 0.086 | 0.298 | 0.035 | 0.085 | 0.290 | 0.023 | 0.845–0.909 | 0.023–0.061 | 0.017–0.042 | 0.850 | 0.915 | — | — | — | 61.951 | 127.033 |
| kev-9b-ft-s19 | 2074 | 0.891 | 0.886 | 0.947 | 0.086 | 0.303 | 0.038 | 0.085 | 0.290 | 0.017 | 0.857–0.908 | 0.026–0.056 | 0.015–0.037 | 0.843 | 0.930 | — | — | — | 62.130 | 127.987 |
| FT mean ± SD [range] | — | 0.887 ± 0.004 [0.883–0.891] | 0.883 ± 0.003 [0.880–0.886] | 0.947 ± 0.001 [0.946–0.947] | 0.088 ± 0.003 [0.086–0.091] | 0.305 ± 0.009 [0.298–0.315] | 0.040 ± 0.006 [0.035–0.046] | 0.086 ± 0.002 [0.085–0.088] | 0.292 ± 0.004 [0.290–0.297] | 0.021 ± 0.004 [0.017–0.024] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 1597 | 0.818 | 0.822 | 0.920 | 0.281 | 0.472 | 0.104 | 0.256 | 0.417 | 0.044 | 0.777–0.865 | 0.065–0.147 | 0.027–0.080 | — | — | 0.003 | 0.968 | 0.040 | 62.502 | 129.922 |
| kev-9b-ft-s18 | 1597 | 0.832 | 0.836 | 0.930 | 0.257 | 0.454 | 0.087 | 0.240 | 0.404 | 0.018 | 0.790–0.877 | 0.052–0.129 | 0.018–0.051 | — | — | 0.003 | 0.969 | 0.034 | 61.951 | 127.033 |
| kev-9b-ft-s19 | 1597 | 0.813 | 0.817 | 0.928 | 0.288 | 0.477 | 0.107 | 0.262 | 0.423 | 0.049 | 0.768–0.863 | 0.067–0.152 | 0.034–0.082 | — | — | 0.003 | 0.972 | 0.031 | 62.130 | 127.987 |
| FT mean ± SD [range] | — | 0.821 ± 0.010 [0.813–0.832] | 0.825 ± 0.010 [0.817–0.836] | 0.926 ± 0.006 [0.920–0.930] | 0.276 ± 0.016 [0.257–0.288] | 0.468 ± 0.012 [0.454–0.477] | 0.099 ± 0.011 [0.087–0.107] | 0.253 ± 0.012 [0.240–0.262] | 0.415 ± 0.010 [0.404–0.423] | 0.037 ± 0.017 [0.018–0.049] | — | — | — | — | — | 0.003 ± 0.000 [0.003–0.003] | 0.970 ± 0.002 [0.968–0.972] | 0.035 ± 0.004 [0.031–0.040] | — | — |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.16xlarge | us-west-2 | 17.155 | 64.840 | 645 | $1.2542 | sv-eval-kev-08b-ft-s17-261003052857715322 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.388 | 66.210 | 646 | $0.7178 | sv-eval-kev-08b-ft-s18-261003054058615493 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.12xlarge | us-east-1 | 17.169 | 65.849 | 651 | $1.6275 | sv-eval-kev-08b-ft-s19-261003054124827141 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.16xlarge | us-east-1 | 64.828 | 204.398 | 1147 | $2.2303 | sv-eval-kev-4b-ft-s17-261003054137841258 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.16xlarge | us-west-2 | 64.942 | 203.296 | 1147 | $2.2303 | sv-eval-kev-4b-ft-s18-261003054417740605 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 64.918 | 201.655 | 1167 | $1.2967 | sv-eval-kev-4b-ft-s19-261003055244515355 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.2xlarge | us-east-1 | 62.502 | 129.922 | 1068 | $1.1867 | sv-eval-kev-9b-ft-s17-261003114551271482 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.4xlarge | us-west-2 | 61.951 | 127.033 | 990 | $1.3750 | sv-eval-kev-9b-ft-s18-261003114615449086 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.8xlarge | us-west-2 | 62.130 | 127.987 | 987 | $1.9192 | sv-eval-kev-9b-ft-s19-261003114638189265 |

Total billed evaluation cost for the reported arms: **$13.8377 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | noul | granularity | document | 943 | 0.701 | 0.697 | 0.105 | 0.648 | 0.747 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 754 | 0.760 | 0.756 | 0.081 | 0.723 | 0.789 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 377 | 0.822 | 0.796 | 0.051 | 0.667 | 0.925 |
| kev-0.8b-ft-s17 | noul | provenance | generated | 201 | 0.871 | 0.531 | 0.064 | 0.080 | 0.983 |
| kev-0.8b-ft-s17 | noul | provenance | human | 1873 | 0.731 | 0.729 | 0.085 | 0.695 | 0.764 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2074 | 0.744 | 0.738 | 0.078 | 0.678 | 0.798 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1314 | 0.758 | 0.715 | 0.074 | 0.596 | 0.833 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 760 | 0.721 | 0.709 | 0.089 | 0.746 | 0.672 |
| kev-0.8b-ft-s17 | noul | source accuracy | generated | 201 | 0.871 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 1873 | 0.731 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 735 | 0.756 | 0.757 | 0.065 | 0.700 | 0.814 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 547 | 0.750 | 0.827 | 0.085 | 0.659 | 0.823 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 315 | 0.705 | 0.470 | 0.138 | 0.712 | 0.697 |
| kev-0.8b-ft-s17 | choice | provenance | generated | 217 | 0.650 | 0.672 | 0.202 | 0.516 | 0.828 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1380 | 0.759 | 0.673 | 0.066 | 0.722 | 0.797 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.744 | 0.664 | 0.081 | 0.691 | 0.801 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 907 | 0.760 | 0.661 | 0.071 | 0.682 | 0.800 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 690 | 0.723 | 0.750 | 0.101 | 0.696 | 0.805 |
| kev-0.8b-ft-s17 | choice | source accuracy | generated | 217 | 0.650 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1380 | 0.759 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 943 | 0.695 | 0.686 | 0.114 | 0.565 | 0.806 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 754 | 0.743 | 0.730 | 0.100 | 0.616 | 0.844 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 377 | 0.772 | 0.724 | 0.076 | 0.487 | 0.960 |
| kev-0.8b-ft-s18 | noul | provenance | generated | 201 | 0.881 | 0.520 | 0.075 | 0.040 | 1.000 |
| kev-0.8b-ft-s18 | noul | provenance | human | 1873 | 0.710 | 0.705 | 0.108 | 0.586 | 0.824 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2074 | 0.726 | 0.711 | 0.101 | 0.571 | 0.851 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1314 | 0.766 | 0.707 | 0.076 | 0.548 | 0.866 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 760 | 0.658 | 0.692 | 0.145 | 0.590 | 0.794 |
| kev-0.8b-ft-s18 | noul | source accuracy | generated | 201 | 0.881 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 1873 | 0.710 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 735 | 0.793 | 0.794 | 0.075 | 0.722 | 0.866 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 547 | 0.775 | 0.844 | 0.093 | 0.679 | 0.853 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 315 | 0.717 | 0.486 | 0.148 | 0.698 | 0.761 |
| kev-0.8b-ft-s18 | choice | provenance | generated | 217 | 0.636 | 0.660 | 0.234 | 0.492 | 0.828 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1380 | 0.793 | 0.696 | 0.072 | 0.740 | 0.849 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.772 | 0.683 | 0.094 | 0.703 | 0.846 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 907 | 0.793 | 0.674 | 0.074 | 0.662 | 0.860 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 690 | 0.745 | 0.763 | 0.121 | 0.727 | 0.799 |
| kev-0.8b-ft-s18 | choice | source accuracy | generated | 217 | 0.636 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1380 | 0.793 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 943 | 0.706 | 0.702 | 0.108 | 0.643 | 0.761 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 754 | 0.765 | 0.759 | 0.106 | 0.702 | 0.816 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 377 | 0.825 | 0.796 | 0.060 | 0.653 | 0.938 |
| kev-0.8b-ft-s19 | noul | provenance | generated | 201 | 0.866 | 0.511 | 0.091 | 0.040 | 0.983 |
| kev-0.8b-ft-s19 | noul | provenance | human | 1873 | 0.737 | 0.735 | 0.093 | 0.684 | 0.786 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2074 | 0.749 | 0.741 | 0.090 | 0.666 | 0.816 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1314 | 0.758 | 0.715 | 0.090 | 0.599 | 0.832 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 760 | 0.734 | 0.740 | 0.097 | 0.722 | 0.759 |
| kev-0.8b-ft-s19 | noul | source accuracy | generated | 201 | 0.866 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 1873 | 0.737 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 735 | 0.771 | 0.772 | 0.027 | 0.703 | 0.841 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 547 | 0.744 | 0.822 | 0.060 | 0.630 | 0.837 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 315 | 0.711 | 0.490 | 0.128 | 0.663 | 0.807 |
| kev-0.8b-ft-s19 | choice | provenance | generated | 217 | 0.627 | 0.652 | 0.189 | 0.476 | 0.828 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1380 | 0.770 | 0.680 | 0.021 | 0.706 | 0.836 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.750 | 0.669 | 0.043 | 0.671 | 0.835 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 907 | 0.775 | 0.662 | 0.041 | 0.643 | 0.843 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 690 | 0.717 | 0.746 | 0.086 | 0.688 | 0.805 |
| kev-0.8b-ft-s19 | choice | source accuracy | generated | 217 | 0.627 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1380 | 0.770 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 943 | 0.842 | 0.834 | 0.071 | 0.728 | 0.941 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 754 | 0.866 | 0.858 | 0.054 | 0.780 | 0.935 |
| kev-4b-ft-s17 | noul | granularity | sentence | 377 | 0.844 | 0.810 | 0.088 | 0.647 | 0.974 |
| kev-4b-ft-s17 | noul | provenance | generated | 201 | 0.881 | 0.571 | 0.067 | 0.160 | 0.983 |
| kev-4b-ft-s17 | noul | provenance | human | 1873 | 0.848 | 0.844 | 0.068 | 0.749 | 0.938 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2074 | 0.851 | 0.839 | 0.066 | 0.733 | 0.945 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1314 | 0.861 | 0.812 | 0.061 | 0.678 | 0.947 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 760 | 0.833 | 0.860 | 0.076 | 0.779 | 0.941 |
| kev-4b-ft-s17 | noul | source accuracy | generated | 201 | 0.881 | — | — | — | — |
| kev-4b-ft-s17 | noul | source accuracy | human | 1873 | 0.848 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 735 | 0.810 | 0.810 | 0.120 | 0.689 | 0.932 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 547 | 0.797 | 0.856 | 0.137 | 0.650 | 0.917 |
| kev-4b-ft-s17 | choice | granularity | sentence | 315 | 0.730 | 0.507 | 0.186 | 0.668 | 0.853 |
| kev-4b-ft-s17 | choice | provenance | generated | 217 | 0.571 | 0.601 | 0.322 | 0.395 | 0.806 |
| kev-4b-ft-s17 | choice | provenance | human | 1380 | 0.824 | 0.717 | 0.106 | 0.722 | 0.930 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.790 | 0.696 | 0.134 | 0.672 | 0.915 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 907 | 0.831 | 0.689 | 0.101 | 0.633 | 0.933 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 690 | 0.735 | 0.773 | 0.178 | 0.696 | 0.851 |
| kev-4b-ft-s17 | choice | source accuracy | generated | 217 | 0.571 | — | — | — | — |
| kev-4b-ft-s17 | choice | source accuracy | human | 1380 | 0.824 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 943 | 0.862 | 0.857 | 0.059 | 0.789 | 0.925 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 754 | 0.870 | 0.863 | 0.048 | 0.801 | 0.926 |
| kev-4b-ft-s18 | noul | granularity | sentence | 377 | 0.889 | 0.866 | 0.060 | 0.753 | 0.978 |
| kev-4b-ft-s18 | noul | provenance | generated | 201 | 0.856 | 0.523 | 0.088 | 0.080 | 0.966 |
| kev-4b-ft-s18 | noul | provenance | human | 1873 | 0.871 | 0.869 | 0.050 | 0.807 | 0.930 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2074 | 0.870 | 0.862 | 0.052 | 0.788 | 0.936 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1314 | 0.870 | 0.830 | 0.057 | 0.721 | 0.939 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 760 | 0.870 | 0.884 | 0.048 | 0.842 | 0.925 |
| kev-4b-ft-s18 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-4b-ft-s18 | noul | source accuracy | human | 1873 | 0.871 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 735 | 0.811 | 0.812 | 0.102 | 0.692 | 0.932 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 547 | 0.797 | 0.522 | 0.114 | 0.622 | 0.943 |
| kev-4b-ft-s18 | choice | granularity | sentence | 315 | 0.721 | 0.501 | 0.176 | 0.659 | 0.844 |
| kev-4b-ft-s18 | choice | provenance | generated | 217 | 0.576 | 0.608 | 0.309 | 0.387 | 0.828 |
| kev-4b-ft-s18 | choice | provenance | human | 1380 | 0.822 | 0.549 | 0.093 | 0.712 | 0.937 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.788 | 0.529 | 0.120 | 0.663 | 0.924 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 907 | 0.827 | 0.520 | 0.090 | 0.633 | 0.928 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 690 | 0.738 | 0.794 | 0.161 | 0.680 | 0.908 |
| kev-4b-ft-s18 | choice | source accuracy | generated | 217 | 0.576 | — | — | — | — |
| kev-4b-ft-s18 | choice | source accuracy | human | 1380 | 0.822 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 943 | 0.841 | 0.833 | 0.084 | 0.725 | 0.941 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 754 | 0.849 | 0.838 | 0.077 | 0.738 | 0.938 |
| kev-4b-ft-s19 | noul | granularity | sentence | 377 | 0.844 | 0.807 | 0.090 | 0.627 | 0.987 |
| kev-4b-ft-s19 | noul | provenance | generated | 201 | 0.871 | 0.514 | 0.088 | 0.040 | 0.989 |
| kev-4b-ft-s19 | noul | provenance | human | 1873 | 0.841 | 0.837 | 0.080 | 0.733 | 0.942 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2074 | 0.844 | 0.831 | 0.080 | 0.714 | 0.949 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1314 | 0.859 | 0.805 | 0.073 | 0.656 | 0.953 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 760 | 0.818 | 0.847 | 0.097 | 0.761 | 0.933 |
| kev-4b-ft-s19 | noul | source accuracy | generated | 201 | 0.871 | — | — | — | — |
| kev-4b-ft-s19 | noul | source accuracy | human | 1873 | 0.841 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 735 | 0.805 | 0.806 | 0.119 | 0.678 | 0.934 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 547 | 0.779 | 0.510 | 0.139 | 0.606 | 0.923 |
| kev-4b-ft-s19 | choice | granularity | sentence | 315 | 0.743 | 0.524 | 0.165 | 0.654 | 0.917 |
| kev-4b-ft-s19 | choice | provenance | generated | 217 | 0.571 | 0.606 | 0.322 | 0.363 | 0.849 |
| kev-4b-ft-s19 | choice | provenance | human | 1380 | 0.817 | 0.547 | 0.105 | 0.702 | 0.938 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.784 | 0.526 | 0.133 | 0.650 | 0.928 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 907 | 0.831 | 0.522 | 0.096 | 0.630 | 0.937 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 690 | 0.722 | 0.780 | 0.184 | 0.663 | 0.897 |
| kev-4b-ft-s19 | choice | source accuracy | generated | 217 | 0.571 | — | — | — | — |
| kev-4b-ft-s19 | choice | source accuracy | human | 1380 | 0.817 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 943 | 0.874 | 0.872 | 0.053 | 0.849 | 0.895 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 754 | 0.875 | 0.872 | 0.057 | 0.839 | 0.904 |
| kev-9b-ft-s17 | noul | granularity | sentence | 377 | 0.923 | 0.910 | 0.040 | 0.847 | 0.974 |
| kev-9b-ft-s17 | noul | provenance | generated | 201 | 0.846 | 0.603 | 0.089 | 0.280 | 0.926 |
| kev-9b-ft-s17 | noul | provenance | human | 1873 | 0.887 | 0.886 | 0.043 | 0.861 | 0.912 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2074 | 0.883 | 0.880 | 0.046 | 0.845 | 0.914 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1314 | 0.872 | 0.848 | 0.063 | 0.784 | 0.913 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 760 | 0.903 | 0.906 | 0.035 | 0.895 | 0.917 |
| kev-9b-ft-s17 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-9b-ft-s17 | noul | source accuracy | human | 1873 | 0.887 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 735 | 0.839 | 0.840 | 0.078 | 0.743 | 0.937 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 547 | 0.821 | 0.871 | 0.109 | 0.667 | 0.947 |
| kev-9b-ft-s17 | choice | granularity | sentence | 315 | 0.762 | 0.539 | 0.166 | 0.663 | 0.954 |
| kev-9b-ft-s17 | choice | provenance | generated | 217 | 0.618 | 0.656 | 0.266 | 0.387 | 0.925 |
| kev-9b-ft-s17 | choice | provenance | human | 1380 | 0.849 | 0.734 | 0.079 | 0.756 | 0.946 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.818 | 0.715 | 0.104 | 0.700 | 0.943 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 907 | 0.850 | 0.704 | 0.076 | 0.669 | 0.943 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 690 | 0.775 | 0.831 | 0.143 | 0.719 | 0.943 |
| kev-9b-ft-s17 | choice | source accuracy | generated | 217 | 0.618 | — | — | — | — |
| kev-9b-ft-s17 | choice | source accuracy | human | 1380 | 0.849 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 943 | 0.877 | 0.876 | 0.043 | 0.856 | 0.895 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 754 | 0.889 | 0.885 | 0.036 | 0.854 | 0.916 |
| kev-9b-ft-s18 | noul | granularity | sentence | 377 | 0.905 | 0.891 | 0.030 | 0.827 | 0.956 |
| kev-9b-ft-s18 | noul | provenance | generated | 201 | 0.841 | 0.532 | 0.091 | 0.120 | 0.943 |
| kev-9b-ft-s18 | noul | provenance | human | 1873 | 0.891 | 0.890 | 0.030 | 0.871 | 0.910 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2074 | 0.886 | 0.883 | 0.035 | 0.850 | 0.915 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1314 | 0.874 | 0.851 | 0.048 | 0.791 | 0.912 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 760 | 0.908 | 0.912 | 0.028 | 0.899 | 0.925 |
| kev-9b-ft-s18 | noul | source accuracy | generated | 201 | 0.841 | — | — | — | — |
| kev-9b-ft-s18 | noul | source accuracy | human | 1873 | 0.891 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 735 | 0.850 | 0.851 | 0.072 | 0.762 | 0.940 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 547 | 0.837 | 0.552 | 0.093 | 0.711 | 0.943 |
| kev-9b-ft-s18 | choice | granularity | sentence | 315 | 0.778 | 0.546 | 0.130 | 0.693 | 0.945 |
| kev-9b-ft-s18 | choice | provenance | generated | 217 | 0.608 | 0.647 | 0.295 | 0.379 | 0.914 |
| kev-9b-ft-s18 | choice | provenance | human | 1380 | 0.867 | 0.579 | 0.056 | 0.792 | 0.946 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.832 | 0.557 | 0.087 | 0.730 | 0.942 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 907 | 0.859 | 0.545 | 0.075 | 0.685 | 0.950 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 690 | 0.796 | 0.835 | 0.111 | 0.756 | 0.914 |
| kev-9b-ft-s18 | choice | source accuracy | generated | 217 | 0.608 | — | — | — | — |
| kev-9b-ft-s18 | choice | source accuracy | human | 1380 | 0.867 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 943 | 0.873 | 0.871 | 0.047 | 0.842 | 0.899 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 754 | 0.898 | 0.894 | 0.040 | 0.854 | 0.933 |
| kev-9b-ft-s19 | noul | granularity | sentence | 377 | 0.923 | 0.906 | 0.045 | 0.820 | 0.991 |
| kev-9b-ft-s19 | noul | provenance | generated | 201 | 0.851 | 0.554 | 0.089 | 0.160 | 0.949 |
| kev-9b-ft-s19 | noul | provenance | human | 1873 | 0.895 | 0.894 | 0.035 | 0.862 | 0.926 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2074 | 0.891 | 0.886 | 0.038 | 0.843 | 0.930 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1314 | 0.879 | 0.847 | 0.050 | 0.760 | 0.934 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 760 | 0.912 | 0.912 | 0.021 | 0.911 | 0.913 |
| kev-9b-ft-s19 | noul | source accuracy | generated | 201 | 0.851 | — | — | — | — |
| kev-9b-ft-s19 | noul | source accuracy | human | 1873 | 0.895 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 735 | 0.831 | 0.832 | 0.091 | 0.719 | 0.945 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 547 | 0.819 | 0.869 | 0.103 | 0.654 | 0.953 |
| kev-9b-ft-s19 | choice | granularity | sentence | 315 | 0.759 | 0.539 | 0.154 | 0.654 | 0.963 |
| kev-9b-ft-s19 | choice | provenance | generated | 217 | 0.594 | 0.633 | 0.306 | 0.363 | 0.903 |
| kev-9b-ft-s19 | choice | provenance | human | 1380 | 0.847 | 0.733 | 0.078 | 0.740 | 0.957 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.813 | 0.711 | 0.107 | 0.683 | 0.951 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 907 | 0.859 | 0.709 | 0.079 | 0.672 | 0.955 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 690 | 0.752 | 0.813 | 0.150 | 0.690 | 0.937 |
| kev-9b-ft-s19 | choice | source accuracy | generated | 217 | 0.594 | — | — | — | — |
| kev-9b-ft-s19 | choice | source accuracy | human | 1380 | 0.847 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1095 | 0.495 | 33 | 0.738 | 0.738 | 0.732 |
| kev-0.8b-ft-s18 | 1095 | 0.432 | 33 | 0.711 | 0.721 | 0.711 |
| kev-0.8b-ft-s19 | 1095 | 0.503 | 33 | 0.741 | 0.741 | 0.736 |
| kev-4b-ft-s17 | 1095 | 0.279 | 33 | 0.839 | 0.851 | 0.848 |
| kev-4b-ft-s18 | 1095 | 0.272 | 33 | 0.862 | 0.870 | 0.860 |
| kev-4b-ft-s19 | 1095 | 0.374 | 33 | 0.831 | 0.843 | 0.843 |
| kev-9b-ft-s17 | 1095 | 0.494 | 33 | 0.880 | 0.880 | 0.874 |
| kev-9b-ft-s18 | 1095 | 0.581 | 33 | 0.883 | 0.882 | 0.866 |
| kev-9b-ft-s19 | 1095 | 0.614 | 33 | 0.886 | 0.880 | 0.868 |

## Interpretation and caveats

- Test label origins: construction (3092), human-adjudication (258), llm-review-consensus (321). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice insufficient-context=2, no-defect=821, real-defect=774; yes/no False=1151, True=923. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.30 finding-confirmation, κ=0.30 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
