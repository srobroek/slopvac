"""The machine-readable output contracts: `--format json` and `--format sarif`.

WHY THESE ARE MODELS AND NOT DICTS. Both payloads were hand-built dicts, and a
hand-built dict has no shape a caller can rely on. Three things went wrong with
that, all of them in this repo:

  A KEY COULD BE RENAMED WITHOUT ANYTHING FAILING. The CI action, the review
  skill, and `docs/` all read these payloads by key. Nothing connected the
  documented key to the emitted one, so the documentation was a claim rather
  than a description.

  SARIF IS A SPECIFICATION, and a dict literal cannot state that `level` is one
  of a closed set or that `partialFingerprints` is required for stable alert
  identity. GitHub rejects a malformed upload with a message about the whole
  file, not the field, so the cheapest place to catch it is here.

  `json.dumps(..., default=str)` HID TYPE ERRORS. A `Path` or an `Enum` reaching
  the encoder serialised as whatever `str()` gave, so a field that should have
  been a string got a `PosixPath` repr in some runs and not others.

The models are the schema, so `slopvac schema` can emit JSON Schema for both and
CI can publish it. That is the point: a consumer validates against the same
definition the tool serialises from.

SARIF FIELD NAMES ARE camelCase because the specification says so, and the
`alias` on each field is what keeps the Python side snake_case. Serialisation
must therefore always pass `by_alias=True` -- `emit()` does it, so callers do
not have to remember.
"""

from __future__ import annotations

import hashlib
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .config import Severity
from .model import CategoryScore, DocumentScore, Finding, Rule, RuleKind

# ---------------------------------------------------------------------------
# `--format json`
# ---------------------------------------------------------------------------


class CategorySummary(BaseModel):
    """One category rolled up across every linted document."""

    model_config = ConfigDict(extra="forbid")

    category: str
    findings: int = Field(ge=0)
    errors: int = Field(ge=0)
    warnings: int = Field(ge=0)
    suggestions: int = Field(ge=0)
    per_100_words: float = Field(ge=0)
    score: float = Field(ge=0, le=100)


class RunSummary(BaseModel):
    """Every document rolled into one result -- what a CI badge reads.

    Densities here are recomputed over TOTAL words rather than averaged over
    documents: averaging per-document densities lets a 30-word file outweigh a
    3,000-word one, which misreports a repository.
    """

    model_config = ConfigDict(extra="forbid")

    documents: int = Field(ge=0)
    words: int = Field(ge=0)
    findings: int = Field(ge=0)
    errors: int = Field(ge=0)
    warnings: int = Field(ge=0)
    suggestions: int = Field(ge=0)
    per_100_words: float = Field(ge=0)
    score: float = Field(ge=0, le=100)
    passed: bool
    categories: list[CategorySummary] = Field(default_factory=list)


class LintReport(BaseModel):
    """The whole `--format json` payload.

    `version` is the tool version, not a schema version, and the two are
    deliberately separate: `schema_version` is what a consumer branches on, and
    it changes only when a key is removed or retyped. Adding a key does not
    break a reader, so it does not bump.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    version: str
    summary: RunSummary
    documents: list[DocumentScore] = Field(default_factory=list)

    def emit(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=False)


# ---------------------------------------------------------------------------
# SARIF 2.1.0
# ---------------------------------------------------------------------------

# The specification's closed set. `note` is unused: slopvac's SUGGESTION maps to
# `note` in principle, but code scanning renders a note as an unfilterable
# informational alert, so suggestions are excluded from the SARIF payload
# entirely rather than shipped at a level nobody can triage.
SarifLevel = Literal["error", "warning", "note", "none"]


class SarifMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str


class SarifMultiformatMessage(BaseModel):
    """A message with an optional markdown rendering, used for rule help.

    The markdown body is what turns a code-scanning alert into a decision: the
    fix, why the rule is worded as it is, and the closed exception list.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    markdown: str | None = None


class SarifRuleProperties(BaseModel):
    """Rule metadata GitHub shows in the alert detail pane.

    A reference the rule does not carry is ABSENT rather than null -- a null in
    that pane renders as an empty row, so `exclude_none` on serialisation is
    load-bearing rather than cosmetic.
    """

    model_config = ConfigDict(extra="forbid")

    category: str
    kind: str
    ste_ref: str | None = None
    orwell_ref: str | None = None


class SarifReportingDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    name: str
    short_description: SarifMessage = Field(alias="shortDescription")
    full_description: SarifMessage = Field(alias="fullDescription")
    help_: SarifMultiformatMessage = Field(alias="help")
    # Only ever a real URL. A dead "learn more" link is worse than none, and most
    # rules cite a specification that has no public page to link to.
    help_uri: str | None = Field(default=None, alias="helpUri")
    properties: SarifRuleProperties


class SarifArtifactLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    uri: str


class SarifRegion(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    start_line: int = Field(alias="startLine", ge=1)
    start_column: int = Field(alias="startColumn", ge=1)
    end_column: int | None = Field(default=None, alias="endColumn", ge=1)


class SarifPhysicalLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    artifact_location: SarifArtifactLocation = Field(alias="artifactLocation")
    region: SarifRegion


class SarifLocation(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    physical_location: SarifPhysicalLocation = Field(alias="physicalLocation")


class SarifResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    rule_id: str = Field(alias="ruleId")
    level: SarifLevel
    message: SarifMessage
    # Required, not optional. Code scanning tracks an alert by fingerprint and
    # falls back to the LINE NUMBER when there is none, so editing one paragraph
    # closes and re-opens every alert below it as new. Typing it as required is
    # what stops a future result being built without one.
    partial_fingerprints: dict[str, str] = Field(
        alias="partialFingerprints", min_length=1
    )
    locations: Annotated[list[SarifLocation], Field(min_length=1)]


class SarifDriver(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    version: str
    information_uri: str = Field(alias="informationUri")
    rules: list[SarifReportingDescriptor] = Field(default_factory=list)


class SarifTool(BaseModel):
    model_config = ConfigDict(extra="forbid")

    driver: SarifDriver


class SarifAutomationDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str


class SarifRun(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tool: SarifTool
    # One repo can run this at more than one profile over more than one path.
    # Without a category GitHub treats the second upload as a REPLACEMENT for the
    # first and silently closes its alerts, so the profile names the run.
    automation_details: SarifAutomationDetails = Field(alias="automationDetails")
    column_kind: Literal["utf16CodeUnits", "utf32CodeUnits"] = Field(
        default="utf16CodeUnits", alias="columnKind"
    )
    results: list[SarifResult] = Field(default_factory=list)


class SarifLog(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: str = Field(
        default="https://json.schemastore.org/sarif-2.1.0.json", alias="$schema"
    )
    version: Literal["2.1.0"] = "2.1.0"
    runs: list[SarifRun] = Field(default_factory=list)

    def emit(self) -> str:
        """camelCase keys and no nulls, which is what the specification wants."""
        return self.model_dump_json(indent=2, by_alias=True, exclude_none=True)


# ---------------------------------------------------------------------------
# builders
# ---------------------------------------------------------------------------


def _sarif_level(severity: Severity) -> SarifLevel:
    return "error" if severity is Severity.ERROR else "warning"


def rule_help_markdown(rule: Rule) -> str:
    """The `explain` output, as the markdown body of a code-scanning alert.

    An alert whose whole content is the one-line message tells a reader what
    matched and nothing about whether it should have. The fix, the reason the
    rule is worded as it is, and the closed exception list are what turn a
    finding into a decision, and they are already on the rule.
    """
    parts = []
    if rule.fix:
        parts.append(f"**Fix.** {rule.fix}")
    if rule.provenance.note:
        parts.append(f"**Why.** {rule.provenance.note}")
    if rule.exceptions:
        named = ", ".join(f"`{name}`" for name in rule.exceptions)
        parts.append(
            f"**Suppress only with a named reason.** {named}. Any other reason is "
            "reported rather than honoured."
        )
    source = rule.provenance.source
    if rule.provenance.ste_ref:
        source = f"{source} rule {rule.provenance.ste_ref.split(':', 1)[1]}"
    parts.append(f"**Source.** {source}")
    return "\n\n".join(parts)


def finding_fingerprint(finding: Finding, ordinal: int) -> str:
    """A stable, unique identity for one finding.

    Excludes the LINE, because code scanning falls back to the line when there is
    no fingerprint and editing one paragraph would then close and re-open every
    alert below it. Includes the MESSAGE, because one rule fires on a file for
    different reasons. Includes an OCCURRENCE ORDINAL, because one rule fires for
    the same reason more than once and two alerts sharing a fingerprint collapse
    into one. Counting occurrences is what makes the identity stable AND unique.
    """
    key = (finding.rule_id, finding.path, finding.message, str(ordinal))
    return hashlib.sha256("\0".join(key).encode()).hexdigest()[:16]


def build_sarif(
    scores: list[DocumentScore], rules: list[Rule], *, version: str, tool_uri: str
) -> SarifLog:
    """Assemble a SARIF log from a run.

    JUDGEMENT rules are excluded: a rule no linter can check has no result to
    attach, and shipping it as a descriptor with zero results makes the alert
    list claim coverage the run does not have.
    """
    descriptors = [
        SarifReportingDescriptor(
            id=rule.qualified_id,
            name=rule.name,
            shortDescription=SarifMessage(text=rule.name),
            fullDescription=SarifMessage(text=rule.fix or rule.name),
            help=SarifMultiformatMessage(
                text=rule.fix or rule.name, markdown=rule_help_markdown(rule)
            ),
            helpUri=rule.provenance.url,
            properties=SarifRuleProperties(
                category=rule.category,
                kind=rule.kind.value,
                ste_ref=rule.provenance.ste_ref,
                orwell_ref=rule.provenance.orwell_ref,
            ),
        )
        for rule in rules
        if rule.kind is not RuleKind.JUDGEMENT
    ]

    seen: dict[tuple[str, str, str], int] = {}
    results: list[SarifResult] = []
    for score in scores:
        for finding in score.findings:
            key = (finding.rule_id, finding.path, finding.message)
            seen[key] = seen.get(key, 0) + 1
            results.append(
                SarifResult(
                    ruleId=finding.rule_id,
                    level=_sarif_level(finding.severity),
                    message=SarifMessage(text=finding.message),
                    partialFingerprints={
                        "slopvacFindingV1": finding_fingerprint(finding, seen[key])
                    },
                    locations=[
                        SarifLocation(
                            physicalLocation=SarifPhysicalLocation(
                                artifactLocation=SarifArtifactLocation(uri=finding.path),
                                region=SarifRegion(
                                    startLine=finding.line,
                                    startColumn=finding.column,
                                    endColumn=finding.end_column,
                                ),
                            )
                        )
                    ],
                )
            )

    profiles = sorted({score.profile for score in scores})
    category = profiles[0] if len(profiles) == 1 else "mixed"
    return SarifLog(
        runs=[
            SarifRun(
                tool=SarifTool(
                    driver=SarifDriver(
                        name="slopvac",
                        version=version,
                        informationUri=tool_uri,
                        rules=descriptors,
                    )
                ),
                automationDetails=SarifAutomationDetails(id=f"slopvac/{category}"),
                results=results,
            )
        ]
    )


def summarize(scores: list[DocumentScore]) -> RunSummary:
    """Roll several documents into one summary.

    Density is recomputed over TOTAL words rather than averaged over documents:
    averaging per-document densities lets a 30-word file outweigh a 3,000-word
    one, which misreports a repository.
    """
    if not scores:
        return RunSummary(
            documents=0,
            words=0,
            findings=0,
            errors=0,
            warnings=0,
            suggestions=0,
            per_100_words=0.0,
            score=100.0,
            passed=True,
        )

    words = sum(s.words for s in scores)
    findings = sum(s.total_findings for s in scores)

    # Word-weighted mean, so a long document counts for more than a stub.
    if words:
        overall = sum(s.score * max(s.words, 1) for s in scores) / sum(
            max(s.words, 1) for s in scores
        )
    else:
        overall = sum(s.score for s in scores) / len(scores)

    buckets: dict[str, list[CategoryScore]] = {}
    for score in scores:
        for entry in score.categories:
            buckets.setdefault(entry.category, []).append(entry)

    categories = [
        CategorySummary(
            category=name,
            findings=sum(e.findings for e in entries),
            errors=sum(e.errors for e in entries),
            warnings=sum(e.warnings for e in entries),
            suggestions=sum(e.suggestions for e in entries),
            per_100_words=(
                round(sum(e.findings for e in entries) / words * 100, 3) if words else 0.0
            ),
            score=round(sum(e.score for e in entries) / len(entries), 1),
        )
        for name, entries in sorted(buckets.items())
    ]

    return RunSummary(
        documents=len(scores),
        words=words,
        findings=findings,
        errors=sum(s.errors for s in scores),
        warnings=sum(s.warnings for s in scores),
        suggestions=sum(s.suggestions for s in scores),
        per_100_words=round(findings / words * 100, 3) if words else 0.0,
        score=round(overall, 1),
        passed=all(s.passed for s in scores),
        categories=categories,
    )
