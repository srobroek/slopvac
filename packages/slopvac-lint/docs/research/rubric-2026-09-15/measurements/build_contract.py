"""Build rubric-contract.json (sorted keys, ID-ordered lists) and its sha256."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib

OUT = pathlib.Path(os.environ.get("SLOPVAC_CONTRACT_OUT", pathlib.Path(__file__).resolve().parents[1]))
SOURCE_COMMIT = "df7ba4412387c474dc8ef646a8d594dc44c1c7eb"

PRESERVATION = [
    {"id": "accessibility_consistency", "replaces": "accessibility_repetition",
     "definition": "Repetition that identifies the same function, label, instruction, or concept for an accessibility need. Arbitrary repeated prose is not protected.",
     "basis": ["https://www.w3.org/WAI/WCAG22/Understanding/consistent-identification.html", "https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html", "https://www.plainlanguage.gov/guidelines/words/use-the-same-terms-consistently/"],
     "deterministic_signals": ["same term repeated as heading, label, or UI string across the document", "profile declares an accessibility audience"]},
    {"id": "authoritative_domain_term", "replaces": "defined_domain_term",
     "definition": "A cited glossary, schema, API, or termbase fixes the designation; the term may not be varied, shortened, or replaced by a synonym.",
     "basis": ["https://www.iso.org/standard/79077.html", "https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences", "https://developers.google.com/style/translation"],
     "deterministic_signals": ["term appears in the configured vocabulary or glossary", "term is a code identifier, path, flag, or product name"]},
    {"id": "controlled_language_clarity", "replaces": "l2_clarity",
     "definition": "An explicitly configured L2 or controlled-language profile requires repeated nouns, exact terms, or explicit connectives. Audience guesswork is insufficient.",
     "basis": ["https://www.asd-ste100.org/", "https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.685491/full", "https://developers.google.com/style/translation"],
     "deterministic_signals": ["profile or genre declares an L2, translation-source, or STE audience"]},
    {"id": "factual_polarity_or_contrast", "replaces": "factual_contrast",
     "definition": "The allegedly removable wording carries negation, exception, correction, or the two poles of a factual contrast; deleting either pole changes what is asserted.",
     "basis": ["https://www.themqm.org/mqm-pillars/the-mqm-full-typology/", "https://aclanthology.org/2021.tacl-1.45/", "https://journals.sagepub.com/doi/10.1177/00754242231195369"],
     "deterministic_signals": ["negation or exception marker inside the quoted span or its antecedent", "both poles name checkable particulars (numbers, identifiers, actors)"]},
    {"id": "normative_obligation", "replaces": "technical_invariant",
     "definition": "Changing requirement force, permission, prohibition, default, safety level, or an operational contract would change behaviour. Covers RFC 2119 and ISO verbal forms, safety signal words, and repository steering markers (MUST/NOT/DEFAULT/SHOULD/MAY), not only technical prose.",
     "basis": ["https://www.rfc-editor.org/rfc/rfc2119.html", "https://www.rfc-editor.org/rfc/rfc8174.html", "https://www.iso.org/sites/directives/current/part2/index.xhtml", "https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf"],
     "deterministic_signals": ["uppercase RFC 2119 keyword or repository steering marker in the unit", "signal word DANGER, WARNING, CAUTION, NOTE, NOTICE", "unit is inside a normative block (RFC boilerplate, rules section, skill steering)"],
     "not_applied_to": "a rule whose criterion adjudicates the protected token itself (rule record field `adjudicates` names this class); ste-safety.risk-level-word-missing-or-wrong judges the signal word and is never preserved by it"},
    {"id": "quoted_specimen",
     "definition": "Exact quoted, example, or source text that is evidence or documentation of the thing it exhibits. It may not be silently edited. Includes rule specimens, blockquotes, fenced examples, and reproduced third-party text.",
     "basis": ["https://www.w3.org/International/questions/qa-translate-flag", "https://creativecommons.org/legal-code-defined/", "packages/slopvac-lint/docs/rules.md (530 specimens read as 530 findings; slopvac.toml:19-25)"],
     "deterministic_signals": ["unit region_class is quoted (Markdown blockquote, fenced block, or example list item)", "unit text equals a rule example, fixture line, or cited source string"],
     "precedence": "evaluated after A5 origin exclusion: a generated quoted region is DROP (A5), an authored quoted region is PRESERVE"},
    {"id": "source_locked_legal_text", "replaces": "formal_legal",
     "definition": "Authoritative licence, warranty, or contract text identified by source metadata (LICENSE files, SPDX-matched text, reproduced terms). Ordinary legal-register prose is not protected and may be reviewed under plain-language guidance.",
     "basis": ["https://creativecommons.org/legal-code-defined/", "https://spdx.github.io/spdx-spec/v3.0.1/annexes/license-matching-guidelines-and-templates/", "https://www.sec.gov/pdf/handbook.pdf"],
     "deterministic_signals": ["file is LICENSE*, NOTICE*, or matches an SPDX licence template", "unit is inside a reproduced licence or warranty block"]},
]

ABSTENTION = [
    {"id": "ambiguous_unit", "definition": "The unit boundary or the referent of the criterion inside it cannot be fixed from the unit and its context."},
    {"id": "conflicting_context", "definition": "The unit and its context support incompatible readings and neither can be settled from the document."},
    {"id": "inconsistent_output", "definition": "Host-assigned: the model's verdict disagrees with the host-derived outcome (a schema-valid confirm with fit=absent, a preserve without reason). The model never emits this reason."},
    {"id": "missing_context", "definition": "A required antecedent, referent, or remainder of the document is not available to the call (includes truncated documents)."},
    {"id": "needs_external_fact", "definition": "Deciding requires a fact outside the repository (a real-world figure, a third-party document)."},
    {"id": "needs_repository_fact", "definition": "Deciding requires a repository artefact not supplied (a glossary, schema, config, or file the unit refers to)."},
    {"id": "no_exact_evidence", "definition": "No span in the permitted evidence sources exactly exhibits the shape the criterion names."},
    {"id": "unit_out_of_scope", "definition": "The unit is admissible but the criterion cannot be answered at this scope (a document-scope question on a paragraph unit)."},
]

TOKEN_CLASSES = [
    {"id": "code_and_identifiers", "members": "code spans, identifiers, paths, flags, commands, URLs, placeholders, tags", "basis": ["https://support.crowdin.com/project-settings/qa-checks/", "https://docs.oasis-open.org/xliff/xliff-core/v2.1/xliff-core-v2.1.html"]},
    {"id": "cross_reference_target", "members": "section references, anchors, figure/table numbers, step numbers referred to elsewhere", "basis": ["https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html"]},
    {"id": "defined_terms", "members": "glossary entries, configured vocabulary, product and API names used as terms", "basis": ["https://www.iso.org/standard/79077.html"]},
    {"id": "modality", "members": "RFC 2119 keywords and repository steering markers MUST/NOT/DEFAULT/SHOULD/MAY/NEVER/AVOID; safety signal words", "basis": ["https://www.rfc-editor.org/rfc/rfc2119.html", "https://www.rfc-editor.org/rfc/rfc8174.html"]},
    {"id": "named_entities", "members": "people, organisations, products, places", "basis": ["https://www.themqm.org/mqm-pillars/the-mqm-full-typology/"]},
    {"id": "negation_polarity", "members": "not, no, never, without, un-/non- prefixes on kept words, exception markers (unless, except)", "basis": ["https://www.themqm.org/mqm-pillars/the-mqm-full-typology/", "https://aclanthology.org/2021.tacl-1.45/"]},
    {"id": "numerals_units_versions_dates", "members": "numerals (digit or spelled), units, version strings, dates, percentages", "basis": ["https://support.crowdin.com/project-settings/qa-checks/", "https://www.themqm.org/mqm-pillars/the-mqm-full-typology/"]},
    {"id": "procedure_dependency", "members": "order of steps whose later step depends on an earlier one; conditions attached to commands", "basis": ["https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf"]},
]

DIMENSIONS = [
    {"id": "fit", "question": "Does the shape this criterion names occur in this unit?", "mandatory": True, "maskable": False, "order": 1,
     "levels": [
         {"code": 0, "id": "absent", "anchor": "The shape is absent; the trigger appears in a different construction."},
         {"code": 1, "id": "partial", "anchor": "One required element of the criterion's definition is missing."},
         {"code": 2, "id": "ambiguous_match", "anchor": "The full shape is present, but a competing reading of the sentence survives the quoted text."},
         {"code": 3, "id": "unambiguous_match", "anchor": "The full shape is present and no competing reading survives the quoted text."}]},
    {"id": "harm", "question": "What does a reader lose if this ships?", "mandatory": True, "maskable": True, "order": 2,
     "levels": [
         {"code": 0, "id": "none", "anchor": "A reader acts identically with the span present or deleted and believes nothing false."},
         {"code": 1, "id": "reader_effort", "anchor": "The reader re-reads, or carries a term or clause that is never used again."},
         {"code": 2, "id": "misleads_or_blocks", "anchor": "The reader takes away a wrong belief about the artefact, or cannot act because the value, actor, or mechanism is missing."},
         {"code": 3, "id": "unsafe_or_normative", "anchor": "The reader takes an unsafe or destructive action, or a normative requirement is unreadable (wrong risk word, unclear MUST/MAY, condition stated after the command)."}]},
    {"id": "repair", "question": "Can it be removed or replaced without changing a fact?", "mandatory": True, "maskable": True, "order": 4,
     "levels": [
         {"code": 0, "id": "authorial_only", "anchor": "No rewrite preserves every protected token; only authorial rewriting would fix it."},
         {"code": 1, "id": "needs_absent_fact", "anchor": "A rewrite exists but needs a fact absent from the unit and its permitted sources (the number the writer has)."},
         {"code": 2, "id": "local_substitution", "anchor": "A substitution inside the span leaves every protected token unchanged."},
         {"code": 3, "id": "safe_deletion", "anchor": "Deleting the span or one of its clauses leaves every fact stated elsewhere in the document."}]},
    {"id": "warrant", "question": "What in the text makes this decidable rather than taste?", "mandatory": True, "maskable": False, "order": 3,
     "levels": [
         {"code": 0, "id": "none", "anchor": "No exact quote from a permitted evidence source supports the finding."},
         {"code": 1, "id": "quote_only", "anchor": "An exact quote exists and the quoted span alone exhibits the named shape; no further particular is cited."},
         {"code": 2, "id": "quote_plus_particular", "anchor": "A quote plus one named checkable particular, present or absent: a number, identifier, actor, path, command, date, or defined term."},
         {"code": 3, "id": "two_locators", "anchor": "A quote plus a second located quote or repository-checkable referent that settles it: the antecedent sentence for a repeat, the invariant contradicted, the term's other spelling."}]},
]

RULES = {
    "ai-tells-content-shape": {"weight": 1.5, "recommended_for": ["consumer", "internal", "change-comms"], "ceiling": "warning",
        "protects": ["normative_obligation", "quoted_specimen"],
        "local": ["epigram-closer-remainder", "over-writing-remainder", "textbook-connector-runs", "unasked-for-rationale"],
        "probe": ["elegant-variation", "fabricated-citations-remainder", "one-point-dilution", "padded-symmetry", "vaporware-description"],
        "arity2": {"fabricated-citations-remainder": ["defect", "referent"]}},
    "ai-tells-formatting": {"weight": 1.0, "recommended_for": ["consumer", "internal", "change-comms"], "ceiling": "suggestion",
        "protects": ["quoted_specimen"], "local": [], "probe": ["table-wrapping-one-sentence"], "arity2": {}},
    "ai-tells-register": {"weight": 1.5, "recommended_for": ["consumer", "internal", "change-comms"], "ceiling": "suggestion",
        "protects": ["controlled_language_clarity", "normative_obligation", "source_locked_legal_text"],
        "local": ["anthropomorphised-justification-remainder", "corporate-analytic-filler-remainder", "false-agency-remainder", "faux-candor-remainder", "figurative-verb-verdict-remainder", "hedged-symmetry", "intensifier-tics-remainder", "organic-consequence-remainder", "urgency-inflation-remainder"],
        "probe": ["over-formatting-reflex"], "arity2": {}},
    "ai-tells-structure": {"weight": 1.5, "recommended_for": ["consumer", "internal", "change-comms"], "ceiling": "suggestion",
        "protects": ["accessibility_consistency", "factual_polarity_or_contrast", "normative_obligation", "quoted_specimen"],
        "local": ["absolute-assertion-remainder", "analogy-stack-authority", "anaphora-abuse", "cataphoric-lead-in-remainder", "contrastive-inversion-remainder", "false-range", "false-suspense-remainder", "heading-echo", "hollow-acknowledgment", "meta-narration-remainder", "negative-inventory-remainder", "staccato-negative-parallel-remainder", "think-of-it-as-remainder", "vague-attribution-remainder"],
        "probe": ["audience-straddle-remainder", "invented-concept-label", "listicle-in-a-trench-coat", "summary-closer-remainder", "tricolon-abuse-remainder"],
        "arity2": {"anaphora-abuse": ["defect", "antecedent"], "contrastive-inversion-remainder": ["defect", "contrast"], "heading-echo": ["defect", "antecedent"], "summary-closer-remainder": ["defect", "antecedent"], "vague-attribution-remainder": ["defect", "referent"]}},
    "orwell": {"weight": 1.5, "recommended_for": ["consumer", "internal", "informal"], "ceiling": "warning",
        "protects": ["authoritative_domain_term", "normative_obligation"], "local": [], "probe": ["concrete-floor"], "arity2": {}},
    "prose-scope": {"weight": 1.0, "recommended_for": ["consumer", "change-comms"], "ceiling": "error",
        "protects": [], "local": [], "probe": ["code-change-prose-scope"], "arity2": {"code-change-prose-scope": ["defect", "referent"]}},
    "prose-discipline": {"weight": 1.5, "recommended_for": ["consumer", "reference", "internal"], "ceiling": "warning",
        "protects": ["authoritative_domain_term", "normative_obligation", "quoted_specimen"],
        "local": ["marketing-register", "overloaded-sentence"],
        "probe": ["bare-quantifier-with-figure-available", "competing-actor-terms", "hedged-into-uselessness"],
        "arity2": {"competing-actor-terms": ["defect", "contrast"]}},
    "ste-descriptive": {"weight": 1.0, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["accessibility_consistency", "controlled_language_clarity"],
        "local": ["information-not-gradual", "missing-key-word-structure", "paragraph-has-multiple-topics", "paragraph-without-related-information"], "probe": [], "arity2": {}},
    "ste-nouns": {"weight": 1.0, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["authoritative_domain_term"], "local": [], "probe": ["long-domain-term-without-short-form"],
        "arity2": {}},
    "ste-practices": {"weight": 0.8, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["authoritative_domain_term"], "local": ["ambiguous-preposition-with", "word-sense-incorrect", "word-swap-insufficient"], "probe": [], "arity2": {}},
    "ste-punctuation": {"weight": 1.0, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["source_locked_legal_text"], "local": ["parentheses-misuse"], "probe": [], "arity2": {}},
    "ste-safety": {"weight": 1.5, "recommended_for": ["reference"], "ceiling": "error",
        "protects": ["normative_obligation", "source_locked_legal_text"], "local": ["risk-level-word-missing-or-wrong"], "probe": [],
        "arity2": {}},
    "ste-sentences": {"weight": 1.0, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["controlled_language_clarity"], "local": ["missing-connector-between-related-sentences", "sentence-not-short-or-clear"], "probe": [],
        "arity2": {"missing-connector-between-related-sentences": ["defect", "antecedent"]}},
    "ste-verbs": {"weight": 1.0, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["normative_obligation"], "local": ["gerund-outside-noun-use", "past-participle-not-adjectival"], "probe": [], "arity2": {}},
    "ste-words": {"weight": 1.0, "recommended_for": ["reference"], "ceiling": "suggestion",
        "protects": ["authoritative_domain_term", "controlled_language_clarity"],
        "local": ["domain-noun-category-membership", "domain-noun-too-long-or-unclear", "domain-verb-category-membership", "unapproved-word-not-a-domain-noun", "word-used-outside-permitted-sense"],
        "probe": ["domain-noun-not-organization-approved"],
        "arity2": {"domain-noun-not-organization-approved": ["defect", "referent"]}},
}

RULE_EXTRA = {
    "ste-safety.risk-level-word-missing-or-wrong": {
        "adjudicates": "normative_obligation",
        "allowed_transitions": {"status": "provisional", "table": [{"class": "modality", "from": "CAUTION", "to": "WARNING"}, {"class": "modality", "from": "WARNING", "to": "CAUTION"}],
                                "requires": "the consequence that fixes the level is quoted as role=invariant from the unit or context",
                                "note": "only the CAUTION<->WARNING pair is evidenced by the rule's own examples (ste-safety.yml:10-43); DANGER and NOTE transitions were marked unsupported by ChContract and are admitted only after a safety authority or calibration supplies them"},
    },
    "ai-tells-structure.heading-echo": {
        "host_predicates": [{"id": "heading_echo_material_redundancy", "definition": "the host reads the antecedent heading and the defect sentence from the evidence and admits the finding only when the sentence is one line with a finite verb or terminal punctuation, shares a normalised content word with the heading, and adds no material token or span (figure, code, path, flag, file, link, normative word) or novel content lemma beyond stopwords; a failing clause converts the outcome to REJECT, and a missing or blank heading is ABSTAIN(heading_echo_no_antecedent)"}],
    },
    "ste-nouns.long-domain-term-without-short-form": {
        "host_predicates": [{"id": "no_short_form_in_document", "definition": "the model names the expected short form as a particular; the host verifies by exact search that it occurs nowhere in the document; a hit converts the outcome to REJECT"}],
    },
    "prose-discipline.bare-quantifier-with-figure-available": {
        "host_predicates": [{"id": "figure_available", "definition": "the figure must be quoted as role=referent from the unit, context, or a repository source; without it the outcome is ABSTAIN(needs_repository_fact), never CONFIRM"}],
    },
    "prose-scope.code-change-prose-scope": {
        "added_in": "1.1.1: the rule entered origin/main after source_commit; its record is inferred from its YAML, not from the review",
        "status": "provisional",
        "host_predicates": [{"id": "code_diff_available", "definition": "the changed hunk is supplied as role=referent repository evidence (path@blob_sha); without it the outcome is ABSTAIN(needs_repository_fact), never CONFIRM"}],
    },
    "orwell.concrete-floor": {
        "scope_class_derivation": "orwell.yml declares no scope; treated as document scope (design §0 counted it as the one prose-scope rule); add scope: document to the YAML before activation",
    },
}

SPAN_CRITERIA_MAX = 4
SPAN_UNITS_MAX = 5
PROBE_CRITERIA_MAX = 4
PROBE_OCCURRENCES_MAX = 12

PROBE_PACKS = [
    {"id": "PROBE-1", "rules": ["ai-tells-structure.invented-concept-label", "ai-tells-structure.listicle-in-a-trench-coat", "ai-tells-structure.summary-closer-remainder", "ai-tells-structure.tricolon-abuse-remainder"]},
    {"id": "PROBE-2", "rules": ["ai-tells-content-shape.fabricated-citations-remainder", "ai-tells-content-shape.one-point-dilution", "ai-tells-content-shape.padded-symmetry", "ai-tells-content-shape.vaporware-description"]},
    {"id": "PROBE-3", "rules": ["ai-tells-content-shape.elegant-variation", "prose-discipline.bare-quantifier-with-figure-available", "prose-discipline.competing-actor-terms", "prose-discipline.hedged-into-uselessness"]},
    {"id": "PROBE-4", "rules": ["ai-tells-formatting.table-wrapping-one-sentence", "ai-tells-register.over-formatting-reflex", "ai-tells-structure.audience-straddle-remainder", "ste-nouns.long-domain-term-without-short-form"]},
    {"id": "PROBE-5", "rules": ["orwell.concrete-floor", "prose-scope.code-change-prose-scope", "ste-words.domain-noun-not-organization-approved"]},
]


def rule_records():
    records = []
    for cat in sorted(RULES):
        spec = RULES[cat]
        for scope_class, ids in (("local", spec["local"]), ("probe", spec["probe"])):
            for rid in ids:
                roles = spec["arity2"].get(rid)
                extra = RULE_EXTRA.get(f"{cat}.{rid}", {})
                records.append({
                    **extra,
                    "category": cat,
                    "dims": {"fit": "ask", "harm": "ask", "repair": "ask", "warrant": "ask"},
                    "evidence": {"min_arity": 2 if roles else 1, "roles": roles or ["defect"]},
                    "id": f"{cat}.{rid}",
                    "judgement_ceiling": spec["ceiling"],
                    "protects": spec["protects"],
                    "scope_class": scope_class,
                    "warrant_min": 2,
                })
    return sorted(records, key=lambda r: r["id"])


def probe_packs():
    packs = []
    for i, p in enumerate(PROBE_PACKS, 1):
        cats = sorted({r.split(".")[0] for r in p["rules"]})
        packs.append({"categories": cats, "chunk": i, "id": p["id"], "protects": sorted({c for cat in cats for c in RULES[cat]["protects"]}),
                      "rules": sorted(p["rules"]), "scope_class": "probe"})
    return sorted(packs, key=lambda p: p["id"])


def span_packs():
    packs = []
    for cat in sorted(RULES):
        local = sorted(RULES[cat]["local"])
        for i in range(0, len(local), SPAN_CRITERIA_MAX):
            chunk = local[i:i + SPAN_CRITERIA_MAX]
            packs.append({"categories": [cat], "chunk": i // SPAN_CRITERIA_MAX + 1, "id": f"SPAN-{cat}-{i // SPAN_CRITERIA_MAX + 1}", "protects": sorted(RULES[cat]["protects"]),
                          "rules": [f"{cat}.{r}" for r in chunk], "scope_class": "local", "units_max": SPAN_UNITS_MAX})
    return sorted(packs, key=lambda p: p["id"])


def category_packs():
    packs = []
    for cat in sorted(RULES):
        s = RULES[cat]
        packs.append({
            "id": cat,
            "judgement_ceiling": s["ceiling"],
            "local_rules": len(s["local"]),
            "probe_rules": len(s["probe"]),
            "protects": sorted(s["protects"]),
            "recommended_for": s["recommended_for"],
            "weight_yaml": s["weight"],
            "weight_use": "initial prior only; effective weight is profile-resolved and must be recalibrated before activation",
        })
    return packs


def model_output_schema():
    level_ids = {d["id"]: [lvl["id"] for lvl in d["levels"]] for d in DIMENSIONS}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "additionalProperties": False,
        "properties": {
            "abstain_reason": {"enum": [a["id"] for a in ABSTENTION if a["id"] != "inconsistent_output"] + [None]},
            "admissible": {"type": "boolean"},
            "evidence": {"type": ["array", "null"], "items": {
                "additionalProperties": False,
                "properties": {
                    "end": {"type": "integer", "minimum": 0},
                    "quote": {"type": "string", "minLength": 1},
                    "role": {"enum": ["antecedent", "contrast", "defect", "invariant", "referent"]},
                    "source": {"enum": ["context", "repository", "unit"]},
                    "source_ref": {"type": ["string", "null"], "description": "unit_id for unit/context; path@blob_sha for repository"},
                    "start": {"type": "integer", "minimum": 0}},
                "required": ["end", "quote", "role", "source", "start"], "type": "object"}},
            "note": {"type": "string", "maxLength": 160, "description": "<=20 words; no rubric vocabulary"},
            "occurrences": {"type": ["array", "null"], "maxItems": PROBE_OCCURRENCES_MAX, "items": {"$ref": "#/$defs/occurrence"}, "description": "PASSAGE_PROBE only: one entry per located occurrence; the top-level scores/evidence/rewrite are null and the top-level verdict is `confirm` if any occurrence confirms, else the most severe of preserve/abstain/reject among occurrences"},
            "occurrences_truncated": {"type": "boolean", "description": "true when the model located more occurrences than maxItems; the host records the remainder as not_run for coverage, never as an abstention of the located ones"},
            "preservation_reason": {"enum": [p["id"] for p in PRESERVATION] + [None]},
            "rewrite": {"type": ["string", "null"]},
            "rewrite_status": {"enum": ["not_applicable", "proposed", "withheld_needs_fact"]},
            "rule_id": {"type": "string"},
            "scores": {"anyOf": [{"$ref": "#/$defs/scores"}, {"type": "null"}]},
            "unit_id": {"type": "string"},
            "kind": {"enum": ["PASSAGE_PROBE", "SPAN_CANDIDATE"]},
            "verdict": {"enum": ["abstain", "confirm", "preserve", "reject"]},
        },
        "required": ["abstain_reason", "admissible", "evidence", "kind", "note", "occurrences", "occurrences_truncated", "preservation_reason", "rewrite", "rewrite_status", "rule_id", "scores", "unit_id", "verdict"],
        "type": "object",
        "if": {"properties": {"kind": {"const": "PASSAGE_PROBE"}}},
        "then": {"properties": {"evidence": {"type": "null"}, "occurrences": {"type": "array"}, "rewrite": {"type": "null"}, "rewrite_status": {"const": "not_applicable"}, "scores": {"type": "null"}}},
        "else": {"properties": {"evidence": {"type": "array"}, "occurrences": {"type": "null"}, "occurrences_truncated": {"const": False}, "scores": {"$ref": "#/$defs/scores"}}},
        "$defs": {"scores": {"type": "object", "additionalProperties": False, "properties": {
                "fit": {"enum": level_ids["fit"]}, "harm": {"enum": level_ids["harm"] + ["inapplicable"]},
                "repair": {"enum": level_ids["repair"] + ["inapplicable"]}, "warrant": {"enum": level_ids["warrant"]}},
                "required": ["fit", "harm", "repair", "warrant"]},
            "occurrence": {"additionalProperties": False, "type": "object",
            "properties": {"abstain_reason": {"enum": [a["id"] for a in ABSTENTION if a["id"] != "inconsistent_output"] + [None]}, "evidence": {"type": "array", "items": {"$ref": "#/properties/evidence/items"}}, "preservation_reason": {"enum": [p["id"] for p in PRESERVATION] + [None]},
                           "rewrite": {"type": ["string", "null"]}, "rewrite_status": {"enum": ["not_applicable", "proposed", "withheld_needs_fact"]}, "scores": {"$ref": "#/$defs/scores"}, "verdict": {"enum": ["abstain", "confirm", "preserve", "reject"]}},
            "required": ["abstain_reason", "evidence", "preservation_reason", "rewrite", "rewrite_status", "scores", "verdict"]}},
        "x-host_finding_record": "The host wraps every model output in a finding record adding: outcome (decision_outcome_enum), severity, core_fired, component_id, rewrite_status extended with withheld_checker_veto, source_sha256, document-coordinate spans, instrument_id, judgement_cache_key. The model never emits any of these.",
        "x-reconciliation": "The host recomputes the outcome from scores, evidence, gates, and rule record. The model's verdict is advisory: when it disagrees with the host outcome the finding is ABSTAIN(inconsistent_output) and counted in coverage; the model's verdict never overrides the algorithm.",
        "x-serialization": "Level ids are the wire format. Codes 0-3 are ordinal serialization aliases for storage only and MUST NOT be summed or averaged.",
        "x-conditionals": [
            "verdict=preserve requires preservation_reason != null and rewrite=null",
            "verdict=abstain requires abstain_reason != null",
            "verdict=confirm requires rewrite_status in {proposed, withheld_needs_fact, not_applicable}; rewrite != null iff rewrite_status=proposed; not_applicable only when the rule masks repair=inapplicable",
            "verdict=confirm requires scores.fit=unambiguous_match or ambiguous_match and scores.warrant != none; otherwise the host assigns inconsistent_output",
            "kind=PASSAGE_PROBE: occurrences is the verdict carrier; top-level evidence/scores/rewrite are null and rewrite_status=not_applicable (enforced by if/then). kind=SPAN_CANDIDATE: occurrences=null (enforced by else)",
            "evidence with role=defect requires source=unit; antecedent/contrast/invariant/referent may use context or repository",
            "repository evidence requires source_ref of the form path@blob_sha and offsets into that blob's UTF-8 text",
        ],
    }


contract = {
    "aggregation": {
        "cluster_gate": {
            "rule": "REVISE when any confirmed finding has harm=unsafe_or_normative. Otherwise merge confirmed findings whose primary spans overlap, or whose rule pair is listed in the dependence table, into one component keeping the maximum severity; REVISE only when one passage holds >= 3 components with pairwise non-overlapping primary spans.",
            "definitions": {"passage": "one paragraph unit: a blank-line-delimited block in document code-point coordinates", "primary_span": "the finding's role=defect evidence projected to document coordinates via the unit's range; a PASSAGE_PROBE occurrence uses its own defect span", "component": "the transitive closure of overlap or dependence-table adjacency among confirmed findings in one passage", "dependence_table": "a frozen versioned artefact {dependence_table_sha, pairs: [[rule_a, rule_b]]} derived from a held-out labelled set that is never used to evaluate the gate"},
            "categories_role": "reported, never used to establish independence",
            "dependence_table": "built from labelled judgement output; mechanical co-occurrence may nominate pairs (e.g. prose-craft.unclear-antecedent x ste-practices.unclear-demonstrative-this, phi 0.985) but may not calibrate the gate",
            "evidence": "session_model_prose corpus: within-category phi mean 0.0263 vs across 0.0267; new '>=2 categories' gate retained 1821 of 1899 old-gate units (96%)",
        },
        "coverage": {
            "counts": ["eligible", "attempted", "confirmed", "rejected", "preserved", "abstained", "failed", "truncated", "not_run"],
            "per": ["document", "pack", "rule"],
            "rule": "coverage = completed/eligible per pack and rule; a document with any failed, truncated, or not-run eligible unit is PARTIAL, never CLEAN; abstention is a completed adjudication reported separately with reason counts",
        },
        "judgement_score": {
            "gating": "Judgement findings never enter min_score, max_warnings, density budgets, or the min_score guard (score.py:267-272). A judgement confirm counts toward max_errors only when its rule's judgement_ceiling is error (today: ste-safety.risk-level-word-missing-or-wrong and prose-scope.code-change-prose-scope). The only other gating path is the cluster gate.",
            "reporting": "judgement_adjusted_score = deterministic_score - min(judgement_penalty, judgement_max_penalty) is reported beside the deterministic score and does not decide pass/fail.",
            "judgement_max_penalty": {"value": 15, "status": "provisional", "derivation": "narrowest passing band: strict min_score 85 leaves 15 points on a clean document; any larger cap gates alone at strict (100-20=80<85). Profile-relative bound if a single composite ever gates: J_max = max(0, 100 - min_score - suggestion_penalty), i.e. strict 0, normal 15. No published precedent for a stochastic-component cap exists; report capped and uncapped values until Q09 is answered."},
            "severity_weight": "reuse SEVERITY_WEIGHT error 1.0 / warning 0.5 / suggestion 0.1 for the reporting score; publish effective weights",
        },
        "preserves": {
            "rule": "preserve_rate = preserved/attempted per rule and reason. Preserves MUST NOT demote a rule and MUST NOT be pooled with false-positive reports.",
            "review_trigger": {"status": "disabled_experimental", "note": "the design's 'three preserves' has no derivation (docs/triage.md:81-84 is undated policy); a trigger is set only from exposure-normalised preserve rates after Q09"},
        },
        "weights": {"rule": "the resolved profile weight of the finding's own category is an initial prior; recalibrate per profile before activation; never infer a judgement weight from a related mechanical category"},
    },
    "category_packs": category_packs(),
    "claim_verdicts": {
        "C1": "AMEND", "C10": "REPLACE", "C11": "REPLACE", "C12": "REPLACE", "C13": "AMEND", "C14": "AMEND",
        "C2": "AMEND", "C3": "AMEND", "C4": "REPLACE", "C5": "REPLACE", "C6": "REPLACE", "C7": "REPLACE", "C8": "REPLACE", "C9": "REPLACE",
    },
    "composition": {
        "caching": "Count a cache hit only when provider telemetry reports a read for the exact prefix. The <=900-token spine is below the 1024-token minimum of OpenAI and common Anthropic/Bedrock models and is not assumed cacheable. Pack prefixes amortise across documents within provider TTL (Anthropic/Bedrock default 5 min), not across different packs on one document. Report cold-write, cache-read, and uncached tokens separately.",
        "document_length": "Whole-document PROBE dispatch is permitted only inside the model's validated length bin; above it, occurrence rules run on overlapping chunks and document-global rules are reported not_run.",
        "probe_criteria_max": PROBE_CRITERIA_MAX,
        "probe_packs": probe_packs(),
        "probe_occurrences_max": {"value": 12, "status": "provisional", "note": "schema maxItems; validated by Q14 before activation; the remainder is reported not_run"},
        "span_criteria_max": SPAN_CRITERIA_MAX,
        "span_packs": span_packs(),
        "span_units_max": SPAN_UNITS_MAX,
        "status": "provisional safety limits below the earliest adverse counts in the closest evidence (ManyIFEval judge inflation +24.1 points at 5 constraints; BatchPrompt degradation at batch size 6); raise only by a versioned repository evaluation showing non-inferior per-rule recall",
    },
    "decision_algorithm": [
        "gates run in order A5, A1, A2, A4, A3; if any admission gate fails: DROP the judgement remainder (audit only). A5 never suppresses the mechanical core finding, whose own exclusions live in slopvac.toml",
        "if preservation_reason: PRESERVE (recorded, never a finding)",
        "if abstain_reason: ABSTAIN (counts against coverage)",
        "if fit in {absent, partial} and model verdict == reject: REJECT (nothing to quote for an absent shape; no evidence required; 1.1.2)",
        "if not evidence_ok: ABSTAIN(no_exact_evidence) (evidence_ok = exact slice match in the named source, in-range offsets, rule min_arity and roles satisfied, role=defect evidence unit-local; required for every candidate confirm or preserve)",
        "if fit in {absent, partial}: REJECT",
        "if warrant_code < rule.warrant_min: REJECT",
        "if harm == none and repair != safe_deletion: REJECT (skipped when the rule masks harm=inapplicable; a masked harm caps severity at suggestion)",
        "if repair == inapplicable (rule mask): rewrite_status must be not_applicable and the checker does not run",
        "for each host_predicate on the rule: evaluate; a failed predicate converts CONFIRM to the outcome the predicate names",
        "severity = error if harm == unsafe_or_normative and fit == unambiguous_match; else warning if harm == misleads_or_blocks and fit == unambiguous_match; else suggestion",
        "severity = min(severity, rule.judgement_ceiling, category_ceiling)",
        "if rewrite_status == proposed and not fact_preserving(rewrite, unit): rewrite_status = withheld_checker_veto; rewrite = null; severity = demote(severity)",
        "if rewrite_status == withheld_needs_fact: no demotion (honest missing-fact finding; repair == needs_absent_fact)",
        "return CONFIRM(severity)",
    ],
    "dimensions": sorted(DIMENSIONS, key=lambda d: d["id"]),
    "dimension_policy": {
        "independence": "The four checks are separately reported and non-interchangeable; independence is an empirical question, not a premise (ASAP++ trait correlations >= .60; TOEFL aspects .84-.96, one factor 90.6% of variance).",
        "masks": "dims values are ask | inapplicable. A rule may mark HARM or REPAIR inapplicable when the check has no meaning for it; a rule MUST NOT inject a constant score. Category-level HARM/REPAIR constants from design §8 are withdrawn (MQM assigns severity per error instance; category weight is a separate multiplier).",
        "scale": "Four named ordinal levels per dimension; codes are serialization only. Adjective anchors are prohibited.",
        "score_order": "The model emits evidence before scores and scores before verdict; the model never emits a severity.",
    },
    "evidence_requirements": {
        "arity": "rule-declared {min_arity, roles}; relational defects (repeat, contrast, term/tense inconsistency) require >= 2 with named roles; chains MAY exceed 2",
        "exactness": "every quote equals the identified source-text slice exactly (Unicode code-point offsets into the named source text); the caller validates against the raw source through a deterministic projection map and stamps source_sha256; a mismatch is ABSTAIN(no_exact_evidence), never editorial",
        "projection_map": {"format": "ordered segments [{proj_start, proj_end, raw_start, raw_end}] in code points (proj) and bytes (raw); a synthetic insertion (joined line, decoded entity, masked code span) is a segment with raw_start == raw_end; unit and context each carry their own range and map", "status": "implementation blocker: analyze.py:582-606,817-845 keeps line starts only; the map must be added before exact evidence or cluster overlap can be computed"},
        "roles": ["antecedent", "contrast", "defect", "invariant", "referent"],
        "sources": {"context": "surrounding blocks; MAY carry antecedent/contrast/invariant/referent evidence; never role=defect", "repository": "path@blob_sha with offsets and exact quote; needed for glossary/schema referents", "unit": "the unit text; the only permitted source for role=defect"},
        "warrant_min": "calibration-gated configuration, default 2 (quote plus a named particular). Universal 2 is unsupported (ChGates); the sentence-scope lexical rules (ai-tells-register intensifier-tics, ai-tells-structure false-range and absolute-assertion) are the candidates for 1 once Q01 measures precision at 1 vs 2. Every rule record carries the default until then.",
    },
    "gates": {
        "admission": [
            {"id": "A1", "rule": "scope legality: a document-scope criterion is not answerable over a paragraph unit"},
            {"id": "A2", "rule": "text availability: the unit text is non-empty and the source projection map resolves it"},
            {"id": "A3", "rule": "core adjudication (replaces double jeopardy): when a rule's mechanical core fired on an admissible unit, set core_fired=true and run the judgement remainder once; PRESERVE or REJECT suppresses the core finding; CONFIRM emits one deduplicated finding. Runs last; when A5 excludes the unit the core finding stands as the deterministic layer reported it"},
            {"id": "A4", "rule": "genre and tier: resolved deterministically upstream from recommended_for and tiers; the model never decides applicability"},
            {"id": "A5", "rule": "origin: units carry origin (authored | generated | vendored | template) and region_class (prose | quoted | code | example) from deterministic file and Markdown structure; generated, vendored, and template units are inadmissible unless the rule opts in; admissible units with region_class quoted or example enter with preservation_reason=quoted_specimen preset. Runs first"},
        ],
        "abstention": {"closed_list": True, "reasons": ABSTENTION, "reporting": "abstentions count against coverage among admissible non-preserved units; report reason-specific rates, selective risk on accepted verdicts, and invalid-abstention rate on gold answerable cases"},
        "order": ["admission (A5, A1, A2, A4, A3)", "preservation", "abstention", "scoring"],
        "preservation": {"closed_list": True, "classes": PRESERVATION, "setting": "deterministic where a signal exists (origin, file class, markers, vocabulary); otherwise model-returned and always recorded", "pack_scope": "a pack lists only the classes its rules collide with (protects); quoted_specimen is preset by origin and need not be listed"},
        "uncertainty": "Uncertainty is never a dimension. A calibrated confidence signal MAY select abstention; it MUST NOT be emitted as a score or treated as evidence; any selector is evaluated with risk-coverage curves and calibration error, never by self-report.",
    },
    "model_output_schema": model_output_schema(),
    "protected_classes": [p["id"] for p in PRESERVATION],
    "protected_token_classes": TOKEN_CLASSES,
    "research_date": "2026-09-15",
    "rewrite_requirements": {
        "additions": "authorised only by (a) the source occurrence under a declared typed normalisation (spelled-number<->digit, date format, unit, case, punctuation), (b) a cited glossary/schema/repository referent supplied as evidence, or (c) an exact rule-declared allowed_transition. Presence elsewhere in the document is not authorisation. Numerals are never introduced without (a) or (b).",
        "checker": "compare typed, located protected tokens between unit and rewrite; require semantic equivalence and referent/location preservation per occurrence",
        "deletion": "deleting a clause quoted as role=defect is permitted only when that clause holds no protected token outside the rule's allowed transitions",
        "exemptions": "rule-relative and exact: the rule record's allowed_transitions table [{class, from, to}] is the only authority and replaces class-wide rewrite_exempt; the checker admits a protected-token change iff the exact (class, from, to) row exists on the rule that produced the finding. Today one rule carries a table: ste-safety.risk-level-word-missing-or-wrong (CAUTION<->WARNING, provisional).",
        "removal_or_alteration": "forbidden; a rewrite that drops or alters a protected token is rejected mechanically: the finding survives, rewrite_status=withheld_checker_veto, severity demoted one level",
        "status_enum": ["not_applicable", "proposed", "withheld_checker_veto", "withheld_needs_fact"],
    },
    "schema_version": "1.1.2",
    "scope": {"in": "prose-quality defect judgement layered over the deterministic slopvac ruleset", "out": ["AI-authorship or provenance detection", "a fifth dimension", "model confidence as a score"]},
    "source_commit": SOURCE_COMMIT,
    "target_base_commit": "12042c9e7d1758f9f02c37884ccf98d38b8e2493",
    "target_base_note": "origin/main at implementation start; carries 66 kind: judgement rules (65 reviewed + prose-scope.code-change-prose-scope, whose record is inferred). Measurements and the review refer to source_commit.",
    "revision_history": [{"version": "1.1.0", "change": "first accepted synthesis after the contract challenge"}, {"version": "1.1.1", "change": "66th provisional rule record; target_base_commit"}, {"version": "1.1.2", "change": "decision order: a model reject with fit absent or partial needs no evidence; the README live run had turned 570 honest rejects into abstentions"}],
    "unit_schema": {
        "fields": {"category": "owning category; dimensions key on the rule record, never on the category", "context": "surrounding blocks with their own range and projection map; quotable only for non-defect roles", "kind": "SPAN_CANDIDATE | PASSAGE_PROBE", "origin": "authored | generated | vendored | template", "path": "repository-relative path", "projection_map": "see evidence_requirements.projection_map", "range": "code-point offsets into the projected prose text plus document code-point offsets; the projection map resolves raw bytes", "region_class": "prose | quoted | code | example", "register_target": "consumer | reference | change-comms | internal | informal | formal_legal", "rule_id": "always set (PASSAGE_PROBE carries the probe pack's rule list)", "source_sha256": "sha256 of the raw source file", "text": "the unit's exact projected text", "unit_id": "sha256(kind, rule_id, path, source_sha256, start, end)[:16]"},
    },
    "unresolved_evaluation_questions": [
        {"id": "Q01", "question": "Per-rule precision and coverage at warrant_min 1 vs 2, separately for local and relational rules, on an adjudicated stratified sample."},
        {"id": "Q02", "question": "Fraction of raw model quotes failing exact-slice validation under verdict-first, evidence-first, and constrained copy; accepted-span fabrication is 0 only after mechanical validation."},
        {"id": "Q03", "question": "Double-rated weighted kappa per dimension, polychoric correlations, and effective rank of FIT/HARM/WARRANT/REPAIR; whether FIT and WARRANT collapse."},
        {"id": "Q04", "question": "Within-rule variance of HARM and REPAIR when asked, versus the withdrawn §8 constants; cost delta of asking four checks on 65 rules."},
        {"id": "Q05", "question": "Repeated-call agreement at temperature 0 and 1 by dimension for named four-level categories vs binary checklist vs anchored 1-5."},
        {"id": "Q06", "question": "Per-rule recall, abstention, and malformed-output rates at 1/2/4/5/8/18 criteria per call and 1/3/5/6/12 units per call, with randomised order and position-resolved recall."},
        {"id": "Q07", "question": "Five PROBE packs vs one 18-rule pack: paired non-inferiority on recall, priced false negatives, and measured cache-read tokens per provider."},
        {"id": "Q08", "question": "Cluster-gate precision/recall on labelled judgement output for raw count, distinct-category, span-component, and phenomenon-component variants; which rule pairs stay dependent after deduplication."},
        {"id": "Q09", "question": "Whether any judgement deduction improves score validity without changing pass/fail; preserve and false-positive rates per rule by preservation reason and document type."},
        {"id": "Q10", "question": "False-veto and unsafe-pass rates of the typed checker vs exact token identity; how often document-membership would have authorised a wrong-location MUST, identifier, term, or number."},
        {"id": "Q11", "question": "Reviewer agreement on source_locked_legal_text vs ordinary legal prose and on accessibility/controlled-language consistency vs mere repetition."},
        {"id": "Q12", "question": "Verdict flip rates under punctuation, whitespace, label, anchor-paraphrase, and shot-order mutations of the spine, per evaluator model; mutation test of the cache key."},
        {"id": "Q13", "question": "Judgement-layer co-occurrence on human and model prose (the measured proxy is mechanical findings on model prose only)."},
        {"id": "Q14", "question": "Occurrence-cap recall for 25 KB, 100 KB, and 250 KB PASSAGE_PROBE documents and how truncation is reported."},
    ],
    "verdict_enum": ["abstain", "confirm", "preserve", "reject"],
    "implementation_gate": {
        "status": "not implementation-ready until every blocker below is closed",
        "blockers": [
            {"id": "B1", "item": "projection map format persisted for unit and context (evidence_requirements.projection_map)"},
            {"id": "B2", "item": "host finding record type with outcome, severity, core_fired, component_id, extended rewrite_status (model_output_schema.x-host_finding_record)"},
            {"id": "B3", "item": "dependence table artefact with sha, derived from a held-out labelled set (aggregation.cluster_gate.definitions)"},
            {"id": "B4", "item": "pack renderer producing the JCS pack_object and rubric_revision bytes (versioning)"},
            {"id": "B5", "item": "YAML schema additions per rule: dims, evidence, warrant_min, protects, judgement_ceiling, adjudicates, allowed_transitions, host_predicates; scope for orwell.concrete-floor"},
            {"id": "B6", "item": "typed fact-preservation checker with per-class semantic equivalence (rewrite_requirements.checker)"},
            {"id": "B7", "item": "origin and region_class classifier from file class and Markdown structure (gates.admission A5)"},
        ],
    },
    "decision_outcome_enum": ["ABSTAIN", "CONFIRM", "DROP", "PRESERVE", "REJECT"],
    "versioning": {
        "comparability": "A comparison declares its independent variable; all other fields of instrument_id, unit content hashes, evaluator/scorer configuration, runner revision, and repeat protocol must match. Cross-release results are separate instruments, never one series.",
        "instrument_id": "sha256(rubric_revision, ordered pack_ids)",
        "judgement_cache_key": "sha256(instrument_id, unit_id + context hash, provider, model_id_and_revision, full_rendered_request_digest, system_prompt, decoding_config, seed, repeat_index, evaluator_runner_revision); any changed field is a miss",
        "pack_id": "sha256(JCS(pack_object)) where JCS is RFC 8785 canonical JSON over UTF-8 and pack_object = {categories, chunk, scope_class, protects, rules: [for each rule id in order: this contract's rule record merged with the YAML rule as loaded at source_commit (judgement_question, message, fix, examples, tiers, exceptions, scope, severity)], template_revision, shots: [ordered full shot messages with labels and delimiters]}; excludes rubric_api_version",
        "canonicalisation": "RFC 8785 (JCS) for every hashed object; prompt text hashed as rendered UTF-8 bytes",
        "rubric_api_version": "semver for parser/schema compatibility only: MAJOR removes/changes fields or meanings; MINOR adds optional fields or enum members only where readers demonstrably ignore unknown values; PATCH changes no model-visible bytes and no scoring behaviour",
        "rubric_revision": "sha256(canonical model-visible spine bytes); changes on every model-visible wording, whitespace, ordering, anchor, gate, or schema change. There is no score-inert model-visible PATCH (formatting-only prompt changes move accuracy by up to 76 points, Sclar et al. 2023).",
        "scorer_config_sha": "sha256 of resolved thresholds, weights, caps, and the aggregation algorithm; retuning may reuse raw verdicts but MUST recompute scores/gates and starts a new aggregate series",
        "thresholds_location": "slopvac.toml and profile defaults, never model-visible text; the §9 constants (penalty cap, cluster thresholds) move there too",
    },
}

# rule_records listed separately so category_packs stays compact
contract["rule_records"] = rule_records()

# --- validation -------------------------------------------------------------
def all_ids(obj, path="root"):
    found = []
    if isinstance(obj, dict):
        if "id" in obj and isinstance(obj["id"], str):
            found.append((path, obj["id"]))
        for k, v in obj.items():
            found.extend(all_ids(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(all_ids(v, f"{path}[{i}]"))
    return found

def check_unique(items, label):
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), f"duplicate ids in {label}: {sorted(i for i in ids if ids.count(i) > 1)}"
    assert ids == sorted(ids), f"{label} not sorted by id"

check_unique(contract["dimensions"], "dimensions")
check_unique(contract["gates"]["preservation"]["classes"], "preservation classes")
check_unique(contract["gates"]["abstention"]["reasons"], "abstention reasons")
check_unique(contract["gates"]["admission"], "admission gates")
check_unique(contract["protected_token_classes"], "token classes")
check_unique(contract["category_packs"], "category packs")
check_unique(contract["rule_records"], "rule records")
check_unique(contract["composition"]["span_packs"], "span packs")
check_unique(contract["composition"]["probe_packs"], "probe packs")
check_unique(contract["unresolved_evaluation_questions"], "questions")
assert len(contract["rule_records"]) == 66, len(contract["rule_records"])
probe_rules = [r for p in contract["composition"]["probe_packs"] for r in p["rules"]]
assert sorted(probe_rules) == sorted(r["id"] for r in contract["rule_records"] if r["scope_class"] == "probe"), "probe packs != probe rules"
assert all(len(p["rules"]) <= PROBE_CRITERIA_MAX for p in contract["composition"]["probe_packs"])
span_rules = [r for p in contract["composition"]["span_packs"] for r in p["rules"]]
assert sorted(span_rules) == sorted(r["id"] for r in contract["rule_records"] if r["scope_class"] == "local"), "span packs != local rules"
for rec in contract["rule_records"]:
    assert set(rec["protects"]) <= set(contract["protected_classes"]), rec["id"]
# global id uniqueness within each list scope is checked above; whole-document ids may repeat across scopes
# (a category id appears in category_packs and in rule ids as prefix); assert no exact duplicate within any single list.
text = json.dumps(contract, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
assert "/Users/" not in text and "/tmp/" not in text, "machine-specific path leaked"
json.loads(text)
OUT.mkdir(parents=True, exist_ok=True)
tmp = OUT / "rubric-contract.json.tmp"
tmp.write_text(text, encoding="utf-8")
tmp.replace(OUT / "rubric-contract.json")
digest = hashlib.sha256((OUT / "rubric-contract.json").read_bytes()).hexdigest()
(OUT / "rubric-contract.sha256.tmp").write_text(f"{digest}  rubric-contract.json\n")
(OUT / "rubric-contract.sha256.tmp").replace(OUT / "rubric-contract.sha256")
print(digest, len(text), "bytes", len(contract["rule_records"]), "rules", len(contract["composition"]["span_packs"]), "span packs")
