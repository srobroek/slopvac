# Document-level metrics from `counter-signals.md`

Source: `packages/slopvac/.apm/skills/review-docs/references/ai-tells/counter-signals.md`.
The counter-signals are INVERSE signals: a linter cannot flag an absence per line, so each
becomes `kind: metric`, `scope: document`. Every threshold below is INFERRED from
the catalog's wording, not measured. Calibrate against the same 147,473-word
human-written corpus used for the slop-axis base rates before enforcing any of
them outside `strict`.

Two of the seven are already emitted in `rules/ai-tells-agentic.yml` and must not
be duplicated: `paragraph-length-dispersion` ships as
`ai-tells-register.uniform-paragraph-mass`, and the em-dash density metric ships
as `ai-tells-formatting.em-dash-density`.

| Metric | Definition | Computation | Target | Counter-signal |
|---|---|---|---|---|
| `non-round-number-ratio` | Share of cardinal numbers in the document that are not multiples of 5, 10, or 100. | Match `\b\d[\d,]*(?:\.\d+)?\b` outside code fences; exclude version strings, dates, ports, exit codes, and list markers. Divide non-round by total. | `>= 0.4`, and fire only when total numbers `>= 5`. | "Non-round numbers from real measurement: 'open rate fell from 31% to 22% in three weeks', not 'results varied'." A document whose only numbers are 10, 50, and 100 was not measured. |
| `named-specific-density` | Named specifics per 100 words: file paths, version strings, flag names, identifiers in backticks, and proper nouns. | Count backticked spans matching a path/flag/identifier shape, plus `v?\d+\.\d+(\.\d+)?` version strings. Normalise per 100 words. | `>= 1.5` per 100 words. | "Named specifics: the actual client, tool version, file path, failure." |
| `second-person-concrete-ratio` | Share of sentences whose subject is `you` and whose main verb is a concrete action, against sentences whose subject is an abstract noun. | Sentence-split; classify the subject as second-person, concrete-noun, or abstract-noun (nominalisation suffixes `-tion/-ment/-ance/-ity/-ness`). Ratio = second-person / (second-person + abstract). | `>= 0.25` for consumer docs; excluded for specs. | "The reader placed in the scene ... 'You hit this when the cache key changes mid-deploy' beats 'this situation arises during deployment'." Same move that fixes false agency, applied before the sentence is written. |
| `unhedged-stance-ratio` | Share of declarative sentences carrying zero hedge tokens. | Reuse the `prose-inflation.hedge-stack` and `vague-quantifier` token sets as the hedge inventory; count sentences with no member. | `>= 0.7`. | "A stance without hedges: 'Subject lines over eight words tank open rates. Keep them short.'" Also the burstiness cause the stylometry section names: "hedged medium-strength claims". |
| `refusal-count` | Count of explicit scope refusals: an unsupported option named with its replacement. | Match `(?:do(?:es)? not\|no\|never) support[s]?\b[^.!?]{0,60}\.` followed within two sentences by an imperative or a `use\b` clause. Count per document. | `>= 1` for any document that documents options; suggestion only. | "An opinionated cut: 'We don't support X. Use Y.' -- models pad; experts refuse." Note the tension: `prose-craft.first-person-plural` flags the `we` form, so the refusal must be written as "slopvac does not support X". |
| `section-length-dispersion` | Coefficient of variation of section word counts (stdev / mean), over H2-level sections. | Split on H2; count words per section; compute stdev/mean. | `>= 0.5`. | "Asymmetric structure: the important point gets three paragraphs, the minor one gets a clause." Direct inverse of `ai-tells-content-shape.padded-symmetry` ("sections stretched to match sibling length"), which is the judgement form of the same defect. |
| `sentence-length-dispersion` | Stdev of sentence word count. | Sentence-split; stdev of word counts. | `>= 8`. | "Vary rhythm deliberately: follow a long sentence with a short one that carries the load-bearing fact. Metronomic paragraphs read generated even when every sentence is fine." This is burstiness at the sentence level; `ai-tells-register.uniform-paragraph-mass` is the paragraph-level twin. Ship both or neither -- they measure different granularities of the same property. |

## Not mechanizable, and not proposed as a metric

| Catalog item | Why no metric |
|---|---|
| "Domain shorthand used without explanation, calibrated to the stated audience" | Requires knowing the audience and the field. Carried as `ai-tells-structure.audience-straddle-remainder` (judgement). |
| "A concrete anecdote or a mistake admitted with its cost" | Presence of an anecdote is not countable. Carried as `ai-tells-register.faux-candor-remainder` (judgement). |
| Register test: "would a named expert ship this text to peers under their own byline?" | The catalog's final gate, and irreducibly a judgement. Should ship as ONE document-scope judgement rule if the deslop skill needs a terminal check; not emitted, because it is a whole-review verdict rather than a rule. FLAGGED for a decision. |
| Perplexity, burstiness, lexical diversity | Detector-side properties, not editable. The catalog says so and gives the rewrite moves instead, which are the dispersion metrics above. The caveat has no home in the schema and must not be dropped: formal and non-native human prose also score low, and 2025 research puts unaided human detection at chance, so detector output is a pointer to passages needing a specificity pass, never proof of authorship. FLAGGED -- see `migration.md`. |
