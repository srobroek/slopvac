"""Steering and release metadata must not depend on a marketplace payload."""
import json
from pathlib import Path

from click.testing import CliRunner

from slopvac.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_removed_distributions_have_no_live_release_targets() -> None:
    for path in ("packages/slopvac", ".claude-plugin", ".codex-plugin", ".omp-plugin"):
        assert not (ROOT / path).exists()
    config = json.loads((ROOT / "release-please-config.json").read_text())
    for entry in config["packages"]["."]["extra-files"]:
        path = entry if isinstance(entry, str) else entry["path"]
        assert (ROOT / path).is_file(), path


def test_agent_guidance_covers_lint_judgement_and_content_verification() -> None:
    result = CliRunner().invoke(main, ["prime", "--format", "json"])
    assert result.exit_code == 0, result.output
    guide = json.loads(result.output)["guidance"]
    for command in ("slopvac lint", "slopvac judgement prepare", "slopvac judgement validate",
                    "slopvac judgement finish", "slopvac judgement compare", "slopvac explain"):
        assert command in guide
    assert "factual accuracy or completeness" in guide
    assert "false positive" in guide
    assert "incomplete check cannot be reported as a pass" in guide
