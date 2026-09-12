# AI-corpus ground-truth label audit

## Summary
- Checked all 17 documents line by line (11,644 words in the assignment corpus; baseline JSON records 878 findings).
- Recorded 941 editor-cut AI-tell/prose-defect labels; 409 baseline findings are compatible true positives and 469 are FP candidates.
- Line-level finding precision = 46.6%; label recall (baseline catch rate) = 37.5%.
- The largest observed FP clusters are contraction/omission, first-person voice, em-dash, passive voice, and term-rotation heuristics; the largest FN clusters are marketing puffery, boilerplate framing, and formatting spray.

## Findings

### F1: AI gate misses conspicuous marketing register
- surface: independent__marketing-feature-flags.md:3-49 and unguided README lines listed in labels
- kind: fn-gap
- evidence: “Flagpost is the hosted feature-flag service built for the people who own the platform, not just the feature.” (independent__marketing-feature-flags.md:3); “Free for 3 seats and 25 flags, forever. No credit card. Production-ready in an afternoon.” (:49). These lines carry puffery/unsupported-evaluative/fake-specificity/slop-lexicon labels; several have no compatible baseline finding.
- proposal: Add judgement coverage for evidence-backed promotional claims, customer-proof claims, and unsupported superlatives; keep numeric claims only when sourced or explicitly marked as examples.
- expected effect: FN↓, on independent marketing and unguided README corpora
- confidence: high

### F2: Boilerplate framing and closers evade deterministic checks
- surface: unguided__guide-migration.md:7,17,76-78; unguided__api-docs-webhook.md:5,81; unguided__runbook-failover.md:61
- kind: fn-gap
- evidence: “In this guide, we'll walk you through everything you need to know.” (:7); “And that's it! Migration should be straightforward for most users.” (:76); “That covers the essentials of our webhook system!” (api-docs-webhook.md:81). These are labeled filler-opener/quotable-closer/reassurance while often lacking matching findings.
- proposal: Add judgement rules for meta-narration, summary-closer frames, and reassurance; avoid firing on genuinely necessary orientation text.
- expected effect: FN↓, on unguided guides/runbooks
- confidence: high

### F3: Baseline overfires on valid technical/legal prose
- surface: independent__spec-resumable-upload.md, independent__legal-dpa-notice.md, independent__design-doc-outbox.md
- kind: fp-risk
- evidence: “The key words MUST, MUST NOT, REQUIRED, SHALL, SHOULD, SHOULD NOT, MAY, and OPTIONAL…” (spec:21) and “For all Customer Data ingested into the Service, the Customer acts as Controller…” (legal:12) are normative/legal prose. Passive voice, term rotation, long-sentence, and enumerative matches are labeled context-appropriate or density-only, with many findings recorded as FP candidates.
- proposal: Gate STE/style rules by genre or mark normative specs/legal notices as advisory; reserve AI-tell rules for rhetorical shape rather than required terminology.
- expected effect: FP↓, especially independent spec/legal/design docs
- confidence: high

### F4: Ordinary punctuation and voice heuristics swamp useful signals
- surface: prose-format.no-unicode-dash, ste-sentences.omitted-word-or-contraction, prose-craft.first-person-plural, ste-verbs.passive-voice
- kind: fp-risk
- evidence: “This isn't really a regression, it's the opposite.” (issue-comment-pgbouncer.md:3) and “Webhooks are delivered as HTTP POST requests…” (api-docs-webhook.md:9) are grammatical/contextual. Baseline records 93 omission/contraction, 84 first-person-plural, 67 em-dash, and 48 passive findings; many are FP candidates.
- proposal: Narrow contractions/omission matching to verified grammar defects, require conspicuous repeated dash/emphasis patterns, and exempt normative passive voice and issue-comment first person by genre.
- expected effect: FP↓, across all three corpora; particularly AI technical docs
- confidence: high

### F5: Lists are useful when they are operational, not ornamental
- surface: ai-tells-structure.tricolon-abuse-core and ste-sentences.complex-text-not-in-vertical-list
- kind: fp-risk
- evidence: “The protocol comprises four operations: creation … offset negotiation … chunk transmission … integrity verification” (spec:39-42) is a real protocol index; “Define policy once and let it apply everywhere: require two-person approval … cap rollouts … force an expiry date …” (marketing:23) is operational but rhythmically dense. The same deterministic list rule hits both useful structure and AI tricolon rhetoric.
- proposal: Keep tricolon judgement focused on ornamental parallelism; do not treat protocol tables/section indexes as violations.
- expected effect: both (FP↓ on specs, FN↓ on ornamental prose)
- confidence: medium


## Per tell_type
| tell_type | labeled | caught (TP) | missed (FN) |
|---|---:|---:|---:|
| `bold-spray` | 12 | 1 | 11 |
| `cataphoric-lead-in` | 5 | 4 | 1 |
| `chat-residue` | 3 | 2 | 1 |
| `contrastive-negation` | 1 | 1 | 0 |
| `em-dash` | 19 | 13 | 6 |
| `emoji` | 15 | 11 | 4 |
| `fake-specificity` | 8 | 1 | 7 |
| `filler-opener` | 38 | 9 | 29 |
| `first-person-plural` | 23 | 13 | 10 |
| `future-tense-roadmap` | 8 | 6 | 2 |
| `hedge` | 22 | 8 | 14 |
| `hedge-both-ways` | 5 | 3 | 2 |
| `history-narration` | 20 | 4 | 16 |
| `label-colon-bullet` | 94 | 20 | 74 |
| `other:article-omission` | 2 | 2 | 0 |
| `other:catalogue-density` | 29 | 5 | 24 |
| `other:code-discussion` | 5 | 0 | 5 |
| `other:conditional-instruction` | 31 | 31 | 0 |
| `other:design-density` | 21 | 0 | 21 |
| `other:editorial-compression` | 30 | 16 | 14 |
| `other:figurative` | 3 | 0 | 3 |
| `other:italicised-copula` | 1 | 0 | 1 |
| `other:legal-enumeration` | 5 | 2 | 3 |
| `other:meta-narration` | 1 | 0 | 1 |
| `other:normative-density` | 11 | 1 | 10 |
| `other:omitted-conjunction` | 10 | 10 | 0 |
| `other:procedural-clarity` | 25 | 15 | 10 |
| `other:semicolon` | 18 | 18 | 0 |
| `other:spelling` | 6 | 6 | 0 |
| `other:think-of-it-as` | 1 | 0 | 1 |
| `passive-agentless` | 19 | 8 | 11 |
| `puffery` | 21 | 2 | 19 |
| `quotable-closer` | 19 | 0 | 19 |
| `reassurance` | 19 | 4 | 15 |
| `rhetorical-question` | 2 | 1 | 1 |
| `sentence-too-long` | 169 | 94 | 75 |
| `slop-lexicon` | 51 | 19 | 32 |
| `title-case-heading` | 103 | 6 | 97 |
| `tricolon` | 17 | 5 | 12 |
| `unsupported-evaluative` | 49 | 12 | 37 |

## Per rule
| rule | findings | TP | FP |
|---|---:|---:|---:|
| `ai-tells-content-shape.durable-vocabulary-habits` | 7 | 4 | 3 |
| `ai-tells-content-shape.fake-specificity` | 1 | 1 | 0 |
| `ai-tells-figurative.figurative-falls` | 1 | 0 | 1 |
| `ai-tells-formatting.bold-spray` | 6 | 0 | 6 |
| `ai-tells-formatting.em-dash-density` | 11 | 1 | 10 |
| `ai-tells-formatting.emoji-list-markers` | 11 | 11 | 0 |
| `ai-tells-formatting.italicised-copula` | 1 | 0 | 1 |
| `ai-tells-formatting.title-case-heading` | 5 | 4 | 1 |
| `ai-tells-register.corporate-analytic-filler-core` | 2 | 2 | 0 |
| `ai-tells-register.intensifier-tics-core` | 5 | 3 | 2 |
| `ai-tells-register.uniform-paragraph-mass` | 3 | 0 | 3 |
| `ai-tells-structure.cataphoric-lead-in-core` | 6 | 3 | 3 |
| `ai-tells-structure.contrastive-inversion-frames` | 1 | 1 | 0 |
| `ai-tells-structure.emphasis-paragraph-metric` | 18 | 8 | 10 |
| `ai-tells-structure.meta-narration-frames` | 4 | 4 | 0 |
| `ai-tells-structure.rhetorical-question-transition` | 1 | 1 | 0 |
| `ai-tells-structure.summary-closer-frames` | 2 | 1 | 1 |
| `ai-tells-structure.think-of-it-as-core` | 1 | 0 | 1 |
| `ai-tells-structure.tricolon-abuse-core` | 11 | 5 | 6 |
| `docs-discipline.history-narration` | 12 | 4 | 8 |
| `docs-discipline.internal-refs` | 2 | 0 | 2 |
| `docs-discipline.status-language` | 5 | 4 | 1 |
| `orwell.unsupported-evaluative` | 7 | 5 | 2 |
| `prose-agency.anthropomorphism` | 2 | 0 | 2 |
| `prose-craft.dead-opener` | 2 | 0 | 2 |
| `prose-craft.directional-ref` | 1 | 1 | 0 |
| `prose-craft.first-person-plural` | 84 | 31 | 53 |
| `prose-craft.future-tense` | 30 | 6 | 24 |
| `prose-craft.gerund-heading` | 1 | 1 | 0 |
| `prose-craft.hyphens` | 3 | 0 | 3 |
| `prose-craft.latinisms` | 4 | 0 | 4 |
| `prose-craft.link-text` | 1 | 1 | 0 |
| `prose-craft.politeness` | 8 | 2 | 6 |
| `prose-craft.relative-date` | 2 | 0 | 2 |
| `prose-craft.sentence-length` | 13 | 12 | 1 |
| `prose-craft.unclear-antecedent` | 8 | 2 | 6 |
| `prose-craft.versions` | 1 | 0 | 1 |
| `prose-craft.wordiness` | 3 | 0 | 3 |
| `prose-discipline.bidirectional-hedge` | 3 | 3 | 0 |
| `prose-discipline.frozen-verb` | 1 | 0 | 1 |
| `prose-discipline.hedged-hedge` | 1 | 1 | 0 |
| `prose-discipline.marketing-lexicon` | 3 | 3 | 0 |
| `prose-discipline.phrasal-verb` | 3 | 0 | 3 |
| `prose-discipline.run-on` | 1 | 1 | 0 |
| `prose-discipline.term-rotation-signal` | 23 | 0 | 23 |
| `prose-format.no-unicode-dash` | 67 | 14 | 53 |
| `prose-format.prose-block` | 2 | 0 | 2 |
| `prose-inflation.borderline-hype` | 10 | 8 | 2 |
| `prose-inflation.business-jargon` | 3 | 3 | 0 |
| `prose-inflation.document-preamble` | 3 | 2 | 1 |
| `prose-inflation.hedge-stack` | 4 | 4 | 0 |
| `prose-inflation.intensifier` | 3 | 0 | 3 |
| `prose-inflation.nominalized-verb` | 1 | 0 | 1 |
| `prose-inflation.slop-lexicon` | 15 | 11 | 4 |
| `prose-inflation.vague-quantifier` | 8 | 6 | 2 |
| `prose-scope.unrequested-reassurance` | 4 | 4 | 0 |
| `ste-descriptive.sentence-too-long-descriptive` | 57 | 53 | 4 |
| `ste-nouns.multiword-noun-too-long` | 36 | 29 | 7 |
| `ste-practices.false-friend-term` | 7 | 2 | 5 |
| `ste-practices.latin-abbreviation` | 7 | 0 | 7 |
| `ste-practices.omitted-conjunction-that` | 10 | 10 | 0 |
| `ste-practices.phrasal-verb` | 5 | 0 | 5 |
| `ste-practices.unclear-demonstrative-this` | 9 | 0 | 9 |
| `ste-procedural.condition-after-command` | 33 | 33 | 0 |
| `ste-procedural.instruction-not-imperative` | 7 | 7 | 0 |
| `ste-procedural.multiple-instructions-per-sentence` | 9 | 9 | 0 |
| `ste-procedural.sentence-too-long-procedural` | 1 | 1 | 0 |
| `ste-punctuation.colon-terminates-sentence-for-count` | 4 | 3 | 1 |
| `ste-punctuation.hyphen-group-too-long` | 1 | 0 | 1 |
| `ste-punctuation.hyphen-missing-in-compound-modifier` | 1 | 1 | 0 |
| `ste-punctuation.semicolon-used` | 18 | 18 | 0 |
| `ste-sentences.complex-text-not-in-vertical-list` | 31 | 26 | 5 |
| `ste-sentences.missing-article-or-determiner` | 2 | 2 | 0 |
| `ste-sentences.omitted-word-or-contraction` | 93 | 4 | 89 |
| `ste-verbs.auxiliary-stacking` | 6 | 3 | 3 |
| `ste-verbs.complex-tense` | 21 | 9 | 12 |
| `ste-verbs.nominalized-action` | 2 | 0 | 2 |
| `ste-verbs.passive-voice` | 48 | 10 | 38 |
| `ste-words.approved-word-substitution` | 11 | 2 | 9 |
| `ste-words.obligation-word-substitution` | 11 | 2 | 9 |
| `ste-words.slang-or-jargon-term` | 1 | 1 | 0 |
| `ste-words.spelling` | 6 | 6 | 0 |

## Totals
- Findings: 878; TP: 409; FP: 469; finding precision: `0.466`.
- Labels: 941; caught: `353`; missed: `588`; line-level recall: `0.375`.

## 30 most consequential FN spans
1. `independent__marketing-feature-flags.md:3` **puffery** — “**Flagpost is the hosted feature-flag service built for the people who own the platform, not just the feature.** Sub-mil”
2. `independent__marketing-feature-flags.md:11` **puffery** — “Your Go services, your Python data jobs, your React apps, and that one Java monolith nobody names out loud — they all re”
3. `independent__marketing-feature-flags.md:13` **puffery** — “Flags are declared as code, reviewed in pull requests, and synced to the control plane on merge. Drift between what's in”
4. `independent__marketing-feature-flags.md:3` **unsupported-evaluative** — “**Flagpost is the hosted feature-flag service built for the people who own the platform, not just the feature.** Sub-mil”
5. `independent__release-notes-4-0.md:17` **unsupported-evaluative** — “That worked fine right up until it didn't — the classic failure being a”
6. `independent__release-notes-4-0.md:36` **unsupported-evaluative** — “Backoff is decorrelated jitter now, capped at 20 seconds by default. If you had”
7. `independent__release-notes-4-0.md:17` **slop-lexicon** — “That worked fine right up until it didn't — the classic failure being a”
8. `independent__release-notes-4-0.md:42` **slop-lexicon** — “`upload()` used to buffer. If you handed it a 4 GB file, it read the whole”
9. `unguided__readme-cache.md:3` **slop-lexicon** — “**Semantic caching for LLM applications — because your users don't phrase things the same way twice.**”
10. `unguided__readme-cache.md:3` **bold-spray** — “**Semantic caching for LLM applications — because your users don't phrase things the same way twice.**”
11. `unguided__readme-cache.md:9` **bold-spray** — “- 🚀 **Blazing fast** — sub-millisecond lookups on the in-memory backend”
12. `unguided__readme-cache.md:10` **bold-spray** — “- 🎯 **Semantically aware** — catches paraphrases, typos, and reorderings that exact caches miss”
13. `dogfood__README.contaminated.md:184` **tricolon** — “per-profile density budgets, and a `recommended_for` list of genres. The 23 ids”
14. `dogfood__README.contaminated.md:248` **tricolon** — “The 150 checked rules produce findings, gate a build, and agree between two runs”
15. `unguided__adr-queue.md:20` **tricolon** — “A second managed option was also considered but was rejected on cost at our expected volume. While it offered a somewhat”
16. `unguided__pr-description.md:30` **hedge-both-ways** — “Happy to discuss any of the design decisions here! I went back and forth on whether the timeout should be configurable p”
17. `unguided__pr-description.md:32` **hedge-both-ways** — “This is a first step towards a broader effort to improve our data layer. More to come!”
18. `independent__blog-skip-locked.md:3` **filler-opener** — “I spent last Saturday and most of Sunday ripping Redis out of our background”
19. `independent__blog-skip-locked.md:5` **filler-opener** — “weird SQL clause. I went in expecting a slog and came out mildly annoyed that”
20. `independent__blog-skip-locked.md:8` **filler-opener** — “Here's how it went, and the parts that bit me.”
21. `independent__tutorial-mtls.md:150` **quotable-closer** — “A test that can't fail proves nothing. Drop the client certificate:”
22. `independent__tutorial-mtls.md:167` **quotable-closer** — “Two different failures, two different causes — that's your confirmation that”
23. `unguided__api-docs-webhook.md:81` **quotable-closer** — “That covers the essentials of our webhook system! With signature verification and idempotent handling in place, you shou”
24. `independent__tutorial-mtls.md:56` **reassurance** — “This is the "mutual" half — the client proves who it is, too.”
25. `independent__tutorial-mtls.md:150` **reassurance** — “A test that can't fail proves nothing. Drop the client certificate:”
26. `unguided__api-docs-webhook.md:81` **reassurance** — “That covers the essentials of our webhook system! With signature verification and idempotent handling in place, you shou”
27. `independent__blog-skip-locked.md:90` **rhetorical-question** — “## Would I recommend it”
28. `unguided__readme-parser.md:41` **cataphoric-lead-in** — “When parsing fails, you get an error that actually tells you something useful:”
29. `unguided__guide-migration.md:76` **future-tense-roadmap** — “And that's it! Migration should be straightforward for most users. If you run into any issues, don't hesitate to open an”
30. `unguided__pr-description.md:32` **future-tense-roadmap** — “This is a first step towards a broader effort to improve our data layer. More to come!”

## Score vs judged slop
| document | linter score | baseline findings | judged slop reading |
|---|---:|---:|---|
| `unguided__adr-queue.md` | 0.0 | 63 | medium-high |
| `unguided__guide-migration.md` | 0.0 | 71 | high |
| `unguided__pr-description.md` | 0.0 | 57 | high |
| `unguided__error-message.md` | 3.2 | 32 | very high |
| `unguided__readme-cache.md` | 10.2 | 68 | very high |
| `unguided__api-docs-webhook.md` | 15.7 | 54 | medium-high |
| `unguided__readme-parser.md` | 19.5 | 45 | high |
| `unguided__runbook-failover.md` | 32.5 | 37 | medium-high |
| `independent__issue-comment-pgbouncer.md` | 52.4 | 35 | low-medium |
| `independent__marketing-feature-flags.md` | 56.6 | 43 | very high |
| `independent__tutorial-mtls.md` | 58.1 | 40 | low |
| `independent__blog-skip-locked.md` | 64.3 | 60 | low |
| `independent__release-notes-4-0.md` | 65.2 | 52 | low-medium |
| `independent__legal-dpa-notice.md` | 65.5 | 62 | low |
| `independent__design-doc-outbox.md` | 71.6 | 53 | low |
| `independent__spec-resumable-upload.md` | 76.0 | 48 | low |
| `dogfood__README.contaminated.md` | 87.7 | 58 | medium-high |

Best linter score is dogfood README (87.7), despite medium-high judged contamination from dense catalogue/meta prose; worst scores are ADR and migration guide (0.0) even though their slop is medium-high rather than uniformly severe. The marketing page (56.6) and error message (3.2) are high-slop by editorial judgment; the score ordering partly agrees but gives technical/legal documents middling scores because generic STE rules dominate.

## Decommission candidates
- `ste-sentences.omitted-word-or-contraction`: 93 findings, 89 FP candidates; ordinary contractions such as “we'll”, “doesn't”, and “they're” dominate. Narrow to a real omitted-conjunction grammar pattern or demote heavily.
- `prose-craft.first-person-plural`: 84 findings, 53 FP candidates; first-person voice is intentional in issue comments, design docs, and essays. Make genre-aware or advisory.
- `prose-format.no-unicode-dash`: 67 findings, 53 FP candidates; ordinary em-dash punctuation is not equivalent to AI dash density. Replace with a density/cluster judgement.
- `ste-verbs.passive-voice`: 48 findings, 38 FP candidates; passive is appropriate in protocol/legal/normative prose. Keep only for agentless action where attribution matters.
- `prose-discipline.term-rotation-signal`: 23 findings, all FP candidates under this ground truth; repeated terms are required in legal/technical docs. Remove or restrict to unexplained synonym alternation.

## Checked and fine
- Corpus inventory and baseline join covered all 17 AI documents and all 878 baseline findings.
- Distinct emoji-list, bold-spray, title-case-heading, fake-specificity, rhetorical-question, and summary-closer patterns were separately labeled.
- Normative spec/legal repetition was separated from conspicuous marketing and reassurance language.
- The 30-FN list is drawn only from labels with no compatible baseline finding.
