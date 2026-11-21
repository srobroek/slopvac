//! Errors that name the file and line they come from.

use std::fmt;
use std::path::PathBuf;

use crate::messages::RulesMessage;

/// Which pack budget a load passed. The list can grow.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum PackBudget {
    /// Rule and category files, in files: [`MAX_PACK_FILES`](crate::MAX_PACK_FILES).
    Files,
    /// Directory entries of any kind, in entries: [`MAX_PACK_ENTRIES`](crate::MAX_PACK_ENTRIES).
    Entries,
    /// Bytes read, in bytes: [`MAX_PACK_BYTES`](crate::MAX_PACK_BYTES).
    Bytes,
    /// Tokens or substitutions in one rule, in entries:
    /// [`MAX_RULE_ENTRIES`](crate::MAX_RULE_ENTRIES).
    RuleEntries,
}

impl PackBudget {
    /// The `data.budget` text, such as `plugin-files`.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Files => "plugin-files",
            Self::Entries => "plugin-entries",
            Self::Bytes => "plugin-bytes",
            Self::RuleEntries => "rule-entries",
        }
    }

    /// The unit of the limit.
    #[must_use]
    pub fn unit(self) -> &'static str {
        match self {
            Self::Files => "files",
            Self::Entries | Self::RuleEntries => "entries",
            Self::Bytes => "bytes",
        }
    }
}

/// What went wrong with one file or rule.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[non_exhaustive]
pub enum LoadErrorKind {
    /// The file or directory could not be read.
    #[error("{}", RulesMessage::ReadFailed { reason: .0.clone() })]
    Read(String),
    /// The file is larger than [`MAX_RULE_FILE_BYTES`](crate::MAX_RULE_FILE_BYTES), the given
    /// number of bytes. Its stable code is `rules-file-too-large`.
    #[error("{}", RulesMessage::FileTooLarge { cap: *.0 })]
    TooLarge(u64),
    /// The pack directory holds more files, or more bytes in total, than
    /// [`MAX_PACK_FILES`](crate::MAX_PACK_FILES) or [`MAX_PACK_BYTES`](crate::MAX_PACK_BYTES)
    /// allow, or one rule lists more than [`MAX_RULE_ENTRIES`](crate::MAX_RULE_ENTRIES) tokens or
    /// substitutions. Its stable code is `rules-budget-exceeded`.
    #[error("{}", RulesMessage::BudgetExceeded {
        limit: *.limit,
        unit: .budget.unit().to_owned(),
        budget: .budget.as_str().to_owned(),
    })]
    BudgetExceeded {
        /// The budget that was passed.
        budget: PackBudget,
        /// The limit, in the unit of `budget`.
        limit: u64,
        /// The pack directory, or for `rule-entries` the rule file, as a display path, never
        /// absolute: relative to the working directory, or `<external>/<name>` outside it.
        path: String,
    },
    /// An authored pattern is longer than
    /// [`MAX_AUTHORED_PATTERN_BYTES`](crate::MAX_AUTHORED_PATTERN_BYTES). The loader refuses the
    /// whole load, as for [`LoadErrorKind::TooLarge`]. Its stable code is
    /// `rules-pattern-too-long`. The error never holds the pattern text. Its line is the line where
    /// the rule starts, because the loader keeps no position for a value inside a rule.
    #[error("{}", RulesMessage::PatternTooLong { len: *.len, limit: *.limit })]
    PatternTooLong {
        /// The pattern length as written, in UTF-8 bytes.
        len: usize,
        /// The limit in bytes, `data.limit`.
        limit: usize,
    },
    /// The file does not parse as a rule or category file.
    #[error("{}", RulesMessage::ParseFailed { reason: .0.clone() })]
    Parse(String),
    /// The extension names no supported format (`json`, `yaml`, `yml`, `toml`).
    #[error("{}", RulesMessage::UnsupportedFormat)]
    UnsupportedFormat,
    /// Two files define the same category.
    #[error("{}", RulesMessage::DuplicateCategory { id: .0.clone() })]
    DuplicateCategory(String),
    /// Two rules of one category share an id.
    #[error("{}", RulesMessage::DuplicateRule { id: .0.clone() })]
    DuplicateRule(String),
    /// A lexical rule's pattern does not compile.
    #[error("{}", RulesMessage::PatternInvalid { reason: .0.clone() })]
    Compile(String),
    /// An example's `bad` text does not match its rule.
    #[error("{}", RulesMessage::BadExampleNoMatch { index: *.index, text: format!("{:?}", .text) })]
    BadExampleDoesNotMatch {
        /// Zero-based example index.
        index: usize,
        /// The example text.
        text: String,
    },
    /// An example's `good` text matches its rule.
    #[error("{}", RulesMessage::GoodExampleMatches { index: *.index, text: format!("{:?}", .text) })]
    GoodExampleMatches {
        /// Zero-based example index.
        index: usize,
        /// The example text.
        text: String,
    },
    /// Matching an example hit a limit.
    #[error("{}", RulesMessage::MatchFailed { reason: .0.clone() })]
    Match(String),
}

/// One problem, with where it is.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoadError {
    /// The file.
    pub file: PathBuf,
    /// The one-based line, when it is known. A minified one-line file reports line 1 for
    /// parse errors and none for a rule.
    pub line: Option<u32>,
    /// The rule (`<category>.<rule>`), when the problem belongs to one.
    pub rule: Option<String>,
    /// What went wrong.
    pub kind: LoadErrorKind,
}

impl fmt::Display for LoadError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.file.display())?;
        if let Some(line) = self.line {
            write!(f, ":{line}")?;
        }
        f.write_str(": ")?;
        if let Some(rule) = &self.rule {
            write!(f, "{rule}: ")?;
        }
        write!(f, "{}", self.kind)
    }
}

impl std::error::Error for LoadError {}

/// Every problem found while loading, so one broken rule reports next to the others.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LoadErrors(pub Vec<LoadError>);

impl LoadErrors {
    /// The problems, in the order found.
    #[must_use]
    pub fn errors(&self) -> &[LoadError] {
        &self.0
    }
}

impl fmt::Display for LoadErrors {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        for (i, e) in self.0.iter().enumerate() {
            if i > 0 {
                f.write_str("\n")?;
            }
            write!(f, "{e}")?;
        }
        Ok(())
    }
}

impl std::error::Error for LoadErrors {}

impl From<LoadError> for LoadErrors {
    fn from(e: LoadError) -> Self {
        Self(vec![e])
    }
}
