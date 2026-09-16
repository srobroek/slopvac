Claim: C1’s shared spine is defensible only as common anchors plus rule-specific profiles; C12’s semver/cache contract is not. Model-visible PATCH wording, omitted pack inputs, and unversioned scoring configuration defeat cache safety and comparability.

VERDICT: CHALLENGED

## Verdicts

| Claim ID | Verdict | One-line reason | Evidence |
|---|---|---|---|
| C1 | **AMEND** | MQM supports a stable core plus selected project/error-type profiles, but not replacing rule-level semantics with category-level prose; slopvac’s same-category rules already ask materially different questions. | E1–E3 |
| C12 | **REPLACE** | No model-visible wording change is safely score-inert; the proposed hash omits decision-bearing fields, its comparison tuple omits evaluator/scorer state, and the design itself places thresholds outside `slopvac.toml`. | E4–E14 |
| C12 PATCH-without-invalidation | **REPLACE** | Formatting, punctuation, option labels, and order alone have produced 35–76-point swings; a model-visible PATCH must change the exact prompt revision and invalidate cached judgements. | E6–E8 |

## Evidence

**E1 — MQM shared core plus profiles.** [MQM Error Typology](https://www.themqm.org/mqm-pillars/typology/) defines **7** high-level error types, a predefined MQM-Core subset, and tells implementers to select the error types needed from MQM-Full. This supports common anchors plus project/rule profiles, not 65 duplicated anchor sets.

**E2 — Category packaging cannot erase rule semantics.** `packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml:46-72` gives `contrastive-inversion-remainder` its own admission/discriminator; `packages/slopvac-lint/src/slopvac/rules/ste-practices.yml:12-63` gives two same-category judgement rules different tests and exceptions. The design itself retains one criterion per rule at `local://rubric-design.md:30-35`. Numbers: **65 rules across 14 categories** (`local://rubric-design.md:7-18`).

**E3 — MQM revisions are substantive, not cache-semver precedent.** [MQM 2.0 change history](https://themqm.org/error-types-2-typology-changes/) records renamed, moved, added, and deleted error types relative to MQM 1.0. Source gives no compatibility promise or rule that patch wording preserves annotations.

**E4 — Internal hash contradiction.** `local://rubric-design.md:30-35,382-390` says packs contain discriminator, admission, shots, and four new YAML fields, but hashes only criterion text, dimensions, and “shot set.” It omits discriminator, admission, `protects`, evidence role/arity, constants, ceiling, `rewrite_exempt`, shot order/content serialization, template, and output schema. `rubric_version` inside every `pack_id` also means a spine change invalidates every pack, contradicting “any pack edit invalidates its own cache and nothing else.” Source numbers: **4** new YAML fields are asserted but not enumerated in the hash.

**E5 — Threshold separation is legitimate, but scorer identity is required.** [MQM scoring models](https://www.themqm.org/mqm-pillars/the-mqm-scoring-models/) separates typology from implementer-selected weights, calibration, and passing thresholds; its example uses **4** severities and multipliers **0-1-5-25**, and warns calibrated scores may not be comparable across tasks/organizations. Thus raw verdict caches may survive a scorer retune, but aggregate scores may not.

**E6 — Formatting-only changes move scores sharply.** Sclar et al., [“Quantifying Language Models’ Sensitivity to Spurious Features in Prompt Design”](https://arxiv.org/html/2310.11324v2), test **11 tasks, 15 models, 8 formats** and report up to **76 accuracy points** between formats; GPT-3.5’s median maximum difference is **6.4 points** and maximum **56**. This directly refutes “wording that cannot move a score” as an operational category.

**E7 — Minimal prompt edits alter both scores and rankings.** Mizrahi et al., [“State of What Art?”](https://aclanthology.org/2024.tacl-1.52.pdf), evaluate **20 models, 39 tasks, 3 benchmarks, 6.5M instances**. Minimal prompt perturbations produce maximum spreads up to **62.1 points**; **21/25** best-prompt comparisons differ significantly and **15/25** have negative Kendall rank correlation.

**E8 — Shot order is content.** Lu et al., [“Fantastically Ordered Prompts”](https://aclanthology.org/2022.acl-long.556.pdf), enumerate up to **24** few-shot permutations and show the same examples ordered differently ranging from **>85%** to about **50%** accuracy; their selector improves performance by **13% relative**. Therefore `shot set` is insufficient: ordered, fully rendered shot messages and labels must be hashed.

**E9 — Real caches hash the request and provider configuration.** [promptfoo caching](https://www.promptfoo.dev/docs/configuration/caching/) keys on provider identifier, prompt/request digest, provider configuration, and context variables; repeats use separate namespaces and TTL defaults to **14 days**. C12 omits model/provider, full rendered prompt, decoding settings, and repeat index from its cache/comparison identity.

**E10 — Evaluation task versions do not replace exact configuration.** [lm-evaluation-harness task guide](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/task_guide.md) says the YAML **plus codebase commit hash** enables precise replication; task metadata should include `version`, while config separately records prompt template, few-shot count, generation kwargs, filters, and repeats. Source gives no semver/cache-reuse rule.

**E11 — Leaderboards re-run versioned configurations.** [HELM leaderboard reproduction](https://crfm-helm.readthedocs.io/en/latest/reproducing_leaderboards/) requires the version-specific run-entry file, schema, model, train-trial count, and evaluation-instance cap; published examples vary from **1 to 3 trials** and **100 to 10,000 instances**. It instructs rerunning, not carrying judgements across rubric edits.

**E12 — Run provenance includes evaluator state.** [Inspect logs](https://inspect.aisi.org.uk/logs.html) records task/version, model, model arguments, creation time, packages, platform, and git revision; sample records include the rendered input and generation configuration. Source gives no single numeric threshold. These belong in an evaluation manifest even if they do not belong in `pack_id`.

**E13 — Dataset practice couples semantic version with content identity.** [Croissant specification](https://docs.mlcommons.org/croissant/docs/croissant-spec.html) defines dataset `version` and distribution/file `sha256`; [Datasheets for Datasets](https://arxiv.org/pdf/1803.09010) asks maintainers to publish updated versions while keeping older versions accessible. Neither source licenses reuse after content edits; both favor immutable identity. Sources give no cache-reuse number.

**E14 — Re-annotation changes published rankings.** [WMT22 Metrics task](https://www.statmt.org/wmt22/metrics/index.html) labels corrected MQM annotation artifacts `v3`, reports bugs in annotations/submitted scores, and publishes corrected results after the initial ranking. Source gives no effect-size number; the practice is correction plus recomputation.

**E15 — “Never in rubric text” is internally and presently false.** `local://rubric-design.md:354-369` hard-codes judgement penalty **20**, cluster threshold **≥3**, category threshold **≥2**, and HARM threshold **3**. Existing defaults also live in rule YAML (`packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml:4-8`) and Python profiles (`packages/slopvac-lint/src/slopvac/profiles.py:31-67`), while project overrides live in `slopvac.toml:43-75`.

**E16 — Independent policy/technique evolution has precedent.** [WCAG techniques](https://www.w3.org/WAI/WCAG22/Understanding/understanding-techniques) says success criteria are stable while informative techniques update periodically; [Vale MinAlertLevel](https://docs.vale.sh/keys/minalertlevel) separates the reporting threshold (`suggestion`, `warning`, `error`) and CI failure behavior from rule prose. These support separation, not omission of the resolved policy hash.

## Assumptions-that-fail

| Assumption | Failure evidence |
|---|---|
| Humans can identify model-visible wording that cannot move a score. | E6–E8 show punctuation, formatting, labels, and order can move scores by tens of points. |
| `pack_id` identifies all decision-bearing pack content. | E4 lists omitted gates, constants, ordered shots, template, and schema. |
| Identical `(rubric_version, pack_id set, unit set)` is sufficient for comparison. | E9–E12 require request digest, evaluator model/config, repeats, runner revision, and scorer policy. |
| A prompt comparison can require identical pack IDs. | If criterion, shots, or pack prompt changes, E4’s own formula changes `pack_id`; the rule makes that intended comparison impossible. |
| All thresholds/weights are outside rubric text. | E15 shows four operational thresholds in §9 and three current sources of policy defaults. |

## Alternatives

| Rank | Alternative | Likelihood |
|---|---|---|
| 1 | Separate schema compatibility (`rubric_api_version`) from exact content identity (`rubric_revision`, `pack_id`, full request digest) and re-run any changed model-visible instrument. | High |
| 2 | Publish immutable benchmark releases and fully rebaseline each release, HELM/WMT style. | Medium-high |
| 3 | Keep the proposed semver labels, but permit cache reuse only when exact model-visible hashes and evaluator manifests are unchanged; PATCH becomes release metadata only. | Medium |

## Strongest counter

The proposed PATCH category has no observable decision rule: the cited studies show that changes a reviewer would call cosmetic can shift accuracy by **35–76 points**. Exact prompt identity, not editorial intent, must govern cache reuse.

## Amendments

### C1 replacement

> **One content-addressed global spine, generated category/scope packs, and rule-specific criterion records; no duplicated per-rule copy of the spine.** The spine owns common FIT/HARM/WARRANT/REPAIR anchors and the output contract. A pack is a batching and calibration unit, not a substitute for rule semantics. Every rule record retains its criterion, discriminator, admission conditions, protected classes, evidence contract, dimension constants/mask, ceiling, rewrite exemptions, and examples.

### C12 replacement

> `rubric_api_version` is semver for parser/schema compatibility: MAJOR removes or changes existing fields or meanings; MINOR adds optional fields or enum members only when old readers demonstrably ignore unknown values; PATCH changes no model-visible bytes and no scoring behavior. `rubric_revision = sha256(canonical_model_visible_spine_bytes)` changes on **every** model-visible wording, whitespace, formatting, ordering, anchor, gate, or schema change. There is no score-inert model-visible PATCH.
>
> `pack_id = sha256(canonical_ordered_pack_bytes)`, where the bytes include category, scope class, chunk, ordered rule records and IDs, criterion, discriminator, admission, dimensions and constants, protects, evidence roles/arity, ceiling, rewrite exemptions, output schema/template revision, and ordered full shot messages, labels, and delimiters. Do not include `rubric_api_version` in `pack_id`; combine `rubric_revision` and ordered `pack_id`s in `instrument_id`.
>
> `judgement_cache_key = sha256(instrument_id, unit_content_and_context_hash, provider, model_id_and_revision, full_rendered_request_digest, system_prompt, decoding_config, seed, repeat_index, evaluator_runner_revision)`. Any changed field is a cache miss.
>
> Thresholds and weights may live outside model-visible rubric text. Store the canonical resolved values and aggregation algorithm in `scorer_config_sha`. Retuning them may reuse raw verdicts, but **must recompute scores/gates** and starts a new aggregate-score series.
>
> A comparison declares its independent variable. All non-varied fields must match: instrument identity, ordered packs, unit/dataset content hashes, evaluator/scorer configuration, runner revision, and sampling/repeat protocol. A model comparison varies only model identity; a prompt comparison varies only the named prompt component and reruns both paired arms on the same units. Report cross-release results as separate instruments, never one continuous series.

## Unsupported

- **UNSUPPORTED:** the exact MAJOR/MINOR/PATCH mapping has no cited benchmark precedent.
- **UNSUPPORTED:** any model-visible wording class “cannot move a score”; available evidence refutes it.
- **UNSUPPORTED:** “new enum reason is parse-compatible” without a demonstrated unknown-enum reader; the design calls preservation reasons a closed list.
- **UNSUPPORTED:** “thresholds/weights never in rubric text” as a universal standard. Separation has analogues, but resolved scorer identity remains mandatory.
- **UNSUPPORTED:** BIG-bench, OpenAI Evals, SemEval, or CoNLL evidence establishing safe cached-judgement reuse after guideline wording changes; no such evidence found.

## Open evaluation questions

1. On the repo’s adjudicated corpus, measure verdict flips, dimension deltas, abstention changes, and rank changes for punctuation, whitespace, label-name, anchor-paraphrase, and shot-order mutations; run repeated paired trials per supported evaluator model.
2. Mutation-test the cache key: alter each discriminator, admission field, constant, protected class, evidence role/arity, ceiling, rewrite exemption, shot label/order, template, model parameter, and scorer threshold; require the appropriate judgement miss or score recomputation.
3. Compare global-only, spine+category-pack+rule-record, and duplicated per-rule-spine arms on the same units; measure accuracy, calibration, false preserves, token cost, and cross-rule score drift.
4. Retune only scorer thresholds/weights over frozen raw verdicts and verify raw-cache reuse while aggregate IDs, scores, gates, and comparison series change.