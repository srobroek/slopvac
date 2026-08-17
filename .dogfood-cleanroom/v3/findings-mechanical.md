# Mechanical findings on README.v3.md

slopvac, profile normal. Score 75.8/100, 39 findings (2650 words, 1.472/100w).

Each entry is a deterministic rule that fired. These are not opinions: the
pattern matched. Ordered by line.

## line 3 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 6 coordinated items. Use a vertical list.

Line as written:

> slopvac is a deterministic prose linter and scorer for documentation. It reads

## line 13 — `prose-agency.anthropomorphism` (warning)

anthropomorphism: the loader refuses -- name the mechanism, not a mind

Line as written:

> and the loader refuses to start without provenance. The command

## line 16 — `ai-tells-structure.emphasis-paragraph-metric` (suggestion)

emphasis paragraph of 7 words -- rejoin the sentence; let the fact carry the weight

Line as written:

> Two commitments run through the whole tool:

## line 25 — `prose-inflation.vague-quantifier` (suggestion)

vague quantifier: usually -- give the count, or name the cases

Line as written:

> Callers usually take one of these shapes:

## line 136 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> - **`text`** prints the findings, an `UNCHECKED` line per gap, a per-category

## line 151 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> Each row of the list gives the kind, the severity, the disposition at a profile,

## line 151 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> Each row of the list gives the kind, the severity, the disposition at a profile,

## line 158 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 5 coordinated items. Use a vertical list.

Line as written:

> The output holds the message, the fix, the tiers per profile, the examples, and

## line 192 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> The generated Markdown reference splits into checked rules and rules of the

## line 252 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> A bare severity string stands in for the whole table, for categories and for

## line 271 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> Precedence follows **file order**. It follows neither specificity nor a

## line 271 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> Precedence follows **file order**. It follows neither specificity nor a

## line 276 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 26 words. Use twenty-five or fewer.

Line as written:

> Specificity ranking loses because no ordering on globs stays predictable.

## line 307 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> A rule's own disposition per profile lives in its `tiers` map, and those tiers

## line 326 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 26 words. Use twenty-five or fewer.

Line as written:

> Each rule has an id qualified as `<category>.<rule>`. It also carries a `kind`

## line 326 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 6 coordinated items. Use a vertical list.

Line as written:

> Each rule has an id qualified as `<category>.<rule>`. It also carries a `kind`

## line 326 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> Each rule has an id qualified as `<category>.<rule>`. It also carries a `kind`

## line 334 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 34 words. Use twenty-five or fewer.

Line as written:

> | Kind | What it does |

## line 334 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 5 coordinated items. Use a vertical list.

Line as written:

> | Kind | What it does |

## line 344 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> Scope keeps a rule off text it must not see. The `prose` scope leaves out code

## line 344 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 5 coordinated items. Use a vertical list.

Line as written:

> Scope keeps a rule off text it must not see. The `prose` scope leaves out code

## line 345 — `ai-tells-structure.tricolon-abuse-core` (suggestion)

tricolon: code, URLs, and front -- cut to the one or two that carry load; break the symmetry

Line as written:

> fences, inline code, URLs, and front matter. The `heading`, `sentence`,

## line 348 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> A match written entirely in capitals is exempt by default. An all-caps token in

## line 381 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> One further exemption stands apart. A rule that declares the `quotation`

## line 387 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 28 words. Use twenty-five or fewer.

Line as written:

> No blocklist ships with slopvac. A packaged dictionary enforced as an

## line 406 — `ste-nouns.multiword-noun-too-long` (warning)

This noun stack has 4 words. Use three or fewer.

Line as written:

> - **gating density** covers errors and warnings only. The budget,

## line 407 — `ste-practices.omitted-conjunction-that` (suggestion)

Add "that" after "checks this".

Line as written:

> `max_total_per_100_words`, checks this number.

## line 408 — `ste-punctuation.semicolon-used` (suggestion)

The semicolon is not permitted. Write two sentences.

Line as written:

> - **`score`** runs from 0 to 100. Errors count 4, warnings 2, and suggestions 1;

## line 411 — `ste-practices.omitted-conjunction-that` (suggestion)

Add "that" after "shows this".

Line as written:

> badge shows this number, and `min_score` reads it.

## line 444 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 5 coordinated items. Use a vertical list.

Line as written:

> A document fails when any configured threshold fails. Every failure names itself

## line 454 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> | Code | Meaning |

## line 462 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 28 words. Use twenty-five or fewer.

Line as written:

> Exit 2 covers a config error, an unknown category name, an unknown rule name, an

## line 462 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 7 coordinated items. Use a vertical list.

Line as written:

> Exit 2 covers a config error, an unknown category name, an unknown rule name, an

## line 477 — `ste-punctuation.semicolon-used` (suggestion)

The semicolon is not permitted. Write two sentences.

Line as written:

> - `vague-attribution-remainder`, line 10: subject.md names no catalog, author, URL, or file for the AI-slop tells, so naming one would invent a source; I glossed the term instead.

## line 477 — `ste-sentences.complex-text-not-in-vertical-list` (warning)

This sentence carries 4 coordinated items. Use a vertical list.

Line as written:

> - `vague-attribution-remainder`, line 10: subject.md names no catalog, author, URL, or file for the AI-slop tells, so naming one would invent a source; I glossed the term instead.

## line 478 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 28 words. Use twenty-five or fewer.

Line as written:

> - `concrete-floor` and `bare-quantifier-with-figure-available`, lines 44-48 / 46: the shipped Vale-versus-native split is not a number subject.md contains, so I removed the "most"/"the rest" quantifiers and moved the routing to `slopvac compile`, where the counts are reported.

## line 481 — `ste-punctuation.semicolon-used` (suggestion)

The semicolon is not permitted. Write two sentences.

Line as written:

> - `figurative-verb-verdict-remainder`, lines 456-457: the arithmetic the finding asks for (what the mean becomes at one category of 40 and twenty of 100) is not in subject.md; I replaced the metaphor with the 22-of-23 count instead.

## line 483 — `prose-scope.rejected-alternative` (warning)

rejected alternative: rather than deleting them, because -- state what it does; the decision belongs in an ADR, spec, or commit

Line as written:

> - `over-writing-remainder`, lines 284-287: I compressed the rejected alternatives and gave them the real globs rather than deleting them, because they are the only statement in the document of why precedence is file order.

## line 483 — `ste-descriptive.sentence-too-long-descriptive` (warning)

This sentence has 30 words. Use twenty-five or fewer.

Line as written:

> - `over-writing-remainder`, lines 284-287: I compressed the rejected alternatives and gave them the real globs rather than deleting them, because they are the only statement in the document of why precedence is file order.

