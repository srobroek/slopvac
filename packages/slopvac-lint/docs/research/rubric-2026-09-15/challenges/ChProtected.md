Claim: C7 identifies several genuine preservation hazards, but its closed classes are overbroad and omit two evidenced hazards; C11’s token inventory is mostly grounded, while its bag-of-tokens addition rule and class-wide exemptions are not.

VERDICT: CHALLENGED

## Verdicts

| Claim ID | Verdict | One-line reason | Evidence |
|---|---|---|---|
| C7 | REPLACE | Keep technical invariants, polarity/contrast, and defined terms; narrow legal/L2/accessibility classes, add normative obligations and quoted/source-locked text, and do not treat generated origin itself as semantic protection. | E1–E12, E16 |
| C11 | REPLACE | All seven areas contain real accuracy risks, but surface-token identity is neither necessary nor sufficient for fidelity; document-wide token presence and class-wide exemptions create both bypasses and false vetoes. | E1–E5, E10–E16 |

## Evidence

**E1.** [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html) assigns distinct force to MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY; changing or deleting one changes the obligation. [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html) limits those meanings to all-uppercase forms. Source gives no quantitative result.

**E2.** [ISO/IEC Directives Part 2](https://www.iso.org/sites/directives/current/part2/index.xhtml) requires prescribed verbal forms: “shall” for requirements, “should” for recommendations, “may” for permission, and “can” for possibility/capability; it also says terms and definitions shall use a consistent style. Source gives no quantitative result.

**E3.** [ANSI on Z535.4](https://blog.ansi.org/ansi/ansi-z535-4-2023-product-safety-sign-or-label/) distinguishes DANGER, WARNING, CAUTION, and NOTICE by hazard severity; [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf) §7.1 likewise reserves WARNING for injury/death and CAUTION for equipment damage. Generic synonym substitution changes the risk classification. Source gives no quantitative result.

**E4.** The US National Archives’ [clear legal writing guide](https://www.archives.gov/federal-register/write/legal-docs/clear-writing.html) says positive form is preferable only when either form can be expressed “accurately”; its examples retain prohibitions where that is the rule. [MQM Full](https://www.themqm.org/mqm-pillars/the-mqm-full-typology/) makes omitted negation its canonical mistranslation example (“should not” becoming “should”). Source gives no quantitative result.

**E5.** Tang et al., [“Revisiting Negation in Neural Machine Translation”](https://aclanthology.org/2021.tacl-1.45/), manually measured negation accuracy at 95.7%, 94.8%, 93.4%, and 91.7% in four directions—non-zero error despite mature systems. The corpus study [“Contrastive *not…but* Constructions”](https://journals.sagepub.com/doi/10.1177/00754242231195369) distinguishes additive and corrective/replacement readings; deleting either pole does not preserve that relation. The latter source gives no reported number in its accessible finding.

**E6.** The [SEC Plain English Handbook](https://www.sec.gov/pdf/handbook.pdf) advocates active voice, shorter sentences, and concrete words in legal disclosure, so “formal legal” is not categorically rewrite-forbidden. The [U.S. Courts 2024 drafting guide](https://www.uscourts.gov/sites/default/files/essentials_for_drafting_clear_legal_rules_2024.pdf) reports only a handful of substantive adjustments across hundreds of rules and thousands of provisions after plain-language redrafting. Protection must turn on legal/source authority, not register.

**E7.** Creative Commons says in [Legal Code Defined](https://creativecommons.org/legal-code-defined/) that changing legal code creates a modified, nonstandard license that must not be represented as a CC license. Conversely, [SPDX license matching](https://spdx.github.io/spdx-spec/v3.0.1/annexes/license-matching-guidelines-and-templates/) expressly tolerates specified whitespace, capitalization, punctuation, and replaceable-text variations. Legal fidelity is therefore source- and transformation-specific, not byte-identity for all legal prose. Sources give no quantitative result.

**E8.** Google’s [global-audience guide](https://developers.google.com/style/translation) explicitly says to repeat a word when redundancy improves comprehension, use helper words such as “then” and “that,” and use the exact same term/capitalization for a concept. Source gives no quantitative result.

**E9.** Zufferey et al.’s [L1/L2 connective experiments](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.685491/full) recruited 80 L1 and 80 L2 readers per experiment; in Experiment 1, explicit connectives benefited L2 readers by about 100 ms, while native readers processed contrast with or without one. This supports audience-conditioned preservation, not an unqualified `l2_clarity` escape hatch.

**E10.** [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf) requires one word for one meaning (§1.1), reuse of approved words (§1.5), approved technical names (§1.6), and says quoted placard/document text cannot be changed into STE (§8.1). It also shows an active-voice conversion that changes a fact, requiring passive voice (§3.6). Source gives no quantitative result.

**E11.** WCAG 2.2 [SC 3.2.4](https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html) (AA) covers consistent identification of components with the same functionality; [SC 2.4.6](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html) (AA) requires descriptive headings/labels, not verbatim repetition. [SC 1.3.1](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html) covers programmatically available structure; [SC 3.1.5](https://www.w3.org/WAI/WCAG22/Understanding/reading-level.html) is AAA and concerns reading level. None supports protecting arbitrary repetition. Sources give no quantitative result.

**E12.** W3C COGA’s [clear-content objective](https://www.w3.org/WAI/WCAG2/supplemental/objectives/o3-clear-content/) calls for simple, unambiguous content; the federal [same-terms guidance](https://www.plainlanguage.gov/guidelines/words/use-the-same-terms-consistently/) and [Microsoft Style Guide](https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences) require one term consistently for one concept. These support `accessibility_consistency`, not `accessibility_repetition`. Sources give no quantitative result.

**E13.** [ISO 704:2022](https://www.iso.org/standard/79077.html) standardizes principles and methods for terminology work; Microsoft and Google (E8/E12) explicitly reject synonym variation for one concept. `defined_domain_term` is supported. Source gives no quantitative result.

**E14.** [Crowdin QA checks](https://support.crowdin.com/project-settings/qa-checks/) separately check tag, variable, special-character, terminology, and number mismatches. [W3C `translate=no`](https://www.w3.org/International/questions/qa-translate-flag) protects keywords, code, proper nouns, and source examples; [XLIFF 2.1](https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html) is designed for lossless interchange and protected inline codes. Sources give no quantitative result.

**E15.** MQM (E4) defines accuracy semantically as distortion, omission, or addition; it has separate Number, Date/time, Entity, Omitted variable, Do-not-translate, and terminology errors, but also says explicitation and unit conversion can be appropriate. It does not support “new numeral always forbidden” or “present elsewhere in the document means authorized.” Source gives no quantitative result.

**E16.** `rubric-design.md:215-242` combines step order with cross-references, permits any nonnumeric protected token already anywhere in the document, and exempts whole token classes. Repo rules show the required legitimate changes are narrower: `packages/slopvac-lint/src/slopvac/rules/ste-safety.yml:24-43` changes a risk marker, while `packages/slopvac-lint/src/slopvac/rules/ste-words.yml:347-379` replaces a phrase with an externally authorized glossary term. Document membership proves neither authorization nor correct location.

## Amendments

### C7 replacement enum and anchors

```text
preservation_reason ∈ {
  normative_obligation,
  factual_polarity_or_contrast,
  source_locked_legal_text,
  controlled_language_clarity,
  accessibility_consistency,
  authoritative_domain_term,
  quoted_specimen
}
```

- `normative_obligation`: changing requirement force, permission, prohibition, default, safety level, or operational contract would change behavior; covers RFC/ISO keywords and repo policy, not only “technical” prose.
- `factual_polarity_or_contrast`: the allegedly removable wording carries negation, exception, correction, or the two poles of a contrast.
- `source_locked_legal_text`: the span is authoritative license/warranty/contract text identified by source metadata; ordinary legal-register prose is not protected.
- `controlled_language_clarity`: an explicitly configured L2/controlled-language profile requires repeated nouns, exact terms, or explicit connectives; audience guesswork is insufficient.
- `accessibility_consistency`: repetition identifies the same function, label, instruction, or concept for an accessibility need; arbitrary repeated prose is not protected.
- `authoritative_domain_term`: a cited glossary/schema/API/termbase fixes the designation.
- `quoted_specimen`: exact quoted/example/source text is evidence and may not be silently edited.

`generated_schema` is not an enum member: generated origin is an admission/exclusion property. A generated fragment is protected only when source metadata makes it `quoted_specimen` or authoritative terminology/schema content.

### C11 replacement checker

```text
Compare typed, located facts—not document-wide token sets.
For each protected occurrence, require semantic equivalence and referent/location preservation.
Allow additions only when authorized by (a) the source occurrence under a declared normalization,
(b) a cited glossary/schema/repository referent, or (c) an exact rule-specific transition.
Never treat occurrence elsewhere in the document as authorization.
```

Split class 7 into `procedure_dependency` and `cross_reference_target`. Permit spelled-number↔digit, date-format, unit, case, and punctuation normalizations only through typed canonicalizers. Replace `rewrite_exempt: [class]` with exact transformations, e.g. `allowed_transition: {class: safety_signal, from: WARNING, to: DANGER}` plus the rule’s postcondition. No numeric thresholds are warranted.

## Unsupported

- **Unsupported as written:** `formal_legal`, `l2_clarity`, and `accessibility_repetition` are too broad; literature supports the narrowed replacements above.
- **Supported additions:** `normative_obligation`/`operational_normative` and `quoted_specimen`.
- **Unsupported as a preservation class:** `generated_schema`; evidence supports origin-based exclusion or source locking, not automatic semantic immunity.
- **Unsupported C11 policies:** “numerals never added,” “token found elsewhere may be added here,” absolute cross-reference preservation, and class-wide rule exemptions.

## Open evaluation questions

1. On this repo, what are false-veto and unsafe-pass rates for typed canonical equivalence versus exact token identity?
2. How often does document-membership authorize a wrong-location MUST, identifier, term, number, or entity? Include matched adversarial controls.
3. Can reviewers reliably distinguish ordinary legal prose from source-locked legal text, and L2/accessibility consistency from mere repetition?
4. Mutation-test every class: negate, weaken modality, swap safety level/entity/number, reorder dependent steps, retarget a cross-reference, and alter a quote.
5. For each rule exemption, does an exact-transition allowlist admit the intended fix and reject every other alteration in that class?