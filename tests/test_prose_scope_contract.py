from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITE_DOCS = ROOT / "packages/slopvac/skills/write-docs/SKILL.md"
REVIEW_DOCS = ROOT / "packages/slopvac/skills/review-docs/SKILL.md"


def test_writer_names_the_code_change_scope_cases() -> None:
    text = WRITE_DOCS.read_text()
    assert "directly explain or specify the changed code" in text
    assert "same file or elsewhere" in text
    assert "explicitly requested prose edit is in scope" in text


def test_reviewer_marks_unrelated_scope_cases_and_keeps_related_cases() -> None:
    text = REVIEW_DOCS.read_text()
    assert "same-file comments and documentation elsewhere" in text
    assert "as a `defect`" in text
    assert "stale comment that directly describes changed behavior in scope" in text
    assert "explicitly requested prose edit is in scope" in text
