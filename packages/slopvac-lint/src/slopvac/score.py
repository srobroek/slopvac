"""Turn findings into a density measurement and a 0-100 score.

THREE NUMBERS, DELIBERATELY. They answer different questions and none replaces
another:

  per_100_words         the raw density, every finding. Comparable across documents
                        of any length, and the honest measurement -- it is a count,
                        not a judgement.
  gating_per_100_words  errors and warnings only. What the BUDGET is checked
                        against.
  score                 0-100, from gating density against the profile's budget,
                        less a bounded suggestion penalty. What a CI badge shows
                        and what a `min_score` gate reads.

A SUGGESTION MAY LOWER A SCORE BUT MUST NOT FAIL A RUN. That one rule explains why
there are three numbers instead of one. `min_score` is a gate, so anything with an
unbounded contribution to the score is a gate too, whatever its label says -- and an
advisory rule resolving to SUGGESTION then fails the run it was excluded from
failing. See MAX_SUGGESTION_PENALTY for the measurement that forced this.

A single raw threshold cannot serve both a 40-word error message and a 4,000-word
guide: one finding in the former is 2.5 per 100 words and unremarkable, the same
finding in the latter is 0.025 and invisible. So short documents get a floor (see
MIN_WORDS_FOR_DENSITY) below which density is not reported as meaningful.

SEVERITY WEIGHTING. An error counts more than a suggestion, because a document
with one error and no warnings is worse than one with three suggestions. The
weights are configuration rather than constants only where a project has a reason;
the defaults below are the shipped calibration.
"""

from __future__ import annotations

from .config import ResolvedConfig, Severity
from .model import CategoryScore, DocumentScore, Finding

# An error is worth 4 suggestions. Chosen so that a single error cannot be
# out-voted by cosmetic findings when both feed one score.
SEVERITY_WEIGHT = {
    Severity.ERROR: 4.0,
    Severity.WARNING: 2.0,
    Severity.SUGGESTION: 1.0,
    Severity.OFF: 0.0,
}

# Below this, density is statistically meaningless: one finding in a 20-word
# error message reads as 5.0 per 100 words and would fail every budget. The
# document is still scored on absolute counts.
MIN_WORDS_FOR_DENSITY = 60

# The density at which a category scores 0. Above the budget the score decays
# linearly to this point rather than cliff-edging, so a document that is slightly
# over reads differently from one that is far over.
ZERO_SCORE_MULTIPLE = 4.0

# The most a document can lose to SUGGESTIONS alone, in points.
#
# A suggestion may lower a score; it must not fail a run. Those two goals conflict
# as soon as `min_score` is a gate and suggestions feed the score without bound,
# which is what shipped: on `design-doc-outbox.md` suggestions were 76 of the 152
# weight units -- exactly half -- and carried a document with ZERO errors past the
# 12.0 zero-score point on their own. All 8 independent-corpus documents scored 0.0
# at `normal` and `strict` while scoring 87 to 99 at `relaxed`.
#
# 15 keeps the signal visible and non-fatal: a document clean of errors and
# warnings but dense with suggestions lands near 85, which reads as "worth a look"
# rather than "rejected", and cannot cross the shipped 70.0 minimum.
MAX_SUGGESTION_PENALTY = 15.0

# Suggestion density at which that penalty is fully spent. Above it the penalty is
# capped, so an advisory rule with hundreds of hits costs the same as one with ten.
SUGGESTION_PENALTY_FULL_AT = 6.0


def _suggestion_penalty(suggestion_density: float) -> float:
    """Points to deduct for suggestion density, bounded by MAX_SUGGESTION_PENALTY."""
    if suggestion_density <= 0 or SUGGESTION_PENALTY_FULL_AT <= 0:
        return 0.0
    share = min(1.0, suggestion_density / SUGGESTION_PENALTY_FULL_AT)
    return MAX_SUGGESTION_PENALTY * share


def _score_from_density(
    weighted_density: float, budget: float | None
) -> float:
    """Map weighted density onto 0-100.

    At or below budget: 100 down to 70, linearly. A document inside its budget is
    passing, and the 70 floor at exactly-budget makes "just inside" visibly
    different from "clean".
    Above budget: 70 down to 0, reaching 0 at ZERO_SCORE_MULTIPLE x budget.
    """
    if budget is None or budget <= 0:
        # No budget: score on density alone against a nominal scale.
        return max(0.0, 100.0 - weighted_density * 10.0)

    if weighted_density <= budget:
        return 100.0 - 30.0 * (weighted_density / budget)

    over = weighted_density - budget
    span = budget * (ZERO_SCORE_MULTIPLE - 1.0)
    if span <= 0:
        return 0.0
    return max(0.0, 70.0 * (1.0 - over / span))


def _score_from_counts(weighted_count: float) -> float:
    """Score a document too short to measure by density.

    Density is meaningless below MIN_WORDS_FOR_DENSITY, but a short document with
    five errors is not a clean document, and reporting 100/100 for it is worse
    than reporting nothing. So the score comes off the weighted COUNT instead:
    one suggestion costs 5, one error costs 20, and four errors reach zero.

    Deliberately harsher per finding than the density path. A 40-word error
    message has room for no defects at all, which is the same reasoning that puts
    the 20-word cap on procedural text.
    """
    return max(0.0, 100.0 - weighted_count * 5.0)


def score_document(
    path: str,
    findings: list[Finding],
    words: int,
    sentences: int,
    paragraphs: int,
    config: ResolvedConfig,
    categories_meta: dict[str, float],
    unchecked: list[str] | None = None,
) -> DocumentScore:
    """Build the full result for one file.

    `categories_meta` maps category id -> its shipped weight, so a category the
    document produced no findings for still appears in the report at score 100.
    """
    profile = config.profile.value
    per_100 = (
        len(findings) / words * 100 if words >= MIN_WORDS_FOR_DENSITY and words else 0.0
    )

    by_category: dict[str, list[Finding]] = {name: [] for name in categories_meta}
    for finding in findings:
        by_category.setdefault(finding.category, []).append(finding)

    category_scores: list[CategoryScore] = []
    weighted_total = 0.0
    weight_sum = 0.0

    for name, items in sorted(by_category.items()):
        settings = config.categories.get(name)
        weight = categories_meta.get(name, 1.0)
        if settings is not None and settings.weight is not None:
            weight = settings.weight
        # A category turned off scores nothing and must not enter the average at
        # 100, which would let a relaxed profile inflate the overall figure with
        # ~15 categories nobody checked. The profiles say this twice, as
        # `severity = "off"` AND `weight = 0.0`, and the pair only agrees while
        # nobody overrides half of it: a project promoting `ste-nouns = "warning"`
        # at `relaxed` inherits the 0.0 and gets findings that cannot move the
        # score or fail the run -- the same silent-ignore the promotion path was
        # just fixed for. Deriving it from the severity instead keeps the two in
        # step.
        if settings is not None and settings.severity is Severity.OFF:
            weight = 0.0

        errors = sum(1 for f in items if f.severity is Severity.ERROR)
        warnings = sum(1 for f in items if f.severity is Severity.WARNING)
        suggestions = sum(1 for f in items if f.severity is Severity.SUGGESTION)

        measurable = words >= MIN_WORDS_FOR_DENSITY and words
        # THREE densities, and conflating any two of them was the calibration bug.
        #   density  every finding, raw. REPORTED, because the report is a
        #            measurement and a count is the honest form of it.
        #   gating   errors and warnings only. Checked against the BUDGET.
        #   weighted severity-weighted. Feeds the SCORE.
        #
        # A SUGGESTION must not be able to fail a run on its own. An advisory rule
        # resolves to SUGGESTION (`engine.severity_for`), so while the budget counted
        # raw findings, a rule the profile explicitly does not stand behind failed
        # the run anyway -- and demoting its severity changed nothing, because the
        # demotion moved the score but not the count the budget read. Measured: the
        # controlled-vocabulary rule is advisory at every profile and still put
        # `ste-words` at 8.29 per 100 words against a 1.5 budget on a correct
        # specification, which drove all 8 independent-corpus documents to 0.0.
        density = len(items) / words * 100 if measurable else 0.0
        gating = (
            sum(1 for f in items if f.severity is not Severity.SUGGESTION)
            / words
            * 100
            if measurable
            else 0.0
        )
        # The SCORE runs on gating weight, with suggestions applied afterwards as a
        # bounded penalty (see MAX_SUGGESTION_PENALTY). Feeding them into the same
        # density let them consume the whole scale.
        weighted = (
            sum(
                SEVERITY_WEIGHT[f.severity]
                for f in items
                if f.severity is not Severity.SUGGESTION
            )
            / words
            * 100
            if measurable
            else 0.0
        )
        suggestion_density = (
            sum(1 for f in items if f.severity is Severity.SUGGESTION) / words * 100
            if measurable
            else 0.0
        )

        budget = None
        if settings is not None and settings.max_per_100_words is not None:
            budget = settings.max_per_100_words

        # Below the density floor, score on the weighted COUNT: a 10-word
        # document with five errors is not clean, and density cannot say so.
        if words < MIN_WORDS_FOR_DENSITY or not words:
            weighted_count = sum(SEVERITY_WEIGHT[f.severity] for f in items)
            score = _score_from_counts(weighted_count)
        else:
            score = max(
                0.0,
                _score_from_density(weighted, budget)
                - _suggestion_penalty(suggestion_density),
            )
        category_scores.append(
            CategoryScore(
                category=name,
                findings=len(items),
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                per_100_words=round(density, 3),
                gating_per_100_words=round(gating, 3),
                budget=budget,
                score=round(score, 1),
                over_budget=budget is not None and gating > budget,
            )
        )

        # A zero-weight category is informational and must not move the overall
        # score, so it contributes to neither numerator nor denominator.
        if weight > 0:
            weighted_total += score * weight
            weight_sum += weight

    overall = weighted_total / weight_sum if weight_sum else 100.0

    # A weighted mean over every category DILUTES: 23 categories that found
    # nothing score 100 each and drown the two that found errors, so a document
    # with five errors read as 92.7. The overall score is therefore taken from the
    # whole document's own findings, using the same two paths as a category, and
    # the per-category means only pull it down further.
    #
    # Both directions matter. Averaging alone is too kind; using the document
    # figure alone loses the signal that one category is far over its budget while
    # the rest are clean. So take the lower.
    document_weighted = sum(
        SEVERITY_WEIGHT[f.severity]
        for f in findings
        if f.severity is not Severity.SUGGESTION
    )
    if words >= MIN_WORDS_FOR_DENSITY and words:
        document_suggestions = (
            sum(1 for f in findings if f.severity is Severity.SUGGESTION) / words * 100
        )
        document_score = max(
            0.0,
            _score_from_density(
                document_weighted / words * 100,
                config.thresholds.max_total_per_100_words,
            )
            - _suggestion_penalty(document_suggestions),
        )
    else:
        # Below the density floor every finding counts, suggestions included: a
        # 40-word message has no room for any, and the count path is already
        # calibrated to be harsher (see `_score_from_counts`).
        document_score = _score_from_counts(
            sum(SEVERITY_WEIGHT[f.severity] for f in findings)
        )
    overall = min(overall, document_score)

    errors = sum(1 for f in findings if f.severity is Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity is Severity.WARNING)
    suggestions = sum(1 for f in findings if f.severity is Severity.SUGGESTION)

    reasons: list[str] = []
    if unchecked:
        reasons.append("incomplete check: " + "; ".join(unchecked))
    thresholds = config.thresholds
    if thresholds.max_errors is not None and errors > thresholds.max_errors:
        reasons.append(
            f"{errors} error(s), limit {thresholds.max_errors}"
        )
    if thresholds.max_warnings is not None and warnings > thresholds.max_warnings:
        reasons.append(
            f"{warnings} warning(s), limit {thresholds.max_warnings}"
        )
    # Checked on errors and warnings, for the reason given at the category budget
    # above: a suggestion must not fail a run. The reason line quotes the figure
    # that was checked, and names it, so it can be reconciled against the raw
    # `per_100_words` in the same report.
    gating_per_100 = (
        (errors + warnings) / words * 100
        if words >= MIN_WORDS_FOR_DENSITY and words
        else 0.0
    )
    if (
        thresholds.max_total_per_100_words is not None
        and words >= MIN_WORDS_FOR_DENSITY
        and gating_per_100 > thresholds.max_total_per_100_words
    ):
        reasons.append(
            f"{gating_per_100:.2f} errors+warnings per 100 words, budget "
            f"{thresholds.max_total_per_100_words}"
        )
    if thresholds.min_score is not None and overall < thresholds.min_score:
        reasons.append(f"score {overall:.1f}, minimum {thresholds.min_score}")
    for entry in category_scores:
        if entry.over_budget:
            reasons.append(
                f"{entry.category} at {entry.gating_per_100_words:.2f} "
                f"errors+warnings per 100 words, budget {entry.budget}"
            )

    return DocumentScore(
        path=path,
        profile=profile,
        words=words,
        sentences=sentences,
        paragraphs=paragraphs,
        findings=findings,
        categories=category_scores,
        total_findings=len(findings),
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
        per_100_words=round(per_100, 3),
        score=round(overall, 1),
        passed=not reasons,
        failure_reasons=reasons,
        unchecked=unchecked or [],
    )
