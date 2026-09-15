---
name: write-docs
description: Invoke before writing or reviewing a README, docs, PR or release text, spec, or CONTRIBUTING.
---

# Write Docs

TRIGGER

+ writing or updating README.md, docs/**, or any doc a consumer of the artifact reads
+ writing a PR description, commit message, release notes, specification, decision record, CONTRIBUTING, or runbook
+ reviewing or de-slopping existing text → review-docs
+ authoring skills, steering, or agent definitions → write-agentic
+ code comments and docstrings → language conventions

## Documentation contract

Ordinary documentation describes the current artifact directly: behavior, interface, configuration, constraints, and reader actions needed to use, verify, or reproduce it. Keep process history in change communications or decision records.

MUST Write direct, concise prose for a technically capable reader. Omit primers, prerequisite tutorials, remedial definitions, hand-holding, repeated rationale, and explanations unrelated to use, verification, or reproduction.
MUST Include explanations and claims only when a reader needs them to act on the current contract, establish a prerequisite, observe a safety constraint, or apply an implicit invariant.
MUST Verify present-tense claims against code at HEAD. Delete claims about behavior the artifact does not implement.
MUST State a measurement only when it supports a current threshold, capacity, cost, or reader decision, with its baseline and method.
MUST Use decisive normative language. Name the actor, action, condition, command, path, version, or other checkable particular.
MUST Apply the aggressive deletion test to every sentence, list item, table row, and paragraph: if removing it changes no reader action or understanding of the current contract, delete it.
Keep ordinary documentation focused on current behavior and reader action. Move process narration, author effort, chronology, job IDs, phase timings, causal journeys, superseded behavior, rejected alternatives, future promises, and operational archaeology to the appropriate genre.
Keep cache and performance details only when a current limit, capacity, cost, or reproduction step requires them.

## Genre boundaries

| Genre | Current artifact rule | Permitted delta/history/future |
|---|---|---|
| `consumer` | Describe shipped behavior and reader use | None in body; feature flags are current opt-in configuration, not roadmap text |
| `reference` | State exact interface, procedure, safety constraint, or reproducible operation | None except dated facts required to operate or verify it |
| `informal` | Keep the reader's immediate context and answer | Keep context separate from project history and promises |
| `change-comms` | Describe the change, rationale, and verification | Deltas and past tense are permitted; keep roadmap and file-by-file archaeology elsewhere |
| `internal` | State requirements, decisions, contributor constraints, and consequences | ADRs may preserve rationale and alternatives; specs may state future intent when acceptance criteria are explicit |
Load the matching reference before writing. Keep genre exceptions in their designated genre.
## Genre → reference
| Surface | LOAD | Lint profile | `genre` |
|---|---|---|---|
| README.md, docs/**, anything a user of the artifact reads | references/consumer-docs.md | `normal` | `consumer` |
| PR bodies, commit messages, hand-written release notes | references/change-comms.md | `normal` | `change-comms` |
| specifications, decision records, constitutions, CONTRIBUTING, contributor docs | references/internal-docs.md | `normal` | `internal` |
| reference material, API docs, runbooks, procedures, safety text | references/internal-docs.md | `strict` | `reference` |
| issue comments, discussion replies, blog posts, informal prose | references/consumer-docs.md | `relaxed` | `informal` |
Exception routing is based on document purpose, not passage wording. Migration guides and explicit before/after change tracking use `change-comms`. ADRs and decision records, future release plans and specifications, and explicitly historical reports or data use `internal`. Procedures and reference documents use `reference` for current operation or reproducibility. Classify these documents by purpose rather than using `consumer` to exempt history or future content.
## Workflow
1. Classify the document with the table. LOAD its reference and record `genre` and `profile`.
2. Draft the smallest current-contract document: purpose, reader actions, behavior, interface, configuration, constraints, and verification steps that apply.
3. Apply the deletion test. Remove tangents, process narration, past-state archaeology, future promises, and explanations that do not change a reader action or understanding. Keep cache details only when a current actionable limit depends on them.
4. Verify every claim against code at HEAD. Every consumer example MUST be copy-paste runnable and have a matching executable test under `examples/`.
5. Run `slopvac lint <file>... --profile <profile> --format json`; fix every ERROR and fix or justify every WARNING. On exit 2, act on native findings and report every `documents[].unchecked`; report the file as incomplete.
6. MUST Invoke `review-docs`, passing `genre` and `profile`. Fix its verdict before shipping.
## Sentence rules
MUST Write one idea per sentence, active voice with the actor named, and one term for each concept.
MUST Put a condition before the command it governs. Keep instructions near 20 words and descriptive sentences near 25 words; split instead of using a semicolon.
MUST Delete adjectives without a number, benchmark, or feature list; delete hedges that do not name real uncertainty; give every comparative its baseline and every quantity its count.
NOT In ordinary docs (`consumer`, `reference`, and `informal`), use relative time references such as `recently`, `currently`, `for now`, `last quarter`, or `in the future`. Give a date or version. Change communications may describe a dated delta, and internal specifications or plans may state dated future intent.
NOT In ordinary docs, use status language or history narration in a doc body. Change communications may describe deltas and past state; internal ADRs, decision records, specifications, or historical reports may retain their permitted rationale, alternatives, or future intent.
MUST State rationale in a change communication or decision record. Include it in ordinary docs only when the reader needs a constraint to operate the artifact.
MUST Describe implemented behavior in ordinary docs. Delete unbuilt behavior rather than weakening it with "coming soon"; an internal specification or plan may state unbuilt behavior only with explicit acceptance criteria.

## Gate

Run `uvx slopvac`; fall back to `pipx run slopvac`, `pip install slopvac`, or `uvx --from <path-to-checkout> slopvac` when resolution requires it, and report which command ran.

The project owns thresholds in `slopvac.toml`. Fix prose before changing a rule. Use `slopvac explain <rule_id>` for closed exception lists; never invent suppression reasons.
