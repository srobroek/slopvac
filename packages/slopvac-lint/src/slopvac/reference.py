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

THE DETERMINISTIC SPLIT IS THE ORGANISING PRINCIPLE, not a column. A rule that a
checker executes and a rule that only a reader can settle are different kinds of
promise, and mixing them produces the two failures this tool exists to avoid: a
reader who thinks a judgement rule gates their build, and an agent that thinks a
mechanical rule is a matter of opinion. `RuleKind.JUDGEMENT` is the whole of the
non-deterministic set -- it is defined as the rules no linter can check -- so the
partition needs no heuristic.

REDISTRIBUTION IS SCOPED. Rules derived from ASD-STE100 cite a rule NUMBER and
nothing else: no rule prose, no worked examples from the specification, and no
part of its wordlist. Those citations are facts about where an idea came from.
Everything shown as prose or example in this document is written here.
"""

from __future__ import annotations

from collections import defaultdict

from .model import Rule, RuleKind
from .rules import RuleSet

#: Every kind except JUDGEMENT. Derived rather than listed, so a new kind added to
#: the enum lands on the deterministic side by default -- which is correct, since
#: a new kind exists because something became checkable.
DETERMINISTIC_KINDS = tuple(k for k in RuleKind if k is not RuleKind.JUDGEMENT)

_KIND_BLURB = {
    RuleKind.TOKENS: "literal phrases, matched on word boundaries",
    RuleKind.PATTERN: "a regular expression",
    RuleKind.SUBSTITUTION: "a from/to map; the message names the replacement",
    RuleKind.VOCABULARY: "a lookup in the project blocklist, keyed by part of speech",
    RuleKind.METRIC: "a counted measurement against a threshold",
    RuleKind.STRUCTURE: "block-level shape",
    RuleKind.JUDGEMENT: "not mechanizable; a reader or a reviewing agent settles it",
}

_TIER_ORDER = ("strict", "normal", "relaxed")


def _anchor(text: str) -> str:
    """A GitHub-style heading anchor.

    Written out rather than imported: the algorithm is three rules and adding a
    dependency to a docs generator to get them is a poor trade.
    """
    keep = [c for c in text.lower() if c.isalnum() or c in " -_"]
    return "".join(keep).strip().replace(" ", "-")


def _provenance_line(rule: Rule) -> str:
    """Where the rule came from, in one line.

    An STE rule cites its NUMBER only. That is the scope of what may be
    redistributed, and it is also all a reader needs to look the rule up in their
    own copy of the specification.
    """
    provenance = rule.provenance
    parts = [provenance.source]
    if provenance.ste_ref:
        issue, number = provenance.ste_ref.split(":", 1)
        parts = [f"ASD-STE100 issue {issue}, rule {number}"]
    elif provenance.orwell_ref:
        parts = [f"Orwell 1946, rule {provenance.orwell_ref}"]
    if provenance.url:
        parts.append(f"<{provenance.url}>")
    return " — ".join(parts)


def _tier_cell(rule: Rule) -> str:
    """The rule's disposition at each profile, most severe profile first.

    `.value` rather than `str()`: `Tier` subclasses `str`, so `str()` returns
    `Tier.ENFORCED` and the Python repr ends up in a published document.
    """
    tiers = rule.tiers or {}
    return " / ".join(
        getattr(tiers.get(tier), "value", "—") for tier in _TIER_ORDER
    )


def _rule_section(rule: Rule) -> list[str]:
    lines = [f"#### `{rule.qualified_id}`", "", rule.name, ""]

    facts = [
        f"- **Kind.** {rule.kind.value} — {_KIND_BLURB[rule.kind]}",
        f"- **Ships as.** {rule.severity.value}",
        f"- **strict / normal / relaxed.** {_tier_cell(rule)}",
        f"- **Scope.** {rule.scope.value}",
    ]
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
    if rule.kind is RuleKind.JUDGEMENT and rule.judgement_question:
        facts.append(f"- **Question.** {rule.judgement_question}")
    facts.append(f"- **Source.** {_provenance_line(rule)}")
    lines.extend(facts)

    if rule.provenance.note:
        lines.extend(["", rule.provenance.note])

    # Examples are shown for judgement rules and withheld for the rest. A
    # mechanical rule's example adds nothing a reader cannot get from `explain`,
    # and 150 of them triples the document; a judgement rule's example is the only
    # thing that makes it applicable at all, because there is no pattern to read.
    if rule.kind is RuleKind.JUDGEMENT and rule.examples:
        lines.append("")
        for example in rule.examples[:2]:
            lines.append(f"  > **Not this.** {example.bad}")
            lines.append("  >")
            # An empty `good` is meaningful and common here: for a whole class of
            # these rules the fix IS deletion. Rendered as words rather than as a
            # bare `**This.**` with nothing after it, which reads as a truncated
            # document rather than as an instruction.
            good = example.good.strip()
            lines.append(
                f"  > **This.** {good}" if good else "  > **This.** *(delete it)*"
            )
            if example.note:
                lines.append("  >")
                lines.append(f"  > {example.note}")
            lines.append("")
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


def _partition(rules: list[Rule]) -> tuple[list[Rule], list[Rule]]:
    deterministic = [r for r in rules if r.kind is not RuleKind.JUDGEMENT]
    judgement = [r for r in rules if r.kind is RuleKind.JUDGEMENT]
    return deterministic, judgement


def _by_category(rules: list[Rule]) -> dict[str, list[Rule]]:
    buckets: dict[str, list[Rule]] = defaultdict(list)
    for rule in rules:
        buckets[rule.category].append(rule)
    return dict(sorted(buckets.items()))


def _summary_table(ruleset: RuleSet, rules: list[Rule]) -> list[str]:
    deterministic, judgement = _partition(rules)
    det_by_category = _by_category(deterministic)
    jud_by_category = _by_category(judgement)

    lines = [
        "| Category | Checked | Judgement | Weight | Recommended for |",
        "| --- | --: | --: | --: | --- |",
    ]
    for category_id in sorted(set(det_by_category) | set(jud_by_category)):
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
            f"| {len(det_by_category.get(category_id, []))} "
            f"| {len(jud_by_category.get(category_id, []))} "
            f"| {weight} | {genres} |"
        )
    lines.append(
        f"| **Total** | **{len(deterministic)}** | **{len(judgement)}** | | |"
    )
    return lines


def render_reference(ruleset: RuleSet, *, version: str) -> str:
    """The whole rules reference, as markdown.

    No timestamp and no run-specific detail anywhere in the output. A generated
    file that changes on every run cannot be diff-checked in CI, and a diff check
    is the only thing that keeps this honest.
    """
    deterministic, judgement = _partition(ruleset.rules)
    kind_counts = sorted(
        ((k, sum(1 for r in deterministic if r.kind is k)) for k in DETERMINISTIC_KINDS),
        key=lambda pair: -pair[1],
    )

    lines: list[str] = [
        "# Rules reference",
        "",
        "<!-- Generated by `slopvac reference`. Do not edit: run "
        "`slopvac reference --write docs/rules.md`. -->",
        "",
        f"slopvac {version} ships **{len(ruleset.rules)} rules** across "
        f"**{len(ruleset.categories)} categories**.",
        "",
        "The split below is the one that matters when you plan work against this "
        "list:",
        "",
        f"- **{len(deterministic)} checked rules** are executed by a checker — Vale "
        "or the native engine. They produce findings, they gate a build, and two "
        "runs over the same text agree.",
        f"- **{len(judgement)} judgement rules** are not mechanizable. No checker "
        "runs them and they never produce a finding. They ship because a reviewing "
        "agent needs one source of truth rather than a second, drifting list, and "
        "because a rule that cannot be automated is not thereby less true.",
        "",
        "Mixing the two produces the failures this tool exists to avoid: a reader "
        "who believes a judgement rule gates their build, and an agent that treats "
        "a mechanical rule as a matter of opinion.",
        "",
        "Rules derived from ASD-STE100 cite a rule **number** only. No rule prose, "
        "worked example, or wordlist entry from that specification is reproduced "
        "here; every example below is written for this project.",
        "",
        "## Categories",
        "",
    ]
    lines.extend(_summary_table(ruleset, ruleset.rules))
    lines.extend(
        [
            "",
            "Weight scales a category's contribution to the overall score. A weight "
            "of 0 makes the category informational: it still reports, and it cannot "
            "fail the score gate.",
            "",
            "## Checked rules",
            "",
            "By kind: "
            + ", ".join(f"{count} {kind.value}" for kind, count in kind_counts if count)
            + ".",
            "",
            "Each rule lists what it ships as, then its disposition at strict, "
            "normal, and relaxed. `off` at a tier means the rule does not run there; "
            "a severity means it runs at that severity.",
            "",
        ]
    )
    for category_id, rules in _by_category(deterministic).items():
        lines.extend(_category_block(ruleset, category_id, rules))

    lines.extend(
        [
            "## Judgement rules",
            "",
            "None of these produce a finding. Each carries the question a reviewer "
            "answers, and an example, because there is no pattern to read instead.",
            "",
        ]
    )
    for category_id, rules in _by_category(judgement).items():
        lines.extend(_category_block(ruleset, category_id, rules))

    # One trailing newline, and no blank line before it, so the file is stable
    # under any formatter a contributor happens to have on save.
    return "\n".join(lines).rstrip("\n") + "\n"
