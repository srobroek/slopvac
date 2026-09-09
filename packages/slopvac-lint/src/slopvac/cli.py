"""Command line interface.

EXIT CODES are the contract every caller depends on -- pre-commit, the GitHub
Action, the skill, and CI:

    0  clean, or findings below every configured threshold
    1  a threshold failed (the run worked; the prose did not)
    2  the run could not be trusted: bad config, unloadable ruleset, missing tool

The 1/2 split matters. A pre-commit hook should block on 1 and shout differently
on 2, because 2 means nothing was checked. Warnings alone stay at 0 unless the
project sets `max_warnings`, which preserves the existing gate's behaviour.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .compile_vale import compile_ruleset
from .config import (
    ConfigError,
    Profile,
    Severity,
    find_config,
    load_config,
    resolve_blocklist_path,
    resolve_for,
)
from .model import RuleKind
from .pipeline import (
    EXIT_ERROR,
    EXIT_FINDINGS,
    EXIT_OK,
    PipelineError,
    emit_report,
    load_run_context,
    run_lint,
)
from .reference import render_reference
from .rules import RuleLoadError, inject_locale_rule, load_ruleset
from .vale_cache import CACHE_KEEP, cache_root, prune_cache
from .vale_probe import ValeUnavailable
from .vocabulary import VocabularyError, load_blocklist


def _console(no_color: bool) -> Console:
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
        if args and not any(a in self.commands for a in args):
            if not all(a in self._GROUP_OPTIONS for a in args if a.startswith("-")):
                args = ["lint", *args]
        return super().parse_args(ctx, args)

    def resolve_command(self, ctx: click.Context, args: list[str]):
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["lint", *args]
        return super().resolve_command(ctx, args)


@click.group(cls=_DefaultGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="slopvac")
@click.pass_context
def main(context: click.Context) -> None:
    """Lint prose for AI slop, Simplified Technical English, and Orwell rules.

    `slopvac FILE...` lints. `slopvac rules` lists the rules.
    """
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@main.command()
@click.argument("targets", nargs=-1, required=True)
@click.option(
    "--profile",
    type=click.Choice([p.value for p in Profile]),
    help="Override the configured tier for this run.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Config file. Default: nearest slopvac.toml walking up from each target.",
)
@click.option(
    "--rules-dir",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Extra rule directory, layered over the packaged rules. Repeatable.",
)
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
@click.option("--no-color", is_flag=True, help="Plain output.")
@click.option("--verbose", is_flag=True, help="Show categories with no findings.")
@click.option(
    "--explain-config",
    is_flag=True,
    help="Print the resolved settings per file and exit without linting.",
)
def lint(
    targets: tuple[str, ...],
    profile: str | None,
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
    no_color: bool,
    verbose: bool,
    explain_config: bool,
) -> None:
    """Lint files or directories."""
    console = _console(no_color)
    run = _load_lint_context(
        console,
        targets,
        profile=profile,
        config_path=config_path,
        rules_dir=rules_dir,
        only_categories=only_categories,
        disabled=disabled,
        min_score=min_score,
        max_per_100_words=max_per_100_words,
        locale_tag=locale_tag,
    )
    if not run.paths:
        console.print("[yellow]no lintable files matched[/]")
        raise SystemExit(EXIT_OK)
    if explain_config:
        _print_resolved_config(run, console)
        raise SystemExit(EXIT_OK)

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
    )
    if any(score.unchecked for score in scores):
        raise SystemExit(EXIT_ERROR)
    raise SystemExit(EXIT_OK if all(score.passed for score in scores) else EXIT_FINDINGS)


def _format_was_given() -> bool:
    return (
        click.get_current_context().get_parameter_source("output_format")
        is not click.core.ParameterSource.DEFAULT
    )


def _load_lint_context(console: Console, targets: tuple[str, ...], **options):
    try:
        return load_run_context(targets, **options)
    except PipelineError as exc:
        for message in exc.messages:
            console.print(message)
        raise SystemExit(exc.code) from None


def _run_lint_or_exit(run, console: Console, *, no_vale: bool):
    try:
        return run_lint(run, no_vale=no_vale)
    except PipelineError as exc:
        for message in exc.messages:
            console.print(message)
        raise SystemExit(exc.code) from None


def _print_resolved_config(run, console: Console) -> None:
    for path in run.paths:
        resolved = resolve_for(run.config, path)
        console.print(f"[bold]{path}[/]")
        console.print(f"  profile: {resolved.profile.value}")
        if resolved.applied_overrides:
            console.print(f"  overrides: {', '.join(resolved.applied_overrides)}")
        console.print(
            f"  thresholds: {resolved.thresholds.model_dump(exclude_none=True)}"
        )
        blocklist = resolve_blocklist_path(resolved.vocabulary, run.config.root)
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
    try:
        config = load_config(
            config_path, root=config_path.parent if config_path else None
        )
    except ConfigError:
        return "en-US", None
    return config.locale.default, config.locale.allow


@main.command("rules")
@click.option(
    "--profile", type=click.Choice([p.value for p in Profile]), default="normal"
)
@click.option("--category", "only", multiple=True, help="Limit to these categories.")
@click.option(
    "--kind", type=click.Choice([k.value for k in RuleKind]), help="Filter by kind."
)
@click.option("--judgement", is_flag=True, help="Only the rules a linter cannot check.")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text"
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--rules-dir",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
def list_rules(
    profile: str,
    only: tuple[str, ...],
    kind: str | None,
    judgement: bool,
    output_format: str,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
) -> None:
    """List the rules and whether each is on at a profile.

    `--judgement` lists only the rules a reader must decide.
    """
    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    inject_locale_rule(ruleset, *_locale_of(config_path or find_config(Path.cwd())))

    selected = [
        rule
        for rule in ruleset.rules
        if (not only or rule.category in only)
        and (not kind or rule.kind.value == kind)
        and (not judgement or rule.kind is RuleKind.JUDGEMENT)
    ]

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
            rule.severity.value,
            rule.provenance.ste_ref
            or rule.provenance.orwell_ref
            or rule.provenance.source,
        )
    console.print(table)
    console.print(f"{len(selected)} rule(s) in {len(ruleset.categories)} category(ies)")


@main.command()
@click.argument("rule_id")
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text"
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--rules-dir",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
def explain(
    rule_id: str,
    output_format: str,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
) -> None:
    """Show one rule in full."""
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

    # The review skill reads the exception list to choose a suppression reason, and
    # scraping it out of Rich-rendered text is what this avoids. `suppression` is
    # rendered here rather than left to the caller, because a reason that is not on
    # the closed list is reported as meta.invalid-suppression rather than honoured.
    if output_format == "json":
        payload = {
            **rule.model_dump(mode="json"),
            "id": rule.qualified_id,
            "tiers": {name: tier.value for name, tier in rule.tiers.items()},
        }
        if rule.exceptions:
            payload["suppression"] = (
                f"<!-- slopvac-allow: rule={rule.qualified_id} "
                f"reason={rule.exceptions[0]} -->"
            )
        click.echo(json.dumps(payload, indent=2))
        raise SystemExit(EXIT_OK)

    console.print(f"[bold]{rule.qualified_id}[/] -- {rule.name}")
    console.print(
        f"kind: {rule.kind.value}   severity: {rule.severity.value}   scope: {rule.scope.value}"
    )
    console.print("tiers: " + "  ".join(f"{k}={v.value}" for k, v in rule.tiers.items()))
    # `message` is a template. Printed raw it shows `{replacement}`, which reads as a
    # bug; the slots are shown as `<name>` so it is clear they are filled per finding.
    console.print("\n" + rule.message.replace("{", "<").replace("}", ">"))
    # A `fix` that only restates the message is noise. `ste-words.spelling` printed
    # 'Use the en-US spelling "<replacement>".' and then 'Fix: Use the en-US spelling.'
    if rule.fix and rule.fix.rstrip(".").lower() not in rule.message.rstrip(".").lower():
        console.print(f"\n[bold]Fix[/]: {rule.fix}")
    if rule.judgement_question:
        console.print(f"\n[bold]Decide by asking[/]: {rule.judgement_question}")
    if rule.exceptions:
        console.print("\n[bold]Named exceptions[/] (a suppression must cite one):")
        for name in rule.exceptions:
            console.print(f"  - {name}")
        console.print(
            f"\n  <!-- slopvac-allow: rule={rule.qualified_id} reason={rule.exceptions[0]} -->"
        )
    if rule.examples:
        console.print("\n[bold]Examples[/]")
        for example in rule.examples:
            console.print(f"  [red]-[/] {example.bad}")
            if example.good:
                console.print(f"  [green]+[/] {example.good}")
    console.print(f"\n[bold]Source[/]: {rule.provenance.source}")
    if rule.provenance.ste_ref:
        console.print(
            f"  ASD-STE100 rule {rule.provenance.ste_ref.split(':', 1)[1]} (Issue {rule.provenance.ste_ref.split(':', 1)[0]})"
        )
    if rule.provenance.note:
        console.print(f"  {rule.provenance.note}")


@main.command("init")
@click.option(
    "--profile", type=click.Choice([p.value for p in Profile]), default="normal"
)
@click.option("--force", is_flag=True, help="Overwrite an existing config.")
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    default=Path("slopvac.toml"),
    show_default=True,
)
def init_config(profile: str, force: bool, path: Path) -> None:
    """Write a starter slopvac.toml."""
    console = _console(False)
    if path.exists() and not force:
        console.print(f"[yellow]{path} exists[/]; pass --force to overwrite.")
        raise SystemExit(EXIT_OK)

    from .templates import STARTER_CONFIG

    path.write_text(STARTER_CONFIG.format(profile=profile), encoding="utf-8")
    console.print(f"wrote {path}")
    console.print("lint with: slopvac 'docs/**/*.md'")


@main.command("compile")
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    help="Where to write the styles. Default: the run cache.",
)
@click.option("--profile", type=click.Choice([p.value for p in Profile]), default=None)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--rules-dir",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip validating each rule against Vale. Faster, but the routing is unverified.",
)
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json"]), default="text"
)
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
                    "judgement": result.judgement_rules,
                    "disabled": result.disabled_rules,
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
    table.add_row("none (judgement)", str(len(result.judgement_rules)), "needs a reader")
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
@click.option(
    "--rules-dir",
    multiple=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
def reference(destination: Path | None, check: bool, rules_dir: tuple[Path, ...]) -> None:
    """Generate the markdown rules reference.

    `--check` fails when the committed copy has drifted.
    """
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
