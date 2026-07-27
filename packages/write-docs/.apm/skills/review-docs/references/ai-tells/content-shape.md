## Content-shape tells

- Fabricated or damaged citations: DOIs that resolve to unrelated papers,
  invented ISBNs, dead URLs, book cites with no page numbers, `utm_source=`
  tracking junk, and raw assistant artifacts (`oaicite`, `contentReference`,
  `[cite: 1]`, `grok_card`). Verify every reference you did not fetch
  yourself (Wikipedia citation section, above).
- Chat-session leakage: knowledge-cutoff disclaimers ("As of my last
  update"), refusal fragments, "As an AI", placeholder text ("This section <!-- write-docs:allow E5 -->
  would ..."). Delete on sight; then audit the surrounding prose, which was
  pasted from the same session. Mechanised as slop-lint E5 -- the one tell here
  that is never a style judgement, so it errors in every genre.
- Fake specificity: "over 100+", "countless", "numerous", "a wide range of".
  Give the number or drop the quantifier.
- Vaporware description: a doc that describes unbuilt behavior in the present
  tense. `docs-discipline.StatusLanguage` bans the hedge ("coming soon", "not yet
  implemented", "planned"), and deleting the hedge alone converts an honest
  roadmap note into a false claim -- the lint passes and the document now lies.
  The rule is a prompt to cut the CLAIM, not the qualifier. Fix, in order:
  delete the whole passage if the feature does not exist; move it to an issue or
  a spec if the plan matters; keep it only as a documented opt-in flag if the
  code is there behind one. Where a genuinely unreleased state must be stated,
  say it once as structured metadata (a version column, a status field), never as
  body prose. The tell is not the honesty -- it is the mixture, a page that reads
  as shipped and hedges in the margins.
- Adjective-per-noun spray: every noun wears a modifier. Keep adjectives
  that carry load ("destructive", "reversible"); cut decoration.
- Anthropomorphism: "the app understands your workflow". The app detects,
  matches, records, refuses.
- Elegant variation: synonym cycling to avoid repeating a name (repetition <!-- write-docs:allow E2 -->
  penalty artifact). Repeat the noun; precision beats variety.
- One-point dilution: the same argument restated eight ways across a long
  doc, each restatement in a fresh metaphor. Say it once; stop.
- Padded symmetry: sections stretched to match sibling length; invented
  FAQ/Tips/Troubleshooting for problems that do not exist. Two sentences is
  a fine section.
- Superficial -ing analysis: trailing clauses that fake insight --
  "..., highlighting the importance of X", "..., ensuring reliability".
  Either the analysis is a fact (state it as one) or it is air.
- Durable vocabulary habits (shapes, not marker words): copula avoidance
  ("serves as", "stands as", "represents" for "is"; "boasts", "offers" for
  "has"); ability framing ("allows you to", "is designed to" -- write what
  it does); significance inflation ("plays a vital role", "testament to");
  textbook connectors ("moreover", "furthermore" opening consecutive
  sentences). Replace with the concrete verb or noun.
- Over-writing: prose that outgrows what the document is for. Three shapes, all
  mechanised in the `prose-scope` style: a rejected alternative defended in place
  ("X rather than Y, because ...", "for the same reason it does not ..."), an
  implementation cost the reader cannot act on (a timing, a process count), and a
  paragraph of loosely related reasoning appended to a section that had already
  finished. Each is real content in the wrong document. Fix: cut it to the
  behavior, and move the decision to an ADR, a spec, or the commit that made it.
  The test is whether a reader of THIS document acts differently for having read
  the sentence.
