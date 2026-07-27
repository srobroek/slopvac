## Appendix: historical lexical era-bands (unreliable for current models)

Marker-word lists date fast: each band below was patched or mocked out of
the next model generation, so absence proves nothing and presence mainly
indicates unedited output from that band's era. Do not weight these against
2025+ text.

```text
2023-mid-2024: delve, tapestry, testament, landscape, interplay, boasts,
               garner, intricate, pivotal, vibrant, meticulous, underscore
mid-2024-2025: fostering, showcasing, highlighting, align with, enduring,
               bolstered, emphasizing, enhance, crucial, pivotal, vibrant
mid-2025+:     emphasizing, enhance, highlighting, showcasing
```

Provenance: Wikipedia's era-tracked bands (above); corpus studies that
measured post-ChatGPT frequency jumps -- Kobak et al., 15M PubMed abstracts,
379 style words with elevated 2024 frequency, the excess in verbs and
adjectives ("delves" 28.0x, "underscores" 13.8x; <!-- write-docs:allow E2 -->
<https://arxiv.org/abs/2406.07016>) and Liang et al. on AI-conference peer
reviews ("meticulous" 34.7x, "intricate" 11.2x;
<https://arxiv.org/abs/2403.07183>).

The `WriteDocs.SlopLexicon` Vale rule owns the mechanical ban list. Words in
these bands are still worth cutting when they displace a more exact word -- but
as style debt, not as authorship evidence. The upstream
`ai-tells.OverusedVocabulary` rule is disabled precisely because it is this
appendix's dead band shipped as an error.
