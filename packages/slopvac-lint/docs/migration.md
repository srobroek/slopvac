# Migration map

## Provenance: which Vale styles are ours

`vale/styles/` is entirely gitignored (`vale/styles/.gitignore:5` = `*/`); only
`.gitignore` and `README.md` are tracked there. The 61 non-`ai-tells` rule files
in that tree are byte-identical to `vale-styles/` on branch
`origin/feat/craft-inclusive-density-styles` (verified by `git ls-tree` diff, 61/61
identical). Those are OURS. `vale/styles/ai-tells/` holds 76 files fetched from
`tbhb/vale-ai-tells` and stays a Vale dependency.

`packages/slopvac-lint/vale-styles/` on the current branch holds only 19 of the 61
-- the 42 in `prose-craft`, `prose-density`, `prose-inclusive`, and the five newer
`prose-agency`/`prose-inflation` rules exist only on the feature branch. **All 61
were converted**, so the port is ahead of the current branch's `vale-styles/`.

## Owned Vale rule -> new rule id

61 rule files in, 61 mapped: 59 converted, 2 kept in Vale only.
`prose-inflation/Uncomparables.yml` produces ONE rule (its `raw` + `tokens` are one
Vale check, not two), which is why 61 files map to 59 rules and not more.

| Vale rule file | New id | Kind | Note |
|---|---|---|---|
| `ai-residue/ChatLeakage.yml` | `ai-residue.chat-leakage` | pattern | |
| `docs-discipline/StatusLanguage.yml` | `docs-discipline.status-language` | pattern | |
| `docs-discipline/HistoryNarration.yml` | `docs-discipline.history-narration` | pattern | |
| `docs-discipline/InternalRefs.yml` | `docs-discipline.internal-refs` | pattern | |
| `prose-agency/FalseAgency.yml` | `prose-agency.false-agency` | pattern | |
| `prose-agency/AgentlessPassive.yml` | `prose-agency.agentless-passive` | pattern | |
| `prose-agency/Anthropomorphism.yml` | `prose-agency.anthropomorphism` | pattern | |
| `prose-agency/NarratorDistance.yml` | `prose-agency.narrator-distance` | pattern | |
| `prose-agency/UnattributedRecommendation.yml` | `prose-agency.unattributed-recommendation` | pattern | |
| `prose-format/NoUnicodeDash.yml` | `prose-format.no-unicode-dash` | pattern | `\x{}` -> literal chars |
| `prose-format/EmojiHeading.yml` | `prose-format.emoji-heading` | pattern | `\x{}` -> `\U` |
| `prose-format/ProseBlock.yml` | `prose-format.prose-block` | metric | `occurrence` -> `paragraph_words` @ 80 |
| `prose-scope/RejectedAlternative.yml` | `prose-scope.rejected-alternative` | pattern | |
| `prose-scope/ImplementationLeak.yml` | `prose-scope.implementation-leak` | pattern | 7 variable-width lookbehinds |
| `prose-scope/UnrequestedReassurance.yml` | `prose-scope.unrequested-reassurance` | pattern | |
| `prose-scope/Epigram.yml` | `prose-scope.epigram` | pattern | backreference `\1` |
| `prose-inflation/SlopLexicon.yml` | `prose-inflation.slop-lexicon` | pattern | |
| `prose-inflation/BusinessJargon.yml` | `prose-inflation.business-jargon` | pattern | |
| `prose-inflation/VagueDeclarative.yml` | `prose-inflation.vague-declarative` | pattern | |
| `prose-inflation/AdditiveHedge.yml` | `prose-inflation.additive-hedge` | pattern | |
| `prose-inflation/HedgeStack.yml` | `prose-inflation.hedge-stack` | pattern | |
| `prose-inflation/Intensifier.yml` | `prose-inflation.intensifier` | pattern | |
| `prose-inflation/Uncomparables.yml` | `prose-inflation.uncomparables` | pattern | `raw`+`tokens` merged into one alternation |
| `prose-inflation/VagueQuantifier.yml` | `prose-inflation.vague-quantifier` | pattern | |
| `prose-inflation/NominalizedVerb.yml` | `prose-inflation.nominalized-verb` | pattern | |
| `prose-inflation/DocumentPreamble.yml` | `prose-inflation.document-preamble` | pattern | |
| `prose-inflation/Apologizing.yml` | `prose-inflation.apologizing` | pattern | |
| `prose-inflation/BorderlineHype.yml` | `prose-inflation.borderline-hype` | pattern | |
| `prose-craft/AcronymPeriods.yml` | `prose-craft.acronym-periods` | pattern | Vale `tokens:` holds a regex |
| `prose-craft/Ambiguity.yml` | `prose-craft.ambiguity` | pattern | |
| `prose-craft/Annotations.yml` | `prose-craft.annotations` | pattern | DUPLICATE, see below |
| `prose-craft/Articles.yml` | `prose-craft.articles` | substitution | 37 swaps |
| `prose-craft/CommandPrompt.yml` | `prose-craft.command-prompt` | pattern | `scope: raw` |
| `prose-craft/ConflictMarkers.yml` | `prose-craft.conflict-markers` | pattern | `scope: raw` |
| `prose-craft/DeadOpener.yml` | `prose-craft.dead-opener` | pattern | 4 lookbehinds |
| `prose-craft/DirectionalRef.yml` | `prose-craft.directional-ref` | substitution | 13 swaps |
| `prose-craft/FirstPersonPlural.yml` | `prose-craft.first-person-plural` | pattern | |
| `prose-craft/FutureTense.yml` | `prose-craft.future-tense` | pattern | |
| `prose-craft/GerundHeading.yml` | `prose-craft.gerund-heading` | pattern | Vale `exceptions:` -> our `allowlist:` |
| `prose-craft/Hyphens.yml` | `prose-craft.hyphens` | pattern | |
| `prose-craft/Latinisms.yml` | `prose-craft.latinisms` | substitution | 10 swaps |
| `prose-craft/LinkText.yml` | `prose-craft.link-text` | pattern | `scope: raw` |
| `prose-craft/Misnomer.yml` | `prose-craft.misnomer` | pattern | |
| `prose-craft/NegativeRequirement.yml` | `prose-craft.negative-requirement` | pattern | |
| `prose-craft/OptionalPlural.yml` | `prose-craft.optional-plural` | pattern | 2 tokens merged |
| `prose-craft/Ordinals.yml` | `prose-craft.ordinals` | pattern | lookbehind |
| `prose-craft/PluralAbbreviation.yml` | `prose-craft.plural-abbreviation` | pattern | **LOSSY** -- see "could not convert" |
| `prose-craft/Politeness.yml` | `prose-craft.politeness` | pattern | |
| `prose-craft/Redundancy.yml` | `prose-craft.redundancy` | pattern | |
| `prose-craft/RelativeDate.yml` | `prose-craft.relative-date` | pattern | |
| `prose-craft/SelfReference.yml` | `prose-craft.self-reference` | pattern | |
| `prose-craft/SentenceLength.yml` | `prose-craft.sentence-length` | metric | `occurrence` -> `sentence_words` @ 34 |
| `prose-craft/Spacing.yml` | `prose-craft.spacing` | pattern | 2 tokens merged; lookbehinds |
| `prose-craft/UnclearAntecedent.yml` | `prose-craft.unclear-antecedent` | pattern | 3 lookbehinds |
| `prose-craft/UndefinedAcronym.yml` | *kept in Vale only* | n/a | `extends: conditional`; see below |
| `prose-craft/Versions.yml` | `prose-craft.versions` | substitution | 6 swaps |
| `prose-craft/Wordiness.yml` | `prose-craft.wordiness` | substitution | 108 swaps |
| `prose-density/PassiveDensity.yml` | *kept in Vale only* | n/a | `extends: script` (Tengo); see below |
| `prose-inclusive/Ableist.yml` | `prose-inclusive.ableist` | substitution | 27 swaps |
| `prose-inclusive/DeviceAssumption.yml` | `prose-inclusive.device-assumption` | substitution | 9 swaps |
| `prose-inclusive/Exclusive.yml` | `prose-inclusive.exclusive` | substitution | 27 swaps; `master`/`slave` negative lookaheads |

## Kept in Vale only

| Rule | Reason |
|---|---|
| `prose-craft/UndefinedAcronym.yml` | `extends: conditional` -- a two-pattern rule where `first` may appear only after `second` has established it. Our schema has no conditional kind and no cross-position state. Its 111-finding measurement and 100-entry exception list are recorded in the rule file and must not be lost; port it when the engine gains a `conditional` kind. |
| `prose-density/PassiveDensity.yml` | `extends: script` (Tengo). The Python engine can compute this natively as `kind: metric`, `metric: passive_sentence_ratio`, `threshold: 35`, `scope: document`, but the 32-measure benchmark table and the p50/p75/p90/p95 distribution (7/13/23/31, max 46) were calibrated against THIS Tengo splitter replicated in Python. Porting without re-running that calibration changes the number silently. NOT converted; flagged as the highest-value follow-up. |

## Duplicated across engines

Vale continues to run as a sub-gate for the upstream `ai-tells` package (76 rules,
13 with dispositions recorded in `exclusions.md`). Duplication is therefore
between OUR engine and UPSTREAM Vale, never our engine against itself.

| Our rule | Upstream Vale rule(s) | Acceptable? |
|---|---|---|
| `ai-tells-structure.contrastive-inversion-frames` | `ContrastiveNegation`, `ContrastiveFormulas` | Deduplicate: disable both upstream rules once ours is calibrated. Upstream's are at error and `ContrastiveNegation` is already `NO` for the package's own normative files. |
| `ai-tells-structure.tricolon-abuse-core` | `VerbTricolon` (demoted to warning), `VerbTricolonDensity` | Deduplicate: keep upstream, drop ours. Upstream carries the density variant we do not have. |
| `ai-tells-structure.summary-closer-frames` | `ConclusionMarkers`, `WrapUpHeadings` | Deduplicate: disable ours; upstream splits body from heading. |
| `ai-tells-register.figurative-verb-verdict-core` | 16 `Figurative*` rules | Deduplicate: disable OURS. Upstream's one-rule-per-verb form gives better messages. Keep our judgement remainder. |
| `ai-tells-register.sycophantic-meta-residue` | `SycophancyMarkers`, `AffirmativeFormulas`, `ClosingPleasantries` | Deduplicate: disable ours. `AffirmativeFormulas` is already trusted at error for source comments. |
| `ai-tells-register.urgency-inflation-core` | `UrgencyInflation` | Deduplicate: disable ours. |
| `ai-tells-register.organic-consequence-core` | `OrganicConsequence` | Deduplicate: disable ours. |
| `ai-tells-structure.vague-attribution-core` | `VagueAttributions` | Deduplicate: disable ours. |
| `ai-tells-content-shape.superficial-ing-analysis` | `ParticipialPadding` | Deduplicate: disable ours. |
| `prose-craft.annotations` | `docs-discipline.status-language` (ours) | ACCEPTABLE. Genre-split by design: `status-language` is off for change comms, where a commit legitimately says "not yet implemented" but never ships "TODO: write this". |
| `prose-format.no-unicode-dash` + `ai-tells-formatting.em-dash-density` | `EmDashUsage` (disabled) | ACCEPTABLE. Presence and density are different checks; upstream is disabled on a measurement. |
| `prose-format.emoji-heading` + `ai-tells-formatting.emoji-list-markers` | none | ACCEPTABLE. Different scopes (`heading` vs `raw` list position). |
| `prose-craft.directional-ref` + `ai-tells-formatting.cross-reference-signposting` | `RestatementMarkers`, `SelfReference` | ACCEPTABLE between ours (position vs reading-order, different fixes). Deduplicate against upstream. |

Net: **9 of our agentic pattern/token rules should be disabled in favour of the
upstream Vale rule** once the port runs alongside Vale. They are emitted anyway
so the catalog is complete and the engine can run standalone.

## Fate of the five prose catalog files

Goal is deletion. Per file:

| File | Redundant after port? | Content with no home in the rule schema |
|---|---|---|
| `references/ai-tells/structure.md` | **YES, delete.** All 26 table rows are emitted as `ai-tells-structure` rules (32 rules: 26 rows, 6 of them split into core+remainder pairs, 2 rows absorbed into a sibling). | None. The four source URLs are carried in `provenance.url`. |
| `references/ai-tells/register.md` | **YES, delete.** All 14 bullets emitted as `ai-tells-register` (19 rules). | The closing model-fingerprint paragraph: Grok overuse of "empirical"/"correlate", Claude's qualifier-reassurance stacking, and the instruction to treat per-model attributions as snapshots. Per-model attribution has no field in `Rule`. ~3 lines. |
| `references/ai-tells/formatting.md` | **YES, delete.** All 12 table rows emitted as `ai-tells-formatting` (10 rules; 2 rows merged as core+shape pairs). | None. |
| `references/ai-tells/content-shape.md` | **YES, delete.** All 14 bullets emitted as `ai-tells-content-shape` (14 rules). | None. The `vaporware-description` rule's `fix` field carries the ordered procedure, and `unasked-for-rationale`'s `judgement_question` carries all three legitimacy tests. |
| `references/ai-tells/counter-signals.md` | **NO, mostly survives.** 7 of its items become document metrics (`counter-signals.md` in this directory), but four items resist. | (1) The register test -- "would a named expert ship this under their own byline?" -- is a whole-review verdict, not a rule. (2) The stylometry caveat: formal and non-native human prose also score low, 2025 research puts unaided human detection at chance, treat detector output as a pointer not proof. (3) "Domain shorthand calibrated to the stated audience". (4) "A concrete anecdote or a mistake admitted with its cost". Items 3 and 4 are covered by existing judgement rules; items 1 and 2 are not, and item 2 is a policy statement about how to USE the output, which no rule field expresses. |
| `references/ai-tells.md` (index) | **NO, survives shrunken.** | The whole "Why structure outranks vocabulary" argument (5 sources: Wikipedia catalog, TechCrunch em-dash suppression, Washington Post 328,744-message analysis, RLHF Book ch. 18, The Register on LinkedIn), the decision procedure ("three or more tells in one passage is a rewrite signal"; "rewrite the fact densely, delete only when the sentence carries no fact"), the `Last researched: 2026-07` date, the decay table, and the "Refreshing this document" procedure. None of this is per-rule. The category `description` fields carry a compressed version of the durability argument. |

**Recommendation:** delete `structure.md`, `register.md`, `formatting.md`,
`content-shape.md` (4 files, 216 lines). Keep `ai-tells.md` reduced to the
durability argument plus the refresh procedure and the three-tell threshold, and
fold `counter-signals.md`'s surviving four items into it. One prose file instead
of six.

## Reconciliation

| Bucket | Count |
|---|---|
| Owned Vale rule files found (`vale/styles/` minus `ai-tells/`) | 61 |
| Converted to rule YAML | 59 |
| Kept in Vale only, with reason | 2 (`prose-craft/UndefinedAcronym`, `prose-density/PassiveDensity`) |
| Catalog entries found (`references/ai-tells/*.md`, excluding counter-signals) | 66 rows/bullets |
| Emitted as `ai-tells-*` rules | 75 |
| Tells split into pattern/tokens + judgement pairs | **16** |
| Catalog rows absorbed into a sibling rule rather than getting their own | 7 |
| Total rules written | **134** |

Rule counts per emitted category: `ai-residue` 1, `docs-discipline` 3,
`prose-agency` 5, `prose-format` 3, `prose-scope` 4, `prose-inflation` 12,
`prose-craft` 28, `prose-inclusive` 3, `ai-tells-structure` 32,
`ai-tells-register` 19, `ai-tells-formatting` 10, `ai-tells-content-shape` 14.

## Go RE2 -> Python `regex` divergences

Recorded in each rule's `provenance.note`. Go RE2 supports neither backreferences
nor lookbehind, so these branches cannot have been matching under a pure RE2
engine and become newly live in the port -- each needs a corpus run before it is
enforced:

| Rule | Feature | Effect |
|---|---|---|
| `prose-scope.epigram` | backreference `\1` | First alternative (same-verb parallel pair) newly live. |
| `prose-scope.implementation-leak` | 7 variable-width lookbehinds | The `timeout of`/`budget of`/`<dd>` exemptions newly enforced; port may be STRICTER than Vale. |
| `prose-craft.dead-opener` | 4 lookbehinds | Clause-initial anchoring newly live. |
| `prose-craft.unclear-antecedent` | 3 lookbehinds | Same. |
| `prose-craft.spacing` | `(?<!\d)` | Version/decimal exemption newly enforced. |
| `prose-craft.ordinals` | `(?<!\w)` | Same. |
| `ai-tells-formatting.italicised-copula` | 2 lookbehinds | New rule; no Vale original. |
| `prose-inclusive.exclusive` | negative lookaheads on `master`/`slave` | RE2 lacks lookahead too; the `master branch`/`master boot record` exemptions may be newly enforced. |
| `prose-format.no-unicode-dash`, `prose-format.emoji-heading`, `ai-tells-formatting.emoji-list-markers` | `\x{NNNN}` syntax | Rewritten as literal characters / `\U0001NNNN`. Behaviour identical. |
| `ai-residue.chat-leakage` | `\x{3010}` CJK bracket range | Rewritten as literal `【`, `†`, `】`. Behaviour identical. |
