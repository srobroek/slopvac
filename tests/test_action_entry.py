from __future__ import annotations

import json
import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from scripts import action_entry


def test_parse_input_paths_preserves_spaces() -> None:
    assert action_entry.parse_input_paths('README.md "docs/release notes.md"') == [
        "README.md",
        "docs/release notes.md",
    ]


def test_lint_writes_json_outputs_and_keeps_path_argument(tmp_path: Path) -> None:
    path_list = tmp_path / "targets"
    path_list.write_bytes(b"docs/release notes.md\0")
    github_output = tmp_path / "output"
    summary_path = tmp_path / "summary"
    report = {
        "summary": {
            "score": 91.5,
            "findings": 1,
            "errors": 0,
            "warnings": 1,
            "suggestions": 0,
            "documents": 1,
            "words": 100,
            "per_100_words": 1.0,
            "passed": True,
            "categories": [
                {
                    "category": "style",
                    "findings": 1,
                    "errors": 0,
                    "warnings": 1,
                    "per_100_words": 1.0,
                    "score": 91.5,
                }
            ],
        },
        "documents": [],
    }
    environment = {
        "PATH_LIST": str(path_list),
        "GITHUB_OUTPUT": str(github_output),
        "GITHUB_STEP_SUMMARY": str(summary_path),
        "RUNNER_TEMP": str(tmp_path),
        "SOURCE": "./package with spaces",
        "VALE": "false",
        "ANNOTATE": "false",
        "SARIF": "false",
        "FAIL_ON_FINDINGS": "true",
    }

    def fake_run(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        assert "docs/release notes.md" in command
        assert "./package with spaces" in command
        output = kwargs["stdout"]
        assert hasattr(output, "write")
        output.write(json.dumps(report))
        return CompletedProcess(command, 1, stderr="")

    with patch.dict(os.environ, environment, clear=False), patch(
        "scripts.action_entry.subprocess.run", side_effect=fake_run
    ):
        status = action_entry.lint()

    assert status == 1
    output = github_output.read_text()
    assert "score=91.5" in output
    assert "findings=1" in output
    assert "passed=true" in output
    assert "json=" in output
    assert "sarif=" in output
    assert "score 91.5/100" in summary_path.read_text()
