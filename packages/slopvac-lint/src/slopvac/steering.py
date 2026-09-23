"""Install a small, CLI-owned section in a project's agent instructions."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt

BEGIN = "<!-- slopvac:begin -->"
END = "<!-- slopvac:end -->"
HARNESS_PATHS = {
    "generic": "AGENTS.md",
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "omp": "AGENTS.md",
    "kiro": ".kiro/steering/slopvac.md",
}

STEERING = """## Slopvac documentation checks

Use `slopvac` when writing or reviewing documentation and source comments.
Run `slopvac prime` for the workflow, or `slopvac prime lint` and
`slopvac prime judgement` for details. Reload this guidance after compaction.

Run the linter with Vale available. An incomplete check is not a pass.
Use `slopvac explain <rule-id>` for rule details and permitted exceptions.
For requested contextual review, use the CLI's judgement prompts and validation.
Check factual accuracy and task completeness against source evidence separately;
report anything you could not verify. Keep the deterministic result separate
from model judgements. Do not weaken project settings to obtain a pass.
"""


class SteeringError(ValueError):
    """Unsafe target or ambiguous managed section."""


@dataclass(frozen=True)
class Edit:
    path: Path
    before: bytes | None
    after: bytes

    @property
    def changed(self) -> bool:
        return self.before != self.after


def snippet() -> str:
    return f"{BEGIN}\n{STEERING}{END}\n"


def safe_target(root: Path, relative: str) -> Path:
    """Follow aliases only within the explicitly selected project."""
    root = root.resolve()
    try:
        target = (root / relative).resolve()
        parts = target.relative_to(root).parts
    except (OSError, RuntimeError, ValueError) as exc:
        raise SteeringError(f"unsafe steering target: {relative}") from exc
    if ".git" in parts or target.suffix.lower() != ".md":
        raise SteeringError(f"steering target must be a project Markdown file: {target}")
    if target.exists() and not target.is_file():
        raise SteeringError(f"not a regular file: {target}")
    return target


def _section(text: str) -> tuple[int, int] | None:
    """Locate written markers, ignoring copies shown inside code fences."""
    quoted: set[int] = set()
    for token in MarkdownIt().parse(text):
        if token.type in {"fence", "code_block"} and token.map:
            quoted.update(range(*token.map))
    found: list[tuple[str, int, int]] = []
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True)):
        if number not in quoted:
            value = line.strip().lstrip("\ufeff")
            if value in {BEGIN, END}:
                start = offset + (1 if line.startswith("\ufeff") else 0)
                found.append((value, start, offset + len(line)))
        offset += len(line)
    if not found:
        return None
    if len(found) != 2 or [entry[0] for entry in found] != [BEGIN, END]:
        raise SteeringError("ambiguous Slopvac markers; repair the begin/end pair first")
    return found[0][1], found[1][2]


def harness_target(root: Path, harness: str) -> Path:
    """Prefer an existing instruction file that shadows the shared default."""
    alternative = {"codex": "AGENTS.override.md", "omp": ".omp/AGENTS.md"}.get(harness)
    if alternative:
        candidate = safe_target(root, alternative)
        if candidate.exists() and candidate.read_bytes().strip():
            return candidate
    return safe_target(root, HARNESS_PATHS[harness])


def plan_steering(root: Path, harnesses: tuple[str, ...], *, remove: bool = False) -> list[Edit]:
    edits: dict[Path, Edit] = {}
    for harness in harnesses:
        target = harness_target(root, harness)
        if target in edits:
            continue
        before = target.read_bytes() if target.exists() else None
        if before is None and remove:
            continue
        try:
            text = (before or b"").decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SteeringError(f"steering must be UTF-8: {target}") from exc
        section = _section(text)
        match = re.search(r"\r\n|\n|\r", text)
        newline = match.group() if match else "\n"
        block = "" if remove else snippet().replace("\n", newline)
        if section:
            updated = text[:section[0]] + block + text[section[1]:]
        elif remove:
            updated = text
        else:
            prefix = text
            if not prefix and harness == "kiro":
                prefix = "---\ninclusion: always\n---\n\n".replace("\n", newline)
            if prefix and not prefix.endswith(newline * 2):
                prefix += newline if prefix.endswith(newline) else newline * 2
            updated = prefix + block
        edits[target] = Edit(target, before, updated.encode("utf-8"))
    return list(edits.values())


def apply_edits(edits: list[Edit]) -> None:
    """Preflight all files, then replace each changed file atomically."""
    for edit in edits:
        actual = edit.path.read_bytes() if edit.path.exists() else None
        if actual != edit.before:
            raise SteeringError(f"file changed during setup; retry: {edit.path}")
    for edit in edits:
        if not edit.changed:
            continue
        edit.path.parent.mkdir(parents=True, exist_ok=True)
        mode = edit.path.stat().st_mode & 0o777 if edit.before is not None else 0o644
        fd, name = tempfile.mkstemp(prefix=".slopvac-", dir=edit.path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(edit.after)
            os.chmod(name, mode)
            os.replace(name, edit.path)
        finally:
            Path(name).unlink(missing_ok=True)
