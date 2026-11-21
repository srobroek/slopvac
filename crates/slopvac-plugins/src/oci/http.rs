//! Redirect-aware HTTP on top of `ureq`.

use std::fmt;
use std::io;
use std::net::IpAddr;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use ureq::config::Config;
use ureq::http::{Request, Response, Uri};
use ureq::tls::{Certificate, RootCerts, TlsConfig};
use ureq::unversioned::resolver::DefaultResolver;
use ureq::unversioned::transport::{
    Buffers, ConnectProxyConnector, ConnectionDetails, Connector, Either, NextTimeout,
    RustlsConnector, TcpConnector, Transport as WireIo,
};
use ureq::{Agent, Body, Proxy};

use super::{MAX_REDIRECTS, OciError, redact_url};

/// Time limits for one exchange.
#[derive(Clone, Copy)]
pub(crate) struct Timeouts {
    /// Longest the request body may take to send.
    pub send_body: Duration,
    /// Longest a whole exchange may take, from connect to the last body byte.
    pub global: Duration,
}

impl Default for Timeouts {
    fn default() -> Self {
        Self {
            send_body: Duration::from_mins(30),
            global: Duration::from_hours(1),
        }
    }
}

/// Raw bytes one hop of an exchange may take besides the body: response
/// headers (ureq limits them to 64 KiB), a TLS handshake with a certificate
/// chain, session tickets and a proxy's `CONNECT` reply.
const HOP_ALLOWANCE: u64 = 192 << 10;

/// Raw bytes allowed on the socket for a response body of at most `body_max`
/// bytes: the body, TLS record and chunk framing at one part in 64 (records and
/// chunks of 4 KiB or more stay below it), and the allowance of the first hop.
/// Each redirect followed adds [`HOP_ALLOWANCE`] ([`WireMeter::allow_hop`]).
fn wire_cap(body_max: u64) -> u64 {
    body_max
        .saturating_add(body_max / 64)
        .saturating_add(HOP_ALLOWANCE)
}

/// Bytes received from one registry exchange, below TLS and any proxy.
///
/// Body limits count decoded bytes only. This counts every byte read from the
/// TCP socket, so TLS records and handshakes, status lines, headers, chunk
/// framing and trailers count too, and a read that fails still has its bytes
/// charged. A response that passes the cap stops the connection.
///
/// [`Transport::send`] stores the meter in the response extensions as an
/// `Arc<WireMeter>`, so callers can charge [`WireMeter::used`] to a budget
/// shared by several responses.
#[derive(Debug)]
pub(crate) struct WireMeter {
    used: AtomicU64,
    cap: AtomicU64,
}

impl WireMeter {
    fn new(cap: u64) -> Self {
        Self {
            used: AtomicU64::new(0),
            cap: AtomicU64::new(cap),
        }
    }

    /// Raw bytes read so far, failed reads included.
    pub(crate) fn used(&self) -> u64 {
        self.used.load(Ordering::Relaxed)
    }

    fn charge(&self, n: u64) {
        self.used.fetch_add(n, Ordering::Relaxed);
    }

    fn cap(&self) -> u64 {
        self.cap.load(Ordering::Relaxed)
    }

    /// Room for the connection and headers of one more redirect hop.
    fn allow_hop(&self) {
        self.cap.fetch_add(HOP_ALLOWANCE, Ordering::Relaxed);
    }

    fn exceeded(&self) -> bool {
        self.used() > self.cap()
    }
}

/// Raw bytes read so far for the exchange that produced `resp`, headers,
/// handshakes and trailers included, and the bytes of every redirect hop and
/// failed read. Zero for a response that did not come from [`Transport::send`].
pub(crate) fn wire_bytes_used<T>(resp: &Response<T>) -> u64 {
    resp.extensions()
        .get::<Arc<WireMeter>>()
        .map_or(0, |m| m.used())
}

/// The I/O error a [`WireMeter`] raises past its cap.
#[derive(Debug)]
struct WireLimit {
    limit: u64,
}

impl fmt::Display for WireLimit {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(
            &crate::messages::transport::TransportText::OciWireLimit { limit: self.limit }
                .to_string(),
        )
    }
}

impl std::error::Error for WireLimit {}

/// The [`OciError`] for a failed read of `url`: [`OciError::TooLarge`] when the
/// wire cap stopped it, otherwise a network error.
pub(crate) fn read_error(url: &str, e: &io::Error) -> OciError {
    if let Some(WireLimit { limit }) = e.get_ref().and_then(|i| i.downcast_ref::<WireLimit>()) {
        return OciError::TooLarge {
            what: crate::messages::transport::TransportPhrase::OciResponse
                .as_static()
                .into(),
            limit: *limit,
        };
    }
    OciError::Network {
        url: url.to_owned(),
        message: e.to_string(),
    }
}

/// [`TcpConnector`] that meters the socket it opens.
///
/// The `CONNECT` proxy connector runs the whole chain again for its own leg and
/// hands the result down as `chained`. That leg is already metered, and so is
/// every byte of the tunnel it carries, so a chained transport passes through
/// and each socket is metered once.
struct MeterTcp {
    tcp: TcpConnector,
    meter: Arc<WireMeter>,
}

impl fmt::Debug for MeterTcp {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("MeterTcp").finish_non_exhaustive()
    }
}

impl<In: WireIo> Connector<In> for MeterTcp {
    type Out = Either<In, Metered>;

    fn connect(
        &self,
        details: &ConnectionDetails<'_>,
        chained: Option<In>,
    ) -> Result<Option<Self::Out>, ureq::Error> {
        if chained.is_some() {
            return Ok(chained.map(Either::A));
        }
        Ok(self
            .tcp
            .connect(details, None::<In>)?
            .map(|opened| match opened {
                Either::A(other) => Either::A(other),
                Either::B(socket) => Either::B(Metered {
                    inner: Box::new(socket),
                    meter: Arc::clone(&self.meter),
                }),
            }))
    }
}

#[derive(Debug)]
struct Metered {
    inner: Box<dyn WireIo>,
    meter: Arc<WireMeter>,
}

impl Metered {
    fn check(&self) -> Result<(), ureq::Error> {
        if self.meter.exceeded() {
            let limit = self.meter.cap();
            return Err(ureq::Error::Io(io::Error::other(WireLimit { limit })));
        }
        Ok(())
    }
}

impl WireIo for Metered {
    fn buffers(&mut self) -> &mut dyn Buffers {
        self.inner.buffers()
    }

    fn transmit_output(&mut self, amount: usize, timeout: NextTimeout) -> Result<(), ureq::Error> {
        self.inner.transmit_output(amount, timeout)
    }

    fn await_input(&mut self, timeout: NextTimeout) -> Result<bool, ureq::Error> {
        self.check()?;
        // The decoder consumes input only between reads, so the growth of the
        // unconsumed input is exactly what this read added.
        let before = self.inner.buffers().input().len();
        let progress = self.inner.await_input(timeout);
        let after = self.inner.buffers().input().len();
        self.meter.charge(after.saturating_sub(before) as u64);
        let progress = progress?;
        self.check()?;
        Ok(progress)
    }

    fn is_open(&mut self) -> bool {
        self.inner.is_open()
    }

    fn is_tls(&self) -> bool {
        self.inner.is_tls()
    }
}

/// Settings only tests use: a trusted root for a local HTTPS registry and a
/// `CONNECT` proxy. Production transports use the platform roots and the
/// proxy settings of the environment.
#[derive(Clone, Default)]
pub(crate) struct TestNet {
    /// DER certificate to trust instead of the platform roots.
    pub root: Option<Vec<u8>>,
    /// Proxy URL, such as `http://127.0.0.1:3128`.
    pub proxy: Option<String>,
}

pub(crate) struct Transport {
    config: Config,
    allow_loopback_http: bool,
}

#[derive(Clone)]
pub(crate) struct Req<'a> {
    pub method: &'static str,
    pub url: String,
    /// Most decoded body bytes the caller will read; the raw bytes of the
    /// exchange are capped relative to it.
    pub max_body: u64,
    pub headers: Vec<(&'static str, String)>,
    /// Full `Authorization` header value, sent only to the first host.
    pub authorization: Option<String>,
    pub body: Option<&'a [u8]>,
}

pub(crate) fn host_of(url: &str) -> Option<(String, String)> {
    let uri: Uri = url.parse().ok()?;
    let scheme = uri.scheme_str()?.to_owned();
    let auth = uri.authority()?;
    Some((
        scheme,
        auth.as_str().rsplit('@').next()?.to_ascii_lowercase(),
    ))
}

pub(crate) fn is_loopback_host(host: &str) -> bool {
    let h = host.trim_start_matches('[').trim_end_matches(']');
    h == "localhost" || h.parse::<IpAddr>().is_ok_and(|ip| ip.is_loopback())
}

/// Host part of an authority (no port, no brackets removed for v6 literals).
pub(crate) fn bare_host(authority: &str) -> &str {
    if let Some(end) = authority.strip_prefix('[').and_then(|r| r.find(']')) {
        return &authority[..end + 2];
    }
    authority.rsplit_once(':').map_or(authority, |(h, _)| h)
}

/// Scheme, lowercase host and port of a URL, with the default port filled in.
/// `None` for a URL without a host or with userinfo.
pub(crate) type Origin = (String, String, u16);

pub(crate) fn origin_of(url: &str) -> Option<Origin> {
    let uri: Uri = url.parse().ok()?;
    let scheme = uri.scheme_str()?.to_ascii_lowercase();
    let auth = uri.authority()?;
    if auth.as_str().contains('@') {
        return None;
    }
    let port = match (uri.port_u16(), scheme.as_str()) {
        (Some(p), _) => p,
        (None, "https") => 443,
        (None, "http") => 80,
        _ => return None,
    };
    let host = uri.host().filter(|h| !h.is_empty())?.to_ascii_lowercase();
    Some((scheme, host, port))
}

/// Whether `url` may be requested: HTTPS, or, when `allow_loopback_http` is set
/// (test clients only), HTTP on a loopback host.
pub(crate) fn url_allowed(url: &str, allow_loopback_http: bool) -> bool {
    match host_of(url) {
        Some((s, a)) if s == "https" => !a.is_empty(),
        Some((s, a)) if s == "http" => allow_loopback_http && is_loopback_host(bare_host(&a)),
        _ => false,
    }
}

/// Remove `.` and `..` segments from an absolute path (RFC 3986 section 5.2.4).
fn remove_dot_segments(path: &str) -> String {
    let mut out: Vec<&str> = Vec::new();
    let mut trailing = false;
    for seg in path.split('/').skip(1) {
        trailing = false;
        match seg {
            "." => trailing = true,
            ".." => {
                out.pop();
                trailing = true;
            }
            s => out.push(s),
        }
    }
    let mut r = String::from("/");
    r.push_str(&out.join("/"));
    if trailing && !r.ends_with('/') {
        r.push('/');
    }
    r
}

/// Resolve a URI reference against `base` (RFC 3986 section 5.2) for the forms
/// registries send: absolute, network-path, absolute-path, query-only and
/// relative-path.
pub(crate) fn resolve(base: &str, reference: &str) -> Option<String> {
    let (scheme, rest) = base.split_once("://")?;
    let rest = rest.split('#').next().unwrap_or(rest);
    let (authority, path_query) = rest
        .find(['/', '?'])
        .map_or((rest, ""), |i| (&rest[..i], &rest[i..]));
    let (base_path, base_query) = match path_query.split_once('?') {
        Some((p, q)) => (p, Some(q)),
        None => (path_query, None),
    };
    let base_path = if base_path.is_empty() { "/" } else { base_path };

    // A fragment is never sent to a server, and a query added later would land
    // inside it.
    let reference = reference.split('#').next().unwrap_or(reference);
    let first_seg = reference.split(['/', '?']).next().unwrap_or("");
    if first_seg.contains(':') {
        return Some(reference.to_owned());
    }
    if let Some(r) = reference.strip_prefix("//") {
        return Some(format!("{scheme}://{r}"));
    }
    if reference.is_empty() {
        let q = base_query.map_or(String::new(), |q| format!("?{q}"));
        return Some(format!("{scheme}://{authority}{base_path}{q}"));
    }
    if let Some(q) = reference.strip_prefix('?') {
        return Some(format!("{scheme}://{authority}{base_path}?{q}"));
    }
    let (ref_path, ref_query) = reference
        .split_once('?')
        .map_or((reference, String::new()), |(p, q)| (p, format!("?{q}")));
    let merged = if ref_path.starts_with('/') {
        ref_path.to_owned()
    } else {
        let dir = base_path.rsplit_once('/').map_or("", |(d, _)| d);
        format!("{dir}/{ref_path}")
    };
    Some(format!(
        "{scheme}://{authority}{}{ref_query}",
        remove_dot_segments(&merged)
    ))
}

impl Transport {
    /// `allow_loopback_http` is set only by the test-only client constructor;
    /// production transports refuse every `http://` URL, redirects included.
    #[cfg(test)]
    pub(crate) fn new(allow_loopback_http: bool, timeouts: Timeouts) -> Self {
        Self::with_test_net(allow_loopback_http, timeouts, &TestNet::default())
    }

    /// A transport with the test settings of `net`.
    pub(crate) fn with_test_net(
        allow_loopback_http: bool,
        timeouts: Timeouts,
        net: &TestNet,
    ) -> Self {
        let roots = net
            .root
            .as_ref()
            .map_or(RootCerts::PlatformVerifier, |der| {
                RootCerts::new_with_certs(&[Certificate::from_der(der).to_owned()])
            });
        let tls = TlsConfig::builder().root_certs(roots).build();
        let mut builder = Config::builder();
        if let Some(proxy) = &net.proxy {
            builder = builder.proxy(Some(Proxy::new(proxy).expect("a proxy URL")));
        }
        let config = builder
            .http_status_as_error(false)
            .max_redirects(0)
            .max_redirects_will_error(false)
            .tls_config(tls)
            .timeout_connect(Some(Duration::from_secs(15)))
            .timeout_recv_response(Some(Duration::from_secs(60)))
            .timeout_recv_body(Some(Duration::from_secs(600)))
            .timeout_send_body(Some(timeouts.send_body))
            .timeout_global(Some(timeouts.global))
            .user_agent(concat!("slopvac/", env!("CARGO_PKG_VERSION")))
            .build();
        Self {
            config,
            allow_loopback_http,
        }
    }

    /// Where a redirect from `url` to `location` may go. This is the only check a
    /// redirect target passes before the next request, so production transports
    /// stop here at any `http://` target, loopback included.
    fn redirect_target(&self, url: &str, location: &str) -> Result<String, &'static str> {
        let next = resolve(url, location)
            .ok_or(crate::messages::transport::TransportPhrase::OciLocationUnusable.as_static())?;
        if url_allowed(&next, self.allow_loopback_http) {
            Ok(next)
        } else {
            Err(crate::messages::transport::TransportPhrase::OciTargetInsecure.as_static())
        }
    }

    pub(crate) fn send(&self, req: &Req<'_>) -> Result<Response<Body>, OciError> {
        let mut url = req.url.clone();
        let mut auth = req.authorization.clone();
        let mut hops = 0;
        // One meter and one agent per exchange: the wire cap is per response,
        // and a pooled connection would carry it into the next request. The
        // price is a new connection, and a TLS handshake, for every request.
        let meter = Arc::new(WireMeter::new(wire_cap(req.max_body)));
        let agent = Agent::with_parts(
            self.config.clone(),
            // The default chain minus SOCKS (not built), with the socket metered
            // below TLS and below a `CONNECT` proxy.
            ().chain(ConnectProxyConnector::default())
                .chain(MeterTcp {
                    tcp: TcpConnector::default(),
                    meter: Arc::clone(&meter),
                })
                .chain(RustlsConnector::default()),
            DefaultResolver::default(),
        );
        loop {
            if !url_allowed(&url, self.allow_loopback_http) {
                return Err(OciError::InsecureUrl(redact_url(&url)));
            }
            let mut b = Request::builder().method(req.method).uri(&url);
            for (k, v) in &req.headers {
                b = b.header(*k, v);
            }
            if let Some(a) = &auth {
                b = b.header("Authorization", a);
            }
            let request = b
                .body(req.body.map(<[u8]>::to_vec).unwrap_or_default())
                .map_err(|e| {
                    OciError::Invalid(
                        crate::messages::transport::TransportText::OciRequest {
                            url: redact_url(&url),
                            detail: e.to_string(),
                        }
                        .to_string(),
                    )
                })?;
            let mut resp = agent.run(request).map_err(|e| match e {
                ureq::Error::Io(e) => read_error(&redact_url(&url), &e),
                e => OciError::Network {
                    url: redact_url(&url),
                    message: e.to_string(),
                },
            })?;
            resp.extensions_mut().insert(Arc::clone(&meter));
            let status = resp.status().as_u16();
            if !matches!(status, 301 | 302 | 303 | 307 | 308) {
                return Ok(resp);
            }
            let bad = |why: &str| OciError::BadRedirect {
                url: redact_url(&url),
                why: why.to_owned(),
                wire_bytes: meter.used(),
            };
            if !matches!(req.method, "GET" | "HEAD") {
                return Err(bad(
                    crate::messages::transport::TransportPhrase::OciRedirectMethod.as_static(),
                ));
            }
            hops += 1;
            meter.allow_hop();
            if hops > MAX_REDIRECTS {
                return Err(bad(
                    crate::messages::transport::TransportPhrase::OciRedirectCount.as_static(),
                ));
            }
            let loc = resp
                .headers()
                .get("location")
                .and_then(|v| v.to_str().ok())
                .ok_or_else(|| {
                    bad(crate::messages::transport::TransportPhrase::OciLocationMissing.as_static())
                })?;
            let next = self.redirect_target(&url, loc).map_err(bad)?;
            if host_of(&next).map(|h| h.1) != host_of(&url).map(|h| h.1) {
                auth = None;
            }
            url = next;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn production_allows_only_https_and_tests_add_loopback_http() {
        for ok in ["https://ghcr.io/v2/", "https://127.0.0.1:5000/v2/"] {
            assert!(url_allowed(ok, false), "{ok}");
        }
        for loopback in [
            "http://127.0.0.1:5000/v2/",
            "http://localhost/v2/",
            "http://[::1]:5000/x",
        ] {
            assert!(!url_allowed(loopback, false), "{loopback}");
            assert!(url_allowed(loopback, true), "{loopback}");
        }
        for bad in [
            "http://ghcr.io/v2/",
            "ftp://x/y",
            "file:///etc/passwd",
            "http://127.0.0.1.evil.com/",
            "/v2/",
            "https://",
        ] {
            assert!(!url_allowed(bad, false), "{bad}");
            assert!(!url_allowed(bad, true), "{bad}");
        }
    }

    #[test]
    fn a_production_redirect_never_leaves_https_even_for_loopback() {
        let production = Transport::new(false, Timeouts::default());
        for location in [
            "http://127.0.0.1:5000/v2/",
            "http://localhost/x",
            "http://[::1]:5000/x",
            "//127.0.0.1:5000/x",
            "http://cdn.example/x",
        ] {
            // `//` resolves against the https base, so it stays HTTPS; the rest
            // name http:// and must be refused.
            let got = production.redirect_target("https://ghcr.io/v2/a/blobs/d", location);
            if location.starts_with("//") {
                assert_eq!(got.as_deref(), Ok("https://127.0.0.1:5000/x"));
            } else {
                assert_eq!(got, Err("target is not HTTPS"), "{location}");
            }
        }
        assert_eq!(
            production.redirect_target("https://ghcr.io/a", "https://cdn.example/b"),
            Ok("https://cdn.example/b".to_owned())
        );
    }

    #[test]
    fn the_test_transport_alone_follows_a_redirect_to_loopback_http() {
        let testing = Transport::new(true, Timeouts::default());
        assert_eq!(
            testing.redirect_target("http://127.0.0.1:1/a", "http://127.0.0.1:2/b"),
            Ok("http://127.0.0.1:2/b".to_owned())
        );
    }

    #[test]
    fn origins_compare_scheme_host_and_port() {
        let o = |u| origin_of(u);
        assert_eq!(o("https://GHCR.io/token"), o("https://ghcr.io:443/x"));
        assert_ne!(o("https://ghcr.io/token"), o("https://ghcr.io:8443/token"));
        assert_ne!(o("https://ghcr.io/token"), o("http://ghcr.io/token"));
        assert_eq!(o("https://u:p@ghcr.io/token"), None);
    }

    #[test]
    fn reference_resolution_follows_rfc_3986() {
        let base = "https://ghcr.io/v2/a/b/tags/list?n=1000";
        for (reference, want) in [
            ("https://cdn.example/x?sig=1", "https://cdn.example/x?sig=1"),
            ("//cdn.example/p", "https://cdn.example/p"),
            ("/v2/other?x=1", "https://ghcr.io/v2/other?x=1"),
            ("?last=1.0.0", "https://ghcr.io/v2/a/b/tags/list?last=1.0.0"),
            ("next?x=1", "https://ghcr.io/v2/a/b/tags/next?x=1"),
            ("../c", "https://ghcr.io/v2/a/b/c"),
            ("./", "https://ghcr.io/v2/a/b/tags/"),
            ("", "https://ghcr.io/v2/a/b/tags/list?n=1000"),
            (
                "?next=http://x/y",
                "https://ghcr.io/v2/a/b/tags/list?next=http://x/y",
            ),
        ] {
            assert_eq!(
                resolve(base, reference).as_deref(),
                Some(want),
                "{reference}"
            );
        }
        assert_eq!(
            resolve("https://ghcr.io", "next").as_deref(),
            Some("https://ghcr.io/next")
        );
    }
}
