"""Analyzer, engine, and scoring behaviour."""

from __future__ import annotations

import pytest

from slopvac_lint.analyze import count_words, classify_text_type, parse
from slopvac_lint.config import (
    CategorySettings,
    Config,
    Override,
    Profile,
    RuleSettings,
    Severity,
    Thresholds,
    resolve_for,
)
from slopvac_lint.engine import Engine, count_clause_boundaries
from slopvac_lint.model import TextType
from slopvac_lint.rules import load_ruleset
from slopvac_lint.score import MIN_WORDS_FOR_DENSITY, score_document
from pathlib import Path


# --- word counting, ASD-STE100 rules 8.4 through 8.7 -------------------------


@pytest.mark.parametrize(
    "text,expected,why",
    [
        # The specification's own worked example: "13" and "16" each count once,
        # giving 10 rather than the 11 a whitespace split reports.
        ("Do steps 13 thru 16 a minimum of three times.", 10, "numbers count as one"),
        ("The spar box has twenty-one ribs.", 6, "a spelled compound number is one word"),
        # The + unit collapses: temperature/in/the/room/is/[10 degC] = 7 with "The".
        ("The temperature in the room is 10 degC.", 7, "number plus unit is one word"),
        ("Set the timeout to 30 s.", 5, "number plus unit, abbreviated"),
        ("Allocate 512 MiB and cap at 80 %.", 6, "binary and percent units collapse"),
        ('Set the flag to "on and off again".', 5, "a quoted span is one word"),
        ("Run the job (but not on Friday) now.", 5, "parenthesized text is one word"),
        # in-flight/entertainment/system plus "Use" = 4 tokens, and the hyphenated
        # compound is one of them rather than two.
        ("Use the in-flight entertainment system.", 5, "a hyphenated word is one word"),
        ("1. Open the valve.", 3, "a step number is not counted"),
        ("Restart the HTTP daemon.", 4, "an abbreviation is one word, not zero"),
    ],
)
def test_word_counting(text, expected, why):
    assert count_words(text) == expected, why


def test_open_unit_pattern_would_swallow_words():
    """Regression, and the reason UNIT is a closed list.

    An open pattern (`[A-Za-z]{1,12}` after a number) treated any short word as a
    unit, so "13 thru 16" collapsed "thru" into "13" and the specification's own
    worked example came out at 8 words instead of 10. Under-counting is the
    dangerous direction: it lets a genuinely over-long sentence pass the cap.
    """
    assert count_words("Do steps 13 thru 16 a minimum of three times.") == 10
    assert count_words("Wait 30 seconds then retry twice.") == 6
    assert count_words("Retry 3 times before you fail the job.") == 8


@pytest.mark.parametrize(
    "text",
    [
        'Set the flag to "on and off again".',
        "Allocate 512 MiB and cap the rate at 80 %.",
        "Run the job (but not on a Friday) now.",
    ],
)
def test_whitespace_split_overcounts(text):
    """The reason count_words exists. A naive split reports each of these as
    longer than the specification's own arithmetic does, so a compliant sentence
    would be flagged for breaching the 20-word procedural cap."""
    assert len(text.split()) > count_words(text)


# --- text-type classification ------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Run the migration before you deploy.", TextType.PROCEDURAL),
        ("The parser reads the manifest at startup.", TextType.DESCRIPTIVE),
        ("WARNING: this deletes every replica.", TextType.SAFETY),
        # A note inside a procedure is descriptive and takes the wider cap, even
        # though its surroundings are procedural.
        ("NOTE: the cache survives a restart.", TextType.DESCRIPTIVE),
        # A warning takes the procedural cap even when phrased descriptively.
        ("CAUTION: an interrupted write leaves the index unusable.", TextType.SAFETY),
    ],
)
def test_text_type(text, expected):
    assert classify_text_type(text) is expected


# --- clause counting ---------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected,why",
    [
        ("Read the file, parse it, and emit the report.", 1, "a list of actions is one idea"),
        ("The parser reads the file; it emits a report.", 1, "a semicolon joins two"),
        (
            "The parser reads the file, and it normalizes paths; then it emits the "
            "report, but it skips bad entries, which the caller handles.",
            4,
            "four stitches",
        ),
        ("To rebuild the index, run the migration.", 0, "condition before command"),
    ],
)
def test_clause_boundaries(text, expected, why):
    assert count_clause_boundaries(text) == expected, why


# --- parsing -----------------------------------------------------------------


def test_code_fences_are_not_prose():
    document = parse("t.md", "Text here.\n\n```\nrobust seamless powerful\n```\n\nMore.")
    assert "robust" not in document.prose_text()


def test_inline_code_and_links_are_stripped():
    document = parse("t.md", "Use `--robust` and [the seamless doc](http://x/robust).")
    prose = document.prose_text()
    assert "--robust" not in prose
    assert "http" not in prose
    # Link TEXT survives, because it is prose a reader reads.
    assert "the seamless doc" in prose


def test_line_numbers_survive_stripping():
    """A finding must open the right line in the real file, so the prose
    projection stays aligned with the source."""
    document = parse("t.md", "one\n\n```\ncode\n```\n\nrobust here\n")
    index = next(
        i for i, line in enumerate(document.prose_lines) if "robust" in line
    )
    assert document.raw_lines[index] == "robust here"


def test_front_matter_is_parsed_not_linted():
    document = parse("t.md", '---\ntitle: robust thing\n---\n\nBody.\n')
    assert document.front_matter["title"] == "robust thing"
    assert "robust" not in document.prose_text()


def test_suppression_comment_is_not_linted():
    document = parse(
        "t.md", "<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->\nBody.\n"
    )
    assert "slopvac-allow" not in document.prose_text()


# --- config resolution -------------------------------------------------------


def _config(**kwargs) -> Config:
    config = Config(**kwargs)
    object.__setattr__(config, "root", Path("/repo"))
    return config


def test_override_patches_per_field_not_per_table():
    """An override that sets only severity must keep the profile's threshold. This
    is the whole reason the config exists instead of Vale's single file."""
    config = _config(
        profile=Profile.NORMAL,
        overrides=[
            Override(
                files=["docs/**"],
                categories={"prose-inflation": CategorySettings(severity=Severity.WARNING)},
            )
        ],
    )
    resolved = resolve_for(config, Path("/repo/docs/guide.md"))
    settings = resolved.categories["prose-inflation"]
    assert settings.severity is Severity.WARNING
    assert settings.max_per_100_words == 0.6, "the profile's budget survived"


def test_later_override_wins_and_both_are_recorded():
    config = _config(
        overrides=[
            Override(files=["docs/**"], profile=Profile.NORMAL),
            Override(files=["docs/reference/**"], profile=Profile.STRICT),
        ]
    )
    resolved = resolve_for(config, Path("/repo/docs/reference/api.md"))
    assert resolved.profile is Profile.STRICT
    assert len(resolved.applied_overrides) == 2, "both matches are traceable"


def test_non_matching_override_is_ignored():
    config = _config(
        overrides=[Override(files=["docs/**"], profile=Profile.STRICT)]
    )
    assert resolve_for(config, Path("/repo/README.md")).profile is Profile.NORMAL


def test_negated_glob():
    config = _config(
        overrides=[
            Override(files=["docs/**", "!docs/generated/**"], profile=Profile.STRICT)
        ]
    )
    assert resolve_for(config, Path("/repo/docs/a.md")).profile is Profile.STRICT
    assert (
        resolve_for(config, Path("/repo/docs/generated/a.md")).profile is Profile.NORMAL
    )


def test_locale_resolves_per_path():
    config = _config(
        overrides=[Override(files=["docs/en-gb/**"], locale={"default": "en-GB"})]
    )
    assert resolve_for(config, Path("/repo/README.md")).locale.default == "en-US"
    assert (
        resolve_for(config, Path("/repo/docs/en-gb/a.md")).locale.default == "en-GB"
    )


# --- severity precedence -----------------------------------------------------


def _engine(profile=Profile.NORMAL, **config_kwargs) -> Engine:
    ruleset = load_ruleset()
    config = _config(profile=profile, **config_kwargs)
    return Engine(ruleset.rules, resolve_for(config, Path("/repo/a.md")))


def test_category_cap_lowers_severity():
    engine = _engine(
        categories={"orwell": CategorySettings(severity=Severity.SUGGESTION)}
    )
    rule = next(r for r in engine.rules if r.qualified_id == "orwell.stale-figure")
    assert engine.severity_for(rule) is Severity.SUGGESTION


def test_category_cap_never_raises_severity():
    """A coarse dial must not create blocking findings the rule author never
    intended."""
    engine = _engine(
        categories={"prose-craft": CategorySettings(severity=Severity.ERROR)}
    )
    for rule in engine.rules:
        if rule.category != "prose-craft":
            continue
        if rule.severity is Severity.SUGGESTION:
            assert engine.severity_for(rule) is Severity.SUGGESTION
            return
    pytest.skip("no suggestion-level rule in prose-craft to test against")


def test_rule_override_wins_over_category():
    engine = _engine(
        categories={"orwell": CategorySettings(severity=Severity.SUGGESTION)},
        rules={"orwell.stale-figure": RuleSettings(severity=Severity.ERROR)},
    )
    rule = next(r for r in engine.rules if r.qualified_id == "orwell.stale-figure")
    assert engine.severity_for(rule) is Severity.ERROR


def test_disabled_category_removes_its_rules():
    engine = _engine(categories={"orwell": CategorySettings(enabled=False)})
    assert not [r for r in engine.rules if r.category == "orwell"]


def test_rule_off_removes_only_that_rule():
    engine = _engine(rules={"orwell.stale-figure": RuleSettings(severity=Severity.OFF)})
    ids = {r.qualified_id for r in engine.rules}
    assert "orwell.stale-figure" not in ids
    assert "orwell.not-un" in ids


# --- suppression contract ----------------------------------------------------


def _run(text: str, profile=Profile.NORMAL):
    ruleset = load_ruleset()
    config = _config(profile=profile)
    resolved = resolve_for(config, Path("/repo/a.md"))
    engine = Engine(ruleset.rules, resolved)
    return engine.run(parse("a.md", text))


def test_valid_suppression_is_honoured():
    findings = _run(
        "<!-- slopvac-allow: rule=orwell.stale-figure reason=quotation -->\n"
        "It is the tip of the iceberg.\n"
    )
    assert not [f for f in findings if f.rule_id == "orwell.stale-figure"]


def test_invalid_reason_is_reported_and_does_not_suppress():
    """An unnamed override collapses the ruleset, which is what Orwell's sixth
    rule does in an automated pipeline."""
    findings = _run(
        "<!-- slopvac-allow: rule=orwell.stale-figure reason=reads-better -->\n"
        "It is the tip of the iceberg.\n"
    )
    assert [f for f in findings if f.rule_id == "meta.invalid-suppression"]
    assert [f for f in findings if f.rule_id == "orwell.stale-figure"]


def test_missing_reason_is_reported():
    findings = _run(
        "<!-- slopvac-allow: rule=orwell.stale-figure -->\n"
        "It is the tip of the iceberg.\n"
    )
    assert [f for f in findings if f.rule_id == "meta.invalid-suppression"]


def test_disable_block_suppresses_a_range():
    findings = _run(
        "<!-- slopvac-disable -->\n"
        "It is the tip of the iceberg.\n"
        "<!-- slopvac-enable -->\n"
    )
    assert not [f for f in findings if f.rule_id == "orwell.stale-figure"]


# --- scoring -----------------------------------------------------------------


def _score(findings, words, profile=Profile.NORMAL, **kwargs):
    config = _config(profile=profile, **kwargs)
    return score_document(
        path="a.md",
        findings=findings,
        words=words,
        sentences=1,
        paragraphs=1,
        config=resolve_for(config, Path("/repo/a.md")),
        categories_meta={"orwell": 1.5},
    )


def test_clean_document_scores_100():
    result = _score([], 500)
    assert result.score == 100.0
    assert result.passed


def test_short_document_is_not_density_gated():
    """One finding in a 20-word error message is 5.0 per 100 words and would fail
    every budget. This is the flaw in scoring short outputs by density."""
    findings = _run("It is the tip of the iceberg.")
    assert len(findings) >= 1
    result = _score(findings, 7)
    assert result.per_100_words == 0.0, "density is not reported below the floor"


def test_density_is_reported_above_the_floor():
    findings = _run("It is the tip of the iceberg.")
    result = _score(findings, MIN_WORDS_FOR_DENSITY)
    assert result.per_100_words > 0


def test_failure_reasons_are_named():
    """An exit code with no reason is not actionable."""
    findings = _run("It is the tip of the iceberg. A robust, comprehensive tool.")
    result = _score(findings, 200)
    assert not result.passed
    assert result.failure_reasons
    assert any("error" in reason for reason in result.failure_reasons)


def test_min_score_gate():
    findings = _run("It is the tip of the iceberg.")
    result = _score(findings, 100, thresholds=Thresholds(max_errors=None, min_score=99.9))
    assert not result.passed
    assert any("score" in reason for reason in result.failure_reasons)


def test_zero_weight_category_does_not_move_the_score():
    findings = _run("It is the tip of the iceberg.")
    weighted = _score(findings, 200)
    unweighted = _score(
        findings, 200, categories={"orwell": CategorySettings(weight=0)}
    )
    assert unweighted.score > weighted.score
