from __future__ import annotations

from pathlib import Path

from slopvac.pipeline import _comment_projection


def test_projection_preserves_full_and_trailing_toml_comments():
    text = "[tool]\nvalue = 1 # trailing\n# full\n"
    projected = _comment_projection(Path("settings.toml"), text)
    assert projected.splitlines()[1].endswith("# trailing")
    assert projected.splitlines()[2].endswith("# full")
    assert projected.splitlines()[0].strip() == ""


def test_projection_masks_hashes_in_string_values():
    text = 'basic = "#"\nliteral = \'#\'\ninline = {x = "#"} # seen\n'
    projected = _comment_projection(Path("settings.toml"), text)
    assert '"#"' not in projected
    assert projected.splitlines()[-1].endswith("# seen")


def test_projection_preserves_newlines_and_columns():
    text = 'key = "# hidden" # visible\r\n# full\r\n'
    projected = _comment_projection(Path("settings.toml"), text)
    assert len(projected) == len(text)
    assert projected.count("\n") == text.count("\n")
    assert projected.splitlines()[0].index("#") == text.splitlines()[0].index("# visible")
    assert projected.splitlines()[0].endswith("# visible")


def test_incomplete_strings_do_not_invent_comments():
    assert _comment_projection(
        Path("settings.toml"), 'broken = "unterminated # not comment'
    ).strip() == ""
    assert _comment_projection(
        Path("settings.toml"), "broken = 'unterminated # not comment"
    ).strip() == ""
