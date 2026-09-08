import json
import subprocess

import pytest

from slopvac.compile_vale import CompileResult, resolved_checks
from slopvac.config import Severity
from slopvac.vale import run_compiled_vale


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
        if "ls-config" in argv:
            return subprocess.CompletedProcess(argv, 0, '{"Checks": ["style.rule"]}', "")
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    monkeypatch.setattr("subprocess.run", run)
    result = run_compiled_vale(
        [tmp_path / "doc.md"], compiled, {"style.rule": Severity.WARNING}, {}
    )
    assert (not result.unchecked) is complete


@pytest.mark.parametrize("payload", [[], {}, {"Checks": "style.rule"}, {"Checks": [None]}])
def test_malformed_resolved_config_cannot_prove_rule_coverage(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(
        "subprocess.run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, json.dumps(payload), ""),
    )
    assert resolved_checks(tmp_path / ".vale.ini") is None
