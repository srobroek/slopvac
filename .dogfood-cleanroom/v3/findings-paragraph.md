# findings — paragraph scope (25 rules)

Note on scope: every rule in `rules-paragraph.json` carries `scope: paragraph`. The brief
mentioned 17 `document`-scope rules; none are in this shard. All 25 were evaluated as
paragraph checks.

## cataphoric-lead-in-remainder
severity: suggestion
scope: paragraph
where: whole document (8, 20, 27, 28, 105, 118, 136, 155-156, 178, 266, 289, 309, 345, 357, 373, 421, 466, 476)
quote: "Three sources feed the ruleset" / "Three shapes of caller cover most use" / "Two design commitments run through the whole tool" / "It skips five patterns by default" / "The output reports the routing in four counts" / "Four layers rank in this order" / "Five failures are possible"
why: Yes — the document announces a count before roughly eighteen separate lists, and in almost every case the list or table directly below shows its own length, so the forecast changes nothing the reader does. The habit is the single strongest machine signature in the text: nearly every section opens on a numeral.
fix: Delete the count from the lead-ins where a list follows immediately (`Three sources feed the ruleset:` → `Sources:`; `Five failures are possible:` → `A document fails when:`). Keep the number only where the reader must budget effort before reading, e.g. the seven `kind` values in a long table.

## marketing-register
severity: suggestion
scope: paragraph
where: 52-53, 118, 155-159, 201, 260, 456
quote: "Setting one rule's severity is the dominant edit anyone makes."
why: Yes — no number, benchmark, version, or citation supports "dominant edit", and someone who said "no, disabling a category is the commoner edit" would be voicing an opinion, not disputing a fact. The same shape recurs in "These flags do the useful work" (118), "The last one is the interesting flag" (156), "A single file is the smallest useful target" (52), "That check is what makes a generated document in the repo trustworthy" (201), and "Both figures earn their place" (456). None of the four listed exceptions applies: this is a README, not a landing page, and none of the claims is quantified.
fix: Delete each evaluative sentence and let the surrounding fact stand, or replace it with the measurable behind it (e.g. drop "the dominant edit anyone makes" and keep only that a bare severity string stands in for the table).

## unasked-for-rationale
severity: suggestion
scope: paragraph
where: 105-106, 262, 276, 395-396, 406, 448
quote: "It skips five patterns by default, because a generated changelog is not authored prose"
why: Yes on the legitimacy test. A reader who disagrees with the default exclude list acts no differently for reading the defence, the reason is not a constraint or invariant or measured number, and a README is not one of the decision-recording genres. The same defect appears as "Per-rule `weight` does not exist, by design" (262), "Overrides form an array of blocks rather than a table keyed by glob, for exactly that reason" (276), "\"Reads better\" sits on nobody's list, by design" (395), "that absence is the design" (406), and "That path is harsher per finding on purpose" (448) — six naked design defences with no behaviour attached.
fix: Cut the `because`/`by design`/`on purpose` clauses and keep the behaviour (the skip list, that `weight` is category-only, that a reason must come from the closed list); move the reasoning to an ADR or the commit that made the choice.

## over-writing-remainder
severity: suggestion
scope: paragraph
where: 284-287
quote: "The two alternatives lose for concrete reasons. Specificity ranking loses because no ordering on globs stays predictable. Strictest-wins loses because it blocks you from relaxing a vendored or generated subtree"
why: No — a reader of THIS document does not act differently for reading it. The behaviour was already fully stated in the paragraph above (file order, last writer wins, reordering changes the result); this paragraph is a defence of two designs that were never shipped, appended to a section that had finished.
fix: Delete the paragraph and move the comparison to the ADR that chose file-order precedence. The same treatment applies to "Both figures earn their place. Averaging alone is too kind..." (456-459).

## hollow-acknowledgment
severity: suggestion
scope: paragraph
where: 318-320
quote: "The tiers do not form a strict ordering. A rule can invert that ordering on purpose, because agentless passive voice is correct in a specification and wrong in a README."
why: Yes — this names a trap (strict is not a superset of normal, so raising the profile can silence a rule you relied on) and then gives the reader no action, no way to measure which rules invert, and no pointer to a command or list that shows them. It closes the profiles section on a warning the reader cannot use.
fix: Name the inverting rules or point at the command that lists them (e.g. `slopvac rules --format json` and the field to read), or delete the paragraph.

## epigram-closer-remainder
severity: suggestion
scope: paragraph
where: 425-426
quote: "It counts. It does not judge."
why: Yes — it performs having concluded. The bullet already said `per_100_words` is raw density over every finding and comparable across lengths; "It counts. It does not judge." adds no fact and survives editing only because it reads quotable.
fix: Delete both sentences; the density definition above already carries the content.

## epigram-closer-remainder
severity: suggestion
scope: paragraph
where: 34
quote: "The worst failure mode available is a disabled rule that still fails the gate."
why: Yes — the paragraph had already stated the behaviour (a mistyped rule id exits 2 with a did-you-mean). This closer states no exit code, no rule, and no observable output; it is a reversal-shaped line whose only job is to sound like a conclusion, and taken literally it is a claim about a bug the tool does not have.
fix: Delete the sentence, or replace it with the actual worst case and its exit code.

## staccato-negative-parallel-remainder
severity: suggestion
scope: paragraph
where: 482
quote: "A threshold failed. The run worked. The prose did not."
why: Yes — of the three clipped clauses only the first carries a fact; the second and third exist to land the negated parallel. The neighbouring exit-code rows are plain descriptions, which makes the rhythm here visible as decoration.
fix: Rejoin to one clause: "A configured threshold failed."

## false-suspense-remainder
severity: suggestion
scope: paragraph
where: 156-157
quote: "The last one is the interesting flag."
why: Yes — the sentence announces that something important follows and states no part of it; the actual content ("it returns only the rules that no linter can check") arrives in the next sentence, which stands perfectly well alone.
fix: Delete the sentence and open on "`--judgement` returns only the rules that no linter can check."

## meta-narration-remainder
severity: suggestion
scope: paragraph
where: 95
quote: "A config file comes next."
why: Yes — it describes the document's own running order rather than any fact about slopvac. The sentence after it ("These three commands write one, show how it resolves, and describe a single rule") already introduces the block.
fix: Delete the sentence.

## heading-echo
severity: suggestion
scope: paragraph
where: 162 (pattern also at 154, 170, 177, 197)
quote: "### `slopvac explain RULE_ID`\n\nThis command prints one rule in full."
why: Yes, it fires: the heading already names the command and its object, so "prints one rule in full" restates it and defers the first new fact (what the output holds) to sentence two. Four of the five command subsections open on the identical "This command ..." restatement, so the echo is systematic rather than incidental.
fix: Open each subsection on the first new fact — here, "The output holds the message, the fix, the tiers per profile, the examples, and the provenance."

## faux-candor-remainder
severity: suggestion
scope: paragraph
where: 289-294
quote: "That choice has two costs, and slopvac pays both in the open:"
why: Yes — the admission costs the author nothing. Both items listed underneath are mitigations the tool ships (duplicate scopes are a validation error; `--explain-config` names the winning block), not costs the reader bears, so the frame performs candour while the content is a feature list.
fix: Either state the real cost with its consequence (a reordered block silently changes which settings apply) or drop the "pays both in the open" frame and present the two behaviours as behaviours.

## corporate-analytic-filler-remainder
severity: suggestion
scope: paragraph
where: 456
quote: "Both figures earn their place."
why: Yes — the sentence inside the analysis frame states no fact, no measurement, and no consequence, only that the topic deserves attention. The following sentences carry the argument without it.
fix: Delete the sentence and open the paragraph on "Averaging alone is too kind." — or better, on the mechanism itself.

## information-not-gradual
severity: suggestion
scope: paragraph
where: 27-30
quote: "Three gaps get an `UNCHECKED` line on the run: a missing Vale binary, an unknown locale tag, and a metric with no implementation."
why: Yes, it fires. Three terms arrive before the sentences that introduce them: Vale first appears here but is only explained at line 44, `[locale]` at 225, and the `metric` kind at 354. A reader must already know all three to parse the sentence. The same defect is at 426, where "The budget check reads this number" uses "budget" nine lines before the budget is described and without ever tying it to `max_total_per_100_words`.
fix: Move the three-gap example after Install, or name each gap in terms already on the page; define "budget" as `max_total_per_100_words` at first use.

## missing-key-word-structure
severity: suggestion
scope: paragraph
where: 406-417
quote: "No wordlist ships with slopvac ... A packaged dictionary enforced as an *allowlist* ... A wordlist is an editorial position ... Point `[vocabulary] path` ... name its own blocklist"
why: Yes, it fires: one object is called wordlist, dictionary, vocabulary, and blocklist across three adjacent paragraphs, and no sentence picks up the previous sentence's key word unchanged. The reader has to infer that all four name the same file.
fix: Pick one term — `blocklist`, since that is what the config and `examples/blocklist.toml` call it — and repeat it in every sentence, reserving `[vocabulary]` for the config table name only.

## paragraph-has-multiple-topics
severity: suggestion
scope: paragraph
where: 366-369
quote: "The `heading`, `sentence`, `paragraph`, `document`, and `raw` scopes widen or narrow that view. A match written entirely in capitals is exempt by default."
why: Yes — the paragraph splits cleanly at that boundary and neither half needs the other. Sentence one closes the scope topic; sentences two and three start a new topic (the all-caps exemption) that has nothing to do with scopes.
fix: Split after the scopes sentence and give the all-caps exemption its own paragraph, or its own short subsection.

## paragraph-without-related-information
severity: suggestion
scope: paragraph
where: 44-48
quote: "[Vale](https://vale.sh) is an optional companion. If your environment allows a second binary, install it. slopvac compiles its own ruleset into Vale styles and hands most mechanical rules to Vale."
why: Yes, it fires. The opening sentence sets up "Vale is optional", but the later sentences do not add to that topic: they cover an install instruction, the compile-and-route architecture, and the degraded-run behaviour. Three topics under one topic sentence that only announces optionality.
fix: Keep the optionality sentence plus the without-`vale` behaviour in this paragraph and move the compile/routing explanation to `slopvac compile`, where it is stated again anyway.

## missing-connector-between-related-sentences
severity: suggestion
scope: paragraph
where: 445-446 (also 407-408)
quote: "One finding in a 20-word error message reaches 5.0 per 100 words. That figure fails every budget."
why: Yes — the second sentence states the result of the first, and nothing marks the relation, so the reader has to supply the "and therefore". Same at 407-408: "makes every unlisted word a finding. It drives a document with zero errors down to a score of 0.0" is a consequence presented as an unlinked assertion.
fix: Name the relation: "One finding in a 20-word error message reaches 5.0 per 100 words, which fails every budget."

## risk-level-word-missing-or-wrong
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
