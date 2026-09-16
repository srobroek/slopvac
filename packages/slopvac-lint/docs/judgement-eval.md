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
