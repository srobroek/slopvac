"""The base `slopvac prime` guide: how an agent uses the CLI from this text alone.

Every command, option, choice, and default it names is rendered from the click
command tree it is given, and every profile, genre, config key, report field,
and exit code from the module that owns it. The hand-written parts are the
grouping of commands, the rules, and the workflows; a test holds each command
and flag they mention to the click tree, so a renamed flag fails the suite
instead of leaving the guide wrong.

The judgement checklists stay in `slopvac prime write|review`; this guide only
routes to them.
"""

from __future__ import annotations

import typing

import click
from pydantic import BaseModel

from . import __version__
from .config import CONFIG_NAMES, PYPROJECT, Config, GuidanceSettings, Override
from .guidance import genres_and_profiles, prime_section, unlinted
from .model import DocumentScore, Finding
from .pipeline import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, LINTABLE
from .report import LintReport, RunSummary
from .steering import harnesses
from .suppression import (
    DISABLE_COMMENT,
    DISABLE_NEXT_LINE_COMMENT,
    ENABLE_COMMENT,
    allow_comment,
)
from .vale_probe import MIN_VALE_VERSION

# Commands grouped by what an agent wants to do. A test fails when a click
# command is missing here or a name here is not a click command.
COMMAND_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Check prose", ("lint",)),
    ("Look up rules", ("rules", "explain", "reference")),
    ("Read agent guidance", ("prime", "onboard")),
    ("Configure a project", ("init", "setup")),
    ("Inspect Vale styles", ("compile", "cache")),
)

# The report keys an agent reads, checked against the models that serialise
# `--format json`, so a renamed field fails the render.
_SUMMARY_KEYS = ("documents", "score", "errors", "warnings", "passed")
_DOCUMENT_KEYS = ("path", "profile", "score", "passed", "failure_reasons", "unchecked")
_FINDING_KEYS = (
    "rule_id",
    "line",
    "column",
    "severity",
    "message",
    "matched_text",
    "replacement",
)

# Common workflows: a comment line, then the commands. A test checks each command
# and flag against click.
_WORKFLOWS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Lint changed prose, then look up a rule",
        ("slopvac lint README.md docs --format json", "slopvac explain <rule_id>"),
    ),
    (
        "Lint only the lines that a branch adds",
        (
            "slopvac lint docs --diff-base origin/main --format json",
            "slopvac lint src --mode code-comments --diff-base origin/main --format json",
        ),
    ),
    (
        "Apply the safe replacements, then lint again",
        ("slopvac lint README.md --fix --format json",),
    ),
    (
        "Check the settings and rules for one file",
        (
            "slopvac lint docs/api.md --explain-config",
            "slopvac rules --profile strict --kind judgement --format json",
        ),
    ),
    (
        "Install steering for one harness and check it",
        ("slopvac init --harness claude", "slopvac setup claude --check"),
    ),
)


def _keys(model: type[BaseModel], names: tuple[str, ...]) -> str:
    missing = [name for name in names if name not in model.model_fields]
    if missing:
        raise KeyError(f"{model.__name__} has no field {', '.join(missing)}")
    return ", ".join(f"`{name}`" for name in names)


def _code_list(values: typing.Iterable[str], last: str = "or") -> str:
    items = [f"`{value}`" for value in values]
    if len(items) < 3:
        return f" {last} ".join(items)
    return ", ".join(items[:-1]) + f", {last} {items[-1]}"


def _one_of(values: typing.Iterable[str]) -> str:
    """A closed set as click prints it, in one code span: `a|b|c`."""
    return "`" + "|".join(values) + "`"


def _contexts(cli: click.Group) -> dict[str, click.Context]:
    """Contexts that make click render usage and defaults the way `--help` does."""
    root = click.Context(cli, info_name="slopvac", show_default=True)
    return {
        name: click.Context(command, info_name=name, parent=root, show_default=True)
        for name, command in cli.commands.items()
    }


def _choices(cli: click.Group, command: str, flag: str) -> str:
    for param in cli.commands[command].params:
        if isinstance(param, click.Option) and flag in param.opts:
            if not isinstance(param.type, click.Choice):
                raise TypeError(f"slopvac {command} {flag} takes no fixed choices")
            return _one_of(param.type.choices)
    raise KeyError(f"slopvac {command} has no option {flag}")


def _summary(command: click.Command) -> str:
    """The first paragraph of a command's help, on one line."""
    return " ".join((command.help or "").split("\n\n", 1)[0].split())


def _usage(name: str, command: click.Command, context: click.Context) -> str:
    """`slopvac <name>` and its arguments, as click's usage line shows them."""
    pieces = [p for p in command.collect_usage_pieces(context) if p != "[OPTIONS]"]
    return " ".join(["slopvac", name, *pieces])


def _commands(cli: click.Group) -> list[str]:
    contexts = _contexts(cli)
    lines = []
    for purpose, names in COMMAND_GROUPS:
        usages = [
            f"`{_usage(name, cli.commands[name], contexts[name])}`" for name in names
        ]
        lines.append(f"- {purpose}: {', '.join(usages)}")
    return [
        "## Essential commands",
        "",
        *lines,
        "",
        "Every command accepts `--help`. `slopvac --version` prints the version.",
        "The command reference at the end lists each option.",
        "",
    ]


def _reference(cli: click.Group) -> list[str]:
    """Every option of every command, as `--help` renders it."""
    contexts = _contexts(cli)
    lines: list[str] = []
    for _, names in COMMAND_GROUPS:
        for name in names:
            command, context = cli.commands[name], contexts[name]
            records = [
                param.get_help_record(context)
                for param in command.params
                if isinstance(param, click.Option)
            ]
            lines.extend([f"### `slopvac {name}`", _summary(command)])
            lines.extend(
                f"- `{flags}`: {' '.join(text.split())}"
                for flags, text in filter(None, records)
            )
            lines.append("")
    return [
        "## Command reference",
        "",
        "Each line gives one option, its value, and the help text that `--help` prints.",
        "",
        *unlinted(lines[:-1]),
    ]


def _is_model(annotation: object) -> bool:
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def _config_keys() -> tuple[list[str], list[str]]:
    """Top-level keys and tables of a config file, read from the `Config` model."""
    keys, tables = [], []
    for name, field in Config.model_fields.items():
        if field.exclude:
            continue
        origin = typing.get_origin(field.annotation)
        args = typing.get_args(field.annotation)
        if origin is list and args and _is_model(args[0]):
            tables.append(f"[[{name}]]")
        elif origin is dict or _is_model(field.annotation):
            tables.append(f"[{name}]")
        else:
            keys.append(name)
    return keys, tables


def _guidance_keys() -> list[str]:
    lines = []
    for name, field in GuidanceSettings.model_fields.items():
        values = typing.get_args(field.annotation)
        lines.append(f"  - `{name}`: {_one_of(values)}, default `{field.default}`")
    return lines


def _workflows() -> list[str]:
    lines = ["## Common workflows", "", "```bash"]
    for title, commands in _WORKFLOWS:
        lines.extend([f"# {title}", *commands])
    return [*lines, "```", ""]


def render_prime(settings: GuidanceSettings, cli: click.Group) -> str:
    """The base guide for an agent, for the given `[guidance]` and command tree."""
    keys, tables = _config_keys()
    patches = [name for name in Override.model_fields if name != "files"]
    vale = ".".join(str(part) for part in MIN_VALE_VERSION)
    schema = LintReport.model_fields["schema_version"].default
    lines = [
        "# Slopvac agent guidance",
        "",
        "> After compaction, a cleared context, or a new session, run `slopvac prime`.",
        f"> This text comes from the installed slopvac {__version__}.",
        "",
        "## Core rules",
        "",
        "- Lint each prose file that you change. Read the JSON report from "
        "`slopvac lint <paths> --format json`.",
        f"- Exit {EXIT_OK} is a pass. Exit {EXIT_FINDINGS} is a failed gate. "
        f"Exit {EXIT_ERROR} is an incomplete run.",
        f"- Never report an exit {EXIT_ERROR} run as clean. Some of its checks did not run.",
        "- Suppress a finding only with a named exception of its rule.",
        "- A lint pass does not prove a claim. Check facts against code or a source.",
        "- Consumer docs describe shipped behavior.",
        "- Put history in change communications. Put plans in specifications or "
        "decision records.",
        "",
        *prime_section(settings),
        *_commands(cli),
        *genres_and_profiles(),
        "## Inputs",
        "",
        "- `TARGETS` are files, directories, or globs.",
        f"- A directory expands to the files that match `{' '.join(LINTABLE)}`.",
        "- The `exclude` globs in the config remove files from the run.",
        "- `--mode code-comments` or `--comments` lints the comments in source files.",
        "- `--diff-base <rev>` keeps the findings on lines that `<rev>...HEAD` adds.",
        "- `--diff-working-tree` keeps the findings on lines that uncommitted changes add.",
        "- `--category <id>` runs one category. `--disable <id>` turns off a category or a rule.",
        "",
        "## Results",
        "",
        f"- `--format` takes one of {_choices(cli, 'lint', '--format')}.",
        "- `--out <file>` writes the report to a file. "
        "`--open` writes an HTML report and opens it.",
        f"- The JSON report has `schema_version` {schema}. The keys to read are:",
        f"  - `summary`: {_keys(RunSummary, _SUMMARY_KEYS)}",
        f"  - `documents[]`: {_keys(DocumentScore, _DOCUMENT_KEYS)}",
        f"  - `documents[].findings[]`: {_keys(Finding, _FINDING_KEYS)}",
        "- `failure_reasons` names each gate that failed. "
        "`unchecked` names each check that did not run.",
        f"- A run that matches no file exits {EXIT_OK}. "
        "Check that `summary.documents` is not 0.",
        "- A config error or a rule error prints text, not JSON.",
        "",
        "| Exit | Meaning | Action |",
        "| --- | --- | --- |",
        f"| `{EXIT_OK}` | Each file passed its gates. | Report the score. |",
        f"| `{EXIT_FINDINGS}` | A gate failed. | Read `failure_reasons`. "
        "Fix the findings and lint again. |",
        f"| `{EXIT_ERROR}` | The run is incomplete. | Report `unchecked` or the error "
        "text. Fix the cause and lint again. |",
        "",
        "## Vale",
        "",
        "- Vale runs the rules that slopvac compiles to Vale styles. "
        "Slopvac runs the other rules natively.",
        f"- Install Vale {vale} or later.",
        f"- Without Vale, its rules go into `unchecked` and lint exits {EXIT_ERROR}.",
        f"- `--no-vale` skips Vale on purpose. That run also exits {EXIT_ERROR}.",
        "",
        "## Fixes and suppressions",
        "",
        "- `slopvac explain <rule_id>` prints the fix, the examples, and the named "
        "exceptions of a rule.",
        "- `--fix` applies safe replacements and lints again. "
        "With a diff option, it edits only added lines.",
        "- To suppress a finding, write "
        f"`{allow_comment('<rule_id>', '<exception>')}` on the line above its block.",
        "- Use a named exception of the rule as the reason. "
        "Otherwise lint reports `meta.invalid-suppression`.",
        f"- `{DISABLE_NEXT_LINE_COMMENT}` skips the next line. "
        f"`{DISABLE_COMMENT}` and `{ENABLE_COMMENT}` skip a region.",
        "  Use them only around generated or quoted text.",
        "",
        "## Configuration",
        "",
        f"- Lint reads the nearest {_code_list(CONFIG_NAMES)}, or a `{PYPROJECT}` "
        "with a `[tool.slopvac]` table.",
        "- The search starts at each target and stops at the directory that holds `.git`.",
        "- `--config <file>` sets one config file for each target.",
        f"- The top-level keys are {_code_list(keys, 'and')}.",
        f"- The tables are `{' '.join(tables)}`.",
        "- An `[[overrides]]` block takes a `files` list of gitignore-style globs. "
        f"Its other keys are `{' '.join(patches)}`.",
        "- Each matching block applies in file order. "
        "A later block wins for each field that it sets.",
        "- `[guidance]` applies to the whole project. Its keys are:",
        *_guidance_keys(),
        "- `slopvac lint --explain-config <file>` prints the source of each setting.",
        "",
        "## Agent setup",
        "",
        "- `slopvac init` writes the config file and the agent steering. "
        "`--force` replaces a config file.",
        "- Without `--harness`, init writes the generic `AGENTS.md` block.",
        "- Each `--harness <name>` writes the steering and the `slopvac-prose` skill "
        "for that harness.",
        "- `--no-skills` skips the skill. `--skip-agents` writes only the config file.",
        f"- A harness name is one of {_one_of(harnesses())}.",
        "- `slopvac setup <harness>` installs only the steering and the skill of one harness.",
        f"- `slopvac setup <harness> --check` changes no file. Exit {EXIT_OK} means current. "
        f"Exit {EXIT_FINDINGS} means missing or stale.",
        f"  Exit {EXIT_ERROR} means malformed. Repair that file by hand.",
        "- `slopvac setup <harness> --remove` removes the steering block and the skill.",
        "- `slopvac setup --list` prints the files of each harness.",
        "",
        *_workflows(),
        *_reference(cli),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"
