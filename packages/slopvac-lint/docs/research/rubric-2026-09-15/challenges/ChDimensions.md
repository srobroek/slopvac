Claim: The proposed rubric treats FIT/HARM/WARRANT/REPAIR as independent 0–3 axes, fixes HARM/REPAIR by rule, maps LAMP gaps to rules, and rejects several alternative dimensions and pack shapes.

VERDICT: CHALLENGED

## Verdicts

| Claim ID | Verdict | One-line reason | Evidence |
|---|---|---|---|
| C2 | **AMEND** | Keep four separately reported checks, but do not call them independent and do not make instance severity a rule constant. | E2–E6 |
| C13 | **AMEND** | The seven LAMP labels are accurate and gaps belong in rule coverage, but the map has five material gaps, not three, and one mapped rule ID is wrong. | E1, E10 |
| C14.scalar-1–10 | **KEEP** | Reject a scalar as the primary finding verdict; it can rank whole texts but cannot diagnose why a span passes. | E1, E7 |
| C14.per-dimension-packs | **AMEND** | Reject for v1 on cost/identity risk, not because recombination is impossible; separated rating is a legitimate anti-halo control to test. | E2, E3 |
| C14.confidence | **AMEND** | Keep confidence out of prose quality, but retain calibrated uncertainty as metadata; “correlates with every axis” is unevidenced. | E9 |
| C14.register | **KEEP** | Register is a target-relative rule/category concern, not a universal fifth score; MQM likewise models audience/style as error types. | E4, E5 |
| C14.originality | **AMEND** | Reject provenance/authorship scoring, but express observable cliché/staleness as rules rather than claiming originality itself is illegitimate. | E1, E10 |

## Assumptions-that-fail

| Assumption | Why it fails |
|---|---|
| Analytic dimensions behave independently merely because anchors differ. | ASAP++ trait pairs are all at least $r=.60$ and 18 are at least $.80$; TOEFL aspect correlations are $.84$–$.96$, with one factor explaining 90.6% of variance (E2–E3). These are not the proposed four constructs, but they defeat independence by declaration. FIT and WARRANT are also definitionally coupled: quoted, role-correct evidence is part of establishing fit. |
| A rule determines HARM. | MQM assigns severity to **each error instance** based on its effect on usability, while category-level Error Type Weight is a separate configurable multiplier (E4). Freitag et al. found raters differed in category use and severity distributions (E5). |
| Repair difficulty can safely stand in for harm, or vice versa. | Post-editing research separates temporal, technical, and cognitive effort; a one-word negation edit can reverse meaning while five word edits can preserve it (E6). No direct factor study of HARM versus REPAIR was found. |
| C13 identifies exactly three LAMP gaps. | Its own rows admit no judgement remainder for cliché and consumer word choice in addition to redundant exposition, purple prose, and tense consistency. Repository inspection confirms those omissions (E10). |
| Scalar scoring is intrinsically unusable. | WQRM successfully trains on 1–10 overall-quality labels and reaches 74.3% RewardBench accuracy, near GPT-4o’s 74.5%; scalar scoring is useful for ranking, just insufficient for finding admission (E7). |

## Evidence

**E1 — LAMP.** [Chakrabarty et al., arXiv:2409.14509](https://arxiv.org/html/2409.14509) defines exactly seven edit categories: awkward word choice/phrasing, poor sentence structure, unnecessary/redundant exposition, cliché, lack of specificity/detail, purple prose, and tense inconsistency. The corpus has 1,057 paragraphs and 8,035 edits. On 50 multiply edited paragraphs, expert span precision is **0.57**, but category-aware precision is only **0.23**; preference reliability over 600 judgments is Kendall’s $W=.505$. Category ambiguity is therefore measured, not hypothetical.

**E2 — ASAP++ trait dependence.** [Li & Ng, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1691.pdf), Table 1, reports every available trait-pair Pearson correlation at **≥.60**, 18 pairs at **≥.80**, and Sentence Fluency–Conventions at **.893** ($p<.001$). Overall-to-trait correlations range **.600–.883**.

**E3 — TOEFL analytic rubric factor structure.** [Sawaki, *ETS Research Report*](https://files.eric.ed.gov/fulltext/EJ1111378.pdf) reports adjacent-category ICCs of **.85–.91**, aspect correlations of **.84–.96**, and a first principal component explaining **90.6%** of variance. The six aspect scores were empirically “essentially unidimensional,” despite distinct rubric prose.

**E4 — MQM scoring specification.** [MQM Scoring Models](https://themqm.org/error-types-2/the-mqm-scoring-models/) says “each error instance” receives Neutral/Minor/Major/Critical severity according to its particular usability risk; suggested multipliers are **0/1/5/25**. Separately, Error Type Weights may weight categories, e.g. Accuracy 2 versus Style 1. This directly refutes a category/rule severity constant while supporting a rule-level weight or prior.

**E5 — MQM reliability.** [Freitag et al., 2021, “Experts, Errors, and Context”](https://aclanthology.org/2021.tacl-1.87.pdf), Table 9, reports average pairwise agreement **.584** (English→German) and **.412** (Chinese→English) for MQM versus **.304** and **.169** for 7-point scalar pSQM. Raters’ aggregate scores varied within ±20% and ±30%; one rater used Style/Awkward more while another barely used it. Explicit error annotation helps, but category/severity remain rater-sensitive.

**E6 — Repair effort is multidimensional.** [Daems et al., 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5539081/) distinguishes temporal, technical, and cognitive post-editing effort. It gives a one-word negation change that alters meaning and a five-word edit that preserves meaning; **source gives no correlation number for that contrast**. Repair size and semantic harm are therefore not interchangeable.

**E7 — WQRM.** [Chakrabarty et al., arXiv:2504.07532](https://arxiv.org/html/2504.07532v1) uses 12 observable writing-weakness criteria to generate feedback but labels overall quality on a **1–10** scale. WQRM scores **74.3%** on RewardBench versus GPT-4o’s **74.5%**; the paper reports **no inter-rater reliability or factor structure** for the 12 criteria.

**E8 — AES survey scope.** [Ke & Ng, IJCAI 2019](https://www.ijcai.org/proceedings/2019/0879.pdf) distinguishes holistic scoring from trait-specific scoring and identifies QWK as the standard agreement metric; **source gives no validating number for the proposed four dimensions**.

**E9 — Confidence calibration.** [Groot & Valdenegro-Toro, 2025](https://arxiv.org/html/2412.14737v2) reports verbal confidence median ECE **.03**, maximum **.11**, but response-length bias up to **.44**. Confidence can be calibrated metadata, not a prose-quality trait.

**E10 — Repository/design facts.** `rubric-design.md:378-407` maps seven LAMP rows but summarizes only three gaps. `packages/slopvac-lint/src/slopvac/rules/orwell.yml:7-31` is a finite stale-figure token list, not an open-set cliché judgement. `prose-discipline.yml:375-422` names the actual sentence rule `overloaded-sentence`, not `one-sentence-one-idea`. `prose-craft.yml:17-65` covers future-tense default and complex verb chains, not cross-sentence tense inconsistency. `ai-tells-agentic.yml:468-537` covers summary closers, not general redundant exposition.

## Alternatives

| Rank | Alternative | Likelihood | What follows |
|---|---|---:|---|
| 1 | Keep all four, describe them as **separately scored/non-interchangeable**, and score HARM/REPAIR per finding. | High | Preserves §5’s useful diagnostics without claiming psychometric independence. |
| 2 | If calibration forces a merge, combine FIT+WARRANT into **VALIDITY**, not HARM+REPAIR. | Medium | Saves one score, but loses the distinction between a genuine weakly evidenced defect and strong evidence for a near-match; §5 can no longer report which admission gate failed. |
| 3 | Merge HARM+REPAIR into one priority score. | Low | Conflates consequence with edit effort, contrary to MQM and post-editing evidence (E4, E6). |

## Strongest counter

MQM’s architecture is the closest mature analogue and is explicit: category weight is configured globally, but severity is assigned to the particular error instance. C2 currently collapses those two different quantities into a per-rule HARM constant.

## Amendments

### C2 replacement

> **Four separately scored checks.** FIT, HARM, WARRANT, and REPAIR are ordinal 0–3 checks. They are separately reported and non-interchangeable; independence is an empirical question, not a rubric premise. FIT and WARRANT are mandatory for every candidate. HARM and REPAIR are scored for each admissible finding. A rule mask may mark a check inapplicable, but must not inject a constant score. Optional profile-specific `error_type_weight` may express category importance; it never replaces instance-level HARM. Keep the current §5 thresholds provisionally until double-rated calibration establishes per-check agreement and correlations.

Schema cutover:

```text
dims: {fit: score, harm: score, warrant: score, repair: score}
error_type_weight: optional positive multiplier  # aggregation only
```

### C13 replacement

> **LAMP coverage is a rule-coverage audit, not a new score dimension.** Use the paper’s seven labels verbatim. Current complete/partial/gap status: cliché—**partial, add open-set judgement remainder**; poor sentence structure—**covered by `prose-discipline.overloaded-sentence` plus STE rules**; awkward word choice/phrasing—**partial, add consumer-register remainder**; unnecessary/redundant exposition—**partial, add general exposition remainder**; lack of specificity/detail—**covered**; purple prose—**gap**; tense inconsistency—**gap**. Thus five rows need rule work; three are wholly or materially uncovered.

### C14 replacements

- **Scalar 1–10:** “Do not use as finding admission. MAY retain only as an evaluation baseline or document-level external criterion.”
- **Per-dimension packs:** “Do not ship in v1 because cross-call candidate identity and cost are unresolved. Evaluate as an anti-halo control; recombine only by deterministic candidate ID.”
- **Confidence:** “Not a quality dimension. MAY emit calibrated uncertainty metadata or abstain; never aggregate it into severity.”
- **Register:** “Not a universal dimension. Encode target register in profile/rule applicability and score concrete mismatches through FIT/HARM/WARRANT/REPAIR.”
- **Originality:** “Never infer authorship or provenance. Encode observable cliché, staleness, or imitation as named rules; do not add an originality dimension.”

## Unsupported

- No evidence found validating FIT/HARM/WARRANT/REPAIR as a four-factor structure.
- No evidence found that 0–3 is more reliable than 0–2, 1–4, or 1–5 for this task.
- No evidence found that HARM or REPAIR has negligible within-rule variance.
- No evidence found for “confidence correlates with every other axis” or “per-dimension packs destroy worst-dimension semantics.”
- WQRM supplies neither criterion-level IAA nor factor analysis; it cannot validate C2.

## Open evaluation questions

1. Double-rate a stratified sample of repo findings; report weighted κ per check, polychoric correlations, and factor/effective-rank results.
2. Compare dynamic HARM/REPAIR with proposed constants per rule; measure within-rule variance and severity-decision flips.
3. Randomize score order and compare joint versus separated packs to quantify halo without changing candidate identity.
4. A/B four checks against merged FIT+WARRANT; measure false-confirm, abstain, and actionable-diagnosis rates.
5. Label LAMP-category cases from this repository and measure both span precision and categorical precision, mirroring LAMP’s **.57/.23** distinction.
6. Keep a 1–10 document score only as a blinded external baseline; test whether four-check decisions predict editor preference better.
7. Calibrate any confidence metadata with ECE/Brier score and test length bias; do not treat it as prose quality.