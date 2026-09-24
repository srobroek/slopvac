"""Project-local agent steering for slopvac.

The managed block stays small. Detailed lint and judgement guidance comes from
the installed CLI through slopvac prime, so harness instructions do not duplicate
the rule catalogue or drift with the implementation.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

BEGIN = "<!-- slopvac:begin -->"
END = "<!-- slopvac:end -->"

_HARNESS_PATHS = {
    "agents": "AGENTS.md",
    "codex": "AGENTS.md",
    "omp": ".omp/AGENTS.md",
    "kiro": ".kiro/steering/slopvac.md",
    "claude": "CLAUDE.md",
}

STEERING_BLOCK = """\
<!-- slopvac:begin -->
## Slopvac

Before writing or reviewing prose, run `slopvac prime` and follow the current
CLI guidance. Use `slopvac prime judgement` for contextual model review.
Use `slopvac rules` and `slopvac explain <rule_id>` for rule details and
named exceptions.

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

JUDGEMENT_PRIME = """\
# Slopvac judgement guidance

Judgement rules are contextual and do not change deterministic lint pass/fail.
The CLI prepares and validates the work; the harness or provider makes model
calls. Contextual review still depends on available evidence. A provider prompt
cannot fetch repository files, citations, or external sources by itself: verify
those claims with the harness's tools, or abstain when the required evidence is
not present.

1. Prepare an agent-readable run:
   `slopvac judgement brief <paths> --out .slopvac-judgement --packs fired`
   Use `--packs all` when contextual review must not depend on deterministic
   findings.
2. Dispatch each call from `brief.json` or `prompts.jsonl` using the supplied
   system prompt, user payload, and response schema.
3. Validate every response before appending it:
   `slopvac judgement validate --run .slopvac-judgement --file response.json`
4. Aggregate responses:
   `slopvac judgement finish --out .slopvac-judgement --responses .slopvac-judgement/responses.jsonl`
5. Compare deterministic and judgement results:
   `slopvac judgement compare --out .slopvac-judgement`

`validate` checks response structure and expected results. `finish` performs
host evidence checks and coverage accounting. Check failed, truncated, and
not-run units before interpreting a report with no confirms.
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

Run `slopvac init` for generic `AGENTS.md` steering, or
`slopvac setup --list` and `slopvac setup <harness>` for a harness-specific
target. The managed block stays intentionally small.

Run `slopvac prime` whenever you need the current detailed lint and judgement
workflow. Use `slopvac prime lint` or `slopvac prime judgement` for one layer.
"""

def prime_text(topic: str) -> str:
    if topic == "lint":
        return LINT_PRIME
    if topic == "judgement":
        return JUDGEMENT_PRIME
    if topic == "all":
        return LINT_PRIME.rstrip() + "\n\n" + JUDGEMENT_PRIME
    raise ValueError(f"unknown prime topic: {topic}")
