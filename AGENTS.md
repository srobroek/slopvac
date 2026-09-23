# slopvac

This repository ships the Slopvac CLI and its packaged rule catalog.
Run the source package when validating this repository, not a published release.
Use `uv run --project packages/slopvac-lint slopvac` and run the relevant tests
with `uv run --project packages/slopvac-lint python -m pytest`.
A linguistic pass does not establish content accuracy or completeness.

<!-- slopvac:begin -->
## Slopvac documentation checks

Use `slopvac` when writing or reviewing documentation and source comments.
Run `slopvac prime` for the workflow, or `slopvac prime lint` and
`slopvac prime judgement` for details. Reload this guidance after compaction.

Run the linter with Vale available. An incomplete check is not a pass.
Use `slopvac explain <rule-id>` for rule details and permitted exceptions.
For requested contextual review, use the CLI's judgement prompts and validation.
Check factual accuracy and task completeness against source evidence separately;
report anything you could not verify. Keep the deterministic result separate
from model judgements. Do not weaken project settings to obtain a pass.
<!-- slopvac:end -->
