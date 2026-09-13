# ADR: Consolidate Four Services into One Monorepo

**Status**: Accepted

## Context

Four independent repositories house the services that compose the platform: API server, worker service, shared schema definitions, and client library.
Three services (API server, worker, client library) share protobuf schemas.
Six developers contribute across the codebase.
Maintaining schemas across repositories via git submodules produced two production incidents in which schema versions drifted between services.
Each incident required manual reconciliation and deployment coordination.

A monorepo consolidation proposal emerged to eliminate drift risk and simplify cross-service changes.
The team identified two alternatives: git submodules (rejected earlier due to drift incidents) and a meta-repo tool.

The CI budget constraint is 2,000 minutes per month.
The current total across four repositories is 1,200 minutes monthly; the team must avoid exceeding 2,000 minutes after consolidation.

## Decision

Merge the four repositories into a single monorepo with the following structure:

- `/services/api` – API server
- `/services/worker` – Worker service
- `/services/client` – Client library
- `/schemas` – Shared protobuf definitions
- `/ci` – Shared CI/CD configuration

Store protobuf schemas in `/schemas` and reference them as a local path dependency from the three consuming services.
This eliminates schema version pinning and submodule synchronization overhead.

Configure CI to build only the services whose code changed in each commit.
Use file-path triggers to run API tests only when `/services/api` or `/schemas` changes, and likewise for the worker and client.

## Consequences

**Positive**

The team establishes a single source of truth for schemas.
Cross-service changes that require schema updates (a field addition, for example) now occur in one commit, eliminating async coordination.
New developers see the full architecture in one clone instead of coordinating three submodule checkouts.
The build-on-change filter keeps CI costs below 1,500 minutes per month, preserving budget headroom.

**Negative**

Developers can no longer work on a single service in isolation; a clone takes longer and the codebase size increases.
A bug in shared CI configuration or build tooling affects all four services.
Code review must account for cross-service changes in one PR; the team must establish conventions for PR scope.

## Rejected Alternatives

| Alternative | Reason |
| --- | --- |
| Continue with git submodules | Schema versions drifted twice in production, requiring manual reconciliation. Team concluded manual synchronization is not reliable. |
| Deploy a meta-repo tool (e.g., Bazel, Pants) | Onboarding six developers on a new build system would delay delivery by four weeks. The team prioritizes deployment speed and chose native tooling. |
