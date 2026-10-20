# Performance profiling and benchmarks

This local toolkit profiles Slopvac on developer machines. It does not add a CI job or block a release. Each command writes to `perf-results/<UTC timestamp>-<recipe>/`. Git ignores that directory. Each run writes `meta.json` with the Git revision, Slopvac and Python versions, OS, CPU count, start and end load, and tool paths and versions.

Install the Python profiling group. Install `uv` and Git. Install `tar` and
`env`. The toolkit also needs `just` and Hyperfine 2.x. Use the six profilers
in the group.
Mise can install `just` and Hyperfine 2.0.0. You can also use the host package
manager. The profiler group is not installed by the default sync. You do not
need mise or just to run the Python driver. Runtime commands do not download
tools from GitHub.

```sh
mise install
uv sync --group profile
just --list
```

On Amazon Linux 2023 aarch64, the idle gate reads `/proc/loadavg` and uses `nproc`. macOS reads the load from `sysctl -n vm.loadavg`. The gate waits until the one-minute load is below `ncpu * PERF_IDLE_RATIO`. The default ratio is `0.5`. It polls every 15 seconds and times out after 1800 seconds. Set `PERF_IDLE_RATIO` and `PERF_IDLE_TIMEOUT` to change these values. For a brief functional check only, use `PERF_SKIP_IDLE=1`. Do not use timings from a bypassed gate as a baseline.

Set `PERF_HYPERFINE` or `PERF_VALE` to an executable path when PATH selects the wrong version. By default, the driver uses `hyperfine` and `vale` on PATH. It records the resolved paths and `--version` output for these tools in `meta.json`. `perf-spy` runs `sudo py-spy` with the Python installed into its profiling venv. It may prompt for a password.

Hyperfine uses one warmup and 15 runs by default. Set `PERF_RUNS` to change the
count. The regression comparison benchmarks BASE and HEAD in one Hyperfine
invocation.

Scenario definitions live in `scripts/perf/scenarios.toml`. The stdlib-only
driver is `scripts/perf/perf.py`. For each run, it creates a scratch project.
It copies the fixture there, initializes git, and runs `slopvac init`. It
removes the project after the scenario ends.

The manifest covers startup commands. It also covers init and rules commands.
Lint cases use the fixture, package README, or docs. Some use Vale, others do
not. The suite also covers JSON and SARIF. Other cases cover cache states,
comments, and notifications. It skips Vale cases when Vale is missing. Results
may then be incomplete.

Select one scenario with `SCENARIO`:

```sh
PERF_SKIP_IDLE=1 PERF_RUNS=2 just perf-bench SCENARIO='startup --version'
```

## Recipes

`just --list` lists the recipes.

| Recipe | Use |
| --- | --- |
| `perf-wait-idle` | Wait for the host to meet the load threshold. |
| `perf-bench` | Benchmark all scenarios or the selected `SCENARIO`. Keep Hyperfine JSON and Markdown exports, including peak RSS. |
| `perf-import` | Capture `python -X importtime` for `slopvac.cli`. See the sorted top 20 cumulative times. Set `PERF_OPEN=1` to open Tuna. |
| `perf-cpu` | Write pyinstrument text and HTML profiles. |
| `perf-scalene` | Write Scalene JSON and `scalene view --cli` output. |
| `perf-timeline` | Write a VizTracer JSON timeline. Use the printed `vizviewer` command or open the trace in Perfetto. |
| `perf-mem` | Write Memray allocation stats and an HTML flamegraph. |
| `perf-spy` | Write a py-spy speedscope profile. The command uses sudo. |
| `perf-lines` | Write per-line timings for `FUNCS`, a space-separated list of `module:qualname` names such as `slopvac.analyze:_align_block_text`. line_profiler traces those functions wherever they are called, so the source needs no `@profile` decorator. |
| `perf` | Run the benchmark and each profiler after one idle gate. |
| `perf-check` | Build BASE and HEAD in temporary venvs. Hyperfine interleaves the revisions. A Markdown table reports timing and peak memory deltas. |

Use `hyperfine.json` to inspect individual runs and summary statistics, including peak RSS. `hyperfine.md` summarizes the primary metric. Import-time totals use microseconds. Pyinstrument and Scalene can help locate CPU work. Memray shows allocation behavior. VizTracer records event order for timeline inspection. Py-spy samples a running Python process. Each profiler adds overhead. Use profiles to choose code to inspect; use Hyperfine for timing comparisons.

All scenarios except `notifier enabled` set `NO_UPDATE_NOTIFIER=1`. The notifier case requires an interactive terminal to exercise update notices. A non-terminal invocation cannot display those notices.

## Pre-release regression comparison

Before merging a release PR, run the report on an idle host and inspect its Markdown table:

```sh
just perf-check
# Or specify the BASE revision:
just perf-check BASE=v2.14.0
```

The default BASE is the latest tag from `git describe --tags --abbrev=0`. Use `PERF_BASE` or the `BASE` argument to select a different commit or tag. The driver installs the package from both revisions. The table reports each revision's mean wall time and peak RSS, plus their deltas and the HEAD/BASE ratio.

The initial thresholds are `PERF_MAX_RATIO=1.25` and `PERF_MIN_DELTA_MS=50`. A row gets a `regression?` marker only when HEAD exceeds both thresholds. These defaults are placeholders. They are not validated release criteria because idle-host baselines do not exist yet. Repeat measurements on an idle machine before changing the defaults. By default, the comparison only reports. It exits successfully even when a row has a `regression?` marker. Set `PERF_FAIL=1` to exit with code 1 on a marked row. This remains an optional local choice. The comparison is not a release gate.

## Current measured facts

One earlier observation recorded `setup` at about 0.9 to 1.0 seconds wall time. Imports accounted for most of the time. The host load was unknown, so this is not a reliable baseline. Repeat the measurement on an idle host before drawing a conclusion.
