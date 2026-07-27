# AI Tells

Last researched: 2026-07.

Markers that flag prose as machine-generated, with the rewrite move for each.
No single tell proves anything -- humans wrote the training data -- but tells
cluster; three or more in one passage is a rewrite signal
(<https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing>).
Rewrite the fact densely; delete only when the sentence carries no fact.

Split by durability, because the sections decay at different rates. LOAD the ones
the review needs; nothing here requires reading all of it.

| File | Covers | Decays |
|---|---|---|
| [ai-tells/structure.md](ai-tells/structure.md) | Rhetorical-structure tells: contrastive inversion, tricolon abuse, false suspense, meta-narration | Slowly |
| [ai-tells/register.md](ai-tells/register.md) | The chat-assistant voice: faux candor, intensifier tics, over-formatting, figurative-verb verdicts | Per model generation |
| [ai-tells/formatting.md](ai-tells/formatting.md) | Punctuation and markup: dash density, emoji headings, bold spray, heading hierarchy | Slowly |
| [ai-tells/content-shape.md](ai-tells/content-shape.md) | Fabricated citations, chat leakage, fake specificity, vaporware description | Slowly |
| [ai-tells/counter-signals.md](ai-tells/counter-signals.md) | What expert prose has that generated prose lacks, and what detectors measure | Slowly |

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
