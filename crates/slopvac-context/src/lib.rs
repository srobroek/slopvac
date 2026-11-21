//! Context taggers, the tag registry and genres.

mod builtin;
mod checklist;
mod cli;
mod declarative;
mod declared;
mod genre;
mod mixed;
mod pattern;
mod reference;
mod schema;
mod structural;
mod tag;
mod view;
mod work;

pub use builtin::{
    BuiltinFile, EnforcedInvariantTagger, GENRE_FILES, ListLeadInTagger, RequirementTagger,
    TAGGER_FILES, builtin_genres, builtin_registry,
};
pub use checklist::{
    ChecklistEntry, ChecklistRule, checklist, checklist_rules, effective_gates, rule_allows,
};
pub use cli::{DeclaredGenres, command, render, run};
pub use declarative::{DeclarativeTagger, Matcher, TaggerSpec, Unit};
pub use declared::{DeclaredContextTagger, context_hint};
pub use genre::{
    Budget, CategorySettings, CategoryTable, DeclaredGenre, Detect, GenreAssignment, GenreRegistry,
    GenreResult, GenreSource, GenreSpec, NoBudget, Profile, Reason, ResolveOptions, RuleLevel,
    Scalar, Signal, SignalKind, parse_genres,
};
pub use mixed::mixed_types_entry;
pub use pattern::{Pattern, normalize_path};
pub use reference::reference_pages;
pub use schema::{GENRE_SCHEMA_VERSION, TAGGER_SCHEMA_VERSION};
pub use structural::{FrontMatterCondition, Scope, When};
pub use tag::{ContextGate, Tag, TagIndex, TagRegistry, TagSink, Tagger, normalize_tags};
pub use view::{
    BlockKind, BlockView, DocumentView, OwnedBlock, PlainDocument, SentenceView, split_sentences,
};
#[cfg(feature = "work-counters")]
#[doc(hidden)]
pub use work::{
    take_admonition_steps, take_build_elements, take_heading_steps, take_lookup_steps,
    take_materialised_tags, take_negation_steps, take_section_steps, take_text_steps,
};

pub use pattern::MAX_PATTERN_BYTES;

/// Errors from this crate. Text from documents, configs and plugins reaches `Display` only
/// through `slopvac_sanitize::line`; the fields and sources stay raw.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// A regular expression failed to compile.
    #[error("invalid pattern `{}`: {}", slopvac_sanitize::line(.pattern), slopvac_sanitize::line(&.source.to_string()))]
    Pattern {
        /// Pattern source.
        pattern: String,
        /// The PCRE2 compile error.
        #[source]
        source: slopvac_pcre2::CompileError,
    },
    /// A pattern is longer than the data-pack limit.
    #[error("pattern is {len} bytes, over the {max}-byte limit")]
    PatternTooLong {
        /// Pattern length in bytes.
        len: usize,
        /// The limit, [`MAX_PATTERN_BYTES`].
        max: usize,
    },
    /// PCRE2 failed while matching, for example on a match or JIT stack limit.
    #[error("pattern `{}` failed while matching: {}", slopvac_sanitize::line(.pattern), slopvac_sanitize::line(&.source.to_string()))]
    Match {
        /// Pattern source.
        pattern: String,
        /// The PCRE2 match error.
        #[source]
        source: slopvac_pcre2::MatchError,
    },
    /// A tagger id was registered twice.
    #[error("tagger `{}` is already registered", slopvac_sanitize::line(.0))]
    DuplicateTagger(String),
    /// The taggers produced more tags than the document is allowed, so no index was built.
    #[error("the document has more than {limit} context tags")]
    TagLimit {
        /// The most tags the document was allowed.
        limit: usize,
    },
    /// A genre id that no definition provides.
    #[error("unknown genre `{}`", slopvac_sanitize::line(.0))]
    UnknownGenre(String),
    /// A YAML data file did not parse.
    #[error("{}", slopvac_sanitize::line(&.0.to_string()))]
    Yaml(#[source] serde_saphyr::Error),
    /// A `files` pattern is not a valid gitignore-style glob.
    #[error("glob `{}`: {}", slopvac_sanitize::line(.pattern), slopvac_sanitize::line(&.source.to_string()))]
    Glob {
        /// The pattern as written.
        pattern: String,
        /// The glob parser error.
        #[source]
        source: ignore::Error,
    },
    /// A list of `files` patterns did not compile as a set.
    #[error("{}", slopvac_sanitize::line(&.0.to_string()))]
    GlobSet(#[source] ignore::Error),
    /// A `path` signal glob of a genre is invalid.
    #[error("genre `{}`: glob `{}`: {}", slopvac_sanitize::line(.genre), slopvac_sanitize::line(.glob), slopvac_sanitize::line(&.source.to_string()))]
    SignalGlob {
        /// Genre id.
        genre: String,
        /// The glob as written.
        glob: String,
        /// The glob parser error.
        #[source]
        source: globset::Error,
    },
    /// A file could not be read. The path and the OS message are escaped for a terminal.
    #[error("{}: {}", slopvac_sanitize::line(.path), slopvac_sanitize::line(&.source.to_string()))]
    Read {
        /// The path as given.
        path: String,
        /// The OS error.
        #[source]
        source: std::io::Error,
    },
    /// A file is larger than the document size cap, so none of it was read.
    #[error("{}: larger than the {cap}-byte document limit", slopvac_sanitize::line(.path))]
    TooLarge {
        /// The path as given.
        path: String,
        /// The cap in bytes, `slopvac_fs::MAX_DOCUMENT_BYTES`.
        cap: u64,
    },
    /// A file was refused without a read: it is not a regular file, or it could not be opened
    /// safely.
    #[error("{}: cannot read", slopvac_sanitize::line(.path))]
    Unreadable {
        /// The path as given.
        path: String,
    },
    /// A data file did not parse or validate.
    #[error("{}", slopvac_sanitize::line(.0))]
    Parse(String),
}
