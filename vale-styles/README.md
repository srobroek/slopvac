# Vale styles

Five [Vale](https://vale.sh) styles that catch AI-generated prose patterns and
documentation-genre defects. Each is a separate package: take the ones that match
your writing, ignore the rest.

## Install

Add the styles you want to `.vale.ini`, then sync:

```ini
StylesPath = styles
MinAlertLevel = warning

Packages = https://github.com/srobroek/slopvac/releases/download/vale-styles/prose-agency.zip, \
  https://github.com/srobroek/slopvac/releases/download/vale-styles/prose-inflation.zip

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
| `prose-scope` | `RejectedAlternative`, `ImplementationLeak`, `UnrequestedReassurance` | Over-writing: a decision defended where it does not belong, a cost the reader cannot act on, an answer to a worry never raised |
| `ai-residue` | `ChatLeakage` | Assistant output pasted into a shipped document: cutoff disclaimers, refusal fragments, placeholder text, citation artifacts |
| `docs-discipline` | `StatusLanguage`, `HistoryNarration`, `InternalRefs` | Documentation describing something other than the released artifact: roadmap status, change narration, links to internal specs |
| `prose-format` | `EmojiHeading`, `NoUnicodeDash`, `ProseBlock` | Formatting tells: emoji headings, Unicode dashes, paragraphs that should be a list |

`prose-agency`, `prose-inflation`, `prose-scope`, and `ai-residue` apply to any
prose. Turn `prose-scope` off for decision records, where the rationale and its
measurement are the point.
`docs-discipline` encodes one house position -- that a doc describes what ships
today -- so read the rules before adopting it. `prose-format` is a house
convention, including a `--` preference over em dashes.

## prose-scope by example

These rules catch text that is correct and useful, sitting in a document whose job
is something else. Each row is a real finding from calibration.

| Flagged | Why | Instead |
| --- | --- | --- |
| "It reports findings rather than asking the agent, because a hook cannot invoke a skill." | Defends a choice against the alternative | "It reports findings." Put the reasoning in an ADR. |
| "For the same reason it does not run detached." | Same, by back-reference | Drop the sentence, or state what it does do. |
| "We chose Python for the hook." | Names the decision, not the behavior | Say what the hook does; the commit records why. |
| "The earlier implementation spawned a shell per check." | Lineage of the code | Describe the current behavior only. |
| "A shell version cost 212 ms per edit, against 52 ms here." | A benchmark result in prose; it ages into a false claim | Move it to the commit, or publish it as a table on a benchmarks page. |
| "An ordinary edit costs one Python startup." | A cost the reader cannot act on | Say nothing, or state the guarantee you will hold. |
| "Nothing here needs a package manager." | Answers a worry nobody raised | "Clone the repo and copy two directories." |
| "The skills work as soon as they are on disk." | Reassurance, no instruction | Delete; the install step above already said it. |
| "No configuration required." | Sales register | Delete; a step with no setup has no setup step. |

These stay clean, because the reader acts on them:

| Kept | Why |
| --- | --- |
| "A timeout of 50 ms applies to each call." | Configuration |
| "At most five subprocesses run concurrently." | A documented limit |
| "\| Rule evaluation \| 2.5 µs \|" | A published figure as structured data |
| "No signing needed for this path." | A factual scope note |
| "You need vale on PATH before the first run." | An instruction |
| "Removed the legacy flag in favor of the config key." | A changelog stating its delta |

`ImplementationLeak` uses `scope: paragraph`, so a figure in a table row or a list
item never fires. A benchmarks page is a deliverable. The rule is for a timing
asserted mid-sentence about how the implementation performs.

Decision records invert all three: point the section glob for your specs and design
records at `prose-scope.* = NO`, which the scaffolded config does already.

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

These need a workaround:

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
