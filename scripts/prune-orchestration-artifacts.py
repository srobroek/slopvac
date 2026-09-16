#!/usr/bin/env python3
"""Prune retained orchestration and Beads artefacts without leaving the repository."""
from __future__ import annotations

import argparse
import os
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

DEFAULT_AUDIT_DAYS = 30
DEFAULT_BACKUP_COUNT = 10
DEFAULT_INTERACTIONS_MAX_BYTES = 10 * 1024 * 1024
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class PruneError(Exception):
    """An expected, user-facing pruning failure."""


def fail(message: str) -> NoReturn:
    raise PruneError(message)


def _component(name: str) -> str:
    if not name or name in {".", ".."} or os.sep in name:
        fail(f"invalid relative component: {name!r}")
    return name


def _open_child(parent_fd: int, name: str, *, directory: bool = True) -> int:
    """Open one directory entry without following a symlink."""
    flags = os.O_RDONLY | _O_NOFOLLOW
    if directory:
        flags |= _O_DIRECTORY
    return os.open(_component(name), flags, dir_fd=parent_fd)


def _open_relative_dir(root_fd: int, components: tuple[str, ...]) -> int:
    current = os.dup(root_fd)
    try:
        for name in components:
            child = _open_child(current, name)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _lstat(parent_fd: int, name: str) -> os.stat_result:
    return os.stat(_component(name), dir_fd=parent_fd, follow_symlinks=False)


@dataclass(frozen=True)
class Candidate:
    parent: tuple[str, ...]
    name: str
    st_dev: int
    st_ino: int

    @property
    def label(self) -> str:
        return "/".join((*self.parent, self.name))


def _identity(st: os.stat_result) -> tuple[int, int]:
    return st.st_dev, st.st_ino


def _protected_snapshot(root_fd: int) -> set[tuple[int, int]]:
    protected = {
        (".beads", "metadata.json"),
        (".beads", "config.yaml"),
        (".beads", "issues.jsonl"),
        (".beads", "hooks"),
        (".orchestration", ".active-run"),
    }
    identities: set[tuple[int, int]] = set()
    for components in protected:
        parent_fd = _open_relative_dir(root_fd, components[:-1])
        try:
            identities.add(_identity(_lstat(parent_fd, components[-1])))
        except FileNotFoundError:
            pass
        finally:
            os.close(parent_fd)
    return identities


def _is_symlink(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode)


def _walk_safe(parent_fd: int, name: str, protected: set[tuple[int, int]]) -> None:
    st = _lstat(parent_fd, name)
    if _is_symlink(st):
        fail(f"refusing symlink path: {name}")
    if _identity(st) in protected:
        fail(f"refusing protected path: {name}")
    if not stat.S_ISDIR(st.st_mode):
        return
    child_fd = _open_child(parent_fd, name)
    try:
        with os.scandir(child_fd) as entries:
            for entry in entries:
                _walk_safe(child_fd, entry.name, protected)
    finally:
        os.close(child_fd)


def _verify_at(root_fd: int, candidate: Candidate, protected: set[tuple[int, int]]) -> os.stat_result:
    parent_fd = _open_relative_dir(root_fd, candidate.parent)
    try:
        st = _lstat(parent_fd, candidate.name)
        if _identity(st) != (candidate.st_dev, candidate.st_ino):
            fail(f"candidate changed before removal: {candidate.label}")
        if _is_symlink(st):
            fail(f"refusing symlink path: {candidate.label}")
        if _identity(st) in protected:
            fail(f"refusing protected path: {candidate.label}")
        if stat.S_ISDIR(st.st_mode):
            _walk_safe(parent_fd, candidate.name, protected)
        return st
    finally:
        os.close(parent_fd)


def _scandir(parent_fd: int):
    return os.scandir(parent_fd)


def _collect_children(parent_fd: int, parent: tuple[str, ...], suffix: str | None = None) -> list[Candidate]:
    result: list[Candidate] = []
    with _scandir(parent_fd) as entries:
        for entry in entries:
            if suffix is not None and not entry.name.endswith(suffix):
                continue
            st = _lstat(parent_fd, entry.name)
            result.append(Candidate(parent, entry.name, st.st_dev, st.st_ino))
    return result


def candidates(root_fd: int, *, audit_days: int, backup_count: int, max_bytes: int) -> tuple[list[Candidate], Candidate | None]:
    protected = _protected_snapshot(root_fd)
    cutoff = time.time() - audit_days * 86400
    old_audits: list[Candidate] = []
    try:
        audit = (".orchestration", "audit")
        audit_fd = _open_relative_dir(root_fd, audit)
    except FileNotFoundError:
        audit_fd = None
    if audit_fd is not None:
        try:
            for candidate in _collect_children(audit_fd, audit):
                st = _lstat(audit_fd, candidate.name)
                if _is_symlink(st):
                    fail(f"refusing symlink path: {candidate.label}")
                if _identity(st) in protected:
                    fail(f"refusing protected path: {candidate.label}")
                if st.st_mtime < cutoff:
                    _walk_safe(audit_fd, candidate.name, protected)
                    old_audits.append(candidate)
        finally:
            os.close(audit_fd)

    old_backups: list[Candidate] = []
    try:
        backup = (".beads", "backup")
        backup_fd = _open_relative_dir(root_fd, backup)
    except FileNotFoundError:
        backup_fd = None
    if backup_fd is not None:
        try:
            archives = _collect_children(backup_fd, backup, ".darc")
            for candidate in archives:
                st = _lstat(backup_fd, candidate.name)
                if _is_symlink(st):
                    fail(f"refusing symlink path: {candidate.label}")
                if _identity(st) in protected:
                    fail(f"refusing protected path: {candidate.label}")
                _walk_safe(backup_fd, candidate.name, protected)
            archives.sort(key=lambda c: (_lstat(backup_fd, c.name).st_mtime, c.label), reverse=True)
            old_backups = archives[backup_count:]
        finally:
            os.close(backup_fd)

    interactions: Candidate | None = None
    beads_fd = _open_relative_dir(root_fd, (".beads",))
    try:
        try:
            st = _lstat(beads_fd, "interactions.jsonl")
        except FileNotFoundError:
            st = None
        if st is not None:
            if _is_symlink(st):
                fail("refusing symlink path: .beads/interactions.jsonl")
            if not stat.S_ISREG(st.st_mode):
                fail("expected file: .beads/interactions.jsonl")
            if st.st_size > max_bytes:
                if _identity(st) in protected:
                    fail("refusing protected path: .beads/interactions.jsonl")
                interactions = Candidate((".beads",), "interactions.jsonl", st.st_dev, st.st_ino)
    finally:
        os.close(beads_fd)
    return sorted([*old_audits, *old_backups], key=lambda c: c.label), interactions


def _remove_tree(parent_fd: int, name: str, protected: set[tuple[int, int]]) -> None:
    st = _lstat(parent_fd, name)
    if _is_symlink(st):
        fail(f"refusing symlink path: {name}")
    if not stat.S_ISDIR(st.st_mode):
        os.unlink(name, dir_fd=parent_fd)
        return
    child_fd = _open_child(parent_fd, name)
    try:
        with os.scandir(child_fd) as entries:
            for entry in entries:
                _remove_tree(child_fd, entry.name, protected)
        os.rmdir(name, dir_fd=parent_fd)
    finally:
        os.close(child_fd)


def _remove_at(root_fd: int, candidate: Candidate, protected: set[tuple[int, int]]) -> None:
    parent_fd = _open_relative_dir(root_fd, candidate.parent)
    try:
        st = _lstat(parent_fd, candidate.name)
        if _identity(st) != (candidate.st_dev, candidate.st_ino):
            fail(f"candidate changed before removal: {candidate.label}")
        if _is_symlink(st) or _identity(st) in protected:
            fail(f"refusing protected or symlink path: {candidate.label}")
        try:
            _remove_tree(parent_fd, candidate.name, protected)
        except (OSError, PruneError) as error:
            if stat.S_ISDIR(st.st_mode):
                raise PruneError(f"partially deleted {candidate.label}: {error}") from error
            raise
    finally:
        os.close(parent_fd)



def truncate_log(beads_fd: int, candidate: Candidate, max_bytes: int) -> None:
    fd = os.open(candidate.name, os.O_RDWR | _O_NOFOLLOW, dir_fd=beads_fd)
    try:
        st = os.fstat(fd)
        if _identity(st) != (candidate.st_dev, candidate.st_ino):
            fail(f"candidate changed before truncation: {candidate.label}")
        if st.st_size <= max_bytes:
            return
        if max_bytes == 0:
            os.ftruncate(fd, 0)
            return
        os.lseek(fd, -max_bytes, os.SEEK_END)
        kept = os.read(fd, max_bytes)
        if kept and not kept.startswith(b"\n"):
            newline = kept.find(b"\n")
            kept = kept[newline + 1 :] if newline >= 0 else b""
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, kept)
        os.ftruncate(fd, len(kept))
    finally:
        os.close(fd)


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
    root_fd = os.open(root, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
    try:
        protected = _protected_snapshot(root_fd)
        paths, interactions = candidates(root_fd, audit_days=args.audit_days, backup_count=args.backup_count, max_bytes=args.interactions_max_bytes)
        for candidate in paths:
            if not args.apply:
                print(f"would delete {candidate.label}")
                continue
            _verify_at(root_fd, candidate, protected)
            _remove_at(root_fd, candidate, protected)
            print(f"deleted {candidate.label}")
        if interactions is not None:
            print(f"{'would truncate' if not args.apply else 'truncated'} {interactions.label} to at most {args.interactions_max_bytes} bytes")
            if args.apply:
                beads_fd = _open_relative_dir(root_fd, (".beads",))
                try:
                    _verify_at(root_fd, interactions, protected)
                    truncate_log(beads_fd, interactions, args.interactions_max_bytes)
                finally:
                    os.close(beads_fd)
        return 0
    finally:
        os.close(root_fd)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PruneError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
