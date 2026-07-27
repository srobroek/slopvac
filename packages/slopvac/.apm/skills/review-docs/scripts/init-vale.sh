#!/usr/bin/env bash
# Scaffold a project prose-gate config, then fetch the styles.
#
# Usage: init-vale.sh [--check] [<project-root>]
#   --check   report what is missing and exit; write nothing.
# Exit: 0 ready (or, with --check, nothing to do) · 1 needs a sync ·
#       2 missing tool, or no config and none written.
#
# The config belongs to the project, not to this package: Vale reads a single file
# with no include directive, and a project that cannot change a rule will turn the
# whole gate off. Every URL in the template points at a rolling release tag, so
# `vale sync` picks up new rules without touching this file.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
template="$here/../vale/vale.ini.template"
check_only=false
root=""

while [ $# -gt 0 ]; do
  case "$1" in
    --check) check_only=true; shift ;;
    -h | --help) sed -n '2,9p' "$0"; exit 0 ;;
    -*) echo "init-vale: unknown option $1" >&2; exit 2 ;;
    *) root="$1"; shift ;;
  esac
done

if [ -z "$root" ]; then
  root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
config="$root/.vale.ini"

if [ ! -f "$template" ]; then
  echo "init-vale: template not found at $template" >&2
  exit 2
fi

if [ "$check_only" = true ]; then
  if [ ! -f "$config" ]; then
    echo "no $config -- run: $0 '$root'"
    exit 2
  fi
  # Check every style the config asks for, not just that the directory exists. A
  # sync that fails partway leaves the styles it already fetched in place, and
  # Vale reports every file as clean for a style it cannot resolve -- so a partial
  # sync looks exactly like a passing run.
  styles="$(sed -n 's/^StylesPath *= *//p' "$config" | head -1)"
  styles="$root/${styles:-.vale-styles}"
  missing=()
  for style in $(sed -n 's/^BasedOnStyles *= *//p' "$config" | tr ',' ' ' | sort -u); do
    [ -d "$styles/$style" ] || missing+=("$style")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "styles not synced (${missing[*]}) -- run: vale --config='$config' sync"
    exit 1
  fi
  echo "prose gate ready: $config"
  exit 0
fi

if [ -f "$config" ]; then
  echo "init-vale: $config already exists; leaving it alone." >&2
  echo "  to take new upstream rules: vale --config='$config' sync" >&2
else
  cp "$template" "$config"
  echo "wrote $config"
  # The styles directory is fetched, not authored, so keep it out of git.
  ignore="$root/.gitignore"
  styles="$(sed -n 's/^StylesPath *= *//p' "$config" | head -1)"
  styles="${styles:-.vale-styles}"
  if [ -f "$ignore" ] && ! grep -qF "$styles" "$ignore"; then
    printf '\n# Vale styles are fetched by `vale sync`, not committed.\n%s/\n' \
      "$styles" >> "$ignore"
    echo "added $styles/ to .gitignore"
  fi
fi

if ! command -v vale >/dev/null 2>&1; then
  echo "init-vale: vale not found on PATH; config written but styles NOT fetched." >&2
  echo "  install: mise use -g vale   (or: brew install vale)" >&2
  echo "  then:    vale --config='$config' sync" >&2
  exit 2
fi

vale --config="$config" sync
echo "prose gate ready. Lint with: scripts/slop-lint.sh --genre consumer <file>"
