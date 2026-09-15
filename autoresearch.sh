#!/bin/sh
set -eu

# The offline deterministic benchmark is the default. Prefix with `--online`
# to use the retained online runner; all following options are forwarded.
exec "${PYTHON:-python3}" "$(dirname "$0")/autoresearch.py" "$@"
