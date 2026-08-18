---
name: review-docs
description: Review written text for AI tells, slop, and genre defects, and return a verdict. Use after drafting any significant prose, or to review text you did not write. Triggers on "review this README", "deslop this", "does this read like AI".
---

# Review Docs

TRIGGER

+ finishing any significant piece of prose -- run this before calling it done
+ "review this README", "deslop this", "does this read like AI", "check the docs"
+ reviewing text someone else drafted, human or model
+ authoring from scratch, or choosing a genre → write-docs (it calls this skill at the end)
+ code comments and docstrings → language conventions

`slopvac` owns every mechanical rule. This skill owns the judgement the
linter cannot make, and the verdict. Neither carries a copy of the other's rules:
the checks in step 3 are read FROM the linter, so they cannot drift from it.

Every command below is written `uvx slopvac`, which installs the published
release. MUST fall back to `uvx --from <path-to-checkout> slopvac` when that
fails to resolve, and say which one ran. Reporting a verdict without the gate
having executed is the one failure mode this skill cannot recover from.

## Workflow

1. Identify the genre and pick the profile:

   | Genre | Profile |
   |---|---|
   | README, docs/, guides, ADRs | `normal` |
   | reference, API docs, runbooks, procedures, safety text | `strict` |
   | issue comments, notes, drafts | `relaxed` |
   | commit message, PR body, release notes | `normal` |

2. Run the gate:

   ```sh
   uvx slopvac <file>... --profile <profile> --format json
   ```

   Read `summary.score`, `summary.per_100_words`, and the per-category table. Fix
   every ERROR. Fix or justify each WARNING in one line.
   MUST Exit 2 means nothing was checked -- a bad config, an unloadable ruleset, or
   a missing tool. Report that; it is not a pass.
   MUST Read `documents[].unchecked`. An absent `vale` or an unsynced style makes
   those rules report every file as clean, which is indistinguishable from a pass.

3. Triage the warnings. An ERROR is a defect: fix it. A WARNING marks a
   candidate the pattern could not settle, so settle it per finding rather than
   by re-reading the document.

   For each warning, read the span at `line`/`column` and its sentence, then
   return one of three verdicts:

   | Verdict | When | Do |
   |---|---|---|
   | `defect` | the shape is a real defect in this sentence | apply the `fix` |
   | `exception` | an exception on the rule's own list applies | annotate with that reason |
   | `false-positive` | the rule matched correct prose | report it; change nothing |

   `uvx slopvac explain <rule_id>` gives the decision question, the closed
   exception list, and worked examples.

   MUST Report every `false-positive` in the verdict, naming the rule, the
   matched text, and the sentence. That is evidence about the RULE, and a rule
   collecting them is one to tighten or demote.
   NOT Suppressing a finding you judged `false-positive`. An annotation claims a
   named exception applies, and "the rule is wrong" is not on any list.
   NOT Editing correct prose to silence a warning. Three rules ship deliberately
   soft, so a warning that survives triage is a finding about the linter.

4. LOAD the checks no pattern reaches:

   ```sh
   uvx slopvac rules --judgement --format json
   ```

   Each entry carries a decidable `judgement_question`, the `fix`, its
   `exceptions`, and worked `examples`. Filter by `scope` to work at the right
   level -- the `document` ones are ratio checks a per-line rule cannot see, and
   they catch the failures where every sentence passes on its own. These always
   run, whatever the gate reported: a document where every sentence passes and
   the whole asserts nothing produces no finding at all.

   Answer each question with evidence from the text, not an impression.

5. Verify the claims. Every sentence checks against code at HEAD; every consumer
   example has a runnable test under `examples/`; no sentence describes unbuilt
   behavior in the present tense. This is where real defects concentrate, more
   than in the register.

6. Report the verdict in the shape below.

MUST Invoke this skill rather than the linter alone. The gate is pattern-matching
and cannot see register, symmetry, or an unsupported claim.

## Selecting rules for a project

A project chooses its own gate. Show the user what is available before changing
anything:

```sh
uvx slopvac rules --profile <profile>                 # every rule and its disposition
uvx slopvac rules --format json | jq '.categories'    # with recommended_for
uvx slopvac explain <category>.<rule>                 # one rule in full
```

DEFAULT Recommend by genre, reading each category's own `recommended_for` field
rather than a list held here:

| Project shape | Recommend |
|---|---|
| Library or CLI with a README and docs/ | `normal`, and `strict` for `docs/reference/**` |
| Reference documentation, runbooks, procedures | `strict` throughout |
| Specs, ADRs, design records | `normal`, with `prose-scope` and `docs-discipline` off -- a decision record exists to hold the rationale those rules ban elsewhere |
| A repo with generated or vendored docs | exclude those paths; a generated file is not authored prose |
| Non-American house style | `locale.default = "en-GB"` |

MUST Name what is off by default and say why, so the choice is the user's. The
word-choice rules check nothing until the project writes a blocklist and sets
`vocabulary.path`; no word list ships. Most other STE word rules are advisory at
`normal`. Read `documents[].unchecked` for the authoritative list on a given run
rather than reciting one from here.
MUST Ask before writing `slopvac.toml`. Scaffold it with
`uvx slopvac init --profile <profile>`.

## Read it adversarially

MUST Default to REVISE. A document that produced no findings has cleared the
mechanical bar and nothing else. Look for a reason to cut before looking for a
reason to pass.

MUST Delete every sentence a reader would act identically without. Ask it of each
sentence individually, not of the paragraph.
MUST Name the weakest claim in the document and say so, even when the document is
good. A review that finds nothing has usually not read for truth.
MUST Check every command, path, flag, and version against the repo. A command
nobody has run is an unverified claim.
MUST Read the headings alone, in order. They should read as an outline of what the
artifact does; if two say the same thing or one promises what its section
withholds, the structure is wrong rather than the prose.
MUST Cut the longest paragraph by a third and see what was lost. Usually nothing.

DEFAULT Say what you would delete, as a specific line rather than a category.
"Cut lines 33-36" beats "tighten the intro".
NOT Praising the document. The author asked for a review.
NOT Softening a finding to be agreeable, then listing it anyway.

## Changing a rule

Fix the prose first. When the rule is genuinely wrong for this project, change the
config; scattered inline suppressions hide the decision.

MUST Suppress one finding by naming an exception from that rule's own closed list:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

Run `uvx slopvac explain <rule>` for the valid reasons. A reason that is not
on the list is reported as `meta.invalid-suppression` rather than honoured, and
"it reads better" is deliberately on no list.
MUST Give every config override a one-line reason; the next reader needs to know
whether it still holds.
NOT Editing the packaged rules: a reinstall overwrites them. Add a house rule with
`--rules-dir`, or set the severity in `slopvac.toml`.

| Situation | Change |
|---|---|
| Rule is wrong for this project | `[rules."cat.rule"]` then `severity = "off"` |
| Worth seeing, not worth gating | `severity = "warning"` |
| Whole category does not apply | `[categories.cat]` then `enabled = false` |
| One path is generated or vendored | add it to `exclude` |
| One passage is a deliberate exception | the annotation above |

A doc needing more than two or three overrides is usually the wrong profile:
check the genre table before widening the config.

## Verdict

Report in this shape, and nothing longer:

```text
VERDICT: PASS | REVISE
Gate:     score <n>/100 - <n> errors, <n> warnings, <n>/100w  (exit <code>)
Register: <one line -- what the prose reads as, with the tell that shows it>
Claims:   <verified | the specific claim that does not hold>
Action:   <the single highest-value change, or "none">
```

`REVISE` when the gate reports an error, when the score is below the profile's
floor, when three or more judgement checks fail in one passage, when any claim
fails against HEAD, or when a section would survive being cut. The threshold sits
at three because no single tell proves anything -- humans wrote the training
data -- but tells cluster.

`PASS` requires all of: gate clean, nothing in `unchecked`, every command
executed, every claim checked against code, and no paragraph you would delete.
State in `Action` what you checked rather than that you checked.

NOT Keyword prefixes (MUST/NOT/DEFAULT) in the verdict: it is user-facing text.
