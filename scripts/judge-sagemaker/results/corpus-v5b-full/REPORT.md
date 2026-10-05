# Corpus evaluation report: `corpus-v5b-full`

## Status

- v5b: lint rules at main ca941af16a; labels human-adjudication > llm-review-consensus > teacher-panel; redesigned semantic items. The human-adjudication test slice is the rows four LLM reviewers could not settle, labelled once by one person with the earlier (confusing) review UI; read it as preliminary.

## Dataset and coverage

- Campaign: `corpus-20261003-s17-v5b/full`. Round 4 on the v5b export (full): lint rules at main ca941af16a87 (latin-abbreviation and latinisms off by profile default), semantic regions without link-reference definitions or bare URLs, and labels from the v5 human queue, the earlier human lint sheets and the settled LLM-review consensus (label_origin llm-review-consensus). runtime_scale is 13,430 train rows / 5,420. Laya fine-tunes are left out until round 1 shows Laya fine-tuning beats its base.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 15 of 15 required (`kev-0.8b`, `kev-4b`, `kev-9b`, `laya-english`, `laya-multilingual`, `laya-typed-decisions`, `kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 144 of 168 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1720 examples; SHA-256 `8534bee7b935ae80b47d35e1e96a4a288ab3ba86c6bfe851ff01e8dcf3300b1b`.
- Test: 3671 examples; SHA-256 `a77f6f64b85b81a13330df57b8cd3973edd2b295ae30efdf4ddc12a4a8bb0b31`.
- Test composition: label origins `construction`=3092, `human-adjudication`=258, `llm-review-consensus`=321; choice labels insufficient-context=2, no-defect=821, real-defect=774; yes/no labels False=1151, True=923.

## Headline by role

Each arm's numbers come from `results/corpus-v5b-full/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1597 (real-defect=774, no-defect=821).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.238 | 0.206–0.277 | 0.136 | 0.341 | 0.193 | 0.094 | NVIDIA A10G | 17.115 | $0.7133 |
| kev-0.8b-ft-s17 | 0.741 | 0.691–0.783 | 0.818 | 0.664 | 0.064 | 0.020 | NVIDIA A10G | 17.251 | $0.7122 |
| kev-0.8b-ft-s18 | 0.738 | 0.694–0.778 | 0.793 | 0.682 | 0.048 | 0.030 | NVIDIA A10G | 17.291 | $0.7122 |
| kev-0.8b-ft-s19 | 0.757 | 0.707–0.800 | 0.822 | 0.693 | 0.041 | 0.037 | NVIDIA A10G | 17.469 | $0.3672 |
| kev-0.8b FT mean ± SD [range] | 0.745 ± 0.011 [0.738–0.757] | — | 0.811 ± 0.015 [0.793–0.822] | 0.680 ± 0.015 [0.664–0.693] | 0.051 ± 0.012 [0.041–0.064] | 0.029 ± 0.008 [0.020–0.037] | — | — | — |
| kev-4b | 0.308 | 0.271–0.351 | 0.487 | 0.129 | 0.114 | 0.049 | NVIDIA A10G | 64.928 | $1.3133 |
| kev-4b-ft-s17 | 0.800 | 0.748–0.849 | 0.915 | 0.685 | 0.105 | 0.047 | NVIDIA A10G | 64.933 | $1.2878 |
| kev-4b-ft-s18 | 0.799 | 0.750–0.844 | 0.898 | 0.700 | 0.107 | 0.047 | NVIDIA A10G | 64.973 | $1.2856 |
| kev-4b-ft-s19 | 0.795 | 0.746–0.843 | 0.901 | 0.689 | 0.096 | 0.057 | NVIDIA A10G | 65.141 | $0.9650 |
| kev-4b FT mean ± SD [range] | 0.798 ± 0.003 [0.795–0.800] | — | 0.904 ± 0.009 [0.898–0.915] | 0.691 ± 0.008 [0.685–0.700] | 0.103 ± 0.006 [0.096–0.107] | 0.051 ± 0.006 [0.047–0.057] | — | — | — |
| kev-9b | 0.503 | 0.475–0.535 | 0.793 | 0.213 | 0.101 | 0.084 | NVIDIA L40S | 62.516 | $1.4111 |
| kev-9b-ft-s17 | 0.824 | 0.775–0.867 | 0.947 | 0.702 | 0.085 | 0.052 | NVIDIA L40S | 62.793 | $3.0586 |
| kev-9b-ft-s18 | 0.806 | 0.759–0.851 | 0.938 | 0.674 | 0.100 | 0.040 | NVIDIA L40S | 62.136 | $1.3833 |
| kev-9b-ft-s19 | 0.813 | 0.764–0.859 | 0.930 | 0.697 | 0.093 | 0.056 | NVIDIA L40S | 62.103 | $1.3750 |
| kev-9b FT mean ± SD [range] | 0.815 ± 0.009 [0.806–0.824] | — | 0.938 ± 0.008 [0.930–0.947] | 0.691 ± 0.015 [0.674–0.702] | 0.093 ± 0.007 [0.085–0.100] | 0.049 ± 0.008 [0.040–0.056] | — | — | — |
| laya-english | 0.431 | 0.401–0.457 | 0.305 | 0.557 | 0.034 | 0.030 | NVIDIA A10G | 27.562 | $1.5400 |
| laya-multilingual | 0.354 | 0.329–0.381 | 0.121 | 0.587 | 0.253 | 0.020 | NVIDIA A10G | 22.767 | $1.4750 |
| laya-typed-decisions | 0.360 | 0.334–0.388 | 0.327 | 0.392 | 0.055 | 0.028 | NVIDIA A10G | 27.974 | $1.2269 |

- Best single arm: `kev-9b-ft-s17` (balanced accuracy 0.824).
- Best fine-tuned family by seed mean: `kev-9b` (0.815 ± 0.009 [0.806–0.824]).

### semantic-detection (`noul`)

Test items: 2074 (True=923, False=1151).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.502 | 0.496–0.510 | 0.024 | 0.980 | 0.167 | 0.020 | NVIDIA A10G | 17.115 | $0.7133 |
| kev-0.8b-ft-s17 | 0.776 | 0.735–0.815 | 0.706 | 0.845 | 0.074 | 0.045 | NVIDIA A10G | 17.251 | $0.7122 |
| kev-0.8b-ft-s18 | 0.769 | 0.721–0.818 | 0.686 | 0.853 | 0.062 | 0.046 | NVIDIA A10G | 17.291 | $0.7122 |
| kev-0.8b-ft-s19 | 0.779 | 0.734–0.822 | 0.698 | 0.860 | 0.064 | 0.044 | NVIDIA A10G | 17.469 | $0.3672 |
| kev-0.8b FT mean ± SD [range] | 0.775 ± 0.005 [0.769–0.779] | — | 0.697 ± 0.010 [0.686–0.706] | 0.853 ± 0.007 [0.845–0.860] | 0.067 ± 0.006 [0.062–0.074] | 0.045 ± 0.001 [0.044–0.046] | — | — | — |
| kev-4b | 0.545 | 0.520–0.572 | 0.154 | 0.937 | 0.104 | 0.055 | NVIDIA A10G | 64.928 | $1.3133 |
| kev-4b-ft-s17 | 0.900 | 0.864–0.927 | 0.857 | 0.943 | 0.034 | 0.026 | NVIDIA A10G | 64.933 | $1.2878 |
| kev-4b-ft-s18 | 0.905 | 0.867–0.933 | 0.865 | 0.946 | 0.037 | 0.023 | NVIDIA A10G | 64.973 | $1.2856 |
| kev-4b-ft-s19 | 0.905 | 0.877–0.928 | 0.870 | 0.940 | 0.030 | 0.025 | NVIDIA A10G | 65.141 | $0.9650 |
| kev-4b FT mean ± SD [range] | 0.903 ± 0.003 [0.900–0.905] | — | 0.864 ± 0.007 [0.857–0.870] | 0.943 ± 0.003 [0.940–0.946] | 0.034 ± 0.003 [0.030–0.037] | 0.025 ± 0.001 [0.023–0.026] | — | — | — |
| kev-9b | 0.679 | 0.631–0.726 | 0.505 | 0.854 | 0.045 | 0.049 | NVIDIA L40S | 62.516 | $1.4111 |
| kev-9b-ft-s17 | 0.905 | 0.879–0.928 | 0.873 | 0.937 | 0.048 | 0.019 | NVIDIA L40S | 62.793 | $3.0586 |
| kev-9b-ft-s18 | 0.898 | 0.870–0.920 | 0.848 | 0.948 | 0.050 | 0.024 | NVIDIA L40S | 62.136 | $1.3833 |
| kev-9b-ft-s19 | 0.894 | 0.864–0.919 | 0.837 | 0.950 | 0.051 | 0.023 | NVIDIA L40S | 62.103 | $1.3750 |
| kev-9b FT mean ± SD [range] | 0.899 ± 0.006 [0.894–0.905] | — | 0.853 ± 0.018 [0.837–0.873] | 0.945 ± 0.007 [0.937–0.950] | 0.050 ± 0.002 [0.048–0.051] | 0.022 ± 0.002 [0.019–0.024] | — | — | — |
| laya-english | 0.469 | 0.435–0.506 | 0.392 | 0.546 | 0.219 | 0.027 | NVIDIA A10G | 27.562 | $1.5400 |
| laya-multilingual | 0.545 | 0.520–0.574 | 0.739 | 0.351 | 0.283 | 0.015 | NVIDIA A10G | 22.767 | $1.4750 |
| laya-typed-decisions | 0.505 | 0.474–0.541 | 0.382 | 0.628 | 0.067 | 0.017 | NVIDIA A10G | 27.974 | $1.2269 |

- Best single arm: `kev-4b-ft-s18` (balanced accuracy 0.905).
- Best fine-tuned family by seed mean: `kev-4b` (0.903 ± 0.003 [0.900–0.905]).

## Balanced accuracy by test label origin

Computed by this generator from each arm's forward-order test predictions (`results/corpus-v5b-full/<arm>/results/predictions/<arm>.jsonl`) joined by item id to the arm's hash-checked test split (`<arm>/data/test.jsonl`), which supplies `label` and `label_origin`. Balanced accuracy is the headline's (`test_raw`): the mean recall of real-defect and no-defect for finding confirmation, where insufficient-context items count in n only, and of True and False for semantic detection. The *All* column reproduces each arm's headline; the generator refuses to render when it does not. A slice that holds one class reduces to that class's recall, and small slices are noisy. Fine-tune family rows give the seed mean ± sample SD over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items by origin: `human-adjudication` 173 (real-defect=96, no-defect=75, insufficient-context=2); `llm-review-consensus` 114 (real-defect=23, no-defect=91); `construction` 1310 (real-defect=655, no-defect=655).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b | 0.238 | 0.446 | 0.330 | 0.195 |
| kev-0.8b-ft-s17 | 0.741 | 0.495 | 0.819 | 0.764 |
| kev-0.8b-ft-s18 | 0.738 | 0.495 | 0.732 | 0.762 |
| kev-0.8b-ft-s19 | 0.757 | 0.485 | 0.672 | 0.792 |
| kev-0.8b FT mean ± SD | 0.745 ± 0.011 | 0.492 ± 0.006 | 0.741 ± 0.074 | 0.773 ± 0.017 |
| kev-4b | 0.308 | 0.376 | 0.317 | 0.292 |
| kev-4b-ft-s17 | 0.800 | 0.492 | 0.808 | 0.836 |
| kev-4b-ft-s18 | 0.799 | 0.505 | 0.737 | 0.837 |
| kev-4b-ft-s19 | 0.795 | 0.491 | 0.737 | 0.837 |
| kev-4b FT mean ± SD | 0.798 ± 0.003 | 0.496 ± 0.008 | 0.761 ± 0.041 | 0.837 ± 0.001 |
| kev-9b | 0.503 | 0.503 | 0.606 | 0.489 |
| kev-9b-ft-s17 | 0.824 | 0.495 | 0.802 | 0.869 |
| kev-9b-ft-s18 | 0.806 | 0.478 | 0.791 | 0.850 |
| kev-9b-ft-s19 | 0.813 | 0.466 | 0.808 | 0.860 |
| kev-9b FT mean ± SD | 0.815 ± 0.009 | 0.480 ± 0.015 | 0.800 ± 0.008 | 0.860 ± 0.010 |
| laya-english | 0.431 | 0.426 | 0.296 | 0.440 |
| laya-multilingual | 0.354 | 0.291 | 0.274 | 0.372 |
| laya-typed-decisions | 0.360 | 0.386 | 0.252 | 0.362 |

### semantic-detection (`noul`)

Test items by origin: `human-adjudication` 85 (False=57, True=28); `llm-review-consensus` 207 (False=203, True=4); `construction` 1782 (False=891, True=891).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| kev-0.8b | 0.502 | 0.500 | 0.498 | 0.500 |
| kev-0.8b-ft-s17 | 0.776 | 0.448 | 0.865 | 0.771 |
| kev-0.8b-ft-s18 | 0.769 | 0.466 | 0.873 | 0.763 |
| kev-0.8b-ft-s19 | 0.779 | 0.466 | 0.870 | 0.774 |
| kev-0.8b FT mean ± SD | 0.775 ± 0.005 | 0.460 ± 0.010 | 0.869 ± 0.004 | 0.769 ± 0.006 |
| kev-4b | 0.545 | 0.475 | 0.483 | 0.547 |
| kev-4b-ft-s17 | 0.900 | 0.475 | 0.870 | 0.910 |
| kev-4b-ft-s18 | 0.905 | 0.501 | 0.873 | 0.914 |
| kev-4b-ft-s19 | 0.905 | 0.448 | 0.865 | 0.917 |
| kev-4b FT mean ± SD | 0.903 ± 0.003 | 0.475 ± 0.027 | 0.869 ± 0.004 | 0.914 ± 0.003 |
| kev-9b | 0.679 | 0.423 | 0.951 | 0.685 |
| kev-9b-ft-s17 | 0.905 | 0.439 | 0.873 | 0.915 |
| kev-9b-ft-s18 | 0.898 | 0.465 | 0.870 | 0.908 |
| kev-9b-ft-s19 | 0.894 | 0.439 | 0.998 | 0.905 |
| kev-9b FT mean ± SD | 0.899 ± 0.006 | 0.448 ± 0.015 | 0.913 ± 0.073 | 0.909 ± 0.005 |
| laya-english | 0.469 | 0.630 | 0.619 | 0.471 |
| laya-multilingual | 0.545 | 0.613 | 0.501 | 0.554 |
| laya-typed-decisions | 0.505 | 0.612 | 0.536 | 0.511 |

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | this campaign | 0.238 | 0.745 | +0.507 | 3/3 | +0.675 | +0.339 | -0.142 | -0.065 |
| kev-4b | this campaign | 0.308 | 0.798 | +0.490 | 3/3 | +0.417 | +0.562 | -0.011 | +0.002 |
| kev-9b | this campaign | 0.503 | 0.815 | +0.311 | 3/3 | +0.145 | +0.477 | -0.009 | -0.034 |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | this campaign | 0.502 | 0.775 | +0.273 | 3/3 | +0.673 | -0.127 | -0.101 | +0.025 |
| kev-4b | this campaign | 0.545 | 0.903 | +0.358 | 3/3 | +0.710 | +0.006 | -0.070 | -0.030 |
| kev-9b | this campaign | 0.679 | 0.899 | +0.219 | 3/3 | +0.348 | +0.091 | +0.005 | -0.027 |

## Comparison with `corpus-v3-on-v5b`

Both campaigns score the same test and calibration export (hashes verified). Δ is `corpus-v5b-full` minus `corpus-v3-on-v5b` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.

### finding-confirmation (`choice`)

| Family | corpus-v5b-full bal. acc. | corpus-v3-on-v5b bal. acc. | Δ bal. acc. | Seeds better | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.745 ± 0.011 [0.738–0.757] | 0.758 ± 0.015 [0.746–0.775] | -0.012 | 1/3 | -0.016 | -0.009 | -0.022 | +0.002 |
| kev-4b | 0.798 ± 0.003 [0.795–0.800] | 0.792 ± 0.003 [0.789–0.794] | +0.006 | 3/3 | -0.018 | +0.030 | -0.026 | +0.004 |
| kev-9b | 0.815 ± 0.009 [0.806–0.824] | 0.825 ± 0.010 [0.817–0.836] | -0.010 | 1/3 | -0.007 | -0.014 | -0.006 | +0.012 |

### semantic-detection (`noul`)

| Family | corpus-v5b-full bal. acc. | corpus-v3-on-v5b bal. acc. | Δ bal. acc. | Seeds better | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.775 ± 0.005 [0.769–0.779] | 0.730 ± 0.017 [0.711–0.741] | +0.045 | 3/3 | +0.058 | +0.032 | -0.023 | +0.010 |
| kev-4b | 0.903 ± 0.003 [0.900–0.905] | 0.844 ± 0.016 [0.831–0.862] | +0.059 | 3/3 | +0.119 | -0.000 | -0.032 | +0.000 |
| kev-9b | 0.899 ± 0.006 [0.894–0.905] | 0.883 ± 0.003 [0.880–0.886] | +0.016 | 3/3 | +0.007 | +0.025 | +0.010 | +0.000 |

## Label-source ablation

Campaigns on this campaign's test and calibration export (hashes verified): `corpus-v5b-full` (`corpus-20261003-s17-v5b/full`); `corpus-v5b-human-only` (`corpus-20261003-s17-v5b/human-only`); `corpus-v5b-llm-only` (`corpus-20261003-s17-v5b/llm-only`); `corpus-v3-on-v5b` (`corpus-20261003-s17-v5b/v3-checkpoints`, checkpoints from `corpus-20260930-s17-v3/full`). Each campaign's notes say what its fine-tunes trained on.

Cells are balanced accuracy as defined under *Balanced accuracy by test label origin*: the seed mean ± sample SD of a complete fine-tune family, or a single base-arm run taken from the first listed campaign that evaluates it. A gap between two families reflects more than training-seed variation only when it is well beyond both SDs.

### finding-confirmation (`choice`)

| Family | Arms from | Seeds | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | base, `corpus-v5b-full` | 1 | 0.238 | 0.446 | 0.330 | 0.195 |
| kev-0.8b FT | `corpus-v5b-full` | 3 | 0.745 ± 0.011 | 0.492 ± 0.006 | 0.741 ± 0.074 | 0.773 ± 0.017 |
| kev-0.8b FT | `corpus-v5b-human-only` | 3 | 0.743 ± 0.002 | 0.510 ± 0.032 | 0.774 ± 0.014 | 0.767 ± 0.005 |
| kev-0.8b FT | `corpus-v5b-llm-only` | 3 | 0.746 ± 0.006 | 0.490 ± 0.020 | 0.788 ± 0.023 | 0.772 ± 0.005 |
| kev-0.8b FT | `corpus-v3-on-v5b` | 3 | 0.758 ± 0.015 | 0.531 ± 0.022 | 0.750 ± 0.033 | 0.784 ± 0.016 |
| kev-4b | base, `corpus-v5b-full` | 1 | 0.308 | 0.376 | 0.317 | 0.292 |
| kev-4b FT | `corpus-v5b-full` | 3 | 0.798 ± 0.003 | 0.496 ± 0.008 | 0.761 ± 0.041 | 0.837 ± 0.001 |
| kev-4b FT | `corpus-v5b-human-only` | 3 | 0.792 ± 0.011 | 0.504 ± 0.010 | 0.772 ± 0.049 | 0.828 ± 0.011 |
| kev-4b FT | `corpus-v5b-llm-only` | 3 | 0.799 ± 0.008 | 0.499 ± 0.009 | 0.723 ± 0.046 | 0.840 ± 0.010 |
| kev-4b FT | `corpus-v3-on-v5b` | 3 | 0.792 ± 0.003 | 0.500 ± 0.015 | 0.728 ± 0.011 | 0.832 ± 0.004 |
| kev-9b | base, `corpus-v5b-full` | 1 | 0.503 | 0.503 | 0.606 | 0.489 |
| kev-9b FT | `corpus-v5b-full` | 3 | 0.815 ± 0.009 | 0.480 ± 0.015 | 0.800 ± 0.008 | 0.860 ± 0.010 |
| kev-9b FT | `corpus-v5b-human-only` | 3 | 0.810 ± 0.004 | 0.474 ± 0.013 | 0.788 ± 0.003 | 0.857 ± 0.006 |
| kev-9b FT | `corpus-v5b-llm-only` | 3 | 0.813 ± 0.003 | 0.476 ± 0.018 | 0.769 ± 0.005 | 0.861 ± 0.005 |
| kev-9b FT | `corpus-v3-on-v5b` | 3 | 0.825 ± 0.010 | 0.502 ± 0.002 | 0.808 ± 0.010 | 0.868 ± 0.012 |
| laya-english | base, `corpus-v5b-full` | 1 | 0.431 | 0.426 | 0.296 | 0.440 |
| laya-multilingual | base, `corpus-v5b-full` | 1 | 0.354 | 0.291 | 0.274 | 0.372 |
| laya-typed-decisions | base, `corpus-v5b-full` | 1 | 0.360 | 0.386 | 0.252 | 0.362 |

### semantic-detection (`noul`)

| Family | Arms from | Seeds | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | base, `corpus-v5b-full` | 1 | 0.502 | 0.500 | 0.498 | 0.500 |
| kev-0.8b FT | `corpus-v5b-full` | 3 | 0.775 ± 0.005 | 0.460 ± 0.010 | 0.869 ± 0.004 | 0.769 ± 0.006 |
| kev-0.8b FT | `corpus-v5b-human-only` | 3 | 0.759 ± 0.009 | 0.457 ± 0.009 | 0.910 ± 0.076 | 0.753 ± 0.008 |
| kev-0.8b FT | `corpus-v5b-llm-only` | 3 | 0.790 ± 0.006 | 0.451 ± 0.010 | 0.948 ± 0.072 | 0.785 ± 0.007 |
| kev-0.8b FT | `corpus-v3-on-v5b` | 3 | 0.730 ± 0.017 | 0.503 ± 0.005 | 0.578 ± 0.072 | 0.716 ± 0.015 |
| kev-4b | base, `corpus-v5b-full` | 1 | 0.545 | 0.475 | 0.483 | 0.547 |
| kev-4b FT | `corpus-v5b-full` | 3 | 0.903 ± 0.003 | 0.475 ± 0.027 | 0.869 ± 0.004 | 0.914 ± 0.003 |
| kev-4b FT | `corpus-v5b-human-only` | 3 | 0.901 ± 0.008 | 0.463 ± 0.005 | 0.826 ± 0.070 | 0.912 ± 0.009 |
| kev-4b FT | `corpus-v5b-llm-only` | 3 | 0.903 ± 0.003 | 0.436 ± 0.033 | 0.870 ± 0.004 | 0.915 ± 0.005 |
| kev-4b FT | `corpus-v3-on-v5b` | 3 | 0.844 ± 0.016 | 0.506 ± 0.019 | 0.661 ± 0.073 | 0.850 ± 0.017 |
| kev-9b | base, `corpus-v5b-full` | 1 | 0.679 | 0.423 | 0.951 | 0.685 |
| kev-9b FT | `corpus-v5b-full` | 3 | 0.899 ± 0.006 | 0.448 ± 0.015 | 0.913 ± 0.073 | 0.909 ± 0.005 |
| kev-9b FT | `corpus-v5b-human-only` | 3 | 0.902 ± 0.008 | 0.439 ± 0.018 | 0.996 ± 0.001 | 0.913 ± 0.008 |
| kev-9b FT | `corpus-v5b-llm-only` | 3 | 0.903 ± 0.005 | 0.439 ± 0.018 | 0.954 ± 0.071 | 0.915 ± 0.005 |
| kev-9b FT | `corpus-v3-on-v5b` | 3 | 0.883 ± 0.003 | 0.454 ± 0.021 | 0.909 ± 0.072 | 0.890 ± 0.004 |
| laya-english | base, `corpus-v5b-full` | 1 | 0.469 | 0.630 | 0.619 | 0.471 |
| laya-multilingual | base, `corpus-v5b-full` | 1 | 0.545 | 0.613 | 0.501 | 0.554 |
| laya-typed-decisions | base, `corpus-v5b-full` | 1 | 0.505 | 0.612 | 0.536 | 0.511 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | — | — | — | — | 1 / 0 / 0 | $0.71 | $0.71 |
| kev-4b | — | — | — | — | 1 / 0 / 0 | $1.31 | $1.31 |
| kev-9b | — | — | — | — | 1 / 0 / 2 | $1.41 | $1.41 |
| laya-english | — | — | — | — | 1 / 0 / 0 | $1.54 | $1.54 |
| laya-multilingual | — | — | — | — | 1 / 0 / 0 | $1.48 | $1.48 |
| laya-typed-decisions | — | — | — | — | 1 / 0 / 0 | $1.23 | $1.23 |
| kev-0.8b-ft-s17 | 1 / 0 / 0 | $12.07 | slopvac-judge-kev-08b-s17-20261003052713 | $12.07 | 1 / 0 / 0 | $0.71 | $12.78 |
| kev-0.8b-ft-s18 | 1 / 0 / 0 | $6.70 | slopvac-judge-kev-08b-s18-20261003052725 | $6.70 | 1 / 0 / 0 | $0.71 | $7.41 |
| kev-0.8b-ft-s19 | 1 / 0 / 0 | $6.71 | slopvac-judge-kev-08b-s19-20261003085411 | $6.71 | 1 / 0 / 0 | $0.37 | $7.08 |
| kev-4b-ft-s17 | 1 / 0 / 0 | $44.29 | slopvac-judge-kev-4b-s17-20261003052736 | $44.29 | 1 / 0 / 0 | $1.29 | $45.58 |
| kev-4b-ft-s18 | 1 / 0 / 0 | $43.94 | slopvac-judge-kev-4b-s18-20261003052746 | $43.94 | 1 / 0 / 0 | $1.29 | $45.22 |
| kev-4b-ft-s19 | 1 / 0 / 0 | $43.87 | slopvac-judge-kev-4b-s19-20261003093057 | $43.87 | 1 / 0 / 0 | $0.96 | $44.83 |
| kev-9b-ft-s17 | 1 / 3 / 0 | $54.01 | slopvac-judge-kev-9b-s17-20261003093324 | $54.01 | 1 / 0 / 0 | $3.06 | $57.07 |
| kev-9b-ft-s18 | 1 / 71 / 0 | $23.85 | slopvac-judge-kev-9b-s18-20261003114524 | $23.85 | 1 / 0 / 0 | $1.38 | $25.24 |
| kev-9b-ft-s19 | 1 / 68 / 0 | $23.94 | slopvac-judge-kev-9b-s19-20261003143225 | $23.94 | 1 / 0 / 0 | $1.38 | $25.31 |

Campaign total: **$278.20 USD** (training $259.38, evaluation $18.83) over 151 training and 17 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-9b | evaluation | Stopped | 2 | $0.00 | scheduler marker `capacity_rotation` |
| kev-9b-ft-s17 | training | Failed | 3 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.16xlarge for training job usage' is… |
| kev-9b-ft-s18 | training | Failed | 71 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.16xlarge for training job usage' is… |
| kev-9b-ft-s19 | training | Failed | 1 | $0.00 | scheduler marker `orphaned_submission` |
| kev-9b-ft-s19 | training | Failed | 1 | $0.00 | scheduler marker `use2_role_trust` |
| kev-9b-ft-s19 | training | Failed | 66 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.16xlarge for training job usage' is… |

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
| kev-0.8b | 2074 | 0.554 | 0.502 | 0.580 | 0.271 | 0.745 | 0.167 | 0.244 | 0.681 | 0.020 | 0.496–0.510 | 0.093–0.235 | 0.011–0.088 | 0.024 | 0.980 | — | — | — | 17.115 | 65.892 |
| kev-0.8b-ft-s17 | 2074 | 0.784 | 0.776 | 0.863 | 0.155 | 0.502 | 0.074 | 0.152 | 0.476 | 0.045 | 0.735–0.815 | 0.049–0.111 | 0.025–0.080 | 0.706 | 0.845 | — | — | — | 17.251 | 66.545 |
| kev-0.8b-ft-s18 | 2074 | 0.779 | 0.769 | 0.854 | 0.159 | 0.509 | 0.062 | 0.156 | 0.492 | 0.046 | 0.721–0.818 | 0.032–0.103 | 0.024–0.086 | 0.686 | 0.853 | — | — | — | 17.291 | 66.251 |
| kev-0.8b-ft-s19 | 2074 | 0.788 | 0.779 | 0.864 | 0.155 | 0.490 | 0.064 | 0.153 | 0.478 | 0.044 | 0.734–0.822 | 0.034–0.104 | 0.021–0.085 | 0.698 | 0.860 | — | — | — | 17.469 | 67.897 |
| FT mean ± SD [range] | — | 0.783 ± 0.005 [0.779–0.788] | 0.775 ± 0.005 [0.769–0.779] | 0.860 ± 0.005 [0.854–0.864] | 0.156 ± 0.002 [0.155–0.159] | 0.500 ± 0.010 [0.490–0.509] | 0.067 ± 0.006 [0.062–0.074] | 0.154 ± 0.002 [0.152–0.156] | 0.482 ± 0.009 [0.476–0.492] | 0.045 ± 0.001 [0.044–0.046] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 1597 | 0.241 | 0.238 | 0.420 | 0.743 | 1.226 | 0.193 | 0.668 | 1.100 | 0.094 | 0.206–0.277 | 0.157–0.225 | 0.058–0.126 | — | — | 0.440 | 0.735 | 0.038 | 17.115 | 65.892 |
| kev-0.8b-ft-s17 | 1597 | 0.738 | 0.741 | 0.805 | 0.368 | 0.575 | 0.064 | 0.363 | 0.565 | 0.020 | 0.691–0.783 | 0.038–0.112 | 0.018–0.065 | — | — | 0.003 | 0.916 | 0.091 | 17.251 | 66.545 |
| kev-0.8b-ft-s18 | 1597 | 0.736 | 0.738 | 0.801 | 0.372 | 0.575 | 0.048 | 0.369 | 0.568 | 0.030 | 0.694–0.778 | 0.029–0.090 | 0.023–0.069 | — | — | 0.003 | 0.898 | 0.090 | 17.291 | 66.251 |
| kev-0.8b-ft-s19 | 1597 | 0.755 | 0.757 | 0.818 | 0.349 | 0.548 | 0.041 | 0.348 | 0.548 | 0.037 | 0.707–0.800 | 0.024–0.080 | 0.029–0.071 | — | — | 0.003 | 0.936 | 0.068 | 17.469 | 67.897 |
| FT mean ± SD [range] | — | 0.743 ± 0.011 [0.736–0.755] | 0.745 ± 0.011 [0.738–0.757] | 0.808 ± 0.009 [0.801–0.818] | 0.363 ± 0.012 [0.349–0.372] | 0.566 ± 0.015 [0.548–0.575] | 0.051 ± 0.012 [0.041–0.064] | 0.360 ± 0.011 [0.348–0.369] | 0.560 ± 0.011 [0.548–0.568] | 0.029 ± 0.008 [0.020–0.037] | — | — | — | — | — | 0.003 ± 0.000 [0.003–0.003] | 0.917 ± 0.019 [0.898–0.936] | 0.083 ± 0.013 [0.068–0.091] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b | 2074 | 0.588 | 0.545 | 0.680 | 0.238 | 0.667 | 0.104 | 0.231 | 0.653 | 0.055 | 0.520–0.572 | 0.050–0.159 | 0.025–0.103 | 0.154 | 0.937 | — | — | — | 64.928 | 204.310 |
| kev-4b-ft-s17 | 2074 | 0.905 | 0.900 | 0.962 | 0.075 | 0.259 | 0.034 | 0.074 | 0.255 | 0.026 | 0.864–0.927 | 0.019–0.059 | 0.015–0.052 | 0.857 | 0.943 | — | — | — | 64.933 | 204.336 |
| kev-4b-ft-s18 | 2074 | 0.910 | 0.905 | 0.965 | 0.068 | 0.239 | 0.037 | 0.067 | 0.234 | 0.023 | 0.867–0.933 | 0.019–0.064 | 0.015–0.050 | 0.865 | 0.946 | — | — | — | 64.973 | 201.316 |
| kev-4b-ft-s19 | 2074 | 0.909 | 0.905 | 0.964 | 0.070 | 0.242 | 0.030 | 0.069 | 0.239 | 0.025 | 0.877–0.928 | 0.017–0.052 | 0.015–0.047 | 0.870 | 0.940 | — | — | — | 65.141 | 206.183 |
| FT mean ± SD [range] | — | 0.908 ± 0.003 [0.905–0.910] | 0.903 ± 0.003 [0.900–0.905] | 0.964 ± 0.002 [0.962–0.965] | 0.071 ± 0.003 [0.068–0.075] | 0.247 ± 0.011 [0.239–0.259] | 0.034 ± 0.003 [0.030–0.037] | 0.070 ± 0.003 [0.067–0.074] | 0.243 ± 0.011 [0.234–0.255] | 0.025 ± 0.001 [0.023–0.026] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b | 1597 | 0.302 | 0.308 | 0.557 | 0.693 | 1.139 | 0.114 | 0.669 | 1.103 | 0.049 | 0.271–0.351 | 0.064–0.156 | 0.006–0.091 | — | — | 0.416 | 0.781 | 0.042 | 64.928 | 204.310 |
| kev-4b-ft-s17 | 1597 | 0.795 | 0.800 | 0.888 | 0.319 | 0.533 | 0.105 | 0.297 | 0.487 | 0.047 | 0.748–0.849 | 0.063–0.156 | 0.032–0.091 | — | — | 0.002 | 0.956 | 0.042 | 64.933 | 204.336 |
| kev-4b-ft-s18 | 1597 | 0.795 | 0.799 | 0.888 | 0.308 | 0.509 | 0.107 | 0.286 | 0.461 | 0.047 | 0.750–0.844 | 0.068–0.150 | 0.026–0.087 | — | — | 0.001 | 0.952 | 0.049 | 64.973 | 201.316 |
| kev-4b-ft-s19 | 1597 | 0.791 | 0.795 | 0.879 | 0.315 | 0.507 | 0.096 | 0.297 | 0.475 | 0.057 | 0.746–0.843 | 0.057–0.143 | 0.032–0.101 | — | — | 0.003 | 0.956 | 0.048 | 65.141 | 206.183 |
| FT mean ± SD [range] | — | 0.794 ± 0.002 [0.791–0.795] | 0.798 ± 0.003 [0.795–0.800] | 0.885 ± 0.005 [0.879–0.888] | 0.314 ± 0.005 [0.308–0.319] | 0.516 ± 0.014 [0.507–0.533] | 0.103 ± 0.006 [0.096–0.107] | 0.293 ± 0.006 [0.286–0.297] | 0.474 ± 0.013 [0.461–0.487] | 0.051 ± 0.006 [0.047–0.057] | — | — | — | — | — | 0.002 ± 0.001 [0.001–0.003] | 0.955 ± 0.003 [0.952–0.956] | 0.046 ± 0.004 [0.042–0.049] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b | 2074 | 0.699 | 0.679 | 0.801 | 0.185 | 0.546 | 0.045 | 0.185 | 0.548 | 0.049 | 0.631–0.726 | 0.028–0.081 | 0.034–0.084 | 0.505 | 0.854 | — | — | — | 62.516 | 131.357 |
| kev-9b-ft-s17 | 2074 | 0.908 | 0.905 | 0.962 | 0.074 | 0.288 | 0.048 | 0.071 | 0.251 | 0.019 | 0.879–0.928 | 0.034–0.071 | 0.011–0.042 | 0.873 | 0.937 | — | — | — | 62.793 | 128.975 |
| kev-9b-ft-s18 | 2074 | 0.904 | 0.898 | 0.956 | 0.081 | 0.311 | 0.050 | 0.078 | 0.274 | 0.024 | 0.870–0.920 | 0.037–0.072 | 0.016–0.046 | 0.848 | 0.948 | — | — | — | 62.136 | 129.845 |
| kev-9b-ft-s19 | 2074 | 0.900 | 0.894 | 0.956 | 0.081 | 0.309 | 0.051 | 0.079 | 0.275 | 0.023 | 0.864–0.919 | 0.036–0.074 | 0.015–0.046 | 0.837 | 0.950 | — | — | — | 62.103 | 128.190 |
| FT mean ± SD [range] | — | 0.904 ± 0.004 [0.900–0.908] | 0.899 ± 0.006 [0.894–0.905] | 0.958 ± 0.003 [0.956–0.962] | 0.079 ± 0.004 [0.074–0.081] | 0.303 ± 0.012 [0.288–0.311] | 0.050 ± 0.002 [0.048–0.051] | 0.076 ± 0.004 [0.071–0.079] | 0.267 ± 0.014 [0.251–0.275] | 0.022 ± 0.002 [0.019–0.024] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b | 1597 | 0.494 | 0.503 | 0.569 | 0.629 | 1.033 | 0.101 | 0.620 | 1.018 | 0.084 | 0.475–0.535 | 0.066–0.158 | 0.051–0.136 | — | — | 0.032 | 0.835 | 0.063 | 62.516 | 131.357 |
| kev-9b-ft-s17 | 1597 | 0.820 | 0.824 | 0.919 | 0.275 | 0.446 | 0.085 | 0.261 | 0.421 | 0.052 | 0.775–0.867 | 0.051–0.126 | 0.032–0.088 | — | — | 0.003 | 0.964 | 0.039 | 62.793 | 128.975 |
| kev-9b-ft-s18 | 1597 | 0.801 | 0.806 | 0.905 | 0.298 | 0.491 | 0.100 | 0.277 | 0.443 | 0.040 | 0.759–0.851 | 0.061–0.143 | 0.024–0.080 | — | — | 0.003 | 0.966 | 0.046 | 62.136 | 129.845 |
| kev-9b-ft-s19 | 1597 | 0.809 | 0.813 | 0.908 | 0.282 | 0.457 | 0.093 | 0.265 | 0.424 | 0.056 | 0.764–0.859 | 0.051–0.138 | 0.028–0.096 | — | — | 0.003 | 0.964 | 0.042 | 62.103 | 128.190 |
| FT mean ± SD [range] | — | 0.810 ± 0.009 [0.801–0.820] | 0.815 ± 0.009 [0.806–0.824] | 0.911 ± 0.007 [0.905–0.919] | 0.285 ± 0.012 [0.275–0.298] | 0.465 ± 0.023 [0.446–0.491] | 0.093 ± 0.007 [0.085–0.100] | 0.267 ± 0.008 [0.261–0.277] | 0.430 ± 0.012 [0.421–0.443] | 0.049 ± 0.008 [0.040–0.056] | — | — | — | — | — | 0.003 ± 0.000 [0.003–0.003] | 0.965 ± 0.001 [0.964–0.966] | 0.042 ± 0.004 [0.039–0.046] | — | — |

### laya-english

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-english | 2074 | 0.478 | 0.469 | 0.448 | 0.317 | 0.884 | 0.219 | 0.250 | 0.694 | 0.027 | 0.435–0.506 | 0.176–0.264 | 0.003–0.066 | 0.392 | 0.546 | — | — | — | 27.562 | 29.732 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-english | 1597 | 0.435 | 0.431 | 0.518 | 0.665 | 1.105 | 0.034 | 0.656 | 1.086 | 0.030 | 0.401–0.457 | 0.025–0.071 | 0.013–0.063 | — | — | 0.148 | 0.696 | 0.063 | 27.562 | 29.732 |

### laya-multilingual

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-multilingual | 2074 | 0.524 | 0.545 | 0.545 | 0.350 | 1.097 | 0.283 | 0.250 | 0.693 | 0.015 | 0.520–0.574 | 0.244–0.326 | 0.001–0.051 | 0.739 | 0.351 | — | — | — | 22.767 | 24.561 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-multilingual | 1597 | 0.361 | 0.354 | 0.501 | 0.797 | 1.338 | 0.253 | 0.665 | 1.096 | 0.020 | 0.329–0.381 | 0.214–0.304 | 0.014–0.066 | — | — | 0.264 | 0.781 | 0.096 | 22.767 | 24.561 |

### laya-typed-decisions

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-typed-decisions | 2074 | 0.519 | 0.505 | 0.528 | 0.253 | 0.701 | 0.067 | 0.250 | 0.693 | 0.017 | 0.474–0.541 | 0.030–0.105 | 0.001–0.058 | 0.382 | 0.628 | — | — | — | 27.974 | 43.794 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-typed-decisions | 1597 | 0.361 | 0.360 | 0.542 | 0.677 | 1.121 | 0.055 | 0.668 | 1.102 | 0.028 | 0.334–0.388 | 0.038–0.083 | 0.010–0.053 | — | — | 0.310 | 0.753 | 0.033 | 27.974 | 43.794 |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.115 | 65.892 | 642 | $0.7133 | sv-eval-kev-08b-261003052758001113 |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.251 | 66.545 | 641 | $0.7122 | sv-eval-kev-08b-ft-s17-261003102753254636 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 17.291 | 66.251 | 641 | $0.7122 | sv-eval-kev-08b-ft-s18-261003085422903410 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.2xlarge | us-west-2 | 17.469 | 67.897 | 661 | $0.3672 | sv-eval-kev-08b-ft-s19-261003122339569616 |
| kev-4b | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 64.928 | 204.310 | 1182 | $1.3133 | sv-eval-kev-4b-261003052808948456 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 64.933 | 204.336 | 1159 | $1.2878 | sv-eval-kev-4b-ft-s17-261003093107487315 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 64.973 | 201.316 | 1157 | $1.2856 | sv-eval-kev-4b-ft-s18-261003093435976659 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.4xlarge | us-east-1 | 65.141 | 206.183 | 1158 | $0.9650 | sv-eval-kev-4b-ft-s19-261003133530114674 |
| kev-9b | NVIDIA L40S | ml.g6e.4xlarge | us-west-2 | 62.516 | 131.357 | 1016 | $1.4111 | sv-eval-kev-9b-261003181452376298 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.16xlarge | us-west-2 | 62.793 | 128.975 | 1001 | $3.0586 | sv-eval-kev-9b-ft-s17-261003144255306136 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.4xlarge | us-west-2 | 62.136 | 129.845 | 996 | $1.3833 | sv-eval-kev-9b-ft-s18-261003163836187324 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.4xlarge | us-east-1 | 62.103 | 128.190 | 990 | $1.3750 | sv-eval-kev-9b-ft-s19-261003192655746258 |
| laya-english | NVIDIA A10G | ml.g5.12xlarge | us-east-1 | 27.562 | 29.732 | 616 | $1.5400 | sv-eval-laya-english-261003052822184517 |
| laya-multilingual | NVIDIA A10G | ml.g5.12xlarge | us-west-2 | 22.767 | 24.561 | 590 | $1.4750 | sv-eval-laya-multilingual-261003052832743844 |
| laya-typed-decisions | NVIDIA A10G | ml.g5.16xlarge | us-east-1 | 27.974 | 43.794 | 631 | $1.2269 | sv-eval-laya-typed-decisions-261003052846106178 |

Total billed evaluation cost for the reported arms: **$18.8265 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | noul | granularity | document | 943 | 0.533 | 0.498 | 0.187 | 0.018 | 0.978 |
| kev-0.8b | noul | granularity | paragraph | 754 | 0.552 | 0.500 | 0.177 | 0.024 | 0.976 |
| kev-0.8b | noul | granularity | sentence | 377 | 0.613 | 0.516 | 0.107 | 0.040 | 0.991 |
| kev-0.8b | noul | provenance | generated | 201 | 0.871 | 0.497 | 0.128 | 0.000 | 0.994 |
| kev-0.8b | noul | provenance | human | 1873 | 0.521 | 0.501 | 0.198 | 0.024 | 0.977 |
| kev-0.8b | noul | role | semantic-detection | 2074 | 0.554 | 0.502 | 0.167 | 0.024 | 0.980 |
| kev-0.8b | noul | rule_held_out | False | 1314 | 0.681 | 0.509 | 0.048 | 0.041 | 0.978 |
| kev-0.8b | noul | rule_held_out | True | 760 | 0.336 | 0.499 | 0.381 | 0.010 | 0.988 |
| kev-0.8b | noul | source accuracy | generated | 201 | 0.871 | — | — | — | — |
| kev-0.8b | noul | source accuracy | human | 1873 | 0.521 | — | — | — | — |
| kev-0.8b | choice | granularity | document | 735 | 0.224 | 0.224 | 0.204 | 0.284 | 0.164 |
| kev-0.8b | choice | granularity | paragraph | 547 | 0.199 | 0.140 | 0.239 | 0.317 | 0.103 |
| kev-0.8b | choice | granularity | sentence | 315 | 0.352 | 0.201 | 0.089 | 0.473 | 0.128 |
| kev-0.8b | choice | provenance | generated | 217 | 0.456 | 0.411 | 0.060 | 0.726 | 0.097 |
| kev-0.8b | choice | provenance | human | 1380 | 0.207 | 0.138 | 0.218 | 0.273 | 0.141 |
| kev-0.8b | choice | role | finding-confirmation | 1597 | 0.241 | 0.159 | 0.193 | 0.341 | 0.136 |
| kev-0.8b | choice | rule_held_out | False | 907 | 0.249 | 0.201 | 0.195 | 0.459 | 0.143 |
| kev-0.8b | choice | rule_held_out | True | 690 | 0.230 | 0.190 | 0.190 | 0.271 | 0.109 |
| kev-0.8b | choice | source accuracy | generated | 217 | 0.456 | — | — | — | — |
| kev-0.8b | choice | source accuracy | human | 1380 | 0.207 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | granularity | document | 943 | 0.779 | 0.776 | 0.080 | 0.728 | 0.824 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 754 | 0.800 | 0.795 | 0.061 | 0.753 | 0.837 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 377 | 0.761 | 0.724 | 0.104 | 0.540 | 0.907 |
| kev-0.8b-ft-s17 | noul | provenance | generated | 201 | 0.836 | 0.563 | 0.086 | 0.200 | 0.926 |
| kev-0.8b-ft-s17 | noul | provenance | human | 1873 | 0.778 | 0.776 | 0.075 | 0.720 | 0.831 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 2074 | 0.784 | 0.776 | 0.074 | 0.706 | 0.845 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 1314 | 0.820 | 0.790 | 0.064 | 0.709 | 0.871 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 760 | 0.721 | 0.730 | 0.109 | 0.704 | 0.755 |
| kev-0.8b-ft-s17 | noul | source accuracy | generated | 201 | 0.836 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 1873 | 0.778 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 735 | 0.731 | 0.731 | 0.054 | 0.630 | 0.833 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 547 | 0.762 | 0.837 | 0.071 | 0.695 | 0.817 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 315 | 0.714 | 0.486 | 0.098 | 0.688 | 0.771 |
| kev-0.8b-ft-s17 | choice | provenance | generated | 217 | 0.631 | 0.652 | 0.199 | 0.508 | 0.796 |
| kev-0.8b-ft-s17 | choice | provenance | human | 1380 | 0.755 | 0.671 | 0.044 | 0.692 | 0.821 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.738 | 0.661 | 0.064 | 0.664 | 0.818 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 907 | 0.772 | 0.666 | 0.064 | 0.679 | 0.820 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 690 | 0.694 | 0.733 | 0.078 | 0.655 | 0.810 |
| kev-0.8b-ft-s17 | choice | source accuracy | generated | 217 | 0.631 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 1380 | 0.755 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 943 | 0.770 | 0.765 | 0.060 | 0.700 | 0.830 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 754 | 0.798 | 0.792 | 0.056 | 0.729 | 0.854 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 377 | 0.761 | 0.725 | 0.102 | 0.547 | 0.903 |
| kev-0.8b-ft-s18 | noul | provenance | generated | 201 | 0.856 | 0.592 | 0.075 | 0.240 | 0.943 |
| kev-0.8b-ft-s18 | noul | provenance | human | 1873 | 0.770 | 0.768 | 0.061 | 0.698 | 0.837 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 2074 | 0.779 | 0.769 | 0.062 | 0.686 | 0.853 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 1314 | 0.828 | 0.803 | 0.039 | 0.736 | 0.871 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 760 | 0.693 | 0.718 | 0.101 | 0.645 | 0.791 |
| kev-0.8b-ft-s18 | noul | source accuracy | generated | 201 | 0.856 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 1873 | 0.770 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 735 | 0.747 | 0.747 | 0.025 | 0.689 | 0.805 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 547 | 0.735 | 0.817 | 0.052 | 0.642 | 0.810 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 315 | 0.711 | 0.474 | 0.122 | 0.717 | 0.706 |
| kev-0.8b-ft-s18 | choice | provenance | generated | 217 | 0.631 | 0.647 | 0.191 | 0.540 | 0.753 |
| kev-0.8b-ft-s18 | choice | provenance | human | 1380 | 0.752 | 0.669 | 0.025 | 0.707 | 0.799 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.736 | 0.658 | 0.048 | 0.682 | 0.793 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 907 | 0.759 | 0.657 | 0.050 | 0.666 | 0.807 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 690 | 0.706 | 0.719 | 0.073 | 0.692 | 0.747 |
| kev-0.8b-ft-s18 | choice | source accuracy | generated | 217 | 0.631 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 1380 | 0.752 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 943 | 0.772 | 0.767 | 0.067 | 0.698 | 0.836 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 754 | 0.804 | 0.798 | 0.063 | 0.741 | 0.854 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 377 | 0.796 | 0.763 | 0.077 | 0.600 | 0.925 |
| kev-0.8b-ft-s19 | noul | provenance | generated | 201 | 0.866 | 0.580 | 0.081 | 0.200 | 0.960 |
| kev-0.8b-ft-s19 | noul | provenance | human | 1873 | 0.779 | 0.777 | 0.064 | 0.712 | 0.842 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 2074 | 0.788 | 0.779 | 0.064 | 0.698 | 0.860 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 1314 | 0.825 | 0.792 | 0.046 | 0.702 | 0.882 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 760 | 0.724 | 0.738 | 0.109 | 0.694 | 0.783 |
| kev-0.8b-ft-s19 | noul | source accuracy | generated | 201 | 0.866 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 1873 | 0.779 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 735 | 0.771 | 0.772 | 0.053 | 0.708 | 0.836 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 547 | 0.761 | 0.835 | 0.050 | 0.675 | 0.830 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 315 | 0.708 | 0.480 | 0.088 | 0.688 | 0.752 |
| kev-0.8b-ft-s19 | choice | provenance | generated | 217 | 0.608 | 0.629 | 0.206 | 0.484 | 0.774 |
| kev-0.8b-ft-s19 | choice | provenance | human | 1380 | 0.778 | 0.686 | 0.021 | 0.730 | 0.828 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.755 | 0.672 | 0.041 | 0.693 | 0.822 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 907 | 0.773 | 0.662 | 0.040 | 0.649 | 0.837 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 690 | 0.732 | 0.745 | 0.063 | 0.719 | 0.770 |
| kev-0.8b-ft-s19 | choice | source accuracy | generated | 217 | 0.608 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 1380 | 0.778 | — | — | — | — |
| kev-4b | noul | granularity | document | 943 | 0.573 | 0.542 | 0.125 | 0.126 | 0.958 |
| kev-4b | noul | granularity | paragraph | 754 | 0.562 | 0.519 | 0.134 | 0.122 | 0.916 |
| kev-4b | noul | granularity | sentence | 377 | 0.679 | 0.616 | 0.070 | 0.307 | 0.925 |
| kev-4b | noul | provenance | generated | 201 | 0.816 | 0.535 | 0.126 | 0.160 | 0.909 |
| kev-4b | noul | provenance | human | 1873 | 0.564 | 0.548 | 0.128 | 0.154 | 0.942 |
| kev-4b | noul | role | semantic-detection | 2074 | 0.588 | 0.545 | 0.104 | 0.154 | 0.937 |
| kev-4b | noul | rule_held_out | False | 1314 | 0.680 | 0.536 | 0.035 | 0.142 | 0.930 |
| kev-4b | noul | rule_held_out | True | 760 | 0.429 | 0.562 | 0.255 | 0.164 | 0.960 |
| kev-4b | noul | source accuracy | generated | 201 | 0.816 | — | — | — | — |
| kev-4b | noul | source accuracy | human | 1873 | 0.564 | — | — | — | — |
| kev-4b | choice | granularity | document | 735 | 0.356 | 0.358 | 0.060 | 0.200 | 0.515 |
| kev-4b | choice | granularity | paragraph | 547 | 0.293 | 0.183 | 0.127 | 0.085 | 0.463 |
| kev-4b | choice | granularity | sentence | 315 | 0.194 | 0.171 | 0.241 | 0.054 | 0.459 |
| kev-4b | choice | provenance | generated | 217 | 0.364 | 0.374 | 0.054 | 0.306 | 0.441 |
| kev-4b | choice | provenance | human | 1380 | 0.293 | 0.197 | 0.125 | 0.098 | 0.493 |
| kev-4b | choice | role | finding-confirmation | 1597 | 0.302 | 0.205 | 0.114 | 0.129 | 0.487 |
| kev-4b | choice | rule_held_out | False | 907 | 0.387 | 0.227 | 0.033 | 0.197 | 0.485 |
| kev-4b | choice | rule_held_out | True | 690 | 0.191 | 0.292 | 0.225 | 0.089 | 0.494 |
| kev-4b | choice | source accuracy | generated | 217 | 0.364 | — | — | — | — |
| kev-4b | choice | source accuracy | human | 1380 | 0.293 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 943 | 0.901 | 0.898 | 0.040 | 0.858 | 0.939 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 754 | 0.914 | 0.911 | 0.035 | 0.884 | 0.938 |
| kev-4b-ft-s17 | noul | granularity | sentence | 377 | 0.894 | 0.877 | 0.037 | 0.793 | 0.960 |
| kev-4b-ft-s17 | noul | provenance | generated | 201 | 0.846 | 0.603 | 0.094 | 0.280 | 0.926 |
| kev-4b-ft-s17 | noul | provenance | human | 1873 | 0.911 | 0.909 | 0.030 | 0.873 | 0.946 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 2074 | 0.905 | 0.900 | 0.034 | 0.857 | 0.943 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 1314 | 0.907 | 0.887 | 0.038 | 0.832 | 0.942 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 760 | 0.900 | 0.911 | 0.035 | 0.878 | 0.945 |
| kev-4b-ft-s17 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-4b-ft-s17 | noul | source accuracy | human | 1873 | 0.911 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 735 | 0.795 | 0.795 | 0.113 | 0.684 | 0.907 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 547 | 0.810 | 0.532 | 0.095 | 0.671 | 0.927 |
| kev-4b-ft-s17 | choice | granularity | sentence | 315 | 0.771 | 0.537 | 0.137 | 0.702 | 0.908 |
| kev-4b-ft-s17 | choice | provenance | generated | 217 | 0.613 | 0.641 | 0.264 | 0.444 | 0.839 |
| kev-4b-ft-s17 | choice | provenance | human | 1380 | 0.824 | 0.551 | 0.085 | 0.727 | 0.925 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.795 | 0.533 | 0.105 | 0.685 | 0.915 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 907 | 0.830 | 0.526 | 0.081 | 0.659 | 0.920 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 690 | 0.749 | 0.798 | 0.151 | 0.700 | 0.897 |
| kev-4b-ft-s17 | choice | source accuracy | generated | 217 | 0.613 | — | — | — | — |
| kev-4b-ft-s17 | choice | source accuracy | human | 1380 | 0.824 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 943 | 0.905 | 0.902 | 0.041 | 0.863 | 0.941 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 754 | 0.918 | 0.915 | 0.032 | 0.887 | 0.943 |
| kev-4b-ft-s18 | noul | granularity | sentence | 377 | 0.907 | 0.892 | 0.041 | 0.820 | 0.965 |
| kev-4b-ft-s18 | noul | provenance | generated | 201 | 0.866 | 0.614 | 0.093 | 0.280 | 0.949 |
| kev-4b-ft-s18 | noul | provenance | human | 1873 | 0.915 | 0.913 | 0.032 | 0.881 | 0.946 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 2074 | 0.910 | 0.905 | 0.037 | 0.865 | 0.946 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 1314 | 0.909 | 0.887 | 0.040 | 0.827 | 0.947 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 760 | 0.912 | 0.920 | 0.032 | 0.895 | 0.945 |
| kev-4b-ft-s18 | noul | source accuracy | generated | 201 | 0.866 | — | — | — | — |
| kev-4b-ft-s18 | noul | source accuracy | human | 1873 | 0.915 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 735 | 0.810 | 0.810 | 0.090 | 0.714 | 0.907 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 547 | 0.799 | 0.526 | 0.110 | 0.679 | 0.900 |
| kev-4b-ft-s18 | choice | granularity | sentence | 315 | 0.756 | 0.522 | 0.145 | 0.702 | 0.862 |
| kev-4b-ft-s18 | choice | provenance | generated | 217 | 0.594 | 0.618 | 0.288 | 0.452 | 0.785 |
| kev-4b-ft-s18 | choice | provenance | human | 1380 | 0.827 | 0.553 | 0.081 | 0.745 | 0.913 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.795 | 0.533 | 0.107 | 0.700 | 0.898 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 907 | 0.817 | 0.518 | 0.095 | 0.649 | 0.905 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 690 | 0.767 | 0.802 | 0.125 | 0.731 | 0.874 |
| kev-4b-ft-s18 | choice | source accuracy | generated | 217 | 0.594 | — | — | — | — |
| kev-4b-ft-s18 | choice | source accuracy | human | 1380 | 0.827 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 943 | 0.900 | 0.898 | 0.039 | 0.860 | 0.935 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 754 | 0.918 | 0.916 | 0.026 | 0.896 | 0.935 |
| kev-4b-ft-s19 | noul | granularity | sentence | 377 | 0.912 | 0.900 | 0.028 | 0.840 | 0.960 |
| kev-4b-ft-s19 | noul | provenance | generated | 201 | 0.836 | 0.563 | 0.098 | 0.200 | 0.926 |
| kev-4b-ft-s19 | noul | provenance | human | 1873 | 0.917 | 0.916 | 0.025 | 0.889 | 0.943 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 2074 | 0.909 | 0.905 | 0.030 | 0.870 | 0.940 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 1314 | 0.905 | 0.881 | 0.037 | 0.815 | 0.947 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 760 | 0.916 | 0.916 | 0.027 | 0.915 | 0.917 |
| kev-4b-ft-s19 | noul | source accuracy | generated | 201 | 0.836 | — | — | — | — |
| kev-4b-ft-s19 | noul | source accuracy | human | 1873 | 0.917 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 735 | 0.795 | 0.795 | 0.099 | 0.686 | 0.904 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 547 | 0.808 | 0.864 | 0.084 | 0.679 | 0.913 |
| kev-4b-ft-s19 | choice | granularity | sentence | 315 | 0.756 | 0.520 | 0.128 | 0.707 | 0.853 |
| kev-4b-ft-s19 | choice | provenance | generated | 217 | 0.585 | 0.610 | 0.274 | 0.435 | 0.785 |
| kev-4b-ft-s19 | choice | provenance | human | 1380 | 0.824 | 0.717 | 0.070 | 0.735 | 0.916 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.791 | 0.697 | 0.096 | 0.689 | 0.901 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 907 | 0.821 | 0.687 | 0.070 | 0.652 | 0.908 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 690 | 0.752 | 0.792 | 0.132 | 0.711 | 0.874 |
| kev-4b-ft-s19 | choice | source accuracy | generated | 217 | 0.585 | — | — | — | — |
| kev-4b-ft-s19 | choice | source accuracy | human | 1380 | 0.824 | — | — | — | — |
| kev-9b | noul | granularity | document | 943 | 0.674 | 0.658 | 0.051 | 0.439 | 0.877 |
| kev-9b | noul | granularity | paragraph | 754 | 0.675 | 0.658 | 0.069 | 0.500 | 0.816 |
| kev-9b | noul | granularity | sentence | 377 | 0.806 | 0.789 | 0.080 | 0.707 | 0.872 |
| kev-9b | noul | provenance | generated | 201 | 0.761 | 0.572 | 0.060 | 0.320 | 0.824 |
| kev-9b | noul | provenance | human | 1873 | 0.692 | 0.685 | 0.051 | 0.510 | 0.859 |
| kev-9b | noul | role | semantic-detection | 2074 | 0.699 | 0.679 | 0.045 | 0.505 | 0.854 |
| kev-9b | noul | rule_held_out | False | 1314 | 0.724 | 0.642 | 0.046 | 0.421 | 0.864 |
| kev-9b | noul | rule_held_out | True | 760 | 0.655 | 0.696 | 0.063 | 0.574 | 0.818 |
| kev-9b | noul | source accuracy | generated | 201 | 0.761 | — | — | — | — |
| kev-9b | noul | source accuracy | human | 1873 | 0.692 | — | — | — | — |
| kev-9b | choice | granularity | document | 735 | 0.505 | 0.507 | 0.088 | 0.238 | 0.775 |
| kev-9b | choice | granularity | paragraph | 547 | 0.516 | 0.324 | 0.074 | 0.179 | 0.793 |
| kev-9b | choice | granularity | sentence | 315 | 0.432 | 0.354 | 0.201 | 0.210 | 0.853 |
| kev-9b | choice | provenance | generated | 217 | 0.525 | 0.552 | 0.141 | 0.363 | 0.742 |
| kev-9b | choice | provenance | human | 1380 | 0.489 | 0.329 | 0.103 | 0.187 | 0.800 |
| kev-9b | choice | role | finding-confirmation | 1597 | 0.494 | 0.335 | 0.101 | 0.213 | 0.793 |
| kev-9b | choice | rule_held_out | False | 907 | 0.603 | 0.347 | 0.065 | 0.262 | 0.778 |
| kev-9b | choice | rule_held_out | True | 690 | 0.351 | 0.514 | 0.257 | 0.184 | 0.845 |
| kev-9b | choice | source accuracy | generated | 217 | 0.525 | — | — | — | — |
| kev-9b | choice | source accuracy | human | 1380 | 0.489 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 943 | 0.913 | 0.911 | 0.044 | 0.888 | 0.935 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 754 | 0.906 | 0.904 | 0.053 | 0.884 | 0.923 |
| kev-9b-ft-s17 | noul | granularity | sentence | 377 | 0.902 | 0.886 | 0.060 | 0.807 | 0.965 |
| kev-9b-ft-s17 | noul | provenance | generated | 201 | 0.846 | 0.569 | 0.122 | 0.200 | 0.938 |
| kev-9b-ft-s17 | noul | provenance | human | 1873 | 0.915 | 0.914 | 0.041 | 0.892 | 0.936 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 2074 | 0.908 | 0.905 | 0.048 | 0.873 | 0.937 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 1314 | 0.907 | 0.892 | 0.053 | 0.851 | 0.933 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 760 | 0.911 | 0.920 | 0.050 | 0.892 | 0.949 |
| kev-9b-ft-s17 | noul | source accuracy | generated | 201 | 0.846 | — | — | — | — |
| kev-9b-ft-s17 | noul | source accuracy | human | 1873 | 0.915 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 735 | 0.838 | 0.839 | 0.075 | 0.741 | 0.937 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 547 | 0.823 | 0.540 | 0.089 | 0.663 | 0.957 |
| kev-9b-ft-s17 | choice | granularity | sentence | 315 | 0.771 | 0.544 | 0.137 | 0.678 | 0.954 |
| kev-9b-ft-s17 | choice | provenance | generated | 217 | 0.604 | 0.641 | 0.264 | 0.379 | 0.903 |
| kev-9b-ft-s17 | choice | provenance | human | 1380 | 0.854 | 0.571 | 0.057 | 0.759 | 0.953 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 1597 | 0.820 | 0.550 | 0.085 | 0.702 | 0.947 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 907 | 0.848 | 0.536 | 0.068 | 0.662 | 0.945 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 690 | 0.783 | 0.839 | 0.109 | 0.725 | 0.954 |
| kev-9b-ft-s17 | choice | source accuracy | generated | 217 | 0.604 | — | — | — | — |
| kev-9b-ft-s17 | choice | source accuracy | human | 1380 | 0.854 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 943 | 0.910 | 0.907 | 0.046 | 0.867 | 0.947 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 754 | 0.891 | 0.886 | 0.062 | 0.839 | 0.933 |
| kev-9b-ft-s18 | noul | granularity | sentence | 377 | 0.912 | 0.896 | 0.063 | 0.813 | 0.978 |
| kev-9b-ft-s18 | noul | provenance | generated | 201 | 0.861 | 0.560 | 0.124 | 0.160 | 0.960 |
| kev-9b-ft-s18 | noul | provenance | human | 1873 | 0.908 | 0.907 | 0.044 | 0.867 | 0.946 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 2074 | 0.904 | 0.898 | 0.050 | 0.848 | 0.948 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 1314 | 0.900 | 0.874 | 0.058 | 0.803 | 0.944 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 760 | 0.911 | 0.923 | 0.045 | 0.886 | 0.960 |
| kev-9b-ft-s18 | noul | source accuracy | generated | 201 | 0.861 | — | — | — | — |
| kev-9b-ft-s18 | noul | source accuracy | human | 1873 | 0.908 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 735 | 0.815 | 0.816 | 0.087 | 0.703 | 0.929 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 547 | 0.804 | 0.527 | 0.100 | 0.634 | 0.947 |
| kev-9b-ft-s18 | choice | granularity | sentence | 315 | 0.762 | 0.538 | 0.147 | 0.668 | 0.945 |
| kev-9b-ft-s18 | choice | provenance | generated | 217 | 0.590 | 0.628 | 0.299 | 0.363 | 0.892 |
| kev-9b-ft-s18 | choice | provenance | human | 1380 | 0.834 | 0.558 | 0.073 | 0.729 | 0.944 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 1597 | 0.801 | 0.537 | 0.100 | 0.674 | 0.938 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 907 | 0.831 | 0.521 | 0.079 | 0.623 | 0.940 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 690 | 0.761 | 0.817 | 0.132 | 0.703 | 0.931 |
| kev-9b-ft-s18 | choice | source accuracy | generated | 217 | 0.590 | — | — | — | — |
| kev-9b-ft-s18 | choice | source accuracy | human | 1380 | 0.834 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 943 | 0.915 | 0.912 | 0.045 | 0.867 | 0.957 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 754 | 0.887 | 0.881 | 0.066 | 0.827 | 0.935 |
| kev-9b-ft-s19 | noul | granularity | sentence | 377 | 0.886 | 0.867 | 0.057 | 0.773 | 0.960 |
| kev-9b-ft-s19 | noul | provenance | generated | 201 | 0.851 | 0.589 | 0.119 | 0.240 | 0.938 |
| kev-9b-ft-s19 | noul | provenance | human | 1873 | 0.905 | 0.903 | 0.045 | 0.854 | 0.952 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 2074 | 0.900 | 0.894 | 0.051 | 0.837 | 0.950 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 1314 | 0.911 | 0.887 | 0.052 | 0.822 | 0.952 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 760 | 0.880 | 0.895 | 0.066 | 0.850 | 0.941 |
| kev-9b-ft-s19 | noul | source accuracy | generated | 201 | 0.851 | — | — | — | — |
| kev-9b-ft-s19 | noul | source accuracy | human | 1873 | 0.905 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 735 | 0.827 | 0.828 | 0.078 | 0.727 | 0.929 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 547 | 0.814 | 0.535 | 0.090 | 0.671 | 0.933 |
| kev-9b-ft-s19 | choice | granularity | sentence | 315 | 0.759 | 0.533 | 0.139 | 0.673 | 0.927 |
| kev-9b-ft-s19 | choice | provenance | generated | 217 | 0.590 | 0.626 | 0.272 | 0.371 | 0.882 |
| kev-9b-ft-s19 | choice | provenance | human | 1380 | 0.843 | 0.564 | 0.065 | 0.755 | 0.937 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 1597 | 0.809 | 0.542 | 0.093 | 0.697 | 0.930 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 907 | 0.843 | 0.534 | 0.062 | 0.662 | 0.938 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 690 | 0.764 | 0.810 | 0.134 | 0.717 | 0.902 |
| kev-9b-ft-s19 | choice | source accuracy | generated | 217 | 0.590 | — | — | — | — |
| kev-9b-ft-s19 | choice | source accuracy | human | 1380 | 0.843 | — | — | — | — |
| laya-english | noul | granularity | document | 943 | 0.483 | 0.483 | 0.210 | 0.490 | 0.476 |
| laya-english | noul | granularity | paragraph | 754 | 0.456 | 0.447 | 0.234 | 0.360 | 0.533 |
| laya-english | noul | granularity | sentence | 377 | 0.509 | 0.453 | 0.224 | 0.180 | 0.727 |
| laya-english | noul | provenance | generated | 201 | 0.488 | 0.639 | 0.221 | 0.840 | 0.438 |
| laya-english | noul | provenance | human | 1873 | 0.477 | 0.473 | 0.221 | 0.380 | 0.566 |
| laya-english | noul | role | semantic-detection | 2074 | 0.478 | 0.469 | 0.219 | 0.392 | 0.546 |
| laya-english | noul | rule_held_out | False | 1314 | 0.516 | 0.498 | 0.180 | 0.450 | 0.547 |
| laya-english | noul | rule_held_out | True | 760 | 0.412 | 0.445 | 0.287 | 0.345 | 0.545 |
| laya-english | noul | source accuracy | generated | 201 | 0.488 | — | — | — | — |
| laya-english | noul | source accuracy | human | 1873 | 0.477 | — | — | — | — |
| laya-english | choice | granularity | document | 735 | 0.424 | 0.424 | 0.065 | 0.557 | 0.290 |
| laya-english | choice | granularity | paragraph | 547 | 0.437 | 0.302 | 0.022 | 0.610 | 0.297 |
| laya-english | choice | granularity | sentence | 315 | 0.454 | 0.623 | 0.068 | 0.493 | 0.376 |
| laya-english | choice | provenance | generated | 217 | 0.396 | 0.391 | 0.087 | 0.427 | 0.355 |
| laya-english | choice | provenance | human | 1380 | 0.441 | 0.459 | 0.032 | 0.580 | 0.298 |
| laya-english | choice | role | finding-confirmation | 1597 | 0.435 | 0.454 | 0.034 | 0.557 | 0.305 |
| laya-english | choice | rule_held_out | False | 907 | 0.379 | 0.444 | 0.086 | 0.531 | 0.302 |
| laya-english | choice | rule_held_out | True | 690 | 0.507 | 0.444 | 0.090 | 0.572 | 0.316 |
| laya-english | choice | source accuracy | generated | 217 | 0.396 | — | — | — | — |
| laya-english | choice | source accuracy | human | 1380 | 0.441 | — | — | — | — |
| laya-multilingual | noul | granularity | document | 943 | 0.504 | 0.527 | 0.338 | 0.842 | 0.211 |
| laya-multilingual | noul | granularity | paragraph | 754 | 0.516 | 0.535 | 0.267 | 0.711 | 0.359 |
| laya-multilingual | noul | granularity | sentence | 377 | 0.589 | 0.574 | 0.205 | 0.500 | 0.648 |
| laya-multilingual | noul | provenance | generated | 201 | 0.313 | 0.539 | 0.519 | 0.840 | 0.239 |
| laya-multilingual | noul | provenance | human | 1873 | 0.546 | 0.554 | 0.259 | 0.736 | 0.371 |
| laya-multilingual | noul | role | semantic-detection | 2074 | 0.524 | 0.545 | 0.283 | 0.739 | 0.351 |
| laya-multilingual | noul | rule_held_out | False | 1314 | 0.494 | 0.560 | 0.316 | 0.740 | 0.380 |
| laya-multilingual | noul | rule_held_out | True | 760 | 0.575 | 0.493 | 0.225 | 0.738 | 0.249 |
| laya-multilingual | noul | source accuracy | generated | 201 | 0.313 | — | — | — | — |
| laya-multilingual | noul | source accuracy | human | 1873 | 0.546 | — | — | — | — |
| laya-multilingual | choice | granularity | document | 735 | 0.476 | 0.474 | 0.146 | 0.835 | 0.112 |
| laya-multilingual | choice | granularity | paragraph | 547 | 0.256 | 0.183 | 0.344 | 0.451 | 0.097 |
| laya-multilingual | choice | granularity | sentence | 315 | 0.273 | 0.174 | 0.351 | 0.302 | 0.220 |
| laya-multilingual | choice | provenance | generated | 217 | 0.263 | 0.235 | 0.358 | 0.427 | 0.043 |
| laya-multilingual | choice | provenance | human | 1380 | 0.376 | 0.249 | 0.236 | 0.615 | 0.132 |
| laya-multilingual | choice | role | finding-confirmation | 1597 | 0.361 | 0.236 | 0.253 | 0.587 | 0.121 |
| laya-multilingual | choice | rule_held_out | False | 907 | 0.251 | 0.212 | 0.359 | 0.518 | 0.117 |
| laya-multilingual | choice | rule_held_out | True | 690 | 0.504 | 0.383 | 0.142 | 0.628 | 0.138 |
| laya-multilingual | choice | source accuracy | generated | 217 | 0.263 | — | — | — | — |
| laya-multilingual | choice | source accuracy | human | 1380 | 0.376 | — | — | — | — |
| laya-typed-decisions | noul | granularity | document | 943 | 0.496 | 0.497 | 0.080 | 0.506 | 0.488 |
| laya-typed-decisions | noul | granularity | paragraph | 754 | 0.525 | 0.506 | 0.060 | 0.327 | 0.684 |
| laya-typed-decisions | noul | granularity | sentence | 377 | 0.562 | 0.492 | 0.073 | 0.147 | 0.837 |
| laya-typed-decisions | noul | provenance | generated | 201 | 0.587 | 0.661 | 0.079 | 0.760 | 0.562 |
| laya-typed-decisions | noul | provenance | human | 1873 | 0.511 | 0.506 | 0.073 | 0.372 | 0.640 |
| laya-typed-decisions | noul | role | semantic-detection | 2074 | 0.519 | 0.505 | 0.067 | 0.382 | 0.628 |
| laya-typed-decisions | noul | rule_held_out | False | 1314 | 0.563 | 0.536 | 0.027 | 0.462 | 0.610 |
| laya-typed-decisions | noul | rule_held_out | True | 760 | 0.442 | 0.505 | 0.139 | 0.318 | 0.692 |
| laya-typed-decisions | noul | source accuracy | generated | 201 | 0.587 | — | — | — | — |
| laya-typed-decisions | noul | source accuracy | human | 1873 | 0.511 | — | — | — | — |
| laya-typed-decisions | choice | granularity | document | 735 | 0.363 | 0.364 | 0.053 | 0.316 | 0.411 |
| laya-typed-decisions | choice | granularity | paragraph | 547 | 0.373 | 0.255 | 0.065 | 0.476 | 0.290 |
| laya-typed-decisions | choice | granularity | sentence | 315 | 0.333 | 0.525 | 0.093 | 0.429 | 0.147 |
| laya-typed-decisions | choice | provenance | generated | 217 | 0.387 | 0.376 | 0.049 | 0.452 | 0.301 |
| laya-typed-decisions | choice | provenance | human | 1380 | 0.357 | 0.404 | 0.063 | 0.382 | 0.330 |
| laya-typed-decisions | choice | role | finding-confirmation | 1597 | 0.361 | 0.406 | 0.055 | 0.392 | 0.327 |
| laya-typed-decisions | choice | rule_held_out | False | 907 | 0.372 | 0.426 | 0.065 | 0.443 | 0.335 |
| laya-typed-decisions | choice | rule_held_out | True | 690 | 0.346 | 0.331 | 0.066 | 0.362 | 0.299 |
| laya-typed-decisions | choice | source accuracy | generated | 217 | 0.387 | — | — | — | — |
| laya-typed-decisions | choice | source accuracy | human | 1380 | 0.357 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 1095 | 0.337 | 33 | 0.502 | 0.536 | 0.535 |
| kev-0.8b-ft-s17 | 1095 | 0.362 | 33 | 0.776 | 0.790 | 0.779 |
| kev-0.8b-ft-s18 | 1095 | 0.429 | 33 | 0.769 | 0.780 | 0.766 |
| kev-0.8b-ft-s19 | 1095 | 0.441 | 33 | 0.779 | 0.782 | 0.772 |
| kev-4b | 1095 | 0.288 | 33 | 0.545 | 0.629 | 0.635 |
| kev-4b-ft-s17 | 1095 | 0.230 | 33 | 0.900 | 0.905 | 0.903 |
| kev-4b-ft-s18 | 1095 | 0.318 | 33 | 0.905 | 0.916 | 0.906 |
| kev-4b-ft-s19 | 1095 | 0.246 | 33 | 0.905 | 0.905 | 0.902 |
| kev-9b | 1095 | 0.397 | 33 | 0.679 | 0.724 | 0.722 |
| kev-9b-ft-s17 | 1095 | 0.580 | 33 | 0.905 | 0.902 | 0.892 |
| kev-9b-ft-s18 | 1095 | 0.428 | 33 | 0.898 | 0.899 | 0.894 |
| kev-9b-ft-s19 | 1095 | 0.374 | 33 | 0.894 | 0.898 | 0.883 |
| laya-english | 1095 | 0.909 | 33 | 0.469 | 0.501 | 0.436 |
| laya-multilingual | 1095 | 0.085 | 33 | 0.545 | 0.514 | 0.564 |
| laya-typed-decisions | 1095 | 0.467 | 33 | 0.506 | 0.534 | 0.534 |

## Interpretation and caveats

- Test label origins: construction (3092), human-adjudication (258), llm-review-consensus (321). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice insufficient-context=2, no-defect=821, real-defect=774; yes/no False=1151, True=923. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.30 finding-confirmation, κ=0.30 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
