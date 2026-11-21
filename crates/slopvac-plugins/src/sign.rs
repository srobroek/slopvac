//! Signed statements for packs and plugins (threat model sections 5.1 to 5.3).
//!
//! A layer cannot sign the manifest that holds it, so a minisign signature
//! covers a canonical JSON *statement* that names the manifest's other content.
//! The verifier recomputes the match. The statement and the `.minisig` text are
//! two layers of the artifact, found by media type.
//!
//! Key authority never comes from the pack index. A key is accepted only from
//! the keys compiled into the binary (first-party namespaces) or from the keys
//! the user pinned, which [`KeyPolicy`] carries.
//!
//! Decisions recorded here, as the threat model asked of `slopvac-8l4.9.5`:
//!
//! - The artifact id is the pack id from its manifest. The namespace is the owner segment of
//!   the repository, and it is signed too, so a signed artifact cannot be passed off under
//!   another owner. Keys are pinned per namespace.
//! - The signature layers use the media types [`MEDIA_STATEMENT`] and [`MEDIA_MINISIG`].
//! - An artifact has exactly one layer of each. They are never listed in the statement.
//! - The minisign trusted comment is signed but never used to decide anything.

use std::collections::BTreeMap;

use std::fmt::Write as _;

use base64::Engine as _;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

use crate::messages::trust::{self as messages, SignPhrase};
use crate::oci::{Client, Descriptor, Digest, Manifest, OciError, Reference};
use crate::strict;

/// Media type of the layer that holds the canonical statement.
pub const MEDIA_STATEMENT: &str = "application/vnd.slopvac.signature.statement.v1+json";
/// Media type of the layer that holds the `.minisig` text.
pub const MEDIA_MINISIG: &str = "application/vnd.slopvac.signature.minisig.v1";
/// Manifest annotation that repeats the artifact id.
pub const ANNOTATION_ID: &str = "dev.slopvac.id";
/// Manifest annotation that repeats the artifact version.
pub const ANNOTATION_VERSION: &str = "dev.slopvac.version";
/// Largest statement the verifier reads.
pub const MAX_STATEMENT_BYTES: usize = 64 * 1024;
const MAX_MINISIG_BYTES: usize = 4 * 1024;

/// Why an artifact failed verification. All of these make `sync` exit 2.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum SignError {
    /// The artifact has no signature layers.
    #[error("{}", SignPhrase::Missing.as_static())]
    MissingSignature,
    /// More than one statement layer or signature layer.
    #[error("{}", SignPhrase::Duplicate.as_static())]
    DuplicateSignature,
    /// The statement is over 64 KiB.
    #[error("{}", messages::statement_too_large(MAX_STATEMENT_BYTES))]
    StatementTooLarge,
    /// The statement is not the canonical encoding of its own content.
    #[error("{}", messages::sign_not_canonical(.0))]
    NotCanonical(String),
    /// The statement does not parse or has unknown fields.
    #[error("{}", messages::sign_invalid_statement(.0))]
    InvalidStatement(String),
    /// No pinned key has the statement's key id.
    #[error("{}", messages::key_not_pinned(.key_id, .namespace))]
    KeyNotPinned {
        /// Key id named by the statement.
        key_id: String,
        /// Namespace of the artifact id.
        namespace: String,
    },
    /// The signature does not verify.
    #[error("{}", SignPhrase::BadSignature.as_static())]
    BadSignature,
    /// The statement and the manifest disagree.
    #[error("{}", messages::sign_mismatch(.0))]
    Mismatch(String),
    /// An older version or an older `notBefore` than the lockfile holds.
    #[error("{}", messages::sign_rollback(.0))]
    Rollback(String),
    /// Fetching a signature blob failed.
    #[error(transparent)]
    Fetch(#[from] OciError),
    /// A public key does not parse.
    #[error("{}", messages::invalid_key(.0))]
    InvalidKey(String),
}

/// A minisign public key.
#[derive(Clone)]
pub struct PublicKey {
    inner: minisign_verify::PublicKey,
    id: [u8; 8],
    raw: Vec<u8>,
}

impl std::fmt::Debug for PublicKey {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "PublicKey({})", self.key_id())
    }
}

impl PublicKey {
    /// Parse the base64 line of a `minisign.pub` file.
    ///
    /// # Errors
    /// [`SignError::InvalidKey`] when the text is not a 42-byte Ed25519 minisign key.
    pub fn from_base64(b64: &str) -> Result<Self, SignError> {
        let b64 = b64.trim();
        let inner = minisign_verify::PublicKey::from_base64(b64)
            .map_err(|e| SignError::InvalidKey(e.to_string()))?;
        let raw = base64::engine::general_purpose::STANDARD
            .decode(b64)
            .map_err(|e| SignError::InvalidKey(e.to_string()))?;
        let id: [u8; 8] = raw[2..10]
            .try_into()
            .map_err(|_| SignError::InvalidKey(SignPhrase::ShortKey.as_static().into()))?;
        Ok(Self { inner, id, raw })
    }

    /// Parse the text of a `minisign.pub` file: an `untrusted comment:` line, then the base64 line.
    ///
    /// # Errors
    /// [`SignError::InvalidKey`] when the file has no key line or the line is not a minisign key.
    pub fn from_pub_file(text: &str) -> Result<Self, SignError> {
        let line = text
            .lines()
            .map(str::trim)
            .find(|l| !l.is_empty() && !l.starts_with("untrusted comment:"))
            .ok_or_else(|| SignError::InvalidKey(SignPhrase::NoKeyLine.as_static().into()))?;
        Self::from_base64(line)
    }

    /// The 8-byte key id as 16 uppercase hex digits, as `minisign -V` prints it and as the lockfile stores it.
    #[must_use]
    pub fn key_id(&self) -> String {
        // minisign prints the id as a little-endian integer: reverse the stored bytes.
        self.id.iter().rev().fold(String::new(), |mut acc, b| {
            let _ = write!(acc, "{b:02X}");
            acc
        })
    }

    /// SHA-256 of the raw key bytes as lowercase hex, shown by `plugins trust`.
    #[must_use]
    pub fn fingerprint(&self) -> String {
        Digest::of(&self.raw).hex().to_owned()
    }

    /// The base64 line of the key, as a `minisign.pub` file holds it.
    #[must_use]
    pub fn to_base64(&self) -> String {
        base64::engine::general_purpose::STANDARD.encode(&self.raw)
    }
}

/// The first-party release public key, compiled in from `keys/slopvac-release.pub`.
/// The secret half lives in release CI; see `docs/release/maintainer-setup.md`.
pub(crate) const RELEASE_KEY_FILE: &str = include_str!("../../../keys/slopvac-release.pub");

/// The only first-party namespace. Only a compiled key verifies an artifact in it.
pub const FIRST_PARTY_NAMESPACE: &str = "slopvac";

/// Namespaces that only the compiled first-party key may sign.
pub const FIRST_PARTY_NAMESPACES: &[&str] = &[FIRST_PARTY_NAMESPACE];

/// Every namespace nobody can pin a key for: the first-party and the built-in
/// one. Search flags them, `pin_key` refuses them and the trust store never
/// loads a pin for them. This is the one list; do not copy it.
pub const RESERVED_NAMESPACES: &[&str] = &[RESERVED_ID, FIRST_PARTY_NAMESPACE];

/// Whether `namespace` is in [`RESERVED_NAMESPACES`].
#[must_use]
pub fn is_reserved_namespace(namespace: &str) -> bool {
    RESERVED_NAMESPACES.contains(&namespace)
}

/// The compiled plugins key file, `keys/slopvac-plugins.pub`. The secret half
/// lives in a protected release environment. The release key, which is the
/// revocation root, can revoke this key by listing its ID.
const PLUGINS_KEY_FILE: &str = include_str!("../../../keys/slopvac-plugins.pub");

/// The compiled plugins key, separate from [`release_key`]. It verifies plugin
/// artifacts in the [`FIRST_PARTY_NAMESPACE`] and the first-party plugin index,
/// and nothing else: not `core`, not a third-party namespace, not the
/// revocation list and not release archives. [`KeyPolicy::compiled`] lists it
/// as the only first-party key.
///
/// # Errors
/// [`SignError::InvalidKey`] when the compiled file is not a minisign key.
pub fn plugins_key() -> Result<PublicKey, SignError> {
    PublicKey::from_pub_file(PLUGINS_KEY_FILE)
}

/// The id and namespace of the built-in plugin. It is reserved: the binary
/// compiles it in and never fetches it, so no lock entry or index entry may use
/// it, no key, compiled or pinned, verifies a fetched artifact in it, and a
/// reader refuses one that does.
pub const RESERVED_ID: &str = "core";

/// The compiled release key. It signs release archives and the revocation list,
/// and it is the revocation root. It signs no plugin.
///
/// # Errors
/// [`SignError::InvalidKey`] when the compiled file is not a minisign key. The
/// revocation root is then missing, so no revocation list verifies.
pub fn release_key() -> Result<PublicKey, SignError> {
    release_key_from(RELEASE_KEY_FILE)
}

pub(crate) fn release_key_from(text: &str) -> Result<PublicKey, SignError> {
    PublicKey::from_pub_file(text)
}

/// Which keys may sign which namespaces.
#[derive(Debug, Clone, Default)]
pub struct KeyPolicy {
    /// Keys compiled into the binary.
    pub first_party: Vec<PublicKey>,
    /// Namespaces that only first-party keys may sign.
    pub first_party_namespaces: Vec<String>,
    /// Keys the user pinned, or an earlier verified sync pinned in the lockfile, by namespace.
    /// A key pinned for one namespace never signs another.
    pub pinned: BTreeMap<String, Vec<PublicKey>>,
}

impl KeyPolicy {
    /// The shipped policy: the compiled plugins key for [`FIRST_PARTY_NAMESPACES`],
    /// and no pinned keys. The release key is not listed. Tests build the struct
    /// directly to inject other keys.
    ///
    /// # Errors
    /// [`SignError::InvalidKey`] when the compiled key does not parse. There is then
    /// no policy, so nothing verifies as first-party.
    pub fn compiled() -> Result<Self, SignError> {
        Self::compiled_from(PLUGINS_KEY_FILE)
    }

    fn compiled_from(key_file: &str) -> Result<Self, SignError> {
        Ok(Self {
            first_party: vec![PublicKey::from_pub_file(key_file)?],
            first_party_namespaces: FIRST_PARTY_NAMESPACES
                .iter()
                .map(|n| (*n).to_owned())
                .collect(),
            pinned: BTreeMap::new(),
        })
    }

    fn candidates(&self, namespace: &str) -> &[PublicKey] {
        if namespace == RESERVED_ID {
            // Fails closed: the built-in pack is never fetched.
            &[]
        } else if namespace == FIRST_PARTY_NAMESPACE
            || self.first_party_namespaces.iter().any(|n| n == namespace)
        {
            &self.first_party
        } else {
            self.pinned.get(namespace).map_or(&[], Vec::as_slice)
        }
    }
}

/// One non-signature layer as the statement lists it.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LayerEntry {
    /// Layer digest.
    pub digest: Digest,
    /// Layer size in bytes.
    pub size: u64,
    /// Layer media type.
    #[serde(rename = "mediaType")]
    pub media_type: String,
}

/// The signed statement.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Statement {
    /// Always 1.
    pub schema_version: u32,
    /// The pack id, as in its manifest (`^[a-z][a-z0-9-]*$`).
    pub id: String,
    /// The namespace: the owner segment of the repository the artifact is published under.
    /// The user pins publisher keys per namespace.
    pub namespace: String,
    /// Semantic version.
    pub version: String,
    /// The manifest's `artifactType`.
    #[serde(rename = "artifactType")]
    pub artifact_type: String,
    /// Digest of the config blob.
    pub config: Digest,
    /// Every layer except the two signature layers, in manifest order.
    pub layers: Vec<LayerEntry>,
    /// 16 uppercase hex digits naming the signing key.
    #[serde(rename = "keyId")]
    pub key_id: String,
    /// `YYYY-MM-DDTHH:MM:SSZ`. Later releases carry later times.
    #[serde(rename = "notBefore")]
    pub not_before: String,
}

fn canonical(v: &Value, out: &mut Vec<u8>) {
    match v {
        Value::Object(m) => {
            let sorted: BTreeMap<&String, &Value> = m.iter().collect();
            out.push(b'{');
            for (i, (k, val)) in sorted.into_iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                out.extend_from_slice(Value::String(k.clone()).to_string().as_bytes());
                out.push(b':');
                canonical(val, out);
            }
            out.push(b'}');
        }
        Value::Array(a) => {
            out.push(b'[');
            for (i, val) in a.iter().enumerate() {
                if i > 0 {
                    out.push(b',');
                }
                canonical(val, out);
            }
            out.push(b']');
        }
        other => out.extend_from_slice(other.to_string().as_bytes()),
    }
}

/// Canonical JSON: sorted keys, no insignificant whitespace.
#[must_use]
pub fn canonical_json(v: &Value) -> Vec<u8> {
    let mut out = Vec::new();
    canonical(v, &mut out);
    out
}

impl Statement {
    /// The canonical bytes that get signed.
    ///
    /// # Panics
    /// Never: the type always serialises.
    #[must_use]
    pub fn canonical_bytes(&self) -> Vec<u8> {
        canonical_json(&serde_json::to_value(self).expect("statement serialises"))
    }

    /// Build the statement for a manifest that has no signature layers yet.
    #[must_use]
    pub fn for_manifest(
        namespace: &str,
        id: &str,
        version: &str,
        key_id: &str,
        not_before: &str,
        manifest: &Manifest,
    ) -> Self {
        Self {
            schema_version: 1,
            id: id.to_owned(),
            namespace: namespace.to_owned(),
            version: version.to_owned(),
            artifact_type: manifest.artifact_type.clone().unwrap_or_default(),
            config: manifest.config.digest.clone(),
            layers: manifest.layers.iter().map(entry_of).collect(),
            key_id: key_id.to_owned(),
            not_before: not_before.to_owned(),
        }
    }
}

fn entry_of(d: &Descriptor) -> LayerEntry {
    LayerEntry {
        digest: d.digest.clone(),
        size: d.size,
        media_type: d.media_type.clone(),
    }
}

/// What the caller expects, from the lockfile request.
#[derive(Debug, Clone)]
pub struct Expectation<'a> {
    /// Pack id.
    pub id: &'a str,
    /// Namespace, from the repository the artifact is fetched from.
    pub namespace: &'a str,
    /// Requested version.
    pub version: &'a str,
    /// Expected `artifactType`.
    pub artifact_type: &'a str,
    /// Version and `notBefore` the lockfile already holds, if any.
    pub floor: Option<(&'a str, &'a str)>,
    /// Allow a version or `notBefore` below the floor (an explicit downgrade).
    pub allow_downgrade: bool,
}

/// A statement that passed every check.
#[derive(Debug, Clone)]
pub struct Verified {
    statement: Statement,
    key: PublicKey,
}

impl Verified {
    /// The statement that passed every check.
    #[must_use]
    pub fn statement(&self) -> &Statement {
        &self.statement
    }

    /// The key that signed it.
    #[must_use]
    pub fn key(&self) -> &PublicKey {
        &self.key
    }
}

/// The two signature layers of a manifest.
///
/// # Errors
/// [`SignError::MissingSignature`] or [`SignError::DuplicateSignature`].
pub fn signature_layers(manifest: &Manifest) -> Result<(&Descriptor, &Descriptor), SignError> {
    let find = |media: &str| -> Result<&Descriptor, SignError> {
        let mut it = manifest.layers.iter().filter(|l| l.media_type == media);
        let first = it.next().ok_or(SignError::MissingSignature)?;
        if it.next().is_some() {
            return Err(SignError::DuplicateSignature);
        }
        Ok(first)
    };
    Ok((find(MEDIA_STATEMENT)?, find(MEDIA_MINISIG)?))
}

fn is_name(s: &str) -> bool {
    let mut c = s.chars();
    c.next().is_some_and(|f| f.is_ascii_lowercase())
        && c.all(|x| x.is_ascii_lowercase() || x.is_ascii_digit() || x == '-')
}

fn mismatch(what: &str) -> SignError {
    SignError::Mismatch(what.to_owned())
}

/// Parse a size-capped, strict and canonical JSON document into `T`.
pub(crate) fn parse_canonical<T: serde::de::DeserializeOwned>(
    bytes: &[u8],
    max: usize,
) -> Result<T, SignError> {
    if bytes.len() > max {
        return Err(SignError::StatementTooLarge);
    }
    let value = strict::parse(bytes).map_err(SignError::InvalidStatement)?;
    if canonical_json(&value) != bytes {
        return Err(SignError::NotCanonical(
            SignPhrase::Reencoding.as_static().into(),
        ));
    }
    serde_json::from_value(value).map_err(|e| SignError::InvalidStatement(e.to_string()))
}

/// Verify a prehashed minisign signature by `key` over exactly `bytes`.
pub(crate) fn verify_bytes(key: &PublicKey, bytes: &[u8], minisig: &str) -> Result<(), SignError> {
    let sig = minisign_verify::Signature::decode(minisig).map_err(|_| SignError::BadSignature)?;
    key.inner
        .verify(bytes, &sig, false)
        .map_err(|_| SignError::BadSignature)
}

/// Whether `text` is 16 uppercase hex digits, the form of a key id.
pub(crate) fn is_key_id(text: &str) -> bool {
    text.len() == 16 && text.bytes().all(|b| matches!(b, b'0'..=b'9' | b'A'..=b'F'))
}

/// Seconds since 1970-01-01T00:00:00Z of a `YYYY-MM-DDTHH:MM:SSZ` time, or
/// `None` for text that is not a real calendar time.
pub(crate) fn utc_seconds(text: &str) -> Option<i64> {
    let (year, month, day, hour, minute, second) = parse_time(text)?;
    // Days from the civil date (H. Hinnant, "chrono-Compatible Low-Level Date Algorithms").
    let y = i64::from(year) - i64::from(month <= 2);
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let m = i64::from(month);
    let doy = (153 * (if m > 2 { m - 3 } else { m + 9 }) + 2) / 5 + i64::from(day) - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    let days = era * 146_097 + doe - 719_468;
    Some(days * 86_400 + i64::from(hour) * 3_600 + i64::from(minute) * 60 + i64::from(second))
}

/// A UTC time as `(year, month, day, hour, minute, second)`, which orders chronologically.
type Time = (u32, u32, u32, u32, u32, u32);

/// Parse `YYYY-MM-DDTHH:MM:SSZ` and reject times that do not exist on the calendar.
fn parse_time(text: &str) -> Option<Time> {
    let bytes = text.as_bytes();
    if bytes.len() != 20
        || !bytes.iter().enumerate().all(|(i, c)| match i {
            4 | 7 => *c == b'-',
            10 => *c == b'T',
            13 | 16 => *c == b':',
            19 => *c == b'Z',
            _ => c.is_ascii_digit(),
        })
    {
        return None;
    }
    let field = |r: std::ops::Range<usize>| text[r].parse::<u32>().ok();
    let year = field(0..4)?;
    let (month, day) = (field(5..7)?, field(8..10)?);
    let (hour, minute, second) = (field(11..13)?, field(14..16)?, field(17..19)?);
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let days = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => return None,
    };
    ((1..=days).contains(&day) && hour < 24 && minute < 60 && second < 60)
        .then_some((year, month, day, hour, minute, second))
}

/// Verify a statement and its signature against a manifest.
///
/// Checks run in the order of the threat model: the signature over the exact
/// statement bytes, the key against the policy, the layer set, the identity
/// fields and the config digest, then rollback.
///
/// # Errors
/// The first failing check, as a [`SignError`].
pub fn verify(
    manifest: &Manifest,
    statement_bytes: &[u8],
    minisig: &str,
    policy: &KeyPolicy,
    expect: &Expectation<'_>,
) -> Result<Verified, SignError> {
    let statement: Statement = parse_canonical(statement_bytes, MAX_STATEMENT_BYTES)?;
    let namespace = statement.namespace.clone();
    if !is_name(&namespace) || !is_name(&statement.id) {
        return Err(SignError::InvalidStatement(
            SignPhrase::NotAName.as_static().into(),
        ));
    }

    // The key id only selects among keys the policy already trusts.
    let key = policy
        .candidates(&namespace)
        .iter()
        .find(|k| k.key_id() == statement.key_id)
        .ok_or_else(|| SignError::KeyNotPinned {
            key_id: statement.key_id.clone(),
            namespace: namespace.clone(),
        })?;
    verify_bytes(key, statement_bytes, minisig)?;

    check_binding(manifest, &statement, expect)?;
    check_rollback(&statement, expect)?;
    Ok(Verified {
        statement,
        key: key.clone(),
    })
}

fn check_binding(
    manifest: &Manifest,
    st: &Statement,
    expect: &Expectation<'_>,
) -> Result<(), SignError> {
    signature_layers(manifest)?;
    if st.schema_version != 1 {
        return Err(mismatch(SignPhrase::Schema.as_static()));
    }
    let signed: Vec<LayerEntry> = manifest
        .layers
        .iter()
        .filter(|l| l.media_type != MEDIA_STATEMENT && l.media_type != MEDIA_MINISIG)
        .map(entry_of)
        .collect();
    if signed != st.layers {
        return Err(mismatch(SignPhrase::Layers.as_static()));
    }
    if manifest.config.digest != st.config {
        return Err(mismatch(SignPhrase::Config.as_static()));
    }
    if manifest.artifact_type.as_deref() != Some(st.artifact_type.as_str())
        || st.artifact_type != expect.artifact_type
    {
        return Err(mismatch(SignPhrase::ArtifactType.as_static()));
    }
    if st.id != expect.id || st.namespace != expect.namespace || st.version != expect.version {
        return Err(mismatch(SignPhrase::Identity.as_static()));
    }
    let ann = |k: &str| manifest.annotations.get(k).map(String::as_str);
    if ann(ANNOTATION_ID) != Some(st.id.as_str())
        || ann(ANNOTATION_VERSION) != Some(st.version.as_str())
    {
        return Err(mismatch(SignPhrase::Annotations.as_static()));
    }
    if parse_time(&st.not_before).is_none() {
        return Err(SignError::InvalidStatement(
            SignPhrase::NotBeforeForm.as_static().into(),
        ));
    }
    Ok(())
}

fn check_rollback(st: &Statement, expect: &Expectation<'_>) -> Result<(), SignError> {
    let new = semver::Version::parse(&st.version)
        .map_err(|e| SignError::InvalidStatement(messages::sign_version(&e.to_string())))?;
    if !new.build.is_empty() {
        return Err(SignError::InvalidStatement(
            SignPhrase::BuildMetadata.as_static().into(),
        ));
    }
    let Some((floor_version, floor_time)) = expect.floor else {
        return Ok(());
    };
    if expect.allow_downgrade {
        return Ok(());
    }
    let floor = semver::Version::parse(floor_version).map_err(|e| {
        SignError::InvalidStatement(messages::sign_lockfile_version(&e.to_string()))
    })?;
    if new < floor {
        return Err(SignError::Rollback(messages::older_version(
            &new.to_string(),
            &floor.to_string(),
        )));
    }
    let floor_at = parse_time(floor_time)
        .ok_or_else(|| SignError::InvalidStatement(SignPhrase::LockfileTime.as_static().into()))?;
    let new_at = parse_time(&st.not_before)
        .ok_or_else(|| SignError::InvalidStatement(SignPhrase::Time.as_static().into()))?;
    if new_at < floor_at {
        return Err(SignError::Rollback(messages::older_not_before(
            &st.not_before,
            floor_time,
        )));
    }
    Ok(())
}

/// Fetch the two signature blobs through `client` and verify.
///
/// # Errors
/// [`SignError::Fetch`] for registry failures, otherwise as [`verify`].
pub fn fetch_and_verify(
    client: &Client,
    repository: &Reference,
    manifest: &Manifest,
    policy: &KeyPolicy,
    expect: &Expectation<'_>,
) -> Result<Verified, SignError> {
    let (statement, minisig) = signature_layers(manifest)?;
    if statement.size > MAX_STATEMENT_BYTES as u64 {
        return Err(SignError::StatementTooLarge);
    }
    let statement_bytes =
        client.fetch_blob_bytes(repository, statement, MAX_STATEMENT_BYTES as u64)?;
    let sig_bytes = client.fetch_blob_bytes(repository, minisig, MAX_MINISIG_BYTES as u64)?;
    let sig_text = String::from_utf8(sig_bytes).map_err(|_| SignError::BadSignature)?;
    verify(manifest, &statement_bytes, &sig_text, policy, expect)
}

/// The `type` of a rotation statement.
pub const ROTATION_TYPE: &str = "rotation";
/// Largest rotation statement the verifier reads.
pub const MAX_ROTATION_BYTES: usize = 4 * 1024;

/// A publisher's announcement that `newKeyId` replaces `oldKeyId` for one
/// namespace (threat model section 5.3). Canonical JSON, signed by both keys.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RotationStatement {
    /// Always 1.
    pub schema_version: u32,
    /// Always [`ROTATION_TYPE`], so no other signed document can pass as a rotation.
    #[serde(rename = "type")]
    pub kind: String,
    /// The namespace whose key changes.
    pub namespace: String,
    /// Key id of the pinned key.
    #[serde(rename = "oldKeyId")]
    pub old_key_id: String,
    /// Key id of the key that replaces it.
    #[serde(rename = "newKeyId")]
    pub new_key_id: String,
    /// The whole new public key, as the base64 line of its `minisign.pub`.
    /// A key id is unsigned metadata that anyone can copy, so the statement
    /// binds the key bytes themselves.
    #[serde(rename = "newKey")]
    pub new_key: String,
    /// `YYYY-MM-DDTHH:MM:SSZ`. It must be later than the pin's own `notBefore`.
    #[serde(rename = "notBefore")]
    pub not_before: String,
}

/// A rotation statement, its two signatures and the new public key.
#[derive(Debug, Clone, Copy)]
pub struct RotationProof<'a> {
    /// The canonical statement bytes.
    pub statement: &'a [u8],
    /// `.minisig` text by the old (pinned) key.
    pub old_signature: &'a str,
    /// `.minisig` text by the new key.
    pub new_signature: &'a str,
    /// The new key. Its id must be the statement's `newKeyId`.
    pub new_key: &'a PublicKey,
}

/// Verify a rotation for `namespace` against the key pinned for it.
///
/// The statement must be strict canonical JSON naming `namespace`, the pinned
/// key as `oldKeyId` and `proof.new_key` as `newKeyId` and, byte for byte, as
/// `newKey`. Both keys must sign it, and its `notBefore` must be later than
/// `floor`, the pin's own `notBefore` when the pin came from an earlier
/// rotation.
///
/// # Errors
/// [`SignError::KeyNotPinned`] when `oldKeyId` is not the pinned key,
/// [`SignError::Mismatch`] for another namespace or new key,
/// [`SignError::BadSignature`] unless both signatures verify,
/// [`SignError::Rollback`] when `notBefore` is not later than `floor`, and the
/// parse errors of [`verify`].
pub fn verify_rotation(
    proof: &RotationProof<'_>,
    namespace: &str,
    pinned: &PublicKey,
    floor: Option<&str>,
) -> Result<RotationStatement, SignError> {
    let st: RotationStatement = parse_canonical(proof.statement, MAX_ROTATION_BYTES)?;
    if st.schema_version != 1 || st.kind != ROTATION_TYPE {
        return Err(SignError::InvalidStatement(
            SignPhrase::NotRotation.as_static().into(),
        ));
    }
    if !is_name(&st.namespace) || !is_key_id(&st.old_key_id) || !is_key_id(&st.new_key_id) {
        return Err(SignError::InvalidStatement(
            SignPhrase::RotationIds.as_static().into(),
        ));
    }
    if st.namespace != namespace {
        return Err(mismatch(SignPhrase::RotationNamespace.as_static()));
    }
    if st.old_key_id != pinned.key_id() {
        return Err(SignError::KeyNotPinned {
            key_id: st.old_key_id,
            namespace: namespace.to_owned(),
        });
    }
    if st.new_key_id != proof.new_key.key_id() || st.new_key_id == st.old_key_id {
        return Err(mismatch(SignPhrase::RotationNewKey.as_static()));
    }
    let bound = PublicKey::from_base64(&st.new_key)
        .map_err(|_| SignError::InvalidStatement(SignPhrase::RotationKeyForm.as_static().into()))?;
    if bound.raw != proof.new_key.raw || bound.key_id() != st.new_key_id {
        return Err(mismatch(SignPhrase::RotationBound.as_static()));
    }
    verify_bytes(pinned, proof.statement, proof.old_signature)?;
    verify_bytes(proof.new_key, proof.statement, proof.new_signature)?;
    let at = utc_seconds(&st.not_before)
        .ok_or_else(|| SignError::InvalidStatement(SignPhrase::Time.as_static().into()))?;
    if let Some(floor) = floor {
        let floor_at = utc_seconds(floor)
            .ok_or_else(|| SignError::InvalidStatement(SignPhrase::PinTime.as_static().into()))?;
        if at <= floor_at {
            return Err(SignError::Rollback(messages::rotation_not_later(
                &st.not_before,
                floor,
            )));
        }
    }
    Ok(st)
}

#[cfg(test)]
mod tests {
    use super::*;

    const MALFORMED: [&str; 3] = [
        "",
        "untrusted comment: x\n",
        "untrusted comment: x\nnot-a-key\n",
    ];

    #[test]
    fn a_malformed_compiled_key_is_a_typed_error_not_a_panic() {
        for text in MALFORMED {
            assert!(
                matches!(release_key_from(text), Err(SignError::InvalidKey(_))),
                "{text:?}"
            );
        }
    }

    #[test]
    fn a_malformed_compiled_key_builds_no_policy() {
        for text in MALFORMED {
            assert!(
                matches!(
                    KeyPolicy::compiled_from(text),
                    Err(SignError::InvalidKey(_))
                ),
                "{text:?}"
            );
        }
    }
}
