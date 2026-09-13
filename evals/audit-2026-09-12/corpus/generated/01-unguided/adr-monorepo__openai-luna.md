# ADR: Consolidate Four Repositories into a Single Monorepo

- **Status:** Accepted
- **Date:** 2026-09-12
- **Decision owners:** Engineering team
- **Scope:** Four service repositories and the shared protobuf schemas

## Context

We currently maintain four repositories, one for each service. Three of the services share protobuf schemas. The fourth service does not currently consume those schemas, but it is part of the same product and is affected by cross-service changes.

The current repository boundaries create several problems:

- Shared protobuf changes must be coordinated across multiple repositories.
- Services can consume different schema revisions.
- Version drift has already caused two production incidents.
- Cross-service changes require multiple pull requests and coordinated releases.
- It is difficult to determine which services need to be tested when a shared schema changes.
- Contributors must understand repository-specific setup and synchronization procedures.

The team consists of six developers. The repository structure must remain understandable and maintainable without requiring a dedicated build-infrastructure team.

CI usage is capped at **2,000 minutes per month**. A monorepo must therefore avoid running the complete test suite for every change while still providing reliable validation for shared schemas and affected services.

## Decision

Move all four service repositories and the shared protobuf schemas into a single monorepo.

The monorepo will use the following high-level structure:

```text
/
├── services/
│   ├── service-a/
│   ├── service-b/
│   ├── service-c/
│   └── service-d/
├── proto/
│   ├── common/
│   └── ...
├── tools/
├── ci/
├── docs/
└── README.md
```

The exact build system and language-specific tooling may be selected during implementation, but the repository must provide:

1. **One checkout** for all services and schemas.
2. **One canonical copy** of each shared protobuf schema.
3. **Reproducible protobuf code generation** from the checked-in schemas.
4. **Dependency-aware CI** that tests only affected services for ordinary changes.
5. **A full-repository validation path** for releases, changes to shared schemas, and scheduled verification.
6. **Clear ownership and contribution documentation** suitable for future contributors.

The shared protobuf schemas will be treated as source files owned by the monorepo, not as independently versioned packages consumed through repository references.

## Rationale

A monorepo directly addresses the failure mode that matters most: schema version drift.

Because the three consumers use the same schema files from the same revision, a change cannot silently update one service while leaving another service on an incompatible revision. Schema changes and their affected consumers can be reviewed and tested together.

The monorepo also reduces coordination overhead for a six-person team:

- One pull request can contain a schema change, generated code, service updates, and tests.
- Contributors do not need to synchronize branches across four repositories.
- Repository-wide conventions can be documented and enforced in one place.
- Cross-service changes have a single review and merge point.

This approach is intentionally simpler than introducing a meta-repository tool. It centralizes source control without adding another orchestration layer that the team would need to learn and maintain.

## Alternatives Considered

### Keep the four repositories and improve coordination

**Rejected.**

This would preserve the existing version-drift risk. Additional process or release checklists could reduce the probability of mistakes but would not make the shared schema atomic with its consumers.

### Git submodules

**Rejected.**

Git submodules were specifically rejected because schema versions drifted twice in production. Submodules preserve independent repository histories and allow a consumer to remain pinned to an outdated schema unless every update is deliberately coordinated.

They also add operational complexity:

- Contributors must initialize and update nested repositories.
- Pull requests span repository boundaries.
- The parent repository can reference a schema revision that is not compatible with all services.
- CI and local development require additional submodule handling.

The observed production incidents demonstrate that this is not merely a theoretical risk.

### Meta-repository tool

**Rejected.**

A meta-repository tool could coordinate multiple repositories, but its learning and maintenance cost is not justified for a six-developer team. It would retain the underlying cross-repository coordination problem while adding another abstraction and failure mode.

### Publish protobuf schemas as a separately versioned package

**Rejected for now.**

A versioned schema package could work if the team needed independent release lifecycles or external consumers. It would not, by itself, prevent consumers from intentionally or accidentally using different versions. The current requirement is atomic coordination across the three internal consumers, which is better served by colocating schemas and consumers.

This option may be reconsidered if schemas become a public API or are consumed by independently operated systems.

## Repository and Dependency Rules

### Protobuf source of truth

- Protobuf files under `proto/` are the canonical schema definitions.
- Generated source code is produced from those files by a reproducible command.
- Generated artifacts must not be edited manually.
- The repository must document whether generated code is committed or generated during builds. The chosen policy must be consistent for all services.
- CI must fail if generated output is stale or differs from the output produced by the pinned toolchain.

### Schema changes

A pull request changing a shared schema must include, as applicable:

- Regenerated client or server code.
- Updates to all affected services.
- Compatibility tests.
- Migration notes for wire-compatible but behaviorally significant changes.
- An explicit list of services that were tested.

Protobuf compatibility rules must be documented and enforced. In particular:

- Existing field numbers must not be reused.
- Removed fields must remain reserved.
- Breaking changes require an explicit migration plan.
- Additive changes must be tested against the relevant older and newer message forms where compatibility is required.

### Service boundaries

Each service remains independently deployable. Moving into one repository does not imply combining service runtimes, databases, deployment units, or ownership.

A contributor should be able to:

- Build and test one service without understanding every other service.
- Identify the service's owners and entry points.
- Run the service's focused checks locally.
- See which shared dependencies affect the service.

## CI Strategy and Cost Control

The 2,000-minute monthly CI cap is a design constraint, not a target to consume.

CI will use change detection and dependency metadata to select checks.

### Pull requests

For an ordinary pull request:

1. Validate formatting, configuration, and repository structure.
2. Determine the changed files.
3. Map changed files to affected services.
4. Run focused tests and builds for affected services.
5. Run protobuf compatibility and generation checks when `proto/` changes.
6. Run integration tests only for services or interfaces affected by the change.
7. Run a lightweight cross-service validation when dependency analysis indicates an interface change.

Changes to shared protobuf schemas are treated as affecting all three schema consumers, even when the change appears narrowly scoped.

Changes to repository-wide tooling, dependency lockfiles, CI configuration, or shared build configuration are treated as affecting all four services unless the dependency metadata proves otherwise.

### Main branch and scheduled validation

The main branch will run:

- The same affected-service checks used for pull requests.
- A complete test suite on a scheduled basis.
- A complete test suite before production releases.
- Periodic verification of dependency metadata and generated code.

Scheduled and release validation must be budgeted separately from ordinary pull-request validation.

### Budget model

The team must track CI minutes monthly using the following categories:

| Category | Purpose |
|---|---|
| Pull-request checks | Fast feedback for changed services |
| Main-branch checks | Protection against merged regressions |
| Scheduled full checks | Detect dependency-analysis gaps |
| Release checks | Required production confidence |
| Retry and diagnostic allowance | Capacity for failed or repeated jobs |

The initial operating budget should reserve no more than approximately:

- **1,200 minutes/month** for pull-request and main-branch checks.
- **500 minutes/month** for scheduled full validation.
- **300 minutes/month** for releases, retries, and diagnostics.

These are planning limits, not guarantees. CI usage must be reviewed monthly. If usage approaches 2,000 minutes, reduce redundant jobs, improve caching, or narrow test selection before adding more parallel work.

The repository should prefer:

- Dependency-aware test selection.
- Build and dependency caching.
- Reusing generated artifacts within a workflow.
- Failing fast on formatting, schema, and configuration errors.
- Avoiding duplicate full-suite jobs across pull requests and main branch.
- A scheduled full suite rather than a full suite on every pull request.

## Migration Plan

Migration will be performed in stages so that the existing repositories remain usable until the monorepo is validated.

### 1. Prepare the destination repository

Create the monorepo with:

- The target directory layout.
- Contribution and development documentation.
- Ownership metadata.
- Build and test entry points.
- Protobuf generation and compatibility checks.
- Initial CI workflows.
- Dependency metadata describing which services consume which schemas.

### 2. Import repository history

Import the histories of all four repositories into their corresponding service directories. Preserve commit history where practical, but do not allow historical layout concerns to dictate the new structure.

Place the shared protobuf repository or schema files under `proto/` and establish one canonical copy. Resolve duplicate files explicitly rather than retaining parallel copies.

### 3. Normalize tooling

Make local commands consistent. At minimum, document commands for:

```text
build one service
test one service
test all affected services
generate protobuf code
check protobuf compatibility
run the complete validation suite
```

Pin the protobuf compiler, plugins, and other code-generation dependencies so that local and CI output is reproducible.

### 4. Establish compatibility validation

Before switching development to the monorepo:

- Generate code for all three protobuf consumers.
- Build all four services.
- Run the existing service tests.
- Run cross-service compatibility tests.
- Confirm that generated output is deterministic.
- Confirm that a schema change causes all three consumers to be selected by CI.

### 5. Cut over development

After the monorepo passes validation:

- Make the monorepo the canonical source for active development.
- Freeze changes to the old repositories except for urgent maintenance.
- Update deployment and release automation to use monorepo paths.
- Archive the old repositories after the agreed retention period.
- Record the migration commit or release point for operational traceability.

## Consequences

### Benefits

- Shared schemas and their consumers are reviewed and tested atomically.
- The specific production failure mode of schema version drift is removed.
- Cross-service changes require less coordination.
- Contributors use one checkout and one set of repository conventions.
- CI can select affected services from explicit dependency relationships.
- Service deployment boundaries remain independent.

### Costs and risks

- The repository becomes larger and requires disciplined ownership.
- Incorrect change-detection rules could skip required tests.
- CI configuration becomes a critical part of repository correctness.
- Developers may accidentally couple unrelated service changes if boundaries are not documented.
- Importing history and normalizing tooling require one-time migration effort.
- A monorepo does not automatically guarantee schema compatibility; incompatible schema changes still require review and migration planning.

### Mitigations

- Maintain explicit dependency metadata.
- Treat shared schema and repository-wide changes conservatively.
- Run scheduled full-repository validation.
- Require generated-code and compatibility checks for schema changes.
- Document independent service build and deployment boundaries.
- Review CI minutes and false-negative test-selection incidents monthly.
- Keep the complete validation suite available for releases and emergency diagnosis.

## Operational Guidelines for Future Contributors

When changing a service, start with that service's focused build and test commands.

When changing anything under `proto/`, assume that all three schema-consuming services are affected. Do not update only the service that motivated the change unless the dependency documentation proves that another consumer is unaffected.

When changing shared build configuration, dependency lockfiles, CI configuration, or repository tooling, assume that all four services are affected.

Do not recreate separate copies of shared protobuf files inside service directories. If a service needs a schema change, modify the canonical file under `proto/` and update the affected consumers in the same change.

Do not introduce submodules or a meta-repository workflow to restore the old repository boundaries. If the monorepo becomes difficult to operate, address the specific build, ownership, or CI problem first and bring a new repository strategy back as a separate architecture decision.

## Success Criteria

The migration is complete when:

- All four services build from the monorepo.
- The three protobuf consumers use the canonical schemas under `proto/`.
- Generated code is reproducible and checked by CI.
- A schema change automatically selects all three consumers for validation.
- A contributor can build and test one service without building unrelated services.
- Full validation runs for releases and on a scheduled basis.
- Monthly CI usage remains below 2,000 minutes.
- No service depends on a separately pinned copy of the shared schemas.
- The old repositories are no longer used as active sources of truth.
