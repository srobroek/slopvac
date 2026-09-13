# ADR: Consolidate Four Repositories into a Single Monorepo

**Status:** Accepted

**Date:** 2026-09-12

**Deciders:** Platform team, engineering leadership

**Drivers:** Shared protobuf schema management, CI cost optimization, team scaling

---

## Context

The organization operates four closely-coupled services with the following characteristics:

- **Team size:** Six developers across all services
- **Shared contract:** Three of four services consume a common protobuf schema
- **Operational pain point:** Schema version mismatches have caused two production incidents when branches diverged during development
- **Cost constraint:** CI infrastructure budget capped at 2,000 minutes per month
- **Deployment cadence:** Services deploy independently but coordinate on schema changes; schema releases currently require manual coordination across three repositories

### Problem Statement

The current multi-repository setup creates a split-brain problem for protobuf schema governance. Schema ownership is ambiguous, versioning across repositories drifts, and developers must manually synchronize schema changes before merging. This workflow has failed twice when a developer updated a schema in one repository without propagating the change to consuming services—both incidents went undetected until reaching production.

Tight coupling around shared schemas, combined with a small team size, makes the separation of repositories costly rather than beneficial. Each repository maintains its own CI pipeline, duplicating build logic and consuming budget inefficiently (three separate lint, test, and build jobs for the shared schema alone).

---

## Decision

We will consolidate the four services into a single monorepo with the following structure:

```
/
├── proto/
│   ├── schema.proto
│   ├── build/
│   └── version.txt
├── services/
│   ├── api-service/
│   ├── worker-service/
│   ├── auth-service/
│   └── legacy-batch-service/
├── shared/
│   ├── go-protos/  (generated, committed)
│   ├── node-protos/  (generated, committed)
│   └── python-protos/  (generated, committed)
├── build/
│   ├── Makefile
│   └── ci/
├── .github/workflows/
│   ├── lint.yml
│   ├── test.yml
│   ├── build.yml
│   └── deploy.yml
└── docs/
    └── DEVELOPMENT.md
```

**Monorepo mechanics:**

- Single CI pipeline executes all jobs in parallel; expensive tests run only on affected services using path filters
- Protobuf schema lives in `proto/` with a single source of truth; schema changes are reviewed in the same PR as consuming code
- Generated protobuf bindings are committed to `shared/` to ensure reproducibility and reduce CI complexity (avoid generator version drift)
- Each service directory is independently deployable; deployment CI detects which services changed and deploys only those
- Shared packages (non-proto) live in `shared/`; cross-service dependencies use workspace tooling (Go modules, npm workspaces, or Python path management)

---

## Consequences

### Positive

1. **Schema safety:** Protobuf schema changes and their consumers are verified in the same CI run. Breaking changes are caught before merge; no schema version mismatch can reach production.

2. **Atomicity:** A developer can update a schema and all three consuming services in a single PR with unified review and testing. The schema version increments deterministically.

3. **CI cost reduction:** Consolidated pipelines eliminate duplicate jobs. Path-based filtering ensures only affected services run tests. Estimated monthly CI cost: ~1,200 minutes (40% reduction from current ~2,000 across four separate pipelines).

4. **Onboarding clarity:** New contributors encounter a single repository with unified build and deployment instructions. Schema ownership is implicit (lives in `proto/`); no need to explain coordination across three repositories.

5. **Dependency management:** Cross-service dependencies are explicit and managed by the monorepo tooling; no hidden drift between pinned versions across independent repositories.

### Negative

1. **Repository size:** The combined repository is larger (~2.5x) than any individual service repository. Clones and shallow operations are slower for developers working on only one service. Mitigation: provide shallow clone instructions in `DEVELOPMENT.md`; Git filtering and worktrees reduce friction for service-specific work.

2. **Deployment coupling risk:** A mistake in the build pipeline can block all deployments. Mitigation: maintain separate deploy jobs per service; deploy failures in one service do not trigger rollback of others unless explicitly orchestrated.

3. **Tooling complexity:** Developers must understand multiple build systems (Go, Node.js, Python, Protocol Buffers). Mitigation: centralized `Makefile` and `build/ci` scripts abstract complexity; scripts are the contract, not individual tools.

4. **Git history:** All four repositories are squashed into one history. Blame and bisect become slower. Mitigation: git-subtree or manual history reconstruction is not required; accept history consolidation as a one-time cost.

---

## Alternatives Considered

### Git Submodules (Rejected)

Submodules were proposed to separate services while linking the schema repository. **Rejected** because:

- Historical incidents: Submodule versions drifted twice in production when developers committed schema updates in the parent repo without updating submodule pins
- Cognitive overhead: Six developers on a small team cannot reliably coordinate submodule update ceremonies
- CI complexity: Submodule CI workflows are fragile; version mismatch failures are often discovered during deployment, not CI
- No performance benefit for a 2.5x repository size increase

### Meta-Repo Tool (Rejected)

Tools like Bazel, Pants, or Lerna were evaluated to manage four repositories as a logical unit. **Rejected** because:

- Learning curve: No team member has prior experience; estimated 3–4 weeks per developer to reach productivity
- Maintenance burden: Tooling complexity inverts the cost-benefit for a six-person team
- Worse failure modes: Submodule misalignment is debuggable; meta-repo cache and build-graph corruption is not
- For the scale of this team and service count, a monorepo is simpler

---

## Implementation

### Migration Steps

1. **Preparation:** Audit both the schema and consuming services for breaking changes; resolve any pre-existing version conflicts
2. **Repository merge:** Use `git subtree` or manual merge to combine four repositories into a single root, preserving history under service directories
3. **Build system migration:** Update CI to run the unified pipeline; implement path-based filtering for test and deploy jobs
4. **Proto generation:** Generate bindings for all target languages into `shared/`; commit bindings to the repository
5. **Dependency updates:** Update service code to import from `shared/` and use local workspace dependencies
6. **Gradual testing:** Run new pipeline in parallel with old pipelines for one sprint; verify no behavioral changes
7. **Cutover:** Merge to main; retire old repositories (archive on GitHub, do not delete)

### Maintenance

- **Schema changes:** Update `proto/schema.proto`, regenerate bindings, update consuming services, and merge in one PR
- **Service-specific changes:** Change only the service directory; CI runs tests only for that service
- **Cross-service refactoring:** Requires careful test coverage; use CI to catch coupling issues
- **New services:** Copy a service template from `services/api-service/`; update `build/ci/` path filters

---

## Decision Authority

This ADR is binding for the platform team and infrastructure. Service teams maintain autonomy over internal service architecture and must comply with the monorepo build and deployment contract defined in `build/ci/`.

---

## Appendix: Rationale for Committing Generated Bindings

Generated protobuf bindings are committed to `shared/` (not gitignored) to:

- **Eliminate generator version drift:** Protobuf compiler versions differ between local developer machines and CI; committing bindings ensures all builds use identical outputs
- **Reduce CI complexity:** Binding generation does not require downloading and configuring multiple language-specific protobuf toolchains in CI
- **Enable offline builds:** Developers can build services locally without regenerating bindings if proto schema is unchanged
- **Simplify review:** Proto schema changes and generated output are reviewed together, making intent and impact explicit

Trade-off: Repository size increases by ~15 MB. Mitigation: `git sparse-checkout` allows developers to skip downloading bindings for unused languages.
