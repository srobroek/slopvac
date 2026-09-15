"""Reference rendering.

A custom judgement rule may omit `good` (the fix is deletion). The renderer
must treat that as empty text, not crash on `.strip()`.
"""

from __future__ import annotations

from slopvac.model import (
    Category,
    Dimension,
    Example,
    JudgementContract,
    JudgementDimension,
    Ownership,
    Provenance,
    Rule,
    RuleKind,
    Severity,
)
from slopvac.reference import render_reference
from slopvac.rules import RuleSet


def test_judgement_example_without_good_renders():
    rule = Rule(
        id="omit-good",
        name="Delete the filler",
        kind=RuleKind.JUDGEMENT,
        dimension=Dimension.REDUNDANCY,
        ownership=Ownership.DOCUMENT_PROBE,
        judgement_contract=JudgementContract(
            admission="The unit is a paragraph of at least two sentences.",
            protects="A closing sentence that states a fact stated nowhere else.",
            dims=[JudgementDimension.FIT, JudgementDimension.WARRANT],
            evidence_arity=1,
            judgement_ceiling=Severity.SUGGESTION,
            rewrite_exempt=False,
        ),
        message="delete it",
        judgement_question="Does this sentence add a fact?",
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
