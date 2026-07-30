#!/usr/bin/env bash
# Prose gate. Runs Vale against the WriteDocs house style plus the pinned
# vale-ai-tells package.
#
# Usage: slop-lint.sh [--genre consumer|change|internal] <file> [<file>...]
# Exit:  0 clean (warnings alone stay 0) · 1 any error · 2 usage or missing tool.
#
# The exit contract is this script's own, not Vale's: Vale exits non-zero on any
# alert at or above MinAlertLevel, which would fail on warnings too. We read the
# JSON and map severities ourselves.
#
# Genre selects the config, it does not filter. Per-path rules live in the
# section globs of vale/.vale.ini, which Vale applies from each file's own path.
# `--genre change` exists because commit messages and PR bodies have no stable
# path for a section glob to match.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
vale_dir="$here/../vale"
genre=""
files=()

while [ $# -gt 0 ]; do
  case "$1" in
    --genre)
      genre="${2:-}"
      case "$genre" in
        consumer | change | internal) ;;
        *)
          echo "slop-lint: --genre must be consumer, change, or internal" >&2
          exit 2
          ;;
      esac
      shift 2
      ;;
    -h | --help)
      sed -n '2,15p' "$0"
      exit 0
      ;;
    -*)
      echo "slop-lint: unknown option $1" >&2
      exit 2
      ;;
    *)
      files+=("$1")
      shift
      ;;
  esac
done

if [ "${#files[@]}" -eq 0 ]; then
  echo "slop-lint: no files given" >&2
  exit 2
fi

if ! command -v vale >/dev/null 2>&1; then
  echo "slop-lint: vale not found on PATH." >&2
  echo "  install: mise use -g vale   (or: brew install vale)" >&2
  echo "  then:    vale --config='$vale_dir/.vale.ini' sync" >&2
  exit 2
fi

# Project override. A repo that wants a different rule set puts a `.vale.ini` at
# its root (or sets SLOP_LINT_CONFIG) and it wins outright. Without this the
# packaged config below is passed with --config, which suppresses Vale's own
# upward search, so a project file would sit there being ignored.
#
# The project config is the whole configuration, not a patch: Vale has no include
# or extends directive, verified. `scripts/init-vale.sh` scaffolds one carrying
# every measured exclusion, so a project changes one line rather than authoring
# 140. The packaged config below is the fallback for a repo that has not run it.
config=""
if [ -n "${SLOP_LINT_CONFIG:-}" ]; then
  if [ ! -f "$SLOP_LINT_CONFIG" ]; then
    echo "slop-lint: SLOP_LINT_CONFIG is set but not a file: $SLOP_LINT_CONFIG" >&2
    exit 2
  fi
  config="$SLOP_LINT_CONFIG"
else
  # Walk up from the first target, the way Vale would.
  probe="$(cd "$(dirname "${files[0]}")" 2>/dev/null && pwd || echo "$PWD")"
  while [ -n "$probe" ] && [ "$probe" != "/" ]; do
    if [ -f "$probe/.vale.ini" ]; then
      config="$probe/.vale.ini"
      break
    fi
    probe="$(dirname "$probe")"
  done
fi

if [ -z "$config" ]; then
  config="$vale_dir/.vale.ini"
  if [ "$genre" = "change" ] && [ -f "$vale_dir/.vale-change.ini" ]; then
    config="$vale_dir/.vale-change.ini"
  fi
fi

if [ ! -f "$config" ]; then
  echo "slop-lint: config not found at $config" >&2
  exit 2
fi

# Every style is fetched by `vale sync`; none is committed. Vale reports a clean
# file for a style it cannot resolve, so a missing or partial sync looks exactly
# like a passing run. Check each style the RESOLVED config asks for, against that
# config's own StylesPath, which a project config may point elsewhere.
styles_path="$(sed -n 's/^StylesPath *= *//p' "$config" | head -1)"
styles_path="${styles_path:-styles}"
case "$styles_path" in
  /*) ;;
  *) styles_path="$(dirname "$config")/$styles_path" ;;
esac
missing=()
for style in $(sed -n 's/^BasedOnStyles *= *//p' "$config" | tr ',' ' ' | sort -u); do
  [ -d "$styles_path/$style" ] || missing+=("$style")
done
if [ "${#missing[@]}" -gt 0 ]; then
  echo "slop-lint: styles not synced (${missing[*]}). Run:" >&2
  echo "  vale --config='$config' sync" >&2
  exit 2
fi

# JSX and TSX have no Vale parser, so their text nodes are extracted to shadow
# files first and linted in place of the source. The shadow keeps each string on
# its original line, and vale-report.py rewrites the shadow path back to the
# source path, so reported positions match the real file.
#
# Missing ast-grep is not fatal: every other file still lints, and
# extract-prose.sh has already printed the install hint on stderr.
lint_files=()
shadow_map=()
jsx_files=()
for file in "${files[@]}"; do
  case "$file" in
    *.tsx | *.jsx) jsx_files+=("$file") ;;
    *) lint_files+=("$file") ;;
  esac
done

if [ "${#jsx_files[@]}" -gt 0 ]; then
  while read -r src shadow; do
    [ -n "${shadow:-}" ] || continue
    lint_files+=("$shadow")
    shadow_map+=("$shadow=$src")
  done < <("$here/extract-prose.sh" "${jsx_files[@]}" || true)
fi

if [ "${#lint_files[@]}" -eq 0 ]; then
  exit 0
fi

vale --config="$config" --output=JSON --no-exit "${lint_files[@]}" 2>/dev/null |
  python3 "$here/vale-report.py" ${shadow_map[@]+"${shadow_map[@]}"}
rc=$?

for entry in ${shadow_map[@]+"${shadow_map[@]}"}; do
  rm -f "${entry%%=*}"
done

exit "$rc"
