# ADR: Consolidate Four Service Repositories into One Monorepo

- **Status:** Accepted
- **Date:** 2026-09-13

## Context

Six developers maintain four services in four Git repositories.

Three services consume the same protobuf schemas. The fourth service does not consume those schemas.

Separate repositories require coordinated schema updates across three service revisions. Production experienced two incidents involving deployed schema-version drift.

CI usage must remain at or below 2,000 provider-recorded minutes per calendar month.

## Decision

The team will store all four services and the shared protobuf schemas in one Git repository.

The repository will use this directory structure:

```text
services/
  <service-one>/
  <service-two>/
  <service-three>/
  <service-four>/
schemas/
  protobuf/
```

Each service will retain its own build, test, release, and deployment configuration.

Each schema consumer will compile against the protobuf schemas from the same repository revision.

A schema change and its required consumer changes must merge through one pull request.

CI will select jobs from changed paths:

- A service-only change will run checks for that service.
- A protobuf schema change will run schema checks and checks for all three schema consumers.
- A repository-level CI change will run checks for all four services.
- A change limited to the fourth service will not run checks for the three schema consumers.
- CI will cancel superseded runs for the same pull request.

The CI provider’s monthly usage report will verify compliance with the 2,000-minute cap.

## Consequences

Schema authors can update schemas and affected consumers in one repository revision.

Each merged revision must leave the protobuf schemas compatible with all three schema consumers.

Path-based CI limits service-only changes to one service’s checks. Schema changes require checks for three services and the schemas.

Each service keeps an independent release and deployment cadence.

A repository access failure affects development for all four services.

Contributors must check out the source trees for all four services.

Repository-level tooling changes require validation across all four services.

## Rejected Alternatives

- **Git submodules:** Rejected because separate schema pointers produced two schema-version drift incidents in production.
- **Meta-repository tool:** Rejected because all six developers would learn another command and configuration model while retaining separate repository revisions.

## Verification

The migration satisfies this decision when all five checks pass:

1. Confirm that one checkout contains four directories under `services/`.
2. Confirm that shared protobuf schemas reside under `schemas/protobuf/`.
3. Change one schema and confirm that CI checks all three schema consumers.
4. Change only the fourth service and confirm that CI skips the other three services.
5. Confirm that the CI provider reports no more than 2,000 consumed minutes for each calendar month.

## Review Triggers

Review this decision if the CI provider reports more than 2,000 consumed minutes during one calendar month.

Review this decision if fewer than two services consume the protobuf schemas.
