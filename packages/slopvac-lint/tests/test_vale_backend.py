import json
import subprocess
from pathlib import Path

import pytest

from slopvac.compile_vale import CompileResult
from slopvac.config import Severity
from slopvac.vale import hide_vale_comments, run_compiled_vale
from slopvac.vale_probe import resolved_checks


@pytest.mark.parametrize(
    ("stdout", "stderr", "returncode", "complete"),
    [
        ("{}", "", 0, True),
        ("{}", "", 2, False),
        ("{}", "warning: skipped input", 0, False),
        ("", "", 0, False),
        ('{"doc.md":', "", 0, False),
        ('{"doc.md": {}}', "", 0, False),
        ('{"doc.md": [null]}', "", 0, False),
        ('{"doc.md": [{"Check": "style.rule"}]}', "", 0, False),
    ],
)
def test_backend_report_completeness(
    tmp_path, monkeypatch, stdout, stderr, returncode, complete
):
    config = tmp_path / ".vale.ini"
    config.write_text("StylesPath = styles\n")
    compiled = CompileResult(tmp_path, config, vale_rules=["style.rule"])
    monkeypatch.setattr("shutil.which", lambda _: "/fake/vale")

    def run(argv, **kwargs):
        if "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, "vale version 3.21.0\n", "")
        if "ls-config" in argv:
            return subprocess.CompletedProcess(argv, 0, '{"Checks": ["style.rule"]}', "")
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    monkeypatch.setattr("subprocess.run", run)
    result = run_compiled_vale(
        [tmp_path / "doc.md"], compiled, {"style.rule": Severity.WARNING}, {}
    )
    assert (not result.unchecked) is complete


@pytest.mark.parametrize(
    ("version_output", "runs"),
    [
        ("vale version 3.21.0\n", True),
        ("vale version 3.15.0\n", True),
        ("vale version 3.14.9\n", False),
        ("", False),
    ],
)
def test_vale_below_the_documented_floor_is_treated_as_absent(
    tmp_path, monkeypatch, version_output, runs
):
    """README: Vale 3.15 or later runs the sub-gate. Before this probe a 3.14 binary
    reused a tree compiled under 3.21 and reported findings with no unchecked note,
    so the run looked complete."""
    config = tmp_path / ".vale.ini"
    config.write_text("StylesPath = styles\n")
    compiled = CompileResult(tmp_path, config, vale_rules=["style.rule"])
    monkeypatch.setattr("shutil.which", lambda _: "/fake/vale")

    def run(argv, **kwargs):
        if "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, version_output, "")
        if "ls-config" in argv:
            return subprocess.CompletedProcess(argv, 0, '{"Checks": ["style.rule"]}', "")
        return subprocess.CompletedProcess(argv, 0, "{}", "")

    monkeypatch.setattr("subprocess.run", run)
    result = run_compiled_vale(
        [tmp_path / "doc.md"], compiled, {"style.rule": Severity.WARNING}, {}
    )
    assert (not result.unchecked) is runs
    if not runs:
        assert "3.15.0" in result.unchecked[0]


def test_cache_fingerprint_changes_with_the_vale_version(tmp_path):
    """A tree compiled under one Vale is not the tree another release produces: the
    probe decides which payloads stay native, and pattern escaping changed at 3.21."""
    from slopvac.config import Config, Profile, resolve_for
    from slopvac.rules import load_ruleset
    from slopvac.vale_cache import fingerprint

    ruleset = load_ruleset()
    resolved = resolve_for(Config(profile=Profile.NORMAL), tmp_path / "sample.md")
    levels = {"style.rule": "warning"}
    old = fingerprint(ruleset.rules, resolved, levels, None, (3, 21, 0))
    new = fingerprint(ruleset.rules, resolved, levels, None, (3, 22, 0))
    same = fingerprint(ruleset.rules, resolved, levels, None, (3, 21, 0))
    assert old != new
    assert old == same


@pytest.mark.parametrize(
    "payload", [[], {}, {"Checks": "style.rule"}, {"Checks": [None]}]
)
def test_malformed_resolved_config_cannot_prove_rule_coverage(
    tmp_path, monkeypatch, payload
):
    monkeypatch.setattr(
        "subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, 0, json.dumps(payload), ""
        ),
    )
    assert resolved_checks(tmp_path / ".vale.ini") is None


@pytest.mark.parametrize(
    "text",
    [
        "<!-- vale off -->\nText.\n<!-- vale on -->\n",
        "<!--vale Style.Rule = NO-->\nText.\n",
        '<!-- vale Style.Rule["a", "b"] = NO -->\n',
        "<!-- Vale styles = Style -->\n",
        "{/* vale off */}\n\nText.\n",
        "Text.\n\n.. vale off\n\nText.\n",
        "..\n   vale Style = NO\n",
    ],
)
def test_each_vale_comment_form_is_blanked_in_place(text):
    hidden = hide_vale_comments(text)
    assert "vale" not in hidden.lower()
    assert len(hidden) == len(text)
    assert [len(line) for line in hidden.split("\n")] == [len(line) for line in text.split("\n")]


def test_text_that_only_names_vale_is_left_alone():
    text = "Vale lints prose.\n<!-- a note on vale -->\n.. note:: vale\n`vale off`\n"
    assert hide_vale_comments(text) == text


def test_vale_reads_a_copy_without_its_comments_and_reports_the_source(tmp_path, monkeypatch):
    doc = tmp_path / "doc.md"
    doc.write_bytes(b"<!-- vale off -->\r\nRobust text.\r\n")
    config = tmp_path / ".vale.ini"
    config.write_text("StylesPath = styles\n")
    compiled = CompileResult(tmp_path, config, vale_rules=["style.rule"])
    monkeypatch.setattr("shutil.which", lambda _: "/fake/vale")
    read: list[bytes] = []

    def run(argv, **kwargs):
        if "--version" in argv:
            return subprocess.CompletedProcess(argv, 0, "vale version 3.21.0\n", "")
        if "ls-config" in argv:
            return subprocess.CompletedProcess(argv, 0, '{"Checks": ["style.rule"]}', "")
        target = argv[-1]
        read.append(Path(target).read_bytes())
        alert = {
            "Check": "style.rule", "Message": "m", "Match": "Robust",
            "Line": 2, "Span": [1, 6], "Severity": "warning",
        }
        return subprocess.CompletedProcess(argv, 0, json.dumps({target: [alert]}), "")

    monkeypatch.setattr("subprocess.run", run)
    result = run_compiled_vale([doc], compiled, {"style.rule": Severity.WARNING}, {})
    assert read == [b"<!--      off -->\r\nRobust text.\r\n"]
    assert not result.unchecked
    [finding] = result.findings_for(str(doc))
    assert (finding.path, finding.line, finding.column) == (str(doc), 2, 1)
