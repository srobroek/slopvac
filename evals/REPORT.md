# Eval report

Eight documents, four genres, three generation conditions, scored by
`slopvac-lint` at 215 rules. Every number here comes from a `scores.json` written
by `score.py`, so the report cannot drift from the measurement.

## Method

| Condition | Ruleset given to the writer |
| --- | --- |
| `01-unguided` | none |
| `02-current-writedocs` | the 56-line write-docs skill as it stood at `7587435~1`, extracted from git rather than paraphrased |
| `03-new-writedocs` | the new steering: STE sentence construction, Orwell restated, attribution and precision, hedging |

Each condition ran as a separate agent with its ruleset quoted inline and an
instruction to load no skill and run no linter, so a condition measures its
ruleset rather than what the environment leaks. No condition saw a lint report:
that is condition 04, not yet run.

Two topics are deliberately hostile. `error-message` is short enough that density
is close to meaningless, which is where the methodology this work started from
broke. `runbook-failover` and `api-docs-webhook` run at the `strict` profile,
where the STE rules are enforced rather than advisory.

## Results

| Topic | Profile | 01 findings | /100w | score | 02 findings | /100w | score | 03 findings | /100w | score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `adr-queue` | normal | 59 | 20.77 | 0 | 23 | 4.06 | 37 | 24 | 4.71 | 29 |
| `api-docs-webhook` | strict | 49 | 15.61 | 0 | 24 | 4.12 | 0 | 21 | 3.40 | 0 |
| `error-message` | normal | 25 | 17.61 | 0 | 8 | 3.32 | 42 | 7 | 3.29 | 46 |
| `guide-migration` | normal | 63 | 23.77 | 0 | 10 | 3.12 | 52 | 8 | 2.25 | 67 |
| `pr-description` | normal | 50 | 16.89 | 0 | 8 | 2.72 | 40 | 3 | 0.98 | 84 |
| `readme-cache` | normal | 64 | 15.31 | 0 | 7 | 2.05 | 62 | 5 | 1.47 | 74 |
| `readme-parser` | normal | 40 | 13.61 | 0 | 9 | 2.69 | 54 | 2 | 0.90 | 86 |
| `runbook-failover` | strict | 32 | 12.70 | 0 | 35 | 4.69 | 0 | 33 | 5.50 | 0 |
| **all 8** | | **382** | **16.87** | **0** | **124** | **3.62** | **36** | **103** | **3.25** | **48** |

Word counts: 2,265 unguided, 3,427 at condition 02, 3,165 at condition 03. The
guided conditions produced longer documents, so the density figures are the
comparable ones.

Density fell 16.87 to 3.62 to 3.25 per 100 words. The first drop is the old
skill's; the second is this change's, and it is much smaller. The mean score rose
36 to 48.

## What the new rules actually removed

Per-rule, across all eight documents, unguided to condition 03:

| Rule | 01 | 03 |
| --- | --- | --- |
| `ste-sentences.omitted-word-or-contraction` | 56 | 0 |
| `prose-craft.first-person-plural` | 56 | 7 |
| `prose-format.no-unicode-dash` | 47 | 0 |
| `prose-inflation.slop-lexicon` | 15 | 0 |
| `prose-craft.future-tense` | 16 | 1 |
| `ste-words.approved-word-substitution` | 13 | 0 |
| `ai-tells-formatting.emoji-list-markers` | 11 | 0 |
| `ste-verbs.passive-voice` | 26 | 16 |
| `prose-inflation.borderline-hype` | 10 | 0 |
| `orwell.unsupported-evaluative` | 7 | 0 |

Every category the new steering names went to zero or near it. The marketing
lexicon, the unsupported evaluatives, the emoji, and the em dashes are gone
outright.

## What the new rules made worse

This is the more useful half.

| Rule | 01 | 03 | Reading |
| --- | --- | --- | --- |
| `ste-punctuation.semicolon-used` | 1 | 15 | The steering pushes toward compressed declaratives, and a semicolon is how a writer compresses two clauses. STE bans it; the steering never says so. |
| `ste-practices.omitted-conjunction-that` | 5 | 15 | Same cause. "Make sure the flag is set" reads tighter than "make sure that the flag is set", and the 20-word cap rewards the tighter form. |
| `ste-procedural.condition-after-command` | 2 | 6 | The steering states the rule and the writer still broke it six times, so stating it is not enough. |
| `ste-procedural.sentence-too-long-procedural` | 0 | 3 | New. The writer hit the 25-word descriptive cap and missed the 20-word procedural one. |
| `ste-procedural.instruction-not-imperative` | 0 | 2 | New. |

The semicolon result is the clearest finding in the eval: a rule the steering
does not mention got 15 times worse **because** the steering worked. Compression
was the instruction; the semicolon is what compression produces; nothing told the
writer that STE forbids it.

## The scoring defect this eval found

Both `strict` topics score 0 in every condition, including the one where errors
fell from 13 to 1.

| Topic | 01 errors | 03 errors | 01 /100w | 03 /100w | score |
| --- | --- | --- | --- | --- | --- |
| `api-docs-webhook` | 13 | 1 | 15.61 | 3.40 | 0 -> 0 |
| `runbook-failover` | 10 | 6 | 12.70 | 5.50 | 0 -> 0 |

The strict profile sets `min_score = 85` and a total density budget of 1.5 per 100
words. Real reference documentation does not reach 1.5 while remaining readable:
the best result here is 3.40, and it carries one error. So the strict tier reports
0 for a document that improved by every other measure, which makes the score
useless exactly where the profile is meant to be most informative.

The density figures moved correctly throughout. The 0-100 mapping is what fails.

## Findings against the ruleset

1. **The strict profile's `min_score` and density budget are unreachable.** Recalibrate
   against this corpus rather than against an assumption. A floor no compliant
   document clears is a floor that gets removed.
2. **`prose-craft.first-person-plural` fires on genres that need it.** 24 hits on the
   ADR and 7 on the pull request body at condition 01, and the rule's own
   provenance note concedes both genres legitimately say "we chose". Already
   scheduled for exclusion at those genres.
3. **Steering that improves one dimension can worsen another.** The semicolon and
   `that`-omission results are caused by the compression instruction. The steering
   needs the STE punctuation rules stated, or the compression instruction needs
   its consequence named.
4. **The 20-word procedural cap is not reaching the writer.** Three new violations at
   condition 03 where there were none unguided. The steering says "about 20 words
   for an instruction", and "about" is doing too much work.
5. **`runbook-failover` got worse on density**, 4.69 to 5.50 between conditions 02 and
   03, while its errors fell 10 to 6. A procedure is the genre where the STE rules
   bite hardest and where the steering's own advice is least sufficient.

## Limits

One generation per cell, no repetition, no variance, and a single model. The
direction of the density result is large enough to survive that; the per-topic
differences are not, and a 2-point score gap between conditions means nothing
here.

The writer and the ruleset share an author, which is the circularity the source
methodology had. It is mitigated only in that the linter was calibrated against a
different corpus than the eval documents, and that the findings above are mostly
against the ruleset rather than for it.

Condition 04, regenerating from a lint report, is not yet run. That is the
condition that tests whether the report is actionable, which is a different
question from whether the rules are right.
