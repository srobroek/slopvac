from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest

from scripts.perf import perf
from scripts.perf.line_target import resolve
from scripts.perf.perf import (
    ROOT,
    _run_hyperfine,
    accepted_exits,
    filter_scenarios,
    is_load_idle,
    load_scenarios,
    profiler_scenario,
    regression,
    resolve_tool,
    run_profiled,
)


def test_load_threshold_is_strictly_below_cpu_ratio() -> None:
    assert is_load_idle(6.99, 14, 0.5)
    assert not is_load_idle(7.0, 14, 0.5)
    assert not is_load_idle(7.01, 14, 0.5)


@pytest.mark.parametrize(
    ("base", "head", "ratio", "delta_ms", "expected"),
    [
        (1.0, 1.30, 1.25, 50, True),
        (1.0, 1.30, 1.30, 50, False),
        (1.0, 1.20, 1.10, 200, False),
        (1.0, 1.30, 1.25, 299.999, True),
        (1.0, 1.30, 1.25, 300.001, False),
        (0.0, 0.2, 1.25, 50, True),
        (0.0, 0.0, 1.25, 0, False),
    ],
)
def test_regression_requires_ratio_and_absolute_delta(
    base: float, head: float, ratio: float, delta_ms: float, expected: bool
) -> None:
    assert regression(base, head, ratio, delta_ms) is expected


def test_load_scenarios_reads_authoritative_manifest() -> None:
    scenarios = load_scenarios()
    assert len(scenarios) >= 15
    assert filter_scenarios(scenarios, "startup --version")[0]["args"] == ["--version"]
    assert any(scenario.get("notifier") for scenario in scenarios)


def test_scenario_parser_rejects_duplicates_and_unknown_kinds(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.toml"
    duplicate.write_text(
        '[[scenario]]\nname="same"\nkind="cli"\n'
        '[[scenario]]\nname="same"\nkind="cli"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        load_scenarios(duplicate)

    unknown = tmp_path / "unknown.toml"
    unknown.write_text('[[scenario]]\nname="bad"\nkind="custom"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported scenario kind"):
        load_scenarios(unknown)


def test_filter_rejects_unknown_scenario() -> None:
    with pytest.raises(ValueError, match="unknown scenario"):
        filter_scenarios([{"name": "known"}], "missing")


def test_scenario_manifest_is_valid_toml() -> None:
    manifest = Path(__file__).parents[1] / "scripts/perf/scenarios.toml"
    with manifest.open("rb") as stream:
        assert len(tomllib.load(stream)["scenario"]) == len(load_scenarios())


def test_tool_override_accepts_explicit_executable(tmp_path: Path, monkeypatch) -> None:
    executable = tmp_path / "hyperfine"
    executable.write_text("#!/bin/sh\necho hyperfine 2.0.0\n", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setenv("PERF_HYPERFINE", str(executable))
    assert resolve_tool("hyperfine", "PERF_HYPERFINE") == str(executable.resolve())


def test_no_vale_scenarios_accept_the_incomplete_exit() -> None:
    assert accepted_exits({"args": ["--no-vale"]}) == {0, 1, 2}
    assert accepted_exits({"args": []}) == {0, 1}


def test_benchmarks_never_run_in_the_repository(tmp_path: Path, monkeypatch) -> None:
    """`setup` and `init` scenarios write steering files to their cwd."""
    record = tmp_path / "cwd.txt"
    fake = tmp_path / "hyperfine"
    fake.write_text(
        "#!/bin/sh\n"
        f'pwd > "{record}"\n'
        'while [ $# -gt 0 ]; do\n'
        '  if [ "$1" = "--export-json" ]; then printf \'{"results": []}\' > "$2"; fi\n'
        "  shift\n"
        "done\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PERF_HYPERFINE", str(fake))
    directory = tmp_path / "results"
    directory.mkdir()
    scenario = filter_scenarios(load_scenarios(), "startup setup claude")

    _run_hyperfine(scenario, directory, runs=1, base_python=sys.executable)

    cwd = Path(record.read_text(encoding="utf-8").strip()).resolve()
    assert cwd != ROOT.resolve() and ROOT.resolve() not in cwd.parents
    assert directory.resolve() in cwd.parents
    assert json.loads((directory / "hyperfine.json").read_text())["results"] == []


@pytest.mark.parametrize(("code", "args", "ok"), [(1, [], True), (2, ["--no-vale"], True), (2, [], False)])
def test_profilers_accept_only_the_exits_a_scenario_expects(code, args, ok) -> None:
    """A failed gate still yields a profile; an incomplete Vale run does not."""
    command = [sys.executable, "-c", f"raise SystemExit({code})"]
    if ok:
        run_profiled(command, {"args": args})
    else:
        with pytest.raises(perf.subprocess.CalledProcessError):
            run_profiled(command, {"args": args})


def test_a_vale_profile_without_vale_fails_instead_of_running_incomplete(monkeypatch) -> None:
    vale_scenario = next(s for s in load_scenarios() if s.get("requires_vale"))
    monkeypatch.setattr(perf, "resolve_tool", lambda name, variable=None: None)
    with pytest.raises(RuntimeError, match="needs Vale"):
        profiler_scenario(vale_scenario["name"])


def test_line_targets_resolve_functions_and_methods() -> None:
    from slopvac import analyze, engine

    assert resolve("slopvac.analyze:_align_block_text") is analyze._align_block_text
    assert resolve("slopvac.engine:Engine.run") is engine.Engine.run


@pytest.mark.parametrize(
    "spec",
    ["slopvac.analyze", "slopvac.analyze:no_such_function", "slopvac.analyze:_ENTITY"],
)
def test_bad_line_targets_fail_before_profiling(spec: str) -> None:
    with pytest.raises(SystemExit, match="perf-lines"):
        resolve(spec)
