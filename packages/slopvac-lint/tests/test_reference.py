"""Generated rule-reference contract."""

from __future__ import annotations

from slopvac.model import Category, Example, Provenance, Rule, RuleKind
from slopvac.reference import render_reference
from slopvac.rules import RuleSet, load_ruleset


def test_judgement_rules_render_apart_from_checked_rules():
    """A reader must never take a judgement rule for one that gates the build."""
    ruleset = load_ruleset()
    rendered = render_reference(ruleset)
    checked_part, judgement_part = rendered.split("\n## Judgement rules\n")

    assert f"**{len(ruleset.rules)} checked rules**" in checked_part
    assert f"**{len(ruleset.judgement_rules)} judgement rules**" in checked_part
    for rule in ruleset.judgement_rules:
        heading = f"#### `{rule.qualified_id}`"
        assert heading in judgement_part
        assert heading not in checked_part
    for rule in ruleset.rules:
        assert f"#### `{rule.qualified_id}`" not in judgement_part


def test_judgement_example_without_good_renders_as_deletion():
    """A judgement fix is often deletion, so an example may omit `good`."""
    rule = Rule(
        id="omit-good",
        name="Delete the filler",
        kind=RuleKind.JUDGEMENT,
        message="delete it",
        judgement_question="Does this sentence add a fact?",
        examples=[Example(bad="In conclusion, the cache is cold.")],
        provenance=Provenance(source="test"),
    )
    object.__setattr__(rule, "category", "probe")
    ruleset = RuleSet(
        categories={
            "probe": Category(
                id="probe", title="Probe", description="Fixture.", rules=[rule]
            )
        }
    )
    rendered = render_reference(ruleset)
    assert "In conclusion, the cache is cold." in rendered
    assert "*(delete it)*" in rendered
    assert "Does this sentence add a fact?" in rendered


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
