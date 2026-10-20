"""The closed value sets that configs, rules, and findings share.

Plain enums with no pydantic import. The CLI declares its click choices from
them when the module loads, and `slopvac --version` should not have to build the
config and rule models before it can print one line. `config` and `model` use
them as field types.
"""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    """A finding's weight. `off` is a level rather than a deletion so that a
    disabled rule still resolves, and `slopvac rules` can report it as off."""

    OFF = "off"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        return {"off": 0, "suggestion": 1, "warning": 2, "error": 3}[self.value]

    def at_least(self, floor: Severity) -> bool:
        return self.rank >= floor.rank


class Profile(str, Enum):
    """Strictness tier.

    STRICT is technical documentation: reference, specs, API docs, runbooks.
    NORMAL is general writing held to a high bar: README, guides, ADRs, essays.
    RELAXED keeps only high-level readability rules: notes, comments, drafts.

    The tiers are NOT a simple ordering. Two rules invert deliberately -- see
    profiles.py -- because agentless passive is correct in a spec and wrong in a
    README, so passive voice is advisory at strict and enforced at normal.
    """

    STRICT = "strict"
    NORMAL = "normal"
    RELAXED = "relaxed"


class Mode(str, Enum):
    """Input surface selected for a lint run."""

    PROSE = "prose"
    CODE_COMMENTS = "code-comments"


class Tier(str, Enum):
    """How a rule behaves per profile. Mirrors `Profile` but describes the
    rule's own shipped disposition rather than the project's choice."""

    ENFORCED = "enforced"
    ADVISORY = "advisory"
    EXCLUDED = "excluded"


class RuleKind(str, Enum):
    """The checker that executes this rule.

    TOKENS       -- literal phrases, word-boundary matched.
    PATTERN      -- a regex with named-group support.
    SUBSTITUTION -- a from -> to map; the message names the replacement.
    VOCABULARY   -- POS-keyed controlled-vocabulary lookup (STE rule 1.2).
    METRIC       -- a counted measurement against a threshold (sentence length,
                    passive ratio, syllables per word).
    STRUCTURE    -- block-level shape (paragraph sentence count, list form).
    JUDGEMENT    -- not mechanizable; carried so writing and review guidance
                    read one source of truth. Never produces a finding.
    """

    TOKENS = "tokens"
    PATTERN = "pattern"
    SUBSTITUTION = "substitution"
    VOCABULARY = "vocabulary"
    METRIC = "metric"
    STRUCTURE = "structure"
    JUDGEMENT = "judgement"


class Scope(str, Enum):
    """Where in the parsed document the rule applies.

    Prose excludes code fences, inline code, URLs, and front matter. `raw` reaches
    everything, which only formatting rules should want.
    """

    PROSE = "prose"
    HEADING = "heading"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    DOCUMENT = "document"
    RAW = "raw"


class TextType(str, Enum):
    """STE's procedural/descriptive split, which selects the word cap: 20 words
    for an instruction, 25 for descriptive text (rules 5.1 and 6.3).

    The spec gives no mechanical test for the distinction, so the detector uses
    imperative mood plus note/warning/caution markers. ANY means the rule does
    not care.
    """

    ANY = "any"
    PROCEDURAL = "procedural"
    DESCRIPTIVE = "descriptive"
    SAFETY = "safety"
