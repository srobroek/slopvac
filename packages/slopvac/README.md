# slopvac skills

Author and review prose with `write-docs` and `review-docs`.

The `slopvac` CLI runs the deterministic checks, using settings from
`slopvac.toml`. The packaged catalogue contains 166 checked rules and 65
contextual rules across 26 categories. Contextual review runs on request and
does not change the deterministic result.

`write-docs` applies the document's genre rules. `review-docs` runs the CLI,
checks claims against the code, and reviews the text for its intended reader.

Works with Oh My Pi, Claude Code, Codex, and Kiro.

## Install

Run the CLI without installing it:

```sh
uvx slopvac README.md
```

For a persistent installation, use `uv tool install slopvac`.

[Vale](https://vale.sh) is optional but **highly recommended**. It executes most
of the deterministic rules. Install Vale 3.15 or later and put it on `PATH`;
slopvac supplies its configuration and styles. Without Vale, selected
Vale-backed checks are unchecked and the CLI returns exit 2.

### Oh My Pi

```sh
omp plugin marketplace add srobroek/slopvac
omp plugin install slopvac@slopvac --scope user
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

Copy `skills/` into `.kiro/skills` for Kiro. The corresponding directories are
`.claude/skills` for Claude Code and `.codex/skills` for Codex.

See the [installation guide](../../README.md#agent-skills) for project scope
and local checkouts. The [CLI reference](../slopvac-lint/README.md) covers
[configuration](../slopvac-lint/README.md#configuration),
[suppressions](../slopvac-lint/README.md#suppress-a-finding), and the
[judgement workflow](../slopvac-lint/README.md#judgement-layer).

## Limits

A passing run means the selected checks stayed within configured thresholds.
It does not establish factual correctness or identify who wrote the text.
Review claims against the code and read the text before publishing it.

## License

Apache-2.0.
