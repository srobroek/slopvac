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

Run `uvx slopvac` (or `pipx run slopvac`); when the published release fails to
resolve, run `uvx --from <path-to-checkout> slopvac` and say which one ran.
Reporting a verdict without the gate having executed is the one failure mode this
skill cannot recover from.

## Documentation contract

Ordinary docs (`consumer`, `reference`, and `informal`) describe the current artifact directly: behavior, interface, configuration, constraints, and reader actions. Consumer docs remain strict: describe shipped behavior and reader use only.

MUST Keep status language, history narration, relative-time claims, chronology, job IDs, future tasks, and operational archaeology out of ordinary docs. Change communications may describe deltas, chronology, job IDs, and verification; internal ADRs, decision records, specifications, future plans, or historical reports may retain their permitted rationale, alternatives, future intent, or archaeology.

MUST Delete unbuilt behavior from ordinary docs rather than weakening it with "coming soon". Internal specifications and future plans may state unbuilt behavior only with explicit acceptance criteria.

## Workflow

1. Identify the genre and pick the profile. When `write-docs` invoked this
   skill, use the `genre` and `profile` it passed. Otherwise pick from the same
   table `write-docs` uses:

   | Surface | `genre` | Profile |
   |---|---|---|
   | README, docs/, guides, anything a user of the artifact reads | `consumer` | `normal` |
   | commit message, PR body, release notes | `change-comms` | `normal` |
   | specifications, decision records, CONTRIBUTING, contributor docs | `internal` | `normal` |
   | reference, API docs, runbooks, procedures, safety text | `reference` | `strict` |
   | issue comments, discussion replies, blog posts, drafts | `informal` | `relaxed` |

2. Run the gate. Prose that is not a file (commit message, PR body) MUST be
   written to a temp `.md` first; lint that path.

   ```sh
   slopvac lint <file>... --profile <profile> --format json
   ```

   Read `summary.score`, `summary.per_100_words`, `documents[].findings`, and
   `documents[].unchecked`. Exit 0 means the gate passed and can still carry
   warnings and suggestions; exit 1 means a threshold failed; exit 2 means the run
   was incomplete because Vale was absent, older than 3.15, disabled in
   `slopvac.toml`, or skipped with `--no-vale`. On exit 2 the native findings
   stay in the report and MUST be acted on, and every `unchecked` entry MUST be
   reported. NOT Calling the file clean on exit 2, and NOT reading it as "nothing
   was checked".

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

4. Read the document adversarially before selecting judgement passages. Apply the deletion test to every sentence, list item, table row, and paragraph, and revise when no reader action or current-contract understanding changes. Read the headings alone as an outline of current behavior. Record every section whose heading promises content that its body withholds, and record the longest paragraph for the later selection step.

5. LOAD the checks no pattern reaches and select only after step 4 records its passages:

   ```sh
   slopvac rules --judgement --format json
   ```

   Keep the entries whose category's `recommended_for` (in `.categories`) names
   the `genre` from step 1; the vocabulary is the same five values. The STE
   categories name `reference` only, so `consumer` selects 44 of the 64 entries
   and `reference` 25; the rest of the bound comes from the routing below. Run
   the selection in this order and stop at one answer per rule per passage:

   + `scope: document` questions once, over the whole document (15 for
     `consumer`). These are the ratio checks a per-line rule cannot see, and they
     catch the failure where every sentence passes and the whole asserts nothing.
   + `scope: paragraph`, `scope: sentence`, and `scope: prose` questions on
     passages only. A passage is the paragraph, list item, or table that holds a
     gate finding from step 2, plus the longest paragraph and every section with
     a heading-gap finding recorded in step 4. These passages exist before this
     selection runs. In each passage ask only the questions of the categories
     that fired there.
   + Skip a `-remainder` rule when its mechanical core already fired on the same
     passage; the remainder exists for the shape the pattern could not name.
   + Stop after 40 passage questions. Past that, the document has failed step 3
     often enough that the verdict is REVISE on the gate alone.

   Use each entry's `rule_id` (qualified `category.rule`) with
   `slopvac explain <rule_id>` for the decision question, the `fix`, and the
   worked `examples`. Answer each question with a quote from the text, not an
   impression, and report only the questions that failed.

6. Verify the claims. Every sentence checks against code at HEAD; every consumer
   example has a runnable test under `examples/`; ordinary docs do not describe
   unbuilt behavior in the present tense. Real defects concentrate here, more
   than in the register.

7. Report the verdict in the shape below.


MUST Invoke this skill rather than the linter alone. The gate is pattern-matching
and cannot see register, symmetry, or an unsupported claim.

## Selecting rules for a project

A project chooses its own gate. `slopvac rules --profile <profile>` lists every
rule and its disposition; `slopvac rules --format json | jq '.categories'` shows
each category's `recommended_for` genres. Recommend by genre from that field
rather than from a list held here, name what is off by default and why, and
MUST ask before writing `slopvac.toml`. Scaffold it with
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
