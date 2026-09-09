"""Lint run mechanics extracted from the click CLI.

Owns path collection, config and ruleset preparation, the Vale-per-vocabulary
run, per-document scoring, and report rendering. The CLI module keeps the
click group, option definitions, and inspection commands; this module is
the part that actually lints.
"""

from __future__ import annotations

import fnmatch
import tempfile
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .analyze import parse
from .compile_vale import CompileResult, ValeUnavailable, compile_ruleset, compiled_levels
from .config import (
    CategorySettings,
    Config,
    ConfigError,
    Profile,
    RuleSettings,
    Severity,
    find_config,
    load_config,
    resolve_blocklist_path,
    resolve_for,
)
from .engine import Engine, drop_quoted_illustrations
from .html import render_html
from .model import DocumentScore, Finding
from .report import LintReport, build_sarif, summarize
from .rules import RuleLoadError, RuleSet, inject_locale_rule, load_ruleset
from .score import score_document
from .vale import ValeResult, run_compiled_vale, unchecked_for_skipped
from .vocabulary import Vocabulary, VocabularyError, load_blocklist

LINTABLE = ("*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.html")

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


class PipelineError(Exception):
    """A lint setup failure already formatted for the console."""

    def __init__(self, messages: str | list[str], code: int = EXIT_ERROR) -> None:
        self.messages = [messages] if isinstance(messages, str) else messages
        self.code = code
        super().__init__("\n".join(self.messages))


@dataclass
class RunContext:
    """Loaded config, ruleset, and target paths for one `lint` invocation."""

    config: Config
    ruleset: RuleSet
    paths: list[Path]
    locale_note: str | None


def collect_paths(targets: tuple[str, ...], config: Config) -> list[Path]:
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
            # A glob the shell did not expand. pathlib's glob takes relative
            # patterns only, so an absolute one is anchored at its root.
            pattern = Path(target)
            if pattern.is_absolute():
                anchor = Path(pattern.anchor)
                matches = sorted(anchor.glob(str(pattern.relative_to(anchor))))
            else:
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


def lint_one(
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
        # Vale reads no annotation either, so a `slopvac-allow` comment is applied
        # here for the same reason. The engine is rebuilt WITHOUT `only`: the rules
        # being filtered are by definition the ones Vale took, so the partitioned
        # engine above does not hold them and could not validate a reason against
        # their exception lists.
        # Vale ran once per vocabulary group with the FIRST file's settings, so a
        # per-file override (`[[overrides]] files = [...]`) never reached its
        # severities: `evals/REPORT.md` demoted docs-discipline to a suggestion and
        # still reported it as a warning whenever another file shared the run.
        # Each finding takes the level this file resolves for its rule, and a rule
        # this file turns off drops out.
        whole = Engine(ruleset.rules, resolved)
        merged: list[Finding] = []
        for finding in whole.drop_suppressed(
            drop_quoted_illustrations(
                vale_result.findings_for(str(path)), document, ruleset
            ),
            document,
        ):
            rule = ruleset.by_id(finding.rule_id)
            if rule is None:
                merged.append(finding)
                continue
            if not whole.is_active(rule):
                continue
            merged.append(finding.model_copy(update={"severity": whole.severity_for(rule)}))
        findings.extend(merged)
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


def validate_names(config: Config, ruleset: RuleSet) -> list[str]:
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


def vale_levels(
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


def report_text(scores: list[DocumentScore], console: Console, verbose: bool) -> None:
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


def emit_report(
    scores: list[DocumentScore],
    ruleset: RuleSet,
    console: Console,
    *,
    output_format: str,
    out_path: Path | None,
    open_report: bool,
    format_given: bool,
    verbose: bool,
) -> None:
    """Render the run in one format and deliver it to stdout, a file, or a browser.

    `--out` alone means an HTML report; `--out` with an explicit `--format` writes
    that format. Text always goes to the console.
    """
    if output_format == "html" or open_report or (out_path is not None and not format_given):
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
    elif output_format == "text":
        report_text(scores, console, verbose)
    else:
        if output_format == "json":
            rendered = LintReport(
                version=__version__, summary=summarize(scores), documents=scores
            ).emit()
        elif output_format == "github":
            # Workflow-command annotations, so findings land on the PR diff.
            summary = summarize(scores)
            lines = [
                f"::{'error' if finding.severity is Severity.ERROR else 'warning'} "
                f"file={finding.path},line={finding.line},"
                f"col={finding.column},title={finding.rule_id}::{finding.message}"
                for score in scores
                for finding in score.findings
            ]
            lines.append(
                f"::notice title=slopvac::score {summary.score}/100, "
                f"{summary.findings} finding(s), "
                f"{summary.per_100_words:.2f} per 100 words"
            )
            rendered = "\n".join(lines)
        else:
            rendered = build_sarif(
                scores,
                ruleset.rules,
                version=__version__,
                tool_uri="https://github.com/srobroek/slopvac",
            ).emit()
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered + "\n", encoding="utf-8")
            console.print(f"report: [bold]{out_path}[/]")
        else:
            click.echo(rendered)


def load_run_context(
    targets: tuple[str, ...],
    *,
    profile: str | None,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
    only_categories: tuple[str, ...],
    disabled: tuple[str, ...],
    min_score: float | None,
    max_per_100_words: float | None,
    locale_tag: str | None,
) -> RunContext:
    """Discover config, apply CLI overrides, inject locale, and collect paths."""
    first = Path(targets[0])
    discovered = config_path or find_config(first if first.exists() else Path.cwd())
    try:
        config = load_config(discovered, root=discovered.parent if discovered else None)
    except ConfigError as exc:
        raise PipelineError(f"[red]config error[/]: {exc}") from None

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
    for entry in disabled:
        if "." in entry:
            config.rules[entry] = RuleSettings(severity=Severity.OFF)
        else:
            config.categories[entry] = CategorySettings(severity=Severity.OFF)

    try:
        ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        raise PipelineError(f"[red]ruleset error[/]: {exc}") from None

    # The spelling rule is generated from the locale, so it is added after the
    # YAML loads. A bad tag becomes an `unchecked` note rather than an exception:
    # a typo here must not stop the other 200 rules from running.
    locale_note = inject_locale_rule(
        ruleset, config.locale.default, config.locale.allow
    )

    # Before anything runs, and EXIT_ERROR rather than a warning: a project that
    # believes it disabled a rule has to hear that it did not.
    name_errors = validate_names(config, ruleset)
    if name_errors:
        raise PipelineError(
            [f"[red]config error[/] {message}" for message in name_errors]
        )

    if only_categories:
        keep = set(only_categories)
        unknown = keep - set(ruleset.categories)
        if unknown:
            raise PipelineError(
                f"[red]unknown category[/]: {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(ruleset.categories))}"
            )
        for name in list(ruleset.categories):
            if name not in keep:
                config.categories[name] = CategorySettings(severity=Severity.OFF)

    try:
        paths = collect_paths(targets, config)
    except click.ClickException as exc:
        raise PipelineError(f"[red]{exc.message}[/]") from None

    return RunContext(
        config=config, ruleset=ruleset, paths=paths, locale_note=locale_note
    )


def group_inputs(
    paths: list[Path], config: Config, ruleset: RuleSet
) -> tuple[dict[Path, Vocabulary], dict[str, list[Path]]]:
    """Load each path's blocklist and group paths that compile to the same tree.

    ONE COMPILE PER DISTINCT COMPILE INPUT. `[[overrides]]` can point a subtree at
    its own wordlist, and the Vale compile BAKES THE WORDLIST IN; it can also turn
    a Vale rule on or off for that subtree, and a rule absent from the style tree
    cannot be recovered afterwards. Keying the compile on the first file's
    resolution would have silently applied the root wordlist -- and the root
    rule set -- to every path. The key is therefore the wordlist fingerprint plus
    the rule levels the file's resolved config compiles to; severity is still
    re-resolved per file when findings come back.

    Paths keep their input order within a group so the report reads the same
    whether or not an override is in play.
    """
    vocabularies: dict[Path, Vocabulary] = {}
    groups: dict[str, list[Path]] = {}
    for path in paths:
        resolved = resolve_for(config, path)
        vocabularies[path] = load_blocklist(
            resolve_blocklist_path(resolved.vocabulary, config.root)
        )
        levels = compiled_levels(ruleset, resolved)
        key = vocabularies[path].fingerprint() + "|" + repr(sorted(levels.items()))
        groups.setdefault(key, []).append(path)
    return vocabularies, groups


def run_lint(ctx: RunContext, *, no_vale: bool) -> list[DocumentScore]:
    """Compile per vocabulary group, run Vale, then score each document."""
    # Loaded HERE, not lazily at compile time, so a broken blocklist is reported
    # before any file is read. A configured-but-unloadable wordlist is a config
    # error like any other: the project asked for the gate by name, and linting on
    # with it silently empty would report every document clean.
    try:
        vocabularies, groups = group_inputs(ctx.paths, ctx.config, ctx.ruleset)
    except VocabularyError as exc:
        raise PipelineError(f"[red]blocklist error[/]: {exc}") from None

    scores: list[DocumentScore] = []
    for group in groups.values():
        vocabulary = vocabularies[group[0]]
        # Every file in the group compiles to the same tree (`group_inputs`), so
        # the first one stands for all of them here.
        compiled, compile_notes = _compile_for(
            group[0], ctx.config, ctx.ruleset, vocabulary
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
        elif ctx.config.vale.enabled:
            severities, categories = vale_levels(
                compiled, ctx.ruleset, ctx.config, group[0]
            )
            vale_result = run_compiled_vale(
                group, compiled, severities, categories, binary=ctx.config.vale.binary
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
                for rule in ctx.ruleset.rules
                if rule.qualified_id not in owned
            }

        scores.extend(
            lint_one(p, ctx.config, ctx.ruleset, vale_result, run_notes, native_only)
            for p in group
        )

    # Back into the order the caller asked for, since the groups reordered them.
    order = {str(path): index for index, path in enumerate(ctx.paths)}
    scores.sort(key=lambda score: order.get(score.path, 0))

    if ctx.locale_note:
        for score in scores:
            score.unchecked.append(ctx.locale_note)

    return scores
