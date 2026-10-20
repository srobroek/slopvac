"""Writing and review guidance printed by `slopvac prime write|review`.

The judgement checklist is GENERATED from the loaded `RuleSet`, never copied
into prose: a question restated here would drift from the rule the catalogue
carries, which is the failure the generated rules reference exists to prevent.
The genre and profile tables are generated the same way, from `genres.GENRES`
and the profile defaults in `config` and `profiles`; the base `slopvac prime`
prints them too. The static text below holds only what no record can: the
documentation contract, the review workflow, and what a tier or a scope asks of
the reader.

Order is deterministic (category id, then rule id) so two runs over the same
catalogue print the same bytes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from .config import (
    Config,
    GuidanceSettings,
    Profile,
    Severity,
    Thresholds,
    profile_thresholds,
)
from .genres import GENRES, ROUTING
from .model import Rule, Scope, Tier
from .profiles import profile_defaults
from .rules import RuleSet
from .suppression import DISABLE_COMMENT, ENABLE_COMMENT, allow_comment

_SURFACE_LIST = (
    "a README or docs",
    "PR or MR text",
    "commit or release text",
    "a specification",
)

# What each scope and tier asks of the person applying a checklist entry. Keyed
# by the enums, so a new member without a meaning fails the render, not silently.
_SCOPE_MEANING = {
    Scope.PROSE: "the running text, without code, URLs, and front matter",
    Scope.HEADING: "each heading",
    Scope.SENTENCE: "each sentence",
    Scope.PARAGRAPH: "each paragraph",
    Scope.DOCUMENT: "the whole document",
    Scope.RAW: "the whole file, code included",
}
_TIER_MEANING = {
    Tier.ENFORCED: "the rule must hold. A failed question makes the review verdict REVISE.",
    Tier.ADVISORY: "apply the rule where it fits. The review reports a failure and does not block.",
    Tier.EXCLUDED: "the rule does not apply at that profile. Skip it.",
}


def unlinted(lines: list[str]) -> list[str]:
    """Wrap a generated listing so that linting the guide skips it.

    Generated rows quote catalogue text, model values, and click help verbatim,
    and those strings are not written to the `strict` profile that every prime
    output must pass. Hand-written guidance stays linted; only generated
    listings go through here.
    """
    return [DISABLE_COMMENT, *lines, ENABLE_COMMENT]


def _clean(text: str) -> str:
    return " ".join(text.split())


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]


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


def _checklist(ruleset: RuleSet, text_of: Callable[[Rule], str]) -> list[str]:
    lines: list[str] = []
    for category_id, rules in _by_category(ruleset.judgement_rules).items():
        lines.extend([_category_heading(ruleset, category_id), ""])
        for rule in rules:
            lines.append(
                f"- `{rule.qualified_id}` ({rule.scope.value}): {_clean(text_of(rule))}"
            )
        lines.append("")
    return lines


def write_checklist(ruleset: RuleSet) -> list[str]:
    return _checklist(ruleset, lambda rule: rule.fix or rule.message)


def review_checklist(ruleset: RuleSet) -> list[str]:
    return _checklist(ruleset, lambda rule: rule.judgement_question or "")


def _entry_guide(ruleset: RuleSet, text: str) -> list[str]:
    """How to read one checklist entry, and where to get more on its rule."""
    scopes = [s for s in Scope if any(r.scope is s for r in ruleset.judgement_rules)]
    return [
        f"Each entry has the form `<category>.<rule-id>` (<scope>): <{text}>.",
        "The scope names the unit that the rule judges:",
        "",
        *(f"- `{scope.value}`: {_SCOPE_MEANING[scope]}" for scope in scopes),
        "",
        "Each rule has a tier at each profile. At the document's profile:",
        "",
        *(f"- `{tier.value}`: {_TIER_MEANING[tier]}" for tier in Tier),
        "",
        "Run `slopvac explain <rule_id>` for one rule. It prints the question, "
        "the fix, and worked examples.",
        "Run `slopvac rules --kind judgement --profile <profile> --format json` "
        "for the tiers. Each `rules[].tier` holds the tier at that profile.",
        "",
    ]


def _genre_categories(ruleset: RuleSet, genre: str) -> str:
    categories = sorted(
        {
            rule.category
            for rule in ruleset.judgement_rules
            if genre in ruleset.categories[rule.category].recommended_for
        }
    )
    return ", ".join(f"`{c}`" for c in categories) or "none"


def genre_table(ruleset: RuleSet | None = None) -> list[str]:
    """One row per genre; with a ruleset, also the checklist categories."""
    header = ["Genre", "Surfaces", "Profile", "Purpose"]
    if ruleset is not None:
        header.append("Checklist categories")
    rows = []
    for genre in GENRES:
        row = [f"`{genre.name}`", genre.surfaces, f"`{genre.profile.value}`", genre.purpose]
        if ruleset is not None:
            row.append(_genre_categories(ruleset, genre.name))
        rows.append(row)
    return _table(header, rows)


def _gate(value: float | None) -> str:
    if value is None:
        return "none"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def profile_table() -> list[str]:
    """Each profile's document gates, from `profile_thresholds`, keyed as in config."""
    keys = list(Thresholds.model_fields)
    rows = []
    for profile in Profile:
        gates = profile_thresholds(profile)
        genres = ", ".join(f"`{g.name}`" for g in GENRES if g.profile is profile)
        rows.append(
            [
                f"`{profile.value}`",
                genres or "none",
                *(_gate(getattr(gates, key)) for key in keys),
            ]
        )
    return _table(["Profile", "Genres", *(f"`{key}`" for key in keys)], rows)


def categories_off() -> list[str]:
    """The categories each profile turns off, from `profile_defaults`."""
    lines = []
    for profile in Profile:
        off = sorted(
            name
            for name, settings in profile_defaults(profile).items()
            if settings.severity is Severity.OFF
        )
        listed = ", ".join(f"`{name}`" for name in off) or "none"
        lines.append(f"- `{profile.value}`: {listed}")
    return lines


def genres_and_profiles(ruleset: RuleSet | None = None) -> list[str]:
    """The genre and profile tables that the base prime and both topics print."""
    default = Config.model_fields["profile"].default.value
    lines = [
        "## Genres and profiles",
        "",
        "A genre is the purpose class of a document.",
        "Find the row whose surfaces match the document. Lint it with the row's profile.",
    ]
    if ruleset is not None:
        lines.append("The row also names the checklist categories for that genre.")
    return [
        *lines,
        "",
        *genre_table(ruleset),
        "",
        ROUTING,
        "",
        "A profile sets the document gates in the next table. "
        "It also sets the categories and rules that run.",
        "",
        *profile_table(),
        "",
        "Each gate is a `[thresholds]` key in the config. `none` means no limit.",
        "These categories are off at each profile:",
        "",
        *categories_off(),
        "",
        f"Each file gets the profile that its config sets, or `{default}` without a config.",
        "`--profile <profile>` overrides it for one run.",
        "A rule whose tier is `excluded` at a profile does not run at that profile.",
        "Run `slopvac lint --explain-config <file>` to print the settings for a file.",
        "Run `slopvac rules --profile <profile>` to list the tier and severity of each rule.",
        "",
    ]


def _handoff_step(settings: GuidanceSettings) -> str | None:
    """The base-prime step before a hand-off, or None when review is off."""
    if settings.review == "auto":
        if settings.review_depth == "self":
            return (
                "Before you hand that text off, run `slopvac prime review`. "
                "Complete its workflow and put its verdict block in the hand-off."
            )
        pass_name = (
            "adversary loop" if settings.review_depth == "adversary" else "reviewer pass"
        )
        return (
            "Before you hand that text off, run `slopvac prime review`. Complete its "
            f"workflow, including the {pass_name}. Put its verdict block in the hand-off."
        )
    if settings.review == "ask":
        return (
            "Before you hand that text off, ask the user whether to run the review "
            "from `slopvac prime review`. If the user agrees, complete its workflow."
        )
    return None


def prime_section(settings: GuidanceSettings) -> list[str]:
    """The base prime's steps that route to the topics; empty when both are off."""
    steps: list[str] = []
    if settings.write != "off":
        steps.append(
            "Before you write or edit that text, run `slopvac prime write`. "
            "Follow its workflow."
        )
    handoff = _handoff_step(settings)
    if handoff:
        steps.append(handoff)
    if not steps:
        return []
    surfaces = ", ".join(_SURFACE_LIST[:-1]) + f", or {_SURFACE_LIST[-1]}"
    return [
        "## Writing and review",
        "",
        f"Follow these steps for {surfaces}.",
        "",
        *(f"{number}. {step}" for number, step in enumerate(steps, 1)),
        "",
    ]


def disabled_notice(topic: str, config_path: Path | None) -> str:
    where = f" in {config_path}" if config_path else ""
    return f'slopvac prime {topic} is disabled by [guidance] {topic} = "off"{where}.'


def render_write(ruleset: RuleSet, settings: GuidanceSettings) -> str:
    """The writing guide: genres, profiles, documentation contract, judgement fixes."""
    lines = [
        "# Slopvac writing guidance",
        "",
        *genres_and_profiles(ruleset),
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
        "1. Find the document's genre in the genre table. Use the profile of that genre.",
        "2. Write from the documentation contract. Keep correct facts from sources.",
        "3. Check claims against code or a source. Verify relevant commands and paths.",
        "4. Apply the rules below that fit the genre.",
        "5. Run each example against a clean install.",
        "6. Lint with `slopvac lint <file>... --profile <profile> --format json`.",
        "7. Fix errors. Run `slopvac explain <rule_id>` to triage warnings.",
        "8. Exit 1 means that a gate failed. Exit 2 means that the run is incomplete.",
    ]
    if settings.review != "off":
        lines.append("9. Before you hand off one of these, run `slopvac prime review`:")
        lines.extend(f"   - {s}" for s in _SURFACE_LIST)
        lines.append("   Complete its configured workflow.")
    lines.extend(
        [
            "",
            *_excluding_content(),
            "## Rules lint cannot check",
            "",
            "Each entry below gives the fix for one rule that needs a reader.",
            *_entry_guide(ruleset, "fix"),
            "Use the categories whose headings list the document's genre.",
            "If the rule question matches the text, apply its fix.",
            "",
            *unlinted(write_checklist(ruleset)),
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"


def _excluding_content() -> list[str]:
    """The order of preference for text that lint must not judge as authored prose."""
    allow = allow_comment("<rule_id>", "<exception>")
    return [
        "## Excluding content",
        "",
        "Lint judges authored prose. For other text, use the first of these that fits:",
        "",
        "1. Put a specimen, a command, or an identifier in a code span or a code block.",
        "2. Put a quotation in quotation marks. "
        "Rules with the `quotation` exception skip it.",
        f"3. For one block that a named exception covers, write `{allow}` "
        "on the line above it.",
        f"4. Put `{DISABLE_COMMENT}` and `{ENABLE_COMMENT}` only around "
        "generated text or quoted specimens.",
        "5. For a whole generated or vendored file, add an `exclude` glob. "
        "Or set its rules off in an `[[overrides]]` block.",
        "",
        "Never suppress a finding to hide a defect in prose that you wrote. Fix the prose.",
        "Run `slopvac prime` for the scope of each directive and how lint reports a bad one.",
        "",
    ]


def _suppression_checks() -> list[str]:
    """What the review asks of each directive that hides text from lint."""
    return [
        "Check each suppression in the document:",
        "",
        "- Each allow reason is a named exception of its rule, and that exception "
        "fits the text.",
        "  Lint does not report a bad reason for a rule that Vale runs. "
        "Check each reason with `slopvac explain <rule_id>`.",
        "- Each directive has the smallest scope that works. "
        "An allow directive for one rule comes before a disable directive.",
        f"- Each `{DISABLE_COMMENT}` has a `{ENABLE_COMMENT}` after it. "
        "A region without one runs to the end of the file.",
        "- No disable directive covers authored prose. "
        "It covers only generated text or quoted specimens.",
        "- A Vale comment, such as `<!-- vale off -->`, hides findings without a reason. "
        "It is an unjustified suppression.",
        "",
    ]


_REVIEWER_PASS = [
    "   - Give it the document and `slopvac prime review` output.",
    "   - If you revised the document, give it the original.",
    "   - Give it any source or brief that is available.",
    "   - It runs steps 1 to 6. It does not edit the document.",
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
    "8. Fix or rebut each reviewer finding.",
    "9. After you edit the document, run lint again.",
    "10. Report the verdict.",
]


def _review_workflow(settings: GuidanceSettings) -> list[str]:
    """The configured author or subagent review steps."""
    if settings.review_depth == "self":
        return [
            '7. Steps 3 to 6 are the review. Report "self (review_depth = self)".',
            "8. Report the verdict.",
        ]
    if settings.review_depth == "adversary":
        return [
            "7. Reviewer pass: run rounds, each with a new fresh-context subagent.",
            *_REVIEWER_PASS,
            "   - The subagent does not run steps 7 to 10.",
            "   - Give each new round the findings you rebutted earlier.",
            "   - When a round reports no finding that you accept, stop.",
            _NO_SUBAGENT,
            *_AFTER_REVIEW,
        ]
    return [
        "7. Reviewer pass: give one fresh-context subagent one pass.",
        *_REVIEWER_PASS,
        "   - The subagent does not run steps 7 to 10.",
        "   - When the user asks for adversary rounds, repeat this pass with a "
        "new subagent. Give it your earlier rebuttals.",
        _NO_SUBAGENT,
        *_AFTER_REVIEW,
    ]


def render_review(ruleset: RuleSet, settings: GuidanceSettings) -> str:
    """The review guide: genres, profiles, lint, checklist, claims, reviewer pass."""
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
            *genres_and_profiles(ruleset),
            "## Workflow",
            "",
            "1. Find the document's genre in the genre table. "
            "Its profile is the `<profile>` in the next steps.",
            "2. Run `slopvac lint <file>... --profile <profile> --format json`.",
            "For errors, run `slopvac explain <rule_id>` to choose a remedy.",
            "Exit 1 means that a gate failed. Exit 2 means that the run is incomplete.",
            "On exit 2, report unchecked entries or the error text.",
            "Fix the cause. Rerun lint. Config or rule errors print text, not JSON.",
            "3. Audit each slopvac directive and each Vale comment in the document.",
            "Apply the suppression checks at the start of the checklist.",
            "4. Ask enforced and advisory checklist questions. Skip excluded ones.",
            "Ask document questions over the document. Ask others at their listed scope.",
            "Find the paired lint rule in each remainder rule's provenance.",
            "When lint reports that partner, ask the remainder question.",
            "Quote failures. Propose rewrites.",
            "5. Mark wording that changes no reader action or contract fact.",
            "The author removes marked wording.",
            "Never mark a fact or an evidence block for removal. Code blocks, logs, "
            "and diffstats are evidence.",
            "List facts in the received document. Confirm each survived or was wrong.",
            "6. Check each claim against code or an authoritative source.",
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
            "Suppressions: <each directive with its rule and reason, and whether it "
            "holds, or none>",
            "Reviewer:  <subagent, <n> rounds | adversary, <n> rounds | self "
            "(review_depth = self | no subagent available)>; <counts of findings fixed and rebutted>",
            "Action:    <the single highest-value change, or none>",
            "```",
            "",
            "Report REVISE for lint exit 1 or 2, a failed claim, or a lost fact.",
            "Also report REVISE for a failed enforced question, failed deletion test, "
            "or open reviewer finding.",
            "Report REVISE for each unjustified suppression too.",
            "Report advisory failures without blocking. Skip excluded questions.",
            "",
            "## Checklist",
            "",
            *_suppression_checks(),
            "Each entry below asks one question that needs a reader.",
            *_entry_guide(ruleset, "question"),
            "Review at the profile from step 1. Ask the questions in the categories "
            "whose headings list the genre.",
            "",
            *unlinted(review_checklist(ruleset)),
        ]
    )
    return "\n".join(lines).rstrip("\n") + "\n"
