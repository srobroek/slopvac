---
name: write-docs
description: Invoke before writing or reviewing a README, docs, PR/release text, spec, ADR, or CONTRIBUTING -- even when documentation is one step of a larger task.
---

# Write Docs

TRIGGER
+ writing or updating README.md, docs/**, or any doc a consumer of the artifact reads
+ writing a PR description, commit message, or hand-written release notes
+ writing specs, ADRs, constitutions, CONTRIBUTING, runbooks (internal genre)
- reviewing or de-slopping text that already exists → review-docs
- authoring skills, steering, or agent definitions → write-agentic
- code comments and docstrings → language conventions

This skill authors. `slopvac-lint` gates mechanically; the `review-docs` skill
judges what no pattern reaches. Steps 4 and 5 run both, and neither is optional --
a document is not finished until it has passed.

## Genre → reference

| Surface | LOAD | Lint profile |
|---|---|---|
| README.md, docs/**, anything a user of the artifact reads | references/consumer-docs.md | `normal` |
| PR bodies, commit messages, hand-written release notes | references/change-comms.md | `normal` |
| specs/, ADRs, constitutions, CONTRIBUTING, contributor docs | references/internal-docs.md | `normal` |
| reference material, API docs, runbooks, procedures, safety text | references/internal-docs.md | `strict` |

## Workflow

1. Classify the doc with the genre table; LOAD that reference before writing.
2. Author or rewrite against the sentence rules below plus the genre reference.
3. Verify every claim against code at HEAD, and give every consumer example a
   runnable test under `examples/`.
4. Run the linter and fix what it reports:

   ```sh
   uvx slopvac-lint <file>                    # or --profile strict
   ```

   Fix every ERROR. Fix or justify each WARNING in one line. The linter names the
   replacement for every substitution, so never guess one from memory.
   MUST Exit 2 means nothing was checked. Report that rather than treating it as
   a pass.
5. MUST Invoke the `review-docs` skill, passing the genre from step 1. It judges
   register, structural symmetry, and claims with nothing behind them. Fix what it
   returns.

## Sentence rules

The linter owns the word lists and the exact limits. These are the rules that
change how you form a sentence in the first place, so they belong in your head
before you draft.

MUST One idea per sentence. One instruction per sentence, unless two actions happen at the same time.
MUST About 20 words for an instruction or a warning; about 25 for descriptive text.
MUST Active voice with the actor named. Use the passive only when the actor is unknown, is any conforming implementation, or is the reader.
MUST One word, one meaning. One name, one thing: never call the same thing by two names in one document.
MUST Use a verb for an action: "analyze the log", not "perform an analysis of the log".
MUST Put a condition before the command it governs.
MUST Six sentences per paragraph at most, one topic each. Steps go in a vertical list, one action per item, imperative.
MUST Every claim names a checkable particular: a number, a path, a command, a version, a named event.
MUST Delete any adjective you cannot back with a number, benchmark, or feature list.
MUST Delete every span whose removal changes no proposition, obligation, or referent.
MUST Take the position the evidence supports. Hedge only where the uncertainty is real and you can name its cause; one hedge at most, never a hedge on a hedge.
NOT Hedging in both directions ("may improve latency, though it might also increase it") -- the halves cancel and the reader learns nothing actionable.
DEFAULT Judge hedging across the whole document, not the sentence: if most load-bearing claims carry a hedge, the document asserts nothing however careful each sentence reads.
MUST Attribute or own every claim. "Experts agree", "research has shown", "it is widely known", and "some people say" dress a claim in authority it does not have: name the source, or state it as your own.
MUST Give a comparative its baseline. "20% faster" than what, measured how.
MUST Give a quantity its count. "Several", "various", "a number of", "in most cases" all name a number the writer has and withheld.
NOT Presuming the reader: "obviously", "clearly", "of course", "note that", "it should be noted that", "as you can see", "interestingly". The sentence stands without them, so delete them.
NOT Puffery: an adjective that praises rather than describes ("award-winning", "innovative", "world-class", "remarkable"). State the fact that would earn it.
NOT A relative time reference in a document that outlives the moment: "recently", "currently", "for now", "last quarter", "in the future". Give a date or a version.
NOT A rhetorical question as a heading. A heading is an index entry: "Configure the pool", not "How do I configure the pool?".
NOT Pairing "including" or "such as" with "etc." -- either already says the list is partial. Where the list is complete, write "consisting of".
MUST Name who acted: an abstraction is not an actor ("the team fixed it", never "the complaint becomes a fix").
MUST State what the artifact does -- never effort, intent, process, or journey.
MUST Cut the claim, not the hedge: a doc that describes unbuilt behavior is fixed by deleting the passage, not by deleting "coming soon".
NOT A figure of speech you are used to seeing in print.
NOT Status language, or history narration in a doc body -- deltas belong to the change-comms genre only.
NOT Justify a choice inside the artifact. The doc states what IS; the reason it is
  that way belongs in the commit or an ADR. Write the rationale only when the
  reader cannot recover it from the text (a constraint, an invariant, a measured
  number that decided a threshold), when the genre exists to record a decision
  (ADR, spec, commit message, PR body), or when the user asked for it.
NOT Over-writing -- real content in the wrong document:
  · a rejected alternative defended in place -> move the decision to an ADR, spec, or commit
  · an implementation cost the reader cannot act on (timing, process count) -> move it to the commit that measured it
  · reassurance answering a worry never raised ("no configuration required", "it just works") -> state the positive alone, or say nothing
  Ask whether a reader of THIS document acts differently for having read the sentence.

## Configuring the gate

A project owns its thresholds in `slopvac.toml`; `uvx slopvac-lint init` writes a
starter file.

MUST Fix the prose before changing a rule. When a rule is genuinely wrong for this
project, change the config and give the override a one-line reason.
MUST Suppress a single finding by naming an exception from that rule's own closed
list: `<!-- slopvac-allow: rule=<id> reason=<name> -->`. Run
`uvx slopvac-lint explain <id>` for the valid reasons. A reason that is not on the
list is reported rather than honoured.
NOT Editing the packaged rules: a reinstall overwrites them. Add a house rule with
`--rules-dir`, or set the severity in `slopvac.toml`.
