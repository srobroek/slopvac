# Vale styles

Five [Vale](https://vale.sh) styles that catch AI-generated prose patterns and
documentation-genre defects. Each is a separate package: take the ones that match
your writing, ignore the rest.

## Install

Add the styles you want to `.vale.ini`, then sync:

```ini
StylesPath = styles
MinAlertLevel = warning

Packages = https://github.com/srobroek/agentic-packages/releases/download/vale-styles/prose-agency.zip, \
  https://github.com/srobroek/agentic-packages/releases/download/vale-styles/prose-inflation.zip

[*.md]
BasedOnStyles = prose-agency, prose-inflation
```

```sh
vale sync
vale README.md
```

The `vale-styles` tag is a rolling release: its assets are replaced on every
publish, so the URLs above always serve the current rules.

## Styles

| Style | Rules | Catches |
|---|---|---|
| `prose-agency` | `FalseAgency`, `AgentlessPassive`, `NarratorDistance` | Prose with the actor deleted: an abstraction doing the acting, a passive with no agent, observation from outside the scene |
| `prose-inflation` | `SlopLexicon`, `BorderlineHype`, `VagueDeclarative`, `AdditiveHedge`, `BusinessJargon` | Claims inflated past their evidence: marketing adjectives, significance asserted without a specific, meeting-register verbs |
| `ai-residue` | `ChatLeakage` | Assistant output pasted into a shipped document: cutoff disclaimers, refusal fragments, placeholder text, citation artifacts |
| `docs-discipline` | `StatusLanguage`, `HistoryNarration`, `InternalRefs` | Documentation describing something other than the released artifact: roadmap status, change narration, links to internal specs |
| `prose-format` | `EmojiHeading`, `NoUnicodeDash`, `ProseBlock` | Formatting tells: emoji headings, Unicode dashes, paragraphs that should be a list |

`prose-agency`, `prose-inflation`, and `ai-residue` apply to any prose.
`docs-discipline` encodes one house position -- that a doc describes what ships
today -- so read the rules before adopting it. `prose-format` is a house
convention, including a `--` preference over em dashes.

## Rule levels

Everything is `error` except `prose-inflation.BorderlineHype` and
`prose-format.ProseBlock`, which are `warning`.

Vale exits non-zero on any alert at or above `MinAlertLevel`, warnings included.
To fail only on errors, set `MinAlertLevel = error`, or read `--output=JSON` and
map severities yourself.

Override any level in your own `.vale.ini`; it survives a sync:

```ini
prose-format.NoUnicodeDash = NO
prose-inflation.BusinessJargon = warning
```

## Which files to lint

Vale parses Markdown, HTML, reStructuredText, AsciiDoc, JSON, and YAML natively.
It is also syntax-aware for source files -- it lints comments and docstrings while
skipping identifiers and string literals, so a variable named `robust` does not
trip `SlopLexicon`.

Two extensions need care:

- `.mdx` has no parser. Without `[formats]` `mdx = md` Vale fails with
  `mdx2vast not found` and exit 1.
- `.tsx` and `.jsx` have no parser and no working alias. Vale reports **zero
  findings and exits 0**, which reads as a pass. `tsx = html` errors out;
  `tsx = md` is silent. Extract JSX text nodes with a separate tool.

Any extension you add to a section needs a fixture proving it produces findings.

## Developing

One directory per package. The directory name is the style name, so
`prose-agency/FalseAgency.yml` is referenced as `prose-agency.FalseAgency`.

```sh
./build.sh            # writes dist/<style>.zip for each directory
./build.sh /tmp/out   # or to a chosen directory
```

To test a change before publishing, serve `dist/` over HTTP and point `Packages`
at it. Vale rejects `file://` URLs.

Measure a new or widened rule against a real corpus before shipping it. A rule
that fires mostly on correct prose trains readers to ignore the whole style.

## Licence

Apache-2.0.
