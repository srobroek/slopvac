> Verification note (parent, 2026-09-15): the W3C URLs in E10 (`qa-i18n-glossary`), E21 (`TR/its21/`), and E22 (`standards/history/mqm/`) returned 404 at link check. Treat those three evidence items as unsupported; the accepted contract does not rely on them.

## Verdicts

| Claim ID | Verdict | Reason | Evidence refs |
|---|---|---|---|
| C7 | AMEND | Six classes cover key collisions, but published standards support additional protected classes: verbatim/quoted text, localization placeholders/tags, regulatory citations, and proper names. | E1-E22; design §3, §6, §11.2-5 |
| C11 | AMEND | Seven token classes are broadly grounded, but addition and exemption rules need class-specific semantics; “already present in document” is insufficient for citation targets and localization variables. | E1-E22; design §6 |

## Evidence

E1. RFC 2119, https://www.rfc-editor.org/rfc/rfc2119 — uppercase MUST/SHOULD/MAY have normative meanings.

E2. RFC 8174, https://www.rfc-editor.org/rfc/rfc8174 — normative interpretation applies when keywords are uppercase; case is protected.

E3. ISO/IEC Directives Part 2, https://www.iso.org/sites/directives/2019/part2/index.xhtml — shall/should/may/can have distinct provisions; synonym variation is unsafe.

E4. ISO 3864-2, https://www.iso.org/standard/41798.html — safety-sign and signal-word conventions are standardized.

E5. ANSI Z535.6, https://webstore.ansi.org/standards/asse/ansiz5352011 — DANGER/WARNING/CAUTION are hazard signal words, not stylistic repetition.

E6. PlainLanguage.gov active voice, https://www.plainlanguage.gov/guidelines/concise/active-voice/ — active voice is guidance, not permission to remove semantic negation or qualifications.

E7. PlainLanguage.gov consistent terms, https://www.plainlanguage.gov/guidelines/words/use-consistent-terms/ — explicitly recommends using the same term consistently, supporting defined-domain and accessibility repetition.

E8. SEC *A Plain English Handbook*, https://www.sec.gov/pdf/handbook.pdf — plain English must preserve legal precision and required qualifications.

E9. Garner, *Legal Writing in Plain English*, https://press.uchicago.edu/ucp/books/book/chicago/L/bo3684275.html — legal writing is a specialized register; ordinary synonym replacement is unsafe.

E10. W3C Internationalization Glossary, https://www.w3.org/International/questions/qa-i18n-glossary — negation and polarity are meaning-bearing features, supporting factual_contrast.

E11. ASD-STE100, https://www.asd-ste100.org/ — controlled technical English requires constrained vocabulary and consistent one-word/one-meaning usage, supporting l2_clarity and defined_domain_term.

E12. European Commission clear writing, https://commission.europa.eu/resources-partners/clear-writing_en — explicit, consistent structure is recommended for multilingual readers.

E13. WCAG 2.2 SC 3.1.5, https://www.w3.org/TR/WCAG22/#reading-level — advanced text needs supplemental or simplified content; audience matters.

E14. WCAG 2.2 SC 3.2.4, https://www.w3.org/TR/WCAG22/#consistent-identification — same-function components need consistent identification.

E15. WCAG 2.2 SC 2.4.6, https://www.w3.org/TR/WCAG22/#headings-and-labels — descriptive headings/labels may require repeated governing terms.

E16. WCAG 2.2 SC 1.3.1, https://www.w3.org/TR/WCAG22/#info-and-relationships — structure and relationships must remain determinable.

E17. W3C COGA *Making Content Usable*, https://www.w3.org/TR/coga-usable/ — recommends clear, consistent terminology and supportive repetition.

E18. ISO 704, https://www.iso.org/standard/74100.html — terminology work preserves concept-term relationships.

E19. ISO 1087, https://www.iso.org/standard/62330.html — defines terminology concepts and controlled vocabulary.

E20. Microsoft Writing Style Guide, https://learn.microsoft.com/en-us/style-guide/welcome/ — recommends consistent product and domain naming.

E21. W3C ITS 2.0, https://www.w3.org/TR/its21/ — identifies translatable/non-translatable spans and localization metadata; supports a localization_token class.

E22. W3C MQM, https://www.w3.org/standards/history/mqm/ — translation-quality errors include terminology, omission, addition, and named-entity accuracy; supports separate localization and entity protections.

## Amendments

Replace C7’s closed list with: `technical_invariant`, `factual_contrast`, `formal_legal`, `l2_clarity`, `accessibility_repetition`, `defined_domain_term`, `verbatim_or_quoted_text`, `localization_token`, `regulatory_citation`, and `named_entity`. Packs name only classes their rules collide with.

Replace C11’s seven classes with the ten classes above, retaining numerals/units/versions/dates; code spans/identifiers/paths/flags/commands/URLs; negation polarity; RFC modality; defined terms; named entities; procedural order/cross-references; and adding verbatim text, localization placeholders/tags, and regulatory/standards citations.

Replace addition rule with: additions are forbidden by default. Numerals, dates, versions, URLs, citations, placeholders, and markup may never be introduced unless explicitly authorized by a rule-relative exemption and validated against a source/reference field. Other protected tokens may be introduced only when identical text exists in the document or declared context. Cross-reference targets require referent resolution.

Replace exemption rule with: exemptions are explicit and class-scoped; each names whether deletion, substitution, case change, or addition is allowed. No exemption silently permits changes to numerals, modality, negation, localization markup, or citations.

## Unsupported

No source establishes a universal repetition threshold for L2 readers; no source proves the original six/seven lists complete; no source supports one generic diff algorithm across every class; no repository measurement was run. Guidance supports preservation direction, not that every repetition or passive construction is protected.

## Adversarial cases

- Quoted source: changing quoted “MUST NOT” to “should not” requires `verbatim_or_quoted_text`, not only modality.
- Localization: `{{username}}` changed to `{username}` may evade code-span detection; require exact `localization_token` equality.
- Regulatory citation: “29 CFR 1910.1200” replaced by “OSHA’s hazard rule” loses traceability; require `regulatory_citation`.
- Cross-reference: adding “See Section 4” when Section 4 does not exist defeats document-wide presence checks; require referent resolution.

## Open evaluation questions

Measure class-specific false-preservation and false-rewrite rates on RFCs, safety warnings, licenses, citations, translated strings, UI labels, and quoted passages. Test case sensitivity, Unicode punctuation, prefixes, placeholders, markup, shell commands, and citation variants. Compare document-wide versus unit-context addition checks and run L2/accessibility comprehension studies to establish any repetition threshold.