# Change Communication (PR bodies, commit messages, release notes)

Write for a technically capable reviewer in direct, concise prose. Explain a prerequisite, safety constraint, or non-obvious tradeoff only when it changes review, merge, release, or reproduction.

## Exception routing

Exception routing follows document purpose. Migration guides and explicit before/after change tracking use `change-comms`. ADRs, decision records, future release plans, specifications, and explicitly historical reports or data use `internal`. Procedures and reference documents use `reference` for current operation or reproducibility.

## Boundaries

MUST Keep each claim tied to a current diff, user-visible behavior change, decision, or verification result.
MUST Use the deletion test: remove process narration, author effort, job IDs, phase timings, and causal journey unless the reader needs the fact to review, merge, release, or reproduce the change.
Keep change communications focused on the current diff, user-visible behavior, decision, or verification result. Store roadmap, task-list, optimization-diary, and life-story content elsewhere. Keep future tasks and cache history only when they support a release plan, specification, current limit, capacity, cost, or test result.

## PR body

MUST Shape: what changed · why · test plan (close keywords and merge rules: see steering-git-workflow).
MUST Every claim under "what changed" maps to a hunk in the diff.
State behavior changes instead of roadmap language or file-by-file diff restatements.

## Commit messages

MUST Conventional commit; imperative subject naming the behavior change.
Use concrete subjects that name the behavior change instead of vague subjects such as "improve" or "update".

## Changelog

MUST Repos with release-please or changesets: never hand-edit CHANGELOG.md -- quality comes from commit subjects and PR titles.
DEFAULT Hand-maintained changelogs: one line per user-visible change; internal refactors only when they change behavior a consumer can observe.
