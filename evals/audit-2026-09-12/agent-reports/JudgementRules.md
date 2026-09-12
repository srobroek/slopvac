# Summary
Checked all 67 `kind: judgement` entries from `slopvac rules --judgement --format json`, their examples/fixes/exceptions, and review-docs step 4.
The strongest defects are (1) the skill says “each” but supplies no candidate-selection algorithm, (2) several entries are tokenizer/config contracts masquerading as judgement rules, and (3) several pairs duplicate either one another or an existing pattern rule.
A 10-rule two-document probe shows useful decisions for concrete, citation, heading, structure, and register questions, but most document-scope questions are not meaningfully decidable without project context.

## Findings
### F1: Step 4 is not executable at stated scale
- surface: `packages/slopvac/skills/review-docs/SKILL.md:76-91`
- kind: architecture
- evidence: The procedure says “Use each entry's `rule_id`” and “Filter by `scope`,” i.e. 67 questions for every paragraph. There is no rule-selection, deduplication, trigger, or result schema. A Python probe over the two supplied documents counted 67 rules × 38 non-empty Markdown blocks in the AI README and 67 × 80 in Black (7,906 question opportunities before sentence/document scopes are considered).
- proposal: Make selection a deterministic staged procedure: (a) load only categories whose `recommended_for` contains the selected genre; (b) run sentence/paragraph rules only on spans implicated by gate findings or explicit structural candidates; (c) run each document rule once; (d) cluster duplicates by a required `family`/`supersedes` metadata field and ask one representative; (e) stop after one answer per family/span. Add `trigger_rules` (pattern/metric IDs), `recommended_for` at rule level, `family`, and `requires_context` fields; return `{rule_id, span, answer, evidence, verdict}`.
- expected effect: FP↓ and review cost↓; both corpora checked.
- confidence: high

### F2: Counting definitions are dead judgement entries
- surface: `ste-punctuation.parenthetical-counts-as-one-word`, `ste-punctuation.hyphenated-word-counts-as-one-word`, `ste-punctuation.elements-counting-as-one-word`
- kind: defect
- evidence: Their questions explicitly say “This is a counting definition, not a prohibition” and fixes say “No rewrite. Implement ... tokenizer”; all three have severity `off`, identical bad/good examples, and empty exceptions. They cannot produce a writer decision. Python probe: `re.findall(r'(?<!\\w)[A-Za-z]+(?!\\w)', 'Set timeout to 30 s for HTTP client')` returns 7 (`Set`, `timeout`, `to`, `s`, `for`, `HTTP`, `client`) while a specification-aware tokenizer must bind `30 s` as one element and count it as 1, demonstrating an implementation contract, not prose review.
- proposal: Remove from the judgement catalogue and represent as versioned tokenizer/metrics metadata or code-level contract; retain STE provenance there. Do not expose to step 4.
- expected effect: correctness and review cost↓.
- confidence: high

### F3: “Every reference” is not reviewable without provenance
- surface: `ai-tells-content-shape.fabricated-citations-remainder`
- kind: scope/architecture
- evidence: Question: “For each reference ... did you fetch it yourself”; document scope cannot know what the reviewer fetched. In the AI document, line 54 says “Most teams find that somewhere in the 0.85–0.95 range tends to work reasonably well,” with no citation; in Black line 29 links to the Playground and line 47 gives a Git URL. The same document can be judged differently based only on reviewer browsing history.
- proposal: Add citation spans and an explicit review input (`verified_refs`) or make this a checklist requiring recorded URL/status evidence; keep vague-attribution as the prose question and merge the rest into a verification gate.
- expected effect: FP↓/correctness.
- confidence: high

### F4: Remainder rules duplicate pattern rules and each other
- surface: contrastive-inversion-remainder vs `ai-tells-structure.contrastive-inversion-frames`; staccato remainder vs `ai-tells-structure.staccato-negative-parallel-frames` and `ai-tells-structure.emphasis-paragraph-metric`; `vague-attribution-remainder` vs fabricated-citations remainder; `word-sense-incorrect` vs `word-used-outside-permitted-sense`.
- kind: duplicate
- evidence: Provenance itself calls these “judgement remainder”; the staccato example is literally `Fast. Deterministic. Auditable.`, a fixed fragment shape already covered by the named frame/metric. On the AI document lines 9-13, five bold-colon bullets are mechanically identifiable as parallel formatting; asking a second “does each add a fact?” question produces no new lexical evidence. For sense rules, both questions differ only in “controlled” versus “vocabulary” wording and their examples test the same replacement operation.
- proposal: Require every remainder to name an uncovered condition and a trigger. Merge word-sense rules; merge vague attribution/fabricated citation into separate `named` and `verified` stages; delete staccato remainder where the existing shape/metric already fired, or retain only a genuinely non-identical paraphrase family.
- expected effect: FP↓ and review cost↓.
- confidence: high

### F5: Fixes are usually actionable, but a few prescribe impossible or context-losing operations
- surface: `ai-tells-structure.summary-closer-remainder`, `ai-tells-content-shape.over-writing-remainder`, `ste-words.domain-verb-category-membership`, `ai-tells-content-shape.vaporware-description`
- kind: defect
- evidence: Summary closer says “Delete the section” even when the final section can contain a unique operational fact; over-writing says “Cut to the behaviour; move the decision to an ADR” without naming which sentence is behaviour; domain-verb fix says “register” a term despite no supplied category store; vaporware’s long ordered fix requires code-at-HEAD and metadata decisions unavailable from prose alone. In AI lines 95-100, Roadmap has real future-state information, so deleting the whole section would lose user-relevant facts.
- proposal: Change fixes to conditional operations with evidence: “delete only the repeated closing sentences; retain unique facts”; “identify the clause with no reader action”; “replace with vocabulary verb unless project glossary explicitly registers it”; “move unreleased behavior to a status/roadmap field.”
- expected effect: correctness and FP↓.
- confidence: high

### F6: Exceptions are dead metadata for judgement rules
- surface: all 67 judgement entries’ `exceptions` field and SKILL.md:61-63
- kind: architecture
- evidence: The rules loader returns exceptions (e.g. `quotation`, `code-span`, `landing-page`) but judgement rules never fire; step 4 asks a question rather than emitting a finding to suppress. A Python probe of the JSON counted 27 rules with non-empty exceptions, yet no judgement result can carry an exception annotation. Thus `<!-- slopvac-allow ... -->` can only affect pattern findings, not these questions.
- proposal: Strip `exceptions`/`allowlist` from judgement metadata unless the engine will emit structured judgement findings; instead add `review_context_exclusions` (quotation/code/span) to selection. Keep exceptions only in the pattern schema.
- expected effect: correctness and maintenance↓.
- confidence: high

### F7: Mechanizable questions should be patterns/metrics, not reviewer prompts
- surface: `ai-tells-content-shape.textbook-connector-runs`, `ai-tells-structure.anaphora-abuse`, `ai-tells-structure.heading-echo`, `orwell.concrete-floor`, `ste-nouns.long-domain-term-without-short-form`, `ste-words.domain-noun-not-organization-approved`
- kind: architecture
- evidence: `textbook-connector-runs` is a fixed adjacency regex: `(?im)^(?:moreover|furthermore|additionally|consequently)\\b.*\\n(?:... )`; on `Moreover, A. Furthermore, B.` Python `re.findall` returns both openings and proves the trigger without semantic review. `anaphora-abuse` specifies three consecutive same subject-verb openings; `heading-echo` compares heading and first sentence; `concrete-floor` asks for a finite anchor set; long-domain-term asks >3 words plus first-use abbreviation; organization-approved asks exact glossary equality. These have fixed lexical/structural triggers or become deterministic once project glossary metadata exists.
- proposal: Move connector/anaphora/heading/anchor/term-length/glossary checks into pattern/metric rules; preserve a narrow remainder only for semantic exceptions. Add `glossary.path`, `anchors`, and `first_use` metadata where needed.
- expected effect: FN↓ and reviewer time↓.
- confidence: high

## Ten-rule document probe
Applied ten questions to the exact supplied documents. “Decision” means a defensible yes/no supported by a quoted line; “—” means the question did not have a stable decision on that document.

| rule | AI evidence (line) / decision | Human evidence (line) / decision | result |
|---|---|---|---|
| `ai-tells-structure.heading-echo` | `## Installation` then “pip install fluxcache” (15-19): no echo | `## Installation and usage` then `### Installation` (38-42): “Black can be installed...” adds command/version facts; no echo | useful, different answers |
| `ai-tells-structure.false-suspense-remainder` | “Need more control?” (56) immediately states hook details (58): no withheld point | “Further information can be found in our docs” (65) gives links, but announces no hidden point: no | useful, both defensible |
| `ai-tells-structure.anaphora-abuse` | bullets 9-13 share adjective-noun shape, not same subject-verb; no | lines 134-140 repeat “The following...” but not same subject-verb; no | stable negative control |
| `ai-tells-structure.analogy-stack-authority` | “Think of it like a librarian...” (89) is one analogy, not stack; no | “They took after its initial author” (103) is a single metaphor, no named-company stack; no | same answer; weak candidate |
| `ai-tells-structure.absolute-assertion-remainder` | “fluxcache will recognize semantic similarity” (36) is defeasible but no single counterexample available from text; yes, counterexample required externally | “Blackened code looks the same regardless...” (24) has future/edge-case caveat elsewhere; yes, can name counterexample from lines 103-111 | stable yes but requires repo/domain evidence |
| `ai-tells-register.intensifier-tics-remainder` | “arguably most important” and “work reasonably well” (54) have no measurement supporting importance; yes | “This vastly improves...” is testimonial quote (161), exception/quotation; no | useful, different answers |
| `ai-tells-register.over-formatting-reflex` | table lines 74-77 has real columns and independent rows; no | badge/link blocks lines 6-14 are parallel independent metadata; no | same negative; question needs table semantics |
| `ai-tells-content-shape.vaporware-description` | Roadmap “coming soon!” (97) explicitly not at HEAD; yes | “planned changes” (92) is a documented future statement, but no HEAD check available; — | useful only with code verification |
| `orwell.concrete-floor` | “minimal dependencies, no vendor lock-in” (13) has no number/path/command in that paragraph; yes | “Black ... Python 3.6.2+” (42) has a version and pip command; no | useful, different answers |
| `prose-discipline.competing-actor-terms` | “Users” (5), “teams” (54), “applications” (3) are not obviously same actor; — | “user” (19), “reader” (25), “author” (103) have distinct roles; — | no stable decision; needs defined actor inventory |

A no-decision or same-answer result is not proof that the rule is wrong, but it is evidence the rule needs a trigger/context input. The ten-probe evidence is deliberately limited to these two documents and does not claim corpus prevalence.

## Full 67-rule table
`Y` means the question is decidable by a second reviewer with the same passage and stated project context; `N` means it requires unavailable/unstated context or invites taste. “Scope” is whether the declared span contains the information the question asks for.

| # | rule | dec? | scope? | duplicate-of | verdict / one-line reason |
|---:|---|:---:|:---:|---|---|
|1|ai-tells-structure.contrastive-inversion-remainder|N|Y|contrastive-inversion-frames|merge; alternative-holder test needs explicit citation/context|
|2|ai-tells-structure.staccato-negative-parallel-remainder|Y|Y|staccato-negative-parallel-frames; emphasis-paragraph-metric|remove; fixed fragment run already decides shape|
|3|ai-tells-structure.tricolon-abuse-remainder|N|Y|tricolon-abuse-core|keep/rewrite; distinct-substance test is semantic but document scope fits|
|4|ai-tells-structure.false-suspense-remainder|Y|Y|false-suspense-frames|keep; withholding is context-light and examples fit|
|5|ai-tells-structure.meta-narration-remainder|Y|Y|meta-narration-frames; document-preamble|merge; sentence navigation is same defect at narrower span|
|6|ai-tells-structure.heading-echo|Y|Y|self-reference; document-preamble|mechanize; heading/first-sentence comparison is structural|
|7|ai-tells-structure.summary-closer-remainder|N|Y|summary-closer-frames|rewrite; final section may add facts and cannot always be deleted|
|8|ai-tells-structure.listicle-in-a-trench-coat|Y|N|sequencing-markers/list-introductions|rewrite; paragraph scope cannot see all consecutive paragraphs|
|9|ai-tells-structure.anaphora-abuse|Y|Y|stacked-anaphora|mechanize; same opener and object slots are structural|
|10|ai-tells-structure.analogy-stack-authority|N|Y|none|keep advisory; causal connection needs domain knowledge|
|11|ai-tells-structure.invented-concept-label|N|N|none|rewrite; “established term” and document-wide definition need glossary/source context|
|12|ai-tells-structure.cataphoric-lead-in-remainder|N|Y|cataphoric-lead-in-core|keep/rewrite; usefulness of count depends on reader task|
|13|ai-tells-structure.hollow-acknowledgment|N|Y|hollow-acknowledgment pattern|keep advisory; action/measurement/pointer can be checked but “handled” needs document context|
|14|ai-tells-structure.absolute-assertion-remainder|Y|Y|absolute-assertion-core|keep; one counterexample is a concrete decision procedure|
|15|ai-tells-structure.think-of-it-as-remainder|Y|Y|think-of-it-as-core|merge; mechanism-presence is directly inspectable in paragraph|
|16|ai-tells-structure.false-range|N|Y|none|keep advisory; endpoint ordering is domain-semantic|
|17|ai-tells-structure.vague-attribution-remainder|Y|Y|vague-attribution-core|keep; named/checkable source test is clear|
|18|ai-tells-structure.audience-straddle-remainder|N|N|audience-straddle-core|rewrite; cross-section knowledge needs document context, not one generic question|
|19|ai-tells-register.faux-candor-remainder|N|Y|faux-candor-core|keep advisory; “cost” is rhetorical and needs author context|
|20|ai-tells-register.intensifier-tics-remainder|Y|Y|intensifier-tics-core|keep; support in passage is a defendable evidence test|
|21|ai-tells-register.corporate-analytic-filler-remainder|Y|Y|corporate-analytic-filler-core|keep; fact/measurement/consequence test is concrete|
|22|ai-tells-register.over-formatting-reflex|N|Y|inline-header-list; prose-block|keep/rewrite; table independence is semantic but document scope fits|
|23|ai-tells-register.hedged-symmetry|N|Y|false-balance pattern; hedge-stack|merge/rewrite; counter-claim holder requires external evidence|
|24|ai-tells-register.figurative-verb-verdict-remainder|N|Y|figurative-verb-verdict-core|keep advisory; whether metaphor is a verdict depends on interpretation/evidence|
|25|ai-tells-register.urgency-inflation-remainder|Y|Y|urgency-inflation-core|keep; consequence-present test is actionable|
|26|ai-tells-register.organic-consequence-remainder|N|Y|organic-consequence-core|keep advisory; actual chooser is external provenance|
|27|ai-tells-register.false-agency-remainder|N|Y|false-agency|merge/rewrite; “can act” depends on ontology and domain|
|28|ai-tells-register.anthropomorphised-justification-remainder|N|Y|anthropomorphised-justification-core|keep advisory; checkability/value distinction is semantic|
|29|ai-tells-formatting.table-wrapping-one-sentence|Y|Y|prose-block inverse|mechanize; table rows/cell variance are parseable, with semantic exception|
|30|ai-tells-content-shape.fabricated-citations-remainder|N|Y|vague-attribution-remainder|rewrite; fetch provenance is not in document scope|
|31|ai-tells-content-shape.vaporware-description|N|N|status-language|keep as verification gate, not prose judgement; requires HEAD/code access|
|32|ai-tells-content-shape.elegant-variation|N|Y|competing-actor-terms|merge; coreference cannot be decided from names alone|
|33|ai-tells-content-shape.one-point-dilution|N|Y|think-of-it-as-remainder|keep advisory; restatement requires semantic equivalence|
|34|ai-tells-content-shape.padded-symmetry|N|N|uniform-paragraph-mass|rewrite; “exists to match length” is author-intent, FAQ applicability is document/task context|
|35|ai-tells-content-shape.textbook-connector-runs|Y|Y|durable-vocabulary-habits|mechanize; exact consecutive openings are regex-decidable|
|36|ai-tells-content-shape.over-writing-remainder|N|Y|prose-scope|merge; reader-action test overlaps scope and is under-specified|
|37|ai-tells-content-shape.unasked-for-rationale|N|Y|prose-scope implementation-leak|keep/rewrite; legitimate-rationale exceptions need genre/user/context metadata|
|38|ai-tells-content-shape.epigram-closer-remainder|N|Y|prose-scope.epigram|merge; existing pattern finds shape, remainder repeats “adds fact” test|
|39|orwell.concrete-floor|Y|N|none|rewrite/mechanize anchors; declared prose scope conflicts with paragraph question|
|40|prose-discipline.competing-actor-terms|N|Y|elegant-variation|merge; actor identity requires ontology/glossary|
|41|prose-discipline.marketing-register|N|Y|unsupported-evaluative|merge; same evidence test should extend pattern rule rather than duplicate|
|42|prose-discipline.overloaded-sentence|Y|Y|sentence-not-short-or-clear|merge; both ask one idea/topic and split boundary|
|43|prose-discipline.hedged-into-uselessness|N|Y|hedge-stack; hedged-symmetry|keep document-level; claim ratio is useful but needs load-bearing-claim extraction|
|44|prose-discipline.bare-quantifier-with-figure-available|N|Y|vague-quantifier|keep/rewrite; figure availability requires whole-document search and measurement context|
|45|ste-descriptive.information-not-gradual|N|Y|sentence-not-short-or-clear|keep advisory; forward-reference/idea ordering is semantic|
|46|ste-descriptive.missing-key-word-structure|Y|Y|inconsistent-term-for-same-thing|merge/mechanize with glossary; key-word carryover is lexical once key terms known|
|47|ste-descriptive.paragraph-without-related-information|N|Y|paragraph-has-multiple-topics|merge; topic cohesion and unrelated sentence overlap substantially|
|48|ste-descriptive.paragraph-has-multiple-topics|Y|Y|paragraph-without-related-information|keep one canonical split test; current pair duplicates topic cohesion|
|49|ste-nouns.long-domain-term-without-short-form|Y|Y|multiword-noun-too-long; hyphen-group-too-long|merge/mechanize length/first-use halves; only immovable-name exception remains judgement|
|50|ste-practices.word-swap-insufficient|Y|Y|approved-word-substitution|keep as substitution fallback; grammaticality/meaning test is a real remainder|
|51|ste-practices.word-sense-incorrect|N|Y|ste-words.word-used-outside-permitted-sense|merge; duplicate question and operation|
|52|ste-practices.ambiguous-preposition-with|N|Y|none|keep advisory; ambiguity is reader-dependent but scope is correct|
|53|ste-punctuation.parentheses-misuse|Y|Y|none|keep; seven-purpose whitelist gives a usable decision|
|54|ste-punctuation.parenthetical-counts-as-one-word|Y|Y|tokenizer contract|remove from judgement; off severity and no-rewrite fix|
|55|ste-punctuation.hyphenated-word-counts-as-one-word|Y|Y|tokenizer contract|remove from judgement; off severity and no-rewrite fix|
|56|ste-punctuation.elements-counting-as-one-word|Y|Y|tokenizer contract|remove from judgement; off severity and no-rewrite fix|
|57|ste-safety.risk-level-word-missing-or-wrong|N|Y|risk-level pattern half|keep as safety verification; consequence classification needs operational context|
|58|ste-sentences.sentence-not-short-or-clear|Y|Y|overloaded-sentence|merge; duplicate one-topic/split operation|
|59|ste-sentences.missing-connector-between-related-sentences|N|Y|none|keep advisory; relation is semantic and paragraph scope fits|
|60|ste-verbs.past-participle-not-adjectival|Y|Y|complex-tense; passive-voice|merge/rewrite; parser can classify most cases and existing rules cover verb half|
|61|ste-verbs.gerund-outside-noun-use|Y|Y|complex-tense|keep parser-backed; noun/modifier vs clause-action is syntactic, not regex|
|62|ste-words.word-used-outside-permitted-sense|N|Y|word-sense-incorrect|merge; same vocabulary-sense question|
|63|ste-words.domain-noun-category-membership|N|Y|unapproved-word-not-a-domain-noun|merge; pair asks same domain-noun legitimacy with different framing|
|64|ste-words.unapproved-word-not-a-domain-noun|N|Y|domain-noun-category-membership|merge; needs project category configuration|
|65|ste-words.domain-noun-not-organization-approved|Y|Y|none|mechanize with project glossary/API/schema path|
|66|ste-words.domain-noun-too-long-or-unclear|N|Y|multiword-noun-too-long|merge; word-count half is duplicate, clarity remains subjective|
|67|ste-words.domain-verb-category-membership|N|Y|none|keep advisory with glossary/context; vocabulary-only possibility is semantic|

## Decommission candidates
- Remove the three tokenizer-contract rules (#54-56) from judgement output; their own metadata says no rewrite and severity `off`.
- Merge duplicate pairs: overloaded-sentence/sentence-not-short-or-clear; word-sense-incorrect/word-used-outside-permitted-sense; domain-noun-category-membership/unapproved-word-not-a-domain-noun; paragraph-without-related-information/paragraph-has-multiple-topics.
- Remove or gate remainder questions when the upstream pattern already fired: staccato remainder, epigram closer, and narrow contrastive inversion.
- Demote/convert broad intent questions (`padded-symmetry`, `faux-candor`, `audience-straddle`) to optional checklist items requiring user/task context, rather than pretending they are decidable rule checks.

## Checked and fine
- Rule IDs are qualified and `slopvac explain <category.rule>` is the correct invocation documented by the skill.
- Scope labels generally match the information needed; the notable mismatch is `orwell.concrete-floor` (`prose` scope, paragraph question), plus document rules whose required external context is absent.
- Fixes for heading echo, false suspense, intensifier support, concrete anchors, and parenthetical purposes are concrete writer operations.
- The category-level `recommended_for` metadata is useful but insufficient: it must be lifted or referenced per rule for executable selection.
- Judgement examples mostly distinguish a concrete rewrite from a defect, but tokenizer definitions intentionally use identical bad/good examples and should not be loaded as review questions.
