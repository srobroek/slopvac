# Regex and token-rule audit

## Summary

- Loaded all `kind: pattern` and `kind: tokens` rules from the requested rule set: 99 rules (82 patterns, 17 token lists) across the 11 present YAML files; `prose-promotion` is YAML document 2 of `ai-tells-figurative.yml`, not a standalone file.
- Compiled every rule with Python `re` and its `ignore_case` setting, checked every loader example, and scanned all raw lines in the human and ai-existing corpora. One rule does not compile: `prose-craft.dead-opener`.
- The three highest-value fixes are the dead-opener compile failure, the sentence-boundary false negative in contrastive inversion, and the broad false-positive families in tricolon/false-agency/token rules.
- No compilable pattern exceeded 0.5 s on a 20 kB worst-case `a` string; complete counts and probe results are in `local://audit/RegexAiTells-probes.json`.

## Method and measurement caveats

Patterns were compiled with `re.IGNORECASE` exactly when `ignore_case: true`. Token rules were compiled as the engine does: longest-first escaped alternatives bounded by `(?<![\\w-])` and `(?![\\w-])`. Corpus counts below are raw-line match occurrences; the linter's prose scope masks inline code and fenced code, while `raw` intentionally does not. I manually inspected up to five distinct human matched lines per rule (all lines where fewer than five existed). The FP fractions below are therefore observed sample fractions, not prevalence estimates. A match is marked FP when the quoted sentence is ordinary, technically useful prose rather than the defect the rule claims.

The current baseline sample JSON is capped at five examples per rule. Raw probes are consequently the source for the full H/A counts in this report and sidecar.

## Findings

### F1: `prose-craft.dead-opener` cannot compile

- surface: `packages/slopvac-lint/src/slopvac/rules/prose-craft.yml:230` (`prose-craft.dead-opener`)
- kind: code-bug
- evidence: Python `re.compile` raises `re.error: global flags not at the start of the expression at position 109`. The pattern has `(?m)` before the first alternative and another `(?m)` before the second. The examples are otherwise sound: `There is a flag that controls this.` and `It is important to note that the loader retries.` are the two bad probes; both good probes are silent only after the compile fix. The baseline sample contains real matches such as `ripgrep-guide-2021.md:546`, `There are`, so this is not an unused rule.
- proposal: Move one `(?m)` to the beginning and remove the second inline flag. Concrete replacement:
  ```regex
  (?m)(?:^|(?<=[.!?;]\s)|(?<=^[-*]\s)|(?<=^>\s))\s*[Tt]here\s+(?:is|are|was|were|will be|has been|have been)\b|(?:^|(?<=[.!?;]\s))\s*[Ii]t\s+(?:is|was)\s+(?:important|worth|essential|critical|necessary|useful|helpful|possible|interesting|notable|clear|obvious|apparent|recommended|advisable)\s+(?:to\s+)?(?:note|mention|remember|point out|observe|understand|see|say)?\b
  ```
- evidence for proposal: replacement compiled; bad examples fired `2/2`, good examples stayed silent `2/2`. Raw human matches are `0` before compilation and `22` after; raw ai-existing matches are `0` before and `2` after. The pre-existing baseline sample had five human findings, confirming the intended rule path.
- expected effect: correctness; restores the rule rather than silently failing/aborting the lexical pass.
- confidence: high

### F2: `contrastive-inversion-frames` misses the canonical two-sentence form

- surface: `ai-tells-structure.contrastive-inversion-frames` (`ai-tells-agentic.yml:35`)
- kind: fn-gap
- evidence: the shipped regex contains `[^.!?]{1,80}`. Its own bad example `It's not a linter, it's a review partner.` fires, but `It's not a linter. It's a review partner.` does not because the negated class cannot cross the full stop. The latter is the same tell split across two sentences.
- proposal: replace only the bounded middle with `[^\n]{1,120}?`:
  ```regex
  \b(?:it's|it is|this isn't|this is not|that's not|it's not|it isn't)\s+(?:not|less about)\b[^\n]{1,120}?\b(?:it's|it is|and more about|but rather)\b
  ```
- evidence for proposal: two bad examples fired `2/2`, two good examples stayed silent `2/2`; human raw matches remained `0` and ai-existing remained `1` (the added form is now reachable). A direct probe of `It's not a linter. It's a review partner.` fired only with the proposed regex.
- expected effect: FN↓; no observed human increase.
- confidence: high

### F3: `fake-specificity` mistakes a version suffix for a count

- surface: `ai-tells-content-shape.fake-specificity` (`ai-tells-agentic.yml:1770`)
- kind: fp-risk
- evidence: `black-readme-2021.md:42` contains `_Black_ ... It requires Python 3.6.2+ to`; the current branch `\b\d+\+\s+(?:different\s+)?\w+` reports `2+ to`. This is a version suffix followed by an infinitive, not fake specificity. The other human match, `ripgrep-guide-2021.md:345`, is the ordinary phrase `a broad range of file extensions`.
- proposal: require a non-stop-word countable token of at least three characters after `N+`:
  ```regex
  \b(?:over|more than|upwards of|nearly|almost)\s+\d+\+|\b\d+\+\s+(?:different\s+)?(?!to\b|of\b|and\b|or\b|the\b|a\b|an\b)\w{3,}|\ba wide range of\b|\ba broad range of\b|\ba host of\b
  ```
- evidence for proposal: both bad examples fired `2/2`, both good examples stayed silent `2/2`; human raw matches fell `2 -> 1`, ai-existing stayed `1 -> 1`. The proposed probe is silent on `3.6.2+ to` and still fires on `over 100+ integrations`.
- expected effect: FP↓, with the intended fake-specificity examples preserved.
- confidence: high

### F4: `tricolon-abuse-core` is a generic technical-list detector, not an AI-tell detector

- surface: `ai-tells-structure.tricolon-abuse-core` (`ai-tells-agentic.yml:130-150`)
- kind: fp-risk
- evidence: all six observed human matches are normal enumerations: `dogfood-readme-human.md:29`, `token, regex, and substitution matching`; `fzf-readme-2021.md:612`, `size, position, and border of the preview window using`; and `redis-readme-2021.md:12`, `durability, clustering, and high availability`. The other three are equally concrete lists (`Assistant, Zulip, and many`; `Polish, refine, and re-send`; `code, tracebacks, and more`). The raw count is H=6, A=8; the manually observed FP sample is 6/6.
- proposal: Decommission the mechanical core from the normal lexical ruleset and retain `ai-tells-structure.tricolon-abuse-remainder` as the judgement rule. If a mechanical prefilter is retained, make it advisory and require the judgement pass; no regex can distinguish `fast, reliable, and secure` from a technical three-item list without sentence-level semantics.
- expected effect: FP↓ substantially; FN↑ only for a judgement case that was already represented by the remainder.
- confidence: high

### F5: `prose-agency.false-agency` treats reader-facing affordances as deleted-agent claims

- surface: `prose-agency.false-agency` (`prose-agency.yml:10`, long final alternation)
- kind: fp-risk
- evidence: raw H=11, A=0. Human examples include `annotated-types-readme-2022.md:69`, ``Interval(gt, ge, lt, le) allows you to specify an upper and lower bound with a single``; `dogfood-readme-human.md:225`, `one entry per sense is what lets you say so`; and `git-contributing-2021.md:415`, `most likely to be knowledgeable enough to help you`. These are reader affordances or an explicit explanation of what the API lets a reader do, not an abstraction pretending to act. The manually sampled false-positive fraction is 5/5; the baseline samples also contain `allows you`, `let you`, and `help you`.
- proposal: In the reader-affordance branch, remove `lets?` and `helps?`; use this concrete replacement fragment:
  ```regex
  \b(?:allows?|enables?|permits?|empowers?)\s+(?:you|user(?:s)?)\s+(?:to|the ability to)\b
  ```
  Keep the subject-anchored complaint/data/culture branches unchanged. In the full existing regex, this is the replacement for `(?:allows?|enables?|lets?|permits?|empowers?|helps?)`.
- evidence for proposal: all three rule bad examples fired `3/3`, all three good examples stayed silent `3/3`; human raw matches fell `11 -> 2`, ai-existing stayed `0 -> 0`. The two remaining human hits are the intended `allows/enables` forms and should be adjudicated as agency rather than silently allowlisted.
- expected effect: FP↓.
- confidence: high

### F6: `emoji-list-markers` has an optional list marker and catches emoji showcases

- surface: `ai-tells-formatting.emoji-list-markers` (`ai-tells-agentic.yml:1678`)
- kind: fp-risk
- evidence: `rich-readme-2020.md:194` is `😃 🧛 💩 👍 🦝`, a showcase line, not a list item. The current pattern has `(?:[-*+][ \t]+)?`, so it fires without a marker. Raw H=1, A=11.
- proposal: require the Markdown marker:
  ```regex
  (?m)^[ \t]*[-*+][ \t]+[\U0001F300-\U0001FAFF☀-➿⬀-⯿]️?[ \t]
  ```
- evidence for proposal: the bad example `- 🚀 Install the plugin` fired `1/1`, the good example `- Install the plugin` stayed silent `1/1`; H fell `1 -> 0`, A fell `11 -> 10`.
- expected effect: FP↓.
- confidence: high

### F7: `summary-closer-frames` catches an ordinary verb phrase mid-sentence

- surface: `ai-tells-structure.summary-closer-frames` (`ai-tells-agentic.yml:413`)
- kind: fp-risk
- evidence: `ripgrep-guide-2021.md:623` says `topic, but we can try to summarize its relevancy to ripgrep:`. The token `to summarize` is not a summary closer there. H=1 and A=2 in the raw scan; the human match is a 1/1 observed FP.
- proposal: This needs a pattern rather than a bare token list, anchored to line/sentence start:
  ```regex
  (?im)(?:^|(?<=[.!?]\s))(?:in conclusion|to wrap up|to wrap things up|to sum up|in summary|to summarize|to summarise|wrapping up|the bottom line is|all in all|at the end of the day)\b
  ```
- evidence for proposal: bad `In conclusion, the gate reads one config file.` fired `1/1`, good `The gate reads one config file.` stayed silent `1/1`; H fell `1 -> 0`, A fell `2 -> 0`.
- expected effect: FP↓ and a clearer definition of “closer”.
- confidence: high

### F8: `rhetorical-question-transition` makes the transition optional

- surface: `ai-tells-structure.rhetorical-question-transition` (`ai-tells-agentic.yml:301`)
- kind: fp-risk
- evidence: H=3, A=1. Human matches are headings or ordinary document questions: `redis-readme-2021.md:3`, `What is Redis?`; `ripgrep-readme-2021.md:87`, `### Why should I use ripgrep?`; and `ripgrep-readme-2021.md:128`, `### Why shouldn't I use ripgrep?`. The current `(?:So|But|Now|And)?` allows all of them; observed FP fraction 3/3.
- proposal: Make the transition cue mandatory:
  ```regex
  (?m)^\s*(?:#{1,6}\s*)?(?:So|But|Now|And)\s+(?:why|what|how|who)\b[^.!?\n]{0,60}\?\s*$
  ```
- evidence for proposal: bad `So why does this matter?` fired `1/1`, good `A false status claim ships a document that lies.` stayed silent `1/1`; H fell `3 -> 0`, A fell `1 -> 0`.
- expected effect: FP↓; this intentionally leaves bare interrogative headings to normal documentation.
- confidence: high

### F9: `optional-plural` treats units and URL fragments as parenthetical plurals

- surface: `prose-craft.optional-plural` (`prose-craft.yml:579`)
- kind: fp-risk
- evidence: raw H=4: `annotated-types-readme-2022.md:132` has `m/s` inside ``Unit("m/s")``; `black-readme-2021.md:154` has `com/s` in a URL; `git-contributing-2021.md:53` has the actual style defect `change(s)`; and `git-contributing-2021.md:204` has `license(s)`. The rule's `/s` alternative is responsible for the first two; observed FP fraction is 2/4.
- proposal: remove the slash branch and keep the parenthetical form:
  ```regex
  \b\w+\((?:s|es)\)
  ```
- evidence for proposal: bad `Select the file(s).` fired `1/1`, good `Select the files.` stayed silent `1/1`; H fell `4 -> 2`, A fell `2 -> 2` (the AI matches are parenthetical forms).
- expected effect: FP↓.
- confidence: high

### F10: unsupported-evaluative token list contains ordinary technical adjectives

- surface: `orwell.unsupported-evaluative` (`orwell.yml:100-117`), overlapping `prose-inflation.slop-lexicon`
- kind: fp-risk
- evidence: H=5, A=8. Human matches are `black-readme-2021.md:72`, `Black has a comprehensive test suite`; `fzf-readme-2021.md:17`, `The most comprehensive feature set`; `requests-readme-2020.md:40`, `building robust and reliable HTTP-speaking applications`; `ripgrep-guide-2021.md:874`, heading `A more robust preprocessor`; and `ripgrep-guide-2021.md:890`, `make our preprocessor script a bit more robust`. The manually observed FP fraction is 5/5. `robust` is specifically a common technical term, and `comprehensive test suite` is backed by the noun it modifies.
- proposal: Keep the high-signal tokens but add exact contextual allowlist entries (the engine already supports phrase allowlists): `robust preprocessor`, `robust and reliable`, `comprehensive test suite`, and `comprehensive feature set`. Alternatively decommission this duplicate and leave the more targeted `prose-inflation.slop-lexicon`; do not remove the own bad example without replacing it with an unambiguous token.
- evidence for proposal: the unchanged regex still fires `A robust parser with comprehensive coverage.` and stays silent on `The parser survives 10^6 malformed inputs; coverage is 94%` (`1/1` bad, `1/1` good). The proposed phrase allowlist removes all five observed human contexts while retaining that synthetic bad example; no regex backtracking change is needed.
- expected effect: FP↓ while retaining true hyperbole.
- confidence: high

### F11: human-corpus review of all other matched rules

The following table records the required manual review. `FP sample` is the number judged ordinary/non-defective in the inspected sample; code-only hits are explicitly discounted where the engine's prose mask applies. The quotes are the observed evidence (source line included).

| rule | raw H/A | FP sample | inspected evidence |
|---|---:|---:|---|
| `ai-tells-content-shape.superficial-ing-analysis` | 2/0 | 2/2 | `git-contributing-2021.md:337` “attachment as plain text, making it impossible to comment on”; `ripgrep-readme-2021.md:104` “highlighting matches with” — ordinary participial/result clauses. |
| `ai-tells-formatting.curly-quotes` | 3/0 | 3/3 | `black-readme-2021.md:17` ““Any color you like.””; `requests-readme-2020.md:20` “There’s no need” — a quotation and a normal contraction, not AI residue. |
| `ai-tells-register.corporate-analytic-filler-core` | 2/2 | 1/2 | `redis-readme-2021.md:240` “discussion at a high level without digging into the details”; `ripgrep-guide-2021.md:727` “At a high level, ripgrep operates...” — the latter is a useful scope qualifier. |
| `ai-tells-structure.cataphoric-lead-in-core` | 4/6 | 4/4 | `annotated-types-readme-2022.md:75` “interpreted in two ways”; `ripgrep-guide-2021.md:180` “in these three categories” — valid enumeration lead-ins. |
| `ai-tells-structure.fragment-question-pivot` | 1/0 | 1/1 | `black-readme-2021.md:142` “Are we missing anyone? Let us know.” — an ordinary feedback request. |
| `ai-tells-structure.staccato-negative-parallel-frames` | 1/0 | 1/1 | `black-readme-2021.md:105` “not many users anyway. Not many edge cases were reported.” — two complete factual sentences, not fragments. |
| `ai-tells-structure.tricolon-abuse-core` | 6/8 | 6/6 | `dogfood-readme-human.md:29` “token, regex, and substitution matching”; `redis-readme-2021.md:12` “durability, clustering, and high availability” — handled in F4. |
| `ai-tells-structure.summary-closer-frames` | 1/2 | 1/1 | `ripgrep-guide-2021.md:623` “we can try to summarize” — handled in F7. |
| `orwell.unsupported-evaluative` | 5/8 | 5/5 | `black-readme-2021.md:72` “a comprehensive test suite”; `ripgrep-guide-2021.md:874` “A more robust preprocessor” — handled in F10. |
| `prose-agency.anthropomorphism` | 1/2 | 1/1 | `ripgrep-guide-2021.md:587` “argument parser knows to treat the single argument” — standard parser documentation phrasing. |
| `prose-agency.false-agency` | 11/0 | 5/5 sample | `annotated-types-readme-2022.md:69` “allows you to specify”; `git-contributing-2021.md:415` “knowledgeable enough to help you” — handled in F5. |
| `prose-agency.unattributed-recommendation` | 3/0 | 1/3 | `fzf-readme-2021.md:522` “it’s not recommended that you add it”; `redis-readme-2021.md:432` “it is recommended to” — passive recommendation, but a legitimate docs convention. |
| `prose-craft.ambiguity` | 2/0 | 0/2 | `annotated-types-readme-2022.md:51` “inclusive and/or exclusive bounds”; `git-contributing-2021.md:470` “and/or” — genuine ambiguity. |
| `prose-craft.command-prompt` | 80/0 | 0/5 style defects | `requests-readme-2020.md:33` “$ python -m pip install requests”; `ripgrep-guide-2021.md:40` “$ curl -LO ...” — intentional prompts, but see F12. |
| `prose-craft.first-person-plural` | 107/84 | 5/5 | `annotated-types-readme-2022.md:56` “We suggest that implementors”; `annotated-types-readme-2022.md:81` “We encourage users” — intentional author/project voice. |
| `prose-craft.future-tense` | 102/30 | 4/5 | `black-readme-2021.md:21` “You will save time”; `black-readme-2021.md:80` “Black will check” — promises/instructions, not necessarily stale-description errors. |
| `prose-craft.gerund-heading` | 12/1 | 2/5 | `black-readme-2021.md:180` “Using the badge”; `redis-readme-2021.md:104` “Selecting a non-default memory allocator” — task headings are genre-dependent. |
| `prose-craft.hyphens` | 2/3 | 2/2 raw, 0/0 engine | `ripgrep-guide-2021.md:482` and `:486` both “only-matching” inside inline code; the prose mask discounts both. |
| `prose-craft.link-text` | 5/1 | 5/5 | `black-readme-2021.md:34` “[Read the documentation on ReadTheDocs!]”; `fzf-readme-2021.md:345` “[the wiki page]” — these labels identify the destination. |
| `prose-craft.negative-requirement` | 1/0 | 1/1 | `ripgrep-guide-2021.md:431` “don’t include files without an extension” — a useful condition, not empty negativity. |
| `prose-craft.optional-plural` | 4/2 | 2/4 | `git-contributing-2021.md:53` “change(s)” and `:204` “license(s)” are defects; `annotated-types-readme-2022.md:132` “m/s” and `black-readme-2021.md:154` “com/s” are not — handled in F9. |
| `prose-craft.politeness` | 26/8 | 5/5 | `annotated-types-readme-2022.md:135` “Please note that”; `black-readme-2021.md:98` “Please refer to this document” — normal docs politeness. |
| `prose-craft.relative-date` | 7/2 | 4/5 | `black-readme-2021.md:215` “long nowadays”; `requests-readme-2020.md:20` “but nowadays” — natural prose, although stale dates can be a real maintenance defect. |
| `prose-craft.self-reference` | 6/0 | 5/5 | `ripgrep-guide-2021.md:119` “In the previous section”; `ripgrep-guide-2021.md:262` “This section covers glob” — useful navigation. |
| `prose-craft.spacing` | 56/0 | 3/5 raw, 0/2 engine | `git-contributing-2021.md:201` “exception.  For example”; `git-contributing-2021.md:205` “exception.  We encourage” are real double-space defects; `annotated-types-readme-2022.md:8` “g.An” and `:163` “t.Un” are inline-code identifiers and masked. |
| `prose-craft.unclear-antecedent` | 39/8 | 4/5 | `annotated-types-readme-2022.md:136` “That is left entirely to downstream libraries”; `black-readme-2021.md:74` “This is made explicit” — the antecedent is present in context. |
| `prose-discipline.bidirectional-hedge` | 2/3 | 2/2 | `annotated-types-readme-2022.md:251` “intend to not be prescriptive ... but ... one might”; `rich-readme-2020.md:175` “could be used ... but is also” — precise alternatives, not stacked uncertainty. |
| `prose-discipline.frozen-verb` | 3/1 | 3/3 | `annotated-types-readme-2022.md:219` “provide a convenience wrapper”; `git-contributing-2021.md:53` “Give an explanation” — light verbs with concrete objects. |
| `prose-discipline.hedged-hedge` | 3/1 | 3/3 | `annotated-types-readme-2022.md:16` “In some cases”; `ripgrep-readme-2021.md:89` “can replace many use cases” — ordinary scope/possibility qualifiers. |
| `prose-discipline.marketing-lexicon` | 1/3 | 1/1 | `rich-readme-2020.md:62` “To effortlessly add rich output” — promotional, but an intentional quick-start register choice. |
| `prose-discipline.term-rotation-signal` | 1/23 | 1/1 | `annotated-types-readme-2022.md:259` “for end-users” — one token alone proves no rotation; this should be document-level or judgement-only. |
| `prose-format.emoji-heading` | 5/18 | 0/0 engine | All five raw occurrences are one body line, `rich-readme-2020.md:194` “😃 🧛 💩 👍 🦝”; heading scope means none is an engine finding. |
| `prose-format.no-unicode-dash` | 6/67 | 0/5 style defects | `requests-readme-2020.md:20` “data — but nowadays”; `requests-readme-2020.md:38` “Best–Practices” — valid under the house ASCII-dash ban, so low H/A is not FP evidence. |
| `prose-inflation.apologizing` | 1/0 | 1/1 | `ripgrep-guide-2021.md:112` “beyond the scope of this guide” — an accurate scope boundary. |
| `prose-inflation.borderline-hype` | 17/10 | 4/5 | `annotated-types-readme-2022.md:198` “simply negates”; `git-contributing-2021.md:47` “really trivial” — ordinary adverbs/adjectives in context. |
| `prose-inflation.document-preamble` | 1/3 | 1/1 raw, 0/0 engine | `fzf-readme-2021.md:273` quote “described later in this document”; quotation exception/prose masking should prevent this engine finding. |
| `prose-inflation.hedge-stack` | 1/4 | 1/1 | `git-contributing-2021.md:367` “contacts command can help to” — a single ordinary modal plus verb, not a stacked hedge. |
| `prose-inflation.intensifier` | 18/3 | 4/5 | `annotated-types-readme-2022.md:82` “very large or non-integer numbers”; `redis-readme-2021.md:454` “very familiar with the rest” — technical scope/emphasis. |
| `prose-inflation.nominalized-verb` | 2/1 | 2/2 | `black-readme-2021.md:201` “take a look”; `redis-readme-2021.md:392` “is responsible for calling” — conventional technical wording. |
| `prose-inflation.slop-lexicon` | 9/16 | 5/5 | `black-readme-2021.md:72` “comprehensive test suite”; `requests-readme-2020.md:3` “a simple, yet elegant HTTP library” — technical/marketing overlap; robust cases handled with F10's allowlist. |
| `prose-inflation.vague-quantifier` | 29/8 | 4/5 | `git-contributing-2021.md:30` “several topics”; `git-contributing-2021.md:449` “various proposed changes” — frequent, often valid quantification. Already advisory at normal. |
| `prose-promotion.promotional-adjective-noun` | 1/0 | 1/1 | `rich-readme-2020.md:119` “sophisticated output with minimal effort” — promotional but valid product description; use judgement/genre tier. |
| `prose-scope.rejected-alternative` | 1/0 | 1/1 | `dogfood-readme-human.md:449` heading “What this deliberately does not do” — useful scope declaration, not a defended implementation alternative. |
| `prose-scope.unrequested-reassurance` | 5/4 | 4/5 | `black-readme-2021.md:156` “you don't have to be”; `rich-readme-2020.md:32` “out of the box” — user-facing assurances, though appropriate targets for consumer-doc review. |

### F12: requested low-ratio audit and disposition

The baseline's explicitly named low-ratio set mixes lexical rules with substitutions/metrics outside this assignment. The baseline table also gives `prose-craft.first-person-plural` an A:H ratio of 1.57 and `prose-craft.future-tense` 0.62, so those two are not mathematically `<0.5`; they are included here because the assignment names them.

- `prose-craft.command-prompt`: raw H=80/A=0; all 80 human matches are prompt-bearing shell examples (`$ markdown-it`, `$ curl`, `$ rg`) and therefore intentional code presentation. This is a genre/style rule, not an AI discriminator. **Disposition: decommission from the normal slop profile or make normal advisory; do not broaden the regex.**
- `prose-craft.spacing`: raw H=56/A=0; 50 are genuine double-space/zero-space sentence-boundary findings, six are inline-code identifiers (`g.An`, `t.Un`, `u.Un`) discounted by the prose mask. **Disposition: keep enforced for real prose; no tier change.**
- `prose-craft.latinisms` (substitution, outside target): baseline samples are ordinary `i.e.`, `N.B.`, `etc.`, and `via`; AI has four sampled hits. **Disposition: outside this pattern/tokens pass; if the normal profile wants a low-FP house rule, make it advisory rather than altering the replacements.**
- `orwell.compound-preposition` (substitution, outside target): baseline H samples include `In order to` and `prior to`, with A=0. They are understandable but common in correct technical prose. **Disposition: normal advisory; retain enforced strict.**
- `prose-inclusive.exclusive` (substitution, outside target): baseline H=5 sampled old terms (`blacklist`/`whitelist`), A=0. These are precisely the legacy terms the accessibility rule is intended to migrate; the low AI ratio reflects corpus vocabulary, not a regex defect. **Disposition: keep warning/enforced as an accessibility rule; do not demote for AI separation.**
- `prose-agency.false-agency`: H=11/A=0, mostly `allows/lets/helps you` reader affordances; **disposition and replacement are F5.**
- `prose-craft.wordiness` (substitution, outside target): baseline H=5 sampled `in order to` and `a number of`; A=3. Some are stylistic rather than defects. **Disposition: normal advisory; keep replacements and strict enforcement.**
- `prose-craft.dead-opener`: baseline H=5 sampled `There are`; current Python `re` compile failure is F1. **Disposition: apply F1 first; no tier change until the rule actually runs.**
- `prose-inflation.intensifier`: raw H=18/A=3; examples include `very large or non-integer numbers` and `very familiar with the rest`. **Disposition: normal advisory (strict may stay enforced); a regex cannot infer whether the degree is measurable.**
- `prose-format.prose-block` (metric, outside target): baseline H=5/A=2 long paragraphs. It is a format/scanability rule, not a model-origin classifier. **Disposition: keep normal warning/advisory by document genre; no regex change.**
- `prose-craft.future-tense`: raw H=102/A=30; human examples include `You will save time`, `Black will check`, and `will probably be wonky`. Some are promises or future obligations, for which present tense is not a valid rewrite. **Disposition: normal advisory; strict enforced, relaxed excluded.**
- `prose-craft.first-person-plural`: raw H=107/A=84; examples include `We suggest that implementors` and `We encourage users`. This is intentional project voice in many human READMEs, not an AI tell. **Disposition: normal advisory; retain strict enforcement only where the selected genre bans vendor voice.**
- `ai-tells-structure.emphasis-paragraph-metric` (metric, outside target): baseline H=5/A=5 sampled, so it is not an A:H `<0.5` rule and needs no regex treatment. It measures paragraph shape; keep as a judgement-adjacent metric.

## Decommission candidates

1. `ai-tells-structure.tricolon-abuse-core`: generic list detector (H=6/A=8; 6/6 human sample FPs). Retain its judgement remainder.
2. `prose-craft.command-prompt`: H=80/A=0, every human hit is an intentional shell prompt. Remove from normal slop scoring or make advisory.
3. `orwell.unsupported-evaluative`: consider removing the duplicate if `prose-inflation.slop-lexicon` owns the lexical ban; otherwise keep it with the exact technical allowlist in F10.
4. `prose-discipline.term-rotation-signal`: H=1/A=23, but one isolated `end-users` token cannot establish rotation. Move candidate detection to document-level judgement rather than decommissioning the judgement rule.

## Checked and fine

- `ai-residue.chat-leakage`: zero human and ai-existing raw matches; all examples compile and separate.
- `ai-tells-content-shape.fabricated-citations-core`: zero human/AI matches; URL tracking markers remain appropriately narrow.
- Figurative family (`figurative-sits`, `runs`, `falls`, `draws`, `casts`, `strikes`, `wins`, `lends`, `rides`, `loud`, `resonate-overuse`, `colloquial-assessment`): no human matches; examples passed, with no backtracking outlier.
- Register token families (`faux-candor`, `intensifier-tics`, `sycophantic-meta-residue`, `figurative-verb-verdict`, `urgency-inflation`, `organic-consequence`, `anthropomorphised-justification`): no human matches; AI-only matches are consistent with their intended residue/tell surface.
- Formatting `title-case-heading`, `italicised-copula`, and cross-reference signposting: no human matches; heading/markup scopes are narrow.
- `orwell.not-un`, `orwell.stale-figure`, and `prose-scope.epigram`: no human matches in this corpus; example contracts passed.
- `prose-craft.acronym-periods`, annotations, conflict markers, misnomer, plural-abbreviation, and relative-date edge branches: no observed broad catastrophic behavior; code spans were discounted where prose scope applies.
- Every proposal above has a Python probe result in the sidecar; all proposed bad/good example checks are recorded as counts, not inferred from source text.
