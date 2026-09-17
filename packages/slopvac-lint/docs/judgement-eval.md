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

## CLI driver

Use the driver when a model call must run outside `slopvac`. The first command runs
the deterministic scan once and writes compact prompts, units, per-document data,
and a manifest. Runs are bounded to 300 calls by default; pass `--yes` to override
the bound after reviewing the per-pack counts printed by an over-limit run.

```sh
uv run slopvac judgement prepare --config slopvac.toml --out .slopvac-judgement docs/guide.md
```

For a stricter bound, set `--max-calls N`. A SPAN call contains up to five passages
and one pair per passage/rule; each passage's text and neighbouring context occur
once, while `pairs` gives the expected result order. `units.jsonl` contains only
unit-local data. Shared projection segments, source hash, and full projected text
are stored once in `documents/<document>.json`.

Fill `.slopvac-judgement/responses.jsonl` with one record per prompt. Each record
has the form `{"call_id": "...", "response": ...}`. Calls with multiple units
wrap outputs as `{"results": [model_output, ...]}` in the documented pair order;
a single PROBE call may return one model output object.

Run the host checks and report generation after the responses are complete.

```sh
uv run slopvac judgement finish --out .slopvac-judgement --responses .slopvac-judgement/responses.jsonl
uv run slopvac judgement compare --out .slopvac-judgement
```

`finish` rejects malformed calls, records schema errors in `failed.jsonl`, and
writes `findings.jsonl`, `report.json`, and `report.md`. `compare --apply-preview`
writes checker-passed proposed rewrites under `.slopvac-judgement/preview/`.

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
