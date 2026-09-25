"""The generated rules reference.

WHY THIS IS GENERATED AND CI-CHECKED. A hand-written list of two hundred rules
across twenty-odd categories is wrong within a week, and wrong in the direction
that costs most: a
reader who plans against the document finds the rule was renamed, retiered, or
never existed. So the document is produced from the same `RuleSet` the linter
loads, and `--check` fails the build when the committed copy disagrees. That makes
the file a build artifact that happens to be committed -- committed because it
must be readable on the forge without running anything, checked because a
committed artifact with no check is just a stale file with extra steps.

ONLY CHECKED RULES ARE PUBLISHED HERE. Contextual rule work lives on a separate
development branch and is not part of the current linter surface.

REDISTRIBUTION IS SCOPED. Rules derived from ASD-STE100 cite a rule NUMBER and
nothing else: no rule prose, no worked examples from the specification, and no
part of its wordlist. Those citations are facts about where an idea came from.
Everything shown as prose or example in this document is written here.
"""

from __future__ import annotations

from collections import defaultdict

from .config import Profile, Severity
from .model import Rule, RuleKind
from .profiles import profile_rule_defaults
from .rules import RuleSet

CHECKED_KINDS = tuple(RuleKind)

_KIND_BLURB = {
    RuleKind.TOKENS: "literal phrases, matched on word boundaries",
    RuleKind.PATTERN: "a regular expression",
    RuleKind.SUBSTITUTION: "a from/to map; the message names the replacement",
    RuleKind.VOCABULARY: "a lookup in the project blocklist, keyed by part of speech",
    RuleKind.METRIC: "a counted measurement against a threshold",
    RuleKind.STRUCTURE: "block-level shape",
}

_TIER_ORDER = ("strict", "normal", "relaxed")


def _anchor(text: str) -> str:
    """A GitHub-style heading anchor.

    Written out rather than imported: the algorithm is three rules and adding a
    dependency to a docs generator to get them is a poor trade.
    """
    keep = [c for c in text.lower() if c.isalnum() or c in " -_"]
    return "".join(keep).strip().replace(" ", "-")


def _reference_line(rule: Rule) -> str | None:
    """Return the user-facing source reference without repository archaeology."""
    provenance = rule.provenance
    if provenance.ste_ref:
        issue, number = provenance.ste_ref.split(":", 1)
        value = f"ASD-STE100 issue {issue}, rule {number}"
        if provenance.url:
            value += f" — <{provenance.url}>"
        return value
    if provenance.orwell_ref:
        value = f"Orwell 1946, rule {provenance.orwell_ref}"
        if provenance.url:
            value += f" — <{provenance.url}>"
        return value
    if provenance.url and "github.com/srobroek/slopvac" not in provenance.url:
        return f"<{provenance.url}>"
    return None

def _tier_cell(rule: Rule) -> str:
    """The rule's disposition at each profile, most severe profile first.

    `.value` rather than `str()`: `Tier` subclasses `str`, so `str()` returns
    `Tier.ENFORCED` and the Python repr ends up in a published document.
    """
    tiers = rule.tiers or {}
    return " / ".join(getattr(tiers.get(tier), "value", "—") for tier in _TIER_ORDER)


def _off_by_default(rule: Rule) -> str | None:
    """The profiles whose per-rule defaults ship this rule off, or None.

    A SEPARATE fact from the tier row, because they answer different questions and
    conflating them is how a reader concludes a rule is unreachable. The tier says
    whether the profile admits the rule at all -- `excluded` is final, no config
    layer undoes it. A profile default says the rule is installed and quiet, and a
    `[rules."..."]` entry turns it on. Read from `profile_rule_defaults` rather than
    restated here so the document cannot disagree with the table the linter loads.
    """
    off: list[str] = []
    for profile in Profile:
        settings = profile_rule_defaults(profile).get(rule.qualified_id)
        if settings is not None and settings.severity is Severity.OFF:
            off.append(profile.value)
    return ", ".join(off) or None


def _rule_section(rule: Rule) -> list[str]:
    lines = [f"#### `{rule.qualified_id}`", "", rule.name, ""]

    facts = [
        f"- **Kind.** {rule.kind.value} — {_KIND_BLURB[rule.kind]}",
        f"- **Ships as.** {rule.severity.value}",
        f"- **strict / normal / relaxed.** {_tier_cell(rule)}",
        f"- **Scope.** {rule.scope.value}",
    ]
    off = _off_by_default(rule)
    if off is not None:
        facts.append(
            f"- **Off by profile default.** {off} — the rule is installed and "
            f'silent; a `[rules."{rule.qualified_id}"]` entry with a severity '
            f"turns on that rule and no other. Distinct from the tier row "
            f"above: an `excluded` tier cannot be switched back on, a profile "
            f"default can"
        )
    if rule.text_type and rule.text_type.value != "any":
        facts.append(f"- **Applies to.** {rule.text_type.value} text")
    if rule.fix:
        facts.append(f"- **Fix.** {rule.fix}")
    if rule.exceptions:
        named = ", ".join(f"`{name}`" for name in rule.exceptions)
        facts.append(
            f"- **Suppressible with.** {named} — any other reason is reported "
            f"rather than honoured"
        )
    reference = _reference_line(rule)
    if reference:
        facts.append(f"- **Reference.** {reference}")
    facts.append(
        f"- **AI register signal.** `{rule.ai_signal}` ({rule.ai_signal_source})"
    )
    lines.extend(facts)

    lines.append("")
    return lines


def _category_block(ruleset: RuleSet, category_id: str, rules: list[Rule]) -> list[str]:
    category = ruleset.categories.get(category_id)
    title = category.title if category else category_id
    lines = [f"### {title} (`{category_id}`)", ""]
    if category:
        lines.extend([category.description, ""])
        meta = f"Weight **{category.weight}**."
        if category.recommended_for:
            genres = ", ".join(f"`{g}`" for g in category.recommended_for)
            meta += f" Recommended for {genres}."
        lines.extend([meta, ""])
    for rule in sorted(rules, key=lambda r: r.qualified_id):
        lines.extend(_rule_section(rule))
    return lines


def _checked(rules: list[Rule]) -> list[Rule]:
    return list(rules)


def _by_category(rules: list[Rule]) -> dict[str, list[Rule]]:
    buckets: dict[str, list[Rule]] = defaultdict(list)
    for rule in rules:
        buckets[rule.category].append(rule)
    return dict(sorted(buckets.items()))


def _summary_table(ruleset: RuleSet, rules: list[Rule]) -> list[str]:
    checked_by_category = _by_category(rules)

    lines = [
        "| Category | Checked | Weight | Recommended for |",
        "| --- | --: | --: | --- |",
    ]
    for category_id, category_rules in checked_by_category.items():
        category = ruleset.categories.get(category_id)
        title = category.title if category else category_id
        genres = (
            ", ".join(f"`{g}`" for g in category.recommended_for)
            if category and category.recommended_for
            else "—"
        )
        weight = category.weight if category else "—"
        lines.append(
            f"| [{title}](#{_anchor(f'{title} {category_id}')}) "
            f"| {len(category_rules)} | {weight} | {genres} |"
        )
    lines.append(f"| **Total** | **{len(rules)}** | | |")
    return lines

def render_reference(ruleset: RuleSet) -> str:
    """Render the checked linter rules as stable Markdown."""
    checked = _checked(ruleset.rules)
    checked_categories = {rule.category for rule in checked}
    kind_counts = sorted(
        (
            (kind, sum(1 for rule in checked if rule.kind is kind))
            for kind in CHECKED_KINDS
        ),
        key=lambda pair: -pair[1],
    )

    lines: list[str] = [
        "# Rules reference",
        "",
        "<!-- Generated by `slopvac reference`. Do not edit: run "
        "`slopvac reference --write docs/rules.md`. -->",
        "",
        f"slopvac ships **{len(checked)} checked rules** across "
        f"**{len(checked_categories)} categories**.",
        "",
        "These rules run through Vale or the native engine and can contribute to "
        "the lint result.",
        "",
        "Rules derived from ASD-STE100 cite a rule **number** only. No rule prose, "
        "worked example, or wordlist entry from that specification is reproduced "
        "here; every example below is written for this project.",
        "",
        "## Categories",
        "",
    ]
    lines.extend(_summary_table(ruleset, checked))
    lines.extend(
        [
            "",
            "Weight scales a category's contribution to the overall score. A weight "
            "of 0 keeps findings visible but removes that category from ordinary "
            "score, density, error, and warning gates. Dedicated gates such as the "
            "Unicode-dash ceiling remain independent.",
            "",
            "## Checked rules",
            "",
            "By kind: "
            + ", ".join(
                f"{count} {kind.value}" for kind, count in kind_counts if count
            )
            + ".",
            "",
            "Each rule lists what it ships as, then its disposition at strict, "
            "normal, and relaxed. `excluded` at a tier means the rule does not run "
            "there and no configuration switches it back on; `advisory` means it "
            "runs but cannot fail the gate on its own; `enforced` means it runs at "
            "the severity the profile resolves.",
            "",
            "A separate **Off by profile default** line names the profiles that "
            "install a rule and leave it silent. That is not a tier: the rule is "
            'reachable, and a `[rules."<id>"]` entry naming a severity turns that '
            "rule on without turning on any sibling rule. The entry is a top-level "
            "setting, so it applies wherever the rule's profile and category admit "
            "it rather than to one profile. A rule in a category the profile "
            "switches off needs the category enabled too, because the category is "
            "checked before the per-rule setting.",
            "",
        ]
    )
    for category_id, rules in _by_category(checked).items():
        lines.extend(_category_block(ruleset, category_id, rules))

    return "\n".join(lines).rstrip("\n") + "\n"
