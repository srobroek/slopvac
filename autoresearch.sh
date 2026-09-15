#!/bin/sh
set -eu

# Invoke the fixed online benchmark. `--smoke` runs one non-holdout case against
# one arm: `--smoke-arm <id>` names it, and the default is the arm confirmed
# callable on this account. `--run-dir <path>` chooses where the redacted
# stdout, stderr and session evidence for each request is retained.
exec "${PYTHON:-python3}" "$(dirname "$0")/autoresearch.py" "$@"
