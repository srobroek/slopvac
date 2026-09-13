# Consolidate Four Service Repositories Into One Monorepo

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-09-13 |
| Owners | Six-person engineering team |
| Scope | Four services and their shared protobuf schemas |

## Context

Six developers maintain four services in four service repositories.

Three services consume the same protobuf schemas. Independent schema versions caused two production incidents when deployed versions drifted.

Hosted CI usage must not exceed 2,000 minutes per billing month.

Schema changes can require coordinated updates across three services. Separate repositories cannot merge those updates in one commit.

## Decision

The engineering team will consolidate the four service repositories into one monorepo.

The monorepo will use this top-level structure:

```text
/
├── services/
│   └── <service-name>/
├── schemas/
│   └── protobuf/
└── ci/
    └── service-dependencies.yml
```

Each service will occupy one directory under `/services`.

The `/schemas/protobuf` directory will contain the canonical shared protobuf schemas. The three consumers must resolve shared schemas from this directory.

Services must not store copies of shared protobuf schemas under `/services`.

A schema change and its required consumer changes must enter the default branch through one pull request.

The `/ci/service-dependencies.yml` file will map repository paths to service workflows. Repository owners must review changes to this mapping.

### CI execution

CI will select workflows from changed paths.

- A change under one service directory must build and test that service.
- A change under `/schemas/protobuf` must build and test the three protobuf consumers.
- A change to shared build configuration must build and test all four services.
- A change under `/ci` must validate the path mapping and all referenced workflow names.
- CI must cancel superseded runs from the same pull request.
- CI must prevent duplicate branch and pull-request runs for the same commit.

Repository administrators must configure the CI provider to deny hosted jobs after usage reaches 2,000 minutes within one billing month.

When usage reaches 1,600 minutes, repository administrators must disable scheduled workflows until the next billing month.

### Migration

Migration owners will preserve each service repository’s commit history under its corresponding `/services/<service-name>` directory.

After migration, migration owners will archive the four service repositories and link each archived README to the monorepo.

The migration is complete when these checks pass:

- The default branch contains four service directories under `/services`.
- The three protobuf consumers resolve shared schemas from `/schemas/protobuf`.
- No duplicate shared protobuf schema remains under `/services`.
- A schema-only test change triggers exactly three service workflows.
- A service-only test change triggers exactly one service workflow.
- The CI provider enforces the 2,000-minute monthly limit.

## Consequences

Contributors can update shared schemas and three consumers in one commit.

Every merged commit references one canonical version of each shared protobuf schema.

A shared schema change runs three service test suites instead of one service test suite.

A service-local change runs one service test suite instead of all four service test suites.

Each monorepo clone contains the Git history and working tree for all four services.

Repository access grants each contributor access to all four service directories.

An outage affecting the monorepo blocks changes to all four services.

The CI path mapping becomes part of the test boundary. An incorrect mapping can omit a required service workflow.

## Rejected alternatives

- **Git submodules:** Independently pinned schema commits caused schema-version drift in two production incidents.
- **Meta-repository tool:** The tool would require all six developers to learn and maintain an additional synchronization and release model.
