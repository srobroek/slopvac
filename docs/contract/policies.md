# Slopvac 3.0 policies: network, accessibility and API lifecycle

Status: contract for 3.0. Bead `slopvac-8l4.2.12`. Plan: [slopvac-3.md](../design/slopvac-3.md).

This document sets three policies that the 3.0 binary, its schemas, and its plugin protocol must follow.

Paragraphs and bullets labeled **2.x behavior** describe `packages/slopvac-lint`, and each names the source file. Every other statement is a 3.0 requirement, and an owning bead follows it. The release-readiness gate (`slopvac-8l4.13.9`) lists this document and blocks on its conformance tests (section 4). An unowned requirement is a gap to close before the gate.

"Must" is a requirement on the 3.0 binary. "Network" means any connection outside the local machine, including DNS lookups and registry or API calls.

## 1. Network and privacy

### 1.1 Principles

1. `lint`, `validate`, `rules`, `explain`, `prime`, `reference`, and `claims` read local files only. The one exception is the background update check (section 1.2), which the opt-outs in section 1.3 disable.
2. Every network feature is a named command or hook in the table in section 1.2. No other code path opens a connection.
3. Document text, finding text, file paths, and rule hit counts stay local. The update-check request is the only usage-like traffic, and it carries no document data. Slopvac has no telemetry.
4. A failed or refused connection never changes a lint verdict. It prints an error, and it exits 2 (incomplete) only when the user asked for the network operation.
5. Slopvac has no prompts, so consent is an explicit command or flag. A flag such as `--yes` binds a command and cannot tell who ran it. The prime text therefore tells agents to get the user's approval of the previewed output first.

### 1.2 Inventory of network features

| Feature | 2.x behavior | 3.0 requirement | Owner |
|---|---|---|---|
| Update check | A detached process asks `https://pypi.org/pypi/slopvac/json` for the latest version and caches the result for 24 hours (`update_notice.py`). Any command except `prime` may start it. Machine-readable output or a report file prevents it (`cli.py`). It runs only when stderr is a TTY. | Check the registry that matches the install method (`update-informer`). Only `lint`, `doctor`, `prime`, and `self update` may start it. Cache the result for 24 hours. Show it in `prime`, in JSON `notices`, and in `--version --json`, so agents see it. | `slopvac-8l4.12.4` |
| `self update` | None. | Runs only for installs from the slopvac installer. It downloads the release archive, verifies the minisign signature, and then replaces the binary. | `slopvac-8l4.12.4`, `slopvac-8l4.13.3` |
| OCI plugin fetch | None. 2.x has no plugins. | `plugins sync`, `plugins update`, and `plugins publish` pull or push OCI artifacts. The client is hand-written on `ureq`. Initial support covers the documented GHCR flows (anonymous and basic tokens). `docker_credential` helpers extend this to other registries within the tested scope of the owning bead. | `slopvac-8l4.9.2`, `slopvac-8l4.9.3`, `slopvac-8l4.9.9` |
| Release-archive plugins | None. | `plugins sync` downloads a plugin archive over HTTPS and checks the digest that the lockfile pins. | `slopvac-8l4.9.3` |
| Git plugins | None. | A plugin pinned to a git commit clones during `plugins sync` only. | `slopvac-8l4.9.3` |
| Outdated check | None. | `plugins outdated` lists newer digests and versions from the pinned sources. | `slopvac-8l4.9.3` |
| Plugin index search | None. | `plugins search` fetches the signed first-party index from `oci://ghcr.io/slopvac/plugin-index` and each extra index that the project config names (`https://` or `oci://`), and verifies only the first-party one. Each index is cached in the per-user cache. A failed fetch shows the cache and exits 2, and offline reads the cache only ([plugin-index.md](plugin-index.md), sections 5 to 9). | `slopvac-8l4.9.8`, `slopvac-8l4.9.62` |
| Issue submission | `prime report` prints a workflow that tells an agent to run `gh issue create` after the user approves the exact post (`guidance.py`). The `gh` program connects. | `slopvac report` posts nothing itself. It prints the exact `gh issue create` command, and `--gh --yes` runs it through the GitHub CLI, which holds the login. Slopvac never reads a token. Without `gh`, the user opens a prefilled issue-form URL. Both paths need the consent step in section 1.5. | `slopvac-8l4.12.6` |
| Model-provider hooks | None. | A plugin that implements the model-provider hook may contact a model service. Slopvac core does not. Consent rules apply (section 1.5). | `slopvac-8l4.9.6`, `slopvac-8l4.11.3` |
| LSP server | None. | `slopvac lsp` talks to the editor over stdio and opens no connection. | `slopvac-8l4.12.7` |
| Code plugins in general | None. | A plugin process is a separate program, and 3.0 leaves its network access unsandboxed. The trust command (section 1.6) is the control. The threat model records the residual risk. | `slopvac-8l4.9.4`, `slopvac-8l4.9.11` |

Downloads at install time sit outside the binary. In this repository, `scripts/install_vale.py` downloads Vale for development, and 3.0 removes Vale (`slopvac-8l4.16.4`).

### 1.3 Offline mode and opt-outs

**2.x behavior.** The update check stops when any of these is true (`update_notice.py`, `_disabled_by_environment` and `_enabled`, and `cli.py`, `_machine_output`):

- the `CI` variable is set, with any value.
- `NO_UPDATE_NOTIFIER`, `SLOPVAC_NO_UPDATE_CHECK`, or `DO_NOT_TRACK` has a non-empty value.
- stderr is not a TTY.
- the command is `prime`, the format is not `text`, or `--out` or `--open` is present.

The environment variables above are the only switches in 2.x. Under `CI` or the other opt-outs, 2.x shows no notice either.

**3.0 requirement.** Offline mode blocks every row of section 1.2. These switches turn it on:

| Switch | Effect |
|---|---|
| `--offline` (global flag) | Offline for this run. |
| `SLOPVAC_OFFLINE=1` | Offline for every run in the environment. |
| `offline = true` under `[network]` in `slopvac.toml` | Offline for the project. |

Offline is sticky. If any source sets it, no other source can unset it, and no flag turns it off. This departs from the layer order of the plan, where a higher layer overrides a lower one.

In offline mode:

- A command that needs the network exits 2 with the code `offline-network-needed` and the message `offline: <command> needs the network`. It does not retry or fall back.
- Plugins that the lockfile pins and that sit in the local cache load normally.
- A plugin missing from the cache exits 2 with the code `offline-plugin-missing`. The message names the plugin and the digest.
- `plugins sync` succeeds from the cache alone. It verifies digests against `.slopvac/plugins.lock` and reports each missing plugin.
- `plugins search` opens no connection and reads the index caches only. An index with no cache gets `offline-network-needed` and the run exits 2, with no results at all when no selected index has a cache ([plugin-index.md](plugin-index.md), section 9).

These opt-outs apply to the update check only:

| Switch | Effect |
|---|---|
| `NO_UPDATE_NOTIFIER`, `SLOPVAC_NO_UPDATE_CHECK`, `DO_NOT_TRACK` | Same as 2.x. |
| `update_check = false` under `[network]` | Project-level opt-out. |
| `CI` | No background check and no notice, as in 2.x. |

Owners: `slopvac-8l4.12.1` for the global flag and environment, `slopvac-8l4.4.2` for the config keys, `slopvac-8l4.12.4` for the update check.

### 1.4 CI defaults

- Slopvac detects CI from the `CI` variable, as 2.x does.
- In CI the update check stays off.
- No code path prompts, in CI or anywhere else.
- `plugins sync` in CI runs from the lockfile. It fails with exit 2 when the lockfile is missing or a digest differs, and it leaves the lockfile as it found it.
- A GitHub Action run that needs plugins runs `plugins sync` as a separate, named step. The lint step runs with `--offline`.

Owners: `slopvac-8l4.9.3` for lockfile behavior, `slopvac-8l4.13.6` for the Action.

### 1.5 Consent

Two features need consent beyond installing slopvac: issue submission and model-provider hooks.

**Issue submission.**

- `slopvac report` prints the exact title and body it would file, then exits. Filing needs `--gh --yes`.
- The body omits local paths, file names, user names, host names, repository names, and organization names. The body includes document text only when the user passes `--include-text <file>`, and the preview shows that text.
- Environment fields come from the CLI, never from environment variables, as `CONTRIBUTING.md` requires for agent reports.
- `slopvac report <category> --title TEXT --field ID=VALUE ...` builds the report from the issue form of that category. The field ids are the form ids, and a missing required field exits 2 with the code `report-incomplete`. Document text comes only from `--include-text FILE`, which reads a regular UTF-8 file of at most 256 KiB.
- Every field goes through a scrub before the preview: the working directory, the home directory, the user name and the host name, path-shaped words (Unix, drive and UNC paths, and relative paths), file names, repository and organization names on GitHub, GitLab and Bitbucket URLs (the slopvac repository stays), GitHub tokens (also when a line break splits one), the value of every `Authorization` header, `Bearer`, `Basic`, `Token` and `Digest` credentials and URL user-info. Percent-escapes in a repository URL are decoded before the check, and only a URL host, a leading host or an scp-style `git@host:` counts as a forge address. Document text gets the exact-string and secret steps only, so the sample stays intact.
- `--body-file FILE` writes the previewed body to `FILE`. The name `-` is refused with `report-body-file`, because `gh` reads it as standard input; `./-` names a file. The write goes to a temporary file in the same directory and then renames over `FILE`, so a reader never sees half a body.
- `--gh` requires `--body-file` and prints the command `gh issue create -R github.com/slopvac/slopvac --title TITLE --body-file FILE`, with each word quoted for a POSIX shell. `gh` has no title-file option, so the title is a quoted argument. The host and repository are constants in the binary. No flag or config key changes them, and slopvac clears `GH_HOST` and `GH_REPO` from the environment of `gh`. A body path that is not UTF-8, or that holds a control character, cannot be printed in the command, so `--gh` exits 2 with `report-body-file`.
- `--gh --yes` runs that command after the preview. Slopvac finds `gh` by a plain lookup in the directories of `PATH`, so a `gh` earlier on `PATH` wins; the threat model records this as a residual risk. It starts `gh` with an argument list and no shell. It first runs `gh auth status --hostname github.com`. When `gh` is missing, the command exits 2 with `report-gh-missing`. When the login check fails, it exits 2 with `report-gh-not-logged-in`. When `gh issue create` fails or runs longer than 60 seconds, it exits 2 with `report-gh-failed`. Slopvac never reads, stores or logs a token, and it prints none of the output of `gh` except the issue URL. Offline mode makes `--gh --yes` exit 2 with `offline-network-needed` before anything is written or printed. `--gh` alone is offline-safe.
- Without `--gh`, the command is offline-safe and prints a prefilled issue-form URL. `--open` starts the browser, except in offline mode, where the URL is only printed.
- The preview shows the target, the title and the body, and no labels, because `gh issue create` would not apply them. The prefilled-form path prints the labels the issue form sets (the category label and `needs-triage`). The form never sets `agent-reported`, so the command never promises it.
- `report` reads no token and no secret from the environment. The scrub works on the supplied text and on the working directory, home directory, user name and host name only.
- A control character other than a tab or a newline in the title, a field or the document sample is refused with `report-invalid` (a CRLF pair becomes a newline first). Text with an escape sequence could otherwise act on the terminal that shows the preview. The error does not echo the text.
- An unknown `--field` id is not echoed back.
- The scrub is best effort and never refuses a report. After it runs, a check over the title, each field, the document sample and the body looks for text that may still hold a credential or private data. For each hit it prints a warning on stderr that names only the field and the kind (``warning: possible credential in field `steps`: review it before posting``), never the matched text. The check looks for a GitHub token prefix (also when whitespace splits it), a long mixed letter-and-digit run, an `Authorization` line (also when folded), `Basic`, `Bearer`, `Token` or `Digest` followed by a credential, a forge address other than `slopvac/slopvac` (after decoding escapes, ignoring a trailing dot in the host and resolving `..`), an absolute path, and the working directory, home directory, user name and host name. It also checks the text as typed, before the scrub, because a partial scrub can leave a fragment. Placeholders such as `<token>` and ordinary prose such as `Basic authentication.` draw no warning. The warning does not stop the run, so the reader of the preview decides.
- A usage error for `report` (a bad category or argument) does not echo what was typed.
- The URL carries the title and every answer that fits in 7000 bytes, keyed by form id. It carries no labels, because GitHub answers 404 when the reader may not set them, and the form sets them. Checkboxes stay unticked. The preview names any field that did not fit. A title over 200 characters is refused.
- The issue forms in `.github/ISSUE_TEMPLATE` are generated from the field definitions in `crates/slopvac/src/report/fields.rs`. A test regenerates them and fails on any difference.
- 2.x already requires the agent to get the user's approval of the exact post (`guidance.py`, the `prime report` workflow). 3.0 keeps that rule in the prime text and adds the command-level guard above.

**Model-provider hooks.**

- A model provider is a plugin. It stays off until the user runs `slopvac plugins trust` for it and names it in `slopvac.toml` under `[review] provider`.
- Slopvac sends a provider only the text that the review type needs: changed claims for fact checking, the changed passages for `update`, and the whole document for `rewrite`. `slopvac review --dry-run` prints the exact payload without calling the provider.
- During `lint`, every provider stays idle.
- In offline mode no provider call happens, even for a trusted provider.
- The reviewer model must differ from the author model. Slopvac cannot verify this for a provider it does not control. The check compares the model names that the config and the provider report.

Owners: `slopvac-8l4.12.6`, `slopvac-8l4.9.6`, `slopvac-8l4.11.3`.

### 1.6 Trust and signatures

- The plugin host refuses to load a code plugin until its content hash is trusted. A hash change revokes trust.
- `slopvac plugins trust` records trust. `sync`, `update`, and flags such as `--yes` never record it.
- CI has one explicit exception: the `SLOPVAC_TRUST` environment variable, which `slopvac-8l4.9.4` defines. A person writes it into the CI configuration, and it names what to trust. It is configuration, not a prompt, and no tool sets it on its own.
- OCI artifacts carry minisign signatures as manifest layers. Slopvac verifies the signature before extraction, and a missing or invalid signature makes `sync` fail with exit 2.
- Release archives verify against the release signature (`self update`).
- The binary compiles in two keys. The release key signs release archives and the revocation list, and it is the revocation root. The plugins key signs first-party plugins in the `slopvac` namespace and the first-party plugin index. The release key can revoke the plugins key ([plugins.md](plugins.md), section 10).
- The namespace `slopvac` verifies against the compiled plugins key only, and no user pin applies to it. `core` is reserved for the built-in plugin and fails closed ([plugins.md](plugins.md), section 9).
- Local folders and git commits carry no signature. A git pin names a commit, and the trust hash covers the content.

Owners: `slopvac-8l4.9.4`, `slopvac-8l4.9.5`, `slopvac-8l4.9.11`.

### 1.7 Logging and redaction

**2.x behavior.** Slopvac has no logging framework and no log file. Two redactions exist:

- Slopvac stages `--stdin` input in a temporary file. Every report shows the path as `<stdin>`, and the temporary directory name never reaches output (`pipeline.py`, `redact_stdin`). Tests in `packages/slopvac-lint/tests/test_cli.py` cover text, JSON, and error output.
- The update-check cache stores the check time and the latest version string.

**3.0 requirement.**

- Logging uses `tracing` and stays off until `SLOPVAC_LOG` is set. Log output goes to stderr, and no log file exists.
- Logs never contain document text, finding text, matched spans, front matter values, or terms.
- Logs record document paths relative to the project root. A path outside the root appears as `<external>/<file name>`. Stdin appears as `<stdin>` everywhere, including logs, panics, and error chains.
- Logs never contain tokens, `Authorization` headers, or URL credentials. Before it logs a URL, slopvac strips the user-info part.
- Rule IDs, plugin IDs, digests, durations, and counts may appear in logs.
- Panic and error output follow the same rules.
- `SLOPVAC_LOG=trace` lifts none of these rules.

Owners: `slopvac-8l4.12.1` for the logging setup, `slopvac-8l4.12.9` for stdin.

### 1.8 Data written to disk

- Caches and state go to the per-user directories that `etcetera` reports. `SLOPVAC_CACHE_DIR` overrides the cache location, as in 2.x (`vale_cache.py`).
- Code that needs to serialize writers takes an exclusive lock through standard-library file locking, on a separate guard file next to the data. It does not lock the data file. A lock is separate from the write.
- An atomic write replaces a file through a new temporary file in the same directory. Slopvac syncs that file to disk, checks that it is still the file it created, renames it over the target, and then syncs the directory. The write itself takes no lock.
- Slopvac writes only to the cache directory, the project's `.slopvac/` directory, and paths the user names. For example, `slopvac migrate` keeps its backup of the files it changes in `.slopvac/migrate-backup/<UTC timestamp>/` inside the project. Its record of that backup stays in the per-user cache.

Owners: `slopvac-8l4.9.3`, `slopvac-8l4.9.4`.

### 1.9 Input size caps

**3.0 requirement.** Every entry point that reads text enforces a size cap before it hands the text to a parser, an index or a matcher. An input over its cap is refused whole, and its text never reaches a parser. The run is incomplete and exits 2, and the error or notice carries the stable code from the table.

The span crates index text with 32-bit offsets and size their structures from its length, and they do not cap their input. Their documentation states the 64 MiB limit as a rule for callers. Memory per read stays bounded by the cap plus one byte, because the reader stops at the cap.

| Entry point | Cap | Code | Why this value |
|---|---|---|---|
| Document: CLI file lint, `validate` documents, `cases --coverage` corpus files, `fix` | 64 MiB | `document-too-large` | The largest size every span crate accepts. A real document is a few hundred KiB. |
| Document from stdin | 64 MiB | `document-too-large` | Same as a file. |
| Document in the language server (`didOpen`, `didChange`), per document | 64 MiB | `document-too-large` | Same as a file. The server drops the document and publishes the notice instead of findings. |
| Document read for `migrate` | 64 MiB | `document-too-large` | Same as a file. |
| Changed file read for `--diff` scoping | 64 MiB | `document-too-large` | Uses the same constant as the lint read. |
| Config file (`slopvac.toml`, each `extends` file, a 2.x config read by `migrate`) | 1 MiB | `config-too-large` | A real config is under 10 KiB. The shipped data files stay under 32 KiB. |
| Rule or category file in a plugin | 2 MiB | `rules-file-too-large` | The largest shipped rule file is about 130 KiB. 2 MiB leaves more than a tenfold margin. |
| Authored pattern in a rule, category or tagger file of a plugin | 8,192 bytes | `rules-pattern-too-long` (rules and categories), `tagger-pattern-too-long` (taggers). A tagger pattern over the cap is refused the same way as a rule pattern. | The longest shipped pattern is 5,709 bytes (`ste-procedural.condition-after-command`). 8,192 leaves room for it to grow while a padded or generated list is still refused, and compile cost grows with length (threat model X3). Generated and locale-built patterns keep the 64 KiB compile limit. |
| Style file | 1 MiB | `style-too-large` | The built-in styles are a few KiB. |
| Update-check policy read (`slopvac.toml`, read before argument parsing) | 1 MiB | `update-policy-too-large` | Same value as the config file. The read covers two keys, and a real file is under 10 KiB. |
| House-style detection read (`.vale.ini`, `STYLE.md`, `_STYLE.md`, `CONTRIBUTING.md`) | 1 MiB | `style-detect-file-too-large` | A real style note is a few KiB. Detection skips a larger file and does not fail. `slopvac init` reports the skipped file as an info notice with this code, naming the file by its root-relative label. |
| Terms file | 1 MiB | `terms-file-too-large` | The built-in terms file is about 30 KiB. |
| Lockfile (`.slopvac/plugins.lock`) | 1 MiB | `update-failed` | A real lockfile holds a few hundred bytes for each plugin. The reader checks the size before it parses TOML. `plugins update` reports `update-failed`, and `slopvac doctor` reports the lockfile as `unreadable`. The lockfile has no code of its own. It also holds at most 1,000 plugins and 256 `requires` entries for each plugin, and an entry whose canonical text would pass the cap is refused when the lockfile is built. |

A per-file cap does not bound the work of many files, or of a long list in one file. Aggregate budgets bound it, and the same error rules apply: the input is refused whole, the run is incomplete and exits 2. Each refusal carries `data.budget`, the name of the budget that tripped, `data.limit`, the limit in the unit below, and `data.path`, the config file, plugin directory or document at which it tripped, relative to the root, or `<external>/<file name>` outside it. For `rule-entries`, `data.path` is the rule file. The list of `data.budget` values can grow. A message names only that path and the limit.

| Entry point | Budget (`data.budget`) | Limit | Unit | Code | Why this value |
|---|---|---|---|---|---|
| `extends` nesting, from the nearest config down | `extends-depth` | 32 | levels | `config-budget-exceeded` | A real chain is two or three levels. |
| `extends` graph, files applied | `extends-files` | 256 | files | `config-budget-exceeded` | A real graph has fewer than ten files. A file that more than one file extends counts once for each time it applies, because it applies each time. |
| `extends` graph, bytes read | `extends-bytes` | 8 MiB | bytes | `config-budget-exceeded` | A real graph is under 100 KiB. Eight files at the 1 MiB cap fit. |
| `extends` graph, bytes of config applied | `extends-applied-bytes` | 64 MiB | bytes | `config-budget-exceeded` | A real graph applies under 100 KiB. A file that more than one file extends counts its size once for each time it applies, so 64 MiB stops a small graph from repeating a large file hundreds of times. |
| Plugin directory, rule and category files | `plugin-files` | 256 | files | `rules-budget-exceeded` | The built-in core has 23 files. |
| Plugin directory, entries of any kind | `plugin-entries` | 1024 | entries | `rules-budget-exceeded` | Bounds directory scanning before the loader resolves any file. |
| Plugin directory, bytes read | `plugin-bytes` | 32 MiB | bytes | `rules-budget-exceeded` | The built-in core is about 450 KiB. |
| Context tags on one document | tags | 1 per 64 bytes of the document, plus 65,536 | tags | context-budget-exceeded | At the 64 MiB document cap, the limit is about 1.1 million tags, an index of about 200 MiB. The densest measured prose holds about 1 tag per 44 bytes, so a document that dense and larger than about 9.5 MB is refused. The cap stops a document made of many short sentences from building an index of gigabytes. |
| Context lookups on one document | tag-lookups | 8 per byte of the document, plus 16,384 | looks | context-budget-exceeded | A document with a few tags on a few cells looks at a few tags for each match. Many tag kinds on one cell, with rules that match across its lines, make the looks grow with kinds times matches. |
| Rule, tokens or substitutions listed | `rule-entries` | 4096 | entries | `rules-budget-exceeded` | The longest shipped list has 112 entries. 4096 is a margin of more than thirty. The loader checks it before it compiles the matcher. |
| Config file, `[[genres]]` and `[[overrides]]` blocks together | `file-blocks` | 256 | blocks | `config-budget-exceeded` | A real config has fewer than ten. Each block compiles a glob matcher, and the 1 MiB file cap alone allows tens of thousands. The loader checks it before the schema check. |
| Config, extra indexes | `index-extra` | 16 | indexes | `config-budget-exceeded` | A real project lists one or two. Each entry is one more host that `plugins search` contacts. The default index does not count. The loader checks it per file before the schema check, the duplicate-name check and any fetch, so it also holds for every file in an `extends` chain. |

How the budgets apply:

- A config file that more than one file extends is read and parsed once. The loader shares that parsed copy between its applications, so the order of settings and their provenance do not change.
- The `extends` counters differ on purpose. Files applied counts every application, and so bounds the merge work. Bytes read counts each read once, and so bounds the I/O. Bytes applied counts every application by size, and so bounds the settings the result holds.
- An extended file whose ancestor is still waiting to apply counts against the file budget. The loader checks the depth of a reused subtree at each place it applies again, and checks every budget before it adds an application.
- An `extends` cycle is not a budget. It keeps `config-extends-cycle`, and the loader checks for a cycle before it checks the depth.
- A rule file reached by more than one name, such as a symlink, loads once under the first name in file-name order, and the file budget counts it once.
- The plugin loader reads and compiles one file at a time.
- Duplicate checks on lists (unique tokens, unique substitution keys, blocks with the same `files`) use hash lookups, so their cost grows linearly with the list and a long list of distinct items is not a quadratic cost.

Code changes that touch a cap record the new value here in the same change. The reader constants live in `slopvac-fs` (`MAX_DOCUMENT_BYTES`), `slopvac-config` (`MAX_CONFIG_BYTES`), `slopvac-update` (`MAX_CONFIG_BYTES`), `slopvac-rules` (`MAX_RULE_FILE_BYTES`) and `slopvac-styles` (`MAX_STYLE_BYTES`, plus a private cap in house-style detection) and `slopvac-plugins` (`MAX_LOCK_BYTES`).

The CLI file and stdin reads enforce their cap and report `document-too-large` with exit 2. The language server and `migrate` document reads, and the `migrate` config read, enforce theirs in a later change. Every other row is enforced. A `fix` refusal for an oversized file carries the code through `Refusal::code`, and a `--diff` scoping read fails with `DiffError::FileTooLarge`. The `lint` command does not yet pass `--fix` or `--diff-base` to the engine. When it does, it reports both with `document-too-large`.

A capped file read opens the file without blocking and accepts only a regular file. A FIFO, device, socket or directory at the path is refused at once, so a repository entry cannot hang a run. The refusal reports through the entry point's existing read-failure error, such as `input-unreadable` for a document, and not through a new code. Stdin is the exception: it reads a pipe by design.

Every read in the table below reports a refusal as one of the kinds listed. Each such refusal exits 2. The advisory house-style detection read is the exception: it skips a file it cannot read and does not fail (see its row in the cap table).

| Input kind | Over the cap | Every other refusal |
|---|---|---|
| Document | `document-too-large` | `input-unreadable`, or `input-not-utf8` when the bytes are not UTF-8 |
| Config file | `config-too-large` | `config-io` |
| Rule or category file | `rules-file-too-large` | No dedicated code yet. |
| Style file | `style-too-large` | No dedicated code yet. |
| Terms file | `terms-file-too-large` | `terms-io` |

The refusal kinds are `unsafe-path`, `not-found`, `symlink`, `not-regular`, `multiply-linked`, `io`, `not-utf8` and `too-large`. The list can grow in a later 3.x release.

Reserved for a later 3.x release, and not emitted yet: the codes `rules-file-unreadable` and `style-unreadable` for the cells above with no dedicated code, `terms-file-unreadable` as a possible later name for `terms-io`, and a `data.reason` key on every refusal that carries the kind as one of the strings above. Until they are emitted, consumers branch on the codes in the table.

Output and protocol caps are separate and already hold: plugin frames 16 MiB, reStructuredText converter output 16 MiB, and fixer edits 1 MiB.

Owner: `slopvac-8l4.21.8`.

### 1.10 Registry credentials

**3.0 requirement.** Slopvac does not discover registry logins from the project's configuration. It reads them from the user's environment and home directory, and from the credential files that environment variables select, such as `REGISTRY_AUTH_FILE`. It does not exclude a project path from those files. A credential helper is the exception: slopvac starts one only from a trusted directory outside the project. Three environment variables supply a login:

| Variable | Use | Sent to |
|---|---|---|
| `SLOPVAC_OCI_USER` and `SLOPVAC_OCI_TOKEN` | A username and a token. Both must be set, and a lone one is ignored. | The registry that the request goes to, and the token endpoint that the client accepts for it: the registry's own origin, or Docker Hub's `auth.docker.io`. |
| `GITHUB_TOKEN` | A token for `ghcr.io`, sent with the username `slopvac`. | `ghcr.io` only, including its token endpoint on `ghcr.io`. For every other registry the token is not used. |

The order, with the first match winning:

1. `SLOPVAC_OCI_USER` with `SLOPVAC_OCI_TOKEN`.
2. `GITHUB_TOKEN`, for `ghcr.io`.
3. A static `auths` login in the Docker config (`$DOCKER_CONFIG/config.json`, else `~/.docker/config.json`).
4. A static `auths` login in the first of these container auth files that exists: `$REGISTRY_AUTH_FILE`, `$XDG_RUNTIME_DIR/containers/auth.json`, then `$XDG_CONFIG_HOME/containers/auth.json`, which is `~/.config/containers/auth.json` when `XDG_CONFIG_HOME` is unset. Slopvac reads only that one file.
5. The credential helper that the Docker config names, found only in trusted directories (section 3.5, `credential-helper-untrusted`).
6. No login.

Section 1.7 keeps the values out of logs and errors. The `Debug` form of a credential prints `<redacted>` for the secret. The order comes from `crates/slopvac-plugins/src/oci/auth.rs`.

## 2. Accessibility

### 2.1 Plain and no-color output

**2.x behavior.**

- Text output goes through a `rich` console. Rich drops styling when stdout is not a terminal, so piped output carries no escape codes (`cli.py`, `_console`). `test_cli.py` tests this.
- `lint --no-color` removes color codes. A test checks that no color code appears. In a forced terminal, bold and italic codes remain, and no test covers that.
- JSON, SARIF, and GitHub annotations contain no terminal escape codes.
- 2.x ignores the `NO_COLOR` variable. `_console` passes `no_color=False`, which overrides the variable that `rich` would read. The 2.x line ends at release 2.18.1, so the defect stays in 2.x.

**3.0 requirement.** Slopvac resolves color once, in this order:

1. `--color never|always|auto` (default `auto`) wins when given.
2. A non-empty `NO_COLOR` means `never`.
3. A non-empty `CLICOLOR_FORCE` or `FORCE_COLOR` means `always`.
4. Otherwise, color is on if stdout is a terminal and `TERM` is not `dumb`.

`--no-color` stays as an alias for `--color never`.

When color is `never`, output also drops bold, italic, underline, and cursor controls. Tables use ASCII borders when `TERM=dumb` or when the locale is not UTF-8.

Owners: `slopvac-8l4.12.1` for the flags, `slopvac-8l4.12.2` for the renderers.

### 2.2 Text that does not depend on sight

- Words carry every signal, and color only reinforces them. Every severity, verdict, and status appears as a word.
  - 2.x text output prints `PASS`, `FAIL`, and `UNCHECKED` (`pipeline.py`).
  - 2.x HTML prints `PASS`, `FAIL`, the severity word of each finding, and a heading that counts the checks that did not run (`html.py`).
- Each finding prints on its own line in the form `path:line:column severity rule-id message`, so a screen reader reads the location first.
- Text output has no spinners, progress bars, or animation. Progress goes to stderr. It appears only if stderr is a terminal and color is not `never`.
- Symbols and emoji carry no meaning. Box-drawing characters are decoration, and each table row also reads in order as plain words.
- When color is `never` and stdout is not a terminal, the renderer adds no alignment padding and inserts no hard line breaks into messages.

Owner: `slopvac-8l4.12.2`.

### 2.3 Accessible HTML report

**2.x behavior** (`html.py`):

- The page sets `lang="en"`, has a `<title>`, and puts content in `<main>`.
- Tables use `<th>` header cells. File details use `<details>` and `<summary>`.
- The verdict and the severity of each finding appear as text.
- The stylesheet respects `prefers-color-scheme`. Computed from the stylesheet variables with the WCAG relative-luminance formula, the status and muted text colors reach at least 4.87:1 against their panel in the light scheme. In the dark scheme they reach at least 5.26:1.
- The `_e` function escapes text from user content or findings: paths, notes, messages, rule IDs, replacements, the timestamp, and the version. The verdict and band words come from constants, and the statistics are numbers, so nothing escapes them.

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
- The HTML report sets `lang="en"`.

Owners: `slopvac-8l4.12.1` for CLI messages, `slopvac-8l4.4.7` for config diagnostics, `slopvac-8l4.12.2` for the HTML report.

## 3. API lifecycle

### 3.1 Versioned surfaces

| Surface | Version field | Where it lives | Schema | Owner |
|---|---|---|---|---|
| Lint JSON report | `schema_version` (integer) | Report root | `lint-report` | `slopvac-8l4.2.2` |
| Config file | `schema_version` (integer) | `slopvac.toml` root | `config` | `slopvac-8l4.2.5` |
| Front matter block | `v` | `slopvac:` key | `frontmatter` | `slopvac-8l4.2.5` |
| Rule, category, style, genre, and terms files | `schema_version` (integer) | File root | One per artifact | `slopvac-8l4.2.3`, `slopvac-8l4.2.4` |
| Plugin manifest | `slopvac_api` (integer) | `slopvac-plugin.toml` | `plugin-manifest` | `slopvac-8l4.2.4` |
| Lockfile | `schema_version` (integer) | `.slopvac/plugins.lock` | `plugins-lock` | `slopvac-8l4.2.4` |
| Plugin protocol | `protocolVersion` (integer) | `initialize` request and response | `plugin-protocol` | `slopvac-8l4.2.6` |

The shared definitions are `SchemaVersion` and `ApiVersion` in `schemas/v3/common.schema.json`. The scaffold bead `slopvac-8l4.2.19` freezes their shape, and `slopvac-8l4.2.12` owns their meaning (section 3.2).

### 3.2 `schema_version` and `slopvac_api`

**2.x behavior.** `LintReport.schema_version` defaults to 1. The docstring in `report.py` states the rule: it changes only when a key is removed or retyped, and adding a key does not bump it. The report has a separate `version` key for the tool version. `doctor --format json` has its own `schema_version` of 1 (`doctor_report.py`). 2.x config files have no version field, and `extra="forbid"` rejects unknown keys (`config.py`). The 2.x function `update_notice.upgrade_hint` returns an install-method command such as `uv tool upgrade slopvac`, `pipx upgrade slopvac`, or `pip install -U slopvac`.

**3.0 requirement.**

- `SchemaVersion` is a positive integer. It counts breaking changes to one artifact's shape and has no minor or patch part.
- Every root instance of a versioned artifact carries `schema_version` with the constant 3. Lint JSON jumps from 1 to 3 so that all artifacts share one number at first. The migration guide states this jump. A later breaking change raises only the number of the artifact it affects, so numbers can diverge after 3.0.
- Changes within one `schema_version` are additive only. Section 3.9 describes the check that enforces this.
  - Allowed: a new optional field, a new optional section, and a new value of an output-only enum that the schema marks as extensible.
  - Not allowed: removing or renaming a field, changing a type, tightening a constraint, or giving a field a new meaning.
- A schema's `$id` never changes within a version. The published URL has the form `https://slopvac.github.io/slopvac/schemas/v3/<artifact>.schema.json`.
- `ApiVersion` is a positive integer for the plugin extension API. The first plugin manifest declares `slopvac_api = 1`. It names the host capabilities a plugin needs. `schema_version` names the shape of one file. The two are independent.
- The binary version is independent of both. A release that adds optional fields keeps `schema_version`. `slopvac --version --json` lists the binary version, each supported `schema_version`, and each supported `slopvac_api`.
  - `schema_versions` is an object. Each key is the name of a versioned artifact's schema under `schemas/v3`, without `.schema.json`. Each value lists the `schema_version` numbers the binary reads or writes for that artifact.
  - The artifacts are `blocklist`, `category`, `config`, `doctor-report`, `genre`, `lint-report`, `plugins-lock`, `style`, `tagger` and `terms`. The list grows when the binary starts to read or write another versioned artifact, such as a plugin manifest, a plugin index or a standalone rule file. Adding a key, or a number to a list, is additive. Removing either is a breaking change.
  - `slopvac_api` is a list of the extension API numbers the binary supports.
  - The same document also carries `name`, `version`, `install_method` and `notices`.
- A config file without `schema_version` is a 2.x config and is rejected (section 3.7). Any other 3.0 artifact without a version is an error.
- A version higher than the binary supports is an error. The message names the file, the version found, and the versions supported. It also prints the upgrade command for the install method, built as `upgrade_hint` builds it in 2.x.

Owners: `slopvac-8l4.2.12` for the semantics, `slopvac-8l4.4.5` for the config version check.

### 3.3 Unknown-field handling

The rule depends on who wrote the file.

| Reader | Writer | Unknown field | Reason |
|---|---|---|---|
| Slopvac | A user (config, front matter, rules, plugins) | Error with file, line, and column, plus the nearest valid key | A misspelled key would silently disable a setting. 2.x already forbids unknown keys. |
| Slopvac | A plugin (protocol messages) | Ignored, logged at debug level | A plugin can be newer than the host within one API version. |
| A consumer of slopvac output | Slopvac | The consumer must ignore it | Additive changes do not bump `schema_version`. |
| A plugin | Slopvac (protocol messages) | The plugin must ignore it | Same reason. |

Authors who attach their own data to a user-written file put it under a key with the prefix `x-`. Slopvac ignores `x-` keys wherever it forbids unknown keys and never gives one a meaning. Each artifact schema records this rule in its `description`.

The schema marks which output enums can gain values. Consumers must tolerate new values of those enums.

Owners: `slopvac-8l4.2.3`, `slopvac-8l4.2.4`, `slopvac-8l4.2.5`, `slopvac-8l4.2.6`.

### 3.4 Capability negotiation

The plugin protocol follows LSP. The `initialize` request carries the host's `protocolVersion`, its supported hook points, and its feature flags. The response carries the plugin's `protocolVersion`, the hooks the plugin implements, and the features it needs.

- The host picks the highest protocol version that both sides support. With no common version, the host does not load the plugin and prints both version lists.
- The host calls only the hooks that the plugin declared.
- If the host lacks a required feature, the load stops with an error that names the feature. The host skips an optional feature it lacks.
- Both sides ignore unknown capability names (section 3.3).
- A data plugin has no handshake. The host compares `slopvac_api` with the range it supports. It loads the plugin only if the value is in range.

The plugin protocol bead defines the message shapes.

Owners: `slopvac-8l4.2.6`, `slopvac-8l4.9.6`, `slopvac-8l4.9.1`.

### 3.5 Error codes

**2.x behavior.** The CLI exit codes are 0 (pass), 1 (a gate failed), and 2 (the run was incomplete) (`contract.py`). Exit 2 means the result cannot establish a pass. 2.x messages have no stable codes.

**3.0 requirement.**

- The exit codes keep their meaning. Slopvac uses no other exit code.
- Exit 2 (incomplete) means slopvac did not read or did not check part of the input: a file refused over a cap or budget, a file that is malformed or unreadable, or content the engine could not extract. Those notices are warnings. In 3.0, a notice that lists active rules the engine did not run on input it did read (`rule-kind-not-implemented`, `comment-rules-not-run`) is an info notice: the run stays complete and exits 0, and the notice names the rules in `data.rules`. A warning notice that is not about unread or unchecked input, such as `config-unknown-rule`, leaves the run complete.
- Every error and notice has a stable `code`: a lowercase kebab-case string such as `config-unknown-key` or `plugin-api-unsupported`. The code appears in brackets in text output, in JSON `notices` and errors, and in the generated documentation. Until the generated reference ships, the tables in this contract are the list of codes.
- The `report` command uses these codes, and each exits 2: `report-incomplete` (a required form field is missing), `report-body-file` (the `--body-file` path is refused or cannot be written), `report-gh-missing` (`gh` is not found), `report-gh-not-logged-in` (`gh` is not logged in to github.com), `report-gh-failed` (`gh issue create` failed or ran longer than 60 seconds), `report-invalid` (a title, field or sample holds a control character) and `report-sample-unreadable` (the `--include-text` file cannot be read).
- No code is reused, and no code changes meaning. A code that stops occurring stays in the documentation, marked retired.
- Registry logins have two codes. Slopvac asks for a login only when a registry demands one.
  - `credential-helper-untrusted`: the credential helper exists only in a directory that is not trusted (section 1.7 paths: relative to the project, or `<external>/<name>`). Slopvac leaves the helper unstarted and sends the request without a login. When the registry allows that, the run continues and the log carries a warning. When the registry demands a login, the operation fails with this code and exits 2. The user tightens the permissions of the directory or signs in with a static `auths` login or the environment variables.
  - `credential-helper-project-unknown`: the caller did not name the project, so no helper starts. The credential constructors take the project, so only a caller that builds the credentials by hand can reach this code, and a user cannot. It is an internal invariant, with the same outcome.
- Plugin protocol errors use the JSON-RPC 2.0 error object. Its numeric `code` follows the JSON-RPC ranges, and `data.slopvac_code` carries the string code. The protocol bead defines the numeric range.
- Extractors share four codes. `extract-unsupported` covers unsupported content inside a supported input, such as a diagram type that no extractor reads. It is an `info` notice at the root of the report and exits 0, because the input is valid. Skipped content counts toward no score or gate, and the report shows that it was skipped. `extract-malformed` and `extract-budget` are `warning` notices in `unchecked` and exit 2, because the result cannot establish a pass. A broken diagram of a type slopvac reads is malformed, and an unknown type in a recognized fence is unsupported. `extract-output-invalid` belongs to first-party extractors. The failed output of a third-party plugin is `plugin-output-invalid`.
- Three cases exit 2 although the input may be valid: a whole input that the user names in a format slopvac does not read (EPUB, PDF), an encrypted or password-protected container, and a file whose name promises source but holds none (`.drawio.png`, `.excalidraw.png`, `.drawio.svg`; the code is `binary-no-source` for a binary file). A plain PNG or SVG with no source is info and exits 0.
- Three document-level `unchecked` entries cover a whole input. Each makes the run exit 2:
  - `input-unreadable`: the reader refused the file or could not read it.
  - `input-not-utf8`: the bytes are not valid UTF-8.
  - `input-unsupported`: no reader handles this input kind. This includes a whole input that the user names in a format slopvac does not read, such as EPUB or PDF. Slopvac has no separate code for binary inputs.
- When one `lint` or gate run holds both an incomplete input and a failed gate, exit 2 wins over exit 1. An incomplete run cannot establish its own result, and the report still lists the failed gates. This rule is for lint and gate results. The case runner orders its exits the other way: it exits 1 when any case fails, otherwise 2 when a check was incomplete, otherwise 0.
- The engine emits these notice codes, each at the level shown. A warning makes the run incomplete and exits 2. An info notice leaves the run complete and exits 0:

  | Code | Level | Meaning |
  | --- | --- | --- |
  | `rule-kind-not-implemented` | info | Active rules of a kind the engine does not run did not run. `data.rules` lists them. |
  | `rule-style-not-implemented` | warning | Active capitalization rules did not run, because the engine runs only the sentence style. |
  | `vocabulary-no-blocklist` | info | Active vocabulary rules did not run, because no word blocklist is set. |
  | `vocabulary-no-taggable-entries` | info | Active vocabulary rules did not run, because the blocklist holds no noun, verb, adjective or adverb entry of three or more letters. |
  | `vocabulary-sweep-shared` | info | Several vocabulary rules share one blocklist sweep, and it runs once under one of them. |
  | `rst-converter-missing` | warning | The reStructuredText converter or its Python interpreter is missing, so the file was not checked. |
  | `rst-unchecked` | warning | The converter failed on the file, so it was not checked. |
  | `rst-prose-unplaced` | warning | Some reStructuredText nodes have no usable source lines, so their prose was not checked. |
  | `rst-line-precise` | info | Some reStructuredText blocks could not be matched word by word, so findings in them point at the whole block. |

- Message text can change in any release. Codes, rule IDs, and exit codes form the interface.
- A `fix` refusal carries its code through `Refusal::code`: `document-too-large`, `fix-outside-root`, `fix-symlink`, `fix-not-regular`, `fix-hardlinked`, `fix-not-owner`, `fix-unsafe-directory`, `fix-group-mismatch`, `fix-acl-present`, `fix-unsupported-platform` and `fix-changed`.

The `slopvac plugins` group reserves this code. It is not emitted yet: nothing in the code raises it, and the message registry does not list it. Plugin-protocol.md, section 10, lists the other plugin host codes.

| Code | Meaning | Exit |
| --- | --- | --- |
| `plugin-not-code` (reserved) | `slopvac plugins trust` or `slopvac plugins untrust` named a data plugin. A data plugin has no executable content, so trust does not apply to it ([plugins.md](plugins.md), section 8). The command records nothing. | 2 |

The `plugins` command is a placeholder in the binary and reports `command-not-wired`. The codes below are errors that the `slopvac-plugins` library returns. Each one exits 2, because slopvac did not finish the part of the run that it names. The `Raised by` column names the command that reports the code once the command is wired. Plugin-protocol.md, section 10, lists the codes of the plugin host that are not in this section.

| Code | Meaning | Raised by |
| --- | --- | --- |
| `offline-plugin-missing` | Offline, a locked plugin is not in the cache. The message names the plugin and its digest (section 1.3). | `plugins sync` |
| `lock-mismatch` | The resolved plugins differ from the lockfile. The message lists each difference. The lockfile is not changed (section 1.4). | `plugins sync` in CI |
| `digest-mismatch` | Fetched or read content does not hash to the digest that the lockfile pins. | `plugins sync` |
| `cache-tampered` | An installed tree differs from its recorded hash and the run is offline, so slopvac cannot fetch it again. Slopvac removes the tree. Online, `plugins sync` installs it again. | `plugins sync` while offline |
| `signature-invalid` | The signature check refused an OCI artifact. The signature is missing, invalid or from a key that is not allowed. Or the lockfile has no signature for the entry, or the signature differs from the one the lockfile records. In `plugins update` it also covers the candidate artifact that update checks. The update reports the refusal for that plugin and still exits 2. | `plugins sync`, `plugins update` |
| `plugin-revoked` | The revocation list names the locked artifact or the key that signed it. In `plugins update` it also covers the candidate artifact. | `plugins sync`, `plugins update` |
| `sync-failed` | Any other failure of the sync that has no code of its own. It covers an archive that the extractor refuses, including one over a limit in threat-model.md, section 5.5. It also covers a git source over its limits, an artifact with the wrong layout, an unusable data directory and a network failure. In `plugins update` it covers the same failures while update fetches, checks and resolves the candidate artifact. | `plugins sync`, `plugins update` |
| `update-lock-busy` | Another `plugins update` holds the guard lock on the lockfile, and this one gave up after 30 seconds. | `plugins update` |
| `update-failed` | Any other failure of the update that has no code of its own. It covers a lockfile that is too large, unreadable or invalid, a plugin id that the lockfile does not list, and a lockfile that cannot be written. | `plugins update` |
| `revocation-list-invalid` | The revocation list or its artifact fails verification. The cause is no usable release key, a list over 1 MiB, a bad signature, text that is not canonical JSON of the list format, or an artifact with the wrong layers. | `plugins sync`, `plugins update` |
| `revocation-list-unavailable` | The list could not be fetched. Online, the command stops and keeps its cache. | `plugins sync`, `plugins update` |
| `revocation-list-expired` | The fetched list is past its signed `expires`, which marks a replayed old list. The cache stays as it was. | `plugins sync`, `plugins update` |
| `revocation-list-rollback` | The fetched list was issued earlier than the cached one. | `plugins sync`, `plugins update` |
| `revocation-list-equivocation` | The fetched list has the same `issued` time as the cached one and different content. The cache stays as it was. | `plugins sync`, `plugins update` |
| `revocation-cache-invalid` | The cached list does not verify, or a file operation on the cache failed. A verified online refresh can replace a damaged cached list. A failed cache read blocks offline use. During a verified online refresh, a failed cache read is ignored, but a failed lock or write on the cache still fails the run. | `plugins sync`, `plugins update` |
| `revocation-clock-invalid` | The clock that the caller passed is not a `YYYY-MM-DDTHH:MM:SSZ` time. The caller supplies the clock, so a user cannot cause this. It is an internal invariant. | `plugins sync`, `plugins update` |
| `trust-key-missing` | Trust records exist but the key that they were made under is gone. | Any command that starts a code plugin |
| `trust-key-mismatch` | The trust records were made under another key than the one in the trust store. | Any command that starts a code plugin |
| `trust-key-unusable` | The trust key file is not private to the user, or does not hold a key. | Any command that starts a code plugin |
| `plugin-usage` | The plugin host refused to start the plugin or misused it. Before spawn it refuses a program file that is missing, is a symlink or is not a file in the plugin tree. It also refuses an environment variable name that is empty, repeated or can load code into the plugin. The code also covers wrong use of an open plugin, for example sending a request to one that has shut down. | Any command that starts a code plugin |

Two notices come from the same revocation list. Neither blocks the run, so each leaves it complete. `revocation-list-missing` means that no list was ever fetched on this machine. `revocation-list-stale` means that the cached list is past its `expires`. Both appear in the report of an offline `plugins sync`. Threat-model.md, section 5.3, gives the freshness rules.

Four codes of `plugins search` are reserved for the index fetch code (`slopvac-8l4.9.62`) and are not registered yet. Each joins this table in the change that first emits it, with its kind and exit. [plugin-index.md](plugin-index.md), section 9, gives the cases:

- `index-fetch-failed`: an index could not be fetched or read. The search shows that index's cache, if any, and exits 2.
- `index-signature-invalid`: the default index failed `sign::verify`. Same outcome.
- `index-rollback`: the default index is older than the cached floor. Same outcome.
- `index-unknown`: `--index` named an index that the config does not define. Exit 2.

The search also reports `offline-network-needed` (section 1.3) for an index with no cache while offline.

Owners: `slopvac-8l4.2.6` for the protocol, `slopvac-8l4.4.7` for config diagnostics, `slopvac-8l4.12.1` for the CLI.

### 3.6 Breaking changes

3.0 carries no deprecation machinery. A breaking change takes effect at a major version, and the release notes list it.

- Minor and patch releases of 3.x make additive changes only (section 3.2). A removal or rename needs a major version.
- Warning periods, deprecated aliases, and flags that emit old output formats do not exist. Slopvac 3.0 rejects removed flags, options and hooks with an error and exit 2. A rule ID in config that no rule has, a removed rule included, is the warning notice `config-unknown-rule`. The notice does not make the run incomplete and does not change its exit status. [`compat/removed-rules.toml`](compat/removed-rules.toml) lists the rule IDs that 3.0 removed.- Plugin `slopvac_api` and code plugin `protocolVersion` follow the same rule. The host loads a plugin whose versions it supports, as section 3.4 describes. A plugin outside that range stays unloaded, and the error names both versions. No grace period applies.

Owners: `slopvac-8l4.12.1`, `slopvac-8l4.9.1`.

### 3.7 2.x surfaces at 3.0

3.0 invalidates the 2.x surfaces at release. Slopvac has no 2.x compatibility mode.

- A config file with no `schema_version`, or with a 2.x value, is rejected with exit 2. This covers `.slopvac.toml`, `slopvac.toml`, and `[tool.slopvac]` in `pyproject.toml`. The error has the code `config-legacy-version`, names the file, and points to `slopvac migrate`.
- Slopvac lints nothing while it holds a 2.x config. No partial run happens.
- `slopvac migrate` is the only path from 2.x. It previews the changes, rewrites the config with comments kept, updates directive IDs and steering blocks in documents, and compares findings before and after.
- The mapping covers every 2.x setting, including negated globs, category budgets and weights, per-path locale, vocabulary files, and guidance controls. A setting with no 3.0 equivalent produces a `config-legacy-dropped` error in `migrate` and never disappears silently.
- A 2.x flag, option, or hook that 3.0 removes fails with an error and exit 2. The compatibility matrix (`slopvac-8l4.2.9`) lists each one with the disposition `remove`.
- Lint JSON from 3.0 has `schema_version` 3 only. No flag emits the 2.x format.

Owners: `slopvac-8l4.4.5` for the version check, `slopvac-8l4.2.5` for the mapping table, `slopvac-8l4.16.1` for `migrate`, `slopvac-8l4.16.2` for `prime migrate`.

### 3.8 SDK support

- The Python SDK implements one `protocolVersion` per SDK major version. It supports the protocol versions that the matching host release supports (section 3.4).
- The SDK ships a conformance suite. A plugin in any language can use it, and the example plugin must pass it.
- The SDK validates messages against the published `plugin-protocol` schema, so a protocol mistake shows up in the plugin's own tests.
- SDK releases follow semantic versioning. A minor release can add optional capabilities. A protocol-incompatible change needs an SDK major release (section 3.6).
- An SDK in another language builds on the published JSON Schemas.

Owners: `slopvac-8l4.9.7`, `slopvac-8l4.19.1`.

### 3.9 Schema source

**Generation.** The files in `schemas/v3/` are generated from the Rust types by the `slopvac-schemas` crate. CI regenerates them and fails on any difference. Edit the Rust types, never the generated files. The conformance corpus under `schemas/v3/conformance/` is hand-written and stays the referee: the Python and Rust implementations must accept and reject it exactly as each `cases.toml` says. Each artifact moves to generation in its own change.

**Additive-only check.** `scripts/contract/schema_compat.py` compares `schemas/v3/*.schema.json` with a baseline and enforces section 3.2. It fails on these changes:

- a removed file, or a changed `$id`
- a removed property or `$defs` entry, at any depth
- a new `required` entry
- a narrowed `type`, `enum` or `const`
- a raised `min*` bound or a lowered `max*` bound
- a changed `pattern`
- `additionalProperties` that is newly `false`, or newly a narrower schema

It then validates every `valid/` instance of the baseline corpus against the new schema and fails on any rejection. Added optional properties, widened enums, new `$defs` entries and new files pass. Each finding prints as `file:json-pointer: kind: old -> new`. The `kind` is a stable kebab-case code. A code is never reused and never changes meaning (see section 3.5 and `docs/engineering.md`). Exit code 0 means compatible, 1 means a breaking finding, and 2 means a usage or read error, which is never a pass.

**Baseline.** Before the first 3.0 release candidate, the baseline is the pull request's merge-base with `origin/main` (`--base <git-ref>`). This catches accidental breaks in each change. At the release candidate, a snapshot is committed under `schemas/v3/baseline/` and replaces the ref (`--baseline-dir`).

**Limits.** The check fails closed where it cannot decide. Each case below needs an allow entry.

- A `$ref` resolves across every file in `schemas/v3`, on both sides. A change to a shared definition is reported against each referrer, as `file:/properties/p/$ref(common.schema.json#/$defs/D)/minLength`. A reference that does not resolve is `unverified`. A schema file without a string `$id` is a read error.
- Proving that a recursive schema and its inlined expansion accept the same instances is out of scope. When a reference was added or removed and the same target recurs, the check stops at that point and reports `unverified`. The corpus re-validation is the backstop.
- `allOf`, `anyOf`, `oneOf` and `prefixItems` compare by position. A list that keeps all its members in another order is `list-reordered`. A new `anyOf` or `oneOf`, and an appended `oneOf` or `prefixItems` member, are `narrowing-possible`.
- A keyword the check does not model is `unverified` when it is added, removed or changed. Only these annotations never count: `description`, `title`, `examples`, `$comment`, `deprecated`, `readOnly` and `writeOnly`. A changed `default` does count, because it changes what consumers see.
- Each added `required` field is its own finding, located by field name, so one allow entry covers one field.
- The check compares `enum` and `const` as JSON values: a Boolean is not a number.
- If the corpus needs a definition that the new schema deleted, the check exits 2.
- A merge-queue entry uses the base commit that the queue built it on as its baseline.

**Allow-file.** `schemas/v3/compat-allow.toml` is the path for a reviewed breaking change. Each `[[allow]]` entry names the `file`, `pointer` and `kind` of one finding, a `reason`, and the reviewer in `approved_by`. Only the entries that the change adds can go stale. An entry that the baseline's allow file already holds approved a change that has landed, so it never counts as stale. It still suppresses a finding that the baseline also has against itself, unchanged, such as a `$ref` that does not resolve on either side. It suppresses nothing else. So an entry keeps passing after its change reaches the base. A different finding at the same pointer, such as a changed reference, needs a new entry and a new review. An added entry that matches a finding suppresses it. An added entry that matches no finding fails the check, so stale entries cannot pile up. `--allow-file` replaces the tree's allow file. The baseline's allow file is always read from the baseline. The file starts empty.

Owner: `slopvac-8l4.2.50`.

## 4. Conformance tests

The 3.0 binary must pass these tests. Each runs the installed binary with an isolated home and cache directory. `slopvac-8l4.13.9` blocks the release until all pass.

| ID | Test | Owner |
|---|---|---|
| N1 | With the update check disabled, `lint`, `validate`, `rules`, `explain`, `prime`, `reference`, and `claims` each finish under a network sandbox that fails any connection. | `slopvac-8l4.12.1` |
| N2 | `--offline`, `SLOPVAC_OFFLINE=1`, and `[network] offline = true` each make `plugins sync` exit 2 with the code `offline-plugin-missing` when the cache lacks a plugin. A command with no network path exits 2 with `offline-network-needed`. | `slopvac-8l4.9.3` |
| N3 | `SLOPVAC_OFFLINE=1` with `[network] offline = false` in the config stays offline. The CLI help lists no flag that turns offline mode off. | `slopvac-8l4.12.1` |
| N4 | With a populated cache and a lockfile, `plugins sync --offline` succeeds and verifies digests. | `slopvac-8l4.9.3` |
| N5 | No update check starts under `CI`, `NO_UPDATE_NOTIFIER`, `SLOPVAC_NO_UPDATE_CHECK`, `DO_NOT_TRACK`, `update_check = false`, or `--offline`. The test extends the 2.x test `test_environment_suppression_prevents_refresh_and_notice`. | `slopvac-8l4.12.4` |
| N6 | Machine formats keep stdout free of update notices, and JSON carries the notice in `notices`. | `slopvac-8l4.12.4` |
| N7 | `plugins sync` in CI exits 2 on a missing lockfile or a digest mismatch and leaves the lockfile unchanged. | `slopvac-8l4.9.3` |
| N8 | `sync` and `update` never record trust, with or without `--yes`. Only `plugins trust` and `SLOPVAC_TRUST` do. | `slopvac-8l4.9.4` |
| N9 | `slopvac report` without `--gh --yes` starts no process and sends zero requests, and it prints the full body. With `--gh --yes`, a fake `gh` on `PATH` receives exactly the arguments of the printed command. | `slopvac-8l4.12.6` |
| N10 | The issue body for a run in a directory with a unique marker path and user name contains neither. | `slopvac-8l4.12.6` |
| N11 | A review run with a model provider and `--dry-run` leaves the provider uncalled and prints the payload. A `lint` run leaves every provider uncalled. | `slopvac-8l4.11.3` |
| N12 | A model provider that is untrusted or absent from the config never starts. | `slopvac-8l4.9.6` |
| R1 | With `SLOPVAC_LOG=trace`, a run over a document with a unique sentinel string logs no copy of the sentinel from the text, matches, front matter, or terms. | `slopvac-8l4.12.1` |
| R2 | The same run over stdin logs `<stdin>` and no temporary path, in logs, errors, and panics. | `slopvac-8l4.12.9` |
| R3 | Paths inside the project root log relative to it. Paths outside log as `<external>/<file name>`. | `slopvac-8l4.12.1` |
| R4 | A token in `GH_TOKEN` and credentials in a registry URL appear in no log, error, or notice. | `slopvac-8l4.9.2` |
| C1 | With stdout piped, no format contains an escape byte. | `slopvac-8l4.12.2` |
| C2 | `NO_COLOR=1`, `--color never`, and `--no-color` each remove all escape codes, including bold and italic, even when `FORCE_COLOR=1` is set. | `slopvac-8l4.12.1` |
| C3 | `--color always` forces color on a pipe, and `--color` wins over `NO_COLOR`. | `slopvac-8l4.12.1` |
| C4 | Every severity and verdict in text output appears as a word. A snapshot test strips all escape codes and compares. | `slopvac-8l4.12.2` |
| C5 | `TERM=dumb` output uses ASCII borders and no cursor controls. | `slopvac-8l4.12.2` |
| H1 | The HTML report passes axe-core with no violations, has `lang="en"`, one `<h1>`, table captions and `scope`, and no remote resource. | `slopvac-8l4.12.2` |
| H2 | The report stylesheet meets the contrast ratios in section 2.3, computed from its variables in both schemes. | `slopvac-8l4.12.2` |
| V1 | Every published schema accepts its conformance instances and rejects the invalid ones. | `slopvac-8l4.2.19` |
| V2 | An artifact with a `schema_version` above the supported range fails with the code, the versions, and the upgrade command. | `slopvac-8l4.4.5` |
| V3 | A user-written file with an unknown key fails with file, line, and column, and an `x-` key passes. A plugin message with an unknown field is ignored. | `slopvac-8l4.2.5`, `slopvac-8l4.2.6` |
| V4 | A handshake with no common protocol version, a missing required feature, or an unknown capability produces the behavior in section 3.4. | `slopvac-8l4.9.6` |
| V5 | A plugin with an unsupported `slopvac_api` stays unloaded, and the error names both versions. | `slopvac-8l4.9.1` |
| V6 | Every error code in the generated docs is unique and kebab-case, and a later release keeps every code of the earlier one. | `slopvac-8l4.19.1` |
| V7 | A config without `schema_version`, or with a 2.x value, exits 2 with `config-legacy-version` and a pointer to `slopvac migrate`, and lints nothing. | `slopvac-8l4.4.5` |
| V8 | Each removed 2.x flag, option, and hook fails with an error and exit 2. No 2.x JSON format flag exists. | `slopvac-8l4.2.9` |
| V9 | The Python SDK example plugin passes the conformance suite. | `slopvac-8l4.9.7` |
| V10 | Each 2.x setting listed in section 3.7 maps in `slopvac migrate`, or produces `config-legacy-dropped`. | `slopvac-8l4.2.5`, `slopvac-8l4.16.1` |

The Python 2.x tests that cover current behavior sit in `packages/slopvac-lint/tests/`:

- stdin redaction in text, JSON, and error output: `test_cli.py`.
- update-check opt-outs and machine-format suppression: `test_update_notice.py`.
- piped text output without escape codes, forced-terminal color codes, and `--no-color` without color codes: `test_cli.py`.

`NO_COLOR` has no 2.x test, because 2.x ignores the variable (section 2.1).

## 5. Follow-up for bead owners

- `slopvac-8l4.12.6` adds the preview and `--gh --yes` behavior from section 1.5.
- `slopvac-8l4.13.6` is the Action bead. Its description lists reviewdog, SARIF, and CodeClimate, so it needs the `plugins sync` step and the `--offline` lint step from section 1.4.
- `slopvac-8l4.12.4` confirms which commands may start the update check (section 1.2).
