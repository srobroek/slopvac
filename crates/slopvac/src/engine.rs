//! The lint backend: discovery, configuration, the engine and report assembly.
//!
//! The CLI codes against [`Linter`]. [`EngineLinter`] discovers the files, loads the nearest
//! `slopvac.toml` for each, builds one [`slopvac_engine::Engine`] per distinct settings, lints
//! every input and assembles the v3 [`Report`] with its summary and gate.
//!
//! Rules come from [`crate::rule_catalog`]; see that module for what is still a stub.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::sync::Arc;

use slopvac_config::frontmatter::{Policy, Read, read as read_front_matter};
use slopvac_config::{ConfigError, Discovery, LoadedConfig};
use slopvac_engine::discover::{DiscoverError, FileKind, Options, Selection, discover};
use slopvac_engine::{EngineError, Input, Kind};
use slopvac_model::{
    Document, KebabName, NonEmptyString, Notice, NoticeLevel, Report, SchemaVersion,
};
use slopvac_styles::{BuiltinSource, StylePresets};

use crate::errors::CliError;
use crate::lint_settings::{self, Overrides};
use crate::lint_terms::{self, TermInputs};
use crate::redact;
use crate::rule_catalog::Catalog;
use crate::stdin::StdinPlan;
use crate::summary::summarize;

/// What the CLI asks the engine to lint.
#[derive(Debug, Clone, Default)]
pub struct LintRequest {
    /// Project root. Paths outside it are redacted in messages.
    pub root: PathBuf,
    /// Files to lint. Empty with `stdin` set means standard input.
    pub targets: Vec<PathBuf>,
    /// Raw stdin bytes, when `--stdin` was given.
    pub stdin: Option<Vec<u8>>,
    /// Parser name and mode for the stdin document, set with `stdin`.
    pub stdin_plan: Option<StdinPlan>,
    /// `--config`: use this file instead of the nearest `slopvac.toml`.
    pub config: Option<PathBuf>,
    /// `--mode code-comments`: lint the comments of source files.
    pub code_comments: bool,
    /// Settings from the command line.
    pub overrides: Overrides,
}

/// The result of one run.
#[derive(Debug, Clone)]
pub struct RunOutcome {
    /// Documents checked.
    pub documents: usize,
    /// Whether at least one gate failed.
    pub gate_failed: bool,
    /// Documents that could not be checked, or checked only in part.
    pub incomplete: Vec<CliError>,
    /// The v3 report for the documents that were checked.
    pub report: Report,
    /// Text of each checked document by report path, for formats that need columns.
    pub sources: HashMap<String, String>,
}

impl Default for RunOutcome {
    fn default() -> Self {
        Self {
            documents: 0,
            gate_failed: false,
            incomplete: Vec::new(),
            report: assemble(&[], Vec::new()),
            sources: HashMap::new(),
        }
    }
}

/// The report of `documents`, with run-level `notices`.
fn assemble(documents: &[Document], notices: Vec<Notice>) -> Report {
    Report {
        schema_version: SchemaVersion,
        slopvac_version: NonEmptyString::new(env!("CARGO_PKG_VERSION"))
            .expect("the package version is not empty"),
        summary: summarize(documents),
        documents: documents.to_vec(),
        notices,
    }
}

/// The engine contract the CLI depends on.
pub trait Linter {
    /// Lint the request.
    fn lint(&self, request: &LintRequest) -> RunOutcome;

    /// Explain the settings of each input of the request, without linting it.
    fn explain_config(&self, request: &LintRequest) -> ExplainOutcome;
}

/// The result of `--explain-config`.
#[derive(Debug, Clone, Default)]
pub struct ExplainOutcome {
    /// One block per input, each headed by its redacted path.
    pub text: String,
    /// Inputs that could not be read, or a failure that stopped the run.
    pub incomplete: Vec<CliError>,
}

/// The linter backed by `slopvac-engine`.
#[derive(Debug, Clone, Copy, Default)]
pub struct EngineLinter;

/// One input that is ready to lint.
struct Item {
    shown: String,
    text: String,
    kind: Kind,
    /// Config of the file and the file's path relative to the config root.
    config: Option<(Arc<LoadedConfig>, PathBuf)>,
    /// The directory that holds the file, canonical. Not set for standard input.
    dir: Option<PathBuf>,
}

/// The run so far.
#[derive(Default)]
struct Run {
    incomplete: Vec<CliError>,
    notices: Vec<Notice>,
}

impl Run {
    /// Record an input that was not checked: an exit-2 error and a report notice.
    fn skip(&mut self, code: &'static str, shown: &str, message: String) {
        let error = CliError::new(code, message);
        self.notices.push(Notice {
            code: KebabName::new(code).expect("skip codes are kebab-case"),
            level: NoticeLevel::Warning,
            message: NonEmptyString::new(error.message.clone()).expect("messages are not empty"),
            path: Some(shown.to_owned()),
            data: serde_json::Map::new(),
        });
        self.incomplete.push(error);
    }

    /// Record what is wrong with a document's `slopvac:` block: an exit-2 error and a report
    /// notice for each diagnostic. The block then contributes nothing and the document is
    /// still linted. The error text is escaped for a terminal; the notice keeps the raw
    /// text, which each report format escapes for itself.
    fn front_matter_errors(&mut self, item: &Item, read: &Read) {
        for e in block_errors(&item.shown, &item.text, read) {
            self.notices.push(Notice {
                code: KebabName::new(e.code).expect("diagnostic codes are kebab-case"),
                level: NoticeLevel::Warning,
                message: NonEmptyString::new(e.raw).expect("messages are not empty"),
                path: Some(item.shown.clone()),
                data: serde_json::Map::new(),
            });
            self.incomplete.push(CliError::new(e.code, e.escaped));
        }
    }

    /// Record a file the engine could not lint: not checked, so the run exits 2.
    fn skip_engine_error(&mut self, shown: &str, err: &EngineError) {
        // `EngineError` is `#[non_exhaustive]`, so a new variant lands in `lint-failed` until
        // it gets a code of its own.
        let code = match err {
            // The check is incomplete for a reason a pack can fix, so it has a code.
            EngineError::TagLookupBudget { .. } | EngineError::TagBuildBudget { .. } => {
                "context-budget-exceeded"
            }
            _ => "lint-failed",
        };
        self.skip(code, shown, format!("{shown}: {err}"));
    }
}

/// The engine kind for a discovered file, or why there is none.
fn kind_of_file(kind: &FileKind) -> Result<Kind, &'static str> {
    match kind {
        FileKind::Markdown => Ok(Kind::Markdown),
        FileKind::Mdx => Ok(Kind::Mdx),
        FileKind::Rst => Ok(Kind::Rst),
        // STUB(slopvac-8l4.12.28): HTML and plain text have no engine parser yet, and
        // comment-mode rules run once slopvac-8l4.3.26 lands.
        FileKind::Html | FileKind::Text | FileKind::Toml | FileKind::Source(_) => {
            Err("this file type has no engine parser yet")
        }
    }
}

fn kind_of_language(plan: &StdinPlan) -> Result<Kind, &'static str> {
    if plan.mode != "prose" {
        return Err("comment mode has no engine parser yet");
    }
    match plan.language.as_str() {
        "markdown" => Ok(Kind::Markdown),
        "mdx" => Ok(Kind::Mdx),
        "rst" => Ok(Kind::Rst),
        _ => Err("this language has no engine parser yet"),
    }
}

/// Redact every backtick-quoted absolute path in `text`.
///
/// The config diagnostics quote the user's own value in backticks, such as the value of a bad
/// `locale` or an unknown key. When the quoted text is an absolute path, the whole quoted text
/// is replaced with `redact::shown_path` (policies.md, 1.7).
fn redact_quoted(text: &str, root: &Path) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(open) = rest.find('`') {
        let (head, tail) = rest.split_at(open);
        out.push_str(head);
        let tail = &tail[1..];
        let Some(close) = tail.find('`') else {
            out.push('`');
            rest = tail;
            continue;
        };
        let quoted = &tail[..close];
        out.push('`');
        if Path::new(quoted).is_absolute() {
            out.push_str(&redact::shown_path(Path::new(quoted), root));
        } else {
            out.push_str(quoted);
        }
        out.push('`');
        rest = &tail[close + 1..];
    }
    out.push_str(rest);
    out
}

/// A refused config from its structured fields: each diagnostic's message, its
/// `file:line:column` pointer and its help. The source excerpt is left out because it quotes
/// the user's own text, paths included.
fn describe_rejected(rejected: &slopvac_config::Rejected, root: &Path) -> String {
    use std::fmt::Write as _;
    rejected
        .diagnostics
        .iter()
        .enumerate()
        .map(|(i, d)| {
            let (line, column) = d.location(&rejected.text);
            let mut text = if i == 0 {
                String::new()
            } else {
                format!("error[{}]: ", d.code.as_str())
            };
            text.push_str(&redact_quoted(&d.message, root));
            let _ = write!(text, "\n --> {}:{line}:{column}", rejected.file);
            if let Some(help) = &d.help {
                text.push_str("\nhelp: ");
                text.push_str(&redact_quoted(help, root));
            }
            text
        })
        .collect::<Vec<_>>()
        .join("\n")
}

pub(crate) fn config_error(err: &ConfigError, root: &Path) -> CliError {
    let mut message = match err {
        ConfigError::Rejected(rejected) => describe_rejected(rejected, root),
        ConfigError::Io { path, .. } | ConfigError::TooLarge { path, .. } => {
            // The path is the label the caller gave, which may be absolute.
            err.to_string()
                .replace(path.as_str(), &redact::shown_path(Path::new(path), root))
        }
    };
    if err.is_legacy() {
        message.push_str("\nhelp: run `slopvac migrate` to convert it");
    }
    let error = CliError::new(err.code().as_str(), message);
    match budget_data(err) {
        Some(data) => error.with_data(data),
        None => error,
    }
}

/// The `budget`, `limit` and `path` keys of a refused config's budget diagnostic.
///
/// Only `ConfigError::Rejected` carries budget data, and the loader builds it with exactly one
/// diagnostic per refusal, so the first diagnostic with data is the only one. The path needs no
/// further redaction: `slopvac-config` already shows it root-relative, or `<external>/<name>`
/// outside the root, and a test pins that for an `extends` target outside the project.
fn budget_data(err: &ConfigError) -> Option<serde_json::Map<String, serde_json::Value>> {
    let ConfigError::Rejected(rejected) = err else {
        return None;
    };
    let budget = rejected
        .diagnostics
        .iter()
        .find_map(|d| d.data.as_deref())?;
    let mut data = serde_json::Map::new();
    data.insert("budget".into(), budget.budget.as_str().into());
    data.insert("limit".into(), budget.limit.into());
    data.insert("path".into(), budget.path.as_str().into());
    Some(data)
}

/// Finds the config of each directory once.
struct Configs<'a> {
    discovery: Discovery<'a>,
    explicit: Option<Arc<LoadedConfig>>,
}

impl Configs<'_> {
    fn of(&self, dir: &Path) -> Result<Option<Arc<LoadedConfig>>, ConfigError> {
        match &self.explicit {
            Some(config) => Ok(Some(Arc::clone(config))),
            None => self.discovery.nearest(dir),
        }
    }
}

impl Linter for EngineLinter {
    fn lint(&self, request: &LintRequest) -> RunOutcome {
        let mut run = Run::default();
        match prepare(request, &mut run) {
            Ok((rules, items)) => lint_items(request, items, rules, run),
            Err(err) => failed(request, run, &err),
        }
    }

    fn explain_config(&self, request: &LintRequest) -> ExplainOutcome {
        let mut run = Run::default();
        let items = match prepare(request, &mut run) {
            Ok((_, items)) => items,
            Err(err) => {
                run.incomplete.push(err);
                Vec::new()
            }
        };
        let none = LoadedConfig::without_files(request.root.clone());
        let mut text = String::new();
        for item in &items {
            let (config, rel) = match &item.config {
                Some((config, rel)) => (config.as_ref(), rel.clone()),
                None => (&none, PathBuf::from(&item.shown)),
            };
            let mut explained = lint_settings::resolve(config, &rel).explain();
            for entry in &mut explained {
                redact_urls(&mut entry.value);
                for replaced in &mut entry.overridden {
                    redact_urls(&mut replaced.value);
                }
            }
            let root = redact::shown_path(&config.root, &request.root);
            if !text.is_empty() {
                text.push('\n');
            }
            text.push_str(&slopvac_sanitize::line(&item.shown));
            text.push('\n');
            text.push_str(&slopvac_config::render_explain(config, &explained, &root));
        }
        ExplainOutcome {
            text,
            incomplete: run.incomplete,
        }
    }
}

/// Strip user-info and query strings from every URL in a config value before it is printed.
fn redact_urls(value: &mut serde_json::Value) {
    match value {
        serde_json::Value::String(text) => *text = redact::redact_url_value(text),
        serde_json::Value::Array(items) => items.iter_mut().for_each(redact_urls),
        serde_json::Value::Object(map) => map.values_mut().for_each(redact_urls),
        _ => {}
    }
}

/// Load the configs, the rules and the inputs of a run, or say why it cannot start.
fn prepare(request: &LintRequest, run: &mut Run) -> Result<(Catalog, Vec<Item>), CliError> {
    let presets = StylePresets(BuiltinSource);
    let mut configs = Configs {
        discovery: Discovery::new(&presets),
        explicit: None,
    };
    if let Some(given) = &request.config {
        let shown = redact::shown_path(given, &request.root);
        if !request.root.join(given).is_file() {
            return Err(CliError::new(
                "config-not-found",
                format!("--config {shown}: no such file"),
            ));
        }
        // A config that cannot be read lints nothing (policies V7).
        let config = configs
            .discovery
            .explicit_in(&request.root, given)
            .map_err(|err| config_error(&err, &request.root))?;
        configs.explicit = Some(config);
    }
    let rules = Catalog::load()?;
    run.notices
        .extend(validate_configs(request, &configs, &rules)?);
    let items = collect(request, &configs, run)?;
    Ok((rules, items))
}

/// Check every config the run reaches against the catalogue, even when no input is left to
/// lint: the config of each target, of standard input and the one named with `--config`.
/// Returns the warning notice of each unknown rule id.
fn validate_configs(
    request: &LintRequest,
    configs: &Configs<'_>,
    rules: &Catalog,
) -> Result<Vec<Notice>, CliError> {
    let mut dirs: Vec<PathBuf> = Vec::new();
    if request.stdin.is_some() {
        dirs.push(request.root.clone());
    }
    for target in &request.targets {
        let path = request.root.join(target);
        // Every file a target reaches, whether it names a file, a directory or a glob, has
        // its own nearest config. All of them are checked, before any exclusion drops a file.
        if let Ok(found) = discover(
            &[target.to_string_lossy().into_owned()],
            Options::default().with_selection(if request.code_comments {
                Selection::CodeComments
            } else {
                Selection::Prose
            }),
        ) {
            dirs.extend(found.files.iter().filter_map(|f| {
                let parent = f.path.parent()?;
                Some(request.root.join(parent))
            }));
        }
        if path.is_dir() {
            dirs.push(path);
        } else if let Some(parent) = path.parent().filter(|p| p.is_dir()) {
            dirs.push(parent.to_path_buf());
        }
    }
    dirs.sort();
    dirs.dedup();
    if dirs.is_empty() {
        dirs.push(request.root.clone());
    }
    let mut seen = HashSet::new();
    let mut notices = Vec::new();
    for dir in dirs {
        let found = configs
            .of(&dir)
            .map_err(|e| config_error(&e, &request.root))?;
        if let Some(config) = found
            && seen.insert(config.root.clone())
        {
            notices.extend(lint_settings::validate(&config, rules)?);
        }
    }
    Ok(notices)
}

/// An outcome for a run that could not start.
fn failed(_request: &LintRequest, mut run: Run, error: &CliError) -> RunOutcome {
    // The report must not read as a clean run: a notice marks it unsuccessful.
    run.notices.push(Notice {
        code: KebabName::new(error.code)
            .unwrap_or_else(|_| KebabName::new("lint-failed").expect("lint-failed is kebab-case")),
        level: NoticeLevel::Warning,
        message: NonEmptyString::new(error.message.clone())
            .unwrap_or_else(|_| NonEmptyString::new("lint failed").expect("not empty")),
        path: None,
        data: error.data.clone(),
    });
    run.incomplete.push(error.clone());
    RunOutcome {
        incomplete: run.incomplete,
        report: assemble(&[], run.notices),
        ..RunOutcome::default()
    }
}

fn collect(
    request: &LintRequest,
    configs: &Configs<'_>,
    run: &mut Run,
) -> Result<Vec<Item>, CliError> {
    let mut items = Vec::new();
    if let Some(bytes) = &request.stdin {
        collect_stdin(request, bytes, configs, run, &mut items)?;
    }
    collect_targets(request, configs, run, &mut items)?;
    unique_identities(&mut items);
    Ok(items)
}

/// Two files outside the project can share a redacted name such as `<external>/a.md`. Each
/// keeps a distinct identity in the report, so one does not replace the other in the source
/// map that column-aware formats read. Every name in use is reserved first, so a number added
/// to one file's name never lands on another file's own name.
fn unique_identities(items: &mut [Item]) {
    let mut taken: HashSet<String> = items.iter().map(|i| i.shown.clone()).collect();
    let mut first_seen: HashSet<String> = HashSet::new();
    for item in items {
        if first_seen.insert(item.shown.clone()) {
            continue;
        }
        let original = item.shown.clone();
        let mut n = 2;
        let renamed = loop {
            let candidate = match original.strip_prefix("<external>/") {
                Some(rest) => format!("<external>/{n}/{rest}"),
                None => format!("{original}#{n}"),
            };
            if !taken.contains(&candidate) {
                break candidate;
            }
            n += 1;
        };
        taken.insert(renamed.clone());
        item.shown = renamed;
    }
}

/// A discovery failure as one line, with paths in the form every other message uses.
fn discover_message(err: &DiscoverError, root: &Path) -> String {
    let shown = |path: &Path| redact::shown_path(path, root);
    match err {
        DiscoverError::NoSuchTarget(target) => {
            format!("{}: not found", shown(Path::new(target)))
        }
        DiscoverError::UnsupportedSource { path, message } => {
            format!("{}: {message}", shown(path))
        }
        DiscoverError::TooManyAlternatives { pattern, limit } => {
            format!(
                "glob {} expands to more than {limit} alternatives",
                shown(Path::new(pattern))
            )
        }
        DiscoverError::InvalidGlob { pattern, .. } => {
            format!("invalid glob {}", shown(Path::new(pattern)))
        }
        DiscoverError::Walk { path, .. } => {
            format!("{}: cannot walk the directory", shown(path))
        }
    }
}

fn collect_stdin(
    request: &LintRequest,
    bytes: &[u8],
    configs: &Configs<'_>,
    run: &mut Run,
    items: &mut Vec<Item>,
) -> Result<(), CliError> {
    let shown = redact::STDIN_NAME;
    let kind = match &request.stdin_plan {
        Some(plan) => kind_of_language(plan),
        None => Ok(Kind::Markdown),
    };
    match (kind, String::from_utf8(bytes.to_vec())) {
        (Ok(kind), Ok(text)) => items.push(Item {
            shown: shown.to_owned(),
            text,
            kind,
            config: config_for(configs, &request.root, Path::new(shown))?,
            dir: None,
        }),
        (Err(why), _) => run.skip("input-unsupported", shown, format!("{shown}: {why}")),
        (_, Err(_)) => run.skip("input-not-utf8", shown, format!("{shown}: not valid UTF-8")),
    }
    Ok(())
}

/// Read a document found on disk. A symlink was resolved by the caller, so `path` names the
/// target. The read refuses a FIFO or device there instead of blocking on it. On a failure the
/// run records a skip and the result is `None`.
fn read_document(path: &Path, shown: &str, run: &mut Run) -> Option<Vec<u8>> {
    match slopvac_fs::read_capped_regular(
        path,
        slopvac_fs::MAX_DOCUMENT_BYTES,
        slopvac_fs::ReadOptions::new(),
    ) {
        Ok(bytes) => Some(bytes),
        Err(e) if e.input_kind() == Some(slopvac_fs::InputKind::TooLarge) => {
            run.skip(
                "document-too-large",
                shown,
                format!("{shown}: larger than the 64 MiB document limit"),
            );
            None
        }
        Err(_) => {
            run.skip("input-unreadable", shown, format!("{shown}: cannot read"));
            None
        }
    }
}

fn collect_targets(
    request: &LintRequest,
    configs: &Configs<'_>,
    run: &mut Run,
    items: &mut Vec<Item>,
) -> Result<(), CliError> {
    let selection = if request.code_comments {
        Selection::CodeComments
    } else {
        Selection::Prose
    };
    let mut seen = HashSet::new();
    let shower = redact::PathShower::new(&request.root);
    for target in &request.targets {
        let shown_target = redact::shown_path(target, &request.root);
        let found = match discover(
            &[target.to_string_lossy().into_owned()],
            Options::default().with_selection(selection),
        ) {
            Ok(found) => found,
            Err(err) => {
                run.skip(
                    "input-unreadable",
                    &shown_target,
                    discover_message(&err, &request.root),
                );
                continue;
            }
        };
        #[cfg(test)]
        after_discovery::run();
        for skipped in found.skipped {
            let shown = redact::shown_path(&skipped.path, &request.root);
            run.skip(
                "input-unsupported",
                &shown,
                format!("{shown}: {}", skipped.reason),
            );
        }
        for file in found.files {
            let resolved = std::fs::canonicalize(&file.path).ok();
            let canonical = resolved.clone().unwrap_or_else(|| file.path.clone());
            if !seen.insert(canonical.clone()) {
                continue;
            }
            let shown = shower.shown(&file.path, resolved.as_deref());
            let config = config_for(configs, &request.root, &canonical)?;
            // Exclusions apply first, whether the config was found or named with `--config`,
            // so an excluded file is never read, parsed or reported.
            if let Some((loaded, rel)) = &config
                && loaded.is_excluded(rel)
            {
                continue;
            }
            let kind = match kind_of_file(&file.kind) {
                Ok(kind) => kind,
                Err(why) => {
                    run.skip("input-unsupported", &shown, format!("{shown}: {why}"));
                    continue;
                }
            };
            let Some(bytes) = read_document(&canonical, &shown, run) else {
                continue;
            };
            let Ok(text) = String::from_utf8(bytes) else {
                run.skip(
                    "input-not-utf8",
                    &shown,
                    format!("{shown}: not valid UTF-8"),
                );
                continue;
            };
            items.push(Item {
                shown,
                text,
                kind,
                config,
                dir: canonical.parent().map(Path::to_path_buf),
            });
        }
    }
    Ok(())
}

/// The config that applies to `file` and its path relative to the config root. A file outside
/// that root comes back absolute, so the config's root-relative matching rejects it. The path
/// is for matching only; reports show the separate `shown` path.
fn config_for(
    configs: &Configs<'_>,
    root: &Path,
    file: &Path,
) -> Result<Option<(Arc<LoadedConfig>, PathBuf)>, CliError> {
    let absolute = if file.is_absolute() {
        file.to_path_buf()
    } else {
        root.join(file)
    };
    let dir = absolute.parent().unwrap_or(root);
    let dir = if dir.as_os_str().is_empty() {
        root
    } else {
        dir
    };
    let found = configs.of(dir).map_err(|e| config_error(&e, root))?;
    Ok(found.map(|config| {
        let rel = absolute
            .strip_prefix(&config.root)
            .map_or_else(|_| absolute.clone(), Path::to_path_buf);
        (config, rel)
    }))
}

/// One problem in a document's `slopvac:` block, worded without the document's values.
pub(crate) struct BlockError {
    /// The diagnostic's stable code.
    pub(crate) code: &'static str,
    /// `<shown>:<line>:<column>: <key pointer>`, as the document gave the names.
    pub(crate) raw: String,
    /// The same with the file name and the key names escaped for a terminal.
    pub(crate) escaped: String,
}

/// Key paths of the `slopvac:` block that the schema itself names. A key under a map
/// (`rules`, `categories`), an unknown key and an array index come from the document, so a
/// path is shown only up to the last prefix listed here.
const SCHEMA_PATHS: &[&[&str]] = &[
    &["slopvac"],
    &["slopvac", "v"],
    &["slopvac", "genre"],
    &["slopvac", "profile"],
    &["slopvac", "profile", "name"],
    &["slopvac", "profile", "severity_shift"],
    &["slopvac", "locale"],
    &["slopvac", "thresholds"],
    &["slopvac", "thresholds", "max_total_per_100_words"],
    &["slopvac", "thresholds", "max_errors"],
    &["slopvac", "thresholds", "max_warnings"],
    &["slopvac", "thresholds", "min_score"],
    &["slopvac", "thresholds", "max_unicode_dashes"],
    &["slopvac", "categories"],
    &["slopvac", "rules"],
    &["slopvac", "terms"],
    &["slopvac", "terms", "allow"],
];

/// The JSON pointer of `path` cut at the first segment the schema does not own, `/` when no
/// segment is owned.
fn schema_pointer(path: &[String]) -> String {
    let owned = (1..=path.len())
        .take_while(|&n| {
            SCHEMA_PATHS.iter().any(|known| {
                known
                    .iter()
                    .copied()
                    .eq(path[..n].iter().map(String::as_str))
            })
        })
        .count();
    if owned == 0 {
        return "/".to_owned();
    }
    path[..owned].iter().fold(String::new(), |mut acc, seg| {
        acc.push('/');
        acc.push_str(seg);
        acc
    })
}

/// The problems that `read` found in the block of the document `text`, shown as `shown`. Only
/// the code, the position and the key path are reported: a diagnostic's own message quotes
/// the offending value, and front matter values stay out of error output (policies 1.7).
pub(crate) fn block_errors(shown: &str, text: &str, read: &Read) -> Vec<BlockError> {
    read.diagnostics
        .iter()
        .map(|d| {
            let (line, column) = d.location(text);
            let pointer = schema_pointer(&d.path);
            BlockError {
                code: d.code.as_str(),
                raw: format!("{shown}:{line}:{column}: {pointer}"),
                escaped: format!(
                    "{}:{line}:{column}: {}",
                    slopvac_sanitize::line(shown),
                    slopvac_sanitize::line(&pointer)
                ),
            }
        })
        .collect()
}

/// The `slopvac:` block of the item's front matter, read under the project's front matter
/// policy. A top-level `genre` key is ordinary data and never counts.
fn read_block(item: &Item) -> Read {
    let config = item.config.as_ref().map(|(config, _)| &**config);
    read_block_under(&item.text, &item.shown, config)
}

/// Read the `slopvac:` block of `text` under the policy of `config`, or the core defaults
/// when no config applies.
pub(crate) fn read_block_under(text: &str, shown: &str, config: Option<&LoadedConfig>) -> Read {
    let policy = config.map_or_else(Policy::core, Policy::from_config);
    read_front_matter(text, shown, &policy)
}

/// The genre that a read block sets, when the policy allows it and the block is valid.
pub(crate) fn declared_genre(read: &Read) -> Option<String> {
    read.settings
        .iter()
        .rfind(|s| s.path == ["genre"])
        .and_then(|s| s.value.as_str().map(str::to_owned))
}

/// A config-relative path as the forward-slash text that `files` patterns match against.
fn rel_text(rel: &Path) -> String {
    rel.components()
        .map(|c| c.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
}

/// Settings and the indexes of the items that share them.
type Groups = BTreeMap<String, (slopvac_engine::Settings, TermInputs, Vec<usize>)>;

/// Group the items by their settings: one engine per distinct settings.
fn group_by_settings(
    request: &LintRequest,
    items: &[Item],
    rules: &Catalog,
) -> Result<Groups, CliError> {
    let mut groups = Groups::new();
    let none = LoadedConfig::without_files(request.root.clone());
    for (index, item) in items.iter().enumerate() {
        let (config, rel) = match &item.config {
            Some((config, rel)) => (config.as_ref(), rel.clone()),
            None => (&none, PathBuf::from(&item.shown)),
        };
        let resolved = lint_settings::resolve(config, &rel);
        let files = config_files(config);
        let mut settings = lint_settings::build(
            rules,
            &resolved,
            lint_settings::config_sources(&files),
            &request.overrides,
        )?;
        let terms = lint_terms::inputs(&resolved, &config.root);
        settings.genre_assignments = Some(lint_settings::genre_assignments(config));
        groups
            .entry(format!("{settings:?}{terms:?}"))
            .or_insert_with(|| (settings, terms, Vec::new()))
            .2
            .push(index);
    }
    Ok(groups)
}

/// The directories an RST interpreter is never taken from: the working directory, the
/// directory of every input and of every named directory, and the repository root of each.
/// A repository outside the working directory is untrusted code, and a `python` it ships on
/// `PATH` must not run.
fn project_roots(request: &LintRequest, items: &[Item]) -> Vec<PathBuf> {
    let mut roots: Vec<PathBuf> = vec![request.root.clone()];
    let mut starts: Vec<PathBuf> = items.iter().filter_map(|i| i.dir.clone()).collect();
    for target in &request.targets {
        let absolute = request.root.join(target);
        if let Ok(dir) = std::fs::canonicalize(&absolute)
            && dir.is_dir()
        {
            starts.push(dir);
        }
    }
    for start in starts {
        if let Some(repo) = start.ancestors().find(|d| d.join(".git").exists()) {
            roots.push(repo.to_path_buf());
        }
        roots.push(start);
    }
    roots.sort();
    roots.dedup();
    roots
}

fn lint_items(request: &LintRequest, items: Vec<Item>, rules: Catalog, mut run: Run) -> RunOutcome {
    let groups = match group_by_settings(request, &items, &rules) {
        Ok(groups) => groups,
        Err(err) => return failed(request, run, &err),
    };

    let mut documents: Vec<Option<Document>> = vec![None; items.len()];
    let mut spare = Some(rules);
    for (settings, terms, indexes) in groups.into_values() {
        // The engine owns its rule sets, and a set does not clone: reload them for later groups.
        let sets = match spare.take().map_or_else(Catalog::load, Ok) {
            Ok(catalog) => catalog.into_sets(),
            Err(err) => return failed(request, run, &err),
        };
        let engine = match lint_terms::build_engine(sets, settings, &terms, &request.root) {
            Ok(engine) => engine.with_project_roots(project_roots(request, &items)),
            Err(err) => return failed(request, run, &err),
        };
        let relatives: Vec<Option<String>> = indexes
            .iter()
            .map(|&i| items[i].config.as_ref().map(|(_, rel)| rel_text(rel)))
            .collect();
        let reads: Vec<Read> = indexes.iter().map(|&i| read_block(&items[i])).collect();
        for (&i, read) in indexes.iter().zip(&reads) {
            run.front_matter_errors(&items[i], read);
        }
        let declared: Vec<Option<String>> = reads.iter().map(declared_genre).collect();
        let inputs: Vec<Input<'_>> = indexes
            .iter()
            .zip(relatives.iter().zip(&declared))
            .map(|(&i, (rel, genre))| {
                let mut input =
                    Input::new(&items[i].shown, &items[i].text).with_kind(items[i].kind);
                if let Some(rel) = rel {
                    input = input.with_relative_path(rel);
                }
                if let Some(genre) = genre {
                    input = input.with_declared_genre(genre);
                }
                input
            })
            .collect();
        for (&index, result) in indexes.iter().zip(engine.lint_all_with_notices(&inputs)) {
            match result {
                Ok((document, notices)) => {
                    // Extraction notices of unsupported content: shown, never a failure.
                    run.notices.extend(notices);
                    documents[index] = Some(document);
                }
                Err(err) => {
                    run.skip_engine_error(&items[index].shown, &err);
                }
            }
        }
    }

    let documents: Vec<Document> = documents.into_iter().flatten().collect();
    for document in &documents {
        for notice in &document.unchecked {
            if notice.level == NoticeLevel::Warning {
                // Part of the check did not run, so the result cannot establish a pass.
                run.incomplete.push(CliError::new(
                    "check-incomplete",
                    format!(
                        "{}: {}: {}",
                        document.path,
                        notice.code.as_str(),
                        notice.message
                    ),
                ));
            }
        }
    }
    let sources = items
        .into_iter()
        .map(|item| (item.shown, item.text))
        .collect();
    RunOutcome {
        documents: documents.len(),
        gate_failed: documents.iter().any(|d| !d.gate.is_passed()),
        incomplete: run.incomplete,
        report: assemble(&documents, run.notices),
        sources,
    }
}

/// The language server's linter for the project config found from `root`: the shipped
/// rules, the term-casing pack, the settings, the project's terms files and the blocklists,
/// built the same way `slopvac lint` builds an engine. The notices are the warnings about the
/// config, which the language server shows to the client.
///
/// # Errors
/// The config error, `terms-invalid`, or `rules-unavailable`.
pub fn project_linter(root: &Path) -> Result<ProjectServer, CliError> {
    let core = Catalog::load()?;
    let presets = StylePresets(BuiltinSource);
    let discovery = Discovery::new(&presets);
    let found = discovery
        .nearest(root)
        .map_err(|e| config_error(&e, root))?;
    let (config, files) = match &found {
        Some(config) => (config.as_ref().clone(), config_files(config)),
        None => (LoadedConfig::without_files(root.to_path_buf()), Vec::new()),
    };
    let notices = lint_settings::validate(&config, &core)?;
    let resolved = lint_settings::resolve(&config, Path::new(""));
    let settings = lint_settings::build(
        &core,
        &resolved,
        lint_settings::config_sources(&files),
        &Overrides::default(),
    )?;
    let terms = lint_terms::inputs(&resolved, &config.root);
    let sets = core.into_sets();
    let reasons = slopvac_lsp::exception_names(&sets);
    let engine = lint_terms::build_engine(sets, settings, &terms, root)?;
    let checks: Vec<Arc<dyn slopvac_lsp::Check>> = vec![Arc::new(
        slopvac_lsp::FrontMatterCheck::new(Policy::from_config(&config)),
    )];
    Ok(ProjectServer {
        linter: slopvac_lsp::EngineLinter::from_engine(engine, reasons),
        notices,
        checks,
    })
}

/// What the language server needs from the project: the engine, the config warnings and the
/// extra checks it runs next to the engine. Term casing comes from the engine.
pub struct ProjectServer {
    /// The engine linter.
    pub linter: slopvac_lsp::EngineLinter,
    /// Warnings about the config.
    pub notices: Vec<Notice>,
    /// Front-matter validation.
    pub checks: Vec<Arc<dyn slopvac_lsp::Check>>,
}

/// The display name of each config file and whether it was pulled in by `extends`.
fn config_files(config: &LoadedConfig) -> Vec<(String, bool)> {
    config
        .files
        .iter()
        .map(|f| {
            (
                f.display.clone(),
                f.layer == slopvac_model::ConfigLayer::Extends,
            )
        })
        .collect()
}

/// A test seam: code that runs once discovery has listed the files and before they are read,
/// so a test can change a file in that window deterministically.
#[cfg(test)]
mod after_discovery {
    use std::cell::RefCell;

    type Hook = Box<dyn FnOnce()>;

    thread_local! {
        static HOOK: RefCell<Option<Hook>> = const { RefCell::new(None) };
    }

    pub(super) fn set(hook: Hook) {
        HOOK.with(|h| *h.borrow_mut() = Some(hook));
    }

    pub(super) fn run() {
        if let Some(hook) = HOOK.with(|h| h.borrow_mut().take()) {
            hook();
        }
    }
}

#[cfg(test)]
mod read_tests {
    use super::*;
    use crate::lint_settings::Overrides;

    fn request(root: &Path, target: &Path) -> LintRequest {
        LintRequest {
            root: root.to_path_buf(),
            targets: vec![target.to_path_buf()],
            stdin: None,
            stdin_plan: None,
            config: None,
            code_comments: false,
            overrides: Overrides::default(),
        }
    }

    /// Run the public linter on a worker thread, with `hook` installed on that thread. When it
    /// blocks, the FIFO at `fifo` is opened without blocking to wake it, and the test fails.
    fn lint_within_timeout(
        fifo: &Path,
        request: LintRequest,
        hook: Option<Box<dyn FnOnce() + Send>>,
    ) -> RunOutcome {
        let probe = fifo.to_path_buf();
        within_timeout(&probe, move || {
            if let Some(hook) = hook {
                after_discovery::set(hook);
            }
            EngineLinter.lint(&request)
        })
    }

    /// Run `f` on a worker thread and return its result. A panic re-raises at once; a worker
    /// that has not finished after five seconds gets the FIFO's write end opened without
    /// blocking, so a reader stuck in `open` wakes, and the test then fails.
    fn within_timeout<T: Send + 'static>(fifo: &Path, f: impl FnOnce() -> T + Send + 'static) -> T {
        use std::os::unix::fs::OpenOptionsExt;
        use std::sync::mpsc::{self, RecvTimeoutError};
        use std::time::Duration;

        const O_NONBLOCK: i32 = if cfg!(target_os = "linux") {
            0o4000
        } else {
            0x4
        };
        const LIMIT: Duration = Duration::from_secs(5);

        let (tx, rx) = mpsc::channel();
        let worker = std::thread::spawn(move || {
            let _ = tx.send(f());
        });
        match rx.recv_timeout(LIMIT) {
            Ok(value) => {
                worker.join().expect("the worker finished");
                value
            }
            Err(RecvTimeoutError::Disconnected) => match worker.join() {
                Err(panic) => std::panic::resume_unwind(panic),
                Ok(()) => panic!("the worker ended without a result"),
            },
            Err(RecvTimeoutError::Timeout) => {
                // ENXIO means no reader is waiting, so there is nothing to wake.
                let _writer = std::fs::OpenOptions::new()
                    .write(true)
                    .custom_flags(O_NONBLOCK)
                    .open(fifo);
                match rx.recv_timeout(LIMIT) {
                    Ok(_) | Err(RecvTimeoutError::Disconnected) => {
                        let _ = worker.join();
                        panic!("the read blocked on a FIFO until it was woken");
                    }
                    Err(RecvTimeoutError::Timeout) => panic!("the read blocked on a FIFO"),
                }
            }
        }
    }

    /// Discovery lists a regular file; the file becomes a FIFO before the read. The run must
    /// report it as unreadable and finish.
    #[test]
    fn a_file_that_becomes_a_fifo_after_discovery_is_unreadable() {
        let dir = tempfile::tempdir().unwrap();
        let root = std::fs::canonicalize(dir.path()).unwrap();
        let doc = root.join("a.md");
        std::fs::write(&doc, "Hello there.\n").unwrap();
        let swap = doc.clone();
        let outcome = lint_within_timeout(
            &doc,
            request(&root, &doc),
            Some(Box::new(move || {
                std::fs::remove_file(&swap).unwrap();
                assert!(
                    std::process::Command::new("mkfifo")
                        .arg(&swap)
                        .status()
                        .unwrap()
                        .success()
                );
            })),
        );
        let codes: Vec<&str> = outcome.incomplete.iter().map(|e| e.code).collect();
        assert_eq!(codes, ["input-unreadable"]);
        assert_eq!(outcome.documents, 0);
    }

    #[test]
    fn a_regular_file_is_linted() {
        let dir = tempfile::tempdir().unwrap();
        let root = std::fs::canonicalize(dir.path()).unwrap();
        let doc = root.join("a.md");
        std::fs::write(&doc, "Hello there.\n").unwrap();
        let outcome = lint_within_timeout(&doc, request(&root, &doc), None);
        assert_eq!(outcome.incomplete.len(), 0);
        assert_eq!(outcome.documents, 1);
    }

    /// A target that is a symlink to a regular file is still linted.
    #[test]
    fn a_symlink_to_a_regular_file_is_linted() {
        let dir = tempfile::tempdir().unwrap();
        let root = std::fs::canonicalize(dir.path()).unwrap();
        let real = root.join("real.md");
        std::fs::write(&real, "Hello there.\n").unwrap();
        let link = root.join("link.md");
        std::os::unix::fs::symlink(&real, &link).unwrap();
        let outcome = lint_within_timeout(&link, request(&root, &link), None);
        assert_eq!(outcome.incomplete.len(), 0);
        assert_eq!(outcome.documents, 1);
    }

    /// A target reached through a symlink to an external directory, which vanishes after
    /// discovery, cannot be canonicalized. Its notice must not show the external directory.
    #[test]
    fn a_vanished_file_behind_an_external_symlink_hides_the_external_directory() {
        let dir = tempfile::tempdir().unwrap();
        let top = std::fs::canonicalize(dir.path()).unwrap();
        let root = top.join("proj");
        let external = top.join("elsewhere").join("sentinel-private");
        std::fs::create_dir_all(&root).unwrap();
        std::fs::create_dir_all(&external).unwrap();
        std::fs::write(external.join("a.md"), "Hello there.\n").unwrap();
        std::os::unix::fs::symlink(top.join("elsewhere"), root.join("link")).unwrap();
        let target = root.join("link").join("sentinel-private").join("a.md");
        let gone = external.join("a.md");
        let outcome = lint_within_timeout(
            &root.join("probe-fifo"),
            request(&root, &target),
            Some(Box::new(move || std::fs::remove_file(&gone).unwrap())),
        );
        let text = format!("{:?}", outcome.incomplete);
        assert!(text.contains("<external>/a.md"), "{text}");
        assert!(!text.contains("sentinel-private"), "{text}");
    }
}

#[cfg(test)]
mod skip_tests {
    use super::*;
    use rstest::rstest;
    use slopvac_model::PositionError;
    use slopvac_parse::ParseError;
    use slopvac_pcre2::MatchError;
    use slopvac_text::TextError;

    /// Every `EngineError` variant. The enum is `#[non_exhaustive]` across crates, so the
    /// compiler cannot force this list to grow: add a case when the engine adds a variant.
    #[rstest]
    #[case::parse(EngineError::from(ParseError::Mdx("x".into())), "lint-failed")]
    #[case::text(
        EngineError::from(TextError::from(MatchError::MatchLimit { limit: 1 })),
        "lint-failed"
    )]
    #[case::context(EngineError::Context("x".into()), "lint-failed")]
    #[case::position(EngineError::from(PositionError::PastEnd(9)), "lint-failed")]
    #[case::bad_range(EngineError::BadRange("x".into()), "lint-failed")]
    #[case::tag_lookup_budget(
        EngineError::TagLookupBudget { limit: 16_384 },
        "context-budget-exceeded"
    )]
    #[case::tag_build_budget(
        EngineError::TagBuildBudget { limit: 65_536 },
        "context-budget-exceeded"
    )]
    #[case::terms(EngineError::Terms("x".into()), "lint-failed")]
    #[case::internal(EngineError::Internal("x".into()), "lint-failed")]
    fn an_engine_error_leaves_the_file_unchecked_and_the_run_incomplete(
        #[case] err: EngineError,
        #[case] code: &str,
    ) {
        let mut run = Run::default();
        run.skip_engine_error("docs/a.md", &err);

        let codes: Vec<&str> = run.incomplete.iter().map(|e| e.code).collect();
        assert_eq!(codes, [code]);
        assert_eq!(run.notices.len(), 1);
        assert_eq!(run.notices[0].code.as_str(), code);
        assert_eq!(run.notices[0].level, NoticeLevel::Warning);
        assert_eq!(run.notices[0].path.as_deref(), Some("docs/a.md"));
    }
}
