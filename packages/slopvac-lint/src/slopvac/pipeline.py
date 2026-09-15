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
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .analyze import parse
from .toml_comments import comment_projection, is_toml_path
from .compile_vale import (
    CompileResult,
    ValeUnavailable,
    canonical_source_language,
    compile_ruleset,
    compiled_levels,
)
from .config import (
    CategorySettings,
    Config,
    ConfigError,
    LocalePatch,
    Mode,
    Override,
    Profile,
    RuleSettings,
    Severity,
    ThresholdPatch,
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
from .vale_probe import rst_converter, vale_version
from .vocabulary import Vocabulary, VocabularyError, load_blocklist

LINTABLE = ("*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.html", "*.toml", "mise.toml")
SOURCE_LINTABLE = (
    "*.py", "*.pyi", "*.pyw", "*.js", "*.jsx", "*.mjs", "*.cjs", "*.ts", "*.tsx",
    "*.rs", "*.go", "*.java", "*.c", "*.h", "*.cc", "*.cpp", "*.cxx", "*.hh",
    "*.hpp", "*.hxx", "*.cs", "*.rb", "*.php", "*.swift", "*.kt", "*.kts", "*.scala",
    "*.sh", "*.bash", "*.zsh", "*.lua", "*.pl", "*.pm", "*.r", "*.ex", "*.exs",
    "*.hs", "*.fs", "*.fsx", "*.jl", "*.ps1", "*.psm1", "*.proto", "*.css",
    "*.scss", "*.less", "*.clj", "*.cljs", "*.dart", "sconstruct", "Gemfile", "Rakefile", "Brewfile",
)


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
    """Loaded per-path configs, rulesets, and targets for one invocation."""

    configs: dict[Path, Config]
    rulesets: dict[Path, RuleSet]
    # Retained for machine reports when collection leaves no lintable paths.
    ruleset: RuleSet
    paths: list[Path]
    locale_note: str | None
    locale_notes: dict[Path, str | None] = field(default_factory=dict)
    collection_notes: list[str] = field(default_factory=list)


def _expand_paths(targets: tuple[str, ...], notes: list[str] | None = None) -> list[Path]:
    """Expand targets, recording skipped RST files when requested."""
    found: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            for pattern in LINTABLE:
                found.extend(sorted(path.rglob(pattern)))
        elif path.is_file():
            found.append(path)
        else:
            pattern = Path(target)
            if pattern.is_absolute():
                anchor = Path(pattern.anchor)
                matches = sorted(anchor.glob(str(pattern.relative_to(anchor))))
            else:
                matches = sorted(Path().glob(target))
            if not matches:
                raise click.ClickException(f"no such file or directory: {target}")
            found.extend(m for m in matches if m.is_file())
    kept = [path for path in found if any(fnmatch.fnmatch(path.name, p) for p in LINTABLE)]
    skipped = [path for path in kept if path.suffix.lower() == ".rst"]
    if notes is not None and skipped and rst_converter() is None:
        kept = [path for path in kept if path.suffix.lower() != ".rst"]
        notes.append("RST target(s) skipped: rst2html or rst2html.py not found on PATH (" + ", ".join(str(p) for p in skipped) + "); install with `pip install docutils`.")
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in kept:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def _config_for(config: Config | dict[Path, Config], path: Path) -> Config:
    return config[path] if isinstance(config, dict) else config


def _ruleset_for(ruleset: RuleSet | dict[Path, RuleSet], path: Path) -> RuleSet:
    return ruleset[path] if isinstance(ruleset, dict) else ruleset

def _relative_to_config(path: Path, config: Config) -> str:
    root = config.root or Path.cwd()
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return path.name


def _source_candidates(targets: tuple[str, ...]) -> list[tuple[Path, bool]]:
    found: list[tuple[Path, bool]] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            found.extend((item, False) for item in sorted(path.rglob("*")) if item.is_file())
        elif path.is_file():
            found.append((path, True))
        else:
            pattern = Path(target)
            if pattern.is_absolute():
                anchor = Path(pattern.anchor)
                matches = sorted(anchor.glob(str(pattern.relative_to(anchor))))
            else:
                matches = sorted(Path().glob(target))
            if not matches:
                raise click.ClickException(f"no such file or directory: {target}")
            found.extend((item, False) for item in matches if item.is_file())
    seen: set[Path] = set()
    unique: list[tuple[Path, bool]] = []
    for path, explicit in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append((path, explicit))
    return unique


def _filter_paths(
    candidates: list[tuple[Path, bool]],
    configs: dict[Path, Config],
    *,
    code_comments: bool,
) -> list[Path]:
    kept: list[Path] = []
    for path, explicit in candidates:
        config = configs[path]
        if config.source is not None and path.resolve() == config.source.resolve():
            continue
        if config.is_excluded(_relative_to_config(path, config)):
            continue
        if code_comments:
            try:
                canonical_source_language(path)
            except ValueError as exc:
                if explicit:
                    raise click.ClickException(str(exc)) from None
                continue
            if not any(
                fnmatch.fnmatch(path.name.lower(), pattern.lower())
                for pattern in SOURCE_LINTABLE
            ):
                continue
        kept.append(path)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in kept:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique

def collect_paths(
    targets: tuple[str, ...], config: Config | dict[Path, Config], notes: list[str] | None = None
) -> list[Path]:
    """Expand targets and apply the exclude list."""
    candidates = [(path, False) for path in _expand_paths(targets, notes)]
    configs = {path: _config_for(config, path) for path, _explicit in candidates}
    return _filter_paths(candidates, configs, code_comments=False)

def collect_source_paths(
    targets: tuple[str, ...], config: Config | dict[Path, Config]
) -> list[Path]:
    """Collect supported source files for one global code-comment run."""
    candidates = _source_candidates(targets)
    configs = {path: _config_for(config, path) for path, _explicit in candidates}
    return _filter_paths(candidates, configs, code_comments=True)


def lint_one(
    path: Path,
    config: Config,
    ruleset: RuleSet,
    vale_result: ValeResult | None,
    extra_unchecked: list[str] | None = None,
    native_only: set[str] | None = None,
) -> DocumentScore:
    resolved = resolve_for(config, path)
    if resolved.mode is Mode.CODE_COMMENTS:
        findings = vale_result.findings_for(str(path)) if vale_result is not None else []
        unchecked = list(extra_unchecked or [])
        if vale_result is not None:
            unchecked.extend(vale_result.unchecked)
        return score_document(
            path=str(path),
            findings=findings,
            words=0,
            sentences=0,
            paragraphs=0,
            config=resolved,
            categories_meta=ruleset.weights,
            unchecked=unchecked,
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    document = parse(str(path), comment_projection(text) if is_toml_path(path) else text)

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
    *,
    validate: bool = True,
) -> tuple[CompileResult | None, list[str]]:
    """Compile the ruleset for `sample`'s resolved config.

    Returns `(None, notes)` when Vale is unusable, so the caller reports the gap
    rather than dying: the native rules still run, and a linter that refuses to
    start because a Go binary is missing is worse than one that says what it
    skipped.
    """
    resolved = resolve_for(config, sample)
    source_language = source_extension = None
    if resolved.mode is Mode.CODE_COMMENTS:
        source_language, source_extension = canonical_source_language(sample)
    try:
        if validate:
            return compile_ruleset(
                ruleset,
                resolved,
                binary=resolved.vale.binary,
                validate=True,
                vocabulary=vocabulary,
                source_language=source_language,
                source_extension=source_extension,
            ), []
        with tempfile.TemporaryDirectory(prefix="slopvac-routing-") as directory:
            compiled = compile_ruleset(
                ruleset,
                resolved,
                outdir=Path(directory),
                binary=resolved.vale.binary,
                validate=False,
                vocabulary=vocabulary,
                source_language=source_language,
                source_extension=source_extension,
            )
            return compiled, []
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
    if config._cli_override is not None:
        check(
            config._cli_override.categories,
            config._cli_override.rules,
            f"overrides[{len(config.overrides)}] ({', '.join(config._cli_override.files)})",
        )
    return errors


def validate_code_comments_vale(
    paths: list[Path], config: Config | dict[Path, Config]
) -> None:
    """Reject project Vale customization from the source-comment mode."""
    errors: list[str] = []
    for path in paths:
        file_config = _config_for(config, path)
        resolved = resolve_for(file_config, path)
        if resolved.vale.config is not None:
            errors.append(
                f"[red]code-comments config error[/] {path}: "
                "custom vale.config is not supported; use the packaged config."
            )
        if resolved.vale.styles:
            errors.append(
                f"[red]code-comments config error[/] {path}: "
                "custom vale.styles are not supported; use the packaged styles."
            )
    if errors:
        raise PipelineError(errors)



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
    ruleset: RuleSet | Mapping[Path, RuleSet],
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
                ruleset if isinstance(ruleset, Mapping) else ruleset.rules,
                version=__version__,
                tool_uri="https://github.com/srobroek/slopvac",
            ).emit()
        if out_path is not None:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered + "\n", encoding="utf-8")
            console.print(f"report: [bold]{out_path}[/]")
        else:
            click.echo(rendered)


def _build_cli_override(
    *,
    profile: str | None,
    only_categories: tuple[str, ...],
    disabled: tuple[str, ...],
    min_score: float | None,
    max_per_100_words: float | None,
    locale_tag: str | None,
    known_categories: set[str],
) -> Override | None:
    categories = {
        name: CategorySettings(severity=Severity.OFF)
        for name in known_categories
        if only_categories and name not in set(only_categories)
    }
    rules: dict[str, RuleSettings] = {}
    for entry in disabled:
        if "." in entry:
            rules[entry] = RuleSettings(severity=Severity.OFF)
        else:
            categories[entry] = CategorySettings(severity=Severity.OFF)
    thresholds = None
    if min_score is not None or max_per_100_words is not None:
        thresholds = ThresholdPatch(
            min_score=min_score,
            max_total_per_100_words=max_per_100_words,
        )
    locale = LocalePatch(default=locale_tag) if locale_tag else None
    values = {
        "profile": Profile(profile) if profile else None,
        "categories": categories,
        "rules": rules,
        "thresholds": thresholds,
        "locale": locale,
    }
    values = {key: value for key, value in values.items() if value not in (None, {}, [])}
    return Override(files=["**"], **values) if values else None

def load_run_context(
    targets: tuple[str, ...],
    *,
    profile: str | None,
    mode: str | None,
    config_path: Path | None,
    rules_dir: tuple[Path, ...],
    only_categories: tuple[str, ...],
    disabled: tuple[str, ...],
    min_score: float | None,
    max_per_100_words: float | None,
    locale_tag: str | None,
) -> RunContext:
    """Discover and prepare the nearest config and ruleset for every target."""
    first = Path(targets[0])
    discovered = config_path or find_config(first if first.exists() else Path.cwd())
    try:
        first_config = load_config(
            discovered, root=discovered.parent if discovered else None
        )
    except ConfigError as exc:
        raise PipelineError(f"[red]config error[/]: {exc}") from None

    if mode is not None:
        try:
            selected_mode = Mode(mode)
        except ValueError:
            raise PipelineError(f"[red]mode error[/]: unknown mode {mode!r}") from None
    else:
        selected_mode = first_config.mode

    try:
        base_ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        raise PipelineError(f"[red]ruleset error[/]: {exc}") from None

    if only_categories:
        unknown = set(only_categories) - set(base_ruleset.categories)
        if unknown:
            raise PipelineError(
                f"[red]unknown category[/]: {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(base_ruleset.categories))}"
            )

    cli_override = _build_cli_override(
        profile=profile,
        only_categories=only_categories,
        disabled=disabled,
        min_score=min_score,
        max_per_100_words=max_per_100_words,
        locale_tag=locale_tag,
        known_categories=set(base_ruleset.categories),
    )

    collection_notes: list[str] = []
    try:
        if selected_mode is Mode.CODE_COMMENTS:
            candidates = _source_candidates(targets)
        else:
            candidates = [(path, False) for path in _expand_paths(targets, collection_notes)]
    except click.ClickException as exc:
        raise PipelineError(f"[red]{exc.message}[/]") from None

    config_cache: dict[Path | None, Config] = {}

    def config_for(path: Path) -> Config:
        source = config_path or find_config(path)
        key = source.resolve() if source is not None else None
        if key not in config_cache:
            try:
                config_cache[key] = load_config(
                    source, root=source.parent if source else None
                )
            except ConfigError as exc:
                raise PipelineError(f"[red]config error[/]: {exc}") from None
            object.__setattr__(config_cache[key], "mode", selected_mode)
            if cli_override is not None:
                object.__setattr__(config_cache[key], "_cli_override", cli_override)
        return config_cache[key]

    configs = {path: config_for(path) for path, _explicit in candidates}
    if not candidates:
        object.__setattr__(first_config, "mode", selected_mode)
        if cli_override is not None:
            object.__setattr__(first_config, "_cli_override", cli_override)
        config_cache[discovered.resolve() if discovered else None] = first_config

    rulesets_all: dict[Path, RuleSet] = {}
    locale_notes_all: dict[Path, str | None] = {}
    name_errors: list[str] = []
    if not candidates:
        resolved = resolve_for(first_config, first)
        inject_locale_rule(
            base_ruleset, resolved.locale.default, resolved.locale.allow
        )
        name_errors.extend(validate_names(first_config, base_ruleset))

    # The spelling rule is generated from the locale, so it is added after the
    # YAML loads. A bad tag becomes an `unchecked` note rather than an exception:
    # a typo here must not stop the other 200 rules from running.
    for path, _explicit in candidates:
        try:
            ruleset = load_ruleset(list(rules_dir) or None)
        except RuleLoadError as exc:
            raise PipelineError(f"[red]ruleset error[/]: {exc}") from None
        config = configs[path]
        resolved = resolve_for(config, path)
        locale_note = inject_locale_rule(
            ruleset, resolved.locale.default, resolved.locale.allow
        )
        rulesets_all[path] = ruleset
        locale_notes_all[path] = locale_note
        name_errors.extend(validate_names(config, ruleset))
    if name_errors:
        raise PipelineError(
            [f"[red]config error[/] {message}" for message in name_errors]
        )

    try:
        paths = _filter_paths(candidates, configs, code_comments=selected_mode is Mode.CODE_COMMENTS)
    except click.ClickException as exc:
        raise PipelineError(f"[red]{exc.message}[/]") from None
    if selected_mode is Mode.CODE_COMMENTS:
        validate_code_comments_vale(paths, configs)

    rulesets = {path: rulesets_all[path] for path in paths}
    locale_notes = {path: locale_notes_all[path] for path in paths}
    locale_note = next(iter(locale_notes.values()), None)
    return RunContext(
        configs=configs,
        rulesets=rulesets,
        ruleset=next(iter(rulesets.values()), next(iter(rulesets_all.values()), base_ruleset)),
        paths=paths,
        locale_note=locale_note,
        locale_notes=locale_notes,
        collection_notes=collection_notes,
    )



def group_inputs(
    paths: list[Path],
    config: Config | dict[Path, Config],
    ruleset: RuleSet | dict[Path, RuleSet],
) -> tuple[dict[Path, Vocabulary], dict[str, list[Path]]]:
    """Load each path's blocklist and group paths that compile to the same tree.

    ONE COMPILE PER DISTINCT COMPILE INPUT. `[[overrides]]` can point a subtree at
    its own wordlist, and the Vale compile BAKES THE WORDLIST IN; it can also turn
    a Vale rule on or off for that subtree, and a rule absent from the style tree
    cannot be recovered afterwards. Keying the compile on the first file's
    resolution would have silently applied the root wordlist -- and the root
    rule set -- to every path. The key is therefore the wordlist fingerprint plus
    the rule levels and locale the file's resolved config compiles to; severity is
    still re-resolved per file when findings come back.

    Paths keep their input order within a group so the report reads the same
    whether or not an override is in play.
    """
    vocabularies: dict[Path, Vocabulary] = {}
    groups: dict[str, list[Path]] = {}
    for path in paths:
        file_config = _config_for(config, path)
        file_ruleset = _ruleset_for(ruleset, path)
        resolved = resolve_for(file_config, path)
        vocabularies[path] = load_blocklist(
            resolve_blocklist_path(resolved.vocabulary, file_config.root)
        )
        levels = compiled_levels(file_ruleset, resolved)
        language = extension = ""
        if resolved.mode is Mode.CODE_COMMENTS:
            language, extension = canonical_source_language(path)
        version = vale_version(resolved.vale.binary) if resolved.vale.enabled else None
        key = "|".join(
            (
                resolved.mode.value,
                language,
                extension,
                str(resolved.vale.enabled),
                resolved.vale.binary,
                repr(version),
                repr(resolved.vale.config),
                repr(resolved.vale.styles),
                resolved.locale.default,
                repr(resolved.locale.allow),
                vocabularies[path].fingerprint(),
                repr(sorted(levels.items())),
            )
        )
        groups.setdefault(key, []).append(path)
    return vocabularies, groups


def run_lint(ctx: RunContext, *, no_vale: bool) -> list[DocumentScore]:
    """Compile per vocabulary group, run Vale, then score each document."""
    # Loaded HERE, not lazily at compile time, so a broken blocklist is reported
    # before any file is read. A configured-but-unloadable wordlist is a config
    # error like any other: the project asked for the gate by name, and linting on
    # with it silently empty would report every document clean.
    try:
        vocabularies, groups = group_inputs(ctx.paths, ctx.configs, ctx.rulesets)
    except VocabularyError as exc:
        raise PipelineError(f"[red]blocklist error[/]: {exc}") from None

    scores: list[DocumentScore] = []
    for group in groups.values():
        sample = group[0]
        config = ctx.configs[sample]
        ruleset = ctx.rulesets[sample]
        vocabulary = vocabularies[sample]
        # Every file in the group compiles to the same tree (`group_inputs`), so
        # the first one stands for all of them here.
        resolved_group = resolve_for(config, sample)
        compiled, compile_notes = _compile_for(
            sample,
            config,
            ruleset,
            vocabulary,
            validate=not no_vale and resolved_group.vale.enabled,
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
        elif not resolved_group.vale.enabled:
            run_notes.extend(
                unchecked_for_skipped(compiled, cause="[vale] enabled = false")
            )
        else:
            # Rules excluded from comment scopes are unchecked even when Vale runs.
            run_notes.extend(unchecked_for_skipped(compiled, vale_skipped=False))
            severities, categories = vale_levels(compiled, ruleset, config, sample)
            vale_result = run_compiled_vale(
                group,
                compiled,
                severities,
                categories,
                binary=resolved_group.vale.binary,
            )

        # When Vale ran, it owns its rules and the native engine must not repeat
        # them. When Vale was explicitly skipped, only the rules that the compiler
        # routed native may run; Vale-owned rules stay unchecked instead of using
        # different parsing and scope semantics.
        native_only = None
        if compiled is not None:
            if vale_result is not None or no_vale or not resolved_group.vale.enabled:
                owned = set(compiled.vale_rules) | set(compiled.aliases.values())
                native_only = {
                    rule.qualified_id
                    for rule in ruleset.rules
                    if rule.qualified_id not in owned
                }

        scores.extend(
            lint_one(
                path,
                ctx.configs[path],
                ctx.rulesets[path],
                vale_result,
                run_notes,
                native_only,
            )
            for path in group
        )

    if ctx.collection_notes:
        if scores:
            scores[0].unchecked.extend(ctx.collection_notes)
        else:
            profile = next(iter(ctx.configs.values()), None)
            profile_name = profile.profile.value if profile is not None else Profile.NORMAL.value
            scores.append(
                DocumentScore(
                    path="<collection>",
                    profile=profile_name,
                    unchecked=list(ctx.collection_notes),
                )
            )

    # Back into the order the caller asked for, since the groups reordered them.
    order = {str(path): index for index, path in enumerate(ctx.paths)}
    scores.sort(key=lambda score: order.get(score.path, 0))

    for score in scores:
        locale_note = ctx.locale_notes.get(Path(score.path))
        if locale_note:
            score.unchecked.append(locale_note)

    return scores
