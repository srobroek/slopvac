# Evidence: local typed judging

> **Status:** dated evidence for [local-judging.md](local-judging.md). All facts
> were observed on 2026-09-28 unless a row states another date. Every figure
> below is self-reported by its publisher. No row is an independent
> replication or a slopvac result.

## Wire protocol sources

| Source | Version observed | Facts the spec uses |
| --- | --- | --- |
| [TypeSafe OpenAPI](https://api.typesafe.ai/openapi.json), [API reference](https://docs.typesafe.ai/api.md) | OpenAPI 3.1.0, `info.version` 0.2.0 | `POST /v1/systemone` and `GET /v1/models`. Bearer auth. `noul` returns P(true). `choice` allows up to 255 options. `score` allows 2 to 10 levels. Errors 401, 422, 429, 529. No streaming, no batch of states, no token logprobs. |
| [TypeSafe models](https://docs.typesafe.ai/models.md) | Jev 1.13, ID `jev-1.13.0` | 64K tokens per request, with state plus the longest question at most 32K. `jev-latest` and `jev-preview` are mutable aliases. The response `model` field reports the versioned ID. No weights revision in the response. $0.042 per million input tokens. |
| [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md) | Reviewed 2026-09-17 | Weak on counting and numeric precision. Sensitive to irrelevant large state and indirection. |
| [TypeSafe privacy policy](https://typesafe.ai/legal/privacy-policy), [DPA](https://typesafe.ai/legal/data-processing) | Updated 2025-11-19 and 2026-04-24 | No training on inputs. No fixed payload deletion period. Zero data retention for enterprise customers only. |
| [DREX API docs](https://drex.nace.ai/docs), [DREX OpenAPI](https://drex.nace.ai/openapi.json) | API 1.0.0. Models `drex-v1.0` and `drex-v1.1` | States Jev wire compatibility. Rejects `jev-latest`. Requires string `instructions`, string criteria descriptions, and string score levels. Adds 402. 512 questions per request. State plus longest question at most 32,768 tokens. Body at most 262,144 bytes. |
| [DREX service terms](https://drex.nace.ai/terms) | Updated 2026-09-25 | Request content kept in operational logs for at most 30 days. Not used for training. |
| [DREX product page](https://www.nace.ai/drex) | Drex 1.1 | Under 10B parameters. Proprietary. No public weights. |

## Jev-native local servers

| Project | Commit observed | Facts the spec uses |
| --- | --- | --- |
| [Kev](https://github.com/jaredpalmer/kev/tree/3e1cd3bb588a388a06827443380befece23e68c7) | `3e1cd3b`, 2026-09-28 | Serves the TypeSafe System One API. Qwen3.5 0.8B, 4B, and 9B and Qwen3.8-27B bases with a rank-16 LoRA and a pointer head. `noul`, `choice`, and `score` with 1 to 255 options. New-source accuracy dev/test: 9B 0.822/0.852, 27B 0.848/0.896. Brier dev/test: 9B 0.286/0.237, 27B 0.236/0.164. Ships `kev.train`, `kev.benchmark`, and `kev.serve`. Apache-2.0. |
| [Laya](https://github.com/NandhaKishorM/laya/tree/9d955671415fc19f069b9cc998928075c1f255ec) | `9d95567`, release 0.3.21, 2026-09-27 | Serves `POST /v1/systemone`. Encoder with a typed decision head: English ModernBERT-large 421M, multilingual mmBERT-base 322M. Typed-decisions fine-tune: accuracy 0.766 against 0.362 for the base on 2,000 decisions. Reported 33 ms for one question on a T4. Context defaults 512 to 1,024 tokens. Apache-2.0. |

Laya's "Honest limits" section, at the commit above, states:

- The base checkpoints are near chance on typed decisions zero-shot. Laya is a
  fast base to specialise, not a zero-shot decision engine.
- Negation defeats semantic choice labels. The section lists confident
  wrong cancellation decisions.
- A 77-option question collapses to 0.425 accuracy against Jev's 0.870 at the
  default head token budget. The section recommends shortlisting options.
- Confidence thresholds are caller policy rather than correctness.

## Secondary model review

| Project | Commit observed | Facts the spec uses |
| --- | --- | --- |
| [SemIf-OpenJev](https://github.com/TheoLeeCJ/SemIf-OpenJev/tree/23cf1f39fc9534fe81437200959b6dfc7106e45a) | `23cf1f3`, 2026-09-23 | Direct readout of next-token logits over 2 to 16 one-token answer slots. No Jev HTTP endpoint and no training tooling observed. MIT. |
| [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | Card observed 2026-09-28 | Apache-2.0 reranker. Issue #162 makes it conditional on measured candidate volume. |

## Kev 27B hardware

Kev's README at the commit above states that Kev 27B serves in bf16 only, with
55 GB of weights, and needs an 80 GB GPU with no Mac path. On 2026-09-28, account
536697262379 had a SageMaker training-job quota of 0 for `ml.p4d`, `ml.p4de`,
`ml.p5`, and `ml.p5.4xlarge` in `us-east-1` and `us-west-2`. It had a quota of 1
for `ml.g6e.xlarge` through `ml.g6e.16xlarge` in `us-east-1`.

## Distribution and calibration references

| Source | Fact the spec uses |
| --- | --- |
| [Hugging Face download guide](https://huggingface.co/docs/huggingface_hub/guides/download) | `snapshot_download` accepts a full commit hash as `revision` and supports `allow_patterns`. |
| [Hugging Face pickle security](https://huggingface.co/docs/hub/security-pickle) | Pickle files can execute code on load. `safetensors` avoids that. |
| [Guo et al. 2017](https://arxiv.org/abs/1706.04599) | Temperature scaling fit on held-out data reduces calibration error. |
| [JudgeBench](https://arxiv.org/html/2410.12784) | Evaluates each pair twice with order swapped and counts inconsistent decisions as wrong. |

## Existing slopvac items

| Commit | Fact the spec uses |
| --- | --- |
| `49a91f2b^` `tests/fixtures/judgement/gold/gold-v1.jsonl` | 98 seeded defect rows across 65 judgement rules, and 100 control rows. Each seeded row names its `defect_span`. |
| `49a91f2b^` rule YAML | 65 rules of kind `judgement`, each with a question and exemplars. |
| `HEAD` rule YAML | 260 `bad` and `good` example pairs across 158 lint rules. |
