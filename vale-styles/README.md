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

<!-- BEGIN GENERATED: styles-table -->
| Style | Axis | Rules | Catches |
|---|---|---|---|
| `ai-residue` | slop | `ChatLeakage` | Assistant output pasted into a shipped document |
| `docs-discipline` | slop | `HistoryNarration`, `InternalRefs`, `StatusLanguage` | Documentation describing something other than the released artifact |
| `prose-agency` | slop | `AgentlessPassive`, `Anthropomorphism`, `FalseAgency`, `NarratorDistance`, `UnattributedRecommendation` | Prose with the actor deleted |
| `prose-craft` | craft | `AcronymPeriods`, `Ambiguity`, `Annotations`, `Articles`, `CommandPrompt`, `ConflictMarkers`, `DeadOpener`, `DirectionalRef`, `FirstPersonPlural`, `FutureTense`, `GerundHeading`, `Hyphens`, `Latinisms`, `LinkText`, `Misnomer`, `NegativeRequirement`, `OptionalPlural`, `Ordinals`, `PluralAbbreviation`, `Politeness`, `Redundancy`, `RelativeDate`, `SelfReference`, `SentenceLength`, `Spacing`, `UnclearAntecedent`, `UndefinedAcronym`, `Versions`, `Wordiness` | Writing craft: wordiness, structure, and mechanics, in any register |
| `prose-density` | craft | `Overwritten`, `PassiveDensity`, `SentenceLoad` | Prose too dense to read in one pass |
| `prose-format` | slop | `EmojiHeading`, `NoUnicodeDash`, `ProseBlock` | Formatting tells |
| `prose-inclusive` | craft | `Ableist`, `DeviceAssumption`, `Exclusive` | Language that excludes a reader who could otherwise use the doc |
| `prose-inflation` | slop | `AdditiveHedge`, `Apologizing`, `BorderlineHype`, `BusinessJargon`, `DocumentPreamble`, `HedgeStack`, `Intensifier`, `NominalizedVerb`, `SlopLexicon`, `Uncomparables`, `VagueDeclarative`, `VagueQuantifier` | Claims inflated past their evidence |
| `prose-scope` | slop | `Epigram`, `ImplementationLeak`, `RejectedAlternative`, `UnrequestedReassurance` | Over-writing: real content in the wrong document |
<!-- END GENERATED: styles-table -->

<!-- BEGIN GENERATED: rule-counts -->
63 rules across 9 styles. 28 sit on the slop axis and gate at error. 35 sit on the craft axis and warn.
<!-- END GENERATED: rule-counts -->

The two axes carry different weight. A slop-axis match is evidence about how the
text was produced, so those rules gate at error. A craft-axis match is bad writing
whoever wrote it, so those warn: worth fixing, not worth blocking a release over.
Keeping them apart is what lets the slop claim mean anything.

`prose-agency`, `prose-inflation`, `prose-scope`, `ai-residue`, and `prose-craft`
apply to any prose. Turn `prose-scope` off for decision records, where the
rationale and its measurement are the point.
`docs-discipline` encodes one house position -- that a doc describes what ships
today -- so read the rules before adopting it. `prose-format` is a house
convention, including a `--` preference over em dashes.

## Every rule

Generated from the rule files by `gen-rule-table.py`; CI fails when it drifts.

<!-- BEGIN GENERATED: rules-table -->
| Rule | Level | Check | What it catches |
|---|---|---|---|
| `ai-residue.ChatLeakage` | error | existence | E5 in the retired slop-lint.py. Errors in EVERY genre, change included: unlike |
| `docs-discipline.HistoryNarration` | error | existence | E4 in the retired slop-lint.py. Off for the change genre, where the delta is |
| `docs-discipline.InternalRefs` | error | existence | E3 in the retired slop-lint.py. |
| `docs-discipline.StatusLanguage` | error | existence | E1 in the retired slop-lint.py. Runtime-state uses of "currently" (currently |
| `prose-agency.AgentlessPassive` | error | existence | Passive voice with the actor deleted. |
| `prose-agency.Anthropomorphism` | error | existence | Software granted a mind. "The parser knows the schema", "the CI thinks it failed". |
| `prose-agency.FalseAgency` | error | existence | An abstraction promoted to actor, so no human has to be named. |
| `prose-agency.NarratorDistance` | error | existence | The lecturer voice: observations delivered from above the scene, with nobody |
| `prose-agency.UnattributedRecommendation` | error | existence | A recommendation with nobody behind it. "It is recommended that you rotate keys." |
| `prose-craft.AcronymPeriods` | warning | existence | Periods inside an initialism. "A.P.I.", "U.R.L." |
| `prose-craft.Ambiguity` | warning | existence | A construction with two readings and no way to pick one. |
| `prose-craft.Annotations` | warning | existence | A code annotation left in shipped prose. TODO, FIXME, XXX, HACK. |
| `prose-craft.Articles` | warning | substitution | The article before an initialism follows pronunciation, not spelling. |
| `prose-craft.CommandPrompt` | warning | existence (raw) | A shell prompt pasted into a code block. "$ npm install", "> Get-Item". |
| `prose-craft.ConflictMarkers` | error | existence (raw) | A Git merge conflict marker committed into prose. |
| `prose-craft.DeadOpener` | warning | existence | A sentence opening on a placeholder subject. |
| `prose-craft.DirectionalRef` | warning | substitution | A cross-reference that depends on where the text landed on the page. |
| `prose-craft.FirstPersonPlural` | warning | existence | The document speaking as a company. "our platform empowers your team". |
| `prose-craft.FutureTense` | warning | existence | Documentation in the future tense. "The loader will retry twice." |
| `prose-craft.GerundHeading` | warning | existence (heading) | A task heading in the -ing form. |
| `prose-craft.Hyphens` | warning | existence | An adverb hyphenated to the word it modifies. "newly-added", "only-but". |
| `prose-craft.Latinisms` | warning | substitution | A Latin abbreviation where an English phrase reads faster. |
| `prose-craft.LinkText` | warning | existence (raw) | A link whose text says nothing. "[here](...)", "[click here](...)", "[link](...)". |
| `prose-craft.Misnomer` | warning | existence | An initialism followed by the word its own last letter stands for. |
| `prose-craft.NegativeRequirement` | warning | existence | A requirement stated as a prohibition. "You cannot deploy without a token." |
| `prose-craft.OptionalPlural` | warning | existence | A plural offered in parentheses. "Select the file(s)." |
| `prose-craft.Ordinals` | warning | existence | An ordinal in the wrong form. |
| `prose-craft.PluralAbbreviation` | warning | sequence | An apostrophe making an initialism plural. "API's" for more than one API. |
| `prose-craft.Politeness` | warning | existence | Courtesy words in an instruction. "Please run the migration first." |
| `prose-craft.Redundancy` | warning | existence | A phrase that says the same thing twice in its own grammar. |
| `prose-craft.RelativeDate` | warning | existence | A date the reader cannot resolve. "recently", "last month", "as of this year". |
| `prose-craft.SelfReference` | warning | existence | A document narrating its own structure. |
| `prose-craft.SentenceLength` | warning | occurrence (sentence) | A sentence past the point where a reader holds it in one pass. |
| `prose-craft.Spacing` | warning | existence | A sentence boundary with the wrong number of spaces. |
| `prose-craft.UnclearAntecedent` | warning | existence | A sentence opening on a bare demonstrative. "This is why it fails." |
| `prose-craft.UndefinedAcronym` | warning | conditional | An initialism used before it is expanded. |
| `prose-craft.Versions` | warning | substitution | A version comparison stated as magnitude instead of order. |
| `prose-craft.Wordiness` | warning | substitution | A long phrase where a short word does the same work. |
| `prose-density.Overwritten` | warning | metric | RIX (Anderson 1983): long words per sentence. |
| `prose-density.PassiveDensity` | warning | script (raw) | The share of sentences in the passive voice, measured across the whole document. |
| `prose-density.SentenceLoad` | warning | metric | Average sentence length across a document. |
| `prose-format.EmojiHeading` | warning | existence (heading) | W2 in the retired slop-lint.py. `scope: heading` replaces the old manual |
| `prose-format.NoUnicodeDash` | error | existence (raw) | House ban: no em-dash (U+2014) or en-dash (U+2013) anywhere in a file, prose |
| `prose-format.ProseBlock` | warning | occurrence (paragraph) | W1 in the retired slop-lint.py. `%d`, not `%s`: occurrence populates an int and |
| `prose-inclusive.Ableist` | warning | substitution | Disability used as an insult or a metaphor. |
| `prose-inclusive.DeviceAssumption` | warning | substitution | An instruction that assumes the reader's input device. |
| `prose-inclusive.Exclusive` | warning | substitution | Terms with an exclusionary history that have a settled plain replacement. |
| `prose-inflation.AdditiveHedge` | error | existence | "not just X but also Y" -- the additive hedge. Both halves are claimed, and the |
| `prose-inflation.Apologizing` | error | existence | Deferring the claim instead of making or cutting it. |
| `prose-inflation.BorderlineHype` | warning | existence | W3 in the retired slop-lint.py. Warning, not error: each of these has a |
| `prose-inflation.BusinessJargon` | error | existence | Meeting-register verbs that survive into written docs. The fix is the plain |
| `prose-inflation.DocumentPreamble` | error | existence | A document announcing what it is about to do. |
| `prose-inflation.HedgeStack` | error | existence | Two or more hedges on one claim. "can help to potentially reduce". |
| `prose-inflation.Intensifier` | error | existence | Degree adverbs that add emphasis and no information. |
| `prose-inflation.NominalizedVerb` | error | existence | A verb buried in a noun, propped up by a light verb. |
| `prose-inflation.SlopLexicon` | error | existence | E2 in the retired slop-lint.py. |
| `prose-inflation.Uncomparables` | error | existence | An absolute modified by degree. "very unique", "more complete", "most perfect". |
| `prose-inflation.VagueDeclarative` | error | existence | A sentence that asserts significance without naming the thing. The tell is an |
| `prose-inflation.VagueQuantifier` | warning | existence | A quantity word standing in for a number nobody counted. |
| `prose-scope.Epigram` | warning | existence (paragraph) | Over-writing: a closing line that restates the section as an aphorism. |
| `prose-scope.ImplementationLeak` | error | existence (paragraph) | Over-writing: internal implementation facts the reader of this document cannot |
| `prose-scope.RejectedAlternative` | error | existence | Over-writing: text defending a decision inside a document whose job is to |
| `prose-scope.UnrequestedReassurance` | error | existence | Over-writing: a sentence answering a worry the reader never raised. |
<!-- END GENERATED: rules-table -->

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
- `.tsx` and `.jsx` have no parser, and no `[formats]` alias fixes it: `tsx = html`
  errors out and `tsx = md` reports **zero findings and exits 0**, which reads as a
  pass. Extract the JSX text nodes and lint those instead. slopvac ships
  `extract-prose.sh` for this, which uses `ast-grep` to pull `jsx_text` and
  copy-bearing attributes into a line-preserving shadow file, so findings still
  report against the real `.tsx` line.

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
