"""Turn findings into a density measurement and a 0-100 score.

TWO NUMBERS, DELIBERATELY. They answer different questions and neither replaces
the other:

  per_100_words  the raw density. Comparable across documents of any length, and
                 the honest measurement -- it is a count, not a judgement.
  score          0-100, derived from density against the profile's budget. What a
                 CI badge shows and what a `min_score` gate reads.

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

        errors = sum(1 for f in items if f.severity is Severity.ERROR)
        warnings = sum(1 for f in items if f.severity is Severity.WARNING)
        suggestions = sum(1 for f in items if f.severity is Severity.SUGGESTION)

        density = (
            len(items) / words * 100
            if words >= MIN_WORDS_FOR_DENSITY and words
            else 0.0
        )
        weighted = (
            sum(SEVERITY_WEIGHT[f.severity] for f in items) / words * 100
            if words >= MIN_WORDS_FOR_DENSITY and words
            else 0.0
        )

        budget = None
        if settings is not None and settings.max_per_100_words is not None:
            budget = settings.max_per_100_words

        score = _score_from_density(weighted, budget)
        category_scores.append(
            CategoryScore(
                category=name,
                findings=len(items),
                errors=errors,
                warnings=warnings,
                suggestions=suggestions,
                per_100_words=round(density, 3),
                budget=budget,
                score=round(score, 1),
                over_budget=budget is not None and density > budget,
            )
        )

        # A zero-weight category is informational and must not move the overall
        # score, so it contributes to neither numerator nor denominator.
        if weight > 0:
            weighted_total += score * weight
            weight_sum += weight

    overall = weighted_total / weight_sum if weight_sum else 100.0

    errors = sum(1 for f in findings if f.severity is Severity.ERROR)
    warnings = sum(1 for f in findings if f.severity is Severity.WARNING)
    suggestions = sum(1 for f in findings if f.severity is Severity.SUGGESTION)

    reasons: list[str] = []
    thresholds = config.thresholds
    if thresholds.max_errors is not None and errors > thresholds.max_errors:
        reasons.append(
            f"{errors} error(s), limit {thresholds.max_errors}"
        )
    if thresholds.max_warnings is not None and warnings > thresholds.max_warnings:
        reasons.append(
            f"{warnings} warning(s), limit {thresholds.max_warnings}"
        )
    if (
        thresholds.max_total_per_100_words is not None
        and words >= MIN_WORDS_FOR_DENSITY
        and per_100 > thresholds.max_total_per_100_words
    ):
        reasons.append(
            f"{per_100:.2f} findings per 100 words, budget "
            f"{thresholds.max_total_per_100_words}"
        )
    if thresholds.min_score is not None and overall < thresholds.min_score:
        reasons.append(f"score {overall:.1f}, minimum {thresholds.min_score}")
    for entry in category_scores:
        if entry.over_budget:
            reasons.append(
                f"{entry.category} at {entry.per_100_words:.2f} per 100 words, "
                f"budget {entry.budget}"
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


def aggregate(scores: list[DocumentScore]) -> dict[str, object]:
    """Roll several documents into one summary.

    Density is recomputed over TOTAL words rather than averaged over documents:
    averaging per-document densities lets a 30-word file outweigh a 3,000-word
    one, which misreports a repository.
    """
    if not scores:
        return {
            "documents": 0,
            "words": 0,
            "findings": 0,
            "errors": 0,
            "warnings": 0,
            "suggestions": 0,
            "per_100_words": 0.0,
            "score": 100.0,
            "passed": True,
            "categories": [],
        }

    words = sum(s.words for s in scores)
    findings = sum(s.total_findings for s in scores)
    errors = sum(s.errors for s in scores)
    warnings = sum(s.warnings for s in scores)
    suggestions = sum(s.suggestions for s in scores)

    # Word-weighted mean, so a long document counts for more than a stub.
    if words:
        overall = sum(s.score * max(s.words, 1) for s in scores) / sum(
            max(s.words, 1) for s in scores
        )
    else:
        overall = sum(s.score for s in scores) / len(scores)

    per_category: dict[str, dict[str, float]] = {}
    for score in scores:
        for entry in score.categories:
            bucket = per_category.setdefault(
                entry.category,
                {"findings": 0, "errors": 0, "warnings": 0, "suggestions": 0, "score": 0.0, "n": 0},
            )
            bucket["findings"] += entry.findings
            bucket["errors"] += entry.errors
            bucket["warnings"] += entry.warnings
            bucket["suggestions"] += entry.suggestions
            bucket["score"] += entry.score
            bucket["n"] += 1

    categories = [
        {
            "category": name,
            "findings": int(data["findings"]),
            "errors": int(data["errors"]),
            "warnings": int(data["warnings"]),
            "suggestions": int(data["suggestions"]),
            "per_100_words": round(data["findings"] / words * 100, 3) if words else 0.0,
            "score": round(data["score"] / data["n"], 1) if data["n"] else 100.0,
        }
        for name, data in sorted(per_category.items())
    ]

    return {
        "documents": len(scores),
        "words": words,
        "findings": findings,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "per_100_words": round(findings / words * 100, 3) if words else 0.0,
        "score": round(overall, 1),
        "passed": all(s.passed for s in scores),
        "categories": categories,
    }
