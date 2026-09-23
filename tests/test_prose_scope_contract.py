"""Scope guidance remains available after removing the skill distribution."""
from slopvac.agent_context import OVERVIEW


def test_cli_guidance_preserves_code_change_scope() -> None:
    assert "directly explains or specifies the changed" in OVERVIEW
    assert "unrelated same-file comments and documentation elsewhere unchanged" in OVERVIEW
    assert "explicitly requested prose edit is in scope" in OVERVIEW
    assert "stale comment about changed" in OVERVIEW
