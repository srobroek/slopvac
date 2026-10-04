# Corpus evaluation report: `corpus-v5b-llm-only`

## Status

- v5b: lint rules at main ca941af16a; labels human-adjudication > llm-review-consensus > teacher-panel; redesigned semantic items. The human-adjudication test slice is the rows four LLM reviewers could not settle, labelled once by one person with the earlier (confusing) review UI; read it as preliminary.

## Dataset and coverage

- Campaign: `corpus-20261003-s17-v5b/llm-only`. Label-source ablation on the v5b export: the full variant's train split without the human answers (export --drop-train-origin human-adjudication; those rows are unlabelled in train), so the settled LLM-review consensus, teacher-panel labels and constructions remain. Test and calibration are byte-identical to v5b full. Base arms are not repeated: v5b-full evaluates them on the same splits. runtime_scale is 13,058 train rows / 5,420.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 9 of 9 required (`kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 14 of 32 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1720 examples; SHA-256 `8534bee7b935ae80b47d35e1e96a4a288ab3ba86c6bfe851ff01e8dcf3300b1b`.
- Test: 3671 examples; SHA-256 `a77f6f64b85b81a13330df57b8cd3973edd2b295ae30efdf4ddc12a4a8bb0b31`.
- Test composition: label origins `construction`=3092, `human-adjudication`=258, `llm-review-consensus`=321; choice labels insufficient-context=2, no-defect=821, real-defect=774; yes/no labels False=1151, True=923.

## Headline by role

Each arm's numbers come from `results/corpus-v5b-llm-only/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1597 (real-defect=774, no-defect=821).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.748 | 0.697–0.790 | 0.818 | 0.678 | 0.066 | 0.051 | NVIDIA A10G | 17.551 | $0.3672 |
| kev-0.8b-ft-s18 | 0.750 | 0.701–0.794 | 0.858 | 0.643 | 0.075 | 0.048 | NVIDIA A10G | 17.414 | $0.3672 |
| kev-0.8b-ft-s19 | 0.740 | 0.692–0.784 | 0.831 | 0.649 | 0.070 | 0.036 | NVIDIA A10G | 17.520 | $0.3728 |
| kev-0.8b FT mean ± SD [range] | 0.746 ± 0.006 [0.740–0.750] | — | 0.835 ± 0.020 [0.818–0.858] | 0.657 ± 0.019 [0.643–0.678] | 0.070 ± 0.004 [0.066–0.075] | 0.045 ± 0.008 [0.036–0.051] | — | — | — |
| kev-4b-ft-s17 | 0.790 | 0.740–0.839 | 0.912 | 0.667 | 0.135 | 0.043 | NVIDIA A10G | 65.451 | $0.6667 |
| kev-4b-ft-s18 | 0.805 | 0.752–0.851 | 0.919 | 0.692 | 0.097 | 0.031 | NVIDIA A10G | 65.392 | $0.6717 |
| kev-4b-ft-s19 | 0.801 | 0.751–0.850 | 0.924 | 0.678 | 0.100 | 0.060 | NVIDIA A10G | 65.326 | $0.6717 |
| kev-4b FT mean ± SD [range] | 0.799 ± 0.008 [0.790–0.805] | — | 0.918 ± 0.006 [0.912–0.924] | 0.679 ± 0.012 [0.667–0.692] | 0.111 ± 0.021 [0.097–0.135] | 0.045 ± 0.015 [0.031–0.060] | — | — | — |
| kev-9b-ft-s17 | 0.812 | 0.761–0.860 | 0.937 | 0.687 | 0.104 | 0.043 | NVIDIA L40S | 62.320 | $1.8978 |
| kev-9b-ft-s18 | 0.810 | 0.765–0.855 | 0.932 | 0.689 | 0.080 | 0.050 | NVIDIA L40S | 62.130 | $1.1844 |
| kev-9b-ft-s19 | 0.816 | 0.764–0.861 | 0.947 | 0.686 | 0.110 | 0.052 | NVIDIA L40S | 62.441 | $1.1856 |
| kev-9b FT mean ± SD [range] | 0.813 ± 0.003 [0.810–0.816] | — | 0.938 ± 0.008 [0.932–0.947] | 0.687 ± 0.002 [0.686–0.689] | 0.098 ± 0.016 [0.080–0.110] | 0.049 ± 0.005 [0.043–0.052] | — | — | — |

- Best single arm: `kev-9b-ft-s19` (balanced accuracy 0.816).
- Best fine-tuned family by seed mean: `kev-9b` (0.813 ± 0.003 [0.810–0.816]).

### semantic-detection (`noul`)

Test items: 2074 (True=923, False=1151).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.792 | 0.748–0.836 | 0.726 | 0.858 | 0.068 | 0.043 | NVIDIA A10G | 17.551 | $0.3672 |
| kev-0.8b-ft-s18 | 0.784 | 0.740–0.828 | 0.730 | 0.838 | 0.059 | 0.039 | NVIDIA A10G | 17.414 | $0.3672 |
| kev-0.8b-ft-s19 | 0.795 | 0.754–0.837 | 0.743 | 0.847 | 0.071 | 0.035 | NVIDIA A10G | 17.520 | $0.3728 |
| kev-0.8b FT mean ± SD [range] | 0.790 ± 0.006 [0.784–0.795] | — | 0.733 ± 0.009 [0.726–0.743] | 0.848 ± 0.010 [0.838–0.858] | 0.066 ± 0.006 [0.059–0.071] | 0.039 ± 0.004 [0.035–0.043] | — | — | — |
| kev-4b-ft-s17 | 0.901 | 0.864–0.927 | 0.861 | 0.940 | 0.039 | 0.024 | NVIDIA A10G | 65.451 | $0.6667 |
| kev-4b-ft-s18 | 0.907 | 0.871–0.932 | 0.862 | 0.951 | 0.033 | 0.023 | NVIDIA A10G | 65.392 | $0.6717 |
| kev-4b-ft-s19 | 0.902 | 0.868–0.929 | 0.865 | 0.940 | 0.035 | 0.028 | NVIDIA A10G | 65.326 | $0.6717 |
| kev-4b FT mean ± SD [range] | 0.903 ± 0.003 [0.901–0.907] | — | 0.863 ± 0.002 [0.861–0.865] | 0.944 ± 0.007 [0.940–0.951] | 0.036 ± 0.003 [0.033–0.039] | 0.025 ± 0.003 [0.023–0.028] | — | — | — |
| kev-9b-ft-s17 | 0.908 | 0.875–0.934 | 0.860 | 0.956 | 0.044 | 0.022 | NVIDIA L40S | 62.320 | $1.8978 |
| kev-9b-ft-s18 | 0.905 | 0.880–0.924 | 0.855 | 0.955 | 0.043 | 0.025 | NVIDIA L40S | 62.130 | $1.1844 |
| kev-9b-ft-s19 | 0.898 | 0.867–0.922 | 0.856 | 0.939 | 0.048 | 0.030 | NVIDIA L40S | 62.441 | $1.1856 |
| kev-9b FT mean ± SD [range] | 0.903 ± 0.005 [0.898–0.908] | — | 0.857 ± 0.003 [0.855–0.860] | 0.950 ± 0.009 [0.939–0.956] | 0.045 ± 0.003 [0.043–0.048] | 0.026 ± 0.004 [0.022–0.030] | — | — | — |

- Best single arm: `kev-9b-ft-s17` (balanced accuracy 0.908).
- Best fine-tuned family by seed mean: `kev-9b` (0.903 ± 0.005 [0.898–0.908]).

## Balanced accuracy by test label origin

Computed by this generator from each arm's forward-order test predictions (`results/corpus-v5b-llm-only/<arm>/results/predictions/<arm>.jsonl`) joined by item id to the arm's hash-checked test split (`<arm>/data/test.jsonl`), which supplies `label` and `label_origin`. Balanced accuracy is the headline's (`test_raw`): the mean recall of real-defect and no-defect for finding confirmation, where insufficient-context items count in n only, and of True and False for semantic detection. The *All* column reproduces each arm's headline; the generator refuses to render when it does not. A slice that holds one class reduces to that class's recall, and small slices are noisy. Fine-tune family rows give the seed mean ± sample SD over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items by origin: `human-adjudication` 173 (real-defect=96, no-defect=75, insufficient-context=2); `llm-review-consensus` 114 (real-defect=23, no-defect=91); `construction` 1310 (real-defect=655, no-defect=655).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.748 | 0.511 | 0.770 | 0.773 |
| kev-0.8b-ft-s18 | 0.750 | 0.471 | 0.814 | 0.776 |
| kev-0.8b-ft-s19 | 0.740 | 0.488 | 0.781 | 0.766 |
| kev-0.8b FT mean ± SD | 0.746 ± 0.006 | 0.490 ± 0.020 | 0.788 ± 0.023 | 0.772 ± 0.005 |
| kev-4b-ft-s17 | 0.790 | 0.508 | 0.677 | 0.828 |
| kev-4b-ft-s18 | 0.805 | 0.489 | 0.770 | 0.846 |
| kev-4b-ft-s19 | 0.801 | 0.500 | 0.720 | 0.846 |
| kev-4b FT mean ± SD | 0.799 ± 0.008 | 0.499 ± 0.009 | 0.723 ± 0.046 | 0.840 ± 0.010 |
| kev-9b-ft-s17 | 0.812 | 0.457 | 0.775 | 0.861 |
| kev-9b-ft-s18 | 0.810 | 0.493 | 0.764 | 0.856 |
| kev-9b-ft-s19 | 0.816 | 0.477 | 0.769 | 0.866 |
| kev-9b FT mean ± SD | 0.813 ± 0.003 | 0.476 ± 0.018 | 0.769 ± 0.005 | 0.861 ± 0.005 |

### semantic-detection (`noul`)

Test items by origin: `human-adjudication` 85 (False=57, True=28); `llm-review-consensus` 207 (False=203, True=4); `construction` 1782 (False=891, True=891).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 0.792 | 0.456 | 0.865 | 0.788 |
| kev-0.8b-ft-s18 | 0.784 | 0.457 | 0.990 | 0.777 |
| kev-0.8b-ft-s19 | 0.795 | 0.439 | 0.990 | 0.791 |
| kev-0.8b FT mean ± SD | 0.790 ± 0.006 | 0.451 ± 0.010 | 0.948 ± 0.072 | 0.785 ± 0.007 |
| kev-4b-ft-s17 | 0.901 | 0.474 | 0.865 | 0.911 |
| kev-4b-ft-s18 | 0.907 | 0.421 | 0.873 | 0.920 |
| kev-4b-ft-s19 | 0.902 | 0.413 | 0.873 | 0.915 |
| kev-4b FT mean ± SD | 0.903 ± 0.003 | 0.436 ± 0.033 | 0.870 ± 0.004 | 0.915 ± 0.005 |
| kev-9b-ft-s17 | 0.908 | 0.457 | 0.873 | 0.920 |
| kev-9b-ft-s18 | 0.905 | 0.439 | 0.998 | 0.916 |
| kev-9b-ft-s19 | 0.898 | 0.421 | 0.993 | 0.909 |
| kev-9b FT mean ± SD | 0.903 ± 0.005 | 0.439 ± 0.018 | 0.954 ± 0.071 | 0.915 ± 0.005 |

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | corpus-v5b-full | 0.238 | 0.746 | +0.508 | 3/3 | +0.700 | +0.316 | -0.122 | -0.050 |
| kev-4b | corpus-v5b-full | 0.308 | 0.799 | +0.491 | 3/3 | +0.431 | +0.550 | -0.003 | -0.005 |
| kev-9b | corpus-v5b-full | 0.503 | 0.813 | +0.310 | 3/3 | +0.145 | +0.474 | -0.004 | -0.035 |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | corpus-v5b-full | 0.502 | 0.790 | +0.288 | 3/3 | +0.709 | -0.132 | -0.101 | +0.019 |
| kev-4b | corpus-v5b-full | 0.545 | 0.903 | +0.358 | 3/3 | +0.709 | +0.007 | -0.068 | -0.030 |
| kev-9b | corpus-v5b-full | 0.679 | 0.903 | +0.224 | 3/3 | +0.352 | +0.096 | +0.000 | -0.023 |

## Comparison with `corpus-v5b-full`

Both campaigns score the same test and calibration export (hashes verified). Δ is `corpus-v5b-llm-only` minus `corpus-v5b-full` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.

### finding-confirmation (`choice`)

| Family | corpus-v5b-llm-only bal. acc. | corpus-v5b-full bal. acc. | Δ bal. acc. | Seeds better | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.746 ± 0.006 [0.740–0.750] | 0.745 ± 0.011 [0.738–0.757] | +0.001 | 2/3 | +0.025 | -0.023 | +0.019 | +0.016 |
| kev-4b | 0.799 ± 0.008 [0.790–0.805] | 0.798 ± 0.003 [0.795–0.800] | +0.001 | 2/3 | +0.014 | -0.012 | +0.008 | -0.006 |
| kev-9b | 0.813 ± 0.003 [0.810–0.816] | 0.815 ± 0.009 [0.806–0.824] | -0.002 | 2/3 | +0.000 | -0.003 | +0.005 | -0.001 |

### semantic-detection (`noul`)

| Family | corpus-v5b-llm-only bal. acc. | corpus-v5b-full bal. acc. | Δ bal. acc. | Seeds better | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.790 ± 0.006 [0.784–0.795] | 0.775 ± 0.005 [0.769–0.779] | +0.016 | 3/3 | +0.036 | -0.005 | -0.000 | -0.006 |
| kev-4b | 0.903 ± 0.003 [0.901–0.907] | 0.903 ± 0.003 [0.900–0.905] | -0.000 | 2/3 | -0.001 | +0.001 | +0.002 | +0.000 |
| kev-9b | 0.903 ± 0.005 [0.898–0.908] | 0.899 ± 0.006 [0.894–0.905] | +0.005 | 3/3 | +0.004 | +0.005 | -0.005 | +0.004 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1 / 0 / 0 | $11.48 | slopvac-judge-kev-08b-s17-20261003114732 | $11.48 | 1 / 0 / 0 | $0.37 | $11.85 |
| kev-0.8b-ft-s18 | 1 / 0 / 0 | $6.55 | slopvac-judge-kev-08b-s18-20261003114742 | $6.55 | 1 / 0 / 0 | $0.37 | $6.92 |
| kev-0.8b-ft-s19 | 1 / 0 / 0 | $6.49 | slopvac-judge-kev-08b-s19-20261003123728 | $6.49 | 1 / 0 / 0 | $0.37 | $6.86 |
| kev-4b-ft-s17 | 1 / 0 / 0 | $15.38 | slopvac-judge-kev-4b-s17-20261003124209 | $15.38 | 1 / 0 / 0 | $0.67 | $16.04 |
| kev-4b-ft-s18 | 1 / 1 / 0 | $15.61 | slopvac-judge-kev-4b-s18-20261003143358 | $15.61 | 1 / 0 / 0 | $0.67 | $16.28 |
| kev-4b-ft-s19 | 1 / 3 / 1 | $15.48 | slopvac-judge-kev-4b-s19-20261003174314 | $15.48 | 1 / 0 / 0 | $0.67 | $16.15 |
| kev-9b-ft-s17 | 1 / 3 / 0 | $76.02 | slopvac-judge-kev-9b-s17-20261003143456 | $76.02 | 1 / 0 / 0 | $1.90 | $77.92 |
| kev-9b-ft-s18 | 1 / 3 / 0 | $76.50 | slopvac-judge-kev-9b-s18-20261003143527 | $76.50 | 1 / 0 / 0 | $1.18 | $77.69 |
| kev-9b-ft-s19 | 1 / 3 / 0 | $16.71 | slopvac-judge-kev-9b-s19-20261003143556 | $16.71 | 1 / 0 / 0 | $1.19 | $17.89 |

Campaign total: **$247.60 USD** (training $240.22, evaluation $7.39) over 23 training and 9 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s18 | training | Failed | 1 | $0.00 | scheduler marker `use2_role_trust` |
| kev-4b-ft-s19 | training | Failed | 1 | $0.00 | scheduler marker `use2_role_trust` |
| kev-4b-ft-s19 | training | Failed | 2 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.4xlarge for training job usage' is … |
| kev-4b-ft-s19 | training | Stopped | 1 | $0.00 | scheduler marker `capacity_rotation` |
| kev-9b-ft-s17 | training | Failed | 1 | $0.00 | scheduler marker `use2_role_trust` |
| kev-9b-ft-s17 | training | Failed | 2 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.4xlarge for training job usage' is … |
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
| kev-0.8b-ft-s17 | 2074 | 0.799 | 0.792 | 0.872 | 0.149 | 0.490 | 0.068 | 0.147 | 0.470 | 0.043 | 0.748–0.836 | 0.042–0.105 | 0.028–0.082 | 0.726 | 0.858 | — | — | — | 17.551 | 67.261 |
| kev-0.8b-ft-s18 | 2074 | 0.790 | 0.784 | 0.868 | 0.149 | 0.477 | 0.059 | 0.147 | 0.463 | 0.039 | 0.740–0.828 | 0.031–0.096 | 0.023–0.076 | 0.730 | 0.838 | — | — | — | 17.414 | 67.183 |
| kev-0.8b-ft-s19 | 2074 | 0.801 | 0.795 | 0.869 | 0.150 | 0.505 | 0.071 | 0.146 | 0.465 | 0.035 | 0.754–0.837 | 0.048–0.106 | 0.023–0.068 | 0.743 | 0.847 | — | — | — | 17.520 | 67.895 |
| FT mean ± SD [range] | — | 0.797 ± 0.006 [0.790–0.801] | 0.790 ± 0.006 [0.784–0.795] | 0.870 ± 0.002 [0.868–0.872] | 0.150 ± 0.001 [0.149–0.150] | 0.491 ± 0.014 [0.477–0.505] | 0.066 ± 0.006 [0.059–0.071] | 0.147 ± 0.001 [0.146–0.147] | 0.466 ± 0.003 [0.463–0.470] | 0.039 ± 0.004 [0.035–0.043] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1597 | 0.746 | 0.748 | 0.816 | 0.357 | 0.570 | 0.066 | 0.352 | 0.555 | 0.051 | 0.697–0.790 | 0.040–0.115 | 0.035–0.087 | — | — | 0.001 | 0.930 | 0.069 | 17.551 | 67.261 |
| kev-0.8b-ft-s18 | 1597 | 0.747 | 0.750 | 0.801 | 0.374 | 0.591 | 0.075 | 0.367 | 0.573 | 0.048 | 0.701–0.794 | 0.044–0.128 | 0.028–0.094 | — | — | 0.003 | 0.938 | 0.070 | 17.414 | 67.183 |
| kev-0.8b-ft-s19 | 1597 | 0.737 | 0.740 | 0.799 | 0.375 | 0.592 | 0.070 | 0.367 | 0.568 | 0.036 | 0.692–0.784 | 0.035–0.119 | 0.026–0.085 | — | — | 0.003 | 0.917 | 0.081 | 17.520 | 67.895 |
| FT mean ± SD [range] | — | 0.743 ± 0.005 [0.737–0.747] | 0.746 ± 0.006 [0.740–0.750] | 0.806 ± 0.009 [0.799–0.816] | 0.369 ± 0.010 [0.357–0.375] | 0.584 ± 0.012 [0.570–0.592] | 0.070 ± 0.004 [0.066–0.075] | 0.362 ± 0.009 [0.352–0.367] | 0.565 ± 0.009 [0.555–0.573] | 0.045 ± 0.008 [0.036–0.051] | — | — | — | — | — | 0.002 ± 0.001 [0.001–0.003] | 0.929 ± 0.010 [0.917–0.938] | 0.073 ± 0.007 [0.069–0.081] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 2074 | 0.905 | 0.901 | 0.960 | 0.073 | 0.263 | 0.039 | 0.072 | 0.250 | 0.024 | 0.864–0.927 | 0.023–0.065 | 0.013–0.048 | 0.861 | 0.940 | — | — | — | 65.451 | 207.752 |
| kev-4b-ft-s18 | 2074 | 0.912 | 0.907 | 0.957 | 0.072 | 0.259 | 0.033 | 0.071 | 0.252 | 0.023 | 0.871–0.932 | 0.017–0.062 | 0.011–0.051 | 0.862 | 0.951 | — | — | — | 65.392 | 205.848 |
| kev-4b-ft-s19 | 2074 | 0.906 | 0.902 | 0.959 | 0.074 | 0.262 | 0.035 | 0.073 | 0.257 | 0.028 | 0.868–0.929 | 0.018–0.060 | 0.016–0.054 | 0.865 | 0.940 | — | — | — | 65.326 | 205.893 |
| FT mean ± SD [range] | — | 0.908 ± 0.004 [0.905–0.912] | 0.903 ± 0.003 [0.901–0.907] | 0.959 ± 0.001 [0.957–0.960] | 0.073 ± 0.001 [0.072–0.074] | 0.262 ± 0.002 [0.259–0.263] | 0.036 ± 0.003 [0.033–0.039] | 0.072 ± 0.001 [0.071–0.073] | 0.253 ± 0.004 [0.250–0.257] | 0.025 ± 0.003 [0.023–0.028] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b-ft-s17 | 1597 | 0.786 | 0.790 | 0.882 | 0.343 | 0.601 | 0.135 | 0.304 | 0.492 | 0.043 | 0.740–0.839 | 0.091–0.183 | 0.026–0.092 | — | — | 0.003 | 0.961 | 0.041 | 65.451 | 207.752 |
| kev-4b-ft-s18 | 1597 | 0.801 | 0.805 | 0.882 | 0.313 | 0.529 | 0.097 | 0.296 | 0.488 | 0.031 | 0.752–0.851 | 0.057–0.147 | 0.020–0.081 | — | — | 0.001 | 0.967 | 0.049 | 65.392 | 205.848 |
| kev-4b-ft-s19 | 1597 | 0.797 | 0.801 | 0.893 | 0.307 | 0.502 | 0.100 | 0.290 | 0.472 | 0.060 | 0.751–0.850 | 0.061–0.144 | 0.033–0.102 | — | — | 0.004 | 0.962 | 0.043 | 65.326 | 205.893 |
| FT mean ± SD [range] | — | 0.795 ± 0.008 [0.786–0.801] | 0.799 ± 0.008 [0.790–0.805] | 0.886 ± 0.006 [0.882–0.893] | 0.321 ± 0.019 [0.307–0.343] | 0.544 ± 0.051 [0.502–0.601] | 0.111 ± 0.021 [0.097–0.135] | 0.297 ± 0.007 [0.290–0.304] | 0.484 ± 0.011 [0.472–0.492] | 0.045 ± 0.015 [0.031–0.060] | — | — | — | — | — | 0.003 ± 0.001 [0.001–0.004] | 0.963 ± 0.003 [0.961–0.967] | 0.044 ± 0.005 [0.041–0.049] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 2074 | 0.913 | 0.908 | 0.960 | 0.072 | 0.285 | 0.044 | 0.071 | 0.257 | 0.022 | 0.875–0.934 | 0.029–0.069 | 0.013–0.047 | 0.860 | 0.956 | — | — | — | 62.320 | 128.961 |
| kev-9b-ft-s18 | 2074 | 0.910 | 0.905 | 0.957 | 0.074 | 0.282 | 0.043 | 0.073 | 0.263 | 0.025 | 0.880–0.924 | 0.031–0.061 | 0.015–0.046 | 0.855 | 0.955 | — | — | — | 62.130 | 132.002 |
| kev-9b-ft-s19 | 2074 | 0.902 | 0.898 | 0.956 | 0.079 | 0.302 | 0.048 | 0.077 | 0.274 | 0.030 | 0.867–0.922 | 0.034–0.072 | 0.019–0.052 | 0.856 | 0.939 | — | — | — | 62.441 | 131.808 |
| FT mean ± SD [range] | — | 0.909 ± 0.006 [0.902–0.913] | 0.903 ± 0.005 [0.898–0.908] | 0.958 ± 0.002 [0.956–0.960] | 0.075 ± 0.003 [0.072–0.079] | 0.290 ± 0.011 [0.282–0.302] | 0.045 ± 0.003 [0.043–0.048] | 0.073 ± 0.003 [0.071–0.077] | 0.265 ± 0.009 [0.257–0.274] | 0.026 ± 0.004 [0.022–0.030] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b-ft-s17 | 1597 | 0.807 | 0.812 | 0.902 | 0.298 | 0.502 | 0.104 | 0.275 | 0.441 | 0.043 | 0.761–0.860 | 0.061–0.152 | 0.023–0.088 | — | — | 0.003 | 0.967 | 0.043 | 62.320 | 128.961 |
| kev-9b-ft-s18 | 1597 | 0.806 | 0.810 | 0.907 | 0.287 | 0.461 | 0.080 | 0.277 | 0.445 | 0.050 | 0.765–0.855 | 0.043–0.122 | 0.029–0.092 | — | — | 0.004 | 0.961 | 0.057 | 62.130 | 132.002 |
| kev-9b-ft-s19 | 1597 | 0.812 | 0.816 | 0.908 | 0.307 | 0.538 | 0.110 | 0.283 | 0.464 | 0.052 | 0.764–0.861 | 0.068–0.161 | 0.021–0.100 | — | — | 0.003 | 0.967 | 0.034 | 62.441 | 131.808 |
| FT mean ± SD [range] | — | 0.808 ± 0.003 [0.806–0.812] | 0.813 ± 0.003 [0.810–0.816] | 0.905 ± 0.003 [0.902–0.908] | 0.297 ± 0.010 [0.287–0.307] | 0.500 ± 0.038 [0.461–0.538] | 0.098 ± 0.016 [0.080–0.110] | 0.278 ± 0.004 [0.275–0.283] | 0.450 ± 0.013 [0.441–0.464] | 0.049 ± 0.005 [0.043–0.052] | — | — | — | — | — | 0.003 ± 0.001 [0.003–0.004] | 0.965 ± 0.003 [0.961–0.967] | 0.045 ± 0.011 [0.034–0.057] | — | — |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.2xlarge | us-west-2 | 17.551 | 67.261 | 661 | $0.3672 | sv-eval-kev-08b-ft-s17-261003163212526066 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 17.414 | 67.183 | 661 | $0.3672 | sv-eval-kev-08b-ft-s18-261003151151302617 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.2xlarge | us-west-2 | 17.520 | 67.895 | 671 | $0.3728 | sv-eval-kev-08b-ft-s19-261003160020669729 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 65.451 | 207.752 | 1200 | $0.6667 | sv-eval-kev-4b-ft-s17-261003173603791961 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 65.392 | 205.848 | 1209 | $0.6717 | sv-eval-kev-4b-ft-s18-261003183037069126 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 65.326 | 205.893 | 1209 | $0.6717 | sv-eval-kev-4b-ft-s19-261004002631414261 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.8xlarge | us-west-2 | 62.320 | 128.961 | 976 | $1.8978 | sv-eval-kev-9b-ft-s17-261003192905316559 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.2xlarge | us-east-2 | 62.130 | 132.002 | 1066 | $1.1844 | sv-eval-kev-9b-ft-s18-261003200413906370 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.2xlarge | us-east-2 | 62.441 | 131.808 | 1067 | $1.1856 | sv-eval-kev-9b-ft-s19-261003191306099634 |

Total billed evaluation cost for the reported arms: **$7.3851 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | noul | granularity | document | 943 | 0.780 | 0.776 | 0.075 | 0.712 | 0.840 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 754 | 0.824 | 0.819 | 0.060 | 0.780 | 0.859 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 377 | 0.798 | 0.773 | 0.090 | 0.647 | 0.899 |
| kev-0.8b-ft-s17 | noul | provenance | generated | 201 | 0.851 | 0.554 | 0.108 | 0.160 | 0.949 |
| kev-0.8b-ft-s17 | noul | provenance | human | 1873 | 0.794 | 0.792 | 0.066 | 0.742 | 0.842 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2074 | 0.799 | 0.792 | 0.068 | 0.726 | 0.858 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1314 | 0.844 | 0.821 | 0.058 | 0.760 | 0.883 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 760 | 0.722 | 0.734 | 0.100 | 0.698 | 0.771 |
| kev-0.8b-ft-s17 | noul | source accuracy | generated | 201 | 0.851 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 1873 | 0.794 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 735 | 0.770 | 0.770 | 0.040 | 0.708 | 0.833 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 547 | 0.751 | 0.828 | 0.070 | 0.646 | 0.837 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 315 | 0.679 | 0.460 | 0.155 | 0.663 | 0.716 |
| kev-0.8b-ft-s17 | choice | provenance | generated | 217 | 0.636 | 0.660 | 0.207 | 0.492 | 0.828 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1380 | 0.763 | 0.676 | 0.048 | 0.712 | 0.816 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.746 | 0.665 | 0.066 | 0.678 | 0.818 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 907 | 0.762 | 0.659 | 0.058 | 0.666 | 0.812 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 690 | 0.725 | 0.763 | 0.082 | 0.686 | 0.839 |
| kev-0.8b-ft-s17 | choice | source accuracy | generated | 217 | 0.636 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1380 | 0.763 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 943 | 0.782 | 0.778 | 0.062 | 0.732 | 0.824 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 754 | 0.798 | 0.796 | 0.060 | 0.777 | 0.816 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 377 | 0.793 | 0.764 | 0.076 | 0.620 | 0.907 |
| kev-0.8b-ft-s18 | noul | provenance | generated | 201 | 0.856 | 0.592 | 0.092 | 0.240 | 0.943 |
| kev-0.8b-ft-s18 | noul | provenance | human | 1873 | 0.783 | 0.781 | 0.059 | 0.744 | 0.818 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2074 | 0.790 | 0.784 | 0.059 | 0.730 | 0.838 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1314 | 0.826 | 0.808 | 0.043 | 0.757 | 0.859 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 760 | 0.726 | 0.735 | 0.093 | 0.708 | 0.763 |
| kev-0.8b-ft-s18 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 1873 | 0.783 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 735 | 0.747 | 0.748 | 0.071 | 0.630 | 0.866 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 547 | 0.768 | 0.838 | 0.068 | 0.654 | 0.860 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 315 | 0.711 | 0.493 | 0.138 | 0.654 | 0.826 |
| kev-0.8b-ft-s18 | choice | provenance | generated | 217 | 0.622 | 0.641 | 0.202 | 0.508 | 0.774 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1380 | 0.767 | 0.679 | 0.061 | 0.667 | 0.869 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.747 | 0.667 | 0.075 | 0.643 | 0.858 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 907 | 0.785 | 0.668 | 0.052 | 0.646 | 0.857 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 690 | 0.697 | 0.752 | 0.118 | 0.641 | 0.862 |
| kev-0.8b-ft-s18 | choice | source accuracy | generated | 217 | 0.622 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1380 | 0.767 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 943 | 0.789 | 0.785 | 0.075 | 0.737 | 0.834 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 754 | 0.812 | 0.811 | 0.066 | 0.801 | 0.821 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 377 | 0.809 | 0.779 | 0.103 | 0.633 | 0.925 |
| kev-0.8b-ft-s19 | noul | provenance | generated | 201 | 0.846 | 0.569 | 0.111 | 0.200 | 0.938 |
| kev-0.8b-ft-s19 | noul | provenance | human | 1873 | 0.796 | 0.795 | 0.068 | 0.758 | 0.831 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2074 | 0.801 | 0.795 | 0.071 | 0.743 | 0.847 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1314 | 0.839 | 0.821 | 0.053 | 0.769 | 0.872 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 760 | 0.734 | 0.740 | 0.114 | 0.722 | 0.759 |
| kev-0.8b-ft-s19 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 1873 | 0.796 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 735 | 0.747 | 0.748 | 0.057 | 0.651 | 0.844 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 547 | 0.740 | 0.820 | 0.076 | 0.630 | 0.830 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 315 | 0.708 | 0.486 | 0.145 | 0.668 | 0.789 |
| kev-0.8b-ft-s19 | choice | provenance | generated | 217 | 0.613 | 0.641 | 0.213 | 0.444 | 0.839 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1380 | 0.757 | 0.672 | 0.051 | 0.686 | 0.830 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.737 | 0.660 | 0.070 | 0.649 | 0.831 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 907 | 0.766 | 0.658 | 0.047 | 0.643 | 0.830 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 690 | 0.699 | 0.743 | 0.106 | 0.653 | 0.833 |
| kev-0.8b-ft-s19 | choice | source accuracy | generated | 217 | 0.613 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1380 | 0.757 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 943 | 0.899 | 0.897 | 0.043 | 0.863 | 0.931 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 754 | 0.911 | 0.908 | 0.044 | 0.878 | 0.938 |
| kev-4b-ft-s17 | noul | granularity | sentence | 377 | 0.907 | 0.892 | 0.043 | 0.820 | 0.965 |
| kev-4b-ft-s17 | noul | provenance | generated | 201 | 0.856 | 0.574 | 0.109 | 0.200 | 0.949 |
| kev-4b-ft-s17 | noul | provenance | human | 1873 | 0.910 | 0.909 | 0.033 | 0.880 | 0.938 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2074 | 0.905 | 0.901 | 0.039 | 0.861 | 0.940 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1314 | 0.901 | 0.879 | 0.045 | 0.817 | 0.940 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 760 | 0.912 | 0.919 | 0.035 | 0.897 | 0.941 |
| kev-4b-ft-s17 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-4b-ft-s17 | noul | source accuracy | human | 1873 | 0.910 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 735 | 0.784 | 0.785 | 0.132 | 0.657 | 0.912 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 547 | 0.808 | 0.863 | 0.135 | 0.667 | 0.923 |
| kev-4b-ft-s17 | choice | granularity | sentence | 315 | 0.752 | 0.523 | 0.163 | 0.688 | 0.881 |
| kev-4b-ft-s17 | choice | provenance | generated | 217 | 0.567 | 0.593 | 0.333 | 0.411 | 0.774 |
| kev-4b-ft-s17 | choice | provenance | human | 1380 | 0.820 | 0.715 | 0.104 | 0.713 | 0.931 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.786 | 0.693 | 0.135 | 0.667 | 0.912 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 907 | 0.834 | 0.694 | 0.104 | 0.656 | 0.925 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 690 | 0.723 | 0.771 | 0.182 | 0.674 | 0.868 |
| kev-4b-ft-s17 | choice | source accuracy | generated | 217 | 0.567 | — | — | — | — |
| kev-4b-ft-s17 | choice | source accuracy | human | 1380 | 0.820 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 943 | 0.913 | 0.911 | 0.041 | 0.876 | 0.945 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 754 | 0.908 | 0.904 | 0.034 | 0.863 | 0.945 |
| kev-4b-ft-s18 | noul | granularity | sentence | 377 | 0.915 | 0.899 | 0.045 | 0.820 | 0.978 |
| kev-4b-ft-s18 | noul | provenance | generated | 201 | 0.841 | 0.549 | 0.120 | 0.160 | 0.938 |
| kev-4b-ft-s18 | noul | provenance | human | 1873 | 0.919 | 0.918 | 0.026 | 0.882 | 0.954 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2074 | 0.912 | 0.907 | 0.033 | 0.862 | 0.951 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1314 | 0.910 | 0.888 | 0.037 | 0.827 | 0.949 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 760 | 0.914 | 0.926 | 0.037 | 0.892 | 0.960 |
| kev-4b-ft-s18 | noul | source accuracy | generated | 201 | 0.841 | — | — | — | — |
| kev-4b-ft-s18 | noul | source accuracy | human | 1873 | 0.919 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 735 | 0.804 | 0.805 | 0.090 | 0.692 | 0.918 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 547 | 0.803 | 0.528 | 0.103 | 0.667 | 0.917 |
| kev-4b-ft-s18 | choice | granularity | sentence | 315 | 0.790 | 0.550 | 0.142 | 0.722 | 0.927 |
| kev-4b-ft-s18 | choice | provenance | generated | 217 | 0.594 | 0.624 | 0.280 | 0.419 | 0.828 |
| kev-4b-ft-s18 | choice | provenance | human | 1380 | 0.833 | 0.557 | 0.074 | 0.740 | 0.931 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.801 | 0.537 | 0.097 | 0.692 | 0.919 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 907 | 0.827 | 0.521 | 0.085 | 0.636 | 0.927 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 690 | 0.767 | 0.808 | 0.115 | 0.725 | 0.891 |
| kev-4b-ft-s18 | choice | source accuracy | generated | 217 | 0.594 | — | — | — | — |
| kev-4b-ft-s18 | choice | source accuracy | human | 1380 | 0.833 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 943 | 0.908 | 0.905 | 0.038 | 0.874 | 0.937 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 754 | 0.907 | 0.904 | 0.037 | 0.878 | 0.931 |
| kev-4b-ft-s19 | noul | granularity | sentence | 377 | 0.902 | 0.886 | 0.041 | 0.807 | 0.965 |
| kev-4b-ft-s19 | noul | provenance | generated | 201 | 0.826 | 0.557 | 0.119 | 0.200 | 0.915 |
| kev-4b-ft-s19 | noul | provenance | human | 1873 | 0.915 | 0.914 | 0.026 | 0.883 | 0.945 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2074 | 0.906 | 0.902 | 0.035 | 0.865 | 0.940 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1314 | 0.906 | 0.885 | 0.040 | 0.827 | 0.943 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 760 | 0.907 | 0.912 | 0.030 | 0.895 | 0.929 |
| kev-4b-ft-s19 | noul | source accuracy | generated | 201 | 0.826 | — | — | — | — |
| kev-4b-ft-s19 | noul | source accuracy | human | 1873 | 0.915 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 735 | 0.801 | 0.802 | 0.094 | 0.689 | 0.915 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 547 | 0.819 | 0.871 | 0.085 | 0.679 | 0.933 |
| kev-4b-ft-s19 | choice | granularity | sentence | 315 | 0.749 | 0.528 | 0.155 | 0.659 | 0.927 |
| kev-4b-ft-s19 | choice | provenance | generated | 217 | 0.562 | 0.595 | 0.289 | 0.363 | 0.828 |
| kev-4b-ft-s19 | choice | provenance | human | 1380 | 0.834 | 0.724 | 0.072 | 0.735 | 0.937 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.797 | 0.701 | 0.100 | 0.678 | 0.924 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 907 | 0.829 | 0.689 | 0.078 | 0.639 | 0.927 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 690 | 0.755 | 0.808 | 0.134 | 0.702 | 0.914 |
| kev-4b-ft-s19 | choice | source accuracy | generated | 217 | 0.562 | — | — | — | — |
| kev-4b-ft-s19 | choice | source accuracy | human | 1380 | 0.834 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 943 | 0.914 | 0.911 | 0.045 | 0.874 | 0.949 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 754 | 0.914 | 0.909 | 0.048 | 0.863 | 0.955 |
| kev-9b-ft-s17 | noul | granularity | sentence | 377 | 0.910 | 0.893 | 0.048 | 0.813 | 0.974 |
| kev-9b-ft-s17 | noul | provenance | generated | 201 | 0.851 | 0.572 | 0.122 | 0.200 | 0.943 |
| kev-9b-ft-s17 | noul | provenance | human | 1873 | 0.920 | 0.918 | 0.036 | 0.879 | 0.958 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2074 | 0.913 | 0.908 | 0.044 | 0.860 | 0.956 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1314 | 0.909 | 0.882 | 0.052 | 0.808 | 0.957 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 760 | 0.920 | 0.928 | 0.040 | 0.903 | 0.953 |
| kev-9b-ft-s17 | noul | source accuracy | generated | 201 | 0.851 | — | — | — | — |
| kev-9b-ft-s17 | noul | source accuracy | human | 1873 | 0.920 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 735 | 0.820 | 0.821 | 0.094 | 0.711 | 0.932 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 547 | 0.821 | 0.540 | 0.094 | 0.679 | 0.940 |
| kev-9b-ft-s17 | choice | granularity | sentence | 315 | 0.752 | 0.533 | 0.159 | 0.654 | 0.945 |
| kev-9b-ft-s17 | choice | provenance | generated | 217 | 0.571 | 0.608 | 0.293 | 0.355 | 0.860 |
| kev-9b-ft-s17 | choice | provenance | human | 1380 | 0.844 | 0.564 | 0.075 | 0.746 | 0.947 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.807 | 0.541 | 0.104 | 0.687 | 0.937 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 907 | 0.846 | 0.531 | 0.075 | 0.643 | 0.952 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 690 | 0.757 | 0.799 | 0.146 | 0.713 | 0.885 |
| kev-9b-ft-s17 | choice | source accuracy | generated | 217 | 0.571 | — | — | — | — |
| kev-9b-ft-s17 | choice | source accuracy | human | 1380 | 0.844 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 943 | 0.917 | 0.915 | 0.036 | 0.881 | 0.949 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 754 | 0.912 | 0.908 | 0.039 | 0.866 | 0.950 |
| kev-9b-ft-s18 | noul | granularity | sentence | 377 | 0.889 | 0.866 | 0.080 | 0.753 | 0.978 |
| kev-9b-ft-s18 | noul | provenance | generated | 201 | 0.851 | 0.572 | 0.126 | 0.200 | 0.943 |
| kev-9b-ft-s18 | noul | provenance | human | 1873 | 0.917 | 0.915 | 0.035 | 0.873 | 0.957 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2074 | 0.910 | 0.905 | 0.043 | 0.855 | 0.955 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1314 | 0.913 | 0.887 | 0.048 | 0.815 | 0.959 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 760 | 0.905 | 0.914 | 0.051 | 0.888 | 0.941 |
| kev-9b-ft-s18 | noul | source accuracy | generated | 201 | 0.851 | — | — | — | — |
| kev-9b-ft-s18 | noul | source accuracy | human | 1873 | 0.917 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 735 | 0.819 | 0.820 | 0.077 | 0.714 | 0.926 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 547 | 0.819 | 0.538 | 0.069 | 0.675 | 0.940 |
| kev-9b-ft-s18 | choice | granularity | sentence | 315 | 0.752 | 0.530 | 0.126 | 0.663 | 0.927 |
| kev-9b-ft-s18 | choice | provenance | generated | 217 | 0.594 | 0.630 | 0.278 | 0.379 | 0.882 |
| kev-9b-ft-s18 | choice | provenance | human | 1380 | 0.839 | 0.561 | 0.065 | 0.745 | 0.938 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.806 | 0.540 | 0.080 | 0.689 | 0.932 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 907 | 0.846 | 0.535 | 0.062 | 0.666 | 0.940 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 690 | 0.754 | 0.803 | 0.121 | 0.703 | 0.902 |
| kev-9b-ft-s18 | choice | source accuracy | generated | 217 | 0.594 | — | — | — | — |
| kev-9b-ft-s18 | choice | source accuracy | human | 1380 | 0.839 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 943 | 0.901 | 0.899 | 0.051 | 0.872 | 0.927 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 754 | 0.908 | 0.904 | 0.045 | 0.863 | 0.945 |
| kev-9b-ft-s19 | noul | granularity | sentence | 377 | 0.891 | 0.875 | 0.061 | 0.793 | 0.956 |
| kev-9b-ft-s19 | noul | provenance | generated | 201 | 0.836 | 0.563 | 0.131 | 0.200 | 0.926 |
| kev-9b-ft-s19 | noul | provenance | human | 1873 | 0.909 | 0.908 | 0.041 | 0.874 | 0.942 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2074 | 0.902 | 0.898 | 0.048 | 0.856 | 0.939 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1314 | 0.904 | 0.883 | 0.051 | 0.827 | 0.940 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 760 | 0.899 | 0.908 | 0.050 | 0.880 | 0.937 |
| kev-9b-ft-s19 | noul | source accuracy | generated | 201 | 0.836 | — | — | — | — |
| kev-9b-ft-s19 | noul | source accuracy | human | 1873 | 0.909 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 735 | 0.823 | 0.824 | 0.108 | 0.708 | 0.940 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 547 | 0.826 | 0.542 | 0.109 | 0.671 | 0.957 |
| kev-9b-ft-s19 | choice | granularity | sentence | 315 | 0.759 | 0.536 | 0.153 | 0.663 | 0.945 |
| kev-9b-ft-s19 | choice | provenance | generated | 217 | 0.571 | 0.612 | 0.311 | 0.331 | 0.892 |
| kev-9b-ft-s19 | choice | provenance | human | 1380 | 0.849 | 0.568 | 0.079 | 0.749 | 0.954 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.812 | 0.544 | 0.110 | 0.686 | 0.947 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 907 | 0.843 | 0.530 | 0.089 | 0.639 | 0.950 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 690 | 0.770 | 0.825 | 0.145 | 0.713 | 0.937 |
| kev-9b-ft-s19 | choice | source accuracy | generated | 217 | 0.571 | — | — | — | — |
| kev-9b-ft-s19 | choice | source accuracy | human | 1380 | 0.849 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b-ft-s17 | 1095 | 0.538 | 33 | 0.792 | 0.788 | 0.769 |
| kev-0.8b-ft-s18 | 1095 | 0.484 | 33 | 0.784 | 0.782 | 0.774 |
| kev-0.8b-ft-s19 | 1095 | 0.530 | 33 | 0.795 | 0.793 | 0.786 |
| kev-4b-ft-s17 | 1095 | 0.393 | 33 | 0.901 | 0.903 | 0.894 |
| kev-4b-ft-s18 | 1095 | 0.281 | 33 | 0.907 | 0.914 | 0.904 |
| kev-4b-ft-s19 | 1095 | 0.332 | 33 | 0.902 | 0.906 | 0.902 |
| kev-9b-ft-s17 | 1095 | 0.526 | 33 | 0.908 | 0.907 | 0.903 |
| kev-9b-ft-s18 | 1095 | 0.488 | 33 | 0.905 | 0.904 | 0.901 |
| kev-9b-ft-s19 | 1095 | 0.295 | 33 | 0.898 | 0.908 | 0.887 |

## Interpretation and caveats

- Test label origins: construction (3092), human-adjudication (258), llm-review-consensus (321). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice insufficient-context=2, no-defect=821, real-defect=774; yes/no False=1151, True=923. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.30 finding-confirmation, κ=0.30 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
