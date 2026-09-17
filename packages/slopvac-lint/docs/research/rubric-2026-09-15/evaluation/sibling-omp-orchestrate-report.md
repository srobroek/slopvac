# Judgement comparison

evidence_offset_mismatch: 5

## skills/orchestrate-with-bd/references/decisions.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 83.3 | 83.3 |
| findings | 57 | 0 confirms |

PRESERVE: factual_polarity_or_contrast=5, normative_obligation=4
ABSTAIN: ambiguous_unit=18, missing_context=2, needs_repository_fact=2, no_exact_evidence=3

## docs/testing.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 84.1 | 84.1 |
| findings | 109 | 0 confirms |

PRESERVE: factual_polarity_or_contrast=3, normative_obligation=4, quoted_specimen=1
ABSTAIN: ambiguous_unit=56, missing_context=8, needs_repository_fact=2, no_exact_evidence=5

## agents/orc-planner.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 82.8 | 82.8 |
| findings | 24 | 0 confirms |

PRESERVE: normative_obligation=6
ABSTAIN: ambiguous_unit=4, needs_repository_fact=3, no_exact_evidence=1

## agents/orc-reviewer.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 84.9 | 84.6 |
| findings | 24 | 2 confirms |

### CONFIRM `ai-tells-content-shape.elegant-variation` (suggestion)

> reviewed task reopens for the same implementer with your findings; you re-check it.

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-content-shape.elegant-variation` (suggestion)

> The brief may name several implementations from one wave; judge each against its own criteria and report per bead.

Rewrite: withheld_checker_veto

PRESERVE: factual_polarity_or_contrast=1, normative_obligation=7
ABSTAIN: needs_repository_fact=1, no_exact_evidence=8

## agents/orc-lead.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 85.0 | 85.0 |
| findings | 48 | 0 confirms |

PRESERVE: factual_polarity_or_contrast=1, normative_obligation=9
ABSTAIN: needs_repository_fact=1, no_exact_evidence=2
