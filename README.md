# slopvac

Remove AI writing patterns from prose.

`write-docs` authors a document against its genre's rules. `review-docs` gates the
result and returns a verdict. The gate is
[Vale](https://vale.sh) over six style packages, and two hooks carry the same rules
into every subagent and every edit.

Works with Claude Code, Codex, and Kiro.

## Install

Needs `vale` on `PATH`:

```sh
mise use -g vale     # or: brew install vale
```

`ast-grep` is optional and extends the gate to JSX text nodes.

### With APM

```sh
apm marketplace add srobroek/slopvac --name slopvac
apm install slopvac@slopvac --target claude,codex
```

For Kiro, target it directly:

```sh
apm install slopvac@slopvac --target kiro
```

### Without installing APM

`uvx` runs it from PyPI and leaves nothing behind:

```sh
uvx --from apm-cli apm marketplace add srobroek/slopvac --name slopvac
uvx --from apm-cli apm install slopvac@slopvac --target kiro
```

### By hand

Nothing here needs a package manager. Clone the repo and copy the two directories
your agent reads:

```sh
git clone https://github.com/srobroek/slopvac /tmp/slopvac

# Kiro
mkdir -p .kiro/skills .kiro/hooks
cp -R /tmp/slopvac/packages/slopvac/.apm/skills/* .kiro/skills/
cp -R /tmp/slopvac/packages/slopvac/scripts .kiro/hooks/slopvac/

# Claude Code
mkdir -p .claude/skills .claude/hooks
cp -R /tmp/slopvac/packages/slopvac/.apm/skills/* .claude/skills/
cp -R /tmp/slopvac/packages/slopvac/scripts .claude/hooks/slopvac/
```

The skills work as soon as they are on disk. To wire the hooks, copy the events and
the matcher from `packages/slopvac/hooks/hooks.json` into your agent's config: Kiro
reads one file per hook under `.kiro/hooks/`, Claude Code reads
`.claude/settings.json`.

### As a native plugin

The repo is a plugin marketplace for both Claude Code and Codex, so neither needs
APM:

```
/plugin marketplace add srobroek/slopvac      # Claude Code
plugin marketplace add srobroek/slopvac       # Codex
```

## First run

Scaffold the project config, which fetches the styles:

```sh
<skills>/review-docs/scripts/init-vale.sh
```

That writes a committed `.vale.ini` you own, and `.vale-styles/`, which it adds to
`.gitignore`. `--check` reports what is missing: exit 0 ready, 1 needs a sync, 2 no
config. `review-docs` runs the check itself on first use and asks before writing.

Take new rules with `vale --config=.vale.ini sync`. Every URL in the config points
at a rolling release tag, so a sync is the whole update.

## Use

```sh
<skills>/review-docs/scripts/slop-lint.sh --genre <consumer|change|internal> <file>...
```

Exit 0 clean or warnings only, 1 on any error, 2 on a missing tool or unsynced
styles. Or ask the agent: "review this README", "deslop this".

## Styles

| Style | Catches |
| --- | --- |
| `prose-agency` | The actor deleted: an abstraction acting, an agentless passive, narration from outside the scene |
| `prose-inflation` | Claims past their evidence: marketing adjectives, significance without a specific, meeting-register verbs |
| `prose-scope` | Over-writing: a rejected alternative defended in place, an implementation cost the reader cannot act on |
| `ai-residue` | Assistant output pasted into a shipped document |
| `docs-discipline` | Text describing something other than the released artifact |
| `prose-format` | Emoji headings, Unicode dashes, paragraphs that should be a list |

Each installs on its own, so a project can take `prose-agency` and leave the house
genre rules. See [vale-styles/README.md](vale-styles/README.md) to use them with
plain Vale. The gate also pulls
[tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells), with the exclusions
that a software corpus needs already applied.

## Overriding a rule

Edit the project `.vale.ini`. Put the line inside the section it applies to,
normally `[*.{md,mdx}]`: a rule line binds to the section above it, so one appended
at the end of the file attaches to the last section instead.

```ini
[*.{md,mdx}]
BasedOnStyles = ai-residue, prose-agency, prose-inflation, prose-scope, docs-discipline, prose-format, ai-tells

prose-scope.ImplementationLeak = NO        # latency is the product; we publish it
prose-format.NoUnicodeDash = NO            # house style uses real em dashes
prose-inflation.BusinessJargon = warning   # advisory, not a gate
```

| Scope | Change |
| --- | --- |
| One rule off | `rule = NO` |
| Advisory only | `rule = warning` |
| A whole style | drop it from that section's `BasedOnStyles` |
| One path | `[**/generated/**]` then `BasedOnStyles =` |
| One passage | `<!-- vale rule = NO -->` ... `<!-- vale rule = YES -->`, each on its own line |

## License

Apache-2.0. Bundles rules harvested from
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT).
