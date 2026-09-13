# Summary
Checked all 41 non-judgement `pattern`, `tokens`, `substitution`, `metric`, and `structure` rules in the nine `ste-*.yml` files plus `docs-discipline.yml`, their lexical/metric execution paths, and all target human/AI baseline counts. Every lexical rule compiled and every own `bad`/`good` example passed self-verification.
The three highest-impact defects are passive regex suffix overreach, auxiliary-stacking duplication of ordinary passive capability prose, and lexical rules ignoring `text_type` (especially `condition-after-command`).
The parser also splits every colon as a sentence boundary and counts `(1)` as a word, while the noun-stack heuristic flags readable headings and modifiers.
Baseline gate separation is poor: passive voice is 239 human vs 48 AI findings; auxiliary stacking 71 vs 6; descriptive long sentences 133 vs 57; condition-after-command 76 vs 33; multiword noun stacks 70 vs 36; omitted words/contractions 122 vs 93.

## Findings

### F1: Passive regex treats ordinary `-en` words as participles
- surface: `ste-verbs.passive-voice` (`packages/slopvac-lint/src/slopvac/rules/ste-verbs.yml`); suffix branch `\\w{3,}(?:ed|en|wn)`
- kind: fp-risk
- evidence: Human `annotated-types-readme-2022.md:122` says “allow a specific timezone, though we note that this is often a symptom of fragile design.” The finding is `Passive voice "is often"`; `often` is an adverb, not a passive participle. Human `redis-readme-2021.md:318` says “are described as `robj` structures” (real passive), showing the same rule mixes valid and invalid hits. Actual CLI probe `The option is often useful.` => 1 `ste-verbs.passive-voice` finding (`is often`); control `The controller enables the option.` => 0. Human baseline: 239/21,208 words (11.27/1k); AI-existing: 48/9,865 (4.87/1k), ratio 0.43.
- proposal: Replace the open suffix branch with a closed participle lexicon or a POS-aware check; at minimum exclude common adverbs/adjectives (`often`, `open`, etc.) and retain explicit `... by ...` matches. Add a must-not-fire probe for `is often`.
- expected effect: FP↓ on human corpus; also reduces the misleading human/AI gap.
- confidence: high

### F2: `auxiliary-stacking` duplicates ordinary passive capability prose
- surface: `ste-verbs.auxiliary-stacking`
- kind: duplicate
- evidence: Human samples include “This package provides metadata objects which can be used to represent common” (`annotated-types-readme-2022.md:13`), “Further information can be found in our docs” (`black-readme-2021.md:65`), “Pre-built binaries for Windows can be downloaded” (`fzf-readme-2021.md:135`), “might be intended” (`black-readme-2021.md:98`), and “can be found on [the wiki page]” (`fzf-readme-2021.md:345`). These are standard capability/reference statements, not a distinct defect from passive voice. Actual CLI probe `The service can be enabled by setting the flag.` => one auxiliary-stacking finding and one passive finding; active control `You can enable the service by setting the flag.` => zero auxiliary-stacking findings. Human baseline 71 (3.35/1k) vs AI 6 (0.61/1k), ratio 0.19.
- proposal: Delete this rule and rely on passive-voice, or narrow it to genuinely triple-auxiliary chains (`will have been`, `has to be`) that passive-voice does not already report. Do not retain a second warning for `can|may|must be + participle`.
- expected effect: FP↓ and duplicate-warning noise↓ on human corpus.
- confidence: high

### F3: Lexical execution ignores declared `text_type`, overfiring condition rules on descriptions
- surface: `ste-procedural.condition-after-command`; `packages/slopvac-lint/src/slopvac/engine.py:667-670` (`_run_lexical` iterates lines but never checks `rule.text_type`)
- kind: code-bug
- evidence: The rule declares `scope: sentence`, `text_type: procedural`, but the actual CLI probe `The command runs if the queue is empty.` parses as `descriptive` and still reports `condition-after-command`; `Restart the worker if the queue is empty.` parses as `procedural` and reports as intended. Human samples demonstrate the false-positive class: “Formatting becomes transparent after a while and you can focus on the content instead.” (`black-readme-2021.md:24`), “You can download fzf executable alone if you don't need the extra” (`fzf-readme-2021.md:82`), and “Fuzzy completion for files and directories can be triggered if the word before” (`fzf-readme-2021.md:352`) are descriptions/capability statements, not direct commands. Baseline 76 human (3.58/1k) vs 33 AI (3.35/1k), ratio 0.93.
- proposal: For `scope: sentence`, run lexical patterns against `Document.sentences` and skip sentences whose `text_type` differs; preserve line/column mapping. Alternatively make the Vale compiler emit the same text-type guard. Add descriptive and procedural controls for every procedural lexical rule (`condition-after-command`, `multiple-instructions-per-sentence`, `instruction-not-imperative`).
- expected effect: FP↓ on human corpus; prevents category-tier metadata from being decorative.
- confidence: high

### F4: Sentence parser violates its own list/word-count contract
- surface: `src/slopvac/analyze.py:294-296` (`re.split(r"(?<=:)\\s+", chunk)`) and `STEP_NUMBER` at `:102`
- kind: code-bug
- evidence: The split is unconditional, although the metric contract says only a colon introducing a vertical list terminates a sentence. Actual CLI probe `The gateway sends the request through the authenticated proxy before it applies the retry policy for all clients in production environments today: the parser reads this value.` (no list follows) reports `ste-punctuation.colon-terminates-sentence-for-count` with “lead-in ... 22 words”; the list control with `The gateway sends these values:` followed by bullets reports zero. Separately, `(1)` is collapsed by `PAREN_SPAN` to one token instead of stripped by rule 8.6: the 25-word unnumbered probe becomes 26 engine words and reports `sentence-too-long-descriptive`; `1.` control is 19 words and does not report. Human long-sentence baseline is 133 (6.27/1k) vs AI 57 (5.78/1k), and colon metric is 25 vs 4.
- proposal: Detect a list colon from block structure (`block.text` ending `:` plus immediately following list item) before splitting; do not split ordinary inline colons. Extend `STEP_NUMBER` to remove parenthesized ordered markers (`(1)`, `(a)`, `(iv)`) before `PAREN_SPAN`, with tests for the documented forms.
- expected effect: FP↓ on both sentence-length and colon-count rules; fixes boundary correctness.
- confidence: high

### F5: Noun-stack suffix heuristic counts adjectives and gerunds as noun stacks
- surface: `ste-nouns.multiword-noun-too-long`; `src/slopvac/analyze.py:740-808` (`longest_noun_stack`)
- kind: fp-risk
- evidence: Human baseline samples include “Quick examples comparing tools” (`ripgrep-readme-2021.md:39`), “Install with `pip` or your favorite PyPI package manager” (`rich-readme-2020.md:48`), “_Black_ is the uncompromising Python code formatter” (`black-readme-2021.md:19`), and “Requests is one of the most downloaded Python package today” (`requests-readme-2020.md:22`). Direct actual metric probes give `longest_noun_stack("Quick examples comparing tools.") == 4` and a lint finding, while the readable control `Set the jitter factor for retry backoff.` gives 2 and no finding. The implementation only requires one suffix hit (`-ing`, `-er`, etc.) and accepts every plain word in the contiguous run, so `comparing` and adjectives inflate the stack. Human baseline 70 (3.30/1k) vs AI 36 (3.65/1k), ratio 1.10.
- proposal: Make the heuristic conservative: exclude gerunds unless they are in a closed noun lexicon, stop at adjective/proper-name modifiers, and do not lint headings as sentence noun stacks. If no POS model is acceptable, demote normal to advisory and keep only explicit registered/domain stacks enforced.
- expected effect: FP↓ on human corpus (with an admitted FN trade-off); likely more useful discrimination after demotion.
- confidence: high

### F6: Omitted-conjunction regex catches sentence-initial imperatives
- surface: `ste-practices.omitted-conjunction-that`
- kind: fp-risk
- evidence: Human `ripgrep-guide-2021.md:1005` says “* `-C/--context`: Show the lines surrounding a match.” and `black-readme-2021.md:172` is the heading “## Show your style”; both are commands/labels, not reporting clauses missing `that`. Actual CLI probe `Show the lines surrounding a match.` reports one `ste-practices.omitted-conjunction-that` finding. In contrast `The dashboard shows the queue is empty.` is the intended reporting-verb shape. Human baseline 21 (0.99/1k) vs AI 10 (1.01/1k), ratio 1.02.
- proposal: Require a non-initial subject/reporting context (or negative-anchor sentence/list starts) for `show|check|note|verify|confirm`; explicitly allow sentence-initial imperatives and headings. Keep `make sure the...` and subject-led `dashboard shows the...` coverage.
- expected effect: FP↓ on human corpus without reducing the intended subject-led conjunction gap.
- confidence: high

### F7: Demonstrative/pro-noun rules treat clear local references as unclear
- surface: `ste-practices.unclear-demonstrative-this`, `ste-practices.unclear-pronoun`
- kind: fp-risk
- evidence: Human samples include “symbols. This is intentional.” (`ripgrep-readme-2021.md:338`), “This will clean: jemalloc, lua, hiredis, linenoise.” (`redis-readme-2021.md:80`), “put the flag and the value on two different lines. This is because ripgrep's...” (`ripgrep-guide-2021.md:586`), and “Since fzf is a general-purpose text filter ... **it is ...**” (`fzf-readme-2021.md:631`). These have an immediate, recoverable antecedent, yet baseline reports 47 demonstrative and 11 pronoun findings on human prose versus 9 and 0 on AI. The rules are advisory/enforced at normal but have no discourse/antecedent analysis. Actual CLI probe `The option is disabled. This is intentional.` reports one `ste-practices.unclear-demonstrative-this` finding, despite the immediately preceding sentence supplying the referent; the same rule is silent on a noun-specific rewrite. These have an immediate, recoverable antecedent, yet baseline reports 47 demonstrative and 11 pronoun findings on human prose versus 9 and 0 on AI. The rules are advisory/enforced at normal but have no discourse/antecedent analysis.
- proposal: Demote `unclear-demonstrative-this` and `unclear-pronoun` to advisory at normal (or require no plausible antecedent in the preceding sentence); retain checks for sentence-opening bare demonstratives with no local noun candidate.
- expected effect: FP↓; candidate human/AI ratios are 0.42 and 0.09.
- confidence: medium

## Decommission candidates
- `ste-verbs.auxiliary-stacking`: delete or narrow as F2; 71 human vs 6 AI and duplicates passive voice.
- `ste-practices.unclear-pronoun`: demote/disable at normal; 11 human vs 0 AI, with clear antecedents in reviewed samples.
- `ste-nouns.multiword-noun-too-long`: do not keep enforced at normal until the POS/heading heuristic is narrowed; 70 human vs 36 AI and four of five reviewed samples are readable modifiers/headings.
- `ste-practices.omitted-conjunction-that`: keep advisory (already advisory) but fix sentence-initial imperative guard; 21 human vs 10 AI.

## Tier check
- At `normal`, 33 target rules are `enforced` and 8 are `advisory`; none of the 41 target rules is `excluded` (the inventory and YAML tiers were loaded with `safe_load_all`).
- The shipped `ste-principles.md` explicitly says the linter owns word lists, substitutions, and length checks and caps instructions at 20/explanations at 25; this matches the metric rules, but it does not justify enforcing passive, noun-stack, or discourse heuristics on README prose.
- Root `slopvac.toml` demotes all eight STE categories to `suggestion`, confirming this repository treats the shipped normal enforcement as too strict for its own README/docs; that is a configuration signal, not proof that all rules are bad.

## Baseline sample classification (human; TP = real STE/style defect, FP = false positive)
- `ste-verbs.passive-voice` (239): `annotated-types:10 be treated` TP; `annotated-types:16 be interpreted` TP; `annotated-types:53 was annotated` TP; `ripgrep-guide:647 will be read` TP; `annotated-types:122 is often` FP (adverb suffix).
- `ste-verbs.auxiliary-stacking` (71): `annotated-types:13 can be used` FP/duplicate; `annotated-types:53 can be compared` FP/duplicate; `black:65 can be found` FP/duplicate; `fzf:135 can be downloaded` FP/duplicate; `black:150 would have taken` TP (multi-auxiliary chain).
- `ste-nouns.multiword-noun-too-long` (70): `annotated-types:515 replacement string ...` FP/technical phrase; `black:19 uncompromising Python code formatter` FP/modifier; `rich:48 favorite PyPI package manager` FP/modifier; `ripgrep:39 Quick examples comparing tools` FP/heading-gerund; `requests:22 most downloaded Python package` FP/modifier.
- `ste-descriptive.sentence-too-long-descriptive` (133): `ripgrep-guide:313 reversing the order ...` TP/over-25 explanatory sentence; `git-contributing:280 People on the Git mailing list ...` TP; `ripgrep-readme:103 ripgrep supports many features ...` TP; `git-contributing:410 Send it to the list ...` TP under 25-word cap only if the full sentence exceeds it; `annotated-types:8 PEP-593 added ...` TP (32 words).
- `ste-procedural.sentence-too-long-procedural` (10): `git-contributing:53 Give an explanation ...` TP; `:81 Do not forget to update ...` TP; `:300 It is a common convention ...` FP (descriptive “It is” misclassified); `:365 Send your patch ...` TP; `redis:199 Make install ...` TP.
- `ste-procedural.condition-after-command` (76): `black:24 Formatting becomes transparent after ...` FP/descriptive; `black:59 You can run ... if ...` FP/capability; `fzf:82 You can download ... if ...` FP/capability; `fzf:314 It will still work ... when ...` FP/descriptive; `fzf:352 ... can be triggered if ...` FP/passive description.
- `ste-sentences.omitted-word-or-contraction` (122): `black:59 doesn't`, `fzf:82 don't`, `fzf:161 it's`, `ripgrep-guide:501 let's`, `annotated-types:265 you'd` are TP under the rule's explicit no-contractions/complete-clause policy. Quoted and code controls produce zero findings; reduced `If configured, ...` produces one intended finding.
- `ste-practices.omitted-conjunction-that` (21): `redis:296 show the main ones` FP/imperative-ish lead-in; `ripgrep-guide:1005 Show the lines` FP/imperative; `black:172 Show your style` FP/heading; `ripgrep-readme:171 That means a single file path...` TP; `git:258 make sure your patch...` TP.
- `ste-practices.unclear-demonstrative-this` (47): `ripgrep:338 This is intentional` FP/local antecedent; `redis:80 This will clean` FP/explicit list follows; `ripgrep-guide:586 This is because...` FP/local antecedent; `redis:10 This means...` FP/local antecedent; `ripgrep-guide:305 This is ...` FP/local antecedent.
- `ste-practices.unclear-pronoun` (11): `ripgrep:295 it is no ...` FP/local antecedent; `redis:56 it is a good idea` FP/generic expletive; `fzf:631 it is ...` FP/local antecedent; `redis:432 it is recommended` FP/local antecedent; `git:492 he applies your patch` FP/known maintainer.
- `ste-practices.phrasal-verb` (8): fzf:536 `set up key bindings` TP; git:491 `end up hand editing` TP; git:481 `set up` TP; fzf:482 `pick up the function` TP; git:434 `pick up and apply the patch` TP (replaceable wording).
- `ste-practices.false-friend-term` (18): git:430 `eventually` TP; ripgrep:70/638/209/999 `actually` are TP where filler/false-friend wording is replaceable.
- `ste-practices.latin-abbreviation` (39): fzf:270, fzf:237, fzf:266, git:130, fzf:266 `e.g./i.e.` are TP under the explicit controlled-English rule; code-span portions are excluded by the engine.
- `ste-practices.gendered-or-exclusionary-language` (10): ripgrep:314/359 and ripgrep-readme:62 `blacklist/whitelist` are TP modernization candidates; markdown-it-py:142 `his work` is FP (known person's pronoun); git:492 `he applies` is FP when referring to a named maintainer.
- `ste-words.approved-word-substitution` (36): redis:371/265/374 and git:100/475 are TP controlled-vocabulary replacements (`in order to`, `ensure`); review semantics before changing `require`/`ensure` globally.
- `ste-words.obligation-word-substitution` (35): ripgrep:609, redis:273, annotated-types:70/243, git:287 are FP-risk/semantic: `should` can be deliberately non-normative; rule is advisory at normal.
- `ste-sentences.complex-text-not-in-vertical-list` (44): ripgrep:707, rich:272, ripgrep:661, dogfood:384, ripgrep:782 are TP/series readability candidates, though headings/tables need structural exemptions.
- `ste-punctuation.semicolon-used` (26): redis:398, fzf:382, git:297, redis:208 are TP under no-semicolon style; git:533 `stripwhitespace();` is FP/code (a fenced/source snippet).
- `ste-punctuation.hyphen-missing-in-compound-modifier` (20): markdown-it-py:20, ripgrep:276, rich:430, git:185, black:115 are FP-risk when the phrase is a product/domain term or normal compound; advisory at normal.
- `ste-punctuation.hyphen-group-too-long` (2): fzf:247/248 are FP/table cells containing identifiers such as `inverse-prefix-exact-match`; `table-cell`/identifier exception should suppress them.
- `docs-discipline.status-language` (6): ripgrep:373, ripgrep:279, requests:22, git:85 are FP/current-state uses of `currently`; black:92 `planned changes` is TP; one ripgrep warning line is FP.
- `docs-discipline.history-narration` (6): git:308 `previously sent`, redis:268 `was refactored`, black:103/150 historical context are FP in explanatory docs; annotated-types:107 rename note is TP migration information.
- `docs-discipline.internal-refs` (1): fzf:392 `names are extracted from /etc/hosts ...` is FP; “extracted from” describes runtime behavior, not an internal process pointer.
- Rules with zero human samples (`inconsistent-wording-for-same-step`, `unclear/possessive-form-unclear`, `note-gives-instruction`, `vertical-list-lead-in-missing-colon`, `vertical-list-item-punctuation`, `missing-article-or-determiner`, `safety-block-*`, `inconsistent-term-for-same-thing`, `noun-used-as-verb`, `slang-or-jargon-term`, `verb-used-as-noun`, and other zero-count structures) compiled and had no corpus evidence; no FP/FN claim is made.

## Checked and fine
- YAML `safe_load_all` loading and all target lexical own examples: every `bad` fired and every `good` stayed silent.
- Code spans, plain URLs, Markdown tables, quoted contractions, and active-voice controls behaved as intended in the probes.
- Omitted-word/contraction has no observed false positive outside the deliberate reduced-clause policy; keep its normal warning pending broader corpus review.
- Safety/list structures and document-wide consistency rules were inspected and had zero baseline human samples; treat their status as unmeasured, not proven.
