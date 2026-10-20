# Suppressions and exclusions

This page lists each control that changes which rules run or which findings
lint reports. `slopvac prime` prints the short form. `slopvac prime write`
gives the order in which to use them, and `slopvac prime review` gives the
audit. `slopvac explain <rule_id>` prints the named exceptions and the scope of
one rule.

## Directives

A directive is an HTML comment in the source file.

| Directive | Covers | Rules |
| --- | --- | --- |
| `<!-- slopvac-allow: rule=<rule_id> reason=<exception> -->` | The next block | The named rule |
| `<!-- slopvac-disable-next-line -->` | The next block | All rules |
| `<!-- slopvac-disable -->` | Each line up to the next `<!-- slopvac-enable -->` | All rules |

### Grammar

Lint matches each directive with one of these regular expressions from
`suppression.py`:

```text
allow:              <!--\s*slopvac-allow:\s*rule=(?P<rule>[\w.-]+)(?:\s+reason=(?P<reason>[\w-]+))?\s*-->
allow attempt:      <!--\s*slopvac-allow\b
disable-next-line:  <!--\s*slopvac-disable-next-line\s*-->
disable:            <!--\s*slopvac-disable\s*-->
enable:             <!--\s*slopvac-enable\s*-->
```

- The match is case-sensitive.
- Any whitespace, or none, can follow `<!--` and `slopvac-allow:` and can
  precede `-->`.
- One or more whitespace characters separate the rule id from `reason=`.
  Whitespace around `=` breaks the match.
- A rule id holds word characters, dots, and hyphens. A reason holds word
  characters and hyphens. Word characters are letters, digits, and `_`.
- Lint searches each source line, so a directive can follow other text on its
  line.
- A directive opens and closes on one line.

### Malformed allow directives

The allow attempt pattern finds each `<!--` that `slopvac-allow` follows as a
whole word. The text from there to the first `-->` on that line must match the
allow pattern. Otherwise lint reports `meta.invalid-suppression`. A missing
colon, a space after `rule=`, and a comment that closes on a later line are
all malformed.

Only allow directives get this check. Lint reports nothing for a misspelled
disable, enable, or disable-next-line comment, or for a directive in capitals.
Each of these is an ordinary HTML comment and has no effect.

### Scope

An allow directive or a disable-next-line directive covers one block:

1. Lint starts at the line after the directive. It skips blank lines and lines
   that start with `<!--`.
2. The first other line is the target. When it starts with `|`, each following
   line that starts with `|` is a target too, so the directive covers a whole
   table.
3. The directive covers each line of the paragraph, heading, list item, table,
   or quote that holds a target line.

When a block starts on the line of the directive, the directive covers that
block instead. This happens when the directive opens a paragraph, or follows
text on the first line of a block.

Each list item is a separate block, so a directive before a list covers the
first item only. More than one allow directive can cover the same block. Put
them on consecutive lines, or together on one line.

A region starts on the line of `<!-- slopvac-disable -->`. It ends on the line
before `<!-- slopvac-enable -->`. It covers each line between them, including
blank lines and code blocks.

- Regions do not nest. The first enable comment ends the region.
- A region without an enable comment runs to the end of the file. Lint reports
  nothing about it.
- An enable comment outside a region has no effect.
- A line with both a disable and an enable comment starts no region. It ends
  the open region, if there is one.

A directive suppresses a finding by the line that lint reports it on. A
document-level metric reports on line 1.

### Reasons and reports

An allow directive suppresses a finding only when its reason is a named
exception of the rule. `slopvac explain <rule_id>` lists them. A rule without
named exceptions takes no allow directive. Use a disable directive or the
config for such a rule.

Lint reports a bad allow directive as `meta.invalid-suppression` on the line of
the directive, at `error` severity. That directive suppresses nothing.

| Cause | Message |
| --- | --- |
| Malformed directive | `invalid suppression; expected <!-- slopvac-allow: rule=<rule-id> reason=<reason> -->.` |
| Unknown rule id | `suppression names unknown rule <rule_id>.` |
| No reason | `suppression of <rule_id> names no reason. Add reason=<one of: <exceptions>>.` |
| Unlisted reason | `reason "<reason>" is not an exception of <rule_id>. Valid: <exceptions>.` |

`<exceptions>` is the exception list of the rule, or `none defined`.

Lint reports a malformed directive and an unknown rule id in each file. It
reports a missing or unlisted reason only for a rule that the native engine
runs:

- A directive for a rule that does not run is silent. The profile, the
  `[categories]` and `[rules]` tables, `--category`, and `--disable` decide
  which rules run.
- A directive for a rule that Vale runs is silent too, and it still suppresses
  nothing. `slopvac compile --format json` lists the rules that Vale runs.
- With `--diff-base` or `--diff-working-tree`, lint reports no
  `meta.invalid-suppression` finding, on added lines too.

### Quoted directives

A directive inside a code span, a code block, or front matter is text. It has
no effect, and lint reports nothing about it. A code span can continue on the
next line of a block. A blank line or a code block ends it. Show directive
syntax in a code span.

### File types and modes

Directives work in each prose file type: `.md`, `.mdx`, `.markdown`, `.txt`,
`.rst`, and `.html`.

In `.rst`, a published page shows an HTML comment as text. Put the directive
in a `.. raw:: html` block to hide it. A directive in an RST comment, after
`..` on the same line, has no effect.

In `--mode code-comments`, lint takes its findings from Vale and applies no
directive. With `--no-vale`, the native engine applies directives to comment
text, but that run is incomplete and exits 2. For source files, use
`[[overrides]]` or `--disable`.

With a diff option, a directive on an unchanged line still covers the added
lines of its block.

`--fix` changes only the findings that lint reports. It does not change
suppressed text.

### Vale comments

Vale reads its own comments. In Markdown and HTML these are
`<!-- vale off -->`, `<!-- vale on -->`, and `<!-- vale <rule_id> = NO -->`.
In RST, `.. vale off` and `.. vale on` do the same. They hide findings of
the rules that Vale runs, without a reason and without a report. They do not
change native rules, `.txt` files, or source comments. Use a slopvac
directive.

## Automatic exceptions

Some text skips rules without a directive.

A rule with the `quotation` exception skips a match inside one quotation on
one line. The quotation holds 200 characters or fewer between its marks:

- straight double quotes, `"` and `"`
- curly double quotes, `“` and `”`
- curly single quotes, `‘` and `’`

Straight single quotes never mark a quotation, because `'` is also an
apostrophe. A word character before an opening straight quote stops the match.
So does whitespace before the closing quote, or a word character after it.
Pattern, token, and substitution rules apply this exception, and so do Vale
findings. Other native rules, such as metrics, need an allow directive.

A rule whose scope is not `raw` skips code spans, code blocks, and HTML
comments. A `raw` rule reads each source line, code included.

Native rules skip front matter. Rules that Vale runs read the values in it, and
no directive can reach them there, because a directive in front matter is text.
For such a finding, set the rule to `off` in an `[[overrides]]` block.

Each other exception name applies only through an allow directive. Examples
are `code-span` and `identifier-fidelity`.

URLs, paths, flags, and identifiers stay in the text that rules match. Each
counts as one word in sentence-length metrics. Lint does not read the
destination of a link as prose. It reads the link text.

## File controls

- `exclude` holds gitignore-style globs, relative to the config file. Lint
  skips each matching file, even when a target names it.
- A config that sets `exclude` replaces the default list. Repeat the defaults
  to keep them:

  ```toml
  exclude = [
    "**/node_modules/**",
    "**/apm_modules/**",
    "**/.venv/**",
    "**/dist/**",
    "**/build/**",
    "**/CHANGELOG.md",
    "**/.git/**",
  ]
  ```

- A directory target skips subdirectories named `.git`, `.hg`, `.svn`,
  `.venv`, `venv`, `node_modules`, `vendor`, `build`, `dist`, `target`, and
  `__pycache__`. A target that names a file in one of them still reaches it.
- An `[[overrides]]` block takes a `files` list of gitignore-style globs. It can
  also set `profile`, `categories`, `rules`, `thresholds`, `vale`, `locale`,
  and `vocabulary`. Each matching block applies in file order, and a later
  block wins for each field that it sets. This block stops one rule for
  generated files:

  ```toml
  [[overrides]]
  files = ["docs/generated/**"]
  rules = { "prose-inflation.slop-lexicon" = "off" }
  ```

- Only the top level sets `mode`, `exclude`, and `[guidance]`.
- `--profile`, `--category`, `--disable`, `--min-score`,
  `--max-per-100-words`, and `--locale` act as one last override block for
  each file. `--mode` sets the mode of the run.

`slopvac lint --explain-config <file>` prints the settings for one file and
the block that set each one.

## What does not change findings

Lint computes these values, but no rule, gate, or report reads them:

- The origin of a file. A first line that starts with `<!-- generated` or with
  `slopvac reference`, or the name `CHANGELOG.md`, marks a file as generated.
  A path through `.agents`, `.beads`, or `node_modules` marks it as vendored.
  A path through `templates` or `fixtures` marks it as a template.
- A heading named `Examples`, and the blocks under it.
- Front matter keys.

The default `exclude` list skips `CHANGELOG.md`. Its origin does not. Add a
generated file to `exclude` to skip it.
