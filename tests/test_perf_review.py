"""Exercise benchmark commands, not just their argument construction."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.perf import perf


@pytest.mark.parametrize("kind", ["cli", "init"])
def test_non_lint_failure_is_an_error(kind):
    with pytest.raises(subprocess.CalledProcessError):
        perf.run_profiled([sys.executable, "-c", "raise SystemExit(1)"], {"kind": kind})


@pytest.fixture
def benchmark(monkeypatch, tmp_path):
    log = tmp_path / "calls.jsonl"
    counter = iter(range(100))

    def scratch(python, parent):
        path = parent / f"scratch-{next(counter)}"
        path.mkdir()
        return path

    monkeypatch.setattr(perf, "_prepare_scratch", scratch)
    monkeypatch.setattr(perf, "hyperfine_command", lambda: ["fake-hyperfine"])
    monkeypatch.setattr(perf, "_scenario_command", lambda scenario, python, scratch, *rest: [
        sys.executable, "-c",
        "import os,json; from pathlib import Path; "
        f"p=Path({str(log)!r}); "
        f"p.open('a').write(json.dumps([{python!r},os.getcwd()])+'\\n'); "
        f"raise SystemExit({scenario.get('exit', 0)})",
    ])
    real_run = subprocess.run

    def hyperfine(command, **kwargs):
        if command[0] != "fake-hyperfine":
            return real_run(command, **kwargs)
        import shlex

        results = []
        for index, arg in enumerate(command):
            if arg == "--command-name":
                real_run(shlex.split(command[index + 2]), check=True)
                results.append({"name": command[index + 1], "summary": {
                    "time_wall_clock": {"mean": 1.0},
                    "memory_peak_resident": {"mean": 100.0},
                }})
        Path(command[command.index("--export-json") + 1]).write_text(json.dumps({"results": results}))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(perf.subprocess, "run", hyperfine)
    directory = tmp_path / "results"
    directory.mkdir()
    return directory, log


def test_comparison_alternates_revisions_in_separate_projects(benchmark):
    directory, log = benchmark
    results = perf._run_hyperfine([{"name": "setup", "kind": "init"}], directory,
                                 runs=3, base_python="base", head_python="head")
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert [label for label, _ in calls] == ["base", "head", "head", "base", "base", "head"]
    assert len({cwd for _, cwd in calls}) == 2
    assert len(results) == 2
    assert all(item["summary"]["time_wall_clock"]["mean"] == 1 for item in results)


@pytest.mark.parametrize("kind,code,accepted", [
    ("cli", 1, False), ("init", 1, False), ("lint", 1, True), ("lint", 2, False),
])
def test_hyperfine_wrapper_enforces_scenario_exits(benchmark, kind, code, accepted):
    directory, _ = benchmark
    args = ([{"name": "test", "kind": kind, "exit": code}], directory)
    if accepted:
        perf._run_hyperfine(*args, runs=1, base_python="base")
    else:
        with pytest.raises(subprocess.CalledProcessError):
            perf._run_hyperfine(*args, runs=1, base_python="base")


@pytest.mark.skipif(os.name != "posix", reason="profilers require Unix")
def test_notifier_target_really_has_a_terminal():
    result = subprocess.run([
        sys.executable, str(perf.ROOT / "scripts/perf/terminal_target.py"),
        sys.executable, "-c", "import sys; raise SystemExit(0 if sys.stderr.isatty() else 9)",
    ], capture_output=True)
    assert result.returncode == 0


@pytest.mark.parametrize("mode", ["cold", "warm"])
def test_profile_cache_environment(monkeypatch, tmp_path, mode):
    calls = []
    monkeypatch.setattr(perf, "prepare_inputs", lambda *_: ["--version"])
    monkeypatch.setattr(perf.subprocess, "run", lambda command, **kwargs:
                        calls.append((command, kwargs)) or subprocess.CompletedProcess(command, 0))
    scenario = {"kind": "cache", "cache": mode}
    perf.run_profiled(["profiler"], scenario, cwd=tmp_path)
    assert len(calls) == (2 if mode == "warm" else 1)
    assert all(call[1]["env"]["SLOPVAC_CACHE_DIR"] == str(tmp_path / "profile-cache") for call in calls)
