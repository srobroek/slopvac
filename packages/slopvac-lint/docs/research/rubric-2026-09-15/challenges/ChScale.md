Claim: C2/C10 treat four 0–3 ratings as a justified measurement scale with stable cut-points, while C14 rejects one 1–10 score. The evidence supports anchored, decomposed judgments—not those exact integers or thresholds.

VERDICT: CHALLENGED

## Verdicts

| Claim ID | Verdict | One-line reason | Evidence |
|---|---|---|---|
| C2 (scale) | AMEND | Keep four observable levels, but make them named ordinal categories whose numbers are serialization codes; no study directly establishes 0–3 as superior to binary+severity or 1–5. | E1–E5, E9–E11 |
| C10 (thresholds) | AMEND | The reject boundaries follow the anchor semantics, but the exact cut-points are unvalidated; an ambiguous FIT=2 should not independently reach warning. | E1, E2, E5–E8, E13 |
| C14 (scalar row) | AMEND | Reject a single holistic score because it collapses actionable dimensions, not because 1–10 is intrinsically unreliable; wider scales sometimes perform better. | E2–E5, E9–E10 |

## Assumptions-that-fail

| Assumption | Evidence |
|---|---|
| Four levels “force a side” and therefore beat five. | G-Eval reports score 3 dominating a 1–5 scale but gives no clustering rate (E4). No located experiment compares anchored four-level prose judgments with anchored five-level judgments. |
| Fewer categories necessarily improve consistency. | At temperature 1.0, Llama-2’s Krippendorff α was 0.801 on numeric 10-point, 0.683 on numeric 5-point, 0.532 binary, and 0.366 verbal Likert; GPT-4 was 0.961, 0.954, 0.881, and 0.835 respectively (E3). |
| A 1–10 scale is itself the defect. | Stureborg et al. found 1–10 best on average Kendall τ=0.428 among tested granularities; a 2025 IR study improved mean NDCG@10 from 0.547 (2-point) to 0.630 (5), 0.634 (7), and 0.638 (11) (E5, E10). |
| C10’s numerical boundaries are calibrated. | The design executed 15 constructed cases, not an adjudicated corpus or scale-width/threshold comparison (E1). No published source located validates FIT≤1, WARRANT≤1, or HARM≥2 for this task. |

## Alternatives

| Rank | Alternative | Why more likely |
|---:|---|---|
| 1 | Four **named ordinal categories**, with 0–3 only as wire codes; semantic membership tests determine admission/severity. | Preserves C2’s observable anchors and C10’s actionability without pretending equal intervals; detailed criteria improve consistency, while bare verbal labels do not (E3, E9). |
| 2 | Binary checklist for FIT/WARRANT subconditions plus separate HARM and REPAIR enums. | CheckEval’s decomposed Boolean questions raised all-model inter-evaluator α from 0.09 (G-Eval) to 0.48 on SummEval and from 0.06 to 0.45 on Topical-Chat at temperature 0 (E2). It may, however, lose partial/ambiguous diagnostic states. |
| 3 | Fully anchored 1–5 per dimension. | Prometheus shows that five described scoring decisions can work (human Pearson r=0.897), but it was trained for that format and does not establish a zero-shot advantage here (E9). |

## Evidence

- **E1 — Repository design:** `local/rubric-design.md:57-96,198-204,332-338,410-457`. C2 defines observable 0–3 FIT/HARM/WARRANT/REPAIR anchors; 35/65 rules mask dimensions; C10 uses the stated cut-points; only `ste-safety` can reach error; the 15/15 run used constructed cases. Source gives no comparative scale or threshold number.
- **E2 — [CheckEval](https://arxiv.org/html/2403.18771):** 12 evaluators; temperature=0, n=1. Decomposed yes/no checklists versus 1–5-style G-Eval produced all-model α 0.48 vs 0.09 (SummEval) and 0.45 vs 0.06 (Topical-Chat); top-three α 0.65 vs 0.07 and 0.57 vs 0.03. This compares decomposition+format, not width alone.
- **E3 — [Evaluating the Consistency of LLM Evaluators](https://arxiv.org/html/2412.00543):** five samples at temperature 1.0; scale-specific α values are reported above. At temperature 0.1, Llama α was 0.951 (5-point numeric), 0.997 (10-point), 0.854 (Likert), 0.957 (binary). More detailed criterion definitions showed an upward consistency slope; source gives no numeric effect size and no 0–3 arm.
- **E4 — [G-Eval](https://arxiv.org/html/2303.16634):** on 1–5, “one digit…such as 3” dominates; **source gives no midpoint-clustering rate**. Probability weighting was proposed, but direct scores had better average Kendall τ than probability-normalized scores (0.418 vs 0.446 appears metric-dependent across columns); CoT improved average Spearman from 0.500 to 0.514 and Kendall τ from 0.407 to 0.418.
- **E5 — [Stureborg et al.](https://arxiv.org/html/2405.01724):** GPT-4 inter-sample α=0.587 versus human α=0.659; 1–5-vs-1–10 cross-scale α=0.597. Samples used N=10, temperature 1.0. The 1–100 outputs clustered largely in 70–100 with peaks at 60/70/80/90/75/85/95; **source gives no peak percentages**. Single-vs-multi-attribute α=0.513, supporting masks indirectly.
- **E6 — [Wang et al., FairEval](https://arxiv.org/html/2305.17926):** order swaps caused conflict rates 46.3% (GPT-4) and 82.5% (ChatGPT) on Vicuna-vs-ChatGPT. At temperature 0, evidence-before-score raised GPT-4 accuracy 52.7%→56.5% and κ 0.24→0.29; ChatGPT 44.4%→52.6% and κ 0.06→0.23.
- **E7 — [Zheng et al., MT-Bench](https://arxiv.org/html/2306.05685):** swap consistency was 65.0% GPT-4, 46.2% GPT-3.5, 23.8% Claude-v1; repetitive-list failure was 8.7%, 91.3%, 91.3% on 23 answers. Reported self-favoring win-rate deltas were +10 points GPT-4 and +25 Claude, but authors deemed self-enhancement inconclusive.
- **E8 — [Saito et al.](https://arxiv.org/html/2310.10076):** accuracy-parity verbosity-bias magnitude was 0.328 GPT-4 and 0.428 GPT-3.5.
- **E9 — [Prometheus](https://arxiv.org/html/2310.08491):** each 1–5 point had a description; feedback preceded score. On 45 custom rubrics, human Pearson correlation was 0.897 versus GPT-4’s 0.882; removing the score rubric reduced Pearson 0.847→0.745 on unseen rubrics. No scale-width or ordering ablation.
- **E10 — [Likert or Not](https://arxiv.org/html/2505.19334):** GPT-4o mean NDCG@10 over ten retrieval datasets rose 0.547→0.597→0.630→0.634→0.638 for 2/3/5/7/11 points. This is relevance ranking, not prose defects.
- **E11 — [Chiang & Lee](https://aclanthology.org/2023.findings-emnlp.599/):** forcing numeric-only ratings was suboptimal and explanations consistently improved human correlation; **source abstract gives no magnitude**. It also says auto-CoT did not always help.
- **E12 — [EvalGen](https://arxiv.org/html/2404.12272):** criteria drift affected both adding and reinterpreting criteria; five of nine participants are named in each pattern. This supports versioned calibration, not a particular scale.
- **E13 — Repository:** `packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml:62-64,186-188` makes judgment rules suggestions; `packages/slopvac-lint/src/slopvac/rules/ste-safety.yml:12-15` is the judgment error exception.

## Amendments

**C2 replacement (paste-ready):**

> Each dimension uses four **named ordered categories**. Codes 0–3 exist only for schema serialization; they are ordinal, not equal intervals, and MUST NOT be averaged or summed. FIT = `absent(0) | partial(1) | ambiguous_match(2) | unambiguous_match(3)`. WARRANT = `none(0) | quote_only(1) | quote_plus_particular(2) | two_locators(3)`. HARM = `none(0) | reader_effort(1) | misleads_or_blocks(2) | unsafe_or_normative(3)`. REPAIR = `authorial_only(0) | needs_external_fact(1) | local_substitution(2) | safe_deletion(3)`. The existing observable descriptions define each member; adjectives such as “poor/good/excellent” are prohibited.

**C10 replacement (paste-ready):**

> Reject when FIT is `absent|partial` or WARRANT is `none|quote_only`. Reject HARM=`none` unless REPAIR=`safe_deletion`. Emit `error` only for HARM=`unsafe_or_normative` with FIT=`unambiguous_match` and admitted WARRANT. Emit `warning` only for HARM=`misleads_or_blocks` with FIT=`unambiguous_match` and admitted WARRANT. Otherwise emit `suggestion`, then apply rule/category ceilings and rewrite checks. This preserves admission boundaries but demotes ambiguous FIT=2 cases from warning to suggestion: precision should rise; recall for genuinely harmful ambiguous readings may fall.

**C14 row replacement (paste-ready):**

> One global scalar quality score, at any width: reject because it collapses defect admission, reader consequence, evidential warrant, and repairability, so it cannot identify a span or action. This is a composition objection; it is not evidence that 1–10 scales are generally inferior.

## Unsupported

- **UNSUPPORTED:** 0–3 is superior to binary+severity or anchored 1–5 for this repository; no direct comparison found.
- **UNSUPPORTED:** exact midpoint-clustering percentage for 1–5; cited work gives no number.
- **UNSUPPORTED:** repeated-call agreement at **temperature 0** by scale width. CheckEval used temperature 0 but n=1; repeat studies used temperature 0.1 or 1.0.
- **UNSUPPORTED:** asking a known-constant dimension adds a measured amount of noise. Multi-attribute anchoring and α=0.513 support the direction indirectly, but no constant-mask ablation was found.
- **UNSUPPORTED:** C10’s exact cut-points. They are defensible policy choices, not literature-derived thresholds.

## Open evaluation questions

1. On an adjudicated, rule-stratified repository sample, compare: named four-level categories; binary FIT/WARRANT checklist + severity; anchored 1–5; and unanchored 1–10 as a negative control. Report per-rule precision/recall, severe false-positive rate, confusion matrices, category occupancy/entropy, and ordinal α.
2. Run five repeated calls at temperature 0 and 1 on the same frozen model/version; report exact agreement and α by dimension and scale—not only aggregate correlation.
3. Ablate masks: ask versus inject each known constant; randomize dimension order. Measure false variance, score anchoring, verdict flips, token cost, and invalid evidence.
4. Cross evidence-first versus verdict-first at temperature 0. Measure admitted-finding precision and unsupported-rating rate; do not infer prose benefit solely from pairwise chatbot results.
5. Tune FIT=2 and HARM=2 severity boundaries on a development split, then freeze and report held-out error/warning precision with confidence intervals.