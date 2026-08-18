"""Config resolution: the cascade, and what makes it legible.

The precedence rule here is FILE ORDER, which is the one thing about this schema a
reader is most likely to guess wrong -- the broader glob wins if it comes later.
These tests pin that behaviour down and pin down the two things that keep it from
being a trap: a duplicate scope is refused, and every surviving setting records
which block set it.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from slopvac.config import (
    Config,
    Override,
    Profile,
    Severity,
    Thresholds,
    resolve_for,
)


def _config(**kwargs) -> Config:
    config = Config.model_validate(kwargs)
    # `root` is set by the loader, not the file, so a hand-built Config needs it
    # before `resolve_for` can make a path relative.
    object.__setattr__(config, "root", pytest.importorskip("pathlib").Path("/repo"))
    return config


def _resolve(config: Config, name: str):
    from pathlib import Path

    return resolve_for(config, Path("/repo") / name)


# --- the cascade --------------------------------------------------------------


def test_a_later_broader_glob_beats_an_earlier_narrower_one():
    """FILE ORDER, not specificity and not strictest-wins.

    This is the case that surprises people: `x.*` after `x.md` wins for `x.md`.
    Specificity ranking was rejected because there is no ordering on globs a reader
    can predict -- `docs/**` against `**/*.md` is differently specific, not more or
    less -- and strictest-wins was rejected because it makes RELAXING a subtree
    impossible, which is the main reason overrides exist.
    """
    config = _config(
        profile="normal",
        overrides=[
            {"files": ["x.md"], "profile": "strict"},
            {"files": ["x.*"], "profile": "relaxed"},
        ],
    )
    assert _resolve(config, "x.md").profile is Profile.RELAXED


def test_reordering_the_blocks_reverses_the_result():
    """The corollary, stated as a test so nobody mistakes it for an accident."""
    config = _config(
        profile="normal",
        overrides=[
            {"files": ["x.*"], "profile": "relaxed"},
            {"files": ["x.md"], "profile": "strict"},
        ],
    )
    assert _resolve(config, "x.md").profile is Profile.STRICT


def test_an_override_can_relax_as_well_as_tighten():
    """Under strictest-wins a vendored subtree could never be dialled down."""
    config = _config(
        profile="strict",
        categories={"prose-craft": {"severity": "error"}},
        overrides=[{"files": ["vendor/**"], "categories": {"prose-craft": "off"}}],
    )
    assert _resolve(config, "vendor/a.md").categories["prose-craft"].severity is Severity.OFF
    assert _resolve(config, "a.md").categories["prose-craft"].severity is Severity.ERROR


def test_the_merge_is_per_field_not_per_block():
    """A block that sets one field leaves the rest of the earlier block standing."""
    config = _config(
        overrides=[
            {"files": ["docs/**"], "profile": "strict", "thresholds": {"max_errors": 3}},
            {"files": ["docs/api/**"], "profile": "relaxed"},
        ],
    )
    resolved = _resolve(config, "docs/api/a.md")
    assert resolved.profile is Profile.RELAXED
    # `max_errors` survives: the second block never mentioned it.
    assert resolved.thresholds.max_errors == 3


# --- duplicate scopes ---------------------------------------------------------


def test_two_blocks_with_the_same_scope_are_refused():
    """TOML cannot catch this, because `[[overrides]]` is an array of tables.

    Duplicating a scope is never what an author means: it reads as two independent
    decisions and resolves as one, so a setting present in both blocks silently
    loses while a setting present in only the first survives.
    """
    with pytest.raises(ValidationError, match="repeats the scope"):
        Config.model_validate(
            {
                "overrides": [
                    {"files": ["docs/**"], "profile": "strict"},
                    {"files": ["docs/**"], "profile": "relaxed"},
                ]
            }
        )


def test_the_scope_is_compared_as_a_set():
    """Reordering the patterns inside a block does not make it a new scope."""
    with pytest.raises(ValidationError, match="repeats the scope"):
        Config.model_validate(
            {
                "overrides": [
                    {"files": ["docs/**", "!docs/generated/**"]},
                    {"files": ["!docs/generated/**", "docs/**"]},
                ]
            }
        )


def test_overlapping_but_different_globs_stay_legal():
    """Overlap is the POINT. Only an identical scope is the mistake."""
    config = _config(
        overrides=[
            {"files": ["docs/**"], "profile": "strict"},
            {"files": ["**/*.md"], "profile": "relaxed"},
        ]
    )
    assert len(config.overrides) == 2


def test_a_multi_pattern_scope_is_why_this_is_a_list():
    """One scope, two patterns, one of them a negation.

    A table keyed by glob would reject duplicates for free but could not express
    this: it would force one scope into two blocks whose settings must then be kept
    in agreement by hand.
    """
    override = Override.model_validate(
        {"files": ["docs/**", "!docs/generated/**"], "profile": "strict"}
    )
    assert override.matches("docs/guide.md")
    assert not override.matches("docs/generated/api.md")


# --- provenance ---------------------------------------------------------------


def test_provenance_names_the_block_that_won():
    """What makes file order legible instead of a guessing game.

    Without this, "why is this rule still on" is an inference over every block in
    the file, and the answer is counter-intuitive whenever globs overlap.
    """
    config = _config(
        overrides=[
            {"files": ["x.md"], "profile": "strict"},
            {"files": ["x.*"], "profile": "relaxed"},
        ],
    )
    provenance = _resolve(config, "x.md").provenance
    assert provenance["profile"] == "overrides[1] (x.*)"


def test_provenance_records_the_layer_for_each_setting_separately():
    """The winner is per setting, so the report has to be per setting too."""
    config = _config(
        rules={"prose-format.no-unicode-dash": "error"},
        overrides=[{"files": ["x.md"], "categories": {"prose-craft": "off"}}],
    )
    provenance = _resolve(config, "x.md").provenance
    assert provenance["rules.prose-format.no-unicode-dash"] == "config"
    assert provenance["categories.prose-craft"] == "overrides[0] (x.md)"


def test_an_untouched_profile_default_is_not_reported():
    """Only settings some layer actually touched.

    The ~30 untouched profile defaults would bury the handful a reader is looking
    for, which is the failure this report exists to avoid.
    """
    provenance = _resolve(_config(profile="normal"), "x.md").provenance
    assert set(provenance) == {"profile"}
    assert provenance["profile"] == "profile default (normal)"


def test_thresholds_are_credited_to_the_profile_when_the_file_is_silent():
    """`Thresholds` has non-None field defaults.

    A truthiness test therefore credited the config file for thresholds it never
    mentioned and the profile actually set.
    """
    assert "thresholds" not in _resolve(_config(profile="strict"), "x.md").provenance

    explicit = _config(profile="strict", thresholds={"max_errors": 9})
    assert _resolve(explicit, "x.md").provenance["thresholds"] == "config"


def test_a_default_thresholds_table_written_out_is_still_the_profile():
    """Writing the default explicitly changes nothing, so it credits nothing."""
    written = _config(thresholds=Thresholds().model_dump(exclude_none=True))
    assert "thresholds" not in _resolve(written, "x.md").provenance
