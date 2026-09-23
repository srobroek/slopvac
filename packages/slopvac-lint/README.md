# slopvac CLI reference

`slopvac` lints prose and source comments for AI writing patterns and writing
quality. The rules cover documentation discipline alongside general prose,
Simplified Technical English, and Orwell-derived checks.

The packaged YAML contains 231 rules across 26 categories: 166 checked rules and
65 contextual rules marked `kind: judgement`. The CLI reports deterministic
findings and scores. Optional model review produces separate advisory results.

See the [project overview](../../README.md) for agent installation and CI
integration.

[Lint documents](#lint-documents) · [Profiles](#profiles) ·
[Configuration](#configuration) · [Scoring](#scoring) ·
[Contextual review](#judgement-layer) · [Rule coverage](#rules)

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

Install [Vale](https://vale.sh) 3.15 or later and put it on `PATH` for the full
deterministic check. `slopvac` generates the Vale configuration and styles.

| Engine | Checks |
| --- | --- |
| Native | Patterns, metrics, and comparisons between text blocks |
| Vale | Compiled patterns, part-of-speech checks, and document metrics |

Missing Vale, or `--no-vale`, leaves selected Vale-backed checks `UNCHECKED` and
returns exit 2. Native findings remain in the report.

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
`.html`, and `.toml` files. TOML input checks comments. Directory scans exclude
`slopvac.toml` and `.slopvac.toml`.

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
| `off` | Does not run under profile defaults |

An explicit category or rule setting can override the profile's treatment.
Inspect the effective rules with `slopvac rules --profile strict` or use
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

Vale's tagger distinguishes the noun in "the deploy failed" from the verb in
"deploy the worker". Every entry needs a `reason`. `replacement` is optional.
Invalid or unreadable blocklists are configuration errors.

[`examples/blocklist.toml`](examples/blocklist.toml) provides a starter. YAML
and JSON formats also work. Without `vocabulary.path`, project blocklist checks
remain inactive. Other word and spelling rules still follow their configured
settings.

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

## Judgement layer

Contextual rules cover questions such as whether a passage repeats one point
or makes a claim without enough support. The model returns `confirm`, `reject`,
`preserve`, or `abstain` for each requested decision.

The CLI does not call a provider. Your harness sends the prepared prompts and
records the responses. These results remain separate from deterministic lint
findings and do not change deterministic pass/fail.

### Prepare a review

For an agent harness:

```sh
slopvac judgement brief README.md --out .slopvac-review --packs fired
```

`brief` writes `brief.md` and `brief.json` alongside the structured run files.
It discovers the configuration, or uses starter defaults when none is present.

`--packs fired` selects packs whose category produced a deterministic finding.
A category without such a finding receives no contextual review through that
selection. Use `--packs all` to include all packs, or provide comma-separated
pack IDs.

For a provider client that consumes JSONL directly:

```sh
slopvac init
slopvac judgement prepare README.md \
  --config slopvac.toml \
  --out .slopvac-review \
  --packs all \
  --max-calls 300
```

`prepare` needs `--config`. It writes deterministic reports before checking the
call budget. Above `--max-calls`, it refuses to write prompts, units, or a
manifest. To approve a larger run, raise the limit or rerun `prepare` with
`--yes`. `brief` accepts a higher `--max-calls` value but has no `--yes` option.

### Call the model and validate responses

Each `prompts.jsonl` row supplies a `call_id` and a `response_schema`. Send
`prompt.system` and `prompt.user` to your model. The user prompt is a JSON
string containing passages and the unit-rule pairs to review.

Write one `responses.jsonl` row per completed call, with the original `call_id`
and the model's parsed JSON object under `response`. Validate each response
before adding it:

```sh
slopvac judgement validate --run .slopvac-review --file response.json
```

`response.json` can contain a bare model response or a `call_id`/`response`
wrapper. Supply `--call-id` to identify the call explicitly, or let validation
infer it. Omitting `--file` reads standard input.

For ordinary response files, validation prints `ok`, `call_id`, and `errors`.
It returns 0 for valid responses, 2 for validation failures, and 1 for unreadable
or malformed JSON. The [evaluation guide](docs/judgement-eval.md) also describes
Claude Code hook payloads and retry handling.

### Finish and compare

After your harness writes `.slopvac-review/responses.jsonl`:

```sh
slopvac judgement finish --out .slopvac-review \
  --responses .slopvac-review/responses.jsonl
slopvac judgement compare --out .slopvac-review
slopvac judgement compare --out .slopvac-review --apply-preview
```

The host checks the response schema and unit ownership, then validates evidence
quotes against the text. `unique-quote` offset salvage relocates an exact quote
that occurs once in its unit. `finish --offset-salvage none` disables that repair.

Failed, truncated, and not-run units reduce coverage. They retain their own
states, separate from model abstentions. Check coverage before interpreting a
report with no confirms.

| Stage | Files |
| --- | --- |
| `prepare` | `prompts.jsonl`, `units.jsonl`, `documents/`, `deterministic/`, and `manifest.json` |
| `brief` | Preparation files plus `brief.md` and `brief.json` |
| `finish` | `findings.jsonl`, `report.json`, and `report.md` |
| `compare --apply-preview` | Accepted rewrite previews under `preview/` |

Model confirms can lower `judgement_adjusted_score`. They do not change the
lint exit status or deterministic error and warning counts. Rewrite previews
leave source files untouched. The checker rejects proposed rewrites that
introduce new deterministic findings.

See [judgement evaluation](docs/judgement-eval.md) for the prompt contract and
coverage definitions. Model review can produce false positives or miss defects.

## Rules

The [generated rule reference](docs/rules.md) lists all 26 categories, including
examples and profile tiers for the 166 checked and 65 contextual rules.

| Family | Categories |
| --- | --- |
| AI register and residue | `ai-residue` and `ai-tells-*`: agentic, content shape, figurative, formatting, register, and structure |
| General prose | `prose-*`: agency, craft, discipline, format, inclusive language, inflation, promotion, and scope |
| Documentation discipline | `docs-discipline` |
| Simplified Technical English | `ste-*`: descriptive, nouns, practices, procedural, punctuation, safety, sentences, verbs, and words |
| Orwell-derived checks | `orwell` |

```sh
slopvac rules --profile strict
slopvac rules --judgement --format json
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

`--prune` keeps the 16 most recently used trees. `--all` removes every cached
tree. Lint runs also prune to 16 trees. Set `SLOPVAC_CACHE_DIR` to choose a
location, or use the default under `XDG_CACHE_HOME`.

To inspect the compiled styles directly:

```sh
slopvac compile --outdir build/vale
slopvac compile --format json
vale --config=build/vale/.vale.ini docs/
```

The routing report names Vale-backed, native, disabled, and contextual rules.
Running Vale alone checks only the compiled Vale portion.

## Exit codes

These codes describe deterministic lint runs:

| Code | Result |
| --- | --- |
| `0` | Selected checks completed within configured thresholds |
| `1` | At least one threshold failed |
| `2` | An incomplete check or invalid configuration |

A passing score does not verify factual correctness or establish authorship.
Model-review commands report their own processing and validation errors.

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
