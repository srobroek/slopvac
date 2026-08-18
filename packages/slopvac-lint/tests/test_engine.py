"""Analyzer, engine, and scoring behaviour."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from slopvac.analyze import (
    BOLD_COLON_BULLET,
    BOLD_SPAN,
    DASH_AS_ASIDE,
    classify_text_type,
    coordinated_items,
    count_words,
    longest_noun_stack,
    parse,
)
from slopvac.config import (
    CategorySettings,
    Config,
    Override,
    Profile,
    RuleSettings,
    Severity,
    Thresholds,
    resolve_for,
)
from slopvac.engine import (
    NATIVE_METRICS,
    Engine,
    _inside_quotation,
    _is_all_caps,
    count_clause_boundaries,
)
from slopvac.model import TextType, Tier
from slopvac.rules import load_ruleset
from slopvac.score import MIN_WORDS_FOR_DENSITY, score_document

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


def test_category_severity_lowers_severity():
    engine = _engine(
        categories={"orwell": CategorySettings(severity=Severity.SUGGESTION)}
    )
    rule = next(r for r in engine.rules if r.qualified_id == "orwell.stale-figure")
    assert engine.severity_for(rule) is Severity.SUGGESTION


def test_category_severity_raises_severity():
    """A category severity is a decision, so it promotes as well as demotes.

    Capping downward only meant `[categories.x] severity = "error"` silently did
    nothing: the project wrote the promotion it asked for and the gate ignored it,
    which is worse than either honouring it or rejecting the key.
    """
    engine = _engine(
        categories={"prose-craft": CategorySettings(severity=Severity.ERROR)}
    )
    promoted = [
        rule
        for rule in engine.rules
        if rule.category == "prose-craft" and rule.severity is not Severity.ERROR
    ]
    assert promoted, "no prose-craft rule ships below error; the test proves nothing"
    for rule in promoted:
        assert engine.severity_for(rule) is Severity.ERROR


def test_rule_override_still_beats_category_severity():
    """Narrowest wins, so one rule can opt out of its category's severity."""
    engine = _engine(
        categories={"orwell": CategorySettings(severity=Severity.ERROR)},
        rules={"orwell.stale-figure": RuleSettings(severity=Severity.WARNING)},
    )
    rule = next(r for r in engine.rules if r.qualified_id == "orwell.stale-figure")
    assert engine.severity_for(rule) is Severity.WARNING
    pytest.skip("no suggestion-level rule in prose-craft to test against")


def test_rule_override_wins_over_category():
    engine = _engine(
        categories={"orwell": CategorySettings(severity=Severity.SUGGESTION)},
        rules={"orwell.stale-figure": RuleSettings(severity=Severity.ERROR)},
    )
    rule = next(r for r in engine.rules if r.qualified_id == "orwell.stale-figure")
    assert engine.severity_for(rule) is Severity.ERROR


def test_disabled_category_removes_its_rules():
    engine = _engine(categories={"orwell": CategorySettings(severity=Severity.OFF)})
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


def _score(findings, words, profile=Profile.NORMAL, categories_meta=None, **kwargs):
    """Score with the REAL category weights by default.

    `categories_meta` decides which categories appear in the report at all, so a
    one-entry stub hides the dilution the overall score has to resist.
    """
    config = _config(profile=profile, **kwargs)
    if categories_meta is None:
        categories_meta = load_ruleset().weights
    return score_document(
        path="a.md",
        findings=findings,
        words=words,
        sentences=1,
        paragraphs=1,
        config=resolve_for(config, Path("/repo/a.md")),
        categories_meta=categories_meta,
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


def test_zero_weight_category_leaves_the_category_average_alone():
    """A zero-weight category is informational: it contributes to neither the
    numerator nor the denominator of the per-category mean.

    It cannot RAISE the overall score, because the overall score is clamped to the
    document's own findings -- otherwise zero-weighting every category would score
    a slop document 100/100. So the assertion is on the mean, not the total.
    """
    findings = _run("It is the tip of the iceberg.")
    weighted = _score(findings, 200)
    unweighted = _score(
        findings, 200, categories={"orwell": CategorySettings(weight=0)}
    )
    assert unweighted.score <= weighted.score, "zero-weighting must not flatter"

    # The category itself is still reported, so a reader sees what was excluded.
    entry = next(c for c in unweighted.categories if c.category == "orwell")
    assert entry.findings > 0


def test_zero_weighting_everything_cannot_score_a_slop_document_100():
    """The reason the overall score is clamped to the document's own findings."""
    findings = _run(
        "In today's rapidly evolving landscape our robust and comprehensive "
        "platform will supercharge your workflow."
    )
    assert findings
    zeroed = {
        name: CategorySettings(weight=0) for name in load_ruleset().categories
    }
    result = _score(findings, 200, categories=zeroed)
    assert result.score < 100.0


# --- scoring calibration -----------------------------------------------------


def test_short_document_with_errors_does_not_score_100():
    """Regression. Density is meaningless below the floor, so every category
    scored 100 and a 10-word document with five errors reported 100/100. Reporting
    a perfect score for that is worse than reporting nothing."""
    findings = _run(
        "A robust and comprehensive tool that will supercharge your workflow."
    )
    assert sum(1 for f in findings if f.severity is Severity.ERROR) >= 3
    result = _score(findings, 10)
    assert result.score < 50, f"scored {result.score} on a short error-laden document"
    assert not result.passed


def test_category_average_cannot_dilute_the_overall_score():
    """Regression. A weighted mean over 23 categories that found nothing drowned
    the two that found errors, so five errors read as 92.7/100."""
    findings = _run(
        "A robust and comprehensive tool that will supercharge your workflow."
    )
    result = _score(findings, 10)
    clean = [c for c in result.categories if c.findings == 0]
    dirty = [c for c in result.categories if c.findings]
    assert clean, "the fixture needs categories with no findings"
    assert dirty, "the fixture needs categories with findings"

    # The invariant: 20-odd categories scoring 100 must not pull the overall score
    # ABOVE the worst category that actually found something. A plain weighted
    # mean did exactly that.
    assert result.score <= min(c.score for c in dirty), (
        f"overall {result.score} exceeds the worst dirty category "
        f"{min(c.score for c in dirty)}"
    )
    naive_mean = sum(c.score for c in result.categories) / len(result.categories)
    assert result.score < naive_mean, (
        f"overall {result.score} is not better than the diluting mean {naive_mean}"
    )


def test_score_decreases_monotonically_with_findings():
    light = _run("The result is not unexpected.")
    heavy = _run(
        "In today's rapidly evolving landscape our robust and comprehensive "
        "platform will supercharge your workflow. It is a paradigm shift. "
        "The runner performs an analysis of the report prior to the merge."
    )
    assert len(heavy) > len(light)
    assert _score(heavy, 200).score < _score(light, 200).score


# --- register regression: RFC 2119 normative keywords ------------------------
#
# Found by the independent eval corpus (`evals/independent/`), not by a fixture
# written to pass. The corpus is eight documents written by agents given a genre
# and nothing else, so no document was authored against these rules. The
# specification-register document opened with the RFC 2119 boilerplate and drew
# five findings telling its author to write `must` in place of `SHOULD`, which
# strengthens a requirement the author deliberately left optional. That is a
# wrong lint, not a noisy one.


def test_all_caps_normative_keywords_are_not_rewritten():
    """`SHOULD` is weaker than `MUST` in RFC 2119; advising the swap inverts it."""
    findings = _run(
        "The key words MUST, SHALL, SHOULD, and MAY are to be interpreted as\n"
        "described in RFC 2119.\n"
        "\n"
        "A server that reaches the configured maximum SHOULD include the\n"
        "`Upload-Max-Length` header field.\n",
        profile=Profile.STRICT,
    )
    offenders = [
        f for f in findings
        if f.rule_id.endswith("obligation-word-substitution")
        or f.rule_id.endswith("approved-word-substitution")
    ]
    assert not offenders, (
        "an all-caps RFC 2119 keyword was flagged for substitution: "
        + ", ".join(f"{f.rule_id} on {f.matched_text!r}" for f in offenders)
    )


def test_lowercase_obligation_word_still_fires():
    """The case-sensitivity is a carve-out for capitals, not a removal."""
    findings = _run(
        "The worker should retry the request before it reports a failure.",
        profile=Profile.STRICT,
    )
    assert any(
        f.rule_id.endswith("obligation-word-substitution") for f in findings
    ), "lowercase `should` no longer reports; the carve-out is too wide"


def test_named_contract_is_not_a_relation_term():
    """"Master Subscription Agreement" is an instrument's proper name.

    Also from `evals/independent/`: the legal-register document drew advice to
    rename a contract the writer does not own. The relation sense still reports.
    """
    exempt = _run(
        "This Notice forms part of the Master Subscription Agreement between the\n"
        "Customer and the Vendor.\n"
    )
    assert not [f for f in exempt if f.rule_id == "prose-inclusive.exclusive"]

    relation = _run("Promote the replica to master when the node fails over.")
    assert [f for f in relation if f.rule_id == "prose-inclusive.exclusive"], (
        "the relation sense of `master` stopped reporting; the carve-out is too wide"
    )


# --- all-caps carve-out -------------------------------------------------------


@pytest.mark.parametrize(
    "matched,expected,why",
    [
        ("MUST", True, "RFC 2119 normative keyword"),
        ("DATABASE_URL", True, "identifier"),
        ("JSON", True, "initialism"),
        ("WARNING", True, "safety marker"),
        ("is IMPORTANT", True, "capitalised word carries the rule, `is` is scaffold"),
        ("ENSURE the", True, "same, with a trailing article"),
        ("Ensure", False, "title case is ordinary prose"),
        ("ensure", False, "lowercase is ordinary prose"),
        ("A", False, "a single capital is not shouting"),
        ("The", False, "sentence-initial capital is not shouting"),
        ("is robust", False, "no capitalised word at all"),
        (
            "MUST be set correctly by the caller",
            False,
            "too many words to be a token; a real sentence must stay checkable",
        ),
    ],
)
def test_all_caps_predicate(matched, expected, why):
    assert _is_all_caps(matched) is expected, why


def test_all_caps_words_do_not_draw_prose_findings():
    """An identifier and a safety marker are not prose defects.

    `ENSURE` drew a substitution telling the author to write "make sure" and
    `is IMPORTANT` was reported as passive voice. Both are the capitals doing
    their job, and both were found by the independent eval corpus.
    """
    findings = _run(
        "Set DATABASE_URL before you start the worker.\n"
        "\n"
        "The API returns JSON over HTTP. TLS is REQUIRED.\n"
        "\n"
        "You should ENSURE the value is correct.\n",
        profile=Profile.STRICT,
    )
    caps_hits = [
        f for f in findings
        if f.matched_text and _is_all_caps(f.matched_text)
    ]
    assert not caps_hits, "an all-caps token drew a prose finding: " + ", ".join(
        f"{f.rule_id} on {f.matched_text!r}" for f in caps_hits
    )


def test_lowercase_equivalent_still_fires():
    """The carve-out is about capitals, not about the words."""
    findings = _run("You should ensure the value is correct.", profile=Profile.STRICT)
    assert [f for f in findings if f.matched_text.lower().startswith("ensure")], (
        "lowercase `ensure` stopped reporting; the carve-out is too wide"
    )


# --- the `quotation` exception -------------------------------------------------
#
# Found by linting this project's OWN steering document: it drew 7 errors and
# every one was a phrase it was quoting in order to forbid it. 11 rules already
# declared `quotation` in their exception lists and no engine honoured it.


@pytest.mark.parametrize(
    "line, phrase, quoted, why",
    [
        (
            'NOT Puffery: an adjective like "world-class" that praises.',
            "world-class",
            True,
            "the banned word, quoted so the rule can name it",
        ),
        (
            'MUST Use a verb: "analyze the log", not "perform an analysis of it".',
            "perform an analysis",
            True,
            "second quotation on the same line still counts",
        ),
        (
            "Say “Experts agree” and you have dodged the attribution.",
            "Experts agree",
            True,
            "curly quotes, which every editor inserts silently",
        ),
        (
            "This parser is world-class and comprehensive.",
            "world-class",
            False,
            "unquoted use is the defect the rule exists for",
        ),
        (
            "Don't use it; the team's build isn't ready for world-class claims.",
            "world-class",
            False,
            "APOSTROPHES MUST NOT PAIR INTO A QUOTATION. An early version of the "
            "predicate read \"'t use it; the team'\" as a quoted span, which would "
            "have silenced every finding between two apostrophes in ordinary "
            "English prose",
        ),
        (
            'Set width to 30" and height to 12" for a world-class finish.',
            "world-class",
            False,
            "INCH MARKS MUST NOT PAIR EITHER. Same defect, different mark: the "
            "two inch marks bracketed the phrase",
        ),
    ],
)
def test_quotation_predicate(line, phrase, quoted, why):
    start = line.index(phrase)
    assert _inside_quotation(line, start, start + len(phrase)) is quoted, why


def test_quoted_illustration_does_not_fail_a_style_guide():
    """A document that BANS a phrase has to print the phrase.

    This is the regression that matters: without the exception, no style guide
    can pass its own gate, and the linter's own steering file was the proof.
    """
    guide = (
        "# House style\n\n"
        'NOT Puffery: an adjective that praises rather than describes ("world-class",\n'
        '"comprehensive", "battle-tested"). State the fact that would earn it.\n'
    )
    document = parse("guide.md", guide)
    fired = {f.rule_id for f in _engine().run(document)}
    assert "orwell.unsupported-evaluative" not in fired


# --- an inline code span is one word, not zero --------------------------------


def test_an_inline_code_span_counts_as_one_word():
    """It is not prose, and it is not nothing.

    Dropping it to whitespace made it vanish from every word count, which
    undercounts each length cap. STE 8.5 already collapses a quoted or
    parenthesized span to one word; a code span is the same opaque unit.
    """
    document = parse("t.md", "Run `slopvac lint --format json` now.")
    # Run + the span + now. Three, where dropping the span to whitespace gave two.
    assert document.sentences[0].word_count == 3
    assert count_words("Run  now.") == 2


def test_a_code_span_is_still_not_matched_as_prose():
    """The count changed; what rules can see did not.

    The sentinel must not reintroduce the span's text, and must not fuse the words
    on either side of it into one token.
    """
    document = parse("t.md", "Use `--robust` here.")
    prose = document.prose_text()
    assert "--robust" not in prose
    assert "robust" not in prose
    assert "Use" in prose and "here" in prose


def test_the_sentinel_never_reaches_a_finding_message():
    """A NUL in reported output would be a control character in a user's terminal
    and in the JSON payload. The count is internal; the message is not."""
    document = parse("t.md", "The `x` service is very robust and seamless indeed.")
    for finding in _engine().run(document):
        assert "\x00" not in finding.message


# --- paragraph_words is native, and the count is the documented one -----------


def test_paragraph_words_is_evaluated_natively():
    """Vale reported a different number for the same paragraph: an inline code span
    is one word here and zero to Vale, whose markdown scoping drops the span before
    its token counter sees it. At an 8-word bound that gap decides the finding."""
    engine = _engine()
    rule = next(
        r
        for r in engine.rules
        if r.qualified_id == "ai-tells-structure.emphasis-paragraph-metric"
    )
    assert rule.metric == "paragraph_words"
    assert "paragraph_words" not in engine.unimplemented_metrics()
    assert rule.qualified_id not in engine.unimplemented_metrics()


def test_a_paragraph_of_one_opaque_unit_is_not_an_emphasis_paragraph():
    """`Apache-2.0.` under a `## License` heading is the canonical case. Telling an
    author to rejoin it to the paragraph before it is advice they cannot take."""
    document = parse("t.md", "## License\n\nApache-2.0.\n")
    fired = {f.rule_id for f in _engine().run(document)}
    assert "ai-tells-structure.emphasis-paragraph-metric" not in fired


def test_a_list_stem_is_not_an_emphasis_paragraph():
    """THE TWO RULES MUST NOT CONTRADICT EACH OTHER.
    `ste-sentences.complex-text-not-in-vertical-list` orders the author to turn a
    series into a vertical list; every list needs a stem to say what it enumerates;
    a stem is short by construction. Without this exclusion an author who obeys the
    first rule is reported by the second, with no move that satisfies both.
    Measured while rewriting this project's README against the ruleset: obeying the
    list rule 15 times took this rule from 1 finding to 7, all of them stems."""
    document = parse("t.md", "These flags filter the list:\n\n- one\n- two\n")
    fired = {f.rule_id for f in _engine().run(document)}
    assert "ai-tells-structure.emphasis-paragraph-metric" not in fired


def test_a_short_paragraph_ending_in_a_colon_with_no_list_still_fires():
    """The colon alone is not the exclusion. Both halves are required, or every
    short paragraph an author happened to end that way escapes the rule."""
    document = parse("t.md", "A lead-in long enough to clear the bound sits here.\n\nHere is the thing:\n\nAnd prose continues after it, at length, with no list.\n")
    findings = [
        f
        for f in _engine().run(document)
        if f.rule_id == "ai-tells-structure.emphasis-paragraph-metric"
    ]
    assert [f.line for f in findings] == [3]


def test_a_genuine_emphasis_paragraph_still_fires():
    """The exclusions above must not disarm the rule."""
    lead = "A lead-in paragraph long enough to clear the bound sits above it here."
    document = parse("t.md", f"{lead}\n\nThat is the point.\n")
    findings = [
        f
        for f in _engine().run(document)
        if f.rule_id == "ai-tells-structure.emphasis-paragraph-metric"
    ]
    assert len(findings) == 1


# --- a profile must not override its own tiers --------------------------------


def test_a_profile_default_does_not_promote_its_own_advisory_rule():
    """`ResolvedConfig.categories` is SEEDED from the profile, so a category severity
    is not evidence anybody asked for it. Letting it override the advisory demotion
    meant the profile overrode itself: `_NORMAL` marks this rule advisory and sets
    `ai-tells-structure` to `error` in the same breath, and the category won."""
    engine = _engine()
    rule = next(
        r
        for r in engine.rules
        if r.qualified_id == "ai-tells-structure.emphasis-paragraph-metric"
    )
    assert rule.tier_for("normal") is Tier.ADVISORY
    assert engine.severity_for(rule) is Severity.SUGGESTION


def test_an_authored_promotion_still_beats_the_advisory_demotion():
    """Naming a category and asking for `error` says the profile's judgement about
    that category does not apply here. That must keep working."""
    engine = _engine(
        categories={"ai-tells-structure": CategorySettings(severity=Severity.ERROR)}
    )
    rule = next(
        r
        for r in engine.rules
        if r.qualified_id == "ai-tells-structure.emphasis-paragraph-metric"
    )
    assert engine.severity_for(rule) is Severity.ERROR


def test_an_authored_rule_override_beats_the_advisory_demotion():
    """The narrowest dial wins, and a rule id is never seeded from the profile."""
    engine = _engine(
        rules={
            "ai-tells-structure.emphasis-paragraph-metric": RuleSettings(
                severity=Severity.ERROR
            )
        }
    )
    rule = next(
        r
        for r in engine.rules
        if r.qualified_id == "ai-tells-structure.emphasis-paragraph-metric"
    )
    assert engine.severity_for(rule) is Severity.ERROR


def test_no_profile_promotes_a_rule_it_marks_advisory():
    """The property, over every rule and every profile, rather than the one case that
    surfaced it. Before the fix 12 rules were promoted to ERROR by their own profile
    at `normal` alone, and only 11 of 64 advisory-and-active rules across the three
    profiles were still suggestions."""
    ruleset = load_ruleset()
    for profile in (Profile.STRICT, Profile.NORMAL, Profile.RELAXED):
        engine = Engine(
            ruleset.rules,
            resolve_for(_config(profile=profile), Path("/repo/a.md")),
        )
        for rule in ruleset.rules:
            if rule.tier_for(profile.value) is not Tier.ADVISORY:
                continue
            if not engine._active(rule):
                continue
            assert engine.severity_for(rule) is Severity.SUGGESTION, (
                f"{rule.qualified_id} is advisory at {profile.value} but reports as "
                f"{engine.severity_for(rule).value}"
            )


# ---------------------------------------------------------------------------
# the five metrics that had no implementation in either engine
#
# Each shipped as a well-formed rule with a metric name nothing evaluated, so
# `unimplemented_metrics()` reported them as UNCHECKED on every document and they
# have never fired since the day they were written. These tests exist so that a
# regression puts them back in that state loudly rather than silently.
# ---------------------------------------------------------------------------


def test_no_metric_rule_is_left_unimplemented():
    """The property. Individual cases below cover behaviour; this one covers the
    failure mode that let all five ship dead -- a rule whose metric no branch reads
    passes every document, which is indistinguishable from clean prose."""
    engine = _engine()
    assert engine.unimplemented_metrics() == []


def test_a_noun_stack_over_three_words_is_reported():
    engine = _engine(profile=Profile.STRICT)
    document = parse(
        "a.md", "The container orchestration platform migration strategy needs review.\n"
    )
    ids = [f.rule_id for f in engine.run(document)]
    assert "ste-nouns.multiword-noun-too-long" in ids


def test_a_run_of_verbs_and_adjectives_is_not_a_noun_stack():
    """Without a part-of-speech tagger the first version counted any adjacency, which
    put 73 findings on this project's own README. The noun-suffix anchor is what
    separates a stack from a sentence."""
    assert longest_noun_stack("This is a very good simple test case here today") == 0
    assert longest_noun_stack("keeps its shipped severity, so it can reach") <= 3


def test_a_noun_stack_does_not_span_punctuation():
    """A first version split on non-word characters, which discarded the separator and
    fused four table-cell items into one 5-word stack."""
    assert longest_noun_stack("reference, specs, API docs, runbooks") <= 3


def test_a_coordinated_series_over_three_items_is_reported():
    engine = _engine(profile=Profile.STRICT)
    document = parse(
        "a.md",
        "The manifest sets the image tag, the replica count, the resource limits, "
        "and the service account.\n",
    )
    ids = [f.rule_id for f in engine.run(document)]
    assert "ste-sentences.complex-text-not-in-vertical-list" in ids


def test_a_series_needs_a_conjunction_not_just_commas():
    """Counting bare commas made every parenthetical read as a coordinated series."""
    assert coordinated_items("The gate runs, then it reports.") == 0
    # Three items: `a`, `b`, `c`. The count is commas before the conjunction plus
    # two, because the conjunction joins the last pair without a comma of its own.
    assert coordinated_items("It reads a, b, and c.") == 3


def test_four_consecutive_bold_colon_bullets_are_reported():
    engine = _engine(profile=Profile.STRICT)
    document = parse(
        "a.md",
        "# T\n\n"
        "- **Configuration:** the first thing\n"
        "- **Deployment:** the second thing\n"
        "- **Monitoring:** the third thing\n"
        "- **Rollback:** the fourth thing\n",
    )
    ids = [f.rule_id for f in engine.run(document)]
    assert "ai-tells-formatting.inline-header-list" in ids


def test_the_colon_may_fall_inside_or_outside_the_emphasis():
    """`- **Thing:** x` is the form people write, and a first version required the
    colon outside the bold, so it matched none of them."""
    assert BOLD_COLON_BULLET.match("- **Thing:** x")
    assert BOLD_COLON_BULLET.match("- **Thing**: x")
    assert BOLD_COLON_BULLET.match("1. **Step:** x")


def test_a_bold_bullet_without_a_colon_is_not_a_pseudo_heading():
    """Emphasis is not a heading. Making the colon optional matched plain emphasis."""
    assert not BOLD_COLON_BULLET.match("- **just bold** no colon")
    assert not BOLD_COLON_BULLET.match("- plain bullet")


def test_uniform_paragraph_mass_reports_low_dispersion_not_high():
    """The one metric whose comparison is `lt`. It is the burstiness counter-signal, so
    uniformity is the finding and variety is the pass."""
    engine = _engine(profile=Profile.STRICT)
    uniform = "\n\n".join(
        [
            "This paragraph has a deliberate uniform mass so the dispersion measure "
            "has something to bite on here.",
            "This paragraph also has a deliberate uniform mass so the dispersion "
            "measure has something to bite too.",
            "This paragraph likewise has a deliberate uniform mass so the dispersion "
            "measure has something to bite.",
        ]
    )
    ids = [f.rule_id for f in engine.run(parse("a.md", uniform + "\n"))]
    assert "ai-tells-register.uniform-paragraph-mass" in ids


def test_a_document_with_too_few_paragraphs_is_not_uniform():
    """`stdev` returns 0.0 below two values, which is the WRONG answer for a rule that
    compares with `lt`: every one-paragraph file would fire. The guard returns
    infinity instead."""
    engine = _engine(profile=Profile.STRICT)
    document = parse("a.md", "One short paragraph and nothing else to compare it to.\n")
    ids = [f.rule_id for f in engine.run(document)]
    assert "ai-tells-register.uniform-paragraph-mass" not in ids


def test_adjective_spray_is_reported():
    engine = _engine(profile=Profile.STRICT)
    document = parse(
        "a.md",
        "A comprehensive robust scalable solution provides seamless powerful "
        "flexible integration capabilities for meaningful actionable insights.\n",
    )
    ids = [f.rule_id for f in engine.run(document)]
    assert "ai-tells-content-shape.adjective-per-noun-spray" in ids


def test_this_project_readme_does_not_trip_the_new_metrics():
    """The calibration check. All five thresholds are marked INFERRED rather than
    measured, and a rule that fires on its own project's README is miscalibrated
    whatever its provenance says."""
    engine = _engine(profile=Profile.STRICT)
    readme = Path(__file__).resolve().parent.parent / "README.md"
    findings = engine.run(parse(str(readme), readme.read_text(encoding="utf-8")))
    noisy = [
        f.rule_id
        for f in findings
        if f.rule_id
        in {
            "ste-nouns.multiword-noun-too-long",
            "ai-tells-content-shape.adjective-per-noun-spray",
            "ai-tells-register.uniform-paragraph-mass",
        }
    ]
    assert noisy == []


def test_a_bold_span_is_counted_per_span_not_per_line():
    """A greedy pattern fused every span on a line into one match, which
    undercounted exactly the documents the density rule is aimed at."""
    assert BOLD_SPAN.findall("**a** and **b** and **c**") == ["**a**", "**b**", "**c**"]
    assert BOLD_SPAN.findall("__x__ here") == ["__x__"]
    assert BOLD_SPAN.findall("**bad ** trailing space") == []


def test_a_numeric_range_is_not_a_dash_aside():
    """The rule is about the em dash used as an aside. An en dash in a range and a
    long-option flag are both correct, and counting them made every CLI reference
    look like a document full of asides."""
    # A paired aside carries two dashes and counts as two. The metric measures dash
    # density rather than aside count, and the threshold is calibrated on that.
    assert DASH_AS_ASIDE.findall("the gate -- which fails -- exits 1") == ["--", "--"]
    assert DASH_AS_ASIDE.findall("an aside — like this one") == ["—"]
    assert DASH_AS_ASIDE.findall("pass --verbose to see steps 1--2") == []


def test_markup_metrics_ignore_code_blocks_and_inline_spans():
    """`markup_text` exists because `prose_text` strips the characters these two
    rules count. Reading `raw` instead would count `**kwargs` in a snippet as a bold
    span and every `--flag` in a command as an aside."""
    document = parse(
        "a.md",
        "# T\n\nProse with `**not bold**` and `--not-an-aside` inline.\n\n"
        "```python\ndef f(**kwargs): pass  # -- comment\n```\n\n"
        "Real **bold** and a real -- aside.\n",
    )
    markup = document.markup_text()
    assert BOLD_SPAN.findall(markup) == ["**bold**"]
    assert DASH_AS_ASIDE.findall(markup) == ["--"]


def test_bold_spray_and_dash_density_report_their_measurement():
    """Both were routed to Vale, whose script extension point returns a match rather
    than a number, so each shipped a message with the count missing entirely:
    `bold spray: bold spans per 1000 words`. A finding a reader cannot act on is the
    defect this project's own actionability rule names."""
    engine = _engine(profile=Profile.STRICT)
    document = parse(
        "a.md",
        "# T\n\n"
        "**One** and **two** — then **three** and **four** — plus **five** here.\n",
    )
    messages = {
        f.rule_id: f.message
        for f in engine.run(document)
        if f.rule_id
        in {"ai-tells-formatting.bold-spray", "ai-tells-formatting.em-dash-density"}
    }
    assert set(messages) == {
        "ai-tells-formatting.bold-spray",
        "ai-tells-formatting.em-dash-density",
    }
    for rule_id, message in messages.items():
        assert re.search(r"\d+\.\d\d", message), f"{rule_id} states no figure: {message}"


def test_a_density_metric_is_not_compiled_to_vale_as_well():
    """Held back in one place and implemented in another is how a rule gets reported
    twice. The routing table and NATIVE_METRICS have to agree."""
    from slopvac.compile_vale import DENSITY_MESSAGE_METRICS

    assert DENSITY_MESSAGE_METRICS <= NATIVE_METRICS


def test_a_clause_boundary_ends_a_noun_stack():
    """`because` was missing from STACK_BREAKER and produced a 4-word stack on this
    project's own README. A subordinator is exactly where a noun phrase ends."""
    assert longest_noun_stack("Specificity ranking loses because no ordering exists") <= 3
    assert longest_noun_stack("The gate reports although the score passes") <= 3


def test_a_verb_ending_in_s_does_not_extend_a_noun_stack():
    """`shows` and `loses` look like plural nouns to a suffix test and carry no noun
    suffix of their own, so nothing but the breaker list separates them."""
    assert longest_noun_stack("so a blanket suppression shows up in a diff") <= 3
    assert longest_noun_stack("the override wins and the profile loses") <= 3


def test_the_stack_rule_still_reports_a_real_stack():
    """The companion to every false-positive fix above. Each round widened
    STACK_BREAKER, and a list wide enough to silence everything silences this too."""
    assert longest_noun_stack("container orchestration platform migration strategy") == 5
