# Slopvac judgement rubric v1: adversarial review

Research date: 2026-09-15. Source commit: `df7ba4412387c474dc8ef646a8d594dc44c1c7eb` (worktree branch `research/rubric-review-20260915`, based on `slopvac-v3-candidate`). Design under review: `rubric-design.md` (531 lines, session artefact). Scope: prose-quality defects only; no provenance or authorship detection was considered, proposed, or accepted.

Method. Fourteen numbered claims (C1-C14, listed below) were attacked in eight briefs: six literature challenges (dimensions, scale, gates, protected classes, composition, versioning), one repository challenge that built counter-cases from real prose, and one aggregation challenge fed with measurements taken on the checkout. Every verdict below cites a URL, a `path:line`, or a measurement. Claims with neither support nor refutation are marked UNSUPPORTED. The accepted contract is `rubric-contract.json` beside this file.

## 1. Verdict table

| ID | Claim (design section) | Verdict | One-line reason |
|---|---|---|---|
| C1 | One global spine plus per-category packs; no per-rule rubric (§1) | AMEND | MQM's stable typology plus selected profiles supports a shared spine, but packs are a batching unit, not a substitute for rule semantics: same-category rules already ask different questions (`ai-tells-agentic.yml:46-72`, `ste-practices.yml:12-63`). Rule records keep criterion, discriminator, admission, protects, evidence contract, ceiling, transitions. |
| C2 | Four independent 0-3 dimensions; per-rule mask with HARM/REPAIR constants (§2, §8) | AMEND | Keep four separately reported checks; drop the independence premise (trait correlations >= .60 in ASAP++, .84-.96 in TOEFL) and drop category-level HARM/REPAIR constants (MQM assigns severity per error instance; `ste-punctuation.yml:130-145` bad example is HARM 1, not the matrix's 0). Levels become named ordinal categories; codes are wire format. |
| C3 | Uncertainty and protectedness are gates, not dimensions (§3) | AMEND | Selective-prediction theory supports gate-before-score, and confidence is never a quality trait; but a calibrated confidence signal may drive abstention (Kamath 2020: 56% coverage at 80% accuracy under shift), so "never used" is wrong, "never a score" is right. Protectedness is model-returned in the design; the contract makes it deterministic where a signal exists. |
| C4 | Confirm requires WARRANT >= 2, exact-substring quote with byte offsets, arity 2 for non-local defects (§4, §5) | REPLACE | Exact mechanically validated spans are well supported (Weller 2024: 99.9% vs 17.0% quote match; Slobodkin 2024: AIS 87.6 -> 94.4). But "byte offsets" checked by Python slicing are code-point offsets over a normalised projection (`analyze.py:582-606`), "context never quotable" makes the design's own heading-echo example abstain, and universal WARRANT >= 2 has no source. Replaced by source-typed evidence, rule-declared `{min_arity, roles}`, rule-declared `warrant_min` (default 2). |
| C5 | Judgement deducts at most 20 points and never gates alone (§9) | REPLACE | Arithmetic: a mechanically clean document scores 100; 100-20 = 80 < strict `min_score` 85 (`config.py:744`). With the suggestion penalty spent, 100-15-20 = 65 < normal 70. The code's `min_score` guard fires only when errors or warnings exist (`score.py:267-272`), which the design never states. Cap set to 15 (narrowest band) and made reporting-only; gating paths named explicitly. |
| C6 | Cluster gate on >= 3 findings from >= 2 distinct categories; within-category rules correlate more (§9) | REPLACE | Measured on 98 model-authored documents (220,336 words, 19,490 findings): within-category phi mean 0.0263 vs across 0.0267; Jaccard 0.0137 vs 0.0142. The strongest pair is across categories and one phenomenon (`prose-craft.unclear-antecedent` x `ste-practices.unclear-demonstrative-this`, phi 0.985). The new gate keeps 1,821 of 1,899 old-gate units (96%). Replaced by non-overlapping evidence components with a dependence table. |
| C7 | Six closed preservation classes (§3) | REPLACE | Three classes are over-broad as written (`formal_legal`: SEC handbook and US Courts guide show legal prose is routinely plain-languaged; `l2_clarity` and `accessibility_repetition` protect arbitrary repetition that WCAG 3.2.4 / 2.4.6 do not). Two evidenced classes are missing: `normative_obligation` (repo steering markers, `change-comms.md:8-20`) and `quoted_specimen` (`docs/rules.md` 530 specimens; `slopvac.toml:19-25`). Seven-class enum adopted. |
| C8 | Four abstention reasons; abstentions count against coverage (§3) | REPLACE | Abstention as a verdict with a coverage cost is strongly supported (GopherCite: abstaining on 30% raises attempted quality 80% -> 90%+). The list conflates evidence location with reason and omits missing/conflicting context and external facts (Wen et al. 2025 taxonomy). Seven reasons plus a separate `source` field. |
| C9 | 8 criteria / 12 units per SPAN call; one 18-criterion PROBE pack (§7) | REPLACE | No count-based prose-judge measurement exists at 8, 12, or 18. Closest evidence: ManyIFEval judge over-reports all-pass by +24.1 points at 5 constraints and +44.4 at 10; BatchPrompt degrades at batch size 6; validated checklist judges decompose (TICK, CheckEval, ComplexBench 87.8% vs 75.2%). Provisional 4 criteria / 5 units; PROBE split into five packs. |
| C10 | Decision algorithm §5 (reject fit<=1 or warrant<=1; harm==0 and repair<3; error iff harm==3 & fit==3; warning iff harm>=2) | REPLACE | Boundaries are defensible policy but unvalidated; three defects found: FIT=2 (ambiguous) can reach `warning`; `harm==0 and repair<3` rejects the parenthesis rule's own bad example; a null rewrite on a confirm is required by §11 case 15 yet forbidden by the schema and demoted by the checker. Replaced with named-level rules and `rewrite_status`. |
| C11 | Seven protected token classes; addition asymmetric; class-wide exemptions (§6) | REPLACE | Token inventory is grounded (Crowdin QA, XLIFF, MQM accuracy types, RFC 2119 case). Two policies fail: "present elsewhere in the document authorises addition" lets a MUST or identifier land in the wrong place and blocks the glossary rule's only honest fix (`ste-words.yml:367-381`); class-wide `rewrite_exempt` admits every alteration in the class. Typed located comparison, referent-authorised additions, exact `allowed_transitions`. |
| C12 | Semver spine (PATCH = wording that cannot move a score); pack_id hash; thresholds outside rubric text; comparability tuple (§10) | REPLACE | Formatting-only prompt changes move accuracy by up to 76 points (Sclar 2023) and 62.1 (Mizrahi 2024); shot order alone spans >85% to ~50% (Lu 2022). No model-visible PATCH is score-inert. The proposed hash omits discriminator, admission, protects, arity, ceilings, template, shot order; the comparison tuple omits model, request digest, decoding. The design's own §9 hard-codes four thresholds. |
| C13 | LAMP categories map onto rule categories; three gaps are rule gaps (§12) | AMEND | LAMP's seven labels are correct (Chakrabarty 2024: 18 writers, 1,057 paragraphs, 8,035 edits; categorical precision only .23). The map has five partial-or-gap rows where the design counted three (cliché and consumer word choice also lack a judgement remainder), and one rule id is wrong (`prose-discipline.one-sentence-one-idea` is `overloaded-sentence`, `prose-discipline.yml:375-422`). |
| C14 | Rejected alternatives (§13) | AMEND | Scalar score: KEEP the rejection for finding admission (WQRM trains on 1-10 and reaches 74.3% RewardBench; useful for ranking, useless for spans). Register and originality: KEEP. Confidence: AMEND (calibrated metadata, never a score). Per-dimension packs: AMEND (a legitimate anti-halo control to test, not an impossibility). "Confidence correlates with every axis": UNSUPPORTED. |

## 2. Evidence by question

### 2.1 Dimension count and independence (C2, C13, C14)

- Analytic writing traits do not behave independently. ASAP++ trait pairs all correlate at r >= .60, eighteen pairs at >= .80, Sentence Fluency-Conventions .893 (Li & Ng, EMNLP 2025, <https://aclanthology.org/2025.emnlp-main.1691.pdf>). TOEFL analytic aspects correlate .84-.96 with one principal component explaining 90.6% of variance (Sawaki, ETS, <https://files.eric.ed.gov/fulltext/EJ1111378.pdf>). These are not FIT/HARM/WARRANT/REPAIR, but they defeat independence by declaration.
- MQM assigns Neutral/Minor/Major/Critical severity to each error instance by its usability effect (multipliers 0/1/5/25) and treats category weight as a separate configurable multiplier (<https://themqm.org/error-types-2/the-mqm-scoring-models/>). This refutes a per-category HARM constant and supports an optional `error_type_weight`.
- Expert MQM raters differ in category use and severity distributions even with training (Freitag et al. 2021, <https://aclanthology.org/2021.tacl-1.87.pdf>). Post-editing research separates temporal, technical, and cognitive effort from meaning change; a one-word negation edit can reverse meaning while five word edits preserve it, so REPAIR cannot stand in for HARM.
- LAMP: seven categories consolidated from 50 with significant semantic overlap; span precision .57 but category-aware precision .23 (<https://arxiv.org/html/2409.14509>). WQRM labels overall quality 1-10 and reports no criterion-level reliability (<https://arxiv.org/html/2504.07532v1>).
- Repository: `orwell.yml:7-31` is a finite stale-figure token list, not an open-set cliché judgement; `prose-craft.yml:17-65` covers tense defaults, not cross-sentence tense inconsistency; `ai-tells-agentic.yml:468-537` covers summary closers, not general redundant exposition.
- Verbal confidence: median ECE .03 but response-length bias up to .44 (Groot & Valdenegro-Toro 2025, <https://arxiv.org/html/2412.14737v2>). Calibrated metadata, not a trait.

Decision: keep all four checks, scored per finding, separately reported, non-interchangeable. If calibration ever forces a merge, merge FIT+WARRANT (validity), never HARM+REPAIR.

### 2.2 Scale granularity (C2, C10, C14)

- Scale width is not the lever. At temperature 1.0, Llama-2 Krippendorff alpha was 0.801 on 10-point numeric, 0.683 on 5-point, 0.532 binary, 0.366 verbal Likert; GPT-4 0.961 / 0.954 / 0.881 / 0.835 (<https://arxiv.org/html/2412.00543>). Stureborg et al.: GPT-4 Kendall tau 1-5 .339, 1-10 .428, 1-100 .383; human inter-rater alpha .659 vs GPT-4 self-consistency .587; 1-100 outputs cluster at 60/70/80/90 (<https://arxiv.org/html/2405.01724v1>). Retrieval: NDCG@10 rises 0.547 -> 0.630 -> 0.638 from 2 to 5 to 11 points (<https://arxiv.org/html/2505.19334v1>).
- Decomposition and anchors are the lever. CheckEval's yes/no checklists raised all-model alpha from 0.09 to 0.48 (SummEval) and 0.06 to 0.45 (Topical-Chat) at temperature 0 (<https://arxiv.org/html/2403.18771>). Prometheus with per-point descriptions: Pearson .897 vs GPT-4 .882; removing the rubric drops .847 -> .745 (<https://arxiv.org/html/2310.08491>).
- Rationale-before-score helps; evidence-first specifically is not isolated. Chiang & Lee: SummEval coherence Pearson score-only .344, rate-explain .557, analyze-rate .635; the two rationale orders are not significantly different (<https://arxiv.org/html/2310.05657v1>). FairEval: evidence-before-score raised GPT-4 accuracy 52.7% -> 56.5% (<https://arxiv.org/html/2305.17926>). G-Eval CoT: Spearman .500 -> .514 (<https://arxiv.org/html/2303.16634>).
- Position and verbosity biases are large: order swaps flip 46.3% (GPT-4) and 82.5% (ChatGPT) of pairwise judgements (FairEval); MT-Bench swap consistency 65.0% GPT-4, 46.2% GPT-3.5, 23.8% Claude-v1 (<https://arxiv.org/html/2306.05685>); verbosity-bias magnitude 0.328 GPT-4, 0.428 GPT-3.5 (<https://arxiv.org/html/2310.10076>). These argue for absolute, single-unit, evidence-anchored judgements over comparative ones.
- UNSUPPORTED: 0-3 superior to binary+severity or anchored 1-5 for this task; any midpoint-clustering percentage; repeated-call agreement at temperature 0 by scale width; measured noise from asking a constant dimension.

Decision: four named ordinal levels per dimension (`absent | partial | ambiguous_match | unambiguous_match` etc.), codes for serialization only, never summed. Thresholds keep the design's boundaries with one change: `ambiguous_match` FIT caps severity at `suggestion`.

### 2.3 Gates versus dimensions; abstention; quote grounding (C3, C4, C8)

- Selective classification formalises abstention as a reject option separate from the predictor (Geifman & El-Yaniv 2017, <https://arxiv.org/abs/1705.08500>; Franc et al. JMLR 2023, <https://jmlr.org/papers/volume24/21-0048/21-0048.pdf>). Kamath et al. 2020: a calibrator retains 56.06% coverage at 80% accuracy under domain shift (<https://aclanthology.org/2020.acl-main.503.pdf>). Kadavath et al. 2022: models are calibrated on P(I know) for large models, RLHF models less so (<https://arxiv.org/abs/2207.05221>).
- Cost of forcing answers: GopherCite quality 80% when forced, above 90% after abstaining on ~30% (<https://arxiv.org/pdf/2203.11147>). Over-abstention has its own cost: a strict abstention prompt raised unanswerable accuracy 83.6 -> 97.8 but lowered answerable accuracy 91.2 -> 87.0 (Madhusudhan et al. COLING 2025, <https://aclanthology.org/2025.coling-main.627.pdf>). Both valid and excessive abstention must be measured.
- Verbatim evidence is not obtained by asking: QUIP-trained models quote exactly 99.9% of the time vs 17.0% for the untuned baseline (Weller et al. EACL 2024, <https://aclanthology.org/2024.eacl-long.140.pdf>). Attribute-first generation raised AIS 87.6 -> 94.4 (Slobodkin et al. ACL 2024, <https://aclanthology.org/2024.acl-long.182.pdf>). Even the best ALCE system lacked complete support 50% of the time (<https://aclanthology.org/2023.emnlp-main.398/>). GopherCite splits a mechanical verbatim check from a human support judgement: exact-slice validation before WARRANT, not instead of it.
- Arity: coreference evaluation scores mention chains, not pairs (Pradhan et al., <https://aclanthology.org/W10-4305.pdf>); tense benchmarks use paired utterances (<https://aclanthology.org/2023.acl-short.164/>). Relational defects need >= 2 role-labelled spans; "exactly 2" has no source.
- Byte offsets: the design validates `text[start:end] == quote` (code points) while calling them byte offsets; `analyze.py:582-597,625-628,665-674` strips and re-joins visible text and keeps line starts, not a byte map. Resolving an offset in `unit.text` to raw bytes requires a projection map.
- Abstention taxonomy (Wen et al., TACL 2025, <https://arxiv.org/abs/2407.18418>) separately lists incomplete input, insufficient context, knowledge conflict, and knowledge limits.
- UNSUPPORTED: universal WARRANT >= 2; a numeric reduction in fabricated spans caused by quote-first ordering (Weller's 99.9% is a match rate under training, not a prompting effect).

### 2.4 Protected classes (C7, C11)

- `normative_obligation` (was `technical_invariant`): RFC 2119 / RFC 8174 fix keyword force and case (<https://www.rfc-editor.org/rfc/rfc2119.html>, <https://www.rfc-editor.org/rfc/rfc8174.html>); ISO/IEC Directives Part 2 prescribe shall/should/may/can (<https://www.iso.org/sites/directives/current/part2/index.xhtml>); ANSI Z535.4-2023 and ASD-STE100 §7.1 reserve DANGER/WARNING/CAUTION by hazard severity (<https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf>; the ANSI text is paywalled). The repo's own steering markers (`change-comms.md:8-20`) are the same class and had no home in the six.
- `factual_polarity_or_contrast`: MQM's canonical mistranslation is dropped negation (<https://www.themqm.org/mqm-pillars/the-mqm-full-typology/>); NMT negation accuracy 91.7-95.7% shows the error is real (<https://aclanthology.org/2021.tacl-1.45/>); corpus work distinguishes additive from corrective not-but frames (<https://journals.sagepub.com/doi/10.1177/00754242231195369>).
- `source_locked_legal_text` (narrowed from `formal_legal`): the SEC Plain English Handbook and the US Courts 2024 drafting guide show legal prose is routinely rewritten (<https://www.sec.gov/pdf/handbook.pdf>, <https://www.uscourts.gov/sites/default/files/essentials_for_drafting_clear_legal_rules_2024.pdf>); Creative Commons forbids altering legal code (<https://creativecommons.org/legal-code-defined/>) while SPDX tolerates whitespace/case variation (<https://spdx.github.io/spdx-spec/v3.0.1/annexes/license-matching-guidelines-and-templates/>). Protection turns on source authority, not register.
- `controlled_language_clarity` (narrowed from `l2_clarity`): explicit connectives benefit L2 readers by ~100 ms while natives are unaffected (Zufferey et al., 80 L1 + 80 L2 per experiment, <https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.685491/full>); Google's global-audience guide says repeat a word when it aids comprehension (<https://developers.google.com/style/translation>); ASD-STE100 one word, one meaning. Audience must be configured, not guessed.
- `accessibility_consistency` (narrowed from `accessibility_repetition`): WCAG 2.2 SC 3.2.4 and 2.4.6 require consistent identification and descriptive labels, not verbatim repetition (<https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html>, <https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html>); SC 3.1.5 is AAA reading level; plainlanguage.gov: use the same term consistently (<https://www.plainlanguage.gov/guidelines/words/use-the-same-terms-consistently/>); COGA clear-content objective (<https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/>).
- `authoritative_domain_term`: ISO 704:2022 (<https://www.iso.org/standard/79077.html>); Microsoft and Google style guides reject synonym variation for one concept.
- `quoted_specimen` (new): `translate=no` protects examples and source strings (<https://www.w3.org/International/questions/qa-translate-flag>); the repo excludes `docs/rules.md` because 530 specimens read as 530 findings (`slopvac.toml:19-25`).
- Token classes: Crowdin QA checks tags, variables, numbers, terminology separately (<https://support.crowdin.com/project-settings/qa-checks/>); XLIFF 2.1 protects inline codes (<https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html>); MQM says explicitation and unit conversion can be appropriate, so "numeral never added" and "present elsewhere authorises" are both too blunt.
- UNSUPPORTED as written: `formal_legal`, `l2_clarity`, `accessibility_repetition`; `generated_schema` as a semantic protection (it is an admission property: origin).

### 2.5 Composition and bloat (C9)

- ManyIFEval: GPT-4o-as-judge reports prompt-level success 0.815 vs 0.574 ground truth at 5 simultaneous instructions (+24.1 points) and 0.657 vs 0.213 at 10 (+44.4) (<https://arxiv.org/html/2509.21051v1>). FollowBench: GPT-4 HSR 84.7% -> 61.9% from 1 to 5 constraints; authors estimate ~3 constraints handled (<https://arxiv.org/html/2310.20410v3>).
- BatchPrompt: naive batching at batch size 6 significantly degraded all eight tasks; GPT-4 lost ~1-2 points at 16 with permutation calibration (<https://arxiv.org/html/2309.00384v3>). ComplexBench decomposed evaluator 87.82% vs 75.18% direct scoring (<https://arxiv.org/html/2407.03978>). TICK asks each checklist question in a separate call, 82.6% accuracy (<https://arxiv.org/html/2410.03608>). CheckEval's 20-33-question checklists showed "no noticeable difference" in an unpublished pilot but default to one question per call (<https://arxiv.org/html/2403.18771v2>).
- Long context: Lost-in-the-Middle U-curve (<https://arxiv.org/html/2307.03172>); RULER GPT-4 96.6 -> 81.2 from 4k to 128k (<https://arxiv.org/html/2404.06654>); NoLiMa: 11/13 models below half their short-context baseline at 32k, GPT-4o 99.3% -> 69.7% (<https://arxiv.org/html/2502.05167v3>).
- Caching: Anthropic minimum cacheable prefix 1,024/2,048/4,096 tokens by model, writes 1.25x, reads 0.1x, default TTL 5 min (<https://platform.claude.com/docs/en/build-with-claude/prompt-caching>); OpenAI 1,024-token minimum (<https://developers.openai.com/api/docs/guides/prompt-caching>); Bedrock 5-minute TTL, Claude 3.5 Sonnet $3.00 / $3.75 / $0.30 per M (<https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html>, <https://aws.amazon.com/bedrock/pricing/>). The <= 900-token spine is below every minimum; 3-6 different packs on one document share no cacheable prefix. The $0.29 vs $0.11 figures have no reproducible ledger (`rubric-design.md:249-303`).
- UNSUPPORTED: any per-criterion recall curve at 1/2/4/8/12/18 for a prose judge; criterion-list position effects; 12 units as a safe cap.

### 2.6 Aggregation (C5, C6) - measured

Corpus and method: `slopvac lint --profile strict --format json` with the repo `slopvac.toml` over (A) 16 repository markdown files (12,339 words, 429 findings) and (B) 98 model-authored session documents (220,336 words, 19,490 findings; unguided prose never tuned to these rules). Units are blank-line paragraphs (5,056 in B) with a 10-line-window robustness check. Pairs of rules with >= 3 unit hits: 266 within-category, 3,562 across. Scripts and raw output are recorded in the research work directory (`cooccurrence.py`, `toppairs.py`, `inventory.py`, `cooccurrence.json`).

| Statistic (B, paragraphs) | Within category | Across categories |
|---|---|---|
| Jaccard mean / median / p90 / max | 0.0137 / 0 / 0.0415 / 0.125 | 0.0142 / 0 / 0.0410 / 0.972 |
| phi mean / median / p90 / max | 0.0263 / -0.0011 / 0.0783 / 0.297 | 0.0267 / -0.0008 / 0.0847 / 0.985 |

Top pairs by phi are all cross-category and mostly one phenomenon under two names: `prose-craft.unclear-antecedent` x `ste-practices.unclear-demonstrative-this` 0.985; `prose-discipline.frozen-verb` x `ste-verbs.nominalized-action` 0.539; `prose-craft.sentence-length` x `ste-descriptive.sentence-too-long-descriptive` 0.445; `prose-craft.latinisms` x `ste-practices.latin-abbreviation` 0.289. Highest within-category pair: 0.192. Gate trips: old ">= 3 findings" 1,899 units; new ">= 3 from >= 2 categories" 1,821 (96%); ">= 3 from one category" 900. Corpus A: 44 vs 43.

Limits: mechanical findings on model prose stand in for the unimplemented judgement layer; `ai-tells-structure` judgement rules are absent from the data. The proxy refutes the taxonomy-based independence premise; it cannot set the judgement gate's cutoff.

Score arithmetic (`score.py:38-43,58-105,172-196,267-272`; `config.py:736-747`):

- SEVERITY_WEIGHT 1.0 / 0.5 / 0.1; base score 100 -> 70 inside budget.
- MAX_SUGGESTION_PENALTY 15. Its comment says it "cannot cross the shipped 70.0 minimum", but 15 is exactly the strict band 100-85.
- `min_score` is tested only when `errors or warnings` exist.
- A 20-point judgement cap fails a clean document at strict (80 < 85) and, with suggestions spent, at normal (65 < 70).
- The guard prevents judgement-only gating only if judgement findings do not count as errors or warnings. The design leaves that unspecified.

Precedent: ETS uses e-rater as a check score and routes to a human at a 0.5-point discrepancy; the machine contributes nothing to the reported score (<https://files.eric.ed.gov/fulltext/EJ1109327.pdf>; <https://www.ets.org/research/policy_research_reports/publications/report/2012/jdyu.html>). Williamson, Xi & Breyer require empirical agreement and adjudication evidence (<https://doi.org/10.1111/j.1745-3992.2011.00223.x>). MQM normalises penalties per word and calibrates to a passing interval; no separate stochastic cap (<https://www.themqm.org/mqm-pillars/the-mqm-scoring-models/>); repeated errors need an explicit policy (<https://www.themqm.org/guidance/repeatederrors/>). Vale gates by per-rule level (<https://vale.sh/docs/keys/minalertlevel>), textlint by severity exit status (<https://textlint.org/docs/configuring/>), proselint caps output (`max_errors`), Acrolinx normalises by length per goal (<https://support.acrolinx.com/hc/en-us/articles/10210995244178-The-Acrolinx-Score-Explained>). No editorial tool documents a "three in one passage" gate. The repo's "three false-positive reports" rule (`docs/triage.md:81-84`) has no derivation, and a PRESERVE is not a false positive.

UNSUPPORTED: `JUDGEMENT_MAX_PENALTY = 20`; "within-category rules correlate more"; "three preserves is the demote signal"; uncalibrated reuse of mechanical category weights.

### 2.7 Versioning and comparability (C1, C12)

- Prompt sensitivity: equivalent formats differ by up to 76 accuracy points; GPT-3.5 median 6.4, max 56 across 320 formats (Sclar et al., <https://arxiv.org/html/2310.11324v2>); paraphrased instructions spread up to 62.1 points, 15/25 best-prompt comparisons have negative rank correlation (Mizrahi et al., <https://aclanthology.org/2024.tacl-1.52.pdf>); few-shot order spans >85% to ~50% (Lu et al., <https://aclanthology.org/2022.acl-long.556.pdf>).
- Benchmarks re-run rather than carry judgements:
  - lm-evaluation-harness bumps a task `version` on breaking config (<https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/new_task_guide.md>).
  - HELM reproduction needs the run-entry file, schema, model, and trials (<https://crfm-helm.readthedocs.io/en/latest/reproducing_leaderboards/>).
  - WMT22 relabelled corrected MQM `v3` and republished (<https://www.statmt.org/wmt22/metrics/index.html>).
  - Inspect logs record task version, model args, packages, and git revision (<https://inspect.aisi.org.uk/eval-logs.html>).
  - promptfoo keys its cache on provider, prompt digest, config, and vars (<https://www.promptfoo.dev/docs/configuration/caching/>).
  - Croissant couples `version` with `sha256` (<https://docs.mlcommons.org/croissant/docs/croissant-spec.html>).
- Separation of thresholds from rubric text has analogues (WCAG techniques vs success criteria, <https://www.w3.org/WAI/WCAG22/Understanding/understanding-techniques>; Vale MinAlertLevel; MQM scoring model vs typology, <https://www.themqm.org/mqm-pillars/typology/>) but every one records the resolved policy identity. The design's §9 hard-codes 20, >= 3, >= 2, HARM 3 in rubric prose (`rubric-design.md:354-369`).
- Internal contradiction: `pack_id` includes `rubric_version`, so a spine change invalidates every pack, contradicting "any pack edit invalidates its own cache and nothing else".
- UNSUPPORTED: the MAJOR/MINOR/PATCH mapping; any score-inert model-visible wording class.

## 3. Adversarial cases

Each case quotes real text from the checkout, walks the design's §5 algorithm, names the failing field, and gives the minimal fix. Cases 1-11 come from the repository challenge; 12-13 from measurement.

1. **A3 preserves the false positive and drops its adjudicator.** Specimen (`packages/slopvac-lint/tests/fixtures/vale/must-not-fire.md:15`):

   ```text
   It is not faster but it is cheaper.
   ```

   The mechanical core `contrastive-inversion-frames` fires; the remainder is A3-inadmissible, so §5 returns DROP before `factual_contrast` can be evaluated. The known false positive survives. Failing field: A3. Fix: `core_fired=true`, adjudicate once, PRESERVE/REJECT suppresses the core (contract gate A3).
2. **Normative policy has no preservation class.** "NOT 'Lays the groundwork'..." and "MUST Repos with release-please or changesets: never hand-edit CHANGELOG.md" (`packages/slopvac/skills/write-docs/references/change-comms.md:8-20`). Register packs are dispatched (genre change-comms); none of the six reasons denotes an operational prohibition, so the unit is scored and exposed to a stochastic confirm. Failing field: `preservation_reason` enum. Fix: `normative_obligation`, set deterministically on steering markers.
3. **Schema-required heading/name pair confirmed as echo.** "#### `ai-residue.chat-leakage`" followed by "Delete chat-session leakage" (`packages/slopvac-lint/docs/rules.md:60-64`). FIT 3, WARRANT 2 (arity satisfied), HARM 0, REPAIR 3 -> CONFIRM/suggestion on a generated reference page where the id is the anchor and the imperative is the label. Failing field: admission lacks origin. Fix: gate A5 `origin: generated` inadmissible unless the rule opts in.
4. **Honest missing-fact finding cannot satisfy the confirm schema.** "Some tests need a live database." (`must-not-fire.md:14`; also `prose-discipline.yml:607-608`). REPAIR 1 (needs absent fact), HARM 2; §11 case 15 expects "warning with rewrite null", but §4 makes `rewrite` required iff confirm and §5 demotes when the checker rejects a null rewrite. Failing field: `rewrite` cardinality. Fix: `rewrite_status = withheld_needs_fact`, no demotion.
5. **The glossary rule cannot introduce the glossary term.** "The job runner picks up the next work item." -> "The worker picks up the next task." (`ste-words.yml:367-381`). The authorised term lives in a glossary the unit does not contain; `context` is unquotable so arity-2 fails (ABSTAIN), and if it did not, adding `worker` is forbidden because it is absent from the document. Failing fields: evidence source, asymmetric addition. Fix: repository evidence `path@blob_sha` as `referent`; additions authorised by cited referent.
6. **`context` prohibition forces abstention on the canonical positive.** "## Install the plugin" / "This section covers installing the plugin." (`docs/rules.md:3053-3059`). heading-echo needs the heading as `antecedent`; the heading is context, never quotable, so `evidence_ok=false` and the design's own worked example abstains. Failing field: evidence quotability. Fix: `source: context` permitted for non-defect roles.
7. **Byte offsets cannot be checked by the specified slice.** "checker - Vale ... They produce findings" (`docs/rules.md:9`), smart apostrophe "the loader's cache" (`ai-tells-agentic.yml:1609-1614`), CRLF projection (`tests/test_toml_comments.py:39-43`), code spans in `README.md:305-313`. `unit.text` is normalised and re-joined (`analyze.py:209-220,589-606`); `text[start:end]` is code-point slicing; after a multibyte character or a stripped code span, exact evidence fails and unit ids drift. Failing fields: `range`, `unit_id`, `evidence_ok`. Fix: code-point offsets into the named source text, a deterministic projection map, `source_sha256`.
8. **Three categories count one generated schema three times.** Every generated rule section repeats id heading, imperative name, and bold field list (`docs/rules.md:60-73,84-95`): heading-echo (structure), over-formatting-reflex (register), padded-symmetry (content-shape) each confirm on the same convention -> ">= 3 from >= 2 categories" -> REVISE. Failing field: cluster gate keyed on categories. Fix: non-overlapping evidence components (contract aggregation.cluster_gate). Measurement backs it: cross-category phi up to 0.985 on one phenomenon.
9. **HARM=0 rejects a real non-deletion repair.** "Rotate the signing key (we found that most teams forget this until an audit, which is why the runbook exists)." (`ste-punctuation.yml:130-145`, the rule's own bad example). FIT 3, WARRANT 2, matrix HARM constant 0, REPAIR 2 -> `harm == 0 and repair < 3` -> REJECT. Failing field: category HARM constant. Fix: score HARM per finding (the example is HARM 1); withdraw §8 constants.
10. **Quoted rule specimens are unprotected probe targets.** The bare-quantifier question enumerates "most, some, many..." and quotes bad examples (`docs/rules.md:3303-3317`). Whole-document probe: FIT 3, WARRANT 2, HARM 2, REPAIR 1 -> findings on documentation that shows the rule. Failing field: C7 enum lacks a quotation class. Fix: `quoted_specimen`, preset from blockquote/fence/example structure.
11. **One document verdict cannot report every document-scope occurrence.** `docs/rules.md` (237.5 KB) holds bare quantifiers at lines 277, 377, 610, 955, 1023, 1234, 1273, 1591, 1674, 3304-3317 and elsewhere; one PASSAGE_PROBE verdict carries one rewrite and one score. Failing field: PASSAGE_PROBE cardinality. Fix: `occurrences[]` with a cap and `missing_context` for the unread remainder.
12. **A 20-point cap gates alone at strict.** Any mechanically clean document under `--profile strict`: 100 - 20 = 80 < 85 (`config.py:744`). Failing field: JUDGEMENT_MAX_PENALTY and the unstated dependence on the `errors or warnings` guard (`score.py:267-272`). Fix: cap 15, reporting-only, gating paths named.
13. **Same-phenomenon rule pairs across categories.** `prose-craft.unclear-antecedent` x `ste-practices.unclear-demonstrative-this` co-occur in 139 of 141 paragraphs each (phi 0.985) on the session corpus; the "distinct categories" test counts them as two independent votes. Failing field: independence premise of C6. Fix: registered dependence table; count components.

## 4. Three changes expected to reduce false positives most

1. **Origin- and region-aware admission with `normative_obligation` and `quoted_specimen` preservation (gate A5, C7).** Removes whole high-density classes before any model call: generated reference (`docs/rules.md` alone is 237.5 KB and repeats its schema hundreds of times), fixtures, quoted specimens, licence text, and steering blocks. Deterministic, so it cannot be stochastic noise, and it fixes cases 2, 3, 10 at once.
2. **Replace A3 double jeopardy with core adjudication (gate A3).** Converts already-known mechanical false positives (`must-not-fire.md:15`) into PRESERVE/REJECT instead of shielding the core from review, and emits one deduplicated finding on CONFIRM. It reduces both false positives and double counting.
3. **Cluster by non-overlapping evidence components, not category labels (aggregation.cluster_gate).** The measured proxy shows category labels carry no independence (within 0.0263 vs across 0.0267) and that the strongest dependence is one phenomenon under two names. Component counting stops one formatting convention or one unclear referent from becoming three votes and a build-level REVISE.

Runner-up: score HARM per finding and demote nothing on `withheld_needs_fact` (cases 4 and 9); these reduce false negatives more than false positives.

## 5. Unsupported claims (consolidated)

- C2: four-factor independence; 0-3 superior to other widths; constants remove measurable noise.
- C4: universal WARRANT >= 2; exactly two evidence items for all non-local defects; five global roles complete; raw byte offsets from the current projection.
- C5: the number 20; any published separate stochastic-component cap.
- C6: within-category correlation exceeds across-category (contradicted by the proxy).
- C7: `formal_legal`, `l2_clarity`, `accessibility_repetition` as written; `generated_schema` as a semantic class.
- C9: 8 / 12 / 18 as safe caps; $0.29 vs $0.11; an 8.7k prefix paying off across different packs.
- C11: "numerals never added"; "present elsewhere authorises addition"; class-wide exemptions.
- C12: score-inert model-visible PATCH; the semver mapping; "thresholds never in rubric text" as practised.
- §9.4: three preserves as a demote signal. §13: "confidence correlates with every other axis". §11: 15/15 executed cases (no implementation, command, or raw output is named, `rubric-design.md:418-438`).

## 6. Second round: the contract itself was challenged

The first synthesis (schema_version 1.0.0) was handed back to the adversarial challenger with the repository and every first-round report. It returned 17 findings and 8 implementation blockers (`challenges/ChContract.md`). Version 1.1.0 amends the contract text for every finding that text can settle. What needs code is recorded under `implementation_gate.blockers` (B1-B7) instead of being described as solved:

| Finding | Change in 1.1.0 |
|---|---|
| `withheld_checker_veto` emitted by the algorithm but absent from the model schema | Split: the model emits `proposed`, `withheld_needs_fact`, `not_applicable`; the host finding record extends the enum (`x-host_finding_record`). |
| `normative_obligation` preserved the safety rule's own target | `not_applied_to` on the class; `adjudicates` on `ste-safety.risk-level-word-missing-or-wrong`. |
| Transitions declared in prose, absent from the rule record; only upgrades allowed | Per-rule `allowed_transitions` table, the checker's only authority. `ste-safety` carries CAUTION<->WARNING (the pair its examples evidence, `ste-safety.yml:27-31`) marked provisional; DANGER and NOTE rows wait for a safety authority. |
| A3 vs A5 order; `quoted` conflated with provenance | Gate order A5, A1, A2, A4, A3; `origin` split from `region_class`; A5 never suppresses the mechanical core. |
| `inapplicable` masks without decision semantics | Explicit branches in the algorithm; masked HARM caps severity at suggestion. |
| Model verdict vs host outcome | Host recomputes; disagreement is `ABSTAIN(inconsistent_output)` (eighth, host-only abstention reason). |
| Untyped `occurrences`, no truncation semantics | `$defs.occurrence`, `maxItems`, `occurrences_truncated`, `if/then/else` on `kind`; both branches validated with jsonschema Draft 2020-12 and two negative cases rejected. |
| Cluster gate not computable | Definitions for passage, primary span, component, and a frozen held-out `dependence_table_sha`. |
| Hash inputs undefined | `pack_object` defined over the contract record merged with the YAML rule, RFC 8785 canonicalisation, multi-category probe serialisation. |
| `long-domain-term-without-short-form` demanded a fictitious antecedent | `host_predicates.no_short_form_in_document`; likewise `figure_available` for the bare-quantifier probe. |
| Unsupported constants restated as facts | 15-point cap, 12-occurrence cap, and the preserve review trigger carry `status: provisional` or `disabled_experimental`. |

Still open and recorded under `implementation_gate.blockers` (B1-B7): the projection map does not exist in `analyze.py`, the host finding record type does not exist, no dependence table exists, and the pack renderer, typed checker, YAML schema fields, and origin classifier are unwritten. Universal `warrant_min = 2` remains in every record as calibration-gated configuration because Q01 has not been run; the challenger's objection stands and is recorded in `evidence_requirements.warrant_min`.

## 7. Measured starting state (design §0 re-checked)

- 21 YAML files (multi-document), 230 rules, 25 categories.
- 65 `kind: judgement` rules in 14 categories; 11 zero-judgement categories.
- Scope: paragraph 26, sentence 21, document 17, unset 1 (`orwell.concrete-floor`).
- Severity: suggestion 58, unset 6, error 1.
- Criterion text mean 363 chars, max 1,007, total 23,600; `judgement_question` alone mean 184.
- 65 rules selected at strict and normal, 24 at relaxed.

All §0 numbers reproduce. Three §8 ids do not: `vague-attribution-remainder` belongs to `ai-tells-structure`, not `ai-tells-content-shape`; `ste-words.glossary-term` does not exist (closest: `domain-noun-not-organization-approved`); `ste-safety.risk-level` is `risk-level-word-missing-or-wrong`. The contract uses the real ids.

## 8. Adjacent artefacts assessed against the contract

### 8.1 Branch `autoresearch/also-for-slopvac-we-just-added-the-new-rules-to-20260915`

21 commits ahead of `slopvac-v3-candidate`, 0 behind, dirty tree (`bench/runner.py`, three rule YAMLs, `tests/test_bench_runner.py`, regenerated `docs/rules.md`, untracked `docs/`). Verdict: PARTIALLY SUPERSEDED; land nothing as-is (`challenges/ChAutoresearch.md`).

- Conflicts: `fc261aeb53` scores an abstention as a terminal error (weight 4, `bench/benchmark_contract.json:20-31`); the contract treats abstention as a completed verdict that lowers coverage. `60c7822434` and `a43178f7f6` type the judgement contract as `admission`, free-text `protects`, an uppercase omission list for `dims`, scalar `evidence_arity`, and boolean `rewrite_exempt` (`model.py:163-220`). The contract needs closed-list protects, `{min_arity, roles}`, `ask|inapplicable` masks, `warrant_min`, and typed `allowed_transitions`. `3567284749` edits model-visible criterion prose, which under content hashing is a new instrument.
- Rework against the contract: `60c7822434`, `a43178f7f6`, `3567284749` (the single schema seam and the ownership metadata are the right place to add the contract's fields). Squash and correct `8aa80ba428`, `cace892253`, `90924e283d` (deterministic heading rules and the contrastive-core dedupe; the dedupe moves the core's qualified id from `ai-tells-structure` to `ai-tells-agentic` and its provenance names a rule that does not exist). Port the online-runner chain (`2cdd00b6e4` through `b83a85257b`) into the Q01-Q14 instrument; it retains evidence and usage but knows nothing of `instrument_id` or `judgement_cache_key`.
- Drop: `5efdbd2730`, `f05bffa9df`, `4a7ef71c8d`, `1473ba824f`, `3736b25433`, `c30c70f504`, `fc261aeb53`.

### 8.2 PR 79 `feat(slopvac): keep documentation on the current artifact` (open, draft flag set)

Head `e389916366`, base `main`, 3 commits, 24 files, +745/-813, `mergeable: MERGEABLE`, checks failing (`challenges/PR79.md`). The candidate branch is fully contained in `origin/main`, and `git merge-tree` of the PR head onto the candidate produces a tree with no conflict markers, so integration is a rebase-free merge once CI is green.

- Relevance: still relevant and independent of the rubric. It changes no `judgement_question` (0 diff lines), so no pack hash moves. It removes one mechanical rule, `prose-craft.annotations` (duplicate of `docs-discipline.status-language`; the pair had phi 0.46 in the co-occurrence data), which is not a judgement rule. The two other `- id:` lines in the diff are blank-line context in hunks, so the rule set loses only `annotations`.
- Blocking defects: (1) `lychee`: 36 provenance URLs added by `158e2b8a6c` point at `packages/slopvac-lint/vale-styles/<category>/<Rule>.yml` at commit `29d6a802`, where those files do not exist (404); the earlier URLs used `f4b4e472.../vale-styles/README.md`. (2) `markdownlint`: `packages/slopvac-lint/docs/vale-traps.md:264` MD012 double blank line. (3) The `gate` job fails only because of those two.
- Interaction with this directory: PR 79's policy is that ordinary documentation states the current artifact and history belongs to change-comms or decision records. This research directory is a decision record; `process.md` declares the genre so the policy is met rather than violated.

## 9. Claim list (for reference)

| ID | Claim |
|---|---|
| C1 | spine plus packs |
| C2 | four 0-3 dimensions with constants |
| C3 | gates, not dimensions |
| C4 | WARRANT >= 2 and exact quote |
| C5 | 20-point cap |
| C6 | category cluster gate |
| C7 | six preservation classes |
| C8 | four abstention reasons |
| C9 | 8 / 12 / 18 composition |
| C10 | §5 algorithm |
| C11 | rewrite checker |
| C12 | versioning |
| C13 | LAMP mapping |
| C14 | rejected alternatives |
