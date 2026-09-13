Claim: The audit’s steering and judgement rewrites are safe, executable reductions in slop, and its six judgement rules can be mechanised without materially increasing false positives.
VERDICT: CHALLENGED

## Summary
The current skill produced most of the measured gain: 16.87→3.62 findings/100 words; the proposed steering improved only 3.62→3.25 (`evals/REPORT.md:37-45`).
The report’s compression causation is unproved: one generation per cell, no repeats, one model, and multiple simultaneous instruction changes (`evals/REPORT.md:123-128`).
On the 418-word parsed/534-word raw target README, the four-pass rewrite required at least 95 review operations, 21 claim rows, nine section counts, and four evidence excerpts; linear scaling is about 680 operations at 3,000 words.
The staged selector is not executable as written: the same README selects 28 judgement rules as `readme`, 38 as `consumer-docs`, and zero as the skill’s `consumer` genre because `recommended_for` uses incompatible vocabularies.
Four of six proposed mechanisations are unsafe or non-executable: human hits were connector 0, exact anaphora 0, heading echo 39, concrete floor 274, long-term heuristic 6, and glossary equality N/A.
The proposals that survive are canonical CLI/exit wording, removal of the three tokenizer contracts, narrow duplicate merges, and connector mechanisation; the rest need the modifications below.

## Verdicts

### Steering.F1: Replace the workflow with the canonical lint command and fuller JSON/option contract
- verdict: ACCEPT-MODIFIED
- counter-evidence: The canonical command and named JSON fields correct drift, but the option catalogue does not itself reduce prose slop. The current shorthand works according to `Steering.md:F1`, so describing every low-frequency HTML/category/locale flag in an always-loaded skill adds routing detail rather than changing writing behavior.
- modification: Keep only the canonical `slopvac lint … --format json`, the shorthand equivalence, `.summary`/`.documents[].findings`/`.documents[].unchecked`, and exit meanings in `SKILL.md`; put HTML and option catalogues in an on-demand CLI reference.
- risk if applied as proposed: none
- word-count delta: -21 words standalone (184 replaced, 163 inserted), measured with the same word-token probe across the cited line ranges. This overlaps F2 and must not be summed with it.

### Steering.F2: Unify exit-code, genre routing, and PASS/REVISE prose
- verdict: ACCEPT-MODIFIED
- counter-evidence: Exit 2 and genre drift are real (`write-docs/SKILL.md:29-63`; `review-docs/SKILL.md:27-50`), but the replacement drops the user-facing verdict fields `Register`, `Claims`, `Action`, and `False positives` at `review-docs/SKILL.md:184-213`. Those fields force concrete output and preserve rule-FP evidence.
- modification: Apply the unified exit and genre text, but retain the existing verdict shape and false-positive reporting contract. State that exit 0 can still contain findings.
- risk if applied as proposed: breaks verdict/false-positive reporting contract
- word-count delta: -44 (146→102), with overlap against F1.

### Steering.F3: Replace the normal-tier warning with exact rule/tier prose
- verdict: REJECT
- counter-evidence: The attacked sentence says normal reports contractions and em dashes; the audit’s own evidence says both rules are enforced at normal (`Steering.md:F3`). It does not mention omitted `that`, so the claimed conflation is absent. The replacement exposes internal rule IDs without evidence that this changes agent behavior.
- risk if applied as proposed: instruction load↑ with no demonstrated slop reduction
- word-count delta: -3 (52→49).

### Steering.F4: Add anti-compression instructions for semicolons, omitted `that`, and chained clauses
- verdict: ACCEPT-MODIFIED
- counter-evidence: The count change is real—semicolon 1→15 and omitted-`that` 5→15 (`evals/REPORT.md:72-83`)—but “because compression” is causal language unsupported by the experiment. The report changed a whole ruleset, ran one sample per cell, and explicitly says per-topic differences are not reliable (`evals/REPORT.md:123-128`). No arm added only the proposed counter-instruction.
- modification: Add the narrow guard “Split two instructions into sentences; do not use a semicolon to meet the cap. Preserve `that` where it marks a clause boundary.” Label the cause unestablished and A/B this instruction with repeated generations before adding the longer verb list.
- risk if applied as proposed: none
- word-count delta: +16 (32→48).

### Steering.F5: Replace 17 sentence rules with compensating-tell counter-instructions
- verdict: REJECT
- counter-evidence: The replacement deletes existing rules for comparative baselines, quantities, bare quantifiers, presumptive openers, attribution, and document-level hedge balance (`write-docs/SKILL.md:70-86`). The eval attributes the dominant improvement to the old skill, 16.87→3.62, versus only 3.62→3.25 for the new rules (`evals/REPORT.md:37-45`). No ablation shows which old rules are dispensable.
- risk if applied as proposed: FN↑ for unsupported comparisons, quantities, attribution, and presumptive prose
- word-count delta: -253 (373→120); the large saving is achieved partly by deleting unablated controls.

### Steering.F6: Replace adversarial review with four register/structure/claims/stance passes
- verdict: REJECT
- counter-evidence: A simulation on `unguided__readme-cache.md` found 21 prose blocks, 33 sentences, nine H2 sections, and 21 externally checkable claim candidates. Minimum work was 34 register operations (frame plus sentence scan), 18 heading/count operations, 21 claim verifications/table rows, and 22 stance operations: at least 95 operations before rewrites. The required evidence included four excerpts (37 quoted words minimum), nine section-count entries, and 21 source/path/command/result rows. At the linter’s 418 words, linear scaling to 3,000 words is about 680 operations and roughly 151 claim rows. The structure rule also flags equal-length one-paragraph sections such as Backends, Contributing, and Roadmap merely because they are within 20%, although their topics legitimately differ (`unguided__readme-cache.md:72-100`).
- modification: none; retain targeted adversarial checks. If a pass procedure is desired, cap evidence to the weakest claim, longest paragraph, and one anomalous sibling rather than tabulating every claim.
- risk if applied as proposed: context exhaustion and FP↑ from length symmetry
- word-count delta: -61 static words (194→133), but dynamic review context grows without a bound.

### Steering.F7: Delete duplicated gate/configuration prose and mechanically clean the skills
- verdict: ACCEPT-MODIFIED
- counter-evidence: The exact deletion candidates remove 290 words (310→20), but “make the skill pass its own normal profile” confuses artifact lint cleanliness with steering effectiveness. The skill deliberately quotes forbidden forms as examples, and the audit does not separate pedagogical matches from operative prose (`Steering.md:F7`).
- modification: Deduplicate runner selection and gate configuration exactly as proposed. Do not rewrite examples or judgement guidance solely to make the skill’s aggregate lint score clean; triage each self-finding first.
- risk if applied as proposed: FN↑ if useful negative examples or judgement instructions are deleted to improve a self-score
- word-count delta: -290 for the two exact deletion candidates; the broader cleanup proposal has no bounded delta and is therefore not measurable as written.

### Steering.F8: Add seven counter-signal inspections to every review
- verdict: REJECT
- counter-evidence: The proposal adds seven uncalibrated inspections while `counter-signals.md` itself says thresholds require calibration, as quoted in `Steering.md:Decommission candidates`. The four-pass simulation already becomes unbounded on claims; adding density and dispersion calculations repeats that problem. A low/high result is explicitly “not evidence of authorship,” so the instruction supplies no decision threshold or action.
- risk if applied as proposed: context load↑ and inconsistent reviewer decisions
- word-count delta: +50.

### JudgementRules.F1: Select judgement rules by genre, triggered spans, document scope, family, and context
- verdict: REJECT
- counter-evidence: `write-docs` emits genre `consumer` (`write-docs/SKILL.md:29-35`), while categories use at least `consumer-docs`, `readme`, and `reference` (`ai-tells-agentic.yml:23`; `orwell.yml:5`; `ste-*` category headers). A corpus probe over all 67 judgement entries selected 28 for `readme`, 38 for `consumer-docs`, and 0 for `consumer`. The target baseline has 68 findings across 61 spans and 34 rule IDs, so “spans implicated by gate findings” is not a small candidate set. Current judgement scope counts are 24 sentence, 25 paragraph, 17 document, and one prose rule. The stage has no deterministic mapping from a finding to a judgement rule until `trigger_rules` exists, and that field is itself only proposed.
- modification: none. First normalize one genre vocabulary and merge true duplicates. Then trial a selector on fixed documents and report selected-question count, missed judgement defects, and context size.
- risk if applied as proposed: FN↑ from empty/wrong genre selection; context exhaustion from broad trigger spans

### JudgementRules.F2: Remove three tokenizer-contract entries from judgement output
- verdict: ACCEPT
- counter-evidence: none. All three say “counting definition,” prescribe no rewrite, and carry severity off (`JudgementRules.md:F2`; entries #54-56).
- risk if applied as proposed: none

### JudgementRules.F4: Merge remainder rules and require an uncovered trigger
- verdict: ACCEPT-MODIFIED
- counter-evidence: The audit proves narrow duplicates—word-sense pair, topic-cohesion pair, and staccato/epigram questions whose mechanical core already fired (`JudgementRules.md:F4` and full table). It does not prove that all remainders are duplicates: the rule files explicitly preserve semantic residuals that regexes cannot settle, such as paraphrased anaphora (`ai-tells-agentic.yml:504-526`).
- modification: Merge only named duplicate pairs and delete a remainder only when its question adds no decision beyond the upstream finding. Do not require a mechanical trigger for standalone semantic checks.
- risk if applied as proposed: FN↑ for nonliteral/paraphrased defects

### JudgementRules.F6: Strip exceptions from judgement rules
- verdict: REJECT
- counter-evidence: Exceptions are operational even though judgement rules do not emit suppressible findings. The audit’s own ten-rule probe judged Black’s “vastly improves” as non-defective because it is a testimonial quotation (`JudgementRules.md:Ten-rule document probe`). Removing `quotation` loses the reason two reviewers should reach the same answer. `review-docs/SKILL.md:76-91` also explicitly tells the reviewer that each judgement entry carries exceptions.
- modification: Retain the semantics. If schema clarity is needed, rename them to typed `review_context_exclusions` only after the review result can record the applied exclusion.
- risk if applied as proposed: FP↑ on quotations, code spans, and genre-specific legitimate uses

### JudgementRules.F7a: Mechanise textbook connector runs
- verdict: ACCEPT
- counter-evidence: The exact adjacency regex `(?is)^(moreover|furthermore|additionally|consequently)…[.!?]\s+(moreover|furthermore|additionally|consequently)\b` produced 0 hits across all 11 human documents. No human quotes exist. The finite opener set and adjacency relation are mechanical (`ai-tells-agentic.yml:2007-2032`).
- risk if applied as proposed: none at advisory severity
- probe count: 0 human hits; three quotes unavailable because there were no hits.

### JudgementRules.F7b: Mechanise anaphora abuse
- verdict: REJECT
- counter-evidence: An exact first-two-token run metric over three consecutive sentences produced 0 human hits, but the rule’s note says the exact mechanical form is already owned by `ai-tells.StackedAnaphora`; this judgement entry exists for paraphrased openers (`ai-tells-agentic.yml:504-526`). Regexing the exact form duplicates coverage, while regexing paraphrases cannot preserve subject/verb identity.
- risk if applied as proposed: duplicate findings or FN↑ if the semantic remainder is removed
- probe count: 0 human hits; three quotes unavailable.

### JudgementRules.F7c: Mechanise heading echo
- verdict: REJECT
- counter-evidence: A metric requiring at least half of two or more non-stopword heading terms in the first sentence produced 39 human hits. Examples include “User Guide” → “This guide is intended…” (`ripgrep-guide-2021.md:3-5`), “Recursive search” → “In the previous section, we showed how to use ripgrep to search…” (`ripgrep-guide-2021.md:119-122`), and “Running tests” → “ripgrep is relatively well-tested…” (`ripgrep-readme-2021.md:412-413`). These introductions add audience, transition, and test-scope facts; lexical overlap is not semantic restatement.
- risk if applied as proposed: FP↑
- probe count: 39 human hits.

### JudgementRules.F7d: Mechanise concrete floor
- verdict: REJECT
- counter-evidence: The implied metric—flag an 8+ word prose block without a number/version, inline identifier, path, command opener, or dated event—produced 274 human candidates. Correct examples include ripgrep’s behavior overview (`ripgrep-readme-2021.md:3-6`), the warning that one benchmark is insufficient (`ripgrep-readme-2021.md:47-49`), and the feature-history paragraph (`ripgrep-readme-2021.md:130-133`). A finite anchor set measures typography, not whether a claim names a checkable particular.
- risk if applied as proposed: FP↑
- probe count: 274 human hits.

### JudgementRules.F7e: Mechanise long domain term without short form
- verdict: REJECT
- counter-evidence: A four-or-more Title-Case-word trigger lacking an immediate parenthesized alias produced six human hits, including “The Uncompromising Code Formatter” (`black-readme-2021.md:3`), “Google’s Assured Open Source Software” (`markdown-it-py-readme-2020.md:20`), and `BEGIN PGP SIGNED MESSAGE` inside a literal (`git-contributing-2021.md:355`). These are a tagline, external proper name, and code literal, not repeated project terms needing short forms. Detecting the actual condition requires term ownership and reuse count, not regex alone.
- risk if applied as proposed: FP↑
- probe count: 6 human hits.

### JudgementRules.F7f: Mechanise organization-approved domain nouns
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence: The implied metric is exact equality against a configured glossary/API/schema. No such glossary input accompanies the 11 human corpus documents, so the probe count is N/A rather than zero; an empty glossary would classify every candidate noun as unapproved. `ste-words.yml:359-382` itself says this is only partially mechanisable once a glossary exists.
- modification: Implement only as an opt-in vocabulary check when a project supplies an authoritative glossary path; otherwise keep the judgement question or exclude it.
- risk if applied as proposed: FP↑ or a silently inert rule
- probe count: N/A; no defensible quoted hits without an authority set.

### JudgementRules.metadata: Add `family`, `trigger_rules`, `requires_context`, and rule-level `recommended_for`
- verdict: ACCEPT-MODIFIED
- counter-evidence: `scope` already exists per rule (`model.py:145`), and `recommended_for` already exists at category level with an explicit statement that the skill reads it (`model.py:263-267`). Rule-level duplication creates two genre authorities. `family` is unnecessary after the proposed duplicate merges. `trigger_rules` is useful only for genuine remainders; making it mandatory would suppress standalone judgement checks. A boolean `requires_context` cannot say whether the missing input is audience, repository HEAD, glossary, or verified references.
- modification: Normalize category-level genre values and keep `recommended_for` there. Add optional `trigger_rules` only to true remainder rules. Replace boolean `requires_context` with typed `required_inputs` values such as `audience`, `repo_head`, `glossary`, and `verified_refs`. Do not add `family` unless measured duplicate families remain after merging.
- risk if applied as proposed: metadata drift and FN↑ from incomplete trigger/context declarations

### TellsCoverage.F1: Add cross-sentence definitional-negation detection
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence: The report measured 0 human and 0 AI corpus matches, so observed recall is zero (`TellsCoverage.md:F1`). Several probes are legitimate technical contrasts, such as “The worker doesn’t retry. The worker does fail fast,” and the proposed `factual-correction` exception leaves the central semantic decision unresolved.
- modification: Do not add this form to always-loaded steering. Require positive corpus examples and human false-positive probes before a mechanical rule.
- risk if applied as proposed: FP↑

### TellsCoverage.F2: Add a chat-style sign-off closer
- verdict: ACCEPT
- counter-evidence: The bounded form has one AI hit, “Happy migrating!”, and zero human hits (`TellsCoverage.md:F2`). It is better kept mechanical and out of the writing skill.
- risk if applied as proposed: none at advisory/relaxed-excluded disposition

### TellsCoverage.F3: Add a second-person “Whether … or …” choice-frame
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence: Evidence is one AI hit and zero human hits (`TellsCoverage.md:F3`), while the report concedes the structure can be legitimate instructional copy. One model occurrence cannot distinguish ceremony from a load-bearing two-case instruction.
- modification: Keep it out of steering; retain only as advisory if a larger held-out corpus preserves the separation and the documented-choice exception is machine-applicable.
- risk if applied as proposed: FP↑

## Missed by the audit
- **Genre vocabulary is already inconsistent.** Deterministic category selection cannot precede normalization: `consumer`, `consumer-docs`, and `readme` select 0, 38, and 28 judgement rules respectively in the current catalogue.
- **F1 and F2 overlap.** Their line replacements touch the same gate prose, so their standalone word deltas cannot be added and their final wording can conflict.
- **Static token savings hide dynamic context cost.** F6 saves 61 skill words but asks for an unbounded claim table and per-paragraph counts; on the 418-word parsed target it already creates 21 claim rows.
- **The mechanisation proposal contradicts rule provenance.** Heading echo says paraphrase defeats string comparison; anaphora says the exact form is already mechanised; organization approval says a project glossary is required (`ai-tells-agentic.yml:387-410,504-526`; `ste-words.yml:359-382`).

## Systemic concerns
- The eval cannot support causal claims about individual steering sentences: it has one generation per cell, one model, no repeats, no variance, and bundles multiple instruction changes (`evals/REPORT.md:123-128`).
- The corpora answer prevalence, not usefulness. A zero-human-hit regex may still duplicate an existing rule or have zero AI recall, as the anaphora and cross-sentence proposals show.
- Paragraph-level joins are required for finding/label comparisons because engine locations use the paragraph’s first line; none of the counts above rely on line-level joins.
- Word deltas use one consistent token regex over exact cited replacement ranges. They are standalone deltas, not a composable final budget.

## Strongest counter
The old skill already delivered 96% of the measured density reduction from unguided to the proposed condition: $16.87-3.62=13.25$ points from current steering versus only $3.62-3.25=0.37$ further points from the rewrite (`evals/REPORT.md:37-45`). Deleting 253 words of unablated sentence controls and replacing targeted adversarial review with unbounded tables risks discarding the proven part to optimize the unproven part.

## Questions back
- What canonical genre enum should category `recommended_for` use: `consumer`, `consumer-docs`, or surface names such as `readme`?
- What maximum selected-question count and evidence-token budget must the staged reviewer obey for a 3,000-word document?
- Which repeated-generation A/B result would be sufficient to attribute semicolon and omitted-`that` regressions to the compression instruction rather than another bundled rule?