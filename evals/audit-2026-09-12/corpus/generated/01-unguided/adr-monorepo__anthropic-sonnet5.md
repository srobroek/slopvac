# ADR-0012: Consolidate Four Repositories into a Monorepo

## Status

Accepted — 2026-09-12

## Context

The team currently maintains four separate repositories, three of which depend on a shared set of protobuf schemas for inter-service communication. The team consists of six developers, and CI spend is capped at 2,000 minutes per month across all repositories.

Schema drift has caused two production incidents. In both cases, a service consumed a protobuf schema version that no longer matched what its peers were using, because the schema repository was versioned and released independently, and nothing forced dependent services to pick up the change in lockstep. The mismatch was only caught after deployment.

The team needs a way to guarantee that a schema change and every consumer of that schema move together, atomically, in a single reviewable unit — without adding tooling overhead that six developers don't have the bandwidth to learn and maintain.

## Decision

Merge the four repositories into a single monorepo. Each service keeps its own top-level directory; the shared protobuf schemas move into a `proto/` directory at the repository root. Schema changes and the corresponding updates to consuming services are made in the same commit and the same pull request, enforced by code review rather than by tooling. CI runs are scoped to only the directories affected by a given change, to stay within the 2,000-minutes-per-month budget.

## Alternatives Considered

### Git submodules (schema repo as a submodule of each service)

Rejected. This is close to the current setup and was tried in spirit already: the schema repository is versioned independently, and each service pins a commit or tag. Schema drift happened twice under this model — a service's submodule pointer was not updated when the schema changed, so it kept running against a stale contract until something broke in production. Submodules make the drift *possible* rather than preventing it; the pointer can always lag behind the actual schema history, and nothing forces it to be updated in the same review as the schema change. Given that this exact failure mode has already caused two incidents, the team ruled it out rather than trying to patch it with more discipline or tooling.

### Meta-repo tool (e.g., a manifest-based multi-repo orchestrator)

Rejected on learning cost. Tools in this category (Google's `repo`, `vcstool`, similar manifest-driven wrappers) can synchronize multiple repositories to consistent states and would address the drift problem without a full merge. However, they introduce a new workflow, a new manifest format, and new failure modes that the team would need to learn, document, and troubleshoot. With six developers and no dedicated platform role, the ongoing cost of maintaining expertise in a tool that exists only to work around multi-repo drift was judged higher than the cost of removing the multi-repo structure itself.

### Status quo (four repositories, independently versioned schemas)

Rejected. This is the setup that produced the two drift incidents. Doing nothing does not solve the problem this ADR exists to address.

## Consequences

**What this buys us:**

- A schema change and its consumers are reviewed and merged as one unit. It is no longer possible to update the schema without the pull request also touching every service directory that depends on it — the drift failure mode is closed by construction, not by process discipline.
- One version-control history, one set of branch protections, one place to look for "what changed and why."
- No new tooling to learn. Contributors already know Git; there is no manifest format or orchestrator CLI layered on top.

**What this costs us:**

- **CI must be scoped, not blanket.** Running the full test suite for all four services on every commit would blow past 2,000 minutes/month quickly. CI is configured to detect which top-level directories (including `proto/`) changed in a given push or PR and run only the relevant services' pipelines. If you add a new service directory or restructure an existing one, you must update the CI path filters — forgetting to do so either silently skips tests it should run, or runs everything and burns the budget. When you touch `proto/`, the pipeline is configured to run all three consuming services' test suites, since that's the one directory where "just build what changed" is not enough — a schema change affects everyone downstream of it even if you didn't touch their code.
- **The repository is bigger.** Clone times, IDE indexing, and search scope all grow. If this becomes a real friction point, consider a sparse-checkout or partial-clone setup for contributors who only work on one service — but do not do this preemptively; wait until someone actually feels the pain.
- **History is now shared and permanent.** The four original repositories' histories were merged in (not squashed to a single initial commit), so `git log` and `git blame` still work across the old boundaries. This makes the migration commit itself large and worth tagging clearly (see `v-monorepo-migration` tag) so anyone bisecting across the merge point knows where the seam is.
- **One repository, one set of outages.** A misconfigured CI pipeline, a broken root-level config file, or a bad `.gitignore` now has the blast radius of the whole team's workflow instead of one service's. This is the trade-off for atomicity: the same property that prevents schema drift also means a mistake in shared configuration affects everyone at once.

## Notes for a Future Contributor

If you're reading this a year from now and wondering why all four services live in one repository: it's because the alternative — independently versioned schemas consumed across repo boundaries — broke production twice. If you're tempted to split a service back out into its own repository, ask first whether that service still depends on `proto/`. If it does, splitting it out reintroduces the exact drift risk this ADR was written to close, and you should have a strong answer for how you'll re-establish atomic schema-and-consumer updates before doing so.

If the CI budget is under pressure, check the path-filter configuration before assuming you need a bigger budget or a different CI provider — the most common cause of budget overrun in this setup is a path filter that's broader than it needs to be, not an inherently expensive test suite.
