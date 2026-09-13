# Rule, steering, and code audit, 2026-09-12

Every number in this report comes from a JSON run under `runs/` or from a file under
`agent-reports/`; the corpora are under `corpus/`. Baseline means the rules and code at
`origin/main` (`3c99532`, slopvac 2.2.0); new means this branch.

## What was asked

Review the deterministic and judgement rules and the two skills, find improvements and
rules to retire, catch the cross-sentence "X is A. X is not B." tell, audit the code and
architecture, challenge every finding adversarially, and measure the result against
prose that has already been through the gate and against fresh content from several
models, including false positives and false negatives.

## Method

Eleven audit agents read the rules, the skills, and the code from separate angles
(`agent-reports/RegexAiTells.md`, `RegexSte.md`, `TellsCoverage.md`, `JudgementRules.md`,
`Steering.md`, `HumanFpLabels.md`, `AiFnLabels.md`, `CodeEngine.md`, `CodePipeline.md`,
`CodeVale.md`, `CodeTestsCi.md`). Four adversarial challengers then attacked those
reports (`ChallengeRules.md`, `ChallengeSteering.md`, `ChallengeCode.md`,
`FnRootCause.md`); only proposals that survived were implemented. A final challenger
reviewed the finished diff (`FinalChallenge.md`) and found eleven defects, all fixed
before the PR; the section "Final challenge" lists them.

### Corpora

| Corpus | Docs | Words | What it is |
|---|--:|--:|---|
| `human` | 11 | 21,208 | pre-2022 human technical prose: ripgrep GUIDE and README (13.0.0), redis README (6.2.0), fzf README (0.27.0), black README (21.9b0), rich README (2020), git SubmittingPatches (2.33), requests README (2.25), annotated-types README, markdown-it-py README, one hand-written README. Findings here are false-positive candidates. |
| `slopvacced` | 22 | 30,488 | prose from repositories already gated by slopvac: this repository's READMEs, docs and skills; agentic-scaffold README and docs; omp-orchestrate README and skill; omp-plugins README. A gate regression shows up here first. |
| `ai-existing` | 17 | 9,865 | the model documents already in `evals/` (unguided runs, independent set, contaminated dogfood README). Labelled span by span by an agent: 941 tell labels, 469 findings judged false positives (`agent-reports/AiFnLabels-labels.json`, `AiFnLabels-fp.json`). |
| `generated/01-unguided` | 48 | 39,976 | 8 topics x 6 models, no style guidance. |
| `generated/02-steered-current` | 47 | 18,428 | the same, with the write-docs sentence rules and genre reference at `origin/main` in the system prompt. |
| `generated/03-steered-new` | 47 | 17,920 | the same, with this branch's sentence rules. |

Models: `anthropic-haiku45`, `anthropic-sonnet5`, `anthropic-opus5-high`, `openai-luna`
(gpt-5.6-luna), `openai-sol-medium`, `openai-sol-high` (gpt-5.6-sol at two reasoning
levels). Generation ran headless (`omp -p --no-tools --no-session --no-skills --no-rules
--no-extensions`, memory disabled by config overlay, fresh working directory) so no
skill, rule, or memory reached the writer; the isolation was probed before the run
(`corpus/generated/MANIFEST.json` holds the prompts and system text). One generation
per cell; one of 96 steered cells failed twice and is absent.

Word counts are the linter's (`summary.words`), so they differ from a plain split.

## Results

### Gate at `normal`, baseline against new

| Corpus | Docs | Words | Errors | Warnings | Suggestions | Findings/100w | Score | Gate pass |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| human | 11 | 21,208 | 132 -> 64 | 1592 -> 481 | 408 -> 1298 | 10.05 -> 8.69 | 55.0 -> 72.4 | 0 -> 1 |
| slopvacced | 22 | 30,488 | 0 -> 0 | 693 -> 320 | 291 -> 627 | 3.23 -> 3.11 | 86.3 -> 89.6 | 19 -> 20 |
| ai-existing | 17 | 9,865 | 139 -> 135 | 561 -> 187 | 178 -> 552 | 8.90 -> 8.86 | 57.7 -> 68.0 | 1 -> 2 |
| gen-unguided | 48 | 39,976 | 203 -> 181 | 2051 -> 558 | 924 -> 2171 | 7.95 -> 7.28 | 64.4 -> 76.0 | 8 -> 13 |
| gen-steered-current | 47 | 18,428 | 42 -> 33 | 664 -> 202 | 389 -> 719 | 5.94 -> 5.18 | 74.6 -> 83.1 | 21 -> 30 |
| gen-steered-new | 47 | 17,920 | 47 -> 39 | 636 -> 164 | 385 -> 705 | 5.96 -> 5.07 | 74.7 -> 83.9 | 23 -> 28 |

Error density per 1,000 words, the number `max_errors = 0` gates on: human 6.22 -> 3.02,
unguided model prose (`ai-existing`) 14.09 -> 13.68. The model:human ratio rose from
2.3x to 4.5x. Warnings on human prose fell 1,592 -> 481 while the model corpora kept
their errors; the difference moved to suggestions, which lower a score by at most 15
points and never fail a run. The error totals are compositions: on `ai-existing`,
`compound-preposition` (-8, a policy demotion), `durable-vocabulary-habits` (-4, a
detector narrowing) and `emphasis-paragraph-metric` (-1, retired) were offset by
`summary-closer-frames` (+5, new tokens) and `dead-opener` (+2, the rule now runs);
per rule, `runs/per_rule_old_new.json`.

Five more unguided model documents pass the `normal` gate than before. All five had
zero errors under both rule sets and failed only on the density of STE rules
(`passive-voice`, `condition-after-command`, `multiword-noun-too-long`) that fire more
often on human prose than on model prose; they pass now for the same reason a human
README does. The judgement pass in `review-docs` is where those documents are meant to
be caught, and this branch makes that step executable (below).

### Labelled false positives and false negatives (`ai-existing`)

Joined at paragraph granularity because the baseline engine reported every finding in a
multi-line paragraph at the paragraph's first line (fixed in this branch).

| Measure | Baseline | New |
|---|--:|--:|
| findings inside a labelled paragraph (precision) | 0.951 | 0.941 |
| labelled paragraphs with at least one finding (recall) | 0.709 | 0.732 |
| findings the labeller judged false positives (469) still reported as error or warning | 469 | 173 |
| of which gone | | 49 |
| of which now suggestions | | 247 |
| findings the labeller judged true positives (367 rule-paragraph keys) that no longer fire | | 12 |
| of which now suggestions | | 101 |

Of the 173 kept false-positive findings, 53 are Unicode dashes and 10 dash density: the
labeller called every em dash "ordinary punctuation", the challenger showed the dash
is 15x denser in model READMEs than in human READMEs, and the rule stays an error (see
"Decisions"). The 12 lost true positives are 8 `emphasis-paragraph-metric` (retired: it
fired 4x more on human prose than on model prose), 3 `auxiliary-stacking` (the
two-auxiliary branch was a duplicate of `passive-voice`), and 1 emoji that was not a
list marker. The 101 demotions are STE and voice rules that still run at `strict`.

Human corpus labels (`agent-reports/HumanFpLabels-labels.json`, 352 sampled findings):
of 251 labelled false positives, 39 are gone and 78 are suggestions now; of 101 labelled
true positives, 85 report at the same severity, 8 are suggestions and 3 are gone. The
challenger's point stands and is recorded: almost every "false positive" on human prose
was a real match of the pattern the rule names (a real passive, a real contraction), so
these are profile decisions, not detector repairs, and `strict` keeps them.

### Already-gated repositories

Each repository was linted with its own configuration, baseline against new:

| Repository | Baseline | New |
|---|---|---|
| this repository (README, lint README, docs, skills, eval report; own `slopvac.toml`) | 0 errors, passed | 0 errors, 6 warnings, score 92.0, passed |
| agentic-scaffold (README, docs; own `slopvac.toml`) | 0 errors, 40 warnings, 90.3 | 0 errors, 35 warnings, 90.6 |
| omp-orchestrate (README, orchestrate skill; `normal`) | 0 errors, 16 warnings, 93.7 | 0 errors, 7 warnings, 94.5 |
| omp-plugins (README; `normal`) | 0 errors, 2 warnings, 97.9 | 0 errors, 0 warnings, 99.2 |

### Per model, new rules

| Model | Condition | Docs | Words | Findings/100w | Errors | Mean score | Gate pass |
|---|---|--:|--:|--:|--:|--:|--:|
| anthropic-haiku45 | unguided | 8 | 4,623 | 10.19 | 41 | 70.2 | 0/8 |
| anthropic-haiku45 | steered (old skill text) | 8 | 2,964 | 6.82 | 15 | 78.1 | 2/8 |
| anthropic-haiku45 | steered (new skill text) | 8 | 3,236 | 6.98 | 16 | 78.2 | 4/8 |
| anthropic-sonnet5 | unguided | 8 | 5,532 | 9.85 | 78 | 64.5 | 0/8 |
| anthropic-sonnet5 | steered (old skill text) | 8 | 2,486 | 5.03 | 9 | 81.8 | 4/8 |
| anthropic-sonnet5 | steered (new skill text) | 8 | 2,179 | 4.96 | 6 | 83.0 | 5/8 |
| anthropic-opus5-high | unguided | 8 | 7,482 | 5.91 | 34 | 77.1 | 2/8 |
| anthropic-opus5-high | steered (old skill text) | 8 | 3,803 | 3.63 | 8 | 86.9 | 5/8 |
| anthropic-opus5-high | steered (new skill text) | 8 | 3,927 | 3.62 | 11 | 86.3 | 3/8 |
| openai-luna | unguided | 8 | 8,556 | 6.57 | 11 | 80.0 | 2/8 |
| openai-luna | steered (old skill text) | 7 | 2,867 | 5.79 | 0 | 83.8 | 7/7 |
| openai-luna | steered (new skill text) | 7 | 3,246 | 5.55 | 6 | 81.9 | 4/7 |
| openai-sol-medium | unguided | 8 | 6,905 | 6.78 | 10 | 82.1 | 5/8 |
| openai-sol-medium | steered (old skill text) | 8 | 3,260 | 4.72 | 0 | 86.0 | 6/8 |
| openai-sol-medium | steered (new skill text) | 8 | 2,384 | 4.99 | 0 | 87.3 | 6/8 |
| openai-sol-high | unguided | 8 | 6,878 | 6.14 | 7 | 82.0 | 4/8 |
| openai-sol-high | steered (old skill text) | 8 | 3,048 | 5.54 | 1 | 85.4 | 6/8 |
| openai-sol-high | steered (new skill text) | 8 | 2,948 | 4.51 | 0 | 84.6 | 6/8 |

The anthropic models write denser slop unguided than the openai models on this
linter's terms (10.1 and 9.8 findings per 100 words for haiku and sonnet against 6.1 to
6.7 for the gpt-5.6 variants); steering closes most of the gap. Reasoning level moved
opus and sol only slightly. One generation per cell: differences under one finding per
100 words are noise.

### Steering: old skill text against new

| Condition | Docs | Words | Findings/100w | Score | Errors | Semicolons | Omitted `that` | Sentences > 25 words | Unicode dashes |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| unguided | 48 | 39,976 | 7.28 | 76.0 | 181 | 115 | 104 | 101 | 150 |
| old steering | 47 | 18,428 | 5.18 | 83.1 | 33 | 35 | 59 | 17 | 32 |
| new steering | 47 | 17,920 | 5.07 | 83.9 | 39 | 14 | 61 | 20 | 34 |
| new steering + `that` bullet | 48 | 18,066 | 5.07 | 83.3 | 34 | 24 | 38 | 26 | 33 |

A fourth arm (`corpus/generated/04-steered-that`, run after the first report) added
one bullet, "Keep the conjunction `that` where it opens a clause", to the new
steering. Omitted `that` fell 61 -> 38 across 48 documents; semicolons rose 14 -> 24,
still under the old steering's 35. One generation per cell, so the semicolon movement
is inside the range two arms with the same guard can differ by; the `that` movement is
the targeted effect and the bullet ships in `write-docs`.

Between the first two steered arms the sentence rules differ in one bullet (the word cap now
says "split into two sentences, never a semicolon or a dropped `that`"), and semicolons
fell from 35 to 14 across the same eight topics and six models. With one generation per
cell that is an association, not a controlled effect; the direction and size match the
2025 eval, which attributed the semicolon rise to the compression instruction. Omitted
`that` did not move (59 -> 61), so that half of the guard is unproven and stays only
because it costs one clause (follow-up filed).

### The new rule

`ai-tells-structure.definitional-negation-pair` catches the two-sentence contrast the
single-sentence rule stops at: "X is A. X is not B.", "X is not A. It is B.", "The
question is not whether A. It is whether B.", "not because A, but because B", across
`.`, `;`, `:` and a dash, with the subject repeated or pronominalised. The negated half
must open with a definitional marker (an article, `about`, `just`, `whether`, ...), so
"It is not configurable" states a property and does not fire.

| Corpus | Hits |
|---|--:|
| human (21,208 parsed words) | 0 |
| slopvacced (30,488 parsed words) | 0 |
| ai-existing (17 docs) | 1: `It's not just a performance optimization -- it's a fundamental rethinking` |
| generated, unguided (48 docs) | 4, all judged tells: `The monorepo is a source-control and coordination boundary. It is not a requirement to combine services`; `The relevant question is not whether ... It is whether ...`; `The user-level plugin is not loaded at all; it is replaced, not merged`; `Not because we like generated code in review, but because` |
| generated, steered (94 docs) | 0 |
| 10 property-negation corrections ("The limit is 100 requests per minute. It is not configurable.", "The token is a JWT. It is not encrypted; verify the signature.", ...) | 0 |
| 15 definitional distinctions of the exact shape, written to be kept ("The lock is a lease. It is not a mutex.") | 15 at PR #56; 1 after PR #58 |
| 12 constructed tells ("Testing is not a phase. It is a habit.", "Security is not a checkbox. It is a process.", ...) | 12 at PR #56; 8 after PR #58 |

PR #58 narrowed the rule after the challenger's objection below: the negated half must now
open with a rhetorical marker (`about`, `just`, `whether`, `because`, ...) or with an
article and one of the nouns the tell reaches for (`a requirement`, `an afterthought`, `a
checkbox`, `a silver bullet`, `a guarantee`, ...). The one distinction that still fires is
"The response is an acknowledgement. It is not a guarantee that the operation completed.",
because `a guarantee` is on that list. The four tells it stops catching have a negated
half that opens with neither: a bare complement ("The goal is not speed. It is
correctness.", "The cache is not a source of truth. It is an optimization.") or an
article and a concrete noun off the list ("The parser is a library. It is not a
compiler.", "The gate isn't a judge -- it's a filter.", an em dash in the probe). The
last two are the distinctions' own shape, and the first two would need a marker list
for every noun. Those stay with the reviewer's judgement remainder
(`ai-tells-structure.contrastive-inversion-remainder`). All five model-corpus hits
survive the narrowing. `tests/test_engine.py` (`DEFINITIONAL_*`) pins the boundary: the
14 kept distinctions must not fire, the 8 rhetorical tells must, and the accepted fire is
named. The four misses are recorded here only; a test asserting them would pin the
current pattern's reach, not a contract.

The distinctions row is the rule's limit and the final challenger's strongest objection: no
pattern separates a strawman restatement from a genuine definitional distinction of
the same shape. What separates them in the corpora is frequency (0 in 51k parsed words
of human and gated prose against 5 in the model corpora), so the rule is a warning the
reviewer settles, never an error, and carries a `factual-correction` exception for the
sentence a writer keeps. It runs natively at paragraph scope. Vale's paragraph scope is the
CommonMark paragraph node only, so a paragraph-scoped rule compiled to Vale reported 0 of
3 on a bullet, a numbered item and a quote carrying the tell; every paragraph-scoped
lexical rule now stays native for that reason.

## Decisions

### Rules changed at `normal` (35 rules; `runs/per_rule_old_new.json`)

| Rule | human | gated | ai-existing | generated (unguided) | severity at normal |
|---|--:|--:|--:|--:|---|
| `ai-tells-content-shape.durable-vocabulary-habits` | 15 -> 3 | 0 -> 0 | 7 -> 6 | 12 -> 1 | error -> suggestion |
| `ai-tells-content-shape.fake-specificity` | 2 -> 1 | 0 -> 0 | 1 -> 1 | 0 -> 0 | error -> error |
| `ai-tells-formatting.bold-spray` | 2 -> 0 | 3 -> 1 | 6 -> 2 | 12 -> 5 | suggestion -> suggestion |
| `ai-tells-formatting.emoji-list-markers` | 1 -> 0 | 0 -> 0 | 11 -> 10 | 0 -> 0 | warning -> warning |
| `ai-tells-formatting.title-case-heading` | 1 -> 27 | 1 -> 5 | 5 -> 51 | 13 -> 123 | suggestion -> suggestion |
| `ai-tells-structure.definitional-negation-pair` | 0 -> 0 | 0 -> 0 | 0 -> 1 | 0 -> 4 | (none) -> warning |
| `ai-tells-structure.emphasis-paragraph-metric` | 80 -> 0 | 35 -> 0 | 18 -> 0 | 190 -> 0 | suggestion -> (removed) |
| `ai-tells-structure.summary-closer-frames` | 1 -> 1 | 0 -> 0 | 2 -> 7 | 0 -> 0 | error -> error |
| `orwell.compound-preposition` | 21 -> 21 | 0 -> 0 | 0 -> 0 | 0 -> 0 | error -> warning |
| `orwell.unsupported-evaluative` | 6 -> 1 | 0 -> 0 | 7 -> 7 | 1 -> 1 | error -> error |
| `prose-agency.false-agency` | 12 -> 2 | 0 -> 0 | 0 -> 0 | 7 -> 3 | warning -> warning |
| `prose-craft.command-prompt` | 80 -> 0 | 0 -> 0 | 0 -> 0 | 1 -> 0 | warning -> (removed) |
| `prose-craft.directional-ref` | 8 -> 8 | 2 -> 2 | 1 -> 1 | 5 -> 5 | warning -> suggestion |
| `prose-craft.first-person-plural` | 115 -> 115 | 0 -> 0 | 84 -> 84 | 209 -> 209 | warning -> suggestion |
| `prose-craft.future-tense` | 105 -> 105 | 2 -> 2 | 30 -> 30 | 54 -> 54 | warning -> suggestion |
| `prose-craft.latinisms` | 44 -> 44 | 0 -> 0 | 4 -> 4 | 18 -> 18 | warning -> suggestion |
| `prose-craft.optional-plural` | 2 -> 2 | 0 -> 0 | 0 -> 0 | 2 -> 0 | warning -> warning |
| `prose-craft.politeness` | 26 -> 26 | 0 -> 0 | 8 -> 8 | 3 -> 3 | warning -> suggestion |
| `prose-craft.self-reference` | 6 -> 6 | 0 -> 0 | 0 -> 0 | 0 -> 0 | warning -> suggestion |
| `prose-craft.spacing` | 48 -> 48 | 0 -> 0 | 0 -> 0 | 0 -> 0 | warning -> suggestion |
| `prose-craft.unclear-antecedent` | 42 -> 42 | 2 -> 2 | 8 -> 8 | 38 -> 38 | warning -> suggestion |
| `prose-craft.versions` | 7 -> 7 | 0 -> 0 | 1 -> 1 | 3 -> 3 | warning -> suggestion |
| `prose-discipline.term-rotation-signal` | 1 -> 0 | 7 -> 0 | 23 -> 0 | 111 -> 0 | suggestion -> (removed) |
| `prose-format.prose-block` | 13 -> 13 | 0 -> 0 | 2 -> 2 | 9 -> 9 | error -> suggestion |
| `prose-inclusive.exclusive` | 13 -> 13 | 0 -> 0 | 0 -> 0 | 1 -> 1 | error -> suggestion |
| `prose-scope.implementation-leak` | 0 -> 0 | 0 -> 1 | 0 -> 1 | 15 -> 48 | warning -> warning |
| `ste-nouns.multiword-noun-too-long` | 70 -> 70 | 70 -> 70 | 36 -> 36 | 196 -> 196 | warning -> suggestion |
| `ste-practices.unclear-demonstrative-this` | 47 -> 0 | 3 -> 0 | 9 -> 0 | 36 -> 0 | suggestion -> (removed) |
| `ste-practices.unclear-pronoun` | 11 -> 0 | 0 -> 0 | 0 -> 0 | 2 -> 0 | suggestion -> (removed) |
| `ste-procedural.condition-after-command` | 76 -> 76 | 73 -> 73 | 33 -> 33 | 395 -> 395 | warning -> suggestion |
| `ste-sentences.omitted-word-or-contraction` | 122 -> 122 | 0 -> 0 | 93 -> 93 | 58 -> 58 | warning -> suggestion |
| `ste-verbs.auxiliary-stacking` | 71 -> 1 | 9 -> 1 | 6 -> 1 | 64 -> 1 | warning -> suggestion |
| `ste-verbs.complex-tense` | 51 -> 51 | 22 -> 22 | 21 -> 21 | 104 -> 104 | warning -> suggestion |
| `ste-verbs.nominalized-action` | 11 -> 11 | 10 -> 10 | 2 -> 2 | 20 -> 20 | warning -> suggestion |
| `ste-verbs.passive-voice` | 239 -> 244 | 184 -> 197 | 48 -> 52 | 356 -> 368 | warning -> suggestion |

The severity column is the level the profile resolves, not the rule's shipped field: a
category severity sets every enforced rule in it, which is why a rule that ships at
`warning` inside `prose-format` reported as an error before. `slopvac rules` now prints
that resolved level (`effective_severity` in JSON) next to the shipped one, so the two
no longer disagree in front of a reader.

Changes outside `normal`, which the table above does not show: `tricolon-abuse-core`
is advisory at `strict` too (the regex names a shape, the judgement remainder decides);
at `relaxed`, `versions`, `directional-ref`, `spacing` and `exclusive` went from
enforced to advisory so that `relaxed` is never stricter than `normal`,
`durable-vocabulary-habits` and `unclear-demonstrative-this` from advisory to excluded,
and `command-prompt` from enforced to excluded. `strict` keeps every demoted STE and
voice rule enforced. Two rules are now dialled
below their category by a profile default (`orwell.compound-preposition` to warning at
`normal`; the new rule to warning everywhere), a mechanism this branch adds
(`profiles.py::_NORMAL_RULES`); a project's own `[rules."..."]` entry still wins.

Retired:

- `ai-tells-structure.emphasis-paragraph-metric`, a lone paragraph of eight words or
  fewer: 3.77 per 1,000 words on human prose against 1.82 on model prose, 0.18x with
  the genre held to READMEs.
- `prose-discipline.term-rotation-signal`, which fired on the word "customers": 23 of
  23 model-corpus hits judged false, 0 in model READMEs. The judgement rule
  `competing-actor-terms` keeps the check.
- The three tokenizer definitions in `ste-punctuation` that were listed as judgement
  rules. They define how words are counted; `docs/metrics.md` phases 0 to 8 carry them.
- `prose-craft.command-prompt` at `normal`: 80 hits on human prose, all `$` prompts
  inside code fences, 0 on model prose.

Regex repairs:

- `prose-craft.dead-opener` had a mid-pattern `(?m)` that Python rejects, so the rule
  never ran natively; repaired, it matches 22 human and 2 model passages.
- `passive-voice` treated `often`, `open`, `even`, `seven` as participles.
- `auxiliary-stacking` duplicated `passive-voice` on every "can be cleared".
- `false-agency` lost `lets you` and `helps you`: 9 of 11 human hits, 0 model hits.
- `optional-plural` lost the `/s` branch.
- `emoji-list-markers` requires a list marker.
- `fake-specificity` stops firing on "3.8+ and".
- `durable-vocabulary-habits` stops firing on the noun "features"; "Supported
  Features" headings were 15 of its 15 human hits.
- `title-case-heading` sees two-word headings and stopwords: 5 -> 51 of 143 model
  headings, 0 -> 27 of 191 human headings. Advisory, because humans title-case too.
- `bold-spray` threshold 10 -> 20 per 1,000 words: 0 of 11 human documents, still 2 of
  17 model documents.
- `summary-closer-frames` gained the sign-off closers "happy coding", "and that's it",
  "more to come": 0 human occurrences.
- `unsupported-evaluative` gained a phrase allowlist for "comprehensive test suite"
  and "a more robust preprocessor".

### Kept against the audit's advice

- `prose-format.no-unicode-dash` stays an error at `normal`. Demoting it to warning was
  tried: 11 more of 48 unguided model documents passed the gate, against 6 dashes in
  27k words of human prose. It is the strongest single origin signal measured (24x).
- `ste-descriptive.sentence-too-long-descriptive` stays enforced at `normal`: the
  guided-generation runs show it is the rule the steering most reliably moves, and its
  human and model densities are close (6.3 against 5.8 per 1,000 words), so it is a
  prose-quality rule rather than a false-positive source.
- `docs-discipline.history-narration` and `status-language`: the challenger showed
  1.8x and 0.9x README ratios; kept as warnings, genre-gated by the category's
  `recommended_for`.
- The three narrowing proposals for `passive-voice`, `omitted-conjunction-that` and
  `multiword-noun-too-long` that came without an executable regex were not applied.

### Judgement rules and the skills

`recommended_for` now uses the five genre values the skills classify into
(`consumer`, `internal`, `change-comms`, `reference`, `informal`), typed in the model,
so `review-docs` step 4 selects judgement rules by equality; before, the categories used
two vocabularies and the skill's `consumer` genre selected zero rules. Step 4 now runs
document-scope questions once, paragraph and sentence questions only on passages the gate
or the adversarial read flagged, and skips a `-remainder` question when its mechanical
core fired on the same passage. Both skills name the one `slopvac lint ... --format json`
command, the same genre table, and the exit meanings (0 can carry findings; 2 is an
incomplete run: Vale absent, older than 3.15, disabled in config, or `--no-vale`).
The project-gate selection section that duplicated the config policy is a short pointer.
Judgement-rule `exceptions` are dead metadata (a judgement never emits a suppressible
finding). The JudgementRules agent counted 27 from the `rules --format json` output; the
YAML at the audit baseline (`3c99532`) carries the key on 29 judgement rules, 25 of them
non-empty, and the three tokenizer-contract entries PR #56 removed took it to 26. PR #58
(`f847b027c1`) deleted all 26 `exceptions:` lines; 0 judgement rules carry the key now.

### Code

Fixes that landed, each with a failing-then-passing test (`agent-reports/ChallengeCode.md`
ranked them; `ChallengeCode` also found M1):

- `[vale] enabled = false` skipped 145 rules and exited 0 with `passed = true`; it now
  reports them unchecked and exits 2, the same path as `--no-vale`.
- Findings inside a multi-line paragraph reported the paragraph's first line (492 of the
  human corpus's blocks). `Block.line_starts` maps the normalised block text back to the
  source, lexical rules at prose, sentence, paragraph and document scope match the whole
  block and map offsets to the real line and column, and a suppression annotation before
  a block covers every line of it.
- CLI flags (`--profile`, `--min-score`, `--max-per-100-words`, `--locale`, `--disable`)
  lost to a matching `[[overrides]]` block; they are applied last.
- An `[overrides.thresholds]` block naming one field reset the others to defaults; patch
  models keep omitted fields.
- GitHub annotations and SARIF mapped suggestions to `warning`; now `notice` and `note`.
- A weight-0 category still lowered the document score, could fail `min_score`, and its
  errors still counted toward `max_errors`; excluded from every document gate unless
  every category is weight 0 (the anti-gaming clamp stays). The raw counts stay in the
  report.
- The allowlist accepted a phrase anywhere within 30 characters of a match; it must
  contain the match.
- A malformed `<!-- slopvac-allow` comment was silently ignored; it is reported, while a
  directive quoted in a code span (including one that closes on the next line), a fence
  or front matter is neither honoured nor reported (that quoting is how the README
  documents the grammar, and a quoted `slopvac-disable` used to silence the rest of the
  file). An annotation or `disable-next-line` covers the block that follows it, which is
  what the old first-line positions delivered in practice; the README now says so.
- A match that wraps to the next source line reported an `end_column` past the end of
  its line (9 findings in the black README alone); the range now stops at the line end
  in both the native and the Vale path.
- `[overrides.vale] enabled = false` in a path override was ignored; the resolved Vale
  settings are part of the compile group now, and the unchecked note names the setting
  that skipped Vale rather than always saying `--no-vale`.
- Vale end columns were inclusive while native and SARIF are exclusive.
- A substitution rule with one punctuation-ending key degraded its whole map to an
  `existence` rule and lost every replacement; the map is split and the punctuation keys
  ride in an aliased companion check that reports under the owning rule id (aliased
  vocabulary checks report under their owner now too).
- Nothing checked the documented Vale 3.15 floor and the cache key ignored the Vale
  version; `vale --version` is probed once, a lower version is treated as absent, and the
  version is in the fingerprint and manifest.
- `slopvac init` wrote commented examples the config rejects; vocabulary entries accepted
  misspelled fields and silent duplicates; the README pinned `v2.0.0`; `slopvac compile
  --format json` omitted the check aliases and the Vale version it keyed the cache on.
- `hedge/BaselinelessComparative.yml` escaped `%` as `%%`, which Vale 3.21 no longer
  formats, so the rule matched nothing; the source-text test that enforced `%%` is gone
  and the fixture test that runs Vale is the contract. `docs/vale-traps.md` trap 9 records
  the version dependency.
- Test oracle: every pattern, tokens and substitution rule's bad examples now run through
  `analyze.parse` and the native engine (2.7 s), which found four `prose-craft` rules
  whose examples the native engine cannot reach (marked xfail with the reason, listed
  under follow-ups).

Not done, with the reason (`agent-reports/ChallengeCode.md` "Separate PRs"): the STE
tokenizer and sentence segmenter (`docs/metrics.md` phases 0-9 are not what `count_words`
implements; a rebaseline of every length threshold follows), per-target config discovery
(`load_run_context` reads the first target's config for every file), `text_type` gating of
lexical rules (the classifier defaults a runbook's instructions to descriptive, so gating
would silence the runbook rules), HTML and MDX block prose, the `.rst` path that needs an
undeclared `rst2html`, and the composite-action test harness.

## Final challenge

`agent-reports/FinalChallenge.md` re-derived the headline numbers (they matched) and
challenged the diff. What it found, and what changed:

- The FixPackaging agent had broken the root README's YAML list markers (`* rev:`).
  Fixed.
- The new rule fires on every definitional distinction of its shape. Documented above;
  exception added; severity kept at warning.
- The strict and relaxed tier changes were undisclosed. Listed above.
- `disable-next-line` covered a whole block without saying so. The README now says so;
  the old engine behaved the same way.
- A `slopvac-disable` quoted in inline code silenced the file, and a code span closing
  on the next line was reported as malformed. Both fixed, with a regression test.
- A path-scoped `[overrides.vale]` was ignored. Fixed.
- Errors in a weight-0 category still failed `max_errors`. Fixed.
- `end_column` overflowed the line on wrapped matches. Fixed in both engines.
- `slopvac rules` showed the shipped severity where `lint` resolved another. It shows
  both now.
- The compile JSON omitted aliases and the Vale version. Added.
- A duplicate test name shadowed a broken test. Removed.
- Step 4 of `review-docs` selected 63 of 64 judgement rules for `consumer`, which is
  true. The step now bounds itself by passage and by a question budget rather than by
  the genre filter.

## Measurement limits

One generation per cell and one labeller per corpus; the label sets are the two agents'
judgement, not ground truth, and the challenger showed the human labels conflate a
detector miss with a profile disagreement. Span-level labels exist only for
`ai-existing` (exhaustive) and for a 352-finding sample of `human`; the 142 generated
documents and the 22 gated documents carry no tell labels, so for them this report gives
finding counts, gate outcomes and the new rule's hand-checked hits, not precision or
recall. Three of the eleven human documents are PyPI long descriptions of projects that
predate language-model writing; the release text may carry later human edits, so their
authorship is unverified (`corpus/human/SOURCES.md`). The human corpus is READMEs and guides, which
is not the genre mix of the model corpus; the challenger's README-only control is what
the decommission decisions rest on. Vale 3.21 dropped one `substitution` alert from an
otherwise identical run in 1 of 6 repeats under CPU load; the compile sweep test settles
a miss with a single-example run.

## Follow-ups filed

See the PR description for the beads issues: STE tokenizer contract, per-target config
discovery, `text_type` classifier before gating, HTML/MDX prose, `.rst` dependency,
action harness, native reach for `prose-craft.acronym-periods`, `annotations`,
`articles`, `gerund-heading`, judgement `exceptions` metadata, Vale messages that lose
the matched text for three substitution rules (`phrasal-verb`, `false-friend-term`,
`noun-used-as-verb`), and the `omitted that` half of the steering guard.
