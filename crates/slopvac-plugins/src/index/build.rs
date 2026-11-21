//! Builds the index document from pack manifests.

use semver::Version;

use crate::messages::pyenv::PyenvText;

use super::model::{Index, IndexEntry, IndexError, MAX_INDEX_BYTES, PackKind, PublisherKey};

/// What the scheduled job learned about one pack: fields of its manifest plus
/// the source it found the pack at and the key that signs it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Listing {
    /// Pack id from the manifest.
    pub id: String,
    /// Publisher namespace the job found the pack under.
    pub namespace: String,
    /// Display name. The manifest has none, so `None` falls back to the id.
    pub name: Option<String>,
    /// Manifest description.
    pub description: String,
    /// Manifest version.
    pub version: Version,
    /// Manifest kind.
    pub kind: PackKind,
    /// Manifest `slopvac_api`.
    pub slopvac_api: u64,
    /// Where the pack can be fetched.
    pub source: String,
    /// The key that signs the pack, for display.
    pub publisher_key: PublisherKey,
}

impl From<Listing> for IndexEntry {
    fn from(l: Listing) -> Self {
        Self {
            name: l.name.unwrap_or_else(|| l.id.clone()),
            id: l.id,
            namespace: l.namespace,
            description: l.description,
            version: l.version,
            kind: l.kind,
            slopvac_api: l.slopvac_api,
            source: l.source,
            publisher_key: l.publisher_key,
        }
    }
}

/// Builds the index from listings in any order. The result is sorted by
/// namespace and id, so the same set of listings gives the same bytes from
/// [`Index::to_json`]. Fails on the first invalid listing or repeated
/// namespace and id pair; the error pointer is the listing's position. Also
/// fails when the canonical document would exceed [`MAX_INDEX_BYTES`], so every
/// index that this function returns is one that a reader accepts.
pub fn build_index(listings: impl IntoIterator<Item = Listing>) -> Result<Index, IndexError> {
    let index = Index::new(listings.into_iter().map(IndexEntry::from).collect())?;
    let size = index.to_json().len();
    if size > MAX_INDEX_BYTES {
        return Err(IndexError::new(
            "",
            PyenvText::IndexTooBigToBuild {
                size,
                limit: MAX_INDEX_BYTES,
            }
            .to_string(),
        ));
    }
    Ok(index)
}
