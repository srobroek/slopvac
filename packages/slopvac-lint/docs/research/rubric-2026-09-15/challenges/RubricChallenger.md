Claim: The proposed gates, evidence contract, decision procedure, constants, and rewrite checker do not reliably separate protected prose from defects; several stated stress cases are impossible under the schema.

VERDICT: CHALLENGED

## Verdicts

| Claim | Verdict | Reason | Evidence refs |
|---|---|---|---|
| C3 | AMEND | Gate-before-score is sound, but protectedness is model-returned and the closed gate vocabulary cannot represent operational requirements, generated schema, or quoted specimens. | `rubric-design.md:106-128`; `packages/slopvac/skills/write-docs/references/change-comms.md:8-20`; `packages/slopvac-lint/docs/rules.md:3304-3317` |
| C4 | REPLACE | “Context never quotable” makes heading antecedents and repo referents fail arity; “byte offsets” conflicts with character slicing and normalized unit text. | `rubric-design.md:130-181`; `packages/slopvac-lint/src/slopvac/analyze.py:209-220,589-606`; `packages/slopvac-lint/docs/rules.md:3053-3059` |
| C7 | REPLACE | Six classes are not exhaustive. Real protected classes missing from the enum are `operational_normative`, `generated_schema`, and `quoted_specimen`. | `packages/slopvac/skills/review-docs/SKILL.md:130-140`; `packages/slopvac-lint/docs/rules.md:54-73,3304-3317` |
| C8 | AMEND | `needs_repo_fact` describes a lookup obligation, not necessarily unchecked work. `no_quote` also conflates absent evidence with evidence stranded in forbidden context. | `rubric-design.md:122-128,173-181`; `packages/slopvac-lint/src/slopvac/rules/ste-words.yml:367-381` |
| C10 | REPLACE | HARM=0/REPAIR<3 rejects a documented genuine parenthesis defect; null rewrites required by the bare-quantifier case contradict the confirm schema and trigger demotion. | `rubric-design.md:195-218,410-425`; `packages/slopvac-lint/src/slopvac/rules/ste-punctuation.yml:117-145`; `packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml:580-622` |
| C11 | AMEND | Token classes are useful, but document-only addition blocks glossary-authoritative fixes, while class-wide exemptions are broader than the one allowed transformation. | `rubric-design.md:219-252`; `packages/slopvac-lint/src/slopvac/rules/ste-words.yml:367-381`; `packages/slopvac-lint/tests/test_engine.py:895-913` |

## Adversarial cases

### 1. A3 preserves the false positive and drops its adjudicator

**Text:** “It is not faster but it is cheaper.” (`packages/slopvac-lint/tests/fixtures/vale/must-not-fire.md:15`).

**Walk:** `contrastive-inversion-frames` matches the fixed frame; its remainder then has A1/A2/A4=true but A3=false, so §5 returns DROP before `factual_contrast`. The mechanical finding remains. **Wrong:** over-firing on a repository-designated clean factual trade-off. **Failure:** A3 assumes the mechanical core is authoritative precisely where the remainder exists to adjudicate semantics. **Minimal fix:** replace A3 with `core_fired: true`; run the remainder once, suppress the core on REJECT/PRESERVE, and deduplicate on CONFIRM. This preserves §11’s factual-contrast outcome rather than breaking it.

### 2. Normative policy has no preservation class

**Text:** “NOT ‘Lays the groundwork’…” and “MUST Repos with release-please or changesets: never hand-edit CHANGELOG.md” (`packages/slopvac/skills/write-docs/references/change-comms.md:8-20`).

**Walk:** the document is `change-comms`, so A4 dispatches AI structure/register packs; A1/A2/A3 pass. None of the six reasons denotes an operational prohibition. A correct scorer must proceed through evidence and FIT and eventually REJECT the negative-inventory candidate instead of PRESERVE. **Wrong:** protected requirements are scored, omitted from `preserved` telemetry, and exposed to stochastic false confirms; policy authors bear the noise. **Failure:** `preservation_reason`. **Minimal fix:** add `operational_normative`, set it deterministically for recognized steering markers, and let it outrank structure/register rules. Existing §11 `formal_legal` remains unchanged.

### 3. Schema-required heading/name pair is classified as echo

**Text:** “#### `ai-residue.chat-leakage`” followed by “Delete chat-session leakage” (`packages/slopvac-lint/docs/rules.md:60-64`).

**Walk:** A1/A2/A4=true, A3=n/a; no preservation reason applies. Heading and name give arity-2 evidence; FIT=3, HARM=0, WARRANT=2, REPAIR=3, hence CONFIRM/suggestion. **Wrong:** over-firing on generated reference schema: the ID is the stable anchor and the imperative is the human label. **Failure:** A4/origin metadata and the six-class enum. **Minimal fix:** add deterministic `origin: authored|generated|vendored|template`; judgement is inadmissible for generated/template units unless a rule opts in. This also protects §11’s authored heading case.

### 4. Honest missing-fact finding cannot satisfy the confirm schema

**Text:** “Some tests need a live database.” (`packages/slopvac-lint/tests/fixtures/vale/must-not-fire.md:14`; also the rule’s bad example at `prose-discipline.yml:607-608`).

**Walk:** A1/A2/A4=true; quote gives WARRANT=2; FIT=3; probe HARM=2; REPAIR=1. §5 initially yields WARNING, but schema says rewrite is required iff confirm; a null rewrite either fails validation or reaches `fact_preserving`, is withheld, and demotes. **Wrong:** under-severity or malformed output for the exact §11 case that says “warning with rewrite null.” **Failure:** `rewrite` cardinality and unconditional checker/demotion. **Minimal fix:** add `rewrite_status: proposed|withheld_needs_fact|not_applicable`; require text only for `proposed`; do not demote `withheld_needs_fact`. A proposed invented numeral still fails, preserving executed case 15.

### 5. The glossary rule cannot introduce the glossary term

**Text:** “The job runner picks up the next work item.” → “The worker picks up the next task.” (`packages/slopvac-lint/src/slopvac/rules/ste-words.yml:367-381`).

**Walk:** A1/A2/A4=true. If the glossary is supplied only in `context`, arity-2 cannot quote its `referent`, so ABSTAIN/no_quote (or needs_repo_fact). If repo evidence is somehow accepted, FIT=3/WARRANT=3/HARM=1/REPAIR=2 confirms, but addition of `worker` and `task` is forbidden when absent from the target document; fix is withheld and demoted. Misclassifying the wrong term as `defined_domain_term` instead yields PRESERVE. **Wrong:** the rule’s only honest fix is unreachable. **Failure:** evidence source, asymmetric addition, and an overbroad preservation class. **Minimal fix:** allow SHA-pinned repo evidence and permit additions present in an authorized `referent`; exemption must name exact from→to token pairs, not all domain terms.

### 6. `context` prohibition forces abstention on a known defect

**Text:** “## Install the plugin” / “This section covers installing the plugin.” (`packages/slopvac-lint/docs/rules.md:3053-3059`).

**Walk:** a paragraph SPAN’s `text` is the sentence and its heading is surrounding `context`; A1/A2/A4=true, FIT=3, but heading-echo requires arity 2. Because the antecedent is never quotable, `evidence_ok=false` and §5 ABSTAINS. **Wrong:** under-firing on the canonical positive that §11 says must confirm. The schema’s own example uses antecedent offsets before `range.start`, contradicting its in-range rule (`rubric-design.md:145-181`). **Minimal fix:** evidence items get `source: unit|context|repo`; only `role:defect` must be unit-local. Alternatively, construct heading-echo units from heading plus opening paragraph.

### 7. Byte offsets cannot be checked by the specified slice

**Text:** “checker — Vale … They produce findings” (`packages/slopvac-lint/docs/rules.md:9`); smart apostrophe specimen “the loader’s cache” (`ai-tells-agentic.yml:1609-1614`); CRLF projection (`tests/test_toml_comments.py:39-43`); code spans in the configuration paragraph (`README.md:305-313`).

**Walk:** A2 depends on source byte ranges, while `unit.text` is normalized: wrapped pieces are stripped and joined with one space, and its mapper stores character offsets (`analyze.py:209-220,589-606`). The specified `text[byte_start:byte_end]` uses character indexing; after `—` or `’`, exact evidence fails. CRLF removal and code-span projection further separate source bytes from normalized text. Result: ABSTAIN/no_quote and unstable IDs for valid evidence. **Wrong:** false unchecked coverage, especially on non-ASCII docs. **Failure:** `range`, `text`, `unit_id`, `evidence_ok`. **Minimal fix:** validate `raw_source_bytes[start:end].decode("utf-8") == quote`; stamp `source_sha256`; keep normalized offsets in a separately named field.

### 8. Three categories count one generated schema three times

**Text:** every generated rule section repeats ID heading, imperative name, and bold field list (`packages/slopvac-lint/docs/rules.md:60-73,84-95`).

**Walk:** absent origin protection, heading-echo (structure) confirms the title/name pair; over-formatting-reflex (register) confirms the bold metadata frame; padded-symmetry (content-shape) confirms equal sibling sections. Each has exact evidence and FIT/WARRANT≥2; ceilings still leave three confirms. §9’s ≥3 findings from ≥2 categories gates REVISE. **Wrong:** false-positive gate on one schema convention, not three independent defects. **Failure:** “distinct category” is not independence. **Minimal fix:** form overlap components from evidence byte ranges and count at most one finding per component toward the cluster gate; require three non-overlapping components across two categories.

### 9. HARM=0 rejects a real non-deletion repair

**Text:** “Rotate the signing key (we found that most teams forget this until an audit, which is why the runbook exists).” (`packages/slopvac-lint/src/slopvac/rules/ste-punctuation.yml:130-145`).

**Walk:** A1/A2/A4=true; FIT=3; exact quote plus `signing key` gives WARRANT=2; matrix forces HARM=0; promoting the second idea to a sentence is local substitution, REPAIR=2. §5 returns REJECT at `harm == 0 and repair < 3`. **Wrong:** false negative against the rule’s own bad example. **Failure:** category HARM constant and global reject clause. **Minimal fix:** set `parentheses-misuse` HARM=1 per rule; retain HARM=0 only for pure-deletion formatting rules. This need not change §11’s unnamed HARM-0 pair.

### 10. Quoted rule specimens are unprotected probe targets

**Text:** the generated question enumerates “most, some, many…” and its quoted bad examples say “Most requests are cached” and “The parser handles many formats” (`packages/slopvac-lint/docs/rules.md:3303-3317`).

**Walk:** whole-document bare-quantifier probe has A1/A2/A4=true. Neither `quotation` nor `rule_specimen` is a preservation enum member. Exact quotes produce FIT=3/WARRANT=2, HARM=2, REPAIR=1; case 4’s rewrite problem follows. **Wrong:** false findings on documentation that demonstrates the rule. Existing rule exceptions include quotation, but `protects` can name only the six classes. **Failure:** C7’s closed enum and deterministic region classification. **Minimal fix:** add `quoted_specimen`; derive it from Markdown quote/fence/example structure before dispatch.

### 11. One document verdict cannot report every document-scope occurrence

**Text:** the 237.5KB generated `docs/rules.md` contains bare quantifiers at lines 277, 377, 610, 955, 1023, 1234, 1273, 1591, 1674, 3304-3317, and elsewhere (grep over `packages/slopvac-lint/docs/rules.md`).

**Walk:** A1/A2/A4=true; one PASSAGE_PROBE unit and one `(unit_id, rule_id)` verdict can carry one rewrite and one score. The question says “Find every,” but the schema has no occurrences array; the model either quotes one (CONFIRM once) or cannot represent the rest. **Wrong:** systematic under-counting and misleading coverage on long docs. **Failure:** PASSAGE_PROBE cardinality, not a score. **Minimal fix:** return `occurrences[]`, each with evidence/scores/rewrite, cap explicitly, and emit `abstain_reason: truncated_document` for the unread remainder.

## Amendments

1. **Admission/preservation enum:** `preservation_reason ∈ {technical_invariant,factual_contrast,formal_legal,operational_normative,l2_clarity,accessibility_repetition,defined_domain_term,generated_schema,quoted_specimen}`. Add `origin` and syntactic-region metadata upstream. Generated, vendored, template, and quoted-specimen judgement is inadmissible unless a rule opts in.
2. **A3 replacement:** “A mechanical core hit does not drop its remainder. Set `core_fired=true`; adjudicate once; PRESERVE/REJECT suppresses the core, CONFIRM emits one deduplicated finding.”
3. **Evidence contract:** `source ∈ unit|context|repo`; defect evidence MUST be unit-local. Context evidence MAY satisfy antecedent/contrast/invariant. Repo evidence MUST carry path, commit/blob SHA, UTF-8 byte offsets, and exact quote. Validate against raw bytes, never a normalized string slice.
4. **Rewrite contract:** add `rewrite_status`. Null rewrite is valid for `withheld_needs_fact` and causes no demotion. Permit protected additions from authorized repo referents. Replace class-wide `rewrite_exempt` with bounded transformations (`class`, `from`, `to`, `evidence_role`).
5. **Thresholds/constants:** remove category-wide HARM/REPAIR constants where rule fixes differ. Set `ste-punctuation.parentheses-misuse.harm = 1`; retain zero only for rules whose compliant fix is deletion with no reader consequence.
6. **Cluster checker:** count non-overlapping evidence components, not raw category labels: `cluster_fail = components>=3 && distinct_categories>=2`.
7. **Probe schema:** one document-rule verdict contains `occurrences[]`; truncation is explicit and counts as unchecked.

## Top-3 false-positive reducers

1. **Origin/region-aware admission plus `generated_schema`/`quoted_specimen`/`operational_normative`.** It removes whole high-density classes before model scoring; `docs/rules.md` alone is 237.5KB and repeats the schema hundreds of times.
2. **Replace A3 with core adjudication.** It directly converts known mechanical false positives such as `must-not-fire.md:15` into PRESERVE/REJECT instead of protecting the core from review.
3. **Cluster by non-overlapping evidence components.** Category names do not establish independence; this prevents one formatting schema from becoming three votes and a build-level REVISE.

## Unsupported

- The assertion that model confidence “correlates with every other axis” has no cited measurement in the design: **UNSUPPORTED** (`rubric-design.md:443-449`).
- Completeness of exactly six preservation classes has no corpus census; repository counterexamples above disprove it.
- The 15/15 executed result names no implementation, command, fixture path, or raw output, so it cannot be independently checked: **UNSUPPORTED** (`rubric-design.md:418-438`).
- Fixed HARM/REPAIR constants are asserted from category names, not measured against rule examples; the parenthesis example contradicts the matrix.

## Open evaluation questions

- On a stratified corpus, how many mechanical-core hits change to PRESERVE/REJECT when their remainders adjudicate them?
- What fraction of judgement candidates occur in generated, vendored, quoted, legal, or operational-normative regions?
- Does overlap-component clustering retain recall on true multi-defect passages while reducing generated-reference gates?
- What occurrence cap preserves recall for 25KB, 100KB, and 250KB document probes, and how is truncated coverage reported?