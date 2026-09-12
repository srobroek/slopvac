# ADR: Move Four Service Repositories into One Monorepo

- **Status:** Accepted
- **Decision:** Consolidate the four service repositories into one monorepo.

## Context

Four services are maintained by six developers.

Three services consume shared Protocol Buffer schemas.

The schema versions drifted twice in production when the schemas remained separately versioned.

The organization limits continuous integration spending to 2,000 minutes per month.

Contributors need one repository structure that identifies schema changes, service dependencies, and required validation.

## Decision

The team will move the four repositories into one monorepo.

The monorepo will contain one top-level directory for each service and one top-level directory for shared Protocol Buffer schemas.

```text
/
├── services/
│   ├── service-a/
│   ├── service-b/
│   ├── service-c/
│   └── service-d/
└── schemas/
    └── protobuf/
```

The three schema-consuming services will import schemas from `schemas/protobuf/`.

The fourth service will remain independent from the shared schemas unless its code later adds an explicit dependency.

The repository will version schema and service changes together.

The CI configuration will run schema validation and tests only for affected services and their dependents.

The CI configuration must keep total monthly usage at or below 2,000 minutes.

The team will document dependency edges between `schemas/protobuf/` and the three consuming services in the repository's build configuration.

## Consequences

Contributors can review a schema change and its three consuming-service changes in one commit.

The repository removes separate schema version selection for the three consuming services.

A schema change requires validation for `schemas/protobuf/` and all three dependent services.

CI path filtering becomes a repository requirement.

A faulty dependency graph can omit required validation, so contributors must update dependency metadata when they add or remove schema usage.

Six developers will share one repository, one issue location, and one change history.

The repository may require additional local build configuration to keep unrelated service tests independent.

The CI configuration must expose monthly usage so the team can compare actual usage with the 2,000-minute cap.

## Rejected alternatives

- **Git submodules:** Rejected because schema versions drifted twice in production.
- **Meta-repository tool:** Rejected because the tool's learning cost was not acceptable for six developers.
- **Separate repositories with manual schema coordination:** Rejected because it preserves independent schema versions and does not prevent production drift.

## Contributor requirements

When you change a shared schema, update every affected service in the same change.

When you add a schema dependency, update the build dependency graph and CI path rules.

When you remove a schema dependency, remove its build dependency edge and CI trigger.

When you change a service without changing its dependencies, run that service's scoped checks.

When you change dependency metadata, run the affected service checks and the dependency-graph validation.

When CI usage approaches 2,000 minutes in one month, reduce redundant jobs before adding new CI workloads.
