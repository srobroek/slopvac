#!/bin/sh
set -eu

run_dir=${SLOPVAC_JUDGEMENT_RUN:-.slopvac-judgement}
exec uvx slopvac judgement validate --run "$run_dir" --hook
