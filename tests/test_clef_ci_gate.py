"""The required CI gate must reject failed Clef security regressions."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "security_result,exit_code", [("success", 0), ("failure", 1), ("skipped", 1)]
)
def test_clef_security_controls_required_gate(security_result, exit_code):
    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/test.yml"
    ).read_text()
    gate = workflow.split("  gate:\n", 1)[1].split("  lint-gate-compat:", 1)[0]
    assert "      - clef-security\n" in gate.split("    if: always()", 1)[0]
    script = textwrap.dedent(
        gate.split("python3 - <<'PY'\n", 1)[1].split("          PY", 1)[0]
    )
    names = [
        "changes",
        "quick-lint",
        "clef-security",
        "test",
        "lint-package",
        "cli-e2e",
        "action-contract",
        "lint",
        "markdown-audit",
        "security",
    ]
    results = {name: {"result": "success"} for name in names}
    results["clef-security"]["result"] = security_result
    env = {**os.environ, "RESULTS": json.dumps(results)}
    for name in [
        "FORCE_ALL",
        "CODE",
        "PACKAGE",
        "ACTION",
        "LINT",
        "DOCS",
        "SECRETS",
        "DEPENDENCIES",
        "FILESYSTEM",
    ]:
        env[name] = "true"
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
