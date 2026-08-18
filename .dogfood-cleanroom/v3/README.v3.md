# slopvac

slopvac is a deterministic prose linter and scorer for documentation. It reads
Markdown, plus `.mdx`, `.markdown`, `.txt`, `.rst`, and `.html`. Each finding
carries a rule id and a line number. The whole run reduces to one 0-100 score
for CI to gate on.

Each rule cites its own source: recurring markers of machine-written prose
(AI-slop tells), an independent restatement of ASD-STE100 (Simplified Technical
English), and Orwell's 1946 rules.

Every rule carries its provenance, a fix, and a closed list of named exceptions,
and the loader refuses to start without provenance. The command
`slopvac explain <rule>` prints all of it.

Two commitments run through the whole tool:

- Nothing passes in silence. slopvac never counts a gap in coverage as clean
  prose.
- A misconfiguration is an error rather than a no-op. See [Exit codes](#exit-codes).

## Who it is for

slopvac suits teams that publish documentation and want a mechanical gate on it.
Callers usually take one of these shapes:

- A pre-commit hook.
- A GitHub Action that posts annotations or SARIF.
- A reviewer, human or agent, that needs a machine-readable source of truth for
  the rules a linter *cannot* check.

## Install

slopvac needs Python 3.11 as a minimum. Install it as a tool:

```sh
uv tool install slopvac   # or: pipx install slopvac, pip install slopvac
```

[Vale](https://vale.sh) is an optional companion. If your environment allows a
second binary, install it. Without `vale` on `PATH` the run still completes on
the native rules. slopvac then tells you, per document, how many rules did not
run.

A gap in coverage gets an `UNCHECKED` line on the run: a missing `vale` binary,
an unknown `[locale]` tag, and a rule of the `metric` kind with no
implementation.

## Quickstart

Point slopvac at one file, at a directory, or at a glob. Take the file
`example.md` below, then lint it with a bare path:

```markdown
# Cache warm-up

The runner performs an analysis of the coverage report prior to the merge.
```

```sh
slopvac example.md
```

slopvac treats a bare path as `slopvac lint <path>`. The implicit subcommand
accepts options in any position, as in `slopvac --profile strict docs/`. Here is
the output of that run, verbatim:

```
example.md SUGGESTION ste-sentences.missing-article-or-determiner line 3: Missing article before "The runner".
example.md ERROR prose-inflation.nominalized-verb line 3: nominalisation: performs an analysis -- use the verb ('validate', not 'perform validation')
example.md ERROR prose-discipline.frozen-verb line 3: "performs an analysis" freezes the action in a noun. Use the plain verb.
example.md WARNING prose-craft.wordiness line 3: wordy: use 'a simpler word' instead of 'prior to'
example.md WARNING ste-words.approved-word-substitution line 3: Use "before" rather than "prior to".
example.md ERROR orwell.compound-preposition line 3: Use "before" rather than "prior to".
UNCHECKED example.md: 5 metric rule(s) have no implementation in either engine, so they did NOT run: ai-tells-content-shape.adjective-per-noun-spray, ai-tells-formatting.inline-header-list, ai-tells-register.uniform-paragraph-mass, ste-nouns.multiword-noun-too-long, ste-sentences.complex-text-not-in-vertical-list

slopvac
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━┓
┃ category         ┃ findings ┃ err ┃ warn ┃ /100w ┃ score ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━┩
│ orwell           │        1 │   1 │    0 │  6.67 │    80 │
│ prose-craft      │        1 │   0 │    1 │  6.67 │    90 │
│ prose-discipline │        1 │   1 │    0 │  6.67 │    80 │
│ prose-inflation  │        1 │   1 │    0 │  6.67 │    80 │
│ ste-sentences    │        1 │   0 │    0 │  6.67 │    95 │
│ ste-words        │        1 │   0 │    1 │  6.67 │    90 │
└──────────────────┴──────────┴─────┴──────┴───────┴───────┘
FAIL  score 15.0/100  6 finding(s) (3 error, 2 warning, 1 suggestion) across 1 file(s), 15 words  = 40.00/100w
  x example.md: 3 error(s), limit 0
  x example.md: score 15.0, minimum 70.0
```

These three commands write a config file, show how it resolves, and describe a
single rule:

```sh
slopvac init                          # writes a commented slopvac.toml
slopvac lint docs/ --explain-config   # what actually applies, per file
slopvac explain orwell.stale-figure   # why a rule exists, and how to suppress it
```

slopvac walks a directory recursively and picks up the lintable extensions. It
skips these patterns by default:

- `**/node_modules/**`
- `**/.venv/**`
- `**/dist/**`
- `**/build/**`
- `**/CHANGELOG.md`

## Commands

### `slopvac lint TARGETS...`

Targets are files, directories, or globs. These flags apply:

| Flag | Effect |
| --- | --- |
| `--profile strict\|normal\|relaxed` | Override the configured profile for this run. |
| `--config PATH` | Use this config instead of discovery. |
| `--rules-dir DIR` | Layer an extra rule directory over the packaged rules. Repeatable. |
| `--category NAME` | Run only these categories. Repeatable. An unknown name exits 2. |
| `--disable NAME` | Disable a category or a qualified rule id. Repeatable. |
| `--format text\|json\|github\|sarif` | Output shape. Default `text`. |
| `--min-score N` | Fail below this 0-100 score. |
| `--max-per-100-words N` | Fail above this finding density. |
| `--locale en-US\|en-GB\|und` | Spelling target. `und` disables the spelling check. |
| `--no-vale` | Skip the Vale step. slopvac reports the skipped rules as unchecked. |
| `--verbose` | Show categories that found nothing. |
| `--no-color` | Plain output. |
| `--explain-config` | Print the resolved settings per file, then exit without linting. |

The output formats hold the same findings in different shapes. Pick the one that
matches the tool reading the output:

- **`text`** prints the findings, an `UNCHECKED` line per gap, a per-category
  table, and a verdict that names each failed threshold.
- **`json`** is a versioned payload. It holds `schema_version`, `summary`, and a
  `documents` array. Each document carries every finding, each category score,
  and `failure_reasons`.
- **`github`** emits `::error` and `::warning` workflow commands, so findings
  land on the PR diff. A `::notice` carries the score.
- **`sarif`** is SARIF 2.1.0 for code scanning. Every result carries a
  `partialFingerprints` entry that leaves out the line number. Editing one
  paragraph therefore does not close and reopen every alert below it. SARIF
  output omits suggestions. slopvac categorizes the run by profile, so two
  uploads do not replace each other.

### `slopvac rules`

Each row of the list gives the kind, the severity, the disposition at a profile,
and the source. `--category`, `--kind`, `--format json`, and `--judgement`
filter the list. `--judgement` returns only the rules that no linter can check.
Each one comes with the decidable question a reviewer must answer.

### `slopvac explain RULE_ID`

The output holds the message, the fix, the tiers per profile, the examples, and
the provenance. It ends with the closed exception list and a suppression comment
you can paste. Use `--format json` for tooling. An unknown rule id exits 2.

### `slopvac init`

A starter `slopvac.toml` gets written. The common overrides are present but
commented out. `--profile` sets the profile in the generated file, and `--path`
names the file. Caution: `--force` overwrites an existing file. A test loads the
starter config, so the shipped example stays valid.

### `slopvac compile`

The ruleset compiles into Vale styles. slopvac hands mechanical rules to Vale,
and the native engine runs the rules that stay behind. The output reports the
routing:

- How many rules Vale took.
- How many stayed native, and *why* each one stayed.
- How many carry the `judgement` kind and so check nothing.
- How many this config disabled.

`--outdir` writes the styles somewhere you can point Vale at by hand, as in
`vale --config=<outdir>/.vale.ini docs/`. The default target is a cache keyed by
a hash of the rules and the resolved config. Relocate that cache with
`SLOPVAC_CACHE_DIR` or `XDG_CACHE_HOME`.

By default the compile step *executes* Vale against each rule. A pattern that Go
cannot compile therefore appears here, and that rule falls back to the native
engine instead of matching nothing in silence. `--no-validate` skips the
execution step. That option runs faster and leaves the routing unproven.

### `slopvac reference`

The generated Markdown reference splits into checked rules and rules of the
`judgement` kind. `--write PATH` writes the file. With `--write PATH --check` the
command exits 2 and prints a unified diff when the committed copy is stale.

## Configuration

Discovery walks up from each target. It looks for `slopvac.toml` first, then
`.slopvac.toml`, then a `[tool.slopvac]` table in `pyproject.toml`. The walk
stops at a `.git` directory. A package in a monorepo can therefore carry its own
config.

slopvac rejects unknown keys. It also rejects unknown category and rule names at
every layer, including the names inside each `[[overrides]]` block.

```toml
#-- 1. the built-in profile
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

#-- 2. the top-level tables
[categories]
prose-scope = "warning"             # shorthand for { severity = "warning" }

[categories.ai-tells-formatting]
max_per_100_words = 2.0             # density budget for this category
weight = 0.5                        # contribution to the score; 0 = informational
enabled = true

[rules]
"prose-format.no-unicode-dash" = "off"   # shorthand for { severity = "off" }

#-- 3. glob-scoped overrides, applied in FILE ORDER
[[overrides]]
files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
profile = "strict"

[[overrides]]
files = ["docs/**", "!docs/generated/**"]
[overrides.categories.prose-scope]
enabled = false
```

A bare severity string stands in for the whole table, for categories and for
rules alike. `severity = "off"` is the documented way to disable a rule.
Per-rule `weight` does not exist. Weight reaches the score only from a category.

### How resolution works

The layers apply in order, and each one patches the layer above it **per
field**. An override that sets only `severity` therefore keeps the profile's
threshold.

1. The built-in profile named by `profile`.
2. The top-level `[categories]` and `[rules]` tables.
3. Every `[[overrides]]` block whose `files` glob matches.

Globs use gitignore semantics from `pathspec`, so `!` negates a pattern. One
scope can list more than one pattern. Overrides form an array of blocks rather
than a table keyed by glob. `docs/**` together with `!docs/generated/**` is then
one scope with one set of settings.

Precedence follows **file order**. It follows neither specificity nor a
strictest-wins rule. Every matching block applies. The last block to set a field
owns that field. A later, broader pattern therefore beats an earlier, narrower
one. If you reorder two blocks, the result changes.

Specificity ranking loses because no ordering on globs stays predictable.
Strictest-wins loses because with it you could not relax a vendored or generated
subtree such as `**/vendor/**` or `docs/generated/**`, which is the main reason
overrides exist.

Two blocks with the *same* scope are a validation error, and slopvac compares
the two scopes as sets of patterns. For each setting that any layer touched,
`--explain-config` names the block that set the surviving value.

The report below covers one file under two matching override blocks. Each
surviving setting names its source:

```
docs/api/reference.md
  profile: strict
  overrides: docs/**, docs/api/**
  thresholds: {'max_total_per_100_words': 1.5, 'max_errors': 0, 'min_score': 85.0}
  set by:
    categories.prose-scope: overrides[1] (docs/api/**)
    profile: overrides[0] (docs/**)
```

The shipped profiles differ in these document gates. The numbers below are the
defaults for each profile:

| Profile | `max_total_per_100_words` | `max_errors` | `min_score` |
| --- | --- | --- | --- |
| `strict` | 1.5 | 0 | 85 |
| `normal` | 3.0 | 0 | 70 |
| `relaxed` | 8.0 | unlimited | none |

A rule's own disposition per profile lives in its `tiers` map, and those tiers
do not form a strict ordering. A rule can invert that ordering, because passive
voice that names no actor is correct in a specification and wrong in a README.
`slopvac rules` prints the disposition at a profile, and `--format json` gives
it to a tool.

## The rule model

A rule is data rather than code. Each rule is YAML, and a Pydantic model
validates it at load time. A malformed rule fails the run. The loader compiles
every regex and executes every example. The `bad` text must match its own
pattern, and the `good` text must not match.

A rule whose pattern never fires would report every document clean, which looks
exactly like good prose. Validation therefore fails at load time instead. Adding
a lexical or a substitution rule needs no Python. `--rules-dir` layers your own
directory over the 216 packaged rules in 23 categories, plus the spelling rule
that `[locale]` generates.

Each rule has an id qualified as `<category>.<rule>`. It also carries a `kind`
that selects the checker, a severity, a message that names the fix, a scope, a
per-profile `tiers` map, and required `provenance`. Optionally it carries `fix`,
`examples`, `allowlist`, and a closed `exceptions` list.

The `kind` field takes one of seven values, and each value names a different
checker:

| Kind | What it does |
| --- | --- |
| `tokens` | Literal phrases, matched on word boundaries. |
| `pattern` | A regex. |
| `substitution` | A from-to map. The message names the replacement. |
| `vocabulary` | A lookup keyed by part of speech against the configured blocklist. |
| `metric` | A counted measurement against a threshold: sentence words, clause boundaries, passive ratio, syllables per word. Five shipped metric rules have no implementation in either engine, and the run lists them on an `UNCHECKED` line. |
| `structure` | Block-level shape that needs cross-block context, such as a heading-level skip. |
| `judgement` | Not mechanizable. Never produces a finding. slopvac carries it so that a reviewer reads one source of truth. |

Scope keeps a rule off text it must not see. The `prose` scope leaves out code
fences, inline code, URLs, and front matter. The `heading`, `sentence`,
`paragraph`, `document`, and `raw` scopes widen or narrow that view.

A match written entirely in capitals is exempt by default. An all-caps token in
technical prose names an identifier, an initialism, an RFC 2119 keyword, or a
safety marker.

### Severity resolution

The narrowest setting wins. The layers rank in this order, strongest first:

1. A per-rule override.
2. An *authored* category severity.
3. The tier's disposition.
4. The rule's shipped severity.

An advisory tier caps a rule at `suggestion`, so that rule alone cannot fail a
run. A category severity that a human wrote overrides the cap in either
direction. A category severity merely inherited from the profile does not.

### Suppression

Suppression is an annotation contract rather than a comment convention. Each
annotation names an exception from that rule's own closed list, and it applies
to the following line:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=dead-metaphor -->
```

slopvac does not act on an annotation that gives no reason, and it does not act
on a reason absent from the list. It reports both as `meta.invalid-suppression`
at ERROR. "Reads better" sits on nobody's list. For blunter control, wrap the
span in `<!-- slopvac-disable -->` and `<!-- slopvac-enable -->`, or use
`<!-- slopvac-disable-next-line -->`.

One further exemption stands apart. A rule that declares the `quotation`
exception does not fire inside a quoted span on the same line. A style guide can
therefore print the phrase it forbids without failing its own gate.

### Vocabulary

No blocklist ships with slopvac. A packaged dictionary enforced as an
*allowlist* makes every unlisted word a finding, and it therefore drives a
document with zero errors down to a score of 0.0.

A blocklist is an editorial position, so you supply it. Point `[vocabulary]
path` at a file whose entries each carry a `word`, a `pos`, and a `reason`. The
part of speech matters here, because `deploy` is a good verb and a poor noun.
See `examples/blocklist.toml` for a starter.

Each subtree can name its own blocklist through an override. slopvac loads the
blocklist before it reads any document.

## How scoring works

slopvac reports these numbers, because they answer different questions and none
replaces another:

- **`per_100_words`** is raw density over every finding. It compares across
  documents of any length.
- **gating density** covers errors and warnings only. The budget,
  `max_total_per_100_words`, checks this number.
- **`score`** runs from 0 to 100. Errors count 4, warnings 2, and suggestions 1;
  gating density under those weights is the weighted density. The score derives
  from weighted density against the budget, less a bounded suggestion penalty. A
  badge shows this number, and `min_score` reads it.

One rule forces that split: a suggestion may lower a score, but it must not fail
a run.

Inside the budget the score falls linearly from 100 to 70, so "just inside"
looks visibly different from "clean". Above the budget the score decays from 70
toward 0. It reaches 0 at four times the budget rather than all at once.

slopvac then subtracts the suggestions as a penalty. The penalty caps at 15
points and reaches the full 15 points at a suggestion density of 6 per 100
words. A document free of errors and warnings but dense with advice therefore
lands near 85. It cannot cross the shipped minimum of 70.

Below 60 words, density means nothing. One finding in a 20-word error message
reaches 5.0 per 100 words, which fails every budget. slopvac scores a short
document on weighted *counts* instead. One suggestion costs 5 points, one error
costs 20 points, and four errors reach zero. That path is harsher per finding.

The document score is the **lower** of two figures:

- The weighted mean of the per-category scores.
- The same calculation over the document's own findings.

Averaging alone is too kind. A category that found nothing scores 100, and 22
such scores outweigh the one category that did find errors. When one category
sits far over budget and the rest stay clean, the document figure alone loses
that signal. A category with `weight = 0` contributes to neither figure.

Across more than one document, the summary recomputes density over the total
word count. It takes a word-weighted mean of the scores, so a 30-word stub
cannot outweigh a 3,000-word guide.

A document fails when any configured threshold fails. Every failure names itself
and quotes the figure it checked: too many errors, too many warnings, gating
density over the total budget, a score under `min_score`, or a category over its
own density budget.

## Exit codes

The 1-versus-2 split is the contract. A caller that distinguishes prose failure
from run failure branches on all three codes:

| Code | Meaning |
| --- | --- |
| `0` | Clean, or findings below every configured threshold. Also: no lintable files matched. |
| `1` | A configured threshold failed. |
| `2` | Do not trust the result: a problem with the config, the ruleset, the target, or the blocklist. |

### Causes of exit 2

Exit 2 covers a config error, an unknown category name, an unknown rule name, an
unloadable ruleset, a missing target, a broken blocklist, and a stale
`reference --check` diff. A mistyped rule id in `slopvac.toml` exits 2 and prints
a did-you-mean.

Unless you set `max_warnings`, warnings alone stay at 0. Prose cannot reach exit
2. That code means slopvac checked nothing, and a hook must shout differently at
it than at a failing document.

## License

Apache-2.0.

## Findings not applied

- `vague-attribution-remainder`, line 10: subject.md names no catalog, author, URL, or file for the AI-slop tells, so naming one would invent a source; I glossed the term instead.
- `concrete-floor` and `bare-quantifier-with-figure-available`, lines 44-48 / 46: the shipped Vale-versus-native split is not a number subject.md contains, so I removed the "most"/"the rest" quantifiers and moved the routing to `slopvac compile`, where the counts are reported.
- `organic-consequence-remainder`, line 433: subject.md names no chooser for the 4:2:1 severity weights and no reason for that ratio.
- `organic-consequence-remainder`, lines 439-440: subject.md names no chooser for the 15-point cap or the 6-per-100-words spend point, and no reason for either figure.
- `figurative-verb-verdict-remainder`, lines 456-457: the arithmetic the finding asks for (what the mean becomes at one category of 40 and twenty of 100) is not in subject.md; I replaced the metaphor with the 22-of-23 count instead.
- `hollow-acknowledgment` and `concrete-floor`, lines 318-320: subject.md names no rule id whose `tiers` map inverts and no pair of dispositions, so I pointed at `slopvac rules` and its `--format json` output instead.
- `over-writing-remainder`, lines 284-287: I compressed the rejected alternatives and gave them the real globs rather than deleting them, because they are the only statement in the document of why precedence is file order.
- `risk-level-word-missing-or-wrong`, line 172: I added the caution marker, but the recovery claim ("not recoverable unless committed") is not a fact subject.md contains.
