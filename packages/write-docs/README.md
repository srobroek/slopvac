# write-docs

`write-docs` supplies the rules and the deterministic gate for written artifacts:
READMEs, consumer docs, PR and release text, specs, ADRs, and CONTRIBUTING. It
ships two skills, a Vale prose gate, and a hook that carries the same rules into
every subagent.

The gate needs `vale` on `PATH` (`mise use -g vale`, or `brew install vale`).
`ast-grep` is optional and extends the gate to JSX text nodes.

```sh
apm marketplace add srobroek/agentic-packages --name srobroek-agentic
apm install write-docs@srobroek-agentic --target claude,codex
vale --config=.claude/skills/write-docs/vale/.vale.ini sync
```

For Kiro, install and sync; there is no compile step:

```sh
apm install write-docs@srobroek-agentic --target kiro
vale --config=.kiro/skills/write-docs/vale/.vale.ini sync
```

Kiro receives the skill at `.kiro/skills/`, the steering at `.kiro/steering/`
with `inclusion: fileMatch` frontmatter, and a Kiro-shaped hook manifest at
`.kiro/hooks/`. Running `apm compile --target kiro` is wrong here: it writes the
steering again into a root `AGENTS.md`, which Kiro does not read as steering, and
overwrites an existing `AGENTS.md`.

The sync is required before the first run, on every target: no style is committed.

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

Rules come from five Vale styles authored in `vale-styles/` at the repo root and
one vendored style, all fetched by `vale sync`:

| Style | Catches |
| --- | --- |
| `prose-agency` | The actor deleted: an abstraction acting, an agentless passive, narration from outside the scene |
| `prose-inflation` | Claims past their evidence: marketing adjectives, significance without a specific, meeting-register verbs |
| `ai-residue` | Assistant output pasted into a shipped document |
| `docs-discipline` | Text describing something other than the released artifact |
| `prose-format` | Emoji headings, Unicode dashes, paragraphs that should be a list |
| `ai-tells` | 76 upstream rules from [tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells); four disabled and four demoted here, each with the measured reason |

Run `vale --config=<skill>/vale/.vale.ini sync` before the first run. The script
exits 2 and names the missing styles when a sync has not happened.

### Which files

Markdown, MDX, HTML, reStructuredText, AsciiDoc, JSON, and YAML get the full
ruleset. Source files get a reduced allowlist: Vale lints their comments and
docstrings and skips identifiers and string literals, so a field named `robust`
does not trip the lexicon, while the doc comment above it does.

The full ruleset on source files produced 214 findings across 55 files in this
repo, almost all false -- code-comment register is terse and legitimately negative.
The allowlist produces 8. Widen it only with a corpus measurement.

`.tsx` and `.jsx` have no Vale parser and no working format alias: Vale reports
zero findings and exits 0, which reads as a pass. Their JSX text nodes are
extracted by `scripts/extract-prose.sh`, which needs `ast-grep` and is skipped
with a hint when it is absent.

## Hooks

### `SubagentStart` -- `inject-doc-discipline.sh`

Injects the documentation rules into every subagent. A subagent inherits
main-session steering weakly, so without this its only trigger signal is a
one-line skill description. The digest opens with its own condition, so a
code-only subagent ignores it.

### `PostToolUse` -- `prose-gate-advisory.sh`

Runs the prose gate on files an edit just touched and returns the findings to the
agent. Step by step:

1. Reads the tool payload and collects every file path the call wrote.
2. Keeps the ones the gate covers: `.md`, `.mdx`, `.html`, `.json`, `.yaml`,
   `.tsx`, `.jsx`. Skips `node_modules/`, `apm_modules/`, `dist/`, `.venv/`.
3. Adds the changed-line and file counts to a per-repo counter and returns
   silently until they cross a threshold, then applies a cooldown. A long editing
   run produces one advisory, not one per keystroke.
4. Runs `slop-lint.sh` and returns `file:line` findings, plus a pointer to
   `review-docs` for the register judgement the linter cannot make.

It reports findings rather than asking the agent to run the skill, because a hook
cannot invoke a skill -- only request one, which is the unreliable path the hook
replaces.

Missing tools are loud. A silent skip would leave prose ungated while the hook
reports success, so an absent `vale`, an unsynced `styles/` directory, or a
JSX edit without `ast-grep` returns a `PROSE GATE UNAVAILABLE` block naming what
went unchecked and the command that fixes it. The hook still exits 0: a
`PreToolUse` guard may block, a `PostToolUse` advisory must not.

Both hooks run on Claude Code, Codex, and Kiro from one manifest. The matcher
covers each harness's file-writing tools, and the payload parser reads
`file_path` (Claude), a patch body (Codex `apply_patch`), and `path` (Kiro).

## Configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `WRITE_DOCS_ADVISORY_LINES` | `120` | Changed prose lines that accumulate before the PostToolUse advisory fires |
| `WRITE_DOCS_ADVISORY_FILES` | `5` | Prose files touched before the advisory fires |
| `WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS` | `300` | Minimum interval between advisories |

Rule levels are overridden in the consuming `.vale.ini`, which survives a sync:

```ini
prose-format.NoUnicodeDash = NO
prose-inflation.BusinessJargon = warning
```

## License

Apache-2.0.
