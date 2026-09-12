## Summary
The audit found many real defects, but overstates the README contract for per-target config, misclassifies a deliberate fast fixture check, and proposes an unbounded registry rewrite.
CodeVale F4 does not reproduce: Vale fired the soft-break rule at 1:1-16; compile routed it to Vale and `--no-vale` omitted it.
The largest missed defect is `[vale] enabled=false`: 145 Vale-owned rules are silently skipped while the run exits 0 with `passed=true, unchecked=[]`.
Vale should be retained now for POS-sensitive blocklists; removal is a separate migration, not cleanup.
Small local fixes belong together; source mapping, STE tokenization, scope routing, per-target config, RST, and Vale removal need isolated PRs.

## Reproduction checks

All inputs were under `/tmp`; commands used `/tmp/slopvac-baseline/packages/slopvac-lint`.

- **CodeEngine:** normal JSON lint of `Use ``a` — b`` safely now.` reproduced `ai-tells-formatting.em-dash-density` despite the dash being inside valid double-backtick code. Exit 1, three findings.
- **CodePipeline:** normal JSON lint of a one-sentence `.rst` exited 2 with `E100 [lintRST] ... rst2html not found` and an unchecked note.
- **CodeVale:** normal JSON lint of `What is the TTL?\nIt is 60 seconds.` exited 0 and **did** report `ai-tells-structure.rhetorical-question-transition` at line 1, column 1, exclusive end 16. `slopvac compile` put it in `vale`; the `--no-vale` control omitted it. F4 could not be reproduced.
- **CodeTestsCi:** one warm shipped CLI run took 1.031 s; in-process `load_ruleset()` took 0.287 s for 232 rules (fresh process total 0.500 s). A fresh CLI per example would cost roughly a second each, unlike the loader check.

## Verdicts

### CodeEngine.F1: preserve multiline source coordinates
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `analyze.py:334-336,516-526` flattens soft breaks; `engine.py:642-698` uses that projected line for location and suppression. `suppression.py:26-48,148-165` targets and matches exact physical lines. Without annotations a span-map-only repair need not change counts; with an annotation on the true later line it **can change counts**, because the suppression finally matches. SARIF positions also change.
- risk if applied as proposed: broad mapping changes can alter suppression and quotation filtering, not merely display positions.

### CodeEngine.F2: implement documented STE tokenization
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `docs/metrics.md:21-145` explicitly requires ordered phases 0-9 and collapse-before-split; the audit probes violate that contract.
- risk if applied as proposed: FP/FN threshold shifts require corpus rebaselining.

### CodeEngine.F3: project visible HTML/MDX prose
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `.mdx` and `.html` are declared lintable at `pipeline.py:28-30`, but the walker at `analyze.py:467-510` has no HTML/JSX projection.
- risk if applied as proposed: FP increase unless script/style/attributes/expressions are excluded.

### CodeEngine.F4: mask every CommonMark code-span delimiter
- verdict: ACCEPT
- classification: real bug
- counter-evidence: reproduced above; `analyze.py:190-208` reparses with a single-backtick regex instead of markdown-it tokens.
- risk if applied as proposed: none after metric rebaseline.

### CodeEngine.F5: route native lexical rules by declared scope
- verdict: ACCEPT-MODIFIED
- classification: real bug
- counter-evidence: `engine.py:642-650` collapses all non-raw/non-heading scopes. Inventory from `load_ruleset()` found 15 lexical sentence rules, 5 paragraph rules, 0 document rules, and 109 prose rules. Correct sentence routing changes all 15 by enabling sentence anchors and preventing cross-sentence matches. Paragraph rules already see a flattened block in the common case, but currently also receive headings, list items, and table cells.
- modification: add typed span iterators, then review all 20 non-prose lexical rules by intent. Preserve cross-sentence matching for paragraph rules. A proposed definitional-negation detector comparing sentences must declare `paragraph`; declaring `sentence` and relying on the present bug would make the routing fix a regression.
- risk if applied as proposed: FN increase for intentional cross-sentence patterns assigned the wrong scope.

### CodeEngine.F6: report malformed suppression-like comments
- verdict: ACCEPT-MODIFIED
- classification: design choice
- counter-evidence: README `Suppress a finding` promises that a recognized annotation with an off-list reason is reported; it does not promise that every comment containing `slopvac-allow` is parsed. `suppression.py:18-21` defines a closed grammar. Silent non-suppression is defensible.
- modification: if added, detect only the exact comment prefix and keep malformed comments non-suppressing; describe this as usability hardening, not contract repair.
- risk if applied as proposed: FP increase on documentation examples.

### CodeEngine.F7: bind allowlist phrases to the matched occurrence
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `engine.py:671-678` suppresses when a multiword allowlist entry appears anywhere within ±30 characters, although its comment says the phrase contains the match. This can suppress a different occurrence.
- risk if applied as proposed: none.

### CodeEngine.F8: make weight-zero categories informational in all gates
- verdict: ACCEPT
- classification: real bug
- counter-evidence: README `Scoring` says weight zero contributes to neither side; `score.py:142-167,190-230,273-277` includes it in whole-document score/density gates.
- risk if applied as proposed: none; intended gates become less strict.

### CodeEngine.F9: use one denominator everywhere
- verdict: INSUFFICIENT-EVIDENCE
- classification: design choice
- counter-evidence: `docs/metrics.md:21-145` defines the special collapsed token universe for `sentence_words`; it does not say hedge/bold/dash lexical densities use that universe. README uses generic “words” but does not resolve the ambiguity. Thresholds may have been calibrated against `_prose_words`.
- risk if applied as proposed: FP/FN changes at every document-metric threshold.

### CodeEngine.F10: replace dispatch with registries
- verdict: REJECT
- classification: design choice
- counter-evidence: the audit measured 1.168 s for the human corpus and found no unimplemented shipped metric. The proposal touches at least six modules without a demonstrated user defect.
- risk if applied as proposed: large regression surface for no contract gain.

### CodePipeline.F1: discover config per target
- verdict: ACCEPT-MODIFIED
- classification: real bug
- counter-evidence: README does **not** promise this (search for nearest/walking/config discovery found none). Public CLI help does: `cli.py:105-111`; `config.py:1-19` repeats it. `pipeline.py:451-453` loads only `targets[0]`. A correct implementation must discover/cache configs per file, apply exclusions relative to each root, and group compile inputs. Naive cost is O(files × ancestors); caching by parent/config path makes it near O(directories).
- modification: cite the CLI/docstring contract, retain `--config` as explicit single-config mode, and avoid claiming README support.
- risk if applied as proposed: more compile trees and changed exclusion semantics.

### CodePipeline.F2: preserve omitted fields in override patches
- verdict: ACCEPT
- classification: real bug
- counter-evidence: README `Configuration` says layers patch per field; concrete defaults in `config.py:149-226` are merged as authored values at `625-650`.
- risk if applied as proposed: none.

### CodePipeline.F3: apply CLI overrides last
- verdict: ACCEPT
- classification: real bug
- counter-evidence: CLI calls `--profile` an override (`cli.py:92-96`), but `load_run_context` mutates top-level config at `pipeline.py:451-475` before `resolve_for` applies file overrides.
- risk if applied as proposed: none.

### CodePipeline.F4: preserve suggestion severity externally
- verdict: ACCEPT
- classification: real bug
- counter-evidence: README `Scoring` says suggestions are advisory; `pipeline.py:428-435` maps every non-error GitHub annotation to warning, and `report.py:259-260,322-351` does likewise for SARIF.
- risk if applied as proposed: none.

### CodePipeline.F5: normalize SARIF end columns
- verdict: ACCEPT
- classification: real bug
- counter-evidence: same defect as CodeVale.F2; `vale.py:207-217` copies inclusive Vale end while native uses exclusive `match.end()+1`.
- risk if applied as proposed: none.

### CodePipeline.F6: declare or remove the RST converter dependency
- verdict: ACCEPT
- classification: real bug
- counter-evidence: reproduced above; `.rst` is accepted at `pipeline.py:28-30`, but `pyproject.toml:20-34` does not provide `rst2html`.
- risk if applied as proposed: removing `.rst` breaks existing users; handle in a compatibility PR.

### CodePipeline.F7: repair init examples
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `templates.py:96-101,132-150` recommends unsupported `enabled=false`; config models forbid it.
- risk if applied as proposed: none.

### CodePipeline.F8: reject vocabulary unknowns and duplicates
- verdict: ACCEPT
- classification: real bug
- counter-evidence: README `Word blocklist` defines the record shape and requires an editorial reason; `vocabulary.py:218-286` accepts misspelled fields and silently overwrites duplicate `(word,pos)` records.
- risk if applied as proposed: intentionally duplicated existing lists will become config errors, which is preferable to silent loss.

### CodePipeline.F9: lazy imports before parallelism
- verdict: INSUFFICIENT-EVIDENCE
- classification: nit
- counter-evidence: 0.42 s import and 4.303 s for 500k words do not violate a documented latency budget.
- risk if applied as proposed: import-graph churn.

### CodeVale.F1: preserve concrete substitution replacements
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `compile_vale.py:534-586` decides fallback from regex source’s last character and replaces the fix with “a simpler word”; this defeats the substitution rule’s actionable replacement.
- risk if applied as proposed: none with five-rule parity probes.

### CodeVale.F2: convert Vale inclusive ends
- verdict: ACCEPT
- classification: real bug
- counter-evidence: `vale.py:207-217` conflicts with native `engine.py:697-698` and SARIF exclusive ends.
- risk if applied as proposed: none.

### CodeVale.F3: enforce Vale >=3.15 and key the cache
- verdict: ACCEPT
- classification: real bug
- counter-evidence: install docs state Vale 3.15 or later; `vale_probe.py:77-113` never checks version and `vale_cache.py:106-144` omits it despite README’s “nothing is ever served stale” promise.
- risk if applied as proposed: cache churn; key semantic version, adding resolved binary identity only if necessary.

### CodeVale.F4: keep source-line anchored patterns native
- verdict: REJECT
- classification: not a present bug on the frozen baseline
- counter-evidence: exact soft-break probe fired through Vale at 1:1-16; compile routed it to Vale and `--no-vale` omitted it.
- risk if applied as proposed: FN increase by moving a working rule to a different parser.

### CodeVale.F5: remove stale upstream-style claims
- verdict: ACCEPT
- classification: nit/documentation defect
- counter-evidence: compile manifest has no upstream `ai-tells.*`; comments claiming those styles remain enabled are false.
- risk if applied as proposed: none.

### CodeTestsCi.F1: run every example through shipped execution
- verdict: ACCEPT-MODIFIED
- classification: design choice with complementary coverage gap
- counter-evidence: README `Rules` promises exactly the current fast check: compile each regex; bad matches, good does not. `rules.py:97-141` implements it. Requiring every good example to be clean under the whole ruleset wrongly couples independent rules. Measured one shipped CLI run at 1.031 s versus 0.287 s in-process loader verification.
- modification: keep `_verify_examples`; add batched per-rule integration oracles proving bad examples emit their own id at declared scope, plus targeted allowlist/exception cases. Never require good examples to avoid unrelated ids.
- risk if applied as proposed: test-time explosion and cross-rule fixture coupling.

### CodeTestsCi.F2: fix locale false-green rows
- verdict: ACCEPT
- classification: real test bug
- counter-evidence: `test_cli.py:232-251` does not read `should_find` and always uses `--no-vale`.
- risk if applied as proposed: none.

### CodeTestsCi.F3: add composite-action contract harness
- verdict: ACCEPT
- classification: real coverage gap, not a product defect
- counter-evidence: action branches at `action.yml:107-368` lack a harness; dogfood at `lint.yml:255-281` covers one path.
- risk if applied as proposed: CI maintenance cost; keep cases boundary-focused.

### CodeTestsCi.F4: update README version pins
- verdict: ACCEPT
- classification: real documentation bug
- counter-evidence: README pins v2.0.0 while package/hook manifests are 2.2.0.
- risk if applied as proposed: none.

### CodeTestsCi.F5: replace pinned tests broadly
- verdict: ACCEPT-MODIFIED
- classification: design choice
- counter-evidence: the top-10 mixes real false-greens with compiler representation invariants. Delete only tests superseded by stronger boundary tests.
- modification: locale test = real bug; report-model self-roundtrip/direct model requiredness/enum tests = nits; reference exact-fragment test and private all-caps matrix = redundant nits once boundary coverage exists; Vale raw-list/nonword/vocabulary grouping tests = defensible compiler invariants; plugin marketplace schema/layout = defensible public integration boundary.
- risk if applied as proposed: test-suite FN increase if Vale representation guards are removed.

## Missed by the audit

### M1 (`pipeline.py`): config-disabled Vale silently passes an incomplete run
- evidence: `run_lint` skips Vale when `config.vale.enabled` is false, removes all Vale-owned rules from `native_only`, but only calls `unchecked_for_skipped` for `--no-vale` (`pipeline.py:583-620`). Probe with `[vale] enabled=false` and obvious lexical violations exited 0 with zero findings, `passed=true`, `unchecked=[]`.
- classification: real bug; highest priority. Treat it like `--no-vale` for accounting/exit 2, or remove the setting.

### M2 (`engine.py`): lexical rules ignore `text_type`
- evidence: `_run_lexical` at `engine.py:652-702` never checks `rule.text_type`; `compile_vale.py:625-633` guards only text-type-aware metrics. Sentence/paragraph lexical rules declare procedural/descriptive/any, so schema intent is ignored in both routes.
- classification: real bug. Fix with scope routing and cross-engine parity.

### M3 (`engine.py`): Vale quotation/code filtering chooses the first duplicate
- evidence: `drop_quoted_illustrations` uses `line.find(finding.matched_text)` and ignores `finding.column` (`engine.py:176-203`). If the same phrase occurs twice and only one occurrence is quoted/code, the wrong occurrence governs filtering.
- classification: real bug. Use normalized source spans.

### M4 (`pipeline.py`): per-file locale overrides never generate per-file spelling rules
- evidence: `load_run_context` injects one locale rule from top-level config at `pipeline.py:477-487` before any `resolve_for`; grouping at `544-565` omits locale-generated rule identity.
- classification: real bug.

### M5 (`pipeline.py`): per-file Vale enabled/binary overrides are ignored
- evidence: `_compile_for` and `run_lint` use top-level `config.vale.binary/enabled` at `pipeline.py:583-599`; resolved config affects levels only. Override provenance can claim a change that never controls execution.
- classification: real bug.

## Vale cost/benefit

Compile output: 145 Vale rules, 21 native, 67 judgement. Vale’s only unique shipped semantic is POS-tagged `sequence` matching for a configured `ste-words` blocklist. The locale/spelling check is a generated substitution and is native-capable. Vale also supplies markup scoping and Tengo, but every current metric/structure rule has a native implementation.

**Call: retain Vale now.** Default config has no uniquely Vale-owned rule id, and compiler/runner/cache code plus ~1.03 s warm smoke time are real costs. But configured blocklists need POS semantics, native scope/text-type parity is currently broken, and removing Vale would rebaseline 145 lexical rules. Reconsider only in a separate PR after replacing POS matching and proving native parity across corpora.

## Ranked fix in this PR

1. Config-disabled Vale must report unchecked/exit 2 (M1): `pipeline.py` + targeted tests; 1-2 source files.
2. Vale exclusive end columns (CodeVale F2/CodePipeline F5): `vale.py` + tests; 1 source file.
3. Preserve Vale substitutions (CodeVale F1): `compile_vale.py` + tests; 1 source file.
4. Make CLI patches last and omitted override fields truly omitted (Pipeline F2/F3): `config.py`, `pipeline.py` + tests; 2-3 files.
5. Exact allowlist spans (Engine F7): `engine.py` + tests; 1 file.
6. Exclude weight-zero from all gates (Engine F8): `score.py` and caller tests; 1-2 files.
7. GitHub/SARIF suggestion levels (Pipeline F4): `pipeline.py`, `report.py` + tests; 2 files.
8. CommonMark code masking (Engine F4): `analyze.py`, `metrics.py` + tests; 2-3 files.
9. Repair init examples and public version pins (Pipeline F7, Tests F4): template/README/release parity; 2-4 files.
10. Validate vocabulary records (Pipeline F8): `vocabulary.py` + tests; 1 file.
11. Fix dead locale test rows and stale upstream comments: tests/docs only.

## Separate PRs

1. Source spans plus HTML/MDX projection (Engine F1/F3): `analyze.py`, `engine.py`, report adapters/tests; 3-4 source files.
2. STE tokenizer/segmenter (Engine F2): `analyze.py`, `metrics.py`, `compile_vale.py`, docs/tests; 3-4 files plus threshold rebaseline.
3. Scope and text-type routing (Engine F5 + M2): `analyze.py`, `engine.py`, `compile_vale.py`, tests; 3-4 files and 20 lexical rules to review.
4. Per-target config discovery (Pipeline F1): RunContext, collection, grouping, explain-config; 4-6 source files.
5. Vale version/cache identity (Vale F3): probe/cache/compiler/tests; 3-4 files.
6. RST packaging/compatibility (Pipeline F6): choose dependency extra versus removal with compatibility data; 3-4 files.
7. Define/recalibrate metric denominators before changing Engine F9.
8. Vale removal evaluation: replace POS semantics and prove 145-rule/corpus parity before cutover.
9. Composite-action harness (Tests F3): action/workflow fixtures; separate CI PR.

## Systemic concerns

- The reports sometimes infer a contract from implementation (`LINTABLE`, model fields) and then call the implementation’s behavior a contract breach; public docs/help must be cited precisely.
- One failed CodeVale reproduction shows that cache/binary/version/input details were not captured tightly enough. Reproduction reports should include exact Vale version, cache directory, emitted rule routing, and control arm.
- Proposed count-changing parser/tokenizer fixes are not safe to combine with rule tuning: location, suppression, scope, and threshold effects need separate baselines.
- “Run every good example through the whole ruleset” creates selection coupling: a fixture can be a correct fix for its own rule while legitimately violating another.
