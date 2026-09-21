# Wider judgement evaluation record -- 2026-09-19

**Bead:** `slopvac-cz0.13`  
**Scope:** wider held-out evaluation and three-repeat noise floor  
**Record status:** complete for the measured host outcomes; blinded precision remains pending.

This record preserves the provenance and denominator rules required by the evaluation-record hygiene contract. Every numeric claim names its source artefact and field below. Schema-valid abstentions remain attempted judgments. Failed rows remain in failed counts, while verdict numerators and attempted-judgement denominators use completed rows.

## Corpus and preregistration

The frozen manifest is `wider/manifest.json`. Its `class`, `genre`, `converted_word_count`, source, revision, and conversion fields are authoritative. The preregistration is `wider/preregistration.md`, sections **Corpus**, **Arms and repeats**, **Blinded adjudication**, and **Success criteria**. It defines a stratified corpus with **333,870** human-authored converted words and **133,900** stated-LLM converted words (`preregistration.md`, Corpus; the manifest is authoritative). It also defines a three-repeat 20% subsample (`preregistration.md`, Arms and repeats), four blinded labels (`preregistration.md`, Blinded adjudication), a human threshold of **0.05 confirms per 1,000 words**, and an LLM lenient-precision target of **0.5** (`preregistration.md`, Success criteria).

Two deviations are explicit. The noise-floor subsample was registered at runtime because no prior registration existed (`packages/slopvac-lint/docs/judgement-eval.md`, Noise-floor instrument; `noise-floor/subsample.json`). The LLM arm includes **148** second samples, accepted by the user; the retry set and its successful rows are recorded in `wider/analysis/q02-salvage/merge-log.json` (`join_key=call_id`, `bedrock-retry/responses.jsonl` successful retry rows). The human arm also includes **144** second-sample retry IDs, accepted by the user; **143** produced valid rows and one remained a provider JSON parse failure (`wider/run/human/failure-disposition.json`, `disposition`, `retried`).

## Runner and model provenance

The first **1,546** calls used the session model `global.anthropic.claude-fable-5-1`; this is verified in the session transcript and documented in `packages/slopvac-lint/docs/judgement-eval.md`, Standalone Bedrock evaluation runner. The explicit Bedrock runner was `packages/slopvac-lint/scripts/judgement_bedrock_batch.py invoke` with `AWS_PROFILE=sjors+ig-genai-Admin`, `AWS_DEFAULT_REGION=eu-west-1`, model `global.anthropic.claude-fable-5-1`, `--max-tokens 32000`, and concurrency **8** (`packages/slopvac-lint/docs/judgement-eval.md`, Running in AWS and Standalone Bedrock evaluation runner). Batch inference was attempted but is unsupported for this model/profile in `eu-west-1`; the documented response is `Batch inference is not supported for the requested model` (same source, Running in AWS). Successful responses require `end_turn`; truncated responses remain error rows (same source, Standalone Bedrock evaluation runner).

## LLM-class arm

The final LLM report is `wider/run/llm/report.json`; its top-level `counts` fields are the source for aggregate accounting. It covers **2,265 calls**, with **148** call IDs retried (the second sample, accepted and flagged rather than excluded), **5** residual schema failures, and **306 confirmed**, **42,039 rejected**, **4,836 abstained**, and **100 failed units** (`report.json`, `counts` and coverage totals; retry count from `analysis/q02-salvage/merge-log.json`). The eight documents comprise **3 CLEAN** and **5 PARTIAL** statuses (`run/llm/report.json`, `documents[].coverage.status`). The **306** confirm total is also reconciled by `analysis/per-rule.md` (`50` confirms, **16.34%**, map to retried calls; retried rows are retained).

The top-ten per-rule table below is copied from `wider/analysis/per-rule.md`, **Top 10 FP-suspect ranking**. It reports stated-LLM confirm counts. The human-class column is unavailable in this arm, and adjudicated precision requires the blinded labels described in the preregistration.

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

The following are **screening candidates**, ranked by human model CONFIRM counts. A human CONFIRM is not an adjudicated false positive: style rules legitimately fire on human prose. Adjudicated precision is the headline measure; human confirm rate is a screening signal only. The denominator remains the attempted count shown in the refreshed `wider/analysis/per-rule-human.md`.

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

The preregistered human confirm-rate criterion is a screening signal, not a precision estimate, because style rules legitimately fire on human prose. The blinded adjudication is the headline measure: report precision both as true positives divided by adjudicated confirms and as false-positive incidence divided by attempted human units. The LLM lenient-precision criterion is **PENDING / NOT MEASURABLE** because the two independent blinded label sets and third-adjudicator resolution are not complete (`wider/verdict.md`, Criterion 2).

## Precision fixes

### Absolute assertion (slopvac-cz0.31, round 2)

The earlier 64 calls used instrument v1 with no criteria examples (two wording iterations over the same 32 narrowed single-unit prompts), so those results are retained only as historical context. The authoritative shipped-pack rerun used the real `load_ruleset` → `build_packs` → `render_pack` → `_prompt_for` path, with `global.anthropic.claude-fable-5-1`, `--max-tokens 32000`, and concurrency 8. Its 32 calls yielded **0/9** human false-positive confirms, **2/3** adjudicated true positives, an abstained borderline, and **9/19** stated-LLM confirms. The rendered system prompt contains the absolute-assertion question and exemplars (generated prompt JSONL line 1; assembly source `src/slopvac/judgement/packs.py:207-224`); this is the authoritative shipped-guidance measurement.

| Unit | Adjudication | Instrument v1, no criteria | Shipped render-path rerun |
|---|---|---|---|
| `f6870b3751011de3` | FP | reject | preserve |
| `dcf382514ba6efd3` | FP | reject | preserve |
| `d02c5a73f3f38bd9` | FP | reject | preserve |
| `e623ab4247e17d60` | FP | reject | preserve |
| `310910e019f5bbc4` | FP | preserve | preserve |
| `c771cf8a40ed85d9` | FP | reject | preserve |
| `f40430eee411e97e` | FP | reject | preserve |
| `561ba05f799ac84a` | FP | reject | preserve |
| `de9b34687303a48a` | FP | reject | reject |
| `0ce0297e9f8459bf` | TP | reject | reject |
| `59bbe735c9ae7b74` | TP | preserve | confirm |
| `2e1e45f820afefc2` | TP | preserve | confirm |
| `9ab9c0ccc3029082` | borderline | reject | abstain |
| `b9acf3d1fba5b2df` | LLM non-confirm | reject | abstain |
| `bc12bbd9bb8c8c87` | LLM non-confirm | reject | reject |
| `e1b1763a090d36ef` | LLM non-confirm | reject | reject |
| `1931a0ee21697a38` | LLM non-confirm | reject | confirm |
| `93563be607c9eea8` | LLM confirm | preserve | preserve |
| `e7f4817cdd35383b` | LLM confirm | preserve | confirm |
| `ef907bb2f8bc7008` | LLM confirm | confirm | confirm |
| `733ae625941f52f4` | LLM non-confirm | reject | reject |
| `3a63334b6c6e6aec` | LLM non-confirm | reject | reject |
| `be11628c9d962b63` | LLM non-confirm | reject | reject |
| `19b89f2a10d2da51` | LLM confirm | confirm | confirm |
| `e5059caf3fec2ed9` | LLM confirm | confirm | confirm |
| `81b47e9897d955d6` | LLM confirm | confirm | confirm |
| `ac5044bb8e73dd69` | LLM confirm | confirm | confirm |
| `a66a1c8e315014b2` | LLM non-confirm | reject | reject |
| `581dd4cb0671cf33` | LLM confirm | confirm | confirm |
| `95a084b645069251` | LLM non-confirm | reject | reject |
| `53637a81d06d2df9` | LLM confirm | confirm | confirm |
| `337ad7777c698819` | LLM non-confirm | reject | reject |

The exact prompt rows and raw responses are retained under `/Users/sjors/tmp/slopvac-judgement-eval/wider/analysis/` during the run; the regression fixture adds the three TP quotes beside the bounded FP controls.

## Q02 salvage comparison

The Q02 decision is **DECIDED (2026-09-19)** for `slopvac-cz0.19`: `unique-quote` offset salvage is the default, while `--offset-salvage none` preserves raw offsets. The comparison reports **1,294 → 4** evidence-offset mismatches, **307 → 482** confirms (**+175**), **42,041 → 42,080** rejected, **4,861 → 4,535** abstained, and **456 → 456** failed. Salvage changes evidence offsets and does not establish semantic precision (`q02-comparison.md`, Reading against Q02).

## Noise floor

The r2 measurement is `noise-floor/r2/noise-floor.json` with rendered summary
`noise-floor/r2/noise-floor.md`: **3** repeats, **1,416** complete units, **308**
incomplete units, and overall flip rate **1.27%**. Failure classes are reported
separately: **60 provider_error** and **1,744 schema_invalid**. The report has no
`missing_response`, `parse_error`, or `unknown_unit` failures. Only complete units
contribute to flip denominators. The legacy rows were backfilled with
`run-config.json`, sourced from `run-noise-floor supervisor script and hub process
slopvac-noise-floor`, and that provenance is retained in `noise-floor.json`.

The instrument is measurement-only: it reports per-rule flip rates, complete-unit
counts, and failure classes. The separate `r2/variance-policy.json` and
`variance-policy.md` run `decide --threshold 0.10 --min-units 30`; its explicit
`applies_to` is **CONFIRM**. All low-n rules remain `single-call` with
`decision_basis: insufficient-units`, matching the guarded run; no `finish` path
applies majority today.

## 2026-09-21 v2 (instrument 6e84cf35: rule criteria rendered)

The v2 instrument rendered each rule's criteria and evidence roles in the system prompt. The official tolerant results are `v2/llm/final/report.json` and `v2/human/final/report.json`; the strict reports remain `v2/llm/report.json` and `v2/human/report.json`. Tolerance strips model annotations while preserving the verdict; the final reports record `counts.annotation_stripped_calls`.

### Population and accounting

Both manifests contain 47,856 units (`v2/README.md`, population reconciliation). v1 admitted 44,700 and v2 admitted 43,848; the shared comparison therefore uses 43,848 units. The remaining 852 units are host-preserved in v2 with `admission_reason=normative_obligation` and are reported separately (`v2/README.md`, population reconciliation). This gate comes from PR #94 and is not a consequence of criteria rendering.

### Arm results

| Arm | Strict report | Final tolerant report | Final annotation-stripped calls |
|---|---|---|---:|
| LLM | `v2/llm/report.json`, `counts` | `v2/llm/final/report.json`, `counts` | 65 |
| Human | `v2/human/report.json`, `counts` | `v2/human/final/report.json`, `counts` | 18 |

The strict and final reports use the same response rows; only the final report is the official tolerant result. Per-rule counts are in `v2/analysis/v2-final-per-rule-x-class.md`.

### v1 to v2

`v2/analysis/v1-v2-shared-43848.md` reports CONFIRM, REJECT, ABSTAIN, and FAILED outcomes overall and per rule, restricted to the 43,848 shared eligible units. It excludes the 852 host-preserved units, which are listed separately above.

### Noise floor

The strict noise-floor rate is **0.79%** (`v2/noise-floor/noise-floor.json`, `overall_flip_rate`); the tolerant final rate is recorded in `v2/noise-floor/final/noise-floor.json`, `overall_flip_rate`. All rules remain `single-call` with insufficient units for a majority decision (`v2/noise-floor/final/variance-policy.json`, `decision_basis`). Annotation stripping is recorded as `annotation_stripped_calls` in the final noise-floor artifact. Incompleteness is due to provider/schema/unknown-unit failures, not missing model calls (`failure_classes`).

### Adjudication

The blinded adjudication contains 60 human confirms: 37 true positives, 21 false positives, and 2 borderline (`v2/adjudication/SUMMARY.md`, summary totals). Adjudicated precision is 65% of adjudicated confirms, and false-positive incidence is 0.06% of attempted human units (`v2/adjudication/summary.csv`, `v2/adjudication/SUMMARY.md`). The five FP rules are absolute assertion, corporate analytic filler, false agency, cataphoric lead-in, and false suspense. Their bounded-guidance, genre-convention, and code-or-list patterns are detailed in the per-rule adjudication files. The five clean rules are elegant variation, one-point dilution, competing actor terms, anthropomorphised justification, and bare quantifier with figure available (`v2/adjudication/*.md`).

### Deviations, limitations, and next steps

The v1 figures are marked **instrument v1 (no criteria)**. The second-sample retry rows remain included and flagged rather than excluded (`v2/README.md`, preparation and retry notes). The external preregistration was not edited; the metric interpretation deviation is recorded here. Human confirms are a screening signal because style rules legitimately fire on human prose, not a false-positive label. Use adjudicated precision with both denominators as the headline metric, complete the per-rule adjudication intervals, and repeat the shared-population comparison after the next instrument change.

## Limitations

- Host CONFIRM/REJECT/ABSTAIN outcomes are not blinded TP/borderline/FP/preservation-miss labels; no semantic precision is claimed (`wider/verdict.md`, Criterion 2).
- The human arm remains partial with **5** residual failed calls after retry (**143** of **144** retry IDs produced valid rows; one provider JSON parse failure), and failed rows remain excluded (`wider/run/human/failure-disposition.json`, `disposition`, `total`, `retried`; `wider/run/human/report.json`, `counts.failed_calls`).
- The runtime registration of the noise-floor subsample is a preregistration deviation (`noise-floor/subsample.json`; `noise-floor/noise-floor.md`).
- The first **1,546** calls used the session model and may not be sampling-homogeneous with the explicit runner arm (`packages/slopvac-lint/docs/judgement-eval.md`, Standalone Bedrock evaluation runner).

## Precision fixes

Adjudication is recorded in `wider/analysis/absolute-assertion-adjudication.md`: **13** human-class confirms are classified as **9 FP, 3 TP, and 1 borderline**. The dominant FP pattern is bounded or attributed historical/editorial prose and local anaphoric quantifiers. The chosen lever is judgement guidance: preserve quoted/attributed claims, finite historical/editorial sets, local anaphora, and explicitly bounded recommendations; flag only unsupported universals in the author's unbounded voice.

The authoritative pre-fix host counts are **13 human** and **19 stated-LLM** confirms (`wider/run/{human,llm}/findings.jsonl`, `rule_id=ai-tells-structure.absolute-assertion-remainder`, `outcome=CONFIRM`). The deterministic lint reruns are `wider/analysis/absolute-assertion-human-after.json` and `absolute-assertion-llm-after.json`; because this rule is a judgement remainder, the deterministic layer emits **0** direct findings in both classes. Guidance-only changes therefore require re-judgement for semantic before/after precision.

Targeted reissue used 13 human and 19 LLM confirmed units (32 one-unit Bedrock calls; the existing prompt rows were narrowed to each unit and the new guidance text was substituted because `judgement prepare` cannot select arbitrary unit IDs). Human outcomes changed from **13 confirm → 0 confirm** (**9 reject, 4 preserve**); LLM outcomes changed from **19 confirm → 7 confirm** (**10 reject, 2 preserve**). The 12 human flips are the bounded/attributed precision wins; the 12 LLM flips are primarily product-specific or bounded claims, while 7 unsupported claims held. Precision rose at a measured recall cost: all **3 adjudicated TPs** and **12 of 19 LLM confirms** were lost under the new guidance.

## Next steps

- Open precision beads for absolute-assertion, heading-echo, and false-agency candidate-suspect review; retain raw counts and adjudicate rather than treating model CONFIRM as FP.
- Run `cz0.30` for the next wider-evaluation increment.
- Resolve the low-n guard proposal in `cz0.12`.

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
