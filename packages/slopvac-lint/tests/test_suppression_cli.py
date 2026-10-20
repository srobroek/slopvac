"""The directive contract end to end, through `slopvac lint --format json`.

`tests/test_engine.py` holds the engine-level cases. These run the CLI, so they
cover what the engine tests cannot: the native and Vale engines together, each
prose file type, diff scope, and `--fix`. Each assertion is a behaviour that
`docs/suppressions.md` and `slopvac prime` state.
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


def test_a_bad_reason_for_a_vale_rule_is_reported_without_vale(tmp_path):
    """The check follows the config, not the engine: `--no-vale` still reports it."""
    doc = tmp_path / "doc.md"
    doc.write_text(
        f"# Notes\n\n{allow_comment(VALE, 'readability')}\n{VALE_TEXT}\n", encoding="utf-8"
    )
    _, findings = _lint(doc, args=("--no-vale",))
    assert _lines(findings["doc.md"], META) == Counter({3: 1})


def test_native_rules_skip_front_matter(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(f"---\nnote: {NATIVE_TEXT}\n---\n\n# Notes\n\n{NATIVE_TEXT}\n", encoding="utf-8")
    _, findings = _lint(doc, args=("--no-vale",))
    assert sorted(_lines(findings["doc.md"], NATIVE)) == [7]


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


def _changed_doc(repo: Path, base: str, changed: str) -> Path:
    """A repository whose `doc.md` holds `base` at HEAD and `changed` in the tree."""
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Slopvac Tests")
    doc = repo / "doc.md"
    doc.write_text(base, encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-qm", "base")
    doc.write_text(changed, encoding="utf-8")
    return doc


@pytest.fixture
def changed_repo(tmp_path, monkeypatch) -> Path:
    """A committed directive and paragraph, then an added line in that paragraph
    and an added invalid allow directive."""
    doc = _changed_doc(
        tmp_path / "repo",
        f"# Notes\n\n{DISABLE_NEXT_LINE_COMMENT}\nIntro line.\n",
        f"# Notes\n\n{DISABLE_NEXT_LINE_COMMENT}\nIntro line.\n{NATIVE_TEXT}\n\n"
        f"{allow_comment(NATIVE, 'readability')}\n{NATIVE_TEXT}\n",
    )
    monkeypatch.chdir(doc.parent)
    return doc


def test_a_directive_on_an_unchanged_line_covers_added_lines(changed_repo):
    _, findings = _lint(changed_repo, args=("--diff-working-tree", "--no-vale"))
    assert sorted(_lines(findings["doc.md"], NATIVE)) == [8]


def test_diff_scope_reports_an_added_invalid_directive(changed_repo):
    _, findings = _lint(changed_repo, args=("--diff-working-tree", "--no-vale"))
    assert sorted(_lines(findings["doc.md"], META)) == [7]


def test_diff_scope_skips_an_invalid_directive_on_an_unchanged_line(tmp_path, monkeypatch):
    """The old directive is not reported, and it still suppresses nothing on the
    line added to its block."""
    directive = allow_comment(NATIVE, "readability")
    doc = _changed_doc(
        tmp_path / "repo",
        f"# Notes\n\n{directive}\nIntro line.\n",
        f"# Notes\n\n{directive}\nIntro line.\n{NATIVE_TEXT}\n",
    )
    monkeypatch.chdir(doc.parent)
    _, findings = _lint(doc, args=("--diff-working-tree", "--no-vale"))
    assert not _lines(findings["doc.md"], META)
    assert sorted(_lines(findings["doc.md"], NATIVE)) == [5]


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
    ("vale-rule-off", f"<!-- vale {VALE} = NO -->\n{VALE_TEXT}\n<!-- vale {VALE} = YES -->"),
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
def test_lint_reports_a_bad_reason_for_a_vale_rule(vale):
    assert _lines(vale, META) == Counter({_VALE_BLOCKS["bad-reason"].start: 1})


@needs_vale
@pytest.mark.parametrize("label", ["vale-off", "vale-rule-off"])
def test_only_slopvac_directives_suppress_a_vale_finding(vale, label):
    assert _reported(vale, VALE, _VALE_BLOCKS[label]), label


@needs_vale
def test_vale_comments_hide_nothing_in_html_and_mdx(tmp_path):
    html = tmp_path / "doc.html"
    html.write_text(
        f"<html><body>\n<!-- vale off -->\n<p>{VALE_TEXT}</p>\n<!-- vale on -->\n"
        f"<!-- vale {VALE} = NO -->\n<p>{VALE_TEXT}</p>\n<!-- vale {VALE} = YES -->\n"
        "</body></html>\n",
        encoding="utf-8",
    )
    mdx = tmp_path / "doc.mdx"
    mdx.write_text(
        f"# Notes\n\n{{/* vale off */}}\n\n{VALE_TEXT}\n\n{{/* vale on */}}\n\n"
        f"<!-- vale off -->\n\n{VALE_TEXT}\n\n<!-- vale on -->\n",
        encoding="utf-8",
    )
    code, findings = _lint(html, mdx)
    assert code != 2, "the Vale run is incomplete"
    assert {3, 6} <= set(_lines(findings["doc.html"], VALE))
    assert {5, 11} <= set(_lines(findings["doc.mdx"], VALE))


@needs_vale
@pytest.mark.skipif(rst_converter() is None, reason="rst2html is not on PATH")
def test_a_vale_comment_hides_nothing_in_rst(tmp_path):
    doc = tmp_path / "doc.rst"
    doc.write_text(f"Notes\n=====\n\n.. vale off\n\n{VALE_TEXT}\n\n.. vale on\n", encoding="utf-8")
    code, findings = _lint(doc)
    assert code != 2, "the Vale run is incomplete"
    assert 6 in _lines(findings["doc.rst"], VALE)


@needs_vale
def test_vale_rules_skip_front_matter_like_native_rules(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text(f"---\nnote: {VALE_TEXT}\n---\n\n# Notes\n\n{VALE_TEXT}\n", encoding="utf-8")
    _, findings = _lint(doc)
    assert sorted(set(_lines(findings["doc.md"], VALE))) == [7]


@needs_vale
def test_a_directive_in_a_text_file_draws_no_vale_finding(tmp_path):
    """Vale reads a `.txt` file as plain text, so it lints the directive's words."""
    doc = tmp_path / "doc.txt"
    doc.write_text(
        f"Notes\n\n{DISABLE_NEXT_LINE_COMMENT}\n{VALE_TEXT}\n\n{VALE_TEXT}\n", encoding="utf-8"
    )
    _, findings = _lint(doc)
    assert not [finding for finding in findings["doc.txt"] if finding["line"] == 3]
    assert sorted(set(_lines(findings["doc.txt"], VALE))) == [6]


@needs_vale
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


# --- code-comment mode ----------------------------------------------------------

# In comment mode every comment-safe rule runs in Vale; with --no-vale the native
# engine runs the same rules on the comment projection. Each line number below is
# asserted for both engines.
_PYTHON = "\n".join(
    [
        f"# {DISABLE_NEXT_LINE_COMMENT}",
        f"# {VALE_TEXT}",  # 2: covered, the next comment block
        f"# {NATIVE_TEXT}",  # 3: covered, the same block
        "x = 1",
        "",
        f"# {VALE_TEXT}",  # 6: reported
        f"# {NATIVE_TEXT}",  # 7: reported
        f"# {allow_comment(VALE, VALE_REASON)}",
        f"# {allow_comment(NATIVE, NATIVE_REASON)}",
        f"# {VALE_TEXT}",  # 10: covered by an allow
        f"# {NATIVE_TEXT}",  # 11: covered by an allow
        f"y = 2  # {DISABLE_NEXT_LINE_COMMENT}",
        "z = 3",
        f"# {VALE_TEXT}",  # 14: covered, after a code line
        f"# {NATIVE_TEXT}",  # 15: covered
        "#",
        f"# {VALE_TEXT}",  # 17: reported, an empty comment line ends a block
        f"# {NATIVE_TEXT}",  # 18: reported
        f"# {allow_comment(VALE, 'readability')}",  # 19: meta.invalid-suppression
        f"# {VALE_TEXT}",  # 20: reported
        f"# {DISABLE_COMMENT}",
        f"# {VALE_TEXT}",  # 22: covered by the region
        "w = 4",
        f"# {NATIVE_TEXT}",  # 24: covered by the region
        f"# {ENABLE_COMMENT}",
        f"# {NATIVE_TEXT}",  # 26: reported
    ]
) + "\n"
_TYPESCRIPT = "\n".join(
    [
        f"// {DISABLE_NEXT_LINE_COMMENT}",
        f"// {VALE_TEXT}",  # 2: covered
        "const x = 1;",
        f"// {VALE_TEXT}",  # 4: reported
        f"/* {DISABLE_NEXT_LINE_COMMENT} */",
        "/*",
        f" * {VALE_TEXT}",  # 7: covered, the next comment block
        " */",
        f"// {VALE_TEXT}",  # 9: reported
    ]
) + "\n"
_DIRECTIVE_LINES = {"a.py": {1, 8, 9, 12, 19, 21, 25}, "a.ts": {1, 5}}


@pytest.fixture(scope="module", params=[pytest.param("vale", marks=needs_vale), "native"])
def comments(request, tmp_path_factory) -> dict[str, list[dict]]:
    """Both runs exit 2: comment mode reports the rules it cannot run in comments."""
    root = tmp_path_factory.mktemp(f"comments-{request.param}")
    (root / "a.py").write_text(_PYTHON, encoding="utf-8")
    (root / "a.ts").write_text(_TYPESCRIPT, encoding="utf-8")
    args = ("--mode", "code-comments") + (("--no-vale",) if request.param == "native" else ())
    _, findings = _lint(root / "a.py", root / "a.ts", args=args)
    return findings


@pytest.mark.parametrize(
    ("name", "rule_id", "line", "reported"),
    [
        ("a.py", VALE, 2, False),
        ("a.py", NATIVE, 3, False),
        ("a.py", VALE, 6, True),
        ("a.py", NATIVE, 7, True),
        ("a.py", VALE, 10, False),
        ("a.py", NATIVE, 11, False),
        ("a.py", VALE, 14, False),
        ("a.py", NATIVE, 15, False),
        ("a.py", VALE, 17, True),
        ("a.py", NATIVE, 18, True),
        ("a.py", VALE, 20, True),
        ("a.py", VALE, 22, False),
        ("a.py", NATIVE, 24, False),
        ("a.py", NATIVE, 26, True),
        ("a.ts", VALE, 2, False),
        ("a.ts", VALE, 4, True),
        ("a.ts", VALE, 7, False),
        ("a.ts", VALE, 9, True),
    ],
)
def test_a_comment_directive_covers_the_next_comment_block(
    comments, name, rule_id, line, reported
):
    assert (line in _lines(comments[name], rule_id)) is reported, (name, rule_id, line)


def test_comment_mode_reports_a_bad_directive_and_lints_no_directive_text(comments):
    assert _lines(comments["a.py"], META) == Counter({19: 1})
    for name, lines in _DIRECTIVE_LINES.items():
        stray = [
            finding
            for finding in comments[name]
            if finding["line"] in lines and finding["rule_id"] != META
        ]
        assert not stray, (name, stray)
