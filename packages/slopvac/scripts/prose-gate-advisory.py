#!/usr/bin/env python3
"""PostToolUse hook: run the prose gate on edited prose files, report findings.

WHAT IT DOES
  1. Parses the tool payload and collects the file paths this edit wrote.
  2. Drops anything the gate does not cover, and anything git ignores.
  3. Accumulates changed-line and file counts per repo, staying silent until the
     work is worth interrupting for, then applies a cooldown.
  4. Runs slop-lint.sh and returns its findings as additionalContext, naming the
     review-docs skill for the register judgement the linter cannot make.

It reports findings rather than asking the agent to invoke the skill: a hook can
only request a skill, which is the unreliable path this hook replaces.

MISSING TOOLS ARE LOUD. A silent skip leaves prose ungated while the hook reports
success, so an absent vale, an unsynced styles directory, or a JSX edit without
ast-grep returns a PROSE GATE UNAVAILABLE block naming what went unchecked. Exit
is always 0: a PreToolUse guard may block, a PostToolUse advisory must not
(constitution III).

NOT RUN ASYNC. The whole return value is additionalContext, which the harness
reads from stdout synchronously; backgrounding the work discards the findings.
Cost is controlled by exiting early instead, in the order the checks are cheap.

PYTHON, NOT SHELL. The shell version spawned nine jq processes plus git and cost
212ms on every non-prose edit -- a tax on ordinary code editing, since the matcher
fires on every Write/Edit. One Python process does the same work in ~44ms and
reaches the extension test before spawning anything at all.

Cross-harness: Claude Code (file_path), Codex (apply_patch patch body), and Kiro
(path) all deliver PostToolUse with a tool_input payload and read
hookSpecificOutput.additionalContext.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Surfaces the gate covers. JSON and YAML are here for i18n locale files, where
# shipped UI copy lives.
PROSE_EXT = (".md", ".mdx", ".html", ".json", ".yaml", ".yml", ".tsx", ".jsx")
JSX_EXT = (".tsx", ".jsx")
STYLES = ("ai-tells", "ai-residue", "prose-agency", "prose-inflation",
          "docs-discipline", "prose-format")
# Vendored and generated trees are not authored prose. git check-ignore covers
# most of these, but apm_modules/ and node_modules/ are not always ignored, and
# this test costs nothing.
SKIP_DIRS = ("/node_modules/", "/apm_modules/", "/dist/", "/build/",
             "/.venv/", "/vale/styles/", "/.git/")
PATCH_TARGET = re.compile(r"^\*\*\* (?:Update|Add) File: (.+)$", re.M)
INTERNAL = re.compile(r"/(specs|adr|ADR)/|CONTRIBUTING|constitution")


def emit(context: str) -> None:
    """Return additionalContext to the harness and exit successfully."""
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": context,
    }}, sys.stdout)
    sys.stdout.write("\n")
    raise SystemExit(0)


def candidate_paths(tool_input: object) -> list[str]:
    """Every file path the tool call wrote, across all three harnesses."""
    if isinstance(tool_input, str):  # legacy string payload
        return PATCH_TARGET.findall(tool_input)
    if not isinstance(tool_input, dict):
        return []

    found = []
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            found.append(value)
    for key in ("edits", "files"):
        for item in tool_input.get(key) or []:
            if isinstance(item, dict):
                value = item.get("file_path") or item.get("path")
                if isinstance(value, str) and value:
                    found.append(value)
    # Codex apply_patch: the patch body names its own targets.
    for key in ("command", "patch", "input"):
        value = tool_input.get(key)
        if isinstance(value, str) and "*** " in value:
            found.extend(PATCH_TARGET.findall(value))
    return found


def changed_line_count(tool_input: object, fallback: int) -> int:
    if not isinstance(tool_input, dict):
        return fallback
    total = 0
    for key in ("content", "new_string"):
        value = tool_input.get(key)
        if isinstance(value, str):
            total += value.count("\n") + 1
    for item in tool_input.get("edits") or []:
        if isinstance(item, dict) and isinstance(item.get("new_string"), str):
            total += item["new_string"].count("\n") + 1
    return total or fallback


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_input = payload.get("tool_input")

    # Cheapest test first: nothing below runs for an ordinary code edit.
    prose = []
    for path in candidate_paths(tool_input):
        if not path.endswith(PROSE_EXT):
            continue
        if any(part in path for part in SKIP_DIRS):
            continue
        prose.append(path)
    if not prose:
        return 0

    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not os.path.isdir(cwd):
        cwd = os.getcwd()

    # One git call resolves the repo root and doubles as the "is this a repo"
    # test. Everything after this point is prose work, so the spawn is earned.
    try:
        repo_root = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or cwd
    except (OSError, subprocess.SubprocessError):
        repo_root = cwd

    # Respect .gitignore: a generated or untracked-by-design file is not prose
    # anyone reviews. One batched call for every candidate, not one per file.
    # check-ignore exits 0 when at least one path is ignored and prints those.
    absolute = [p if os.path.isabs(p) else os.path.join(cwd, p) for p in prose]
    try:
        ignored = set(subprocess.run(
            ["git", "-C", repo_root, "check-ignore", "--stdin"],
            input="\n".join(absolute), capture_output=True, text=True, timeout=5,
        ).stdout.split("\n"))
        prose = [p for p, a in zip(prose, absolute) if a not in ignored]
    except (OSError, subprocess.SubprocessError):
        pass  # No git, or check-ignore unavailable: lint everything.
    prose = [p for p in prose if os.path.isfile(p)]
    if not prose:
        return 0

    # Locate the gate. The hook and the skill land in different trees depending
    # on how the package was deployed, and the two are not siblings:
    #   installed:  <root>/hooks/slopvac/scripts/  ->  <root>/skills/review-docs/...
    #   source:     packages/slopvac/scripts/      ->  .../.apm/skills/review-docs/...
    # So walk up from this script and look for either shape at each level, rather
    # than guessing a fixed number of `..` hops.
    here = Path(__file__).resolve().parent
    tail = Path("skills") / "review-docs" / "scripts" / "slop-lint.sh"
    lint = None
    for parent in [here, *here.parents][:6]:
        for candidate in (parent / tail, parent / ".apm" / tail):
            if candidate.is_file():
                lint = candidate
                break
        if lint:
            break
    if lint is None:
        emit("PROSE GATE UNAVAILABLE: the review-docs slop-lint.sh script was not "
             "found next to this hook, so edited prose is NOT being checked. "
             "Reinstall: `apm install slopvac@slopvac`.")
    lint = lint.resolve()
    vale_dir = lint.parent.parent / "vale"

    if shutil.which("vale") is None:
        emit(f"PROSE GATE UNAVAILABLE: `vale` is not on PATH, so the prose edited "
             f"in this session is NOT being checked. Install it: `mise use -g vale` "
             f"(or `brew install vale`), then `vale --config='{vale_dir}/.vale.ini' "
             f"sync`. Until then apply the write-docs rules by hand, and say in your "
             f"report that the gate did not run.")

    # No style is committed. An unsynced directory makes Vale report a clean file
    # for rules it cannot resolve -- the exact failure this check prevents.
    absent = [s for s in STYLES if not (vale_dir / "styles" / s).is_dir()]
    if absent:
        emit(f"PROSE GATE UNAVAILABLE: Vale styles are not synced (missing: "
             f"{' '.join(absent)}), so edited prose is NOT being checked -- an "
             f"unsynced style reports every file as clean. Run: "
             f"`vale --config='{vale_dir}/.vale.ini' sync`")

    jsx_warning = ""
    if any(p.endswith(JSX_EXT) for p in prose) and shutil.which("ast-grep") is None:
        jsx_warning = (" WARNING: a .tsx/.jsx file was edited but `ast-grep` is not "
                       "on PATH, so its JSX text was NOT checked. Install it: "
                       "`mise use -g ast-grep` (or `brew install ast-grep`).")

    # --- Throttle ------------------------------------------------------------
    # The gate is cheap (~0.3s) but an advisory per keystroke-sized edit is noise.
    digest = hashlib.md5(repo_root.encode()).hexdigest()  # noqa: S324 - cache key
    state = Path(tempfile.gettempdir()) / f"slopvac-prose-{digest}"
    try:
        state.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    files_state, lines_state, last_state = (
        state / "files", state / "lines", state / "last")

    def read_int(path: Path) -> int:
        try:
            return int(path.read_text().strip())
        except (OSError, ValueError):
            return 0

    seen = set()
    try:
        seen = {ln for ln in files_state.read_text().split("\n") if ln}
    except OSError:
        pass
    seen.update(prose)

    total = read_int(lines_state) + changed_line_count(tool_input, len(prose) * 10)
    try:
        files_state.write_text("\n".join(sorted(seen)))
        lines_state.write_text(str(total))
    except OSError:
        return 0

    line_threshold = int(os.environ.get("SLOPVAC_ADVISORY_LINES", "120"))
    file_threshold = int(os.environ.get("SLOPVAC_ADVISORY_FILES", "5"))
    cooldown = int(os.environ.get("SLOPVAC_ADVISORY_COOLDOWN_SECONDS", "300"))

    if total < line_threshold and len(seen) < file_threshold:
        return 0
    now = int(time.time())
    if now - read_int(last_state) < cooldown:
        return 0

    to_lint = sorted(p for p in seen if os.path.isfile(p))
    try:
        last_state.write_text(str(now))
        files_state.write_text("")
        lines_state.write_text("0")
    except OSError:
        pass
    if not to_lint:
        return 0

    genre = "internal" if any(INTERNAL.search(p) for p in to_lint) else "consumer"
    try:
        result = subprocess.run(
            ["bash", str(lint), "--genre", genre, *to_lint],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        emit("PROSE GATE: the linter timed out after 60s, so this batch was NOT "
             "checked. Run it directly on the edited files to see why.")
    except OSError as exc:
        emit(f"PROSE GATE UNAVAILABLE: could not run the linter ({exc}). Edited "
             f"prose is NOT being checked.")

    findings = (result.stdout + result.stderr).strip()
    if not findings:
        return 0

    emit(f"PROSE GATE ({len(findings.splitlines())} finding(s) across "
         f"{len(to_lint)} edited file(s), genre: {genre}):\n{findings}\n\n"
         f"Fix every ERROR. Fix or justify each WARNING in one line. Then invoke "
         f"the review-docs skill for what the linter cannot judge: structural "
         f"symmetry, uniform paragraph mass, and claims with nothing measured "
         f"behind them.{jsx_warning}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        pass
