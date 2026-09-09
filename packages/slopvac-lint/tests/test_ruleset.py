"""Ruleset integrity.


These tests are the reason the shipped rules can be trusted. A rule whose pattern
stopped firing passes every document, which is indistinguishable from clean prose,
so every claim a rule makes about itself is checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import regex as re

from slopvac.engine import build_substitution_pattern
from slopvac.model import RuleKind, Tier
from slopvac.rules import RuleLoadError, inject_locale_rule, load_ruleset


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()


def test_ruleset_loads_and_verifies(ruleset):
    """load_ruleset raises on any broken rule, so reaching here is the assertion."""
    assert ruleset.rules
    assert ruleset.categories


def test_every_rule_has_provenance(ruleset):
    """A rule nobody can trace is a rule nobody can argue with."""
    for rule in ruleset.rules:
        assert rule.provenance.source, f"{rule.qualified_id} has no source"


def test_ste_refs_are_issue_qualified(ruleset):
    """Rule numbers are not portable across issues: Issue 7 rule 2.3 became
    Issue 9 rule 4.5. An unqualified reference is therefore ambiguous."""
    for rule in ruleset.rules:
        ref = rule.provenance.ste_ref
        if ref is None:
            continue
        assert re.fullmatch(r"\d+:(?:\d+\.\d+|GR-\d+)", ref), (
            f"{rule.qualified_id} has a non-issue-qualified ref: {ref}"
        )


def test_qualified_ids_are_unique(ruleset):
    ids = [r.qualified_id for r in ruleset.rules]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate rule ids: {duplicates}"


def test_judgement_rules_carry_a_decidable_question(ruleset):
    """A judgement rule is the reviewer's only instruction, so an empty or
    taste-based question makes the rule unusable."""
    # Phrases that make the ANSWER a matter of taste. A question may describe the
    # effect a construction has on a reader -- "so the affirmed half sounds
    # larger" is a testable claim about a rhetorical move -- so the test targets
    # the reviewer being asked for a preference, not any use of these verbs.
    banned = (
        "does it read better",
        "does it sound better",
        "do you prefer",
        "is it more elegant",
        "is it beautiful",
        "how does it feel",
        "does it feel right",
        "is it nicer",
    )
    for rule in ruleset.judgement_rules():
        question = rule.judgement_question
        assert question, f"{rule.qualified_id} has no judgement_question"
        assert "?" in question, f"{rule.qualified_id} question is not a question"
        lowered = " ".join(question.lower().split())
        for phrase in banned:
            assert phrase not in lowered, (
                f"{rule.qualified_id} asks for a preference: {phrase!r}"
            )


def test_judgement_rules_never_fire(ruleset):
    """They are carried for the agentic reviewer. If one produced a finding the
    linter would be claiming to check something it cannot."""
    from pathlib import Path

    from slopvac.analyze import parse
    from slopvac.config import Config, resolve_for
    from slopvac.engine import Engine

    judgement = {rule.qualified_id for rule in ruleset.judgement_rules()}
    assert judgement
    text = "\n".join(
        example.bad for rule in ruleset.judgement_rules() for example in rule.examples
    )
    engine = Engine(ruleset.rules, resolve_for(Config(), Path("/repo/a.md")))
    fired = {finding.rule_id for finding in engine.run(parse("a.md", text + "\n"))}
    assert not fired & judgement


def test_reads_better_is_never_an_exception(ruleset):
    """The whole point of the annotation contract: an unnamed override collapses
    the ruleset, which is what Orwell's sixth rule does in an automated pipeline."""
    for rule in ruleset.rules:
        for exception in rule.exceptions:
            assert exception not in {"reads-better", "readability", "flow", "style"}, (
                f"{rule.qualified_id} admits a taste exception: {exception}"
            )


def test_every_lexical_rule_has_an_example(ruleset):
    """An example is the rule's own regression test. Without one, a pattern can
    rot silently."""
    for rule in ruleset.rules:
        if rule.kind in (RuleKind.TOKENS, RuleKind.PATTERN, RuleKind.SUBSTITUTION):
            assert rule.examples, f"{rule.qualified_id} ships no example"


def test_substitution_keys_resolve_to_a_replacement(ruleset):
    """A substitution rule must be able to name the fix for anything it matches.
    Keys are regex, so a direct dict lookup is not enough."""
    from slopvac.engine import match_substitution

    for rule in ruleset.rules:
        if rule.kind is not RuleKind.SUBSTITUTION or not rule.substitutions:
            continue
        pattern = re.compile(
            build_substitution_pattern(rule.substitutions),
            re.IGNORECASE if rule.ignore_case else 0,
        )
        for example in rule.examples:
            match = pattern.search(example.bad)
            assert match, f"{rule.qualified_id}: example does not match"
            replacement = match_substitution(rule.substitutions, match.group(0))
            assert replacement is not None, (
                f"{rule.qualified_id}: matched {match.group(0)!r} but no "
                f"replacement resolved"
            )


def test_tier_values_are_complete(ruleset):
    for rule in ruleset.rules:
        for profile in ("strict", "normal", "relaxed"):
            assert isinstance(rule.tier_for(profile), Tier)


def test_relaxed_is_never_stricter_than_normal_except_by_design(ruleset):
    """Two rules invert the tier ordering deliberately. Every OTHER rule must not,
    because an unexplained inversion is a mistake."""
    allowed = {"meta.invalid-suppression"}
    ranks = {Tier.EXCLUDED: 0, Tier.ADVISORY: 1, Tier.ENFORCED: 2}
    for rule in ruleset.rules:
        if rule.qualified_id in allowed:
            continue
        relaxed = ranks[rule.tier_for("relaxed")]
        normal = ranks[rule.tier_for("normal")]
        assert relaxed <= normal, (
            f"{rule.qualified_id} is stricter at relaxed than at normal"
        )


# --- locale ------------------------------------------------------------------


@pytest.mark.parametrize("tag", ["en-US", "en-GB"])
def test_locale_rule_generates_and_verifies(tag):
    """The generated rule goes through the same validation as a YAML rule, so a
    direction that inverted would fail to load rather than rewrite prose
    backwards."""
    ruleset = load_ruleset()
    note = inject_locale_rule(ruleset, tag)
    assert note is None, note
    rule = ruleset.by_id("ste-words.spelling")
    assert rule is not None
    assert rule.substitutions
    assert tag in rule.name


def test_locale_und_disables_without_error():
    ruleset = load_ruleset()
    assert inject_locale_rule(ruleset, "und") is None
    assert ruleset.by_id("ste-words.spelling") is None


def test_unknown_locale_reports_rather_than_raises():
    """A typo in locale.default must not stop the other 200 rules running."""
    ruleset = load_ruleset()
    note = inject_locale_rule(ruleset, "en-XX")
    assert note is not None
    assert "not known" in note
    assert ruleset.by_id("ste-words.spelling") is None


@pytest.mark.parametrize(
    "tag,text",
    [
        # Neither direction may rewrite correct technical prose. `program`,
        # `disk`, and `check` were all in the variant table at one point and all
        # three broke this.
        ("en-US", "The build checks the program on disk."),
        ("en-GB", "The build checks the program on disk."),
        ("en-US", "Set the color to gray and read the catalog."),
        ("en-GB", "Set the colour to grey and read the catalogue."),
        # CSS and web platform identifiers are American by specification.
        ("en-GB", "Set background-color and currentColor on the dialog."),
        # `whilst`, `amongst`, and `amidst` were in the table and are archaic
        # register rather than locale. The en-GB direction demanded `whilst` for
        # every `while`, which put 3 findings on this project's own README and
        # lowered its score for being written plainly. British technical writing
        # uses the short forms, so both directions must leave these alone.
        ("en-GB", "While the gate runs, it counts among the checks amid the rest."),
        ("en-US", "While the gate runs, it counts among the checks amid the rest."),
    ],
)
def test_locale_leaves_correct_prose_alone(tag, text):
    from slopvac.locale import resolve

    locale = resolve(tag)
    pattern = re.compile(build_substitution_pattern(locale.substitutions), re.I)
    hits = [m.group(0) for m in pattern.finditer(text)]
    assert not hits, f"{tag} would rewrite correct prose: {hits}"


@pytest.mark.parametrize(
    "tag,text,expected",
    [
        ("en-US", "The parser normalises the colour value.", "normalizes"),
        ("en-US", "The build cancelled the licence check.", "canceled"),
        ("en-GB", "The parser normalizes the color value.", "normalises"),
        ("en-GB", "The build canceled the license check.", "cancelled"),
    ],
)
def test_locale_catches_the_other_variant(tag, text, expected):
    from slopvac.engine import match_substitution
    from slopvac.locale import resolve

    locale = resolve(tag)
    pattern = re.compile(build_substitution_pattern(locale.substitutions), re.I)
    replacements = {
        match_substitution(locale.substitutions, m.group(0))
        for m in pattern.finditer(text)
    }
    assert expected in replacements, f"{tag}: got {replacements}"


def test_locale_inflections_are_generated():
    """`initialise` was caught and `initialises` was not, in the first revision of
    the hand-written rule. Generation exists to close that class of gap."""
    from slopvac.locale import resolve

    us = resolve("en-US").substitutions
    for form in ("initialise", "initialises", "initialised", "initialising"):
        assert form in us, f"{form} is missing from the en-US target map"


# --- schema tightening --------------------------------------------------------

_FIXTURES = Path(__file__).parent / "fixtures" / "rules"


def test_a_stray_kind_payload_is_a_load_error():
    """Exactly one kind-specific payload. A leftover field is not ignored."""
    with pytest.raises(RuleLoadError, match=r"stray-tokens.*`tokens`"):
        load_ruleset(extra_dirs=[_FIXTURES / "stray-payload"], verify=False)


def test_a_non_mapping_yaml_document_names_file_and_index(tmp_path):
    (tmp_path / "scalar.yml").write_text("just a string\n", encoding="utf-8")
    with pytest.raises(RuleLoadError, match=r"scalar\.yml: document 0 is a str"):
        load_ruleset(extra_dirs=[tmp_path], verify=False)

    (tmp_path / "scalar.yml").unlink()
    (tmp_path / "list.yml").write_text("- not\n- a mapping\n", encoding="utf-8")
    with pytest.raises(RuleLoadError, match=r"list\.yml: document 0 is a list"):
        load_ruleset(extra_dirs=[tmp_path], verify=False)


def test_empty_yaml_documents_are_allowed():
    ruleset = load_ruleset(extra_dirs=[_FIXTURES / "empty-docs"], verify=False)
    assert ruleset.by_id("empty-docs-probe.only-rule") is not None
