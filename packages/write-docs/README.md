# write-docs

`write-docs` supplies the rules and the deterministic gate for written artifacts:
READMEs, consumer docs, PR and release text, specs, ADRs, and CONTRIBUTING. It
ships two skills, a Vale prose gate, and a hook that carries the same rules into
every subagent.

Install the APM package `write-docs@srobroek-agentic`. The gate needs `vale` on
`PATH` (`mise use -g vale`, or `brew install vale`). `ast-grep` is optional and
extends the gate to JSX text nodes.

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

| Event | Effect |
| --- | --- |
| `SubagentStart` | Injects the documentation discipline into every subagent. A subagent inherits main-session steering weakly, so its only trigger signal would otherwise be a one-line skill description. The digest opens with its own condition, so a code-only subagent ignores it. |
| `PostToolUse` | After edits to prose files, runs the gate and reports findings with the `review-docs` pointer. Accumulates across edits and applies a cooldown, so it fires on a body of work rather than every write. |

Both fail open: a missing `jq` or `vale` never blocks a spawn or an edit.

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
