# Architecture Decision Record: Monorepo for Four Services

**Status:** Accepted

## Context

Four repositories handle related services that share protobuf schemas.
Three of these services depend on the same schema definitions.
Schema coordination via Git submodules failed twice in production: the submodule version reference drifted from the pinned schema version, causing the consuming service to run mismatched protocol definitions.

The team has six developers.
Monthly CI budget is capped at 2,000 minutes.
Development velocity has suffered because schema changes require coordinated commits and PRs across two or more repositories.

## Decision

Consolidate the four repositories into one monorepo with the following structure:

- `/services/` contains the four service codebases in separate directories.
- `/schemas/` contains all protobuf definitions; each service imports from this directory.
- A single `go.mod`, `package.json`, or equivalent for each language runtime.
- Continuous integration runs per-service tests and generates protocol bindings on every commit to `/schemas/` or a service directory.

Every commit atomically updates service code and its schema dependencies.
No separate schema repository exists.

## Consequences

**Schema safety:** Services cannot run mismatched schemas.
Schema and code updates arrive in one atomic commit.
This eliminates the two categories of production incidents observed with submodules.

**CI cost:** Running four separate pipelines (one per service) costs approximately 12–18 minutes per commit if each service test takes 3–5 minutes.
Assuming 80–120 commits per month across all services, monthly CI cost ranges from 960 to 2,160 minutes.
Shared test caching and parallelization can reduce this to 1,200–1,600 minutes.
This fits within the 2,000-minute budget.

**Developer workflow:** Six developers no longer coordinate schema changes across repository boundaries.
Onboarding time to understand schema dependencies decreases.
Local development requires one clone and one `make build` instead of managing four repositories and submodule state.

**Build artifact size:** Generated protocol bindings for all three affected services reside in one repository.
Binary artifact size increases by the sum of unused generated code for each developer machine.
Unused bindings in a given service are excluded from production builds via build tags or link-time stripping.

**Blast radius:** A bug in one service's code can no longer cause cascading failures in a separate repository.
All four services depend on the same test infrastructure and CI configuration, increasing risk of a shared test failure blocking all deployments.
Test infrastructure changes affect all services simultaneously.

**Version boundaries:** No minor-version incompatibilities between services occur via repository mismatches.
Service versions are released independently; the monorepo does not enforce lockstep releases.

## Rejected Alternatives

**Git submodules:** Schema versions drifted in production on two separate occasions; atomic schema + code updates were not enforced by the tool.

**Meta-repo tool:** Learning cost for six developers to master tool-specific commands and workflows (branching, merging, partial clones) exceeded project timeline; tool required a separate control plane.
