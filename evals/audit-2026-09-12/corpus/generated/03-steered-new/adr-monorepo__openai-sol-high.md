# ADR: Consolidate four repositories into one monorepo

- **Status:** Accepted
- **Date:** 2026-09-13
- **Scope:** Four services and their shared protobuf schemas

## Context

The six-developer team maintains four service repositories.

Three services consume protobuf schemas shared across repository boundaries.

Schema versions drifted twice in production when service repositories referenced different schema revisions.

CI usage must remain within 2,000 runner minutes per calendar month.

Schema changes and corresponding consumer updates require one atomic commit.

Service-specific changes must avoid running test suites for unaffected services.

## Decision

The team stores all four services and the shared protobuf schemas in one Git repository.

The monorepo uses this directory structure:

```text
services/
  <service-name>/
schemas/
  protobuf/
```

Each service retains its own build, test, deployment, and release configuration.

Each service release records the monorepo commit SHA that produced its artifact.

The migration imports each repository's Git history beneath its service directory.

The four source repositories become read-only after migration and direct contributors to the monorepo.

### CI selection

CI selects jobs from changed paths.

| Changed path | Required CI jobs |
|---|---|
| `services/<service-name>/**` | Test the changed service |
| `schemas/protobuf/**` | Validate schemas and test all three schema consumers |
| Multiple service directories | Test each changed service |
| Repository-wide build or CI configuration | Test all four services |

A pull request that changes protobuf schemas may update all affected consumers in the same commit.

The CI administrator configures a hard limit of 2,000 runner minutes per calendar month.

CI blocks additional runner use after the account reaches the monthly limit.

## Consequences

- One commit identifies the exact schemas and service code used together.
- Schema validation covers all three consumers before a schema change merges.
- Service-only pull requests omit unrelated suites instead of running all four service suites.
- Repository-wide configuration changes run all four service suites.
- CI cannot validate additional changes after monthly usage reaches 2,000 runner minutes.
- Contributors use one checkout and one pull request workflow across four services.
- Service releases remain independent despite sharing one commit history.
- Repository permissions apply across four services unless the hosting platform supports path-based ownership controls.

## Rejected alternatives

- **Git submodules:** Rejected because schema revisions drifted twice in production across the three schema-consuming services.
- **Meta-repository tool:** Rejected because all six developers would need to learn and maintain a second repository-synchronization workflow.
