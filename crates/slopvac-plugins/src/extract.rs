//! Safe extraction of `.tar.gz` artifacts into a content-addressed store
//! (threat model section 6.5, E1 to E9).
//!
//! The extractor never calls `Archive::unpack`. It walks entries itself and
//! accepts only regular files and directories. It ignores modes and owners,
//! refuses any path that is not a plain relative name, stops at hard limits
//! while streaming, writes into a private staging directory with exclusive
//! creation, hashes the tree, and renames it atomically into the store.

use std::collections::{HashMap, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, SystemTime};

use flate2::read::MultiGzDecoder;
use sha2::{Digest as _, Sha256};
use slopvac_sanitize::line as esc;
use unicode_normalization::UnicodeNormalization;

use crate::hooks::check_relative_path;
use crate::messages::transport::{TransportPhrase, TransportText};

/// Limits from the threat model, section 5.5.
#[derive(Debug, Clone, Copy)]
pub struct Limits {
    /// Compressed layer size.
    pub compressed_bytes: u64,
    /// Expanded size of one artifact.
    pub expanded_bytes: u64,
    /// Largest expanded-to-compressed ratio, checked once 1 MiB has expanded.
    pub max_ratio: u64,
    /// Entries in one archive.
    pub entries: usize,
    /// Files, directories (implicit parents included) and the executable list in
    /// one tree. Values above the verification ceiling of 20 000 are clamped to
    /// it, so every extracted tree also verifies.
    pub nodes: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            compressed_bytes: 64 << 20,
            expanded_bytes: 256 << 20,
            max_ratio: 100,
            entries: 10_000,
            nodes: MAX_TREE_NODES,
        }
    }
}

/// Name of the sidecar that records which files are executable. It sits at the
/// tree root and is hashed like any other file, so the executable set is part of
/// the tree hash on every platform instead of depending on file system modes.
const EXEC_SIDECAR: &str = ".slopvac-exec";
/// Largest GNU long name or PAX header block the extractor reads into memory.
const MAX_META_BYTES: u64 = 64 * 1024;
/// Ceiling on nodes (files, directories and the sidecar) in a stored tree.
/// Extraction and verification charge the same [`NodeBudget`], and extraction
/// clamps its limit to this ceiling, so a tree that extracts also verifies.
const MAX_TREE_NODES: usize = 20_000;
/// Deepest directory nesting verification accepts (path segments).
const MAX_TREE_DEPTH: usize = 32;
/// Most bytes tree verification hashes.
const MAX_TREE_BYTES: u64 = 256 << 20;
/// Longest sidecar line: a path of at most 1024 bytes plus its newline.
const MAX_SIDECAR_LINE: u64 = 1025;

/// Counts the nodes a tree occupies on disk: every file, every directory that
/// holds something (including implicit parents of nested files) and the sidecar.
#[derive(Debug)]
struct NodeBudget {
    used: usize,
    limit: usize,
}

impl NodeBudget {
    fn new(limit: usize) -> Self {
        Self {
            used: 0,
            limit: limit.min(MAX_TREE_NODES),
        }
    }

    fn charge(&mut self, n: usize) -> Result<(), ExtractError> {
        self.used = self.used.saturating_add(n);
        if self.used > self.limit {
            return Err(refused(
                TransportText::ExtractNodes { limit: self.limit }.to_string(),
            ));
        }
        Ok(())
    }
}

/// The ancestors of `rel` (`a`, `a/b`, ...) that are not in `dirs` yet.
fn new_parents(dirs: &HashSet<String>, rel: &str) -> Vec<String> {
    rel.match_indices('/')
        .map(|(i, _)| &rel[..i])
        .filter(|d| !dirs.contains(*d))
        .map(str::to_owned)
        .collect()
}

/// Why an artifact was refused. Any error leaves the store unchanged.
///
/// The variants hold raw text. `Display` escapes it with `slopvac-sanitize`;
/// [`ExtractError::unescaped`] gives the text before that, for a caller that
/// builds a larger message and escapes it once.
#[derive(Debug)]
pub enum ExtractError {
    /// The archive breaks a rule.
    Refused(String),
    /// The archive is not valid gzip or tar.
    Malformed(String),
    /// A cached tree differs from its recorded hash.
    Tampered {
        /// The tree.
        path: PathBuf,
    },
    /// A file system operation failed.
    Io {
        /// The operation.
        what: String,
        /// The cause.
        source: io::Error,
    },
}

impl ExtractError {
    /// The message as built, before escaping. Do not print it.
    #[must_use]
    pub fn unescaped(&self) -> String {
        match self {
            Self::Refused(m) => TransportText::ExtractRefused { detail: m.clone() }.to_string(),
            Self::Malformed(m) => TransportText::ExtractMalformed { detail: m.clone() }.to_string(),
            Self::Tampered { path } => TransportText::ExtractTampered {
                path: path.to_string_lossy().into_owned(),
            }
            .to_string(),
            Self::Io { what, source } => TransportText::ExtractIo {
                what: what.clone(),
                detail: source.to_string(),
            }
            .to_string(),
        }
    }
}

impl std::fmt::Display for ExtractError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&esc(&self.unescaped()))
    }
}

impl std::error::Error for ExtractError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            _ => None,
        }
    }
}

fn refused(msg: impl Into<String>) -> ExtractError {
    ExtractError::Refused(msg.into())
}

fn io_err(what: impl Into<String>) -> impl FnOnce(io::Error) -> ExtractError {
    let what = what.into();
    move |source| ExtractError::Io { what, source }
}

/// `sha256:<hex>` over the file records of a tree.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct TreeHash(String);

impl TreeHash {
    /// Parse a `sha256:<64 lowercase hex>` string, for example from a lockfile.
    ///
    /// # Errors
    /// [`ExtractError::Refused`] when the string has another form.
    pub fn parse(s: &str) -> Result<Self, ExtractError> {
        let ok = s.strip_prefix("sha256:").is_some_and(|h| {
            h.len() == 64 && h.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
        });
        if ok {
            Ok(Self(s.to_owned()))
        } else {
            Err(refused(
                TransportText::ExtractTreeHash { hash: s.to_owned() }.to_string(),
            ))
        }
    }

    /// The `sha256:...` string.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Only the hex part.
    #[must_use]
    pub fn hex(&self) -> &str {
        &self.0[7..]
    }

    /// Parse the 64 lowercase hex digits of a hash, for example read back from a record.
    #[must_use]
    pub fn from_hex(hex: &str) -> Option<Self> {
        (hex.len() == 64 && hex.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')))
            .then(|| Self(format!("sha256:{hex}")))
    }
}

impl std::fmt::Display for TreeHash {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

fn hex(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push(char::from(b"0123456789abcdef"[usize::from(b >> 4)]));
        s.push(char::from(b"0123456789abcdef"[usize::from(b & 15)]));
    }
    s
}

/// One extracted file: relative path, executable flag, content digest and size.
struct FileRecord {
    path: String,
    executable: bool,
    sha: [u8; 32],
    len: u64,
}

fn tree_hash_of(mut files: Vec<FileRecord>) -> TreeHash {
    files.sort_by(|a, b| a.path.as_bytes().cmp(b.path.as_bytes()));
    let mut h = Sha256::new();
    for f in files {
        h.update(b"F\0");
        h.update(f.path.as_bytes());
        h.update(b"\0");
        h.update([u8::from(f.executable)]);
        h.update(f.len.to_be_bytes());
        h.update(f.sha);
    }
    TreeHash(format!("sha256:{}", hex(&h.finalize())))
}

/// The result of a successful extraction.
#[derive(Debug, Clone)]
pub struct Extracted {
    /// Final directory inside the store.
    pub root: PathBuf,
    /// Hash of the tree.
    pub hash: TreeHash,
    /// Files written.
    pub files: usize,
    /// Expanded bytes.
    pub bytes: u64,
    /// Where a cached tree that failed verification and was too large to delete
    /// was moved. It still occupies storage until the operator removes it.
    pub quarantined: Option<PathBuf>,
}

/// What [`evict`] did with a tree.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Evicted {
    /// The tree is gone.
    Removed,
    /// The tree was past the walk bounds and was renamed, whole, to this path.
    /// It keeps using storage until the operator deletes it.
    Quarantined(PathBuf),
}

/// What [`clean_staging`] did.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct StagingReport {
    /// Stale staging directories deleted.
    pub removed: usize,
    /// Stale staging directories renamed aside instead of deleted, with their
    /// new paths, for callers to report as retained storage.
    pub quarantined: Vec<PathBuf>,
}

struct Counting<R> {
    inner: R,
    seen: Arc<AtomicU64>,
    limit: u64,
}

impl<R: Read> Read for Counting<R> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let n = self.inner.read(buf)?;
        let total = self.seen.fetch_add(n as u64, Ordering::SeqCst) + n as u64;
        if total > self.limit {
            return Err(io::Error::other(
                TransportText::ExtractCompressedSize { limit: self.limit }.to_string(),
            ));
        }
        Ok(n)
    }
}

/// Guards the expanded size and ratio while the tar reader pulls bytes.
struct Guarded<R> {
    inner: R,
    expanded: u64,
    compressed: Arc<AtomicU64>,
    limits: Limits,
}

impl<R: Read> Read for Guarded<R> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let n = self.inner.read(buf)?;
        self.expanded += n as u64;
        if self.expanded > self.limits.expanded_bytes {
            return Err(io::Error::other(
                TransportText::ExtractExpandedSize {
                    limit: self.limits.expanded_bytes,
                }
                .to_string(),
            ));
        }
        let comp = self.compressed.load(Ordering::SeqCst).max(1);
        if self.expanded > (1 << 20) && self.expanded / comp > self.limits.max_ratio {
            return Err(io::Error::other(
                TransportText::ExtractRatio {
                    limit: self.limits.max_ratio,
                }
                .to_string(),
            ));
        }
        Ok(n)
    }
}

fn normalise_entry_path(raw: &[u8]) -> Result<String, ExtractError> {
    let s = std::str::from_utf8(raw)
        .map_err(|_| refused(TransportPhrase::ExtractPathUtf8.as_static()))?;
    let s = s.strip_prefix("./").unwrap_or(s);
    let s = s.strip_suffix('/').unwrap_or(s);
    check_name(s).map_err(|e| {
        refused(
            TransportText::ExtractEntryPath {
                path: s.to_owned(),
                detail: e,
            }
            .to_string(),
        )
    })?;
    Ok(s.to_owned())
}

/// `dir` without a trailing separator or `.` component. Either spelling would
/// make `lstat` follow a root symlink; `components()` drops both. Every public
/// function that inspects a caller-supplied root uses this once, then works on
/// the result only.
fn normalised(dir: &Path) -> PathBuf {
    dir.components().collect()
}

/// The one name rule for extraction and verification. A colon would open an NTFS
/// alternate data stream that directory listing hides.
fn check_name(s: &str) -> Result<(), String> {
    check_relative_path(s)?;
    if s.contains(':') {
        return Err(TransportPhrase::ExtractPathColon.as_static().into());
    }
    Ok(())
}

/// Claim `path` in the namespace. A directory may repeat with the same spelling;
/// anything else that folds to the same key is a collision.
fn claim(
    names: &mut HashMap<String, (String, bool)>,
    path: &str,
    is_dir: bool,
) -> Result<(), ExtractError> {
    let keys = collision_keys(path);
    for key in &keys {
        match names.get(key) {
            None => {}
            Some((orig, true)) if is_dir && orig == path => {}
            Some((orig, _)) => {
                return Err(refused(
                    TransportText::ExtractCollision {
                        path: path.to_owned(),
                        existing: orig.clone(),
                    }
                    .to_string(),
                ));
            }
        }
    }
    for key in keys {
        names
            .entry(key)
            .or_insert_with(|| (path.to_owned(), is_dir));
    }
    Ok(())
}

/// Every parent is a directory; a path may be claimed once, by one spelling.
fn claim_with_parents(
    names: &mut HashMap<String, (String, bool)>,
    rel: &str,
    is_dir: bool,
) -> Result<(), ExtractError> {
    let parts: Vec<&str> = rel.split('/').collect();
    let mut parent = String::new();
    for seg in &parts[..parts.len() - 1] {
        if !parent.is_empty() {
            parent.push('/');
        }
        parent.push_str(seg);
        claim(names, &parent, true)?;
    }
    claim(names, rel, is_dir)
}

/// Keys under which two names count as the same file. Names collide when any
/// key matches; the prefixes keep the two key spaces apart.
///
/// The canonical key is the caseless match of Unicode 3.13 (D145):
/// `NFD(toCasefold(NFD(x)))`. The case fold is the full, table-backed
/// `CaseFolding.txt` fold from the `caseless` crate, so `ς` and `Σ` meet at `σ`
/// and both `ß` and `ẞ` become `ss`, with none of the context rules of
/// `str::to_lowercase`.
///
/// That fold is not a superset of file system equivalence. NTFS compares names
/// by an uppercase table, which merges `I` with the dotless `ı` (U+0131) where
/// default folding keeps them apart. The second key models it: NFC, then simple
/// per-character uppercasing, keeping a character whose uppercase is more than
/// one character. The keys can merge more names than a given file system does,
/// which only refuses more archives; pack paths are not limited to ASCII, so
/// refusing non-ASCII names was not an option.
fn collision_keys(path: &str) -> [String; 2] {
    let decomposed: String = path.nfd().collect();
    let canonical: String = caseless::default_case_fold_str(&decomposed).nfd().collect();
    let upper: String = path
        .nfc()
        .map(|c| {
            let mut up = c.to_uppercase();
            match (up.next(), up.next()) {
                (Some(u), None) => u,
                _ => c,
            }
        })
        .collect();
    [format!("c:{canonical}"), format!("n:{upper}")]
}

#[cfg(unix)]
fn create_file(path: &Path, executable: bool) -> io::Result<File> {
    use std::os::unix::fs::OpenOptionsExt;
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(if executable { 0o755 } else { 0o644 })
        .open(path)
}

#[cfg(not(unix))]
fn create_file(path: &Path, _executable: bool) -> io::Result<File> {
    OpenOptions::new().write(true).create_new(true).open(path)
}

#[cfg(unix)]
fn set_mode(path: &Path, mode: u32) -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(mode))
}

#[cfg(not(unix))]
fn set_mode(path: &Path, mode: u32) -> io::Result<()> {
    let mut perms = fs::metadata(path)?.permissions();
    perms.set_readonly(mode & 0o222 == 0);
    fs::set_permissions(path, perms)
}

/// Create the store and restrict it to the owner. The caller chose this path, so
/// a link at the store root itself is followed.
///
/// On Unix this sets mode 0700. On Windows it only clears the read-only
/// attribute: no ACL is written, because that needs either `unsafe` Win32 calls
/// or a new dependency. The directory therefore keeps the ACL it inherits from
/// its parent, and the store must live under a per-user location such as
/// `%LOCALAPPDATA%`. This is a documented residual risk (CWE-732).
pub(crate) fn ensure_private_dir(path: &Path) -> Result<(), ExtractError> {
    fs::create_dir_all(path).map_err(io_err(
        TransportText::ExtractCreating {
            path: path.display().to_string(),
        }
        .to_string(),
    ))?;
    set_mode(path, 0o700).map_err(io_err(
        TransportText::ExtractSecuring {
            path: path.display().to_string(),
        }
        .to_string(),
    ))
}

/// Create or reuse a directory the store owns (`.staging`) and restrict it to the
/// owner. A link, a non-directory, or on Unix a directory owned by someone else
/// is refused before any permission change, so a planted link cannot redirect
/// the chmod (CWE-59).
pub(crate) fn ensure_private_child(path: &Path) -> Result<(), ExtractError> {
    match fs::create_dir(path) {
        Ok(()) => {}
        Err(e) if e.kind() == io::ErrorKind::AlreadyExists => {}
        Err(e) => {
            return Err(io_err(
                TransportText::ExtractCreating {
                    path: path.display().to_string(),
                }
                .to_string(),
            )(e));
        }
    }
    let meta = inspect_private_child(path)?.ok_or_else(|| {
        refused(
            TransportText::ExtractVanished {
                path: path.display().to_string(),
            }
            .to_string(),
        )
    })?;
    secure_checked(path, &meta)
}

#[cfg(unix)]
fn check_owner(path: &Path, meta: &fs::Metadata) -> Result<(), ExtractError> {
    use std::os::unix::fs::MetadataExt;
    if meta.uid() != rustix::process::getuid().as_raw() {
        return Err(refused(
            TransportText::ExtractOwner {
                path: path.display().to_string(),
            }
            .to_string(),
        ));
    }
    Ok(())
}

#[cfg(not(unix))]
#[allow(clippy::unnecessary_wraps)]
fn check_owner(_: &Path, _: &fs::Metadata) -> Result<(), ExtractError> {
    Ok(())
}

/// Inspect a directory the store owns without following links or changing it:
/// `None` when absent, a refusal for a link, a non-directory, or (Unix) a
/// directory owned by someone else.
fn inspect_private_child(path: &Path) -> Result<Option<fs::Metadata>, ExtractError> {
    let meta = match fs::symlink_metadata(path) {
        Ok(m) => m,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(e) => {
            return Err(io_err(
                TransportText::ExtractInspecting {
                    path: path.display().to_string(),
                }
                .to_string(),
            )(e));
        }
    };
    if !meta.is_dir() {
        return Err(refused(
            TransportText::ExtractDirectory {
                path: path.display().to_string(),
            }
            .to_string(),
        ));
    }
    check_owner(path, &meta)?;
    Ok(Some(meta))
}

#[cfg(unix)]
fn secure_checked(path: &Path, meta: &fs::Metadata) -> Result<(), ExtractError> {
    use std::os::unix::fs::{MetadataExt, PermissionsExt};
    check_owner(path, meta)?;
    // chmod through a handle, and make sure the handle is the directory that was
    // inspected, so a swap between the check and the open changes nothing.
    let dir = File::open(path).map_err(io_err(
        TransportText::ExtractOpening {
            path: path.display().to_string(),
        }
        .to_string(),
    ))?;
    let opened = dir.metadata().map_err(io_err(
        TransportText::ExtractInspecting {
            path: path.display().to_string(),
        }
        .to_string(),
    ))?;
    if (opened.dev(), opened.ino()) != (meta.dev(), meta.ino()) {
        return Err(refused(
            TransportText::ExtractChanged {
                path: path.display().to_string(),
            }
            .to_string(),
        ));
    }
    dir.set_permissions(fs::Permissions::from_mode(0o700))
        .map_err(io_err(
            TransportText::ExtractSecuring {
                path: path.display().to_string(),
            }
            .to_string(),
        ))
}

#[cfg(not(unix))]
fn secure_checked(path: &Path, _: &fs::Metadata) -> Result<(), ExtractError> {
    set_mode(path, 0o700).map_err(io_err(
        TransportText::ExtractSecuring {
            path: path.display().to_string(),
        }
        .to_string(),
    ))
}

/// Extract a `.tar.gz` stream into `store` and return the final tree.
///
/// `executable` lists the relative paths that become mode 0755. Everything else
/// is 0644. Archive modes and owners are ignored. On success the tree is
/// read-only and sits at `store/tree-<hex>`. On any error nothing is left in
/// the store except possibly an unreferenced staging directory, which
/// [`clean_staging`] removes.
///
/// # Errors
/// [`ExtractError::Refused`] for a rule violation, [`ExtractError::Malformed`]
/// for bad gzip or tar, [`ExtractError::Io`] for file system failures.
pub fn extract_targz<S: std::hash::BuildHasher>(
    archive: impl Read,
    store: &Path,
    executable: &HashSet<String, S>,
    limits: Limits,
) -> Result<Extracted, ExtractError> {
    ensure_private_dir(store)?;
    let staging_parent = store.join(".staging");
    ensure_private_child(&staging_parent)?;
    let staging = tempfile::Builder::new()
        .prefix("x-")
        .tempdir_in(&staging_parent)
        .map_err(io_err(TransportPhrase::ExtractCreateStaging.as_static()))?;
    let root = staging.path().join("tree");
    fs::create_dir(&root).map_err(io_err(TransportPhrase::ExtractCreateTree.as_static()))?;

    let result = unpack(archive, &root, store, executable, limits);
    // Discarded copies (a duplicate of a stored tree, or a failed install) can be
    // sealed, which TempDir cannot delete. Unseal and remove them here.
    let leftover = if root.exists() {
        evict(&root).map(drop)
    } else {
        Ok(())
    };
    let closed = staging
        .close()
        .map_err(io_err(TransportPhrase::ExtractRemoveStaging.as_static()));
    let out = result?;
    leftover?;
    closed?;
    Ok(out)
}

/// A tree built file by file in a private staging directory, for sources that
/// are not a `.tar.gz` (a pinned git commit). Nothing reaches the store until
/// [`StagedTree::install`], so the caller can hash the tree, compare it with the
/// lock and drop it without a trace. Dropping the value removes the staging
/// directory.
///
/// Files are created exclusively with a plain name, so a second spelling of one
/// name or a path through a link fails instead of replacing anything. The
/// executable set is part of the tree: as for a project directory, the tree
/// carries its own `.slopvac-exec` list, and [`tree_hash`] refuses a tree whose
/// file modes disagree with it.
#[derive(Debug)]
pub struct StagedTree {
    staging: tempfile::TempDir,
    root: PathBuf,
    executable: HashSet<String>,
    files: usize,
    bytes: u64,
    names: HashMap<String, (String, bool)>,
    dirs: HashSet<String>,
    budget: NodeBudget,
}

impl StagedTree {
    /// An empty staged tree under `store`, which is created if needed. The tree
    /// may hold at most `limits.nodes` files and directories.
    ///
    /// # Errors
    /// [`ExtractError::Io`] when the staging directory cannot be made, or
    /// [`ExtractError::Refused`] when `store` is not a private directory.
    pub fn new(store: &Path, limits: Limits) -> Result<Self, ExtractError> {
        ensure_private_dir(store)?;
        let staging_parent = store.join(".staging");
        ensure_private_child(&staging_parent)?;
        let staging = tempfile::Builder::new()
            .prefix("x-")
            .tempdir_in(&staging_parent)
            .map_err(io_err(TransportPhrase::ExtractCreateStaging.as_static()))?;
        let root = staging.path().join("tree");
        fs::create_dir(&root).map_err(io_err(TransportPhrase::ExtractCreateTree.as_static()))?;
        Ok(Self {
            staging,
            root,
            executable: HashSet::new(),
            files: 0,
            bytes: 0,
            names: HashMap::new(),
            dirs: HashSet::new(),
            budget: NodeBudget::new(limits.nodes),
        })
    }

    /// Write one regular file from `content`, which the caller has already
    /// bounded in size.
    ///
    /// # Errors
    /// [`ExtractError::Refused`] for a name the extractor would refuse or a name
    /// that is taken or collides with another, or when the tree has too many
    /// nodes; [`ExtractError::Io`] for a failed write.
    pub fn write_file(
        &mut self,
        path: &str,
        content: &mut dyn Read,
        executable: bool,
    ) -> Result<(), ExtractError> {
        let rel = normalise_entry_path(path.as_bytes())?;
        // Everything that can refuse the name is checked before anything is
        // created: case and Unicode collisions, then the node budget.
        claim_with_parents(&mut self.names, &rel, false)?;
        let parents = new_parents(&self.dirs, &rel);
        self.budget.charge(parents.len() + 1)?;
        self.dirs.extend(parents);
        let target = self.root.join(&rel);
        if let Some(dir) = target.parent() {
            fs::create_dir_all(dir)
                .map_err(io_err(TransportPhrase::ExtractCreateDirectory.as_static()))?;
        }
        let mut out = create_file(&target, executable).map_err(io_err(
            TransportText::ExtractCreatingFile { path: rel.clone() }.to_string(),
        ))?;
        let (_, len) = hash_stream(content, Some(&mut out), &rel, None)?;
        self.bytes += len;
        self.files += 1;
        if executable {
            self.executable.insert(rel);
        }
        Ok(())
    }

    /// The staging directory of the tree, for inspection.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// The tree hash of what was written.
    ///
    /// # Errors
    /// As [`tree_hash`].
    pub fn hash(&self) -> Result<TreeHash, ExtractError> {
        tree_hash(&self.root)
    }

    /// Seal the tree and move it into `store` under its hash. The hash is
    /// computed again here, so what is stored is what was hashed last.
    ///
    /// # Errors
    /// As [`tree_hash`], plus [`ExtractError::Io`] when the move fails.
    pub fn install(self, store: &Path) -> Result<Extracted, ExtractError> {
        let hash = tree_hash(&self.root)?;
        let exec: HashSet<&str> = self.executable.iter().map(String::as_str).collect();
        let result = install(&self.root, store, &hash, &exec);
        let leftover = if self.root.exists() {
            evict(&self.root).map(drop)
        } else {
            Ok(())
        };
        let closed = self
            .staging
            .close()
            .map_err(io_err(TransportPhrase::ExtractRemoveStaging.as_static()));
        let (root, quarantined) = result?;
        leftover?;
        closed?;
        Ok(Extracted {
            root,
            hash,
            files: self.files,
            bytes: self.bytes,
            quarantined,
        })
    }
}

#[expect(
    clippy::too_many_lines,
    reason = "the catalog calls take more lines than the former literals; the body is unchanged"
)]
fn unpack<S: std::hash::BuildHasher>(
    archive: impl Read,
    root: &Path,
    store: &Path,
    executable: &HashSet<String, S>,
    limits: Limits,
) -> Result<Extracted, ExtractError> {
    let seen = Arc::new(AtomicU64::new(0));
    let counted = Counting {
        inner: archive,
        seen: Arc::clone(&seen),
        limit: limits.compressed_bytes,
    };
    // Every gzip member passes through the same guards.
    let guarded = Guarded {
        inner: MultiGzDecoder::new(counted),
        expanded: 0,
        compressed: Arc::clone(&seen),
        limits,
    };
    let mut tar = tar::Archive::new(guarded);
    let malformed = |e: io::Error| ExtractError::Malformed(e.to_string());

    let mut files: Vec<FileRecord> = Vec::new();
    let mut exec_paths: Vec<String> = Vec::new();
    let mut names: HashMap<String, (String, bool)> = HashMap::new();
    claim(&mut names, EXEC_SIDECAR, false)?;
    let mut count = 0usize;
    let mut budget = NodeBudget::new(limits.nodes);
    let mut dirs: HashSet<String> = HashSet::new();
    let mut bytes = 0u64;
    let mut pending_name: Option<Vec<u8>> = None;

    // Raw entries: the tar crate's own preprocessing allocates sparse
    // descriptors before any type check, so long names and PAX records are
    // handled here with a size bound.
    for entry in tar.entries().map_err(malformed)?.raw(true) {
        let mut entry = entry.map_err(malformed)?;
        count += 1;
        if count > limits.entries {
            return Err(refused(
                TransportText::ExtractEntries {
                    limit: limits.entries,
                }
                .to_string(),
            ));
        }
        let kind = entry.header().entry_type();
        if kind.is_gnu_sparse() {
            return Err(refused(TransportPhrase::ExtractSparse.as_static()));
        }
        if kind.is_gnu_longname() {
            let mut name = read_meta(&mut entry)?;
            if let Some(nul) = name.iter().position(|&b| b == 0) {
                name.truncate(nul);
            }
            set_pending(&mut pending_name, name)?;
            continue;
        }
        if kind.is_pax_local_extensions() {
            for path in pax_paths(&read_meta(&mut entry)?)? {
                set_pending(&mut pending_name, path)?;
            }
            continue;
        }
        let is_dir = kind.is_dir();
        if !(kind.is_file() || is_dir) {
            return Err(refused(
                TransportText::ExtractEntryType {
                    kind: format!("{kind:?}"),
                }
                .to_string(),
            ));
        }
        let raw_name = pending_name
            .take()
            .unwrap_or_else(|| entry.path_bytes().into_owned());
        let rel = normalise_entry_path(&raw_name)?;
        claim_with_parents(&mut names, &rel, is_dir)?;
        if is_dir {
            continue;
        }
        let parents = new_parents(&dirs, &rel);
        budget.charge(parents.len() + 1)?;
        dirs.extend(parents);
        let exec = executable.contains(&rel);
        let rec = write_entry(&mut entry, root, rel, exec)?;
        bytes += rec.len;
        if exec {
            exec_paths.push(rec.path.clone());
        }
        files.push(rec);
    }
    if pending_name.is_some() {
        return Err(ExtractError::Malformed(
            TransportPhrase::ExtractLongName.as_static().into(),
        ));
    }
    // Drain what follows the tar end marker so trailing data counts against the limits.
    let mut rest = tar.into_inner();
    io::copy(&mut rest, &mut io::sink()).map_err(malformed)?;

    let file_count = files.len();
    if !exec_paths.is_empty() {
        budget.charge(1)?;
    }
    if let Some(rec) = write_sidecar(root, &mut exec_paths)? {
        files.push(rec);
    }

    let hash = tree_hash_of(files);
    let exec_set: HashSet<&str> = exec_paths.iter().map(String::as_str).collect();
    let (final_dir, quarantined) = install(root, store, &hash, &exec_set)?;
    Ok(Extracted {
        quarantined,
        root: final_dir,
        hash,
        files: file_count,
        bytes,
    })
}

/// Write the executable list into the staged tree and return its record.
fn write_sidecar(
    root: &Path,
    exec_paths: &mut [String],
) -> Result<Option<FileRecord>, ExtractError> {
    if exec_paths.is_empty() {
        return Ok(None);
    }
    exec_paths.sort();
    let sidecar = sidecar_bytes(exec_paths);
    let mut out = create_file(&root.join(EXEC_SIDECAR), false).map_err(io_err(
        TransportPhrase::ExtractCreateExecutableList.as_static(),
    ))?;
    out.write_all(&sidecar).map_err(io_err(
        TransportPhrase::ExtractWriteExecutableList.as_static(),
    ))?;
    Ok(Some(FileRecord {
        path: EXEC_SIDECAR.to_owned(),
        executable: false,
        sha: Sha256::digest(&sidecar).into(),
        len: sidecar.len() as u64,
    }))
}

/// The `path` records of a PAX block. Records that change sizes or sparse
/// layout are refused, since the extractor reads entries raw.
fn pax_paths(block: &[u8]) -> Result<Vec<Vec<u8>>, ExtractError> {
    let mut paths = Vec::new();
    for ext in tar::PaxExtensions::new(block) {
        let ext = ext.map_err(|e| ExtractError::Malformed(e.to_string()))?;
        let key = ext
            .key()
            .map_err(|_| refused(TransportPhrase::ExtractPaxUtf8.as_static()))?;
        if key == "path" {
            paths.push(ext.value_bytes().to_vec());
        } else if key == "size" || key.starts_with("GNU.sparse") {
            return Err(refused(
                TransportText::ExtractPaxRecord {
                    key: key.to_owned(),
                }
                .to_string(),
            ));
        }
    }
    Ok(paths)
}

/// Write one regular file into the staged tree and record its digest.
fn write_entry(
    entry: &mut tar::Entry<'_, impl Read>,
    root: &Path,
    rel: String,
    exec: bool,
) -> Result<FileRecord, ExtractError> {
    let target = root.join(&rel);
    if let Some(dir) = target.parent() {
        fs::create_dir_all(dir)
            .map_err(io_err(TransportPhrase::ExtractCreateDirectory.as_static()))?;
    }
    let mut out = create_file(&target, exec).map_err(io_err(
        TransportText::ExtractCreatingFile { path: rel.clone() }.to_string(),
    ))?;
    let declared = entry
        .header()
        .size()
        .map_err(|e| ExtractError::Malformed(e.to_string()))?;
    let (sha, len) = hash_stream(entry, Some(&mut out), &rel, None)?;
    if len != declared {
        return Err(ExtractError::Malformed(
            TransportText::ExtractShortEntry { path: rel.clone() }.to_string(),
        ));
    }
    Ok(FileRecord {
        path: rel,
        executable: exec,
        sha,
        len,
    })
}

fn sidecar_bytes(sorted: &[String]) -> Vec<u8> {
    let mut out = String::new();
    for p in sorted {
        out.push_str(p);
        out.push('\n');
    }
    out.into_bytes()
}

fn set_pending(slot: &mut Option<Vec<u8>>, name: Vec<u8>) -> Result<(), ExtractError> {
    if slot.replace(name).is_some() {
        return Err(refused(TransportPhrase::ExtractTwoNames.as_static()));
    }
    Ok(())
}

/// Read a long-name or PAX block, refusing one over [`MAX_META_BYTES`].
fn read_meta(entry: &mut impl Read) -> Result<Vec<u8>, ExtractError> {
    let mut buf = Vec::new();
    entry
        .take(MAX_META_BYTES + 1)
        .read_to_end(&mut buf)
        .map_err(|e| ExtractError::Malformed(e.to_string()))?;
    if buf.len() as u64 > MAX_META_BYTES {
        return Err(refused(
            TransportText::ExtractExtensionSize {
                limit: MAX_META_BYTES,
            }
            .to_string(),
        ));
    }
    Ok(buf)
}

/// Seal the staged tree and move it to its content-addressed place. Returns the
/// final directory and, if a corrupt cached tree had to be set aside, where.
fn install(
    root: &Path,
    store: &Path,
    hash: &TreeHash,
    exec: &HashSet<&str>,
) -> Result<(PathBuf, Option<PathBuf>), ExtractError> {
    seal(root, root, exec)?;
    let final_dir = store.join(format!("tree-{}", hash.hex()));
    let mut quarantined = None;
    match fs::rename(root, &final_dir) {
        Ok(()) => {}
        Err(_) if final_dir.exists() => {
            // Another process stored the same tree first. Keep it only if it verifies.
            if verify_tree(&final_dir, hash).is_err() {
                if let Evicted::Quarantined(aside) = evict(&final_dir)? {
                    quarantined = Some(aside);
                }
                fs::rename(root, &final_dir)
                    .map_err(io_err(TransportPhrase::ExtractStoreTree.as_static()))?;
            }
        }
        Err(e) => {
            return Err(ExtractError::Io {
                what: TransportPhrase::ExtractStoreTree.as_static().into(),
                source: e,
            });
        }
    }
    // Renaming a directory needs write access to it, so the root is sealed last.
    set_mode(&final_dir, 0o555).map_err(io_err(TransportPhrase::ExtractSealTree.as_static()))?;
    Ok((final_dir, quarantined))
}

/// Read `src` to the end, hash it and optionally copy it to `sink`.
fn hash_stream(
    src: &mut dyn Read,
    mut sink: Option<&mut File>,
    what: &str,
    cap: Option<u64>,
) -> Result<([u8; 32], u64), ExtractError> {
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 64 * 1024];
    let mut len = 0u64;
    loop {
        let n = src.read(&mut buf).map_err(|e| {
            ExtractError::Malformed(
                TransportText::ExtractEntryRead {
                    what: what.to_owned(),
                    detail: e.to_string(),
                }
                .to_string(),
            )
        })?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
        if let Some(out) = sink.as_deref_mut() {
            out.write_all(&buf[..n]).map_err(io_err(
                TransportText::ExtractEntryWrite {
                    what: what.to_owned(),
                }
                .to_string(),
            ))?;
        }
        len += n as u64;
        if cap.is_some_and(|c| len > c) {
            return Err(refused(
                TransportText::ExtractEntrySize {
                    what: what.to_owned(),
                }
                .to_string(),
            ));
        }
    }
    Ok((hasher.finalize().into(), len))
}

/// Make files read-only and directories non-writable, bottom-up. The base
/// directory itself is left for the caller, which seals it last.
fn seal(base: &Path, dir: &Path, exec: &HashSet<&str>) -> Result<(), ExtractError> {
    for entry in
        fs::read_dir(dir).map_err(io_err(TransportPhrase::ExtractReadDirectory.as_static()))?
    {
        let entry = entry.map_err(io_err(TransportPhrase::ExtractReadDirectory.as_static()))?;
        let path = entry.path();
        let ty = entry
            .file_type()
            .map_err(io_err(TransportPhrase::ExtractInspectEntry.as_static()))?;
        if ty.is_dir() {
            seal(base, &path, exec)?;
            set_mode(&path, 0o555)
                .map_err(io_err(TransportPhrase::ExtractSealDirectory.as_static()))?;
        } else {
            let rel = path
                .strip_prefix(base)
                .ok()
                .and_then(Path::to_str)
                .map(|r| r.replace('\\', "/"))
                .unwrap_or_default();
            let mode = if exec.contains(rel.as_str()) {
                0o555
            } else {
                0o444
            };
            set_mode(&path, mode).map_err(io_err(TransportPhrase::ExtractSealFile.as_static()))?;
        }
    }
    Ok(())
}

#[cfg(unix)]
fn is_executable(path: &Path) -> bool {
    use std::os::unix::fs::PermissionsExt;
    fs::metadata(path).is_ok_and(|m| m.permissions().mode() & 0o100 != 0)
}

#[cfg(not(unix))]
fn is_executable(_: &Path) -> bool {
    false
}

/// Open `path` for reading and require that the opened handle is a regular file.
///
/// A path checked a moment ago may have been swapped for a FIFO or a link to a device. The open
/// does not block (a FIFO with no writer would hang an ordinary open), and the check runs on the
/// handle, not the name, so a swap cannot slip between check and read. Regular files ignore the
/// non-blocking flag.
///
/// # Errors
/// An [`io::ErrorKind::InvalidInput`] error when the handle is not a regular file, or the open's
/// own error.
pub(crate) fn open_regular(path: &Path) -> io::Result<File> {
    let mut opts = OpenOptions::new();
    opts.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        opts.custom_flags(i32::try_from(rustix::fs::OFlags::NONBLOCK.bits()).unwrap_or_default());
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        // FILE_FLAG_BACKUP_SEMANTICS lets a directory open, so the handle check names it
        // (InvalidInput) instead of the open failing with PermissionDenied.
        opts.custom_flags(0x0200_0000);
    }
    let file = opts.open(path)?;
    if file.metadata()?.is_file() {
        Ok(file)
    } else {
        Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            TransportPhrase::ExtractNotRegular.as_static(),
        ))
    }
}

/// A reader that keeps a copy of what it reads, so a file hashed in one pass is parsed from the
/// same bytes instead of being opened a second time.
struct Capture<'a> {
    inner: &'a mut File,
    kept: Vec<u8>,
}

impl Read for Capture<'_> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let n = self.inner.read(buf)?;
        self.kept.extend_from_slice(&buf[..n]);
        Ok(n)
    }
}

/// Recompute the hash of a stored tree.
///
/// Refuses anything but regular files and directories, a root that is a link,
/// names the extractor would refuse, and trees past the entry, depth or size
/// bounds. The walk is iterative. The executable set comes from the sidecar
/// file, so the result is the same on every platform; on Unix the file modes
/// must also match it.
///
/// # Errors
/// [`ExtractError::Refused`] for a link, special file, bad name or bound
/// breach, [`ExtractError::Io`] for read failures.
pub fn tree_hash(dir: &Path) -> Result<TreeHash, ExtractError> {
    tree_hash_observed(dir, &mut |_, _| {})
}

/// [`tree_hash`] with a callback after each file is hashed, given its relative name and path.
///
/// The callback is the test seam for the single-read guarantee: a test rewrites the sidecar from
/// it, and the result must still come from the bytes that were hashed.
#[expect(
    clippy::too_many_lines,
    reason = "the catalog calls take more lines than the former literals; the body is unchanged"
)]
fn tree_hash_observed(
    dir: &Path,
    after_hash: &mut dyn FnMut(&str, &Path),
) -> Result<TreeHash, ExtractError> {
    let dir = normalised(dir);
    let dir = dir.as_path();
    let root_meta = fs::symlink_metadata(dir)
        .map_err(io_err(TransportPhrase::ExtractInspectRoot.as_static()))?;
    if !root_meta.is_dir() {
        return Err(refused(TransportPhrase::ExtractRootType.as_static()));
    }
    let mut files = Vec::new();
    let mut names: HashMap<String, (String, bool)> = HashMap::new();
    let mut stack = vec![(dir.to_owned(), String::new())];
    let mut nodes = NodeBudget::new(MAX_TREE_NODES);
    let mut budget = MAX_TREE_BYTES;
    let mut sidecar: Option<Vec<u8>> = None;
    let mut on_disk_exec: HashSet<String> = HashSet::new();
    while let Some((path, prefix)) = stack.pop() {
        for entry in fs::read_dir(&path)
            .map_err(io_err(TransportPhrase::ExtractReadDirectory.as_static()))?
        {
            let entry = entry.map_err(io_err(TransportPhrase::ExtractReadDirectory.as_static()))?;
            nodes.charge(1)?;
            let name = entry
                .file_name()
                .into_string()
                .map_err(|_| refused(TransportPhrase::ExtractNameUtf8.as_static()))?;
            let rel = if prefix.is_empty() {
                name
            } else {
                format!("{prefix}/{name}")
            };
            check_name(&rel).map_err(|e| {
                refused(
                    TransportText::ExtractPath {
                        path: rel.clone(),
                        detail: e,
                    }
                    .to_string(),
                )
            })?;
            let child = entry.path();
            let meta = fs::symlink_metadata(&child)
                .map_err(io_err(TransportPhrase::ExtractInspectEntry.as_static()))?;
            if meta.is_dir() {
                claim(&mut names, &rel, true)?;
                stack.push((child, rel));
            } else if meta.is_file() {
                claim(&mut names, &rel, false)?;
                if meta.len() > budget {
                    return Err(refused(
                        TransportText::ExtractTreeSize { path: rel.clone() }.to_string(),
                    ));
                }
                if is_executable(&child) {
                    on_disk_exec.insert(rel.clone());
                }
                let mut f = open_regular(&child).map_err(|e| {
                    if e.kind() == io::ErrorKind::InvalidInput {
                        refused(TransportText::ExtractFileType { path: rel.clone() }.to_string())
                    } else {
                        io_err(TransportText::ExtractReadingFile { path: rel.clone() }.to_string())(
                            e,
                        )
                    }
                })?;
                let (sha, len) = if rel == EXEC_SIDECAR {
                    let mut tee = Capture {
                        inner: &mut f,
                        kept: Vec::new(),
                    };
                    let hashed = hash_stream(&mut tee, None, &rel, Some(budget))?;
                    sidecar = Some(tee.kept);
                    hashed
                } else {
                    hash_stream(&mut f, None, &rel, Some(budget))?
                };
                after_hash(&rel, &child);
                budget -= len;
                files.push(FileRecord {
                    path: rel,
                    executable: false,
                    sha,
                    len,
                });
            } else {
                return Err(refused(
                    TransportText::ExtractSpecialFile { path: rel.clone() }.to_string(),
                ));
            }
        }
    }
    files.sort_by(|a, b| a.path.as_bytes().cmp(b.path.as_bytes()));
    if let Some(bytes) = sidecar {
        mark_executables(&bytes, &mut files)?;
    }
    if cfg!(unix) {
        for f in &files {
            let on_disk = on_disk_exec.contains(f.path.as_str());
            if on_disk && !f.executable {
                return Err(refused(
                    TransportPhrase::ExtractExecutableUnlisted.as_static(),
                ));
            }
            if !on_disk && f.executable {
                return Err(refused(TransportPhrase::ExtractExecutableBit.as_static()));
            }
        }
    }
    Ok(tree_hash_of(files))
}

/// Parse the sidecar bytes (read once while the tree was hashed) and flag the files it lists.
///
/// The format is canonical: one path per line, each ending in a newline, in
/// strictly ascending byte order, each naming a file in the tree other than the
/// sidecar. Each line is read under a length cap and checked as it is parsed, so
/// the work and memory are bounded by the (already bounded) set of files.
/// `files` must be sorted by path.
fn mark_executables(bytes: &[u8], files: &mut [FileRecord]) -> Result<(), ExtractError> {
    let mut reader = io::BufReader::new(bytes);
    let mut previous: Vec<u8> = Vec::new();
    let mut line: Vec<u8> = Vec::new();
    loop {
        line.clear();
        let n = (&mut reader)
            .take(MAX_SIDECAR_LINE)
            .read_until(b'\n', &mut line)
            .map_err(io_err(
                TransportPhrase::ExtractReadExecutableList.as_static(),
            ))?;
        if n == 0 {
            return Ok(());
        }
        if line.pop() != Some(b'\n') {
            return Err(refused(TransportPhrase::ExtractExecutableLine.as_static()));
        }
        if !previous.is_empty() && line <= previous {
            return Err(refused(TransportPhrase::ExtractExecutableOrder.as_static()));
        }
        let idx = files
            .binary_search_by(|r| r.path.as_bytes().cmp(line.as_slice()))
            .map_err(|_| refused(TransportPhrase::ExtractExecutableMissing.as_static()))?;
        if files[idx].path == EXEC_SIDECAR {
            return Err(refused(TransportPhrase::ExtractExecutableSelf.as_static()));
        }
        files[idx].executable = true;
        std::mem::swap(&mut previous, &mut line);
    }
}

/// Check that a stored tree still has `expected` as its hash.
///
/// # Errors
/// [`ExtractError::Tampered`] on any difference. Callers evict the entry and fail the run (exit 2).
pub fn verify_tree(dir: &Path, expected: &TreeHash) -> Result<(), ExtractError> {
    match tree_hash(dir) {
        Ok(actual) if actual == *expected => Ok(()),
        Ok(_) | Err(ExtractError::Refused(_)) => Err(ExtractError::Tampered {
            path: dir.to_owned(),
        }),
        Err(e) => Err(e),
    }
}

/// Prefix of the directories [`evict`] renames oversized trees to.
const QUARANTINE_PREFIX: &str = ".quarantine-";

/// Remove a stored tree, restoring write permission first.
///
/// The walk is iterative and bounded by the same node and depth limits as
/// verification. A tree past those limits is hostile: it is renamed, whole and
/// unread, to `.quarantine-<name>-<unique>` next to itself and left for the
/// operator, and the call succeeds because `dir` no longer exists; the result
/// is [`Evicted::Quarantined`] with the new path so the caller can report the
/// retained storage. Nothing below such a tree is touched past the bound. A link
/// at `dir` is removed itself, never followed.
///
/// # Errors
/// [`ExtractError::Io`] when removal or quarantine fails.
pub fn evict(dir: &Path) -> Result<Evicted, ExtractError> {
    let dir = normalised(dir);
    let dir = dir.as_path();
    if !fs::symlink_metadata(dir).is_ok_and(|m| m.is_dir()) {
        return remove_tree(dir).map(|()| Evicted::Removed);
    }
    // (directory, depth); the root is depth 0, as in verification.
    let mut stack = vec![(dir.to_owned(), 0usize)];
    let mut nodes = NodeBudget::new(MAX_TREE_NODES);
    while let Some((path, depth)) = stack.pop() {
        let _ = set_mode(&path, 0o700);
        let Ok(rd) = fs::read_dir(&path) else {
            continue;
        };
        let mut oversized = false;
        for e in rd.flatten() {
            let Ok(ty) = e.file_type() else { continue };
            if nodes.charge(1).is_err() || (ty.is_dir() && depth >= MAX_TREE_DEPTH) {
                oversized = true;
                break;
            }
            if ty.is_dir() {
                stack.push((e.path(), depth + 1));
            } else if cfg!(windows) && ty.is_file() {
                // Windows refuses to delete read-only files.
                let _ = set_mode(&e.path(), 0o600);
            }
        }
        if oversized {
            // `rd` ended with the loop above: Windows refuses to rename a
            // directory while a handle is open on it or below it.
            return quarantine(dir).map(Evicted::Quarantined);
        }
    }
    remove_tree(dir).map(|()| Evicted::Removed)
}

fn remove_tree(dir: &Path) -> Result<(), ExtractError> {
    match fs::remove_dir_all(dir) {
        Ok(()) => Ok(()),
        Err(e) if e.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(ExtractError::Io {
            what: TransportText::ExtractRemoving {
                path: dir.display().to_string(),
            }
            .to_string(),
            source: e,
        }),
    }
}

/// Rename `dir` to a unique sibling without reading it.
fn quarantine(dir: &Path) -> Result<PathBuf, ExtractError> {
    static SERIAL: AtomicU64 = AtomicU64::new(0);
    let name = dir
        .file_name()
        .map_or_else(String::new, |n| n.to_string_lossy().into_owned());
    let nanos = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .map_or(0, |d| d.as_nanos());
    let aside = dir.with_file_name(format!(
        "{QUARANTINE_PREFIX}{name}-{}-{}-{nanos}",
        std::process::id(),
        SERIAL.fetch_add(1, Ordering::Relaxed)
    ));
    fs::rename(dir, &aside).map_err(io_err(
        TransportText::ExtractQuarantining {
            path: dir.display().to_string(),
        }
        .to_string(),
    ))?;
    Ok(aside)
}

/// Remove staging directories older than `max_age`, for example left by a killed run.
///
/// The `.staging` directory is inspected without following links first: a link,
/// a non-directory, or a directory owned by someone else is refused and nothing
/// is listed, changed or removed. An absent directory is an empty report.
/// Existing `.quarantine-*` entries are kept. A stale entry too large to walk is
/// renamed aside and listed in [`StagingReport::quarantined`].
///
/// # Errors
/// [`ExtractError::Refused`] for an unsafe `.staging` directory. Entries that
/// cannot be removed are skipped.
pub fn clean_staging(store: &Path, max_age: Duration) -> Result<StagingReport, ExtractError> {
    let parent = store.join(".staging");
    let mut report = StagingReport::default();
    if inspect_private_child(&parent)?.is_none() {
        return Ok(report);
    }
    let Ok(rd) = fs::read_dir(&parent) else {
        return Ok(report);
    };
    for e in rd.flatten() {
        if e.file_name()
            .to_string_lossy()
            .starts_with(QUARANTINE_PREFIX)
        {
            continue;
        }
        let old = e
            .metadata()
            .and_then(|m| m.modified())
            .is_ok_and(|t| SystemTime::now().duration_since(t).unwrap_or_default() >= max_age);
        if !old {
            continue;
        }
        match evict(&e.path()) {
            Ok(Evicted::Removed) => report.removed += 1,
            Ok(Evicted::Quarantined(aside)) => report.quarantined.push(aside),
            Err(_) => {}
        }
    }
    Ok(report)
}

#[cfg(test)]
mod open_regular_tests {
    use super::*;
    use std::sync::mpsc;

    /// Run `f` on a thread and fail the test if it does not return in ten seconds, which is what
    /// a blocking open of a FIFO with no writer would do.
    fn within_ten_seconds<T: Send + 'static>(f: impl FnOnce() -> T + Send + 'static) -> T {
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            let _ = tx.send(f());
        });
        rx.recv_timeout(Duration::from_secs(10))
            .expect("the open blocked")
    }

    #[test]
    fn a_regular_file_opens_and_reads() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("f");
        fs::write(&path, b"hello").unwrap();
        let mut text = String::new();
        open_regular(&path)
            .unwrap()
            .read_to_string(&mut text)
            .unwrap();
        assert_eq!(text, "hello");
    }

    #[test]
    fn a_missing_file_keeps_its_own_error() {
        let dir = tempfile::tempdir().unwrap();
        let err = open_regular(&dir.path().join("nope")).unwrap_err();
        assert_eq!(err.kind(), io::ErrorKind::NotFound);
    }

    #[test]
    fn a_directory_is_not_a_regular_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().to_owned();
        let err = within_ten_seconds(move || open_regular(&path).unwrap_err());
        assert_eq!(err.kind(), io::ErrorKind::InvalidInput);
    }

    #[cfg(unix)]
    #[test]
    fn a_fifo_and_a_link_to_one_are_refused_without_blocking() {
        let dir = tempfile::tempdir().unwrap();
        let fifo = dir.path().join("fifo");
        assert!(
            std::process::Command::new("mkfifo")
                .arg(&fifo)
                .status()
                .unwrap()
                .success()
        );
        let link = dir.path().join("link");
        std::os::unix::fs::symlink(&fifo, &link).unwrap();
        for path in [fifo, link] {
            let err = within_ten_seconds(move || open_regular(&path).unwrap_err());
            assert_eq!(err.kind(), io::ErrorKind::InvalidInput);
        }
    }
}

#[cfg(test)]
mod single_read_tests {
    use super::*;

    /// A tree with one executable file and the sidecar that lists it.
    fn tree(root: &Path) {
        fs::create_dir_all(root).unwrap();
        fs::write(root.join("run.sh"), b"#!/bin/sh\n").unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(root.join("run.sh"), fs::Permissions::from_mode(0o755)).unwrap();
        }
        fs::write(root.join(EXEC_SIDECAR), b"run.sh\n").unwrap();
    }

    #[test]
    fn the_sidecar_is_parsed_from_the_bytes_that_were_hashed() {
        let scratch = tempfile::tempdir().unwrap();
        let plain = scratch.path().join("plain");
        let swapped = scratch.path().join("swapped");
        tree(&plain);
        tree(&swapped);
        let expected = tree_hash(&plain).unwrap();

        // Right after the sidecar is hashed, replace it with a list that names a missing file.
        // A second open would read that list and fail; the captured bytes ignore it.
        let got = tree_hash_observed(&swapped, &mut |rel, path| {
            if rel == EXEC_SIDECAR {
                fs::write(path, b"missing.sh\n").unwrap();
            }
        })
        .expect("the hashed bytes are what gets parsed");
        assert_eq!(got, expected);
    }

    #[test]
    fn the_seam_sees_every_file_once() {
        let scratch = tempfile::tempdir().unwrap();
        tree(scratch.path());
        let mut seen = Vec::new();
        tree_hash_observed(scratch.path(), &mut |rel, _| seen.push(rel.to_owned())).unwrap();
        seen.sort();
        assert_eq!(seen, [EXEC_SIDECAR, "run.sh"]);
    }
}
