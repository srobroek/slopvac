# ADR-0001: Merge four service repositories into one monorepo

**Status:** Accepted

## Context

Four repositories currently hold separate services. Three of them import protobuf schemas from a shared package; that package has drifted from the consuming services twice in production, each time via an unsynchronized submodule pointer. The team has six developers, and CI spend must stay under 2,000 minutes per month.

## Decision

Merge the four repositories into one repository (`platform-monorepo`). Each service keeps its existing directory structure at the top level. The shared protobuf schemas move to `proto/` at the repository root, and each service imports them via the language's package manager pointing at an in-repo path.

CI runs on path-based triggers: a push touching only `service-a/` runs only `service-a`'s pipeline, and a push touching `proto/` runs the pipeline for all three consuming services. This keeps monthly CI minutes under the 2,000-minute cap.

## Rejected alternatives

- **Git submodules for the shared schema package.** Rejected: schema versions drifted from consumers twice in production because submodule pointers were not updated atomically with consumer code.
- **A meta-repo tool (e.g., a multi-repo orchestrator) to coordinate the four existing repositories.** Rejected on learning cost: the tool's workflow model has no existing expertise on the six-developer team, and onboarding time competes directly with feature work.

## Consequences

- A schema change and its consumers commit atomically in one pull request; drift between schema version and consumer code becomes structurally impossible.
- Path-based CI triggers keep unrelated services from rebuilding on every push, holding total CI minutes under the 2,000-minute monthly cap.
- Git history for each of the four services is preserved via `git subtree` merge, so `git log -- service-a/` still returns pre-merge commits.
- A single repository means a single set of branch-protection and CODEOWNERS rules to maintain, instead of four.
- Contributors must scope their working directory (or use sparse-checkout) to avoid pulling in the other three services' unrelated build artifacts.
