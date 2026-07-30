# Write Docs

Always-on prose rules, applying to every document you write or edit.

The mechanical set is deliberately NOT here. `slopvac-lint` reports every banned
word, substitution, and length breach with the exact replacement, so this file
carries only what shapes a sentence before it is written, and what no linter can
decide. Restating a word list here would drift from the tool that enforces it.

Check your own output:

```sh
uvx slopvac-lint <file>                    # normal tier
uvx slopvac-lint --profile strict docs/    # reference material, runbooks, specs
uvx slopvac-lint --format json <file>      # score plus per-category breakdown
```

Exit 1 means the prose failed a threshold. Exit 2 means nothing was checked, which
is not a pass. Fix every ERROR; fix or justify each WARNING in one line. For the
register, structural symmetry, and claims with nothing behind them, invoke the
review-docs skill -- the linter cannot see any of those.

## Sentence construction (Simplified Technical English)

MUST One idea per sentence. One instruction per sentence, unless two actions happen at the same time.
MUST About 20 words for an instruction or a warning; about 25 for descriptive text.
MUST Active voice with the actor named. Use the passive only when the actor is unknown, is any conforming implementation, or is the reader.
MUST One word, one meaning. One name, one thing: never call the same thing by two names in one document.
MUST Use a verb for an action: "analyze the log", not "perform an analysis of the log".
MUST Put a condition before the command it governs: "To rebuild the index, run X", not "Run X to rebuild the index".
MUST Six sentences per paragraph at most, one topic each. Use a vertical list for steps, one action per item, imperative.

## Claims and evidence (Orwell, restated)

MUST Every claim names a checkable particular: a number, a path, a command, a version, a named event. An abstraction is not a substitute for evidence you do not have.
MUST Delete any adjective you cannot back with a number, benchmark, or feature list. Where the fact exists, state the fact and drop the adjective.
MUST Delete every span whose removal changes no proposition, obligation, or referent.
MUST Name who acted. An abstraction is not an actor: "the team fixed it that week", never "the complaint becomes a fix". If no person fits, use "you".
NOT A figure of speech you are used to seeing in print. Write the fact, a fresh image, or nothing.
NOT Two physical images colliding in one sentence.
NOT Reporting a failure, cost, or harm without naming who did what to whom.

## All genres

MUST State what the artifact does -- never effort, intent, process, or journey.
MUST Lists and tables over prose paragraphs.
MUST Greenfield has no history: state the current design as the design; do not narrate change ("revised", "previously Y now Z", "we dropped X").
MUST Cut the claim, not the hedge: a doc describing unbuilt behavior is fixed by deleting the passage, not by deleting "coming soon".
NOT Status language, or history narration in a document body.
NOT Justify a choice inside the artifact. The doc states what IS; the reason belongs in the commit or an ADR. Write the rationale only when the reader cannot recover it from the text (a constraint, an invariant, a measured number that decided a threshold), when the genre exists to record a decision (ADR, spec, commit message, PR body), or when the user asked for it.
NOT Over-writing -- three shapes, all of them real content in the wrong document:
  · a rejected alternative defended in place -> the decision belongs in an ADR, spec, or commit
  · an implementation cost the reader cannot act on (a timing, a speedup ratio, a process count) -> belongs in the commit that measured it; a published benchmark page or a table cell is fine
  · reassurance answering a worry never raised ("no configuration required", "it just works") -> state the positive alone, or say nothing
DEFAULT Ask of any sentence whether a reader of THIS document acts differently for having read it.

## Genre

Consumer surfaces (README, docs/ -- read by users of the artifact):

MUST Every sentence verifiable against code at HEAD; no target states, no roadmap.
MUST Every example copy-paste runnable, with a matching executable test under `examples/`.
NOT Internal references: specs/, ADRs, constitutions, tickets, extraction lineage.
DEFAULT Mention another package only when this artifact imports or requires it at runtime.

Change surfaces (PR bodies, commit messages, release notes):

MUST Describe the delta: what changed · why · test plan; every claim maps to a diff hunk.
NOT "Lays the groundwork", "first step towards", roadmap sections.
NOT Hand-editing CHANGELOG.md where release-please or changesets generate it.

Internal surfaces (specs, ADRs, constitutions, CONTRIBUTING, runbooks):

DEFAULT Internal references allowed -- link, do not restate.
MUST Same prose discipline as consumer surfaces; structured status metadata allowed, status narration in body prose is not.
DEFAULT Run `--profile strict` on runbooks and reference material: a procedure a reader misreads is a defect.
