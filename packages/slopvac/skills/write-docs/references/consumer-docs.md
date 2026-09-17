# Consumer Docs (README, docs/)

Audience: a technically capable user of the released artifact with zero access to internal process. Use direct, concise prose; omit primers and remedial definitions unless they are required to complete the documented task.

## Current-artifact contract

MUST Describe the current behavior, interface, configuration, constraints, and reader actions needed to use, verify, or reproduce the artifact.
MUST Apply the deletion test to every sentence: delete anything that does not change a reader action or understanding of that contract.
Keep the document focused on the current artifact. Exclude work logs, postmortems, roadmaps, task lists, optimization diaries, and life stories.
Keep process narration, past job IDs, phase timings, causal journeys, superseded behavior, rejected alternatives, future tasks, and operational archaeology in internal or change-comms documents.
Keep cache and performance narratives only when a current actionable limit, capacity, or reproduction step depends on them.

## Released-artifact test

MUST Every sentence is verifiable against the code at HEAD of the branch being merged.
MUST A sentence that stops making sense once git history, specs, and this conversation vanish gets deleted.
MUST Feature flags: document behavior that is on by default, or document the flag as opt-in configuration -- never the roadmap.
NOT Target states, milestones, completion percentages, "phase 2", section names like "Planned API".
MUST Cut the claim, not the hedge: deleting "coming soon" from a sentence about an unbuilt feature makes the doc assert the feature ships. Delete the passage, or move it to an allowed future-intent genre.
DEFAULT A pre-release artifact says so once, as structured metadata (a status field, a version column) -- never as body prose that leaves the rest reading as shipped.

## Exception routing

Exception routing follows document purpose. Migration guides and explicit before/after change tracking use `change-comms`. ADRs, decision records, future release plans, specifications, and explicitly historical reports or data use `internal`. Procedures and reference documents use `reference` for current operation or reproducibility.

## Structure (README skeleton -- omit empty sections, never pad)

1. Name + one-line purpose (what it does, for whom)
2. Install
3. Usage -- minimal working invocation first
4. Examples -- one per major capability
5. Configuration -- table: name · type · default · effect
6. License

## Examples

MUST Copy-paste runnable exactly as written against a fresh install.
MUST Each example has a matching executable test under `examples/` in the repo; run it before shipping the doc.
DEFAULT Environment blocks execution (credentials, external service) → state that in the PR body; never silently skip.
MUST Present runnable examples as complete, executable code rather than pseudo-code.

## Internal references

Keep links to and mentions of internal references out of consumer docs. Keep extraction lineage in internal documentation.
DEFAULT Mention another package only when this artifact imports or requires it at runtime -- one line naming the dependency and what it provides.

## Rationale

DEFAULT State the choice; add a one-line reason only when the reader needs the constraint to use the artifact.
Keep rationale concise. Explain prerequisite concepts only when they affect use or verification. Retain safety constraints and implicit requirements.
