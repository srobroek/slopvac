set shell := ["bash", "-cu"]

# Wait for a normal system load before measuring.
perf-wait-idle:
    uv run --group profile python scripts/perf/perf.py wait-idle

# Benchmark all scenarios or the selected SCENARIO; retain Hyperfine exports.
perf-bench $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py bench --idle-checked

# Profile Python import time; PERF_OPEN=1 opens Tuna interactively.
perf-import $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py import --idle-checked

# Capture a pyinstrument text and HTML profile.
perf-cpu $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py cpu --idle-checked

# Capture Scalene JSON and its CLI rendering.
perf-scalene $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py scalene --idle-checked

# Capture a VizTracer JSON timeline.
perf-timeline $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py timeline --idle-checked

# Capture Memray stats and an HTML flamegraph.
perf-mem $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py mem --idle-checked

# Record py-spy speedscope output with sudo (may prompt for a password).
perf-spy $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py spy --idle-checked

# Run the benchmark and all profilers in sequence after one idle gate.
perf $SCENARIO="": perf-wait-idle
    PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py all --idle-checked

# Compare BASE and HEAD in one interleaved run; report unless PERF_FAIL=1.
# Pass `BASE=<ref>` and `SCENARIO=<name>` in either order; a bare first value is BASE.
perf-check $BASE="" $SCENARIO="": perf-wait-idle
    #!/usr/bin/env bash
    set -euo pipefail
    base="" scenario=""
    for value in "$BASE" "$SCENARIO"; do
        case "$value" in
            BASE=*) base="${value#BASE=}" ;;
            SCENARIO=*) scenario="${value#SCENARIO=}" ;;
            "") ;;
            *) if [ -z "$base" ]; then base="$value"; else scenario="$value"; fi ;;
        esac
    done
    PERF_BASE="$base" PERF_SCENARIO="$scenario" uv run --group profile python scripts/perf/perf.py check --idle-checked
