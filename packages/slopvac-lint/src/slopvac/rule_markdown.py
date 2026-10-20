"""Rules as Markdown for an agent to read: `slopvac rules --format md` and
`slopvac explain --format md`.

Both commands render a rule through `rule_block`, so the fields an agent reads
cannot differ between the listing and the single-rule view. Every value comes
from the loaded catalogue and the profile the caller resolved; nothing here
restates a rule.

Order is deterministic (category id, then rule id) so two runs over the same
catalogue print the same bytes.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable

from .config import Profile
from .guidance import unlinted
from .model import Example, Rule
from .rules import RuleSet

_BACKTICKS = re.compile(r"`+")


def _clean(text: str) -> str:
    """Catalogue prose on one line: YAML folds it across lines."""
    return " ".join(text.split())


def message_text(rule: Rule) -> str:
    """The message with its slots shown as `<name>`.

    `message` is a template. Printed raw it shows `{replacement}`, which reads as
    a bug; `<replacement>` says the slot is filled per finding.
    """
    return rule.message.replace("{", "<").replace("}", ">")


def _by_category(rules: Iterable[Rule]) -> dict[str, list[Rule]]:
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
    return f"## {category.title} (`{category_id}`), recommended for: {genres}"


def _fenced(text: str) -> list[str]:
    """A specimen as a fenced block, two spaces in so it stays in its list item.

    A fence, not a code span: examples hold headings, tables, and lists that a
    span would flatten or that would leak into the outline. Lint skips code
    blocks, so the deliberately bad text raises no finding. The fence is longer
    than any backtick run in the text, so no specimen can close it early.
    """
    longest = max((len(run) for run in _BACKTICKS.findall(text)), default=0)
    fence = "`" * max(3, longest + 1)
    body = [f"  {line}" if line else "" for line in text.strip("\n").splitlines()]
    return [f"  {fence}text", *body, f"  {fence}"]


def _example(number: int, example: Example) -> list[str]:
    lines = [f"- Example {number}, `bad`:", "", *_fenced(example.bad), ""]
    if example.good is None:
        lines.append("  `good`: none.")
    elif not example.good.strip():
        # An empty rewrite is the rewrite: the fix deletes the text.
        lines.append("  `good`: empty, so the fix deletes the text.")
    else:
        lines.extend(["  `good`:", "", *_fenced(example.good)])
    if example.note:
        lines.extend(["", f"  Note: {_clean(example.note)}"])
    return lines


def _source(rule: Rule) -> str:
    provenance = rule.provenance
    refs = [
        f"{name} `{value}`"
        for name, value in (
            ("ste_ref", provenance.ste_ref),
            ("orwell_ref", provenance.orwell_ref),
        )
        if value
    ]
    if provenance.url:
        refs.append(f"url <{provenance.url}>")
    return "; ".join([_clean(provenance.source), *refs])


def rule_block(rule: Rule, profile: str, severity: str) -> list[str]:
    """One rule at `profile`, whose resolved severity is `severity`."""
    tiers = " ".join(f"{p.value}={rule.tier_for(p.value).value}" for p in Profile)
    lines = [
        f"### `{rule.qualified_id}`: {_clean(rule.name)}",
        "",
        f"- Category: `{rule.category}`",
        f"- Scope: `{rule.scope.value}`",
        f"- Kind: `{rule.kind.value}`",
        f"- Severity: `{rule.severity.value}`; at `{profile}`: `{severity}`",
        f"- Tier at `{profile}`: `{rule.tier_for(profile).value}`; all tiers: `{tiers}`",
    ]
    if rule.judgement_question:
        lines.append(f"- Question: {_clean(rule.judgement_question)}")
    else:
        lines.append(f"- Message: {_clean(message_text(rule))}")
    if rule.fix:
        lines.append(f"- Fix: {_clean(rule.fix)}")
    for number, example in enumerate(rule.examples, 1):
        lines.extend(_example(number, example))
    if rule.exceptions:
        lines.append("- Exceptions: " + ", ".join(f"`{name}`" for name in rule.exceptions))
    lines.append(f"- Source: {_source(rule)}")
    if rule.provenance.note:
        lines.append(f"- Source note: {_clean(rule.provenance.note)}")
    return lines


def render_explain(rule: Rule, profile: str, severity: str) -> str:
    """`slopvac explain --format md`: the block that `slopvac rules` prints."""
    return "\n".join(unlinted(rule_block(rule, profile, severity))) + "\n"


def render_rules(
    ruleset: RuleSet,
    rules: Iterable[Rule],
    profile: str,
    severity_of: Callable[[Rule], str],
    excluded_omitted: bool,
) -> str:
    """`slopvac rules --format md`: one block per rule, grouped by category."""
    grouped = _by_category(rules)
    count = sum(len(bucket) for bucket in grouped.values())
    lines = [
        "# Slopvac rules",
        "",
        f"This list has {count} {'rule' if count == 1 else 'rules'}, "
        f"with tiers and severities at `{profile}`.",
    ]
    if excluded_omitted:
        lines.append(
            f"It omits the rules that `{profile}` excludes. "
            "Add `--include-excluded` to print them."
        )
    body: list[str] = []
    for category_id, bucket in grouped.items():
        body.extend([_category_heading(ruleset, category_id), ""])
        for rule in bucket:
            body.extend([*rule_block(rule, profile, severity_of(rule)), ""])
    if body:
        # The fences already keep the specimens out of lint. The rest of each
        # block quotes catalogue prose, such as questions, fixes, and source
        # notes, that is not written to the `strict` profile that agent guidance
        # is linted at: unwrapped, the `consumer` judgement listing raised over
        # 400 findings. So the generated body is unlinted and the header is not,
        # as in the prime guides.
        lines.extend(["", *unlinted(body[:-1])])
    return "\n".join(lines) + "\n"
