# slopvac

This repository ships the `slopvac` CLI and its agent skills. The CLI checks prose against configured rules in `slopvac.toml`; `write-docs` and `review-docs` use that contract for authoring and review.

Run the relevant package tests with `pytest`; use `uvx slopvac <files...>` for the prose gate. A document is ready only when the CLI clears its thresholds and the review finds no clustered register tells.
