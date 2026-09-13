# ADR-0012: Merge Four Service Repositories into One Monorepo

**Status:** Accepted

## Context

Four repositories — `orders`, `billing`, `inventory`, and `notifications` — each build and deploy independently. `orders`, `billing`, and `inventory` share protobuf schemas for their inter-service APIs. The team has six developers. CI spend is capped at 2,000 minutes per month.

Git submodules held the shared schemas in a fifth repository, `proto-shared`, referenced by pointer commit. Schema versions drifted from the pinned submodule commit twice in production: once in `orders` in 2025-11, once in `billing` in 2026-02. Both incidents shipped a service against a newer schema than its dependents expected, breaking deserialization at runtime.

The team evaluated a meta-repo tool (Google's `repo` tool) to coordinate the four repositories without merging history. Adopting it requires each developer to learn a second version-control workflow layered on top of Git. No developer on the team has prior experience with it.

## Decision

Merge `orders`, `billing`, `inventory`, `notifications`, and `proto-shared` into one repository, `platform`, preserving commit history via `git filter-repo` and subtree merge. The `proto/` directory holds the shared protobuf schemas. Each service keeps its own top-level directory: `services/orders`, `services/billing`, `services/inventory`, `services/notifications`.

CI runs a single pipeline per push. A path-filter step determines which services changed and runs only their build and test jobs, plus the jobs for any service that imports `proto/`. A change to `proto/` triggers the build and test jobs for `orders`, `billing`, and `inventory`, since all three import it; it does not trigger `notifications`, which does not.

## Consequences

- Schema changes and their consuming service changes land in one commit, eliminating the pinned-commit drift that caused the 2025-11 and 2026-02 incidents.
- CI cost stays under the 2,000-minute cap because path filtering skips jobs for unaffected services; a change scoped to `notifications` alone runs zero jobs for the other three services.
- Four repositories collapse into one; branch protection, issue tracking, and release tagging move from four configurations to one.
- A contributor changing `proto/` must run the test suites for `orders`, `billing`, and `inventory` locally before pushing, since a CI failure in any of the three blocks the merge.
- Git history for all five source repositories lives in `platform`; `git log --follow` on a moved file still traces its origin repository.

## Rejected alternatives

- **Git submodules** (previous state): pinned-commit references let dependents run against a stale schema version, causing the 2025-11 `orders` and 2026-02 `billing` production incidents.
- **Meta-repo tool (`repo`)**: requires every developer to learn a second version-control workflow on top of Git; no developer on the team has used it.
