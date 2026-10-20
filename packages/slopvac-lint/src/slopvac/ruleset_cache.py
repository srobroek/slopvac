"""Reuse an earlier verified ruleset load while its inputs stay the same.

Loading the ruleset parses about 400KB of YAML and then proves every example
against its own pattern, which compiles every regex. Both are pure functions of
the rule files and the code that reads them, so a run whose rule files and loader
code match an earlier verified load reuses that load's parsed documents and
skips the proof. The documents still go through model validation on every load:
the entry stores the parse and the fact that it passed verification, never the
models, so a schema change can only reject an entry, not hand out a stale model.

ONE FILE PER SLOT. A slot is the set of rule directories, and the entry inside it
records its content key. An edited rule file, loader module, or upgrade therefore
overwrites its slot instead of adding a file: the cache grows with the number of
`--rules-dir` sets in use, not with edits. Two installs of different versions
that share a cache directory take turns overwriting the slot. Each load is then
a miss and costs one uncached load.

A DAMAGED ENTRY IS A MISS. The entry carries a checksum of its documents, so a
truncated, edited, or otherwise corrupt file never yields rules that differ from
a fresh load. Writing is atomic and never raises.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path

from .vale_cache import cache_root, source_digest

# The loader, the entry format, the schema the documents validate against, and
# the substitution-pattern builder that verification compiles. A change to any
# of them can change what a rule file loads to or whether its examples pass.
_LOADER_SOURCES = ("rules.py", "ruleset_cache.py", "model.py", "engine.py")

Documents = list[tuple[str, list[dict]]]


def entry_path(extra_dirs: list[Path]) -> Path:
    """The slot for this set of rule directories."""
    slot = hashlib.sha256(b"rulesets")
    for directory in extra_dirs:
        slot.update(b"\0" + str(directory.resolve()).encode())
    return cache_root() / "rulesets" / f"{slot.hexdigest()[:16]}.json"


def content_key(sources: list[tuple[str, str]]) -> str:
    """Hash of everything a verified load depends on: the package version, the
    loader's source, and each rule file's name and text, in load order."""
    from . import __version__

    digest = hashlib.sha256()
    digest.update(__version__.encode() + b"\0")
    digest.update(source_digest(_LOADER_SOURCES).encode())
    for origin, text in sources:
        digest.update(b"\0" + origin.encode() + b"\0")
        digest.update(hashlib.sha256(text.encode("utf-8")).digest())
    return digest.hexdigest()


def read(path: Path, key: str) -> Documents | None:
    """The documents stored under `key`, or None when the entry is absent, holds
    another key, or fails its checksum or shape check."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    header, _, body = raw.partition(b"\n")
    try:
        meta = json.loads(header)
        if not isinstance(meta, dict) or meta.get("key") != key:
            return None
        if meta.get("sha256") != hashlib.sha256(body).hexdigest():
            return None
        stored = json.loads(body)
    except ValueError:
        return None
    if not isinstance(stored, list):
        return None
    documents: Documents = []
    for item in stored:
        if not (
            isinstance(item, list)
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], list)
            and all(isinstance(document, dict) for document in item[1])
        ):
            return None
        documents.append((item[0], item[1]))
    return documents


def write(path: Path, key: str, documents: Documents) -> None:
    """Store `documents` under `key`, replacing the slot atomically.

    Stores nothing when the documents do not survive a JSON round trip unchanged:
    YAML can produce dates, sets, and non-string keys that JSON would drop or
    coerce, and a reused entry must validate exactly as a fresh parse does.
    Never raises: a failed write costs the next run a fresh load, which is no
    reason to fail this one.
    """
    stored = [[origin, loaded] for origin, loaded in documents]
    try:
        body = json.dumps(stored, ensure_ascii=True, separators=(",", ":"))
        if json.loads(body) != stored:
            return
    except (TypeError, ValueError):
        return
    encoded = body.encode("ascii")
    header = json.dumps({"key": key, "sha256": hashlib.sha256(encoded).hexdigest()})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(header.encode("ascii") + b"\n" + encoded)
            os.replace(temporary, path)
        except BaseException:
            with suppress(OSError):
                os.unlink(temporary)
            raise
    except OSError:
        return
