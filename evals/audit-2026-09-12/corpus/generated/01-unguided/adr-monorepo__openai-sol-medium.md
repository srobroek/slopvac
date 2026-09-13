# ADR: Consolidate Four Service Repositories into a Monorepo

- **Status:** Accepted
- **Date:** 2026-09-12
- **Decision owners:** Engineering team
- **Scope:** Four service repositories and their shared Protocol Buffer schemas

## Context

The system is maintained by six developers across four repositories. Three of the four services consume shared Protocol Buffer schemas.

Keeping the services and schemas in separate repositories has made coordinated changes difficult. In particular, schema versions drifted between repositories and caused two production incidents. Changes that should have been reviewed and tested together instead moved through independent versioning, release, and deployment workflows.

The build and test strategy must also remain within a CI budget of **2,000 minutes per month**. A monorepo that runs every service's complete pipeline for every change would risk exceeding this limit.

This decision is intended to remain understandable to future contributors. It therefore favors standard repository and build-tool behavior over a specialized coordination layer.

## Decision drivers

- Prevent incompatible protobuf schema and consumer changes from drifting apart.
- Allow schema changes and corresponding service updates in one atomic commit.
- Make cross-service changes easier to review, test, and revert.
- Keep monthly CI use below 2,000 minutes.
- Minimize tooling and operational overhead for a six-person team.
- Preserve clear service ownership and independent deployment where appropriate.
- Make local development and CI behavior understandable without specialized meta-repository knowledge.

## Decision

We will move all four repositories into a single monorepo.

The monorepo will contain each service in a separate top-level directory and will maintain the protobuf schemas in a dedicated shared directory. A representative layout is:

```text
/
├── services/
│   ├── service-a/
│   ├── service-b/
│   ├── service-c/
│   └── service-d/
├── schemas/
│   └── protobuf/
├── tooling/
└── docs/
```

Exact names may differ, but the following boundaries are required:

1. Each service retains its own build, test, packaging, and deployment definition.
2. Shared protobuf source files have one canonical location.
3. Generated protobuf code is produced from that canonical source through repository-provided commands.
4. Schema changes and required consumer updates can be committed and reviewed together.
5. A change to one service does not automatically release or deploy the other services.
6. CI selects work according to the files and dependencies affected by a change.

The monorepo is a source-control and coordination boundary. It is not a requirement to combine services into one application, one artifact, or one deployment unit.

## Repository history

Existing repository history should be retained during migration where practical. Each repository will be imported into its destination directory using a history-preserving Git migration method.

After migration:

- the original repositories will become read-only;
- their default documentation will point contributors to the monorepo;
- new changes will be accepted only in the monorepo; and
- tags or migration notes will identify the final standalone revision and its corresponding monorepo revision.

We accept that some historical commands, paths, and commit references will continue to reflect the former repository layouts.

## Protobuf ownership and compatibility

The files under `schemas/protobuf/` are the authoritative schema definitions for the three consuming services.

CI must apply the following rules:

- A protobuf change triggers schema validation and compatibility checks.
- A protobuf change triggers tests for all affected consumers.
- Generated code must be reproducible from the checked-in schema source.
- CI must detect stale generated output if generated code is committed.
- Reviews of schema changes must include owners or maintainers of affected consumers.

Backward-compatible schema changes may be deployed incrementally. Breaking changes require an explicit migration sequence, such as introducing new fields or messages before removing old ones. A monorepo makes coordinated source changes possible, but it does not make simultaneous production deployment safe or guaranteed.

## CI strategy

CI will use path and dependency awareness rather than running every job for every commit.

### Change selection

At minimum, CI will apply these rules:

| Changed area | Required CI work |
|---|---|
| One service only | Build and test that service |
| Shared protobuf schemas | Validate schemas and build and test all affected consumers |
| Shared tooling or root build configuration | Run jobs for every affected service; run the full suite when impact cannot be determined safely |
| Documentation only | Run documentation checks without service builds, unless the changed files affect executable examples |
| Multiple services | Build and test each changed or transitively affected service |

A scheduled full build and test will catch errors in dependency selection. The schedule may be reduced if it threatens the monthly cap, but pull-request checks for directly affected components remain mandatory.

### CI budget controls

The team will monitor CI consumption against the 2,000-minute monthly cap. The initial operating target is no more than **1,600 minutes per month**, leaving 20% for retries, incident response, release work, and temporary increases.

CI configuration should favor:

- canceling superseded runs on the same branch;
- caching dependencies and generated artifacts;
- avoiding duplicate work between pull-request and branch pipelines;
- running independent jobs in parallel only when parallelism does not increase billed minutes unacceptably;
- using change detection to skip unaffected services;
- reserving full-repository runs for scheduled validation, shared infrastructure changes, and explicit requests; and
- recording job duration and monthly usage so regressions are visible.

If projected usage exceeds the operating target, the team will first remove redundant jobs and improve caching or change selection. Required correctness checks must not be silently disabled solely to meet the cap.

## Local development

Repository commands will provide a consistent way to:

- build or test one service;
- build or test all affected components;
- regenerate protobuf outputs;
- validate protobuf compatibility; and
- run the checks that CI applies to a change.

Contributors should not need to install or understand a separate meta-repository orchestration product to perform routine work.

Service-specific tools may remain within each service directory. The monorepo does not require immediate standardization of programming languages, frameworks, or build systems.

## Access and ownership

The repository will use path-based ownership rules for service and schema directories. These rules guide review but do not create strong confidentiality boundaries.

If a service later requires materially different source-access restrictions, the team must revisit this decision. A Git monorepo is not suitable for enforcing independent read access to individual directories.

## Deployment and releases

Services remain independently versioned and deployable unless a later decision changes that model.

A merge to the monorepo does not imply that all four services share:

- a release version;
- a release schedule;
- a deployment pipeline; or
- a rollback unit.

Deployment pipelines should use service paths and dependency information to determine which artifacts need to be built or released. Schema migrations must continue to account for services running different production versions during rollout.

## Alternatives considered

### Keep separate repositories

This would preserve current boundaries and minimize migration work. It was rejected because coordinated schema and consumer changes would still depend on cross-repository versioning and release discipline. That approach has already allowed schema versions to drift twice in production.

Separate repositories could be made safer with stronger automation, but that would recreate much of the coordination machinery the monorepo provides while retaining non-atomic changes.

### Git submodules

A parent repository could pin each service and the schema repository to specific commits.

This was rejected because pinned references still require contributors and automation to update multiple repositories correctly. The team has already experienced two production incidents caused by schema-version drift. Submodules expose rather than remove that coordination problem, and their detached working states and multi-step update workflow increase the chance of stale references.

### Meta-repository orchestration tool

A meta-repository tool could coordinate commands and revisions across the existing repositories.

This was rejected because its learning and maintenance cost is disproportionate for a six-developer team. Contributors would need to understand both Git repositories and an additional orchestration model. It would also leave atomic cross-repository commits and reviews unresolved or tool-dependent.

### Publish protobuf schemas as a versioned package

Publishing generated clients or schemas could formalize dependency versions while retaining separate repositories.

This remains useful for external consumers, but it was rejected as the primary internal coordination model. Package publication alone does not prevent one service from remaining on an incompatible or stale version. It also requires multi-step publication and upgrade workflows for changes spanning schemas and consumers.

## Consequences

### Positive

- Schema definitions and their consumers can change in one commit and one review.
- CI can validate all known consumers whenever a shared schema changes.
- Contributors have one repository to clone, search, and navigate.
- Cross-service refactoring and rollback become easier to coordinate.
- Shared tooling and standards can be introduced without duplicating changes across repositories.
- The team avoids the operational and learning costs of submodules or a meta-repository layer.

### Negative

- The repository and its history will be larger.
- CI change detection and dependency mapping become critical infrastructure.
- Incorrect dependency rules could skip necessary tests.
- Broad root-level changes may trigger expensive full-repository pipelines.
- Repository-wide permissions provide less isolation than separate repositories.
- Teams must avoid accidental coupling merely because all source code is colocated.
- History around renamed and imported files may be less convenient to inspect.

### Neutral or unchanged

- Services remain separate runtime and deployment units.
- Protobuf compatibility across staggered deployments is still required.
- A single repository does not guarantee a single release or synchronized deployment.
- Service-specific technologies may remain different.

## Migration plan

1. Define the target directory structure and path ownership rules.
2. Record the final standalone revision of each repository.
3. Import each repository with history into its target directory.
4. Move protobuf schemas to their canonical shared location.
5. Update consumers to generate or consume code from the canonical schemas.
6. Add schema validation and compatibility checks.
7. Add path- and dependency-aware CI rules.
8. Verify representative CI scenarios:
   - a change isolated to each service;
   - a schema-only change;
   - a schema change with consumer updates;
   - a shared-tooling change;
   - a documentation-only change; and
   - a full-repository validation.
9. Measure projected CI use and adjust caching, cancellation, and scheduling to remain within the operating target.
10. Update development, release, ownership, and incident-response documentation.
11. Freeze the original repositories and direct contributors to the monorepo.
12. Monitor build duration, CI usage, missed dependency edges, and contributor friction after migration.

## Validation and review

For the first three months after migration, the team will review:

- monthly CI minutes, including canceled and retried runs;
- changes in median pull-request feedback time;
- failures found by scheduled full builds but missed by selective CI;
- protobuf compatibility failures;
- deployment incidents related to schema or generated-code drift; and
- maintenance time spent on monorepo tooling.

This decision should be reconsidered if:

- CI cannot remain below 2,000 minutes per month without removing required checks;
- selective CI repeatedly misses affected services;
- repository access requirements demand service-level confidentiality;
- repository size materially degrades normal development; or
- independent teams and release processes grow enough that the coordination benefits no longer outweigh repository-wide costs.

## Operational invariant

A shared protobuf schema change is not complete unless the repository can validate it against every affected in-repository consumer. Any CI or repository change that weakens this invariant requires a new architecture decision.
