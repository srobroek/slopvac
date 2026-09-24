# slopvac

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/slopvac-dark-1200-q85.webp">
    <source media="(prefers-color-scheme: light)" srcset="assets/slopvac-light-1200-q85.webp">
    <img alt="Slopvac robot vacuum cleaning prose" src="assets/slopvac-light-1200-q85.webp" width="480">
  </picture>
</p>

[![Tests](https://github.com/srobroek/slopvac/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/test.yml)
[![Code and prose checks](https://github.com/srobroek/slopvac/actions/workflows/lint.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/lint.yml)
[![Security](https://github.com/srobroek/slopvac/actions/workflows/security.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/security.yml)
[![PyPI version](https://img.shields.io/pypi/v/slopvac)](https://pypi.org/project/slopvac/)

---

[Quick start](#quick-start) · [CLI reference](packages/slopvac-lint/README.md) ·
[Rules](packages/slopvac-lint/docs/rules.md) ·
[Configuration](packages/slopvac-lint/README.md#configuration) ·
[Agent setup](#agent-skills) · [CI](#ci-integration) ·
[Evaluation](packages/slopvac-lint/docs/judgement-eval.md)

`slopvac` lints prose and source comments. Its rules cover AI writing patterns
and general prose quality, including documentation discipline and
technical-writing constraints.

Use the CLI locally or in CI. The `write-docs` and `review-docs` agent skills
add review of claims and structure, with optional model-based checks.

## Quick start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and use
Python 3.11 or later. [Vale](https://vale.sh) is optional, but **highly
recommended**: it executes most deterministic rules. Install Vale 3.15 or later
and put it on `PATH` for full deterministic coverage.

With Homebrew, install Vale and check the installed version:

```sh
brew install vale
vale --version
```

Other platforms can use the installers linked from the [Vale site](https://vale.sh).

From your project's root directory:

```sh
uv tool install slopvac
slopvac init
slopvac README.md
```

`init` creates `slopvac.toml` with the `normal` profile and leaves an existing
file unchanged. Replace `README.md` with the file or directory you need to check.
A passing run exits 0; findings above a threshold exit 1. An incomplete check
exits 2, including when selected Vale-backed checks cannot run.

For a one-off check without installing slopvac persistently:

```sh
uvx slopvac README.md
```

### Use the results

```sh
slopvac --format json --out slopvac-report.json README.md
slopvac --open README.md
slopvac --fix README.md
```

`--fix` edits source files using deterministic replacements. Review the diff
before keeping those edits. The **[CLI reference](packages/slopvac-lint/README.md)**
covers [linting and fixes](packages/slopvac-lint/README.md#lint-documents),
[profiles](packages/slopvac-lint/README.md#profiles),
[scoring](packages/slopvac-lint/README.md#scoring), and
[contextual review](packages/slopvac-lint/README.md#judgement-layer).

## What it checks

The packaged YAML contains 231 rules across 26 categories: 166 checked rules and
65 contextual rules marked `kind: judgement`.

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
slopvac rules --judgement
```

### Deterministic checks

The native engine and Vale report findings with source locations. The report
includes density per 100 words and a 0-100 score. Profiles and project settings
control which findings fail a run.

Missing Vale, or `--no-vale`, leaves selected Vale-backed checks unchecked.
Native findings remain available, but the run returns exit 2.

### The judgement layer

Contextual rules ask a model about passages that need interpretation, such as
repeated explanations or claims without enough support. The CLI prepares the
prompts and validates the responses. Your agent harness or provider client makes
the model calls.

```sh
slopvac judgement brief README.md --out .slopvac-review --packs fired
```

This writes a review brief and structured prompts without contacting a provider.
`--packs fired` selects categories with deterministic findings. If none qualify,
`brief` keeps all packs and prints a warning. When some categories qualify,
others receive no contextual review. Use `--packs all` for broader review.

Review the printed call count before sending prompts to a provider. `brief`
does not enforce the call-budget refusal available through `judgement prepare`.

Model results are advisory. They can lower `judgement_adjusted_score` but do not
change the deterministic result. See the
[complete workflow](packages/slopvac-lint/README.md#judgement-layer) for response
validation, coverage, and rewrite previews.

## Agent skills

`write-docs` applies the document's genre rules and hands the text to
`review-docs`. The review checks the prose against the code and removes material
that the intended reader does not need. Contextual model review runs on request.

### Oh My Pi

```sh
omp plugin marketplace add srobroek/slopvac
omp plugin install slopvac@slopvac --scope user
```

Use `--scope project` for a project installation. Start a new session after
installing. To use a local checkout:

```sh
omp plugin link ./slopvac/packages/slopvac
```

### Claude Code

Run these commands in Claude Code:

```text
/plugin marketplace add srobroek/slopvac
/plugin install slopvac@slopvac
```

### Codex

```sh
codex plugin marketplace add srobroek/slopvac
codex plugin add slopvac@slopvac
```

### Kiro and manual installation

Copy the skills into the harness's skills directory. For Kiro:

```sh
git clone https://github.com/srobroek/slopvac /tmp/slopvac
mkdir -p .kiro/skills
cp -R /tmp/slopvac/packages/slopvac/skills/* .kiro/skills/
```

The corresponding project directories are `.claude/skills` for Claude Code and
`.codex/skills` for Codex.

After installing, ask the agent to write or review a document. To include
contextual checks, ask it to review the document for AI tells as well.

## CI integration

### pre-commit

```yaml
repos:
  - repo: https://github.com/srobroek/slopvac
    rev: v2.10.0
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
- uses: srobroek/slopvac@v2.10.0
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
[suppressions](packages/slopvac-lint/README.md#suppress-a-finding) for a local
exception and [comment mode](packages/slopvac-lint/README.md#comment-mode) for
source files.

## Limits and evaluation

A passing run means the selected checks stayed within configured thresholds.
It does not establish factual correctness or identify who wrote the text.
AI-signal labels describe rule evidence, without changing the gate.

Model review can miss defects or flag correct prose. The
[evaluation guide](packages/slopvac-lint/docs/judgement-eval.md) documents
validation and measurement methods. The
[evaluation record](packages/slopvac-lint/docs/research/rubric-2026-09-15/evaluation/2026-09-19-wider-evaluation.md)
reports the tested corpus and denominators for its results.

## License

Apache-2.0. Includes rules derived from
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT).
See [sources](packages/slopvac-lint/README.md#sources) for rule provenance.
