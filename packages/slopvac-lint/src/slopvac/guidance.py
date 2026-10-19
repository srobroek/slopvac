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
    Genre(
        "consumer",
        "README, docs, guides, anything a user of the artifact reads",
        "normal",
        "Current shipped behavior and reader use only",
    ),
    Genre(
        "reference",
        "API and reference docs, runbooks, procedures, safety text",
        "strict",
        "Exact operation, plus dated facts needed to operate or verify it",
    ),
    Genre(
        "change-comms",
        "PR or MR descriptions, commit messages, release notes, migration guides",
        "normal",
        "Delta, past tense, rationale, and verification; never a roadmap",
    ),
    Genre(
        "internal",
        "Specifications, decision records, CONTRIBUTING, contributor docs",
        "normal",
        "Requirements and constraints; decision records keep rationale and "
        "alternatives; specs state future intent only with acceptance criteria",
    ),
    Genre(
        "informal",
        "Issue comments, discussion replies, blog posts, drafts",
        "relaxed",
        "Immediate context; no project history or promises",
    ),
)

_ROUTING = (
    "Route by document purpose, not passage wording: migration guides and "
    "explicit before/after tracking are `change-comms`; decision records, "
    "release plans, specifications, and explicitly historical reports are "
    "`internal`; procedures are `reference`."
)

_SURFACES = (
    "a README, docs, a PR or MR description, commit or release text, or a "
    "specification"
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
        return (
            f"Before handing off {_SURFACES}, run `slopvac prime review` and "
            "complete its workflow, including the adversary review."
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
        lines.append(
            f"- Before drafting or editing {_SURFACES}, run `slopvac prime write` "
            "and follow it."
        )
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
        "Use this before drafting or editing documentation and change text. "
        "Lint checks the mechanical rules; the contract and the generated list "
        "below cover what lint cannot check.",
        "",
        "## Genres",
        "",
        "Classify the document first. The genre sets the lint profile and what "
        "the body may contain.",
        "",
        "| Genre | Surfaces | Profile | What the body may contain |",
        "| --- | --- | --- | --- |",
        *(f"| `{g.name}` | {g.surfaces} | `{g.profile}` | {g.body} |" for g in GENRES),
        "",
        _ROUTING,
        "",
        "## Documentation contract",
        "",
        "- Describe the current artifact: behavior, interface, configuration, "
        "constraints, and the reader actions needed to use, verify, or "
        "reproduce it.",
        "- Write for a technically capable reader. Omit primers, remedial "
        "definitions, hand-holding, and repeated rationale.",
        "- Keep an explanation only when the reader needs it to act, meet a "
        "prerequisite, observe a safety constraint, or apply an implicit "
        "invariant.",
        "- Verify every present-tense claim against the code. Delete claims "
        "about behavior the artifact does not implement; deleting only "
        '"coming soon" makes the document assert that the feature ships.',
        "- Keep each claim exactly as strong as its source. When rewording, "
        'do not turn "not equivalent" into "cannot", "some" into "all", or a '
        "reported result into a verified one.",
        "- Name the actor, action, condition, command, path, or version. Use "
        "decisive normative language.",
        "- Apply the deletion test to every sentence, list item, table row, and "
        "paragraph: if removing it changes no reader action or understanding "
        "of the current contract, delete it.",
        "- Keep process narration, author effort, chronology, job IDs, "
        "superseded behavior, rejected alternatives, and future promises out "
        "of `consumer`, `reference`, and `informal` text. Change communications "
        "and decision records hold them.",
        "- State a measurement only when it supports a current threshold, "
        "capacity, cost, or reader decision, and give its baseline and method.",
        "- Make every example run as written against a fresh install, and run "
        "it before shipping.",
        "",
        "## Sentences",
        "",
        "- One idea per sentence, active voice with the actor named, one term "
        "for each concept.",
        "- Put a condition before the command it governs. Keep instructions "
        "near 20 words and descriptive sentences near 25.",
        "- Delete adjectives without a number, benchmark, or feature list. "
        "Delete hedges that name no real uncertainty. Give every comparative "
        "its baseline.",
        "- In ordinary docs, give a date or version instead of `recently`, "
        "`currently`, or `in the future`.",
        "",
        "## Change communications",
        "",
        "- PR or MR description: what changed, why, and how it was verified. "
        "Map every claim to a hunk in the diff.",
        "- Commit message: a conventional-commit subject in the imperative that "
        "names the behavior change, not `improve` or `update`.",
        "- Never hand-edit a changelog that release tooling generates; its "
        "quality comes from commit subjects and PR titles.",
        "",
        "## Workflow",
        "",
        "1. Classify the document and note its genre and profile.",
        "2. Draft the smallest current-contract document, then apply the "
        "deletion test.",
        "3. Verify every claim, command, path, flag, default, and version "
        "against the code.",
        "4. Run `slopvac lint <file>... --profile <profile> --format json`. Fix "
        "every error, and fix or justify every warning. Exit 2 means the run "
        "is incomplete.",
    ]
    step = review_step(settings)
    if step:
        lines.append(f"5. {step}")
    lines.extend(
        [
            "",
            "## Judgement rules",
            "",
            "Lint never reports these. Apply each rewrite while drafting; "
            "`slopvac explain <rule_id>` shows the question and examples. Apply "
            "a category when its recommended genres include the document's.",
            "",
            *write_checklist(ruleset),
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"


def render_review(ruleset: RuleSet, settings: GuidanceSettings) -> str:
    """The review guide: lint, semantic checklist, claims, adversary loop."""
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
            "1. Classify the document with the genre table below and note its "
            "profile.",
            "2. Run `slopvac lint <file>... --profile <profile> --format json` "
            "first. Fix every error and triage every warning with `slopvac "
            "explain <rule_id>`. Exit 2 is incomplete: act on the native "
            "findings and report each `documents[].unchecked` entry.",
            "3. Semantic pass. Take the checklist categories recommended for the "
            "genre. Ask `document` questions once over the whole document and "
            "the others per paragraph or sentence. Ask every `-remainder` "
            "question even where its mechanical partner fired: the partner "
            "matches fixed wording, and the remainder covers every other phrasing. "
            "For every failure, quote the offending text and propose a rewrite; "
            "`slopvac explain <rule_id>` shows worked examples.",
            "4. Read adversarially. For every sentence, list item, table row, and "
            "paragraph, ask which reader action or current-contract fact it "
            "changes, and revise when the answer is none.",
            "5. Verify every factual claim against the code: commands, paths, "
            "flags, defaults, versions, and behavior. Flag a claim stated more "
            "strongly than its source supports.",
            "6. Adversary review. Hand the document and this output to a "
            "separate reviewer with fresh context: a subagent or a second "
            "person. Instruct it to find failures only and to cite each as the "
            "rule id, the quoted text, and a proposed rewrite. Fix each "
            "confirmed finding, or rebut it with evidence. Repeat until the "
            "adversary reports no confirmed findings.",
            "7. Report the verdict.",
            "",
            "```text",
            "VERDICT: PASS | REVISE",
            "Gate:      score <n>/100, <n> errors, <n> warnings (exit <code>)",
            "Semantic:  <failed rule ids with quoted text, or none>",
            "Claims:    <verified, or the claim that does not hold>",
            "Adversary: <rounds, findings fixed, findings rebutted>",
            "Action:    <the single highest-value change, or none>",
            "```",
            "",
            "REVISE when the gate reports an error or an unchecked entry, a claim "
            "fails, a semantic question fails, a section fails the deletion "
            "test, or the adversary still holds a confirmed finding. PASS needs "
            "all of these clear.",
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
            _ROUTING,
            "",
            "## Checklist",
            "",
            "Generated from the rule catalogue. Each line is the rule id, the "
            "scope the question is asked over, and the question. For the same "
            "checklist as JSON, with each rule's category, fix, and examples, "
            "run `slopvac rules --kind judgement --format json`.",
            "",
            *review_checklist(ruleset),
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"
