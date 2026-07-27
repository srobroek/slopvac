## Register tells (current generation, 2025-26)

The chat-assistant register that survived lexical patching. Each entry is a
voice, not a word -- synonym-swapping does not remove it.

- Faux-candor pivot: "Here's the thing:", "honestly?", "let's be real",
  performative vulnerability that reads polished and risk-free
  (tropes.fyi "False Vulnerability"). Fix: cut the intimacy performance;
  candor is the unhedged claim itself.
- Punchy-fragment cadence: TED-talk rhythm -- short dramatic fragments,
  slow build to a Big Insight, repetition for effect. Fix: rejoin fragments;
  one long sentence and one short one beat six fragments.
- Intensifier tics: "genuinely", "actually", "quietly excellent", "deeply",
  "fundamentally", "remarkably" -- unearned emotion announced instead of
  earned (tropes.fyi "magic adverbs";
  <https://github.com/conorbronsdon/avoid-ai-writing>). Fix: drop the
  intensifier, add the specific claim that would justify it.
- Corporate-analytic filler: "at its core", "it's worth noting",
  "importantly", "nuanced", "granular", "lean into" -- analysis-flavored
  packaging around no analysis. Fix: delete the wrapper; keep the noun.
- Over-formatting reflex: headers, tables, and bold-colon bullets where two
  sentences of prose would do -- a direct reward-model artifact (RLHF Book
  ch. 18; per-model formatting fingerprints in
  <https://arxiv.org/abs/2502.12150>). Fix: format only when the data has
  columns or the items are parallel and independent.
- Uniform paragraph mass: every paragraph three sentences of 15-20 words,
  metronomic transitions, no tangents. Fix: vary length deliberately; let
  one point take three paragraphs and the next one clause.
- Hedged symmetry: every claim balanced by its counter-claim nobody made;
  comprehensive even-handedness where a human picks a side. Fix: take the <!-- write-docs:allow E2 -->
  position the evidence supports; cut the ballast.
- Sycophantic meta-residue: "Great question!", "You're absolutely right",
  qualifier-then-immediate-reassurance stacks -- chat-approval training
  leaking into shipped prose. Fix: delete; then audit the surrounding text,
  which came from the same session.
- Figurative-verb verdict: judgement delivered as metaphor rather than claim --
  "the point lands", "the argument holds", "stays quiet about", "punches above
  its weight", "the abstraction earns its keep". The construction carries the
  verdict so no evidence has to. Fix: state the judgement literally, with the
  observation that supports it. Distinctly 2026 register -- it survived the
  lexical patching that killed the 2023-24 adjective bands.
- Urgency inflation: "cannot be overstated", "more important than ever", "at an
  inflection point", "in an increasingly complex world" -- stakes asserted to
  substitute for consequence. Fix: name what breaks if the reader ignores it,
  or drop the framing.
- Organic-consequence framing: "falls out naturally", "emerges organically",
  "a natural consequence of" -- presenting a designed decision as something that
  happened by itself, which erases the agent who chose it. Fix: say the choice
  was made, and why.
- False agency: an abstraction promoted to actor so no human is named -- "the
  complaint becomes a fix", "the culture shifts", "the data tells us the market
  rewards speed", "a bet lives or dies in days", "X stops being a helper and
  starts being a framework". Distinct from the two entries around it: those grant
  a component desert ("earns its keep") or self-causation ("falls out
  naturally"); this promotes the object into the subject slot. Fix: name the
  human. "The team fixed it that week" beats "the complaint becomes a fix"; if no
  specific person fits, use "you" and put the reader in the seat. Mechanised as
  `prose-agency.FalseAgency`.
- Anthropomorphised justification: "earns its keep", "pulls its weight",
  "load-bearing", "deserves a closer look", "settles the debate" -- a component
  granted intent so its value needs no argument. Fix: state the measured
  property. (Broader than the anthropomorphism entry under content-shape tells,
  which covers subjects *acting*; this covers subjects *deserving*.)

Model fingerprints inside this register drift fast: as of 2026 Wikipedia
tracks Grok-specific overuse ("empirical", "correlate") and notes hedged
qualifier-reassurance stacking as characteristic of Claude
(<https://matthewvollmer.substack.com/p/i-asked-the-machine-to-tell-on-itself>).
Treat per-model attributions as snapshots, not durable rules.
