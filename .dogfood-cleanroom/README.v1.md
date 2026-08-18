# slopvac

A deterministic prose linter and scorer for documentation. It reads Markdown (and
`.mdx`, `.markdown`, `.txt`, `.rst`, `.html`), reports findings with a rule id and
a line number, and reduces the whole run to a 0–100 score that CI can gate on.

The ruleset is drawn from three sources, cited per rule: AI-slop tells, an
independent restatement of ASD-STE100 (Simplified Technical English), and Orwell's
1946 rules. Nothing is a black box — every rule carries provenance, a fix, and a
closed list of named exceptions, and `slopvac explain <rule>` prints all of it.

**Who it is for.** Teams that publish documentation and want a mechanical gate on
it: a pre-commit hook, a GitHub Action posting annotations or SARIF, or an agentic
reviewer that needs a machine-readable source of truth for the rules a linter
*cannot* check. Two design commitments run through the whole tool:

- **Nothing silently passes.** A missing Vale binary, an unknown locale tag, a
  metric with no implementation — each is reported as `UNCHECKED` on the run
  rather than counted as clean prose.
- **A misconfiguration is an error, not a no-op.** A mistyped rule id in
  `slopvac.toml` exits 2 with a did-you-mean, because "I disabled it and the gate
  still fails" is the worst failure mode available.

## Install

Requires Python 3.11 or newer.

```sh
uv tool install slopvac   # or: pipx install slopvac, pip install slopvac
```

[Vale](https://vale.sh) is an optional but recommended companion. slopvac compiles
its own ruleset into Vale styles and hands most of the mechanical rules to it; the
rest run in the native engine. Without `vale` on `PATH` the run still completes on
the native rules and tells you, per document, how many rules did not run.

## Quickstart

```sh
slopvac README.md
```

A bare path is treated as `slopvac lint <path>`, so the implicit subcommand works
with options in any position: `slopvac --profile strict docs/`.

```
README.md WARNING prose-craft.future-tense line 12: future tense: will -- describe what it does now
README.md ERROR orwell.compound-preposition line 31: Use "before" rather than "prior to".

slopvac
category           findings  err  warn  /100w  score
orwell                    1    1     0   0.42     88
prose-craft               1    0     1   0.42     94

FAIL  score 61.0/100  2 finding(s) (1 error, 1 warning, 0 suggestion) across 1 file(s), 238 words  = 0.84/100w
  x README.md: 1 error(s), limit 0
```

Then write a config and tune from there:

```sh
slopvac init                          # writes a commented slopvac.toml
slopvac lint docs/ --explain-config   # what actually applies, per file
slopvac explain orwell.stale-figure   # why a rule exists, and how to suppress it
```

Directories are walked recursively for lintable extensions. `**/node_modules/**`,
`**/.venv/**`, `**/dist/**`, `**/build/**`, and `**/CHANGELOG.md` are excluded by
default — a generated changelog is not authored prose.

## Commands

### `slopvac lint TARGETS...`

Files, directories, or globs. Useful flags:

| Flag | Effect |
| --- | --- |
| `--profile strict\|normal\|relaxed` | Override the configured tier for this run. |
| `--config PATH` | Use this config instead of discovery. |
| `--rules-dir DIR` | Layer an extra rule directory over the packaged rules. Repeatable. |
| `--category NAME` | Run only these categories. Repeatable; an unknown name exits 2. |
| `--disable NAME` | Turn off a category or a qualified rule id. Repeatable. |
| `--format text\|json\|github\|sarif` | Output shape. Default `text`. |
| `--min-score N` | Fail below this 0–100 score. |
| `--max-per-100-words N` | Fail above this finding density. |
| `--locale en-US\|en-GB\|und` | Spelling target; `und` disables the spelling check. |
| `--no-vale` | Skip the Vale sub-gate, and report what it skipped as unchecked. |
| `--verbose` | Show categories that found nothing. |
| `--no-color` | Plain output. |
| `--explain-config` | Print the resolved settings per file and exit without linting. |

The formats: **`text`** is findings, an `UNCHECKED` line per gap, a per-category
table, and a verdict naming each failed threshold. **`json`** is a versioned
payload with `schema_version`, `summary`, and a `documents` array carrying every
finding, category score, and `failure_reasons`. **`github`** emits
`::error`/`::warning` workflow commands so findings land on the PR diff, plus a
`::notice` with the score. **`sarif`** is SARIF 2.1.0 for code scanning: every
result carries a `partialFingerprints` entry that excludes the line number, so
editing one paragraph does not close and re-open every alert below it. Suggestions
are omitted from SARIF, and the run is categorised by profile so two uploads do
not replace each other.

### `slopvac rules`

Lists the ruleset with each rule's kind, severity, disposition at a profile, and
source. `--category`, `--kind`, `--format json`, and `--judgement` filter it.
`--judgement` is the interesting one: it returns only the rules no linter can
check, each with the decidable question a reviewer must answer.

### `slopvac explain RULE_ID`

One rule in full: message, fix, tiers per profile, examples, provenance, and the
closed exception list with a ready-to-paste suppression comment. `--format json`
for tooling. An unknown rule id exits 2.

### `slopvac init`

Writes a starter `slopvac.toml` with the common overrides commented out.
`--profile` seeds the tier, `--path` names the file, `--force` overwrites. The
starter config is itself covered by a test that loads it.

### `slopvac compile`

Compiles the ruleset into Vale styles and prints the routing: how many rules Vale
took, how many stayed native and *why* each one did, how many are judgement-only,
and how many this config disabled. `--outdir` writes them somewhere you can point
Vale at by hand (`vale --config=<outdir>/.vale.ini docs/`); the default is a cache
keyed by a hash of the rules and the resolved config (relocate it with
`SLOPVAC_CACHE_DIR` or `XDG_CACHE_HOME`). By default the compile step
*executes* Vale against each rule, so a pattern Go will not compile is discovered
here and falls back to the native engine rather than silently matching nothing;
`--no-validate` skips that, which is faster and leaves the routing unproven.

### `slopvac reference`

Generates the rules reference as markdown, split into checked and judgement rules.
`--write PATH` writes it; `--write PATH --check` exits 2 with a unified diff when
the committed copy is stale, which is what makes a generated document in the repo
trustworthy.

## Configuration

Discovery walks up from each target looking for `slopvac.toml`, then
`.slopvac.toml`, then a `[tool.slopvac]` table in `pyproject.toml`, stopping at a
`.git` directory. A monorepo package can therefore carry its own config.

Unknown keys are rejected. Unknown category and rule names are rejected, at every
layer including inside each `[[overrides]]` block.

```toml
# 1. the built-in profile
profile = "normal"                  # strict | normal | relaxed

exclude = ["**/vendor/**", "**/CHANGELOG.md"]

[thresholds]
max_errors = 0                      # default 0
max_warnings = 12                   # unset by default: warnings alone do not fail
max_total_per_100_words = 3.0
min_score = 70

[locale]
default = "en-US"                   # en-US | en-GB | und
allow = ["Colour", "OrganisationId"]

[vocabulary]
path = "docs/blocklist.toml"        # off unless set; relative to THIS file

[vale]
enabled = true
binary = "vale"

# 2. the top-level tables
[categories]
prose-scope = "warning"             # shorthand for { severity = "warning" }

[categories.ai-tells-formatting]
max_per_100_words = 2.0             # density budget for this category
weight = 0.5                        # contribution to the score; 0 = informational
enabled = true

[rules]
"prose-format.no-unicode-dash" = "off"   # shorthand for { severity = "off" }

# 3. glob-scoped overrides, applied in FILE ORDER
[[overrides]]
files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
profile = "strict"

[[overrides]]
files = ["docs/**", "!docs/generated/**"]
[overrides.categories.prose-scope]
enabled = false
```

A bare severity string stands in for the whole table for both categories and
rules, because setting one rule's severity is the dominant edit anyone makes.
`severity = "off"` is the documented way to disable. There is deliberately no
per-rule `weight`: weight reaches the score only from a category.

### How resolution works

Three layers, each patching the one above **per field**, so an override that sets
only `severity` keeps the profile's threshold:

1. the built-in profile named by `profile`
2. the top-level `[categories]` and `[rules]` tables
3. every `[[overrides]]` block whose `files` glob matches

Globs use gitignore semantics via `pathspec`, so `!` negates and one scope can be
several patterns. Overrides are an array of blocks rather than a table keyed by
glob precisely so that `docs/**` plus `!docs/generated/**` is one scope with one
set of settings.

**Precedence is file order, not specificity and not strictest-wins.** Every
matching block applies and the last one to set a field owns it — so a later,
broader pattern beats an earlier, narrower one, and reordering two blocks changes
the result. Specificity ranking was rejected because no ordering on globs is
predictable; strictest-wins was rejected because it makes relaxing a vendored or
generated subtree impossible, which is the main reason overrides exist.

Two costs of that choice are paid explicitly. Two blocks with the *same* scope are
a validation error, compared as a set of patterns. And `--explain-config` prints,
per setting that any layer touched, which block set the surviving value:

```
docs/api/reference.md
  profile: strict
  overrides: docs/**, docs/api/**
  thresholds: {'max_total_per_100_words': 1.5, 'max_errors': 0, 'min_score': 85.0}
  set by:
    categories.prose-scope: overrides[1] (docs/api/**)
    profile: overrides[0] (docs/**)
```

Profiles ship these document gates:

| Profile | `max_total_per_100_words` | `max_errors` | `min_score` |
| --- | --- | --- | --- |
| `strict` | 1.5 | 0 | 85 |
| `normal` | 3.0 | 0 | 70 |
| `relaxed` | 8.0 | unlimited | none |

The tiers are not a simple ordering. A couple of rules invert on purpose, because
agentless passive voice is correct in a specification and wrong in a README.

## The rule model

A rule is data, not code: YAML validated against a Pydantic model at load time. A
malformed rule fails the run, every regex is compiled, and every example is
executed — `bad` text must match its own pattern and `good` text must not. A rule
whose pattern no longer fires would report every document clean, which is
indistinguishable from good prose, so the loader refuses to ship one. Adding a
lexical or substitution rule needs no Python; `--rules-dir` layers your own
directory over the 216 packaged rules in 23 categories, plus the spelling rule
generated from `[locale]`.

Each rule has an id qualified as `<category>.<rule>`, a `kind` selecting the
checker, a severity, a message naming the fix, a scope, a per-profile `tiers` map,
required `provenance`, and optionally `fix`, `examples`, `allowlist`, and a closed
`exceptions` list. `kind` is one of:

| Kind | What it does |
| --- | --- |
| `tokens` | Literal phrases, word-boundary matched. |
| `pattern` | A regex. |
| `substitution` | A from → to map; the message names the replacement. |
| `vocabulary` | Part-of-speech-keyed lookup against the configured blocklist. |
| `metric` | A counted measurement against a threshold (sentence words, clause boundaries, passive ratio, syllables per word, …). |
| `structure` | Block-level shape needing cross-block context, such as heading-level skips. |
| `judgement` | Not mechanizable. Never produces a finding; carried so a human or agentic reviewer reads one source of truth. |

Scope keeps rules off text they should not see: `prose` excludes code fences,
inline code, URLs, and front matter, while `heading`, `sentence`, `paragraph`,
`document`, and `raw` widen or narrow it. A match written entirely in capitals is
exempt by default, because an all-caps token in technical prose is usually an
identifier, an initialism, an RFC 2119 keyword, or a safety marker.

**Severity resolution**, narrowest wins: a per-rule override beats an *authored*
category severity, which beats the tier's disposition, which beats the rule's
shipped severity. An advisory tier caps a rule at `suggestion` so it cannot fail a
run on its own; a category severity written by a human overrides that in either
direction, and one merely inherited from the profile does not.

**Suppression is an annotation contract**, not a comment convention. A suppression
must name an exception from that rule's own closed list, and applies to the
following line:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=dead-metaphor -->
```

An annotation with no reason, or a reason absent from the list, is reported as
`meta.invalid-suppression` at ERROR rather than honoured — "reads better" is
deliberately on nobody's list. `<!-- slopvac-disable -->` /
`<!-- slopvac-enable -->` and `<!-- slopvac-disable-next-line -->` are the blunt
instruments. Separately, a rule declaring the `quotation` exception does not fire
inside a quoted span on the same line, so a style guide can print the phrase it
forbids without failing its own gate.

### Vocabulary

There is no packaged wordlist, and the absence is the design. An earlier version
shipped an extracted dictionary enforced as an *allowlist*, which made every
unlisted word a finding and drove documents with zero errors to a score of 0.0. A
wordlist is an editorial position, so it comes from the project: point
`[vocabulary] path` at a file whose entries each carry a `word`, a `pos`, and a
`reason`. The part of speech is the point, since `deploy` is a good verb and a poor
noun. See `examples/blocklist.toml` for a starter. A blocklist can be overridden
per subtree, and it is loaded before any document is read, so a broken one is a
config error rather than a silently empty gate.

## How scoring works

Three numbers, because they answer different questions and none replaces another:

- **`per_100_words`** — raw density, every finding. Comparable across documents of
  any length; a count, not a judgement.
- **gating density** — errors and warnings only. This is what the budget is
  checked against.
- **`score`** — 0–100, derived from severity-weighted gating density against the
  budget, less a bounded suggestion penalty. This is what a badge shows and what
  `min_score` reads.

The rule that forces this split: **a suggestion may lower a score but must not
fail a run.** Severity weights are error 4, warning 2, suggestion 1.

Within a budget the score runs 100 down to 70 linearly, so "just inside" is
visibly different from "clean". Above it the score decays from 70 to 0, reaching 0
at four times the budget rather than cliff-edging. Suggestions are then subtracted
as a penalty capped at 15 points, fully spent at a suggestion density of 6 per 100
words — so a document clean of errors and warnings but dense with advice lands
near 85 and cannot cross the shipped 70 minimum.

Below 60 words density is meaningless — one finding in a 20-word error message is
5.0 per 100 words and would fail every budget — so short documents are scored on
weighted *counts* instead: one suggestion costs 5 points, one error costs 20, four
errors reach zero. That path is harsher per finding on purpose.

The document score is the **lower** of two figures: the weighted mean of the
per-category scores, and the same calculation applied to the document's own
findings. Averaging alone is too kind, since twenty-odd categories that found
nothing score 100 each and drown the two that found errors; the document figure
alone loses the signal that one category is far over budget while the rest are
clean. A category with `weight = 0` contributes to neither.

Across several documents, the summary recomputes density over total words and
takes a word-weighted mean of scores, so a 30-word stub cannot outweigh a
3,000-word guide.

A document fails when any configured threshold fails, and every failure names
itself and quotes the figure checked: too many errors, too many warnings, gating
density over the total budget, score under `min_score`, or a category over its own
density budget.

## Exit codes

Every caller — pre-commit, the Action, CI — branches on these, and the 1/2 split
is the contract:

| Code | Meaning |
| --- | --- |
| `0` | Clean, or findings below every configured threshold. Also: no lintable files matched. |
| `1` | A threshold failed. The run worked; the prose did not. |
| `2` | The run could not be trusted: bad config, unknown category or rule name, unloadable ruleset, missing target, broken blocklist, a stale `reference --check`. |

Warnings alone stay at 0 unless the project sets `max_warnings`. Exit 2 is not
reachable from prose: it means nothing was checked, and a hook should shout
differently at it than at a failing document.

## License

Apache-2.0.
