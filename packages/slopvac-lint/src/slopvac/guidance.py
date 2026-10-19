"""Writing and review guidance printed by `slopvac prime write|review`.

The judgement checklist is GENERATED from the loaded `RuleSet`, never copied
into prose: a question restated here would drift from the rule the catalogue
carries, which is the failure the generated rules reference exists to prevent.
The static text below holds only what no rule record can: the genre table, the
documentation contract, and the review workflow.

Order is deterministic (category id, then rule id) so two runs over the same
catalogue print the same bytes.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

from .config import GuidanceSettings
from .model import Rule
from .rules import RuleSet


class Genre(NamedTuple):
    name: str
    surfaces: str
    profile: str
    body: str


GENRES = (
    Genre("consumer", "README, docs, guides", "normal", "Shipped behavior and reader use"),
    Genre("reference", "API docs, runbooks, procedures, safety text", "strict", "Exact operations and dated facts for use or verification"),
    Genre("change-comms", "PR or MR descriptions, commits, release notes, migration guides", "normal", "Delta, past tense, rationale, verification"),
    Genre("internal", "Specifications, decision records, contributor docs", "normal", "Requirements and constraints; decisions include rationale and alternatives"),
    Genre("informal", "Issue comments, discussions, blogs, drafts", "relaxed", "Immediate context"),
)

_SURFACES = "a README, docs, commit or release text, or a specification"
_ROUTING = (
    "Choose the genre by document purpose. Migration guides use `change-comms`; "
    "decision records and specifications use `internal`; procedures use `reference`."
)

def _clean(text: str) -> str:
    return " ".join(text.split())


def _by_category(rules: list[Rule]) -> dict[str, list[Rule]]:
    buckets: dict[str, list[Rule]] = defaultdict(list)
    for rule in rules:
        buckets[rule.category].append(rule)
    return {
        category: sorted(bucket, key=lambda r: r.id)
        for category, bucket in sorted(buckets.items())
    }


def _category_heading(ruleset: RuleSet, category_id: str) -> str:
    category = ruleset.categories[category_id]
    genres = ", ".join(category.recommended_for) or "no genre"
    return f"### {category.title} (`{category_id}`), recommended for: {genres}"


def write_checklist(ruleset: RuleSet) -> list[str]:
    """One constructive line per judgement rule: its id and the rewrite."""
    lines: list[str] = []
    for category_id, rules in _by_category(ruleset.judgement_rules).items():
        lines.extend([_category_heading(ruleset, category_id), ""])
        for rule in rules:
            lines.append(f"- `{rule.qualified_id}`: {_clean(rule.fix or rule.message)}")
        lines.append("")
    return lines


def review_checklist(ruleset: RuleSet) -> list[str]:
    """One question per judgement rule, with the scope it is asked over."""
    lines: list[str] = []
    for category_id, rules in _by_category(ruleset.judgement_rules).items():
        lines.extend([_category_heading(ruleset, category_id), ""])
        for rule in rules:
            lines.append(
                f"- `{rule.qualified_id}` ({rule.scope.value}): "
                f"{_clean(rule.judgement_question or '')}"
            )
        lines.append("")
    return lines


def _genre_categories(ruleset: RuleSet, genre: str) -> str:
    categories = sorted(
        {
            rule.category
            for rule in ruleset.judgement_rules
            if genre in ruleset.categories[rule.category].recommended_for
        }
    )
    return ", ".join(f"`{c}`" for c in categories) or "none"



def review_step(settings: GuidanceSettings) -> str | None:
    """The hand-off instruction for the configured review mode, or None when off."""
    if settings.review == "auto":
        pass_name = "adversary loop" if settings.review_depth == "adversary" else "reviewer pass"
        return (
            "Before hand-off, run `slopvac prime review` and complete its workflow, "
            f"including the {pass_name}."
        )
    if settings.review == "ask":
        return (
            f"Before handing off {_SURFACES}, ask the user whether to run the "
            "semantic review from `slopvac prime review`."
        )
    return None


def prime_section(settings: GuidanceSettings) -> str:
    """The lines base `slopvac prime` adds for the configured guidance modes."""
    lines: list[str] = []
    if settings.write != "off":
        lines.append("- Before drafting docs, run `slopvac prime write`.")
    step = review_step(settings)
    if step:
        lines.append(f"- {step}")
    if not lines:
        return ""
    return "\n".join(["", "## Writing and review", "", *lines]) + "\n"


def disabled_notice(topic: str, config_path: Path | None) -> str:
    where = f" in {config_path}" if config_path else ""
    return f'slopvac prime {topic} is disabled by [guidance] {topic} = "off"{where}.'


def render_write(ruleset: RuleSet, settings: GuidanceSettings) -> str:
    """The writing guide: genre table, documentation contract, judgement fixes."""
    lines = [
        "# Slopvac writing guidance",
        "",
        "Use this guide before changing docs or release text. Lint checks mechanics. "
        "The contract and the rule list below add checks that need a reader.",
        "",
        "## Genres",
        "",
        "Classify each document. Its genre sets the lint profile and allowed content.",
        "",
        "| Genre | Surfaces | Profile | What the body may contain |",
        "| --- | --- | --- | --- |",
        *(f"| `{g.name}` | {g.surfaces} | `{g.profile}` | {g.body} |" for g in GENRES),
        "",
        _ROUTING,
        "",
        "## Documentation contract",
        "",
        "- Describe what the artifact does, how to configure it, and its limits. "
        "Name the reader actions needed to use or verify it.",
        "- Write for a technically capable reader. Omit primers and repeated rationale.",
        "- Keep an explanation when the reader needs it to act or to stay safe. "
        "Keep prerequisites and invariants the reader must know.",
        "- Check present-tense claims against the code. Remove claims about behavior "
        "the artifact lacks.",
        "- Match each claim's strength to its source. Do not turn \"not equivalent\" "
        "into \"cannot\", or \"some\" into \"all\".",
        "- Name the actor and the action. Give the exact command, path, or version.",
        "- Keep every fact the reader needs, including versions and paths. Keep "
        "evidence blocks. Remove wording that changes no reader action or contract.",
        "- Put process narration, superseded behavior, and future promises in change "
        "communications or decision records, not consumer or reference docs.",
        "- State a measurement only when it supports a threshold, a capacity, or a "
        "cost. A measurement that supports a reader decision also stays. Include "
        "the baseline and method.",
        "- Test each example against a fresh install before shipping.",
        "",
        "## Sentences",
        "",
        "- Write one idea per sentence. Name the actor and use one term for each concept.",
        "- Put each condition before its command. Limit instructions to 20 words and "
        "descriptions to 25.",
        "- Remove unmeasured adjectives and unsupported hedges. Give comparisons a baseline.",
        "- Give a date or a version instead of a relative time word.",
        "",
        "## Change communications",
        "",
        "- PR or MR descriptions state the change, reason, and verification. Map each "
        "claim to a diff hunk.",
        "- Commit messages use an imperative conventional-commit subject that names "
        "the behavior change.",
        "- Do not edit a changelog generated by release tooling. Commit subjects and "
        "PR titles supply its content.",
        "",
        "## Workflow",
        "",
        "1. Classify the document and record its genre and profile.",
        "2. Write the current contract. Remove words that change no reader action; "
        "keep needed facts.",
        "3. Check each claim against the code. Check every command, path, and flag. "
        "Check every default, version, and described behavior.",
        "4. Run `slopvac lint <file>... --profile <profile> --format json`. Fix errors "
        "and triage warnings with `slopvac explain <rule_id>`. Exit 2 means the run "
        "is incomplete.",
    ]
    step = review_step(settings)
    if step:
        lines.append(f"5. {step}")
    lines.extend(
        [
            "",
            "## Rules lint cannot check",
            "",
            "Lint does not report these rules. Apply each rewrite while drafting. "
            "Run `slopvac explain <rule_id>` for examples. Apply categories listed "
            "for the document's genre.",
            "",
            "<!-- slopvac-disable -->",
            *write_checklist(ruleset),
            "<!-- slopvac-enable -->",
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"


_REVIEWER_PASS = [
    "   - Give it the document and this review output.",
    "   - Add the original if you revised one, and any source or brief.",
    "   - It runs lint, the checklist, and a fact check.",
    "   - It reports each finding as the rule id, the quoted text, and a rewrite.",
    "   - It lists the original's facts and marks each one kept or wrong.",
    "   - It flags claims stronger than their source.",
    "   - You fix or rebut each finding.",
]
_NO_SUBAGENT = (
    '   - If no subagent is available, review the document yourself. Report the '
    'reviewer as "self (no subagent available)".'
)


def _review_workflow(settings: GuidanceSettings) -> list[str]:
    """The reviewer pass selected by project guidance."""
    if settings.review_depth == "self":
        step = ['6. Reviewer pass. Review the document yourself. Report the reviewer as "self".']
    elif settings.review_depth == "adversary":
        step = [
            "6. Reviewer pass. Run rounds with a fresh-context subagent each time.",
            *_REVIEWER_PASS,
            "   - Repeat until the reviewer confirms no findings.",
            _NO_SUBAGENT,
        ]
    else:
        step = [
            "6. Reviewer pass. Hand the document to one fresh-context subagent for "
            "one pass.",
            *_REVIEWER_PASS,
            "   - Run the adversary loop instead only when the user asks for it.",
            _NO_SUBAGENT,
        ]
    return [*step, "7. Report the verdict."]



def render_review(ruleset: RuleSet, settings: GuidanceSettings) -> str:
    """The review guide: lint, semantic checklist, claims, and reviewer pass."""
    lines = ["# Slopvac review guidance", ""]
    if settings.review == "ask":
        lines.extend(
            [
                '`[guidance] review = "ask"`: confirm with the user before '
                "starting this review.",
                "",
            ]
        )
    lines.extend(
        [
            "## Workflow",
            "",
            "1. Classify the document with the genre table. Record the profile.",
            "2. Run `slopvac lint <file>... --profile <profile> --format json`. Fix "
            "errors and triage warnings with `slopvac explain <rule_id>`. Exit 2 "
            "means incomplete. Report each `documents[].unchecked` entry.",
            "3. Semantic pass. Use categories recommended for the genre. Ask "
            "document questions over the whole document. Ask other questions "
            "per paragraph or sentence. Ask each remainder question even when "
            "its mechanical partner fires. The partner matches fixed wording. "
            "The remainder covers other wording. Quote failures and propose "
            "rewrites. Run `slopvac explain <rule_id>` for examples.",
            "4. Apply the deletion test to every section. Remove wording that "
            "changes no reader action or contract fact. List original facts. "
            "Confirm each fact survived or was wrong.",
            "5. Check claims against the code. Flag claims stronger than their source.",
            *_review_workflow(settings),
            "",
            "```text",
            "VERDICT: PASS | REVISE",
            "Gate:      score <n>/100, <n> errors, <n> warnings (exit <code>)",
            "Semantic:  <failed rule ids with quoted text, or none>",
            "Claims:    <verified, or the claim that does not hold>",
            "Facts:     <all kept, or the facts the revision lost>",
            "Reviewer:  <subagent, one pass | adversary, <n> rounds | self (reason)>; "
            "findings fixed, findings rebutted",
            "Action:    <the single highest-value change, or none>",
            "```",
            "",
            "Report REVISE when any of these holds:",
            "",
            "- the gate reports an error or an unchecked entry;",
            "- a claim fails, or a fact was lost;",
            "- a semantic question or the deletion test fails;",
            "- a reviewer finding is still open.",
            "",
            "Otherwise report PASS.",
            "",
            "## Genres",
            "",
            "| Genre | Surfaces | Profile | Checklist categories |",
            "| --- | --- | --- | --- |",
            *(
                f"| `{g.name}` | {g.surfaces} | `{g.profile}` | "
                f"{_genre_categories(ruleset, g.name)} |"
                for g in GENRES
            ),
            "",
            "## Checklist",
            "",
            "Run `slopvac rules --kind judgement --format json` for checklist metadata.",
            "",
            "<!-- slopvac-disable -->",
            *review_checklist(ruleset),
            "<!-- slopvac-enable -->",
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"
