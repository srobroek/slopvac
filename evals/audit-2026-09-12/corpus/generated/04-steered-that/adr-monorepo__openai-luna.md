# ADR: Consolidate Four Repositories into One Monorepo

- **Status:** Accepted
- **Decision:** Move the four service repositories into one monorepo.
- **Audience:** Contributors maintaining the repository after migration.

## Context

Six developers maintain four services that currently reside in separate repositories.

Three services consume shared Protocol Buffers schemas.

Git submodules allowed schema versions to drift, and that drift caused two production incidents.

The build system must remain within a monthly CI budget of 2,000 minutes.

Contributors need one repository view for service code, shared schemas, tests, and ownership rules.

## Decision

Create one Git repository with the following top-level layout:

```text
services/
  service-a/
  service-b/
  service-c/
  service-d/
proto/
build/
docs/
```

Store shared Protocol Buffers schemas under `proto/`.

Treat `proto/` as the single source of truth for schemas consumed by the three dependent services.

Generate language-specific schema artifacts during the build instead of committing generated artifacts.

Require schema changes to run compatibility checks against all three consuming services.

Require each service to retain an independent build, test, and deploy target inside the monorepo.

Configure CI to identify changed paths before scheduling service jobs.

Run the affected service jobs when a service directory changes.

Run all three schema consumer jobs when `proto/` changes.

Run repository-wide checks only for changes to shared build logic, dependency manifests, CI configuration, or root-level tooling.

Track monthly CI usage and keep total consumption at or below 2,000 minutes.

Document service ownership in each service directory and schema ownership in `proto/`.

Use one repository history for coordinated changes across schemas and consuming services.

## Requirements

| ID | Requirement | Acceptance criterion |
|---|---|---|
| ADR-001 | The monorepo must contain four service directories. | The repository contains exactly four entries under `services/`, one for each migrated service. |
| ADR-002 | The monorepo must contain one canonical schema directory. | The three dependent services reference schemas from `proto/` rather than separate repositories. |
| ADR-003 | Schema changes must test all consumers. | A pull request changing `proto/` schedules compatibility and service tests for all three consumers. |
| ADR-004 | Unrelated service changes must avoid unrelated jobs. | A pull request changing only one service does not schedule tests for the other three services. |
| ADR-005 | CI must remain within the cost cap. | The monthly CI report records 2,000 minutes or fewer. |
| ADR-006 | Each service must preserve independent delivery. | Contributors can build, test, and deploy each service without building all four services. |
| ADR-007 | Contributors must find ownership information locally. | Each service directory and `proto/` contains an ownership file with named maintainers or teams. |

## CI Selection Rules

| Changed path | Required jobs |
|---|---|
| `services/service-a/**` | Service A build, test, and packaging jobs |
| `services/service-b/**` | Service B build, test, and packaging jobs |
| `services/service-c/**` | Service C build, test, and packaging jobs |
| `services/service-d/**` | Service D build, test, and packaging jobs |
| `proto/**` | Compatibility checks and jobs for services A, B, and C |
| `build/**` | Jobs for all four services |
| Root dependency manifests | Jobs for all four services |
| CI configuration | Repository-wide validation |
| Documentation only | Documentation validation |

## Consequences

Contributors can review schema and consumer changes in one pull request.

The three schema consumers use one versioned schema source.

The repository must maintain path-based CI selection and dependency mapping.

A schema change consumes CI time for three services instead of one schema repository job.

The six developers must coordinate ownership and review rules in one repository.

Service teams retain independent deployment targets despite sharing repository storage.

The CI budget requires monthly reporting and periodic adjustment of job parallelism or test scope.

Repository-level build changes affect all four services and require broader validation.

## Rejected Alternatives

- **Git submodules:** Rejected because schema versions drifted twice in production.
- **Meta-repository tool:** Rejected because six developers could not justify its learning cost.
- **Separate schema repository:** Rejected because it would preserve version coordination across repository boundaries.
- **Unfiltered monorepo CI:** Rejected because running all service jobs for every change could exceed 2,000 minutes per month.

## Contributor Guidance

When a change modifies a schema, update the schema and its three consumers in the same pull request.

When a change modifies one service, avoid editing shared build files unless the change requires it.

When a change modifies shared build logic, run validation for all four services.

When a change adds a service dependency, update the CI path-to-job mapping and ownership documentation.

Before merging CI changes, verify that the projected monthly usage remains at or below 2,000 minutes.
