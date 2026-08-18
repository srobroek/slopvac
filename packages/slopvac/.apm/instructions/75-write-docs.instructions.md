---
description: Apply the prose rules to every document, and check the result with slopvac.
---

When writing or reviewing a README, docs, spec, ADR, constitution, PR
description, commit message, release notes, CONTRIBUTING, or runbook, use the
write-docs skill; without skill support, apply
[write-docs rules](../context/write-docs.write-docs-index.context.md) directly.

Either way, check the result with `uvx slopvac <file>` before calling the
document done. The linter owns every word list, substitution, and length limit, so
never restate one from memory -- run it and read what it reports. Exit 2 means
nothing was checked, which is not a pass.
