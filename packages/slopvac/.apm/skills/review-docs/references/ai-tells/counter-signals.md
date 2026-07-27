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
