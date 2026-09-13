# ADR 0014: Consolidate four service repositories into one monorepo

Status: Accepted
Date: 2026-09-13
Deciders: platform team (6 developers)

## Context

Four repositories hold the system: `gateway`, `billing`, `ledger`, and `notifier`. Three of them (`gateway`, `billing`, `ledger`) compile the same protobuf schemas into generated clients and servers.

The schemas lived in a fifth repository, `contracts`, consumed through a Git submodule pin in each of the three services. That arrangement failed twice in production:

- 2026-02-11: `billing` served a `ChargeRequest` with a field number that `ledger` had already renumbered. The submodule pin in `ledger` was 23 commits behind. Reconciliation ran on stale amounts for 4 hours.
- 2026-05-03: `gateway` deployed against a `contracts` commit that removed a required field. The submodule pin in `gateway` had been advanced by a merge that touched no other file, so no reviewer read the schema diff.

Both incidents share one cause: a submodule pin is a commit hash in a parent tree, and a hash does not fail a build when it is old. Nothing in CI compared the three pins to each other.

CI spend is capped at 2,000 minutes per month across the GitHub Actions org account. Measured over 2026-06-01 to 2026-08-31, the four repositories consumed 1,730 minutes per month on average. Of that, 410 minutes went to duplicated protobuf generation and lint jobs that ran once per repository on identical inputs.

Six developers work across all four services. Every developer has commit access to every repository.

## Decision

Move the four service repositories and `contracts` into a single repository, `platform`, with this layout:

```
platform/
  proto/            # former contracts repo, single source of schemas
  services/gateway/
  services/billing/
  services/ledger/
  services/notifier/
```

Rules that follow from the decision:

- `proto/` holds exactly one version of each schema. No service vendors a copy.
- CI generates protobuf code once per commit into a shared artifact. The four service jobs consume that artifact.
- Each service job runs only when the commit touches `services/<name>/`, `proto/`, or the root build files. Path filters live in `.github/workflows/service.yml`.
- History from all five repositories is preserved with `git subtree add`, one subtree per source repository.
- The five source repositories are archived read-only on the cutover date, not deleted.

## Consequences

**A schema change breaks the build of every consumer in the same commit.** A field renumbering in `proto/` compiles `gateway`, `billing`, and `ledger` against the new definition before merge. The failure mode behind the 2026-02-11 and 2026-05-03 incidents cannot occur, because there is no per-service pin to be stale.

**CI minutes drop by the 410 minutes per month spent on duplicated generation and lint.** Path filtering keeps single-service changes at roughly one service job. A commit touching `proto/` runs all four service jobs, which measures 38 minutes. Budget headroom against the 2,000-minute cap therefore depends on schema-change frequency: at the 2026 rate of 9 `proto/` commits per month, projected spend is 1,320 minutes per month.

**A broken path filter silently skips tests.** The filter is the only thing standing between a service change and its test suite. `.github/workflows/service.yml` carries a job that runs the full four-service matrix on `main` after merge, so a skipped test surfaces within one commit rather than at release.

**Clones grow.** The combined repository is 890 MB with full history against 210 MB for the largest single source repository. Contributors on metered connections use `git clone --filter=blob:none`.

**Per-service access control is gone.** Every one of the 6 developers can now merge to any service path. `CODEOWNERS` assigns review per directory; it does not restrict merge.

**Release tags need a prefix.** Tags take the form `gateway/v2.4.0`. A bare `v2.4.0` is ambiguous across four services and is rejected by the tag-protection rule.

## Alternatives rejected

- **Keep Git submodules, add a CI check comparing pins.** The check compares hashes across four repositories that cannot be updated atomically; a passing check on each repository still permits a window where the three pins disagree.
- **Meta-repo tool (`meta`, `gita`, or Google `repo`).** Each of the 6 developers would learn a second command vocabulary layered over `git`, and the tool state lives outside Git, so `git bisect` no longer crosses a schema change.
- **Publish schemas as a versioned package to an internal registry.** Version skew becomes a semver range in four manifests, which reproduces the drift the incidents demonstrated, one indirection further from the diff.
- **Merge only the three protobuf consumers, leave `notifier` separate.** Keeps two CI configurations and two release processes for 6 developers, and `notifier` already imports the `ledger` client.

## References

- Incident report 2026-02-11: `docs/incidents/2026-02-11-ledger-amounts.md`
- Incident report 2026-05-03: `docs/incidents/2026-05-03-gateway-required-field.md`
- CI minute measurement: issue `plat-118`
- Migration runbook: `docs/runbooks/monorepo-cutover.md`
