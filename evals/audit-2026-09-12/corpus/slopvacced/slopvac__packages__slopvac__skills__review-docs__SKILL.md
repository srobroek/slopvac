---
name: review-docs
description: Review prose for slop and genre defects. Triggers on review this README, deslop this, does this read like AI.
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
read the checks in step 3 FROM the linter, so they cannot drift from it.

Run `uvx slopvac`. Without `uv` or `uvx`, run `pipx run slopvac`, or
`pip install slopvac` and then `slopvac`. MUST fall back to
`uvx --from <path-to-checkout> slopvac` when the published release fails to
resolve, and say which one ran. Reporting a verdict without the gate
having executed is the one failure mode this skill cannot recover from.

## Workflow

1. Identify the genre and pick the profile. When `write-docs` invoked this
   skill, use the `genre` and `profile` it passed. Otherwise pick from:

   | Genre | Profile |
   |---|---|
   | README, docs/, guides, decision records | `normal` |
   | reference, API docs, runbooks, procedures, safety text | `strict` |
   | issue comments, notes, drafts | `relaxed` |
   | commit message, PR body, release notes | `normal` |

2. Run the gate. Prose that is not a file (commit message, PR body) MUST be
   written to a temp `.md` first; lint that path.

   ```sh
   slopvac <file>... --profile <profile> --format json
   ```

   Read `summary.score`, `summary.per_100_words`, and the per-category table. Fix
   every ERROR. Fix or justify each WARNING in one line.
   MUST Treat exit 2 as an incomplete run: the Vale sub-gate was absent, failed,
   or skipped with `--no-vale`. Native findings stay in the report and MUST be
   acted on. Report every entry in `documents[].unchecked`. NOT Calling the
   file clean, and NOT reading exit 2 as "nothing was checked".

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

   `slopvac explain <rule_id>` prints the decision question, the closed
   exception list, and worked examples.

   MUST Report every `false-positive` on the verdict's `False positives:` line,
   naming the rule, the matched text, and the sentence. That report is evidence
   about the RULE, and a rule collecting them is one to tighten or demote.
   NOT Suppressing a finding you judged `false-positive`. An annotation claims a
   named exception applies, and "the rule is wrong" is not on any list.
   NOT Editing correct prose to silence a warning. Three rules ship deliberately
   soft, so a warning that survives triage is a finding about the linter.

4. LOAD the checks no pattern reaches:

   ```sh
   slopvac rules --judgement --format json
   ```

   Use each entry's `rule_id` (qualified `category.rule`) with
   `slopvac explain <rule_id>`. Do not pass the bare `id` field to `explain`.
   Each entry carries a decidable `judgement_question`, the `fix`, its
   `exceptions`, and worked `examples`. Filter by `scope` to work at the right
   level -- the `document` ones are ratio checks a per-line rule cannot see, and
   they catch the failures where every sentence passes on its own. These always
   run, whatever the gate reported: a document where every sentence passes and
   the whole asserts nothing produces no finding at all.

   Answer each question with evidence from the text, not an impression.

5. Verify the claims. Every sentence checks against code at HEAD; every consumer
   example has a runnable test under `examples/`; no sentence describes unbuilt
   behavior in the present tense. Real defects concentrate here, more than in
   the register.

6. Report the verdict in the shape below.

MUST Invoke this skill rather than the linter alone. The gate is pattern-matching
and cannot see register, symmetry, or an unsupported claim.

## Selecting rules for a project

A project chooses its own gate. Before changing anything, show the user
what is available:

```sh
slopvac rules --profile <profile>                 # every rule and its disposition
slopvac rules --format json | jq '.categories'    # with recommended_for
slopvac explain <rule_id>                         # one rule in full
```

DEFAULT Recommend by genre, reading each category's own `recommended_for` field
rather than a list held here:

| Project shape | Recommend |
|---|---|
| Library or CLI with a README and docs/ | `normal`, and `strict` for `docs/reference/**` |
| Reference documentation, runbooks, procedures | `strict` throughout |
| Specs, decision records, design records | `normal`, with `prose-scope` and `docs-discipline` off -- a decision record exists to hold the rationale those rules ban elsewhere |
| A repo with generated or vendored docs | exclude those paths; a generated file is not authored prose |
| Non-American house style | `locale.default = "en-GB"` |

MUST Name what is off by default and say why, so the choice is the user's. The
word-choice rules check nothing until the project writes a blocklist and sets
`vocabulary.path`; no word list ships. Most other STE word rules are advisory at
`normal`. Read `documents[].unchecked` for the authoritative list on a given run
rather than reciting one from here.
MUST Ask before writing `slopvac.toml`. Scaffold it with
`slopvac init --profile <profile>`.

## Read it adversarially

MUST Default to REVISE. A document that produced no findings has cleared the
mechanical bar and nothing else. Before looking for a reason to pass, look for
a reason to cut.

+ MUST Delete every sentence a reader would act identically without. Ask it of each sentence individually, not of the paragraph.
+ MUST Name the weakest claim in the document and say so, even when the document is good. A review that finds nothing has not read for truth.
+ MUST Check every command, path, flag, and version against the repo. A command nobody has run is an unverified claim.
+ MUST Read the headings alone, in order. They must read as an outline of what the artifact does. If two say the same thing, or one promises what its section withholds, the structure is wrong rather than the prose.
+ MUST Cut the longest paragraph by a third and see what the cut removed. The usual result is that nothing of substance left.

DEFAULT Say what you would delete, as a specific line rather than a category.
"Cut lines 33-36" beats "tighten the intro".
NOT Praising the document. The author asked for a review.
NOT Softening a finding to be agreeable, then listing it anyway.

## Change a rule

Fix the prose first. When the rule is wrong for this project, change the
config; scattered inline suppressions hide the decision.

MUST Suppress one finding by naming an exception from that rule's own closed list:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

Run `slopvac explain <rule_id>` for the valid reasons. A reason that is not
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
| Whole category does not apply | `[categories.cat]` then `severity = "off"` |
| One run only | `--disable <category-or-rule>` |
| One path is generated or vendored | add it to `exclude` |
| One passage is a deliberate exception | the annotation above |

A doc that needs more than two or three overrides is the wrong profile:
check the genre table before widening the config.

## Verdict

Report in this shape, and nothing longer:

```text
VERDICT: PASS | REVISE
Gate:     score <n>/100 - <n> errors, <n> warnings, <n>/100w  (exit <code>)
Register: <one line -- what the prose reads as, with the tell that shows it>
Claims:   <verified | the specific claim that does not hold>
Action:   <the single highest-value change, or "none">
False positives: <none | rule · matched text · sentence>
```

`REVISE` when any of these hold:

+ the gate reports an error
+ the score is below the profile's floor
+ three or more judgement checks fail in one passage
+ any claim fails against HEAD
+ a section would survive being cut

The threshold sits at three because no single tell proves anything -- humans
wrote the training data -- but tells cluster.

`PASS` requires all of:

+ gate clean
+ nothing in `unchecked`
+ every command executed
+ every claim checked against code
+ no paragraph you would delete

State in `Action` what you checked rather than that you checked.

NOT Keyword prefixes (MUST/NOT/DEFAULT) in the verdict: it is user-facing text.
