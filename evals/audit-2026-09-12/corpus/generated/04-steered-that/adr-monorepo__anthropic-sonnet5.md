# ADR-0012: Merge four service repositories into one monorepo

Status: Accepted
Date: 2026-09-13

## Context

Four repositories comprise the system: `orders`, `billing`, `notifications`, and `gateway`. `orders`, `billing`, and `notifications` share protobuf schemas. Schema drift between repositories reached production twice. The team has six developers. The CI budget is 2,000 minutes per month.

## Decision

Merge `orders`, `billing`, `notifications`, and `gateway` into one repository named `platform`. Store the shared protobuf schemas at `platform/proto/` as a single versioned source. Each service keeps its own top-level directory: `platform/orders/`, `platform/billing/`, `platform/notifications/`, `platform/gateway/`.

CI runs path-filtered: a change under `platform/orders/` or `platform/proto/` triggers the `orders` pipeline; a change under `platform/proto/` triggers the pipelines for all three consuming services. `gateway` does not consume `proto/` and its pipeline runs only on changes under `platform/gateway/`.

### Rejected alternatives

- Git submodules: rejected. Submodule references caused two production incidents from schema-version drift between the schema repository and consuming services.
- A meta-repo tool (coordinated multi-repo tooling): rejected. The tool's learning cost exceeded the value for a six-developer team.

## Consequences

- A schema change in `platform/proto/` and its consuming service change land in one commit; no cross-repository version pin can drift.
- CI path filtering keeps monthly usage under the 2,000-minute cap: a change to one service triggers only that service's pipeline, and a `proto/` change triggers at most three pipelines.
- `git blame` and `git log` cover all four services in one history.
- A contributor clones one repository to work on any service; the clone includes the code for all four services.
- Add a fifth service by creating a new top-level directory and a corresponding CI path filter.

## Acceptance criteria

- A commit that changes `platform/proto/` and does not update all three consumers fails CI for each unupdated consumer.
- A commit that changes only `platform/gateway/` runs the `gateway` pipeline and no other.
- Total CI minutes for a calendar month stay at or under 2,000, measured from the CI provider's usage report.
