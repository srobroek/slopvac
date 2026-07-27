---
name: review-docs
description: Review written text for AI tells, slop, writing craft, and genre defects, and return a verdict. Use after drafting any significant prose, or to review text you did not write. Triggers on "review this README", "deslop this", "does this read like AI", "is this well written".
---

# Review Docs

TRIGGER
+ finishing any significant piece of prose -- run this before calling it done
+ "review this README", "deslop this", "does this read like AI", "check the docs"
+ reviewing text someone else drafted, human or model
+ a PostToolUse advisory named this skill
- authoring from scratch, or choosing a genre → write-docs (it calls this skill at the end)
- code comments and docstrings → language conventions

This skill owns the gate and the verdict. `write-docs` owns genre routing and the
authoring rules, and finishes by handing off here. Neither carries a copy of the
other's rules.

The gate runs two axes, and the distinction decides what a finding means:

| Axis | Level | A match says |
|---|---|---|
| Slop | error | Something about how the text was produced |
| Craft | warning | The writing is worse, whoever wrote it |

Fix every slop ERROR. Fix or justify each craft WARN in one line. A craft warning
never moves the verdict on its own: wordiness is not evidence of generation, and
treating it that way is what makes a gate get switched off.

## Workflow

0. First run in a repo: `scripts/init-vale.sh --check`. Exit 2 means no project
   config; ASK before scaffolding, then run `scripts/init-vale.sh`, which writes a
   committed `.vale.ini` and fetches the styles. Exit 1 means the styles need
   `vale --config=.vale.ini sync`. Take new upstream rules the same way: every
   URL is a rolling tag.
1. Identify the genre, because it selects the config: `consumer` (README, docs/),
   `change` (commit message, PR body, release notes), or `internal` (spec, ADR,
   CONTRIBUTING, runbook). If `write-docs` already classified it, take that.
2. Run the gate:
   `scripts/slop-lint.sh --genre <consumer|change|internal> <file>...`
   Fix every ERROR. Fix or justify each WARN in one line. The genre selects which
   craft rules apply: first-person plural is a defect in a README and the point of
   a commit message, so the config inverts it rather than the reader having to. Paths are relative to
   this skill, so they resolve wherever the package installed. A project
   `.vale.ini` wins over the packaged config; `SLOP_LINT_CONFIG` overrides both.
3. LOAD `references/ai-tells.md` -- an index -- then the section files the text
   calls for. Judge what patterns cannot reach: register, structural symmetry,
   and the counter-signals.
   Start with `ai-tells/register.md` and `ai-tells/structure.md`; load
   `ai-tells/content-shape.md` when the text makes factual claims or cites
   sources.
4. Verify the claims. Every sentence checks against code at HEAD; every consumer
   example has a runnable test under `examples/`; no sentence describes unbuilt
   behavior in the present tense.
5. Report the verdict in the format below.

MUST Invoke this skill rather than the linter alone. The gate is deterministic
pattern-matching and cannot see register, symmetry, or an unsupported claim.
Scripts and CI may call `apm run slop-lint` directly inside this repo.

## What the gate does not catch

Read for these directly; none is mechanizable.

| Look for | Fix |
|---|---|
| Uniform paragraph mass, metronomic transitions | Vary deliberately; let one point take three paragraphs and the next a clause |
| Bulleted symmetry with near-zero content per bullet | Merge into prose, or keep only bullets with distinct substance |
| One argument restated in fresh metaphors | Say it once and stop |
| Hedged even-handedness where a human picks a side | Take the position the evidence supports |
| Sections padded to match a sibling's length | Let the short section stay short |
| A claim with no number, path, version, or named failure behind it | Add the specific, or cut the claim |
| Present-tense description of unbuilt behavior | Cut the passage; a hedge is not a fix |
| A balanced pair or maxim closing a section that already concluded | Delete it |
| A heading promising something the section withholds | Name the thing in the heading |

## Read it adversarially

MUST Default to REVISE. A document that produced no gate errors has cleared the
mechanical bar and nothing else. Look for a reason to cut before looking for a
reason to pass.

Take these positions rather than summarising:

MUST Delete every sentence a reader would act identically without. Ask it of each
sentence individually, not of the paragraph.
MUST Name the weakest claim in the document and say so, even when the document is
good. A review that finds nothing has usually not read for truth.
MUST Check every command, path, flag, and version against the repo. A command
nobody has run is an unverified claim, and this is where real defects concentrate --
more than in the register.
MUST Read the headings alone, in order. They should read as an outline of what the
artifact does; if two say the same thing or one promises what its section withholds,
the structure is wrong, not the prose.
MUST Cut the longest paragraph by a third and see what was lost. Usually nothing.

DEFAULT Say what you would delete, in the verdict, as a specific line rather than a
category. "Cut lines 33-36" beats "tighten the intro".
NOT Praising the document. The author asked for a review.
NOT Softening a finding to be agreeable, then listing it anyway.

## Changing a rule

Fix the prose first. When the rule is genuinely wrong for this project, change the
config; scattered inline suppressions hide the decision.

MUST Put the line inside the section it applies to -- normally `[*.{md,mdx}]`.
A rule line binds to the section ABOVE it, so one appended at the end of the file
silently attaches to the last section and the rule keeps firing everywhere else.
MUST Give every override a one-line reason in a trailing comment; the next reader
needs to know whether it still holds.
NOT Editing the packaged config under the skill directory: a reinstall overwrites
it. Edit the project `.vale.ini`.

| Situation | Change |
|---|---|
| Rule is wrong for this project | `rule = NO` under the right section |
| Worth seeing, not worth gating | `rule = warning` |
| Whole style does not apply | drop it from that section's `BasedOnStyles` |
| One path is generated or vendored | `[**/generated/**]` then `BasedOnStyles =` |
| One passage is a deliberate exception | `<!-- vale rule = NO -->` / `= YES -->` around it, each on its own line |

A doc that needs more than two or three overrides is usually the wrong genre:
check the routing table before widening the config.

## Verdict

Report in this shape, and nothing longer:

```text
VERDICT: PASS | REVISE
Gate:    <n> errors, <n> warnings  (exit <code>)
Register: <one line -- what the prose reads as, with the tell that shows it>
Claims:   <verified | the specific claim that does not hold>
Action:   <the single highest-value change, or "none">
```

`REVISE` when the gate errors, when three or more register tells cluster in one
passage, when any claim fails against HEAD, or when a section would survive being
cut. The threshold sits at three because no single tell proves anything -- humans
wrote the training data -- but tells cluster.

`PASS` requires all of: gate clean, every command executed, every claim checked
against code, and no paragraph you would delete. State in `Action` what you checked
rather than that you checked.

NOT Keyword prefixes (MUST/NOT/DEFAULT) in the verdict: it is user-facing text.
