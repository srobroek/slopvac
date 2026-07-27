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
