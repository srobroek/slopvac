# Vale behaviour traps

Vale 3.15.2, macOS arm64. Every entry is reproduced from a minimal case, and every
one was found by execution rather than by reading Vale's docs.

A trap belongs here when the failure is SILENT. The rule loads, Vale exits 0, and
every file reports clean. A silent failure is indistinguishable from a pass, which is the
failure this project exists to prevent. Vale reports `E201` for a *deprecated*
scope and says nothing about any other mistake below.

## The compiler validates against this file

`compile_vale.validate_scope` raises on any scope outside Vale's closed list, so
trap 1 cannot reach a generated style. The rest are asserted in
`tests/test_compile_vale.py`. A trap without a test is a trap waiting to return.

## Scope

### 1. An invalid `scope:` disables the rule silently

`scope: prose` is the worst case, because `prose` is the DEFAULT value of `scope` in
slopvac's rule model. Emitting that scope name verbatim would have disabled every rule
that never sets one -- the majority -- while every fixture reported clean.

```yaml
# reports ZERO on "The gizmo is here."
extends: existence
scope: prose        # <- not a Vale scope. No error. Never fires.
tokens: [gizmo]
```

Delete the line and the same rule fires at 1:5. Valid scopes, each confirmed by
firing a rule against a document holding the token in a heading, a paragraph, a
table, a list, a blockquote, and a code span:

`text` | `summary` | `heading` | `heading.h1`..`h6` | `table` | `table.header` |
`table.cell` | `list` | `paragraph` | `sentence` | `raw` | `alt`

### 2. `scope: sentence` cannot see list items, blockquotes, headings, or table cells

It selects paragraph blocks only, then splits those into sentences. Every other
block type is dropped, with no error.

One document, two rules differing ONLY in `scope:`:

| scope | findings |
| --- | --- |
| default | 7 -- paragraph, two list items, blockquote, ordered item, table cell, heading |
| `sentence` | **1** -- the paragraph only |

Reproduced again with `extends: occurrence`, the form that matters here: at
`scope: sentence` a words-per-sentence rule reports 1 where the default scope
reports 4. A long enumeration is usually written as a list item, which is exactly
what this scope cannot see. Never use `scope: sentence` as a cheap sentence splitter.

### 3. `scope:` accepts a YAML LIST, which is undocumented

`scope: [paragraph, heading]` fires in both block kinds and excludes code fences.
A heading-or-paragraph rule needs it to keep working anchors.

### 4. `scope: raw` forfeits code-fence handling

Adding it reflexively put 7 false positives inside code fences on the five hedge
rules. Removing it took them to 0 with no true positive lost. Only a
PARAGRAPH-spanning pattern needs `raw`; a clause-spanning one fires fine at the
default scope.

## Anchors and patterns

### 5. `^` and `$` anchor to the BLOCK, not the line, and `(?m)` is a no-op

Vale hands the regex one whole block with the newlines already gone, so `$` matches
after the block's last character and a mid-paragraph sentence is not anchorable.

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
ONLY at `scope: raw`, where the whole file arrives as one string. Either take
`scope: raw` and its fence blindness (trap 4), or take a scope list (trap 3) with
bare anchors.

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
| `(?<!\d )(?<!\d%% )\bmost\s+users\b` | stacked lookbehinds, once `%` is escaped |
| `(?<!\d+ )\bmost users\b` | variable-length lookbehind |
| `(?<=[.!?]\s+)ZQ\w+` | every sentence-initial hit, any gap width |

No width enumeration is needed, and the fixed-width restriction this file once
claimed does not exist.

### 8. A lookbehind guard on a `\b`-anchored match guards NOTHING

The reason is anchoring, not width. `\b[^\s-]+ly-\w+\b` starts matching at the word
start, so a leading lookbehind is evaluated BEFORE the stem it means to exclude.

```yaml
# reports all five spans. family/supply/early/assembly were NOT excluded.
raw:
  - '(?<!\b(?:family|supply|early|assembly)\b)\b[^\s-]+ly-\w+\b'
```

A stem guard must be a leading negative LOOKAHEAD inside the match:

```yaml
raw:
  - '\b(?!(?:early|only|family|supply|assembly)-)[^\s-]+ly-\w+\b'
```

The unquoted guard is the trap that ships a rule reading as guarded while the guard does nothing.

### 9. A literal `%` in a `raw:` pattern kills the rule, not just the message

The printf formatter runs over the PATTERN as well as the message. `%` must be `%%`
in both places.

```yaml
# reports ZERO. Escape to `\d%% ` and it fires.
raw:
  - '(?<!\d )(?<!\d% )\bmost\s+users\b'
```

The pattern above also stacked two lookbehinds, so the obvious reading was that
Vale limits lookbehind. It does not (trap 7). Isolate one variable at a time: `%`
was the whole cause and the lookbehinds were innocent.

### 10. Multiple `raw:` entries concatenate with NO separator

The entries become one pattern requiring the first to be immediately followed by
the second, which matches nothing.

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
12. Any token list holding `?`, `.`, `+`, `*`, `(`, or `|` is affected. The fix is
`raw:` with the metacharacter escaped.

### 12. `nonword`'s ABSENCE kills a punctuation-terminated token, and its PRESENCE breaks a plain one

`nonword` applies to `tokens:` and `swap:`, which Vale word-wraps. It is a no-op on
`raw:`, which is never wrapped.

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
all-caps token is usually an RFC 2119 keyword, an identifier, or an initialism, so
such a key is a false-positive generator. An inline case-sensitivity group works
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

`max: 0` is silently treated as unset, so the rule never fires -- the compiler
raises rather than emit one. The message interpolates an int, so `%s` renders
`%!s(int=4)`; use `%d`. `min:` works and is how a lower-bound metric is expressed
in stock Vale.

### 16. A malformed table yields a phantom EMPTY block reported at line 1

An ASCII-pipe pseudo-table with no delimiter row parses as a malformed table whose
block holds only code spans, so every word token is stripped. A `min:`-based rule
then fires with a count of zero against 1:1 -- the document start, not the
offending line, which makes it undiagnosable from the finding alone. A well-formed
GFM table is exempt at `scope: paragraph`; a malformed one is not. Any `min:`
metric needs a floor above zero.

### 17. `sequence` needs a `pattern:`, and the POS tagger is not reliable

A `sequence` token carrying `tag:` but no `pattern:` is inert. The tagger also
mis-tags "reads" as `VB`, so a lexical test often beats a POS one.

## Configuration

### 18. A `.vale.ini` per-glob section is anchored to the CONFIG ROOT

It is not matched anywhere in the path, so an exclusion reads as configured and
does nothing one directory down. Measured on a document with 14 findings unfiltered:

| path | findings | glob applied |
| --- | --- | --- |
| `specs/x.md` | 0 | yes |
| `docs/specs/z.md` | **14** | **no** |
| `CHANGELOG.md` | 0 | yes |
| `sub/CHANGELOG.md` | **5** | **no** |

`docs/specs/` and a per-package `sub/CHANGELOG.md` are the common case in a
monorepo, not the edge case. Lead every genre glob with `**/`.

## Method note: three fixtures are not enough

Across the rules verified this way, most passed their own hand-written negative
fixture and then failed a third fixture written adversarially against the regex. A
sample of what only the adversarial pass caught:

| rule | passed negative, failed adversarial on |
| --- | --- |
| `orwell.NotUn` | "not under the schema root", "not unique to", "do not uninstall" -- 5 false hits from `\bnot\s+un\w+` |
| `prose-inflation.VagueDeclarative` | "The risk is real memory pressure above 200 MB" |
| `prose-inflation.Uncomparables` | "Most unique identifiers are UUIDv7" -- `most` quantifies the NOUN |
| `prose-craft.Hyphens` | "family-friendly", "supply-chain", "reply-to" -- no stem test |
| `prose-craft.LinkText` | `[learn more about mTLS]`, `[Settings page]` -- matched a label CONTAINING a vague word |

And the strongest case for a FOURTH pass, against real documents:
`ste-verbs.PassiveVoice` survived a positive, a negative, AND an adversarial
fixture. Its `nt|lt|ft` suffixes matched
judgment/different/current/important/consistent/permanent, and it flagged "are
irreducibly judgment" in this project's own `coverage.md`.
`ai-tells-structure.ContrastiveInversionFrames` fired on the repo's own
`tests/fixtures/vale/must-not-fire.md:15`.

A corpus pass belongs INSIDE the verification loop. `evals/independent/` holds 8
documents across 5 registers, none written against these rules. Four defects came
out of it that no fixture had imagined: the RFC 2119 substitution inversion, the
"Master Subscription Agreement" false positive, the all-caps class, and the dead
`quotation` exception.

One false-positive class no rule here fixes: a **blockquoted citation**. 14 of
`wordiness` plus `latinisms`' 40 corpus hits are inside quoted Orwell, and Vale has
no blockquote-excluding scope.
