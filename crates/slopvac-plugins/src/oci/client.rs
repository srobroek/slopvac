//! The client: auth, manifests, blobs, referrers, tags and push.

use std::collections::HashMap;
use std::fmt::Write as _;
use std::io::{Read, Write};
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{Duration, Instant};

use serde::Deserialize;
use sha2::{Digest as _, Sha256};
use ureq::Body;
use ureq::http::Response;

use super::auth::{Challenge, Credential, CredentialSource, DefaultCredentials};
use super::http::{
    Req, TestNet, Timeouts, Transport, bare_host, host_of, is_loopback_host, origin_of, read_error,
    resolve, url_allowed, wire_bytes_used,
};
use super::reference::{Reference, Target};
use super::types::{
    Descriptor, Digest, Index, MAX_BLOB_BYTES, MAX_MANIFEST_BYTES, MEDIA_INDEX, MEDIA_MANIFEST,
    Manifest,
};
use super::{OciError, redact_url};

const MANIFEST_ACCEPT: &str =
    "application/vnd.oci.image.manifest.v1+json, application/vnd.oci.image.index.v1+json";
const MAX_TOKEN_BYTES: usize = 64 * 1024;
const MAX_TAG_PAGES: usize = 10;
const MAX_TAGS: usize = 10_000;

/// Token services that may be named by a registry on another origin, as
/// `(registry origin, token service origin)`. Every other registry may only
/// name a realm on its own origin (scheme, host and port). GHCR's token
/// endpoint, `https://ghcr.io/token`, is on its own origin and needs no entry.
const TOKEN_SERVICES: &[(&str, &str)] = &[
    ("https://registry-1.docker.io", "https://auth.docker.io"),
    ("https://docker.io", "https://auth.docker.io"),
];

struct CachedToken {
    value: String,
    expires: Instant,
    /// Why a credential helper was not used when this token was fetched
    /// anonymously. A later denial with the token reports it.
    refused: Option<OciError>,
}

#[derive(Deserialize)]
struct Tok {
    token: Option<String>,
    access_token: Option<String>,
    expires_in: Option<u64>,
}

/// A fetched manifest or index with its computed digest.
#[derive(Debug, Clone)]
pub struct Fetched {
    /// Digest of `body`.
    pub digest: Digest,
    /// `application/vnd.oci.image.manifest.v1+json` or the index type.
    pub media_type: String,
    /// Raw bytes. Sign and hash these, never a re-encoding.
    pub body: Vec<u8>,
}

impl Fetched {
    /// Parse as an image manifest.
    ///
    /// # Errors
    /// [`OciError::UnsupportedMediaType`] for an index, [`OciError::Invalid`] for bad JSON.
    pub fn manifest(&self) -> Result<Manifest, OciError> {
        if self.media_type != MEDIA_MANIFEST {
            return Err(OciError::UnsupportedMediaType(self.media_type.clone()));
        }
        serde_json::from_slice(&self.body).map_err(|e| {
            OciError::Invalid(
                crate::messages::transport::TransportText::OciManifest {
                    detail: e.to_string(),
                }
                .to_string(),
            )
        })
    }

    /// Parse as an image index.
    ///
    /// # Errors
    /// [`OciError::UnsupportedMediaType`] for a manifest, [`OciError::Invalid`] for bad JSON.
    pub fn index(&self) -> Result<Index, OciError> {
        if self.media_type != MEDIA_INDEX {
            return Err(OciError::UnsupportedMediaType(self.media_type.clone()));
        }
        serde_json::from_slice(&self.body).map_err(|e| {
            OciError::Invalid(
                crate::messages::transport::TransportText::OciIndex {
                    detail: e.to_string(),
                }
                .to_string(),
            )
        })
    }
}

/// The response's `Content-Type` without parameters, lower-cased.
fn content_type<T>(resp: &ureq::http::Response<T>) -> Option<String> {
    resp.headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .map(|v| v.split(';').next().unwrap_or(v).trim().to_ascii_lowercase())
}

/// The manifest or index type of a body: the header's when it is one of the
/// two, else the body's own `mediaType` behind a generic JSON header.
fn manifest_media_type(header_type: Option<&str>, body: &[u8]) -> Result<String, OciError> {
    match header_type {
        Some(t @ (MEDIA_MANIFEST | MEDIA_INDEX)) => Ok(t.to_owned()),
        other => {
            // Some registries send a generic type; the body then names its own.
            let declared = serde_json::from_slice::<serde_json::Value>(body)
                .ok()
                .and_then(|v| {
                    v.get("mediaType")
                        .and_then(|m| m.as_str().map(str::to_owned))
                });
            match declared.as_deref() {
                Some(t @ (MEDIA_MANIFEST | MEDIA_INDEX))
                    if other
                        .is_none_or(|o| o.starts_with("application/json") || o == "text/plain") =>
                {
                    Ok(t.to_owned())
                }
                _ => Err(OciError::UnsupportedMediaType(
                    other
                        .unwrap_or(
                            crate::messages::transport::TransportPhrase::OciMediaNone.as_static(),
                        )
                        .to_owned(),
                )),
            }
        }
    }
}

/// OCI registry client. One per run; it caches bearer tokens by registry
/// origin and scope, so a token never goes to another registry.
pub struct Client {
    transport: Transport,
    creds: Box<dyn CredentialSource>,
    tokens: Mutex<HashMap<String, CachedToken>>,
    allow_loopback_http: bool,
}

impl Client {
    /// Client with credentials from the environment and the Docker config.
    /// `project_root` is the enclosing project, where no credential helper may
    /// run from.
    #[must_use]
    pub fn new(project_root: impl Into<std::path::PathBuf>) -> Self {
        Self::with_credentials(Box::new(DefaultCredentials::from_env(project_root)))
    }

    /// Client with a given credential source.
    #[must_use]
    pub fn with_credentials(creds: Box<dyn CredentialSource>) -> Self {
        Self::build(creds, false, Timeouts::default(), &TestNet::default())
    }

    /// Test seam: like [`Client::with_credentials`] but speaks plain HTTP to
    /// loopback registries, which integration tests need for their fake server.
    ///
    /// Production code never calls this: `new` and `with_credentials` refuse
    /// every `http://` URL, redirects and token realms included, and no
    /// configuration or reference can switch it on.
    #[doc(hidden)]
    #[must_use]
    pub fn with_loopback_http_for_tests(creds: Box<dyn CredentialSource>) -> Self {
        Self::build(creds, true, Timeouts::default(), &TestNet::default())
    }

    /// Test seam: like [`Client::with_loopback_http_for_tests`] with a short limit
    /// on sending a request body, so a stalled upload fails within seconds.
    #[doc(hidden)]
    #[must_use]
    pub fn with_send_timeout_for_tests(
        creds: Box<dyn CredentialSource>,
        send_body: std::time::Duration,
    ) -> Self {
        let timeouts = Timeouts {
            send_body,
            ..Timeouts::default()
        };
        Self::build(creds, true, timeouts, &TestNet::default())
    }

    /// Test seam: an HTTPS-only client that trusts the DER certificate `root`
    /// instead of the platform roots and, when `proxy` is set, reaches
    /// registries through that `CONNECT` proxy (for example
    /// `http://127.0.0.1:3128`).
    ///
    /// Production code never calls this.
    #[doc(hidden)]
    #[must_use]
    pub fn with_tls_root_for_tests(
        creds: Box<dyn CredentialSource>,
        root: &[u8],
        proxy: Option<&str>,
    ) -> Self {
        let net = TestNet {
            root: Some(root.to_vec()),
            proxy: proxy.map(str::to_owned),
        };
        Self::build(creds, false, Timeouts::default(), &net)
    }

    fn build(
        creds: Box<dyn CredentialSource>,
        allow_loopback_http: bool,
        timeouts: Timeouts,
        net: &TestNet,
    ) -> Self {
        Self {
            transport: Transport::with_test_net(allow_loopback_http, timeouts, net),
            creds,
            tokens: Mutex::new(HashMap::new()),
            allow_loopback_http,
        }
    }

    fn base(&self, r: &Reference) -> String {
        let scheme = if self.allow_loopback_http && is_loopback_host(bare_host(&r.registry)) {
            "http"
        } else {
            "https"
        };
        format!("{scheme}://{}", r.registry.to_ascii_lowercase())
    }

    /// Cache key: registry origin plus scope.
    fn token_key(&self, r: &Reference, scope: &str) -> String {
        format!("{}|{scope}", self.base(r))
    }

    /// A realm is trusted on the registry's exact origin, or on a listed token
    /// service for that registry.
    fn realm_allowed(&self, r: &Reference, realm: &str) -> bool {
        if !url_allowed(realm, self.allow_loopback_http) {
            return false;
        }
        let Some(realm_origin) = origin_of(realm) else {
            return false;
        };
        let registry_origin = origin_of(&self.base(r));
        if registry_origin.as_ref() == Some(&realm_origin) {
            return true;
        }
        TOKEN_SERVICES.iter().any(|(reg, tok)| {
            origin_of(reg) == registry_origin && origin_of(tok).as_ref() == Some(&realm_origin)
        })
    }

    fn cached(&self, scope: &str) -> Option<(String, Option<OciError>)> {
        let mut t = self
            .tokens
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        match t.get(scope) {
            Some(c) if c.expires > Instant::now() => Some((c.value.clone(), c.refused.clone())),
            Some(_) => {
                t.remove(scope);
                None
            }
            None => None,
        }
    }

    /// The login for `registry`. A refusal to start a credential helper does not
    /// fail the request: anonymous access may still work. The refusal goes to
    /// `refused`, and the caller reports it when the registry then denies access.
    /// Each lookup starts clean, so a refusal from an earlier lookup (inherited
    /// with a cached token) never describes this one.
    fn login(
        &self,
        registry: &str,
        refused: &mut Option<OciError>,
    ) -> Result<Option<Credential>, OciError> {
        *refused = None;
        match self.creds.credential(registry) {
            Err(e) if e.code().is_some() => {
                tracing::warn!(
                    code = e.code(),
                    "a credential helper was refused; continuing without a login"
                );
                *refused = Some(e);
                Ok(None)
            }
            other => other,
        }
    }

    fn fetch_token(
        &self,
        r: &Reference,
        ch: &Challenge,
        scope: &str,
        refused: &mut Option<OciError>,
    ) -> Result<String, OciError> {
        let realm = ch.param("realm").ok_or_else(|| {
            OciError::Invalid(
                crate::messages::transport::TransportPhrase::OciRealmMissing
                    .as_static()
                    .into(),
            )
        })?;
        if !self.realm_allowed(r, realm) {
            return Err(OciError::RealmRejected(redact_url(realm)));
        }
        let mut url = realm.to_owned();
        url.push(if realm.contains('?') { '&' } else { '?' });
        if let Some(service) = ch.param("service") {
            let _ = write!(url, "service={}&", encode(service));
        }
        let _ = write!(url, "scope={}", encode(scope));
        let cred = self.login(&r.registry, refused)?;
        let mut resp = self.transport.send(&Req {
            method: "GET",
            url: url.clone(),
            max_body: MAX_TOKEN_BYTES as u64,
            headers: vec![("Accept", "application/json".into())],
            authorization: cred.map(|c| c.basic_header()),
            body: None,
        })?;
        let status = resp.status().as_u16();
        if status != 200 {
            return Err(if matches!(status, 401 | 403) {
                refused
                    .take()
                    .unwrap_or_else(|| OciError::Denied(redact_url(&url)))
            } else {
                OciError::Status {
                    status,
                    url: redact_url(&url),
                }
            });
        }
        let body = read_limited(
            resp.body_mut(),
            MAX_TOKEN_BYTES,
            crate::messages::transport::TransportPhrase::OciTokenResponse.as_static(),
        )?;
        let t: Tok = serde_json::from_slice(&body).map_err(|_| {
            OciError::Invalid(
                crate::messages::transport::TransportPhrase::OciTokenJson
                    .as_static()
                    .into(),
            )
        })?;
        let value = t
            .token
            .or(t.access_token)
            .filter(|v| !v.is_empty())
            .ok_or_else(|| OciError::Denied(redact_url(&url)))?;
        let ttl = Duration::from_secs(t.expires_in.unwrap_or(60).clamp(15, 3600) - 10);
        self.tokens
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .insert(
                self.token_key(r, scope),
                CachedToken {
                    value: value.clone(),
                    expires: Instant::now() + ttl,
                    refused: refused.clone(),
                },
            );
        Ok(value)
    }

    /// Send a request with lazy token acquisition and one retry after a 401.
    /// The response is a manifest-sized document at most.
    fn call(
        &self,
        r: &Reference,
        actions: &str,
        method: &'static str,
        url: &str,
        headers: &[(&'static str, String)],
        body: Option<&[u8]>,
    ) -> Result<Response<Body>, OciError> {
        self.call_capped(
            r,
            actions,
            MAX_MANIFEST_BYTES as u64,
            &Req {
                method,
                url: url.to_owned(),
                max_body: 0,
                headers: headers.to_vec(),
                authorization: None,
                body,
            },
        )
    }

    /// [`Client::call`] for a response body of up to `max_body` bytes; the raw
    /// bytes read are capped relative to it.
    fn call_capped(
        &self,
        r: &Reference,
        actions: &str,
        max_body: u64,
        template: &Req<'_>,
    ) -> Result<Response<Body>, OciError> {
        let scope = format!("repository:{}:{actions}", r.repository);
        let make = |authorization: Option<String>| Req {
            max_body,
            authorization,
            ..template.clone()
        };
        let (first, mut refused) = match self.cached(&self.token_key(r, &scope)) {
            // ast-grep-ignore: user-text-literal
            Some((token, refused)) => (Some(format!("Bearer {token}")), refused),
            None => (None, None),
        };
        let resp = self.transport.send(&make(first))?;
        let status = resp.status().as_u16();
        if status == 403
            && let Some(e) = refused
        {
            // The cached token is anonymous because a helper was refused.
            return Err(e);
        }
        if status != 401 {
            return Ok(resp);
        }
        let challenge = resp
            .headers()
            .get("www-authenticate")
            .and_then(|v| v.to_str().ok())
            .and_then(Challenge::parse);
        let Some(challenge) = challenge else {
            return Ok(resp);
        };
        let auth = match challenge.scheme.as_str() {
            // ast-grep-ignore: user-text-literal
            "bearer" => format!(
                "Bearer {}",
                self.fetch_token(r, &challenge, &scope, &mut refused)?
            ),
            "basic" => match self.login(&r.registry, &mut refused)? {
                Some(c) => c.basic_header(),
                // Anonymous access was refused already, so the refusal is why.
                None => return refused.map_or(Ok(resp), Err),
            },
            _ => return Ok(resp),
        };
        let resp = self.transport.send(&make(Some(auth)))?;
        match refused {
            Some(e) if matches!(resp.status().as_u16(), 401 | 403) => Err(e),
            _ => Ok(resp),
        }
    }

    fn deny_or_status(url: &str, status: u16) -> OciError {
        match status {
            401 | 403 => OciError::Denied(redact_url(url)),
            404 => OciError::NotFound(redact_url(url)),
            _ => OciError::Status {
                status,
                url: redact_url(url),
            },
        }
    }

    /// Fetch a manifest or index, verifying its digest when the reference is one.
    ///
    /// # Errors
    /// Any [`OciError`]: access denied, an oversized body, a digest mismatch, an unknown media type.
    pub fn fetch_manifest(&self, r: &Reference) -> Result<Fetched, OciError> {
        let url = format!(
            "{}/v2/{}/manifests/{}",
            self.base(r),
            r.repository,
            r.target
        );
        let mut resp = self.call(
            r,
            "pull",
            "GET",
            &url,
            &[("Accept", MANIFEST_ACCEPT.into())],
            None,
        )?;
        let status = resp.status().as_u16();
        if status != 200 {
            return Err(Self::deny_or_status(&url, status));
        }
        let header_type = content_type(&resp);
        check_declared_length(
            &resp,
            MAX_MANIFEST_BYTES as u64,
            crate::messages::transport::TransportPhrase::OciManifest.as_static(),
        )?;
        let body = read_limited(
            resp.body_mut(),
            MAX_MANIFEST_BYTES,
            crate::messages::transport::TransportPhrase::OciManifest.as_static(),
        )?;
        let digest = Digest::of(&body);
        if let Target::Digest(want) = &r.target
            && *want != digest
        {
            return Err(OciError::DigestMismatch {
                expected: want.to_string(),
                actual: digest.to_string(),
            });
        }
        let media_type = manifest_media_type(header_type.as_deref(), &body)?;
        Ok(Fetched {
            digest,
            media_type,
            body,
        })
    }

    /// The URL to request. Test clients (and only they) reach an `https://`
    /// URL on a loopback host over plain HTTP, so a lock, which only accepts
    /// `https://`, can point at the fake server. Production clients return the
    /// URL unchanged.
    fn reach(&self, url: &str) -> String {
        match url.strip_prefix("https://") {
            Some(rest)
                if self.allow_loopback_http
                    && is_loopback_host(bare_host(rest.split('/').next().unwrap_or_default())) =>
            {
                format!("http://{rest}")
            }
            _ => url.to_owned(),
        }
    }

    /// Download a release archive from an `https://` URL into `out`, reading at most
    /// `max` bytes. Redirects follow the same rules as registry requests, and no
    /// credentials are sent. The caller checks the digest of what was written.
    ///
    /// # Errors
    /// [`OciError::InsecureUrl`] for anything but HTTPS, [`OciError::TooLarge`] past `max`,
    /// and the usual network and status errors.
    pub fn download(&self, url: &str, max: u64, out: &mut dyn Write) -> Result<(), OciError> {
        let url = self.reach(url);
        let url = url.as_str();
        let mut resp = self.transport.send(&Req {
            method: "GET",
            url: url.to_owned(),
            max_body: max,
            headers: vec![],
            authorization: None,
            body: None,
        })?;
        let status = resp.status().as_u16();
        if status != 200 {
            return Err(Self::deny_or_status(url, status));
        }
        let shown = redact_url(url);
        let mut reader = resp.body_mut().with_config().limit(max + 1).reader();
        let copied = std::io::copy(&mut reader, out).map_err(|e| read_error(&shown, &e))?;
        if copied > max {
            return Err(OciError::TooLarge {
                what: crate::messages::transport::TransportPhrase::OciArchive
                    .as_static()
                    .into(),
                limit: max,
            });
        }
        Ok(())
    }

    /// Stream a blob into `out`, checking size and digest as it goes.
    ///
    /// On `Err` the bytes already written must be discarded: the caller writes
    /// to a temporary file and keeps it only on `Ok`.
    ///
    /// # Errors
    /// [`OciError::TooLarge`] before any request when the descriptor exceeds 256 MiB,
    /// [`OciError::SizeMismatch`] and [`OciError::DigestMismatch`] after the stream.
    pub fn pull_blob(
        &self,
        r: &Reference,
        desc: &Descriptor,
        out: &mut dyn Write,
    ) -> Result<(), OciError> {
        if desc.size > MAX_BLOB_BYTES {
            return Err(OciError::TooLarge {
                what: crate::messages::transport::TransportPhrase::OciBlob
                    .as_static()
                    .into(),
                limit: MAX_BLOB_BYTES,
            });
        }
        let url = format!("{}/v2/{}/blobs/{}", self.base(r), r.repository, desc.digest);
        let mut resp = self.call_capped(
            r,
            "pull",
            desc.size,
            &Req {
                method: "GET",
                url: url.clone(),
                max_body: 0,
                headers: vec![],
                authorization: None,
                body: None,
            },
        )?;
        let status = resp.status().as_u16();
        if status != 200 {
            return Err(Self::deny_or_status(&url, status));
        }
        check_declared_length(
            &resp,
            desc.size,
            crate::messages::transport::TransportPhrase::OciBlob.as_static(),
        )?;
        let mut reader = resp.body_mut().with_config().limit(desc.size + 1).reader();
        let mut hasher = Sha256::new();
        let mut buf = vec![0u8; 64 * 1024];
        let mut total: u64 = 0;
        loop {
            let n = reader
                .read(&mut buf)
                .map_err(|e| read_error(&redact_url(&url), &e))?;
            if n == 0 {
                break;
            }
            total += n as u64;
            if total > desc.size {
                return Err(OciError::SizeMismatch {
                    expected: desc.size,
                    actual: total,
                });
            }
            hasher.update(&buf[..n]);
            out.write_all(&buf[..n]).map_err(|e| OciError::Network {
                url: redact_url(&url),
                message: crate::messages::transport::TransportText::OciWrite {
                    detail: e.to_string(),
                }
                .to_string(),
            })?;
        }
        if total != desc.size {
            return Err(OciError::SizeMismatch {
                expected: desc.size,
                actual: total,
            });
        }
        let actual = Digest::from_hasher(hasher);
        if actual != desc.digest {
            return Err(OciError::DigestMismatch {
                expected: desc.digest.to_string(),
                actual: actual.to_string(),
            });
        }
        Ok(())
    }

    /// Fetch a small blob into memory, up to `max` bytes (for example a signature statement).
    ///
    /// # Errors
    /// As [`Client::pull_blob`], plus [`OciError::TooLarge`] above `max`.
    pub fn fetch_blob_bytes(
        &self,
        r: &Reference,
        desc: &Descriptor,
        max: u64,
    ) -> Result<Vec<u8>, OciError> {
        if desc.size > max {
            return Err(OciError::TooLarge {
                what: crate::messages::transport::TransportPhrase::OciBlob
                    .as_static()
                    .into(),
                limit: max,
            });
        }
        let mut buf = Vec::new();
        self.pull_blob(r, desc, &mut buf)?;
        Ok(buf)
    }

    /// Manifests that refer to `subject`, through the referrers API or, when the
    /// registry lacks it (GHCR), the `sha256-<hex>` tag schema.
    ///
    /// # Errors
    /// Any [`OciError`] other than a missing API or tag, which give an empty list.
    pub fn referrers(
        &self,
        r: &Reference,
        subject: &Digest,
        artifact_type: Option<&str>,
    ) -> Result<Vec<Descriptor>, OciError> {
        let mut url = format!("{}/v2/{}/referrers/{subject}", self.base(r), r.repository);
        let mut found: Vec<Descriptor> = Vec::new();
        for page in 0..MAX_TAG_PAGES {
            let mut resp = self.call(
                r,
                "pull",
                "GET",
                &url,
                &[("Accept", MEDIA_INDEX.into())],
                None,
            )?;
            let status = resp.status().as_u16();
            if status == 404 && page == 0 {
                // No referrers API: use the tag schema.
                let tag = format!("sha256-{}", subject.hex());
                match self.fetch_manifest(&r.with_target(Target::Tag(tag))) {
                    Ok(f) => found.extend(f.index()?.manifests),
                    Err(OciError::NotFound(_)) => {}
                    Err(e) => return Err(e),
                }
                Self::check_referrers_count(found.len())?;
                break;
            }
            if status != 200 {
                return Err(Self::deny_or_status(&url, status));
            }
            let next = next_link(&resp, &url);
            let header_type = content_type(&resp);
            let body = read_limited(
                resp.body_mut(),
                MAX_MANIFEST_BYTES,
                crate::messages::transport::TransportPhrase::OciReferrersIndex.as_static(),
            )?;
            let media_type = manifest_media_type(header_type.as_deref(), &body)?;
            let index = Fetched {
                digest: Digest::of(&body),
                media_type,
                body,
            }
            .index()?;
            found.extend(index.manifests);
            Self::check_referrers_count(found.len())?;
            let Some(next) = next else { break };
            url = next;
        }
        if let Some(want) = artifact_type {
            found.retain(|d| d.artifact_type.as_deref() == Some(want));
        }
        Ok(found)
    }

    /// Refuse a referrers list past the descriptor limit, before any filtering.
    fn check_referrers_count(count: usize) -> Result<(), OciError> {
        if count > MAX_TAGS {
            return Err(OciError::TooLarge {
                what: crate::messages::transport::TransportPhrase::OciReferrersList
                    .as_static()
                    .into(),
                limit: MAX_TAGS as u64,
            });
        }
        Ok(())
    }

    /// List tags, following `Link` pagination up to 10 pages and 10,000 tags.
    ///
    /// # Errors
    /// Any [`OciError`].
    pub fn list_tags(&self, r: &Reference) -> Result<Vec<String>, OciError> {
        self.list_tags_within(r, &AtomicU64::new(u64::MAX))
    }

    /// Like [`Client::list_tags`], but every page is charged to `allowance`, a
    /// byte count shared by several listings. The charge is the raw bytes read
    /// from the socket for the page (headers, TLS, chunk framing and trailers
    /// included), taken whether the page parses, fails or is refused, so a
    /// listing that fails on a later page has still used its share. A page read
    /// stops when the allowance runs out, and a listing started with none left
    /// fails at once without a request. Bytes of a request that fails before a
    /// response arrives are not charged; the per-exchange cap bounds them.
    ///
    /// # Errors
    /// Any [`OciError`]; [`OciError::TooLarge`] when the allowance is used up.
    pub fn list_tags_within(
        &self,
        r: &Reference,
        allowance: &AtomicU64,
    ) -> Result<Vec<String>, OciError> {
        #[derive(Deserialize)]
        struct Tags {
            tags: Option<Vec<String>>,
        }
        let mut url = format!("{}/v2/{}/tags/list?n=1000", self.base(r), r.repository);
        let mut all: Vec<String> = Vec::new();
        for _ in 0..MAX_TAG_PAGES {
            if allowance.load(Ordering::Relaxed) == 0 {
                return Err(OciError::TooLarge {
                    what: crate::messages::transport::TransportPhrase::OciTagList
                        .as_static()
                        .into(),
                    limit: 0,
                });
            }
            let page_max = allowance
                .load(Ordering::Relaxed)
                .min(MAX_MANIFEST_BYTES as u64);
            let called = self.call_capped(
                r,
                "pull",
                page_max,
                &Req {
                    method: "GET",
                    url: url.clone(),
                    max_body: 0,
                    headers: vec![],
                    authorization: None,
                    body: None,
                },
            );
            // A refused redirect has no response to read the meter from.
            if let Err(OciError::BadRedirect { wire_bytes, .. }) = &called {
                charge(allowance, *wire_bytes);
            }
            let mut resp = called?;
            let status = resp.status().as_u16();
            if status != 200 {
                charge(allowance, wire_bytes_used(&resp));
                return Err(Self::deny_or_status(&url, status));
            }
            let next = next_link(&resp, &url);
            let limit = usize::try_from(page_max).unwrap_or(MAX_MANIFEST_BYTES);
            let read = read_limited(
                resp.body_mut(),
                limit,
                crate::messages::transport::TransportPhrase::OciTagList.as_static(),
            );
            charge(allowance, wire_bytes_used(&resp));
            let body = read?;
            let page: Tags = serde_json::from_slice(&body).map_err(|e| {
                OciError::Invalid(
                    crate::messages::transport::TransportText::OciTagList {
                        detail: e.to_string(),
                    }
                    .to_string(),
                )
            })?;
            all.extend(page.tags.unwrap_or_default());
            if all.len() > MAX_TAGS {
                return Err(OciError::TooLarge {
                    what: crate::messages::transport::TransportPhrase::OciTagList
                        .as_static()
                        .into(),
                    limit: MAX_TAGS as u64,
                });
            }
            let Some(next) = next else { break };
            url = next;
        }
        Ok(all)
    }

    /// Upload a blob in one request, skipping the upload when the registry has it.
    ///
    /// # Errors
    /// Any [`OciError`]; 401/403 on GHCR usually means the token lacks `write:packages`.
    pub fn push_blob(
        &self,
        r: &Reference,
        media_type: &str,
        bytes: &[u8],
    ) -> Result<Descriptor, OciError> {
        if bytes.len() as u64 > MAX_BLOB_BYTES {
            return Err(OciError::TooLarge {
                what: crate::messages::transport::TransportPhrase::OciBlob
                    .as_static()
                    .into(),
                limit: MAX_BLOB_BYTES,
            });
        }
        let desc = Descriptor::for_bytes(media_type, bytes);
        let base = self.base(r);
        let head = format!("{base}/v2/{}/blobs/{}", r.repository, desc.digest);
        let exists = self.call(r, "pull,push", "HEAD", &head, &[], None)?;
        if exists.status().as_u16() == 200 {
            return Ok(desc);
        }
        let start = format!("{base}/v2/{}/blobs/uploads/", r.repository);
        let resp = self.call(
            r,
            "pull,push",
            "POST",
            &start,
            &[("Content-Length", "0".into())],
            None,
        )?;
        let status = resp.status().as_u16();
        if status != 202 {
            return Err(Self::deny_or_status(&start, status));
        }
        let location = resp
            .headers()
            .get("location")
            .and_then(|v| v.to_str().ok())
            .and_then(|l| resolve(&start, l))
            .ok_or_else(|| {
                OciError::Invalid(
                    crate::messages::transport::TransportPhrase::OciUploadLocation
                        .as_static()
                        .into(),
                )
            })?;
        if host_of(&location) != host_of(&start) {
            return Err(OciError::BadRedirect {
                url: redact_url(&start),
                why: crate::messages::transport::TransportPhrase::OciUploadHost
                    .as_static()
                    .into(),
                wire_bytes: 0,
            });
        }
        let put = format!(
            "{location}{}digest={}",
            if location.contains('?') { '&' } else { '?' },
            desc.digest
        );
        let resp = self.call(
            r,
            "pull,push",
            "PUT",
            &put,
            &[("Content-Type", "application/octet-stream".into())],
            Some(bytes),
        )?;
        let status = resp.status().as_u16();
        if status != 201 {
            return Err(Self::deny_or_status(&put, status));
        }
        Ok(desc)
    }

    /// Put a manifest under the reference's tag or digest. Returns its digest.
    ///
    /// # Errors
    /// Any [`OciError`].
    pub fn push_manifest(
        &self,
        r: &Reference,
        media_type: &str,
        body: &[u8],
    ) -> Result<Digest, OciError> {
        if body.len() > MAX_MANIFEST_BYTES {
            return Err(OciError::TooLarge {
                what: crate::messages::transport::TransportPhrase::OciManifest
                    .as_static()
                    .into(),
                limit: MAX_MANIFEST_BYTES as u64,
            });
        }
        let url = format!(
            "{}/v2/{}/manifests/{}",
            self.base(r),
            r.repository,
            r.target
        );
        let resp = self.call(
            r,
            "pull,push",
            "PUT",
            &url,
            &[("Content-Type", media_type.into())],
            Some(body),
        )?;
        let status = resp.status().as_u16();
        if status != 201 && status != 200 {
            return Err(Self::deny_or_status(&url, status));
        }
        Ok(Digest::of(body))
    }
}

/// The `rel="next"` target of a paginated response, resolved against `url`.
/// Every link-value of every `Link` header is considered. A link to another
/// origin is ignored, so a page can never steer the client elsewhere.
fn next_link(resp: &Response<Body>, url: &str) -> Option<String> {
    let target = resp
        .headers()
        .get_all("link")
        .iter()
        .filter_map(|v| v.to_str().ok())
        .find_map(next_target)?;
    let next = resolve(url, target)?;
    (origin_of(&next) == origin_of(url)).then_some(next)
}

/// The URI reference of the first link-value with `rel` `next` (RFC 8288).
fn next_target(header: &str) -> Option<&str> {
    let mut rest = header;
    while let Some(open) = rest.find('<') {
        let after = &rest[open + 1..];
        let close = after.find('>')?;
        let (target, tail) = (&after[..close], &after[close + 1..]);
        // The parameters end at the next comma outside a quoted string.
        let (mut quoted, mut escaped, mut end) = (false, false, tail.len());
        for (i, c) in tail.char_indices() {
            match c {
                _ if escaped => escaped = false,
                '\\' if quoted => escaped = true,
                '"' => quoted = !quoted,
                ',' if !quoted => {
                    end = i;
                    break;
                }
                _ => {}
            }
        }
        if has_rel_next(&tail[..end]) {
            return Some(target);
        }
        rest = &tail[(end + 1).min(tail.len())..];
    }
    None
}

fn has_rel_next(params: &str) -> bool {
    let (mut quoted, mut escaped) = (false, false);
    let mut start = 0;
    let mut pieces = Vec::new();
    for (i, c) in params.char_indices() {
        match c {
            _ if escaped => escaped = false,
            '\\' if quoted => escaped = true,
            '"' => quoted = !quoted,
            ';' if !quoted => {
                pieces.push(&params[start..i]);
                start = i + 1;
            }
            _ => {}
        }
    }
    pieces.push(&params[start..]);
    pieces.iter().any(|piece| {
        piece.split_once('=').is_some_and(|(name, value)| {
            name.trim().eq_ignore_ascii_case("rel")
                && value
                    .trim()
                    .trim_matches('"')
                    .split_ascii_whitespace()
                    .any(|rel| rel.eq_ignore_ascii_case("next"))
        })
    })
}

fn check_declared_length(resp: &Response<Body>, limit: u64, what: &str) -> Result<(), OciError> {
    let declared = resp
        .headers()
        .get("content-length")
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.parse::<u64>().ok());
    match declared {
        Some(n) if n > limit => Err(OciError::TooLarge {
            what: what.into(),
            limit,
        }),
        _ => Ok(()),
    }
}

fn read_limited(body: &mut Body, limit: usize, what: &str) -> Result<Vec<u8>, OciError> {
    let mut buf = Vec::new();
    body.with_config()
        .limit(limit as u64 + 1)
        .reader()
        .read_to_end(&mut buf)
        .map_err(|e| read_error(what, &e))?;
    if buf.len() > limit {
        return Err(OciError::TooLarge {
            what: what.into(),
            limit: limit as u64,
        });
    }
    Ok(buf)
}

/// Take `used` bytes from the shared `allowance`, down to zero.
fn charge(allowance: &AtomicU64, used: u64) {
    let _ = allowance.try_update(Ordering::Relaxed, Ordering::Relaxed, |v| {
        Some(v.saturating_sub(used))
    });
}

fn encode(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for b in s.bytes() {
        if b.is_ascii_alphanumeric() || matches!(b, b'-' | b'.' | b'_' | b'~') {
            out.push(char::from(b));
        } else {
            let _ = write!(out, "%{b:02X}");
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::encode;

    #[test]
    fn query_encoding_keeps_unreserved_and_escapes_the_rest() {
        assert_eq!(
            encode("repository:a/b:pull,push"),
            "repository%3Aa%2Fb%3Apull%2Cpush"
        );
        assert_eq!(encode("ghcr.io"), "ghcr.io");
    }
}
