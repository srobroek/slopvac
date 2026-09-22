---
name: review-docs
description: Review prose for slop and genre defects. Triggers on review this README, deslop this, does this read like AI.
hooks:
  SubagentStop:
    - matcher: "slopvac-judge"
      hooks:
        - type: command
          command: "${CLAUDE_PLUGIN_ROOT}/skills/review-docs/hooks/validate-judge.sh"
---
# Review Docs

TRIGGER

+ finishing any significant piece of prose
+ "review this README", "deslop this", "does this read like AI", or "check the docs"
+ reviewing text someone else drafted, human or model
+ authoring from scratch or choosing a genre → write-docs
+ code comments and docstrings → language conventions

The linter owns mechanical rules. This skill owns reader relevance, genre boundaries, unsupported claims, and the verdict.

Ordinary documentation describes the current artifact directly: behavior, interface, configuration, constraints, and reader actions needed to use, verify, or reproduce it. Keep process history in change communications or decision records.

MUST Review for a technically capable reader. Require direct, concise prose; flag introductory primers, prerequisite tutorials, remedial definitions, hand-holding, repeated rationale, and explanations that do not enable use, verification, or reproduction.
MUST Keep explanations that establish a prerequisite, safety constraint, implicit invariant, or other fact required for the documented task.
MUST Default to REVISE for any paragraph, list item, table row, or sentence that does not change a reader action or understanding of the current contract.
MUST Apply the aggressive deletion test before polishing: remove tangents, process narration, past-state archaeology, future promises, and over-explanation.
MUST Verify present-tense claims against code at HEAD. Delete unbuilt behavior from ordinary docs rather than weakening it with "coming soon"; internal specifications and plans may state unbuilt behavior only with explicit acceptance criteria.
MUST Keep status language, history narration, relative-time claims, chronology, job IDs, future tasks, and operational archaeology out of ordinary docs.
Change communications may describe deltas, chronology, job IDs, and verification.
Internal ADRs, decision records, specifications, plans, or historical reports may retain permitted rationale, alternatives, future intent, or archaeology.
MUST Keep measurements only when they support a current threshold, capacity, cost, or reader decision, and require a baseline and method.
Keep ordinary documentation focused on current behavior. Move chronology, author effort, job IDs, phase timings, causal journeys, superseded behavior, rejected alternatives, future tasks, and operational archaeology to their permitted genres.
Keep cache and performance details only when a current actionable limit or reproduction step depends on them.

## Genre routing and exceptions

Use the genre and profile passed by `write-docs`; otherwise use this table and LOAD the matching reference under `write-docs/references/`:

| Surface | `genre` | Profile | What may remain |
|---|---|---|---|
| README, docs, guides, released-artifact user docs | `consumer` | `normal` | Current shipped behavior and reader use only |
| API/reference docs, runbooks, procedures, safety text | `reference` | `strict` | Exact operation and dated facts needed to operate or verify |
| commit message, PR body, release notes | `change-comms` | `normal` | Delta, past tense, rationale, and verification; never a roadmap |
| specifications, ADRs, CONTRIBUTING, contributor docs | `internal` | `normal` | Requirements and constraints; ADRs may preserve rationale and alternatives; specs may state future intent with acceptance criteria |
| issue comments, discussion replies, blog posts, drafts | `informal` | `relaxed` | Immediate context; no project history or promises |
Exception routing follows document purpose. Migration guides and explicit before/after change tracking use `change-comms`. ADRs, decision records, future release plans, specifications, and explicitly historical reports or data use `internal`. Procedures and reference documents use `reference` for current operation or reproducibility.

MUST Keep each genre exception in its designated genre. Change communications may compare states; consumer docs describe current behavior. ADRs may preserve rejected alternatives. Specifications may state future intent with testable acceptance criteria.

## Workflow

1. Identify `genre` and profile. LOAD the matching reference and check that the document belongs in that genre.
2. Run `slopvac lint <file>... --profile <profile> --format json`. Read `summary.score`, `summary.per_100_words`, `documents[].findings`, and `documents[].unchecked`. Exit 2 is incomplete: act on native findings and report every unchecked entry.
3. Triage each ERROR and WARNING using `slopvac explain <rule_id>` and the rule's closed exception list. Fix defects, annotate named exceptions, and report false positives without suppressing them.
4. Read the document adversarially before selecting judgement passages. For every sentence, list item, table row, and paragraph ask: "What reader action or current-contract understanding changes?" Revise when the answer is none. Name the weakest remaining claim. Check headings alone as an outline of current behavior, record every section whose heading promises content that its body withholds, and record the longest paragraph.
5. Run an opt-in judgement pass only when the user asks for a judgement pass or deep review; the default review stops at step 4 and the verdict. For the in-context pass, run `slopvac rules --judgement --format json` after recording the passages.

   Keep entries whose category's `recommended_for` in `.categories` names the `genre` from step 1. Run selected questions in this order, stopping at one answer per rule per passage:
   + Run `scope: document` questions once over the whole document. Run `scope: paragraph`, `scope: sentence`, and `scope: prose` questions only on selected passages. Select the paragraph, list item, or table row containing a gate finding from step 2, plus the longest paragraph and every section with a heading-gap finding recorded in step 4. Ask only questions from categories that fired in each passage.
   + Skip a `-remainder` question when its mechanical core already fired on the same passage; the remainder covers only shapes the pattern could not name. Stop after 40 passage questions; at that cap the verdict is `REVISE` on the gate alone.

   For every selected entry, use its qualified `rule_id` (`category.rule`) with `slopvac explain <rule_id>` for the question, fix, and worked examples. Answer with a quote from the text. Report only failed questions. This metadata-driven selection applies all rules recommended for ordinary `consumer` documentation without copying rule questions into this skill.

   For a structured judgement pass when the user wants rewrites or machine-readable confirms, run `slopvac judgement brief <file> --out .slopvac-judgement --packs fired`. For each call in `brief.json`, dispatch a judge using the shared system text, that call's user payload, and `Respond with the JSON object only`. Write `{call_id, response}` rows to `responses.jsonl`.

   Harness dispatch:
   - OMP: use a task with `outputSchema` set to the response schema in strict mode; re-dispatch on `schema_violation`.
   - Claude Code: use a `slopvac-judge` subagent and the `SubagentStop` hook; retry exit-2 validation failures, stop after 8 blocks, and honor `stop_hook_active`.
   - Codex: prompt-only JSON, then validate every response.

   Validate each row (skip this on OMP when strict schema already passed) with `slopvac judgement validate --run .slopvac-judgement --call-id …`.

   Apply and compare the structured judgement with `slopvac judgement finish --out .slopvac-judgement` and `slopvac judgement compare --out .slopvac-judgement --apply-preview`.

   Add a `Judgement:` line to the verdict confirming by rule, rewrites accepted, and coverage.
6. Verify every claim against code at HEAD. Every consumer example MUST be runnable and have a matching test under `examples/`; check every command, path, flag, and version.
7. When reviewing a code change, inspect every changed comment or documentation passage against the code diff. Mark unrelated prose edits as a `defect`, including same-file comments and documentation elsewhere. Keep a stale comment that directly describes changed behavior in scope for correction. An explicitly requested prose edit is in scope even when it is unrelated to the code.

## Verdict

Report only:

```text
VERDICT: PASS | REVISE
Gate:     score <n>/100 - <n> errors, <n> warnings, <n>/100w  (exit <code>)
Register: <one line -- what the prose reads as, with the tell that shows it>
Claims:   <verified | the specific claim that does not hold>
Judgement: <confirmed by rule, rewrites accepted, coverage>
Action: <the single highest-value change, or "none">
False positives: <none | rule · matched text · sentence>
```

REVISE when the gate reports an error, the score is below its floor, any claim fails, any unchecked entry remains, three judgement checks fail in one passage, or any section survives the deletion test.

PASS requires a clean gate, no unchecked entries, executed commands, checked claims, no paragraph worth deleting, and no unsupported present-tense behavior.

## Change a rule

Fix prose first. For a deliberate exception, use only a reason from `slopvac explain <rule_id>`:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

MUST Report a finding called a false positive with its rule, matched text, and sentence. Keep packaged rules unchanged; use project config or a house rules directory for policy changes.
