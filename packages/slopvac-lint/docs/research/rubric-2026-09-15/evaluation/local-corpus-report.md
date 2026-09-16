# Judgement comparison

evidence_offset_mismatch: 57

## README.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 91.9 | 91.9 |
| findings | 25 | 0 confirms |

PRESERVE: factual_polarity_or_contrast=1
ABSTAIN: ambiguous_unit=12, inconsistent_output=1, missing_context=7, needs_repository_fact=3, no_exact_evidence=4

## AGENTS.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 87.9 | 87.9 |
| findings | 3 | 0 confirms |

PRESERVE: 0
ABSTAIN: needs_repository_fact=1, no_exact_evidence=1

## packages/slopvac-lint/README.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 94.0 | 92.2 |
| findings | 76 | 12 confirms |

### CONFIRM `ai-tells-register.anthropomorphised-justification-remainder` (suggestion)

> knows your domain

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,2 +1,2 @@
 A blocklist you wrote is the only word

-list that knows your domain.
+list that contains your domain's terms.
```

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> knows your domain

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,2 +1,2 @@
 A blocklist you wrote is the only word

-list that knows your domain.
+list that contains your domain's terms.
```

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> A lint prunes on its own

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1 +1 @@
-A lint prunes on its own and keeps the 16 trees used last.
+Each lint run prunes the cache automatically and keeps the 16 trees used last.
```

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> The project asked
  for that gate by name

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,3 +1 @@
-The project asked

-  for that gate by name; linting on with an empty wordlist would report every

-  document clean.
+The project's configuration named that gate; linting on with an empty wordlist would report every document clean.
```

### CONFIRM `ai-tells-structure.cataphoric-lead-in-remainder` (suggestion)

> three rulesets:

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.absolute-assertion-remainder` (suggestion)

> because a reader applies a suggestion
without thinking.

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.absolute-assertion-remainder` (suggestion)

> nothing is ever served stale

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.absolute-assertion-remainder` (suggestion)

> every caller

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,3 +1,3 @@
 A bad config, an unloadable ruleset, or a missing tool

-  exits 2, and every caller treats that as "nothing was checked" rather than as a

+  exits 2, so a caller treats that as "nothing was checked" rather than as a

   pass.
```

### CONFIRM `ai-tells-structure.absolute-assertion-remainder` (suggestion)

> Nobody but its author can argue with, or later remove, an entry that gives no
reason.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,2 +1 @@
-Nobody but its author can argue with, or later remove, an entry that gives no

-reason.
+An entry that gives no reason leaves later readers nothing to argue with, so only its author can say why it exists or whether to remove it.
```

### CONFIRM `ai-tells-structure.contrastive-inversion-remainder` (suggestion)

> and neither replaces the other.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1 +1 @@
-Two numbers, because they answer different questions and neither replaces the other.
+Two numbers, because they answer different questions.
```

### CONFIRM `ai-tells-structure.false-suspense-remainder` (suggestion)

> They are worth stating because
the obvious alternative is what most prose linters do.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,2 +1 @@
-They are worth stating because

-the obvious alternative is what most prose linters do.
+The obvious alternative is what most prose linters do.
```

### CONFIRM `ai-tells-structure.false-suspense-remainder` (suggestion)

> They ship for two reasons.

Rewrite: withheld_checker_veto

PRESERVE: factual_polarity_or_contrast=17, normative_obligation=2
ABSTAIN: ambiguous_unit=47, inconsistent_output=1, missing_context=12, needs_external_fact=1, needs_repository_fact=1, no_exact_evidence=25

## packages/slopvac/README.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 86.7 | 86.7 |
| findings | 7 | 0 confirms |

PRESERVE: source_locked_legal_text=8
ABSTAIN: missing_context=3, needs_repository_fact=3

## packages/slopvac-lint/docs/domain-categories.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 91.4 | 91.4 |
| findings | 28 | 0 confirms |

PRESERVE: factual_polarity_or_contrast=3
ABSTAIN: inconsistent_output=4, needs_external_fact=1, needs_repository_fact=1, no_exact_evidence=4

## packages/slopvac-lint/docs/metrics.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 91.7 | 90.5 |
| findings | 66 | 8 confirms |

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> Phase-1 analysis flagged this as unresolved and predicted it would be the largest
false-positive driver.

Rewrite: withheld_needs_fact

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> a false positive
gets the rule disabled

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-register.anthropomorphised-justification-remainder` (suggestion)

> which is correct

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,2 +1,2 @@
-The default at step 5 means a README classifies as descriptive throughout, which is correct;

+The default at step 5 means a README classifies as descriptive throughout;

 its imperative install steps classify as procedural individually at step 3 or 4.
```

### CONFIRM `ai-tells-structure.cataphoric-lead-in-remainder` (suggestion)

> This ordering depends on two properties:

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.false-suspense-remainder` (suggestion)

> The second is the decisive one.

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.contrastive-inversion-remainder` (suggestion)

> positively, not merely disfavoured

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.false-suspense-remainder` (suggestion)

> Notes on the last two.

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-content-shape.elegant-variation` (suggestion)

> A checker that splits on whitespace

Rewrite: withheld_checker_veto

PRESERVE: factual_polarity_or_contrast=11
ABSTAIN: ambiguous_unit=61, inconsistent_output=5, missing_context=1, needs_external_fact=1, needs_repository_fact=1, no_exact_evidence=14

## packages/slopvac-lint/docs/ste-principles.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 90.7 | 90.6 |
| findings | 10 | 1 confirms |

### CONFIRM `ai-tells-structure.contrastive-inversion-remainder` (suggestion)

> It reports the mechanical rules with exact replacements; fix what it names rather than re-reading this list.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1 +1 @@
-It reports the mechanical rules with exact replacements; fix what it names rather than re-reading this list.
+It reports the mechanical rules with exact replacements; fix what it names.
```

PRESERVE: factual_polarity_or_contrast=1
ABSTAIN: missing_context=5, needs_external_fact=1, needs_repository_fact=2, no_exact_evidence=3

## packages/slopvac-lint/docs/triage.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 92.1 | 91.5 |
| findings | 20 | 4 confirms |

### CONFIRM `ai-tells-structure.cataphoric-lead-in-remainder` (suggestion)

> one of three
verdicts:

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.cataphoric-lead-in-remainder` (suggestion)

> two precedents

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-content-shape.elegant-variation` (suggestion)

> the skill settles

Rewrite: withheld_checker_veto

### CONFIRM `prose-discipline.competing-actor-terms` (suggestion)

> the skill settles

Rewrite: withheld_checker_veto

PRESERVE: factual_polarity_or_contrast=5, normative_obligation=3
ABSTAIN: ambiguous_unit=8, inconsistent_output=1, missing_context=9, needs_repository_fact=6, no_exact_evidence=8

## packages/slopvac-lint/docs/vale-traps.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 90.5 | 90.2 |
| findings | 58 | 2 confirms |

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> ships a rule

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1 +1 @@
-The unquoted guard is the trap that ships a rule reading as guarded while the guard does nothing.
+The unquoted guard is the trap: a rule ships reading as guarded while the guard does nothing.
```

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> no fixture had imagined

Rewrite: withheld_checker_veto

PRESERVE: factual_polarity_or_contrast=4, normative_obligation=1
ABSTAIN: ambiguous_unit=17, inconsistent_output=2, missing_context=2, needs_external_fact=2, needs_repository_fact=6, no_exact_evidence=27

## packages/slopvac/skills/review-docs/SKILL.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 90.3 | 89.9 |
| findings | 52 | 3 confirms |

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> A review that finds nothing has not read for truth.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1 +1 @@
-A review that finds nothing has not read for truth.
+A reviewer who finds nothing has not read for truth.
```

### CONFIRM `ai-tells-structure.contrastive-inversion-remainder` (suggestion)

> NOT Calling the file clean on exit 2, and NOT reading it as "nothing
   was checked".

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.heading-echo` (suggestion)

> A project chooses its own gate.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1,5 +1 @@
-A project chooses its own gate. `slopvac rules --profile <profile>` lists every

-rule and its disposition; `slopvac rules --format json | jq '.categories'` shows

-each category's `recommended_for` genres. Recommend by genre from that field

-rather than from a list held here, name what is off by default and why, and

-MUST ask before writing 
+`slopvac rules --profile <profile>` lists every rule and its disposition; `slopvac rules --format json | jq '.categories'` shows each category's `recommended_for` genres. Recommend by genre from that field rather than from a list held here, name what is off by default and why, and MUST ask before writing 
```

PRESERVE: factual_polarity_or_contrast=8, normative_obligation=5
ABSTAIN: ambiguous_unit=13, inconsistent_output=1, missing_context=5, needs_repository_fact=2, no_exact_evidence=16, unit_out_of_scope=12

## packages/slopvac/skills/write-docs/SKILL.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 88.6 | 88.3 |
| findings | 55 | 2 confirms |

### CONFIRM `ai-tells-structure.absolute-assertion-remainder` (suggestion)

> A gate that fails correct prose is a gate people turn off.

Rewrite: withheld_checker_veto

### CONFIRM `ai-tells-structure.absolute-assertion-remainder` (suggestion)

> all name a number the writer has and withheld.

Rewrite: proposed

```diff
--- unit
+++ rewrite
@@ -1 +1 @@
-MUST Give a quantity its count. "Several", "various", "a number of", "in most cases" all name a number the writer has and withheld.
+MUST Give a quantity its count. "Several", "various", "a number of", "in most cases" each stand in for a number the writer may have had and withheld.
```

PRESERVE: factual_polarity_or_contrast=4, normative_obligation=10, quoted_specimen=1
ABSTAIN: inconsistent_output=1, needs_repository_fact=6, no_exact_evidence=10

## packages/slopvac/skills/write-docs/references/change-comms.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 91.5 | 91.2 |
| findings | 4 | 2 confirms |

### CONFIRM `ai-tells-content-shape.elegant-variation` (suggestion)

> release notes

Rewrite: withheld_checker_veto

### CONFIRM `prose-discipline.competing-actor-terms` (suggestion)

> a consumer can observe.

Rewrite: withheld_checker_veto

PRESERVE: factual_polarity_or_contrast=1, normative_obligation=3, quoted_specimen=2
ABSTAIN: needs_repository_fact=1

## packages/slopvac/skills/write-docs/references/consumer-docs.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 88.6 | 88.6 |
| findings | 13 | 0 confirms |

PRESERVE: normative_obligation=8
ABSTAIN: inconsistent_output=2, missing_context=1, no_exact_evidence=26

## packages/slopvac/skills/write-docs/references/internal-docs.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 85.0 | 85.0 |
| findings | 11 | 0 confirms |

PRESERVE: normative_obligation=3, quoted_specimen=1
ABSTAIN: inconsistent_output=2, no_exact_evidence=1

## .github/action-fixtures/slop-laden.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 0.0 | 0.0 |
| findings | 11 | 3 confirms |

### CONFIRM `ai-tells-register.anthropomorphised-justification-remainder` (suggestion)

> groundbreaking solution is obviously revolutionary and truly innovative

Rewrite: withheld_needs_fact

### CONFIRM `ai-tells-register.anthropomorphised-justification-remainder` (suggestion)

> a robust, seamless, world-class workflow to deliver amazing results

Rewrite: withheld_needs_fact

### CONFIRM `ai-tells-register.false-agency-remainder` (suggestion)

> It leverages a robust, seamless, world-class workflow to deliver amazing results.

Rewrite: withheld_needs_fact

PRESERVE: quoted_specimen=1
ABSTAIN: inconsistent_output=1, needs_repository_fact=1

## .github/action-fixtures/clean.md

| measure | deterministic | judgement |
| --- | ---: | ---: |
| score | 95.0 | 95.0 |
| findings | 2 | 0 confirms |

PRESERVE: 0
ABSTAIN: needs_repository_fact=1
