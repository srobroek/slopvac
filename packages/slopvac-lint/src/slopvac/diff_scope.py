"""Git hunk scopes for upstream/changed-line linting.

The first-party linter intentionally remains whole-document by default.  This
module provides the opt-in scope used by upstream integrations: Git supplies the
changed line intervals, while the normal parser and both engines still inspect
the complete current document.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .model import Finding, Rule, Scope

_HUNK = re.compile(
    r"^@@ -(?P<old>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new>\d+)(?:,(?P<new_count>\d+))? @@"
)


class DiffScopeError(RuntimeError):
    """A requested Git scope could not be determined reliably."""


@dataclass(frozen=True)
class ChangedFile:
    """One repository-relative file and its added-line intervals."""

    path: str
    ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class DiffScope:
    """A complete, validated hunk scope."""

    root: Path
    files: dict[Path, ChangedFile]
    mode: str
    base: str | None = None
    all_files: frozenset[Path] = frozenset()

    def ranges_for(self, path: Path) -> tuple[tuple[int, int], ...]:
        """Return added line intervals for ``path`` (inclusive, 1-based)."""
        resolved = path.resolve(strict=False)
        if resolved in self.all_files:
            return ((1, 2**31 - 1),)
        return self.files.get(resolved, ChangedFile("", ())).ranges

    def paths(self) -> set[Path]:
        return set(self.files) | set(self.all_files)

    def all_lines_for(self, path: Path) -> bool:
        """Whether every current line is in scope (an untracked new file)."""
        return path.resolve(strict=False) in self.all_files


def _safe_repo_path(root: Path, relative: str) -> Path:
    """Resolve a patch path without following a symlink or escaping root."""
    candidate = root / relative
    current = root
    for part in Path(relative).parts:
        current /= part
        if current.is_symlink():
            raise DiffScopeError(f"symlinked changed path is not supported: {relative}")
    resolved = candidate.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise DiffScopeError(f"changed path escapes Git root: {relative}")
    return resolved


def _run_git(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise DiffScopeError(f"could not run git: {exc}") from exc


def _git_root() -> Path:
    result = _run_git(["rev-parse", "--show-toplevel"])
    if result.returncode != 0 or not result.stdout.strip():
        detail = result.stderr.strip() or "not inside a Git repository"
        raise DiffScopeError(f"Git repository required: {detail}")
    return Path(result.stdout.strip()).resolve()


def _decode_path(value: str, prefix: str) -> str | None:
    """Decode one Git patch path without splitting on spaces in a filename."""
    value = value.rstrip("\r")
    if value == "/dev/null":
        return None
    if value.startswith('"') and value.endswith('"'):
        # Git's quoted path format uses C escapes.  Decode the octal bytes as
        # UTF-8 (with surrogateescape for a repository name Git cannot decode),
        # rather than turning each UTF-8 byte into a separate Unicode codepoint.
        body = value[1:-1]
        decoded = bytearray()
        index = 0
        escapes = {
            "\\": ord("\\"),
            '"': ord('"'),
            "a": 7,
            "b": 8,
            "f": 12,
            "n": 10,
            "r": 13,
            "t": 9,
            "v": 11,
        }
        while index < len(body):
            if body[index] != "\\":
                decoded.extend(body[index].encode("utf-8"))
                index += 1
                continue
            if index + 1 >= len(body):
                raise DiffScopeError("malformed quoted Git path")
            marker = body[index + 1]
            if marker in escapes:
                decoded.append(escapes[marker])
                index += 2
                continue
            octal = body[index + 1 : index + 4]
            if len(octal) != 3 or not re.fullmatch(r"[0-7]{3}", octal):
                raise DiffScopeError(f"ambiguous Git path escape: {value}")
            decoded.append(int(octal, 8))
            index += 4
        value = bytes(decoded).decode("utf-8", errors="surrogateescape")
    if not value.startswith(prefix):
        raise DiffScopeError(f"malformed Git path marker: {value}")
    return value[len(prefix) :]


def _parse_patch(patch: str, root: Path) -> dict[Path, ChangedFile]:
    """Parse added ranges from a complete ``git diff --unified=0`` patch.

    Git's patch format has enough metadata to distinguish a binary/rename-only
    section from malformed text.  Silently ignoring a truncated section would
    turn a requested changed-line check into a false clean result, so malformed
    headers and hunks fail closed.
    """
    found: dict[Path, tuple[str, list[tuple[int, int]]]] = {}
    current: str | None = None
    section = False
    old_seen = False
    new_seen = False
    binary = False
    rename_metadata = False
    saw_hunk = False
    hunk_body = False

    def finish_section() -> None:
        if saw_hunk and not hunk_body:
            raise DiffScopeError("malformed Git diff: hunk has no body")
        if section and not new_seen and not binary and not rename_metadata:
            raise DiffScopeError("malformed Git diff: file section has no new path")

    for line in patch.splitlines():
        if line.startswith("diff --git "):
            finish_section()
            section = True
            current = None
            old_seen = False
            new_seen = False
            binary = False
            rename_metadata = False
            saw_hunk = False
            continue
        if line.startswith("diff --"):
            raise DiffScopeError("ambiguous Git diff format")
        if not section:
            if line.strip():
                raise DiffScopeError("malformed Git diff: content before file header")
            continue
        if line.startswith("@@"):
            if not new_seen:
                raise DiffScopeError("malformed Git diff: hunk before file paths")
            if saw_hunk and not hunk_body:
                raise DiffScopeError("malformed Git diff: hunk has no body")
            match = _HUNK.match(line)
            if match is None:
                raise DiffScopeError(f"malformed Git hunk header: {line}")
            start = int(match.group("new"))
            count = int(match.group("new_count") or "1")
            if count < 0 or (count and start < 1):
                raise DiffScopeError(f"invalid Git hunk range: {line}")
            saw_hunk = True
            hunk_body = False
            if current is not None and count:
                found[_safe_repo_path(root, current)][1].append(
                    (start, start + count - 1)
                )
            continue
        if saw_hunk:
            if line.startswith("\\ No newline at end of file"):
                continue
            hunk_body = True
            # Once a hunk starts, all subsequent lines belong to its body until
            # the next file or hunk header. This prevents deleted `--- ...` and
            # added `+++ ...` content from being mistaken for file metadata.
            continue
        if line.startswith("\\ No newline at end of file"):
            if not saw_hunk:
                raise DiffScopeError("malformed Git diff: newline marker without hunk")
            continue
        if line.startswith("Binary files ") or line == "GIT binary patch":
            binary = True
            continue
        if line.startswith("rename from ") or line.startswith("rename to "):
            rename_metadata = True
            continue
        if line.startswith("--- "):
            if old_seen:
                raise DiffScopeError("malformed Git diff: duplicate old path")
            _decode_path(line[4:], "a/")
            old_seen = True
            continue
        if line.startswith("+++ "):
            if not old_seen or new_seen:
                raise DiffScopeError("malformed Git diff: misplaced new path")
            current = _decode_path(line[4:], "b/")
            new_seen = True
            if current is not None:
                path = _safe_repo_path(root, current)
                if path in found:
                    raise DiffScopeError(f"ambiguous Git diff: duplicate path {current}")
                found[path] = (current, [])
            continue
        # index/mode/rename/similarity metadata is not needed for intervals.
        continue

    finish_section()

    result: dict[Path, ChangedFile] = {}
    for path, (display, ranges) in found.items():
        if not ranges:
            continue
        merged: list[tuple[int, int]] = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        result[path] = ChangedFile(display, tuple(merged))
    return result


def changed_scope(*, base: str | None = None, working_tree: bool = False) -> DiffScope:
    """Resolve one explicit committed or working-tree scope.

    ``base`` compares ``base...HEAD``.  ``working_tree`` compares ``HEAD`` to
    the combined index and working tree, plus untracked files as all-line scope.
    """
    if (base is None) == (not working_tree):
        raise DiffScopeError("choose exactly one of --diff-base or --diff-working-tree")
    root = _git_root()
    if base is not None:
        revision = _run_git(["rev-parse", "--verify", f"{base}^{{commit}}"], cwd=root)
        if revision.returncode != 0:
            detail = revision.stderr.strip() or f"invalid Git revision: {base}"
            raise DiffScopeError(detail)
        diff_args = [
            "diff",
            "--no-ext-diff",
            "--no-color",
            "--unified=0",
            "--find-renames",
            f"{base}...HEAD",
            "--",
        ]
        mode = "diff-base"
    else:
        diff_args = [
            "diff",
            "--no-ext-diff",
            "--no-color",
            "--unified=0",
            "--find-renames",
            "HEAD",
            "--",
        ]
        mode = "diff-working-tree"
    diff = _run_git(diff_args, cwd=root)
    if diff.returncode != 0:
        detail = diff.stderr.strip() or "git diff failed"
        raise DiffScopeError(detail)
    all_files: frozenset[Path] = frozenset()
    if working_tree:
        untracked = _run_git(
            ["ls-files", "--others", "--exclude-standard", "-z"], cwd=root
        )
        if untracked.returncode != 0:
            detail = untracked.stderr.strip() or "git ls-files failed"
            raise DiffScopeError(detail)
        all_files = frozenset(
            _safe_repo_path(root, relative)
            for relative in untracked.stdout.split("\0")
            if relative
        )
    return DiffScope(
        root=root,
        files=_parse_patch(diff.stdout, root),
        mode=mode,
        base=base,
        all_files=all_files,
    )


def _span_lines(finding: Finding) -> tuple[int, int] | None:
    if finding.line < 1 or not finding.matched_text:
        return None
    return finding.line, finding.line + finding.matched_text.count("\n")


def _physical_span(finding: Finding, source: str) -> tuple[int, int] | None:
    """Map an analyzer match to raw source, rejecting normalized ambiguity."""
    if finding.line < 1 or finding.column < 1 or not finding.matched_text:
        return None
    lines = source.splitlines(keepends=True)
    if finding.line > len(lines):
        return None
    offset = sum(len(line) for line in lines[: finding.line - 1]) + finding.column - 1
    end = offset + len(finding.matched_text)
    if source[offset:end] != finding.matched_text:
        return None
    return finding.line, finding.line + finding.matched_text.count("\n")


def finding_in_scope(
    finding: Finding,
    rule: Rule | None,
    ranges: tuple[tuple[int, int], ...],
    source: str | None = None,
) -> bool:
    """Return whether a located finding touches at least one added line."""
    if rule is not None and rule.scope is Scope.DOCUMENT:
        return False
    span = _physical_span(finding, source) if source is not None else _span_lines(finding)
    if span is None:
        return False
    start, end = span
    return any(
        start <= changed_end and end >= changed_start
        for changed_start, changed_end in ranges
    )


def finding_fixable(
    finding: Finding,
    rule: Rule | None,
    ranges: tuple[tuple[int, int], ...],
    source: str | None = None,
) -> bool:
    """Return whether replacing this finding cannot touch an unchanged line."""
    if not finding_in_scope(finding, rule, ranges, source) or not finding.replacement:
        return False
    span = _physical_span(finding, source) if source is not None else _span_lines(finding)
    if span is None:
        return False
    return all(
        any(changed_start <= line <= changed_end for changed_start, changed_end in ranges)
        for line in range(span[0], span[1] + 1)
    )


def filter_findings(
    findings: list[Finding],
    rules: dict[str, Rule],
    ranges: tuple[tuple[int, int], ...],
    source: str | None = None,
) -> list[Finding]:
    """Keep only located, physically mapped changed-line findings."""
    return [
        finding
        for finding in findings
        if finding_in_scope(finding, rules.get(finding.rule_id), ranges, source)
    ]


def apply_replacements(
    scores, rules: dict[str, Rule], scope: DiffScope | None = None
) -> int:
    """Apply safe, bottom-up replacements while preserving untouched bytes."""
    applied = 0
    by_path: dict[str, list[Finding]] = {}
    for score in scores:
        for finding in score.findings:
            if not finding.replacement or finding.line < 1 or not finding.matched_text:
                continue
            by_path.setdefault(score.path, []).append(finding)

    for name, findings in by_path.items():
        path = Path(name)
        if path.is_symlink():
            continue
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            if path.stat().st_nlink > 1:
                continue
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines(keepends=True)
        offsets: list[int] = []
        total = 0
        for line in lines:
            offsets.append(total)
            total += len(line)
        edits: list[tuple[int, int, str]] = []
        for finding in findings:
            if scope is not None:
                rule = rules.get(finding.rule_id)
                ranges = scope.ranges_for(path)
                if not finding_fixable(finding, rule, ranges, text):
                    continue
            if finding.line > len(offsets) or finding.column < 1:
                continue
            start = offsets[finding.line - 1] + finding.column - 1
            end = start + len(finding.matched_text)
            if text[start:end] != finding.matched_text:
                continue
            if any(
                start < other_end and end > other_start
                for other_start, other_end, _ in edits
            ):
                continue
            edits.append((start, end, finding.replacement or ""))
        for start, end, replacement in sorted(edits, reverse=True):
            text = text[:start] + replacement + text[end:]
        if edits:
            try:
                path.write_bytes(text.encode("utf-8"))
            except OSError:
                continue
            applied += len(edits)
    return applied
