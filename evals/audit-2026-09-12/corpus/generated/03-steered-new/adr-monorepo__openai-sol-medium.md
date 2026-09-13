# ADR-001: Consolidate four service repositories into one monorepo

- **Status:** Accepted
- **Date:** 2026-09-13
- **Owners:** Six-person development team

## Context

The team maintains four services in four Git repositories.

Three services consume the same protobuf schemas. Coordinated schema changes require synchronized commits and deployments across three repositories.

Schema versions drifted twice in production when Git submodules referenced different commits. The team must prevent another independently versioned schema reference.

CI usage must not exceed 2,000 billed minutes per calendar month. Building all four services for every change would consume minutes unrelated to changed paths.

The six developers contribute across service boundaries. Repository-level access controls do not represent separate ownership groups.

## Decision

The team will move the four repositories into one Git repository. The migration will preserve each repository's commit history.

The monorepo will use this top-level structure:

```text
/
├── services/
│   ├── <service-one>/
│   ├── <service-two>/
│   ├── <service-three>/
│   └── <service-four>/
├── schemas/
│   └── protobuf/
├── tooling/
└── docs/
    └── decisions/
```

Each service will retain its build files beneath `services/<service-name>/`. Shared protobuf sources will reside only in `schemas/protobuf/`.

The three schema consumers will compile schemas from the monorepo commit under test. CI and release workflows will not fetch schemas from external repositories.

A schema change and its required consumer updates will use one pull request. CI will reject incompatible schema changes unless the pull request contains an approved compatibility exception.

CI will select jobs from changed paths:

| Changed path | Required CI scope |
|---|---|
| `services/<service-name>/**` | Changed service |
| `schemas/protobuf/**` | Schema checks and three schema consumers |
| `tooling/**` | Four services |
| Root build or CI configuration | Four services |
| `docs/**` only | Documentation checks |

CI configuration will enforce a monthly limit of 2,000 billed minutes. Scheduled and optional jobs will stop before their execution could exceed that limit.

The team will review CI usage after each 500 billed minutes. The review will compare projected monthly usage against the 2,000-minute limit.

All six developers will receive contributor access to the monorepo. Path-based ownership rules will request reviewers without restricting cross-service contributions.

Each service will keep an independent release version and deployment workflow. A monorepo commit will not require the four services to release together.

## Consequences

Schema changes and consumer updates can share one commit. Code review can evaluate the schema and all three affected services together.

Path-based CI avoids building unchanged services for service-local changes. Schema and infrastructure changes still test every affected service.

The repository will contain four build systems unless contributors consolidate them through a separate decision. Root commands must delegate to each service's existing build commands.

Repository clones will contain the history and files of all four services. Contributors cannot clone one service as an independent repository.

CI configuration becomes a shared dependency for four services. Changes under the root CI path require tests for all four services.

A failed schema compatibility check blocks the complete pull request. Contributors must update the schema or its three consumers before merging.

Service releases remain independent. Release automation must map tags and artifacts to one path under `services/`.

## Rejected alternatives

- **Git submodules:** Rejected because independent schema references caused production version drift twice.
- **Meta-repository tool:** Rejected because six developers would need to learn and maintain another repository orchestration tool.
- **Four repositories with published schema packages:** Rejected because package versions would preserve independent schema and consumer commits.
