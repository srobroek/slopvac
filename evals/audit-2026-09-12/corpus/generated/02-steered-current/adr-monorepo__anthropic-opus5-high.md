# ADR-0014: Consolidate four service repositories into one monorepo

Status: Accepted
Date: 2026-09-12
Supersedes: ADR-0007 (shared schemas via git submodule)

## Context

Six developers maintain four repositories:

| Repository | Language | Consumes `payments.v1` protobuf |
| --- | --- | --- |
| `checkout-api` | Go 1.24 | yes |
| `pricing-svc` | Go 1.24 | yes |
| `ledger-svc` | Go 1.24 | yes |
| `web-console` | TypeScript 5.6 | no |

Three services share the `payments.v1` protobuf schemas. Under ADR-0007 each service pinned a submodule commit of `payments-proto`.

Two production incidents traced to divergent pins:

- INC-212 (2026-03-04): `ledger-svc` ran a pin 19 commits behind `checkout-api` and dropped the `settlement_id` field on 4,100 transfers.
- INC-247 (2026-06-18): `pricing-svc` read `discount_bps` as the removed `discount_pct`, producing a 100x price error on 3 tenants for 47 minutes.

Neither pin mismatch was detectable in a single repository's CI, because no repository built all three services against one schema revision.

The GitHub Actions budget caps billable time at 2,000 minutes per month. Metered usage from 2026-07-01 to 2026-07-31 was 2,480 minutes across the four repositories, for 118 pushes. Submodule-bump pull requests accounted for 390 of those minutes and changed no service code.

## Decision

Merge the four repositories into one repository, `platform`, with this layout:

```
proto/payments/v1/     # the only .proto location in the tree
services/checkout-api/
services/pricing-svc/
services/ledger-svc/
apps/web-console/
```

Histories move with `git subtree add`, preserving commits and authorship. Source repositories become archived and read-only on the merge date.

The following rules hold, each enforced by a named check in `.github/workflows/ci.yml`:

1. `proto-location`: fails when any `.proto` file exists outside `proto/`. This makes the single schema revision structural, not conventional.
2. `buf-breaking`: runs `buf breaking --against '.git#branch=main'`. A breaking field change fails the pull request that introduces it.
3. `proto-fanout`: a pull request touching `proto/` runs the test suites of `checkout-api`, `pricing-svc`, and `ledger-svc` in the same run.
4. `path-filter`: a pull request touching only one service directory runs only that service's suite.
5. `codegen`: generates Go and TypeScript stubs during the build. Generated stubs are not committed; `git status --porcelain` must be empty after `make generate`.
6. `budget`: a scheduled job reads the Actions billing API on the 1st, 11th, and 21st of each month, and opens an issue when projected month-end minutes exceed 1,800.

Ownership stays per directory in `CODEOWNERS`. Releases use tag prefixes, `checkout-api/v1.4.0` and `web-console/v3.2.0`, so one repository carries four independent version streams.

Replaying July's 118 pushes against the path-filtered pipeline on branch `spike/monorepo-ci` consumed 1,340 minutes, 54% of the 2,000-minute cap.

## Consequences

- A schema change and its three consumer updates land in one commit. The class of defect behind INC-212 and INC-247 cannot reach `main` while check 3 passes.
- A pull request touching `proto/` costs 16 minutes of CI, against 6 minutes for a single-service change. Schema churn is the dominant cost driver.
- Clone size rises from 340 MB across four repositories to 410 MB for `platform`, including four grafted histories. Shallow clones (`--depth 1`) are 90 MB.
- `git log` on a moved file needs `--follow` to cross the subtree merge commit, `a3f19c2`. `git blame` before that commit reports the original repository's authors.
- The merge queue serializes all four components. A red `main` blocks six developers rather than the one or two who own the failing service.
- `web-console` pays no schema cost and gains no schema benefit. It moves for one issue tracker, one CODEOWNERS file, and one billing account.

## Rejected alternatives

- Git submodules per ADR-0007: pins drifted and caused INC-212 and INC-247; no single CI run compiles all consumers against one revision.
- Meta-repo tool (`meta`, `gita`): every contributor learns a second clone-and-sync workflow on top of `git`, and pins still live in four places.
- Publish `payments-proto` as versioned language packages: replaces pin drift with dependency-range drift, and adds a publish step between a schema change and its consumers.
- Keep four repositories and raise the CI budget: the 2,000-minute cap is fixed for the fiscal year, and July usage already exceeded it by 480 minutes.
