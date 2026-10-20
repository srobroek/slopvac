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
truncated or accidentally damaged file is a miss. A checksum is not authentication:
ownership and permissions establish trust before a read. Writing is atomic and never raises.

THE GENERATED SPELLING RULE HAS ITS OWN SLOT, one per locale, in the same format.
`rules.inject_locale_rule` builds it from the locale table and the project's
allowlist on every run, then proves its examples, which compiles a pattern of
about 280 alternatives: about 15 ms of CPU in each `lint`, `rules`, and `explain`
run. Its entry stores the generated document under a key of that document, the
package version, and the loader's source, so a hit means this exact rule already
passed under this exact code.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path

from .vale_cache import cache_root, source_digest, trusted_cache_path

# The loader, the entry format, the schema the documents validate against, and
# the substitution-pattern builder that verification compiles. A change to any
# of them can change what a rule file loads to or whether its examples pass.
_LOADER_SOURCES = ("rules.py", "ruleset_cache.py", "model.py", "engine.py")

Documents = list[tuple[str, list[dict]]]


def entry_path(extra_dirs: list[Path]) -> Path:
    """The slot for this set of rule directories."""
    slot = hashlib.sha256(b"rulesets")
    for directory in extra_dirs:
        slot.update(b"\0" + os.fsencode(directory.resolve()))
    return cache_root() / "rulesets" / f"{slot.hexdigest()[:16]}.json"


def locale_entry_path(tag: str) -> Path:
    """The slot for the generated spelling rule of locale `tag`.

    One slot per locale, so a changed allowlist or generator overwrites it rather
    than adding a file. Two allowlists for one locale, in two projects or in two
    overrides of one config, take turns in the slot, and each turn costs a proof.
    """
    return cache_root() / "rulesets" / f"locale-{tag}.json"


def generated_key(origin: str, document: dict) -> str | None:
    """The content key of one generated rule document, or None when JSON cannot
    hold it exactly, in which case the rule is proved on every run.

    Keyed on the document rather than on the generator's source: the locale and
    the allowlist reach the proof only through the document, so any change to
    them or to the generator that changes the rule also changes the key. The
    text keeps the document's key order, which decides the order of
    equal-length alternatives in the pattern.
    """
    try:
        text = json.dumps(document, ensure_ascii=True, separators=(",", ":"))
        if json.loads(text) != document:
            return None
    except (TypeError, ValueError):
        return None
    return content_key([(origin, text)])


def content_key(sources: list[tuple[str, str]]) -> str:
    """Hash of everything a verified load depends on: the package version, the
    loader's source, and each rule file's name and text, in load order."""
    import platform

    import regex
    import yaml

    from . import __version__

    digest = hashlib.sha256()
    digest.update(__version__.encode() + b"\0")
    digest.update(source_digest(_LOADER_SOURCES).encode())
    digest.update(
        repr(
            (
                platform.python_implementation(),
                platform.python_version(),
                regex.__version__,
                yaml.__version__,
                getattr(yaml, "__with_libyaml__", False),
                yaml._yaml.get_version_string() if getattr(yaml, "__with_libyaml__", False) else None,
            )
        ).encode()
    )
    for origin, text in sources:
        identity = str(Path(origin).resolve()) if Path(origin).is_file() else origin
        digest.update(b"\0" + os.fsencode(identity) + b"\0")
        digest.update(hashlib.sha256(text.encode("utf-8")).digest())
    return digest.hexdigest()


def read(path: Path, key: str) -> Documents | None:
    """The documents stored under `key`, or None when the entry is absent, holds
    another key, or fails its checksum or shape check."""
    try:
        if not trusted_cache_path(path):
            return None
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
        if not trusted_cache_path(path.parent, create=True):
            return
        if path.exists() and not trusted_cache_path(path):
            return
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
