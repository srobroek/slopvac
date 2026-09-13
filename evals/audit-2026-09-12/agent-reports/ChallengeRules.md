Claim: The audit treats sampled editorial acceptability as detector precision and recommends deleting or narrowing rules without genre-controlled separation or executable loss tests.
VERDICT: CHALLENGED

## Summary
- Recomputed from the baseline JSON: 8 decommission proposals reverse under the README control; `no-unicode-dash` is 15.2×, tricolon 3.26×, unsupported-evaluative 3.42×, and complex-list 2.21× denser in AI READMEs.
- `HumanFpLabels` and `AiFnLabels` conflate detector false positives with policy disagreement. In the requested relabel, every sampled passive, contraction, dash, tricolon, Latinism, compound-preposition, and inclusion term actually contains the named pattern.
- Three narrowing proposals are not executable: no participle lexicon, omitted-conjunction regex, or noun-stack algorithm is supplied. Their TP loss cannot be measured.
- Naive `text_type` gating removes 30 of 33 AI condition-rule hits and every runbook hit, including “Remember to update … when you get a chance.”
- Decommission is justified for weak mechanical proxies such as emphasis-paragraph, command-prompt-in-code, and simple auxiliary stacking; discriminating AI-tell rules should instead remain advisory or feed judgement.

## Method and genre-controlled density

Counts come from `runs/baseline__human__normal.json` and `runs/baseline__ai-existing__normal.json`. Denominators are 21,208 human words, 9,865 AI words, 13,009 words in the nine named human READMEs, and 2,850 words in the three named AI READMEs. Each cell is `findings / findings per 1,000 words`.

| proposed demotion/decommission | human all | AI all | human READMEs | AI READMEs | AI:H README ratio |
|---|---:|---:|---:|---:|---:|
| `ai-tells-content-shape.durable-vocabulary-habits` | 15 / 0.71 | 7 / 0.71 | 13 / 1.00 | 1 / 0.35 | 0.35× |
| `ai-tells-structure.emphasis-paragraph-metric` | 80 / 3.77 | 18 / 1.82 | 52 / 4.00 | 2 / 0.70 | 0.18× |
| `ai-tells-structure.tricolon-abuse-core` | 7 / 0.33 | 11 / 1.12 | 7 / 0.54 | 5 / 1.75 | **3.26×** |
| `docs-discipline.history-narration` | 6 / 0.28 | 12 / 1.22 | 5 / 0.38 | 1 / 0.35 | 0.91× |
| `docs-discipline.status-language` | 6 / 0.28 | 5 / 0.51 | 5 / 0.38 | 2 / 0.70 | **1.83×** |
| `orwell.unsupported-evaluative` | 6 / 0.28 | 7 / 0.71 | 4 / 0.31 | 3 / 1.05 | **3.42×** |
| `prose-agency.false-agency` | 12 / 0.57 | 0 / 0.00 | 5 / 0.38 | 0 / 0.00 | 0.00× |
| `prose-craft.command-prompt` | 80 / 3.77 | 0 / 0.00 | 30 / 2.31 | 0 / 0.00 | 0.00× |
| `prose-craft.directional-ref` | 8 / 0.38 | 1 / 0.10 | 5 / 0.38 | 0 / 0.00 | 0.00× |
| `prose-craft.first-person-plural` | 115 / 5.42 | 84 / 8.51 | 43 / 3.31 | 3 / 1.05 | 0.32× |
| `prose-craft.future-tense` | 105 / 4.95 | 30 / 3.04 | 51 / 3.92 | 3 / 1.05 | 0.27× |
| `prose-craft.latinisms` | 44 / 2.07 | 4 / 0.41 | 27 / 2.08 | 0 / 0.00 | 0.00× |
| `prose-craft.link-text` | 6 / 0.28 | 1 / 0.10 | 6 / 0.46 | 0 / 0.00 | 0.00× |
| `prose-craft.politeness` | 26 / 1.23 | 8 / 0.81 | 16 / 1.23 | 2 / 0.70 | 0.57× |
| `prose-craft.self-reference` | 6 / 0.28 | 0 / 0.00 | 0 / 0.00 | 0 / 0.00 | 0.00× |
| `prose-craft.unclear-antecedent` | 42 / 1.98 | 8 / 0.81 | 14 / 1.08 | 2 / 0.70 | 0.65× |
| `prose-craft.versions` | 7 / 0.33 | 1 / 0.10 | 6 / 0.46 | 1 / 0.35 | 0.76× |
| `prose-discipline.term-rotation-signal` | 1 / 0.05 | 23 / 2.33 | 1 / 0.08 | 0 / 0.00 | 0.00× |
| `prose-format.no-unicode-dash` | 6 / 0.28 | 67 / 6.79 | 6 / 0.46 | 20 / 7.02 | **15.22×** |
| `prose-format.prose-block` | 13 / 0.61 | 2 / 0.20 | 4 / 0.31 | 0 / 0.00 | 0.00× |
| `prose-inclusive.exclusive` | 13 / 0.61 | 0 / 0.00 | 4 / 0.31 | 0 / 0.00 | 0.00× |
| `ste-nouns.multiword-noun-too-long` | 70 / 3.30 | 36 / 3.65 | 42 / 3.23 | 6 / 2.11 | 0.65× |
| `ste-practices.gendered-or-exclusionary-language` | 10 / 0.47 | 0 / 0.00 | 2 / 0.15 | 0 / 0.00 | 0.00× |
| `ste-practices.latin-abbreviation` | 39 / 1.84 | 7 / 0.71 | 26 / 2.00 | 0 / 0.00 | 0.00× |
| `ste-practices.omitted-conjunction-that` | 21 / 0.99 | 10 / 1.01 | 8 / 0.61 | 1 / 0.35 | 0.57× |
| `ste-practices.phrasal-verb` | 8 / 0.38 | 5 / 0.51 | 2 / 0.15 | 1 / 0.35 | **2.28×** |
| `ste-practices.unclear-demonstrative-this` | 47 / 2.22 | 9 / 0.91 | 18 / 1.38 | 2 / 0.70 | 0.51× |
| `ste-practices.unclear-pronoun` | 11 / 0.52 | 0 / 0.00 | 7 / 0.54 | 0 / 0.00 | 0.00× |
| `ste-procedural.condition-after-command` | 76 / 3.58 | 33 / 3.35 | 34 / 2.61 | 7 / 2.46 | 0.94× |
| `ste-procedural.instruction-not-imperative` | 38 / 1.79 | 7 / 0.71 | 27 / 2.08 | 1 / 0.35 | 0.17× |
| `ste-procedural.multiple-instructions-per-sentence` | 41 / 1.93 | 9 / 0.91 | 19 / 1.46 | 2 / 0.70 | 0.48× |
| `ste-punctuation.colon-terminates-sentence-for-count` | 25 / 1.18 | 4 / 0.41 | 12 / 0.92 | 4 / 1.40 | **1.52×** |
| `ste-punctuation.semicolon-used` | 26 / 1.23 | 18 / 1.82 | 17 / 1.31 | 4 / 1.40 | **1.07×** |
| `ste-sentences.complex-text-not-in-vertical-list` | 44 / 2.07 | 31 / 3.14 | 33 / 2.54 | 16 / 5.61 | **2.21×** |
| `ste-sentences.omitted-word-or-contraction` | 122 / 5.75 | 93 / 9.43 | 61 / 4.69 | 12 / 4.21 | 0.90× |
| `ste-verbs.auxiliary-stacking` | 71 / 3.35 | 6 / 0.61 | 46 / 3.54 | 1 / 0.35 | 0.10× |
| `ste-verbs.complex-tense` | 51 / 2.40 | 21 / 2.13 | 24 / 1.84 | 1 / 0.35 | 0.19× |
| `ste-verbs.nominalized-action` | 11 / 0.52 | 2 / 0.20 | 4 / 0.31 | 0 / 0.00 | 0.00× |
| `ste-verbs.passive-voice` | 239 / 11.27 | 48 / 4.87 | 145 / 11.15 | 7 / 2.46 | 0.22× |
| `ste-words.spelling` | 9 / 0.42 | 6 / 0.61 | 9 / 0.69 | 0 / 0.00 | 0.00× |

The README control kills the decommission case for tricolon, status-language, unsupported-evaluative, STE phrasal-verb, colon-count, semicolon, complex-list, and Unicode dash. A ratio alone does not prove a good rule, but deleting these would discard observed genre-controlled signal.

## Relabel of claimed human false positives

`HumanFpLabels-labels.json` does not contain ten `FP-correct-prose` rows for any requested rule. Available counts are passive 9, first-person 0, future 7, contraction 5, dash 4, tricolon 8, emphasis 7, Latinisms 5, compound-preposition 0, and exclusive 5. I therefore used a reproducible random sample of baseline findings (seed 20260912 plus rule index), taking all findings where fewer than ten existed. This substitution matters: the requested sample literally cannot be drawn from the sidecar.

Labels below separate **P** = pattern occurred but normal-profile policy should not care, **H** = pattern occurred and the policy has an actionable style hit, and **D** = detector FP because the named pattern did not occur. There were **zero D labels** in all 93 rows.

### `ste-verbs.passive-voice` — 7 P, 3 H, 0 D
- P — `annotated-types-readme-2022.md:200`: “We do not specify what behaviour should be expected for predicates that raise an exception.”
- P — `ripgrep-guide-2021.md:194`: “Hidden files and directories can be searched with the `--hidden` flag.”
- H — `git-contributing-2021.md:468`: “If a branch did not pass all test cases then it is marked with a red cross.”
- P — `dogfood-readme-human.md:430`: “`slopvac explain <rule>` gives the reason the rule is worded as it is.”
- H — `dogfood-readme-human.md:175`: “Specificity ranking was rejected because there is no ordering on globs a reader can predict.”
- P — `annotated-types-readme-2022.md:108`: “`min_inclusive` has been renamed to `min_length`.”
- H — `requests-readme-2020.md:22`: “Requests is currently depended upon by `500,000+` repositories.”
- P — `ripgrep-guide-2021.md:278`: “TOML files … are how dependencies are communicated to Rust's build tool.”
- P — `redis-readme-2021.md:354`: “`serverCron()` is called periodically.”
- P — `ripgrep-guide-2021.md:193`: “Binary files can be searched via the `--text` flag.”

Every row is syntactically passive. `HumanFpLabels` calls four sampled passives “correct prose,” while `AiFnLabels` calls 38/48 AI passives FP candidates; both are policy judgements, not detector errors.

### `prose-craft.first-person-plural` — 10 P, 0 H, 0 D
- P — `annotated-types-readme-2022.md:251`: “We intend to not be prescriptive as to how the metadata and constraints are used.”
- P — `ripgrep-guide-2021.md:291`: “If we wanted, we could tell ripgrep to search anything but `*.toml` files.”
- P — `ripgrep-guide-2021.md:784`: “In our case, we want to search Bruce Watson's excellent dissertation.”
- P — `black-readme-2021.md:227`: “We are not savages.”
- P — `git-contributing-2021.md:89`: “We currently have a liberal mixture of US and UK English norms.”
- P — `ripgrep-guide-2021.md:801`: “The tool we use, `pdftotext`, is part of the poppler library.”
- P — `ripgrep-guide-2021.md:913`: “We can even extend our preprocessor to search other kinds of files.”
- P — `ripgrep-guide-2021.md:821`: “So let's write a simple shell script that wraps `pdftotext`.”
- P — `ripgrep-guide-2021.md:787`: “After downloading it, let's try searching it.”
- P — `ripgrep-guide-2021.md:795`: “Our search isn't picking it up because PDFs are a binary format.”

The pattern is present in all ten. The report's `FP-genre` label is a defensible normal-profile policy call, but cannot support a detector-precision claim.

### `prose-craft.future-tense` — 9 P, 1 H, 0 D
- P — `ripgrep-guide-2021.md:30`: “If a line matches the pattern … that line will be printed.”
- P — `ripgrep-guide-2021.md:798`: “Even passing the `--text` flag … will not make our search work.”
- P — `ripgrep-guide-2021.md:657`: “Character classes like `\w` will match all word characters.”
- P — `ripgrep-guide-2021.md:201`: “Repeated uses of this flag will cause ripgrep to disable more and more filtering.”
- P — `ripgrep-guide-2021.md:671`: “The value `none` … will completely disable all encoding-related logic.”
- P — `rich-readme-2020.md:99`: “This will print `Hello World!` to the terminal.”
- P — `ripgrep-guide-2021.md:614`: “The `--no-config` flag … will always prevent ripgrep from reading extraneous configuration.”
- P — `ripgrep-guide-2021.md:876`: “The preprocessor … will fail if you try to search a file that isn't a PDF.”
- H — `annotated-types-readme-2022.md:264`: “Staying simple … will give users and maintainers the best experience.”
- P — `ripgrep-guide-2021.md:658`: “Ripgrep will transcode the contents … and then execute the search.”

Nine are conditional/result semantics rather than roadmap narration. The detector found future tense correctly; the broad policy is what fails.

### `ste-sentences.omitted-word-or-contraction` — 10 P at normal, 10 H under strict STE, 0 D
- `ripgrep-guide-2021.md:679`: “That's just an example.”
- `ripgrep-guide-2021.md:598`: “Let's say you're using the above configuration file.”
- `ripgrep-guide-2021.md:877`: “A file that isn't a PDF.”
- `fzf-readme-2021.md:162`: “A plugin manager that doesn't support hooks.”
- `ripgrep-guide-2021.md:999`: “Don't actually search them.”
- `git-contributing-2021.md:230`: “Please don't hide your real name.”
- `ripgrep-readme-2021.md:295`: “Bug reports that I don't know how to fix.”
- `ripgrep-guide-2021.md:34`: “Let's try searching ripgrep's source code.”
- `ripgrep-guide-2021.md:988`: “Nearly what you'd find in ripgrep's man page.”
- `black-readme-2021.md:59`: “If running it as a script doesn't work.”

All ten are literal contractions. `HumanFpLabels` calls them detector FPs even though the named controlled-English policy expressly bans contractions. The sound conclusion is profile demotion, not “the detector is 100% FP.”

### `prose-format.no-unicode-dash` — 2 P, 4 H, 0 D (all 6 available)
- P — `rich-readme-2020.md:32`: “Tracebacks, and more — out of the box.”
- P — `requests-readme-2020.md:20`: “To form-encode your data — but nowadays, just use the `json` method.”
- H — `requests-readme-2020.md:40`: “HTTP–speaking applications.”
- H — `requests-readme-2020.md:47`: “Familiar `dict`–like Cookies.”
- H — `requests-readme-2020.md:38`: “Supported Features & Best–Practices.”
- H — `requests-readme-2020.md:22`: “`14M downloads / week`— according to GitHub.”

All six contain U+2013 or U+2014; the last four also use a dash where a hyphen or spacing correction is warranted. `AiFnLabels`'s 53/67 “FP” count is entirely a policy count. The rule pattern is exactly `[—–]` at `rules/prose-format.yml:9-20`, so its detector-FP count is zero unless the engine reports a span without either character.

### `ai-tells-structure.tricolon-abuse-core` — 6 P, 1 H, 0 D (all 7 available)
- P — `fzf-readme-2021.md:612`: “The size, position, and border of the preview window.”
- P — `black-readme-2021.md:137`: “Home Assistant, Zulip, and many more.”
- P — `dogfood-readme-human.md:29`: “Token, regex, and substitution matching.”
- P — `rich-readme-2020.md:32`: “Source code, tracebacks, and more.”
- P — `fzf-readme-2021.md:327`: “Key bindings for bash, zsh, and fish.”
- H — `black-readme-2021.md:20`: “Speed, determinism, and freedom from `pycodestyle` nagging.”
- P — `redis-readme-2021.md:12`: “Durability, clustering, and high availability.”

Every row is a three-part coordinate construction. Six are technical enumeration; one is promotional cadence. The audit correctly identifies semantic overbreadth but incorrectly reports this as 100% detector FP.

### `ai-tells-structure.emphasis-paragraph-metric` — 9 P, 1 H, 0 D
- P — `git-contributing-2021.md:458`: “Follow these steps for the initial setup:”
- P — `fzf-readme-2021.md:510`: “See `README-VIM.md`.”
- P — `black-readme-2021.md:163`: “Carl Meyer, Django core developer:”
- P — `rich-readme-2020.md:107`: “The output will be something like the following:”
- P — `markdown-it-py-readme-2020.md:53`: “or with extras”
- H — `git-contributing-2021.md:513`: “.... And 4.58 needs at least this.”
- P — `fzf-readme-2021.md:688`: “will list all files and directories under `/var/`.”
- P — `ripgrep-readme-2021.md:15`: “Dual-licensed under MIT or the UNLICENSE.”
- P — `fzf-readme-2021.md:4`: “fzf is a general-purpose command-line fuzzy finder.”
- P — `ripgrep-guide-2021.md:337`: “or, more succinctly,”

The short standalone-paragraph shape exists in all ten. Its policy has poor utility, consistent with the 0.18× README ratio, but the metric is not hallucinating spans.

### `prose-craft.latinisms` — 10 P at normal, 10 H under strict controlled English, 0 D
- `ripgrep-readme-2021.md:112`: “served via memory maps”
- `fzf-readme-2021.md:10`: “processes, hostnames, bookmarks, git commits, etc.”
- `git-contributing-2021.md:306`: “`[PATCH v2]`, `[PATCH v3]` etc. are often seen”
- `fzf-readme-2021.md:121`: “NixOS, etc.”
- `git-contributing-2021.md:304`: “E.g. `[RFC PATCH]`”
- `git-contributing-2021.md:443`: “i.e. it will not tell you”
- `ripgrep-guide-2021.md:260`: “manual or ad hoc filtering”
- `git-contributing-2021.md:122`: “E.g. `doc: clarify...`”
- `annotated-types-readme-2022.md:189`: “write e.g. `x: IsFinite[float]`”
- `annotated-types-readme-2022.md:247`: “unpacks itself into `Gt`, `Lt`, etc.”

The exact banned terms occur in every row. Calling these “FP-correct-prose” measures disagreement with simplified-English policy, not detection.

### `orwell.compound-preposition` — 0 P, 10 H, 0 D
- `ripgrep-guide-2021.md:715`: “In order to figure out whether a file is binary…”
- `redis-readme-2021.md:374`: “in order to append data”
- `redis-readme-2021.md:265`: “in order to disclose different layers”
- `redis-readme-2021.md:409`: “in order to get a pointer”
- `redis-readme-2021.md:403`: “in order to perform certain operations”
- `redis-readme-2021.md:385`: “in order to create a thread”
- `redis-readme-2021.md:252`: “in order to execute the unit tests”
- `redis-readme-2021.md:371`: “in order to append data”
- `redis-readme-2021.md:345`: “steps in order to startup the Redis server”
- `git-contributing-2021.md:433`: “in order to make it easier”

All ten have a direct shorter rewrite (“to”). `HumanFpLabels` already labels its five sampled rows TP; this is the requested control case showing that not every stylistic pattern was conflated.

### `prose-inclusive.exclusive` — 2 P, 8 H, 0 D
- H — `redis-readme-2021.md:438`: “replica instances connected to our master”
- P — `git-contributing-2021.md:441`: “when your patch is merged in master”
- H — `ripgrep-readme-2021.md:62`: “searches with a whitelist instead”
- P — `git-contributing-2021.md:445`: “rebase on top of master”
- H — `ripgrep-guide-2021.md:359`: “write blacklist globs”
- H — `redis-readme-2021.md:434`: “the master and replica role of Redis”
- H — `ripgrep-guide-2021.md:359`: “blacklist file types”
- H — `ripgrep-guide-2021.md:303`: “whitelist … blacklist”
- H — `ripgrep-guide-2021.md:316`: “the blacklist glob takes precedence”
- H — `ripgrep-guide-2021.md:237`: “the `!log/` whitelist rule”

The two policy FPs are exact historical branch names; the other eight are modernizable generic terms. The audit labels all five sampled rows FP and thereby converts a policy decision into a detector claim. The random sample also exposes dependence: two findings come from the same Git paragraph and two from the same ripgrep line.

## Regex narrowing TP-loss audit

Raw-line comparisons use the shipped pattern/token construction and each exact `proposed_regex` in `RegexAiTells-probes.json`. `text_type` gating was simulated with `analyze.parse` and `classify_text_type`. “AI lost” counts all lost current matches; quoted rows identify actual tell/style TPs among them.

| proposal | human change | AI change | true AI TPs lost | verdict |
|---|---:|---:|---|---|
| dead-opener compile fix | uncompilable → 22 | baseline 2 → proposed 2 | none; both baseline spans remain | ACCEPT |
| contrastive-inversion cross-sentence | 0 → 0 | 1 → 1 | none | ACCEPT |
| fake-specificity stop-word guard | 2 → 1 | 1 → 1 | none | ACCEPT |
| optional-plural remove `/s` | 4 → 2 | 2 → 2 | none | ACCEPT |
| emoji-list marker required | 1 → 0 | 11 → 10 | one cross-family emoji-residue TP, but not a list-marker TP | ACCEPT |
| rhetorical-question cue required | 3 → 0 | 1 → 0 | one rhetorical-heading TP | ACCEPT-MODIFIED |
| false-agency remove `lets/helps` | 11 → 2 | 0 → 0 | none | ACCEPT |
| summary-closer sentence anchor (also proposed in RegexAiTells F7) | 1 → 0 | 2 → 0 | two | REJECT |
| passive closed participle lexicon | unspecified | unspecified | unmeasurable | INSUFFICIENT-EVIDENCE |
| omitted-conjunction imperative guard | unspecified | unspecified | unmeasurable | INSUFFICIENT-EVIDENCE |
| noun-stack conservatism | unspecified | unspecified | unmeasurable | INSUFFICIENT-EVIDENCE |
| condition-after-command `text_type` gate | parsed matches: 90 → 4 kept | parsed matches: 33 → 3 kept | at least five of 30 losses | REJECT |

TP-loss quotes:

- Emoji marker: `unguided__error-message.md:3`, “⚠️ **Whoa there!** You've hit our rate limit.” It is genuine AI formatting residue, but the rule is specifically named `emoji-list-markers`; accepting the narrowing requires another emoji-residue rule to own this non-list case.
- Rhetorical cue: `unguided__readme-cache.md:7`, “## Why fluxcache?” This is a rhetorical product-heading TP. The exact modification is to keep cue-led questions mechanical and send bare question headings to judgement rather than declaring them clean.
- Summary closer: `unguided__guide-migration.md:74` and `unguided__runbook-failover.md:59`, both “## Wrapping Up”. The proposed regex loses two AI TPs while removing one human hit. Use a line/heading-aware anchor such as optional Markdown heading markers before the closer; do not require the closer token itself to start column 1.
- Condition gate true losses include `independent__blog-skip-locked.md:99`, “Measure before you commit”; `independent__design-doc-outbox.md:30`, “Guarantee that an event is published if and only if its database transaction commits”; `unguided__api-docs-webhook.md:36`, “You should always verify the signature before processing a delivery”; `unguided__readme-cache.md:87`, “Decide — if the best match exceeds your threshold, it's a hit”; and `unguided__runbook-failover.md:61`, “Remember to update the incident channel … when you get a chance.”
- Passive lexicon at-risk TPs include “Webhooks are delivered as HTTP POST requests” (`unguided__api-docs-webhook.md:9`), “an event is published if and only if…” (`independent__design-doc-outbox.md:30`), and “can no longer be reattached” (`unguided__runbook-failover.md:35`). RegexSte F1 supplies no closed lexicon or exact regex, so no honest loss number exists.
- Omitted-conjunction guard supplies no anchor or replacement regex. Current AI matches include the real missing conjunction “verify it genuinely came from us” (`unguided__api-docs-webhook.md:9`) and false matches such as the heading “Verify the handshake” (`independent__tutorial-mtls.md:135`). A prose description cannot establish which one a proposed regex preserves.
- Noun-stack conservatism is an algorithm proposal, not a regex. Its undefined adjective/proper-name stops could lose AI phrases such as “new pooled connection manager,” “new pool configuration options,” and “future scalability improvements” (`unguided__pr-description.md:5,17,20`).

## Condition-after-command and `text_type`

The engine classifies a sentence as safety when it starts with a warning marker, descriptive when it starts with a note marker, procedural when the remaining text matches the closed `IMPERATIVE_MARKERS`, and descriptive otherwise (`analyze.py:251-271`). The current lexical path iterates `prose_lines` without consulting either sentence boundaries or `rule.text_type` (`engine.py:655-670`); only sentence metrics honor `text_type` (`engine.py:757-760`). RegexSte F3 is correct about that mismatch.

The proposed fix is nevertheless unsafe. The runbook parses as 29 descriptive and 4 procedural sentences. All three baseline `condition-after-command` findings are classified descriptive and would be removed:

- `unguided__runbook-failover.md:5`: “don't worry — if you follow the steps … you'll be fine” — current FP.
- `unguided__runbook-failover.md:35`: “Promoting the replica is irreversible — once you do this…” — descriptive safety information.
- `unguided__runbook-failover.md:61`: “Remember to update the incident channel … when you get a chance” — true procedural hit.

`remember` and `decide` are absent from `IMPERATIVE_MARKERS` (`analyze.py:101-116`), and modal instructions such as “You should always verify…” default to descriptive. Gate lexical rules by `text_type` only after the classifier recognizes these runbook forms and a runbook control proves the true instruction survives.

## Em-dash position

AiFnLabels is wrong on detector precision. `prose-format.no-unicode-dash` is a literal `[—–]` presence rule with `scope: raw` and an explicit house-style replacement (`rules/prose-format.yml:9-35`). All 67 AI findings therefore contain the prohibited character; “ordinary punctuation” can only be a policy objection. The root README also says a clean run means checked patterns are absent, “nothing more” (`README.md:130-131`).

The density evidence is stronger than the stated “20×”: AI has 6.79 findings/1k versus human 0.28, about 24× overall; the README control remains 7.02 versus 0.46, or 15.2×. Presence is thus a useful AI-origin signal in these corpora, although it is not proof that any one sentence is AI-written.

Severity should be **error in strict or explicit house-style mode, advisory/suggestion at normal, and excluded at relaxed**. This preserves the strong signal and exact mechanical contract without making ordinary typographic preference fail every consumer or informal document. The separate density rule can remain advisory for origin/style clustering. Decommissioning the presence rule loses signal; leaving it as an unconditional error confuses a configurable house choice with universal correctness.

## Verdicts

### HumanFpLabels.table.durable-vocabulary-habits: demote or decommission the broad vocabulary proxy
- verdict: ACCEPT
- counter-evidence: 0.35× README ratio and equal 0.71/1k overall density; sampled tokens such as “features” and “acts as” do not establish an AI habit.
- risk if applied as proposed: none

### HumanFpLabels.table.emphasis-paragraph-metric: decommission the short emphasis-paragraph metric
- verdict: ACCEPT
- counter-evidence: AI READMEs are only 0.18× human README density; the ten-row relabel found the shape every time but only one actionable policy hit.
- risk if applied as proposed: none

### HumanFpLabels.table + RegexAiTells.F4.tricolon-abuse-core: decommission the mechanical tricolon core
- verdict: ACCEPT-MODIFIED
- counter-evidence: AI READMEs are 3.26× denser; one sampled human row is rhetorical cadence and six are technical lists.
- modification: Keep it as an advisory candidate feeding the judgement remainder; do not let the regex alone fail a document.
- risk if applied as proposed: FN↑

### HumanFpLabels.table.history-narration: decommission history narration
- verdict: ACCEPT-MODIFIED
- counter-evidence: overall AI density is 1.22 versus 0.28/1k, while README density is tied at 0.35–0.38; the report itself labels the human examples `FP-genre`.
- modification: Gate by genre: exclude change communications and migration history, retain advisory detection in current-state consumer docs.
- risk if applied as proposed: FN↑ in evergreen docs

### HumanFpLabels.table.status-language: decommission status language
- verdict: REJECT
- counter-evidence: AI READMEs are 1.83× denser, and relative status is a maintenance defect independent of origin.
- risk if applied as proposed: FN↑

### RegexAiTells.F10.unsupported-evaluative: remove the duplicate unsupported-evaluative rule
- verdict: ACCEPT-MODIFIED
- counter-evidence: AI READMEs are 3.42× denser; deletion discards genre-controlled signal.
- modification: Retain one owner and apply the report's exact technical phrase allowlist; remove only the duplicate implementation, not the policy.
- risk if applied as proposed: FN↑

### HumanFpLabels.table + RegexAiTells.F5.false-agency: decommission false-agency
- verdict: ACCEPT-MODIFIED
- counter-evidence: 12 human and zero AI findings; reader affordances dominate.
- modification: Remove `lets?/helps?` as proposed, retain the complaint/data/culture branches, and remeasure before deleting the whole rule.
- risk if applied as proposed: FN↑ on genuine deleted-agent claims

### HumanFpLabels.table + RegexAiTells.F12.command-prompt: remove command prompts from normal scoring
- verdict: ACCEPT-MODIFIED
- counter-evidence: 80 human and zero AI findings; all sampled rows are shell examples.
- modification: Mask fenced/indented command examples and disable this rule at normal; retain only an explicitly opted-in copy/paste house policy.
- risk if applied as proposed: none

### HumanFpLabels.table.directional-ref: decommission directional references
- verdict: ACCEPT-MODIFIED
- counter-evidence: 0.00× README ratio but directional references can still be a navigation/accessibility defect.
- modification: Make normal advisory and retain strict detection for unlinked “above/below” references.
- risk if applied as proposed: breaks navigation-quality contract

### HumanFpLabels.table + AiFnLabels.decommission.first-person-plural: demote first-person plural
- verdict: ACCEPT
- counter-evidence: genre control reverses the aggregate: 0.32× in AI READMEs despite 1.57× overall; all ten samples are intentional project/tutorial voice.
- risk if applied as proposed: none if strict retains it

### HumanFpLabels.table.future-tense: demote future tense
- verdict: ACCEPT
- counter-evidence: 0.27× README ratio; nine of ten samples describe conditional program behavior, not roadmap promises.
- risk if applied as proposed: none if roadmap judgement remains

### HumanFpLabels.table.latinisms: demote Latinisms
- verdict: ACCEPT
- counter-evidence: zero AI README hits versus 27 human; every sample is a true lexical match but normal technical prose commonly uses the terms.
- risk if applied as proposed: none if strict STE retains it

### HumanFpLabels.table.link-text: decommission non-descriptive link text
- verdict: ACCEPT-MODIFIED
- counter-evidence: the audit labels link text “not prose,” but link names are exactly the accessibility surface this rule should inspect.
- modification: Keep the accessibility rule, revise its bad-label vocabulary, and mask destinations rather than visible link text.
- risk if applied as proposed: breaks link-accessibility contract

### HumanFpLabels.table.politeness: decommission politeness
- verdict: ACCEPT
- counter-evidence: 0.57× README ratio and genre-dependent examples such as “Please refer.”
- risk if applied as proposed: none if strict procedural prose retains it

### HumanFpLabels.table.self-reference: decommission self-reference
- verdict: ACCEPT-MODIFIED
- counter-evidence: zero AI findings and sampled navigation such as “previous section” is useful.
- modification: Remove the broad normal rule; retain only broken/vague references in judgement or accessibility checks.
- risk if applied as proposed: none

### HumanFpLabels.table.unclear-antecedent: decommission the antecedent heuristic
- verdict: ACCEPT
- counter-evidence: 0.65× README ratio and the report's examples have immediate recoverable antecedents.
- risk if applied as proposed: none if judgement retains discourse review

### HumanFpLabels.table.versions: decommission version-comparison wording
- verdict: ACCEPT-MODIFIED
- counter-evidence: 0.76× README ratio and only one AI README hit.
- modification: Demote normal wording substitutions; keep checks that detect objectively stale or invalid versions.
- risk if applied as proposed: breaks version-accuracy contract if removed wholesale

### RegexAiTells.F12 + AiFnLabels.decommission.term-rotation-signal: decommission the token signal
- verdict: ACCEPT-MODIFIED
- counter-evidence: aggregate AI density is 46× human, but an isolated token cannot prove rotation and the README control has zero AI hits.
- modification: Remove the lexical firing rule and retain document-level synonym alternation judgement.
- risk if applied as proposed: FN↑ if the judgement remainder is also removed

### HumanFpLabels.table + AiFnLabels.decommission.no-unicode-dash: decommission Unicode-dash presence
- verdict: ACCEPT-MODIFIED
- counter-evidence: 15.22× README ratio, 24× overall density, and zero detector FPs in the relabel.
- modification: Retain; strict/explicit house style `error`, normal advisory, relaxed excluded.
- risk if applied as proposed: FN↑

### HumanFpLabels.table.prose-block: decommission long prose blocks
- verdict: ACCEPT-MODIFIED
- counter-evidence: 0.00× README ratio but scanability remains a genre-specific quality policy.
- modification: Make thresholds advisory at normal and retain strict/reference enforcement.
- risk if applied as proposed: breaks scanability contract

### HumanFpLabels.table.prose-inclusive.exclusive: decommission inclusive-language substitutions
- verdict: ACCEPT-MODIFIED
- counter-evidence: zero AI hits shows it is not an origin discriminator; eight of ten sampled terms remain generic and modernizable.
- modification: Retain as inclusion policy, downgrade normal to advisory, and allow exact historical identifiers/branch names.
- risk if applied as proposed: breaks inclusion contract

### HumanFpLabels.table + RegexSte.F5.multiword-noun-too-long: demote/decommission noun stacks
- verdict: ACCEPT
- counter-evidence: 0.65× README ratio and the current suffix heuristic counts adjectives/gerunds; no executable replacement algorithm was supplied.
- risk if applied as proposed: none at normal; keep strict only after repair

### HumanFpLabels.table.gendered-or-exclusionary-language: decommission the STE inclusion rule
- verdict: ACCEPT-MODIFIED
- counter-evidence: zero AI hits measures corpus vocabulary, not policy validity.
- modification: Retain as advisory inclusion policy with named-person and exact-identifier exceptions.
- risk if applied as proposed: breaks inclusion contract

### HumanFpLabels.table.latin-abbreviation: decommission Latin abbreviations
- verdict: ACCEPT-MODIFIED
- counter-evidence: zero AI README hits and 26 human README hits; this is controlled-English policy.
- modification: Exclude or keep advisory at normal; retain strict STE enforcement.
- risk if applied as proposed: breaks strict STE contract

### HumanFpLabels.table + RegexSte.F6.omitted-conjunction-that: decommission or guard omitted conjunctions
- verdict: ACCEPT-MODIFIED
- counter-evidence: README ratio is 0.57×, but the AI corpus contains a real misspelling of the construction: “verify it genuinely came from us.”
- modification: Keep advisory; require an exact subject/reporting context and supply loss-tested regex before implementation.
- risk if applied as proposed: FN↑

### HumanFpLabels.table.ste-practices.phrasal-verb: decommission STE phrasal verbs
- verdict: REJECT
- counter-evidence: AI README density is 2.28× human README density.
- risk if applied as proposed: FN↑

### HumanFpLabels.table.unclear-demonstrative-this: decommission the bare-demonstrative heuristic
- verdict: ACCEPT
- counter-evidence: 0.51× README ratio and immediate antecedents in the report's own examples.
- risk if applied as proposed: none if judgement retains discourse review

### HumanFpLabels.table + RegexSte.decommission.unclear-pronoun: disable unclear pronouns at normal
- verdict: ACCEPT
- counter-evidence: zero AI hits and 11 human hits; local antecedents defeat the heuristic.
- risk if applied as proposed: none if strict/judgement remains

### HumanFpLabels.table.condition-after-command: decommission condition ordering
- verdict: ACCEPT-MODIFIED
- counter-evidence: README densities are nearly equal, but a true runbook instruction survives as a useful policy target.
- modification: Demote normal until classification is repaired; do not delete the runbook rule.
- risk if applied as proposed: breaks procedural-order contract

### HumanFpLabels.table.instruction-not-imperative: decommission imperative-instruction checks
- verdict: REJECT
- counter-evidence: `HumanFpLabels.md` reports 5/5 TP in already-gated prose; origin discrimination is not the validity criterion for an STE instruction rule.
- risk if applied as proposed: breaks procedural-imperative contract

### HumanFpLabels.table.multiple-instructions-per-sentence: decommission one-action checks
- verdict: REJECT
- counter-evidence: the same report finds 4/5 TP in already-gated prose.
- risk if applied as proposed: breaks one-action-per-step contract

### HumanFpLabels.table.colon-terminates-sentence-for-count: decommission colon counting
- verdict: REJECT
- counter-evidence: AI README density is 1.52× human; RegexSte F4 identifies a parser implementation defect rather than invalid policy.
- risk if applied as proposed: FN↑

### HumanFpLabels.table.semicolon-used: decommission semicolon policy
- verdict: REJECT
- counter-evidence: AI README density is slightly higher (1.07×), and every prose semicolon is a mechanically correct match under STE.
- risk if applied as proposed: breaks strict STE punctuation contract

### HumanFpLabels.table.complex-text-not-in-vertical-list: decommission list-shape detection
- verdict: REJECT
- counter-evidence: AI README density is 2.21× human, the strongest controlled STE separation among the proposed deletions.
- risk if applied as proposed: FN↑

### HumanFpLabels.table + AiFnLabels.decommission.omitted-word-or-contraction: remove contractions from the rule
- verdict: ACCEPT-MODIFIED
- counter-evidence: all ten relabeled rows are true contraction matches; AI overall density is 9.43 versus 5.75/1k and README density is nearly tied.
- modification: Keep contractions enforced in strict STE, advisory at normal, excluded at relaxed; do not rename policy disagreement as detector error.
- risk if applied as proposed: breaks strict STE contraction contract

### HumanFpLabels.table + RegexSte.F2.auxiliary-stacking: delete simple passive-capability duplication
- verdict: ACCEPT-MODIFIED
- counter-evidence: 0.10× README ratio and overlap with passive voice.
- modification: Delete `can|may|must be + participle`; retain genuinely triple-auxiliary constructions such as `will have been`.
- risk if applied as proposed: none

### HumanFpLabels.table.complex-tense: demote complex tense
- verdict: ACCEPT
- counter-evidence: 0.19× README ratio and ordinary technical capability/state prose dominates.
- risk if applied as proposed: none if strict STE retains it

### HumanFpLabels.table.nominalized-action: demote nominalized-action heuristic
- verdict: ACCEPT
- counter-evidence: zero AI README hits and only 2 AI findings overall.
- risk if applied as proposed: none

### HumanFpLabels.table + AiFnLabels.decommission.passive-voice: demote/decommission passive voice
- verdict: ACCEPT-MODIFIED
- counter-evidence: 0.22× README ratio, but all ten relabeled rows are real passives and three are actionable; this is a policy/profile problem plus one regex bug.
- modification: Demote normal, retain strict, preserve unknown/irrelevant-agent exceptions, and do not implement a closed lexicon until its exact contents pass loss testing.
- risk if applied as proposed: breaks strict active-voice contract

### HumanFpLabels.table.spelling: decommission spelling substitutions
- verdict: ACCEPT-MODIFIED
- counter-evidence: zero AI README hits, but dialect normalization is a project locale policy rather than an AI tell.
- modification: Make locale explicit and normal advisory; retain configured-locale enforcement.
- risk if applied as proposed: breaks locale-consistency contract

### RegexAiTells.F1.dead-opener: repair the inline-flag compile failure
- verdict: ACCEPT
- counter-evidence: proposed regex retains both baseline AI hits, “There is” and “There were,” and loses none.
- risk if applied as proposed: none

### RegexAiTells.F2.contrastive-inversion: allow a same-line sentence boundary
- verdict: ACCEPT
- counter-evidence: 0 human and 1 AI match before and after; no TP loss observed.
- risk if applied as proposed: none observed

### RegexAiTells.F3.fake-specificity: exclude version suffix stop words
- verdict: ACCEPT
- counter-evidence: human matches fall 2→1 while the sole AI match remains.
- risk if applied as proposed: none observed

### RegexAiTells.F6.emoji-list-markers: require a Markdown list marker
- verdict: ACCEPT
- counter-evidence: one AI emoji-residue hit is lost, but it is not a list-marker instance; human and AI each lose one match.
- risk if applied as proposed: FN↑ only if no other emoji rule owns non-list residue

### RegexAiTells.F8.rhetorical-question-transition: require a transition cue
- verdict: ACCEPT-MODIFIED
- counter-evidence: removes three human headings but also the real AI product heading “Why fluxcache?”
- modification: Keep cue-led mechanical detection and retain bare rhetorical headings as a judgement candidate.
- risk if applied as proposed: FN↑

### RegexAiTells.F9.optional-plural: remove the `/s` branch
- verdict: ACCEPT
- counter-evidence: human falls 4→2, AI stays 2→2, and no AI TP is lost.
- risk if applied as proposed: none

### RegexAiTells.F5.false-agency: remove `lets/helps`
- verdict: ACCEPT
- counter-evidence: human falls 11→2, AI remains 0, and all bad examples remain covered.
- risk if applied as proposed: none observed

### RegexAiTells.F7.summary-closer: anchor closers to sentence start
- verdict: REJECT
- counter-evidence: drops both AI “Wrapping Up” headings and only one human hit; this is the audit's own regression criterion.
- risk if applied as proposed: FN↑

### RegexSte.F1.passive-voice: replace suffix inference with a closed participle lexicon
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence: no lexicon or regex is supplied; 44 distinct AI matched phrases include low-frequency participles such as “be reattached,” “is acknowledged,” and “be operated.”
- risk if applied as proposed: FN↑ unbounded

### RegexSte.F6.omitted-conjunction: add a sentence-initial imperative guard
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence: no regex is supplied; current AI matches mix real omission with imperative-heading FPs.
- risk if applied as proposed: FN↑ unknown

### RegexSte.F5.noun-stack: stop adjectives/proper names and restrict gerunds
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence: no POS rule, closed noun lexicon, or heading algorithm is supplied; 36 AI findings cannot be replayed against prose.
- risk if applied as proposed: FN↑ unknown

### RegexSte.F3.condition-after-command: enforce declared `text_type`
- verdict: REJECT
- counter-evidence: retains only 3/33 parsed AI matches, removes all three runbook findings, and loses at least five true instructions.
- risk if applied as proposed: FN↑; breaks runbook condition-order contract

## Missed by the audit

1. The decommission decision rule is category-blind. AI-tell discrimination, controlled-English conformance, accessibility policy, typography house style, and origin detection are scored as though they were one binary classifier. `prose-inclusive.exclusive` and spelling can be valuable while having zero AI separation.
2. The label sidecar cannot support the requested ten-row relabel. Several rules have zero `FP-correct-prose` rows, and none has ten. Extrapolated “FP rates” from five editorial judgements are then presented as detector precision.
3. Finding-level random samples are dependent. The exclusive sample contains repeated hits from one paragraph and duplicate tricolon/condition contexts; paragraph-level clustering must be the sampling unit.
4. RegexSte's three largest proposed repairs are not implementation proposals. Without the closed lexicon, guard, or noun-stack algorithm, their claimed expected effect is not falsifiable.
5. Summary-closer narrowing drops more AI hits than human hits and should have been rejected by the audit's own rule.

## Systemic concerns

| rank | alternative conclusion | evidence |
|---:|---|---|
| 1 | Most “FP” findings are policy-profile mismatches, not detector mistakes; demote by genre/profile instead of deleting. | Zero detector FPs in 93 relabeled findings; `README.md:130-131` defines clean as pattern absence only. |
| 2 | Repair scope and sentence classification before re-estimating rule precision. | Lexical rules ignore `text_type` at `engine.py:655-670`; runbook true imperatives default descriptive under `analyze.py:251-271`. |
| 3 | Keep controlled discriminators as advisory/judgement features even when individual human matches are acceptable. | Eight deletion candidates have AI:H README ratios above 1, including 15.22× Unicode dash and 3.26× tricolon. |

## Strongest counter

The audit's central deletion heuristic—sampled editorial FP rate ≥60% plus extrapolated count—does not measure detector precision. Literal contractions, Unicode dashes, passive constructions, Latinisms, and inclusion terms were all present exactly where the detector said they were. Acting on those labels as detector failures would delete valid strict-profile contracts and, for eight rules, measurable README discrimination.