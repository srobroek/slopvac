# slopvac judge corpus builder

This project builds provenance-only human source pointers and matched document generations for slopvac local judging. Source text, briefs, and generated text stay in the private S3 bucket or the gitignored `.cache/` directory.

## Install

```sh
cd scripts/judge-corpus
uv sync --locked
```

Use AWS profile `sjors+ig-genai-Admin` in account `536697262379` and region `us-east-1`. The profile must be allowed to create one tagged private S3 bucket, one Bedrock batch service role, and Bedrock batch jobs.

## Reproduce

Run the smoke corpus before scaling. The commands create a 50-source manifest, a roster, one Stage 1 batch input, and a Stage 2 batch input.

```sh
cd scripts/judge-corpus
uv run judge-corpus sources --limit 50
uv run judge-corpus roster
uv run judge-corpus provision
uv run judge-corpus prepare-briefs --limit 50 --model amazon.nova-lite-v1:0
uv run judge-corpus submit-briefs --input briefs/input.jsonl --model amazon.nova-lite-v1:0 --stage smoke-briefs
uv run judge-corpus wait --job-arn ARN_FROM_THE_PREVIOUS_COMMAND
uv run judge-corpus collect-briefs --prefix outputs/smoke-briefs/INPUT_STEM --model amazon.nova-lite-v1:0
uv run judge-corpus prepare-generation --limit 50
```

After inspecting the smoke report, rebuild the full manifest and submit each generation input file sequentially. `prepare-generation` assigns every brief to two models with deterministic vendor and tier rotation.

```sh
uv run judge-corpus sources --limit 3000
uv run judge-corpus prepare-briefs --limit 3000 --model amazon.nova-lite-v1:0
uv run judge-corpus submit-briefs --input briefs/input.jsonl --model amazon.nova-lite-v1:0 --stage briefs
uv run judge-corpus wait --job-arn ARN_FROM_THE_PREVIOUS_COMMAND
uv run judge-corpus collect-briefs --prefix outputs/briefs/INPUT_STEM --model amazon.nova-lite-v1:0
uv run judge-corpus prepare-generation --limit 3000
```

For each model entry printed by `prepare-generation`, submit its JSONL input and wait for completion before collecting it:

```sh
uv run judge-corpus submit-generation --input generated/inputs/MODEL.jsonl --model MODEL_ID
uv run judge-corpus wait --job-arn ARN_FROM_THE_PREVIOUS_COMMAND
uv run judge-corpus collect-generation --prefix outputs/generation/MODEL --model MODEL_ID
```

The submit command estimates input and output tokens at the published on-demand price with the documented batch discount. It refuses a job that would take the ledger above the USD 200 cap. It also refuses models without a recorded price.

## Outputs

- `sources/human.jsonl` records one immutable source pointer, revision date, licence, normalized-text digest, and S3 key per admitted document or section.
- `sources/dedup.jsonl` records every accepted or near-duplicate decision.
- `briefs/manifest.jsonl` records the abstract brief digest and source-overlap score. `briefs/rejections.jsonl` records invalid or leaking outputs; rejected briefs are written to `briefs/retry-input.jsonl` for a new batch.
- `models/roster.json` records live Bedrock text models, inference profiles, tier, vendor, and batch verification state.
- `generated/manifest.jsonl` records model, vendor, tier, inference parameters, token count, digest, and leak score. Leaking outputs are absent from this manifest and recorded in `generated/rejections.jsonl`.
- `ledgers/cost-ledger.json` records every submitted job and its pre-submit estimate.
- `ledgers/resources.json` records the bucket, role, and job ARNs.
- `corpus-build-report.md` summarizes counts by genre, source family, vendor, and tier.

Never commit `.cache/` or model output text. The root `.gitignore` excludes this cache path.

## Licence

The builder code is licensed under the repository licence. Each source row records the source licence; the corpus cannot be redistributed without checking the source licence and consent field.
