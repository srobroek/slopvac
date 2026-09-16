## Verdicts

| Claim ID | Verdict | Reason | Evidence refs |
|---|---|---|---|
| C5 | REPLACE | Bounding stochastic deductions is justified, but 20 and “never gate alone” are incompatible if the composite is tested normally. For a mechanically clean document, `score = 100 − S − J`: strict fails when `S+J>15`; normal fails when `S+J>30`. Thus `J=20` alone gives 80 and fails strict, while normal fails only when `S>10` (full `S=15` gives 65). More generally, a full 20 turns every strict pre-judgement pass into a score failure and turns a normal pass below 90 into failure. Current code muddies this: `min_score` is checked only when a mechanical error/warning exists, so judgement-only cannot gate if that guard remains. The design must specify that invariant; a cap cannot ensure non-gating for a score arbitrarily close to threshold. | E1–E4 |
| C6 | REPLACE | Category labels do not establish independence. In the measured proxy, within/across-category phi and Jaccard are indistinguishable; the strongest pair is across categories but describes the same unclear-reference phenomenon (phi 0.985, Jaccard 0.972), and the new gate retains 1,821/1,899 = 96% of old trips. This corroborates `RubricChallenger.md` case 8/amendment 6. Mechanical findings can refute the taxonomy-based independence premise, but cannot estimate judgement-gate precision, recall, or the right dependence cutoff. | E2, E5, E9–E13 |
| §9.3 | AMEND | Reporting unchecked work is necessary but a list lacks denominators and conflates abstained, ineligible, truncated, failed, and never-run work. Automated-scoring standards require transparent operation, construct coverage, validation, and monitoring; published short-answer work reports the proportion unscored. | E4, [ACT automated-scoring standards](https://www.act.org/content/dam/act/unsecured/documents/R2100-auto-scoring-standards-2021-07.pdf), [short-answer scoring progress report](https://www.tandfonline.com/doi/full/10.1080/08957347.2024.2386945) |
| §9.4 | REPLACE | The repository does say three false-positive reports from different documents trigger review, but provides no derivation. A PRESERVE is not a false positive: it can show a legitimate protected collision. Counts without exposure denominators punish frequently routed rules. Acrolinx sorts frequent rules for human review but explicitly does not prescribe the action; MQM keeps neutral/repeated annotations traceable without score impact. | E6–E8 |
| §9.5 | AMEND | Category weighting has strong MQM precedent, including project/content-specific error-type weights, and Smartling applies shared severity scoring to an LQA Agent schema. That supports calibrated weights, not blindly reusing mechanical weights. In this repo the effective weight is profile-resolved (for example, `prose-craft` is YAML 0.8, strict 1.0, normal 0.8), and current whole-document scoring is not category-weighted except for excluding weight-zero categories. The judgement formula must name which resolved weight it uses and be calibrated separately. | E1, E9, E10 |

## Evidence

- **E1.** `packages/slopvac-lint/src/slopvac/score.py:58-82,172-196,245-249,294-301`; `config.py:736-747`. The suggestion rationale documents the eight-document failure incident, but 15 is exactly the strict 100−85 band; “cannot cross 70” is not the controlling arithmetic. The score-gate guard also requires an error/warning.
- **E2.** `AggregationFacts.md`: thresholds, caps, pair statistics, and gate-trip counts. The proxy contains mechanical findings over 98 model-prose files, not implemented judgement findings or human prose.
- **E3.** [ETS GRE e-rater study](https://files.eric.ed.gov/fulltext/EJ1109327.pdf): at ±0.5 discrepancy, the machine requests human adjudication and contributes nothing to the reported score. This is precedent for containing stochastic influence, not for a 20-point cap. The [2012 ETS operational summary](https://www.ets.org/research/policy_research_reports/publications/report/2012/jdyu.html) confirms the 0.5 check-score threshold.
- **E4.** [Williamson, Xi & Breyer framework](https://doi.org/10.1111/j.1745-3992.2011.00223.x) and the ACT synthesis above require empirical human-machine agreement, degradation, subgroup, and adjudication evidence. No published basis for 20 was found.
- **E5.** `RubricChallenger.md`, case 8/amendment 6: generated schema can create three cross-category votes from one convention; count overlap components instead.
- **E6.** `packages/slopvac-lint/docs/triage.md:81-84` supplies the local “three false positives” precedent, but no statistical or operational derivation.
- **E7.** [Acrolinx Guidance Wizard](https://support.acrolinx.com/hc/en-us/articles/10228284411538-Fine-Tune-Your-Guidelines-With-the-Guidance-Wizard) ranks guidelines by occurrence and leaves enable/disable/context decisions to a reviewer.
- **E8.** [MQM repeated errors](https://www.themqm.org/guidance/repeatederrors/) requires an explicit repeated-error policy and supports neutral, traceable, non-penalizing annotations.
- **E9.** [MQM scoring models](https://www.themqm.org/mqm-pillars/the-mqm-scoring-models/) normalize penalties by evaluated word count, calibrate them to a passing interval, allow project-specific error-type weights, and permit one critical error to fail. They do not define a separate stochastic-component cap or a three-in-one-passage gate.
- **E10.** [Smartling MQM templates](https://help.smartling.com/hc/en-us/articles/19601042280731-LQA-MQM-Schema-Templates) expose severity weights, acceptable penalty points, neutralization, and an LQA Agent schema; this is hybrid-agent precedent without a separate cap.
- **E11.** [Vale MinAlertLevel](https://vale.sh/docs/keys/minalertlevel) gates by per-rule severity; [Vale styles](https://vale.sh/docs/topics/styles) offers a per-rule per-file output `limit`, not a cluster gate.
- **E12.** [textlint severity](https://textlint.org/docs/configuring/) makes any error exit 1 while warning/info do not; [exit-status docs](https://textlint.org/docs/faq/exit-status) define no density or cluster threshold.
- **E13.** [proselint](https://github.com/amperser/proselint/blob/main/README.md) emits diagnostics and caps output with `max_errors`; [alex](https://github.com/get-alex/alex/blob/main/readme.md) emits warnings; [write-good](https://github.com/btford/write-good/blob/master/README.md) returns a suggestion array. [Acrolinx](https://support.acrolinx.com/hc/en-us/articles/10210995244178-The-Acrolinx-Score-Explained) instead normalizes issue count by document length per goal and averages required goal scores. None documents a co-located three-finding gate.

## Amendments

**Cap and gate (paste-ready).** “Judgement deductions are advisory and MUST NOT participate in pass/fail evaluation. Compute and report `judgement_adjusted_score`, but evaluate `min_score` on the deterministic score. If one composite must gate, set `J_max(profile, S)=max(0,100−min_score(profile)−S)`: with the shipped maximum suggestion penalty, strict = 0 and normal = 15. If judgement is considered alone, the largest global clean-document cap is 15, the narrowest passing band. A 20-point cap is reporting-only.”

**Cluster gate (paste-ready).** “REVISE if any confirmed finding has HARM=3. Otherwise, first merge findings connected by overlapping primary evidence spans or by a registered same-phenomenon/dependent-rule relation; retain the maximum HARM/severity per component. REVISE only when one passage contains at least three resulting components with pairwise non-overlapping primary spans. Categories are reported but do not establish independence. Build the dependence table on held-out labelled judgement output; mechanical co-occurrence may nominate pairs but may not calibrate this gate.”

**Coverage (paste-ready).** “For every run report eligible, attempted, confirmed, rejected, preserved, abstained, failed, truncated, and not-run counts by pack and rule, plus reason counts and `coverage = completed/eligible`. A document with any failed, truncated, or not-run eligible unit is `PARTIAL`, never `CLEAN`; abstention remains a completed adjudication but is shown separately.”

**Preserves (paste-ready).** “Report preserves with their exposure denominator and reason: `preserve_rate = preserved/attempted`. Three preserves from distinct documents MAY open human review; they MUST NOT demote a rule. Demotion requires separately adjudicated false positives on a representative sample and a preregistered acceptable false-positive rate. Preserve and false-positive counts MUST NOT be combined.”

**Weights (paste-ready).** “Use the resolved profile weight for the judgement finding’s own category only as an initial prior. Publish the effective weights and recalibrate judgement precision and score/gate effects by profile before activation; do not infer a judgement weight from a related mechanical category.”

## Unsupported

- `JUDGEMENT_MAX_PENALTY=20`: **UNSUPPORTED**; no derivation or published separate-component cap found.
- “Within-category rules correlate more”: contradicted by the measured proxy; judgement-specific claim remains unmeasured.
- “Three preserves is the demote signal”: **UNSUPPORTED** beyond an underived local analogy to false-positive reports.
- Any editorial-tool precedent for “three findings in one passage”: **no evidence found** in the cited Vale, textlint, proselint, alex, write-good, Acrolinx, MQM, or targeted-search material.
- Uncalibrated reuse of exact mechanical category weights for model-derived findings: **UNSUPPORTED**.

## Open evaluation questions

- On labelled judgement output from both human and model prose, what are gate precision/recall for raw count, distinct-category, span-component, and phenomenon-component variants?
- Which rule pairs remain dependent after phenomenon deduplication, and is that dependence stable across genre/profile?
- What judgement deduction, if any, improves score validity without changing pass/fail outcomes?
- What preserve and false-positive rates emerge per rule after stratifying by preservation reason and document type?