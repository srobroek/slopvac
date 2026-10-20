"""`slopvac rules --genre`, `--format md`, and `--include-excluded`, the md
block that `slopvac explain` shares, and the reference for both machine formats.

Expected values come from the command's own JSON, which dumps the catalogue
models field by field, never from fixed prose. A reworded block passes; a
dropped field, a wrong filter, or an undocumented key fails.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from slopvac.cli import main
from slopvac.config import Profile
from slopvac.genres import GENRES
from slopvac.model import Tier
from slopvac.prime import RULES_OUTPUT_DOC
from slopvac.suppression import DISABLE_COMMENT, ENABLE_COMMENT

ROOT = Path(__file__).resolve().parents[3]
# The heading that opens one rule's block: "### `<rule_id>`: <name>".
RULE_HEADING = re.compile(r"^### `(?P<id>[^`]+)`: ", re.MULTILINE)


def _run(*args: str) -> str:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def _json(*args: str) -> dict:
    return json.loads(_run("rules", *args, "--format", "json"))


def _blocks(markdown: str) -> dict[str, str]:
    """Each rule's block, keyed by rule id. A rule printed twice fails here."""
    starts = list(RULE_HEADING.finditer(markdown))
    blocks: dict[str, str] = {}
    for match, after in zip(starts, [*starts[1:], None], strict=True):
        assert match["id"] not in blocks, f"{match['id']} printed twice"
        blocks[match["id"]] = markdown[match.start() : after.start() if after else None]
    return blocks


def _clean(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture(scope="module")
def catalogue() -> dict:
    """Every rule and category, unfiltered."""
    return _json()


# --- --genre ---------------------------------------------------------------------


@pytest.mark.parametrize("genre", [genre.name for genre in GENRES])
def test_genre_keeps_exactly_the_categories_that_recommend_it(catalogue, genre):
    recommending = {
        c["id"] for c in catalogue["categories"] if genre in c["recommended_for"]
    }
    expected = [r["rule_id"] for r in catalogue["rules"] if r["category"] in recommending]
    assert expected, f"no rule recommends {genre}; the test proves nothing"
    assert [r["rule_id"] for r in _json("--genre", genre)["rules"]] == expected


def test_genre_combines_with_category_and_kind(catalogue):
    def judged(category: str) -> bool:
        return any(
            r["category"] == category and r["kind"] == "judgement"
            for r in catalogue["rules"]
        )

    categories = catalogue["categories"]
    inside = next(
        c["id"] for c in categories if "consumer" in c["recommended_for"] and judged(c["id"])
    )
    outside = next(
        c["id"] for c in categories if "consumer" not in c["recommended_for"] and judged(c["id"])
    )
    selected = _json(
        "--genre", "consumer", "--category", inside, "--category", outside,
        "--kind", "judgement",
    )["rules"]
    expected = [
        r["rule_id"]
        for r in catalogue["rules"]
        if r["category"] == inside and r["kind"] == "judgement"
    ]
    assert [r["rule_id"] for r in selected] == expected


# --- --format md -----------------------------------------------------------------


def test_md_gives_every_field_of_every_rule(catalogue):
    """Every id once, and for each rule: its question or message, fix, each
    example's text and note, each profile's tier, its tier and severity at the
    profile, and its source and source note."""
    blocks = _blocks(_run("rules", "--format", "md"))
    rules = {r["rule_id"]: r for r in catalogue["rules"]}
    assert set(blocks) == set(rules)
    for rule_id, block in blocks.items():
        rule = rules[rule_id]
        if rule["kind"] == "judgement":
            assert _clean(rule["judgement_question"]) in block, rule_id
        else:
            message = rule["message"].replace("{", "<").replace("}", ">")
            assert _clean(message) in block, rule_id
        if rule["fix"]:
            assert _clean(rule["fix"]) in block, rule_id
        for example in rule["examples"]:
            for text in (example["bad"], example["good"] or ""):
                for line in filter(str.strip, text.splitlines()):
                    assert line in block, (rule_id, line)
            if example["note"]:
                assert _clean(example["note"]) in block, rule_id
        for profile in Profile:
            tier = rule["tiers"].get(profile.value, Tier.EXCLUDED.value)
            assert f"{profile.value}={tier}" in block, (rule_id, profile)
        assert f"`{rule['tier']}`" in block and f"`{rule['effective_severity']}`" in block
        assert _clean(rule["provenance"]["source"]) in block, rule_id
        for ref in ("ste_ref", "orwell_ref", "url"):
            if rule["provenance"][ref]:
                assert rule["provenance"][ref] in block, (rule_id, ref)
        if rule["provenance"]["note"]:
            assert _clean(rule["provenance"]["note"]) in block, rule_id
        for name in rule["exceptions"]:
            assert f"`{name}`" in block, (rule_id, name)


def test_md_prints_each_judgement_rule_once_without_filters(catalogue):
    judgement = {r["rule_id"] for r in catalogue["rules"] if r["kind"] == "judgement"}
    blocks = _blocks(_run("rules", "--kind", "judgement", "--format", "md"))
    assert set(blocks) == judgement


def test_md_and_json_select_the_same_rules_for_a_genre():
    args = ("--kind", "judgement", "--genre", "consumer", "--profile", "normal")
    kept = [r["rule_id"] for r in _json(*args)["rules"] if r["tier"] != Tier.EXCLUDED.value]
    blocks = _blocks(_run("rules", *args, "--format", "md"))
    assert kept and list(blocks) == sorted(kept, key=lambda i: tuple(i.split(".", 1)))


def test_a_chosen_profile_omits_its_excluded_rules_unless_asked(catalogue):
    judgement = {r["rule_id"] for r in catalogue["rules"] if r["kind"] == "judgement"}
    at_relaxed = _json("--kind", "judgement", "--profile", "relaxed")["rules"]
    kept = {r["rule_id"] for r in at_relaxed if r["tier"] != Tier.EXCLUDED.value}
    assert kept and kept != judgement, "relaxed must exclude some rules to prove this"

    args = ("rules", "--kind", "judgement", "--format", "md")
    assert set(_blocks(_run(*args, "--profile", "relaxed"))) == kept
    assert set(_blocks(_run(*args, "--profile", "relaxed", "--include-excluded"))) == judgement
    assert set(_blocks(_run(*args))) == judgement, "no --profile, no omission"


def test_json_and_text_ignore_include_excluded():
    plain = _run("rules", "--profile", "relaxed", "--format", "json")
    assert _run("rules", "--profile", "relaxed", "--include-excluded", "--format", "json") == plain
    text = _run("rules", "--profile", "relaxed")
    assert _run("rules", "--profile", "relaxed", "--include-excluded") == text


def test_md_is_byte_stable():
    args = ("rules", "--kind", "judgement", "--genre", "reference", "--format", "md")
    assert _run(*args) == _run(*args)


def test_lint_reports_nothing_from_the_rule_blocks(tmp_path):
    """The blocks quote catalogue prose, so they are wrapped; the title lines
    stay linted. A document-level metric may still report at line 1."""
    output = _run(
        "rules", "--kind", "judgement", "--genre", "consumer", "--profile", "normal",
        "--format", "md",
    )
    path = tmp_path / "rules.md"
    path.write_text(output, encoding="utf-8")
    lines = output.splitlines()
    start = lines.index(DISABLE_COMMENT) + 1
    assert lines[-1] == ENABLE_COMMENT

    result = CliRunner().invoke(main, ["lint", str(path), "--profile", "strict", "--format", "json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)["documents"][0]
    assert document["errors"] == 0
    assert all(finding["line"] < start for finding in document["findings"]), document["findings"]


# --- explain shares the block ------------------------------------------------------


@pytest.fixture(scope="module")
def relaxed_listing() -> str:
    return _run("rules", "--profile", "relaxed", "--include-excluded", "--format", "md")


@pytest.mark.parametrize(
    "rule_id",
    [
        "ai-tells-content-shape.fabricated-citations-remainder",  # url, example note
        "orwell.stale-figure",  # checked, named exceptions, orwell_ref
        "ste-words.spelling",  # generated per locale
    ],
)
def test_explain_md_is_the_block_that_rules_prints(relaxed_listing, rule_id):
    lines = _run("explain", rule_id, "--profile", "relaxed", "--format", "md").splitlines()
    assert lines[0] == DISABLE_COMMENT and lines[-1] == ENABLE_COMMENT
    block = "\n".join(lines[1:-1])
    assert block.startswith(f"### `{rule_id}`: ")
    end = relaxed_listing.index(block) + len(block)
    assert relaxed_listing[end:].startswith(("\n\n", f"\n{ENABLE_COMMENT}")), rule_id


def test_explain_json_gives_the_tier_and_severity_at_the_profile():
    rule_id = "orwell.stale-figure"
    listed = next(
        r for r in _json("--profile", "relaxed")["rules"] if r["rule_id"] == rule_id
    )
    explained = json.loads(_run("explain", rule_id, "--profile", "relaxed", "--format", "json"))
    assert (explained["tier"], explained["effective_severity"]) == (
        listed["tier"],
        listed["effective_severity"],
    )


# --- the output reference ----------------------------------------------------------


def _reference() -> str:
    return (ROOT / RULES_OUTPUT_DOC).read_text(encoding="utf-8")


def test_the_reference_documents_every_json_key_and_no_other(catalogue):
    """Keys are paths: `rules[].provenance.url`. `tiers` and `substitutions`
    are maps keyed by data, so they are documented as one key each."""
    actual = set(catalogue)
    actual |= {f"categories[].{key}" for c in catalogue["categories"] for key in c}
    for rule in catalogue["rules"]:
        actual |= {f"rules[].{key}" for key in rule}
        actual |= {f"rules[].provenance.{key}" for key in rule["provenance"]}
        actual |= {f"rules[].examples[].{key}" for e in rule["examples"] for key in e}
    section = _reference().split("\n## JSON\n", 1)[1].split("\n## Markdown\n", 1)[0]
    documented = set(re.findall(r"^\| `([^`]+)` \|", section, re.MULTILINE))
    assert documented == actual, {
        "undocumented": sorted(actual - documented),
        "gone": sorted(documented - actual),
    }


def test_the_reference_example_block_is_current_output():
    reference = _reference()
    command, block = re.search(
        r"`(slopvac explain \S+ --format md)`:\n\n````markdown\n(.*?)^````$",
        reference,
        re.MULTILINE | re.DOTALL,
    ).groups()
    assert _run(*command.split()[1:]) == block
