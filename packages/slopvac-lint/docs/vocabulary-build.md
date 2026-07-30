# Building the runtime vocabulary from the extracted dictionary

Input: `/tmp/ste100/dictionary.csv`, 2,090 lines (one header plus 2,089 entries), extracted from
the Issue 9 published word list by parsing column 1 of the dictionary pages.

Output: one JSON file keyed on `word|pos`, with the overlay applied on top.

The build is a pure function of the two inputs. Re-running it must produce a byte-identical
result, so the runtime file is generated and never hand-edited.

## Input format

```csv
word,part_of_speech,status,issue
"A",art,approved,9
"ABLE",adj,approved,9
"branch",v,unapproved,9
```

The extraction already resolved the specification's presentation convention: an uppercase
headword is approved, a lowercase headword is not. That convention is why `status` is a real
column rather than an inference the build has to make.

Measured shape of the input:

| Property | Value |
|---|---|
| Entries | 2,089 |
| `status=approved` | 800 |
| `status=unapproved` | 1,289 |
| Headwords with more than one part-of-speech row | 124 |
| Distinct `part_of_speech` values | 8 |

## Part-of-speech normalization

The CSV uses the specification's own eight tags. Map each to our part-of-speech vocabulary.
The mapping is one-to-one, so it is a rename rather than a reduction — no information is lost,
and no two input tags collapse into one output tag.

| CSV tag | Count | Our POS | Note |
|---|---|---|---|
| `v` | 866 | `verb` | Largest class. Includes modals and auxiliaries (`can`, `must`, `will`, `be`, `have`), which a naive checker misreads. |
| `adj` | 496 | `adjective` | Includes participle-shaped adjectives whose matching verb is not approved. |
| `n` | 438 | `noun` | |
| `adv` | 170 | `adverb` | |
| `prep` | 66 | `preposition` | |
| `pron` | 25 | `pronoun` | The rule against gendered pronouns is enforced by absence from this class. |
| `conj` | 25 | `conjunction` | |
| `art` | 3 | `article` | `a`, `an`, `the`. |

Reject the build on any tag outside this table. A ninth tag means the extraction changed and the
mapping needs review, which must fail loudly rather than silently drop entries.

## Key construction

```text
key = lower(word) + "|" + normalize_pos(part_of_speech)
```

Lowercase the word, because the case in the input carries the status signal and that signal is
already captured in the `status` column. Keeping the case would make `TEST|noun` and `test|verb`
look like different words rather than two parts of speech of one word.

### Multiple parts of speech become multiple keys

This is the whole point of the schema. A headword with N part-of-speech rows produces N
independent keys, each with its own status. 124 headwords in the input take this path.

Input:

```csv
"TEST",n,approved,9
"test",v,unapproved,9
```

Output:

```jsonc
"test|noun": { "status": "approved",   "replacement": null },
"test|verb": { "status": "unapproved", "replacement": "do a test of" }
```

Both keys exist. Neither overwrites the other. A checker that finds `test` used as a verb reads
`test|verb`, sees `unapproved`, and reports; the same checker finds `test` used as a noun, reads
`test|noun`, sees `approved`, and stays silent.

A single-status-per-word structure cannot do this. It must choose one verdict for `test` and is
then wrong in one of the two directions. The main third-party wordset in circulation has exactly
this defect and collapses `test`, `check`, `damage`, `fit`, and `cover` to one status each.

**Build assertion.** After the build, `count(keys) == count(input rows) + count(overlay
additions)`. A shortfall means two rows collided on one key, which means the key construction
lost a distinction. Fail the build.

## Populating `replacement`

The CSV carries no replacement column; the extraction captured status only. Fill `replacement`
from three sources, in precedence order.

1. **The published recurring-error table** — `/tmp/ste100/recurring-errors.csv`, 39 rows, from
   the specification's own front matter. Highest confidence: it is the maintainers' own list of
   the errors they observe. Parse each row as `word (pos) -> replacement (pos)` and write the
   replacement onto the matching key. Two rows carry no lexical replacement at all and set
   `replacement: null` with a note, because they can only be flagged, never auto-fixed. Four
   rows are part-of-speech shifts rather than word swaps — the word stays and its grammatical
   use changes — and the POS-keyed structure expresses those correctly where a flat list would
   fire on the legal use.
2. **The overlay** — any `replacement` in `vocabulary-overlay.yml` wins over source 1, because
   the overlay is where a software-specific rewrite lives.
3. **Null** — the remaining unapproved entries have no replacement yet. The per-entry
   alternative for each of the 1,289 unapproved headwords sits in the dictionary's second
   column and is not yet extracted; it needs fixed-width column parsing rather than the
   line-prefix regex the current extraction used. Until then, those entries flag without
   suggesting, which is correct behaviour and not a defect.

Do not invent a replacement to fill a null. A wrong suggestion is worse than none, because a
reader applies it.

## Applying the overlay

Load `vocabulary-overlay.yml` after the base and merge by key.

- Key absent from the base: insert, with `source: "overlay"`.
- Key present in the base: overwrite `status` and `replacement`, keep `source: "overlay"`, and
  require a `reason`. This is a deviation from a validated source and must be visible.

**Build assertion.** Every overlay entry that overwrites a base key must carry a non-empty
`reason`. Fail the build on a missing reason — an unexplained deviation is the thing the
two-layer design exists to prevent.

Emit a build report listing every overwritten key. That report is the review artifact: a
reviewer reads it instead of diffing 2,089 lines.

## What the build does not produce

Three fields the rules need and this input cannot supply. Each is a named extraction job, not a
gap to paper over.

| Missing | Rules that need it | Where it lives |
|---|---|---|
| Inflected forms (`adapt, adapts, adapted, adapted`) | The verb-form and adjective-form rules | Same dictionary entry as the headword; needs column parsing |
| Approved-meaning gloss | The two word-sense rules | Dictionary column 2; authored prose, so not shippable verbatim even once extracted |
| Per-entry replacement for all 1,289 unapproved headwords | The substitution rules, beyond the 39 already covered | Dictionary column 2 |

Until inflected forms are extracted, the form rules cannot run and are correctly marked
advisory at the normal tier. Do not approximate inflections with a stemmer: the specification
refuses the past participle of a small number of verbs, and a generated inflection cannot know
which.

The gloss is the one item that stays out of the shipped artifact even after extraction. It is
authored explanatory prose rather than a factual triple, so the two word-sense rules remain
reviewer questions rather than becoming mechanical checks.

## Version pinning

Write `issue: 9` into the output and check it at load time. Two counting rules and one status
list changed between issues: Issue 9 binds a number to its unit for word counting and adds
proper names to the collapse list, and one rule moved chapters entirely (articles moved from
the noun chapter to the sentence chapter). A ruleset citing Issue 9 rule numbers against an
Issue 7 word list is silently wrong, which is the failure mode the version field prevents.
