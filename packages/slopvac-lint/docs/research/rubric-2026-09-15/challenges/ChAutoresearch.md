Claim: The branch remains useful in parts, but its present judgement schema, evaluator, and abstention policy can land unchanged on the accepted candidate.

VERDICT: CHALLENGED

## Summary verdict

**PARTIALLY SUPERSEDED.** The 21 committed changes are topologically current with `slopvac-v3-candidate` (21 ahead, 0 behind), but semantic currency is the issue: the branch encodes an earlier six-field judgement contract and an unrelated 34-case prose classifier, while the accepted contract requires typed preservation classes, evidence roles, per-rule warrant thresholds, explicit masks, gates, packs, and content-derived identities (`rubric-contract.json:535-560,680-729,2784-2791`). The taxonomy/ownership work, deterministic heading rules, and some runner plumbing remain useful, but no commit set should land **as-is**; the tree is also dirty.

### Assumptions that fail

| Assumption | Evidence |
|---|---|
| “Judgement contract” names the accepted structure | Branch fields are `admission`, free-text `protects`, list `dims`, scalar `evidence_arity`, ceiling, and boolean `rewrite_exempt` (`packages/slopvac-lint/src/slopvac/model.py:163-220`); accepted records require mask-valued dimensions, `{min_arity, roles}`, `warrant_min`, closed-list `protects`, ceiling, and transition-aware rewriting (`rubric-contract.json:1149-1171,2788`). |
| The benchmark answers Q01–Q14 | It asks one accept/reject/preserve/abstain classification with quote/reason (`bench/rubric.json:1-74`) over 34 broad-category examples (`bench/cases.json:1-100`), whereas Q01–Q14 require per-rule threshold, dimensional reliability, batching, pack, cluster, checker, mutation, provenance, and long-document experiments (`rubric-contract.json:2720-2782`). |
| Current ancestry implies landability | The committed ancestry is current, but seven tracked files plus generated reference output are modified and `docs/rules.md` is untracked (`local://rubric-research/AutoresearchEvidence.md:5216-5431`). |

### Alternatives

| Rank | Conclusion | Evidence |
|---:|---|---|
| 1 | Rebase and split; port useful pieces into the accepted contract | Branch taxonomy is broader across all shipped rules (`model.py:88-158,270-301`), while the accepted evaluator schema is much richer (`rubric-contract.json:869-1056`). |
| 2 | Land only a corrected, squashed deterministic-heading slice | The two additions are deterministic syntax checks (`ai-tells-agentic.yml:2857-2907`; `prose-scope.yml:160-207`), outside the judgement packs (`rubric-contract.json:280-530`). |
| 3 | Abandon the branch wholesale | Safer than as-is landing, but would discard useful ownership/seed validation (`rules.py:148-190`) and runner evidence-retention plumbing (`bench/runner.py:1-24`). |

## Per-commit assessment

| SHA | What it does | Contract relevance | Landable as-is? | Reason |
|---|---|---|---|---|
| `fc261aeb53` | Penalizes abstention as terminal error | **conflicts** | No | Policy says classification `error`, weight 4 (`benchmark_contract.json:20-31`), opposite accepted first-class abstention (`rubric-contract.json:9-25,540-547`). |
| `3567284749` | Rewords three judgement contracts | **conflicts** | No | Changes model-visible admission/protection prose under obsolete fields (`ai-tells-agentic.yml:34-42`); accepted hashing treats every wording/whitespace change as a new rubric (`rubric-contract.json:2784-2790`). |
| `a43178f7f6` | Populates taxonomy/contract metadata on 232 rules | **partly aligned** | No | Ownership and seed links are useful, but records use free-text protection and no roles/warrant threshold (`ai-tells-agentic.yml:25-44`; `model.py:163-220`). |
| `60c7822434` | Adds typed dimension, ownership, contract schema/API/reference | **partly aligned** | No | Good single schema seam, wrong accepted shape; its tests explicitly pin that earlier shape (`test_judgement_metadata.py:38-45,367-402`). |
| `1473ba824f` | Offline harness setup tweak | **orthogonal** | No | Current entrypoint ultimately delegates to static taxonomy scoring, not adjudication (`autoresearch.py:1-22`; `deterministic_runner.py:71-194`). |
| `4a7ef71c8d` | Offline harness setup tweak | **orthogonal** | No | Same superseded static-contract path (`deterministic_runner.py:10-24,71-194`). |
| `c30c70f504` | Validates taxonomy counts/metrics | **conflicts** | No | Validates old dimensions, ownership, and field names (`benchmark_contract.json:1-33`), not accepted records or Q01–Q14. |
| `90924e283d` | Removes duplicate contrastive core | **partly aligned** | No, not standalone | Remainder survives as `ai-tells-structure...` (`ai-tells-agentic.yml:24-44`), and core survives under **changed ID** `ai-tells-agentic...` (`:2908-2960`). Its provenance wrongly points to nonexistent `ai-tells-agentic.contrastive-inversion-remainder` (`:2957-2960`). |
| `cace892253` | Repairs/adds slogan category and rules | **orthogonal** | No; squash/fix | Adds deterministic category absent from accepted judgement packs (`ai-tells-agentic.yml:2857-2910`; `rubric-contract.json:280-530`), plus the stale core cross-reference above. |
| `8aa80ba428` | First formulaic-heading implementation | **orthogonal** | No | Superseded by `cace892253`; final rules are deterministic syntax checks, not `heading-echo` adjudication (`prose-scope.yml:160-207`; `ai-tells-agentic.yml:2857-2907`). |
| `3736b25433` | Makes deterministic offline runner default | **conflicts** | No | It replaces model evaluation with metadata scoring (`autoresearch.sh:1-6`; `deterministic_runner.py:71-194`). |
| `b83a85257b` | Replaces unavailable model arm | **orthogonal** | No | Arm selection alone supplies none of accepted instrument identity/repeat comparability (`bench/arms.json:1-23`; `rubric-contract.json:2784-2788`). |
| `86af551c0d` | Adds partition/one-unit/arm/repeat selectors | **partly aligned** | No | Useful for Q05/Q06, but runner units are cases rather than rule/unit hashes (`bench/runner.py:718-744`; `rubric-contract.json:2704-2717`). |
| `939fc945c1` | Retains evidence; validates outcomes | **partly aligned** | No | Sound substrate, but output lacks accepted evidence roles/offsets and verdict schema (`bench/runner.py:380-425,640-676`; `rubric-contract.json:869-1056`). |
| `c21a6ade84` | Rejects malformed result sets | **aligned substrate** | No | Exact set/order checks are reusable (`bench/runner.py:390-425`), but validate the old row shape. |
| `5f970b2720` | Normalizes benchmark parser | **aligned substrate** | No | Robust payload extraction is reusable (`bench/runner.py:360-389`), not sufficient contract implementation. |
| `8f8a6592f5` | Simplifies online runner | **orthogonal** | No | Current protocol still measures broad case accuracy rather than accepted per-rule decisions (`bench/runner.py:677-717`). |
| `9ae7a4abfa` | Parses assistant payload/usage | **aligned substrate** | No | Usage accounting helps Q07, but accepted cache/version dimensions are absent (`bench/runner.py:340-378`; `rubric-contract.json:2784-2791`). |
| `2cdd00b6e4` | Introduces canonical online benchmark/assets | **partly aligned** | No | Multi-arm retained-evidence runner is useful, but rubric/cases encode the wrong instrument (`bench/rubric.json:1-74`; `bench/cases.json:1-100`). |
| `f05bffa9df` | Initial autoresearch harness | **orthogonal** | No | Superseded by later canonical then offline entrypoints (`autoresearch.py:1-22`; `autoresearch.sh:1-6`). |
| `5efdbd2730` | Initial autoresearch harness | **orthogonal** | No | Same superseded scaffold; no accepted rule-record or evaluator behavior remains attributable to it. |

## Dirty tree

This is unfinished integration, not a clean follow-up. `bench/runner.py` adds a per-request prompt digest but only records `batch_prompt_sha256`, not `rubric_revision`, `pack_id`, `instrument_id`, or the full accepted cache key (`bench/runner.py:640-649,776-780`; `rubric-contract.json:2784-2790`). `tests/test_bench_runner.py:451-466,607-642` adjusts that provenance and flips entrypoint expectations, showing the harness transition is still active. Three YAML edits alter model-visible contract prose, so they collide directly with accepted content-hash semantics (`ai-tells-agentic.yml:34-42`; `rubric-contract.json:2790`). `packages/slopvac-lint/docs/rules.md` is regenerated from the obsolete schema, while untracked `docs/rules.md` duplicates that generated reference surface; neither is an authored contract source. `uv.lock:511` merely resyncs editable package version 2.2.0→2.3.2 (`local://rubric-research/AutoresearchUvLock.diff:1-13`). Discard/regenerate generated and lock artifacts only after the accepted schema is implemented.

## Conflicts with the contract

- **Dimensions:** branch uses an omission-based uppercase list and even states rules ask “two or three, not four” (`model.py:181-185`); accepted uses all four lowercase keys with explicit `ask|inapplicable`, forbidding injected constants (`rubric-contract.json:559-562`).
- **Evidence/warrant:** scalar arity cannot encode named roles, arity above two, source restrictions, or `warrant_min` (`model.py:186-191`; `rubric-contract.json:680-697`).
- **Protection/rewrites:** free text plus `rewrite_exempt: bool` cannot express the seven closed preservation classes or typed `allowed_transitions` (`model.py:176-200`; `rubric-contract.json:854-867,1132-1134,2788`).
- **Admission/runtime:** branch has prose mentioning scope/double jeopardy but no A1–A5 execution, origin classification, core adjudication, exact-evidence abstention, pack limits, cluster gate, or reporting-only capped penalty (`model.py:168-175`; `rubric-contract.json:3-35,735-754`).
- **Abstention:** this is a real evaluator conflict, but benchmark-local: product rule loading is unchanged. It becomes release-blocking if this runner is reused for the accepted rubric (`bench/runner.py:677-717`; `benchmark_contract.json:20-31`).
- **Contrastive removal:** it does not delete the remainder or mechanical behavior, but changes the core’s qualified ID/category from baseline `ai-tells-structure` to `ai-tells-agentic`; custom category enablement and A3 linkage can change (`research-rubric-review.../ai-tells-agentic.yml:20-60`; branch file `:24-44,2908-2960`).
- **Headings:** neither new pattern duplicates `heading-echo`: the patterns classify title syntax, while `heading-echo` compares heading with its first sentence and needs defect+antecedent evidence (`ai-tells-agentic.yml:499-526`; `rubric-contract.json:1828-1848`). They add deterministic coverage outside the five PROBE packs, not new accepted judgement categories (`rubric-contract.json:287-331`).

## Recommended disposition

**Rebase and split; do not merge or cherry-pick the branch wholesale.**

- **Land as-is:** none.
- **Rework against the accepted contract:** `60c7822434`, `a43178f7f6`, `3567284749`; separately squash and correct `8aa80ba428` + `cace892253` + `90924e283d`; port—not cherry-pick—the reusable online-runner chain `2cdd00b6e4`, `9ae7a4abfa`, `8f8a6592f5`, `5f970b2720`, `c21a6ade84`, `939fc945c1`, `86af551c0d`, `b83a85257b` into the Q01–Q14 instrument.
- **Drop:** `5efdbd2730`, `f05bffa9df`, `4a7ef71c8d`, `1473ba824f`, `3736b25433`, `c30c70f504`, `fc261aeb53`.

## Risks

The strongest counter to landing is not cosmetic drift: the branch would make an obsolete schema appear authoritative and would score a legitimate abstention as model error. Additional risks are silent category-ID breakage for the contrastive core, stale generated reference text, misleading benchmark “quality” numbers unrelated to Q01–Q14, and incomparable cached results because accepted content-derived identifiers are missing.