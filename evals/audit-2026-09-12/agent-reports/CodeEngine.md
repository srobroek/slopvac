## Summary
Checked the loader, Markdown projection, segmentation, native checker dispatch, metric arithmetic, score gates, and suppression parser against the documented contracts and direct baseline-package probes.
The largest correctness gaps are 492 human-corpus multiline blocks losing source coordinates, incomplete STE tokenization/sentence segmentation, and valid HTML/MDX prose being omitted.
Scoring is monotone in finding removal, but category `weight = 0` is not informational as documented because the unweighted whole-document score can still fail `min_score`.
The 11-file human corpus completed in 1.168 s (`--no-vale`); no profiler run was warranted.

## Findings

### F1: Preserve source coordinates through multiline Markdown projection
- surface: `packages/slopvac-lint/src/slopvac/analyze.py:516-526`, `engine.py:642-650`
- kind: defect
- evidence: `_inline_prose` converts `softbreak`/`hardbreak` to a space (`analyze.py:334-336`), so the parser cannot take its `pieces` branch and writes the entire paragraph to its first source line. Probe input `Clean first line.\njargon is on line two.` produced `prose_lines == ['Clean first line. jargon is on line two.', '']`; a token rule for `jargon` reported `(line=1, column=19)` although the token is at line 2, column 1. Across the 11 human files, 492 multiline blocks span multiple source lines while their projection has content on only one line (for example `ripgrep-readme-2021.md:3-9`).
- proposal: make the parsed prose projection carry source spans, not flattened strings: retain each inline child's source line/column (or align rendered inline text back to the raw block), store sentence fragments with absolute offsets, and have `_lines_for_scope` yield span objects. Blast radius: `analyze.py` (`Sentence`, `Block`, `_inline_prose`, `parse`), `engine.py` (lexical and metric finding locations), and report adapters that consume `Finding` columns.
- expected effect: correctness and actionable locations; both FP/FN triage on all three corpora, measured directly on the human corpus.
- confidence: high

### F2: Implement the documented STE tokenization before sentence splitting
- surface: `packages/slopvac-lint/src/slopvac/analyze.py:217-307`; `packages/slopvac-lint/docs/metrics.md:27-160`
- kind: defect
- evidence: direct probes against the baseline package: `count_words('Step 3. Restart the worker.') == 5` (documented result is 3 after deleting `Step 3.`); `(1) Restart the worker.`, `A. Restart the worker.`, and `iv. Restart the worker.` each returned 4 instead of 3; `New York City deploys now.` returned 5 although the documented proper-name phase collapses `New York City`; `count_words("Don't run the team's failed build now.") == 6` instead of 7 because `QUOTED_SPAN` pairs the two apostrophes into a false quotation. The segmentation probe `A sentence (with another sentence. And more words inside). End.` split inside the parenthetical into three ordinary sentences, despite docs/metrics.md requiring collapsed spans to be non-terminators and the parenthetical content to be a separate second measurement. A heading plus this paragraph counted 14 words, while the documented heading/proper-name/parenthetical phases are absent.
- proposal: replace the independent regex substitutions with the ordered phase pipeline specified in docs/metrics.md: complete Phase 0 (`Step`, parenthesized markers, uppercase and Roman markers), tokenize inline-code/identifiers, use quote parsing that distinguishes apostrophes, collapse configured titles/proper names, extract parenthetical child sentences, then split the masked outer text. Blast radius: `analyze.py`, `metrics.py` consumers, and the Vale counter compiler/oracle in `compile_vale.py`.
- expected effect: both; FP↓ for sentence caps and denominator-driven rules, FN↓ where undercounting hides violations. Step headings occur repeatedly in `ai-existing/independent__tutorial-mtls.md` and `unguided__runbook-failover.md`; proper names are abundant in the human corpus.
- confidence: high

### F3: Do not discard valid HTML blocks and MDX/JSX prose
- surface: `packages/slopvac-lint/src/slopvac/analyze.py:467-510`
- kind: fn-gap
- evidence: the Markdown walker handles `inline`, fences, tables, headings, paragraphs, quotes, and lists, but has no `html_block`/`html_inline` projection. `parse('x.md', '<div>\nVisible prose here.\n</div>\nAfter.')` returned no blocks and four empty prose lines; `<Callout>\nVisible prose here.\n</Callout>\nAfter.` did the same. In the human corpus, `black-readme-2021.md:3` (`<h2 align="center">The Uncompromising Code Formatter</h2>`) is raw visible prose but projects to an empty line; 14 same-line HTML elements with visible text were omitted across the human corpus, including `rich-readme-2020.md:142` `<summary>Log</summary>`.
- proposal: feed CommonMark `html_block` and `html_inline` token content through the existing `_HtmlTextExtractor`, preserving their token maps; treat known non-prose tags with `_SKIP_HTML_TAGS`, and treat JSX/MDX element bodies as prose while masking attributes/expressions. Blast radius: `analyze.py` only if the source-span abstraction from F1 is used.
- expected effect: FN↓ on human Markdown with embedded HTML and on MDX/JSX documentation.
- confidence: high

### F4: Mask all CommonMark inline-code delimiter lengths in markup metrics
- surface: `packages/slopvac-lint/src/slopvac/analyze.py:35,190-208`; `metrics.py:190-200`
- kind: fp-risk
- evidence: `Document.markup_text()` reparses code with `INLINE_CODE = re.compile(r"`[^`\n]+`")` rather than using markdown-it tokens. Probe `Use ``a` — b`` safely now.` projected markup as `'Use `  — b`` safely now.'` and `dash_per_1000_words == 333.33`; `Use ``a` **not bold** b`` safely now.` produced `bold_spans_per_1000_words == 333.33`. Both dash and bold text are inside valid double-backtick code spans and must be masked. Single-backtick and fence/indented-code controls were correctly masked.
- proposal: build `markup_text` during the markdown-it token walk, replacing every `code_inline` child with an equal-line placeholder regardless of delimiter length; delete the separate `INLINE_CODE` regex path. Blast radius: `analyze.py` and the two markup metrics in `metrics.py`.
- expected effect: FP↓ for `ai-tells-formatting.em-dash-density` and `bold-spray` on all Markdown corpora.
- confidence: high

### F5: Honor sentence, paragraph, and document scopes in the native lexical engine
- surface: `packages/slopvac-lint/src/slopvac/engine.py:642-650`
- kind: code-bug
- evidence: `_lines_for_scope` special-cases only `raw` and `heading`; every other scope receives non-empty physical `prose_lines`. A direct native `scope=sentence`, pattern `^Second`, input `First sentence. Second sentence.` returned no finding, though applying the pattern to each parsed sentence must match the second sentence. The same implementation means a `scope=document` pattern can never cross a physical line. Vale normally takes many lexical rules, but any custom or Vale-rejected lexical rule falls back to this native path, so its declared scope changes behavior silently.
- proposal: centralize scope iteration on `Document.spans(scope)` yielding real sentence, paragraph, document, heading, prose-line, or raw spans with locations; make both native lexical execution and Vale result mapping consume that seam. Blast radius: `analyze.py`, `engine.py`, and `compile_vale.py` scope mapping tests.
- expected effect: both, especially custom/Vale-rejected rules; correctness on all corpora.
- confidence: high

### F6: Report malformed suppression annotations instead of ignoring them
- surface: `packages/slopvac-lint/src/slopvac/suppression.py:18-21,70-139`
- kind: defect
- evidence: `SUPPRESSION` only iterates comments matching its entire narrow grammar, so malformed attempts never enter validation. Actual-engine probes: `<!-- slopvac-allow: rule=probe.x reason=not valid -->` and `<!-- slopvac-allow: rule=probe.x,probe.y reason=term -->` each emitted only the underlying `probe.x` finding and no `meta.invalid-suppression`. The recognized control `reason=wrong` emitted both `meta.invalid-suppression` and the underlying finding. Thus typos/spaces/multi-rule attempts bypass the promised “reason off the list is reported” audit signal.
- proposal: first detect every `<!-- slopvac-allow:` prefix, then parse its payload; emit `meta.invalid-suppression` for syntax errors with the accepted single-rule grammar (or explicitly add a comma-separated multi-rule grammar and validate every rule/reason). Keep malformed annotations non-suppressing. Blast radius: `suppression.py` and suppression help text in README/docs if multi-rule support is chosen.
- expected effect: correctness; malformed annotations become visible on every corpus rather than silently inert.
- confidence: high

### F7: Match allowlist phrases to the occurrence, not a nearby window
- surface: `packages/slopvac-lint/src/slopvac/engine.py:671-678`
- kind: fn-gap
- evidence: for token `iron` with allowlist `iron resolution`, input `iron resolution is fixed.` correctly emitted none. But `iron fails near iron resolution.` also emitted none: the first, disallowed `iron` was suppressed merely because the allowed phrase occurred within the fixed ±30-character window. Moving the allowed phrase more than 30 characters away restored the finding at column 1.
- proposal: compile allowlist entries as literal spans for the line and suppress a match only when its `[start,end)` is contained by an allowlisted span; remove the proximity window. Blast radius: `engine.py` only, plus loader example verification if examples should exercise allowlists.
- expected effect: FN↓ for rules with phrase allowlists; observed on `orwell.stale-figure` semantics and applicable to the human/AI corpora.
- confidence: high

### F8: Make category weight zero truly informational in the whole-document score
- surface: `packages/slopvac-lint/src/slopvac/score.py:142-167,190-230,273-277`; `config.py:104-109`
- kind: defect
- evidence: `CategorySettings.weight` says “0 scores the category as informational.” Probe: 100 words, one warning in category `probe`, `weight=0`, global budget 3, and `min_score=99` produced category score 95.0, overall score 95.0, `passed=False`, reason `score 95.0, minimum 99.0`. `_weighted_category_score` excludes weight-zero categories, but `_whole_document_score` and `_blocking_density` sum every finding without category weights, so the same informational category still lowers and gates the document.
- proposal: pass resolved category weights into whole-document scoring and global blocking density, excluding weight-zero categories consistently (or reject `weight=0` as unsupported and change its documentation). Blast radius: `score.py`, its callers in `pipeline.py`, and summary scoring if run-level aggregation recomputes density.
- expected effect: correctness; prevents configured informational categories from failing `min_score`/global density gates.
- confidence: high

### F9: Use one word-count denominator for scores and document metrics
- surface: `packages/slopvac-lint/src/slopvac/metrics.py:93-125,190-200`; `analyze.py:177-179,217-252`
- kind: architecture
- evidence: scores use `Document.words` (STE `count_words` over sentences), while six document metrics use `_prose_words`, a second tokenizer `re.findall(r"[A-Za-z']+", text)`. Probe `Perhaps "one two three four".` has `Document.words == 2` but `hedge_per_100_words == 20.0`, proving a denominator of 5 rather than 2. `**Bold** and the quoted phrase "one two three four".` has `Document.words == 6` but `bold_spans_per_1000_words == 111.11`, proving a denominator of 9. The same document therefore has incompatible meanings for “per 100/1000 words.”
- proposal: make `Document` expose the canonical counted-token stream (and optionally a separate linguistic-token stream for syllable/POS heuristics); density metrics must divide by `Document.words`, while metrics needing lexical tokens consume the explicitly named linguistic stream. Delete `_prose_words` as a denominator provider. Blast radius: `analyze.py`, `metrics.py`, and metric documentation.
- expected effect: correctness and both FP/FN near document-metric thresholds on all corpora.
- confidence: high

### F10: Replace string-and-enum fan-out with checker and metric registries
- surface: `packages/slopvac-lint/src/slopvac/model.py:122-240`, `engine.py:550-590,629-637,713-864`, `metrics.py:55-89,204-225`, `rules.py:102-135`
- kind: architecture
- evidence: a new rule kind requires synchronized edits to `RuleKind`, payload ownership validation, loader example verification, native dispatch, Vale compilation, and reference rendering. Metrics duplicate the same inventory in `NATIVE_METRICS`, `_DOCUMENT_METRICS`, and the `_run_metric` string `if/elif`; `document_metric` returns `0.0` for an unknown name while `unimplemented_metrics` separately tries to catch it. The model also declares `minimum_severity` twice in `config.py:88-101`, evidence that this fan-out is already hard to audit. `RuleSet.by_id` rebuilds/linearly scans `rules` on each lookup (`rules.py:42-52`), including once per merged Vale finding.
- proposal: define a `RuleExecutor` registry keyed by kind and a `MetricSpec` registry keyed by metric name, where each entry owns payload validation, supported scopes, execution, and Vale capability; derive inventories from registry keys and make unknown dispatch impossible. Cache a qualified-id map inside `RuleSet`. Blast radius: `model.py`, `rules.py`, `engine.py`, `metrics.py`, `compile_vale.py`, and `reference.py`; remove the duplicate `minimum_severity` declaration in `config.py` during the cutover.
- expected effect: correctness and maintainability; prevents silent omissions when adding a kind/scope/metric. Runtime benefit is secondary because the measured corpus run is already fast.
- confidence: high

## Decommission candidates
- `analyze.INLINE_CODE` and regex-based `Document.markup_text()` masking: remove; it demonstrably leaks double-backtick content into two formatting metrics.
- `metrics._prose_words` as a density denominator: remove; it disagrees with `Document.words` on quoted/code/identifier collapses.
- `Engine.document_metric`: remove the pass-through wrapper at `engine.py:923-930`; callers already import `metrics.document_metric` and the wrapper adds no seam.
- `RuleSet.by_id` linear scan and repeatedly rebuilt `RuleSet.rules` list: replace with cached maps/lists; low performance priority, but it simplifies the interface.
- Duplicate `CategorySettings.minimum_severity` declaration at `config.py:88-101`: delete one.

## Checked and fine
- Fenced blocks with backticks or `~~~` and four-space indented code were masked in direct probes; their contents did not enter prose sentences.
- Single-backtick and ordinary double-backtick inline code was masked correctly by markdown-it for prose rules.
- Link reference definitions were omitted while visible reference-link labels remained prose (`[label]: URL` plus `See [label].` projected only `See label.`).
- Version numbers, decimals, `e.g.`, `p.m.`, and `Dr.` did not create false sentence splits in the tested capitalized-following-sentence cases (the abbreviation guard does unnecessarily lowercase `Dr.`).
- Regex compilation is cached for the lifetime of each `Engine`; `lint_one` constructs an engine per document, but the 11 human files completed in 1.168 s, so profiling was not justified.
- Scoring hand reproduction: with 200 words, 1 error + 2 warnings + 3 suggestions gives blocking weight 2.0, blocking density 1.0, base `100 - 30*(1/3) = 90`, suggestion density 1.5 and penalty `15*(1.5/6)=3.75`, observed score 86.2 after rounding; raw density was 3.0/100w. Removing any finding from the inspected formula cannot lower either score branch.
- Short-document behavior matched implementation: 20 words + one warning reports both densities as 0, scores from absolute weight (`100 - 0.5*20 = 90`), and passes when count/min-score gates do not reject it.
- Errors count 1.0 and warnings 0.5 toward score/global and category density gates; suggestions count only toward the bounded 15-point score penalty and cannot alone trigger `min_score` because `_failure_reasons` requires an error or warning.
- `match_all_caps` is applied after regex matching and before finding creation; explicit `true` bypasses the default technical-token exemption.
