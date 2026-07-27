#!/usr/bin/env bash
# Extract JSX/TSX text nodes into a line-preserving shadow file the prose gate
# can lint.
#
# Usage: extract-prose.sh <file.tsx|file.jsx> [<file>...]
# Exit:  0 wrote a shadow for every input (or an input had no prose) ·
#        2 usage error or ast-grep missing.
#
# Prints one `<original> <shadow>` pair per line for each file that produced
# prose, so a caller can lint the shadow and report the original path.
#
# Why this exists: Vale has no parser for .tsx/.jsx, and neither format alias
# works -- `tsx = html` errors out, `tsx = md` reports zero findings and exits 0.
# An alias would also defeat Vale's native comment scoping. So the prose is
# extracted by AST instead.
#
# The shadow is `.md` so it inherits the markdown ruleset -- a `.txt` shadow
# matched a different section and re-enabled rules disabled for prose.
#
# Prose is written FLUSH LEFT, not at its source column: 4+ leading spaces make
# Markdown treat a line as an indented code block, which Vale skips entirely.
# Blank lines still pad the shadow so every string keeps its original LINE
# number; only the reported column shifts, and vale-report.py drops columns.
set -euo pipefail

if [ $# -eq 0 ]; then
  echo "extract-prose: no files given" >&2
  echo "usage: extract-prose.sh <file.tsx|file.jsx> [<file>...]" >&2
  exit 2
fi

if ! command -v ast-grep >/dev/null 2>&1; then
  echo "extract-prose: ast-grep not found on PATH; JSX prose is NOT being checked." >&2
  echo "  install: mise use -g ast-grep   (or: brew install ast-grep)" >&2
  exit 2
fi

# jsx_text is the element body. The attribute arm covers copy that ships in an
# attribute: aria-label, alt, placeholder, title. className and event handlers
# are deliberately excluded.
read -r -d '' rule <<'RULE' || true
id: prose
language: tsx
rule:
  any:
    - kind: jsx_text
    - kind: jsx_attribute
      regex: '^(aria-label|aria-description|title|alt|placeholder|label|summary)='
RULE

for src in "$@"; do
  if [ ! -f "$src" ]; then
    echo "extract-prose: no such file: $src" >&2
    exit 2
  fi

  # Strip any trailing slash from TMPDIR: macOS sets it with one, and the
  # resulting `//` does not match the path Vale normalizes and reports back, so
  # the shadow-to-source rewrite in vale-report.py would silently miss.
  tmpdir="${TMPDIR:-/tmp}"
  shadow="${tmpdir%/}/$(basename "$src").prose.md"

  # `--json=compact` gives 0-based line/column for every match. A file with no
  # JSX prose yields an empty array, which the filter turns into no output.
  ast-grep scan --inline-rules "$rule" --json=compact "$src" 2>/dev/null |
    python3 -c '
import json, re, sys

try:
    matches = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    matches = []


def is_prose(text):
    """Keep human sentences; drop identifiers, paths, and module specifiers."""
    text = text.strip()
    if len(text) < 12 or len(text.split()) < 3:
        return False
    if re.fullmatch(r"[\w./@~-]+", text):
        return False
    return not text.startswith(("http://", "https://", "/"))


by_line = {}
for match in matches:
    text = match["text"].strip()
    # An attribute match arrives as `alt="..."`; keep only the quoted value.
    quoted = re.match(r"^[\w-]+=[\"\x27](.*)[\"\x27]$", text, re.S)
    if quoted:
        text = quoted.group(1).strip()
    if not is_prose(text):
        continue
    start = match["range"]["start"]
    by_line.setdefault(start["line"], []).append((start["column"], text))

if not by_line:
    sys.exit(0)

out = []
for line in range(max(by_line) + 1):
    if line in by_line:
        _, text = sorted(by_line[line])[0]
        out.append(" ".join(text.split()))
    else:
        out.append("")
sys.stdout.write("\n".join(out) + "\n")
' > "$shadow"

  if [ -s "$shadow" ]; then
    printf '%s %s\n' "$src" "$shadow"
  else
    rm -f "$shadow"
  fi
done
