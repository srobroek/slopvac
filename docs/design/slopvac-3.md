# Slopvac 3.0 plan

Status: approved direction, 2026-11-14. Beads epic `slopvac-8l4`, labelled `slopvac-3.0`, tracks the work.
This document records the decisions, the evidence behind them, and the order of work.
slopvac 3.0 is a Rust rewrite with a public data and plugin API. It also absorbs the fixes that were meant for 2.x, because no further 2.x release ships.

## Inputs

- GitHub issues #252 to #257 from the Mecatl documentation trial, and the open dependency PRs.
- A Slack thread with the same reporter: trial results, model evaluations, and integration feedback.
- Experiments run on 2026-11-14. Their outputs stay out of the repository. The closed evidence beads in the table below record each method and result.

## Evidence summary

Labels in these experiments are single-annotator, and several samples are small. Treat the figures as estimates for these corpora.

| Experiment (bead) | Result | Decision |
|---|---|---|
| Stacklok page, before and after, default and trial config (`slopvac-8l4.2.13`) | Reproduces the reporter's scores. One false-positive error fails the gate: `negative-inventory-core` on the phrase `excluded from` in a constraint. | Fix the rule in the Python reference. Keep the page as an Apache-2.0 regression fixture. |
| Detector prototype, 92 public docs, 181k words (`slopvac-8l4.2.14`) | Correct findings: history-narration 5 of 175, negative-inventory 0 of 6, condition-after-command about 17%, title-case 225 of 280. Neither the `requirement` nor the sentence-level `enforced-invariant` detector removed an observed true positive. A lexical security tagger marked 40% of security-doc sentences. | Adopt `requirement`, `enforced-invariant`, and `change-note` contexts. Security context is declared, not inferred. |
| Rust regex spike, 143 compiled patterns, 8,496 texts (`slopvac-8l4.2.15`) | After two Unicode escapes were rewritten, PCRE2 with JIT matched Python on 142 patterns. One lookbehind failed to compile. PCRE2 ran about 4.5 times faster on one thread and about 40 times faster on 14 threads. Newline and case-folding edge cases are untested. | Use PCRE2. Bound the one variable-length lookbehind in `prose-craft.future-tense`. |
| Similarity A/B, lexical against model2vec, 40 docs, three rewrite replicates (`slopvac-8l4.2.16`) | Lexical matched or beat model2vec on alignment, dropped facts, and claim grouping. Dropped-fact F1 was 0.10 to 0.18 higher with lexical. A literal and negation diff found changed literals for review. | Lexical only. No embedding model in 3.0. |
| OCI spike: hand-rolled client on ureq, `oci-client`, smol (`slopvac-8l4.2.17`) | The ureq client pulls from GHCR in about 250 lines and adds 1.7 MB. `oci-client` adds 5.4 MB and needs tokio. smol shortened the subprocess prototype by about 20 lines but added 40 dependencies, and HTTP stayed blocking. GHCR has no referrers API. | Hand-rolled OCI client. No async runtime. Signatures ship as manifest layers. |
| rumdl and reviewdog evaluation (`slopvac-8l4.2.18`) | rumdl reports style, not slop: about 95% of 7,806 corpus findings are style or flavor noise. reviewdog parsed slopvac rdjsonl and SARIF locally. | Mention rumdl in docs only. Adopt reviewdog for PR reporting. |
| Rust crate research | Among the crates evaluated, none gave per-value provenance with line numbers, front matter with value spans, or install-method detection. | Write these. |
| Config spike: `schematic` against a layer stack of our own (`slopvac-8l4.4.1`) | Both resolve 10,000 files in under 9 µs each. `schematic` cannot show where each list element came from, gives no spans for YAML errors, and crashes on a cyclic `extends`. It adds 54 crates and 1.64 MB. | A layer stack of our own, which keeps file, line, and column for every contribution. |
| Diagram prototype: 37 human Mermaid blocks, 82 draw.io files, 61 LLM Mermaid diagrams (`slopvac-8l4.10.1`) | Default Sonnet output did not over-explain in this sample. 8 of 20 diagrams from a verbose prompt did. Maximum label length separated verbose diagrams from human ones (AUC 0.93). Token coverage flagged 14 of 14 redundant-prose cases, but only three human diagrams had prose to score. | Experimental lint rules for long labels, long notes, and prose that restates labels. Judgement rules for the rest. |

## Fixes rolled into 3.0

No 2.18.x or 2.19 release ships. The epic "Fixes rolled into 3.0" holds the fixes.

**Rule-data fixes in the Python reference.** These land on `main` without a release. The golden suite then records the fixed behavior, and the rule YAML carries into 3.0.

- #257 title case: count only words that start with one capital, then lower case. Skip acronyms, CamelCase, and project terms.
- #255: split "no longer" into its own rule that fires before change verbs only.
- #254: skip headings and table cells, and require an imperative opener.
- `negative-inventory-core`: fire on inventory forms only, and add the `requirement` exception.
- #256: accept the `versioned-change-note` exception.
- Bound the `future-tense` lookbehind. Hoist shared boundaries in the substitution and token pattern builders.

**Fixes the Rust beads own.** The 2.x beads for these are superseded by 3.0 beads that carry each requirement:

- #253 symlinks outside lint targets.
- #252: the `judgement` checklist honors config, error text keeps every interpolated value, and `prime write` reflects config.
- Update notices reach agents.
- `--format rdjsonl`.
- A warning for `[[overrides]]` globs that match nothing.
- STE stays out of the default behavior.
- release-please covers the Cargo workspace.

**Repository hygiene, to do now.**

- Dependabot only: remove `renovate.json`. Auto-merge patch updates and security updates with `dependabot/fetch-metadata` and the release app token. A weekly workflow checks the mise and Vale pins.
- Triage the open PRs. Close #245, #246, and #191 without merging: 3.0 removes Vale and ships a Rust binary.
- Adopt reviewdog in this repository, with a read-only lint job and a separate reporting job. Until 3.0 adds rdjsonl, reviewdog reads the 2.x SARIF output.

Python-only work is closed as not needed. That covers the standard-library swaps, Vale 3.27 support, and Python 3.15 classifiers.
When 3.0 ships, a bead tracks the replies on #252 to #257 and the Slack thread.

## 3.0 architecture

### Language and runtime

- **Language:** Rust, in a Cargo workspace. The Python 2.x code is the reference implementation until the golden suite passes.
- **Concurrency:** no async runtime. rayon handles CPU work. Dedicated threads handle waiting work. crossbeam-channel connects them, and `select!` with deadlines handles timeouts. ureq handles HTTP.
- **Engine:** slopvac matches every rule itself, and Vale is removed entirely. The README keeps an "Inspired by Vale" section that thanks the project.

| Concern | Choice |
|---|---|
| Regex | `pcre2` (JIT, match limits). The `regex` crate is optional for patterns without lookaround. |
| Word lists | `aho-corasick` |
| Markdown | `pulldown-cmark`. `markdown-rs` for MDX. A pre-pass masks `:::` and `!!!` containers. |
| Front matter | A new generic crate, `frontmatter-spans`: YAML, TOML, and JSON with per-value spans and serde support. |
| Part-of-speech tags | `harper-brill`, after a parity spike against Vale's tags |
| Spelling | `spellbook` with SCOWL and VarCon data |
| Code comments | `tree-sitter` with the language pack |
| HTML | `html5ever` |
| RST | A bundled docutils-to-HTML adapter in core |
| AsciiDoc | An experimental first-party extractor plugin that converts through asciidoctor to HTML |
| Discovery | `ignore` and `globset`. `.gitignore` support sits behind a setting. |
| Diff scope | `git` subprocess or `git2`, with `similar` |
| Config | A layer stack of our own: `toml_edit`, `saphyr`, serde, `schemars`. The `schematic` spike lost on provenance. |
| Errors | `thiserror` in libraries, `anyhow` in the binary, `annotate-snippets` for rendering |
| CLI | `clap`, `clap_complete`, `clap_mangen` |
| HTML report | `minijinja` |
| Paths, writes, locks | `etcetera`, `tempfile` persist, `fs4` |
| Downloads | `ureq`, `sha2`, `flate2`, `tar`, `zip`, with safe extraction |
| Updates | `update-informer`, plus `axoupdater` for installs made by our own installer |
| Signatures | `minisign-verify` for releases and plugins |
| LSP | `lsp-server` |
| Logging | `tracing`, enabled with `SLOPVAC_LOG` |

### Data and API schema

pydantic models defined the 2.x schema. In 3.0, Rust types generate the JSON Schema, which is published per API major version.

- **IDs:** namespaced as `<pack>:<id>`. Built-ins live in `core`. Short names still work where they are unambiguous.
- **Rules:**
  - A typed `match:` block (`tokens`, `pattern`, `substitution`, `metric`, `structure`, `capitalization`, `vocabulary`, `judgement`).
  - Fields for `exclude_blocks`, `contexts`, `applies_to`, and named exception detectors.
  - Test cases in the `vale test` style: `input`, `want`, `contains`, `absent`.
  - `tiers` is removed.
- **Profiles:** set gate thresholds and a severity shift only.
- **Styles:** ordered presets with `extends` and declared `conflicts`. The last listed style wins.
- **Genres:** data files with detection signals. A content type such as `how-to` is a genre that extends a genre. Diátaxis types are consumer content types.
- **Context tags:** `{kind, span, confidence, evidence}` from registered taggers. Taggers are declarative in data packs and code in plugins.
- **Terms:** `.slopvac/terms.toml`. Each term needs only `term`. `variants` and `kind` are optional.
- **Config:**
  - `slopvac.toml` with `schema_version = 3`, `extends`, `styles`, `packs`, `plugins`, `[[genres]]`, `[frontmatter]` policy, `[vale]` removed, `[guidance] level`, `[thresholds]`, and `[[overrides]]`.
  - The nearest config to each file applies.
  - Front matter is an allowed-fields layer under a `slopvac:` key.
- **Lint JSON v3:** `schema_version`, `notices`, per-document `genre` and config sources, and per-finding `pack`, `contexts`, and `end_line`.
- **Output formats:** `text`, `json`, `sarif`, `rdjsonl`, `codeclimate`, `junit`, `checkstyle`, `markdown`, `html`, and LSP diagnostics. Each rule has a stable documentation page that the formats link to.

### Layer order

From lowest priority to highest: core defaults, styles, the genre chain, `extends`, project config, matching `[[genres]]` and `[[overrides]]`, front matter, inline directives, CLI flags.
`--explain-config` prints the layer, the file, and the line for each value, and what the value overrode.

### Packs and plugins

- **Data packs** hold rules, styles, genres, terms, declarative taggers, and prime snippets. They contain no code. A `slopvac-pack.toml` manifest declares `slopvac_api`.
- **Code plugins** speak JSON-RPC 2.0 over stdio. Framing follows LSP. The `initialize` handshake exchanges capabilities. A Python SDK ships with them, and a conformance suite tests them.
  - Hook points: taggers, extractors, reporters, harness recipes, fixers, scorers, and model providers.
  - Python plugins run in their own environment.
- **Distribution:** OCI artifacts on GHCR or any registry is the primary channel. Release archives, local folders, and git pinned to a commit also work.
- **Lockfile:** `.slopvac/packs.lock` records the version, source, and digest.
- **Signatures:** minisign signatures ship as manifest layers. Publisher keys are listed in the index.
- **Trust:**
  - The plugin host refuses to load an untrusted code plugin. slopvac lists each one with the command that trusts it.
  - `slopvac plugins trust` records trust per content hash. Trust is an explicit command, not a prompt.
  - Agents and CI never trust on the user's behalf.
- **Commands:** `plugins sync`, `outdated`, `update`, `status`, `trust`, and `search`, which reads an index that a job rebuilds automatically. `pack new`, `validate`, `test`, and `publish` complete the set.

### Agents

- **prime:**
  - The base topic is about 250 words. It has one line per command and an index of topics.
  - Each topic is a terse checklist with its own index.
  - slopvac renders each topic from a Markdown file, against the config, at the detail that `[guidance] level` selects.
  - `.slopvac/PRIME.md` overrides a topic.
- **Setup:** `setup <harness>` supports `opencode`. The flags select the block, the skill, and the reviewer agent, and set the reviewer model. Skills follow the Agent Skills specification.
- **Review:**
  - Types are `mechanical`, `update`, and `rewrite`.
  - Fact checking covers changed claims only, with a scope that scales with the change. slopvac asks the user to confirm the scope when it would be exceeded.
  - Fact preservation uses lexical alignment and a literal diff.
  - The reviewer must use a different model from the author.
- **Model guidance:** prime and the docs list model recommendations per review type. The eval results generate the list.

### Distribution and release

- cargo-dist builds release archives, installers, and a Homebrew tap (`srobroek/homebrew-tap`).
- maturin wheels keep `uvx slopvac` as the documented default.
- Release candidates follow the platevault model: an `rc/vX.Y.Z-rc.N` tag cut on demand and a provenance gate before stable.
- Releases carry minisign signatures. GitHub attestations, an SBOM, and an auditable binary come with each release.
- `slopvac self update` runs for installs made by our installer. Other installs print the matching upgrade command.
- The GitHub Action uses reviewdog with `reporter: auto`, or uploads SARIF. Its own annotation code is removed.
- MegaLinter and Trunk descriptors follow the release.

### Quality

- Tests: nextest, `cargo test --doc`, insta, and snapbox or trycmd.
- Lints: clippy with workspace lints, and rustfmt.
- Hygiene: cargo-deny, cargo-shear, typos, cargo-sort, Swatinem/rust-cache, and Dependabot for cargo.
- Hooks: prek.
- Added later: cargo-llvm-cov, cargo-mutants on the diff, fuzzing of parsers, CodeQL, gungraun benchmarks, and an MSRV check.

### Generated documentation

slopvac generates every reference document from code and data, and CI fails when a generated file is stale:

- API schemas from the Rust types: lint JSON, config, front matter, pack manifest, rules, styles, genres, terms, lockfile, and plugin protocol messages. Each schema is versioned per API major and published at a stable URL.
- One page per rule, with examples, exceptions, contexts, severity per profile and style, and provenance. Output formats link to these pages.
- One page per style preset and per genre or content type.
- The plugin protocol reference, the hook points, the pack manifest reference, and a page per pack.
- Rust API docs: crate docs in every `lib.rs`, `missing_docs` on library crates, rustdoc with warnings denied, and docs.rs for published crates.

### Evals

- An eval corpus lives in the repository as a manifest and a fetch script. It contains:
  - human text written before 2022;
  - LLM text that its publisher labels as model output;
  - human twins, where models write from human outlines;
  - seeded defects with clean controls;
  - rewrite pairs.
- Labels come from judges of two model families plus a human spot check.
- A paired bootstrap over documents measures each change.
- `just eval` runs an offline tier in CI, A/B comparisons between refs, and model comparisons.
- A precision ratchet blocks rule changes that lower precision beyond the noise.

### Migration from 2.x

- `uvx slopvac@latest prime migrate` runs the chain of migrations from the detected version.
- `docs/migrate-2-to-3.md` and `prime migrate` render from one source.
- `slopvac migrate` previews the changes, then rewrites the config with comments kept. It updates directive IDs and steering blocks. It compares findings before and after migration.
- 3.x reads 2.x configs in a compatibility mode for one minor release.

## Release gate and risks

An adversarial review of this plan and its beads found these gaps. Each one now has a bead:

- **Compatibility:** a generated matrix of every 2.x command, flag, and behavior, with a disposition (preserve, migrate, or remove with deprecation) and an owning bead. Installed-binary tests cover the preserved rows. stdin, `--diff-working-tree`, `--fix`, `reference`, `onboard`, `init`, `setup --remove`, and the published pre-commit hook IDs each have their own bead.
- **Golden suite modes:** reference parity pinned to a Python commit, Vale 3.24, and corpus hashes; 3.0 default-policy tests with reviewed deltas; and migration-preservation tests. The 2.x profiles have per-rule dispositions, so a separate bead maps them onto the 3.0 model.
- **Plugin security:** a threat model and an independent review before the plugin host and OCI client close. The review covers what the signature covers, publisher-key authority, key rotation, extraction limits, subprocess containment, and regex resource limits.
- **PCRE2 build policy:** pin version 10.43 or later, test JIT and non-JIT across Windows, macOS, glibc, and musl, and prove a match-limit mechanism.
- **POS parity:** the `harper-brill` spike is an architecture gate with a go/no-go threshold judged on per-rule findings.
- **Accuracy gate:** recall on seeded and adjudicated positives, false-positive rates on clean controls, and a held-out set, as well as precision.
- **Position contract:** byte spans, line and column bases, and per-format conversions, including LSP UTF-16. Agree these before fixes and suggestions ship.
- **RST:** stays in core through a bundled docutils adapter. AsciiDoc is new and experimental.
- **Performance:** budgets for the installed binary, measured before they gate releases.
- **Policies:** network and privacy, accessibility, and API deprecation windows.
- **Release readiness:** one gate bead that the stable release depends on, separate from building candidates.
- **Interim status:** no 2.x release ships, so the issues get status and workarounds now.

The review also proposes a smaller 3.0.0. Under that cut, 3.0.0 is a Rust lint replacement with compatibility, migration, safe fixes, local custom rules, and the current outputs. Remote packs and plugins, LSP, diagrams, Diátaxis detection, proper-noun inference, extra reporters, self update, and model evals move to 3.1 or later. That cut is not decided yet.

## Order of work

1. Rule-data fixes in the Python reference, and repository hygiene.
2. 3.0 contract: schemas, plugin protocol, golden suite, fixtures.
3. Rust engine crates, behind the golden suite.
4. Config, front matter, terms, genres, styles, and context tagger.
5. CLI, output formats, LSP, prime, and setup.
6. Packs and plugins: protocol, OCI, trust, signatures, and first-party packs.
7. Diagrams, experimental.
8. Distribution, release candidates, and migration.
9. Evals and the precision ratchet. These start in step 2 and continue in parallel.

## Backlog

- A WASM build.
- Languages other than English.
- D2 and Structurizr extractors.
- An optional MCP wrapper.
- Sigstore and attestation verification in Rust.
- A model2vec plugin.
