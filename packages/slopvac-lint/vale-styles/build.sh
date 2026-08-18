#!/usr/bin/env bash
# Package each style directory as a Vale package zip.
#
# Vale's package format: a zip whose single top-level entry is a directory named
# after the style, containing only rule .yml files plus an optional meta.json.
# The directory name becomes the style name, so `BasedOnStyles = prose-agency`
# resolves rules as `prose-agency.FalseAgency`.
#
# Usage: build.sh [outdir]     (default: dist/)
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
outdir="${1:-$here/dist}"

command -v zip >/dev/null 2>&1 || {
  echo "build: zip not found on PATH" >&2
  exit 2
}

rm -rf "$outdir"
mkdir -p "$outdir"

built=0
for dir in "$here"/*/; do
  style="$(basename "$dir")"
  [ "$style" = "dist" ] && continue
  # A style with no rules would sync successfully and lint nothing, so refuse it.
  count="$(find "$dir" -maxdepth 1 -name '*.yml' | wc -l | tr -d ' ')"
  if [ "$count" -eq 0 ]; then
    echo "build: $style has no .yml rules" >&2
    exit 1
  fi
  (cd "$here" && zip -q -r "$outdir/$style.zip" "$style" -x '*.bak')
  echo "built $style.zip ($count rules)"
  built=$((built + 1))
done

[ "$built" -gt 0 ] || {
  echo "build: no style directories found" >&2
  exit 1
}
echo "$built package(s) in $outdir"
