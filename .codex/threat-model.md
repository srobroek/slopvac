# Slopvac threat model

> Codex Security scan and Security Review context. This describes the current
> deterministic linter. Update it when the architecture or trust assumptions change.

Last reviewed: 2026-09-25

## Project overview

Slopvac is a Python 3.11+ CLI and composite GitHub Action that lints prose,
documentation, and source-code comments. It uses packaged deterministic rules and
an optional Vale subprocess, then emits text, JSON, HTML, GitHub annotations, or
SARIF.

There is no application server, database, account system, or inbound network
endpoint. The main security boundaries are local filesystem access, subprocess
execution, parsing attacker-controlled repository content, GitHub Actions, and the
release/publishing supply chain.

The planned agentic judgement / typed-judge layer in issue #162 is **not part of
the current CLI or this threat model**. Update this file before that feature ships.

## Security objectives

- Linting untrusted repository content must not cause arbitrary code execution.
- Reads and writes must not escape paths deliberately authorized by the caller.
- Pull-request content must not gain secrets, writable credentials, release
  capabilities, or unintended GitHub token permissions.
- Incomplete analysis must fail closed rather than appear clean.
- Hostile source text and filenames must not inject workflow commands, HTML,
  SARIF, terminal/log control data, or misleading report structure.
- Release tags, artifacts, and PyPI publication must remain maintainer-controlled.
- Hostile inputs should not cause unreasonable CPU, memory, disk, process, or
  network use.

## Attacker model and untrusted inputs

Primary attacker: a contributor who can provide files for Slopvac to inspect,
including through a pull request.

Treat these as untrusted:

- file contents, source comments, markup, Unicode, and file size;
- Git-valid filenames and repository-relative paths;
- changed-file paths and other Git-derived metadata;
- project configuration from an untrusted checkout;
- vocabulary data referenced by project configuration;
- custom rule YAML when a caller enables `--rules-dir`;
- Vale stdout/stderr/JSON and output from other helper executables;
- source-derived finding text used in reports or annotations;
- GitHub Action inputs if a calling workflow derives them from PR-controlled data.

These are **operator-authorized capabilities, not sandbox boundaries**:

- explicit CLI targets/globs and `--config`, `--rules-dir`, `--out`,
  `--fix`, compile/reference output, setup, and init;
- configured `vale.binary`;
- Action inputs including `source`, `version`, `rules-dir`, `config`,
  `sarif-file`, and `vale-version`.

A workflow must not populate those capabilities from attacker-controlled data
unless it separately constrains the value.

## Important trust boundaries

### Filesystem and Git

Target collection reads repository files. Directory walks do not follow symlink
directories/files. Diff-scoped paths are resolved under the Git root and reject
symlinked changed paths and root escapes.

`--fix` is privileged: it writes source files. It currently skips symlinks and
hardlinks and verifies the expected source span before replacing it. Agent
steering setup writes only project-contained Markdown targets and uses atomic
replacement.

Review explicit file/glob targets, path normalization, symlink/hardlink handling,
TOCTOU races, report/output paths, caches, worktrees/submodules, and unusual Git
filenames.

### Configuration and rule loading

Configuration uses `tomllib` plus strict Pydantic models. Vocabulary YAML uses a
safe loader. Extra rule YAML also uses safe loading and eager rule/regex
validation.

Security-sensitive configuration includes:

- `[vocabulary].path`, which may be absolute and can therefore read a file
  outside the repository;
- `vale.binary`, which selects an executable through `PATH`;
- explicit config/rules/output paths chosen by the caller.

These are intentional local-tool capabilities. They become security-sensitive
when an untrusted checkout controls them inside a privileged CI job.

### Vale and subprocesses

Slopvac invokes Git, Vale, uvx, and helper executables with argument arrays rather
than `shell=True`. Vale rule trees are generated and probed before use; malformed
or missing checks should produce an incomplete result rather than a clean pass.

The GitHub Action downloads a selected Vale release and checksum file from Vale's
GitHub release location, verifies SHA-256, extracts only the expected regular-file
`vale` member, then executes it.

Review executable selection, `vale-version`, package/source resolution, tool
output parsing, timeouts, output-size limits, and upstream-release compromise.

### GitHub Action and report surfaces

The composite Action can install Slopvac with `uvx --from <source>`, where
`source` may be a path or URL; this is deliberate workflow-authorized code
execution. It can also install Vale, read checkout content, create JSON/SARIF
files, write `GITHUB_OUTPUT` and `GITHUB_STEP_SUMMARY`, print workflow
annotations, and upload SARIF when the caller grants `security-events: write`.

The JSON report includes each finding's `matched_text`. Treat reports/artifacts
as potentially containing source excerpts.

### CI, release, and publishing

PR workflows generally use read-only contents permission and checkout with
`persist-credentials: false`. Several jobs execute code from the PR checkout,
including `uses: ./`; their token/secrets boundary is therefore important.

Third-party Actions are pinned by commit SHA. Security CI includes CodeQL, Trivy,
OSV, TruffleHog, dependency review, and pin checks.

Publishing uses PyPI Trusted Publishing/OIDC. `release-please.yml` may use a
GitHub App private key to mint a repository-write token, falling back to
`GITHUB_TOKEN`. Treat the App key, minted token, OIDC identity, release tags,
build artifacts, and publishing environments as high-value assets.

The workflow names a protected `pypi` environment, but environment protection is
a repository setting and must be verified separately.

## Review priorities

Review these areas first:

1. **GitHub workflow-command injection.** The current `github` formatter builds
   `::error` / `::warning` / `::notice` strings directly from finding paths,
   rule IDs, and messages. Test Git-valid filenames and source-derived content
   containing newlines, `%`, commas, colons, or workflow-command syntax. Require
   GitHub-command escaping if the path is exploitable.
2. **Path/link/TOCTOU escape.** Test explicit targets/globs, `--fix`, vocabulary
   paths, report paths, generated Vale/cache directories, steering files, and
   changed-file mode.
3. **Execution through configuration or Action inputs.** Trace `vale.binary`,
   `source`, `version`, `vale-version`, custom rules, and helper binaries.
   Separate intended operator-authorized execution from PR-reachable execution.
4. **CI privilege boundaries.** Verify PR-controlled code cannot reach the release
   App key, write token, PyPI OIDC publishing, writable checkout credentials, or
   unnecessary GitHub scopes.
5. **Supply-chain integrity.** Review uvx resolution, Vale download/checksum trust,
   pinned Actions, build dependencies, tag handling, and build-artifact handoff to
   publishing jobs.
6. **Fail-open behavior.** Look for parser/tool errors, malformed Vale output,
   missing rules, cache corruption, diff failures, or `continue-on-error` paths
   that can yield exit 0 or a misleading clean result.
7. **Output injection/confidentiality.** Test `GITHUB_OUTPUT`, step-summary
   Markdown, terminal output, SARIF, JSON, and HTML against hostile paths/content.
   HTML already centralizes escaping; verify equivalent safety elsewhere.
8. **Resource exhaustion.** Exercise large files, pathological Unicode/markup,
   expensive custom regexes, huge diffs, oversized tool output, and cache growth.

## Existing controls worth testing for bypasses

- argv-based subprocess calls rather than shell execution;
- safe YAML loaders and strict config validation;
- exit code 2 for analysis that cannot be trusted;
- validated Vale cache publication using staging/locking/atomic replacement;
- Git-root and symlink validation in diff scope;
- symlink/hardlink and exact-span checks before `--fix` writes;
- project-contained, atomic agent-steering writes;
- centralized HTML escaping;
- checksum verification and selective extraction of downloaded Vale;
- SHA-pinned Actions and mostly least-privilege PR workflows;
- OIDC-based PyPI publishing rather than a stored PyPI API token.

## Assumptions and non-goals

- Slopvac is a developer tool, not a sandbox for arbitrary untrusted binaries or
  configuration.
- Explicitly choosing an executable, package URL, custom rule directory, arbitrary
  output path, or external file authorizes access using the invoking process's OS
  permissions.
- The local CLI inherits the invoking user's filesystem/process privileges.
- GitHub-hosted runners are the intended CI environment. Self-hosted runners have
  a materially larger persistence, credential, and filesystem impact.
- Style/prose correctness is not itself a security property unless it bypasses a
  gate or triggers a privileged side effect.

## Update this model when

Update this file for new network/API integrations, the semantic judge layer,
credentials, executable/plugin discovery, rule/config loading, file-writing
behavior, Action permissions/inputs, release credentials, report uploads, or cache
trust assumptions.
