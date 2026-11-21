//! Messages for the trust store, signatures, revocation and strict JSON parsing.
//!
//! Three kinds of entry per topic: one per published error code, sentences with parameters, and
//! fixed phrases that callers read as `&'static str`. The helper functions build one message
//! each and apply the escape that the text needs, so a caller passes raw values.

use std::path::Path;

use slopvac_messages::{Catalog, Entry};
use slopvac_sanitize::line;

/// `value` escaped for one line of output.
fn esc(value: &str) -> String {
    line(value)
}

/// The stable codes of the trust and revocation errors, one constant for each published code.
pub(crate) mod codes {
    pub(crate) const NAMESPACE_RESERVED: &str = "namespace-reserved";
    pub(crate) const LIST_INVALID: &str = "revocation-list-invalid";
    pub(crate) const LIST_UNAVAILABLE: &str = "revocation-list-unavailable";
    pub(crate) const LIST_EXPIRED: &str = "revocation-list-expired";
    pub(crate) const LIST_ROLLBACK: &str = "revocation-list-rollback";
    pub(crate) const LIST_EQUIVOCATION: &str = "revocation-list-equivocation";
    pub(crate) const CACHE_INVALID: &str = "revocation-cache-invalid";
    pub(crate) const CLOCK_INVALID: &str = "revocation-clock-invalid";
    pub(crate) const LIST_MISSING: &str = "revocation-list-missing";
    pub(crate) const LIST_STALE: &str = "revocation-list-stale";
}

/// The published error codes and notices of the trust store and the revocation list.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum TrustMessage {
    /// A key cannot be pinned for a reserved or first-party namespace.
    #[code("namespace-reserved")]
    #[message("namespace `{namespace}` is reserved; no key can be pinned for it")]
    NamespaceReserved { namespace: String },
    /// The revocation list, its signature or its artifact cannot be used. The detail is the
    /// sentence of the failure.
    #[code("revocation-list-invalid")]
    #[message("{detail}")]
    ListInvalid { detail: String },
    /// The registry or the network failed, or withheld the revocation list.
    #[code("revocation-list-unavailable")]
    #[message("the revocation list could not be fetched: {detail}")]
    ListUnavailable { detail: String },
    /// The fetched list is past its signed expiry.
    #[code("revocation-list-expired")]
    #[message(
        "the revocation list served online expired at {expires}; the source is replaying an old list"
    )]
    ListExpired { expires: String },
    /// The fetched list is older than the cached one.
    #[code("revocation-list-rollback")]
    #[message(
        "the fetched revocation list (issued {fetched}) is older than the cached one (issued {cached})"
    )]
    ListRollback { cached: String, fetched: String },
    /// Two different signed lists claim the same issue time.
    #[code("revocation-list-equivocation")]
    #[message(
        "the fetched revocation list differs from the cached one with the same issued time ({issued})"
    )]
    ListEquivocation { issued: String },
    /// The cache file does not hold a signed list, or a file operation on it failed. The detail
    /// is the sentence of the failure.
    #[code("revocation-cache-invalid")]
    #[message("{detail}")]
    CacheInvalid { detail: String },
    /// The caller's clock is not a UTC time in the expected form.
    #[code("revocation-clock-invalid")]
    #[message("the current time `{now}` is not YYYY-MM-DDTHH:MM:SSZ")]
    ClockInvalid { now: String },
    /// No revocation list was ever fetched on this machine.
    #[code("revocation-list-missing")]
    #[notice("no revocation list has been fetched; run `slopvac plugins sync` online")]
    ListMissing,
    /// The cached revocation list is past its signed expiry.
    #[code("revocation-list-stale")]
    #[notice(
        "the cached revocation list (issued {issued}) expired at {expires}; run `slopvac plugins sync` online"
    )]
    ListStale { issued: String, expires: String },
}

/// Sentences with parameters: trust store failures, program and environment refusals, and the
/// operations a failure names.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum TrustText {
    /// The store file is unreadable or invalid.
    #[code("plugins-trust-store-damaged")]
    #[text("the trust store {path} is damaged: {why}")]
    StoreDamaged {
        #[display_path]
        path: String,
        why: String,
    },
    /// A file system operation failed.
    #[code("plugins-trust-io")]
    #[text("{what}: {cause}")]
    Io { what: String, cause: String },
    /// `SLOPVAC_TRUST` names something other than a content hash.
    #[code("plugins-trust-not-a-hash")]
    #[text(
        "`{token}` in SLOPVAC_TRUST is not a sha256 content hash; it names hashes only, never a name or a tag"
    )]
    NotAHash { token: String },
    /// A namespace already has a different pinned key.
    #[code("plugins-trust-namespace-bound")]
    #[text(
        "namespace `{namespace}` is already bound to key {existing}; a new key needs a rotation statement signed by the old key"
    )]
    NamespaceBound { namespace: String, existing: String },
    /// The program cannot be tied to the verified tree or the allowlist.
    #[code("plugins-trust-program-refused")]
    #[text("program refused: {why}")]
    ProgramRefused { why: String },
    /// The environment or `PATH` handed to the plugin is not allowed.
    #[code("plugins-trust-environment-refused")]
    #[text("environment refused: {why}")]
    EnvironmentRefused { why: String },
    /// A rotation statement failed verification.
    #[code("plugins-trust-rotation-refused")]
    #[text("rotation refused: {cause}")]
    RotationRefused { cause: String },
    /// A rotation names a namespace that has no pinned key.
    #[code("plugins-trust-not-pinned")]
    #[text("namespace `{namespace}` has no pinned key to rotate; pin one first")]
    NotPinned { namespace: String },
    /// The revocation list names a key the operation needs.
    #[code("plugins-trust-revoked")]
    #[text("{what} is on the revocation list")]
    Revoked { what: String },
    /// A publisher key, named for the revocation list.
    #[code("plugins-trust-revoked-key")]
    #[text("key {id}")]
    RevokedKey { id: String },
    /// A write would push the store past the size the reader accepts.
    #[code("plugins-trust-store-too-large")]
    #[text("the trust store would reach {bytes} bytes; the reader accepts at most 8 MiB")]
    StoreTooLarge {
        #[count]
        bytes: usize,
    },
    /// Trust records exist but the key they were made under is gone.
    #[code("plugins-trust-key-missing")]
    #[text(
        "the trust key {file} is missing while trust records exist, so they cannot be checked; run `slopvac plugins trust` for each plugin to trust it again"
    )]
    KeyMissing {
        #[display_path]
        file: String,
    },
    /// The key file is not private to the user or does not hold a key.
    #[code("plugins-trust-key-unusable")]
    #[text(
        "the trust key {file} cannot be used: {why}; fix it, or delete it and run `slopvac plugins trust` for each plugin"
    )]
    KeyUnusable {
        #[display_path]
        file: String,
        why: String,
    },
    /// The key file belongs to another user.
    #[code("plugins-trust-key-other-user")]
    #[text("it belongs to user {uid}, not to you ({euid})")]
    KeyOtherUser {
        #[count]
        uid: u32,
        #[count]
        euid: u32,
    },
    /// The key file mode is not 600.
    #[code("plugins-trust-key-mode")]
    #[text("its mode is {mode}, not 600")]
    KeyMode { mode: String },
    /// The network setting of a declaration changed.
    #[code("plugins-trust-diff-network")]
    #[text("network: {old} -> {new}")]
    DiffNetwork { old: String, new: String },
    /// A declaration gained an entry.
    #[code("plugins-trust-diff-added")]
    #[text("{label} added: {item}")]
    DiffAdded { label: String, item: String },
    /// A declaration lost an entry.
    #[code("plugins-trust-diff-removed")]
    #[text("{label} removed: {item}")]
    DiffRemoved { label: String, item: String },
    /// The operation of opening a file.
    #[code("plugins-trust-opening")]
    #[text("opening {path}")]
    Opening {
        #[display_path]
        path: String,
    },
    /// The operation of reading a file.
    #[code("plugins-trust-reading")]
    #[text("reading {path}")]
    Reading {
        #[display_path]
        path: String,
    },
    /// The operation of creating a directory.
    #[code("plugins-trust-creating")]
    #[text("creating {path}")]
    Creating {
        #[display_path]
        path: String,
    },
    /// The operation of inspecting a file.
    #[code("plugins-trust-inspecting")]
    #[text("inspecting {path}")]
    Inspecting {
        #[display_path]
        path: String,
    },
    /// A declared environment variable has an invalid name.
    #[code("plugins-trust-env-bad-name")]
    #[text("`{name}` is not a variable name")]
    EnvBadName { name: String },
    /// A declared environment variable can load code into the plugin.
    #[code("plugins-trust-env-forbidden")]
    #[text("`{name}` can load code into the plugin")]
    EnvForbidden { name: String },
    /// A declared environment variable is set twice.
    #[code("plugins-trust-env-duplicate")]
    #[text("`{name}` is set twice")]
    EnvDuplicate { name: String },
    /// A `PATH` entry is relative.
    #[code("plugins-trust-env-path-relative")]
    #[text("PATH entry `{dir}` is not an absolute directory")]
    EnvPathRelative {
        #[display_path]
        dir: String,
    },
    /// The program is a bare or relative path.
    #[code("plugins-trust-program-not-absolute")]
    #[text("`{path}` is not an absolute path; a bare name would be found through PATH")]
    ProgramNotAbsolute {
        #[display_path]
        path: String,
    },
    /// The program path holds `.` or `..`.
    #[code("plugins-trust-program-dots")]
    #[text("`{path}` contains `.` or `..`")]
    ProgramDots {
        #[display_path]
        path: String,
    },
    /// The program is outside the verified tree and not on the allowlist.
    #[code("plugins-trust-program-outside")]
    #[text("`{path}` lies outside the verified tree and is not on the external allowlist")]
    ProgramOutside {
        #[display_path]
        path: String,
    },
    /// The program path has a part that is not a plain name.
    #[code("plugins-trust-program-not-plain")]
    #[text("`{path}` is not a plain path")]
    ProgramNotPlain {
        #[display_path]
        path: String,
    },
    /// A part of the program path could not be inspected.
    #[code("plugins-trust-program-unreadable")]
    #[text("`{path}`: {cause}")]
    ProgramUnreadable {
        #[display_path]
        path: String,
        cause: String,
    },
    /// A part of the program path is a symlink.
    #[code("plugins-trust-program-symlink")]
    #[text("`{path}` is a symlink")]
    ProgramSymlink {
        #[display_path]
        path: String,
    },
    /// The program path is not a file in the tree.
    #[code("plugins-trust-program-not-file")]
    #[text("`{path}` is not a file in the tree")]
    ProgramNotFile {
        #[display_path]
        path: String,
    },
    /// The program is not the managed interpreter.
    #[code("plugins-trust-program-not-managed")]
    #[text("`{program}` is not the managed interpreter `{managed}`")]
    ProgramNotManaged {
        #[display_path]
        program: String,
        #[display_path]
        managed: String,
    },
    /// The plugin does not run from its verified tree.
    #[code("plugins-trust-mismatch-cwd")]
    #[text("{name} (it does not run from its verified tree)")]
    MismatchCwd { name: String },
    /// The tree changed since it was verified.
    #[code("plugins-trust-mismatch-tree-changed")]
    #[text("{name} (tree now {actual}, verified {verified})")]
    MismatchTreeChanged {
        name: String,
        actual: String,
        verified: String,
    },
    /// The tree could not be hashed.
    #[code("plugins-trust-mismatch-tree-refused")]
    #[text("{name} (tree refused: {cause})")]
    MismatchTreeRefused { name: String, cause: String },
    /// A plugin name with a detail in parentheses.
    #[code("plugins-trust-name-with")]
    #[text("{name} ({detail})")]
    NameWith { name: String, detail: String },
    /// A spawn was refused because of the program.
    #[code("plugins-trust-spawn-program-refused")]
    #[text("{name}: program refused: {why}")]
    SpawnProgramRefused { name: String, why: String },
    /// A spawn was refused because of the environment.
    #[code("plugins-trust-spawn-environment-refused")]
    #[text("{name}: environment refused: {why}")]
    SpawnEnvironmentRefused { name: String, why: String },
    /// A spawn was refused because the trust key cannot be used.
    #[code("plugins-trust-spawn-key-unusable")]
    #[text("{name}: {file} ({why})")]
    SpawnKeyUnusable {
        name: String,
        #[display_path]
        file: String,
        why: String,
    },
}

/// Fixed phrases of the trust store: operations, reasons and labels.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum TrustPhrase {
    /// A store file past the size cap.
    #[code("plugins-trust-phrase-store-over-cap")]
    #[text("larger than 8 MiB")]
    StoreOverCap,
    /// A store file with another schema version.
    #[code("plugins-trust-phrase-store-schema")]
    #[text("unsupported schema_version")]
    StoreSchema,
    /// The operation of opening the store lock.
    #[code("plugins-trust-phrase-open-lock")]
    #[text("opening the trust lock")]
    OpenLock,
    /// The operation of locking the store.
    #[code("plugins-trust-phrase-lock-store")]
    #[text("locking the trust store")]
    LockStore,
    /// The operation of creating the temporary store file.
    #[code("plugins-trust-phrase-temp-store")]
    #[text("creating a temporary store file")]
    TempStore,
    /// The operation of writing the store.
    #[code("plugins-trust-phrase-write-store")]
    #[text("writing the trust store")]
    WriteStore,
    /// The operation of syncing the store.
    #[code("plugins-trust-phrase-sync-store")]
    #[text("syncing the trust store")]
    SyncStore,
    /// The operation of replacing the store.
    #[code("plugins-trust-phrase-replace-store")]
    #[text("replacing the trust store")]
    ReplaceStore,
    /// The operation of securing the store directory.
    #[code("plugins-trust-phrase-secure-dir")]
    #[text("securing the trust directory")]
    SecureDir,
    /// The operation of securing the store file.
    #[code("plugins-trust-phrase-secure-file")]
    #[text("securing the trust file")]
    SecureFile,
    /// The operation of creating the temporary key file.
    #[code("plugins-trust-phrase-temp-key")]
    #[text("creating a temporary trust key file")]
    TempKey,
    /// The operation of writing the key.
    #[code("plugins-trust-phrase-write-key")]
    #[text("writing the trust key")]
    WriteKey,
    /// The operation of syncing the key.
    #[code("plugins-trust-phrase-sync-key")]
    #[text("syncing the trust key")]
    SyncKey,
    /// The operation of installing the key.
    #[code("plugins-trust-phrase-install-key")]
    #[text("installing the trust key")]
    InstallKey,
    /// The operation of drawing a random key.
    #[code("plugins-trust-phrase-draw-key")]
    #[text("drawing a trust key from the system")]
    DrawKey,
    /// The key file is a symbolic link.
    #[code("plugins-trust-phrase-key-symlink")]
    #[text("it is a symbolic link")]
    KeySymlink,
    /// The key file is not a regular file.
    #[code("plugins-trust-phrase-key-not-regular")]
    #[text("it is not a regular file")]
    KeyNotRegular,
    /// The key file does not hold a key.
    #[code("plugins-trust-phrase-key-not-hex")]
    #[text("it does not hold a 32-byte key in hex")]
    KeyNotHex,
    /// A trust record was made under another key.
    #[code("plugins-trust-phrase-key-mismatch")]
    #[text(
        "the trust key changed since the trust records were made, so they cannot be checked; run `slopvac plugins trust` for each plugin to trust it again"
    )]
    KeyMismatch,
    /// The declared `PATH` is empty.
    #[code("plugins-trust-phrase-path-empty")]
    #[text("PATH is empty")]
    PathEmpty,
    /// A managed interpreter runs without its isolation flags first.
    #[code("plugins-trust-phrase-python-flags")]
    #[text("a managed interpreter must run with `-I -B` first")]
    PythonFlags,
    /// The label of a hook in a declaration difference.
    #[code("plugins-trust-phrase-label-hook")]
    #[text("hook")]
    LabelHook,
    /// The label of a required feature in a declaration difference.
    #[code("plugins-trust-phrase-label-required")]
    #[text("required feature")]
    LabelRequiredFeature,
    /// The label of an optional feature in a declaration difference.
    #[code("plugins-trust-phrase-label-optional")]
    #[text("optional feature")]
    LabelOptionalFeature,
}

/// Sentences with parameters of signature verification.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum SignText {
    /// The statement is over the size cap.
    #[code("plugins-sign-statement-too-large")]
    #[text("the signed statement is larger than {limit} bytes")]
    StatementTooLarge {
        #[count]
        limit: usize,
    },
    /// The statement is not the canonical encoding of its content.
    #[code("plugins-sign-not-canonical")]
    #[text("the signed statement is not canonical JSON: {why}")]
    NotCanonical { why: String },
    /// The statement does not parse or has unknown fields.
    #[code("plugins-sign-invalid-statement")]
    #[text("the signed statement is invalid: {why}")]
    InvalidStatement { why: String },
    /// No pinned key has the key id of the statement.
    #[code("plugins-sign-key-not-pinned")]
    #[text(
        "key {key_id} is not pinned for namespace `{namespace}`; pin it with `slopvac plugins trust --key <fingerprint>`"
    )]
    KeyNotPinned { key_id: String, namespace: String },
    /// The statement and the manifest disagree.
    #[code("plugins-sign-mismatch")]
    #[text("the signed statement does not match the manifest: {why}")]
    Mismatch { why: String },
    /// An older version or an older `notBefore` than the lockfile holds.
    #[code("plugins-sign-rollback")]
    #[text("rollback refused: {why}")]
    Rollback { why: String },
    /// A public key does not parse.
    #[code("plugins-sign-invalid-key")]
    #[text("invalid public key: {why}")]
    InvalidKey { why: String },
    /// The version of the statement does not parse.
    #[code("plugins-sign-version")]
    #[text("version: {cause}")]
    Version { cause: String },
    /// The version in the lockfile does not parse.
    #[code("plugins-sign-lockfile-version")]
    #[text("lockfile version: {cause}")]
    LockfileVersion { cause: String },
    /// The statement version is older than the lockfile version.
    #[code("plugins-sign-older-version")]
    #[text("{new} is older than {floor}")]
    OlderVersion { new: String, floor: String },
    /// The statement `notBefore` is older than the lockfile one.
    #[code("plugins-sign-older-not-before")]
    #[text("notBefore {not_before} is older than {floor}")]
    OlderNotBefore { not_before: String, floor: String },
    /// A rotation `notBefore` is not later than the pin's.
    #[code("plugins-sign-rotation-not-later")]
    #[text("rotation notBefore {not_before} is not later than the pin's {floor}")]
    RotationNotLater { not_before: String, floor: String },
}

/// Fixed phrases of signature verification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum SignPhrase {
    /// The artifact has no signature layers.
    #[code("plugins-sign-phrase-missing")]
    #[text("the artifact has no signature")]
    Missing,
    /// The artifact has more than one signature layer.
    #[code("plugins-sign-phrase-duplicate")]
    #[text("the artifact has more than one signature layer")]
    Duplicate,
    /// The signature does not verify.
    #[code("plugins-sign-phrase-bad-signature")]
    #[text("the signature does not verify")]
    BadSignature,
    /// The statement re-encodes to other bytes.
    #[code("plugins-sign-phrase-reencoding")]
    #[text("re-encoding differs")]
    Reencoding,
    /// The key is too short.
    #[code("plugins-sign-phrase-short-key")]
    #[text("short key")]
    ShortKey,
    /// The key file has no key line.
    #[code("plugins-sign-phrase-no-key-line")]
    #[text("no key line")]
    NoKeyLine,
    /// The id or namespace is not a lowercase name.
    #[code("plugins-sign-phrase-not-a-name")]
    #[text("id or namespace is not a lowercase name")]
    NotAName,
    /// The statement schema version is not 1.
    #[code("plugins-sign-phrase-schema")]
    #[text("unsupported statement schema_version")]
    Schema,
    /// The layers differ from the signed list.
    #[code("plugins-sign-phrase-layers")]
    #[text("the layers differ from the signed list")]
    Layers,
    /// The config digest differs.
    #[code("plugins-sign-phrase-config")]
    #[text("the config digest differs")]
    Config,
    /// The artifact type differs.
    #[code("plugins-sign-phrase-artifact-type")]
    #[text("the artifact type differs")]
    ArtifactType,
    /// The identity differs from the one requested.
    #[code("plugins-sign-phrase-identity")]
    #[text("the id, namespace or version is not the one requested")]
    Identity,
    /// The manifest annotations differ from the statement.
    #[code("plugins-sign-phrase-annotations")]
    #[text("the manifest annotations differ from the statement")]
    Annotations,
    /// The `notBefore` is not in the expected form.
    #[code("plugins-sign-phrase-not-before-form")]
    #[text("notBefore is not YYYY-MM-DDTHH:MM:SSZ")]
    NotBeforeForm,
    /// The statement version has build metadata.
    #[code("plugins-sign-phrase-build-metadata")]
    #[text("version carries build metadata")]
    BuildMetadata,
    /// The lockfile `notBefore` is not a valid UTC time.
    #[code("plugins-sign-phrase-lockfile-time")]
    #[text("lockfile notBefore is not a valid UTC time")]
    LockfileTime,
    /// The `notBefore` is not a valid UTC time.
    #[code("plugins-sign-phrase-time")]
    #[text("notBefore is not a valid UTC time")]
    Time,
    /// The pin's `notBefore` is not a valid UTC time.
    #[code("plugins-sign-phrase-pin-time")]
    #[text("the pin's notBefore is not a valid UTC time")]
    PinTime,
    /// The statement is not a version 1 rotation.
    #[code("plugins-sign-phrase-not-rotation")]
    #[text("not a version 1 rotation statement")]
    NotRotation,
    /// The rotation namespace or a key id is malformed.
    #[code("plugins-sign-phrase-rotation-ids")]
    #[text("the namespace or a key id is malformed")]
    RotationIds,
    /// The rotation is for another namespace.
    #[code("plugins-sign-phrase-rotation-namespace")]
    #[text("the rotation is for another namespace")]
    RotationNamespace,
    /// The new key is not the one the rotation names.
    #[code("plugins-sign-phrase-rotation-new-key")]
    #[text("the new key is not the one the rotation names, or equals the old key")]
    RotationNewKey,
    /// The new key in the rotation is not a minisign key.
    #[code("plugins-sign-phrase-rotation-key-form")]
    #[text("newKey is not a minisign public key")]
    RotationKeyForm,
    /// The new key differs from the key the rotation binds.
    #[code("plugins-sign-phrase-rotation-bound")]
    #[text("the new key differs from the key the rotation binds")]
    RotationBound,
}

/// Sentences with parameters of the revocation list and its cache.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum RevokeText {
    /// The compiled root key does not parse.
    #[code("plugins-revoke-root-key-unusable")]
    #[text("the compiled first-party root key is unusable: {why}")]
    RootKeyUnusable { why: String },
    /// The list is over the size cap.
    #[code("plugins-revoke-too-large")]
    #[text("the revocation list is larger than {limit} bytes")]
    TooLarge {
        #[count]
        limit: usize,
    },
    /// The list is not a valid version 1 list.
    #[code("plugins-revoke-invalid")]
    #[text("the revocation list is invalid: {why}")]
    Invalid { why: String },
    /// The list artifact has the wrong shape.
    #[code("plugins-revoke-layout")]
    #[text("the revocation list artifact is malformed: {why}")]
    Layout { why: String },
    /// The cache file does not hold a list the root signed.
    #[code("plugins-revoke-cache-damaged")]
    #[text("the revocation cache {path} is damaged: {why}; run an online sync to replace it")]
    CacheDamaged {
        #[display_path]
        path: String,
        why: String,
    },
    /// A file operation on the cache failed.
    #[code("plugins-revoke-cache-io")]
    #[text("revocation cache: {what}: {cause}")]
    CacheIo { what: String, cause: String },
    /// A trust record is revoked by a publisher key.
    #[code("plugins-revoke-flag-key")]
    #[text("revoked: publisher key {id}")]
    FlagKey { id: String },
    /// A trust record is revoked by an artifact digest.
    #[code("plugins-revoke-flag-artifact")]
    #[text("revoked: artifact {digest}")]
    FlagArtifact { digest: String },
}

/// Fixed phrases of the revocation list and its cache.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum RevokePhrase {
    /// No root key is configured.
    #[code("plugins-revoke-phrase-no-root-key")]
    #[text("no first-party root key is configured to verify the revocation list")]
    NoRootKey,
    /// No root key signed the list.
    #[code("plugins-revoke-phrase-bad-signature")]
    #[text("the revocation list is not signed by the first-party root key")]
    BadSignature,
    /// The list is not UTF-8.
    #[code("plugins-revoke-phrase-not-utf8")]
    #[text("the list is not UTF-8")]
    NotUtf8,
    /// The list is not a version 1 list.
    #[code("plugins-revoke-phrase-not-v1")]
    #[text("not a version 1 revocation list")]
    NotVersionOne,
    /// The issue or expiry time is not a valid UTC time.
    #[code("plugins-revoke-phrase-time")]
    #[text("issued or expires is not a valid UTC time")]
    Time,
    /// The expiry is not after the issue time or is more than 30 days later.
    #[code("plugins-revoke-phrase-window")]
    #[text("expires must be after issued by at most 30 days")]
    Window,
    /// A key id has the wrong form.
    #[code("plugins-revoke-phrase-key-id")]
    #[text("a key id is not 16 uppercase hex digits")]
    KeyId,
    /// A digest has the wrong form.
    #[code("plugins-revoke-phrase-digest")]
    #[text("a digest is not sha256 with 64 lowercase hex digits")]
    Digest,
    /// The keys or digests are not sorted and unique.
    #[code("plugins-revoke-phrase-unsorted")]
    #[text("keys and digests must be sorted and unique")]
    Unsorted,
    /// The artifact type is not a list.
    #[code("plugins-revoke-phrase-artifact-type")]
    #[text("the artifact type is not a revocation list")]
    ArtifactType,
    /// The artifact does not have two layers.
    #[code("plugins-revoke-phrase-layer-count")]
    #[text("a list artifact has exactly two layers")]
    LayerCount,
    /// The layers are not a list and its signature.
    #[code("plugins-revoke-phrase-layer-types")]
    #[text("the layers are not a list and its signature")]
    LayerTypes,
    /// The cache file is over the size cap.
    #[code("plugins-revoke-phrase-cache-too-large")]
    #[text("too large")]
    CacheTooLarge,
    /// The cache has another schema version or a bad fetch time.
    #[code("plugins-revoke-phrase-cache-schema")]
    #[text("unsupported schema_version or fetch time")]
    CacheSchema,
    /// The operation of creating the state directory.
    #[code("plugins-revoke-phrase-create-dir")]
    #[text("creating the state directory")]
    CreateDir,
    /// The operation of opening the cache lock.
    #[code("plugins-revoke-phrase-open-lock")]
    #[text("opening the cache lock")]
    OpenLock,
    /// The operation of locking the cache.
    #[code("plugins-revoke-phrase-lock-cache")]
    #[text("locking the cache")]
    LockCache,
    /// The operation of encoding the cache.
    #[code("plugins-revoke-phrase-encode-cache")]
    #[text("encoding the cache")]
    EncodeCache,
    /// The operation of creating the temporary cache file.
    #[code("plugins-revoke-phrase-temp-cache")]
    #[text("creating a temporary cache file")]
    TempCache,
    /// The operation of securing the cache file.
    #[code("plugins-revoke-phrase-secure-cache")]
    #[text("securing the cache file")]
    SecureCache,
    /// The operation of writing the cache.
    #[code("plugins-revoke-phrase-write-cache")]
    #[text("writing the cache")]
    WriteCache,
    /// The operation of syncing the cache.
    #[code("plugins-revoke-phrase-sync-cache")]
    #[text("syncing the cache")]
    SyncCache,
    /// The operation of replacing the cache.
    #[code("plugins-revoke-phrase-replace-cache")]
    #[text("replacing the cache")]
    ReplaceCache,
}

/// Sentences with parameters of the strict JSON reader.
#[derive(Debug, Clone, PartialEq, Eq, Catalog)]
pub(crate) enum StrictText {
    /// An integer is outside the range every JSON reader keeps exact.
    #[code("plugins-strict-integer-range")]
    #[text("integer {value} outside ±(2^53-1)")]
    IntegerRange { value: String },
    /// The nesting is deeper than the cap.
    #[code("plugins-strict-nesting")]
    #[text("nesting deeper than {limit}")]
    Nesting {
        #[count]
        limit: usize,
    },
    /// An object repeats a key.
    #[code("plugins-strict-duplicate-key")]
    #[text("duplicate key `{key}`")]
    DuplicateKey { key: String },
}

/// Fixed phrases of the strict JSON reader.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Catalog)]
pub(crate) enum StrictPhrase {
    /// A number is not finite.
    #[code("plugins-strict-phrase-non-finite")]
    #[text("non-finite number")]
    NonFinite,
    /// What the reader expects at a position.
    #[code("plugins-strict-phrase-expecting")]
    #[text("a JSON value")]
    Expecting,
}

// ---- trust store ----

pub(crate) fn namespace_reserved(namespace: &str) -> String {
    TrustMessage::NamespaceReserved {
        namespace: esc(namespace),
    }
    .to_string()
}

pub(crate) fn store_damaged(path: &Path, why: &str) -> String {
    TrustText::StoreDamaged {
        path: esc(&path.to_string_lossy()),
        why: esc(why),
    }
    .to_string()
}

pub(crate) fn trust_io(what: &str, cause: &str) -> String {
    TrustText::Io {
        what: esc(what),
        cause: esc(cause),
    }
    .to_string()
}

pub(crate) fn not_a_hash(token: &str) -> String {
    TrustText::NotAHash { token: esc(token) }.to_string()
}

pub(crate) fn namespace_bound(namespace: &str, existing: &str) -> String {
    TrustText::NamespaceBound {
        namespace: esc(namespace),
        existing: esc(existing),
    }
    .to_string()
}

pub(crate) fn program_refused(why: &str) -> String {
    TrustText::ProgramRefused { why: esc(why) }.to_string()
}

pub(crate) fn environment_refused(why: &str) -> String {
    TrustText::EnvironmentRefused { why: esc(why) }.to_string()
}

pub(crate) fn rotation_refused(cause: &str) -> String {
    TrustText::RotationRefused {
        cause: cause.to_owned(),
    }
    .to_string()
}

pub(crate) fn not_pinned(namespace: &str) -> String {
    TrustText::NotPinned {
        namespace: namespace.to_owned(),
    }
    .to_string()
}

pub(crate) fn revoked(what: &str) -> String {
    TrustText::Revoked {
        what: what.to_owned(),
    }
    .to_string()
}

pub(crate) fn revoked_key(id: &str) -> String {
    TrustText::RevokedKey { id: id.to_owned() }.to_string()
}

pub(crate) fn store_too_large(bytes: usize) -> String {
    TrustText::StoreTooLarge { bytes }.to_string()
}

pub(crate) fn key_missing(file: &str) -> String {
    TrustText::KeyMissing { file: esc(file) }.to_string()
}

pub(crate) fn key_unusable(file: &str, why: &str) -> String {
    TrustText::KeyUnusable {
        file: esc(file),
        why: esc(why),
    }
    .to_string()
}

pub(crate) fn key_mismatch() -> String {
    TrustPhrase::KeyMismatch.as_static().to_owned()
}

pub(crate) fn key_other_user(uid: u32, euid: u32) -> String {
    TrustText::KeyOtherUser { uid, euid }.to_string()
}

pub(crate) fn key_mode(bits: u32) -> String {
    TrustText::KeyMode {
        mode: format!("{bits:03o}"),
    }
    .to_string()
}

pub(crate) fn diff_network(old: bool, new: bool) -> String {
    TrustText::DiffNetwork {
        old: old.to_string(),
        new: new.to_string(),
    }
    .to_string()
}

pub(crate) fn diff_added(label: &str, item: &str) -> String {
    TrustText::DiffAdded {
        label: label.to_owned(),
        item: esc(item),
    }
    .to_string()
}

pub(crate) fn diff_removed(label: &str, item: &str) -> String {
    TrustText::DiffRemoved {
        label: label.to_owned(),
        item: esc(item),
    }
    .to_string()
}

pub(crate) fn opening(path: &str) -> String {
    TrustText::Opening {
        path: path.to_owned(),
    }
    .to_string()
}

pub(crate) fn reading(path: &str) -> String {
    TrustText::Reading {
        path: path.to_owned(),
    }
    .to_string()
}

pub(crate) fn creating(path: &str) -> String {
    TrustText::Creating {
        path: path.to_owned(),
    }
    .to_string()
}

pub(crate) fn inspecting(path: &str) -> String {
    TrustText::Inspecting {
        path: path.to_owned(),
    }
    .to_string()
}

pub(crate) fn env_bad_name(name: &str) -> String {
    TrustText::EnvBadName {
        name: name.to_owned(),
    }
    .to_string()
}

pub(crate) fn env_forbidden(name: &str) -> String {
    TrustText::EnvForbidden {
        name: name.to_owned(),
    }
    .to_string()
}

pub(crate) fn env_duplicate(name: &str) -> String {
    TrustText::EnvDuplicate {
        name: name.to_owned(),
    }
    .to_string()
}

pub(crate) fn env_path_relative(dir: &Path) -> String {
    TrustText::EnvPathRelative {
        dir: dir.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_not_absolute(path: &Path) -> String {
    TrustText::ProgramNotAbsolute {
        path: path.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_dots(path: &Path) -> String {
    TrustText::ProgramDots {
        path: path.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_outside(path: &Path) -> String {
    TrustText::ProgramOutside {
        path: path.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_not_plain(path: &Path) -> String {
    TrustText::ProgramNotPlain {
        path: path.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_unreadable(path: &Path, cause: &str) -> String {
    TrustText::ProgramUnreadable {
        path: path.display().to_string(),
        cause: cause.to_owned(),
    }
    .to_string()
}

pub(crate) fn program_symlink(path: &Path) -> String {
    TrustText::ProgramSymlink {
        path: path.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_not_file(path: &Path) -> String {
    TrustText::ProgramNotFile {
        path: path.display().to_string(),
    }
    .to_string()
}

pub(crate) fn program_not_managed(program: &Path, managed: &Path) -> String {
    TrustText::ProgramNotManaged {
        program: program.display().to_string(),
        managed: managed.display().to_string(),
    }
    .to_string()
}

pub(crate) fn mismatch_cwd(name: &str) -> String {
    TrustText::MismatchCwd {
        name: name.to_owned(),
    }
    .to_string()
}

pub(crate) fn mismatch_tree_changed(name: &str, actual: &str, verified: &str) -> String {
    TrustText::MismatchTreeChanged {
        name: name.to_owned(),
        actual: actual.to_owned(),
        verified: verified.to_owned(),
    }
    .to_string()
}

pub(crate) fn mismatch_tree_refused(name: &str, cause: &str) -> String {
    TrustText::MismatchTreeRefused {
        name: name.to_owned(),
        cause: cause.to_owned(),
    }
    .to_string()
}

pub(crate) fn name_with(name: &str, detail: &str) -> String {
    TrustText::NameWith {
        name: name.to_owned(),
        detail: detail.to_owned(),
    }
    .to_string()
}

pub(crate) fn spawn_program_refused(name: &str, why: &str) -> String {
    TrustText::SpawnProgramRefused {
        name: name.to_owned(),
        why: why.to_owned(),
    }
    .to_string()
}

pub(crate) fn spawn_environment_refused(name: &str, why: &str) -> String {
    TrustText::SpawnEnvironmentRefused {
        name: name.to_owned(),
        why: why.to_owned(),
    }
    .to_string()
}

pub(crate) fn spawn_key_unusable(name: &str, file: &str, why: &str) -> String {
    TrustText::SpawnKeyUnusable {
        name: name.to_owned(),
        file: file.to_owned(),
        why: why.to_owned(),
    }
    .to_string()
}

// ---- signatures ----

pub(crate) fn statement_too_large(limit: usize) -> String {
    SignText::StatementTooLarge { limit }.to_string()
}

/// The canonical-JSON failure with `why` as it is, for a caller that escapes the whole text once.
pub(crate) fn sign_not_canonical_raw(why: &str) -> String {
    SignText::NotCanonical {
        why: why.to_owned(),
    }
    .to_string()
}

pub(crate) fn sign_not_canonical(why: &str) -> String {
    sign_not_canonical_raw(&esc(why))
}

/// The invalid-statement failure with `why` as it is, for a caller that escapes the whole text
/// once.
pub(crate) fn sign_invalid_statement_raw(why: &str) -> String {
    SignText::InvalidStatement {
        why: why.to_owned(),
    }
    .to_string()
}

pub(crate) fn sign_invalid_statement(why: &str) -> String {
    sign_invalid_statement_raw(&esc(why))
}

pub(crate) fn key_not_pinned(key_id: &str, namespace: &str) -> String {
    SignText::KeyNotPinned {
        key_id: esc(key_id),
        namespace: esc(namespace),
    }
    .to_string()
}

pub(crate) fn sign_mismatch(why: &str) -> String {
    SignText::Mismatch { why: esc(why) }.to_string()
}

pub(crate) fn sign_rollback(why: &str) -> String {
    SignText::Rollback { why: esc(why) }.to_string()
}

pub(crate) fn invalid_key(why: &str) -> String {
    SignText::InvalidKey { why: esc(why) }.to_string()
}

pub(crate) fn sign_version(cause: &str) -> String {
    SignText::Version {
        cause: cause.to_owned(),
    }
    .to_string()
}

pub(crate) fn sign_lockfile_version(cause: &str) -> String {
    SignText::LockfileVersion {
        cause: cause.to_owned(),
    }
    .to_string()
}

pub(crate) fn older_version(new: &str, floor: &str) -> String {
    SignText::OlderVersion {
        new: new.to_owned(),
        floor: floor.to_owned(),
    }
    .to_string()
}

pub(crate) fn older_not_before(not_before: &str, floor: &str) -> String {
    SignText::OlderNotBefore {
        not_before: not_before.to_owned(),
        floor: floor.to_owned(),
    }
    .to_string()
}

pub(crate) fn rotation_not_later(not_before: &str, floor: &str) -> String {
    SignText::RotationNotLater {
        not_before: not_before.to_owned(),
        floor: floor.to_owned(),
    }
    .to_string()
}

// ---- revocation ----

fn list_invalid(detail: String) -> String {
    TrustMessage::ListInvalid { detail }.to_string()
}

pub(crate) fn revoke_no_root_key() -> String {
    list_invalid(RevokePhrase::NoRootKey.as_static().to_owned())
}

pub(crate) fn revoke_root_key_unusable(why: &str) -> String {
    list_invalid(
        RevokeText::RootKeyUnusable {
            why: why.to_owned(),
        }
        .to_string(),
    )
}

pub(crate) fn revoke_too_large(limit: usize) -> String {
    list_invalid(RevokeText::TooLarge { limit }.to_string())
}

/// The invalid-list failure with `why` as it is, for a caller that escapes the whole text once.
pub(crate) fn revoke_invalid_raw(why: &str) -> String {
    RevokeText::Invalid {
        why: why.to_owned(),
    }
    .to_string()
}

pub(crate) fn revoke_invalid(why: &str) -> String {
    list_invalid(revoke_invalid_raw(&esc(why)))
}

pub(crate) fn revoke_bad_signature() -> String {
    list_invalid(RevokePhrase::BadSignature.as_static().to_owned())
}

/// The malformed-artifact failure with `why` as it is, for a caller that escapes the whole
/// text once.
pub(crate) fn revoke_layout_raw(why: &str) -> String {
    RevokeText::Layout {
        why: why.to_owned(),
    }
    .to_string()
}

pub(crate) fn revoke_layout(why: &str) -> String {
    list_invalid(revoke_layout_raw(&esc(why)))
}

pub(crate) fn revoke_unavailable(detail: &str) -> String {
    TrustMessage::ListUnavailable {
        detail: detail.to_owned(),
    }
    .to_string()
}

pub(crate) fn revoke_expired(expires: &str) -> String {
    TrustMessage::ListExpired {
        expires: esc(expires),
    }
    .to_string()
}

pub(crate) fn revoke_rollback(cached: &str, fetched: &str) -> String {
    TrustMessage::ListRollback {
        cached: esc(cached),
        fetched: esc(fetched),
    }
    .to_string()
}

pub(crate) fn revoke_equivocation(issued: &str) -> String {
    TrustMessage::ListEquivocation {
        issued: esc(issued),
    }
    .to_string()
}

pub(crate) fn revoke_cache_damaged(path: &Path, why: &str) -> String {
    TrustMessage::CacheInvalid {
        detail: RevokeText::CacheDamaged {
            path: esc(&path.to_string_lossy()),
            why: esc(why),
        }
        .to_string(),
    }
    .to_string()
}

pub(crate) fn revoke_cache_io(what: &str, cause: &str) -> String {
    TrustMessage::CacheInvalid {
        detail: RevokeText::CacheIo {
            what: esc(what),
            cause: esc(cause),
        }
        .to_string(),
    }
    .to_string()
}

pub(crate) fn revoke_clock(now: &str) -> String {
    TrustMessage::ClockInvalid { now: esc(now) }.to_string()
}

pub(crate) fn revoke_flag_key(id: &str) -> String {
    RevokeText::FlagKey { id: esc(id) }.to_string()
}

pub(crate) fn revoke_flag_artifact(digest: &str) -> String {
    RevokeText::FlagArtifact {
        digest: esc(digest),
    }
    .to_string()
}

pub(crate) fn revoke_notice_missing() -> String {
    TrustMessage::ListMissing.to_string()
}

pub(crate) fn revoke_notice_stale(issued: &str, expires: &str) -> String {
    TrustMessage::ListStale {
        issued: esc(issued),
        expires: esc(expires),
    }
    .to_string()
}

// ---- strict JSON ----

pub(crate) fn strict_integer_range(value: &str) -> String {
    StrictText::IntegerRange {
        value: value.to_owned(),
    }
    .to_string()
}

pub(crate) fn strict_nesting(limit: usize) -> String {
    StrictText::Nesting { limit }.to_string()
}

pub(crate) fn strict_duplicate_key(key: &str) -> String {
    StrictText::DuplicateKey {
        key: key.to_owned(),
    }
    .to_string()
}

/// The entries of every trust catalog.
pub(super) fn entries() -> Vec<Entry> {
    [
        TrustMessage::entries(),
        TrustText::entries(),
        TrustPhrase::entries(),
        SignText::entries(),
        SignPhrase::entries(),
        RevokeText::entries(),
        RevokePhrase::entries(),
        StrictText::entries(),
        StrictPhrase::entries(),
    ]
    .concat()
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
        let messages: Vec<(TrustMessage, &str, &str)> = vec![
            (
                TrustMessage::NamespaceReserved {
                    namespace: s("core"),
                },
                "namespace-reserved",
                "namespace `core` is reserved; no key can be pinned for it",
            ),
            (
                TrustMessage::ListInvalid { detail: s("d") },
                "revocation-list-invalid",
                "d",
            ),
            (
                TrustMessage::ListUnavailable { detail: s("down") },
                "revocation-list-unavailable",
                "the revocation list could not be fetched: down",
            ),
            (
                TrustMessage::ListExpired {
                    expires: s("2026-01-02T03:04:05Z"),
                },
                "revocation-list-expired",
                "the revocation list served online expired at 2026-01-02T03:04:05Z; the source is replaying an old list",
            ),
            (
                TrustMessage::ListRollback {
                    cached: s("C"),
                    fetched: s("F"),
                },
                "revocation-list-rollback",
                "the fetched revocation list (issued F) is older than the cached one (issued C)",
            ),
            (
                TrustMessage::ListEquivocation { issued: s("I") },
                "revocation-list-equivocation",
                "the fetched revocation list differs from the cached one with the same issued time (I)",
            ),
            (
                TrustMessage::CacheInvalid { detail: s("d") },
                "revocation-cache-invalid",
                "d",
            ),
            (
                TrustMessage::ClockInvalid { now: s("x") },
                "revocation-clock-invalid",
                "the current time `x` is not YYYY-MM-DDTHH:MM:SSZ",
            ),
            (
                TrustMessage::ListMissing,
                "revocation-list-missing",
                "no revocation list has been fetched; run `slopvac plugins sync` online",
            ),
            (
                TrustMessage::ListStale {
                    issued: s("I"),
                    expires: s("E"),
                },
                "revocation-list-stale",
                "the cached revocation list (issued I) expired at E; run `slopvac plugins sync` online",
            ),
        ];
        let all = registered();
        for (message, code, text) in &messages {
            assert_eq!(message.code(), *code);
            assert_eq!(message.to_string(), *text);
            assert!(all.iter().any(|e| e.code == *code), "{code}");
        }
        let constants = [
            codes::NAMESPACE_RESERVED,
            codes::LIST_INVALID,
            codes::LIST_UNAVAILABLE,
            codes::LIST_EXPIRED,
            codes::LIST_ROLLBACK,
            codes::LIST_EQUIVOCATION,
            codes::CACHE_INVALID,
            codes::CLOCK_INVALID,
            codes::LIST_MISSING,
            codes::LIST_STALE,
        ];
        assert_eq!(constants.len(), messages.len());
        for (constant, (_, code, _)) in constants.iter().zip(&messages) {
            assert_eq!(constant, code);
        }
    }

    #[test]
    #[expect(
        clippy::too_many_lines,
        reason = "one table pins every published text; splitting it would only move rows"
    )]
    fn trust_sentences_keep_their_text_and_are_registered() {
        let texts: Vec<(TrustText, &str)> = vec![
            (
                TrustText::StoreDamaged {
                    path: s("/s/trust.json"),
                    why: s("bad"),
                },
                "the trust store /s/trust.json is damaged: bad",
            ),
            (
                TrustText::Io {
                    what: s("writing"),
                    cause: s("denied"),
                },
                "writing: denied",
            ),
            (
                TrustText::NotAHash { token: s("abc") },
                "`abc` in SLOPVAC_TRUST is not a sha256 content hash; it names hashes only, never a name or a tag",
            ),
            (
                TrustText::NamespaceBound {
                    namespace: s("acme"),
                    existing: s("ff"),
                },
                "namespace `acme` is already bound to key ff; a new key needs a rotation statement signed by the old key",
            ),
            (
                TrustText::ProgramRefused { why: s("w") },
                "program refused: w",
            ),
            (
                TrustText::EnvironmentRefused { why: s("w") },
                "environment refused: w",
            ),
            (
                TrustText::RotationRefused { cause: s("c") },
                "rotation refused: c",
            ),
            (
                TrustText::NotPinned {
                    namespace: s("acme"),
                },
                "namespace `acme` has no pinned key to rotate; pin one first",
            ),
            (
                TrustText::Revoked { what: s("key A") },
                "key A is on the revocation list",
            ),
            (TrustText::RevokedKey { id: s("A") }, "key A"),
            (
                TrustText::StoreTooLarge { bytes: 9_000_000 },
                "the trust store would reach 9000000 bytes; the reader accepts at most 8 MiB",
            ),
            (
                TrustText::KeyMissing {
                    file: s("trust.key"),
                },
                "the trust key trust.key is missing while trust records exist, so they cannot be checked; run `slopvac plugins trust` for each plugin to trust it again",
            ),
            (
                TrustText::KeyUnusable {
                    file: s("trust.key"),
                    why: s("w"),
                },
                "the trust key trust.key cannot be used: w; fix it, or delete it and run `slopvac plugins trust` for each plugin",
            ),
            (
                TrustText::KeyOtherUser {
                    uid: 1001,
                    euid: 1000,
                },
                "it belongs to user 1001, not to you (1000)",
            ),
            (
                TrustText::KeyMode { mode: s("644") },
                "its mode is 644, not 600",
            ),
            (
                TrustText::DiffNetwork {
                    old: s("false"),
                    new: s("true"),
                },
                "network: false -> true",
            ),
            (
                TrustText::DiffAdded {
                    label: s("hook"),
                    item: s("x"),
                },
                "hook added: x",
            ),
            (
                TrustText::DiffRemoved {
                    label: s("hook"),
                    item: s("x"),
                },
                "hook removed: x",
            ),
            (TrustText::Opening { path: s("p") }, "opening p"),
            (TrustText::Reading { path: s("p") }, "reading p"),
            (TrustText::Creating { path: s("p") }, "creating p"),
            (TrustText::Inspecting { path: s("p") }, "inspecting p"),
            (
                TrustText::EnvBadName { name: s("A=B") },
                "`A=B` is not a variable name",
            ),
            (
                TrustText::EnvForbidden { name: s("LD_X") },
                "`LD_X` can load code into the plugin",
            ),
            (TrustText::EnvDuplicate { name: s("X") }, "`X` is set twice"),
            (
                TrustText::EnvPathRelative { dir: s("bin") },
                "PATH entry `bin` is not an absolute directory",
            ),
            (
                TrustText::ProgramNotAbsolute { path: s("run") },
                "`run` is not an absolute path; a bare name would be found through PATH",
            ),
            (
                TrustText::ProgramDots { path: s("/a/../b") },
                "`/a/../b` contains `.` or `..`",
            ),
            (
                TrustText::ProgramOutside { path: s("/bin/sh") },
                "`/bin/sh` lies outside the verified tree and is not on the external allowlist",
            ),
            (
                TrustText::ProgramNotPlain { path: s("/a") },
                "`/a` is not a plain path",
            ),
            (
                TrustText::ProgramUnreadable {
                    path: s("/a"),
                    cause: s("gone"),
                },
                "`/a`: gone",
            ),
            (
                TrustText::ProgramSymlink { path: s("/a") },
                "`/a` is a symlink",
            ),
            (
                TrustText::ProgramNotFile { path: s("/a") },
                "`/a` is not a file in the tree",
            ),
            (
                TrustText::ProgramNotManaged {
                    program: s("/a"),
                    managed: s("/b"),
                },
                "`/a` is not the managed interpreter `/b`",
            ),
            (
                TrustText::MismatchCwd { name: s("p") },
                "p (it does not run from its verified tree)",
            ),
            (
                TrustText::MismatchTreeChanged {
                    name: s("p"),
                    actual: s("A"),
                    verified: s("V"),
                },
                "p (tree now A, verified V)",
            ),
            (
                TrustText::MismatchTreeRefused {
                    name: s("p"),
                    cause: s("c"),
                },
                "p (tree refused: c)",
            ),
            (
                TrustText::NameWith {
                    name: s("p"),
                    detail: s("d"),
                },
                "p (d)",
            ),
            (
                TrustText::SpawnProgramRefused {
                    name: s("p"),
                    why: s("w"),
                },
                "p: program refused: w",
            ),
            (
                TrustText::SpawnEnvironmentRefused {
                    name: s("p"),
                    why: s("w"),
                },
                "p: environment refused: w",
            ),
            (
                TrustText::SpawnKeyUnusable {
                    name: s("p"),
                    file: s("f"),
                    why: s("w"),
                },
                "p: f (w)",
            ),
        ];
        let all = registered();
        for (text, expected) in &texts {
            assert_eq!(text.to_string(), *expected);
            assert!(all.iter().any(|e| e.code == text.code()), "{}", text.code());
        }
        assert_eq!(TrustText::entries().len(), texts.len());
    }

    #[test]
    fn trust_phrases_keep_their_text_and_are_registered() {
        let phrases = [
            (TrustPhrase::StoreOverCap, "larger than 8 MiB"),
            (TrustPhrase::StoreSchema, "unsupported schema_version"),
            (TrustPhrase::OpenLock, "opening the trust lock"),
            (TrustPhrase::LockStore, "locking the trust store"),
            (TrustPhrase::TempStore, "creating a temporary store file"),
            (TrustPhrase::WriteStore, "writing the trust store"),
            (TrustPhrase::SyncStore, "syncing the trust store"),
            (TrustPhrase::ReplaceStore, "replacing the trust store"),
            (TrustPhrase::SecureDir, "securing the trust directory"),
            (TrustPhrase::SecureFile, "securing the trust file"),
            (TrustPhrase::TempKey, "creating a temporary trust key file"),
            (TrustPhrase::WriteKey, "writing the trust key"),
            (TrustPhrase::SyncKey, "syncing the trust key"),
            (TrustPhrase::InstallKey, "installing the trust key"),
            (TrustPhrase::DrawKey, "drawing a trust key from the system"),
            (TrustPhrase::KeySymlink, "it is a symbolic link"),
            (TrustPhrase::KeyNotRegular, "it is not a regular file"),
            (
                TrustPhrase::KeyNotHex,
                "it does not hold a 32-byte key in hex",
            ),
            (
                TrustPhrase::KeyMismatch,
                "the trust key changed since the trust records were made, so they cannot be checked; run `slopvac plugins trust` for each plugin to trust it again",
            ),
            (TrustPhrase::PathEmpty, "PATH is empty"),
            (
                TrustPhrase::PythonFlags,
                "a managed interpreter must run with `-I -B` first",
            ),
            (TrustPhrase::LabelHook, "hook"),
            (TrustPhrase::LabelRequiredFeature, "required feature"),
            (TrustPhrase::LabelOptionalFeature, "optional feature"),
        ];
        let all = registered();
        for (phrase, expected) in phrases {
            assert_eq!(phrase.as_static(), expected);
            assert!(all.iter().any(|e| e.code == phrase.code()));
        }
        assert_eq!(TrustPhrase::entries().len(), phrases.len());
    }

    #[test]
    fn sign_sentences_keep_their_text_and_are_registered() {
        let texts: Vec<(SignText, &str)> = vec![
            (
                SignText::StatementTooLarge { limit: 65_536 },
                "the signed statement is larger than 65536 bytes",
            ),
            (
                SignText::NotCanonical { why: s("w") },
                "the signed statement is not canonical JSON: w",
            ),
            (
                SignText::InvalidStatement { why: s("w") },
                "the signed statement is invalid: w",
            ),
            (
                SignText::KeyNotPinned {
                    key_id: s("AB"),
                    namespace: s("acme"),
                },
                "key AB is not pinned for namespace `acme`; pin it with `slopvac plugins trust --key <fingerprint>`",
            ),
            (
                SignText::Mismatch { why: s("w") },
                "the signed statement does not match the manifest: w",
            ),
            (SignText::Rollback { why: s("w") }, "rollback refused: w"),
            (
                SignText::InvalidKey { why: s("w") },
                "invalid public key: w",
            ),
            (SignText::Version { cause: s("c") }, "version: c"),
            (
                SignText::LockfileVersion { cause: s("c") },
                "lockfile version: c",
            ),
            (
                SignText::OlderVersion {
                    new: s("1.0.0"),
                    floor: s("2.0.0"),
                },
                "1.0.0 is older than 2.0.0",
            ),
            (
                SignText::OlderNotBefore {
                    not_before: s("N"),
                    floor: s("F"),
                },
                "notBefore N is older than F",
            ),
            (
                SignText::RotationNotLater {
                    not_before: s("N"),
                    floor: s("F"),
                },
                "rotation notBefore N is not later than the pin's F",
            ),
        ];
        let all = registered();
        for (text, expected) in &texts {
            assert_eq!(text.to_string(), *expected);
            assert!(all.iter().any(|e| e.code == text.code()), "{}", text.code());
        }
        assert_eq!(SignText::entries().len(), texts.len());
    }

    #[test]
    fn sign_phrases_keep_their_text_and_are_registered() {
        let phrases = [
            (SignPhrase::Missing, "the artifact has no signature"),
            (
                SignPhrase::Duplicate,
                "the artifact has more than one signature layer",
            ),
            (SignPhrase::BadSignature, "the signature does not verify"),
            (SignPhrase::Reencoding, "re-encoding differs"),
            (SignPhrase::ShortKey, "short key"),
            (SignPhrase::NoKeyLine, "no key line"),
            (
                SignPhrase::NotAName,
                "id or namespace is not a lowercase name",
            ),
            (SignPhrase::Schema, "unsupported statement schema_version"),
            (SignPhrase::Layers, "the layers differ from the signed list"),
            (SignPhrase::Config, "the config digest differs"),
            (SignPhrase::ArtifactType, "the artifact type differs"),
            (
                SignPhrase::Identity,
                "the id, namespace or version is not the one requested",
            ),
            (
                SignPhrase::Annotations,
                "the manifest annotations differ from the statement",
            ),
            (
                SignPhrase::NotBeforeForm,
                "notBefore is not YYYY-MM-DDTHH:MM:SSZ",
            ),
            (SignPhrase::BuildMetadata, "version carries build metadata"),
            (
                SignPhrase::LockfileTime,
                "lockfile notBefore is not a valid UTC time",
            ),
            (SignPhrase::Time, "notBefore is not a valid UTC time"),
            (
                SignPhrase::PinTime,
                "the pin's notBefore is not a valid UTC time",
            ),
            (
                SignPhrase::NotRotation,
                "not a version 1 rotation statement",
            ),
            (
                SignPhrase::RotationIds,
                "the namespace or a key id is malformed",
            ),
            (
                SignPhrase::RotationNamespace,
                "the rotation is for another namespace",
            ),
            (
                SignPhrase::RotationNewKey,
                "the new key is not the one the rotation names, or equals the old key",
            ),
            (
                SignPhrase::RotationKeyForm,
                "newKey is not a minisign public key",
            ),
            (
                SignPhrase::RotationBound,
                "the new key differs from the key the rotation binds",
            ),
        ];
        let all = registered();
        for (phrase, expected) in phrases {
            assert_eq!(phrase.as_static(), expected);
            assert!(all.iter().any(|e| e.code == phrase.code()));
        }
        assert_eq!(SignPhrase::entries().len(), phrases.len());
    }

    #[test]
    fn revoke_sentences_keep_their_text_and_are_registered() {
        let texts: Vec<(RevokeText, &str)> = vec![
            (
                RevokeText::RootKeyUnusable { why: s("w") },
                "the compiled first-party root key is unusable: w",
            ),
            (
                RevokeText::TooLarge { limit: 1_048_576 },
                "the revocation list is larger than 1048576 bytes",
            ),
            (
                RevokeText::Invalid { why: s("w") },
                "the revocation list is invalid: w",
            ),
            (
                RevokeText::Layout { why: s("w") },
                "the revocation list artifact is malformed: w",
            ),
            (
                RevokeText::CacheDamaged {
                    path: s("/c/r.json"),
                    why: s("w"),
                },
                "the revocation cache /c/r.json is damaged: w; run an online sync to replace it",
            ),
            (
                RevokeText::CacheIo {
                    what: s("writing the cache"),
                    cause: s("denied"),
                },
                "revocation cache: writing the cache: denied",
            ),
            (
                RevokeText::FlagKey { id: s("AB") },
                "revoked: publisher key AB",
            ),
            (
                RevokeText::FlagArtifact {
                    digest: s("sha256:ab"),
                },
                "revoked: artifact sha256:ab",
            ),
        ];
        let all = registered();
        for (text, expected) in &texts {
            assert_eq!(text.to_string(), *expected);
            assert!(all.iter().any(|e| e.code == text.code()), "{}", text.code());
        }
        assert_eq!(RevokeText::entries().len(), texts.len());
    }

    #[test]
    fn revoke_phrases_keep_their_text_and_are_registered() {
        let phrases = [
            (
                RevokePhrase::NoRootKey,
                "no first-party root key is configured to verify the revocation list",
            ),
            (
                RevokePhrase::BadSignature,
                "the revocation list is not signed by the first-party root key",
            ),
            (RevokePhrase::NotUtf8, "the list is not UTF-8"),
            (
                RevokePhrase::NotVersionOne,
                "not a version 1 revocation list",
            ),
            (
                RevokePhrase::Time,
                "issued or expires is not a valid UTC time",
            ),
            (
                RevokePhrase::Window,
                "expires must be after issued by at most 30 days",
            ),
            (
                RevokePhrase::KeyId,
                "a key id is not 16 uppercase hex digits",
            ),
            (
                RevokePhrase::Digest,
                "a digest is not sha256 with 64 lowercase hex digits",
            ),
            (
                RevokePhrase::Unsorted,
                "keys and digests must be sorted and unique",
            ),
            (
                RevokePhrase::ArtifactType,
                "the artifact type is not a revocation list",
            ),
            (
                RevokePhrase::LayerCount,
                "a list artifact has exactly two layers",
            ),
            (
                RevokePhrase::LayerTypes,
                "the layers are not a list and its signature",
            ),
            (RevokePhrase::CacheTooLarge, "too large"),
            (
                RevokePhrase::CacheSchema,
                "unsupported schema_version or fetch time",
            ),
            (RevokePhrase::CreateDir, "creating the state directory"),
            (RevokePhrase::OpenLock, "opening the cache lock"),
            (RevokePhrase::LockCache, "locking the cache"),
            (RevokePhrase::EncodeCache, "encoding the cache"),
            (RevokePhrase::TempCache, "creating a temporary cache file"),
            (RevokePhrase::SecureCache, "securing the cache file"),
            (RevokePhrase::WriteCache, "writing the cache"),
            (RevokePhrase::SyncCache, "syncing the cache"),
            (RevokePhrase::ReplaceCache, "replacing the cache"),
        ];
        let all = registered();
        for (phrase, expected) in phrases {
            assert_eq!(phrase.as_static(), expected);
            assert!(all.iter().any(|e| e.code == phrase.code()));
        }
        assert_eq!(RevokePhrase::entries().len(), phrases.len());
    }

    #[test]
    fn strict_messages_keep_their_text_and_are_registered() {
        let texts: Vec<(StrictText, &str)> = vec![
            (
                StrictText::IntegerRange {
                    value: s("9007199254740992"),
                },
                "integer 9007199254740992 outside ±(2^53-1)",
            ),
            (StrictText::Nesting { limit: 64 }, "nesting deeper than 64"),
            (
                StrictText::DuplicateKey { key: s("a") },
                "duplicate key `a`",
            ),
        ];
        let all = registered();
        for (text, expected) in &texts {
            assert_eq!(text.to_string(), *expected);
            assert!(all.iter().any(|e| e.code == text.code()), "{}", text.code());
        }
        assert_eq!(StrictText::entries().len(), texts.len());
        let phrases = [
            (StrictPhrase::NonFinite, "non-finite number"),
            (StrictPhrase::Expecting, "a JSON value"),
        ];
        for (phrase, expected) in phrases {
            assert_eq!(phrase.as_static(), expected);
            assert!(all.iter().any(|e| e.code == phrase.code()));
        }
        assert_eq!(StrictPhrase::entries().len(), phrases.len());
    }

    #[test]
    fn every_registered_code_is_unique() {
        let all = registered();
        let mut codes: Vec<_> = all.iter().map(|e| e.code).collect();
        codes.sort_unstable();
        let before = codes.len();
        codes.dedup();
        assert_eq!(codes.len(), before);
    }

    /// An ESC byte in a namespace shows as the escape `slopvac_sanitize::line` documents for a
    /// control character, `\u{1b}`, and the template text around it stays as it was.
    #[test]
    fn a_control_character_in_a_namespace_is_still_escaped() {
        assert_eq!(
            namespace_reserved("a\u{1b}b"),
            "namespace `a\\u{1b}b` is reserved; no key can be pinned for it"
        );
        assert_eq!(program_refused("a\nb"), "program refused: a\\u{a}b");
    }
}
