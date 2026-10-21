"""The issue-form contract shared by `prime report` and GitHub's forms."""

from __future__ import annotations

from dataclasses import dataclass, replace

REPOSITORY_SLUG = "srobroek/slopvac"


@dataclass(frozen=True)
class ReportField:
    id: str
    label: str
    type: str
    required: bool
    render: str | None = None
    options: tuple[str, ...] = ()
    multiple: bool = False
    description: str | None = None


@dataclass(frozen=True)
class ReportCategory:
    key: str
    form_file: str
    form_name: str
    title_prefix: str
    labels: tuple[str, ...]
    meaning: str
    fields: tuple[ReportField, ...]


def _field(
    id: str,
    label: str,
    type: str,
    *,
    required: bool = True,
    render: str | None = None,
    options: tuple[str, ...] = (),
    multiple: bool = False,
    description: str | None = None,
) -> ReportField:
    return ReportField(
        id=id,
        label=label,
        type=type,
        required=required,
        render=render,
        options=options,
        multiple=multiple,
        description=description,
    )


_COMMON_FIELDS = (
    _field(
        "reporter",
        "Reported by",
        "dropdown",
        options=("A person", "An AI agent, with the user's approval"),
    ),
    _field(
        "agent",
        "Agent and model",
        "input",
        description=(
            "Agent name and model, for example `Claude Code, claude-sonnet-4-5`. "
            "Write `none` when no agent was involved."
        ),
    ),
    _field(
        "harness",
        "Harness and version",
        "input",
        description=(
            "For example omp 14.2, Claude Code 2.1, Codex CLI, Kiro, "
            "GitHub Action, pre-commit, or terminal."
        ),
    ),
    _field("version", "slopvac version", "input", description="Output of `slopvac --version`."),
    _field(
        "latest",
        "Reproduces on the latest release",
        "dropdown",
        options=("Yes", "Not checked"),
        description=(
            "Rerun the command with `uvx --from slopvac@latest slopvac ...`. "
            "If the latest release fixes it, upgrade instead of filing."
        ),
    ),
    _field("environment", "Environment", "textarea", required=False, render="json", description="Output of `slopvac doctor --format json`. Home paths print as `~`."),
    _field("command", "Command", "textarea", required=False, render="shell", description="The exact command or commands you ran."),
)


def _category_fields(*fields: ReportField, proposal: bool = False) -> tuple[ReportField, ...]:
    """Set common environment and command requirements for each category."""
    required = not proposal
    common = (
        *_COMMON_FIELDS[:5],
        replace(_COMMON_FIELDS[5], required=required),
        replace(_COMMON_FIELDS[6], required=required),
    )
    return (*common, *fields)


REPORT_CATEGORIES: tuple[ReportCategory, ...] = (
    ReportCategory(
        key="bug",
        form_file="bug.yml",
        form_name="Bug report",
        title_prefix="[bug]: ",
        labels=("bug", "needs-triage"),
        meaning="Crash, traceback, wrong exit code, wrong or unstable output format, config/setup/init/Vale/cache/prime defects.",
        fields=_category_fields(
            _field("what-happened", "What happened", "textarea"),
            _field("expected", "Expected behavior", "textarea"),
            _field("output", "Output", "textarea", required=False, render="text", description="stderr, traceback, or report excerpt"),
            _field("config", "Configuration", "textarea", required=False, render="toml", description="Relevant `slopvac.toml` lines"),
        ),
    ),
    ReportCategory(
        key="false-positive",
        form_file="false-positive.yml",
        form_name="Rule flags text that is not slop",
        title_prefix="[false positive]: ",
        labels=("false-positive", "needs-triage"),
        meaning="A rule flags text that is not slop.",
        fields=_category_fields(
            _field("rule-id", "Rule ID", "input"),
            _field("context", "Genre and profile", "input", description="For example `reference`, `strict`. `slopvac lint --explain-config <file>` prints the profile."),
            _field("input", "Flagged text", "textarea", render="markdown", description="The smallest sample that still triggers the finding."),
            _field("finding", "Finding", "textarea", render="json", description="The finding object from `slopvac lint <file> --format json`."),
            _field("why", "Why this is not slop", "textarea"),
        ),
    ),
    ReportCategory(
        key="missed-slop",
        form_file="missed-slop.yml",
        form_name="Slop that slopvac missed",
        title_prefix="[missed slop]: ",
        labels=("false-negative", "needs-triage"),
        meaning="Slop that no finding reports, where an existing rule should cover it; when unsure, use this form.",
        fields=_category_fields(
            _field("context", "Genre and profile", "input", description="For example `reference`, `strict`. `slopvac lint --explain-config <file>` prints the profile."),
            _field("input", "Missed text", "textarea", render="markdown"),
            _field("expected-rule", "Rule that should fire", "input", required=False, description="Leave empty when you do not know. When no rule covers the pattern, use the new rule form."),
            _field("why", "Why this is slop", "textarea"),
        ),
    ),
    ReportCategory(
        key="mis-tagged",
        form_file="mis-tagged.yml",
        form_name="Slop tagged incorrectly",
        title_prefix="[mis-tagged]: ",
        labels=("mis-tagged", "needs-triage"),
        meaning="The flagged text is slop, but the rule, severity, or span/location is wrong.",
        fields=_category_fields(
            _field("rule-id", "Rule ID", "input"),
            _field("context", "Genre and profile", "input", description="For example `reference`, `strict`. `slopvac lint --explain-config <file>` prints the profile."),
            _field("input", "Flagged text", "textarea", render="markdown"),
            _field("finding", "Finding", "textarea", render="json"),
            _field("problem", "What is wrong", "dropdown", options=("Wrong rule", "Wrong severity", "Wrong span or location"), multiple=True),
            _field("expected", "Expected finding", "textarea", description="The rule, severity, or span you expected."),
        ),
    ),
    ReportCategory(
        key="wrong-fix",
        form_file="wrong-fix.yml",
        form_name="Correct match, wrong suggestion or fix",
        title_prefix="[wrong fix]: ",
        labels=("wrong-fix", "needs-triage"),
        meaning="The flagged text is slop and the right rule fired, but the message, suggested replacement, fix guidance, or `--fix` edit is wrong, unclear, or changes the meaning.",
        fields=_category_fields(
            _field("rule-id", "Rule ID", "input"),
            _field("context", "Genre and profile", "input", description="For example `reference`, `strict`. `slopvac lint --explain-config <file>` prints the profile."),
            _field("input", "Flagged text", "textarea", render="markdown"),
            _field("finding", "Finding", "textarea", render="json"),
            _field("problem", "What is wrong", "dropdown", options=("Wrong suggested replacement", "--fix changed the meaning", "--fix produced broken text", "Misleading or unclear message", "Fix guidance does not apply here"), multiple=True),
            _field("fixed-text", "Text after the fix", "textarea", required=False, render="markdown", description="Output of `slopvac lint --fix`, when you ran it."),
            _field("expected", "Expected suggestion", "textarea"),
        ),
    ),
    ReportCategory(
        key="new-rule",
        form_file="new-rule.yml",
        form_name="New rule proposal",
        title_prefix="[new rule]: ",
        labels=("new-rule", "needs-triage"),
        meaning="A writing pattern that no existing rule covers.",
        fields=_category_fields(
            _field("pattern", "Pattern", "textarea", description="Describe the writing pattern and why it reads as slop."),
            _field("bad-examples", "Examples that should fire", "textarea", render="markdown"),
            _field("good-examples", "Examples that must not fire", "textarea", render="markdown"),
            _field("kind", "Rule kind", "dropdown", options=("Pattern (deterministic)", "Judgement (reviewer question)", "Unsure")),
            _field("genres", "Genres", "dropdown", required=False, options=("consumer", "reference", "change-comms", "internal", "informal"), multiple=True),
            _field("related", "Related existing rules", "input", required=False),
            _field("source", "Evidence or source", "textarea", required=False),
            proposal=True,
        ),
    ),
    ReportCategory(
        key="rule-improvement",
        form_file="rule-improvement.yml",
        form_name="Rule improvement",
        title_prefix="[rule improvement]: ",
        labels=("rule-improvement", "needs-triage"),
        meaning="A change to an existing rule as a whole: accuracy across many findings, examples, exceptions, judgement question, tier or severity, genre recommendation, message or fix wording in general, or docs.",
        fields=_category_fields(
            _field("rule-id", "Rule ID", "input"),
            _field("aspect", "What to improve", "dropdown", options=("Accuracy across many findings", "Message or fix wording", "Examples", "Exceptions", "Judgement question", "Severity or tier", "Genre recommendation", "Documentation"), multiple=True),
            _field("current", "Current behavior", "textarea"),
            _field("proposal", "Proposed change", "textarea"),
            _field("accuracy", "Accuracy sample", "textarea", required=False, description="Findings judged on a sample: how many were true slop, how many were not, and the corpus they came from."),
            _field("evidence", "Evidence", "textarea", required=False),
            proposal=True,
        ),
    ),
)
