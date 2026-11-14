# 0001. Slopvac 3.0 architecture

- Status: accepted, 2026-11-14. Every decision holds for 3.0 except decision 2, which waits on the `harper-brill` parity spike (`slopvac-8l4.3.10`, running). Removing Vale proceeds only if that spike passes its go or no-go threshold.
- Deciders: slopvac maintainers
- Tracking: bead `slopvac-8l4.2.1`, epic `slopvac-8l4`
- Detail: [Slopvac 3.0 plan](slopvac-3.md)

## Context

Slopvac 2.x is a Python package. It generates Vale configuration, runs Vale, and scores the output. That design has three limits:

- Matching is split. 2.x has native rule types in Python, and Vale runs the rest. Slopvac filters Vale findings and supplies their metadata, suppression, severity, replacements, and provenance. Each new match type, provenance field, or context tag must work in both engines.
- An ordinary Vale-enabled lint run starts a Python process and a Vale subprocess. `prime` does not call Vale, and `--no-vale` or a disabled config skips it.
- Users install two tools, and the Vale version affects results.

A documentation trial (GitHub issues #252 to #257) also found rule defects that need fixes. No 2.x release ships, so those fixes and a public data and plugin API land together in 3.0.0.

Labels in the experiments below come from one annotator, and several samples are small (40 to 92 documents). Treat the figures as estimates for those corpora.

## Decision drivers

- Slopvac owns matching, config, and output, so findings can carry provenance, spans, and contexts.
- One self-contained binary with no runtime to install, and `uvx slopvac` must keep working.
- A small dependency and binary footprint.
- A plugin boundary that a third party can use without running inside the slopvac process.
- Install and update without prompts, so agents and CI behave like people.
- Reference material must not drift from the code.

## Decisions

### 1. Rust Cargo workspace

Rewrite slopvac in Rust as a Cargo workspace. The Python 2.x code stays the reference implementation until the golden suite passes.

- Evidence: the regex spike (`slopvac-8l4.2.15`) ran PCRE2 with JIT at 1.7 to 1.8 seconds on one thread and 0.2 seconds on 14 threads, against 7.7 to 9.1 seconds for Python. This measures matcher throughput for 143 patterns over 8,496 texts. It does not measure whole-run time.
- Rejected: keep Python and Vale. It keeps all three limits above.

### 2. Remove Vale entirely

Slopvac matches every rule itself. The README keeps an "Inspired by Vale" section that thanks the project.

- Evidence: the PCRE2 spike matched Python on 142 of 143 patterns (decision 4), which shows regex rule patterns run without Vale's engine. It does not cover rules that use part-of-speech tags. The `harper-brill` parity spike (`slopvac-8l4.3.10`) covers those and gates this decision.
- Rejected: keep Vale as an optional engine. It would keep two code paths and two behaviors to test.

### 3. No async runtime

Use rayon for CPU work. Use dedicated threads for waiting work, joined by crossbeam-channel, with `select!` and deadlines for timeouts. Use ureq for HTTP. Write the OCI client by hand.

- Evidence (`slopvac-8l4.2.17`):

| Option | Code | Dependencies | Size added |
|---|---|---|---|
| Hand-rolled OCI client on ureq | about 250 lines | 42 | 1.67 MB stripped |
| `oci-client` on tokio | 71 lines | 180 | 5.4 MB |
| Plugin host on threads and crossbeam | 49 lines | 7 | not measured |
| Plugin host on smol | 26 lines | 47 | not measured |

- The ureq client did the anonymous token flow and pulled manifests and blobs with sha256 checks from `ghcr.io`. Push was tested on a local registry only, because GHCR push needs `write:packages`.
- Rejected: tokio with `oci-client` (three times the size, 180 dependencies).
- Rejected: smol, which saved 23 lines but added 40 dependencies, and HTTP stayed blocking.

### 4. PCRE2 for regex

- Evidence (`slopvac-8l4.2.15`): 143 compiled patterns over 8,496 texts. After two `\u` and `\U` escapes were rewritten, PCRE2 with JIT matched Python on 142 patterns with 0 mismatches. `prose-craft.future-tense` failed on an unbounded lookbehind. `fancy-regex` compiled 143 patterns, with 1 backtrack-limit error after hoisting.
- Untested: `$` before a trailing newline, exotic case folding, and unusual `\s` whitespace.
- Rejected: `fancy-regex`, for the backtrack-limit error.
- Rejected: the `regex` crate alone, because it lacks lookaround. It stays optional for patterns that need none.
- Follow-up: bound the `future-tense` lookbehind. Pin PCRE2 10.43 or later and test JIT and non-JIT builds.

### 5. Lexical similarity only

- Evidence (`slopvac-8l4.2.16`): 40 excerpts of 22 sentences, three rewrite replicates, and paired bootstrap over documents.
  - Dropped-fact F1: lexical 0.943, 0.915, 0.802 against model2vec 0.798, 0.733, 0.702. The difference of 0.10 to 0.18 is significant.
  - Claim grouping ARI: 0.300 against 0.194, significant.
  - PAWS-Wiki AUC: 0.687 against 0.485.
  - A literal and negation diff caught 73 to 94% of planted changes, with a false-positive rate of about 10 to 20% on faithful rewrites.
- Limits: gold alignment came from the rewriting model, and the edits were synthetic.
- Rejected: model2vec. It scored lower on this corpus, so 3.0 ships lexical similarity only. A model2vec plugin is on the backlog.

### 6. Hand-rolled config layer stack with provenance

Build the stack on `toml_edit`, `saphyr`, serde, and `schemars`. Record file, line, and column for every contribution.

- Evidence (`slopvac-8l4.4.1`): both prototypes resolved 10,000 files in under 9 µs per file with identical values.
  - `schematic` 0.20.12 has no per-list-element provenance, gives YAML errors without spans, reports the first error only, and overflows the stack on a cyclic `extends`. It adds 54 crates and 1.64 MB, and it was still pre-1.0.
  - The layer stack is about 850 lines. `schematic` would save about 25 to 30% of the code.
- Rejected: `schematic`.

### 7. Generic front-matter crate with value spans

Write `frontmatter-spans` for YAML, TOML, and JSON, with per-value spans and serde support.

- Evidence: among the crates evaluated, none gave front matter with value spans (plan, "Rust crate research").
- Rejected: an existing front-matter crate plus a second parse to recover positions.

### 8. JSON-RPC 2.0 over stdio for code plugins

Framing follows LSP. An `initialize` handshake exchanges capabilities. A Python SDK and a conformance suite ship with the protocol.

- Evidence: the plugin host prototype in `slopvac-8l4.2.17` ran on threads and crossbeam (49 lines, 7 dependencies), which shows the transport needs no async runtime.
- Rejected: in-process dynamic libraries and WASM. Design reasoning, not measured: a subprocess keeps plugin crashes and memory use outside the host. WASM is on the backlog.

### 9. OCI artifacts, minisign, and mise-style trust

Distribute packs and plugins as OCI artifacts on GHCR or any registry. Ship minisign signatures as manifest layers, and verify them with `minisign-verify`. The host loads a code plugin only after `slopvac plugins trust` records its content hash, and it prints that command for an untrusted plugin. No code path prompts, so an agent or CI job cannot answer a prompt on a user's behalf.

- Evidence: GHCR returns 404 for the referrers API, so signatures cannot attach as referrers. The tag-schema fallback works (`slopvac-8l4.2.17`).
- Rejected: Sigstore verification in 3.0, which moves to the backlog.
- Rejected: prompting for trust, because an agent or CI job could answer it.
- Follow-up: a threat model and independent review must pass before the plugin host and OCI client close.

### 10. Error and diagnostic rendering: thiserror, anyhow, annotate-snippets

`thiserror` in libraries, `anyhow` in the binary, and `annotate-snippets` to render source diagnostics. This is the standard Rust split.

### 11. CLI and editor: clap and lsp-server

`clap` with `clap_complete` and `clap_mangen` for the CLI. `lsp-server` for the language server, which fits the no-async decision.

### 12. Distribution: cargo-dist, Homebrew tap, and maturin wheels

cargo-dist builds archives and installers and feeds a Homebrew tap (`srobroek/homebrew-tap`). maturin builds binary wheels, so `uvx slopvac` stays the default install. Each release also carries GitHub attestations, an SBOM, and an auditable binary.

### 13. Dependabot only

Remove Renovate and use Dependabot for cargo and workflow updates. Patch and security updates merge automatically through `dependabot/fetch-metadata`. This landed for 2.x in PR #260, together with a weekly check of the mise and Vale pins. The Vale pin check ends when Vale is removed.

### 14. reviewdog for PR reporting

The GitHub Action uses reviewdog with `reporter: auto`, or uploads SARIF. Its own annotation code is removed. The 2.x repository already reports lint findings on pull requests with reviewdog (PR #262).

- Evidence (`slopvac-8l4.2.18`): reviewdog 0.21.3 parsed slopvac rdjsonl (151 diagnostics, 8 with replacements) and SARIF locally. The GitHub reporters were not tested.
- Also: rumdl 0.3.4 reported 7,806 findings on the corpus with defaults. About 95% were style or flavor noise (MD013 3,381, MD033 1,712, MD051 689). It overlaps slopvac only on heading hierarchy, and partly on dashes and bold. The docs mention rumdl and nothing integrates it.

### 15. Output formats and LSP

Slopvac emits these formats:

- `text`, `json`, and `markdown`;
- `sarif`, `rdjsonl`, and `codeclimate`;
- `junit`, `checkstyle`, and `html`;
- LSP diagnostics.

Each rule has a stable documentation page that formats link to. The formats follow what reviewdog, CI systems, and editors read.

### 16. Generated reference material

Generate every reference document from code and data. CI fails when a generated file is stale. The generated set:

- JSON Schemas from Rust types;
- one page per rule, style, genre, and pack;
- the plugin protocol reference;
- Rust API docs.

Rejected: hand-written reference pages, which drift from the code.

### 17. No 2.x releases

No 2.18.x or 2.19 release ships. Rule-data fixes land on `main` in the Python reference, and the golden suite records the fixed behavior. Fixes that need Rust get 3.0 beads.

- Evidence: the trial page reproduced the reporter's scores (`slopvac-8l4.2.13`). "Before" is the Mecatl permissions page at its merge base, and "after" is the page with the trial edits. Results as findings, errors, score, gate:
  - Default config before: 150, 1, 85.4, fail.
  - Default config after: 83, 0, 91.8, pass.
  - Trial config before: 80, 1, 92.3, fail.
  - Trial config after: 35, 0, 97.0, pass.
- The single error is `negative-inventory-core` on a constraint phrased with the words "excluded" and "from".
- The detector prototype on 92 docs (`slopvac-8l4.2.14`) gave baseline precision of history-narration 5 of 175, `negative-inventory-core` 0 of 6, and title-case 225 of 280. The `requirement` tagger touched 9% of sentences and lost no observed true positive.

### 18. Full scope in 3.0.0

Confirmed 2026-11-14. An adversarial review proposed a smaller 3.0.0 with new platforms in 3.1. The decision keeps every programme bead outside the backlog in 3.0.0, under the `release:3.0.0` label. A release-readiness gate bead covers the whole scope.

### 19. Public data contracts

Rust types generate versioned JSON Schemas, published per API major version.

- IDs are namespaced as `<pack>:<id>`, with built-ins in `core`.
- Rules use a typed `match:` block, and `tiers` is removed.
- Profiles set gate thresholds and a severity shift only.
- Styles are ordered presets with `extends` and declared `conflicts`.
- Genres are data files with detection signals.
- Lint JSON v3 adds these fields:
  - `schema_version` and `notices`;
  - per document, `genre` and config sources;
  - per finding, `pack`, `contexts`, and `end_line`.

Evidence: none from a spike. This follows the 2.x pydantic schema and the trial feedback. Detail: plan section "Data and API schema".

### 20. Config precedence, nearest config, and front matter

Layer order, lowest to highest priority:

1. core defaults;
2. styles;
3. the genre chain;
4. `extends`;
5. project config;
6. matching `[[genres]]` and `[[overrides]]`;
7. front matter;
8. inline directives;
9. CLI flags.

The nearest config to each file applies. Front matter is an allowed-fields layer under a `slopvac:` key. `--explain-config` prints the layer, file, and line of each value.

- Evidence: the layer-stack spike in decision 6 shows that every contribution can carry its file, line, and column. The layer order itself comes from the plan.
- Detail: plan sections "Data and API schema" and "Layer order".

### 21. Context tags

Adopt `requirement`, `enforced-invariant`, and `change-note` contexts. Security context is declared, not inferred.

- Evidence (`slopvac-8l4.2.14`; single annotator, 92 docs): the `requirement` tagger touched 9% of sentences and lost no observed true positive. The sentence-level `enforced-invariant` tagger touched 9% and lost none. Extended change-note detection cleared all 150 release-note false positives of `history-narration`. A lexical security tagger marked 40% of security-doc sentences, which is too broad to infer.
- Rejected: inferring security context lexically.

### 22. Extractors

`pulldown-cmark` for Markdown, `markdown-rs` for MDX, `html5ever` for HTML, and `tree-sitter` for code comments. RST stays in core through a bundled docutils-to-HTML adapter. The plan does not say how the adapter is bundled. Because docutils is Python, RST is the one format that may need a Python runtime. AsciiDoc is an experimental first-party extractor plugin through asciidoctor.

- Evidence: none from a spike. AsciiDoc is new, so it ships as experimental.
- Detail: plan section "Language and runtime" table.

### 23. Agent review

Review types are `mechanical`, `update`, and `rewrite`. Fact checking covers changed claims only, and its scope scales with the change. Fact preservation uses lexical alignment and a literal diff (decision 5). The reviewer must use a different model from the author.

- Evidence: decision 5 for alignment. Nothing measures the same-model restriction.
- Detail: plan section "Agents".

### 24. Release and quality gates

Release candidates and stable releases follow these rules:

- A release candidate is an `rc/vX.Y.Z-rc.N` tag cut on demand.
- A provenance gate must pass before a stable release.
- In 2.x, candidates build from each update to the release PR branch, wait for approval in the `pypi` environment, and get no tag or changelog entry (`CONTRIBUTING.md`, "Stable releases and release candidates"). The 3.0 plan changes this to an on-demand tag.

Quality gates:

- The accuracy gate measures recall on seeded and adjudicated positives, false-positive rates on clean controls, and a held-out set, as well as precision.
- A precision ratchet blocks rule changes that lower precision beyond the noise.
- A position contract fixes byte spans, line and column bases, and per-format conversions, including LSP UTF-16.

The golden suite runs in three modes:

- reference parity, pinned to a Python commit, Vale 3.24, and corpus hashes;
- 3.0 default-policy tests with reviewed deltas;
- migration-preservation tests.

Evidence: none from a spike. These gates came from the adversarial plan review. Detail: plan sections "Distribution and release", "Evals", and "Release gate and risks".

## Consequences

Good:

- One binary with no Vale and no Python runtime for Markdown, MDX, and HTML (RST may need Python, see decision 22), and a data and plugin API that third parties can build on.
- Every finding can name the layer, file, line, and column that produced its settings.

Bad or risky:

- The hand-rolled OCI client adds 42 dependencies and 1.67 MB stripped. No bead measures the size of the full binary.
- The rewrite is large, and the full scope raises the release risk. The golden suite, a compatibility matrix, and the readiness gate exist to manage it.
- PCRE2 is a C dependency. Its build must work on Windows, macOS, glibc, and musl.
- `harper-brill` must match Vale's POS tags well enough per rule. That spike is a go or no-go gate, and no result is recorded yet.
- The plugin host and OCI client carry security risk. The threat model and independent review gate them.
- No spike numbers back decisions 7, 10 to 13, 15, 16, 19, and 22 to 24. Decisions 8 and 9 have spikes for the transport and the registry, but none for the protocol or the trust model. These decisions rest on convention and the plan.
- Users on 2.x must migrate. `slopvac migrate` and a one-minor compatibility mode cover this.

## Evidence

| Bead | Subject |
|---|---|
| `slopvac-8l4.2.13` | Stacklok page, before and after |
| `slopvac-8l4.2.14` | Detector prototype on 92 public docs |
| `slopvac-8l4.2.15` | Rust regex parity |
| `slopvac-8l4.2.16` | Lexical against model2vec |
| `slopvac-8l4.2.17` | OCI client and async runtime |
| `slopvac-8l4.2.18` | rumdl and reviewdog |
| `slopvac-8l4.4.1` | `schematic` against the layer stack |
| `slopvac-8l4.10.1` | Diagram over-explanation signals. Non-decisional: it informs experimental diagram rules only. |

The scratch data behind these runs is not in the repository. The beads hold the method and results.
