# Finding triage

A deterministic finding says that a rule matched. Severity controls reporting and
gating; it is not a confidence score. Read the matched passage before changing
meaning, including for an error-level finding.

## Triage a deterministic finding

JSON output includes the fields needed to inspect one match:

| Field | Use |
| --- | --- |
| `rule_id` | Look up the rule contract |
| `line`, `column` | Locate the finding; `end_column` can be absent |
| `matched_text` | See what triggered the rule; metric and structure findings can leave it empty |
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

A suppression must use a named exception of the rule. `slopvac explain
<rule_id>` lists them:

```markdown
<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->
```

Before you suppress, keep specimens and commands in code and quotations in
quotation marks. `slopvac prime write` gives that order. `slopvac prime`
summarizes the scope of each directive and what lint reports for a bad one.
`slopvac prime review` gives the audit for each directive. The
[suppressions and exclusions reference](suppressions.md) holds the full
grammar, the edge cases, and the config controls.

Do not use a suppression to hide an unexplained false positive.

## Review claims separately

Lint does not prove that a factual statement is correct. For documentation, verify commands, paths, defaults, versions, and
behavior against the implementation or another authoritative source before
publishing the text.
