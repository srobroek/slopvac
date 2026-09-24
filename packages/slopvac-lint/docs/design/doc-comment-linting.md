# Design: documentation-comment-only linting

> **Status:** proposed. The narrower `doc-comments` mode described here is not
> implemented. The shipped `code-comments` mode is implemented and is the
> baseline this design extends.

## Existing behavior

The CLI already supports source-comment linting:

```sh
slopvac lint --mode code-comments src/
# Equivalent shorthand:
slopvac lint --comments src/
```

`code-comments` uses Vale's source scopes and a comment-safe subset of the
ruleset. It checks ordinary line and block comments, including documentation
comments that the language exposes through those scopes. Source code and strings
remain outside the lint input. Directory scans skip unsupported source types;
an explicitly named unsupported file is an error.

This design proposes a separate mode for users who want **documentation comments
only** rather than all comments.

## Goal

A future `--mode doc-comments` should lint API documentation embedded in source
while excluding ordinary implementation comments. It should preserve the same
rule, configuration, reporting, and source-location contracts as the existing
CLI.

The mode must distinguish documentation from ordinary comments using
syntax-aware evidence. File extensions or regular expressions alone are not
sufficient because comment markers can occur in strings and because Python
docstrings are string nodes rather than comments.

## Extraction contract

The extractor should admit a language only after an execution-backed fixture
proves its documentation-comment query against the supported Vale version.

For an admitted language it must:

1. select documentation line comments, documentation block comments, or
   declaration docstrings according to that language's syntax;
2. exclude ordinary comments, source code, strings, and comment-looking text
   inside strings;
3. preserve a mapping from every retained span to the original path, line,
   column, and source offsets;
4. fail closed when extraction cannot be trusted rather than falling back to
   whole-file prose scanning.

Vale tree-sitter Views are the preferred extraction mechanism because Vale is
already the execution engine for source-comment mode. A capability probe is
required before a language is advertised: View availability and query behavior
can differ by Vale version and language.

## Documentation association

A documentation comment should be associated with its declaration when the
grammar exposes that relationship. The lint input contains the documentation
text, not declaration source code.

Python support requires declaration-position docstrings rather than every
triple-quoted string. Languages with explicit documentation markers can admit a
comment without declaration association when the marker itself identifies the
comment as documentation.

Adjacent line comments may be joined only when the language's documentation
syntax says they form one block. A blank or ordinary code line terminates the
group unless the grammar says otherwise.

## Markdown inside comments

After source extraction, documentation text may be projected through the normal
Markdown parser. This preserves headings, lists, links, and fenced examples while
keeping code fences outside prose rules.

Delimiter and indentation removal must retain source mapping. The extractor may
remove syntax such as `/**`, `*/`, `///`, and conventional leading
decoration, but it must not strip arbitrary prose whitespace.

## Diagnostics

The mode needs explicit diagnostics for:

- an explicitly requested language that the installed Vale cannot extract;
- a source file whose syntax prevents reliable extraction;
- a documentation span whose source mapping cannot be resolved.

Directory discovery may skip unsupported source files with a counted note, as
`code-comments` already does. An explicitly named unsupported target must not be
reported as a successful prose check.

## Rule selection

Documentation comments are often much shorter than standalone documents. The
mode should start from comment-safe local rules and avoid document-wide
assumptions that do not have enough text to measure.

Any new profile or rule subset must be explicit and inspectable through the same
configuration and rule commands as prose linting. It must not silently change
the `normal`, `strict`, or `relaxed` profiles for ordinary documents.

## CLI integration

The proposed interface is a mutually exclusive mode value:

```sh
slopvac lint --mode doc-comments src/
```

The existing `prose` and `code-comments` modes remain unchanged. A
configuration or migration must opt in explicitly; source discovery must not
begin linting documentation comments merely because a source directory is
present.

## Acceptance criteria

Implementation is complete only when tests prove:

- documentation and ordinary comments with identical prose are separated;
- Python declaration docstrings are separated from arbitrary strings;
- strings containing comment markers remain outside the lint input;
- fenced examples inside documentation comments remain excluded from prose
  findings;
- reported locations map back to the original source;
- malformed or unsupported source fails closed;
- every advertised language passes the extraction fixtures on the supported Vale
  floor;
- existing `code-comments` behavior and ordinary prose behavior are unchanged.

Performance measurements should compare the new mode with `code-comments` on
the same fixture corpus. A performance target should be set from those
measurements rather than embedded here before implementation exists.
