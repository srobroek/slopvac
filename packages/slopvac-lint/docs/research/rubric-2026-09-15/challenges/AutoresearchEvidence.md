# autoresearch branch evidence (read-only git output)

## diff --stat slopvac-v3-candidate..HEAD

 .gitignore                                         |   4 +
 autoresearch-fixture.json                          |  20 +
 autoresearch.py                                    |  26 +
 autoresearch.sh                                    |   6 +
 bench/arms.json                                    |  10 +
 bench/cases.json                                   |  56 ++
 bench/manifest.json                                |  11 +
 bench/prompt_template.txt                          |   7 +
 bench/rubric.json                                  |  16 +
 bench/runner.py                                    | 854 +++++++++++++++++++++
 bench/shots.json                                   |   9 +
 benchmark_contract.json                            |  33 +
 deterministic_runner.py                            | 284 +++++++
 packages/slopvac-lint/src/slopvac/__init__.py      |  16 +-
 packages/slopvac-lint/src/slopvac/cli.py           |  19 +
 packages/slopvac-lint/src/slopvac/locale.py        |   6 +
 packages/slopvac-lint/src/slopvac/model.py         | 235 +++++-
 packages/slopvac-lint/src/slopvac/profiles.py      |   8 +
 packages/slopvac-lint/src/slopvac/reference.py     |  93 ++-
 packages/slopvac-lint/src/slopvac/rules.py         |  57 +-
 .../slopvac-lint/src/slopvac/rules/ai-residue.yml  |   2 +
 .../src/slopvac/rules/ai-tells-agentic.yml         | 744 +++++++++++++++++-
 .../src/slopvac/rules/ai-tells-figurative.yml      |  32 +
 .../src/slopvac/rules/docs-discipline.yml          |   6 +
 packages/slopvac-lint/src/slopvac/rules/orwell.yml |  21 +
 .../src/slopvac/rules/prose-agency.yml             |  10 +
 .../slopvac-lint/src/slopvac/rules/prose-craft.yml |  56 ++
 .../src/slopvac/rules/prose-discipline.yml         |  96 +++
 .../src/slopvac/rules/prose-format.yml             |   6 +
 .../src/slopvac/rules/prose-inclusive.yml          |   6 +
 .../src/slopvac/rules/prose-inflation.yml          |  24 +
 .../slopvac-lint/src/slopvac/rules/prose-scope.yml |  55 ++
 .../src/slopvac/rules/ste-descriptive.yml          |  59 ++
 .../slopvac-lint/src/slopvac/rules/ste-nouns.yml   |  16 +
 .../src/slopvac/rules/ste-practices.yml            |  63 ++
 .../src/slopvac/rules/ste-procedural.yml           |  10 +
 .../src/slopvac/rules/ste-punctuation.yml          |  21 +
 .../slopvac-lint/src/slopvac/rules/ste-safety.yml  |  20 +
 .../src/slopvac/rules/ste-sentences.yml            |  39 +
 .../slopvac-lint/src/slopvac/rules/ste-verbs.yml   |  42 +
 .../slopvac-lint/src/slopvac/rules/ste-words.yml   | 107 +++
 .../tests/fixtures/rules/empty-docs/category.yml   |   2 +
 .../fixtures/rules/stray-payload/category.yml      |   2 +
 packages/slopvac-lint/tests/test_cli.py            |   2 +
 packages/slopvac-lint/tests/test_engine.py         |  14 +-
 .../slopvac-lint/tests/test_judgement_metadata.py  | 407 +++++++++-
 packages/slopvac-lint/tests/test_reference.py      |  23 +-
 tests/fake_omp.py                                  | 151 ++++
 tests/test_bench_runner.py                         | 626 +++++++++++++++
 49 files changed, 4353 insertions(+), 79 deletions(-)


## show --stat per commit

fc261aeb53 fix(benchmark): count abstentions as terminal scoring errors


 bench/runner.py            |  2 ++
 benchmark_contract.json    |  8 +++++++-
 tests/test_bench_runner.py | 13 +++++++++++++
 3 files changed, 22 insertions(+), 1 deletion(-)

3567284749 refactor(rules): clarify judgement contracts and exception wording


 .../slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml    | 14 ++++++--------
 .../slopvac-lint/src/slopvac/rules/prose-discipline.yml    |  5 ++---
 packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml      |  6 ++----
 3 files changed, 10 insertions(+), 15 deletions(-)

a43178f7f6 feat(rules): add taxonomy and judgement contract metadata to every rule
Every one of the 232 shipped rules now declares a `dimension` (one of the
twelve cross-cutting dimensions) and an `ownership` layer. The 43 seeded
adjudicators name their deterministic seeds in `seed_rule_ids`; the 22
full-document and full-context rules are `document_probe`.

All 65 judgement rules carry a `judgement_contract`: the unit precondition
that admits the question, the preservation classes that outrank the rule,
the dimensions the rubric asks for, the evidence arity, the severity ceiling
a confirm may reach, and whether the fix may change a protected token.

24 judgement rules had their exception tokens swallowed into the
`judgement_question` folded scalar as orphan list items. Those tokens are
now real `exceptions:` lists.

No pattern, tier, severity, allowlist, message, or example content changed.


 .../slopvac-lint/src/slopvac/rules/ai-residue.yml  |   2 +
 .../src/slopvac/rules/ai-tells-agentic.yml         | 615 +++++++++++++++++++++
 .../src/slopvac/rules/ai-tells-figurative.yml      |  32 ++
 .../src/slopvac/rules/docs-discipline.yml          |   6 +
 packages/slopvac-lint/src/slopvac/rules/orwell.yml |  21 +
 .../src/slopvac/rules/prose-agency.yml             |  10 +
 .../slopvac-lint/src/slopvac/rules/prose-craft.yml |  56 ++
 .../src/slopvac/rules/prose-discipline.yml         |  97 ++++
 .../src/slopvac/rules/prose-format.yml             |   6 +
 .../src/slopvac/rules/prose-inclusive.yml          |   6 +
 .../src/slopvac/rules/prose-inflation.yml          |  24 +
 .../slopvac-lint/src/slopvac/rules/prose-scope.yml |  10 +
 .../src/slopvac/rules/ste-descriptive.yml          |  59 ++
 .../slopvac-lint/src/slopvac/rules/ste-nouns.yml   |  18 +
 .../src/slopvac/rules/ste-practices.yml            |  63 +++
 .../src/slopvac/rules/ste-procedural.yml           |  10 +
 .../src/slopvac/rules/ste-punctuation.yml          |  21 +
 .../slopvac-lint/src/slopvac/rules/ste-safety.yml  |  20 +
 .../src/slopvac/rules/ste-sentences.yml            |  39 ++
 .../slopvac-lint/src/slopvac/rules/ste-verbs.yml   |  42 ++
 .../slopvac-lint/src/slopvac/rules/ste-words.yml   | 107 ++++
 21 files changed, 1264 insertions(+)

60c7822434 feat(slopvac-lint): type rule dimension, layer ownership, and the judgement contract


 packages/slopvac-lint/src/slopvac/__init__.py      |  16 +-
 packages/slopvac-lint/src/slopvac/cli.py           |  19 +
 packages/slopvac-lint/src/slopvac/locale.py        |   6 +
 packages/slopvac-lint/src/slopvac/model.py         | 235 +++++++++++-
 packages/slopvac-lint/src/slopvac/reference.py     |  93 ++++-
 packages/slopvac-lint/src/slopvac/rules.py         |  57 ++-
 .../tests/fixtures/rules/empty-docs/category.yml   |   2 +
 .../fixtures/rules/stray-payload/category.yml      |   2 +
 packages/slopvac-lint/tests/test_cli.py            |   2 +
 packages/slopvac-lint/tests/test_engine.py         |  14 +-
 .../slopvac-lint/tests/test_judgement_metadata.py  | 407 +++++++++++++++++++--
 packages/slopvac-lint/tests/test_reference.py      |  23 +-
 12 files changed, 835 insertions(+), 41 deletions(-)

1473ba824f autoresearch: harness setup
Benchmark entrypoint: bash autoresearch.sh
Goal: Migrate all slopvac rules to a validated prose-dimension and execution-ownership taxonomy, structure every judgement rule for candidate-routed online review, and preserve perfect formulaic-heading behavior.

 deterministic_runner.py | 1 +
 1 file changed, 1 insertion(+)

4a7ef71c8d autoresearch: harness setup
Benchmark entrypoint: bash autoresearch.sh
Goal: Migrate all slopvac rules to a validated prose-dimension and execution-ownership taxonomy, structure every judgement rule for candidate-routed online review, and preserve perfect formulaic-heading behavior.

 deterministic_runner.py | 4 +---
 1 file changed, 1 insertion(+), 3 deletions(-)

c30c70f504 feat(benchmark): validate taxonomy contract metrics


 benchmark_contract.json |  27 ++++++++++
 deterministic_runner.py | 131 +++++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 156 insertions(+), 2 deletions(-)

90924e283d refactor(lint): remove duplicate contrastive inversion frame rule


 .../src/slopvac/rules/ai-tells-agentic.yml         | 75 +++++++++++-----------
 .../slopvac-lint/src/slopvac/rules/prose-scope.yml |  2 +-
 2 files changed, 38 insertions(+), 39 deletions(-)

cace892253 feat(lint): detect formulaic slogan headings
Two pattern rules for the title-shaped formulae an agent reaches for when a
section needs a name and no fact is available: the comma-joined
subject-verb pair (prose-scope.formulaic-subject-verb-slogan) and the
universal claim (ai-tells-agentic.formulaic-universal-heading), plus the
ai-tells-agentic category that carries the second one and its entries in
the three profile policy tables.

The previous attempt crashed the CLI before it emitted any JSON. Its
examples list carried a `good`-only entry, `Example.bad` is required, and
the loader's eager validation turned that into a ruleset error on stderr
with an empty stdout. It also filed the rule under the ai-tells-structure
category, so its qualified id was not the one it claimed.

Both rules match syntax rather than phrases, and each shape condition is
what keeps a real class invariant out: the predicate sits against the bare
subject, the complement is at least two words, and the match runs to the
end of the block through word characters only, so terminal punctuation
excludes it. A heading carries none; a body sentence does.

`scope: paragraph`, not `heading`: the native engine's paragraph scope
already covers every rendered block including headings, while heading
scope compiles to a Vale payload and Vale then owns the rule, which leaves
it unchecked whenever Vale does not run.


 packages/slopvac-lint/src/slopvac/profiles.py      |  8 +++
 .../src/slopvac/rules/ai-tells-agentic.yml         | 84 ++++++++++++++--------
 .../slopvac-lint/src/slopvac/rules/prose-scope.yml | 74 +++++++++++--------
 3 files changed, 109 insertions(+), 57 deletions(-)

8aa80ba428 feat(lint): add formulaic heading detection rules


 .../src/slopvac/rules/ai-tells-agentic.yml         | 28 +++++++++++++++++++++
 .../slopvac-lint/src/slopvac/rules/prose-scope.yml | 29 ++++++++++++++++++++++
 2 files changed, 57 insertions(+)

3736b25433 feat: add deterministic offline benchmark runner as default


 autoresearch.py         |  15 ++++-
 autoresearch.sh         |   7 +--
 deterministic_runner.py | 158 ++++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 173 insertions(+), 7 deletions(-)

b83a85257b Replace unavailable GPT-OSS benchmark arm


 bench/arms.json     | 2 +-
 bench/manifest.json | 2 +-
 2 files changed, 2 insertions(+), 2 deletions(-)

86af551c0d feat(runner): add partition and execution selectors


 autoresearch.sh |   9 ++--
 bench/runner.py | 125 ++++++++++++++++++++++++++++++++++++++++++--------------
 2 files changed, 100 insertions(+), 34 deletions(-)

939fc945c1 feat(bench): retain evidence and validate benchmark outcomes


 .gitignore                 |   4 +
 autoresearch.sh            |   5 +-
 bench/runner.py            | 935 +++++++++++++++++++++++++++++++++++++--------
 tests/fake_omp.py          | 151 ++++++++
 tests/test_bench_runner.py | 613 +++++++++++++++++++++++++++++
 5 files changed, 1555 insertions(+), 153 deletions(-)

c21a6ade84 Reject malformed benchmark result sets


 bench/runner.py | 25 +++++++++++++++++++++----
 1 file changed, 21 insertions(+), 4 deletions(-)

5f970b2720 Fix benchmark parser normalization


 bench/runner.py | 52 +++++++++++++++++++++++++++++++---------------------
 1 file changed, 31 insertions(+), 21 deletions(-)

8f8a6592f5 refactor(bench): simplify benchmark runner implementation


 bench/runner.py | 403 +++++++++++++++++---------------------------------------
 1 file changed, 124 insertions(+), 279 deletions(-)

9ae7a4abfa fix(bench): parse assistant payloads and normalize usage metrics


 bench/runner.py | 67 ++++++++++++++++++++++++++++++++++++++++++++++++---------
 1 file changed, 57 insertions(+), 10 deletions(-)

2cdd00b6e4 refactor: delegate autoresearch entry point to canonical segment


 autoresearch.py           | 131 +------------------------
 autoresearch.sh           |   5 +-
 bench/arms.json           |  10 ++
 bench/cases.json          |  56 +++++++++++
 bench/manifest.json       |  11 +++
 bench/prompt_template.txt |   7 ++
 bench/rubric.json         |  16 ++++
 bench/runner.py           | 237 ++++++++++++++++++++++++++++++++++++++++++++++
 bench/shots.json          |   9 ++
 9 files changed, 352 insertions(+), 130 deletions(-)

f05bffa9df autoresearch: harness setup
Benchmark entrypoint: bash autoresearch.sh
Goal: Evaluate a general local instruction model against a structured multi-shot prose-quality rubric, then use the evidence to improve slopvac's deterministic and non-deterministic detection of formulaic subject-verb slogans while preserving natural headings and technical controls.

 autoresearch-fixture.json | 18 +++++++++---------
 1 file changed, 9 insertions(+), 9 deletions(-)

5efdbd2730 autoresearch: harness setup
Benchmark entrypoint: bash autoresearch.sh
Goal: Improve slopvac so it flags formulaic subject-verb slogans and synthetic contrast headings while preserving natural noun-phrase headings, factual contrasts, technical invariants, and genre-appropriate prose; use cited modern writing research to propose deterministic rules and non-deterministic review criteria without claiming authorship detection.

 autoresearch-fixture.json |  20 +++++++
 autoresearch.py           | 138 ++++++++++++++++++++++++++++++++++++++++++++++
 autoresearch.sh           |   6 ++
 3 files changed, 164 insertions(+)


## full diffs of key commits


### 60c7822434

60c7822434 feat(slopvac-lint): type rule dimension, layer ownership, and the judgement contract


diff --git a/packages/slopvac-lint/src/slopvac/__init__.py b/packages/slopvac-lint/src/slopvac/__init__.py
index 860fc044d1..24a4d4d14a 100644
--- a/packages/slopvac-lint/src/slopvac/__init__.py
+++ b/packages/slopvac-lint/src/slopvac/__init__.py
@@ -10,14 +10,28 @@ carrying a parallel prose catalog.
 __version__ = "2.3.2"  # x-release-please-version
 
 from .config import Config, Profile, Severity, load_config, resolve_for
-from .model import Category, DocumentScore, Finding, Rule, RuleKind
+from .model import (
+    Category,
+    Dimension,
+    DocumentScore,
+    Finding,
+    JudgementContract,
+    JudgementDimension,
+    Ownership,
+    Rule,
+    RuleKind,
+)
 from .rules import RuleSet, load_ruleset
 
 __all__ = [
     "Category",
     "Config",
+    "Dimension",
     "DocumentScore",
     "Finding",
+    "JudgementContract",
+    "JudgementDimension",
+    "Ownership",
     "Profile",
     "Rule",
     "RuleKind",
diff --git a/packages/slopvac-lint/src/slopvac/cli.py b/packages/slopvac-lint/src/slopvac/cli.py
index 52d156f9e5..2d84f25561 100644
--- a/packages/slopvac-lint/src/slopvac/cli.py
+++ b/packages/slopvac-lint/src/slopvac/cli.py
@@ -514,6 +514,11 @@ def explain(
         f"kind: {rule.kind.value}   severity: {rule.severity.value}   scope: {rule.scope.value}"
     )
     console.print("tiers: " + "  ".join(f"{k}={v.value}" for k, v in rule.tiers.items()))
+    console.print(
+        f"dimension: {rule.dimension.value}   layer: {rule.ownership.value}"
+    )
+    if rule.seed_rule_ids:
+        console.print("adjudicates: " + "  ".join(rule.seed_rule_ids))
     # `message` is a template. Printed raw it shows `{replacement}`, which reads as a
     # bug; the slots are shown as `<name>` so it is clear they are filled per finding.
     console.print("\n" + rule.message.replace("{", "<").replace("}", ">"))
@@ -523,6 +528,20 @@ def explain(
         console.print(f"\n[bold]Fix[/]: {rule.fix}")
     if rule.judgement_question:
         console.print(f"\n[bold]Decide by asking[/]: {rule.judgement_question}")
+    # The adjudication contract, printed for the same reason the exception list is:
+    # a reviewer that has to scrape these terms out of Rich-rendered prose will
+    # invent its own, and then the ceiling stops capping anything.
+    if rule.judgement_contract is not None:
+        contract = rule.judgement_contract
+        console.print(f"\n[bold]Applies when[/]: {contract.admission}")
+        console.print(f"[bold]Must not flag[/]: {contract.protects}")
+        console.print(
+            "scored on: "
+            + ", ".join(dim.value for dim in contract.dims)
+            + f"   evidence: {contract.evidence_arity}"
+            + f"   confirms at most: {contract.judgement_ceiling.value}"
+            + f"   rewrite exempt: {'yes' if contract.rewrite_exempt else 'no'}"
+        )
     if rule.exceptions:
         console.print("\n[bold]Named exceptions[/] (a suppression must cite one):")
         for name in rule.exceptions:
diff --git a/packages/slopvac-lint/src/slopvac/locale.py b/packages/slopvac-lint/src/slopvac/locale.py
index eb6f444de2..7f5c67f1a6 100644
--- a/packages/slopvac-lint/src/slopvac/locale.py
+++ b/packages/slopvac-lint/src/slopvac/locale.py
@@ -273,6 +273,12 @@ def build_spelling_rule(tag: str) -> dict | None:
         "id": "spelling",
         "name": f"Use {tag} spelling",
         "kind": "substitution",
+        # A spelling variant is the wrong WORD for this project, not a defect of
+        # sentence shape, so it sits with the other vocabulary rules under
+        # `wording`. A substitution map is executed by a checker, so the layer is
+        # deterministic and there is nothing for a reviewer to adjudicate.
+        "dimension": "wording",
+        "ownership": "deterministic",
         "severity": "warning",
         "message": f'Use the {tag} spelling "{{replacement}}".',
         "scope": "prose",
diff --git a/packages/slopvac-lint/src/slopvac/model.py b/packages/slopvac-lint/src/slopvac/model.py
index 292ecd7674..a6b2ef18fe 100644
--- a/packages/slopvac-lint/src/slopvac/model.py
+++ b/packages/slopvac-lint/src/slopvac/model.py
@@ -11,6 +11,7 @@ substitution rule needs no Python; only a genuinely new detection strategy does.
 
 from __future__ import annotations
 
+import re
 from enum import Enum
 from typing import Literal
 
@@ -88,6 +89,141 @@ class TextType(str, Enum):
 # the language's own conventions.
 Genre = Literal["consumer", "internal", "change-comms", "reference", "informal"]
 
+
+class Dimension(str, Enum):
+    """The rubric-facing axis: what KIND of defect a rule names, independent of
+    which checker executes it.
+
+    Single-valued per rule and orthogonal to `category`. `category` stays the unit
+    a user enables, weights, and scores by; `dimension` is the unit a rubric and a
+    dimension-keyed pack select by. The two are genuinely different partitions --
+    `wording` spans 13 categories and every category spans between 1 and 6
+    dimensions -- so a single-valued `dimension` is what makes dimension-keyed
+    packs disjoint by construction.
+
+    Seven of the twelve carry a LAMP category as their primary label; the other
+    five (`agency`, `veracity`, `scope`, `presentation`, `inclusion`) name defects
+    LAMP has no category for, which is why LAMP is a crosswalk here rather than
+    the vocabulary itself.
+    """
+
+    SPECIFICITY = "specificity"
+    INFLATION = "inflation"
+    STALENESS = "staleness"
+    REDUNDANCY = "redundancy"
+    ARCHITECTURE = "architecture"
+    WORDING = "wording"
+    CONSISTENCY = "consistency"
+    AGENCY = "agency"
+    VERACITY = "veracity"
+    SCOPE = "scope"
+    PRESENTATION = "presentation"
+    INCLUSION = "inclusion"
+
+
+class Ownership(str, Enum):
+    """Which layer settles the rule.
+
+    DETERMINISTIC        -- a checker executes it and the judgement layer never
+                            sees it.
+    SEEDED_ADJUDICATION  -- adjudication of a span some deterministic rule already
+                            found. The existing `-core`/`-remainder` pair,
+                            generalised: `seed_rule_ids` names the generators.
+    DOCUMENT_PROBE       -- no deterministic trigger at all; the rule is handed a
+                            block or a document and must locate its own span.
+
+    Three modes rather than two, because "not mechanizable" hides the distinction
+    that decides how a unit reaches the reviewer: a seeded rule is handed a span,
+    a probe is handed a passage and may find nothing.
+    """
+
+    DETERMINISTIC = "deterministic"
+    SEEDED_ADJUDICATION = "seeded_adjudication"
+    DOCUMENT_PROBE = "document_probe"
+
+
+class JudgementDimension(str, Enum):
+    """A scored axis of the judgement rubric. Upper-case because these are the
+    rubric's own names, quoted verbatim in packs and verdicts."""
+
+    FIT = "FIT"
+    HARM = "HARM"
+    WARRANT = "WARRANT"
+    REPAIR = "REPAIR"
+
+
+class JudgementContract(BaseModel):
+    """What a judgement rule promises the adjudication layer.
+
+    Every field is load-bearing at call time, which is why none is optional: the
+    pack cannot be generated without `admission` and `protects`, the verdict
+    cannot be scored without `dims`, a verdict cannot be checked without
+    `evidence_arity`, and a confirm cannot be assigned a severity without
+    `judgement_ceiling`. A rule that declares none of this is a rule the layer
+    would have to guess at, and guessing is what the ceiling exists to stop.
+    """
+
+    model_config = ConfigDict(extra="forbid")
+
+    admission: str = Field(
+        description="What must be true of the unit for the question to apply. "
+        "Scope legality and double-jeopardy, in words a pack can print.",
+    )
+    protects: str = Field(
+        description="The correct prose this rule must not flag. Names the "
+        "preservation classes that outrank it, so the carve-out is stated once "
+        "per rule rather than reprinted in every pack.",
+    )
+    dims: list[JudgementDimension] = Field(
+        description="The rubric axes this rule is scored on. A rule asks two or "
+        "three, not four: asking for a score nothing depends on invents variance "
+        "that later reads as signal.",
+    )
+    evidence_arity: int = Field(
+        ge=1,
+        description="How many located spans a verdict must return. Non-local "
+        "defects need two -- a repeat needs its antecedent, a term "
+        "inconsistency needs both spellings.",
+    )
+    judgement_ceiling: Severity = Field(
+        description="The most severe level a confirm may reach. This is how a "
+        "judgement finding reaches `error` without the rule carrying a mechanical "
+        "severity it cannot earn; a build-failing model finding has to be named "
+        "rule by rule.",
+    )
+    rewrite_exempt: bool = Field(
+        description="Whether this rule's fix may legitimately alter a protected "
+        "token. False for almost every rule: a rewrite that edits a number, a "
+        "path, or a negation is rejected mechanically rather than editorially.",
+    )
+
+    @model_validator(mode="after")
+    def _check_contract(self) -> JudgementContract:
+        for name in ("admission", "protects"):
+            if not getattr(self, name).strip():
+                raise ValueError(f"`judgement_contract.{name}` must not be empty")
+        if not self.dims:
+            raise ValueError(
+                "`judgement_contract.dims` must name at least one scored axis; a "
+                "rule scored on nothing cannot be confirmed"
+            )
+        seen: set[JudgementDimension] = set()
+        for dim in self.dims:
+            if dim in seen:
+                raise ValueError(
+                    f"`judgement_contract.dims` repeats {dim.value}; a weighted "
+                    "axis counted twice is not the axis it claims to be"
+                )
+            seen.add(dim)
+        if self.judgement_ceiling is Severity.OFF:
+            raise ValueError(
+                "`judgement_contract.judgement_ceiling` cannot be `off`: a "
+                "ceiling of off makes every confirm unreachable, which is what "
+                "`severity: off` on the rule already says"
+            )
+        return self
+
+
 class Provenance(BaseModel):
     """Where a rule came from. Required, because a rule nobody can trace is a
     rule nobody can argue with.
@@ -139,6 +275,32 @@ class Rule(BaseModel):
     )
     name: str = Field(description="Short imperative label.")
     kind: RuleKind
+
+    # --- taxonomy and layer; required on every rule ---------------------------
+    # Required rather than defaulted. A default would be silently wrong for most
+    # of the catalog, and a taxonomy that guesses is a taxonomy nobody can select
+    # by: the whole point of `dimension` is that a dimension-keyed pack contains
+    # exactly the rules that name that defect.
+    dimension: Dimension = Field(
+        description="What kind of defect this rule names. Orthogonal to "
+        "`category`, which stays the unit users enable and score by.",
+    )
+    ownership: Ownership = Field(
+        description="Which layer settles the rule. Must agree with `kind`: a "
+        "mechanical kind is `deterministic`, a judgement rule is "
+        "`seeded_adjudication` or `document_probe`.",
+    )
+    seed_rule_ids: list[str] = Field(
+        default_factory=list,
+        description="Fully qualified ids of the deterministic rules whose matches "
+        "this rule adjudicates. Required and non-empty for "
+        "`ownership=seeded_adjudication`, empty for every other mode.",
+    )
+    judgement_contract: JudgementContract | None = Field(
+        default=None,
+        description="Required for kind=judgement, forbidden elsewhere. What the "
+        "adjudication layer needs in order to call the rule at all.",
+    )
     severity: Severity = Field(
         default=Severity.WARNING,
         description="The rule's shipped level. A category cap can lower it, "
@@ -226,6 +388,7 @@ class Rule(BaseModel):
             "metric": RuleKind.METRIC,
             "threshold": RuleKind.METRIC,
             "judgement_question": RuleKind.JUDGEMENT,
+            "judgement_contract": RuleKind.JUDGEMENT,
         }
         for name, owner in owners.items():
             if getattr(self, name) is not None and self.kind is not owner:
@@ -237,17 +400,71 @@ class Rule(BaseModel):
             raise ValueError(f"kind={self.kind.value} requires `{field}`")
         if self.kind is RuleKind.METRIC and self.threshold is None:
             raise ValueError("kind=metric requires `threshold`")
-        if self.kind is RuleKind.JUDGEMENT and self.exceptions:
+
+        # `exceptions` on a judgement rule USED to be a load error, on the
+        # reasoning that a rule which emits no finding has nothing to suppress.
+        # That was true of the carried-prose layer and is false of the
+        # adjudication layer: a confirmed judgement finding is a finding, and the
+        # named exception is what lets an author cite `quotation` against it
+        # instead of overriding it unnamed. Deterministic exception handling is
+        # unchanged; see engine.py, which still requires an annotation to cite a
+        # name this list carries.
+
+        # A judgement rule cannot fire mechanically, so it cannot own a
+        # mechanical severity. `judgement_contract.judgement_ceiling` is where its
+        # confirmable level lives.
+        if self.kind is RuleKind.JUDGEMENT:
+            if not self.judgement_question:
+                raise ValueError("kind=judgement requires `judgement_question`")
+            if self.judgement_contract is None:
+                raise ValueError(
+                    f"{self.id}: kind=judgement requires `judgement_contract`; a "
+                    "rule the adjudication layer cannot admit, score, or cap is a "
+                    "rule it would have to guess at"
+                )
+            if self.ownership is Ownership.DETERMINISTIC:
+                raise ValueError(
+                    f"{self.id}: kind=judgement cannot be "
+                    f"ownership={Ownership.DETERMINISTIC.value}; no checker "
+                    "executes a judgement rule"
+                )
+            if self.severity is not Severity.OFF:
+                object.__setattr__(self, "severity", Severity.SUGGESTION)
+        elif self.ownership is not Ownership.DETERMINISTIC:
             raise ValueError(
-                f"{self.id}: kind=judgement cannot declare `exceptions`; "
-                "judgement rules never emit findings to suppress"
+                f"{self.id}: kind={self.kind.value} is executed by a checker, so "
+                f"ownership must be {Ownership.DETERMINISTIC.value}, not "
+                f"{self.ownership.value}"
             )
-        if self.kind is RuleKind.JUDGEMENT and not self.judgement_question:
-            raise ValueError("kind=judgement requires `judgement_question`")
-        if self.kind is RuleKind.JUDGEMENT and self.severity is not Severity.OFF:
-            # A judgement rule cannot fire mechanically; letting it carry a real
-            # severity would imply the linter checks it.
-            object.__setattr__(self, "severity", Severity.SUGGESTION)
+
+        # Seeds are the generalised `-core`/`-remainder` link. Only a seeded rule
+        # has them, and it is useless without them: with no generator, nothing
+        # ever hands it a span.
+        if self.ownership is Ownership.SEEDED_ADJUDICATION:
+            if not self.seed_rule_ids:
+                raise ValueError(
+                    f"{self.id}: ownership="
+                    f"{Ownership.SEEDED_ADJUDICATION.value} requires at least one "
+                    "`seed_rule_ids` entry; with no generator nothing hands this "
+                    "rule a span"
+                )
+        elif self.seed_rule_ids:
+            raise ValueError(
+                f"{self.id}: `seed_rule_ids` is not valid for "
+                f"ownership={self.ownership.value}; only "
+                f"{Ownership.SEEDED_ADJUDICATION.value} adjudicates another "
+                "rule's matches"
+            )
+        seen_seeds: set[str] = set()
+        for seed in self.seed_rule_ids:
+            if not re.fullmatch(r"[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*", seed):
+                raise ValueError(
+                    f"{self.id}: seed '{seed}' is not a qualified "
+                    "`category.rule` id"
+                )
+            if seed in seen_seeds:
+                raise ValueError(f"{self.id}: seed '{seed}' is named twice")
+            seen_seeds.add(seed)
         return self
 
     def tier_for(self, profile: str) -> Tier:
diff --git a/packages/slopvac-lint/src/slopvac/reference.py b/packages/slopvac-lint/src/slopvac/reference.py
index ad815a1f91..5287a134e2 100644
--- a/packages/slopvac-lint/src/slopvac/reference.py
+++ b/packages/slopvac-lint/src/slopvac/reference.py
@@ -18,6 +18,11 @@ mechanical rule is a matter of opinion. `RuleKind.JUDGEMENT` is the whole of the
 non-deterministic set -- it is defined as the rules no linter can check -- so the
 partition needs no heuristic.
 
+`ownership` refines the non-deterministic half into the two shapes that differ in
+how a unit reaches the reviewer: a seeded rule is handed a span some checked rule
+already found, a probe is handed a passage and may locate nothing. That is a fact
+about the rule a planner needs, so it is printed rather than derived.
+
 REDISTRIBUTION IS SCOPED. Rules derived from ASD-STE100 cite a rule NUMBER and
 nothing else: no rule prose, no worked examples from the specification, and no
 part of its wordlist. Those citations are facts about where an idea came from.
@@ -28,7 +33,7 @@ from __future__ import annotations
 
 from collections import defaultdict
 
-from .model import Rule, RuleKind
+from .model import Dimension, Ownership, Rule, RuleKind
 from .rules import RuleSet
 
 #: Every kind except JUDGEMENT. Derived rather than listed, so a new kind added to
@@ -46,6 +51,14 @@ _KIND_BLURB = {
     RuleKind.JUDGEMENT: "not mechanizable; a reader or a reviewing agent settles it",
 }
 
+_OWNERSHIP_BLURB = {
+    Ownership.DETERMINISTIC: "a checker executes it; no reviewer is involved",
+    Ownership.SEEDED_ADJUDICATION: "a reviewer settles a span a deterministic rule "
+    "already found",
+    Ownership.DOCUMENT_PROBE: "no deterministic trigger; a reviewer reads a block "
+    "and locates the span",
+}
+
 _TIER_ORDER = ("strict", "normal", "relaxed")
 
 
@@ -90,6 +103,30 @@ def _tier_cell(rule: Rule) -> str:
     )
 
 
+def _contract_facts(rule: Rule) -> list[str]:
+    """The adjudication contract, in full.
+
+    Printed rather than summarised because these are the terms a reviewing agent
+    is held to. A reader who can see `dims` and `evidence_arity` can tell whether
+    a finding they disagree with broke the contract or kept it; a reader shown
+    only "judgement" cannot.
+    """
+    contract = rule.judgement_contract
+    if contract is None:
+        return []
+    dims = ", ".join(dim.value for dim in contract.dims)
+    spans = "span" if contract.evidence_arity == 1 else "spans"
+    return [
+        f"- **Applies when.** {contract.admission}",
+        f"- **Must not flag.** {contract.protects}",
+        f"- **Scored on.** {dims}",
+        f"- **Evidence.** {contract.evidence_arity} located {spans}",
+        f"- **Confirms at most.** {contract.judgement_ceiling.value}",
+        "- **Rewrite may alter a protected token.** "
+        + ("yes" if contract.rewrite_exempt else "no"),
+    ]
+
+
 def _rule_section(rule: Rule) -> list[str]:
     lines = [f"#### `{rule.qualified_id}`", "", rule.name, ""]
 
@@ -98,6 +135,8 @@ def _rule_section(rule: Rule) -> list[str]:
         f"- **Ships as.** {rule.severity.value}",
         f"- **strict / normal / relaxed.** {_tier_cell(rule)}",
         f"- **Scope.** {rule.scope.value}",
+        f"- **Dimension.** {rule.dimension.value}",
+        f"- **Layer.** {rule.ownership.value} — {_OWNERSHIP_BLURB[rule.ownership]}",
     ]
     if rule.text_type and rule.text_type.value != "any":
         facts.append(f"- **Applies to.** {rule.text_type.value} text")
@@ -109,8 +148,12 @@ def _rule_section(rule: Rule) -> list[str]:
             f"- **Suppressible with.** {named} — any other reason is reported "
             f"rather than honoured"
         )
+    if rule.seed_rule_ids:
+        seeds = ", ".join(f"`{seed}`" for seed in rule.seed_rule_ids)
+        facts.append(f"- **Adjudicates matches of.** {seeds}")
     if rule.kind is RuleKind.JUDGEMENT and rule.judgement_question:
         facts.append(f"- **Question.** {rule.judgement_question}")
+    facts.extend(_contract_facts(rule))
     facts.append(f"- **Source.** {_provenance_line(rule)}")
     lines.extend(facts)
 
@@ -201,6 +244,35 @@ def _summary_table(ruleset: RuleSet, rules: list[Rule]) -> list[str]:
     return lines
 
 
+def _dimension_table(rules: list[Rule]) -> list[str]:
+    """Rules per dimension, split by which layer settles them.
+
+    The second axis of the catalog, and the one a reviewer selects by: a
+    dimension-keyed pack contains exactly the rules that name that defect, so the
+    counts here are the size of each pack. Dimensions with no rules are omitted
+    rather than printed as zeros -- a row a reader cannot act on is noise, and the
+    enum is the place to look for the full vocabulary.
+    """
+    lines = [
+        "| Dimension | Rules | Checked | Seeded adjudication | Document probe |",
+        "| --- | --: | --: | --: | --: |",
+    ]
+    for dimension in Dimension:
+        owned = [r for r in rules if r.dimension is dimension]
+        if not owned:
+            continue
+        counts = {
+            mode: sum(1 for r in owned if r.ownership is mode) for mode in Ownership
+        }
+        lines.append(
+            f"| `{dimension.value}` | {len(owned)} "
+            f"| {counts[Ownership.DETERMINISTIC]} "
+            f"| {counts[Ownership.SEEDED_ADJUDICATION]} "
+            f"| {counts[Ownership.DOCUMENT_PROBE]} |"
+        )
+    return lines
+
+
 def render_reference(ruleset: RuleSet) -> str:
     """The whole rules reference, as markdown.
 
@@ -259,6 +331,25 @@ def render_reference(ruleset: RuleSet) -> str:
             "Weight scales a category's contribution to the overall score. A weight "
             "of 0 makes the category informational: it still reports, and it cannot "
             "fail the score gate.",
+            "",
+            "## Dimensions",
+            "",
+            "`category` is the unit you enable, disable, and weight. `dimension` "
+            "is the second axis: what kind of defect the rule names. The two are "
+            "different partitions on purpose — a category spans several "
+            "dimensions and a dimension spans several categories — so a review "
+            "selects by dimension and a build configures by category.",
+            "",
+            "The layer columns say who settles the rule. **Checked** is executed "
+            "by a checker. **Seeded adjudication** is a reader settling a span "
+            "some checked rule already found, and each such rule names its "
+            "generators. **Document probe** has no mechanical trigger at all.",
+            "",
+        ]
+    )
+    lines.extend(_dimension_table(ruleset.rules))
+    lines.extend(
+        [
             "",
             "## Checked rules",
             "",
diff --git a/packages/slopvac-lint/src/slopvac/rules.py b/packages/slopvac-lint/src/slopvac/rules.py
index d2cd650a93..a7480b2445 100644
--- a/packages/slopvac-lint/src/slopvac/rules.py
+++ b/packages/slopvac-lint/src/slopvac/rules.py
@@ -10,6 +10,12 @@ compiled, and every `examples[].bad` is asserted to match while `examples[].good
 is asserted not to. A rule whose pattern no longer fires is a rule that silently
 passes every document, which is indistinguishable from clean prose -- the failure
 mode this project already documented for unsynced Vale styles.
+
+Cross-rule references are resolved once the WHOLE registry is in memory. A seeded
+adjudication rule names the deterministic rules that generate its candidates, and
+those seeds cross category and file boundaries, so a per-file check would reject
+the forward references the catalog contains. An unresolvable seed is the same
+failure in a different place: the rule looks configured and adjudicates nothing.
 """
 
 from __future__ import annotations
@@ -78,13 +84,6 @@ def _load_documents(text: str, origin: str) -> list[dict]:
 
 
 def _build_category(data: dict, origin: str) -> Category:
-    for raw_rule in data.get("rules", []):
-        if raw_rule.get("kind") == RuleKind.JUDGEMENT.value and raw_rule.get("exceptions"):
-            rule_id = raw_rule.get("id", "<unknown>")
-            raise RuleLoadError(
-                f"{origin}: rule '{rule_id}': kind=judgement cannot declare "
-                "`exceptions`; judgement rules never emit findings to suppress"
-            )
     try:
         category = Category.model_validate(data)
     except Exception as exc:
@@ -146,6 +145,48 @@ def _verify_examples(category: Category, origin: str) -> list[str]:
     return problems
 
 
+def _verify_seed_references(ruleset: RuleSet) -> list[str]:
+    """Resolve every `seed_rule_ids` entry against the WHOLE registry.
+
+    Deferred until every file has loaded, because a seed legitimately crosses
+    category and file boundaries: `ste-safety.risk-level-word-missing-or-wrong`
+    adjudicates `ste-safety.safety-block-missing-consequence`, but nothing stops a
+    seeded rule from naming a generator in another file, and the loader reads
+    files in name order. Checking per file would reject the forward references
+    that the catalog actually contains.
+
+    A seed that does not resolve is the failure this whole layer exists to
+    prevent: the rule looks configured, no generator ever hands it a span, and it
+    silently adjudicates nothing -- indistinguishable from a document with no
+    defects. Reported rather than raised, so all of them surface at once.
+    """
+    problems: list[str] = []
+    by_id = {rule.qualified_id: rule for rule in ruleset.rules}
+
+    for rule in ruleset.rules:
+        for seed in rule.seed_rule_ids:
+            target = by_id.get(seed)
+            if target is None:
+                problems.append(
+                    f"{rule.qualified_id}: seed '{seed}' names no rule in the "
+                    f"loaded ruleset"
+                )
+                continue
+            if target is rule:
+                problems.append(
+                    f"{rule.qualified_id}: seed '{seed}' is the rule itself; a "
+                    f"rule cannot generate its own candidates"
+                )
+                continue
+            if target.kind is RuleKind.JUDGEMENT:
+                problems.append(
+                    f"{rule.qualified_id}: seed '{seed}' is kind=judgement, so "
+                    f"it produces no span to adjudicate; a seed must be a "
+                    f"deterministic rule"
+                )
+    return problems
+
+
 def inject_locale_rule(ruleset: RuleSet, tag: str, allow: list[str] | None = None) -> str | None:
     """Add the generated spelling rule for `tag` to the ste-words category.
 
@@ -234,6 +275,8 @@ def load_ruleset(
                 problems.extend(_verify_examples(category, origin))
             ruleset.categories[category.id] = category
 
+    problems.extend(_verify_seed_references(ruleset))
+
     if problems:
         raise RuleLoadError(
             "the ruleset failed self-verification:\n  " + "\n  ".join(problems)
diff --git a/packages/slopvac-lint/tests/fixtures/rules/empty-docs/category.yml b/packages/slopvac-lint/tests/fixtures/rules/empty-docs/category.yml
index feff1a35bc..b39bc97d57 100644
--- a/packages/slopvac-lint/tests/fixtures/rules/empty-docs/category.yml
+++ b/packages/slopvac-lint/tests/fixtures/rules/empty-docs/category.yml
@@ -7,6 +7,8 @@ rules:
   - id: only-rule
     name: Keep a valid pattern
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     message: unused
     pattern: '\bxyzzy\b'
     examples:
diff --git a/packages/slopvac-lint/tests/fixtures/rules/stray-payload/category.yml b/packages/slopvac-lint/tests/fixtures/rules/stray-payload/category.yml
index 625b260aee..dbae4daa74 100644
--- a/packages/slopvac-lint/tests/fixtures/rules/stray-payload/category.yml
+++ b/packages/slopvac-lint/tests/fixtures/rules/stray-payload/category.yml
@@ -5,6 +5,8 @@ rules:
   - id: stray-tokens
     name: Pattern with leftover tokens
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     message: unused
     pattern: foo
     tokens:
diff --git a/packages/slopvac-lint/tests/test_cli.py b/packages/slopvac-lint/tests/test_cli.py
index e848149acc..2ad2be9d41 100644
--- a/packages/slopvac-lint/tests/test_cli.py
+++ b/packages/slopvac-lint/tests/test_cli.py
@@ -769,6 +769,8 @@ def test_unimplemented_metrics_are_reported_not_skipped(tmp_path):
         "  - id: nonexistent-metric\n"
         "    name: A metric no branch reads\n"
         "    kind: metric\n"
+        "    dimension: architecture\n"
+        "    ownership: deterministic\n"
         "    severity: warning\n"
         "    message: 'fixture: {match} against {replacement}'\n"
         "    scope: document\n"
diff --git a/packages/slopvac-lint/tests/test_engine.py b/packages/slopvac-lint/tests/test_engine.py
index c91a8c2468..f554ac7b96 100644
--- a/packages/slopvac-lint/tests/test_engine.py
+++ b/packages/slopvac-lint/tests/test_engine.py
@@ -34,7 +34,17 @@ from slopvac.engine import (
     count_clause_boundaries,
 )
 from slopvac.metrics import NATIVE_METRICS
-from slopvac.model import Finding, Provenance, Rule, RuleKind, Scope, TextType, Tier
+from slopvac.model import (
+    Dimension,
+    Finding,
+    Ownership,
+    Provenance,
+    Rule,
+    RuleKind,
+    Scope,
+    TextType,
+    Tier,
+)
 from slopvac.rules import load_ruleset
 from slopvac.score import MIN_WORDS_FOR_DENSITY, score_document
 
@@ -52,6 +62,8 @@ def _fixture_rule(
         id=rule_id,
         name="fixture rule",
         kind=RuleKind.PATTERN,
+        dimension=Dimension.WORDING,
+        ownership=Ownership.DETERMINISTIC,
         pattern=pattern,
         scope=scope,
         text_type=text_type,
diff --git a/packages/slopvac-lint/tests/test_judgement_metadata.py b/packages/slopvac-lint/tests/test_judgement_metadata.py
index 08ffa5bfaf..526da3c023 100644
--- a/packages/slopvac-lint/tests/test_judgement_metadata.py
+++ b/packages/slopvac-lint/tests/test_judgement_metadata.py
@@ -1,30 +1,395 @@
+"""Rule taxonomy and the judgement contract.
+
+`dimension` and `ownership` are required on every rule and `judgement_contract` on
+every judgement rule, so the failures worth pinning are the ones that would
+otherwise ship a rule that LOOKS configured and adjudicates nothing: a seed that
+resolves to no rule, a seeded rule with no seed, a contract on a rule no reviewer
+ever sees.
+
+These tests load only the fixture directories they write, not the shipped catalog.
+The subject is the schema and the loader, so the 230-rule ruleset would only
+couple a schema failure to a catalog failure and report the wrong one.
+"""
+
+from __future__ import annotations
+
+import json
 from pathlib import Path
 
 import pytest
+from click.testing import CliRunner
+
+from slopvac.cli import main
+from slopvac.model import (
+    Category,
+    Dimension,
+    Example,
+    JudgementContract,
+    JudgementDimension,
+    Ownership,
+    Provenance,
+    Rule,
+    RuleKind,
+    Severity,
+)
+from slopvac.reference import render_reference
+from slopvac.rules import RuleLoadError, RuleSet, load_ruleset
+
+_CONTRACT = """    judgement_contract:
+      admission: The unit is a paragraph of at least two sentences.
+      protects: A closing sentence that states a fact stated nowhere else.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
+"""
+
+
+@pytest.fixture
+def fixture_rules(monkeypatch):
+    """Load from `extra_dirs` alone.
+
+    `resources.files` on a package that does not exist raises, which `load_ruleset`
+    already treats as "no packaged rules", so this is the supported no-catalog
+    path rather than a hole punched in the loader.
+    """
+    monkeypatch.setattr("slopvac.rules.RULES_PACKAGE", "slopvac_no_such_package")
+
+    def load(directory: Path):
+        return load_ruleset(extra_dirs=[directory], verify=False)
+
+    return load
+
+
+def _write(directory: Path, name: str, body: str) -> None:
+    directory.mkdir(parents=True, exist_ok=True)
+    (directory / name).write_text(body, encoding="utf-8")
+
+
+def _category(rules: str, category_id: str = "custom") -> str:
+    return (
+        f"id: {category_id}\n"
+        f"title: Custom\n"
+        f"description: Fixture category.\n"
+        f"rules:\n{rules}"
+    )
+
+
+def _pattern_rule(rule_id: str = "core", pattern: str = "xyzzy") -> str:
+    return (
+        f"  - id: {rule_id}\n"
+        f"    name: Fixture pattern\n"
+        f"    kind: pattern\n"
+        f"    dimension: wording\n"
+        f"    ownership: deterministic\n"
+        f"    message: unused\n"
+        f"    pattern: '{pattern}'\n"
+        f"    provenance:\n"
+        f"      source: test\n"
+    )
 
-from slopvac.model import Rule
-from slopvac.rules import RuleLoadError, load_ruleset
+
+def _judgement_rule(
+    rule_id: str = "remainder",
+    *,
+    ownership: str = "document_probe",
+    seeds: str | None = None,
+    extra: str = "",
+    contract: str = _CONTRACT,
+) -> str:
+    body = (
+        f"  - id: {rule_id}\n"
+        f"    name: Fixture judgement\n"
+        f"    kind: judgement\n"
+        f"    dimension: redundancy\n"
+        f"    ownership: {ownership}\n"
+        f"    message: Check it.\n"
+        f"    judgement_question: Does this sentence add a fact?\n"
+    )
+    if seeds is not None:
+        body += f"    seed_rule_ids: [{seeds}]\n"
+    body += contract
+    body += extra
+    body += "    provenance:\n      source: test\n"
+    return body
 
 
-def test_judgement_exceptions_are_rejected_by_model() -> None:
-    with pytest.raises(ValueError, match=r"demo:.*judgement.*exceptions.*never emit"):
-        Rule.model_validate(
-            {
-                "id": "demo",
-                "name": "Demo",
-                "kind": "judgement",
-                "message": "Check it.",
-                "judgement_question": "Is it clear?",
-                "exceptions": ["quotation"],
-                "provenance": {"source": "test"},
-            }
-        )
+# --- exceptions on a judgement rule ------------------------------------------
 
 
-def test_loader_rejects_judgement_exceptions(tmp_path: Path) -> None:
-    (tmp_path / "category.yml").write_text(
-        """id: custom\nname: Custom\nrules:\n  - id: demo\n    name: Demo\n    kind: judgement\n    message: Check it.\n    judgement_question: Is it clear?\n    exceptions: [quotation]\n    provenance:\n      source: test\n""",
-        encoding="utf-8",
+def test_a_judgement_rule_may_carry_named_exceptions(tmp_path, fixture_rules):
+    """The prohibition this replaces was true of a rule that emitted nothing. An
+    adjudicated finding IS a finding, so an author must be able to cite a named
+    reason against it rather than override it unnamed."""
+    _write(
+        tmp_path,
+        "category.yml",
+        _category(_judgement_rule(extra="    exceptions: [quotation, code-span]\n")),
     )
-    with pytest.raises(RuleLoadError, match=r"demo.*judgement.*exceptions.*never emit"):
-        load_ruleset([tmp_path], verify=False)
+    ruleset = fixture_rules(tmp_path)
+    rule = ruleset.by_id("custom.remainder")
+    assert rule is not None
+    assert rule.exceptions == ["quotation", "code-span"]
+
+
+def test_a_judgement_rule_still_ships_at_suggestion(tmp_path, fixture_rules):
+    """Allowing exceptions must not have promoted judgement rules into the
+    mechanical severity band. The confirmable level lives on the contract."""
+    _write(tmp_path, "category.yml", _category(_judgement_rule(extra="    severity: error\n")))
+    rule = fixture_rules(tmp_path).by_id("custom.remainder")
+    assert rule is not None
+    assert rule.severity is Severity.SUGGESTION
+    assert rule.judgement_contract is not None
+    assert rule.judgement_contract.judgement_ceiling is Severity.SUGGESTION
+
+
+# --- the contract is required exactly where it applies ------------------------
+
+
+def test_a_judgement_rule_without_a_contract_does_not_load(tmp_path, fixture_rules):
+    _write(tmp_path, "category.yml", _category(_judgement_rule(contract="")))
+    with pytest.raises(RuleLoadError, match=r"requires `judgement_contract`"):
+        fixture_rules(tmp_path)
+
+
+def test_a_checked_rule_cannot_carry_a_contract(tmp_path, fixture_rules):
+    """A rule no reviewer ever sees has nothing to promise one, and a contract
+    sitting on it reads as though the reviewer will be called."""
+    _write(tmp_path, "category.yml", _category(_pattern_rule() + _CONTRACT))
+    with pytest.raises(
+        RuleLoadError, match=r"`judgement_contract` is not valid for kind=pattern"
+    ):
+        fixture_rules(tmp_path)
+
+
+@pytest.mark.parametrize(
+    "rules,expected",
+    [
+        (
+            _judgement_rule(ownership="deterministic"),
+            r"kind=judgement cannot be ownership=deterministic",
+        ),
+        (
+            _pattern_rule().replace("deterministic", "document_probe"),
+            r"ownership must be deterministic, not document_probe",
+        ),
+    ],
+    ids=["judgement-claims-deterministic", "pattern-claims-probe"],
+)
+def test_ownership_must_agree_with_kind(tmp_path, fixture_rules, rules, expected):
+    _write(tmp_path, "category.yml", _category(rules))
+    with pytest.raises(RuleLoadError, match=expected):
+        fixture_rules(tmp_path)
+
+
+def test_a_contract_scored_on_nothing_does_not_load(tmp_path, fixture_rules):
+    _write(
+        tmp_path,
+        "category.yml",
+        _category(_judgement_rule(contract=_CONTRACT.replace("[FIT, WARRANT]", "[]"))),
+    )
+    with pytest.raises(RuleLoadError, match=r"dims` must name at least one scored axis"):
+        fixture_rules(tmp_path)
+
+
+def test_a_repeated_scored_axis_does_not_load(tmp_path, fixture_rules):
+    _write(
+        tmp_path,
+        "category.yml",
+        _category(_judgement_rule(contract=_CONTRACT.replace("[FIT, WARRANT]", "[FIT, FIT]"))),
+    )
+    with pytest.raises(RuleLoadError, match=r"dims` repeats FIT"):
+        fixture_rules(tmp_path)
+
+
+def test_a_ceiling_of_off_does_not_load(tmp_path, fixture_rules):
+    """`off` would make every confirm unreachable while the rule still advertised
+    a question, which is the silent-pass shape this schema exists to stop.
+
+    Quoted, because YAML 1.1 reads a bare `off` as the boolean False and the
+    error would then be about a type rather than about the ceiling.
+    """
+    _write(
+        tmp_path,
+        "category.yml",
+        _category(
+            _judgement_rule(
+                contract=_CONTRACT.replace(
+                    "judgement_ceiling: suggestion", "judgement_ceiling: 'off'"
+                )
+            )
+        ),
+    )
+    with pytest.raises(RuleLoadError, match=r"judgement_ceiling` cannot be `off`"):
+        fixture_rules(tmp_path)
+
+
+# --- seeds --------------------------------------------------------------------
+
+
+def test_a_seed_may_point_into_a_file_loaded_later(tmp_path, fixture_rules):
+    """The reason seeds resolve after the whole registry loads. Files are read in
+    name order, so `a.yml` naming a rule in `b.yml` is a forward reference the
+    catalog legitimately contains."""
+    _write(tmp_path, "a.yml", _category(_judgement_rule(
+        ownership="seeded_adjudication", seeds="'later.core'"
+    )))
+    _write(tmp_path, "b.yml", _category(_pattern_rule(), category_id="later"))
+    ruleset = fixture_rules(tmp_path)
+    rule = ruleset.by_id("custom.remainder")
+    assert rule is not None
+    assert rule.seed_rule_ids == ["later.core"]
+
+
+def test_a_seed_that_names_no_rule_does_not_load(tmp_path, fixture_rules):
+    _write(tmp_path, "category.yml", _category(_judgement_rule(
+        ownership="seeded_adjudication", seeds="'custom.absent'"
+    )))
+    with pytest.raises(RuleLoadError, match=r"seed 'custom.absent' names no rule"):
+        fixture_rules(tmp_path)
+
+
+def test_a_rule_cannot_seed_itself(tmp_path, fixture_rules):
+    _write(tmp_path, "category.yml", _category(_judgement_rule(
+        ownership="seeded_adjudication", seeds="'custom.remainder'"
+    )))
+    with pytest.raises(RuleLoadError, match=r"seed 'custom.remainder' is the rule itself"):
+        fixture_rules(tmp_path)
+
+
+def test_a_seed_cannot_be_another_judgement_rule(tmp_path, fixture_rules):
+    """A judgement rule produces no span, so seeding one gives the adjudicator
+    nothing to be handed."""
+    _write(
+        tmp_path,
+        "category.yml",
+        _category(
+            _judgement_rule(ownership="seeded_adjudication", seeds="'custom.probe'")
+            + _judgement_rule(rule_id="probe")
+        ),
+    )
+    with pytest.raises(RuleLoadError, match=r"seed 'custom.probe' is kind=judgement"):
+        fixture_rules(tmp_path)
+
+
+def test_a_seeded_rule_with_no_seed_does_not_load(tmp_path, fixture_rules):
+    _write(tmp_path, "category.yml", _category(_judgement_rule(ownership="seeded_adjudication")))
+    with pytest.raises(RuleLoadError, match=r"requires at least one `seed_rule_ids` entry"):
+        fixture_rules(tmp_path)
+
+
+def test_a_probe_cannot_declare_a_seed(tmp_path, fixture_rules):
+    _write(tmp_path, "category.yml", _category(
+        _pattern_rule() + _judgement_rule(seeds="'custom.core'")
+    ))
+    with pytest.raises(RuleLoadError, match=r"`seed_rule_ids` is not valid for ownership=document_probe"):
+        fixture_rules(tmp_path)
+
+
+def test_an_unqualified_seed_does_not_load(tmp_path, fixture_rules):
+    _write(tmp_path, "category.yml", _category(_judgement_rule(
+        ownership="seeded_adjudication", seeds="'core'"
+    )))
+    with pytest.raises(RuleLoadError, match=r"seed 'core' is not a qualified"):
+        fixture_rules(tmp_path)
+
+
+# --- export -------------------------------------------------------------------
+
+
+def _seeded_ruleset() -> RuleSet:
+    core = Rule(
+        id="core",
+        name="Fixture pattern",
+        kind=RuleKind.PATTERN,
+        dimension=Dimension.STALENESS,
+        ownership=Ownership.DETERMINISTIC,
+        pattern="xyzzy",
+        message="unused",
+        provenance=Provenance(source="test"),
+    )
+    remainder = Rule(
+        id="remainder",
+        name="Settle the rest",
+        kind=RuleKind.JUDGEMENT,
+        dimension=Dimension.VERACITY,
+        ownership=Ownership.SEEDED_ADJUDICATION,
+        seed_rule_ids=["probe.core"],
+        message="Check it.",
+        judgement_question="Does the sentence claim something checkable?",
+        judgement_contract=JudgementContract(
+            admission="The core rule already matched inside this unit.",
+            protects="A quoted claim attributed to a named source.",
+            dims=[JudgementDimension.FIT, JudgementDimension.WARRANT, JudgementDimension.HARM],
+            evidence_arity=2,
+            judgement_ceiling=Severity.ERROR,
+            rewrite_exempt=True,
+        ),
+        examples=[Example(bad="Everyone agrees the cache is warm.")],
+        provenance=Provenance(source="test"),
+    )
+    for rule in (core, remainder):
+        object.__setattr__(rule, "category", "probe")
+    return RuleSet(
+        categories={
+            "probe": Category(
+                id="probe",
+                title="Probe",
+                description="Fixture category.",
+                rules=[core, remainder],
+            )
+        }
+    )
+
+
+def test_the_reference_prints_the_whole_contract():
+    """A reviewer held to these terms has to be able to read them. Summarising
+    them here is how the two copies drift."""
+    rendered = render_reference(_seeded_ruleset())
+
+    assert "**Dimension.** staleness" in rendered
+    assert "**Dimension.** veracity" in rendered
+    assert "**Layer.** deterministic" in rendered
+    assert "**Layer.** seeded_adjudication" in rendered
+    assert "**Adjudicates matches of.** `probe.core`" in rendered
+    assert "**Applies when.** The core rule already matched inside this unit." in rendered
+    assert "**Must not flag.** A quoted claim attributed to a named source." in rendered
+    assert "**Scored on.** FIT, WARRANT, HARM" in rendered
+    assert "**Evidence.** 2 located spans" in rendered
+    assert "**Confirms at most.** error" in rendered
+    assert "**Rewrite may alter a protected token.** yes" in rendered
+
+
+def test_the_reference_counts_rules_per_dimension_and_layer():
+    rendered = render_reference(_seeded_ruleset())
+    assert "| Dimension | Rules | Checked | Seeded adjudication | Document probe |" in rendered
+    assert "| `staleness` | 1 | 1 | 0 | 0 |" in rendered
+    assert "| `veracity` | 1 | 0 | 1 | 0 |" in rendered
+    # A dimension no rule claims is omitted rather than printed as a zero row.
+    assert "`inclusion`" not in rendered
+
+
+def test_explain_json_carries_the_taxonomy_and_contract(tmp_path, monkeypatch):
+    """`explain --format json` is what the review skill reads. A field it cannot
+    see is a field the reviewer invents for itself."""
+    monkeypatch.setattr("slopvac.rules.RULES_PACKAGE", "slopvac_no_such_package")
+    _write(tmp_path, "a.yml", _category(_judgement_rule(
+        ownership="seeded_adjudication", seeds="'custom.core'"
+    ) + _pattern_rule()))
+
+    result = CliRunner().invoke(
+        main, ["explain", "custom.remainder", "--format", "json", "--rules-dir", str(tmp_path)]
+    )
+    payload = json.loads(result.output)
+
+    assert payload["dimension"] == "redundancy"
+    assert payload["ownership"] == "seeded_adjudication"
+    assert payload["seed_rule_ids"] == ["custom.core"]
+    assert payload["judgement_contract"] == {
+        "admission": "The unit is a paragraph of at least two sentences.",
+        "protects": "A closing sentence that states a fact stated nowhere else.",
+        "dims": ["FIT", "WARRANT"],
+        "evidence_arity": 1,
+        "judgement_ceiling": "suggestion",
+        "rewrite_exempt": False,
+    }
diff --git a/packages/slopvac-lint/tests/test_reference.py b/packages/slopvac-lint/tests/test_reference.py
index 9e83e99724..d22f662e22 100644
--- a/packages/slopvac-lint/tests/test_reference.py
+++ b/packages/slopvac-lint/tests/test_reference.py
@@ -6,7 +6,18 @@ must treat that as empty text, not crash on `.strip()`.
 
 from __future__ import annotations
 
-from slopvac.model import Category, Example, Provenance, Rule, RuleKind, Severity
+from slopvac.model import (
+    Category,
+    Dimension,
+    Example,
+    JudgementContract,
+    JudgementDimension,
+    Ownership,
+    Provenance,
+    Rule,
+    RuleKind,
+    Severity,
+)
 from slopvac.reference import render_reference
 from slopvac.rules import RuleSet
 
@@ -16,6 +27,16 @@ def test_judgement_example_without_good_renders():
         id="omit-good",
         name="Delete the filler",
         kind=RuleKind.JUDGEMENT,
+        dimension=Dimension.REDUNDANCY,
+        ownership=Ownership.DOCUMENT_PROBE,
+        judgement_contract=JudgementContract(
+            admission="The unit is a paragraph of at least two sentences.",
+            protects="A closing sentence that states a fact stated nowhere else.",
+            dims=[JudgementDimension.FIT, JudgementDimension.WARRANT],
+            evidence_arity=1,
+            judgement_ceiling=Severity.SUGGESTION,
+            rewrite_exempt=False,
+        ),
         message="delete it",
         judgement_question="Does this sentence add a fact?",
         examples=[Example(bad="In conclusion, the cache is cold.")],


### a43178f7f6

a43178f7f6 feat(rules): add taxonomy and judgement contract metadata to every rule
Every one of the 232 shipped rules now declares a `dimension` (one of the
twelve cross-cutting dimensions) and an `ownership` layer. The 43 seeded
adjudicators name their deterministic seeds in `seed_rule_ids`; the 22
full-document and full-context rules are `document_probe`.

All 65 judgement rules carry a `judgement_contract`: the unit precondition
that admits the question, the preservation classes that outrank the rule,
the dimensions the rubric asks for, the evidence arity, the severity ceiling
a confirm may reach, and whether the fix may change a protected token.

24 judgement rules had their exception tokens swallowed into the
`judgement_question` folded scalar as orphan list items. Those tokens are
now real `exceptions:` lists.

No pattern, tier, severity, allowlist, message, or example content changed.


diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-residue.yml b/packages/slopvac-lint/src/slopvac/rules/ai-residue.yml
index 0c4d861304..9c0120935b 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-residue.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-residue.yml
@@ -11,6 +11,8 @@ rules:
     exceptions: [quotation]
     name: Delete chat-session leakage
     kind: pattern
+    dimension: veracity
+    ownership: deterministic
     severity: error
     message: 'chat-session leakage: {match} -- delete it, then audit the surrounding prose'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
index ad6137e6ba..be2f942255 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
@@ -25,6 +25,22 @@ rules:
   - id: contrastive-inversion-remainder
     name: Judge whether a contrast names a real alternative
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-agentic.contrastive-inversion-frames
+      - ai-tells-structure.definitional-negation-pair
+    judgement_contract:
+      admission: >-
+        The paragraph holds a negated-half contrast a seed matched, or one of the ambiguous bare-clause and
+        subjectless-imperative forms the seed leaves clean, and both halves are quotable inside the unit.
+      protects: >-
+        factual_contrast and technical_invariant: a negated half that states a real boundary, a safety constraint, or
+        a documented invariant outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: 'contrastive inversion: state what the thing is; cut the strawman'
     scope: paragraph
@@ -66,6 +82,8 @@ rules:
     exceptions: [quotation, factual-correction]
     name: Cut a cross-sentence definitional contrast
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'definitional contrast across sentences: {match} -- state what the thing is once; cut the invented alternative'
     scope: paragraph
@@ -124,6 +142,8 @@ rules:
   - id: staccato-negative-parallel-frames
     name: Replace a staccato negative run with one sentence
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'staccato negative parallel: {match} -- one plain sentence naming the thing'
     scope: paragraph
@@ -149,6 +169,21 @@ rules:
   - id: staccato-negative-parallel-remainder
     name: Judge whether a fragment run carries content
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.staccato-negative-parallel-frames
+    judgement_contract:
+      admission: >-
+        The paragraph holds the run of consecutive fragments a seed matched, and every fragment in the run is quotable
+        inside the unit.
+      protects: >-
+        accessibility_repetition and l2_clarity: a short-sentence run written for scanning or for a non-native reader
+        outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'fragment cadence: rejoin the fragments and let the fact carry the weight'
     scope: paragraph
@@ -174,6 +209,8 @@ rules:
   - id: tricolon-abuse-core
     name: Cut a three-item list to the items that carry load
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'tricolon: {match} -- cut to the one or two that carry load; break the symmetry'
     scope: sentence
@@ -210,6 +247,21 @@ rules:
   - id: tricolon-abuse-remainder
     name: Judge whether parallel bullets carry distinct substance
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.tricolon-abuse-core
+    judgement_contract:
+      admission: >-
+        The document holds the three identical-shape items, or the two consecutive tricolons, a seed matched, and
+        every item is quotable inside the unit.
+      protects: >-
+        technical_invariant and accessibility_repetition: parallel items that enumerate a fixed set, and repetition an
+        assisted reader navigates by, outrank this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'parallel symmetry: keep only the items with distinct substance'
     scope: document
@@ -237,6 +289,8 @@ rules:
   - id: false-suspense-frames
     name: Delete the drumroll
     kind: tokens
+    dimension: staleness
+    ownership: deterministic
     severity: error
     message: 'false suspense: {match} -- delete the drumroll; state the point'
     scope: prose
@@ -273,6 +327,20 @@ rules:
   - id: false-suspense-remainder
     name: Judge whether a transition withholds the point
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.false-suspense-frames
+    judgement_contract:
+      admission: >-
+        The paragraph opens on the announcement phrase a seed matched, and the sentences that would state the point
+        are inside the unit.
+      protects: >-
+        l2_clarity: a transition a non-native reader needs to follow the turn outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'false suspense: delete the drumroll; state the point'
     scope: paragraph
@@ -297,6 +365,8 @@ rules:
   - id: fragment-question-pivot
     name: Replace a question-answer fragment pair with a declarative
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'fragment-question pivot: {match} -- one declarative sentence'
     scope: prose
@@ -321,6 +391,8 @@ rules:
   - id: rhetorical-question-transition
     name: Answer directly instead of asking
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'rhetorical question: {match} -- answer directly; delete the question'
     scope: prose
@@ -347,6 +419,8 @@ rules:
   - id: meta-narration-frames
     name: Delete the navigation announcement
     kind: tokens
+    dimension: redundancy
+    ownership: deterministic
     severity: error
     message: 'meta-narration: {match} -- delete it; navigation is the TOC''s job'
     scope: prose
@@ -384,6 +458,21 @@ rules:
   - id: meta-narration-remainder
     name: Judge whether a sentence spends itself on navigation
     kind: judgement
+    dimension: redundancy
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.meta-narration-frames
+    judgement_contract:
+      admission: >-
+        The paragraph contains the navigational frame a seed matched, and the whole framing sentence is quotable
+        inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: a statement about document structure that a standard or a contract
+        requires outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'meta-narration: delete it; navigation is the TOC''s job'
     scope: paragraph
@@ -407,6 +496,21 @@ rules:
   - id: heading-echo
     name: Start with the first new fact after a heading
     kind: judgement
+    dimension: redundancy
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-craft.self-reference
+    judgement_contract:
+      admission: >-
+        The unit is the first paragraph under a heading and the heading text sits in the same block, so heading and
+        opening sentence are both quotable.
+      protects: >-
+        accessibility_repetition and l2_clarity: a restatement that orients a reader arriving from a link, a search
+        result, or a screen reader outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'heading echo: start with the first new fact'
     scope: paragraph
@@ -434,6 +538,8 @@ rules:
     exceptions: [quotation]
     name: End on the last fact
     kind: tokens
+    dimension: redundancy
+    ownership: deterministic
     severity: error
     message: 'summary closer: {match} -- end on the last fact'
     scope: prose
@@ -482,6 +588,20 @@ rules:
   - id: summary-closer-remainder
     name: Judge whether a closing section adds a fact
     kind: judgement
+    dimension: redundancy
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.summary-closer-frames
+    judgement_contract:
+      admission: >-
+        The document's final section opens on the closer frame a seed matched, and the sections it may be re-listing
+        are inside the unit.
+      protects: >-
+        accessibility_repetition: a recap a long reference document gives a returning reader outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'summary closer: end on the last fact'
     scope: document
@@ -509,6 +629,19 @@ rules:
   - id: listicle-in-a-trench-coat
     name: Make it a real list or real prose
     kind: judgement
+    dimension: architecture
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document holds at least two consecutive paragraphs that open on an ordinal position in a sequence, both
+        quotable inside the unit.
+      protects: >-
+        l2_clarity and accessibility_repetition: ordinal signposting a reader needs to keep place in a long procedure
+        outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'listicle in prose: either a real list, or prose with connective logic'
     scope: document
@@ -534,6 +667,19 @@ rules:
   - id: anaphora-abuse
     name: Say it once and merge the objects
     kind: judgement
+    dimension: staleness
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph holds three or more consecutive sentences whose opening subject-verb pair repeats, and each
+        opening is quotable inside the unit.
+      protects: >-
+        accessibility_repetition and l2_clarity: a repeated frame that carries parallel instructions for an assisted
+        or non-native reader outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'anaphora: say it once; merge the objects'
     scope: paragraph
@@ -558,6 +704,19 @@ rules:
   - id: analogy-stack-authority
     name: Keep one apt comparison, or none
     kind: judgement
+    dimension: veracity
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph names at least one well-known company, product, or system, and the claim it is attached to is
+        quotable inside the unit.
+      protects: >-
+        technical_invariant and defined_domain_term: a named product that is part of the mechanism, or a term of art,
+        outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'analogy stack: one apt comparison, or none'
     scope: paragraph
@@ -582,6 +741,19 @@ rules:
   - id: invented-concept-label
     name: Coin nothing
     kind: judgement
+    dimension: wording
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document presents a title-cased or quoted concept label, and any definition or citation the label carries
+        is inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a label the project glossary, the schema, or the code defines
+        outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: 'invented concept label: use the plain description; coin nothing'
     scope: document
@@ -607,6 +779,8 @@ rules:
   - id: cataphoric-lead-in-core
     name: Cut the count forecast
     kind: pattern
+    dimension: redundancy
+    ownership: deterministic
     severity: warning
     message: 'cataphoric lead-in: {match} -- let the list carry its own length; cut the forecast'
     scope: prose
@@ -634,6 +808,19 @@ rules:
   - id: cataphoric-lead-in-remainder
     name: Judge whether a forecast tells the reader anything
     kind: judgement
+    dimension: redundancy
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.cataphoric-lead-in-core
+    judgement_contract:
+      admission: >-
+        The paragraph contains the count forecast a seed matched, and the list it forecasts is inside the unit.
+      protects: >-
+        l2_clarity: a forecast a reader needs to budget effort before a long list outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'cataphoric lead-in: cut the forecast'
     scope: paragraph
@@ -655,6 +842,19 @@ rules:
   - id: hollow-acknowledgment
     name: Solve it, or cut the paragraph that raises it
     kind: judgement
+    dimension: specificity
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph names a risk, a limitation, or a problem, and any action, measurement, or pointer it offers is
+        inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: a disclosure a standard or a contract requires, and a documented
+        limitation, outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'hollow acknowledgment: solve it, or cut the paragraph that raises it'
     scope: paragraph
@@ -681,6 +881,8 @@ rules:
   - id: absolute-assertion-core
     name: State the claim with its actual scope
     kind: pattern
+    dimension: veracity
+    ownership: deterministic
     severity: warning
     message: 'absolute assertion: {match} -- state the claim with its actual scope'
     scope: prose
@@ -709,6 +911,21 @@ rules:
   - id: absolute-assertion-remainder
     name: Judge whether an absolute claim survives one counterexample
     kind: judgement
+    dimension: veracity
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.absolute-assertion-core
+    judgement_contract:
+      admission: >-
+        The sentence carries the universal quantifier or absolute adverb a seed matched, and any scope that bounds the
+        claim is in the same sentence.
+      protects: >-
+        technical_invariant and formal_legal: a defined scoped invariant, and a normative requirement whose force
+        depends on the absolute, outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: 'absolute assertion: state the claim with its actual scope'
     scope: sentence
@@ -735,6 +952,8 @@ rules:
   - id: negative-inventory-core
     name: Cut low-value negative inventory
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: warning
     message: 'negative inventory: {match} -- state the supported behavior or constraint'
     scope: prose
@@ -767,6 +986,21 @@ rules:
   - id: negative-inventory-remainder
     name: Judge whether a negative constraint is actionable
     kind: judgement
+    dimension: scope
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.negative-inventory-core
+    judgement_contract:
+      admission: >-
+        The paragraph contains the negative statement a seed matched, and any constraint, result, or pointer it
+        carries is inside the unit.
+      protects: >-
+        technical_invariant and formal_legal: an enforced exclusion, an audit fact, or a compliance constraint
+        outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'negative inventory: keep only an actionable constraint, result, or pointer'
     scope: paragraph
@@ -797,6 +1031,8 @@ rules:
   - id: think-of-it-as-core
     name: Explain the mechanism instead of the metaphor
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'teacher voice: {match} -- explain the actual mechanism once; cut the teacher voice'
     scope: prose
@@ -821,6 +1057,20 @@ rules:
   - id: think-of-it-as-remainder
     name: Judge whether an analogy replaces the mechanism
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.think-of-it-as-core
+    judgement_contract:
+      admission: >-
+        The paragraph contains the analogy frame a seed matched, and any statement of the mechanism is inside the
+        unit.
+      protects: >-
+        l2_clarity: an analogy that shortens the explanation for a non-specialist reader outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'teacher voice: explain the actual mechanism once'
     scope: paragraph
@@ -842,6 +1092,18 @@ rules:
   - id: false-range
     name: List the actual items or name the real dimension
     kind: judgement
+    dimension: wording
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The sentence contains a from-X-to-Y construction whose two endpoints are both quotable inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a real scale whose endpoints the domain or the schema defines
+        outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'false range: list the actual items, or name the real dimension'
     scope: sentence
@@ -869,6 +1131,8 @@ rules:
     exceptions: [quotation]
     name: Name the source or own the claim
     kind: pattern
+    dimension: specificity
+    ownership: deterministic
     severity: error
     message: 'vague attribution: {match} -- name the source or own the claim'
     scope: prose
@@ -896,6 +1160,21 @@ rules:
   - id: vague-attribution-remainder
     name: Judge whether a cited source is checkable
     kind: judgement
+    dimension: specificity
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.vague-attribution-core
+    judgement_contract:
+      admission: >-
+        The sentence contains the unnamed-source phrase a seed matched, and any citation it offers is in the same
+        sentence.
+      protects: >-
+        formal_legal and technical_invariant: an attribution a licence, a citation standard, or an anonymity
+        requirement fixes outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'vague attribution: name the source or own the claim'
     scope: sentence
@@ -920,6 +1199,8 @@ rules:
   - id: audience-straddle-core
     name: Write for the one audience the doc has
     kind: pattern
+    dimension: consistency
+    ownership: deterministic
     severity: warning
     message: 'audience straddle: {match} -- write for the one audience the doc has'
     scope: prose
@@ -944,6 +1225,21 @@ rules:
   - id: audience-straddle-remainder
     name: Judge whether the document holds one audience
     kind: judgement
+    dimension: consistency
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-structure.audience-straddle-core
+    judgement_contract:
+      admission: >-
+        The document explains a term in one place and uses it without explanation in another, and both places are
+        inside the unit.
+      protects: >-
+        l2_clarity and accessibility_repetition: an explanation repeated for a reader who enters the document mid-way
+        outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'audience straddle: write for the one audience the doc has'
     scope: document
@@ -974,6 +1270,8 @@ rules:
   - id: faux-candor-core
     name: Cut the intimacy performance
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'faux candor: {match} -- cut the intimacy performance; candor is the unhedged claim'
     scope: prose
@@ -1008,6 +1306,20 @@ rules:
   - id: faux-candor-remainder
     name: Judge whether an admission carries risk
     kind: judgement
+    dimension: inflation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.faux-candor-core
+    judgement_contract:
+      admission: >-
+        The paragraph contains the admission frame a seed matched, and any named cost, mistake, or refused feature is
+        inside the unit.
+      protects: >-
+        formal_legal: a disclosure a licence, a policy, or a contract requires outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'faux candor: candor is the unhedged claim itself'
     scope: paragraph
@@ -1032,6 +1344,8 @@ rules:
   - id: intensifier-tics-core
     name: Drop the unearned intensifier
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'intensifier tic: {match} -- drop it; add the specific claim that would justify it'
     scope: prose
@@ -1068,6 +1382,21 @@ rules:
   - id: intensifier-tics-remainder
     name: Judge whether emotion is announced or earned
     kind: judgement
+    dimension: inflation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.intensifier-tics-core
+    judgement_contract:
+      admission: >-
+        The sentence carries the intensifying adverb a seed matched, and the passage that would support the reaction
+        is inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: an adverb that belongs to a defined term or reports a measured
+        degree outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'unearned emotion: add the specific claim, or drop the adverb'
     scope: sentence
@@ -1089,6 +1418,8 @@ rules:
   - id: corporate-analytic-filler-core
     name: Delete the analysis wrapper and keep the noun
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'analytic filler: {match} -- delete the wrapper; keep the noun'
     scope: prose
@@ -1129,6 +1460,20 @@ rules:
   - id: corporate-analytic-filler-remainder
     name: Judge whether an analysis frame contains analysis
     kind: judgement
+    dimension: inflation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.corporate-analytic-filler-core
+    judgement_contract:
+      admission: >-
+        The paragraph opens on the analysis frame a seed matched, and the sentence the frame wraps is quotable inside
+        the unit.
+      protects: >-
+        formal_legal: framing a report format, a template, or a standard requires outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'analytic filler: analysis-flavored packaging around no analysis'
     scope: paragraph
@@ -1150,6 +1495,22 @@ rules:
   - id: over-formatting-reflex
     name: Format only when the data has columns
     kind: judgement
+    dimension: presentation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-formatting.inline-header-list
+      - ai-tells-formatting.bold-spray
+    judgement_contract:
+      admission: >-
+        The document contains at least one table, bold-colon bullet, or inline-header run a seed matched, and its rows
+        or items are inside the unit.
+      protects: >-
+        accessibility_repetition and l2_clarity: structure a screen reader or a scanning reader navigates by outranks
+        this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'over-formatting: format only when the data has columns or the items are parallel and independent'
     scope: document
@@ -1180,6 +1541,8 @@ rules:
   - id: uniform-paragraph-mass
     name: Vary paragraph length deliberately
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'uniform paragraph mass: stdev of paragraph word count is {match} -- vary length deliberately'
     scope: document
@@ -1207,6 +1570,18 @@ rules:
   - id: hedged-symmetry
     name: Take the position the evidence supports
     kind: judgement
+    dimension: veracity
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph states a position and at least one counter-claim, both quotable inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: a counter-claim a standard records, and a measured variance, outrank
+        this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'hedged symmetry: take the position the evidence supports; cut the ballast'
     scope: paragraph
@@ -1235,6 +1610,8 @@ rules:
   - id: sycophantic-meta-residue
     name: Delete the approval residue and audit the surrounding text
     kind: tokens
+    dimension: veracity
+    ownership: deterministic
     severity: error
     message: 'sycophancy residue: {match} -- delete it, then audit the surrounding text'
     scope: prose
@@ -1270,6 +1647,8 @@ rules:
   - id: figurative-verb-verdict-core
     name: State the judgement literally
     kind: tokens
+    dimension: staleness
+    ownership: deterministic
     severity: error
     message: 'figurative verdict: {match} -- state the judgement literally, with the observation that supports it'
     scope: prose
@@ -1307,6 +1686,20 @@ rules:
   - id: figurative-verb-verdict-remainder
     name: Judge whether a metaphor carries a verdict with no evidence
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.figurative-verb-verdict-core
+    judgement_contract:
+      admission: >-
+        The sentence carries the figurative verdict verb a seed matched, and any observation that would support the
+        verdict is in the same sentence.
+      protects: >-
+        defined_domain_term: a figurative verb that belongs to a defined term of art outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'figurative verdict: the construction carries the verdict so no evidence has to'
     scope: sentence
@@ -1331,6 +1724,8 @@ rules:
   - id: urgency-inflation-core
     name: Name what breaks, or drop the framing
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'urgency inflation: {match} -- name what breaks if the reader ignores it, or drop the framing'
     scope: prose
@@ -1364,6 +1759,20 @@ rules:
   - id: urgency-inflation-remainder
     name: Judge whether stakes name a consequence
     kind: judgement
+    dimension: inflation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.urgency-inflation-core
+    judgement_contract:
+      admission: >-
+        The paragraph carries the urgency phrase a seed matched, and any named failure mode is inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: urgency a safety requirement, a deprecation deadline, or a regulation
+        fixes outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'urgency inflation: name what breaks if the reader ignores it'
     scope: paragraph
@@ -1385,6 +1794,8 @@ rules:
   - id: organic-consequence-core
     name: Say the choice was made, and why
     kind: tokens
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'organic-consequence framing: {match} -- say the choice was made, and who made it'
     scope: prose
@@ -1418,6 +1829,20 @@ rules:
   - id: organic-consequence-remainder
     name: Judge whether a design is presented as self-caused
     kind: judgement
+    dimension: agency
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.organic-consequence-core
+    judgement_contract:
+      admission: >-
+        The sentence carries the self-causation frame a seed matched, and its subject is quotable in the same
+        sentence.
+      protects: >-
+        technical_invariant: emergent behaviour the system genuinely has, with no chooser to name, outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'organic-consequence framing: a designed decision presented as something that happened'
     scope: sentence
@@ -1438,6 +1863,20 @@ rules:
   - id: false-agency-remainder
     name: Judge whether an abstraction occupies the subject slot
     kind: judgement
+    dimension: agency
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-agency.false-agency
+    judgement_contract:
+      admission: >-
+        The sentence's subject is the abstraction a seed matched, and the verb it governs is in the same sentence.
+      protects: >-
+        defined_domain_term and technical_invariant: a subject the domain defines as an actor, such as a named service
+        or job, outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'false agency: name the human, or use "you" and put the reader in the seat'
     scope: sentence
@@ -1469,6 +1908,8 @@ rules:
     exceptions: [quotation]
     name: State the measured property, not the desert
     kind: tokens
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'anthropomorphised justification: {match} -- state the measured property'
     scope: prose
@@ -1504,6 +1945,21 @@ rules:
   - id: anthropomorphised-justification-remainder
     name: Judge whether a component is granted intent
     kind: judgement
+    dimension: agency
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-register.anthropomorphised-justification-core
+    judgement_contract:
+      admission: >-
+        The sentence grants a component the merit term a seed matched, and the property it claims is in the same
+        sentence.
+      protects: >-
+        defined_domain_term: a merit word that names a measured property or belongs to a defined term outranks this
+        rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'anthropomorphised justification: a component granted intent so its value needs no argument'
     scope: sentence
@@ -1534,6 +1990,8 @@ rules:
   - id: em-dash-density
     name: Keep only the em dashes that mark a real aside
     kind: metric
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'dash density: {match} dashes per 1000 words -- most become commas, colons, or two sentences'
     scope: document
@@ -1564,6 +2022,8 @@ rules:
   - id: curly-quotes
     name: Normalise curly quotes to straight ones
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'curly quote: {match} -- normalise to a straight quote'
     scope: raw
@@ -1590,6 +2050,8 @@ rules:
   - id: title-case-heading
     name: Use sentence case in headings
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'title-case heading: {match} -- use sentence case unless house style says otherwise'
     scope: heading
@@ -1630,6 +2092,8 @@ rules:
   - id: bold-spray
     name: Bold at most the first definitional use
     kind: metric
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'bold spray: {match} bold spans per 1000 words -- bold at most first definitional use'
     scope: document
@@ -1654,6 +2118,8 @@ rules:
   - id: inline-header-list
     name: Convert a repeated bold-colon bullet run to prose or a table
     kind: metric
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'inline-header list: {match} consecutive bold-colon bullets -- prose, or a table with real columns'
     scope: document
@@ -1678,6 +2144,8 @@ rules:
   - id: heading-hierarchy
     name: Fix a skipped heading level
     kind: structure
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'heading hierarchy: {match} -- fix the level; delete the rule before it'
     scope: document
@@ -1700,6 +2168,17 @@ rules:
   - id: table-wrapping-one-sentence
     name: Unwrap a table that holds one sentence
     kind: judgement
+    dimension: presentation
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document contains at least one table whose header and rows are inside the unit.
+      protects: >-
+        accessibility_repetition: a table a screen reader or a reference reader navigates by outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'table wrapping prose: unwrap it'
     scope: document
@@ -1724,6 +2203,8 @@ rules:
   - id: italicised-copula
     name: Delete manufactured emphasis
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'italicised copula: {match} -- delete the emphasis; let word order carry the contrast'
     scope: raw
@@ -1750,6 +2231,8 @@ rules:
   - id: cross-reference-signposting
     name: Delete the cross-reference signpost
     kind: tokens
+    dimension: redundancy
+    ownership: deterministic
     severity: warning
     message: 'cross-reference signposting: {match} -- delete it; a doc with a TOC is not read linearly'
     scope: prose
@@ -1784,6 +2267,8 @@ rules:
   - id: emoji-list-markers
     name: Delete emoji used as list markers
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'emoji list marker: {match} -- delete it; the list marker carries the structure'
     scope: raw
@@ -1824,6 +2309,8 @@ rules:
   - id: fabricated-citations-core
     name: Strip citation junk
     kind: pattern
+    dimension: veracity
+    ownership: deterministic
     severity: error
     message: 'damaged citation: {match} -- verify the reference and strip the tracking junk'
     scope: raw
@@ -1851,6 +2338,20 @@ rules:
   - id: fabricated-citations-remainder
     name: Verify every reference you did not fetch yourself
     kind: judgement
+    dimension: veracity
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ai-tells-content-shape.fabricated-citations-core
+    judgement_contract:
+      admission: >-
+        The document contains the reference a seed matched, and the sentence whose claim rests on it is inside the
+        unit.
+      protects: >-
+        formal_legal: a citation a licence, a standard, or an attribution requirement fixes outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'unverified citation: verify every reference you did not fetch yourself'
     scope: document
@@ -1881,6 +2382,8 @@ rules:
   - id: fake-specificity
     name: Give the number or drop the quantifier
     kind: pattern
+    dimension: specificity
+    ownership: deterministic
     severity: error
     message: 'fake specificity: {match} -- give the number or drop the quantifier'
     scope: prose
@@ -1913,6 +2416,18 @@ rules:
   - id: vaporware-description
     name: Cut the claim, not the qualifier
     kind: judgement
+    dimension: veracity
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document describes a behaviour in the present tense and names the artifact the behaviour belongs to.
+      protects: >-
+        formal_legal and technical_invariant: a specification, a standard, or a contract that states required
+        behaviour outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'vaporware: cut the CLAIM, not the qualifier'
     scope: document
@@ -1951,6 +2466,8 @@ rules:
   - id: adjective-per-noun-spray
     name: Cut decorative modifiers
     kind: metric
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: 'adjective spray: {match} adjectives per noun -- keep the ones that carry load'
     scope: document
@@ -1976,6 +2493,17 @@ rules:
   - id: elegant-variation
     name: Repeat the noun
     kind: judgement
+    dimension: consistency
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document refers to one thing by two or more names, and every spelling is quotable inside the unit.
+      protects: >-
+        defined_domain_term and l2_clarity: two names the domain genuinely distinguishes outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: 'elegant variation: repeat the noun; precision beats variety'
     scope: document
@@ -2001,6 +2529,18 @@ rules:
   - id: one-point-dilution
     name: Say it once and stop
     kind: judgement
+    dimension: redundancy
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document restates an argument it already made, and both the first statement and the restatement are
+        quotable inside the unit.
+      protects: >-
+        accessibility_repetition: a restatement a long document gives a reader who enters mid-way outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'one-point dilution: say it once; stop'
     scope: document
@@ -2026,6 +2566,19 @@ rules:
   - id: padded-symmetry
     name: Let a section be two sentences
     kind: judgement
+    dimension: redundancy
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document contains the section under question and the sibling section whose length it may be matching, or a
+        FAQ, Tips, or Troubleshooting section, inside the unit.
+      protects: >-
+        accessibility_repetition and formal_legal: a section a template, a standard, or a publishing contract requires
+        outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'padded symmetry: two sentences is a fine section'
     scope: document
@@ -2054,6 +2607,8 @@ rules:
   - id: superficial-ing-analysis
     name: State the analysis as a fact or delete it
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'superficial -ing analysis: {match} -- state it as a fact, or delete it'
     scope: prose
@@ -2079,6 +2634,8 @@ rules:
     exceptions: [quotation]
     name: Use the concrete verb
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: "copula avoidance: use '{replacement}' instead of '{match}'"
     scope: prose
@@ -2126,6 +2683,18 @@ rules:
   - id: textbook-connector-runs
     name: Do not open consecutive sentences on a textbook connector
     kind: judgement
+    dimension: staleness
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        Two consecutive sentences in the paragraph each open on a connector, and both openings are quotable inside the
+        unit.
+      protects: >-
+        l2_clarity: a connector that makes the relation explicit for a non-native reader outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'textbook connectors: replace with the concrete relation, or delete'
     scope: paragraph
@@ -2156,6 +2725,22 @@ rules:
   - id: over-writing-remainder
     name: Judge whether the reader acts differently for having read it
     kind: judgement
+    dimension: scope
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-scope.rejected-alternative
+      - prose-scope.implementation-leak
+    judgement_contract:
+      admission: >-
+        The paragraph contains the rejected alternative or implementation detail a seed matched, and the behaviour
+        statement it surrounds is inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: content the genre exists to record, such as an ADR, a spec, or an audit
+        trail, outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'over-writing: cut it to the behavior; move the decision to an ADR, spec, or commit'
     scope: paragraph
@@ -2183,6 +2768,18 @@ rules:
   - id: unasked-for-rationale
     name: Delete the clause and keep the behavior
     kind: judgement
+    dimension: scope
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph defends a choice, and the behaviour the defence is attached to is inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: a reason the genre exists to record, and a constraint or measured
+        threshold a reader cannot recover from the text, outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'unasked-for rationale: delete the clause and keep the behavior, or move the reason to the commit'
     scope: paragraph
@@ -2221,6 +2818,20 @@ rules:
   - id: epigram-closer-remainder
     name: Judge whether a closing line adds a fact
     kind: judgement
+    dimension: staleness
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-scope.epigram
+    judgement_contract:
+      admission: >-
+        The paragraph's closing line is the epigram a seed matched, and the paragraph or table it closes is inside the
+        unit.
+      protects: >-
+        accessibility_repetition: a closing line that carries the one fact a scanning reader needs outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: 'epigram closer: the paragraph or table above already carried the content'
     scope: paragraph
@@ -2257,6 +2868,8 @@ rules:
   - id: formulaic-universal-heading
     name: Replace a universal slogan with a title
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'universal slogan: {match} -- title it with a noun phrase, or state one scoped fact'
     scope: paragraph
@@ -2302,6 +2915,8 @@ rules:
   - id: contrastive-inversion-frames
     name: Cut the strawman half of a contrastive frame
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: error
     message: 'contrastive inversion: {match} -- state what the thing is; cut the strawman'
     scope: paragraph
diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-figurative.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-figurative.yml
index 8ac380bb54..04a7637164 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-figurative.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-figurative.yml
@@ -28,6 +28,8 @@ rules:
   - id: figurative-sits
     name: Name the literal relation
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "sits": {match} -- write the literal relation: is at, rests with, is unused'
     scope: prose
@@ -55,6 +57,8 @@ rules:
   - id: figurative-runs
     name: Name the actual behaviour
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "runs": {match} -- name the behaviour, not the motion'
     scope: prose
@@ -80,6 +84,8 @@ rules:
   - id: figurative-falls
     name: Name the shortfall or the membership
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "falls": {match} -- name the shortfall, or say which set it belongs to'
     scope: prose
@@ -105,6 +111,8 @@ rules:
   - id: figurative-draws
     name: Name the source or the comparison
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "draws": {match} -- name the source, or state the comparison directly'
     scope: prose
@@ -130,6 +138,8 @@ rules:
   - id: figurative-casts
     name: State the doubt or the effect
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "casts": {match} -- state the doubt and what supports it'
     scope: prose
@@ -150,6 +160,8 @@ rules:
   - id: figurative-strikes
     name: State the effect or the tradeoff
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "strikes": {match} -- state the effect or the tradeoff directly'
     scope: prose
@@ -176,6 +188,8 @@ rules:
   - id: figurative-wins
     name: State the benefit or the outcome
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "wins": {match} -- state the benefit and its size'
     scope: prose
@@ -199,6 +213,8 @@ rules:
   - id: figurative-lends
     name: State what it adds or enables
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "lends": {match} -- say what it adds, or what it makes possible'
     scope: prose
@@ -219,6 +235,8 @@ rules:
   - id: figurative-rides
     name: Name the dependency or the mechanism
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "rides": {match} -- name what depends on what'
     scope: prose
@@ -242,6 +260,8 @@ rules:
   - id: figurative-loud
     name: Name the behaviour, not the volume
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "loud": {match} -- name what it actually does'
     scope: prose
@@ -265,6 +285,8 @@ rules:
   - id: resonate-overuse
     name: Name what connects and why
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'figurative "resonate": {match} -- name what connects, and with whom'
     scope: prose
@@ -288,6 +310,8 @@ rules:
   - id: colloquial-assessment
     name: State the assessment directly
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'colloquial assessment: {match} -- state the judgement and the evidence for it'
     scope: prose
@@ -322,6 +346,8 @@ rules:
   - id: promotional-puffery
     name: Use neutral, specific language
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'puffery: {match} -- replace with the fact that would justify it'
     scope: prose
@@ -350,6 +376,8 @@ rules:
   - id: strategy-buzzwords
     name: Describe the mechanism
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'strategy buzzword: {match} -- describe the actual mechanism or advantage'
     scope: prose
@@ -377,6 +405,8 @@ rules:
   - id: promotional-adjective-noun
     name: Cut the promotional adjective
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: 'promotional adjective: {match} -- delete it, or give the measurement'
     scope: prose
@@ -407,6 +437,8 @@ rules:
   - id: promotional-verbs
     name: Use the direct verb
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: 'promotional verb: {match} -- use the direct verb'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/docs-discipline.yml b/packages/slopvac-lint/src/slopvac/rules/docs-discipline.yml
index efad06be56..7e26524c73 100644
--- a/packages/slopvac-lint/src/slopvac/rules/docs-discipline.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/docs-discipline.yml
@@ -10,6 +10,8 @@ rules:
     exceptions: [quotation]
     name: State what the artifact does at HEAD
     kind: pattern
+    dimension: veracity
+    ownership: deterministic
     severity: error
     message: 'status language: {match} -- state what the artifact does at HEAD'
     scope: prose
@@ -41,6 +43,8 @@ rules:
     exceptions: [quotation]
     name: Keep deltas out of a doc body
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: error
     message: 'history narration: {match} -- deltas belong in change comms, not a doc body'
     scope: prose
@@ -67,6 +71,8 @@ rules:
     exceptions: [quotation]
     name: Keep internal references out of consumer docs
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: error
     message: 'internal reference: {match} -- consumer docs describe the released artifact only'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/orwell.yml b/packages/slopvac-lint/src/slopvac/rules/orwell.yml
index 313d5fb79f..056417ee91 100644
--- a/packages/slopvac-lint/src/slopvac/rules/orwell.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/orwell.yml
@@ -7,6 +7,8 @@ rules:
   - id: stale-figure
     name: Cut the stale figure
     kind: tokens
+    dimension: staleness
+    ownership: deterministic
     severity: error
     message: '"{match}" is a worn figure. State the fact it stands in for.'
     tiers: {strict: enforced, normal: enforced, relaxed: advisory}
@@ -50,6 +52,8 @@ rules:
   - id: not-un
     name: Drop the not-un formation
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Replace "{match}" with the positive adjective.'
     tiers: {strict: enforced, normal: enforced, relaxed: excluded}
@@ -67,6 +71,8 @@ rules:
   - id: compound-preposition
     name: Use the single preposition
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Use "{replacement}" rather than "{match}".'
     tiers: {strict: enforced, normal: enforced, relaxed: excluded}
@@ -98,6 +104,8 @@ rules:
   - id: unsupported-evaluative
     name: Back the adjective or cut it
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: '"{match}" evaluates without evidence. Add the number, or cut the word.'
     tiers: {strict: enforced, normal: enforced, relaxed: advisory}
@@ -146,6 +154,19 @@ rules:
   - id: concrete-floor
     name: Name a checkable particular
     kind: judgement
+    dimension: specificity
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The unit makes a factual claim about the artifact, and any number, identifier, path, command, or dated event
+        it offers is inside the unit.
+      protects: >-
+        l2_clarity and defined_domain_term: a general statement that opens a section, and a defined term standing for
+        a class rather than an instance, outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     message: This paragraph makes a factual claim with no checkable particular.
     tiers: {strict: enforced, normal: enforced, relaxed: advisory}
     judgement_question: >-
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-agency.yml b/packages/slopvac-lint/src/slopvac/rules/prose-agency.yml
index 0d9ca23788..ecdeedb087 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-agency.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-agency.yml
@@ -10,6 +10,8 @@ rules:
   - id: false-agency
     name: Name who acted
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'false agency: {match} -- name who acted'
     scope: prose
@@ -47,6 +49,8 @@ rules:
     exceptions: [quotation]
     name: Name who acted in a passive
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'agentless passive: {match} -- name who acted'
     scope: prose
@@ -76,6 +80,8 @@ rules:
   - id: anthropomorphism
     name: Name the mechanism, not a mind
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'anthropomorphism: {match} -- name the mechanism, not a mind'
     scope: prose
@@ -106,6 +112,8 @@ rules:
   - id: narrator-distance
     name: Put the reader in the scene
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'narrator-from-a-distance: {match} -- put the reader in the scene, or name who acted'
     scope: prose
@@ -134,6 +142,8 @@ rules:
   - id: unattributed-recommendation
     name: Name who recommends it
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: error
     message: 'unattributed recommendation: {match} -- name who recommends it, or give the instruction'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-craft.yml b/packages/slopvac-lint/src/slopvac/rules/prose-craft.yml
index 701cbf89ba..8e58036a23 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-craft.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-craft.yml
@@ -11,6 +11,8 @@ rules:
   - id: acronym-periods
     name: Write an initialism unpunctuated
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'initialism periods: {match} -- write it unpunctuated'
     scope: prose
@@ -37,6 +39,8 @@ rules:
   - id: ambiguity
     name: Pick the reading you meant
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'ambiguous: {match} -- pick the reading you meant'
     scope: prose
@@ -70,6 +74,8 @@ rules:
     exceptions: [quotation]
     name: Move an annotation to an issue
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: warning
     message: 'annotation: {match} -- move it to an issue or a code comment'
     scope: prose
@@ -97,6 +103,8 @@ rules:
   - id: articles
     name: Match the article to the initialism's pronunciation
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: "article: use '{replacement}' instead of '{match}' (the article follows pronunciation)"
     scope: prose
@@ -163,6 +171,8 @@ rules:
   - id: command-prompt
     name: Drop the shell prompt from a command
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'shell prompt: {match} -- drop the prompt so the command can be copied'
     scope: raw
@@ -196,6 +206,8 @@ rules:
   - id: conflict-markers
     name: Resolve the merge conflict
     kind: pattern
+    dimension: veracity
+    ownership: deterministic
     severity: error
     message: 'merge conflict marker: {match} -- resolve the conflict'
     scope: raw
@@ -221,6 +233,8 @@ rules:
   - id: dead-opener
     name: Start the sentence with its real subject
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'dead opener: {match} -- start the sentence with its real subject'
     scope: prose
@@ -254,6 +268,8 @@ rules:
     exceptions: [quotation]
     name: Link the heading by name instead of by position
     kind: substitution
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: "directional reference: use '{replacement}' instead of '{match}', or link the heading by name"
     scope: prose
@@ -299,6 +315,8 @@ rules:
     exceptions: [quotation]
     name: Name the artifact, not the vendor
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: warning
     message: 'first-person plural: {match} -- name the artifact instead of the vendor'
     scope: prose
@@ -327,6 +345,8 @@ rules:
   - id: future-tense
     name: Describe what it does now
     kind: pattern
+    dimension: consistency
+    ownership: deterministic
     severity: warning
     message: 'future tense: {match} -- describe what it does now'
     scope: prose
@@ -357,6 +377,8 @@ rules:
   - id: gerund-heading
     name: Use the imperative in a task heading
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'gerund heading: {match} -- use the imperative (''Install'', not ''Installing'')'
     scope: heading
@@ -418,6 +440,8 @@ rules:
   - id: hyphens
     name: Drop the hyphen after an -ly adverb
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'adverb hyphen: {match} -- an -ly adverb takes no hyphen'
     scope: prose
@@ -460,6 +484,8 @@ rules:
     exceptions: [quotation]
     name: Use the English phrase
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: "Latin abbreviation: use '{replacement}' instead of '{match}'"
     scope: prose
@@ -496,6 +522,8 @@ rules:
   - id: link-text
     name: Name the destination in the link text
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'link text: {match} -- name the destination in the link text'
     scope: raw
@@ -526,6 +554,8 @@ rules:
   - id: misnomer
     name: Drop the word the initialism already contains
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'misnomer: {match} -- the initialism already contains that word'
     scope: prose
@@ -555,6 +585,8 @@ rules:
   - id: negative-requirement
     name: State what is required
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'negative requirement: {match} -- state what is required, not what is forbidden'
     scope: prose
@@ -580,6 +612,8 @@ rules:
   - id: optional-plural
     name: Use the plural
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'optional plural: {match} -- use the plural'
     scope: prose
@@ -605,6 +639,8 @@ rules:
   - id: ordinals
     name: Write the word ordinal, or let the list carry the order
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'ordinal: {match} -- use ''first'', or let the list carry the order'
     scope: prose
@@ -631,6 +667,8 @@ rules:
   - id: politeness
     name: State the step, not a request
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'politeness: {match} -- an instruction is not a request; state the step'
     scope: prose
@@ -660,6 +698,8 @@ rules:
   - id: redundancy
     name: Cut the repeated half
     kind: pattern
+    dimension: redundancy
+    ownership: deterministic
     severity: warning
     message: 'redundant: {match} -- cut the repeated half'
     scope: prose
@@ -688,6 +728,8 @@ rules:
   - id: relative-date
     name: Give the absolute date or version
     kind: pattern
+    dimension: specificity
+    ownership: deterministic
     severity: warning
     message: 'relative date: {match} -- give the absolute date or version'
     scope: prose
@@ -716,6 +758,8 @@ rules:
   - id: self-reference
     name: Start with the first new fact
     kind: pattern
+    dimension: redundancy
+    ownership: deterministic
     severity: warning
     message: 'self-reference: {match} -- the heading already says this; start with the first new fact'
     scope: prose
@@ -748,6 +792,8 @@ rules:
   - id: sentence-length
     name: Split a long sentence
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'sentence of {match} words > 34 -- split it, or convert the enumeration to a list'
     scope: sentence
@@ -775,6 +821,8 @@ rules:
   - id: spacing
     name: Use one space after a period
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'sentence spacing: {match} -- use exactly one space after the period'
     scope: prose
@@ -803,6 +851,8 @@ rules:
   - id: unclear-antecedent
     name: Name the noun the demonstrative points at
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'unclear antecedent: {match} -- name the noun the demonstrative points at'
     scope: prose
@@ -830,6 +880,8 @@ rules:
   - id: versions
     name: State version order, not magnitude
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: "version comparison: use '{replacement}' instead of '{match}'"
     scope: prose
@@ -861,6 +913,8 @@ rules:
     exceptions: [quotation]
     name: Use the short word
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: "wordy: use '{replacement}' instead of '{match}'"
     scope: prose
@@ -1012,6 +1066,8 @@ rules:
   - id: plural-abbreviation
     name: Drop the apostrophe from a plural initialism
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'plural initialism: {match} -- drop the apostrophe'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml b/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
index c62dd561fc..10afadcd5c 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
@@ -16,6 +16,20 @@ rules:
   - id: competing-actor-terms
     name: Pick one term for one subject
     kind: judgement
+    dimension: consistency
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-words.inconsistent-term-for-same-thing
+    judgement_contract:
+      admission: >-
+        The document uses two or more actor terms, and every term is quotable inside the unit.
+      protects: >-
+        defined_domain_term and l2_clarity: two actor terms the document defines as different subjects at first use
+        outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     message: >-
       Two or more terms name what may be the same subject. Pick one and use it
       everywhere, or state the distinction at first use.
@@ -30,6 +44,7 @@ rules:
       operator, admin, developer, integrator, subscriber, end user. For each
       pair, do they name the same subject? If yes, that is rotation and one term
       must win. If no, does the document define the difference at first use?
+    exceptions:
       - defined-distinction
       - quotation
       - api-name
@@ -67,6 +82,8 @@ rules:
   - id: frozen-verb
     name: Put the action in the verb
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: error
     message: >-
       "{match}" freezes the action in a noun. Use the plain verb.
@@ -117,6 +134,8 @@ rules:
   - id: run-on
     name: Split the run-on
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: >-
       This sentence stitches {match} independent ideas together; the limit is
@@ -162,6 +181,8 @@ rules:
   - id: phrasal-verb
     name: Use the plain verb
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Use "{replacement}" rather than "{match}".'
     scope: prose
@@ -260,6 +281,23 @@ rules:
   - id: marketing-register
     name: Describe, do not sell
     kind: judgement
+    dimension: inflation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-discipline.marketing-lexicon
+      - orwell.unsupported-evaluative
+      - prose-promotion.promotional-puffery
+    judgement_contract:
+      admission: >-
+        The paragraph contains the evaluative claim a seed matched, and the sentence that would support it is in the
+        same unit or the one after it.
+      protects: >-
+        formal_legal and defined_domain_term: a claim a licence, a trademark, or a defined term of art fixes outranks
+        this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     message: >-
       This passage sells rather than describes. State what the artifact does and
       what a reader can measure.
@@ -274,6 +312,7 @@ rules:
       next one? And would the claim's opposite be recognized as a disagreement
       about fact rather than a difference of opinion? A claim that fails both is
       marketing.
+    exceptions:
       - quantified
       - quotation
       - defined-term-of-art
@@ -304,6 +343,8 @@ rules:
   - id: marketing-lexicon
     name: Cut the marketing adjective
     kind: tokens
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: '"{match}" is sales register. State the measurable fact instead.'
     scope: prose
@@ -375,6 +416,21 @@ rules:
   - id: overloaded-sentence
     name: One sentence, one idea
     kind: judgement
+    dimension: architecture
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-discipline.run-on
+      - prose-craft.sentence-length
+    judgement_contract:
+      admission: >-
+        The sentence is the one a length or run-on seed matched, and its clause boundaries are inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: a sentence whose normative force or invariant depends on staying one
+        clause outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     message: >-
       This sentence carries more than one idea. Split it at the point where the
       reader has to start holding something new.
@@ -390,6 +446,7 @@ rules:
       A list of parallel actions sharing one subject and one verb is ONE idea,
       however long; two clauses joined by "and" that could each stand alone are
       two.
+    exceptions:
       - quotation
       - code-span
       - vertical-list
@@ -435,6 +492,24 @@ rules:
   - id: hedged-into-uselessness
     name: The document must assert something
     kind: judgement
+    dimension: inflation
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-discipline.bidirectional-hedge
+      - prose-discipline.hedged-hedge
+      - prose-inflation.hedge-stack
+      - prose-inflation.additive-hedge
+    judgement_contract:
+      admission: >-
+        The unit is a whole document, at least one hedge a seed matched is inside it, and the load-bearing claims the
+        hedges attach to are quotable.
+      protects: >-
+        formal_legal and technical_invariant: a hedge a warranty disclaimer, a safety statement, or a measured
+        variance requires outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     message: >-
       This document hedges its own claims to the point of asserting nothing. Take
       the position the evidence supports.
@@ -453,6 +528,7 @@ rules:
       help in some cases")? A document where the majority of load-bearing claims
       carry a hedge is a document that says nothing, whatever each sentence
       looks like on its own.
+    exceptions:
       - genuine-uncertainty
       - quotation
       - legal-force
@@ -495,6 +571,8 @@ rules:
   - id: bidirectional-hedge
     name: Do not hedge both ways
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: >-
       "{match}" hedges in both directions, so the two halves cancel. State which
@@ -537,6 +615,8 @@ rules:
   - id: hedged-hedge
     name: One hedge or none
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: >-
       "{match}" hedges a hedge. Keep at most one, or state the claim plainly.
@@ -580,6 +660,22 @@ rules:
   - id: bare-quantifier-with-figure-available
     name: Give the bare quantifier its number
     kind: judgement
+    dimension: specificity
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - prose-inflation.vague-quantifier
+      - ai-tells-content-shape.fake-specificity
+    judgement_contract:
+      admission: >-
+        The document contains the bare quantifier a seed matched together with the count, list, or measurement it
+        quantifies over, both inside the unit.
+      protects: >-
+        technical_invariant and formal_legal: a quantifier over a genuinely unbounded set, and one a standard's
+        wording fixes, outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     message: >-
       A bare quantifier stands where a figure was available. Give the number.
     scope: document
@@ -595,6 +691,7 @@ rules:
       or over a measurement it reports is a withheld figure and must be
       replaced. A quantifier over a genuinely unbounded or unmeasured set is
       correct and stays.
+    exceptions:
       - genuinely-unmeasured
       - quotation
       - unbounded-set
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-format.yml b/packages/slopvac-lint/src/slopvac/rules/prose-format.yml
index 800cb5e14e..05f9fe9b2e 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-format.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-format.yml
@@ -9,6 +9,8 @@ rules:
   - id: no-unicode-dash
     name: Write ASCII double-hyphen instead of an em or en dash
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: error
     message: 'em/en dash: {match} -- write `--` instead, or a comma, colon, or two sentences'
     scope: raw
@@ -50,6 +52,8 @@ rules:
   - id: emoji-heading
     name: Delete emoji from a heading
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: 'emoji in heading: {match} -- delete it'
     scope: heading
@@ -77,6 +81,8 @@ rules:
   - id: prose-block
     name: Convert a long paragraph to a list or table
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'prose block of {match} words > 80 -- convert to a list or table'
     scope: paragraph
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-inclusive.yml b/packages/slopvac-lint/src/slopvac/rules/prose-inclusive.yml
index f6430ad181..7b22d9e628 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-inclusive.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-inclusive.yml
@@ -9,6 +9,8 @@ rules:
   - id: ableist
     name: Replace a disability metaphor with the plainer word
     kind: substitution
+    dimension: inclusion
+    ownership: deterministic
     severity: warning
     message: "ableist: consider {replacement} instead of '{match}'"
     scope: prose
@@ -66,6 +68,8 @@ rules:
   - id: device-assumption
     name: Do not assume the reader's input device
     kind: substitution
+    dimension: inclusion
+    ownership: deterministic
     severity: warning
     message: "device assumption: use {replacement} instead of '{match}'"
     scope: prose
@@ -105,6 +109,8 @@ rules:
   - id: exclusive
     name: Replace an exclusionary term with its settled form
     kind: substitution
+    dimension: inclusion
+    ownership: deterministic
     severity: warning
     message: "exclusionary term: use {replacement} instead of '{match}'"
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-inflation.yml b/packages/slopvac-lint/src/slopvac/rules/prose-inflation.yml
index 14915aa488..b95de132d5 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-inflation.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-inflation.yml
@@ -11,6 +11,8 @@ rules:
     exceptions: [quotation]
     name: Replace a marketing adjective with a measurable claim
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'slop lexicon: {match} -- delete it or replace it with a measurable claim'
     scope: prose
@@ -38,6 +40,8 @@ rules:
   - id: business-jargon
     name: Use the plain verb
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'business jargon: {match} -- use the plain verb'
     scope: prose
@@ -67,6 +71,8 @@ rules:
     exceptions: [quotation]
     name: Name the specific thing
     kind: pattern
+    dimension: specificity
+    ownership: deterministic
     severity: error
     message: 'vague declarative: {match} -- name the specific thing'
     scope: prose
@@ -92,6 +98,8 @@ rules:
   - id: additive-hedge
     name: Keep the claim that carries load
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'additive hedge: {match} -- keep the claim that carries load'
     scope: prose
@@ -118,6 +126,8 @@ rules:
   - id: hedge-stack
     name: One hedge or none
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'stacked hedge: {match} -- one hedge or none; commit to the claim or cut it'
     scope: prose
@@ -146,6 +156,8 @@ rules:
   - id: intensifier
     name: Delete the degree adverb
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'intensifier: {match} -- delete it, or replace the adjective with a number'
     scope: prose
@@ -175,6 +187,8 @@ rules:
     exceptions: [quotation]
     name: Drop the intensifier from an absolute
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: error
     message: 'not comparable: {match} -- the adjective is already absolute; drop the intensifier'
     scope: prose
@@ -205,6 +219,8 @@ rules:
     exceptions: [quotation]
     name: Give the count
     kind: pattern
+    dimension: specificity
+    ownership: deterministic
     severity: warning
     message: 'vague quantifier: {match} -- give the count, or name the cases'
     scope: prose
@@ -240,6 +256,8 @@ rules:
     exceptions: [quotation]
     name: Use the verb, not the noun
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: error
     message: 'nominalisation: {match} -- use the verb (''validate'', not ''perform validation'')'
     scope: prose
@@ -272,6 +290,8 @@ rules:
   - id: document-preamble
     name: Start with the first fact
     kind: pattern
+    dimension: redundancy
+    ownership: deterministic
     severity: error
     message: 'preamble: {match} -- the title already says this; start with the first fact'
     scope: prose
@@ -302,6 +322,8 @@ rules:
   - id: apologizing
     name: Answer the question or cut the passage
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: error
     message: 'deferred claim: {match} -- answer it, or cut the passage that raises it'
     scope: prose
@@ -332,6 +354,8 @@ rules:
     exceptions: [quotation]
     name: Back the claim with a number or example
     kind: pattern
+    dimension: inflation
+    ownership: deterministic
     severity: warning
     message: 'borderline hype: {match} -- keep it only if a number or example backs it'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
index 1b015836f3..4617b678c3 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
@@ -10,6 +10,8 @@ rules:
   - id: rejected-alternative
     name: Move the decision to an ADR, spec, or commit
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: error
     message: 'rejected alternative: {match} -- state what it does; the decision belongs in an ADR, spec, or commit'
     scope: prose
@@ -42,6 +44,8 @@ rules:
     exceptions: [quotation]
     name: Move a benchmark result out of the doc
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: error
     message: 'implementation leak: {match} -- the reader cannot act on this; move it to the commit, ADR, or spec'
     scope: paragraph
@@ -79,6 +83,8 @@ rules:
   - id: unrequested-reassurance
     name: State the positive, or say nothing
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: error
     message: 'unrequested reassurance: {match} -- state what it does, or say nothing'
     scope: prose
@@ -108,6 +114,8 @@ rules:
   - id: epigram
     name: Cut the closing flourish
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'epigram: {match} -- the section already made this point; cut the flourish'
     scope: paragraph
@@ -144,6 +152,8 @@ rules:
   - id: formulaic-subject-verb-slogan
     name: Replace a paired subject-verb slogan with a title
     kind: pattern
+    dimension: staleness
+    ownership: deterministic
     severity: warning
     message: 'formulaic slogan: {match} -- title it with a noun phrase, or state one scoped fact'
     scope: paragraph
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-descriptive.yml b/packages/slopvac-lint/src/slopvac/rules/ste-descriptive.yml
index 5f6a4eb60f..798afbf565 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-descriptive.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-descriptive.yml
@@ -10,6 +10,18 @@ rules:
   - id: information-not-gradual
     name: Give information gradually
     kind: judgement
+    dimension: architecture
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph has at least two sentences, and every term it introduces is inside the unit.
+      protects: >-
+        l2_clarity and defined_domain_term: an order a procedure fixes, and a term the glossary defines before the
+        document begins, outrank this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check that this paragraph introduces one idea at a time.
     scope: paragraph
@@ -22,6 +34,7 @@ rules:
       Does each sentence introduce at most one new idea, and does every term appear after
       the sentence that introduced it? If a reader must already know a later term to parse
       an earlier sentence, reorder.
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -46,6 +59,18 @@ rules:
   - id: missing-key-word-structure
     name: Use key words to structure the text
     kind: judgement
+    dimension: consistency
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph has at least two consecutive sentences whose key words are quotable inside the unit.
+      protects: >-
+        defined_domain_term and l2_clarity: a key word the controlled vocabulary fixes, and a second term a non-native
+        reader needs, outrank this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check that this paragraph repeats its key words instead of varying them.
     scope: paragraph
@@ -57,6 +82,7 @@ rules:
     judgement_question: >-
       Does each sentence pick up a key word or key phrase from the sentence before it, and
       is that key word written the same way each time?
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -78,6 +104,8 @@ rules:
   - id: sentence-too-long-descriptive
     name: Keep an explanatory sentence to twenty-five words
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: error
     message: 'This sentence has {value} words. Use twenty-five or fewer.'
     scope: sentence
@@ -115,6 +143,17 @@ rules:
   - id: paragraph-without-related-information
     name: Group related information in a paragraph
     kind: judgement
+    dimension: architecture
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph has at least two sentences, and its first sentence is quotable inside the unit.
+      protects: >-
+        l2_clarity and formal_legal: an opening a template or a standard fixes outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check that this paragraph opens with a topic sentence.
     scope: paragraph
@@ -126,6 +165,7 @@ rules:
     judgement_question: >-
       Does the first sentence of this paragraph tell the reader what the paragraph is about,
       and does every later sentence add to that topic?
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -147,6 +187,22 @@ rules:
   - id: paragraph-has-multiple-topics
     name: Keep one topic per paragraph
     kind: judgement
+    dimension: architecture
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-descriptive.paragraph-too-many-sentences
+      - prose-format.prose-block
+    judgement_contract:
+      admission: >-
+        The paragraph is the one a length seed matched, and the sentence boundary a split would use is inside the
+        unit.
+      protects: >-
+        l2_clarity and technical_invariant: a paragraph whose halves depend on each other, or whose order a procedure
+        fixes, outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check that this paragraph carries one topic.
     scope: paragraph
@@ -158,6 +214,7 @@ rules:
     judgement_question: >-
       Could this paragraph be split at any sentence boundary without either half needing the
       other? If yes, it carries more than one topic.
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -180,6 +237,8 @@ rules:
   - id: paragraph-too-many-sentences
     name: Keep a paragraph to six sentences
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'This paragraph has {value} sentences. Use six or fewer.'
     scope: paragraph
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml b/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
index 4a5b1f2cd3..b06431070b 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
@@ -10,6 +10,8 @@ rules:
   - id: multiword-noun-too-long
     name: Keep a noun stack to three words
     kind: metric
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'This noun stack has {value} words. Use three or fewer.'
     scope: sentence
@@ -47,6 +49,21 @@ rules:
   - id: long-domain-term-without-short-form
     name: Give a short form for a long domain term
     kind: judgement
+    dimension: consistency
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-nouns.multiword-noun-too-long
+    judgement_contract:
+      admission: >-
+        The document contains the long domain term a seed matched, at its first use and at a later use, both inside
+        the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a term whose full spelling an identifier, an API name, or a
+        standard fixes outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this long domain term is written in full once and then given a short form.
     scope: document
@@ -59,6 +76,7 @@ rules:
       This domain term is longer than three words and cannot be shortened, because the
       project owns the name. Is it written in full at first use, and is either a short form
       declared or the words joined with hyphens as one unit?
+    exceptions:
       - code-span
       - identifier-fidelity
     allowlist: []
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-practices.yml b/packages/slopvac-lint/src/slopvac/rules/ste-practices.yml
index 895a4e49d3..4060c25d9c 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-practices.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-practices.yml
@@ -10,6 +10,22 @@ rules:
   - id: word-swap-insufficient
     name: Rewrite the sentence when a word swap fails
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-words.approved-word-substitution
+      - ste-practices.phrasal-verb
+    judgement_contract:
+      admission: >-
+        The sentence contains the word a substitution seed matched, and the whole clause the swap would change is
+        inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a word an identifier, an API name, or a defined term fixes
+        outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check whether this sentence needs a rewrite rather than a word swap.
     scope: sentence
@@ -22,6 +38,7 @@ rules:
       After you substitute the replacement word, is the sentence still grammatical, still
       meaningful, and still carrying your original meaning? If any of the three fails, or the
       word has no replacement at all, restructure the sentence instead.
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -42,6 +59,20 @@ rules:
   - id: word-sense-incorrect
     name: Use each word in its correct sense
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-words.word-used-in-wrong-part-of-speech
+    judgement_contract:
+      admission: >-
+        The sentence contains the vocabulary word a seed matched, and the clause that fixes its sense is inside the
+        unit.
+      protects: >-
+        defined_domain_term: a word whose sense the project's own vocabulary or glossary records outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that each word carries the sense the vocabulary records for it.
     scope: sentence
@@ -53,6 +84,7 @@ rules:
     judgement_question: >-
       For each vocabulary word in this sentence, does the sentence use the single sense the
       vocabulary entry records, rather than another common sense of the same spelling?
+    exceptions:
       - quotation
       - code-span
     allowlist: []
@@ -73,6 +105,8 @@ rules:
   - id: phrasal-verb
     name: Do not use a phrasal verb
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Phrasal verb "{match}". Use "{replacement}".'
     scope: prose
@@ -136,6 +170,8 @@ rules:
   - id: inconsistent-wording-for-same-step
     name: Word the same step the same way
     kind: structure
+    dimension: consistency
+    ownership: deterministic
     severity: warning
     message: 'This step is worded two ways in one document ("{match}" and "{other}").'
     scope: document
@@ -169,6 +205,8 @@ rules:
   - id: omitted-conjunction-that
     name: Keep the conjunction
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: suggestion
     message: 'Add "that" after "{match}".'
     scope: prose
@@ -210,6 +248,18 @@ rules:
   - id: ambiguous-preposition-with
     name: Keep the instrument sense clear
     kind: judgement
+    dimension: wording
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The sentence uses "with" outside a code span, and the anchors of every reading are inside the sentence.
+      protects: >-
+        defined_domain_term and technical_invariant: "with" inside a defined term, a command flag, or an API name
+        outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check which of the three senses "with" carries here.
     scope: sentence
@@ -222,6 +272,7 @@ rules:
       Does "with" mean an association, a shared action, or an instrument? If a reader could
       pick more than one, name the instrument in a separate clause or state the condition
       first.
+    exceptions:
       - quotation
       - code-span
     allowlist: []
@@ -242,6 +293,8 @@ rules:
   - id: unclear-pronoun
     name: Replace an unclear pronoun with the noun
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: suggestion
     message: 'Pronoun "{match}" may have more than one referent.'
     scope: sentence
@@ -276,6 +329,8 @@ rules:
   - id: unclear-demonstrative-this
     name: Give the referent for a bare demonstrative
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: suggestion
     message: 'Bare demonstrative "{match}". Name the thing it refers to.'
     scope: sentence
@@ -316,6 +371,8 @@ rules:
   - id: false-friend-term
     name: Avoid a false friend
     kind: substitution
+    dimension: inclusion
+    ownership: deterministic
     severity: suggestion
     message: '"{match}" reads differently to a non-native reader. Use "{replacement}".'
     scope: prose
@@ -369,6 +426,8 @@ rules:
   - id: latin-abbreviation
     name: Do not use a Latin abbreviation
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Use "{replacement}" rather than "{match}".'
     scope: prose
@@ -414,6 +473,8 @@ rules:
   - id: gendered-or-exclusionary-language
     name: Use inclusive language
     kind: substitution
+    dimension: inclusion
+    ownership: deterministic
     severity: warning
     message: 'Use "{replacement}" rather than "{match}".'
     scope: prose
@@ -463,6 +524,8 @@ rules:
   - id: possessive-form-unclear
     name: Use the possessive only when it is clear
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: suggestion
     message: 'Possessive "{match}" may be unclear. Consider "of the ...".'
     scope: prose
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-procedural.yml b/packages/slopvac-lint/src/slopvac/rules/ste-procedural.yml
index b28a5b099c..e2bd3c7582 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-procedural.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-procedural.yml
@@ -10,6 +10,8 @@ rules:
   - id: sentence-too-long-procedural
     name: Keep an instruction to twenty words
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: error
     message: 'This instruction has {value} words. Use twenty or fewer.'
     scope: sentence
@@ -45,6 +47,8 @@ rules:
   - id: multiple-instructions-per-sentence
     name: Write one instruction per sentence
     kind: pattern
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'This step carries more than one instruction ("{match}").'
     scope: sentence
@@ -82,6 +86,8 @@ rules:
   - id: instruction-not-imperative
     name: Write instructions in the imperative
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'This step is not in the imperative ("{match}").'
     scope: sentence
@@ -120,6 +126,8 @@ rules:
   - id: condition-after-command
     name: Put the condition before the command
     kind: pattern
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'The condition follows the command ("{match}"). Put the condition first.'
     scope: sentence
@@ -153,6 +161,8 @@ rules:
   - id: note-gives-instruction
     name: Keep notes free of instructions
     kind: pattern
+    dimension: scope
+    ownership: deterministic
     severity: warning
     message: 'This note gives an instruction ("{match}"). A note only gives information.'
     scope: paragraph
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-punctuation.yml b/packages/slopvac-lint/src/slopvac/rules/ste-punctuation.yml
index 46fe52fd49..012a80c5be 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-punctuation.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-punctuation.yml
@@ -10,6 +10,8 @@ rules:
   - id: semicolon-used
     name: Do not use a semicolon
     kind: pattern
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: The semicolon is not permitted. Write two sentences.
     scope: prose
@@ -43,6 +45,8 @@ rules:
   - id: hyphen-missing-in-compound-modifier
     name: Hyphenate a compound modifier before a noun
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: suggestion
     message: 'Hyphenate the compound modifier "{match}".'
     scope: prose
@@ -81,6 +85,8 @@ rules:
   - id: hyphen-group-too-long
     name: Do not hyphenate more than three words
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'This hyphen group joins more than three words ("{match}").'
     scope: prose
@@ -116,6 +122,18 @@ rules:
   - id: parentheses-misuse
     name: Use parentheses only for the listed purposes
     kind: judgement
+    dimension: architecture
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The sentence contains a parenthetical whose full text is inside the unit.
+      protects: >-
+        technical_invariant and defined_domain_term: a parenthetical carrying an identifier, a step number, an
+        abbreviation, or a cross-reference outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check that this parenthetical serves a listed purpose.
     scope: sentence
@@ -128,6 +146,7 @@ rules:
       Does this parenthetical give a cross-reference, an item identifier, a step number, an
       abbreviation, a singular-and-plural form, a short explanation, or an alternative? If it
       carries a second idea, promote it to its own sentence.
+    exceptions:
       - code-span
       - quotation
     allowlist: []
@@ -150,6 +169,8 @@ rules:
   - id: colon-terminates-sentence-for-count
     name: Count a list lead-in as its own sentence
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: error
     message: 'The lead-in before the colon has {value} words. Use the sentence cap.'
     scope: sentence
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-safety.yml b/packages/slopvac-lint/src/slopvac/rules/ste-safety.yml
index d70a1e8ce2..6d6b962272 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-safety.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-safety.yml
@@ -10,6 +10,21 @@ rules:
   - id: risk-level-word-missing-or-wrong
     name: Mark the risk level with the right word
     kind: judgement
+    dimension: veracity
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-safety.safety-block-missing-consequence
+    judgement_contract:
+      admission: >-
+        The paragraph is a safety block whose stated consequence is inside the unit, so the real risk level can be
+        read from the text.
+      protects: >-
+        formal_legal and technical_invariant: a marker a standard, a regulation, or the product's own safety scheme
+        fixes outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: error
+      rewrite_exempt: true
     severity: error
     message: Check that this block uses the risk word that matches its actual risk level.
     scope: paragraph
@@ -22,6 +37,7 @@ rules:
       Does this block describe a risk of harm to a person, or only a risk of damage to data,
       systems, or equipment? Harm to a person takes the higher marker; damage alone takes the
       lower one; when both apply, use the higher marker.
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -45,6 +61,8 @@ rules:
   - id: safety-block-does-not-start-with-command
     name: Start a safety block with the command or the condition
     kind: pattern
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'This safety block does not open with a command or condition ("{match}").'
     scope: paragraph
@@ -79,6 +97,8 @@ rules:
   - id: safety-block-missing-consequence
     name: Explain the consequence
     kind: structure
+    dimension: specificity
+    ownership: deterministic
     severity: error
     message: This safety block gives no explanation of the risk or the result.
     scope: paragraph
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-sentences.yml b/packages/slopvac-lint/src/slopvac/rules/ste-sentences.yml
index 9527165971..5567e0c042 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-sentences.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-sentences.yml
@@ -10,6 +10,22 @@ rules:
   - id: sentence-not-short-or-clear
     name: Write short and clear sentences
     kind: judgement
+    dimension: architecture
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-descriptive.sentence-too-long-descriptive
+      - ste-procedural.sentence-too-long-procedural
+    judgement_contract:
+      admission: >-
+        The sentence is the one a length seed matched, and the instruction or topic boundary a split would use is
+        inside the unit.
+      protects: >-
+        formal_legal and technical_invariant: a sentence whose normative force or step order depends on staying whole
+        outranks this rule.
+      dims: [FIT, WARRANT, HARM]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check that this sentence carries one instruction or one topic.
     scope: sentence
@@ -21,6 +37,7 @@ rules:
     judgement_question: >-
       Does this sentence give exactly one instruction (in a procedure) or carry exactly one
       topic (in description)? If it carries more, split it.
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -45,6 +62,8 @@ rules:
   - id: omitted-word-or-contraction
     name: Do not omit words or use contractions
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Omitted word or contraction "{match}". Write the full form.'
     scope: sentence
@@ -83,6 +102,8 @@ rules:
   - id: complex-text-not-in-vertical-list
     name: Use a vertical list for complex content
     kind: metric
+    dimension: architecture
+    ownership: deterministic
     severity: warning
     message: 'This sentence carries {value} coordinated items. Use a vertical list.'
     scope: sentence
@@ -122,6 +143,8 @@ rules:
   - id: vertical-list-lead-in-missing-colon
     name: End the list lead-in with a colon
     kind: structure
+    dimension: presentation
+    ownership: deterministic
     severity: warning
     message: The sentence before a vertical list must end with a colon.
     scope: paragraph
@@ -155,6 +178,8 @@ rules:
   - id: vertical-list-item-punctuation
     name: Punctuate list items consistently
     kind: structure
+    dimension: presentation
+    ownership: deterministic
     severity: suggestion
     message: 'List item punctuation is wrong: {detail}.'
     scope: paragraph
@@ -194,6 +219,17 @@ rules:
   - id: missing-connector-between-related-sentences
     name: Connect related sentences
     kind: judgement
+    dimension: architecture
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The paragraph holds two consecutive sentences, both quotable inside the unit.
+      protects: >-
+        l2_clarity: a pair a procedure needs as two separate steps, with no relation to name, outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 2
+      judgement_ceiling: suggestion
+      rewrite_exempt: false
     severity: suggestion
     message: Check whether these two sentences need a connecting word.
     scope: paragraph
@@ -205,6 +241,7 @@ rules:
     judgement_question: >-
       Does the second sentence add a result, a contrast, or a next step to the first? If
       yes, does a connecting word or phrase make that relation explicit?
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -222,6 +259,8 @@ rules:
   - id: missing-article-or-determiner
     name: Use an article or a demonstrative before a noun
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Missing article before "{match}".'
     scope: sentence
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-verbs.yml b/packages/slopvac-lint/src/slopvac/rules/ste-verbs.yml
index 4c007a59f6..5ba0715718 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-verbs.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-verbs.yml
@@ -10,6 +10,8 @@ rules:
   - id: verb-form-not-listed
     name: Use only listed verb forms
     kind: vocabulary
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: '"{match}" is not a listed form of "{lemma}".'
     scope: prose
@@ -38,6 +40,8 @@ rules:
   - id: complex-tense
     name: Use simple tenses only
     kind: pattern
+    dimension: consistency
+    ownership: deterministic
     severity: error
     message: 'Complex verb construction "{match}". Use a simple present, past, or future tense.'
     scope: sentence
@@ -82,6 +86,22 @@ rules:
   - id: past-participle-not-adjectival
     name: Use a past participle only as an adjective
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-verbs.complex-tense
+      - ste-verbs.auxiliary-stacking
+    judgement_contract:
+      admission: >-
+        The sentence contains the participle a verb-form seed matched, together with the auxiliary or the noun it
+        attaches to.
+      protects: >-
+        defined_domain_term and technical_invariant: a participle inside a defined term, an identifier, or a normative
+        clause outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this past participle acts as an adjective, not as part of a verb.
     scope: sentence
@@ -94,6 +114,7 @@ rules:
       Does this past participle sit before a noun, or after a form of "be", "become", or
       "stay", describing a condition? If it sits after another auxiliary, it is part of a
       verb construction and is not permitted.
+    exceptions:
       - quotation
       - code-span
     allowlist: []
@@ -116,6 +137,8 @@ rules:
   - id: auxiliary-stacking
     name: Do not stack auxiliaries
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Auxiliary stack "{match}". Give the action directly.'
     scope: sentence
@@ -158,6 +181,20 @@ rules:
   - id: gerund-outside-noun-use
     name: Use an -ing form only as a noun or a noun modifier
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-verbs.nominalized-action
+    judgement_contract:
+      admission: >-
+        The sentence contains the -ing form a seed matched, and the clause whose action it may carry is inside the
+        unit.
+      protects: >-
+        defined_domain_term: an -ing form registered as a domain noun, or part of one, outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this -ing form works as a noun or as part of a noun, not as a verb.
     scope: sentence
@@ -169,6 +206,7 @@ rules:
     judgement_question: >-
       Is this -ing word a noun (the name of a thing or a process), or a modifier inside a
       domain noun? If it carries the action of the clause, rewrite it.
+    exceptions:
       - quotation
       - code-span
       - registered-domain-term
@@ -192,6 +230,8 @@ rules:
   - id: passive-voice
     name: Use the active voice
     kind: pattern
+    dimension: agency
+    ownership: deterministic
     severity: warning
     message: 'Passive voice "{match}". Name the actor and use the active voice.'
     scope: sentence
@@ -279,6 +319,8 @@ rules:
   - id: nominalized-action
     name: State an action with a verb
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Nominalized action "{match}". Use the verb.'
     scope: sentence
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-words.yml b/packages/slopvac-lint/src/slopvac/rules/ste-words.yml
index d5301736ed..fd1c02d08a 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-words.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-words.yml
@@ -10,6 +10,8 @@ rules:
   - id: word-outside-controlled-vocabulary
     name: Do not use a word this project refuses
     kind: vocabulary
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: '"{match}" is on this project''s word blocklist.'
     scope: prose
@@ -62,6 +64,8 @@ rules:
   - id: approved-word-substitution
     name: Use the controlled replacement word
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Use "{replacement}" rather than "{match}".'
     scope: prose
@@ -114,6 +118,8 @@ rules:
   - id: obligation-word-substitution
     name: Use one obligation word
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Use "{replacement}" rather than "{match}".'
     scope: prose
@@ -162,6 +168,8 @@ rules:
   - id: word-used-in-wrong-part-of-speech
     name: Use the word only in its permitted part of speech
     kind: vocabulary
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: '"{match}" is permitted as {allowed_pos} but not as {found_pos}.'
     scope: prose
@@ -192,6 +200,20 @@ rules:
   - id: word-used-outside-permitted-sense
     name: Use the word only in its permitted sense
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-words.word-outside-controlled-vocabulary
+    judgement_contract:
+      admission: >-
+        The sentence contains the controlled word a seed matched, and the clause that fixes its meaning is inside the
+        unit.
+      protects: >-
+        defined_domain_term: a word whose permitted sense the vocabulary entry itself records outranks this rule.
+      dims: [FIT, WARRANT, REPAIR]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that each controlled word carries its permitted meaning.
     scope: sentence
@@ -203,6 +225,7 @@ rules:
     judgement_question: >-
       Does every controlled word in this sentence carry the single meaning recorded in the
       vocabulary entry, rather than another dictionary meaning of the same spelling?
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -220,6 +243,8 @@ rules:
   - id: verb-or-adjective-form-not-permitted
     name: Use only permitted word forms
     kind: vocabulary
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: '"{match}" is not a permitted form of "{lemma}".'
     scope: prose
@@ -248,6 +273,21 @@ rules:
   - id: domain-noun-category-membership
     name: Confirm the domain noun belongs to a declared category
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-words.word-outside-controlled-vocabulary
+    judgement_contract:
+      admission: >-
+        The sentence contains the out-of-vocabulary noun a seed matched, outside a code span, and the check needs the
+        project's declared domain-noun categories as a repo fact.
+      protects: >-
+        defined_domain_term and technical_invariant: a noun an identifier, an API name, or a schema fixes outranks
+        this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that each out-of-vocabulary noun belongs to a declared domain-noun category.
     scope: sentence
@@ -260,6 +300,7 @@ rules:
       For each noun in this sentence that is not in the controlled vocabulary, does it name
       a specified concept inside one of the declared domain-noun categories for this
       project?
+    exceptions:
       - code-span
       - identifier-fidelity
     allowlist: []
@@ -278,6 +319,21 @@ rules:
   - id: unapproved-word-not-a-domain-noun
     name: Allow an out-of-vocabulary word only as a domain noun
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-words.word-outside-controlled-vocabulary
+    judgement_contract:
+      admission: >-
+        The sentence contains the out-of-vocabulary word a seed matched, and the multi-word noun it may belong to is
+        inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a word inside a registered domain noun, an identifier, or an API
+        name outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this out-of-vocabulary word is a domain noun or part of one.
     scope: sentence
@@ -289,6 +345,7 @@ rules:
     judgement_question: >-
       Is this out-of-vocabulary word a domain noun, or a word inside a multi-word domain
       noun? If it is neither, it must be replaced.
+    exceptions:
       - code-span
       - identifier-fidelity
       - quotation
@@ -308,6 +365,8 @@ rules:
   - id: noun-used-as-verb
     name: Do not use a domain noun as a verb
     kind: substitution
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Do not use "{match}" as a verb. Use "{replacement}".'
     scope: sentence
@@ -356,6 +415,18 @@ rules:
   - id: domain-noun-not-organization-approved
     name: Use the domain term your project already uses
     kind: judgement
+    dimension: consistency
+    ownership: document_probe
+    judgement_contract:
+      admission: >-
+        The document names a domain thing whose term is quotable inside the unit, and the check needs the project
+        glossary, API reference, or schema as a repo fact.
+      protects: >-
+        defined_domain_term: a term the glossary itself declares outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this term is the one your project's glossary defines.
     scope: document
@@ -367,6 +438,7 @@ rules:
     judgement_question: >-
       Does the project glossary, API reference, or schema already name this thing? If yes,
       does the document use that exact name?
+    exceptions:
       - quotation
     allowlist: []
     examples:
@@ -383,6 +455,20 @@ rules:
   - id: domain-noun-too-long-or-unclear
     name: Choose a short and clear domain term
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-nouns.multiword-noun-too-long
+    judgement_contract:
+      admission: >-
+        The sentence contains the invented multi-word term a seed matched, and its whole span is inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a term whose length an identifier, an API name, or a standard
+        fixes outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this new domain term is short and understandable.
     scope: sentence
@@ -412,6 +498,8 @@ rules:
   - id: slang-or-jargon-term
     name: Do not use slang or jargon as a domain term
     kind: tokens
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: '"{match}" is slang or jargon. Use a plain term.'
     scope: prose
@@ -462,6 +550,8 @@ rules:
   - id: inconsistent-term-for-same-thing
     name: Use one term per thing
     kind: structure
+    dimension: consistency
+    ownership: deterministic
     severity: warning
     message: 'This document calls the same thing "{match}" and "{other}".'
     scope: document
@@ -490,6 +580,20 @@ rules:
   - id: domain-verb-category-membership
     name: Confirm the domain verb belongs to a declared category
     kind: judgement
+    dimension: wording
+    ownership: seeded_adjudication
+    seed_rule_ids:
+      - ste-verbs.verb-form-not-listed
+    judgement_contract:
+      admission: >-
+        The sentence contains the out-of-vocabulary verb a seed matched, and the clause it governs is inside the unit.
+      protects: >-
+        defined_domain_term and technical_invariant: a verb an API name or a declared domain-verb category fixes
+        outranks this rule.
+      dims: [FIT, WARRANT]
+      evidence_arity: 1
+      judgement_ceiling: suggestion
+      rewrite_exempt: true
     severity: suggestion
     message: Check that this out-of-vocabulary verb is a declared domain verb used in its own context.
     scope: sentence
@@ -502,6 +606,7 @@ rules:
       Could this sentence be written with vocabulary verbs alone? If yes, the domain verb
       is not permitted. If no, does the verb belong to a declared domain-verb category and
       carry its category meaning in this sentence?
+    exceptions:
       - code-span
       - api-name
     allowlist: []
@@ -525,6 +630,8 @@ rules:
   - id: verb-used-as-noun
     name: Do not use a domain verb as a noun
     kind: pattern
+    dimension: wording
+    ownership: deterministic
     severity: warning
     message: 'Do not use "{match}" as a noun. Use the noun form.'
     scope: sentence


### 3567284749

3567284749 refactor(rules): clarify judgement contracts and exception wording


diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
index be2f942255..1d0cc16b3f 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
@@ -33,10 +33,10 @@ rules:
     judgement_contract:
       admission: >-
         The paragraph holds a negated-half contrast a seed matched, or one of the ambiguous bare-clause and
-        subjectless-imperative forms the seed leaves clean, and both halves are quotable inside the unit.
+        subjectless-imperative forms the seed leaves clean, and both halves are within the unit.
       protects: >-
-        factual_contrast and technical_invariant: a negated half that states a real boundary, a safety constraint, or
-        a documented invariant outranks this rule.
+        Exception: retain a negated half that states a real boundary, a safety constraint, or a documented invariant.
+
       dims: [FIT, WARRANT, REPAIR]
       evidence_arity: 2
       judgement_ceiling: suggestion
@@ -2858,10 +2858,8 @@ rules:
 id: ai-tells-agentic
 title: AI tells -- agentic slogan formulae
 description: >-
-  The formulae an agent reaches for when it has to name a section and has no fact
-  to name it with: a universal claim about a whole class, standing in for a title.
-  The shape is the tell, not the vocabulary, so these rules match syntax and a
-  rewritten slogan does not escape by swapping words.
+  Recurring agent-generated heading patterns that make a universal claim stand in for a section title.
+  The rule matches the syntactic shape, so replacing its vocabulary does not avoid it.
 weight: 1.5
 recommended_for: [consumer, internal, change-comms]
 rules:
@@ -2903,7 +2901,7 @@ rules:
         And the match runs to the end of the block through word characters only, so
         any terminal punctuation excludes it -- a heading carries none, a body
         sentence does. Together they select the title-shaped universal claim and leave
-        the class invariant, which is the one construction "every" is genuinely for.
+        the class invariant, which preserves uses of “every” that state a scoped invariant.
         `scope: paragraph`, not `heading`: the native engine's paragraph scope covers
         every rendered block INCLUDING headings, list items, and quotes, whereas
         heading scope compiles to a Vale `heading` payload and Vale then owns the
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml b/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
index 10afadcd5c..bdeb2ee99d 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
@@ -22,10 +22,9 @@ rules:
       - ste-words.inconsistent-term-for-same-thing
     judgement_contract:
       admission: >-
-        The document uses two or more actor terms, and every term is quotable inside the unit.
+        The unit uses two or more terms for the same actor; the occurrences needed to compare them are within the unit.
       protects: >-
-        defined_domain_term and l2_clarity: two actor terms the document defines as different subjects at first use
-        outrank this rule.
+        Exception: retain terms explicitly defined as different subjects at first use.
       dims: [FIT, WARRANT, HARM]
       evidence_arity: 2
       judgement_ceiling: suggestion
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml b/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
index b06431070b..e17f116f5a 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
@@ -55,11 +55,9 @@ rules:
       - ste-nouns.multiword-noun-too-long
     judgement_contract:
       admission: >-
-        The document contains the long domain term a seed matched, at its first use and at a later use, both inside
-        the unit.
+        The document contains the long domain term a seed matched at its first use and at a later use; both occurrences are within the unit.
       protects: >-
-        defined_domain_term and technical_invariant: a term whose full spelling an identifier, an API name, or a
-        standard fixes outranks this rule.
+        Exception: retain a spelling fixed by an identifier, API name, or standard.
       dims: [FIT, WARRANT]
       evidence_arity: 2
       judgement_ceiling: suggestion


### fc261aeb53

fc261aeb53 fix(benchmark): count abstentions as terminal scoring errors


diff --git a/bench/runner.py b/bench/runner.py
index 06ebb1b205..61458f34be 100755
--- a/bench/runner.py
+++ b/bench/runner.py
@@ -676,6 +676,7 @@ def score(cases: list[dict], results: list[dict]) -> dict[str, Any]:
         expected = "reject" if case.get("label") == "defect" else "preserve"
         if row["verdict"] == "abstain":
             out["abstains"] += 1
+            continue
         if row["verdict"] == expected:
             out["correct"] += 1
         elif case.get("label") == "control" and row["verdict"] == "reject":
@@ -692,6 +693,7 @@ def score(cases: list[dict], results: list[dict]) -> dict[str, Any]:
             + 4 * out["false_positives"]
             + 5 * out["false_confirms"]
             + 4 * out["misses"]
+            + 4 * out["abstains"]
             + 4 * out["missing"]
         )
         / count
diff --git a/benchmark_contract.json b/benchmark_contract.json
index cdd849b13d..1e802899ae 100644
--- a/benchmark_contract.json
+++ b/benchmark_contract.json
@@ -23,5 +23,11 @@
     "evidence_arity",
     "judgement_ceiling",
     "rewrite_exempt"
-  ]
+  ],
+  "abstain_policy": {
+    "classification": "error",
+    "terminal": true,
+    "penalty_weight": 4,
+    "description": "An abstain is counted once as an abstain error and is excluded from correct, false-positive, false-confirm, and miss classifications."
+  }
 }
diff --git a/tests/test_bench_runner.py b/tests/test_bench_runner.py
index 0e6afb7557..cc6592d5b2 100644
--- a/tests/test_bench_runner.py
+++ b/tests/test_bench_runner.py
@@ -225,10 +225,23 @@ def test_row_sets_get_precise_complaints(rows: object, expected: str) -> None:
     assert runner.validate_rows(CASES, rows) == expected
 
 
+
 def test_valid_row_set_passes() -> None:
     assert runner.validate_rows(CASES, [{"case_id": "a"}, {"case_id": "b"}]) is None
 
 
+def test_abstain_is_terminal_and_not_counted_as_a_miss() -> None:
+    cases = [{"id": "a", "text": "alpha", "label": "defect"}]
+    results = [{"case_id": "a", "verdict": "abstain", "quote": "alpha"}]
+
+    scored = runner.score(cases, results)
+
+    assert scored["abstains"] == 1
+    assert scored["misses"] == 0
+    assert scored["false_positives"] == 0
+    assert scored["false_confirms"] == 0
+
+
 def session(user_text: str, non_message_tokens: int = 9000) -> list[dict]:
     return [
         {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": user_text}]}},


### 90924e283d

90924e283d refactor(lint): remove duplicate contrastive inversion frame rule


diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
index 755c756e76..ad6137e6ba 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
@@ -22,41 +22,6 @@ description: >-
 weight: 1.5
 recommended_for: [consumer, internal, change-comms]
 rules:
-  - id: contrastive-inversion-frames
-    name: Cut the strawman half of a contrastive frame
-    kind: pattern
-    severity: error
-    message: 'contrastive inversion: {match} -- state what the thing is; cut the strawman'
-    scope: prose
-    tiers:
-      strict: enforced
-      normal: enforced
-      relaxed: advisory
-    pattern: '\b(?:it''s|it is|this isn''t|this is not|that''s not|it''s not|it isn''t)\s+(?:not|less about)\b[^.!?]{1,80}\b(?:it''s|it is|and more about|but rather)\b|(?:^|[.!?][ \t]+)(?:the|a|an|this|that|these|those|our|your|my|his|her|its|their)\s+[\w-]+(?:\s+[\w-]+){0,3}\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed))\b(?:\s+[\w-]+){0,6}\s*[,;]\s+(?:(?:it|this|that|they|these|those)\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must)\s+not|not)\s+[^.!?\n]{1,50}'
-    ignore_case: true
-    fix: Delete the negated half and state what the thing is.
-    examples:
-      - bad: It's not a linter, it's a review partner.
-        good: The linter reports 61 rules and scores the document.
-      - bad: It's less about speed and more about determinism.
-        good: The gate produces the same findings on every run.
-      - bad: The Harness Measures, It Does Not Judge
-        good: The Harness Measures.
-      - bad: The parser reads JSON; it does not read YAML.
-        good: The parser reads JSON.
-      - bad: The client supports HTTP; it does not support FTP.
-        good: The client supports HTTP.
-    provenance:
-      source: references/ai-tells/structure.md ("Contrastive inversion")
-      url: https://gc.ai/blog/ai-writing-pattern-to-know-contrastive-negation
-      note: >-
-        The mechanizable core of the single most-cited current tell. Judgement
-        remainder in ai-tells-structure.contrastive-inversion-remainder, which
-        covers the forms that carry no fixed frame. Upstream Vale
-        ai-tells.ContrastiveNegation and ai-tells.ContrastiveFormulas cover
-        overlapping ground and stay enabled, so expect duplicate findings until one
-        side is disabled.
-
   - id: contrastive-inversion-remainder
     name: Judge whether a contrast names a real alternative
     kind: judgement
@@ -92,10 +57,10 @@ rules:
       source: references/ai-tells/structure.md ("Contrastive inversion", "Strawman antithesis")
       url: https://gc.ai/blog/ai-writing-pattern-to-know-contrastive-negation
       note: >-
-        Judgement remainder of ai-tells-structure.contrastive-inversion-frames. The
+        Judgement remainder of ai-tells-agentic.contrastive-inversion-frames. The
         remainder needs a reader who knows whether the alternative exists, which no
         pattern can supply. Also absorbs the catalog's "Strawman antithesis" row,
-        whose "While other tools struggle, X ..." shape is the same defect.
+        whose "While other gates struggle, X ..." shape is the same defect.
 
   - id: definitional-negation-pair
     exceptions: [quotation, factual-correction]
@@ -136,7 +101,7 @@ rules:
       note: >-
         The two-sentence form of the contrastive inversion: "X is A. X is not B."
         and its mirror, with the subject repeated or pronominalised. The
-        single-sentence frame (ai-tells-structure.contrastive-inversion-frames)
+        single-sentence frame (ai-tells-agentic.contrastive-inversion-frames)
         stops at a sentence boundary, so this rule runs at paragraph scope, where
         the native engine matches against the whole block (list items and quotes
         included; Vale's paragraph scope skips both, so the rule stays native). The
@@ -2334,3 +2299,37 @@ rules:
         The comma-joined pair form is prose-scope.formulaic-subject-verb-slogan; the
         judgement remainder for a slogan carrying no fixed frame is
         ai-tells-content-shape.epigram-closer-remainder.
+  - id: contrastive-inversion-frames
+    name: Cut the strawman half of a contrastive frame
+    kind: pattern
+    severity: error
+    message: 'contrastive inversion: {match} -- state what the thing is; cut the strawman'
+    scope: paragraph
+    tiers:
+      strict: enforced
+      normal: enforced
+      relaxed: advisory
+    pattern: '\b(?:it''s|it is|this isn''t|this is not|that''s not|it''s not|it isn''t)\s+(?:not|less about)\b[^.!?]{1,80}\b(?:it''s|it is|and more about|but rather)\b|(?:^|[.!?][ \t]+)(?:the|a|an|this|that|these|those|our|your|my|his|her|its|their)\s+[\w-]+(?:\s+[\w-]+){0,3}\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed))\b(?:\s+[\w-]+){0,6}\s*[,;]\s+(?:(?:it|this|that|they|these|those)\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must)\s+not|not)\s+[^.!?\n]{1,50}'
+    ignore_case: true
+    fix: Delete the negated half and state what the thing is.
+    examples:
+      - bad: It's not a linter, it's a review partner.
+        good: The linter reports 61 rules and scores the document.
+      - bad: It's less about speed and more about determinism.
+        good: The gate produces the same findings on every run.
+      - bad: The Harness Measures, It Does Not Judge
+        good: The Harness Measures.
+      - bad: The parser reads JSON; it does not read YAML.
+        good: The parser reads JSON.
+      - bad: The client supports HTTP; it does not support FTP.
+        good: The client supports HTTP.
+    provenance:
+      source: references/ai-tells/structure.md ("Contrastive inversion")
+      url: https://gc.ai/blog/ai-writing-pattern-to-know-contrastive-negation
+      note: >-
+        The mechanizable core of the single most-cited current tell. Judgement
+        remainder in ai-tells-agentic.contrastive-inversion-remainder, which
+        covers the forms that carry no fixed frame. Upstream Vale
+        ai-tells.ContrastiveNegation and ai-tells.ContrastiveFormulas cover
+        overlapping ground and stay enabled, so expect duplicate findings until one
+        side is disabled.
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
index eaadaedf0c..1b015836f3 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
@@ -176,7 +176,7 @@ rules:
         keeps the rule off a factual contrast ("The parser reads JSON, not YAML.") and
         off a contrastive inversion whose second subject is a pronoun ("The Harness
         Measures, It Does Not Judge") -- that shape belongs to
-        ai-tells-structure.contrastive-inversion-frames.
+        ai-tells-agentic.contrastive-inversion-frames.
         The predicate alternation ends in `[a-z][\w-]*(?<!s)s` rather than `\w+s`, so a
         plural noun spelled with a double s ("The Address Class, The Access Class")
         cannot pose as a verb.


### 8aa80ba428

8aa80ba428 feat(lint): add formulaic heading detection rules


diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
index 3c9cc8262f..c9f7adf84c 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
@@ -22,6 +22,34 @@ description: >-
 weight: 1.5
 recommended_for: [consumer, internal, change-comms]
 rules:
+  - id: formulaic-universal-heading
+    name: Replace a universal slogan heading
+    kind: pattern
+    severity: warning
+    message: 'formulaic universal heading: {match} -- use a noun phrase or a scoped factual statement'
+    scope: heading
+    tiers:
+      strict: advisory
+      normal: advisory
+      relaxed: excluded
+    pattern: '^every\s+[a-z][\w-]*\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed|ing))\b(?:\s+[a-z][\w-]*){1,8}$'
+    ignore_case: true
+    fix: Rewrite the heading as a noun phrase or state one scoped fact.
+    examples:
+      - bad: Every Change Opens A Door
+        good: Change opportunities
+      - bad: Every Request Finds Its Way
+        good: Request routing
+      - good: Every request to this endpoint requires authentication
+    provenance:
+      source: references/content-shape.md ("Formulaic universal headings")
+      note: >-
+        The heading scope is part of the rule: a title must begin with Every,
+        use one singular noun, and immediately follow it with a finite-looking
+        predicate plus a short complement. This grammatical shape catches
+        universal slogans without matching body invariants such as "Every request
+        to this endpoint requires authentication".
+
   - id: contrastive-inversion-frames
     name: Cut the strawman half of a contrastive frame
     kind: pattern
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
index a8e346b433..2610406ce3 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
@@ -7,6 +7,35 @@ description: >-
 weight: 1.0
 recommended_for: [consumer, change-comms]
 rules:
+  - id: formulaic-subject-verb-slogan
+    name: Replace a parallel subject-verb slogan heading
+    kind: pattern
+    severity: warning
+    message: 'formulaic heading: {match} -- use a noun phrase or a scoped factual statement'
+    scope: heading
+    tiers:
+      strict: advisory
+      normal: advisory
+      relaxed: excluded
+    pattern: '^(?:the|a|an|this|that|these|those|our|your|their)\s+[a-z][\w-]*(?:\s+[a-z][\w-]*)?\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed|ing))\b(?:\s+[a-z][\w-]*){0,2},\s+(?:the|a|an|this|that|these|those|our|your|their)\s+[a-z][\w-]*(?:\s+[a-z][\w-]*)?\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed|ing))\b(?:\s+[a-z][\w-]*){0,2}$'
+    ignore_case: true
+    fix: Rewrite the heading as a noun phrase or state one scoped fact.
+    examples:
+      - bad: The Review Guides, The Reader Decides
+        good: Review guidance
+      - bad: The Service Learns, The Operator Knows
+        good: Service learning and operator knowledge
+    provenance:
+      source: references/content-shape.md ("Formulaic parallel headings")
+      note: >-
+        Heading scope is essential: the comma-separated pair is a slogan-shaped
+        title only when both short clauses have a determiner-led subject and a
+        finite-looking predicate. The pattern is grammatical rather than lexical,
+        and does not inspect body sentences or object-level contrasts such as
+        "Parser reads JSON, not YAML".
+
+
+
   - id: rejected-alternative
     name: Move the decision to an ADR, spec, or commit
     kind: pattern


### cace892253

cace892253 feat(lint): detect formulaic slogan headings
Two pattern rules for the title-shaped formulae an agent reaches for when a
section needs a name and no fact is available: the comma-joined
subject-verb pair (prose-scope.formulaic-subject-verb-slogan) and the
universal claim (ai-tells-agentic.formulaic-universal-heading), plus the
ai-tells-agentic category that carries the second one and its entries in
the three profile policy tables.

The previous attempt crashed the CLI before it emitted any JSON. Its
examples list carried a `good`-only entry, `Example.bad` is required, and
the loader's eager validation turned that into a ruleset error on stderr
with an empty stdout. It also filed the rule under the ai-tells-structure
category, so its qualified id was not the one it claimed.

Both rules match syntax rather than phrases, and each shape condition is
what keeps a real class invariant out: the predicate sits against the bare
subject, the complement is at least two words, and the match runs to the
end of the block through word characters only, so terminal punctuation
excludes it. A heading carries none; a body sentence does.

`scope: paragraph`, not `heading`: the native engine's paragraph scope
already covers every rendered block including headings, while heading
scope compiles to a Vale payload and Vale then owns the rule, which leaves
it unchecked whenever Vale does not run.


diff --git a/packages/slopvac-lint/src/slopvac/profiles.py b/packages/slopvac-lint/src/slopvac/profiles.py
index d071162d8a..b94fa9614f 100644
--- a/packages/slopvac-lint/src/slopvac/profiles.py
+++ b/packages/slopvac-lint/src/slopvac/profiles.py
@@ -34,6 +34,10 @@ _STRICT: dict[str, CategorySettings] = {
     "ai-tells-register": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.3, weight=1.5),
     "ai-tells-formatting": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.5, weight=0.8),
     "ai-tells-content-shape": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.2, weight=1.5),
+    # Heading-shaped slogans. WARNING rather than ERROR at every profile that runs
+    # them: the defect is a title that carries no fact, which costs the reader an
+    # outline entry and never a wrong instruction.
+    "ai-tells-agentic": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.3, weight=1.5),
     # A figurative verb has a literal alternative in any register, but the
     # budget is looser than the other ai-tells bands: these are single-word
     # matches, so one metaphor-heavy paragraph spends a tight budget outright.
@@ -74,6 +78,7 @@ _NORMAL: dict[str, CategorySettings] = {
     "ai-tells-register": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.6, weight=1.5),
     "ai-tells-formatting": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=0.8),
     "ai-tells-content-shape": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.5),
+    "ai-tells-agentic": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.6, weight=1.5),
     "ai-tells-figurative": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.8, weight=1.0),
     "prose-inflation": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.6, weight=1.5),
     "prose-promotion": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.2),
@@ -114,6 +119,9 @@ _RELAXED: dict[str, CategorySettings] = {
     "ai-tells-register": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=1.0),
     "ai-tells-formatting": CategorySettings(severity=Severity.OFF),
     "ai-tells-content-shape": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=1.0),
+    # OFF, like the formatting band: every rule in it is `relaxed: excluded`, and a
+    # slogan heading is a register choice in the prose relaxed covers.
+    "ai-tells-agentic": CategorySettings(severity=Severity.OFF),
     # OFF, and every rule in it is `relaxed: excluded` anyway: a metaphor is a
     # register choice, and relaxed is the profile that grants register latitude.
     "ai-tells-figurative": CategorySettings(severity=Severity.OFF),
diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
index c9f7adf84c..755c756e76 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
@@ -22,34 +22,6 @@ description: >-
 weight: 1.5
 recommended_for: [consumer, internal, change-comms]
 rules:
-  - id: formulaic-universal-heading
-    name: Replace a universal slogan heading
-    kind: pattern
-    severity: warning
-    message: 'formulaic universal heading: {match} -- use a noun phrase or a scoped factual statement'
-    scope: heading
-    tiers:
-      strict: advisory
-      normal: advisory
-      relaxed: excluded
-    pattern: '^every\s+[a-z][\w-]*\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed|ing))\b(?:\s+[a-z][\w-]*){1,8}$'
-    ignore_case: true
-    fix: Rewrite the heading as a noun phrase or state one scoped fact.
-    examples:
-      - bad: Every Change Opens A Door
-        good: Change opportunities
-      - bad: Every Request Finds Its Way
-        good: Request routing
-      - good: Every request to this endpoint requires authentication
-    provenance:
-      source: references/content-shape.md ("Formulaic universal headings")
-      note: >-
-        The heading scope is part of the rule: a title must begin with Every,
-        use one singular noun, and immediately follow it with a finite-looking
-        predicate plus a short complement. This grammatical shape catches
-        universal slogans without matching body invariants such as "Every request
-        to this endpoint requires authentication".
-
   - id: contrastive-inversion-frames
     name: Cut the strawman half of a contrastive frame
     kind: pattern
@@ -2306,3 +2278,59 @@ rules:
         occasionally states a real contrast. That warning level IS the judgement gap,
         and this rule names it. A reward-model favourite: it survives editing because
         it reads quotable.
+---
+id: ai-tells-agentic
+title: AI tells -- agentic slogan formulae
+description: >-
+  The formulae an agent reaches for when it has to name a section and has no fact
+  to name it with: a universal claim about a whole class, standing in for a title.
+  The shape is the tell, not the vocabulary, so these rules match syntax and a
+  rewritten slogan does not escape by swapping words.
+weight: 1.5
+recommended_for: [consumer, internal, change-comms]
+rules:
+  - id: formulaic-universal-heading
+    name: Replace a universal slogan with a title
+    kind: pattern
+    severity: warning
+    message: 'universal slogan: {match} -- title it with a noun phrase, or state one scoped fact'
+    scope: paragraph
+    tiers:
+      strict: enforced
+      normal: enforced
+      relaxed: excluded
+    pattern: '^every\s+[\w-]+\s+(?:is|are|was|were|has|have|does|do|can|cannot|will|would|should|must|[a-z][\w-]*(?<!s)s)(?:\s+[\w-]+){2,8}$'
+    ignore_case: true
+    fix: Name the section with a noun phrase, or scope the claim and state it as a sentence.
+    examples:
+      - bad: Every Number Traces To A Record
+        good: Every number in the ledger traces to a source record.
+        note: >-
+          The rewrite scopes the subject with a prepositional phrase, so the
+          predicate no longer sits against the bare noun. The loader proves the
+          non-match, which is the body invariant this rule must never claim.
+      - bad: Every Change Tells A Story
+        good: Every change requires a changelog entry.
+      - bad: Every Request Finds Its Way
+        good: Request routing
+    provenance:
+      source: packages/slopvac/skills/review-docs/SKILL.md ("Read the headings alone, in order")
+      note: >-
+        Three shape conditions carry this rule, and each one alone is what keeps a
+        real invariant out of it. The predicate must sit IMMEDIATELY against the bare
+        subject noun, so a scoped invariant is not a match ("Every request TO THIS
+        ENDPOINT requires authentication", "Every file IN THIS DIRECTORY contains a
+        header"). The complement must be at least two words, so a terse invariant with
+        a one-word object is not a match ("Every request requires authentication").
+        And the match runs to the end of the block through word characters only, so
+        any terminal punctuation excludes it -- a heading carries none, a body
+        sentence does. Together they select the title-shaped universal claim and leave
+        the class invariant, which is the one construction "every" is genuinely for.
+        `scope: paragraph`, not `heading`: the native engine's paragraph scope covers
+        every rendered block INCLUDING headings, list items, and quotes, whereas
+        heading scope compiles to a Vale `heading` payload and Vale then owns the
+        rule, leaving it unchecked under `--no-vale`. See
+        compile_vale.PARAGRAPH_SCOPE_REASON.
+        The comma-joined pair form is prose-scope.formulaic-subject-verb-slogan; the
+        judgement remainder for a slogan carrying no fixed frame is
+        ai-tells-content-shape.epigram-closer-remainder.
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
index 2610406ce3..eaadaedf0c 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-scope.yml
@@ -7,35 +7,6 @@ description: >-
 weight: 1.0
 recommended_for: [consumer, change-comms]
 rules:
-  - id: formulaic-subject-verb-slogan
-    name: Replace a parallel subject-verb slogan heading
-    kind: pattern
-    severity: warning
-    message: 'formulaic heading: {match} -- use a noun phrase or a scoped factual statement'
-    scope: heading
-    tiers:
-      strict: advisory
-      normal: advisory
-      relaxed: excluded
-    pattern: '^(?:the|a|an|this|that|these|those|our|your|their)\s+[a-z][\w-]*(?:\s+[a-z][\w-]*)?\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed|ing))\b(?:\s+[a-z][\w-]*){0,2},\s+(?:the|a|an|this|that|these|those|our|your|their)\s+[a-z][\w-]*(?:\s+[a-z][\w-]*)?\s+(?:is|are|was|were|does|do|did|has|have|had|can|cannot|will|would|should|must|[a-z][\w-]*(?:s|ed|ing))\b(?:\s+[a-z][\w-]*){0,2}$'
-    ignore_case: true
-    fix: Rewrite the heading as a noun phrase or state one scoped fact.
-    examples:
-      - bad: The Review Guides, The Reader Decides
-        good: Review guidance
-      - bad: The Service Learns, The Operator Knows
-        good: Service learning and operator knowledge
-    provenance:
-      source: references/content-shape.md ("Formulaic parallel headings")
-      note: >-
-        Heading scope is essential: the comma-separated pair is a slogan-shaped
-        title only when both short clauses have a determiner-led subject and a
-        finite-looking predicate. The pattern is grammatical rather than lexical,
-        and does not inspect body sentences or object-level contrasts such as
-        "Parser reads JSON, not YAML".
-
-
-
   - id: rejected-alternative
     name: Move the decision to an ADR, spec, or commit
     kind: pattern
@@ -169,3 +140,48 @@ rules:
         alternative cannot have been matching under a pure RE2 engine; the Python
         `regex` module supports it, so the ported rule is stricter and this
         alternative newly becomes live. Test it against the corpus before enforcing.
+
+  - id: formulaic-subject-verb-slogan
+    name: Replace a paired subject-verb slogan with a title
+    kind: pattern
+    severity: warning
+    message: 'formulaic slogan: {match} -- title it with a noun phrase, or state one scoped fact'
+    scope: paragraph
+    tiers:
+      strict: enforced
+      normal: enforced
+      relaxed: excluded
+    pattern: '^(?:the|a|an|this|that|these|those|its|our|your|their)\s+[\w-]+(?:\s+[\w-]+)?\s+(?:is|are|was|were|has|have|does|do|can|cannot|will|would|should|must|[a-z][\w-]*(?<!s)s)(?:\s+[\w-]+){0,3}\s*,\s*(?:the|a|an|this|that|these|those|its|our|your|their)\s+[\w-]+(?:\s+[\w-]+)?\s+(?:is|are|was|were|has|have|does|do|can|cannot|will|would|should|must|[a-z][\w-]*(?<!s)s)(?:\s+[\w-]+){0,3}$'
+    ignore_case: true
+    fix: Name the section with a noun phrase, or state the one fact the two clauses gesture at.
+    examples:
+      - bad: The Harness Reports, The Customer Decides
+        good: Reporting and approval responsibilities
+      - bad: The Boundary Protects, The Audit Proves
+        good: The boundary rejects unsigned requests; the audit log records each rejection.
+      - bad: The Parser Reads, The Loader Rejects
+        good: The parser reads JSON, not YAML.
+        note: >-
+          The rewrite is an object-level factual contrast, which is the shape this
+          rule must never claim. The loader proves the non-match: the second half
+          of a real contrast is a bare object, not a second determiner-led clause.
+    provenance:
+      source: packages/slopvac/skills/review-docs/SKILL.md ("Read the headings alone, in order")
+      note: >-
+        The comma-joined sibling of prose-scope.epigram. Epigram matches the parallel
+        pair written as two SENTENCES and uses the full stops to tell it apart from an
+        ordinary two-clause sentence; this rule matches the same pair written as a
+        TITLE, and the absence of terminal punctuation does that same work here. Both
+        halves must be determiner-led with a finite-looking predicate, which is what
+        keeps the rule off a factual contrast ("The parser reads JSON, not YAML.") and
+        off a contrastive inversion whose second subject is a pronoun ("The Harness
+        Measures, It Does Not Judge") -- that shape belongs to
+        ai-tells-structure.contrastive-inversion-frames.
+        The predicate alternation ends in `[a-z][\w-]*(?<!s)s` rather than `\w+s`, so a
+        plural noun spelled with a double s ("The Address Class, The Access Class")
+        cannot pose as a verb.
+        `scope: paragraph`, not `heading`: the native engine's paragraph scope covers
+        every rendered block INCLUDING headings, list items, and quotes, so the rule
+        reaches a bolded pseudo-heading too. Heading scope would instead compile to a
+        Vale `heading` payload, and Vale then owns the rule -- which means `--no-vale`
+        leaves it unchecked. See compile_vale.PARAGRAPH_SCOPE_REASON.


## dirty tree diff

 bench/runner.py                                    |    5 +-
 packages/slopvac-lint/docs/rules.md                | 1071 +++++++++++++++++++-
 .../src/slopvac/rules/ai-tells-agentic.yml         |   34 +-
 .../src/slopvac/rules/prose-discipline.yml         |    2 +-
 .../slopvac-lint/src/slopvac/rules/ste-nouns.yml   |    2 +-
 packages/slopvac-lint/uv.lock                      |    2 +-
 tests/test_bench_runner.py                         |   56 +-
 7 files changed, 1085 insertions(+), 87 deletions(-)

diff --git a/bench/runner.py b/bench/runner.py
index 61458f34be..fb2ef63645 100755
--- a/bench/runner.py
+++ b/bench/runner.py
@@ -641,7 +641,8 @@ def invoke(
         return None, stats, f"schema_invalid: {problem}"
     if outer.get("run_nonce") != nonce:
         return None, stats, "transmission_error: answer does not echo the request nonce"
-    return outer["results"], stats, ""
+    prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()
+    return [dict(row, prompt_sha256=prompt_sha256) for row in outer["results"]], stats, ""
 
 
 def score(cases: list[dict], results: list[dict]) -> dict[str, Any]:
@@ -776,7 +777,7 @@ def main(argv: list[str] | None = None) -> int:
     metric("one_unit", args.one_unit)
     metric("case_count", len(eligible))
     metric("holdout_count", sum(bool(case.get("holdout")) for case in cases))
-    metric("prompt_sha256", hashlib.sha256(prompt.encode()).hexdigest())
+    metric("batch_prompt_sha256", hashlib.sha256(prompt.encode()).hexdigest())
     metric("system_prompt_sha256", hashlib.sha256(DECLARED_SYSTEM_PROMPT.encode()).hexdigest())
     metric("repeats", repeats)
 
diff --git a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
index 1d0cc16b3f..715b76ccb1 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ai-tells-agentic.yml
@@ -32,10 +32,9 @@ rules:
       - ai-tells-structure.definitional-negation-pair
     judgement_contract:
       admission: >-
-        The paragraph holds a negated-half contrast a seed matched, or one of the ambiguous bare-clause and
-        subjectless-imperative forms the seed leaves clean, and both halves are within the unit.
+        A seed matched a contrast in the paragraph. Alternatively, the paragraph contains a bare clause or subjectless imperative that the seeds leave clean. Both halves appear in the unit.
       protects: >-
-        Exception: retain a negated half that states a real boundary, a safety constraint, or a documented invariant.
+        Exception: retain a half that uses negation to document a boundary, constraint, or invariant.
 
       dims: [FIT, WARRANT, REPAIR]
       evidence_arity: 2
@@ -2858,7 +2857,7 @@ rules:
 id: ai-tells-agentic
 title: AI tells -- agentic slogan formulae
 description: >-
-  Recurring agent-generated heading patterns that make a universal claim stand in for a section title.
+  Recurring agent-generated headings that substitute a universal claim for a section title.
   The rule matches the syntactic shape, so replacing its vocabulary does not avoid it.
 weight: 1.5
 recommended_for: [consumer, internal, change-comms]
@@ -2891,25 +2890,14 @@ rules:
         good: Request routing
     provenance:
       source: packages/slopvac/skills/review-docs/SKILL.md ("Read the headings alone, in order")
-      note: >-
-        Three shape conditions carry this rule, and each one alone is what keeps a
-        real invariant out of it. The predicate must sit IMMEDIATELY against the bare
-        subject noun, so a scoped invariant is not a match ("Every request TO THIS
-        ENDPOINT requires authentication", "Every file IN THIS DIRECTORY contains a
-        header"). The complement must be at least two words, so a terse invariant with
-        a one-word object is not a match ("Every request requires authentication").
-        And the match runs to the end of the block through word characters only, so
-        any terminal punctuation excludes it -- a heading carries none, a body
-        sentence does. Together they select the title-shaped universal claim and leave
-        the class invariant, which preserves uses of “every” that state a scoped invariant.
-        `scope: paragraph`, not `heading`: the native engine's paragraph scope covers
-        every rendered block INCLUDING headings, list items, and quotes, whereas
-        heading scope compiles to a Vale `heading` payload and Vale then owns the
-        rule, leaving it unchecked under `--no-vale`. See
-        compile_vale.PARAGRAPH_SCOPE_REASON.
-        The comma-joined pair form is prose-scope.formulaic-subject-verb-slogan; the
-        judgement remainder for a slogan carrying no fixed frame is
-        ai-tells-content-shape.epigram-closer-remainder.
+      note: |-
+        Three conditions exclude invariants:
+
+        - The predicate follows a bare subject noun. Adding a preposition to the subject stops the match.
+        - The complement contains at least two words. This excludes terse requirements.
+        - The match reaches the end of the block through word characters only. A period or other terminal mark excludes a body sentence.
+
+        Paragraph scope covers headings, list items, and quotes in the native engine. Heading scope would pass ownership to Vale and go unchecked under `--no-vale`. See `compile_vale.PARAGRAPH_SCOPE_REASON`. The comma-joined form belongs to `prose-scope.formulaic-subject-verb-slogan`. Slogans without a fixed frame belong to `ai-tells-content-shape.epigram-closer-remainder`.
   - id: contrastive-inversion-frames
     name: Cut the strawman half of a contrastive frame
     kind: pattern
diff --git a/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml b/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
index bdeb2ee99d..13cabf7c2b 100644
--- a/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/prose-discipline.yml
@@ -22,7 +22,7 @@ rules:
       - ste-words.inconsistent-term-for-same-thing
     judgement_contract:
       admission: >-
-        The unit uses two or more terms for the same actor; the occurrences needed to compare them are within the unit.
+        The unit uses two or more terms for the same actor. The occurrences needed to compare them are within the unit.
       protects: >-
         Exception: retain terms explicitly defined as different subjects at first use.
       dims: [FIT, WARRANT, HARM]
diff --git a/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml b/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
index e17f116f5a..78636978ac 100644
--- a/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
+++ b/packages/slopvac-lint/src/slopvac/rules/ste-nouns.yml
@@ -55,7 +55,7 @@ rules:
       - ste-nouns.multiword-noun-too-long
     judgement_contract:
       admission: >-
-        The document contains the long domain term a seed matched at its first use and at a later use; both occurrences are within the unit.
+        The document contains the long domain term a seed matched at its first use and at a later use. Both occurrences are within the unit.
       protects: >-
         Exception: retain a spelling fixed by an identifier, API name, or standard.
       dims: [FIT, WARRANT]
diff --git a/tests/test_bench_runner.py b/tests/test_bench_runner.py
index cc6592d5b2..a23a15d2d0 100644
--- a/tests/test_bench_runner.py
+++ b/tests/test_bench_runner.py
@@ -1,5 +1,6 @@
 from __future__ import annotations
 
+import hashlib
 import json
 import os
 import subprocess
@@ -450,7 +451,16 @@ def test_invoke_sends_the_prompt_on_stdin_and_no_message_argument(fake_omp: Path
         and argument != "-p"
         and not record["argv"][index - 1].startswith("--")
     ]
-    assert rows == [{"case_id": cases[0]["id"], "verdict": "reject", "quote": cases[0]["text"], "reason": "formulaic construction"}]
+    assert rows[0]["prompt_sha256"] == hashlib.sha256(prompt.encode()).hexdigest()
+    assert rows == [
+        {
+            "case_id": cases[0]["id"],
+            "verdict": "reject",
+            "quote": cases[0]["text"],
+            "reason": "formulaic construction",
+            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
+        }
+    ]
     assert stats["total_tokens"] == 2164
     assert stats["cost_usd"] == pytest.approx(0.0004635)
     assert stats["request_count"] == 1
@@ -589,7 +599,7 @@ def test_scored_run_keeps_the_committed_arm_order(
 
     assert code == 0
     assert order == [
-        "arm_gpt_oss_120b_quality_score",
+        "arm_claude_sonnet_quality_score",
         "arm_gpt_5_6_luna_quality_score",
         "arm_claude_haiku_quality_score",
         "arm_gpt_5_6_sol_quality_score",
@@ -597,6 +607,36 @@ def test_scored_run_keeps_the_committed_arm_order(
     assert metrics["case_count"] == "34"
     assert metrics["repeats"] == "2"
 
+def test_entry_point_rejects_offline_benchmark_arguments() -> None:
+    proc = subprocess.run(
+        ["/bin/sh", "autoresearch.sh", "--smoke", "--smoke-arm", "nope"],
+        cwd=ROOT,
+        capture_output=True,
+        text=True,
+        check=False,
+        env={**os.environ, "PATH": "/usr/bin:/bin", "PYTHON": sys.executable},
+    )
+
+    assert proc.returncode == 1
+    assert proc.stderr == (
+        "autoresearch: offline benchmark does not accept arguments: "
+        "--smoke --smoke-arm nope\n"
+    )
+
+def test_one_unit_provenance_distinguishes_batch_template_from_sent_prompt(
+    fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
+) -> None:
+    run_dir = tmp_path / "run"
+    code, metrics = run_main(["--one-unit", "--arm", "gpt-5.6-luna", "--repeats", "1"], run_dir, capsys)
+
+    assert code == 0
+    assert "prompt_sha256" not in metrics
+    assert "batch_prompt_sha256" in metrics
+    request = json.loads(
+        (run_dir / "arm_gpt_5_6_luna_repeat_1_case_34" / "request.json").read_text(encoding="utf-8")
+    )
+    assert metrics["batch_prompt_sha256"] != request["prompt_sha256"]
+
 
 def test_unmeasured_run_exits_nonzero_and_scores_no_cases(
     fake_omp: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
@@ -612,15 +652,3 @@ def test_unmeasured_run_exits_nonzero_and_scores_no_cases(
     assert "arm_gpt_5_6_luna_repeat_1_quality_score" not in metrics
 
 
-def test_entry_point_forwards_smoke_arm_selection() -> None:
-    proc = subprocess.run(
-        ["/bin/sh", "autoresearch.sh", "--smoke", "--smoke-arm", "nope"],
-        cwd=ROOT,
-        capture_output=True,
-        text=True,
-        check=False,
-        env={**os.environ, "PATH": "/usr/bin:/bin", "PYTHON": sys.executable},
-    )
-
-    assert proc.returncode == 2
-    assert "unknown smoke arm 'nope'" in proc.stderr


## untracked docs/

docs/rules.md (306885 B)