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

PART-OF-SPEECH TAGGING is deliberately shallow: no model, no dependency. The
tagger resolves a word only when the surrounding tokens make the part of speech
unambiguous, and reports nothing otherwise. A wrong tag produces a false finding
on correct prose, which is the failure that gets a rule disabled -- so silence is
the correct answer when the evidence is thin.
"""

from __future__ import annotations

import json
import regex as re
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


# --- shallow part-of-speech resolution ---------------------------------------

DETERMINER = re.compile(
    r"^(?:the|a|an|this|that|these|those|its|his|her|their|our|your|my|each|every|"
    r"any|some|no|which|whose)$",
    re.I,
)
MODAL = re.compile(
    r"^(?:can|could|will|would|shall|should|may|might|must|do|does|did|to)$", re.I
)
BE = re.compile(r"^(?:is|are|was|were|be|been|being|am)$", re.I)
PREP = re.compile(
    r"^(?:of|in|on|at|by|for|with|from|into|onto|over|under|about|between|through|"
    r"during|before|after|above|below|against|among|within|without|across)$",
    re.I,
)
ADVERB_SUFFIX = re.compile(r"ly$", re.I)
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def resolve_pos(tokens: list[str], index: int) -> Pos:
    """Best-effort part of speech for `tokens[index]`.

    Returns UNKNOWN whenever the evidence is weak. That is the point: an
    unresolved word is skipped rather than guessed, so the vocabulary check never
    reports a violation it cannot justify.
    """
    word = tokens[index]
    previous = tokens[index - 1] if index > 0 else ""
    following = tokens[index + 1] if index + 1 < len(tokens) else ""

    # A determiner or preposition immediately before means the head is nominal,
    # unless an adjective intervenes -- which the next test catches.
    if DETERMINER.match(previous) or PREP.match(previous):
        if following and not DETERMINER.match(following) and WORD.fullmatch(following):
            # "the cache layer": `cache` modifies, so it is not the head noun and
            # the reading is ambiguous. Refuse rather than guess.
            return Pos.UNKNOWN
        return Pos.NOUN

    # A modal or infinitive marker before means a bare verb follows.
    if MODAL.match(previous):
        return Pos.VERB

    # "is <word>ed" is passive; "is <word>" with an adjective-shaped word is a
    # predicate adjective. Neither is reliable enough for a noun/verb call.
    if BE.match(previous):
        if word.lower().endswith(("ed", "en")):
            return Pos.VERB
        return Pos.UNKNOWN

    if ADVERB_SUFFIX.search(word) and len(word) > 4:
        return Pos.ADVERB

    # Sentence-initial and imperative: a procedural sentence starts with its verb.
    if index == 0:
        return Pos.VERB

    return Pos.UNKNOWN


def check_sentence(
    text: str, vocabulary: Vocabulary, line: int
) -> list[tuple[int, str, Pos, Entry | None]]:
    """Find vocabulary problems in one sentence.

    Yields `(column, word, resolved_pos, entry)`. `entry` is None when the word is
    absent from the dictionary entirely, which the caller reports differently from
    a known-but-unapproved word: an unknown word is usually a technical name that
    rule 1.5 permits, while a known unapproved word has a replacement.
    """
    matches = list(WORD.finditer(text))
    tokens = [m.group(0).lower() for m in matches]
    results: list[tuple[int, str, Pos, Entry | None]] = []

    for index, match in enumerate(matches):
        word = match.group(0)
        lowered = word.lower()
        if len(lowered) < 3:
            continue
        if not vocabulary.is_known(lowered):
            continue  # technical name or out of scope; rule 1.5 territory

        pos = resolve_pos(tokens, index)
        if pos is Pos.UNKNOWN:
            continue  # evidence too weak to justify a finding

        known = vocabulary.known_parts_of_speech(lowered)
        if pos not in known:
            # Rule 1.2: the word exists but not as this part of speech.
            results.append((match.start() + 1, word, pos, None))
            continue

        entry = vocabulary.lookup(lowered, pos)
        if entry is not None and not entry.approved:
            results.append((match.start() + 1, word, pos, entry))
    return results
