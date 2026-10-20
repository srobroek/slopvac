"""The Vale probe batches its runs and still judges each rule as if alone.

One bad rule makes Vale refuse the whole style directory, so the probe runs every
payload at once and splits only a failing batch. These tests hold the batched
verdicts to the one-at-a-time ones: the same rules refused, for the same reasons,
in the same order. A fake `vale` drives both ways of splitting and a failure that
is not a refusal; the real binary checks the shipped payloads.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from slopvac import compile_vale, vale_probe
from slopvac.config import Config, resolve_for
from slopvac.rules import load_ruleset
from slopvac.vale_probe import ValeUnavailable, probe_payloads
from slopvac.vocabulary import load_blocklist


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("3.17.9", "Vale 3.18.0 or later is required"),
        ("3.18.0", None),
        ("3.24.0", None),
    ],
)
def test_require_vale_checks_version(tmp_path, version, expected):
    binary = tmp_path / "vale"
    binary.write_text(f"#!/bin/sh\necho 'vale version {version}'\n", encoding="utf-8")
    binary.chmod(0o755)
    if expected:
        with pytest.raises(ValeUnavailable, match=expected.replace(".", r"\.")):
            vale_probe.require_vale(str(binary))
    else:
        assert vale_probe.require_vale(str(binary)) == str(binary)


def test_require_vale_reports_missing_executable():
    with pytest.raises(ValeUnavailable, match="not on PATH"):
        vale_probe.require_vale("vale-this-executable-does-not-exist")


VALE = shutil.which("vale")
needs_vale = pytest.mark.skipif(VALE is None, reason="vale is not on PATH")
EXAMPLE_BLOCKLIST = Path(__file__).parent.parent / "examples" / "blocklist.toml"

# Reads the style directory as Vale does, in name order, and stops at the first
# rule it refuses. Each run appends the number of rule files it saw to LOG.
FAKE_VALE = """\
import pathlib
import re
import sys

config = pathlib.Path(sys.argv[1].removeprefix("--config="))
rules = sorted((config.parent / "styles" / "probe").iterdir())
with open(LOG, "a", encoding="utf-8") as log:
    log.write(f"{len(rules)}\\n")
for rule in rules:
    text = rule.read_text(encoding="utf-8")
    refused = re.search(r"REFUSE-\\d+\\(", text)
    if refused:
        where = f" [{rule}:5:3]" if NAMES_FILE else ""
        sys.stderr.write(
            f"E201 Invalid value{where}:\\n\\n"
            f"error parsing regexp: missing closing ): `{refused.group(0)}`\\n"
        )
        sys.exit(2)
    if "CRASH" in text:
        sys.stderr.write("panic: runtime error\\n")
        sys.exit(2)
"""


def _fake_vale(tmp_path: Path, *, names_file: bool) -> tuple[str, Path]:
    log = tmp_path / "runs.log"
    script = tmp_path / "vale"
    script.write_text(
        f"#!{sys.executable}\nLOG = {str(log)!r}\nNAMES_FILE = {names_file!r}\n{FAKE_VALE}",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return str(script), log


def _runs(log: Path) -> list[int]:
    """The number of rule files each fake run saw, in run order."""
    return [int(line) for line in log.read_text(encoding="utf-8").split()]


def _payloads(count: int, *, refused=(), crashing=()) -> dict[str, dict]:
    payloads = {}
    for index in range(count):
        token = f"word{index}"
        if index in refused:
            token = f"REFUSE-{index}("
        elif index in crashing:
            token = "CRASH"
        payloads[f"house.rule-{index}"] = {
            "extends": "existence",
            "message": "m",
            "level": "warning",
            "tokens": [token],
        }
    return payloads


def _refusal(index: int) -> tuple[str, str]:
    return (
        f"house.rule-{index}",
        f"error parsing regexp: missing closing ): `REFUSE-{index}(`",
    )


def test_an_accepted_set_costs_one_vale_run(tmp_path):
    binary, log = _fake_vale(tmp_path, names_file=True)
    assert probe_payloads(_payloads(40), binary) == {}
    assert _runs(log) == [40]


@pytest.mark.parametrize("names_file", [True, False], ids=["file-named", "no-file-named"])
def test_a_batch_refuses_the_same_rules_for_the_same_reasons_in_order(
    tmp_path, names_file
):
    """Vale names the first file it refused, and the split isolates that rule.
    Without a name the split halves the batch. Both reach the same verdicts."""
    binary, log = _fake_vale(tmp_path, names_file=names_file)
    payloads = _payloads(40, refused={0, 17, 18, 39})
    assert list(probe_payloads(payloads, binary).items()) == [
        _refusal(0),
        _refusal(17),
        _refusal(18),
        _refusal(39),
    ]
    runs = _runs(log)
    assert runs[0] == 40
    assert len(runs) < len(payloads)
    if names_file:
        assert len(runs) <= 1 + 3 * 4


def test_a_failure_that_is_not_a_refusal_still_raises(tmp_path):
    """A batch that fails without a refusal is split like any other; the single
    rule that fails alone raises, as it did when every rule ran alone."""
    binary, _ = _fake_vale(tmp_path, names_file=True)
    payloads = _payloads(40, refused={3}, crashing={25})
    with pytest.raises(
        ValeUnavailable, match=r"^Vale validation failed \(2\): panic: runtime error$"
    ):
        probe_payloads(payloads, binary)


@pytest.fixture(scope="module")
def shipped_payloads() -> dict[str, dict]:
    """The payloads a README compile with the example blocklist hands the probe."""
    if VALE is None:
        pytest.skip("vale is not on PATH")
    seen: list[dict[str, dict]] = []

    def record(payloads, binary):
        seen.append(dict(payloads))
        return {}

    with pytest.MonkeyPatch.context() as patch, tempfile.TemporaryDirectory() as out:
        patch.setattr(compile_vale, "probe_payloads", record)
        compile_vale.compile_ruleset(
            load_ruleset(),
            resolve_for(Config(), Path("README.md")),
            outdir=Path(out),
            validate=True,
            vocabulary=load_blocklist(EXAMPLE_BLOCKLIST),
            force=True,
        )
    [payloads] = seen
    return payloads


@pytest.fixture
def vale_runs(monkeypatch) -> list[list[str]]:
    """The argv of every subprocess the probe starts."""
    seen: list[list[str]] = []
    real = vale_probe.subprocess.run

    def spy(args, **kwargs):
        seen.append(list(args))
        return real(args, **kwargs)

    monkeypatch.setattr(vale_probe.subprocess, "run", spy)
    return seen


@needs_vale
def test_the_shipped_payloads_cost_one_run_plus_three_per_refusal(
    shipped_payloads, vale_runs
):
    rejected = probe_payloads(shipped_payloads, VALE)
    assert 1 <= len(vale_runs) <= 1 + 3 * len(rejected)


@needs_vale
def test_the_shipped_payloads_route_as_they_did_one_at_a_time(shipped_payloads):
    """Three payloads Vale refuses, at the start, middle, and end of the shipped
    set. The batch must refuse exactly what single-rule runs refuse."""
    payloads = dict(shipped_payloads)
    ids = list(payloads)
    broken = {ids[0]: r"(?a:\w+)", ids[len(ids) // 2]: "foo(bar", ids[-1]: "[z-a]"}
    for rule_id, token in broken.items():
        payloads[rule_id] = {
            "extends": "existence",
            "message": "m",
            "level": "warning",
            "tokens": [token],
        }

    one_at_a_time: dict[str, str] = {}
    for rule_id, payload in payloads.items():
        one_at_a_time.update(probe_payloads({rule_id: payload}, VALE))

    assert set(broken) <= set(one_at_a_time)
    assert list(probe_payloads(payloads, VALE).items()) == list(one_at_a_time.items())
