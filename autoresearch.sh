#!/bin/sh
set -eu

# Invoke the fixed online benchmark. All selector options are forwarded to the
# Python runner: `--partition screen|holdout`, `--one-unit`, `--arm <id>`, and
# `--repeats <n>`. `--smoke` remains the one-case exploratory screen shortcut;
# `--smoke-arm <id>` is its legacy exact-arm alias. `--run-dir <path>` chooses
# where the redacted stdout, stderr and session evidence for each request is retained.
exec "${PYTHON:-python3}" "$(dirname "$0")/autoresearch.py" "$@"
