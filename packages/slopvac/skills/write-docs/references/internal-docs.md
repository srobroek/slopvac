# Internal Docs (specs, ADRs, constitutions, CONTRIBUTING, runbooks)

Audience: technically capable contributors. State the requirement, decision, or procedure directly; omit primers, remedial definitions, and repeated rationale unless they are needed to act or verify.

## Current-artifact contract

MUST Use the same reader-relevance and deletion test as consumer docs: keep what changes a contributor action, requirement, decision, constraint, or verification step.
Keep internal docs focused on requirements, decisions, procedures, and contributor actions. Store work logs, postmortems, task lists, optimization diaries, and life stories elsewhere. Keep job IDs, phase timings, causal journeys, superseded behavior, and future tasks only when the current requirement or decision makes them actionable.

## Explicit exceptions

MUST ADRs state context, decision, and consequences. ADRs MAY preserve rejected alternatives and rationale because recording the decision is their purpose; keep each alternative tied to the decision.
MUST Specs state testable requirements and MAY state future intent only with explicit acceptance criteria, scope, and verification. A target without those criteria is roadmap prose and must be deleted.
MUST Runbooks state the current procedure and safety constraints. Include history only when a dated fact changes the current operation.
DEFAULT Structured status metadata (ADR "Status: Accepted", spec frontmatter) is allowed; status narration inside body prose is not.
Keep journey narration, linked-source restatements, and prerequisite teaching out of the body. Reference linked sources once. Retain safety constraints, implicit invariants, and explanations required for the current action.

## Exception routing

Exception routing follows document purpose. Migration guides and explicit before/after change tracking use `change-comms`. ADRs, decision records, future release plans, specifications, and explicitly historical reports or data use `internal`. Procedures and reference documents use `reference` for current operation or reproducibility.
