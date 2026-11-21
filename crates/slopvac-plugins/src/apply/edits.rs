//! Applying fixer edits to one file.

use std::path::Path;

use crate::hooks::{FixEdit, MAX_EDITS_PER_DOCUMENT, MAX_INSERTED_BYTES};
use crate::messages::transport::{TransportPhrase, TransportText};

use super::fs::{Expect, locate, replace};
use super::{ApplyError, WriteOutcome};

/// What [`apply_edits`] did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditReport {
    /// Path as given.
    pub path: String,
    /// Number of edits in the set.
    pub edits: usize,
    /// Whether the file changed.
    pub outcome: WriteOutcome,
}

fn bad(msg: impl Into<String>) -> ApplyError {
    ApplyError::InvalidEdits(msg.into())
}

/// Apply `edits` to `source` in memory, following `docs/contract/positions.md`.
///
/// Spans use the original offsets. Edits sort by `(start, end)` and keep array
/// order for equal pairs, so zero-width edits at one offset apply in array
/// order. Edits that touch at one offset do not overlap. A zero-width edit
/// strictly inside another span does.
///
/// # Errors
/// [`ApplyError::InvalidEdits`] when the source is not UTF-8, a span is out of
/// range or splits a character, spans overlap, or a cap is exceeded. Nothing is
/// applied then.
pub fn edited_bytes(source: &[u8], edits: &[FixEdit]) -> Result<Vec<u8>, ApplyError> {
    if edits.len() > MAX_EDITS_PER_DOCUMENT {
        return Err(bad(TransportText::ApplyEditCount {
            count: edits.len(),
            limit: MAX_EDITS_PER_DOCUMENT,
        }
        .to_string()));
    }
    let inserted: usize = edits.iter().map(|e| e.text.len()).sum();
    if inserted > MAX_INSERTED_BYTES {
        return Err(bad(TransportText::ApplyInsertedSize {
            count: inserted,
            limit: MAX_INSERTED_BYTES,
        }
        .to_string()));
    }
    let text = std::str::from_utf8(source)
        .map_err(|_| bad(TransportPhrase::ApplySourceUtf8.as_static()))?;
    if edits.iter().any(|e| !e.span.fits(text)) {
        return Err(bad(TransportPhrase::ApplySpanCharacter.as_static()));
    }
    let splits_crlf = |at: u64| {
        usize::try_from(at)
            .ok()
            .filter(|&i| i > 0)
            .is_some_and(|i| source[i - 1] == b'\r' && source.get(i) == Some(&b'\n'))
    };
    if edits
        .iter()
        .any(|e| splits_crlf(e.span.start) || splits_crlf(e.span.end))
    {
        return Err(bad(TransportPhrase::ApplySpanCrlf.as_static()));
    }
    let mut order: Vec<&FixEdit> = edits.iter().collect();
    order.sort_by_key(|e| (e.span.start, e.span.end));
    for pair in order.windows(2) {
        if pair[0].span.end > pair[1].span.start {
            return Err(bad(TransportPhrase::ApplyOverlap.as_static()));
        }
    }
    let mut out = Vec::with_capacity(source.len() + inserted);
    let mut at = 0_usize;
    for e in order {
        // `fits` proved both offsets are in range for this text.
        let (Ok(start), Ok(end)) = (usize::try_from(e.span.start), usize::try_from(e.span.end))
        else {
            return Err(bad(TransportPhrase::ApplySpanRange.as_static()));
        };
        out.extend_from_slice(&source[at..start]);
        out.extend_from_slice(e.text.as_bytes());
        at = end;
    }
    out.extend_from_slice(&source[at..]);
    Ok(out)
}

/// Apply `edits` to the file at `path` under `root`.
///
/// `source` holds the bytes the edits were computed against. The file is
/// rewritten only while it still holds exactly those bytes (see the module
/// documentation for the checks). The edits are validated before the file system
/// is touched.
///
/// On Windows nothing is written: the call returns
/// [`ApplyError::UnsupportedOnWindows`] after the edits validate. Use
/// [`edited_bytes`] to preview the result there.
///
/// # Errors
/// [`ApplyError`] naming why the edits or the target were refused. The file is
/// whole and unchanged on every error.
pub fn apply_edits(
    root: &Path,
    path: &str,
    source: &[u8],
    edits: &[FixEdit],
) -> Result<EditReport, ApplyError> {
    apply_edits_on(root, path, source, edits, cfg!(windows))
}

/// Test seam for [`apply_edits`]: pretend to run on `windows` (or not). Not
/// part of the supported API.
#[doc(hidden)]
pub fn apply_edits_seam(
    root: &Path,
    path: &str,
    source: &[u8],
    edits: &[FixEdit],
    windows: bool,
) -> Result<EditReport, ApplyError> {
    apply_edits_on(root, path, source, edits, windows)
}

fn apply_edits_on(
    root: &Path,
    path: &str,
    source: &[u8],
    edits: &[FixEdit],
    windows: bool,
) -> Result<EditReport, ApplyError> {
    let new = edited_bytes(source, edits)?;
    if windows {
        return Err(ApplyError::UnsupportedOnWindows(path.to_owned()));
    }
    let at = locate(root, path, windows)?;
    let parent = at.open_parent()?;
    let outcome = replace(
        &parent,
        &at.name,
        path,
        &Expect::Bytes(source),
        &new,
        &mut |_| {},
    )?;
    Ok(EditReport {
        path: path.to_owned(),
        edits: edits.len(),
        outcome,
    })
}
