# Finding triage

A deterministic finding says that a rule matched. Severity controls reporting and
gating; it is not a confidence score. Read the matched passage before changing
meaning, including for an error-level finding.

## Triage a deterministic finding

JSON output includes the fields needed to inspect one match:

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

An unknown reason is reported as `meta.invalid-suppression`. For intentional
specimen text, including examples whose purpose is to show a bad pattern, disable
linting around the specimen rather than weakening the rule:

```markdown
<!-- slopvac-disable -->
This example intentionally contains text that a rule should reject.
<!-- slopvac-enable -->
```

Do not use a suppression to hide an unexplained false positive.

## Review claims separately

Lint does not prove that a factual statement is correct. For documentation, verify commands, paths, defaults, versions, and
behavior against the implementation or another authoritative source before
publishing the text.
