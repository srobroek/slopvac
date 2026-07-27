# slopvac

Remove AI writing patterns from prose.

Generated documentation has a texture: contrastive inversions, adjectives nothing
measures, rationale that belongs in a decision record, roadmap language for something
that does not ship yet. Each model generation swaps the vocabulary and keeps the
shapes, so a word list goes stale while the structures persist.

Two skills. `write-docs` classifies a document by genre and authors against that
genre's rules. `review-docs` gates the result with a deterministic
[Vale](https://vale.sh) pass, judges the register against a catalog of tells no regex
reaches, and returns a verdict. Either runs alone. Hooks carry the same rules into
every subagent and gate prose files as they are edited.

Works with Claude Code, Codex, and Kiro.

## Quick start

Needs [`vale`](https://vale.sh) on `PATH` (`brew install vale`, or
`mise use -g vale`).

```sh
apm marketplace add srobroek/slopvac --name slopvac
apm install slopvac@slopvac --target claude --global   # or codex, or kiro
```

No APM installed? `uvx --from apm-cli apm ...` runs the same two commands. Claude
Code and Codex can also load this repo natively with
`/plugin marketplace add srobroek/slopvac`. Per-harness options, global against
project scope, and installing by hand are all under [Install](#install).

Then ask the agent: *"write the README for this package"*, or *"review this
README"*. It scaffolds a `.vale.ini` on first use and asks before writing.

## How it works

You ask the agent for a document, or to review one. The agent runs the gate and the
judgement pass.

```
you: "write the README for this package"
        │
        ▼
  write-docs skill ──── classifies the genre (consumer | change | internal)
                        loads that genre's rules, authors against them
        │
        ▼
  review-docs skill ─── scaffolds .vale.ini on first use (asks first)
                        runs the Vale gate      → deterministic findings
                        reads the tells catalog → register judgement
                        checks every claim against code at HEAD
        │
        ▼
  VERDICT: PASS | REVISE, with the one change worth making
```

The hooks close the loop without being asked. `SubagentStart` injects the rules
into every subagent, because a subagent inherits main-session steering weakly.
`PostToolUse` gates prose files after an edit, accumulating changes and returning
`file:line` findings once they cross a threshold.

## What it catches

Two layers, because half of this resists mechanization.

**Deterministic** -- 23 Vale rules across seven packages, each one regex over parsed
prose, tested and calibrated against a real corpus.

| Package | Rules | Catches |
| --- | --- | --- |
| `prose-agency` | `FalseAgency`, `AgentlessPassive`, `NarratorDistance` | The actor deleted: an abstraction acting, a passive with no agent, narration from outside the scene |
| `prose-inflation` | `SlopLexicon`, `BorderlineHype`, `VagueDeclarative`, `AdditiveHedge`, `BusinessJargon` | Claims past their evidence: marketing adjectives, significance without a specific, meeting-register verbs |
| `prose-scope` | `RejectedAlternative`, `ImplementationLeak`, `UnrequestedReassurance`, `Epigram` | Over-writing: a decision defended in place, a cost the reader cannot act on, an answer to a worry never raised, an epigram closing a section that already concluded |
| `ai-residue` | `ChatLeakage` | Assistant output pasted into a shipped document |
| `docs-discipline` | `StatusLanguage`, `HistoryNarration`, `InternalRefs` | Text describing something other than the released artifact |
| `prose-format` | `EmojiHeading`, `NoUnicodeDash`, `ProseBlock` | Emoji headings, Unicode dashes, paragraphs that should be a list |
| `ai-tells` | 76 upstream | [tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells), with the exclusions a software corpus needs applied |

**Agentic** -- the skill reads a catalog of tells no regex reaches, and applies them
by judgement:

| Category | Examples |
| --- | --- |
| Register | Faux-candor pivots, punchy-fragment cadence, corporate-analytic filler, figurative-verb verdicts, sycophantic residue |
| Structure | Contrastive inversion, tricolon abuse, false-suspense transitions, meta-narration, heading echo |
| Formatting | Em-dash density, bold spray, inline-header lists, tables wrapping one sentence |
| Content shape | Fabricated citations, fake specificity, one-point dilution, padded symmetry, vaporware description |
| Counter-signals | What expert prose has and generated prose lacks: non-round numbers, named specifics, an unhedged stance, asymmetric structure |

A document passes when both layers agree.

## Limits

A clean run means the checked patterns are absent, and nothing more. Neither layer
reads for truth: a sentence can pass every rule and still be wrong, name a function
that is absent from the code, describe a flag that never shipped, or contradict the paragraph
above it. Judgement of the register is a model reading a catalog, so it misses tells
and occasionally objects to prose that is fine.

Read the text before you ship it. The gate removes the patterns you would otherwise
spend attention on, so that the attention goes to whether the document is correct.

## Install

Needs `vale` on `PATH`:

```sh
mise use -g vale     # or: brew install vale
```

`ast-grep` is optional and extends the gate to JSX text nodes.

### Claude Code

Native plugin:

```
/plugin marketplace add srobroek/slopvac
```

With APM:

```sh
apm marketplace add srobroek/slopvac --name slopvac
apm install slopvac@slopvac --target claude --global   # every project
apm install slopvac@slopvac --target claude            # this project only
```

By hand, into `~/.claude` for every project or `.claude` for one:

```sh
git clone https://github.com/srobroek/slopvac /tmp/slopvac
mkdir -p .claude/skills .claude/hooks
cp -R /tmp/slopvac/packages/slopvac/.apm/skills/* .claude/skills/
cp -R /tmp/slopvac/packages/slopvac/scripts .claude/hooks/slopvac/
```

Then copy the events and matcher from `packages/slopvac/hooks/hooks.json` into
`.claude/settings.json`.

### Codex

Native plugin:

```
plugin marketplace add srobroek/slopvac
```

With APM:

```sh
apm marketplace add srobroek/slopvac --name slopvac
apm install slopvac@slopvac --target codex --global
```

By hand: as above, replacing `.claude` with `.codex`.

### Kiro

With APM:

```sh
apm marketplace add srobroek/slopvac --name slopvac
apm install slopvac@slopvac --target kiro --global
```

Install writes the skills, the steering, and the hook manifests Kiro reads
natively. Do not run `apm compile --target kiro`: it additionally writes a root
`AGENTS.md` that Kiro does not read as steering, and overwrites one already there.

By hand, into `~/.kiro` for every project or `.kiro` for one:

```sh
git clone https://github.com/srobroek/slopvac /tmp/slopvac
mkdir -p .kiro/skills .kiro/hooks
cp -R /tmp/slopvac/packages/slopvac/.apm/skills/* .kiro/skills/
cp -R /tmp/slopvac/packages/slopvac/scripts .kiro/hooks/slopvac/
```

Kiro reads one file per hook under `.kiro/hooks/`; copy the events and matcher from
`packages/slopvac/hooks/hooks.json`.

### Any harness, without installing APM

`uvx` runs APM from PyPI:

```sh
uvx --from apm-cli apm marketplace add srobroek/slopvac --name slopvac
uvx --from apm-cli apm install slopvac@slopvac --target kiro --global
```

`--global` installs to `~/.claude`, `~/.codex`, or `~/.kiro`. Drop it to install
into the current project, which is what you want when the config belongs in version
control with the code. Target several at once with `--target claude,codex,kiro`.

## Dependencies

| What | Needed for | Without it |
| --- | --- | --- |
| [`vale`](https://vale.sh) 3.x | The whole deterministic gate. Everything else is configuration for it. | The gate refuses to run and names the install command; the skill still applies its judgement rules by reading |
| `python3` 3.7+ | The `PostToolUse` hook and the finding reporter, both stdlib only | The hook exits quietly; the gate is unaffected |
| `jq` | The `SubagentStart` hook, to build its JSON payload | That hook warns on stderr and skips, so a spawn is never blocked |
| [`ast-grep`](https://ast-grep.github.io) | Extracting prose from `.tsx` and `.jsx`, which Vale cannot parse | Those files are reported as unchecked rather than passed silently |
| `bash` 3.2+ | The gate and scaffold scripts. Stock macOS bash is the floor, so no `mapfile` | -- |
| `git` | Resolving the repo root and honouring `.gitignore` | Ignored files get linted too |

The skills need none of this to be installed by APM; the gate needs `vale` at the
point it runs.

### Rule sources

`vale sync` fetches the style packages listed under
[What it catches](#what-it-catches). All but one are built from `vale-styles/` in
this repo; `ai-tells` comes from
[tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells) (MIT), whose 76 rules
arrive with the exclusions a software corpus needs already applied. The lexical rules in `prose-inflation` were harvested from
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT).

Development adds `pytest`, `bats`, `actionlint`, `zizmor`, `yamllint`, and
`shellcheck`, all pinned in the workflows.

## Configuration

The gate reads one file, `.vale.ini` at your project root, and the project owns it.
The agent scaffolds it on first use and asks before writing. It is committed; the
fetched `.vale-styles/` directory is not.

Take new upstream rules with `vale --config=.vale.ini sync`. Every URL in the file
points at a rolling release tag, so a sync is the whole update.

### Overriding a rule

Put the line inside the section it applies to, normally `[*.{md,mdx}]`: a rule line
binds to the section above it, so one appended at the end of the file attaches to
the last section instead.

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

Decision records invert some rules: a spec, a design record, or CONTRIBUTING is
where a rationale and its measurement belong, so those paths already exempt
`prose-scope` and the internal-reference rule.

## Using the styles without an agent

Every package is a plain Vale style that installs on its own. A project that wants
`prose-agency` and none of the house genre rules takes just that one:

```ini
StylesPath = .vale-styles
MinAlertLevel = warning
Packages = https://github.com/srobroek/slopvac/releases/download/vale-styles/prose-agency.zip

[*.md]
BasedOnStyles = prose-agency
```

Vale parses Markdown, MDX, HTML, JSON, and YAML, and it is syntax-aware for source
files: it lints comments and docstrings while skipping identifiers and string
literals, so a field named `robust` stays clean. `.mdx` needs `[formats]`
`mdx = md`, or Vale fails with `mdx2vast not found`.
`.tsx` and `.jsx` have no parser and no working alias, and Vale reports zero
findings and exits 0 for them, which reads as a pass -- the skill extracts their JSX
text with `ast-grep` instead.

See [vale-styles/README.md](vale-styles/README.md) for the full rule set.

## License

Apache-2.0. Bundles rules harvested from
[hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT).
