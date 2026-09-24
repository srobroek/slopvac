# Rubric research record, 2026-09-15

> **Status:** frozen historical research tied to the source commits and artifacts
> named below. Counts, paths, branch names, and implementation gaps describe the
> 2026-09-15 study and are not current runtime documentation. The current
> judgement contract is documented in [../../judgement-eval.md](../../judgement-eval.md).

Genre: internal research record. This file records how the review was run and
what it produced.

## What is in this directory

| Path | Content |
|---|---|
| `rubric-review.md` | Verdicts on the 14 design claims, evidence, 13 adversarial cases, the three highest-yield false-positive reducers, the second-round contract challenge. |
| `rubric-contract.json` | The accepted machine-readable contract, schema_version 1.1.2, source_commit `df7ba4412387c474dc8ef646a8d594dc44c1c7eb`, target_base_commit `12042c9e7d`. Authoritative for the downstream implementation; the 66th rule record is provisional (see rubric-review.md section 6.1). |
| `rubric-contract.sha256` | SHA-256 of the exact `rubric-contract.json` bytes. |
| `challenges/claims.md` | The numbered claim list C1-C14 every challenge used. |
| `challenges/Ch*.md` | Adversarial-challenger reports: one per research question, one on the aggregation measurements, one on the synthesised contract, one on the sibling `autoresearch/*` branch. |
| `challenges/*Lit.md` | Supplementary literature collection by scout agents; provisional, superseded where a `Ch*` report disagrees. |
| `challenges/AggregationFacts.md` | The measurement digest handed to the aggregation challenger. |
| `measurements/*.py` | Scripts that produced every number in the review: rule inventory, co-occurrence, top pairs, contract builder with validation. |
| `measurements/cooccurrence.json` | Raw co-occurrence output for both corpora. |

## How the numbers were produced

- Checkout: worktree branch `research/rubric-review-20260915` at `df7ba4412387c474dc8ef646a8d594dc44c1c7eb`; no repository file was modified during the study.
- Linter: `slopvac lint --profile strict --format json` with this repository's `slopvac.toml`, Vale enabled (133 of 167 Vale-backed rules ran).
- Corpus A: 16 repository Markdown files after the config exclusions (12,339 words).
- Corpus B: 98 model-authored Markdown documents over 2 KB from local agent-session artefacts (220,336 words). The corpus is not in the repository; `cooccurrence.json` holds its results.
- Units: blank-line-delimited paragraphs, with 10-line windows as a robustness check. Pairs were formed over rules with at least 3 unit hits.
- Reproduce the inventory and the contract from the stored location:

  ```sh
  uv run --project packages/slopvac-lint python packages/slopvac-lint/docs/research/rubric-2026-09-15/measurements/inventory.py
  uv run --project packages/slopvac-lint python packages/slopvac-lint/docs/research/rubric-2026-09-15/measurements/build_contract.py
  sha256sum -c packages/slopvac-lint/docs/research/rubric-2026-09-15/rubric-contract.sha256
  ```

  `build_contract.py` writes `rubric-contract.json` and its digest next to itself, sorts every key, orders every ID-keyed list, and asserts that its 66 rule records carry unique ids, that the probe and span packs partition them exactly once, and that no machine path leaks. It does not read the YAML; the equality of the loaded YAML contracts with these records is asserted by the package test `tests/test_judgement_metadata.py` (PR #81).

## How the review was run

1. The design document was decomposed into 14 numbered claims (`challenges/claims.md`).
2. Eight briefs ran in parallel: six literature challenges (dimensions, scale, gates, protected classes, composition, versioning), one repository challenge that built counter-cases from real prose, and one aggregation challenge fed with the measurements above. Each brief required a URL, a `path:line`, or a measurement behind every verdict and an explicit UNSUPPORTED mark otherwise.
3. The eight reports were synthesised into the review and the contract.
4. The contract was challenged again (`challenges/ChContract.md`: 17 findings, 8 implementation blockers). Version 1.1.0 amends the contract text for every finding that text can settle; what needs code is recorded as `implementation_gate.blockers` B1-B7.
5. Two adjacent artefacts were assessed against the contract: the `autoresearch/also-for-slopvac-we-just-added-the-new-rules-to-20260915` branch (`challenges/ChAutoresearch.md`) and draft PR 79 (`challenges/PR79.md`).

Agent routing during the study: the generic `task` and `scout` agents were routed to a provider that rate-limited for the whole session and could not write shared artefacts; three literature scouts failed outright and the rest delivered late. Every verdict-bearing report came from the `adversarial-challenger` agent, which ran 3-9 minutes per brief.

## Status of the contract

Not implementation-ready. `implementation_gate.blockers` lists what must exist first:

- B1 projection map (code-point to raw-byte segments) persisted for unit and context; `analyze.py:582-606,817-845` keeps line starts only.
- B2 host finding record type carrying outcome, severity, `core_fired`, `component_id`, extended `rewrite_status`.
- B3 dependence table artefact with a hash, derived from a held-out labelled set.
- B4 pack renderer producing the RFC 8785 `pack_object` and `rubric_revision` bytes.
- B5 YAML schema additions per rule: `dims`, `evidence`, `warrant_min`, `protects`, `judgement_ceiling`, `adjudicates`, `allowed_transitions`, `host_predicates`; a `scope` for `orwell.concrete-floor`.
- B6 typed fact-preservation checker.
- B7 origin and region classifier for admission gate A5.

Every threshold marked `provisional` or `disabled_experimental` in the contract stays that way until the matching question in `unresolved_evaluation_questions` (Q01-Q14) has been measured on this repository.
