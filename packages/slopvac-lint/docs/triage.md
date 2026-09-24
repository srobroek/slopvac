# Finding triage

A deterministic finding says that a rule matched. Severity controls reporting and
gating; it is not a confidence score. Read the matched passage before changing
meaning, including for an error-level finding.

## Triage a deterministic finding

JSON output gives the information needed to inspect one match:

| Field | Use |
| --- | --- |
| `rule_id` | Look up the rule contract |
| `line`, `column`, `end_column` | Locate the match |
| `matched_text` | See what triggered the rule |
| `replacement` | Use the deterministic replacement when one exists |
| `severity` | Understand the configured gate consequence |

Use `slopvac explain <rule_id>` for the rule's rationale, examples, fix, and
closed exception list.

Classify the match as one of these cases:

- **Defect:** change the prose without changing the underlying fact.
- **Named exception:** keep the prose and use a suppression reason listed by the
  rule.
- **False positive:** keep the prose, do not invent a suppression reason, and
  report the rule and matched text so the rule can be improved.

A high-severity false positive is still a false positive. If a project
deliberately wants different policy, change its configuration rather than
rewriting correct prose to satisfy a pattern.

## Suppress only documented exceptions

A suppression must use a reason returned by `slopvac explain`:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

An unknown reason is reported as `meta.invalid-suppression`. Use
`slopvac-disable` regions for material that is intentionally specimen text, such
as examples whose purpose is to demonstrate a bad pattern. Do not use a
suppression to hide an unexplained false positive.

## Contextual judgement is separate

The 65 `kind: judgement` rules do not produce deterministic lint findings.
Use the judgement workflow when contextual review is required:

```sh
slopvac judgement brief README.md --out .slopvac-review --packs fired
```

`--packs fired` selects judgement packs whose categories also produced a
deterministic finding. If no category qualifies, `brief` falls back to all packs
and prints a warning. Use `--packs all` when the review must not depend on
deterministic findings.

The harness or provider performs the model calls. Validate each response before
recording it, then finish and compare the run:

```sh
slopvac judgement validate --run .slopvac-review --file response.json
slopvac judgement finish --out .slopvac-review \
  --responses .slopvac-review/responses.jsonl
slopvac judgement compare --out .slopvac-review
```

`validate` checks the response shape and the expected result set. `finish`
performs the host evidence checks and coverage accounting. Model outcomes remain
separate from deterministic pass/fail.

## Review claims separately

Neither deterministic lint nor model judgement proves that a factual statement
is correct. For documentation, verify commands, paths, defaults, versions, and
behavior against the implementation or another authoritative source before
publishing the text.
