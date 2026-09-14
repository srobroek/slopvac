"""Global comment-mode routing and Vale scope behavior."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from slopvac.cli import main
from slopvac.compile_vale import canonical_source_language, source_scopes
from slopvac.config import Config, Mode, Override
from slopvac.pipeline import EXIT_ERROR

VALE = shutil.which("vale")


def _write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_override_cannot_select_a_comment_mode():
    with pytest.raises(ValidationError):
        Override.model_validate({"files": ["src/**"], "mode": "code-comments"})


def test_default_mode_keeps_toml_in_prose_and_projects_comments(tmp_path):
    path = _write(tmp_path, "settings.toml", "# The very important setting.\nvalue = 1\n")
    result = CliRunner().invoke(main, ["lint", str(path), "--no-vale", "--format", "json"])
    assert result.exit_code != EXIT_ERROR, result.output
    report = json.loads(result.output)
    assert report["documents"][0]["path"].endswith("settings.toml")
    assert report["documents"][0]["words"] > 0


def test_cli_mode_and_explain_are_global(tmp_path):
    py = _write(tmp_path, "src/a.py", "# Very important comment\nvalue = 1\n")
    js = _write(tmp_path, "src/b.js", "// Very important comment\nconst value = 1;\n")
    result = CliRunner().invoke(
        main, ["lint", str(py), str(js), "--mode", "code-comments", "--no-vale", "--format", "json"]
    )
    assert result.exit_code != EXIT_ERROR, result.output
    report = json.loads(result.output)
    assert {Path(d["path"]).suffix for d in report["documents"]} == {".py", ".js"}

    explained = CliRunner().invoke(main, ["lint", str(py), "--mode", "doc-comments", "--explain-config"])
    assert explained.exit_code == 0, explained.output
    assert "doc-comments" in explained.output


def test_code_directory_selects_supported_source_and_rejects_explicit_unknown(tmp_path):
    _write(tmp_path, "src/a.py", "# ordinary comment\n")
    _write(tmp_path, "src/readme.md", "ordinary prose\n")
    directory = CliRunner().invoke(
        main, ["lint", str(tmp_path / "src"), "--mode", "code-comments", "--no-vale", "--format", "json"]
    )
    assert directory.exit_code != EXIT_ERROR, directory.output
    assert [Path(d["path"]).suffix for d in json.loads(directory.output)["documents"]] == [".py"]

    unknown = _write(tmp_path, "notes.yaml", "key: value\n")
    explicit = CliRunner().invoke(main, ["lint", str(unknown), "--mode", "code-comments", "--no-vale"])
    assert explicit.exit_code == EXIT_ERROR
    assert "unsupported source language" in explicit.output


def test_source_mapping_and_unsuffixed_doc_scopes():
    assert canonical_source_language("x.py") == ("python", ".py")
    assert canonical_source_language("Gemfile") == ("ruby", "gemfile")
    assert source_scopes(Mode.CODE_COMMENTS, ".ts") == (
        "text.comment.line.ts", "text.comment.block.ts"
    )
    assert source_scopes(Mode.DOC_COMMENTS, ".ts") == (
        "text.comment.doc.line", "text.comment.doc.block"
    )


@pytest.mark.skipif(VALE is None, reason="vale is not on PATH")
def test_real_vale_sees_comment_scope_but_not_code_or_string(tmp_path):
    """The shipped compiler must produce an executable Vale config, not only YAML."""
    source = _write(
        tmp_path,
        "src/a.py",
        "# very important comment\nvalue = 'very important string'\n",
    )
    result = CliRunner().invoke(
        main,
        ["lint", str(source), "--mode", "code-comments", "--format", "json"],
    )
    assert result.exit_code in (0, 1), result.output
    payload = json.loads(result.output)
    findings = payload["documents"][0]["findings"]
    assert findings, "real Vale did not report the comment fixture"
    assert all(f["line"] == 1 for f in findings)


def test_disabled_or_custom_vale_and_excluded_routing(tmp_path):
    config = _write(
        tmp_path,
        "slopvac.toml",
        'exclude = ["vendor/**"]\n[vale]\nenabled = false\n',
    )
    source = _write(tmp_path, "src/a.py", "# comment\n")
    vendor = _write(tmp_path, "vendor/b.py", "# comment\n")
    result = CliRunner().invoke(
        main,
        ["lint", str(tmp_path), "--config", str(config), "--mode", "code-comments", "--format", "json"],
    )
    assert result.exit_code != EXIT_ERROR, result.output
    paths = {Path(d["path"]).name for d in json.loads(result.output)["documents"]}
    assert "a.py" in paths and "b.py" not in paths

    if VALE:
        custom = _write(tmp_path, "custom.toml", f'[vale]\nenabled = true\nbinary = "{VALE}"\n')
        custom_run = CliRunner().invoke(
            main,
            ["lint", str(source), "--config", str(custom), "--mode", "code-comments", "--format", "json"],
        )
        assert custom_run.exit_code in (0, 1), custom_run.output
