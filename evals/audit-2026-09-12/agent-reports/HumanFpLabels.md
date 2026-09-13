# Human false-positive labels

## Summary
- Audited 352 human findings (95 rules) from 2,132 total human findings, plus 174 samples (48 rules) from 984 findings in already-gated prose.
- Human sample labels: 101 TP, 178 FP-correct-prose, 51 FP-not-prose, 22 FP-genre (71% FP overall); slopvacced samples: 26 TP and 148 FP (85% FP overall).
- The three material actions are: demote/decommission broad normal-tier rules with extrapolated FP counts, mask raw/code/table/heading scopes before matching, and keep sentence-length/procedural rules where gated authors still leave real warnings.
- Error-severity human findings are separately listed below; sampled error FPs include durable-vocabulary, Unicode dash, prose-block, exclusive-language, and phrasal-verb paths.

## Findings
### F1: Error-severity rules fail on correct human prose
- surface: human corpus; error-severity rules
- kind: fp-risk
- evidence: `ai-tells-content-shape.durable-vocabulary-habits` (error, 15 findings) matched “## Supported Features & Best–Practices” at `requests-readme-2020.md:38` and image alt text “![Features](...)” at `rich-readme-2020.md:34`; all 5 sampled rows were FP (3 correct prose, 2 not-prose). `prose-format.no-unicode-dash` (error, 6) matched ordinary typography in “There’s no need ... data — but nowadays...” at `requests-readme-2020.md:20`; all 5 sampled rows were FP. `prose-format.prose-block` (error, 13) sampled 4/5 FP, including “As you can guess from the names, these files implement the RDB and AOF persistence for Redis.” at `redis-readme-2021.md:380`. `prose-inclusive.exclusive` (error, 13) sampled 5/5 FP on established `blacklist`/`whitelist`/`master` terminology. `prose-discipline.phrasal-verb` (error, 5) sampled 4/5 FP because `unpacks` occurs in API/code prose at `annotated-types-readme-2022.md:247`.
- evidence probe: `re.search(r"[—–]", "There’s no need to add data — but nowadays...")` returned a match; this is a real character match but not evidence of defective prose. The documented command-prompt regex returned a match on a code-fence line `$ sudo yum install ripgrep`, confirming that raw matching sees non-prose.
- proposal: Make error rules fail closed on documented exceptions and genre/scope boundaries: route headings, image alt text, code spans/fences, tables, established API terminology, and quoted text out before enforcement; demote broad style/house-choice rules from error to advisory until masks exist.
- expected effect: FP↓ and gate correctness on human corpus; especially reduces costly error FPs.
- confidence: high

### F2: Broad warning rules do not separate human prose at normal profile
- surface: `ste-verbs.passive-voice`, `prose-craft.first-person-plural`, `prose-craft.future-tense`, `prose-craft.command-prompt`, `ste-sentences.omitted-word-or-contraction`, `ste-descriptive.sentence-too-long-descriptive`
- kind: fp-risk
- evidence: Baseline density is 11.27/1,000 for `ste-verbs.passive-voice` and 5.42/1,000 for `prose-craft.first-person-plural`. Samples show acceptable statements such as “The first three bytes of a file will be read ...” (`ripgrep-guide-2021.md:647`), “For example, let’s say we wanted to find all occurrences...” (`ripgrep-guide-2021.md:501`), and “If you’re an Ubuntu Cosmic ... user, ripgrep is available...” (`ripgrep-readme-2021.md:285`). `prose-craft.command-prompt` sampled 5/5 non-prose code lines. The measured human sample is 101 TP versus 251 FP overall.
- evidence probe: `re.search(r"\b(?:we|we[’']re|let[’']s|you[’']re|doesn[’']t|don[’']t)\b", "For example, let’s say we wanted to find all occurrences")` returned a match although the sentence is readable instructional prose; `re.search(r"\b(?:will|would|shall)\b", "If you’re an Ubuntu Cosmic user, ripgrep is available")` returned `None`, showing that a finding needs rule-context interpretation.
- proposal: Treat first-person plural and future tense as genre-sensitive advisory signals; preserve contractions in consumer/readme and contributor genres; retain passive only when the actor is unknown/irrelevant; enforce command-prompt only within command examples after raw-scope masking.
- expected effect: FP↓ on human corpus; warning density becomes more discriminative without suppressing genuine sentence-length defects.
- confidence: high

### F3: Raw/structural scope masking is the largest engine defect
- surface: rules with FP-not-prose >= 30% of sampled rows
- kind: masking defect
- evidence: 16 rules cross the required FP-not-prose threshold. Examples include heading-only hits (`ai-tells-formatting.bold-spray`, `ai-tells-formatting.title-case-heading`, `prose-craft.gerund-heading`), table/code hits (`ste-punctuation.hyphen-group-too-long`, `ste-punctuation.semicolon-used`, `prose-discipline.run-on`), and markup/link hits (`prose-craft.command-prompt`, `prose-craft.link-text`). `ste-practices.latin-abbreviation` matched ordinary `item` in “The end of a vertical-list item.” at `metrics.md:163`, outside the intended Latin vocabulary. Human sample counts are 51 FP-not-prose of 352.
- evidence probe: `re.search(r"\b(?:e\.g\.|i\.e\.|etc\.)\b", "The end of a vertical-list item.", re.I)` returned `None`, whereas the finding matched `item`; `re.search(r"(?m)^#{1,6}\s", "## Supported Features & Best–Practices")` returned a heading match before prose rules run.
- proposal: Add one shared preprocessing boundary tagging headings, tables, fenced/indented code, inline code, URLs, image/link destinations, and quoted strings; enforce each rule scope against those tags. Correct the Latin-abbreviation matcher/allowlist after the boundary.
- expected effect: FP↓ and correctness; reduces masking-induced false positives across many rules at once.
- confidence: high

### F4: Gated prose retains real sentence-shape warnings but rejects many tell/style warnings
- surface: slopvacced corpus (22 already-gated documents, 984 findings)
- kind: fp-risk
- evidence: In 174 labeled gated samples, only 26 were TP. High-TP rules are `prose-craft.sentence-length` (5/5 TP; 27 findings), `ste-descriptive.paragraph-too-many-sentences` (2/2 TP), `ste-descriptive.sentence-too-long-descriptive` (3/5 TP; 118 findings), `ste-procedural.instruction-not-imperative` (5/5 TP; 8 findings), and `ste-procedural.multiple-instructions-per-sentence` (4/5 TP; 20 findings). Conversely, 5/5 samples were FP for `ai-tells-structure.cataphoric-lead-in-core`, `ai-tells-structure.emphasis-paragraph-metric`, `ai-tells-structure.tricolon-abuse-core`, and `prose-agency.anthropomorphism`; “Four steps are human gates, and three of them are unconditional:” (`agentic-scaffold__docs__architecture.md:118`) is ordinary structured documentation.
- evidence probe: `re.search(r"\b(?:four|six|two) (?:steps|kinds|things)\b", "Four steps are human gates, and three of them are unconditional:")` returned a match; the explicit list lead-in is not itself an AI tell. A 25-character-run probe returned a match on the long `repomix` sentence, consistent with high-TP sentence-length samples.
- proposal: Keep and possibly strengthen sentence/paragraph shape rules in long-form technical docs; demote or genre-gate tell rules whose gated samples are acceptable lists, headings, or explanatory frames. Use slopvacced prose as an acceptance control.
- expected effect: FP↓ for tell/style rules; FN↓/quality↑ for sentence-shape rules that gated authors still leave unresolved.
- confidence: high

## Human per-rule table

| rule | severity | findings | sampled | TP | FP-correct-prose | FP-not-prose | FP-genre | FP rate | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `ai-tells-content-shape.durable-vocabulary-habits` | error | 15 | 5 | 0 | 3 | 2 | 0 | 100% | DEMOTE/DECOMMISSION, MASK ENGINE; extrap FP 15.0 |
| `ai-tells-content-shape.fake-specificity` | error | 2 | 2 | 0 | 2 | 0 | 0 | 100% | RETAIN; extrap FP 2.0 |
| `ai-tells-content-shape.superficial-ing-analysis` | error | 2 | 2 | 0 | 2 | 0 | 0 | 100% | RETAIN; extrap FP 2.0 |
| `ai-tells-formatting.bold-spray` | suggestion | 2 | 2 | 0 | 0 | 2 | 0 | 100% | MASK ENGINE; extrap FP 2.0 |
| `ai-tells-formatting.curly-quotes` | warning | 3 | 3 | 0 | 1 | 2 | 0 | 100% | MASK ENGINE; extrap FP 3.0 |
| `ai-tells-formatting.em-dash-density` | suggestion | 1 | 1 | 0 | 0 | 1 | 0 | 100% | MASK ENGINE; extrap FP 1.0 |
| `ai-tells-formatting.emoji-list-markers` | warning | 1 | 1 | 0 | 0 | 1 | 0 | 100% | MASK ENGINE; extrap FP 1.0 |
| `ai-tells-formatting.title-case-heading` | suggestion | 1 | 1 | 0 | 0 | 1 | 0 | 100% | MASK ENGINE; extrap FP 1.0 |
| `ai-tells-register.corporate-analytic-filler-core` | error | 2 | 2 | 2 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `ai-tells-register.uniform-paragraph-mass` | suggestion | 2 | 2 | 0 | 0 | 2 | 0 | 100% | MASK ENGINE; extrap FP 2.0 |
| `ai-tells-structure.cataphoric-lead-in-core` | suggestion | 4 | 4 | 0 | 4 | 0 | 0 | 100% | RETAIN; extrap FP 4.0 |
| `ai-tells-structure.emphasis-paragraph-metric` | suggestion | 80 | 5 | 0 | 2 | 3 | 0 | 100% | DEMOTE/DECOMMISSION, MASK ENGINE; extrap FP 80.0 |
| `ai-tells-structure.fragment-question-pivot` | suggestion | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `ai-tells-structure.rhetorical-question-transition` | suggestion | 3 | 3 | 0 | 0 | 3 | 0 | 100% | MASK ENGINE; extrap FP 3.0 |
| `ai-tells-structure.staccato-negative-parallel-frames` | suggestion | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `ai-tells-structure.summary-closer-frames` | error | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `ai-tells-structure.tricolon-abuse-core` | suggestion | 7 | 5 | 0 | 4 | 1 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 7.0 |
| `docs-discipline.history-narration` | warning | 6 | 5 | 0 | 0 | 0 | 5 | 100% | DEMOTE/DECOMMISSION; extrap FP 6.0 |
| `docs-discipline.internal-refs` | warning | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `docs-discipline.status-language` | warning | 6 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 6.0 |
| `orwell.compound-preposition` | error | 21 | 5 | 5 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `orwell.unsupported-evaluative` | error | 6 | 5 | 4 | 0 | 1 | 0 | 20% | RETAIN; extrap FP 1.2 |
| `prose-agency.anthropomorphism` | warning | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `prose-agency.false-agency` | warning | 12 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 12.0 |
| `prose-agency.unattributed-recommendation` | warning | 3 | 3 | 3 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-craft.ambiguity` | warning | 2 | 2 | 2 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-craft.command-prompt` | warning | 80 | 5 | 0 | 0 | 5 | 0 | 100% | DEMOTE/DECOMMISSION, MASK ENGINE; extrap FP 80.0 |
| `prose-craft.dead-opener` | warning | 22 | 5 | 4 | 1 | 0 | 0 | 20% | RETAIN; extrap FP 4.4 |
| `prose-craft.directional-ref` | warning | 8 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 8.0 |
| `prose-craft.first-person-plural` | warning | 115 | 5 | 0 | 0 | 0 | 5 | 100% | DEMOTE/DECOMMISSION; extrap FP 115.0 |
| `prose-craft.future-tense` | warning | 105 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 105.0 |
| `prose-craft.gerund-heading` | warning | 2 | 2 | 0 | 0 | 2 | 0 | 100% | MASK ENGINE; extrap FP 2.0 |
| `prose-craft.latinisms` | warning | 44 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 44.0 |
| `prose-craft.link-text` | warning | 6 | 5 | 0 | 0 | 5 | 0 | 100% | DEMOTE/DECOMMISSION, MASK ENGINE; extrap FP 6.0 |
| `prose-craft.negative-requirement` | warning | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `prose-craft.optional-plural` | warning | 2 | 2 | 2 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-craft.politeness` | warning | 26 | 5 | 0 | 0 | 1 | 4 | 100% | DEMOTE/DECOMMISSION; extrap FP 26.0 |
| `prose-craft.relative-date` | warning | 7 | 5 | 5 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-craft.self-reference` | warning | 6 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 6.0 |
| `prose-craft.sentence-length` | warning | 43 | 5 | 4 | 0 | 1 | 0 | 20% | RETAIN; extrap FP 8.6 |
| `prose-craft.spacing` | warning | 48 | 5 | 5 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-craft.unclear-antecedent` | warning | 42 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 42.0 |
| `prose-craft.versions` | warning | 7 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 7.0 |
| `prose-craft.wordiness` | warning | 32 | 5 | 5 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-discipline.bidirectional-hedge` | error | 2 | 2 | 1 | 1 | 0 | 0 | 50% | RETAIN; extrap FP 1.0 |
| `prose-discipline.frozen-verb` | error | 3 | 3 | 3 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-discipline.hedged-hedge` | error | 4 | 4 | 2 | 2 | 0 | 0 | 50% | RETAIN; extrap FP 2.0 |
| `prose-discipline.marketing-lexicon` | error | 1 | 1 | 1 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-discipline.phrasal-verb` | error | 5 | 5 | 1 | 0 | 4 | 0 | 80% | MASK ENGINE; extrap FP 4.0 |
| `prose-discipline.run-on` | error | 2 | 2 | 0 | 0 | 2 | 0 | 100% | MASK ENGINE; extrap FP 2.0 |
| `prose-discipline.term-rotation-signal` | suggestion | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `prose-format.no-unicode-dash` | error | 6 | 5 | 0 | 4 | 1 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 6.0 |
| `prose-format.prose-block` | error | 13 | 5 | 0 | 4 | 1 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 13.0 |
| `prose-inclusive.device-assumption` | error | 2 | 2 | 0 | 2 | 0 | 0 | 100% | RETAIN; extrap FP 2.0 |
| `prose-inclusive.exclusive` | error | 13 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 13.0 |
| `prose-inflation.apologizing` | error | 1 | 1 | 1 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-inflation.borderline-hype` | suggestion | 17 | 5 | 5 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-inflation.document-preamble` | error | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |
| `prose-inflation.hedge-stack` | error | 1 | 1 | 1 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-inflation.intensifier` | error | 16 | 5 | 4 | 1 | 0 | 0 | 20% | RETAIN; extrap FP 3.2 |
| `prose-inflation.nominalized-verb` | error | 2 | 2 | 2 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-inflation.slop-lexicon` | error | 9 | 5 | 4 | 0 | 1 | 0 | 20% | RETAIN; extrap FP 1.8 |
| `prose-inflation.vague-quantifier` | suggestion | 26 | 5 | 4 | 1 | 0 | 0 | 20% | RETAIN; extrap FP 5.2 |
| `prose-promotion.promotional-adjective-noun` | error | 2 | 2 | 2 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `prose-scope.rejected-alternative` | warning | 1 | 1 | 0 | 0 | 1 | 0 | 100% | MASK ENGINE; extrap FP 1.0 |
| `prose-scope.unrequested-reassurance` | warning | 5 | 5 | 1 | 3 | 1 | 0 | 80% | RETAIN; extrap FP 4.0 |
| `ste-descriptive.paragraph-too-many-sentences` | warning | 2 | 2 | 2 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `ste-descriptive.sentence-too-long-descriptive` | warning | 133 | 5 | 4 | 0 | 1 | 0 | 20% | RETAIN; extrap FP 26.6 |
| `ste-nouns.multiword-noun-too-long` | warning | 70 | 5 | 0 | 4 | 1 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 70.0 |
| `ste-practices.false-friend-term` | suggestion | 18 | 5 | 3 | 2 | 0 | 0 | 40% | RETAIN; extrap FP 7.2 |
| `ste-practices.gendered-or-exclusionary-language` | suggestion | 10 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 10.0 |
| `ste-practices.latin-abbreviation` | suggestion | 39 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 39.0 |
| `ste-practices.omitted-conjunction-that` | suggestion | 21 | 5 | 0 | 4 | 1 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 21.0 |
| `ste-practices.phrasal-verb` | suggestion | 8 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 8.0 |
| `ste-practices.unclear-demonstrative-this` | suggestion | 47 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 47.0 |
| `ste-practices.unclear-pronoun` | suggestion | 11 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 11.0 |
| `ste-procedural.condition-after-command` | warning | 76 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 76.0 |
| `ste-procedural.instruction-not-imperative` | warning | 38 | 5 | 0 | 0 | 0 | 5 | 100% | DEMOTE/DECOMMISSION; extrap FP 38.0 |
| `ste-procedural.multiple-instructions-per-sentence` | warning | 41 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 41.0 |
| `ste-procedural.sentence-too-long-procedural` | warning | 10 | 5 | 4 | 1 | 0 | 0 | 20% | RETAIN; extrap FP 2.0 |
| `ste-punctuation.colon-terminates-sentence-for-count` | suggestion | 25 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 25.0 |
| `ste-punctuation.hyphen-group-too-long` | suggestion | 2 | 2 | 0 | 0 | 2 | 0 | 100% | MASK ENGINE; extrap FP 2.0 |
| `ste-punctuation.hyphen-missing-in-compound-modifier` | suggestion | 20 | 5 | 4 | 1 | 0 | 0 | 20% | RETAIN; extrap FP 4.0 |
| `ste-punctuation.semicolon-used` | suggestion | 26 | 5 | 0 | 4 | 1 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 26.0 |
| `ste-sentences.complex-text-not-in-vertical-list` | warning | 44 | 5 | 0 | 1 | 1 | 3 | 100% | DEMOTE/DECOMMISSION; extrap FP 44.0 |
| `ste-sentences.omitted-word-or-contraction` | warning | 122 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 122.0 |
| `ste-verbs.auxiliary-stacking` | warning | 71 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 71.0 |
| `ste-verbs.complex-tense` | warning | 51 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 51.0 |
| `ste-verbs.nominalized-action` | warning | 11 | 5 | 2 | 3 | 0 | 0 | 60% | DEMOTE/DECOMMISSION; extrap FP 6.6 |
| `ste-verbs.passive-voice` | warning | 239 | 5 | 1 | 4 | 0 | 0 | 80% | DEMOTE/DECOMMISSION; extrap FP 191.2 |
| `ste-words.approved-word-substitution` | warning | 36 | 5 | 3 | 2 | 0 | 0 | 40% | RETAIN; extrap FP 14.4 |
| `ste-words.obligation-word-substitution` | suggestion | 35 | 5 | 4 | 1 | 0 | 0 | 20% | RETAIN; extrap FP 7.0 |
| `ste-words.slang-or-jargon-term` | warning | 1 | 1 | 1 | 0 | 0 | 0 | 0% | RETAIN; extrap FP 0.0 |
| `ste-words.spelling` | warning | 9 | 5 | 0 | 5 | 0 | 0 | 100% | DEMOTE/DECOMMISSION; extrap FP 9.0 |
| `ste-words.verb-used-as-noun` | warning | 1 | 1 | 0 | 1 | 0 | 0 | 100% | RETAIN; extrap FP 1.0 |

## Error-severity findings on human prose

The human baseline has 132 error findings. Every error-producing rule and its sampled labels is listed here; labels are in sample order and backed by the sidecar JSON.

| rule | error findings | sampled labels | sampled TP/FP |
|---|---:|---|---|
| `ai-tells-content-shape.durable-vocabulary-habits` | 15 | FP-not-prose, FP-correct-prose, FP-not-prose, FP-correct-prose, FP-correct-prose | 0 TP; 3 FP-correct; 2 FP-not-prose; 0 FP-genre |
| `ai-tells-content-shape.fake-specificity` | 2 | FP-correct-prose, FP-correct-prose | 0 TP; 2 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `ai-tells-content-shape.superficial-ing-analysis` | 2 | FP-correct-prose, FP-correct-prose | 0 TP; 2 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `ai-tells-register.corporate-analytic-filler-core` | 2 | TP, TP | 2 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `ai-tells-structure.summary-closer-frames` | 1 | FP-correct-prose | 0 TP; 1 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `orwell.compound-preposition` | 21 | TP, TP, TP, TP, TP | 5 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `orwell.unsupported-evaluative` | 6 | TP, TP, TP, TP, FP-not-prose | 4 TP; 0 FP-correct; 1 FP-not-prose; 0 FP-genre |
| `prose-discipline.bidirectional-hedge` | 2 | TP, FP-correct-prose | 1 TP; 1 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-discipline.frozen-verb` | 3 | TP, TP, TP | 3 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-discipline.hedged-hedge` | 4 | TP, FP-correct-prose, FP-correct-prose, TP | 2 TP; 2 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-discipline.marketing-lexicon` | 1 | TP | 1 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-discipline.phrasal-verb` | 5 | FP-not-prose, FP-not-prose, FP-not-prose, TP, FP-not-prose | 1 TP; 0 FP-correct; 4 FP-not-prose; 0 FP-genre |
| `prose-discipline.run-on` | 2 | FP-not-prose, FP-not-prose | 0 TP; 0 FP-correct; 2 FP-not-prose; 0 FP-genre |
| `prose-format.no-unicode-dash` | 6 | FP-correct-prose, FP-correct-prose, FP-not-prose, FP-correct-prose, FP-correct-prose | 0 TP; 4 FP-correct; 1 FP-not-prose; 0 FP-genre |
| `prose-format.prose-block` | 13 | FP-correct-prose, FP-correct-prose, FP-correct-prose, FP-not-prose, FP-correct-prose | 0 TP; 4 FP-correct; 1 FP-not-prose; 0 FP-genre |
| `prose-inclusive.device-assumption` | 2 | FP-correct-prose, FP-correct-prose | 0 TP; 2 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inclusive.exclusive` | 13 | FP-correct-prose, FP-correct-prose, FP-correct-prose, FP-correct-prose, FP-correct-prose | 0 TP; 5 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inflation.apologizing` | 1 | TP | 1 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inflation.document-preamble` | 1 | FP-correct-prose | 0 TP; 1 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inflation.hedge-stack` | 1 | TP | 1 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inflation.intensifier` | 16 | TP, FP-correct-prose, TP, TP, TP | 4 TP; 1 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inflation.nominalized-verb` | 2 | TP, TP | 2 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |
| `prose-inflation.slop-lexicon` | 9 | TP, TP, TP, FP-not-prose, TP | 4 TP; 0 FP-correct; 1 FP-not-prose; 0 FP-genre |
| `prose-promotion.promotional-adjective-noun` | 2 | TP, TP | 2 TP; 0 FP-correct; 0 FP-not-prose; 0 FP-genre |

## Slopvacced per-rule readout

| rule | findings | sampled | TP | FP | TP rate | FP rate | interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| `ai-tells-formatting.bold-spray` | 3 | 3 | 0 | 3 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ai-tells-formatting.em-dash-density` | 4 | 4 | 0 | 4 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ai-tells-formatting.title-case-heading` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ai-tells-register.uniform-paragraph-mass` | 5 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ai-tells-structure.cataphoric-lead-in-core` | 5 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ai-tells-structure.emphasis-paragraph-metric` | 35 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ai-tells-structure.tricolon-abuse-core` | 25 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `docs-discipline.internal-refs` | 9 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-agency.anthropomorphism` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-agency.narrator-distance` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.ambiguity` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.dead-opener` | 2 | 2 | 0 | 2 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.directional-ref` | 2 | 2 | 0 | 2 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.future-tense` | 2 | 2 | 0 | 2 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.gerund-heading` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.hyphens` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.plural-abbreviation` | 3 | 3 | 0 | 3 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.relative-date` | 1 | 1 | 0 | 1 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-craft.sentence-length` | 27 | 5 | 5 | 0 | 100% | 0% | authors left a real warning; keep/strengthen or make genre-specific |
| `prose-craft.unclear-antecedent` | 2 | 2 | 0 | 2 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-discipline.term-rotation-signal` | 7 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-inflation.borderline-hype` | 3 | 3 | 0 | 3 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-inflation.vague-quantifier` | 4 | 4 | 0 | 4 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `prose-scope.rejected-alternative` | 2 | 2 | 0 | 2 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-descriptive.paragraph-too-many-sentences` | 2 | 2 | 2 | 0 | 100% | 0% | authors left a real warning; keep/strengthen or make genre-specific |
| `ste-descriptive.sentence-too-long-descriptive` | 118 | 5 | 3 | 2 | 60% | 40% | authors left a real warning; keep/strengthen or make genre-specific |
| `ste-nouns.multiword-noun-too-long` | 70 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-practices.false-friend-term` | 4 | 4 | 4 | 0 | 100% | 0% | authors left a real warning; keep/strengthen or make genre-specific |
| `ste-practices.latin-abbreviation` | 19 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-practices.omitted-conjunction-that` | 19 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-practices.phrasal-verb` | 4 | 4 | 0 | 4 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-practices.unclear-demonstrative-this` | 3 | 3 | 0 | 3 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-procedural.condition-after-command` | 73 | 5 | 2 | 3 | 40% | 60% | wrong for this gated prose or needs scope masking/demotion |
| `ste-procedural.instruction-not-imperative` | 8 | 5 | 5 | 0 | 100% | 0% | authors left a real warning; keep/strengthen or make genre-specific |
| `ste-procedural.multiple-instructions-per-sentence` | 20 | 5 | 4 | 1 | 80% | 20% | authors left a real warning; keep/strengthen or make genre-specific |
| `ste-procedural.sentence-too-long-procedural` | 2 | 2 | 1 | 1 | 50% | 50% | mixed; inspect rule-specific exceptions |
| `ste-punctuation.colon-terminates-sentence-for-count` | 10 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-punctuation.hyphen-group-too-long` | 2 | 2 | 0 | 2 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-punctuation.semicolon-used` | 129 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-sentences.complex-text-not-in-vertical-list` | 69 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-sentences.missing-article-or-determiner` | 6 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-verbs.auxiliary-stacking` | 9 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-verbs.complex-tense` | 22 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-verbs.nominalized-action` | 10 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-verbs.passive-voice` | 184 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-words.approved-word-substitution` | 3 | 3 | 0 | 3 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-words.spelling` | 43 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |
| `ste-words.verb-used-as-noun` | 8 | 5 | 0 | 5 | 0% | 100% | wrong for this gated prose or needs scope masking/demotion |

## Decommission candidates

Candidates are flagged when sampled FP rate >= 60% and extrapolated FP count >= 5; MASK ENGINE is added when FP-not-prose is >= 30%.

- `ai-tells-content-shape.durable-vocabulary-habits` (error): 15 findings, 100% sampled FP, extrapolated 15.0 FPs — DEMOTE/DECOMMISSION, MASK ENGINE.
- `ai-tells-formatting.bold-spray` (suggestion): 2 findings, 100% sampled FP, extrapolated 2.0 FPs — MASK ENGINE.
- `ai-tells-formatting.curly-quotes` (warning): 3 findings, 100% sampled FP, extrapolated 3.0 FPs — MASK ENGINE.
- `ai-tells-formatting.em-dash-density` (suggestion): 1 findings, 100% sampled FP, extrapolated 1.0 FPs — MASK ENGINE.
- `ai-tells-formatting.emoji-list-markers` (warning): 1 findings, 100% sampled FP, extrapolated 1.0 FPs — MASK ENGINE.
- `ai-tells-formatting.title-case-heading` (suggestion): 1 findings, 100% sampled FP, extrapolated 1.0 FPs — MASK ENGINE.
- `ai-tells-register.uniform-paragraph-mass` (suggestion): 2 findings, 100% sampled FP, extrapolated 2.0 FPs — MASK ENGINE.
- `ai-tells-structure.emphasis-paragraph-metric` (suggestion): 80 findings, 100% sampled FP, extrapolated 80.0 FPs — DEMOTE/DECOMMISSION, MASK ENGINE.
- `ai-tells-structure.rhetorical-question-transition` (suggestion): 3 findings, 100% sampled FP, extrapolated 3.0 FPs — MASK ENGINE.
- `ai-tells-structure.tricolon-abuse-core` (suggestion): 7 findings, 100% sampled FP, extrapolated 7.0 FPs — DEMOTE/DECOMMISSION.
- `docs-discipline.history-narration` (warning): 6 findings, 100% sampled FP, extrapolated 6.0 FPs — DEMOTE/DECOMMISSION.
- `docs-discipline.status-language` (warning): 6 findings, 100% sampled FP, extrapolated 6.0 FPs — DEMOTE/DECOMMISSION.
- `prose-agency.false-agency` (warning): 12 findings, 100% sampled FP, extrapolated 12.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.command-prompt` (warning): 80 findings, 100% sampled FP, extrapolated 80.0 FPs — DEMOTE/DECOMMISSION, MASK ENGINE.
- `prose-craft.directional-ref` (warning): 8 findings, 100% sampled FP, extrapolated 8.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.first-person-plural` (warning): 115 findings, 100% sampled FP, extrapolated 115.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.future-tense` (warning): 105 findings, 100% sampled FP, extrapolated 105.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.gerund-heading` (warning): 2 findings, 100% sampled FP, extrapolated 2.0 FPs — MASK ENGINE.
- `prose-craft.latinisms` (warning): 44 findings, 100% sampled FP, extrapolated 44.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.link-text` (warning): 6 findings, 100% sampled FP, extrapolated 6.0 FPs — DEMOTE/DECOMMISSION, MASK ENGINE.
- `prose-craft.politeness` (warning): 26 findings, 100% sampled FP, extrapolated 26.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.self-reference` (warning): 6 findings, 100% sampled FP, extrapolated 6.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.unclear-antecedent` (warning): 42 findings, 100% sampled FP, extrapolated 42.0 FPs — DEMOTE/DECOMMISSION.
- `prose-craft.versions` (warning): 7 findings, 100% sampled FP, extrapolated 7.0 FPs — DEMOTE/DECOMMISSION.
- `prose-discipline.phrasal-verb` (error): 5 findings, 80% sampled FP, extrapolated 4.0 FPs — MASK ENGINE.
- `prose-discipline.run-on` (error): 2 findings, 100% sampled FP, extrapolated 2.0 FPs — MASK ENGINE.
- `prose-format.no-unicode-dash` (error): 6 findings, 100% sampled FP, extrapolated 6.0 FPs — DEMOTE/DECOMMISSION.
- `prose-format.prose-block` (error): 13 findings, 100% sampled FP, extrapolated 13.0 FPs — DEMOTE/DECOMMISSION.
- `prose-inclusive.exclusive` (error): 13 findings, 100% sampled FP, extrapolated 13.0 FPs — DEMOTE/DECOMMISSION.
- `prose-scope.rejected-alternative` (warning): 1 findings, 100% sampled FP, extrapolated 1.0 FPs — MASK ENGINE.
- `ste-nouns.multiword-noun-too-long` (warning): 70 findings, 100% sampled FP, extrapolated 70.0 FPs — DEMOTE/DECOMMISSION.
- `ste-practices.gendered-or-exclusionary-language` (suggestion): 10 findings, 100% sampled FP, extrapolated 10.0 FPs — DEMOTE/DECOMMISSION.
- `ste-practices.latin-abbreviation` (suggestion): 39 findings, 100% sampled FP, extrapolated 39.0 FPs — DEMOTE/DECOMMISSION.
- `ste-practices.omitted-conjunction-that` (suggestion): 21 findings, 100% sampled FP, extrapolated 21.0 FPs — DEMOTE/DECOMMISSION.
- `ste-practices.phrasal-verb` (suggestion): 8 findings, 100% sampled FP, extrapolated 8.0 FPs — DEMOTE/DECOMMISSION.
- `ste-practices.unclear-demonstrative-this` (suggestion): 47 findings, 100% sampled FP, extrapolated 47.0 FPs — DEMOTE/DECOMMISSION.
- `ste-practices.unclear-pronoun` (suggestion): 11 findings, 100% sampled FP, extrapolated 11.0 FPs — DEMOTE/DECOMMISSION.
- `ste-procedural.condition-after-command` (warning): 76 findings, 100% sampled FP, extrapolated 76.0 FPs — DEMOTE/DECOMMISSION.
- `ste-procedural.instruction-not-imperative` (warning): 38 findings, 100% sampled FP, extrapolated 38.0 FPs — DEMOTE/DECOMMISSION.
- `ste-procedural.multiple-instructions-per-sentence` (warning): 41 findings, 100% sampled FP, extrapolated 41.0 FPs — DEMOTE/DECOMMISSION.
- `ste-punctuation.colon-terminates-sentence-for-count` (suggestion): 25 findings, 100% sampled FP, extrapolated 25.0 FPs — DEMOTE/DECOMMISSION.
- `ste-punctuation.hyphen-group-too-long` (suggestion): 2 findings, 100% sampled FP, extrapolated 2.0 FPs — MASK ENGINE.
- `ste-punctuation.semicolon-used` (suggestion): 26 findings, 100% sampled FP, extrapolated 26.0 FPs — DEMOTE/DECOMMISSION.
- `ste-sentences.complex-text-not-in-vertical-list` (warning): 44 findings, 100% sampled FP, extrapolated 44.0 FPs — DEMOTE/DECOMMISSION.
- `ste-sentences.omitted-word-or-contraction` (warning): 122 findings, 100% sampled FP, extrapolated 122.0 FPs — DEMOTE/DECOMMISSION.
- `ste-verbs.auxiliary-stacking` (warning): 71 findings, 100% sampled FP, extrapolated 71.0 FPs — DEMOTE/DECOMMISSION.
- `ste-verbs.complex-tense` (warning): 51 findings, 100% sampled FP, extrapolated 51.0 FPs — DEMOTE/DECOMMISSION.
- `ste-verbs.nominalized-action` (warning): 11 findings, 60% sampled FP, extrapolated 6.6 FPs — DEMOTE/DECOMMISSION.
- `ste-verbs.passive-voice` (warning): 239 findings, 80% sampled FP, extrapolated 191.2 FPs — DEMOTE/DECOMMISSION.
- `ste-words.spelling` (warning): 9 findings, 100% sampled FP, extrapolated 9.0 FPs — DEMOTE/DECOMMISSION.

## Checked and fine

- All 95 human rule keys have complete samples: five rows for rules with >=3 findings and every row for rules with <3.
- All 48 slopvacced rule keys have complete samples: five rows for rules with >=5 findings and every row for rules with <5.
- Human source lines and containing sentences were loaded from corpus files for every sidecar row.
- No judgement rule was treated as a firing finding; the sidecar covers deterministic baseline findings only.
- Full per-row evidence and reasons are in `local://audit/HumanFpLabels-labels.json`.
