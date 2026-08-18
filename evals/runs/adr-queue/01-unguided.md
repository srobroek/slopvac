# ADR 0014: Adopt a Managed Queue

**Status:** Accepted
**Date:** 2026-03-14

## Context

As our system has grown, we've increasingly found ourselves in need of a robust message queue to decouple our services. This has become a mission-critical requirement, and after much discussion we felt it was important to document our thinking here.

We evaluated a number of options across the landscape of available solutions. Our constraints were fairly clear from the outset: we're a two-person team, we already have an existing cloud account, and we need to survive a zone outage.

## Decision

We will leverage a managed queue service rather than self-hosting.

## Rationale

Self-hosting was ultimately rejected on the grounds of operational load. With only two engineers, taking on the burden of running a distributed queue — patching, monitoring, capacity planning, upgrade coordination — simply wasn't tenable. We initially tried spiking a self-hosted deployment and quickly realized the ongoing cost would dominate our engineering time.

A second managed option was also considered but was rejected on cost at our expected volume. While it offered a somewhat richer feature set, the pricing model didn't align well with our usage pattern, and we couldn't justify the delta.

The chosen service integrates seamlessly with our existing cloud account, which was a significant factor. It also provides multi-zone durability out of the box, satisfying our availability requirement without additional work on our part.

## Consequences

- We accept vendor lock-in as a trade-off for reduced operational burden
- Our costs will scale with volume, which we'll need to monitor going forward
- We lose some flexibility around custom routing logic, though we don't currently need it

## Alternatives Considered

| Option | Verdict |
|---|---|
| Self-hosted | Rejected — operational load too high for a two-person team |
| Alternative managed service | Rejected — cost at expected volume |
| Managed service (chosen) | Accepted |
