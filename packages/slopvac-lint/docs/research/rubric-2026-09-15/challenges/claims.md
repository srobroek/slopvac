# Numbered claims under review (use these IDs verbatim)

Source: the design doc at
/Users/sjors/.omp/agent/sessions/-tmp-worktrees-slopvac-work-slopvac-session-20260915/2026-09-15T15-29-48-433Z_01a0a5b0-4791-7626-9e6e-b9bc251434cf/local/rubric-design.md
(531 lines; read it whole with `read <path>:1-260` and `read <path>:260-531`).

Repository checkout for measurements (read-only, never edit):
/Users/sjors/tmp/worktrees/slopvac/research-rubric-review-20260915
(commit df7ba4412387c474dc8ef646a8d594dc44c1c7eb). Rules live in
packages/slopvac-lint/src/slopvac/rules/*.yml; skills in skills/ or plugin dirs;
fixtures and corpora under tests/ and docs/. Discover with glob.

| ID | Claim (design doc section) |
|---|---|
| C1 | One global rubric spine (constant, cacheable prompt prefix) plus per-category packs; no per-rule rubric (§1). |
| C2 | Exactly four scored dimensions FIT, HARM, WARRANT, REPAIR, each integer 0-3 with observable anchors; a per-rule mask lets HARM and REPAIR be declared constants (§2). |
| C3 | Uncertainty and protectedness are gates (abstain, preserve), not dimensions; model confidence is never a dimension (§3, §13). |
| C4 | Every confirm requires WARRANT >= 2 and an exact-substring quote with byte offsets; evidence arity 2 (with named roles antecedent/contrast/invariant/referent) for non-local defects; a finding without quote abstains (§4, §5). |
| C5 | Judgement findings deduct at most JUDGEMENT_MAX_PENALTY = 20 points from the composite and never gate alone; density and cluster gates carry severity (§9). |
| C6 | Cluster gate keyed on >= 2 distinct categories (or any HARM=3) rather than "3 checks in one passage", because within-category rules correlate more than across-category rules (§9). |
| C7 | Six closed preservation classes: technical_invariant, factual_contrast, formal_legal, l2_clarity, accessibility_repetition, defined_domain_term; a pack names only the classes its rules collide with (§3). |
| C8 | Abstention reasons closed list: no_quote, needs_repo_fact, ambiguous_unit, unit_out_of_scope; abstentions count against coverage and are reported in judgement_unchecked (§3). |
| C9 | SPAN packs cap at 8 criteria and 12 units per call; PROBE pack is one consolidated pack of all 18 document/prose-scope rules over the whole document (§7). |
| C10 | Decision algorithm §5: REJECT when fit<=1 or warrant<=1, or harm==0 and repair<3; ERROR iff harm==3 and fit==3 and warrant>=2; WARNING iff harm>=2 and warrant>=2; else SUGGESTION; severity = min(severity, rule ceiling, category ceiling); fix withheld (not finding) when rewrite fails the fact checker (§5). |
| C11 | Fact-preserving rewrite checker over seven protected token classes (numerals/units/versions/dates; code spans/identifiers/paths/flags/commands/URLs; negation polarity; RFC-2119 modality; defined domain terms; named entities/product names; step order/cross-references); removal/alteration forbidden; addition asymmetric (numerals never; others only if already present in document); exemptions rule-relative (§6). |
| C12 | Versioning: rubric_version semver over the spine (MAJOR on dimension/anchor change, MINOR on new gate/evidence role, PATCH on wording); pack_id hash; thresholds and weights live in slopvac.toml, never in rubric text; comparisons valid only under identical (rubric_version, pack_id set, unit set) (§10). |
| C13 | LAMP editor categories map onto existing rule categories; the three gaps (redundant exposition, purple prose, tense sequence) are rule gaps not rubric gaps (§12). |
| C14 | Rejected alternatives (§13): scalar 1-10 quality score; per-rule rubrics; global rubric without category content; per-dimension packs; model confidence as a dimension; register as a dimension; originality/AI-authorship dimension; free-form judgement_question; judgement inside density budget; per-rule cluster threshold; thresholds inside rubric text. |

Verdict vocabulary: KEEP / AMEND / REPLACE. Every verdict needs either a
citation (URL to published work), a repository example (path:line), or a
measurement you ran (command + numbers). Where none exists write
"no evidence found" and mark the claim UNSUPPORTED. Never reason from
plausibility alone. Never propose AI-authorship detection or a fifth
dimension unless a defect cannot be expressed with the four; the taxonomy is
about quality defects, not provenance.
