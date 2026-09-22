"""Lint run mechanics extracted from the click CLI.

Owns path collection, config and ruleset preparation, the Vale-per-vocabulary
run, per-document scoring, and report rendering. The CLI module keeps the
click group, option definitions, and inspection commands; this module is
the part that actually lints.
"""

from __future__ import annotations

import copy
import fnmatch
import os
import tempfile
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .analyze import parse
from .compile_vale import (
    SOURCE_FILENAMES,
    SOURCE_LANGUAGE_BY_EXTENSION,
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
from .diff_scope import DiffScope, filter_findings
from .engine import (
    Engine,
    drop_quoted_illustrations,
    is_single_replacement,
    match_substitution,
)
from .html import render_html
from .model import DocumentScore, Finding
from .report import LintReport, build_sarif, summarize
from .rules import RuleLoadError, RuleSet, inject_locale_rule, load_ruleset
from .score import score_document
from .vale import ValeResult, run_compiled_vale, unchecked_for_skipped
from .vale_probe import rst_converter
from .vocabulary import Vocabulary, VocabularyError, load_blocklist

LINTABLE = ("*.md", "*.mdx", "*.markdown", "*.txt", "*.rst", "*.html")
SOURCE_LINTABLE = tuple(f"*{suffix}" for suffix in SOURCE_LANGUAGE_BY_EXTENSION) + tuple(
    SOURCE_FILENAMES
)
COMMENTABLE = (*SOURCE_LINTABLE, "*.toml", "mise.toml")


def _comment_source_language(path: Path | str) -> tuple[str, str]:
    """Return a comment scope identity, including TOML's syntax projection."""
    candidate = Path(path)
    if candidate.suffix.lower() == ".toml":
        return "toml", ".toml"
    return canonical_source_language(candidate)


SKIP_SOURCE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "node_modules",
        "vendor",
        "build",
        "dist",
        "target",
        "__pycache__",
    }
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
    """Loaded configs, rulesets, and target paths for one `lint` invocation."""

    configs: dict[Path, Config]
    rulesets: dict[Path, RuleSet]
    ruleset: RuleSet
    paths: list[Path]
    locale_notes: dict[Path, str]
    diff_scope: DiffScope | None = None
    mode: Mode = Mode.PROSE
    comments: bool = False
    # Informational notes about directory entries omitted from code-comment scans.
    # They are emitted in JSON/text and do not affect the exit status.
    collection_notes: list[str] = field(default_factory=list)
    # Notes about targets that were asked for and could not be collected (an
    # `.rst` with no converter on PATH). These remain unchecked so the run exits 2.
    collection_unchecked: list[str] = field(default_factory=list)




def _relative_to_config(path: Path, config: Config) -> str:
    root = config.root or Path.cwd()
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        # Outside the config root -- match on the name alone rather than silently
        # applying no overrides or exclusions.
        return path.name


def _expand_paths(
    targets: tuple[str, ...],
    notes: list[str] | None = None,
    *,
    comments: bool | None = False,
    skipped: dict[Path, str] | None = None,
) -> list[Path]:

    """Expand targets with the document/source selection used by the CLI."""
    found: list[Path] = []
    if comments is None:
        patterns = tuple(dict.fromkeys((*LINTABLE, *COMMENTABLE)))
    else:
        patterns = COMMENTABLE if comments else LINTABLE
    prose_patterns = LINTABLE

    for target in targets:
        path = Path(target)
        if path.is_dir():
            for directory, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = sorted(
                    name
                    for name in dirs
                    if name not in SKIP_SOURCE_DIRS
                    and not (Path(directory) / name).is_symlink()
                )
                for name in sorted(files):
                    candidate = Path(directory) / name
                    if candidate.is_symlink():
                        continue
                    if not comments and candidate.name.lower() in {"slopvac.toml", ".slopvac.toml"}:
                        continue
                    if any(
                        fnmatch.fnmatch(name.lower(), pattern.lower()) for pattern in patterns
                    ):
                        found.append(candidate)
                    elif comments is not False and not any(
                        fnmatch.fnmatch(name.lower(), pattern.lower()) for pattern in prose_patterns
                    ):
                        try:
                            canonical_source_language(candidate)
                        except ValueError as exc:
                            message = (
                                f"unsupported source language skipped: {candidate} ({exc})"
                            )
                            if skipped is not None:
                                skipped[candidate] = message
                            if notes is not None:
                                notes.append(message)

        elif path.is_file():
            if comments is True:
                try:
                    _comment_source_language(path)
                except ValueError as exc:
                    raise click.ClickException(str(exc)) from None
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
            for match in matches:
                if not match.is_file():
                    continue
                if comments is True:
                    try:
                        _comment_source_language(match)
                    except ValueError as exc:
                        raise click.ClickException(str(exc)) from None
                found.append(match)


    kept = [
        path
        for path in found
        if any(fnmatch.fnmatch(path.name.lower(), pattern.lower()) for pattern in patterns)
    ]
    skipped_rst = [path for path in kept if path.suffix.lower() == ".rst"]
    if skipped_rst and rst_converter() is None:
        kept = [path for path in kept if path.suffix.lower() != ".rst"]
        message = (
            f"RST target(s) skipped: rst2html or rst2html.py not found on PATH "
            f"({', '.join(str(path) for path in skipped_rst)}); install with `pip install docutils`."
        )
        if skipped is not None:
            for path in skipped_rst:
                skipped[path] = message
        if notes is not None:
            notes.append(message)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in kept:
        resolved = path.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _comment_projection(path: Path, text: str) -> str:
    """Mask code while retaining comments, strings, escapes, and block bounds."""
    suffix = path.suffix.lower()
    html = suffix in {".html", ".xml", ".svg"}
    sql = suffix == ".sql"
    c_like = suffix in {
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".cs",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".rs",
        ".swift",
        ".ts",
        ".tsx",
    }
    line_markers = () if html else ("--",) if sql else ("//",) if c_like else ("#",)
    block_open, block_close = ("<!--", "-->") if html else ("/*", "*/")
    in_block = False
    quote: str | None = None
    output: list[str] = []
    for source_line in text.splitlines(keepends=True):
        line = source_line.rstrip("\r\n")
        newline = source_line[len(line) :]
        visible = [" "] * len(line)
        index = 0
        while index < len(line):
            if in_block:
                if line.startswith(block_close, index):
                    for offset in range(len(block_close)):
                        visible[index + offset] = line[index + offset]
                    index += len(block_close)
                    in_block = False
                else:
                    visible[index] = line[index]
                    index += 1
                continue
            if quote is not None:
                if line.startswith(quote, index):
                    index += len(quote)
                    quote = None
                elif line[index] == "\\":
                    index += 2
                else:
                    index += 1
                continue
            if any(line.startswith(marker, index) for marker in line_markers):
                visible[index:] = line[index:]
                break
            if line.startswith(block_open, index):
                for offset in range(len(block_open)):
                    visible[index + offset] = line[index + offset]
                index += len(block_open)
                in_block = True
                continue
            if line.startswith('"""', index) or line.startswith("'''", index):
                quote = line[index : index + 3]
                index += 3
            elif line[index] in {'"', "'", "`"}:
                quote = line[index]
                index += 1
            else:
                index += 1
        output.append("".join(visible) + newline)
    return "".join(output)


def lint_one(
    path: Path,
    config: Config,
    ruleset: RuleSet,
    vale_result: ValeResult | None,
    extra_unchecked: list[str] | None = None,
    native_only: set[str] | None = None,
    *,
    diff_scope: DiffScope | None = None,
    comments: bool = False,
) -> DocumentScore:
    resolved = resolve_for(config, path)
    text = path.read_text(encoding="utf-8", errors="replace")

    if resolved.mode is Mode.CODE_COMMENTS:
        unchecked: list[str] = list(extra_unchecked or [])
        if vale_result is not None:
            findings = vale_result.findings_for(str(path))
            unchecked.extend(vale_result.unchecked)
            document = parse(str(path), _comment_projection(path, text))
        else:
            # An explicit --no-vale still runs the native projection where it is
            # available, while the run notes make the Vale gap fail closed.
            document = parse(str(path), _comment_projection(path, text))
            findings = Engine(ruleset.rules, resolved).run(document)
        if diff_scope is not None:
            ranges = diff_scope.ranges_for(path)
            by_id = {rule.qualified_id: rule for rule in ruleset.rules}
            findings = filter_findings(findings, by_id, ranges, text)
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

    document = parse(str(path), text)
    engine = Engine(ruleset.rules, resolved, only=native_only)
    findings = engine.run(document)

    unchecked = list(extra_unchecked or [])
    missing = engine.unimplemented_metrics()
    if missing:
        unchecked.append(
            f"{len(missing)} metric rule(s) have no implementation in either "
            f"engine, so they did NOT run: {', '.join(missing)}"
        )
    if vale_result is not None:
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
            replacement = finding.replacement
            if rule.kind.value == "substitution" and rule.substitutions:
                candidate = match_substitution(rule.substitutions, finding.matched_text)
                replacement = candidate if is_single_replacement(candidate) else None
            merged.append(
                finding.model_copy(
                    update={
                        "severity": whole.severity_for(rule),
                        "replacement": replacement,
                    }
                )
            )
        findings.extend(merged)
        unchecked.extend(vale_result.unchecked)

    if diff_scope is not None:
        ranges = diff_scope.ranges_for(path)
        by_id = {rule.qualified_id: rule for rule in ruleset.rules}
        findings = filter_findings(findings, by_id, ranges, text)
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
    """Compile the ruleset for `sample`'s resolved config."""
    resolved = resolve_for(config, sample)
    source_language = source_extension = None
    if resolved.mode is Mode.CODE_COMMENTS:
        source_language, source_extension = _comment_source_language(sample)
    try:
        if validate:
            return (
                compile_ruleset(
                    ruleset,
                    resolved,
                    binary=resolved.vale.binary,
                    validate=True,
                    vocabulary=vocabulary,
                    source_language=source_language,
                    source_extension=source_extension,
                ),
                [],
            )
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


def report_text(
    scores: list[DocumentScore],
    console: Console,
    verbose: bool,
    notes: list[str] | None = None,
) -> None:
    for note in notes or []:
        console.print(f"[yellow]SKIPPED[/] {note}")
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
    notes: list[str] | None = None,
) -> None:

    """Render the run in one format and deliver it to stdout, a file, or a browser.

    `--out` alone means an HTML report; `--out` with an explicit `--format` writes
    that format. Text always goes to the console.
    """
    if (
        output_format == "html"
        or open_report
        or (out_path is not None and not format_given)
    ):
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
        report_text(scores, console, verbose, notes)

    else:
        if output_format == "json":
            rendered = LintReport(
                version=__version__, summary=summarize(scores), documents=scores,
                notes=notes or [],
            ).emit()
        elif output_format == "github":
            # Workflow-command annotations, so findings land on the PR diff.
            summary = summarize(scores)
            lines = [
                f"::{'error' if finding.severity is Severity.ERROR else 'warning' if finding.severity is Severity.WARNING else 'notice'} "
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
    mode: str | Mode | None = None,
    diff_scope: DiffScope | None = None,
    comments: bool = False,
) -> RunContext:
    """Discover and apply the nearest config independently for every target."""
    auto_mode = mode is None and not comments
    selected_mode = (
        Mode(mode)
        if mode is not None
        else Mode.CODE_COMMENTS
        if comments
        else Mode.PROSE
    )
    collection_notes: list[str] = []
    skipped_collections: dict[Path, str] = {}
    try:
        candidates = _expand_paths(
            targets,
            collection_notes,
            comments=None if auto_mode else selected_mode is Mode.CODE_COMMENTS,
            skipped=skipped_collections,
        )
    except click.ClickException as exc:
        raise PipelineError(f"[red]{exc.message}[/]") from None
    if diff_scope is not None:
        allowed = diff_scope.paths()
        candidates = [path for path in candidates if path.resolve() in allowed]

    # Discovery can visit the same config for every file in a tree. Load each
    # source once, then copy it before adding the invocation-wide CLI layer.
    loaded: dict[Path | None, Config] = {}
    explicit = config_path.resolve() if config_path is not None else None

    def load_discovered(discovered: Path | None) -> Config:
        key = discovered.resolve() if discovered is not None else None
        if key not in loaded:
            try:
                loaded[key] = load_config(key, root=key.parent if key else None)
            except ConfigError as exc:
                raise PipelineError(f"[red]config error[/]: {exc}") from None
        return loaded[key]

    # Automatic mode needs configs for explicit files and skipped directory
    # entries before it can decide which input surface they belong to.
    if auto_mode:
        for target in targets:
            path = Path(target)
            if path.is_file():
                load_discovered(explicit or find_config(path))
    for path in skipped_collections:
        load_discovered(explicit or find_config(path))

    # An empty directory still needs its nearest config loaded so malformed
    # configuration is reported rather than silently treated as a clean run.
    starts = [Path(target) for target in targets] if not candidates else candidates
    base_by_path: dict[Path, Config] = {}
    for path in starts:
        discovered = explicit or find_config(path if path.exists() else Path.cwd())
        base = load_discovered(discovered)
        if path in candidates:
            base_by_path[path] = base

    try:
        base_ruleset = load_ruleset(list(rules_dir) or None)
    except RuleLoadError as exc:
        raise PipelineError(f"[red]ruleset error[/]: {exc}") from None

    cli_categories: dict[str, CategorySettings] = {}
    cli_rules: dict[str, RuleSettings] = {}
    for entry in disabled:
        if "." in entry:
            cli_rules[entry] = RuleSettings(severity=Severity.OFF)
        else:
            cli_categories[entry] = CategorySettings(severity=Severity.OFF)

    if only_categories:
        keep = set(only_categories)
        unknown = keep - set(base_ruleset.categories)
        if unknown:
            raise PipelineError(
                f"[red]unknown category[/]: {', '.join(sorted(unknown))}. "
                f"Known: {', '.join(sorted(base_ruleset.categories))}"
            )
        for name in base_ruleset.categories:
            if name not in keep:
                cli_categories[name] = CategorySettings(severity=Severity.OFF)

    has_cli_override = bool(
        profile
        or min_score is not None
        or max_per_100_words is not None
        or locale_tag
        or cli_categories
        or cli_rules
    )
    cli_override = Override(
        files=["**"],
        profile=Profile(profile) if profile else None,
        thresholds=(
            ThresholdPatch(
                min_score=min_score,
                max_total_per_100_words=max_per_100_words,
            )
            if min_score is not None or max_per_100_words is not None
            else None
        ),
        locale=LocalePatch(default=locale_tag) if locale_tag else None,
        categories=cli_categories,
        rules=cli_rules,
    )

    effective_by_source: dict[Path | None, Config] = {}
    for source, base in loaded.items():
        config = copy.deepcopy(base)
        if not auto_mode:
            config.mode = selected_mode
        if has_cli_override:
            config.overrides.append(copy.deepcopy(cli_override))
        effective_by_source[source] = config

    configs: dict[Path, Config] = {}
    paths: list[Path] = []
    for path in candidates:
        base = base_by_path[path]
        source = base.source.resolve() if base.source is not None else None
        config = effective_by_source[source]
        if auto_mode:
            patterns = COMMENTABLE if config.mode is Mode.CODE_COMMENTS else LINTABLE
            if not any(
                fnmatch.fnmatch(path.name.lower(), pattern.lower()) for pattern in patterns
            ):
                continue
        if config.is_excluded(_relative_to_config(path, config)):
            continue
        paths.append(path)
        configs[path] = config

    # An explicit file still has to fail when its selected code-comment mode
    # cannot map the suffix to a source language.
    if auto_mode:
        for target in targets:
            path = Path(target)
            if not path.is_file():
                continue
            discovered = explicit or find_config(path)
            base = load_discovered(discovered)
            source = base.source.resolve() if base.source is not None else None
            config = effective_by_source[source]
            if config.mode is Mode.CODE_COMMENTS:
                try:
                    _comment_source_language(path)
                except ValueError as exc:
                    raise PipelineError(f"[red]{exc}[/]") from None
    informational: list[str] = []
    incomplete: list[str] = []
    for path, message in skipped_collections.items():
        discovered = explicit or find_config(path)
        base = load_discovered(discovered)
        source = base.source.resolve() if base.source is not None else None
        config = effective_by_source[source]
        if message.startswith("unsupported source language skipped:"):
            if config.mode is Mode.CODE_COMMENTS and message not in informational:
                informational.append(message)
        elif config.mode is Mode.PROSE and message not in incomplete:
            incomplete.append(message)
    collection_notes = informational

    # The generated spelling rule is part of the ruleset, so keep one ruleset
    # per final locale. All other rules are loaded once and deep-copied locally.
    rulesets_by_locale: dict[tuple[str, tuple[str, ...]], tuple[RuleSet, str | None]] = {}
    locale_notes: dict[Path, str] = {}
    name_errors: list[str] = []

    def ruleset_for(tag: str, allow: list[str] | None) -> tuple[RuleSet, str | None]:
        key = (tag, tuple(allow or ()))
        if key not in rulesets_by_locale:
            local = copy.deepcopy(base_ruleset)
            note = inject_locale_rule(local, tag, list(allow) if allow else None)
            rulesets_by_locale[key] = (local, note)
        return rulesets_by_locale[key]

    # Validate every loaded config, including one belonging to an empty target.
    for config in effective_by_source.values():
        local, _ = ruleset_for(config.locale.default, config.locale.allow)
        name_errors.extend(validate_names(config, local))
    if name_errors:
        raise PipelineError([f"[red]config error[/] {message}" for message in name_errors])

    rulesets: dict[Path, RuleSet] = {}
    for path in paths:
        config = configs[path]
        resolved = resolve_for(config, path)
        local, note = ruleset_for(resolved.locale.default, resolved.locale.allow)
        rulesets[path] = local
        if note is not None:
            locale_notes[path] = note

    canonical = next(
        iter(rulesets.values()),
        next(iter(rulesets_by_locale.values()), (base_ruleset, None))[0],
    )
    return RunContext(
        configs=configs,
        rulesets=rulesets,
        ruleset=canonical,
        paths=paths,
        locale_notes=locale_notes,
        diff_scope=diff_scope,
        mode=selected_mode,
        comments=selected_mode is Mode.CODE_COMMENTS,
        collection_notes=collection_notes,
        collection_unchecked=incomplete,
    )


def group_inputs(
    paths: list[Path], configs: dict[Path, Config], rulesets: dict[Path, RuleSet]
) -> tuple[dict[Path, Vocabulary], dict[str, list[Path]]]:
    """Load each path's blocklist and group paths that compile to the same tree.

    ONE COMPILE PER DISTINCT COMPILE INPUT. The config, locale, vocabulary, Vale
    settings, and compiled levels all belong to the individual path; the key
    includes each so a file never inherits a neighbouring config's Vale tree.
    """
    vocabularies: dict[Path, Vocabulary] = {}
    groups: dict[str, list[Path]] = {}
    for path in paths:
        config = configs[path]
        ruleset = rulesets[path]
        resolved = resolve_for(config, path)
        blocklist_path = resolve_blocklist_path(resolved.vocabulary, config.root)
        vocabularies[path] = (
            load_blocklist(blocklist_path) if blocklist_path is not None else Vocabulary()
        )
        levels = compiled_levels(ruleset, resolved)
        # Locale changes the generated spelling rule's pattern, so it is a
        # compile input even when the selected severity levels are identical.
        key = "|".join(
            (
                vocabularies[path].fingerprint(),
                repr(sorted(levels.items())),
                repr(resolved.vale.model_dump()),
                repr(resolved.locale.model_dump()),
                resolved.mode.value,
                repr(_comment_source_language(path))
                if resolved.mode is Mode.CODE_COMMENTS
                else "",
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
        # Every file in the group compiles to the same tree and resolves to the
        # same Vale settings (`group_inputs`), so the first one stands for all.
        vale_settings = resolve_for(config, sample).vale
        compiled, compile_notes = _compile_for(
            sample,
            config,
            ruleset,
            vocabulary,
            validate=not no_vale and vale_settings.enabled,
        )

        vale_result = None
        run_notes = list(compile_notes)
        if compiled is None:
            run_notes.append(
                "the Vale styles could not be compiled, so no Vale rule ran. "
                "Findings below come from the native rules only."
            )
        elif no_vale or not vale_settings.enabled:
            run_notes.extend(
                unchecked_for_skipped(
                    compiled, "--no-vale" if no_vale else "[vale] enabled = false"
                )
            )
        else:
            run_notes.extend(unchecked_for_skipped(compiled, vale_skipped=False))
            severities, categories = vale_levels(compiled, ruleset, config, sample)
            vale_result = run_compiled_vale(
                group, compiled, severities, categories, binary=vale_settings.binary
            )

        # When Vale ran, it owns its rules and the native engine must not repeat
        # them. When Vale was explicitly skipped, only the rules that the compiler
        # routed native may run; Vale-owned rules stay unchecked instead of using
        # different parsing and scope semantics.
        native_only = None
        if compiled is not None:
            owned = set(compiled.vale_rules) | set(compiled.aliases.values())
            native_only = {
                rule.qualified_id
                for rule in ruleset.rules
                if rule.qualified_id not in owned
            }
        for path in group:
            score = lint_one(
                path,
                ctx.configs[path],
                ctx.rulesets[path],
                vale_result,
                run_notes,
                native_only,
                diff_scope=ctx.diff_scope,
                comments=ctx.comments,
            )
            note = ctx.locale_notes.get(path)
            if note is not None:
                score.unchecked.append(note)
            scores.append(score)

    if ctx.collection_unchecked:
        if scores:
            scores[0].unchecked.extend(ctx.collection_unchecked)
        else:
            # Every target was skipped (a directory of .rst files with no
            # converter): an incomplete result, not the no-files success.
            first = next(iter(ctx.configs.values()), None)
            scores.append(
                DocumentScore(
                    path="<collection>",
                    profile=first.profile.value if first else Profile.NORMAL.value,
                    words=0,
                    sentences=0,
                    paragraphs=0,
                    passed=False,
                    unchecked=list(ctx.collection_unchecked),
                )
            )
    # Back into the order the caller asked for, since the groups reordered them.
    order = {str(path): index for index, path in enumerate(ctx.paths)}
    scores.sort(key=lambda score: order.get(score.path, 0))
    return scores
