# ADR: Consolidate Four Service Repositories into One Monorepo

- **Status:** Accepted
- **Date:** 2026-09-12
- **Decision owners:** Service maintainers
- **Scope:** Source code, protobuf schemas, build configuration, and CI workflows for all four services

## Context

The organization maintains four services in separate repositories. Six developers contribute across these services.

Three services use shared protobuf schemas. Keeping the schemas synchronized across repositories has required explicit version updates and coordinated releases. Schema versions drifted twice in production, causing services to run against incompatible definitions.

The repositories also duplicate parts of their CI and development setup. CI usage must remain below **2,000 minutes per month**.

This decision should remain understandable to contributors who did not participate in the migration.

## Decision drivers

- Keep shared protobuf schemas at one authoritative revision.
- Prevent services from merging changes that are incompatible with a schema update.
- Keep monthly CI usage below 2,000 minutes.
- Minimize workflow complexity for a six-developer team.
- Make cross-service changes reviewable and testable as one change.
- Preserve service ownership and independent deployment.
- Avoid introducing a repository-management tool that contributors must learn and maintain.

## Decision

We will move all four service repositories into one monorepo.

The monorepo will contain:

```text
/
├── services/
│   ├── service-a/
│   ├── service-b/
│   ├── service-c/
│   └── service-d/
├── schemas/
│   └── protobuf/
├── tools/
└── ci/
```

The exact service names and language-specific directories may differ, but the following boundaries apply:

1. Each service remains an independently buildable and deployable unit.
2. Shared protobuf source files live only under `schemas/protobuf/`.
3. The three schema-consuming services generate or validate their protobuf bindings from that directory.
4. Schema and consumer changes may be submitted in the same pull request.
5. The fourth service does not acquire a dependency on protobuf tooling unless it begins consuming the schemas.
6. Service-specific dependencies remain scoped to the relevant service. The monorepo does not require all services to share dependency versions or a release cadence.
7. Ownership rules identify the reviewers for each service and for shared schemas.

## CI strategy

A monorepo can exceed the CI budget if every change builds all four services. CI will therefore use affected-path selection.

For each pull request, CI will:

- Run repository-wide lightweight checks.
- Build and test a service when files in that service change.
- Build and test all three schema consumers when protobuf schemas or schema-generation tooling change.
- Avoid building unaffected services.
- Permit an explicit full-validation run when path selection is uncertain or a contributor requests it.
- Treat changes to shared CI or build infrastructure as affecting every service unless narrower impact can be established safely.

Changes to path-selection logic must fail conservatively: uncertainty triggers more validation rather than skipping a potentially affected service.

Monthly CI usage will be monitored against the 2,000-minute cap. The operating target is at most **1,800 minutes per month**, leaving 200 minutes for retries, incident work, and unexpected full validations. If usage exceeds the target, maintainers will first reduce duplicate work, improve caching, and cancel superseded runs rather than weaken required validation.

## Protobuf policy

The files under `schemas/protobuf/` are the source of truth.

A schema change must:

1. Pass protobuf syntax and repository lint checks.
2. Pass compatibility checks against the version on the main branch.
3. Build and test each of the three consuming services.
4. Include consumer changes in the same pull request when the schema change is not backward compatible at source level.
5. Follow the repository's compatibility policy before removing or reusing fields.

Deployments remain independent. When a schema migration requires ordered rollout, the change must use an additive sequence:

1. Add the new schema elements.
2. Deploy consumers that can handle both old and new forms.
3. Begin producing the new form.
4. Remove obsolete elements only after all consumers have migrated.

Co-location makes compatible changes atomic in source control, but it does not make separately deployed services atomic at runtime.

## Repository and release model

The monorepo uses one main branch and one pull-request workflow. A merged commit records the compatible state of all services and shared schemas.

Each service retains:

- Its own build and test entry points.
- Its own deployment pipeline.
- Its own release version and changelog, where applicable.
- Its own runtime configuration and operational ownership.
- The ability to release without releasing the other services.

A change touching multiple services receives review from the owners of each affected area. A change to shared schemas receives review from the schema owners and affected service owners.

## Migration approach

The migration will proceed as follows:

1. Create the monorepo structure and repository-wide contribution guidance.
2. Import each repository while preserving useful commit history.
3. Move the authoritative protobuf schemas into `schemas/protobuf/`.
4. Update the three consuming services to use schemas from the monorepo.
5. Add affected-path CI selection and schema compatibility checks.
6. Verify that each service can build, test, and deploy independently.
7. Freeze the old repositories and redirect contributors to the monorepo.
8. Archive the old repositories after outstanding work has been migrated or closed.

The migration is complete only when production builds no longer obtain schemas or service source from the old repositories.

## Alternatives considered

### Keep separate repositories

This preserves current repository boundaries and allows each service to evolve independently.

It was rejected because shared protobuf updates would still require coordinated version publication and consumption across three repositories. That process already allowed schema versions to drift twice in production. Additional automation could reduce the risk, but it would preserve the central failure mode: related schema and consumer changes cannot be reviewed and merged as one repository change.

### Git submodules

A repository could reference a separate schema repository at a specific commit.

This was rejected because submodule pointers still require explicit updates in each consuming repository. The team previously experienced two production incidents caused by schema-version drift. Submodules would represent that synchronization problem rather than remove it. They would also add detached checkouts and recursive clone/update behavior to routine contributor workflows.

### Meta-repository tool

A meta-repository tool could coordinate commands and revisions across otherwise separate repositories.

This was rejected because it would introduce a new tool, configuration model, and debugging workflow for a six-developer team. The expected learning and maintenance cost is not justified when a standard monorepo directly provides atomic source changes and a single checkout.

### Publish schemas as versioned packages

The schemas or generated bindings could be published and consumed as independently versioned artifacts.

This remains useful at external boundaries, but it was rejected as the primary internal coordination mechanism. Consumers would still need separate dependency updates, allowing versions to drift. Publication also adds release and artifact-management steps to every schema change.

## Consequences

### Positive

- Shared protobuf schemas have one source of truth.
- Schema and consumer updates can be reviewed and merged together.
- A contributor needs one checkout and one pull-request workflow.
- Cross-service refactoring becomes easier to inspect and validate.
- Repository-wide ownership and compatibility rules are visible in one place.
- Duplicate CI and development configuration can be consolidated where appropriate.

### Negative

- The repository and its history will be larger.
- CI path selection becomes critical infrastructure.
- A mistake in shared build or CI configuration can affect all services.
- Access control is primarily repository-wide; directory ownership guides review but is not equivalent to separate repository permissions.
- Repository-wide searches and tooling may require explicit service boundaries.
- Unrelated teams or services may encounter merge activity in the same main branch.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Every pull request builds every service and exceeds the CI cap | Use affected-path CI selection, caching, and cancellation of superseded runs. |
| Path selection skips a required test | Treat schema, CI, and shared-tooling changes conservatively; provide explicit full validation. |
| A schema change breaks a deployed consumer | Run compatibility checks and test all three consumers; use additive rollout sequences. |
| Service boundaries erode | Keep independent build, dependency, ownership, and deployment definitions. |
| A shared configuration change blocks all development | Require owner review and validate shared infrastructure against all services. |
| Old repositories continue to receive changes | Freeze and archive them, with clear links to the monorepo. |

## Success criteria

The decision is successful when:

- All four services build and deploy from the monorepo.
- The three protobuf consumers use only the schemas under `schemas/protobuf/`.
- A schema pull request validates all three consumers.
- No production deployment uses an untracked or independently copied schema revision.
- Unaffected service builds are normally skipped.
- CI consumption remains below 2,000 minutes per month.
- Contributors can build and test any service from a fresh checkout using documented commands.

## Reconsideration triggers

Revisit this decision if:

- CI cannot remain below the monthly cap without skipping required validation.
- Repository size or tooling performance materially impairs normal development.
- Service access controls require isolation that directory ownership cannot provide.
- The services move to separate organizations with independent governance.
- Shared schemas become a public product requiring an independent release and compatibility lifecycle.
