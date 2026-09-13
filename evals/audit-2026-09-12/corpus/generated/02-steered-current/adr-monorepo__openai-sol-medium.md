# ADR-001: Consolidate Four Service Repositories into One Monorepo

- **Status:** Accepted
- **Date:** 2026-09-12
- **Scope:** Source control, protobuf ownership, release boundaries, and CI execution

## Context

Six developers maintain four services in four Git repositories.

Three services consume the same protobuf schemas. Separate schema references allowed schema versions to drift during two production deployments.

CI usage across the four services must not exceed 2,000 minutes per calendar month.

Contributors need one commit boundary for changes that modify a protobuf schema and its three consumers.

## Decision

The team will move the four services and their shared protobuf schemas into one Git repository.

The repository will use this top-level structure:

```text
/
├── services/
│   ├── service-a/
│   ├── service-b/
│   ├── service-c/
│   └── service-d/
├── schemas/
│   └── protobuf/
├── tooling/
└── .github/
    └── workflows/
```

`schemas/protobuf/` will contain the canonical protobuf source for `service-a`, `service-b`, and `service-c`.

Each protobuf change will include required consumer changes in the same pull request.

CI will calculate affected services from changed paths and the protobuf dependency graph.

A change under `schemas/protobuf/` will run schema checks and tests for all three protobuf consumers.

A service-only change will run that service’s checks unless the change also modifies shared tooling or CI configuration.

CI maintainers will review provider usage each calendar month and keep billed usage at or below 2,000 minutes.

Each service will retain its own deployment workflow and use tags named `<service>/v<major>.<minor>.<patch>`.

Repository protection will require affected-service checks to pass before a pull request enters the default branch.

## Consequences

A single commit can update a protobuf schema and all three consumers.

The monorepo gives the six developers one pull-request queue, permission model, and branch-protection configuration.

Each checkout contains four services, shared schemas, repository tooling, and CI configuration.

Path filtering and dependency mapping become required CI configuration.

A default-branch access failure affects contributions to all four services.

Service-specific tags preserve four release sequences without restoring separate repositories.

## Rejected Alternatives

- **Git submodules:** Reject submodules because per-repository schema pointers failed to prevent two production schema-version drifts.
- **Meta-repository tool:** Reject a meta-repository tool because six developers would need to learn an additional synchronization and release command model.
- **Four independent repositories:** Reject separate repositories because they cannot commit schema and three-consumer changes as one Git transaction.

## Acceptance Criteria

- One Git repository contains four directories under `services/`.
- `schemas/protobuf/` contains the protobuf source consumed by exactly three services.
- One pull request can change a protobuf schema and each affected consumer.
- A protobuf change triggers CI checks for `service-a`, `service-b`, and `service-c`.
- A change confined to `services/service-d/` does not trigger tests for the other three services.
- CI billing remains at or below 2,000 minutes for each calendar month.
- Each service can deploy from a service-specific version tag.
