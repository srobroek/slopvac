# slopvac

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/slopvac-dark-1200-q85.webp">
    <source media="(prefers-color-scheme: light)" srcset="assets/slopvac-light-1200-q85.webp">
    <img alt="Slopvac robot vacuum cleaning prose" src="assets/slopvac-light-1200-q85.webp" width="480">
  </picture>
</p>

[![Tests](https://github.com/srobroek/slopvac/actions/workflows/test.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/test.yml)
[![Lint](https://github.com/srobroek/slopvac/actions/workflows/lint.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/lint.yml)
[![Markdown audit](https://github.com/srobroek/slopvac/actions/workflows/markdown-audit.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/markdown-audit.yml)
[![Security](https://github.com/srobroek/slopvac/actions/workflows/security.yml/badge.svg?branch=main&event=push)](https://github.com/srobroek/slopvac/actions/workflows/security.yml)
[![PyPI version](https://img.shields.io/pypi/v/slopvac)](https://pypi.org/project/slopvac/)

---

[Quick start](#quick-start) · [CLI reference](packages/slopvac-lint/README.md) ·
[Rules](packages/slopvac-lint/docs/rules.md) ·
[Metrics](packages/slopvac-lint/docs/metrics.md) ·
[Triage](packages/slopvac-lint/docs/triage.md) ·
[Configuration](packages/slopvac-lint/README.md#configuration) ·
[Agent setup](#agent-setup) · [CI](#ci-integration) · [Roadmap](#roadmap)

`slopvac` lints prose and source comments. Its rules cover AI writing patterns
and general prose quality, including documentation discipline and
technical-writing constraints. Use it on AI-generated documentation, PR descriptions,
source comments, static TSX/JSX text, and other prose.

Coding agents can run the CLI, inspect findings, and apply fixes. The same checks
can run in pre-commit or CI for automated validation.

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

Other platforms can use the [Vale installation instructions](https://vale.sh).

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
[profiles](packages/slopvac-lint/README.md#profiles), and
[scoring](packages/slopvac-lint/README.md#scoring).

## What it checks

The linter ships 166 checked rules across 26 categories.

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

Missing Vale, or `--no-vale`, leaves selected Vale-backed checks unchecked.
Native findings remain available, but the run returns exit 2.

## Agent setup

Slopvac uses project-local steering instead of harness marketplaces or copied
skills. The managed block tells the agent to ask the installed CLI for the
current lint workflow instead of duplicating rule policy.

`slopvac init` adds the generic `AGENTS.md` block by default. Use
`--skip-agents` when only configuration should be created.

For harness-specific setup:

| Harness | Command | Managed file |
| --- | --- | --- |
| Generic AGENTS.md consumers | `slopvac setup agents` | `AGENTS.md` |
| Codex | `slopvac setup codex` | non-empty `AGENTS.override.md`, otherwise `AGENTS.md` |
| Claude Code | `slopvac setup claude` | `CLAUDE.md` |
| Oh My Pi | `slopvac setup omp` | `.omp/AGENTS.md` |
| Kiro | `slopvac setup kiro` | `.kiro/steering/slopvac.md` (`inclusion: always` for a new file) |

`setup` preserves content outside Slopvac's managed markers. Use
`slopvac setup <harness> --check` to report `current`, `missing`, `stale`,
or `malformed` without changing the file. Remove only the managed block with
`slopvac setup <harness> --remove`. Run `slopvac setup --list` to inspect
supported targets.

Agents get detailed guidance on demand:

```sh
slopvac prime
```

`prime` covers linting, exit-code semantics, Vale coverage, rule explanation,
named exceptions, and factual-claim verification. `slopvac onboard` prints a short setup handoff that points the agent to
`prime` for the detailed workflow.

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
It does not establish factual correctness or make an overall judgement about
writing quality beyond the configured rules. AI-signal labels describe rule
evidence without changing the gate.

## Roadmap

## Agentic judgement

The current release is a deterministic linter. A separate development track is
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
