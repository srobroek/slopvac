# findings-prose

Rule source: rules-prose.json (1 rule, scope `prose`).
Rule: `concrete-floor` — "Does this paragraph name at least one number, identifier, path, command, or dated event? If the writer possesses a more specific term than the one used, did they use it?"

The rule fired on four paragraphs. All four are second-half failures: the document
demonstrably holds the specific figure or identifier elsewhere and used a category
word in its place. Most paragraphs in this document pass the rule comfortably, and
that is noted in the summary rather than padded into findings.

## concrete-floor
severity: suggestion
scope: prose
where: 318-320
quote: A rule can invert that ordering on purpose, because agentless passive voice is correct in a specification and wrong in a README.
why: The judgement_question answers no on both halves. The paragraph names no number, identifier, path, command, or dated event, and it asserts that a rule inverts the tier ordering without naming the rule that does it — in a document that qualifies every other rule as `<category>.<rule>` (`orwell.stale-figure`, `prose-format.no-unicode-dash`). The claim is the sole justification for "the tiers do not form a strict ordering" and is the one claim a reader cannot check.
fix: Name the actual rule id whose `tiers` map inverts, and the two dispositions, e.g. the passive-voice rule at `enforced` under one profile and `advisory` under another.

## concrete-floor
severity: suggestion
scope: prose
where: 284-287
quote: The two alternatives lose for concrete reasons. Specificity ranking loses because no ordering on globs stays predictable.
why: Answers no. The paragraph promises "concrete reasons" and then supplies none: no glob, no path, no number, no identifier. "A vendored or generated subtree" is a category, and the document already holds the instances (`**/vendor/**`, `docs/generated/**`, `**/CHANGELOG.md`). The exception `genuinely-general-claim` does not cover it, because the paragraph is arguing a specific implementation choice against two specific rejected alternatives.
fix: Show the failing case with the real patterns: two globs where specificity ranking is ambiguous, and the `docs/**` plus `!docs/generated/**` subtree that strictest-wins would prevent you from relaxing.

## concrete-floor
severity: suggestion
scope: prose
where: 455-459
quote: twenty-odd such scores drown out the categories that did find errors
why: First half passes ("scores 100"), second half fails. The writer possesses the exact number and printed it 120 lines earlier — "the 216 packaged rules in 23 categories" — so "twenty-odd" is a vaguer term than the one already in hand.
fix: Replace "twenty-odd such scores" with the count implied by the shipped ruleset, i.e. state that the other 22 of 23 categories score 100.

## concrete-floor
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
