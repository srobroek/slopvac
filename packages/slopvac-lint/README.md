# slopvac CLI reference

`slopvac` lints prose and comments in source files. It checks for AI writing patterns, documentation discipline, technical writing,
and general prose. The
rules include constraints derived from Simplified Technical English and Orwell.

The linter ships 166 checked rules across 26 categories. The CLI reports
findings, scores, and incomplete coverage when selected checks cannot run. The
catalog also carries 67 judgment rules that lint never reports. Agents apply
them through [writing guidance and semantic review](docs/semantic-guidance.md).

See the [project overview](../../README.md) for agent setup and CI integration.

[Lint documents](#lint-documents) · [Profiles](#profiles) ·
[Configuration](#configuration) · [Scoring](#scoring) ·
[Metrics](docs/metrics.md) · [Finding triage](docs/triage.md) ·
[Suppressions](docs/suppressions.md) ·
[Semantic guidance](docs/semantic-guidance.md) · [Rule coverage](#rules)

## Install

The package needs Python 3.11 or later. Choose a persistent installation or run
it through `uvx`.

```sh
# Persistent installation.
uv tool install slopvac
slopvac --help
uv tool upgrade slopvac

# One-off run; uvx reuses its cached environment.
uvx slopvac README.md

# Force uvx to use the latest release.
uvx slopvac@latest README.md

# Alternative persistent installation.
pipx install slopvac
pipx upgrade slopvac
```

If the cache contains a newer stable PyPI release, Slopvac prints an update notice after an eligible command.
Slopvac refreshes that cache in the background. A newly discovered release can appear on a later run.
Slopvac skips the check in these cases:

- The command is `prime`.
- The output format is non-text.
- The report goes to a file or opens in a browser.
- The environment contains `CI`.
- Standard error is not a terminal.

To disable the check, set one of these environment variables:

- `NO_UPDATE_NOTIFIER=1`
- `SLOPVAC_NO_UPDATE_CHECK=1`
- `DO_NOT_TRACK=1`

**[Vale](https://vale.sh) 3.18 or later is required for complete linting.**
Install Vale separately and add its executable to `PATH` (`brew install vale`
on macOS). Run `slopvac doctor` to check that Vale meets the required version.
Slopvac generates Vale's configuration and styles.

Contributors can run
`mise install` to install the pinned Python, uv, and Vale tools.
Users of uvx, uv, or pipx do not need mise. They install Vale separately.

| Engine | Checks |
| --- | --- |
| Vale | Most deterministic rules, including compiled patterns and part-of-speech checks |
| Native | Additional patterns and metrics, including comparisons between text blocks |

Without Vale, only native findings are available. Missing or unsupported Vale,
or `--no-vale`, leaves selected Vale-backed checks `UNCHECKED` and returns exit 2. Native findings
remain in the report, but this is an incomplete check.

## Agent steering

Slopvac installs a managed steering block that tells the agent to run
`slopvac prime`, and a thin `slopvac-prose` skill for harnesses that load
project skills. Detailed instructions stay in the installed CLI, which only
prints them:

```sh
slopvac prime
slopvac prime write
slopvac prime review
```

`slopvac prime` prints the lint workflow and says when to run the `write` and
`review` topics. [Semantic guidance](docs/semantic-guidance.md) describes both topics.

Two commands write the steering files:

- `slopvac init` creates `slopvac.toml` when absent and keeps an existing file
  unless you pass `--force`. Repeat `--harness <name>` to write steering for
  multiple harnesses. Without `--harness`, it writes generic `AGENTS.md` steering.
  Naming a harness replaces that default, so add `--harness agents` to keep it.
  `--no-skills` writes steering without skills. `--skip-agents` writes only the
  config and rejects `--harness` and `--no-skills`.
- `slopvac setup <harness>` writes, checks, or removes one harness's steering
  and its skill when available. It writes only those files and reads
  `[guidance]` from `slopvac.toml`. Without a config it uses the defaults. It
  works with or without `init`.
`slopvac setup <harness> --remove` removes Slopvac's block and skill. It deletes
the skill directory only when that directory is empty. `slopvac setup --list`
prints each harness with its steering and skill paths.

```sh
slopvac init --harness claude --harness omp   # config plus Claude Code and Oh My Pi
slopvac init --harness codex --no-skills      # config plus Codex steering, no skill
slopvac setup kiro                            # one harness; reads config, never writes it
```

| Harness | `<name>` | Managed steering | Skill |
| --- | --- | --- | --- |
| Generic AGENTS.md consumers | `agents` | `AGENTS.md` | none |
| Codex | `codex` | non-empty `AGENTS.override.md`, otherwise `AGENTS.md` | `.agents/skills/slopvac-prose/SKILL.md` |
| Claude Code | `claude` | `CLAUDE.md` | `.claude/skills/slopvac-prose/SKILL.md` |
| Oh My Pi | `omp` | `.omp/AGENTS.md` | `.omp/skills/slopvac-prose/SKILL.md` |
| Kiro | `kiro` | `.kiro/steering/slopvac.md` (`inclusion: always` for a new file) | `.kiro/skills/slopvac-prose/SKILL.md` |

Both commands preserve content outside Slopvac's managed markers.
They also preserve skill files that Slopvac did not write.

`slopvac setup <harness> --check` reports each steering block's status.
A block can be `current`, `missing`, `stale`, or `malformed`.
A skill can also be `disabled`. The check leaves files unchanged.

| Exit code | Condition |
| --- | --- |
| 0 | Every item is current or disabled |
| 1 | An item is missing or stale |
| 2 | A file is malformed |

`slopvac setup <harness> --remove` removes Slopvac's managed block and skill.
It deletes the skill directory only when empty.
`slopvac setup --list` prints harness names and their steering and skill paths.

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
All lines of an untracked file fall within the scope.

`--fix` edits source files using deterministic replacements with a single
alternative. It preserves match case and skips replacements that offer multiple
choices. In a diff-scoped run, it leaves unchanged lines alone. The CLI lints
again after applying replacements. Review the resulting diff for meaning.

## Supported file types

Prose directory targets select `.md`, `.mdx`, `.markdown`, `.txt`, `.rst`,
and `.html` files. An explicitly named TOML file is accepted only in
code-comments mode, where Slopvac checks its comments. Comment-mode directory
scans also include TOML files.

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
Comment mode uses the Vale configuration and styles that Slopvac compiles.
`vale.config` and `vale.styles` settings do not change that configuration.

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
| `excluded` | Does not run in that profile. Configuration cannot re-enable it |

A tier is separate from configured severity. `severity = "off"` disables an
otherwise admitted category or rule. A project setting can override a
profile-default `off` at the same level: use `[categories]` for a category
setting and `[rules]` for a rule setting. A rule setting cannot override a
category-level `off` or an `excluded` tier.

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
| `mode` | Whether the CLI checks prose or code comments |
| `profile` | Default rule treatment and thresholds |
| `exclude` | Gitignore-style file exclusions |
| `[thresholds]` | Error and warning limits, density, minimum score, and Unicode dash count |
| `[categories]` | Severity, minimum severity, density budget, and score weight |
| `[rules]` | Severity for an individual rule |
| `[[overrides]]` | Path-specific configuration patches |
| `[locale]` | Spelling target and allowed spellings |
| `[vocabulary]` | Path to a project word blocklist |
| `[vale]` | Vale enablement and binary. `config` and `styles` are accepted but currently have no effect |
| `[guidance]` | Whether `slopvac prime` points agents at writing guidance and semantic review |

### Agent guidance

```toml
[guidance]
write = "auto"             # auto | off
review = "auto"            # auto | ask | off
review_depth = "subagent"  # self | subagent | adversary
```

`write = "off"` drops the writing step. `review = "ask"` prompts before review.
`review = "off"` disables review. The default `review_depth = "subagent"` uses
one fresh-context reviewer pass. The author gives the subagent the document and
the `slopvac prime review` output, plus the original and any source or brief.
The subagent runs lint, the semantic checklist, and a fact check, and edits
nothing. It reports each finding once with rule id, quoted text, and proposed
rewrite, and it lists lost facts and claims stronger than the source. The author
fixes or rebuts each finding.

Set `review_depth = "self"` for an author-run pass, or `"adversary"` for
repeated rounds. Each round gets the earlier rebuttals, and the loop stops when
a round reports no finding the author accepts. If no subagent is available, the
author runs the pass and reports `self (no subagent available)`.
`review = "off"` still disables review. Guidance keys cannot appear in
`[[overrides]]`. With both modes off, `init --harness` and `setup` install no
skill. See [semantic guidance](docs/semantic-guidance.md#configuration).

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

A category with `weight = 0` reports findings without contributing to the score,
error and warning counts, or density gates when any category has a positive
weight. If every category has zero weight, the document score and document-level
error, warning, and density thresholds use all categories together. The Unicode
dash gate always counts its named findings regardless of category weight.

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

`slopvac explain orwell.stale-figure` lists the accepted reasons. The directive
covers the next block, such as a paragraph, list item, or table.
`<!-- slopvac-disable-next-line -->` suppresses all rules in that block. Use
`<!-- slopvac-disable -->` and `<!-- slopvac-enable -->` around a region.
A directive quoted in inline code or a code block has no effect.

[Suppressions and exclusions](docs/suppressions.md) gives the full grammar and
each `meta.invalid-suppression` message. It also covers directives in source
comments, Vale's own comments, and the config controls that exclude files.

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
not contribute to the weighted mean. If all categories have zero weight, the
weighted mean is 100, so the whole-document score determines the result.

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

The [rule reference](docs/rules.md) lists 26 categories.
It describes 167 checked rules and 67 judgment rules.
Each judgment rule includes review questions and examples.

| Family | Categories |
| --- | --- |
| AI register and residue | `ai-residue` and `ai-tells-*`: agentic, content shape, figurative, formatting, register, and structure |
| General prose | `prose-*`: agency, craft, discipline, format, inclusive language, inflation, promotion, and scope |
| Documentation discipline | `docs-discipline` |
| Simplified Technical English | `ste-*`: descriptive, nouns, practices, procedural, punctuation, safety, sentences, verbs, and words |
| Orwell-derived checks | `orwell` |

```sh
slopvac rules --profile strict
slopvac rules --kind judgement --genre consumer --profile normal --format md
slopvac explain ste-sentences.sentence-not-short-or-clear
slopvac lint --rules-dir ./my-rules docs/
```

`slopvac rules --format md` prints each selected rule in full.
Each block contains its question or message, fix, examples, tiers, and source. `--format json` prints the same rules as data for tools.
`--genre <genre>` keeps the categories whose `recommended_for` lists that
genre. The filters `--kind`, `--category`, and `--genre` combine, so a rule
appears only when it passes each one. With `--profile`, md output omits the
rules that the profile excludes. `--include-excluded` keeps them.
`slopvac explain <rule_id> --format md` prints the same block for one rule.
The [rules output reference](docs/rules-output.md) lists every JSON key and
the layout of each md block.

`slopvac prime write` and `slopvac prime review` list no rules. Each prints the
`slopvac rules --kind judgement --genre <genre> --profile <profile> --format md`
command for the document, and the agent passes it the same `--rules-dir` as
lint.

`--rules-dir` adds project categories over packaged YAML and is repeatable. A
project category with the same id replaces the packaged category. Each directory
must exist. It can be empty if the packaged rules provide files. Rule files that
it contains must be valid.

`slopvac rules` also includes the spelling rule generated for the configured
locale. The YAML rule count excludes that generated rule.

## The compiled-rule cache

Slopvac caches compiled Vale styles between runs. Use these commands to inspect
or reclaim the cache:

```sh
slopvac cache
slopvac cache --prune
slopvac cache --all
```

`--prune` removes older compiled trees and ruleset slots. `--all` removes all of those entries. Set
`SLOPVAC_CACHE_DIR` to choose a location. Otherwise Slopvac uses
`$XDG_CACHE_HOME/slopvac` or `~/.cache/slopvac` on Linux,
`~/Library/Caches/slopvac` on macOS, and `%LOCALAPPDATA%/slopvac/Cache` on Windows.
The configured cache paths must be absolute. Ruleset reuse requires verified
ownership and permissions, including the ancestor directories. Unsafe paths and
platforms without these checks use a fresh parse and example proof.
Slopvac does not migrate entries from the old cache in shared temporary storage.

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

Slopvac is evaluating a separate semantic layer with typed decisions. The
current [semantic review](docs/semantic-guidance.md) is a checklist an agent
applies, with no model calls from Slopvac. The typed layer would
run after the current parser has produced exact spans and deterministic
candidates. A provider such as Jev, Laya, Nimble, Kev, or a SemIf-compatible
backend would answer bounded questions while Slopvac code keeps ownership of the
final policy. The same provider interface would support two jobs:

- Detect semantic-only cases that deterministic rules cannot express reliably.
- Check a linter finding against the rule's intended meaning.

A local reranker such as Qwen3-Reranker-0.6B may be tested before the typed
provider when candidate volume is high. It is a recall-first prefilter, never
the final judge, and filtered candidates must remain visible in coverage
measurement. This work lives on the separate `feat/judgement-rewrite` branch.
It is not part of the current CLI or deterministic exit status. See the
[project overview](../../README.md#agentic-judgment)
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
