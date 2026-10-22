"""Command line interface.

EXIT CODES are the contract every caller depends on -- pre-commit, the GitHub
Action, agent steering, and CI:

    0  clean, or findings below every configured threshold
    1  a threshold failed (the run worked; the prose did not)
    2  the run could not be trusted: bad config, unloadable ruleset, missing tool

The 1/2 split matters. A pre-commit hook should block on 1 and shout differently
on 2, because 2 means nothing was checked. Warnings alone stay at 0 unless the
project sets `max_warnings`, which preserves the existing gate's behaviour.
"""

from __future__ import annotations

# Every command, `--version` included, pays for what this module imports when it
# loads. So the top level imports only what the click declarations need, and each
# command imports its own machinery.
import sys
from contextlib import contextmanager
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

import click

from . import __version__
from .contract import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK
from .enums import Mode, Profile, RuleKind, Severity, Tier
from .genres import GENRES
from .steering import harnesses
from .vale_cache import CACHE_KEEP

if TYPE_CHECKING:
    from collections.abc import Callable

    from rich.console import Console

    from .config import GuidanceSettings
    from .model import Rule
    from .rules import RuleSet


def _console(no_color: bool) -> Console:
    from rich.console import Console

    # force_terminal=False lets rich detect a pipe and drop styling, so piped
    # output stays greppable.
    return Console(no_color=no_color, soft_wrap=True, stderr=False)


class _DefaultGroup(click.Group):
    """Treat an unrecognised first argument as a path for `lint`.

    `slopvac README.md` has to work: it is what a reader tries first, what
    the pre-commit hook passes (staged filenames, positionally), and what the
    GitHub Action forwards. Without this, click reports the filename as an
    unknown command and exits 2, which a caller reads as "the run could not be
    trusted".
    """

    #: Options the group itself owns. Anything else on a bare invocation belongs
    #: to `lint`.
    _GROUP_OPTIONS = frozenset({"--help", "-h", "--version"})

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        """Insert the implicit `lint` BEFORE click parses options.

        `resolve_command` runs too late: click has already rejected `--profile` as
        an unknown group option by then, so the documented
        `slopvac --profile relaxed FILE` exited 2 while the same run with an
        explicit `lint` passed. An advertised invocation that fails is worse than
        no default subcommand at all.
        """
        if ctx.parent is None:
            ctx.meta["slopvac_update_arguments"] = tuple(args)
        if (
            args
            and not any(a in self.commands for a in args)
            and not all(a in self._GROUP_OPTIONS for a in args if a.startswith("-"))
        ):
            args = ["lint", *args]
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx: click.Context, args: list[str]):
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["lint", *args]
        return super().resolve_command(ctx, args)


def _note_output(output_format: str | None, *report_targets: object) -> None:
    """Record what the command emits, so the update notice stays out of machine output."""
    meta = click.get_current_context().find_root().meta
    meta["slopvac_update_format"] = output_format
    meta["slopvac_update_to_file"] = any(report_targets)


def _machine_output(arguments: tuple[str, ...] | list[str]) -> bool:
    """True when raw arguments ask for non-text or file output.

    Read before the subcommand parses, so a machine-output run never starts a
    network check. `_note_output` still guards the notice after parsing.
    """
    formats = [nxt for cur, nxt in pairwise(arguments) if cur == "--format"]
    formats += [arg.partition("=")[2] for arg in arguments if arg.startswith("--format=")]
    to_file = any(arg in ("--out", "--open") or arg.startswith("--out=") for arg in arguments)
    return to_file or any(fmt != "text" for fmt in formats)


# Options several commands share, declared once so their help cannot diverge.
_rules_dir_option = click.option(
    "--rules-dir",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Extra rule directory, layered over the packaged rules. Repeatable.",
)
_text_or_json_option = click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="text for humans, json for tooling.",
)
_rule_format_option = click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "md"]),
    default="text",
    help="text for humans, json for tooling, md for agents to read.",
)
_rule_profile_option = click.option(
    "--profile",
    type=click.Choice([p.value for p in Profile]),
    default="normal",
    help="Show the tier and severity at this profile.",
)


@click.group(cls=_DefaultGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="slopvac")
@click.pass_context
def main(context: click.Context) -> None:
    """Lint prose and source comments with the unified slopvac ruleset.

    `slopvac FILE...` lints. `slopvac rules` lists the rules.
    """
    if context.invoked_subcommand is None:
        click.echo(context.get_help())
        return

    if context.invoked_subcommand == "prime" or _machine_output(
        context.meta.get("slopvac_update_arguments", ())
    ):
        return
    from .update_notice import show_update_notice, start_refresh

    start_refresh()

    def notice() -> None:
        meta = context.find_root().meta
        show_update_notice(
            command=context.invoked_subcommand,
            output_format=meta.get("slopvac_update_format"),
            output_to_file=meta.get("slopvac_update_to_file", False),
        )

    context.call_on_close(notice)


@main.command()
@_text_or_json_option
@click.option(
    "--binary",
    default=None,
    help="Vale executable name or path. Defaults to [vale].binary or vale.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read [vale].binary from this configuration file.",
)
def doctor(binary: str | None, config_path: Path | None, output_format: str) -> None:
    """Check that the required Vale executable is available and supported."""
    from .config import ConfigError, find_config, load_config
    from .vale_probe import ValeUnavailable, require_vale, vale_version

    if output_format == "text":
        discovered = config_path or find_config(Path.cwd())
        try:
            config = load_config(discovered, root=discovered.parent if discovered else None)
        except ConfigError as exc:
            click.echo(f"config error: {exc}", err=True)
            raise SystemExit(EXIT_ERROR) from None
        try:
            executable = require_vale(binary or config.vale.binary)
        except ValeUnavailable as exc:
            click.echo(f"Vale prerequisite failed: {exc}", err=True)
            raise SystemExit(EXIT_ERROR) from None
        version = vale_version(executable)
        click.echo(f"Vale {'.'.join(map(str, version))} available: {executable}")
        return

    from . import doctor_report

    discovered = config_path or find_config(Path.cwd())
    if discovered is not None:
        discovered = discovered.resolve()
    try:
        config = load_config(discovered, root=discovered.parent if discovered else None)
    except ConfigError as exc:
        config = None
        config_error = str(exc)
    else:
        config_error = None
    report = doctor_report.build_report(
        discovered,
        config=config,
        config_error=config_error,
        binary=binary or (config.vale.binary if config else "vale"),
        root=discovered.parent if discovered else Path.cwd(),
    )
    import json

    click.echo(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(EXIT_ERROR)

@main.command()
@click.argument("targets", nargs=-1, required=False)
@click.option("--stdin", "stdin_input", is_flag=True, help="Read one UTF-8 document from standard input.")
@click.option("--language", help="Input format: markdown, mdx, rst, html, text, or a source language in code-comments.")
@click.option(
    "--profile",
    type=click.Choice([p.value for p in Profile]),
    help="Override the configured tier for this run.",
)
@click.option(
    "--mode",
    type=click.Choice([m.value for m in Mode]),
    default=None,
    help="Input surface: prose or code-comments.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Config file. Default: nearest slopvac.toml from the current directory with --stdin, or each target.",
)
@_rules_dir_option
@click.option(
    "--category",
    "only_categories",
    multiple=True,
    help="Run only these categories. Repeatable.",
)
@click.option(
    "--disable",
    "disabled",
    multiple=True,
    help="Disable a category or a qualified rule id. Repeatable.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "github", "sarif", "html"]),
    default="text",
    help="text for humans, json for tooling, github for Action annotations, "
    "sarif for code scanning, html for a standalone report.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the report here instead of stdout. Without --format the report "
    "is HTML; with one, that format is written. Implied by --open.",
)
@click.option(
    "--open",
    "open_report",
    is_flag=True,
    help="Open the HTML report in a browser. Writes to a temp file unless --out "
    "names one.",
)
@click.option("--min-score", type=float, help="Fail below this 0-100 score.")
@click.option(
    "--max-per-100-words",
    type=float,
    help="Fail above severity-weighted error/warning density (1.0/0.5).",
)
@click.option(
    "--locale",
    "locale_tag",
    help="Spelling target: en-US, en-GB, or und to disable. Overrides slopvac.toml.",
)
@click.option(
    "--no-vale", is_flag=True, help="Skip the Vale sub-gate even when configured."
)
@click.option(
    "--diff-base",
    metavar="REV",
    help="Scope findings to added lines in REV...HEAD (committed branch diff).",
)
@click.option(
    "--diff-working-tree",
    is_flag=True,
    help="Scope findings to added lines in HEAD versus the index and working tree.",
)
@click.option(
    "--comments",
    is_flag=True,
    help="Alias for --mode code-comments.",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Apply safe replacements; hunk mode never edits unchanged lines.",
)
@click.option("--no-color", is_flag=True, help="Plain output.")
@click.option("--verbose", is_flag=True, help="Show categories with no findings.")
@click.option(
    "--explain-config",
    is_flag=True,
    help="Print the resolved settings per file and exit without linting.",
)
def lint(
    targets: tuple[str, ...],
    stdin_input: bool,
    language: str | None,
    profile: str | None,
    mode: str | None,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
    only_categories: tuple[str, ...],
    disabled: tuple[str, ...],
    output_format: str,
    out_path: Path | None,
    open_report: bool,
    min_score: float | None,
    max_per_100_words: float | None,
    locale_tag: str | None,
    no_vale: bool,
    diff_base: str | None,
    diff_working_tree: bool,
    comments: bool,
    fix: bool,
    no_color: bool,
    verbose: bool,
    explain_config: bool,
) -> None:
    """Lint TARGETS, or one document read from standard input.

    Exit 0 passes, 1 fails a threshold, and 2 is an incomplete run.
    """
    from .diff_scope import DiffScopeError, apply_replacements, changed_scope
    from .pipeline import emit_report

    mode, language, code_comments = _resolve_input_options(
        targets,
        stdin_input=stdin_input,
        language=language,
        mode=mode,
        comments=comments,
        diff_base=diff_base,
        diff_working_tree=diff_working_tree,
        fix=fix,
        open_report=open_report,
    )
    with _staged_stdin(targets, stdin_input, language, code_comments) as (inputs, stdin_path):
        _note_output(output_format, out_path, open_report)
        console = _console(no_color)
        scope = None
        if diff_base is not None or diff_working_tree:
            try:
                scope = changed_scope(base=diff_base, working_tree=diff_working_tree)
            except DiffScopeError as exc:
                console.print(f"[red]incomplete check[/]: {exc}")
                raise SystemExit(EXIT_ERROR) from None
        run = _load_lint_context(
            console,
            inputs,
            profile=profile,
            mode=mode,
            config_path=config_path,
            rules_dir=rules_dir,
            only_categories=only_categories,
            disabled=disabled,
            min_score=min_score,
            max_per_100_words=max_per_100_words,
            locale_tag=locale_tag,
            diff_scope=scope,
            comments=comments,
            stdin_path=stdin_path,
        )
        if not run.paths and not run.collection_unchecked:
            # A run with nothing to lint still owes the caller a report in the format
            # it asked for: the GitHub action parses the JSON, and a bare text line
            # where JSON was expected read as "the report could not be produced" on
            # every release PR, whose only prose change (CHANGELOG.md) is excluded.
            # The notice goes to stderr so a machine format on stdout stays parseable.
            click.echo("no lintable files matched", err=True)
            emit_report(
                [],
                run.ruleset,
                console,
                output_format=output_format,
                out_path=out_path,
                open_report=open_report,
                format_given=_format_was_given(),
                verbose=verbose,
                notes=run.collection_notes,
            )
            raise SystemExit(EXIT_OK)

        if explain_config:
            _print_resolved_config(run, console)
            raise SystemExit(EXIT_OK)

        scores = _run_lint_or_exit(run, console, no_vale=no_vale)
        if fix:
            rules = {
                rule.qualified_id: rule
                for ruleset in run.rulesets.values()
                for rule in ruleset.rules
            }
            if apply_replacements(scores, rules, scope) > 0:
                scores = _run_lint_or_exit(run, console, no_vale=no_vale)
        emit_report(
            scores,
            run.ruleset,
            console,
            output_format=output_format,
            out_path=out_path,
            open_report=open_report,
            format_given=_format_was_given(),
            verbose=verbose,
            notes=run.collection_notes,
        )
    if any(score.unchecked for score in scores):
        raise SystemExit(EXIT_ERROR)
    raise SystemExit(EXIT_OK if all(score.passed for score in scores) else EXIT_FINDINGS)


def _resolve_input_options(
    targets: tuple[str, ...],
    *,
    stdin_input: bool,
    language: str | None,
    mode: str | None,
    comments: bool,
    diff_base: str | None,
    diff_working_tree: bool,
    fix: bool,
    open_report: bool,
) -> tuple[str | None, str | None, bool]:
    """Validate TARGETS against --stdin and return the mode, language and comment flag.

    Without --stdin the mode is returned unchanged. With it, the mode is made
    explicit so the staged file and the pipeline agree on how to read it."""
    if not stdin_input:
        if language is not None:
            raise click.UsageError("--language requires --stdin.")
        if not targets:
            raise click.UsageError("TARGETS are required unless --stdin is set.")
        return mode, language, False
    if targets:
        raise click.UsageError("TARGETS must be empty when --stdin is set.")
    rejected = {
        "--diff-base": diff_base is not None,
        "--diff-working-tree": diff_working_tree,
        "--fix": fix,
        "--open": open_report,
    }
    for option, given in rejected.items():
        if given:
            reason = " because stdin has no file to write back to" if option == "--fix" else ""
            raise click.UsageError(f"{option} is not supported with --stdin{reason}.")
    # The pipeline lets an explicit --mode win over --comments, so the language
    # check follows the same rule.
    code_comments = mode == Mode.CODE_COMMENTS.value if mode is not None else comments
    if mode is None:
        mode = Mode.CODE_COMMENTS.value if comments else Mode.PROSE.value
    if code_comments and language is None:
        raise click.UsageError("--language is required with --stdin --mode code-comments.")
    language = language or "markdown"
    valid_languages = _stdin_languages(code_comments)
    if language not in valid_languages:
        raise click.UsageError(
            f"--language {language!r} is not valid for mode {mode}. "
            f"Valid values: {', '.join(valid_languages)}."
        )
    return mode, language, code_comments


@contextmanager
def _staged_stdin(
    targets: tuple[str, ...], stdin_input: bool, language: str | None, code_comments: bool
):
    """Yield the targets to lint and the staged stdin file, or None without --stdin.

    The pipeline lints paths, so stdin goes through a file named only by its
    extension; every report maps that file back to `<stdin>`. The directory is
    removed on every exit, including errors."""
    if not stdin_input:
        yield targets, None
        return
    from tempfile import TemporaryDirectory

    # Stdin is documented as UTF-8. Reject anything else up front: Vale panics on
    # invalid UTF-8, so a replaced decode would still end incomplete.
    raw = click.get_binary_stream("stdin").read()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        click.echo(f"incomplete check: stdin is not valid UTF-8 (byte {exc.start}).", err=True)
        raise SystemExit(EXIT_ERROR) from None
    with TemporaryDirectory(prefix="slopvac-stdin-") as directory:
        staged = Path(directory) / f"stdin{_stdin_suffix(language or 'markdown', code_comments)}"
        staged.write_bytes(raw)
        yield (str(staged),), staged


def _stdin_extensions(code_comments: bool) -> dict[str, str]:
    """Map each `--language` value to the extension the staged file takes.

    Built from the lists that select files by extension, so a format slopvac
    lints from disk is a format it lints from stdin, and nothing else is."""
    if code_comments:
        from .compile_vale import SOURCE_LANGUAGE_BY_EXTENSION

        extensions = {".toml": "toml", **SOURCE_LANGUAGE_BY_EXTENSION}
    else:
        from .contract import LINTABLE

        aliases = {".md": "markdown", ".markdown": "markdown", ".txt": "text"}
        extensions = {
            suffix: aliases.get(suffix, suffix.lstrip("."))
            for suffix in (pattern.removeprefix("*") for pattern in LINTABLE)
        }
    by_language: dict[str, str] = {}
    for suffix, language in extensions.items():
        by_language.setdefault(language, suffix)
    return by_language


def _stdin_languages(code_comments: bool) -> tuple[str, ...]:
    return tuple(sorted(_stdin_extensions(code_comments)))


def _stdin_suffix(language: str, code_comments: bool) -> str:
    return _stdin_extensions(code_comments)[language]


def _print_pipeline_error(console: Console, exc, stdin_path: Path | None) -> None:
    from .pipeline import redact_stdin

    for message in exc.messages:
        console.print(redact_stdin(message, stdin_path))


def _format_was_given() -> bool:
    return (
        click.get_current_context().get_parameter_source("output_format")
        is not click.core.ParameterSource.DEFAULT
    )


def _load_lint_context(
    console: Console,
    targets: tuple[str, ...],
    *,
    stdin_path: Path | None = None,
    **options,
):
    from .pipeline import PipelineError, load_run_context

    try:
        return load_run_context(targets, stdin_input=stdin_path is not None, **options)
    except PipelineError as exc:
        _print_pipeline_error(console, exc, stdin_path)
        raise SystemExit(exc.code) from None


def _run_lint_or_exit(run, console: Console, *, no_vale: bool):
    from .pipeline import PipelineError, run_lint

    try:
        return run_lint(run, no_vale=no_vale)
    except PipelineError as exc:
        _print_pipeline_error(console, exc, run.stdin_path)
        raise SystemExit(exc.code) from None


def _print_resolved_config(run, console: Console) -> None:
    from .config import resolve_blocklist_path, resolve_for

    for path in run.paths:
        config = run.configs[path]
        resolved = resolve_for(config, path)
        display_path = "<stdin>" if run.stdin_path == path else path
        console.print(f"[bold]{display_path}[/]")
        console.print(f"  config: {config.source or '(defaults)'}")
        console.print(f"  profile: {resolved.profile.value}")
        if resolved.applied_overrides:
            console.print(f"  overrides: {', '.join(resolved.applied_overrides)}")
        console.print(
            f"  thresholds: {resolved.thresholds.model_dump(exclude_none=True)}"
        )
        blocklist = resolve_blocklist_path(resolved.vocabulary, config.root)
        if blocklist is not None:
            console.print(f"  blocklist: {blocklist}")
        off = sorted(
            name
            for name, category in resolved.categories.items()
            if category.severity is Severity.OFF
        )
        if off:
            console.print(f"  disabled: {', '.join(off)}")
        if resolved.provenance:
            console.print("  set by:")
            for setting, where in sorted(resolved.provenance.items()):
                console.print(f"    {setting}: {where}")


def _locale_of(config_path: Path | None) -> tuple[str, list[str] | None]:
    """The locale the spelling rule is generated from, for the inspection commands.

    `lint` reads this from the config it already loaded. `rules` and `explain` load
    no config, so without this they describe a ruleset that differs from the one
    `lint` runs: the spelling rule is generated per locale rather than shipped as
    YAML, so it is absent from an uninjected ruleset. A rule the gate reports and
    `explain` then calls unknown is the failure this avoids.

    A broken config is not worth failing an inspection command over -- it falls back
    to the default locale, and `lint` is where a config error is reported.
    """
    from .config import ConfigError, load_config

    try:
        config = load_config(
            config_path, root=config_path.parent if config_path else None
        )
    except ConfigError:
        return "en-US", None
    return config.locale.default, config.locale.allow


def _severity_at(
    console: Console, ruleset: RuleSet, profile: str, config_path: Path | None
) -> Callable[[Rule], str]:
    """The level each rule REPORTS at, resolved the way `lint` resolves it.

    That is the profile's category severity, the profile's own per-rule dials,
    and the config file's authored overrides. The shipped `severity` field alone
    told a reader `warning` for a rule that `lint` reported as an error.
    """
    from .config import Config, ConfigError, load_config, resolve_for
    from .engine import Engine

    try:
        config = load_config(config_path) if config_path else Config()
    except ConfigError as exc:
        console.print(f"[red]config error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None
    # Inspection has no input file. File-specific overrides must not replace
    # the requested profile or leak settings from a synthetic README path.
    config = config.model_copy(update={"profile": Profile(profile), "overrides": []})
    resolved = resolve_for(config, Path("README.md"))
    engine = Engine(ruleset.rules, resolved)
    active = {rule.qualified_id for rule in engine.rules}

    def effective(rule: Rule) -> str:
        if rule.kind is RuleKind.JUDGEMENT:
            # Never fires mechanically; the reviewer reads it at its shipped level.
            return rule.severity.value
        if rule.qualified_id not in active:
            return Severity.OFF.value
        return engine.severity_for(rule).value

    return effective


@main.command("rules")
@_rule_profile_option
@click.option("--category", "only", multiple=True, help="Limit to these categories.")
@click.option(
    "--kind",
    type=click.Choice([k.value for k in RuleKind]),
    help="Filter by rule kind; `judgement` lists the rules lint never checks.",
)
@click.option(
    "--genre",
    type=click.Choice([genre.name for genre in GENRES]),
    help="Limit to the categories recommended for this genre.",
)
@_rule_format_option
@click.option(
    "--include-excluded",
    is_flag=True,
    help="With --profile, md output omits the rules that the profile excludes. "
    "This flag keeps them.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Resolve severities with this config's settings. Default: the profile's "
    "own settings.",
)
@_rules_dir_option
def list_rules(
    profile: str,
    only: tuple[str, ...],
    kind: str | None,
    genre: str | None,
    output_format: str,
    include_excluded: bool,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
) -> None:
    """List the rules and whether each is on at a profile.

    `--format md` prints each rule in full, grouped by category, for an agent to
    read. The filters combine: a rule must pass every one given.
    """
    import json

    from rich.table import Table

    from .config import find_config
    from .rule_markdown import render_rules
    from .rules import RuleLoadError, inject_locale_rule, load_ruleset

    _note_output(output_format)
    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    inject_locale_rule(ruleset, *_locale_of(config_path or find_config(Path.cwd())))

    selected = [
        rule
        for rule in ruleset.all_rules
        if (not only or rule.category in only)
        and (not kind or rule.kind.value == kind)
        and (not genre or genre in ruleset.categories[rule.category].recommended_for)
    ]
    effective = _severity_at(console, ruleset, profile, config_path)

    if output_format == "md":
        # Only a profile the caller chose drops rules: without `--profile`, md lists
        # every rule and shows the default profile's tiers.
        omit = not include_excluded and (
            click.get_current_context().get_parameter_source("profile")
            is not click.core.ParameterSource.DEFAULT
        )
        shown = [
            rule
            for rule in selected
            if not (omit and rule.tier_for(profile) is Tier.EXCLUDED)
        ]
        click.echo(render_rules(ruleset, shown, profile, effective, omit), nl=False)
        raise SystemExit(EXIT_OK)

    if output_format == "json":
        click.echo(
            json.dumps(
                {
                    "profile": profile,
                    "categories": [
                        {
                            "id": c.id,
                            "title": c.title,
                            "description": c.description,
                            "weight": c.weight,
                            "recommended_for": c.recommended_for,
                        }
                        for c in ruleset.categories.values()
                    ],
                    "rules": [
                        {
                            **rule.model_dump(mode="json"),
                            "rule_id": rule.qualified_id,
                            "tier": rule.tier_for(profile).value,
                            "effective_severity": effective(rule),
                        }
                        for rule in selected
                    ],
                },
                indent=2,
            )
        )
        raise SystemExit(EXIT_OK)

    table = Table(header_style="bold")
    table.add_column("rule")
    table.add_column("kind")
    table.add_column(f"@{profile}")
    table.add_column("severity")
    table.add_column("source")
    for rule in selected:
        table.add_row(
            rule.qualified_id,
            rule.kind.value,
            rule.tier_for(profile).value,
            effective(rule),
            rule.provenance.ste_ref
            or rule.provenance.orwell_ref
            or rule.provenance.source,
        )
    console.print(table)
    console.print(f"{len(selected)} rule(s) in {len(ruleset.categories)} category(ies)")


@main.command()
@click.argument("rule_id")
@_rule_format_option
@_rule_profile_option
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read the spelling locale from this file, and resolve severities with its "
    "settings. Default: the nearest slopvac config's locale and the profile's own "
    "settings.",
)
@_rules_dir_option
def explain(
    rule_id: str,
    output_format: str,
    profile: str,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
) -> None:
    """Show one rule in full.

    `--format md` prints the block that `slopvac rules --format md` prints.
    """
    import json

    from rich.markup import escape

    from .config import find_config
    from .rule_markdown import message_text, render_explain
    from .rules import RuleLoadError, inject_locale_rule, load_ruleset
    from .suppression import allow_comment

    _note_output(output_format)
    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    inject_locale_rule(ruleset, *_locale_of(config_path or find_config(Path.cwd())))

    rule = ruleset.by_id(rule_id)
    if rule is None:
        console.print(f"[red]unknown rule[/]: {rule_id}")
        raise SystemExit(EXIT_ERROR) from None
    profile_tier = rule.tier_for(profile).value
    severity = _severity_at(console, ruleset, profile, config_path)(rule)

    if output_format == "md":
        click.echo(render_explain(rule, profile, severity), nl=False)
        raise SystemExit(EXIT_OK)

    # Agents and tooling read the exception list to choose a suppression reason, and
    # scraping it out of Rich-rendered text is what this avoids. `suppression` is
    # rendered here rather than left to the caller, because a reason that is not on
    # the closed list is reported as meta.invalid-suppression rather than honoured.
    if output_format == "json":
        payload = {
            **rule.model_dump(mode="json"),
            "id": rule.qualified_id,
            "tiers": {name: tier.value for name, tier in rule.tiers.items()},
            "tier": profile_tier,
            "effective_severity": severity,
        }
        if rule.exceptions:
            payload["suppression"] = allow_comment(rule.qualified_id, rule.exceptions[0])
        click.echo(json.dumps(payload, indent=2))
        raise SystemExit(EXIT_OK)

    console.print(f"[bold]{rule.qualified_id}[/] -- {rule.name}")
    console.print(
        f"kind: {rule.kind.value}   severity: {rule.severity.value}   scope: {rule.scope.value}"
    )
    console.print("tiers: " + "  ".join(f"{k}={v.value}" for k, v in rule.tiers.items()))
    console.print(f"at {profile}: tier {profile_tier}, severity {severity}")
    console.print("\n" + escape(message_text(rule)))
    # A `fix` that only restates the message is noise. `ste-words.spelling` printed
    # 'Use the en-US spelling "<replacement>".' and then 'Fix: Use the en-US spelling.'
    if rule.fix and rule.fix.rstrip(".").lower() not in rule.message.rstrip(".").lower():
        console.print(f"\n[bold]Fix[/]: {rule.fix}")
    if rule.judgement_question:
        console.print(f"\n[bold]Decide by asking[/]: {rule.judgement_question}")
        console.print(
            "Lint never reports this rule; `slopvac prime review` applies it."
        )
    if rule.exceptions:
        console.print("\n[bold]Named exceptions[/] (a suppression must cite one):")
        for name in rule.exceptions:
            console.print(f"  - {name}")
        console.print(f"\n  {allow_comment(rule.qualified_id, rule.exceptions[0])}")
    if rule.examples:
        console.print("\n[bold]Examples[/]")
        for example in rule.examples:
            console.print(f"  [red]-[/] {example.bad}")
            if example.good:
                console.print(f"  [green]+[/] {example.good}")
            if example.note:
                console.print(f"    {escape(example.note)}")
    console.print(f"\n[bold]Source[/]: {rule.provenance.source}")
    if rule.provenance.ste_ref:
        console.print(
            f"  ASD-STE100 rule {rule.provenance.ste_ref.split(':', 1)[1]} (Issue {rule.provenance.ste_ref.split(':', 1)[0]})"
        )
    if rule.provenance.orwell_ref:
        console.print(f"  Orwell rule {escape(rule.provenance.orwell_ref)}")
    if rule.provenance.url:
        console.print(f"  {escape(rule.provenance.url)}")
    if rule.provenance.note:
        console.print(f"  {rule.provenance.note}")


@main.command("init")
@click.option(
    "--profile",
    type=click.Choice([p.value for p in Profile]),
    default="normal",
    help="Profile the new config sets.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing config.")
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    default=Path("slopvac.toml"),
    show_default=True,
    help="Config file to write.",
)
@click.option(
    "--skip-agents",
    is_flag=True,
    help="Write configuration only: no steering block and no skill.",
)
@click.option(
    "--harness",
    "selected",
    multiple=True,
    type=click.Choice(harnesses()),
    help="Write this harness's steering block and slopvac-prose skill. Repeat for "
    "several. Default: the generic AGENTS.md block only.",
)
@click.option(
    "--no-skills",
    is_flag=True,
    help="Write the steering blocks but no slopvac-prose skill.",
)
def init_config(
    profile: str,
    force: bool,
    path: Path,
    skip_agents: bool,
    selected: tuple[str, ...],
    no_skills: bool,
) -> None:
    """Initialize project configuration and agent steering."""
    console = _console(False)
    from .templates import STARTER_CONFIG

    if skip_agents and (selected or no_skills):
        raise click.UsageError(
            "--skip-agents writes no steering; drop --harness and --no-skills."
        )

    if path.exists() and not force:
        console.print(f"[yellow]{path} exists[/]; keeping it.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(STARTER_CONFIG.format(profile=profile), encoding="utf-8")
        console.print(f"wrote {path}")

    if not skip_agents:
        chosen = tuple(dict.fromkeys(selected)) or ("agents",)
        guidance = _guidance_of(path)[0]
        console.print(f"harnesses: {', '.join(chosen)}")
        for name in chosen:
            _install_harness(
                console, path.parent, name, skills=not no_skills, guidance=guidance
            )

    console.print("next: slopvac prime")


def _guidance_of(config_path: Path | None) -> tuple[GuidanceSettings, Path | None]:
    """The `[guidance]` settings and the config file they came from.

    A broken config fails the command rather than falling back to defaults, which
    would tell an agent to run a step the project switched off.
    """
    from .config import ConfigError, GuidanceSettings, load_config

    if config_path is None:
        return GuidanceSettings(), None
    try:
        return load_config(config_path).guidance, config_path
    except ConfigError as exc:
        from rich.markup import escape

        # The console is built only on this error: `prime` prints through click
        # and otherwise never loads rich.
        _console(False).print(f"[red]config error[/]: {escape(str(exc))}")
        raise SystemExit(EXIT_ERROR) from None


def _install_harness(
    console: Console,
    root: Path,
    harness: str,
    *,
    skills: bool,
    guidance: GuidanceSettings,
) -> None:
    """Write one harness's steering block and, unless skipped, its skill stub."""
    from .steering import install_steering, skill_path, sync_skill

    try:
        target, changed = install_steering(root, harness)
        console.print(f"{'updated' if changed else 'kept'} {target} with slopvac steering")
        stub = skill_path(root, harness) if skills else None
        if stub is None:
            return
        changed = sync_skill(stub, wanted=guidance.enabled)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if guidance.enabled:
        console.print(f"{'updated' if changed else 'kept'} {stub}")
    else:
        verb = "removed" if changed else "skipped"
        console.print(f"{verb} {stub} (\\[guidance] write and review are off)")


@main.command("prime")
@click.argument("topic", required=False, type=click.Choice(["write", "review", "report"]))
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Read [guidance] from this file. Default: the nearest slopvac config.",
)
@_rules_dir_option
def prime(topic: str | None, config_path: Path | None, rules_dir: tuple[Path, ...]) -> None:
    """Print current guidance for agents.

    With no TOPIC, print how to use every command, the genres and profiles, and
    when to run the topics. `write` prints the writing guide, `review` prints the
    review workflow, and `report` prints the issue reporting workflow. The first
    two print the `slopvac rules` command for a genre. Prime only prints; it never
    writes files.
    """
    from .config import find_config
    from .guidance import disabled_notice, render_report, render_review, render_write
    from .prime import render_prime

    settings, source = _guidance_of(config_path or find_config(Path.cwd()))
    if topic is None:
        click.echo(render_prime(settings, main), nl=False)
        return
    if getattr(settings, topic) == "off":
        click.echo(disabled_notice(topic, source))
        return
    if topic == "report":
        click.echo(render_report(), nl=False)
        return

    from .rules import RuleLoadError, load_ruleset

    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        _console(False).print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None
    render = render_write if topic == "write" else render_review
    click.echo(render(ruleset, settings), nl=False)


@main.command("onboard")
def onboard() -> None:
    """Print concise setup guidance that points agents to prime."""
    from .steering import ONBOARD_TEXT

    click.echo(ONBOARD_TEXT)


@main.command("setup")
@click.argument("harness", required=False)
@click.option("--list", "list_harnesses", is_flag=True, help="List supported harnesses.")
@click.option(
    "--remove", is_flag=True, help="Remove the managed slopvac block and skill."
)
@click.option(
    "--check",
    is_flag=True,
    help="Report whether the managed block and skill are current without "
    "changing files.",
)
@click.option(
    "--root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Project directory that holds the steering files and config.",
)
def setup_agent(
    harness: str | None,
    list_harnesses: bool,
    remove: bool,
    check: bool,
    root: Path,
) -> None:
    """Install or remove project-local steering for a harness. HARNESS is
    required unless --list is used."""
    from .steering import (
        harness_path,
        managed_block_state,
        remove_managed_block,
        skill_path,
        skill_state,
        sync_skill,
    )

    console = _console(False)
    if list_harnesses:
        try:
            for name in harnesses():
                stub = skill_path(root, name)
                console.print(
                    f"{name:8} {harness_path(root, name)}" + (f"  {stub}" if stub else "")
                )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        raise SystemExit(EXIT_OK)

    if harness is None:
        raise click.UsageError("HARNESS is required unless --list is used.")
    if harness not in harnesses():
        raise click.UsageError(
            f"unknown harness {harness!r}; choose from: {', '.join(harnesses())}"
        )
    if check and remove:
        raise click.UsageError("--check and --remove cannot be used together.")

    try:
        target = harness_path(root, harness)
        stub = skill_path(root, harness)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if check:
        from .config import find_config

        guidance = _guidance_of(find_config(root))[0]
        states = [(managed_block_state(target), target)]
        if stub is not None:
            states.append((skill_state(stub, wanted=guidance.enabled), stub))
        for state, path in states:
            console.print(f"{state} {path}")
        found = {state for state, _ in states}
        if "malformed" in found:
            raise SystemExit(EXIT_ERROR)
        if found <= {"current", "disabled"}:
            raise SystemExit(EXIT_OK)
        raise SystemExit(EXIT_FINDINGS)

    if not remove:
        from .config import find_config

        guidance = _guidance_of(find_config(root))[0]
        _install_harness(console, root, harness, skills=True, guidance=guidance)
        return

    try:
        removed = [(remove_managed_block(target), target)]
        if stub is not None:
            removed.append((sync_skill(stub, wanted=False), stub))
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    for changed, path in removed:
        console.print(f"{'removed from' if changed else 'unchanged'} {path}")


@main.command("compile")
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    help="Where to write the styles. Default: the run cache.",
)
@click.option(
    "--profile",
    type=click.Choice([p.value for p in Profile]),
    default=None,
    help="Override the configured profile.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Config file. Default: the nearest slopvac config.",
)
@_rules_dir_option
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip validating each rule against Vale. Faster, but the routing is unverified.",
)
@_text_or_json_option
def compile_styles(
    outdir: Path | None,
    profile: str | None,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
    no_validate: bool,
    output_format: str,
) -> None:
    """Write the Vale styles and show which engine runs each rule.

    To run Vale by hand: `vale --config=<outdir>/.vale.ini docs/`.
    """
    import json
    import tempfile

    from rich.table import Table

    from .compile_vale import compile_ruleset
    from .config import ConfigError, find_config, load_config, resolve_for
    from .rules import RuleLoadError, inject_locale_rule, load_ruleset
    from .vale_probe import ValeUnavailable
    from .vocabulary import VocabularyError, load_blocklist

    _note_output(output_format)
    console = _console(False)
    discovered = config_path or find_config(Path.cwd())
    try:
        config = load_config(discovered, root=discovered.parent if discovered else None)
    except ConfigError as exc:
        console.print(f"[red]config error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None
    if profile:
        object.__setattr__(config, "profile", Profile(profile))

    try:
        vocabulary = load_blocklist(config.blocklist_path())
    except VocabularyError as exc:
        console.print(f"[red]blocklist error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    inject_locale_rule(ruleset, config.locale.default, config.locale.allow)
    resolved = resolve_for(config, Path("README.md"))

    # An unvalidated tree may hold a rule Vale refuses to load, and one such rule
    # makes Vale lint nothing at all while exiting 0. The compiler therefore refuses
    # to put one in the shared cache, so `--no-validate` without `--outdir` gets a
    # throwaway directory of its own. It is not cleaned up: the path is printed, and
    # inspecting the generated styles is the reason to pass this flag.
    destination = outdir
    if destination is None and no_validate:
        destination = Path(tempfile.mkdtemp(prefix="slopvac-styles-"))

    try:
        result = compile_ruleset(
            ruleset,
            resolved,
            outdir=destination,
            binary=config.vale.binary,
            validate=not no_validate,
            vocabulary=vocabulary,
            force=True,
        )
    except ValeUnavailable as exc:
        console.print(
            f"[red]vale is required to validate the compiled rules[/]: {exc}\n"
            f"Pass --no-validate to compile without proving each rule loads."
        )
        raise SystemExit(EXIT_ERROR) from None

    if output_format == "json":
        click.echo(
            json.dumps(
                {
                    "outdir": str(result.outdir),
                    "config": str(result.config_path),
                    "vale": result.vale_rules,
                    "native": [n.__dict__ for n in result.native_rules],
                    "disabled": result.disabled_rules,
                    # A generated check (vocabulary part of speech, punctuation
                    # companion) and the rule it reports under; without this a
                    # reader sees an id no rule declares.
                    "aliases": result.aliases,
                    "vale_version": result.vale_version,
                },
                indent=2,
            )
        )
        raise SystemExit(EXIT_OK)

    console.print(f"styles: [bold]{result.outdir}[/]")
    console.print(f"config: [bold]{result.config_path}[/]")
    table = Table(header_style="bold", title="routing", title_justify="left")
    table.add_column("engine")
    table.add_column("rules", justify="right")
    table.add_column("why")
    table.add_row("vale", str(result.vale_count), "compiled, load proven")
    table.add_row("native", str(result.native_count), "vale cannot express it")
    table.add_row("none (off)", str(len(result.disabled_rules)), "off in this config")
    console.print(table)

    if result.native_rules:
        console.print("\n[bold]native rules[/]")
        for entry in result.native_rules:
            console.print(f"  {entry.rule_id}  [dim]{entry.reason}[/]")


@main.command("cache")
@click.option(
    "--prune",
    is_flag=True,
    help=f"Delete all but the {CACHE_KEEP} most recently used trees. Lint prunes "
    f"on its own; this forces it now.",
)
@click.option("--all", "prune_all", is_flag=True, help="Delete every compiled tree.")
def cache(prune: bool, prune_all: bool) -> None:
    """Show the compiled-style cache, or prune it.

    A tree's key hashes the rules and the config, so nothing is served stale.
    Pruning only frees disk.
    """
    import json
    from datetime import datetime

    from rich.table import Table

    from .vale_cache import cache_root, prune_cache

    console = _console(False)
    root = cache_root()
    if not root.is_dir():
        console.print(f"no cache at [bold]{root}[/]")
        raise SystemExit(EXIT_OK)

    if prune_all:
        removed = prune_cache(root, keep=0)
        console.print(f"removed {len(removed)} tree(s) from [bold]{root}[/]")
        raise SystemExit(EXIT_OK)
    if prune:
        removed = prune_cache(root)
        console.print(f"removed {len(removed)} tree(s) from [bold]{root}[/]")

    trees = sorted(
        (p for p in root.iterdir() if (p / "manifest.json").is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    total = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    console.print(f"cache: [bold]{root}[/]")
    console.print(f"{len(trees)} tree(s), {total / 1_048_576:.1f} MiB, keep {CACHE_KEEP}")
    if not trees:
        raise SystemExit(EXIT_OK)

    table = Table(header_style="bold", title="compiled trees", title_justify="left")
    table.add_column("fingerprint")
    table.add_column("vale rules", justify="right")
    table.add_column("last used")
    for tree in trees:
        try:
            manifest = json.loads((tree / "manifest.json").read_text(encoding="utf-8"))
            count = str(len(manifest.get("vale_rules", [])))
        except (OSError, json.JSONDecodeError):
            count = "?"
        stamp = datetime.fromtimestamp(tree.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(tree.name, count, stamp)
    console.print(table)
    raise SystemExit(EXIT_OK)


@main.command("reference")
@click.option(
    "--write",
    "destination",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the reference to this path instead of stdout.",
)
@click.option(
    "--check",
    is_flag=True,
    help="Exit 2 if the file at --write differs from what would be generated.",
)
@_rules_dir_option
def reference(destination: Path | None, check: bool, rules_dir: tuple[Path, ...]) -> None:
    """Generate the markdown rules reference.

    `--check` fails when the committed copy has drifted.
    """
    from .reference import render_reference
    from .rules import RuleLoadError, load_ruleset

    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]rule error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    rendered = render_reference(ruleset)

    if check:
        if destination is None:
            console.print("[red]--check needs --write[/] to name the file to compare")
            raise SystemExit(EXIT_ERROR) from None
        current = destination.read_text() if destination.exists() else ""
        if current == rendered:
            console.print(f"[green]{destination} is current[/]")
            raise SystemExit(EXIT_OK)
        # A diff rather than "files differ": the whole point is that whoever hits
        # this in CI can see whether they renamed a rule or dropped one.
        import difflib

        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=f"{destination} (committed)",
            tofile=f"{destination} (generated)",
            n=1,
        )
        sys.stdout.writelines(diff)
        console.print(
            f"\n[red]{destination} is out of date[/]. Regenerate with "
            f"`slopvac reference --write {destination}` and commit the result."
        )
        raise SystemExit(EXIT_ERROR) from None

    if destination is None:
        click.echo(rendered, nl=False)
        raise SystemExit(EXIT_OK)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered)
    console.print(f"wrote [bold]{destination}[/] ({len(ruleset.rules)} rules)")
    raise SystemExit(EXIT_OK)


if __name__ == "__main__":
    main()
