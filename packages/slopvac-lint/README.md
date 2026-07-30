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
| Vale | 133 | token, regex, and substitution matching; sentence and paragraph word counts; part-of-speech checks against your word blocklist; whole-document ratios |
| built-in | 15 | patterns Go's regex engine rejects, metrics with no Vale form, and block-shape comparisons |
| neither | 67 | rules stating a question a reviewer answers; `slopvac rules --judgement` lists them |

Without the binary the run still scores the 15 built-in rules and reports the rest
as `UNCHECKED`, so a partial check never reads as a pass. `--no-vale` reports the
same way.

Inspect the routing, or run Vale by hand against the generated config:

```sh
slopvac compile --outdir build/vale
vale --config=build/vale/.vale.ini docs/
```

## Profiles

| Profile | For | Sentence cap | Approved-word check |
| --- | --- | --- | --- |
| `strict` | reference, specs, API docs, runbooks | 20 procedural / 25 descriptive | on |
| `normal` | README, guides, ADRs | 25 advisory | off |
| `relaxed` | notes, comments, drafts | advisory | off |

`normal` is the default. Two rules invert the tier ordering on purpose: passive
voice is advisory at `strict` and enforced at `normal`, because the agentless
passive is correct in a specification and wrong in a guide.

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

A misspelled rule id or category name is an **error**, not a silent no-op —
including inside an `[[overrides]]` block. `slopvac` refuses to lint and offers
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

Specificity ranking was rejected because there is no ordering on globs a reader
can predict — `docs/**` against `**/*.md` is differently specific, not more or
less — and any rule that picks a winner there has to be memorised. Strictest-wins
was rejected because under it nothing can be **relaxed**: a vendored subtree or a
generated `docs/api/` could never be dialled down, which is the main reason
overrides exist.

Two blocks with the *same* scope are refused, since that reads as two independent
decisions and resolves as one. Overlap between different globs is legitimate and
stays legal.

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

Only settings some layer actually touched are listed; the untouched profile
defaults would bury them.

## Word blocklist

Off by default. Nothing checks your words until you name a file:

```toml
[vocabulary]
path = "docs/blocklist.toml"     # relative to this config file
```

Each entry names a word, the part of speech it is refused as, and why:

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
one entry per sense is what lets you say so: "the deploy failed" is flagged and
"deploy the worker" is not. Vale's tagger decides which is which.

**`reason` is required.** The file is refused without one, on the grounds that an
undocumented refusal cannot be reviewed or removed by anyone but its author.
`replacement` is optional — omit it when the fix depends on the sentence, because
a reader applies a suggestion without thinking.

A word absent from the file is fine by definition. There is no way to express "only
these words are allowed", and that is deliberate: this package shipped an
ASD-STE100 word list enforced that way, and on ordinary software prose it produced
828 findings for words that merely had no entry — half of everything it reported.
The list is deleted rather than disabled. A blocklist you wrote is the only word
list that knows your domain.

## Suppressing a finding

A suppression must name an exception from the rule's own list:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

`slopvac explain orwell.stale-figure` lists the valid reasons. An annotation
naming a reason that is not on the list is reported rather than honoured, and the
suppression rate is tracked as a metric.

## Exit codes

| Code | Means |
| --- | --- |
| 0 | clean, or every threshold met |
| 1 | a threshold failed |
| 2 | the run could not be trusted: bad config, unloadable rules, missing tool |

The 1/2 split is load-bearing. Exit 2 means nothing was checked, which is not the
same as passing.

## Scoring

Two numbers, because they answer different questions.

`per_100_words` is the raw density, comparable across documents of any length.
`score` is 0-100, derived from density against the profile's budget, and is what
a badge or a `min_score` gate reads.

Documents under 60 words are scored on absolute counts rather than density: one
finding in a 20-word error message is 5.0 per 100 words and would fail every
budget.

An error weighs 4 suggestions, so a document with one error is not out-voted by
cosmetic findings.

## Rules

Rules are data. Each lives in a YAML file under `rules/<category>.yml`, so adding
a lexical, substitution, or threshold rule needs no code.

```sh
slopvac rules --profile strict
slopvac rules --judgement          # what a linter cannot check
slopvac explain ste-sentences.max-words
slopvac lint --rules-dir ./my-rules docs/
```

Every rule is validated at load: each regex is compiled, and each example's `bad`
text must match while its `good` text must not. A rule whose pattern stopped
firing passes every document, which is indistinguishable from clean prose.

Rules marked `kind: judgement` never produce a finding. They carry the checks no
pattern reaches, as decidable questions, so an agentic reviewer reads one source
of truth instead of a parallel prose catalog.

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

No word list ships, and the word check does nothing until you write one. See
[Word blocklist](#word-blocklist).

## Sources

The Simplified Technical English rules are an independent restatement, cited by
rule number. ASD-STE100 is copyright
[ASD](https://www.asd-ste100.org) and is an EU registered trademark; this package
reproduces none of its rule text, definitions, or examples.

No dictionary content is shipped or read. An earlier version carried the Issue 9
word list; it is removed, and the word check now reads a blocklist you write.

The AI-slop rules are calibrated against a corpus of software documentation. The
lexical ones perish: a memorized word list tracks one model generation, which is
why the structural and register rules carry more weight.

## License

Apache-2.0.
