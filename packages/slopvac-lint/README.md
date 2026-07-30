# slopvac-lint

Score prose against three rulesets: AI-slop patterns, Simplified Technical
English, and Orwell's rules restated as objective tests.

Reports a finding density per 100 words and a 0-100 score, per category and
overall, with warn and error levels you set per category.

```sh
uvx slopvac-lint README.md
uvx slopvac-lint --profile strict docs/
uvx slopvac-lint --format json docs/ | jq .summary
```

## Install

```sh
uv tool install slopvac-lint     # persistent, no per-call resolution
uvx slopvac-lint --help          # or run it without installing
pipx install slopvac-lint
```

[Vale](https://vale.sh) is optional and extends the run with the upstream
[tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells) package. Without it
those rules report as `UNCHECKED` rather than passing silently.

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

`slopvac-lint init` writes a `slopvac.toml`. Three layers patch each other per
field:

1. the profile
2. the `[categories]` and `[rules]` tables
3. every `[[overrides]]` block whose glob matches, in file order

```toml
profile = "normal"

[thresholds]
max_errors = 0
min_score = 70

[categories.ste-vocabulary]
enabled = false

[rules."prose-format.no-unicode-dash"]
severity = "off"           # house style uses real em dashes

[[overrides]]
files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
profile = "strict"
```

A setting belongs to the block it is written in, so appending to the end of the
file cannot silently re-target it. `slopvac-lint lint --explain-config <file>`
prints what actually applies.

A category cap lowers a rule's severity and never raises it: `severity = "error"`
on a category will not promote a suggestion into a gate failure.

## Suppressing a finding

A suppression must name an exception from the rule's own list:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

`slopvac-lint explain orwell.stale-figure` lists the valid reasons. An annotation
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
slopvac-lint rules --profile strict
slopvac-lint rules --judgement          # what a linter cannot check
slopvac-lint explain ste-sentences.max-words
slopvac-lint lint --rules-dir ./my-rules docs/
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

The part-of-speech tagger is shallow by design and reports nothing when the
surrounding tokens leave a word ambiguous, so the approved-word check misses
cases rather than firing on correct prose.

## Sources

The Simplified Technical English rules are an independent restatement, cited by
rule number. ASD-STE100 is copyright
[ASD](https://www.asd-ste100.org) and is an EU registered trademark; this package
reproduces none of its rule text, definitions, or examples.

The approved-word data is the Issue 9 dictionary's word, part-of-speech, and
status triples. Deviations for software documentation are held separately in
`vocabulary-overlay.yml` so every one of them is visible.

The AI-slop rules are calibrated against a corpus of software documentation. The
lexical ones perish: a memorized word list tracks one model generation, which is
why the structural and register rules carry more weight.

## License

Apache-2.0.
