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

config="$vale_dir/.vale.ini"
if [ "$genre" = "change" ] && [ -f "$vale_dir/.vale-change.ini" ]; then
  config="$vale_dir/.vale-change.ini"
fi

if [ ! -f "$config" ]; then
  echo "slop-lint: config not found at $config" >&2
  exit 2
fi

# Every style is fetched by `vale sync`; none is committed. A missing sync leaves
# Vale with rules it cannot resolve, which it reports as a clean file, so check
# for each expected style directory rather than trusting a zero exit.
missing=()
for style in ai-tells ai-residue prose-agency prose-inflation docs-discipline prose-format; do
  [ -d "$vale_dir/styles/$style" ] || missing+=("$style")
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
