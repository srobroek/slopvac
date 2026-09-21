# Corporate-analytic filler: FP patterns

The v3 LLM adjudication produced 92 FP-majority units and 18 TP-majority units for `ai-tells-register.corporate-analytic-filler-remainder`. The labels were checked against the complete unit text and adjudicator reasons.

| Pattern | FP-majority units | Share | Interpretation |
|---|---:|---:|---|
| bounded-guidance | 63 | 68.5% | Importance or consideration wording introduces concrete advice, criteria, risks, or safety constraints supplied by the same sentence or passage. |
| genre-convention | 9 | 9.8% | Conventional survey, disclaimer, synthesis, or explanatory framing carries factual scope or a usable qualification. |
| other | 9 | 9.8% | The analytic-looking frame is attached to a specific consequence, classification, or qualification rather than empty evaluation. |
| fragment-anaphora | 5 | 5.4% | A sentence fragment points to a substantive complement; the fragment is not independently removable evidence. |
| finite-set | 4 | 4.3% | Importance wording introduces a bounded list, ranking, or finite set that remains factual after the wrapper is removed. |
| attributed-claim | 2 | 2.2% | The frame preserves attribution or source/scope qualification for a factual claim. |

The dominant FP pattern is bounded guidance: 63/92 units. The two largest clusters (bounded guidance and genre convention) account for 72/92 (78.3%), exceeding the 70% pattern-coverage target, but their concrete facts overlap the rule's intended tell. The adjudication therefore does not support a prompt-only precision fix.

## Representative patterns

- **bounded-guidance:** “One important factor to consider is” followed by a concrete interest-rate comparison criterion; “it's a good idea to shop around” tied to financing details.
- **genre-convention:** a tax disclaimer preserving an eligibility constraint; a policy synthesis stating the purpose of the Fed's actions.
- **other:** “is an important process in vision because” followed by a concrete detection consequence; an asset-transfer consideration followed by a specific tax-cost consequence.
- **fragment-anaphora:** “It is important to note that” followed by a substantive distinction about compensation and investment income.
- **finite-set:** “a number of ways, including …” followed by a bounded list; “worth noting” followed by a ranking and measurement.
- **attributed-claim:** “important sources of historical information” preserving the evidentiary role and named domains; a number qualified by Microsoft attribution and regional scope.

Genuine TP examples remain generic evaluations or recommendations with no particular fact, measurement, consequence, constraint, or actionable criterion: “Such functions can be difficult to analyze and predict”; “It's important to understand how taxes work”; and “mitigating global catastrophic risks is an important area of study.”

**Decision:** measured, not shipped. The next lever is a deterministic scope/threshold change or retirement of the rule; that choice belongs to the user.
