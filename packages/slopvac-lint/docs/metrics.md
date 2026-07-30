# The word-counting contract

Every length rule in this ruleset depends on this document. The source specification caps a
procedural sentence at 20 words and an explanatory sentence at 25, then spends four separate
rules (8.4 through 8.7) redefining what one word is. A checker that splits on whitespace
counts more words than the specification does and fires on compliant text.

Worked example. Under this contract the sentence

> Set the timeout to 30 s for the HTTP client in the "edge gateway" service.

counts 11 words. A whitespace tokenizer counts 15. On a 20-word cap that gap is the
difference between silence and a false positive on a sentence the specification permits.

All rule citations below are to Issue 9. Two of these rules changed between issues, so an
implementation targets one issue; this contract targets Issue 9.

## 1. Tokenization for `sentence_words`

Input: one sentence, already delimited by section 3 below. Output: an integer.

Apply the collapse phases in order. Each phase replaces a matched span with a single token
and removes it from the input of later phases. Order matters, because the spans nest: a
quoted title contains numbers, and a parenthetical contains abbreviations.

### Phase 0 — Strip uncounted numbering (rule 8.6 carve-out)

Delete a leading step or paragraph identifier before anything else. It is not counted at all,
which is different from counting as one.

Delete, at the start of the sentence only:

- An ordered-list marker: `1.`, `1)`, `(1)`, `A.`, `a)`, `iv.`
- A dotted section number: `4.2.1`, `4.2.1.`
- A step label: `Step 3.`, `Step 3:`

This is the phase implementers skip most often. Skipping it adds one word to every numbered
step in the document, so a 20-word step measures 21.

### Phase 1 — Collapse code and identifiers to one token each

Not from the source specification, which predates none of this but addresses none of it
either. This phase is our addition for software documentation, and it is a superset of the
specification's alphanumeric-identifier class (rule 8.6, item 4).

Collapse to one token:

- An inline code span (backtick-delimited)
- A file path, a URL, a flag (`--dry-run`), an environment variable
- A dotted or namespaced identifier (`client.retry.limit`, `v1beta1.Deployment`)
- An alphanumeric identifier: any token mixing letters and digits (`36L7`, `SHA256`, `T4g2`)

A fenced code block is not a sentence and never enters the tokenizer.

### Phase 2 — Collapse quoted spans to one token (rule 8.6, item 5)

A span in double, single, or typographic quotes counts as one word regardless of length. The
specification also treats an all-caps run and a font-distinguished run as quoted text; in
Markdown, treat a bold or italic span the same way only when it names a UI element or a
literal value, not when it is emphasis.

Consequence worth stating: a 40-word quoted error message counts as one word. That is correct
and intentional, because the writer cannot edit a quotation.

### Phase 3 — Collapse titles, headings, and label text to one token (rule 8.6, item 6)

A referenced document title, section heading, or label text counts as one word. Detect it
from an explicit reference frame (`refer to`, `see`, `in the`) followed by a title-cased run
of two or more words, or from a quoted span already collapsed in phase 2.

This class needs a project configuration list to work well. Without one, implement it as
quoted-span-only and accept the undercount of unquoted titles.

### Phase 4 — Collapse proper names to one token (rule 8.6, item 7)

A personal name, an organization name, or a place name counts as one word however many words
it spans. Detect a run of two or more capitalized tokens, permitting internal lowercase
function words (`of`, `and`, `for`, `the`).

New in Issue 9. Under Issue 7 these did not collapse, so a counter written against the older
issue reports higher counts on the same text.

### Phase 5 — Collapse parentheticals to one token (rule 8.5)

A parenthesized span counts as one word in the containing sentence. This holds whether it
contains an identifier, an abbreviation, or a full clause.

The parenthetical's own content is then counted a second time, as a separate sentence, against
the same cap. So a parenthetical is both one word outside and N words inside. Implement it as
a second measurement, not as a replacement for the first.

### Phase 6 — Collapse a number with its unit to one token (rule 8.6, item 2)

A numeral or spelled-out number, optionally followed by a unit, counts as one word.

- `30 s`, `30 seconds`, `10 °C`, `10 degrees Celsius`, `20 kg`, `512 MiB` — one word each
- `twenty-one`, `forty-seven` — one word each (a spelled number collapses too)
- `13` and `16` in a range — one word each, so `thru`/`to` between them still counts

Issue 9 binds the number to its unit. Issue 7 counted the unit separately. This is the second
place a counter must declare its target issue.

### Phase 7 — Collapse abbreviations to one token (rule 8.6, item 3)

An acronym, an initialism, or a dotted abbreviation counts as one word: `HTTP`, `VPN`, `NASA`,
`a.m.`, `No. 1`. When an abbreviation directly follows its number, the pair is one word, not
two.

### Phase 8 — Collapse hyphenated groups to one token (rule 8.7)

A hyphen-joined group counts as one word however many segments it has. `read-only`,
`in-flight entertainment system` (2 words: the hyphenated group plus two bare words — the
group is one), `main-gear-door retraction-winch handle` (3 words).

This creates a real incentive: hyphenating a compound shortens the counted sentence. The
specification permits it, and caps the group at three words in rule 8.2, which is why
`hyphen-group-too-long` is enforced independently.

### Phase 9 — Count what remains

Split the residue on whitespace. Count non-empty tokens. Punctuation attached to a word
(a trailing period, comma, or colon) does not produce a token of its own.

### Reference implementation order

```text
sentence_words(s):
    s = strip_leading_numbering(s)        # phase 0, delete
    for phase in [code_and_identifiers,   # phases 1-8, each replaces span -> "\x00"
                  quoted_spans,
                  titles_and_labels,
                  proper_names,
                  parentheticals,
                  numbers_with_units,
                  abbreviations,
                  hyphenated_groups]:
        s = phase(s)
    return len([t for t in s.split() if t])
```

The sentinel token must be a character that cannot appear in prose, so a collapsed span is
never re-split by a later phase.

## 2. `lead_in_words`

Same algorithm as `sentence_words`, applied to the text between the start of the sentence and
a colon that introduces a vertical list. Rule 8.4 gives the colon the force of a period, so
the lead-in is measured as a complete sentence against the cap for its own text type.

Detect a list-introducing colon as: a colon at end of line, followed by one or more lines that
each begin with a list marker (`-`, `*`, `+`, a digit plus `.` or `)`, or a letter plus `.` or
`)`). A colon inside a sentence, or a colon followed by running prose, is not a list colon and
does not terminate the sentence.

## 3. Sentence delimitation

A sentence ends at any of:

1. A period, question mark, or exclamation mark followed by whitespace and a capital letter,
   or by end of input.
2. A list-introducing colon (section 2). Rule 8.4.
3. The end of a vertical-list item. Rule 8.4 makes each item its own sentence, whether or not
   the item ends in a period.
4. A hard line break that ends a heading, a table cell, or a list item.

Non-terminators, because each produces a false split:

- A period inside a collapsed span from phases 1 through 8. Run the collapse phases before
  splitting, or the version string `v1.2.3` becomes three sentences.
- A period in an abbreviation (`a.m.`, `No.`, `e.g.`).
- A period inside a decimal number.

## 4. `paragraph_sentences` versus `sentence_words`: the resolved conflict

Phase-1 analysis flagged this as unresolved and predicted it would be the largest
false-positive driver. It is resolved, from the specification's own worked examples.

**The two counts use different sentence units. They are not the same measurement.**

- For a **word count** (rules 5.1, 6.3, 8.4), each vertical-list item is its own sentence.
- For the **six-sentences-per-paragraph cap** (rule 6.6), a lead-in plus its whole vertical
  list is **one** sentence. The list items contribute nothing.

**Evidence.** The rule 6.6 body carries a six-paragraph worked example in which each paragraph
is annotated with its own sentence count (`/tmp/ste100/_bodies-i9.txt:1707-1737`). Two
annotated blocks settle it:

- A block containing one lead-in sentence and a three-item bulleted list is annotated as one
  sentence.
- A block containing one ordinary sentence, then a second lead-in sentence with a four-item
  bulleted list, is annotated as two sentences.

The second is the decisive one. Four bullets contribute zero to the count, and the number
matches the count of lead-in sentences exactly. A second, independent instance appears in the
rule 6.1 example (`:1541-1542`): a paragraph whose fifth sentence carries a two-item list is
annotated as having five sentences, not seven.

**Confidence: high.** Three annotated instances agree, drawn from two different rules, and the
arithmetic is unambiguous in each. The specification never states the interaction in prose, so
this remains an inference from examples rather than a quoted requirement — that is the only
reason it is not stated as certain. The competing reading (unify the counts) is ruled out
positively, not merely disfavoured: under it, every annotation in the rule 6.6 example is
wrong, and any four-bullet list would breach the six-sentence cap, which would make the
specification's own compliant example non-compliant.

**Implementation.** Count `paragraph_sentences` by counting sentence-terminating punctuation
and list-introducing colons at the paragraph's top level, and skip every line that begins with
a list marker. The word-count path does the opposite and visits each item.

## 5. Procedural, descriptive, or safety: the discriminator

The caps differ by text type and the specification gives no mechanical test. This is ours. It
runs per block, not per document, because a note inside a procedure is descriptive and a
warning inside a procedure is procedural.

Evaluate in order and stop at the first match.

```text
classify(block):
    1. if block starts with a safety marker
         (WARNING | CAUTION | DANGER | NOTICE | ATTENTION, optionally wrapped in
          markdown emphasis or a blockquote, followed by ':' or '.')
       -> safety                      # cap 20  (rule 5.1: safety obeys the procedural cap)

    2. if block starts with an information marker
         (NOTE | TIP | INFO | IMPORTANT, same wrapping tolerance)
       -> descriptive                 # cap 25  (rule 5.5)

    3. if block is a numbered or lettered list item
       AND its first word is a base-form verb not preceded by a subject
       -> procedural                  # cap 20

    4. if the block's first sentence begins with a base-form verb and has no subject
         (imperative mood)
       -> procedural                  # cap 20

    5. otherwise
       -> descriptive                 # cap 25
```

Two properties of this ordering are load-bearing:

- A safety block takes the **procedural** cap of 20 even though its content is usually
  descriptive. Rule 5.1 states this directly.
- A note takes the **descriptive** cap of 25 even though it sits inside a procedure. Rule 5.5
  states this directly.

Imperative detection (steps 3 and 4) needs a verb list plus a no-subject test. Use the
vocabulary's verb base forms as the lexicon. Where the mood is genuinely ambiguous, prefer
`descriptive`: the wider cap produces a miss rather than a false positive, and a false positive
gets the rule disabled.

The default at step 5 means a README classifies as descriptive throughout, which is correct;
its imperative install steps classify as procedural individually at step 3 or 4.

## 6. Metric reference

Every `kind: metric` rule references one of these names.

| Metric | Definition | Threshold | Applies to |
|---|---|---|---|
| `sentence_words` | Section 1 tokenization, one sentence | 20 | procedural, safety |
| `sentence_words` | Section 1 tokenization, one sentence | 25 | descriptive (includes notes) |
| `lead_in_words` | Section 1 tokenization, text before a list colon | 20 | procedural, safety |
| `lead_in_words` | Section 1 tokenization, text before a list colon | 25 | descriptive |
| `sentence_words` | Section 1 tokenization, one vertical-list item | 20 / 25 | by the lead-in's type |
| `paragraph_sentences` | Section 4 count; a list collapses into its lead-in | 6 | descriptive |
| `multiword_noun_words` | Words in a contiguous noun stack, after phase 8 collapse | 3 | any |
| `coordinated_items` | Comma- or `and`-separated items in one series | 3 | any |

Notes on the last two.

`multiword_noun_words` needs a part-of-speech tagger to find the stack boundary. It counts
words, not nouns: a vendor restatement of rule 2.1 says nouns, and that reading contradicts
the specification's own worked counts, which label a four-word stack (three nouns plus an
adjective) a violation. Count words.

`coordinated_items` has no basis in the specification, which states rule 4.3 as a direction
rather than a threshold. Four is our operational trigger, chosen because three inline items
still read cleanly.

## 7. Thresholds the specification does not set

Recorded so no implementer invents them: there is no maximum paragraph count, no maximum words
per paragraph, no minimum sentence length, no limit on list items or list nesting depth, and no
readability-score target. The specification declines to regulate units of measurement,
abbreviation style, and text formatting. The uppercase presentation of safety blocks in the
source examples is a property of those examples, not a rule.
