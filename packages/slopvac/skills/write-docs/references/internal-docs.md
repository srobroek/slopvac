# Internal Docs (specs, ADRs, constitutions, CONTRIBUTING, runbooks)

Audience: contributors. Internal references (specs, ADRs, issues, constitutions)
are allowed -- link them, do not restate them.

MUST Same prose discipline as consumer docs: declarative sentences, lists and tables over paragraphs, no slop lexicon.
MUST ADRs: context · decision · consequences; one line per rejected alternative.
MUST Specs: every requirement testable; no aspiration without an acceptance criterion.
DEFAULT Structured status metadata (ADR "Status: Accepted", spec frontmatter) is allowed; status narration inside body prose is not.
NOT Journey narration: "after much discussion", "we initially tried", "it was decided".
NOT Restating a linked source -- reference it once.

## Exception routing

Exception routing is based on document purpose, not a passage's wording. Migration guides and explicit before/after change tracking use `change-comms`. ADRs and decision records, future release plans and specifications, and explicitly historical reports or data use `internal`. A procedure or reference document uses `reference` only when its purpose is current operation or reproducibility. Do not classify one of these documents as `consumer` to exempt its history or future content.
