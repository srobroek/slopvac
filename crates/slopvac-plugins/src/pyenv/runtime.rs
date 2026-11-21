//! The `[plugin]` fields of the pack manifest that select a managed Python
//! environment (`runtime`, `python`, `command`, `args`).
//!
//! This reads only what the environment needs. The pack loader owns full
//! manifest validation; the manifest bytes are part of the trust hash, so an
//! edit here changes nothing without a new trust decision.

use std::fs::{self, File};
use std::io;
use std::path::{Path, PathBuf};

use serde::Deserialize;
use slopvac_fs::read_capped;
use slopvac_sanitize::line as esc;

use super::{ManagedEnv, PyEnvError};
use crate::messages::pyenv::{self as messages, PyenvPhrase, PyenvText};

/// File name of the manifest at the root of a pack.
pub const MANIFEST_FILE: &str = "slopvac-plugin.toml";

const MAX_MANIFEST_BYTES: u64 = 1 << 20;

/// Why a manifest cannot select a managed Python environment.
///
/// The variants hold raw text. `Display` escapes it once with
/// [`slopvac_sanitize::line`] (the sanitizing exception to derived `Display`),
/// and [`RuntimeError::unescaped`] gives the text before escaping, for a
/// caller that builds a larger message and escapes it once.
#[derive(Debug, thiserror::Error)]
pub enum RuntimeError {
    /// The manifest is not a regular file (a symlink, a directory).
    NotRegular,
    /// The manifest cannot be examined or opened.
    Io(#[source] io::Error),
    /// The manifest cannot be read, or holds more than 1 MiB.
    Read(#[source] Box<slopvac_fs::Error>),
    /// The manifest is not UTF-8 text.
    NotUtf8(#[source] std::str::Utf8Error),
    /// The manifest is not valid TOML for the fields read here.
    Toml(#[source] TomlCause),
    /// `python` is set without `runtime = "python"`.
    PythonWithoutRuntime,
    /// `runtime = "python"` in a pack that is not `kind = "code"`.
    RuntimeNeedsCodeKind,
    /// `runtime = "python"` without this field.
    MissingField(&'static str),
    /// The `python` value is not a plain version request.
    NotARequest,
    /// The `command` value is not a relative script path inside the pack.
    NotAScript,
    /// The `runtime` value is neither `native` nor `python`.
    UnknownRuntime,
    /// A requirement has a pre-release suffix, which PEP 440 cannot express.
    PreRelease,
    /// A comparator is not a version of one to three numbers.
    BadVersion,
    /// A number does not fit in 64 bits.
    NumberTooLarge,
    /// The translated requirement is over 64 bytes.
    TooLong,
}

/// Where a manifest failed to parse, and nothing else.
///
/// The TOML error prints the offending source line, which is manifest text and may hold
/// terminal controls. The cause keeps only the position, the same scrub as the
/// `slopvac-fs` errors (docs/engineering.md, approved departures).
#[derive(Debug, Clone, Copy, PartialEq, Eq, thiserror::Error)]
#[error("{}", messages::toml_syntax(*.line, *.column))]
pub struct TomlCause {
    /// One-based line.
    pub line: usize,
    /// One-based column, in characters.
    pub column: usize,
}

impl TomlCause {
    fn new(text: &str, e: &toml::de::Error) -> Self {
        let at = e.span().map_or(0, |r| r.start).min(text.len());
        let before = text.get(..at).unwrap_or_default();
        let line = before.matches('\n').count() + 1;
        let column = before.rsplit('\n').next().map_or(0, |l| l.chars().count()) + 1;
        Self { line, column }
    }
}

/// Result of reading or translating the manifest fields.
pub type RuntimeResult<T> = std::result::Result<T, RuntimeError>;

impl RuntimeError {
    /// The message as built, before escaping. Do not print it.
    #[must_use]
    pub fn unescaped(&self) -> String {
        match self {
            Self::NotRegular => PyenvPhrase::ManifestNotRegular.as_static().into(),
            Self::Io(e) => e.to_string(),
            Self::Read(e) if matches!(**e, slopvac_fs::Error::CapExceeded { .. }) => {
                PyenvPhrase::ManifestTooLarge.as_static().into()
            }
            Self::Read(e) => e.to_string(),
            Self::NotUtf8(e) => e.to_string(),
            Self::Toml(c) => PyenvText::TomlAt {
                line: c.line,
                column: c.column,
            }
            .to_string(),
            Self::PythonWithoutRuntime => PyenvPhrase::PythonWithoutRuntime.as_static().into(),
            Self::RuntimeNeedsCodeKind => PyenvPhrase::RuntimeNeedsCodeKind.as_static().into(),
            Self::MissingField(f) => PyenvText::MissingField {
                field: (*f).to_owned(),
            }
            .to_string(),
            Self::NotARequest => PyenvPhrase::PythonNotARequest.as_static().into(),
            Self::NotAScript => PyenvPhrase::CommandNotAScript.as_static().into(),
            Self::UnknownRuntime => PyenvPhrase::UnknownRuntime.as_static().into(),
            Self::PreRelease => PyenvPhrase::PreRelease.as_static().into(),
            Self::BadVersion => PyenvPhrase::BadVersion.as_static().into(),
            Self::NumberTooLarge => PyenvPhrase::NumberTooLarge.as_static().into(),
            Self::TooLong => PyenvPhrase::RequestTooLong.as_static().into(),
        }
    }
}

impl std::fmt::Display for RuntimeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&esc(&self.unescaped()))
    }
}

#[derive(Debug, Deserialize)]
struct Manifest {
    kind: Option<String>,
    plugin: Option<PluginTable>,
}

#[derive(Debug, Default, Deserialize)]
struct PluginTable {
    runtime: Option<String>,
    python: Option<String>,
    command: Option<String>,
    #[serde(default)]
    args: Vec<String>,
}

/// A plugin that runs in a managed Python environment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PythonRuntime {
    /// The interpreter request as a PEP 440 specifier set that uv takes, for
    /// example `3.12` or `>=3.12,<4` (see [`pep440_specifier`]). The environment
    /// store keys on this value.
    pub python: String,
    /// The script to run, relative to the plugin tree.
    pub command: String,
    /// Arguments after the script.
    pub args: Vec<String>,
}

impl PythonRuntime {
    /// The runtime the manifest at the root of `root` selects, or `None` for a
    /// tree without a manifest, a data pack and a native plugin.
    ///
    /// # Errors
    /// [`PyEnvError::Manifest`] with a [`RuntimeError`] source, for
    /// `runtime = "python"` without a valid `python` request or `command`,
    /// for `python` without that runtime, for an unknown runtime, and for a
    /// manifest that is too large, not a regular file or not TOML.
    pub fn read(root: &Path) -> std::result::Result<Option<Self>, PyEnvError> {
        let path = root.join(MANIFEST_FILE);
        Self::read_manifest(&path).map_err(|source| PyEnvError::Manifest { path, source })
    }

    fn read_manifest(path: &Path) -> RuntimeResult<Option<Self>> {
        let meta = match fs::symlink_metadata(path) {
            Ok(m) => m,
            Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
            Err(e) => return Err(RuntimeError::Io(e)),
        };
        if !meta.is_file() {
            return Err(RuntimeError::NotRegular);
        }
        let bytes = read_capped(
            File::open(path).map_err(RuntimeError::Io)?,
            MAX_MANIFEST_BYTES,
        )
        .map_err(|e| RuntimeError::Read(Box::new(e)))?;
        let text = std::str::from_utf8(&bytes).map_err(RuntimeError::NotUtf8)?;
        let manifest: Manifest =
            toml::from_str(text).map_err(|e| RuntimeError::Toml(TomlCause::new(text, &e)))?;
        let Some(plugin) = manifest.plugin else {
            return Ok(None);
        };
        match plugin.runtime.as_deref() {
            None | Some("native") => {
                if plugin.python.is_some() {
                    return Err(RuntimeError::PythonWithoutRuntime);
                }
                Ok(None)
            }
            Some("python") => {
                if manifest.kind.as_deref() != Some("code") {
                    return Err(RuntimeError::RuntimeNeedsCodeKind);
                }
                let python = plugin.python.ok_or(RuntimeError::MissingField("python"))?;
                if !super::is_python_request(&python) {
                    return Err(RuntimeError::NotARequest);
                }
                let python = pep440_specifier(&python)?;
                if !super::is_python_request(&python) {
                    return Err(RuntimeError::NotARequest);
                }
                let command = plugin
                    .command
                    .ok_or(RuntimeError::MissingField("command"))?;
                if !is_script_path(&command) {
                    return Err(RuntimeError::NotAScript);
                }
                Ok(Some(Self {
                    python,
                    command,
                    args: plugin.args,
                }))
            }
            Some(_) => Err(RuntimeError::UnknownRuntime),
        }
    }

    /// The program and arguments of the plugin spec: the environment's
    /// interpreter, then [`super::PYTHON_FLAGS`], the script and its
    /// arguments. The script path is relative; the plugin runs from its tree.
    #[must_use]
    pub fn launch(&self, env: &ManagedEnv) -> (PathBuf, Vec<String>) {
        let rest: Vec<String> = std::iter::once(self.command.clone())
            .chain(self.args.iter().cloned())
            .collect();
        (env.python(), env.args(&rest))
    }
}

/// What the `PackPath` def of the plugin-manifest schema accepts, minus a
/// leading dash (the interpreter would read it as an option): relative,
/// forward slashes, no drive letter, no `..` segment. A NUL cannot reach an
/// argument list, so it is refused as well.
fn is_script_path(command: &str) -> bool {
    let drive =
        command.as_bytes().get(1) == Some(&b':') && command.as_bytes()[0].is_ascii_alphabetic();
    !command.is_empty()
        && !command.starts_with(['-', '/', '\\'])
        && !drive
        && !command.contains(['\\', '\0'])
        && !command.split('/').any(|s| s == "..")
}

/// Translate a `python` value of the manifest (the `VersionReq` def of the
/// plugin-manifest schema, semver rules) into the PEP 440 specifier set that uv
/// takes as `--python`.
///
/// The grammar is comma-separated comparators, each an optional operator
/// (`^ ~ = >= <= > <`) and a version of one to three numeric parts, with an
/// optional `-` pre-release suffix. Rules, with semver's partial-version
/// meaning:
///
/// | Manifest | PEP 440 |
/// | --- | --- |
/// | `3.12`, `3.12.4` alone | unchanged (uv reads `3.12` as any 3.12.x) |
/// | `=3.12`, `=3`, `=3.12.4` | `==3.12.*`, `==3.*`, `==3.12.4` |
/// | `^3.12`, `^3`, `^0.2.3`, `^0.0.3` | `>=3.12,<4`, `>=3,<4`, `>=0.2.3,<0.3`, `>=0.0.3,<0.0.4` |
/// | `~3.12`, `~3.12.4`, `~3` | `>=3.12,<3.13`, `>=3.12.4,<3.13`, `>=3,<4` |
/// | `>=3.12`, `<3.13` | unchanged |
/// | `>3.12`, `>3`, `>3.12.4` | `>=3.13`, `>=4`, `>3.12.4` |
/// | `<=3.12`, `<=3`, `<=3.12.4` | `<3.13`, `<4`, `<=3.12.4` |
///
/// In a list, a bare version means `=`. Comma-separated parts join with `,`.
///
/// # Errors
/// [`RuntimeError`] naming the value, for a pre-release suffix (PEP 440
/// interpreter requests cannot express it), a part that is not a number, a
/// list entry that is empty, a number too large, or a result over 64 bytes.
pub fn pep440_specifier(req: &str) -> RuntimeResult<String> {
    let parts: Vec<&str> = req.split(',').map(str::trim).collect();
    if let [only] = parts[..]
        && let Ok((None, _)) = comparator(only)
    {
        return Ok(only.to_owned());
    }
    let mut out = Vec::new();
    for part in &parts {
        let (op, v) = comparator(part)?;
        out.extend(clauses(op.unwrap_or("="), &v)?);
    }
    let joined = out.join(",");
    if joined.len() > 64 {
        return Err(RuntimeError::TooLong);
    }
    Ok(joined)
}

fn comparator(part: &str) -> RuntimeResult<(Option<&'static str>, Vec<u64>)> {
    let (op, rest) = ["<=", ">=", "^", "~", "=", ">", "<"]
        .iter()
        .find_map(|o| part.strip_prefix(o).map(|r| (Some(*o), r)))
        .unwrap_or((None, part));
    let rest = rest.trim();
    if rest.contains('-') {
        return Err(RuntimeError::PreRelease);
    }
    let nums: Vec<u64> = rest
        .split('.')
        .map(|n| {
            if n.is_empty() || !n.bytes().all(|b| b.is_ascii_digit()) {
                return Err(RuntimeError::BadVersion);
            }
            n.parse().map_err(|_| RuntimeError::NumberTooLarge)
        })
        .collect::<RuntimeResult<_>>()?;
    if nums.is_empty() || nums.len() > 3 {
        return Err(RuntimeError::BadVersion);
    }
    Ok((op, nums))
}

fn dotted(v: &[u64]) -> String {
    v.iter().map(u64::to_string).collect::<Vec<_>>().join(".")
}

/// `v` with the number at `idx` raised by one and the later parts dropped.
fn bumped(v: &[u64], idx: usize) -> RuntimeResult<String> {
    let mut head = v[..=idx].to_vec();
    head[idx] = head[idx]
        .checked_add(1)
        .ok_or(RuntimeError::NumberTooLarge)?;
    Ok(dotted(&head))
}

fn clauses(op: &str, v: &[u64]) -> RuntimeResult<Vec<String>> {
    let n = v.len();
    let ver = dotted(v);
    let bump = |idx| bumped(v, idx);
    Ok(match op {
        "=" if n == 3 => vec![format!("=={ver}")],
        "=" => vec![format!("=={ver}.*")],
        ">=" | "<" => vec![format!("{op}{ver}")],
        ">" if n == 3 => vec![format!(">{ver}")],
        ">" => vec![format!(">={}", bump(n - 1)?)],
        "<=" if n == 3 => vec![format!("<={ver}")],
        "<=" => vec![format!("<{}", bump(n - 1)?)],
        "~" => vec![
            format!(">={ver}"),
            format!("<{}", bump(usize::from(n > 1))?),
        ],
        // "^": the leftmost non-zero number stays; a trailing all-zero version
        // keeps its last given number.
        _ => {
            let idx = v
                .iter()
                .position(|x| *x != 0)
                .map_or(n - 1, |i| i.min(n - 1));
            vec![format!(">={ver}"), format!("<{}", bump(idx)?)]
        }
    })
}
