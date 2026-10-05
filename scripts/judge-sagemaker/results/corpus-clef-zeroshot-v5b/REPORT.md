# Corpus evaluation report: `corpus-clef-zeroshot-v5b`

## Dataset and coverage

- Campaign: `corpus-20261003-s17-v5b/clef-zeroshot`. Zero-shot Cloudflare Clef decision models (Apache-2.0) on the v5b full test and calibration splits, the same bytes as v5b-full: clef-flash (Cloudflare/clef-flash, 9B, Qwen3.5-9B backbone, one 24 GB L4 on ml.g6.2xlarge) and clef (Cloudflare/clef, 27B, Qwen3.8-27B backbone, bf16 sharded over the four L40S of ml.g6e.12xlarge). No training; each item becomes one System One record (state plus the question's type, instructions and criteria) answered by the release's joint_schema_model.systemone under transformers 5.10.2 on the DLC's torch 2.8.0. Kev and Laya base arms and the Kev fine-tunes are in v5b-full.
- Dataset builder: `corpus-export`; same calibration/test hashes are verified for all arms.
- Evaluated arms: 2 of 2 required (`clef-flash`, `clef`). Missing arms: none; the generator refuses to render while any required arm lacks complete artifacts.
- Failed or stopped SageMaker attempts: 7 of 9 campaign jobs; each arm's accepted run and every unfinished attempt are listed under *Campaign jobs, failures, and cost*.
- Calibration: 1720 examples; SHA-256 `8534bee7b935ae80b47d35e1e96a4a288ab3ba86c6bfe851ff01e8dcf3300b1b`.
- Test: 3671 examples; SHA-256 `a77f6f64b85b81a13330df57b8cd3973edd2b295ae30efdf4ddc12a4a8bb0b31`.
- Test composition: label origins `construction`=3092, `human-adjudication`=258, `llm-review-consensus`=321; choice labels insufficient-context=2, no-defect=821, real-defect=774; yes/no labels False=1151, True=923.

## Headline by role

Each arm's numbers come from `results/corpus-clef-zeroshot-v5b/<arm>/results/<arm>.json`: balanced accuracy and its cluster-bootstrap 95% CI from `metrics.<kind>.test_raw` / `test_raw_ci95`, ECE-15 from `test_raw` (raw) and `test_cal` (temperature fit on calibration), class recalls from `metrics.<kind>.test_slices.role.<role>` (metrics.py names them by class index: `good_recall` is choice real-defect / yes-no False, `bad_recall` is choice no-defect / yes-no True). GPU, single-request p50 over all test items (`latency.single_request_all_test_ms`), and evaluation USD (cost ledger, matched by the arm's `manifest.json` job) are per arm. Fine-tune rows give the seed mean ± sample SD [min–max] over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items: 1597 (real-defect=774, no-defect=821).

| Arm | Bal. acc. | Bal. acc. 95% CI | real-defect recall | no-defect recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef-flash | 0.513 | 0.466–0.558 | 0.413 | 0.613 | 0.107 | 0.076 | NVIDIA L4 | 206.469 | $1.5938 |
| clef | 0.656 | 0.617–0.694 | 0.898 | 0.414 | 0.060 | 0.053 | NVIDIA L40S | 171.009 | $8.8622 |

- Best single arm: `clef` (balanced accuracy 0.656).

### semantic-detection (`noul`)

Test items: 2074 (True=923, False=1151).

| Arm | Bal. acc. | Bal. acc. 95% CI | True recall | False recall | ECE raw | ECE cal. | GPU | p50 ms | Eval USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef-flash | 0.672 | 0.617–0.724 | 0.433 | 0.910 | 0.172 | 0.060 | NVIDIA L4 | 206.469 | $1.5938 |
| clef | 0.808 | 0.763–0.847 | 0.758 | 0.858 | 0.074 | 0.040 | NVIDIA L40S | 171.009 | $8.8622 |

- Best single arm: `clef` (balanced accuracy 0.808).

## Balanced accuracy by test label origin

Computed by this generator from each arm's forward-order test predictions (`results/corpus-clef-zeroshot-v5b/<arm>/results/predictions/<arm>.jsonl`) joined by item id to the arm's hash-checked test split (`<arm>/data/test.jsonl`), which supplies `label` and `label_origin`. Balanced accuracy is the headline's (`test_raw`): the mean recall of real-defect and no-defect for finding confirmation, where insufficient-context items count in n only, and of True and False for semantic detection. The *All* column reproduces each arm's headline; the generator refuses to render when it does not. A slice that holds one class reduces to that class's recall, and small slices are noisy. Fine-tune family rows give the seed mean ± sample SD over seeds 17, 18, 19.

### finding-confirmation (`choice`)

Test items by origin: `human-adjudication` 173 (real-defect=96, no-defect=75, insufficient-context=2); `llm-review-consensus` 114 (real-defect=23, no-defect=91); `construction` 1310 (real-defect=655, no-defect=655).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| clef-flash | 0.513 | 0.544 | 0.596 | 0.505 |
| clef | 0.656 | 0.524 | 0.835 | 0.653 |

### semantic-detection (`noul`)

Test items by origin: `human-adjudication` 85 (False=57, True=28); `llm-review-consensus` 207 (False=203, True=4); `construction` 1782 (False=891, True=891).

| Arm | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- |
| clef-flash | 0.672 | 0.421 | 0.730 | 0.675 |
| clef | 0.808 | 0.513 | 0.961 | 0.814 |

## Comparison with `corpus-v5b-full`

Both campaigns score the same test and calibration export (hashes verified). Δ is `corpus-clef-zeroshot-v5b` minus `corpus-v5b-full` seed means for the same family and seeds; "Seeds better" counts seeds whose balanced accuracy is higher here than the same seed there.

No fine-tuned family is complete in both campaigns.

## Label-source ablation

Campaigns on this campaign's test and calibration export (hashes verified): `corpus-clef-zeroshot-v5b` (`corpus-20261003-s17-v5b/clef-zeroshot`); `corpus-v5b-full` (`corpus-20261003-s17-v5b/full`). Each campaign's notes say what its fine-tunes trained on.

Cells are balanced accuracy as defined under *Balanced accuracy by test label origin*: the seed mean ± sample SD of a complete fine-tune family, or a single base-arm run taken from the first listed campaign that evaluates it. A gap between two families reflects more than training-seed variation only when it is well beyond both SDs.

### finding-confirmation (`choice`)

| Family | Arms from | Seeds | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- | --- | --- |
| clef-flash | base, `corpus-clef-zeroshot-v5b` | 1 | 0.513 | 0.544 | 0.596 | 0.505 |
| clef | base, `corpus-clef-zeroshot-v5b` | 1 | 0.656 | 0.524 | 0.835 | 0.653 |
| kev-0.8b | base, `corpus-v5b-full` | 1 | 0.238 | 0.446 | 0.330 | 0.195 |
| kev-0.8b FT | `corpus-v5b-full` | 3 | 0.745 ± 0.011 | 0.492 ± 0.006 | 0.741 ± 0.074 | 0.773 ± 0.017 |
| kev-4b | base, `corpus-v5b-full` | 1 | 0.308 | 0.376 | 0.317 | 0.292 |
| kev-4b FT | `corpus-v5b-full` | 3 | 0.798 ± 0.003 | 0.496 ± 0.008 | 0.761 ± 0.041 | 0.837 ± 0.001 |
| kev-9b | base, `corpus-v5b-full` | 1 | 0.503 | 0.503 | 0.606 | 0.489 |
| kev-9b FT | `corpus-v5b-full` | 3 | 0.815 ± 0.009 | 0.480 ± 0.015 | 0.800 ± 0.008 | 0.860 ± 0.010 |
| laya-english | base, `corpus-v5b-full` | 1 | 0.431 | 0.426 | 0.296 | 0.440 |
| laya-multilingual | base, `corpus-v5b-full` | 1 | 0.354 | 0.291 | 0.274 | 0.372 |
| laya-typed-decisions | base, `corpus-v5b-full` | 1 | 0.360 | 0.386 | 0.252 | 0.362 |

### semantic-detection (`noul`)

| Family | Arms from | Seeds | All | human-adjudication | llm-review-consensus | construction |
| --- | --- | --- | --- | --- | --- | --- |
| clef-flash | base, `corpus-clef-zeroshot-v5b` | 1 | 0.672 | 0.421 | 0.730 | 0.675 |
| clef | base, `corpus-clef-zeroshot-v5b` | 1 | 0.808 | 0.513 | 0.961 | 0.814 |
| kev-0.8b | base, `corpus-v5b-full` | 1 | 0.502 | 0.500 | 0.498 | 0.500 |
| kev-0.8b FT | `corpus-v5b-full` | 3 | 0.775 ± 0.005 | 0.460 ± 0.010 | 0.869 ± 0.004 | 0.769 ± 0.006 |
| kev-4b | base, `corpus-v5b-full` | 1 | 0.545 | 0.475 | 0.483 | 0.547 |
| kev-4b FT | `corpus-v5b-full` | 3 | 0.903 ± 0.003 | 0.475 ± 0.027 | 0.869 ± 0.004 | 0.914 ± 0.003 |
| kev-9b | base, `corpus-v5b-full` | 1 | 0.679 | 0.423 | 0.951 | 0.685 |
| kev-9b FT | `corpus-v5b-full` | 3 | 0.899 ± 0.006 | 0.448 ± 0.015 | 0.913 ± 0.073 | 0.909 ± 0.005 |
| laya-english | base, `corpus-v5b-full` | 1 | 0.469 | 0.630 | 0.619 | 0.471 |
| laya-multilingual | base, `corpus-v5b-full` | 1 | 0.545 | 0.613 | 0.501 | 0.554 |
| laya-typed-decisions | base, `corpus-v5b-full` | 1 | 0.505 | 0.612 | 0.536 | 0.511 |

## Campaign jobs, failures, and cost

Every cost-ledger job attributed to this campaign the way the scheduler attributes them (training on this export; evaluations marked with this campaign). C / F / S counts Completed / Failed / Stopped. The accepted training job is the one whose `model.tar.gz` the arm's evaluation loaded (`manifest.json` `checkpoint_ref`); a failed job can be accepted when it saved a validated checkpoint before failing. Submissions that SageMaker rejected bill $0.

| Arm | Training jobs C / F / S | Training USD (all) | Accepted training job | Accepted training USD | Eval jobs C / F / S | Eval USD (all) | Arm USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| clef-flash | — | — | — | — | 1 / 0 / 7 | $1.59 | $1.59 |
| clef | — | — | — | — | 1 / 0 / 0 | $8.86 | $8.86 |

Campaign total: **$10.46 USD** (training $0.00, evaluation $10.46) over 0 training and 9 evaluation jobs.

### Failed and stopped attempts

| Target | Task | Status | Jobs | USD | Reason |
| --- | --- | --- | --- | --- | --- |
| clef-flash | evaluation | Stopped | 7 | $0.00 | scheduler marker `capacity_rotation` |

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

### clef-flash

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef-flash | 2074 | 0.698 | 0.672 | 0.811 | 0.226 | 0.688 | 0.172 | 0.196 | 0.575 | 0.060 | 0.617–0.724 | 0.122–0.224 | 0.035–0.110 | 0.433 | 0.910 | — | — | — | 206.469 | 413.495 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef-flash | 1597 | 0.517 | 0.513 | 0.584 | 0.645 | 1.083 | 0.107 | 0.627 | 1.042 | 0.076 | 0.466–0.558 | 0.074–0.147 | 0.041–0.120 | — | — | 0.115 | 0.998 | 0.000 | 206.469 | 413.495 |

### clef

#### noul

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef | 2074 | 0.813 | 0.808 | 0.903 | 0.134 | 0.425 | 0.074 | 0.128 | 0.405 | 0.040 | 0.763–0.847 | 0.045–0.107 | 0.025–0.067 | 0.758 | 0.858 | — | — | — | 171.009 | 366.200 |

#### choice

| Arm / seed summary | N | Accuracy | Balanced acc. | AUROC | Brier raw | NLL raw | ECE raw | Brier cal. | NLL cal. | ECE cal. | Bal. acc. 95% CI | ECE raw 95% CI | ECE cal. 95% CI | Bad recall | Good recall | Abstain | Order-swap agree | Order-swap prob. shift | Latency p50 ms | Latency p95 ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef | 1597 | 0.648 | 0.656 | 0.830 | 0.481 | 0.833 | 0.060 | 0.480 | 0.830 | 0.053 | 0.617–0.694 | 0.042–0.102 | 0.039–0.092 | — | — | 0.056 | 0.997 | 0.000 | 171.009 | 366.200 |

## Latency by GPU class and billed evaluation cost

| Arm | GPU class | Instance type | Region | p50 ms | p95 ms | Billable seconds | Billed USD | Job |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef | NVIDIA L40S | ml.g6e.12xlarge | us-west-2 | 171.009 | 366.200 | 1994 | $8.8622 | sv-eval-clef-261005050400799362 |
| clef-flash | NVIDIA L4 | ml.g6.2xlarge | us-east-2 | 206.469 | 413.495 | 2295 | $1.5938 | sv-eval-clef-flash-261005073926441797 |

Total billed evaluation cost for the reported arms: **$10.4560 USD** (completed SageMaker jobs matched by job name and ARN in `USD` ledger).

## Per-arm slice and source details

All available test slice/source cells are listed per arm; subgroup scores are descriptive and not pooled.

| Arm | Metric kind | Breakdown | Value | N | Accuracy | Balanced accuracy | ECE-15 | Bad recall | Good recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clef | noul | granularity | document | 943 | 0.812 | 0.807 | 0.069 | 0.730 | 0.883 |
| clef | noul | granularity | paragraph | 754 | 0.792 | 0.788 | 0.090 | 0.756 | 0.821 |
| clef | noul | granularity | sentence | 377 | 0.859 | 0.857 | 0.054 | 0.847 | 0.868 |
| clef | noul | provenance | generated | 201 | 0.791 | 0.692 | 0.125 | 0.560 | 0.824 |
| clef | noul | provenance | human | 1873 | 0.816 | 0.814 | 0.069 | 0.764 | 0.864 |
| clef | noul | role | semantic-detection | 2074 | 0.813 | 0.808 | 0.074 | 0.758 | 0.858 |
| clef | noul | rule_held_out | False | 1314 | 0.783 | 0.742 | 0.109 | 0.630 | 0.854 |
| clef | noul | rule_held_out | True | 760 | 0.866 | 0.867 | 0.032 | 0.864 | 0.870 |
| clef | noul | source accuracy | generated | 201 | 0.791 | — | — | — | — |
| clef | noul | source accuracy | human | 1873 | 0.816 | — | — | — | — |
| clef | choice | granularity | document | 735 | 0.631 | 0.633 | 0.065 | 0.365 | 0.901 |
| clef | choice | granularity | paragraph | 547 | 0.665 | 0.428 | 0.074 | 0.394 | 0.890 |
| clef | choice | granularity | sentence | 315 | 0.657 | 0.478 | 0.090 | 0.527 | 0.908 |
| clef | choice | provenance | generated | 217 | 0.622 | 0.645 | 0.113 | 0.484 | 0.806 |
| clef | choice | provenance | human | 1380 | 0.652 | 0.437 | 0.067 | 0.402 | 0.910 |
| clef | choice | role | finding-confirmation | 1597 | 0.648 | 0.437 | 0.060 | 0.414 | 0.898 |
| clef | choice | rule_held_out | False | 907 | 0.744 | 0.450 | 0.052 | 0.456 | 0.893 |
| clef | choice | rule_held_out | True | 690 | 0.522 | 0.652 | 0.136 | 0.390 | 0.914 |
| clef | choice | source accuracy | generated | 217 | 0.622 | — | — | — | — |
| clef | choice | source accuracy | human | 1380 | 0.652 | — | — | — | — |
| clef-flash | noul | granularity | document | 943 | 0.673 | 0.655 | 0.191 | 0.405 | 0.905 |
| clef-flash | noul | granularity | paragraph | 754 | 0.710 | 0.685 | 0.169 | 0.455 | 0.914 |
| clef-flash | noul | granularity | sentence | 377 | 0.735 | 0.689 | 0.151 | 0.467 | 0.912 |
| clef-flash | noul | provenance | generated | 201 | 0.831 | 0.526 | 0.092 | 0.120 | 0.932 |
| clef-flash | noul | provenance | human | 1873 | 0.683 | 0.674 | 0.181 | 0.442 | 0.906 |
| clef-flash | noul | role | semantic-detection | 2074 | 0.698 | 0.672 | 0.172 | 0.433 | 0.910 |
| clef-flash | noul | rule_held_out | False | 1314 | 0.761 | 0.654 | 0.129 | 0.363 | 0.945 |
| clef-flash | noul | rule_held_out | True | 760 | 0.588 | 0.637 | 0.259 | 0.491 | 0.783 |
| clef-flash | noul | source accuracy | generated | 201 | 0.831 | — | — | — | — |
| clef-flash | noul | source accuracy | human | 1873 | 0.683 | — | — | — | — |
| clef-flash | choice | granularity | document | 735 | 0.518 | 0.518 | 0.092 | 0.608 | 0.427 |
| clef-flash | choice | granularity | paragraph | 547 | 0.510 | 0.680 | 0.112 | 0.626 | 0.413 |
| clef-flash | choice | granularity | sentence | 315 | 0.524 | 0.657 | 0.148 | 0.605 | 0.367 |
| clef-flash | choice | provenance | generated | 217 | 0.576 | 0.555 | 0.140 | 0.702 | 0.409 |
| clef-flash | choice | provenance | human | 1380 | 0.507 | 0.670 | 0.104 | 0.597 | 0.414 |
| clef-flash | choice | role | finding-confirmation | 1597 | 0.517 | 0.675 | 0.107 | 0.613 | 0.413 |
| clef-flash | choice | rule_held_out | False | 907 | 0.479 | 0.668 | 0.103 | 0.580 | 0.425 |
| clef-flash | choice | rule_held_out | True | 690 | 0.567 | 0.503 | 0.153 | 0.632 | 0.374 |
| clef-flash | choice | source accuracy | generated | 217 | 0.576 | — | — | — | — |
| clef-flash | choice | source accuracy | human | 1380 | 0.507 | — | — | — | — |

## Decision thresholds (yes/no questions)

Thresholds are fit on calibration only: one global threshold that maximises balanced accuracy, and one per rule where each class has at least 5 calibration items (other rules fall back to the global one). Test balanced accuracy at each:

| arm | calibration n | global threshold | rules with own threshold | test bal. acc @0.5 | @global | @per-rule |
| --- | --- | --- | --- | --- | --- | --- |
| clef | 1095 | 0.315 | 33 | 0.808 | 0.819 | 0.831 |
| clef-flash | 1095 | 0.208 | 33 | 0.672 | 0.721 | 0.732 |

## Interpretation and caveats

- Test label origins: construction (3092), human-adjudication (258), llm-review-consensus (321). Constructions are injected known-answer cases, not a random sample of deployment text; human-adjudicated rows are the natural-text estimate once present.
- Test class counts: choice insufficient-context=2, no-defect=821, real-defect=774; yes/no False=1151, True=923. Plain accuracy is not comparable across splits with different class balance; read balanced accuracy and AUROC.
- Training labels come from a teacher panel with κ=0.30 finding-confirmation, κ=0.30 semantic-detection. Treat model-vs-label scores on panel-labelled rows as agreement with the panel, not with human consensus.
- Cluster-bootstrap intervals quantify only within-test-set uncertainty. They do not capture corpus construction, prompt, model-release, or deployment variation; overall intervals are not subgroup-specific.
- Calibration temperature is fit on the calibration split and applied to test predictions; it does not turn test data into calibration data.
- Latency is recorded single-request p50/p95, grouped by actual GPU class/instance/region; comparisons across different hardware are confounded by the hardware and are not concurrency/throughput comparisons.
- Billed USD is evaluation-job instance time from the completed SageMaker ledger entry, not a full lifecycle or inference cost estimate. Campaign totals add every attributed training and evaluation attempt, failed and stopped ones included.
- Fine-tune seed spread describes training-seed variation on one fixed corpus; it is not uncertainty across independent evaluation sets.
