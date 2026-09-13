## Summary
Checked the baseline CLI, config cascade, target discovery, report formats, reference generation, locale patches, vocabulary loading, large inputs, and import cost.
The three highest-impact defects are: only the first target's config is discovered; partial threshold/locale overrides reset fields the user did not set; CLI thresholds lose to matching file overrides.
Machine integrations also promote suggestions to warnings, Vale end columns use the wrong SARIF convention, and `.rst` is unusable without an undeclared `rst2html` executable.
The generated starter config contains invalid examples and contradicts the implemented category-severity contract.
HTML escaping, JSON schema versioning, validation, traversal/excludes, reference checking, and exit codes passed their probes.

## Findings

### F1: Discover configuration for every target, not only the first
- surface: `src/slopvac/pipeline.py:451-453`; `src/slopvac/config.py:1-19`; `src/slopvac/cli.py:105-111`
- kind: defect
- evidence: The CLI says `Default: nearest slopvac.toml walking up from each target`, and `config.py` makes the same claim. The implementation instead does `first = Path(targets[0])` and loads one config. `uv run --project /tmp/slopvac-baseline/packages/slopvac-lint slopvac lint --explain-config /tmp/slopvac-audit-codepipeline/tree/docs/nested/clean.md /tmp/slopvac-audit-codepipeline/other/other.md` printed `clean.md profile: relaxed` and `other.md profile: normal`, although `other/slopvac.toml` says strict/min_score 99. Reversing target order made both strict/min_score 99. Expected each file to use its own nearest config independent of argument order.
- proposal: Discover/load config per collected path and group compilation by `(config root, resolved compile inputs, vocabulary fingerprint)`. Keep rules shared and retain `--config` as the explicit single-config path. Blast radius: `RunContext`, `load_run_context`, exclusion application, `group_inputs`, `lint_one`, `_print_resolved_config`; reports unchanged.
- expected effect: correctness for multi-package/monorepo runs
- confidence: high

### F2: Use patch models whose omitted fields remain omitted
- surface: `src/slopvac/config.py:149-180`, `src/slopvac/config.py:185-226`, `src/slopvac/config.py:625-650`
- kind: defect
- evidence: README promises per-field patches. `Thresholds.max_errors` defaults to 0, `LocaleSettings.default` to en-US, and `ValeSettings.enabled/binary` have concrete defaults, yet these models are reused inside `Override`. A top-level `max_errors = 5` plus matching override containing only `min_score = 12` resolved as `{'max_total_per_100_words': 3.0, 'max_errors': 0, 'min_score': 12.0}`; expected max_errors 5. A top-level en-GB locale plus override containing only `allow = ["othername"]` resolved as `{'default': 'en-US', 'allow': ['othername']}`; expected en-GB to survive.
- proposal: Add internal `ThresholdPatch`, `LocalePatch`, and `ValePatch` models with all fields defaulting to None; merge only `model_fields_set`, which also permits explicit empty lists. Keep concrete models for resolved config. Blast radius: config declarations/merge functions and config tests; callers unchanged.
- expected effect: correctness for every partial threshold, locale, or Vale override
- confidence: high

### F3: Apply command-line overrides after per-file overrides
- surface: `src/slopvac/pipeline.py:458-475`; `src/slopvac/config.py:614-638`
- kind: defect
- evidence: CLI options say they override config. `load_run_context` mutates top-level config, then `resolve_for` folds path overrides over it. `slopvac lint --config .../config-overrides.toml --min-score 77 --max-per-100-words 6 --explain-config .../finding.md` printed max density 6 but min_score 99 because a matching override set min_score. Expected min_score 77. The same ordering defect affects `--profile`, `--locale`, and `--disable` when an override writes the same field; the comment calling disables “the last word” is false.
- proposal: Carry an explicit CLI patch in `RunContext` and apply it to each `ResolvedConfig` after `resolve_for`, before grouping/compile/score; record CLI provenance. Blast radius: pipeline resolution call sites and compile-group keys.
- expected effect: correctness and order-independent CLI behavior
- confidence: high

### F4: Preserve suggestion severity in GitHub and SARIF output
- surface: `src/slopvac/pipeline.py:428-435`; `src/slopvac/report.py:259-260`, `src/slopvac/report.py:322-351`
- kind: defect
- evidence: README says suggestions are advisory. `slopvac lint --format github .../finding.md` emitted `::warning` for `ai-tells-content-shape.adjective-per-noun-spray` and `ai-tells-formatting.em-dash-density`, both suggestions in JSON. SARIF emitted both as `"level": "warning"`. `_sarif_level` maps every non-error to warning and `build_sarif` fails to implement its own comment that suggestions are excluded. Expected GitHub `notice`; SARIF `note` or omission, with omission matching stated policy.
- proposal: Centralize external severity mapping. Emit GitHub suggestions as notice; filter suggestions before SARIF results (or intentionally map to note and update policy). Blast radius: `emit_report`, `build_sarif`, format tests.
- expected effect: correctness; stops advisory findings appearing as CI warnings
- confidence: high

### F5: Convert Vale's inclusive span end to SARIF's exclusive end
- surface: `src/slopvac/vale.py:201-216`; `src/slopvac/report.py:338-349`
- kind: defect
- evidence: Vale `Span[1]` is copied to `Finding.end_column`, then SARIF `endColumn`. The generated SARIF emitted a one-character em dash as startColumn 70/endColumn 70 and `robust` as 6/11. SARIF's schema describes endColumn as the character following the region; expected 71 and 12. Native regex findings already use `match.end() + 1`, so the model mixes conventions by producer.
- proposal: Normalize at the Vale adapter seam with `end_column=span[1] + 1`, and document Finding end columns as one-based exclusive. Blast radius: `vale.py` and position tests.
- expected effect: correctness in code-scanning highlights
- confidence: high

### F6: Declare or disable the RST converter requirement
- surface: `src/slopvac/pipeline.py:28-30`; `pyproject.toml:20-34`
- kind: defect
- evidence: `.rst` is lintable, but no converter is a dependency or documented prerequisite. `slopvac lint --config /dev/null --format json .../probe.rst` exited 2 and recorded `E100 [lintRST] Runtime error ... rst2html not found`. The same sentence in `.txt` exited 0 with no unchecked checks. Expected a default lintable suffix to run completely or be rejected up front with an actionable installation message.
- proposal: Remove `.rst` from LINTABLE until an explicit `rst` extra supplies/checks docutils, or preflight `rst2html` and name the exact dependency. Blast radius: path collection, package extras/docs, suffix smoke tests.
- expected effect: correctness for RST users
- confidence: high

### F7: Fix `slopvac init` examples and category-severity prose
- surface: `src/slopvac/templates.py:96-101`, `src/slopvac/templates.py:132-150`; README lines 146-161
- kind: steering-drift
- evidence: Starter says category severity only lowers; README/model say it promotes and demotes. A category error plus qualified rule warning emitted the dash as warning, confirming rule-over-category set semantics. Starter examples also use nonexistent `enabled = false`. Uncommenting one and running lint exited 2 with `overrides.0.categories.prose-scope.enabled Extra inputs are not permitted`. Expected generated examples to validate.
- proposal: Replace all three `enabled = false` examples with `severity = "off"`; change “cap LOWERS” to set semantics. Blast radius: template and byte snapshot.
- expected effect: correctness for users following generated guidance
- confidence: high

### F8: Reject misspelled and duplicate vocabulary fields
- surface: `src/slopvac/vocabulary.py:218-286`
- kind: defect
- evidence: Blocklist records are untyped dicts. Entry with `replacment = "deployment"` was accepted; lint exited 0, emitted the blocklist finding, and produced `replacement: null`. Expected an unknown-field/did-you-mean error. `entries[(word, pos)] = ...` also silently lets a later duplicate overwrite the earlier editorial reason.
- proposal: Validate records with a small `VocabularyEntryModel(extra="forbid")`; reject duplicate `(word,pos)` with both entry numbers. Preserve frozen runtime Entry. Blast radius: vocabulary loader/tests only.
- expected effect: correctness for controlled vocabulary configuration
- confidence: high

### F9: Reduce eager imports before adding execution parallelism
- surface: `src/slopvac/cli.py`, `src/slopvac/pipeline.py:552-638`, `src/slopvac/__init__.py`
- kind: perf
- evidence: config.py is 27,190 bytes, cli.py 26,952, pipeline.py 25,068. `python -X importtime -c 'import slopvac.cli'` measured 0.42 s wall/316,313 µs cumulative; config was 150,009 µs, pipeline 79,709, analyze 62,436, Rich console 33,443. `run_lint` processes groups and native files sequentially; Vale already batches each group. A 2.8 MB/500,000-word file with only prose-format completed in 4.303 s without crashing.
- proposal: First create a minimal entry module for version/help and lazy-import command implementations. Only after corpus timing justifies it, parallelize native parse/engine work within a compiled group using bounded workers while preserving output order. Do not parallelize cache publication. Blast radius: CLI import graph first; later `run_lint` only.
- expected effect: startup latency first; possible throughput later
- confidence: medium

## Decommission candidates
- Delete the duplicate `minimum_severity` declaration in `CategorySettings` (`config.py:105-114`); it has no runtime benefit.
- Stop using fully defaulted concrete models as override patch models; retain the feature with optional patch models.
- Remove `.rst` from LINTABLE unless the project commits to the runtime converter.
- Remove invalid `enabled = false` examples rather than adding a second disable spelling.

## Checked and fine
- Exit codes: empty file/Vale 0; finding-heavy file 1; `--no-vale` empty file 2 with JSON passed false and unchecked rules.
- `/dev/null` gave normal defaults; omitted config discovered the nearest config for the first target (multi-target defect F1).
- Later matching overrides won: `**/finding.md` then `tree/docs/**/*.md` resolved to the latter relaxed/min_score 12.
- Unknown config keys and misspelled qualified rule ids reject with exit 2; rule typo includes did-you-mean.
- Category/qualified-rule `--disable` removed the dash; `--category prose-format` emitted only that category's finding.
- Directory targets recurse/deduplicate and `**/excluded/**` excluded the probe.
- Empty Markdown and front-matter-only Markdown produced 0 words/0 findings/pass. Plain text ran completely. RST is F6.
- JSON emitted schema_version 1 separately from tool version 2.2.0.
- SARIF emitted schema/version/descriptors/ruleId/levels/fingerprints/locations. ruleIndex is optional when ruleId resolves against driver rules.
- HTML escaped matched `[click <script>alert(1)</script> here](` as `&lt;script&gt;...&lt;/script&gt;`; no injected script appeared.
- `slopvac reference --check --write .../docs/rules.md` exited 0/current.
- Missing rules-dir was rejected by Click with exit 2 and the exact path.
- Locale table generation and vocabulary suffix/top-level/required-field errors are fail-closed; isolated merge/extra-field defects are above.
