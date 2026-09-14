from pathlib import Path

import pytest

from slopvac.compile_vale import compile_ruleset, source_scopes
from slopvac.config import Config, Mode, load_config, resolve_for
from slopvac.rules import load_ruleset


def test_mode_is_orthogonal_and_override_wins(tmp_path: Path):
    config_path = tmp_path / "slopvac.toml"
    config_path.write_text(
        'mode = "prose"\n[[overrides]]\nfiles = ["src/**/*.py"]\nmode = "code-comments"\n',
        encoding="utf-8",
    )
    config = load_config(config_path)
    resolved = resolve_for(config, tmp_path / "src" / "x.py")
    assert resolved.profile.value == "normal"
    assert resolved.mode is Mode.CODE_COMMENTS


def test_source_scope_names_are_distinct():
    assert source_scopes(Mode.CODE_COMMENTS, ".py") == (
        "text.comment.line.py", "text.comment.block.py"
    )
    assert source_scopes(Mode.DOC_COMMENTS, ".rs") == (
        "text.comment.doc.line.rs", "text.comment.doc.block.rs"
    )


def test_unknown_source_extension_fails(tmp_path: Path):
    from slopvac.compile_vale import canonical_source_language

    with pytest.raises(ValueError, match="unsupported source language"):
        canonical_source_language(tmp_path / "config.yaml")
