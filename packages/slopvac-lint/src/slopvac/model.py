"""Rule, finding, and score types.

A rule is DATA, not code. Every rule lives in a YAML file under `rules/<category>/`
and is validated against `Rule` at load time, so a malformed rule fails the run
instead of silently matching nothing -- the failure mode this repo already
documented for Vale, where an unresolvable style reports every file as clean.

The `kind` field selects which checker executes the rule. Adding a lexical or
substitution rule needs no Python; only a genuinely new detection strategy does.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

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


# The genre vocabulary the write-docs skill classifies a document into (its genre
# table). `Category.recommended_for` is typed against it so the review skill's
# `genre` value selects categories by equality rather than by a mapping table
# nobody maintains. Code comments are not a genre here: the skills route them to
# the language's own conventions.
Genre = Literal["consumer", "internal", "change-comms", "reference", "informal"]


class Dimension(str, Enum):
    """The rubric-facing axis: what KIND of defect a rule names, independent of
    which checker executes it.

    Single-valued per rule and orthogonal to `category`. `category` stays the unit
    a user enables, weights, and scores by; `dimension` is the unit a rubric and a
    dimension-keyed pack select by. The two are genuinely different partitions --
    `wording` spans 13 categories and every category spans between 1 and 6
    dimensions -- so a single-valued `dimension` is what makes dimension-keyed
    packs disjoint by construction.

    Seven of the twelve carry a LAMP category as their primary label; the other
    five (`agency`, `veracity`, `scope`, `presentation`, `inclusion`) name defects
    LAMP has no category for, which is why LAMP is a crosswalk here rather than
    the vocabulary itself.
    """

    SPECIFICITY = "specificity"
    INFLATION = "inflation"
    STALENESS = "staleness"
    REDUNDANCY = "redundancy"
    ARCHITECTURE = "architecture"
    WORDING = "wording"
    CONSISTENCY = "consistency"
    AGENCY = "agency"
    VERACITY = "veracity"
    SCOPE = "scope"
    PRESENTATION = "presentation"
    INCLUSION = "inclusion"


class Ownership(str, Enum):
    """Which layer settles the rule.

    DETERMINISTIC        -- a checker executes it and the judgement layer never
                            sees it.
    SEEDED_ADJUDICATION  -- adjudication of a span some deterministic rule already
                            found. The existing `-core`/`-remainder` pair,
                            generalised: `seed_rule_ids` names the generators.
    DOCUMENT_PROBE       -- no deterministic trigger at all; the rule is handed a
                            block or a document and must locate its own span.

    Three modes rather than two, because "not mechanizable" hides the distinction
    that decides how a unit reaches the reviewer: a seeded rule is handed a span,
    a probe is handed a passage and may find nothing.
    """

    DETERMINISTIC = "deterministic"
    SEEDED_ADJUDICATION = "seeded_adjudication"
    DOCUMENT_PROBE = "document_probe"


class JudgementDimension(str, Enum):
    """A scored axis of the judgement rubric. Upper-case because these are the
    rubric's own names, quoted verbatim in packs and verdicts."""

    FIT = "FIT"
    HARM = "HARM"
    WARRANT = "WARRANT"
    REPAIR = "REPAIR"


class JudgementContract(BaseModel):
    """What a judgement rule promises the adjudication layer.

    Every field is load-bearing at call time, which is why none is optional: the
    pack cannot be generated without `admission` and `protects`, the verdict
    cannot be scored without `dims`, a verdict cannot be checked without
    `evidence_arity`, and a confirm cannot be assigned a severity without
    `judgement_ceiling`. A rule that declares none of this is a rule the layer
    would have to guess at, and guessing is what the ceiling exists to stop.
    """

    model_config = ConfigDict(extra="forbid")

    admission: str = Field(
        description="What must be true of the unit for the question to apply. "
        "Scope legality and double-jeopardy, in words a pack can print.",
    )
    protects: str = Field(
        description="The correct prose this rule must not flag. Names the "
        "preservation classes that outrank it, so the carve-out is stated once "
        "per rule rather than reprinted in every pack.",
    )
    dims: list[JudgementDimension] = Field(
        description="The rubric axes this rule is scored on. A rule asks two or "
        "three, not four: asking for a score nothing depends on invents variance "
        "that later reads as signal.",
    )
    evidence_arity: int = Field(
        ge=1,
        description="How many located spans a verdict must return. Non-local "
        "defects need two -- a repeat needs its antecedent, a term "
        "inconsistency needs both spellings.",
    )
    judgement_ceiling: Severity = Field(
        description="The most severe level a confirm may reach. This is how a "
        "judgement finding reaches `error` without the rule carrying a mechanical "
        "severity it cannot earn; a build-failing model finding has to be named "
        "rule by rule.",
    )
    rewrite_exempt: bool = Field(
        description="Whether this rule's fix may legitimately alter a protected "
        "token. False for almost every rule: a rewrite that edits a number, a "
        "path, or a negation is rejected mechanically rather than editorially.",
    )

    @model_validator(mode="after")
    def _check_contract(self) -> JudgementContract:
        for name in ("admission", "protects"):
            if not getattr(self, name).strip():
                raise ValueError(f"`judgement_contract.{name}` must not be empty")
        if not self.dims:
            raise ValueError(
                "`judgement_contract.dims` must name at least one scored axis; a "
                "rule scored on nothing cannot be confirmed"
            )
        seen: set[JudgementDimension] = set()
        for dim in self.dims:
            if dim in seen:
                raise ValueError(
                    f"`judgement_contract.dims` repeats {dim.value}; a weighted "
                    "axis counted twice is not the axis it claims to be"
                )
            seen.add(dim)
        if self.judgement_ceiling is Severity.OFF:
            raise ValueError(
                "`judgement_contract.judgement_ceiling` cannot be `off`: a "
                "ceiling of off makes every confirm unreachable, which is what "
                "`severity: off` on the rule already says"
            )
        return self


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

    # --- taxonomy and layer; required on every rule ---------------------------
    # Required rather than defaulted. A default would be silently wrong for most
    # of the catalog, and a taxonomy that guesses is a taxonomy nobody can select
    # by: the whole point of `dimension` is that a dimension-keyed pack contains
    # exactly the rules that name that defect.
    dimension: Dimension = Field(
        description="What kind of defect this rule names. Orthogonal to "
        "`category`, which stays the unit users enable and score by.",
    )
    ownership: Ownership = Field(
        description="Which layer settles the rule. Must agree with `kind`: a "
        "mechanical kind is `deterministic`, a judgement rule is "
        "`seeded_adjudication` or `document_probe`.",
    )
    seed_rule_ids: list[str] = Field(
        default_factory=list,
        description="Fully qualified ids of the deterministic rules whose matches "
        "this rule adjudicates. Required and non-empty for "
        "`ownership=seeded_adjudication`, empty for every other mode.",
    )
    judgement_contract: JudgementContract | None = Field(
        default=None,
        description="Required for kind=judgement, forbidden elsewhere. What the "
        "adjudication layer needs in order to call the rule at all.",
    )
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
        owners = {
            "tokens": RuleKind.TOKENS,
            "pattern": RuleKind.PATTERN,
            "substitutions": RuleKind.SUBSTITUTION,
            "metric": RuleKind.METRIC,
            "threshold": RuleKind.METRIC,
            "judgement_question": RuleKind.JUDGEMENT,
            "judgement_contract": RuleKind.JUDGEMENT,
        }
        for name, owner in owners.items():
            if getattr(self, name) is not None and self.kind is not owner:
                raise ValueError(
                    f"{self.id}: `{name}` is not valid for kind={self.kind.value}"
                )
        field = required.get(self.kind)
        if field and getattr(self, field) is None:
            raise ValueError(f"kind={self.kind.value} requires `{field}`")
        if self.kind is RuleKind.METRIC and self.threshold is None:
            raise ValueError("kind=metric requires `threshold`")

        # `exceptions` on a judgement rule USED to be a load error, on the
        # reasoning that a rule which emits no finding has nothing to suppress.
        # That was true of the carried-prose layer and is false of the
        # adjudication layer: a confirmed judgement finding is a finding, and the
        # named exception is what lets an author cite `quotation` against it
        # instead of overriding it unnamed. Deterministic exception handling is
        # unchanged; see engine.py, which still requires an annotation to cite a
        # name this list carries.

        # A judgement rule cannot fire mechanically, so it cannot own a
        # mechanical severity. `judgement_contract.judgement_ceiling` is where its
        # confirmable level lives.
        if self.kind is RuleKind.JUDGEMENT:
            if not self.judgement_question:
                raise ValueError("kind=judgement requires `judgement_question`")
            if self.judgement_contract is None:
                raise ValueError(
                    f"{self.id}: kind=judgement requires `judgement_contract`; a "
                    "rule the adjudication layer cannot admit, score, or cap is a "
                    "rule it would have to guess at"
                )
            if self.ownership is Ownership.DETERMINISTIC:
                raise ValueError(
                    f"{self.id}: kind=judgement cannot be "
                    f"ownership={Ownership.DETERMINISTIC.value}; no checker "
                    "executes a judgement rule"
                )
            if self.severity is not Severity.OFF:
                object.__setattr__(self, "severity", Severity.SUGGESTION)
        elif self.ownership is not Ownership.DETERMINISTIC:
            raise ValueError(
                f"{self.id}: kind={self.kind.value} is executed by a checker, so "
                f"ownership must be {Ownership.DETERMINISTIC.value}, not "
                f"{self.ownership.value}"
            )

        # Seeds are the generalised `-core`/`-remainder` link. Only a seeded rule
        # has them, and it is useless without them: with no generator, nothing
        # ever hands it a span.
        if self.ownership is Ownership.SEEDED_ADJUDICATION:
            if not self.seed_rule_ids:
                raise ValueError(
                    f"{self.id}: ownership="
                    f"{Ownership.SEEDED_ADJUDICATION.value} requires at least one "
                    "`seed_rule_ids` entry; with no generator nothing hands this "
                    "rule a span"
                )
        elif self.seed_rule_ids:
            raise ValueError(
                f"{self.id}: `seed_rule_ids` is not valid for "
                f"ownership={self.ownership.value}; only "
                f"{Ownership.SEEDED_ADJUDICATION.value} adjudicates another "
                "rule's matches"
            )
        seen_seeds: set[str] = set()
        for seed in self.seed_rule_ids:
            if not re.fullmatch(r"[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*", seed):
                raise ValueError(
                    f"{self.id}: seed '{seed}' is not a qualified "
                    "`category.rule` id"
                )
            if seed in seen_seeds:
                raise ValueError(f"{self.id}: seed '{seed}' is named twice")
            seen_seeds.add(seed)
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
    recommended_for: list[Genre] = Field(
        default_factory=list,
        description="Genres this category suits, in the vocabulary the write-docs "
        "and review-docs skills use, so a reviewer can select judgement rules by "
        "the genre it classified. A second vocabulary here selected zero rules for "
        "the skill's `consumer` genre.",
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
