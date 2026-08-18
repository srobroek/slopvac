# AI Tells

Last researched: 2026-07.

The per-tell catalog now lives in `slopvac` as rule data, not here. Read it
with `uvx slopvac rules --judgement --format json`: each entry carries a
decidable question, its fix, its named exceptions, and worked examples. That is
one source of truth for the linter and the reviewer, so the two cannot drift.

This file keeps only what is whole-review policy rather than per-rule data: why
structure outranks vocabulary, the clustering threshold, the counter-signals, and
how to refresh the perishable parts.

## The clustering threshold

No single tell proves anything -- humans wrote the training data -- but tells
cluster. Three or more in one passage is a rewrite signal
(<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>).
Rewrite the fact densely; delete only when the sentence carries no fact.

## Why structure outranks vocabulary

Vendors patch lexical tells.
<!-- vale prose-inflation.SlopLexicon = NO -->
"Delve" peaked in 2023-24, fell once mocked, and
<!-- vale prose-inflation.SlopLexicon = YES -->
dropped off sharply in 2025 (Wikipedia catalog, above); OpenAI shipped
instruction-following em-dash suppression in late-2025 frontier models
(<https://techcrunch.com/2025/11/14/openai-says-its-fixed-chatgpts-em-dash-problem/>);
a Washington Post analysis of 328,744 ChatGPT messages found the cliché
palette rotates each generation
(<https://decrypt.co/348923/5-biggest-tells-something-written-ai>). Any
memorized word list is perishable: the 2023-24 band (delve, tapestry, intricate)
was patched or mocked out of the next generation, which is why
`ai-tells.OverusedVocabulary` ships disabled.

Structural and register tells endure because preference training produces
them: raters reward length, markdown, bulleted symmetry, and confident
even-handedness, so every generation reconverges on the same shapes even as
the vocabulary changes (RLHF Book ch. 18, <https://rlhfbook.com/c/18-style>).
When LinkedIn announced demotion of "contrastive construction" slop in 2026,
the pattern named was structural, not lexical
(<https://www.theregister.com/ai-and-ml/2026/07/09/ai-slop-writing-has-taken-over-the-internet-particularly-linkedin-and-x/5269525>).
Weight everything in the next two sections above any word list.

## Refreshing this document

Lexical sections decay per model generation; structural and register
sections endure. When the Last-researched date is more than one model
generation (~12 months) old:

- Re-pull the current revision of Wikipedia's "Signs of AI writing" -- its
  era bands and model-specific notes are actively maintained.
- Sample recent practitioner catalogs (tropes.fyi or successors, editor and
  writing-community threads) for the newest generation's register.
- Check for new lexical-frequency corpus studies (Kobak/Liang-style) and
  for vendor steerability changes that retire a formatting tell.
- Leave the structural, register, stylometric, and counter-signal sections unless
  a source shows a generation broke them.

## Human counter-signals and the register test

Expert prose under-produced by models -- presence of these is evidence of a
human author, and injecting them is the strongest de-slopping move
(<https://gptzero.me/news/how-to-write-like-a-human/>,
<https://matthewvollmer.substack.com/p/i-asked-the-machine-to-tell-on-itself>):

- Non-round numbers from real measurement: "open rate fell from 31% to 22%
  in three weeks", not "results varied".
- Named specifics: the actual client, tool version, file path, failure.
- The reader placed in the scene: second person doing something concrete, where a
  model writes an abstract noun as subject. "You hit this when the cache key
  changes mid-deploy" beats "this situation arises during deployment". The same
  move that fixes false agency above, applied before the sentence is written.
- A stance without hedges: "Subject lines over eight words tank open rates.
  Keep them short."
- An opinionated cut: "We don't support X. Use Y." -- models pad; experts
  refuse.
- Domain shorthand used without explanation, calibrated to the stated
  audience.
- Asymmetric structure: the important point gets three paragraphs, the
  minor one gets a clause.
- A concrete anecdote or a mistake admitted with its cost.

Register test, applied last: would a named expert ship this text to peers
under their own byline? If any sentence survives only because it sounds
finished, it fails.

## Stylometric properties

What detectors measure (GPTZero-class:
<https://gptzero.me/news/how-ai-detectors-work/>,
<https://gptzero.me/news/perplexity-and-burstiness-what-is-it/>):

- Low perplexity -- each next word is the one a language model would predict.
- Low burstiness -- uniform sentence length and structure; GPTZero computes
  it as the standard deviation of per-sentence perplexity.
- Low lexical diversity and a preference for common syntactic frames;
  predictable function-word sequences.

You cannot edit "perplexity" directly, but its causes are the tells above:
stock transitions, symmetric structure, hedged medium-strength claims.
Direct rewrite moves:

- Vary rhythm deliberately: follow a long sentence with a short one that
  carries the load-bearing fact. Metronomic paragraphs read generated even
  when every sentence is fine.
- Break structural symmetry: unequal bullet lengths, a section that is one
  line, an aside where it belongs rather than where the template wants it.
- Replace the predictable word when a more exact one exists -- exactness,
  not thesaurus variety, is what raises information density.
- Caveat: formal and non-native human prose also scores low on these
  metrics, and 2025 research puts unaided human detection at chance. Treat
  detector output as a pointer to passages needing a specificity pass,
  never as proof of authorship.
