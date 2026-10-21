# Security policy

## Supported versions

Slopvac provides security fixes for the latest minor release on PyPI. Older minor releases do not receive backported fixes.

## Report a vulnerability

Use [GitHub's private reporting feature](https://github.com/srobroek/slopvac/security/advisories/new) to report vulnerabilities. Do not report them in public issues.

Include these details in your report:

- Affected Slopvac version and component
- Operating system and Python version
- Steps to reproduce
- Expected behavior and observed behavior
- Impact
- A minimal proof of concept, when available

Remove secrets and private or proprietary text. Do not attach sensitive sample data.

The maintainer aims to acknowledge reports within seven days and assess them within 14 days. The maintainer shares material status changes when possible. For this single-maintainer project, these are best-effort targets. Report complexity and maintainer availability affect timing.

## Scope

This policy covers:

- The Slopvac CLI
- The [published Python package](https://pypi.org/project/slopvac/)
- The GitHub Action in [`action.yml`](action.yml)
- The pre-commit hooks in [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml)

See the [Codex Security threat model](.codex/threat-model.md) for the project's security objectives, trust boundaries, and review priorities.
