# Sentence-scope judgement pass

Rule source: `rules-sentence.json` (24 rules). Note: every rule in this file is
`scope: sentence`; there are no `scope: document` rules in my slice, so the
ratio/shape checks belong to another reviewer. Nothing below duplicates the
mechanical linter: no length, punctuation, passive-voice or word-list findings.

## absolute-assertion-remainder
severity: suggestion
scope: sentence
where: 476
quote: Every caller branches on these three codes, and the 1-versus-2 split is the contract
why: Counterexample available: a pre-commit hook that runs `slopvac` and only tests for a non-zero status branches on one code, not three. The claim is stated at tool-wide scope but only holds for callers that distinguish prose failure from run failure.
fix: Narrow it: "A caller that distinguishes prose failure from run failure must branch on all three codes."

## absolute-assertion-remainder
severity: suggestion
scope: sentence
where: 33-34
quote: The worst failure mode available is a disabled rule that still fails the gate.
why: A superlative over an unbounded set. A silently mis-parsed blocklist that drops every vocabulary check, or a rule that fires on nothing and reports clean, are both defensible candidates for worse; the document itself calls the second one out on line 328.
fix: State the ranking with its scope, or replace the superlative with the concrete consequence you mean.

## vague-attribution-remainder
severity: suggestion
scope: sentence
where: 10
quote: - AI-slop tells.
why: This is one of three cited sources for the ruleset, and it is the only one a reader cannot locate. Lines 11 and 12 name ASD-STE100 and Orwell 1946; this line names no catalog, no author, no URL, no file. The answer to "could a reader locate the source behind this claim" is no.
fix: Name the catalog or reference file the tells come from (as the other two bullets do), or state plainly that the tells are the project's own observations.

## figurative-verb-verdict-remainder
severity: suggestion
scope: sentence
where: 289
quote: That choice has two costs, and slopvac pays both in the open:
why: The verdict ("we are honest about the downside") arrives entirely through the paying-in-the-open metaphor. The sentence states no observation a reader could dispute; the two bullets that follow are mechanisms, not the claim the metaphor makes.
fix: Replace with the observation: "That choice has two costs. slopvac makes both visible: it rejects duplicate scopes, and `--explain-config` names the winning block."

## figurative-verb-verdict-remainder
severity: suggestion
scope: sentence
where: 456-457
quote: twenty-odd such scores drown out the categories that did find errors
why: The judgement that averaging is wrong is carried by "drown out". No number is given for how far the mean moves, so a reader who thinks the effect is small has nothing to argue with.
fix: Give the arithmetic: state what the mean becomes when one category scores 40 and twenty score 100.

## organic-consequence-remainder
severity: suggestion
scope: sentence
where: 439-440
quote: The penalty caps at 15 points and spends in full at a suggestion density of 6 per 100 words.
why: Yes, a person chose 15 and 6, and the sentence presents both as behaviour the penalty exhibits on its own. This is the shape the rule's own example flags ("The threshold settles at 34 words").
fix: Name the chooser and the reason: who set the cap at 15, and why 6 per 100 words rather than 3 or 10.

## organic-consequence-remainder
severity: suggestion
scope: sentence
where: 433
quote: The severity weights are error 4, warning 2, and suggestion 1.
why: Three chosen constants presented as facts of the world. No chooser, and no reason why the ratio is 4:2:1 rather than 3:2:1, in a section whose whole purpose is to justify the scoring model.
fix: State who picked the weights and what the ratio is meant to express.

## false-agency-remainder
severity: suggestion
scope: sentence
where: 14
quote: No rule hides its reasoning.
why: A rule is not a thing that can hide anything. A person decided every rule must carry provenance, and the loader enforces it; the sentence puts the abstraction in the seat and the decision disappears.
fix: "Every rule carries its provenance, and the loader refuses to start without it." Or put the reader in the seat: "You can see why any rule exists."

## false-agency-remainder
severity: suggestion
scope: sentence
where: 483
quote: The run earns no trust
why: A run cannot earn or fail to earn anything; trust is something a reader or a CI owner extends. The subject slot holds an abstraction so that no one has to say who should distrust what.
fix: "Do not trust the result: the config, the ruleset, the target, or the blocklist was broken."

## anthropomorphised-justification-remainder
severity: suggestion
scope: sentence
where: 455
quote: Both figures earn their place.
why: The value of keeping two figures is asserted by granting them desert rather than by naming a checkable property. The two sentences after it do the actual work, which is what makes this one merit-talk standing in for an argument.
fix: Delete it and let the two reasons carry the paragraph, or replace it with the property: "Each figure catches a failure the other misses."

## overloaded-sentence
severity: suggestion
scope: sentence
where: 281-282
quote: A later, broader pattern therefore beats an earlier, narrower one, and reordering two blocks changes the result.
why: Two independent claims joined by "and": a precedence consequence and a reordering consequence. Each stands alone without repeating a noun phrase, so the reader is holding two things. Not a parallel list: two different subjects, two different verbs.
fix: Split at "and": "A later, broader pattern therefore beats an earlier, narrower one. Reordering two blocks changes the result."

## overloaded-sentence
severity: suggestion
scope: sentence
where: 280-281
quote: Every matching block applies, and the last block to set a field owns that field.
why: Two separate rules of the resolution model in one sentence, with two subjects. A reader has to hold "all blocks apply" and "last write wins" at once, and each is a complete sentence on its own.
fix: "Every matching block applies. The last block to set a field owns that field."

## overloaded-sentence
severity: suggestion
scope: sentence
where: 476
quote: Every caller branches on these three codes, and the 1-versus-2 split is the contract:
why: One clause states what callers do, the other states what the interesting part is. Two ideas, no shared subject, and the second one is the point of the section.
fix: Cut the first clause or promote the second: "The 1-versus-2 split is the contract."

## word-swap-insufficient
severity: suggestion
scope: sentence
where: 260
quote: Setting one rule's severity is the dominant edit anyone makes.
why: No single word substitution rescues this. "Dominant" cannot be swapped for a plainer adjective without leaving a gerund subject asserting a frequency claim with no measurement behind it; the sentence needs restructuring, not a replacement word.
fix: Rewrite around a human subject and a real claim: "Most people only change one rule's severity."

## word-sense-incorrect
severity: suggestion
scope: sentence
where: 394-395
quote: An annotation with no reason gets no honor
why: "Honour" is recorded as a verb meaning "to act on" or "to respect"; here it is pressed into service as a mass noun meaning "the state of being acted on". That is not a sense the word carries, and the reader has to reverse-engineer the intended passive.
fix: Use the verb in its recorded sense: "slopvac ignores an annotation that gives no reason."

## ambiguous-preposition-with
severity: suggestion
scope: sentence
where: 397-398
quote: use `<!-- slopvac-disable -->` with `<!-- slopvac-enable -->`
why: All three senses are live. A reader can read "with" as association (both markers exist), as shared action (they take effect together), or as instrument (disable using enable). The intended meaning is a paired open/close bracket, which is none of the three.
fix: Name the relation: "wrap the span in `<!-- slopvac-disable -->` and `<!-- slopvac-enable -->`."

## ambiguous-preposition-with
severity: suggestion
scope: sentence
where: 170-171
quote: writes a starter `slopvac.toml` with the common overrides commented out
why: "With" can be read as instrument (the file is written using the overrides) or as description of the result (the file contains them, commented). Only the second is meant.
fix: State the result: "writes a starter `slopvac.toml`. The common overrides are present but commented out."

## sentence-not-short-or-clear
severity: suggestion
scope: sentence
where: 158-159
quote: It returns only the rules that no linter can check, and it gives the decidable question a reviewer must answer for each.
why: Two topics: what the flag filters, and what extra field the output carries. In a description one sentence should carry one topic, and a reader here has to hold both the selection and the payload.
fix: "It returns only the rules that no linter can check. Each one comes with the question a reviewer must answer."

## past-participle-not-adjectival
severity: suggestion
scope: sentence
where: 170-171
quote: with the common overrides commented out
why: "Commented" sits after the noun with no form of "be", "become" or "stay" in front of it. It is a reduced passive clause, not an adjective in front of the noun it describes, which is the position the rule permits.
fix: Move it in front of the noun ("the commented-out overrides") or give it a finite active verb ("the command comments out the common overrides").

## gerund-outside-noun-use
severity: suggestion
scope: sentence
where: 286-287
quote: it blocks you from relaxing a vendored or generated subtree
why: "Relaxing" is not naming a thing or modifying a domain noun; it carries the action of the clause as the object of a preposition. This is the shape of the rule's own second bad example ("reduce cost by caching the response").
fix: Use a finite verb: "with strictest-wins you could not relax a vendored or generated subtree."

## gerund-outside-noun-use
severity: suggestion
scope: sentence
where: 282
quote: reordering two blocks changes the result
why: "Reordering" takes its own object and carries the action of the clause; it names no thing and modifies no noun. The reader has to unpack an event compressed into a subject.
fix: "If you reorder two blocks, the result changes."

## word-used-outside-permitted-sense
severity: suggestion
scope: sentence
where: 440
quote: The penalty caps at 15 points and spends in full at a suggestion density of 6 per 100 words.
why: "Spend" is a transitive verb about an agent using up a resource. Here it is intransitive with the penalty as its own subject, in a sense no vocabulary entry records. A reader has to guess that it means "reaches its maximum".
fix: Use the recorded sense or drop the metaphor: "reaches the full 15 points at a suggestion density of 6 per 100 words."

## domain-noun-category-membership
severity: suggestion
scope: sentence
where: 131
quote: Skip the Vale sub-gate.
why: "Sub-gate" is out of vocabulary and appears exactly once, undefined. The document elsewhere calls Vale an engine that some rules route to, never a gate, so the noun does not name a specified concept in any category this document declares.
fix: Use the term the rest of the document uses ("the Vale engine"), or register "sub-gate" and define it where the routing is explained.

## domain-noun-category-membership
severity: suggestion
scope: sentence
where: 10
quote: - AI-slop tells.
why: "Tells" as a noun is domain jargon borrowed from poker and never defined here, and it is doing load-bearing work: it names one of the three sources of the entire ruleset. A reader outside the team cannot place it in any category.
fix: Define it on first use, or name the concept plainly ("recurring markers of machine-written prose").

## unapproved-word-not-a-domain-noun
severity: suggestion
scope: sentence
where: 319
quote: because agentless passive voice is correct in a specification
why: "Agentless" is out of vocabulary and it is an adjective, not a domain noun or part of a multi-word one. It is also the load-bearing word in the only justification given for tiers not forming an ordering.
fix: Replace with plain words: "passive voice that names no actor", or register the term.

## unapproved-word-not-a-domain-noun
severity: suggestion
scope: sentence
where: 456
quote: twenty-odd such scores
why: "Twenty-odd" is out of vocabulary, is not a domain noun, and is an informal approximation in a sentence whose point is arithmetic. The document states elsewhere that there are 23 categories, so the exact number is known.
fix: Use the figure: "twenty-two such scores", or "the other categories".

## domain-noun-too-long-or-unclear
severity: suggestion
scope: sentence
where: 428-429
quote: It derives from severity-weighted gating density against the budget, less a bounded suggestion penalty.
why: "Severity-weighted gating density" is a four-part invented term, and it stacks on "gating density", which is itself introduced two bullets earlier. A reader outside the team cannot resolve it without a definition, and none is given for the "severity-weighted" layer.
fix: Define the weighted figure once by name, then use the short form: state that errors count 4, warnings 2, and call the result the weighted density.

## domain-verb-category-membership
severity: suggestion
scope: sentence
where: 190-192
quote: A pattern that Go cannot compile therefore surfaces here
why: The sentence can be written with vocabulary verbs alone ("appears here", "is found here"), so the domain verb is not permitted. "Surface" as an intransitive verb of appearing belongs to no declared category and is a register borrowing.
fix: "You therefore find a pattern that Go cannot compile at compile time."

## domain-verb-category-membership
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
