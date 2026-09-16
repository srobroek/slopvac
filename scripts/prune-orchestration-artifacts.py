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
CHUNK_SIZE = 1024 * 1024
PARENT_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

Identity = tuple[int, int]


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


def ensure_no_symlink_components(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError:
        checked_path(root, path)
        return
    current = root
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            checked_path(root, current)
            fail(f"refusing symlink path: {current}")


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


@dataclass(frozen=True)
class ProtectedSnapshot:
    paths: tuple[Path, ...]
    identities: frozenset[Identity]


def _identity_from_stat(result: os.stat_result) -> Identity:
    return (result.st_dev, result.st_ino)


def _protected_identities(path: Path, identities: set[Identity]) -> None:
    try:
        result = os.lstat(path)
    except FileNotFoundError:
        return
    identities.add(_identity_from_stat(result))
    if path.name != "hooks" or not stat.S_ISDIR(result.st_mode):
        return
    pending = [path]
    while pending:
        current = pending.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                child = Path(entry.path)
                child_result = os.lstat(child)
                identities.add(_identity_from_stat(child_result))
                if stat.S_ISDIR(child_result.st_mode):
                    pending.append(child)


def protected_snapshot(root: Path) -> ProtectedSnapshot:
    paths = protected_paths(root)
    identities: set[Identity] = set()
    for path in paths:
        _protected_identities(path, identities)
    return ProtectedSnapshot(paths, frozenset(identities))


def is_protected(
    root: Path,
    candidate: Path,
    identity: Identity | None = None,
    snapshot: ProtectedSnapshot | None = None,
) -> bool:
    """Check both the protected path contract and protected inode identities."""
    candidate = checked_path(root, candidate)
    protected = snapshot if snapshot is not None else protected_snapshot(root)
    for protected_path in protected.paths:
        resolved = protected_path.resolve(strict=False)
        if candidate == resolved or resolved in candidate.parents:
            return True
    return identity is not None and identity in protected.identities


@dataclass(frozen=True)
class Candidate:
    path: Path
    identity: Identity
    mtime: float
    is_dir: bool


def _select_candidate(
    root: Path,
    path: Path,
    protected: ProtectedSnapshot,
    *,
    ensure_safe: bool,
) -> Candidate:
    ensure_no_symlink_components(root, path)
    checked_path(root, path)
    if ensure_safe:
        ensure_tree_is_safe(root, path)
    result = os.lstat(path)
    if stat.S_ISLNK(result.st_mode):
        checked_path(root, path)
        fail(f"refusing symlink path: {path}")
    identity = _identity_from_stat(result)
    if is_protected(root, path, identity, protected):
        fail(f"refusing protected path: {path}")
    return Candidate(path, identity, result.st_mtime, stat.S_ISDIR(result.st_mode))


def candidates(
    root: Path,
    *,
    audit_days: int,
    backup_count: int,
    max_bytes: int,
) -> tuple[list[Candidate], Candidate | None, ProtectedSnapshot]:
    protected = protected_snapshot(root)
    audit = root / ".orchestration" / "audit"
    backups = root / ".beads" / "backup"
    old_audits: list[Candidate] = []
    cutoff = time.time() - audit_days * 86400
    if audit.exists() or audit.is_symlink():
        ensure_no_symlink_components(root, audit)
        checked_path(root, audit)
        if audit.is_symlink():
            fail(f"refusing symlink path: {audit}")
        if not audit.is_dir():
            fail(f"expected directory: {audit}")
        for run in audit.iterdir():
            candidate = _select_candidate(root, run, protected, ensure_safe=True)
            if candidate.mtime < cutoff:
                old_audits.append(candidate)

    old_backups: list[Candidate] = []
    if backups.exists() or backups.is_symlink():
        ensure_no_symlink_components(root, backups)
        checked_path(root, backups)
        if backups.is_symlink():
            fail(f"refusing symlink path: {backups}")
        if not backups.is_dir():
            fail(f"expected directory: {backups}")
        archive_paths: list[Candidate] = []
        for archive in backups.glob("*.darc"):
            archive_paths.append(_select_candidate(root, archive, protected, ensure_safe=True))
        archive_paths.sort(key=lambda candidate: (candidate.mtime, str(candidate.path)), reverse=True)
        old_backups = archive_paths[backup_count:]

    interactions = root / ".beads" / "interactions.jsonl"
    truncate_to: Candidate | None = None
    if interactions.exists() or interactions.is_symlink():
        ensure_no_symlink_components(root, interactions)
        checked_path(root, interactions)
        if interactions.is_symlink():
            fail(f"refusing symlink path: {interactions}")
        if not interactions.is_file():
            fail(f"expected file: {interactions}")
        result = os.lstat(interactions)
        identity = _identity_from_stat(result)
        if result.st_size > max_bytes:
            if is_protected(root, interactions, identity, protected):
                fail(f"refusing protected path: {interactions}")
            truncate_to = Candidate(interactions, identity, result.st_mtime, False)

    return sorted([*old_audits, *old_backups], key=lambda candidate: str(candidate.path)), truncate_to, protected


def _open_parent(path: Path) -> int:
    return os.open(path.parent, PARENT_FLAGS)


def _lstat_at(directory_fd: int, name: str) -> os.stat_result:
    # os.lstat never follows the final component; dir_fd anchors the lookup.
    return os.lstat(name, dir_fd=directory_fd)


def _verify_at(
    root: Path,
    candidate: Candidate,
    directory_fd: int,
    protected: ProtectedSnapshot,
) -> os.stat_result:
    checked_path(root, candidate.path)
    try:
        result = _lstat_at(directory_fd, candidate.path.name)
    except FileNotFoundError:
        fail(f"candidate changed before removal: {candidate.path}")
    identity = _identity_from_stat(result)
    if stat.S_ISLNK(result.st_mode):
        fail(f"refusing symlink path: {candidate.path}")
    if identity != candidate.identity:
        fail(f"candidate changed before removal: {candidate.path}")
    if is_protected(root, candidate.path, identity, protected):
        fail(f"refusing protected path: {candidate.path}")
    return result


def _validate_tree_fd(directory_fd: int, path: Path) -> None:
    with os.scandir(directory_fd) as entries:
        for entry in entries:
            result = _lstat_at(directory_fd, entry.name)
            child = path / entry.name
            if stat.S_ISLNK(result.st_mode):
                fail(f"refusing symlink path: {child}")
            if stat.S_ISDIR(result.st_mode):
                child_fd = os.open(entry.name, PARENT_FLAGS, dir_fd=directory_fd)
                try:
                    _validate_tree_fd(child_fd, child)
                finally:
                    os.close(child_fd)


@dataclass
class RemovalHandle:
    candidate: Candidate
    directory_fd: int
    name: str
    is_dir: bool


def _prepare_removal(
    root: Path,
    candidate: Candidate,
    protected: ProtectedSnapshot,
) -> RemovalHandle:
    directory_fd = _open_parent(candidate.path)
    try:
        result = _verify_at(root, candidate, directory_fd, protected)
        if stat.S_ISDIR(result.st_mode):
            target_fd = os.open(candidate.path.name, PARENT_FLAGS, dir_fd=directory_fd)
            try:
                _validate_tree_fd(target_fd, candidate.path)
            finally:
                os.close(target_fd)
        return RemovalHandle(candidate, directory_fd, candidate.path.name, stat.S_ISDIR(result.st_mode))
    except BaseException:
        os.close(directory_fd)
        raise


def _remove_tree_fd(directory_fd: int, path: Path) -> None:
    with os.scandir(directory_fd) as entries:
        names = [entry.name for entry in entries]
    for name in names:
        result = _lstat_at(directory_fd, name)
        child = path / name
        if stat.S_ISLNK(result.st_mode):
            fail(f"refusing symlink path: {child}")
        if stat.S_ISDIR(result.st_mode):
            child_fd = os.open(name, PARENT_FLAGS, dir_fd=directory_fd)
            try:
                _remove_tree_fd(child_fd, child)
            finally:
                os.close(child_fd)
            os.rmdir(name, dir_fd=directory_fd)
        else:
            os.unlink(name, dir_fd=directory_fd)


def _remove_handle(root: Path, handle: RemovalHandle, protected: ProtectedSnapshot) -> None:
    result = _verify_at(root, handle.candidate, handle.directory_fd, protected)
    if stat.S_ISDIR(result.st_mode) != handle.is_dir:
        fail(f"candidate changed before removal: {handle.candidate.path}")
    if handle.is_dir:
        target_fd = os.open(handle.name, PARENT_FLAGS, dir_fd=handle.directory_fd)
        try:
            try:
                _remove_tree_fd(target_fd, handle.candidate.path)
                os.rmdir(handle.name, dir_fd=handle.directory_fd)
            except (OSError, PruneError):
                print(f"partially deleted {handle.candidate.path}")
                raise
        finally:
            os.close(target_fd)
    else:
        os.unlink(handle.name, dir_fd=handle.directory_fd)


def _new_temp(directory_fd: int, basename: str) -> tuple[int, str]:
    for suffix in range(1000):
        name = f".{basename}.tmp-{os.getpid()}-{suffix}"
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory_fd,
            )
            return descriptor, name
        except FileExistsError:
            continue
    fail(f"could not create temporary file beside {basename}")


def _align_tail_start(source_fd: int, offset: int) -> int:
    os.lseek(source_fd, offset - 1, os.SEEK_SET)
    previous = os.read(source_fd, 1)
    os.lseek(source_fd, offset, os.SEEK_SET)
    first = os.read(source_fd, 1)
    os.lseek(source_fd, offset, os.SEEK_SET)
    if previous == b"\n" and first != b"\n":
        return offset
    while True:
        start = os.lseek(source_fd, 0, os.SEEK_CUR)
        chunk = os.read(source_fd, CHUNK_SIZE)
        if not chunk:
            return start + len(chunk)
        newline = chunk.find(b"\n")
        if newline < 0:
            continue
        boundary = start + newline + 1
        os.lseek(source_fd, boundary, os.SEEK_SET)
        while True:
            next_byte = os.read(source_fd, 1)
            if next_byte != b"\n":
                if next_byte:
                    os.lseek(source_fd, -1, os.SEEK_CUR)
                return os.lseek(source_fd, 0, os.SEEK_CUR)
            boundary += 1
            os.lseek(source_fd, boundary, os.SEEK_SET)


def _write_all(file_descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(file_descriptor, view)
        if written <= 0:
            fail("short write while creating temporary log")
        view = view[written:]


def truncate_log(
    path: Path,
    max_bytes: int,
    expected_identity: Identity | None = None,
    directory_fd: int | None = None,
) -> None:
    """Atomically retain a bounded, complete-record tail of an interaction log."""
    own_directory_fd = directory_fd is None
    if own_directory_fd:
        directory_fd = _open_parent(path)
    assert directory_fd is not None
    temp_name: str | None = None
    source_fd: int | None = None
    temp_fd: int | None = None
    try:
        result = _lstat_at(directory_fd, path.name)
        identity = _identity_from_stat(result)
        if stat.S_ISLNK(result.st_mode):
            fail(f"refusing symlink path: {path}")
        if expected_identity is not None and identity != expected_identity:
            fail(f"candidate changed before truncation: {path}")
        source_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        source_result = os.fstat(source_fd)
        if _identity_from_stat(source_result) != identity:
            fail(f"candidate changed before truncation: {path}")
        source_size = source_result.st_size
        if source_size <= max_bytes:
            return
        temp_fd, temp_name = _new_temp(directory_fd, path.name)
        os.fchmod(temp_fd, stat.S_IMODE(source_result.st_mode))
        retained_start = max(0, source_size - max_bytes)
        if max_bytes:
            if retained_start:
                retained_start = _align_tail_start(source_fd, retained_start)
            else:
                os.lseek(source_fd, 0, os.SEEK_SET)
            written = 0
            last_newline = 0
            while written < max_bytes:
                chunk = os.read(source_fd, min(CHUNK_SIZE, max_bytes - written))
                if not chunk:
                    break
                _write_all(temp_fd, chunk)
                written += len(chunk)
                newline = chunk.rfind(b"\n")
                if newline >= 0:
                    last_newline = written - len(chunk) + newline + 1
            os.ftruncate(temp_fd, last_newline)
        else:
            os.ftruncate(temp_fd, 0)
        os.fsync(temp_fd)
        final_result = _lstat_at(directory_fd, path.name)
        if _identity_from_stat(final_result) != identity or stat.S_ISLNK(final_result.st_mode):
            fail(f"candidate changed before truncation: {path}")
        os.replace(temp_name, path.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        temp_name = None
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        if own_directory_fd:
            os.close(directory_fd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
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
    paths, interactions, protected = candidates(
        root,
        audit_days=args.audit_days,
        backup_count=args.backup_count,
        max_bytes=args.interactions_max_bytes,
    )
    if not args.apply:
        for candidate in paths:
            print(f"would delete {candidate.path}")
        if interactions is not None:
            print(f"would truncate {interactions.path} to at most {args.interactions_max_bytes} bytes")
        return 0

    handles: list[RemovalHandle] = []
    interaction_fd: int | None = None
    try:
        for candidate in paths:
            handles.append(_prepare_removal(root, candidate, protected))
        if interactions is not None:
            interaction_fd = _open_parent(interactions.path)
            result = _verify_at(root, interactions, interaction_fd, protected)
            if stat.S_ISDIR(result.st_mode):
                fail(f"expected file: {interactions.path}")
        for handle in handles:
            _remove_handle(root, handle, protected)
            print(f"deleted {handle.candidate.path}")
        if interactions is not None:
            assert interaction_fd is not None
            truncate_log(
                interactions.path,
                args.interactions_max_bytes,
                interactions.identity,
                interaction_fd,
            )
            print(f"truncated {interactions.path} to at most {args.interactions_max_bytes} bytes")
    finally:
        for handle in handles:
            os.close(handle.directory_fd)
        if interaction_fd is not None:
            os.close(interaction_fd)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, PruneError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
