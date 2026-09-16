Claim: C9 treats 8 criteria × 12 units as a defensible SPAN ceiling and one 18-criterion whole-document PROBE as worth its reported cost advantage because an ~8.7k-token prefix will be cheap when cached.

VERDICT: CHALLENGED

## Verdicts

| Claim ID | Verdict | One-line reason | Evidence |
|---|---|---|---|
| C9 | **REPLACE** | Eight criteria, 12 units, and especially 18 full-document criteria are unvalidated production defaults: the closest direct judge study already overstates all-criteria success by **24.1 points at 5 criteria** and **44.4 points at 10**, while validated checklist judges decompose questions; caching helps only after an **identical** prefix recurs, which 3–6 different packs in one document do not establish. | E1, E3–E6, E10–E14 |

## Evidence

**E1.** https://arxiv.org/html/2509.21051v1 — ManyIFEval supplies programmatic ground truth for 1–10 simultaneous instructions. GPT-4o-as-judge reported prompt-level success **0.815 vs 0.574 ground truth at 5** (+24.1 points) and **0.657 vs 0.213 at 10** (+44.4 points). This is the most directly analogous count-based judge result found, but it reports prompt-level inflation, **not per-criterion recall**.

**E2.** https://arxiv.org/html/2310.20410v3 — FollowBench increases constraints across levels 1–5. GPT-4 Preview HSR falls **84.7%→61.9%** (−22.8 points) and SSR **84.7%→72.3%** (−12.4 points); the authors estimate GPT-4/GPT-3.5 handle about **3 constraints**. This measures generation-side following, not judging, so it warns about dilution but cannot set the judge cap by itself.

**E3.** https://arxiv.org/html/2309.00384v3 — BatchPrompt tests unit batching. Naïve batching at **batch size 6** significantly degraded all eight tested classification tasks versus individual prompting; recency bias was significant overall and worsened with larger batches. Permutation/calibration largely repaired it, and GPT-4 showed only about **1–2 points** loss at batch size **16** on two tasks. Thus “12 units” is model- and mitigation-dependent, not a safe universal cap.

**E4.** https://arxiv.org/html/2407.03978 — ComplexBench averages **4.19 constraints** and **4.61 scoring questions**. Its decomposed, dependency-aware evaluator reached **87.82%** question-level human agreement versus **75.18%** for direct scoring; pairwise agreement was **61.4% vs 51.2%**. Decomposition, not a large consolidated rubric, is the demonstrated design.

**E5.** https://arxiv.org/html/2410.03608 — TICK evaluates **each checklist question in a separate judge call** and obtains **82.6%** GPT-4o question-level accuracy; checklist judging improves exact human-preference agreement **46.4%→52.2%**. The paper gives **no count-at-which-accuracy-drops measurement** because it deliberately decomposes.

**E6.** https://arxiv.org/html/2403.18771v2 — CheckEval checklists contain **20 relevance, 33 consistency, 27 coherence, and 24 fluency questions**. The authors say a pilot answering all questions simultaneously showed “no noticeable performance difference,” but publish **no values, sample size, confidence interval, per-question recall, or position analysis** and retain one-question-at-a-time as the default. This is the strongest counterevidence to a four-criterion cap, but it does not validate an 18-rule defect detector.

**E7.** https://arxiv.org/html/2307.03172 — Lost-in-the-Middle finds a U-shaped position effect over **10, 20, and 30 documents**; GPT-3.5’s middle-position QA fell below its **56.1% closed-book** result, and non-query-aware key-value retrieval reached a **45.6% worst case**. The source gives no criterion-list position number.

**E8.** https://arxiv.org/html/2404.06654 — RULER uses **500 examples per task per length** from 4k–128k. Across 13 tasks, GPT-4 declines **96.6→81.2** from 4k to 128k; Qwen2 **96.9→53.7**. Claimed context size therefore does not establish effective whole-document reliability.

**E9.** https://arxiv.org/html/2502.05167v3 — NoLiMa tests 13 ≥128k-context models without literal retrieval cues. At **32k, 11/13** fall below half their short-context baseline; GPT-4o falls **99.3%→69.7%**, with noticeable declines already at **2k–8k**. A prose-defect detector likewise cannot rely on exact query/document lexical overlap.

**E10.** https://platform.claude.com/docs/en/build-with-claude/prompt-caching — Anthropic requires exact reusable prefixes; default TTL is **5 minutes**. Five-minute writes cost **1.25×** base input and hits **0.1×**; minimum cacheable input is model-dependent (**1,024**, **2,048**, or **4,096** tokens in the documented table). For one truly identical prefix, 3 calls cost 1.45 fresh-input equivalents (about **52% less** than 3), and 6 cost 1.75 (about **71% less**). Different pack prefixes do not produce that arithmetic.

**E11.** https://developers.openai.com/api/docs/guides/prompt-caching — OpenAI caching starts at **1,024 tokens**, requires exact prefix matches, and currently advertises **up to 90%** input-cost reduction (model-dependent). Cached-token accounting advances in **128-token increments**. The source does not guarantee a discount for merely similar pack prompts.

**E12.** https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html — Bedrock’s default cache lifetime is **5 minutes**, reset on each hit; minimum tokens and checkpoint counts vary by model. Cache hits require content through the checkpoint to match. The source gives no universal cache-read price ratio.

**E13.** https://aws.amazon.com/bedrock/pricing/ — Bedrock’s published Claude 3.5 Sonnet example prices ordinary input at **$3.00/M**, 5-minute cache writes at **$3.75/M** (1.25×), and cache reads at **$0.30/M** (0.1×), corroborating Anthropic’s ratios for that model, not every Bedrock model.

**E14.** `/Users/sjors/.omp/agent/sessions/-tmp-worktrees-slopvac-work-slopvac-session-20260915/2026-09-15T15-29-48-433Z_01a0a5b0-4791-7626-9e6e-b9bc251434cf/local/rubric-design.md:249-303` — The design defines 8/12/18, reports **$0.29 vs $0.11**, calls the ≤900-token spine “cacheable,” and itself labels the 8-cap a heuristic requiring a consolidated-vs-chunked recall test. No provider/model ID, price date, token ledger, cache-hit trace, or underlying `SubagentScanDesign` artifact is supplied. A ≤900 common spine is below the **1,024-token** OpenAI and common Anthropic/Bedrock minima (E10–E12); the larger pack-specific prefix can recur across documents, but not across different packs solely because one document makes 3–6 calls.

**E15.** https://arxiv.org/html/2311.07911 — IFEval’s **541 prompts** contain only **1–3** verifiable instructions. Its GPT-4 instruction-level strict accuracy is **83.57%**, but it performs no 4/8/18-count comparison; it cannot validate C9’s caps.

## Assumptions-that-fail

| Assumption | Why it fails |
|---|---|
| Eight criteria is conservative. | Direct judge error is already large at five and ten criteria (E1); eight has no repo-specific calibration (E14). |
| Twelve units is a harmless output-length cap. | Naïve batching is significantly worse by six in the closest controlled unit-count study, with position effects (E3). |
| Eighteen grouped criteria preserve recall. | No published prose-judge experiment measures per-rule recall at 18; validated checklist methods decompose (E4–E6). |
| Three to six calls create cache reuse. | They create reuse only if the prefix is identical; C9’s calls are different packs, and the only explicitly common prefix is ≤900 tokens (E10–E14). |
| The $0.18 saving establishes the trade. | The amount lacks a reproducible ledger and cannot price an unmeasured false-negative cost (E14). |

## Alternatives

| Rank | Alternative conclusion | Support |
|---:|---|---|
| 1 | Use conservative decomposed packs until this repository measures recall: **≤4 criteria and ≤5 units**. | Stays below the first direct judge comparison at five (E1) and the batch size six where naïve batching significantly degrades (E3); matches decomposition gains (E4–E5). |
| 2 | Criterion count may matter less than document length; even five small packs can miss middle-document defects. | E7–E9. |
| 3 | A consolidated 18-question call may be acceptable on short documents with a strong model and structured output. | CheckEval’s unpublished-number pilot over 20–33 questions (E6); this remains plausible, not demonstrated. |

## Amendments

Paste-ready replacement for C9/§7:

> **Pack limits are provisional safety limits, not capability claims.** A SPAN pack contains at most **4 criteria** and at most **5 units**. These values keep the production default below the earliest adverse counts in the closest judge- and batch-composition evidence; they may be raised only by a versioned, model-specific repository evaluation showing non-inferior per-rule recall, malformed-output rate, and position robustness.
>
> Replace the single 18-rule PROBE with five packs: **(1)** AI tics (3), **(2)** abstract framing (3), **(3)** meta-process (2) + semantic overreach (2), **(4)** discourse structure (2) + restatement (1) + pedagogical calibration (1), **(5)** genre mismatch (1) + structural balance (1) + scope/density (2). Do not consolidate these packs until the paired control named below passes.
>
> Full-document dispatch is permitted only within the selected model’s empirically validated length bin. Above it, occurrence-oriented rules run on overlapping chunks; genuinely document-global rules are reported `judgement_unchecked` unless a separately validated whole-document route exists.
>
> Cache budgeting counts a hit only when provider telemetry reports a read for the exact reusable prefix. The **≤900-token spine is not assumed cacheable**. Pack-specific prefixes amortize across repeated documents/runs within provider TTL, not merely across different packs for one document. Report cold-write, cache-read, and uncached dynamic-input tokens separately. Cost never substitutes for the recall gate.

Replacement thresholds:

```text
SPAN_CRITERIA_MAX = 4
SPAN_UNITS_MAX = 5
PROBE_CRITERIA_MAX = 4
PROBE_PACK_COUNT = 5
```

## Unsupported

- **No evidence found** for a prose-quality LLM judge’s per-criterion precision/recall curve at exactly 1, 2, 4, 8, 12, or 18 simultaneous slopvac-like criteria.
- **No evidence found** for criterion-list position effects in a multi-criteria prose judge; available position results concern batched units or facts inside long contexts (E3, E7).
- **No evidence found** that 8 is either the optimal or a safe universal cap, or that 12 units is safe across models.
- **No evidence found** from the supplied material that reproduces **$0.29 chunked vs $0.11 consolidated**; model, provider, prices, tokens, cache state, and raw calls are absent (E14).
- **No evidence found** that an 8.7k pack prefix pays off from 3–6 *different* calls on a single document. It pays off only when that exact pack prefix recurs; at three or six identical calls the Anthropic/Claude-3.5 arithmetic is favorable (E10, E13).

## Strongest counter

CheckEval reports no noticeable pilot loss when answering 20–33 questions simultaneously (E6). Because it publishes no numerical comparison and defaults to separate questions, it supports testing C9’s consolidation but not shipping it before that test.

## Open evaluation questions

1. On human-adjudicated repository passages, what are per-rule precision, recall, abstention, and malformed-output rates at criterion counts **1/2/4/5/8/18**, holding documents, shots, model, and output schema fixed?
2. Cross unit counts **1/3/5/6/12** with four criteria; randomize unit and criterion order and report recall by ordinal position, not only macro-average.
3. Plant and naturally annotate defects at document quartiles over **1k/2k/4k/8k/16k/32k** token bins; compare full-document versus overlapping-chunk recall.
4. Compare the proposed five PROBE packs with the consolidated 18-rule pack using paired documents and a preregistered non-inferiority margin; price false negatives separately from API spend.
5. For each supported provider/model, record cache-write tokens, cache-read tokens, TTL, first-document cost, subsequent-document cost, and observed exact-prefix hit rate. Separate within-document calls from same-pack reuse across documents.