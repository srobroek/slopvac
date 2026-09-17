# Judgement evaluation

The evaluator measures model decisions against the rubric contract. An instrument
sets one independent variable. It freezes the other comparison fields. An arm
names a provider and model revision. It also stores decoding settings, a seed,
and a repeat count. Each host record stores the instrument, unit, repeat, request
digest, and cache key. A changed request cannot reuse an old result.

## Replay mode

Run `python -m slopvac.judgement.eval run --replay fixture.jsonl` for a network-free
run. A JSONL fixture stores one response per request. Replay uses the same parser
and result checks as a provider adapter.

## Coverage report

`report` emits counts for each unit state. The states are eligible, attempted,
confirmed, rejected, preserved, abstained, failed, truncated, and not-run.

Abstention is a completed adjudication. It reduces coverage. The report lists its
reason in a separate table. The evaluator reports a document as partial when a unit
is failed, truncated, or not-run. The evaluator never changes those states into
abstentions.

## Dependence table status

The shipped `src/slopvac/judgement/dependence_table.json` has status
`uncalibrated` and contains no rule pairs. The aggregation layer therefore
builds components from span overlap only and logs that limitation. B3 remains
open until a held-out labelled set derives and validates the dependence pairs.

## CLI driver

The CLI driver prepares and adjudicates a reporting-only judgement run. See the [README judgement layer guide](../README.md#judgement-layer) for the user workflow.

`prepare` runs the deterministic scan and writes model-ready artifacts. It never calls a provider. The caller reads each `prompts.jsonl` row, sends `prompt.system` and `prompt.user` to a provider, validates the provider response against `response_schema`, and appends a `responses.jsonl` row.

```sh
uv run slopvac judgement prepare --config slopvac.toml --out .slopvac-judgement --packs all --max-calls 300 docs/guide.md
uv run slopvac judgement finish --out .slopvac-judgement --responses .slopvac-judgement/responses.jsonl
uv run slopvac judgement compare --out .slopvac-judgement
```

`--packs` accepts `all` or comma-separated pack ids. `prepare` refuses a run above `--max-calls` (300 by default), unless the caller passes `--yes`. The caller owns provider selection, authentication, retries, and transport.

Each prompt row contains `call_id`, `prompt.system`, `prompt.user`, `response_schema`, `pack_id`, and `units` or `pairs`. Each response row contains `call_id` and `response`. A multi-unit response uses `{"results": [...]}` in prompt order.

`prepare` writes `prompts.jsonl`, `units.jsonl`, `documents/*.json`, deterministic per-document reports, and `manifest.json` under `--out`. `finish` writes `findings.jsonl`, `report.json`, and `report.md`. `compare --apply-preview` writes checker-passed rewrites under `--out/preview/`.

The driver records malformed responses as failures instead of silently dropping units. The host then performs schema checks, evidence checks, adjudication, coverage, and aggregation.

## Reading confirms

A confirm is a suggestion, never a gate. The layer is reporting-only: no confirm
changes a pass/fail result, and the adjusted score moves by at most two points.

Measured precision on the two full runs so far
(`docs/research/rubric-2026-09-15/evaluation/`): 6 of 37 confirms on the local
corpus and 5 of 95 on the sibling repositories were real defects. Most wrong
confirms are style objections to ordinary technical agency ("the parser rejects"),
to normative lines (MUST, NOT, DEFAULT), to factual "X, not Y" contrasts, and to
plain section titles. When you act on a report, discard a confirm whose rewrite
changes what the sentence claims, targets a specification or steering line, or
rests on an evidence quote that is not in the unit. Do not add rule-level
suppressions for these cases; they also remove the true positives, which sit on the
same rules.
