# Summary
Checked all 17 `ai-existing` documents, the complete normal-profile baseline findings, every rule YAML, and paragraph handling in `src/slopvac/engine.py`.
The strongest uncovered corpus signals were one sign-off closer (`Happy migrating!`) and one `Whether you ... or ...` frame; both had 1 AI hit and 0 human hits.
The required cross-sentence definitional-negation detector is specified below; no such pair occurred in either audit corpus, so its measured corpus recall is 0.
Most named candidate families are already owned by mechanical rules or judgement catalog entries; candidates with more human than AI density were rejected.

## Findings
### F1: Cross-sentence definitional negation pair is absent from the mechanical checker
- surface: `ai-tells-structure.contrastive-inversion-frames` (`packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml:25-45`)
- kind: fn-gap
- evidence: The shipped rule's frame is sentence-local (`[^.!?]{1,80}`), while the same tell appears in `independent__issue-comment-pgbouncer.md:3` as “this isn't really a regression, it's the opposite.” The current baseline flags that same-sentence instance, but cannot span `X is A. X is not B.`. The paragraph-scope engine feeds a complete paragraph to a paragraph rule before matching; therefore a paragraph-scoped rule can inspect the boundary.
- evidence: Python `regex` probe (engine-style `regex.I`) returned `True` for `The parser is a library. The parser is not a compiler.`, `The parser is not a compiler. The parser is a library.`, `This isn't about speed. It's about correctness.`, `The migration isn't a rewrite; it's a refactor.`, `Not because it is fast, but because it is deterministic.`, and `The worker doesn't retry. The worker does fail fast.`; it returned `False` for the genuine correction `The limit is 100 requests. It is not configurable.` and for `The parser validates headers. It rejects malformed input.`. The exact ready-to-paste pattern below was compiled and tested. It matched 0 human and 0 AI corpus passages (both corpora were read in full).
- proposal: Add this rule to `ai-tells-agentic.yml`:

```yaml
  - id: definitional-negation-pair
    name: Cut a cross-sentence definitional contrast
    kind: pattern
    severity: error
    message: 'cross-sentence contrast: {match} -- state the claim directly; cut the invented alternative'
    scope: paragraph
    text_type: any
    tiers:
      strict: enforced
      normal: enforced
      relaxed: advisory
    pattern: >-
      (?:(?P<s1>\b(?:the|this|that)\s+[A-Za-z][\w-]*)\s+(?:is|are|was|were|does|do|did)\s+[^.!?;\n]{1,80}\.\s+(?P=s1)\s+(?:isn't|aren't|wasn't|weren't|is not|are not|was not|were not|doesn't|does not|don't|do not|didn't|did not)\s+[^.!?;\n]{1,80}|(?P<s2>\b(?:the|this|that)\s+[A-Za-z][\w-]*)\s+(?:isn't|aren't|wasn't|weren't|is not|are not|was not|were not|doesn't|does not|don't|do not|didn't|did not)\s+[^.!?;\n]{1,80}\.\s+(?P=s2)\s+(?:is|are|was|were|does|do|did)\s+[^.!?;\n]{1,80}|\b(?:the\s+[A-Za-z][\w-]*|this|that)\s+(?:isn't|aren't|wasn't|weren't|is not|are not|was not|were not|'s not|'re not)\s+(?:a|an|the|about|just|simply|only)\s+[^.!?;\n]{1,80}[.;]\s+(?:it(?:'s| is)|this(?:'s| is)|that(?:'s| is))\s+(?:a|an|the|about|just|simply|only)\s+[^.!?;\n]{1,80}|\b(?:the|this|that)\s+[A-Za-z][\w-]*\s+is\s+a\s+[A-Za-z][\w-]*\.\s+it\s+is\s+not\s+a\s+[A-Za-z][\w-]*|\bnot because\b[^.!?;\n]{1,80},\s*but because\b[^.!?;\n]{1,80})
    ignore_case: true
    exceptions: [quotation, defined-term, factual-correction]
    fix: Delete the invented alternative and state the surviving claim; retain a factual correction when the two sentences assert independent properties.
    examples:
      - bad: The parser is a library. The parser is not a compiler.
        good: The parser is a library, not a compiler.
      - bad: The parser is not a compiler. The parser is a library.
        good: The parser validates headers and rejects malformed input.
      - bad: This isn't about speed. It's about correctness.
        good: Correctness is the priority because malformed input must be rejected.
      - bad: The migration isn't a rewrite; it's a refactor.
        good: The migration is a refactor.
      - bad: Not because it is fast, but because it is deterministic.
        good: It is deterministic, so repeated runs produce the same result.
      - bad: The worker doesn't retry. The worker does fail fast.
        good: The worker fails fast without retrying.
      - bad: The parser is a library. It is not a compiler.
        good: The limit is 100 requests. It is not configurable.
    provenance:
      source: references/ai-tells/structure.md ("Contrastive inversion", "Definitional negation")
      url: https://gc.ai/blog/ai-writing-pattern-to-know-contrastive-negation
      note: >-
        Extends the existing sentence-local frame across a paragraph boundary. Exact
        subject repetition supports both polarity orders. The pronominal branch is
        intentionally restricted to definitional markers (a/an/the/about/just/only)
        plus a narrow noun example, so an independent correction such as a numeric
        limit followed by its configurability is not reported by default.
```
- expected effect: FN↓ on future AI prose; measured AI density 0.000/1k and human density 0.000/1k in this fixed corpus because no cross-sentence instance occurred.
- confidence: high for the mechanical gap and paragraph scope; medium for the semantic heuristic (the `factual-correction` exception remains a reviewer decision if a writer intentionally uses the same form).

### F2: Chat-style sign-off closer (`Happy migrating!`) is not covered
- surface: `unguided__guide-migration.md:77`
- kind: fn-gap
- evidence: “Happy migrating! 🎉” is a standalone closing sign-off. The complete baseline has no finding at line 77, and no existing rule token/pattern covers `happy migrating` or `happy coding`. Python probe input `Happy coding!` and `Happy migrating! 🎉` returned `True`; `The migration completes successfully.` and `Happy migration days are here.` returned `False`. Full-corpus counts: human 0, AI 1; no human quotes exist because there were no human matches.
- proposal: Add this rule:

```yaml
  - id: signoff-closer
    name: Remove assistant sign-off
    kind: pattern
    severity: warning
    message: 'assistant sign-off: {match} -- end on the last useful fact'
    scope: prose
    text_type: any
    tiers:
      strict: enforced
      normal: advisory
      relaxed: excluded
    pattern: '(?m)^\s*(?:happy\s+(?:coding|migrating|hacking|reviewing))\s*[!.]?\s*(?:[🎉!.]*)\s*$'
    ignore_case: true
    exceptions: [quotation]
    fix: Delete the sign-off; end with the last actionable or factual sentence.
    examples:
      - bad: Happy coding!
        good: The command exits with status 0 on success.
      - bad: Happy migrating! 🎉
        good: Restart the worker after updating the configuration.
    provenance:
      source: references/ai-tells/structure.md ("Assistant chat residue", "Summary closer")
      url: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
      note: The existing summary-closer rule catches headings such as “Wrapping Up”, not standalone conversational sign-offs.
```
- expected effect: FN↓; AI 1/9,865 words = 0.1014/1k, human 0/21,208 = 0.0000/1k.
- confidence: high for the observed sign-off; low breadth because only one corpus occurrence was found.

### F3: `Whether you're ... or ...` choice-frame is not covered
- surface: `unguided__readme-cache.md:93`
- kind: fn-gap
- evidence: “Whether you're fixing a typo or building a whole new backend, we'd love to have your help.” has no finding in the complete baseline at line 93. Python probe returned `True` for `Whether you're fixing a typo or building a backend, open an issue.` and `Whether you are debugging locally or deploying to production, use the same config.`; it returned `False` for `Users can run the CLI or edit the file.` and `Whether the client is online or offline, retry.`. Full-corpus counts: human 0, AI 1; no human quotes exist because there were no human matches.
- proposal: Add this rule:

```yaml
  - id: whether-choice-frame
    name: State the alternatives directly
    kind: pattern
    severity: suggestion
    message: 'whether-choice frame: {match} -- state the two cases directly or remove the ceremony'
    scope: sentence
    text_type: any
    tiers:
      strict: enforced
      normal: advisory
      relaxed: excluded
    pattern: '\\bwhether\\s+you(?:''re|\\s+are)?\\b[^.!?\\n]{1,100}\\bor\\b[^.!?\\n]{1,100}'
    ignore_case: true
    exceptions: [quotation, documented-choice]
    fix: Name the two supported cases directly, or keep the sentence only when the choice itself is load-bearing.
    examples:
      - bad: Whether you're fixing a typo or building a backend, open an issue.
        good: Open an issue for typo fixes and new backends.
      - bad: Whether you are debugging locally or deploying to production, use the same config.
        good: Use the same config locally and in production.
    provenance:
      source: references/ai-tells/structure.md ("Whether ... or ... choice frame")
      url: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
      note: >-
        Deliberately requires a second-person subject and same-sentence `or`; this avoids
        ordinary technical alternatives such as “whether the client is online or offline”.
```
- expected effect: FN↓; AI 1/9,865 words = 0.1014/1k, human 0/21,208 = 0.0000/1k.
- confidence: medium; one observed AI instance and no human matches, but the structure can be legitimate in instructional copy.

## Decommission candidates
- Do not add a broad `Here's how/why` token. It had AI 1 (independent__blog-skip-locked.md:8) versus human 3 (`ripgrep-guide-2021.md:125, 634, 672`), i.e. AI 0.1014/1k versus human 0.1415/1k; it fails the required discrimination criterion.
- Do not add a broad `From X to Y` detector. It had AI 1 (the dogfood README's score range) versus human 3 (`git-contributing-2021.md:225`, `redis-readme-2021.md:354`, `ripgrep-guide-2021.md:649`), so it also has higher human density.
- Do not duplicate covered lexicon/structure families: `at its core`, `think of it as`, `let's dive`, `acts as`, `which means`, `so that you can`, `isn't just`, `in other words`, `what this means`, `key takeaway`, `in conclusion`, `robust`, `comprehensive`, `seamless`, `leverage`, `utilize`, `facilitate`, `cutting-edge`, `state-of-the-art`, `game-changer`, `moving forward`, `unpack`, and `dive deep` are already represented by existing rules, judgement entries, or the active STE/Orwell lexicon. The baseline sample/full finding mapping was checked before treating a candidate as uncovered.

## Checked and fine
- All 17 AI documents were read, including the contaminated dogfood README and the nine independent/unguided genre documents.
- `ai-residue.chat-leakage` already covers `I hope this helps`, `feel free to ask`, knowledge-cutoff language, and `[insert ... here]`; no duplicate proposal was made.
- `ai-tells-structure.false-suspense-frames`, `meta-narration-frames`, `fragment-question-pivot`, `rhetorical-question-transition`, `think-of-it-as-core`, and `summary-closer-frames` cover their listed mechanical cores.
- Existing `prose-inflation.slop-lexicon`, `prose-inflation.business-jargon`, `orwell.unsupported-evaluative`, and STE substitutions cover most listed adjectives and verbs.
- Label-colon bullets, `The result?`/`Why? Because`, `no X, no Y, just Z`, `ensuring/allowing/enabling you to`, `enter/meet`, `say goodbye`, `in today's fast-paced`, `ever-evolving`, `the world of`, `testament`, `underscores`, `plays a crucial role`, and `double-edged sword` produced no uncovered AI candidates in this corpus scan.
- Side metrics: `local://audit/TellsCoverage-proposals.json`.
