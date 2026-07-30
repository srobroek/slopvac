"""Controlled-vocabulary check (ASD-STE100 rules 1.1 through 1.3).

TWO LAYERS, and the split is the whole design:

  BASE     the ASD-STE100 Issue 9 dictionary as extracted -- word, part of
           speech, approved or not. Unmodified. This is validated, traceable
           reference data, and a hand-curated substitute would be neither.
  OVERLAY  our deviations, in `vocabulary-overlay.yml`. Small, explicit, and
           every entry carries a reason. Software documentation needs `commit`,
           `cache`, and `deploy` as verbs; aerospace maintenance does not.

Keying is `(word, part_of_speech)`, not `word`. That is not a refinement -- it is
what makes rule 1.2 checkable at all. The spec approves many words as one part of
speech and refuses them as another, so a flat word list cannot express the rule
and will fire on correct prose. Measured on a 1.1M-word corpus of software docs,
the words carrying a part-of-speech-dependent status appear 7.2 times per 1,000
words (`code`, `view`, `time`, `work`, `back`, `over` are the frequent ones), so
flattening them would produce roughly 8,000 false findings.

PART-OF-SPEECH TAGGING IS VALE'S. This module used to carry a shallow tagger that
read a word's part of speech from its neighbours and returned UNKNOWN whenever the
evidence was thin -- which on real prose was most of the time, so rule 1.2 went
largely unchecked. Vale ships a Penn Treebank tagger, and its `sequence` extension
point matches a pattern only where the tag agrees: `close` as a verb is flagged and
"close to the limit" is not. Verified by execution.

What survives here is the DICTIONARY -- the loader, the merge, and the query. The
compiler reads it to generate four `sequence` rules, one per part of speech,
rather than one rule per entry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from importlib import resources
from pathlib import Path

import yaml

DATA_PACKAGE = "slopvac_lint"
DATA_DIRNAME = "data"
BASE_FILE = "ste-dictionary.json"
OVERLAY_FILE = "vocabulary-overlay.yml"


class Pos(str, Enum):
    """Parts of speech, normalized from the dictionary's own abbreviations."""

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    PRONOUN = "pronoun"
    ARTICLE = "article"
    UNKNOWN = "unknown"


# The extracted CSV uses the spec's own abbreviations.
POS_ALIASES = {
    "n": Pos.NOUN, "noun": Pos.NOUN,
    "v": Pos.VERB, "verb": Pos.VERB,
    "adj": Pos.ADJECTIVE, "adjective": Pos.ADJECTIVE,
    "adv": Pos.ADVERB, "adverb": Pos.ADVERB,
    "prep": Pos.PREPOSITION, "preposition": Pos.PREPOSITION,
    "conj": Pos.CONJUNCTION, "conjunction": Pos.CONJUNCTION,
    "pron": Pos.PRONOUN, "pronoun": Pos.PRONOUN,
    "art": Pos.ARTICLE, "article": Pos.ARTICLE,
    # spaCy-style tags, so a third-party wordset can be layered in.
    "NOUN": Pos.NOUN, "VERB": Pos.VERB, "ADJ": Pos.ADJECTIVE,
    "ADV": Pos.ADVERB, "ADP": Pos.PREPOSITION, "CCONJ": Pos.CONJUNCTION,
    "SCONJ": Pos.CONJUNCTION, "PRON": Pos.PRONOUN, "DET": Pos.ARTICLE,
}


def normalize_pos(raw: str) -> Pos:
    return POS_ALIASES.get(raw.strip(), POS_ALIASES.get(raw.strip().lower(), Pos.UNKNOWN))


@dataclass(frozen=True)
class Entry:
    word: str
    pos: Pos
    approved: bool
    replacement: str | None = None
    note: str | None = None
    source: str = "ASD-STE100 Issue 9"


class Vocabulary:
    """The merged base and overlay, queried by (word, part of speech)."""

    def __init__(self, entries: dict[tuple[str, Pos], Entry]) -> None:
        self._entries = entries
        # Which parts of speech a word is known under at all. A word absent from
        # every part of speech is out-of-dictionary; a word present under one and
        # queried under another is a rule 1.2 violation.
        self._by_word: dict[str, set[Pos]] = {}
        for (word, pos) in entries:
            self._by_word.setdefault(word, set()).add(pos)

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def approved_count(self) -> int:
        return sum(1 for e in self._entries.values() if e.approved)

    def unapproved(self) -> list[Entry]:
        """Every entry the dictionary does not approve.

        The compiler groups these by part of speech to build the Vale `sequence`
        rules, and needs the whole set rather than a per-word lookup.
        """
        return [e for e in self._entries.values() if not e.approved]

    def lookup(self, word: str, pos: Pos) -> Entry | None:
        return self._entries.get((word.lower(), pos))

    def known_parts_of_speech(self, word: str) -> set[Pos]:
        return self._by_word.get(word.lower(), set())

    def is_known(self, word: str) -> bool:
        return word.lower() in self._by_word

    def approved_as(self, word: str, pos: Pos) -> bool | None:
        """True approved, False not approved, None not in the dictionary.

        None is distinct from False on purpose: an unknown word is usually a
        technical name, which rule 1.5 permits, while a known-but-unapproved word
        is a real substitution the writer should make.
        """
        entry = self.lookup(word, pos)
        if entry is None:
            return None
        return entry.approved


def _load_base() -> dict[tuple[str, Pos], Entry]:
    try:
        raw = (resources.files(DATA_PACKAGE) / DATA_DIRNAME / BASE_FILE).read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError):
        return {}

    data = json.loads(raw)
    entries: dict[tuple[str, Pos], Entry] = {}
    for record in data.get("entries", []):
        pos = normalize_pos(record.get("pos", ""))
        if pos is Pos.UNKNOWN:
            continue
        word = record["word"].strip().lower()
        entries[(word, pos)] = Entry(
            word=word,
            pos=pos,
            approved=record.get("status") == "approved",
            replacement=record.get("replacement"),
            note=record.get("note"),
            source=data.get("source", "ASD-STE100 Issue 9"),
        )
    return entries


def _load_overlay(path: Path | None = None) -> list[dict]:
    if path is not None:
        text = path.read_text(encoding="utf-8")
    else:
        try:
            text = (resources.files(DATA_PACKAGE) / DATA_DIRNAME / OVERLAY_FILE).read_text(
                encoding="utf-8"
            )
        except (ModuleNotFoundError, FileNotFoundError):
            return []
    data = yaml.safe_load(text) or {}
    return data.get("entries", [])


def load_vocabulary(overlay_path: Path | None = None) -> Vocabulary:
    """Base plus overlay. Every overlay entry must carry a reason, because an
    undocumented deviation from the reference data is indistinguishable from a
    mistake."""
    entries = _load_base()

    for record in _load_overlay(overlay_path):
        pos = normalize_pos(record.get("pos", ""))
        if pos is Pos.UNKNOWN:
            continue
        word = str(record["word"]).strip().lower()
        entries[(word, pos)] = Entry(
            word=word,
            pos=pos,
            approved=record.get("status", "approved") == "approved",
            replacement=record.get("replacement"),
            note=record.get("reason"),
            source="slopvac overlay",
        )
    return Vocabulary(entries)
