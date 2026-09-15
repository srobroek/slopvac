#!/bin/sh
set -eu

# Invoke the fixed online benchmark; --smoke runs one arm and one case.
exec "${PYTHON:-python3}" "$(dirname "$0")/autoresearch.py" "$@"
