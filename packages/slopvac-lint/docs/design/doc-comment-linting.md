# Design: documentation-comment-only linting

> **Not implemented.** This document records a design for a future feature. It does not change the shipped CLI, Vale styles, parser dependencies, or default scanning.

## Decision summary

`slopvac` should add a future `--mode doc-comments` mode that extracts documentation comments with Vale tree-sitter Views. The extractor should emit virtual text with source coordinates and should run a deliberately smaller prose-rule subset. It should not parse source with a new Python parser dependency. Origin/main currently exposes only the `--comments` boolean flag (`packages/slopvac-lint/src/slopvac/cli.py:187-190`); the `--mode code-comments` enum, config names, comment scopes, `COMMENT_SAFE_KINDS`, and `tests/test_comment_modes.py` belong to the unmerged `slopvac-8xe.1` source-comment work, not shipped behavior. The existing `prose` route remains unchanged.

The first release should support Python, Java, and Rust. Swift remains deferred until the Vale binary used by the project exposes Swift Views. The release should report Go and Swift as unsupported when the capability probe cannot load their Views. The implementation must fail closed when extraction is unavailable: it must report an explicit diagnostic rather than linting the source file as prose.

## 1. Supported languages

**Decision.** Admit Python, Java, and Rust in the first implementation. Use an explicit admission table keyed by source extension and language. Defer Go, Swift, and every other language until the selected Vale binary exposes a View and a fixture proves extraction, coordinates, malformed-input behavior, and false-positive controls.

**Evidence.** Vale's tree-sitter View exposes language-specific captures. The repository's source-comment work is not merged into origin/main: the current CLI has only `--comments` (`packages/slopvac-lint/src/slopvac/cli.py:187-190`). Vale 3.21.0 doc-only probes succeeded for Python, Java, and Rust. A three-line marker-less Go comment returned only its last line when queried with the available adjacency form. Swift admission requires a capability probe because Vale 3.21 does not expose a Swift View in every binary.

## 2. Docstrings

**Decision.** Treat Python triple-quoted strings that occupy a module, class, or function docstring position as documentation comments. Do not treat arbitrary triple-quoted strings as prose. The query must select declaration-associated string nodes, and the extractor must preserve their declaration association.

**Evidence.** Python docstrings are string literals in the syntax tree, not comment tokens. A lexical `"""..."""` rule would lint ordinary strings and violate the feature's scope. Fixtures must place identical text in a declaration docstring and in an assigned string; only the former may produce findings.

## 3. Block documentation comments

**Decision.** Select block documentation comments for languages that mark them in the tree-sitter grammar. Remove only the language delimiter and the leading decoration that the query identifies. Preserve interior text and line boundaries.

**Evidence.** Java `/** ... */`, Rust `/*! ... */` and `///`-adjacent forms, Swift `/** ... */`, and Python docstrings have distinct syntax nodes or marker patterns. The query must not widen ordinary `/* ... */` comments into documentation comments. A fixture pair containing identical prose in ordinary and documentation blocks is required.

## 4. Line documentation comments

**Decision.** Select only line comments whose language marker denotes documentation. Preserve one virtual line for each source line, including blank decorated lines. Do not merge unrelated comments separated by code or a blank unmarked line.

**Evidence.** Rust `///` and `//!` and Swift `///` provide explicit markers. Marker adjacency is language-specific. The extractor must carry the original line number on every virtual line so a finding on a continuation line points to that line, not the declaration's first line.

## 5. Declaration association

**Decision.** Associate a documentation comment with the following declaration when the grammar exposes that relationship. Store the declaration kind and name as metadata, but do not include declaration source text in the lint input. A comment without a valid associated declaration remains a comment candidate only when its language marker explicitly identifies documentation.

**Evidence.** Declaration association prevents a comment-like string or ordinary comment from becoming documentation through proximity alone. Fixtures must cover a comment before a function, class, method, field, and module, plus a comment separated from a declaration by code. The association stores metadata for diagnostics and future policy.

## 6. Markdown association

**Decision.** Parse Markdown inside extracted documentation text only after extraction. Headings, lists, code fences, and links remain Markdown structures in the virtual document. Do not treat source-language fences or examples inside a documentation comment as source files.

**Evidence.** The existing prose engine already handles Markdown targets and masks code fences. Reusing that path preserves current block rules. The extraction layer must map virtual Markdown offsets back to source offsets. Fixtures must prove that a fenced example inside `/** ... */` is not linted as prose and that a list item remains lintable.

## 7. Source path, line, and column mapping

**Decision.** Every virtual document span carries `(source_path, source_line, source_column)` for its first character and a per-character or per-line offset map. Findings must report the original path and the original location. A finding spanning removed delimiters maps to the first retained character.

**Evidence.** The source-mapping contract is coordination with the unmerged `slopvac-8xe.1` source-comment work; origin/main currently exposes only `--comments` (`packages/slopvac-lint/src/slopvac/cli.py:187-190`) and has no `--mode code-comments` route. The implementation must reuse that work's finding-location contract rather than introduce virtual paths. Mapping fixtures must assert path, first line, and first column for block, line, and docstring cases.

## 8. Indentation and delimiter removal

**Decision.** Remove the smallest common indentation after delimiter removal. Strip `/**` and `*/`, `///`, `//!`, and Python string delimiters according to the selected grammar. Strip one optional conventional space after a line marker. Never strip arbitrary leading prose spaces. Keep a mapping entry for every retained character.

**Evidence.** Documentation comments commonly indent interior lines and prefix them with `*`. Removing indentation is necessary for Markdown paragraphs and lists; removing all whitespace changes columns and can join words. Fixtures must cover empty lines, `*` decoration, tabs, nested declarations, and delimiters adjacent to prose.

## 9. Strings or code resembling comments

**Decision.** The extractor operates on syntax nodes. It ignores comment markers inside strings, raw strings, character literals, heredocs, and code fences. It also ignores declaration names and executable code.

**Evidence.** The existing comment-mode contract says strings and source code are not linted. The same invariant is mandatory here. Each supported language needs a fixture containing `"/// not documentation"`, escaped delimiters, raw strings, and comment text inside a code example. The expected result is zero findings from those spans.

## 10. Malformed and partial files

**Decision.** Parse recoverable syntax trees when the selected View can identify a documentation node. If parsing fails before extraction, emit `DOC_COMMENT_PARSE_ERROR` with path and parser details, and do not fall back to prose scanning. A partial file may produce findings only for nodes that the parser identifies unambiguously.

**Evidence.** Source editors and CI often lint incomplete files. Falling back to whole-file prose would create false positives and violate the mode boundary. Fixtures must include an unterminated block, an incomplete declaration, and an unterminated string. The result must distinguish extracted findings from an extraction diagnostic.

## 11. Unsupported-language diagnostics

**Decision.** An explicitly named unsupported source file is an error with `DOC_COMMENT_UNSUPPORTED_LANGUAGE` and a list of admitted extensions. Unsupported files discovered inside a directory are skipped with a counted diagnostic, matching the existing source-comment mode policy. The run exits nonzero when an explicit target cannot be processed.

**Evidence.** The explicit-file and directory distinction is coordination with the unmerged `slopvac-8xe.1` source-comment work. Origin/main currently exposes only `--comments` (`packages/slopvac-lint/src/slopvac/cli.py:187-190`), so its `code-comments` diagnostics are not shipped. A new mode must make the same distinction and must never silently reinterpret an unsupported source file as Markdown or plain text.

## 12. False-positive controls

**Decision.** Enforce five controls: syntax-node extraction, explicit language admission, declaration or marker evidence, source-code and fence masking, and fixture-backed coordinate checks. Add a diagnostic count for skipped spans. Do not add a broad suppression switch that turns the mode into whole-file prose scanning.

**Evidence.** Each control blocks a distinct failure: regex extraction catches strings, extension inference catches unknown languages, proximity catches ordinary comments, missing masking catches examples, and coordinate tests catch virtual-text drift. The test matrix must include negative controls for every supported language.

## 13. Prose-rule subsets for terse comments

**Decision.** Define a `doc-comments` profile subset containing rules that operate on local prose spans: AI residue, unsupported figurative language, unnecessary hedges, and unsafe punctuation. Exclude document-wide density, paragraph-length, heading hierarchy, and sentence-count gates unless the extracted comment has enough text. Keep suggestions available, but cap comment-mode severity so a one-line API annotation does not fail a project because it lacks a paragraph.

**Evidence.** The profile model in `packages/slopvac-lint/src/slopvac/profiles.py` already separates rule tiers and document gates. Terse comments have different units and cannot satisfy document-wide assumptions. The implementation bead must define exact rule IDs and thresholds with fixtures; this design does not silently change current profiles.

## 14. Interaction with `--mode code-comments`

**Decision.** Coordinate with the unmerged `slopvac-8xe.1` source-comment work for ordinary-comment behavior. Origin/main currently exposes only `--comments` (`packages/slopvac-lint/src/slopvac/cli.py:187-190`), not a `--mode code-comments` enum. Once that work lands, `doc-comments` should be a mutually exclusive mode value, not a boolean modifier. `doc-comments` selects documentation nodes only; the ordinary source-comment route selects its documented ordinary and documentation-comment scopes. The default `prose` mode is unchanged.

**Evidence.** `packages/slopvac-lint/src/slopvac/cli.py:187-190` shows the shipped `--comments` flag and no `--mode` option. The `slopvac-8xe.1` acceptance criteria define the separate ordinary and documentation-comment profiles that this design must coordinate with.

## 15. Vale-native scopes versus tree-sitter versus a native lexer

**Decision.** Use generated Vale tree-sitter Views as the extraction mechanism. Vale-native scopes are the execution surface and provide the existing rule engine. A generated View named `__slopvac_doc` is consumed through `text.comment.__slopvac_doc.line` and `text.comment.__slopvac_doc.block`. Tree-sitter queries provide syntax-aware selection. Do not add a Python tree-sitter parser or a native lexer in the first implementation.

**Evidence.** Vale appends a tree-sitter View scope entry's `name` to `text.comment`, then appends `.line` or `.block`; the View filename does not create that scope. The generated scope entry must therefore be named `__slopvac_doc`, so the exact targets are `text.comment.__slopvac_doc.line` and `text.comment.__slopvac_doc.block`. The repository's supported Vale floor is 3.15.0 (`packages/slopvac-lint/src/slopvac/vale_probe.py:26-29`). The 3.21.0 probes are development evidence only; implementation acceptance requires the same fixture matrix to pass on a separately probed minimum for this feature, because the existing floor does not yet have View evidence. A Python parser bundle would add binary dependencies, platform packaging work, and a second grammar source. A native lexer would duplicate grammar behavior and mishandle nested strings, raw strings, and recovery. The generated View keeps the dependency footprint at zero.

## 16. Vale 3.21 limitations and rejected options

**Decision.** Treat View behavior as version- and language-specific. Probe a separate minimum Vale version for this feature instead of assuming the repository floor supports Views. Run a startup capability probe and report a diagnostic when a required View query is unavailable. Defer Go until the adjacency and quantified-capture limitations are resolved upstream or a safe query exists.

**Evidence.** In Vale 3.21.0, a `#match?` predicate on a quantified capture dropped the whole match in measurement. An adjacency anchor rejected a quantified capture. These behaviors make marker-less Go runs unreliable. The repository's supported Vale floor is 3.15.0 (`packages/slopvac-lint/src/slopvac/vale_probe.py:26-29`), while `packages/slopvac-lint/docs/vale-traps.md:3-4` records execution-backed evidence on Vale 3.15.2. The implementation must add an execution-backed View fixture on the selected minimum before claiming support; until then, 3.21.0 remains development evidence, not the support floor. Reference material includes [Vale code format](https://docs.vale.sh/formats/code), [Views](https://docs.vale.sh/topics/views/), and the [View key](https://docs.vale.sh/keys/view/). Vale issue 1125 and PR 1151 concern language support, so they are not evidence for these query limitations.

## 17. Performance and dependency implications

**Decision.** Generate Views once per invocation, cache compiled query definitions, and process each source file once. The acceptance target is no more than 1.25 times the existing comment-mode wall time on the repository fixture set, excluding Vale startup. Record cold and warm measurements in the implementation PR. Add no runtime Python dependency.

**Evidence.** The implementation team must measure these figures. The implementation PR must run `uv run --project packages/slopvac-lint python -m pytest packages/slopvac-lint/tests` against the repository fixture corpus and attach cold and warm wall-time output for 23 source files and 270 compiled checks. It must report the comparison between doc-only and ordinary-comment runs and measure the rejected parser stack's installed size and first-import time. The implementation team must record the Vale version with each result.

## 18. Migration and unchanged defaults

**Decision.** Ship the mode behind an explicit CLI value and no automatic migration. Existing configurations continue to use `prose` by default. Existing `--mode code-comments` invocations retain their current scope. Documentation may add an opt-in example after the implementation passes the fixture and performance gates.

**Evidence.** Origin/main defines `prose` as the default route and exposes `--comments` as the source-comment flag (`packages/slopvac-lint/src/slopvac/cli.py:187-190`). The `--mode code-comments` invocation and its scope are coordination points for the unmerged `slopvac-8xe.1` work, not current shipped behavior. Changing default discovery would lint source trees unexpectedly and break existing CI assumptions. Migration consists of choosing `doc-comments` for selected commands after implementation and fixture gates pass.

## Implementation boundary and follow-on beads

This design creates no implementation. A future implementation should create these ordered beads:

1. Add the language admission table and diagnostic codes.
2. Add the `doc-comments` mode value and CLI validation.
3. Emit and validate generated Vale Views.
4. Add positive and negative extraction fixtures for each admitted language.
5. Add source mapping and delimiter/indentation audits.
6. Define and review the terse-comment rule subset.
7. Add Markdown association and fence masking tests.
8. Track upstream Vale limitations and Go support separately.
9. Update user documentation only after the mode is implemented and measured.

## Relationship to existing comment work

This design does not replace `slopvac-8xe`, which investigates broader prose rules and TOML comments. It coordinates with, but does not implement, `slopvac-8xe.1`, the unmerged source-comment work. Origin/main currently has only the `--comments` flag (`packages/slopvac-lint/src/slopvac/cli.py:187-190`); the mode enum, config names, scopes, and tests described by that bead are not shipped. Ordinary comments and documentation comments remain separate because they have different extraction boundaries and rule budgets.
