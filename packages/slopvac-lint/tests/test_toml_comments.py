import json
import shutil
import subprocess

import pytest

from slopvac.compile_vale import CompileResult
from slopvac.config import Severity
from slopvac.toml_comments import comment_projection, extract_comments
from slopvac.vale import run_compiled_vale

def test_extracts_full_and_trailing_comments_with_columns():
    text = "[tool]" + chr(10) + "value = 1 # trailing" + chr(10) + "# full" + chr(10)
    assert [(c.line, c.column, c.body) for c in extract_comments(text)] == [(2, 11, " trailing"), (3, 1, " full")]

def test_ignores_hash_in_all_string_forms_and_values():
    q = chr(34)
    text = "basic = " + q + "#" + q + chr(10) + "literal = '#'" + chr(10) + "multib = " + q * 3 + "#" + chr(10) + "inside" + q * 3 + chr(10) + "literalb = " + chr(39) * 3 + "#" + chr(10) + "inside" + chr(39) * 3 + chr(10) + "arr = [" + q + "#" + q + ", 1]" + chr(10) + "inline = {x = " + q + "#" + q + "} # seen" + chr(10)
    assert [(c.line, c.body) for c in extract_comments(text)] == [(8, " seen")]

def test_projection_preserves_newlines_columns_and_masks_values():
    text = "key = " + chr(34) + "# hidden" + chr(34) + " # visible" + chr(13) + chr(10) + "# full" + chr(13) + chr(10)
    projected = comment_projection(text)
    assert len(projected) == len(text) and projected.count(chr(10)) == text.count(chr(10))
    assert projected.splitlines()[0].rindex("#") == text.splitlines()[0].rindex("#")
    assert projected.splitlines()[0].endswith("# visible")

def test_incomplete_strings_do_not_crash_or_invent_comments():
    assert extract_comments('broken = "unterminated # not comment') == []
    assert extract_comments("broken = 'unterminated # not comment") == []

def test_vale_projection_maps_temp_findings_to_original_path(tmp_path, monkeypatch):
    source = tmp_path / "mise.toml"
    source.write_text("x = 1 # robust" + chr(10))
    config = tmp_path / ".vale.ini"
    config.write_text("StylesPath = styles" + chr(10))
    compiled = CompileResult(tmp_path, config, vale_rules=["style.rule"])
    monkeypatch.setattr("shutil.which", lambda _: "/fake/vale")
    def run(argv, **kwargs):
        if "--version" in argv: return subprocess.CompletedProcess(argv, 0, "vale version 3.21.0" + chr(10), "")
        if "ls-config" in argv: return subprocess.CompletedProcess(argv, 0, json.dumps({"Checks": ["style.rule"]}), "")
        target = argv[-1]
        alert = {"Check": "style.rule", "Message": "bad", "Match": "robust", "Line": 1, "Span": [7, 13], "Severity": "warning"}
        return subprocess.CompletedProcess(argv, 0, json.dumps({target: [alert]}), "")
    monkeypatch.setattr("subprocess.run", run)
    result = run_compiled_vale([source], compiled, {"style.rule": Severity.WARNING}, {})
    finding = result.by_path[str(source)][0]
    assert finding.path == str(source) and finding.line == 1 and finding.column == 7


@pytest.mark.skipif(shutil.which("vale") is None, reason="vale is not on PATH")
def test_real_vale_lints_only_toml_comments_and_maps_position(tmp_path):
    source = tmp_path / "settings.toml"
    source.write_text('key = "needle"\nvalue = "needle"\n# needle\n', encoding="utf-8")
    styles = tmp_path / "styles" / "test"
    styles.mkdir(parents=True)
    (styles / "rule.yml").write_text(
        "extends: existence\nmessage: 'forbidden token: %s'\nlevel: warning\ntokens:\n  - needle\n",
        encoding="utf-8",
    )
    config = tmp_path / ".vale.ini"
    config.write_text(
        "StylesPath = styles\nMinAlertLevel = suggestion\n\n[*.md]\nBasedOnStyles = test\n",
        encoding="utf-8",
    )
    compiled = CompileResult(tmp_path, config, vale_rules=["test.rule"])
    result = run_compiled_vale([source], compiled, {"test.rule": Severity.WARNING}, {"test.rule": "prose"})
    assert not any("E201" in note for note in result.unchecked)
    findings = result.by_path[str(source)]
    assert [(finding.line, finding.column, finding.matched_text) for finding in findings] == [(3, 3, "needle")]
