//! Registry credentials and `WWW-Authenticate` challenges.
//!
//! Precedence, first match wins:
//!
//! 1. `SLOPVAC_OCI_USER` plus `SLOPVAC_OCI_TOKEN`;
//! 2. `GITHUB_TOKEN`, for `ghcr.io` only;
//! 3. static `auths` in the Docker config (`$DOCKER_CONFIG/config.json` or
//!    `~/.docker/config.json`);
//! 4. static `auths` in the first registry auth file that exists, in the order
//!    go-containerregistry's default keychain uses: `$REGISTRY_AUTH_FILE`,
//!    `$XDG_RUNTIME_DIR/containers/auth.json`, then
//!    `$XDG_CONFIG_HOME/containers/auth.json` (`~/.config` when unset);
//! 5. the credential helper the Docker config names (`credHelpers` for the
//!    registry, else `credsStore`), found only in trusted `PATH` directories;
//! 6. anonymous.
//!
//! Credentials live in memory and in request headers only.
//!
//! The `docker_credential` crate was considered. It runs a helper with no
//! timeout, no output cap and no name check, which the threat model (N6)
//! requires, so this module reads the config and runs the helper itself.

use std::fmt;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use base64::Engine as _;
use serde::Deserialize;

use super::OciError;
use super::process::Contained;
use crate::trusted_path::find_trusted;

/// Longest a credential helper may run.
pub(crate) const HELPER_TIMEOUT: Duration = Duration::from_secs(10);
/// Most bytes a credential helper may print.
pub(crate) const HELPER_MAX_OUTPUT: usize = 64 * 1024;
const MAX_CONFIG_BYTES: u64 = 1 << 20;

/// A username and secret. `Debug` never prints the secret.
#[derive(Clone, PartialEq, Eq)]
pub struct Credential {
    /// Account name.
    pub username: String,
    /// Password or token.
    pub secret: String,
}

impl fmt::Debug for Credential {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Credential")
            .field("username", &self.username)
            .field("secret", &"<redacted>")
            .finish()
    }
}

impl Credential {
    pub(crate) fn basic_header(&self) -> String {
        let raw = format!("{}:{}", self.username, self.secret);
        // ast-grep-ignore: user-text-literal
        format!(
            "Basic {}",
            base64::engine::general_purpose::STANDARD.encode(raw)
        )
    }
}

/// Where credentials come from. Called once per registry request that needs them.
pub trait CredentialSource: Send + Sync {
    /// Credential for `registry` (host with optional port), or `None` for anonymous.
    ///
    /// # Errors
    /// [`OciError::Credential`] when a helper fails or the config is unreadable.
    fn credential(&self, registry: &str) -> Result<Option<Credential>, OciError>;
}

/// No credentials: anonymous access only.
#[derive(Debug, Default, Clone, Copy)]
pub struct Anonymous;

impl CredentialSource for Anonymous {
    fn credential(&self, _: &str) -> Result<Option<Credential>, OciError> {
        Ok(None)
    }
}

/// Environment and Docker config, in the documented precedence.
#[derive(Debug, Clone, Default)]
pub struct DefaultCredentials {
    /// Values for `SLOPVAC_OCI_USER`, `SLOPVAC_OCI_TOKEN` and `GITHUB_TOKEN`
    /// in that order, read by the caller so tests need no process environment.
    pub env: EnvCredentials,
    /// Directory that holds `config.json`. `None` disables the Docker config.
    pub docker_config_dir: Option<PathBuf>,
    /// Registry auth files, tried in order. The first one that is a file
    /// supplies static `auths`; the others are not read.
    pub auth_files: Vec<PathBuf>,
    /// Directories searched for `docker-credential-*`. `None` uses `PATH`.
    /// Only trusted directories count: absolute, outside the project, and
    /// closed to group and others (CWE-427).
    pub helper_search_path: Option<std::ffi::OsString>,
    /// The project directory, where no helper may run from. A helper lookup
    /// without it fails with [`OciError::HelperProjectUnknown`]: slopvac never
    /// guesses the project from the working directory, which may be a
    /// subdirectory of a hostile checkout.
    pub project_root: Option<PathBuf>,
    /// Helper time limit. `None` means the default of 10 seconds; tests shorten it.
    pub helper_timeout: Option<Duration>,
}

/// Credential-related environment values.
#[derive(Clone, Default)]
pub struct EnvCredentials {
    /// `SLOPVAC_OCI_USER`.
    pub user: Option<String>,
    /// `SLOPVAC_OCI_TOKEN`.
    pub token: Option<String>,
    /// `GITHUB_TOKEN`.
    pub github_token: Option<String>,
}

impl fmt::Debug for EnvCredentials {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("EnvCredentials")
            .field("user", &self.user)
            .finish_non_exhaustive()
    }
}

impl DefaultCredentials {
    /// Read the process environment: `SLOPVAC_OCI_*`, `GITHUB_TOKEN`, `DOCKER_CONFIG`
    /// and the home directory's `.docker`. The project directory is never read for
    /// settings; `project_root` only keeps helpers out of it.
    #[must_use]
    pub fn from_env(project_root: impl Into<PathBuf>) -> Self {
        let mut creds = Self::from_lookup(|k| std::env::var(k).ok(), cfg!(windows));
        creds.project_root = Some(project_root.into());
        creds
    }

    /// Test seam: [`Self::from_env`] over any variable lookup and platform, so
    /// tests need no process environment.
    #[doc(hidden)]
    #[must_use]
    pub fn from_lookup_for_tests(var: impl Fn(&str) -> Option<String>, windows: bool) -> Self {
        Self::from_lookup(var, windows)
    }

    /// Docker finds its default config under `USERPROFILE` on Windows and
    /// `HOME` elsewhere; on Windows `HOME` is the fallback for shells that set
    /// only it.
    fn from_lookup(var: impl Fn(&str) -> Option<String>, windows: bool) -> Self {
        let get = |k: &str| var(k).filter(|v| !v.is_empty());
        let home = if windows {
            get("USERPROFILE").or_else(|| get("HOME"))
        } else {
            get("HOME")
        };
        let home_dir = home.clone();
        let docker = get("DOCKER_CONFIG")
            .map(PathBuf::from)
            .or_else(|| home.map(|h| Path::new(&h).join(".docker")));
        Self {
            env: EnvCredentials {
                user: get("SLOPVAC_OCI_USER"),
                token: get("SLOPVAC_OCI_TOKEN"),
                github_token: get("GITHUB_TOKEN"),
            },
            docker_config_dir: docker,
            auth_files: auth_file_candidates(&get, home_dir.as_deref()),
            helper_search_path: None,
            project_root: None,
            helper_timeout: None,
        }
    }
}

/// Where registry auth files may be, in go-containerregistry's order.
fn auth_file_candidates(get: &impl Fn(&str) -> Option<String>, home: Option<&str>) -> Vec<PathBuf> {
    let mut found = Vec::new();
    found.extend(get("REGISTRY_AUTH_FILE").map(PathBuf::from));
    found.extend(get("XDG_RUNTIME_DIR").map(|d| Path::new(&d).join("containers/auth.json")));
    let config = get("XDG_CONFIG_HOME")
        .map(PathBuf::from)
        .or_else(|| home.map(|h| Path::new(h).join(".config")));
    found.extend(config.map(|d| d.join("containers/auth.json")));
    found
}

#[derive(Deserialize, Default)]
struct DockerConfig {
    #[serde(default)]
    auths: std::collections::HashMap<String, AuthEntry>,
    #[serde(default, rename = "credHelpers")]
    cred_helpers: std::collections::HashMap<String, String>,
    #[serde(default, rename = "credsStore")]
    creds_store: Option<String>,
}

#[derive(Deserialize, Default, PartialEq, Eq)]
struct AuthEntry {
    #[serde(default)]
    auth: Option<String>,
    #[serde(default)]
    username: Option<String>,
    #[serde(default)]
    password: Option<String>,
}

/// Normalise a key of `auths`: drop the scheme and any path.
fn auth_key_host(key: &str) -> &str {
    let k = key.split_once("://").map_or(key, |(_, r)| r);
    k.split('/').next().unwrap_or(k)
}

/// The one value among `matches`, the config entries whose key names `registry`
/// up to ASCII case. Keys that differ only in case are one host (RFC 4343), so
/// differing values are ambiguous and refused instead of picked by map order.
fn unique_match<'a, T: PartialEq>(
    mut matches: impl Iterator<Item = &'a T>,
    section: &str,
    registry: &str,
) -> Result<Option<&'a T>, OciError> {
    let first = matches.next();
    if let Some(a) = first
        && matches.any(|b| a != b)
    {
        return Err(OciError::Credential(
            crate::messages::transport::TransportText::OciConfigConflict {
                section: section.to_owned(),
                registry: registry.to_owned(),
            }
            .to_string(),
        ));
    }
    Ok(first)
}

/// A registry name safe to hand to a helper: host characters and an optional port.
pub(crate) fn safe_registry_name(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 260
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'-' | b':'))
}

/// `[a-z0-9_.-]+`, not starting with a dot or dash.
pub(crate) fn safe_helper_name(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 64
        && !s.starts_with(['.', '-'])
        && s.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'_' | b'.' | b'-')
        })
}

#[derive(Deserialize)]
#[serde(rename_all = "PascalCase")]
struct HelperReply {
    username: String,
    secret: String,
}

/// File-name suffixes that make a helper runnable on this platform. Unix needs
/// none. Windows honours `PATHEXT` but only for `.exe` and `.com`: batch files
/// would run through `cmd.exe`, whose argument parsing is unsafe to feed.
fn executable_suffixes() -> Vec<String> {
    if !cfg!(windows) {
        return vec![String::new()];
    }
    let pathext = std::env::var("PATHEXT").unwrap_or_default();
    let mut found: Vec<String> = pathext
        .split(';')
        .map(str::to_ascii_lowercase)
        .filter(|e| matches!(e.as_str(), ".exe" | ".com"))
        .collect();
    if found.is_empty() {
        found = vec![".exe".into(), ".com".into()];
    }
    found
}

pub(crate) fn find_in_path(program: &str, search: Option<&std::ffi::OsStr>) -> Option<PathBuf> {
    let path = search
        .map(ToOwned::to_owned)
        .or_else(|| std::env::var_os("PATH"))?;
    let suffixes = executable_suffixes();
    std::env::split_paths(&path).find_map(|dir| find_with_suffixes(program, &dir, &suffixes))
}

/// `program` in the single directory `dir`, which is not parsed as a `PATH`
/// list, so a `:` in its name stays part of the name.
pub(crate) fn find_in_dir(program: &str, dir: &Path) -> Option<PathBuf> {
    find_with_suffixes(program, dir, &executable_suffixes())
}

fn find_with_suffixes(program: &str, dir: &Path, suffixes: &[String]) -> Option<PathBuf> {
    // A name that already ends in a runnable suffix (`desktop.exe`) is tried as
    // written before any suffix is appended.
    let lower = program.to_ascii_lowercase();
    let as_written = suffixes
        .iter()
        .any(|ext| !ext.is_empty() && lower.ends_with(ext.as_str()));
    let written = as_written.then(|| dir.join(program));
    written
        .into_iter()
        .chain(
            suffixes
                .iter()
                .map(|ext| dir.join(format!("{program}{ext}"))),
        )
        .find(|p| p.is_file())
}

/// `program` from a trusted directory only (see [`crate::trusted_path`]). The
/// resolved path is what runs, so a link cannot be repointed after the check.
fn resolve_helper(
    program: &str,
    search: Option<&std::ffi::OsStr>,
    project_root: Option<&Path>,
) -> Result<PathBuf, OciError> {
    let Some(project) = project_root else {
        return Err(OciError::HelperProjectUnknown(program.to_owned()));
    };
    if let Some(found) = find_trusted(program, search, project) {
        return Ok(found);
    }
    // Not trusted anywhere. Say where it is, if it is anywhere, so the user can
    // tell a refusal from a missing install. This path is shown, never run.
    match find_in_path(program, search) {
        Some(seen) => {
            let seen = std::fs::canonicalize(&seen).unwrap_or(seen);
            let dir = seen.parent().unwrap_or(&seen);
            let project = std::fs::canonicalize(project).unwrap_or_else(|_| project.to_owned());
            Err(OciError::HelperUntrusted {
                program: program.to_owned(),
                dir: slopvac_fs::display_under_root(dir, &project),
            })
        }
        None => Err(OciError::Credential(
            crate::messages::transport::TransportText::OciHelperMissing {
                program: program.to_owned(),
            }
            .to_string(),
        )),
    }
}

#[expect(
    clippy::too_many_lines,
    reason = "the catalog calls take more lines than the former literals; the body is unchanged"
)]
fn run_helper(
    name: &str,
    registry: &str,
    search: Option<&std::ffi::OsStr>,
    project_root: Option<&Path>,
    timeout: Duration,
) -> Result<Option<Credential>, OciError> {
    let cred = |m: String| OciError::Credential(m);
    if !safe_helper_name(name) {
        return Err(cred(
            crate::messages::transport::TransportText::OciHelperName {
                name: name.to_owned(),
            }
            .to_string(),
        ));
    }
    if !safe_registry_name(registry) {
        return Err(cred(
            crate::messages::transport::TransportPhrase::OciRegistryUnsafe
                .as_static()
                .into(),
        ));
    }
    let program = format!("docker-credential-{name}");
    let path = resolve_helper(&program, search, project_root)?;
    // One deadline covers the helper's exit and the draining of its output.
    let deadline = Instant::now() + timeout;
    let mut command = Command::new(path);
    command
        .arg("get")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    let mut helper = Contained::spawn(&mut command).map_err(|e| {
        cred(
            crate::messages::transport::TransportText::OciHelperStart {
                program: program.clone(),
                detail: e.to_string(),
            }
            .to_string(),
        )
    })?;
    if let Some(mut stdin) = helper.child_mut().stdin.take() {
        // A helper that never reads is caught by the deadline below.
        let reg = registry.to_owned();
        std::thread::spawn(move || {
            let _ = stdin.write_all(reg.as_bytes());
        });
    }
    let Some(mut stdout) = helper.child_mut().stdout.take() else {
        helper.kill_tree();
        return Err(cred(
            crate::messages::transport::TransportPhrase::OciHelperStdout
                .as_static()
                .into(),
        ));
    };
    let (tx, rx) = std::sync::mpsc::channel();
    // The reader ends at end-of-file or after one byte past the cap. Killing the
    // helper's whole tree closes every write end, so it never outlives a lookup.
    std::thread::spawn(move || {
        let mut buf = Vec::new();
        let _ = (&mut stdout)
            .take(HELPER_MAX_OUTPUT as u64 + 1)
            .read_to_end(&mut buf);
        let _ = tx.send(buf);
    });
    let mut exited = false;
    let mut output = None;
    while !exited || output.is_none() {
        if !exited {
            exited = match helper.has_exited() {
                Ok(done) => done,
                Err(e) => {
                    helper.kill_tree();
                    return Err(cred(
                        crate::messages::transport::TransportText::OciHelperWait {
                            program: program.clone(),
                            detail: e.to_string(),
                        }
                        .to_string(),
                    ));
                }
            };
        }
        if output.is_none() {
            match rx.try_recv() {
                Ok(buf) if buf.len() > HELPER_MAX_OUTPUT => {
                    helper.kill_tree();
                    return Err(cred(
                        crate::messages::transport::TransportText::OciHelperOutput {
                            program: program.clone(),
                            limit: HELPER_MAX_OUTPUT,
                        }
                        .to_string(),
                    ));
                }
                Ok(buf) => output = Some(buf),
                Err(std::sync::mpsc::TryRecvError::Empty) => {}
                Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                    helper.kill_tree();
                    return Err(cred(
                        crate::messages::transport::TransportPhrase::OciHelperReader
                            .as_static()
                            .into(),
                    ));
                }
            }
        }
        if exited && output.is_some() {
            break;
        }
        if Instant::now() >= deadline {
            helper.kill_tree();
            return Err(cred(
                crate::messages::transport::TransportText::OciHelperTimeout {
                    program: program.clone(),
                }
                .to_string(),
            ));
        }
        std::thread::sleep(Duration::from_millis(10));
    }
    let Some(out) = output else {
        return Err(cred(
            crate::messages::transport::TransportPhrase::OciHelperUnfinished
                .as_static()
                .into(),
        ));
    };
    let status = helper.reap().map_err(|e| {
        cred(
            crate::messages::transport::TransportText::OciHelperWait {
                program: program.clone(),
                detail: e.to_string(),
            }
            .to_string(),
        )
    })?;
    if !status.success() {
        // "credentials not found in native keychain" is a normal miss.
        return Ok(None);
    }
    let reply: HelperReply = serde_json::from_slice(&out).map_err(|_| {
        cred(
            crate::messages::transport::TransportText::OciHelperJson {
                program: program.clone(),
            }
            .to_string(),
        )
    })?;
    if reply.username == "<token>" {
        return Err(cred(
            crate::messages::transport::TransportPhrase::OciHelperIdentityToken
                .as_static()
                .into(),
        ));
    }
    Ok(Some(Credential {
        username: reply.username,
        secret: reply.secret,
    }))
}

/// Read a Docker-format config. `Ok(None)` when the file cannot be opened.
fn read_config(file: &Path, what: &str) -> Result<Option<DockerConfig>, OciError> {
    let Ok(f) = std::fs::File::open(file) else {
        return Ok(None);
    };
    let mut raw = Vec::new();
    f.take(MAX_CONFIG_BYTES + 1)
        .read_to_end(&mut raw)
        .map_err(|e| {
            OciError::Credential(
                crate::messages::transport::TransportText::OciConfigRead {
                    what: what.to_owned(),
                    detail: e.to_string(),
                }
                .to_string(),
            )
        })?;
    if raw.len() as u64 > MAX_CONFIG_BYTES {
        return Err(OciError::Credential(
            crate::messages::transport::TransportText::OciConfigSize {
                what: what.to_owned(),
            }
            .to_string(),
        ));
    }
    serde_json::from_slice(&raw).map(Some).map_err(|_| {
        OciError::Credential(
            crate::messages::transport::TransportText::OciConfigJson {
                what: what.to_owned(),
            }
            .to_string(),
        )
    })
}

/// The static login `cfg` holds for `registry`, if any.
fn static_login(cfg: &DockerConfig, registry: &str) -> Result<Option<Credential>, OciError> {
    let entry = unique_match(
        cfg.auths
            .iter()
            .filter(|(k, _)| auth_key_host(k).eq_ignore_ascii_case(registry))
            .map(|(_, v)| v),
        "auths",
        registry,
    )?;
    let Some(entry) = entry else {
        return Ok(None);
    };
    if let Some(auth) = &entry.auth {
        let decoded = base64::engine::general_purpose::STANDARD
            .decode(auth.trim())
            .ok()
            .and_then(|b| String::from_utf8(b).ok())
            .ok_or_else(|| {
                OciError::Credential(
                    crate::messages::transport::TransportPhrase::OciAuthBase64
                        .as_static()
                        .into(),
                )
            })?;
        let (u, p) = decoded.split_once(':').ok_or_else(|| {
            OciError::Credential(
                crate::messages::transport::TransportPhrase::OciAuthColon
                    .as_static()
                    .into(),
            )
        })?;
        return Ok(Some(Credential {
            username: u.to_owned(),
            secret: p.to_owned(),
        }));
    }
    Ok(match (&entry.username, &entry.password) {
        (Some(u), Some(p)) => Some(Credential {
            username: u.clone(),
            secret: p.clone(),
        }),
        _ => None,
    })
}

impl DefaultCredentials {
    fn docker_config(&self) -> Result<Option<DockerConfig>, OciError> {
        match &self.docker_config_dir {
            Some(dir) => read_config(
                &dir.join("config.json"),
                crate::messages::transport::TransportPhrase::OciDockerConfig.as_static(),
            ),
            None => Ok(None),
        }
    }

    /// Static `auths` from the first auth file that exists.
    fn auth_file_credential(&self, registry: &str) -> Result<Option<Credential>, OciError> {
        let Some(file) = self.auth_files.iter().find(|f| f.is_file()) else {
            return Ok(None);
        };
        match read_config(
            file,
            crate::messages::transport::TransportPhrase::OciRegistryAuthFile.as_static(),
        )? {
            Some(cfg) => static_login(&cfg, registry),
            None => Ok(None),
        }
    }

    /// The helper `cfg` names for `registry`, run.
    fn helper_credential(
        &self,
        cfg: &DockerConfig,
        registry: &str,
    ) -> Result<Option<Credential>, OciError> {
        let helper = unique_match(
            cfg.cred_helpers
                .iter()
                .filter(|(k, _)| k.eq_ignore_ascii_case(registry))
                .map(|(_, v)| v),
            "credHelpers",
            registry,
        )?
        .or(cfg.creds_store.as_ref());
        match helper {
            Some(name) => run_helper(
                name,
                registry,
                self.helper_search_path.as_deref(),
                self.project_root.as_deref(),
                self.helper_timeout.unwrap_or(HELPER_TIMEOUT),
            ),
            None => Ok(None),
        }
    }
}

impl CredentialSource for DefaultCredentials {
    fn credential(&self, registry: &str) -> Result<Option<Credential>, OciError> {
        let e = &self.env;
        if let (Some(u), Some(t)) = (&e.user, &e.token) {
            return Ok(Some(Credential {
                username: u.clone(),
                secret: t.clone(),
            }));
        }
        if registry.eq_ignore_ascii_case("ghcr.io")
            && let Some(t) = &e.github_token
        {
            return Ok(Some(Credential {
                username: "slopvac".into(),
                secret: t.clone(),
            }));
        }
        let docker = self.docker_config()?;
        if let Some(cfg) = &docker
            && let Some(c) = static_login(cfg, registry)?
        {
            return Ok(Some(c));
        }
        if let Some(c) = self.auth_file_credential(registry)? {
            return Ok(Some(c));
        }
        match &docker {
            Some(cfg) => self.helper_credential(cfg, registry),
            None => Ok(None),
        }
    }
}

/// A parsed `WWW-Authenticate` challenge.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Challenge {
    /// Lowercased scheme: `bearer` or `basic`.
    pub scheme: String,
    /// Parameters with lowercased names.
    pub params: Vec<(String, String)>,
}

impl Challenge {
    /// A parameter by name.
    #[must_use]
    pub fn param(&self, name: &str) -> Option<&str> {
        self.params
            .iter()
            .find(|(k, _)| k == name)
            .map(|(_, v)| v.as_str())
    }

    /// Parse the first challenge of a header value. Quoted strings may hold commas
    /// and backslash escapes.
    #[must_use]
    pub fn parse(header: &str) -> Option<Self> {
        let header = header.trim();
        let (scheme, mut rest) = header
            .split_once(char::is_whitespace)
            .unwrap_or((header, ""));
        if scheme.is_empty() {
            return None;
        }
        let mut params = Vec::new();
        loop {
            rest = rest.trim_start_matches([' ', '\t', ',']);
            if rest.is_empty() {
                break;
            }
            let eq = rest.find('=')?;
            let name = rest[..eq].trim().to_ascii_lowercase();
            // RFC 9110 allows optional whitespace around `=`.
            rest = rest[eq + 1..].trim_start_matches([' ', '\t']);
            let value;
            if let Some(q) = rest.strip_prefix('"') {
                let mut out = String::new();
                let mut chars = q.char_indices();
                let mut end = None;
                while let Some((i, c)) = chars.next() {
                    match c {
                        '\\' => {
                            if let Some((_, n)) = chars.next() {
                                out.push(n);
                            }
                        }
                        '"' => {
                            end = Some(i + 1);
                            break;
                        }
                        _ => out.push(c),
                    }
                }
                rest = &q[end?..];
                value = out;
            } else {
                let stop = rest.find(',').unwrap_or(rest.len());
                value = rest[..stop].trim().to_owned();
                rest = &rest[stop..];
            }
            params.push((name, value));
        }
        Some(Self {
            scheme: scheme.to_ascii_lowercase(),
            params,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_a_bearer_challenge_with_quoted_commas() {
        let c = Challenge::parse(
            r#"Bearer realm="https://ghcr.io/token",service="ghcr.io",scope="repository:a/b:pull,push""#,
        )
        .unwrap();
        assert_eq!(c.scheme, "bearer");
        assert_eq!(c.param("realm"), Some("https://ghcr.io/token"));
        assert_eq!(c.param("scope"), Some("repository:a/b:pull,push"));
    }

    #[test]
    fn parses_unquoted_values_escapes_and_basic() {
        let c = Challenge::parse(r#"Basic realm="a \"b\"", charset=UTF-8"#).unwrap();
        assert_eq!(c.scheme, "basic");
        assert_eq!(c.param("realm"), Some(r#"a "b""#));
        assert_eq!(c.param("charset"), Some("UTF-8"));
        assert!(Challenge::parse("").is_none());
        assert!(Challenge::parse(r#"Bearer realm="unterminated"#).is_none());
    }

    #[test]
    fn challenge_parameters_may_have_whitespace_around_the_equals_sign() {
        let c = Challenge::parse(r#"Bearer realm = "https://r.example/token" , service= "reg""#)
            .unwrap();
        assert_eq!(c.param("realm"), Some("https://r.example/token"));
        assert_eq!(c.param("service"), Some("reg"));
    }

    #[test]
    fn helper_names_must_be_plain() {
        for ok in ["osxkeychain", "pass", "ecr-login", "desktop.exe", "a_b"] {
            assert!(safe_helper_name(ok), "{ok}");
        }
        for bad in [
            "",
            "../x",
            "a/b",
            "a;b",
            "a b",
            "-x",
            ".x",
            "A",
            "a\0",
            &"a".repeat(65),
        ] {
            assert!(!safe_helper_name(bad), "{bad:?}");
        }
    }

    #[test]
    fn registry_names_for_helpers_are_hosts() {
        assert!(safe_registry_name("ghcr.io"));
        assert!(safe_registry_name("localhost:5000"));
        for bad in ["", "a b", "a\n", "a/b", "a;b", "$(x)"] {
            assert!(!safe_registry_name(bad), "{bad:?}");
        }
    }

    #[test]
    fn debug_never_prints_the_secret() {
        let c = Credential {
            username: "u".into(),
            secret: "hunter2".into(),
        };
        assert!(!format!("{c:?}").contains("hunter2"));
        let e = EnvCredentials {
            github_token: Some("ghp_secret".into()),
            ..EnvCredentials::default()
        };
        assert!(!format!("{e:?}").contains("ghp_secret"));
    }

    #[test]
    fn env_precedence_and_github_token_scope() {
        let creds = DefaultCredentials {
            env: EnvCredentials {
                github_token: Some("t".into()),
                ..EnvCredentials::default()
            },
            ..DefaultCredentials::default()
        };
        assert!(creds.credential("ghcr.io").unwrap().is_some());
        assert!(
            creds.credential("registry.example").unwrap().is_none(),
            "GITHUB_TOKEN must stay on ghcr.io"
        );
        let both = DefaultCredentials {
            env: EnvCredentials {
                user: Some("me".into()),
                token: Some("s".into()),
                github_token: Some("t".into()),
            },
            ..DefaultCredentials::default()
        };
        assert_eq!(both.credential("ghcr.io").unwrap().unwrap().username, "me");
    }
}
