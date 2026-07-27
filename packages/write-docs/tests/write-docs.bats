#!/usr/bin/env bats
# Tests for the write-docs SubagentStart doc-discipline injector.
# Portability floor: bash 3.2.57 + BSD coreutils (stock macOS).
# Run with: bats packages/write-docs/tests/write-docs.bats

setup() {
  SCRIPT="${BATS_TEST_DIRNAME}/../scripts/inject-doc-discipline.sh"
}

@test "inject: subagent payload yields valid JSON" {
  run bash "$SCRIPT" <<<'{"agent_id":"a1","agent_type":"general-purpose","cwd":"/whatever"}'
  [ "$status" -eq 0 ]
  echo "$output" | jq . >/dev/null
}

@test "inject: emits a SubagentStart hookSpecificOutput" {
  run bash "$SCRIPT" <<<'{"agent_id":"a1"}'
  [ "$status" -eq 0 ]
  echo "$output" | jq -e '.hookSpecificOutput.hookEventName == "SubagentStart"' >/dev/null
  echo "$output" | jq -e '.hookSpecificOutput.additionalContext | length > 0' >/dev/null
}

@test "inject: carries the discipline header, the skill-invocation rule, and the buried-task clause" {
  run bash "$SCRIPT" <<<'{"agent_id":"a1","agent_type":"coder","cwd":"/x"}'
  [ "$status" -eq 0 ]
  ctx="$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')"
  echo "$ctx" | grep -q "DOCUMENTATION DISCIPLINE" || { echo "no discipline header"; return 1; }
  echo "$ctx" | grep -q "Invoke the write-docs skill" || { echo "no skill-invocation rule"; return 1; }
  echo "$ctx" | grep -q "one step of a larger task" || { echo "no buried-task clause"; return 1; }
}

@test "inject: self-gates on the conditional documentation lead" {
  # The digest applies conditionally (unlike the universal working-style digest),
  # so a code-only subagent can harmlessly ignore it. The lead must state that.
  run bash "$SCRIPT" <<<'{"agent_id":"a1"}'
  [ "$status" -eq 0 ]
  ctx="$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')"
  echo "$ctx" | grep -q "applies when this task includes writing or reviewing any document" \
    || { echo "no conditional gate in lead"; return 1; }
}

@test "inject: carries the core MUST rules and NOT prohibitions" {
  run bash "$SCRIPT" <<<'{"agent_id":"a1"}'
  [ "$status" -eq 0 ]
  ctx="$(echo "$output" | jq -r '.hookSpecificOutput.additionalContext')"
  for rule in "MUST State what the artifact does" "MUST One idea per sentence" "MUST Consumer docs"; do
    echo "$ctx" | grep -q "$rule" || { echo "missing rule: $rule"; return 1; }
  done
  echo "$ctx" | grep -q "NOT Status language" || { echo "missing status-language prohibition"; return 1; }
  echo "$ctx" | grep -q "NOT Slop lexicon" || { echo "missing slop-lexicon prohibition"; return 1; }
}

@test "inject: non-subagent (no agent_id) exits silently" {
  run bash "$SCRIPT" <<<'{"cwd":"/whatever"}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "inject: malformed/empty stdin does not crash" {
  run bash "$SCRIPT" <<<''
  [ "$status" -eq 0 ]
}

# --- PostToolUse prose gate --------------------------------------------------
# Cross-harness: Claude sends Write/Edit with tool_input.file_path, Codex sends
# apply_patch with a patch body, Kiro sends fsWrite with tool_input.path. All
# three must reach the same file list.

setup_prose() {
  GATE="${BATS_TEST_DIRNAME}/../scripts/prose-gate-advisory.sh"
  WORK="$(mktemp -d)"
  cat > "$WORK/doc.md" <<'DOC'
# Guide

The library leverages a robust parser. The complaint becomes a fix.
DOC
  # Fire on the first edit so a test does not depend on accumulation.
  export WRITE_DOCS_ADVISORY_LINES=1
  export WRITE_DOCS_ADVISORY_FILES=1
  export WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS=0
}

ctx_for() {
  printf '%s' "$1" | bash "$GATE" | jq -r '.hookSpecificOutput.additionalContext // empty'
}

@test "prose gate: claude Write payload yields findings" {
  setup_prose
  command -v vale >/dev/null 2>&1 || skip "vale not installed"
  run ctx_for "{\"cwd\":\"$WORK\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$WORK/doc.md\",\"content\":\"x\"}}"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "PROSE GATE" || { echo "no gate output: $output"; return 1; }
  echo "$output" | grep -q "prose-agency.FalseAgency" || { echo "rule missing: $output"; return 1; }
}

@test "prose gate: codex apply_patch payload reaches the same file" {
  setup_prose
  command -v vale >/dev/null 2>&1 || skip "vale not installed"
  patch="*** Begin Patch
*** Update File: $WORK/doc.md
+leverages a robust parser
*** End Patch"
  payload="$(jq -n --arg p "$patch" --arg cwd "$WORK" \
    '{cwd:$cwd,tool_name:"apply_patch",tool_input:{command:$p}}')"
  run ctx_for "$payload"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "PROSE GATE" || { echo "no gate output: $output"; return 1; }
}

@test "prose gate: kiro fsWrite payload uses tool_input.path" {
  setup_prose
  command -v vale >/dev/null 2>&1 || skip "vale not installed"
  run ctx_for "{\"cwd\":\"$WORK\",\"tool_name\":\"fsWrite\",\"tool_input\":{\"path\":\"$WORK/doc.md\",\"content\":\"x\"}}"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "PROSE GATE" || { echo "no gate output: $output"; return 1; }
}

@test "prose gate: missing vale is loud, not silent" {
  setup_prose
  # A silent skip would leave prose ungated while the hook reports success.
  run env PATH=/usr/bin:/bin bash -c "printf '%s' '{\"cwd\":\"$WORK\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$WORK/doc.md\",\"content\":\"x\"}}' | bash '$GATE'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "UNAVAILABLE" || { echo "not loud: $output"; return 1; }
  echo "$output" | grep -q "NOT being checked" || { echo "no consequence stated: $output"; return 1; }
}

@test "prose gate: non-prose edits stay silent" {
  setup_prose
  printf 'fn main() {}\n' > "$WORK/main.rs"
  run ctx_for "{\"cwd\":\"$WORK\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$WORK/main.rs\",\"content\":\"x\"}}"
  [ "$status" -eq 0 ]
  [ -z "$output" ] || { echo "expected silence, got: $output"; return 1; }
}

@test "prose gate: clean prose stays silent" {
  setup_prose
  command -v vale >/dev/null 2>&1 || skip "vale not installed"
  printf '# Title\n\nThe parser rejects malformed input at startup.\n' > "$WORK/clean.md"
  run ctx_for "{\"cwd\":\"$WORK\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$WORK/clean.md\",\"content\":\"x\"}}"
  [ "$status" -eq 0 ]
  [ -z "$output" ] || { echo "expected silence, got: $output"; return 1; }
}

@test "prose gate: a tiny edit is throttled at default thresholds" {
  GATE="${BATS_TEST_DIRNAME}/../scripts/prose-gate-advisory.sh"
  WORK="$(mktemp -d)"
  printf '# T\n\nleverages a robust parser.\n' > "$WORK/doc.md"
  unset WRITE_DOCS_ADVISORY_LINES WRITE_DOCS_ADVISORY_FILES WRITE_DOCS_ADVISORY_COOLDOWN_SECONDS
  run bash -c "printf '%s' '{\"cwd\":\"$WORK\",\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$WORK/doc.md\",\"content\":\"one line\"}}' | bash '$GATE'"
  [ "$status" -eq 0 ]
  [ -z "$output" ] || { echo "expected throttled silence, got: $output"; return 1; }
}
