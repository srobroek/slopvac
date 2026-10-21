"""Every prime output against its sources: the click command tree, the genre
table, the profile thresholds, the report models, and the annotation grammar.

The assertions are structural -- which command, flag, key, or number appears
where -- rather than wording, so a rephrased sentence passes and a renamed flag,
a dropped option, or a changed threshold fails.
"""

from __future__ import annotations

import json
import re
import tomllib
import typing
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from slopvac import __version__, model
from slopvac.cli import main
from slopvac.config import (
    Config,
    Override,
    Profile,
    Severity,
    Thresholds,
    profile_thresholds,
)
from slopvac.contract import SKIP_SOURCE_DIRS
from slopvac.genres import GENRES
from slopvac.guidance import RULES_COMMAND
from slopvac.model import Tier
from slopvac.prime import (
    COMMAND_GROUPS,
    RULES_OUTPUT_DOC,
    RULES_OUTPUT_URL,
    SUPPRESSIONS_DOC,
    SUPPRESSIONS_URL,
)
from slopvac.profiles import profile_defaults
from slopvac.rules import load_ruleset
from slopvac.suppression import (
    DISABLE_COMMENT,
    DISABLE_END,
    DISABLE_LINE,
    DISABLE_START,
    ENABLE_COMMENT,
    SUPPRESSION,
    SUPPRESSION_ATTEMPT,
    allow_comment,
)

FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")
SPAN = re.compile(r"`([^`\n]+)`")
# A slopvac directive as a guide or a doc shows it. Placeholders such as
# `<rule_id>` hold `>` but never `-->`, so the first `-->` closes the directive.
SLOPVAC_DIRECTIVE = re.compile(r"<!--\s*slopvac-.*?-->")
ROOT = Path(__file__).resolve().parents[3]
DIRECTIVE_DOCS = tuple(
    ROOT / path
    for path in (
        SUPPRESSIONS_DOC,
        "packages/slopvac-lint/docs/triage.md",
        "packages/slopvac-lint/docs/semantic-guidance.md",
        "packages/slopvac-lint/README.md",
        "README.md",
    )
)

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


@pytest.fixture(scope="module")
def report_output() -> str:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["prime", "report"])
        assert result.exit_code == 0, result.output
        return result.output


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


_GITHUB_FLAGS = frozenset(
    {
        "--state",
        "--search",
        "--json",
        "--limit",
        "--from",
        "--label",
        "--title",
        "--body-file",
    }
)


def _assert_commands_and_flags_exist(text: str, *, name: str) -> set[str]:
    root, contexts = _contexts()
    known = _flags(main, root).union(
        *(_flags(command, contexts[name]) for name, command in main.commands.items())
    )
    assert set(FLAG.findall(text)) <= known.union(_GITHUB_FLAGS), (
        name,
        set(FLAG.findall(text)) - known - _GITHUB_FLAGS,
    )
    commands_seen = set()
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
    return commands_seen


def test_every_command_and_flag_a_guide_names_exists_in_click(outputs):
    commands_seen = set()
    for name, text in outputs.items():
        commands_seen.update(_assert_commands_and_flags_exist(text, name=name))
    assert commands_seen == set(main.commands), "the check must reach every command"


def test_report_command_and_flags_exist_in_click(report_output):
    _assert_commands_and_flags_exist(report_output, name="report")


def _reference_sections(base: str) -> dict[str, tuple[str, str]]:
    """Each command's usage heading and the lines under it, keyed by command name."""
    reference = base.split("\n## Command reference\n", 1)[1]
    return {
        name: (usage, body)
        for name, usage, body in re.findall(
            r"^### `slopvac (\S+)([^`]*)`\n(.*?)(?=^### |\Z)",
            reference,
            re.MULTILINE | re.DOTALL,
        )
    }


def test_the_base_prime_lists_every_click_command_and_option(outputs):
    base = outputs["base-default"]
    grouped = [name for _, names in COMMAND_GROUPS for name in names]
    assert sorted(grouped) == sorted(main.commands), "each command in exactly one group"

    essentials = base.split("\n## Essential commands\n", 1)[1].split("\n## ", 1)[0]
    sections = {name: body for name, (_, body) in _reference_sections(base).items()}
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


def test_the_command_reference_gives_every_argument_of_every_command(outputs):
    """The usage heading shows each argument as click's usage line does, and one
    line per argument says whether it is required, repeatable, and its choices."""
    sections = _reference_sections(outputs["base-default"])
    _, contexts = _contexts()
    arguments = 0
    for name, command in main.commands.items():
        usage, body = sections[name]
        for param in command.params:
            if not isinstance(param, click.Argument):
                continue
            arguments += 1
            assert param.make_metavar(contexts[name]) in usage.split(), (name, usage)
            line = next(
                (
                    line
                    for line in body.splitlines()
                    if line.startswith(f"- `{param.human_readable_name}`: ")
                ),
                None,
            )
            assert line is not None, (name, param.human_readable_name)
            facts = line.split(": ", 1)[1].split(", ")
            assert facts[0] == ("required" if param.required else "optional"), line
            assert ("repeatable" in facts) is (param.nargs == -1), line
            if isinstance(param.type, click.Choice):
                assert f"one of `{'|'.join(param.type.choices)}`" in facts, line
    assert arguments, "the check must reach an argument"


def test_setup_states_when_its_harness_argument_is_required(outputs):
    """The rule lives in the command's help, so `--help` and prime both carry it."""
    _, body = _reference_sections(outputs["base-default"])["setup"]
    summary = body.splitlines()[0]
    assert "HARNESS" in summary and "--list" in summary
    assert "HARNESS" in main.commands["setup"].help


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


# --- the rules command the topics print, and where to read more ---------------------


@pytest.mark.parametrize("topic", ["write", "review"])
def test_topics_explain_the_blocks_the_rules_command_prints(outputs, topic):
    text = outputs[f"{topic}-default"]
    assert f"\n```bash\n{RULES_COMMAND}\n```\n" in text
    after = text.split(RULES_COMMAND, 1)[1]
    assert "`slopvac explain <rule_id> --format md`" in after
    scopes = {rule.scope.value for rule in load_ruleset().judgement_rules}
    for scope in scopes:
        assert f"- `{scope}`: " in after, scope
    for tier in Tier:
        assert f"- `{tier.value}`: " in after, tier


@pytest.mark.parametrize("genre", GENRES, ids=lambda genre: genre.name)
def test_the_rules_command_runs_for_each_genre_at_its_profile(genre):
    command = RULES_COMMAND.replace("<genre>", genre.name).replace(
        "<profile>", genre.profile.value
    )
    result = CliRunner().invoke(main, command.split()[1:])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("# "), "md output"


def test_the_base_prime_routes_rule_lookup_to_md_and_json(outputs):
    base = outputs["base-default"]
    spans = _spans(base)
    assert "slopvac rules --format md" in spans and "slopvac rules --format json" in spans
    assert f"`{RULES_OUTPUT_URL}`" in base
    assert RULES_OUTPUT_URL.endswith(f"/v{__version__}/{RULES_OUTPUT_DOC}")
    assert (ROOT / RULES_OUTPUT_DOC).is_file()


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


def _guides_and_docs(outputs: dict[str, str]) -> dict[str, str]:
    """Every prime output, and each doc that shows directives or config controls."""
    return {
        **outputs,
        **{
            str(path.relative_to(ROOT)): path.read_text(encoding="utf-8")
            for path in DIRECTIVE_DOCS
        },
    }


def test_every_directive_a_guide_or_doc_shows_parses_with_its_pattern(outputs):
    """A shown form with placeholders parses once they are filled with a real rule
    and one of its exceptions. A concrete allow names a real rule and exception."""
    ruleset = load_ruleset()
    rule = next(rule for rule in ruleset.rules if rule.exceptions)
    placeholders = {
        "<rule_id>": rule.qualified_id,
        "<rule-id>": rule.qualified_id,
        "<exception>": rule.exceptions[0],
        "<reason>": rule.exceptions[0],
    }
    patterns = (SUPPRESSION, DISABLE_LINE, DISABLE_START, DISABLE_END)
    for name, text in _guides_and_docs(outputs).items():
        matched = set()
        for snippet in _snippets(text):
            for directive in SLOPVAC_DIRECTIVE.findall(snippet):
                concrete = directive
                for placeholder, value in placeholders.items():
                    concrete = concrete.replace(placeholder, value)
                parsed = [p for p in patterns if p.fullmatch(concrete)]
                assert parsed, (name, directive)
                matched.update(parsed)
                allow = SUPPRESSION.fullmatch(directive)
                if allow:
                    real = ruleset.by_id(allow["rule"])
                    assert real is not None, (name, directive)
                    assert allow["reason"] in real.exceptions, (name, directive)
        if name.startswith("base-"):
            assert matched == set(patterns), name
    assert SUPPRESSION.fullmatch(allow_comment(rule.qualified_id, rule.exceptions[0]))


def test_the_reference_quotes_each_directive_pattern_and_prime_links_it(outputs):
    reference = (ROOT / SUPPRESSIONS_DOC).read_text(encoding="utf-8")
    for pattern in (SUPPRESSION, SUPPRESSION_ATTEMPT, DISABLE_LINE, DISABLE_START, DISABLE_END):
        assert pattern.pattern in reference, pattern.pattern
    assert f"`{SUPPRESSIONS_URL}`" in outputs["base-default"]
    assert SUPPRESSIONS_URL.endswith(f"/v{__version__}/{SUPPRESSIONS_DOC}")


def _spans(text: str) -> set[str]:
    return set(SPAN.findall(text))


def _line_after(text: str, prefix: str) -> str:
    return next(line for line in text.splitlines() if line.startswith(prefix))[len(prefix) :]


def _words_in_span(line: str) -> list[str]:
    """The space-separated values of the one code span on a rendered line."""
    (span,) = SPAN.findall(line)
    return span.split()


def test_the_config_keys_prime_lists_are_the_config_models(outputs):
    base = outputs["base-default"]
    override_keys = set(Override.model_fields) - {"files"}
    patches = _line_after(base, "- An `[[overrides]]` block takes ").split("keys are ", 1)[1]
    assert set(_words_in_span(patches)) == override_keys

    top_only = {span.strip("[]") for span in _spans(_line_after(base, "- Only the top level sets "))}
    assert top_only and top_only <= set(Config.model_fields)
    assert not top_only & set(Override.model_fields)
    assert top_only == set(Config.model_fields) - set(Override.model_fields) - {
        "overrides",
        "source",
        "root",
    }

    excluded = _line_after(base, "- A config that sets `exclude` replaces the default list ")
    assert _words_in_span(excluded) == Config().exclude
    skipped = _line_after(base, "  It skips the directories ")
    assert set(_words_in_span(skipped)) == SKIP_SOURCE_DIRS


def test_the_config_keys_the_reference_lists_are_the_config_models():
    reference = (ROOT / SUPPRESSIONS_DOC).read_text(encoding="utf-8")
    controls = reference.split("\n## File controls\n", 1)[1].split("\n## ", 1)[0]

    def sentence(start: str) -> str:
        match = re.search(rf"{start} (.*?)\.\s", controls, re.DOTALL)
        assert match, start
        return match[1]

    assert _spans(sentence("also set")) == set(Override.model_fields) - {"files"}
    assert "`files`" in controls

    top_only = {span.strip("[]") for span in _spans(sentence("Only the top level sets"))}
    assert top_only <= set(Config.model_fields)
    assert not top_only & set(Override.model_fields)

    block = re.search(r"```toml\n(\s*exclude = .*?)```", controls, re.DOTALL)
    assert block, "the reference shows the default exclude list as TOML"
    assert tomllib.loads(block[1])["exclude"] == Config().exclude
    assert _spans(sentence("skips subdirectories named")) == SKIP_SOURCE_DIRS


# --- how to exclude content, and how a review audits it ------------------------------


def test_write_orders_the_ways_to_exclude_content(outputs):
    section = outputs["write-default"].split("\n## Excluding content\n", 1)[1]
    steps = re.findall(r"^\d+\. (.+)$", section.split("\n## ", 1)[0], re.MULTILINE)
    markers = [
        "code span",
        "`quotation`",
        allow_comment("<rule_id>", "<exception>"),
        DISABLE_COMMENT,
        "`exclude`",
    ]
    assert len(steps) == len(markers)
    for step, marker in zip(steps, markers, strict=True):
        assert marker in step, (marker, step)
    assert ENABLE_COMMENT in steps[3] and "`[[overrides]]`" in steps[4]


_REVIEWS = ("review-default", "review-ask", "review-adversary", "review-self")


@pytest.mark.parametrize("name", _REVIEWS)
def test_the_review_audits_each_directive_inside_the_review_steps(outputs, name):
    workflow = outputs[name].split("\n## Workflow\n", 1)[1].split("\n```text\n", 1)[0]
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", workflow, re.MULTILINE)]
    assert numbers == list(range(1, len(numbers) + 1)), numbers
    for first, last in re.findall(r"[Ss]teps (\d+) to (\d+)", workflow):
        assert 1 <= int(first) < int(last) <= numbers[-1], (first, last)

    audit = next(
        int(n) for n, text in re.findall(r"^(\d+)\. (.+)$", workflow, re.MULTILINE)
        if "directive" in text
    )
    review = re.search(r"runs steps (\d+) to (\d+)|Steps (\d+) to (\d+) are the review", workflow)
    low, high = (int(n) for n in review.groups() if n)
    assert low <= audit <= high

    checklist = outputs[name].split("\n## Checklist\n", 1)[1]
    checks = checklist.split(RULES_COMMAND, 1)[0]
    assert DISABLE_COMMENT in checks and ENABLE_COMMENT in checks
    assert "`slopvac explain <rule_id>`" in checks


@pytest.mark.parametrize("name", _REVIEWS)
def test_the_verdict_reports_suppressions_and_an_unjustified_one_is_revise(outputs, name):
    review = outputs[name]
    verdict = review.split("\n```text\n", 1)[1].split("\n```", 1)[0].splitlines()
    assert verdict[0].startswith("VERDICT: ")
    assert "Suppressions" in [line.split(":", 1)[0] for line in verdict[1:]]
    revise = [line for line in review.splitlines() if "REVISE for" in line]
    assert any("suppression" in line for line in revise), revise


@pytest.mark.parametrize("name", _REVIEWS)
def test_the_verdict_lists_the_rules_asked_and_a_skipped_fetch_is_revise(outputs, name):
    """The `Checked` line makes a review that never ran the rules command visible."""
    review = outputs[name]
    verdict = review.split("\n```text\n", 1)[1].split("\n```", 1)[0].splitlines()
    assert "Checked" in [line.split(":", 1)[0] for line in verdict[1:]]
    after = review.split("\n```\n", 1)[1].split("\n## ", 1)[0]
    assert any("`Checked`" in line and "REVISE" in line for line in after.splitlines())
