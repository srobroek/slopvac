"""The directive contract end to end, through `slopvac lint --format json`.

`tests/test_engine.py` holds the engine-level cases. These run the CLI, so they
cover what the engine tests cannot: the native and Vale engines together, each
prose file type, diff scope, and `--fix`. Each assertion is a behaviour that
`docs/suppressions.md` and `slopvac prime` state.

A test marked `xfail(strict=True)` records a known defect: it asserts the
behaviour the contract asks for, and it fails today in the way the docs
describe. When a fix lands, the strict marker turns it red. Then delete the
marker and update the docs.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.rules import load_ruleset
from slopvac.suppression import (
    DISABLE_COMMENT,
    DISABLE_NEXT_LINE_COMMENT,
    ENABLE_COMMENT,
    allow_comment,
)
from slopvac.vale_probe import rst_converter

needs_vale = pytest.mark.skipif(shutil.which("vale") is None, reason="vale is not on PATH")

META = "meta.invalid-suppression"
# A rule the native engine runs, and the text that triggers it once. The baseline
# assertion in each test fails first if routing moves the rule to Vale.
NATIVE = "ai-tells-structure.definitional-negation-pair"
NATIVE_TEXT = "Testing is not a phase. It is a habit."
NATIVE_REASON = "factual-correction"
# A rule Vale runs, and the text that triggers it.
VALE = "prose-inflation.slop-lexicon"
VALE_TEXT = "A robust, comprehensive linter."
VALE_REASON = "quotation"

DOCS = Path(__file__).resolve().parents[1] / "docs"


def _document(*blocks: tuple[str, str], head: str = "# Notes") -> tuple[str, dict[str, range]]:
    """Join labelled blocks with blank lines. Return the text and each block's lines."""
    lines = head.splitlines()
    spans: dict[str, range] = {}
    for label, body in blocks:
        lines.append("")
        start = len(lines) + 1
        lines.extend(body.splitlines())
        spans[label] = range(start, len(lines) + 1)
    return "\n".join(lines) + "\n", spans


def _lint(*paths: Path, args: tuple[str, ...] = ()) -> tuple[int, dict[str, list[dict]]]:
    result = CliRunner().invoke(
        main, ["lint", *map(str, paths), "--format", "json", *args]
    )
    assert result.exit_code in (0, 1, 2), result.output
    report = json.loads(result.output)
    return result.exit_code, {
        Path(document["path"]).name: document["findings"] for document in report["documents"]
    }


def _lines(findings: list[dict], rule_id: str) -> Counter[int]:
    return Counter(finding["line"] for finding in findings if finding["rule_id"] == rule_id)


def _reported(findings: list[dict], rule_id: str, span: range) -> bool:
    return any(line in span for line in _lines(findings, rule_id))


# --- the native engine ----------------------------------------------------------

_MARKDOWN, _BLOCKS = _document(
    ("plain", NATIVE_TEXT),
    ("allowed", f"{allow_comment(NATIVE, NATIVE_REASON)}\n{NATIVE_TEXT}"),
    ("other-rule-allowed", f"{allow_comment(VALE, VALE_REASON)}\n{NATIVE_TEXT}"),
    ("bad-reason", f"{allow_comment(NATIVE, 'readability')}\n{NATIVE_TEXT}"),
    ("no-reason", f"<!-- slopvac-allow: rule={NATIVE} -->\n{NATIVE_TEXT}"),
    ("unknown-rule", f"{allow_comment('nope.nothing', 'quotation')}\n{NATIVE_TEXT}"),
    ("malformed", f"<!-- slopvac-allow: rule= {NATIVE} reason={NATIVE_REASON} -->"),
    (
        "no-exceptions",
        f"{allow_comment('prose-format.no-unicode-dash', 'readability')}\nA dash \u2014 here.",
    ),
    (
        "next-block",
        f"{DISABLE_NEXT_LINE_COMMENT}\n\n<!-- a plain comment -->\n"
        f"The first line of a paragraph.\n{NATIVE_TEXT}",
    ),
    ("same-line", f"{allow_comment(NATIVE, NATIVE_REASON)} {NATIVE_TEXT}"),
    ("first-item", f"{DISABLE_NEXT_LINE_COMMENT}\n- {NATIVE_TEXT}"),
    ("second-item", f"- {NATIVE_TEXT}"),
    ("table", f"{DISABLE_NEXT_LINE_COMMENT}\n| a | b |\n| --- | --- |\n| {NATIVE_TEXT} | x |"),
    ("region", f"{DISABLE_COMMENT}\n{NATIVE_TEXT}\n\n{NATIVE_TEXT}\n{ENABLE_COMMENT}"),
    ("after-region", NATIVE_TEXT),
    ("stray-enable", f"{ENABLE_COMMENT}\n{NATIVE_TEXT}"),
    ("code-span", f"Write `{DISABLE_COMMENT}` to start a region."),
    ("after-code-span", NATIVE_TEXT),
    ("fence", f"```markdown\n{DISABLE_COMMENT}\n```"),
    ("after-fence", NATIVE_TEXT),
    ("capitals", f"<!-- SLOPVAC-DISABLE-NEXT-LINE -->\n{NATIVE_TEXT}"),
    ("capitals-allow", f"<!-- SLOPVAC-ALLOW: rule={NATIVE} reason={NATIVE_REASON} -->"),
    ("nested", f"{DISABLE_COMMENT}\n{DISABLE_COMMENT}\n{NATIVE_TEXT}\n{ENABLE_COMMENT}"),
    ("after-first-enable", f"{NATIVE_TEXT}\n{ENABLE_COMMENT}"),
    ("unclosed", f"{DISABLE_COMMENT}\n{NATIVE_TEXT}\n\n{NATIVE_TEXT}"),
    head=f'---\nnote: "{DISABLE_COMMENT}"\n---\n\n# Notes',
)


@pytest.fixture(scope="module")
def native(tmp_path_factory) -> dict[str, list[dict]]:
    """One `--no-vale` run over a Markdown, a text, an HTML, and a generated file."""
    root = tmp_path_factory.mktemp("native")
    files = {
        "doc.md": _MARKDOWN,
        "doc.txt": (
            f"Notes\n\n{DISABLE_NEXT_LINE_COMMENT}\n{NATIVE_TEXT}\n\n"
            f"{allow_comment(NATIVE, NATIVE_REASON)}\n{NATIVE_TEXT}\n\n{NATIVE_TEXT}\n"
        ),
        "doc.html": (
            f"<html><body>\n{DISABLE_NEXT_LINE_COMMENT}\n<p>{NATIVE_TEXT}</p>\n"
            f"{DISABLE_COMMENT}\n<p>{NATIVE_TEXT}</p>\n{ENABLE_COMMENT}\n"
            f"<p>{NATIVE_TEXT}</p>\n</body></html>\n"
        ),
        "generated.md": f"<!-- generated by a tool -->\n# Notes\n\n{NATIVE_TEXT}\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    _, findings = _lint(*(root / name for name in files), args=("--no-vale",))
    return findings


def test_the_native_rule_fires_without_a_directive(native):
    assert _reported(native["doc.md"], NATIVE, _BLOCKS["plain"]), "the rule moved to Vale"


@pytest.mark.parametrize(
    ("label", "reported"),
    [
        ("allowed", False),
        ("other-rule-allowed", True),
        ("bad-reason", True),
        ("no-reason", True),
        ("unknown-rule", True),
        ("next-block", False),
        ("same-line", False),
        ("first-item", False),
        ("second-item", True),
        ("table", False),
        ("region", False),
        ("after-region", True),
        ("stray-enable", True),
        ("after-code-span", True),
        ("after-fence", True),
        ("capitals", True),
        ("nested", False),
        ("after-first-enable", True),
        ("unclosed", False),
    ],
)
def test_each_directive_covers_the_documented_scope(native, label, reported):
    assert _reported(native["doc.md"], NATIVE, _BLOCKS[label]) is reported, label


def test_front_matter_holds_a_quoted_directive(native):
    """A disable comment in front matter would otherwise silence the whole file."""
    front_matter = range(1, 4)
    assert _reported(native["doc.md"], NATIVE, _BLOCKS["plain"])
    assert not any(line in front_matter for line in _lines(native["doc.md"], META))


def test_lint_reports_each_bad_allow_directive_on_its_line(native):
    reported = set(_lines(native["doc.md"], META))
    expected = {
        _BLOCKS[label].start
        for label in ("bad-reason", "no-reason", "unknown-rule", "malformed", "no-exceptions")
    }
    assert reported == expected, "capitals and quoted directives report nothing"
    assert _reported(native["doc.md"], "prose-format.no-unicode-dash", _BLOCKS["no-exceptions"])


def test_a_bad_reason_for_a_rule_that_does_not_run_is_silent(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(
        f"# Notes\n\n{allow_comment(NATIVE, 'readability')}\n{NATIVE_TEXT}\n", encoding="utf-8"
    )
    _, findings = _lint(doc, args=("--no-vale", "--disable", NATIVE))
    assert not _lines(findings["doc.md"], META)
    assert not _lines(findings["doc.md"], NATIVE)


def test_the_reference_gives_each_message_that_lint_reports(native):
    """Each emitted message, with its values put back as placeholders, is a row of
    the message table in docs/suppressions.md."""
    reference = (DOCS / "suppressions.md").read_text(encoding="utf-8")
    rule = load_ruleset().by_id(NATIVE)
    templated = set()
    for finding in native["doc.md"]:
        if finding["rule_id"] != META:
            continue
        message = (
            finding["message"]
            .replace(", ".join(rule.exceptions), "<exceptions>")
            .replace("none defined", "<exceptions>")
            .replace('"readability"', '"<reason>"')
            .replace("prose-format.no-unicode-dash", "<rule_id>")
            .replace("nope.nothing", "<rule_id>")
            .replace(NATIVE, "<rule_id>")
        )
        templated.add(message)
        assert f"`{message}`" in reference, message
    assert len(templated) == 4, templated


def test_text_and_html_files_honour_directives(native):
    text = native["doc.txt"]
    assert sorted(_lines(text, NATIVE)) == [9]
    html = native["doc.html"]
    assert sorted(_lines(html, NATIVE)) == [7]


def test_a_generated_marker_does_not_exclude_a_file(native):
    assert _lines(native["generated.md"], NATIVE)


@pytest.mark.skipif(rst_converter() is None, reason="rst2html is not on PATH")
def test_rst_honours_a_directive_on_its_own_line_and_in_a_raw_block(tmp_path):
    doc = tmp_path / "doc.rst"
    doc.write_text(
        f"Notes\n=====\n\n{DISABLE_NEXT_LINE_COMMENT}\n{NATIVE_TEXT}\n\n"
        f".. raw:: html\n\n   {DISABLE_NEXT_LINE_COMMENT}\n\n{NATIVE_TEXT}\n\n"
        f".. {DISABLE_NEXT_LINE_COMMENT}\n\n{NATIVE_TEXT}\n",
        encoding="utf-8",
    )
    _, findings = _lint(doc, args=("--no-vale",))
    assert sorted(_lines(findings["doc.rst"], NATIVE)) == [15]


# --- diff scope -----------------------------------------------------------------


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def changed_repo(tmp_path, monkeypatch) -> Path:
    """A committed directive and paragraph, then an added line in that paragraph
    and an added invalid allow directive."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Slopvac Tests")
    doc = repo / "doc.md"
    doc.write_text(f"# Notes\n\n{DISABLE_NEXT_LINE_COMMENT}\nIntro line.\n", encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-qm", "base")
    doc.write_text(
        f"# Notes\n\n{DISABLE_NEXT_LINE_COMMENT}\nIntro line.\n{NATIVE_TEXT}\n\n"
        f"{allow_comment(NATIVE, 'readability')}\n{NATIVE_TEXT}\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)
    return doc


def test_a_directive_on_an_unchanged_line_covers_added_lines(changed_repo):
    _, findings = _lint(changed_repo, args=("--diff-working-tree", "--no-vale"))
    assert sorted(_lines(findings["doc.md"], NATIVE)) == [8]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="diff scope drops every meta.invalid-suppression finding: it has no "
    "matched_text, so diff_scope cannot place it on an added line",
)
def test_diff_scope_reports_an_added_invalid_directive(changed_repo):
    _, findings = _lint(changed_repo, args=("--diff-working-tree", "--no-vale"))
    assert sorted(_lines(findings["doc.md"], META)) == [7]


# --- the Vale engine ------------------------------------------------------------

_VALE_MARKDOWN, _VALE_BLOCKS = _document(
    ("plain", VALE_TEXT),
    ("allowed", f"{allow_comment(VALE, VALE_REASON)}\n{VALE_TEXT}"),
    ("bad-reason", f"{allow_comment(VALE, 'readability')}\n{VALE_TEXT}"),
    ("next-block", f"{DISABLE_NEXT_LINE_COMMENT}\nThe first line.\n{VALE_TEXT}"),
    ("region", f"{DISABLE_COMMENT}\n{VALE_TEXT}\n{ENABLE_COMMENT}"),
    ("after-region", VALE_TEXT),
    ("quotation", 'Avoid "robust" in docs.'),
    ("code-span", "Avoid `robust` in docs."),
    ("vale-off", f"<!-- vale off -->\n{VALE_TEXT}\n<!-- vale on -->"),
)


@pytest.fixture(scope="module")
def vale(tmp_path_factory) -> list[dict]:
    doc = tmp_path_factory.mktemp("vale") / "doc.md"
    doc.write_text(_VALE_MARKDOWN, encoding="utf-8")
    code, findings = _lint(doc)
    assert code != 2, "the Vale run is incomplete"
    return findings["doc.md"]


@needs_vale
@pytest.mark.parametrize(
    ("label", "reported"),
    [
        ("plain", True),
        ("allowed", False),
        ("bad-reason", True),
        ("next-block", False),
        ("region", False),
        ("after-region", True),
        ("quotation", False),
        ("code-span", False),
    ],
)
def test_directives_and_automatic_exceptions_apply_to_vale_findings(vale, label, reported):
    assert _reported(vale, VALE, _VALE_BLOCKS[label]) is reported, label


@needs_vale
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="a Vale-routed rule is not in the native engine's active set, so "
    "scan_suppressions treats it as inactive and reports no bad reason",
)
def test_lint_reports_a_bad_reason_for_a_vale_rule(vale):
    assert set(_lines(vale, META)) == {_VALE_BLOCKS["bad-reason"].start}


@needs_vale
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Vale honours its own comments, which name no exception",
)
def test_only_slopvac_directives_suppress_a_vale_finding(vale):
    assert _reported(vale, VALE, _VALE_BLOCKS["vale-off"])


@needs_vale
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="Vale reads front matter values, which the native engine skips",
)
def test_vale_rules_skip_front_matter_like_native_rules(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(f"---\nnote: {VALE_TEXT}\n---\n\n# Notes\n\nPlain text.\n", encoding="utf-8")
    _, findings = _lint(doc)
    assert not _lines(findings["doc.md"], VALE)


@needs_vale
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="comment mode takes Vale findings as they are and applies no directive",
)
def test_comment_mode_honours_a_directive(tmp_path):
    source = tmp_path / "a.ts"
    source.write_text(
        f"// {DISABLE_NEXT_LINE_COMMENT}\n// {VALE_TEXT}\nconst x = 1;\n", encoding="utf-8"
    )
    _, findings = _lint(source, args=("--mode", "code-comments"))
    assert _lines(findings["a.ts"], VALE) == Counter()


@needs_vale
def test_fix_leaves_suppressed_text_alone(tmp_path):
    doc = tmp_path / "doc.md"
    sentence = "We utilize the tool."
    doc.write_text(
        f"# Notes\n\n{sentence}\n\n{DISABLE_NEXT_LINE_COMMENT}\n{sentence}\n\n"
        f"{DISABLE_COMMENT}\n{sentence}\n{ENABLE_COMMENT}\n",
        encoding="utf-8",
    )
    _lint(doc, args=("--fix",))
    lines = doc.read_text(encoding="utf-8").splitlines()
    assert lines[2] == "We use the tool."
    assert lines[5] == sentence
    assert lines[8] == sentence
