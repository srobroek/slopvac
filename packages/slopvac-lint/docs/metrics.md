# Metrics and text analysis

Slopvac uses deterministic text analysis for its native metric rules. The
[CLI reference](../README.md#scoring) describes how findings become scores and
gates.

## Word counting

Sentence-length rules use a software-documentation-aware word counter rather
than a whitespace split. The counter applies these operations in order:

1. Remove a leading step, list, or section number such as `1.`, `(a)`,
   `4.2.1`, or `Step 3:`.
2. Count each inline-code span, URL or path, command-line flag, environment
   variable, dotted or namespaced identifier, and mixed alphanumeric identifier
   as one word.
3. Count quoted spans and forms such as `No. 1` as one word.
4. Count a detected multiword proper name as one word.
5. Count a parenthesized span as one word in its containing sentence.
6. Count a numeric value with its unit as one word.
7. Count a dotted abbreviation such as `U.S.` as one word.
8. Keep apostrophes and hyphens inside a word when word characters occur on
   both sides.

Examples:

| Text | Counted as |
| --- | --- |
| `30 s` | one word |
| `512 MiB` | one word |
| `"edge gateway"` | one word |
| `client.retry.limit` | one word |
| `--dry-run` | one word |
| `read-only` | one word |

Titles and Markdown emphasis do not receive a separate one-word exemption.
Unquoted title text is counted by the same identifier, proper-name, and lexical
rules as other prose.

## Sentence boundaries

The parser builds prose blocks with `markdown-it-py` and then splits their text
into sentences. It treats a period, question mark, or exclamation mark as a
sentence end only when it occurs at a valid boundary. Periods inside protected
spans, decimal numbers, and recognized abbreviations do not split a sentence.

A colon that introduces a vertical list terminates the lead-in. Each list item
then becomes its own sentence for sentence-level metrics. List items remain
separate Markdown blocks, so they do not increase the
`paragraph_sentences` count of the preceding paragraph.

Dotted initialisms use a conservative boundary heuristic. A following
closed-class opener such as `The`, `This`, `If`, or `We` can start a new
sentence; a following proper-name-like continuation remains attached.

## Text type

Sentence caps depend on the text type. Slopvac classifies text with lexical
rules; it does not use a dependency parser or general part-of-speech model.

- A safety marker such as `WARNING`, `CAUTION`, or `DANGER` produces safety
  text unless the following text is an instruction.
- `NOTE`, `TIP`, `HINT`, and `INFO` are descriptive.
- An instruction recognized from the closed imperative-verb vocabulary is
  procedural.
- Ambiguous text falls back to descriptive.

The current word caps are 20 words for procedural and safety text and 25 words
for descriptive text.

## Native metrics

These metrics are evaluated by the native engine when selected by an active
rule.

| Metric | Measurement |
| --- | --- |
| `sentence_words` | canonical word count for one sentence |
| `clause_boundaries` | heuristic count of clause joins in a sentence |
| `lead_in_words` | words before a colon that terminates a list lead-in |
| `paragraph_words` | canonical word count for one paragraph |
| `paragraph_sentences` | sentence count inside a paragraph block |
| `multiword_noun_words` | longest noun-stack candidate in a sentence |
| `coordinated_items` | longest comma/conjunction series in a sentence |
| `syllables_per_word` | average syllable estimate over prose words |
| `passive_ratio` | share of sentences matching the passive-voice heuristic |
| `hedge_per_100_words` | hedge-pattern matches per 100 prose words |
| `abstraction_density` | abstraction-suffix matches per 100 prose words |
| `concrete_referents_per_paragraph` | concrete-referent matches per paragraph |
| `paragraph_words_stdev` | standard deviation of paragraph word counts |
| `adjectives_per_noun` | adjective-suffix matches divided by noun-suffix matches |
| `consecutive_bold_colon_bullets` | longest run of bold-label list items |
| `bold_spans_per_1000_words` | bold spans per 1,000 prose words |
| `dash_per_1000_words` | aside-style dash matches per 1,000 prose words |

The noun-stack, passive-voice, adjective, abstraction, hedge, and concrete
referent metrics are lexical heuristics. Their names describe the signal being
approximated, not a claim that Slopvac performed full grammatical parsing.

## Source mapping

Markdown code blocks and front matter are kept out of the prose projection.
Inline code and other protected spans remain available to the word counter so
they can count as opaque units. Findings retain source locations mapped back to
the original document.

## Limits

The analysis is deterministic, but several classifications are intentionally
heuristic. Proper-name detection relies on capitalization, imperative detection
uses a closed verb set, and noun-stack detection uses lexical and suffix
patterns. A sentence outside those patterns can be classified differently from
a human grammatical analysis.

Use `slopvac explain <rule-id>` to inspect the rule that consumes a metric.
Use the [triage guide](triage.md) when a deterministic match is valid text in its
specific context.
