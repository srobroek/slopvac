"""The HTML report.

The report exists to make a run actionable, and its one non-negotiable property is
that a gap is louder than a score: a reader who sees 90/100 and misses "the Vale
engine did not run" has been actively misled. Most of what follows asserts that.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from slopvac.html import render_html
from slopvac.model import DocumentScore, Finding, Severity
from slopvac.report import CategorySummary, RunSummary

STAMP = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)


def _finding(**kwargs) -> Finding:
    base = dict(
        path="a.md",
        line=7,
        column=3,
        rule_id="prose-craft.sentence-length",
        category="prose-craft",
        severity=Severity.WARNING,
        message="sentence of 40 words > 34",
    )
    base.update(kwargs)
    return Finding(**base)


def _doc(**kwargs) -> DocumentScore:
    base = dict(
        path="a.md",
        profile="normal",
        words=100,
        sentences=8,
        paragraphs=3,
        findings=[],
        categories=[],
        total_findings=0,
        score=100.0,
        passed=True,
    )
    base.update(kwargs)
    return DocumentScore(**base)


def _summary(**kwargs) -> RunSummary:
    base = dict(
        documents=1,
        words=100,
        findings=0,
        errors=0,
        warnings=0,
        suggestions=0,
        per_100_words=0.0,
        score=100.0,
        passed=True,
        categories=[],
    )
    base.update(kwargs)
    return RunSummary(**base)


def _render(summary: RunSummary, documents: list[DocumentScore]) -> str:
    return render_html(summary, documents, "1.2.3", generated=STAMP)


def test_a_clean_run_renders_a_whole_page():
    page = _render(_summary(), [_doc()])
    assert page.startswith("<!doctype html>")
    assert page.rstrip().endswith("</html>")
    assert "PASS" in page
    assert "1.2.3" in page
    assert "2026-01-02 03:04 UTC" in page


def test_the_page_needs_no_network_or_assets():
    """It is mailed, attached to a CI artifact, and opened from file://. Any
    external reference breaks all three."""
    page = _render(_summary(), [_doc()])
    for forbidden in ("<script", "http://", "https://cdn", "<link", "<img", "@import"):
        assert forbidden not in page, f"the report reaches outside itself: {forbidden}"


def test_an_unchecked_note_is_rendered_above_the_score():
    """THE CENTRAL GUARANTEE. A score produced with an engine that failed to start
    is an upper bound, and a reader must see that before the number."""
    doc = _doc(
        score=91.5,
        unchecked=["Vale rejected a compiled rule and therefore linted NOTHING"],
    )
    page = _render(_summary(score=91.5), [doc])
    assert "did not run" in page
    assert page.index("did not run") < page.index("91.5"), (
        "the score appears before the gap that invalidates it"
    )
    # And the document row carries a marker, so a 40-file report still shows which.
    assert "&#9888;" in page


def test_a_clean_run_has_no_unchecked_panel():
    page = _render(_summary(), [_doc()])
    assert "did not run" not in page


def test_matched_text_and_messages_are_escaped():
    """A finding carries source text, and the documents this tool reads are exactly
    the ones that discuss markup."""
    doc = _doc(
        findings=[_finding(message="<script>alert(1)</script> & <b>", matched_text="<i>")],
        total_findings=1,
        score=80.0,
        passed=True,
    )
    page = _render(_summary(findings=1, score=80.0), [doc])
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page
    assert "&amp;" in page


def test_a_path_with_markup_in_it_is_escaped():
    doc = _doc(path="<img src=x>.md")
    page = _render(_summary(), [doc])
    assert "<img src=x>" not in page
    assert "&lt;img" in page


def test_categories_with_no_findings_are_omitted():
    """23 categories fire on nothing in a clean-ish document, and listing the zeroes
    buries the ones that matter."""
    page = _render(
        _summary(
            findings=3,
            categories=[
                CategorySummary(
                    category="prose-craft",
                    findings=3,
                    errors=0,
                    warnings=3,
                    suggestions=0,
                    per_100_words=3.0,
                    score=90.0,
                ),
                CategorySummary(
                    category="ste-safety",
                    findings=0,
                    errors=0,
                    warnings=0,
                    suggestions=0,
                    per_100_words=0.0,
                    score=100.0,
                ),
            ],
        ),
        [_doc()],
    )
    assert "prose-craft" in page
    assert "ste-safety" not in page


def test_failing_documents_are_expanded_and_passing_ones_are_not():
    """A reader opens the report because something failed. Making them click for it
    is the one interaction the report should not require."""
    bad = _doc(
        path="bad.md",
        score=40.0,
        passed=False,
        total_findings=2,
        findings=[_finding(path="bad.md"), _finding(path="bad.md", line=9)],
        failure_reasons=["score 40.0 is below min_score 70"],
    )
    good = _doc(path="good.md", score=95.0, total_findings=1, findings=[_finding(path="good.md")])
    page = _render(_summary(documents=2, findings=3, score=67.0, passed=False), [bad, good])

    bad_at = page.index("bad.md")
    good_at = page.index("good.md")
    # Worst first, in every table on the page.
    assert bad_at < good_at
    assert "<details open>" in page
    assert "score 40.0 is below min_score 70" in page


def test_a_single_document_is_expanded_even_when_it_passes():
    """A one-file report that renders as one collapsed line hides the whole reason
    it was generated."""
    doc = _doc(total_findings=1, score=95.0, findings=[_finding()])
    page = _render(_summary(findings=1, score=95.0), [doc])
    assert "<details open>" in page


def test_findings_are_ordered_by_severity_then_line():
    doc = _doc(
        total_findings=3,
        score=50.0,
        findings=[
            _finding(line=50, severity=Severity.SUGGESTION, rule_id="a.suggestion"),
            _finding(line=40, severity=Severity.ERROR, rule_id="a.error"),
            _finding(line=30, severity=Severity.WARNING, rule_id="a.warning"),
        ],
    )
    page = _render(_summary(findings=3, score=50.0), [doc])
    assert page.index("a.error") < page.index("a.warning") < page.index("a.suggestion")


@pytest.mark.parametrize(
    "score,band",
    [(100.0, "strong"), (85.0, "strong"), (84.9, "fair"), (70.0, "fair"), (69.9, "weak")],
)
def test_score_bands_match_the_profile_thresholds(score, band):
    """A badge must never read `good` on a document the gate rejected, so the
    boundaries are the profile `min_score` values: strict 85, normal 70."""
    page = _render(_summary(score=score), [_doc(score=score)])
    assert band in page


def test_a_replacement_is_shown_as_the_fix():
    doc = _doc(
        total_findings=1,
        score=90.0,
        findings=[_finding(matched_text="utilise", replacement="use")],
    )
    page = _render(_summary(findings=1, score=90.0), [doc])
    assert "use" in page
    assert "&rarr;" in page
