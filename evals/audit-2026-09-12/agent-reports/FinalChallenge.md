Claim: The change set is presented as a selective policy correction with sound measurements, a low-false-positive new rule, complete engine routing, and executable steering.
VERDICT: CHALLENGED

## Summary
- The three advertised error counts and the 2.26x -> 4.53x ratio recompute, but the inference does not: durable-vocabulary detections collapse and new summary-closer errors offset model-side removals.
- The new definitional-negation rule fired on all 15 legitimate technical contrasts; the claimed corpus denominator is also wrong (142 generated documents in the runs, not 96 or 143).
- Strict does not enforce tricolon; five headline rules lose relaxed enforcement, and three additional normal-profile demotions are absent from the headline.
- Source starts and named multiline suppression work, but multiline end columns are invalid, `disable-next-line` suppresses a whole paragraph, and code-quoted disable markers still disable linting.
- Weight-zero error categories still fail global error gates; path-scoped Vale disable is ignored; the review skill selects 63 of 64 judgement rules.
- The root README now contains invalid YAML, and a duplicated Python test name silently shadows a broken test body.

## Assumptions-that-fail
| Assumption | Evidence |
|---|---|
| Aggregate error totals demonstrate detector retention | Raw-run recount shows `durable-vocabulary-habits` matches change human 15->3, ai-existing 7->6, gen-unguided 12->1; model errors also gain five `summary-closer-frames` errors (2->7). |
| Zero corpus hits imply low human false-positive risk | The required 15-case technical probe fired 15/15. |
| `disable-next-line` still means one source line | The annotation suppressed findings on both lines of a two-line paragraph. |
| Weight zero removes a category from document gates | A weight-zero `prose-inflation.intensifier` error still caused `1 error(s), limit 0`. |
| Genre filtering produces a bounded review | `consumer` selects 63/64 judgement rules, including a `scope=prose` rule the procedure never routes. |

## Alternatives
| Rank | Alternative conclusion | Evidence |
|---:|---|---|
| 1 | This is a broad policy-and-detector rewrite, not only demotion of noisy enforcement. | 35 normal-profile rules changed; durable/auxiliary detectors were narrowed, three rules were retired, new error-producing lexicons were added, and relaxed/strict tiers changed. |
| 2 | The new definitional rule is a generic technical contrast detector whose warning requires human triage. | 15/15 legitimate contrasts and 10/10 tell-shaped controls fired. |
| 3 | The engine fixes start coordinates while leaving suppression and range contracts internally inconsistent. | Exact start slices pass; nine findings in one README have `end_column` beyond the reported source line, and next-line/code-marker probes fail. |

## Verdicts

### 1. Normal-profile rule demotions and headline measurements
- verdict: REJECT
- counter-evidence:
  - Independent command: `python3` flattened `runs/{baseline,new}__{human,ai-existing}__normal.json` and counted `severity == "error"`. Output: human `132 -> 64`; ai-existing `139 -> 135`; both equal each file's summary. The density calculation `(139/9865)/(132/21208)` is `2.2648` and `(135/9865)/(64/21208)` is `4.5345`, so the advertised counts and rounded ratios are correct.
  - The same raw-run composition command reported: human `durable-vocabulary-habits 15->3`, `passive-voice 239->244`; ai-existing `durable 7->6`, `passive 48->52`; gen-unguided `durable 12->1`, `passive 356->368`. This is detector loss for a named headline rule, not only a policy/profile change.
  - Ai-existing error composition changed by `durable -1`, `prose-block -2`, `unsupported-evaluative -6`, and `summary-closer-frames +5`. Therefore the small net drop of four hides a nine-error removal offset by five new errors.
  - `evals/audit-2026-09-12/REPORT.md:189-252` itself discloses the durable narrowing, auxiliary-stacking collapse, and new summary-closer phrases; the headline overstates that underlying evidence.
  - Most tier demotions resolve to suggestions, not warnings (`REPORT.md:189-224`). Only the explicit profile default for `orwell.compound-preposition` resolves to warning.
- required change: Rewrite the claim as a composition-aware result. Separate severity-only changes from detector pattern/allowlist changes and show per-rule matched-count and error-severity deltas. Do not use the net model total as evidence of retention.
- risk if shipped as is: Reviewers may approve lost model coverage and new error detectors under the false impression that only false-positive policy changed.

### 2. `ai-tells-structure.definitional-negation-pair`
- verdict: REJECT
- counter-evidence:
  - Raw JSON recount found human 0, slopvacced 0, ai-existing 1, gen-unguided 4, gen-steered-current 0, gen-steered-new 0. The generated run files contain `48+47+47 = 142` documents; the corpus directories also contain 142 generated Markdown files. The headline's 96 and `REPORT.md`'s 143 are unsupported.
  - Word denominators mix definitions: the run summary reports 21,208 parsed human words, while whitespace splitting the same 11 source documents gives 27,157. The zero count is stable, but “27k” is not the denominator used in the density ratio.
  - Command for both probe files: `uv run slopvac lint /tmp/slopvac-{legitimate,tell}-defneg.md --profile normal --format json --config /dev/null`. Vale was on (`unchecked=[]`). Legitimate result: exit 1, 15 definitional hits out of 15. Every firing, verbatim:
    1. `The endpoint is a compatibility alias. It is not a stable API.`
    2. `The file is a cache. It is not the source of truth.`
    3. `The process is a child of systemd. It is not a member of the service cgroup.`
    4. `This is an authorization check. It is not an authentication step.`
    5. `The token is a bearer credential. It is not a user session.`
    6. `The lock is a lease. It is not a mutex.`
    7. `The value is a byte count. It is not the number of characters.`
    8. `The response is an acknowledgement. It is not a guarantee that the operation completed.`
    9. `The replica is a recovery target. It is not a failover source.`
    10. `The checksum is an integrity signal. It is not an authenticity proof.`
    11. `The flag is a process-wide setting. It is not a per-request option.`
    12. `The route is an internal endpoint. It is not a public contract.`
    13. `The timeout is a client budget. It is not a server deadline.`
    14. `The cache isn't a copy of the database; it's an index over immutable records.`
    15. `The operation isn't a retry; it's a new transaction with a new idempotency key.`
  - Tell-shaped control result: exit 1, 10/10 fired. Tell-shaped pairs that did **not** fire: none.
  - The ten published adversarial corrections avoid the rule's semantic danger by using property negations such as “not configurable”; they do not test legitimate definitional contrasts of the exact accepted shape. `TellsCoverage.md:30-31` originally called for a `factual-correction` exception, but the shipped rule keeps only `quotation`.
- required change: Do not ship this as a normal-profile mechanical rule on this evidence. At minimum, add representative definitional factual corrections to the evaluation, restore an operable exception contract, and require a discriminating signal beyond an article/about marker.
- risk if shipped as is: Correct API, security, type, lifecycle, and scope distinctions become warnings and can fail density/maximum-warning gates.

### 3. Decommissioned rules and profile integrity
- verdict: ACCEPT-MODIFIED
- counter-evidence:
  - The removals/exclusion exist, but the profile boundary changed more broadly than stated. Command: `uv run slopvac rules --profile {strict,normal,relaxed} --format json` in the new package, with the relaxed command repeated in `/tmp/slopvac-baseline/packages/slopvac-lint`.
  - `E/A/X` below mean enforced/advisory/excluded. Every named demotion was checked:

| Rule | new strict | relaxed baseline -> new |
|---|:---:|:---:|
| passive-voice | E | A->A |
| first-person-plural | E | E->E |
| future-tense | E | E->E |
| omitted-word-or-contraction | E | E->E |
| multiword-noun-too-long | E | A->A |
| condition-after-command | E | E->E |
| complex-tense | E | A->A |
| nominalized-action | E | A->A |
| latinisms | E | A->A |
| politeness | E | A->A |
| self-reference | E | A->A |
| unclear-antecedent | E | A->A |
| versions | E | E->A |
| directional-ref | E | E->A |
| spacing | E | E->A |
| prose-block | E | A->A |
| exclusive | E | E->A |
| durable-vocabulary-habits | E | A->X |
| tricolon-abuse-core | **A** | A->A |
| compound-preposition | E | A->A |

  - Strict therefore does not enforce tricolon. Relaxed loses enforcement for versions, directional-ref, spacing, and exclusive, and loses durable from advisory to excluded.
  - Additional normal changes omitted from the headline: `ste-verbs.auxiliary-stacking` E->A; `ste-practices.unclear-demonstrative-this` E->X; `ste-practices.unclear-pronoun` A->X. The demonstrative rule also changes relaxed A->X.
  - `prose-craft.command-prompt` changes relaxed E->X as well as normal E->X; strict remains advisory.
- required change: Disclose and justify all strict/relaxed changes, or restore prior non-normal tiers. Correct the claim that strict preserves all named enforcement.
- risk if shipped as is: Users selecting strict or relaxed receive an unmeasured policy change unrelated to the advertised normal-profile audit.

### 4a. True source starts and multiline named suppression
- verdict: ACCEPT-MODIFIED
- counter-evidence:
  - Command: `uv run slopvac lint ../../evals/audit-2026-09-12/corpus/human/black-readme-2021.md --profile normal --format json --config /dev/null`. `ai-tells-structure.tricolon-abuse-core` reported line 20, column 72; the source slice is exactly `speed,`. `ste-procedural.condition-after-command` reported line 24, column 73; the source slice is exactly `Formatting`.
  - Control command on `/tmp/slopvac-multiline-control.md` reported `orwell.stale-figure` on the third paragraph line (source line 3). Adding `<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->` immediately before the paragraph produced zero stale-figure and zero invalid-suppression findings (`unchecked=[]`).
  - However, the same README command found nine findings whose `end_column` exceeds `len(reported line)+1`; examples include tricolon line 20 column 72 end 108 on a 77-character line, and condition-after-command line 24 column 73 end 134 on a 77-character line. The JSON/SARIF model has no `end_line`, so these are invalid ranges.
- required change: Preserve the start-coordinate fix, but represent multiline end positions with `end_line` plus line-relative `end_column`, or cap ranges to the first source line and bump/document the output contract as needed.
- risk if shipped as is: Editors and SARIF consumers can reject or mis-highlight multiline findings even though their start is correct.

### 4b. Suppression contract
- verdict: REJECT
- counter-evidence:
  - Command on a multiline inline code span containing `<!-- slopvac-allow: rule=<id> reason=<name> -->` reported `meta.invalid-suppression` at line 2. `_inside_code_span` only scans delimiters on the current physical line (`suppression.py:98-114`), despite the added comment claiming a span may close on a later line.
  - Command on ``Use `<!-- slopvac-disable -->` to disable a region.`` followed by a stale-figure paragraph returned zero findings. Disable markers are processed before the new inline-code guard, so a quoted documentation example disables the remainder of the file.
  - Control with stale figures on adjacent paragraph lines reported hits on lines 1 and 2. Prefixing `<!-- slopvac-disable-next-line -->` reported no hits on either line: `_expand_block_targets` expands the next physical line to the entire parsed block (`suppression.py:367-376`).
- required change: Parse all suppression directives against Markdown code-span tokens, including multiline spans, before changing state. Expand named block annotations only; keep `disable-next-line` scoped to one physical line, or rename and document a breaking directive.
- risk if shipped as is: Documentation examples can silently disable linting, and a one-line exception becomes a paragraph-wide bypass.

### 4c. Vale disable, override, and exit semantics
- verdict: ACCEPT-MODIFIED
- counter-evidence:
  - Global config command with `[vale] enabled=false`: `uv run slopvac lint /tmp/slopvac-vale-global.md --config /tmp/slopvac-vale-global.toml --format json` exits 2, marks the document failed, and reports unchecked coverage. This part works.
  - The unchecked reason falsely says `--no-vale skipped the Vale engine` even though the cause was configuration.
  - A path override `[[overrides]] files=["*.md"] [overrides.vale] enabled=false` is resolved as false by `--explain-config`, but the corresponding lint exits 1 with `unchecked=[]` and emits Vale-owned findings including `orwell.compound-preposition`. `pipeline.py:572-581` checks only top-level `ctx.config.vale.enabled`, then groups only levels/rules, not resolved Vale settings.
- required change: Apply resolved per-path `ValeSettings` when grouping/compiling inputs, and distinguish config disable from `--no-vale` in the unchecked reason.
- risk if shipped as is: Configuration inspection says Vale is off while execution runs it; CI exit behavior depends on whether the same setting is top-level or path-scoped.

### 4d. Weight-zero categories
- verdict: REJECT
- counter-evidence:
  - Command: `uv run slopvac lint /tmp/slopvac-weight0.md --profile normal --config /tmp/slopvac-weight0.toml --format json`, where the config sets `[categories.prose-inflation] weight=0`. Output: exit 1, `passed=false`, and failure reason `1 error(s), limit 0` for a `prose-inflation.intensifier` error.
  - `_failure_reasons` filters active categories only for density (`score.py:119-137`); global error and warning counts still include zero-weight categories (`score.py:87-94`). The added test disables max error/warning gates, so it cannot catch this contradiction.
- required change: Filter max-error and max-warning gate counts to active categories, while retaining raw counts for reporting. Add a behavioral test with a zero-weight error and the normal `max_errors=0` gate.
- risk if shipped as is: Setting a category weight to zero does not actually remove it from document gates.

### 4e. Profile rule defaults and inspection output
- verdict: REJECT
- counter-evidence:
  - Default normal lint reports `orwell.compound-preposition` as warning; an authored `[rules."orwell.compound-preposition"] severity="error"` correctly wins and lint reports error.
  - Yet `uv run slopvac rules --profile normal --format json --config /tmp/slopvac-compound-error.toml` still returns `tier=enforced, severity=warning`. The public inventory ignores the resolved `[rules]` override while the linter applies it.
- required change: Serialize effective resolved disposition in `rules --config`, including authored rule overrides and profile defaults, or explicitly remove `--config` from that command and stop presenting its output as effective policy.
- risk if shipped as is: Reviewers and automation verify one severity while lint enforces another.

### 4f. Compile serialization and aliased Vale ownership
- verdict: ACCEPT-MODIFIED
- counter-evidence:
  - `slopvac compile` writes `aliases` and `vale_version` in `manifest.json`, but its `--format json` stdout serializer (`cli.py:617-623`) omits both. The stdout `vale_rules` therefore contains `prose-craft.latinisms--punct` without its owner mapping.
- required change: Add `aliases` and `vale_version` to compile JSON stdout, or declare stdout a summary and direct machine consumers to the manifest.
- risk if shipped as is: A consumer auditing stdout sees an apparent unregistered rule and cannot reproduce the cache/version decision.

### 5. Vale routing completeness
- verdict: ACCEPT
- counter-evidence:
  - Commands compiled baseline and new packages to `/tmp/slopvac-compile-{baseline,new}` with `uv run slopvac compile --outdir ... --profile normal --config /dev/null --format json`.
  - Manifest counts changed from Vale/native/judgement/disabled `141/21/67/2` to `137/26/64/2`.
  - Rules moved Vale -> native: `ai-tells-structure.staccato-rhythm`, `prose-craft.dead-opener`, `prose-craft.politeness`, `prose-craft.spacing`, `prose-craft.weasel-term-density`. No rule moved native -> Vale.
  - Inventory against `slopvac rules` found 165 non-judgement rules, `missing=[]`, `multi=[]`. The only extra engine id is the intentional alias `prose-craft.latinisms--punct`, mapped in the manifest.
- risk if shipped as is: No routing loss found.

### 6. Review-docs step 4 and judgement selection
- verdict: REJECT
- counter-evidence:
  - Literal commands against the named README: `uv run slopvac lint .../readme-ratelimit__anthropic-haiku45.md --profile normal --format json --config /dev/null` returned 44 findings on 34 distinct lines; `uv run slopvac rules --judgement --format json` returned 64 judgement rules.
  - Filtering each rule through its category's `recommended_for` selected **63** rules for `consumer`: 17 document, 24 paragraph, 21 sentence, and 1 prose; 18 categories contribute.
  - The procedure is not executable in one unambiguous pass. It gives routing only for document/paragraph/sentence, not the selected `scope=prose` rule; it does not define whether 34 flagged lines mean lines, sentences, or containing paragraphs as “passages”; and it requires the longest paragraph plus a withheld section to be chosen during the same process that says selection happens before reading.
- required change: Set a hard question budget and deterministic passage unit, define `prose` routing, and materially narrow `recommended_for`. Emit the selected plan directly from a command instead of requiring a join over two JSON collections.
- risk if shipped as is: The “filter” is effectively the whole catalogue, producing inconsistent, non-repeatable reviews and excessive context cost.

### 7. Steering measurement claim
- verdict: INSUFFICIENT-EVIDENCE
- counter-evidence:
  - Raw new-run recount confirms semicolon findings `35 -> 14` across 18,428 -> 17,920 parsed words. `REPORT.md:122-153` also says there was one generation per cell and differences under one finding/100 words are noise.
  - The two arms changed the full skill text; no arm isolated the compression guard and there were no repeated controls. The count supports association, not “the guard cut” or “confirms the semicolon half.”
  - The reported omitted-`that` `59 -> 61` comes from a separate counter in `REPORT.md`, not `ste-sentences.omitted-word-or-contraction` (the raw rule count is 0->1), so the metric provenance must stay explicit.
- required change: Use causal wording only after a guard-only repeated A/B; otherwise report the matched-arm association and the one-sample limitation.
- risk if shipped as is: Steering policy may be credited to the wrong text change and retained without reproducible evidence.

### Packaging: root README GitHub YAML
- verdict: REJECT
- counter-evidence:
  - The diff changes two workflow snippets to `* rev: v3` and `*- uses: ...`. Parsing every root-README `yaml` fence with `yaml.safe_load` produced `ScannerError` for both changed blocks (`README.md:208-217`).
- required change: Restore valid `rev: v3` and `- uses:` YAML.
- risk if shipped as is: Users copying the documented workflow receive syntactically invalid YAML.

### Test hunk: duplicate `test_html_format_renders_unchecked_before_score`
- verdict: REJECT
- counter-evidence:
  - `packages/slopvac-lint/tests/test_cli.py:557-577` defines the same test name twice. The first body references undefined `payload`; Python replaces it with the second definition before pytest collection, so the broken body is silently dead rather than tested.
- required change: Remove the shadowed definition and retain one complete behavioral test.
- risk if shipped as is: The suite appears to contain coverage that collection silently discarded.

## Regressions found (things that got worse and were not disclosed)
1. Root README workflow YAML is invalid (`README.md:208-217`; two `ScannerError`s).
2. `slopvac-disable-next-line` now suppresses later lines in the same paragraph.
3. Code-quoted disable markers still alter suppression state; multiline code-quoted allow examples are reported as malformed.
4. `rules --config` reports a different effective severity from `lint` for authored overrides.
5. Strict tricolon enforcement and relaxed enforcement for four headline rules were removed; durable and unclear-demonstrative coverage also drop out of relaxed.
6. A duplicated test function shadows a broken body.

## Missed (defects in the diff the change set did not address)
1. Per-path `[overrides.vale] enabled=false` is visible in `--explain-config` but ignored during lint execution.
2. Weight-zero categories remain active in global max-error/max-warning gates.
3. Multiline findings still have impossible end columns and no end line in JSON/SARIF.
4. Compile stdout omits newly material ownership/version fields that are present in the manifest.
5. The definitional rule's factual-correction problem was known (`TellsCoverage.md:30-31`, `ChallengeSteering.md:134-137`) but the shipped rule lacks that exception and the new probe matrix does not exercise same-shape legitimate contrasts.
