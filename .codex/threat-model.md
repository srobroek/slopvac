# Slopvac threat model

> Security context for Codex Security scans and Security Review. Keep this file
> aligned with the code; it describes the current deterministic linter, not planned
> features.

Last reviewed: 2026-09-25

## Scope and architecture

Slopvac is a Python 3.11+ command-line linter and composite GitHub Action. It
processes prose, documentation, and source-code comments using packaged deterministic
rules plus an optional Vale subprocess. It can emit text, JSON, HTML, GitHub
workflow annotations, and SARIF.

The normal lint path is local and has no application server, account system,
database, or inbound network endpoint. The GitHub Action adds package installation,
Vale download/execution, Git diff handling, workflow annotations, and optional SARIF
upload. Repository workflows build, test, scan, release, and publish the package.

The optional agentic judgement / typed-judge layer described in the roadmap and
issue #162 is **not part of the current CLI or security boundary**. Update this
model before that feature ships, especially if it adds model endpoints, API keys,
remote inference, or new untrusted model output.

## Security objectives

Protect these properties:

- **No unintended code execution.** Linting attacker-controlled prose, comments,
  configuration, rule data, paths, filenames, or Git diffs must not become shell
  or arbitrary process execution.
- **No unintended filesystem access.** Read and write operations must stay within
  the paths explicitly authorized by the caller. In particular, `--fix`,
  `init`, `setup`, report output, generated Vale files, and caches must not
  follow malicious links or traverse to unintended files.
- **CI isolation.** Pull-request content must not obtain repository secrets,
  writable credentials, release credentials, or unintended GitHub token
  capabilities.
- **Release integrity.** Git tags, release metadata, built distributions, PyPI
  publication, and release automation must not be controllable by an untrusted
  contribution without the intended review/approval boundary.
- **Fail closed when analysis is incomplete.** Invalid configuration, broken
  rules, missing or failing Vale checks, bad diff state, and malformed tool output
  must not be reported as a clean lint pass.
- **Safe result rendering.** Attacker-controlled paths or source-derived text must
  not inject HTML, GitHub workflow commands, SARIF structure, terminal control
  behavior, or misleading report content.
- **Bounded resource use.** Hostile files, patterns, rule sets, and tool output
  should not cause unreasonable CPU, memory, disk, process, or network use.

## Attacker and trust model

Primary attacker: a contributor who can provide files for Slopvac to inspect,
including through a pull request to a repository that runs Slopvac in CI.

Treat as **untrusted input**:

- file contents, source comments, markup, Unicode, and file size;
- repository-relative filenames and paths, including unusual Git-valid names;
- changed-file lists, diff paths, and other Git-derived metadata;
- `slopvac.toml` / `.slopvac.toml` / `pyproject.toml` when they come from an
  untrusted checkout;
- vocabulary files referenced by project configuration;
- custom rule YAML supplied through `--rules-dir`;
- stdout/stderr/JSON returned by Vale or other external helper programs;
- report strings that can contain source-derived matches;
- any GitHub Action input that a calling workflow derives from pull-request
  content or other attacker-controlled data.

Treat as **operator-authorized configuration, not a sandbox boundary**:

- explicit CLI target paths and globs;
- `--config`, `--rules-dir`, `--out`, `--fix`, compile/reference output
  paths, and setup/init commands;
- the configured `vale.binary`;
- GitHub Action inputs such as `source`, `version`, `rules-dir`,
  `config`, `sarif-file`, and `vale-version`.

Those values are legitimate power-user controls. They are not safe to populate
from untrusted PR metadata unless the caller separately constrains them.

External trust anchors include GitHub, PyPI, the Vale GitHub release repository,
pinned GitHub Actions, the local Python/runtime toolchain, and executables found on
`PATH`. Compromise of those dependencies is a supply-chain threat rather than
an input-validation bug in Slopvac.

## Entry points and important data flows

### 1. CLI target collection

Targets may be files, directories, or globs. Directory traversal deliberately
does not follow symlink directories or symlink files. Explicit paths and globs
still require review for link traversal, race conditions, path normalization, and
reads outside the intended project root.

Source text flows into parsers, native regex/metric rules, optional Vale, scoring,
and output renderers.

### 2. Project configuration

Configuration is loaded with `tomllib` and strict Pydantic models. Configuration
can affect thresholds, rule severity, exclusions, locale, vocabulary, and Vale
settings.

Security-sensitive configuration includes:

- `[vocabulary].path`, which may be absolute and therefore can reference a
  readable file outside the repository;
- `vale.binary`, which selects an executable through `PATH`;
- any explicit config path supplied by the caller.

These are trusted local configuration features. CI must treat contributor changes
to them as untrusted when the job has capabilities worth protecting.

### 3. Extra rule directories

`--rules-dir` loads YAML and regex-based rules. YAML parsing uses safe loaders,
and rules are eagerly validated, but custom regexes and examples are still
attacker-influenced computation if a caller points this option at untrusted data.

### 4. Vale subprocess boundary

Slopvac compiles selected rules into a generated Vale tree, probes Vale to verify
that rules resolve, then invokes Vale with argument arrays rather than a shell.
Vale output is parsed as untrusted JSON.

In the GitHub Action, `scripts/install_vale.py` downloads a selected Vale release
and its checksum file from the official GitHub release location, verifies SHA-256,
extracts only the expected regular-file `vale` member, installs it to a temporary
prefix, and executes it.

Review both the integrity of the download process and ways untrusted
`vale-version` or executable configuration could alter what is run.

### 5. Git diff boundary

Changed-file mode runs Git commands with argument arrays and parses diff paths.
`diff_scope.py` resolves changed paths under the Git root and rejects symlinked
changed paths and root escapes.

Review unusual Git filenames, malformed/ambiguous patch paths, revisions,
submodules/worktrees, filesystem races, and any discrepancy between the file Git
describes and the file later read or modified.

### 6. File modification

`--fix` can modify lint targets. The replacement path currently skips symlinks
and hardlinks, verifies that the exact expected source span is still present, and
only changes eligible spans. Harness setup uses project-contained Markdown targets
and atomic replacement.

Review for TOCTOU, link replacement after validation, path aliasing, permission
changes, writes outside the intended project, and partial/corrupt writes.

### 7. GitHub Action installation and outputs

The composite Action can:

- install Slopvac with `uvx --from <source>`; `source` may be a local path or
  URL and therefore represents deliberate code execution selected by the workflow;
- install and execute Vale;
- consume repository paths/configuration/rules;
- write JSON/SARIF files and GitHub outputs;
- print GitHub workflow-command annotations;
- upload SARIF when the caller grants `security-events: write`.

Review all boundaries between repository-controlled strings and
`GITHUB_OUTPUT`, `GITHUB_STEP_SUMMARY`, workflow commands, SARIF, and log output.

### 8. Release and publishing workflows

Publishing builds distributions on GitHub-hosted runners and publishes with PyPI
Trusted Publishing/OIDC. The publish workflow disables dependency cache on the
publishing path and pins third-party Actions by commit SHA.

`release-please.yml` can use a GitHub App private key to mint a token with
repository write capability, falling back to `GITHUB_TOKEN`. Treat the release
App private key, minted token, OIDC identity, tags, release configuration, and
published distributions as high-value assets.

The workflow declares a `pypi` environment and is designed to rely on environment
approval. Repository environment-protection settings are an external control and
must be verified separately; this file does not assume they are present merely
because the workflow names the environment.

## Sensitive data and report handling

Slopvac does not require application secrets to lint text. Nevertheless, users may
point it at files containing secrets or confidential source text.

The JSON report includes each finding's `matched_text`. Treat JSON reports and
any artifacts derived from them as potentially containing source excerpts.
GitHub annotations, summaries, HTML, and SARIF may also reveal paths, rule
messages, and source-derived information. Do not intentionally lint secret stores,
and do not publish reports from private/sensitive repositories to public
locations.

## Existing controls to account for

Codex should test these controls for bypasses rather than assume their presence
eliminates the threat:

- subprocess calls use argv lists rather than `shell=True`;
- YAML loaders for rule/vocabulary data are safe loaders;
- configuration models reject unknown fields and malformed input;
- incomplete lint execution uses exit code 2 instead of silently passing;
- Vale rules are validated before shared-cache publication, and cache publication
  uses staging plus atomic replacement/locking;
- diff-scoped paths reject symlinks and paths escaping the Git root;
- `--fix` skips symlinks and hardlinks and rechecks source spans before writes;
- managed agent steering targets are constrained to project Markdown files and
  written atomically;
- standalone HTML escapes interpolated values;
- Vale release archives are checksum-verified and selectively extracted;
- repository Actions are pinned by commit SHA;
- PR workflows generally use read-only contents permission and checkout with
  `persist-credentials: false`;
- CodeQL, Trivy, OSV, TruffleHog, dependency review, and action-pin checks run in
  CI;
- PyPI publishing uses OIDC rather than a stored PyPI API token.

## Review priorities

Review these areas first, in roughly this order:

1. **GitHub workflow-command injection.** The current `github` formatter builds
   `::error` / `::warning` / `::notice` command strings directly from
   finding paths, rule IDs, and messages. Validate whether Git-valid filenames or
   source-derived message content containing newlines, `%`, commas, colons, or
   workflow-command syntax can alter runner commands or annotations. Require
   GitHub-command escaping if validation confirms the path.
2. **Path traversal, symlink, hardlink, and TOCTOU behavior.** Cover explicit
   targets/globs, `--fix`, config/vocabulary paths, report output, generated Vale
   directories, cache directories, steering files, and changed-file mode.
3. **Process execution from configuration or Action inputs.** Trace
   `vale.binary`, `source`, `version`, `vale-version`, helper binaries found
   on `PATH`, and any future external tool setting. Distinguish intended
   operator-authorized execution from execution reachable through untrusted repo
   content.
4. **CI permission and secret boundaries.** Verify that PR-controlled code cannot
   reach the release App key, minted write token, PyPI OIDC publication, writable
   checkout credentials, or unnecessary GitHub token scopes. Give special
   attention to jobs that execute `uses: ./` from the PR checkout.
5. **Supply-chain integrity.** Review `uvx` package/source resolution, Vale
   release download/checksum trust, build dependencies, pinned Actions, release
   tag handling, artifact handoff between build and publish jobs, and dependency
   update automation.
6. **Fail-open analysis paths.** Look for exceptions, parser/tool errors, malformed
   Vale output, cache corruption, missing rules, diff failures, or Action
   `continue-on-error` behavior that can produce exit 0 or a misleading clean
   report when checks did not run.
7. **Output and report injection.** Validate GitHub output-file protocol,
   step-summary Markdown, terminal/log output, SARIF fields, JSON, and HTML against
   hostile filenames and source text. HTML already centralizes escaping; verify
   the other formats to the same standard.
8. **Resource exhaustion.** Exercise very large files, deeply nested markup,
   pathological Unicode, expensive regexes/custom rule sets, huge Git diffs,
   oversized Vale output, and cache growth. External subprocesses should have
   practical timeouts and bounded output where appropriate.
9. **Report confidentiality.** Confirm which formats include source excerpts and
   whether default CI behavior can upload or expose them more broadly than the
   source repository itself.

## Assumptions and non-goals

- Slopvac is a developer tool, not a sandbox for executing arbitrary untrusted
  binaries or configurations.
- A caller that explicitly chooses an executable, package URL, custom rule
  directory, arbitrary output path, or file outside the repository is authorizing
  access to that resource with the invoking process's OS permissions.
- The local CLI inherits the invoking user's filesystem and process privileges.
  Running Slopvac on an untrusted checkout does not create an isolation boundary.
- GitHub-hosted runners are the intended CI environment. A self-hosted runner
  materially increases the impact of filesystem, credential, persistence, and
  process-execution bugs and should be threat-modeled separately.
- Correctness of prose/style findings is not a security property unless a failure
  can be used to bypass a security gate or trigger a privileged side effect.

## Update this model when

Update this file when Slopvac adds or changes:

- network services or remote APIs;
- the planned semantic/judge layer;
- authentication, tokens, or model/provider credentials;
- executable/plugin discovery;
- rule or configuration loading;
- file-writing behavior;
- GitHub Action inputs or permissions;
- release/publishing credentials or workflow structure;
- report formats or uploads;
- cache location, format, or trust assumptions.
