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
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .analyze import parse
from .compile_vale import (
    CACHE_KEEP,
    CompileResult,
    ValeUnavailable,
    cache_root,
    compile_ruleset,
    prune_cache,
)
from .config import (
    Config,
    ConfigError,
    Profile,
    Severity,
    find_config,
    load_config,
    resolve_blocklist_path,
    resolve_for,
)
from .engine import Engine, drop_quoted_illustrations
from .html import render_html
from .model import DocumentScore, RuleKind
from .reference import render_reference
from .report import LintReport, build_sarif, summarize
from .rules import RuleLoadError, RuleSet, inject_locale_rule, load_ruleset
from .score import score_document
from .vale import ValeResult, run_compiled_vale, unchecked_for_skipped
from .vocabulary import Vocabulary, VocabularyError, load_blocklist

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
    path: Path,
    config: Config,
    ruleset: RuleSet,
    vale_result: ValeResult | None,
    extra_unchecked: list[str] | None = None,
    native_only: set[str] | None = None,
) -> DocumentScore:
    resolved = resolve_for(config, path)
    text = path.read_text(encoding="utf-8", errors="replace")
    document = parse(str(path), text)

    # THE TWO ENGINES PARTITION THE RULESET. `native_only` names the rules Vale did
    # not take; without it both engines run everything and every finding is
    # reported twice.
    engine = Engine(ruleset.rules, resolved, only=native_only)
    findings = engine.run(document)

    unchecked: list[str] = list(extra_unchecked or [])
    # A metric rule with no implementation matches nothing and would otherwise
    # read as compliant prose.
    missing = engine.unimplemented_metrics()
    if missing:
        unchecked.append(
            f"{len(missing)} metric rule(s) have no implementation in either "
            f"engine, so they did NOT run: {', '.join(missing)}"
        )
    if vale_result is not None:
        # Vale has no notion of our exception list, so the `quotation` exception has
        # to be applied on this side or it holds for only half the ruleset. Before
        # this, the project's own steering document drew 7 errors and every one was
        # the phrase it was forbidding: a style guide could not pass its own gate.
        findings.extend(
            drop_quoted_illustrations(
                vale_result.findings_for(str(path)), document, ruleset
            )
        )
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


def _compile_for(
    sample: Path,
    config: Config,
    ruleset: RuleSet,
    console: Console,
    vocabulary: Vocabulary,
) -> tuple[CompileResult | None, list[str]]:
    """Compile the ruleset for `sample`'s resolved config.

    Returns `(None, notes)` when Vale is unusable, so the caller reports the gap
    rather than dying: the native rules still run, and a linter that refuses to
    start because a Go binary is missing is worse than one that says what it
    skipped.
    """
    resolved = resolve_for(config, sample)
    try:
        return compile_ruleset(
            ruleset,
            resolved,
            binary=config.vale.binary,
            validate=True,
            vocabulary=vocabulary,
        ), []
    except ValeUnavailable as exc:
        return None, [
            f"the Vale styles were not compiled ({exc}), so every rule that runs "
            f"in Vale did NOT run. Install vale, or pass --no-vale to acknowledge "
            f"the gap explicitly."
        ]


def _suggest(unknown: str, known: set[str]) -> str:
    """The closest known name, for a did-you-mean. Empty when nothing is close."""
    import difflib

    match = difflib.get_close_matches(unknown, sorted(known), n=1, cutoff=0.7)
    return f" Did you mean `{match[0]}`?" if match else ""


def _validate_names(config: Config, ruleset: RuleSet) -> list[str]:
    """Every category and rule id the config names must exist. Returns the errors.

    THE SILENT NO-OP THIS CLOSES. `extra="forbid"` protects the FIELD names inside
    a settings table, and nothing protected the MAP KEY. So
    `[rules."prose-format.no-unicode-dashes"]` -- plural, a typo -- validated
    cleanly and did nothing, in the one place a reader hand-types a
    forty-character string. The failure mode is the worst available: "I disabled
    it and the gate still fails."

    Run against the INJECTED ruleset, so the generated spelling rule counts as
    known. Checked across every layer including each `[[overrides]]` block, since a
    typo in an override is no more visible than one at the top level.
    """
    known_categories = set(ruleset.categories)
    known_rules = {rule.qualified_id for rule in ruleset.rules}
    errors: list[str] = []

    def check(categories: dict, rules: dict, where: str) -> None:
        for name in sorted(categories):
            if name not in known_categories:
                errors.append(
                    f"{where}: unknown category `{name}`."
                    f"{_suggest(name, known_categories)}"
                )
        for name in sorted(rules):
            if name in known_rules:
                continue
            # A bare rule name is the likeliest mistake, so name the qualified form
            # rather than only rejecting it.
            if "." not in name:
                candidates = sorted(r for r in known_rules if r.split(".", 1)[1] == name)
                hint = (
                    f" A rule id is qualified: try `{candidates[0]}`."
                    if candidates
                    else " A rule id is `<category>.<rule>`; a bare category name "
                    "belongs in [categories]."
                )
                errors.append(f"{where}: unknown rule `{name}`.{hint}")
            else:
                errors.append(
                    f"{where}: unknown rule `{name}`.{_suggest(name, known_rules)}"
                )

    check(config.categories, config.rules, "config")
    for index, override in enumerate(config.overrides):
        check(
            override.categories,
            override.rules,
            f"overrides[{index}] ({', '.join(override.files)})",
        )
    return errors


def _vale_levels(
    compiled: CompileResult, ruleset: RuleSet, config: Config, sample: Path
) -> tuple[dict[str, Severity], dict[str, str]]:
    """Our resolved severity and category per compiled rule id.

    Vale reports the level we told it to, but ours stays authoritative: resolving
    here rather than trusting the echo means an ini bug surfaces as a mismatch
    instead of quietly changing what the gate blocks on.
    """
    resolved = resolve_for(config, sample)
    engine = Engine(ruleset.rules, resolved)
    by_id = {r.qualified_id: r for r in ruleset.rules}

    severities: dict[str, Severity] = {}
    categories: dict[str, str] = {}
    for rule_id in compiled.vale_rules:
        # A generated rule reports under the rule that owns it, so its severity
        # and category come from that rule rather than from its own name.
        owner = compiled.aliases.get(rule_id, rule_id)
        rule = by_id.get(owner)
        if rule is None:
            categories[rule_id] = rule_id.split(".", 1)[0]
            severities[rule_id] = Severity.WARNING
            continue
        severities[rule_id] = engine.severity_for(rule)
        categories[rule_id] = rule.category
    return severities, categories


def _report_text(scores: list[DocumentScore], console: Console, verbose: bool) -> None:
    for score in scores:
        for finding in score.findings:
            console.print(finding.as_line(), highlight=False)
        for note in score.unchecked:
            console.print(f"[yellow]UNCHECKED[/] {score.path}: {note}")

    summary = summarize(scores)
    console.print()
    table = Table(title="slopvac", title_justify="left", header_style="bold")
    table.add_column("category")
    table.add_column("findings", justify="right")
    table.add_column("err", justify="right")
    table.add_column("warn", justify="right")
    table.add_column("/100w", justify="right")
    table.add_column("score", justify="right")

    for entry in summary.categories:
        if not verbose and entry.findings == 0:
            continue
        table.add_row(
            entry.category,
            str(entry.findings),
            str(entry.errors),
            str(entry.warnings),
            f"{entry.per_100_words:.2f}",
            f"{entry.score:.0f}",
        )
    if table.row_count:
        console.print(table)

    verdict = "[green]PASS[/]" if summary.passed else "[red]FAIL[/]"
    console.print(
        f"{verdict}  score [bold]{summary.score}[/]/100  "
        f"{summary.findings} finding(s) "
        f"({summary.errors} error, {summary.warnings} warning, "
        f"{summary.suggestions} suggestion) "
        f"across {summary.documents} file(s), {summary.words} words  "
        f"= {summary.per_100_words:.2f}/100w"
    )
    for score in scores:
        for reason in score.failure_reasons:
            console.print(f"  [red]x[/] {score.path}: {reason}")


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
    """Score prose against AI-slop, Simplified Technical English, and Orwell rules.

    Run with paths to lint them; `slopvac rules` lists the ruleset.
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
    "html for a self-contained report.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the report here instead of stdout. Implied by --open.",
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

    first = Path(targets[0])
    discovered = config_path or find_config(first if first.exists() else Path.cwd())
    try:
        config = load_config(discovered, root=discovered.parent if discovered else None)
    except ConfigError as exc:
        console.print(f"[red]config error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

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
            config.categories[entry] = CategorySettings(severity=Severity.OFF)

    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]ruleset error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    # The spelling rule is generated from the locale, so it is added after the
    # YAML loads. A bad tag becomes an `unchecked` note rather than an exception:
    # a typo here must not stop the other 200 rules from running.
    locale_note = inject_locale_rule(
        ruleset, config.locale.default, config.locale.allow
    )

    # Before anything runs, and EXIT_ERROR rather than a warning: a project that
    # believes it disabled a rule has to hear that it did not.
    name_errors = _validate_names(config, ruleset)
    if name_errors:
        for message in name_errors:
            console.print(f"[red]config error[/] {message}")
        raise SystemExit(EXIT_ERROR) from None

    if only_categories:
        keep = set(only_categories)
        unknown = keep - set(ruleset.categories)
        if unknown:
            console.print(
                f"[red]unknown category[/]: {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(ruleset.categories))}"
            )
            raise SystemExit(EXIT_ERROR) from None
        for name in list(ruleset.categories):
            if name not in keep:
                config.categories[name] = CategorySettings(severity=Severity.OFF)

    try:
        paths = _collect_paths(targets, config)
    except click.ClickException as exc:
        console.print(f"[red]{exc.message}[/]")
        raise SystemExit(EXIT_ERROR) from None

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
            blocklist = resolve_blocklist_path(resolved.vocabulary, config.root)
            if blocklist is not None:
                console.print(f"  blocklist: {blocklist}")
            off = [
                n
                for n, c in resolved.categories.items()
                if c.severity is Severity.OFF
            ]
            if off:
                console.print(f"  disabled: {', '.join(sorted(off))}")

            # WHICH BLOCK WON, per setting. Resolution is a cascade in file order,
            # so with two overlapping globs the answer to "why is this rule still
            # on" is otherwise an inference over every block in the file -- and the
            # BROADER pattern wins if it comes later, which is the opposite of what
            # a reader assumes. Listing only settings some layer actually touched:
            # the ~30 untouched profile defaults would bury the handful that matter.
            if resolved.provenance:
                console.print("  set by:")
                for setting, where in sorted(resolved.provenance.items()):
                    console.print(f"    {setting}: {where}")
        raise SystemExit(EXIT_OK)

    # Loaded HERE, not lazily at compile time, so a broken blocklist is reported
    # before any file is read. A configured-but-unloadable wordlist is a config
    # error like any other: the project asked for the gate by name, and linting on
    # with it silently empty would report every document clean.
    #
    # ONE LOAD PER DISTINCT BLOCKLIST, because `[[overrides]]` can point a subtree
    # at its own wordlist and the Vale compile BAKES THE WORDLIST IN. Keying the
    # compile on the first file's resolution would have silently applied the root
    # wordlist to every path -- the compiled ini is what Vale runs, so a per-path
    # override that never reached the compile is not an override at all.
    try:
        vocabularies = {
            path: load_blocklist(
                resolve_blocklist_path(resolve_for(config, path).vocabulary, config.root)
            )
            for path in paths
        }
    except VocabularyError as exc:
        console.print(f"[red]blocklist error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    # One compile per distinct blocklist, and paths keep their input order within
    # a group so the report reads the same whether or not an override is in play.
    groups: dict[str, list[Path]] = {}
    for path in paths:
        groups.setdefault(vocabularies[path].fingerprint(), []).append(path)

    scores: list[DocumentScore] = []
    for group in groups.values():
        vocabulary = vocabularies[group[0]]
        # Severity still resolves per file inside `_lint_one`, so the wordlist is
        # the only setting the group has to agree on: it is the one thing baked
        # into the compiled artifact that cannot be re-resolved afterwards.
        compiled, compile_notes = _compile_for(
            group[0], config, ruleset, console, vocabulary
        )

        vale_result = None
        run_notes = list(compile_notes)
        if compiled is None:
            run_notes.append(
                "the Vale styles could not be compiled, so no Vale rule ran. "
                "Findings below come from the native rules only."
            )
        elif no_vale:
            run_notes.extend(unchecked_for_skipped(compiled))
        elif config.vale.enabled:
            severities, categories = _vale_levels(compiled, ruleset, config, group[0])
            vale_result = run_compiled_vale(
                group, compiled, severities, categories, binary=config.vale.binary
            )
        else:
            run_notes.extend(unchecked_for_skipped(compiled))

        # When Vale ran, it owns its rules and the native engine must not repeat
        # them. When it did not, the native engine runs everything it can, so a
        # missing binary degrades coverage rather than silently halving it twice.
        native_only = None
        if vale_result is not None and compiled is not None:
            owned = set(compiled.vale_rules) | set(compiled.aliases.values())
            native_only = {
                rule.qualified_id
                for rule in ruleset.rules
                if rule.qualified_id not in owned
            }

        scores.extend(
            _lint_one(p, config, ruleset, vale_result, run_notes, native_only)
            for p in group
        )

    # Back into the order the caller asked for, since the groups reordered them.
    order = {str(path): index for index, path in enumerate(paths)}
    scores.sort(key=lambda score: order.get(score.path, 0))

    if locale_note:
        for score in scores:
            score.unchecked.append(locale_note)

    if output_format == "html" or open_report:
        page = render_html(summarize(scores), scores, __version__)
        destination = out_path
        if destination is None and open_report:
            # A named temp file rather than stdout: a browser needs a path, and the
            # file has to outlive this process, so NamedTemporaryFile(delete=False)
            # is the shape. Keyed on nothing, so repeated runs do not collide.
            handle = tempfile.NamedTemporaryFile(
                prefix="slopvac-report-", suffix=".html", delete=False
            )
            destination = Path(handle.name)
            handle.close()
        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(page, encoding="utf-8")
            console.print(f"report: [bold]{destination}[/]")
            if open_report:
                # A browser that will not open is not a lint failure, so this
                # reports and carries on to the exit code the prose earned.
                if webbrowser.open(destination.resolve().as_uri()):
                    console.print("opened in your browser")
                else:
                    console.print(
                        "[yellow]could not open a browser[/]; the report is at the "
                        "path above"
                    )
        else:
            click.echo(page, nl=False)
    elif output_format == "json":
        click.echo(
            LintReport(
                version=__version__, summary=summarize(scores), documents=scores
            ).emit()
        )
    elif output_format == "github":
        # Workflow-command annotations, so findings land on the PR diff.
        for score in scores:
            for finding in score.findings:
                level = "error" if finding.severity is Severity.ERROR else "warning"
                click.echo(
                    f"::{level} file={finding.path},line={finding.line},"
                    f"col={finding.column},title={finding.rule_id}::{finding.message}"
                )
        summary = summarize(scores)
        click.echo(
            f"::notice title=slopvac::score {summary.score}/100, "
            f"{summary.findings} finding(s), "
            f"{summary.per_100_words:.2f} per 100 words"
        )
    elif output_format == "sarif":
        click.echo(
            build_sarif(
                scores,
                ruleset.rules,
                version=__version__,
                tool_uri="https://github.com/srobroek/slopvac",
            ).emit()
        )
    else:
        _report_text(scores, console, verbose)

    raise SystemExit(EXIT_OK if all(s.passed for s in scores) else EXIT_FINDINGS)


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
@click.option("--profile", type=click.Choice([p.value for p in Profile]), default="normal")
@click.option("--category", "only", multiple=True, help="Limit to these categories.")
@click.option("--kind", type=click.Choice([k.value for k in RuleKind]), help="Filter by kind.")
@click.option("--judgement", is_flag=True, help="Only the rules a linter cannot check.")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--config", "config_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--rules-dir", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def list_rules(
    profile: str,
    only: tuple[str, ...],
    kind: str | None,
    judgement: bool,
    output_format: str,
    config_path: Path | None,
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
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
@click.option("--config", "config_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--rules-dir", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def explain(
    rule_id: str,
    output_format: str,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
) -> None:
    """Show one rule in full: why it exists, its exceptions, and its examples."""
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
    console.print(f"kind: {rule.kind.value}   severity: {rule.severity.value}   scope: {rule.scope.value}")
    console.print("tiers: " + "  ".join(f"{k}={v.value}" for k, v in rule.tiers.items()))
    console.print(f"\n{rule.message}")
    if rule.fix:
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
    console.print("lint with: slopvac 'docs/**/*.md'")



@main.command("compile")
@click.option(
    "--outdir",
    type=click.Path(path_type=Path),
    help="Where to write the styles. Default: the run cache, keyed by a hash of "
    "the rules and the resolved config.",
)
@click.option("--profile", type=click.Choice([p.value for p in Profile]), default=None)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--rules-dir", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip handing each rule to Vale. Faster, and the routing is then unproven.",
)
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def compile_styles(
    outdir: Path | None,
    profile: str | None,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
    no_validate: bool,
    output_format: str,
) -> None:
    """Write the Vale styles and print which engine runs each rule.

    Use this to inspect the routing, or to run Vale by hand against the generated
    config: `vale --config=<outdir>/.vale.ini docs/`.
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
    table.add_row("vale", str(result.vale_count), "compiled and proven to load")
    table.add_row("native", str(result.native_count), "vale cannot express it; see below")
    table.add_row("none (judgement)", str(len(result.judgement_rules)), "not mechanizable")
    table.add_row("none (off)", str(len(result.disabled_rules)), "disabled by this config")
    console.print(table)

    if result.native_rules:
        console.print("\n[bold]rules that stay native[/]")
        for entry in result.native_rules:
            console.print(f"  {entry.rule_id} [{entry.kind}]")
            console.print(f"    {entry.reason}")


@main.command("cache")
@click.option(
    "--prune",
    is_flag=True,
    help=f"Delete all but the {CACHE_KEEP} most recently used trees. A lint does "
    f"this on its own; use this to reclaim the disk now.",
)
@click.option("--all", "prune_all", is_flag=True, help="Delete every compiled tree.")
def cache(prune: bool, prune_all: bool) -> None:
    """Show the compiled-style cache, and prune it.

    A tree is keyed by a hash of the rules and the resolved config, so a ruleset
    edit, a severity change, or a blocklist edit mints a new one. Nothing is ever
    served stale -- the key would differ -- so pruning is only about disk.
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


if __name__ == "__main__":
    main()


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
@click.option("--rules-dir", multiple=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def reference(destination: Path | None, check: bool, rules_dir: tuple[Path, ...]) -> None:
    """Generate the rules reference, split into checked and judgement rules.

    `--check` is what makes the committed copy trustworthy. A generated document
    with no check is a stale file with extra steps, and the failure it produces is
    the expensive kind: somebody plans against a rule that was renamed, retiered,
    or removed. So CI regenerates and compares rather than trusting the commit.
    """
    console = _console(False)
    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        console.print(f"[red]rule error[/]: {exc}")
        raise SystemExit(EXIT_ERROR) from None

    rendered = render_reference(ruleset, version=__version__)

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
