Claim: The design is right to separate abstention from prose-quality scores, but its universal WARRANT threshold, byte-offset contract, and four-member abstention enum are not supported by the evidence.

VERDICT: CHALLENGED

## Verdicts

| Claim ID | Decision | One-line reason | Evidence |
|---|---|---|---|
| C3 | AMEND | Reject-option theory makes uncertainty a selection signal, not a quality label; confidence may drive a calibrated gate, so “never a dimension” is sound only if it does not mean “never used.” Protectedness likewise belongs before defect scoring. | E1–E5, E12 |
| C4 | REPLACE | Exact, mechanically validated excerpts materially improve attribution, and relational defects need multiple localized mentions; however, no source supports universal `WARRANT>=2`, exactly two items for every non-local rule, or byte offsets over normalized Python strings. | E6–E11, E13–E14 |
| C8 | REPLACE | First-class abstention and its coverage cost are strongly supported, but the list omits missing/incomplete context, external-fact dependence, and conflicting evidence; reason and evidence source must be separate fields. | E1–E5, E15 |

## Evidence

**E1.** [Franc, Prusa & Voracek, JMLR 2023](https://jmlr.org/papers/volume24/21-0048/21-0048.pdf), pp. 1–11: a selective classifier is explicitly decomposed into predictor `h` and selection function `c`; uncertainty orders cases for acceptance, while selective risk and coverage remain separate objectives. The cost-based, bounded-risk, and bounded-coverage formulations yield the same thresholded rejection strategy. Source gives no empirical accuracy number. This supports a gate rather than adding uncertainty to FIT/HARM/WARRANT/REPAIR, but permits calibrated confidence as the gate input.

**E2.** [Kamath, Jia & Liang, ACL 2020](https://aclanthology.org/2020.acl-main.503.pdf), Table 1: under QA domain shift, a trained calibrator could retain **56.06% coverage at 80% accuracy** and **29.42% at 90% accuracy**; the best-possible selector reached **74.92%** and **66.59%** respectively. Confidence therefore has decision value, but only through an empirically measured risk–coverage curve.

**E3.** [Menick et al., GopherCite 2022](https://arxiv.org/pdf/2203.11147), §§1, 3.3 and Fig. 4: when forced to attempt all filtered NaturalQuestions, supported-and-plausible quality was **80%**; abstaining on about **30%** raised attempted-answer quality above **90%**. On ELI5 it rose from **67%** overall to above **80%** at **70% coverage**. This directly quantifies the cost of forcing answers and supports counting abstentions against coverage.

**E4.** [Madhusudhan et al., COLING 2025](https://aclanthology.org/2025.coling-main.627.pdf), Tables 1–3: on PopQA, GPT-4 Turbo’s ordinary prompt had answerable accuracy **91.2**, unanswerable accuracy **83.6**, and abstention rate **45.9**; a strict abstention prompt changed these to **87.0**, **97.8**, and **59.5**. Abstention improved unanswerable accuracy by **14.2 points** but cost **4.2 points** on answerable cases. Coverage alone is therefore insufficient; valid and excessive abstention must both be measured.

**E5.** [Kadavath et al. 2022](https://arxiv.org/abs/2207.05221): models can estimate whether their own answers are correct, and those probabilities are generally calibrated across several tasks; the abstract gives no aggregate number. This refutes any reading of C3 that bans confidence from the selector, while not making confidence a prose-quality dimension.

**E6.** [Weller et al., EACL 2024](https://aclanthology.org/2024.eacl-long.140.pdf), Table 1: QUIP-trained models produced quotations matching the source corpus **99.9%** of the time versus **17.0%** for the untuned LLaMA-65B baseline. The paper tests source quotations, not linter findings, but supplies the requested exact-substring rate and shows that verbatim evidence is not obtained reliably from an unconstrained model merely by asking.

**E7.** [Slobodkin et al., ACL 2024](https://aclanthology.org/2024.acl-long.182.pdf), §§2–5, Tables 2–4: selected spans are located by string matching and undetectable spans are omitted; fine-tuned selection uses constrained decoding for lexical identity. In LFQA human evaluation, attribute-first raised AIS from **87.6 to 94.4** (**+6.8 points**) while shortening average cited text from **59 to 35 tokens**; reported unattributed-sentence rate is **0.0%** for attribute-first versus **26.9%** for the ALCE baseline in the automatic table. These are attribution/support results, not proof that every prose verdict becomes correct.

**E8.** [Gao et al., ALCE, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/): even the best evaluated ELI5 system lacked complete citation support **50% of the time**. Citation presence alone is inadequate; entailment/relevance still needs WARRANT scoring after exact-span validation.

**E9.** [Menick et al.](https://arxiv.org/pdf/2203.11147), §§2.6 and 5: their contract deliberately splits a mechanical check—special syntax proving a quote verbatim—from a human support judgment. A quote can be exact yet misleading; source gives examples but no aggregate misleading-evidence rate. This is direct support for `evidence_ok` before, not in place of, WARRANT.

**E10.** [Pradhan et al., CoNLL coreference scorer](https://aclanthology.org/W10-4305.pdf), §§1–3: coreference evaluation represents a response through mention spans grouped into entities and scores links/clusters with MUC, B³ and CEAF. Source gives **three** principal metrics, not a prescribed two-evidence schema. It supports localized mention spans and at least two participants for a claimed relation, but not “exactly two” for chains with three or more mentions.

**E11.** [Ai et al., TeCS, ACL 2023](https://aclanthology.org/2023.acl-short.164/), §§2–4: the tense benchmark uses **552 paired utterances** containing **780 tense structures**, and accuracy compares the predicted utterance’s tense with its reference. This supports paired, role-labelled evidence for inconsistency; it does not establish universal arity 2 for every non-local prose defect.

**E12.** Repository `packages/slopvac-lint/src/slopvac/model.py:31-39` defines prose scope as excluding code fences, inline code, URLs, and front matter, while raw scope includes them. Protectedness is already a deterministic applicability distinction, not prose quality. Source gives no evaluation number.

**E13.** Design `rubric-design.md:132-155` calls ranges “byte offsets” but validates them by Python slicing, `text[start-range.start:end-range.start]`; Python string indices are Unicode code-point indices, not UTF-8 byte offsets. The contract is internally inconsistent before any model error occurs.

**E14.** Repository `packages/slopvac-lint/src/slopvac/analyze.py:582-597,625-628,665-674` strips visible text, joins pieces with synthesized spaces, and retains source **line starts**, not a byte-for-byte source map. Therefore offsets into `unit.text` cannot also identify raw-file bytes without a new deterministic projection map.

**E15.** [Wen et al., “Know Your Limits,” TACL 2025](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00754/131566/Know-Your-Limits-A-Survey-of-Abstention-in-Large): its query taxonomy separately includes incomplete/ambiguous input, irrelevant or insufficient context, misleading questions, and knowledge conflict, in addition to model knowledge limits and alignment. Source gives no single accuracy number. C8 conflates some of these and omits others applicable to prose review.

## Amendments

### C3 replacement wording

> Evaluate admission, preservation/protectedness, and abstention before FIT/HARM/WARRANT/REPAIR. Uncertainty is not a prose-quality dimension. A calibrated confidence or uncertainty signal MAY select abstention, but MUST NOT be emitted as a fifth score or treated as evidence. Evaluate any selector on held-out data with risk–coverage curves and calibration error; raw self-reported confidence is insufficient.

### C4 replacement contract

> `evidence_ok` requires every evidence quote to equal the identified source-text slice exactly. Store `evidence_source: unit | context | repository`, a stable source identifier, and Unicode code-point offsets relative to that source text; call them byte offsets only when a deterministic UTF-8 source map proves raw-file byte positions. Local defects require one defect span. Relational/non-local defects require the rule-declared minimum arity—at least two—with rule-declared roles; chains MAY require more than two. A confirm requires `WARRANT>=1` when the entire claim is demonstrated by the localized text, and `WARRANT>=2` only when the rule depends on a second named/checkable particular. Missing or invalid required evidence yields abstention.

Proposed enum/value changes: `evidence_arity: {min: 1..N, roles: [...]}` rather than `1 | 2`; offset unit `unicode_codepoint`; role names remain rule-declared rather than globally pretending five roles cover every relation.

### C8 replacement contract

> `abstain_reason` is a closed enum: `no_exact_evidence | needs_repository_fact | needs_external_fact | ambiguous_unit | missing_context | conflicting_context | unit_out_of_scope`. `truncated_document` maps to `missing_context`; a withheld verdict requiring a non-repository fact maps to `needs_external_fact`. Evidence location is not an abstention reason and MUST be recorded separately as `unit | context | repository`. Every abstention reduces coverage among admissible, non-preserved units. Also report reason-specific abstention rates, selective risk on accepted verdicts, and invalid-abstention rate on answerable gold cases.

## Unsupported

- **Universal `WARRANT>=2`:** no evidence found that an exact, sufficient local span must also name a number, identifier, owner, source, or second passage. It would force score inflation or abstention for observable local defects.
- **Exactly two evidence objects for all non-local defects:** no evidence found. Coreference practice permits entity chains larger than two; the defensible invariant is per-rule minimum arity.
- **The five global role names:** no evidence found that they are complete across all repository judgment rules.
- **Raw-file byte offsets from the current projection:** refuted by E13–E14.
- **Treating all abstentions as equally good:** unsupported. E4 shows over-abstention can lower answerable accuracy even while unanswerable accuracy rises.

## Open evaluation questions

1. On a stratified gold set of this repository’s judgment rules, what precision and coverage result from `WARRANT>=1` versus `>=2`, separately for local and relational rules?
2. What fraction of raw model quotes fail exact-substring validation under verdict-first, quote-first, and constrained/copy selection? Report accepted-span fabrication as **0 only after mechanical validation**, not as model accuracy.
3. Does minimum arity 2 improve precision for anaphora, repetition, term, and tense inconsistency, and how often do gold cases require three or more spans?
4. Plot risk–coverage and invalid-abstention curves for evidence validity, calibrated confidence, and their conjunction; do not infer selector quality from self-reported confidence.
5. Measure each proposed abstention reason’s prevalence and inter-annotator validity, especially `missing_context`, `conflicting_context`, and external-versus-repository fact dependence.
6. Verify offset round-trips on ASCII, multibyte Unicode, Markdown links/code, HTML entities, and synthesized inter-line spaces before choosing code-point or raw-byte coordinates.

## Strongest counter

The design says WARRANT 2 is what makes a finding “a claim about the text,” but its own WARRANT 1 already requires a localized excerpt. Published attribution systems instead separate exact mechanical localization from semantic support. Making a named particular mandatory for every defect does not improve localization; it changes the construct and predictably converts valid local findings into abstentions or falsely elevated WARRANT scores.