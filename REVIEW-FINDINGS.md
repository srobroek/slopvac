# Review disposition: 2026-10-20

Base: `f9dee48` (current main when this branch started). The initial query covered the 35 most recent PRs through #217 and found 67 unresolved threads, including 34 code-review findings. A subsequent paginated query covered all 215 PRs and found 377 unresolved threads. Every PR and thread page was complete. The full linked inventory is in `review-inventory.csv`. Outdated threads were checked against source rather than treated as resolved. No remote review threads were resolved by this patch.

Open PRs and remote branches were checked before editing. The existing checkout was copied into an isolated working branch, preserving its untracked marketplace.json. PR #217 merged as `591c1e0` before this PR was ready to merge. Its supported-Vale checks are preserved here.

The cache exploit does not require an empty ruleset: a model-valid document can selectively remove findings while keeping locale checks complete. The regression tests exercise that case. POSIX ownership/permission checks establish the trust boundary; a checksum detects accidental damage, not authorship. Windows selects LocalAppData as its standard cache location, but this patch deliberately skips ruleset reuse where POSIX trust checks are unavailable. Unsafe compiled-cache roots use transient private output. Existing shared entries are not migrated or repaired.

| Review thread | Disposition | Source or regression evidence |
| --- | --- | --- |
| [#183 / 4164080347](https://github.com/srobroek/slopvac/pull/183#discussion_r4164080347) | Valid; fixed | metrics.md splits the semicolon sentence |
| [#184 / 4171122523](https://github.com/srobroek/slopvac/pull/184#discussion_r4171122523) | Already fixed | PR #185 restored ste-practices.latin-abbreviation including et al. and ibid.; it is intentionally opt-in |
| [#185 / 4171632906](https://github.com/srobroek/slopvac/pull/185#discussion_r4171632906) | Valid; fixed | ste-practices provenance and CHANGELOG say to enable an off category as well as the rule |
| [#185 / 4171632911](https://github.com/srobroek/slopvac/pull/185#discussion_r4171632911) | Already fixed | current pipeline.lint_one filters all Vale findings with engine.is_active in both prose and comment modes |
| [#197 / 4312856754](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856754) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856781](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856781) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856804](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856804) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856816](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856816) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856830](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856830) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856845](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856845) | Unsupported | shows an update notice has a noun object; adding that here is grammatically unsupported. The paragraph is rewritten for the separate condition finding |
| [#197 / 4312856859](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856859) | Unsupported | command only is not a compound modifier in this sentence. The paragraph is rewritten for the separate condition finding |
| [#197 / 4312856875](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856875) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856886](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856886) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856895](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856895) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856906](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856906) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856916](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856916) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#197 / 4312856925](https://github.com/srobroek/slopvac/pull/197#discussion_r4312856925) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#202 / 4323443937](https://github.com/srobroek/slopvac/pull/202#discussion_r4323443937) | Valid; fixed | suppression._comment_text and projected Markdown code blocks; test_fenced_comment_directives_are_inert |
| [#202 / 4323854430](https://github.com/srobroek/slopvac/pull/202#discussion_r4323854430) | Valid; fixed | comment_blocks now accepts nonempty punctuation after removing source delimiters; test_punctuation_comment_is_next_block |
| [#202 / 4323854436](https://github.com/srobroek/slopvac/pull/202#discussion_r4323854436) | Valid; fixed | pathless inspection drops file overrides before resolving the explicit profile; test_explicit_inspection_profile_ignores_file_overrides |
| [#203 / 4323572909](https://github.com/srobroek/slopvac/pull/203#discussion_r4323572909) | Valid; fixed | each measured shell command changes to its own scratch project; test_comparison_alternates_revisions_in_separate_projects |
| [#203 / 4323572920](https://github.com/srobroek/slopvac/pull/203#discussion_r4323572920) | Already fixed | PR #205 passes the resolved py_spy executable to sudo |
| [#203 / 4323572931](https://github.com/srobroek/slopvac/pull/203#discussion_r4323572931) | Valid; fixed | run_profiled prepares cold/warm caches and notifier environment; test_profile_cache_environment and test_notifier_target_really_has_a_terminal |
| [#203 / 4323572941](https://github.com/srobroek/slopvac/pull/203#discussion_r4323572941) | Already fixed | perf.main already prepends the resolved PERF_VALE directory to child PATH |
| [#203 / 4323572945](https://github.com/srobroek/slopvac/pull/203#discussion_r4323572945) | Valid; fixed | terminal_target.py supplies a PTY for benchmark and profiler notifier runs; test_notifier_target_really_has_a_terminal |
| [#203 / 4323572953](https://github.com/srobroek/slopvac/pull/203#discussion_r4323572953) | Already fixed | run_scalene already passes --program-path pointing to the Slopvac source |
| [#203 / 4323853254](https://github.com/srobroek/slopvac/pull/203#discussion_r4323853254) | Valid; fixed | accepted_exits distinguishes lint gates from startup/setup failures; test_hyperfine_wrapper_enforces_scenario_exits |
| [#203 / 4323853264](https://github.com/srobroek/slopvac/pull/203#discussion_r4323853264) | Valid; fixed | one measured sample per revision per round, reversing order; test_comparison_alternates_revisions_in_separate_projects |
| [#203 / 4323853277](https://github.com/srobroek/slopvac/pull/203#discussion_r4323853277) | Valid; fixed | result_dir records git_dirty, binary diff hash, and untracked paths alongside HEAD |
| [#208 / 4326473952](https://github.com/srobroek/slopvac/pull/208#discussion_r4326473952) | Valid; fixed | CHANGELOG 2.12.0 now includes prose-block and its series predicate/100-word threshold |
| [#208 / 4326473966](https://github.com/srobroek/slopvac/pull/208#discussion_r4326473966) | Valid; fixed | CHANGELOG describes the complete latinisms rule as off and names all substitutions |
| [#208 / 4326473979](https://github.com/srobroek/slopvac/pull/208#discussion_r4326473979) | Valid; fixed | CHANGELOG qualifies the restored one-point-dilution question |
| [#208 / 4326473989](https://github.com/srobroek/slopvac/pull/208#discussion_r4326473989) | Valid; fixed | CHANGELOG separates write auto/off from review auto/ask/off, matching GuidanceSettings |
| [#208 / 4326474003](https://github.com/srobroek/slopvac/pull/208#discussion_r4326474003) | Valid; fixed | CHANGELOG scopes --no-skills to init, matching CLI option declarations |
| [#208 / 4326474012](https://github.com/srobroek/slopvac/pull/208#discussion_r4326474012) | Valid; fixed | CHANGELOG includes non-raw HTML-comment filtering, matching drop_hidden_text |
| [#208 / 4326474023](https://github.com/srobroek/slopvac/pull/208#discussion_r4326474023) | Valid; fixed | CHANGELOG says fix when defined, matching rule_block |
| [#211 / 4326671276](https://github.com/srobroek/slopvac/pull/211#discussion_r4326671276) | Valid; fixed | private platform defaults plus path/owner/mode checks and uncached fallback; forged model-valid cache, symlink, permissions and foreign-owner tests |
| [#211 / 4326671285](https://github.com/srobroek/slopvac/pull/211#discussion_r4326671285) | Valid; fixed | content_key includes Python, regex, and YAML runtime identities; test_dependency_versions_invalidate_proof |
| [#211 / 4326671296](https://github.com/srobroek/slopvac/pull/211#discussion_r4326671296) | Valid; fixed | prune_cache includes ruleset and locale slots; test_cache_all_removes_ruleset_and_locale_slots |
| [#211 / 4326671308](https://github.com/srobroek/slopvac/pull/211#discussion_r4326671308) | Valid; fixed | filesystem names use os.fsencode; test_canonical_and_surrogate_origins |
| [#211 / 4326671318](https://github.com/srobroek/slopvac/pull/211#discussion_r4326671318) | Valid; fixed | content keys use canonical file identities; test_canonical_and_surrogate_origins |
| [#212 / 4326705404](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705404) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326705438](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705438) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326705452](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705452) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326705474](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705474) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326705489](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705489) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326705508](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705508) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326705522](https://github.com/srobroek/slopvac/pull/212#discussion_r4326705522) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#212 / 4326884975](https://github.com/srobroek/slopvac/pull/212#discussion_r4326884975) | Already fixed | PR #213 intentionally added will/can never. Both will never and will not ever now fire consistently; test_negative_guarantee_review_examples |
| [#212 / 4326884994](https://github.com/srobroek/slopvac/pull/212#discussion_r4326884994) | Valid; fixed | negative-guarantee subject accepts the inline-code NUL token; test_negative_guarantee_review_examples |
| [#212 / 4326885006](https://github.com/srobroek/slopvac/pull/212#discussion_r4326885006) | Valid; fixed | each table cell has an independent lexical span with preserved source offsets; test_table_cell_matches_keep_their_start_and_end |
| [#212 / 4326885023](https://github.com/srobroek/slopvac/pull/212#discussion_r4326885023) | Valid; fixed | add irregular past forms including drove and understood to the exclusion; test_negative_guarantee_review_examples. This remains a heuristic, not a complete tense parser |
| [#213 / 4327762090](https://github.com/srobroek/slopvac/pull/213#discussion_r4327762090) | Unsupported | no config exists describes the actual setup default-resolution condition, not an unrequested guarantee; preserve this configuration fact |
| [#213 / 4327762139](https://github.com/srobroek/slopvac/pull/213#discussion_r4327762139) | Unsupported | no config exists describes the actual setup default-resolution condition, not an unrequested guarantee; preserve this configuration fact |
| [#213 / 4327762155](https://github.com/srobroek/slopvac/pull/213#discussion_r4327762155) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#213 / 4327762174](https://github.com/srobroek/slopvac/pull/213#discussion_r4327762174) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#213 / 4327762201](https://github.com/srobroek/slopvac/pull/213#discussion_r4327762201) | Valid; fixed | README notifier/exit-code prose, catalog/judgment spelling, or semantic-guidance exit list corrected in this patch; verified against CLI and notifier source. |
| [#215 / 4327781062](https://github.com/srobroek/slopvac/pull/215#discussion_r4327781062) | Valid; fixed | cell slicing bounds greedy matches at the original start; test_table_cell_matches_keep_their_start_and_end |
| [#217 / 4328694899](https://github.com/srobroek/slopvac/pull/217#discussion_r4328694899) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696309](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696309) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696316](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696316) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696510](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696510) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696550](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696550) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696560](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696560) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696575](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696575) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696591](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696591) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |
| [#217 / 4328696600](https://github.com/srobroek/slopvac/pull/217#discussion_r4328696600) | Reassessed after merge | See the current-state assessment below. PR #217 merged as 591c1e0. |

## Complete-history scope

The older history adds 308 automated prose annotations and two CodeQL annotations. There are no additional older code-review findings on merged code. Repeated prose annotations are consolidated below by file and rule title. They include deleted skill packages, archived evaluation reports, and repeated lint messages against successive revisions of the same prose. They remain explicitly unresolved in the inventory. This correction PR addresses the recent technical review, factual documentation defects, and recent actionable prose comments. It does not claim to rewrite or individually resolve every historical advisory style annotation. Current changed prose is checked with the repository gate.

| Older technical thread | Disposition | Evidence |
| --- | --- | --- |
| [#177 / 4119833645](https://github.com/srobroek/slopvac/pull/177#discussion_r4119833645) | Unsupported on main | `scripts/judge-corpus/judge_corpus/sources.py` exists only on the open experimental branch. Keep its URL validation review in #177. |
| [#178 / 4182141855](https://github.com/srobroek/slopvac/pull/178#discussion_r4182141855) | Unsupported on main | `scripts/judge-sagemaker/src/judge_sagemaker/pilot/clef_server.py` exists only on the open experimental branch. Keep its exception exposure review in #178. |

| Historical file | Automated rule title | Unresolved annotations |
| --- | --- | ---: |
| `README.md` | Cut a three-item list to the items that carry load | 2 |
| `README.md` | Do not use a semicolon | 5 |
| `README.md` | Keep a noun stack to three words | 1 |
| `README.md` | Keep an explanatory sentence to twenty-five words | 7 |
| `README.md` | Put the condition before the command | 4 |
| `README.md` | Rejoin a one-fragment paragraph | 6 |
| `README.md` | Use a vertical list for complex content | 7 |
| `README.md` | Use an article or a demonstrative before a noun | 1 |
| `README.md` | Use en-US spelling | 11 |
| `README.md` | Use one obligation word | 1 |
| `README.md` | Use sentence case in headings | 1 |
| `README.md` | Use the active voice | 3 |
| `packages/slopvac-lint/README.md` | Count a list lead-in as its own sentence | 1 |
| `packages/slopvac-lint/README.md` | Do not use a Latin abbreviation | 1 |
| `packages/slopvac-lint/README.md` | Do not use a semicolon | 11 |
| `packages/slopvac-lint/README.md` | Keep an explanatory sentence to twenty-five words | 3 |
| `packages/slopvac-lint/README.md` | Put the condition before the command | 3 |
| `packages/slopvac-lint/README.md` | Use a vertical list for complex content | 4 |
| `packages/slopvac-lint/README.md` | Use en-US spelling | 3 |
| `packages/slopvac-lint/README.md` | Use the active voice | 11 |
| `packages/slopvac-lint/docs/domain-categories.md` | Do not hyphenate more than three words | 1 |
| `packages/slopvac-lint/docs/domain-categories.md` | Keep an explanatory sentence to twenty-five words | 1 |
| `packages/slopvac-lint/docs/domain-categories.md` | Use a vertical list for complex content | 2 |
| `packages/slopvac-lint/docs/domain-categories.md` | Use en-US spelling | 1 |
| `packages/slopvac-lint/docs/domain-categories.md` | Use the active voice | 2 |
| Archived evaluation report (exact path in CSV) | Convert a long paragraph to a list or table | 5 |
| Archived evaluation report (exact path in CSV) | Cut a three-item list to the items that carry load | 3 |
| Archived evaluation report (exact path in CSV) | Do not hyphenate more than three words | 1 |
| Archived evaluation report (exact path in CSV) | Do not use a semicolon | 21 |
| Archived evaluation report (exact path in CSV) | Give the absolute date or version | 1 |
| Archived evaluation report (exact path in CSV) | Keep a noun stack to three words | 19 |
| Archived evaluation report (exact path in CSV) | Keep a paragraph to six sentences | 6 |
| Archived evaluation report (exact path in CSV) | Keep an explanatory sentence to twenty-five words | 10 |
| Archived evaluation report (exact path in CSV) | Put the condition before the command | 8 |
| Archived evaluation report (exact path in CSV) | Start with the first new fact | 1 |
| Archived evaluation report (exact path in CSV) | Use a vertical list for complex content | 10 |
| Archived evaluation report (exact path in CSV) | Use en-US spelling | 10 |
| Archived evaluation report (exact path in CSV) | Use sentence case in headings | 1 |
| Archived evaluation report (exact path in CSV) | Use simple tenses only | 1 |
| Archived evaluation report (exact path in CSV) | Use the active voice | 19 |
| Archived evaluation report (exact path in CSV) | Use the controlled replacement word | 1 |
| Archived evaluation report (exact path in CSV) | Write one instruction per sentence | 1 |
| `packages/slopvac-lint/docs/metrics.md` | Convert a long paragraph to a list or table | 1 |
| `packages/slopvac-lint/docs/metrics.md` | Cut a three-item list to the items that carry load | 2 |
| `packages/slopvac-lint/docs/metrics.md` | Do not use a Latin abbreviation | 3 |
| `packages/slopvac-lint/docs/metrics.md` | Do not use a semicolon | 10 |
| `packages/slopvac-lint/docs/metrics.md` | Keep a noun stack to three words | 6 |
| `packages/slopvac-lint/docs/metrics.md` | Keep a paragraph to six sentences | 1 |
| `packages/slopvac-lint/docs/metrics.md` | Keep an explanatory sentence to twenty-five words | 7 |
| `packages/slopvac-lint/docs/metrics.md` | Keep the conjunction | 1 |
| `packages/slopvac-lint/docs/metrics.md` | Put the condition before the command | 7 |
| `packages/slopvac-lint/docs/metrics.md` | Split a long sentence | 2 |
| `packages/slopvac-lint/docs/metrics.md` | Use a vertical list for complex content | 6 |
| `packages/slopvac-lint/docs/metrics.md` | Use en-US spelling | 7 |
| `packages/slopvac-lint/docs/metrics.md` | Use the active voice | 7 |
| `packages/slopvac-lint/docs/migration.md` | Do not hyphenate more than three words | 1 |
| `packages/slopvac-lint/docs/migration.md` | Do not stack auxiliaries | 1 |
| `packages/slopvac-lint/docs/migration.md` | Do not use a semicolon | 1 |
| `packages/slopvac-lint/docs/migration.md` | Put the condition before the command | 1 |
| `packages/slopvac-lint/docs/migration.md` | Use en-US spelling | 2 |
| `packages/slopvac-lint/docs/migration.md` | Use one obligation word | 1 |
| `packages/slopvac-lint/docs/migration.md` | Use simple tenses only | 1 |
| `packages/slopvac-lint/docs/migration.md` | Use the active voice | 2 |
| `packages/slopvac-lint/docs/ste-principles.md` | Cut a three-item list to the items that carry load | 1 |
| `packages/slopvac-lint/docs/ste-principles.md` | Put the condition before the command | 2 |
| `packages/slopvac-lint/docs/vale-traps.md` | Back the claim with a number or example | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Convert a long paragraph to a list or table | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Do not stack auxiliaries | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Do not use a semicolon | 3 |
| `packages/slopvac-lint/docs/vale-traps.md` | Keep an explanatory sentence to twenty-five words | 2 |
| `packages/slopvac-lint/docs/vale-traps.md` | Put the condition before the command | 2 |
| `packages/slopvac-lint/docs/vale-traps.md` | State an action with a verb | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Use a vertical list for complex content | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Use en-US spelling | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Use simple tenses only | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Use the active voice | 1 |
| `packages/slopvac-lint/docs/vale-traps.md` | Write one instruction per sentence | 1 |
| Retired review skill (exact path in CSV) | Use a vertical list for complex content | 1 |
| Retired review skill (exact path in CSV) | Use en-US spelling | 1 |
| Retired writing skill (exact path in CSV) | Do not use a Latin abbreviation | 2 |
| Retired writing skill (exact path in CSV) | Do not use a semicolon | 3 |
| Retired writing skill (exact path in CSV) | Keep a noun stack to three words | 3 |
| Retired writing skill (exact path in CSV) | Keep an explanatory sentence to twenty-five words | 1 |
| Retired writing skill (exact path in CSV) | Keep an instruction to twenty words | 1 |
| Retired writing skill (exact path in CSV) | Use a vertical list for complex content | 4 |


## Assessment before merge

PR #217 is now merged. Its two technical findings are already fixed: `compile_ruleset` calls `require_vale` when validation is requested, and unreadable-version errors include the 3.18.0 floor. The CodeQL URL annotation targets a test assertion against CLI output. That assertion neither validates a URL nor authorizes a request, so the security finding is unsupported. Its remaining prose annotations are advisory. Claims that “checks the” needs “that” are unsupported when the phrase introduces a noun object.

PR #177 still owns the URL validation issue. Its current `_request` checks whether `api.github.com` occurs anywhere in a URL before attaching authorization. An exact HTTPS hostname check and redirect handling can address this on that branch, with tests for deceptive hostnames and redirects. This code is absent from main.

PR #178 still owns the exception exposure review. Its current 422 response returns `str(error)` from model request handling. Return a stable public error and log internal details server-side, with a regression test for sensitive exception text. This PR does not import that server into main.

The 308 historical prose annotations are not 308 distinct current defects. Retired skills, domain-categories.md, and migration.md are obsolete targets; archived evaluation reports should retain their historical content. Current documentation can receive a separate, deduplicated editorial pass. A fresh check of ste-principles.md and vale-traps.md found 46 advisory suggestions, with zero errors or warnings. Remaining categories include sentence length, punctuation, lists, voice, instruction structure, and spelling. Existing changed-file prose checks passed. Historical annotations still need individual comparison before resolution. No decision is needed to assess current prose. Rewriting archived reports or adopting experimental branches needs separate scope.

The new #218 review was also checked before merge:

| Thread | Disposition | Regression evidence |
| --- | --- | --- |
| [4328939735](https://github.com/srobroek/slopvac/pull/218#discussion_r4328939735) | Fixed: preserve authored indentation in comment examples | test_indented_comment_example_is_inert |
| [4328939741](https://github.com/srobroek/slopvac/pull/218#discussion_r4328939741) | Fixed: render inline-code subjects from source | test_inline_code_subject_preserves_reported_source |
| [4328939751](https://github.com/srobroek/slopvac/pull/218#discussion_r4328939751) | Already fixed: retired paths retained in CSV | retired integration invariant and full suite |
| [4328939764](https://github.com/srobroek/slopvac/pull/218#discussion_r4328939764) | Fixed: require a directory for compiled output | blocker regression now sets mode 0600 |
| [4328939774](https://github.com/srobroek/slopvac/pull/218#discussion_r4328939774) | Fixed: refresh validated cache-hit recency | test_ruleset_hit_refreshes_recency |
