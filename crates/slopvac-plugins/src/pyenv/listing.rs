//! The file listing of a managed environment and its two checks (Y4, Y5).
//!
//! The listing records every directory, file and symlink below the
//! environment root. The quick check reads directories and file metadata
//! only: the set of paths, kinds, sizes, modification times, executable bits
//! and link targets. The full check also hashes every file.

use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io;
use std::path::Path;
use std::time::UNIX_EPOCH;

use serde::{Deserialize, Serialize};
use sha2::{Digest as _, Sha256};

use super::PyEnvError;
use super::lock::hex;
use crate::messages::pyenv::{self as messages, PyenvPhrase, PyenvText};

/// Bounds on one environment (threat model section 5.5, Y7).
pub(super) const MAX_NODES: usize = 20_000;
pub(super) const MAX_DEPTH: usize = 32;
pub(super) const MAX_BYTES: u64 = 1 << 30;

/// The walk bounds in force: the constants above, or a test's smaller ones.
#[derive(Debug, Clone, Copy)]
pub(super) struct WalkBounds {
    pub nodes: usize,
    pub depth: usize,
    pub bytes: u64,
}

impl Default for WalkBounds {
    fn default() -> Self {
        Self {
            nodes: MAX_NODES,
            depth: MAX_DEPTH,
            bytes: MAX_BYTES,
        }
    }
}

/// What an entry is.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(super) enum Kind {
    Dir,
    File,
    Link,
}

/// One entry of the listing.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct Entry {
    /// Relative path with `/` separators.
    pub path: String,
    pub kind: Kind,
    /// File size in bytes; 0 for others.
    #[serde(default)]
    pub size: u64,
    /// Modification time as seconds and nanoseconds from the epoch; files only.
    #[serde(default)]
    pub mtime: Option<(i64, u32)>,
    /// Executable for the owner (Unix files only).
    #[serde(default)]
    pub exec: bool,
    /// Lowercase hex sha256 of a file.
    #[serde(default)]
    pub sha256: Option<String>,
    /// Target of a symlink, as stored.
    #[serde(default)]
    pub target: Option<String>,
}

/// The fields the quick check compares.
type QuickKey<'a> = (Kind, u64, Option<(i64, u32)>, bool, Option<&'a str>);

impl Entry {
    /// The fields the quick check compares.
    fn quick(&self) -> QuickKey<'_> {
        (
            self.kind,
            self.size,
            self.mtime,
            self.exec,
            self.target.as_deref(),
        )
    }
}

pub(super) fn mtime_of(meta: &fs::Metadata) -> io::Result<(i64, u32)> {
    let t = meta.modified()?;
    Ok(match t.duration_since(UNIX_EPOCH) {
        Ok(d) => (
            i64::try_from(d.as_secs()).unwrap_or(i64::MAX),
            d.subsec_nanos(),
        ),
        Err(e) => {
            let d = e.duration();
            let secs = i64::try_from(d.as_secs()).unwrap_or(i64::MAX);
            if d.subsec_nanos() == 0 {
                (-secs, 0)
            } else {
                (-secs - 1, 1_000_000_000 - d.subsec_nanos())
            }
        }
    })
}

#[cfg(unix)]
fn is_exec(meta: &fs::Metadata) -> bool {
    use std::os::unix::fs::PermissionsExt;
    meta.permissions().mode() & 0o100 != 0
}

#[cfg(not(unix))]
fn is_exec(_: &fs::Metadata) -> bool {
    false
}

/// The sha256 of a file and the bytes read, reading at most `max + 1` bytes.
pub(super) fn sha256_upto(path: &Path, max: u64) -> Result<(String, u64), PyEnvError> {
    let mut f = File::open(path).map_err(PyEnvError::io(messages::reading(path)))?;
    let mut h = Sha256::new();
    let n = io::copy(&mut io::Read::take(&mut f, max.saturating_add(1)), &mut h)
        .map_err(PyEnvError::io(messages::reading(path)))?;
    Ok((hex(&h.finalize()), n))
}

/// The sha256 of a whole file the walk bounds do not cover (an interpreter).
pub(super) fn sha256_file(path: &Path) -> Result<String, PyEnvError> {
    Ok(sha256_upto(path, u64::MAX - 1)?.0)
}

/// Walk `root` and list it, hashing file contents when `hash` is set.
///
/// Refuses special files, names that are not UTF-8 and trees past `bounds`:
/// more entries, more directory levels, or more file bytes in total.
pub(super) fn scan(root: &Path, hash: bool, bounds: WalkBounds) -> Result<Vec<Entry>, PyEnvError> {
    let meta = fs::symlink_metadata(root).map_err(PyEnvError::io(messages::inspecting(root)))?;
    if !meta.is_dir() {
        return Err(PyEnvError::Refused(
            PyenvText::NotDirectory {
                path: root.display().to_string(),
            }
            .to_string(),
        ));
    }
    let mut out = Vec::new();
    let mut total = 0u64;
    let mut stack = vec![(root.to_owned(), String::new(), 0usize)];
    while let Some((dir, prefix, depth)) = stack.pop() {
        let rd = fs::read_dir(&dir).map_err(PyEnvError::io(messages::reading(&dir)))?;
        for e in rd {
            let e = e.map_err(PyEnvError::io(messages::reading(&dir)))?;
            if out.len() >= bounds.nodes {
                return Err(PyEnvError::Refused(
                    PyenvText::TooManyEntries {
                        nodes: bounds.nodes,
                    }
                    .to_string(),
                ));
            }
            let name = e.file_name().into_string().map_err(|_| {
                PyEnvError::Refused(PyenvPhrase::FileNameNotUtf8.as_static().into())
            })?;
            let rel = if prefix.is_empty() {
                name
            } else {
                format!("{prefix}/{name}")
            };
            let path = e.path();
            let m =
                fs::symlink_metadata(&path).map_err(PyEnvError::io(messages::inspecting(&path)))?;
            let ft = m.file_type();
            let entry = if ft.is_symlink() {
                link_entry(&path, rel)?
            } else if ft.is_dir() {
                if depth + 1 >= bounds.depth {
                    return Err(PyEnvError::Refused(
                        PyenvText::TooDeep {
                            depth: bounds.depth,
                        }
                        .to_string(),
                    ));
                }
                stack.push((path, rel.clone(), depth + 1));
                Entry {
                    path: rel,
                    kind: Kind::Dir,
                    size: 0,
                    mtime: None,
                    exec: false,
                    sha256: None,
                    target: None,
                }
            } else if ft.is_file() {
                total = total.saturating_add(m.len());
                if total > bounds.bytes {
                    return Err(PyEnvError::Refused(
                        PyenvText::TooManyBytes {
                            bytes: bounds.bytes,
                        }
                        .to_string(),
                    ));
                }
                file_entry(&path, rel, &m, hash)?
            } else {
                return Err(PyEnvError::Refused(
                    PyenvText::SpecialFile { rel }.to_string(),
                ));
            };
            out.push(entry);
        }
    }
    out.sort_by(|a, b| a.path.as_bytes().cmp(b.path.as_bytes()));
    Ok(out)
}

fn link_entry(path: &Path, rel: String) -> Result<Entry, PyEnvError> {
    let t = fs::read_link(path).map_err(PyEnvError::io(messages::reading_link(path)))?;
    let t = t.into_os_string().into_string().map_err(|_| {
        PyEnvError::Refused(PyenvText::LinkTargetNotUtf8 { rel: rel.clone() }.to_string())
    })?;
    Ok(Entry {
        path: rel,
        kind: Kind::Link,
        size: 0,
        mtime: None,
        exec: false,
        sha256: None,
        target: Some(t),
    })
}

fn file_entry(path: &Path, rel: String, m: &fs::Metadata, hash: bool) -> Result<Entry, PyEnvError> {
    let sha = if hash {
        let (sha, n) = sha256_upto(path, m.len())?;
        if n != m.len() {
            return Err(PyEnvError::Changed {
                path: rel,
                why: PyenvPhrase::ChangedWhileRead.as_static().into(),
            });
        }
        Some(sha)
    } else {
        None
    };
    Ok(Entry {
        size: m.len(),
        mtime: Some(mtime_of(m).map_err(PyEnvError::io(messages::inspecting(path)))?),
        exec: is_exec(m),
        sha256: sha,
        target: None,
        kind: Kind::File,
        path: rel,
    })
}

/// Compare a fresh scan with the recorded listing. `full` also compares content hashes.
pub(super) fn compare(recorded: &[Entry], now: &[Entry], full: bool) -> Result<(), PyEnvError> {
    let old: BTreeMap<&str, &Entry> = recorded.iter().map(|e| (e.path.as_str(), e)).collect();
    let new: BTreeMap<&str, &Entry> = now.iter().map(|e| (e.path.as_str(), e)).collect();
    for (p, n) in &new {
        let Some(o) = old.get(p) else {
            return Err(PyEnvError::Changed {
                path: (*p).to_owned(),
                why: PyenvPhrase::AddedAfterBuild.as_static().into(),
            });
        };
        if o.quick() != n.quick() {
            return Err(PyEnvError::Changed {
                path: (*p).to_owned(),
                why: PyenvPhrase::EntryChanged.as_static().into(),
            });
        }
        if full && o.sha256 != n.sha256 {
            return Err(PyEnvError::Changed {
                path: (*p).to_owned(),
                why: PyenvPhrase::ContentChanged.as_static().into(),
            });
        }
    }
    if let Some(p) = old.keys().find(|p| !new.contains_key(*p)) {
        return Err(PyEnvError::Changed {
            path: (*p).to_owned(),
            why: PyenvPhrase::RemovedAfterBuild.as_static().into(),
        });
    }
    Ok(())
}

/// The listing as it goes into the trust hash: content, never times.
pub(super) fn digest_input(entries: &[Entry]) -> serde_json::Value {
    serde_json::Value::Array(
        entries
            .iter()
            .map(|e| serde_json::json!([e.path, e.kind, e.size, e.exec, e.sha256, e.target,]))
            .collect(),
    )
}

/// Make the listed entries below `root` read-only. `root` itself is left for
/// the caller. The listing comes from [`scan`], so the walk bounds apply.
pub(super) fn make_read_only(root: &Path, entries: &[Entry]) -> Result<(), PyEnvError> {
    for e in entries.iter().filter(|e| e.kind == Kind::File) {
        set_read_only(&root.join(&e.path), false)?;
    }
    // Directories last, deepest first (reverse path order puts `a/b` before
    // `a`), so their contents stay reachable.
    for e in entries.iter().rev().filter(|e| e.kind == Kind::Dir) {
        set_read_only(&root.join(&e.path), true)?;
    }
    Ok(())
}

#[cfg(unix)]
pub(super) fn set_read_only(path: &Path, dir: bool) -> Result<(), PyEnvError> {
    use std::os::unix::fs::PermissionsExt;
    let meta = fs::symlink_metadata(path)
        .map_err(PyEnvError::io(PyenvPhrase::InspectingEntry.as_static()))?;
    let mode = if dir || meta.permissions().mode() & 0o100 != 0 {
        0o555
    } else {
        0o444
    };
    fs::set_permissions(path, fs::Permissions::from_mode(mode))
        .map_err(PyEnvError::io(messages::protecting(path)))
}

#[cfg(not(unix))]
pub(super) fn set_read_only(path: &Path, dir: bool) -> Result<(), PyEnvError> {
    if dir {
        return Ok(());
    }
    let mut p = fs::metadata(path)
        .map_err(PyEnvError::io(PyenvPhrase::InspectingEntry.as_static()))?
        .permissions();
    p.set_readonly(true);
    fs::set_permissions(path, p).map_err(PyEnvError::io(messages::protecting(path)))
}
