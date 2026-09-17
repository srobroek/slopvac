Claim: The contract is not yet a consistent or implementable specification: several gates defeat their own rules, the output schema cannot represent algorithmic outcomes, and multiple aggregation/version identities lack required inputs.

VERDICT: CHALLENGED

## Verdict

| Contract section | Verdict | Reason |
|---|---|---|
| dimensions | AMEND | Named levels are coherent, but masked `inapplicable` values have no decision semantics. |
| gates | BROKEN | Preservation can suppress the safety rule; A3 and A5 conflict; `quoted` is not a mutually exclusive origin. |
| evidence_requirements | BROKEN | The required projection map and cross-unit coordinate system do not exist as specified. |
| rewrite_requirements | BROKEN | A checker outcome is absent from the output enum; safety transitions are neither sourced nor stored per rule. |
| decision_algorithm | BROKEN | It produces schema-invalid output and does not define how model verdicts are reconciled. |
| composition | AMEND | The 65-rule partition survives, but PROBE metadata and the 12-occurrence cap do not. |
| aggregation | BROKEN | The reporting/pass-fail split is coherent, but the cluster gate is not computable as written. |
| versioning | BROKEN | Hash recipes reference absent content and undefined canonical encodings. |
| model_output_schema | BROKEN | Conditionals are incomplete; occurrences are untyped; checker veto cannot validate. |
| category_packs/rule_records | BROKEN | Records omit decision-bearing criterion/transition content, and one source scope is invented. |

## Findings

1. **`rewrite_requirements.status_enum` / `model_output_schema.properties.rewrite_status`** — The algorithm emits `withheld_checker_veto`, but the schema permits only `not_applicable`, `proposed`, and `withheld_needs_fact`; its confirm conditional excludes veto too. Evidence: `rubric-contract.json:547-550,951-960,1051-1056,1132-1143`. **Minimal fix:** add the value to the schema and confirm conditional, including `rewrite=null` and the specified demotion.

2. **`gates.preservation` / `category_packs[ste-safety]`** — `normative_obligation` is preset by safety signal words, while the only judgement error rule explicitly protects that class. Thus the YAML’s bad `CAUTION`→`WARNING` example is preserved before scoring. Evidence: `rubric-contract.json:129-140,789-807`; `packages/slopvac-lint/src/slopvac/rules/ste-safety.yml:10-43`. **Minimal fix:** preservation must protect obligation force from generic rewrites but must not exempt `ste-safety.risk-level-word-missing-or-wrong` from adjudicating the signal word.

3. **`rewrite_requirements.exemptions` / `rule_records[ste-safety…]`** — The contract declares `WARNING→DANGER`, `CAUTION→WARNING`, and `NOTE→CAUTION`, but the rule record contains no `allowed_transitions`; the YAML supports only a consequence-based higher/lower choice and demonstrates only `CAUTION→WARNING`. It also permits a marker to be “wrong,” while the contract allows upgrades only. Evidence: `rubric-contract.json:1133-1137,2443-2465`; `ste-safety.yml:10-43`. **Minimal fix:** store exact transitions on the rule record and derive a complete bidirectional policy from an explicit software risk taxonomy; remove unsupported `NOTE`/`DANGER` transitions meanwhile.

4. **`gates.admission[A3,A5]`** — A3 says every fired mechanical core runs its remainder and PRESERVE/REJECT suppresses the core; A5 makes generated/template/vendored units inadmissible, so the algorithm drops before any suppressing verdict. Evidence: `rubric-contract.json:734-760`. **Minimal fix:** define core disposition at A5: either suppress both core and remainder for excluded origins, or explicitly exempt core adjudication from A5.

5. **`unit_schema.origin` / `gates.admission[A5]`** — `quoted` is encoded as an alternative to `authored|generated|vendored|template`, although quotation is a region property that can coexist with every provenance. A generated quoted specimen can therefore be either DROP or PRESERVE depending on an undefined choice. Evidence: `rubric-contract.json:752-754,2709-2711`. **Minimal fix:** split `origin` from `region_class`; make `quoted_specimen` an orthogonal boolean/class with explicit precedence.

6. **`dimension_policy.masks` / `decision_algorithm`** — Schema permits `harm=inapplicable` and `repair=inapplicable`, but the algorithm only tests `harm==none`; an inapplicable HARM therefore falls through to a confirmed suggestion. Evidence: `rubric-contract.json:543-550,558-561,972-1007`. No current rule record uses the mask, so this is latent rather than observed. **Minimal fix:** define masked-dimension branches, or remove `inapplicable` until a rule-specific decision table exists.

7. **`model_output_schema.verdict` / `decision_algorithm`** — The model emits a verdict and `admissible`, while the deterministic algorithm independently derives DROP/PRESERVE/ABSTAIN/REJECT/CONFIRM. A schema-valid `confirm` with `fit=absent` is currently possible, and no trust/recompute rule exists. Evidence: `rubric-contract.json:538-550,869-1056`. **Minimal fix:** remove derived fields from model output, or state that the host recomputes and rejects any mismatch; encode that validation.

8. **`model_output_schema.occurrences` / `composition.probe_occurrences_max`** — `occurrences` has no item schema, is not required for probes, and does not enforce 12. A single top-level verdict also cannot represent confirmed occurrences plus a truncated remainder: `missing_context` would make the whole verdict ABSTAIN. Evidence: `rubric-contract.json:285-287,944-950,1040-1056`; Q14 at `2774-2777`. **Minimal fix:** add a recursive occurrence definition, `maxItems`, per-occurrence outcomes, and a separate `truncated` flag/count.

9. **`aggregation.cluster_gate`** — “Passage,” “primary” defect span, and component coordinates are undefined. Unit evidence uses unit-relative offsets, so spans from different units cannot be overlap-tested without document coordinates. No registered dependence table or table identity is supplied. Evidence: `rubric-contract.json:3-7,682-697,914-927`. Bootstrapping from raw verdicts is not logically circular, but using the same labelled output to construct and validate the gate is calibration leakage. **Minimal fix:** define passage boundaries, document-coordinate projection, primary-span selection, and ship a frozen held-out-derived table with a hash.

10. **`aggregation.judgement_score`** — The reporting/pass-fail split itself is coherent: judgement penalties do not gate, while the safety error separately counts toward `max_errors`. But the value 15 is justified solely by a passing band that the reporting score never enters. Evidence: `rubric-contract.json:28-35`; `score.py:267-272`; `config.py:736-747`. Prior review found no published stochastic cap (`local://rubric-research/ChAggregation.md:39-45`). **Minimal fix:** label 15 provisional and calibrate its reporting interpretation, or report uncapped and capped values.

11. **`composition.probe_packs[PROBE-4]` / `gates.preservation.pack_scope`** — The gate says a pack lists its collided protection classes, but PROBE-4 lists none. Its four rules span four categories and collectively require all seven classes. Evidence: `rubric-contract.json:315-322,849-865,1354-1374,1568-1590,1692-1715,2332-2353`. **Minimal fix:** add the unioned `protects` and explicit multi-category/scope metadata to every probe pack.

12. **`versioning.pack_id` / `rule_records[*]`** — The hash requires criterion, discriminator, admission, allowed transitions, template revision, and ordered full shots, but rule records contain none of those, and probe packs have no single `category` or `chunk`. “Canonical ordered bytes” names no canonicalization. Evidence: `rubric-contract.json:287-330,1145-1167,2784-2792`. **Minimal fix:** make all hashed content authoritative fields, define JCS/UTF-8 canonicalization and prompt rendering, and define multi-category probe serialization.

13. **`evidence_requirements.exactness` / `unit_schema.range`** — Code-point offsets plus `source_sha256` would be sufficient only with a deterministic, retained projection. Current parsing strips pieces, inserts spaces, decodes HTML, and stores line starts—not character-to-raw-byte mappings. Context has no independent range/map at all. Evidence: `rubric-contract.json:682-695,2708-2717`; `analyze.py:582-606,817-845`. **Minimal fix:** specify and persist projected-code-point→raw-byte segments for unit and context, including synthetic gaps and HTML/entity normalization.

14. **`rule_records[*].warrant_min`** — All 65 records set 2; no declared exception uses the promised local-span threshold of 1. This reinstates the universal threshold prior review explicitly marked unsupported. Evidence: `rubric-contract.json:697,1145-2693`; `local://rubric-research/ChGates.md:61-67`. **Minimal fix:** treat the threshold as calibration-gated configuration and identify local rules whose exact span alone satisfies warrant.

15. **`rule_records[ste-nouns.long-domain-term-without-short-form].evidence.roles`** — Required `defect+antecedent` cannot prove the missing short form; the YAML bad example contains only the long term. Evidence: `rubric-contract.json:2332-2353`; `ste-nouns.yml:47-73`. **Minimal fix:** use one defect span plus a host-verified full-document absence predicate, not a fictitious antecedent.

16. **`rule_records[orwell.concrete-floor].scope_class`** — In a ten-record YAML spot-check, nine existence/category/scope mappings agree; this record is assigned `probe` although the YAML has no `scope`. Evidence: `rubric-contract.json:2096-2117`; `orwell.yml:146-166`. **Minimal fix:** add an authoritative document scope or record the derivation explicitly. The pack partition itself survives: category totals are 65; probe packs contain 18 and span packs 47, each observed once (`rubric-contract.json:44-281,287-530`).

17. **`composition.probe_occurrences_max` / `aggregation.preserves.rule`** — The 12-occurrence cap and three-preserve review trigger remain asserted despite being unresolved/unsupported in prior reports. Evidence: `rubric-contract.json:286,37-38`; `local://rubric-research/ChComposition.md:82-87`; `ChAggregation.md:39-45`. **Minimal fix:** mark both as disabled experimental policy until Q14 and exposure-normalized calibration supply thresholds.

## Internal contradictions

- Checker veto is required by the algorithm but forbidden by the output schema.
- Safety-marker preservation preempts the rule whose purpose is to correct safety markers.
- A3 requires adjudication where A5 can forbid it.
- `quoted` is simultaneously provenance and preservation region.
- Probe packs violate the stated pack-level protection contract.
- Hash recipes require fields the authoritative records do not contain.

## Implementation blockers

1. No valid serialization for `withheld_checker_veto`.
2. No rule for reconciling model-emitted and host-derived verdict/admissibility.
3. No executable occurrence schema or truncation accounting.
4. No projection-map format for unit/context evidence or cluster overlap.
5. No definitions for passage, primary span, dependence-table content/version, or component boundaries.
6. No canonical prompt/pack bytes, full shots, discriminator/admission fields, or multi-category probe hash rule.
7. No per-rule safety transitions and no complete risk-marker transition policy.
8. No precedence for generated-and-quoted regions or A3/A5 core disposition.

## Unresolved

- Q01: warrant 1 versus 2 remains uncalibrated; the contract nevertheless fixes 2 everywhere.
- Q08/Q13: cluster precision, dependence stability, and human-prose behavior remain unmeasured.
- Q10: typed-checker false-veto and unsafe-pass rates remain unmeasured.
- Q14: the 12-occurrence cap remains unvalidated.
- The 4-criterion/5-unit limits are correctly labelled provisional, not proven safe.