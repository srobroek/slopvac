# slopvac

[![Tests](https://github.com/srobroek/slopvac/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/test.yml)
[![Code and prose checks](https://github.com/srobroek/slopvac/actions/workflows/lint.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/lint.yml)
[![Security](https://github.com/srobroek/slopvac/actions/workflows/security.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/security.yml)
[![PyPI version](https://img.shields.io/pypi/v/slopvac)](https://pypi.org/project/slopvac/)

---

[Quick start](#quick-start) · [CLI reference](packages/slopvac-lint/README.md) ·
[Rules](packages/slopvac-lint/docs/rules.md) ·
[Configuration](packages/slopvac-lint/README.md#configuration) ·
[Agent setup](#agent-setup) · [CI](#ci-integration) ·
[Evaluation](packages/slopvac-lint/docs/judgement-eval.md)

`slopvac` lints prose and source comments. Its rules cover AI writing patterns
and general prose quality, including documentation discipline and
technical-writing constraints.

Use the CLI locally or in CI. `slopvac init` adds project instructions for
your agent, with detailed lint and contextual-review guidance available on demand.

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

## Agent setup

Choose the harness that reads your project:

| Harness | Command |
| --- | --- |
| Claude Code | `slopvac init --harness claude` |
| Codex | `slopvac init --harness codex` |
| Oh My Pi | `slopvac init --harness omp` |
| Kiro | `slopvac init --harness kiro` |
| Other `AGENTS.md` clients | `slopvac init` |

Setup preserves existing configuration and unrelated instructions. Use
`--skip-agents` for configuration alone, or `slopvac setup HARNESS` to refresh
steering without changing configuration. After setup, start a new agent session.

The agent reads the short steering section and obtains details through the CLI:

```sh
slopvac prime
slopvac prime lint
slopvac prime judgement
slopvac explain prose-craft.relative-date
```

No skill or marketplace installation is required. The
[agent setup guide](packages/slopvac-lint/docs/agents.md) covers file destinations,
checks, removal, and custom harness settings. `slopvac onboard` prints the steering
for another client without writing files.

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
