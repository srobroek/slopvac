//! `slopvac plugins update`: move the lock to the newest versions the config
//! ranges allow (contract: `docs/contract/plugins.md` section 7; threat model
//! sections 5 and 6.5; policies.md exit codes).
//!
//! This module is a library. The CLI (`slopvac-8l4.12`) reads the config
//! ranges, builds an [`Updater`] and prints the [`UpdateReport`].
//!
//! # What update does
//!
//! Update needs the network. Offline it fails with [`UpdateError::Offline`]
//! (exit 2) before it reads anything, because it has nothing to resolve from.
//! It never prompts and never touches the trust store: a new version is
//! content the user has not reviewed, so `plugins trust` stays a separate step
//! (a pack that needs re-trust is refused at spawn, not here).
//!
//! Online, it gets the revocation list ([`Revocations::refresh`]), then for each
//! OCI entry in scope:
//!
//! 1. lists the repository's semver tags (tags that fail the OCI tag grammar are skipped; one listing per repository) and picks the
//!    highest version the config range allows ([`outdated`]);
//! 2. fetches that version's manifest and takes its digest from the bytes;
//! 3. verifies the signed statement under the [`KeyPolicy`], with the lock's
//!    version and `notBefore` as the rollback floor (threat model K1-K3), so a
//!    statement older than the lock is refused. An entry that has no signature
//!    yet has no floor, which lets `update` sign it after the user pins a key;
//! 4. refuses an artifact digest or a signing key on the revocation list (K5).
//!
//! A refusal is per pack: the other packs still update and the report names the
//! reason ([`Outcome::Refused`]), and the exit code is 2. Entries that are not
//! OCI sources, or have no range, are left as they are. A newer version the
//! range excludes is never taken; the report names it
//! ([`PackUpdate::outside_range`]).
//!
//! The new lock is written in canonical form through a temporary file and a
//! rename, only when it differs from the file, so a second run changes nothing.
//! The lock is `.slopvac/plugins.lock` under the project root. Update reaches it
//! through a directory handle that never follows a link, reads at most 1 MiB,
//! and holds an exclusive lock on a guard file ([`GUARD_PATH`]) from read to
//! write.
//! Update does not extract anything; `plugins sync` installs the new lock.
//!
//! `slopvac_api` and `requires` are carried over from the old entry.
// STUB(slopvac-8l4.9.36): the new version's values come from its pack manifest,
// and no manifest reader exists yet. Until the swap lands, an update that
// changes them needs a hand edit of the lock.

use std::collections::BTreeMap;
use std::ffi::OsStr;
use std::io::ErrorKind;
use std::path::Path;
use std::str::FromStr;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use cap_fs_ext::{DirExt, FollowSymlinks, OpenOptionsFollowExt};
use cap_std::ambient_authority;
use cap_std::fs::{Dir, OpenOptions};
use thiserror::Error;

use crate::apply::ApplyError;
use crate::apply::fs::{self, Current, Expect, nonblocking};

use crate::lock::{
    LockError, LockedPack, Lockfile, MAX_LOCK_BYTES, PackId, Signature, Source, SourceKind,
    Version, VersionReq, outdated,
};
use crate::messages::sync::{self as messages, SyncPhrase};
use crate::oci::{Client, MEDIA_MANIFEST, Reference, Target, valid_tag};
use crate::revoke::{RevocationError, RevocationList, RevocationNotice, Revocations};
use crate::sign::{Expectation, KeyPolicy, MEDIA_MINISIG, MEDIA_STATEMENT, fetch_and_verify};
use crate::sync::{ARTIFACT_TYPE_PACK, MEDIA_PACK_LAYER, Network, SyncError};

/// The lock file, relative to the project root.
pub const LOCK_PATH: &str = ".slopvac/plugins.lock";
/// How long update waits for the guard lock before it gives up.
pub const GUARD_TIMEOUT: Duration = Duration::from_secs(30);
/// The guard file next to the lock. An exclusive lock on it serialises updates.
/// It stays after the run; keep it out of version control.
pub const GUARD_PATH: &str = ".slopvac/plugins.lock.guard";
const LOCK_DIR: &str = ".slopvac";
const LOCK_NAME: &str = "plugins.lock";
const GUARD_NAME: &str = "plugins.lock.guard";

/// Why update could not run at all. Every variant makes the command exit 2.
/// A refusal of one pack is not an error; see [`Outcome::Refused`].
#[derive(Debug, Error)]
pub enum UpdateError {
    /// Offline mode. Update has no cache to resolve from.
    #[error("{}", crate::messages::offline_network_needed("plugins update"))]
    Offline,
    /// Another update holds the guard lock and did not release it in time.
    #[error("{}", messages::update_busy(path, timeout.as_secs_f32()))]
    Busy {
        /// The guard file.
        path: String,
        /// How long update waited.
        timeout: Duration,
    },
    /// Windows: the replacement primitive resolves paths in a way a junction
    /// swap can redirect, so lock writes are refused (as in [`crate::apply`]).
    #[error("{}", messages::unsupported_on_windows(.0))]
    UnsupportedOnWindows(String),
    /// A named plugin is not in the lock.
    #[error("{}", messages::update_unknown_plugin(.0))]
    UnknownPlugin(PackId),
    /// The lock file is unreadable, too large or invalid.
    #[error("{}", messages::update_lock_file(path, message))]
    Lock {
        /// The file.
        path: String,
        /// What is wrong.
        message: String,
    },
    /// The revocation list could not be fetched or verified.
    #[error(transparent)]
    Revocation(#[from] RevocationError),
    /// The new lock could not be written.
    #[error("{}", messages::update_write(path, source))]
    Write {
        /// The file.
        path: String,
        /// The cause.
        #[source]
        source: std::io::Error,
    },
}

impl UpdateError {
    /// The exit code. Slopvac uses no other failing code for an incomplete run.
    #[must_use]
    pub fn exit_code(&self) -> u8 {
        2
    }

    /// The stable error code of the contract (policies.md, section 1.3), where
    /// one exists.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Offline => "offline-network-needed",
            Self::UnknownPlugin(_) => "update-plugin-unknown",
            Self::Busy { .. } => "update-lock-busy",
            Self::UnsupportedOnWindows(_) => "unsupported-on-windows",
            Self::Revocation(e) => e.code(),
            _ => "update-failed",
        }
    }
}

/// What update did with one pack.
#[derive(Debug)]
pub enum Outcome {
    /// The lock entry moved to a newer version.
    Updated {
        /// The new version.
        to: Version,
    },
    /// Nothing newer in range (or the entry is not in scope).
    Unchanged,
    /// A newer in-range version exists but failed a check. The old entry stays.
    Refused(SyncError),
}

/// The result for one pack.
#[derive(Debug)]
pub struct PackUpdate {
    /// Pack id.
    pub id: PackId,
    /// The version the lock held before.
    pub locked: Version,
    /// What happened.
    pub outcome: Outcome,
    /// The newest stable version above the lock that the range excludes, when
    /// it is newer than what update chose. Changing the range is up to the user.
    pub outside_range: Option<Version>,
}

/// What update did, sorted by pack id.
#[derive(Debug, Default)]
pub struct UpdateReport {
    /// One entry per pack in scope.
    pub packs: Vec<PackUpdate>,
    /// Revocation-list notices. They do not fail the run.
    pub notices: Vec<RevocationNotice>,
    /// Whether the lock file was rewritten.
    pub wrote_lock: bool,
}

impl UpdateReport {
    /// 2 when any pack was refused, otherwise 0.
    #[must_use]
    pub fn exit_code(&self) -> u8 {
        if self
            .packs
            .iter()
            .any(|p| matches!(p.outcome, Outcome::Refused(_)))
        {
            2
        } else {
            0
        }
    }
}

type GuardWaitHook = Arc<dyn Fn() + Send + Sync>;

/// Resolves newer pack versions and rewrites the lock.
pub struct Updater<'a> {
    network: Network<'a>,
    policy: &'a KeyPolicy,
    revocations: &'a Revocations,
    guard_timeout: Duration,
    listing_budget: u64,
    guard_wait_hook: Option<GuardWaitHook>,
}

impl<'a> Updater<'a> {
    /// `policy` carries the keys; `revocations` says where the revocation list
    /// comes from and is cached.
    #[must_use]
    pub fn new(network: Network<'a>, policy: &'a KeyPolicy, revocations: &'a Revocations) -> Self {
        Self {
            network,
            policy,
            revocations,
            guard_timeout: GUARD_TIMEOUT,
            listing_budget: LISTING_BUDGET_BYTES,
            guard_wait_hook: None,
        }
    }

    /// Test seam: `hook` runs each time update finds the guard held and is
    /// about to wait. Not part of the supported API.
    #[doc(hidden)]
    #[must_use]
    pub fn with_guard_wait_hook(mut self, hook: impl Fn() + Send + Sync + 'static) -> Self {
        self.guard_wait_hook = Some(Arc::new(hook));
        self
    }

    /// Reads at most `bytes` of tag lists per run (default
    /// [`LISTING_BUDGET_BYTES`]).
    #[must_use]
    pub fn with_listing_budget(mut self, bytes: u64) -> Self {
        self.listing_budget = bytes;
        self
    }

    /// Waits at most `timeout` for the guard lock (default [`GUARD_TIMEOUT`]).
    #[must_use]
    pub fn with_guard_timeout(mut self, timeout: Duration) -> Self {
        self.guard_timeout = timeout;
        self
    }

    /// Updates `.slopvac/plugins.lock` under `project_root`.
    ///
    /// All lock I/O goes through a directory handle for the project root and
    /// never follows a link: a `.slopvac` directory or lock file that is a
    /// link, or a lock that is not a regular file, is refused. The lock is read
    /// with a 1 MiB cap. An exclusive lock on [`GUARD_PATH`] is held from the
    /// read to the write, so two updates cannot lose each other's changes; the
    /// write also checks that the lock still holds the bytes that were read.
    ///
    /// `ranges` are the config version requirements by pack id; a pack with no
    /// range stays as it is. `only` limits the run to the named packs; an empty
    /// slice means every pack.
    ///
    /// # Errors
    /// An [`UpdateError`] when the run cannot start or finish; a pack that
    /// fails a check is reported in the [`UpdateReport`] instead.
    pub fn update(
        &self,
        project_root: &Path,
        ranges: &BTreeMap<PackId, VersionReq>,
        only: &[PackId],
    ) -> Result<UpdateReport, UpdateError> {
        self.update_on(project_root, ranges, only, cfg!(windows))
    }

    /// Test seam for [`Updater::update`]: pretend to run on `windows` (or
    /// not). Not part of the supported API.
    #[doc(hidden)]
    pub fn update_seam(
        &self,
        project_root: &Path,
        ranges: &BTreeMap<PackId, VersionReq>,
        only: &[PackId],
        windows: bool,
    ) -> Result<UpdateReport, UpdateError> {
        self.update_on(project_root, ranges, only, windows)
    }

    fn update_on(
        &self,
        project_root: &Path,
        ranges: &BTreeMap<PackId, VersionReq>,
        only: &[PackId],
        windows: bool,
    ) -> Result<UpdateReport, UpdateError> {
        let Network::Online(client) = self.network else {
            return Err(UpdateError::Offline);
        };
        let shown = project_root.join(LOCK_PATH).display().to_string();
        let lock_error = |message: String| UpdateError::Lock {
            path: shown.clone(),
            message,
        };
        let dir = open_lock_dir(project_root).map_err(|e| lock_error(e.to_string()))?;
        let _guard = match take_guard(&dir, self.guard_timeout, self.guard_wait_hook.as_deref()) {
            Ok(guard) => guard,
            Err(GuardError::Busy) => {
                return Err(UpdateError::Busy {
                    path: project_root.join(GUARD_PATH).display().to_string(),
                    timeout: self.guard_timeout,
                });
            }
            Err(GuardError::Refused(e)) => return Err(lock_error(e.to_string())),
        };
        let text = read_lock(&dir, &shown).map_err(|e| lock_error(e.to_string()))?;
        let lock = Lockfile::parse(&text).map_err(|e: LockError| lock_error(e.to_string()))?;
        if let Some(missing) = only.iter().find(|id| lock.get(id).is_none()) {
            return Err(UpdateError::UnknownPlugin(missing.clone()));
        }
        let current = self.revocations.refresh(client)?;

        let in_scope = |pack: &&LockedPack| only.is_empty() || only.contains(&pack.id);
        let Listed {
            mut results,
            repos,
            available,
        } = list_candidates(client, &lock, ranges, in_scope, self.listing_budget);
        let newer = outdated(&lock, ranges, &available);

        let mut report = UpdateReport {
            notices: current.notices,
            ..UpdateReport::default()
        };
        let mut next: Vec<LockedPack> = lock.packs().to_vec();
        for pack in lock.packs().iter().filter(in_scope) {
            let found = newer.iter().find(|o| o.id == pack.id);
            let target = found.and_then(|o| o.update.clone());
            let outside_range = found.and_then(|o| {
                o.newest
                    .clone()
                    .filter(|n| *n > o.update.clone().unwrap_or_else(|| pack.version.clone()))
            });
            let outcome = if let Some(e) = results.remove(&pack.id) {
                Outcome::Refused(e)
            } else if let (Some(version), Some(repo)) = (target, repos.get(&pack.id)) {
                match resolve(client, self.policy, &current.list, pack, repo, &version) {
                    Ok(entry) => {
                        if let Some(slot) = next.iter_mut().find(|p| p.id == pack.id) {
                            *slot = entry;
                        }
                        Outcome::Updated { to: version }
                    }
                    Err(e) => Outcome::Refused(e),
                }
            } else {
                Outcome::Unchanged
            };
            report.packs.push(PackUpdate {
                id: pack.id.clone(),
                locked: pack.version.clone(),
                outcome,
                outside_range,
            });
        }

        let updated = Lockfile::new(next).map_err(|e| lock_error(e.to_string()))?;
        let canonical = updated.to_toml();
        if canonical != text {
            if windows {
                return Err(UpdateError::UnsupportedOnWindows(shown));
            }
            fs::replace_bounded(
                &dir,
                OsStr::new(LOCK_NAME),
                &shown,
                &Expect::Bytes(text.as_bytes()),
                canonical.as_bytes(),
                &mut |_| {},
            )
            .map_err(|e| UpdateError::Write {
                path: shown.clone(),
                source: std::io::Error::other(e.to_string()),
            })?;
            report.wrote_lock = true;
        }
        Ok(report)
    }
}

/// What listing the registries found, by pack id.
struct Listed {
    /// Packs whose listing failed.
    results: BTreeMap<PackId, SyncError>,
    repos: BTreeMap<PackId, Reference>,
    available: BTreeMap<PackId, Vec<Version>>,
}

/// Most tag bytes update reads from registries in one run.
pub const LISTING_BUDGET_BYTES: u64 = 64 << 20;

/// Lists each distinct repository once and keeps at most two versions per pack:
/// the highest in range and the highest stable one. The full tag list is
/// dropped as soon as the packs of its repository are reduced.
///
/// Tags that fail the OCI tag grammar (including its 128-byte limit) are
/// skipped before they reach semver parsing. The tag bytes read across all
/// repositories count against `budget`; past it, the remaining packs are
/// refused.
fn list_candidates(
    client: &Client,
    lock: &Lockfile,
    ranges: &BTreeMap<PackId, VersionReq>,
    in_scope: impl Fn(&&LockedPack) -> bool,
    budget: u64,
) -> Listed {
    let mut listed = Listed {
        results: BTreeMap::new(),
        repos: BTreeMap::new(),
        available: BTreeMap::new(),
    };
    let mut groups: BTreeMap<(String, String), Vec<(&LockedPack, Reference)>> = BTreeMap::new();
    for pack in lock.packs().iter().filter(in_scope) {
        let SourceKind::Oci(text) = pack.source.kind() else {
            continue;
        };
        if !ranges.contains_key(&pack.id) {
            continue;
        }
        match reference_of(pack, text) {
            Ok(r) => groups
                .entry((r.registry.clone(), r.repository.clone()))
                .or_default()
                .push((pack, r)),
            Err(e) => {
                listed.results.insert(pack.id.clone(), e);
            }
        }
    }
    let allowance = AtomicU64::new(budget);
    for packs in groups.into_values() {
        let fail = |pack: &LockedPack, why: SyncErrorKind| match why {
            SyncErrorKind::Fetch(source) => SyncError::Fetch {
                id: pack.id.clone(),
                source,
            },
            SyncErrorKind::Budget => SyncError::Source {
                id: pack.id.clone(),
                why: messages::update_budget(budget),
            },
        };
        let tags = client
            .list_tags_within(&packs[0].1, &allowance)
            .map_err(|e| {
                if allowance.load(Ordering::Relaxed) == 0 {
                    SyncErrorKind::Budget
                } else {
                    SyncErrorKind::Fetch(e)
                }
            });
        let tags = match tags {
            Ok(tags) => tags,
            Err(why) => {
                for (pack, _) in &packs {
                    listed
                        .results
                        .insert(pack.id.clone(), fail(pack, why.clone()));
                }
                continue;
            }
        };
        let versions: Vec<Version> = tags
            .iter()
            .filter(|t| valid_tag(t))
            .filter_map(|t| Version::parse(t).ok())
            .filter(|v| v.build.is_empty())
            .collect();
        drop(tags);
        for (pack, reference) in packs {
            let Some(req) = ranges.get(&pack.id) else {
                continue;
            };
            let newer = || versions.iter().filter(|v| **v > pack.version);
            let best = newer().filter(|v| req.matches(v)).max().cloned();
            let newest = newer().filter(|v| v.pre.is_empty()).max().cloned();
            let mut kept: Vec<Version> = best.into_iter().chain(newest).collect();
            kept.sort();
            kept.dedup();
            listed.repos.insert(pack.id.clone(), reference);
            listed.available.insert(pack.id.clone(), kept);
        }
    }
    listed
}

#[derive(Clone)]
enum SyncErrorKind {
    Fetch(crate::oci::OciError),
    Budget,
}

/// Opens `.slopvac` under the project root without following links.
fn open_lock_dir(project_root: &Path) -> Result<Dir, ApplyError> {
    let root = Dir::open_ambient_dir(project_root, ambient_authority())
        .map_err(|e| ApplyError::io(project_root.display(), &e))?;
    root.open_dir_nofollow(LOCK_DIR)
        .map_err(|e| ApplyError::PathRefused(messages::update_lock_dir(LOCK_DIR, &e)))
}

enum GuardError {
    Busy,
    Refused(ApplyError),
}

impl From<ApplyError> for GuardError {
    fn from(e: ApplyError) -> Self {
        Self::Refused(e)
    }
}

/// Takes the exclusive guard lock, waiting at most `timeout`; it is released
/// when the file is dropped.
///
/// The file is created private (0600). An existing one must be a plain file
/// that the current user owns and that grants nothing to group or others,
/// checked on the open handle: another user who could open it could also lock
/// it and stall every update.
fn take_guard(
    dir: &Dir,
    timeout: Duration,
    on_wait: Option<&(dyn Fn() + Send + Sync)>,
) -> Result<std::fs::File, GuardError> {
    let name = OsStr::new(GUARD_NAME);
    match dir.symlink_metadata(name) {
        Ok(m) if !m.is_file() => return Err(ApplyError::NotRegularFile(GUARD_PATH.into()).into()),
        Ok(_) => {}
        Err(e) if e.kind() == ErrorKind::NotFound => {}
        Err(e) => return Err(ApplyError::io(GUARD_PATH, &e).into()),
    }
    let mut opts = OpenOptions::new();
    opts.write(true).create(true).follow(FollowSymlinks::No);
    #[cfg(unix)]
    {
        use cap_std::fs::OpenOptionsExt;
        opts.mode(0o600);
    }
    nonblocking(&mut opts)?;
    let file = dir
        .open_with(name, &opts)
        .map_err(|e| ApplyError::io(GUARD_PATH, &e))?;
    let meta = file
        .metadata()
        .map_err(|e| ApplyError::io(GUARD_PATH, &e))?;
    if !meta.is_file() {
        return Err(ApplyError::NotRegularFile(GUARD_PATH.into()).into());
    }
    #[cfg(unix)]
    {
        use cap_std::fs::MetadataExt;
        let me = rustix::process::getuid().as_raw();
        if meta.uid() != me || meta.mode() & 0o077 != 0 {
            return Err(ApplyError::PathRefused(messages::update_guard_private(GUARD_PATH)).into());
        }
    }
    let file = file.into_std();
    let deadline = Instant::now() + timeout;
    loop {
        match file.try_lock() {
            Ok(()) => return Ok(file),
            Err(std::fs::TryLockError::WouldBlock) => {
                if let Some(hook) = on_wait {
                    hook();
                }
                if Instant::now() >= deadline {
                    return Err(GuardError::Busy);
                }
                std::thread::sleep(Duration::from_millis(10));
            }
            Err(std::fs::TryLockError::Error(e)) => {
                return Err(ApplyError::io(GUARD_PATH, &e).into());
            }
        }
    }
}

fn read_lock(dir: &Dir, shown: &str) -> Result<String, ApplyError> {
    let max = MAX_LOCK_BYTES as u64;
    let bytes = match fs::read_current_limited(dir, OsStr::new(LOCK_NAME), shown, max)? {
        Current::File(bytes) => bytes,
        Current::Absent => return Err(ApplyError::Io(messages::update_lock_missing(LOCK_PATH))),
    };
    String::from_utf8(bytes).map_err(|_| ApplyError::Io(messages::update_lock_not_utf8(LOCK_PATH)))
}

fn reference_of(pack: &LockedPack, text: &str) -> Result<Reference, SyncError> {
    Reference::parse(text.strip_prefix("oci://").unwrap_or(text)).map_err(|source| {
        SyncError::Fetch {
            id: pack.id.clone(),
            source,
        }
    })
}

/// Fetches, verifies and checks `version` of `pack`; returns the new entry.
fn resolve(
    client: &Client,
    policy: &KeyPolicy,
    revoked: &RevocationList,
    pack: &LockedPack,
    repository: &Reference,
    version: &Version,
) -> Result<LockedPack, SyncError> {
    let id = &pack.id;
    let layout = |why: &str| SyncError::Layout {
        id: id.clone(),
        why: why.to_owned(),
    };
    let fetch = |source| SyncError::Fetch {
        id: id.clone(),
        source,
    };
    let tag = version.to_string();
    let fetched = client
        .fetch_manifest(&repository.with_target(Target::Tag(tag.clone())))
        .map_err(fetch)?;
    if fetched.media_type != MEDIA_MANIFEST {
        return Err(layout(SyncPhrase::ManifestNotImage.as_static()));
    }
    if revoked.revokes_digest(fetched.digest.as_str()) {
        return Err(SyncError::Revoked {
            id: id.clone(),
            what: messages::revoked_artifact(&fetched.digest),
        });
    }
    let manifest = fetched
        .manifest()
        .map_err(|e| layout(&messages::manifest_parse(&e)))?;
    let mut payload = manifest
        .layers
        .iter()
        .filter(|l| l.media_type != MEDIA_STATEMENT && l.media_type != MEDIA_MINISIG);
    let (Some(layer), None) = (payload.next(), payload.next()) else {
        return Err(layout(SyncPhrase::OneLayer.as_static()));
    };
    if layer.media_type != MEDIA_PACK_LAYER {
        return Err(layout(SyncPhrase::LayerNotArchive.as_static()));
    }

    let namespace = repository.repository.split('/').next().unwrap_or_default();
    let by_digest = repository.with_target(Target::Digest(fetched.digest.clone()));
    let locked_version = pack.version.to_string();
    let expect = Expectation {
        id: id.as_str(),
        namespace,
        version: &tag,
        artifact_type: ARTIFACT_TYPE_PACK,
        floor: pack
            .signature
            .as_ref()
            .map(|s| (locked_version.as_str(), s.not_before.as_str())),
        allow_downgrade: false,
    };
    let verified =
        fetch_and_verify(client, &by_digest, &manifest, policy, &expect).map_err(|source| {
            SyncError::Sign {
                id: id.clone(),
                source,
            }
        })?;
    let key_id = verified.key().key_id();
    if revoked.revokes_key(&key_id) {
        return Err(SyncError::Revoked {
            id: id.clone(),
            what: messages::revoked_key(&key_id),
        });
    }

    let source_text = match &repository.target {
        Target::Digest(_) => format!(
            "oci://{}/{}@{}",
            repository.registry, repository.repository, fetched.digest
        ),
        Target::Tag(_) => format!(
            "oci://{}/{}:{tag}",
            repository.registry, repository.repository
        ),
    };
    let invalid = |why: String| SyncError::Source {
        id: id.clone(),
        why,
    };
    Ok(LockedPack {
        version: version.clone(),
        source: Source::from_str(&source_text).map_err(|e| invalid(e.to_string()))?,
        digest: fetched
            .digest
            .as_str()
            .parse()
            .map_err(|e: crate::lock::ValueError| invalid(e.to_string()))?,
        signature: Some(Signature {
            key_id: key_id
                .parse()
                .map_err(|e: crate::lock::ValueError| invalid(e.to_string()))?,
            not_before: verified
                .statement()
                .not_before
                .parse()
                .map_err(|e: crate::lock::ValueError| invalid(e.to_string()))?,
        }),
        ..pack.clone()
    })
}
