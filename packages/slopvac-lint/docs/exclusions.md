# Measured exclusions from `.vale.ini`

Source: `packages/slopvac/.apm/skills/review-docs/vale/.vale.ini:56-118`.
All 13 rule-level dispositions against the upstream `tbhb/vale-ai-tells` package.
Corpus where quoted: 488 tracked `*.md` in the source repo.

| Vale rule | Disposition | Measurement / reason | Carry over? |
|---|---|---|---|
| `ai-tells.OverusedVocabulary` | `NO` | ~190 tokens of the 2023-mid-2024 lexical era-band our own appendix records as retired (delve, tapestry, testament, intricate, pivotal, meticulous, underscores, multifaceted, myriad, plethora), plus a creative-writing tail (gossamer, labyrinthine) and words with ordinary technical uses (comprehensive, granular, scalable). `prose-inflation.SlopLexicon` owns the maintained ban list. | Yes. Kept disabled. `prose-inflation.slop-lexicon` is the replacement and is enforced at every tier. |
| `ai-tells.FormalRegister` | `NO` | Flags implement / implementation / implementing / framework / frameworks. Correct words in this corpus. | Yes. Kept disabled. Same class as the `prose-craft.wordiness` technical-homograph trim. |
| `ai-tells.RedundantPrecaution` | `NO` | One idiom per rule file (over-fitted). | Yes. Kept disabled. No replacement. |
| `ai-tells.GrowthMetaphors` | `NO` | Startup-as-organism metaphors (domain-narrow). | Yes. Kept disabled. No replacement. |
| `ai-tells.EmDashUsage` | `NO` | Token list includes the literal `--`, this repo's sanctioned dash form: 6,743 `--` against 2,124 real Unicode dashes, so it fired ~40 times per document on the house convention and buried every other finding. | Yes. Kept disabled. Replaced by `prose-format.no-unicode-dash` (presence, error) plus `ai-tells-formatting.em-dash-density` (density, threshold INFERRED not measured). |
| `ai-tells.FormalTransitions` | `NO` | "Specifically", "likewise", "therefore", "additionally" at error. Ordinary English connectives used correctly here; the rule encodes a preference for shorter connectors, not a generated-text signal. | Yes. Kept disabled. This is why `ai-tells-content-shape.textbook-connector-runs` carries only the ADJACENCY claim (two consecutive sentence openings) and no bare token list. |
| `ai-tells.SemicolonUsage` | `NO` | 612 hits; matches are ordinary correct punctuation (a semicolon joining two independent clauses in a steering rule). Encodes a preference about punctuation frequency, not an AI tell. | Yes. Kept disabled. No replacement; do not port. |
| `ai-tells.ColonUsage` | `NO` | 128 hits; same class ("Note: Serena"). | Yes. Kept disabled. No replacement; do not port. |
| `ai-tells.ShipOveruse` | `NO` | 53 hits, all the literal verb ("the package ships a skill", "shipped in v2"). Domain vocabulary; in a software repo the word carries no signal at all. Disabled rather than demoted for that reason. | Yes. Kept disabled. No replacement. |
| `ai-tells.MicDrop` | `warning` | Upstream's own rule comments concede the pattern is over-broad. | Yes. `prose-scope.epigram` is the nearest owned rule and carries the same warning level for the same reason. |
| `ai-tells.ParallelStaccato` | `warning` | Same: upstream concedes over-breadth. | Yes. `ai-tells-structure.staccato-negative-parallel-frames` inherits the warning level explicitly. |
| `ai-tells.AICompoundPhrases` | `warning` | Same dead era-band as `OverusedVocabulary` (intricate, tapestry, testament, pivotal, multifaceted), scored as compound pairs. Demoted rather than disabled because the compound form is a stronger signal than the bare adjective: worth seeing, not gating on. | Yes. No owned replacement; keep it in Vale at warning. |
| `ai-tells.VerbTricolon` | `warning` | 149 hits, and the rule cannot tell a rhetorical tricolon from a three-item technical enumeration ("create, update, and delete"), which this corpus is full of. | Yes. `ai-tells-structure.tricolon-abuse-core` ships at warning citing this same 149-hit measurement. |

## The 23 orphaned `ai-tells` rules (never in `.vale.ini`, so never measured)

A second set of `ai-tells` rules existed only on the retired `agentic-packages`
branch `chore/context-engineering-audit` and in the archived
`bailiff/.vale-styles/ai-tells/`. They were never referenced from any
`.vale.ini`, so the 488-file corpus never ran them and there is no hit count for
any of them. Ported on that basis, at the levels recorded in
`rules/ai-tells-figurative.yml`.

| Vale rule | Disposition | Reason |
|---|---|---|
| `Figurative{Sits,Runs,Falls,Draws,Casts,Strikes,Wins,Lends,Rides,Loud}` | Ported, `warning` | One rule per verb, because the scope caveat differs per verb. `ai-tells-register.figurative-verb-verdict-core` reaches none of them: it is a 10-token list about verdicts. |
| `ResonateOveruse` | Ported, `warning` | Single token, no owned rule matched it. |
| `ColloquialAssessments` | Ported, `warning` | Overlaps an owned rule on one branch of 22 (`the point lands`). |
| `PromotionalPuffery` | Ported, `error` | 0 of 55 tokens reachable. `prose-inflation.slop-lexicon` owns single adjectives; this owns multi-word constructions. |
| `StrategyBuzzwords` | Ported, `error` | Only `north star` was owned. Flywheel, moat, network-effect, land-grab were not. |
| `AIAdjectiveNounPairs` | Ported, `warning`, narrowed | Vale `sequence` with POS tags; this engine has no tagger outside `kind: vocabulary`, so the noun side is a following lowercase word. Under-matches, which is the safe direction. `holistic`/`seamless`/`comprehensive` dropped as already owned. |
| `OverusedVocabularyVerbs` | Ported, `warning`, as tokens | Same POS problem, so noun uses fire too; `domain-term` is the exception for them. `leverage` dropped as already owned. |
| `SemicolonUsage`, `ColonUsage`, `ShipOveruse`, `FormalRegister`, `RedundantPrecaution`, `GrowthMetaphors`, `AICompoundPhrases` | NOT ported | Same rules as the measured table above, which already says not to port them. A filename absent from the engine is not evidence of a gap when the reason is recorded. |

`FigurativeStrikes` does NOT cover `strikes a balance`: the source noun list is
note/tone/chord. The loader's example check established that by rejecting a
first draft that claimed otherwise.

## Section-level exclusions (not rule dispositions, same institutional value)

| Scope | What is turned off | Measurement / reason | Carry over? |
|---|---|---|---|
| `[*.{go,rs,py,...}]` source files | `BasedOnStyles` emptied; 13-rule ALLOWLIST substituted | Full set produced 214 findings across 55 shell/Python files, almost all false: code-comment register is terse and legitimately negative (a test named "No PCRE, no \b" trips `ContrastiveNegation`). The allowlist scored 8 on the same files, 7 of them a ban list quoted inside `inject-doc-discipline.sh`. Every allowlisted rule is one whose match is a defect in any register. | Yes. The allowlist IS the "enforced at relaxed" set: `ai-residue.chat-leakage`, `prose-inflation.slop-lexicon`/`business-jargon`/`vague-declarative`/`additive-hedge`, `docs-discipline.status-language`, `prose-agency.false-agency`/`agentless-passive`, `prose-format.no-unicode-dash`. |
| same | `NoUnicodeDash` IS in the allowlist | An earlier revision excluded it believing it fired on `--`; that was wrong. The rule cannot match `--`, and the 172 hits were real U+2014/U+2013 in source comments (206 Unicode dashes against 2,591 ASCII `--` across the same files). | Yes. Recorded in `prose-format.no-unicode-dash` provenance. |
| same | Structural and punctuation-frequency rules excluded by design | "Add one only with a corpus measurement." | Yes. Encoded as the tier policy: structural/metric rules are `excluded` or `advisory` at relaxed. |
| `[{specs,.specify}/**]`, `[**/{adr,ADR}/**]`, `[**/{CONTRIBUTING,constitution}*.md]` | `docs-discipline.InternalRefs`, `prose-scope.RejectedAlternative`, `prose-scope.ImplementationLeak` | An ADR, spec, or constitution is where a decision and its measurement belong, so the over-writing rules invert for those paths. Genre is decided by glob, not by detecting it from the prose. | Yes, as `relaxed: excluded` on those four rules plus `ai-tells-content-shape.over-writing-remainder` and `unasked-for-rationale`. |
| `[**/ai-tells/*.md]` | all styles | The catalog quotes every tell it documents. The index (`ai-tells.md`) quotes nothing and IS gated -- splitting the monolith is what made that possible. | Situational. If the catalog files are deleted (see `migration.md`), this exclusion dies with them. |
| `[**/{SKILL,...,internal-docs}.md]` | 16 rules | This package's own rule text quotes the ban lists it enforces. Every file matched is normative source for the gate. | Yes, verbatim; the same 16 rules exist in the port. |
| `[**/inject-doc-discipline.sh]` | all styles | Quotes the ban list it enforces. | Yes. |
| `[**/{slopvac,write-docs}/README.md]` | `docs-discipline.InternalRefs` | The README documents the docs-discipline rules, which means naming the internal-reference surfaces. | Yes. |
| `[**/vale-styles/README.md]` | 5 rules | The style docs quote every pattern they document. Note: `InternalRefs` is listed TWICE (`.vale.ini:234-235`) -- harmless, but a copy-paste artifact worth dropping. | Yes, minus the duplicate line. |

## Config traps recorded in the same file (`.vale.ini:8-14`, `43-49`), all silent when wrong

| Trap | Effect |
|---|---|
| `\|` alternation in a section header | Matches NOTHING. Use `{a,b}`. |
| `Style.* = <level>` | Accepted and IGNORED. Does not demote a whole style; every rule needs its own line. |
| An extension with no Vale parser and no `[formats]` alias | Lints NOTHING and exits 0. `.tsx` did exactly that. |
| `tsx = html` alias | Errors out. `tsx = md` silently reports zero findings. An alias also defeats Vale's native comment scoping. |
| `releases/latest/download/` for our own styles | 404s: the monorepo has ~125 release-please components, so `latest` resolves to whichever published most recently. Owned styles use a rolling `vale-styles` tag whose assets are clobbered per publish. |

None of these five traps applies to the ported engine: rules are pydantic-validated at load, so a malformed rule fails the run instead of reporting every file clean.
