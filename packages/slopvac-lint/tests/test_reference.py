"""Reference rendering.

A custom judgement rule may omit `good` (the fix is deletion). The renderer
must treat that as empty text, not crash on `.strip()`.
"""

from __future__ import annotations

from slopvac.model import Category, Example, Provenance, Rule, RuleKind, Severity
from slopvac.reference import render_reference
from slopvac.rules import RuleSet, load_ruleset


def test_judgement_example_without_good_renders():
    rule = Rule(
        id="omit-good",
        name="Delete the filler",
        kind=RuleKind.JUDGEMENT,
        message="delete it",
        judgement_question="Does this sentence add a fact?",
        judgement={"dims": {"fit": "ask", "harm": "ask", "repair": "ask", "warrant": "ask"}, "evidence": {"min_arity": 1, "roles": ["defect"]}, "warrant_min": 2, "protects": ["normative_obligation"], "judgement_ceiling": "suggestion"},
        examples=[Example(bad="In conclusion, the cache is cold.")],
        provenance=Provenance(source="test"),
    )
    object.__setattr__(rule, "category", "probe")
    ruleset = RuleSet(
        categories={
            "probe": Category(
                id="probe",
                title="Probe",
                description="Fixture category.",
                rules=[rule],
            )
        }
    )
    rendered = render_reference(ruleset)
    assert "omit-good" in rendered
    assert "In conclusion, the cache is cold." in rendered
    assert "*(delete it)*" in rendered
    assert rule.severity is Severity.SUGGESTION


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
