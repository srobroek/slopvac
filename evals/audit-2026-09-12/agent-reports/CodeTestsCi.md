# Summary

Reviewed 279 test functions across 11 lint-package modules plus the repository plugin module, then the action, hooks, scripts, six workflows, release metadata, local mise config, wheel, and plugin manifests.
The strongest defect is rule-example verification: it searches a bare regex, not the shipped scope/profile/allowlist/exception path or whole ruleset.
`test_locale_flag` is four padding rows: `should_find` is never read and every row asserts the same no-Vale outcome.
Public install examples still pin v2.0.0 while all current package and hook manifests are 2.2.0.
The observed wheel is sound: 21 packaged rule YAML files, its console entry point, and no verified Vale test fixture.

# Test classification

Counts are test functions, not parameter expansions. Contract means observable consumer behavior; implementation-pinning includes helpers, routing tables, internal models, source/layout, or exact wording; tautology has no independent oracle; padding repeats the same path without a new boundary.

| module | contract | implementation-pinning | tautology | padding | total |
| --- | ---: | ---: | ---: | ---: | ---: |
| packages/slopvac-lint/tests/test_cli.py | 46 | 4 | 1 | 3 | 54 |
| packages/slopvac-lint/tests/test_compile_vale.py | 24 | 15 | 1 | 1 | 41 |
| packages/slopvac-lint/tests/test_config.py | 10 | 3 | 0 | 0 | 13 |
| packages/slopvac-lint/tests/test_engine.py | 61 | 21 | 2 | 3 | 87 |
| packages/slopvac-lint/tests/test_html.py | 12 | 0 | 0 | 0 | 12 |
| packages/slopvac-lint/tests/test_reference.py | 0 | 1 | 0 | 0 | 1 |
| packages/slopvac-lint/tests/test_report.py | 7 | 2 | 2 | 0 | 11 |
| packages/slopvac-lint/tests/test_ruleset.py | 9 | 10 | 1 | 0 | 20 |
| packages/slopvac-lint/tests/test_vale_backend.py | 2 | 0 | 0 | 0 | 2 |
| packages/slopvac-lint/tests/test_vale_rules.py | 8 | 7 | 0 | 0 | 15 |
| packages/slopvac-lint/tests/test_vocabulary.py | 18 | 3 | 0 | 0 | 21 |
| tests/test_plugin_package.py | 1 | 1 | 0 | 0 | 2 |
| **Total** | **198** | **67** | **7** | **7** | **279** |

The target has 12 test modules rather than the stated 13. Contract tests are 71.0%; 74 functions (26.5%) pin implementation or have no independent oracle, and seven (2.5%) are same-path padding.

# Ten worst pinned, tautological, or padded tests

1. `packages/slopvac-lint/tests/test_cli.py:241` `test_locale_flag`: four rows provide `should_find`, but the body never reads it; all run `--no-vale` and assert `not spelling`. A CLI that ignores every locale passes.
2. `packages/slopvac-lint/tests/test_report.py:104` `test_the_json_payload_round_trips_through_its_own_model`: producer and oracle share `LintReport`; a wrong but internally consistent public schema passes.
3. `packages/slopvac-lint/tests/test_report.py:204` `test_a_result_without_a_fingerprint_is_rejected_at_construction`: directly tests Pydantic requiredness; CLI fingerprint tests already cover the consumer contract.
4. `packages/slopvac-lint/tests/test_report.py:216` `test_an_off_specification_level_is_rejected`: tests an internal enum by directly constructing `SarifResult`, not emitted SARIF.
5. `packages/slopvac-lint/tests/test_reference.py:14` `test_judgement_example_without_good_renders`: constructs and mutates internal models and pins three rendered fragments; it never invokes the reference CLI or validates the generated document.
6. `packages/slopvac-lint/tests/test_vale_rules.py:283` `test_multi_entry_raw_list_is_never_used`: bans one YAML representation; an equivalent compiler fails despite identical findings.
7. `packages/slopvac-lint/tests/test_vale_rules.py:303` `test_nonword_is_never_used`: source-structure prohibition; the actual contract is compiled-rule load and fire behavior.
8. `packages/slopvac-lint/tests/test_compile_vale.py:177` `test_vocabulary_rules_compile_to_grouped_sequence_rules`: pins grouping and an alias-count formula rather than latency, artifact size, or duplicate findings.
9. `packages/slopvac-lint/tests/test_engine.py:711` `test_all_caps_predicate`: 12 direct rows against private `_is_all_caps`; line 715 has the stronger full-engine contract. Several rows add no consumer boundary.
10. `tests/test_plugin_package.py:30` `test_omp_marketplace_uses_native_skill_root`: exact schema URL and absence of `.apm/skills` pin layout. The contract is successful plugin discovery.

# Ten most valuable contract tests

1. `test_cli.py:477` missing Vale produces exit 2, passed=false, and an unchecked explanation.
2. `test_config.py:42` overlapping overrides use file order even when the later glob is broader.
3. `test_engine.py:364` invalid suppression reports meta.invalid-suppression and leaves the original finding active.
4. `test_engine.py:614` score decreases for an observed heavier finding set.
5. `test_cli.py:176` SARIF fingerprints are unique and stable when source lines shift.
6. `test_html.py:90` incomplete-engine warning renders before score.
7. `test_compile_vale.py:347` real Vale word counts match the documented oracle corpus.
8. `test_compile_vale.py:519` every compiled lexical rule fires on its own bad example.
9. `test_compile_vale.py:654` readers cannot see a half-built shared cache tree.
10. `tests/test_plugin_package.py:9` both marketplace sources resolve to manifests containing both skills.

# Contract coverage gaps

The examples named in the assignment are mostly covered: exit 2 (`test_cli.py:95,100,477,513`), override precedence (`test_config.py:42-90`; `test_cli.py:284`), qualified disable (`test_cli.py:312`), SARIF validity (`test_cli.py:161-213`), invalid suppression (`test_engine.py:364`), all-caps masking (`test_engine.py:711-755`), inline-code masking/counting (`test_engine.py:820-851`), score monotonicity (`test_engine.py:614`), and short-document density/scoring (`test_engine.py:458,576`).

Uncovered or indirect contracts:

- No CLI test covers `--open`, `--out report.html`, `--format json --out report.json`, browser dispatch, implied HTML, or stdout/file separation (README `packages/slopvac-lint/README.md:262-271`).
- No test invokes `slopvac cache`, `cache --prune`, or `cache --all`, checks reported path/count/size, or proves `--all` removes trees (README lines 285-294). Cache helpers are well tested.
- No end-to-end CLI test feeds blocking findings to `--profile relaxed` and proves exit 0 because relaxed gates nothing (README lines 59-73).
- No report/CLI test proves suppression-rate tracking, although valid and invalid suppression behavior is covered (README lines 249-257).
- Category `minimum_severity` is tested with constructed objects, not through TOML plus CLI output, including rule-override precedence (README lines 135-141).
- `--rules-dir` is used for an unimplemented-metric fixture, but no public-boundary test proves an added category runs, packaged rules remain, or collision behavior (README lines 392-405).
- HTML checks unchecked-first ordering; terminal format does not have a test for the README's unchecked-before-score promise (README lines 275-280).
- No test drives composite-action `changed-files-only`, empty outputs, `fail-on-findings=false`, `version`, `source` pin semantics, `rules-dir`, SARIF without upload, or missing permission. The one dogfood invocation (`lint.yml:255-281`) covers only nonempty paths, source, SARIF upload, and blocking mode.
- No disposable pre-commit environment runs `slopvac`, `slopvac-strict`, and `slopvac-no-vale`; only manifest resolution is tested.
- No parity test compares release manifest, Python version, pyproject, hook dependencies, package/plugin JSON, and marketplaces. They agree now.

# Findings

## F1: Verify examples through the shipped execution path
- surface: `packages/slopvac-lint/src/slopvac/rules.py:97-141`
- kind: test-gap
- evidence: `_verify_examples` limits itself to TOKENS, PATTERN, and SUBSTITUTION (line 105), compiles a bare Python regex (108-125), and only calls `pattern.search(example.bad/good)` (127-140). It never parses a document, resolves a profile/tier, applies scope, consults allowlist or exceptions, or executes Engine. Good text is checked only against that rule; a good example firing another rule passes. `test_compile_vale.py:519` covers bad examples only.
- proposal: retain compilation checks, then run every lexical example through parser and engine at a profile where the rule is enabled and at its declared scope. Require bad to emit that qualified id. Run good through the complete ruleset and report any id. Add one case per nonempty allowlist and declared exception reason.
- expected effect: correctness and FN↓ across all corpora.
- confidence: high

## F2: Remove the dead locale parameter rows
- surface: `packages/slopvac-lint/tests/test_cli.py:232-251`
- kind: test-gap
- evidence: parametrization supplies `should_find`, but the function never references it. Every row passes `--no-vale` and asserts `not spelling`. Replacing locale with a constant leaves all assertions unchanged.
- proposal: keep one no-Vale accounting test and add a real-Vale CLI matrix asserting `bool(spelling) is should_find` for en-US, en-GB, and und.
- expected effect: correctness; closes a false-green locale path.
- confidence: high

## F3: Add a disposable composite-action contract harness
- surface: `action.yml:107-368`, `.github/workflows/lint.yml:255-281`
- kind: test-gap
- evidence: test search found no `action.yml`, `changed-files-only`, `fail-on-findings`, or `upload-sarif` reference. Dogfood uses fixed nonempty paths, source, sarif=true, and blocking mode; it misses empty outputs (`action.yml:193-210`), changed selection (151-180), nonblocking verdict (337-341), and upload branches (350-368).
- proposal: exercise no changed prose, a changed path containing spaces, shallow-clone refusal, fail-on-findings=false, vale=false/incomplete exit 2, and SARIF written with upload disabled; assert all declared outputs.
- expected effect: correctness in downstream CI.
- confidence: high

## F4: Update public install examples with each release
- surface: `README.md:212-237`
- kind: steering-drift
- evidence: pre-commit and Action examples pin v2.0.0 (`README.md:218,228`), while pyproject, `.pre-commit-hooks.yaml:12,27,42`, all package/plugin manifests, marketplaces, and `.release-please-manifest.json:2` are 2.2.0. Copying the pre-commit example installs the older tag and dependency.
- proposal: add both README versions to release-please extra-files with annotations, or maintain and document a moving major tag; add a parity test.
- expected effect: correctness for downstream installs.
- confidence: high

## F5: Replace redundant implementation tests with boundary probes
- surface: `packages/slopvac-lint/tests/`
- kind: architecture
- evidence: 67/279 functions pin implementation and seven are tautologies. Examples: private predicates (`test_engine.py:711,796`), compiler tables (`test_compile_vale.py:127,177,202,557`), Vale YAML source (`test_vale_rules.py:215-317`), model self-validation (`test_report.py:104,204,216`), exact renderer fragments (`test_reference.py:14`). Several have stronger integration counterparts.
- proposal: retain representation tests only at real safety boundaries (atomic cache, RE2, invalid Vale config). Replace redundant helper/source checks with CLI or real-Vale probes and delete same-path rows.
- expected effect: correctness and maintainability; capacity for uncovered contracts.
- confidence: medium

# CI and delivery inventory

- Tests, Lint, Security, and Supply Chain trigger on PR. Lint aggregates workflow/actionlint/agnix/yamllint, typos, lychee, markdownlint, taplo, pinact, prek/Ruff, lizard, shellcheck, the local action, and prose into `gate` (`lint.yml:301-336`). Workflow logic is blocking. Actual branch-protection configuration is outside the repo and is [INFERENCE].
- Security OSV's raw scan is `continue-on-error`, but the reporter uses `--fail-on-vuln=true` and feeds security-gate. Composite SARIF upload is intentionally advisory; prose verdict remains blocking.
- Only release-please reads `RELEASE_APP_PRIVATE_KEY`; it passes it to a SHA-pinned token action and falls back to GITHUB_TOKEN. PyPI jobs use scoped OIDC `id-token: write`; no stored PyPI token appears.
- Every third-party `uses:` in six workflows and action.yml is pinned to a 40-character SHA with version comment. No unpinned action found.
- Hook ids and pins are consistent: slopvac, slopvac-strict, slopvac-no-vale all pin slopvac==2.2.0. The repository's own pre-commit config runs Ruff only; prose is gated in CI.
- The tracked Git hook chains an existing hook then runs agnix staged validation, not slopvac. Its disposable script covers staged/index and worktree installation.
- `install-vale.sh` downloads Vale plus release checksums and runs sha256sum verification. CI/action default to 3.15.2.
- Primary-checkout `mise.toml` declares 23 developer tools, all at latest. No workflow references mise. `check-agnix-staged.sh:85-118` uses it only under AGNIX_USE_MISE=1. CI installs pinned tools directly and does not depend on the untracked file.

# Packaging and manifests

- pyproject entry point is `slopvac = slopvac.cli:main`; Python floor >=3.11; runtime dependencies have minimum bounds, not exact pins: click, pydantic, pathspec, rich, regex, pyyaml, markdown-it-py. CI tests 3.11-3.14.
- Observed command: `uv build --wheel --out-dir /tmp/slopvac-wheel-audit` against frozen baseline succeeded. Wheel inspection found modules, entry_points.txt, and 21 `slopvac/rules/*.yml`. No `vale/styles-verified`, examples, or wordlist appeared, matching pyproject and publish assertions.
- Version/name parity is 2.2.0 across pyproject, release targets, hooks, package/plugin JSON, native marketplaces, and release manifest. OMP marketplace points to `./packages/slopvac` and intentionally has no duplicate version.
- Claude/Codex manifests both declare `skills: ./skills`; marketplace sources consistently point to `./packages/slopvac`; write-docs and review-docs exist.
- Nested client manifests are regular files, not symlinks. `release-please-config.json:48-84` lists each JSON version path explicitly, so current release handling does not rely on symlink traversal.

# Decommission candidates

- Delete three current locale rows until the test drives Vale; all ignore expected output.
- Replace report model roundtrip and direct SarifResult construction tests with independent emitted-SARIF validation.
- Shrink private all-caps/quotation predicate matrices once full-engine tests cover their boundaries.
- Keep Vale YAML representation bans only if documented as compiler invariants; otherwise real Vale load/fire probes supersede them.

# Checked and fine

- Exit 0/1/2 semantics, override precedence, invalid suppression behavior, and qualified disabling have public-path coverage.
- SARIF shape, descriptors, fingerprints, and context are covered at the CLI boundary.
- Short-document density, score monotonicity, inline-code masking/counting, and all-caps exclusions are covered.
- All workflow actions are SHA-pinned; no secret exposure found.
- Release/plugin versions agree at 2.2.0.
- Built wheel contains runtime YAML and excludes verified Vale test styles as designed.

