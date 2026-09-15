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

    with (
        patch.dict(os.environ, environment, clear=False),
        patch("scripts.action_entry.subprocess.run", side_effect=fake_run),
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


def test_changed_only_without_pull_request_base_fails_closed(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("CHANGED_ONLY", "true")
    monkeypatch.setenv("INPUT_PATHS", ".")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.delenv("BASE_SHA", raising=False)
    assert action_entry.resolve_targets() == 1
    assert "requires" in capsys.readouterr().out
    assert not (tmp_path / "slopvac-paths").exists()


def test_changed_only_resolves_exact_base_and_prose_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("CHANGED_ONLY", "true")
    monkeypatch.setenv("INPUT_PATHS", "ignored.md")
    monkeypatch.setenv("BASE_SHA", "abc123")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["git", "cat-file", "-e"]:
            return CompletedProcess(command, 0, stdout="", stderr="")
        return CompletedProcess(
            command, 0, stdout=b"docs/release notes.md\0", stderr=b""
        )

    with patch("scripts.action_entry.subprocess.run", side_effect=fake_run):
        assert action_entry.resolve_targets() == 0

    assert calls[0] == ["git", "cat-file", "-e", "abc123^{commit}"]
    assert "abc123...HEAD" in calls[1]
    assert (
        calls[1][-7:]
        == ["*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.html", "--"]
        or "--" in calls[1]
    )
    assert action_entry._read_paths(tmp_path / "slopvac-paths") == [
        "docs/release notes.md"
    ]


def test_command_passes_exact_diff_base_and_path_argv(monkeypatch):
    monkeypatch.setenv("CHANGED_ONLY", "true")
    monkeypatch.setenv("BASE_SHA", "deadbeef")
    monkeypatch.setenv("VALE", "false")
    command = action_entry._command(["docs/release notes.md"])
    assert command[-5:] == [
        "--diff-base",
        "deadbeef",
        "--format",
        "json",
        "docs/release notes.md",
    ]


def test_changed_only_missing_merge_base_fails_closed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHANGED_ONLY", "true")
    monkeypatch.setenv("INPUT_PATHS", ".")
    monkeypatch.setenv("BASE_SHA", "missing")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))

    def missing_base(command, **kwargs):
        return CompletedProcess(command, 128, stdout=b"", stderr=b"missing object")

    with patch("scripts.action_entry.subprocess.run", side_effect=missing_base):
        assert action_entry.resolve_targets() == 1
    assert "merge base" in capsys.readouterr().out
