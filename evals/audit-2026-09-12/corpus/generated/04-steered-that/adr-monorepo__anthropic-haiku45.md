# ADR: Monorepo for Four Services with Shared Protobuf Schemas

**Status:** Accepted

## Context

Four services share protobuf schemas across three of them. Six developers maintain these repositories. CI pipeline cost is capped at 2,000 minutes per month.

Schema versioning drift occurred twice in production with git submodules as the dependency mechanism. A meta-repo tool was evaluated but rejected due to toolchain learning cost for a six-person team.

## Decision

Consolidate the four repositories into a single monorepo. Each service occupies its own directory at the repository root. Protobuf schemas reside in a shared `proto/` directory at the repository root. A single CI pipeline runs per commit, with service-specific build steps triggered by file-change filters to stay within the 2,000-minute monthly budget.

## Consequences

**Positive:**
- Protobuf schema changes and their dependents are committed atomically, eliminating version drift.
- A single CI build per commit stays within budget when service-level change filters prevent redundant builds.
- Contributors see all four services and their dependencies in one clone, reducing mental overhead for cross-service features.
- Schema ownership is explicit: one protobuf file state is the source of truth for all three dependent services.

**Negative:**
- All four services share a single release cadence and tag history; services cannot be versioned independently.
- The repository size grows with all four service histories, increasing clone time for new contributors.
- A breaking change in one service requires coordination across the six developers before merge, since all code lives on main.

**Constraints and trade-offs:**
- Service-specific CI triggers (fire builds only when service code or shared `proto/` changes) are required to meet the 2,000-minute budget. Implement as native CI condition logic, not shell wrapper scripts.
- Schema changes touching the `proto/` directory trigger rebuilds for all three dependent services in a single job, not separately.
- The six developers must adopt a pre-merge review discipline for changes touching shared code (the `proto/` directory and any cross-service integration code).

## Rejected Alternatives

| Alternative | Reason |
|---|---|
| Git submodules | Schema version drift occurred twice in production with submodule pinning. Commit hash references are decoupled from schema code changes and are prone to skew during rapid development. |
| Meta-repo tool (e.g., Bazel, Pants) | Learning cost for a six-person team outweighs the benefit; contributors would spend weeks learning tool semantics and debugging tool-specific issues before delivering features. Monorepo achieves the same atomicity with standard Git and CI primitives. |
