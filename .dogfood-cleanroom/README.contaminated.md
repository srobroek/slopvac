# slopvac

A prose linter that scores Markdown, reStructuredText, plain text, and HTML
against three rulesets: AI-slop tells, Simplified Technical English, and
Orwell's rules for writing. It emits one line per finding, a 0-100 score per
document, and an exit code a CI job or a pre-commit hook can gate on.

The package ships 216 rules in 23 categories, and the loader adds one generated
spelling rule per locale, so a run assembles 217. A checker executes 150 of
them. The other 67 are `kind: judgement`, held as data for a reviewing agent to
read: no checker runs them and they never fail a run.

## Who it is for

Repositories that review documentation and want the mechanical part of that
review automated. Teams that enforce Simplified Technical English on reference
material, runbooks, and procedures. Anyone who gates LLM-drafted prose: the
`ai-residue`, `ai-tells-*`, and `prose-inflation` categories target that
register and its rhetorical shapes.

## Install

```bash
pip install slopvac        # or: uvx slopvac --help
```

Python 3.11 or newer. Runtime dependencies: click, pydantic, pathspec, rich,
regex, pyyaml, markdown-it-py.

[Vale](https://vale.sh) is an optional external binary that executes 129 of the
150 mechanical rules when present. Without it the run marks those rules
`UNCHECKED` and scores only what the native engine ran, so a missing binary
never reads as a pass.

## Quickstart

```bash
slopvac README.md      # `lint` is the default subcommand
slopvac docs/          # walks the tree for *.md, *.mdx, *.markdown,
                       # *.txt, *.rst, *.html
slopvac init           # write a starter slopvac.toml
slopvac explain prose-inflation.slop-lexicon
```

A failing run prints findings, any `UNCHECKED` notes, a per-category table, and
a verdict:

```
README.md ERROR prose-inflation.slop-lexicon line 12: slop lexicon: robust
FAIL  score 0.0/100  12 finding(s) (7 error, 3 warning, 2 suggestion)
  x README.md: 7 error(s), limit 0    x README.md: score 0.0, minimum 70.0
```

## Commands

### `slopvac lint TARGETS...`

A bare `slopvac FILE` inserts `lint` for you, which is what pre-commit relies
on.

| Flag | Effect |
| --- | --- |
| `--profile {strict,normal,relaxed}` | Override the configured tier for this run. |
| `--config PATH` | Use this config file instead of the nearest discovered one. |
| `--rules-dir DIR` | Layer an extra rule directory over the packaged rules. Repeatable. |
| `--category NAME` | Run only these categories. Repeatable. Unknown names exit 2. |
| `--disable NAME` | Turn off a category, or a qualified `category.rule` id. Repeatable. |
| `--format {text,json,github,sarif}` | Human table, JSON payload, Actions annotations, or SARIF. |
| `--min-score N` | Fail below this 0-100 score. |
| `--max-per-100-words N` | Fail above this finding density. |
| `--locale TAG` | `en-US`, `en-GB`, or `und` to disable spelling. |
| `--no-vale` | Skip the Vale sub-gate and report its rules as unchecked. |
| `--verbose` | Include categories with zero findings in the table. |
| `--explain-config` | Print the resolved settings per file and exit 0 without linting. |

`--explain-config` prints the profile, thresholds, matched override globs,
resolved blocklist path, disabled categories, and the layer that set each
touched setting. `--no-color` drops styling.

### `slopvac rules` and `slopvac explain RULE_ID`

`rules` lists the ruleset with each rule's kind, tier at a profile, severity,
and source citation. `--category`, `--kind`, `--profile`, `--rules-dir`, and
`--format {text,json}` narrow or reshape it. `--judgement` restricts the list to
the 67 rules no checker runs, which is what an agentic reviewer reads.

`explain` prints one rule in full: kind, severity, scope, per-profile tiers,
message, fix, the judgment question if it has one, its exceptions, the
before/after examples, and the provenance. `--format json` adds a ready-made
suppression comment under a `suppression` key.

### `slopvac init`, `compile`, and `reference`

`init` writes a starter `slopvac.toml` with the common overrides commented out;
`--profile` seeds the tier, `--path` names the file, `--force` overwrites.

`compile` compiles the ruleset into a Vale style directory plus a `.vale.ini`,
then prints the routing: how many rules went to Vale, how many stayed native and
why, how many are judgment, and how many the config disabled. `--no-validate`
skips handing each rule to Vale, which runs faster and leaves the routing
unproven.

`--outdir` picks the output path. The default is a cache directory keyed by a
hash of the rules and the resolved config, located from `SLOPVAC_CACHE_DIR`,
then `XDG_CACHE_HOME/slopvac`, then the platform temp directory.

`reference` generates the rules reference document. `--write PATH` writes it,
and `--check` alongside it prints a unified diff and exits 2 when the committed
copy differs from the generated one.

## Configuration

Config discovery walks up from each target: `slopvac.toml`, then
`.slopvac.toml`, then a `[tool.slopvac]` table in `pyproject.toml`. The walk
stops at a directory containing `.git`, so a monorepo package can carry its own
config.

```toml
profile = "normal"

exclude = ["**/node_modules/**", "**/.venv/**", "**/CHANGELOG.md"]

[thresholds]
max_total_per_100_words = 3.0
max_errors = 0
max_warnings = 20
min_score = 70.0
[locale]
default = "en-US"                 # en-US, en-GB, or und
allow = ["behaviour"]             # spelled this way whatever the locale
[vocabulary]
path = "docs/blocklist.toml"      # relative to THIS file
[vale]
enabled = true                    # binary = "vale"
[categories]
prose-scope = "warning"           # bare string == severity
ai-tells-formatting = { max_per_100_words = 2.0, weight = 0.8 }
[rules]
"prose-format.no-unicode-dash" = "off"

[[overrides]]                     # applied in file order
files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
profile = "strict"
[[overrides]]
files = ["docs/**", "!docs/generated/**"]
categories = { docs-discipline = { enabled = false } }
```

Every top-level key must sit above the first `[table]` header, since a TOML
table header captures every key after it.

### Resolution order

Three layers, each patching the one above it **per field**, so an override that
sets only `severity` keeps the profile's threshold: the built-in profile named
by `profile`, then the top-level `[categories]` and `[rules]` tables, then every
`[[overrides]]` block whose `files` glob matches, **in file order**.

slopvac ranks overrides by neither specificity nor strictness. Every matching
block applies and the last block to set a field owns it, so a broader glob
written later wins, and `--explain-config` reports which layer set each
surviving value. Two `[[overrides]]` blocks with the same `files` set are a load
error. Globs use gitignore semantics through `pathspec`, so a leading `!`
negates.

### Profiles

| Profile | For | Density budget | max_errors | min_score |
| --- | --- | --- | --- | --- |
| `strict` | reference, specs, API docs, runbooks | 1.5 / 100 words | 0 | 85 |
| `normal` | README, guides, decision records, essays | 3.0 / 100 words | 0 | 70 |
| `relaxed` | notes, comments, drafts | 8.0 / 100 words | unlimited | none |

The tiers are not a monotonic ordering. `orwell-voice` (passive voice) is
advisory at `strict` and enforced at `normal`, because agentless passive is
correct in a specification. Every profile, `relaxed` included, enforces
suppression validity and the actor-attribution rules. The controlled-vocabulary
category stays off at `normal`, and `relaxed` disables 97 mechanical rules
rather than demoting them.

### Categories

`slopvac rules` lists them. Each carries a title, a description, a score weight,
per-profile density budgets, and a `recommended_for` list of genres. The 23 ids
group into `ai-residue` and four `ai-tells-*`, seven `prose-*`, nine `ste-*`,
then `orwell` and `docs-discipline`.

Category settings are `severity`, `max_per_100_words`, `weight`, and `enabled`.
`severity` both promotes and demotes, so `severity = "error"` promotes a
suggestion to blocking. A per-rule `[rules."cat.rule"]` entry still wins over
it. A category `weight` of 0 scores that category as informational and drops it
from the overall score. Rules take `severity` only, with no per-rule weight.

### Word blocklist

No wordlist ships with the package, and the word-choice rules check nothing
until `[vocabulary] path` points at one. `examples/blocklist.toml` is a starting
file and stays unpackaged.

- TOML, YAML, or JSON. Every entry needs a `word`, a `pos`, and a `reason`, and
  the loader refuses a file with an unexplained entry.
- The part of speech decides the match, through Vale's Penn-tagged `sequence`
  matching. `deploy` blocked as a noun flags "the deploy failed" and leaves
  "deploy the worker" alone.
- No "only these words are allowed" setting exists. A word absent from the file
  passes by definition.
- An `[[overrides]]` block can point a subtree at its own blocklist. Each
  distinct blocklist gets its own Vale compile, because the compile bakes the
  wordlist into the artifact.

## The rule model

A rule is data. Every rule lives in YAML under `src/slopvac/rules/`, and the
loader validates it against a pydantic model, so a malformed rule fails the run
instead of matching nothing quietly. A token or substitution rule needs no
Python. `kind` selects the checker, and the counts below total the assembled
217:

| Kind | What it does | Count |
| --- | --- | --- |
| `pattern` | A regex, with named-group support. | 89 |
| `substitution` | A `from -> to` map; the message names the replacement. Keys are regexes. | 19 |
| `tokens` | Literal phrases, word-boundary matched, longest-first. | 17 |
| `metric` | A counted measurement against a threshold. | 15 |
| `structure` | Block-level shape, needing cross-block comparison. | 6 |
| `vocabulary` | Part-of-speech-keyed blocklist lookup. | 4 |
| `judgement` | Requires a decision no pattern reaches. Never fires. | 67 |

Implemented metrics count words or sentences per unit, clause boundaries, and
adjectives per noun. Five metric rules have no implementation in either engine,
and two more only run under Vale. The run names each in an `UNCHECKED` note
rather than letting it read as compliant prose.

`scope` bounds where a rule applies: `prose` (which excludes code fences, inline
code, URLs, and front matter), `heading`, `sentence`, `paragraph`, `document`,
or `raw`. `text_type` splits procedural from descriptive text and selects the
sentence word cap, 20 words for an instruction or a safety statement against 25
for descriptive text. Block structure comes from markdown-it-py's CommonMark
parser, which reports a source line map per block, so a reported line number
opens the right place in the real file.

Every rule carries a `provenance` block naming its source, and optionally an
issue-qualified ASD-STE100 rule number (`"9:1.2"`) or an Orwell rule id. The
rules cite rule numbers as facts and quote no specification text.

### Deterministic and judgment rules

The 150 checked rules produce findings, gate a build, and agree between two runs
over the same text. Each of the 67 judgment rules declares a
`judgement_question` that must be decidable rather than a matter of taste,
carries `suggestion` severity, and emits no finding. They ship in the same YAML,
so a reviewing agent reads one catalog instead of a second, drifting one.
`slopvac rules --judgement --format json` is that interface.

`examples[].bad` and `examples[].good` double as test fixtures: the loader
compiles every regex, then asserts that each `bad` matches and each `good` does
not, because a rule that stops firing reports every document clean.

### Two engines, one ruleset

`slopvac compile` routes each mechanical rule to Vale or the native engine and
prints the reason for every rule that stays native: Vale rejected the pattern,
the metric has no Vale expression, or the check needs cross-block comparison.
The compile hands each rule to Vale, so execution proves the routing.

Severity resolution, profile tiers, and suppressions stay with slopvac, and the
compiler asks the native engine what level a rule resolves to before it writes
the ini. When Vale runs, the native engine skips the rules Vale owns, so no
finding appears twice. When Vale is unusable it runs what it can and reports the
gap.

## Suppressions

A suppression names an exception from the rule's own closed list and applies to
the following line:

```markdown
<!-- slopvac-allow: rule=prose-inflation.slop-lexicon reason=quotation -->
<!-- slopvac-disable-next-line -->
<!-- slopvac-disable --> ... <!-- slopvac-enable -->
```

`slopvac explain <rule> --format json` prints a ready-made annotation. An
annotation with no `reason`, or with a reason absent from the rule's
`exceptions`, suppresses nothing and reports `meta.invalid-suppression` at
ERROR. "Reads better" is on no list. The last two forms cover a line no rule can
be named for.

## Scoring

Each run reports three numbers. `per_100_words` is raw density over every
finding, comparable across documents of any length. `gating_per_100_words`
counts errors and warnings only, and a density budget checks against that one.
`score` is 0-100, derived from severity-weighted gating density against the
budget, less a bounded suggestion penalty.

Severity weights are 4.0 for an error, 2.0 for a warning, 1.0 for a suggestion.
Within budget the score runs from 100 down to 70 linearly, so "just inside"
differs visibly from "clean". Above budget it decays from 70 to 0, reaching 0 at
four times the budget. With no budget set, the score is `100 - density * 10`.

A suggestion may lower a score and must not fail a run. The gating density
therefore excludes suggestions, and the scorer applies them afterwards as a
penalty capped at 15 points, fully spent at 6.0 suggestions per 100 words. A
document clean of errors and warnings but dense with suggestions lands near 85
and cannot cross the shipped 70.0 minimum.

Below 60 words density says nothing useful, since one finding in a 20-word file
reads as 5.0 per 100 words. Short documents score on the weighted count instead,
at 5 points per weight unit, so one suggestion costs 5 and four errors reach 0.

The document score is the lower of the weighted mean of the per-category scores
and the score from the whole document's findings, because averaging alone
dilutes: 23 categories that found nothing score 100 each and drown the two that
found errors. A run fails when any threshold fails, and the report names each
failure by name.

## Output formats

- `text` prints findings, `UNCHECKED` notes, a per-category table, and a
  verdict.
- `json` emits a versioned payload of `schema_version`, `version`, a `summary`,
  and a `documents` list holding per-file findings, category scores,
  `failure_reasons`, and `unchecked`. The summary recomputes densities over
  total words rather than averaging per document.
- `github` emits `::error` and `::warning` workflow commands, which attach
  findings to the PR diff, plus a `::notice` that carries the score.
- `sarif` emits SARIF 2.1.0 with `partialFingerprints` for stable alert
  identity, ready for `upload-sarif`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Clean, or every finding below every configured threshold. Also: no lintable files matched. |
| `1` | A threshold failed. The run worked; the prose did not. |
| `2` | Nothing was checked: bad config, unknown category or rule id in the config, unloadable ruleset, unreadable blocklist, or a missing target path. |

The 1/2 split is the contract every caller depends on: a hook blocks on 1 and
reports 2 differently, because 2 means nothing was checked. Warnings alone stay
at 0 until you set `max_warnings`. An unknown category or a mistyped rule id
anywhere in the config exits 2 with a did-you-mean rather than checking nothing
quietly.

## pre-commit

```yaml
repos:
  - repo: https://github.com/srobroek/slopvac
    rev: <tag>
    hooks:
      - id: slopvac        # also: slopvac-strict, slopvac-no-vale
```

`slopvac-strict` runs the strict tier, so scope it with `files:`.
`slopvac-no-vale` needs no external binary, and the Vale-routed rules do not
run.

## Extending the ruleset

`--rules-dir DIR` layers `*.yml` files over the packaged rules. A category whose
id already exists **replaces** the packaged one wholesale rather than merging
per rule, so a project that redefines a category owns it. The loader validates
and example-verifies extra rules on the same path as the packaged ones.

## Tests

265 tests cover the CLI, engine, config, ruleset, report, Vale compiler, and
vocabulary loader. Run `pip install -e '.[dev]' && pytest`.

## License

Apache-2.0. The rules restate ASD-STE100 requirements independently and cite
rule numbers as facts. They reproduce no specification text, examples, or
dictionary entries.