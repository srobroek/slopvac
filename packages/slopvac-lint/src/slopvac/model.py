"""Rule, finding, and score types.

A rule is DATA, not code. Every rule lives in a YAML file under `rules/<category>/`
and is validated against `Rule` at load time, so a malformed rule fails the run
instead of silently matching nothing -- the failure mode this repo already
documented for Vale, where an unresolvable style reports every file as clean.

The `kind` field selects which checker executes the rule. Adding a lexical or
substitution rule needs no Python; only a genuinely new detection strategy does.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import Severity


class Tier(str, Enum):
    """How a rule behaves per profile. Mirrors config.Profile but describes the
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
    JUDGEMENT    -- not mechanizable; carried so the agentic reviewer can load a
                    single source of truth. Never produces a finding.
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


class Provenance(BaseModel):
    """Where a rule came from. Required, because a rule nobody can trace is a
    rule nobody can argue with.

    `ste_ref` is issue-qualified (`"9:1.2"`) because rule numbers are NOT portable
    across issues -- Issue 7 rule 2.3 became Issue 9 rule 4.5.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="Human-readable origin, e.g. 'ASD-STE100', 'Orwell 1946'.")
    ste_ref: str | None = Field(
        default=None,
        pattern=r"^\d+:\d+\.\d+$|^\d+:GR-\d+$",
        description="Issue-qualified STE rule number, e.g. '9:1.2' or '9:GR-2'. "
        "A citation only; no spec text is reproduced.",
    )
    orwell_ref: str | None = Field(
        default=None, description="Orwell rule id, e.g. 'stale-figure'."
    )
    url: str | None = None
    note: str | None = Field(
        default=None,
        description="Why this rule is worded as it is, where a reader would "
        "otherwise assume it restates the source verbatim.",
    )


class Example(BaseModel):
    """A before/after pair. Doubles as a test fixture: the loader asserts `bad`
    matches and `good` does not, so a rule cannot ship with a broken pattern."""

    model_config = ConfigDict(extra="forbid")

    bad: str
    good: str | None = None
    note: str | None = None


class Rule(BaseModel):
    """One check. Loaded from YAML, never constructed in code."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Unique within its category. Fully qualified as "
        "`<category>.<id>` everywhere a user sees it.",
    )
    name: str = Field(description="Short imperative label.")
    kind: RuleKind
    severity: Severity = Field(
        default=Severity.WARNING,
        description="The rule's shipped level. A category cap can lower it, "
        "never raise it.",
    )
    message: str = Field(
        description="Shown on a finding. Names the fix, not the violation: "
        "'use \"start\"' beats 'unapproved word'. `{match}` and `{replacement}` "
        "interpolate.",
    )
    scope: Scope = Scope.PROSE
    text_type: TextType = TextType.ANY

    tiers: dict[str, Tier] = Field(
        default_factory=lambda: {
            "strict": Tier.ENFORCED,
            "normal": Tier.ENFORCED,
            "relaxed": Tier.EXCLUDED,
        },
        description="Disposition per profile. Two rules invert strict/normal on "
        "purpose -- see profiles.py.",
    )

    # --- kind-specific payloads; exactly one must be populated ----------------
    tokens: list[str] | None = Field(
        default=None, description="Literal phrases for kind=tokens."
    )
    pattern: str | None = Field(default=None, description="Regex for kind=pattern.")
    substitutions: dict[str, str] | None = Field(
        default=None, description="from -> to for kind=substitution."
    )
    metric: str | None = Field(
        default=None, description="Metric name for kind=metric, e.g. 'sentence_words'."
    )
    threshold: float | None = Field(default=None, description="Limit for kind=metric.")
    comparison: Literal["gt", "gte", "lt", "lte"] = "gt"

    ignore_case: bool = True
    match_all_caps: bool = Field(
        default=False,
        description="Report a match written entirely in capitals. Default False: an "
        "all-caps token is usually a normative keyword (RFC 2119 MUST/SHOULD), an "
        "identifier (DATABASE_URL), an initialism (JSON/TLS), or a safety marker "
        "(WARNING), none of which the prose rules are about. Set True only for a "
        "rule about the capitals themselves.",
    )
    exceptions: list[str] = Field(
        default_factory=list,
        description="Named, closed exception list. A suppression annotation must "
        "cite one of these by name; 'reads better' is deliberately never here.",
    )
    allowlist: list[str] = Field(
        default_factory=list,
        description="Literal strings that never fire, even when the pattern "
        "matches. Dead metaphors and identifiers live here.",
    )
    examples: list[Example] = Field(default_factory=list)
    provenance: Provenance
    judgement_question: str | None = Field(
        default=None,
        description="Required for kind=judgement: the question the reviewer must "
        "answer. Must be decidable, not a matter of taste.",
    )
    fix: str | None = Field(default=None, description="The rewrite operation.")

    # Set by the loader.
    category: str = Field(default="", description="Owning category; set on load.")

    @property
    def qualified_id(self) -> str:
        return f"{self.category}.{self.id}" if self.category else self.id

    @model_validator(mode="after")
    def _check_payload(self) -> Rule:
        required = {
            RuleKind.TOKENS: "tokens",
            RuleKind.PATTERN: "pattern",
            RuleKind.SUBSTITUTION: "substitutions",
            RuleKind.METRIC: "metric",
        }
        field = required.get(self.kind)
        if field and getattr(self, field) is None:
            raise ValueError(f"kind={self.kind.value} requires `{field}`")
        if self.kind is RuleKind.METRIC and self.threshold is None:
            raise ValueError("kind=metric requires `threshold`")
        if self.kind is RuleKind.JUDGEMENT and not self.judgement_question:
            raise ValueError("kind=judgement requires `judgement_question`")
        if self.kind is RuleKind.JUDGEMENT and self.severity is not Severity.OFF:
            # A judgement rule cannot fire mechanically; letting it carry a real
            # severity would imply the linter checks it.
            object.__setattr__(self, "severity", Severity.SUGGESTION)
        return self

    def tier_for(self, profile: str) -> Tier:
        return self.tiers.get(profile, Tier.EXCLUDED)


class Category(BaseModel):
    """A group of rules, and the unit users enable, disable, and score by."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    description: str
    weight: float = Field(
        default=1.0,
        ge=0,
        description="Contribution to the overall score, before any config "
        "override.",
    )
    max_per_100_words: dict[str, float] = Field(
        default_factory=dict,
        description="Density budget per profile. Absent means no budget.",
    )
    recommended_for: list[str] = Field(
        default_factory=list,
        description="Genres this category suits. The skill reads this to "
        "recommend a selection to the user.",
    )
    rules: list[Rule] = Field(default_factory=list)


class Finding(BaseModel):
    """One violation, at one position."""

    model_config = ConfigDict(extra="forbid")

    path: str
    line: int
    column: int = 1
    end_column: int | None = None
    rule_id: str
    category: str
    severity: Severity
    message: str
    matched_text: str = ""
    replacement: str | None = None
    ste_ref: str | None = None
    orwell_ref: str | None = None

    def as_line(self) -> str:
        """One-line report, matching the existing gate's shape so downstream
        parsers keep working."""
        label = "ERROR" if self.severity is Severity.ERROR else self.severity.value.upper()
        return f"{self.path} {label} {self.rule_id} line {self.line}: {self.message}"


class CategoryScore(BaseModel):
    """Per-category result."""

    model_config = ConfigDict(extra="forbid")

    category: str
    findings: int
    errors: int
    warnings: int
    suggestions: int
    per_100_words: float
    #: Errors and warnings per 100 words -- the figure the budget is checked
    #: against. Reported separately from `per_100_words` so a failure reason can
    #: quote the number that actually failed; quoting the raw density instead
    #: reads as a contradiction when the two differ by a wall of suggestions.
    gating_per_100_words: float = 0.0
    budget: float | None = None
    score: float = Field(ge=0, le=100)
    over_budget: bool = False


class DocumentScore(BaseModel):
    """The whole result for one file. This is what `--format json` emits and what
    the CI action reports."""

    model_config = ConfigDict(extra="forbid")

    path: str
    profile: str
    words: int
    sentences: int
    paragraphs: int
    findings: list[Finding] = Field(default_factory=list)
    categories: list[CategoryScore] = Field(default_factory=list)

    total_findings: int = 0
    errors: int = 0
    warnings: int = 0
    suggestions: int = 0
    per_100_words: float = 0.0
    score: float = Field(default=100.0, ge=0, le=100)
    passed: bool = True
    failure_reasons: list[str] = Field(
        default_factory=list,
        description="Which threshold failed, named. An exit code with no reason "
        "is not actionable.",
    )
    unchecked: list[str] = Field(
        default_factory=list,
        description="What did NOT run, and why. A missing vale binary or an "
        "unsynced style must never read as a pass.",
    )
