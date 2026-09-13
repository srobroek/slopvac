# ADR: Consolidate Four Repositories into One Monorepo

- **Status:** Accepted
- **Decision:** Move four service repositories into one monorepo.
- **Audience:** Contributors maintaining the monorepo after migration.

## Context

The system contains four services that currently live in separate repositories.

Three services consume shared Protocol Buffers schemas.

Production has experienced schema-version drift twice because services could deploy different schema revisions.

The development team contains six developers.

The CI budget cannot exceed 2,000 minutes per month.

Contributors need one repository that exposes service code, shared schemas, dependency changes, and validation rules.

## Decision

The team will store all four services and the shared Protocol Buffers schemas in one monorepo.

The repository will use this directory layout:

```text
services/
  service-a/
  service-b/
  service-c/
  service-d/
schemas/
  protobuf/
```

The team will maintain one canonical schema version under `schemas/protobuf/`.

The three consuming services will generate or consume schema artifacts from that canonical directory during their builds.

The fourth service will remain in the monorepo without a dependency on the shared schemas unless its code later adopts them.

The CI pipeline will identify changed paths before running service-specific jobs.

A change under `services/service-a/` will run the `service-a` validation jobs.

A change under `schemas/protobuf/` will run validation jobs for all three consuming services.

A change that affects shared build configuration will run validation jobs for all four services.

The team will track monthly CI usage against the 2,000-minute budget.

The team will review CI job scope when monthly usage reaches 1,600 minutes.

The repository will require schema validation before merging changes under `schemas/protobuf/`.

The repository will require all affected consuming services to pass their CI jobs before merging schema changes.

The team will preserve each repository's commit history during migration when the migration tooling supports history preservation.

## Consequences

### Benefits

Contributors will review schema changes and affected service changes in one pull request.

The three consuming services will validate against the same schema revision before merging.

The monorepo will make cross-service dependency changes visible in one change set.

The six developers will use one issue, review, and CI location for all four services.

### Costs

The repository will contain four service build systems and one shared schema area.

A broad configuration change can trigger CI jobs for all four services.

The team must maintain path-based CI rules and monthly usage tracking.

The team must resolve dependency and toolchain conflicts within one repository.

## Rejected Alternatives

- **Git submodules:** The team rejected submodules because schema versions drifted twice in production.
- **Meta-repository tool:** The team rejected a meta-repository tool because its learning cost exceeded the team's adoption limit.
- **Four separate repositories:** The team rejected separate repositories because they allow schema and service changes to merge against different revisions.

## Contributor Rules

Contributors must place shared Protocol Buffers definitions under `schemas/protobuf/`.

Contributors must update affected generated artifacts or generation commands in the same change.

Contributors must run all three consuming service validations for schema changes.

Contributors must keep service-specific code under its corresponding `services/<service-name>/` directory.

Contributors must update CI path rules when they add a service or shared build dependency.

Contributors must not copy shared schema definitions into service directories.

## Acceptance Criteria

- The monorepo contains four service directories under `services/`.
- The monorepo contains one canonical Protocol Buffers directory under `schemas/protobuf/`.
- A schema change triggers validation for three consuming services.
- A service-only change does not trigger unrelated service jobs.
- A shared build configuration change triggers validation for four services.
- Monthly CI usage remains at or below 2,000 minutes.
- Contributors can review a schema change and its consuming service changes in one pull request.
