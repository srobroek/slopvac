set shell := ["bash", "-cu"]

# Dispatch stable publishing for an existing version tag; approve it in GitHub.
release VERSION:
    #!/usr/bin/env bash
    set -euo pipefail
    version={{quote(VERSION)}}
    if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "expected stable version X.Y.Z, got $version" >&2
        exit 2
    fi
    tag="v$version"
    if ! git ls-remote --exit-code --refs origin "refs/tags/$tag" >/dev/null; then
        echo "tag $tag does not exist on origin" >&2
        exit 1
    fi
    run_url="$(gh workflow run publish-lint.yml --ref "$tag" -f dry-run=false -f target=pypi)"
    printf '%s\nRun waits for the pypi environment approval.\n' "$run_url"

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

# Time each line of FUNCS (space-separated module:qualname) without decorators.
perf-lines $FUNCS $SCENARIO="": perf-wait-idle
    PERF_LINE_FUNCS="${FUNCS#FUNCS=}" PERF_SCENARIO="${SCENARIO#SCENARIO=}" uv run --group profile python scripts/perf/perf.py lines --idle-checked

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
