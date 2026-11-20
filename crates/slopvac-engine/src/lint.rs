//! The engine: rules in, a scored document out.
//!
//! One [`Engine`] holds the loaded rules, the resolved [`Settings`], the exception
//! detectors, the context taggers and any diagram checkers. [`Engine::lint`] runs them over
//! one [`Input`] and returns the `slopvac-model` [`Document`] that the report contract
//! describes. [`Engine::lint_all`] runs many inputs in parallel and keeps their order.

use std::collections::{HashMap, HashSet};
use std::ops::Range;
use std::sync::Arc;

use frontmatter_spans::{FrontMatter, detect};
use rayon::prelude::*;
use slopvac_comments::Language;
use slopvac_context::{
    DeclaredContextTagger, DeclaredGenre, GenreRegistry, ResolveOptions, TagIndex, TagRegistry,
};
use slopvac_diagrams::{
    Extraction, ExtractionStatus, Format as DiagramFormat, Signal, extract, extract_fenced,
};
use slopvac_model::{
    AiSignal, BomMode, CategoryId, ContextTag, Contexts, Document, Edit, Extent, Finding, Fix,
    GenreId, GenreReason, GenreResult, GenreSource, KebabName, LineCol, NonEmptyString, Notice,
    NoticeLevel, PackId, PositionError, RuleId, RuleProvenance, Severity, SourceIndex, Span,
};
use slopvac_parse::{BlockKind, Document as Parsed, ParseError, parse_markdown, parse_mdx};
use slopvac_rules::{LoadedRule, Match, MatchKind, RuleSet, Scope};
use slopvac_terms::{Blocklist, TermSet};
use slopvac_text::{TextError, TextType};

use crate::capitalization::{self, SentenceCase};
use crate::comments;
use crate::diagrams::{self, DiagramChecker, DiagramHit, DiagramInput, DiagramRule, SignalChecker};
use crate::directives::{Directives, Lines, Target, scan};
use crate::exceptions::{Detectors, MatchSite, TextOrigin};
use crate::matcher_work;
use crate::matching::{
    LazyReplacements, allowlisted, format_message, is_all_caps, is_single_replacement,
};
use crate::metrics::{self, Subject};
use crate::prepare::{Prepared, Unit, with_html_prose};
use crate::rst::{RstAdapter, RstError, RstOptions};
use crate::score::{CategoryInfo, score_document};
use crate::settings::{Level, Settings};
use crate::skip::{self, SkipRanges};
use crate::structure::{self, Check};
use crate::tagging;
use crate::terms;

mod casing;
mod vocabulary;
use vocabulary::Vocabulary;

/// The id of the finding for a directive that does not hold.
const INVALID_SUPPRESSION: &str = "meta.invalid-suppression";
/// The pack that owns the findings of the engine itself.
const ENGINE_PACK: &str = "core";

/// What kind of file an [`Input`] is.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum Kind {
    /// Markdown.
    Markdown,
    /// MDX.
    Mdx,
    /// reStructuredText, read through docutils (see [`crate::rst`]).
    Rst,
    /// A source file in this language. Only its comments are prose: see
    /// [`Input::comments`].
    Comments(Language),
    /// A diagram file. Only diagram rules read it.
    Diagram(DiagramFormat),
}

/// One file to lint.
///
/// Build one with [`Input::new`] and the `with_*` setters, or with a shortcut such as
/// [`Input::markdown`]. The struct is `#[non_exhaustive]`, so a new field is not a
/// breaking change for callers.
#[derive(Debug, Clone)]
#[non_exhaustive]
pub struct Input<'a> {
    /// The path, as shown in the report.
    pub path: &'a str,
    /// The file text.
    pub source: &'a str,
    /// The kind of file.
    pub kind: Kind,
    /// How a leading byte order mark counts in columns.
    pub bom: BomMode,
    /// The path relative to the project root, for matching `[[genres]]` file patterns. When
    /// unset, patterns match against [`Input::path`].
    pub relative_path: Option<&'a str>,
    /// The genre the document declares for itself, as the config reader validated it and the
    /// project's front matter policy allows. The engine never reads a genre from the raw
    /// front matter; without this, a document declares none.
    pub declared_genre: Option<&'a str>,
}

impl<'a> Input<'a> {
    /// A Markdown file read from disk. Change the rest with the `with_*` setters.
    #[must_use]
    pub const fn new(path: &'a str, source: &'a str) -> Self {
        Self {
            path,
            source,
            kind: Kind::Markdown,
            bom: BomMode::Disk,
            relative_path: None,
            declared_genre: None,
        }
    }

    /// The same input with the genre its front matter declares, already validated against
    /// the project's policy.
    #[must_use]
    pub const fn with_declared_genre(mut self, genre: &'a str) -> Self {
        self.declared_genre = Some(genre);
        self
    }

    /// The same input with its path relative to the project root.
    #[must_use]
    pub const fn with_relative_path(mut self, relative_path: &'a str) -> Self {
        self.relative_path = Some(relative_path);
        self
    }

    /// The same input with another file kind.
    #[must_use]
    pub const fn with_kind(mut self, kind: Kind) -> Self {
        self.kind = kind;
        self
    }

    /// The same input with another byte order mark mode.
    #[must_use]
    pub const fn with_bom(mut self, bom: BomMode) -> Self {
        self.bom = bom;
        self
    }

    /// The same input with other file text, for a re-lint after an edit.
    #[must_use]
    pub const fn with_source(mut self, source: &'a str) -> Self {
        self.source = source;
        self
    }

    /// The same input with another path.
    #[must_use]
    pub const fn with_path(mut self, path: &'a str) -> Self {
        self.path = path;
        self
    }

    /// A Markdown file read from disk.
    #[must_use]
    pub const fn markdown(path: &'a str, source: &'a str) -> Self {
        Self::new(path, source)
    }

    /// An MDX file read from disk.
    #[must_use]
    pub const fn mdx(path: &'a str, source: &'a str) -> Self {
        Self {
            kind: Kind::Mdx,
            ..Self::markdown(path, source)
        }
    }

    /// An RST file read from disk.
    #[must_use]
    pub const fn rst(path: &'a str, source: &'a str) -> Self {
        Self {
            kind: Kind::Rst,
            ..Self::markdown(path, source)
        }
    }

    /// A source file read from disk, linted in code-comment mode.
    ///
    /// Only the prose of the comments is read, and a finding points at its exact bytes in
    /// `source`. As in 2.x `--mode code-comments`:
    ///
    /// - The tokens, pattern and substitution rules run, and the capitalization rules the
    ///   engine runs. A comment is the unit for every one of them, whatever the `scope` of
    ///   the rule, and its text carries the context `code-comment`.
    /// - Every other active rule is listed in one `info` notice, `comment-rules-not-run`,
    ///   with their ids in `data.rules`. The run stays complete.
    /// - An inline directive in a comment covers the comment block it starts or precedes. A
    ///   directive indented as a Markdown code example is an example and does nothing.
    ///
    /// A Python docstring, the string that opens a module, class or function body, is read.
    /// Other strings are code. See [`slopvac_comments`] for what a comment is, and
    /// [`EngineError::Comments`] for the work limits.
    #[must_use]
    pub const fn comments(path: &'a str, source: &'a str, language: Language) -> Self {
        Self {
            kind: Kind::Comments(language),
            ..Self::markdown(path, source)
        }
    }

    /// A diagram file read from disk.
    #[must_use]
    pub const fn diagram(path: &'a str, source: &'a str, format: DiagramFormat) -> Self {
        Self {
            kind: Kind::Diagram(format),
            ..Self::markdown(path, source)
        }
    }
}

/// Why a document could not be linted.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[non_exhaustive]
pub enum EngineError {
    /// The document did not parse.
    #[error(transparent)]
    Parse(#[from] ParseError),
    /// A pattern failed while matching, for example on a match limit.
    #[error(transparent)]
    Text(#[from] TextError),
    /// A context tagger failed.
    #[error("context tagger failed: {0}")]
    Context(String),
    /// A computed position was not valid for the file.
    #[error(transparent)]
    Position(#[from] PositionError),
    /// A diagram checker returned a range that is reversed or outside the file and the
    /// prose it was given.
    #[error("diagram checker returned a bad range: {0}")]
    BadRange(String),
    /// Context lookups looked at more tags than the document allows, so the findings that
    /// depend on them cannot be trusted and the document is not checked. A pack that puts many
    /// kinds of tag on one table cell, with rules that match across the cell's lines, causes
    /// it.
    #[error(
        "context lookups passed their budget of {limit} tag looks: the document is not checked"
    )]
    TagLookupBudget {
        /// The looks the document was allowed.
        limit: usize,
    },
    /// The document holds more context tags than its size allows, so no index was built and
    /// the document is not checked. A very large document of very short sentences causes it.
    #[error("the document has more than {limit} context tags: the document is not checked")]
    TagBuildBudget {
        /// The tags the document was allowed.
        limit: usize,
    },
    /// A terms file could not be read or is not valid.
    #[error("terms file: {0}")]
    Terms(String),
    /// The comments of a source file could not be extracted within the work limits of
    /// `slopvac-comments`, so the file is incomplete.
    #[error("comment extraction: {0}")]
    Comments(String),
    /// A value the engine built broke a model invariant. This is a bug.
    #[error("internal error: {0}")]
    Internal(String),
}

/// A rule that runs.
struct Active {
    pub(crate) set: usize,
    pub(crate) category: usize,
    pub(crate) rule: usize,
    severity: Severity,
    replacements: LazyReplacements,
}

impl Active {
    fn new(set: usize, category: usize, rule: usize, severity: Severity) -> Self {
        Self {
            set,
            category,
            rule,
            severity,
            replacements: LazyReplacements::default(),
        }
    }
}

/// A diagram rule that runs.
struct ActiveDiagram {
    severity: Severity,
    /// Where the loaded rule is, as set, category and rule. A rule of a custom checker has no
    /// loaded rule.
    at: Option<(usize, usize, usize)>,
}

/// An active rule of a kind, style or metric the engine does not run.
struct NotRun {
    kind: &'static str,
    /// The qualified id of the rule.
    id: RuleId,
    /// The genres the rule is limited to, if any.
    genres: Option<Vec<GenreId>>,
}

impl NotRun {
    fn of(kind: &'static str, id: &RuleId, rule: &slopvac_rules::Rule) -> Self {
        Self {
            kind,
            id: id.clone(),
            genres: rule
                .applies_to
                .as_ref()
                .and_then(|a| a.genres.as_ref())
                .map(|g| g.iter().cloned().collect()),
        }
    }
}

/// Where a rule id points.
enum Catalog {
    Loaded(usize),
    Diagram,
}

/// The engine.
pub struct Engine {
    pub(crate) sets: Vec<Arc<RuleSet>>,
    /// The blocklist the vocabulary rules enforce, kept to rebuild a restricted engine.
    pub(crate) blocklist: Blocklist,
    pub(crate) settings: Settings,
    detectors: Detectors,
    tagger: TagRegistry,
    /// The genres a document is matched to, when the settings ask for per-document genres.
    genres: Option<GenreRegistry>,
    /// The contexts the run's genre declares, when documents do not choose their own genre.
    run_declared: Option<DeclaredContextTagger>,
    /// The diagram checkers, each with the ids of the rules it reports.
    checkers: Vec<(Box<dyn DiagramChecker>, Vec<RuleId>)>,
    /// Lexical rules that run.
    active: Vec<Active>,
    /// Vocabulary rules that run. They share one sweep over the word blocklist.
    vocabulary_rules: Vec<Active>,
    /// The blocklist sweep and the notices about it.
    vocabulary: Vocabulary,
    /// Term-casing rules that run.
    casing_rules: Vec<Active>,
    /// The terms the casing rules enforce.
    pub(crate) terms: TermSet,
    /// Metric rules that run.
    metrics: Vec<Active>,
    /// Structure rules that run, with their checks.
    structure: Vec<(Active, Check)>,
    /// Diagram rules that run, by id.
    diagram_rules: HashMap<RuleId, ActiveDiagram>,
    /// The rules that run a signal of `slopvac-diagrams`.
    signal_rules: Vec<(Signal, DiagramRule)>,
    /// Every known rule id.
    catalog: HashMap<String, Catalog>,
    /// Ids of rules that run, including the ones that produce no finding here.
    pub(crate) running: HashSet<String>,
    /// Active rules the engine cannot run. Each document is told about those that apply to it.
    not_run: Vec<NotRun>,
    categories: std::collections::BTreeMap<CategoryId, CategoryInfo>,
    /// How RST files are read, and the adapter built from it. The adapter finds its
    /// interpreter on the first file.
    rst_options: RstOptions,
    rst: RstAdapter,
}

/// Whether the engine matches rules of this kind in the text of a unit.
fn runs_lexically(kind: MatchKind, m: &Match) -> bool {
    match kind {
        MatchKind::Tokens | MatchKind::Pattern | MatchKind::Substitution => true,
        MatchKind::Capitalization => {
            matches!(m, Match::Capitalization(c) if capitalization::runs(c.style))
        }
        _ => false,
    }
}

/// Notice codes for input that an extractor could not read in full. All extractors share
/// the family, and this table is the one place that spells the strings.
pub mod extract_code {
    /// Valid content inside a supported input that the extractor does not read, such as a
    /// diagram type. An info notice at the root of the report; the run stays complete.
    pub const UNSUPPORTED: &str = "extract-unsupported";
    /// The input is not well formed. A warning in `unchecked`; the run is incomplete.
    pub const MALFORMED: &str = "extract-malformed";
    /// A size or work limit stopped the read. A warning in `unchecked`; the run is incomplete.
    pub const BUDGET: &str = "extract-budget";
    /// An extractor plugin returned output that breaks the protocol. Reserved: the
    /// built-in extractors never emit it.
    pub const OUTPUT_INVALID: &str = "extract-output-invalid";
}

/// A linted document and its run-level notices, or why the input could not be linted.
pub type LintOutcome = Result<(Document, Vec<Notice>), EngineError>;

/// The `data.kind` of an `extract-unsupported` notice: the format of the diagram that was
/// not read.
const fn format_name(format: DiagramFormat) -> &'static str {
    match format {
        DiagramFormat::Mermaid => "mermaid",
        DiagramFormat::PlantUml => "plantuml",
        DiagramFormat::Excalidraw => "excalidraw",
        DiagramFormat::Drawio => "drawio",
        DiagramFormat::DrawioSvg => "drawio-svg",
        DiagramFormat::DrawioPng => "drawio-png",
    }
}

/// What the diagram pass found in one input.
#[derive(Default)]
struct DiagramResult {
    findings: Vec<Finding>,
    /// Warnings for diagrams that were malformed or over a limit.
    unchecked: Vec<Notice>,
    /// Info notices for diagrams of an unsupported type.
    notices: Vec<Notice>,
}

/// The `unrun` key of capitalization rules in a style the engine does not run.
const CAPITALIZATION: &str = "capitalization";

fn not_run_notice(kind: &str, rules: &[&RuleId]) -> Result<Notice, EngineError> {
    let count = rules.len();
    if kind == CAPITALIZATION {
        // A style that cannot run would otherwise pass in silence, so the check is incomplete.
        return notice(
            "rule-style-not-implemented",
            NoticeLevel::Warning,
            format!(
                "{count} active {kind} rule(s) did not run: the engine runs only the sentence \
                 style"
            ),
        );
    }
    // The rules are an info notice's data: the run read the input, so it stays complete.
    let mut ids: Vec<&str> = rules.iter().map(|id| id.as_str()).collect();
    ids.sort_unstable();
    let data = serde_json::Map::from_iter([(
        "rules".to_owned(),
        ids.iter()
            .map(|id| serde_json::Value::String((*id).to_owned()))
            .collect(),
    )]);
    Ok(notice(
        "rule-kind-not-implemented",
        NoticeLevel::Info,
        format!(
            "{count} active {kind} rule(s) did not run: the engine does not run {kind} rules yet"
        ),
    )?
    .with_data(data))
}

fn level_of(settings: &Settings, id: &RuleId, category: &CategoryId, shipped: Severity) -> Level {
    settings
        .rule_levels
        .get(id)
        .copied()
        .or_else(|| settings.categories.get(category).and_then(|d| d.level))
        // The genre chain and the rule definition are the levels the profile shifts.
        .unwrap_or_else(|| {
            settings
                .genre_levels
                .get(id)
                .copied()
                .unwrap_or(Level::On(shipped))
                .shifted(settings.severity_shift)
        })
}

fn notice(code: &str, level: NoticeLevel, message: String) -> Result<Notice, EngineError> {
    Ok(Notice {
        code: KebabName::new(code).map_err(|e| EngineError::Internal(e.to_string()))?,
        level,
        message: NonEmptyString::new(message).map_err(|e| EngineError::Internal(e.to_string()))?,
        path: None,
        data: serde_json::Map::new(),
    })
}

impl Engine {
    /// An engine for `sets` under `settings`, with the built-in taggers and detectors and
    /// no diagram checker.
    ///
    /// Rules of kinds the engine does not run yet (capitalization styles and metrics it does
    /// not measure, and structure checks it does not know) are skipped, and each document says
    /// so in an `info` notice.
    pub fn new(sets: Vec<RuleSet>, settings: Settings) -> Result<Self, EngineError> {
        Self::new_shared(sets.into_iter().map(Arc::new).collect(), settings)
    }

    /// Like [`Engine::new`], over rule sets that other engines share.
    pub fn new_shared(
        sets: Vec<Arc<RuleSet>>,
        mut settings: Settings,
    ) -> Result<Self, EngineError> {
        let genres =
            slopvac_context::builtin_genres().map_err(|e| EngineError::Context(e.to_string()))?;
        // Per-document genres apply their levels to each document's findings. Otherwise the
        // run's genre sets the genre levels now. Levels the caller already filled stay.
        let (genres, run_declared) = if settings.genre_assignments.is_some() {
            (Some(genres), None)
        } else {
            settings
                .apply_genre_levels(&genres)
                .map_err(|e| EngineError::Internal(e.to_string()))?;
            let declared = declared_tagger(&genres, &settings.genre)?;
            (None, declared)
        };
        let tagger =
            slopvac_context::builtin_registry().map_err(|e| EngineError::Context(e.to_string()))?;
        let mut engine = Self {
            sets,
            blocklist: Blocklist::default(),
            settings,
            detectors: Detectors::builtin(),
            tagger,
            genres,
            run_declared,
            checkers: Vec::new(),
            active: Vec::new(),
            vocabulary_rules: Vec::new(),
            vocabulary: Vocabulary::default(),
            casing_rules: Vec::new(),
            terms: TermSet::default(),
            metrics: Vec::new(),
            structure: Vec::new(),
            diagram_rules: HashMap::new(),
            signal_rules: Vec::new(),
            catalog: HashMap::new(),
            running: HashSet::new(),
            not_run: Vec::new(),
            categories: std::collections::BTreeMap::new(),
            rst_options: RstOptions::from_env(),
            rst: RstAdapter::new(RstOptions::from_env()),
        };
        engine.resolve();
        if !engine.casing_rules.is_empty() {
            engine.terms = TermSet::builtin();
        }
        engine.add_signal_checker();
        engine.plan_vocabulary(&Blocklist::default())?;
        Ok(engine)
    }

    /// Set the word blocklist that the vocabulary rules enforce. Without one, or with an
    /// empty one, they have nothing to check and each document says so in an `info` notice.
    pub fn with_blocklist(mut self, blocklist: &Blocklist) -> Result<Self, EngineError> {
        self.plan_vocabulary(blocklist)?;
        self.blocklist = blocklist.clone();
        Ok(self)
    }

    /// Set the terms that the term-casing rules enforce, replacing the built-in list. Build
    /// the set from the project's terms files, the built-in list or both. Words in
    /// `Settings::allowed_words` are never flagged.
    #[must_use]
    pub fn with_terms(mut self, terms: TermSet) -> Self {
        self.terms = terms;
        self
    }

    /// Set the terms from project terms files, then the built-in list. A spelling in an
    /// earlier file wins over a later file and over the built-in list. The paths are the
    /// resolved `terms.files` of the configuration and the `terms` of the active styles.
    ///
    /// # Errors
    /// A file cannot be read or is not a valid terms file.
    pub fn with_term_files<P: AsRef<std::path::Path>>(
        self,
        files: &[P],
    ) -> Result<Self, EngineError> {
        let mut entries = Vec::new();
        for path in files {
            entries.extend(
                slopvac_terms::TermsFile::load(path.as_ref())
                    .map_err(|e| EngineError::Terms(e.to_string()))?
                    .terms,
            );
        }
        Ok(self.with_term_entries(entries))
    }

    /// Set the terms from entries the caller has already read and validated, then the
    /// built-in list. An entry that comes earlier wins over a later one and over the built-in
    /// list. No file is read, so a caller that validated its files reads each only once.
    #[must_use]
    pub fn with_term_entries(mut self, mut entries: Vec<slopvac_terms::TermEntry>) -> Self {
        entries.extend(slopvac_terms::TermsFile::builtin().terms);
        self.terms = TermSet::new(entries);
        self
    }

    /// Whether `id` is a term-casing rule.
    pub(crate) fn is_term_casing(&self, id: &RuleId) -> bool {
        self.casing_rules
            .iter()
            .any(|a| self.sets[a.set].categories()[a.category].rules()[a.rule].id() == id)
    }

    /// Replace the exception detectors.
    #[must_use]
    pub fn with_detectors(mut self, detectors: Detectors) -> Self {
        self.detectors = detectors;
        self
    }

    /// Replace the context taggers.
    #[must_use]
    pub fn with_taggers(mut self, tagger: TagRegistry) -> Self {
        self.tagger = tagger;
        self
    }

    /// Replace how RST files are read: the interpreter, the project roots it must stay
    /// out of, and the limits. The default reads `SLOPVAC_RST_CONVERTER`.
    #[must_use]
    pub fn with_rst(mut self, options: RstOptions) -> Self {
        self.rst = RstAdapter::new(options.clone());
        self.rst_options = options;
        self
    }

    /// The adapter that reads RST files.
    pub(crate) const fn rst_adapter(&self) -> &RstAdapter {
        &self.rst
    }

    /// Tell the engine where the project is: the repository and the targets of the run.
    /// An RST interpreter is never taken from inside these directories. Until they are
    /// given, no interpreter is found on `PATH` and RST files are an incomplete check.
    #[must_use]
    pub fn with_project_roots(mut self, roots: Vec<std::path::PathBuf>) -> Self {
        self.rst_options.project_roots = roots;
        self.rst = RstAdapter::new(self.rst_options.clone());
        self
    }

    /// Add a checker for diagram rules.
    #[must_use]
    pub fn with_diagram_checker(mut self, checker: Box<dyn DiagramChecker>) -> Self {
        let mut ids = Vec::new();
        for DiagramRule { id, severity } in checker.rules() {
            ids.push(id.clone());
            let category = category_of(&id);
            let key = id.as_str().to_owned();
            self.catalog.insert(key.clone(), Catalog::Diagram);
            if let Level::On(severity) = level_of(&self.settings, &id, &category, severity) {
                self.running.insert(key);
                self.diagram_rules
                    .insert(id, ActiveDiagram { severity, at: None });
            }
        }
        self.checkers.push((checker, ids));
        self
    }

    /// One checker for the signal rules that run.
    fn add_signal_checker(&mut self) {
        if !self.signal_rules.is_empty() {
            let rules = std::mem::take(&mut self.signal_rules);
            let ids = rules.iter().map(|(_, rule)| rule.id.clone()).collect();
            self.checkers
                .push((Box::new(SignalChecker::from_rules(rules)), ids));
        }
    }

    /// Decide which rules run: level, `applies_to`, and whether the engine runs the kind.
    #[allow(clippy::too_many_lines)]
    fn resolve(&mut self) {
        // A rule id defined by several sets belongs to the last one: a set added later, such as
        // the generated locale rule, replaces the same id in an earlier set.
        let mut owner: HashMap<&RuleId, usize> = HashMap::new();
        for (s, set) in self.sets.iter().enumerate() {
            for rule in set.rules() {
                owner.insert(rule.id(), s);
            }
        }
        for (s, set) in self.sets.iter().enumerate() {
            for (c, category) in set.categories().iter().enumerate() {
                let meta = self.settings.categories.get(category.id());
                let info = CategoryInfo {
                    weight: match meta.and_then(|d| d.level) {
                        Some(Level::Off) => 0.0,
                        _ => meta
                            .and_then(|d| d.weight)
                            .unwrap_or(category.weight().get()),
                    },
                    budget: if meta.is_some_and(|d| d.budget_cleared) {
                        None
                    } else {
                        meta.and_then(|d| d.max_per_100_words).or_else(|| {
                            category
                                .max_per_100_words()
                                .and_then(|m| {
                                    m.iter()
                                        .find(|(p, _)| p.as_str() == self.settings.profile.as_str())
                                })
                                .map(|(_, d)| d.get())
                        })
                    },
                };
                self.categories.insert(category.id().clone(), info);
                for (r, loaded) in category.rules().iter().enumerate() {
                    if owner.get(loaded.id()) != Some(&s) {
                        continue;
                    }
                    let rule = loaded.rule();
                    let Level::On(severity) = level_of(
                        &self.settings,
                        loaded.id(),
                        loaded.category(),
                        rule.severity,
                    ) else {
                        continue;
                    };
                    if let Some(applies) = &rule.applies_to {
                        let mode = self.settings.mode.apply_mode();
                        if applies.modes.as_ref().is_some_and(|m| !m.contains(&mode))
                            || (self.genres.is_none()
                                && applies
                                    .genres
                                    .as_ref()
                                    .is_some_and(|g| !g.contains(&self.settings.genre.id)))
                        {
                            continue;
                        }
                    }
                    self.running.insert(loaded.id().as_str().to_owned());
                    match loaded.kind() {
                        kind if runs_lexically(kind, &rule.match_) => {
                            self.active.push(Active::new(s, c, r, severity));
                        }
                        MatchKind::Judgement
                        | MatchKind::Tokens
                        | MatchKind::Pattern
                        | MatchKind::Substitution => {}
                        MatchKind::Metric => {
                            let supported = matches!(
                                &rule.match_,
                                Match::Metric(m) if metrics::supported(m.metric.as_str())
                            );
                            if supported {
                                self.metrics.push(Active::new(s, c, r, severity));
                            } else {
                                self.not_run.push(NotRun::of("metric", loaded.id(), rule));
                            }
                        }
                        MatchKind::Structure => {
                            if let Some(signal) = signal_of_rule(loaded) {
                                let id = loaded.id().clone();
                                let rule = DiagramRule {
                                    id: id.clone(),
                                    severity,
                                };
                                let at = Some((s, c, r));
                                self.diagram_rules
                                    .insert(id, ActiveDiagram { severity, at });
                                self.signal_rules.push((signal, rule));
                            } else {
                                let check = match &rule.match_ {
                                    Match::Structure(m) => Check::named(m.check.as_str()),
                                    _ => None,
                                };
                                if let Some(check) = check {
                                    self.structure.push((Active::new(s, c, r, severity), check));
                                } else {
                                    self.not_run
                                        .push(NotRun::of("structure", loaded.id(), rule));
                                }
                            }
                        }
                        MatchKind::Vocabulary => {
                            let casing =
                                matches!(&rule.match_, Match::Vocabulary(v) if terms::is_casing(v));
                            let list = if casing {
                                &mut self.casing_rules
                            } else {
                                &mut self.vocabulary_rules
                            };
                            list.push(Active::new(s, c, r, severity));
                        }
                        MatchKind::Capitalization => {
                            self.not_run
                                .push(NotRun::of(CAPITALIZATION, loaded.id(), rule));
                        }
                    }
                }
            }
        }
        for (s, set) in self.sets.iter().enumerate() {
            for rule in set.rules() {
                self.catalog
                    .insert(rule.id().as_str().to_owned(), Catalog::Loaded(s));
            }
        }
    }

    /// Why the engine does not execute `rule`, or `None` when it does.
    ///
    /// A rule that is switched off, limited by `applies_to` to another genre or mode, of a
    /// kind the engine does not implement, or of a capitalization style or metric it does
    /// not run is not executed. A vocabulary rule runs only with a blocklist it can use.
    #[must_use]
    pub fn unexecuted(&self, rule: &LoadedRule) -> Option<&'static str> {
        let id = rule.id();
        let at = |a: &&crate::lint::Active| {
            self.sets[a.set].categories()[a.category].rules()[a.rule].id() == id
        };
        if !self.running.contains(id.as_str()) {
            return Some("the rule is switched off or does not apply under the engine settings");
        }
        let owns =
            |plan: &vocabulary::Plan| plan.owner.is_some_and(|i| at(&&self.vocabulary_rules[i]));
        let executes = self.active.iter().any(|a| at(&a))
            || self.structure.iter().any(|(a, _)| at(&a))
            || self.metrics.iter().any(|a| at(&a))
            || self.casing_rules.iter().any(|a| at(&a))
            || self.vocabulary.plans().any(owns);
        if executes {
            None
        } else if rule.kind() == MatchKind::Vocabulary {
            Some("a vocabulary rule needs a usable word blocklist")
        } else {
            Some("the engine does not run this kind, style or metric of rule")
        }
    }

    /// The loaded rule for a qualified id.
    fn loaded(&self, id: &str) -> Option<&LoadedRule> {
        let Catalog::Loaded(set) = self.catalog.get(id)? else {
            return None;
        };
        let rule_id = RuleId::new(id).ok()?;
        self.sets[*set].get(&rule_id)
    }

    /// Lint many inputs in parallel. Results keep the order of `inputs`.
    #[must_use]
    pub fn lint_all(&self, inputs: &[Input<'_>]) -> Vec<Result<Document, EngineError>> {
        inputs.par_iter().map(|input| self.lint(input)).collect()
    }

    /// Like [`Engine::lint_all`], with the run-level notices of each input as
    /// [`Engine::lint_with_notices`] returns them.
    #[must_use]
    pub fn lint_all_with_notices(&self, inputs: &[Input<'_>]) -> Vec<LintOutcome> {
        inputs
            .par_iter()
            .map(|input| self.lint_with_notices(input))
            .collect()
    }

    /// Lint one input.
    pub fn lint(&self, input: &Input<'_>) -> Result<Document, EngineError> {
        self.lint_with_notices(input).map(|(document, _)| document)
    }

    /// Lint one input and also return its run-level notices.
    ///
    /// The notices are about the run, not about a check that failed to run. An extractor
    /// emits one at level `info` for unsupported content inside a supported input: the
    /// content is not read, and the run is still complete. A caller adds them to the root
    /// `notices` of the report, where they never make the run incomplete. Input that is
    /// malformed or over a limit is reported in [`Document::unchecked`] instead, and makes
    /// the run incomplete.
    pub fn lint_with_notices(
        &self,
        input: &Input<'_>,
    ) -> Result<(Document, Vec<Notice>), EngineError> {
        // Front matter is metadata, not prose: the parser reads only what follows it.
        let front = match input.kind {
            Kind::Diagram(_) | Kind::Rst | Kind::Comments(_) => None,
            _ => detect(input.source),
        };
        let body_start = front.as_ref().map_or(0, |b| b.body_start);
        let front_span = front
            .as_ref()
            .map(|b| Span::new(0, b.body_start).expect("0 <= body start"))
            .filter(|s| !s.is_empty());
        let body = Span::new(body_start, input.source.len()).expect("body starts inside the file");
        let front_matter = front.and_then(|b| FrontMatter::parse_block(input.source, b).ok());
        let mut extra = Vec::new();
        // The text rules read: the source, or the source with all but comment text blanked,
        // and for the directive scan the same with directive text kept.
        let mut masked = None;
        let parsed = match input.kind {
            Kind::Markdown => parse_markdown(input.source, body)?,
            Kind::Mdx => parse_mdx(input.source, body)?,
            Kind::Rst => self.parse_rst(input, &mut extra)?,
            Kind::Diagram(_) => Parsed::default(),
            Kind::Comments(language) => {
                let text = comments::read(input.source, language)?;
                masked = Some((text.masked, text.lexical));
                text.parsed
            }
        };
        let text = masked
            .as_ref()
            .map_or(input.source, |(_, lexical)| lexical.as_str());
        let index = SourceIndex::new(input.source, input.bom);
        let parsed = with_html_prose(input.source, &index, parsed)?;
        let prepared = Prepared::new(text, &parsed)?;
        let (genre, tags) = self.genre_and_tags(input, &parsed, front_matter.as_ref())?;
        let lines = Lines::new(input.source);
        let lookup = |id: &str| self.directive_target(id);
        let directives = match input.kind {
            Kind::Diagram(_) => Directives::default(),
            Kind::Comments(_) => comments::directives(
                input.source,
                masked.as_ref().map_or("", |(masked, _)| masked.as_str()),
                lookup,
            ),
            _ => scan(&parsed, &lines, front_span, lookup),
        };
        let subject = Subject::new(&prepared, &parsed, &lines, front_span);
        let run = Run {
            engine: self,
            input,
            parsed: &parsed,
            prepared: &prepared,
            tags: &tags,
            lines: &lines,
            directives: &directives,
            front_matter: front_span,
            subject: &subject,
            index,
            genre: &genre,
        };
        let mut findings = run.lexical()?;
        // Code-comment mode runs the lexical rules only; `comment_notice` lists the rest.
        let mut diagram_notices = Vec::new();
        let mut seen = tags.kinds_seen();
        if !matches!(input.kind, Kind::Comments(_)) {
            findings.extend(run.vocabulary()?);
            findings.extend(run.term_casing()?);
            findings.extend(run.metrics()?);
            findings.extend(run.structure()?);
            let diagrams = run.diagrams()?;
            findings.extend(diagrams.findings);
            extra.extend(diagrams.unchecked);
            diagram_notices = diagrams.notices;
            seen.extend(run.holds_diagram().then_some(slopvac_diagrams::CONTEXT));
        }
        findings.extend(run.invalid_directives()?);
        // Lookups that passed their budget answered nothing, so nothing found above stands.
        if tags.lookup_budget_exceeded() {
            return Err(EngineError::TagLookupBudget {
                limit: tagging::lookup_budget(input.source.len()),
            });
        }
        findings.sort_by(|a, b| (a.start, a.rule_id.as_str()).cmp(&(b.start, b.rule_id.as_str())));
        self.apply_genre(&genre, &mut findings);
        // Notices about rules that cannot run come first, then the ones the parse raised.
        // Code-comment mode lists every rule it cannot read in one notice of its own.
        let mut notices = if matches!(input.kind, Kind::Comments(_)) {
            self.comment_notice()?.into_iter().collect()
        } else {
            self.not_run_notices(&genre.id)?
        };
        notices.extend(extra);
        let document = self.document(input, &prepared, seen, genre, findings, notices);
        Ok((document, diagram_notices))
    }

    /// The genre of one document and its context tags. The genre comes first: the contexts
    /// it declares are tags of the document.
    fn genre_and_tags(
        &self,
        input: &Input<'_>,
        parsed: &Parsed,
        front_matter: Option<&FrontMatter<'_>>,
    ) -> Result<(GenreResult, TagIndex), EngineError> {
        let genre = self.genre_of(input, parsed, front_matter)?;
        let declared = match (&self.genres, &self.run_declared) {
            (Some(registry), _) => declared_tagger(registry, &genre)?,
            (None, run) => run.clone(),
        };
        // A standalone diagram has no structure to tag, but its genre's contexts still hold.
        let none = TagRegistry::new();
        let registry = if matches!(input.kind, Kind::Diagram(_)) {
            &none
        } else {
            &self.tagger
        };
        let tags = tagging::tag(
            registry,
            input.path,
            input.source,
            parsed,
            front_matter,
            declared.as_ref(),
        )
        .map_err(|e| match e {
            tagging::TagError::Budget { limit } => EngineError::TagBuildBudget { limit },
            other => EngineError::Context(other.to_string()),
        })?;
        Ok((genre, tags))
    }

    /// The notices about active rules the engine does not run and that apply to a document of
    /// `genre`.
    fn not_run_notices(&self, genre: &GenreId) -> Result<Vec<Notice>, EngineError> {
        let mut ids: std::collections::BTreeMap<&str, Vec<&RuleId>> =
            std::collections::BTreeMap::new();
        for n in &self.not_run {
            if n.genres.as_ref().is_none_or(|g| g.contains(genre)) {
                ids.entry(n.kind).or_default().push(&n.id);
            }
        }
        ids.into_iter()
            .map(|(kind, rules)| not_run_notice(kind, &rules))
            .collect()
    }

    /// The genre of one document: chosen from the document when the settings ask for it,
    /// else the run's genre.
    fn genre_of(
        &self,
        input: &Input<'_>,
        parsed: &Parsed,
        front_matter: Option<&FrontMatter<'_>>,
    ) -> Result<GenreResult, EngineError> {
        let (Some(registry), Some(assignments), false) = (
            &self.genres,
            &self.settings.genre_assignments,
            matches!(input.kind, Kind::Diagram(_)),
        ) else {
            return Ok(self.settings.genre.clone());
        };
        let opts = ResolveOptions {
            assignments,
            relative_path: input.relative_path,
            declared: DeclaredGenre::Given(input.declared_genre),
        };
        let found = tagging::genre(
            registry,
            &opts,
            input.path,
            input.source,
            parsed,
            front_matter,
        )
        .map_err(|e| EngineError::Context(e.to_string()))?;
        Ok(GenreResult {
            id: GenreId::new(found.id).map_err(|e| EngineError::Internal(e.to_string()))?,
            source: match found.source {
                slopvac_context::GenreSource::Explicit => GenreSource::Explicit,
                slopvac_context::GenreSource::Detected => GenreSource::Detected,
                slopvac_context::GenreSource::Default => GenreSource::Default,
            },
            reasons: found
                .reasons
                .into_iter()
                .map(|r| {
                    Ok(GenreReason {
                        signal: KebabName::new(r.signal)
                            .map_err(|e| EngineError::Internal(e.to_string()))?,
                        detail: r.detail,
                    })
                })
                .collect::<Result<_, EngineError>>()?,
        })
    }

    /// Give the findings of one document the levels of its genre. A rule or category level
    /// from the configuration stays above a genre level, as in `level_of`. A rule that
    /// `applies_to` other genres does not report.
    fn apply_genre(&self, genre: &GenreResult, findings: &mut Vec<Finding>) {
        let Some(registry) = &self.genres else {
            return;
        };
        // An unreadable genre key leaves the document at the shipped levels.
        let levels = crate::settings::genre_levels(registry, genre.id.as_str()).unwrap_or_default();
        findings.retain_mut(|f| {
            let loaded = self.loaded(f.rule_id.as_str());
            if loaded
                .and_then(|l| l.rule().applies_to.as_ref()?.genres.as_ref())
                .is_some_and(|g| !g.contains(&genre.id))
            {
                return false;
            }
            let category = loaded.map_or_else(|| category_of(&f.rule_id), |l| l.category().clone());
            let explicit = self.settings.rule_levels.contains_key(&f.rule_id)
                || self
                    .settings
                    .categories
                    .get(&category)
                    .is_some_and(|d| d.level.is_some());
            if explicit {
                return true;
            }
            // The profile shifts a genre level as it shifts the shipped one.
            match levels
                .get(&f.rule_id)
                .map(|l| l.shifted(self.settings.severity_shift))
            {
                Some(Level::Off) => false,
                Some(Level::On(severity)) => {
                    f.severity = severity;
                    true
                }
                None => true,
            }
        });
    }

    /// What an inline directive naming `id` points at.
    fn directive_target(&self, id: &str) -> Target<'_> {
        match self.catalog.get(id) {
            None => Target::Unknown,
            Some(_) if !self.running.contains(id) => Target::Inactive,
            Some(Catalog::Loaded(_)) => Target::Active(
                self.loaded(id)
                    .map(|r| {
                        r.rule()
                            .exceptions()
                            .iter()
                            .map(|e| e.name.as_str())
                            .collect()
                    })
                    .unwrap_or_default(),
            ),
            Some(Catalog::Diagram) => Target::Active(Vec::new()),
        }
    }

    /// The notice for the active rules that code-comment mode does not run, or `None` when it
    /// runs them all. As in 2.x, only the lexical rules read comments. Every other active
    /// checker is listed in `data.rules`, diagram rules and the rules of a custom checker
    /// included, so none passes in silence. A judgement rule never produces a finding, so it
    /// is not listed.
    ///
    /// The notice is `info`, so the run stays complete. The contract asks for a `warning`
    /// (an incomplete run) when the user enabled such a rule by name, but the engine sees one
    /// level per rule and not the configuration layer it came from, so it cannot tell that
    /// apart from a rule the profile or a style turns on.
    fn comment_notice(&self) -> Result<Option<Notice>, EngineError> {
        let runs: HashSet<&RuleId> = self
            .active
            .iter()
            .map(|a| self.sets[a.set].categories()[a.category].rules()[a.rule].id())
            .collect();
        let mut skipped: Vec<&str> = Vec::new();
        for set in &self.sets {
            for rule in set.rules() {
                let id = rule.id();
                if self.running.contains(id.as_str())
                    && !runs.contains(id)
                    && rule.kind() != MatchKind::Judgement
                    && !skipped.contains(&id.as_str())
                {
                    skipped.push(id.as_str());
                }
            }
        }
        // The rules of a custom checker have no loaded rule.
        let mut custom: Vec<&str> = self
            .diagram_rules
            .keys()
            .map(RuleId::as_str)
            .filter(|id| !skipped.contains(id))
            .collect();
        custom.sort_unstable();
        skipped.extend(custom);
        if skipped.is_empty() {
            return Ok(None);
        }
        let rules = skipped
            .iter()
            .map(|id| serde_json::Value::String((*id).to_owned()))
            .collect();
        let data = serde_json::Map::from_iter([("rules".to_owned(), rules)]);
        Ok(Some(
            notice(
                "comment-rules-not-run",
                NoticeLevel::Info,
                format!(
                    "{} active rule(s) do not run on code comments, which only the tokens, \
                     pattern, substitution and capitalization rules read: {}",
                    skipped.len(),
                    skipped.join(", ")
                ),
            )?
            .with_data(data),
        ))
    }

    /// Read an RST file. A file that cannot be read is an empty document with a warning
    /// notice, so the run is incomplete and the file is never skipped silently.
    fn parse_rst(&self, input: &Input<'_>, extra: &mut Vec<Notice>) -> Result<Parsed, EngineError> {
        let make = |code: &str, level, message: String| -> Result<Notice, EngineError> {
            let mut notice = notice(code, level, message)?;
            notice.path = Some(input.path.to_owned());
            Ok(notice)
        };
        match self.rst.parse(input.source) {
            Ok(parsed) => {
                for n in parsed.notices {
                    let level = if n.warning {
                        NoticeLevel::Warning
                    } else {
                        NoticeLevel::Info
                    };
                    extra.push(make(n.code, level, n.message)?);
                }
                Ok(parsed.document)
            }
            Err(error) => {
                let code = if error.is_missing() {
                    "rst-converter-missing"
                } else {
                    "rst-unchecked"
                };
                extra.push(make(
                    code,
                    NoticeLevel::Warning,
                    RstError::message(&error, &[std::path::Path::new(input.path)]),
                )?);
                Ok(Parsed::default())
            }
        }
    }

    fn document(
        &self,
        input: &Input<'_>,
        prepared: &Prepared<'_>,
        mut seen: Vec<&str>,
        genre: GenreResult,
        findings: Vec<Finding>,
        extra: Vec<Notice>,
    ) -> Document {
        let words = prepared.words();
        if matches!(input.kind, Kind::Comments(_)) && !prepared.blocks().is_empty() {
            seen.push(COMMENT_CONTEXT);
        }
        seen.sort_unstable();
        seen.dedup();
        let mut unchecked = extra;
        // Code-comment mode runs no vocabulary rule, so it has no vocabulary notice.
        if !matches!(input.kind, Kind::Comments(_)) {
            unchecked.extend(self.vocabulary.plan(&genre.id).notices().iter().cloned());
        }
        let scoring = score_document(
            &findings,
            words,
            &self.categories,
            &self.settings.thresholds,
            &unchecked,
        );
        Document {
            path: NonEmptyString::new(input.path).unwrap_or_else(|_| {
                NonEmptyString::new("<stdin>").expect("a literal is not empty")
            }),
            profile: self.settings.profile.clone(),
            genre,
            contexts_seen: contexts(seen),
            config_sources: self.settings.config_sources.clone(),
            words,
            sentences: prepared.sentence_count(),
            paragraphs: prepared.paragraph_count(),
            findings,
            categories: scoring.categories,
            total_findings: scoring.total_findings,
            errors: scoring.errors,
            warnings: scoring.warnings,
            suggestions: scoring.suggestions,
            per_100_words: scoring.per_100_words,
            score: scoring.score,
            gate: scoring.gate,
            unchecked,
            ai_register: scoring.ai_register,
            prose: scoring.prose,
        }
    }
}

/// The context kinds that hold at a match: those of the tags that cover every source range it
/// is made of, or the tags around its span when it has one range.
fn kinds_of<'t>(tags: &'t TagIndex, span: Span, covering: &[Range<usize>]) -> Vec<&'t str> {
    if covering.len() > 1 {
        tags.kinds_covering(covering)
    } else {
        tags.kinds_at(&(span.start()..span.end()))
    }
}

/// The context tag of comment text in a source file (`docs/contract/lint-report.md`).
const COMMENT_CONTEXT: &str = "code-comment";

/// The signal a loaded rule runs, if it runs one.
fn signal_of_rule(loaded: &LoadedRule) -> Option<Signal> {
    match &loaded.rule().match_ {
        Match::Structure(m) => diagrams::signal_of(m),
        _ => None,
    }
}

fn category_of(id: &RuleId) -> CategoryId {
    let local = id.local();
    CategoryId::new(local.split_once('.').map_or(local, |(c, _)| c))
        .unwrap_or_else(|_| CategoryId::new("meta").expect("meta is a category id"))
}

/// The tagger for the contexts `genre` declares, if it declares any.
fn declared_tagger(
    registry: &GenreRegistry,
    genre: &GenreResult,
) -> Result<Option<DeclaredContextTagger>, EngineError> {
    DeclaredContextTagger::for_genre_id(registry, genre.id.as_str())
        .map_err(|e| EngineError::Context(e.to_string()))
}

fn contexts(kinds: Vec<&str>) -> Contexts {
    Contexts::new(
        kinds
            .into_iter()
            .filter_map(|k| ContextTag::new(k).ok())
            .collect(),
    )
    .unwrap_or_default()
}

/// The state of one document run.
struct Run<'a> {
    engine: &'a Engine,
    input: &'a Input<'a>,
    parsed: &'a Parsed,
    prepared: &'a Prepared<'a>,
    tags: &'a TagIndex,
    lines: &'a Lines<'a>,
    directives: &'a Directives,
    front_matter: Option<Span>,
    subject: &'a Subject<'a>,
    index: SourceIndex<'a>,
    genre: &'a GenreResult,
}

/// A paragraph next to a fenced diagram, and where a checker sees it.
struct NearbyProse<'a> {
    /// Where the paragraph's text starts in the coordinates the checker gets.
    base: usize,
    block: &'a slopvac_parse::Block,
    projection: &'a slopvac_parse::Projection,
    /// What the prose checks read from the paragraph, shared by every diagram beside it.
    analysis: &'a slopvac_diagrams::ProseAnalysis<'a>,
}

/// A parsed paragraph that has prose, with its analysis. Built once per paragraph, so every
/// [`NearbyProse`] for the paragraph shares the same text and analysis.
struct Paragraph<'a> {
    block: &'a slopvac_parse::Block,
    projection: &'a slopvac_parse::Projection,
    analysis: slopvac_diagrams::ProseAnalysis<'a>,
}

impl NearbyProse<'_> {
    fn text(&self) -> &str {
        self.projection.text()
    }
}

/// The paragraphs next to a diagram and the analysis of each, one for one in the same order.
fn prose_inputs<'a>(
    nearby: &'a [NearbyProse<'a>],
) -> (
    Vec<slopvac_diagrams::ProseBlock<'a>>,
    Vec<&'a slopvac_diagrams::ProseAnalysis<'a>>,
) {
    nearby
        .iter()
        .map(|n| {
            (
                slopvac_diagrams::ProseBlock {
                    span: n.base..n.base + n.text().len(),
                    text: n.text(),
                },
                n.analysis,
            )
        })
        .unzip()
}

/// A finding before it gets its position.
struct Candidate<'r> {
    rule_id: &'r RuleId,
    pack: &'r PackId,
    category: CategoryId,
    severity: Severity,
    message: String,
    span: Span,
    matched_text: String,
    ai_signal: AiSignal,
    fix: Option<Fix>,
    extra_context: Option<&'static str>,
    /// The source ranges the match is made of, when it reads out of source order. Empty
    /// means the span.
    covering: Vec<Range<usize>>,
}

/// Block visits made while finding the prose near each diagram in this process.
#[cfg(feature = "test-counters")]
static NEARBY_BLOCK_VISITS: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

/// The number of block visits made so far in this process to find nearby prose. A test that
/// lints a run of diagrams and reads the difference shows whether the lookup does work
/// proportional to the blocks or to the blocks times the diagrams.
#[cfg(feature = "test-counters")]
#[doc(hidden)]
#[must_use]
pub fn nearby_block_visits() -> usize {
    NEARBY_BLOCK_VISITS.load(std::sync::atomic::Ordering::Relaxed)
}

#[cfg(feature = "test-counters")]
fn count_block_visit() {
    NEARBY_BLOCK_VISITS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
}

#[cfg(not(feature = "test-counters"))]
fn count_block_visit() {}

/// Bytes of matched text built for diagram findings on a paragraph in this process.
#[cfg(feature = "test-counters")]
static PROSE_FINDING_BYTES: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);

/// The number of matched-text bytes built so far in this process for diagram findings on a
/// paragraph. A test that lints many diagrams around one paragraph and reads the difference
/// shows whether the paragraph is copied once or once per diagram.
#[cfg(feature = "test-counters")]
#[doc(hidden)]
#[must_use]
pub fn prose_finding_bytes() -> usize {
    PROSE_FINDING_BYTES.load(std::sync::atomic::Ordering::Relaxed)
}

#[cfg(feature = "test-counters")]
fn count_prose_finding_bytes(bytes: usize) {
    PROSE_FINDING_BYTES.fetch_add(bytes, std::sync::atomic::Ordering::Relaxed);
}

#[cfg(not(feature = "test-counters"))]
fn count_prose_finding_bytes(_bytes: usize) {}

impl Run<'_> {
    fn finding(&self, c: Candidate<'_>) -> Result<Finding, EngineError> {
        let start = self.index.line_col(c.span.start())?;
        let end = self.index.line_col(c.span.end())?;
        let mut kinds = kinds_of(self.tags, c.span, &c.covering);
        if let Some(extra) = c.extra_context.or_else(|| self.ambient())
            && !kinds.contains(&extra)
        {
            kinds.push(extra);
        }
        Ok(Finding {
            rule_id: c.rule_id.clone(),
            pack: c.pack.clone(),
            category: c.category,
            severity: c.severity,
            message: NonEmptyString::new(c.message)
                .map_err(|e| EngineError::Internal(e.to_string()))?,
            start,
            extent: Some(Extent { span: c.span, end }),
            contexts: contexts(kinds),
            ai_signal: c.ai_signal,
            matched_text: c.matched_text,
            fix: c.fix,
            provenance: Some(RuleProvenance {
                pack: c.pack.clone(),
                version: None,
                source: None,
            }),
            origin: None,
        })
    }

    /// Whether a directive covers a finding of `id` that starts at `span`.
    fn suppressed(&self, id: &str, exceptions: &[&str], span: Span) -> bool {
        self.directives
            .suppressed(id, exceptions, self.lines.line_of(span.start()))
    }

    /// The text context that every match in this input sits in, which no tagger gives: comment
    /// text in a source file.
    fn ambient(&self) -> Option<&'static str> {
        matches!(self.input.kind, Kind::Comments(_)).then_some(COMMENT_CONTEXT)
    }

    /// Whether the document's genre is one the rule applies to. A rule limited to other genres
    /// does not run, so it cannot fail the document.
    fn applies(&self, rule: &slopvac_rules::Rule) -> bool {
        rule.applies_to
            .as_ref()
            .and_then(|a| a.genres.as_ref())
            .is_none_or(|g| g.contains(&self.genre.id))
    }

    /// Whether the diagram rule `id` runs and applies to the document's genre. A rule of a
    /// custom checker has no loaded rule, so no genre limits it.
    fn diagram_rule_applies(&self, id: &RuleId) -> bool {
        self.engine.diagram_rules.get(id).is_some_and(|active| {
            active.at.is_none_or(|(s, c, r)| {
                self.applies(self.engine.sets[s].categories()[c].rules()[r].rule())
            })
        })
    }

    fn lexical(&self) -> Result<Vec<Finding>, EngineError> {
        let engine = self.engine;
        if matches!(self.input.kind, Kind::Diagram(_)) {
            // A diagram file is not prose. Only diagram rules read it.
            return Ok(Vec::new());
        }
        let comments = matches!(self.input.kind, Kind::Comments(_));
        let inline_code = skip::build(self.parsed, &[], None, true);
        let mut out = Vec::new();
        for active in &engine.active {
            let set = &engine.sets[active.set];
            let loaded = &set.categories()[active.category].rules()[active.rule];
            let rule = loaded.rule();
            if !self.applies(rule) {
                continue;
            }
            // In code-comment mode a comment is the unit whatever the scope of the rule: 2.x
            // replaced it with the comment scope of the source language.
            let scope = if comments { Scope::Prose } else { rule.scope };
            let exclusions;
            let skip: &SkipRanges = match (&rule.exclude_blocks, scope) {
                (Some(kinds), scope) => {
                    exclusions =
                        skip::build(self.parsed, kinds, self.front_matter, scope != Scope::Raw);
                    &exclusions
                }
                (None, Scope::Raw) => {
                    exclusions = SkipRanges::default();
                    &exclusions
                }
                (None, _) => &inline_code,
            };
            let exceptions: Vec<&str> = rule.exceptions().iter().map(|e| e.name.as_str()).collect();
            let detectors: Vec<&str> = rule
                .exceptions()
                .iter()
                .filter_map(|e| e.detector.as_ref().map(slopvac_rules::Slug::as_str))
                .collect();
            let sentence_case = match &rule.match_ {
                Match::Capitalization(m) => {
                    Some(SentenceCase::new(m, &engine.settings.allowed_words))
                }
                _ => None,
            };
            for unit in self.prepared.units(scope)? {
                matcher_work::entered(loaded.kind());
                let ranges = match &sentence_case {
                    Some(check) => check.find(unit.text)?.into_iter().collect(),
                    None => loaded.find_all(unit.text)?,
                };
                for range in ranges {
                    if let Some(c) =
                        self.candidate(active, set, loaded, &unit, &range, skip, &detectors)?
                    {
                        if self.suppressed(loaded.id().as_str(), &exceptions, c.span) {
                            continue;
                        }
                        out.push(self.finding(c)?);
                    }
                }
            }
        }
        Ok(out)
    }

    /// Whether the rule's context gate or an exception detector drops a match: `range` in
    /// `text`, at `span` in the source.
    #[allow(clippy::too_many_arguments)]
    fn guarded(
        &self,
        rule: &slopvac_rules::Rule,
        detectors: &[&str],
        text: &str,
        range: &Range<usize>,
        origin: Option<TextOrigin<'_>>,
        span: Span,
        covering: &[Range<usize>],
    ) -> bool {
        self.guarded_with(
            self.ambient(),
            rule,
            detectors,
            text,
            range,
            origin,
            span,
            covering,
        )
    }

    /// [`Self::guarded`] for a match that sits in `extra` context, a tag the context index
    /// does not hold, such as `diagram-label`.
    #[allow(clippy::too_many_arguments)]
    fn guarded_with(
        &self,
        extra: Option<&'static str>,
        rule: &slopvac_rules::Rule,
        detectors: &[&str],
        text: &str,
        range: &Range<usize>,
        origin: Option<TextOrigin<'_>>,
        span: Span,
        covering: &[Range<usize>],
    ) -> bool {
        self.guarded_in(
            self.tags,
            self.parsed,
            extra,
            rule,
            detectors,
            text,
            range,
            origin,
            span,
            covering,
        )
    }

    /// [`Self::guarded`] for text of another parse of the file, with that parse's context
    /// tags and document.
    #[allow(clippy::too_many_arguments)]
    fn guarded_in(
        &self,
        tags: &TagIndex,
        document: &Parsed,
        extra: Option<&'static str>,
        rule: &slopvac_rules::Rule,
        detectors: &[&str],
        text: &str,
        range: &Range<usize>,
        origin: Option<TextOrigin<'_>>,
        span: Span,
        covering: &[Range<usize>],
    ) -> bool {
        let gate = rule.contexts.as_ref();
        let mut kinds = if gate.is_some() || !detectors.is_empty() {
            kinds_of(tags, span, covering)
        } else {
            Vec::new()
        };
        kinds.extend(extra.filter(|e| !kinds.contains(e)));
        if let Some(gate) = gate {
            let has = |tags: &Option<slopvac_rules::UniqueVec<ContextTag>>| {
                tags.as_ref()
                    .map(|t| t.iter().any(|t| kinds.contains(&t.as_str())))
            };
            if has(&gate.skip) == Some(true) || has(&gate.only) == Some(false) {
                return true;
            }
        }
        let site = MatchSite {
            text,
            range,
            span,
            origin,
            document,
            tags: &kinds,
        };
        detectors
            .iter()
            .any(|d| self.engine.detectors.detects(d, &site))
    }

    /// Findings of metric rules: one per sentence or paragraph over its threshold, or one for
    /// the document. A finding has a line and column 1 and no source range.
    fn metrics(&self) -> Result<Vec<Finding>, EngineError> {
        let engine = self.engine;
        if matches!(self.input.kind, Kind::Diagram(_)) {
            return Ok(Vec::new());
        }
        let inline_code = skip::build(self.parsed, &[], None, true);
        let mut out = Vec::new();
        for active in &engine.metrics {
            let set = &engine.sets[active.set];
            let loaded = &set.categories()[active.category].rules()[active.rule];
            let rule = loaded.rule();
            if !self.applies(rule) {
                continue;
            }
            let Match::Metric(metric) = &rule.match_ else {
                continue;
            };
            let exceptions: Vec<&str> = rule.exceptions().iter().map(|e| e.name.as_str()).collect();
            let detectors: Vec<&str> = rule
                .exceptions()
                .iter()
                .filter_map(|e| e.detector.as_ref().map(slopvac_rules::Slug::as_str))
                .collect();
            let exclusions;
            let skip: &SkipRanges = match &rule.exclude_blocks {
                Some(kinds) => {
                    exclusions = skip::build(self.parsed, kinds, self.front_matter, true);
                    &exclusions
                }
                None => &inline_code,
            };
            matcher_work::entered(MatchKind::Metric);
            for hit in self.subject.measure(metric, rule.text_type)? {
                // The guards read the measured sentence or paragraph. A document-wide
                // measurement has no unit to guard.
                if let Some(unit) = &hit.unit
                    && (skip.hides(unit.span)
                        || self.guarded(
                            rule,
                            &detectors,
                            unit.text,
                            &unit.range,
                            None,
                            unit.span,
                            &[],
                        ))
                {
                    continue;
                }
                let at = Span::empty(hit.at);
                if self.suppressed(loaded.id().as_str(), &exceptions, at) {
                    continue;
                }
                let line = self.index.line_col(hit.at)?.line();
                out.push(Finding {
                    rule_id: loaded.id().clone(),
                    pack: set.pack().clone(),
                    category: loaded.category().clone(),
                    severity: active.severity,
                    message: NonEmptyString::new(format_message(
                        rule.message.as_str(),
                        &hit.shown,
                        &hit.limit,
                    ))
                    .map_err(|e| EngineError::Internal(e.to_string()))?,
                    start: LineCol::new(line, 1)
                        .map_err(|e| EngineError::Internal(e.to_string()))?,
                    extent: None,
                    contexts: Contexts::default(),
                    ai_signal: rule.ai_signal,
                    matched_text: String::new(),
                    fix: None,
                    provenance: Some(RuleProvenance {
                        pack: set.pack().clone(),
                        version: None,
                        source: None,
                    }),
                    origin: None,
                });
            }
        }
        Ok(out)
    }

    /// Findings of structure rules that run. A heading finding covers the heading line, as
    /// the 2.x script reported it. A finding on a front matter line or on a line that starts
    /// inside an HTML comment is dropped, unless the rule is `raw`; those lines still set the
    /// heading level that the next heading is compared with.
    fn structure(&self) -> Result<Vec<Finding>, EngineError> {
        let engine = self.engine;
        if engine.structure.is_empty() || matches!(self.input.kind, Kind::Diagram(_)) {
            return Ok(Vec::new());
        }
        let source = self.input.source;
        let skips = structure::heading_skips(source);
        let (comments, _) = structure::html_comments(source);
        let mut out = Vec::new();
        for (active, check) in &engine.structure {
            let Check::HeadingHierarchy = check;
            let set = &engine.sets[active.set];
            let loaded = &set.categories()[active.category].rules()[active.rule];
            let rule = loaded.rule();
            let exceptions: Vec<&str> = rule.exceptions().iter().map(|e| e.name.as_str()).collect();
            let detectors: Vec<&str> = rule
                .exceptions()
                .iter()
                .filter_map(|e| e.detector.as_ref().map(slopvac_rules::Slug::as_str))
                .collect();
            let exclusions = rule.exclude_blocks.as_ref().map(|kinds| {
                skip::build(
                    self.parsed,
                    kinds,
                    self.front_matter,
                    rule.scope != Scope::Raw,
                )
            });
            // Front matter and comments hide a finding only from rules that are not `raw`.
            let hides_automatically = rule.scope != Scope::Raw;
            let mut next_comment = 0;
            for line in &skips.lines {
                // The lines come in order, so the comments before this one are done with.
                while comments
                    .get(next_comment)
                    .is_some_and(|c| c.end <= line.start)
                {
                    next_comment += 1;
                }
                if hides_automatically
                    && (self.front_matter.is_some_and(|f| line.start < f.end())
                        || comments
                            .get(next_comment)
                            .is_some_and(|c| c.start <= line.start))
                {
                    continue;
                }
                let span = Span::new(line.start, line.end)
                    .map_err(|e| EngineError::Internal(e.to_string()))?;
                let text = &source[line.clone()];
                if exclusions.as_ref().is_some_and(|skip| skip.hides(span))
                    || self.guarded(rule, &detectors, text, &(0..text.len()), None, span, &[])
                    || self.suppressed(loaded.id().as_str(), &exceptions, span)
                {
                    continue;
                }
                out.push(
                    self.finding(Candidate {
                        rule_id: loaded.id(),
                        pack: set.pack(),
                        category: loaded.category().clone(),
                        severity: active.severity,
                        // The 2.x report folded the whitespace left where `{match}` was empty.
                        message: format_message(rule.message.as_str(), "", "")
                            .split_whitespace()
                            .collect::<Vec<_>>()
                            .join(" "),
                        span,
                        matched_text: text.to_owned(),
                        ai_signal: rule.ai_signal,
                        fix: None,
                        extra_context: None,
                        covering: Vec::new(),
                    })?,
                );
            }
        }
        Ok(out)
    }

    /// The finding for one match, or `None` when a filter drops it.
    #[allow(clippy::too_many_arguments)]
    fn candidate<'s>(
        &self,
        active: &Active,
        set: &'s RuleSet,
        loaded: &'s LoadedRule,
        unit: &Unit<'_>,
        range: &Range<usize>,
        skip: &SkipRanges,
        detectors: &[&str],
    ) -> Result<Option<Candidate<'s>>, EngineError> {
        let rule = loaded.rule();
        if rule.text_type != TextType::Any {
            let at = unit.base() + range.start;
            let typed = unit
                .sentences
                .and_then(|s| s.iter().find(|s| s.start <= at && at < s.end));
            if typed.is_none_or(|s| s.text_type != rule.text_type) {
                return Ok(None);
            }
        }
        if allowlisted(loaded, unit.text, range) {
            return Ok(None);
        }
        let matched = &unit.text[range.clone()];
        let match_all_caps = loaded
            .matcher()
            .is_some_and(slopvac_rules::LexicalMatcher::match_all_caps);
        if !match_all_caps && is_all_caps(matched) {
            return Ok(None);
        }
        let span = unit.span(range);
        if skip.hides(span) {
            return Ok(None);
        }
        let covering = unit.ranges(range);
        if self.guarded(
            rule,
            detectors,
            unit.text,
            range,
            unit.origin(),
            span,
            &covering,
        ) {
            return Ok(None);
        }
        // A match that spans masked text (inline code) reports the source text.
        let source_text = &self.input.source[span.start()..span.end()];
        let shown = if matched.contains('\0') {
            source_text
        } else {
            matched
        };
        let candidate = match &rule.match_ {
            Match::Substitution(_) => active
                .replacements
                .get(loaded)
                .find(shown)
                .map(str::to_owned),
            _ => None,
        };
        let fix = match candidate.as_deref() {
            Some(text) if is_single_replacement(text) && source_text == shown => Some(
                Fix::new(vec![Edit {
                    span,
                    text: text.to_owned(),
                }])
                .map_err(|e| EngineError::Internal(e.to_string()))?,
            ),
            _ => None,
        };
        Ok(Some(Candidate {
            rule_id: loaded.id(),
            pack: set.pack(),
            category: loaded.category().clone(),
            severity: active.severity,
            message: format_message(
                rule.message.as_str(),
                shown,
                candidate.as_deref().unwrap_or(""),
            ),
            span,
            matched_text: shown.to_owned(),
            ai_signal: rule.ai_signal,
            fix,
            extra_context: None,
            covering,
        }))
    }

    /// Findings of diagram rules, over diagram files and fenced diagram blocks, a warning
    /// notice for each diagram that was malformed or over a limit, and an info notice for
    /// each diagram of an unsupported type.
    /// Whether the input is a diagram file or holds a fenced diagram, so its labels are a
    /// context the document has. Reads the parsed fences only, whether or not a checker runs.
    fn holds_diagram(&self) -> bool {
        matches!(self.input.kind, Kind::Diagram(_))
            || self.parsed.blocks.iter().any(|block| {
                matches!(
                    &block.kind,
                    BlockKind::CodeBlock { lang: Some(lang), fenced: true, .. }
                        if DiagramFormat::from_lang(lang).is_some()
                )
            })
    }

    fn diagrams(&self) -> Result<DiagramResult, EngineError> {
        let engine = self.engine;
        // A checker none of whose rules applies to the document's genre does not run. One that
        // names no rules is not limited by a genre.
        let checkers: Vec<&dyn DiagramChecker> = engine
            .checkers
            .iter()
            .filter(|(_, ids)| ids.is_empty() || ids.iter().any(|id| self.diagram_rule_applies(id)))
            .map(|(checker, _)| checker.as_ref())
            .collect();
        if checkers.is_empty() {
            return Ok(DiagramResult::default());
        }
        let mut diagrams: Vec<(DiagramFormat, Extraction, Vec<NearbyProse<'_>>)> = Vec::new();
        // Parsed paragraphs and fences are in source order and do not overlap. A diagram file
        // has no paragraphs. Each paragraph is analysed lazily, and at most once.
        let paragraphs = self.paragraphs();
        if let Kind::Diagram(format) = self.input.kind {
            diagrams.push((format, extract(format, self.input.source, 0), Vec::new()));
        } else {
            // Each cursor visits each paragraph once, even when there are no neighbours.
            let mut preceding = paragraphs.iter().peekable();
            let mut following = paragraphs.iter().peekable();
            let mut before = None;
            for block in &self.parsed.blocks {
                count_block_visit();
                let BlockKind::CodeBlock {
                    lang: Some(lang),
                    body,
                    fenced: true,
                    ..
                } = &block.kind
                else {
                    continue;
                };
                let Some(format) = DiagramFormat::from_lang(lang) else {
                    continue;
                };
                while preceding
                    .peek()
                    .is_some_and(|p| p.block.span.end() <= block.span.start())
                {
                    count_block_visit();
                    before = preceding.next();
                }
                while following
                    .peek()
                    .is_some_and(|p| p.block.span.start() < block.span.end())
                {
                    count_block_visit();
                    following.next();
                }
                diagrams.push((
                    format,
                    extract_fenced(format, self.input.source, body.start()..body.end()),
                    self.nearby_prose([before, following.peek().copied()]),
                ));
            }
        }
        let mut reported = HashSet::new();
        let mut out = Vec::new();
        let mut unchecked = Vec::new();
        let mut notices = Vec::new();
        for (format, extraction, nearby) in &diagrams {
            match self.extraction_notice(*format, extraction.status)? {
                Some(n) if n.level == NoticeLevel::Info => notices.push(n),
                Some(n) => unchecked.push(n),
                None => {}
            }
            let (prose, prose_analysis) = prose_inputs(nearby);
            let input = DiagramInput {
                format: *format,
                source: self.input.source,
                extraction,
                prose: &prose,
                prose_analysis: &prose_analysis,
            };
            for checker in &checkers {
                matcher_work::entered(MatchKind::Structure);
                for hit in checker.check(&input) {
                    // A hit on a paragraph belongs to the paragraph, not to the diagram that
                    // found it, so the paragraphs shared by adjacent diagrams report once.
                    // Decide that from the rule and the mapped span, before any finding with
                    // the paragraph's text is built.
                    if hit.span.start > self.input.source.len()
                        && !reported
                            .insert((hit.rule.to_string(), self.source_span(&hit.span, nearby)?))
                    {
                        continue;
                    }
                    let Some(finding) = self.diagram_finding(&hit, nearby)? else {
                        continue;
                    };
                    out.push(finding);
                }
            }
        }
        Ok(DiagramResult {
            findings: out,
            unchecked,
            notices,
        })
    }

    /// The notice for a diagram that was not read in full.
    ///
    /// A diagram that is malformed or over a limit gets a warning: the result cannot
    /// establish a pass, so the run is incomplete. A diagram of an unsupported type gets an
    /// info notice: valid content that the extractor does not read.
    fn extraction_notice(
        &self,
        format: DiagramFormat,
        status: ExtractionStatus,
    ) -> Result<Option<Notice>, EngineError> {
        let (code, message) = match status {
            ExtractionStatus::Ok => return Ok(None),
            ExtractionStatus::Unsupported(r) => (extract_code::UNSUPPORTED, r.to_owned()),
            ExtractionStatus::Malformed(r) => (extract_code::MALFORMED, r.to_owned()),
            ExtractionStatus::BudgetExhausted(hit) => (
                extract_code::BUDGET,
                format!("the {} limit of {} was reached", hit.cap, hit.limit),
            ),
            // A status added later is a failure until this match learns its code.
            _ => (
                extract_code::MALFORMED,
                "diagram extraction failed".to_owned(),
            ),
        };
        let (level, tail) = if code == extract_code::UNSUPPORTED {
            (NoticeLevel::Info, "the diagram was not checked")
        } else {
            (NoticeLevel::Warning, "the diagram was not fully checked")
        };
        let mut n = notice(code, level, format!("{message}; {tail}"))?;
        n.path = Some(self.input.path.to_owned());
        let mut data = serde_json::Map::new();
        match status {
            ExtractionStatus::Unsupported(_) => {
                data.insert("document".to_owned(), self.input.path.into());
                data.insert("kind".to_owned(), format_name(format).into());
            }
            ExtractionStatus::BudgetExhausted(hit) => {
                data.insert("budget".to_owned(), hit.cap.into());
                data.insert("limit".to_owned(), hit.limit.into());
            }
            _ => {}
        }
        Ok(Some(n.with_data(data)))
    }

    /// The parsed paragraphs that have prose, each with its analysis. A diagram file has none.
    fn paragraphs(&self) -> Vec<Paragraph<'_>> {
        if matches!(self.input.kind, Kind::Diagram(_)) {
            return Vec::new();
        }
        self.parsed
            .blocks
            .iter()
            .filter(|b| {
                count_block_visit();
                matches!(b.kind, BlockKind::Paragraph)
            })
            .filter_map(|block| {
                let projection = block.projection.as_ref()?;
                Some(Paragraph {
                    block,
                    projection,
                    analysis: slopvac_diagrams::ProseAnalysis::new(projection.text()),
                })
            })
            .collect()
    }

    /// The paragraphs next to a fenced block: the last one before it and the first after.
    ///
    /// Their text is projected prose, so a checker's offsets into it are not source bytes.
    /// Each paragraph gets a base past the end of the source and the paragraphs follow each
    /// other, one byte apart. [`Self::source_span`] maps a hit back through the projection.
    fn nearby_prose<'b>(&self, neighbours: [Option<&'b Paragraph<'b>>; 2]) -> Vec<NearbyProse<'b>> {
        // The first base is past the end of the source, so a range in prose never reads as a
        // source range: `hit.span.start > source.len()` marks a hit on a paragraph.
        let mut base = self.input.source.len() + 1;
        let mut out = Vec::new();
        for paragraph in neighbours.into_iter().flatten() {
            out.push(NearbyProse {
                base,
                block: paragraph.block,
                projection: paragraph.projection,
                analysis: &paragraph.analysis,
            });
            base += paragraph.projection.text().len() + 1;
        }
        out
    }

    /// The source span of a checker's hit: a source range as it is, or a range in the
    /// projected prose mapped back to source bytes.
    fn source_span(
        &self,
        hit: &Range<usize>,
        nearby: &[NearbyProse<'_>],
    ) -> Result<Span, EngineError> {
        let bad = |why: &str| EngineError::BadRange(format!("{hit:?}: {why}"));
        if hit.start > hit.end {
            return Err(bad("the range is reversed"));
        }
        let span = if hit.start <= self.input.source.len() {
            if hit.end > self.input.source.len() {
                return Err(bad("the range ends past the file"));
            }
            Span::new(hit.start, hit.end).map_err(|e| bad(&e.to_string()))?
        } else {
            let prose = nearby
                .iter()
                .find(|n| n.base <= hit.start && hit.end <= n.base + n.text().len())
                .ok_or_else(|| bad("the range is outside the prose"))?;
            let (from, to) = (hit.start - prose.base, hit.end - prose.base);
            if from == 0 && to == prose.text().len() {
                prose.block.span
            } else if prose.text().is_char_boundary(from) && prose.text().is_char_boundary(to) {
                prose.projection.span_for_bytes(from, to)
            } else {
                return Err(bad("the range splits a character"));
            }
        };
        self.index.check_span(span)?;
        Ok(span)
    }

    fn diagram_finding(
        &self,
        hit: &DiagramHit,
        nearby: &[NearbyProse<'_>],
    ) -> Result<Option<Finding>, EngineError> {
        let Some(active) = self.engine.diagram_rules.get(&hit.rule) else {
            return Ok(None);
        };
        if !self.diagram_rule_applies(&hit.rule) {
            return Ok(None);
        }
        let span = self.source_span(&hit.span, nearby)?;
        let loaded = active
            .at
            .map(|(s, c, r)| &self.engine.sets[s].categories()[c].rules()[r]);
        let rule = loaded.map(LoadedRule::rule);
        let exceptions: Vec<&str> = rule.map_or_else(Vec::new, |r| {
            r.exceptions().iter().map(|e| e.name.as_str()).collect()
        });
        let detectors: Vec<&str> = rule.map_or_else(Vec::new, |r| {
            r.exceptions()
                .iter()
                .filter_map(|e| e.detector.as_ref().map(slopvac_rules::Slug::as_str))
                .collect()
        });
        let matched = hit
            .matched
            .clone()
            .unwrap_or_else(|| self.input.source[span.start()..span.end()].to_owned());
        if hit.span.start > self.input.source.len() {
            count_prose_finding_bytes(matched.len());
        }
        if let Some(rule) = rule
            && self.guarded_with(
                Some(slopvac_diagrams::CONTEXT),
                rule,
                &detectors,
                self.input.source,
                &(span.start()..span.end()),
                None,
                span,
                &[],
            )
        {
            return Ok(None);
        }
        if self.suppressed(hit.rule.as_str(), &exceptions, span) {
            return Ok(None);
        }
        let pack =
            PackId::new(hit.rule.pack()).map_err(|e| EngineError::Internal(e.to_string()))?;
        let rule_id = hit.rule.clone();
        let message = rule.map_or_else(
            || hit.message.clone(),
            |r| format_message(r.message.as_str(), &matched, ""),
        );
        self.finding(Candidate {
            rule_id: &rule_id,
            pack: &pack,
            category: category_of(&rule_id),
            severity: active.severity,
            message,
            span,
            matched_text: matched,
            ai_signal: rule.map_or(AiSignal::None, |r| r.ai_signal),
            fix: None,
            extra_context: Some(slopvac_diagrams::CONTEXT),
            covering: Vec::new(),
        })
        .map(Some)
    }

    /// One `meta.invalid-suppression` error for each directive that does not hold.
    fn invalid_directives(&self) -> Result<Vec<Finding>, EngineError> {
        let pack = PackId::new(ENGINE_PACK).map_err(|e| EngineError::Internal(e.to_string()))?;
        let rule_id = RuleId::new(format!("{ENGINE_PACK}:{INVALID_SUPPRESSION}"))
            .map_err(|e| EngineError::Internal(e.to_string()))?;
        self.directives
            .invalid
            .iter()
            .map(|invalid| {
                self.finding(Candidate {
                    rule_id: &rule_id,
                    pack: &pack,
                    category: CategoryId::new("meta")
                        .map_err(|e| EngineError::Internal(e.to_string()))?,
                    severity: Severity::Error,
                    message: invalid.message.clone(),
                    span: invalid.span,
                    matched_text: self.input.source[invalid.span.start()..invalid.span.end()]
                        .to_owned(),
                    ai_signal: AiSignal::None,
                    fix: None,
                    extra_context: None,
                    covering: Vec::new(),
                })
            })
            .collect()
    }
}
