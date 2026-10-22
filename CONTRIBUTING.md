# Contributing

## Development setup

Install the pinned development tools and project dependencies from the repository root:

```sh
mise install
uv sync --extra dev
```

`mise.toml` pins Python, uv, Vale, and other development tools. The project supports Python 3.11 or later. Vale 3.18 or later enables complete linting. Run `mise install` to install pinned tools.

Run the test suite from the repository root:

```sh
uv run pytest
```

The root `pyproject.toml` configures pytest to discover `packages/slopvac-lint/tests` and `tests`. CI runs the full suite with `python -m pytest` from the repository root. For documentation changes, CI runs the Slopvac prose gate and Markdown checks.

## Prose checks

Run Slopvac's repository prose gate on the files you changed:

```sh
uvx --from ./packages/slopvac-lint slopvac <files>
```

Exit 2 means the check is incomplete, not clean. If the command exits 2, install Vale 3.18 or later and rerun it. Fix findings before you open a pull request.

## Rules

Rule definitions live in [`packages/slopvac-lint/src/slopvac/rules/`](packages/slopvac-lint/src/slopvac/rules/). Each YAML file defines a category and its rules. Add examples of text the rule should flag and text it should leave alone.

Run the ruleset tests after changing examples:

```sh
uv run pytest packages/slopvac-lint/tests/test_ruleset.py
```

These tests check that each lexical rule's `bad` example matches its pattern. A `good` example must not match. The tests check that each lexical rule has an example. For substitutions, the tests check that each example resolves to a replacement.

## Commits and pull requests

Use [Conventional Commits](https://www.conventionalcommits.org/). Release-please reads the commit message to prepare releases. Examples: `feat(rules): add a rule`, `fix: correct a rule`, and `docs: clarify setup`.

Open a pull request with a concise description and a list of checks you ran. CI must pass before merge. Maintainers squash-merge pull requests.

## Report a problem or propose a rule

Choose an issue form at [New issue](https://github.com/srobroek/slopvac/issues/new/choose):

The forms cover these categories:

- **Bug:** Covers crashes, tracebacks, wrong exit codes, wrong or unstable output, or config, setup, init, Vale, cache, or prime defects.
- **False positive:** Covers text that a rule flags as slop incorrectly.
- **Missed slop:** Covers slop that no finding reports but an existing rule should catch. Use this form if unsure.
- **Mis-tagged:** Covers a finding on slop with the wrong rule, severity, or span/location.
- **Wrong fix:** Covers a correct match with a wrong message, replacement, or fix guidance. Use this form if `--fix` changes meaning or produces broken text.
- **New rule:** Covers a writing pattern that no existing rule detects.
- **Rule improvement:** Covers whole-rule changes to accuracy, examples, exceptions, judgment, tier, severity, genre advice, wording, or docs.

Before submitting an agent report, run `slopvac prime report`. Get the user's approval for the exact post.

Do not include paths or private data.
File names may only be `repro.md` and `slopvac.toml`.
Do not include user names, host names, repository names, or organisation names.
Paste sample text into the report. A local file path is not enough.
Prefer a synthetic sample over text from private or proprietary sources.
Record the agent product name. Record the active model exactly as the harness reports it in its system prompt, context, or `/model` selection. Do not use model self-description or config defaults. Write N/A when the active model is unavailable.
Get the harness version from its version command. Write N/A when unavailable.
Do not infer these fields from environment variables.
