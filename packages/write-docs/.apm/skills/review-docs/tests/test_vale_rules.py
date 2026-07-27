"""Behavioural tests for the published Vale styles and the slop-lint entrypoint.

Replaces test_slop_lint.py. Vale has no rule-test framework, so these drive the
real binary over fixtures and assert on rule names and the exit contract.

Skipped when `vale` is absent so a checkout without it still collects.
"""

from __future__ import annotations

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
