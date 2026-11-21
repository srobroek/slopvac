//! The messages `slopvac-rules` reports, as one catalog that the binary registers through
//! [`message_entries`].
//!
//! [`RulesMessage`] holds the text of each [`crate::LoadErrorKind`] variant. The first three
//! entries are errors with a stable code that also shows in the text; the rest are plain
//! sentences.

use slopvac_messages::{Catalog, Entry};

/// The text of each [`crate::LoadErrorKind`] variant.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum RulesMessage {
    /// A rule or category file or directory could not be read.
    #[code("rules-read-failed")]
    #[text("cannot read: {reason}")]
    ReadFailed { reason: String },
    /// A rule or category file is larger than the file cap.
    #[code("rules-file-too-large")]
    #[message("[rules-file-too-large] file is larger than {cap} bytes")]
    FileTooLarge {
        #[count]
        cap: u64,
    },
    /// A load passed one of the pack budgets: files, entries, bytes, or entries in one rule.
    #[code("rules-budget-exceeded")]
    #[message("[rules-budget-exceeded] the input passes the limit of {limit} {unit} ({budget})")]
    BudgetExceeded {
        #[count]
        limit: u64,
        unit: String,
        budget: String,
    },
    /// An authored pattern is longer than the pattern cap.
    #[code("rules-pattern-too-long")]
    #[message("[rules-pattern-too-long] a pattern is {len} bytes, over the {limit}-byte limit")]
    PatternTooLong {
        #[count]
        len: usize,
        #[count]
        limit: usize,
    },
    /// A rule or category file does not parse. The reason is the parser's own message.
    #[code("rules-parse-failed")]
    #[text("{reason}")]
    ParseFailed { reason: String },
    /// A rule file has an extension that names no supported format.
    #[code("rules-unsupported-format")]
    #[text("unsupported file type (expected json, yaml, yml or toml)")]
    UnsupportedFormat,
    /// Two files define the same category.
    #[code("rules-duplicate-category")]
    #[text("duplicate category `{id}`")]
    DuplicateCategory { id: String },
    /// Two rules of one category share an id.
    #[code("rules-duplicate-rule")]
    #[text("duplicate rule id `{id}` in its category")]
    DuplicateRule { id: String },
    /// A lexical rule's pattern does not compile.
    #[code("rules-pattern-invalid")]
    #[text("pattern does not compile: {reason}")]
    PatternInvalid { reason: String },
    /// An example's `bad` text does not match its rule. The text shows quoted.
    #[code("rules-example-bad-no-match")]
    #[text("example {index} 'bad' text does not match its own pattern: {text}")]
    BadExampleNoMatch {
        #[count]
        index: usize,
        text: String,
    },
    /// An example's `good` text matches its rule. The text shows quoted.
    #[code("rules-example-good-matches")]
    #[text(
        "example {index} 'good' text matches the pattern, so the rule fires on its own fix: {text}"
    )]
    GoodExampleMatches {
        #[count]
        index: usize,
        text: String,
    },
    /// Matching an example hit a limit.
    #[code("rules-match-failed")]
    #[text("matching failed: {reason}")]
    MatchFailed { reason: String },
}

/// The entries of the rules catalog.
#[must_use]
pub fn message_entries() -> &'static [Entry] {
    RulesMessage::entries()
}

#[cfg(test)]
mod tests {
    use rstest::rstest;
    use slopvac_messages::Kind;

    use super::*;

    #[rstest]
    #[case::read_failed(
        RulesMessage::ReadFailed { reason: "denied".to_owned() },
        "cannot read: denied"
    )]
    #[case::file_too_large(
        RulesMessage::FileTooLarge { cap: 2_097_152 },
        "[rules-file-too-large] file is larger than 2097152 bytes"
    )]
    #[case::budget_exceeded(
        RulesMessage::BudgetExceeded {
            limit: 256,
            unit: "files".to_owned(),
            budget: "plugin-files".to_owned(),
        },
        "[rules-budget-exceeded] the input passes the limit of 256 files (plugin-files)"
    )]
    #[case::pattern_too_long(
        RulesMessage::PatternTooLong { len: 9000, limit: 8192 },
        "[rules-pattern-too-long] a pattern is 9000 bytes, over the 8192-byte limit"
    )]
    #[case::parse_failed(
        RulesMessage::ParseFailed { reason: "line 3: bad key".to_owned() },
        "line 3: bad key"
    )]
    #[case::unsupported_format(
        RulesMessage::UnsupportedFormat,
        "unsupported file type (expected json, yaml, yml or toml)"
    )]
    #[case::duplicate_category(
        RulesMessage::DuplicateCategory { id: "voice".to_owned() },
        "duplicate category `voice`"
    )]
    #[case::duplicate_rule(
        RulesMessage::DuplicateRule { id: "passive".to_owned() },
        "duplicate rule id `passive` in its category"
    )]
    #[case::pattern_invalid(
        RulesMessage::PatternInvalid { reason: "missing )".to_owned() },
        "pattern does not compile: missing )"
    )]
    #[case::bad_example(
        RulesMessage::BadExampleNoMatch { index: 2, text: "\"x\"".to_owned() },
        "example 2 'bad' text does not match its own pattern: \"x\""
    )]
    #[case::good_example(
        RulesMessage::GoodExampleMatches { index: 0, text: "\"y\"".to_owned() },
        "example 0 'good' text matches the pattern, so the rule fires on its own fix: \"y\""
    )]
    #[case::match_failed(
        RulesMessage::MatchFailed { reason: "match limit".to_owned() },
        "matching failed: match limit"
    )]
    fn each_message_renders_its_published_text(
        #[case] message: RulesMessage,
        #[case] expected: &str,
    ) {
        assert_eq!(message.to_string(), expected);
    }

    #[test]
    fn the_catalog_registers_each_code_with_its_kind() {
        let entries: Vec<_> = message_entries().iter().map(|e| (e.code, e.kind)).collect();
        assert_eq!(
            entries,
            [
                ("rules-read-failed", Kind::Text),
                ("rules-file-too-large", Kind::Error),
                ("rules-budget-exceeded", Kind::Error),
                ("rules-pattern-too-long", Kind::Error),
                ("rules-parse-failed", Kind::Text),
                ("rules-unsupported-format", Kind::Text),
                ("rules-duplicate-category", Kind::Text),
                ("rules-duplicate-rule", Kind::Text),
                ("rules-pattern-invalid", Kind::Text),
                ("rules-example-bad-no-match", Kind::Text),
                ("rules-example-good-matches", Kind::Text),
                ("rules-match-failed", Kind::Text),
            ]
        );
    }
}
