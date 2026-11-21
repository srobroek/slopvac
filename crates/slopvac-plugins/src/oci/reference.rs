//! Image references: `registry/repository[:tag][@digest]`.

use std::fmt;

use super::OciError;
use super::types::Digest;
use crate::messages::transport::{TransportPhrase, TransportText};

/// A tag or a digest.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Target {
    /// A mutable tag.
    Tag(String),
    /// A content digest.
    Digest(Digest),
}

impl fmt::Display for Target {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Tag(t) => f.write_str(t),
            Self::Digest(d) => f.write_str(d.as_str()),
        }
    }
}

/// A parsed reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Reference {
    /// Registry host with optional port, for example `ghcr.io`.
    pub registry: String,
    /// Repository path, for example `slopvac/slopvac-plugins/core`.
    pub repository: String,
    /// Tag or digest. A digest wins when both are present.
    pub target: Target,
}

fn valid_registry(s: &str) -> bool {
    let (host, port) = match s.rsplit_once(':') {
        Some((h, p)) => (h, Some(p)),
        None => (s, None),
    };
    let host_ok = !host.is_empty()
        && host.len() <= 253
        && host
            .split('.')
            .all(|l| !l.is_empty() && l.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'-'));
    let port_ok =
        port.is_none_or(|p| !p.is_empty() && p.len() <= 5 && p.bytes().all(|b| b.is_ascii_digit()));
    host_ok && port_ok
}

fn valid_repository(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 255
        && s.split('/').all(|comp| {
            let mut parts = comp.split(['.', '_', '-']);
            // Components are lowercase alphanumeric runs joined by single separators.
            comp.bytes().all(|b| {
                b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'.' | b'_' | b'-')
            }) && !comp.is_empty()
                && parts.all(|p| !p.is_empty())
        })
}

pub(crate) fn valid_tag(s: &str) -> bool {
    let mut bytes = s.bytes();
    s.len() <= 128
        && bytes
            .next()
            .is_some_and(|b| b.is_ascii_alphanumeric() || b == b'_')
        && bytes.all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'.' | b'-'))
}

impl Reference {
    /// Parse `registry/repository[:tag][@sha256:...]`. A bare reference with no
    /// tag or digest is refused: callers must pin one.
    ///
    /// # Errors
    /// [`OciError::Invalid`] for any malformed part.
    pub fn parse(s: &str) -> Result<Self, OciError> {
        let bad = |why: &str| {
            OciError::Invalid(
                TransportText::OciReference {
                    reference: s.to_owned(),
                    reason: why.to_owned(),
                }
                .to_string(),
            )
        };
        let (rest, digest) = match s.split_once('@') {
            Some((r, d)) => (r, Some(Digest::parse(d)?)),
            None => (s, None),
        };
        let (registry, path) = rest
            .split_once('/')
            .ok_or_else(|| bad(TransportPhrase::OciNoRepository.as_static()))?;
        if !valid_registry(registry) {
            return Err(bad(TransportPhrase::OciBadHost.as_static()));
        }
        let (repository, tag) = match path.rsplit_once(':') {
            Some((r, t)) if !t.contains('/') => (r, Some(t)),
            _ => (path, None),
        };
        if !valid_repository(repository) {
            return Err(bad(TransportPhrase::OciBadRepository.as_static()));
        }
        let target = match (digest, tag) {
            (Some(d), _) => Target::Digest(d),
            (None, Some(t)) if valid_tag(t) => Target::Tag(t.to_owned()),
            (None, Some(_)) => return Err(bad(TransportPhrase::OciBadTag.as_static())),
            (None, None) => return Err(bad(TransportPhrase::OciTargetRequired.as_static())),
        };
        Ok(Self {
            registry: registry.to_owned(),
            repository: repository.to_owned(),
            target,
        })
    }

    /// The same repository with another target.
    #[must_use]
    pub fn with_target(&self, target: Target) -> Self {
        Self {
            target,
            ..self.clone()
        }
    }

    /// Host without the port.
    #[must_use]
    pub fn host(&self) -> &str {
        self.registry
            .rsplit_once(':')
            .map_or(&self.registry, |(h, _)| h)
    }
}

impl fmt::Display for Reference {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.target {
            Target::Tag(t) => write!(f, "{}/{}:{t}", self.registry, self.repository),
            Target::Digest(d) => write!(f, "{}/{}@{d}", self.registry, self.repository),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const D: &str = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    #[test]
    fn parses_tag_digest_and_port_forms() {
        let r = Reference::parse("ghcr.io/slopvac/plugins/core:1.2.3").unwrap();
        assert_eq!(
            (r.registry.as_str(), r.repository.as_str()),
            ("ghcr.io", "slopvac/plugins/core")
        );
        assert_eq!(r.target, Target::Tag("1.2.3".into()));
        let r = Reference::parse(
            "127.0.0.1:5000/a/b@"
                .to_owned()
                .as_str()
                .replace('@', &format!("@{D}"))
                .as_str(),
        )
        .unwrap();
        assert_eq!(r.registry, "127.0.0.1:5000");
        assert_eq!(r.host(), "127.0.0.1");
        assert!(matches!(r.target, Target::Digest(_)));
    }

    #[test]
    fn digest_wins_over_tag() {
        let r = Reference::parse(&format!("ghcr.io/a/b:1@{D}")).unwrap();
        assert!(matches!(r.target, Target::Digest(_)));
    }

    #[test]
    fn rejects_malformed_references() {
        for bad in [
            "ghcr.io/a/b",
            "ghcr.io",
            "ghcr.io/A/b:1",
            "ghcr.io/a//b:1",
            "ghcr.io/a/b:-x",
            "ghcr.io/a/b:",
            "gh cr.io/a/b:1",
            "ghcr.io/../b:1",
            "user@ghcr.io/a/b:1",
            "ghcr.io/a/b@sha256:xyz",
            "ghcr.io:port/a/b:1",
            "/a/b:1",
        ] {
            assert!(Reference::parse(bad).is_err(), "{bad}");
        }
    }
}
