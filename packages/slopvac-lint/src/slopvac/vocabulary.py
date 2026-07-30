"""The word blocklist: opt-in, and the project's own.

A BLOCKLIST, NOT AN ALLOWLIST, and that reverses what this module used to be. It
shipped an extracted ASD-STE100 Issue 9 dictionary and treated the 859 approved
words as the permitted set, so every word outside them drew a finding. Measured on
an 8-document corpus of ordinary software prose that rule alone was 51% of all
findings at `strict` (443 of 864), and drove all 8 documents to a score of 0.0 --
including documents with zero errors.

The failure was structural, not a matter of calibration:

  ABSENCE IS NOT DISAPPROVAL. 51% of the hits (828 across 421 words) were words
  with no dictionary entry at all -- `reviewer`, `transaction`, `threshold`,
  `subprocessor`, plus inflections the source lists only as base forms (`needs`,
  `matches`, `requires`). No override could reach them, because there was no entry
  to override.

  THE SOURCE IS DELIBERATELY INCOMPLETE. ASD-STE100 excludes technical nouns and
  technical verbs by design and delegates them to its own rules 1.5 through 1.13,
  so the wordlist was never meant to stand alone. Our extraction notes predicted
  exactly this in writing, and the one third-party implementation we found
  requires the user to load a company technical-noun list first.

  MEMBERSHIP IS CONTEXT-DEPENDENT. The specification's own worked example makes one
  word legal in one sentence and illegal in another. A lexical test cannot express
  that, so it fires on correct prose: `never`, `already`, `case`, `false`, `order`,
  and `whole` were all flagged in normal use.

So the packaged dictionary is GONE -- not disabled, deleted. A default that is
wrong for everyone outside aerospace maintenance is not a default, and keeping it
loadable would have kept the wrong answer one config key away. Deleting it also
ends this package's redistribution of ASD-STE100 content, which was scoped.

WHAT REPLACES IT: nothing, until a project opts in. Point `[vocabulary] path` at a
TOML file of words your project refuses, each with a reason. `examples/blocklist.toml`
is a working starter -- the eleven entries this repo actually authored, which were
the only editorial content in the old 12.5 KB overlay worth keeping.

Keying stays `(word, part_of_speech)`. Part-of-speech tagging is Vale's: its
`sequence` extension point matches only where the Penn tag agrees, so `close` as a
verb is flagged and "close to the limit" is not. That is why a blocklist of any
size costs at most four generated rules.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml


class Pos(str, Enum):
    """Parts of speech, normalized from whatever abbreviation the file uses."""

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    ARTICLE = "article"
    UNKNOWN = "unknown"


# Accepts the abbreviations a human writes, the words they might write instead,
# and spaCy-style tags, so a wordlist exported from another tool loads unchanged.
POS_ALIASES = {
    "n": Pos.NOUN, "noun": Pos.NOUN,
    "v": Pos.VERB, "verb": Pos.VERB,
    "adj": Pos.ADJECTIVE, "adjective": Pos.ADJECTIVE,
    "adv": Pos.ADVERB, "adverb": Pos.ADVERB,
    "prep": Pos.PREPOSITION, "preposition": Pos.PREPOSITION,
    "conj": Pos.CONJUNCTION, "conjunction": Pos.CONJUNCTION,
    "pron": Pos.PRONOUN, "pronoun": Pos.PRONOUN,
    "art": Pos.ARTICLE, "article": Pos.ARTICLE,
    "NOUN": Pos.NOUN, "VERB": Pos.VERB, "ADJ": Pos.ADJECTIVE,
    "ADV": Pos.ADVERB, "ADP": Pos.PREPOSITION, "CCONJ": Pos.CONJUNCTION,
    "SCONJ": Pos.CONJUNCTION, "PRON": Pos.PRONOUN, "DET": Pos.ARTICLE,
}


def normalize_pos(raw: str) -> Pos:
    return POS_ALIASES.get(raw.strip(), POS_ALIASES.get(raw.strip().lower(), Pos.UNKNOWN))


class VocabularyError(Exception):
    """A blocklist file that cannot be loaded, or that is missing a reason.

    Raised rather than warned. A blocklist is opt-in, so the project asked for it
    by name; silently linting with an empty one would report a clean document and
    be indistinguishable from a pass.
    """


@dataclass(frozen=True)
class Entry:
    """One refused word.

    `reason` is required, and that is the one piece of validation this loader does.
    An entry with no reason cannot be reviewed, argued with, or removed later by
    anyone but its author -- and the old dictionary's real defect was 1,275 of
    1,282 refusals carrying neither a reason nor a replacement.
    """

    word: str
    pos: Pos
    reason: str
    replacement: str | None = None
    source: str = "project blocklist"


class Vocabulary:
    """The refused words, queried by (word, part of speech).

    Empty is a valid and expected state: it is what every project gets until one
    opts in. Every query answers "no finding" against it.
    """

    def __init__(self, entries: dict[tuple[str, Pos], Entry] | None = None) -> None:
        self._entries = dict(entries or {})
        self._by_word: dict[str, set[Pos]] = {}
        for (word, pos) in self._entries:
            self._by_word.setdefault(word, set()).add(pos)

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return bool(self._entries)

    def blocked(self) -> list[Entry]:
        """Every refused entry.

        The compiler groups these by part of speech to build the Vale `sequence`
        rules, and needs the whole set rather than a per-word lookup.
        """
        return list(self._entries.values())

    def fingerprint(self) -> str:
        """A stable identity for this wordlist's CONTENT.

        `lint` groups files by this so one Vale compile serves every file that
        shares a wordlist. Content rather than the source path, because two
        overrides can point at the same file, and an empty wordlist is an empty
        wordlist however it was reached -- keying on the path would compile the
        same ini twice and split one report into two runs for no reason.
        """
        payload = "\0".join(
            sorted(f"{word}\0{pos.value}" for word, pos in self._entries)
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def lookup(self, word: str, pos: Pos) -> Entry | None:
        return self._entries.get((word.lower(), pos))

    def blocked_parts_of_speech(self, word: str) -> set[Pos]:
        return self._by_word.get(word.lower(), set())

    def is_blocked(self, word: str, pos: Pos) -> bool:
        """Whether this word is refused AS THIS PART OF SPEECH.

        The only question a blocklist answers. There is deliberately no
        `is_known`: under allowlist semantics an unknown word was a finding, and
        that produced 828 of them on correct prose.
        """
        return (word.lower(), pos) in self._entries


def _read_records(path: Path) -> list[dict]:
    """Parse a blocklist by suffix. TOML, YAML, and JSON all accepted.

    TOML is the documented form and what `examples/blocklist.toml` uses: a
    blocklist entry's whole value is its reason, and JSON cannot carry a comment
    beside one. JSON stays accepted because a wordlist exported from another tool
    arrives that way, and refusing it would be gatekeeping over syntax.

    Suffix dispatch rather than sniffing, so a malformed file reports a parse
    error in the format the author intended instead of falling through three
    parsers and blaming the last.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise VocabularyError(f"cannot read blocklist {path}: {exc}") from exc

    suffix = path.suffix.lower()
    try:
        if suffix == ".toml":
            data = tomllib.loads(raw.decode("utf-8"))
        elif suffix in {".yml", ".yaml"}:
            data = yaml.safe_load(raw.decode("utf-8")) or {}
        elif suffix == ".json":
            data = json.loads(raw.decode("utf-8"))
        else:
            raise VocabularyError(
                f"blocklist {path} has an unrecognized suffix '{suffix}'; use "
                f".toml, .yml, or .json"
            )
    except (tomllib.TOMLDecodeError, yaml.YAMLError, json.JSONDecodeError) as exc:
        raise VocabularyError(f"cannot parse blocklist {path}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise VocabularyError(f"blocklist {path} is not valid UTF-8: {exc}") from exc

    if not isinstance(data, dict):
        raise VocabularyError(f"blocklist {path} must be a table, not {type(data).__name__}")

    # A WRONG TOP-LEVEL KEY IS AN ERROR, NOT AN EMPTY WORDLIST. `data.get(...)`
    # alone meant a file whose array of tables was named `[[words]]` -- the obvious
    # guess -- loaded as zero entries, and every vocabulary rule then reported the
    # document clean while announcing nothing. That is precisely the outcome
    # `VocabularyError` exists to prevent: the project asked for the gate by name.
    if "entries" not in data:
        named = ", ".join(f"`{key}`" for key in sorted(data)) or "nothing"
        raise VocabularyError(
            f"blocklist {path} has no `entries` array; it defines {named}. "
            f"Each word is a `[[entries]]` table -- see examples/blocklist.toml"
        )
    records = data["entries"]
    if not isinstance(records, list):
        raise VocabularyError(f"blocklist {path}: `entries` must be an array of tables")
    return records


def load_blocklist(path: Path | None) -> Vocabulary:
    """Load a project blocklist, or return an empty one when none is configured.

    `None` returns empty rather than raising: no blocklist is the default state,
    not an error. A path that is set and unloadable IS an error -- see
    `VocabularyError`.
    """
    if path is None:
        return Vocabulary()

    entries: dict[tuple[str, Pos], Entry] = {}
    for index, record in enumerate(_read_records(path)):
        if not isinstance(record, dict):
            raise VocabularyError(f"{path}: entry {index + 1} is not a table")

        word = str(record.get("word", "")).strip().lower()
        if not word:
            raise VocabularyError(f"{path}: entry {index + 1} has no `word`")

        pos = normalize_pos(str(record.get("pos", "")))
        if pos is Pos.UNKNOWN:
            raise VocabularyError(
                f"{path}: entry '{word}' has an unrecognized `pos` "
                f"{record.get('pos')!r}; use noun, verb, adjective, adverb, "
                f"preposition, conjunction, pronoun, or article"
            )

        reason = str(record.get("reason", "")).strip()
        if not reason:
            # See `Entry.reason`. The old dictionary's 1,275 reasonless refusals
            # are the argument for making this fatal rather than a warning.
            raise VocabularyError(
                f"{path}: entry '{word}' ({pos.value}) has no `reason`. Every "
                f"refused word needs one, or nobody can review or remove it later."
            )

        replacement = record.get("replacement")
        entries[(word, pos)] = Entry(
            word=word,
            pos=pos,
            reason=reason,
            replacement=str(replacement) if replacement else None,
            source=str(path),
        )
    return Vocabulary(entries)
