//! Rule definitions and rule loading.
//!
//! A pack ships category files (`json`, `yaml`, `yml` or `toml`) in the v3 shape that
//! `schemas/v3/category.schema.json` describes. [`RuleSet::load_dir`] reads them, compiles
//! every lexical rule with PCRE2 through `slopvac-text`, and checks each rule's examples.
//! The engine then iterates [`RuleSet::rules`], [`RuleSet::rules_of_kind`] or
//! [`RuleSet::rules_in_scope`] and calls [`LoadedRule::find_all`].
//!
//! The types in [`Rule`] and [`Category`] reject what the schemas reject. The JSON Schemas
//! the types generate come from [`rule_schema`], [`rule_file_schema`] and [`category_schema`].

mod error;
mod ext;
mod matcher;
mod messages;
mod model;
mod ruleset;
mod schema;

pub use error::{LoadError, LoadErrorKind, LoadErrors, PackBudget};
pub use ext::{UniqueVec, ValueError};
pub use matcher::{CompileError, CompileOptions, LexicalMatcher};
pub use messages::message_entries;
pub use model::*;
pub use ruleset::{
    LoadedCategory, LoadedRule, MAX_AUTHORED_PATTERN_BYTES, MAX_PACK_BYTES, MAX_PACK_ENTRIES,
    MAX_PACK_FILES, MAX_RULE_ENTRIES, MAX_RULE_FILE_BYTES, RuleSet,
};
pub use schema::{category_schema, rule_file_schema, rule_schema, schema_generator};
