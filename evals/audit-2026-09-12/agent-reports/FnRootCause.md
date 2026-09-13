# FnRootCause — adversarial root-cause audit

## Summary
- The apparent contradiction is mostly a label/rule-shape mismatch, not one missing universal detector: 74 `label-colon-bullet` labels contain **zero** exact `inline-header-list` shapes, and 76/103 AI `title-case-heading` labels are either not headings or are sentence-case/one-word headings under a reproducible case test.
- `normal` is not the main cause for these misses. The relevant deterministic rules are enforced or advisory (and advisory findings are present in the baseline); the real causes are narrow patterns, paragraph/document scope, valid genre use, and labels that overcall ordinary technical prose.
- The two INFERRED formatting thresholds cannot be calibrated from this corpus: there are no runs of 2, 3, or 4+ bold-colon bullets in any corpus. Bold density separates AI only weakly and costs 2/11 human documents at the shipped `>10` threshold.
- Safe changes are therefore narrow phrase additions (with advisory severity), a title-case detector with stopword/punctuation/code handling, and possibly `bold-spray: 20` if zero human document hits is the priority. Do not add broad evaluative/hedge/reassurance token lists.
- The audit's high FN totals remain useful as a label inventory, but its implied “rule nominally covers this span” claim is overstated for label-colon, title-case, tricolon, fake-specificity, puffery, and single-hedge rows.

## Root causes per tell type

Method: I loaded every `AiFnLabels-labels.json` row with `caught_by == []` for the 13 requested types. Samples below are representative and spread by document. For rule shape/tier/scope I inspected the shipped YAML. For paragraph evidence I used the source Markdown block, not just the label's first-line join; this matters because CodeEngine.md F1 reports that multiline projections report the paragraph's first source line.

| tell type | missed | root-cause tally (misses can have more than one cause) | rule that nominally owns the shape |
|---|---:|---|---|
| `label-colon-bullet` | 74 | 74 shape mismatch; 27 are not bullets at all, 15 are unbold bullets, 14 have bold but no colon; 0 tier; 0 exact metric shapes in all 74 | `ai-tells-structure.inline-header-list`, document metric, `>=4`, normal advisory |
| `title-case-heading` | 97 | 64 are headings but sentence case/one-word under the test below; 12 are not headings (table/metadata/prose); 21 are genuine title-case but pattern rejects two words, stopwords, punctuation, digits, or code; 0 tier | `ai-tells-formatting.title-case-heading`, heading scope, normal advisory |
| `puffery` | 19 | 16 broad “marketing-register” judgement/genre claims; 3 lexical/phrase gaps; several are quantified or technical claims and should not be mechanically banned | `prose-discipline.marketing-register` (paragraph judgement, normal enforced), `ai-tells-figurative.promotional-puffery` (narrow travel/biography pattern) |
| `quotable-closer` | 19 | 8 are quoted/testimonial or factual closing prose; 7 are closing frames with no shipped marker token; 4 are sign-off/reassurance candidates; 0 tier | `ai-tells-structure.summary-closer-frames` only owns 11 exact marker tokens, normal enforced; remainder is document judgement, normal advisory |
| `unsupported-evaluative` | 37 | 29 lexical items absent from the 12-token `orwell.unsupported-evaluative` list; 6 are context/technical or quantified claims; 2 are label/rule overlap with existing slop/borderline rules; 0 tier | `orwell.unsupported-evaluative`, tokens, normal enforced |
| `slop-lexicon` | 32 | 20 absent lexical/compound forms; 8 are descriptive technical words (`lightweight`, `pure Rust`, `typed access`, etc.), 4 are context/structure labels; 0 tier | `prose-inflation.slop-lexicon`, prose pattern, normal enforced |
| `filler-opener` | 29 | 18 openers are broad framing or personal narrative outside existing fixed tokens; 7 are ordinary procedural orientation; 4 overlap existing `document-preamble`/`meta-narration` but are line/span mismatches; 0 tier | `ai-tells-structure.meta-narration-frames` and `prose-inflation.document-preamble`, normal enforced; `corporate-analytic-filler-core`, normal enforced |
| `history-narration` | 16 | all are in `independent__release-notes-4-0.md`, a change-comms genre where the rule's own provenance says deltas are expected; pattern also omits `got rewritten`, `replaces that`, and “the other change”; 0 tier | `docs-discipline.history-narration`, prose pattern, normal enforced but relaxed excluded |
| `reassurance` | 15 | 9 subjective/contextual or technically justified (`sufficiently caught up`, `acceptable`, `client proves who it is`); 6 phrase gaps (`straightforward`, `reasonable confidence`, `don't hesitate`, etc.); 0 tier | `prose-scope.unrequested-reassurance`, prose pattern, normal enforced |
| `hedge` | 14 | 14 are single hedges or legitimate uncertainty; `hedge-stack` intentionally requires combinations and `bidirectional-hedge` requires both directions; 0 tier | `prose-inflation.hedge-stack` / `prose-discipline.bidirectional-hedge`, both normal enforced |
| `bold-spray` | 11 | 11 are individual bold spans, not a document density finding; the metric is document scope and `>10/1000`; 1 likely paragraph/metric label overlap, 10 are not proof of density; normal advisory | `ai-tells-formatting.bold-spray`, document metric, normal advisory |
| `tricolon` | 12 | 8 labels are three-item technical enumerations or lead-ins (“three main categories”); 4 are multiword/punctuation shapes outside the regex; 0 tier | `ai-tells-structure.tricolon-abuse-core`, sentence pattern, normal advisory |
| `fake-specificity` | 7 | all are broad marketing/feature claims, not the shipped forms (`over 100+`, `wide range`, `a host of`, etc.); 0 tier | `ai-tells-content-shape.fake-specificity`, prose pattern, normal enforced |

### Evidence from the eight-span samples

- **Label-colon-bullet:** `guide-migration.md:13` is `1. **Renamed keys** — ...`, `pr-description.md:9` is `- **Connection pooling** — ...`, `readme-cache.md:85` is `1. **Embed** — ...`, and `readme-parser.md:73` is `- [ ] Streaming API ...`. The metric's actual `BOLD_COLON_BULLET` shape requires a list marker followed by `**Label:**` (colon inside or immediately after the closing emphasis). None of these four has that shape. `api-docs-webhook.md:50` is ordinary prose ending in a colon, not a list. `adr-queue.md:26` is an unbold bullet. This is not an engine FN.
- **Title case:** `api-docs-webhook.md:1` (`# Webhook Delivery`) and `runbook-failover.md:14` (`## Step 1: Check Replication Lag`) are true title-case candidates that the three-word, no-punctuation regex misses. In contrast, `pr-description.md:1` (`## Summary`), `readme-parser.md:5` (`## Overview`), `readme-cache.md:95` (`## Roadmap`), and `runbook-failover.md:59` (`## Wrapping Up`) do not provide a sentence-case contrast and should not be error candidates. `api-docs-webhook.md:15` (`| Header | Description |`) is a table header, not a heading; `adr-queue.md:3` (`**Status:** Accepted`) is metadata; `release-notes-4-0.md:3` is prose. These account for 12 of the label rows that are not headings.
- **Puffery:** `guide-migration.md:5` (“We're excited to announce ... significant improvement”) is a genuine marketing-register candidate; `marketing-feature-flags.md:13` (“declared as code, reviewed in pull requests, and synced ...”) is a factual, measurable mechanism and is not safe to call puffery mechanically. `marketing-feature-flags.md:15-17` contain network, p99, and deterministic claims; those labels are overbroad even though the surrounding page is promotional.
- **Quotable closer:** `guide-migration.md:76` (“And that's it! ...”) and `api-docs-webhook.md:81` (“That covers the essentials ...”) are plausible close-frame candidates, but `marketing-feature-flags.md:37` and `:40` are blockquoted testimonials and should be excluded by `quotation`; `release-notes-4-0.md:98-102` are a factual release-note close, not a generic closer. The empty `readme-parser.md:78` row is a label artifact.
- **Unsupported evaluative:** `pr-description.md:3` (`significant step forward`), `readme-cache.md:23` (`dead simple`), and `readme-parser.md:13-17` (`zero-copy`, `great errors`, `pure Rust`) are outside the 12 shipped tokens. Some are genuine register candidates, but `zero-copy`, `pure Rust`, and a measured p99/feature claim should not be added as unqualified banned tokens.
- **Slop lexicon:** `readme-cache.md:10-13` (`semantically aware`, `highly configurable`, `lightweight`) and `readme-parser.md:13-17` (`zero-copy`, `typed access`, `great errors`, `pure Rust`) are descriptive feature labels, not interchangeable marketing adjectives. `marketing-feature-flags.md:49` (`Free for 3 seats and 25 flags, forever`) is a claim that needs evidence, not a word-list hit.
- **Filler opener:** `tutorial-mtls.md:3-6` is an orientation paragraph that is necessary to tell the reader what the tutorial does; `blog-skip-locked.md:3` is a personal essay opener. `guide-migration.md:5` and `api-docs-webhook.md:36` are closer to the existing meta-narration/importance rules. A single opener token cannot distinguish these genres.
- **History:** all eight samples are from `release-notes-4-0.md` (`We've been sitting ...`, `two things got rewritten`, `replaces that`, `used to buffer`). This is precisely the genre exception described by `docs-discipline.history-narration` provenance, not evidence that normal enforcement is missing.
- **Reassurance:** `tutorial-mtls.md:56` (“the client proves who it is, too”) is an explanation, not reassurance; `pr-description.md:24` (“reasonable confidence”) is a review claim; `runbook-failover.md:16` is an operational precondition. `guide-migration.md:76` and `api-docs-webhook.md:81` are the only close-frame-like examples in the sample.
- **Hedge:** `adr-queue.md:20` and `readme-cache.md:40` contain one hedge each; the shipped rule explicitly says one hedge is often correct and only flags combinations. Treating all 14 as FNs would reverse the rule's documented contract.
- **Bold spray:** every sampled row is a span (`readme-cache.md:3`, `:9-13`, `readme-parser.md:13-14`), while `bold-spray` fires once per document only when the document density exceeds its threshold. Span labels cannot be joined one-for-one to this rule.
- **Tricolon:** `guide-migration.md:11` (“three main categories of change”) is a lead-in, not a three-item rhetorical list; `marketing-feature-flags.md:11` is a technical service list; `dogfood__README.contaminated.md:184` is a catalogue. The rule's own provenance admits it cannot distinguish technical enumerations. The remaining misses are mostly punctuation/multiword pattern boundaries.
- **Fake specificity:** the seven samples are feature inventory, telemetry, deployment choices, or pricing (“full REST and gRPC APIs”, “multi-tenant”, “3 seats and 25 flags”), not one of the four regex forms. They are label-family confusion, not pattern misses.

### Tiers, scope, and engine checks

- All relevant normal settings were read from YAML. `title-case-heading`, `tricolon-abuse-core`, `bold-spray`, and `inline-header-list` are advisory at normal, not excluded. Advisory findings are present in the baseline, so “advisory means not run” is false.
- The threshold/scope explanation is decisive for formatting: `inline-header-list` is a **document** metric requiring the longest run `>=4`, and `bold-spray` is a **document** metric `>10/1000 words`; an individual label span cannot satisfy either rule by itself.
- Paragraph granularity is a real measurement caveat, not the explanation for these shape failures. Among missed labels, many blocks have unrelated findings at the block's first line, but no exact owning-rule finding. The clearest engine probe from CodeEngine.md F1 (`Clean first line.\njargon is on line two.` reports line 1) means a true lexical finding can be line-joined to the wrong label; therefore counts below are conservative. It does not turn a bold-dash bullet into a bold-colon bullet or a one-word heading into title case.
- The `marketing-register`, `summary-closer-remainder`, and other judgement rules are paragraph/document judgements, not deterministic lexical coverage. Their existence in YAML cannot be counted as a baseline mechanical catch without a judgement execution result. AiFnLabels should not call every such row a deterministic FN.

## Calibration

### Bold-colon bullet runs

I counted source lines using the implementation's `BOLD_COLON_BULLET` regex and grouped maximal nonblank runs; a blank line does not break a Markdown list run, matching `metrics.py:163-180`. Results use parsed `Document.words` (21,208 / 9,865 / 30,488), not raw regex word counts.

| corpus | words | runs of exactly 2 | runs of exactly 3 | runs of 4+ | longest run in any document |
|---|---:|---:|---:|---:|---:|
| human | 21,208 | 0 | 0 | 0 | 0 |
| ai-existing | 9,865 | 0 | 0 | 0 | 0 |
| slopvacced | 30,488 | 0 | 0 | 0 | 1 |

The AI label inventory is a different shape: `**Label** — text` and unbold/list forms dominate. Thus thresholds 2, 3, and 4 have identical measured human cost (0 documents) and identical measured corpus recall (0 documents). There is no empirical basis to lower the shipped `4` threshold; the proposed “x 6” illustration is not represented in this corpus.

### Bold spans per 1,000 words

Using the implementation's `bold_spans_per_1000_words` metric (Markdown markup, parsed prose denominator): weighted densities are human **2.64**, ai-existing **6.32**, slopvacced **2.52**. Human document costs for the `comparison: gt` rule are:

| threshold edit | human documents hit (`value > threshold`) | AI documents hit | slopvacced documents hit |
|---:|---:|---:|---:|
| 5 | 5/11 | 11/17 | 5/22 |
| 10 (shipped) | 2/11 | 6/17 | 3/22 |
| 12 | 2/11 | 5/17 | 3/22 |
| 15 | 1/11 | 3/17 | 2/22 |
| 20 | **0/11** | 2/17 | 1/22 |

The two human hits at `>10` are `markdown-it-py-readme-2020.md` (16.22) and `ripgrep-readme-2021.md` (14.53), both real technical README markup. Recommendation: keep the rule advisory at normal; if a zero-human-document policy is mandatory, change only `threshold: 20` and retain `normal: advisory`. This is a calibration choice, not evidence for normal enforcement.

### Title headings: extraction and case judgement

I extracted ATX headings (`^ {0,3}#{1,6}\s+`) from every file: human **191**, ai-existing **143**, slopvacced **253**. I classified a heading as title case when it has at least two alphabetic/numeric content tokens, every content token is initial-capital/all-caps (allowing a closed stopword list: `a an and as at but by for from in into nor of on or the to up via with without your you is are was were than`), and allowing punctuation, numeric prefixes, and inline-code tokens. One-word headings are sentence-case-equivalent, not evidence of a title-case defect.

| corpus | extracted headings | judged title-case | judged sentence-case/equivalent |
|---|---:|---:|---:|
| human | 191 | 16 | 175 |
| ai-existing | 143 | 30 | 113 |
| slopvacced | 253 | 7 | 246 |

Representative true AI positives: `Webhook Delivery`, `Request Format`, `Signature Verification`, `Retry Schedule`, `Alternatives Considered`, `Quick Start`, `Data Processing and Subprocessor Notice`, `What's Changed`, `Renamed Keys`, `Step 1: Check Replication Lag`, and `Postgres Failover Runbook`. Representative human positives: `Table of Contents`, `Rich Print`, `Using the Console`, `Code of Conduct`, and `Installing Requests and Supported Versions`.

The current pattern requires **three** plain words and rejects stopwords/punctuation/digits/code. A ready replacement (tested against the extraction above) is this `regex` pattern; it requires two capitalized words while allowing the closed stopword/punctuation/code/numeric vocabulary:

```yaml
pattern: >-
  (?x)^(?=(?:.*\b[A-Z][A-Za-z0-9]*(?:[-'’][A-Za-z0-9]+)*\b){2,})
  (?:(?:[A-Z][A-Za-z0-9]*(?:[-'’][A-Za-z0-9]+)*|[A-Z]{2,}|`[^`\n]+`|\d+(?:\.\d+)*|a|an|and|as|at|but|by|for|from|in|into|nor|of|on|or|the|to|up|via|with|without|your|you|is|are|was|were|than|[,:;.!?&()/+-])(?:[ \t]+|$))*$
```

This is still a **warning/advisory** style preference. Humans use title case (16/191 in this sample), so changing it to enforced would create a house-style break; leave `tiers.normal: advisory` and `tiers.strict: advisory`.

## Ready-to-apply changes with measured cost

These are proposed edits, not applied to the repository.

### 1. Title-case pattern (ACCEPT-MODIFIED)

File: `packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml`, rule `title-case-heading`.

Replace only the current `pattern: ^(?:[A-Z][a-z]+\s+){2,}[A-Z][a-z]+$` with the pattern above. Keep:

```yaml
tiers:
  strict: advisory
  normal: advisory
  relaxed: excluded
```

Measured cost: **16/191 human headings** under the explicit classifier; **30/143 AI headings**. The shipped pattern catches 5/143 AI headings and 0/191 human headings, but misses two-word titles and stopword/punctuation forms. The 16 human hits are why this must stay advisory.

### 2. Bold density zero-FP option (ACCEPT-MODIFIED, optional)

File: `ai-tells-agentic.yml`, rule `bold-spray`.

```yaml
threshold: 20
comparison: gt
```

Do not change severity or normal tier. Measured cost: **0/11 human documents**, versus 2/17 AI and 1/22 slopvacced documents. This intentionally trades recall for no observed human document hit; do not present it as a validated universal threshold.

### 3. Do not change `inline-header-list` threshold (REJECT threshold proposal)

Keep:

```yaml
metric: consecutive_bold_colon_bullets
threshold: 4
comparison: gte
tiers:
  normal: advisory
```

Human, AI, and slopvacced corpora have 0 runs of length 2, 3, or 4+; threshold edits are unidentifiable. If the intended tell is `**Label** — text`, that is a **pattern/metric-shape change**, not a threshold change, and needs a separately labelled corpus.

### 4. Narrow summary-closer phrase additions (ACCEPT-MODIFIED; keep advisory alternatives)

The current `summary-closer-frames` token list is the only deterministic closer coverage. If product owners explicitly want these observed sign-off/closer phrases, add only the zero-human-occurrence phrases below and demote the new rule or additions to advisory in consumer/change-comms profiles:

```yaml
tokens:
  - and that's it
  - that covers the essentials
  - more to come
  - happy migrating
  - don't panic
  - if anything goes wrong
  - we shipped it
```

Human probe counts for each exact phrase: **0** in 21,208 human words. Do **not** add `built with` (3 human occurrences) or `thanks to` (1); those are ordinary technical/documentary phrases. Keep quotation exceptions; the two testimonial rows are not safe targets.

### 5. Narrow meta-narration opener additions (ACCEPT-MODIFIED)

For `ai-tells-agentic.yml` `meta-narration-frames`, add only the clearly navigational forms:

```yaml
  - in this tutorial
  - this runbook walks you through
```

Human probe count: **0** exact occurrences for each in the human corpus. Keep normal enforced only if the intended genres exclude tutorial/runbook orientation; otherwise use `normal: advisory`, because `tutorial-mtls.md:3-6` is necessary orientation and is currently labelled filler.

### 6. Do not add broad evaluative/slop tokens (REJECT)

No ready token-list addition survives as an unconditional normal/error rule. Human probe counts for the most tempting additions were:

| candidate | target list | missed-label spans | human occurrences | decision |
|---|---|---:|---:|---|
| `semantically aware` | slop | 1 | 0 | reject: descriptive feature property |
| `highly configurable` | slop | 1 | 0 | reject: technical property |
| `lightweight` | slop | 1 | 0 | reject: ordinary performance/size descriptor |
| `great errors` | slop | 1 | 0 | reject: phrase is odd but not a stable token |
| `pure Rust` | slop/evaluative | 1 | 0 | reject: language implementation fact |
| `production-ready` | slop/evaluative | 1 | 0 | advisory-only candidate; no human hit, but genre-dependent |
| `insidious` | unsupported-evaluative | 1 | 0 | advisory-only candidate; no human hit, but evidence/incident context matters |
| `mission-critical` | unsupported-evaluative | 1 | 0 | advisory-only candidate; no human hit, but safety/ops context matters |
| `high-throughput` | unsupported-evaluative | 1 | 0 | reject as unconditional token: technical claim can be benchmarked |
| `significant` | unsupported-evaluative | 1 | 2 | reject; human hit |
| `important` | unsupported-evaluative | 1 | 15 | reject; human hit |
| `free` | puffery | 1 | 3 | reject; ordinary pricing/factual use |
| `built for` | puffery | 1 | 1 | reject; ordinary construction/use |
| `most important` | reassurance/filler | 2 | 6 | reject; human hit |
| `note that` | filler | 1 | 18 | reject; human hit |
| `unfortunately` | filler | 2 | 2 | reject; human hit |
| `make absolutely sure` | reassurance | 1 | 1 | reject; human hit |
| `built with` | closer | 1 | 3 | reject; ordinary attribution |
| `thanks to` | closer | 1 | 1 | reject; ordinary attribution |

For `puffery`, `marketing-register` already asks the right paragraph-scoped question (number/benchmark/limit/version/citation); its judgement should not be replaced by a token dump. For `reassurance`, add no normal/error tokens: `should be straightforward`, `reasonable confidence`, `acceptable`, and `sufficiently caught up` all have legitimate operational uses even though they have 0 human hits in this small corpus.

### 7. No history/hedge/tricolon/fake-specificity edit (REJECT)

- `history-narration`: do not broaden normal enforcement in release notes; 16/16 misses are in a genre where the delta is the subject. If broadening for consumer docs, add `got rewritten|replaces? (?:that|the old)|the other change` only under a genre-scoped profile, not the global rule.
- `hedge`: do not add single hedge tokens. The shipped `hedge-stack` intentionally requires combinations, and the sample's 14 misses are single/legitimate hedges.
- `tricolon`: do not broaden the regex without a technical-enumeration exception; 8/12 missed labels are technical lists/lead-ins and the rule's own provenance documents this FP class.
- `fake-specificity`: do not add `full`, `multi-tenant`, `every`, or other feature inventory words; all seven missed rows are not the four shipped fake-quantifier forms.

## Labels I judged wrong

The following are labels judged wrong under the contract “this span is a tell that the named nominal rule should cover,” not claims that the prose is perfect:

- **Title case: 76/103 labels** are not true title-case targets under the explicit classifier: 64 headings are sentence-case/equivalent or one-word headings, and 12 are not headings (table header, ADR metadata, or prose). Examples: `## Summary`, `## Context`, `## Conclusion`, `## Overview`, `## Roadmap`, `| Header | Description |`, and `**Status:** Accepted`.
- **Label-colon bullets:** all 74 missed spans are wrong for `inline-header-list`'s exact shape. The labels describe a broader “label + explanation” or bold-dash convention, while the YAML metric only recognizes `**Label:**` bullets in runs. This is a taxonomy mismatch, not 74 metric FNs.
- **Fake specificity:** all 7 missed labels are wrong for the shipped rule's four forms. “Full REST and gRPC APIs”, “multi-tenant”, “RBAC”, and pricing/features are not `over 100+`, `N+ different`, `a wide/broad range`, or `a host of`.
- **Tricolon:** at least 8/12 are wrong as rhetorical-tricolon labels: `three main categories`, protocol/service inventories, and catalogue rows are technical structure. The remaining four are pattern-boundary candidates, not proof that all lists should fire.
- **History narration:** 16/16 are in release notes/change comms. The rule's provenance explicitly says this genre makes the assumption wrong by construction; these labels should be genre-negative or excluded from the normal consumer-doc ground truth.
- **Hedge:** 14/14 are single or contextually honest hedges. A single `may`, `could`, `while`, or `depending on` is not the shipped `hedge-stack` or `bidirectional-hedge` contract.
- **Bold spray:** 11/11 are span labels. A span cannot be adjudicated against a document-level `>10/1000` metric. The label needs a document id/density label, not a per-span FN row.
- **Reassurance:** at least 9/15 are explanatory or operational (`sufficiently caught up`, `acceptable`, `client proves who it is`, `reasonable confidence`), not unrequested reassurance.
- **Puffery:** at least 5/19 are quantified/technical mechanisms (`100 ms p99`, deterministic bucketing, network path, telemetry, feature inventory). Promotional surrounding context does not make every sentence puffery.
- **Quotable closer:** at least 8/19 are quotation, factual release-note, or technical close; the empty `readme-parser.md:78` row is invalid evidence.

## Verdicts

### AiFnLabels.F1: Add judgement coverage for evidence-backed promotional claims, customer proof, and unsupported superlatives
- verdict: ACCEPT-MODIFIED
- counter-evidence: `orwell.unsupported-evaluative` is already normal enforced and `prose-discipline.marketing-register` is already normal enforced at paragraph scope. The 37 unsupported-evaluative misses are mostly absent tokens plus label/rule overlap; `marketing-feature-flags.md:13-17` contains measurable mechanism claims and should not be called a FN. The phrase/token probe found `significant` in 2 human occurrences and `important` in 15.
- modification: Keep the paragraph judgement; add only a small, genre-scoped/advisory phrase set (`production-ready`, `insidious`, `mission-critical`) after independent review. Do not add a broad evidence-backed promotional detector or tokenise feature facts.
- risk if applied as proposed: FP↑

### AiFnLabels.F2: Add judgement rules for meta-narration, summary closers, and reassurance
- verdict: ACCEPT-MODIFIED
- counter-evidence: Existing `meta-narration-frames`, `document-preamble`, `summary-closer-frames`, `summary-closer-remainder`, and `unrequested-reassurance` already own these families. The missing rows include quoted testimonials, release-note facts, necessary tutorial orientation, and one-word/metadata labels. Human probe cost is 0 for the narrow phrases `and that's it`, `that covers the essentials`, `more to come`, `happy migrating`, `don't panic`, `if anything goes wrong`, and `we shipped it`; broad alternatives such as `built with` and `thanks to` occur in human prose.
- modification: Add only the narrow navigation/sign-off phrases above, keep quotation exceptions, and make reassurance additions advisory or genre-scoped rather than normal error tokens.
- risk if applied as proposed: FP↑

### TellsCoverage.Summary: Most named candidate families are already covered; add only three new rules
- verdict: REJECT
- counter-evidence: The summary compares broad editor labels with narrow mechanical rules. There are 74 label-colon rows but 0 exact bold-colon metric shapes; 97 title labels but only 27 of those labelled rows are true title-case under the stated test; and 12 tricolon rows are technical lists/lead-ins. This makes “already covered” and “uncovered FN” incomparable without a span-shape join.
- modification: Re-run coverage by rule contract: exact shape, scope, threshold, tier, paragraph-granularity join, then a separate judgement-label table. Keep the sign-off and whether-frame proposals as low-confidence, advisory, corpus-specific candidates only.
- risk if applied as proposed: FP↑

### CodeEngine.F1: Preserve source coordinates through multiline Markdown projection
- verdict: ACCEPT
- counter-evidence: This is the one engine finding that can explain real residual undercount after shape filtering: the direct probe reports a line-2 token at line 1, and 492 human multiline blocks are affected. It cannot explain headings, document metrics, or labels whose source shape never matches.
- modification: Preserve spans/absolute offsets before changing rule inventories; re-run label joins at paragraph granularity first.
- risk if applied as proposed: none

### CodeEngine.F5: Honor sentence, paragraph, and document scopes in native lexical execution
- verdict: ACCEPT-MODIFIED
- counter-evidence: The scope defect is real, but the requested families' main misses are not all scope misses: `inline-header-list` and `bold-spray` intentionally use document scope, while title-case uses heading scope and history/slop use prose scope. The report should not attribute every missed label to this defect.
- modification: Fix scope routing, then re-measure only rows whose exact pattern matches inside the intended span; do not broaden labels first.
- risk if applied as proposed: breaks contract X (scope-specific findings can change)

## Systemic concerns

1. **Label/rule ontology mismatch.** `label-colon-bullet`, `title-case-heading`, `tricolon`, `fake-specificity`, `puffery`, and `hedge` are broad editorial categories, while the YAML rules intentionally encode narrow mechanical cores plus separate judgements. A raw labeled-span recall number cannot evaluate those rules.
2. **Wrong unit of analysis.** Span labels are joined to document metrics (`bold-spray`, `inline-header-list`) and paragraph/document judgements. The proper unit is document or block, with counts and thresholds, not one label row per span.
3. **Genre contamination.** All 16 missed `history-narration` labels are release-note prose; the audit calls a rule FN where its own provenance says that genre is an exception. Marketing/README/tutorial/runbook/ADR/spec/legal documents are also mixed without a profile-stratified denominator.
4. **Judgement results are not deterministic baseline findings.** A judgement rule's YAML presence is not evidence that the CLI ran or emitted it. Reports need the judgement engine's input/output and a separate recall metric.
5. **Line-level joins undercount multiline matches.** CodeEngine F1 is a real confounder. Any claim of exact per-tell recall must be recomputed at paragraph granularity before changing rules.
6. **Small and non-independent threshold calibration.** There are zero bold-colon runs in all three corpora, so the threshold is unidentifiable. Bold density is driven by Markdown house style: 2/11 human documents exceed 10, and the slopvacced corpus has a 24.19/1000 document. A zero-human threshold of 20 is a corpus-specific operating point, not a general calibration.
7. **Human “FP” counts are not all errors.** The human corpus contains legitimate title-case headings, bold markup, technical adjectives, and release-like prose. Those observations should be reported as house-style costs, not automatic false positives.
