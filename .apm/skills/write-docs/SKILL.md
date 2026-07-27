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

This skill authors. The `review-docs` skill gates: it owns the linter, the AI-tells
catalog, and the verdict. Step 4 below hands off to it, and it is not optional --
a document is not finished until it has passed.

The gate checks two axes. Slop rules error, and a match says something about how
the text was produced. Craft rules warn, and a match says the writing is worse
whoever wrote it: wordiness, a dead sentence opener, a directional cross-reference,
a nominalised verb. Write against both from the start; the rules below cover the
slop axis, and the craft ones are ordinary good prose.

## Genre → reference

| Surface | LOAD |
|---|---|
| README.md, docs/**, anything a user of the artifact reads | references/consumer-docs.md |
| PR bodies, commit messages, hand-written release notes | references/change-comms.md |
| specs/, ADRs, constitutions, CONTRIBUTING, contributor/internal docs | references/internal-docs.md |

## Workflow

1. Classify the doc with the genre table; LOAD that reference before writing.
2. Author or rewrite against the genre rules plus the shared rules below.
3. Verify every claim against code at HEAD, and give every consumer example a
   runnable test under `examples/`.
4. MUST Invoke the `review-docs` skill, passing the genre from step 1. It runs
   the gate and judges the register the gate cannot see. Fix what it returns.

## Rules (all genres)

MUST State what the artifact does -- never effort, intent, process, or journey.
MUST Delete any adjective you cannot back with a number, benchmark, or feature list.
MUST One idea per sentence; lists and tables over prose paragraphs. Keep a sentence
under 34 words and put the real subject first: "There is a flag that controls X"
has spent four words before naming anything.
MUST Put the action in the verb: write "validate the token" rather than "perform
validation of the token".
MUST Cross-reference by heading name. A positional reference ("see below") breaks
for every reader who arrives at one section rather than the top.
MUST Name who acted: an abstraction is not an actor ("the team fixed it", never "the complaint becomes a fix").
MUST Cut the claim, not the hedge: a doc that describes unbuilt behavior is fixed by deleting the passage, not by deleting "coming soon".
NOT Status language: "under construction", "WIP", "coming soon", "currently", "for now", "planned", "being specified".
NOT Slop lexicon -- the prose-inflation Vale style owns the banned list; prose never restates it.
NOT History narration in a doc body ("previously", "we changed X to Y") -- deltas belong to the change-comms genre only.
NOT Over-writing -- real content in the wrong document:
  · a rejected alternative defended in place -> move the decision to an ADR, spec, or commit
  · an implementation cost the reader cannot act on (timing, process count) -> move it to the commit that measured it
  · reassurance answering a worry never raised ("no configuration required", "it just works") -> state the positive alone, or say nothing
  Ask whether a reader of THIS document acts differently for having read the sentence.
