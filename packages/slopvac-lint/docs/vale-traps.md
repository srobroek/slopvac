# Vale behavior traps

Vale 3.15.2, macOS arm64. These entries come from minimal cases discovered through
execution rather than by reading Vale's docs.

A trap belongs here when the failure is SILENT. The rule loads, Vale exits 0, and
every file reports clean. A silent failure is indistinguishable from a pass, which is the
failure this project exists to prevent. Vale reports `E201` for a *deprecated*
scope and says nothing about any other mistake below.

## The compiler validates against this file

`compile_vale.validate_scope` raises on any scope outside Vale's closed list, so
trap 1 cannot reach a generated style. The tests in `tests/test_compile_vale.py` assert the remaining cases. A trap without a test is a trap waiting to return.

## Scope

### 1. An invalid `scope:` disables the rule silently

`scope: prose` is the worst case, because `prose` is the DEFAULT value of `scope` in
slopvac's rule model. Emitting that scope name verbatim disables rules that omit a scope, while fixtures can still report clean.

```yaml
# reports ZERO on "The gizmo is here."
extends: existence
scope: prose        # <- not a Vale scope. No error. Never fires.
tokens: [gizmo]
```

Without that line, the same rule fires at 1:5.

The following scopes passed probes covering prose blocks and protected code spans:

`text` | `summary` | `heading` | `heading.h1`..`h6` | `table` | `table.header` |
`table.cell` | `list` | `paragraph` | `sentence` | `raw` | `alt`

### 2. `scope: sentence` skips non-paragraph blocks

It selects paragraph blocks only. It splits those blocks into sentences. Vale drops
non-paragraph blocks without reporting an error.

One document, two rules differing ONLY in `scope:`:

| scope | findings |
| --- | --- |
| default | 7 -- paragraph, two list items, blockquote, ordered item, table cell, heading |
| `sentence` | **1** -- the paragraph only |

Reproduced again with `extends: occurrence`, the form that matters here: at
`scope: sentence` a words-per-sentence rule reports 1 where the default scope
reports 4. A long enumeration in a list item falls outside this scope. Never use `scope: sentence` as a cheap sentence splitter.

### 3. `scope:` accepts a YAML list

`scope: [paragraph, heading]` fires in both block kinds and excludes code fences.
A heading-or-paragraph rule needs it to keep working anchors.

### 4. `scope: raw` forfeits code-fence handling

Adding it reflexively put 7 false positives inside code fences on the five hedge
rules. Removing it took them to 0 with no true positive lost. Only a
PARAGRAPH-spanning pattern needs `raw`. A clause-spanning one fires fine at the
default scope.

## Anchors and patterns

### 5. `^` and `$` anchor to the BLOCK, not the line, and `(?m)` is a no-op

Vale removes newlines before passing a whole block to the regex. The `$` anchor matches the block end. It cannot anchor to a sentence inside the paragraph.

```yaml
# fires on BOTH lines, though only the second is a whole-line question
raw:
  - '(?m)^[ \t]{0,3}(?:#{1,6}[ \t]+)?(?:why|what)\b[^.!?\n]{0,60}\?[ \t]*$'
```

```
What is the TTL? 60 seconds.     <- FIRES; `$` matched the block end
Why does the build fail?         <- correct hit
```

Adding a leading `(?m)` changes nothing: two rules that differ only in that flag
produce byte-identical output at the default scope. `(?m)` changes the match set
ONLY at `scope: raw`, where the whole file arrives as one string. Use either `scope: raw` with its fence limitation (trap 4), or a scope list with bare anchors (trap 3).

### 6. A sentence-boundary alternation double-reports, and a lookbehind fixes it

`(?:^|[.!?]\s+)` consumes the boundary, so the block-initial and mid-block spans
differ and Vale reports both. A lookbehind consumes nothing, so there is one span:

```yaml
raw:
  - '(?:^|(?<=[.!?;]\s{1,3}))[Tt]here\s+(?:is|are)\b'
```

### 7. Lookbehind and backreferences work, and are NOT width-restricted

Vale is not using stock RE2 for `raw:`. All of these compile and fire:

| pattern | fires on |
| --- | --- |
| `(?<![\w-])customers?` | "The customer called" |
| `\b(\w+)\s+\1\b` | "The the config is set" |
| `\bmaster(?! branch)\b` | "Promote to master", not "master branch" |
| `(?<!\d )(?<!\d%% )\bmost\s+users\b` | stacked lookbehinds, with an escaped `%` |
| `(?<!\d+ )\bmost users\b` | variable-length lookbehind |
| `(?<=[.!?]\s+)ZQ\w+` | every sentence-initial hit, any gap width |

These examples work without width enumeration or a fixed-width restriction.

### 8. A lookbehind guard on a `\b`-anchored match guards NOTHING

The guard fails because of where the match starts. Match width is irrelevant.
`\b[^\s-]+ly-\w+\b` starts matching at the word start, so Vale evaluates a leading lookbehind BEFORE the stem it means to exclude.

```yaml
# reports all five spans. family/supply/early/assembly were NOT excluded.
raw:
  - '(?<!\b(?:family|supply|early|assembly)\b)\b[^\s-]+ly-\w+\b'
```

Place a leading negative LOOKAHEAD inside the match to guard the stem:

```yaml
raw:
  - '\b(?!(?:early|only|family|supply|assembly)-)[^\s-]+ly-\w+\b'
```

The first guard cannot exclude the stem because it inspects text before the match.

### 9. A literal `%` in a `raw:` pattern depends on the Vale version. Write `\x25`

Vale 3.15 runs the printf formatter over the PATTERN as well as the message, so a
bare `%` corrupts the pattern and it reports zero with no error. `%%` was the
escape. Vale 3.21 passes the pattern through unchanged, so `%%` matches nothing
and `%` matches. Measured with `The build is now 20% faster.` against
`hedge/BaselinelessComparative.yml`: on 3.15.2 the `%%` form fired and the `%`
form reported zero. On 3.21.0 the reverse. The hex escape `\x25` is a `%` to RE2
and nothing to the formatter, so it fired on both.

```yaml
# Fires on 3.15 and 3.21 alike. `%` fires only on 3.21; `%%` only before it.
raw:
  - '(?<!\d )(?<!\d\x25 )\bmost\s+users\b'
```

The fixture test `test_weasel_fixture_fires` carries the probe, so a Vale release
that changes the escaping again fails a behavior test rather than a source-text
check. The pattern above also stacked two lookbehinds, which initially obscured the escaping defect. Vale does not impose a fixed-width lookbehind restriction (trap 7). Isolate one variable at a time:
`%` was the whole cause and the lookbehinds were innocent.

### 10. Multiple `raw:` entries concatenate with NO separator

Vale concatenates the entries. The resulting pattern requires adjacent matches and fails on the separated words in this example.

```yaml
# reports ZERO on "alpha and beta"
raw:
  - '\balpha\b'
  - '\bbeta\b'
```

Splitting ONE long pattern across entries as continuation fragments is the
supported use and works. Joining two whole patterns needs an explicit `|`.

## Tokens and substitutions

### 11. A `tokens:` entry is a REGEX, so punctuation in it widens the rule

```yaml
tokens:
  - honestly?      # "honestl" + optional "y" -> fires on bare "honestly"
```

Verified identical with and without `nonword: true`, so this is distinct from trap
12. Regex metacharacters in a token list change what the token matches. The fix is
`raw:` with the metacharacter escaped.

### 12. `nonword`'s ABSENCE kills a punctuation-terminated token, and its PRESENCE breaks a plain one

`nonword` applies to `tokens:` and `swap:`, which Vale word-wraps. It leaves `raw:` patterns unchanged because Vale does not wrap them.

| rule | result on "Use a cache, e.g. Redis" |
| --- | --- |
| `tokens: ['e\.g\.']` with `nonword: true` | fires |
| `tokens: ['e\.g\.']` without it | **zero, silently** |

Any token beginning or ending in punctuation needs it: `e.g.`, `i.e.`, `etc.`,
`--`, `&`, `%`. The inverse also holds: `nonword: true` on an ordinary word
disables the wrapping, so `here is the thing` matched inside `thingamajig`.

### 13. `swap:` auto-wraps keys, and `ignorecase: true` swallows all-caps

A bare key is safe from substring matches -- `expend` does not fire on
`expenditure`. But with `ignorecase: true` an all-caps occurrence MATCHES, and the
finding names the all-caps span: `VIA`, `is ABLE TO`, and `PRIOR TO` all fire. An
all-caps token can be an RFC 2119 keyword, an identifier, or an initialism.
Case-insensitive replacement can therefore produce false positives. An inline case-sensitivity group works
inside a key:

```yaml
ignorecase: true
swap:
  '(?-i:via)': through   # fires on 'via' and 'Via', NOT on 'VIA'
```

### 14. `substitution` renders REPLACEMENT first, then MATCH

The argument order is the reverse of the reading order in the finding. A message
written `"'%s' -- use '%s' instead"` quotes the FIX where the reader expects the
DEFECT, and tells the author the correct text is wrong. Put the replacement first.

## Counting and tables

### 15. `occurrence` quirks

Vale treats `max: 0` as unset, so the rule never fires. The compiler rejects this value. The message interpolates an int, so `%s` renders
`%!s(int=4)`. Use `%d`. Stock Vale uses `min:` for a lower-bound metric.

### 16. A malformed table yields a phantom EMPTY block reported at line 1

An ASCII-pipe pseudo-table without a delimiter row produces a malformed table block containing only code spans. Vale strips its word tokens. A `min:`-based rule
then fires with a count of zero against 1:1 -- the document start, not the
offending line, which makes it undiagnosable from the finding alone. A well-formed
GFM table is exempt at `scope: paragraph`. A malformed one is not. Any `min:`
metric needs a floor above zero.

### 17. `sequence` needs a `pattern:`, and the POS tagger is not reliable

A `sequence` token carrying `tag:` but no `pattern:` is inert. The tagger also
mis-tags "reads" as `VB`, so a lexical test often beats a POS one.

## Configuration

### 18. A `.vale.ini` per-glob section matches from the config root

Vale matches it relative to the config root. A pattern that matches a root-level path can miss the same path one directory down. Measured on a document with 14 findings unfiltered:

| path | findings | glob applied |
| --- | --- | --- |
| `specs/x.md` | 0 | yes |
| `docs/specs/z.md` | **14** | **no** |
| `CHANGELOG.md` | 0 | yes |
| `sub/CHANGELOG.md` | **5** | **no** |

`docs/specs/` and per-package `sub/CHANGELOG.md` paths are common in monorepos.
Lead every genre glob with `**/`.
