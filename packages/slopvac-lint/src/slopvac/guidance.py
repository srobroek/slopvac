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
    Genre("reference", "API docs, runbooks, procedures, safety text, agent guidance", "strict", "Exact operations and dated facts for use or verification"),
    Genre("change-comms", "PR or MR descriptions, commits, release notes, migration guides", "normal", "Change, rationale, verification"),
    Genre("internal", "Specifications, decision records, contributor docs", "normal", "Requirements and decision rationale"),
    Genre("informal", "Issue comments, discussions, blogs, drafts", "relaxed", "Immediate context"),
)

_SURFACE_LIST = (
    "a README or docs",
    "PR or MR text",
    "commit or release text",
    "a specification",
)
_ROUTING = (
    "When two genres fit, choose by purpose. Migration guides are `change-comms`. "
    "Decision records and specifications are `internal`. Agent guidance and "
    "procedures are `reference`."
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
    lines: list[str] = []
    for category_id, rules in _by_category(ruleset.judgement_rules).items():
        lines.extend([_category_heading(ruleset, category_id), ""])
        for rule in rules:
            lines.append(f"- `{rule.qualified_id}`: {_clean(rule.fix or rule.message)}")
        lines.append("")
    return lines


def review_checklist(ruleset: RuleSet) -> list[str]:
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
    """The base-prime review line for one of the listed surfaces, or None."""
    if settings.review == "auto":
        pass_name = "adversary loop" if settings.review_depth == "adversary" else "reviewer pass"
        return (
            "Before you hand one off, run `slopvac prime review`. Complete its "
            f"workflow, including the {pass_name}."
        )
    if settings.review == "ask":
        return (
            "Before you hand one off, ask the user whether to run the semantic "
            "review from `slopvac prime review`."
        )
    return None


def prime_section(settings: GuidanceSettings) -> str:
    lines: list[str] = []
    if settings.write != "off":
        lines.append("- Before you write or edit one, run `slopvac prime write`.")
    step = review_step(settings)
    if step:
        lines.append(f"- {step}")
    if not lines:
        return ""
    surfaces = [f"- {s}" for s in _SURFACE_LIST]
    return "\n".join(
        ["", "## Writing and review", "", "These steps cover:", "", *surfaces, "", *lines]
    ) + "\n"


def disabled_notice(topic: str, config_path: Path | None) -> str:
    where = f" in {config_path}" if config_path else ""
    return f'slopvac prime {topic} is disabled by [guidance] {topic} = "off"{where}.'




def render_write(ruleset: RuleSet, settings: GuidanceSettings) -> str:
    """The writing guide: genre table, documentation contract, judgement fixes."""
    lines = [
        "# Slopvac writing guidance",
        "",
        "Classify the document by purpose. Use the listed genre and profile as guidance.",
        "",
        "| Genre | Surfaces | Profile | What the body may contain |",
        "| --- | --- | --- | --- |",
        *(f"| `{g.name}` | {g.surfaces} | `{g.profile}` | {g.body} |" for g in GENRES),
        "",
        _ROUTING,
        "",
        "## Documentation contract",
        "",
        "- Describe the artifact's behavior, configuration, and limits.",
        "- Name the actions readers take to use the artifact.",
        "- Write for technically capable readers. Omit primers and repeated rationale.",
        "- Keep explanations readers need to act or stay safe.",
        "- In consumer docs, check present-tense claims against code.",
        "  Remove claims about behavior the artifact does not have.",
        "- Match each claim's strength to its source.",
        "  Do not make a limited claim universal.",
        "- Name the actor and action. Use one term for each concept.",
        "- State exact commands, paths, and versions.",
        "- Keep every correct fact and supporting test result.",
        "- Remove wording that changes no reader action or contract fact.",
        "- Put process history in change communications.",
        "- Put plans in specifications or decision records.",
        "- Keep history and plans out of consumer and reference docs.",
        "- When a measurement guides readers, give the baseline and method.",
        "- Before release, test each example on a clean install.",
        "",
        "## Sentences",
        "",
        "- Write one idea per sentence. Use one term for each concept.",
        "- Write the condition first and the command second. Limit instructions "
        "to 20 words and descriptions to 25.",
        "- Remove unmeasured adjectives and unsupported hedges. Give comparisons a baseline.",
        "- Replace relative time words with a date or version.",
        "",
        "## Change communications",
        "",
        "- PR or MR descriptions state the change, reason, and verification. Map "
        "each claim to a diff hunk.",
        "- If the repository uses Conventional Commits, write an imperative subject "
        "that names the behavior change.",
        "- Do not edit a changelog that release tooling generates. Change the "
        "commit subject or PR title that the tool reads.",
        "",
        "## Workflow",
        "",
        "1. Classify the document. Note its genre and lint profile for the review.",
        "2. Write from the documentation contract. Keep correct facts from sources.",
        "3. Check claims against code or a source. Verify relevant commands and paths.",
        "4. Apply the rules below that fit the genre. `slopvac explain <rule_id>` "
        "shows each rule's question and examples.",
        "5. Run each example against a clean install.",
        "6. Lint with `slopvac lint <file>... --profile <profile> --format json`.",
        "7. Fix errors. Run `slopvac explain <rule_id>` to triage warnings.",
        "8. Exit 1 means that a gate failed. Exit 2 means that the run is incomplete.",
    ]
    step = review_step(settings)
    if step:
        lines.append("9. Before you hand off one of these, run `slopvac prime review`:")
        lines.extend(f"   - {s}" for s in _SURFACE_LIST)
        lines.append("   Complete its configured workflow.")
    lines.extend(
        [
            "",
            "## Rules lint cannot check",
            "",
            "Use categories whose headings list the document's genre.",
            "Each line gives the fix for one rule that needs a reader.",
            "If the rule question matches the text, apply its fix.",
            "",
            "<!-- slopvac-disable -->",
            *write_checklist(ruleset),
            "<!-- slopvac-enable -->",
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"

_REVIEWER_PASS = [
    "   - Give it the document and `slopvac prime review` output.",
    "   - If you revised the document, give it the original.",
    "   - Give it any source or brief that is available.",
    "   - It runs steps 1 to 5. It does not edit the document.",
    "   - It marks wording for the author to consider removing.",
    "   - It reports each finding as rule id, quoted text, and proposed rewrite.",
    "   - It lists the received document's facts and marks each kept or wrong.",
    "   - It flags claims stronger than their source.",
]
_NO_SUBAGENT = (
    "   - When no subagent is available, review yourself. Report "
    '"self (no subagent available)".'
)


_AFTER_REVIEW = [
    "7. Fix or rebut each reviewer finding.",
    "8. After you edit the document, run lint again.",
    "9. Report the verdict.",
]


def _review_workflow(settings: GuidanceSettings) -> list[str]:
    """The configured author or subagent review steps."""
    if settings.review_depth == "self":
        return [
            '6. Steps 3 to 5 are the review. Report "self (review_depth = self)".',
            "7. Report the verdict.",
        ]
    if settings.review_depth == "adversary":
        return [
            "6. Reviewer pass: run rounds, each with a new fresh-context subagent.",
            *_REVIEWER_PASS,
            "   - The subagent does not run steps 6 to 9.",
            "   - Give each new round the findings you rebutted earlier.",
            "   - When a round reports no finding that you accept, stop.",
            _NO_SUBAGENT,
            *_AFTER_REVIEW,
        ]
    return [
        "6. Reviewer pass: give one fresh-context subagent one pass.",
        *_REVIEWER_PASS,
        "   - The subagent does not run steps 6 to 9.",
        "   - When the user asks for adversary rounds, repeat this pass with a "
        "new subagent. Give it your earlier rebuttals.",
        _NO_SUBAGENT,
        *_AFTER_REVIEW,
    ]



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
            "1. Classify the document. Choose its genre and profile.",
            "2. Run `slopvac lint <file>... --profile <profile> --format json`.",
            "For errors, run `slopvac explain <rule_id>` to choose a remedy.",
            "Exit 1 means that a gate failed. Exit 2 means that the run is incomplete.",
            "On exit 2, report unchecked entries or the error text.",
            "Fix the cause. Rerun lint. Config or rule errors print text, not JSON.",
            "3. Ask enforced and advisory checklist questions. Skip excluded ones.",
            "Ask document questions over the document. Ask others at their listed scope.",
            "Find the paired lint rule in each remainder rule's provenance.",
            "When lint reports that partner, ask the remainder question.",
            "Quote failures. Propose rewrites.",
            "4. Mark wording that changes no reader action or contract fact.",
            "The author removes marked wording.",
            "Never mark a fact or an evidence block for removal. Code blocks, logs, "
            "and diffstats are evidence.",
            "List facts in the received document. Confirm each survived or was wrong.",
            "5. Check each claim against code or an authoritative source.",
            "Flag claims stronger than their source.",
            *_review_workflow(settings),
            "",
            "```text",
            "VERDICT: PASS | REVISE",
            "Gate:      profile <profile>, score <n>/100, <n> errors, <n> warnings, "
            "unchecked <entries or none> (exit <code>)",
            "Semantic:  <failed enforced rule ids with quoted text, advisory findings, or none>",
            "Deletion:  <wording marked for deletion, or none>",
            "Claims:    <verified, or the claim that does not hold>",
            "Facts:     <all kept, or the facts the revision lost>",
            "Reviewer:  <subagent, <n> rounds | adversary, <n> rounds | self "
            "(review_depth = self | no subagent available)>; <counts of findings fixed and rebutted>",
            "Action:    <the single highest-value change, or none>",
            "```",
            "",
            "Report REVISE for lint exit 1 or 2, a failed claim, or a lost fact.",
            "Also report REVISE for a failed enforced question, failed deletion test, "
            "or open reviewer finding.",
            "Report advisory failures without blocking. Skip excluded questions.",
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
            "Run `slopvac rules --kind judgement --profile <profile> --format json` "
            "to inspect tiers. Review the profile named in step 1.",
            "",
            "<!-- slopvac-disable -->",
            *review_checklist(ruleset),
            "<!-- slopvac-enable -->",
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"
