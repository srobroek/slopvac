"""Per-rule finding counts on vendored real pages and issue samples.

`fixtures/regression/manifest.json` records, for each fixture, the finding count per
rule the Python reference produces today. The counts record current behaviour, not
desired behaviour. A rule fix that changes a count updates the manifest in the same
change; regenerate it with `SLOPVAC_UPDATE_REGRESSION=1 uv run pytest -k regression`
and review the diff.

Fixtures are linted through stdin so the file path (`fixtures/` classifies as a
template) cannot change the result. Counts include the Vale sub-gate and depend on
its version, which the manifest records. Regenerate with the version pinned in
mise.toml. The test skips when Vale is absent, and skips on another Vale version
outside CI.
"""

from __future__ import annotations

import collections
import json
import os
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.contract import EXIT_ERROR
from slopvac.vale_probe import vale_version

ROOT = Path(__file__).parent / "fixtures" / "regression"
MANIFEST = ROOT / "manifest.json"
UPDATE = os.environ.get("SLOPVAC_UPDATE_REGRESSION") == "1"

_MANIFEST = json.loads(MANIFEST.read_text(encoding="utf-8"))
_ENTRIES = _MANIFEST["fixtures"]
_IN_CI = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def _counts(entry: dict) -> dict[str, int]:
    text = (ROOT / entry["path"]).read_text(encoding="utf-8")
    config = ROOT / entry.get("config", "default.toml")
    result = CliRunner().invoke(
        main,
        [
            "lint",
            "--stdin",
            "--language",
            "markdown",
            "--config",
            str(config),
            "--format",
            "json",
        ],
        input=text,
    )
    assert result.exit_code != EXIT_ERROR, result.output
    findings = [
        finding["rule_id"]
        for document in json.loads(result.output)["documents"]
        for finding in document["findings"]
    ]
    return dict(sorted(collections.Counter(findings).items()))


@pytest.mark.skipif(shutil.which("vale") is None, reason="vale is not on PATH")
@pytest.mark.parametrize("entry", _ENTRIES, ids=[entry["id"] for entry in _ENTRIES])
def test_regression_fixture_per_rule_counts(entry: dict) -> None:
    if UPDATE and _IN_CI:
        pytest.fail(
            "SLOPVAC_UPDATE_REGRESSION=1 must not run in CI; it rewrites the expectations"
        )
    version = ".".join(map(str, vale_version() or ()))
    if UPDATE:
        _MANIFEST["vale"] = version
    elif version != _MANIFEST["vale"]:
        # Vale's tokenizer shifts a few counts between releases. CI installs the
        # version pinned in mise.toml, so a bump there must regenerate the manifest.
        message = f"counts were recorded with Vale {_MANIFEST['vale']}, found {version}"
        if _IN_CI:
            pytest.fail(message)
        pytest.skip(message)
    actual = _counts(entry)
    if UPDATE:
        entry["expected"] = actual
        MANIFEST.write_text(json.dumps(_MANIFEST, indent=2) + "\n", encoding="utf-8")
    assert actual == entry["expected"]
