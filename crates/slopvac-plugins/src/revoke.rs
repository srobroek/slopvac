//! The signed revocation list and its cache (threat model section 5.3, K5, K6).
//!
//! A publisher whose key is stolen cannot sign its own revocation, so the
//! first-party root key signs one list for everyone. It names publisher key
//! ids and artifact manifest digests. A key or digest on the list fails `sync`
//! with exit 2 and refuses to spawn; trust records for it are inert, and
//! [`RevocationList::flag`] marks them in `plugins status`.
//!
//! # Format
//!
//! The list is strict canonical JSON (sorted keys, no white space, at most
//! 1 MiB), signed by a root key in minisign's prehashed mode:
//!
//! ```json
//! {"digests":["sha256:..."],"expires":"2026-12-12T00:00:00Z","issued":"2026-11-12T00:00:00Z","keys":["C0E5E326B2F9B470"],"schema_version":1,"type":"revocations"}
//! ```
//!
//! `keys` holds 16-digit uppercase key ids and `digests` holds manifest
//! digests, each sorted and without repeats, so one list has one encoding.
//! `issued` orders lists: a fetched list older than the cached one is a
//! rollback and is refused, and so is a different list with the same
//! `issued` (equivocation). `expires` is later than `issued` by at most
//! [`STALE_AFTER_DAYS`] days, so the root must sign a new list at least that
//! often.
//!
//! # Where it comes from
//!
//! The list is an OCI artifact of type [`ARTIFACT_TYPE_REVOCATIONS`] with
//! exactly two layers, the list ([`MEDIA_REVOCATIONS`]) and its `.minisig`
//! ([`crate::sign::MEDIA_MINISIG`]), at [`DEFAULT_SOURCE`]. `sync` fetches it
//! on every online run ([`Revocations::refresh`]), and so must the CLI's
//! `update` and `outdated`. Online, a list that cannot be fetched, or whose
//! signed `expires` has passed (a replayed old list), fails the command with
//! exit 2 and leaves the cache as it was; the user must go offline explicitly
//! to run on the cache.
//!
//! # Cache and offline use
//!
//! A verified list is cached in one private file in the per-user state
//! directory, with the time it was fetched. A refresh holds the cache lock
//! ([`Revocations::lock`]) while it re-reads the cache, compares and replaces
//! it, so two refreshes cannot commit a newer list and then an older one.
//!
//! Every read verifies the signature again, so an edit to the signed list
//! fails closed ([`RevocationError::CacheInvalid`]): spawn and offline sync
//! exit 2 until an online refresh replaces it. The fetch time beside the list
//! is not signed and is only shown to the user; freshness comes from the
//! signed `expires`. Offline runs and every spawn read the cache
//! ([`Revocations::cached`]). A cached list past its `expires` prints a notice
//! and does not block; a machine that never fetched a list runs with a notice
//! too (residual risk R3). A local process of the same user can still put back
//! an older signed list (R6).

use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::messages::trust::{self as messages, RevokePhrase, codes};
use crate::oci::{Client, Digest, OciError, Reference};
use crate::sign::{
    MEDIA_MINISIG, PublicKey, RELEASE_KEY_FILE, SignError, is_key_id, parse_canonical,
    release_key_from, utc_seconds, verify_bytes,
};
use crate::trust::{Revocation, TrustRecord};

/// `artifactType` of the revocation-list artifact.
pub const ARTIFACT_TYPE_REVOCATIONS: &str = "application/vnd.slopvac.revocations.v1";
/// Media type of the layer that holds the list.
pub const MEDIA_REVOCATIONS: &str = "application/vnd.slopvac.revocations.v1+json";
/// The `type` field of a list.
pub const LIST_TYPE: &str = "revocations";
/// Where the list is published. The release process must publish a signed
/// list here before the CLI ships.
pub const DEFAULT_SOURCE: &str = "ghcr.io/slopvac/slopvac-revocations:latest";
/// Largest list the verifier reads.
pub const MAX_LIST_BYTES: usize = 1 << 20;
/// The longest a list is valid (`expires` minus `issued`). An offline cache
/// past its `expires` prints a notice (threat model R3).
pub const STALE_AFTER_DAYS: i64 = 30;

const DAY: i64 = 86_400;
const MAX_MINISIG_BYTES: u64 = 4 * 1024;
const CACHE_FILE: &str = "revocations.json";
const LOCK_FILE: &str = "revocations.lock";
const MAX_CACHE_BYTES: u64 = 3 << 20;

/// Why the list could not be used. Every variant makes the command exit 2.
#[derive(Debug, Error)]
pub enum RevocationError {
    /// No root key is configured, so no list can verify. Fails closed.
    #[error("{}", messages::revoke_no_root_key())]
    NoRootKey,
    /// The compiled root key does not parse. Fails closed like [`Self::NoRootKey`].
    #[error("{}", messages::revoke_root_key_unusable(.0))]
    RootKey(String),
    /// The list is larger than [`MAX_LIST_BYTES`].
    #[error("{}", messages::revoke_too_large(MAX_LIST_BYTES))]
    TooLarge,
    /// The list is not a valid version 1 list.
    #[error("{}", messages::revoke_invalid(.0))]
    Invalid(String),
    /// No root key signed these bytes.
    #[error("{}", messages::revoke_bad_signature())]
    BadSignature,
    /// The registry or the network failed, or withheld the list.
    #[error("{}", messages::revoke_unavailable(&.0.to_string()))]
    Fetch(#[from] OciError),
    /// The fetched list is past its signed `expires`: the source serves an
    /// old list. Treated like a withheld list.
    #[error("{}", messages::revoke_expired(.expires))]
    Expired {
        /// The list's `expires`.
        expires: String,
    },
    /// The artifact does not have the shape of a list artifact.
    #[error("{}", messages::revoke_layout(.0))]
    Layout(String),
    /// The fetched list is older than the cached one.
    #[error("{}", messages::revoke_rollback(.cached, .fetched))]
    Rollback {
        /// `issued` of the cached list.
        cached: String,
        /// `issued` of the fetched list.
        fetched: String,
    },
    /// The fetched list has the cached list's `issued` time but other
    /// content: two signed lists claim one moment, and the cache is kept.
    #[error("{}", messages::revoke_equivocation(.issued))]
    Equivocation {
        /// The shared `issued` time.
        issued: String,
    },
    /// The cache file does not hold a list the root signed.
    #[error("{}", messages::revoke_cache_damaged(.path, .why))]
    CacheInvalid {
        /// The cache file.
        path: PathBuf,
        /// What is wrong.
        why: String,
    },
    /// A file operation on the cache failed.
    #[error("{}", messages::revoke_cache_io(.what, &.source.to_string()))]
    Io {
        /// The operation.
        what: String,
        /// The cause.
        #[source]
        source: io::Error,
    },
    /// The caller's clock is not a `YYYY-MM-DDTHH:MM:SSZ` time.
    #[error("{}", messages::revoke_clock(.0))]
    Clock(String),
}

impl RevocationError {
    /// The stable error code (policies.md section 3.5).
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::NoRootKey
            | Self::RootKey(_)
            | Self::TooLarge
            | Self::Invalid(_)
            | Self::BadSignature
            | Self::Layout(_) => codes::LIST_INVALID,
            // A refused credential helper is a login problem, not an
            // unavailable list.
            Self::Fetch(e) => e.code().unwrap_or(codes::LIST_UNAVAILABLE),
            Self::Expired { .. } => codes::LIST_EXPIRED,
            Self::Rollback { .. } => codes::LIST_ROLLBACK,
            Self::Equivocation { .. } => codes::LIST_EQUIVOCATION,
            Self::CacheInvalid { .. } | Self::Io { .. } => codes::CACHE_INVALID,
            Self::Clock(_) => codes::CLOCK_INVALID,
        }
    }
}

impl From<SignError> for RevocationError {
    fn from(e: SignError) -> Self {
        match e {
            SignError::BadSignature => Self::BadSignature,
            SignError::StatementTooLarge => Self::TooLarge,
            // The raw reason: `Invalid` escapes it once, on display.
            SignError::NotCanonical(m) => Self::Invalid(messages::sign_not_canonical_raw(&m)),
            SignError::InvalidStatement(m) => {
                Self::Invalid(messages::sign_invalid_statement_raw(&m))
            }
            other => Self::Invalid(other.to_string()),
        }
    }
}

/// The reason in `e` before escaping, for a variant that escapes it once.
fn raw_reason(e: RevocationError) -> String {
    match e {
        RevocationError::Invalid(m) => messages::revoke_invalid_raw(&m),
        RevocationError::Layout(m) => messages::revoke_layout_raw(&m),
        other => other.to_string(),
    }
}

fn io_err(what: &str) -> impl FnOnce(io::Error) -> RevocationError + '_ {
    move |source| RevocationError::Io {
        what: what.to_owned(),
        source,
    }
}

/// What a revoked trust record is revoked by.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Revoked {
    /// The publisher key with this key id.
    Key(String),
    /// The artifact with this manifest digest.
    Digest(String),
}

impl std::fmt::Display for Revoked {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Key(id) => f.write_str(&messages::revoke_flag_key(id)),
            Self::Digest(d) => f.write_str(&messages::revoke_flag_artifact(d)),
        }
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ListDoc {
    schema_version: u32,
    #[serde(rename = "type")]
    kind: String,
    issued: String,
    expires: String,
    keys: Vec<String>,
    digests: Vec<String>,
}

/// A verified revocation list. The default is the empty list of a machine
/// that never fetched one.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RevocationList {
    issued: Option<String>,
    expires: Option<String>,
    keys: Vec<String>,
    digests: Vec<String>,
}

fn strictly_sorted(v: &[String]) -> bool {
    v.windows(2).all(|w| w[0] < w[1])
}

impl RevocationList {
    /// Verify `statement` and its `.minisig` text against the root keys.
    ///
    /// # Errors
    /// [`RevocationError::NoRootKey`] with no roots,
    /// [`RevocationError::TooLarge`] over [`MAX_LIST_BYTES`],
    /// [`RevocationError::BadSignature`] unless a root signed exactly these
    /// bytes (prehashed), [`RevocationError::Invalid`] for anything that is not
    /// a canonical version 1 list valid for at most [`STALE_AFTER_DAYS`] days.
    pub fn verify(
        statement: &[u8],
        minisig: &str,
        roots: &[PublicKey],
    ) -> Result<Self, RevocationError> {
        if roots.is_empty() {
            return Err(RevocationError::NoRootKey);
        }
        if statement.len() > MAX_LIST_BYTES {
            return Err(RevocationError::TooLarge);
        }
        if !roots
            .iter()
            .any(|k| verify_bytes(k, statement, minisig).is_ok())
        {
            return Err(RevocationError::BadSignature);
        }
        let doc: ListDoc = parse_canonical(statement, MAX_LIST_BYTES)?;
        let invalid = |why: &str| Err(RevocationError::Invalid(why.to_owned()));
        if doc.schema_version != 1 || doc.kind != LIST_TYPE {
            return invalid(RevokePhrase::NotVersionOne.as_static());
        }
        let (Some(issued), Some(expires)) = (utc_seconds(&doc.issued), utc_seconds(&doc.expires))
        else {
            return invalid(RevokePhrase::Time.as_static());
        };
        if expires <= issued || expires - issued > STALE_AFTER_DAYS * DAY {
            return invalid(RevokePhrase::Window.as_static());
        }
        if !doc.keys.iter().all(|k| is_key_id(k)) {
            return invalid(RevokePhrase::KeyId.as_static());
        }
        if doc.digests.iter().any(|d| Digest::parse(d).is_err()) {
            return invalid(RevokePhrase::Digest.as_static());
        }
        if !strictly_sorted(&doc.keys) || !strictly_sorted(&doc.digests) {
            return invalid(RevokePhrase::Unsorted.as_static());
        }
        Ok(Self {
            issued: Some(doc.issued),
            expires: Some(doc.expires),
            keys: doc.keys,
            digests: doc.digests,
        })
    }

    /// When the root issued the list; `None` for the empty default.
    #[must_use]
    pub fn issued(&self) -> Option<&str> {
        self.issued.as_deref()
    }

    /// When the list stops being fresh; `None` for the empty default.
    #[must_use]
    pub fn expires(&self) -> Option<&str> {
        self.expires.as_deref()
    }

    fn expired_at(&self, now: i64) -> bool {
        self.expires
            .as_deref()
            .and_then(utc_seconds)
            .is_some_and(|e| now > e)
    }

    /// Whether the key with this key id is revoked.
    #[must_use]
    pub fn revokes_key(&self, key_id: &str) -> bool {
        self.keys
            .binary_search_by(|k| k.as_str().cmp(&key_id.to_ascii_uppercase()))
            .is_ok()
    }

    /// Whether the artifact with this manifest digest is revoked.
    #[must_use]
    pub fn revokes_digest(&self, digest: &str) -> bool {
        self.digests
            .binary_search_by(|d| d.as_str().cmp(digest))
            .is_ok()
    }

    /// The entries in the form [`crate::trust::TrustGate::with_revoked`] takes.
    #[must_use]
    pub fn revocations(&self) -> Vec<Revocation> {
        let keys = self.keys.iter().cloned().map(Revocation::KeyId);
        let digests = self
            .digests
            .iter()
            .filter_map(|d| Digest::parse(d).ok())
            .map(Revocation::ManifestDigest);
        keys.chain(digests).collect()
    }

    /// Why a trust record is revoked, for `plugins status`. `None` when it is not.
    #[must_use]
    pub fn flag(&self, record: &TrustRecord) -> Option<Revoked> {
        if let Some(d) = record
            .manifest_digest
            .as_deref()
            .filter(|d| self.revokes_digest(d))
        {
            return Some(Revoked::Digest(d.to_owned()));
        }
        record
            .key_id
            .as_deref()
            .filter(|k| self.revokes_key(k))
            .map(|k| Revoked::Key(k.to_ascii_uppercase()))
    }
}

/// A notice about the list. It never blocks the run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RevocationNotice {
    /// No list was ever fetched on this machine.
    Missing,
    /// The cached list is past its signed `expires`.
    Stale {
        /// When the root issued it.
        issued: String,
        /// When it expired.
        expires: String,
    },
}

impl RevocationNotice {
    /// The stable notice code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Missing => codes::LIST_MISSING,
            Self::Stale { .. } => codes::LIST_STALE,
        }
    }
}

impl std::fmt::Display for RevocationNotice {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Missing => f.write_str(&messages::revoke_notice_missing()),
            Self::Stale { issued, expires } => {
                f.write_str(&messages::revoke_notice_stale(issued, expires))
            }
        }
    }
}

/// The list in force for this run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Current {
    /// The verified list, or the empty list when none was ever fetched.
    pub list: RevocationList,
    /// When the list was fetched, if ever. Unsigned; for display only.
    pub fetched_at: Option<String>,
    /// Notices to print. They do not block.
    pub notices: Vec<RevocationNotice>,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct CacheDoc {
    schema_version: u32,
    fetched_at: String,
    statement: String,
    minisig: String,
}

/// The exclusive cache lock. Dropping it releases the lock.
#[derive(Debug)]
pub struct CacheLock {
    _file: File,
}

/// Where the list comes from, where it is cached, which keys verify it and
/// what time it is.
#[derive(Debug, Clone)]
pub struct Revocations {
    dir: PathBuf,
    roots: Vec<PublicKey>,
    source: Reference,
    now: String,
    now_at: i64,
}

impl Revocations {
    /// `dir` is the per-user state directory. `roots` are the first-party root
    /// keys; with none, every list fails closed. `now` is the caller's clock as
    /// `YYYY-MM-DDTHH:MM:SSZ`.
    ///
    /// # Errors
    /// [`RevocationError::Clock`] for a malformed `now`.
    pub fn new(
        dir: impl Into<PathBuf>,
        roots: Vec<PublicKey>,
        source: Reference,
        now: &str,
    ) -> Result<Self, RevocationError> {
        let now_at = utc_seconds(now).ok_or_else(|| RevocationError::Clock(now.to_owned()))?;
        Ok(Self {
            dir: dir.into(),
            roots,
            source,
            now: now.to_owned(),
            now_at,
        })
    }

    /// The shipped configuration: the compiled first-party release key is the
    /// only root. Tests and tools that need another root use [`Revocations::new`].
    ///
    /// # Errors
    /// [`RevocationError::RootKey`] when the compiled key does not parse, so no
    /// list can verify, and [`RevocationError::Clock`] for a malformed `now`.
    pub fn with_compiled_root(
        dir: impl Into<PathBuf>,
        source: Reference,
        now: &str,
    ) -> Result<Self, RevocationError> {
        Self::with_root_text(RELEASE_KEY_FILE, dir, source, now)
    }

    fn with_root_text(
        key_file: &str,
        dir: impl Into<PathBuf>,
        source: Reference,
        now: &str,
    ) -> Result<Self, RevocationError> {
        let root =
            release_key_from(key_file).map_err(|e| RevocationError::RootKey(e.to_string()))?;
        Self::new(dir, vec![root], source, now)
    }

    /// The root keys that verify a list.
    #[must_use]
    pub fn roots(&self) -> &[PublicKey] {
        &self.roots
    }

    /// The cache file.
    #[must_use]
    pub fn cache_file(&self) -> PathBuf {
        self.dir.join(CACHE_FILE)
    }

    /// Take the exclusive cache lock, waiting for another holder. A refresh
    /// takes it itself; this is public for callers that need the cache to
    /// stay put across several steps.
    ///
    /// # Errors
    /// [`RevocationError::Io`] when the lock file cannot be created or locked.
    pub fn lock(&self) -> Result<CacheLock, RevocationError> {
        create_private_dir(&self.dir).map_err(io_err(RevokePhrase::CreateDir.as_static()))?;
        let file = OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .open(self.dir.join(LOCK_FILE))
            .map_err(io_err(RevokePhrase::OpenLock.as_static()))?;
        file.lock()
            .map_err(io_err(RevokePhrase::LockCache.as_static()))?;
        Ok(CacheLock { _file: file })
    }

    /// The cached list, for offline runs and every spawn. Never uses the network.
    ///
    /// # Errors
    /// [`RevocationError::CacheInvalid`] when the cache exists but does not
    /// hold a list a root key signed.
    pub fn cached(&self) -> Result<Current, RevocationError> {
        let Some((list, fetched_at)) = self.read_cache()? else {
            return Ok(Current {
                list: RevocationList::default(),
                fetched_at: None,
                notices: vec![RevocationNotice::Missing],
            });
        };
        let notices = if list.expired_at(self.now_at) {
            vec![RevocationNotice::Stale {
                issued: list.issued().unwrap_or_default().to_owned(),
                expires: list.expires().unwrap_or_default().to_owned(),
            }]
        } else {
            vec![]
        };
        Ok(Current {
            list,
            fetched_at: Some(fetched_at),
            notices,
        })
    }

    /// Fetch, verify and cache the list. A damaged cache is replaced.
    ///
    /// # Errors
    /// [`RevocationError::Fetch`] when the registry fails or withholds the
    /// list, [`RevocationError::Expired`] for a list past its signed
    /// `expires`, the verification errors of [`RevocationList::verify`],
    /// [`RevocationError::Rollback`] for a list older than the cache,
    /// [`RevocationError::Equivocation`] for a different list with the
    /// cache's `issued` time, and
    /// cache write failures. The cache is unchanged on any error.
    pub fn refresh(&self, client: &Client) -> Result<Current, RevocationError> {
        let (statement, minisig) = self.fetch(client)?;
        let list = RevocationList::verify(&statement, &minisig, &self.roots)?;
        if list.expired_at(self.now_at) {
            return Err(RevocationError::Expired {
                expires: list.expires().unwrap_or_default().to_owned(),
            });
        }
        let statement = String::from_utf8(statement)
            .map_err(|_| RevocationError::Invalid(RevokePhrase::NotUtf8.as_static().into()))?;

        // Re-read, compare and replace as one step under the lock.
        let _lock = self.lock()?;
        if let Ok(Some((cached, _))) = self.read_cache()
            && let (Some(old), Some(new)) = (cached.issued(), list.issued())
        {
            let (old_at, new_at) = (utc_seconds(old), utc_seconds(new));
            if new_at < old_at {
                return Err(RevocationError::Rollback {
                    cached: old.to_owned(),
                    fetched: new.to_owned(),
                });
            }
            // One canonical encoding per list, so equal fields mean equal bytes.
            if new_at == old_at && cached != list {
                return Err(RevocationError::Equivocation {
                    issued: new.to_owned(),
                });
            }
        }
        self.write_cache(&CacheDoc {
            schema_version: 1,
            fetched_at: self.now.clone(),
            statement,
            minisig,
        })?;
        Ok(Current {
            list,
            fetched_at: Some(self.now.clone()),
            notices: vec![],
        })
    }

    fn fetch(&self, client: &Client) -> Result<(Vec<u8>, String), RevocationError> {
        let layout = |why: &str| RevocationError::Layout(why.to_owned());
        let manifest = client.fetch_manifest(&self.source)?.manifest()?;
        if manifest.artifact_type.as_deref() != Some(ARTIFACT_TYPE_REVOCATIONS) {
            return Err(layout(RevokePhrase::ArtifactType.as_static()));
        }
        let [a, b] = manifest.layers.as_slice() else {
            return Err(layout(RevokePhrase::LayerCount.as_static()));
        };
        let (list, sig) = match (a.media_type.as_str(), b.media_type.as_str()) {
            (MEDIA_REVOCATIONS, MEDIA_MINISIG) => (a, b),
            (MEDIA_MINISIG, MEDIA_REVOCATIONS) => (b, a),
            _ => return Err(layout(RevokePhrase::LayerTypes.as_static())),
        };
        if list.size > MAX_LIST_BYTES as u64 {
            return Err(RevocationError::TooLarge);
        }
        let statement = client.fetch_blob_bytes(&self.source, list, MAX_LIST_BYTES as u64)?;
        let sig = client.fetch_blob_bytes(&self.source, sig, MAX_MINISIG_BYTES)?;
        let sig = String::from_utf8(sig).map_err(|_| RevocationError::BadSignature)?;
        Ok((statement, sig))
    }

    fn read_cache(&self) -> Result<Option<(RevocationList, String)>, RevocationError> {
        let path = self.cache_file();
        let invalid = |why: String| RevocationError::CacheInvalid {
            path: path.clone(),
            why,
        };
        let file = match File::open(&path) {
            Ok(f) => f,
            Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(invalid(e.to_string())),
        };
        let mut raw = Vec::new();
        file.take(MAX_CACHE_BYTES + 1)
            .read_to_end(&mut raw)
            .map_err(|e| invalid(e.to_string()))?;
        if raw.len() as u64 > MAX_CACHE_BYTES {
            return Err(invalid(RevokePhrase::CacheTooLarge.as_static().into()));
        }
        let doc: CacheDoc = serde_json::from_slice(&raw).map_err(|e| invalid(e.to_string()))?;
        if doc.schema_version != 1 || utc_seconds(&doc.fetched_at).is_none() {
            return Err(invalid(RevokePhrase::CacheSchema.as_static().into()));
        }
        let list = RevocationList::verify(doc.statement.as_bytes(), &doc.minisig, &self.roots)
            .map_err(|e| invalid(raw_reason(e)))?;
        Ok(Some((list, doc.fetched_at)))
    }

    fn write_cache(&self, doc: &CacheDoc) -> Result<(), RevocationError> {
        create_private_dir(&self.dir).map_err(io_err(RevokePhrase::CreateDir.as_static()))?;
        let bytes = serde_json::to_vec(doc).map_err(|e| RevocationError::Io {
            what: RevokePhrase::EncodeCache.as_static().into(),
            source: io::Error::other(e),
        })?;
        let mut tmp = tempfile::Builder::new()
            .prefix(".revocations-")
            .tempfile_in(&self.dir)
            .map_err(io_err(RevokePhrase::TempCache.as_static()))?;
        set_private_file(tmp.path()).map_err(io_err(RevokePhrase::SecureCache.as_static()))?;
        tmp.write_all(&bytes)
            .map_err(io_err(RevokePhrase::WriteCache.as_static()))?;
        tmp.as_file()
            .sync_all()
            .map_err(io_err(RevokePhrase::SyncCache.as_static()))?;
        tmp.persist(self.cache_file())
            .map_err(|e| RevocationError::Io {
                what: RevokePhrase::ReplaceCache.as_static().into(),
                source: e.error,
            })?;
        Ok(())
    }
}

#[cfg(unix)]
fn create_private_dir(dir: &Path) -> io::Result<()> {
    use std::os::unix::fs::{DirBuilderExt, PermissionsExt};
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(dir)?;
    fs::set_permissions(dir, fs::Permissions::from_mode(0o700))
}

#[cfg(not(unix))]
fn create_private_dir(dir: &Path) -> io::Result<()> {
    fs::create_dir_all(dir)
}

#[cfg(unix)]
fn set_private_file(path: &Path) -> io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(0o600))
}

#[cfg(not(unix))]
#[allow(clippy::unnecessary_wraps)]
fn set_private_file(_: &Path) -> io::Result<()> {
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_malformed_compiled_root_builds_no_revocations() {
        let source = Reference::parse("127.0.0.1:9/slopvac/revocations:latest").unwrap();
        for text in [
            "",
            "untrusted comment: x\n",
            "untrusted comment: x\nnot-a-key\n",
        ] {
            let r =
                Revocations::with_root_text(text, "unused", source.clone(), "2026-11-01T00:00:00Z");
            assert!(matches!(r, Err(RevocationError::RootKey(_))), "{text:?}");
        }
    }
}

#[cfg(test)]
mod refusal_code_tests {
    use super::*;

    #[test]
    fn a_helper_refusal_during_the_list_fetch_keeps_its_code() {
        let refusal = OciError::HelperUntrusted {
            program: "docker-credential-x".into(),
            dir: "tools".into(),
        };
        assert_eq!(
            RevocationError::Fetch(refusal).code(),
            "credential-helper-untrusted"
        );
    }

    #[test]
    fn another_fetch_failure_stays_revocation_list_unavailable() {
        let err = RevocationError::Fetch(OciError::NotFound("list".into()));
        assert_eq!(err.code(), "revocation-list-unavailable");
    }
}
