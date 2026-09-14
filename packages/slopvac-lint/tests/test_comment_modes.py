from pathlib import Path
import shutil

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.compile_vale import compile_ruleset, source_scopes
from slopvac.config import Config, Mode, Severity, load_config, resolve_for
from slopvac.pipeline import _collect_paths_modes, _group_inputs_modes
from slopvac.rules import load_ruleset
from slopvac.toml_comments import comment_projection
from slopvac.vale import run_compiled_vale


VALE = shutil.which("vale")
requires_vale = pytest.mark.skipif(VALE is None, reason="requires the real Vale binary")


def _ruleset(tmp_path: Path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "comments.yml").write_text(
        """id: comments
title: Comment rules
description: Rules used by comment-mode integration tests.
rules:
  - id: forbidden-word
    name: Replace forbidden word
    kind: tokens
    tokens: [forbidden]
    message: Use a different word.
    severity: error
    examples:
      - bad: forbidden
        good: allowed
    provenance:
      source: test
""",
        encoding="utf-8",
    )
    return load_ruleset([rules_dir])


def _compile(tmp_path: Path, mode: Mode, extension: str, language: str):
    source = tmp_path / f"sample{extension}"
    config = Config(mode=mode)
    resolved = resolve_for(config, source)
    compiled = compile_ruleset(
        _ruleset(tmp_path),
        resolved,
        outdir=tmp_path / "compiled",
        binary=VALE or "vale",
        validate=True,
        source_language=language,
        source_extension=extension,
    )
    severities = {check: Severity.ERROR for check in compiled.vale_rules}
    categories = {check: "comments" for check in compiled.vale_rules}
    return source, compiled, severities, categories


def test_source_scope_names_keep_doc_comments_language_independent():
    assert source_scopes(Mode.CODE_COMMENTS, ".py") == (
        "text.comment.line.py",
        "text.comment.block.py",
    )
    assert source_scopes(Mode.DOC_COMMENTS, ".rs") == (
        "text.comment.doc.line",
        "text.comment.doc.block",
    )


def test_default_prose_mode_excludes_source_files(tmp_path: Path):
    source = tmp_path / "sample.py"
    source.write_text("# forbidden\n", encoding="utf-8")
    assert _collect_paths_modes((str(source),), Config()) == []


@requires_vale
def test_yaml_rule_finds_ordinary_comments_but_not_strings_or_code(tmp_path: Path):
    source, compiled, severities, categories = _compile(
        tmp_path, Mode.CODE_COMMENTS, ".py", "python"
    )
    source.write_text(
        "# forbidden\nvalue = 'forbidden'\ndef forbidden():\n    return 'forbidden'\n",
        encoding="utf-8",
    )
    result = run_compiled_vale(
        [source], compiled, severities, categories, binary=VALE or "vale"
    )
    assert not result.unchecked
    assert len(result.by_path[str(source)]) == 1
    finding = result.by_path[str(source)][0]
    assert finding.path == str(source)
    assert finding.line == 1
    assert finding.column >= 1
    assert finding.end_column > finding.column


@requires_vale
def test_yaml_rule_finds_doc_comments_but_not_ordinary_comments_or_strings(tmp_path: Path):
    source, compiled, severities, categories = _compile(
        tmp_path, Mode.DOC_COMMENTS, ".py", "python"
    )
    source.write_text(
        '"""forbidden"""\nvalue = "forbidden"\n# forbidden\n',
        encoding="utf-8",
    )
    result = run_compiled_vale(
        [source], compiled, severities, categories, binary=VALE or "vale"
    )
    assert not result.unchecked
    assert len(result.by_path[str(source)]) == 1
    finding = result.by_path[str(source)][0]
    assert finding.path == str(source)
    assert finding.line == 1
    assert finding.column >= 1


def test_mixed_source_extensions_are_compiled_in_homogeneous_groups(tmp_path: Path):
    py = tmp_path / "sample.py"
    rs = tmp_path / "sample.rs"
    py.write_text("# clean\n", encoding="utf-8")
    rs.write_text("// clean\n", encoding="utf-8")
    config = Config(mode=Mode.CODE_COMMENTS)
    _, groups = _group_inputs_modes([py, rs], config, _ruleset(tmp_path))
    assert len(groups) == 2
    assert sorted(len(paths) for paths in groups.values()) == [1, 1]


def test_toml_comments_remain_prose_and_are_projected_for_vale(tmp_path: Path):
    toml = tmp_path / "settings.toml"
    original = "# forbidden\n[tool]\nvalue = 'forbidden'\n"
    toml.write_text(original, encoding="utf-8")
    assert _collect_paths_modes((str(toml),), Config()) == [toml]
    projected = comment_projection(original)
    assert "forbidden" in projected
    assert "value = 'forbidden'" not in projected


def test_configured_and_yaml_modes_are_explained(tmp_path: Path):
    source = tmp_path / "src" / "sample.py"
    source.parent.mkdir()
    source.write_text("# clean\n", encoding="utf-8")
    config_path = tmp_path / "slopvac.toml"
    config_path.write_text(
        'mode = "prose"\n\n[[overrides]]\nfiles = ["src/**/*.py"]\nmode = "doc-comments"\n',
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert resolve_for(config, source).mode is Mode.DOC_COMMENTS
    runner = CliRunner()
    result = runner.invoke(
        main, ["lint", str(source), "--config", str(config_path), "--explain-config"]
    )
    assert result.exit_code == 0, result.output
    assert "mode: doc-comments" in result.output


def test_mode_override_resolution_is_orthogonal_to_profile(tmp_path: Path):
    config_path = tmp_path / "slopvac.toml"
    config_path.write_text(
        'profile = "relaxed"\nmode = "prose"\n[[overrides]]\n'
        'files = ["src/**/*.rs"]\nmode = "code-comments"\n',
        encoding="utf-8",
    )
    config = load_config(config_path)
    resolved = resolve_for(config, tmp_path / "src" / "x.rs")
    assert resolved.profile.value == "relaxed"
    assert resolved.mode is Mode.CODE_COMMENTS
