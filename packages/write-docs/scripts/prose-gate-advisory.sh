#!/usr/bin/env bash
# Hook: PostToolUse -- run the prose gate over edited prose files and report the
# findings back to the agent.
#
# WHAT IT DOES
#   1. Reads the tool payload and collects the files this edit touched.
#   2. Keeps the ones the gate covers (markdown, MDX, HTML, JSON/YAML locale
#      files, and JSX/TSX, whose text nodes are extracted by ast-grep).
#   3. Accumulates changed-line and file counts in a per-repo state directory and
#      stays silent until the work is worth interrupting for, then applies a
#      cooldown so a long editing run gets one advisory, not twenty.
#   4. Runs scripts/slop-lint.sh and returns its findings as additionalContext,
#      naming the review-docs skill for the register judgement the gate cannot do.
#
# WHY FINDINGS AND NOT A NUDGE: a hook cannot invoke a skill, only ask the model
# to. Asking is the unreliable path this hook exists to replace, so it runs the
# gate itself and hands over `file:line` findings, which are actionable on their
# own. The skill pointer rides along for what the patterns cannot reach.
#
# TOOL PREREQUISITES ARE LOUD. A silent skip would mean prose ships ungated while
# the hook reports success, so a missing `vale`, an unsynced styles directory, or
# a JSX edit with no `ast-grep` emits a WARNING block naming the install command.
# The hook still exits 0 -- a PreToolUse guard may block, a PostToolUse advisory
# must not (constitution III) -- but it never fails quietly.
#
# Cross-harness: Claude Code and Kiro both deliver PostToolUse with a
# `tool_input` payload and both read `hookSpecificOutput.additionalContext`. Kiro
# names the file-writing tools differently, so the file extraction below accepts
# every known key rather than matching on tool name.
set -uo pipefail

payload="$(cat 2>/dev/null || true)"

# jq absent: emit a plain-text warning rather than dying silently. Every later
# step needs it, so there is nothing to fall back to.
if ! command -v jq >/dev/null 2>&1; then
  echo "prose-gate: jq not found; prose files edited in this session are NOT being checked." >&2
  echo "  install: mise use -g jq   (or: brew install jq)" >&2
  exit 0
fi

here="$(cd "$(dirname "$0")" && pwd)"
# Installed layout puts the skill beside this package's scripts/ directory; the
# source tree nests it under .apm/skills/. Try both.
lint=""
for candidate in \
  "$here/../skills/review-docs/scripts/slop-lint.sh" \
  "$here/../.apm/skills/review-docs/scripts/slop-lint.sh" \
  "$here/../../skills/review-docs/scripts/slop-lint.sh"; do
  [ -f "$candidate" ] && lint="$candidate" && break
done

cwd="$(printf '%s' "$payload" | jq -r '.cwd // empty' 2>/dev/null || true)"
[ -n "$cwd" ] && [ -d "$cwd" ] || cwd="$PWD"
repo_root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$repo_root" ] || repo_root="$cwd"

# Collect every file path this tool call touched. Covers Write/Edit
# (`file_path`), MultiEdit (`edits[]`), Kiro's `path`, and apply_patch, whose
# payload is a patch body listing its own targets.
# Portability floor is bash 3.2 (stock macOS), so no `mapfile`.
candidates=()
while IFS= read -r line; do
  [ -n "$line" ] && candidates+=("$line")
done < <(
  printf '%s' "$payload" | jq -r '
    [ .tool_input.file_path?,
      .tool_input.path?,
      .tool_input.notebook_path?,
      (.tool_input.edits[]?.file_path?),
      (.tool_input.files[]?.path?)
    ] | .[] | select(. != null and . != "")
  ' 2>/dev/null || true
  printf '%s' "$payload" | jq -r '
    (if (.tool_input | type) == "string" then .tool_input
     else (.tool_input.command // .tool_input.patch // .tool_input.input // "") end)
  ' 2>/dev/null | sed -nE 's/^\*\*\* (Update|Add) File: (.*)$/\2/p'
)

prose=()
for file in ${candidates[@]+"${candidates[@]}"}; do
  case "$file" in
    *.md | *.mdx | *.html | *.json | *.yaml | *.yml | *.tsx | *.jsx) ;;
    *) continue ;;
  esac
  # A generated or vendored file is not authored prose.
  case "$file" in
    */node_modules/* | */apm_modules/* | */dist/* | */.venv/* | */styles/ai-tells/*) continue ;;
  esac
  [ -f "$file" ] && prose+=("$file")
done

[ "${#prose[@]}" -gt 0 ] || exit 0

emit() {
  jq -n --arg ctx "$1" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: $ctx
    }
  }'
  exit 0
}

if [ -z "$lint" ]; then
  emit "PROSE GATE UNAVAILABLE: the review-docs slop-lint.sh script was not found next to this hook, so edited prose is NOT being checked. Reinstall the write-docs package (\`apm install write-docs@srobroek-agentic\`)."
fi

vale_dir="$(cd "$(dirname "$lint")/../vale" 2>/dev/null && pwd || true)"

if ! command -v vale >/dev/null 2>&1; then
  emit "PROSE GATE UNAVAILABLE: \`vale\` is not on PATH, so the prose files edited in this session are NOT being checked. Install it now: \`mise use -g vale\` (or \`brew install vale\`), then run \`vale --config='${vale_dir:-<skill>/vale}/.vale.ini' sync\`. Until then, apply the write-docs rules by hand and say in your report that the gate did not run."
fi

# No style is committed; an unsynced directory makes Vale report a clean file for
# rules it cannot resolve, which is the failure this check exists to prevent.
missing_styles=()
for style in ai-tells ai-residue prose-agency prose-inflation docs-discipline prose-format; do
  [ -d "${vale_dir:-/nonexistent}/styles/$style" ] || missing_styles+=("$style")
done
if [ "${#missing_styles[@]}" -gt 0 ]; then
  emit "PROSE GATE UNAVAILABLE: Vale styles are not synced (missing: ${missing_styles[*]}), so edited prose is NOT being checked -- an unsynced style reports every file as clean. Run: \`vale --config='${vale_dir}/.vale.ini' sync\`"
fi

jsx_edited=false
for file in "${prose[@]}"; do
  case "$file" in *.tsx | *.jsx) jsx_edited=true ;; esac
done
astgrep_warning=""
if [ "$jsx_edited" = true ] && ! command -v ast-grep >/dev/null 2>&1; then
  astgrep_warning=" WARNING: a .tsx/.jsx file was edited but \`ast-grep\` is not on PATH, so its JSX text was NOT checked -- install it with \`mise use -g ast-grep\` (or \`brew install ast-grep\`)."
fi

# --- Throttle -----------------------------------------------------------------
# Only past this point does the hook consider firing. The gate is cheap (~0.3s)
# but an advisory on every keystroke-sized edit is noise, so accumulate first.
changed_lines="$(
  printf '%s' "$payload" | jq -r '
    [ .tool_input.content?,
      .tool_input.new_string?,
      (.tool_input.edits[]?.new_string?)
    ] | map(select(. != null)) | join("\n")
  ' 2>/dev/null | wc -l | tr -d ' '
)"
[ "$changed_lines" -gt 0 ] 2>/dev/null || changed_lines=$(( ${#prose[@]} * 10 ))

repo_hash="$(printf '%s' "$repo_root" | { md5sum 2>/dev/null || md5 -q 2>/dev/null; } | awk '{print $1}')"
[ -n "$repo_hash" ] || exit 0
state_dir="${TMPDIR:-/tmp}/write-docs-prose-advisory-$repo_hash"
mkdir -p "$state_dir" 2>/dev/null || exit 0
files_state="$state_dir/files"
lines_state="$state_dir/lines"
last_state="$state_dir/last"

printf '%s\n' "${prose[@]}" >> "$files_state" 2>/dev/null || true
sort -u "$files_state" -o "$files_state" 2>/dev/null || true

previous=0
[ -f "$lines_state" ] && previous="$(cat "$lines_state" 2>/dev/null || echo 0)"
case "$previous" in '' | *[!0-9]*) previous=0 ;; esac
total=$(( previous + changed_lines ))
printf '%s\n' "$total" > "$lines_state"

file_count="$(wc -l < "$files_state" | tr -d ' ')"
line_threshold="${WRITE_DOCS_ADVISORY_LINES:-120}"
file_threshold="${WRITE_DOCS_ADVISORY_FILES:-5}"
cooldown="${WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS:-300}"

if [ "$total" -lt "$line_threshold" ] && [ "$file_count" -lt "$file_threshold" ]; then
  exit 0
fi

now="$(date +%s)"
last=0
[ -f "$last_state" ] && last="$(cat "$last_state" 2>/dev/null || echo 0)"
case "$last" in '' | *[!0-9]*) last=0 ;; esac
[ $(( now - last )) -lt "$cooldown" ] && exit 0

# --- Run the gate -------------------------------------------------------------
existing=()
while IFS= read -r file; do
  [ -n "$file" ] && [ -f "$file" ] && existing+=("$file")
done < "$files_state"

printf '%s\n' "$now" > "$last_state"
: > "$files_state"
printf '0\n' > "$lines_state"

[ "${#existing[@]}" -gt 0 ] || exit 0

# Genre: a path under specs/ or an ADR directory is internal, everything else
# consumer. The gate's own section globs do the finer routing per file.
genre=consumer
for file in "${existing[@]}"; do
  case "$file" in
    */specs/* | */adr/* | */ADR/* | *CONTRIBUTING* | *constitution*) genre=internal ;;
  esac
done

findings="$(bash "$lint" --genre "$genre" "${existing[@]}" 2>&1)"
status=$?

if [ "$status" -eq 0 ] && [ -z "$findings" ]; then
  exit 0
fi

count="$(printf '%s\n' "$findings" | grep -c . || true)"
emit "PROSE GATE (${count} finding(s) across ${#existing[@]} edited file(s), genre: ${genre}):
${findings}

Fix every ERROR. Fix or justify each WARNING in one line. Then invoke the review-docs skill for the register judgement the linter cannot make -- structural symmetry, uniform paragraph mass, and claims with nothing measured behind them.${astgrep_warning}"
