# slopvac CLI reference

`slopvac` lints prose and comments in source files. It checks for AI writing patterns, documentation discipline, technical writing,
and general prose. The
rules include constraints derived from Simplified Technical English and Orwell.

The linter ships 166 checked rules across 26 categories. The CLI reports
findings, scores, and incomplete coverage when selected checks cannot run.

See the [project overview](../../README.md) for agent setup and CI integration.

[Lint documents](#lint-documents) · [Profiles](#profiles) ·
[Configuration](#configuration) · [Scoring](#scoring) ·
[Metrics](docs/metrics.md) · [Finding triage](docs/triage.md) ·
[Rule coverage](#rules)

## Install

The package needs Python 3.11 or later. Choose a persistent installation or run
it through `uvx`:

```sh
uv tool install slopvac
slopvac --help

# Run without a persistent installation.
uvx slopvac README.md

# Alternative installer.
pipx install slopvac
```

[Vale](https://vale.sh) is optional.

For full deterministic coverage, install Vale 3.15 or later and put it on
`PATH`. We **highly recommend** doing so because Vale executes most deterministic
rules. `slopvac` generates the Vale configuration and styles.

| Engine | Checks |
| --- | --- |
| Vale | Most deterministic rules, including compiled patterns and part-of-speech checks |
| Native | Additional patterns and metrics, including comparisons between text blocks |

Without Vale, only the native checks run. Missing Vale, or `--no-vale`, leaves
selected Vale-backed checks `UNCHECKED` and returns exit 2. Native findings
remain in the report, but this is an incomplete check.

## Agent steering

`slopvac init` writes project configuration and, unless `--skip-agents` is
used, maintains a small Slopvac block in `AGENTS.md`. Detailed instructions stay
in the installed CLI:

```sh
slopvac prime
```

Use a harness-specific steering target when needed:

```sh
slopvac setup codex
slopvac setup claude
slopvac setup omp
slopvac setup kiro
```

Codex uses a non-empty `AGENTS.override.md` when one already exists, otherwise
`AGENTS.md`. Claude Code uses `CLAUDE.md`, and Oh My Pi uses `.omp/AGENTS.md`.
Kiro uses `.kiro/steering/slopvac.md`; new files include `inclusion: always`.
The generic `agents` target also manages `AGENTS.md`.

`slopvac setup <harness> --check` reports whether the managed block is current
without modifying files. `--remove` removes only the managed block. Use
`slopvac setup --list` for the supported targets and paths.

## Lint documents

```sh
slopvac README.md docs/
slopvac --profile strict docs/
slopvac --category prose-craft README.md
slopvac --disable prose-craft.relative-date README.md
slopvac --format json docs/ | jq .summary
```

`slopvac <paths>` and `slopvac lint <paths>` invoke the same command. Repeat
`--category` to select categories or `--disable` to disable named categories
or rules.

### Changed lines and fixes

```sh
slopvac --diff-base main README.md docs/
slopvac --diff-working-tree README.md docs/
slopvac --fix README.md
```

`--diff-base REV` limits findings to added lines in the committed `REV...HEAD`
diff. `--diff-working-tree` uses the index and working tree relative to `HEAD`.

`--fix` edits source files using deterministic replacements with a single
alternative. It preserves match case and skips replacements that offer multiple
choices. In a diff-scoped run, it leaves unchanged lines alone. The CLI lints
again after applying replacements. Review the resulting diff for meaning.

## Supported file types

Prose directory targets select `.md`, `.mdx`, `.markdown`, `.txt`, `.rst`,
and `.html` files. An explicitly named TOML file is accepted and checks its
comments. In comment mode, directory scans also include TOML files.

RST processing needs Docutils's `rst2html` or `rst2html.py` command on `PATH`.
Install it with `pip install docutils`. A selected RST target without the
converter reports an incomplete check and exits 2.

## Comment mode

```sh
slopvac lint --mode code-comments src/
```

Comment mode selects supported source extensions and runs comment-safe lexical
rules through Vale. It checks ordinary line and block comments, including
documentation comments that the language exposes through those scopes. Source
code and strings are outside those checks. `--comments` is an alias for this
mode.

Reports retain source paths and finding locations. Directory scans skip
unsupported source types with a non-failing note. An explicitly named
unsupported file is an error. Configured exclusions still apply.

`--mode` applies to the whole invocation and cannot appear in `[[overrides]]`.
Comment mode uses the packaged Vale configuration. It rejects a custom
`vale.config` or nonempty `vale.styles`, including per-file settings.

## Profiles

`normal` is the default. Profiles set rule tiers, severities, and density
budgets. Individual rules can have different treatment within a profile.

| Profile | Use | Total density budget | Max errors | Minimum score |
| --- | --- | --- | --- | --- |
| `strict` | Reference material and procedures | 1.5 / 100 words | 0 | 85 |
| `normal` | READMEs and guides | 3.0 / 100 words | 0 | 70 |
| `relaxed` | Informal text | 8.0 / 100 words | Unlimited | None |

The density budgets count errors at 1.0 and warnings at 0.5. Category budgets
also apply, including in `relaxed`. All profiles default to
`max_unicode_dashes = 0`. See [scoring](#scoring) for the gates.

| Rule tier | Effect |
| --- | --- |
| `enforced` | Uses its effective severity and can fail a gate |
| `advisory` | Reports at suggestion level under profile defaults |
| `excluded` | Does not run in that profile; configuration cannot re-enable it |

A tier is separate from configured severity. `severity = "off"` disables an
otherwise admitted category or rule. A project setting can override a
profile-default `off`, but it cannot override an `excluded` tier.

For rules admitted by their tier, explicit category and rule settings can
override profile-default severity. An `excluded` tier remains final. Inspect
effective rules with `slopvac rules --profile strict` or use
`--explain-config` to inspect a file's settings.

Categories also carry `recommended_for` genres for agent review. Reference
material maps to `strict`, informal text to `relaxed`, and consumer, internal,
and change-communication documents to `normal`. Genre recommendations do not
replace file configuration.

## Configuration

```sh
slopvac init
slopvac lint --explain-config README.md
```

The CLI discovers configuration separately for each target by searching its
parent directories. It accepts `slopvac.toml`, `.slopvac.toml`, or a
`[tool.slopvac]` table in `pyproject.toml`. `--config PATH` applies an explicit
configuration to all targets.

```toml
profile = "normal"
exclude = ["vendor/**", "generated/**"]

[thresholds]
max_errors = 0
max_warnings = 10

[categories]
prose-promotion = "warning"

[rules]
"prose-craft.relative-date" = "error"

[locale]
default = "en-US"

[[overrides]]
files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
profile = "strict"
```

| Setting | Controls |
| --- | --- |
| `profile` | Default rule treatment and thresholds |
| `exclude` | Gitignore-style file exclusions |
| `[thresholds]` | Error and warning limits, density, minimum score, and Unicode dash count |
| `[categories]` | Severity, minimum severity, density budget, and score weight |
| `[rules]` | Severity for an individual rule |
| `[[overrides]]` | Path-specific configuration patches |
| `[locale]` | Spelling target and allowed spellings |
| `[vocabulary]` | Path to a project word blocklist |
| `[vale]` | Vale enablement, binary, configuration, and styles |

### Precedence

Configuration starts with the profile, applies top-level settings, then applies
every matching `[[overrides]]` block in file order. Later blocks replace only
the fields they set. Other fields retain their values.

```toml
[[overrides]]
files = ["docs/**"]
profile = "strict"

[[overrides]]
files = ["docs/notes/**"]
profile = "relaxed"
```

A file under `docs/notes/` uses `relaxed` in this example. The last matching
block to set `profile` determines the value. Duplicate override scopes are
configuration errors.

`--explain-config` shows the resolved settings and the blocks that supplied
them. Unknown category names or rule IDs cause an error, including inside
overrides.

### Severity and weight

Severity settings can promote or demote findings. A per-rule setting takes
precedence over the category. The string shorthand
`"prose-craft.relative-date" = "error"` is equivalent to a rule table with
`severity = "error"`.

A category's `minimum_severity` raises findings below that level while retaining
higher severities. Per-rule overrides still take precedence.

A category with `weight = 0` reports its findings without contributing to the
score or ordinary gates. The Unicode dash gate counts its named findings
independently of category weight.

### Spelling

`[locale] default` accepts `en-US`, `en-GB`, or `und`. Use `und` to disable
spelling checks. The `allow` array lists spellings the project accepts regardless
of locale.

## Word blocklist

Project word restrictions need a blocklist:

```toml
[vocabulary]
path = "docs/blocklist.toml"
```

The path is relative to the configuration file. A blocklist entry identifies a
word and its part of speech:

```toml
[[entries]]
word = "deploy"
pos = "noun"
replacement = "deployment"
reason = "Use the noun deployment for the result of deploying."
```

Vale's `sequence` tagger applies the blocklist entry only when its part-of-speech
tag matches. Every entry needs a `reason`. `replacement` is optional.
Invalid or unreadable blocklists are configuration errors.

Use [`examples/blocklist.toml`](examples/blocklist.toml) as a starter. TOML,
YAML, and JSON formats work. If `vocabulary.path` is unset, the project blocklist
is inactive. Other spelling and word rules use their configured settings.

## Suppress a finding

Use a reason from the rule's exception list:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

`slopvac explain orwell.stale-figure` lists the accepted reasons. An unknown
reason or malformed directive produces `meta.invalid-suppression`.

The annotation covers the following block, such as a paragraph, list entry, or
table. `<!-- slopvac-disable-next-line -->` suppresses all rules in that block.
Use `<!-- slopvac-disable -->` and `<!-- slopvac-enable -->` around a region.
Directives quoted in inline code or fenced blocks do not suppress findings.

## Output formats

```sh
slopvac docs/
slopvac --format json docs/ | jq .
slopvac --format github docs/
slopvac --format sarif docs/ > out.sarif
slopvac --open docs/
slopvac --out report.html docs/
slopvac --format json --out report.json docs/
```

The default output is a terminal report. JSON includes findings, document
scores, and a summary. `github` produces workflow annotations. SARIF supports
code-scanning integrations.

`--open` writes a self-contained HTML report and opens it in a browser.
`--out` chooses the destination and implies HTML unless `--format` selects
another format. The HTML report needs no external assets.

Inspect `documents[].unchecked` in JSON results. An incomplete check can include
scores and useful findings, but it cannot report a pass.

### Report axes

Reports group findings under prose quality and AI register. AI-register counts
separate `strong` and `weak` signals. Rules with `ai_signal: none` contribute
to the prose-quality group.

`ai_signal_source` records the evidence behind a signal: `measured`, `catalog`,
or `unmeasured`. These labels do not change scores or gates and do not estimate
the probability that a document has an AI author.

## Scoring

| Field | Meaning |
| --- | --- |
| `per_100_words` | Raw finding count per 100 words, including suggestions |
| `gating_per_100_words` | Error count plus half the warning count, per 100 words |
| `score` | 0-100 score after a bounded suggestion penalty |

For documents of at least 60 words:

```text
raw density = findings / words * 100
gating density = (errors + 0.5 * warnings) / words * 100
suggestion penalty = min(15, 2.5 * suggestions / words * 100)
```

For a category with a positive density budget, its base score decreases linearly
from 100 to 70 at the budget. It reaches zero at four times that budget.
The scorer then subtracts the suggestion penalty, with a floor of zero.

A zero budget gives a base score of 100 at zero gating density and zero above
it. Without a category budget, each unit of gating density costs 10 points.

The document score is the lower of the weighted category mean and the score
computed over all scoring categories together. Categories with zero weight do
not contribute to either calculation.

Below 60 words, the scorer uses absolute counts: 20 points per error and 10 per
warning. Each suggestion costs 2.5 points, capped at 15. Density fields are zero
for these short documents.

### What fails a run

| Gate | Fails when |
| --- | --- |
| `max_errors` | The counted errors exceed the limit |
| `max_warnings` | The counted warnings exceed the limit |
| `max_total_per_100_words` | Gating density exceeds the document budget |
| Category `max_per_100_words` | Gating density exceeds that category's budget |
| `min_score` | The score is below the floor and a scoring category has an error or warning |
| `max_unicode_dashes` | Findings for `prose-format.no-unicode-dash` exceed the limit |

Suggestions alone do not trigger the ordinary score or density gates. The
Unicode dash limit counts its named findings at any severity. Turning off or
suppressing that rule removes those findings from the count.

Incomplete checks take exit 2. Otherwise, a failed gate takes exit 1 and a
passing run takes exit 0.

### Word counting

Sentence-length checks use STE counting conventions. Numbers with units,
abbreviations, quoted spans, and hyphenated terms each count as one word.
Parenthesized text counts as one word in its surrounding sentence. Step and
paragraph numbers do not count.

See [metrics](docs/metrics.md) for counting and text-type classification details.

## Rules

In the [generated rule reference](docs/rules.md), you can find all 26 categories
and profile tiers for the 166 checked rules.

| Family | Categories |
| --- | --- |
| AI register and residue | `ai-residue` and `ai-tells-*`: agentic, content shape, figurative, formatting, register, and structure |
| General prose | `prose-*`: agency, craft, discipline, format, inclusive language, inflation, promotion, and scope |
| Documentation discipline | `docs-discipline` |
| Simplified Technical English | `ste-*`: descriptive, nouns, practices, procedural, punctuation, safety, sentences, verbs, and words |
| Orwell-derived checks | `orwell` |

```sh
slopvac rules --profile strict
slopvac explain ste-sentences.sentence-not-short-or-clear
slopvac lint --rules-dir ./my-rules docs/
```

`--rules-dir` adds project rules over the packaged YAML and is repeatable.
The `my-rules` directory must exist and contain valid rule files. The loader
validates regexes and their positive and negative examples.

`slopvac rules` also includes the spelling rule generated for the configured
locale. The YAML rule count excludes that generated rule.

## The compiled-rule cache

Compiled Vale styles are cached between runs. Use these commands to inspect
or reclaim the cache:

```sh
slopvac cache
slopvac cache --prune
slopvac cache --all
```

`--prune` removes older compiled trees; `--all` clears the cache. Set
`SLOPVAC_CACHE_DIR` to choose a location, or use the default under
`XDG_CACHE_HOME`.

To inspect the compiled styles directly:

```sh
slopvac compile --outdir build/vale
slopvac compile --format json
vale --config=build/vale/.vale.ini docs/
```

The routing report separates Vale, native, and disabled entries.
Running Vale directly checks only the compiled Vale subset.

## Exit codes

These codes describe deterministic lint runs:

| Code | Result |
| --- | --- |
| `0` | Selected checks completed within configured thresholds |
| `1` | At least one threshold failed |
| `2` | An incomplete check or invalid configuration |

A passing score does not verify factual correctness or establish authorship.

## In development

Slopvac is evaluating a separate semantic layer with typed decisions. It would
run after the current parser has produced exact spans and deterministic
candidates. A provider such as Jev, Laya, Nimble, Kev, or a SemIf-compatible
backend would answer bounded questions while Slopvac code keeps ownership of the
final policy. The same provider interface would support two jobs: detect semantic-only
cases the linter cannot express reliably, and check a finding from the linter
against the rule's intended meaning.

A local reranker such as Qwen3-Reranker-0.6B may be tested before the typed
provider when candidate volume is high. It is a recall-first prefilter, never
the final judge, and filtered candidates must remain visible in coverage
measurement. This work lives on the separate `feat/judgement-rewrite` branch;
it is not part of the current CLI or deterministic exit status. See the
[project overview](../../README.md#agentic-judgement)
and [issue #162](https://github.com/srobroek/slopvac/issues/162).

## Sources

Each rule's provenance identifies its source. The rules include material derived
from [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), independent
restatements of STE principles, and Orwell-derived checks. Prose and
documentation categories have their own per-rule references.

ASD-STE100 is copyright [ASD](https://www.asd-ste100.org) and an EU registered
trademark. This package reproduces none of its rule text, definitions, or
examples. Project word restrictions use the [blocklist](#word-blocklist).

## License

Apache-2.0. The stop-slop source material is MIT-licensed.
