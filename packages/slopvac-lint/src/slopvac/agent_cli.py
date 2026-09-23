"""Project setup and progressive disclosure for agent harnesses."""

from __future__ import annotations

import json
from pathlib import Path

import click

from .agent_context import GENRES, context
from .config import Profile
from .rules import RuleLoadError, load_ruleset
from .steering import (
    HARNESS_PATHS,
    Edit,
    SteeringError,
    apply_edits,
    plan_steering,
    snippet,
)
from .templates import STARTER_CONFIG


class SetupError(click.ClickException):
    exit_code = 2


def _report(edits: list[Edit], dry_run: bool) -> None:
    for edit in edits:
        status = "unchanged" if not edit.changed else "would write" if dry_run else "wrote"
        click.echo(f"{status} {edit.path}")


@click.command("init")
@click.option("--profile", type=click.Choice([p.value for p in Profile]), default="normal")
@click.option("--force", is_flag=True, help="Replace only an existing configuration file.")
@click.option("--path", type=click.Path(path_type=Path), default=Path("slopvac.toml"), show_default=True)
@click.option("--harness", "harnesses", type=click.Choice(list(HARNESS_PATHS)), multiple=True,
              help="Install project steering for this harness. Repeatable; default: generic.")
@click.option("--skip-agents", is_flag=True, help="Write configuration without agent steering.")
@click.option("--dry-run", is_flag=True, help="Show file changes without writing them.")
def init_config(profile: str, force: bool, path: Path, harnesses: tuple[str, ...],
                skip_agents: bool, dry_run: bool) -> None:
    """Create configuration and CLI-based agent steering for a project."""
    if skip_agents and harnesses:
        raise click.UsageError("--skip-agents cannot be combined with --harness")
    try:
        # Do not follow a configuration symlink outside the selected project.
        root = path.absolute().parent.resolve()
        target = path.resolve()
        target.relative_to(root)
        if target.exists() and not target.is_file():
            raise SteeringError(f"not a regular configuration file: {path}")
        before = target.read_bytes() if target.exists() else None
        after = STARTER_CONFIG.format(profile=profile).encode("utf-8")
        config_edit = Edit(target, before, before if before is not None and not force else after)
        edits = [config_edit]
        if not skip_agents:
            edits.extend(plan_steering(root, harnesses or ("generic",)))
        if len({edit.path for edit in edits}) != len(edits):
            raise SteeringError("configuration and steering cannot use the same path")
        if not dry_run:
            apply_edits(edits)
        _report(edits, dry_run)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SetupError(str(exc)) from None
    click.echo("Lint with: slopvac README.md\nAgent guidance: slopvac prime")


@click.command("setup")
@click.argument("harness", required=False, type=click.Choice(list(HARNESS_PATHS)))
@click.option("--root", type=click.Path(file_okay=False, path_type=Path), default=Path("."), show_default=True)
@click.option("--list", "list_harnesses", is_flag=True, help="List harnesses and project destinations.")
@click.option("--check", is_flag=True, help="Check managed steering without writing. Exit 1 if absent or stale.")
@click.option("--remove", is_flag=True, help="Remove only the Slopvac-managed section.")
@click.option("--dry-run", is_flag=True, help="Show file changes without writing them.")
def setup(harness: str | None, root: Path, list_harnesses: bool, check: bool,
          remove: bool, dry_run: bool) -> None:
    """Install, refresh, check, or remove project harness steering."""
    if list_harnesses:
        if harness or check or remove or dry_run:
            raise click.UsageError("--list cannot be combined with a harness or an operation")
        for name, path in HARNESS_PATHS.items():
            click.echo(f"{name}\t{path}")
        return
    if not harness:
        raise click.UsageError("choose a harness, or use --list")
    if check and (remove or dry_run):
        raise click.UsageError("--check cannot be combined with --remove or --dry-run")
    try:
        edits = plan_steering(root, (harness,), remove=remove)
        if check:
            current = all(not edit.changed for edit in edits)
            click.echo("current" if current else "missing or stale; run slopvac setup " + harness)
            raise SystemExit(0 if current else 1)
        if not dry_run:
            apply_edits(edits)
        _report(edits, dry_run)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SetupError(str(exc)) from None


@click.command("onboard")
def onboard() -> None:
    """Print the short steering section for an unsupported harness. No writes."""
    click.echo(snippet(), nl=False)


@click.command("prime")
@click.argument("topic", type=click.Choice(["all", "overview", "lint", "judgement"]), default="all")
@click.option("--genre", type=click.Choice(GENRES), help="Show catalog categories recommended for this genre.")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def prime(topic: str, genre: str | None, output_format: str) -> None:
    """Print lint and judgement workflow details without running a review."""
    try:
        payload = context(topic, load_ruleset(), genre)
    except RuleLoadError as exc:
        raise SetupError(str(exc)) from None
    if output_format == "json":
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(payload["guidance"], nl=False)
        if genre:
            click.echo(f"\nCatalog categories recommended for {genre}:\n")
            for category in payload["categories"]:
                click.echo(f"- `{category['id']}`")
