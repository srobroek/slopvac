//! The messages of sync, the plugins lock and `plugins update`.
//!
//! [`SyncMessage`] has one entry per published error code of those areas. `sync-failed`,
//! `signature-invalid` and `update-failed` cover several failures, so their entries render the
//! wrapped sentence and each failure keeps its own [`SyncText`]. [`SyncText`] holds the
//! sentences with parameters, and [`SyncPhrase`] the fixed phrases that callers read as
//! `&'static str`. The helper functions apply the escaping that the text needs before it goes
//! into a catalog value, because the render does not escape.

use std::fmt::Display;
use std::path::Path;

use slopvac_messages::{Catalog, Entry};
use slopvac_sanitize::line as esc;

use crate::lock::{LockDiff, PackId};

/// The published error codes of sync, the lock and update.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum SyncMessage {
    /// Offline mode and the cache lacks content the lock needs.
    #[code("offline-plugin-missing")]
    #[message("offline: plugin `{id}` ({digest}) is not in the cache: {what}")]
    OfflinePluginMissing {
        id: String,
        digest: String,
        what: String,
    },
    /// The resolved plugins differ from the lock.
    #[code("lock-mismatch")]
    #[message("the lock does not match the resolved plugins:\n{diff}")]
    LockMismatch { diff: String },
    /// An installed tree changed and offline sync cannot fetch it again.
    #[code("cache-tampered")]
    #[message(
        "plugin `{id}`: the cached tree {path} was modified and was removed; offline sync cannot restore it"
    )]
    CacheTampered {
        id: String,
        #[display_path]
        path: String,
    },
    /// Fetched or read content does not hash to the locked digest.
    #[code("digest-mismatch")]
    #[message("plugin `{id}`: digest mismatch: the lock pins {expected}, the content is {actual}")]
    DigestMismatch {
        id: String,
        expected: String,
        actual: String,
    },
    /// The signature gate refused the artifact.
    #[code("signature-invalid")]
    #[message("{detail}")]
    SignatureInvalid { detail: String },
    /// A network or registry fetch failed and the source error has no code of its own.
    #[code("sync-fetch")]
    #[message("{detail}")]
    SyncFetch { detail: String },
    /// The lock has no signature for an OCI entry.
    #[code("sync-unsigned")]
    #[message("{detail}")]
    SyncUnsigned { detail: String },
    /// The revocation list names the artifact or its signing key.
    #[code("plugin-revoked")]
    #[message("plugin `{id}`: {what} is on the revocation list")]
    PluginRevoked { id: String, what: String },
    /// Any other failure of a sync, status or check.
    #[code("sync-failed")]
    #[message("{detail}")]
    SyncFailed { detail: String },
    /// Another update holds the guard lock.
    #[code("update-lock-busy")]
    #[message("another `plugins update` holds the lock on {path}; gave up after {secs} s")]
    UpdateLockBusy {
        #[display_path]
        path: String,
        secs: String,
    },
    /// The lock cannot be written on Windows.
    #[code("unsupported-on-windows")]
    #[message("`{path}`: writes are not supported on Windows yet; the lock was not changed")]
    UnsupportedOnWindows {
        #[display_path]
        path: String,
    },
    /// `plugins update` named a plugin that the lock does not list.
    #[code("update-plugin-unknown")]
    #[message("{detail}")]
    UpdatePluginUnknown { detail: String },
    /// Any other failure of `plugins update`.
    #[code("update-failed")]
    #[message("{detail}")]
    UpdateFailed { detail: String },
}

/// Sentences with parameters: failure detail, lock problems and update notices.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum SyncText {
    /// The lock entry cannot be resolved as written.
    #[code("plugins-sync-source")]
    #[text("plugin `{id}`: {why}")]
    Source { id: String, why: String },
    /// Fetching or exporting a pinned git commit failed.
    #[code("plugins-sync-git-source")]
    #[text("plugin `{id}`: git source: {why}")]
    GitSource { id: String, why: String },
    /// A git source passed a limit.
    #[code("plugins-sync-git-limit")]
    #[text("plugin `{id}`: git source passes a limit: {why}")]
    GitSourceLimit { id: String, why: String },
    /// A failure of a pack that carries the cause's own text.
    #[code("plugins-sync-plugin-cause")]
    #[text("plugin `{id}`: {cause}")]
    PluginCause { id: String, cause: String },
    /// The signature gate refused the artifact.
    #[code("plugins-sync-sign-failed")]
    #[text("plugin `{id}`: signature check failed: {cause}")]
    SignFailed { id: String, cause: String },
    /// An OCI entry has no signature in the lock.
    #[code("plugins-sync-unsigned")]
    #[text("plugin `{id}`: the lock has no signature for an OCI plugin; pin its key, then update")]
    Unsigned { id: String },
    /// The signed statement is not the one the lock records.
    #[code("plugins-sync-sign-differs")]
    #[text("plugin `{id}`: the signature differs from the lock: {why}")]
    SignDiffers { id: String, why: String },
    /// The manifest does not have the shape of a pack artifact.
    #[code("plugins-sync-layout")]
    #[text("plugin `{id}`: unexpected artifact layout: {why}")]
    Layout { id: String, why: String },
    /// The managed Python environment of a pack could not be built.
    #[code("plugins-sync-pack-env")]
    #[text("pack `{id}`: {cause}")]
    PackEnv { id: String, cause: String },
    /// The data directory could not be prepared or written.
    #[code("plugins-sync-data-dir")]
    #[text("data directory: {detail}")]
    DataDir { detail: String },
    /// The artifact digest in a revocation failure.
    #[code("plugins-sync-revoked-artifact")]
    #[text("artifact {digest}")]
    RevokedArtifact { digest: String },
    /// The publisher key in a revocation failure.
    #[code("plugins-sync-revoked-key")]
    #[text("publisher key {key_id}")]
    RevokedKey { key_id: String },
    /// A blob could not be opened.
    #[code("plugins-sync-opening")]
    #[text("opening {path}")]
    Opening {
        #[display_path]
        path: String,
    },
    /// The manifest is not valid JSON of the expected shape.
    #[code("plugins-sync-manifest-parse")]
    #[text("the manifest does not parse: {reason}")]
    ManifestParse { reason: String },
    /// The signing key differs from the one the lock records.
    #[code("plugins-sync-signed-key")]
    #[text("signed by key {actual}, the lock records {locked}")]
    SignedKey { actual: String, locked: String },
    /// The `notBefore` time differs from the one the lock records.
    #[code("plugins-sync-signed-not-before")]
    #[text("notBefore is {actual}, the lock records {locked}")]
    SignedNotBefore { actual: String, locked: String },
    /// The plugin launcher could not be located.
    #[code("plugins-sync-launcher-missing")]
    #[text("cannot find the launcher: {reason}")]
    LauncherMissing { reason: String },
    /// Hashing downloaded content failed.
    #[code("plugins-sync-hashing")]
    #[text("hashing: {reason}")]
    Hashing { reason: String },
    /// A path source could not be inspected.
    #[code("plugins-sync-path-io")]
    #[text("path source `{rel}`: {reason}")]
    PathIo {
        #[display_path]
        rel: String,
        reason: String,
    },
    /// A path source goes through a link.
    #[code("plugins-sync-path-link")]
    #[text("path source `{rel}` goes through a link")]
    PathLink {
        #[display_path]
        rel: String,
    },
    /// A path source leaves the project.
    #[code("plugins-sync-path-outside")]
    #[text("path source `{rel}` leaves the project")]
    PathOutside {
        #[display_path]
        rel: String,
    },
    /// A path source could not be read.
    #[code("plugins-sync-path-reading")]
    #[text("reading `{rel}`: {reason}")]
    PathReading {
        #[display_path]
        rel: String,
        reason: String,
    },
    /// A path source is larger than the archive limit.
    #[code("plugins-sync-path-too-large")]
    #[text("`{rel}` exceeds the archive size limit")]
    PathTooLarge {
        #[display_path]
        rel: String,
    },
    /// A newer version in the configured range is available.
    #[code("plugins-sync-notice-update")]
    #[text("plugin {id}: {version} is available (locked {locked}); run `slopvac plugins update`")]
    NoticeUpdate {
        id: String,
        version: String,
        locked: String,
    },
    /// A newer version outside the configured range is available.
    #[code("plugins-sync-notice-outside")]
    #[text(
        "plugin {id}: {version} is available but outside the configured range; change the range to use it"
    )]
    NoticeOutside { id: String, version: String },
    /// The store lock file is not a plain file.
    #[code("plugins-sync-not-plain-file")]
    #[text("{path} is not a plain file")]
    NotPlainFile {
        #[display_path]
        path: String,
    },
    /// The store lock file could not be opened.
    #[code("plugins-sync-store-lock-open")]
    #[text("opening the store lock: {reason}")]
    StoreLockOpen { reason: String },
    /// The store lock could not be taken.
    #[code("plugins-sync-store-lock-take")]
    #[text("taking the store lock: {reason}")]
    StoreLockTake { reason: String },
    /// The download file could not be created.
    #[code("plugins-sync-download-file")]
    #[text("creating a download file: {reason}")]
    DownloadFile { reason: String },
    /// A scratch directory could not be created.
    #[code("plugins-sync-scratch-dir")]
    #[text("creating a scratch directory: {reason}")]
    ScratchDir { reason: String },
    /// A finished download does not hash to the digest.
    #[code("plugins-sync-download-hash")]
    #[text("a download hashed to {actual}, not {digest}")]
    DownloadHash { actual: String, digest: String },
    /// A finished download could not be moved into place.
    #[code("plugins-sync-download-store")]
    #[text("storing a download: {reason}")]
    DownloadStore { reason: String },
    /// A download could not be written.
    #[code("plugins-sync-download-write")]
    #[text("writing a download: {reason}")]
    DownloadWrite { reason: String },
    /// The record of an install could not be written.
    #[code("plugins-sync-record-install")]
    #[text("recording an install: {reason}")]
    RecordInstall { reason: String },
    /// The repository download passed its size limit.
    #[code("plugins-sync-git-download-limit")]
    #[text("the repository download exceeds {max} bytes")]
    GitDownloadLimit {
        #[count]
        max: u64,
    },
    /// Reading the output of a git command failed.
    #[code("plugins-sync-git-reading")]
    #[text("reading `git {what}`: {reason}")]
    GitReading { what: String, reason: String },
    /// A git command printed more than the cap.
    #[code("plugins-sync-git-output-cap")]
    #[text("`git {what}` printed more than {cap} bytes")]
    GitOutputCap {
        what: String,
        #[count]
        cap: usize,
    },
    /// The commit holds more files than the limit.
    #[code("plugins-sync-git-too-many-files")]
    #[text("the commit has more than {max} files")]
    GitTooManyFiles {
        #[count]
        max: usize,
    },
    /// The commit holds a symbolic link.
    #[code("plugins-sync-git-symlink")]
    #[text("`{path}` is a symbolic link")]
    GitSymlink {
        #[display_path]
        path: String,
    },
    /// The commit holds a submodule.
    #[code("plugins-sync-git-submodule")]
    #[text("`{path}` is a submodule")]
    GitSubmodule {
        #[display_path]
        path: String,
    },
    /// The commit holds an entry with a mode a pack may not have.
    #[code("plugins-sync-git-mode")]
    #[text("`{path}` has the unsupported mode {mode}")]
    GitMode {
        #[display_path]
        path: String,
        mode: String,
    },
    /// The commit expands past the size limit.
    #[code("plugins-sync-git-expands")]
    #[text("the commit expands past the size limit of {max} bytes")]
    GitExpands {
        #[count]
        max: u64,
    },
    /// Reading the reply of `git cat-file` failed.
    #[code("plugins-sync-git-cat-file-read")]
    #[text("reading `git cat-file`: {reason}")]
    GitCatFileRead { reason: String },
    /// An object is missing or is not a file.
    #[code("plugins-sync-git-object-missing")]
    #[text("object {oid} is missing or is not a file")]
    GitObjectMissing { oid: String },
    /// The git process could not be started.
    #[code("plugins-sync-git-spawn")]
    #[text("cannot start git: {reason}")]
    GitSpawn { reason: String },
    /// A git command ran out of time.
    #[code("plugins-sync-git-timed-out")]
    #[text("`git {what}` timed out")]
    GitTimedOut { what: String },
    /// A git command was stopped.
    #[code("plugins-sync-git-stopped")]
    #[text("`git {what}` was stopped")]
    GitStopped { what: String },
    /// Waiting for a git command failed.
    #[code("plugins-sync-git-waiting")]
    #[text("waiting for `git {what}`: {reason}")]
    GitWaiting { what: String, reason: String },
    /// A git command exited with a failure status.
    #[code("plugins-sync-git-exit")]
    #[text("`git {what}` failed ({status}){detail}")]
    GitExit {
        what: String,
        status: String,
        detail: String,
    },
    /// The error output of a failed git command.
    #[code("plugins-sync-git-exit-detail")]
    #[text(": {text}")]
    GitExitDetail { text: String },
    /// A lock error with the place in the file.
    #[code("plugins-lock-error")]
    #[text("{pointer}: {message}")]
    LockError { pointer: String, message: String },
    /// A plugin id is too long.
    #[code("plugins-lock-id-too-long")]
    #[text("a plugin id is longer than {max} bytes")]
    IdTooLong {
        #[count]
        max: usize,
    },
    /// A plugin id has the wrong shape.
    #[code("plugins-lock-id-invalid")]
    #[text(
        "`{value}` is not a plugin id (lowercase letters, digits and `-`, starting with a letter)"
    )]
    IdInvalid { value: String },
    /// A digest has the wrong shape.
    #[code("plugins-lock-digest-invalid")]
    #[text("`{value}` is not a digest (`sha256:` and 64 lowercase hex digits)")]
    DigestInvalid { value: String },
    /// A key id has the wrong shape.
    #[code("plugins-lock-key-id-invalid")]
    #[text("`{value}` is not a key id (16 uppercase hex digits)")]
    KeyIdInvalid { value: String },
    /// A time has the wrong shape.
    #[code("plugins-lock-time-invalid")]
    #[text("`{value}` is not a UTC time (`YYYY-MM-DDTHH:MM:SSZ`, calendar-valid)")]
    TimeInvalid { value: String },
    /// A plugin kind is not `data` or `code`.
    #[code("plugins-lock-kind-invalid")]
    #[text("`{value}` is not a plugin kind (`data` or `code`)")]
    KindInvalid { value: String },
    /// A source is too long.
    #[code("plugins-lock-source-too-long")]
    #[text("a source is longer than {max} bytes")]
    SourceTooLong {
        #[count]
        max: usize,
    },
    /// The lock holds too many plugins.
    #[code("plugins-lock-too-many-plugins")]
    #[text("more than {max} plugins")]
    TooManyPlugins {
        #[count]
        max: usize,
    },
    /// The id `core` is reserved.
    #[code("plugins-lock-reserved")]
    #[text("`{id}` is reserved for the built-in plugin and is never locked")]
    Reserved { id: String },
    /// An id is locked twice.
    #[code("plugins-lock-locked-twice")]
    #[text("plugin id `{id}` is locked twice")]
    LockedTwice { id: String },
    /// A version has build metadata.
    #[code("plugins-lock-build-metadata")]
    #[text("`{version}` has build metadata")]
    BuildMetadata { version: String },
    /// A version is too long.
    #[code("plugins-lock-version-too-long")]
    #[text("longer than {max} bytes")]
    VersionTooLong {
        #[count]
        max: usize,
    },
    /// The API version is outside its range.
    #[code("plugins-lock-api-range")]
    #[text("must be between 1 and {max}")]
    ApiRange {
        #[count]
        max: u64,
    },
    /// A pack lists too many `requires` entries.
    #[code("plugins-lock-too-many-requires")]
    #[text("more than {max} entries")]
    TooManyRequires {
        #[count]
        max: usize,
    },
    /// A `requires` entry is listed twice.
    #[code("plugins-lock-listed-twice")]
    #[text("`{id}` is listed twice")]
    ListedTwice { id: String },
    /// The canonical text is larger than the limit.
    #[code("plugins-lock-canonical-too-large")]
    #[text("the canonical text is larger than {max} bytes")]
    CanonicalTooLarge {
        #[count]
        max: usize,
    },
    /// A resolved pack is not in the lock.
    #[code("plugins-lock-diff-added")]
    #[text("added: {id} {version} is not in the lock")]
    DiffAdded { id: String, version: String },
    /// A locked pack was not resolved.
    #[code("plugins-lock-diff-removed")]
    #[text("removed: {id} is locked but was not resolved")]
    DiffRemoved { id: String },
    /// The start of a changed pack.
    #[code("plugins-lock-diff-changed")]
    #[text("changed: {id}")]
    DiffChanged { id: String },
    /// A changed version.
    #[code("plugins-lock-diff-version")]
    #[text("version {locked} -> {resolved}")]
    DiffVersion { locked: String, resolved: String },
    /// A changed source.
    #[code("plugins-lock-diff-source")]
    #[text("source {locked} -> {resolved}")]
    DiffSource { locked: String, resolved: String },
    /// A changed digest.
    #[code("plugins-lock-diff-digest")]
    #[text("digest {locked} -> {resolved}")]
    DiffDigest { locked: String, resolved: String },
    /// A version comparator has the wrong shape.
    #[code("plugins-lock-comparator-invalid")]
    #[text("`{comparator}` is not a version comparator in `{text}`")]
    ComparatorInvalid { comparator: String, text: String },
    /// A version requirement does not parse.
    #[code("plugins-lock-req-invalid")]
    #[text("`{text}` is not a version requirement: {reason}")]
    ReqInvalid { text: String, reason: String },
    /// The lock holds a key the schema does not define.
    #[code("plugins-lock-unknown-key")]
    #[text("unknown key `{key}`")]
    UnknownKey { key: String },
    /// A required key is missing.
    #[code("plugins-lock-missing-key")]
    #[text("missing required key `{key}`")]
    MissingKey { key: String },
    /// The lock text is larger than the limit.
    #[code("plugins-lock-too-large")]
    #[text("larger than {max} bytes")]
    LockTooLarge {
        #[count]
        max: usize,
    },
    /// The lock text is not valid TOML.
    #[code("plugins-lock-toml-invalid")]
    #[text("invalid TOML: {reason}")]
    TomlInvalid { reason: String },
    /// The lock text is not valid TOML, with the byte offset.
    #[code("plugins-lock-toml-invalid-at")]
    #[text("invalid TOML at byte {offset}: {reason}")]
    TomlInvalidAt {
        #[count]
        offset: usize,
        reason: String,
    },
    /// A version is not a semantic version.
    #[code("plugins-lock-version-invalid")]
    #[text("`{version}` is not a semantic version")]
    VersionInvalid { version: String },
    /// A named pack is not in the lock.
    #[code("plugins-update-unknown-pack")]
    #[text("plugin `{id}` is not in the lock")]
    UpdateUnknownPack { id: String },
    /// The lock file could not be used.
    #[code("plugins-update-lock-file")]
    #[text("lock file {path}: {message}")]
    UpdateLockFile {
        #[display_path]
        path: String,
        message: String,
    },
    /// The new lock could not be written.
    #[code("plugins-update-write")]
    #[text("writing {path}: {reason}")]
    UpdateWrite {
        #[display_path]
        path: String,
        reason: String,
    },
    /// The lock directory is not a plain directory.
    #[code("plugins-update-lock-dir")]
    #[text("`{dir}` is not a plain directory ({reason})")]
    UpdateLockDir {
        #[display_path]
        dir: String,
        reason: String,
    },
    /// The guard file is not private.
    #[code("plugins-update-guard-private")]
    #[text("`{path}` must be owned by you and private (mode 0600)")]
    UpdateGuardPrivate {
        #[display_path]
        path: String,
    },
    /// The lock file does not exist.
    #[code("plugins-update-lock-missing")]
    #[text("{path}: no such file")]
    UpdateLockMissing {
        #[display_path]
        path: String,
    },
    /// The lock file is not UTF-8.
    #[code("plugins-update-lock-not-utf8")]
    #[text("{path}: not UTF-8")]
    UpdateLockNotUtf8 {
        #[display_path]
        path: String,
    },
    /// The registry tag lists passed the byte budget.
    #[code("plugins-update-budget")]
    #[text("registry tag lists exceed the {budget}-byte budget for one update")]
    UpdateBudget {
        #[count]
        budget: u64,
    },
}

/// Fixed phrases: what sync needed from the network, artifact layout problems and git and lock
/// refusals. Each reads as a `&'static str`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum SyncPhrase {
    /// What was missing: the plugin archive.
    #[code("plugins-sync-what-archive")]
    #[text("plugin archive")]
    WhatArchive,
    /// What was missing: the git tree.
    #[code("plugins-sync-what-git-tree")]
    #[text("git tree")]
    WhatGitTree,
    /// What was missing: the release archive.
    #[code("plugins-sync-what-release")]
    #[text("release archive")]
    WhatRelease,
    /// What was missing: the manifest.
    #[code("plugins-sync-what-manifest")]
    #[text("manifest")]
    WhatManifest,
    /// What was missing: the signed statement.
    #[code("plugins-sync-what-statement")]
    #[text("signed statement")]
    WhatStatement,
    /// What was missing: the signature.
    #[code("plugins-sync-what-signature")]
    #[text("signature")]
    WhatSignature,
    /// The manifest is not an image manifest.
    #[code("plugins-sync-manifest-not-image")]
    #[text("the manifest is not an image manifest")]
    ManifestNotImage,
    /// A plugin has more or fewer content layers than one.
    #[code("plugins-sync-one-layer")]
    #[text("a plugin has exactly one content layer")]
    OneLayer,
    /// The content layer has the wrong media type.
    #[code("plugins-sync-layer-not-archive")]
    #[text("the content layer is not a plugin archive")]
    LayerNotArchive,
    /// The content layer is larger than the archive limit.
    #[code("plugins-sync-layer-too-large")]
    #[text("the content layer exceeds the archive size limit")]
    LayerTooLarge,
    /// The signature blob is not text.
    #[code("plugins-sync-signature-not-text")]
    #[text("the signature is not text")]
    SignatureNotText,
    /// No git was found.
    #[code("plugins-sync-git-not-found")]
    #[text("git was not found in a trusted PATH directory")]
    GitNotFound,
    /// A git source must use https.
    #[code("plugins-sync-git-https-only")]
    #[text("only https:// repositories are fetched")]
    GitHttpsOnly,
    /// A git source must name a full commit hash.
    #[code("plugins-sync-git-commit-short")]
    #[text("the commit is not a full 40-digit hash")]
    GitCommitShort,
    /// The fetched commit differs from the pinned one.
    #[code("plugins-sync-git-commit-differs")]
    #[text("the fetched commit is not the pinned commit")]
    GitCommitDiffers,
    /// `git cat-file` printed nothing.
    #[code("plugins-sync-git-no-output")]
    #[text("no output from `git cat-file`")]
    GitNoOutput,
    /// A line of `git ls-tree` has the wrong shape.
    #[code("plugins-sync-git-ls-tree-line")]
    #[text("`git ls-tree` printed an unexpected line")]
    GitLsTreeLine,
    /// A path in the commit is not UTF-8.
    #[code("plugins-sync-git-path-not-utf8")]
    #[text("a path in the commit is not UTF-8")]
    GitPathNotUtf8,
    /// An object id of `git ls-tree` has the wrong shape.
    #[code("plugins-sync-git-ls-tree-oid")]
    #[text("`git ls-tree` printed an unexpected object id")]
    GitLsTreeOid,
    /// A size of `git ls-tree` has the wrong shape.
    #[code("plugins-sync-git-ls-tree-size")]
    #[text("`git ls-tree` printed an unexpected size")]
    GitLsTreeSize,
    /// The header of `git cat-file` has the wrong shape.
    #[code("plugins-sync-git-cat-file-header")]
    #[text("`git cat-file` printed an unexpected header")]
    GitCatFileHeader,
    /// A size of `git cat-file` has the wrong shape.
    #[code("plugins-sync-git-cat-file-size")]
    #[text("`git cat-file` printed an unexpected size")]
    GitCatFileSize,
    /// `git cat-file` answered for another object.
    #[code("plugins-sync-git-cat-file-object")]
    #[text("`git cat-file` answered for another object")]
    GitCatFileObject,
    /// The sizes of `git cat-file` and `git ls-tree` differ.
    #[code("plugins-sync-git-size-differs")]
    #[text("`git cat-file` printed another size than `git ls-tree`")]
    GitSizeDiffers,
    /// `git cat-file` ended early.
    #[code("plugins-sync-git-ended-early")]
    #[text("`git cat-file` ended early")]
    GitEndedEarly,
    /// A source is a control or bidirectional character.
    #[code("plugins-lock-source-unsafe")]
    #[text("a source must not contain control, bidirectional or zero-width characters")]
    SourceUnsafe,
    /// A source URL carries user-info.
    #[code("plugins-lock-source-credentials")]
    #[text("a source URL must not carry user-info (credentials)")]
    SourceCredentials,
    /// An `oci://` source has whitespace or no reference.
    #[code("plugins-lock-oci-whitespace")]
    #[text("an oci:// source needs a reference without whitespace")]
    OciWhitespace,
    /// An `https://` source has whitespace or no URL.
    #[code("plugins-lock-https-whitespace")]
    #[text("an https:// source needs a URL without whitespace")]
    HttpsWhitespace,
    /// A git source is not pinned to a commit.
    #[code("plugins-lock-git-pin")]
    #[text("a git+https:// source must end in `@` and a full 40-digit lowercase commit hash")]
    GitPin,
    /// A source uses plain `http://`.
    #[code("plugins-lock-http-refused")]
    #[text("http:// sources are not allowed; use https://")]
    HttpRefused,
    /// A source uses an unknown scheme.
    #[code("plugins-lock-scheme-unknown")]
    #[text("the source scheme is not oci, https or git+https")]
    SchemeUnknown,
    /// A path source is absolute or uses backslashes.
    #[code("plugins-lock-path-absolute")]
    #[text("a path source must be relative and use forward slashes")]
    PathAbsolute,
    /// A path source contains a colon.
    #[code("plugins-lock-path-colon")]
    #[text("a path source must not contain `:`")]
    PathColon,
    /// A path source contains a `..` segment.
    #[code("plugins-lock-path-dotdot")]
    #[text("a path source must not contain a `..` segment")]
    PathDotDot,
    /// A path source starts with whitespace or spans lines.
    #[code("plugins-lock-path-start")]
    #[text("a path source must start with a non-space character and fit on one line")]
    PathStart,
    /// A value must be a string.
    #[code("plugins-lock-must-be-string")]
    #[text("must be a string")]
    MustBeString,
    /// The schema version is not 3.
    #[code("plugins-lock-schema-version")]
    #[text("must be the integer 3")]
    SchemaVersion,
    /// `plugins` must be an array of tables.
    #[code("plugins-lock-plugins-array")]
    #[text("must be an array of tables")]
    PluginsArray,
    /// A value must be a table.
    #[code("plugins-lock-must-be-table")]
    #[text("must be a table")]
    MustBeTable,
    /// `slopvac_api` must be an integer of at least 1.
    #[code("plugins-lock-api-integer")]
    #[text("must be an integer of at least 1")]
    ApiInteger,
    /// `requires` must be an array of plugin ids.
    #[code("plugins-lock-requires-array")]
    #[text("must be an array of plugin ids")]
    RequiresArray,
}

/// The entries of every catalog of this file.
pub(super) fn entries() -> Vec<Entry> {
    [
        SyncMessage::entries(),
        SyncText::entries(),
        SyncPhrase::entries(),
    ]
    .concat()
}

fn s(value: &impl Display) -> String {
    value.to_string()
}

fn sync_failed(detail: &SyncText) -> String {
    SyncMessage::SyncFailed {
        detail: detail.to_string(),
    }
    .to_string()
}

/// `offline-plugin-missing`.
pub(crate) fn offline_missing(id: &PackId, digest: &str, what: &str) -> String {
    SyncMessage::OfflinePluginMissing {
        id: s(id),
        digest: esc(digest),
        what: esc(what),
    }
    .to_string()
}

/// `sync-failed` for a lock entry that cannot be resolved.
pub(crate) fn source_failed(id: &PackId, why: &str) -> String {
    sync_failed(&SyncText::Source {
        id: s(id),
        why: esc(why),
    })
}

/// `sync-failed` for a git source that failed.
pub(crate) fn git_source(id: &PackId, why: &str) -> String {
    sync_failed(&SyncText::GitSource {
        id: s(id),
        why: esc(why),
    })
}

/// `sync-failed` for a git source that passed a limit.
pub(crate) fn git_source_limit(id: &PackId, why: &str) -> String {
    sync_failed(&SyncText::GitSourceLimit {
        id: s(id),
        why: esc(why),
    })
}

/// `sync-failed` for a failure that carries the cause's text.
pub(crate) fn plugin_cause(id: &PackId, cause: &impl Display) -> String {
    sync_failed(&SyncText::PluginCause {
        id: s(id),
        cause: s(cause),
    })
}

/// `sync-fetch` for a failed fetch that carries the cause's text.
pub(crate) fn fetch_cause(id: &PackId, cause: &impl Display) -> String {
    SyncMessage::SyncFetch {
        detail: SyncText::PluginCause {
            id: s(id),
            cause: s(cause),
        }
        .to_string(),
    }
    .to_string()
}

/// `signature-invalid` for a refused signature check.
pub(crate) fn sign_failed(id: &PackId, cause: &impl Display) -> String {
    signature_invalid(&SyncText::SignFailed {
        id: s(id),
        cause: s(cause),
    })
}

/// `sync-unsigned` for an OCI entry without a signature in the lock.
pub(crate) fn unsigned(id: &PackId) -> String {
    SyncMessage::SyncUnsigned {
        detail: SyncText::Unsigned { id: s(id) }.to_string(),
    }
    .to_string()
}

/// `signature-invalid` for a statement that differs from the lock.
pub(crate) fn sign_differs(id: &PackId, why: &str) -> String {
    signature_invalid(&SyncText::SignDiffers {
        id: s(id),
        why: esc(why),
    })
}

fn signature_invalid(detail: &SyncText) -> String {
    SyncMessage::SignatureInvalid {
        detail: detail.to_string(),
    }
    .to_string()
}

/// `digest-mismatch`.
pub(crate) fn digest_mismatch(id: &PackId, expected: &str, actual: &str) -> String {
    SyncMessage::DigestMismatch {
        id: s(id),
        expected: esc(expected),
        actual: esc(actual),
    }
    .to_string()
}

/// `sync-failed` for an unexpected artifact layout.
pub(crate) fn layout(id: &PackId, why: &str) -> String {
    sync_failed(&SyncText::Layout {
        id: s(id),
        why: esc(why),
    })
}

/// `cache-tampered`.
pub(crate) fn cache_tampered(id: &PackId, path: &Path) -> String {
    SyncMessage::CacheTampered {
        id: s(id),
        path: esc(&path.to_string_lossy()),
    }
    .to_string()
}

/// `sync-failed` for a Python environment that could not be built.
pub(crate) fn pack_env(id: &PackId, cause: &impl Display) -> String {
    sync_failed(&SyncText::PackEnv {
        id: s(id),
        cause: s(cause),
    })
}

/// `sync-failed` for the data directory.
pub(crate) fn data_dir(detail: &str) -> String {
    sync_failed(&SyncText::DataDir {
        detail: esc(detail),
    })
}

/// `plugin-revoked`.
pub(crate) fn revoked(id: &PackId, what: &str) -> String {
    SyncMessage::PluginRevoked {
        id: s(id),
        what: what.to_owned(),
    }
    .to_string()
}

/// `lock-mismatch`.
pub(crate) fn lock_mismatch(diff: &LockDiff) -> String {
    SyncMessage::LockMismatch { diff: s(diff) }.to_string()
}

/// What is revoked: the artifact.
pub(crate) fn revoked_artifact(digest: &impl Display) -> String {
    SyncText::RevokedArtifact { digest: s(digest) }.to_string()
}

/// What is revoked: the publisher key.
pub(crate) fn revoked_key(key_id: &str) -> String {
    SyncText::RevokedKey {
        key_id: key_id.to_owned(),
    }
    .to_string()
}

/// The step "opening" a blob.
pub(crate) fn opening(path: &Path) -> String {
    SyncText::Opening {
        path: path.display().to_string(),
    }
    .to_string()
}

/// The manifest does not parse.
pub(crate) fn manifest_parse(reason: &impl Display) -> String {
    SyncText::ManifestParse { reason: s(reason) }.to_string()
}

/// The signing key differs from the lock.
pub(crate) fn signed_key(actual: &impl Display, locked: &impl Display) -> String {
    SyncText::SignedKey {
        actual: s(actual),
        locked: s(locked),
    }
    .to_string()
}

/// The `notBefore` time differs from the lock.
pub(crate) fn signed_not_before(actual: &impl Display, locked: &impl Display) -> String {
    SyncText::SignedNotBefore {
        actual: s(actual),
        locked: s(locked),
    }
    .to_string()
}

/// The launcher cannot be found.
pub(crate) fn launcher_missing(reason: &impl Display) -> String {
    SyncText::LauncherMissing { reason: s(reason) }.to_string()
}

/// Hashing failed.
pub(crate) fn hashing(reason: &impl Display) -> String {
    SyncText::Hashing { reason: s(reason) }.to_string()
}

/// A path source could not be inspected.
pub(crate) fn path_io(rel: &str, reason: &impl Display) -> String {
    SyncText::PathIo {
        rel: rel.to_owned(),
        reason: s(reason),
    }
    .to_string()
}

/// A path source goes through a link.
pub(crate) fn path_link(rel: &str) -> String {
    SyncText::PathLink {
        rel: rel.to_owned(),
    }
    .to_string()
}

/// A path source leaves the project.
pub(crate) fn path_outside(rel: &str) -> String {
    SyncText::PathOutside {
        rel: rel.to_owned(),
    }
    .to_string()
}

/// A path source could not be read.
pub(crate) fn path_reading(rel: &str, reason: &impl Display) -> String {
    SyncText::PathReading {
        rel: rel.to_owned(),
        reason: s(reason),
    }
    .to_string()
}

/// A path source is larger than the archive limit.
pub(crate) fn path_too_large(rel: &str) -> String {
    SyncText::PathTooLarge {
        rel: rel.to_owned(),
    }
    .to_string()
}

/// The notice for a newer version inside the configured range.
pub(crate) fn notice_update(
    id: &impl Display,
    version: &impl Display,
    locked: &impl Display,
) -> String {
    SyncText::NoticeUpdate {
        id: s(id),
        version: s(version),
        locked: s(locked),
    }
    .to_string()
}

/// The notice for a newer version outside the configured range.
pub(crate) fn notice_outside(id: &impl Display, version: &impl Display) -> String {
    SyncText::NoticeOutside {
        id: s(id),
        version: s(version),
    }
    .to_string()
}

/// The store lock file is not a plain file.
pub(crate) fn not_plain_file(path: &Path) -> String {
    SyncText::NotPlainFile {
        path: path.display().to_string(),
    }
    .to_string()
}

/// The store lock file could not be opened.
pub(crate) fn store_lock_open(reason: &impl Display) -> String {
    SyncText::StoreLockOpen { reason: s(reason) }.to_string()
}

/// The store lock could not be taken.
pub(crate) fn store_lock_take(reason: &impl Display) -> String {
    SyncText::StoreLockTake { reason: s(reason) }.to_string()
}

/// The download file could not be created.
pub(crate) fn download_file(reason: &impl Display) -> String {
    SyncText::DownloadFile { reason: s(reason) }.to_string()
}

/// A scratch directory could not be created.
pub(crate) fn scratch_dir(reason: &impl Display) -> String {
    SyncText::ScratchDir { reason: s(reason) }.to_string()
}

/// A download hashed to another digest.
pub(crate) fn download_hash(actual: &impl Display, digest: &impl Display) -> String {
    SyncText::DownloadHash {
        actual: s(actual),
        digest: s(digest),
    }
    .to_string()
}

/// A download could not be moved into place.
pub(crate) fn download_store(reason: &impl Display) -> String {
    SyncText::DownloadStore { reason: s(reason) }.to_string()
}

/// A download could not be written.
pub(crate) fn download_write(reason: &impl Display) -> String {
    SyncText::DownloadWrite { reason: s(reason) }.to_string()
}

/// The record of an install could not be written.
pub(crate) fn record_install(reason: &impl Display) -> String {
    SyncText::RecordInstall { reason: s(reason) }.to_string()
}

/// The repository download passed its limit.
pub(crate) fn git_download_limit(max: u64) -> String {
    SyncText::GitDownloadLimit { max }.to_string()
}

/// Reading the output of a git command failed.
pub(crate) fn git_reading(what: &str, reason: &impl Display) -> String {
    SyncText::GitReading {
        what: what.to_owned(),
        reason: s(reason),
    }
    .to_string()
}

/// A git command printed more than the cap.
pub(crate) fn git_output_cap(what: &str, cap: usize) -> String {
    SyncText::GitOutputCap {
        what: what.to_owned(),
        cap,
    }
    .to_string()
}

/// The commit holds too many files.
pub(crate) fn git_too_many_files(max: usize) -> String {
    SyncText::GitTooManyFiles { max }.to_string()
}

/// The commit holds a symbolic link.
pub(crate) fn git_symlink(path: &str) -> String {
    SyncText::GitSymlink {
        path: path.to_owned(),
    }
    .to_string()
}

/// The commit holds a submodule.
pub(crate) fn git_submodule(path: &str) -> String {
    SyncText::GitSubmodule {
        path: path.to_owned(),
    }
    .to_string()
}

/// The commit holds an entry with an unsupported mode.
pub(crate) fn git_mode(path: &str, mode: &str) -> String {
    SyncText::GitMode {
        path: path.to_owned(),
        mode: mode.to_owned(),
    }
    .to_string()
}

/// The commit expands past the size limit.
pub(crate) fn git_expands(max: u64) -> String {
    SyncText::GitExpands { max }.to_string()
}

/// Reading the reply of `git cat-file` failed.
pub(crate) fn git_cat_file_read(reason: &impl Display) -> String {
    SyncText::GitCatFileRead { reason: s(reason) }.to_string()
}

/// An object is missing or is not a file.
pub(crate) fn git_object_missing(oid: &str) -> String {
    SyncText::GitObjectMissing {
        oid: oid.to_owned(),
    }
    .to_string()
}

/// The git process could not be started.
pub(crate) fn git_spawn(reason: &impl Display) -> String {
    SyncText::GitSpawn { reason: s(reason) }.to_string()
}

/// A git command ran out of time.
pub(crate) fn git_timed_out(what: &str) -> String {
    SyncText::GitTimedOut {
        what: what.to_owned(),
    }
    .to_string()
}

/// A git command was stopped.
pub(crate) fn git_stopped(what: &str) -> String {
    SyncText::GitStopped {
        what: what.to_owned(),
    }
    .to_string()
}

/// Waiting for a git command failed.
pub(crate) fn git_waiting(what: &str, reason: &impl Display) -> String {
    SyncText::GitWaiting {
        what: what.to_owned(),
        reason: s(reason),
    }
    .to_string()
}

/// A git command exited with a failure status; `stderr` is its trimmed error output.
pub(crate) fn git_exit(what: &str, status: &impl Display, stderr: &str) -> String {
    let detail = if stderr.is_empty() {
        String::new()
    } else {
        SyncText::GitExitDetail {
            text: stderr.to_owned(),
        }
        .to_string()
    };
    SyncText::GitExit {
        what: what.to_owned(),
        status: s(status),
        detail,
    }
    .to_string()
}

/// A lock error: the pointer (`/` for the whole file) and the message.
pub(crate) fn lock_error(pointer: &str, message: &str) -> String {
    SyncText::LockError {
        pointer: if pointer.is_empty() { "/" } else { pointer }.to_owned(),
        message: message.to_owned(),
    }
    .to_string()
}

/// A plugin id is too long.
pub(crate) fn id_too_long(max: usize) -> String {
    SyncText::IdTooLong { max }.to_string()
}

/// A plugin id has the wrong shape.
pub(crate) fn id_invalid(value: &str) -> String {
    SyncText::IdInvalid {
        value: value.to_owned(),
    }
    .to_string()
}

/// A digest has the wrong shape.
pub(crate) fn digest_invalid(value: &str) -> String {
    SyncText::DigestInvalid {
        value: value.to_owned(),
    }
    .to_string()
}

/// A key id has the wrong shape.
pub(crate) fn key_id_invalid(value: &str) -> String {
    SyncText::KeyIdInvalid {
        value: value.to_owned(),
    }
    .to_string()
}

/// A time has the wrong shape.
pub(crate) fn time_invalid(value: &str) -> String {
    SyncText::TimeInvalid {
        value: value.to_owned(),
    }
    .to_string()
}

/// A plugin kind is not `data` or `code`.
pub(crate) fn kind_invalid(value: &str) -> String {
    SyncText::KindInvalid {
        value: value.to_owned(),
    }
    .to_string()
}

/// A source is too long.
pub(crate) fn source_too_long(max: usize) -> String {
    SyncText::SourceTooLong { max }.to_string()
}

/// The lock holds too many plugins.
pub(crate) fn too_many_plugins(max: usize) -> String {
    SyncText::TooManyPlugins { max }.to_string()
}

/// The id `core` is reserved.
pub(crate) fn reserved(id: &impl Display) -> String {
    SyncText::Reserved { id: s(id) }.to_string()
}

/// An id is locked twice.
pub(crate) fn locked_twice(id: &impl Display) -> String {
    SyncText::LockedTwice { id: s(id) }.to_string()
}

/// A version has build metadata.
pub(crate) fn build_metadata(version: &impl Display) -> String {
    SyncText::BuildMetadata {
        version: s(version),
    }
    .to_string()
}

/// A version is too long.
pub(crate) fn version_too_long(max: usize) -> String {
    SyncText::VersionTooLong { max }.to_string()
}

/// The API version is outside its range.
pub(crate) fn api_range(max: u64) -> String {
    SyncText::ApiRange { max }.to_string()
}

/// A pack lists too many `requires` entries.
pub(crate) fn too_many_requires(max: usize) -> String {
    SyncText::TooManyRequires { max }.to_string()
}

/// A `requires` entry is listed twice.
pub(crate) fn listed_twice(id: &impl Display) -> String {
    SyncText::ListedTwice { id: s(id) }.to_string()
}

/// The canonical text is larger than the limit.
pub(crate) fn canonical_too_large(max: usize) -> String {
    SyncText::CanonicalTooLarge { max }.to_string()
}

/// The diff line for a resolved pack that is not locked.
pub(crate) fn diff_added(id: &impl Display, version: &impl Display) -> String {
    SyncText::DiffAdded {
        id: s(id),
        version: s(version),
    }
    .to_string()
}

/// The diff line for a locked pack that was not resolved.
pub(crate) fn diff_removed(id: &impl Display) -> String {
    SyncText::DiffRemoved { id: s(id) }.to_string()
}

/// The start of the diff line for a changed pack.
pub(crate) fn diff_changed(id: &impl Display) -> String {
    SyncText::DiffChanged { id: s(id) }.to_string()
}

/// A changed version.
pub(crate) fn diff_version(locked: &impl Display, resolved: &impl Display) -> String {
    let text = SyncText::DiffVersion {
        locked: s(locked),
        resolved: s(resolved),
    };
    format!(" {text}")
}

/// A changed source. A source is free text, so both sides are escaped.
pub(crate) fn diff_source(locked: &str, resolved: &str) -> String {
    let text = SyncText::DiffSource {
        locked: esc(locked),
        resolved: esc(resolved),
    };
    format!(" {text}")
}

/// A changed digest.
pub(crate) fn diff_digest(locked: &impl Display, resolved: &impl Display) -> String {
    let text = SyncText::DiffDigest {
        locked: s(locked),
        resolved: s(resolved),
    };
    format!(" {text}")
}

/// A version comparator has the wrong shape.
pub(crate) fn comparator_invalid(comparator: &str, text: &str) -> String {
    SyncText::ComparatorInvalid {
        comparator: comparator.to_owned(),
        text: text.to_owned(),
    }
    .to_string()
}

/// A version requirement does not parse.
pub(crate) fn req_invalid(text: &str, reason: &impl Display) -> String {
    SyncText::ReqInvalid {
        text: text.to_owned(),
        reason: s(reason),
    }
    .to_string()
}

/// The lock holds a key the schema does not define.
pub(crate) fn unknown_key(key: &str) -> String {
    SyncText::UnknownKey {
        key: key.to_owned(),
    }
    .to_string()
}

/// A required key is missing.
pub(crate) fn missing_key(key: &str) -> String {
    SyncText::MissingKey {
        key: key.to_owned(),
    }
    .to_string()
}

/// The lock text is larger than the limit.
pub(crate) fn lock_too_large(max: usize) -> String {
    SyncText::LockTooLarge { max }.to_string()
}

/// The lock text is not valid TOML; `offset` is the byte offset when the parser knows it.
pub(crate) fn toml_invalid(offset: Option<usize>, reason: &str) -> String {
    match offset {
        Some(offset) => SyncText::TomlInvalidAt {
            offset,
            reason: reason.to_owned(),
        },
        None => SyncText::TomlInvalid {
            reason: reason.to_owned(),
        },
    }
    .to_string()
}

/// A version is not a semantic version.
pub(crate) fn version_invalid(version: &str) -> String {
    SyncText::VersionInvalid {
        version: version.to_owned(),
    }
    .to_string()
}

/// `update-lock-busy`.
pub(crate) fn update_busy(path: &str, secs: f32) -> String {
    SyncMessage::UpdateLockBusy {
        path: esc(path),
        secs: secs.to_string(),
    }
    .to_string()
}

/// `unsupported-on-windows`.
pub(crate) fn unsupported_on_windows(path: &str) -> String {
    SyncMessage::UnsupportedOnWindows { path: esc(path) }.to_string()
}

fn update_failed(detail: &SyncText) -> String {
    SyncMessage::UpdateFailed {
        detail: detail.to_string(),
    }
    .to_string()
}

/// `update-plugin-unknown` for a plugin that is not in the lock.
pub(crate) fn update_unknown_plugin(id: &impl Display) -> String {
    SyncMessage::UpdatePluginUnknown {
        detail: SyncText::UpdateUnknownPack { id: s(id) }.to_string(),
    }
    .to_string()
}

/// `update-failed` for a lock file that cannot be used.
pub(crate) fn update_lock_file(path: &str, message: &str) -> String {
    update_failed(&SyncText::UpdateLockFile {
        path: esc(path),
        message: message.to_owned(),
    })
}

/// `update-failed` for a lock that could not be written.
pub(crate) fn update_write(path: &str, reason: &impl Display) -> String {
    update_failed(&SyncText::UpdateWrite {
        path: esc(path),
        reason: s(reason),
    })
}

/// The lock directory is not a plain directory.
pub(crate) fn update_lock_dir(dir: &str, reason: &impl Display) -> String {
    SyncText::UpdateLockDir {
        dir: dir.to_owned(),
        reason: s(reason),
    }
    .to_string()
}

/// The guard file is not private.
pub(crate) fn update_guard_private(path: &str) -> String {
    SyncText::UpdateGuardPrivate {
        path: path.to_owned(),
    }
    .to_string()
}

/// The lock file does not exist.
pub(crate) fn update_lock_missing(path: &str) -> String {
    SyncText::UpdateLockMissing {
        path: path.to_owned(),
    }
    .to_string()
}

/// The lock file is not UTF-8.
pub(crate) fn update_lock_not_utf8(path: &str) -> String {
    SyncText::UpdateLockNotUtf8 {
        path: path.to_owned(),
    }
    .to_string()
}

/// The registry tag lists passed the byte budget.
pub(crate) fn update_budget(budget: u64) -> String {
    SyncText::UpdateBudget { budget }.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(text: &str) -> String {
        text.to_owned()
    }

    fn registered() -> Vec<Entry> {
        entries()
    }

    #[test]
    fn every_published_code_keeps_its_text_and_is_registered() {
        let table: Vec<(SyncMessage, &str)> = vec![
            (
                SyncMessage::OfflinePluginMissing {
                    id: s("demo"),
                    digest: s("sha256:ab"),
                    what: s("manifest"),
                },
                "offline: plugin `demo` (sha256:ab) is not in the cache: manifest",
            ),
            (
                SyncMessage::LockMismatch {
                    diff: s("added: x 1.0.0 is not in the lock\n"),
                },
                "the lock does not match the resolved plugins:\nadded: x 1.0.0 is not in the lock\n",
            ),
            (
                SyncMessage::CacheTampered {
                    id: s("demo"),
                    path: s("/data/trees/tree-ab"),
                },
                "plugin `demo`: the cached tree /data/trees/tree-ab was modified and was removed; offline sync cannot restore it",
            ),
            (
                SyncMessage::DigestMismatch {
                    id: s("demo"),
                    expected: s("sha256:aa"),
                    actual: s("sha256:bb"),
                },
                "plugin `demo`: digest mismatch: the lock pins sha256:aa, the content is sha256:bb",
            ),
            (SyncMessage::SignatureInvalid { detail: s("d") }, "d"),
            (
                SyncMessage::PluginRevoked {
                    id: s("demo"),
                    what: s("artifact sha256:aa"),
                },
                "plugin `demo`: artifact sha256:aa is on the revocation list",
            ),
            (SyncMessage::SyncFailed { detail: s("d") }, "d"),
            (SyncMessage::SyncFetch { detail: s("d") }, "d"),
            (SyncMessage::SyncUnsigned { detail: s("d") }, "d"),
            (SyncMessage::UpdatePluginUnknown { detail: s("d") }, "d"),
            (
                SyncMessage::UpdateLockBusy {
                    path: s("/p/.slopvac/plugins.lock.guard"),
                    secs: s("30"),
                },
                "another `plugins update` holds the lock on /p/.slopvac/plugins.lock.guard; gave up after 30 s",
            ),
            (
                SyncMessage::UnsupportedOnWindows { path: s("p") },
                "`p`: writes are not supported on Windows yet; the lock was not changed",
            ),
            (SyncMessage::UpdateFailed { detail: s("d") }, "d"),
        ];
        let all = registered();
        for (value, expected) in &table {
            assert_eq!(value.to_string(), *expected);
            assert!(all.iter().any(|e| e.code == value.code()));
        }
        assert_eq!(SyncMessage::entries().len(), table.len());
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_text_keeps_its_sentence_and_is_registered() {
        let table: Vec<(SyncText, &str)> = vec![
            (
                SyncText::Source {
                    id: s("a"),
                    why: s("w"),
                },
                "plugin `a`: w",
            ),
            (
                SyncText::GitSource {
                    id: s("a"),
                    why: s("w"),
                },
                "plugin `a`: git source: w",
            ),
            (
                SyncText::GitSourceLimit {
                    id: s("a"),
                    why: s("w"),
                },
                "plugin `a`: git source passes a limit: w",
            ),
            (
                SyncText::PluginCause {
                    id: s("a"),
                    cause: s("c"),
                },
                "plugin `a`: c",
            ),
            (
                SyncText::SignFailed {
                    id: s("a"),
                    cause: s("c"),
                },
                "plugin `a`: signature check failed: c",
            ),
            (
                SyncText::Unsigned { id: s("a") },
                "plugin `a`: the lock has no signature for an OCI plugin; pin its key, then update",
            ),
            (
                SyncText::SignDiffers {
                    id: s("a"),
                    why: s("w"),
                },
                "plugin `a`: the signature differs from the lock: w",
            ),
            (
                SyncText::Layout {
                    id: s("a"),
                    why: s("w"),
                },
                "plugin `a`: unexpected artifact layout: w",
            ),
            (
                SyncText::PackEnv {
                    id: s("a"),
                    cause: s("c"),
                },
                "pack `a`: c",
            ),
            (SyncText::DataDir { detail: s("d") }, "data directory: d"),
            (
                SyncText::RevokedArtifact {
                    digest: s("sha256:aa"),
                },
                "artifact sha256:aa",
            ),
            (SyncText::RevokedKey { key_id: s("AB") }, "publisher key AB"),
            (SyncText::Opening { path: s("/b/x") }, "opening /b/x"),
            (
                SyncText::ManifestParse { reason: s("r") },
                "the manifest does not parse: r",
            ),
            (
                SyncText::SignedKey {
                    actual: s("A"),
                    locked: s("B"),
                },
                "signed by key A, the lock records B",
            ),
            (
                SyncText::SignedNotBefore {
                    actual: s("A"),
                    locked: s("B"),
                },
                "notBefore is A, the lock records B",
            ),
            (
                SyncText::LauncherMissing { reason: s("r") },
                "cannot find the launcher: r",
            ),
            (SyncText::Hashing { reason: s("r") }, "hashing: r"),
            (
                SyncText::PathIo {
                    rel: s("x/y"),
                    reason: s("r"),
                },
                "path source `x/y`: r",
            ),
            (
                SyncText::PathLink { rel: s("x/y") },
                "path source `x/y` goes through a link",
            ),
            (
                SyncText::PathOutside { rel: s("x/y") },
                "path source `x/y` leaves the project",
            ),
            (
                SyncText::PathReading {
                    rel: s("x/y"),
                    reason: s("r"),
                },
                "reading `x/y`: r",
            ),
            (
                SyncText::PathTooLarge { rel: s("x/y") },
                "`x/y` exceeds the archive size limit",
            ),
            (
                SyncText::NoticeUpdate {
                    id: s("a"),
                    version: s("1.1.0"),
                    locked: s("1.0.0"),
                },
                "plugin a: 1.1.0 is available (locked 1.0.0); run `slopvac plugins update`",
            ),
            (
                SyncText::NoticeOutside {
                    id: s("a"),
                    version: s("2.0.0"),
                },
                "plugin a: 2.0.0 is available but outside the configured range; change the range to use it",
            ),
            (
                SyncText::NotPlainFile {
                    path: s("/d/.lock"),
                },
                "/d/.lock is not a plain file",
            ),
            (
                SyncText::StoreLockOpen { reason: s("r") },
                "opening the store lock: r",
            ),
            (
                SyncText::StoreLockTake { reason: s("r") },
                "taking the store lock: r",
            ),
            (
                SyncText::DownloadFile { reason: s("r") },
                "creating a download file: r",
            ),
            (
                SyncText::ScratchDir { reason: s("r") },
                "creating a scratch directory: r",
            ),
            (
                SyncText::DownloadHash {
                    actual: s("A"),
                    digest: s("B"),
                },
                "a download hashed to A, not B",
            ),
            (
                SyncText::DownloadStore { reason: s("r") },
                "storing a download: r",
            ),
            (
                SyncText::DownloadWrite { reason: s("r") },
                "writing a download: r",
            ),
            (
                SyncText::RecordInstall { reason: s("r") },
                "recording an install: r",
            ),
            (
                SyncText::GitDownloadLimit { max: 1024 },
                "the repository download exceeds 1024 bytes",
            ),
            (
                SyncText::GitReading {
                    what: s("fetch"),
                    reason: s("r"),
                },
                "reading `git fetch`: r",
            ),
            (
                SyncText::GitOutputCap {
                    what: s("fetch"),
                    cap: 4096,
                },
                "`git fetch` printed more than 4096 bytes",
            ),
            (
                SyncText::GitTooManyFiles { max: 10 },
                "the commit has more than 10 files",
            ),
            (
                SyncText::GitSymlink { path: s("a/b") },
                "`a/b` is a symbolic link",
            ),
            (
                SyncText::GitSubmodule { path: s("a/b") },
                "`a/b` is a submodule",
            ),
            (
                SyncText::GitMode {
                    path: s("a/b"),
                    mode: s("100666"),
                },
                "`a/b` has the unsupported mode 100666",
            ),
            (
                SyncText::GitExpands { max: 2048 },
                "the commit expands past the size limit of 2048 bytes",
            ),
            (
                SyncText::GitCatFileRead { reason: s("r") },
                "reading `git cat-file`: r",
            ),
            (
                SyncText::GitObjectMissing { oid: s("abc") },
                "object abc is missing or is not a file",
            ),
            (SyncText::GitSpawn { reason: s("r") }, "cannot start git: r"),
            (
                SyncText::GitTimedOut { what: s("fetch") },
                "`git fetch` timed out",
            ),
            (
                SyncText::GitStopped { what: s("fetch") },
                "`git fetch` was stopped",
            ),
            (
                SyncText::GitWaiting {
                    what: s("fetch"),
                    reason: s("r"),
                },
                "waiting for `git fetch`: r",
            ),
            (
                SyncText::GitExit {
                    what: s("fetch"),
                    status: s("exit status: 1"),
                    detail: s(": boom"),
                },
                "`git fetch` failed (exit status: 1): boom",
            ),
            (SyncText::GitExitDetail { text: s("boom") }, ": boom"),
            (
                SyncText::LockError {
                    pointer: s("/plugins/0"),
                    message: s("m"),
                },
                "/plugins/0: m",
            ),
            (
                SyncText::IdTooLong { max: 4096 },
                "a plugin id is longer than 4096 bytes",
            ),
            (
                SyncText::IdInvalid { value: s("X") },
                "`X` is not a plugin id (lowercase letters, digits and `-`, starting with a letter)",
            ),
            (
                SyncText::DigestInvalid { value: s("X") },
                "`X` is not a digest (`sha256:` and 64 lowercase hex digits)",
            ),
            (
                SyncText::KeyIdInvalid { value: s("X") },
                "`X` is not a key id (16 uppercase hex digits)",
            ),
            (
                SyncText::TimeInvalid { value: s("X") },
                "`X` is not a UTC time (`YYYY-MM-DDTHH:MM:SSZ`, calendar-valid)",
            ),
            (
                SyncText::KindInvalid { value: s("X") },
                "`X` is not a plugin kind (`data` or `code`)",
            ),
            (
                SyncText::SourceTooLong { max: 4096 },
                "a source is longer than 4096 bytes",
            ),
            (
                SyncText::TooManyPlugins { max: 1000 },
                "more than 1000 plugins",
            ),
            (
                SyncText::Reserved { id: s("core") },
                "`core` is reserved for the built-in plugin and is never locked",
            ),
            (
                SyncText::LockedTwice { id: s("a") },
                "plugin id `a` is locked twice",
            ),
            (
                SyncText::BuildMetadata {
                    version: s("1.0.0+b"),
                },
                "`1.0.0+b` has build metadata",
            ),
            (
                SyncText::VersionTooLong { max: 4096 },
                "longer than 4096 bytes",
            ),
            (
                SyncText::ApiRange {
                    max: 9_223_372_036_854_775_807,
                },
                "must be between 1 and 9223372036854775807",
            ),
            (
                SyncText::TooManyRequires { max: 256 },
                "more than 256 entries",
            ),
            (SyncText::ListedTwice { id: s("a") }, "`a` is listed twice"),
            (
                SyncText::CanonicalTooLarge { max: 1_048_576 },
                "the canonical text is larger than 1048576 bytes",
            ),
            (
                SyncText::DiffAdded {
                    id: s("a"),
                    version: s("1.0.0"),
                },
                "added: a 1.0.0 is not in the lock",
            ),
            (
                SyncText::DiffRemoved { id: s("a") },
                "removed: a is locked but was not resolved",
            ),
            (SyncText::DiffChanged { id: s("a") }, "changed: a"),
            (
                SyncText::DiffVersion {
                    locked: s("1.0.0"),
                    resolved: s("1.1.0"),
                },
                "version 1.0.0 -> 1.1.0",
            ),
            (
                SyncText::DiffSource {
                    locked: s("x"),
                    resolved: s("y"),
                },
                "source x -> y",
            ),
            (
                SyncText::DiffDigest {
                    locked: s("sha256:aa"),
                    resolved: s("sha256:bb"),
                },
                "digest sha256:aa -> sha256:bb",
            ),
            (
                SyncText::ComparatorInvalid {
                    comparator: s("^x"),
                    text: s("^x, 1"),
                },
                "`^x` is not a version comparator in `^x, 1`",
            ),
            (
                SyncText::ReqInvalid {
                    text: s("1.x.y"),
                    reason: s("r"),
                },
                "`1.x.y` is not a version requirement: r",
            ),
            (SyncText::UnknownKey { key: s("k") }, "unknown key `k`"),
            (
                SyncText::MissingKey { key: s("k") },
                "missing required key `k`",
            ),
            (
                SyncText::LockTooLarge { max: 1_048_576 },
                "larger than 1048576 bytes",
            ),
            (SyncText::TomlInvalid { reason: s("r") }, "invalid TOML: r"),
            (
                SyncText::TomlInvalidAt {
                    offset: 12,
                    reason: s("r"),
                },
                "invalid TOML at byte 12: r",
            ),
            (
                SyncText::VersionInvalid { version: s("x") },
                "`x` is not a semantic version",
            ),
            (
                SyncText::UpdateUnknownPack { id: s("a") },
                "plugin `a` is not in the lock",
            ),
            (
                SyncText::UpdateLockFile {
                    path: s("/p/l"),
                    message: s("m"),
                },
                "lock file /p/l: m",
            ),
            (
                SyncText::UpdateWrite {
                    path: s("/p/l"),
                    reason: s("r"),
                },
                "writing /p/l: r",
            ),
            (
                SyncText::UpdateLockDir {
                    dir: s(".slopvac"),
                    reason: s("r"),
                },
                "`.slopvac` is not a plain directory (r)",
            ),
            (
                SyncText::UpdateGuardPrivate { path: s("g") },
                "`g` must be owned by you and private (mode 0600)",
            ),
            (
                SyncText::UpdateLockMissing { path: s("l") },
                "l: no such file",
            ),
            (SyncText::UpdateLockNotUtf8 { path: s("l") }, "l: not UTF-8"),
            (
                SyncText::UpdateBudget { budget: 64 },
                "registry tag lists exceed the 64-byte budget for one update",
            ),
        ];
        let all = registered();
        for (value, expected) in &table {
            assert_eq!(value.to_string(), *expected);
            assert!(all.iter().any(|e| e.code == value.code()));
        }
        assert_eq!(SyncText::entries().len(), table.len());
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn every_phrase_keeps_its_text_and_is_registered() {
        let table: Vec<(SyncPhrase, &str)> = vec![
            (SyncPhrase::WhatArchive, "plugin archive"),
            (SyncPhrase::WhatGitTree, "git tree"),
            (SyncPhrase::WhatRelease, "release archive"),
            (SyncPhrase::WhatManifest, "manifest"),
            (SyncPhrase::WhatStatement, "signed statement"),
            (SyncPhrase::WhatSignature, "signature"),
            (
                SyncPhrase::ManifestNotImage,
                "the manifest is not an image manifest",
            ),
            (
                SyncPhrase::OneLayer,
                "a plugin has exactly one content layer",
            ),
            (
                SyncPhrase::LayerNotArchive,
                "the content layer is not a plugin archive",
            ),
            (
                SyncPhrase::LayerTooLarge,
                "the content layer exceeds the archive size limit",
            ),
            (SyncPhrase::SignatureNotText, "the signature is not text"),
            (
                SyncPhrase::GitNotFound,
                "git was not found in a trusted PATH directory",
            ),
            (
                SyncPhrase::GitHttpsOnly,
                "only https:// repositories are fetched",
            ),
            (
                SyncPhrase::GitCommitShort,
                "the commit is not a full 40-digit hash",
            ),
            (
                SyncPhrase::GitCommitDiffers,
                "the fetched commit is not the pinned commit",
            ),
            (SyncPhrase::GitNoOutput, "no output from `git cat-file`"),
            (
                SyncPhrase::GitLsTreeLine,
                "`git ls-tree` printed an unexpected line",
            ),
            (
                SyncPhrase::GitPathNotUtf8,
                "a path in the commit is not UTF-8",
            ),
            (
                SyncPhrase::GitLsTreeOid,
                "`git ls-tree` printed an unexpected object id",
            ),
            (
                SyncPhrase::GitLsTreeSize,
                "`git ls-tree` printed an unexpected size",
            ),
            (
                SyncPhrase::GitCatFileHeader,
                "`git cat-file` printed an unexpected header",
            ),
            (
                SyncPhrase::GitCatFileSize,
                "`git cat-file` printed an unexpected size",
            ),
            (
                SyncPhrase::GitCatFileObject,
                "`git cat-file` answered for another object",
            ),
            (
                SyncPhrase::GitSizeDiffers,
                "`git cat-file` printed another size than `git ls-tree`",
            ),
            (SyncPhrase::GitEndedEarly, "`git cat-file` ended early"),
            (
                SyncPhrase::SourceUnsafe,
                "a source must not contain control, bidirectional or zero-width characters",
            ),
            (
                SyncPhrase::SourceCredentials,
                "a source URL must not carry user-info (credentials)",
            ),
            (
                SyncPhrase::OciWhitespace,
                "an oci:// source needs a reference without whitespace",
            ),
            (
                SyncPhrase::HttpsWhitespace,
                "an https:// source needs a URL without whitespace",
            ),
            (
                SyncPhrase::GitPin,
                "a git+https:// source must end in `@` and a full 40-digit lowercase commit hash",
            ),
            (
                SyncPhrase::HttpRefused,
                "http:// sources are not allowed; use https://",
            ),
            (
                SyncPhrase::SchemeUnknown,
                "the source scheme is not oci, https or git+https",
            ),
            (
                SyncPhrase::PathAbsolute,
                "a path source must be relative and use forward slashes",
            ),
            (SyncPhrase::PathColon, "a path source must not contain `:`"),
            (
                SyncPhrase::PathDotDot,
                "a path source must not contain a `..` segment",
            ),
            (
                SyncPhrase::PathStart,
                "a path source must start with a non-space character and fit on one line",
            ),
            (SyncPhrase::MustBeString, "must be a string"),
            (SyncPhrase::SchemaVersion, "must be the integer 3"),
            (SyncPhrase::PluginsArray, "must be an array of tables"),
            (SyncPhrase::MustBeTable, "must be a table"),
            (SyncPhrase::ApiInteger, "must be an integer of at least 1"),
            (SyncPhrase::RequiresArray, "must be an array of plugin ids"),
        ];
        let all = registered();
        for (value, expected) in &table {
            assert_eq!(value.as_static(), *expected);
            assert!(all.iter().any(|e| e.code == value.code()));
        }
        assert_eq!(SyncPhrase::entries().len(), table.len());
    }

    #[test]
    fn a_control_character_in_a_name_is_escaped_in_the_offline_message() {
        // `slopvac_sanitize::line` renders ESC (U+001B) as `\u{1b}`.
        let id: PackId = "demo".parse().expect("valid id");
        assert_eq!(
            offline_missing(&id, "sha256:ab", "man\u{1b}ifest"),
            "offline: plugin `demo` (sha256:ab) is not in the cache: man\\u{1b}ifest"
        );
    }
}
