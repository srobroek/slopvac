# Judgement evaluation

The judgement evaluator measures the 65 contextual rules separately from the
deterministic lint gate. The CLI prepares prompts and validates model output.
Your harness selects and calls the provider.

A reproducible evaluation arm records the provider, model revision, decoding
settings, request identity, and repeat number. Reusing a cached response requires
the same request identity.

## Runtime contract

The shared judgement spine is
[`src/slopvac/judgement/spine.md`](../src/slopvac/judgement/spine.md). Each model
result uses one of four verdicts: `confirm`, `reject`, `preserve`, or
`abstain`.

Host validation is authoritative. Model output can be parsed successfully and
still fail host checks such as expected unit membership or evidence location.
Benign annotation keys that the compatibility layer accepts are recorded
separately rather than becoming part of the canonical result.

## Coverage

Coverage is reported by document, pack, and rule. The counters distinguish:

- eligible units;
- attempted units;
- confirmed, rejected, preserved, and abstained results;
- failed, truncated, and not-run units.

An abstention is a completed attempt and is counted separately. It does **not**
make coverage `PARTIAL`. Failed, truncated, and not-run units do make the
affected coverage bucket partial. The evaluator does not convert those states
into abstentions.

The shipped dependence table,
[`src/slopvac/judgement/dependence_table.json`](../src/slopvac/judgement/dependence_table.json),
is marked `uncalibrated`. Until calibrated pairs are supplied, aggregation
groups confirmed findings by overlapping evidence spans only.

## Recall fixture

The committed gold manifest is
[`tests/fixtures/judgement/gold/gold-v1.jsonl`](../tests/fixtures/judgement/gold/gold-v1.jsonl).
It contains one metadata row, **98 seeded defect rows across all 65 judgement
rules, and 100 control rows**.

For a seeded row, evidence must overlap the row's `defect_span` to count as a
hit. Controls measure behavior on neutral text. Human-prose confirms are not
automatically false positives; measured precision requires adjudication.

## CLI workflow

Prepare a run:

```sh
slopvac judgement prepare README.md \
  --config slopvac.toml \
  --out .slopvac-judgement \
  --packs all \
  --max-calls 300
```

`prepare` runs deterministic lint first and writes its reports. It then prepares
units, prompts, and a manifest. If the proposed call count exceeds
`--max-calls`, it refuses to write the prompt/unit/manifest portion unless
`--yes` is supplied.

Each `prompts.jsonl` row contains its `call_id`, `unit_ids`, prompt, response
schema, pack id, kind, and cache keys. The caller sends `prompt.system` and
`prompt.user` to a provider and writes one `responses.jsonl` row per call:

```json
{"call_id":"CALL_ID","response":{"results":[]}}
```

Finish and compare:

```sh
slopvac judgement finish --out .slopvac-judgement \
  --responses .slopvac-judgement/responses.jsonl
slopvac judgement compare --out .slopvac-judgement
```

`finish` writes `findings.jsonl`, `report.json`, and `report.md`.
`compare --apply-preview` may additionally write checker-passed rewrite previews
under `preview/`; it does not edit the source document.

The default `unique-quote` offset salvage relocates quoted evidence only when
the quote occurs exactly once in its unit. Use `finish --offset-salvage none`
when raw model offsets must be preserved.

## Agent-facing preparation

For a harness that prefers one readable bundle:

```sh
slopvac judgement brief README.md --out .slopvac-judgement --packs fired
```

`brief` writes `brief.md` and `brief.json` in addition to the structured run
files. `--packs fired` selects packs whose categories produced deterministic
findings. If none qualify, it falls back to all packs and prints a warning. Use
`--packs all` when contextual review must not depend on deterministic findings.

`brief` uses the nearest discovered configuration, or starter defaults when no
configuration exists. Unlike `prepare`, it calls preparation with the call
budget approved, so `--max-calls` does not act as a refusal gate. Inspect the
reported call count before dispatching model work.

Validate each response before appending it:

```sh
slopvac judgement validate --run .slopvac-judgement --file response.json
```

`validate` checks response shape, call resolution, expected unit membership,
result ordering, and the model-output schema. It returns 0 for a valid response,
2 for a validation failure, and 1 for unreadable or malformed JSON. Evidence
quote locations are checked during `finish`.

## Reporting and gates

Judgement confirms can lower `judgement_adjusted_score` by a bounded reporting
penalty. They do not change deterministic findings, deterministic error or warning
counts, the lint exit status, or deterministic thresholds such as `max_errors`.

A judgement cluster result is also reported separately from the deterministic
gate. The current dependence table is uncalibrated, so cluster interpretation
must retain that limitation.

A passing deterministic run and a clean judgement report still do not establish
factual correctness. Documentation claims require verification against code or
another authoritative source.

## Normalized evaluation records

The normalization schema is
[`research/rubric-2026-09-15/evaluation/RECORD-SCHEMA.md`](research/rubric-2026-09-15/evaluation/RECORD-SCHEMA.md).
Committed normalized records include:

- [local corpus](research/rubric-2026-09-15/evaluation/local-corpus-run.normalized.json)
- [sibling full run](research/rubric-2026-09-15/evaluation/sibling-full-run.normalized.json)
- [sibling adjudication](research/rubric-2026-09-15/evaluation/sibling-full-run-adjudication.normalized.json)
- [held-out baseline](research/rubric-2026-09-15/evaluation/heldout-baseline.normalized.json)
- [held-out baseline adjudication](research/rubric-2026-09-15/evaluation/heldout-baseline-adjudication.normalized.json)
- [held-out v2](research/rubric-2026-09-15/evaluation/heldout-v2.normalized.json)
- [held-out v2 adjudication](research/rubric-2026-09-15/evaluation/heldout-v2-adjudication.normalized.json)

The dated wider evaluation record is
[`2026-09-19-wider-evaluation.md`](research/rubric-2026-09-15/evaluation/2026-09-19-wider-evaluation.md).
Historical records retain the instrument and denominators used when they were
created; they are not rewritten to look like results from the current contract.

## Bedrock runner

The optional Bedrock helper can run prepared prompts synchronously or through
Bedrock batch inference:

```sh
cd packages/slopvac-lint
uv run scripts/judgement_bedrock_batch.py todo \
  --prompts prompts.jsonl --responses responses.jsonl --out todo.jsonl

uv run scripts/judgement_bedrock_batch.py invoke \
  --todo todo.jsonl --model-id MODEL_ID \
  --out responses.jsonl --concurrency 4
```

For batch inference:

```sh
uv run scripts/judgement_bedrock_batch.py submit \
  --todo todo.jsonl --model-id MODEL_ID \
  --bucket BUCKET --role-arn ROLE_ARN \
  --job-name judgement-001 --out-dir bedrock-batch-001

uv run scripts/judgement_bedrock_batch.py collect \
  --job-dir bedrock-batch-001 --out responses.jsonl
```

The caller is responsible for AWS credentials, region selection, a private S3
bucket, and a Bedrock batch role appropriate to that account. Model and batch
availability are account- and region-dependent; this guide does not encode a
developer's account, bucket, or profile.

## Noise-floor measurement

The noise-floor helper prepares repeated calls, analyses verdict variation, and
keeps the policy decision separate from the measurement:

```sh
uv run scripts/judgement_noise_floor.py prepare \
  --prompts prompts.jsonl --subsample subsample.json \
  --out repeated-prompts.jsonl --model-id MODEL_ID --max-tokens 32000

uv run scripts/judgement_noise_floor.py analyse \
  --prompts repeated-prompts.jsonl --responses responses.jsonl \
  --out-dir noise-floor

uv run scripts/judgement_noise_floor.py decide \
  --noise-floor noise-floor/noise-floor.json \
  --threshold 0.10 --min-units 30 \
  --out noise-floor/variance-policy.json
```

The instrument reports measurements; `decide` writes a policy record. The
normal `finish` command does not apply majority-of-three aggregation.

## Adjudication

The adjudication helper independently labels model confirms for precision
measurement. It does not rewrite the finished judgement report.

```sh
uv run scripts/judgement_adjudicate.py run \
  --run-dir .slopvac-judgement \
  --corpus-root /path/to/corpus \
  --model-id MODEL_ID --reasoning-effort high \
  --repeats 3 --out .slopvac-adjudication --class human
```

Saved calls can be re-rendered without provider access:

```sh
uv run scripts/judgement_adjudicate.py report \
  --run-dir .slopvac-judgement --corpus-root /path/to/corpus \
  --out .slopvac-adjudication --class human

uv run scripts/judgement_adjudicate.py consistency \
  --run-dir .slopvac-judgement --corpus-root /path/to/corpus \
  --out .slopvac-adjudication --class human
```

Precision claims must state their adjudication denominator. Confirm rate by
itself is a screening measure, not a precision estimate.
