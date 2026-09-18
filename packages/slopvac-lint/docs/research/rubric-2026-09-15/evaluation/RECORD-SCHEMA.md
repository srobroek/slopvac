# Evaluation record schema

Normalized files are written beside each source record as
`<record>.normalized.json`. They retain the complete `raw_record` and the raw
outcome/adjudication counters; normalization never fills an unavailable value.
Unavailable measurements are `null` and named in `not_derivable`.

## Required fields

- `metrics.strict_precision`: `TP / (TP + FP + borderline)`. Borderline is an
  FP in the strict view.
- `metrics.lenient_precision`: `(TP + borderline) / (TP + FP + borderline)`.
  Borderline is a TP in the lenient view. `FP-*` labels remain false positives;
  in particular, `FP-PRESERVE-MISS` is a false positive that should have been
  preserved and is counted as FP.
- `metrics.abstention_rate`: `ABSTAIN / all units`.
- `metrics.evidence_validity`: `host_confirms_after_gate /
  model_confirms_before_gate`. The numerator sums host confirms across all
  repositories in a record; the denominator is only the explicit pre-gate
  model `confirm` counter. Outcome `CONFIRM` counters are not model confirms.
- `per_rule`: one row per rule with TP, FP, borderline, and both precision views.
  A missing rule-level adjudication remains an empty table, never a fabricated
  zero.
- `raw_outcomes` and `raw_adjudication`: counters copied from the source.
- `denominators`: the numeric denominator, when derivable, and its definition.

## Denominator and coverage rules

`all_units` means **distinct `unit_id` values**, not response rows. Duplicate
response rows therefore cannot increase coverage. `response_rows` is retained
as a diagnostic count and is never used as the unit denominator.

Failed and truncated units, and eligible units with no response, are counted as
`not-run` for coverage. They are not silently converted into abstentions or
removed from the denominator. An abstention is a completed adjudication and is
reported separately by reason. When the source record does not expose distinct
unit IDs, the normalized record leaves `all_units` and abstention rate null and
records the reason in `not_derivable`.

The normalizer only derives values from counters, unit IDs, and adjudication
rows already present in the source. It does not infer a denominator from
`pairs`, `calls`, documents, or prose such as a caveat.
