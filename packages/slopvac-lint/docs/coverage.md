# Coverage

All 53 numbered rules and all 8 general recommendations have an entry. 65 rule entries cover
61 source items, because three items split into more than one entry where the source rule
carries two independent obligations.

Tier column reads `strict/normal/relaxed`, where `e` is enforced, `a` is advisory, and `x` is
excluded.

| Rule | Our rule id | Kind | Tiers | Mechanizable |
|---|---|---|---|---|
| 1.1 | `word-outside-controlled-vocabulary` | vocabulary | e/a/x | partial |
| 1.1 | `approved-word-substitution` | substitution | e/e/a | yes |
| 1.2 | `word-used-in-wrong-part-of-speech` | vocabulary | e/a/x | partial |
| 1.3 | `word-used-outside-permitted-sense` | judgement | e/a/x | no |
| 1.4 | `verb-or-adjective-form-not-permitted` | vocabulary | e/a/x | partial |
| 1.5 | `domain-noun-category-membership` | judgement | e/a/x | no |
| 1.6 | `unapproved-word-not-a-domain-noun` | judgement | e/a/x | no |
| 1.7 | `noun-used-as-verb` | substitution | e/e/a | partial |
| 1.8 | `domain-noun-not-organization-approved` | judgement | e/a/x | partial |
| 1.9 | `domain-noun-too-long-or-unclear` | judgement | a/a/x | partial |
| 1.10 | `slang-or-jargon-term` | tokens | e/e/a | yes |
| 1.11 | `inconsistent-term-for-same-thing` | structure | e/e/a | partial |
| 1.12 | `domain-verb-category-membership` | judgement | e/a/x | no |
| 1.13 | `verb-used-as-noun` | pattern | e/e/a | partial |
| 1.14 | `non-american-spelling` | substitution | e/e/e | yes |
| 2.1 | `multiword-noun-too-long` | metric | e/e/a | partial |
| 2.2 | `long-domain-term-without-short-form` | judgement | e/a/x | partial |
| 3.1 | `verb-form-not-listed` | vocabulary | e/a/x | partial |
| 3.2 | `complex-tense` | pattern | e/e/a | yes |
| 3.3 | `past-participle-not-adjectival` | judgement | e/a/x | partial |
| 3.4 | `auxiliary-stacking` | pattern | e/e/a | yes |
| 3.5 | `gerund-outside-noun-use` | judgement | e/a/x | no |
| 3.6 | `passive-voice` | pattern | e/e/a | yes |
| 3.7 | `nominalized-action` | pattern | e/e/a | partial |
| 4.1 | `sentence-not-short-or-clear` | judgement | e/e/a | no |
| 4.2 | `omitted-word-or-contraction` | pattern | e/e/a | partial |
| 4.3 | `complex-text-not-in-vertical-list` | metric | e/e/a | yes |
| 4.3 | `vertical-list-lead-in-missing-colon` | structure | e/e/a | yes |
| 4.3 | `vertical-list-item-punctuation` | structure | e/a/x | yes |
| 4.4 | `missing-connector-between-related-sentences` | judgement | e/a/x | no |
| 4.5 | `missing-article-or-determiner` | pattern | e/a/x | partial |
| 5.1 | `sentence-too-long-procedural` | metric | e/e/e | yes |
| 5.2 | `multiple-instructions-per-sentence` | pattern | e/e/a | partial |
| 5.3 | `instruction-not-imperative` | pattern | e/e/a | partial |
| 5.4 | `condition-after-command` | pattern | e/e/a | yes |
| 5.5 | `note-gives-instruction` | pattern | e/e/e | yes |
| 6.1 | `information-not-gradual` | judgement | e/a/x | no |
| 6.2 | `missing-key-word-structure` | judgement | e/a/x | no |
| 6.3 | `sentence-too-long-descriptive` | metric | e/e/e | yes |
| 6.4 | `paragraph-without-related-information` | judgement | a/a/x | no |
| 6.5 | `paragraph-has-multiple-topics` | judgement | e/e/a | no |
| 6.6 | `paragraph-too-many-sentences` | metric | e/e/a | yes |
| 7.1 | `risk-level-word-missing-or-wrong` | judgement | e/e/e | partial |
| 7.2 | `safety-block-does-not-start-with-command` | pattern | e/e/e | yes |
| 7.3 | `safety-block-missing-consequence` | structure | e/e/e | yes |
| 8.1 | `semicolon-used` | pattern | e/e/a | yes |
| 8.2 | `hyphen-missing-in-compound-modifier` | pattern | e/a/x | partial |
| 8.2 | `hyphen-group-too-long` | pattern | e/e/a | yes |
| 8.3 | `parentheses-misuse` | judgement | a/a/x | no |
| 8.4 | `colon-terminates-sentence-for-count` | metric | e/e/e | yes |
| 8.5 | `parenthetical-counts-as-one-word` | judgement | e/e/e | yes (tokenizer) |
| 8.6 | `elements-counting-as-one-word` | judgement | e/e/e | yes (tokenizer) |
| 8.7 | `hyphenated-word-counts-as-one-word` | judgement | e/e/e | yes (tokenizer) |
| 9.1 | `word-swap-insufficient` | judgement | e/e/a | no |
| 9.2 | `word-sense-incorrect` | judgement | e/a/x | no |
| 9.3 | `phrasal-verb` | substitution | e/e/a | partial |
| 9.4 | `inconsistent-wording-for-same-step` | structure | e/e/a | partial |
| GR-1 | `omitted-conjunction-that` | pattern | e/a/x | yes |
| GR-2 | `ambiguous-preposition-with` | judgement | a/a/x | no |
| GR-3 | `unclear-pronoun` | pattern | e/a/x | partial |
| GR-4 | `unclear-demonstrative-this` | pattern | e/e/a | yes |
| GR-5 | `false-friend-term` | substitution | e/a/x | yes |
| GR-6 | `latin-abbreviation` | substitution | e/e/a | yes |
| GR-7 | `gendered-or-exclusionary-language` | substitution | e/e/e | yes |
| GR-8 | `possessive-form-unclear` | pattern | a/a/x | partial |

Counts: 61 of 61 source items covered. By kind: 23 judgement, 19 pattern, 7 substitution, 6
metric, 5 structure, 4 vocabulary, 1 tokens. Mechanizable: 30 yes, 20 partial, 15 no.

## Why three rules split into two entries

| Source rule | Split into | Reason |
|---|---|---|
| 1.1 | vocabulary check plus substitution table | The vocabulary check needs the dataset and a domain-term registry; the substitution table works today with no dependency. Different tiers, different fixes. |
| 4.3 | list trigger, lead-in colon, item punctuation | One direction plus nine formatting sub-requirements. The trigger is a threshold; the colon feeds the word counter; the punctuation set is house-style-sensitive. |
| 8.2 | compound-modifier hyphen, hyphen-group cap | The first needs an open-ended word list and is our largest false-positive risk. The second is a pure segment count and needs nothing. |

## Not adopted

Nothing is dropped, but eight items produce no finding and exist only so the reviewer and the
implementer have one source of truth.

**Three are tokenizer constraints, not prohibitions.** Rules 8.5, 8.6, and 8.7 define what one
word is. They carry `severity: off` and identical bad and good examples. They belong in the
ruleset because the word counts in rules 5.1, 6.3, and 8.4 are meaningless without them, and
burying the counting contract in code makes it untraceable.

**Five are irreducibly judgement and cannot be faked.** Rules 1.3, 1.5, 1.12, 9.1, and 9.2 all
turn on sense rather than surface form. The source's own worked example has one verb refused in
a sentence where the reader is the subject and permitted in a sentence where a machine is,
which no word list can encode. Rule 9.1 requires knowing whether a paraphrase exists. Each gets
a decidable reviewer question instead of a regex.

**Two aerospace-specific parts of larger rules are narrowed rather than dropped.** Rule 1.10
also covers regional dialect, which we do not implement, because a dialect list for software
prose is not maintainable; the slang and jargon half is a token list. Rule 1.5's 22-category
noun taxonomy is replaced by a 9-category subset plus 4 new software categories, analysed in
`vocabulary-design.md` — 11 of the 22 are physical-artifact categories with no software
analogue.

**One recommendation is deliberately weaker than the source.** GR-8 permits the possessive and
only asks a writer to drop it when unsure. A rule flagging every possessive would contradict
the source, so ours targets only the two shapes that are hard to parse and stays advisory
everywhere.

## Rules that need the vocabulary dataset

Nine rules cannot run without `vocabulary-build.md` output. They are the reason the vocabulary
is a required deliverable.

| Rule | Needs | Available now? |
|---|---|---|
| 1.1 `word-outside-controlled-vocabulary` | Word, POS, status | Yes, from the base CSV |
| 1.2 `word-used-in-wrong-part-of-speech` | POS-keyed status, plus a tagger | Status yes; tagger is a dependency |
| 1.4 `verb-or-adjective-form-not-permitted` | Inflected forms | **No** — not yet extracted |
| 3.1 `verb-form-not-listed` | Inflected forms | **No** — not yet extracted |
| 1.3, 9.2 word-sense rules | Approved-meaning gloss | **No** — and it stays unshipped even once extracted, because it is authored prose |
| 1.1 `approved-word-substitution` | Replacement per word | 39 pairs from the published recurring-error table, plus our overlay; the remaining 1,289 need column extraction |
| 1.5, 1.6, 1.12 domain-term rules | A project domain-term registry | Project configuration, not shipped data |

Two of these are hard blocks. The form rules cannot run at all until inflected forms are
extracted, which is why both sit at advisory on the normal tier. Do not substitute a stemmer:
the source refuses the past participle of a small number of verbs and a generated inflection
cannot know which ones.

## Top five false-positive risks

Ordered by expected finding volume. A false positive costs more than a miss, because it gets
the whole rule switched off.

### 1. Passive voice on adjectival predicates

`passive-voice` matches a form of "be" plus a participle-shaped word, which is also the shape of
an ordinary adjectival predicate. "The flag is deprecated" and "the field is required" describe
states, not hidden actors.

**Mitigation.** A 14-entry allowlist of state predicates, shipped with the rule. Plus: raise
severity when the match ends in "by" and lower it otherwise, since the "by" branch is the
high-confidence case. This rule is the noisiest in the set and the allowlist is not optional.

### 2. Word-count over-counting against every length cap

The three enforced length rules fire on compliant sentences whenever the tokenizer splits on
whitespace. The example in `metrics.md` counts 11 words under the contract and 15 under
whitespace, against a cap of 20.

**Mitigation.** `metrics.md` specifies nine collapse phases in a fixed order, with the
uncounted-numbering phase first, because that one is the most often skipped and it inflates
every numbered step by one. The length rules must not ship before the tokenizer does.

### 3. The paragraph-sentence count colliding with the word-count sentence

If `paragraph_sentences` uses the same sentence unit the word caps use, every four-item bulleted
list breaches the six-sentence cap, and reference documentation is nothing but bulleted lists.

**Mitigation.** Two distinct sentence units, resolved from three annotated examples in the
source and documented in `metrics.md` section 4. A list collapses into its lead-in for the
paragraph count and expands for the word count.

### 4. Identifiers matched as prose

Software documentation is full of tokens that look like prose violations. A semicolon in a shell
command. A four-segment hyphenated package name. A British spelling inside an API field name. A
CSS property. Each fires a rule that is correct about prose and wrong about code.

**Mitigation.** Four exception classes — `code-span`, `identifier-fidelity`, `api-name`,
`table-cell` — resolved by the runtime before any rule runs, not by individual patterns. 41 of
the 65 rules declare at least one. A fenced code block never enters the tokenizer at all.

### 5. Open-ended compound-modifier hyphenation

Rule 8.2's first case (a multi-word adjective before a noun) is unbounded in English. A general
pattern for it fires constantly. Phase-1 analysis flagged this before any rule was written.

**Mitigation.** Implemented as a closed two-part word list rather than a general rule, advisory
at the normal tier, excluded at relaxed. The mitigation deliberately accepts misses: a missing
hyphen does not block comprehension, so a miss is cheap here and a false positive is not.

### Also watched

Two more that did not make the top five but caused real test failures during drafting.

The nominalization rule anchored on a suffix alone fires on "the deployment" and "the
configuration", so it requires a preceding light verb. And four patterns failed their own
examples on irregular participles or on case: "is to be rebuilt", "has to be set", "It's", and a
lowercase demonstrative inside parentheses. Every regex in the ruleset was run against its own
bad and good examples plus trap sentences; four failed on the first pass and were fixed, and the
fix is recorded in each rule's provenance note.
