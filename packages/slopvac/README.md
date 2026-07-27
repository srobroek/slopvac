# write-docs

`write-docs` supplies the rules and the deterministic gate for written artifacts:
READMEs, consumer docs, PR and release text, specs, ADRs, and CONTRIBUTING. It
ships two skills, a Vale prose gate, and a hook that carries the same rules into
every subagent.

The gate needs `vale` on `PATH` (`mise use -g vale`, or `brew install vale`).
`ast-grep` is optional and extends the gate to JSX text nodes.

```sh
apm marketplace add srobroek/slopvac --name slopvac
apm install slopvac@slopvac --target claude,codex
vale --config=.claude/skills/review-docs/vale/.vale.ini sync
```

For Kiro, install and sync; there is no compile step:

```sh
apm install slopvac@slopvac --target kiro
vale --config=.kiro/skills/review-docs/vale/.vale.ini sync
```

Kiro receives the skill at `.kiro/skills/`, the steering at `.kiro/steering/`, and
a hook manifest at `.kiro/hooks/`.

The sync is required before the first run on every target; no style is committed.

## Skills

| Skill | Use |
| --- | --- |
| `write-docs` | Classify a document by genre, load that genre's rules, author or rewrite against them, then hand off to `review-docs` |
| `review-docs` | Run the gate and the register judgement the patterns cannot reach. Called by `write-docs`, and callable alone to review text you did not write |

`review-docs` owns the rules, the marker catalog, and the verdict format.
`write-docs` owns genre routing and the authoring rules. Neither carries a second
copy.

## Genres

Each genre has a different test for whether a sentence belongs.

| Surface | Rules |
| --- | --- |
| README, `docs/**`, anything a user of the artifact reads | Every sentence verifiable against code at HEAD; no roadmap; no internal references; every example runnable |
| PR bodies, commit messages, release notes | Describes a delta: what changed, why, test plan; every claim maps to a diff hunk |
| Specs, ADRs, constitutions, CONTRIBUTING, runbooks | Contributor audience, so internal references are allowed; same prose discipline |

## The gate

```sh
scripts/slop-lint.sh --genre <consumer|change|internal> <file>...
```

Exit 0 clean or warnings only, 1 on any error, 2 on a usage error or a missing
tool. Vale itself exits non-zero on warnings; this script reads the JSON and maps
severities so warnings alone do not fail a run.

Rules come from six Vale styles authored in `vale-styles/` at the repo root and
one vendored style, all fetched by `vale sync`:

| Style | Catches |
| --- | --- |
| `prose-agency` | The actor deleted: an abstraction acting, an agentless passive, narration from outside the scene |
| `prose-inflation` | Claims past their evidence: marketing adjectives, significance without a specific, meeting-register verbs |
| `prose-scope` | Over-writing: a rejected alternative defended in place, an implementation cost the reader cannot act on, an answer to a worry never raised |
| `ai-residue` | Assistant output pasted into a shipped document |
| `docs-discipline` | Text describing something other than the released artifact |
| `prose-format` | Emoji headings, Unicode dashes, paragraphs that should be a list |
| `ai-tells` | 76 upstream rules from [tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells); four disabled and four demoted here, each with the measured reason |

### Project configuration

The gate reads one config file, and the project owns it. Scaffold it once:

```sh
scripts/init-vale.sh          # writes .vale.ini, fetches the styles
scripts/init-vale.sh --check  # 0 ready, 1 needs a sync, 2 no config
```

`.vale.ini` is committed and yours to edit; `init-vale.sh` never overwrites it.
`.vale-styles/` is fetched and added to `.gitignore`. Take new upstream rules with
`vale --config=.vale.ini sync`, because every URL in the file points at a rolling
release tag.

`slop-lint.sh` prefers the nearest project `.vale.ini`, walking up from the file
being linted, and falls back to the packaged config. `SLOP_LINT_CONFIG` overrides
both.

### Overriding a rule

Edit the project `.vale.ini`. Put the line inside the section it applies to,
normally `[*.{md,mdx}]`: a rule line binds to the section above it, so one
appended at the end of the file attaches to the last section instead and the rule
keeps firing everywhere else.

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

Vale has no `include` or `extends` directive, so the scaffolded file is the whole
configuration. It ships with every measured exclusion already in place, so a
project changes one line rather than authoring the file.

### Which files

Markdown, MDX, HTML, reStructuredText, AsciiDoc, JSON, and YAML get the full
ruleset. Source files get a reduced allowlist: Vale lints their comments and
docstrings and skips identifiers and string literals, so a field named `robust`
does not trip the lexicon, while the doc comment above it does.

`.tsx` and `.jsx` have no Vale parser. Their JSX text nodes are extracted by
`scripts/extract-prose.sh`, which needs `ast-grep` and is skipped with a hint when
it is absent.

## Hooks

### `SubagentStart` -- `inject-doc-discipline.sh`

Injects the documentation rules into every subagent. A subagent inherits
main-session steering weakly, so without this its only trigger signal is a
one-line skill description. The digest opens with its own condition, so a
code-only subagent ignores it.

### `PostToolUse` -- `prose-gate-advisory.py`

Runs the prose gate on files an edit just touched and returns the findings to the
agent. Step by step:

1. Parses the tool payload and collects every file path the call wrote.
2. Keeps the ones the gate covers: `.md`, `.mdx`, `.html`, `.json`, `.yaml`,
   `.tsx`, `.jsx`. Drops vendored and generated trees, then drops anything
   `git check-ignore` reports, in one batched call.
3. Adds the changed-line and file counts to a per-repo counter and returns
   silently until they cross a threshold, then applies a cooldown. A long editing
   run produces one advisory, not one per keystroke.
4. Runs `slop-lint.sh` and returns `file:line` findings, plus a pointer to
   `review-docs` for the register judgement the linter cannot make.

An absent `vale`, an unsynced `styles/` directory, or a JSX edit without
`ast-grep` returns a `PROSE GATE UNAVAILABLE` block naming what went unchecked and
the command that fixes it. The hook always exits 0 and never blocks the edit.

Both hooks run on Claude Code, Codex, and Kiro from one manifest. The matcher
covers each harness's file-writing tools, and the payload parser reads
`file_path` (Claude), a patch body (Codex `apply_patch`), and `path` (Kiro).

## Configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `SLOPVAC_ADVISORY_LINES` | `120` | Changed prose lines that accumulate before the PostToolUse advisory fires |
| `SLOPVAC_ADVISORY_FILES` | `5` | Prose files touched before the advisory fires |
| `SLOPVAC_ADVISORY_COOLDOWN_SECONDS` | `300` | Minimum interval between advisories |

Rule levels are overridden in the consuming `.vale.ini`, which survives a sync:

```ini
prose-format.NoUnicodeDash = NO
prose-inflation.BusinessJargon = warning
```

## License

Apache-2.0.
