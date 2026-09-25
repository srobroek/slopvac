# slopvac

This repository ships the `slopvac` CLI. Run `slopvac prime` before writing or
reviewing prose; it prints the current lint guidance from the installed version.

Run the relevant package tests with `pytest`. Use
`uvx --from ./packages/slopvac-lint slopvac <files...>` for the repository
prose gate. Treat lint exit 2 as incomplete, and verify documentation claims
against the code rather than inferring correctness from a prose score.
