"""Global code-comment mode routing and Vale scope behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from slopvac.cli import main
from slopvac.compile_vale import (
    _render_ini,
    canonical_source_language,
    compile_ruleset,
    source_scopes,
)
from slopvac.config import Config, Mode, Override, resolve_for
from slopvac.pipeline import EXIT_ERROR, _expand_paths
from slopvac.rules import load_ruleset


def _write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _json_run(*args: str) -> tuple[int, dict]:
    result = CliRunner().invoke(main, ["lint", *args, "--format", "json"])
    assert result.output, result.exception or "the CLI returned no report"
    return result.exit_code, json.loads(result.output)


def test_only_global_code_comments_mode_is_configurable():
    assert set(Mode) == {Mode.PROSE, Mode.CODE_COMMENTS}
    assert Config().mode is Mode.PROSE
    with pytest.raises(ValidationError):
        Override.model_validate({"files": ["src/**"], "mode": "code-comments"})
    with pytest.raises(ValidationError):
        Config.model_validate({"mode": "doc-comments"})


def test_source_mapping_uses_extension_scopes():
    assert canonical_source_language("x.py") == ("python", ".py")
    assert canonical_source_language("x.rs") == ("rust", ".rs")
    assert source_scopes(Mode.CODE_COMMENTS, ".py") == (
        "text.comment.line.py",
        "text.comment.block.py",
    )
    with pytest.raises(ValueError, match="unsupported source language"):
        canonical_source_language("notes.yaml")


def test_default_prose_mode_keeps_toml_projection(tmp_path):
    path = _write(tmp_path, "settings.toml", "# robust setting\nvalue = 1\n")
    exit_code, report = _json_run(str(path), "--no-vale")
    assert exit_code == EXIT_ERROR
    document = report["documents"][0]
    assert document["path"].endswith("settings.toml")
    assert document["words"] > 0


def test_unsupported_file_in_directory_is_reported_as_skip(tmp_path):
    _write(tmp_path, "source.py", "# robust comment\n")
    _write(tmp_path, "notes.yaml", "robust: value\n")
    exit_code, report = _json_run(str(tmp_path), "--mode", "code-comments", "--no-vale")
    assert exit_code == EXIT_ERROR
    assert len(report["documents"]) == 1
    notes = "\n".join(report["documents"][0]["unchecked"])
    assert "notes.yaml" in notes
    assert "unsupported source language" in notes


def test_explicit_unsupported_file_is_an_error(tmp_path):
    unknown = _write(tmp_path, "notes.yaml", "robust: value\n")
    result = CliRunner().invoke(
        main, ["lint", str(unknown), "--mode", "code-comments", "--no-vale"]
    )
    assert result.exit_code == EXIT_ERROR
    assert "unsupported source language" in result.output


def test_prose_directory_does_not_scan_code_files(tmp_path):
    _write(tmp_path, "source.py", "# robust comment\n")
    _write(tmp_path, "README.md", "Robust prose.\n")
    exit_code, report = _json_run(str(tmp_path), "--no-vale")
    assert exit_code == EXIT_ERROR
    assert {Path(doc["path"]).suffix for doc in report["documents"]} == {".md"}


def test_comments_alias_selects_code_mode(tmp_path):
    source = _write(tmp_path, "source.py", "# robust comment\n")
    exit_code, report = _json_run(str(source), "--comments", "--no-vale")
    assert exit_code == EXIT_ERROR
    assert report["documents"][0]["path"].endswith("source.py")


def test_no_vale_reports_comment_excluded_rule_ids(tmp_path):
    source = _write(tmp_path, "src/a.py", "# robust comment\n")
    exit_code, report = _json_run(
        str(source), "--mode", "code-comments", "--no-vale"
    )
    assert exit_code == EXIT_ERROR
    unchecked = "\n".join(
        note for document in report["documents"] for note in document["unchecked"]
    )
    assert "active rule(s) are not safe for code-comment scopes" in unchecked


def test_compiled_code_mode_runs_comment_scoped_rules(tmp_path):
    source = _write(tmp_path, "source.py", "# robust comment\n")
    config = Config(root=tmp_path, mode=Mode.CODE_COMMENTS)
    resolved = config.model_copy(update={"root": tmp_path, "mode": Mode.CODE_COMMENTS})
    result = compile_ruleset(
        load_ruleset(),
        resolve_for(resolved, source),
        outdir=tmp_path / "compiled",
        validate=False,
        source_language="python",
        source_extension=".py",
    )
    assert "[*.py]" in result.config_path.read_text(encoding="utf-8")
    payloads = "\n".join(
        path.read_text(encoding="utf-8")
        for path in result.outdir.rglob("*.yml")
    )
    assert "text.comment.line.py" in payloads
    assert "text.comment.block.py" in payloads


def test_extensionless_source_uses_exact_vale_selector():
    rendered = _render_ini([], {}, mode=Mode.CODE_COMMENTS, extension="gemfile")
    assert "[Gemfile]" in rendered
    assert "[*.gemfile]" not in rendered


def test_explicit_uppercase_extension_is_collected(tmp_path):
    source = _write(tmp_path, "EXAMPLE.PY", "# robust comment\n")
    assert _expand_paths((str(source),), comments=True) == [source]
