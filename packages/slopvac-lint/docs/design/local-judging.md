# Spec: local typed judging

> **Status:** draft. Tracks GitHub issue #162 and bead `slopvac-2jg`. Work lands
> on branch `feat/local-judging`. Every worktree pull request targets that branch.
> Nothing in this spec changes the `slopvac` lint CLI, its findings, or its exit
> status.

Source versions, benchmark figures, and licence facts cited here are recorded
with their observation date in
[local-judging-evidence.md](local-judging-evidence.md). Re-verify a pinned
revision before an implementation stage depends on it.

## Scope

The judging layer answers typed questions about prose-quality defects in a
bounded span that the host selects. It has two roles:

- **Semantic detection.** The host asks whether a candidate span exhibits a
  defect that syntax, structure, patterns, or metrics cannot express.
- **Finding validation.** The host asks whether a deterministic finding is a real
  defect, a false positive, or undecidable from the supplied context.

Non-goals:

- Questions about authorship, provenance, or whether text is machine-generated.
- Changes to deterministic findings, lint scores, or exit status. A later,
  separately measured policy decision owns any such change.
- A generic quality score. Provider probabilities are decision evidence, not
  slopvac scores.
- A required cloud service. Every stage has a fully local path.

## Architecture

The client speaks one wire protocol: the TypeSafe Jev System One API. Local
judging runs the slopvac default model behind `slopvac-judge serve`. A user
overrides it by pointing the client at any other Jev-compatible endpoint, with an
optional token.

```text
slopvac-lint findings + candidate spans
        |
        v
slopvac-judge client --(Jev: POST /v1/systemone)--> default: slopvac-judge serve
        |                                             (slopvac default model)
        v                                            override: any Jev endpoint
deterministic host policy                             - hosted Jev (TypeSafe)
        |                                             - hosted DREX (Nace)
        v                                             - kev serve, Laya server
separately reported validation states
```

The host owns span selection, source offsets, rule identity, question wording,
and the mapping from answers to outcomes. A provider answers typed questions and
never emits source text, offsets, or replacement text that the host uses as
evidence.

### Package boundary

All judging code lives in a new package, `packages/slopvac-judge`, with its own
`slopvac-judge` CLI. It depends on `slopvac-lint` for findings and spans.
`slopvac-lint` gains no command, flag, or dependency. The existing test that
rejects a `judgement` command in the lint CLI stays green.

## Provider contract

### Wire protocol

The client MUST use this portable subset of the Jev API. The subset is the
intersection of hosted Jev 1.13.0 and DREX, which rejects some inputs Jev
accepts.

| Element | Requirement |
| --- | --- |
| Base URL | User-configured. The client appends `/v1/systemone` and `/v1/models`. |
| Auth | `Authorization: Bearer <token>` when a token is configured. The header is omitted when no token is configured. |
| Request | `state` is a JSON object built by the host. `model` is always an explicit versioned ID, never an alias such as `jev-latest`. `questions` maps host question IDs to typed questions. |
| `instructions` | A string. |
| `noul` | Optional `criteria` with string `true` and `false` descriptions. |
| `choice` | `criteria` maps option IDs to string descriptions. |
| `score` | `criteria` is an array of 2 to 10 string level descriptions. |
| Response | HTTP 200 with `model`, `answers`, and `usage`. Every requested question ID appears in `answers`. |
| Errors | 401, 402, 422, 429, and 529 are recognised. The client retries only 429 and 529, honours `Retry-After`, and never retries with a different model. |

The client normalises answers into one internal shape:

- `noul` becomes the distribution `{false: 1 - p, true: p}`. The raw scalar is kept.
- `choice` and `score` keep the provider's `probabilities` map.
- A distribution whose sum is outside `1 ± 0.01`, or that omits a requested
  option, is a provider error. The client never repairs it.

### Portable question profile

Question packs MUST fit both the default model and the Laya and Kev families,
so an override answers the same questions. The binding limits are Laya's 512 to
1,024 token context defaults, the 8,192-token native context of its ModernBERT
encoders, and Laya's documented option-budget collapse.

- At most 8 options per `choice` question and at most 10 levels per `score`.
- Serialized `state` plus the longest question fit in 1,024 tokens for sentence
  and paragraph spans, and in 4,096 tokens for document spans. Tokens are
  counted with whichever Laya or Kev tokenizer yields more.
- A server that cannot accept a 4,096-token document span reports those
  questions as `not-run`. Document-span results are reported as their own slice.
- Option IDs are lowercase ASCII identifiers. Option descriptions are one
  sentence each.
- Each question pack has a semantic version. Its SHA-256 digest is part of every
  request identity.

A pack that exceeds the profile is invalid and fails its unit test. Longer
contexts need a profile revision with its own evaluation, not a per-server
exception.

### Configuration

With no `[judge]` table, the client uses `slopvac-judge serve` on its default
socket with the default model. A `[judge]` table in `slopvac.toml` overrides it:

```toml
[judge]
endpoint = "https://api.typesafe.ai"
model = "jev-1.13.0"
token_env = "SLOPVAC_JUDGE_TOKEN"
timeout_seconds = 10
remote = "allow"
```

- `endpoint` and `model` are set together. An override without `model` is a
  configuration error, because aliases such as `jev-latest` are mutable.
- The token is read only from the environment variable that `token_env` names.
  A literal token in any configuration file is a configuration error. With no
  `token_env`, the client sends no `Authorization` header.
- `remote = "deny"` rejects every endpoint whose host is not a loopback address
  or a unix socket. The default is `deny`. Projects opt in with `allow`.
- A non-loopback endpoint MUST use `https`.
- A provider error or timeout records `not-run` for the affected questions.
  It never becomes a pass or a rejection.
- An override endpoint runs the conformance suite once per `(endpoint, model)`
  and caches the verdict. A failing endpoint is refused.

### Result record

Every answered question produces one record:

| Field | Source |
| --- | --- |
| `question_id`, `pack_version`, `pack_digest` | Host |
| `state_digest` | SHA-256 of the canonical JSON state |
| `request_digest` | SHA-256 of the canonical request body |
| `endpoint` | Scheme, host, and port only |
| `model` | Response `model` field |
| `served_revision` | Server extension header `x-slopvac-model-revision`, or `unknown` |
| `answer`, `distribution`, `raw_answer` | Response, normalised as described above |
| `latency_ms`, `usage`, `attempts` | Client |

The cache key is `(endpoint, model, served_revision, pack_digest,
state_digest, question_id)`. An `unknown` revision disables caching for that
endpoint, because a hosted model can change behind a versioned ID.

### Conformance suite

`slopvac-judge conformance <base-url> --model <id>` runs a fixture suite. It
exits non-zero when a required check fails. An endpoint is Jev-compatible for
slopvac only after every required check passes.

Required checks:

1. One `noul`, one `choice`, and one `score` question in a single request.
2. Question IDs returned exactly as sent.
3. Distribution coverage and sums for every requested option.
4. Score legend and probability keys that match the requested levels.
5. `model` and `usage` present.
6. 401 without a token when the server requires one. A 4xx status for a
   malformed request.
7. A state whose text instructs the judge to answer a fixed way. The host
   outcome is unchanged because the host never reads provider text.
8. Five identical requests. Distribution differences stay within `1e-4`.

Advisory checks print a warning and do not fail the suite, because the client
never depends on them:

- An oversized state returns a 4xx status. The client enforces the portable
  profile before sending, so it never sends an oversized state.
- The `model` field names the served model rather than echoing the request.
- `GET /v1/models` exists, and the response carries a weight revision.

The suite runs in CI against a stub server and against `slopvac-judge serve`
with the default model. Against `slopvac-judge serve`, every advisory check is
required.

## Local server

`slopvac-judge serve` serves the slopvac default model over the Jev surface. It
keeps one model resident and serves until stopped.

```sh
slopvac-judge serve --listen unix:/tmp/slopvac-judge.sock
```

- Without `--model`, it serves the default model at the revision pinned in the
  installed `slopvac-judge` release. The model must already be in the cache.
- Listens on a unix socket or a loopback port by default. A non-loopback bind
  requires `--token-env` and TLS termination in front of the server.
- Returns `x-slopvac-model-revision` with the full weight revision, and exposes
  `GET /v1/models`.
- Enforces the request-size and state-token limits of the portable profile and
  rejects oversized requests with 422.
- Persists no request payload. Logs record digests, latency, and status only.

The server loads the model through the upstream inference library for its
base: `laya` for a Laya-format encoder, or `kev` for a Kev-format LoRA with a
pointer head. The model's `manifest.json` names the format. slopvac adds only
the Jev surface, the limits, the revision header, and the logging policy.

### Secondary models

Local judging needs no secondary model:

- **SemIf direct logit readout.** Both Laya and Kev return typed distributions
  from a trained head, so a logit-readout path adds a second scoring method
  without a role. SemIf also has no Jev endpoint and no training path.
- **Qwen3-Reranker-0.6B prefilter.** Issue #162 makes the reranker conditional
  on measured candidate volume. It stays out of scope until stage 4 shows that
  judge calls, not model quality, bound latency.

## Model selection

The default model comes from the Laya and Kev families, base and post-trained.
Both families serve the Jev surface, publish weights under Apache-2.0, and ship
a training path. Every other model reaches slopvac only as a user override.

The benchmark runs local models only. Hosted Jev and DREX are not benchmark
arms. Arms run one at a time: one model is trained, served, or evaluated at
any moment, and its process stops before the next arm starts.

| Arm | Model | Params | Fits on | Use case |
| --- | --- | --- | --- | --- |
| L1 | Laya English | 421M | Laptop, CPU or Metal | Fastest arm. Fine-tuning base only. |
| L2 | Laya multilingual | 322M | Laptop, CPU or Metal | Non-English prose. Fine-tuning base only. |
| L3 | Laya typed-decisions | 421M | Laptop, CPU or Metal | Laya's own typed fine-tune. Fine-tuning base. |
| K1 | Kev 0.8B | 764M | Laptop, Apple Silicon or 8 GB GPU | Smallest Kev arm. |
| K2 | Kev 4B | 4.2B | Workstation, L40S-class GPU or 32 GB Mac | Mid tier. |
| K3 | Kev 9B | 8.0B | Workstation, 48 GB GPU or 48 GB Mac | Largest arm that runs on a Mac. |

Kev 27B needs one 80 GB GPU in bf16. The benchmark account has no SageMaker
quota for an 80 GB instance, so K4 is deferred. Adding it needs a quota for
`ml.p5.4xlarge` or an equivalent instance.

Every arm runs twice: zero-shot and post-trained on the corpus `train` split.
The benchmark report gives, for each of the 12 runs, the metrics in
[Harness](#harness), disk size, peak memory, load time, p50 and p95 latency, and
the smallest reference hardware it fits on:

- Laptop: Apple M-series with 16 GB.
- Workstation: one 24 to 48 GB GPU, or Apple M-series with 32 to 48 GB.
- CI: one GPU behind an authenticated endpoint.

The maintainer selects the default from that report. The selected model must
pass every gate in [Evaluation gates](#evaluation-gates).

## Evaluation

### Corpus

The corpus pairs AI-free human documents with model-generated documents on the
same briefs. Human versus generated is provenance metadata. It is never a
label, a question, or a training target.

**Human documents.** Only public text whose content revision predates
2022-11-30 is admitted. Each document is pinned to an immutable revision: a
repository commit and path, a Wikipedia `oldid`, or a data-dump post ID. The
sources cover the five slopvac genres:

| Genre | Sources |
| --- | --- |
| `consumer` | READMEs and user guides from permissively licensed repositories. Python, Django, PostgreSQL, Rust, Kubernetes, and MDN documentation at 2021 tags. |
| `reference` | API references, man pages, RFCs, and language references. |
| `internal` | PEPs, Kubernetes KEPs, Rust RFCs, and project design documents. |
| `change-comms` | Release notes, changelogs, and migration guides from releases before 2022. |
| `informal` | Wikipedia articles across all topics, and Stack Exchange answers from the data dump. |

The repository stores pointers only: `sources/human.jsonl` records the
locator, licence, revision date, word count, and SHA-256 of the normalised
text. The text lives in a private S3 bucket and a local cache. Near-duplicates
at a shingle Jaccard similarity of 0.8 or more are removed.

**Generated documents.** Bedrock batch inference produces them in two stages:

1. One model writes a brief for each human document. The brief states the
   genre, audience, purpose, requirements, an abstract section outline, and the
   target length. A brief that shares any 8-gram with its source is rejected.
2. Two generation models write a document from the brief alone. They never see
   the source. A generated document that shares any 8-gram with the source is
   dropped.

Generation models span vendors and capability tiers: Anthropic, Amazon, Meta,
Mistral, OpenAI open-weight, Qwen, DeepSeek, Google, and others that support
Bedrock batch inference. The roster records each model's vendor and tier. No
model produces more than 12% of the generated documents.

**Items.** An item is a span, a question from the question pack, and a label.
Spans come at three granularities, recorded on every item and reported as
separate slices:

| Granularity | Span | Target share |
| --- | --- | --- |
| Sentence | One sentence | 30% |
| Paragraph | One paragraph, with the section heading and neighbouring paragraphs as context | 45% |
| Document | The whole unit, or its longest leading run of whole sections within the cap, marked `truncated` | 25% |

Seeded defects and finding offsets are expressed relative to the span at each
granularity. Items serve the two roles:

- **Finding confirmation (lint rules).** slopvac lints every corpus document.
  Each finding becomes one item: the paragraph that contains it, the rule ID and
  message, and the finding's offsets. The question asks whether the finding is a
  `real-defect`, a `false-positive`, or `insufficient-context`. Lint rules are
  never asked as open-ended detection questions.
- **Semantic detection (judgement rules).** Each of the 65 judgement rules at
  commit `49a91f2b^` asks its own question of a paragraph. The answer is `noul`,
  with the rule's exemplars as criteria.

| Source | Role | Label origin | Splits |
| --- | --- | --- | --- |
| Lint findings on human and generated documents | Confirmation | Teacher panel for `train`. Two human adjudicators for `test` | `train`, `test` |
| Lint-rule `bad` examples seeded into human paragraphs, linted in place | Confirmation | Construction: `real-defect` | All splits |
| Judgement-rule exemplars seeded into human paragraphs, with the unseeded paragraph as control | Detection | Construction | All splits |
| Judgement rules asked of unseeded human and generated paragraphs | Detection | Teacher panel for `train`. Two human adjudicators for `test` | `train`, `test` |
| gold-v1 seeded and control rows at commit `49a91f2b^` | Detection | Construction | `test` |

The teacher panel is three Bedrock models from different vendors. An item enters
`train` only when at least two panel models agree. Teacher labels never enter
`calibration` or `test`.

Each item carries the document genre in its state. One model serves all genres.
Calibration temperatures and decision thresholds are fitted per genre, and
every metric is reported per genre. A per-genre Kev LoRA adapter is trained only
when one genre trails the others by more than a gate margin.

Splits are grouped by document family: a human document and the documents
generated from its brief share one split. About 20% of lint rules and 20% of
judgement rules are held out. Their items appear only in `test`, which reports
seen-rule and unseen-rule slices separately. The `train`, `dev`, `calibration`, and `test` manifests are
frozen with SHA-256 digests before any arm runs on `test`.

`test` and `calibration` hold every constructed and gold-v1 item in their
documents. Model-derived items there need human labels, so each split keeps a
stratified sample for two adjudicators: 600 items in `test` and 300 in
`calibration`. The sample is stratified by role, rule category, genre,
granularity, and provenance. Model-derived items in those documents outside the
sample are dropped from every split. The report gives Cohen's kappa.

### Harness

`slopvac-judge eval --arm <id> --split <name>` runs one arm and writes a JSONL
file of result records plus a summary. Each run:

- sends every question twice with option order reversed;
- repeats a 5% sample five times to measure provider noise;
- fits per-question, per-genre temperature scaling on `calibration` and reports
  raw and calibrated metrics separately;
- records hardware, runtime version, model revision, pack digest, and split
  digest.

Metrics per question type:

- `noul`: accuracy, balanced accuracy with a 95% bootstrap interval over rules,
  AUROC, Brier, and ECE.
- `choice`: accuracy, macro-F1, confusion matrix, and order-swap agreement.
- `score`: MAE and quadratic-weighted kappa.

Each summary also reports accuracy by item type (defect, clean counterpart,
cross-rule negative), per genre, and per provenance. It reports false-positive
incidence per 1,000 words on human documents, abstention coverage, and latency.

### Evaluation gates

A model passes when, on `test`:

1. It passes the conformance suite through `slopvac-judge serve`.
2. Balanced accuracy on `noul` beats the best zero-shot arm in a paired
   bootstrap over rules, at the 95% level.
3. Accuracy on defect items and on clean items are both at least 0.8.
4. Order-swap agreement is at least 95%.
5. Calibrated ECE is at most 0.05 on each question type.
6. No genre trails the overall balanced accuracy by more than 5 percentage
   points.

Any threshold change requires a spec revision recorded before a model runs on
`test`.

## Post-training

### Bases

- **Laya.** A CPU-servable encoder of 421M parameters with a typed head, one
  forward pass for several questions, and temperature calibration. Its
  published fine-tune rises from 0.362 to 0.766 accuracy on 2,000 typed
  decisions.
- **Kev.** A rank-16 LoRA and a pointer head on Qwen3.5 bases. Post-training
  starts from the released Kev checkpoint through `kev.train --init_from`, the
  path Kev documents for user fine-tunes.

Laya's "Honest limits" section constrains its use:

| Laya limit | Spec response |
| --- | --- |
| Base checkpoints are near chance on typed decisions zero-shot | Laya arms ship only post-trained. |
| Negation defeats semantic choice labels | Constructed negation pairs are reported per rule. |
| A 77-option question collapses to 0.425 accuracy against Jev's 0.870 | The portable profile caps questions at 8 options. |
| Context defaults are 512 to 1,024 tokens | The portable profile caps state plus question at 1,024 tokens. |
| Confidence thresholds are caller policy, not correctness | The host fits thresholds on `calibration` and never uses a vendor default. |
| The notebook calibrates on training items | The pipeline calibrates on the separate `calibration` split. |

### Compute

Laya arms and Kev 0.8B train on the maintainer's Apple Silicon workstation.
Kev 4B and 9B train as SageMaker training jobs on `ml.g6e` instances with one
L40S GPU of 48 GB, in `us-east-1` under the `sjors+ig-genai-Admin` account.
Each job sets a maximum runtime, writes its outputs to the corpus S3 bucket, and
terminates when training ends. Jobs run one at a time. The benchmark's total
SageMaker and Bedrock spend is capped at USD 500, recorded in the cost ledger.

### Rebuild pipeline

`judge-rebuild.yml` is a manually triggered and scheduled GitHub Actions
workflow. It submits SageMaker training jobs through GitHub OIDC and an IAM role
scoped to the training bucket. Each stage writes its outputs under
`build/<run-id>/` and fails the run on error.

1. **Freeze.** Resolve the base model's full 40-character revision. Read the
   split manifests and verify their digests. Record the pack version and digest.
2. **Train.** Train with the pinned framework version, a fixed hyperparameter
   config, and three seeds. Hyperparameters are selected on `dev` only.
3. **Calibrate.** Fit per-question, per-genre temperatures on `calibration`.
4. **Evaluate.** Run the harness on `test` for the new build, the zero-shot
   base, and the latest published release.
5. **Gate.** Apply the evaluation gates. The build also fails if any gate metric
   regresses against the latest published release beyond the gate margins.
6. **Package.** Write weights as `safetensors`, the calibration file, the
   question pack, the model card, `LICENSE` files for the base and the adapter,
   and `manifest.json`.
7. **Sign.** Compute SHA-256 for every file into `manifest.json`. Sign the
   manifest with Sigstore keyless signing from the workflow's OIDC identity.
8. **Publish.** Push to the Hugging Face repository as a new commit, then tag it
   `v<pack-major>.<build>`. A maintainer approves publication in a protected
   GitHub environment after reading the gate report.

`manifest.json` records the run ID, base repository and revision, adapter
method and config, framework and Python versions, hardware and dtype, seeds,
split digests, pack digest, calibration temperatures, gate metrics, SageMaker
job ARN, and file digests.

A rebuild runs when any of these change: the base revision, the question pack,
a split manifest, or the training framework's minor version. The scheduled run
executes monthly and rebuilds only when an input digest differs from the
latest release. A rerun with identical inputs MUST produce identical host
outcomes on `test`. Byte-identical probabilities are not required, and the
accepted numeric tolerance is `1e-3` per probability.

### Distribution

Post-trained models are published on the Hugging Face Hub as
`srobroek/slopvac-judge-<family>-<size>`, for example
`srobroek/slopvac-judge-kev-4b`. Laya and Kev both load from the Hub, and the
Hub keeps every revision addressable by commit. Kev adapters stay under their
Qwen3.5 Apache-2.0 notices, and Laya checkpoints under Laya's Apache-2.0 licence.
The corpus is not published, because the human text keeps its source licences
and the S3 bucket is private.

Users download a model with:

```sh
slopvac-judge pull slopvac-judge-kev-4b --revision v1.3
```

`pull` resolves the tag to a full commit, downloads only `*.safetensors`,
`*.json`, `*.md`, and `LICENSE*` files, verifies the Sigstore signature on
`manifest.json`, and verifies every file digest. A verification failure deletes
the partial download and exits non-zero. Models are cached under
`$XDG_CACHE_HOME/slopvac-judge/models/<repo>/<commit>/`. `serve` runs offline
against a cached model and never downloads implicitly.

The model card states the intended use and prohibits authorship classification.
It names the base model and revision, and the provenance and licences of the
training data. It reports gate metrics against the zero-shot base, per-genre
results, known failure modes, and serving instructions.

## Delivery

Each stage is one bead and one pull request against `feat/local-judging`,
created from a worktree branched off that branch. The feature branch merges to
`main` only after stage 5.

| Stage | Deliverable | Acceptance |
| --- | --- | --- |
| 1. Pilot | Zero-shot and post-trained runs of every arm on lint-rule example pairs | Report with per-arm metrics and hardware fit. |
| 2. Corpus | Human pointers, briefs, generated documents, paragraph items for both roles, teacher labels, frozen splits | Counts per genre, vendor, and tier. Item counts per role, rule, and label origin. Leak and dedup counts. Split digests committed. |
| 3. Benchmark | Zero-shot and post-trained runs of every arm on the corpus, serially | Full metric report per run. Maintainer selects the default. |
| 4. Contract and server | `slopvac-judge` package, Jev client, config, conformance suite, `serve`, `pull` | Conformance passes against `serve` with the default model, every advisory check included. Lint CLI tests unchanged. |
| 5. Release | Rebuild workflow, signed Hub release of the default model | `pull` verifies the release on a clean machine, and the gates pass. |

Finding validation stays evaluation-only through stage 5. The report states
four validation states separately: supported, rejected, uncertain, and not run.
