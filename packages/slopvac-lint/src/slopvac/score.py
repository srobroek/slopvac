"""Turn findings into a density measurement and a 0-100 score.

THREE NUMBERS, DELIBERATELY. They answer different questions and none replaces
another:

  per_100_words         the raw density, every finding. Comparable across documents
                        of any length, and the honest measurement -- it is a count,
                        not a judgement.
  gating_per_100_words  severity-weighted errors and warnings (1.0/0.5). What the
                        BUDGET is checked against.
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

# Severity is the multiplier used by both category and document gates.
SEVERITY_WEIGHT = {
    Severity.ERROR: 1.0,
    Severity.WARNING: 0.5,
    Severity.SUGGESTION: 0.1,
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


def _score_from_density(weighted_density: float, budget: float | None) -> float:
    """Map weighted density onto 0-100.

    At or below budget: 100 down to 70, linearly. A document inside its budget is
    passing, and the 70 floor at exactly-budget makes "just inside" visibly
    different from "clean".
    Above budget: 70 down to 0, reaching 0 at ZERO_SCORE_MULTIPLE x budget.
    """
    if budget is None:
        return max(0.0, 100.0 - weighted_density * 10.0)
    if budget == 0:
        return 100.0 if weighted_density == 0 else 0.0

    if weighted_density <= budget:
        return 100.0 - 30.0 * (weighted_density / budget)

    over = weighted_density - budget
    span = budget * (ZERO_SCORE_MULTIPLE - 1.0)
    if span <= 0:
        return 0.0
    return max(0.0, 70.0 * (1.0 - over / span))


def _score_from_counts(weighted_count: float) -> float:
    """Score a document too short for a meaningful density measurement."""
    return max(0.0, 100.0 - weighted_count * 20.0)


def _category_result(
    name: str,
    items: list[Finding],
    words: int,
    config: ResolvedConfig,
    categories_meta: dict[str, float],
) -> tuple[CategoryScore, float]:
    settings = config.categories.get(name)
    weight = categories_meta.get(name, 1.0)
    if settings is not None and settings.weight is not None:
        weight = settings.weight
    if settings is not None and settings.severity is Severity.OFF:
        weight = 0.0

    errors = sum(f.severity is Severity.ERROR for f in items)
    warnings = sum(f.severity is Severity.WARNING for f in items)
    suggestions = sum(f.severity is Severity.SUGGESTION for f in items)
    measurable = words >= MIN_WORDS_FOR_DENSITY and words > 0
    density = len(items) / words * 100 if measurable else 0.0
    gating_weight = sum(
        SEVERITY_WEIGHT[f.severity]
        for f in items
        if f.severity is not Severity.SUGGESTION
    )
    gating = gating_weight / words * 100 if measurable else 0.0
    suggestion_density = suggestions / words * 100 if measurable else suggestions
    budget = settings.max_per_100_words if settings is not None else None
    base_score = (
        _score_from_density(gating, budget)
        if measurable
        else _score_from_counts(gating_weight)
    )
    score = max(0.0, base_score - _suggestion_penalty(suggestion_density))
    return (
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
        ),
        weight,
    )


def _weighted_category_score(entries: list[tuple[CategoryScore, float]]) -> float:
    active = [(entry.score, weight) for entry, weight in entries if weight > 0]
    if not active:
        return 100.0
    return sum(score * weight for score, weight in active) / sum(
        weight for _, weight in active
    )


def _whole_document_score(
    findings: list[Finding], words: int, budget: float | None
) -> float:
    blocking_weight = sum(
        SEVERITY_WEIGHT[f.severity]
        for f in findings
        if f.severity is not Severity.SUGGESTION
    )
    suggestions = sum(f.severity is Severity.SUGGESTION for f in findings)
    measurable = words >= MIN_WORDS_FOR_DENSITY and words > 0
    base_score = (
        _score_from_density(blocking_weight / words * 100, budget)
        if measurable
        else _score_from_counts(blocking_weight)
    )
    suggestion_density = suggestions / words * 100 if measurable else suggestions
    return max(0.0, base_score - _suggestion_penalty(suggestion_density))


def _blocking_density(findings: list[Finding], words: int) -> float:
    if words < MIN_WORDS_FOR_DENSITY or not words:
        return 0.0
    return (
        sum(
            SEVERITY_WEIGHT[f.severity]
            for f in findings
            if f.severity is not Severity.SUGGESTION
        )
        / words
        * 100
    )


def _failure_reasons(
    findings: list[Finding],
    category_scores: list[CategoryScore],
    words: int,
    overall: float,
    config: ResolvedConfig,
    unchecked: list[str],
) -> list[str]:
    errors = sum(f.severity is Severity.ERROR for f in findings)
    warnings = sum(f.severity is Severity.WARNING for f in findings)
    thresholds = config.thresholds
    reasons = ["incomplete check: " + "; ".join(unchecked)] if unchecked else []
    if thresholds.max_errors is not None and errors > thresholds.max_errors:
        reasons.append(f"{errors} error(s), limit {thresholds.max_errors}")
    if thresholds.max_warnings is not None and warnings > thresholds.max_warnings:
        reasons.append(f"{warnings} warning(s), limit {thresholds.max_warnings}")

    density = _blocking_density(findings, words)
    if (
        thresholds.max_total_per_100_words is not None
        and words >= MIN_WORDS_FOR_DENSITY
        and density > thresholds.max_total_per_100_words
    ):
        reasons.append(
            f"{density:.2f} severity-weighted findings per 100 words, budget "
            f"{thresholds.max_total_per_100_words}"
        )
    if (
        thresholds.min_score is not None
        and (errors or warnings)
        and overall < thresholds.min_score
    ):
        reasons.append(f"score {overall:.1f}, minimum {thresholds.min_score}")
    reasons.extend(
        f"{entry.category} at {entry.gating_per_100_words:.2f} "
        f"severity-weighted findings per 100 words, budget {entry.budget}"
        for entry in category_scores
        if entry.over_budget
    )
    return reasons


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
    """Build the full result for one file."""
    unchecked = unchecked or []
    by_category: dict[str, list[Finding]] = {name: [] for name in categories_meta}
    for finding in findings:
        by_category.setdefault(finding.category, []).append(finding)

    entries = [
        _category_result(name, items, words, config, categories_meta)
        for name, items in sorted(by_category.items())
    ]
    category_scores = [entry for entry, _ in entries]
    overall = min(
        _weighted_category_score(entries),
        _whole_document_score(findings, words, config.thresholds.max_total_per_100_words),
    )
    errors = sum(f.severity is Severity.ERROR for f in findings)
    warnings = sum(f.severity is Severity.WARNING for f in findings)
    suggestions = sum(f.severity is Severity.SUGGESTION for f in findings)
    reasons = _failure_reasons(
        findings, category_scores, words, overall, config, unchecked
    )
    per_100 = (
        len(findings) / words * 100 if words >= MIN_WORDS_FOR_DENSITY and words else 0.0
    )
    return DocumentScore(
        path=path,
        profile=config.profile.value,
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
        unchecked=unchecked,
    )
