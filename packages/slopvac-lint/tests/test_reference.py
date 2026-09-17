"""Reference rendering.

A custom judgement rule may omit `good` (the fix is deletion). The renderer
must treat that as empty text, not crash on `.strip()`.
"""

from __future__ import annotations

from slopvac.model import Category, Example, Provenance, Rule, RuleKind, Severity
from slopvac.reference import render_reference
from slopvac.rules import RuleSet


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
