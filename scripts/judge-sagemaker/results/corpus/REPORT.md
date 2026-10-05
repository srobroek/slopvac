# Corpus evaluation report: `corpus`

## Status

- Pre-v4 baseline. v4 rebuilds the judge items against the merged lint rules (main 7544c168e0: curly-quotes and uniform-paragraph-mass retired, about 13 rules narrowed) and the human-labelled rows, then re-tests every arm on the rebuilt items; v4 scores are not comparable with this test export.

## Dataset and coverage

- Campaign: `corpus-20260929-s17-v2`. Round 1 (default campaign) on the export named in resources.json: six base arms plus three-seed fine-tunes of Kev 0.8B, 4B, 9B and Laya typed-decisions.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 18 of 18 required (`kev-0.8b`, `kev-4b`, `kev-9b`, `laya-english`, `laya-multilingual`, `laya-typed-decisions`, `kev-0.8b-ft-s17`, `kev-0.8b-ft-s18`, `kev-0.8b-ft-s19`, `kev-4b-ft-s17`, `kev-4b-ft-s18`, `kev-4b-ft-s19`, `kev-9b-ft-s17`, `kev-9b-ft-s18`, `kev-9b-ft-s19`, `laya-typed-decisions-ft-s17`, `laya-typed-decisions-ft-s18`, `laya-typed-decisions-ft-s19`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 97 of 125 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 37 examples; SHA-256 `b78f4e52f4fdd09e4d76dab93e386337ee94a6b17a0d7c569dd9aa387503c452`.
- Test: 484 examples; SHA-256 `794e0af7205c2d0b5495964cb4efa0d905e4f54a2ea9f287ada99952ba4a3436`.
- Test composition: label origins `construction`=484; choice labels real-defect=18; yes/no labels False=334, True=132.

## Headline by role

Each arm's numbers come from `results/corpus/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 18 (real-defect=18, no-defect=0).

No test item has the class behind no-defect recall, so that recall is undefined and balanced accuracy reduces to the recall of the class present.

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.167 | 0.000–0.353 | 0.167 | — | 0.253 | 0.168 | NVIDIA L4 | 16.246 | $0.2764 |
| kev-0.8b-ft-s17 | 0.556 | 0.294–0.789 | 0.556 | — | 0.415 | 0.256 | NVIDIA A10G | 13.256 | $0.5111 |
| kev-0.8b-ft-s18 | 0.611 | 0.353–0.833 | 0.611 | — | 0.263 | 0.194 | NVIDIA A10G | 13.252 | $0.3825 |
| kev-0.8b-ft-s19 | 0.611 | 0.353–0.842 | 0.611 | — | 0.291 | 0.193 | NVIDIA A10G | 13.241 | $0.5011 |
| kev-0.8b FT mean ± SD [range] | 0.593 ± 0.032 [0.556–0.611] | — | 0.593 ± 0.032 [0.556–0.611] | — | 0.323 ± 0.081 [0.263–0.415] | 0.214 ± 0.036 [0.193–0.256] | — | — | — |
| kev-4b | 0.500 | 0.294–0.706 | 0.500 | — | 0.186 | 0.320 | NVIDIA A10G | 47.498 | $0.4125 |
| kev-4b-ft-s17 | 0.722 | 0.471–0.895 | 0.722 | — | 0.224 | 0.207 | NVIDIA A10G | 47.252 | $1.2025 |
| kev-4b-ft-s18 | 0.722 | 0.471–0.895 | 0.722 | — | 0.244 | 0.256 | NVIDIA A10G | 47.544 | $0.4250 |
| kev-4b-ft-s19 | 0.667 | 0.450–0.882 | 0.667 | — | 0.265 | 0.322 | NVIDIA A10G | 47.285 | $0.4175 |
| kev-4b FT mean ± SD [range] | 0.704 ± 0.032 [0.667–0.722] | — | 0.704 ± 0.032 [0.667–0.722] | — | 0.244 ± 0.020 [0.224–0.265] | 0.262 ± 0.058 [0.207–0.322] | — | — | — |
| kev-9b | 0.833 | 0.647–1.000 | 0.833 | — | 0.265 | 0.165 | NVIDIA L40S | 55.068 | $0.8944 |
| kev-9b-ft-s17 | 0.667 | 0.450–0.882 | 0.667 | — | 0.297 | 0.333 | NVIDIA L40S | 54.672 | $0.6178 |
| kev-9b-ft-s18 | 0.722 | 0.529–0.941 | 0.722 | — | 0.248 | 0.278 | NVIDIA L40S | 54.768 | $0.6472 |
| kev-9b-ft-s19 | 0.667 | 0.450–0.882 | 0.667 | — | 0.317 | 0.317 | NVIDIA L40S | 55.227 | $0.8653 |
| kev-9b FT mean ± SD [range] | 0.685 ± 0.032 [0.667–0.722] | — | 0.685 ± 0.032 [0.667–0.722] | — | 0.287 ± 0.035 [0.248–0.317] | 0.309 ± 0.029 [0.278–0.333] | — | — | — |
| laya-english | 0.278 | 0.095–0.529 | 0.278 | — | 0.294 | 0.062 | NVIDIA A10G | 28.347 | $0.3542 |
| laya-multilingual | 0.056 | 0.000–0.176 | 0.056 | — | 0.523 | 0.301 | NVIDIA A10G | 23.215 | $0.4389 |
| laya-typed-decisions | 0.167 | 0.000–0.353 | 0.167 | — | 0.279 | 0.306 | NVIDIA A10G | 27.503 | $0.4478 |
| laya-typed-decisions-ft-s17 | 0.722 | 0.529–0.906 | 0.722 | — | 0.179 | 0.192 | NVIDIA A10G | 28.206 | $0.2228 |
| laya-typed-decisions-ft-s18 | 0.556 | 0.333–0.778 | 0.556 | — | 0.386 | 0.380 | NVIDIA A10G | 27.934 | $0.2306 |
| laya-typed-decisions-ft-s19 | 0.722 | 0.500–0.889 | 0.722 | — | 0.289 | 0.270 | NVIDIA A10G | 29.115 | $0.3333 |
| laya-typed-decisions FT mean ± SD [range] | 0.667 ± 0.096 [0.556–0.722] | — | 0.667 ± 0.096 [0.556–0.722] | — | 0.285 ± 0.104 [0.179–0.386] | 0.280 ± 0.094 [0.192–0.380] | — | — | — |

- Best single arm: `kev-9b` (balanced accuracy 0.833).
- Best fine-tuned family by seed mean: `kev-4b` (0.704 ± 0.032 [0.667–0.722]).

### semantic-detection (`noul`)

Test items: 466 (True=132, False=334).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 0.531 | 0.504–0.562 | 0.098 | 0.964 | 0.074 | 0.101 | NVIDIA L4 | 16.246 | $0.2764 |
| kev-0.8b-ft-s17 | 0.634 | 0.596–0.670 | 0.280 | 0.988 | 0.178 | 0.129 | NVIDIA A10G | 13.256 | $0.5111 |
| kev-0.8b-ft-s18 | 0.628 | 0.588–0.670 | 0.295 | 0.961 | 0.121 | 0.148 | NVIDIA A10G | 13.252 | $0.3825 |
| kev-0.8b-ft-s19 | 0.652 | 0.611–0.691 | 0.318 | 0.985 | 0.109 | 0.126 | NVIDIA A10G | 13.241 | $0.5011 |
| kev-0.8b FT mean ± SD [range] | 0.638 ± 0.012 [0.628–0.652] | — | 0.298 ± 0.019 [0.280–0.318] | 0.978 ± 0.015 [0.961–0.988] | 0.136 ± 0.037 [0.109–0.178] | 0.135 ± 0.012 [0.126–0.148] | — | — | — |
| kev-4b | 0.554 | 0.516–0.595 | 0.174 | 0.934 | 0.056 | 0.056 | NVIDIA A10G | 47.498 | $0.4125 |
| kev-4b-ft-s17 | 0.725 | 0.683–0.766 | 0.500 | 0.949 | 0.128 | 0.119 | NVIDIA A10G | 47.252 | $1.2025 |
| kev-4b-ft-s18 | 0.727 | 0.679–0.767 | 0.523 | 0.931 | 0.126 | 0.110 | NVIDIA A10G | 47.544 | $0.4250 |
| kev-4b-ft-s19 | 0.697 | 0.652–0.739 | 0.455 | 0.940 | 0.131 | 0.102 | NVIDIA A10G | 47.285 | $0.4175 |
| kev-4b FT mean ± SD [range] | 0.716 ± 0.016 [0.697–0.727] | — | 0.492 ± 0.035 [0.455–0.523] | 0.940 ± 0.009 [0.931–0.949] | 0.128 ± 0.002 [0.126–0.131] | 0.110 ± 0.009 [0.102–0.119] | — | — | — |
| kev-9b | 0.578 | 0.527–0.634 | 0.333 | 0.823 | 0.124 | 0.156 | NVIDIA L40S | 55.068 | $0.8944 |
| kev-9b-ft-s17 | 0.723 | 0.675–0.770 | 0.485 | 0.961 | 0.129 | 0.126 | NVIDIA L40S | 54.672 | $0.6178 |
| kev-9b-ft-s18 | 0.702 | 0.658–0.745 | 0.417 | 0.988 | 0.107 | 0.093 | NVIDIA L40S | 54.768 | $0.6472 |
| kev-9b-ft-s19 | 0.718 | 0.672–0.763 | 0.455 | 0.982 | 0.135 | 0.133 | NVIDIA L40S | 55.227 | $0.8653 |
| kev-9b FT mean ± SD [range] | 0.715 ± 0.011 [0.702–0.723] | — | 0.452 ± 0.034 [0.417–0.485] | 0.977 ± 0.014 [0.961–0.988] | 0.124 ± 0.015 [0.107–0.135] | 0.117 ± 0.021 [0.093–0.133] | — | — | — |
| laya-english | 0.476 | 0.433–0.521 | 0.447 | 0.506 | 0.235 | 0.074 | NVIDIA A10G | 28.347 | $0.3542 |
| laya-multilingual | 0.544 | 0.501–0.593 | 0.508 | 0.581 | 0.267 | 0.030 | NVIDIA A10G | 23.215 | $0.4389 |
| laya-typed-decisions | 0.520 | 0.473–0.567 | 0.288 | 0.751 | 0.055 | 0.101 | NVIDIA A10G | 27.503 | $0.4478 |
| laya-typed-decisions-ft-s17 | 0.612 | 0.573–0.648 | 0.295 | 0.928 | 0.210 | 0.137 | NVIDIA A10G | 28.206 | $0.2228 |
| laya-typed-decisions-ft-s18 | 0.607 | 0.567–0.648 | 0.265 | 0.949 | 0.176 | 0.082 | NVIDIA A10G | 27.934 | $0.2306 |
| laya-typed-decisions-ft-s19 | 0.597 | 0.561–0.633 | 0.258 | 0.937 | 0.210 | 0.100 | NVIDIA A10G | 29.115 | $0.3333 |
| laya-typed-decisions FT mean ± SD [range] | 0.605 ± 0.007 [0.597–0.612] | — | 0.273 ± 0.020 [0.258–0.295] | 0.938 ± 0.011 [0.928–0.949] | 0.199 ± 0.020 [0.176–0.210] | 0.106 ± 0.028 [0.082–0.137] | — | — | — |

- Best single arm: `kev-4b-ft-s18` (balanced accuracy 0.727).
- Best fine-tuned family by seed mean: `kev-4b` (0.716 ± 0.016 [0.697–0.727]).

## Fine-tune vs base

Δ is the fine-tune seed mean minus the base arm on the same test items (positive balanced accuracy or recall is better; negative ECE is better). "Seeds > base" counts seeds whose balanced accuracy beats the base.

### finding-confirmation (`choice`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ real-defect recall | Δ no-defect recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | this campaign | 0.167 | 0.593 | +0.426 | 3/3 | +0.426 | — | +0.070 | +0.046 |
| kev-4b | this campaign | 0.500 | 0.704 | +0.204 | 3/3 | +0.204 | — | +0.058 | -0.059 |
| kev-9b | this campaign | 0.833 | 0.685 | -0.148 | 0/3 | -0.148 | — | +0.022 | +0.144 |
| laya-typed-decisions | this campaign | 0.167 | 0.667 | +0.500 | 3/3 | +0.500 | — | +0.006 | -0.026 |

### semantic-detection (`noul`)

| Family | Base from | Base bal. acc. | FT mean bal. acc. | Δ bal. acc. | Seeds > base | Δ True recall | Δ False recall | Δ ECE raw | Δ ECE cal. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | this campaign | 0.531 | 0.638 | +0.107 | 3/3 | +0.199 | +0.014 | +0.062 | +0.033 |
| kev-4b | this campaign | 0.554 | 0.716 | +0.162 | 3/3 | +0.318 | +0.006 | +0.072 | +0.055 |
| kev-9b | this campaign | 0.578 | 0.715 | +0.136 | 3/3 | +0.119 | +0.154 | -0.001 | -0.039 |
| laya-typed-decisions | this campaign | 0.520 | 0.605 | +0.086 | 3/3 | -0.015 | +0.187 | +0.144 | +0.005 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | — | — | — | — | 1 / 1 / 0 | $0.28 | $0.28 |
| kev-4b | — | — | — | — | 1 / 0 / 0 | $0.41 | $0.41 |
| kev-9b | — | — | — | — | 1 / 0 / 4 | $0.89 | $0.89 |
| laya-english | — | — | — | — | 1 / 5 / 1 | $1.63 | $1.63 |
| laya-multilingual | — | — | — | — | 1 / 5 / 1 | $1.82 | $1.82 |
| laya-typed-decisions | — | — | — | — | 1 / 3 / 1 | $1.76 | $1.76 |
| kev-0.8b-ft-s17 | 0 / 4 / 2 | $5.78 | slopvac-judge-kev-08b-s17-20260929033635 | $5.14 | 1 / 0 / 0 | $0.51 | $6.29 |
| kev-0.8b-ft-s18 | 1 / 0 / 1 | $7.25 | slopvac-judge-kev-08b-s18-20260929104701 | $5.15 | 1 / 3 / 0 | $1.38 | $8.63 |
| kev-0.8b-ft-s19 | 1 / 0 / 1 | $7.78 | slopvac-judge-kev-08b-s19-20260929104711 | $5.17 | 1 / 0 / 1 | $0.76 | $8.54 |
| kev-4b-ft-s17 | 0 / 2 / 3 | $8.26 | slopvac-judge-kev-4b-s17-20260929062810 | $8.26 | 1 / 0 / 0 | $1.20 | $9.46 |
| kev-4b-ft-s18 | 0 / 2 / 3 | $10.30 | slopvac-judge-kev-4b-s18-20260929062915 | $10.30 | 1 / 0 / 0 | $0.42 | $10.73 |
| kev-4b-ft-s19 | 0 / 1 / 3 | $17.00 | slopvac-judge-kev-4b-s19-20260929062949 | $14.33 | 1 / 1 / 0 | $0.67 | $17.67 |
| kev-9b-ft-s17 | 0 / 7 / 7 | $13.94 | slopvac-judge-kev-9b-s17-20260929081017 | $11.13 | 1 / 0 / 2 | $0.62 | $14.56 |
| kev-9b-ft-s18 | 1 / 2 / 4 | $14.38 | slopvac-judge-kev-9b-s18-20260929113826 | $11.13 | 1 / 0 / 0 | $0.65 | $15.03 |
| kev-9b-ft-s19 | 1 / 3 / 2 | $21.35 | slopvac-judge-kev-9b-s19-20260929113847 | $15.56 | 1 / 1 / 0 | $1.41 | $22.76 |
| laya-typed-decisions-ft-s17 | 2 / 2 / 3 | $51.03 | slopvac-judge-laya-typed-decisions-s17-20260930083119 | $11.00 | 1 / 0 / 0 | $0.22 | $51.25 |
| laya-typed-decisions-ft-s18 | 2 / 3 / 4 | $50.57 | slopvac-judge-laya-typed-decisions-s18-20260930083141 | $11.17 | 1 / 0 / 0 | $0.23 | $50.80 |
| laya-typed-decisions-ft-s19 | 2 / 2 / 4 | $58.05 | slopvac-judge-laya-typed-decisions-s19-20260930083241 | $16.39 | 1 / 0 / 0 | $0.33 | $58.39 |

Campaign total: **$281.39 USD** (training $266.19, evaluation $15.20) over 78 training and 47 evaluation jobs.

Ledger jobs for targets outside this campaign's arms: kev-9b-ft-s? (no seed).

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| kev-0.8b | evaluation | Failed | 1 | $0.00 | no reason recorded |
| kev-0.8b-ft-s17 | training | Failed | 1 | $5.14 | ACCEPTED (checkpoint saved before the failure): AlgorithmError: ContextOverflow: state exceeds 384 tokens: 3013 |
| kev-0.8b-ft-s17 | training | Failed | 1 | $0.13 | AlgorithmError: , exit code: 1 |
| kev-0.8b-ft-s17 | training | Failed | 2 | $0.00 | create_training_job raised |
| kev-0.8b-ft-s17 | training | Stopped | 2 | $0.50 | cancelled or superseded before completing this campaign recipe |
| kev-0.8b-ft-s18 | evaluation | Failed | 3 | $1.00 | AlgorithmError: KeyError: 'train' |
| kev-0.8b-ft-s18 | training | Stopped | 1 | $2.10 | no failure reason; secondary status MaxRuntimeExceeded |
| kev-0.8b-ft-s19 | evaluation | Stopped | 1 | $0.26 | no reason recorded |
| kev-0.8b-ft-s19 | training | Stopped | 1 | $2.61 | no failure reason; secondary status MaxRuntimeExceeded |
| kev-4b-ft-s17 | training | Failed | 1 | $8.26 | ACCEPTED (checkpoint saved before the failure): AlgorithmError: ContextOverflow: state exceeds 384 tokens: 3013 |
| kev-4b-ft-s17 | training | Failed | 1 | $0.00 | scheduler marker `kev_max_state_default` |
| kev-4b-ft-s17 | training | Stopped | 1 | $0.00 | cancelled or superseded before completing this campaign recipe |
| kev-4b-ft-s17 | training | Stopped | 1 | $0.00 | scheduler marker `approved_epoch_alignment` |
| kev-4b-ft-s17 | training | Stopped | 1 | $0.00 | scheduler marker `kev_max_state_default` |
| kev-4b-ft-s18 | training | Failed | 1 | $10.30 | ACCEPTED (checkpoint saved before the failure): AlgorithmError: ContextOverflow: state exceeds 384 tokens: 3013 |
| kev-4b-ft-s18 | training | Failed | 1 | $0.00 | create_training_job raised |
| kev-4b-ft-s18 | training | Stopped | 1 | $0.00 | cancelled or superseded before completing this campaign recipe |
| kev-4b-ft-s18 | training | Stopped | 1 | $0.00 | scheduler marker `approved_epoch_alignment` |
| kev-4b-ft-s18 | training | Stopped | 1 | $0.00 | scheduler marker `kev_max_state_default` |
| kev-4b-ft-s19 | evaluation | Failed | 1 | $0.25 | AlgorithmError: SystemExit: model.tar.gz has no finetune.json |
| kev-4b-ft-s19 | training | Failed | 1 | $14.33 | ACCEPTED (checkpoint saved before the failure): AlgorithmError: ContextOverflow: state exceeds 384 tokens: 3013 |
| kev-4b-ft-s19 | training | Stopped | 2 | $2.67 | scheduler marker `approved_epoch_alignment` |
| kev-4b-ft-s19 | training | Stopped | 1 | $0.00 | scheduler marker `kev_max_state_default` |
| kev-9b | evaluation | Stopped | 1 | $0.00 | cancelled or superseded before completing this campaign recipe |
| kev-9b | evaluation | Stopped | 3 | $0.00 | scheduler marker `capacity_rotation` |
| kev-9b-ft-s17 | evaluation | Stopped | 2 | $0.00 | scheduler marker `capacity_rotation` |
| kev-9b-ft-s17 | training | Failed | 1 | $11.13 | ACCEPTED (checkpoint saved before the failure): AlgorithmError: NameError: name 'ckpt' is not defined |
| kev-9b-ft-s17 | training | Failed | 1 | $2.12 | AlgorithmError: ContextOverflow: state exceeds 384 tokens: 3013 |
| kev-9b-ft-s17 | training | Failed | 1 | $0.52 | AlgorithmError: KeyError: 'dtype' |
| kev-9b-ft-s17 | training | Failed | 4 | $0.00 | create_training_job raised |
| kev-9b-ft-s17 | training | Stopped | 6 | $0.17 | cancelled or superseded before completing this campaign recipe |
| kev-9b-ft-s17 | training | Stopped | 1 | $0.00 | scheduler marker `approved_runtime_resize` |
| kev-9b-ft-s18 | training | Failed | 2 | $0.00 | create_training_job raised |
| kev-9b-ft-s18 | training | Stopped | 1 | $0.00 | cancelled or superseded before completing this campaign recipe |
| kev-9b-ft-s18 | training | Stopped | 1 | $0.00 | scheduler marker `approved_runtime_resize` |
| kev-9b-ft-s18 | training | Stopped | 1 | $0.00 | scheduler marker `kev_max_state_default` |
| kev-9b-ft-s18 | training | Stopped | 1 | $3.25 | stopped before retraining due known NameError ckpt post-training path |
| kev-9b-ft-s19 | evaluation | Failed | 1 | $0.54 | AlgorithmError: KeyError: 'train' |
| kev-9b-ft-s19 | training | Failed | 1 | $2.93 | AlgorithmError: ContextOverflow: state exceeds 384 tokens: 3013 |
| kev-9b-ft-s19 | training | Failed | 1 | $0.76 | AlgorithmError: SystemExit: kev.train failed (1); see train.log |
| kev-9b-ft-s19 | training | Failed | 1 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g6e.4xlarge for training job usage' is … |
| kev-9b-ft-s19 | training | Stopped | 1 | $0.00 | cancelled or superseded before completing this campaign recipe |
| kev-9b-ft-s19 | training | Stopped | 1 | $2.10 | stopped before retraining due known NameError ckpt post-training path |
| kev-9b-ft-s? (no seed) | training | Failed | 1 | $0.51 | AlgorithmError: KeyError: 'seed' |
| kev-9b-ft-s? (no seed) | training | Failed | 1 | $0.00 | create_training_job raised |
| kev-9b-ft-s? (no seed) | training | Stopped | 1 | $0.00 | cancelled or superseded before completing this campaign recipe |
| laya-english | evaluation | Failed | 2 | $0.77 | AlgorithmError: KeyError: 'laya_commit' |
| laya-english | evaluation | Failed | 2 | $0.51 | AlgorithmError: SystemExit: hyperparameters do not match arms.py for laya-english |
| laya-english | evaluation | Failed | 1 | $0.00 | scheduler marker `laya_eval_identity_commit` |
| laya-english | evaluation | Stopped | 1 | $0.00 | no reason recorded |
| laya-multilingual | evaluation | Failed | 2 | $0.70 | AlgorithmError: KeyError: 'laya_commit' |
| laya-multilingual | evaluation | Failed | 2 | $0.69 | AlgorithmError: SystemExit: hyperparameters do not match arms.py for laya-multilingual |
| laya-multilingual | evaluation | Failed | 1 | $0.00 | scheduler marker `laya_eval_identity_commit` |
| laya-multilingual | evaluation | Stopped | 1 | $0.00 | no reason recorded |
| laya-typed-decisions | evaluation | Failed | 1 | $0.99 | AlgorithmError: KeyError: 'laya_commit' |
| laya-typed-decisions | evaluation | Failed | 1 | $0.31 | AlgorithmError: SystemExit: hyperparameters do not match arms.py for laya-typed-decisions |
| laya-typed-decisions | evaluation | Failed | 1 | $0.00 | scheduler marker `laya_eval_identity_commit` |
| laya-typed-decisions | evaluation | Stopped | 1 | $0.01 | no reason recorded |
| laya-typed-decisions-ft-s17 | training | Failed | 2 | $22.00 | AlgorithmError: , exit code: 1 |
| laya-typed-decisions-ft-s17 | training | Stopped | 1 | $8.13 | no failure reason; secondary status MaxRuntimeExceeded |
| laya-typed-decisions-ft-s17 | training | Stopped | 1 | $1.57 | no failure reason; secondary status Stopped |
| laya-typed-decisions-ft-s17 | training | Stopped | 1 | $8.13 | scheduler marker `approved_runtime_resize` |
| laya-typed-decisions-ft-s18 | training | Failed | 1 | $11.34 | AlgorithmError: , exit code: 1 |
| laya-typed-decisions-ft-s18 | training | Failed | 2 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g5.2xlarge for training job usage' is 1… |
| laya-typed-decisions-ft-s18 | training | Stopped | 1 | $8.13 | no failure reason; secondary status MaxRuntimeExceeded |
| laya-typed-decisions-ft-s18 | training | Stopped | 2 | $11.60 | no failure reason; secondary status Stopped |
| laya-typed-decisions-ft-s18 | training | Stopped | 1 | $8.14 | scheduler marker `approved_runtime_resize` |
| laya-typed-decisions-ft-s19 | training | Failed | 1 | $16.39 | AlgorithmError: , exit code: 1 |
| laya-typed-decisions-ft-s19 | training | Failed | 1 | $0.00 | submission rejected: ResourceLimitExceeded: The account-level service limit 'ml.g5.2xlarge for training job usage' is 1… |
| laya-typed-decisions-ft-s19 | training | Stopped | 1 | $12.20 | no failure reason; secondary status MaxRuntimeExceeded |
| laya-typed-decisions-ft-s19 | training | Stopped | 2 | $0.57 | no failure reason; secondary status Stopped |
| laya-typed-decisions-ft-s19 | training | Stopped | 1 | $12.20 | scheduler marker `approved_runtime_resize` |

## Panel agreement caveat

Independent corpus panel agreement (source: `/Users/sjors/tmp/worktrees/slopvac/exp-judge-corpus/scripts/judge-corpus/.cache/items-v2/panel-agreement.json`):
- finding-confirmation: Fleiss κ=0.13 (3599 three-vote items).
- semantic-detection: Fleiss κ=0.02 (1587 three-vote items).
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
| kev-0.8b | 466 | 0.719 | 0.531 | 0.596 | 0.200 | 0.591 | 0.074 | 0.208 | 0.608 | 0.101 | 0.504–0.562 | 0.050–0.127 | 0.077–0.145 | 0.098 | 0.964 | — | — | — | 16.246 | 117.167 |
| kev-0.8b-ft-s17 | 466 | 0.788 | 0.634 | 0.667 | 0.194 | 0.833 | 0.178 | 0.182 | 0.623 | 0.129 | 0.596–0.670 | 0.156–0.206 | 0.108–0.164 | 0.280 | 0.988 | — | — | — | 13.256 | 119.322 |
| kev-0.8b-ft-s18 | 466 | 0.773 | 0.628 | 0.679 | 0.178 | 0.603 | 0.121 | 0.187 | 0.720 | 0.148 | 0.588–0.670 | 0.101–0.167 | 0.125–0.184 | 0.295 | 0.961 | — | — | — | 13.252 | 119.199 |
| kev-0.8b-ft-s19 | 466 | 0.796 | 0.652 | 0.692 | 0.173 | 0.568 | 0.109 | 0.175 | 0.587 | 0.126 | 0.611–0.691 | 0.086–0.150 | 0.099–0.166 | 0.318 | 0.985 | — | — | — | 13.241 | 120.098 |
| FT mean ± SD [range] | — | 0.785 ± 0.012 [0.773–0.796] | 0.638 ± 0.012 [0.628–0.652] | 0.680 ± 0.013 [0.667–0.692] | 0.182 ± 0.011 [0.173–0.194] | 0.668 ± 0.144 [0.568–0.833] | 0.136 ± 0.037 [0.109–0.178] | 0.181 ± 0.006 [0.175–0.187] | 0.643 ± 0.069 [0.587–0.720] | 0.135 ± 0.012 [0.126–0.148] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 18 | 0.167 | 0.167 | — | 0.777 | 1.274 | 0.253 | 0.669 | 1.102 | 0.168 | 0.000–0.353 | 0.164–0.431 | 0.018–0.335 | — | — | 0.500 | 0.833 | 0.038 | 16.246 | 117.167 |
| kev-0.8b-ft-s17 | 18 | 0.556 | 0.556 | — | 0.730 | 1.219 | 0.415 | 0.594 | 0.862 | 0.256 | 0.294–0.789 | 0.226–0.626 | 0.137–0.506 | — | — | 0.000 | 0.889 | 0.150 | 13.256 | 119.322 |
| kev-0.8b-ft-s18 | 18 | 0.611 | 0.611 | — | 0.632 | 1.046 | 0.263 | 0.574 | 0.874 | 0.194 | 0.353–0.833 | 0.116–0.538 | 0.066–0.456 | — | — | 0.000 | 0.944 | 0.100 | 13.252 | 119.199 |
| kev-0.8b-ft-s19 | 18 | 0.611 | 0.611 | — | 0.533 | 0.856 | 0.291 | 0.516 | 0.800 | 0.193 | 0.353–0.842 | 0.161–0.508 | 0.122–0.461 | — | — | 0.000 | 0.833 | 0.085 | 13.241 | 120.098 |
| FT mean ± SD [range] | — | 0.593 ± 0.032 [0.556–0.611] | 0.593 ± 0.032 [0.556–0.611] | — | 0.632 ± 0.099 [0.533–0.730] | 1.040 ± 0.182 [0.856–1.219] | 0.323 ± 0.081 [0.263–0.415] | 0.561 ± 0.041 [0.516–0.594] | 0.845 ± 0.040 [0.800–0.874] | 0.214 ± 0.036 [0.193–0.256] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.889 ± 0.056 [0.833–0.944] | 0.112 ± 0.034 [0.085–0.150] | — | — |

### kev-4b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b | 466 | 0.719 | 0.554 | 0.624 | 0.199 | 0.586 | 0.056 | 0.198 | 0.586 | 0.056 | 0.516–0.595 | 0.037–0.111 | 0.043–0.115 | 0.174 | 0.934 | — | — | — | 47.498 | 220.146 |
| kev-4b-ft-s17 | 466 | 0.822 | 0.725 | 0.814 | 0.151 | 0.684 | 0.128 | 0.144 | 0.549 | 0.119 | 0.683–0.766 | 0.107–0.172 | 0.098–0.162 | 0.500 | 0.949 | — | — | — | 47.252 | 218.821 |
| kev-4b-ft-s18 | 466 | 0.815 | 0.727 | 0.830 | 0.149 | 0.602 | 0.126 | 0.142 | 0.493 | 0.110 | 0.679–0.767 | 0.101–0.172 | 0.085–0.153 | 0.523 | 0.931 | — | — | — | 47.544 | 215.752 |
| kev-4b-ft-s19 | 466 | 0.803 | 0.697 | 0.813 | 0.164 | 0.593 | 0.131 | 0.153 | 0.491 | 0.102 | 0.652–0.739 | 0.115–0.177 | 0.085–0.152 | 0.455 | 0.940 | — | — | — | 47.285 | 220.184 |
| FT mean ± SD [range] | — | 0.813 ± 0.010 [0.803–0.822] | 0.716 ± 0.016 [0.697–0.727] | 0.819 ± 0.010 [0.813–0.830] | 0.155 ± 0.008 [0.149–0.164] | 0.627 ± 0.050 [0.593–0.684] | 0.128 ± 0.002 [0.126–0.131] | 0.146 ± 0.006 [0.142–0.153] | 0.511 ± 0.033 [0.491–0.549] | 0.110 ± 0.009 [0.102–0.119] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-4b | 18 | 0.500 | 0.500 | — | 0.624 | 1.050 | 0.186 | 0.732 | 1.513 | 0.320 | 0.294–0.706 | 0.095–0.391 | 0.204–0.542 | — | — | 0.444 | 1.000 | 0.033 | 47.498 | 220.146 |
| kev-4b-ft-s17 | 18 | 0.722 | 0.722 | — | 0.417 | 0.929 | 0.224 | 0.360 | 0.667 | 0.207 | 0.471–0.895 | 0.085–0.438 | 0.088–0.405 | — | — | 0.000 | 0.833 | 0.107 | 47.252 | 218.821 |
| kev-4b-ft-s18 | 18 | 0.722 | 0.722 | — | 0.409 | 0.956 | 0.244 | 0.437 | 1.492 | 0.256 | 0.471–0.895 | 0.091–0.448 | 0.092–0.467 | — | — | 0.000 | 0.889 | 0.086 | 47.544 | 215.752 |
| kev-4b-ft-s19 | 18 | 0.667 | 0.667 | — | 0.474 | 1.259 | 0.265 | 0.624 | 1.861 | 0.322 | 0.450–0.882 | 0.113–0.451 | 0.113–0.533 | — | — | 0.000 | 0.722 | 0.122 | 47.285 | 220.184 |
| FT mean ± SD [range] | — | 0.704 ± 0.032 [0.667–0.722] | 0.704 ± 0.032 [0.667–0.722] | — | 0.433 ± 0.035 [0.409–0.474] | 1.048 ± 0.183 [0.929–1.259] | 0.244 ± 0.020 [0.224–0.265] | 0.474 ± 0.136 [0.360–0.624] | 1.340 ± 0.611 [0.667–1.861] | 0.262 ± 0.058 [0.207–0.322] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.815 ± 0.085 [0.722–0.889] | 0.105 ± 0.018 [0.086–0.122] | — | — |

### kev-9b

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b | 466 | 0.685 | 0.578 | 0.596 | 0.220 | 0.644 | 0.124 | 0.239 | 0.670 | 0.156 | 0.527–0.634 | 0.088–0.182 | 0.095–0.216 | 0.333 | 0.823 | — | — | — | 55.068 | 190.758 |
| kev-9b-ft-s17 | 466 | 0.826 | 0.723 | 0.793 | 0.152 | 0.661 | 0.129 | 0.152 | 0.636 | 0.126 | 0.675–0.770 | 0.109–0.172 | 0.107–0.169 | 0.485 | 0.961 | — | — | — | 54.672 | 190.866 |
| kev-9b-ft-s18 | 466 | 0.826 | 0.702 | 0.810 | 0.140 | 0.475 | 0.107 | 0.135 | 0.435 | 0.093 | 0.658–0.745 | 0.082–0.144 | 0.068–0.134 | 0.417 | 0.988 | — | — | — | 54.768 | 192.061 |
| kev-9b-ft-s19 | 466 | 0.833 | 0.718 | 0.790 | 0.152 | 0.652 | 0.135 | 0.152 | 0.642 | 0.133 | 0.672–0.763 | 0.113–0.173 | 0.109–0.171 | 0.455 | 0.982 | — | — | — | 55.227 | 191.262 |
| FT mean ± SD [range] | — | 0.828 ± 0.004 [0.826–0.833] | 0.715 ± 0.011 [0.702–0.723] | 0.798 ± 0.011 [0.790–0.810] | 0.148 ± 0.007 [0.140–0.152] | 0.596 ± 0.105 [0.475–0.661] | 0.124 ± 0.015 [0.107–0.135] | 0.146 ± 0.010 [0.135–0.152] | 0.571 ± 0.118 [0.435–0.642] | 0.117 ± 0.021 [0.093–0.133] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-9b | 18 | 0.833 | 0.833 | — | 0.367 | 0.667 | 0.265 | 0.333 | 2.304 | 0.165 | 0.647–1.000 | 0.198–0.440 | 0.002–0.353 | — | — | 0.056 | 0.944 | 0.072 | 55.068 | 190.758 |
| kev-9b-ft-s17 | 18 | 0.667 | 0.667 | — | 0.557 | 1.017 | 0.297 | 0.667 | 4.605 | 0.333 | 0.450–0.882 | 0.105–0.492 | 0.118–0.550 | — | — | 0.000 | 1.000 | 0.070 | 54.672 | 190.866 |
| kev-9b-ft-s18 | 18 | 0.722 | 0.722 | — | 0.456 | 0.745 | 0.248 | 0.556 | 3.838 | 0.278 | 0.529–0.941 | 0.100–0.429 | 0.059–0.471 | — | — | 0.000 | 0.944 | 0.048 | 54.768 | 192.061 |
| kev-9b-ft-s19 | 18 | 0.667 | 0.667 | — | 0.610 | 1.310 | 0.317 | 0.609 | 1.302 | 0.317 | 0.450–0.882 | 0.111–0.524 | 0.111–0.523 | — | — | 0.000 | 1.000 | 0.032 | 55.227 | 191.262 |
| FT mean ± SD [range] | — | 0.685 ± 0.032 [0.667–0.722] | 0.685 ± 0.032 [0.667–0.722] | — | 0.541 ± 0.078 [0.456–0.610] | 1.024 ± 0.283 [0.745–1.310] | 0.287 ± 0.035 [0.248–0.317] | 0.610 ± 0.056 [0.556–0.667] | 3.248 ± 1.729 [1.302–4.605] | 0.309 ± 0.029 [0.278–0.333] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.981 ± 0.032 [0.944–1.000] | 0.050 ± 0.019 [0.032–0.070] | — | — |

### laya-english

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-english | 466 | 0.489 | 0.476 | 0.449 | 0.314 | 0.867 | 0.235 | 0.256 | 0.705 | 0.074 | 0.433–0.521 | 0.179–0.305 | 0.030–0.137 | 0.447 | 0.506 | — | — | — | 28.347 | 29.724 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-english | 18 | 0.278 | 0.278 | — | 0.677 | 1.123 | 0.294 | 0.666 | 1.097 | 0.062 | 0.095–0.529 | 0.190–0.415 | 0.007–0.246 | — | — | 0.222 | 0.556 | 0.081 | 28.347 | 29.724 |

### laya-multilingual

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-multilingual | 466 | 0.560 | 0.544 | 0.567 | 0.327 | 1.029 | 0.267 | 0.245 | 0.683 | 0.030 | 0.501–0.593 | 0.219–0.349 | 0.013–0.106 | 0.508 | 0.581 | — | — | — | 23.215 | 25.343 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-multilingual | 18 | 0.056 | 0.056 | — | 0.979 | 1.559 | 0.523 | 0.681 | 1.119 | 0.301 | 0.000–0.176 | 0.432–0.638 | 0.183–0.363 | — | — | 0.500 | 0.667 | 0.128 | 23.215 | 25.343 |

### laya-typed-decisions

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-typed-decisions | 466 | 0.620 | 0.520 | 0.526 | 0.228 | 0.649 | 0.055 | 0.231 | 0.655 | 0.101 | 0.473–0.567 | 0.037–0.123 | 0.057–0.158 | 0.288 | 0.751 | — | — | — | 27.503 | 35.142 |
| laya-typed-decisions-ft-s17 | 466 | 0.749 | 0.612 | 0.648 | 0.217 | 0.876 | 0.210 | 0.191 | 0.596 | 0.137 | 0.573–0.648 | 0.190–0.245 | 0.116–0.173 | 0.295 | 0.928 | — | — | — | 28.206 | 35.509 |
| laya-typed-decisions-ft-s18 | 466 | 0.755 | 0.607 | 0.615 | 0.208 | 0.793 | 0.176 | 0.186 | 0.572 | 0.082 | 0.567–0.648 | 0.154–0.214 | 0.069–0.126 | 0.265 | 0.949 | — | — | — | 27.934 | 35.105 |
| laya-typed-decisions-ft-s19 | 466 | 0.745 | 0.597 | 0.618 | 0.222 | 0.906 | 0.210 | 0.188 | 0.572 | 0.100 | 0.561–0.633 | 0.185–0.244 | 0.080–0.138 | 0.258 | 0.937 | — | — | — | 29.115 | 35.226 |
| FT mean ± SD [range] | — | 0.750 ± 0.005 [0.745–0.755] | 0.605 ± 0.007 [0.597–0.612] | 0.627 ± 0.018 [0.615–0.648] | 0.216 ± 0.007 [0.208–0.222] | 0.858 ± 0.059 [0.793–0.906] | 0.199 ± 0.020 [0.176–0.210] | 0.188 ± 0.003 [0.186–0.191] | 0.580 ± 0.014 [0.572–0.596] | 0.106 ± 0.028 [0.082–0.137] | — | — | — | — | — | — | — | — | — | — |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| laya-typed-decisions | 18 | 0.167 | 0.167 | — | 0.725 | 1.193 | 0.279 | 0.774 | 1.282 | 0.306 | 0.000–0.353 | 0.123–0.401 | 0.185–0.431 | — | — | 0.500 | 0.722 | 0.026 | 27.503 | 35.142 |
| laya-typed-decisions-ft-s17 | 18 | 0.722 | 0.722 | — | 0.422 | 0.705 | 0.179 | 0.416 | 0.696 | 0.192 | 0.529–0.906 | 0.070–0.387 | 0.099–0.404 | — | — | 0.000 | 1.000 | 0.075 | 28.206 | 35.509 |
| laya-typed-decisions-ft-s18 | 18 | 0.556 | 0.556 | — | 0.655 | 1.090 | 0.386 | 0.642 | 1.046 | 0.380 | 0.333–0.778 | 0.208–0.567 | 0.203–0.559 | — | — | 0.000 | 0.667 | 0.241 | 27.934 | 35.105 |
| laya-typed-decisions-ft-s19 | 18 | 0.722 | 0.722 | — | 0.526 | 0.983 | 0.289 | 0.428 | 0.745 | 0.270 | 0.500–0.889 | 0.114–0.481 | 0.200–0.441 | — | — | 0.000 | 0.944 | 0.070 | 29.115 | 35.226 |
| FT mean ± SD [range] | — | 0.667 ± 0.096 [0.556–0.722] | 0.667 ± 0.096 [0.556–0.722] | — | 0.534 ± 0.117 [0.422–0.655] | 0.926 ± 0.199 [0.705–1.090] | 0.285 ± 0.104 [0.179–0.386] | 0.495 ± 0.127 [0.416–0.642] | 0.829 ± 0.189 [0.696–1.046] | 0.280 ± 0.094 [0.192–0.380] | — | — | — | — | — | 0.000 ± 0.000 [0.000–0.000] | 0.870 ± 0.179 [0.667–1.000] | 0.129 ± 0.097 [0.070–0.241] | — | — |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | NVIDIA L4 | ml.g6.2xlarge | us-east-1 | 16.246 | 117.167 | 398 | $0.2764 | sv-eval-kev-08b-260929032437584768 |
| kev-0.8b-ft-s17 | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 13.256 | 119.322 | 460 | $0.5111 | sv-eval-kev-08b-ft-s17-260929104931586180 |
| kev-0.8b-ft-s18 | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 13.252 | 119.199 | 459 | $0.3825 | sv-eval-kev-08b-ft-s18-260929142219205009 |
| kev-0.8b-ft-s19 | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 13.241 | 120.098 | 451 | $0.5011 | sv-eval-kev-08b-ft-s19-260929142238015785 |
| kev-4b | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 47.498 | 220.146 | 495 | $0.4125 | sv-eval-kev-4b-260929041224096974 |
| kev-4b-ft-s17 | NVIDIA A10G | ml.g5.12xlarge | us-east-1 | 47.252 | 218.821 | 481 | $1.2025 | sv-eval-kev-4b-ft-s17-260929104958309380 |
| kev-4b-ft-s18 | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 47.544 | 215.752 | 510 | $0.4250 | sv-eval-kev-4b-ft-s18-260930083520945776 |
| kev-4b-ft-s19 | NVIDIA A10G | ml.g5.4xlarge | us-east-1 | 47.285 | 220.184 | 501 | $0.4175 | sv-eval-kev-4b-ft-s19-260929094659059066 |
| kev-9b | NVIDIA L40S | ml.g6e.8xlarge | us-west-2 | 55.068 | 190.758 | 460 | $0.8944 | sv-eval-kev-9b-261001111500613129 |
| kev-9b-ft-s17 | NVIDIA L40S | ml.g6e.2xlarge | us-east-1 | 54.672 | 190.866 | 556 | $0.6178 | sv-eval-kev-9b-ft-s17-260930121851307804 |
| kev-9b-ft-s18 | NVIDIA L40S | ml.g6e.4xlarge | us-east-1 | 54.768 | 192.061 | 466 | $0.6472 | sv-eval-kev-9b-ft-s18-260929160037425047 |
| kev-9b-ft-s19 | NVIDIA L40S | ml.g6e.8xlarge | us-west-2 | 55.227 | 191.262 | 445 | $0.8653 | sv-eval-kev-9b-ft-s19-260929161800845034 |
| laya-english | NVIDIA A10G | ml.g5.4xlarge | us-west-2 | 28.347 | 29.724 | 425 | $0.3542 | sv-eval-laya-english-260929114322949881 |
| laya-multilingual | NVIDIA A10G | ml.g5.8xlarge | us-east-1 | 23.215 | 25.343 | 395 | $0.4389 | sv-eval-laya-multilingual-260929114336173281 |
| laya-typed-decisions | NVIDIA A10G | ml.g5.8xlarge | us-west-2 | 27.503 | 35.142 | 403 | $0.4478 | sv-eval-laya-typed-decisions-260929114346788194 |
| laya-typed-decisions-ft-s17 | NVIDIA A10G | ml.g5.2xlarge | us-east-1 | 28.206 | 35.509 | 401 | $0.2228 | sv-eval-laya-typed-decisions-ft-s17-261001105909364041 |
| laya-typed-decisions-ft-s18 | NVIDIA A10G | ml.g5.2xlarge | us-west-2 | 27.934 | 35.105 | 415 | $0.2306 | sv-eval-laya-typed-decisions-ft-s18-261001105926563387 |
| laya-typed-decisions-ft-s19 | NVIDIA A10G | ml.g5.4xlarge | us-east-1 | 29.115 | 35.226 | 400 | $0.3333 | sv-eval-laya-typed-decisions-ft-s19-261001105946898827 |

Total billed evaluation cost for the reported arms: **$9.1809 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | noul | granularity | document | 118 | 0.703 | 0.503 | 0.168 | 0.029 | 0.976 |
| kev-0.8b | noul | granularity | paragraph | 217 | 0.700 | 0.515 | 0.073 | 0.081 | 0.948 |
| kev-0.8b | noul | granularity | sentence | 131 | 0.763 | 0.587 | 0.123 | 0.194 | 0.979 |
| kev-0.8b | noul | provenance | human | 466 | 0.719 | 0.531 | 0.074 | 0.098 | 0.964 |
| kev-0.8b | noul | role | semantic-detection | 466 | 0.719 | 0.531 | 0.074 | 0.098 | 0.964 |
| kev-0.8b | noul | rule_held_out | False | 380 | 0.703 | 0.515 | 0.075 | 0.073 | 0.956 |
| kev-0.8b | noul | rule_held_out | True | 86 | 0.791 | 0.609 | 0.150 | 0.217 | 1.000 |
| kev-0.8b | noul | source accuracy | human | 466 | 0.719 | — | — | — | — |
| kev-0.8b | choice | granularity | document | 4 | 0.250 | 0.250 | 0.296 | — | 0.250 |
| kev-0.8b | choice | granularity | paragraph | 8 | 0.000 | 0.000 | 0.424 | — | 0.000 |
| kev-0.8b | choice | granularity | sentence | 6 | 0.333 | 0.333 | 0.230 | — | 0.333 |
| kev-0.8b | choice | provenance | human | 18 | 0.167 | 0.167 | 0.253 | — | 0.167 |
| kev-0.8b | choice | role | finding-confirmation | 18 | 0.167 | 0.167 | 0.253 | — | 0.167 |
| kev-0.8b | choice | rule_held_out | False | 17 | 0.176 | 0.176 | 0.245 | — | 0.176 |
| kev-0.8b | choice | rule_held_out | True | 1 | 0.000 | 0.000 | 0.388 | — | 0.000 |
| kev-0.8b | choice | source accuracy | human | 18 | 0.167 | — | — | — | — |
| kev-0.8b-ft-s17 | noul | granularity | document | 118 | 0.780 | 0.626 | 0.192 | 0.265 | 0.988 |
| kev-0.8b-ft-s17 | noul | granularity | paragraph | 217 | 0.783 | 0.635 | 0.179 | 0.290 | 0.981 |
| kev-0.8b-ft-s17 | noul | granularity | sentence | 131 | 0.802 | 0.639 | 0.173 | 0.278 | 1.000 |
| kev-0.8b-ft-s17 | noul | provenance | human | 466 | 0.788 | 0.634 | 0.178 | 0.280 | 0.988 |
| kev-0.8b-ft-s17 | noul | role | semantic-detection | 466 | 0.788 | 0.634 | 0.178 | 0.280 | 0.988 |
| kev-0.8b-ft-s17 | noul | rule_held_out | False | 380 | 0.787 | 0.639 | 0.197 | 0.294 | 0.985 |
| kev-0.8b-ft-s17 | noul | rule_held_out | True | 86 | 0.791 | 0.609 | 0.134 | 0.217 | 1.000 |
| kev-0.8b-ft-s17 | noul | source accuracy | human | 466 | 0.788 | — | — | — | — |
| kev-0.8b-ft-s17 | choice | granularity | document | 4 | 0.500 | 0.500 | 0.446 | — | 0.500 |
| kev-0.8b-ft-s17 | choice | granularity | paragraph | 8 | 0.625 | 0.625 | 0.386 | — | 0.625 |
| kev-0.8b-ft-s17 | choice | granularity | sentence | 6 | 0.500 | 0.500 | 0.453 | — | 0.500 |
| kev-0.8b-ft-s17 | choice | provenance | human | 18 | 0.556 | 0.556 | 0.415 | — | 0.556 |
| kev-0.8b-ft-s17 | choice | role | finding-confirmation | 18 | 0.556 | 0.556 | 0.415 | — | 0.556 |
| kev-0.8b-ft-s17 | choice | rule_held_out | False | 17 | 0.529 | 0.529 | 0.440 | — | 0.529 |
| kev-0.8b-ft-s17 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.010 | — | 1.000 |
| kev-0.8b-ft-s17 | choice | source accuracy | human | 18 | 0.556 | — | — | — | — |
| kev-0.8b-ft-s18 | noul | granularity | document | 118 | 0.746 | 0.603 | 0.188 | 0.265 | 0.940 |
| kev-0.8b-ft-s18 | noul | granularity | paragraph | 217 | 0.779 | 0.642 | 0.139 | 0.323 | 0.961 |
| kev-0.8b-ft-s18 | noul | granularity | sentence | 131 | 0.786 | 0.628 | 0.125 | 0.278 | 0.979 |
| kev-0.8b-ft-s18 | noul | provenance | human | 466 | 0.773 | 0.628 | 0.121 | 0.295 | 0.961 |
| kev-0.8b-ft-s18 | noul | role | semantic-detection | 466 | 0.773 | 0.628 | 0.121 | 0.295 | 0.961 |
| kev-0.8b-ft-s18 | noul | rule_held_out | False | 380 | 0.768 | 0.632 | 0.146 | 0.312 | 0.952 |
| kev-0.8b-ft-s18 | noul | rule_held_out | True | 86 | 0.791 | 0.609 | 0.089 | 0.217 | 1.000 |
| kev-0.8b-ft-s18 | noul | source accuracy | human | 466 | 0.773 | — | — | — | — |
| kev-0.8b-ft-s18 | choice | granularity | document | 4 | 0.500 | 0.500 | 0.497 | — | 0.500 |
| kev-0.8b-ft-s18 | choice | granularity | paragraph | 8 | 0.750 | 0.750 | 0.106 | — | 0.750 |
| kev-0.8b-ft-s18 | choice | granularity | sentence | 6 | 0.500 | 0.500 | 0.452 | — | 0.500 |
| kev-0.8b-ft-s18 | choice | provenance | human | 18 | 0.611 | 0.611 | 0.263 | — | 0.611 |
| kev-0.8b-ft-s18 | choice | role | finding-confirmation | 18 | 0.611 | 0.611 | 0.263 | — | 0.611 |
| kev-0.8b-ft-s18 | choice | rule_held_out | False | 17 | 0.588 | 0.588 | 0.280 | — | 0.588 |
| kev-0.8b-ft-s18 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.031 | — | 1.000 |
| kev-0.8b-ft-s18 | choice | source accuracy | human | 18 | 0.611 | — | — | — | — |
| kev-0.8b-ft-s19 | noul | granularity | document | 118 | 0.780 | 0.626 | 0.154 | 0.265 | 0.988 |
| kev-0.8b-ft-s19 | noul | granularity | paragraph | 217 | 0.802 | 0.668 | 0.096 | 0.355 | 0.981 |
| kev-0.8b-ft-s19 | noul | granularity | sentence | 131 | 0.802 | 0.648 | 0.094 | 0.306 | 0.989 |
| kev-0.8b-ft-s19 | noul | provenance | human | 466 | 0.796 | 0.652 | 0.109 | 0.318 | 0.985 |
| kev-0.8b-ft-s19 | noul | role | semantic-detection | 466 | 0.796 | 0.652 | 0.109 | 0.318 | 0.985 |
| kev-0.8b-ft-s19 | noul | rule_held_out | False | 380 | 0.800 | 0.662 | 0.134 | 0.339 | 0.985 |
| kev-0.8b-ft-s19 | noul | rule_held_out | True | 86 | 0.779 | 0.601 | 0.059 | 0.217 | 0.984 |
| kev-0.8b-ft-s19 | noul | source accuracy | human | 466 | 0.796 | — | — | — | — |
| kev-0.8b-ft-s19 | choice | granularity | document | 4 | 0.500 | 0.500 | 0.487 | — | 0.500 |
| kev-0.8b-ft-s19 | choice | granularity | paragraph | 8 | 0.625 | 0.625 | 0.354 | — | 0.625 |
| kev-0.8b-ft-s19 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.382 | — | 0.667 |
| kev-0.8b-ft-s19 | choice | provenance | human | 18 | 0.611 | 0.611 | 0.291 | — | 0.611 |
| kev-0.8b-ft-s19 | choice | role | finding-confirmation | 18 | 0.611 | 0.611 | 0.291 | — | 0.611 |
| kev-0.8b-ft-s19 | choice | rule_held_out | False | 17 | 0.588 | 0.588 | 0.312 | — | 0.588 |
| kev-0.8b-ft-s19 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.069 | — | 1.000 |
| kev-0.8b-ft-s19 | choice | source accuracy | human | 18 | 0.611 | — | — | — | — |
| kev-4b | noul | granularity | document | 118 | 0.703 | 0.529 | 0.095 | 0.118 | 0.940 |
| kev-4b | noul | granularity | paragraph | 217 | 0.728 | 0.577 | 0.077 | 0.226 | 0.929 |
| kev-4b | noul | granularity | sentence | 131 | 0.718 | 0.538 | 0.082 | 0.139 | 0.937 |
| kev-4b | noul | provenance | human | 466 | 0.719 | 0.554 | 0.056 | 0.174 | 0.934 |
| kev-4b | noul | role | semantic-detection | 466 | 0.719 | 0.554 | 0.056 | 0.174 | 0.934 |
| kev-4b | noul | rule_held_out | False | 380 | 0.729 | 0.558 | 0.078 | 0.156 | 0.959 |
| kev-4b | noul | rule_held_out | True | 86 | 0.674 | 0.543 | 0.102 | 0.261 | 0.825 |
| kev-4b | noul | source accuracy | human | 466 | 0.719 | — | — | — | — |
| kev-4b | choice | granularity | document | 4 | 0.500 | 0.500 | 0.226 | — | 0.500 |
| kev-4b | choice | granularity | paragraph | 8 | 0.625 | 0.625 | 0.209 | — | 0.625 |
| kev-4b | choice | granularity | sentence | 6 | 0.333 | 0.333 | 0.300 | — | 0.333 |
| kev-4b | choice | provenance | human | 18 | 0.500 | 0.500 | 0.186 | — | 0.500 |
| kev-4b | choice | role | finding-confirmation | 18 | 0.500 | 0.500 | 0.186 | — | 0.500 |
| kev-4b | choice | rule_held_out | False | 17 | 0.471 | 0.471 | 0.163 | — | 0.471 |
| kev-4b | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.590 | — | 1.000 |
| kev-4b | choice | source accuracy | human | 18 | 0.500 | — | — | — | — |
| kev-4b-ft-s17 | noul | granularity | document | 118 | 0.822 | 0.709 | 0.163 | 0.441 | 0.976 |
| kev-4b-ft-s17 | noul | granularity | paragraph | 217 | 0.802 | 0.711 | 0.152 | 0.500 | 0.923 |
| kev-4b-ft-s17 | noul | granularity | sentence | 131 | 0.855 | 0.762 | 0.109 | 0.556 | 0.968 |
| kev-4b-ft-s17 | noul | provenance | human | 466 | 0.822 | 0.725 | 0.128 | 0.500 | 0.949 |
| kev-4b-ft-s17 | noul | role | semantic-detection | 466 | 0.822 | 0.725 | 0.128 | 0.500 | 0.949 |
| kev-4b-ft-s17 | noul | rule_held_out | False | 380 | 0.795 | 0.689 | 0.159 | 0.440 | 0.937 |
| kev-4b-ft-s17 | noul | rule_held_out | True | 86 | 0.942 | 0.891 | 0.064 | 0.783 | 1.000 |
| kev-4b-ft-s17 | noul | source accuracy | human | 466 | 0.822 | — | — | — | — |
| kev-4b-ft-s17 | choice | granularity | document | 4 | 0.500 | 0.500 | 0.398 | — | 0.500 |
| kev-4b-ft-s17 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.097 | — | 0.875 |
| kev-4b-ft-s17 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.292 | — | 0.667 |
| kev-4b-ft-s17 | choice | provenance | human | 18 | 0.722 | 0.722 | 0.224 | — | 0.722 |
| kev-4b-ft-s17 | choice | role | finding-confirmation | 18 | 0.722 | 0.722 | 0.224 | — | 0.722 |
| kev-4b-ft-s17 | choice | rule_held_out | False | 17 | 0.706 | 0.706 | 0.237 | — | 0.706 |
| kev-4b-ft-s17 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.000 | — | 1.000 |
| kev-4b-ft-s17 | choice | source accuracy | human | 18 | 0.722 | — | — | — | — |
| kev-4b-ft-s18 | noul | granularity | document | 118 | 0.780 | 0.679 | 0.164 | 0.441 | 0.917 |
| kev-4b-ft-s18 | noul | granularity | paragraph | 217 | 0.802 | 0.716 | 0.145 | 0.516 | 0.916 |
| kev-4b-ft-s18 | noul | granularity | sentence | 131 | 0.870 | 0.790 | 0.079 | 0.611 | 0.968 |
| kev-4b-ft-s18 | noul | provenance | human | 466 | 0.815 | 0.727 | 0.126 | 0.523 | 0.931 |
| kev-4b-ft-s18 | noul | role | semantic-detection | 466 | 0.815 | 0.727 | 0.126 | 0.523 | 0.931 |
| kev-4b-ft-s18 | noul | rule_held_out | False | 380 | 0.787 | 0.692 | 0.162 | 0.468 | 0.915 |
| kev-4b-ft-s18 | noul | rule_held_out | True | 86 | 0.942 | 0.891 | 0.063 | 0.783 | 1.000 |
| kev-4b-ft-s18 | noul | source accuracy | human | 466 | 0.815 | — | — | — | — |
| kev-4b-ft-s18 | choice | granularity | document | 4 | 0.500 | 0.500 | 0.395 | — | 0.500 |
| kev-4b-ft-s18 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.118 | — | 0.875 |
| kev-4b-ft-s18 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.343 | — | 0.667 |
| kev-4b-ft-s18 | choice | provenance | human | 18 | 0.722 | 0.722 | 0.244 | — | 0.722 |
| kev-4b-ft-s18 | choice | role | finding-confirmation | 18 | 0.722 | 0.722 | 0.244 | — | 0.722 |
| kev-4b-ft-s18 | choice | rule_held_out | False | 17 | 0.706 | 0.706 | 0.259 | — | 0.706 |
| kev-4b-ft-s18 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.000 | — | 1.000 |
| kev-4b-ft-s18 | choice | source accuracy | human | 18 | 0.722 | — | — | — | — |
| kev-4b-ft-s19 | noul | granularity | document | 118 | 0.788 | 0.685 | 0.177 | 0.441 | 0.929 |
| kev-4b-ft-s19 | noul | granularity | paragraph | 217 | 0.797 | 0.703 | 0.142 | 0.484 | 0.923 |
| kev-4b-ft-s19 | noul | granularity | sentence | 131 | 0.824 | 0.698 | 0.120 | 0.417 | 0.979 |
| kev-4b-ft-s19 | noul | provenance | human | 466 | 0.803 | 0.697 | 0.131 | 0.455 | 0.940 |
| kev-4b-ft-s19 | noul | role | semantic-detection | 466 | 0.803 | 0.697 | 0.131 | 0.455 | 0.940 |
| kev-4b-ft-s19 | noul | rule_held_out | False | 380 | 0.779 | 0.670 | 0.175 | 0.413 | 0.926 |
| kev-4b-ft-s19 | noul | rule_held_out | True | 86 | 0.907 | 0.826 | 0.098 | 0.652 | 1.000 |
| kev-4b-ft-s19 | noul | source accuracy | human | 466 | 0.803 | — | — | — | — |
| kev-4b-ft-s19 | choice | granularity | document | 4 | 0.250 | 0.250 | 0.601 | — | 0.250 |
| kev-4b-ft-s19 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.121 | — | 0.875 |
| kev-4b-ft-s19 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.311 | — | 0.667 |
| kev-4b-ft-s19 | choice | provenance | human | 18 | 0.667 | 0.667 | 0.265 | — | 0.667 |
| kev-4b-ft-s19 | choice | role | finding-confirmation | 18 | 0.667 | 0.667 | 0.265 | — | 0.667 |
| kev-4b-ft-s19 | choice | rule_held_out | False | 17 | 0.647 | 0.647 | 0.281 | — | 0.647 |
| kev-4b-ft-s19 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.001 | — | 1.000 |
| kev-4b-ft-s19 | choice | source accuracy | human | 18 | 0.667 | — | — | — | — |
| kev-9b | noul | granularity | document | 118 | 0.653 | 0.546 | 0.172 | 0.294 | 0.798 |
| kev-9b | noul | granularity | paragraph | 217 | 0.677 | 0.576 | 0.130 | 0.339 | 0.813 |
| kev-9b | noul | granularity | sentence | 131 | 0.725 | 0.612 | 0.167 | 0.361 | 0.863 |
| kev-9b | noul | provenance | human | 466 | 0.685 | 0.578 | 0.124 | 0.333 | 0.823 |
| kev-9b | noul | role | semantic-detection | 466 | 0.685 | 0.578 | 0.124 | 0.333 | 0.823 |
| kev-9b | noul | rule_held_out | False | 380 | 0.692 | 0.573 | 0.147 | 0.294 | 0.852 |
| kev-9b | noul | rule_held_out | True | 86 | 0.651 | 0.610 | 0.083 | 0.522 | 0.698 |
| kev-9b | noul | source accuracy | human | 466 | 0.685 | — | — | — | — |
| kev-9b | choice | granularity | document | 4 | 0.750 | 0.750 | 0.203 | — | 0.750 |
| kev-9b | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.401 | — | 0.875 |
| kev-9b | choice | granularity | sentence | 6 | 0.833 | 0.833 | 0.331 | — | 0.833 |
| kev-9b | choice | provenance | human | 18 | 0.833 | 0.833 | 0.265 | — | 0.833 |
| kev-9b | choice | role | finding-confirmation | 18 | 0.833 | 0.833 | 0.265 | — | 0.833 |
| kev-9b | choice | rule_held_out | False | 17 | 0.824 | 0.824 | 0.270 | — | 0.824 |
| kev-9b | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.186 | — | 1.000 |
| kev-9b | choice | source accuracy | human | 18 | 0.833 | — | — | — | — |
| kev-9b-ft-s17 | noul | granularity | document | 118 | 0.797 | 0.700 | 0.170 | 0.471 | 0.929 |
| kev-9b-ft-s17 | noul | granularity | paragraph | 217 | 0.834 | 0.734 | 0.147 | 0.500 | 0.968 |
| kev-9b-ft-s17 | noul | granularity | sentence | 131 | 0.840 | 0.726 | 0.122 | 0.472 | 0.979 |
| kev-9b-ft-s17 | noul | provenance | human | 466 | 0.826 | 0.723 | 0.129 | 0.485 | 0.961 |
| kev-9b-ft-s17 | noul | role | semantic-detection | 466 | 0.826 | 0.723 | 0.129 | 0.485 | 0.961 |
| kev-9b-ft-s17 | noul | rule_held_out | False | 380 | 0.797 | 0.680 | 0.159 | 0.404 | 0.956 |
| kev-9b-ft-s17 | noul | rule_held_out | True | 86 | 0.953 | 0.927 | 0.051 | 0.870 | 0.984 |
| kev-9b-ft-s17 | noul | source accuracy | human | 466 | 0.826 | — | — | — | — |
| kev-9b-ft-s17 | choice | granularity | document | 4 | 0.250 | 0.250 | 0.704 | — | 0.250 |
| kev-9b-ft-s17 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.100 | — | 0.875 |
| kev-9b-ft-s17 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.294 | — | 0.667 |
| kev-9b-ft-s17 | choice | provenance | human | 18 | 0.667 | 0.667 | 0.297 | — | 0.667 |
| kev-9b-ft-s17 | choice | role | finding-confirmation | 18 | 0.667 | 0.667 | 0.297 | — | 0.667 |
| kev-9b-ft-s17 | choice | rule_held_out | False | 17 | 0.647 | 0.647 | 0.315 | — | 0.647 |
| kev-9b-ft-s17 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.012 | — | 1.000 |
| kev-9b-ft-s17 | choice | source accuracy | human | 18 | 0.667 | — | — | — | — |
| kev-9b-ft-s18 | noul | granularity | document | 118 | 0.797 | 0.682 | 0.153 | 0.412 | 0.952 |
| kev-9b-ft-s18 | noul | granularity | paragraph | 217 | 0.829 | 0.702 | 0.119 | 0.403 | 1.000 |
| kev-9b-ft-s18 | noul | granularity | sentence | 131 | 0.847 | 0.722 | 0.061 | 0.444 | 1.000 |
| kev-9b-ft-s18 | noul | provenance | human | 466 | 0.826 | 0.702 | 0.107 | 0.417 | 0.988 |
| kev-9b-ft-s18 | noul | role | semantic-detection | 466 | 0.826 | 0.702 | 0.107 | 0.417 | 0.988 |
| kev-9b-ft-s18 | noul | rule_held_out | False | 380 | 0.811 | 0.681 | 0.135 | 0.376 | 0.985 |
| kev-9b-ft-s18 | noul | rule_held_out | True | 86 | 0.895 | 0.804 | 0.088 | 0.609 | 1.000 |
| kev-9b-ft-s18 | noul | source accuracy | human | 466 | 0.826 | — | — | — | — |
| kev-9b-ft-s18 | choice | granularity | document | 4 | 0.250 | 0.250 | 0.655 | — | 0.250 |
| kev-9b-ft-s18 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.124 | — | 0.875 |
| kev-9b-ft-s18 | choice | granularity | sentence | 6 | 0.833 | 0.833 | 0.237 | — | 0.833 |
| kev-9b-ft-s18 | choice | provenance | human | 18 | 0.722 | 0.722 | 0.248 | — | 0.722 |
| kev-9b-ft-s18 | choice | role | finding-confirmation | 18 | 0.722 | 0.722 | 0.248 | — | 0.722 |
| kev-9b-ft-s18 | choice | rule_held_out | False | 17 | 0.706 | 0.706 | 0.264 | — | 0.706 |
| kev-9b-ft-s18 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.027 | — | 1.000 |
| kev-9b-ft-s18 | choice | source accuracy | human | 18 | 0.722 | — | — | — | — |
| kev-9b-ft-s19 | noul | granularity | document | 118 | 0.797 | 0.682 | 0.168 | 0.412 | 0.952 |
| kev-9b-ft-s19 | noul | granularity | paragraph | 217 | 0.843 | 0.726 | 0.149 | 0.452 | 1.000 |
| kev-9b-ft-s19 | noul | granularity | sentence | 131 | 0.847 | 0.739 | 0.115 | 0.500 | 0.979 |
| kev-9b-ft-s19 | noul | provenance | human | 466 | 0.833 | 0.718 | 0.135 | 0.455 | 0.982 |
| kev-9b-ft-s19 | noul | role | semantic-detection | 466 | 0.833 | 0.718 | 0.135 | 0.455 | 0.982 |
| kev-9b-ft-s19 | noul | rule_held_out | False | 380 | 0.816 | 0.693 | 0.156 | 0.404 | 0.982 |
| kev-9b-ft-s19 | noul | rule_held_out | True | 86 | 0.907 | 0.840 | 0.091 | 0.696 | 0.984 |
| kev-9b-ft-s19 | noul | source accuracy | human | 466 | 0.833 | — | — | — | — |
| kev-9b-ft-s19 | choice | granularity | document | 4 | 0.250 | 0.250 | 0.726 | — | 0.250 |
| kev-9b-ft-s19 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.117 | — | 0.875 |
| kev-9b-ft-s19 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.311 | — | 0.667 |
| kev-9b-ft-s19 | choice | provenance | human | 18 | 0.667 | 0.667 | 0.317 | — | 0.667 |
| kev-9b-ft-s19 | choice | role | finding-confirmation | 18 | 0.667 | 0.667 | 0.317 | — | 0.667 |
| kev-9b-ft-s19 | choice | rule_held_out | False | 17 | 0.647 | 0.647 | 0.336 | — | 0.647 |
| kev-9b-ft-s19 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.005 | — | 1.000 |
| kev-9b-ft-s19 | choice | source accuracy | human | 18 | 0.667 | — | — | — | — |
| laya-english | noul | granularity | document | 118 | 0.534 | 0.533 | 0.204 | 0.529 | 0.536 |
| laya-english | noul | granularity | paragraph | 217 | 0.475 | 0.487 | 0.248 | 0.516 | 0.458 |
| laya-english | noul | granularity | sentence | 131 | 0.473 | 0.404 | 0.265 | 0.250 | 0.558 |
| laya-english | noul | provenance | human | 466 | 0.489 | 0.476 | 0.235 | 0.447 | 0.506 |
| laya-english | noul | role | semantic-detection | 466 | 0.489 | 0.476 | 0.235 | 0.447 | 0.506 |
| laya-english | noul | rule_held_out | False | 380 | 0.492 | 0.485 | 0.230 | 0.468 | 0.502 |
| laya-english | noul | rule_held_out | True | 86 | 0.477 | 0.436 | 0.306 | 0.348 | 0.524 |
| laya-english | noul | source accuracy | human | 466 | 0.489 | — | — | — | — |
| laya-english | choice | granularity | document | 4 | 0.500 | 0.500 | 0.276 | — | 0.500 |
| laya-english | choice | granularity | paragraph | 8 | 0.000 | 0.000 | 0.408 | — | 0.000 |
| laya-english | choice | granularity | sentence | 6 | 0.500 | 0.500 | 0.225 | — | 0.500 |
| laya-english | choice | provenance | human | 18 | 0.278 | 0.278 | 0.294 | — | 0.278 |
| laya-english | choice | role | finding-confirmation | 18 | 0.278 | 0.278 | 0.294 | — | 0.278 |
| laya-english | choice | rule_held_out | False | 17 | 0.294 | 0.294 | 0.285 | — | 0.294 |
| laya-english | choice | rule_held_out | True | 1 | 0.000 | 0.000 | 0.447 | — | 0.000 |
| laya-english | choice | source accuracy | human | 18 | 0.278 | — | — | — | — |
| laya-multilingual | noul | granularity | document | 118 | 0.568 | 0.574 | 0.264 | 0.588 | 0.560 |
| laya-multilingual | noul | granularity | paragraph | 217 | 0.465 | 0.481 | 0.348 | 0.516 | 0.445 |
| laya-multilingual | noul | granularity | sentence | 131 | 0.710 | 0.619 | 0.185 | 0.417 | 0.821 |
| laya-multilingual | noul | provenance | human | 466 | 0.560 | 0.544 | 0.267 | 0.508 | 0.581 |
| laya-multilingual | noul | role | semantic-detection | 466 | 0.560 | 0.544 | 0.267 | 0.508 | 0.581 |
| laya-multilingual | noul | rule_held_out | False | 380 | 0.587 | 0.565 | 0.246 | 0.514 | 0.616 |
| laya-multilingual | noul | rule_held_out | True | 86 | 0.442 | 0.453 | 0.418 | 0.478 | 0.429 |
| laya-multilingual | noul | source accuracy | human | 466 | 0.560 | — | — | — | — |
| laya-multilingual | choice | granularity | document | 4 | 0.250 | 0.250 | 0.623 | — | 0.250 |
| laya-multilingual | choice | granularity | paragraph | 8 | 0.000 | 0.000 | 0.471 | — | 0.000 |
| laya-multilingual | choice | granularity | sentence | 6 | 0.000 | 0.000 | 0.653 | — | 0.000 |
| laya-multilingual | choice | provenance | human | 18 | 0.056 | 0.056 | 0.523 | — | 0.056 |
| laya-multilingual | choice | role | finding-confirmation | 18 | 0.056 | 0.056 | 0.523 | — | 0.056 |
| laya-multilingual | choice | rule_held_out | False | 17 | 0.059 | 0.059 | 0.528 | — | 0.059 |
| laya-multilingual | choice | rule_held_out | True | 1 | 0.000 | 0.000 | 0.442 | — | 0.000 |
| laya-multilingual | choice | source accuracy | human | 18 | 0.056 | — | — | — | — |
| laya-typed-decisions | noul | granularity | document | 118 | 0.627 | 0.554 | 0.064 | 0.382 | 0.726 |
| laya-typed-decisions | noul | granularity | paragraph | 217 | 0.590 | 0.495 | 0.077 | 0.274 | 0.716 |
| laya-typed-decisions | noul | granularity | sentence | 131 | 0.664 | 0.527 | 0.124 | 0.222 | 0.832 |
| laya-typed-decisions | noul | provenance | human | 466 | 0.620 | 0.520 | 0.055 | 0.288 | 0.751 |
| laya-typed-decisions | noul | role | semantic-detection | 466 | 0.620 | 0.520 | 0.055 | 0.288 | 0.751 |
| laya-typed-decisions | noul | rule_held_out | False | 380 | 0.632 | 0.525 | 0.067 | 0.275 | 0.775 |
| laya-typed-decisions | noul | rule_held_out | True | 86 | 0.570 | 0.499 | 0.123 | 0.348 | 0.651 |
| laya-typed-decisions | noul | source accuracy | human | 466 | 0.620 | — | — | — | — |
| laya-typed-decisions | choice | granularity | document | 4 | 0.250 | 0.250 | 0.392 | — | 0.250 |
| laya-typed-decisions | choice | granularity | paragraph | 8 | 0.125 | 0.125 | 0.272 | — | 0.125 |
| laya-typed-decisions | choice | granularity | sentence | 6 | 0.167 | 0.167 | 0.213 | — | 0.167 |
| laya-typed-decisions | choice | provenance | human | 18 | 0.167 | 0.167 | 0.279 | — | 0.167 |
| laya-typed-decisions | choice | role | finding-confirmation | 18 | 0.167 | 0.167 | 0.279 | — | 0.167 |
| laya-typed-decisions | choice | rule_held_out | False | 17 | 0.176 | 0.176 | 0.271 | — | 0.176 |
| laya-typed-decisions | choice | rule_held_out | True | 1 | 0.000 | 0.000 | 0.420 | — | 0.000 |
| laya-typed-decisions | choice | source accuracy | human | 18 | 0.167 | — | — | — | — |
| laya-typed-decisions-ft-s17 | noul | granularity | document | 118 | 0.780 | 0.653 | 0.183 | 0.353 | 0.952 |
| laya-typed-decisions-ft-s17 | noul | granularity | paragraph | 217 | 0.728 | 0.592 | 0.228 | 0.274 | 0.910 |
| laya-typed-decisions-ft-s17 | noul | granularity | sentence | 131 | 0.756 | 0.607 | 0.208 | 0.278 | 0.937 |
| laya-typed-decisions-ft-s17 | noul | provenance | human | 466 | 0.749 | 0.612 | 0.210 | 0.295 | 0.928 |
| laya-typed-decisions-ft-s17 | noul | role | semantic-detection | 466 | 0.749 | 0.612 | 0.210 | 0.295 | 0.928 |
| laya-typed-decisions-ft-s17 | noul | rule_held_out | False | 380 | 0.750 | 0.616 | 0.209 | 0.303 | 0.930 |
| laya-typed-decisions-ft-s17 | noul | rule_held_out | True | 86 | 0.744 | 0.591 | 0.224 | 0.261 | 0.921 |
| laya-typed-decisions-ft-s17 | noul | source accuracy | human | 466 | 0.749 | — | — | — | — |
| laya-typed-decisions-ft-s17 | choice | granularity | document | 4 | 0.500 | 0.500 | 0.380 | — | 0.500 |
| laya-typed-decisions-ft-s17 | choice | granularity | paragraph | 8 | 0.750 | 0.750 | 0.207 | — | 0.750 |
| laya-typed-decisions-ft-s17 | choice | granularity | sentence | 6 | 0.833 | 0.833 | 0.158 | — | 0.833 |
| laya-typed-decisions-ft-s17 | choice | provenance | human | 18 | 0.722 | 0.722 | 0.179 | — | 0.722 |
| laya-typed-decisions-ft-s17 | choice | role | finding-confirmation | 18 | 0.722 | 0.722 | 0.179 | — | 0.722 |
| laya-typed-decisions-ft-s17 | choice | rule_held_out | False | 17 | 0.765 | 0.765 | 0.150 | — | 0.765 |
| laya-typed-decisions-ft-s17 | choice | rule_held_out | True | 1 | 0.000 | 0.000 | 0.683 | — | 0.000 |
| laya-typed-decisions-ft-s17 | choice | source accuracy | human | 18 | 0.722 | — | — | — | — |
| laya-typed-decisions-ft-s18 | noul | granularity | document | 118 | 0.746 | 0.603 | 0.202 | 0.265 | 0.940 |
| laya-typed-decisions-ft-s18 | noul | granularity | paragraph | 217 | 0.737 | 0.584 | 0.195 | 0.226 | 0.942 |
| laya-typed-decisions-ft-s18 | noul | granularity | sentence | 131 | 0.794 | 0.651 | 0.179 | 0.333 | 0.968 |
| laya-typed-decisions-ft-s18 | noul | provenance | human | 466 | 0.755 | 0.607 | 0.176 | 0.265 | 0.949 |
| laya-typed-decisions-ft-s18 | noul | role | semantic-detection | 466 | 0.755 | 0.607 | 0.176 | 0.265 | 0.949 |
| laya-typed-decisions-ft-s18 | noul | rule_held_out | False | 380 | 0.755 | 0.609 | 0.188 | 0.266 | 0.952 |
| laya-typed-decisions-ft-s18 | noul | rule_held_out | True | 86 | 0.756 | 0.599 | 0.169 | 0.261 | 0.937 |
| laya-typed-decisions-ft-s18 | noul | source accuracy | human | 466 | 0.755 | — | — | — | — |
| laya-typed-decisions-ft-s18 | choice | granularity | document | 4 | 0.250 | 0.250 | 0.619 | — | 0.250 |
| laya-typed-decisions-ft-s18 | choice | granularity | paragraph | 8 | 0.625 | 0.625 | 0.360 | — | 0.625 |
| laya-typed-decisions-ft-s18 | choice | granularity | sentence | 6 | 0.667 | 0.667 | 0.294 | — | 0.667 |
| laya-typed-decisions-ft-s18 | choice | provenance | human | 18 | 0.556 | 0.556 | 0.386 | — | 0.556 |
| laya-typed-decisions-ft-s18 | choice | role | finding-confirmation | 18 | 0.556 | 0.556 | 0.386 | — | 0.556 |
| laya-typed-decisions-ft-s18 | choice | rule_held_out | False | 17 | 0.529 | 0.529 | 0.378 | — | 0.529 |
| laya-typed-decisions-ft-s18 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.530 | — | 1.000 |
| laya-typed-decisions-ft-s18 | choice | source accuracy | human | 18 | 0.556 | — | — | — | — |
| laya-typed-decisions-ft-s19 | noul | granularity | document | 118 | 0.763 | 0.606 | 0.211 | 0.235 | 0.976 |
| laya-typed-decisions-ft-s19 | noul | granularity | paragraph | 217 | 0.710 | 0.569 | 0.234 | 0.242 | 0.897 |
| laya-typed-decisions-ft-s19 | noul | granularity | sentence | 131 | 0.786 | 0.637 | 0.179 | 0.306 | 0.968 |
| laya-typed-decisions-ft-s19 | noul | provenance | human | 466 | 0.745 | 0.597 | 0.210 | 0.258 | 0.937 |
| laya-typed-decisions-ft-s19 | noul | role | semantic-detection | 466 | 0.745 | 0.597 | 0.210 | 0.258 | 0.937 |
| laya-typed-decisions-ft-s19 | noul | rule_held_out | False | 380 | 0.745 | 0.602 | 0.213 | 0.266 | 0.937 |
| laya-typed-decisions-ft-s19 | noul | rule_held_out | True | 86 | 0.744 | 0.577 | 0.207 | 0.217 | 0.937 |
| laya-typed-decisions-ft-s19 | noul | source accuracy | human | 466 | 0.745 | — | — | — | — |
| laya-typed-decisions-ft-s19 | choice | granularity | document | 4 | 0.250 | 0.250 | 0.691 | — | 0.250 |
| laya-typed-decisions-ft-s19 | choice | granularity | paragraph | 8 | 0.875 | 0.875 | 0.235 | — | 0.875 |
| laya-typed-decisions-ft-s19 | choice | granularity | sentence | 6 | 0.833 | 0.833 | 0.161 | — | 0.833 |
| laya-typed-decisions-ft-s19 | choice | provenance | human | 18 | 0.722 | 0.722 | 0.289 | — | 0.722 |
| laya-typed-decisions-ft-s19 | choice | role | finding-confirmation | 18 | 0.722 | 0.722 | 0.289 | — | 0.722 |
| laya-typed-decisions-ft-s19 | choice | rule_held_out | False | 17 | 0.706 | 0.706 | 0.276 | — | 0.706 |
| laya-typed-decisions-ft-s19 | choice | rule_held_out | True | 1 | 1.000 | 1.000 | 0.513 | — | 1.000 |
| laya-typed-decisions-ft-s19 | choice | source accuracy | human | 18 | 0.722 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| kev-0.8b | 26 | 0.383 | 0 | 0.531 | 0.593 | 0.593 |
| kev-0.8b-ft-s17 | 26 | 0.764 | 0 | 0.634 | 0.617 | 0.617 |
| kev-0.8b-ft-s18 | 26 | 0.500 | 0 | 0.628 | 0.628 | 0.628 |
| kev-0.8b-ft-s19 | 26 | 0.870 | 0 | 0.652 | 0.602 | 0.602 |
| kev-4b | 26 | 0.340 | 0 | 0.554 | 0.601 | 0.601 |
| kev-4b-ft-s17 | 26 | 0.149 | 0 | 0.725 | 0.737 | 0.737 |
| kev-4b-ft-s18 | 26 | 0.500 | 0 | 0.727 | 0.727 | 0.727 |
| kev-4b-ft-s19 | 26 | 0.894 | 0 | 0.697 | 0.664 | 0.664 |
| kev-9b | 26 | 0.733 | 0 | 0.578 | 0.537 | 0.537 |
| kev-9b-ft-s17 | 26 | 0.500 | 0 | 0.723 | 0.723 | 0.723 |
| kev-9b-ft-s18 | 26 | 0.266 | 0 | 0.702 | 0.719 | 0.719 |
| kev-9b-ft-s19 | 26 | 0.321 | 0 | 0.718 | 0.720 | 0.720 |
| laya-english | 26 | 0.297 | 0 | 0.476 | 0.486 | 0.486 |
| laya-multilingual | 26 | 0.939 | 0 | 0.544 | 0.523 | 0.523 |
| laya-typed-decisions | 26 | 0.338 | 0 | 0.520 | 0.498 | 0.498 |
| laya-typed-decisions-ft-s17 | 26 | 0.688 | 0 | 0.612 | 0.614 | 0.614 |
| laya-typed-decisions-ft-s18 | 26 | 0.362 | 0 | 0.607 | 0.605 | 0.605 |
| laya-typed-decisions-ft-s19 | 26 | 0.738 | 0 | 0.597 | 0.599 | 0.599 |

## Interpretation and caveats

- Test label origins: construction (484). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice real-defect=18; yes/no False=334, True=132. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.13 finding-confirmation, κ=0.02 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
