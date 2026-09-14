"""Global code-comment mode routing and Vale scope behavior."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from slopvac.cli import main
from slopvac.compile_vale import _render_ini, canonical_source_language, source_scopes
from slopvac.config import Config, Mode, Override, ValePatch
from slopvac.pipeline import EXIT_ERROR, group_inputs
from slopvac.rules import load_ruleset

VALE = shutil.which("vale")


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


def test_code_directory_selects_supported_sources_and_excludes_paths(tmp_path):
    _write(tmp_path, "src/a.py", "# robust comment\n")
    _write(tmp_path, "src/b.rs", "// robust comment\n")
    _write(tmp_path, "src/readme.md", "robust prose\n")
    _write(tmp_path, "src/notes.yaml", "robust: value\n")
    _write(tmp_path, "vendor/ignored.py", "# robust comment\n")
    config = _write(tmp_path, "slopvac.toml", 'exclude = ["vendor/**"]\n')

    exit_code, report = _json_run(
        str(tmp_path / "src"),
        "--mode",
        "code-comments",
        "--config",
        str(config),
        "--no-vale",
    )
    assert exit_code == EXIT_ERROR
    paths = {Path(document["path"]).suffix for document in report["documents"]}
    assert paths == {".py", ".rs"}

    unknown = _write(tmp_path, "notes.yaml", "robust: value\n")
    result = CliRunner().invoke(
        main,
        ["lint", str(unknown), "--mode", "code-comments", "--no-vale"],
    )
    assert result.exit_code == EXIT_ERROR
    assert "unsupported source language" in result.output


def test_disabled_vale_reports_unchecked(tmp_path):
    config = _write(tmp_path, "slopvac.toml", "[vale]\nenabled = false\n")
    source = _write(tmp_path, "src/a.py", "# robust comment\n")
    exit_code, report = _json_run(
        str(source), "--mode", "code-comments", "--config", str(config)
    )
    assert exit_code == EXIT_ERROR
    assert report["documents"][0]["unchecked"]


@pytest.mark.skipif(VALE is None, reason="vale is not on PATH")
def test_real_vale_checks_comments_and_doc_comments_not_strings(tmp_path):
    python = _write(
        tmp_path,
        "src/comments.py",
        "# robust ordinary comment\nvalue = 'robust string'\nrobust_name = 1\n",
    )
    rust = _write(
        tmp_path,
        "src/comments.rs",
        'fn main() { let robust_name = "robust string"; } // robust ordinary\n'
        "/// robust documentation comment\n"
        "// robust ordinary comment\n",
    )

    py_exit, py_report = _json_run(str(python), "--mode", "code-comments")
    assert py_exit in (0, 1)
    py_findings = py_report["documents"][0]["findings"]
    assert py_findings
    assert all(finding["path"].endswith("comments.py") for finding in py_findings)
    assert all(finding["line"] == 1 for finding in py_findings)
    assert all(finding["column"] > 0 for finding in py_findings)

    rs_exit, rs_report = _json_run(str(rust), "--mode", "code-comments")
    assert rs_exit in (0, 1)
    rs_findings = rs_report["documents"][0]["findings"]
    assert rs_findings
    lines = {finding["line"] for finding in rs_findings}
    assert 2 in lines
    assert 3 in lines
    assert all(finding["path"].endswith("comments.rs") for finding in rs_findings)


def test_doc_only_mode_is_removed(tmp_path):
    source = _write(tmp_path, "src/a.py", "# robust comment\n")
    result = CliRunner().invoke(main, ["lint", str(source), "--mode", "doc-comments"])
    assert result.exit_code == EXIT_ERROR
    assert "Invalid value for '--mode'" in result.output

def test_code_comments_rejects_top_level_vale_customization(tmp_path):
    source = _write(tmp_path, "src/a.py", "# robust comment\n")
    _write(tmp_path, "custom.ini", "StylesPath = custom-styles\n")
    _write(
        tmp_path,
        "slopvac.toml",
        '[vale]\nconfig = "custom.ini"\nstyles = ["custom"]\n',
    )

    result = CliRunner().invoke(main, ["lint", str(source), "--mode", "code-comments"])

    assert result.exit_code == EXIT_ERROR
    assert "custom vale.config is not supported" in result.output
    assert "custom vale.styles are not supported" in result.output


def test_code_comments_rejects_per_file_vale_customization(tmp_path):
    clean = _write(tmp_path, "src/clean.py", "# robust comment\n")
    custom = _write(tmp_path, "src/custom.py", "# robust comment\n")
    _write(
        tmp_path,
        "slopvac.toml",
        '[[overrides]]\nfiles = ["src/custom.py"]\n'
        '[overrides.vale]\nconfig = "custom.ini"\nstyles = ["custom"]\n',
    )

    result = CliRunner().invoke(
        main,
        ["lint", str(clean), str(custom), "--mode", "code-comments"],
    )

    assert result.exit_code == EXIT_ERROR
    assert str(custom) in result.output
    assert "custom vale.config is not supported" in result.output
    assert "custom vale.styles are not supported" in result.output


def test_grouping_separates_vale_enabled_overrides_in_both_orders(tmp_path, monkeypatch):
    from slopvac import pipeline

    monkeypatch.setattr(pipeline, "vale_version", lambda _binary: (3, 0))
    enabled = _write(tmp_path, "enabled.py", "# robust comment\n")
    disabled = _write(tmp_path, "disabled.py", "# robust comment\n")
    config = Config(
        root=tmp_path,
        overrides=[Override(files=["disabled.py"], vale=ValePatch(enabled=False))],
    )
    ruleset = load_ruleset()

    for paths in ((enabled, disabled), (disabled, enabled)):
        _vocabularies, groups = group_inputs(list(paths), config, ruleset)
        assert len(groups) == 2
        assert {tuple(group) for group in groups.values()} == {
            (enabled,),
            (disabled,),
        }


def test_extensionless_source_uses_exact_vale_selector():
    rendered = _render_ini([], {}, mode=Mode.CODE_COMMENTS, extension="gemfile")
    assert "[Gemfile]" in rendered
    assert "[*.gemfile]" not in rendered


def test_explicit_uppercase_extension_is_collected(tmp_path):
    from slopvac.pipeline import collect_source_paths

    source = _write(tmp_path, "EXAMPLE.PY", "# robust comment\n")
    assert collect_source_paths((str(source),), Config(root=tmp_path)) == [source]
