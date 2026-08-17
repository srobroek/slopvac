# Merged judgement findings: subject.md


Four read-only scoped judges over the 67 `kind: judgement` rules.

Counts by scope: document=10, paragraph=19, sentence=29, prose=4

Total: 62 findings, ordered by line.


## [sentence] vague-attribution-remainder
severity: suggestion
scope: sentence
where: 10
quote: - AI-slop tells.
why: This is one of three cited sources for the ruleset, and it is the only one a reader cannot locate. Lines 11 and 12 name ASD-STE100 and Orwell 1946; this line names no catalog, no author, no URL, no file. The answer to "could a reader locate the source behind this claim" is no.
fix: Name the catalog or reference file the tells come from (as the other two bullets do), or state plainly that the tells are the project's own observations.

## [sentence] domain-noun-category-membership
severity: suggestion
scope: sentence
where: 10
quote: - AI-slop tells.
why: "Tells" as a noun is domain jargon borrowed from poker and never defined here, and it is doing load-bearing work: it names one of the three sources of the entire ruleset. A reader outside the team cannot place it in any category.
fix: Define it on first use, or name the concept plainly ("recurring markers of machine-written prose").

## [sentence] false-agency-remainder
severity: suggestion
scope: sentence
where: 14
quote: No rule hides its reasoning.
why: A rule is not a thing that can hide anything. A person decided every rule must carry provenance, and the loader enforces it; the sentence puts the abstraction in the seat and the decision disappears.
fix: "Every rule carries its provenance, and the loader refuses to start without it." Or put the reader in the seat: "You can see why any rule exists."

## [document] competing-actor-terms
severity: suggestion
scope: document
where: 19-25, 155-159, 356, 410, 495
quote: "An agentic reviewer that needs a machine-readable source of truth" / "the decidable question a reviewer must answer" / "a human or an agentic reviewer reads one source of truth"
why: Rotation, and the distinction is never drawn. "reviewer", "agentic reviewer", and "human" act on the same output, and line 159's bare "reviewer" cannot be resolved to either. A second rotation covers the audience: "teams" (19), "you"/"your project" (185, 188, 411), "the project" (410, 495), and "anyone" (260) all name whoever configures slopvac.
fix: Use "reviewer" for the role and say once at first use whether it may be a person or an agent; pick one of "you" or "the project" for the configuring actor and replace the rest.

## [document] listicle-in-a-trench-coat
severity: suggestion
scope: document
where: 27-34
quote: "First, nothing passes in silence. ... Second, a misconfiguration is an error rather than a no-op."
why: Yes. Two consecutive paragraphs enumerate positions in a sequence ("First, ... Second, ...") and neither depends on the other; the second paragraph would read identically if the first were deleted. The prose form is carrying list content.
fix: Convert to a two-item list under the "Two design commitments" lead-in, or drop the ordinal markers and let each commitment be its own short paragraph.

## [paragraph] information-not-gradual
severity: suggestion
scope: paragraph
where: 27-30
quote: "Three gaps get an `UNCHECKED` line on the run: a missing Vale binary, an unknown locale tag, and a metric with no implementation."
why: Yes, it fires. Three terms arrive before the sentences that introduce them: Vale first appears here but is only explained at line 44, `[locale]` at 225, and the `metric` kind at 354. A reader must already know all three to parse the sentence. The same defect is at 426, where "The budget check reads this number" uses "budget" nine lines before the budget is described and without ever tying it to `max_total_per_100_words`.
fix: Move the three-gap example after Install, or name each gap in terms already on the page; define "budget" as `max_total_per_100_words` at first use.

## [document] one-point-dilution
severity: suggestion
scope: document
where: 32-34, 125, 166, 210-211, 415-417, 483, 487-497
quote: "Second, a misconfiguration is an error rather than a no-op."
why: Yes. The "a misconfiguration exits 2 rather than passing silently" argument is made at least six times in fresh clothing: as a design commitment (32-34), as flag notes ("An unknown name exits 2", "An unknown rule id exits 2"), as "slopvac rejects unknown keys" (210), as "a config error rather than a gate that checks nothing in silence" (417), as the exit-code table row (483), and again as the "Causes of exit 2" list plus its closing paragraph (487-497). The later passages add no fact the earlier ones lack.
fix: State the rule once where exit codes are defined, and delete the restatements at 32-34 and 415-417, leaving only the specifics that are new (which layer validates what).

## [sentence] absolute-assertion-remainder
severity: suggestion
scope: sentence
where: 33-34
quote: The worst failure mode available is a disabled rule that still fails the gate.
why: A superlative over an unbounded set. A silently mis-parsed blocklist that drops every vocabulary check, or a rule that fires on nothing and reports clean, are both defensible candidates for worse; the document itself calls the second one out on line 328.
fix: State the ranking with its scope, or replace the superlative with the concrete consequence you mean.

## [paragraph] epigram-closer-remainder
severity: suggestion
scope: paragraph
where: 34
quote: "The worst failure mode available is a disabled rule that still fails the gate."
why: Yes — the paragraph had already stated the behaviour (a mistyped rule id exits 2 with a did-you-mean). This closer states no exit code, no rule, and no observable output; it is a reversal-shaped line whose only job is to sound like a conclusion, and taken literally it is a claim about a bug the tool does not have.
fix: Delete the sentence, or replace it with the actual worst case and its exit code.

## [paragraph] paragraph-without-related-information
severity: suggestion
scope: paragraph
where: 44-48
quote: "[Vale](https://vale.sh) is an optional companion. If your environment allows a second binary, install it. slopvac compiles its own ruleset into Vale styles and hands most mechanical rules to Vale."
why: Yes, it fires. The opening sentence sets up "Vale is optional", but the later sentences do not add to that topic: they cover an install instruction, the compile-and-route architecture, and the degraded-run behaviour. Three topics under one topic sentence that only announces optionality.
fix: Keep the optionality sentence plus the without-`vale` behaviour in this paragraph and move the compile/routing explanation to `slopvac compile`, where it is stated again anyway.

## [prose] concrete-floor
severity: suggestion
scope: prose
where: 44-48
quote: slopvac compiles its own ruleset into Vale styles and hands most mechanical rules to Vale. The native engine runs the rest.
why: First half passes (`vale`, `PATH`), second half fails. "Most" and "the rest" are categories where the document establishes that exact counts exist: `slopvac compile` "reports the routing in four counts", including how many Vale took and how many stayed native. The specific term was available and a quantifier was used instead.
fix: Give the shipped split as two numbers out of 216, and cross-reference `slopvac compile` for the per-config figure.

# Summary
- rules evaluated: 1
- rules that fired: 1
- rules that did not apply: 0

The one rule in scope fired, on four separate paragraphs. No exception in its list
(`genuinely-general-claim`, `deliberate-summary-layer`, `redaction`, `quotation`)
covers any of the four: none sits in a summary layer, none is quoted, and each
argues a specific implementation choice rather than a general truth.

| category | rule id | occurrences | lines |
| --- | --- | --- | --- |
| orwell | `concrete-floor` | 4 | 318-320, 284-287, 455-459, 44-48 |

Paragraphs deliberately NOT reported, to be explicit about where the document is
clean: the scoring section (433-448) carries weights 4/2/1, the 15-point cap, the
6-per-100-words spend, the 60-word floor and the 20/5-point counts; the exit-code
and threshold sections quote codes and key names throughout; the config walkthrough
names every file it looks for in order. On the first half of the judgement_question
this document passes almost everywhere.

## [document] bare-quantifier-with-figure-available
severity: suggestion
scope: document
where: 46, 457
quote: "hands most mechanical rules to Vale" / "twenty-odd such scores drown out the categories"
why: Yes for both. The document has the numbers: it states 216 packaged rules in 23 categories (333-334) and says `slopvac compile` reports exactly how many rules Vale took (177-183), so "most mechanical rules" withholds a count the tool prints. "twenty-odd" rounds off the 23 categories the same document names. Neither set is unbounded or unmeasured, so no exception applies.
fix: Give the routing count in the Install section ("hands N of the 216 rules to Vale"), and replace "twenty-odd" with 23.

## [paragraph] marketing-register
severity: suggestion
scope: paragraph
where: 52-53, 118, 155-159, 201, 260, 456
quote: "Setting one rule's severity is the dominant edit anyone makes."
why: Yes — no number, benchmark, version, or citation supports "dominant edit", and someone who said "no, disabling a category is the commoner edit" would be voicing an opinion, not disputing a fact. The same shape recurs in "These flags do the useful work" (118), "The last one is the interesting flag" (156), "A single file is the smallest useful target" (52), "That check is what makes a generated document in the repo trustworthy" (201), and "Both figures earn their place" (456). None of the four listed exceptions applies: this is a README, not a landing page, and none of the claims is quantified.
fix: Delete each evaluative sentence and let the surrounding fact stand, or replace it with the measurable behind it (e.g. drop "the dominant edit anyone makes" and keep only that a bare severity string stands in for the table).

## [paragraph] meta-narration-remainder
severity: suggestion
scope: paragraph
where: 95
quote: "A config file comes next."
why: Yes — it describes the document's own running order rather than any fact about slopvac. The sentence after it ("These three commands write one, show how it resolves, and describe a single rule") already introduces the block.
fix: Delete the sentence.

## [paragraph] unasked-for-rationale
severity: suggestion
scope: paragraph
where: 105-106, 262, 276, 395-396, 406, 448
quote: "It skips five patterns by default, because a generated changelog is not authored prose"
why: Yes on the legitimacy test. A reader who disagrees with the default exclude list acts no differently for reading the defence, the reason is not a constraint or invariant or measured number, and a README is not one of the decision-recording genres. The same defect appears as "Per-rule `weight` does not exist, by design" (262), "Overrides form an array of blocks rather than a table keyed by glob, for exactly that reason" (276), "\"Reads better\" sits on nobody's list, by design" (395), "that absence is the design" (406), and "That path is harsher per finding on purpose" (448) — six naked design defences with no behaviour attached.
fix: Cut the `because`/`by design`/`on purpose` clauses and keep the behaviour (the skip list, that `weight` is category-only, that a reason must come from the closed list); move the reasoning to an ADR or the commit that made the choice.

## [document] domain-noun-not-organization-approved
severity: suggestion
scope: document
where: 122, 131, 171, 311-318, 406-417
quote: "`--profile strict\|normal\|relaxed` | Override the configured tier for this run." / "Skip the Vale sub-gate."
why: No. The config schema in this same document is the glossary, and it names the setting `profile` and the section `[vocabulary]`; the prose calls them "tier" and "wordlist"/"blocklist". "Vale sub-gate" (131) appears once and matches nothing in the schema, where the switch is `[vale] enabled`.
fix: Use the schema's own names in prose: `profile` for the setting, `vocabulary` (or a single declared synonym) for the word file, and "Vale" or "the Vale step" instead of "sub-gate".

# Rules that did not fire

- **summary-closer-remainder** — the last section is `## License / Apache-2.0.`, a fact, not a re-list. No closing recap section exists.
- **invented-concept-label** — no title-cased or quoted coinage. "gating density" is bolded but defined in place (426-428); "strictest-wins" and "specificity ranking" are named and then explained (280-287).
- **audience-straddle-remainder** — no term is both glossed and later assumed. ASD-STE100 is expanded once (11) and never re-assumed; the unglossed items (SARIF, `pathspec`, RFC 2119, Pydantic) are consistently unglossed, which is one audience.
- **table-wrapping-one-sentence** — all four tables (120-134, 348-356, 312-316, 479-483) have two or more rows whose cells vary in the same dimension.
- **fabricated-citations-remainder** — the only references are https://vale.sh, ASD-STE100, Orwell's 1946 rules, SARIF 2.1.0, and RFC 2119. All are real, all are cited as facts rather than as support for a number, and none carries a DOI, ISBN, or author-year cite. No claim in the document rests on a source I would have had to fetch to check.
- **padded-symmetry** — no FAQ, Tips, or Troubleshooting section, and section lengths are genuinely uneven (License is one line). The five `slopvac <command>` subsections share an opening formula ("This command ...") and a similar mass, but each carries its own facts, so nothing exists purely to match a sibling.
- **hedged-into-uselessness** — the document asserts throughout. Load-bearing claims (precedence is file order, exit 2 means no trust, the score floor) are stated flat, with no double hedge and no hedged hedge.
- **long-domain-term-without-short-form** — no project-owned term runs past three words outside code spans; the long identifiers (`max_total_per_100_words`, `partialFingerprints`) fall under the code-span exception.

# Summary
- rules evaluated: 17
- rules that fired: 9 (11 findings, tricolon-abuse-remainder twice)
- rules that did not apply: 8

| category | fired rule ids |
| --- | --- |
| ai-tells-structure | tricolon-abuse-remainder (x2), listicle-in-a-trench-coat |
| ai-tells-register | over-formatting-reflex |
| ai-tells-content-shape | vaporware-description, elegant-variation, one-point-dilution |
| prose-discipline | competing-actor-terms, bare-quantifier-with-figure-available |
| ste-words | domain-noun-not-organization-approved |

## [sentence] domain-noun-category-membership
severity: suggestion
scope: sentence
where: 131
quote: Skip the Vale sub-gate.
why: "Sub-gate" is out of vocabulary and appears exactly once, undefined. The document elsewhere calls Vale an engine that some rules route to, never a gate, so the noun does not name a specified concept in any category this document declares.
fix: Use the term the rest of the document uses ("the Vale engine"), or register "sub-gate" and define it where the routing is explained.

## [paragraph] false-suspense-remainder
severity: suggestion
scope: paragraph
where: 156-157
quote: "The last one is the interesting flag."
why: Yes — the sentence announces that something important follows and states no part of it; the actual content ("it returns only the rules that no linter can check") arrives in the next sentence, which stands perfectly well alone.
fix: Delete the sentence and open on "`--judgement` returns only the rules that no linter can check."

## [sentence] sentence-not-short-or-clear
severity: suggestion
scope: sentence
where: 158-159
quote: It returns only the rules that no linter can check, and it gives the decidable question a reviewer must answer for each.
why: Two topics: what the flag filters, and what extra field the output carries. In a description one sentence should carry one topic, and a reader here has to hold both the selection and the payload.
fix: "It returns only the rules that no linter can check. Each one comes with the question a reviewer must answer."

## [paragraph] heading-echo
severity: suggestion
scope: paragraph
where: 162 (pattern also at 154, 170, 177, 197)
quote: "### `slopvac explain RULE_ID`\n\nThis command prints one rule in full."
why: Yes, it fires: the heading already names the command and its object, so "prints one rule in full" restates it and defers the first new fact (what the output holds) to sentence two. Four of the five command subsections open on the identical "This command ..." restatement, so the echo is systematic rather than incidental.
fix: Open each subsection on the first new fact — here, "The output holds the message, the fix, the tiers per profile, the examples, and the provenance."

## [sentence] ambiguous-preposition-with
severity: suggestion
scope: sentence
where: 170-171
quote: writes a starter `slopvac.toml` with the common overrides commented out
why: "With" can be read as instrument (the file is written using the overrides) or as description of the result (the file contains them, commented). Only the second is meant.
fix: State the result: "writes a starter `slopvac.toml`. The common overrides are present but commented out."

## [sentence] past-participle-not-adjectival
severity: suggestion
scope: sentence
where: 170-171
quote: with the common overrides commented out
why: "Commented" sits after the noun with no form of "be", "become" or "stay" in front of it. It is a reduced passive clause, not an adjective in front of the noun it describes, which is the position the rule permits.
fix: Move it in front of the noun ("the commented-out overrides") or give it a finite active verb ("the command comments out the common overrides").

## [sentence] domain-verb-category-membership
severity: suggestion
scope: sentence
where: 171
quote: `--profile` seeds the tier
why: "Seeds" is available in plain vocabulary ("sets the tier", "writes the tier into the file"), so the metaphorical verb is not permitted. It also hides which value ends up in the file.
fix: "`--profile` sets the tier in the generated file."

# Summary
- rules evaluated: 24
- rules that fired: 18
- rules that did not apply: 6

Did not apply, and why:
- `false-range` — the only "from X to Y" constructions are numeric scales (0 to 100, 100 to 70). Both endpoints sit on a real scale.
- `intensifier-tics-remainder` — the adverbs present ("visibly different", "harsher per finding") are each backed by a number or a named consequence in the same passage.
- `parentheses-misuse` — the one prose parenthetical is an abbreviation expansion on line 11, a permitted purpose. Every other parenthesis is inside a code fence or a table cell.
- `parenthetical-counts-as-one-word`, `hyphenated-word-counts-as-one-word`, `elements-counting-as-one-word` — severity `off` by construction. These are tokenizer contracts and cannot produce a finding against a document.

Fired rules by category:

| category | rule id | occurrences |
| --- | --- | --- |
| ai-tells-structure | absolute-assertion-remainder | 2 |
| ai-tells-structure | vague-attribution-remainder | 1 |
| ai-tells-register | figurative-verb-verdict-remainder | 2 |
| ai-tells-register | organic-consequence-remainder | 2 |
| ai-tells-register | false-agency-remainder | 2 |
| ai-tells-register | anthropomorphised-justification-remainder | 1 |
| prose-discipline | overloaded-sentence | 3 |
| ste-practices | word-swap-insufficient | 1 |
| ste-practices | word-sense-incorrect | 1 |
| ste-practices | ambiguous-preposition-with | 2 |
| ste-sentences | sentence-not-short-or-clear | 1 |
| ste-verbs | past-participle-not-adjectival | 1 |
| ste-verbs | gerund-outside-noun-use | 2 |
| ste-words | word-used-outside-permitted-sense | 1 |
| ste-words | domain-noun-category-membership | 2 |
| ste-words | unapproved-word-not-a-domain-noun | 2 |
| ste-words | domain-noun-too-long-or-unclear | 1 |
| ste-words | domain-verb-category-membership | 2 |

Total findings: 31 across 18 rules.

## [paragraph] risk-level-word-missing-or-wrong
severity: suggestion
scope: paragraph
where: 172
quote: "`--force` overwrites an existing file."
why: It fires weakly. This is the document's only destructive operation and it carries no risk marker at all. The consequence is damage to data only, not harm to a person, so the lower marker is the correct one — but the rule's second bad example is exactly this shape: a destructive effect stated with no marker.
fix: Add the lower risk marker to the sentence and state the recovery ("`--force` overwrites an existing `slopvac.toml`; the previous contents are not recoverable unless committed").

# Summary
- rules evaluated: 25
- rules that fired: 18 (across 19 finding blocks — `epigram-closer-remainder` fired twice)
- rules that did not apply: 7

Rules that did NOT fire, and why:
- `contrastive-inversion-remainder` — the "X rather than Y" constructions (data rather than code, error rather than a no-op, annotation contract rather than a comment convention) all name alternatives that real tools implement. No strawman.
- `anaphora-abuse` — no run of three consecutive sentences shares a subject-verb pair with only the object changing. The four `How many ...` bullets at 180-183 are parallel list items, which is correct list style, not anaphora.
- `analogy-stack-authority` — no company or product names are borrowed for authority anywhere in the document.
- `think-of-it-as-remainder` — the document contains no analogies at all; every explanation is stated as mechanism.
- `hedged-symmetry` — every counter-position named (specificity ranking, strictest-wins, averaging alone) is one a real designer holds, and the document takes a side each time.
- `urgency-inflation-remainder` — where the document raises stakes it names the failure (a 20-word message reaching 5.0/100w, a score of 0.0, exit 2). No bare "this is critical".
- `textbook-connector-runs` — no occurrence of moreover, furthermore, additionally, or consequently.

| category | fired rule ids |
| --- | --- |
| ai-tells-structure | cataphoric-lead-in-remainder, hollow-acknowledgment, staccato-negative-parallel-remainder, false-suspense-remainder, meta-narration-remainder, heading-echo |
| ai-tells-register | faux-candor-remainder, corporate-analytic-filler-remainder |
| ai-tells-content-shape | over-writing-remainder, unasked-for-rationale, epigram-closer-remainder (x2) |
| prose-discipline | marketing-register |
| ste-descriptive | information-not-gradual, missing-key-word-structure, paragraph-has-multiple-topics, paragraph-without-related-information |
| ste-safety | risk-level-word-missing-or-wrong |
| ste-sentences | missing-connector-between-related-sentences |

## [sentence] domain-verb-category-membership
severity: suggestion
scope: sentence
where: 190-192
quote: A pattern that Go cannot compile therefore surfaces here
why: The sentence can be written with vocabulary verbs alone ("appears here", "is found here"), so the domain verb is not permitted. "Surface" as an intransitive verb of appearing belongs to no declared category and is a register borrowing.
fix: "You therefore find a pattern that Go cannot compile at compile time."

## [sentence] word-swap-insufficient
severity: suggestion
scope: sentence
where: 260
quote: Setting one rule's severity is the dominant edit anyone makes.
why: No single word substitution rescues this. "Dominant" cannot be swapped for a plainer adjective without leaving a gerund subject asserting a frequency claim with no measurement behind it; the sentence needs restructuring, not a replacement word.
fix: Rewrite around a human subject and a real claim: "Most people only change one rule's severity."

## [sentence] overloaded-sentence
severity: suggestion
scope: sentence
where: 280-281
quote: Every matching block applies, and the last block to set a field owns that field.
why: Two separate rules of the resolution model in one sentence, with two subjects. A reader has to hold "all blocks apply" and "last write wins" at once, and each is a complete sentence on its own.
fix: "Every matching block applies. The last block to set a field owns that field."

## [sentence] overloaded-sentence
severity: suggestion
scope: sentence
where: 281-282
quote: A later, broader pattern therefore beats an earlier, narrower one, and reordering two blocks changes the result.
why: Two independent claims joined by "and": a precedence consequence and a reordering consequence. Each stands alone without repeating a noun phrase, so the reader is holding two things. Not a parallel list: two different subjects, two different verbs.
fix: Split at "and": "A later, broader pattern therefore beats an earlier, narrower one. Reordering two blocks changes the result."

## [sentence] gerund-outside-noun-use
severity: suggestion
scope: sentence
where: 282
quote: reordering two blocks changes the result
why: "Reordering" takes its own object and carries the action of the clause; it names no thing and modifies no noun. The reader has to unpack an event compressed into a subject.
fix: "If you reorder two blocks, the result changes."

## [paragraph] over-writing-remainder
severity: suggestion
scope: paragraph
where: 284-287
quote: "The two alternatives lose for concrete reasons. Specificity ranking loses because no ordering on globs stays predictable. Strictest-wins loses because it blocks you from relaxing a vendored or generated subtree"
why: No — a reader of THIS document does not act differently for reading it. The behaviour was already fully stated in the paragraph above (file order, last writer wins, reordering changes the result); this paragraph is a defence of two designs that were never shipped, appended to a section that had finished.
fix: Delete the paragraph and move the comparison to the ADR that chose file-order precedence. The same treatment applies to "Both figures earn their place. Averaging alone is too kind..." (456-459).

## [prose] concrete-floor
severity: suggestion
scope: prose
where: 284-287
quote: The two alternatives lose for concrete reasons. Specificity ranking loses because no ordering on globs stays predictable.
why: Answers no. The paragraph promises "concrete reasons" and then supplies none: no glob, no path, no number, no identifier. "A vendored or generated subtree" is a category, and the document already holds the instances (`**/vendor/**`, `docs/generated/**`, `**/CHANGELOG.md`). The exception `genuinely-general-claim` does not cover it, because the paragraph is arguing a specific implementation choice against two specific rejected alternatives.
fix: Show the failing case with the real patterns: two globs where specificity ranking is ambiguous, and the `docs/**` plus `!docs/generated/**` subtree that strictest-wins would prevent you from relaxing.

## [sentence] gerund-outside-noun-use
severity: suggestion
scope: sentence
where: 286-287
quote: it blocks you from relaxing a vendored or generated subtree
why: "Relaxing" is not naming a thing or modifying a domain noun; it carries the action of the clause as the object of a preposition. This is the shape of the rule's own second bad example ("reduce cost by caching the response").
fix: Use a finite verb: "with strictest-wins you could not relax a vendored or generated subtree."

## [document] tricolon-abuse-remainder
severity: suggestion
scope: document
where: 289-295
quote: "That choice has two costs, and slopvac pays both in the open:"
why: No. The two parallel bullets are not two instances of the same thing: the first is a real cost (duplicate scopes become a validation error), the second is a mitigation (`--explain-config` names the block that won). The symmetry of the pair is asserted by the lead-in and not carried by the items.
fix: State the one cost as prose and move the `--explain-config` sentence out of the pair, since it is the remedy rather than a second cost.

## [paragraph] faux-candor-remainder
severity: suggestion
scope: paragraph
where: 289-294
quote: "That choice has two costs, and slopvac pays both in the open:"
why: Yes — the admission costs the author nothing. Both items listed underneath are mitigations the tool ships (duplicate scopes are a validation error; `--explain-config` names the winning block), not costs the reader bears, so the frame performs candour while the content is a feature list.
fix: Either state the real cost with its consequence (a reordered block silently changes which settings apply) or drop the "pays both in the open" frame and present the two behaviours as behaviours.

## [sentence] figurative-verb-verdict-remainder
severity: suggestion
scope: sentence
where: 289
quote: That choice has two costs, and slopvac pays both in the open:
why: The verdict ("we are honest about the downside") arrives entirely through the paying-in-the-open metaphor. The sentence states no observation a reader could dispute; the two bullets that follow are mechanisms, not the claim the metaphor makes.
fix: Replace with the observation: "That choice has two costs. slopvac makes both visible: it rejects duplicate scopes, and `--explain-config` names the winning block."

## [paragraph] hollow-acknowledgment
severity: suggestion
scope: paragraph
where: 318-320
quote: "The tiers do not form a strict ordering. A rule can invert that ordering on purpose, because agentless passive voice is correct in a specification and wrong in a README."
why: Yes — this names a trap (strict is not a superset of normal, so raising the profile can silence a rule you relied on) and then gives the reader no action, no way to measure which rules invert, and no pointer to a command or list that shows them. It closes the profiles section on a warning the reader cannot use.
fix: Name the inverting rules or point at the command that lists them (e.g. `slopvac rules --format json` and the field to read), or delete the paragraph.

## [prose] concrete-floor
severity: suggestion
scope: prose
where: 318-320
quote: A rule can invert that ordering on purpose, because agentless passive voice is correct in a specification and wrong in a README.
why: The judgement_question answers no on both halves. The paragraph names no number, identifier, path, command, or dated event, and it asserts that a rule inverts the tier ordering without naming the rule that does it — in a document that qualifies every other rule as `<category>.<rule>` (`orwell.stale-figure`, `prose-format.no-unicode-dash`). The claim is the sole justification for "the tiers do not form a strict ordering" and is the one claim a reader cannot check.
fix: Name the actual rule id whose `tiers` map inverts, and the two dispositions, e.g. the passive-voice rule at `enforced` under one profile and `advisory` under another.

## [sentence] unapproved-word-not-a-domain-noun
severity: suggestion
scope: sentence
where: 319
quote: because agentless passive voice is correct in a specification
why: "Agentless" is out of vocabulary and it is an adjective, not a domain noun or part of a multi-word one. It is also the load-bearing word in the only justification given for tiers not forming an ordering.
fix: Replace with plain words: "passive voice that names no actor", or register the term.

## [document] vaporware-description
severity: suggestion
scope: document
where: 354 vs 77
quote: "| `metric` | A counted measurement against a threshold: sentence words, clause boundaries, passive ratio, syllables per word. |"
why: Not for every behaviour. The rule-kind table presents `metric` in the present tense as a working checker, while the sample run at line 77 discloses that five metric rules "have no implementation in either engine, so they did NOT run". That is the mixture the rule targets: the body prose reads as shipped and the unshipped part is admitted in a transcript. I could not verify the remaining present-tense claims against HEAD, since I am read-only on the document.
fix: State the coverage where the kind is described: say in the `metric` row (or a status column) how many metric rules have a checker and how many do not, rather than leaving the gap to a sample transcript.

## [document] over-formatting-reflex
severity: suggestion
scope: document
where: 358-364, 474-493 (also 8-12, 335-343, 466-472)
quote: "- Code fences.\n- Inline code.\n- URLs.\n- Front matter."
why: No. Several lists hold no columns and no independent parallel items, only a noun phrase per line where a single sentence says the same thing: the four excluded spans (358-364), the five possible failures (466-472), the seven causes of exit 2 (487-493), and the three ruleset sources (8-12). "Would two sentences of prose say the same thing?" answers yes for each. The four real tables are fine.
fix: Unwrap the single-noun-phrase lists into sentences, e.g. "The `prose` scope leaves out code fences, inline code, URLs, and front matter." Keep bullets only where an item runs to a clause with its own detail, as in the output-format list at 139-150.

## [paragraph] paragraph-has-multiple-topics
severity: suggestion
scope: paragraph
where: 366-369
quote: "The `heading`, `sentence`, `paragraph`, `document`, and `raw` scopes widen or narrow that view. A match written entirely in capitals is exempt by default."
why: Yes — the paragraph splits cleanly at that boundary and neither half needs the other. Sentence one closes the scope topic; sentences two and three start a new topic (the all-caps exemption) that has nothing to do with scopes.
fix: Split after the scopes sentence and give the all-caps exemption its own paragraph, or its own short subsection.

## [sentence] word-sense-incorrect
severity: suggestion
scope: sentence
where: 394-395
quote: An annotation with no reason gets no honor
why: "Honour" is recorded as a verb meaning "to act on" or "to respect"; here it is pressed into service as a mass noun meaning "the state of being acted on". That is not a sense the word carries, and the reader has to reverse-engineer the intended passive.
fix: Use the verb in its recorded sense: "slopvac ignores an annotation that gives no reason."

## [sentence] ambiguous-preposition-with
severity: suggestion
scope: sentence
where: 397-398
quote: use `<!-- slopvac-disable -->` with `<!-- slopvac-enable -->`
why: All three senses are live. A reader can read "with" as association (both markers exist), as shared action (they take effect together), or as instrument (disable using enable). The intended meaning is a paired open/close bracket, which is none of the three.
fix: Name the relation: "wrap the span in `<!-- slopvac-disable -->` and `<!-- slopvac-enable -->`."

## [document] elegant-variation
severity: suggestion
scope: document
where: 406-417 and 122/171/311-319
quote: "No wordlist ships with slopvac ... A packaged dictionary enforced as an *allowlist* ... Point `[vocabulary] path` at a file ... slopvac loads the blocklist"
why: Yes, twice. One file is called a wordlist, a dictionary, a blocklist, and `[vocabulary] path` inside eight lines, with no sentence saying they are the same file. Separately, "tier" and "profile" rotate for one referent: `--profile` "Override the configured tier" (122), "`--profile` seeds the tier" (171), "The three shipped profiles" and "The tiers do not form a strict ordering" (311-318).
fix: Pick one name for the file (the config key `vocabulary`, or `blocklist` if that is the shipped word) and use it every time; likewise choose either "profile" or "tier" and state the relationship once if both must exist.

## [paragraph] missing-key-word-structure
severity: suggestion
scope: paragraph
where: 406-417
quote: "No wordlist ships with slopvac ... A packaged dictionary enforced as an *allowlist* ... A wordlist is an editorial position ... Point `[vocabulary] path` ... name its own blocklist"
why: Yes, it fires: one object is called wordlist, dictionary, vocabulary, and blocklist across three adjacent paragraphs, and no sentence picks up the previous sentence's key word unchanged. The reader has to infer that all four name the same file.
fix: Pick one term — `blocklist`, since that is what the config and `examples/blocklist.toml` call it — and repeat it in every sentence, reserving `[vocabulary]` for the config table name only.

## [paragraph] epigram-closer-remainder
severity: suggestion
scope: paragraph
where: 425-426
quote: "It counts. It does not judge."
why: Yes — it performs having concluded. The bullet already said `per_100_words` is raw density over every finding and comparable across lengths; "It counts. It does not judge." adds no fact and survives editing only because it reads quotable.
fix: Delete both sentences; the density definition above already carries the content.

## [sentence] domain-noun-too-long-or-unclear
severity: suggestion
scope: sentence
where: 428-429
quote: It derives from severity-weighted gating density against the budget, less a bounded suggestion penalty.
why: "Severity-weighted gating density" is a four-part invented term, and it stacks on "gating density", which is itself introduced two bullets earlier. A reader outside the team cannot resolve it without a definition, and none is given for the "severity-weighted" layer.
fix: Define the weighted figure once by name, then use the short form: state that errors count 4, warnings 2, and call the result the weighted density.

## [sentence] organic-consequence-remainder
severity: suggestion
scope: sentence
where: 433
quote: The severity weights are error 4, warning 2, and suggestion 1.
why: Three chosen constants presented as facts of the world. No chooser, and no reason why the ratio is 4:2:1 rather than 3:2:1, in a section whose whole purpose is to justify the scoring model.
fix: State who picked the weights and what the ratio is meant to express.

## [sentence] organic-consequence-remainder
severity: suggestion
scope: sentence
where: 439-440
quote: The penalty caps at 15 points and spends in full at a suggestion density of 6 per 100 words.
why: Yes, a person chose 15 and 6, and the sentence presents both as behaviour the penalty exhibits on its own. This is the shape the rule's own example flags ("The threshold settles at 34 words").
fix: Name the chooser and the reason: who set the cap at 15, and why 6 per 100 words rather than 3 or 10.

## [sentence] word-used-outside-permitted-sense
severity: suggestion
scope: sentence
where: 440
quote: The penalty caps at 15 points and spends in full at a suggestion density of 6 per 100 words.
why: "Spend" is a transitive verb about an agent using up a resource. Here it is intransitive with the penalty as its own subject, in a sense no vocabulary entry records. A reader has to guess that it means "reaches its maximum".
fix: Use the recorded sense or drop the metaphor: "reaches the full 15 points at a suggestion density of 6 per 100 words."

## [paragraph] missing-connector-between-related-sentences
severity: suggestion
scope: paragraph
where: 445-446 (also 407-408)
quote: "One finding in a 20-word error message reaches 5.0 per 100 words. That figure fails every budget."
why: Yes — the second sentence states the result of the first, and nothing marks the relation, so the reader has to supply the "and therefore". Same at 407-408: "makes every unlisted word a finding. It drives a document with zero errors down to a score of 0.0" is a consequence presented as an unlinked assertion.
fix: Name the relation: "One finding in a 20-word error message reaches 5.0 per 100 words, which fails every budget."

## [prose] concrete-floor
severity: suggestion
scope: prose
where: 455-459
quote: twenty-odd such scores drown out the categories that did find errors
why: First half passes ("scores 100"), second half fails. The writer possesses the exact number and printed it 120 lines earlier — "the 216 packaged rules in 23 categories" — so "twenty-odd" is a vaguer term than the one already in hand.
fix: Replace "twenty-odd such scores" with the count implied by the shipped ruleset, i.e. state that the other 22 of 23 categories score 100.

## [sentence] anthropomorphised-justification-remainder
severity: suggestion
scope: sentence
where: 455
quote: Both figures earn their place.
why: The value of keeping two figures is asserted by granting them desert rather than by naming a checkable property. The two sentences after it do the actual work, which is what makes this one merit-talk standing in for an argument.
fix: Delete it and let the two reasons carry the paragraph, or replace it with the property: "Each figure catches a failure the other misses."

## [paragraph] corporate-analytic-filler-remainder
severity: suggestion
scope: paragraph
where: 456
quote: "Both figures earn their place."
why: Yes — the sentence inside the analysis frame states no fact, no measurement, and no consequence, only that the topic deserves attention. The following sentences carry the argument without it.
fix: Delete the sentence and open the paragraph on "Averaging alone is too kind." — or better, on the mechanism itself.

## [sentence] figurative-verb-verdict-remainder
severity: suggestion
scope: sentence
where: 456-457
quote: twenty-odd such scores drown out the categories that did find errors
why: The judgement that averaging is wrong is carried by "drown out". No number is given for how far the mean moves, so a reader who thinks the effect is small has nothing to argue with.
fix: Give the arithmetic: state what the mean becomes when one category scores 40 and twenty score 100.

## [sentence] unapproved-word-not-a-domain-noun
severity: suggestion
scope: sentence
where: 456
quote: twenty-odd such scores
why: "Twenty-odd" is out of vocabulary, is not a domain noun, and is an informal approximation in a sentence whose point is arithmetic. The document states elsewhere that there are 23 categories, so the exact number is known.
fix: Use the figure: "twenty-two such scores", or "the other categories".

## [sentence] absolute-assertion-remainder
severity: suggestion
scope: sentence
where: 476
quote: Every caller branches on these three codes, and the 1-versus-2 split is the contract
why: Counterexample available: a pre-commit hook that runs `slopvac` and only tests for a non-zero status branches on one code, not three. The claim is stated at tool-wide scope but only holds for callers that distinguish prose failure from run failure.
fix: Narrow it: "A caller that distinguishes prose failure from run failure must branch on all three codes."

## [sentence] overloaded-sentence
severity: suggestion
scope: sentence
where: 476
quote: Every caller branches on these three codes, and the 1-versus-2 split is the contract:
why: One clause states what callers do, the other states what the interesting part is. Two ideas, no shared subject, and the second one is the point of the section.
fix: Cut the first clause or promote the second: "The 1-versus-2 split is the contract."

## [paragraph] staccato-negative-parallel-remainder
severity: suggestion
scope: paragraph
where: 482
quote: "A threshold failed. The run worked. The prose did not."
why: Yes — of the three clipped clauses only the first carries a fact; the second and third exist to land the negated parallel. The neighbouring exit-code rows are plain descriptions, which makes the rhythm here visible as decoration.
fix: Rejoin to one clause: "A configured threshold failed."

## [sentence] false-agency-remainder
severity: suggestion
scope: sentence
where: 483
quote: The run earns no trust
why: A run cannot earn or fail to earn anything; trust is something a reader or a CI owner extends. The subject slot holds an abstraction so that no one has to say who should distrust what.
fix: "Do not trust the result: the config, the ruleset, the target, or the blocklist was broken."

## [document] tricolon-abuse-remainder
severity: suggestion
scope: document
where: 487-493
quote: "- Bad config.\n- An unknown category name.\n- An unknown rule name.\n- An unloadable ruleset.\n- A broken blocklist."
why: No. Seven identical-shape fragments where the first item subsumes at least three of the others: an unknown category name, an unknown rule name, and a blocklist path that does not load are all "bad config" by the document's own account (lines 210-211 say the config layer rejects unknown category and rule names). The items do not each state a fact the others do not.
fix: Drop the generic "Bad config." bullet and keep only the causes that name a distinct failure, or fold the whole list into one sentence: exit 2 covers a config error, an unknown category or rule name, an unloadable ruleset, a missing target, a broken blocklist, and a stale `reference --check` diff.

## [paragraph] cataphoric-lead-in-remainder
severity: suggestion
scope: paragraph
where: whole document (8, 20, 27, 28, 105, 118, 136, 155-156, 178, 266, 289, 309, 345, 357, 373, 421, 466, 476)
quote: "Three sources feed the ruleset" / "Three shapes of caller cover most use" / "Two design commitments run through the whole tool" / "It skips five patterns by default" / "The output reports the routing in four counts" / "Four layers rank in this order" / "Five failures are possible"
why: Yes — the document announces a count before roughly eighteen separate lists, and in almost every case the list or table directly below shows its own length, so the forecast changes nothing the reader does. The habit is the single strongest machine signature in the text: nearly every section opens on a numeral.
fix: Delete the count from the lead-ins where a list follows immediately (`Three sources feed the ruleset:` → `Sources:`; `Five failures are possible:` → `A document fails when:`). Keep the number only where the reader must budget effort before reading, e.g. the seven `kind` values in a long table.
