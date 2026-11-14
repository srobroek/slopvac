# 0001. Slopvac 3.0 architecture

- Status: accepted, 2026-11-14
- Deciders: slopvac maintainers
- Tracking: bead `slopvac-8l4.2.1`, epic `slopvac-8l4`
- Detail: [Slopvac 3.0 plan](slopvac-3.md)

## Context

Slopvac 2.x is a Python package. It generates Vale configuration, runs Vale, and scores the output. That design has three limits:

- Vale owns matching, so every new match type, provenance field, or context tag needs work in a second tool.
- Every run starts a Python process and a Vale subprocess. The regex spike measured Python at 7.7 to 9.1 seconds for 143 patterns over 8,496 texts on one thread.
- Users install two tools, and the Vale version affects results.

A documentation trial (GitHub issues #252 to #257) also found rule defects that need fixes. No 2.x release ships, so those fixes and a public data and plugin API land together in 3.0.0. This record covers the architecture decisions. The plan holds the order of work.

Labels in the experiments below come from one annotator, and several samples are small. Treat the figures as estimates for those corpora.

## Decision drivers

- Matching, config, and output must be ours, so findings can carry provenance, spans, and contexts.
- One self-contained binary with no runtime to install, and `uvx slopvac` must keep working.
- A small dependency and binary footprint.
- A plugin boundary that a third party can use without trusting our process.
- Install and update without prompts, so agents and CI behave the same as people.
- Reference material must not drift from the code.

## Decisions

Each decision is final for 3.0. The considered options list what was rejected.

### 1. Rust Cargo workspace

Rewrite slopvac in Rust as a Cargo workspace. The Python 2.x code stays the reference implementation until the golden suite passes.

- Evidence: the regex spike (`slopvac-8l4.2.15`) ran PCRE2 with JIT at 1.7 to 1.8 seconds on one thread and 0.2 seconds on 14 threads, against 7.7 to 9.1 seconds for Python.
- Rejected: keep Python and Vale. It keeps both limits above. No spike measured a Python-only rewrite of the engine, so this record has no numbers for it.

### 2. Remove Vale entirely

Slopvac matches every rule itself. The README keeps an "Inspired by Vale" section that thanks the project.

- Evidence: the PCRE2 spike matched Python on 142 of 143 patterns (decision 4), which shows rule patterns run without Vale's engine. The POS-tag parity spike for `harper-brill` is still open and gates this decision (see Consequences).
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
- Rejected: tokio with `oci-client` (three times the size, 180 dependencies). Rejected: smol, which saved 23 lines but added 40 dependencies, and HTTP stayed blocking.

### 4. PCRE2 for regex

- Evidence (`slopvac-8l4.2.15`): 143 compiled patterns over 8,496 texts. After two `\u` and `\U` escapes were rewritten, PCRE2 with JIT matched Python on 142 patterns with 0 mismatches. `prose-craft.future-tense` failed on an unbounded lookbehind. `fancy-regex` compiled 143 patterns, with 1 backtrack-limit error after hoisting.
- Untested: `$` before a trailing newline, exotic case folding, and unusual `\s` whitespace.
- Rejected: `fancy-regex`, for the backtrack-limit error and because it has no JIT. Rejected: the `regex` crate alone, because it lacks lookaround. It stays optional for patterns that need none.
- Follow-up: bound the `future-tense` lookbehind. Pin PCRE2 10.43 or later and test JIT and non-JIT builds.

### 5. Lexical similarity only

- Evidence (`slopvac-8l4.2.16`): 40 excerpts of 22 sentences, three rewrite replicates, and paired bootstrap over documents.
  - Dropped-fact F1: lexical 0.943, 0.915, 0.802 against model2vec 0.798, 0.733, 0.702. The difference of 0.10 to 0.18 is significant.
  - Claim grouping ARI: 0.300 against 0.194, significant.
  - PAWS-Wiki AUC: 0.687 against 0.485.
  - A literal and negation diff caught 73 to 94% of planted changes, with a false-positive rate of about 10 to 20% on faithful rewrites.
- Limits: gold alignment came from the rewriting model, and the edits were synthetic.
- Rejected: model2vec. It scored lower and would add a model to ship. A model2vec plugin is on the backlog.

### 6. Hand-rolled config layer stack with provenance

Build the stack on `toml_edit`, `saphyr`, serde, and `schemars`. Record file, line, and column for every contribution.

- Evidence (`slopvac-8l4.4.1`): both prototypes resolved 10,000 files in in under a hundredth of a millisecond per file with identical values.
  - `schematic` 0.20.12 has no per-list-element provenance, gives YAML errors without spans, reports the first error only, and overflows the stack on a cyclic `extends`. It adds 54 crates and 1.64 MB, and it was still pre-1.0.
  - Our stack is about 850 lines. `schematic` would save about 25 to 30% of the code.
- Rejected: `schematic`.

### 7. Generic front-matter crate with value spans

Write `frontmatter-spans` for YAML, TOML, and JSON, with per-value spans and serde support.

- Evidence: a survey of Rust crates found none that gave front matter with value spans (plan, "Rust crate research"). The survey has no bead with numbers, so this record has none.
- Rejected: an existing front-matter crate plus a second parse to recover positions.

### 8. JSON-RPC 2.0 over stdio for code plugins

Framing follows LSP. An `initialize` handshake exchanges capabilities. A Python SDK and a conformance suite ship with the protocol.

- Evidence: the plugin host prototype in `slopvac-8l4.2.17` ran on threads and crossbeam (49 lines, 7 dependencies), which shows the transport needs no async runtime. No bead measures the protocol against another transport, so this record has no comparison numbers.
- Rejected: in-process dynamic libraries and WASM. A subprocess keeps plugin crashes and memory use outside the host. WASM is on the backlog.

### 9. OCI artifacts, minisign, and mise-style trust

Distribute packs and plugins as OCI artifacts on GHCR or any registry. Ship minisign signatures as manifest layers, and verify them with `minisign-verify`. The host refuses an untrusted code plugin and prints the command that trusts it. `slopvac plugins trust` records trust per content hash. Agents and CI never trust on a user's behalf, and nothing prompts.

- Evidence: GHCR returns 404 for the referrers API, so signatures cannot attach as referrers. The tag-schema fallback works (`slopvac-8l4.2.17`). No bead has numbers for the trust model.
- Rejected: Sigstore verification in 3.0, which moves to the backlog. Rejected: prompting for trust, because an agent or CI job could answer it.
- Follow-up: a threat model and independent review must pass before the plugin host and OCI client close.

### 10. Error and diagnostic rendering: thiserror, anyhow, annotate-snippets

`thiserror` in libraries, `anyhow` in the binary, and `annotate-snippets` to render source diagnostics. No bead measured this choice. It follows the standard Rust split.

### 11. CLI and editor: clap and lsp-server

`clap` with `clap_complete` and `clap_mangen` for the CLI. `lsp-server` for the language server, which fits the no-async decision. No bead measured these choices.

### 12. Distribution: cargo-dist, Homebrew tap, and maturin wheels

cargo-dist builds archives and installers and feeds a Homebrew tap (`srobroek/homebrew-tap`). maturin builds binary wheels, so `uvx slopvac` stays the default install. The plan also adds GitHub attestations, an SBOM, and an auditable binary. No bead measured these choices.

### 13. Dependabot only

Remove Renovate. Dependabot covers cargo and the workflows. Patch and security updates merge automatically. No bead measured this choice.

### 14. reviewdog for PR reporting

The GitHub Action uses reviewdog with `reporter: auto`, or uploads SARIF. Its own annotation code is removed.

- Evidence (`slopvac-8l4.2.18`): reviewdog 0.21.3 parsed slopvac rdjsonl (151 diagnostics, 8 with replacements) and SARIF locally. The GitHub reporters were not tested.
- Also: rumdl 0.3.4 reported 7,806 findings on the corpus with defaults. About 95% were style or flavor noise (MD013 3,381, MD033 1,712, MD051 689). It overlaps slopvac on heading hierarchy, and partly on dashes and bold. The docs mention rumdl and nothing integrates it.

### 15. Output formats and LSP

Slopvac emits `text`, `json`, `sarif`, `rdjsonl`, `codeclimate`, `junit`, `checkstyle`, `markdown`, `html`, and LSP diagnostics. Each rule has a stable documentation page that formats link to. No bead measured this choice. The formats follow what reviewdog, CI systems, and editors read.

### 16. Generated reference material

Generate every reference document from code and data: JSON Schemas from Rust types, one page per rule, style, genre, and pack, the plugin protocol reference, and Rust API docs. CI fails when a generated file is stale.

- Rejected: hand-written reference pages. They drift. The 2.x docs and code already disagreed in places, and the plan carries a compatibility matrix bead for that reason.

### 17. No 2.x releases

No 2.18.x or 2.19 release ships. Rule-data fixes land on `main` in the Python reference, and the golden suite records the fixed behavior. Fixes that need Rust get 3.0 beads.

- Evidence: the trial page reproduced the reporter's scores (`slopvac-8l4.2.13`). Default config: 150 findings, 1 error, score 85.4, fail before; 83, 0, 91.8, pass after. Trial config: 80, 1, 92.3, fail before; 35, 0, 97.0, pass after. The single error is `negative-inventory-core` on a constraint phrased with the words "excluded" and "from".
- The detector prototype on 92 docs (`slopvac-8l4.2.14`) gave baseline precision of history-narration 5 of 175, `negative-inventory-core` 0 of 6, and title-case 225 of 280. The `requirement` tagger touched 9% of sentences and lost no observed true positive.

### 18. Full scope in 3.0.0

Confirmed 2026-11-14. An adversarial review proposed a smaller 3.0.0 with new platforms in 3.1. The decision keeps every programme bead outside the backlog in 3.0.0, under the `release:3.0.0` label. A release-readiness gate bead covers the whole scope.

## Consequences

Good:

- One binary, no Vale, no Python runtime, and a data and plugin API that third parties can build on.
- Every finding can name the layer, file, line, and column that produced its settings.
- Dependency count and binary size stay small.

Bad or risky:

- The rewrite is large, and the full scope raises the release risk. The golden suite, a compatibility matrix, and the readiness gate exist to manage it.
- PCRE2 is a C dependency. Its build must work on Windows, macOS, glibc, and musl.
- `harper-brill` must match Vale's POS tags well enough per rule. That spike is a go or no-go gate. No result is recorded yet.
- The plugin host and OCI client carry security risk. The threat model and independent review gate them.
- Several decisions (10 to 13, 15) have no spike numbers. They rest on convention and the plan.
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
| `slopvac-8l4.4.1` | `schematic` against our own layer stack |
| `slopvac-8l4.10.1` | Diagram over-explanation signals, which informs experimental diagram rules and no decision above |

The scratch data behind these runs is not in the repository. The beads hold the method and results.
