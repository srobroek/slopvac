"""Where compiled Vale trees live, how they are keyed, and when they are pruned.

A compiled tree is a pure function of its inputs: the rules, the resolved levels,
the profile, the blocklist, and the compiler source itself. `fingerprint` hashes
all of them so that a change to any one mints a new key and a stale tree is never
served. `prune_cache` bounds the number of trees kept. Separate from
`compile_vale` so the compiler owns translation and this module owns storage.
`cache_root` and `source_digest` also serve the other caches under the same root.

Cheap to import: the startup path imports it for `cache_root` and `CACHE_KEEP`,
so the config and model types stay annotation-only.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
import tempfile
from contextlib import contextmanager
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import ResolvedConfig
    from .model import Rule


@cache
def source_digest(names: tuple[str, ...]) -> str:
    """Hash the source of these package modules, for a cache key.

    Read from `__file__` rather than tracked as a hand-bumped version constant,
    because a constant only invalidates when someone REMEMBERS to bump it, and the
    failure it guards against is silent. Falls back to the package version if the
    source is unreadable (a zipimport or a frozen build), which is weaker but never
    worse than an input-only key. Computed once per process, on first use.
    """
    try:
        here = Path(__file__).parent
        digest = hashlib.sha256()
        for name in names:
            digest.update((here / name).read_bytes())
        return digest.hexdigest()[:16]
    except OSError:
        from . import __version__

        return f"v{__version__}"


# The modules whose code decides what a compiled tree contains.
_COMPILER_SOURCES = ("compile_vale.py", "vale_cache.py", "vale_probe.py")


def cache_root() -> Path:
    """Where compiled styles live.

    Use the platform's per-user cache. Never reuse the old shared temp cache.
    Ruleset reads and writes separately validate the directory's trust boundary.
    """
    override = os.environ.get("SLOPVAC_CACHE_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        return (
            Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
            / "slopvac/Cache"
        )
    if sys.platform == "darwin":
        return Path.home() / "Library/Caches/slopvac"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "slopvac"
    return Path.home() / ".cache/slopvac"


def trusted_cache_path(path: Path, *, create: bool = False) -> bool:
    """Fail closed unless POSIX ownership and permissions prove a private path.

    Ancestors must be owned by this user or root and not writable by others.
    A root-owned sticky directory (such as /tmp) may contain a private user
    directory. Links and non-regular entries are never proof of verified rules.
    On platforms without these checks, loading simply parses and proves afresh.
    Existing permissions are never repaired, and shared entries are never copied.
    """
    if os.name != "posix" or not path.is_absolute() or ".." in path.parts:
        return False
    uid = os.getuid()
    try:
        for component in reversed((path, *path.parents)):
            try:
                info = component.lstat()
            except FileNotFoundError:
                if not create:
                    return False
                component.mkdir(mode=0o700)
                info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or info.st_uid not in {0, uid}:
                return False
            if component == path:
                if info.st_uid != uid or info.st_mode & 0o077:
                    return False
                if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
                    return False
            elif not stat.S_ISDIR(info.st_mode):
                return False
            elif info.st_mode & 0o022 and not (
                info.st_uid == 0 and info.st_mode & stat.S_ISVTX
            ):
                return False
        return True
    except OSError:
        return False


@cache
def _temporary_cache() -> tempfile.TemporaryDirectory:
    """Keep transient compiled output alive until this process exits."""
    return tempfile.TemporaryDirectory(prefix="slopvac-private-")


def private_compile_root() -> Path:
    root = cache_root()
    if trusted_cache_path(root, create=True):
        return root
    return Path(_temporary_cache().name)


@contextmanager
def cache_lock(root: Path):
    """Serialize publication and pruning for one shared cache root."""
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".slopvac.lock").open("a+") as handle:
        if os.name == "nt":
            import msvcrt

            handle.write("\0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# How many compiled trees to keep. Each is ~400KB, so 16 is a few megabytes and
# covers the profiles and locales one project alternates between, plus a handful of
# other checkouts, without a second compile. The number that matters is not the
# disk: it is that every ruleset edit, severity change, and blocklist edit mints a
# new key, so an unpruned cache grows with development activity rather than use.
# One developer machine reached 209 trees and 83MB.
CACHE_KEEP = 16


def prune_cache(root: Path | None = None, keep: int = CACHE_KEEP) -> list[Path]:
    """Delete all but the `keep` most recently used compiled trees.

    Returns what it removed. Never raises: a cache that cannot be pruned is a
    disk-space problem, and failing a lint over one would be worse than the leak.

    Recency is the directory's own mtime, refreshed on every cache hit, so the tree
    a project keeps hitting survives no matter how long ago it was compiled. Sorted
    by name as a tiebreak, because two trees written in the same mtime granule must
    still order deterministically or the survivor set varies between runs.
    """
    root = cache_root() if root is None else root
    removed: list[Path] = []
    try:
        entries = [p for p in root.iterdir() if (p / "manifest.json").is_file()]
    except OSError:
        return removed
    def recency(path: Path) -> tuple[float, str]:
        try:
            return (path.stat().st_mtime, path.name)
        except OSError:
            return (0.0, path.name)

    # Ruleset slots have their own recency budget, including generated locales.
    rulesets = root / "rulesets"
    if trusted_cache_path(rulesets):
        slots = list(rulesets.glob("*.json"))
        for stale in sorted(slots, key=recency, reverse=True)[keep:]:
            try:
                stale.unlink()
                removed.append(stale)
            except OSError:
                pass


    for stale in sorted(entries, key=recency, reverse=True)[keep:]:
        try:
            shutil.rmtree(stale)
        except OSError:
            continue
        removed.append(stale)
    return removed


def fingerprint(
    rules: list[Rule],
    config: ResolvedConfig,
    levels: dict[str, str],
    vocabulary=None,
    vale_version: tuple[int, int, int] | None = None,
) -> str:
    """Hash of everything that changes the output.

    Keyed on the resolved LEVELS rather than the raw config, because that is what
    reaches the ini: two configs that resolve every rule to the same severity
    produce identical output and should share a cache entry.

    The Vale version is part of the key when known: which payloads Vale accepts
    (the probe decides what stays native) and how it treats a pattern (`%%`
    against `%` changed at 3.21) both depend on the binary, so a tree compiled
    under one release is not the tree another release would have produced.
    """
    digest = hashlib.sha256()
    if vale_version is not None:
        digest.update(".".join(str(n) for n in vale_version).encode())
    # THE COMPILER'S OWN SOURCE IS PART OF THE KEY. Rules, levels, and profile are
    # the compiler's INPUT; the generated style also depends on the code that
    # translates them, so keying on input alone serves a stale style after every
    # compiler change. This cost real debugging time: the fix that stops a
    # text-type-scoped metric from reaching Vale appeared to do NOTHING -- three
    # rescores of the whole corpus came back byte-identical, including counts that
    # had to change -- because the fingerprint was unchanged and the cached style
    # still held the rule. A silently stale cache is indistinguishable from a fix
    # that does not work, which is the more expensive failure of the two.
    digest.update(source_digest(_COMPILER_SOURCES).encode())
    for rule in sorted(rules, key=lambda r: r.qualified_id):
        digest.update(rule.qualified_id.encode())
        digest.update(rule.model_dump_json(exclude={"category"}).encode())
    for rule_id in sorted(levels):
        digest.update(f"{rule_id}={levels[rule_id]}".encode())
    digest.update(config.profile.value.encode())
    # THE BLOCKLIST IS PART OF THE KEY TOO, and for the same reason: its words are
    # baked into the generated `sequence` rules, so adding one and re-running would
    # otherwise hit a cache entry compiled without it. The failure mode is the one
    # documented above -- an edit that appears to do nothing -- and it would land on
    # a USER editing their own wordlist rather than on us editing the compiler,
    # which makes it harder to diagnose, not easier.
    #
    # Hashed from the entries rather than the file bytes, so reformatting the file
    # or moving it between TOML and YAML does not invalidate a still-correct style.
    if vocabulary is not None:
        for entry in sorted(vocabulary.blocked(), key=lambda e: (e.word, e.pos.value)):
            digest.update(f"{entry.word}:{entry.pos.value}".encode())
    return digest.hexdigest()[:16]
