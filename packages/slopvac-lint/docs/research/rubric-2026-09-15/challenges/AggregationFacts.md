# Measured facts for aggregation claims C5 and C6 (parent-run, read-only)

Checkout: /Users/sjors/tmp/worktrees/slopvac/research-rubric-review-20260915 @ df7ba4412387c474dc8ef646a8d594dc44c1c7eb
Scripts and raw output: /Users/sjors/tmp/slopvac-rubric-research/work/corpus/{cooccurrence.py,toppairs.py,inventory.py,cooccurrence.json}

## Score composition (packages/slopvac-lint/src/slopvac/score.py)
- SEVERITY_WEIGHT error 1.0 / warning 0.5 / suggestion 0.1 (score.py:38-43)
- _score_from_density: 100 -> 70 linearly up to budget; 70 -> 0 to ZERO_SCORE_MULTIPLE(4.0) x budget (score.py:85-105)
- MAX_SUGGESTION_PENALTY = 15.0, SUGGESTION_PENALTY_FULL_AT = 6.0/100 words (score.py:58-82). Comment: on design-doc-outbox.md suggestions were 76 of 152 weight units; all 8 independent-corpus documents scored 0.0 at normal and strict while scoring 87-99 at relaxed. 15 chosen so "a document clean of errors and warnings but dense with suggestions lands near 85 ... and cannot cross the shipped 70.0 minimum."
- Document score = base_score - suggestion_penalty, floor 0 (score.py:172-196)
- Profile thresholds (config.py:736-747): strict max_total_per_100_words=1.5, max_errors=0, min_score=85; normal 3.0 / 0 / 70; relaxed 8.0 / None / None. README override in slopvac.toml:91-96 sets min_score=0.
- Arithmetic consequence: a document with zero mechanical findings scores 100. Deduct the design's JUDGEMENT_MAX_PENALTY=20 -> 80, which is BELOW strict min_score 85. With the suggestion penalty also spent: 100-15-20 = 65 < normal min_score 70. So "judgement never gates alone" holds only at normal and only when suggestions are absent; at strict a 20-point cap fails a mechanically clean document by itself. Non-gating caps: strict <= 15 - suggestion_penalty (i.e. 0 when both are spent), normal <= 30 - 15 = 15.

## Rule inventory (inventory.py)
21 YAML files (multi-document), 230 rules, 25 categories; 65 kind=judgement rules in 14 categories (11 zero-judgement categories); scope paragraph 26 / sentence 21 / document 17 / none 1 (orwell); severity suggestion 58, unset 6, error 1 (ste-safety); criterion text (name+question+fix+message) mean 363 chars, max 1007, total 23,600 chars; judgement_question alone mean 184, max 691. Tier selection: 65 at strict, 65 at normal, 24 at relaxed. Design doc §0 numbers match except "prose 1" is a rule with no scope field.

## Co-occurrence (cooccurrence.py; slopvac lint --profile strict --format json with the repo slopvac.toml; document-scope findings at line 1 without matched text excluded)
Two corpora:
A. repo_markdown: 16 documents (config exclusions applied), 12,339 words, 429 findings (24 error / 11 warning / 394 suggestion), 3.48 per 100 words.
B. session_model_prose: 98 model-authored markdown files from ~/.omp/agent/sessions/*/*/local (>2KB), 220,336 words, 19,490 findings (3,376 / 2,272 / 13,842), 8.85 per 100 words. Unguided model prose, never tuned against these rules.

Paragraph units (blank-line delimited), rules with >= 3 unit hits, pairwise Jaccard and phi:
- B paragraphs: 5,056 units, 3,137 with findings, 10,805 span findings, 88 rules; within-category pairs n=266: Jaccard mean 0.0137 median 0 p90 0.0415 max 0.125; phi mean 0.0263 median -0.0011 p90 0.0783 max 0.297. Across-category pairs n=3,562: Jaccard mean 0.0142 median 0 p90 0.0410 max 0.972; phi mean 0.0267 median -0.0008 p90 0.0847 max 0.985.
- B 10-line windows: within phi mean 0.0192 p90 0.0704 max 0.297; across phi mean 0.0214 p90 0.0775 max 0.981.
- A paragraphs: 585 units, 204 with findings, 353 span findings, 21 rules; within n=10 phi mean 0.049 max 0.153; across n=200 phi mean 0.035 p90 0.176 max 0.326.
Conclusion of the numbers: within-category and across-category co-occurrence are statistically indistinguishable in mean/median/p90; the extreme dependence is ACROSS categories.

Top pairs by phi (B, rules with >= 10 units), phi / jaccard / both / |a| / |b|:
- 0.985 / 0.972 / 139 / 141 / 141  prose-craft.unclear-antecedent  x  ste-practices.unclear-demonstrative-this  (different categories, same phenomenon)
- 0.539 / 0.293 / 12 / 12 / 41  prose-discipline.frozen-verb  x  ste-verbs.nominalized-action
- 0.460 / 0.216 / 32 / 148 / 32  docs-discipline.status-language  x  prose-craft.annotations
- 0.445 / 0.253 / 270 / 286 / 1050  prose-craft.sentence-length  x  ste-descriptive.sentence-too-long-descriptive
- 0.411 / 0.189  prose-format.prose-block  x  ste-descriptive.paragraph-too-many-sentences
- 0.365 / 0.237  prose-craft.sentence-length  x  prose-discipline.run-on
- 0.289 / 0.182  prose-craft.latinisms  x  ste-practices.latin-abbreviation
Highest WITHIN-category pair: 0.192 ste-procedural.condition-after-command x ste-procedural.sentence-too-long-procedural.

Gate trip counts (B paragraphs): units with >= 3 findings (old gate) 1,899; with >= 3 findings from >= 2 distinct categories (new gate) 1,821 (96% of old); units with >= 3 findings from ONE category 900. Cluster categories most often present: ste-punctuation 1,276; ste-descriptive 938; prose-format 835; ste-verbs 830. (A paragraphs: old 44, new 43.)
Most frequent rules (B): ste-punctuation.semicolon-used 5,337; prose-format.no-unicode-dash 2,244; ste-descriptive.sentence-too-long-descriptive 1,601; ste-verbs.passive-voice 1,550.

Limits: these are MECHANICAL findings (the judgement layer is not implemented), so they measure rule-category dependence in the ruleset as a proxy for the judgement rules' category structure; ai-tells-structure judgement rules are not in the data. Corpus B is model prose, so dependence patterns of human prose are not measured.
