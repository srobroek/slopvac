# ADR 0012: Consolidate the four service repositories into one monorepo

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Platform team (6 engineers), signed off by the engineering lead
- **Supersedes:** ADR 0004 (Share protobuf definitions via Git submodule)

## Context

We maintain four repositories:

| Repository | Language | Uses `proto/` |
|---|---|---|
| `api-gateway` | Go | yes |
| `billing-service` | Go | yes |
| `ledger-service` | Go | yes |
| `web-console` | TypeScript | no (consumes the gateway's generated OpenAPI file) |

Three of the four build directly from a shared set of `.proto` files. Until now those files lived in a fifth repository, `proto`, wired into each consumer as a Git submodule (ADR 0004).

### Why we are changing

**Two production incidents caused by submodule pointer drift.**

1. *2025-11-14.* `billing-service` had its submodule pinned three commits behind `proto@main`. Field 7 of `Invoice` had been changed from `int64 tax_cents` to a `Tax` message. The old binary decoded the new bytes as a varint and produced wrong totals for 41 minutes. 1,900 invoices were reissued.
2. *2026-04-02.* A merge into `ledger-service` resolved a submodule pointer conflict by taking the older side. The deployed binary did not know about `LedgerEntry.idempotency_key`, dropped it as an unknown field, and double-posted retried entries. Detection took roughly three hours; 12 duplicate entries were reversed by hand.

Both failures share a shape: a schema change was reviewed and merged in one repository, and a consumer kept compiling and passing its own tests against an older copy. Neither CI nor code review saw the mismatch, because no single diff contained both sides.

**CI spend is already over the cap.** The budget is 2,000 GitHub Actions minutes per month. Billed usage averaged 2,020 minutes over June to August 2026, split roughly 610 / 540 / 480 / 390 across the four repositories. About 210 of those minutes were the same protobuf codegen and lint steps run three times.

## Decision

Merge all four repositories, plus `proto`, into a single repository named `platform`, with per-path CI selection and four independent release pipelines.

### Layout

```
platform/
├── proto/acme/{gateway,billing,ledger}/v1/   # the only copy of the schemas
├── gen/{go,ts,openapi}/                      # generated code, committed
├── services/{api-gateway,billing,ledger}/    # Go
├── apps/web-console/                         # TypeScript
├── tools/ci/affected.sh
├── buf.yaml, buf.gen.yaml
└── go.work
```

### Rules that make the merge worth doing

- **A schema change and every consumer's adaptation land in the same pull request.** This is the whole point. `proto/` has a CODEOWNERS entry requiring two approvals.
- **`buf breaking --against '.git#branch=main'`** runs on every pull request that touches `proto/`. Wire-incompatible edits fail the build instead of reaching a deploy.
- **`gen/` is committed.** CI re-runs `buf generate` and fails if the working tree is dirty afterwards. Reviewers therefore see the wire-format consequence of a schema edit in the same diff, and a fresh clone builds without a codegen toolchain.
- **One repository does not mean one deployable.** Each service keeps its own pipeline and its own tags (`billing/v1.4.2`). Merging to `main` does not deploy anything.

### CI budget

`tools/ci/affected.sh` maps changed paths to build targets and skips the rest. Pull request runs also cancel superseded pushes via a `concurrency` group.

| Line item | Volume | Minutes each | Monthly |
|---|---|---|---|
| Pull request runs (affected subset) | ~125 | 7 | 875 |
| `main` builds after merge (full) | ~52 | 11 | 572 |
| **Total** | | | **~1,450** |

That leaves roughly 550 minutes of headroom against the cap, and removes the duplicated codegen. Full-repo builds run on `main` only, not on every push to a branch.

## Alternatives considered

**Keep Git submodules.** Rejected. The two incidents above are the argument. A submodule pointer records an intent that nothing verifies against the consumer's behaviour, and the failure mode is silent at compile time and expensive at runtime.

**A meta-repo tool (`git-repo`, `meta`, `mu-repo`).** Rejected on learning cost. Six engineers would each need to learn a second, non-standard set of commands layered over Git, and every new contributor would need the same. The tools synchronise checkouts; they do not make a schema change and its consumers reviewable as one diff, so the drift window stays open.

**Publish the schemas as a versioned package** (Buf Schema Registry, or a private Go module plus npm package). Rejected for now. It is a real improvement over submodules and it is the right answer if we ever split the repository again. It was rejected here because a consumer can still sit on an old version indefinitely, which is exactly incident 1, and because it adds a publish-and-bump cycle to every schema change for three consumers we control.

**Bazel or Nx for build graph selection.** Rejected on learning cost, same reasoning as the meta-repo tool. `affected.sh` is about 60 lines of `git diff --name-only` plus a path-to-target table. When that table stops being maintainable, revisit this.

## Consequences

**Good**

- Schema changes are atomic across producer and consumers. The class of incident described above cannot happen inside the repository.
- CI spend drops from over-cap to roughly 1,450 minutes, with the duplicated codegen gone.
- One dependency update, one lint config, one Go workspace, one release checklist to maintain instead of four.

**Bad**

- A broken `main` blocks all four services. Mitigated by scoping required status checks per path and keeping `main` builds under 11 minutes, but the coupling is real.
- Clone size grows to about 340 MB with full history. Contributors on slow links should use `git clone --filter=blob:none`.
- Per-repository access control is gone. Everyone with write access can touch every service.
- `git blame` crosses the migration commit. Use `--follow`, and note that `.git-blame-ignore-revs` lists the one repository-wide formatting commit.
- Third-party tools that assume the repository root is the project root (some IDE plugins, some scanners) need per-directory configuration.

**Neutral**

- History was moved with `git-filter-repo`, rewriting paths so that per-file history survives. The four original repositories are archived read-only rather than deleted, and their final commit SHAs are recorded in `docs/migration/0012-source-shas.txt`.

## If this looks wrong to you in a year

Three choices here are deliberate and look like mistakes at first glance:

1. **Generated code is committed.** Not because we like generated code in review, but because it makes wire-format changes visible in the diff that causes them. The dirty-tree check in CI is what keeps `gen/` honest. Do not delete it without replacing that visibility.
2. **`web-console` is in a repository whose main justification is protobuf sharing, and it does not use protobuf.** It consumes `gen/openapi/gateway.v1.yaml`, which is derived from the gateway protos, so it needs lockstep with the gateway anyway. Leaving it out would have preserved a two-repository split with cross-repository version coupling, which is the thing we were removing.
3. **There is no build system beyond shell scripts and `go.work`.** That is a choice sized to six engineers, not a claim that it scales.

## Revisit this decision when any of these is true

- Engineering headcount passes 15, or a second team owns one of the services outright.
- CI usage exceeds 1,800 minutes for three consecutive months.
- A service needs a release cadence or a compliance audit boundary that per-path CI cannot express.
- A fifth language enters the repository and `affected.sh` needs a real dependency graph.

## References

- ADR 0004, Share protobuf definitions via Git submodule (superseded)
- Incident reports INC-0231 (2025-11-14) and INC-0287 (2026-04-02)
- `docs/ci/affected-targets.md` for the path-to-target table
- Buf breaking-change detection: <https://buf.build/docs/breaking/overview>
