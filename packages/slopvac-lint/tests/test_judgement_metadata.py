from pathlib import Path

import pytest

from slopvac.model import Rule
from slopvac.rules import RuleLoadError, load_ruleset


def test_judgement_exceptions_are_rejected_by_model() -> None:
    with pytest.raises(ValueError, match=r"demo:.*judgement.*exceptions.*never emit"):
        Rule.model_validate(
            {
                "id": "demo",
                "name": "Demo",
                "kind": "judgement",
                "message": "Check it.",
                "judgement_question": "Is it clear?",
                "exceptions": ["quotation"],
                "provenance": {"source": "test"},
            }
        )


def test_loader_rejects_judgement_exceptions(tmp_path: Path) -> None:
    (tmp_path / "category.yml").write_text(
        """id: custom\nname: Custom\nrules:\n  - id: demo\n    name: Demo\n    kind: judgement\n    message: Check it.\n    judgement_question: Is it clear?\n    exceptions: [quotation]\n    provenance:\n      source: test\n""",
        encoding="utf-8",
    )
    with pytest.raises(RuleLoadError, match=r"demo.*judgement.*exceptions.*never emit"):
        load_ruleset([tmp_path], verify=False)
