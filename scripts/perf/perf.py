#!/usr/bin/env python3
"""Local, reproducible Slopvac profiling and benchmarking (stdlib only)."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "scripts/perf/scenarios.toml"
DEFAULT_SCENARIO = "startup --version"
PROFILE_TOOLS = ("pyinstrument", "scalene", "viztracer", "memray", "py-spy", "tuna", "kernprof")
LOAD_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
IMPORT_RE = re.compile(r"import time:\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.*)")


def load_scenarios(path: Path = SCENARIOS) -> list[dict[str, Any]]:
    with path.open("rb") as stream:
        scenarios = tomllib.load(stream).get("scenario")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenario manifest must contain at least one [[scenario]]")

    names: set[str] = set()
    kinds = {"cli", "init", "lint", "cache", "comments"}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise TypeError("each scenario must be a table")
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError(f"scenario names must be non-empty and unique: {name!r}")
        names.add(name)
        if scenario.get("kind") not in kinds:
            raise ValueError(f"unsupported scenario kind for {name!r}")
        args = scenario.get("args", [])
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ValueError(f"scenario args must be strings: {name!r}")
        if scenario["kind"] in {"lint", "cache", "comments"}:
            path_value = scenario.get("path")
            if not isinstance(path_value, str) or not (ROOT / path_value).exists():
                raise ValueError(f"scenario input does not exist: {name!r}")
        if scenario.get("cache", "") not in {"", "cold", "warm"}:
            raise ValueError(f"invalid cache mode for {name!r}")
    return scenarios


def filter_scenarios(scenarios: list[dict[str, Any]], name: str | None) -> list[dict[str, Any]]:
    if name is None:
        return scenarios
    selected = [scenario for scenario in scenarios if scenario["name"] == name]
    if not selected:
        choices = ", ".join(scenario["name"] for scenario in scenarios)
        raise ValueError(f"unknown scenario {name!r}; choose one of: {choices}")
    return selected


def load_average() -> float:
    if sys.platform == "darwin":
        result = subprocess.run(
            ["sysctl", "-n", "vm.loadavg"], check=True, text=True, capture_output=True
        )
        values = LOAD_RE.findall(result.stdout)
    elif sys.platform.startswith("linux"):
        values = Path("/proc/loadavg").read_text(encoding="ascii").split()
    else:
        raise RuntimeError(f"performance load gate is unsupported on {sys.platform}")
    if not values:
        raise RuntimeError("could not read the one-minute system load average")
    return float(values[0])


def is_load_idle(load: float, ncpu: int, ratio: float) -> bool:
    if ncpu < 1 or ratio < 0:
        raise ValueError("CPU count must be positive and idle ratio non-negative")
    return load < ncpu * ratio


def wait_for_idle() -> tuple[float, float]:
    ratio = float(os.environ.get("PERF_IDLE_RATIO", "0.5"))
    timeout = float(os.environ.get("PERF_IDLE_TIMEOUT", "1800"))
    if ratio < 0 or timeout < 0:
        raise ValueError("PERF_IDLE_RATIO and PERF_IDLE_TIMEOUT must be non-negative")
    initial = load_average()
    if os.environ.get("PERF_SKIP_IDLE") == "1":
        print(f"Idle gate bypassed (load {initial:.2f}, PERF_SKIP_IDLE=1).")
        return initial, initial
    ncpu = cpu_count()
    current = initial
    started = time.monotonic()
    while True:
        if is_load_idle(current, ncpu, ratio):
            print(f"Load {current:.2f} is below {ncpu} × {ratio:g}; starting measurements.")
            return initial, current
        elapsed = time.monotonic() - started
        if elapsed >= timeout:
            raise TimeoutError(
                f"System load stayed at or above {ncpu * ratio:.2f} for {timeout:g}s "
                f"(last 1-minute load: {current:.2f}); retry when the host is idle, "
                "or set PERF_SKIP_IDLE=1."
            )
        remaining = timeout - elapsed
        print(
            f"Waiting for load {current:.2f} to fall below {ncpu * ratio:.2f} "
            f"({remaining:.0f}s remaining)."
        )
        time.sleep(min(15, remaining))
        current = load_average()


def regression(base_mean: float, head_mean: float, max_ratio: float, min_delta_ms: float) -> bool:
    if min(base_mean, head_mean, max_ratio, min_delta_ms) < 0:
        raise ValueError("benchmark means and thresholds must be non-negative")
    return head_mean > base_mean * max_ratio and (head_mean - base_mean) * 1000 > min_delta_ms


def git_output(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def package_version(python: str) -> str:
    result = subprocess.run(
        [python, "-c", "import slopvac; print(slopvac.__version__)"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip()


def resolve_tool(name: str, variable: str | None = None) -> str | None:
    requested = os.environ.get(variable) if variable else None
    executable = shutil.which(requested or name)
    if executable is None:
        mise = shutil.which("mise")
        if mise is None:
            return None
        result = subprocess.run([mise, "which", name], check=False, text=True, capture_output=True)
        if result.returncode == 0:
            candidate = Path(result.stdout.strip())
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None
    resolved = Path(executable).resolve()
    if resolved.name == "mise":
        mise = shutil.which("mise")
        if mise is None:
            return None
        mise_which = subprocess.run(
            [mise, "which", requested or name], check=False, text=True, capture_output=True
        )
        if mise_which.returncode == 0:
            candidate = Path(mise_which.stdout.strip())
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        return None
    return str(resolved)


def tool_versions() -> tuple[dict[str, str | None], dict[str, str | None]]:
    versions: dict[str, str | None] = {"python": sys.version.split()[0]}
    paths: dict[str, str | None] = {}
    for tool in PROFILE_TOOLS + ("hyperfine", "vale"):
        variable = {"hyperfine": "PERF_HYPERFINE", "vale": "PERF_VALE"}.get(tool)
        executable = resolve_tool(tool, variable)
        paths[tool] = executable
        if executable is None:
            versions[tool] = None
            continue
        try:
            result = subprocess.run([executable, "--version"], check=False, text=True, capture_output=True, timeout=10)
            lines = (result.stdout or result.stderr).strip().splitlines()
            versions[tool] = lines[0] if lines else f"exit {result.returncode}"
        except (OSError, subprocess.TimeoutExpired) as error:
            versions[tool] = f"unavailable: {error}"
    return versions, paths


def result_dir(recipe: str) -> Path:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = ROOT / "perf-results" / f"{stamp}-{recipe}"
    suffix = 1
    while destination.exists():
        destination = ROOT / "perf-results" / f"{stamp}-{recipe}-{suffix}"
        suffix += 1
    destination.mkdir(parents=True, exist_ok=False)
    versions, paths = tool_versions()
    metadata = {
        "git_sha": git_output("rev-parse", "HEAD"),
        "git_dirty": bool(git_output("status", "--porcelain")),
        "git_diff_sha256": hashlib.sha256(git_output("diff", "HEAD", "--binary").encode()).hexdigest(),
        "git_untracked": git_output("ls-files", "--others", "--exclude-standard").splitlines(),
        "slopvac_version": package_version(sys.executable),
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "ncpu": cpu_count(),
        "load_average_start": load_average(),
        "load_average_end": None,
        "tools": versions,
        "tool_paths": paths,
    }
    (destination / "meta.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return destination


def finish_metadata(directory: Path) -> None:
    path = directory / "meta.json"
    if path.exists():
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["load_average_end"] = load_average()
        path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def check_tools(*names: str) -> None:
    overrides = {"hyperfine": "PERF_HYPERFINE", "vale": "PERF_VALE"}
    missing = [name for name in names if resolve_tool(name, overrides.get(name)) is None]
    if missing:
        raise RuntimeError("missing required tools: " + ", ".join(missing))


def _prepare_scratch(python: str, parent: Path) -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="slopvac-perf-project-", dir=parent))
    try:
        subprocess.run(["git", "init", "-q"], cwd=scratch, check=True)
        env = os.environ.copy()
        env["NO_UPDATE_NOTIFIER"] = "1"
        subprocess.run(
            [python, "-m", "slopvac.cli", "init", "--harness", "claude", "--force"],
            cwd=scratch,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
        )
    except BaseException:
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    return scratch


def prepare_inputs(scenario: dict[str, Any], scratch: Path) -> list[str]:
    args = list(scenario.get("args", []))
    if scenario["kind"] not in {"lint", "cache", "comments"}:
        return args
    source = ROOT / scenario["path"]
    destination = scratch / "benchmark-inputs" / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(source, destination)
    args.append(str(destination))
    return args


def _scenario_command(
    scenario: dict[str, Any],
    python: str,
    scratch: Path,
    warm_cache: Path,
    cache: Path | None,
) -> list[str]:
    command = [python, "-m", "slopvac.cli", *prepare_inputs(scenario, scratch)]
    if scenario.get("cache") == "warm":
        command = ["env", f"SLOPVAC_CACHE_DIR={warm_cache}", *command]
    elif scenario.get("cache") == "cold" and cache is not None:
        command = ["env", f"SLOPVAC_CACHE_DIR={cache}", *command]
    if scenario.get("notifier"):
        return [
            "env", "-u", "NO_UPDATE_NOTIFIER", "-u", "SLOPVAC_NO_UPDATE_CHECK",
            "-u", "DO_NOT_TRACK", "-u", "CI", *command,
        ]
    return ["env", "NO_UPDATE_NOTIFIER=1", *command]


def _prepare_cache_command(path: Path) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "prepare-cache", str(path)]


def hyperfine_command() -> list[str]:
    executable = resolve_tool("hyperfine", "PERF_HYPERFINE")
    if executable:
        return [executable]
    raise RuntimeError("hyperfine is not on PATH; install it or set PERF_HYPERFINE")


def cpu_count() -> int:
    if sys.platform.startswith("linux"):
        nproc = shutil.which("nproc")
        if nproc:
            result = subprocess.run([nproc], check=True, text=True, capture_output=True)
            return max(1, int(result.stdout.strip()))
    return os.cpu_count() or 1


def _run_hyperfine(
    scenarios: list[dict[str, Any]],
    directory: Path,
    *,
    runs: int,
    base_python: str,
    head_python: str | None = None,
) -> list[dict[str, Any]]:
    hyperfine = hyperfine_command()
    available = []
    for scenario in scenarios:
        if scenario.get("requires_vale") and resolve_tool("vale", "PERF_VALE") is None:
            print(f"SKIP {scenario['name']}: Vale not found on PATH or PERF_VALE.")
        else:
            available.append(scenario)
    if not available:
        raise RuntimeError("no selected scenarios can run")

    head_python = head_python or base_python
    paired = head_python != base_python
    commands = [
        *hyperfine,
        "-N", "--warmup", "1", "--runs", str(runs), "--style", "basic",
        # slopvac exits 1 for a failed gate and 2 for an incomplete run (every
        # `--no-vale` scenario); both are expected results, not benchmark errors.
        "--metrics", "time_wall_clock,memory_peak_resident",
        "--export-json", str(directory / "hyperfine.json"),
        "--export-markdown", str(directory / "hyperfine.md"),
    ]
    scratch_dirs: list[Path] = []
    prepares: list[str] = []
    specs: list[tuple[str, str]] = []
    try:
        for index, scenario in enumerate(available):
            scenario_dir = directory / f"scenario-{index}"
            scenario_dir.mkdir()
            variants = [("BASE", base_python), ("HEAD", head_python)] if paired else [(scenario["name"], base_python)]
            for label, interpreter in variants:
                scratch = _prepare_scratch(interpreter, scenario_dir)
                scratch_dirs.append(scratch)
                cache = None
                warm_cache = scenario_dir / f"cache-{label.replace(' ', '-')}-warm"
                if scenario.get("cache") == "warm":
                    warm_cache.mkdir(mode=0o700)
                    warm_args = prepare_inputs(scenario, scratch)
                    warm_env = os.environ.copy()
                    warm_env.update({"NO_UPDATE_NOTIFIER": "1", "SLOPVAC_CACHE_DIR": str(warm_cache)})
                    warm = subprocess.run(
                        [interpreter, "-m", "slopvac.cli", *warm_args],
                        cwd=scratch,
                        env=warm_env,
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if warm.returncode not in accepted_exits(scenario):
                        raise subprocess.CalledProcessError(warm.returncode, warm.args)
                    prepares.append("true")
                elif scenario.get("cache") == "cold":
                    cache = scenario_dir / f"cache-{label.replace(' ', '-')}-cold"
                    prepares.append(shlex.join(_prepare_cache_command(cache)))
                else:
                    prepares.append("true")
                command = _scenario_command(scenario, interpreter, scratch, warm_cache, cache)
                if scenario.get("notifier"):
                    command = [sys.executable, str(ROOT / "scripts/perf/terminal_target.py"), *command]
                accepted = "|".join(map(str, sorted(accepted_exits(scenario))))
                script = (f"cd {shlex.quote(str(scratch))} || exit 125; "
                          f"{shlex.join(command)}; status=$?; "
                          f"case $status in {accepted}) exit 0;; *) exit 125;; esac")
                specs.append((f"{label} {scenario['name']}" if paired else scenario["name"],
                              shlex.join(["sh", "-c", script])))
        # A paired comparison runs one sample of each revision per round.
        # Reverse the order every round to balance which revision runs first.
        samples: dict[str, list[dict[str, Any]]] = {}
        rounds = runs if paired else 1
        for round_index in range(rounds):
            invocation = list(commands)
            output = directory / (f"hyperfine-{round_index}.json" if paired else "hyperfine.json")
            invocation[invocation.index("--export-json") + 1] = str(output)
            if paired:
                invocation[invocation.index("--export-markdown") + 1] = str(directory / f"hyperfine-{round_index}.md")
                invocation[invocation.index("--runs") + 1] = "1"
                invocation[invocation.index("--warmup") + 1] = "1" if round_index == 0 else "0"
            order = list(range(len(specs)))
            if round_index % 2:
                order.reverse()
            for index in order:
                name, command = specs[index]
                invocation.extend(["--command-name", name, command])
            if any(prepare != "true" for prepare in prepares):
                for index in order:
                    invocation.extend(["--prepare", prepares[index]])
            subprocess.run(invocation, cwd=scratch_dirs[0], check=True, text=True)
            result = json.loads(output.read_text(encoding="utf-8"))["results"]
            if not paired:
                return result
            for item in result:
                samples.setdefault(item["name"], []).append(item)
        combined = []
        for name, items in samples.items():
            summary = {}
            for metric in items[0]["summary"]:
                values = [item["summary"][metric]["mean"] for item in items]
                summary[metric] = {"mean": statistics.mean(values),
                                   "stddev": statistics.stdev(values) if len(values) > 1 else 0,
                                   "min": min(values), "max": max(values)}
            combined.append({"name": name, "summary": summary})
        (directory / "hyperfine.json").write_text(json.dumps({"results": combined}, indent=2) + "\n")
        return combined
    finally:
        for scratch in scratch_dirs:
            shutil.rmtree(scratch, ignore_errors=True)


def accepted_exits(scenario: dict[str, Any]) -> set[int]:
    """Exit codes that mean the scenario ran as intended.

    0 is a pass and 1 a failed gate. `--no-vale` leaves Vale-backed rules
    unchecked, so those runs always exit 2 and that is their expected outcome.
    """
    accepted = {0, 1} if scenario.get("kind") in {"lint", "cache", "comments"} else {0}
    if "--no-vale" in scenario.get("args", []):
        accepted.add(2)
    return accepted


def run_scenario(name: str, python: str, scratch: Path, warm_cache: Path) -> None:
    scenario = filter_scenarios(load_scenarios(), name)[0]
    cache = Path(tempfile.mkdtemp(prefix="slopvac-perf-cache-")) if scenario.get("cache") == "cold" else None
    command = _scenario_command(scenario, python, scratch, warm_cache, cache)
    try:
        result = subprocess.run(command, cwd=scratch, check=False)
        if result.returncode not in accepted_exits(scenario):
            raise subprocess.CalledProcessError(result.returncode, command)
    finally:
        if cache is not None:
            shutil.rmtree(cache, ignore_errors=True)


def run_bench(scenarios: list[dict[str, Any]], runs: int) -> None:
    check_tools("hyperfine")
    directory = result_dir("bench")
    try:
        _run_hyperfine(scenarios, directory, runs=runs, base_python=sys.executable)
    finally:
        finish_metadata(directory)
    print(f"Benchmark artifacts: {directory}")


def run_import(scenario: str | None) -> None:
    if scenario:
        filter_scenarios(load_scenarios(), scenario)
    directory = result_dir("import")
    log = directory / "importtime.log"
    with log.open("w", encoding="utf-8") as stream:
        subprocess.run(
            [sys.executable, "-X", "importtime", "-c", "import slopvac.cli"],
            cwd=ROOT,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=True,
        )
    rows = []
    for line in log.read_text(encoding="utf-8").splitlines():
        match = IMPORT_RE.search(line)
        if match:
            rows.append((int(match.group(2)), int(match.group(1)), match.group(3)))
    print(f"Top import-time entries from {log} (cumulative microseconds):")
    for cumulative, own, name in sorted(rows, reverse=True)[:20]:
        print(f"{cumulative:>10} {own:>8} {name}")
    print(f"Inspect interactively with: uv run --group profile tuna {shlex.quote(str(log))}")
    if os.environ.get("PERF_OPEN") == "1":
        subprocess.run(["uv", "run", "--group", "profile", "tuna", str(log)], check=True)
    finish_metadata(directory)


def profiler_scratch(directory: Path, scenario: dict[str, Any]) -> tuple[Path, list[str]]:
    parent = Path(tempfile.mkdtemp(prefix="scratch-", dir=directory))
    scratch = _prepare_scratch(sys.executable, parent)
    return scratch, prepare_inputs(scenario, scratch)


def profiler_scenario(name: str | None) -> dict[str, Any]:
    scenario = filter_scenarios(load_scenarios(), name or DEFAULT_SCENARIO)[0]
    if scenario.get("requires_vale") and resolve_tool("vale", "PERF_VALE") is None:
        raise RuntimeError(f"{scenario['name']} needs Vale: put it on PATH or set PERF_VALE")
    return scenario


def run_profiled(command: list[str], scenario: dict[str, Any], *, python: str | None = None, **kwargs: Any) -> None:
    """Run a profiler over slopvac, accepting the exits the scenario expects."""
    scratch = kwargs.get("cwd")
    if scratch is not None:
        env = dict(kwargs.pop("env", os.environ.copy()))
        if scenario.get("notifier"):
            for name in ("NO_UPDATE_NOTIFIER", "SLOPVAC_NO_UPDATE_CHECK", "DO_NOT_TRACK", "CI"):
                env.pop(name, None)
            command = [sys.executable, str(ROOT / "scripts/perf/terminal_target.py"), *command]
        else:
            env["NO_UPDATE_NOTIFIER"] = "1"
        if scenario.get("cache"):
            cache = Path(scratch) / "profile-cache"
            if scenario["cache"] == "cold":
                shutil.rmtree(cache, ignore_errors=True)
            cache.mkdir(mode=0o700, exist_ok=True)
            env["SLOPVAC_CACHE_DIR"] = str(cache)
            if scenario["cache"] == "warm":
                warm = subprocess.run([python or sys.executable, "-m", "slopvac.cli", *prepare_inputs(scenario, Path(scratch))],
                                      cwd=scratch, env=env, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if warm.returncode not in accepted_exits(scenario):
                    raise subprocess.CalledProcessError(warm.returncode, warm.args)
        # sudo resets its environment. Put the scenario settings on the profiled
        # child command as well, without forwarding unrelated environment values.
        if "sudo" in command and "--" in command:
            child = command.index("--") + 1
            settings = ["env"]
            for name in ("SLOPVAC_CACHE_DIR", "NO_UPDATE_NOTIFIER", "PATH"):
                if name in env:
                    settings.append(f"{name}={env[name]}")
            if scenario.get("notifier"):
                settings = ["env", "-u", "NO_UPDATE_NOTIFIER", "-u",
                            "SLOPVAC_NO_UPDATE_CHECK", "-u", "DO_NOT_TRACK",
                            "-u", "CI", *settings[1:]]
            command = [*command[:child], *settings, *command[child:]]
        kwargs["env"] = env
    result = subprocess.run(command, check=False, **kwargs)
    if result.returncode not in accepted_exits(scenario):
        raise subprocess.CalledProcessError(result.returncode, command)


def run_cpu(scenario_name: str | None) -> None:
    check_tools("pyinstrument")
    scenario = profiler_scenario(scenario_name)
    directory = result_dir("cpu")
    scratch, args = profiler_scratch(directory, scenario)
    env = os.environ.copy()
    env["NO_UPDATE_NOTIFIER"] = "1"
    try:
        with (directory / "cpu.txt").open("w", encoding="utf-8") as output:
            run_profiled(["pyinstrument", "-m", "slopvac.cli", *args], scenario, cwd=scratch, env=env, stdout=output)
        run_profiled(["pyinstrument", "--renderer", "html", "-o", str(directory / "cpu.html"), "-m", "slopvac.cli", *args], scenario, cwd=scratch, env=env, stdout=subprocess.DEVNULL)
    finally:
        shutil.rmtree(scratch.parent, ignore_errors=True)
        finish_metadata(directory)
    print(f"CPU profile artifacts: {directory}")


def run_scalene(scenario_name: str | None) -> None:
    check_tools("scalene")
    scenario = profiler_scenario(scenario_name)
    directory = result_dir("scalene")
    scratch, args = profiler_scratch(directory, scenario)
    target = directory / "target.py"
    target.write_text("from slopvac.cli import main\nmain()\n", encoding="utf-8")
    env = os.environ.copy()
    env["NO_UPDATE_NOTIFIER"] = "1"
    try:
        # Scalene attributes samples only to code under the target's directory by
        # default, which here is the stub `target.py`; point it at the package.
        source = ROOT / "packages/slopvac-lint/src/slopvac"
        run_profiled(["scalene", "run", "--program-path", str(source), "-o", str(directory / "scalene.json"), str(target), "---", *args], scenario, cwd=scratch, env=env, stdout=subprocess.DEVNULL)
        with (directory / "scalene.txt").open("w", encoding="utf-8") as output:
            subprocess.run(["scalene", "view", "--cli", str(directory / "scalene.json")], check=True, stdout=output, stderr=subprocess.STDOUT)
    finally:
        shutil.rmtree(scratch.parent, ignore_errors=True)
        finish_metadata(directory)
    print(f"Scalene profile artifacts: {directory}")


def run_lines(scenario_name: str | None) -> None:
    """Time each line of the functions in PERF_LINE_FUNCS; the source needs no decorators."""
    check_tools("kernprof")
    if not os.environ.get("PERF_LINE_FUNCS", "").split():
        raise RuntimeError("perf-lines needs FUNCS, e.g. FUNCS=slopvac.analyze:_align_block_text")
    scenario = profiler_scenario(scenario_name)
    directory = result_dir("lines")
    scratch, args = profiler_scratch(directory, scenario)
    env = os.environ.copy()
    env["NO_UPDATE_NOTIFIER"] = "1"
    env["PERF_LINE_OUT"] = str(directory / "lines.txt")
    try:
        run_profiled([sys.executable, str(ROOT / "scripts/perf/line_target.py"), *args], scenario, cwd=scratch, env=env, stdout=subprocess.DEVNULL)
    finally:
        shutil.rmtree(scratch.parent, ignore_errors=True)
        finish_metadata(directory)
    print(f"Line profile: {directory / 'lines.txt'} (raw stats: {directory / 'lines.lprof'})")


def run_timeline(scenario_name: str | None) -> None:
    check_tools("viztracer")
    scenario = profiler_scenario(scenario_name)
    directory = result_dir("timeline")
    scratch, args = profiler_scratch(directory, scenario)
    env = os.environ.copy()
    env["NO_UPDATE_NOTIFIER"] = "1"
    try:
        run_profiled(["viztracer", "-o", str(directory / "timeline.json"), "--module", "slopvac.cli", *args], scenario, cwd=scratch, env=env, stdout=subprocess.DEVNULL)
    finally:
        shutil.rmtree(scratch.parent, ignore_errors=True)
        finish_metadata(directory)
    print(f"Timeline: {directory / 'timeline.json'}")
    print(f"Open with: uv run --group profile vizviewer {directory / 'timeline.json'}")


def run_mem(scenario_name: str | None) -> None:
    check_tools("memray")
    scenario = profiler_scenario(scenario_name)
    directory = result_dir("mem")
    scratch, args = profiler_scratch(directory, scenario)
    trace = directory / "memray.bin"
    env = os.environ.copy()
    env["NO_UPDATE_NOTIFIER"] = "1"
    try:
        run_profiled(["memray", "run", "-o", str(trace), "-m", "slopvac.cli", *args], scenario, cwd=scratch, env=env, stdout=subprocess.DEVNULL)
        with (directory / "memray-stats.txt").open("w", encoding="utf-8") as output:
            subprocess.run(["memray", "stats", str(trace)], check=True, text=True, stdout=output, stderr=subprocess.STDOUT)
        subprocess.run(["memray", "flamegraph", "-o", str(directory / "memray.html"), str(trace)], check=True, stdout=subprocess.DEVNULL)
    finally:
        shutil.rmtree(scratch.parent, ignore_errors=True)
        finish_metadata(directory)
    print(f"Memory profile artifacts: {directory}")


def run_spy(scenario_name: str | None) -> None:
    check_tools("py-spy", "sudo", "uv")
    scenario = profiler_scenario(scenario_name)
    directory = result_dir("spy")
    venv = directory / "venv"
    subprocess.run(["uv", "venv", str(venv)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(["uv", "pip", "install", "--python", str(python), "-e", str(ROOT / "packages/slopvac-lint")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    parent = Path(tempfile.mkdtemp(prefix="scratch-", dir=directory))
    scratch = _prepare_scratch(str(python), parent)
    args = prepare_inputs(scenario, scratch)
    py_spy = resolve_tool("py-spy")
    if py_spy is None:
        raise RuntimeError("py-spy is not installed")
    print("py-spy uses sudo and may prompt for your password.", flush=True)
    try:
        # The scratch venv holds only slopvac; py-spy lives in the profile group,
        # so pass its resolved absolute path (sudo's secure_path would not find it).
        run_profiled(["sudo", py_spy, "record", "--idle", "-f", "speedscope", "-o", str(directory / "spy.json"), "--", str(python), "-m", "slopvac.cli", *args], scenario, python=str(python), cwd=scratch)
    finally:
        shutil.rmtree(parent, ignore_errors=True)
        finish_metadata(directory)
    print(f"py-spy speedscope profile: {directory / 'spy.json'}")


def build_ref(ref: str, directory: Path, venv: Path) -> str:
    commit = git_output("rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}")
    source = directory / f"source-{len(list(directory.glob('source-*')))}"
    source.mkdir()
    archive = subprocess.Popen(["git", "archive", commit], cwd=ROOT, stdout=subprocess.PIPE)
    assert archive.stdout is not None
    extracted = subprocess.run(["tar", "-x", "-C", str(source)], stdin=archive.stdout, check=False)
    archive.stdout.close()
    if archive.wait() or extracted.returncode:
        raise RuntimeError(f"could not extract source for ref {ref!r}")
    subprocess.run(["uv", "venv", str(venv)], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(["uv", "pip", "install", "--python", str(python), str(source / "packages/slopvac-lint")], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return str(python)


def regression_table(base_results: list[dict[str, Any]], head_results: list[dict[str, Any]], ratio: float, delta_ms: float) -> tuple[str, bool]:
    base_by_name = {result["name"]: result for result in base_results}
    head_by_name = {result["name"]: result for result in head_results}
    rows = [
        "| Scenario | BASE mean | HEAD mean | Δ time | HEAD/BASE | BASE peak | HEAD peak | Δ memory | Status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    if base_by_name.keys() != head_by_name.keys():
        raise RuntimeError("BASE and HEAD hyperfine results contain different scenarios")
    flagged_any = False
    for name in sorted(base_by_name):
        base = base_by_name[name]["summary"]
        head = head_by_name[name]["summary"]
        base_time = base["time_wall_clock"]["mean"]
        head_time = head["time_wall_clock"]["mean"]
        base_memory = base["memory_peak_resident"]["mean"]
        head_memory = head["memory_peak_resident"]["mean"]
        ratio_text = "∞" if base_time == 0 and head_time > 0 else f"{head_time / base_time:.2f}x" if base_time else "1.00x"
        delta = (head_time - base_time) * 1000
        flagged = regression(base_time, head_time, ratio, delta_ms)
        flagged_any |= flagged
        status = "regression?" if flagged else "—"
        rows.append(
            f"| {name} | {base_time * 1000:.1f} ms | {head_time * 1000:.1f} ms | "
            f"{delta:+.1f} ms | {ratio_text} | {base_memory / 1024 / 1024:.1f} MiB | "
            f"{head_memory / 1024 / 1024:.1f} MiB | "
            f"{(head_memory - base_memory) / 1024 / 1024:+.1f} MiB | {status} |"
        )
    return "\n".join(rows), flagged_any


def run_check(base_ref: str, scenarios: list[dict[str, Any]], runs: int) -> None:
    check_tools("hyperfine", "uv")
    directory = result_dir("check")
    base_python = build_ref(base_ref, directory, directory / "venv-base")
    head_python = build_ref(git_output("rev-parse", "HEAD"), directory, directory / "venv-head")
    try:
        results = _run_hyperfine(scenarios, directory, runs=runs, base_python=base_python, head_python=head_python)
        base_results = [result for result in results if result["name"].startswith("BASE ")]
        head_results = [result for result in results if result["name"].startswith("HEAD ")]
        for result in base_results + head_results:
            result["name"] = result["name"][5:]
        ratio = float(os.environ.get("PERF_MAX_RATIO", "1.25"))
        delta_ms = float(os.environ.get("PERF_MIN_DELTA_MS", "50"))
        if ratio < 0 or delta_ms < 0:
            raise ValueError("PERF_MAX_RATIO and PERF_MIN_DELTA_MS must be non-negative")
        table, flagged = regression_table(base_results, head_results, ratio, delta_ms)
        (directory / "comparison.md").write_text(table + "\n", encoding="utf-8")
        print(f"Thresholds: ratio > {ratio:g} AND absolute wall-time delta > {delta_ms:g} ms (placeholders pending idle-host baselines).")
        print(table)
        if os.environ.get("PERF_FAIL") == "1" and flagged:
            raise SystemExit(1)
    finally:
        finish_metadata(directory)
    print(f"Regression comparison artifacts: {directory}")


def dispatch(action: str, scenarios: list[dict[str, Any]], args: argparse.Namespace) -> None:
    if action == "bench":
        run_bench(scenarios, args.runs)
    elif action == "import":
        run_import(args.scenario)
    elif action == "cpu":
        run_cpu(args.scenario)
    elif action == "scalene":
        run_scalene(args.scenario)
    elif action == "timeline":
        run_timeline(args.scenario)
    elif action == "mem":
        run_mem(args.scenario)
    elif action == "spy":
        run_spy(args.scenario)
    elif action == "lines":
        run_lines(args.scenario)
    elif action == "check":
        base = args.base or git_output("describe", "--tags", "--abbrev=0")
        run_check(base, scenarios, args.runs)
    elif action == "all":
        run_bench(scenarios, args.runs)
        run_import(args.scenario)
        run_cpu(args.scenario)
        run_scalene(args.scenario)
        run_timeline(args.scenario)
        run_mem(args.scenario)
        run_spy(args.scenario)
    elif action == "run":
        if not args.scratch or not args.warm_cache:
            raise ValueError("run needs --scratch and --warm-cache")
        run_scenario(args.scenario or DEFAULT_SCENARIO, args.python, Path(args.scratch), Path(args.warm_cache))
    elif action == "wait-idle":
        directory = result_dir("wait-idle")
        wait_for_idle()
        finish_metadata(directory)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("wait-idle", "bench", "import", "cpu", "scalene", "timeline", "mem", "spy", "lines", "check", "all", "run", "prepare-cache"))
    parser.add_argument("extra", nargs="*")
    parser.add_argument("--scenario", default=os.environ.get("PERF_SCENARIO"), help="Exact scenario name in scripts/perf/scenarios.toml")
    parser.add_argument("--base", default=os.environ.get("PERF_BASE"), help="BASE revision for pre-release comparison")
    parser.add_argument("--runs", type=int, default=int(os.environ.get("PERF_RUNS", "15")))
    parser.add_argument("--python", default=sys.executable, help=argparse.SUPPRESS)
    parser.add_argument("--scratch", help=argparse.SUPPRESS)
    parser.add_argument("--warm-cache", help=argparse.SUPPRESS)
    parser.add_argument("--idle-checked", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")
    vale = resolve_tool("vale", "PERF_VALE")
    if os.environ.get("PERF_VALE") and vale:
        # slopvac finds Vale on PATH, so an explicit PERF_VALE must lead it.
        os.environ["PATH"] = os.path.dirname(vale) + os.pathsep + os.environ.get("PATH", "")
    try:
        if args.action == "prepare-cache":
            if len(args.extra) != 1:
                parser.error("prepare-cache needs exactly one path")
            cache_path = Path(args.extra[0])
            if cache_path.exists():
                shutil.rmtree(cache_path)
            cache_path.mkdir(parents=True, mode=0o700)
            return 0
        if args.action == "wait-idle":
            dispatch(args.action, [], args)
            return 0
        scenarios = load_scenarios()
        if args.scenario and args.action in {"bench", "check", "all", "import", "cpu", "scalene", "timeline", "mem", "spy", "lines"}:
            filter_scenarios(scenarios, args.scenario)
            if args.action in {"bench", "check", "all"}:
                scenarios = filter_scenarios(scenarios, args.scenario)
        if args.action in {"bench", "check", "all", "import", "cpu", "scalene", "timeline", "mem", "spy", "lines"} and not args.idle_checked and os.environ.get("PERF_SKIP_IDLE") != "1":
            wait_for_idle()
        dispatch(args.action, scenarios, args)
    except SystemExit:
        raise
    except (OSError, RuntimeError, ValueError, TimeoutError, subprocess.CalledProcessError) as error:
        print(f"perf: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
