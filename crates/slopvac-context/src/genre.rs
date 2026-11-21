//! Genres as data: the `genre` artifact of `schemas/v3/genre.schema.json`, specified in
//! `docs/contract/plugins.md`, section 4. This module holds the definitions, a registry with
//! an `extends` chain, detection with reasons, and resolution of the genre for one document.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::path::Path;

use globset::{GlobBuilder, GlobMatcher};
use serde::Deserialize;
use serde::de::{self, Visitor};
use slopvac_config::{FilesError, FilesMatcher};

use crate::schema::{
    Extensions, GENRE_SCHEMA_VERSION, check_schema_version, is_name, is_ref, is_rule_key, present,
};
use crate::{BlockKind, DocumentView, Error, Pattern, normalize_path};

/// The level a rule or category reports at (`RuleLevel` in `config.schema.json`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum RuleLevel {
    /// Report as an error.
    Error,
    /// Report as a warning.
    Warning,
    /// Report as a suggestion.
    Suggestion,
    /// Disable.
    Off,
}

/// Strictness profile that a genre selects.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Profile {
    /// Strict.
    Strict,
    /// Normal.
    Normal,
    /// Relaxed.
    Relaxed,
}

impl Profile {
    /// The profile name as written in data files.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Strict => "strict",
            Self::Normal => "normal",
            Self::Relaxed => "relaxed",
        }
    }
}

/// A density budget: a number, or `none` to clear a budget from a lower layer.
#[derive(Debug, Clone, Copy, PartialEq, Deserialize)]
#[serde(untagged)]
pub enum Budget {
    /// Findings per 100 words, at least 0.
    Limit(f64),
    /// No budget.
    None(NoBudget),
}

/// The string `none`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
pub enum NoBudget {
    /// The only accepted string.
    #[serde(rename = "none")]
    None,
}

/// The table form of `CategorySettings`.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct CategoryTable {
    /// Level of the category.
    #[serde(default, deserialize_with = "present")]
    pub severity: Option<RuleLevel>,
    /// Lowest level that inherited rules may report at.
    #[serde(default, deserialize_with = "present")]
    pub minimum_severity: Option<RuleLevel>,
    /// Density budget.
    #[serde(default, deserialize_with = "present")]
    pub max_per_100_words: Option<Budget>,
    /// Multiplier on the category's share of the score.
    #[serde(default, deserialize_with = "present")]
    pub weight: Option<f64>,
    #[serde(flatten)]
    _extensions: Extensions,
}

/// Per-category dials. A bare level stands for `{ severity = <level> }`.
#[derive(Debug, Clone)]
pub enum CategorySettings {
    /// A bare level.
    Level(RuleLevel),
    /// A table of dials.
    Table(CategoryTable),
}

impl<'de> Deserialize<'de> for CategorySettings {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = CategorySettings;

            fn expecting(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str("a rule level or a table of category settings")
            }

            fn visit_str<E: de::Error>(self, v: &str) -> Result<CategorySettings, E> {
                RuleLevel::deserialize(de::value::StrDeserializer::new(v))
                    .map(CategorySettings::Level)
            }

            fn visit_map<A: de::MapAccess<'de>>(
                self,
                map: A,
            ) -> Result<CategorySettings, A::Error> {
                CategoryTable::deserialize(de::value::MapAccessDeserializer::new(map))
                    .map(CategorySettings::Table)
            }
        }
        d.deserialize_any(V)
    }
}

impl CategorySettings {
    fn as_table(&self) -> CategoryTable {
        match self {
            Self::Level(l) => CategoryTable {
                severity: Some(*l),
                ..CategoryTable::default()
            },
            Self::Table(t) => t.clone(),
        }
    }
}

impl CategoryTable {
    /// Set every dial that `over` sets.
    fn patch(&mut self, over: &CategoryTable) {
        self.severity = over.severity.or(self.severity);
        self.minimum_severity = over.minimum_severity.or(self.minimum_severity);
        self.max_per_100_words = over.max_per_100_words.or(self.max_per_100_words);
        self.weight = over.weight.or(self.weight);
    }
}

/// Which text a detection signal reads.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum SignalKind {
    /// A glob over the project-relative path.
    Path,
    /// A front matter key with an optional exact value.
    FrontMatter,
    /// A PCRE2 pattern over heading text.
    Heading,
    /// A PCRE2 pattern over the body.
    Text,
}

impl SignalKind {
    fn as_str(self) -> &'static str {
        match self {
            Self::Path => "path",
            Self::FrontMatter => "front-matter",
            Self::Heading => "heading",
            Self::Text => "text",
        }
    }
}

/// A front matter value that a signal compares with.
#[derive(Debug, Clone, PartialEq, Deserialize)]
#[serde(untagged)]
pub enum Scalar {
    /// A boolean.
    Bool(bool),
    /// A whole number.
    Int(i64),
    /// A fractional number.
    Float(f64),
    /// A string.
    Str(String),
}

impl Scalar {
    /// The text a front matter value is compared as: `true`, `42`, `1.5`, or the string.
    ///
    /// Signals compile their expected value through this, and the engine renders the
    /// scalars of a document's front matter through it, so both sides compare one text.
    #[must_use]
    pub fn to_text(&self) -> String {
        match self {
            Self::Bool(b) => b.to_string(),
            Self::Int(i) => i.to_string(),
            Self::Float(f) => f.to_string(),
            Self::Str(s) => s.clone(),
        }
    }
}

/// One detection signal. `kind` selects which other field applies.
#[derive(Debug, Clone, Deserialize)]
pub struct Signal {
    /// Signal kind.
    pub kind: SignalKind,
    /// Score added when the signal matches. Defaults to 1.
    #[serde(default = "default_weight")]
    pub weight: f64,
    /// `path`: glob over the path.
    #[serde(default, deserialize_with = "present")]
    pub glob: Option<String>,
    /// `front-matter`: key name.
    #[serde(default, deserialize_with = "present")]
    pub key: Option<String>,
    /// `front-matter`: exact value; absent means the key only has to exist.
    #[serde(default, deserialize_with = "present")]
    pub equals: Option<Scalar>,
    /// `heading` and `text`: PCRE2 pattern.
    #[serde(default, deserialize_with = "present")]
    pub pattern: Option<String>,
    #[serde(flatten)]
    _extensions: Extensions,
}

fn default_weight() -> f64 {
    1.0
}

fn default_min_score() -> f64 {
    1.0
}

/// Signals that suggest the genre. A document scores the sum of the weights of the signals
/// that match. The genre is a candidate when the score reaches `min_score`.
#[derive(Debug, Clone, Deserialize)]
pub struct Detect {
    /// Score a genre needs to be a candidate. Defaults to 1.
    #[serde(default = "default_min_score")]
    pub min_score: f64,
    /// Detection signals, at least one.
    pub signals: Vec<Signal>,
    #[serde(flatten)]
    _extensions: Extensions,
}

/// A genre definition as written in a pack file.
#[derive(Debug, Clone, Deserialize)]
pub struct GenreSpec {
    /// Must be 3.
    pub schema_version: u32,
    /// Genre id, `^[a-z][a-z0-9-]*$`.
    pub id: String,
    /// Display title.
    #[serde(default, deserialize_with = "present")]
    pub title: Option<String>,
    /// What the genre is for.
    #[serde(default, deserialize_with = "present")]
    pub description: Option<String>,
    /// Typical documents, for people.
    #[serde(default, deserialize_with = "present")]
    pub surfaces: Option<String>,
    /// Genres this one builds on, lowest first. Their settings apply below this genre's.
    #[serde(default)]
    pub extends: Vec<String>,
    /// Strictness profile that the genre selects when no other layer sets one.
    #[serde(default, deserialize_with = "present")]
    pub profile: Option<Profile>,
    /// Detection. A genre without it is never detected.
    #[serde(default, deserialize_with = "present")]
    pub detect: Option<Detect>,
    /// Styles the genre activates, in order.
    #[serde(default)]
    pub styles: Vec<String>,
    /// Context tags that every document of the genre carries.
    #[serde(default)]
    pub contexts: Vec<String>,
    /// Settings per category name.
    #[serde(default)]
    pub categories: BTreeMap<String, CategorySettings>,
    /// Level per rule name.
    #[serde(default)]
    pub rules: BTreeMap<String, RuleLevel>,
    #[serde(flatten)]
    _extensions: Extensions,
}

impl GenreSpec {
    /// Parse one genre from YAML.
    pub fn from_yaml(text: &str) -> Result<Self, Error> {
        serde_saphyr::from_str(text).map_err(Error::Yaml)
    }

    /// Check the rules that the schema states beyond field types.
    pub fn validate(&self) -> Result<(), Error> {
        let id = &self.id;
        let fail = |msg: String| Error::Parse(format!("genre `{id}`: {msg}"));
        check_schema_version(
            &format!("genre `{id}`"),
            self.schema_version,
            GENRE_SCHEMA_VERSION,
        )?;
        if !is_name(id) {
            return Err(fail("id must be lowercase kebab-case".into()));
        }
        for (what, text) in [
            ("title", &self.title),
            ("description", &self.description),
            ("surfaces", &self.surfaces),
        ] {
            if text.as_deref().is_some_and(str::is_empty) {
                return Err(fail(format!("{what} needs at least one character")));
            }
        }
        let mut seen = BTreeSet::new();
        for r in &self.extends {
            if !is_ref(r) {
                return Err(fail(format!("`extends` entry `{r}` is not a genre name")));
            }
            if !seen.insert(r) {
                return Err(fail(format!("`extends` repeats `{r}`")));
            }
        }
        if let Some(r) = self.styles.iter().find(|r| !is_ref(r)) {
            return Err(fail(format!("`styles` entry `{r}` is not a style name")));
        }
        let mut tags = BTreeSet::new();
        for c in &self.contexts {
            if !is_name(c) {
                return Err(fail(format!(
                    "`contexts` entry `{c}` is not a context tag (lowercase kebab-case)"
                )));
            }
            if !tags.insert(c) {
                return Err(fail(format!("`contexts` repeats `{c}`")));
            }
        }
        let mut keys = self.categories.keys().chain(self.rules.keys());
        if let Some(k) = keys.find(|k| !is_rule_key(k)) {
            return Err(fail(format!("`{k}` is not a rule or category name")));
        }
        for c in self.categories.values() {
            if let CategorySettings::Table(t) = c
                && (matches!(t.max_per_100_words, Some(Budget::Limit(n)) if !at_least_zero(n))
                    || t.weight.is_some_and(|w| !at_least_zero(w)))
            {
                return Err(fail("budgets and weights are at least 0".into()));
            }
        }
        if let Some(d) = &self.detect {
            d.validate(id)?;
        }
        Ok(())
    }
}

impl Detect {
    fn validate(&self, genre: &str) -> Result<(), Error> {
        let fail = |msg: &str| Error::Parse(format!("genre `{genre}`: {msg}"));
        if !above_zero(self.min_score) {
            return Err(fail("`min_score` must be greater than 0"));
        }
        if self.signals.is_empty() {
            return Err(fail("`detect.signals` needs at least one signal"));
        }
        for s in &self.signals {
            if !above_zero(s.weight) {
                return Err(fail("signal weight must be greater than 0"));
            }
            let (own, others) = s.fields();
            if !own {
                return Err(fail(&format!(
                    "a `{}` signal is missing its field",
                    s.kind.as_str()
                )));
            }
            if let Some(name) = others {
                return Err(fail(&format!(
                    "a `{}` signal does not take `{name}`",
                    s.kind.as_str()
                )));
            }
            if [&s.glob, &s.key, &s.pattern]
                .into_iter()
                .flatten()
                .any(String::is_empty)
            {
                return Err(fail("signal fields need at least one character"));
            }
        }
        Ok(())
    }
}

/// A finite number of at least 0. NaN and infinity fail, as does anything below 0.
fn at_least_zero(n: f64) -> bool {
    n.is_finite() && n >= 0.0
}

/// A finite number above 0 (`exclusiveMinimum: 0`).
fn above_zero(n: f64) -> bool {
    n.is_finite() && n > 0.0
}

impl Signal {
    /// Whether the field that the kind needs is set, and the first field it does not take.
    fn fields(&self) -> (bool, Option<&'static str>) {
        let set = [
            ("glob", self.glob.is_some()),
            ("key", self.key.is_some()),
            ("equals", self.equals.is_some()),
            ("pattern", self.pattern.is_some()),
        ];
        let takes: &[&str] = match self.kind {
            SignalKind::Path => &["glob"],
            SignalKind::FrontMatter => &["key", "equals"],
            SignalKind::Heading | SignalKind::Text => &["pattern"],
        };
        let required = match self.kind {
            SignalKind::Path => "glob",
            SignalKind::FrontMatter => "key",
            SignalKind::Heading | SignalKind::Text => "pattern",
        };
        let has_required = set.iter().any(|(n, on)| *n == required && *on);
        let stray = set
            .iter()
            .find(|(n, on)| *on && !takes.contains(n))
            .map(|(n, _)| *n);
        (has_required, stray)
    }
}

/// Parse a YAML list of genre definitions.
pub fn parse_genres(yaml: &str) -> Result<Vec<GenreSpec>, Error> {
    serde_saphyr::from_str(yaml).map_err(Error::Yaml)
}

struct CompiledSignal {
    matcher: Matcher,
    weight: f64,
}

enum Matcher {
    Heading(Pattern),
    Text(Pattern),
    Path(GlobMatcher),
    FrontMatter(String, Option<String>),
}

struct Genre {
    spec: GenreSpec,
    min_score: f64,
    signals: Vec<CompiledSignal>,
}

/// Why a genre was chosen, or how well a candidate scored.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reason {
    /// Kebab-case signal name, as in the lint report.
    pub signal: String,
    /// What matched.
    pub detail: String,
}

/// How the genre was chosen.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GenreSource {
    /// Front matter or a config assignment.
    Explicit,
    /// Detection signals.
    Detected,
    /// The fallback genre.
    Default,
}

/// The genre applied to one document.
#[derive(Debug, Clone, PartialEq)]
pub struct GenreResult {
    /// Genre id.
    pub id: String,
    /// How it was chosen.
    pub source: GenreSource,
    /// Signals behind the choice.
    pub reasons: Vec<Reason>,
    /// Detection score for every concrete genre, best first.
    pub scores: Vec<(String, f64)>,
    /// The genre a `[[genres]]` block assigns, when front matter chose another one. Its
    /// contexts still apply: contexts from a path or the config are additive.
    pub assigned: Option<String>,
}

/// A `[[genres]]` block reduced to what assignment needs.
#[derive(Debug, Clone)]
pub struct GenreAssignment {
    /// Globs relative to the config directory.
    pub files: Vec<String>,
    /// Genre id.
    pub genre: String,
}

/// Inputs to [`GenreRegistry::resolve`] besides the document.
#[derive(Debug, Clone, Default)]
pub struct ResolveOptions<'a> {
    /// `[[genres]]` blocks in file order. The last matching block wins.
    pub assignments: &'a [GenreAssignment],
    /// Path relative to the config directory, for glob matching. Defaults to the document path.
    pub relative_path: Option<&'a str>,
    /// Where the genre a document declares for itself comes from.
    pub declared: DeclaredGenre<'a>,
}

/// Where [`GenreRegistry::resolve`] takes the genre that a document declares for itself.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
#[non_exhaustive]
pub enum DeclaredGenre<'a> {
    /// The `genre` field of the document's versioned `slopvac:` block
    /// ([`DocumentView::slopvac_block`]). A top-level `genre` key is ordinary data. This reads
    /// no project policy; a host that has one passes the checked genre as `Given`.
    #[default]
    FromFrontMatter,
    /// A genre the host has already read, validated and checked against the project policy,
    /// or none. The document's own front matter is not consulted.
    Given(Option<&'a str>),
}

/// Validated set of genres.
pub struct GenreRegistry {
    genres: Vec<Genre>,
    default: String,
    /// Context tags the host declares in code, on top of the `contexts` of the genre files,
    /// see [`GenreRegistry::with_contexts`].
    contexts: BTreeMap<String, Vec<String>>,
}

impl GenreRegistry {
    /// Validate and compile `specs`. `default` is the fallback genre id.
    pub fn new(specs: Vec<GenreSpec>, default: &str) -> Result<Self, Error> {
        let mut seen = BTreeSet::new();
        for s in &specs {
            s.validate()?;
            if !seen.insert(s.id.clone()) {
                return Err(Error::Parse(format!("genre `{}` is defined twice", s.id)));
            }
        }
        for s in &specs {
            if let Some(p) = s.extends.iter().find(|r| !seen.contains(ref_name(r))) {
                return Err(Error::Parse(format!(
                    "genre `{}` extends unknown genre `{p}`",
                    s.id
                )));
            }
        }
        let genres = specs
            .into_iter()
            .map(compile)
            .collect::<Result<Vec<_>, _>>()?;
        let reg = Self {
            genres,
            default: default.to_string(),
            contexts: BTreeMap::new(),
        };
        for g in &reg.genres {
            reg.chain(&g.spec.id)?;
        }
        match reg.get(default) {
            Some(_) => Ok(reg),
            None => Err(Error::UnknownGenre(default.to_string())),
        }
    }

    /// Declare more context tags for a genre than its file lists. Documents of the genre, and of genres that extend
    /// it, carry the tags for the whole document (see `DeclaredContextTagger`).
    pub fn with_contexts(mut self, genre: &str, tags: &[&str]) -> Result<Self, Error> {
        self.get(genre)
            .ok_or_else(|| Error::UnknownGenre(genre.to_string()))?;
        if let Some(t) = tags.iter().find(|t| !is_name(t)) {
            return Err(Error::Parse(format!(
                "genre `{genre}`: `{t}` is not a context tag (lowercase kebab-case)"
            )));
        }
        self.contexts.insert(
            genre.to_string(),
            tags.iter().map(|t| (*t).to_string()).collect(),
        );
        Ok(self)
    }

    fn get(&self, id: &str) -> Option<&Genre> {
        self.genres.iter().find(|g| g.spec.id == id)
    }

    /// Genre ids in definition order.
    #[must_use]
    pub fn ids(&self) -> Vec<&str> {
        self.genres.iter().map(|g| g.spec.id.as_str()).collect()
    }

    /// The definition of one genre.
    #[must_use]
    pub fn spec(&self, id: &str) -> Option<&GenreSpec> {
        self.get(id).map(|g| &g.spec)
    }

    /// The genre and everything it extends, lowest first and the genre itself last. A
    /// genre that several paths reach appears once, at its first position.
    pub fn chain(&self, id: &str) -> Result<Vec<&GenreSpec>, Error> {
        let mut out = Vec::new();
        self.visit(id, &mut Vec::new(), &mut out)?;
        Ok(out)
    }

    fn visit<'a>(
        &'a self,
        id: &str,
        path: &mut Vec<String>,
        out: &mut Vec<&'a GenreSpec>,
    ) -> Result<(), Error> {
        let g = self
            .get(ref_name(id))
            .ok_or_else(|| Error::UnknownGenre(id.to_string()))?;
        if path.contains(&g.spec.id) {
            return Err(Error::Parse(format!(
                "genre `{}` has an `extends` cycle",
                g.spec.id
            )));
        }
        if out.iter().any(|s| s.id == g.spec.id) {
            return Ok(());
        }
        path.push(g.spec.id.clone());
        for parent in &g.spec.extends {
            self.visit(parent, path, out)?;
        }
        path.pop();
        out.push(&g.spec);
        Ok(())
    }

    /// Level per rule for a genre. Later genres in the chain win over earlier ones.
    pub fn rules(&self, id: &str) -> Result<BTreeMap<String, RuleLevel>, Error> {
        let mut out = BTreeMap::new();
        for s in self.chain(id)? {
            out.extend(s.rules.iter().map(|(k, v)| (k.clone(), *v)));
        }
        Ok(out)
    }

    /// Settings per category for a genre. A map merges by key, and a later genre in the
    /// chain patches an earlier one's entry dial by dial (`docs/contract/config.md`,
    /// section 1.2). A bare level counts as `severity`.
    pub fn categories(&self, id: &str) -> Result<BTreeMap<String, CategoryTable>, Error> {
        let mut out: BTreeMap<String, CategoryTable> = BTreeMap::new();
        for s in self.chain(id)? {
            for (k, v) in &s.categories {
                out.entry(k.clone()).or_default().patch(&v.as_table());
            }
        }
        Ok(out)
    }

    /// Declared context tags for a genre, lowest first, without duplicates.
    pub fn contexts(&self, id: &str) -> Result<Vec<String>, Error> {
        let mut out: Vec<String> = Vec::new();
        for s in self.chain(id)? {
            for c in s
                .contexts
                .iter()
                .chain(self.contexts.get(&s.id).into_iter().flatten())
            {
                if !out.contains(c) {
                    out.push(c.clone());
                }
            }
        }
        Ok(out)
    }

    /// Profile from the nearest genre in the chain that sets one.
    pub fn profile(&self, id: &str) -> Result<Option<Profile>, Error> {
        Ok(self.chain(id)?.iter().rev().find_map(|s| s.profile))
    }

    /// Choose the genre for a document: front matter, then a config assignment, then
    /// detection, then the default.
    pub fn resolve(
        &self,
        doc: &dyn DocumentView,
        opts: &ResolveOptions<'_>,
    ) -> Result<GenreResult, Error> {
        // Assignments match the path as given, like the config stack does; only the path
        // signals below read a normalized copy.
        let native = opts.relative_path.unwrap_or_else(|| doc.path());
        let rel = normalize_path(native);
        let rel = rel.as_str();
        let candidates = self.score(doc, rel)?;
        let mut scores: Vec<(String, f64)> = candidates
            .iter()
            .map(|(g, s, _)| (g.spec.id.clone(), *s))
            .collect();
        scores.sort_by(|a, b| b.1.total_cmp(&a.1));
        let explicit = |id: &str, signal: &str, detail: String| -> Result<GenreResult, Error> {
            self.get(id)
                .ok_or_else(|| Error::UnknownGenre(id.to_string()))?;
            Ok(GenreResult {
                id: id.to_string(),
                source: GenreSource::Explicit,
                reasons: vec![Reason {
                    signal: signal.to_string(),
                    detail,
                }],
                scores: scores.clone(),
                assigned: None,
            })
        };
        let declared = match opts.declared {
            DeclaredGenre::FromFrontMatter => doc.slopvac_block("genre"),
            DeclaredGenre::Given(id) => id,
        };
        let mut assigned = None;
        for (i, a) in opts.assignments.iter().enumerate() {
            if files_match(&a.files, native)? {
                assigned = Some((i, a));
            }
        }
        if let Some(id) = declared {
            // Front matter picks the genre, but a path or config assignment keeps its
            // contexts and stays on record as a reason.
            let mut result = explicit(id, "front-matter", format!("`genre: {id}`"))?;
            if let Some((i, a)) = assigned.filter(|(_, a)| a.genre != id) {
                result.reasons.push(Reason {
                    signal: "path-glob".to_string(),
                    detail: format!("`[[genres]]` block {i} matches `{rel}`"),
                });
                result.assigned = Some(a.genre.clone());
            }
            return Ok(result);
        }
        if let Some((i, a)) = assigned {
            return explicit(
                &a.genre,
                "path-glob",
                format!("`[[genres]]` block {i} matches `{rel}`"),
            );
        }
        let mut best: Option<&(&Genre, f64, Vec<Reason>)> = None;
        // plugins.md section 4: a tie goes to the genre listed last in the config, then to the
        // lexically smaller qualified id. The registry holds the genres in the order the
        // host registered them, which is the order the config lists its packs and genre
        // files, so a later position is a genre listed later. Positions are unique, so a tie
        // always resolves on the first rule; the id rule would only apply to two genres at
        // one position, and `new` rejects a repeated id. `>=` lets the later candidate win.
        for c in candidates.iter().filter(|(g, s, _)| g.is_candidate(*s)) {
            if best.is_none_or(|b| c.1 >= b.1) {
                best = Some(c);
            }
        }
        if let Some((g, _, reasons)) = best {
            return Ok(GenreResult {
                id: g.spec.id.clone(),
                source: GenreSource::Detected,
                reasons: reasons.clone(),
                scores,
                assigned: None,
            });
        }
        Ok(GenreResult {
            id: self.default.clone(),
            source: GenreSource::Default,
            reasons: vec![Reason {
                signal: "default".to_string(),
                detail: format!("no genre reached its threshold; using `{}`", self.default),
            }],
            scores,
            assigned: None,
        })
    }

    /// Genres that extend `parent` and reach their detection threshold on this document,
    /// best first. Two or more entries mean the page mixes content types, which the
    /// mixed-type judgement rule asks a reviewer to split.
    pub fn mixed_types(
        &self,
        doc: &dyn DocumentView,
        parent: &str,
    ) -> Result<Vec<(String, f64)>, Error> {
        let mut out = Vec::new();
        let rel = normalize_path(doc.path());
        for (g, score, _) in self.score(doc, &rel)? {
            let below_parent =
                g.spec.id != parent && self.chain(&g.spec.id)?.iter().any(|s| s.id == parent);
            if below_parent && g.is_candidate(score) {
                out.push((g.spec.id.clone(), score));
            }
        }
        out.sort_by(|a, b| b.1.total_cmp(&a.1));
        Ok(out)
    }

    /// Score every genre that has detection signals. `rel` is the normalized path that
    /// `path` signals match.
    fn score<'a>(&'a self, doc: &dyn DocumentView, rel: &str) -> Result<Vec<Candidate<'a>>, Error> {
        let blocks = doc.blocks();
        let headings: Vec<&str> = blocks
            .iter()
            .filter(|b| b.kind == BlockKind::Heading)
            .map(|b| b.text)
            .collect();
        let body = blocks.iter().map(|b| b.text).collect::<Vec<_>>().join("\n");
        let mut out = Vec::new();
        for g in self.genres.iter().filter(|g| !g.signals.is_empty()) {
            let mut total = 0.0;
            let mut reasons = Vec::new();
            for s in &g.signals {
                let hit = match &s.matcher {
                    Matcher::Heading(p) => {
                        let mut found = None;
                        for h in &headings {
                            if p.is_match(h)? {
                                found = Some(("heading", format!("heading `{h}`")));
                                break;
                            }
                        }
                        found
                    }
                    Matcher::Text(p) => p
                        .find(&body)?
                        .map(|m| ("text", format!("text `{}`", lossy(&body, m)))),
                    Matcher::Path(glob) => glob
                        .is_match(rel)
                        .then(|| ("path", format!("path `{}`", doc.path()))),
                    Matcher::FrontMatter(k, want) => match doc.front_matter(k) {
                        Some(v) if want.as_deref().is_none_or(|w| w == v) => {
                            Some(("front-matter", format!("`{k}: {v}`")))
                        }
                        _ => None,
                    },
                };
                if let Some((signal, detail)) = hit {
                    total += s.weight;
                    reasons.push(Reason {
                        signal: signal.to_string(),
                        detail: format!("{detail} (+{})", s.weight),
                    });
                }
            }
            out.push((g, total, reasons));
        }
        Ok(out)
    }
}

impl Genre {
    /// A genre with detection signals is a candidate when its score reaches `min_score`.
    fn is_candidate(&self, score: f64) -> bool {
        !self.signals.is_empty() && score >= self.min_score
    }
}

/// The matched bytes as text. A pattern such as `\C` can end a match inside a character.
fn lossy(text: &str, range: std::ops::Range<usize>) -> std::borrow::Cow<'_, str> {
    String::from_utf8_lossy(text.as_bytes().get(range).unwrap_or_default())
}

/// The genre name in a `Ref`. A registry holds one set of genres, so the pack prefix of a
/// qualified `<plugin>:<name>` only names where the genre came from.
fn ref_name(r: &str) -> &str {
    r.rsplit_once(':').map_or(r, |(_, name)| name)
}

type Candidate<'a> = (&'a Genre, f64, Vec<Reason>);

/// Whether a `files` list matches a path relative to the config directory. The config crate
/// owns the matching, so a `[[genres]]` block selects the same files here and in the config
/// stack.
fn files_match(patterns: &[String], native: &str) -> Result<bool, Error> {
    let matcher = FilesMatcher::new(patterns, Path::new("")).map_err(|e| match e {
        FilesError::Pattern { pattern, source } => Error::Glob { pattern, source },
        FilesError::Set(source) => Error::GlobSet(source),
    })?;
    Ok(matcher.is_match(Path::new(native)))
}

fn compile(spec: GenreSpec) -> Result<Genre, Error> {
    let mut signals = Vec::new();
    let mut min_score = 0.0;
    if let Some(d) = &spec.detect {
        min_score = d.min_score;
        for s in &d.signals {
            let field = |v: &Option<String>| v.clone().unwrap_or_default();
            if matches!(s.kind, SignalKind::Heading | SignalKind::Text) {
                crate::pattern::check_authored(&field(&s.pattern))?;
            }
            let matcher = match s.kind {
                SignalKind::Heading => Matcher::Heading(Pattern::new_caseless(&field(&s.pattern))?),
                SignalKind::Text => Matcher::Text(Pattern::new_caseless(&field(&s.pattern))?),
                SignalKind::Path => {
                    let glob = field(&s.glob);
                    let g = GlobBuilder::new(&glob)
                        .case_insensitive(true)
                        .literal_separator(true)
                        .build()
                        .map_err(|source| Error::SignalGlob {
                            genre: spec.id.clone(),
                            glob: glob.clone(),
                            source,
                        })?;
                    Matcher::Path(g.compile_matcher())
                }
                SignalKind::FrontMatter => {
                    Matcher::FrontMatter(field(&s.key), s.equals.as_ref().map(Scalar::to_text))
                }
            };
            signals.push(CompiledSignal {
                matcher,
                weight: s.weight,
            });
        }
    }
    Ok(Genre {
        spec,
        min_score,
        signals,
    })
}
