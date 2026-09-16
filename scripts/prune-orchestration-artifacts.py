#!/usr/bin/env python3
"""Prune retained orchestration and Beads artefacts without leaving the repository."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from typing import NoReturn

DEFAULT_AUDIT_DAYS = 30
DEFAULT_BACKUP_COUNT = 10
DEFAULT_INTERACTIONS_MAX_BYTES = 10 * 1024 * 1024


class PruneError(Exception):
    """An expected, user-facing pruning failure."""


def fail(message: str) -> NoReturn:
    raise PruneError(message)


def inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def checked_path(root: Path, path: Path) -> Path:
    resolved = path.resolve(strict=False)
    if not inside(root, resolved):
        fail(f"refusing path outside root: {path}")
    return resolved


def ensure_tree_is_safe(root: Path, path: Path) -> None:
    """Reject symlink escapes before a candidate tree is removed."""
    if path.is_symlink():
        checked_path(root, path)
        fail(f"refusing symlink path: {path}")
    if not path.is_dir():
        return
    for current, directories, files in os.walk(path, followlinks=False):
        current_path = Path(current)
        checked_path(root, current_path)
        for name in [*directories, *files]:
            child = current_path / name
            if child.is_symlink():
                checked_path(root, child)
                fail(f"refusing symlink path: {child}")


def protected_paths(root: Path) -> tuple[Path, ...]:
    return tuple(
        root / relative
        for relative in (
            ".beads/metadata.json",
            ".beads/config.yaml",
            ".beads/issues.jsonl",
            ".beads/hooks",
            ".orchestration/.active-run",
        )
    )


def is_protected(root: Path, candidate: Path) -> bool:
    candidate = checked_path(root, candidate)
    return any(candidate == protected or protected in candidate.parents for protected in protected_paths(root))


def candidates(root: Path, *, audit_days: int, backup_count: int, max_bytes: int) -> tuple[list[Path], Path | None]:
    audit = root / ".orchestration" / "audit"
    backups = root / ".beads" / "backup"
    old_audits: list[Path] = []
    cutoff = time.time() - audit_days * 86400
    if audit.exists() or audit.is_symlink():
        checked_path(root, audit)
        if audit.is_symlink():
            fail(f"refusing symlink path: {audit}")
        if not audit.is_dir():
            fail(f"expected directory: {audit}")
        for run in audit.iterdir():
            checked_path(root, run)
            ensure_tree_is_safe(root, run)
            if is_protected(root, run):
                fail(f"refusing protected path: {run}")
            if run.stat().st_mtime < cutoff:
                old_audits.append(run)

    old_backups: list[Path] = []
    if backups.exists() or backups.is_symlink():
        checked_path(root, backups)
        if backups.is_symlink():
            fail(f"refusing symlink path: {backups}")
        if not backups.is_dir():
            fail(f"expected directory: {backups}")
        archive_paths = []
        for archive in backups.glob("*.darc"):
            checked_path(root, archive)
            ensure_tree_is_safe(root, archive)
            if is_protected(root, archive):
                fail(f"refusing protected path: {archive}")
            archive_paths.append(archive)
        archive_paths.sort(key=lambda path: (path.stat().st_mtime, str(path)), reverse=True)
        old_backups = archive_paths[backup_count:]

    interactions = root / ".beads" / "interactions.jsonl"
    truncate_to: Path | None = None
    if interactions.exists() or interactions.is_symlink():
        checked_path(root, interactions)
        if interactions.is_symlink():
            fail(f"refusing symlink path: {interactions}")
        if not interactions.is_file():
            fail(f"expected file: {interactions}")
        if interactions.stat().st_size > max_bytes:
            if is_protected(root, interactions):
                fail(f"refusing protected path: {interactions}")
            truncate_to = interactions

    return sorted([*old_audits, *old_backups], key=str), truncate_to


def truncate_log(path: Path, max_bytes: int) -> None:
    data = path.read_bytes()
    if len(data) <= max_bytes:
        return
    kept = data[-max_bytes:] if max_bytes else b""
    if kept and not kept.startswith(b"\n"):
        newline = kept.find(b"\n")
        kept = kept[newline + 1 :] if newline >= 0 else b""
    path.write_bytes(kept)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--dry-run", action="store_true", help="report changes without applying them")
    parser.add_argument("--apply", action="store_true", help="apply the reported changes")
    parser.add_argument("--audit-days", type=int, default=DEFAULT_AUDIT_DAYS, help="retain audit entries for this many days")
    parser.add_argument("--backup-count", type=int, default=DEFAULT_BACKUP_COUNT, help="retain this many newest backup archives")
    parser.add_argument("--interactions-max-bytes", type=int, default=DEFAULT_INTERACTIONS_MAX_BYTES, help="retain at most this many interaction-log bytes")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("--apply and --dry-run are mutually exclusive")
    if args.audit_days < 0 or args.backup_count < 0 or args.interactions_max_bytes < 0:
        parser.error("retention values must be non-negative")
    return args


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        fail(f"root is not a directory: {args.root}")
    paths, interactions = candidates(
        root,
        audit_days=args.audit_days,
        backup_count=args.backup_count,
        max_bytes=args.interactions_max_bytes,
    )
    for path in paths:
        print(f"{'would delete' if not args.apply else 'deleted'} {path}")
        if args.apply:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    if interactions is not None:
        print(f"{'would truncate' if not args.apply else 'truncated'} {interactions} to at most {args.interactions_max_bytes} bytes")
        if args.apply:
            truncate_log(interactions, args.interactions_max_bytes)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PruneError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
