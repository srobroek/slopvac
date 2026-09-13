# slopvac skills

Author and review prose with `write-docs` and `review-docs`.

The mechanical gate is the `slopvac` CLI: 232 rules in 25 categories, configured
by `slopvac.toml`. Install it with `uvx slopvac`. The skills do not run Vale
as a standalone gate.

`write-docs` classifies a document by genre and authors against that genre's
rules. `review-docs` runs `slopvac`, judges the register, and returns a verdict.

Works with Oh My Pi, Claude Code, Codex, and Kiro.

## Install

```sh
uvx slopvac README.md
```

**Oh My Pi**

```sh
omp plugin marketplace add srobroek/slopvac
omp plugin install slopvac@slopvac --scope user
```

**Claude Code**

```
/plugin marketplace add srobroek/slopvac
/plugin install slopvac@slopvac
```

**Codex**

```
codex plugin marketplace add srobroek/slopvac
codex plugin add slopvac@slopvac
```

Copy `skills/` into `.kiro/skills` for Kiro, or into `.claude/skills` /
`.codex/skills` for a hand install.

The root [README](../../README.md) has the full install matrix, profiles,
`slopvac-allow` syntax, pre-commit hooks, and the GitHub Action.
[`packages/slopvac-lint/README.md`](../slopvac-lint/README.md) is the CLI
contract.

## Limits

A clean lint run means the checked patterns were not found. Verify claims against
code. Read the text before you ship it.

## License

Apache-2.0.
