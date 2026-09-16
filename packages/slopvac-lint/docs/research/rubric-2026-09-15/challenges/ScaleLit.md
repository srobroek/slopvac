## Verdicts

| Claim ID | KEEP/AMEND/REPLACE | reason | evidence refs |
|---|---|---|---|
| C2 | **AMEND** | Keep four dimensions, ordinal integer scores, observable anchors, and per-rule masks. Evidence supports small anchored scales but does not establish exactly 0–3 as universally superior to binary or 1–5 for prose-quality judging. Treat scores as ordinal gates, not interval measurements; require quoted evidence before scoring. | E1–E8; design §2, rubric-design.md:189-212 |
| C10 | **AMEND** | Retain `WARRANT >= 2` and special `HARM == 3` escalation. `<=1` and `==3` are brittle when one-point ratings vary across calls. Calibrate thresholds against repeated-call and human annotations, report score distributions, and abstain near unstable boundaries. | E1, E2, E4, E5 |
| C14 | **KEEP, narrow rationale** | Rejecting a scalar 1–10 global quality score is supported: wide scales exhibit unused ranges, round-number bias, and unstable individual ratings. Do not claim every 1–10 scale is inferior to every 0–3 or 1–5 design; anchored dimensions and evidence obligations are decisive. | E1–E4 |

## Evidence

**E1 — Stureborg et al. (2024)** https://arxiv.org/html/2405.01724v1 — more than **560,000 generated outputs**; GPT-4 Kendall tau averages: 1–5 **.339**, 1–10 **.428**, 1–100 **.383**; 1–100 clusters at round values **60, 70, 80, 90** and largely ignores **1–60**; Krippendorff alpha human **.659** vs GPT-4 **.587**; multi-attribute position correlations **.400, .391, .359, .368**.

**E2 — Wang et al. (2023)** https://ar5iv.labs.arxiv.org/html/2305.17926 — Table 2 GPT-4 position-conflict rates **46.3%** and **5.0%**; ChatGPT **82.5%** and **52.5%**. Vicuna GPT-4 win rate changed **51.3% to 23.8%** under position swap; ChatGPT **2.5% to 82.5%**. Evidence calibration and balanced-position calibration improved alignment **9.8%** and **14.3%**.

**E3 — Chiang & Lee (2023)** https://arxiv.org/html/2310.05657v1 — numeric-only output is “suboptimal”; SummEval coherence Pearson score-only **.344** vs analyze-rate **.635**; Topical-Chat groundedness **.358** vs **.725**; default averaging used **N=20** sequences; some auto-CoT differences were **<.025** and nonsignificant.

**E4 — Nie et al. (2025)** https://arxiv.org/html/2505.19334v1 — GPT-4 Omni DL19 NDCG: 2-point **.645**, 3-point **.711**, 5-point **.736**, 7-point **.747**, 11-point **.737**; only **9/40** model-dataset combinations significantly favored listwise over 11-bin pointwise. This is retrieval evidence, not prose-quality evidence.

**E5 — Zheng et al. (2023)** https://arxiv.org/abs/2306.05685 — indexed paper materials report verbosity attacks fooling Claude/GPT-3.5 about **91%** vs GPT-4 **8.7%**, and self-enhancement about **+10% GPT-4**, **+25% Claude**. These are not scale-width experiments.

**E6 — Prometheus** https://proceedings.iclr.cc/paper_files/paper/2024/file/803485352e61e3ebf41221e4776c9fd4-Paper-Conference.pdf — across **45 customized score rubrics**, Pearson correlation **.897** vs GPT-4 **.882**. Supports detailed anchored 1–5 rubrics, not unanchored global scores. Prometheus 2: https://aclanthology.org/2024.emnlp-main.248/ — four direct-assessment and four pairwise benchmarks, but no scale-width number in abstract.

**E7 — Saito et al. (2023)** https://arxiv.org/abs/2310.10076 — directly studies verbosity bias; source gives no numeric magnitude in abstract.

**E8 — Shankar et al. (2024), EvalGen** https://arxiv.org/abs/2404.12272 — identifies criteria drift; source gives no numeric magnitude in abstract.

**E9 — Thakur et al. (2024)** https://arxiv.org/abs/2406.12624 — abstract gives no exact scale-width, temperature-0 agreement, or binary-vs-Likert number.

## Amendments

> Scores are ordinal labels, not presumed interval measurements. Use the smallest scale that separates actionable states. For v1, use 0–3 with observable, text-grounded anchors. Every non-constant dimension must cite the exact quoted span and the particular distinguishing adjacent levels. FIT and WARRANT remain mandatory; HARM and REPAIR may be constants when rule semantics make them invariant.

> For each scored dimension, emit: (1) exact quote and offsets, (2) named checkable particular or absent element, (3) anchor comparison, (4) integer score. The scorer MUST NOT emit the score before evidence. Evidence is independently checked; unsupported rationale does not satisfy WARRANT.

> Thresholds are policy parameters over ordinal labels. Before release, estimate boundary stability by repeated calls and human adjudication. Report score histograms, boundary disagreement, and abstention rates. If a boundary’s repeated-call agreement is below target, route to ABSTAIN rather than treating a one-point difference as meaningful.

Keep `FIT <= 1` / `WARRANT <= 1` as conservative admission gates, `HARM == 3` as high-risk escalation, and `REPAIR < 3` for clean deletion only if calibration shows it is not overused. Do not interpret ordinal increments as equal severity.

## Unsupported

No primary study directly compares binary vs exactly 0–3 vs 1–5 for prose defect detection. No reliable published number found for temperature-0 repeated-call agreement across these widths. No evidence found that evidence-before-score alone prevents hallucinated quotes. No evidence found that 0–3 is universally more reliable than 1–5. Saito, Shankar, and Thakur abstracts provide no relevant magnitudes.

## Open evaluation questions

1. On a fixed slopvac corpus, what are Krippendorff alpha and exact agreement for binary, 0–3, and 1–5 at temperature 0?
2. Do observable anchors reduce midpoint/round-number clustering?
3. Does quote-first ordering improve quote validity, not merely human-score correlation?
4. Are C10 boundaries stable enough for deterministic routing, or should borderline scores abstain?
5. Does masking constant HARM/REPAIR improve repeatability?
6. Does pairwise defect-present/absent adjudication outperform absolute FIT/WARRANT scoring while preserving HARM/REPAIR severity?

## ChScale post-yield correction (IRC)
Use Chiang & Lee https://arxiv.org/html/2310.05657v1 Table 1/2: SummEval coherence Pearson score-only .344, rate-explain .557, analyze-rate .635; Topical-Chat groundedness .358, .580, .725; rate-explain vs analyze-rate not significantly different overall, so evidence supports rationale+rating, not uniquely evidence-first. Stureborg Table 2 (temp 0): Kendall avg 1-5=.339, 1-10=.428, 1-100=.383. G-Eval direct vs probability normalization is metric-dependent (Spearman .514 vs .502 favours direct; Kendall .418 vs .446 favours normalization).
