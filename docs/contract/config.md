# Slopvac 3.0 config and front matter

Status: contract for 3.0. Bead `slopvac-8l4.2.5`. Plan: [slopvac-3.md](../design/slopvac-3.md). Decision: [architecture record 0001](../design/0001-slopvac-3-architecture.md), section 20.

The schemas are [`config.schema.json`](../../schemas/v3/config.schema.json) for `slopvac.toml` and [`frontmatter.schema.json`](../../schemas/v3/frontmatter.schema.json) for the `slopvac:` block. Field meanings live in the schema `description` fields. This document states what the schemas cannot: layer order, merge rules, discovery, and the move from 2.x.

Each statement is a **2.x behavior** with its source in `packages/slopvac-lint/src/slopvac/config.py`, or a **3.0 requirement** with an owning bead.

## 1. Layers

### 1.1 Order

Lowest priority first. A higher layer wins.

| # | Layer | `ConfigSource.layer` | Holds |
|---|---|---|---|
| 1 | Core defaults | `core` | Rule definitions, built-in profiles, default `exclude` |
| 2 | Styles | `style` | The `styles` list, in order. The last listed wins. |
| 3 | Genre chain | `genre` | The settings of the document's genre and the genres it extends |
| 4 | `extends` | `extends` | Extended configs, in list order. A later entry wins. |
| 5 | Project config | `project` | The nearest `slopvac.toml` |
| 6 | Matching `[[genres]]` and `[[overrides]]` | `override` | Blocks in file order. The last writer of a field wins. |
| 7 | Front matter | `front-matter` | The `slopvac:` block, limited by `[frontmatter] allow` |
| 8 | Inline directives | `directive` | Directives in the document |
| 9 | CLI flags | `cli` | Flags such as `--profile` |

The order comes from the plan, section "Layer order". Environment switches (`SLOPVAC_OFFLINE`) are source `env`. They only set sticky values, so they sit outside the order (section 1.3).

**2.x behavior.** The chain had three layers: the profile, the top-level tables, and each matching `[[overrides]]` block in file order (`config.py`, module docstring and `resolve_for`). Front matter, genres, styles and `extends` did not exist.

### 1.2 Merge rules

**3.0 requirement.** A higher layer patches a lower one field by field.

- A scalar replaces the lower value. This covers `profile` fields and `locale`.
- A map merges by key. This covers `rules`, `categories`, `thresholds` and `terms`. A higher layer that names one key leaves the others alone.
- A list replaces the lower list. This covers `exclude`, `styles`, `terms.allow`, `terms.files`, `terms.blocklists` and `files`. A project that wants the default `exclude` plus one pattern restates the defaults. This matches 2.x, where a user `exclude` replaced the default list (`Config.exclude`) and an override `locale.allow` replaced the project's.
- An explicit threshold survives a profile change. The resolver picks the final profile across all layers. Then it applies each `thresholds` entry on top, layer by layer (`resolve_for`, which also does this in 2.x).
- `severity_shift` moves the levels that come from rule definitions, styles and the genre chain. A level that a `rules` or `categories` entry sets is final, and the shift leaves it alone. `off` stays `off`, and the result clamps at `suggestion` and `error`. The numbers for each built-in profile are in the profile mapping (`slopvac-8l4.2.10`).
- A higher layer cannot reset a field to unset. It sets a value. The one exception is the category budget: `max_per_100_words = "none"` clears a budget that a lower layer set, so a profile override can drop it. 2.x had no spelling for this, and thresholds have none either.

Sticky settings break the rule. `network.offline = true` in any layer, from any file in an `extends` chain, from the `SLOPVAC_OFFLINE` variable or from `--offline`, makes the run offline. No layer can set it back. See [policies.md](policies.md), section 1.3.

Scopes that apply to one file combine in file order, not by specificity. A glob that is more general and later in the file wins over a narrower one earlier. 2.x works this way (`resolve_for`), and 3.0 keeps it because file order needs no ranking of globs.

### 1.3 Project-wide tables

`guidance`, `network`, `review`, `plugins`, `index`, `styles`, `extends`, `frontmatter`, `mode` and `exclude` apply to the whole run or to file selection. They are not part of the `Settings` patch. An `[[overrides]]` or `[[genres]]` block that names one is an error, and so is a front matter field of that name. 2.x already rejected `guidance` in an override (`Override._reject_guidance`). 3.0 extends the rule to the other tables.

#### 1.3.1 Plugins

`[[plugins]]` lists every data plugin and code plugin that the project uses, in one array. Each entry has `id`, `source` and an optional `version` requirement. The config does not state the kind: the plugin manifest declares it, and the lockfile records it (plugins.md, section 2).

- Each `id` appears once. A repeated id is an error at the second entry.
- `core` is reserved for the built-in plugin, which the binary compiles in. An entry with the id `core` is an error.
- A listed code plugin starts only after `slopvac plugins trust` records its content hash. A code plugin that is not trusted never starts. The run reports it with the code `plugin-untrusted` and exits 2.
- A separate `[[packs]]` array is an unknown key.

#### 1.3.2 Plugin indexes

`[index]` sets which indexes `slopvac plugins search` reads (plugin-index.md, sections 5 and 6). It is project-scoped. There is no user-level config layer, and an environment variable, front matter, `[[overrides]]` block, `[[genres]]` block or inline directive cannot set it.

- `default` is a boolean and defaults to `true`. It turns the signed first-party index on or off.
- `[[index.extra]]` is a list of at most 16 extra indexes. The default index does not count. A file with more entries is refused with `config-budget-exceeded`, `data.budget = "index-extra"` and `data.limit = 16`, before the duplicate-name check and before any fetch (policies.md, section 1.9). The loader checks every file, extended files included, and a later layer replaces the list instead of adding to it, so the merged list never holds more than 16. Each entry has `name` and `source`, both required.
- `name` is a lowercase slug of the form of a plugin id: a letter, then letters, digits and hyphens. `core` and `slopvac` are refused, because `slopvac` is the name of the default index. Each `name` appears once. A repeated name is an error at the second entry.
- `source` is an `oci://` reference or an `https://` URL, at most 2048 characters. It carries no user-info. `http://`, `git+https://` and a path are invalid.
- Naming an index grants it no trust (plugin-index.md, section 10).
- A refused `source` is reported with its field, such as `index.extra[0].source`, and the reason: unsupported scheme, user-info, no host, whitespace or too long. The message never repeats the value, because a source can carry a credential (policies.md, section 1.7). Rendered output masks the value of every `index.extra[*].source` in the quoted config line, whichever diagnostic quotes it, keeping the quotes, line and column.

### 1.4 Provenance

Every resolved value carries a `ConfigSource` (`common.schema.json#/$defs/ConfigSource`):

- `layer` is one of the names in section 1.1, or `env`.
- `file` is the path relative to the project root. A value from a plugin uses `plugin:<id>/<path>`. A `core`, `cli` or `env` value has no file.
- `line` and `column` are one-based and point at the key that set the value. For front matter, they count from the start of the document file, not from the start of the block.
- A `[[genres]]` or `[[overrides]]` value uses layer `override`. The report names the block by its index.

`slopvac lint --explain-config` prints the layer, file, line and column of each value and the value it overrode. 2.x printed only a label such as `overrides[0] (docs/**)` (`provenance` in `resolve_for`). Owners: `slopvac-8l4.4.2` for the stack, `slopvac-8l4.4.7` for diagnostics.

#### 1.4.1 `--explain-config` output

`slopvac lint --explain-config <targets>` prints how the settings of each input resolve, then exits. It lints nothing: no report, no gate and no summary.

- It writes to standard output and exits 0. A target that cannot be read, or a config that cannot be loaded, is reported on standard error as for a lint run, and the exit code is 2.
- It prints one block per input, in argument order, with a blank line between blocks. A block is headed by the input's path as the report shows it (policies.md, section 1.7), or `<stdin>` for standard input.
- Below the heading, a block lists `config root: <root>` and one `config file: <file> (<layer>)` line for each file of the config stack. The root is `.` for the working directory, the path relative to the working directory for a directory below it, and `<external>/<name>` for any other directory (policies.md, section 1.7). The root and the path metadata (the heading, the config files and the origins) never carry an absolute path. Values are printed as configured, except that a value that is a URL is printed without its user-info, query and fragment.
- Every field of the output, the heading included, is escaped as one line, so a file name or a value cannot inject a control sequence or a line break.
- Then comes each resolved key as `<key> = <value>  [<layer> <file>:<line>:<column>]`. The origin of a `core` value has no file. Each value the key replaced follows on an indented line `replaced <value>  [<origin>]`, highest layer first.
- Until front matter takes part in resolution, a block ends with the line `front matter overrides are not shown`.
- The output is text only. `--explain-config` with a `--format` other than `text` fails before any file is read, with the code `explain-config-format-unsupported` and exit 2.
- `--explain-config` with `--min-score`, `--max-per-100-words`, `--locale`, `--category`, `--disable`, `--out`, `--open` or `--verbose` fails the same way, with the code `explain-config-option-unsupported` and exit 2. It does not show the command-line layer yet, and the refusal keeps it from ignoring those options.

## 2. Nearest config

**2.x behavior.** `find_config` runs once from the working directory (`cli.py`, `config_path or find_config(Path.cwd())`). It checks `slopvac.toml`, then `.slopvac.toml`, then a `[tool.slopvac]` table in `pyproject.toml`, in each directory from the start upward. It stops after the first directory that contains `.git`. The docstring of `config.py` says discovery walks up from each target file. The code does not: one config applies to every file in the run.

**3.0 requirement.**

1. For each file, start in the file's directory. Walk up, one directory at a time.
2. The first directory that holds `slopvac.toml` supplies the config. Call it the nearest config.
3. A directory that holds `.git`, as a directory or a file, ends the walk after its own `slopvac.toml` is checked. The walk never leaves the repository.
4. A file without a `slopvac.toml` on its path uses the core defaults.
5. Only the nearest config applies. A parent config does not merge in on its own. Use `extends` to inherit.
6. `--config <path>` skips discovery and applies that one file to every file in the run. Its directory is the root for globs.
7. Input from `--stdin` uses the nearest config of the working directory.
8. A config pattern in `exclude`, `files` or a negated form matches the path relative to the directory of the nearest config. A file outside that directory matches no override. The 2.x fallback to the bare file name is removed.
9. Path values for files (`terms.files`, `terms.blocklists`, a local `plugins` source, `extends`) are relative to the file that holds the value.
10. The walk finds only `slopvac.toml`. A `.slopvac.toml` file or a `[tool.slopvac]` table that the walk meets is a 2.x config and is rejected (section 5).

Resolution is cached per directory, so a run over many files reads each config once.

### 2.1 `extends`

- Entries apply in list order, and a later entry wins. The extending file wins over all of them.
- An entry is a path relative to the extending file, or `<plugin>:<name>` for a config that a plugin ships.
- An extended file is a v3 config. It must carry `schema_version = 3`. It may extend others.
- A cycle is an error that names the chain: `config-extends-cycle`.
- The nearest config decides `exclude` globs and override globs, wherever the pattern was written.

## 3. Front matter

The block is the mapping under the `slopvac:` key of a document's front matter. Front matter in YAML (`---`), TOML (`+++`) or JSON is read, and the block has the same shape in each. The schema validates the parsed mapping. Conformance instances are YAML.

- `v` is required and equals 3, the same number as `schema_version`. A larger value is an error that names the versions supported and the upgrade command.
- The fields are `genre`, `profile`, `locale`, `thresholds`, `categories`, `rules` and `terms.allow`. No other key is allowed, and a misspelling is an error at its line and column.
- `[frontmatter] allow` in the project config sets which fields take effect. The default is `genre`, `locale` and `terms`. A field outside the list is an error: `config-frontmatter-field-denied`. Slopvac reports it every time.
- The default list lets a document weaken its own gate without a project opt-in, the same way an inline `slopvac-allow` comment does. A document that picks a lenient genre, or lists `terms.allow` words, changes what it is held to. A stricter project removes `genre` from the list. For example, `allow = ["locale", "terms"]` makes a `genre` field in any document an error, and the genre comes from the `[[genres]]` blocks or from detection.
- The `genre` field changes the genre only. Contexts that a `[[genres]]` block or the config assigns to a file are additive, so a document cannot remove them by naming another genre. The report lists both the front matter reason and the path reason.
- `[frontmatter] enabled = false` makes `slopvac:` ordinary data. Slopvac neither reads nor validates it.
- Keys outside `slopvac:` are the document's own and are never checked.
- Keys that start with `x-` are ignored inside the block.

## 4. Other config rules

- Every `slopvac.toml` carries `schema_version = 3`. A file without it, or with 2, is a 2.x config.
- Unknown keys are errors with file, line and column, and the nearest valid key. Keys that start with `x-` are ignored. The exception is a map keyed by rule or category name (`rules`, `categories`). Its keys are data, so `x-` has no special meaning there ([policies.md](policies.md), section 3.3).
- A rule or category key is qualified (`<plugin>:<id>`) or a bare name that is unambiguous across the active plugins. An ambiguous name is an error from the resolver. An unknown rule id is the warning notice `config-unknown-rule`. The notice does not make the run incomplete and does not change its exit status ([lint-report.md](lint-report.md), Notice data). An unknown category is an error. The schema checks only the form.
- `rules` takes a bare level. The 2.x table form `[rules."x"] severity = "off"` is not valid, because a level is the only field.
- Two blocks in `[[overrides]]` or `[[genres]]` with the same `files` set are an error: `config-duplicate-scope`. This keeps `Config._reject_duplicate_scopes` from 2.x. The patterns compare as a set after whitespace is trimmed.
- A `[[genres]]` block assigns a genre to the files it matches and patches their settings. The genre itself is defined in a genre file (`genre.schema.json`, owned by another bead).
- `exclude` and `files` patterns use gitignore semantics through the same engine as 2.x. A leading `!` negates, and the last matching pattern wins.
- A threshold absent from a profile and from every layer is unset, and its gate does not run.

## 5. Moving from 2.x

3.0 invalidates 2.x configs. No compatibility mode exists, and there is no warning period. Section 3.7 of [policies.md](policies.md) states the policy.

- A config with no `schema_version`, or with 2, makes every command that reads config exit 2 with `config-legacy-version`. The error names the file and points to `slopvac migrate`. Nothing is linted.
- Discovery treats a `.slopvac.toml` file and a `[tool.slopvac]` table as 2.x configs and fails the same way.
- `slopvac migrate` is the only path. It previews every change and then rewrites the file with comments kept. It compares findings before and after.
- A setting with no 3.0 equivalent stops the migration with `config-legacy-dropped`. The error names the key, the file, the line and the reason. `migrate` writes nothing until the user removes or rewrites that setting. It reports every such setting in one run.

Owners for the behavior: `slopvac-8l4.16.1` for `migrate`, `slopvac-8l4.4.5` for the version check.

### 5.1 Dispositions

- **preserve**: the key and its meaning carry over. `migrate` copies the value.
- **migrate**: 3.0 has the setting under a new key or form. `migrate` rewrites it.
- **remove**: 3.0 has no equivalent. `migrate` fails with `config-legacy-dropped`, except where the table says the removal is lossless or ends in a notice.

### 5.2 Mapping table

Rule and category names change with the plugin model. `migrate` maps a 2.x name such as `prose-format.no-unicode-dash` to its 3.0 qualified id through the rename table in the binary. A name with no entry stops the migration. The table is part of the profile and rule mapping (`slopvac-8l4.2.10`). The rows below call this "rename".

| 2.x setting | Disposition | 3.0 | `slopvac migrate` |
|---|---|---|---|
| File `slopvac.toml` | preserve | `slopvac.toml` | Adds `schema_version = 3`. |
| File `.slopvac.toml` | migrate | `slopvac.toml` in the same directory | Renames the file. Stops if a `slopvac.toml` exists there, because 2.x ignored the dotfile in that case. |
| Table `[tool.slopvac]` in `pyproject.toml` | migrate | `slopvac.toml` next to `pyproject.toml` | Writes the new file and deletes the table from `pyproject.toml`, keeping its comments. |
| No version field | migrate | `schema_version = 3` | Adds it. |
| `mode` | preserve | `mode` | Copies it. |
| `profile` | preserve | `profile`, as a name | Copies the name. What a tier does changes: it sets thresholds and a severity shift only. The rule defaults it carried move to styles and rule definitions (`slopvac-8l4.2.10`). |
| `exclude` | preserve | `exclude` | Copies the list. A list replaces the default, as in 2.x. |
| Negated globs in `exclude` | preserve | `!pattern` | Copies them. Order matters and is kept. |
| `categories.<name>` as a bare level | preserve | `categories.<name>` | Renames the category. |
| `categories.<name>.severity` | preserve | `categories.<name>.severity`, or a bare level when it is the only field | Renames the category. |
| `categories.<name>.minimum_severity` | preserve | same key, `off` included | Renames the category. In 2.x, `off` sets no floor (`engine.py`, the rank test skips it), and 3.0 gives it the same meaning. |
| `categories.<name>.max_per_100_words` | preserve | same key | Renames the category. |
| `categories.<name>.weight` | preserve | same key | Renames the category. |
| `rules.<id>` as a bare level | preserve | `rules.<qualified id>` | Renames the rule. |
| `rules.<id>.severity` as a table | migrate | `rules.<qualified id>` as a bare level | Renames the rule and writes the bare level. |
| A rule that 3.0 removed, or a category with no rules in 3.0 | remove, with a notice | none | Drops the entry. Each drop prints a non-fatal notice and `migrate` exits 0. A removed category has the code `migrate-category-removed`. A removed rule has the code `migrate-rule-removed`, at info level. Both notices point to [`compat/removed-rules.toml`](compat/removed-rules.toml), which lists the removed rule ids. Policies section 3.7 forbids a silent drop. |
| `thresholds.max_total_per_100_words` | preserve | same key | Copies it. |
| `thresholds.max_errors` | preserve | same key | Copies it. |
| `thresholds.max_warnings` | preserve | same key | Copies it. |
| `thresholds.min_score` | preserve | same key | Copies it. |
| `thresholds.max_unicode_dashes` | preserve | same key | Copies it. |
| `locale.default` | migrate | `locale` | Moves the value up one level. |
| `locale.allow` | migrate | `terms.allow` | Moves the list. The words still skip the spelling check. |
| `vocabulary.path` | migrate | `terms.blocklists = [<path>]` | Keeps the path and rewrites each 2.x blocklist: it adds `schema_version = 3` and normalises `pos` values that 3.0 does not accept to their long form. The entries keep `word`, `pos` and `reason`. It rewrites TOML blocklists inside the project only. For any other blocklist it names what to change by hand. |
| `vale.enabled = false` | remove, lossless | none | Deletes the table and lists the deletion in the summary. Vale is gone in 3.0 (architecture record 0001, decision 2). |
| `vale.enabled = true` | remove | none | Fails with `config-legacy-dropped`. |
| `vale.binary` | remove | none | Fails, unless `vale.enabled = false` is set in the same table. |
| `vale.config` | remove | none | Fails, unless `vale.enabled = false` is set in the same table. |
| `vale.styles` | remove | none | Fails, unless `vale.enabled = false` is set in the same table. |
| `guidance.write` | preserve | `guidance.write` | Copies it. |
| `guidance.review` | preserve | `guidance.review` | Copies it. |
| `guidance.review_depth` | preserve | `guidance.review_depth` | Copies it. |
| `guidance.report` | preserve | `guidance.report` | Copies it. |
| None (new) | none | `guidance.level` | Not written. The default is `standard`. |
| `overrides[].files` | preserve | `overrides[].files` | Copies it, negated globs included. Patterns now match from the nearest config's directory. |
| `overrides[].profile` | preserve | same key | Copies it. |
| `overrides[].categories` | preserve | same key | Renames the categories. |
| `overrides[].rules` | preserve | same key | Renames the rules and writes bare levels. |
| `overrides[].thresholds` | preserve | same key | Copies it. |
| `overrides[].locale.default` | migrate | `overrides[].locale` | Moves the value up one level. |
| `overrides[].locale.allow` | migrate | `overrides[].terms.allow` | Moves the list. |
| `overrides[].vocabulary.path` | migrate | `overrides[].terms.blocklists` | Same as the project-level row. |
| `overrides[].vale` | remove | none | Same rules as the project-level `vale` rows. |
| `overrides[].guidance` | preserve (rejected) | rejected | 2.x already refused it. The error carries over. |
| Unknown keys rejected (`extra="forbid"`) | preserve | unknown keys are errors | The error gains line and column. |
| Duplicate override scopes rejected | preserve | `config-duplicate-scope` | Fails on the same inputs. |
| Override cascade in file order, last writer wins | preserve | layer 6 | Order is kept. |
| One config chosen from the working directory | migrate | nearest config per file | No rewrite. The effect is described in section 2. |
| Override match on the bare file name outside the root | remove | none | No rewrite. The file matches no override. |
| Table `[tool.slopvac]` and `.slopvac.toml` discovery | remove | none | Section 2, rule 10. |

The `minimum_severity` row has one 2.x quirk. `CategorySettings` declares the field twice. The two declarations are identical, so the duplicate has no effect, and `migrate` ignores it.

## 6. Conformance

The conformance corpus is the lasting golden. Generated schemas must accept and reject the same files.

- `schemas/v3/conformance/config/valid/` holds TOML configs: a minimal one, one that uses every table, and one in the shape `migrate` writes.
- `schemas/v3/conformance/config/invalid/` holds one defect per file. Each is mapped to a JSON pointer in `cases.toml`. The cases cover a missing or old `schema_version`, a 2.x `[vale]` table, unknown keys, bad levels, the 2.x table form of a rule and a `guidance` table inside an override. Further cases cover an invalid plugin id, the reserved id `core` and the retired `[[packs]]` array, and an index with a reserved name, an unsupported source scheme or user-info in its source.
- `schemas/v3/conformance/frontmatter/` holds YAML front matter, including a document with other keys, a document with no `slopvac:` key, and an `x-` key inside the block.
- `schemas/v3/conformance/common/` holds `ConfigSource` instances for each layer shape.

A schema checks form only. These behaviors need the resolver and have their own tests there: ambiguous rule names, duplicate scopes, `extends` cycles, denied front matter fields, and sticky offline mode. A repeated plugin id is an error that JSON Schema cannot express, so the config validator checks it and its tests cover it. The same holds for a repeated `[[index.extra]]` name.
