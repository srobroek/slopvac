"""Where compiled Vale trees live, how they are keyed, and when they are pruned.

A compiled tree is a pure function of its inputs: the rules, the resolved levels,
the profile, the blocklist, and the compiler source itself. `fingerprint` hashes
all of them so that a change to any one mints a new key and a stale tree is never
served. `prune_cache` bounds the number of trees kept. Separate from
`compile_vale` so the compiler owns translation and this module owns storage.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from .config import ResolvedConfig
from .model import Rule


def _compiler_source_digest() -> str:
    """Hash the compiler's source, for the cache key.

    Read from `__file__` rather than tracked as a hand-bumped version constant,
    because a constant only invalidates when someone REMEMBERS to bump it, and the
    failure it guards against is silent. Falls back to the package version if the
    source is unreadable (a zipimport or a frozen build), which is weaker but never
    worse than the input-only key it replaces.
    """
    try:
        here = Path(__file__).parent
        digest = hashlib.sha256()
        for name in ("compile_vale.py", "vale_cache.py", "vale_probe.py"):
            digest.update((here / name).read_bytes())
        return digest.hexdigest()[:16]
    except OSError:
        from . import __version__

        return f"v{__version__}"


_COMPILER_SOURCE_DIGEST = _compiler_source_digest()


def cache_root() -> Path:
    """Where compiled styles live.

    Overridable through `SLOPVAC_CACHE_DIR`, then `XDG_CACHE_HOME`, then the
    platform temp dir. A user-writable location matters because the compile runs
    on every lint and a read-only cache would recompile every time.
    """
    override = os.environ.get("SLOPVAC_CACHE_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "slopvac"
    return Path(tempfile.gettempdir()) / "slopvac-cache"


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
    if len(entries) <= keep:
        return removed

    def recency(path: Path) -> tuple[float, str]:
        try:
            return (path.stat().st_mtime, path.name)
        except OSError:
            return (0.0, path.name)

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
) -> str:
    """Hash of everything that changes the output.

    Keyed on the resolved LEVELS rather than the raw config, because that is what
    reaches the ini: two configs that resolve every rule to the same severity
    produce identical output and should share a cache entry.
    """
    digest = hashlib.sha256()
    # THE COMPILER'S OWN SOURCE IS PART OF THE KEY. Rules, levels, and profile are
    # the compiler's INPUT; the generated style also depends on the code that
    # translates them, so keying on input alone serves a stale style after every
    # compiler change. This cost real debugging time: the fix that stops a
    # text-type-scoped metric from reaching Vale appeared to do NOTHING -- three
    # rescores of the whole corpus came back byte-identical, including counts that
    # had to change -- because the fingerprint was unchanged and the cached style
    # still held the rule. A silently stale cache is indistinguishable from a fix
    # that does not work, which is the more expensive failure of the two.
    digest.update(_COMPILER_SOURCE_DIGEST.encode())
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
