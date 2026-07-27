#!/usr/bin/env python3
"""Generate the rule reference from the rule files themselves.

Usage:
  gen-rule-table.py --check          exit 1 if any managed block is stale
  gen-rule-table.py                  rewrite the managed blocks in place

Every rule's one-line summary is its FIRST comment line, and its level and check
type come from the YAML. Nothing is duplicated by hand, so a rule cannot ship
with a stale description: `--check` runs in CI and fails the build when a rule
file and the docs disagree.

The blocks it owns are delimited, and everything outside them is left alone:

    <!-- BEGIN GENERATED: <block> -->
    ...replaced...
    <!-- END GENERATED: <block> -->
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

STYLES = Path(__file__).resolve().parent
REPO = STYLES.parent

# Style -> what it is for. The only prose in this script, because a style has no
# file of its own to carry a comment.
BLURBS = {
    "ai-residue": "Assistant output pasted into a shipped document",
    "prose-agency": "Prose with the actor deleted",
    "prose-inflation": "Claims inflated past their evidence",
    "prose-scope": "Over-writing: real content in the wrong document",
    "docs-discipline": "Documentation describing something other than the released artifact",
    "prose-format": "Formatting tells",
    "prose-craft": "Writing craft: wordiness, structure, and mechanics, in any register",
    "prose-inclusive": "Language that excludes a reader who could otherwise use the doc",
    "prose-density": "Prose too dense to read in one pass",
}

# Which axis each style sits on. A gate that treats craft as evidence of
# generation is making a claim it cannot support, so the table says which is which.
AXIS = {
    "ai-residue": "slop",
    "prose-agency": "slop",
    "prose-inflation": "slop",
    "prose-scope": "slop",
    "docs-discipline": "slop",
    "prose-format": "slop",
    "prose-craft": "craft",
    "prose-inclusive": "craft",
    "prose-density": "craft",
}

BEGIN = "<!-- BEGIN GENERATED: {} -->"
END = "<!-- END GENERATED: {} -->"


def summary(path: Path) -> str:
    """The rule's first comment line, minus the leading `# `."""
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped in ("---", ""):
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        break
    return ""


def load(path: Path) -> dict:
    # A rule with a `---` document separator inside a comment block parses as
    # multi-document YAML, so take the first document rather than failing.
    docs = [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
    return docs[0] if docs else {}


def rules() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for style in sorted(d.name for d in STYLES.iterdir() if d.is_dir() and d.name != "dist"):
        found = []
        for rule in sorted((STYLES / style).glob("*.yml")):
            data = load(rule)
            found.append(
                {
                    "name": rule.stem,
                    "level": data.get("level", "suggestion"),
                    "extends": data.get("extends", "?"),
                    "scope": data.get("scope", "text"),
                    "summary": summary(rule),
                }
            )
        if found:
            out[style] = found
    return out


def styles_table(data: dict[str, list[dict]]) -> str:
    lines = ["| Style | Axis | Rules | Catches |", "|---|---|---|---|"]
    for style, found in data.items():
        names = ", ".join(f"`{r['name']}`" for r in found)
        lines.append(
            f"| `{style}` | {AXIS.get(style, '?')} | {names} | "
            f"{BLURBS.get(style, '')} |"
        )
    return "\n".join(lines)


def rules_table(data: dict[str, list[dict]]) -> str:
    lines = ["| Rule | Level | Check | What it catches |", "|---|---|---|---|"]
    for style, found in data.items():
        for r in found:
            scope = "" if r["scope"] == "text" else f" ({r['scope']})"
            lines.append(
                f"| `{style}.{r['name']}` | {r['level']} | "
                f"{r['extends']}{scope} | {r['summary']} |"
            )
    return "\n".join(lines)


def counts(data: dict[str, list[dict]]) -> str:
    total = sum(len(v) for v in data.values())
    slop = sum(len(v) for k, v in data.items() if AXIS.get(k) == "slop")
    craft = total - slop
    return (
        f"{total} rules across {len(data)} styles. {slop} sit on the slop axis "
        f"and gate at error. {craft} sit on the craft axis and warn."
    )


BLOCKS = {
    "styles-table": styles_table,
    "rules-table": rules_table,
    "rule-counts": counts,
}


def apply(path: Path, data: dict, write: bool) -> bool:
    """Replace every managed block. Returns True when the file is already current."""
    original = path.read_text()
    updated = original
    for block, render in BLOCKS.items():
        begin, end = BEGIN.format(block), END.format(block)
        # `[\s\S]*?` rather than `.*?\n`: an empty block is two adjacent marker
        # lines with nothing between them, and a pattern demanding a body line
        # silently skips it -- which reads exactly like "already current".
        pattern = re.compile(
            re.escape(begin) + r"[\s\S]*?" + re.escape(end)
        )
        if not pattern.search(updated):
            continue
        body = render(data)
        updated = pattern.sub(f"{begin}\n{body}\n{end}", updated)
    if updated == original:
        return True
    if write:
        path.write_text(updated)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="report staleness, write nothing")
    args = parser.parse_args()

    data = rules()
    targets = [REPO / "README.md", STYLES / "README.md"]
    stale = []
    for target in targets:
        if not target.is_file():
            continue
        if not apply(target, data, write=not args.check):
            stale.append(target.relative_to(REPO))

    if args.check:
        if stale:
            print("rule tables are stale: " + ", ".join(map(str, stale)), file=sys.stderr)
            print("run: ./vale-styles/gen-rule-table.py", file=sys.stderr)
            return 1
        print("rule tables current")
        return 0

    if stale:
        print("updated " + ", ".join(map(str, stale)))
    else:
        print("rule tables already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
