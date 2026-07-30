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

import fnmatch
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .analyze import parse
from .config import Config, ConfigError, Profile, Severity, find_config, load_config, resolve_for
from .engine import Engine
from .model import DocumentScore, RuleKind
from .rules import RuleLoadError, RuleSet, inject_locale_rule, load_ruleset
from .score import aggregate, score_document
from .vale import ValeResult, run_vale

LINTABLE = ("*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.html")

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


def _console(no_color: bool) -> Console:
    # force_terminal=False lets rich detect a pipe and drop styling, so piped
    # output stays greppable.
    return Console(no_color=no_color, soft_wrap=True, stderr=False)


def _collect_paths(targets: tuple[str, ...], config: Config) -> list[Path]:
    """Expand directories, apply the exclude list, keep only lintable files."""
    found: list[Path] = []
    root = config.root or Path.cwd()

    for target in targets:
        path = Path(target)
        if path.is_dir():
            for pattern in LINTABLE:
                found.extend(sorted(path.rglob(pattern)))
        elif path.is_file():
            found.append(path)
        else:
            # A glob the shell did not expand.
            matches = sorted(Path().glob(target))
            if not matches:
                raise click.ClickException(f"no such file or directory: {target}")
            found.extend(m for m in matches if m.is_file())

    kept: list[Path] = []
    for path in found:
        try:
            relative = str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            relative = path.name
        if config.is_excluded(relative):
            continue
        if not any(fnmatch.fnmatch(path.name, p) for p in LINTABLE):
            continue
        kept.append(path)

    # Deduplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in kept:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _lint_one(
    path: Path, config: Config, ruleset: RuleSet, vale_result: ValeResult | None
) -> DocumentScore:
    resolved = resolve_for(config, path)
    text = path.read_text(encoding="utf-8", errors="replace")
    document = parse(str(path), text)

    engine = Engine(ruleset.rules, resolved)
    findings = engine.run(document)

    unchecked: list[str] = []
    if vale_result is not None:
        findings.extend(vale_result.findings_for(str(path)))
        unchecked.extend(vale_result.unchecked)

    return score_document(
        path=str(path),
        findings=findings,
        words=document.words,
        sentences=len(document.sentences),
        paragraphs=len(document.paragraphs),
        config=resolved,
        categories_meta=ruleset.weights,
        unchecked=unchecked,
    )


def _report_text(scores: list[DocumentScore], console: Console, verbose: bool) -> None:
    for score in scores:
        for finding in score.findings:
            console.print(finding.as_line(), highlight=False)
        for note in score.unchecked:
            console.print(f"[yellow]UNCHECKED[/] {score.path}: {note}")

    summary = aggregate(scores)
    console.print()
    table = Table(title="slopvac", title_justify="left", header_style="bold")
    table.add_column("category")
    table.add_column("findings", justify="right")
    table.add_column("err", justify="right")
    table.add_column("warn", justify="right")
    table.add_column("/100w", justify="right")
    table.add_column("score", justify="right")

    for entry in summary["categories"]:  # type: ignore[index]
        if not verbose and entry["findings"] == 0:
            continue
        table.add_row(
            entry["category"],
            str(entry["findings"]),
            str(entry["errors"]),
            str(entry["warnings"]),
            f"{entry['per_100_words']:.2f}",
            f"{entry['score']:.0f}",
        )
    if table.row_count:
        console.print(table)

    verdict = "[green]PASS[/]" if summary["passed"] else "[red]FAIL[/]"
    console.print(
        f"{verdict}  score [bold]{summary['score']}[/]/100  "
        f"{summary['findings']} finding(s) "
        f"({summary['errors']} error, {summary['warnings']} warning, "
        f"{summary['suggestions']} suggestion) "
        f"across {summary['documents']} file(s), {summary['words']} words  "
        f"= {summary['per_100_words']:.2f}/100w"
    )
    for score in scores:
        for reason in score.failure_reasons:
            console.print(f"  [red]x[/] {score.path}: {reason}")


class _DefaultGroup(click.Group):
    """Treat an unrecognised first argument as a path for `lint`.

    `slopvac-lint README.md` has to work: it is what a reader tries first, what
    the pre-commit hook passes (staged filenames, positionally), and what the
    GitHub Action forwards. Without this, click reports the filename as an
    unknown command and exits 2, which a caller reads as "the run could not be
    trusted".
    """

    def resolve_command(self, ctx: click.Context, args: list[str]):
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["lint", *args]
        return super().resolve_command(ctx, args)


@click.group(cls=_DefaultGroup, invoke_without_command=True)
@click.version_option(__version__, prog_name="slopvac-lint")
@click.pass_context
def main(context: click.Context) -> None:
    """Score prose against AI-slop, Simplified Technical English, and Orwell rules.

    Run with paths to lint them; `slopvac-lint rules` lists the ruleset.
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
    type=click.Choice(["text", "json", "github", "sarif"]),
    default="text",
    help="text for humans, json for tooling, github for Action annotations.",
)
@click.option("--min-score", type=float, help="Fail below this 0-100 score.")
@click.option(
    "--max-per-100-words", type=float, help="Fail above this finding density."
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

    first = Path(targets[0])
    discovered = config_path or find_config(first if first.exists() else Path.cwd())
    try:
        config = load_config(discovered, root=discovered.parent if discovered else None)
    except ConfigError as exc:
        console.print(f"[red]config error[/]: {exc}")
        raise SystemExit(EXIT_ERROR)

    if profile:
        object.__setattr__(config, "profile", Profile(profile))
    if min_score is not None:
        config.thresholds.min_score = min_score
    if max_per_100_words is not None:
        config.thresholds.max_total_per_100_words = max_per_100_words
    if locale_tag:
        config.locale.default = locale_tag

    # CLI disables are the last word, applied as config so the normal
    # precedence chain still reports them under --explain-config.
    from .config import CategorySettings, RuleSettings

    for entry in disabled:
        if "." in entry:
            config.rules[entry] = RuleSettings(severity=Severity.OFF)
        else:
            config.categories[entry] = CategorySettings(enabled=False)

    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR)

    # The spelling rule is generated from the locale, so it is added after the
    # YAML loads. A bad tag becomes an `unchecked` note rather than an exception:
    # a typo here must not stop the other 200 rules from running.
    locale_note = inject_locale_rule(
        ruleset, config.locale.default, config.locale.allow
    )

    if only_categories:
        keep = set(only_categories)
        unknown = keep - set(ruleset.categories)
        if unknown:
            console.print(
                f"[red]unknown category[/]: {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(ruleset.categories))}"
            )
            raise SystemExit(EXIT_ERROR)
        for name in list(ruleset.categories):
            if name not in keep:
                config.categories[name] = CategorySettings(enabled=False)

    try:
        paths = _collect_paths(targets, config)
    except click.ClickException as exc:
        console.print(f"[red]{exc.message}[/]")
        raise SystemExit(EXIT_ERROR)

    if not paths:
        console.print("[yellow]no lintable files matched[/]")
        raise SystemExit(EXIT_OK)

    if explain_config:
        for path in paths:
            resolved = resolve_for(config, path)
            console.print(f"[bold]{path}[/]")
            console.print(f"  profile: {resolved.profile.value}")
            if resolved.applied_overrides:
                console.print(f"  overrides: {', '.join(resolved.applied_overrides)}")
            console.print(f"  thresholds: {resolved.thresholds.model_dump(exclude_none=True)}")
            off = [n for n, c in resolved.categories.items() if c.enabled is False]
            if off:
                console.print(f"  disabled: {', '.join(sorted(off))}")
        raise SystemExit(EXIT_OK)

    vale_result = None
    if config.vale.enabled and not no_vale:
        vale_result = run_vale(paths, config)

    scores = [_lint_one(p, config, ruleset, vale_result) for p in paths]
    if locale_note:
        for score in scores:
            score.unchecked.append(locale_note)

    if output_format == "json":
        payload = {
            "version": __version__,
            "summary": aggregate(scores),
            "documents": [s.model_dump() for s in scores],
        }
        click.echo(json.dumps(payload, indent=2, default=str))
    elif output_format == "github":
        # Workflow-command annotations, so findings land on the PR diff.
        for score in scores:
            for finding in score.findings:
                level = "error" if finding.severity is Severity.ERROR else "warning"
                click.echo(
                    f"::{level} file={finding.path},line={finding.line},"
                    f"col={finding.column},title={finding.rule_id}::{finding.message}"
                )
        summary = aggregate(scores)
        click.echo(
            f"::notice title=slopvac::score {summary['score']}/100, "
            f"{summary['findings']} finding(s), "
            f"{summary['per_100_words']:.2f} per 100 words"
        )
    elif output_format == "sarif":
        click.echo(json.dumps(_sarif(scores, ruleset), indent=2))
    else:
        _report_text(scores, console, verbose)

    raise SystemExit(EXIT_OK if all(s.passed for s in scores) else EXIT_FINDINGS)


def _sarif(scores: list[DocumentScore], ruleset: RuleSet) -> dict:
    """SARIF 2.1.0, so GitHub code scanning can ingest the findings."""
    rules = [
        {
            "id": rule.qualified_id,
            "name": rule.name,
            "shortDescription": {"text": rule.name},
            "fullDescription": {"text": rule.fix or rule.name},
            "properties": {
                "category": rule.category,
                "ste_ref": rule.provenance.ste_ref,
                "orwell_ref": rule.provenance.orwell_ref,
            },
        }
        for rule in ruleset.rules
        if rule.kind is not RuleKind.JUDGEMENT
    ]
    results = []
    for score in scores:
        for finding in score.findings:
            results.append(
                {
                    "ruleId": finding.rule_id,
                    "level": "error" if finding.severity is Severity.ERROR else "warning",
                    "message": {"text": finding.message},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": finding.path},
                                "region": {
                                    "startLine": finding.line,
                                    "startColumn": finding.column,
                                },
                            }
                        }
                    ],
                }
            )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "slopvac-lint",
                        "version": __version__,
                        "informationUri": "https://github.com/srobroek/slopvac",
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }


@main.command("rules")
@click.option("--profile", type=click.Choice([p.value for p in Profile]), default="normal")
@click.option("--category", "only", multiple=True, help="Limit to these categories.")
@click.option("--kind", type=click.Choice([k.value for k in RuleKind]), help="Filter by kind.")
@click.option("--judgement", is_flag=True, help="Only the rules a linter cannot check.")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--rules-dir", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def list_rules(
    profile: str,
    only: tuple[str, ...],
    kind: str | None,
    judgement: bool,
    output_format: str,
    rules_dir: tuple[Path, ...],
) -> None:
    """List the ruleset, with each rule's disposition at a profile.

    `--judgement` is what the agentic reviewer reads: the rules carried as
    decidable questions because no pattern reaches them.
    """
    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR)

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
            rule.provenance.ste_ref or rule.provenance.orwell_ref or rule.provenance.source,
        )
    console.print(table)
    console.print(f"{len(selected)} rule(s) in {len(ruleset.categories)} category(ies)")


@main.command()
@click.argument("rule_id")
@click.option("--rules-dir", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def explain(rule_id: str, rules_dir: tuple[Path, ...]) -> None:
    """Show one rule in full: why it exists, its exceptions, and its examples."""
    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR)

    rule = ruleset.by_id(rule_id)
    if rule is None:
        console.print(f"[red]unknown rule[/]: {rule_id}")
        raise SystemExit(EXIT_ERROR)

    console.print(f"[bold]{rule.qualified_id}[/] -- {rule.name}")
    console.print(f"kind: {rule.kind.value}   severity: {rule.severity.value}   scope: {rule.scope.value}")
    console.print(f"tiers: " + "  ".join(f"{k}={v.value}" for k, v in rule.tiers.items()))
    console.print(f"\n{rule.message}")
    if rule.fix:
        console.print(f"\n[bold]Fix[/]: {rule.fix}")
    if rule.judgement_question:
        console.print(f"\n[bold]Decide by asking[/]: {rule.judgement_question}")
    if rule.exceptions:
        console.print(f"\n[bold]Named exceptions[/] (a suppression must cite one):")
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
        console.print(f"  ASD-STE100 rule {rule.provenance.ste_ref.split(':', 1)[1]} (Issue {rule.provenance.ste_ref.split(':', 1)[0]})")
    if rule.provenance.note:
        console.print(f"  {rule.provenance.note}")


@main.command("init")
@click.option("--profile", type=click.Choice([p.value for p in Profile]), default="normal")
@click.option("--force", is_flag=True, help="Overwrite an existing config.")
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    default=Path("slopvac.toml"),
    show_default=True,
)
def init_config(profile: str, force: bool, path: Path) -> None:
    """Write a starter slopvac.toml with the common overrides commented out."""
    console = _console(False)
    if path.exists() and not force:
        console.print(f"[yellow]{path} exists[/]; pass --force to overwrite.")
        raise SystemExit(EXIT_OK)

    from .templates import STARTER_CONFIG

    path.write_text(STARTER_CONFIG.format(profile=profile), encoding="utf-8")
    console.print(f"wrote {path}")
    console.print(f"lint with: slopvac-lint 'docs/**/*.md'")


if __name__ == "__main__":
    main()
