# Architecture Decision Record: Consolidate Four Services into One Monorepo

- **Status:** Accepted
- **Date:** 2026-09-12
- **Decision owners:** Six service developers

## Context

Four repositories contain four independently deployed services.

Three services consume shared protobuf schemas. Independent repository references allowed those services to deploy different schema revisions twice in production.

The team has six developers. CI usage must not exceed 2,000 billed minutes per calendar month.

## Decision

The team will consolidate the four service repositories into one monorepo.

The monorepo will use this directory structure:

```text
services/
  <service-name>/
proto/
build/
ci/
```

Each service will retain its own build definition, release version, deployment workflow, and ownership rules.

The `proto/` directory will contain the canonical protobuf schemas. The three schema consumers will compile against this directory without repository references or copied schemas.

A schema change and its consumer updates will share one pull request. Branch protection will prevent merging that pull request until all three consumer pipelines pass.

The migration will preserve commit authors, timestamps, and messages from all four repositories.

## CI design

CI will use changed paths to select service pipelines.

- A change under `services/<service-name>/` will run that service's build and tests.
- A change under `proto/` will validate schemas and run builds and tests for all three schema consumers.
- A change under `build/` will run builds and tests for all four services.
- A change under `ci/` will run builds and tests for every service affected by the changed CI configuration.
- An unmatched dependency or executable configuration change will run builds and tests for all four services.
- CI will cancel a superseded run for the same pull request.
- A release workflow will run only for the service named by its release tag.

CI will record provider-reported billed minutes by calendar month. The team will treat 2,000 minutes as a hard monthly limit.

At 1,800 billed minutes, maintainers will disable scheduled and optional workflows until the provider resets the monthly counter. The remaining 200 minutes will be reserved for required pull-request checks.

## Ownership

The root ownership file will assign each service directory to its service owners. The file will assign `proto/` changes to owners from all three schema consumers.

Changes to `build/` or shared CI configuration will require review from two developers. Service-only changes will follow that service's ownership rules.

## Consequences

- One commit can update a protobuf schema and all three consumers.
- One pull request can verify schema compatibility before merge.
- Each service can retain an independent release schedule.
- Shared build changes can trigger four service pipelines.
- Repository access grants visibility into all four services.
- Root ownership and branch-protection rules replace four repository-level configurations.
- Path selection and run cancellation become required controls for the 2,000-minute CI limit.

## Rejected alternatives

- **Git submodules:** Independent submodule references allowed schema revisions to drift twice in production.
- **Meta-repository tool:** The tool would require all six developers to learn its commands and maintain another configuration layer.

## Acceptance criteria

The migration is complete when all checks pass:

1. Verify that the monorepo contains the preserved histories of all four repositories.
2. Verify that each service builds from its directory under `services/`.
3. Verify that all shared protobuf schemas reside under `proto/`.
4. Verify that each of the three consumers resolves schemas from `proto/`.
5. Verify that a service-only test change triggers one service pipeline.
6. Verify that a protobuf-only test change triggers all three consumer pipelines.
7. Verify that a shared build test change triggers all four service pipelines.
8. Verify that each service can produce and deploy an independently versioned release.
9. Verify that the CI billing report never exceeds 2,000 minutes in a calendar month.
