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

The recall gold set is `tests/fixtures/judgement/gold/gold-v1.jsonl`: 100 seeded defects and 100 matched controls spanning every shipped judgement family. A seeded row is a hit when the model's evidence quote overlaps that row's `defect_span`; a confirm on a control is a false positive. Recall is therefore `hits / 100`, while controls measure false positives separately.

## CLI driver

The CLI driver prepares and adjudicates a judgement run. It reports model confirms and rejects, and a CONFIRM on a rule whose `judgement_ceiling` is `error` counts toward the `max_errors` gate. See the [README judgement layer guide](../README.md#judgement-layer) for the user workflow.

`prepare` runs the deterministic scan and writes model-ready artifacts. It never calls a provider. The caller reads each `prompts.jsonl` row, sends `prompt.system` and `prompt.user` to a provider, validates the provider response against `response_schema`, and appends a `responses.jsonl` row.

```sh
uv run --project packages/slopvac-lint slopvac judgement prepare --config slopvac.toml --out .slopvac-judgement --packs all --max-calls 300 --yes packages/slopvac-lint/README.md
uv run --project packages/slopvac-lint slopvac judgement finish --out .slopvac-judgement --responses .slopvac-judgement/responses.jsonl
uv run --project packages/slopvac-lint slopvac judgement compare --out .slopvac-judgement
```

`--packs` accepts `all` or comma-separated pack ids. `prepare` creates `--out`, runs lint, and writes deterministic reports before it checks the call count. If the count exceeds `--max-calls` (300 by default), it refuses before writing prompts, units, or the manifest; the earlier output remains. Pass `--yes` to continue. The caller owns provider selection, authentication, retries, and transport.

Each `prompts.jsonl` row contains `call_id`, top-level `unit_ids`, `prompt.system`, `prompt.user`, `response_schema`, `pack_id`, `kind`, and `cache_keys`. The JSON string in `prompt.user` contains `passages` and `pairs`; `pairs` is not a top-level row field. Each `responses.jsonl` row contains `call_id` and `response`. A multi-unit response uses `{"results": [...]}` in prompt order.

`prepare` writes `prompts.jsonl`, `units.jsonl`, `documents/*.json`, deterministic per-document reports, and `manifest.json` under `--out`. `finish` writes `findings.jsonl`, `report.json`, and `report.md`. `compare --apply-preview` writes checker-passed rewrites under `--out/preview/`.

The driver records malformed responses as failures instead of silently dropping units. The host then performs schema checks, evidence checks, adjudication, coverage, and aggregation.

The judgement layer reports model confirms and rejects rather than rewriting source or deterministic findings. A CONFIRM on a rule whose `judgement_ceiling` is `error` counts toward the `max_errors` gate. Other judgement outcomes can adjust the reported score without entering deterministic warning or error counts.

Measured precision on the two full runs so far
(`docs/research/rubric-2026-09-15/evaluation/`): 9 of 37 confirms on the local
corpus and 5 of 95 on the sibling repositories were real defects. `FP-PRESERVE-MISS`
is counted as a false positive; diagnostic fragment-unit labels are not added to FP.
to normative lines (MUST, NOT, DEFAULT), to factual "X, not Y" contrasts, and to
plain section titles. When you act on a report, discard a confirm whose rewrite
changes what the sentence claims, targets a specification or steering line, or
rests on an evidence quote that is not in the unit. Do not add rule-level
suppressions for these cases; they also remove the true positives, which sit on the
same rules.

## Normalized evaluation records

The raw records and their normalization contract live in the [record schema](research/rubric-2026-09-15/evaluation/RECORD-SCHEMA.md). Each normalized file preserves the raw record, reports strict and lenient precision, per-rule adjudication, abstention and evidence-validity fields, and marks unavailable denominators as `null`.

| Run | Normalized record |
| --- | --- |
| Local corpus | [local-corpus-run.normalized.json](research/rubric-2026-09-15/evaluation/local-corpus-run.normalized.json) |
| Sibling full run | [sibling-full-run.normalized.json](research/rubric-2026-09-15/evaluation/sibling-full-run.normalized.json) |
| Sibling adjudication | [sibling-full-run-adjudication.normalized.json](research/rubric-2026-09-15/evaluation/sibling-full-run-adjudication.normalized.json) |
| Heldout baseline | [heldout-baseline.normalized.json](research/rubric-2026-09-15/evaluation/heldout-baseline.normalized.json) |
| Heldout baseline adjudication | [heldout-baseline-adjudication.normalized.json](research/rubric-2026-09-15/evaluation/heldout-baseline-adjudication.normalized.json) |
| Heldout v2 | [heldout-v2.normalized.json](research/rubric-2026-09-15/evaluation/heldout-v2.normalized.json) |
| Heldout v2 adjudication | [heldout-v2-adjudication.normalized.json](research/rubric-2026-09-15/evaluation/heldout-v2-adjudication.normalized.json) |

## Standalone Bedrock evaluation runner

The repeatable runner uses the same prompt assembly and JSON parser as the original
session shard template, while supporting resumable synchronous calls and Bedrock batch
inference. Run it from the package directory with `uv run scripts/judgement_bedrock_batch.py`:

```sh
uv run scripts/judgement_bedrock_batch.py todo --prompts prompts.jsonl --responses responses.jsonl --out todo.jsonl
uv run scripts/judgement_bedrock_batch.py invoke --todo todo.jsonl --model-id MODEL_ID --out responses.jsonl --concurrency 4
uv run scripts/judgement_bedrock_batch.py submit --todo todo.jsonl --model-id MODEL_ID --bucket BUCKET --role-arn ROLE_ARN --job-name judgement-001 --out-dir bedrock-batch-001
uv run scripts/judgement_bedrock_batch.py collect --job-dir bedrock-batch-001 --out responses.jsonl
```

Batch jobs require at least 100 records; smaller remainders automatically use `invoke`.
The model id is required and recorded in `job.json`. The earlier 1,546 calls used the
session default `global.anthropic.claude-fable-5-1`; this runner is explicit and therefore
repeatable, but its sampling settings may not be homogeneous with that earlier arm.
