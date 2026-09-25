"""Generated rule-reference contract."""

from __future__ import annotations

from slopvac.reference import render_reference
from slopvac.rules import load_ruleset


def test_profile_default_off_is_reported_apart_from_the_tier_row():
    """The two answer different questions. An `excluded` tier is final; a profile
    default is a switch. A reader who reads one as the other concludes a rule they
    can enable is unreachable, so the document says which it is."""
    rendered = render_reference(load_ruleset())

    section = rendered.split("#### `ste-practices.unclear-pronoun`")[1].split("####")[0]
    assert "**Off by profile default.** strict, normal, relaxed" in section
    assert '[rules."ste-practices.unclear-pronoun"]' in section
    assert "**strict / normal / relaxed.** advisory / advisory / advisory" in section
    assert "turns on that rule and no other" in section, (
        "a rule entry is a top-level setting; the document must not promise it is "
        "scoped to one profile"
    )

    kept_on = rendered.split("#### `ste-practices.phrasal-verb`")[1].split("####")[0]
    assert "Off by profile default" not in kept_on, (
        "the fact is emitted only where a profile actually sets the rule off"
    )
