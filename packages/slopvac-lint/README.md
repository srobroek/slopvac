# slopvac

Score prose against three rulesets: AI-slop patterns, Simplified Technical
English, and Orwell's rules restated as objective tests.

Reports a finding density per 100 words and a 0-100 score, per category and
overall, with warn and error levels you set per category.

```sh
uvx slopvac README.md
uvx slopvac --profile strict docs/
uvx slopvac --format json docs/ | jq .summary
```

## Install

```sh
uv tool install slopvac     # persistent, no per-call resolution
uvx slopvac --help          # or run it without installing
pipx install slopvac
```

[Vale](https://vale.sh) 3.15 or later executes most of the ruleset and belongs on
your PATH. `slopvac` compiles its own YAML rules into a Vale style directory
and generates the `.vale.ini` it passes to Vale.

| Engine | Rules | Covers |
| --- | --- | --- |
| Vale | 132 | token, regex, and substitution matching; sentence and paragraph word counts; part-of-speech checks against your word blocklist; whole-document ratios |
| built-in | 18 | patterns Go's regex engine rejects, metrics with no Vale form, and block-shape comparisons |
| neither | 67 | rules stating a question a reviewer answers; `slopvac rules --judgement` lists them |

Without the binary the run still scores the 18 built-in rules and reports the rest
as `UNCHECKED`, so a partial check never reads as a pass. `--no-vale` reports the
same way.

`slopvac compile --format json` prints the current split, and
[`docs/rules.md`](docs/rules.md) lists every rule.

Inspect the routing, or run Vale by hand against the generated config:

```sh
slopvac compile --outdir build/vale
vale --config=build/vale/.vale.ini docs/
```

## Profiles

A profile is the strictness dial. It sets which rules run, how loud each one is,
and what gates the document must clear.

| Profile | For | Sentence cap | Approved-word check |
| --- | --- | --- | --- |
| `strict` | reference, specs, API docs, runbooks | 20 procedural / 25 descriptive | on |
| `normal` | README, guides, decision records | 25 advisory | off |
| `relaxed` | notes, comments, drafts | advisory | off |

`normal` is the default. `strict` on an existing repository produces a wall of
findings, which teaches people to ignore the tool.

### What strictness changes

Each rule declares a *tier* per profile, and the tier decides how the rule
reports:

| Tier | Effect |
| --- | --- |
| `enforced` | keeps its shipped severity, so it can reach `error` |
| `advisory` | caps at `suggestion`, so it lowers the score but never fails a run |
| `off` | does not run |

Beyond the tiers, a profile sets the gates the whole document must clear:

| Profile | Total density budget | Max errors | `min_score` |
| --- | --- | --- | --- |
| `strict` | 1.5 / 100 words | 0 | 85 |
| `normal` | 3.0 / 100 words | 0 | 70 |
| `relaxed` | 8.0 / 100 words | unlimited | none |

At `relaxed` the run reports the score for information and gates nothing.

Two rules invert the tier ordering on purpose. Passive voice is advisory at
`strict` and enforced at `normal`, because the agentless passive is correct in a
specification and wrong in a guide.

A profile never overrides its own tiers. Naming a category in `slopvac.toml` and
asking for `error` beats the advisory cap, because a human wrote it. The value
the profile itself supplied does not, which is what stops a profile from
contradicting its own tiers.

### Genres

Categories declare the genres they suit, in a `recommended_for` field that
[`docs/rules.md`](docs/rules.md) tabulates:

`adr`, `api-docs`, `change-comms`, `consumer-docs`, `essay`, `guide`,
`internal-docs`, `pr-description`, `readme`, `reference`, `runbook`,
`source-comments`

Genre and profile are separate. The genre says what the document is, and the
profile says how hard to press. `genre_recommendation()` maps one to the other so
that a caller recommends rather than asks:

| Genre | Profile |
| --- | --- |
| `reference`, `api-docs`, `runbook`, `spec`, `procedure`, `safety` | `strict` |
| `issue`, `comment`, `note`, `draft`, `chat`, `scratch` | `relaxed` |
| anything else | `normal` |

The `review-docs` skill reads both fields. It picks the profile from the genre,
and enables the categories whose `recommended_for` names that genre.

## Configuration

`slopvac init` writes a `slopvac.toml`. Three layers patch each other per
field:

1. the profile
2. the `[categories]` and `[rules]` tables
3. every `[[overrides]]` block whose glob matches, in file order

```toml
profile = "normal"

[thresholds]
max_errors = 0
min_score = 70

[categories]
ste-vocabulary = "off"

[rules]
"prose-format.no-unicode-dash" = "off"    # house style uses real em dashes

[[overrides]]
files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
profile = "strict"
```

Severity is the only per-rule setting, so a bare string stands in for the table
form: `"prose-format.no-unicode-dash" = "off"` and `[rules."prose-format.no-unicode-dash"]`
with `severity = "off"` are the same thing. The same shorthand works for a
category.

Severity is a **set at every layer, not a cap**. A category's `severity` promotes
as well as demotes, and so does a rule's, so `severity = "error"` on a category
does turn its suggestions into gate failures. Narrowest wins: a rule override
beats its category, which beats the profile's disposition, which beats the
severity the rule ships with.

A misspelled rule id or category name is an **error**, not a silent no-op,
including inside an `[[overrides]]` block. `slopvac` refuses to lint and gives
the closest real name, because the alternative failure is "I disabled it and the
gate still fails."

### How overlapping globs resolve

Every matching `[[overrides]]` block applies, in **file order**, and the last
block to set a field owns that field. It is not strictest-wins and not
most-specific-wins:

```toml
[[overrides]]
files = ["x.md"]
profile = "strict"

[[overrides]]
files = ["x.*"]      # broader, but LATER, so this one wins for x.md
profile = "relaxed"
```

Two alternatives lost. Specificity ranking loses because no ordering on globs a
reader can predict exists: `docs/**` against `**/*.md` is differently specific,
not more or less, so any winner a rule picks there is a rule you memorise.
Strictest-wins loses because under it nothing relaxes, and a vendored subtree or a
generated `docs/api/` then has no way down, which is the main reason overrides
exist.

`slopvac` refuses two blocks with the *same* scope, since that reads as two
independent decisions and resolves as one. Overlap between different globs is
legitimate and stays legal.

`slopvac lint --explain-config <file>` prints what applies **and which block set
each setting**:

```
x.md
  profile: relaxed
  overrides: x.md, x.*
  set by:
    profile: overrides[1] (x.*)
    rules.prose-format.no-unicode-dash: overrides[0] (x.md)
```

The report lists only the settings some layer actually touched. The untouched
profile defaults would bury them.

## Word blocklist

Off by default. Nothing checks your words until you name a file:

```toml
[vocabulary]
path = "docs/blocklist.toml"     # relative to this config file
```

Each entry names a word, the part of speech to refuse it as, and why:

```toml
[[entries]]
word = "deploy"
pos = "noun"
replacement = "deployment"
reason = "The verb is fine. The noun form is a verb used as a noun."

[[entries]]
word = "simple"
pos = "adjective"
reason = "Judges the reader's experience rather than the work."
```

`examples/blocklist.toml` is a working starter. `.yml` and `.json` load too.

**The part of speech is the point.** `deploy` is a good verb and a bad noun, and
one entry per sense is what lets you say so: `slopvac` reports "the deploy failed"
and passes "deploy the worker". Vale's tagger decides which is which.

**`reason` is required.** `slopvac` refuses a file without one, because nobody but
the author can review or remove an undocumented refusal. `replacement` is optional:
omit it when the fix depends on the sentence, because a reader applies a suggestion
without thinking.

A word absent from the file is fine by definition. Nothing expresses "only these
words are allowed", and that gap is deliberate: this package once shipped an
ASD-STE100 word list enforced that way, and on ordinary software prose it produced
828 findings for words that merely had no entry, half of everything it reported.
That list is gone rather than switched off. A blocklist you wrote is the only word
list that knows your domain.

## Suppressing a finding

A suppression must name an exception from the rule's own list:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

`slopvac explain orwell.stale-figure` lists the valid reasons. When an annotation
names a reason off that list, `slopvac` reports it rather than honors it, and
tracks the suppression rate as a metric.

## Output formats

```sh
slopvac docs/                            # a terminal report
slopvac --format json docs/ | jq .        # every finding, every score
slopvac --format github docs/            # Action annotations on the diff
slopvac --format sarif docs/ > out.sarif  # code scanning
slopvac --open docs/                     # an HTML report, in your browser
```

`--open` writes a self-contained page and opens it. `--out report.html` names the
file instead of a temporary one, and implies HTML. The page needs no network and
no assets, so it survives being attached to a CI run or mailed to a reviewer.

The report leads with what did **not** run, before the score, and flags each
affected document in the table. A score from an engine that failed to start is an
upper bound, and a reader who misses that has been misled by their own report.

Below that: the verdict, then the documents worst first, then the categories that
fired, then the findings, grouped per document. Anything that failed starts open.

## The compiled-rule cache

`slopvac` compiles its YAML rules into a Vale style directory once and reuses it.
The cache key is a hash of the rules, the resolved config, the severities, and
your blocklist, so **nothing is ever served stale**: any edit mints a new key.

```sh
slopvac cache            # where it is, how many trees, how much disk
slopvac cache --prune    # keep the 16 most recently used
slopvac cache --all      # delete every tree
```

A lint prunes on its own, keeping the 16 trees used most recently. A cache hit
counts as use. A tree that a project keeps hitting therefore survives, however
old it is.
Pruning is only ever about disk: it cannot cause a wrong result. Set
`SLOPVAC_CACHE_DIR` to move it; it defaults under `XDG_CACHE_HOME`.

## Exit codes

| Code | Means |
| --- | --- |
| 0 | clean, or every threshold met |
| 1 | a threshold failed |
| 2 | the run could not be trusted: bad config, unloadable rules, missing tool |

The 1/2 split is what makes a clean result meaningful. Exit 2 means the run checked
nothing, which is not the same as passing.

## Scoring

Three numbers, because they answer different questions and none replaces another.

| Number | Counts | Answers |
| --- | --- | --- |
| `per_100_words` | every finding | how dense is this document |
| `gating_per_100_words` | errors and warnings | what the budget checks |
| `score` | 0-100 | what a badge shows and `min_score` gates |

Suggestions appear in the first number and not the second, because **a suggestion
may lower a score but must not fail a run**. That one rule is why there are three
numbers instead of one.

### Density: the n-per-100-words figure

A raw count cannot compare a 40-word error message against a 4,000-word guide.
One finding is 2.5 per 100 words in the first and 0.025 in the second. The
measurement is therefore always a density:

```
density = findings / words * 100
```

Below 60 words density means nothing, so the scorer switches to absolute counts.
Every finding counts there, suggestions included, and the count path is harsher on
purpose: one suggestion costs 5 points, one error costs 20, and four errors reach
0. A 40-word message has room for no defects.

### Per-category score

Every category gets its own density and its own 0-100 score against its own
budget. Weighted density drives it, so severity matters:

| Severity | Weight |
| --- | --- |
| `error` | 4.0 |
| `warning` | 2.0 |
| `suggestion` | 1.0 |
| `off` | 0.0 |

An error weighs 4 suggestions, so a document with one error is not out-voted by
cosmetic findings.

The curve has two halves and no sudden drop:

```
at or below budget:  100 down to 70, linearly
above budget:        70 down to 0, reaching 0 at 4x budget
```

A document exactly at budget scores 70, which makes "just inside" visibly
different from "clean". Above budget the score decays linearly rather than
instantly, so slightly over reads differently from far over.

The scorer subtracts suggestions afterwards, as a **bounded** penalty rather than
folding them into the density: at most 15 points, reaching that maximum at a
suggestion density of 6.0 per 100 words. Unbounded, they consumed the whole scale. Measured
on one document, suggestions were 76 of 152 findings and an advisory rule the
profile explicitly does not stand behind failed the run anyway.

A category with `weight = 0` is informational. It reports its findings and
contributes to neither side of the mean below.

### Document score

The document score is the **lower** of two figures:

1. the weight-weighted mean of the per-category scores
2. the same calculation run over the whole document's findings at once

Both directions matter. The mean alone is too kind: 23 categories that found
nothing score 100 each and drown the two that found errors, so a document with
five errors read as 92.7. While the rest are clean, the whole-document figure
alone loses the signal that one category sits far over its budget. Taking the
lower of the two keeps both.

### What fails a run

A run fails when any gate breaks: the error count exceeds `max_errors`, the
gating density exceeds `max_total_per_100_words`, the score falls below
`min_score`, or any single category exceeds its own `max_per_100_words`. The
report names each broken gate with the number that broke it.

## Rules

Rules are data. Each lives in a YAML file under `rules/<category>.yml`, so adding
a lexical, substitution, or threshold rule needs no code.

```sh
slopvac rules --profile strict
slopvac rules --judgement          # what a linter cannot check
slopvac explain ste-sentences.max-words
slopvac lint --rules-dir ./my-rules docs/
```

`slopvac` validates every rule at load: it compiles each regex, and requires each
example's `bad` text to match while its `good` text must not. A rule whose pattern
stopped firing passes every document, which is indistinguishable from clean prose.

Rules marked `kind: judgement` never produce a finding. They carry the checks no
pattern reaches, as decidable questions, so an agentic reviewer reads one source
of truth instead of a parallel prose catalog.

[`docs/rules.md`](docs/rules.md) is the full reference, generated from the same
ruleset the linter loads and split into checked and judgement rules. CI
regenerates it and fails on a diff, so it cannot drift from the code.

## Philosophy

Four positions, and each one rules something out. They are worth stating because
the obvious alternative is what most prose linters do.

### Density, not zero tolerance

Nearly every prose linter reports a count. A count makes a long document worse
than a short one for writing at the same quality, so the incentive it creates is
to write less rather than to write better, and any threshold set against a count
either passes a 3,000-word document with forty problems or fails a 200-word one
with three.

So the gate is **findings per 100 words**, and the score follows from that density
against the profile's budget. A long document earns proportionally more
findings. Under 60 words, scoring switches to absolute counts, because one finding
in a 20-word error message is 5.0 per 100 words and would fail every budget ever
set.

### Rules that fire deterministically, separated from rules that do not

A rule either has a checker or it does not, and the two make different promises.
Pretending otherwise produces the two failures this tool exists to prevent: a
reader who believes a judgement rule gates their build, and an agent that treats a
mechanical rule as a matter of opinion.

So the same ruleset carries `kind: judgement` rules, and they **never produce a
finding**. They ship for two reasons. A reviewing agent needs one source of truth
rather than a second, drifting prose catalog. And a rule no tool can automate is not
thereby less true. Deleting it would quietly redefine the standard as
"whatever a regex can reach", which is how a style guide becomes a list of
typography preferences.

### Silence is a finding

The failure a linter is worst at reporting is its own. A rule that stopped
matching, an absent Vale binary, a metric with no implementation: each produces a
document with no findings, which is indistinguishable from clean prose.

So:

- **Exit 2 is not exit 0.** A bad config, an unloadable ruleset, or a missing tool
  exits 2, and every caller treats that as "nothing was checked" rather than as a
  pass.
- **Skipped rules are reported as `UNCHECKED`**, per run. Without the Vale binary
  the built-in rules still score and the rest are named as not run.
- **Every rule is validated at load.** Each regex compiles, and each example's
  `bad` text must match while its `good` text must not, so a rule that stopped
  firing fails the build instead of passing every document.
- **A misspelled rule id is an error**, not a silent no-op: the failure it
  otherwise produces is "I disabled it and the gate still fails".
- **A configured blocklist that cannot be loaded is an error.** The project asked
  for that gate by name; linting on with an empty wordlist would report every
  document clean.

### A finding must be actionable, and a refusal must be reviewable

A finding a reader cannot act on trains them to disable the rule. So each one
carries the replacement or the operation, `slopvac explain <rule>` gives the
reason behind the rule's wording, and every rule cites a source.

The same standard applies to the word blocklist, and it is why **no word list
ships**. An earlier version treated ASD-STE100's 859 approved words as the
permitted set. Measured on an 8-document corpus:

- that one rule produced 51% of all findings
- it drove every document to a score of 0.0, including documents with zero errors
- 1,275 of its 1,282 refusals carried neither a reason nor a replacement

Absence from a deliberately incomplete dictionary is not disapproval. It is a
**blocklist** now, empty until you write one, and every entry requires a reason.
Nobody but its author can argue with, or later remove, an entry that gives no
reason.

Suppression follows from the same position: `<!-- slopvac-disable-next-line rule:
reason -->` requires a reason from the rule's own closed list. `slopvac` reports
any other reason rather than honors it, so a blanket suppression shows up in a
diff.

### What this deliberately does not do

A clean run means the checked patterns are absent, and nothing more. It is not a
review. The linter does not read for truth: a sentence can pass every rule and
name a function that does not exist, describe a flag that never shipped, or
contradict the paragraph above it.

The lexical rules also perish. A memorized word list tracks one model generation,
which is why the structural and register categories carry more weight than the
token ones.

## Word counting

Sentence-length limits use ASD-STE100's own definition of a word (rules 8.4
through 8.7), not a whitespace split:

- a number counts as one word, with its unit if it has one
- an abbreviation counts as one word
- a quoted span counts as one word
- parenthesized text counts as one word
- a hyphenated word counts as one word
- numbers identifying a step or paragraph are not counted

`Do steps 13 thru 16 a minimum of three times.` is 10 words.

## Limits

A clean run means the checked patterns are absent, and nothing more. The linter
does not read for truth. A sentence can pass every rule and name a function that
does not exist, describe a flag that never shipped, or contradict the paragraph
above it.

No word list ships, and the word check stays inert until you write one. See
[Word blocklist](#word-blocklist).

## Sources

The Simplified Technical English rules are an independent restatement, cited by
rule number. ASD-STE100 is copyright
[ASD](https://www.asd-ste100.org) and is an EU registered trademark; this package
reproduces none of its rule text, definitions, or examples.

This package ships and reads no dictionary content. An earlier version carried the
Issue 9 word list. That version is gone, and the word check now reads a blocklist
you write.

The AI-slop rules take their calibration from a corpus of software documentation. The
lexical ones perish: a memorized word list tracks one model generation, which is
why the structural and register rules carry more weight.

## License

Apache-2.0.
