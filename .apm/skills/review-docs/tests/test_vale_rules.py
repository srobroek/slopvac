"""Behavioural tests for the published Vale styles and the slop-lint entrypoint.

Replaces test_slop_lint.py. Vale has no rule-test framework, so these drive the
real binary over fixtures and assert on rule names and the exit contract.

Skipped when `vale` is absent so a checkout without it still collects.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
ENTRY = SKILL / "scripts" / "slop-lint.sh"
CONFIG = SKILL / "vale" / ".vale.ini"
FIXTURES = Path(__file__).parent / "fixtures"

pytestmark = pytest.mark.skipif(
    shutil.which("vale") is None or not (SKILL / "vale" / "styles" / "ai-tells").is_dir(),
    reason="vale not installed, or packaged styles not synced (`vale sync`)",
)


def rules(*paths: Path) -> dict[str, int]:
    """Rule name -> hit count for the given fixtures."""
    proc = subprocess.run(
        ["vale", f"--config={CONFIG}", "--output=JSON", "--no-exit", *map(str, paths)],
        capture_output=True,
        text=True,
        check=False,
    )
    counts: dict[str, int] = {}
    for alerts in json.loads(proc.stdout or "{}").values():
        for alert in alerts:
            counts[alert["Check"]] = counts.get(alert["Check"], 0) + 1
    return counts


def run_entry(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(ENTRY), *args], capture_output=True, text=True, check=False
    )


# --- E1 status language ------------------------------------------------------


def test_status_language_fires_and_respects_the_lookahead():
    # "currently running" is runtime state, not doc status: the negative
    # lookahead ported from slop-lint.py:32 must still exclude it.
    found = rules(FIXTURES / "e1-status.md")
    assert found.get("docs-discipline.StatusLanguage") == 3


# --- E5 chat-session leakage -------------------------------------------------


def test_chat_leakage_catches_disclaimers_and_artifacts():
    found = rules(FIXTURES / "e5-leakage.md")
    assert found.get("ai-residue.ChatLeakage", 0) >= 3


# --- W1 prose block ----------------------------------------------------------


def test_long_prose_block_warns():
    assert rules(FIXTURES / "w1-long.md").get("prose-format.ProseBlock") == 1


def test_prose_block_ignores_lists_and_tables():
    """The old line-prefix heuristic counted wrapped list continuations and
    table rows as prose. Vale's paragraph scope does not."""
    assert "prose-format.ProseBlock" not in rules(FIXTURES / "w1-prose.md")


# --- Code and structure exclusions ------------------------------------------


def test_inline_code_and_fences_are_not_scanned(tmp_path):
    doc = tmp_path / "code.md"
    doc.write_text(
        "Run `apm compile --no-constitution` to skip it.\n\n"
        "```\nA powerful robust WIP tool.\n```\n",
        encoding="utf-8",
    )
    found = rules(doc)
    assert "prose-inflation.SlopLexicon" not in found
    assert "docs-discipline.StatusLanguage" not in found
    assert "docs-discipline.InternalRefs" not in found


def test_unicode_dash_is_banned_but_double_hyphen_is_not(tmp_path):
    doc = tmp_path / "dash.md"
    doc.write_text("An em dash — here.\n\nDouble hyphens -- are fine.\n", encoding="utf-8")
    assert rules(doc).get("prose-format.NoUnicodeDash") == 1


# --- Genre routing -----------------------------------------------------------


def test_internal_refs_off_under_specs(tmp_path, monkeypatch):
    specs = tmp_path / "specs" / "001"
    specs.mkdir(parents=True)
    doc = specs / "spec.md"
    doc.write_text("Per the spec, see ADR-7 for the constitution.\n", encoding="utf-8")
    # Section globs match the path Vale is given, so run from tmp_path.
    monkeypatch.chdir(tmp_path)
    proc = subprocess.run(
        ["vale", f"--config={CONFIG}", "--output=JSON", "--no-exit", "specs/001/spec.md"],
        capture_output=True,
        text=True,
        check=False,
    )
    checks = {
        a["Check"] for alerts in json.loads(proc.stdout or "{}").values() for a in alerts
    }
    assert "docs-discipline.InternalRefs" not in checks


# --- Entrypoint exit contract ------------------------------------------------


def test_exit_zero_when_clean():
    assert run_entry(str(FIXTURES / "clean.md")).returncode == 0


def test_exit_one_on_error():
    assert run_entry(str(FIXTURES / "e1-status.md")).returncode == 1


def test_warnings_alone_still_exit_zero(tmp_path):
    doc = tmp_path / "warn.md"
    doc.write_text("It simply works.\n", encoding="utf-8")
    proc = run_entry(str(doc))
    assert "WARNING" in proc.stdout
    assert proc.returncode == 0


def test_usage_errors_exit_two():
    assert run_entry().returncode == 2
    assert run_entry("--genre", "bogus", str(FIXTURES / "clean.md")).returncode == 2


# --- Harvested register rules ------------------------------------------------
#
# One case per rule, plus the negative that shaped the pattern. The negatives
# matter more than the positives: each is prose this repo actually writes, and a
# rule that flags it would be reverted.


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ("The complaint becomes a fix.", "prose-agency.FalseAgency"),
        ("The data tells us the market rewards speed.", "prose-agency.FalseAgency"),
        ("The decision emerges from review.", "prose-agency.FalseAgency"),
        (
            "The abstraction stops being a helper and starts being a framework.",
            "prose-agency.FalseAgency",
        ),
        ("It is believed that the cache is warm.", "prose-agency.AgentlessPassive"),
        ("Mistakes were made during the migration.", "prose-agency.AgentlessPassive"),
        ("The decision was reached last week.", "prose-agency.AgentlessPassive"),
        ("People tend to forget the timeout.", "prose-agency.NarratorDistance"),
        ("Nobody designed this.", "prose-agency.NarratorDistance"),
        ("Look, the answer is a bigger buffer.", "prose-agency.NarratorDistance"),
        ("We should double down on caching.", "prose-inflation.BusinessJargon"),
        ("Let us circle back to the loader.", "prose-inflation.BusinessJargon"),
        ("Moving forward, the parser accepts UTF-8.", "prose-inflation.BusinessJargon"),
        ("The reasons are structural.", "prose-inflation.VagueDeclarative"),
        (
            "The implications are significant for callers.",
            "prose-inflation.VagueDeclarative",
        ),
        ("The feature is not just fast but also safe.", "prose-inflation.AdditiveHedge"),
    ],
)
def test_harvested_rule_fires(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule in rules(doc), f"{rule} did not fire on: {text}"


@pytest.mark.parametrize(
    "text",
    [
        # A passive that names its agent keeps the actor in view.
        "The record was created by the importer.",
        # State description, not a deleted actor. Spec and rule prose needs it.
        "Internal references are allowed in this genre.",
        "The rule is disabled in the shipped config.",
        "The branch being merged carries the fix.",
        # A predicate that continues into a specific is not a vague declarative.
        "The implications are documented in the ADR.",
        # Real subjects doing real things.
        "The loader resolves paths at startup.",
        "The team fixed the regression that week.",
        # Domain use of a banned-band verb.
        "The report tells a clear story about the collected data.",
    ],
)
def test_harvested_rules_stay_quiet_on_correct_prose(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    harvested = {
        "prose-agency.FalseAgency",
        "prose-agency.AgentlessPassive",
        "prose-agency.NarratorDistance",
        "prose-inflation.BusinessJargon",
        "prose-inflation.VagueDeclarative",
        "prose-inflation.AdditiveHedge",
    }
    fired = harvested & set(rules(doc))
    assert not fired, f"{fired} fired on correct prose: {text}"


# --- Multi-format coverage ---------------------------------------------------


@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("copy.html", "<h1>Our seamless platform</h1>\n"),
        ("en.json", '{"hero": {"title": "Our seamless platform"}}\n'),
        ("en.yaml", "hero:\n  title: Our seamless platform\n"),
        ("page.mdx", "import X from './x'\n\n# Our seamless platform\n"),
    ],
)
def test_markup_formats_are_linted(tmp_path, name, body):
    # An extension with no parser and no [formats] alias lints as NOTHING and
    # exits 0, which reads as a pass. Each format needs a fixture proving it
    # produces findings.
    doc = tmp_path / name
    doc.write_text(body, encoding="utf-8")
    assert "prose-inflation.SlopLexicon" in rules(doc), f"{name} produced no findings"


def test_source_comments_are_linted_but_identifiers_are_not(tmp_path):
    doc = tmp_path / "loader.go"
    doc.write_text(
        "package main\n"
        "\n"
        "// Loader is a seamless cache.\n"
        "type Loader struct{ comprehensive bool }\n"
        "\n"
        'var Msg = "robust string"\n',
        encoding="utf-8",
    )
    found = rules(doc)
    # The comment is prose and is flagged; the field name and the string literal
    # are code and are not. Vale's own syntax awareness draws that line.
    assert found.get("prose-inflation.SlopLexicon") == 1


def test_source_files_use_the_reduced_ruleset(tmp_path):
    doc = tmp_path / "notes.sh"
    doc.write_text(
        "#!/usr/bin/env bash\n"
        "# A test named: No PCRE, no lookbehind -- terse comment register.\n",
        encoding="utf-8",
    )
    found = set(rules(doc))
    # Structural and punctuation-frequency rules are excluded for source files:
    # terse comments are legitimately negative and dash-heavy.
    assert "ai-tells.ContrastiveNegation" not in found
    assert "prose-format.NoUnicodeDash" not in found


# --- Unicode dashes reach into code -----------------------------------------


def test_unicode_dash_is_caught_in_code_as_well_as_prose(tmp_path):
    # `scope: raw` on the rule. Vale's default scope skips code, which is where a
    # pasted Unicode dash is most harmful: invisible in review, and it breaks the
    # command or identifier it lands in. One dash in each of the four positions.
    doc = tmp_path / "dash.md"
    doc.write_text(
        "Body prose with an em dash — here.\n"
        "\n"
        "```sh\n"
        'echo "fenced — dash"\n'
        "```\n"
        "\n"
        "    indented code — dash\n"
        "\n"
        "Inline `code — dash` here.\n",
        encoding="utf-8",
    )
    assert rules(doc).get("prose-format.NoUnicodeDash") == 4


def test_source_files_are_gated_on_unicode_dashes(tmp_path):
    doc = tmp_path / "guard.sh"
    doc.write_text(
        "#!/usr/bin/env bash\n"
        "# A comment with an em dash — here.\n"
        "# A flag written the house way -- stays clean.\n",
        encoding="utf-8",
    )
    found = rules(doc)
    assert found.get("prose-format.NoUnicodeDash") == 1, "one Unicode dash, not the `--`"


# --- Over-writing (prose-scope) ----------------------------------------------


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (
            "It reports findings rather than asking the agent, because a hook cannot.",
            "prose-scope.RejectedAlternative",
        ),
        ("For the same reason it does not run detached.", "prose-scope.RejectedAlternative"),
        ("We chose Python for the hook.", "prose-scope.RejectedAlternative"),
        (
            "The earlier implementation spawned a shell for every check.",
            "prose-scope.RejectedAlternative",
        ),
        ("It deliberately does not cache the result.", "prose-scope.RejectedAlternative"),
        ("A shell version cost 212ms per edit.", "prose-scope.ImplementationLeak"),
        ("The check is 4x faster than the shell version.", "prose-scope.ImplementationLeak"),
        ("An ordinary edit costs one Python startup.", "prose-scope.ImplementationLeak"),
        ("The parser makes three subprocess calls.", "prose-scope.ImplementationLeak"),
    ],
)
def test_over_writing_fires(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule in rules(doc), f"{rule} did not fire on: {text}"


@pytest.mark.parametrize(
    "text",
    [
        # Ordinary substitution, with no rejected alternative behind it.
        "Run the wrapper instead of the raw binary.",
        "Use a table rather than a list when the data has columns.",
        # A changelog states the delta; that is the genre's job.
        "Removed the legacy flag in favor of the config key.",
        # Actionable configuration and limits, not benchmark prose.
        "The default timeout is 30 seconds.",
        "Set the port to 8080 in the config.",
        "At most five subprocesses run concurrently.",
        "Requires Python 3.14 or newer.",
    ],
)
def test_over_writing_stays_quiet(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    fired = {"prose-scope.RejectedAlternative", "prose-scope.ImplementationLeak"} & set(rules(doc))
    assert not fired, f"{fired} fired on acceptable prose: {text}"


def test_over_writing_is_off_for_decision_records(tmp_path, monkeypatch):
    # An ADR exists to record the decision and its measurement.
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    doc = adr / "0001-hook-language.md"
    doc.write_text(
        "We chose Python because the shell version cost 212ms per edit.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    proc = subprocess.run(
        ["vale", f"--config={CONFIG}", "--output=JSON", "--no-exit",
         "docs/adr/0001-hook-language.md"],
        capture_output=True, text=True, check=False,
    )
    checks = {a["Check"] for alerts in json.loads(proc.stdout or "{}").values() for a in alerts}
    assert "prose-scope.RejectedAlternative" not in checks
    assert "prose-scope.ImplementationLeak" not in checks


@pytest.mark.parametrize(
    "text",
    [
        # A duration that names configuration the reader sets or relies on.
        "A timeout of 50 ms applies to each call.",
        "The adapter gives the daemon 50 ms before falling back.",
        "Retries happen every 200 ms.",
        "The request must complete within 30 ms.",
    ],
)
def test_configured_durations_are_not_implementation_leaks(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-scope.ImplementationLeak" not in rules(doc), text


def test_published_figures_in_tables_and_lists_are_not_leaks(tmp_path):
    # `scope: paragraph`. A benchmarks page publishing figures as structured data
    # is a deliverable; the rule is for a timing asserted mid-sentence.
    doc = tmp_path / "benchmarks.md"
    doc.write_text(
        "| Step | Cost |\n|---|---|\n| Rule evaluation | 2.5 ms |\n"
        "\n- Wall clock per hook: 90 ms\n",
        encoding="utf-8",
    )
    assert "prose-scope.ImplementationLeak" not in rules(doc)

    prose = tmp_path / "readme.md"
    prose.write_text("The parser takes 212 ms per call.\n", encoding="utf-8")
    assert "prose-scope.ImplementationLeak" in rules(prose)


@pytest.mark.parametrize(
    "text",
    [
        "Nothing here needs a package manager.",
        "The skills work as soon as they are on disk.",
        "uvx leaves nothing behind.",
        "No configuration required.",
        "It just works, out of the box.",
        "You do not have to install anything.",
        "Don't worry, rest assured this is safe.",
    ],
)
def test_unrequested_reassurance_fires(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-scope.UnrequestedReassurance" in rules(doc), text


@pytest.mark.parametrize(
    "text",
    [
        # Factual scope notes, not reassurance. Narrowing to the setup/config band
        # cut these from 16 to 3 on an external corpus.
        "No signing needed for this path.",
        "No spec change needed.",
        "Nothing is committed under styles; a sync fetches it.",
        # An instruction the reader must act on.
        "You need vale on PATH before the first run.",
        "The parser requires Python 3.14 or newer.",
        "No files were changed.",
    ],
)
def test_unrequested_reassurance_stays_quiet(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-scope.UnrequestedReassurance" not in rules(doc), text


@pytest.mark.parametrize(
    "text",
    [
        "The gate finds tokens. The catalog finds voice.",
        "The linter is deterministic. The reviewer is not.",
        "The agent runs the pass; the scripts are its tools, not yours.",
    ],
)
def test_epigram_fires(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-scope.Epigram" in rules(doc), text


@pytest.mark.parametrize(
    "text",
    [
        # Two sentences about different things, with no mirrored shape.
        "The parser rejects malformed input. Callers see a 400 with the field named.",
        # A real contrast that names the alternative.
        "Run the wrapper instead of the raw binary, not the other script there.",
        # Ordinary reporting.
        "The gate reports six findings across two files, all in the install section.",
        "The cache stores 4,096 entries and evicts by least-recent use.",
    ],
)
def test_epigram_stays_quiet(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-scope.Epigram" not in rules(doc), text


# --- prose-craft: writing craft, warning level -------------------------------
# These fire on prose a human wrote badly, not on generated prose, so each case
# pairs a positive with the near-miss that must stay clean. The near-misses are
# where a craft rule earns or loses its place: a rule that flags correct prose
# gets the whole style switched off.


@pytest.mark.parametrize(
    "text,rule",
    [
        ("There is a flag that controls retries.", "prose-craft.DeadOpener"),
        ("It is important to note that the loader caches.", "prose-craft.DeadOpener"),
        ("In order to configure it, edit the file.", "prose-craft.Wordiness"),
        ("The parser utilizes a lookahead.", "prose-craft.Wordiness"),
        ("Open a HTML file.", "prose-craft.Articles"),
        ("Fetch an URL.", "prose-craft.Articles"),
        ("Three API's are exposed.", "prose-craft.PluralAbbreviation"),
        ("See the table above for the list.", "prose-craft.DirectionalRef"),
        ("This section explains the loader.", "prose-craft.SelfReference"),
        ("Select the file(s) you want.", "prose-craft.OptionalPlural"),
        ("A newly-added flag controls this.", "prose-craft.Hyphens"),
        ("The ATM machine failed.", "prose-craft.Misnomer"),
        ("The output is generally always correct.", "prose-craft.Redundancy"),
        ("Firstly, install the binary.", "prose-craft.Ordinals"),
        ("Read the A.P.I. reference.", "prose-craft.AcronymPeriods"),
        ("Requires version 3 and higher.", "prose-craft.Versions"),
        ("You cannot deploy without a token.", "prose-craft.NegativeRequirement"),
        ("TODO: document the flag.", "prose-craft.Annotations"),
        ("The loader was rewritten recently.", "prose-craft.RelativeDate"),
        ("The gate will reject the file.", "prose-craft.FutureTense"),
        ("Use the flag, e.g. --json, to change the output.", "prose-craft.Latinisms"),
        ("This is why the sync fails.", "prose-craft.UnclearAntecedent"),
        ("The script performs validation of the token.",
         "prose-inflation.NominalizedVerb"),
        ("Our tool reads one config file.", "prose-craft.FirstPersonPlural"),
    ],
)
def test_craft_rules_fire(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule in rules(doc), text


@pytest.mark.parametrize(
    "text,rule",
    [
        # Existential "there" mid-sentence is not a dead opener.
        ("Check whether there is a lockfile before syncing.", "prose-craft.DeadOpener"),
        # A possessive apostrophe on an initialism is correct.
        ("The API's rate limit is 60 per minute.", "prose-craft.PluralAbbreviation"),
        # A demonstrative WITH its noun names its own antecedent.
        ("This flag controls retries.", "prose-craft.UnclearAntecedent"),
        # A real noun phrase, not a light-verb construction.
        ("The validation step runs after parsing.", "prose-craft.NominalizedVerb"),
        # `master boot record` and `master branch` are fixed technical terms; the
        # negative lookaheads in prose-inclusive.Exclusive exist for exactly this.
        ("Write the master boot record first.", "prose-inclusive.Exclusive"),
        ("Merge into the master branch.", "prose-inclusive.Exclusive"),
        # A config state, not a person. Microsoft's rule flags this; ours must not.
        ("The rule is disabled for generated files.", "prose-inclusive.Ableist"),
        # A click event is a noun, not an instruction.
        ("The handler fires on a click event.", "prose-inclusive.DeviceAssumption"),
        # Directional words with no cross-reference sense.
        ("Left-shift the value by two bits.", "prose-craft.DirectionalRef"),
        # An -ly adverb NOT hyphenated.
        ("A newly added flag controls this.", "prose-craft.Hyphens"),
        # Bare gerund headings are topics, not tasks.
        ("## Logging\n\nText.", "prose-craft.GerundHeading"),
        ("## Troubleshooting\n\nText.", "prose-craft.GerundHeading"),
        # An SPDX identifier is not an initialism awaiting expansion.
        ("Licensed under MIT and Apache-2.0.", "prose-craft.UndefinedAcronym"),
        # Directive vocabulary in agent-facing prose.
        ("MUST name who acted. NOT status language.", "prose-craft.UndefinedAcronym"),
    ],
)
def test_craft_rules_stay_quiet(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule not in rules(doc), text


def test_gerund_heading_fires_on_a_task_heading(tmp_path):
    doc = tmp_path / "case.md"
    doc.write_text("## Installing the plugin\n\nText.\n", encoding="utf-8")
    assert "prose-craft.GerundHeading" in rules(doc)


def test_sentence_length_threshold(tmp_path):
    """34 words, measured: Microsoft's 30 and Red Hat's 32 both flagged correct
    enumerations in this repo's prose."""
    doc = tmp_path / "case.md"
    short = " ".join(["word"] * 30) + ".\n"
    long = " ".join(["word"] * 40) + ".\n"
    doc.write_text(short, encoding="utf-8")
    assert "prose-craft.SentenceLength" not in rules(doc)
    doc.write_text(long, encoding="utf-8")
    assert "prose-craft.SentenceLength" in rules(doc)


def test_conflict_markers_are_caught_inside_code_fences(tmp_path):
    """`scope: raw`, because a botched merge usually lands inside a fence."""
    doc = tmp_path / "case.md"
    doc.write_text("```\n<<<<<<< HEAD\nx = 1\n>>>>>>> other\n```\n", encoding="utf-8")
    assert rules(doc).get("prose-craft.ConflictMarkers", 0) >= 2


# --- prose-inflation: the harvested slop-axis additions ----------------------


@pytest.mark.parametrize(
    "text,rule",
    [
        ("The design is very unique.", "prose-inflation.Uncomparables"),
        ("A more complete rewrite landed.", "prose-inflation.Uncomparables"),
        ("The parser is very fast.", "prose-inflation.Intensifier"),
        ("Several options control this.", "prose-inflation.VagueQuantifier"),
        ("The loader usually retries.", "prose-inflation.VagueQuantifier"),
        ("More research is needed here.", "prose-inflation.Apologizing"),
        ("This may help to potentially reduce latency.", "prose-inflation.HedgeStack"),
        ("Obviously the flag is required.", "prose-inflation.BorderlineHype"),
        ("We productized the north star.", "prose-inflation.BusinessJargon"),
        ("The team hit the ground running.", "prose-inflation.BusinessJargon"),
        ("The tool allows you to filter.", "prose-agency.FalseAgency"),
    ],
)
def test_harvested_inflation_rules_fire(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule in rules(doc), text


@pytest.mark.parametrize(
    "text,rule",
    [
        # A single hedge is often the correct, true statement.
        ("The loader may retry once.", "prose-inflation.HedgeStack"),
        # Load-bearing next to a figure, so deliberately not in the token list.
        ("The parser is significantly faster: 12 ms against 84 ms.",
         "prose-inflation.Intensifier"),
        # A real capability with a real object, not a grant of permission.
        ("The config allows two retries.", "prose-agency.FalseAgency"),
        # An exact quantity.
        ("All three styles sync from one tag.", "prose-inflation.VagueQuantifier"),
        # `greenfield` names a real project condition; it is not vision vocabulary.
        ("Greenfield repos have no history to narrate.",
         "prose-inflation.BusinessJargon"),
    ],
)
def test_harvested_inflation_rules_stay_quiet(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule not in rules(doc), text


# --- prose-density -----------------------------------------------------------


def test_density_flags_nominalised_prose_and_not_plain_prose(tmp_path):
    """Reading ease under 30. The threshold is measured against this repo: the
    READMEs score 64-70 and the reference material 41-53, so 30 reaches only prose
    that has stopped being long and started being nested."""
    doc = tmp_path / "case.md"
    doc.write_text(
        "The utilization of the aforementioned methodology facilitates the "
        "optimization of operational efficiency in a manner that is both effective "
        "and efficacious, thereby enabling the achievement of desired outcomes "
        "within the requisite timeframe.\n",
        encoding="utf-8",
    )
    assert "prose-density.Overwritten" in rules(doc)

    doc.write_text(
        "The loader reads one file. It retries twice, then fails. "
        "Each retry waits one second.\n",
        encoding="utf-8",
    )
    assert "prose-density.Overwritten" not in rules(doc)


# --- Genre routing for the craft rules ---------------------------------------


def test_first_person_plural_is_off_for_decision_records(tmp_path, monkeypatch):
    """An ADR records what WE decided; that is the document's job. Same inversion
    the over-writing rules already get for these paths."""
    adr = tmp_path / "docs" / "adr"
    adr.mkdir(parents=True)
    doc = adr / "0001-choose-vale.md"
    doc.write_text("We chose Vale over a bespoke linter.\n", encoding="utf-8")
    assert "prose-craft.FirstPersonPlural" not in rules(doc)

    consumer = tmp_path / "README.md"
    consumer.write_text("We chose Vale over a bespoke linter.\n", encoding="utf-8")
    assert "prose-craft.FirstPersonPlural" in rules(consumer)


def test_negative_requirement_is_off_for_specs(tmp_path):
    spec = tmp_path / "specs"
    spec.mkdir()
    doc = spec / "loader.md"
    doc.write_text("The loader cannot start without a config.\n", encoding="utf-8")
    assert "prose-craft.NegativeRequirement" not in rules(doc)


# --- Late additions from the topic-page survey --------------------------------
# Openly's Anthropomorphism and Link, the two rules the first pass over
# github.com/topics/vale-linter-style missed.


@pytest.mark.parametrize(
    "text",
    [
        "The parser knows the schema.",
        "The linter thinks it failed.",
        "The gate decides which rules apply.",
        "The agent wants a config file.",
    ],
)
def test_anthropomorphism_fires(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-agency.Anthropomorphism" in rules(doc), text


@pytest.mark.parametrize(
    "text",
    [
        # A person is allowed a mind. The rule is subject-anchored for this reason.
        "The reviewer knows the schema.",
        "The maintainer decided to drop the flag.",
        # Ordinary correct English about a program.
        "The loader behaves the same way on Windows.",
        "The parser requires a schema.",
        "The gate reports six findings.",
    ],
)
def test_anthropomorphism_stays_quiet(tmp_path, text):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert "prose-agency.Anthropomorphism" not in rules(doc), text


def test_link_text_fires_on_empty_labels_and_not_on_named_ones(tmp_path):
    doc = tmp_path / "case.md"
    doc.write_text(
        "See [here](https://example.com) and [click here](https://example.com).\n",
        encoding="utf-8",
    )
    assert rules(doc).get("prose-craft.LinkText") == 2

    doc.write_text("Read the [Vale docs](https://vale.sh) for detail.\n", encoding="utf-8")
    assert "prose-craft.LinkText" not in rules(doc)


# --- Second survey pass: the remaining 28 vale-linter-style repos --------------
# The first pass covered 8 of the 36 repos on the topic page. These rules come
# from the other 28, deduplicated by pattern payload rather than by rule name.


@pytest.mark.parametrize(
    "text,rule",
    [
        ("It is recommended that you rotate keys.",
         "prose-agency.UnattributedRecommendation"),
        ("Rotation is recommended.", "prose-agency.UnattributedRecommendation"),
        ("Set the flag and/or the env var.", "prose-craft.Ambiguity"),
        ("The job runs bi-weekly.", "prose-craft.Ambiguity"),
        ("Please run the migration.", "prose-craft.Politeness"),
        ("Unfortunately the sync fails.", "prose-craft.Politeness"),
        ("This document describes the loader.", "prose-inflation.DocumentPreamble"),
        ("The purpose of this guide is to explain the gate.",
         "prose-inflation.DocumentPreamble"),
        ("See [read more](https://example.com).", "prose-craft.LinkText"),
    ],
)
def test_second_survey_rules_fire(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule in rules(doc), text


@pytest.mark.parametrize(
    "text,rule",
    [
        # An attributed recommendation is exactly the fix the rule asks for.
        ("The maintainers recommend rotating keys.",
         "prose-agency.UnattributedRecommendation"),
        ("Rotate keys every 90 days.", "prose-agency.UnattributedRecommendation"),
        # `run` and `make` are real verbs with real objects, not light verbs. An
        # earlier revision flagged both and had to be narrowed.
        ("Run the migration before deploying.", "prose-inflation.NominalizedVerb"),
        ("Make a backup first.", "prose-inflation.NominalizedVerb"),
        ("Do the comparison by hand.", "prose-inflation.NominalizedVerb"),
        # A weekly schedule is unambiguous; only bi-weekly is not.
        ("The job runs weekly.", "prose-craft.Ambiguity"),
        # Not a trailing preposition: the sentence has its object.
        ("Read the config from disk.", "prose-craft.Ambiguity"),
        # A named link.
        ("Read the [Vale docs](https://vale.sh).", "prose-craft.LinkText"),
    ],
)
def test_second_survey_rules_stay_quiet(tmp_path, text, rule):
    doc = tmp_path / "case.md"
    doc.write_text(text + "\n", encoding="utf-8")
    assert rule not in rules(doc), text


def test_command_prompt_is_caught_inside_a_fence(tmp_path):
    """`scope: raw`: a pasted prompt lives inside a code fence, which the prose
    parser skips entirely."""
    doc = tmp_path / "case.md"
    doc.write_text("```sh\n$ npm install\nnpm test\n```\n", encoding="utf-8")
    assert rules(doc).get("prose-craft.CommandPrompt") == 1


def test_self_reference_does_not_double_report_a_link_label(tmp_path):
    """Vale's `text` scope strips the brackets, so `[this page](...)` reaches the
    rule as bare prose. LinkText owns that case; SelfReference must not also claim
    it, which is why `page` is absent from its noun list."""
    doc = tmp_path / "case.md"
    doc.write_text("See [this page](https://example.com).\n", encoding="utf-8")
    found = rules(doc)
    assert "prose-craft.LinkText" in found
    assert "prose-craft.SelfReference" not in found
    # The prose case still fires.
    doc.write_text("This section explains the loader.\n", encoding="utf-8")
    assert "prose-craft.SelfReference" in rules(doc)


# --- Axis placement, decided by measured base rate ----------------------------
# A rule belongs on the slop axis when a match is evidence about how the text was
# produced. That is an empirical claim, so it was measured: each rule was run over
# 147,473 words of human-written technical documentation (the upstream Vale style
# repos) and compared against the median rate of the rules already accepted as
# provenance evidence, 0.8 hits per 10k words.


def test_promoted_rules_error_on_the_slop_axis(tmp_path):
    """DocumentPreamble (0.7 per 10k human) and NominalizedVerb (0.9) sit at or
    below the slop-axis median, so both gate at error."""
    doc = tmp_path / "case.md"
    doc.write_text(
        "This document describes the loader.\n\n"
        "The script performs validation of the token.\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["vale", f"--config={CONFIG}", "--output=JSON", "--no-exit", str(doc)],
        capture_output=True, text=True, check=False,
    )
    levels = {
        a["Check"]: a["Severity"]
        for alerts in json.loads(proc.stdout or "{}").values()
        for a in alerts
    }
    assert levels.get("prose-inflation.DocumentPreamble") == "error"
    assert levels.get("prose-inflation.NominalizedVerb") == "error"


def test_vague_quantifier_warns_despite_living_in_prose_inflation(tmp_path):
    """9.9 hits per 10k on human prose -- the highest of any slop-axis rule, and 12x
    the median. It keeps its home in prose-inflation because the defect IS inflation,
    but the level carries the epistemic weight and it must not gate."""
    doc = tmp_path / "case.md"
    doc.write_text("Several options control this.\n", encoding="utf-8")
    proc = subprocess.run(
        ["vale", f"--config={CONFIG}", "--output=JSON", "--no-exit", str(doc)],
        capture_output=True, text=True, check=False,
    )
    levels = {
        a["Check"]: a["Severity"]
        for alerts in json.loads(proc.stdout or "{}").values()
        for a in alerts
    }
    assert levels.get("prose-inflation.VagueQuantifier") == "warning"


def test_redundancy_and_misnomer_are_separate_rules(tmp_path):
    """Grammatical redundancy and RAS syndrome have different causes, so they report
    under different names: 'past history' is a slip in the sentence, 'ATM machine' is
    a gap in what the writer knows the initialism expands to."""
    doc = tmp_path / "case.md"
    doc.write_text("The past history is here.\n", encoding="utf-8")
    found = rules(doc)
    assert "prose-craft.Redundancy" in found
    assert "prose-craft.Misnomer" not in found

    doc.write_text("The ATM machine failed.\n", encoding="utf-8")
    found = rules(doc)
    assert "prose-craft.Misnomer" in found
    assert "prose-craft.Redundancy" not in found


def test_density_rules_are_the_published_metrics(tmp_path):
    """RIX (Anderson 1983) for density, average sentence length for load.

    A doc of long TECHNICAL nouns in SHORT sentences must stay clean -- that is the
    case every syllable-based metric gets wrong, and the reason Flesch was dropped:
    the paragraph below scores Flesch-Kincaid 19.5 at 3.5 words per sentence."""
    doc = tmp_path / "case.md"
    doc.write_text(
        "Initialization happens asynchronously. The orchestration layer waits. "
        "Configuration parameters live in the environment. The deployment manifest "
        "lists dependencies. Serialization uses the standard encoder. Availability "
        "is measured per region. Authentication middleware validates credentials.\n",
        encoding="utf-8",
    )
    found = rules(doc)
    assert "prose-density.Overwritten" not in found
    assert "prose-density.SentenceLoad" not in found


def test_the_two_density_rules_catch_disjoint_defects(tmp_path):
    """Neither rule alone is sufficient, which is why there are two.

    RIX counts long words per sentence, so it misses a rambling sentence built from
    short words. Average sentence length misses dense nominalisation in sentences
    that happen to be short."""
    doc = tmp_path / "case.md"

    # Long sentences, plain vocabulary: sentence load only.
    doc.write_text(
        "The loader will read the file and then it will try again and then it will "
        "give up and log the error to the file that you set in the config that you "
        "passed on the command line when you ran it there.\n",
        encoding="utf-8",
    )
    found = rules(doc)
    assert "prose-density.SentenceLoad" in found
    assert "prose-density.Overwritten" not in found

    # Nominalised and long: density fires.
    doc.write_text(
        "The utilization of the aforementioned methodology facilitates the "
        "optimization of operational efficiency in a manner that is both effective "
        "and efficacious, thereby enabling the achievement of the desired "
        "organizational outcomes within the requisite implementation timeframe.\n",
        encoding="utf-8",
    )
    assert "prose-density.Overwritten" in rules(doc)


# --- Passive density ----------------------------------------------------------
# Document-level, and the only measure of 32 benchmarked against a graded corpus of
# human technical docs that both ranked the audience gradient (rho 0.77) and showed
# no vocabulary confound.


def test_passive_density_fires_above_the_threshold(tmp_path):
    doc = tmp_path / "case.md"
    doc.write_text(
        "The file is read by the loader. "
        "The retry is attempted twice. "
        "The error is written to stderr. "
        "The exit code is returned to the caller. "
        "The state is retained between runs. "
        "The config is parsed at startup. "
        "The token is refreshed automatically. "
        "The result is cached for an hour. "
        "The connection is closed on failure. "
        "The log is rotated each day. "
        "The schema is validated on load. "
        "The report is generated nightly.\n",
        encoding="utf-8",
    )
    assert "prose-density.PassiveDensity" in rules(doc)


def test_passive_density_stays_quiet_on_active_prose(tmp_path):
    doc = tmp_path / "case.md"
    doc.write_text(
        "The loader reads the file. "
        "It retries twice, then fails. "
        "It writes the error to stderr. "
        "It returns exit code two. "
        "It keeps no state between runs. "
        "The parser reads the config at startup. "
        "The client refreshes the token. "
        "The cache holds the result for an hour. "
        "The server closes the connection on failure. "
        "A cron job rotates the log each day. "
        "The loader validates the schema. "
        "A nightly job generates the report.\n",
        encoding="utf-8",
    )
    assert "prose-density.PassiveDensity" not in rules(doc)


def test_passive_density_needs_ten_sentences(tmp_path):
    """Below the floor the share is noise: one passive in four reads as 25%."""
    doc = tmp_path / "case.md"
    doc.write_text(
        "The file is read by the loader. "
        "The retry is attempted twice. "
        "The error is written to stderr.\n",
        encoding="utf-8",
    )
    assert "prose-density.PassiveDensity" not in rules(doc)


def test_passive_density_is_off_for_internal_docs(tmp_path):
    """A specification written in the passive is conventional. Two of the RFC samples
    in the reference corpus score 37% and 33%, above the 35 threshold."""
    spec = tmp_path / "specs"
    spec.mkdir()
    body = (
        "The file is read by the loader. "
        "The retry is attempted twice. "
        "The error is written to stderr. "
        "The exit code is returned to the caller. "
        "The state is retained between runs. "
        "The config is parsed at startup. "
        "The token is refreshed automatically. "
        "The result is cached for an hour. "
        "The connection is closed on failure. "
        "The log is rotated each day. "
        "The schema is validated on load. "
        "The report is generated nightly.\n"
    )
    (spec / "loader.md").write_text(body, encoding="utf-8")
    assert "prose-density.PassiveDensity" not in rules(spec / "loader.md")

    consumer = tmp_path / "README.md"
    consumer.write_text(body, encoding="utf-8")
    assert "prose-density.PassiveDensity" in rules(consumer)
