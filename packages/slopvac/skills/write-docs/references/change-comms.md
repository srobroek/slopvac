# Change Communication (PR bodies, commit messages, release notes)

The one genre that describes a delta. Past tense about the change belongs here,
and only here.

## Exception routing

Exception routing is based on document purpose, not a passage's wording. Migration guides and explicit before/after change tracking use `change-comms`. ADRs and decision records, future release plans and specifications, and explicitly historical reports or data use `internal`. A procedure or reference document uses `reference` only when its purpose is current operation or reproducibility. Do not classify one of these documents as `consumer` to exempt its history or future content.

## PR body

MUST Shape: what changed · why · test plan (close keywords and merge rules: see steering-git-workflow).
MUST Every claim under "what changed" maps to a hunk in the diff.
NOT "Lays the groundwork", "first step towards", "part of a broader effort", roadmap sections.
NOT File-by-file diff restatement -- state behavior changes, not file lists.

## Commit messages

MUST Conventional commit; imperative subject naming the behavior change.
NOT Vague subjects: "improve", "enhance", "update", "polish" without the concrete change.

## Changelog

MUST Repos with release-please or changesets: never hand-edit CHANGELOG.md -- quality comes from commit subjects and PR titles.
DEFAULT Hand-maintained changelogs: one line per user-visible change; internal refactors only when they change behavior a consumer can observe.
