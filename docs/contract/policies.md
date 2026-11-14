# Slopvac 3.0 policies: network, accessibility and API lifecycle

Status: contract for 3.0. Bead `slopvac-8l4.2.12`. Plan: [slopvac-3.md](../design/slopvac-3.md).

This document fixes three policies that the 3.0 binary, its schemas, and its plugin protocol must follow. Each section marks every statement as one of these:

- **2.x behavior** describes behavior of `packages/slopvac-lint`, with the source file that implements it.
- **3.0 requirement** describes behavior that does not exist yet. An owning bead follows each requirement. A requirement without an owning bead is a gap, and the release-readiness gate (`slopvac-8l4.13.9`) blocks on it.

"Must" is a requirement on the 3.0 binary. "Network" means any connection outside the local machine, including DNS lookups and registry or API calls.

## 1. Network and privacy

### 1.1 Principles

1. `lint`, `validate`, `rules`, `explain`, `prime`, `reference`, and `claims` read local files only. They open no connection.
2. Every network feature is a named command or hook in the table in section 1.2. No other code path opens a connection.
3. Telemetry is absent. Slopvac transmits no document text, finding text, file path, rule hit count, or usage data to any server.
4. A failed or refused connection never changes a lint verdict. It prints an error and exits 2 (incomplete) only when the user asked for the network operation.
5. Agents and CI never consent on the user's behalf. Consent is an explicit command or flag that a person runs. No prompt exists that an agent could answer.

### 1.2 Inventory of network features

| Feature | 2.x behavior | 3.0 requirement | Owner |
|---|---|---|---|
| Update check | A detached process asks `https://pypi.org/pypi/slopvac/json` for the latest version and caches the result for 24 hours (`update_notice.py`). It runs only when stderr is a TTY. | Check the registry that matches the install method (`update-informer`). Cache for 24 hours. Show the result in `prime`, in JSON `notices`, and in `--version --json`, so agents see it. | `slopvac-8l4.12.4` |
| `self update` | None. | Runs only for installs made by the slopvac installer. Downloads the release archive and verifies its minisign signature before it replaces the binary. | `slopvac-8l4.12.4`, `slopvac-8l4.13.3` |
| Pack and plugin fetch | None. 2.x has no packs. | `plugins sync`, `plugins update`, and `pack publish` pull or push OCI artifacts. The client is hand-written on `ureq`. It uses anonymous tokens on GHCR and `docker_credential` for private registries. | `slopvac-8l4.9.2`, `slopvac-8l4.9.3`, `slopvac-8l4.9.9` |
| Outdated check | None. | `plugins outdated` lists newer digests and versions from the pinned sources. | `slopvac-8l4.9.3` |
| Pack index search | None. | `plugins search` reads the published index over HTTPS. | `slopvac-8l4.9.8` |
| Git packs | None. | A pack pinned to a git commit clones during `plugins sync` only. | `slopvac-8l4.9.3` |
| Issue submission | `prime report` prints a workflow that tells an agent to run `gh issue create` after the user approves the exact post (`guidance.py`). The `gh` program connects. | `slopvac report` reads a token from `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth token` and posts the issue. Without a token it opens a prefilled issue-form URL. Both paths need the consent step in section 1.5. | `slopvac-8l4.12.6` |
| Model-provider hooks | None. | A plugin that implements the model-provider hook may contact a model service. Slopvac core does not. Consent rules apply (section 1.5). | `slopvac-8l4.9.6`, `slopvac-8l4.11.3` |
| LSP server | None. | `slopvac lsp` talks to the editor over stdio and opens no connection. | `slopvac-8l4.12.7` |
| Code plugins in general | None. | A plugin process is a separate program. Slopvac 3.0 leaves plugin network access unsandboxed. The trust command (section 1.6) is the control, and the threat model records the residual risk. | `slopvac-8l4.9.4`, `slopvac-8l4.9.11` |

Install-time downloads sit outside the binary. In this repository, `scripts/install_vale.py` downloads Vale for development, and 3.0 removes Vale (`slopvac-8l4.16.4`).

### 1.3 Offline mode and opt-outs

**2.x behavior.** The update check stops when any of these is true (`update_notice.py`, `_disabled_by_environment` and `_enabled`; `cli.py`, `_machine_output`):

- the `CI` variable is set, with any value;
- `NO_UPDATE_NOTIFIER`, `SLOPVAC_NO_UPDATE_CHECK`, or `DO_NOT_TRACK` has a non-empty value;
- stderr is not a TTY;
- the command is `prime`, the format is not `text`, or `--out` or `--open` is present.

2.x has only the environment variables above as switches.

**3.0 requirement.** Offline mode blocks every row of section 1.2. These switches turn it on:

| Switch | Effect |
|---|---|
| `--offline` (global flag) | Offline for this run. |
| `SLOPVAC_OFFLINE=1` | Offline for every run in the environment. |
| `offline = true` under `[network]` in `slopvac.toml` | Offline for the project. |

Offline is sticky. If any source sets it, no other source can unset it. This departs from the layer order of the plan, where a higher layer overrides a lower one.

In offline mode:

- A command that needs the network exits 2 with the message `offline: <command> needs the network`. It does not retry or fall back.
- Packs that the lockfile pins and that sit in the local cache load normally. A missing cache entry is an error that names the pack and the digest.
- `plugins sync` can succeed from the cache alone. It verifies digests against `.slopvac/packs.lock` and reports any missing pack.

These opt-outs apply to the update check only:

| Switch | Effect |
|---|---|
| `NO_UPDATE_NOTIFIER`, `SLOPVAC_NO_UPDATE_CHECK`, `DO_NOT_TRACK` | Same as 2.x. |
| `update_check = false` under `[network]` | Project-level opt-out. |
| `CI` | No background update check in CI. A cached notice still shows if a cache exists. |

Owners: `slopvac-8l4.12.1` for the global flag and environment, `slopvac-8l4.4.2` for the config keys, `slopvac-8l4.12.4` for the update check.

### 1.4 CI defaults

- Slopvac detects CI from the `CI` variable, as 2.x does.
- In CI the update check stays off, and every command runs without prompts.
- `plugins sync` in CI runs from the lockfile. It fails with exit 2 when the lockfile is missing or a digest differs, and it leaves the lockfile as it found it.
- A GitHub Action run that needs packs runs `plugins sync` as a separate, named step. The lint step runs with `--offline`.

Owners: `slopvac-8l4.9.3` for lockfile behavior, `slopvac-8l4.13.6` for the Action.

### 1.5 Consent

Two features need consent beyond installing slopvac: issue submission and model-provider hooks.

**Issue submission.**

- `slopvac report` prints the exact title, labels, and body it would post, then exits. Posting needs `--submit`.
- The body contains no local paths, file names, user names, host names, repository names, or organization names. Document text appears only when the user passes `--include-text <file>`, and the preview shows that text.
- Environment fields come from the CLI, never from environment variables, as `CONTRIBUTING.md` requires for agent reports.
- 2.x already requires the agent to get the user's approval of the exact post (`guidance.py`, the `prime report` workflow). 3.0 keeps that rule in the prime text and adds the command-level guard above.

**Model-provider hooks.**

- A model provider is a plugin. It stays off until the user trusts the plugin (`slopvac plugins trust`) and names it in `slopvac.toml` under `[review] provider`.
- Slopvac sends a provider only the text that the review type needs: changed claims for fact checking, the changed passages for `update`, and the whole document for `rewrite`. `slopvac review --dry-run` prints the exact payload without calling the provider.
- During `lint`, every provider stays idle.
- In offline mode no provider call happens, even for a trusted provider.
- The reviewer must use a different model from the author. Slopvac cannot verify this for a provider it does not control, so the check compares the model names that the config and the provider report.

Owners: `slopvac-8l4.12.6`, `slopvac-8l4.9.6`, `slopvac-8l4.11.3`.

### 1.6 Trust

- The plugin host refuses to load a code plugin until `slopvac plugins trust` records its content hash. A hash change revokes trust.
- `sync`, `update`, and flags such as `--yes` never record trust.
- Signatures verify the artifact before extraction. A missing or invalid signature makes `sync` fail with exit 2.

Owners: `slopvac-8l4.9.4`, `slopvac-8l4.9.5`, `slopvac-8l4.9.11`.

### 1.7 Logging and redaction

**2.x behavior.** Slopvac has no logging framework and no log file. Two redactions exist:

- Input from `--stdin` is staged in a temporary file. Every report shows the path as `<stdin>`, and the temporary directory name never reaches output (`pipeline.py`, `redact_stdin`). Tests in `packages/slopvac-lint/tests/test_cli.py` cover text, JSON, and error output.
- The update-check cache stores the check time and the latest version string.

**3.0 requirement.**

- Logging uses `tracing` and stays off unless `SLOPVAC_LOG` is set. Log output goes to stderr. No log file is written.
- Logs never contain document text, finding text, matched spans, front matter values, or terms.
- Logs record document paths relative to the project root. A path outside the root appears as `<external>/<file name>`. Stdin appears as `<stdin>` everywhere, including logs, panics, and error chains.
- Logs never contain tokens, `Authorization` headers, or URL credentials. Slopvac strips the user-info part of a URL before it logs the URL.
- Rule IDs, pack IDs, digests, durations, and counts may appear in logs.
- Panic and error output follow the same rules.
- `SLOPVAC_LOG=trace` lifts none of these rules.

Owners: `slopvac-8l4.12.1` for the logging setup, `slopvac-8l4.12.9` for stdin.

### 1.8 Data written to disk

- Caches and state go to the per-user directories that `etcetera` reports. `SLOPVAC_CACHE_DIR` overrides the cache location, as in 2.x (`vale_cache.py`).
- Slopvac writes files atomically and takes a lock for shared state (`tempfile` persist and `fs4`).
- Slopvac writes only to the cache directory, the project's `.slopvac/` directory, and paths the user names.

Owners: `slopvac-8l4.9.3`, `slopvac-8l4.9.4`.

## 2. Accessibility

### 2.1 Plain and no-color output

**2.x behavior.**

- Text output goes through a `rich` console. Rich drops styling when stdout is not a terminal, so piped output carries no escape codes (`cli.py`, `_console`). `test_cli.py` tests this.
- `lint --no-color` removes color codes. Bold and italic styling remain in a terminal. A test covers this.
- JSON, SARIF, and GitHub annotations contain no terminal escape codes.
- The `NO_COLOR` variable is ignored. `_console` passes `no_color=False`, which overrides the variable that `rich` would read. The defect is optional to fix in 2.x, because no 2.x release ships.

**3.0 requirement.** Color is resolved once, in this order:

1. `--color never|always|auto` (default `auto`) wins when given.
2. A non-empty `NO_COLOR` means `never`.
3. A non-empty `CLICOLOR_FORCE` or `FORCE_COLOR` means `always`.
4. Otherwise color is on when stdout is a terminal and `TERM` is not `dumb`.

`--no-color` stays as an alias for `--color never`.

When color is `never`, output also drops bold, italic, underline, and cursor controls. Tables use ASCII borders when `TERM=dumb` or when the locale is not UTF-8.

Owners: `slopvac-8l4.12.1` for the flags, `slopvac-8l4.12.2` for the renderers.

### 2.2 Text that does not depend on sight

- No signal relies on color alone. Every severity, verdict, and status appears as a word (`error`, `warning`, `suggestion`, `PASS`, `FAIL`, `UNCHECKED`). 2.x already does this in text and HTML (`html.py`).
- Each finding prints on its own line in the form `path:line:column severity rule-id message`, so a screen reader reads the location first.
- Text output has no spinners, progress bars, or animation. Progress goes to stderr, and only when stderr is a terminal and color is not `never`.
- Symbols and emoji carry no meaning. Box-drawing characters are decoration, and each table row also reads in order as plain words.
- When color is `never` and stdout is not a terminal, the renderer inserts no padding to align columns and does not wrap messages with hard line breaks.

Owner: `slopvac-8l4.12.2`.

### 2.3 Accessible HTML report

**2.x behavior** (`html.py`):

- The page sets `lang="en"`, has a `<title>`, and puts content in `<main>`.
- Tables use `<th>` header cells. File details use `<details>` and `<summary>`.
- The verdict and the severity of each finding appear as text.
- The stylesheet respects `prefers-color-scheme`. Computed from the stylesheet variables with the WCAG relative-luminance formula, the status and muted text colors reach at least 4.87:1 against their panel in the light scheme. In the dark scheme they reach at least 5.26:1.
- Every interpolated value is HTML-escaped.

**3.0 requirement.** The 3.0 report keeps those properties and adds:

- `scope="col"` or `scope="row"` on table headers, and a `<caption>` on each table.
- One `<h1>`, and headings that skip no level.
- A "Skip to findings" link as the first focusable element.
- Visible keyboard focus on every interactive element, with at least 3:1 contrast.
- A `prefers-reduced-motion` media query. The report has no animation.
- Contrast of at least 4.5:1 for body text and 3:1 for large text and UI borders, in both schemes.
- No JavaScript and no remote resources (fonts, scripts, or images).

An automated checker (axe-core) finds only part of the WCAG 2.2 AA failures. The release checklist adds a manual keyboard and screen-reader pass.

Owner: `slopvac-8l4.12.2`.

### 2.4 Language

- 3.0 messages, rule explanations, and generated pages are English only. `slopvac-8l4.18.2` tracks other languages after 3.0.
- Message text is not an interface. Consumers branch on rule IDs, error codes, and exit codes (section 3.5).
- The HTML report sets `lang="en"`. Strings live in one message table, so a later release can translate them without changing logic.

Owner: `slopvac-8l4.12.2`.

## 3. API lifecycle

### 3.1 Versioned surfaces

| Surface | Version field | Where it lives | Schema | Owner |
|---|---|---|---|---|
| Lint JSON report | `schema_version` (integer) | Report root | `lint-report` | `slopvac-8l4.2.2` |
| Config file | `schema_version` (integer) | `slopvac.toml` root | `config` | `slopvac-8l4.2.5` |
| Front matter block | `v` | `slopvac:` key | `frontmatter` | `slopvac-8l4.2.5` |
| Rule, category, style, genre, and terms files | `schema_version` (integer) | File root | One per artifact | `slopvac-8l4.2.3`, `slopvac-8l4.2.4` |
| Pack manifest | `slopvac_api` (integer) | `slopvac-pack.toml` | `pack-manifest` | `slopvac-8l4.2.4` |
| Lockfile | `schema_version` (integer) | `.slopvac/packs.lock` | `packs-lock` | `slopvac-8l4.2.4` |
| Plugin protocol | `protocolVersion` (integer) | `initialize` request and response | `plugin-protocol` | `slopvac-8l4.2.6` |

The shared definitions are `SchemaVersion` and `ApiVersion` in `schemas/v3/common.schema.json`. The scaffold bead `slopvac-8l4.2.19` freezes their shape. This document fixes their meaning.

### 3.2 `schema_version` and `slopvac_api`

**2.x behavior.** `LintReport.schema_version` defaults to 1. The docstring in `report.py` states the rule: it changes only when a key is removed or retyped, and adding a key does not bump it. The report has a separate `version` key for the tool version. `doctor --format json` has its own `schema_version` of 1 (`doctor_report.py`). 2.x config files have no version field, and `extra="forbid"` rejects unknown keys (`config.py`).

**3.0 requirement.**

- `SchemaVersion` is a positive integer. It counts breaking changes to one artifact's shape and has no minor or patch part.
- Every root instance of a versioned artifact carries `schema_version` with the constant 3. Lint JSON jumps from 1 to 3 so that all artifacts share one number at first. The migration guide states this jump. A later breaking change raises only the number of the artifact it affects, so numbers can diverge after 3.0.
- Changes within one `schema_version` are additive only. Allowed: a new optional field, a new optional section, and a new value of an output-only enum that the schema marks as extensible. Not allowed: removing or renaming a field, changing a type, tightening a constraint, or giving a field a new meaning.
- A schema's `$id` never changes within a version. The published URL has the form `https://srobroek.github.io/slopvac/schemas/v3/<artifact>.schema.json`.
- `ApiVersion` is a positive integer for the pack and plugin extension API. The first pack manifest declares `slopvac_api = 1`. It names the host capabilities a pack needs. `schema_version` names the shape of one file. The two are independent.
- The binary version is independent of both. A release that adds optional fields keeps `schema_version`. `slopvac --version --json` lists the binary version, each supported `schema_version`, and each supported `slopvac_api`.
- A config file without `schema_version` selects the 2.x compatibility mode (section 3.7). Any other 3.0 artifact without a version is an error.
- A version higher than the binary supports is an error that names the file, the version found, the versions supported, and the upgrade command (`upgrade_hint`, as in 2.x).

Owners: `slopvac-8l4.2.12` for the semantics, `slopvac-8l4.4.5` for the config migration chain.

### 3.3 Unknown-field handling

The rule depends on who wrote the file.

| Reader | Writer | Unknown field | Reason |
|---|---|---|---|
| Slopvac | A user (config, front matter, rules, packs) | Error with file, line, and column, plus the nearest valid key | A misspelled key would silently disable a setting. 2.x already forbids unknown keys. |
| Slopvac | A plugin (protocol messages) | Ignored, logged at debug level | A plugin can be newer than the host within one API version. |
| A consumer of slopvac output | Slopvac | The consumer should ignore it | Additive changes do not bump `schema_version`. |
| A plugin | Slopvac (protocol messages) | The plugin must ignore it | Same reason. |

Authors who attach their own data to a user-written file put it under a key with the prefix `x-`. Slopvac ignores `x-` keys wherever it forbids unknown keys and never gives one a meaning. Each artifact schema records this 3.0 decision in its `description`.

The schema marks which output enums can gain values. Consumers must tolerate new values of those enums.

Owners: `slopvac-8l4.2.3`, `slopvac-8l4.2.4`, `slopvac-8l4.2.5`, `slopvac-8l4.2.6`.

### 3.4 Capability negotiation

The plugin protocol follows LSP. The `initialize` request carries the host's `protocolVersion`, its supported hook points, and its feature flags. The response carries the plugin's `protocolVersion`, the hooks the plugin implements, and the features it needs.

- The host picks the highest protocol version that both sides support. With no common version, the host does not load the plugin and prints both version lists.
- The host calls only the hooks that the plugin declared.
- A required feature that the host lacks stops the load with an error that names the feature. The host skips an optional feature it lacks.
- Unknown capability names are ignored (section 3.3).
- A data pack has no handshake. The host compares `slopvac_api` with the range it supports and loads the pack only when the value is in range.

The message shapes belong to the plugin protocol bead. This document fixes the behavior above.

Owners: `slopvac-8l4.2.6`, `slopvac-8l4.9.6`, `slopvac-8l4.9.1`.

### 3.5 Error codes

**2.x behavior.** The CLI exit codes are 0 (pass), 1 (a gate failed), and 2 (the run was incomplete) (`contract.py`). Exit 2 means the result cannot establish a pass. 2.x messages have no stable codes.

**3.0 requirement.**

- The exit codes keep their meaning. Slopvac uses no other exit code.
- Every error and notice has a stable `code`: a lowercase kebab-case string such as `config-unknown-key` or `pack-api-unsupported`. The code appears in brackets in text output, in JSON `notices` and errors, and in the generated documentation.
- A code is never reused and never changes meaning. A code that stops occurring stays in the documentation as retired.
- Plugin protocol errors use the JSON-RPC 2.0 error object. Its numeric `code` follows the JSON-RPC ranges, and `data.slopvac_code` carries the string code. The protocol bead defines the numeric range.
- Message text can change in any release. Codes, rule IDs, and exit codes form the interface.

Owners: `slopvac-8l4.2.6` for the protocol, `slopvac-8l4.4.7` for config diagnostics, `slopvac-8l4.12.1` for the CLI.

### 3.6 Deprecation windows

A deprecation passes through three states: announced, warning, and removed.

| Surface | Warning period | Earliest removal |
|---|---|---|
| CLI command, flag, or environment variable | At least one minor release, with a one-line stderr warning that names the replacement | The next major release |
| Config key or value | At least one minor release, with a warning from `validate` and `lint` | The next major release |
| Output fields (JSON, SARIF, and others) | The earlier `schema_version` stays available through `--schema-version <n>` for the whole next major release | The major release after the replacement |
| Rule ID | The old ID resolves to the new one for at least one minor release and emits a warning | The next major release |
| Data pack `slopvac_api` | The host loads the value that the new one replaced for at least 12 months after the new one ships | After those 12 months, and not before the next major release |
| Plugin `protocolVersion` | The host speaks the version that the new one replaced for at least 12 months after the new one ships | After those 12 months, and not before the next major release |

Release notes and the generated docs announce every deprecation. A deprecation never changes a lint verdict in its warning period. Warnings go to stderr and to JSON `notices`, and they leave the exit code alone.

The 2.x configuration window is a special case (section 3.7).

Owners: `slopvac-8l4.12.1`, `slopvac-8l4.4.5`, `slopvac-8l4.9.1`.

### 3.7 Compatibility window for 2.x configs

**Decision.** 3.x reads 2.x configs in compatibility mode until the later of these two events:

- the release of 3.2.0;
- six months after the release date of 3.0.0.

The release before the one that ends the window must announce the end in its release notes.

**Reasoning.** The plan says "one minor release" (`docs/design/slopvac-3.md`, "Migration from 2.x"). Bead `slopvac-8l4.2.5` asks for a minimum calendar period, because minor releases can ship days apart. The decision keeps both a release count and a calendar floor. The count is two minors after 3.0, which is longer than the plan's wording. No 2.x release ships, so no 2.x user gets an earlier warning.

**Behavior in compatibility mode.**

- A config file without `schema_version` is a 2.x config. This covers `.slopvac.toml`, `slopvac.toml`, and `[tool.slopvac]` in `pyproject.toml`.
- Slopvac migrates the file in memory with the same pure function that `slopvac migrate` uses. The result equals what `migrate` would write.
- Every run that reads a 2.x config prints one warning on stderr with the code `config-legacy-version` and adds a notice to JSON output. The warning names the file and the command `slopvac migrate`.
- The mapping covers every 2.x setting, including negated globs, category budgets and weights, per-path locale, vocabulary files, and guidance controls. A setting with no 3.0 equivalent produces a `config-legacy-dropped` error and never disappears silently.
- Findings in compatibility mode match the findings after `slopvac migrate` writes the file.
- A config with `schema_version` 3 is always read as a 3.0 config.
- Directive IDs and steering blocks in documents sit outside the window. `slopvac migrate` rewrites them.

Owners: `slopvac-8l4.4.5` for the chain and the mode, `slopvac-8l4.2.5` for the mapping table, `slopvac-8l4.16.1` for `migrate`, `slopvac-8l4.16.2` for `prime migrate`.

### 3.8 SDK support

- The Python SDK implements one `protocolVersion` per SDK major version. It supports the host's current and previous protocol versions for the windows in section 3.6.
- The SDK ships a conformance suite. A plugin in any language can use it, and the example plugin must pass it.
- The SDK validates messages against the published `plugin-protocol` schema, so a protocol mistake shows up in the plugin's own tests.
- SDK releases follow semantic versioning. A minor release can add optional capabilities. A protocol-incompatible change needs an SDK major release.
- An SDK in another language builds on the published JSON Schemas.

Owners: `slopvac-8l4.9.7`, `slopvac-8l4.19.1`.

## 4. Conformance tests

The 3.0 binary must pass these tests. Each runs the installed binary with an isolated home and cache directory. `slopvac-8l4.13.9` blocks the release until all pass.

| ID | Test | Owner |
|---|---|---|
| N1 | `lint`, `validate`, `rules`, `explain`, `prime`, `reference`, and `claims` each finish under a network sandbox that fails any connection. | `slopvac-8l4.12.1` |
| N2 | `--offline`, `SLOPVAC_OFFLINE=1`, and `[network] offline = true` each make `plugins sync` exit 2 when the cache lacks a pack, with the message in section 1.3. | `slopvac-8l4.9.3` |
| N3 | Offline set in the environment survives a flag or config that tries to unset it. | `slopvac-8l4.12.1` |
| N4 | With a populated cache and a lockfile, `plugins sync --offline` succeeds and verifies digests. | `slopvac-8l4.9.3` |
| N5 | No update check starts under `CI`, `NO_UPDATE_NOTIFIER`, `SLOPVAC_NO_UPDATE_CHECK`, `DO_NOT_TRACK`, `update_check = false`, or `--offline`. This extends the 2.x test `test_environment_suppression_prevents_refresh_and_notice`. | `slopvac-8l4.12.4` |
| N6 | Machine formats and `prime` keep stdout free of update notices. JSON carries it in `notices`. | `slopvac-8l4.12.4` |
| N7 | `plugins sync` in CI exits 2 on a missing lockfile or a digest mismatch and leaves the lockfile unchanged. | `slopvac-8l4.9.3` |
| N8 | `sync` and `update` never record trust, with or without `--yes`. | `slopvac-8l4.9.4` |
| N9 | `slopvac report` without `--submit` sends zero requests and prints the full body. Against a mock server, `--submit` posts exactly the previewed body. | `slopvac-8l4.12.6` |
| N10 | The issue body for a run in a directory with a unique marker path and user name contains neither. | `slopvac-8l4.12.6` |
| N11 | A review run with a model provider and `--dry-run` leaves the provider uncalled and prints the payload. A `lint` run leaves every provider uncalled. | `slopvac-8l4.11.3` |
| N12 | A model provider that is untrusted or absent from the config never starts. | `slopvac-8l4.9.6` |
| R1 | With `SLOPVAC_LOG=trace`, a run over a document with a unique sentinel string logs no copy of the sentinel from the text, matches, front matter, or terms. | `slopvac-8l4.12.1` |
| R2 | The same run over stdin logs `<stdin>` and no temporary path, in logs, errors, and panics. The 2.x tests in `test_cli.py` cover the output side. | `slopvac-8l4.12.9` |
| R3 | Paths inside the project root log relative to it. Paths outside log as `<external>/<file name>`. | `slopvac-8l4.12.1` |
| R4 | A token in `GH_TOKEN` and credentials in a registry URL appear in no log, error, or notice. | `slopvac-8l4.9.2` |
| C1 | With stdout piped, no format contains an escape byte. This extends the 2.x test for piped text. | `slopvac-8l4.12.2` |
| C2 | `NO_COLOR=1`, `--color never`, and `--no-color` each remove all escape codes, including bold and italic, even when `FORCE_COLOR=1` is set. | `slopvac-8l4.12.1` |
| C3 | `--color always` forces color on a pipe, and `--color` wins over `NO_COLOR`. | `slopvac-8l4.12.1` |
| C4 | Every severity and verdict in text output appears as a word. A snapshot test strips all escape codes and compares. | `slopvac-8l4.12.2` |
| C5 | `TERM=dumb` output uses ASCII borders and no cursor controls. | `slopvac-8l4.12.2` |
| H1 | The HTML report passes axe-core with no violations, has `lang="en"`, one `<h1>`, table captions and `scope`, and no remote resource. | `slopvac-8l4.12.2` |
| H2 | The report stylesheet meets the contrast ratios in section 2.3, computed from its variables in both schemes. | `slopvac-8l4.12.2` |
| V1 | Every published schema accepts its conformance instances and rejects the invalid ones. | `slopvac-8l4.2.19` |
| V2 | An artifact with a higher `schema_version` than supported fails with the code, the versions, and the upgrade hint. | `slopvac-8l4.4.5` |
| V3 | A user-written file with an unknown key fails with file, line, and column, and an `x-` key passes. A plugin message with an unknown field is ignored. | `slopvac-8l4.2.5`, `slopvac-8l4.2.6` |
| V4 | A handshake with no common protocol version, a missing required feature, or an unknown capability produces the behavior in section 3.4. | `slopvac-8l4.9.6` |
| V5 | A pack with an unsupported `slopvac_api` stays unloaded, and the error names both versions. | `slopvac-8l4.9.1` |
| V6 | Every error code in the generated docs is unique and kebab-case, and the list keeps every code of release 3.0.0. | `slopvac-8l4.19.1` |
| V7 | A 2.x config without `schema_version` produces the same findings in compatibility mode as after `slopvac migrate`, and prints `config-legacy-version` once. | `slopvac-8l4.4.5`, `slopvac-8l4.16.1` |
| V8 | Each 2.x setting listed in section 3.7 maps, or produces `config-legacy-dropped`. | `slopvac-8l4.2.5` |
| V9 | The Python SDK example plugin passes the conformance suite. | `slopvac-8l4.9.7` |

The Python 2.x tests that cover current behavior sit in `packages/slopvac-lint/tests/`:

- stdin redaction in text, JSON, and error output: `test_cli.py`;
- update-check opt-outs and machine-format suppression: `test_update_notice.py`;
- piped text output without escape codes, forced-terminal color codes, and `--no-color`: `test_cli.py`, added with this document.

`NO_COLOR` has no 2.x test, because 2.x ignores the variable (section 2.1).

## 5. Follow-up for bead owners

- `slopvac-8l4.12.1` owns the global `--offline`, `--color`, and `SLOPVAC_LOG` surface. Its description does not mention them yet.
- `slopvac-8l4.4.2` adds the `[network]` table and `[review] provider` to the config schema.
- `slopvac-8l4.4.5` says "one minor". Update it to the window in section 3.7.
- `slopvac-8l4.12.6` adds the preview and `--submit` behavior from section 1.5.
