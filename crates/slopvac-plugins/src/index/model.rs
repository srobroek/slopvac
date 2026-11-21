//! The index document: typed model, strict parser and canonical writer.
//!
//! The shape is `schemas/v3/plugin-index.schema.json`; the semantics are in
//! `docs/contract/plugin-index.md`.

use std::collections::HashSet;
use std::fmt;

use semver::Version;
use serde::Serialize;

use crate::messages::pyenv::{self as messages, PyenvPhrase, PyenvText};

/// Largest index document the reader accepts, in bytes. Checked before parsing
/// (threat model N11).
pub const MAX_INDEX_BYTES: usize = 32 * 1024 * 1024;
/// Most entries in one index.
pub const MAX_ENTRIES: usize = 100_000;
/// Longest pack id or namespace, in characters.
pub const MAX_ID_CHARS: usize = 64;
/// Longest display name, in characters.
pub const MAX_NAME_CHARS: usize = 128;
/// Longest description, in characters.
pub const MAX_DESCRIPTION_CHARS: usize = 1024;
/// Longest source, in characters.
pub const MAX_SOURCE_CHARS: usize = 2048;
/// Largest `slopvac_api`.
pub const MAX_API: u64 = u32::MAX as u64;
/// Largest major, minor or patch number in a version (nine digits).
pub const MAX_VERSION_NUMBER: u64 = 999_999_999;

/// A rejected index document or entry. `pointer` is a JSON Pointer into the
/// document (for example `/plugins/0/source`); it is empty for the whole document.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error("{}", messages::index_error(.pointer, .message))]
pub struct IndexError {
    /// JSON Pointer to the offending value.
    pub pointer: String,
    /// What is wrong. Unsafe characters from the document are escaped.
    pub message: String,
}

impl IndexError {
    pub(super) fn new(pointer: impl Into<String>, message: impl AsRef<str>) -> Self {
        Self {
            pointer: pointer.into(),
            message: slopvac_sanitize::line(message.as_ref()),
        }
    }
}

/// What a plugin is: a data plugin, or a code plugin that also runs a command.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum PackKind {
    /// A data plugin: rules, styles, genres, terms and taggers. No code.
    Data,
    /// A code plugin: adds a command for the host to run as a subprocess.
    Code,
}

impl PackKind {
    /// The spelling in the document.
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Data => "data",
            Self::Code => "code",
        }
    }
}

/// The key a publisher claims to sign with, as the index lists it.
///
/// **Display only** (threat model section 5.2). This type has no conversion
/// to a verification key or to a key policy, and none may be added: a key
/// becomes trusted only through the explicit pinning command, never through
/// the index.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublisherKey {
    /// Minisign key id: 16 uppercase hex digits.
    pub key_id: String,
    /// SHA-256 of the raw public key bytes: 64 lowercase hex digits.
    pub fingerprint: String,
}

impl fmt::Display for PublisherKey {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // ast-grep-ignore: user-text-literal
        write!(f, "{} (fingerprint {})", self.key_id, self.fingerprint)
    }
}

/// One listed pack.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndexEntry {
    /// Pack id.
    pub id: String,
    /// Publisher namespace.
    pub namespace: String,
    /// Display name.
    pub name: String,
    /// One-line summary. Untrusted text: print it through
    /// [`slopvac_sanitize::line`].
    pub description: String,
    /// Latest listed version, without build metadata.
    pub version: Version,
    /// Data or plugin.
    pub kind: PackKind,
    /// Lowest extension API the host must implement.
    pub slopvac_api: u64,
    /// `oci://`, `https://` or pinned `git+https://` source.
    pub source: String,
    /// The publisher's claimed key. Display only.
    pub publisher_key: PublisherKey,
}

/// A validated index: entries sorted by namespace and id, with no pair repeated.
///
/// Canonical by construction, so `Index::parse(&index.to_json()) == Ok(index)`.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct Index {
    packs: Vec<IndexEntry>,
}

fn is_id(s: &str) -> bool {
    let mut chars = s.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

fn is_hex(s: &str, len: usize, upper: bool) -> bool {
    s.len() == len
        && s.bytes().all(|b| {
            b.is_ascii_digit()
                || if upper {
                    (b'A'..=b'F').contains(&b)
                } else {
                    (b'a'..=b'f').contains(&b)
                }
        })
}

/// True when the text after `scheme://` has a non-empty authority without
/// user-info and no whitespace anywhere.
fn is_url_rest(rest: &str) -> bool {
    let authority_end = rest.find(['/', '?', '#']).unwrap_or(rest.len());
    let authority = &rest[..authority_end];
    !authority.is_empty() && !authority.contains('@') && !rest.chars().any(char::is_whitespace)
}

// NOTE: the same source forms as the lock reader (packs/9.3 lock/model.rs),
// minus path sources. Fold the two into one type when that module is on main.
fn is_source(s: &str) -> bool {
    if let Some(rest) = s
        .strip_prefix("oci://")
        .or_else(|| s.strip_prefix("https://"))
    {
        return is_url_rest(rest);
    }
    s.strip_prefix("git+https://")
        .and_then(|rest| rest.rsplit_once('@'))
        .is_some_and(|(url, commit)| is_url_rest(url) && is_hex(commit, 40, false))
}

fn check_len(value: &str, min: usize, max: usize, at: &str, what: &str) -> Result<(), IndexError> {
    let n = value.chars().count();
    if (min..=max).contains(&n) {
        Ok(())
    } else {
        Err(IndexError::new(
            at,
            PyenvText::LengthBetween {
                what: what.to_owned(),
                min,
                max,
                n,
            }
            .to_string(),
        ))
    }
}

impl IndexEntry {
    fn validate(&self, at: &str) -> Result<(), IndexError> {
        let p = |key: &str| format!("{at}/{key}");
        for (key, value) in [("id", &self.id), ("namespace", &self.namespace)] {
            check_len(value, 1, MAX_ID_CHARS, &p(key), key)?;
            if !is_id(value) {
                return Err(IndexError::new(
                    p(key),
                    PyenvText::IdInvalid {
                        value: value.clone(),
                        key: key.to_owned(),
                    }
                    .to_string(),
                ));
            }
            if value == crate::sign::RESERVED_ID {
                return Err(IndexError::new(
                    p(key),
                    PyenvText::IdReserved {
                        value: value.clone(),
                    }
                    .to_string(),
                ));
            }
        }
        check_len(&self.name, 1, MAX_NAME_CHARS, &p("name"), "name")?;
        check_len(
            &self.description,
            1,
            MAX_DESCRIPTION_CHARS,
            &p("description"),
            "description",
        )?;
        if !self.version.build.is_empty() {
            return Err(IndexError::new(
                p("version"),
                PyenvPhrase::BuildMetadata.as_static(),
            ));
        }
        let v = &self.version;
        if [v.major, v.minor, v.patch]
            .iter()
            .any(|&n| n > MAX_VERSION_NUMBER)
        {
            return Err(IndexError::new(
                p("version"),
                PyenvText::VersionNumberTooLarge {
                    max: MAX_VERSION_NUMBER,
                }
                .to_string(),
            ));
        }
        if !(1..=MAX_API).contains(&self.slopvac_api) {
            return Err(IndexError::new(
                p("slopvac_api"),
                PyenvText::ApiOutOfRange { max: MAX_API }.to_string(),
            ));
        }
        check_len(&self.source, 1, MAX_SOURCE_CHARS, &p("source"), "source")?;
        // The raw value is not echoed: it may carry credentials (CWE-532).
        if !is_source(&self.source) {
            return Err(IndexError::new(
                p("source"),
                PyenvPhrase::SourceInvalid.as_static(),
            ));
        }
        if !is_hex(&self.publisher_key.key_id, 16, true) {
            return Err(IndexError::new(
                p("publisher_key/key_id"),
                PyenvPhrase::KeyIdInvalid.as_static(),
            ));
        }
        if !is_hex(&self.publisher_key.fingerprint, 64, false) {
            return Err(IndexError::new(
                p("publisher_key/fingerprint"),
                PyenvPhrase::FingerprintInvalid.as_static(),
            ));
        }
        Ok(())
    }
}

impl Index {
    /// Validates every entry, rejects a repeated namespace and id pair, and
    /// sorts by namespace and then id. Error pointers use the positions in
    /// `packs` as given.
    pub fn new(mut packs: Vec<IndexEntry>) -> Result<Self, IndexError> {
        if packs.len() > MAX_ENTRIES {
            return Err(IndexError::new(
                "/plugins",
                PyenvText::TooManyIndexEntries { max: MAX_ENTRIES }.to_string(),
            ));
        }
        let mut seen = HashSet::with_capacity(packs.len());
        for (i, entry) in packs.iter().enumerate() {
            entry.validate(&format!("/plugins/{i}"))?;
            if !seen.insert((&entry.namespace, &entry.id)) {
                return Err(IndexError::new(
                    format!("/plugins/{i}/id"),
                    PyenvText::ListedTwice {
                        namespace: entry.namespace.clone(),
                        id: entry.id.clone(),
                    }
                    .to_string(),
                ));
            }
        }
        packs.sort_by(|a, b| (&a.namespace, &a.id).cmp(&(&b.namespace, &b.id)));
        Ok(Self { packs })
    }

    /// The entries, sorted by namespace and id.
    #[must_use]
    pub fn entries(&self) -> &[IndexEntry] {
        &self.packs
    }

    /// Parses an index document. The size limit is checked before any
    /// parsing, and the reader streams: it never builds a tree of the document.
    /// Unknown keys and repeated keys are errors, and `x-` keys are ignored.
    pub fn parse(bytes: &[u8]) -> Result<Self, IndexError> {
        Self::new(super::read::read(bytes)?)
    }

    /// Writes the canonical document: fixed key order, two-space indent, a
    /// final newline. The same index always gives the same bytes.
    #[must_use]
    pub fn to_json(&self) -> String {
        let out = IndexOut {
            schema_version: 3,
            plugins: self.packs.iter().map(EntryOut::from).collect(),
        };
        let mut text = serde_json::to_string_pretty(&out).unwrap_or_default();
        text.push('\n');
        text
    }
}

#[derive(Serialize)]
struct IndexOut<'a> {
    schema_version: u8,
    plugins: Vec<EntryOut<'a>>,
}

#[derive(Serialize)]
struct EntryOut<'a> {
    id: &'a str,
    namespace: &'a str,
    name: &'a str,
    description: &'a str,
    version: String,
    kind: &'static str,
    slopvac_api: u64,
    source: &'a str,
    publisher_key: KeyOut<'a>,
}

#[derive(Serialize)]
struct KeyOut<'a> {
    key_id: &'a str,
    fingerprint: &'a str,
}

impl<'a> From<&'a IndexEntry> for EntryOut<'a> {
    fn from(e: &'a IndexEntry) -> Self {
        Self {
            id: &e.id,
            namespace: &e.namespace,
            name: &e.name,
            description: &e.description,
            version: e.version.to_string(),
            kind: e.kind.as_str(),
            slopvac_api: e.slopvac_api,
            source: &e.source,
            publisher_key: KeyOut {
                key_id: &e.publisher_key.key_id,
                fingerprint: &e.publisher_key.fingerprint,
            },
        }
    }
}
