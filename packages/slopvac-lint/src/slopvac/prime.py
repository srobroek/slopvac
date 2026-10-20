"""The base `slopvac prime` guide: how an agent uses the CLI from this text alone.

Every command, argument, option, choice, and default it names is rendered from
the click command tree it is given, and every profile, genre, config key,
directive form, skipped directory, report field, and exit code from the module
that owns it. The hand-written parts are the grouping of commands, the rules,
and the workflows; a test holds each command and flag they mention to the click
tree, so a renamed flag fails the suite instead of leaving the guide wrong.

The judgement rules are not listed here or in `slopvac prime write|review`:
`slopvac rules --format md` prints them, and this guide only routes to it.
"""

from __future__ import annotations

import typing

import click
from pydantic import BaseModel

from . import __version__
from .config import (
    CONFIG_NAMES,
    PYPROJECT,
    Config,
    GuidanceSettings,
    Override,
    Severity,
)
from .guidance import genres_and_profiles, prime_section, unlinted
from .model import DocumentScore, Finding
from .pipeline import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, LINTABLE, SKIP_SOURCE_DIRS
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

# The complete directive and exclusion reference, at the tag of this version. A
# test holds the path to a file in the repository.
SUPPRESSIONS_DOC = "packages/slopvac-lint/docs/suppressions.md"
SUPPRESSIONS_URL = (
    f"https://github.com/srobroek/slopvac/blob/v{__version__}/{SUPPRESSIONS_DOC}"
)
# The reference for both `slopvac rules` output formats. A test holds the path to
# a file in the repository and the documented JSON keys to the command's output.
RULES_OUTPUT_DOC = "packages/slopvac-lint/docs/rules-output.md"
RULES_OUTPUT_URL = (
    f"https://github.com/srobroek/slopvac/blob/v{__version__}/{RULES_OUTPUT_DOC}"
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
        "Read the rules that a reviewer applies to one genre",
        ("slopvac rules --kind judgement --genre reference --profile strict --format md",),
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


def _argument(param: click.Argument) -> str:
    """One positional argument: its name, whether it is required, and its values."""
    facts = ["required" if param.required else "optional"]
    if param.nargs == -1:
        facts.append("repeatable")
    if isinstance(param.type, click.Choice):
        facts.append(f"one of {_one_of(param.type.choices)}")
    return f"- `{param.human_readable_name}`: {', '.join(facts)}"


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
        "The command reference at the end lists each argument and option.",
        "",
    ]


def _reference(cli: click.Group) -> list[str]:
    """The usage, every argument, and every option of each command, as `--help`
    renders them."""
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
            lines.extend([f"### `{_usage(name, command, context)}`", _summary(command)])
            lines.extend(
                _argument(param)
                for param in command.params
                if isinstance(param, click.Argument)
            )
            lines.extend(
                f"- `{flags}`: {' '.join(text.split())}"
                for flags, text in filter(None, records)
            )
            lines.append("")
    return [
        "## Command reference",
        "",
        "Each heading gives the usage of one command.",
        "An argument line says if the argument is required and lists its values.",
        "An option line gives its value and the help text that `--help` prints.",
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


def _suppressions() -> list[str]:
    """The directives, their scope, and how lint treats a bad one or a quoted one."""
    return [
        "## Fixes and suppressions",
        "",
        "- `slopvac explain <rule_id>` prints the fix, the examples, and the named "
        "exceptions of a rule.",
        "- `--fix` applies safe replacements and lints again. "
        "With a diff option, it edits only added lines.",
        "  It does not edit text that a directive suppresses.",
        "- A rule with the `quotation` exception skips a match inside quotation marks "
        "on one line.",
        "  Other named exceptions apply only through an allow directive.",
        "- A rule whose scope is not `raw` skips these parts of a file:",
        "  - code spans and code blocks",
        "  - HTML comments",
        "- The native engine also skips front matter. Vale reads the values in it.",
        "- A directive is an HTML comment. Write it in one of these case-sensitive forms:",
        f"  - `{allow_comment('<rule_id>', '<exception>')}` skips one rule "
        "in the next block.",
        f"  - `{DISABLE_NEXT_LINE_COMMENT}` skips all rules in the next block.",
        f"  - `{DISABLE_COMMENT}` skips all rules up to the next `{ENABLE_COMMENT}`.",
        "- The next block is the first one of these after the directive:",
        "  - a paragraph or a heading",
        "  - a list item",
        "  - a table",
        "  - a quote",
        "- The directive skips blank lines and other HTML comments before the block.",
        "  A directive at the start of a block applies to that block.",
        "- Use a named exception of the rule as the reason. "
        "A rule without named exceptions takes no allow directive.",
        "- Lint reports `meta.invalid-suppression` for a malformed allow directive.",
        "  It also reports one for an unknown rule id, or for a missing or unlisted reason.",
        "  That directive suppresses nothing. A directive for a rule that does not run "
        "is silent.",
        "- Lint does not report a missing or unlisted reason for a rule that Vale runs.",
        "  `slopvac compile --format json` lists those rules. "
        "Check each of their reasons with `slopvac explain <rule_id>`.",
        "- Regions do not nest. The first enable comment ends a region. "
        "A region without one runs to the end of the file.",
        "- A directive in a code span, a code block, or front matter is text. "
        "It has no effect.",
        "- With `--mode code-comments`, directives have no effect.",
        "- Use a disable directive only around generated or quoted text.",
        "- Vale also reads its own comments, such as `<!-- vale off -->`. "
        "They hide Vale findings with no reason check. Do not write them.",
        f"- The full reference is `{SUPPRESSIONS_URL}`.",
        "",
    ]


def _rule_lookup(cli: click.Group) -> list[str]:
    """Which `slopvac rules` format to read, and how its filters combine."""
    return [
        "## Rule lookup",
        "",
        "- `slopvac rules --format md` prints each rule in full, for an agent to read.",
        "- `slopvac rules --format json` prints the same rules as data, for tools.",
        "- `--kind`, `--category`, and `--genre` select rules. "
        "The list keeps the rules that match each filter that you give.",
        f"- `--genre` takes one of {_choices(cli, 'rules', '--genre')}. "
        "It keeps the categories that list that genre.",
        "- With `--profile`, md output omits the rules that the profile excludes. "
        "`--include-excluded` keeps them.",
        "- `slopvac explain <rule_id> --format md` prints the block of one rule.",
        "- Give these commands the `--rules-dir` that lint uses. "
        "Then they include the house rules.",
        f"- The output reference is `{RULES_OUTPUT_URL}`.",
        "",
    ]


def render_prime(settings: GuidanceSettings, cli: click.Group) -> str:
    """The base guide for an agent, for the given `[guidance]` and command tree."""
    keys, tables = _config_keys()
    patches = [name for name in Override.model_fields if name != "files"]
    shared = {*Override.model_fields, "overrides"}
    top_only = [name for name in (*keys, *tables) if name.strip("[]") not in shared]
    default_exclude = Config().exclude
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
        *_rule_lookup(cli),
        "## Inputs",
        "",
        "- `TARGETS` are files, directories, or globs.",
        f"- A directory expands to the files that match `{' '.join(LINTABLE)}`.",
        f"  It skips the directories `{' '.join(sorted(SKIP_SOURCE_DIRS))}`.",
        "- The `exclude` globs in the config remove files from the run, "
        "named files too.",
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
        *_suppressions(),
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
        f"- Only the top level sets {_code_list(top_only, 'and')}.",
        "- To stop one rule for some files, give a block `files` and "
        f'`rules = {{ "<rule_id>" = "{Severity.OFF.value}" }}`.',
        "- Command-line settings, such as `--profile` and `--disable`, act as a last "
        "block for each file.",
        "- A config that sets `exclude` replaces the default list "
        f"`{' '.join(default_exclude)}`.",
        "- These parts of a file change no finding:",
        "  - a comment on line 1 that starts with `<!-- generated`",
        "  - a heading named `Examples`",
        "  - front matter keys",
        "- Exclude a generated file with `exclude`.",
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
