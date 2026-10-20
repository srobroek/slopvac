"""Every prime output against its sources: the click command tree, the genre
table, the profile thresholds, the report models, and the annotation grammar.

The assertions are structural -- which command, flag, key, or number appears
where -- rather than wording, so a rephrased sentence passes and a renamed flag,
a dropped option, or a changed threshold fails.
"""

from __future__ import annotations

import json
import re
import typing
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from slopvac import model
from slopvac.cli import main
from slopvac.config import Profile, Severity, Thresholds, profile_thresholds
from slopvac.genres import GENRES
from slopvac.model import Tier
from slopvac.prime import COMMAND_GROUPS
from slopvac.profiles import profile_defaults
from slopvac.suppression import (
    DISABLE_END,
    DISABLE_LINE,
    DISABLE_START,
    SUPPRESSION,
    allow_comment,
)

FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")
SPAN = re.compile(r"`([^`\n]+)`")
DIRECTIVE = re.compile(r"<!--.*?-->")
# One checklist entry: `<category>.<rule-id>` (<scope>): <fix or question>.
ENTRY = re.compile(r"^- `(?P<id>[a-z0-9-]+\.[a-z0-9-]+)` \((?P<scope>[a-z]+)\): .+$")

_MODES = {
    "default": "",
    "ask": 'review = "ask"\n',
    "adversary": 'review_depth = "adversary"\n',
    "self": 'review_depth = "self"\n',
}


@pytest.fixture(scope="module")
def outputs() -> dict[str, str]:
    """Every topic under each `[guidance]` mode that changes the text."""
    runner = CliRunner()
    rendered = {}
    with runner.isolated_filesystem():
        for mode, body in _MODES.items():
            Path("slopvac.toml").write_text(f"[guidance]\n{body}", encoding="utf-8")
            for topic in ("base", "write", "review"):
                args = ["prime"] if topic == "base" else ["prime", topic]
                result = runner.invoke(main, args)
                assert result.exit_code == 0, result.output
                rendered[f"{topic}-{mode}"] = result.output
    return rendered


def _contexts() -> tuple[click.Context, dict[str, click.Context]]:
    root = click.Context(main, info_name="slopvac")
    return root, {
        name: click.Context(command, info_name=name, parent=root)
        for name, command in main.commands.items()
    }


def _flags(command: click.Command, context: click.Context) -> set[str]:
    return {
        flag
        for param in command.get_params(context)
        if isinstance(param, click.Option)
        for flag in (*param.opts, *param.secondary_opts)
    }


def _snippets(text: str) -> typing.Iterator[str]:
    """Inline code spans and fenced code lines: where a guide writes a command."""
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif fenced:
            yield line.split("#", 1)[0].strip()
        else:
            yield from SPAN.findall(line)


def _table(text: str, first_header: str) -> list[dict[str, str]]:
    """The rows of the first table whose header starts with `first_header`."""
    lines = text.splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.startswith(f"| {first_header} |")
    )
    header = [cell.strip().strip("`") for cell in lines[start].strip("|").split("|")]
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


# --- click is the source of every command and flag --------------------------------


def test_every_command_and_flag_a_guide_names_exists_in_click(outputs):
    root, contexts = _contexts()
    known = _flags(main, root).union(
        *(_flags(command, contexts[name]) for name, command in main.commands.items())
    )
    commands_seen = set()
    for name, text in outputs.items():
        assert set(FLAG.findall(text)) <= known, (name, set(FLAG.findall(text)) - known)
        for snippet in _snippets(text):
            words = snippet.split()
            if len(words) < 2 or words[0] != "slopvac":
                continue
            if words[1].startswith("-"):
                command, context = main, root
            else:
                assert words[1] in main.commands, (name, snippet)
                command, context = main.commands[words[1]], contexts[words[1]]
                commands_seen.add(words[1])
            unknown = set(FLAG.findall(snippet)) - _flags(command, context)
            assert not unknown, (name, snippet, unknown)
    assert commands_seen == set(main.commands), "the check must reach every command"


def test_the_base_prime_lists_every_click_command_and_option(outputs):
    base = outputs["base-default"]
    grouped = [name for _, names in COMMAND_GROUPS for name in names]
    assert sorted(grouped) == sorted(main.commands), "each command in exactly one group"

    essentials = base.split("\n## Essential commands\n", 1)[1].split("\n## ", 1)[0]
    reference = base.split("\n## Command reference\n", 1)[1]
    sections = dict(
        re.findall(
            r"^### `slopvac (\S+)`\n(.*?)(?=^### |\Z)",
            reference,
            re.MULTILINE | re.DOTALL,
        )
    )
    for name, command in main.commands.items():
        assert f"`slopvac {name}" in essentials, name
        assert name in sections, name
        for param in command.params:
            if isinstance(param, click.Option):
                for flag in (*param.opts, *param.secondary_opts):
                    assert f"- `{flag}" in sections[name], (name, flag)
    root, _ = _contexts()
    for flag in _flags(main, root):
        assert f"{flag}`" in base, flag


# --- one source for genres and profiles -------------------------------------------


def test_genre_names_have_one_source():
    names = [genre.name for genre in GENRES]
    assert len(set(names)) == len(names)
    assert set(typing.get_args(model.Genre)) == set(names)


def test_every_guide_renders_the_genre_table_from_its_source(outputs):
    expected = [(g.name, g.surfaces, g.profile.value) for g in GENRES]
    for name, text in outputs.items():
        rows = [
            (row["Genre"].strip("`"), row["Surfaces"], row["Profile"].strip("`"))
            for row in _table(text, "Genre")
        ]
        assert rows == expected, name


def _gate(cell: str) -> float | None:
    return None if cell == "none" else float(cell)


def test_profile_gates_in_every_guide_equal_profile_thresholds(outputs):
    for name, text in outputs.items():
        rows = {row["Profile"].strip("`"): row for row in _table(text, "Profile")}
        assert set(rows) == {profile.value for profile in Profile}, name
        for profile in Profile:
            row = rows[profile.value]
            gates = profile_thresholds(profile)
            for key in Thresholds.model_fields:
                value = getattr(gates, key)
                assert _gate(row[key]) == (None if value is None else float(value)), (
                    name,
                    profile,
                    key,
                )
            genres = {cell.strip("` ") for cell in row["Genres"].split(",")}
            assert genres == {g.name for g in GENRES if g.profile is profile}


def test_every_guide_lists_the_categories_each_profile_turns_off(outputs):
    for name, text in outputs.items():
        for profile in Profile:
            line = next(
                line
                for line in text.splitlines()
                if line.startswith(f"- `{profile.value}`: ")
            )
            listed = set(re.findall(r"`([a-z0-9-]+)`", line.split(": ", 1)[1]))
            off = {
                category
                for category, settings in profile_defaults(profile).items()
                if settings.severity is Severity.OFF
            }
            assert listed == off, (name, profile)


@pytest.mark.parametrize("topic", ["write", "review"])
def test_topics_define_genres_and_profiles_before_the_workflow(outputs, topic):
    head = outputs[f"{topic}-default"].split("\n## Workflow\n", 1)[0]
    assert "\n| Genre |" in head and "\n| Profile |" in head
    assert "`slopvac lint --explain-config <file>`" in head
    assert "`slopvac rules --profile <profile>`" in head


# --- checklist entries and where to read more ---------------------------------------


@pytest.mark.parametrize("topic", ["write", "review"])
def test_topics_explain_the_entry_format_before_the_first_entry(outputs, topic):
    lines = outputs[f"{topic}-default"].splitlines()
    first = next(i for i, line in enumerate(lines) if ENTRY.match(line))
    before = "\n".join(lines[:first])
    assert "`<category>.<rule-id>` (<scope>)" in before
    assert "`slopvac explain <rule_id>`" in before
    assert "`slopvac rules --kind judgement --profile <profile> --format json`" in before
    for scope in {m["scope"] for line in lines if (m := ENTRY.match(line))}:
        assert f"- `{scope}`: " in before, scope
    for tier in Tier:
        assert f"- `{tier.value}`: " in before, tier


def test_the_tier_key_the_topics_name_is_in_the_rules_json(outputs):
    assert "`rules[].tier`" in outputs["write-default"]
    assert "`rules[].tier`" in outputs["review-default"]
    result = CliRunner().invoke(
        main, ["rules", "--kind", "judgement", "--profile", "strict", "--format", "json"]
    )
    rules = json.loads(result.output)["rules"]
    assert rules and {rule["tier"] for rule in rules} <= {tier.value for tier in Tier}


# --- report keys and annotations ----------------------------------------------------


def test_report_keys_the_base_prime_names_are_in_a_lint_report(outputs, tmp_path):
    document = tmp_path / "doc.md"
    document.write_text("# Notes\n\nThe tool runs — and it stops.\n", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["lint", str(document), "--no-vale", "--format", "json"]
    )
    report = json.loads(result.output)
    scopes = {
        "summary": report["summary"],
        "documents[]": report["documents"][0],
        "documents[].findings[]": report["documents"][0]["findings"][0],
    }
    lines = outputs["base-default"].splitlines()
    for path, payload in scopes.items():
        line = next(line for line in lines if line.lstrip().startswith(f"- `{path}`: "))
        keys = re.findall(r"`([a-z_]+)`", line.split(": ", 1)[1])
        assert keys and set(keys) <= set(payload), (path, set(keys) - set(payload))


def test_the_annotations_the_base_prime_shows_are_the_ones_lint_parses(outputs):
    shown = [
        directive
        for span in SPAN.findall(outputs["base-default"])
        for directive in DIRECTIVE.findall(span)
    ]
    assert len(shown) >= 4
    patterns = (SUPPRESSION, DISABLE_LINE, DISABLE_START, DISABLE_END)
    for directive in shown:
        concrete = directive.replace("<rule_id>", "prose-format.no-unicode-dash").replace(
            "<exception>", "quotation"
        )
        assert any(p.fullmatch(concrete) for p in patterns), directive

    allow = SUPPRESSION.fullmatch(
        allow_comment("prose-format.no-unicode-dash", "quotation")
    )
    assert allow and allow["rule"] == "prose-format.no-unicode-dash"
    assert allow["reason"] == "quotation"
