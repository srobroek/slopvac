# slopvac

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/slopvac-dark-1200-q85.webp">
    <source media="(prefers-color-scheme: light)" srcset="assets/slopvac-light-1200-q85.webp">
    <img alt="Slopvac robot vacuum cleaning prose" src="assets/slopvac-light-1200-q85.webp" width="480">
  </picture>
</p>

[![CI](https://github.com/srobroek/slopvac/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/test.yml)
[![Security](https://github.com/srobroek/slopvac/actions/workflows/security.yml/badge.svg?branch=main&event=schedule)](https://github.com/srobroek/slopvac/actions/workflows/security.yml)
[![PyPI version](https://img.shields.io/pypi/v/slopvac)](https://pypi.org/project/slopvac/)

---

[Quick start](#quick-start) · [CLI reference](packages/slopvac-lint/README.md) ·
[Rules](packages/slopvac-lint/docs/rules.md) ·
[Metrics](packages/slopvac-lint/docs/metrics.md) ·
[Triage](packages/slopvac-lint/docs/triage.md) ·
[Suppressions](packages/slopvac-lint/docs/suppressions.md) ·
[Configuration](packages/slopvac-lint/README.md#configuration) ·
[Agent setup](#agent-setup) · [Writing guidance](#writing-guidance) ·
[Semantic review](#semantic-review) · [CI](#ci-integration) · [Roadmap](#roadmap)

`slopvac` lints prose and source comments. Its rules cover AI writing patterns
and general prose quality, including documentation discipline and
technical-writing constraints. Use it on AI-generated documentation, PR
descriptions, Markdown, and comments in supported source files such as TSX and
JSX. Comment mode checks comments, not code or strings.

Coding agents can run the CLI, inspect findings, and apply fixes. The same checks
can run in pre-commit or CI for automated validation.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use
Python 3.11 or later. **[Vale](https://vale.sh) 3.18 or later is required
for a complete lint run.** Vale executes most deterministic rules and must be
available on `PATH`. SlopVac checks the Vale version before compiling rules.
Without Vale, lint exits 2 (incomplete) instead of 0 (pass).

With Homebrew, install Vale and check the installed version:

```sh
brew install vale
vale --version
```

Other platforms can use the [Vale installation instructions](https://vale.sh).
Contributors can run `mise install` to install the pinned Python, uv, and Vale
tools from `mise.toml`. **End users do not need mise.** After installation,
run `slopvac doctor` to check the Vale prerequisite.

Install slopvac for persistent use with uv:

```sh
uv tool install slopvac
slopvac init
slopvac README.md
```

Upgrade the installation with `uv tool upgrade slopvac`. To run slopvac without
a persistent install, use `uvx slopvac README.md`. uvx reuses its cached
environment. Use `uvx slopvac@latest README.md` to force the latest release.

`init` creates `slopvac.toml` with the `normal` profile when absent and keeps an
existing config unless you pass `--force`. Replace `README.md` with the file or
directory to check. A passing run exits 0. Findings above a threshold exit 1.
An incomplete check exits 2.

### Update notice

If the cache contains a newer stable PyPI release, Slopvac prints an update notice after an eligible command.
Slopvac refreshes that cache in the background. A newly discovered release can appear on a later run.
Slopvac skips the check in these cases:

- The command is `prime`.
- The output format is non-text.
- The report goes to a file or opens in a browser.
- The environment contains `CI`.
- Standard error is not a terminal.

To disable the check, set `NO_UPDATE_NOTIFIER=1`, `SLOPVAC_NO_UPDATE_CHECK=1`, or `DO_NOT_TRACK=1`.

### Use the results

```sh
slopvac --format json --out slopvac-report.json README.md
slopvac --open README.md
slopvac --fix README.md
```

`--fix` edits source files using deterministic replacements. Review the diff
before keeping those edits. The **[CLI reference](packages/slopvac-lint/README.md)**
covers [linting and fixes](packages/slopvac-lint/README.md#lint-documents),
[profiles](packages/slopvac-lint/README.md#profiles), and
[scoring](packages/slopvac-lint/README.md#scoring).

## What it checks

The linter ships 166 checked rules across 26 categories. The catalog also
carries 67 judgment rules that lint never reports. The
[writing guidance](#writing-guidance) and [semantic review](#semantic-review)
apply them.

| Coverage | Examples |
| --- | --- |
| AI writing patterns | Repeated structures, inflated register, formatting tells, and generated residue |
| General prose | Agency, word choice, scope, consistency, and promotional language |
| Documentation discipline | Internal references, status language, and project history in user documentation |
| Simplified Technical English | Sentence length, noun groups, procedural writing, and safety text |
| Orwell-derived checks | Stale figures of speech, excess words, and unclear agency |

The [rule reference](packages/slopvac-lint/docs/rules.md) lists individual rules
and examples. Inspect them from the CLI:

```sh
slopvac rules
slopvac explain prose-craft.relative-date
```

### Deterministic checks

The native engine and Vale report findings with source locations. The report
includes density per 100 words and a 0-100 score. Profiles and project settings
control which findings fail a run.

Missing or unsupported Vale, or `--no-vale`, leaves selected Vale-backed checks unchecked.
Native findings remain available, but the run returns exit 2.

## Agent setup

Slopvac installs small project-local files instead of harness marketplaces.
The managed steering block tells the agent to run `slopvac prime`, and a
`slopvac-prose` skill tells harnesses that load project skills to run
`slopvac prime write` and `slopvac prime review` around prose work. Neither
copies rule policy; the installed CLI prints it.

Two commands write these files:

- `slopvac init` creates `slopvac.toml` when absent and keeps an existing file
  unless `--force` is set. Repeat `--harness <name>` for several harnesses.
  Without `--harness`, it writes generic `AGENTS.md` steering; naming a harness
  replaces that default, so add `--harness agents` to keep it. `--no-skills`
  writes steering without skills. `--skip-agents` writes only the config and
  cannot be combined with `--harness` or `--no-skills`.
- `slopvac setup <harness>` writes, checks, or removes one harness's steering
  and its skill when available. It writes only those files: it reads
  `[guidance]` from `slopvac.toml`, or uses the defaults when no config exists.
  Run it with or without `init`.

`slopvac setup --list` prints each harness with its steering and skill paths.
The [CLI reference](packages/slopvac-lint/README.md#agent-steering) lists the
per-harness paths, `setup --check` exit codes, and `--remove` behavior.

```sh
slopvac init --harness claude --harness omp   # config plus Claude Code and Oh My Pi
slopvac setup codex                           # one harness; reads config, never writes it
```

Agents get detailed guidance on demand:

```sh
slopvac prime
```

`prime` covers linting, exit-code semantics, Vale coverage, rule explanation,
named exceptions, factual-claim verification, and when to run the writing and
review topics. It only prints. `slopvac onboard` prints a short setup handoff
that points the agent to `prime` for the detailed workflow.

## Writing guidance

`slopvac prime write` prints a writing guide for READMEs, docs, PR or MR
descriptions, commit and release text, and specifications. The guide holds a
genre table, a documentation contract, and the `slopvac rules` command that
prints the judgement rules for the document's genre. `slopvac prime` tells the
agent to run it before drafting or editing that prose.

Disable it with `[guidance] write = "off"` in `slopvac.toml`. The
[semantic guidance reference](packages/slopvac-lint/docs/semantic-guidance.md)
lists every mode.

## Semantic review

`slopvac prime review` prints a review workflow. The agent runs `slopvac lint`
first, answers the judgement checklist for the document's genre, and checks
factual claims against the code. The default reviewer pass uses one
fresh-context subagent. The author gives it the draft, original if revised,
source or brief if available, and review output. It runs lint, the checklist,
and fact check, then reports findings once with rule id, quoted text, proposed
rewrite, lost facts, and claims stronger than the source. The author fixes or
rebuts each finding. No loop follows unless requested.

Set `[guidance] review_depth = "self"` when the author should run the pass, or
`"adversary"` to run repeated reviewer rounds. Each round gets the findings the
author rebutted earlier, and the loop stops when a round reports no finding the
author accepts. If no subagent is available, the author runs the pass and
records `self (no subagent available)`. `review = "ask"` asks before the review;
`review = "off"` disables it. Slopvac only prints the workflow and the
checklist. The agent's own model runs the review.

## CI integration

### pre-commit

```yaml
repos:
  - repo: https://github.com/srobroek/slopvac
    rev: v2.17.0 # x-release-please-version
    hooks:
      - id: slopvac
```

Use the `slopvac-strict` hook for the strict profile. Install Vale on the machine
running pre-commit. The `slopvac-no-vale` hook leaves selected Vale-backed checks
unchecked and returns exit 2.

### GitHub Actions

Add these steps to a workflow job:

```yaml
- uses: actions/checkout@v7
- uses: srobroek/slopvac@v2.17.0 # x-release-please-version
  with:
    paths: README.md docs/
    profile: normal
```

The action supports annotations and SARIF output, plus configuration and
changed-file selection. See [action.yml](action.yml) for its inputs and outputs.

## Configure a project

```sh
slopvac lint --explain-config README.md
```

The default profile is `normal`. Use `strict` for reference material or
`relaxed` for informal text. Configure thresholds and rule severities in
`slopvac.toml`, with `[[overrides]]` for path-specific settings.

The [configuration reference](packages/slopvac-lint/README.md#configuration)
includes precedence and examples. See
[suppressions and exclusions](packages/slopvac-lint/docs/suppressions.md) for a
local exception or an excluded file, and
[comment mode](packages/slopvac-lint/README.md#comment-mode) for source files.

## Limits and evaluation

A passing run means the selected checks stayed within configured thresholds.
It does not establish factual correctness or make an overall judgement about
writing quality beyond the configured rules. AI-signal labels describe rule
evidence without changing the gate.

Before merging a release PR, maintainers can run the report-only local
[performance comparison](packages/slopvac-lint/docs/performance.md#pre-release-regression-comparison)
on an idle host. It reports regressions and exits 0; set `PERF_FAIL=1` to fail
on them.

## Roadmap

## Agentic judgement

Lint is deterministic, and the [semantic review](#semantic-review) is a
checklist that an agent applies. A separate development track is
evaluating an optional semantic decision layer built around **typed judge
models** rather than free-form text generation. Candidate backends include
hosted [Jev](https://www.typesafeai.org/jev) and local/open models such as
[Laya](https://github.com/NandhaKishorM/laya),
[Nimble](https://github.com/bespokelabsai/nimble), and
[Kev](https://github.com/jaredpalmer/kev), plus the
[SemIf](https://github.com/theoleecj/semif) direct-logit scoring approach.
The design is tracked in
[issue #162](https://github.com/srobroek/slopvac/issues/162).

The planned layer fits **after** Slopvac has parsed the document and generated
candidate spans. It has two uses:

1. **Semantic detection.** For AI/style defects that cannot be expressed
   reliably as syntax, structure, or fixed patterns, a typed judge evaluates
   bounded questions such as applicability, semantic fit, evidence sufficiency,
   and repair category. Slopvac code, not the model, derives the final
   confirm/reject/uncertain policy.
2. **Rule validation.** For an ordinary linter rule that already fired, the same
   decision provider receives the rule id, exact source span, and local context
   and asks whether the trigger actually matches the defect the rule intends to
   detect. This is intended to measure false positives, validate rule changes
   against gold/control corpora, and identify rules whose deterministic trigger
   should be improved.

An optional local reranker may sit before the typed judge when candidate volume
is high. The first candidate is
[Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).
It can prioritize likely candidates to reduce judge cost, but the typed judge
and deterministic host policy remain authoritative.

The intended shape is:

```text
source
  -> deterministic parsing and candidate generation
  -> optional recall-first local reranker
  -> typed decision provider
  -> deterministic host policy
  -> semantic detection / rule-validation report
```

Exact source locations remain host-authoritative. This semantic layer is being
developed separately and is not part of the current linter CLI or exit status.

## License

Apache-2.0. Includes rules derived from
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT).
See [sources](packages/slopvac-lint/README.md#sources) for rule provenance.
