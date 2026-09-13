# ADR 0014: Merge four service repositories into the `platform` monorepo

Status: Accepted
Date: 2026-09-13
Deciders: platform team (6 developers)
Supersedes: ADR 0009 (submodule-based schema sharing)

## Context

Four repositories hold the production system: `api-gateway`, `billing`, `notifier`, and `web-console`. Three of them (`api-gateway`, `billing`, `notifier`) compile the same protobuf definitions. `web-console` consumes the generated TypeScript client.

The protobuf definitions lived in a fifth repository, `contracts`, wired into the three services as a git submodule. Submodule pointers drifted from `contracts@main` twice, and both drifts reached production: INC-412 (2025-11-04, `billing` rejected a field `api-gateway` had started sending) and INC-587 (2026-03-19, `notifier` deserialized a renamed enum as its zero value).

A single schema change required four pull requests: one to `contracts`, then one per consuming service. Each of the four repositories ran a full pipeline on every push, with no cross-repository path filtering. In August 2026 the four repositories plus `contracts` consumed 2,340 CI minutes against a cap of 2,000 minutes per month.

Six developers share all four codebases. No repository has a dedicated owner.

## Decision

The platform team merges all five repositories into one repository named `platform`, preserving history with `git subtree add` per source repository.

### Layout

| Path | Contents |
| --- | --- |
| `proto/` | Protobuf definitions, single source of truth |
| `gen/go/`, `gen/ts/` | Generated code, committed |
| `services/api-gateway/` | Go service |
| `services/billing/` | Go service |
| `services/notifier/` | Go service |
| `web/console/` | TypeScript application |
| `.github/workflows/` | All pipelines |

### Schema ownership

`proto/` is the only location for `.proto` files. A change to `proto/` and the changes to its three consumers land in one commit. `make gen` regenerates `gen/go/` and `gen/ts/` from `proto/`. CI fails the pull request when `make gen` produces a diff against the committed output.

`buf breaking --against '.git#branch=main,subdir=proto'` runs on every pull request that touches `proto/`. A breaking change fails the pipeline unless the pull request body contains the line `Breaking-Change-Approved: <issue-id>`.

### CI budget

Every job carries a `paths` filter rooted at its directory. Job durations below are the August 2026 medians from the source repositories.

| Trigger path | Jobs run | Minutes |
| --- | --- | --- |
| `services/api-gateway/**` | gateway test | 4 |
| `services/billing/**` | billing test | 5 |
| `services/notifier/**` | notifier test | 3 |
| `web/console/**` | console test and build | 6 |
| `proto/**` | codegen check, buf breaking, all three service tests | 14 |

The merge queue runs the full 18-minute pipeline once per merge, not once per push. The team reserves 300 minutes per month for nightly builds and release tagging.

At the August 2026 rate of 96 merged pull requests per month, this allocation projects to 1,480 minutes per month. That figure is a projection from measured job durations, not a measurement of the merged repository.

### Enforcement

`CODEOWNERS` assigns `proto/` to the whole team and requires two approvals. Every other path requires one approval.

## Rejected alternatives

- **Keep git submodules** — the pointer-versus-branch gap caused INC-412 and INC-587, and nothing in the submodule model prevents a third occurrence.
- **Meta-repo tool (`repo`, `meta`, or `gita`)** — six developers would each maintain a second version-control CLI on top of git, and the tool still leaves schema changes split across four pull requests.
- **Publish protobuf as versioned artifacts** — solves drift but adds a publish-and-bump round trip per schema change, and the CI cost of running four repository pipelines stays at 2,340 minutes per month.
- **Merge only the three Go services** — leaves `web/console` consuming `gen/ts/` across a repository boundary, so the drift class survives for the TypeScript client.

## Consequences

### Gained

- A schema change and its three consumer updates land atomically. Drift between `proto/` and a service becomes unrepresentable.
- Path filters cut CI minutes below the 2,000-minute cap without dropping any job.
- One `go.work` file and one `pnpm-workspace.yaml` replace five dependency manifests.
- `git log --follow` reaches pre-merge history through the subtree grafts.

### Lost

- A pull request touching `proto/` blocks on a 14-minute pipeline instead of a 2-minute one.
- A revert of a schema change reverts its three consumer updates in the same commit, with no way to keep one of them.
- Clone size grows to the sum of five histories. `git clone --filter=blob:none` is the documented default in `CONTRIBUTING.md`.
- Repository-level GitHub features (releases, issue labels, branch protection) no longer separate per service. Release tags carry a `service/` prefix.

### Obligations

- Every new job MUST declare a `paths` filter. A job without one runs on every pull request and consumes the budget.
- Whoever adds a fifth service adds its `paths` filter and records the measured job duration in the CI budget table above.
- If measured monthly CI minutes exceed 1,800, the team removes jobs from the pull-request pipeline and moves them to the nightly build.

## Acceptance criteria

- `git log --oneline services/billing/` returns commits authored before 2026-09-13.
- A pull request that edits `proto/` without running `make gen` fails on the codegen check.
- A pull request that renames a protobuf enum value fails `buf breaking` without a `Breaking-Change-Approved:` line.
- A pull request touching only `web/console/**` runs the console jobs and no Go jobs.
- The GitHub Actions billing page reports under 2,000 minutes for the first full calendar month after the merge.
