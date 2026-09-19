# Wider judgement evaluation record — 2026-09-19

**Bead:** `slopvac-cz0.13`  
**Scope:** wider held-out evaluation and three-repeat noise floor  
**Record status:** complete for the measured host outcomes; blinded precision remains pending.

This record preserves the provenance and denominator rules required by the evaluation-record hygiene contract. Every numeric claim names its source artefact and field below. Failed rows are not converted to abstentions and are excluded from verdict numerators and attempted-judgement denominators.

## Corpus and preregistration

The frozen manifest is `wider/manifest.json`; its `class`, `genre`, `converted_word_count`, source, revision, and conversion fields are authoritative. The preregistration is `wider/preregistration.md`, sections **Corpus**, **Arms and repeats**, **Blinded adjudication**, and **Success criteria**. It defines a stratified corpus, **333,870** human-authored converted words and **133,900** stated-LLM converted words (`preregistration.md`, Corpus; the manifest is authoritative), a three-repeat 20% subsample (`preregistration.md`, Arms and repeats), four blinded labels (`preregistration.md`, Blinded adjudication), and the human threshold of **0.05 confirms per 1,000 words** plus the LLM lenient-precision target of **0.5** (`preregistration.md`, Success criteria).

Two deviations are explicit. The noise-floor subsample was registered at runtime because no prior registration existed (`packages/slopvac-lint/docs/judgement-eval.md`, Noise-floor instrument; `noise-floor/subsample.json`). The LLM arm includes **148** second samples, accepted by the user; the retry set and its successful rows are recorded in `wider/analysis/q02-salvage/merge-log.json` (`join_key=call_id`, `bedrock-retry/responses.jsonl` successful retry rows). The human arm also includes **144** second-sample retry IDs, accepted by the user; **143** produced valid rows and one remained a provider JSON parse failure (`wider/run/human/failure-disposition.json`, `disposition`, `retried`).

## Runner and model provenance

The first **1,546** calls used the session model `global.anthropic.claude-fable-5-1`; this is verified in the session transcript and documented in `packages/slopvac-lint/docs/judgement-eval.md`, Standalone Bedrock evaluation runner. The explicit Bedrock runner was `packages/slopvac-lint/scripts/judgement_bedrock_batch.py invoke` with `AWS_PROFILE=sjors+ig-genai-Admin`, `AWS_DEFAULT_REGION=eu-west-1`, model `global.anthropic.claude-fable-5-1`, `--max-tokens 32000`, and concurrency **8** (`packages/slopvac-lint/docs/judgement-eval.md`, Running in AWS and Standalone Bedrock evaluation runner). Batch inference was attempted but is unsupported for this model/profile in `eu-west-1`; the documented response is `Batch inference is not supported for the requested model` (same source, Running in AWS). Successful responses require `end_turn`; truncated responses remain error rows (same source, Standalone Bedrock evaluation runner).

## LLM-class arm

The final LLM report is `wider/run/llm/report.json`; its top-level `counts` fields are the source for aggregate accounting. It covers **2,265 calls**, with **148** call IDs retried (the second sample, accepted and flagged rather than excluded), **5** residual schema failures, and **306 confirmed**, **42,039 rejected**, **4,836 abstained**, and **100 failed units** (`report.json`, `counts` and coverage totals; retry count from `analysis/q02-salvage/merge-log.json`). The eight documents comprise **3 CLEAN** and **5 PARTIAL** statuses (`run/llm/report.json`, `documents[].coverage.status`). The **306** confirm total is also reconciled by `analysis/per-rule.md` (`50` confirms, **16.34%**, map to retried calls; retried rows are retained).

The top-ten per-rule table below is copied from `wider/analysis/per-rule.md`, **Top 10 FP-suspect ranking**. These are stated-LLM confirm counts, not adjudicated precision and not human false-positive estimates; the human-class column is unavailable in this arm.

| Rank | Rule | Model CONFIRM count | Human-class CONFIRM count |
|---:|---|---:|---:|
| 1 | `ai-tells-register.corporate-analytic-filler-remainder` | 148 | unavailable |
| 2 | `ai-tells-structure.cataphoric-lead-in-remainder` | 58 | unavailable |
| 3 | `ai-tells-structure.absolute-assertion-remainder` | 19 | unavailable |
| 4 | `ai-tells-register.faux-candor-remainder` | 13 | unavailable |
| 5 | `ai-tells-structure.false-range` | 13 | unavailable |
| 6 | `ai-tells-register.anthropomorphised-justification-remainder` | 10 | unavailable |
| 7 | `ai-tells-register.false-agency-remainder` | 9 | unavailable |
| 8 | `ai-tells-structure.anaphora-abuse` | 8 | unavailable |
| 9 | `ai-tells-structure.heading-echo` | 8 | unavailable |
| 10 | `ai-tells-structure.false-suspense-remainder` | 5 | unavailable |

## Human-class arm and candidate FP suspects

The human report is `wider/run/human/report.json`; the per-rule extraction is `wider/analysis/per-rule-human.md`. It covers **36 documents**, has **45 confirms**, and is **PARTIAL** overall (`per-rule-human.md`, refreshed Human per-document coverage; **29 CLEAN** and **7 PARTIAL** statuses from `run/human/report.json`, `documents[].coverage.status`). The retry completed after **144** queued IDs: **143** produced valid rows and one remained a provider JSON parse failure (`run/human/failure-disposition.json`, `disposition`, `retried`; refreshed `report.json`, `counts.failed_calls: 5`). The refreshed report has **4,433 abstentions** (`run/human/report.json`, coverage totals). Retried-call confirmations are **13 / 2,054 = 0.63%** (`run/human/report.json`, retry-marked rows and coverage totals).

The following are **candidate FP suspects**, ranked by human model CONFIRM counts. They are not adjudicated FPs; they are not silently relabelled, and the denominator remains the attempted count shown in the refreshed `wider/analysis/per-rule-human.md`.

| Rank | Rule | Model CONFIRM count | Attempted | Human confirm rate |
|---:|---|---:|---:|---:|
| 1 | `ai-tells-structure.absolute-assertion-remainder` | 13 | 3447 | 0.38% |
| 2 | `ai-tells-register.corporate-analytic-filler-remainder` | 6 | 3447 | 0.17% |
| 3 | `ai-tells-structure.cataphoric-lead-in-remainder` | 7 | 3447 | 0.20% |
| 4 | `ai-tells-register.false-agency-remainder` | 4 | 3447 | 0.12% |
| 5 | `ai-tells-structure.false-suspense-remainder` | 3 | 3447 | 0.09% |
| 6 | `ai-tells-register.anthropomorphised-justification-remainder` | 3 | 3447 | 0.09% |
| 7 | `ai-tells-register.faux-candor-remainder` | 2 | 3447 | 0.06% |
| 8 | `ai-tells-structure.analogy-stack-authority` | 1 | 3447 | 0.03% |
| 9 | `ai-tells-structure.anaphora-abuse` | 1 | 3447 | 0.03% |
| 10 | `ai-tells-structure.false-range` | 1 | 3447 | 0.03% |

The preregistered human criterion is **not met**: **45** confirms / **333,870** manifest words = **0.1348 per 1,000 words**, above **0.05** (`wider/run/human/report.json`, refreshed `documents[].confirmed`; denominator from `wider/manifest.json`, `converted_word_count`). The LLM lenient-precision criterion is **PENDING / NOT MEASURABLE** because the two independent blinded label sets and third-adjudicator resolution are not complete (`wider/verdict.md`, Criterion 2).


## Q02 salvage comparison

The opt-in decision remains **OPEN** for `slopvac-cz0.19`. `wider/analysis/q02-comparison.md` reports **1,294 → 4** evidence-offset mismatches, **307 → 482** confirms (**+175**), **42,041 → 42,080** rejected, **4,861 → 4,535** abstained, and **456 → 456** failed. Salvage changes evidence offsets and does not establish semantic precision (`q02-comparison.md`, Reading against Q02). No default adoption is recorded here.

## Noise floor

The measured noise floor is `noise-floor/noise-floor.json` and its rendered summary `noise-floor/noise-floor.md`: **3** repeats, **1,416** complete units, **308** incomplete units, and overall flip rate **1.27%** (`noise-floor.json`, `repeat_count`, `complete_units`, `incomplete_units`, `overall_flip_rate`). The standing decision rule is strictly **> 10%** flip rate ⇒ `majority-of-3`; exactly **10%** remains `single-call` (`noise-floor.json`, `threshold`; `noise-floor.md`).

Rules selected for `majority-of-3` are: `ai-tells-content-shape.elegant-variation` (**16.67%**, 2 units), `fabricated-citations-remainder` (**22.22%**, 3), `one-point-dilution` (**11.11%**, 3), `ai-tells-structure.invented-concept-label` (**22.22%**, 3), `listicle-in-a-trench-coat` (**22.22%**, 3), `tricolon-abuse-remainder` (**11.11%**, 3), `prose-discipline.competing-actor-terms` (**16.67%**, 2), and `hedged-into-uselessness` (**33.33%**, 2) (`noise-floor.json`, `rules[]`). All other rules in `noise-floor.json` remain `single-call` under the same rule.

The low-n caveat is an **OPEN proposal**, not a decision: several majority-of-3 decisions are based on only **2–3 complete units** (`noise-floor.json`, `rules[].unit_count`), so cz0.12 must decide whether to add a low-n guard while preserving the measured >10% policy.

## Limitations

- Host CONFIRM/REJECT/ABSTAIN outcomes are not blinded TP/borderline/FP/preservation-miss labels; no semantic precision is claimed (`wider/verdict.md`, Criterion 2).
- The human arm remains partial with **5** residual failed calls after retry (**143** of **144** retry IDs produced valid rows; one provider JSON parse failure), and failed rows remain excluded (`wider/run/human/failure-disposition.json`, `disposition`, `total`, `retried`; `wider/run/human/report.json`, `counts.failed_calls`).
- The runtime registration of the noise-floor subsample is a preregistration deviation (`noise-floor/subsample.json`; `noise-floor/noise-floor.md`).
- The first **1,546** calls used the session model and may not be sampling-homogeneous with the explicit runner arm (`packages/slopvac-lint/docs/judgement-eval.md`, Standalone Bedrock evaluation runner).

## Next steps

- Open precision beads for absolute-assertion, heading-echo, and false-agency candidate-suspect review; retain raw counts and adjudicate rather than treating model CONFIRM as FP.
- Run `cz0.30` for the next wider-evaluation increment.
- Resolve the low-n guard proposal in `cz0.12`.
- Decide whether to opt in to Q02 salvage in `cz0.19`.

## Source inventory

- `wider/preregistration.md`
- `wider/manifest.json`
- `wider/run/llm/report.json`
- `wider/run/human/report.json`
- `wider/run/human/failure-disposition.json`
- `wider/analysis/per-rule.md`
- `wider/analysis/per-rule-human.md`
- `wider/analysis/q02-comparison.md`
- `wider/analysis/q02-salvage/merge-log.json`
- `noise-floor/noise-floor.json`
- `noise-floor/noise-floor.md`
- `noise-floor/subsample.json`
- `packages/slopvac-lint/docs/judgement-eval.md`
- `packages/slopvac-lint/docs/research/rubric-2026-09-15/process.md`
