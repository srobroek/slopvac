## Verdicts

| Claim ID | KEEP/AMEND/REPLACE | one-line reason | evidence refs |
|---|---|---|---|
| C2 | AMEND | Four dimensions are a defensible operational decomposition, but no cited study establishes their orthogonality; writing traits and error categories overlap, so require per-rule calibration and permit conditional dependence. | E1–E8; design §2 (:39-133) |
| C13 | AMEND | The LAMP names and count are correct; the assertion that all three uncovered categories are merely rule gaps is not demonstrated by LAMP and should be marked an implementation hypothesis. | E1,E2; design §12 (:350-390) |
| C14 | AMEND | Scalar scores and confidence/register dimensions are reasonable rejects for actionability, but the rejection needs empirical comparison rather than “orthogonality” assertion; confidence/register are gates or metadata, not quality traits. | E3–E8; design §13 (:390-430) |

## Evidence

1. **E1 — LAMP primary paper.** https://arxiv.org/html/2409.14509. The abstract reports 18 professional writers, a corpus of 1,057 LLM-generated paragraphs, and seven-category taxonomy. The contribution list reports 8,035 fine-grained edits. The formative study reports 8 participants × 25 samples = 200 paragraphs and roughly 1,600 edits across 50 initial categories. The final taxonomy retained a category only when initial evidence came from at least four participants; the paper explicitly says the 50 categories had “significant semantic overlap.” This supports category consolidation and directly warns against treating categories as independent.

2. **E2 — LAMP category table (same primary source).** https://arxiv.org/html/2409.14509#S4.SS3. The seven final categories are exactly: Cliché; Unnecessary/Redundant Exposition; Purple Prose; Poor Sentence Structure; Lack of Specificity and Detail; Awkward Word Choice and Phrasing; Tense Inconsistency. Thus C13’s list is accurate. The paper does not test whether a missing detector is a rubric gap versus a rule gap; that part is an engineering inference.

3. **E3 — ASAP++ trait resource.** https://www.cse.iitb.ac.in/~sam/papers/SAM-LREC-2018-ASAP++.pdf. The resource scores multiple essay traits (including content, word choice, organization, sentence fluency and conventions), demonstrating precedent for analytic multidimensional assessment rather than one scalar. It is not evidence that traits are independent; trait scores are collected on the same essays and require correlation/reliability analysis before treating them as separable dimensions.

4. **E4 — ASAP++ publication record.** https://lrec.elra.info/lrec2018-main-187. Confirms the resource’s attribute-score design and trait set. It provides no evidence for FIT/HARM/WARRANT/REPAIR specifically; therefore it supports only the general “multiple traits are useful” part of C2.

5. **E5 — MQM framework.** https://aclanthology.org/2013.tc-1.6.pdf. MQM’s published framework decomposes evaluation into explicit error categories and severity. This is a category × severity design, supporting HARM as an impact/severity axis that can vary across categories. It does not support treating severity as constant per rule: the same error category can have different user impact in context. It also does not supply an independent repairability axis.

6. **E6 — Freitag et al., Experts, Errors, and Context.** https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00437/108866/Experts-Errors-and-Context. The study evaluates large-scale expert MQM annotation and reports Table 9 with pairwise rater agreement for MQM and pSQM, finding MQM agreement significantly better across language pairs. The source is evidence that explicit category/severity annotation can improve agreement, but it also documents context sensitivity and does not establish orthogonality among impact, evidence, and repairability.

7. **E7 — Ke & Ng AES survey.** https://www.ijcai.org/proceedings/2019/0879.pdf. Reviews holistic and trait-based automated essay scoring and reports that AES remains unsolved despite decades of work. This cautions against assuming a fixed small dimension set is calibrated merely because it is interpretable; C2 should require corpus validation.

8. **E8 — TOEFL/EFL rubric reliability evidence.** https://files.eric.ed.gov/fulltext/EJ1110371.pdf and https://link.springer.com/article/10.1007/s11145-022-10279-1. These are published rubric-validation/reliability studies (TOEFL writing and many-facet Rasch EFL scoring). The Springer abstract reports four rating criteria were reasonably designed but scoring bands were not uniformly functioning, illustrating that dimension count can be acceptable while anchors remain unreliable. No exact FIT/HARM/WARRANT/REPAIR correlation is reported; do not invent one.

9. **E9 — WQRM/preference alternative.** https://arxiv.org/html/2504.07532v2. Reports human evaluation by nine experienced writers: WQRM-selected writing was preferred 66% overall and 72.2% when reward gap exceeded one point. This supports pairwise/preference evaluation as a useful comparator, not a replacement for span-grounded repair decisions; it is a scalar reward and is not actionable by itself.

## Amendments

- **C2 replacement:** “Use FIT, HARM, WARRANT, and REPAIR as conditionally distinct operational fields, integer 0–3 with observable anchors. Do not assume orthogonality. For each rule/dimension mask, report calibration data (inter-rater agreement and pairwise/polychoric correlations); if a pair is highly dependent, retain fields for decision semantics but prohibit additive interpretation without calibration.”
- **C13 replacement:** “Map LAMP’s seven categories exactly as listed. Treat uncovered categories as detector-coverage hypotheses; classify them as rule gaps only after a repository detector/fixture audit demonstrates that the existing rubric can express their judgement.”
- **C14 replacement:** “Reject scalar 1–10, confidence, register, and originality as *primary defect dimensions* because scalar/preference scores are not span-actionable and the latter are metadata/gates. Validate this rejection against pairwise and analytic baselines; do not claim independence without measurements.”
- **HARM/REPAIR merge decision:** If one pair must merge, merge only for a composite *actionability* analysis, not the stored schema. Both are reader/consequence-facing and likely confounded. Keeping them separate preserves the crucial distinction between (a) high-harm, locally repairable defects and (b) low-harm defects whose repair requires unavailable facts. FIT and WARRANT must not merge: occurrence and evidence sufficiency have different abstention behavior.
- **MQM implication:** Do not make HARM constant per rule by default. MQM’s severity is explicitly context/user-impact dependent; constants are acceptable only where a rule’s contract proves invariant impact and should be audited against counterexamples.

## Unsupported

- No published source located in this slice reports correlations specifically among FIT, HARM, WARRANT, and REPAIR, or validates the exact 0–3 anchors.
- No source found proving that confidence correlates numerically with every quality axis; retain that statement only as a hypothesis pending measurement.
- No source found proving that LAMP’s three uncovered categories are rubric-expressible but solely missing rules.
- The consulted search results did not expose exact Table 9 agreement coefficients from Freitag’s HTML; report exact values only after extracting the table/PDF, not from the abstract.

## Open evaluation questions

1. Double-score a stratified repository sample with at least two trained raters per dimension; report weighted kappa/ICC and FIT–HARM, HARM–REPAIR, WARRANT–REPAIR correlations by category and register.
2. Fit a hierarchical/multifacet model to determine whether a common halo factor dominates the four dimensions; test whether adding HARM and REPAIR separately improves prediction of editor-selected repairs over a merged actionability score.
3. Construct paired cases with equal HARM but different REPAIR (local deletion versus missing fact), and equal REPAIR but different HARM (cosmetic redundancy versus unsafe instruction), then test whether raters preserve the intended ordering.
4. Audit all seven LAMP categories against current YAML rules and fixtures; specifically create consumer-genre awkward-word-choice, redundant-exposition, purple-prose, and tense-sequence cases before calling them rule gaps.