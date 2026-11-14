"""`ste-procedural.condition-after-command` fires on instructions, not on prose
that merely contains `when`, `if`, `before` or `after`.

Every case goes through the public `slopvac lint` interface. The rule is
Vale-owned, so the tests need Vale. The samples come from issue #254 and from a
labelled run over a documentation page (see the pull request for the dataset).
"""

from __future__ import annotations

import json
import shutil

import pytest
from click.testing import CliRunner

from slopvac.cli import main

RULE = "ste-procedural.condition-after-command"

pytestmark = pytest.mark.skipif(
    shutil.which("vale") is None, reason="vale is not on PATH"
)


def _fired_lines(tmp_path, text: str) -> list[int]:
    path = tmp_path / "doc.md"
    path.write_text(text, encoding="utf-8")
    result = CliRunner().invoke(
        main,
        ["lint", str(path), "--format", "json", "--profile", "strict"],
        catch_exceptions=False,
    )
    report = json.loads(result.output)
    return [
        finding["line"]
        for document in report["documents"]
        for finding in document["findings"]
        if finding["rule_id"] == RULE
    ]


@pytest.mark.parametrize(
    "sentence",
    [
        "Restart the worker if the queue depth is above one thousand.",
        "Choose `auto` when you want the checker to block findings.",
        "Pass `--permission-mode` when you start `mecated` or `mecatui`.",
        "Use `yolo` if the main agent must run them unattended.",
        # Lead-in, then the command, then the condition.
        "For headless servers and one-shot jobs, configure the permissions required by "
        "the workload before it starts.",
        "To save time, rerun the check after the import completes.",
        # A verb outside the closed list, found by its object.
        "Reconcile the ledger when the import completes.",
        # `before`/`after` followed by a noun is still a condition.
        "Back up the database before installation.",
    ],
)
def test_instruction_with_trailing_condition_is_reported(tmp_path, sentence):
    assert _fired_lines(tmp_path, f"{sentence}\n") == [1]


@pytest.mark.parametrize(
    "sentence",
    [
        # The condition comes first.
        "If the queue depth is above one thousand, restart the worker.",
        "When you start `mecated`, pass `--permission-mode`.",
        "After the import completes, clear the cache.",
        "If you roll back to a release without session-scoped modes, that release "
        "still loads `auto` sessions unless the server pins a mode.",
        # Descriptive sentences whose subject is a noun phrase.
        "Action reviews offer **Run once** or **Cancel**.",
        "Result reviews offer **Release once** or **Cancel** before the client replies.",
        "Derivation consumes one remaining delegation hop before allocating the child.",
        "Mecatl rejects a tool call whose arguments repeat a key before any rule runs.",
        "Only `yolo` also serves external paths when the root is trusted.",
        "What happens when the cycle lands on a mode depends on the server ceiling.",
        "So is passing `--yolo` while your operator sets `permissionMode`.",
        "Headless deployments have no approval channel, so configure access before "
        "starting work.",
        # A lead-in does not turn a descriptive clause into a command.
        "For each plan it presents, the model calls the review tool once before it "
        "stops.",
    ],
)
def test_prose_without_a_trailing_condition_on_a_command_is_left_alone(
    tmp_path, sentence
):
    assert _fired_lines(tmp_path, f"{sentence}\n") == []


def test_issue_254_sample_reports_only_the_real_instruction(tmp_path):
    sample = (
        "## Change the mode after launch\n"  # 1: heading
        "\n"
        "For each plan it presents, the model calls the review tool once.\n"  # 3
        "\n"
        "Action reviews offer **Run once** or **Cancel**.\n"  # 5
        "\n"
        "|Mode|Behavior|\n"
        "|-|-|\n"
        "|`block`|For action reviews, stops or asks before execution.|\n"  # 9: cell
        "\n"
        "The server loads its policy once at startup; an invalid policy prevents "
        "startup.\n"  # 11
        "\n"
        "Choose `auto` when you want the checker to block findings.\n"  # 13
    )
    assert _fired_lines(tmp_path, sample) == [13]


@pytest.mark.parametrize(
    "cell",
    ["Restart the worker if the queue is full.", "Clear the cache when it fills."],
)
def test_table_cells_and_headings_are_not_checked(tmp_path, cell):
    table = f"|Mode|Behavior|\n|-|-|\n|`block`|{cell}|\n"
    heading = f"## {cell}\n"
    assert _fired_lines(tmp_path, table) == []
    assert _fired_lines(tmp_path, heading) == []


def test_list_items_are_still_checked(tmp_path):
    assert _fired_lines(tmp_path, "- Use `yolo` if the agent runs unattended.\n") == [1]
