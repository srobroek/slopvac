"""Project-local agent steering for slopvac.

The managed block stays small. Detailed lint guidance comes from the installed
CLI through slopvac prime, so harness instructions do not duplicate the rule
catalogue or drift with the implementation.

Harnesses that load project skills also get one thin `slopvac-prose` skill. It
carries triggers only and points at `slopvac prime write|review`, for the same
reason: the guidance itself is generated from the installed catalogue.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

from .config import GuidanceSettings
from .guidance import prime_section

BEGIN = "<!-- slopvac:begin -->"
END = "<!-- slopvac:end -->"

_HARNESS_PATHS = {
    "agents": "AGENTS.md",
    "codex": "AGENTS.md",
    "omp": ".omp/AGENTS.md",
    "kiro": ".kiro/steering/slopvac.md",
    "claude": "CLAUDE.md",
}

SKILL_NAME = "slopvac-prose"

# Project skill directories, each from the harness's own documentation:
#   claude  https://code.claude.com/docs/en/skills  (.claude/skills/<name>/SKILL.md)
#   codex   https://developers.openai.com/codex/skills  (.agents/skills, scanned
#           from the working directory up to the repository root)
#   kiro    https://kiro.dev/docs/skills  (.kiro/skills; name must match the folder)
#   omp     https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md
# The generic `agents` target has no skill convention, so it gets none.
_SKILL_DIRS = {
    "codex": ".agents/skills",
    "omp": ".omp/skills",
    "kiro": ".kiro/skills",
    "claude": ".claude/skills",
}

# Identifies the stub as ours, so init and setup never overwrite or delete a
# hand-written skill that happens to share the path. Ownership is an exact marker
# line; when the wording changes, keep the old line in _KNOWN_SKILL_MARKERS so
# installed stubs stay manageable.
SKILL_MARKER = "<!-- slopvac:managed; slopvac init or slopvac setup rewrites this file -->"
_KNOWN_SKILL_MARKERS = frozenset({SKILL_MARKER})


def _has_skill_marker(text: str) -> bool:
    """True when the line right after the frontmatter is a known marker."""
    lines = [line.rstrip("\r") for line in text.split("\n")]
    if not lines or lines[0] != "---":
        return False
    try:
        close = lines.index("---", 1)
    except ValueError:
        return False
    return close + 1 < len(lines) and lines[close + 1] in _KNOWN_SKILL_MARKERS

# Every harness above matches a skill to a request by its `description`, and each
# documents the same recipe: front-load the use case and the words a request
# would contain, under the Agent Skills 1024-character limit. Nothing here sets
# `disable-model-invocation`, `hide`, or `enabled`, which would stop automatic use.
SKILL_STUB = f"""\
---
name: {SKILL_NAME}
description: >-
  Use when writing, editing, or reviewing prose: README files, documentation,
  Markdown pages, PR or MR descriptions, commit messages, release notes, and
  specifications. Run before drafting such text and again before handing it
  off, even when the user does not mention slopvac.
---
{SKILL_MARKER}

# Slopvac prose

Before drafting or editing a README, documentation, a Markdown page, a PR or
MR description, a commit message, release notes, or a specification, run
`slopvac prime write` and follow it.

Before handing that prose off, run `slopvac prime review` and follow it.
"""

STEERING_BLOCK = """\
<!-- slopvac:begin -->
## Slopvac

Before writing or reviewing prose, run `slopvac prime` and follow the current
CLI guidance. Use `slopvac rules` and `slopvac explain <rule_id>` for rule
details and named exceptions.

Treat lint exit 2 as incomplete. Vale 3.15 or later is optional but highly
recommended for full deterministic coverage.
<!-- slopvac:end -->
"""

LINT_PRIME = """\
# Slopvac lint guidance

- Run `slopvac lint <paths> --format json` against the project configuration.
- Treat exit 0 as a completed pass, exit 1 as a threshold failure, and exit 2 as
  an incomplete or invalid run. Do not report exit 2 as clean.
- Vale 3.15 or later is optional but highly recommended because most checked
  rules route through Vale. Inspect `documents[].unchecked` in JSON output.
- Use `slopvac rules` to inspect the active catalogue and
  `slopvac explain <rule_id>` for rationale, examples, fixes, and named
  suppression reasons.
- Fix prose before changing policy. Use only suppression reasons listed by
  `slopvac explain`; report unexplained false positives instead of inventing
  exceptions.
- `slopvac --fix <paths>` applies only deterministic, unambiguous
  replacements. Review the resulting diff.
- Linting does not prove factual correctness. Verify commands, paths, defaults,
  versions, and behavioral claims against the implementation or another
  authoritative source.
- For consumer documentation, describe shipped behavior and reader actions.
  Remove superseded features, implementation chronology, repository archaeology,
  rejected alternatives, and internal tradeoffs unless the reader needs one to
  operate or verify the artifact. Keep deltas in change communications and
  rationale in decision records.
- Apply a deletion test before polishing: if a paragraph, list item, table row,
  or sentence changes no reader action or understanding of the current contract,
  remove it.
- Use `strict` for reference/procedural material, `normal` for READMEs,
  guides, internal docs, and change communications, and `relaxed` for informal
  prose. These profiles do not replace factual verification.
"""


class SteeringError(ValueError):
    """Unsafe target or ambiguous managed steering."""


def _safe_target(root: Path, relative: str) -> Path:
    """Resolve a harness target and refuse aliases that escape the project."""
    project = root.resolve()
    try:
        target = (project / relative).resolve()
        parts = target.relative_to(project).parts
    except (OSError, RuntimeError, ValueError) as exc:
        raise SteeringError(f"unsafe steering target: {relative}") from exc
    if ".git" in parts or target.suffix.lower() != ".md":
        raise SteeringError(
            f"steering target must be a project Markdown file: {target}"
        )
    if target.exists() and not target.is_file():
        raise SteeringError(f"not a regular file: {target}")
    return target


def _section(text: str) -> tuple[int, int] | None:
    """Locate managed markers while ignoring copies shown in fenced code."""
    fenced: set[int] = set()
    for token in MarkdownIt().parse(text):
        if token.type in {"fence", "code_block"} and token.map:
            fenced.update(range(*token.map))
    found: list[tuple[str, int, int]] = []
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True)):
        if number not in fenced:
            value = line.strip().lstrip("\ufeff")
            if value in {BEGIN, END}:
                start = offset + (1 if line.startswith("\ufeff") else 0)
                found.append((value, start, offset + len(line)))
        offset += len(line)
    if not found:
        return None
    if len(found) != 2 or [entry[0] for entry in found] != [BEGIN, END]:
        raise SteeringError(
            "malformed or ambiguous slopvac markers; repair the begin/end pair first"
        )
    return found[0][1], found[1][2]


def _newline(text: str) -> str:
    match = re.search(r"\r\n|\n|\r", text)
    return match.group() if match else "\n"


def _native_newlines(value: str, newline: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)


def _atomic_write(path: Path, before: bytes | None, after: bytes) -> bool:
    """Replace one steering file atomically after checking it did not move."""
    if before == after:
        return False
    actual = path.read_bytes() if path.exists() else None
    if actual != before:
        raise SteeringError(f"file changed during setup; retry: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if before is not None else 0o644
    fd, name = tempfile.mkstemp(prefix=".slopvac-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(after)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    return True


def harness_path(root: Path, harness: str) -> Path:
    """Return the effective steering file for a supported harness."""
    try:
        relative = _HARNESS_PATHS[harness]
    except KeyError as exc:
        raise ValueError(f"unknown harness: {harness}") from exc
    if harness == "codex":
        override = _safe_target(root, "AGENTS.override.md")
        if override.exists() and override.read_bytes().strip():
            return override
    return _safe_target(root, relative)


def harnesses() -> tuple[str, ...]:
    return tuple(_HARNESS_PATHS)


def install_steering(root: Path, harness: str) -> tuple[Path, bool]:
    """Write one harness's managed block. Returns the target and whether it changed.

    Kiro loads a steering file only when its front matter says how; a new file
    gets `inclusion: always` so the block is read on every request.
    """
    target = harness_path(root, harness)
    preamble = (
        "---\ninclusion: always\n---" if harness == "kiro" and not target.exists() else ""
    )
    return target, update_managed_block(target, preamble=preamble)


def skill_path(root: Path, harness: str) -> Path | None:
    """The `slopvac-prose` skill file for a harness, or None when it has none."""
    if harness not in _HARNESS_PATHS:
        raise ValueError(f"unknown harness: {harness}")
    directory = _SKILL_DIRS.get(harness)
    if directory is None:
        return None
    return _safe_target(root, f"{directory}/{SKILL_NAME}/SKILL.md")


def skill_state(path: Path, wanted: bool = True) -> str:
    """Return missing, current, stale, malformed, or disabled for the skill stub.

    `wanted` is False when `[guidance]` turns both modes off: an absent stub is
    then `disabled`, and a present one is `stale` because setup would remove it.
    A file without the managed marker is `malformed`: it is not ours to touch.
    """
    if not path.exists():
        return "missing" if wanted else "disabled"
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return "malformed"
    if not _has_skill_marker(text):
        return "malformed"
    if not wanted:
        return "stale"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "current" if normalized == SKILL_STUB else "stale"


def _owned_skill(path: Path) -> bytes | None:
    """The stub's bytes, or None when absent. Refuses a file slopvac did not write."""
    if not path.exists():
        return None
    before = path.read_bytes()
    try:
        owned = _has_skill_marker(before.decode("utf-8"))
    except UnicodeDecodeError:
        owned = False
    if not owned:
        raise SteeringError(
            f"{path} is not a slopvac-managed skill; move it aside to install the stub"
        )
    return before


def sync_skill(path: Path, wanted: bool = True) -> bool:
    """Write the stub when wanted, remove it when not. Returns whether it changed.

    Removal deletes only the stub file, then its `slopvac-prose` directory when
    nothing else is left in it.
    """
    before = _owned_skill(path)
    if wanted:
        return _atomic_write(path, before, SKILL_STUB.encode("utf-8"))
    if before is None:
        return False
    if path.read_bytes() != before:
        raise SteeringError(f"file changed during setup; retry: {path}")
    path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass  # not empty: the directory holds files slopvac did not write
    return True


def managed_block_state(path: Path, block: str = STEERING_BLOCK) -> str:
    """Return missing, current, stale, or malformed for one managed block."""
    if not path.exists():
        return "missing"
    try:
        text = path.read_bytes().decode("utf-8")
        section = _section(text)
    except (UnicodeDecodeError, SteeringError):
        return "malformed"
    if section is None:
        return "missing"
    start, end = section
    installed = text[start:end].strip()
    expected = block.strip()
    normalized = installed.replace("\r\n", "\n").replace("\r", "\n")
    return "current" if normalized == expected else "stale"


def update_managed_block(
    path: Path,
    block: str = STEERING_BLOCK,
    *,
    preamble: str = "",
) -> bool:
    """Insert or replace the managed block without touching surrounding text."""
    before = path.read_bytes() if path.exists() else None
    try:
        text = (before or b"").decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SteeringError(f"steering must be UTF-8: {path}") from exc
    section = _section(text)
    newline = _newline(text)
    native_block = _native_newlines(block.rstrip("\r\n"), newline) + newline

    if section is not None:
        start, end = section
        updated = text[:start] + native_block + text[end:]
    else:
        prefix = text.rstrip("\r\n")
        if not prefix and preamble:
            prefix = _native_newlines(preamble.rstrip("\r\n"), newline)
        updated = (prefix + newline * 2 if prefix else "") + native_block

    return _atomic_write(path, before, updated.encode("utf-8"))


def remove_managed_block(path: Path) -> bool:
    """Remove only the slopvac block and preserve the surrounding instructions."""
    if not path.exists():
        return False
    before = path.read_bytes()
    try:
        text = before.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SteeringError(f"steering must be UTF-8: {path}") from exc
    section = _section(text)
    if section is None:
        return False
    start, end = section
    newline = _newline(text)
    left = text[:start].rstrip("\r\n")
    right = text[end:].lstrip("\r\n")
    if left and right:
        updated = left + newline * 2 + right
    elif left:
        updated = left + newline
    else:
        updated = right
    return _atomic_write(path, before, updated.encode("utf-8"))


ONBOARD_TEXT = """\
# Slopvac agent setup

Run `slopvac init` for generic `AGENTS.md` steering. Add `--harness <name>`,
once per harness, to write that harness's steering and its `slopvac-prose`
skill instead. `slopvac setup --list` names the harnesses, and
`slopvac setup <harness>` installs one into an existing project. The managed
block stays intentionally small.

Run `slopvac prime` whenever you need the current detailed lint workflow.
"""


def prime_text(settings: GuidanceSettings) -> str:
    """Base prime: the lint workflow plus the configured writing and review steps."""
    return LINT_PRIME + prime_section(settings)
