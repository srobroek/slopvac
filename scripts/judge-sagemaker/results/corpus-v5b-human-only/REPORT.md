# Corpus evaluation report: `corpus-v5b-human-only`

## Status

- v5b: lint rules at main ca941af16a; labels human-adjudication > llm-review-consensus > teacher-panel; redesigned semantic items. The human-adjudication test slice is the rows four LLM reviewers could not settle, labelled once by one person with the earlier (confusing) review UI; read it as preliminary.

## Dataset and coverage

- Campaign: `corpus-20261003-s17-v5b/human-only`. Label-source ablation on the v5b export: the full variant's train split without the settled LLM-review consensus labels (export --drop-train-origin llm-review-consensus; those rows are unlabelled in train, as if never reviewed), so human answers, teacher-panel labels and constructions remain. Test and calibration are byte-identical to v5b full. Base arms are not repeated: v5b-full evaluates them on the same splits. runtime_scale is 13,319 train rows / 5,420.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 9 of 9 required (`kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 7 of 25 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1720 examples; SHA-256 `8534bee7b935ae80b47d35e1e96a4a288ab3ba86c6bfe851ff01e8dcf3300b1b`.
- Test: 3671 examples; SHA-256 `a77f6f64b85b81a13330df57b8cd3973edd2b295ae30efdf4ddc12a4a8bb0b31`.
- Test composition: label origins `construction`=3092, `human-adjudication`=258, `llm-review-consensus`=321; choice labels insufficient-context=2, no-defect=821, real-defect=774; yes/no labels False=1151, True=923.

## Headline by role

Each arm's numbers come from `results/corpus-v5b-human-only/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1597 (real-defect=774, no-defect=821).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.743 | 0.698–0.784 | 0.813 | 0.674 | 0.059 | 0.042 | NVIDIA A10G | 17.584 | $0.3672 |
| kev-0.8b-ft-s18 | 0.744 | 0.694–0.788 | 0.835 | 0.654 | 0.040 | 0.027 | NVIDIA A10G | 17.495 | $0.3678 |
| kev-0.8b-ft-s19 | 0.741 | 0.690–0.786 | 0.851 | 0.630 | 0.044 | 0.029 | NVIDIA A10G | 17.471 | $0.3700 |
| kev-0.8b FT mean ± SD [range] | 0.743 ± 0.002 [0.741–0.744] | — | 0.833 ± 0.019 [0.813–0.851] | 0.652 ± 0.022 [0.630–0.674] | 0.048 ± 0.010 [0.040–0.059] | 0.033 ± 0.008 [0.027–0.042] | — | — | — |
| kev-4b-ft-s17 | 0.780 | 0.729–0.828 | 0.916 | 0.644 | 0.131 | 0.045 | NVIDIA A10G | 65.543 | $0.6667 |
| kev-4b-ft-s18 | 0.800 | 0.751–0.844 | 0.920 | 0.680 | 0.115 | 0.050 | NVIDIA A10G | 65.526 | $0.6706 |
| kev-4b-ft-s19 | 0.797 | 0.742–0.846 | 0.913 | 0.680 | 0.126 | 0.046 | NVIDIA A10G | 65.281 | $0.9700 |
| kev-4b FT mean ± SD [range] | 0.792 ± 0.011 [0.780–0.800] | — | 0.916 ± 0.003 [0.913–0.920] | 0.668 ± 0.020 [0.644–0.680] | 0.124 ± 0.008 [0.115–0.131] | 0.047 ± 0.003 [0.045–0.050] | — | — | — |
| kev-9b-ft-s17 | 0.806 | 0.754–0.851 | 0.946 | 0.666 | 0.109 | 0.049 | NVIDIA L40S | 62.025 | $1.1678 |
| kev-9b-ft-s18 | 0.813 | 0.764–0.859 | 0.947 | 0.680 | 0.088 | 0.052 | NVIDIA L40S | 62.117 | $1.3764 |
| kev-9b-ft-s19 | 0.812 | 0.759–0.860 | 0.943 | 0.681 | 0.112 | 0.049 | NVIDIA L40S | 62.043 | $1.3778 |
| kev-9b FT mean ± SD [range] | 0.810 ± 0.004 [0.806–0.813] | — | 0.945 ± 0.002 [0.943–0.947] | 0.676 ± 0.008 [0.666–0.681] | 0.103 ± 0.013 [0.088–0.112] | 0.050 ± 0.002 [0.049–0.052] | — | — | — |

- Best single arm: `kev-9b-ft-s18` (balanced accuracy 0.813).
- Best fine-tuned family by seed mean: `kev-9b` (0.810 ± 0.004 [0.806–0.813]).

### semantic-detection (`noul`)

Test items: 2074 (True=923, False=1151).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.751 | 0.706–0.798 | 0.652 | 0.850 | 0.062 | 0.047 | NVIDIA A10G | 17.584 | $0.3672 |
| kev-0.8b-ft-s18 | 0.759 | 0.709–0.811 | 0.665 | 0.853 | 0.064 | 0.047 | NVIDIA A10G | 17.495 | $0.3678 |
| kev-0.8b-ft-s19 | 0.768 | 0.728–0.812 | 0.690 | 0.846 | 0.065 | 0.040 | NVIDIA A10G | 17.471 | $0.3700 |
| kev-0.8b FT mean ± SD [range] | 0.759 ± 0.009 [0.751–0.768] | — | 0.669 ± 0.019 [0.652–0.690] | 0.850 ± 0.003 [0.846–0.853] | 0.064 ± 0.001 [0.062–0.065] | 0.045 ± 0.004 [0.040–0.047] | — | — | — |
| kev-4b-ft-s17 | 0.892 | 0.847–0.921 | 0.848 | 0.936 | 0.053 | 0.026 | NVIDIA A10G | 65.543 | $0.6667 |
| kev-4b-ft-s18 | 0.902 | 0.865–0.929 | 0.849 | 0.954 | 0.040 | 0.020 | NVIDIA A10G | 65.526 | $0.6706 |
| kev-4b-ft-s19 | 0.908 | 0.878–0.933 | 0.876 | 0.939 | 0.039 | 0.014 | NVIDIA A10G | 65.281 | $0.9700 |
| kev-4b FT mean ± SD [range] | 0.901 ± 0.008 [0.892–0.908] | — | 0.858 ± 0.016 [0.848–0.876] | 0.943 ± 0.010 [0.936–0.954] | 0.044 ± 0.008 [0.039–0.053] | 0.020 ± 0.006 [0.014–0.026] | — | — | — |
| kev-9b-ft-s17 | 0.906 | 0.873–0.930 | 0.867 | 0.946 | 0.048 | 0.015 | NVIDIA L40S | 62.025 | $1.1678 |
| kev-9b-ft-s18 | 0.894 | 0.864–0.916 | 0.833 | 0.954 | 0.046 | 0.019 | NVIDIA L40S | 62.117 | $1.3764 |
| kev-9b-ft-s19 | 0.907 | 0.881–0.929 | 0.876 | 0.938 | 0.042 | 0.013 | NVIDIA L40S | 62.043 | $1.3778 |
| kev-9b FT mean ± SD [range] | 0.902 ± 0.008 [0.894–0.907] | — | 0.859 ± 0.023 [0.833–0.876] | 0.946 ± 0.008 [0.938–0.954] | 0.045 ± 0.003 [0.042–0.048] | 0.016 ± 0.003 [0.013–0.019] | — | — | — |

- Best single arm: `kev-4b-ft-s19` (balanced accuracy 0.908).
- Best fine-tuned family by seed mean: `kev-9b` (0.902 ± 0.008 [0.894–0.907]).

## Balanced accuracy by test label origin

Computed by this generator from each arm's forward-order test predictions (`results/corpus-v5b-human-only/<arm>/results/predictions/<arm>.jsonl`) joined by item id to the arm's hash-checked test split (`<arm>/data/test.jsonl`), which supplies `label` and `label_origin`. Balanced accuracy is the headline's (`test_raw`): the mean recall of real-defect and no-defect for finding confirmation, where insufficient-context items count in n only, and of True and False for semantic detection. The *All* column reproduces each arm's headline; the generator refuses to render when it does not. A slice that holds one class reduces to that class's recall, and small slices are noisy. Fine-tune family rows give the seed mean ± sample SD over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items by origin: `human-adjudication` 173 (real-defect=96, no-defect=75, insufficient-context=2); `llm-review-consensus` 114 (real-defect=23, no-defect=91); `construction` 1310 (real-defect=655, no-defect=655).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.743 | 0.546 | 0.786 | 0.763 |
| kev-0.8b-ft-s18 | 0.744 | 0.485 | 0.759 | 0.773 |
| kev-0.8b-ft-s19 | 0.741 | 0.500 | 0.775 | 0.767 |
| kev-0.8b FT mean ± SD | 0.743 ± 0.002 | 0.510 ± 0.032 | 0.774 ± 0.014 | 0.767 ± 0.005 |
| kev-4b-ft-s17 | 0.780 | 0.496 | 0.721 | 0.816 |
| kev-4b-ft-s18 | 0.800 | 0.501 | 0.819 | 0.837 |
| kev-4b-ft-s19 | 0.797 | 0.514 | 0.775 | 0.831 |
| kev-4b FT mean ± SD | 0.792 ± 0.011 | 0.504 ± 0.010 | 0.772 ± 0.049 | 0.828 ± 0.011 |
| kev-9b-ft-s17 | 0.806 | 0.489 | 0.786 | 0.850 |
| kev-9b-ft-s18 | 0.813 | 0.463 | 0.786 | 0.862 |
| kev-9b-ft-s19 | 0.812 | 0.471 | 0.791 | 0.859 |
| kev-9b FT mean ± SD | 0.810 ± 0.004 | 0.474 ± 0.013 | 0.788 ± 0.003 | 0.857 ± 0.006 |

### semantic-detection (`noul`)

Test items by origin: `human-adjudication` 85 (False=57, True=28); `llm-review-consensus` 207 (False=203, True=4); `construction` 1782 (False=891, True=891).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.751 | 0.466 | 0.863 | 0.745 |
| kev-0.8b-ft-s18 | 0.759 | 0.448 | 0.998 | 0.752 |
| kev-0.8b-ft-s19 | 0.768 | 0.456 | 0.870 | 0.761 |
| kev-0.8b FT mean ± SD | 0.759 ± 0.009 | 0.457 ± 0.009 | 0.910 ± 0.076 | 0.753 ± 0.008 |
| kev-4b-ft-s17 | 0.892 | 0.466 | 0.868 | 0.902 |
| kev-4b-ft-s18 | 0.902 | 0.457 | 0.745 | 0.914 |
| kev-4b-ft-s19 | 0.908 | 0.466 | 0.865 | 0.919 |
| kev-4b FT mean ± SD | 0.901 ± 0.008 | 0.463 ± 0.005 | 0.826 ± 0.070 | 0.912 ± 0.009 |
| kev-9b-ft-s17 | 0.906 | 0.439 | 0.995 | 0.918 |
| kev-9b-ft-s18 | 0.894 | 0.457 | 0.995 | 0.905 |
| kev-9b-ft-s19 | 0.907 | 0.421 | 0.998 | 0.918 |
| kev-9b FT mean ± SD | 0.902 ± 0.008 | 0.439 ± 0.018 | 0.996 ± 0.001 | 0.913 ± 0.008 |

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | corpus-v5b-full | 0.238 | 0.743 | +0.504 | 3/3 | +0.697 | +0.311 | -0.145 | -0.062 |
| kev-4b | corpus-v5b-full | 0.308 | 0.792 | +0.484 | 3/3 | +0.429 | +0.539 | +0.010 | -0.002 |
| kev-9b | corpus-v5b-full | 0.503 | 0.810 | +0.307 | 3/3 | +0.152 | +0.462 | +0.001 | -0.033 |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | corpus-v5b-full | 0.502 | 0.759 | +0.258 | 3/3 | +0.645 | -0.130 | -0.103 | +0.025 |
| kev-4b | corpus-v5b-full | 0.545 | 0.901 | +0.355 | 3/3 | +0.704 | +0.006 | -0.060 | -0.035 |
| kev-9b | corpus-v5b-full | 0.679 | 0.902 | +0.223 | 3/3 | +0.354 | +0.092 | +0.001 | -0.033 |

## Comparison with `corpus-v5b-full`

Both campaigns score the same test and calibration export (hashes verified). Δ is `corpus-v5b-human-only` minus `corpus-v5b-full` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.

### finding-confirmation (`choice`)

| Family | corpus-v5b-human-only bal. acc. | corpus-v5b-full bal. acc. | Δ bal. acc. | Seeds better | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.743 ± 0.002 [0.741–0.744] | 0.745 ± 0.011 [0.738–0.757] | -0.003 | 2/3 | +0.022 | -0.027 | -0.003 | +0.004 |
| kev-4b | 0.792 ± 0.011 [0.780–0.800] | 0.798 ± 0.003 [0.795–0.800] | -0.006 | 2/3 | +0.012 | -0.024 | +0.021 | -0.004 |
| kev-9b | 0.810 ± 0.004 [0.806–0.813] | 0.815 ± 0.009 [0.806–0.824] | -0.004 | 1/3 | +0.007 | -0.015 | +0.010 | +0.001 |

### semantic-detection (`noul`)

| Family | corpus-v5b-human-only bal. acc. | corpus-v5b-full bal. acc. | Δ bal. acc. | Seeds better | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.759 ± 0.009 [0.751–0.768] | 0.775 ± 0.005 [0.769–0.779] | -0.015 | 0/3 | -0.027 | -0.003 | -0.003 | -0.000 |
| kev-4b | 0.901 ± 0.008 [0.892–0.908] | 0.903 ± 0.003 [0.900–0.905] | -0.003 | 1/3 | -0.006 | +0.000 | +0.010 | -0.005 |
| kev-9b | 0.902 ± 0.008 [0.894–0.907] | 0.899 ± 0.006 [0.894–0.905] | +0.004 | 2/3 | +0.006 | +0.001 | -0.004 | -0.006 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1 / 0 / 0 | $11.72 | slopvac-judge-kev-08b-s17-20261003113300 | $11.72 | 1 / 0 / 0 | $0.37 | $12.09 |
| kev-0.8b-ft-s18 | 1 / 0 / 0 | $9.37 | slopvac-judge-kev-08b-s18-20261003114701 | $9.37 | 1 / 0 / 0 | $0.37 | $9.74 |
| kev-0.8b-ft-s19 | 1 / 0 / 0 | $9.48 | slopvac-judge-kev-08b-s19-20261003114711 | $9.48 | 1 / 0 / 0 | $0.37 | $9.85 |
| kev-4b-ft-s17 | 1 / 0 / 0 | $27.62 | slopvac-judge-kev-4b-s17-20261003114723 | $27.62 | 1 / 0 / 0 | $0.67 | $28.29 |
| kev-4b-ft-s18 | 1 / 0 / 0 | $19.69 | slopvac-judge-kev-4b-s18-20261003120537 | $19.69 | 1 / 0 / 0 | $0.67 | $20.36 |
| kev-4b-ft-s19 | 1 / 0 / 0 | $27.62 | slopvac-judge-kev-4b-s19-20261003120548 | $27.62 | 1 / 0 / 0 | $0.97 | $28.59 |
| kev-9b-ft-s17 | 1 / 0 / 0 | $52.19 | slopvac-judge-kev-9b-s17-20261003133552 | $52.19 | 1 / 0 / 1 | $1.17 | $53.35 |
| kev-9b-ft-s18 | 1 / 3 / 0 | $33.01 | slopvac-judge-kev-9b-s18-20261003143308 | $33.01 | 1 / 0 / 0 | $1.38 | $34.38 |
| kev-9b-ft-s19 | 1 / 3 / 0 | $52.46 | slopvac-judge-kev-9b-s19-20261003143337 | $52.46 | 1 / 0 / 0 | $1.38 | $53.84 |

Campaign total: **$250.49 USD** (training $243.16, evaluation $7.33) over 15 training and 10 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | evaluation | Stopped | 1 | $0.00 | scheduler marker `capacity_rotation` |
| kev-9b-ft-s18 | training | Failed | 1 | $0.00 | scheduler marker `use2_role_trust` |
| kev-9b-ft-s18 | training | Failed | 2 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.4xlarge for training job usage' is … |
| kev-9b-ft-s19 | training | Failed | 1 | $0.00 | scheduler marker `use2_role_trust` |
| kev-9b-ft-s19 | training | Failed | 2 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.4xlarge for training job usage' is … |

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
| kev-0.8b-ft-s17 | 2074 | 0.762 | 0.751 | 0.848 | 0.165 | 0.510 | 0.062 | 0.163 | 0.499 | 0.047 | 0.706–0.798 | 0.034–0.102 | 0.027–0.086 | 0.652 | 0.850 | — | — | — | 17.584 | 67.356 |
| kev-0.8b-ft-s18 | 2074 | 0.770 | 0.759 | 0.851 | 0.163 | 0.514 | 0.064 | 0.161 | 0.500 | 0.047 | 0.709–0.811 | 0.039–0.109 | 0.027–0.094 | 0.665 | 0.853 | — | — | — | 17.495 | 67.355 |
| kev-0.8b-ft-s19 | 2074 | 0.777 | 0.768 | 0.851 | 0.161 | 0.515 | 0.065 | 0.158 | 0.494 | 0.040 | 0.728–0.812 | 0.044–0.101 | 0.022–0.076 | 0.690 | 0.846 | — | — | — | 17.471 | 67.711 |
| FT mean ± SD [range] | — | 0.769 ± 0.007 [0.762–0.777] | 0.759 ± 0.009 [0.751–0.768] | 0.850 ± 0.002 [0.848–0.851] | 0.163 ± 0.002 [0.161–0.165] | 0.513 ± 0.003 [0.510–0.515] | 0.064 ± 0.001 [0.062–0.065] | 0.161 ± 0.003 [0.158–0.163] | 0.498 ± 0.004 [0.494–0.500] | 0.045 ± 0.004 [0.040–0.047] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1597 | 0.741 | 0.743 | 0.809 | 0.365 | 0.582 | 0.059 | 0.360 | 0.567 | 0.042 | 0.698–0.784 | 0.033–0.112 | 0.029–0.084 | — | — | 0.001 | 0.920 | 0.079 | 17.584 | 67.356 |
| kev-0.8b-ft-s18 | 1597 | 0.741 | 0.744 | 0.821 | 0.354 | 0.558 | 0.040 | 0.352 | 0.556 | 0.027 | 0.694–0.788 | 0.022–0.086 | 0.020–0.070 | — | — | 0.003 | 0.906 | 0.092 | 17.495 | 67.355 |
| kev-0.8b-ft-s19 | 1597 | 0.737 | 0.741 | 0.810 | 0.365 | 0.571 | 0.044 | 0.362 | 0.565 | 0.029 | 0.690–0.786 | 0.025–0.093 | 0.025–0.070 | — | — | 0.004 | 0.927 | 0.080 | 17.471 | 67.711 |
| FT mean ± SD [range] | — | 0.740 ± 0.002 [0.737–0.741] | 0.743 ± 0.002 [0.741–0.744] | 0.813 ± 0.007 [0.809–0.821] | 0.361 ± 0.006 [0.354–0.365] | 0.570 ± 0.012 [0.558–0.582] | 0.048 ± 0.010 [0.040–0.059] | 0.358 ± 0.005 [0.352–0.362] | 0.563 ± 0.006 [0.556–0.567] | 0.033 ± 0.008 [0.027–0.042] | — | — | — | — | — | 0.003 ± 0.002 [0.001–0.004] | 0.918 ± 0.011 [0.906–0.927] | 0.083 ± 0.007 [0.079–0.092] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 2074 | 0.897 | 0.892 | 0.959 | 0.083 | 0.304 | 0.053 | 0.080 | 0.274 | 0.026 | 0.847–0.921 | 0.033–0.087 | 0.012–0.060 | 0.848 | 0.936 | — | — | — | 65.543 | 206.067 |
| kev-4b-ft-s18 | 2074 | 0.907 | 0.902 | 0.962 | 0.072 | 0.258 | 0.040 | 0.071 | 0.246 | 0.020 | 0.865–0.929 | 0.021–0.067 | 0.012–0.046 | 0.849 | 0.954 | — | — | — | 65.526 | 208.269 |
| kev-4b-ft-s19 | 2074 | 0.911 | 0.908 | 0.958 | 0.071 | 0.260 | 0.039 | 0.069 | 0.245 | 0.014 | 0.878–0.933 | 0.023–0.062 | 0.010–0.036 | 0.876 | 0.939 | — | — | — | 65.281 | 204.836 |
| FT mean ± SD [range] | — | 0.905 ± 0.007 [0.897–0.911] | 0.901 ± 0.008 [0.892–0.908] | 0.960 ± 0.002 [0.958–0.962] | 0.076 ± 0.007 [0.071–0.083] | 0.274 ± 0.026 [0.258–0.304] | 0.044 ± 0.008 [0.039–0.053] | 0.073 ± 0.006 [0.069–0.080] | 0.255 ± 0.017 [0.245–0.274] | 0.020 ± 0.006 [0.014–0.026] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 1597 | 0.775 | 0.780 | 0.872 | 0.354 | 0.619 | 0.131 | 0.319 | 0.522 | 0.045 | 0.729–0.828 | 0.085–0.185 | 0.026–0.096 | — | — | 0.002 | 0.944 | 0.049 | 65.543 | 206.067 |
| kev-4b-ft-s18 | 1597 | 0.796 | 0.800 | 0.892 | 0.320 | 0.540 | 0.115 | 0.292 | 0.478 | 0.050 | 0.751–0.844 | 0.074–0.163 | 0.029–0.089 | — | — | 0.003 | 0.956 | 0.053 | 65.526 | 208.269 |
| kev-4b-ft-s19 | 1597 | 0.792 | 0.797 | 0.888 | 0.325 | 0.558 | 0.126 | 0.295 | 0.479 | 0.046 | 0.742–0.846 | 0.081–0.177 | 0.025–0.093 | — | — | 0.000 | 0.957 | 0.045 | 65.281 | 204.836 |
| FT mean ± SD [range] | — | 0.788 ± 0.011 [0.775–0.796] | 0.792 ± 0.011 [0.780–0.800] | 0.884 ± 0.010 [0.872–0.892] | 0.333 ± 0.018 [0.320–0.354] | 0.572 ± 0.041 [0.540–0.619] | 0.124 ± 0.008 [0.115–0.131] | 0.302 ± 0.015 [0.292–0.319] | 0.493 ± 0.025 [0.478–0.522] | 0.047 ± 0.003 [0.045–0.050] | — | — | — | — | — | 0.001 ± 0.001 [0.000–0.003] | 0.952 ± 0.007 [0.944–0.957] | 0.049 ± 0.004 [0.045–0.053] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 2074 | 0.911 | 0.906 | 0.959 | 0.073 | 0.290 | 0.048 | 0.070 | 0.249 | 0.015 | 0.873–0.930 | 0.034–0.069 | 0.011–0.038 | 0.867 | 0.946 | — | — | — | 62.025 | 129.253 |
| kev-9b-ft-s18 | 2074 | 0.900 | 0.894 | 0.952 | 0.081 | 0.303 | 0.046 | 0.079 | 0.276 | 0.019 | 0.864–0.916 | 0.033–0.072 | 0.011–0.043 | 0.833 | 0.954 | — | — | — | 62.117 | 127.112 |
| kev-9b-ft-s19 | 2074 | 0.911 | 0.907 | 0.958 | 0.074 | 0.282 | 0.042 | 0.072 | 0.252 | 0.013 | 0.881–0.929 | 0.031–0.064 | 0.010–0.034 | 0.876 | 0.938 | — | — | — | 62.043 | 127.579 |
| FT mean ± SD [range] | — | 0.907 ± 0.006 [0.900–0.911] | 0.902 ± 0.008 [0.894–0.907] | 0.956 ± 0.004 [0.952–0.959] | 0.076 ± 0.005 [0.073–0.081] | 0.292 ± 0.011 [0.282–0.303] | 0.045 ± 0.003 [0.042–0.048] | 0.073 ± 0.005 [0.070–0.079] | 0.259 ± 0.015 [0.249–0.276] | 0.016 ± 0.003 [0.013–0.019] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 1597 | 0.801 | 0.806 | 0.908 | 0.309 | 0.513 | 0.109 | 0.284 | 0.452 | 0.049 | 0.754–0.851 | 0.068–0.157 | 0.025–0.094 | — | — | 0.003 | 0.964 | 0.040 | 62.025 | 129.253 |
| kev-9b-ft-s18 | 1597 | 0.808 | 0.813 | 0.910 | 0.285 | 0.463 | 0.088 | 0.270 | 0.435 | 0.052 | 0.764–0.859 | 0.045–0.136 | 0.028–0.095 | — | — | 0.001 | 0.969 | 0.050 | 62.117 | 127.112 |
| kev-9b-ft-s19 | 1597 | 0.807 | 0.812 | 0.920 | 0.296 | 0.492 | 0.112 | 0.268 | 0.431 | 0.049 | 0.759–0.860 | 0.068–0.159 | 0.029–0.091 | — | — | 0.002 | 0.959 | 0.043 | 62.043 | 127.579 |
| FT mean ± SD [range] | — | 0.805 ± 0.004 [0.801–0.808] | 0.810 ± 0.004 [0.806–0.813] | 0.913 ± 0.006 [0.908–0.920] | 0.297 ± 0.012 [0.285–0.309] | 0.489 ± 0.025 [0.463–0.513] | 0.103 ± 0.013 [0.088–0.112] | 0.274 ± 0.009 [0.268–0.284] | 0.440 ± 0.011 [0.431–0.452] | 0.050 ± 0.002 [0.049–0.052] | — | — | — | — | — | 0.002 ± 0.001 [0.001–0.003] | 0.964 ± 0.005 [0.959–0.969] | 0.044 ± 0.005 [0.040–0.050] | — | — |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 17.584 | 67.356 | 661 | $0.3672 | sv-eval-kev-08b-ft-s17-261003161715345786 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 17.495 | 67.355 | 662 | $0.3678 | sv-eval-kev-08b-ft-s18-261003163945971997 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.2xlarge | us-east-2 | 17.471 | 67.711 | 666 | $0.3700 | sv-eval-kev-08b-ft-s19-261003163959303594 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 65.543 | 206.067 | 1200 | $0.6667 | sv-eval-kev-4b-ft-s17-261003155236955862 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.2xlarge | us-east-2 | 65.526 | 208.269 | 1207 | $0.6706 | sv-eval-kev-4b-ft-s18-261003160822387548 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.4xlarge | us-east-1 | 65.281 | 204.836 | 1164 | $0.9700 | sv-eval-kev-4b-ft-s19-261003160841564809 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.2xlarge | us-east-2 | 62.025 | 129.253 | 1051 | $1.1678 | sv-eval-kev-9b-ft-s17-261003214228829649 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.4xlarge | us-west-2 | 62.117 | 127.112 | 991 | $1.3764 | sv-eval-kev-9b-ft-s18-261003191957660397 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.4xlarge | us-east-2 | 62.043 | 127.579 | 992 | $1.3778 | sv-eval-kev-9b-ft-s19-261003192800972029 |

Total billed evaluation cost for the reported arms: **$7.3343 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | noul | granularity | document | 943 | 0.759 | 0.753 | 0.056 | 0.673 | 0.834 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 754 | 0.769 | 0.762 | 0.065 | 0.690 | 0.833 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 377 | 0.753 | 0.711 | 0.098 | 0.507 | 0.916 |
| kev-0.8b-ft-s17 | noul | provenance | generated | 201 | 0.856 | 0.574 | 0.078 | 0.200 | 0.949 |
| kev-0.8b-ft-s17 | noul | provenance | human | 1873 | 0.752 | 0.748 | 0.063 | 0.665 | 0.832 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2074 | 0.762 | 0.751 | 0.062 | 0.652 | 0.850 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1314 | 0.817 | 0.784 | 0.040 | 0.695 | 0.874 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 760 | 0.666 | 0.690 | 0.109 | 0.617 | 0.763 |
| kev-0.8b-ft-s17 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 1873 | 0.752 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 735 | 0.752 | 0.753 | 0.045 | 0.662 | 0.844 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 547 | 0.744 | 0.825 | 0.068 | 0.675 | 0.800 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 315 | 0.708 | 0.479 | 0.126 | 0.693 | 0.743 |
| kev-0.8b-ft-s17 | choice | provenance | generated | 217 | 0.645 | 0.668 | 0.204 | 0.508 | 0.828 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1380 | 0.756 | 0.671 | 0.043 | 0.703 | 0.811 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.741 | 0.662 | 0.059 | 0.674 | 0.813 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 907 | 0.762 | 0.660 | 0.053 | 0.669 | 0.810 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 690 | 0.713 | 0.749 | 0.071 | 0.676 | 0.822 |
| kev-0.8b-ft-s17 | choice | source accuracy | generated | 217 | 0.645 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1380 | 0.756 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 943 | 0.766 | 0.760 | 0.063 | 0.680 | 0.840 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 754 | 0.792 | 0.786 | 0.062 | 0.735 | 0.837 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 377 | 0.735 | 0.689 | 0.121 | 0.467 | 0.912 |
| kev-0.8b-ft-s18 | noul | provenance | generated | 201 | 0.861 | 0.577 | 0.074 | 0.200 | 0.955 |
| kev-0.8b-ft-s18 | noul | provenance | human | 1873 | 0.760 | 0.757 | 0.065 | 0.678 | 0.835 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2074 | 0.770 | 0.759 | 0.064 | 0.665 | 0.853 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1314 | 0.821 | 0.794 | 0.046 | 0.719 | 0.869 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 760 | 0.680 | 0.710 | 0.121 | 0.621 | 0.798 |
| kev-0.8b-ft-s18 | noul | source accuracy | generated | 201 | 0.861 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 1873 | 0.760 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 735 | 0.755 | 0.756 | 0.038 | 0.681 | 0.830 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 547 | 0.737 | 0.817 | 0.049 | 0.614 | 0.837 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 315 | 0.717 | 0.499 | 0.098 | 0.654 | 0.844 |
| kev-0.8b-ft-s18 | choice | provenance | generated | 217 | 0.618 | 0.642 | 0.161 | 0.468 | 0.817 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1380 | 0.761 | 0.675 | 0.022 | 0.687 | 0.837 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.741 | 0.663 | 0.040 | 0.654 | 0.835 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 907 | 0.772 | 0.661 | 0.036 | 0.649 | 0.835 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 690 | 0.701 | 0.745 | 0.063 | 0.657 | 0.833 |
| kev-0.8b-ft-s18 | choice | source accuracy | generated | 217 | 0.618 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1380 | 0.761 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 943 | 0.777 | 0.773 | 0.061 | 0.719 | 0.828 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 754 | 0.794 | 0.790 | 0.058 | 0.750 | 0.830 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 377 | 0.740 | 0.695 | 0.123 | 0.473 | 0.916 |
| kev-0.8b-ft-s19 | noul | provenance | generated | 201 | 0.856 | 0.557 | 0.084 | 0.160 | 0.955 |
| kev-0.8b-ft-s19 | noul | provenance | human | 1873 | 0.768 | 0.766 | 0.065 | 0.705 | 0.827 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2074 | 0.777 | 0.768 | 0.065 | 0.690 | 0.846 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1314 | 0.820 | 0.789 | 0.053 | 0.702 | 0.875 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 760 | 0.701 | 0.712 | 0.106 | 0.680 | 0.743 |
| kev-0.8b-ft-s19 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 1873 | 0.768 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 735 | 0.754 | 0.754 | 0.044 | 0.649 | 0.860 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 547 | 0.755 | 0.828 | 0.065 | 0.618 | 0.867 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 315 | 0.667 | 0.463 | 0.121 | 0.610 | 0.780 |
| kev-0.8b-ft-s19 | choice | provenance | generated | 217 | 0.618 | 0.645 | 0.178 | 0.452 | 0.839 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1380 | 0.756 | 0.672 | 0.027 | 0.661 | 0.853 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.737 | 0.660 | 0.044 | 0.630 | 0.851 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 907 | 0.768 | 0.655 | 0.047 | 0.623 | 0.843 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 690 | 0.696 | 0.757 | 0.071 | 0.634 | 0.879 |
| kev-0.8b-ft-s19 | choice | source accuracy | generated | 217 | 0.618 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1380 | 0.756 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 943 | 0.890 | 0.886 | 0.062 | 0.840 | 0.933 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 754 | 0.899 | 0.897 | 0.054 | 0.875 | 0.919 |
| kev-4b-ft-s17 | noul | granularity | sentence | 377 | 0.910 | 0.893 | 0.053 | 0.813 | 0.974 |
| kev-4b-ft-s17 | noul | provenance | generated | 201 | 0.846 | 0.586 | 0.116 | 0.240 | 0.932 |
| kev-4b-ft-s17 | noul | provenance | human | 1873 | 0.902 | 0.901 | 0.047 | 0.865 | 0.936 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2074 | 0.897 | 0.892 | 0.053 | 0.848 | 0.936 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1314 | 0.901 | 0.879 | 0.054 | 0.817 | 0.940 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 760 | 0.889 | 0.897 | 0.065 | 0.874 | 0.921 |
| kev-4b-ft-s17 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-4b-ft-s17 | noul | source accuracy | human | 1873 | 0.902 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 735 | 0.785 | 0.786 | 0.130 | 0.632 | 0.940 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 547 | 0.781 | 0.513 | 0.132 | 0.638 | 0.900 |
| kev-4b-ft-s17 | choice | granularity | sentence | 315 | 0.743 | 0.518 | 0.156 | 0.673 | 0.881 |
| kev-4b-ft-s17 | choice | provenance | generated | 217 | 0.590 | 0.616 | 0.308 | 0.435 | 0.796 |
| kev-4b-ft-s17 | choice | provenance | human | 1380 | 0.804 | 0.538 | 0.108 | 0.681 | 0.932 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.775 | 0.520 | 0.131 | 0.644 | 0.916 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 907 | 0.826 | 0.520 | 0.096 | 0.633 | 0.927 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 690 | 0.709 | 0.765 | 0.187 | 0.651 | 0.879 |
| kev-4b-ft-s17 | choice | source accuracy | generated | 217 | 0.590 | — | — | — | — |
| kev-4b-ft-s17 | choice | source accuracy | human | 1380 | 0.804 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 943 | 0.911 | 0.908 | 0.044 | 0.865 | 0.951 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 754 | 0.908 | 0.904 | 0.042 | 0.863 | 0.945 |
| kev-4b-ft-s18 | noul | granularity | sentence | 377 | 0.897 | 0.876 | 0.048 | 0.773 | 0.978 |
| kev-4b-ft-s18 | noul | provenance | generated | 201 | 0.846 | 0.552 | 0.097 | 0.160 | 0.943 |
| kev-4b-ft-s18 | noul | provenance | human | 1873 | 0.914 | 0.912 | 0.034 | 0.869 | 0.956 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2074 | 0.907 | 0.902 | 0.040 | 0.849 | 0.954 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1314 | 0.909 | 0.884 | 0.041 | 0.815 | 0.952 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 760 | 0.905 | 0.919 | 0.042 | 0.878 | 0.960 |
| kev-4b-ft-s18 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-4b-ft-s18 | noul | source accuracy | human | 1873 | 0.914 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 735 | 0.804 | 0.805 | 0.114 | 0.686 | 0.923 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 547 | 0.808 | 0.864 | 0.108 | 0.671 | 0.920 |
| kev-4b-ft-s18 | choice | granularity | sentence | 315 | 0.756 | 0.529 | 0.146 | 0.678 | 0.908 |
| kev-4b-ft-s18 | choice | provenance | generated | 217 | 0.590 | 0.624 | 0.284 | 0.387 | 0.860 |
| kev-4b-ft-s18 | choice | provenance | human | 1380 | 0.828 | 0.720 | 0.093 | 0.732 | 0.928 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.796 | 0.700 | 0.115 | 0.680 | 0.920 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 907 | 0.825 | 0.685 | 0.102 | 0.630 | 0.925 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 690 | 0.758 | 0.806 | 0.142 | 0.709 | 0.902 |
| kev-4b-ft-s18 | choice | source accuracy | generated | 217 | 0.590 | — | — | — | — |
| kev-4b-ft-s18 | choice | source accuracy | human | 1380 | 0.828 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 943 | 0.902 | 0.900 | 0.053 | 0.872 | 0.929 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 754 | 0.915 | 0.913 | 0.033 | 0.890 | 0.935 |
| kev-4b-ft-s19 | noul | granularity | sentence | 377 | 0.926 | 0.915 | 0.032 | 0.860 | 0.969 |
| kev-4b-ft-s19 | noul | provenance | generated | 201 | 0.851 | 0.572 | 0.103 | 0.200 | 0.943 |
| kev-4b-ft-s19 | noul | provenance | human | 1873 | 0.918 | 0.917 | 0.034 | 0.895 | 0.938 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2074 | 0.911 | 0.908 | 0.039 | 0.876 | 0.939 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1314 | 0.908 | 0.887 | 0.042 | 0.829 | 0.944 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 760 | 0.917 | 0.918 | 0.037 | 0.915 | 0.921 |
| kev-4b-ft-s19 | noul | source accuracy | generated | 201 | 0.851 | — | — | — | — |
| kev-4b-ft-s19 | noul | source accuracy | human | 1873 | 0.918 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 735 | 0.804 | 0.805 | 0.117 | 0.689 | 0.921 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 547 | 0.799 | 0.525 | 0.128 | 0.663 | 0.913 |
| kev-4b-ft-s19 | choice | granularity | sentence | 315 | 0.752 | 0.524 | 0.160 | 0.683 | 0.890 |
| kev-4b-ft-s19 | choice | provenance | generated | 217 | 0.608 | 0.637 | 0.299 | 0.435 | 0.839 |
| kev-4b-ft-s19 | choice | provenance | human | 1380 | 0.821 | 0.549 | 0.100 | 0.723 | 0.924 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.792 | 0.531 | 0.126 | 0.680 | 0.913 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 907 | 0.821 | 0.518 | 0.101 | 0.633 | 0.920 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 690 | 0.754 | 0.799 | 0.163 | 0.707 | 0.891 |
| kev-4b-ft-s19 | choice | source accuracy | generated | 217 | 0.608 | — | — | — | — |
| kev-4b-ft-s19 | choice | source accuracy | human | 1380 | 0.821 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 943 | 0.909 | 0.906 | 0.052 | 0.872 | 0.941 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 754 | 0.907 | 0.903 | 0.049 | 0.863 | 0.943 |
| kev-9b-ft-s17 | noul | granularity | sentence | 377 | 0.923 | 0.912 | 0.042 | 0.860 | 0.965 |
| kev-9b-ft-s17 | noul | provenance | generated | 201 | 0.846 | 0.569 | 0.118 | 0.200 | 0.938 |
| kev-9b-ft-s17 | noul | provenance | human | 1873 | 0.918 | 0.916 | 0.040 | 0.885 | 0.948 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2074 | 0.911 | 0.906 | 0.048 | 0.867 | 0.946 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1314 | 0.903 | 0.878 | 0.056 | 0.810 | 0.947 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 760 | 0.924 | 0.929 | 0.036 | 0.913 | 0.945 |
| kev-9b-ft-s17 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-9b-ft-s17 | noul | source accuracy | human | 1873 | 0.918 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 735 | 0.815 | 0.816 | 0.100 | 0.689 | 0.942 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 547 | 0.815 | 0.534 | 0.093 | 0.642 | 0.960 |
| kev-9b-ft-s17 | choice | granularity | sentence | 315 | 0.743 | 0.524 | 0.166 | 0.654 | 0.917 |
| kev-9b-ft-s17 | choice | provenance | generated | 217 | 0.590 | 0.629 | 0.301 | 0.355 | 0.903 |
| kev-9b-ft-s17 | choice | provenance | human | 1380 | 0.834 | 0.558 | 0.083 | 0.722 | 0.952 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.801 | 0.537 | 0.109 | 0.666 | 0.946 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 907 | 0.831 | 0.519 | 0.089 | 0.610 | 0.947 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 690 | 0.761 | 0.821 | 0.145 | 0.700 | 0.943 |
| kev-9b-ft-s17 | choice | source accuracy | generated | 217 | 0.590 | — | — | — | — |
| kev-9b-ft-s17 | choice | source accuracy | human | 1380 | 0.834 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 943 | 0.911 | 0.908 | 0.049 | 0.865 | 0.951 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 754 | 0.889 | 0.881 | 0.052 | 0.812 | 0.950 |
| kev-9b-ft-s18 | noul | granularity | sentence | 377 | 0.897 | 0.878 | 0.061 | 0.787 | 0.969 |
| kev-9b-ft-s18 | noul | provenance | generated | 201 | 0.856 | 0.592 | 0.108 | 0.240 | 0.943 |
| kev-9b-ft-s18 | noul | provenance | human | 1873 | 0.905 | 0.903 | 0.041 | 0.850 | 0.956 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2074 | 0.900 | 0.894 | 0.046 | 0.833 | 0.954 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1314 | 0.909 | 0.878 | 0.048 | 0.796 | 0.961 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 760 | 0.886 | 0.896 | 0.049 | 0.864 | 0.929 |
| kev-9b-ft-s18 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-9b-ft-s18 | noul | source accuracy | human | 1873 | 0.905 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 735 | 0.824 | 0.825 | 0.073 | 0.714 | 0.937 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 547 | 0.826 | 0.542 | 0.080 | 0.667 | 0.960 |
| kev-9b-ft-s18 | choice | granularity | sentence | 315 | 0.740 | 0.526 | 0.144 | 0.634 | 0.945 |
| kev-9b-ft-s18 | choice | provenance | generated | 217 | 0.585 | 0.626 | 0.274 | 0.339 | 0.914 |
| kev-9b-ft-s18 | choice | provenance | human | 1380 | 0.843 | 0.564 | 0.059 | 0.740 | 0.952 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.808 | 0.542 | 0.088 | 0.680 | 0.947 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 907 | 0.840 | 0.528 | 0.063 | 0.636 | 0.947 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 690 | 0.767 | 0.827 | 0.122 | 0.705 | 0.948 |
| kev-9b-ft-s18 | choice | source accuracy | generated | 217 | 0.585 | — | — | — | — |
| kev-9b-ft-s18 | choice | source accuracy | human | 1380 | 0.843 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 943 | 0.914 | 0.913 | 0.039 | 0.892 | 0.933 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 754 | 0.901 | 0.897 | 0.055 | 0.869 | 0.926 |
| kev-9b-ft-s19 | noul | granularity | sentence | 377 | 0.923 | 0.910 | 0.066 | 0.847 | 0.974 |
| kev-9b-ft-s19 | noul | provenance | generated | 201 | 0.841 | 0.566 | 0.146 | 0.200 | 0.932 |
| kev-9b-ft-s19 | noul | provenance | human | 1873 | 0.918 | 0.917 | 0.034 | 0.895 | 0.939 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2074 | 0.911 | 0.907 | 0.042 | 0.876 | 0.938 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1314 | 0.901 | 0.881 | 0.049 | 0.825 | 0.937 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 760 | 0.928 | 0.932 | 0.036 | 0.919 | 0.945 |
| kev-9b-ft-s19 | noul | source accuracy | generated | 201 | 0.841 | — | — | — | — |
| kev-9b-ft-s19 | noul | source accuracy | human | 1873 | 0.918 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 735 | 0.822 | 0.823 | 0.096 | 0.700 | 0.945 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 547 | 0.815 | 0.536 | 0.113 | 0.667 | 0.940 |
| kev-9b-ft-s19 | choice | granularity | sentence | 315 | 0.759 | 0.536 | 0.150 | 0.663 | 0.945 |
| kev-9b-ft-s19 | choice | provenance | generated | 217 | 0.585 | 0.622 | 0.307 | 0.363 | 0.882 |
| kev-9b-ft-s19 | choice | provenance | human | 1380 | 0.842 | 0.563 | 0.081 | 0.737 | 0.952 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.807 | 0.541 | 0.112 | 0.681 | 0.943 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 907 | 0.837 | 0.525 | 0.093 | 0.630 | 0.945 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 690 | 0.768 | 0.824 | 0.138 | 0.711 | 0.937 |
| kev-9b-ft-s19 | choice | source accuracy | generated | 217 | 0.585 | — | — | — | — |
| kev-9b-ft-s19 | choice | source accuracy | human | 1380 | 0.842 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1095 | 0.530 | 33 | 0.751 | 0.746 | 0.728 |
| kev-0.8b-ft-s18 | 1095 | 0.427 | 33 | 0.759 | 0.769 | 0.757 |
| kev-0.8b-ft-s19 | 1095 | 0.461 | 33 | 0.768 | 0.771 | 0.762 |
| kev-4b-ft-s17 | 1095 | 0.291 | 33 | 0.892 | 0.896 | 0.893 |
| kev-4b-ft-s18 | 1095 | 0.300 | 33 | 0.902 | 0.908 | 0.899 |
| kev-4b-ft-s19 | 1095 | 0.395 | 33 | 0.908 | 0.912 | 0.908 |
| kev-9b-ft-s17 | 1095 | 0.294 | 33 | 0.906 | 0.912 | 0.902 |
| kev-9b-ft-s18 | 1095 | 0.580 | 33 | 0.894 | 0.889 | 0.884 |
| kev-9b-ft-s19 | 1095 | 0.451 | 33 | 0.907 | 0.908 | 0.891 |

## Interpretation and caveats

- Test label origins: construction (3092), human-adjudication (258), llm-review-consensus (321). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice insufficient-context=2, no-defect=821, real-defect=774; yes/no False=1151, True=923. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.30 finding-confirmation, κ=0.30 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
