# Write Docs

Condensed doc-writing rules. The write-docs skill owns the full genre
references and the prose gate; invoke the skill rather than its linter directly,
since the patterns cannot reach the register judgement. When de-slopping
prose or reviewing AI-drafted text, load the skill's `references/ai-tells.md`
index and the section files it points to,
which pairs AI-generation markers with rewrite moves. If its Last-researched
date is over ~12 months old, flag that the lexical sections need a research
refresh before relying on them.

All genres:

MUST State what the artifact does -- never effort, intent, process, or journey.
MUST Delete any adjective you cannot back with a number, benchmark, or feature list.
MUST One idea per sentence; lists and tables over prose paragraphs.
MUST Greenfield has no history: state the current design as the design; don't narrate change ("revised", "previously Y now Z", "we dropped X").
MUST Justify a library/tool/dependency choice only when a real constraint or tradeoff drove it, then in one line; drop filler ("popular", "standard", "battle-tested").
NOT Status language: "under construction", "WIP", "coming soon", "currently", "for now", "planned", "being specified", "Draft".
NOT Slop lexicon: "seamlessly", "robust", "powerful", "comprehensive", "leverage", "blazingly fast", "battle-tested", emoji headings.
MUST Name who acted: an abstraction is not an actor. "The team fixed it that week", never "the complaint becomes a fix"; if no person fits, use "you".
MUST Cut the claim, not the hedge: a doc describing unbuilt behavior is fixed by deleting the passage, not by deleting "coming soon".
NOT Justify a choice inside the artifact. The doc states what IS; the reason it is that way belongs in the commit or an ADR. Write the rationale only when the reader cannot recover it from the text (a constraint, an invariant, a measured number that decided a threshold), when the genre exists to record a decision (ADR, spec, commit message, PR body), or when the user asked for it.
NOT Over-writing -- three shapes, all of them real content in the wrong document:
  · a rejected alternative defended in place ("X rather than Y, because...", "for the same reason it does not...", "the earlier implementation") -> the decision belongs in an ADR, spec, or commit
  · an implementation cost the reader cannot act on (a timing, a speedup ratio, a process count) -> belongs in the commit that measured it; a published benchmark page or a table cell is fine
  · reassurance answering a worry never raised ("nothing here needs a package manager", "works as soon as it is on disk", "no configuration required", "it just works") -> state the positive alone, or say nothing
DEFAULT Ask of any sentence whether a reader of THIS document acts differently for having read it.

Consumer surfaces (README, docs/ -- read by users of the artifact):

MUST Write for the released artifact: every sentence verifiable against code at HEAD; no target states or roadmap.
MUST Every example is copy-paste runnable and has a matching executable test under `examples/`.
NOT Internal references: specs/, ADRs, constitutions, tickets, extraction lineage ("extracted from X").
DEFAULT Mention another package only when this artifact imports or requires it at runtime.

Change surfaces (PR bodies, commit messages, release notes):

MUST Describe the delta: what changed · why · test plan; every claim maps to a diff hunk.
NOT "Lays the groundwork", "first step towards", roadmap sections.
NOT Hand-editing CHANGELOG.md in repos where release-please or changesets generate it.

Internal surfaces (specs, ADRs, constitutions, CONTRIBUTING, runbooks):

DEFAULT Internal references allowed -- link, do not restate.
MUST Same prose discipline as consumer surfaces; structured status metadata allowed, status narration in body prose is not.
