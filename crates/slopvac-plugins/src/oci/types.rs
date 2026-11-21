//! Digests, descriptors and manifests (OCI image spec v1.1 subset).

use std::collections::BTreeMap;
use std::fmt;

use serde::{Deserialize, Deserializer, Serialize};

use super::OciError;
use crate::messages::transport::TransportText;

/// OCI image manifest media type.
pub const MEDIA_MANIFEST: &str = "application/vnd.oci.image.manifest.v1+json";
/// OCI image index media type.
pub const MEDIA_INDEX: &str = "application/vnd.oci.image.index.v1+json";
/// Media type of the empty config blob.
pub const MEDIA_EMPTY: &str = "application/vnd.oci.empty.v1+json";

/// Largest manifest or index body the client reads (threat model N2).
pub const MAX_MANIFEST_BYTES: usize = 4 << 20;
/// Largest blob the client reads (threat model N1).
pub const MAX_BLOB_BYTES: u64 = 256 << 20;

/// A `sha256:<64 lowercase hex>` content digest.
#[derive(Clone, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize)]
pub struct Digest(String);

impl Digest {
    /// Parse and validate a digest string.
    ///
    /// # Errors
    /// [`OciError::Invalid`] unless the string is `sha256:` plus 64 lowercase hex digits.
    pub fn parse(s: &str) -> Result<Self, OciError> {
        Self::parse_raw(s).map_err(OciError::Invalid)
    }

    /// Like [`Digest::parse`], with the reason as raw text for a caller that
    /// builds a larger message and escapes it once.
    pub(crate) fn parse_raw(s: &str) -> Result<Self, String> {
        let hex = s.strip_prefix("sha256:").ok_or_else(|| {
            TransportText::OciDigestAlgorithm {
                digest: s.to_owned(),
            }
            .to_string()
        })?;
        if hex.len() != 64 || !hex.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
            return Err(TransportText::OciDigestHex {
                digest: s.to_owned(),
            }
            .to_string());
        }
        Ok(Self(s.to_owned()))
    }

    /// Digest of `bytes`.
    #[must_use]
    pub fn of(bytes: &[u8]) -> Self {
        use sha2::{Digest as _, Sha256};
        Self::from_hasher(Sha256::new_with_prefix(bytes))
    }

    pub(crate) fn from_hasher(h: sha2::Sha256) -> Self {
        use sha2::Digest as _;
        let out = h.finalize();
        let mut s = String::with_capacity(71);
        s.push_str("sha256:");
        for b in out {
            s.push(char::from(b"0123456789abcdef"[usize::from(b >> 4)]));
            s.push(char::from(b"0123456789abcdef"[usize::from(b & 15)]));
        }
        Self(s)
    }

    /// The full `sha256:...` string.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Only the hex part.
    #[must_use]
    pub fn hex(&self) -> &str {
        &self.0[7..]
    }
}

impl fmt::Display for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl fmt::Debug for Digest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Digest({})", self.0)
    }
}

impl<'de> Deserialize<'de> for Digest {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        Self::parse_raw(&s).map_err(serde::de::Error::custom)
    }
}

/// A content descriptor.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Descriptor {
    /// Media type of the content.
    pub media_type: String,
    /// Content digest.
    pub digest: Digest,
    /// Content size in bytes.
    pub size: u64,
    /// Artifact type, when the descriptor points at a manifest that has one.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub artifact_type: Option<String>,
    /// Free-form annotations.
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub annotations: BTreeMap<String, String>,
}

impl Descriptor {
    /// Descriptor for `bytes` with the given media type.
    #[must_use]
    pub fn for_bytes(media_type: &str, bytes: &[u8]) -> Self {
        Self {
            media_type: media_type.to_owned(),
            digest: Digest::of(bytes),
            size: bytes.len() as u64,
            artifact_type: None,
            annotations: BTreeMap::new(),
        }
    }
}

/// An image manifest, used here as an artifact manifest.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Manifest {
    /// Always 2.
    pub schema_version: u32,
    /// `application/vnd.oci.image.manifest.v1+json`.
    #[serde(default)]
    pub media_type: Option<String>,
    /// The artifact type.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub artifact_type: Option<String>,
    /// The config descriptor.
    pub config: Descriptor,
    /// The layers, in order.
    pub layers: Vec<Descriptor>,
    /// The manifest this one refers to, if any.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subject: Option<Descriptor>,
    /// Free-form annotations.
    #[serde(default, skip_serializing_if = "BTreeMap::is_empty")]
    pub annotations: BTreeMap<String, String>,
}

/// An image index, also the shape of a referrers response.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Index {
    /// Always 2.
    pub schema_version: u32,
    /// `application/vnd.oci.image.index.v1+json`.
    #[serde(default)]
    pub media_type: Option<String>,
    /// The listed manifests.
    pub manifests: Vec<Descriptor>,
}

#[cfg(test)]
mod tests {
    use super::*;

    const EMPTY_SHA: &str =
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    #[test]
    fn digest_of_empty_input_is_the_known_value() {
        assert_eq!(Digest::of(b"").as_str(), EMPTY_SHA);
        assert_eq!(Digest::of(b"").hex().len(), 64);
    }

    #[test]
    fn digest_parse_rejects_bad_forms() {
        for bad in [
            "sha256:ABC",
            "sha512:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "sha256:E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855",
            "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85",
            "",
        ] {
            assert!(Digest::parse(bad).is_err(), "{bad}");
        }
        assert!(Digest::parse(EMPTY_SHA).is_ok());
    }

    #[test]
    fn manifest_round_trips_and_ignores_unknown_fields() {
        let json = format!(
            r#"{{"schemaVersion":2,"mediaType":"{MEDIA_MANIFEST}","artifactType":"application/vnd.slopvac.pack.v1",
            "config":{{"mediaType":"{MEDIA_EMPTY}","digest":"{EMPTY_SHA}","size":0,"future":1}},
            "layers":[{{"mediaType":"x","digest":"{EMPTY_SHA}","size":0,"annotations":{{"a":"b"}}}}],"extra":true}}"#
        );
        let m: Manifest = serde_json::from_str(&json).unwrap();
        assert_eq!(m.layers[0].annotations["a"], "b");
        assert_eq!(
            m.artifact_type.as_deref(),
            Some("application/vnd.slopvac.pack.v1")
        );
    }
}
