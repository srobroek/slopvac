#!/bin/sh
set -eu

# Keep the harness offline and invoke the installed source tree's production CLI
# through autoresearch.py; no Vale/network access is required for Phase 1.
exec "${PYTHON:-python3}" "$(dirname "$0")/autoresearch.py"
