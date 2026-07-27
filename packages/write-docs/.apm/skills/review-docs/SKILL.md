---
name: review-docs
description: Review written text for AI tells, slop, and genre defects, and return a verdict. Use after drafting any significant prose, or to review text you did not write. Triggers on "review this README", "deslop this", "does this read like AI".
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

## Workflow

1. Identify the genre, because it selects the config: `consumer` (README, docs/),
   `change` (commit message, PR body, release notes), or `internal` (spec, ADR,
   CONTRIBUTING, runbook). If `write-docs` already classified it, take that.
2. Run the gate:
   `scripts/slop-lint.sh --genre <consumer|change|internal> <file>...`
   Fix every ERROR. Fix or justify each WARN in one line. Paths are relative to
   this skill, so they resolve wherever the package installed.
3. LOAD `references/ai-tells.md` and judge what patterns cannot reach: register,
   structural symmetry, and the counter-signals in its last section. The linter
   finds tokens; the tells catalog finds voice.
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
passage, or when any claim fails against HEAD. The threshold sits at three
because no single tell proves anything -- humans wrote the training data -- but
tells cluster.

NOT Keyword prefixes (MUST/NOT/DEFAULT) in the verdict: it is user-facing text.
