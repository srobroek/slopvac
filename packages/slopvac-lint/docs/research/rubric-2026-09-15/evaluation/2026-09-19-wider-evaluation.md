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
### v2 adjudication rerun: bounded-guidance fixes (2026-09-21)

The three bounded-guidance changes were rerun through the shipped path (`load_ruleset` → `build_packs` → `render_pack` → `driver._prompt_for`) rather than a hand-written prompt. The Bedrock command was `judgement_bedrock_batch.py invoke` with `AWS_PROFILE=sjors+ig-genai-Admin`, `AWS_DEFAULT_REGION=eu-west-1`, model `global.anthropic.claude-fable-5-1`, `--max-tokens 32000`, and concurrency **8**. The corrected run completed **33 calls**: absolute assertion **18**, one-point dilution **8**, and corporate analytic filler **7**. “Before” below is the blinded adjudicator class from `v2/adjudication`; “after” is the v2 model verdict. `confirm` means the model still judged the unit in scope; `reject` means it did not; `abstain` means it withheld a verdict.

| Rule | Calls | Before FP units | After FP verdicts | Before TP units | After TP verdicts | Decision |
|---|---:|---:|---|---:|---|---|
| `ai-tells-structure.absolute-assertion-remainder` | 18 | 5 | 0 confirm (5 abstain) | 8 | 3 confirm, 4 abstain, 1 reject | **measured, not shipped**: recall guard fails (3/8 TP confirm) |
| `ai-tells-content-shape.one-point-dilution` | 8 | 4 | 0 confirm (4 reject) | 1 | 1 confirm | **ship**: recall guard passes |
| `ai-tells-register.corporate-analytic-filler-remainder` | 7 | 5 FP plus 1 separate borderline control | 3 confirm, 1 abstain (FP-only: 2 confirm, 1 abstain) | 1 | 1 confirm | **measured, not shipped**: inconclusive residual confirms |

The complete per-unit before/after record is:

#### `ai-tells-structure.absolute-assertion-remainder`

| Unit | Before | After | Disposition |
|---|---|---|---|
| `human:defd126579a0` | TP | abstain | recall loss |
| `human:5180bc49a5fb` | TP | reject | recall loss |
| `human:af462e22e3da` | TP | confirm | retained |
| `human:a0d7cec12db3` | TP | abstain | recall loss |
| `human:e2fe89d8caa7` | FP | abstain | fixed |
| `human:54d641fb9a31` | FP | abstain | fixed |
| `human:be9f6ab16457` | FP | abstain | fixed |
| `human:83f352843d9c` | TP | abstain | recall loss |
| `human:5ef39537909f` | TP | confirm | retained |
| `human:25c3a8b245d6` | FP | abstain | fixed |
| `human:5600907c8479` | TP | abstain | recall loss |
| `human:e22e0b56c835` | TP | confirm | retained |
| `human:6098cb174ffe` | FP | abstain | fixed |
| `llm:060abd9f3311` | TP | abstain | recall loss |
| `llm:0c49781d15d7` | TP | abstain | recall loss |
| `llm:1020e8f35190` | FP | confirm | residual confirm |
| `llm:103d78ed6b90` | FP | reject | fixed |
| `llm:13adfc00a76e` | TP | confirm | retained |

#### `ai-tells-content-shape.one-point-dilution`

| Unit | Before | After | Disposition |
|---|---|---|---|
| `human:bdd483d1b54a` | FP | reject | fixed |
| `human:cb9fa3d9302e` | TP | confirm | retained |
| `human:5c4814642f89` | FP | reject | fixed |
| `human:fb59af1558a4` | FP | reject | fixed |
| `human:1a8eaf8921b6` | FP | reject | fixed |
| `llm:104fb25f0583` | FP | reject | fixed |
| `llm:ad6f1a6d30c4` | FP | reject | fixed |
| `llm:b56d86dac207` | TP | reject | recall loss |

#### `ai-tells-register.corporate-analytic-filler-remainder`

| Unit | Before | After | Disposition |
|---|---|---|---|
| `human:e601bb6704c4` | FP | abstain | fixed |
| `human:2df5c1866dc4` | FP | confirm | residual confirm |
| `llm:00abad7087e9` | FP | confirm | residual confirm |
| `llm:01670a2a8c76` | borderline | confirm | borderline |
| `llm:0567e91201bd` | FP | confirm | residual confirm |
| `llm:090ed9d9bfad` | TP | confirm | retained |
| `llm:0ac253411cd6` | FP | abstain | fixed |

The recall guard ships only one-point-dilution: every FP control was rejected and its TP was confirmed. Absolute-assertion is measured but not shipped because only 3/8 adjudicated TPs remained confirmed. Corporate-analytic-filler is measured but not shipped because one of two human FPs remained confirmed and the LLM controls were inconclusive. The elegant-variation and competing-actor-terms changes are **deferred** pending adjudicator consistency; no ship claim is made for them.


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
