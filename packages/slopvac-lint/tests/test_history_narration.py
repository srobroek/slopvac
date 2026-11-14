"""`history-narration` and `no-longer-change` through `slopvac lint --format json`.

Issue #255: "no longer" fired on runtime state. Issue #256: a labelled, versioned
change note needs a named exception.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.suppression import allow_comment

HISTORY = "docs-discipline.history-narration"
NO_LONGER = "docs-discipline.no-longer-change"
META = "meta.invalid-suppression"


def _rule_ids(tmp_path, text: str) -> list[str]:
    path = tmp_path / "doc.md"
    path.write_text(f"# Notes\n\n{text}\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["lint", str(path), "--format", "json"])
    assert result.exit_code in (0, 1, 2), result.output
    findings = json.loads(result.output)["documents"][0]["findings"]
    return [f["rule_id"] for f in findings]


@pytest.mark.parametrize(
    "sentence",
    [
        "The loader no longer resolves paths.",
        "The parser no longer supports YAML anchors.",
        "The tool is no longer available on Windows.",
        "The flag is no longer required.",
        "The command no longer prints a banner.",
        "The CLI is no longer using the cache.",
        "You no longer need a config file.",
    ],
)
def test_no_longer_before_a_change_verb_is_reported(tmp_path, sentence):
    ids = _rule_ids(tmp_path, sentence)
    assert NO_LONGER in ids
    assert HISTORY not in ids


@pytest.mark.parametrize(
    "sentence",
    [
        "Stop polling when the run is no longer live.",
        "The lock is released once the job is no longer running.",
        "A node that is no longer healthy is drained.",
        "The session is no longer valid after logout.",
    ],
)
def test_no_longer_describing_runtime_state_is_silent(tmp_path, sentence):
    ids = _rule_ids(tmp_path, sentence)
    assert NO_LONGER not in ids
    assert HISTORY not in ids


def test_other_history_phrases_still_report_under_history_narration(tmp_path):
    assert HISTORY in _rule_ids(tmp_path, "The loader was previously named the resolver.")


@pytest.mark.parametrize("rule", [HISTORY, NO_LONGER])
def test_versioned_change_note_is_an_accepted_reason(tmp_path, rule):
    text = (
        "The loader was previously named the resolver and no longer resolves paths."
    )
    plain = _rule_ids(tmp_path, text)
    assert rule in plain
    allowed = _rule_ids(tmp_path, f"{allow_comment(rule, 'versioned-change-note')}\n{text}")
    assert rule not in allowed
    assert META not in allowed


def test_an_unlisted_reason_is_still_rejected(tmp_path):
    text = "The loader was previously named the resolver."
    ids = _rule_ids(tmp_path, f"{allow_comment(HISTORY, 'readability')}\n{text}")
    assert META in ids
    assert HISTORY in ids
