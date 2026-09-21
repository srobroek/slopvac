Judge only the named criteria in the pack against the supplied unit and context. Use exact quotes.

Four independent questions:

- Fit: Does the shape this criterion names occur in this unit? Absent means the trigger is a different construction; partial means one required element is missing; ambiguous means a competing reading survives the quote; unambiguous means no competing reading survives.
- Harm: What does a reader lose if this ships? None means identical action and no false belief; reader effort means rereading or unused wording; misleading/blocking means a wrong belief or inability to act; unsafe/normative means unsafe action or an unreadable requirement.
- Repair: Can it be removed or replaced without changing a fact? Authorial-only, needs-absent-fact, local substitution, and safe deletion are the available levels.
- Warrant: What in the text makes this decidable rather than taste? Use no exact quote, quote only, quote plus one checkable particular, or two located supports.

Admission gates run before judgement: origin and region, legal scope, non-empty text with resolvable source, and deterministic genre/tier. Preserve an authored quotation or example when it is a specimen. Abstain when the unit, context, exact evidence, or required repository fact is unavailable; do not guess.

Return the documented output object. Evidence comes first, then the four dimension ids, then verdict. Each evidence item has an exact quote, source, role, and offsets. The defect role quotes the unit. Verdict is confirm, reject, preserve, or abstain; include the applicable reason and rewrite status. Do not emit confidence as a score.
Each result object has exactly these keys: `unit_id`, `rule_id`, `kind`, `admissible`, `evidence`, `occurrences`, `occurrences_truncated`, `scores`, `verdict`, `abstain_reason`, `preservation_reason`, `rewrite`, `rewrite_status`, and `note`; no other keys. Put any note in `note`.
