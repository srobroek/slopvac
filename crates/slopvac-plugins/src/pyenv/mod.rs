//! Managed Python environments for plugins (threat model section 6.6, Y1 to Y7).
//!
//! A Python plugin ships a PEP 751 lock, `pylock.toml`, at the root of its
//! signed tree, and every locked package as a wheel inside the tree. The host
//! builds one environment per tree with uv and runs the plugin as
//! `<env>/bin/python -I -B ...` ([`PYTHON_FLAGS`]).
//!
//! Windows is refused for now ([`PyEnvError::UnsupportedPlatform`]): the
//! build, [`EnvStore::load`] and both checks return that error there. 3.0
//! ships no native Windows support.
//!
//! # Wiring
//!
//! The pack manifest selects an environment with `runtime = "python"` and a
//! `python` request in its `[plugin]` table ([`PythonRuntime::read`]).
//! [`crate::sync::Syncer::with_python`] builds the environment after it
//! extracts the pack (offline when the sync is offline),
//! [`crate::sync::status_with_python`] runs [`ManagedEnv::verify_full`] for
//! `plugins status` and `doctor`, and
//! [`crate::trust::TrustGate::with_python_plugins`] wires the environment into
//! the spawn gate.
//!
//! # Build
//!
//! [`EnvStore::build`] checks the lock first ([`PyLock`]): every package must
//! be a wheel in the tree whose sha256 matches, so a source-only dependency is
//! refused before any installer runs (Y1). uv then runs twice, with an empty
//! environment except `UV_PYTHON_INSTALL_DIR`, with `--no-config` and outside
//! any project (Y3):
//!
//! 1. `uv venv --managed-python --python <request> --relocatable`, which uses
//!    only a uv-managed interpreter, never one on `PATH` (Y6). Offline it adds
//!    `--offline --no-python-downloads`.
//! 2. `uv pip install --offline --no-index --find-links <wheel dirs>
//!    --no-build --no-deps --require-hashes --link-mode copy
//!    -r <requirements>`. The requirements file pins each package to its
//!    exact version and locked hashes, so no resolver picks anything, and no
//!    build backend can run.
//!
//! The build then compiles bytecode and probes the interpreter, both with
//! `-I -S`, so no `.pth` file or `sitecustomize` from a wheel runs before the
//! user trusts the plugin. Before each of those runs it checks that the
//! interpreter and `pyvenv.cfg` are still what `uv venv` made, so a wheel that
//! overwrote them stops the build. uv's own `--compile-bytecode` starts the
//! interpreter with `site` enabled, so the build does not use it. The build
//! records the interpreter identity (version, build and the sha256 of each
//! executable), makes the environment read-only, lists every entry with its
//! size, modification time and sha256, and moves the environment into place.
//! The record sits beside it in `<key>.json`.
//!
//! # Trust and verification (Y5)
//!
//! The interpreter identity and a digest of the lock and the content listing
//! fill the `interpreter` and `environment` slots of the trust hash
//! ([`crate::trust::TrustGate::with_managed_python`]). Times are not in the
//! hash.
//!
//! The spawn gate runs [`ManagedEnv::check_quick`] before every spawn: it
//! walks the environment and compares paths, kinds, sizes, modification times,
//! executable bits and link targets with the record, and the interpreter's
//! size and modification time. It hashes nothing. [`ManagedEnv::verify_full`]
//! hashes every file and the interpreter. `plugins trust` runs it
//! ([`crate::trust::TrustGate::record_trust`]), and it is the check for
//! `plugins status` and `doctor`. An edit that keeps the size and restores the
//! modification time passes the quick check and fails the full one. Writing
//! the environment needs the user's own rights, so that gap is residual risk
//! R6.

mod listing;
mod lock;
mod runtime;

use std::fs::{self, File, OpenOptions};
use std::io::{self, Read as _, Write as _};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use serde_json::json;
use slopvac_sanitize::{line as esc, terminal};

pub use lock::{LockedPackage, LockedWheel, PyLock};
pub use runtime::{
    MANIFEST_FILE, PythonRuntime, RuntimeError, RuntimeResult, TomlCause, pep440_specifier,
};

use crate::extract::{Evicted, ExtractError, TreeHash, evict, verify_tree};
use crate::messages::pyenv::{self as messages, PyenvPhrase, PyenvText};
use crate::oci::Digest;
use crate::sign::canonical_json;
use listing::{
    Entry, WalkBounds, compare, digest_input, make_read_only, mtime_of, scan, sha256_file,
};

/// Name of the lock at the root of a Python plugin tree.
pub const LOCK_FILE: &str = "pylock.toml";

/// Interpreter flags every managed plugin runs with: `-I` (isolated: no
/// `PYTHON*` variables, user site or script directory on `sys.path`) and `-B`
/// (write no bytecode into the read-only environment).
pub const PYTHON_FLAGS: [&str; 2] = ["-I", "-B"];

const RECORD_SCHEMA: u32 = 1;
const MAX_RECORD_BYTES: u64 = 64 << 20;
const MAX_PROBE_BYTES: u64 = 64 << 10;
/// How long one uv or probe run may take, downloads included.
const STEP_DEADLINE: Duration = Duration::from_secs(600);

const PROBE: &str = "import json, platform, sys\n\
print(json.dumps({'version': sys.version, 'hexversion': sys.hexversion, \
'implementation': sys.implementation.name, 'cache_tag': sys.implementation.cache_tag, \
'base_executable': getattr(sys, '_base_executable', None) or sys.executable, \
'platform': sys.platform, 'machine': platform.machine()}))";

/// Errors from building or checking a managed environment.
///
/// The variants hold raw text: package names, paths and installer output are
/// untrusted. `Display` escapes them once with `slopvac-sanitize` (installer
/// output with [`slopvac_sanitize::terminal`], everything else with
/// [`slopvac_sanitize::line()`]). [`PyEnvError::unescaped`] gives the message
/// before escaping, for a caller that builds a larger message and escapes it
/// once.
#[derive(Debug)]
pub enum PyEnvError {
    /// The lock is malformed.
    Lock(String),
    /// A package is not a wheel inside the artifact (Y1).
    SourceOnly {
        /// The package.
        package: String,
        /// What the lock offers instead.
        source_kind: String,
    },
    /// A locked wheel is missing, misnamed or does not match its hash.
    Wheel {
        /// The package.
        package: String,
        /// What is wrong.
        why: String,
    },
    /// The `[plugin]` table of the pack manifest cannot select an environment.
    Manifest {
        /// The manifest file. Messages show it redacted.
        path: PathBuf,
        /// What is wrong.
        source: RuntimeError,
    },
    /// No environment is built for the plugin tree.
    EnvMissing {
        /// The plugin.
        plugin: String,
        /// The interpreter request.
        python: String,
    },
    /// The installer setup is unusable.
    Installer(String),
    /// Offline, and no managed interpreter matches the request.
    OfflinePythonMissing(String),
    /// A uv or interpreter run failed.
    Step {
        /// What ran.
        step: String,
        /// Exit status or reason.
        status: String,
        /// The end of its error output, raw.
        output: String,
    },
    /// The environment changed after its build (Y5).
    Changed {
        /// The entry, relative to the environment, or the interpreter path.
        path: String,
        /// What changed.
        why: String,
    },
    /// The environment holds something it may not, or passes a bound.
    Refused(String),
    /// Managed environments are not supported on this platform yet.
    UnsupportedPlatform,
    /// The environment record is damaged.
    Record {
        /// The record file.
        path: PathBuf,
        /// What is wrong.
        why: String,
    },
    /// The plugin tree no longer verifies.
    Tree(ExtractError),
    /// A file system operation failed.
    Io {
        /// The operation.
        what: String,
        /// The cause.
        source: io::Error,
    },
}

impl PyEnvError {
    /// The message as built, before escaping. Do not print it.
    #[must_use]
    pub fn unescaped(&self) -> String {
        match self {
            Self::Lock(m) => PyenvText::LockRefused { detail: m.clone() }.to_string(),
            Self::SourceOnly {
                package,
                source_kind,
            } => PyenvText::SourceOnly {
                package: package.clone(),
                source_kind: source_kind.clone(),
            }
            .to_string(),
            Self::Manifest { path, source } => PyenvText::ManifestUnusable {
                path: slopvac_fs::display_under_root(path, Path::new(".")),
                reason: source.unescaped(),
            }
            .to_string(),
            Self::EnvMissing { plugin, python } => PyenvText::EnvMissing {
                plugin: plugin.clone(),
                python: python.clone(),
            }
            .to_string(),
            Self::Wheel { package, why } => PyenvText::WheelRefused {
                package: package.clone(),
                why: why.clone(),
            }
            .to_string(),
            Self::Installer(m) => PyenvText::InstallerRefused { detail: m.clone() }.to_string(),
            Self::OfflinePythonMissing(r) => {
                PyenvText::OfflinePythonMissing { request: r.clone() }.to_string()
            }
            Self::Step {
                step,
                status,
                output,
            } => PyenvText::StepOutput {
                head: Self::step_head(step, status),
                output: output.clone(),
            }
            .to_string(),
            Self::Changed { path, why } => PyenvText::EnvChanged {
                path: path.clone(),
                why: why.clone(),
            }
            .to_string(),
            Self::Refused(m) => PyenvText::EnvRefused { detail: m.clone() }.to_string(),
            Self::UnsupportedPlatform => PyenvPhrase::UnsupportedPlatform.as_static().into(),
            Self::Record { path, why } => PyenvText::RecordDamaged {
                path: path.to_string_lossy().into_owned(),
                why: why.clone(),
            }
            .to_string(),
            Self::Tree(e) => e.unescaped(),
            Self::Io { what, source } => PyenvText::IoFailed {
                what: what.clone(),
                cause: source.to_string(),
            }
            .to_string(),
        }
    }

    fn step_head(step: &str, status: &str) -> String {
        PyenvText::StepHead {
            step: step.to_owned(),
            status: status.to_owned(),
        }
        .to_string()
    }
}

impl std::fmt::Display for PyEnvError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            // Installer output keeps its lines; everything else stays on one.
            Self::Step {
                step,
                status,
                output,
            } => f.write_str(
                &PyenvText::StepOutput {
                    head: esc(&Self::step_head(step, status)),
                    output: terminal(output),
                }
                .to_string(),
            ),
            _ => f.write_str(&esc(&self.unescaped())),
        }
    }
}

impl std::error::Error for PyEnvError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Tree(e) => Some(e),
            Self::Manifest { source, .. } => Some(source),
            Self::Io { source, .. } => Some(source),
            _ => None,
        }
    }
}

impl From<ExtractError> for PyEnvError {
    fn from(e: ExtractError) -> Self {
        Self::Tree(e)
    }
}

impl PyEnvError {
    fn io(what: impl Into<String>) -> impl FnOnce(io::Error) -> Self {
        let what = what.into();
        move |source| Self::Io { what, source }
    }
}

/// `NotAbsolute` for an installer path.
fn not_absolute(path: &Path) -> String {
    PyenvText::NotAbsolute {
        path: path.display().to_string(),
    }
    .to_string()
}

/// Refuse on Windows: the `Scripts` layout, launcher and read-only handling
/// there have no runtime tests yet (threat model section 6.6).
fn supported_platform() -> Result<(), PyEnvError> {
    if cfg!(windows) {
        return Err(PyEnvError::UnsupportedPlatform);
    }
    Ok(())
}

/// Whether the build may download an interpreter. Wheels never download.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstallNetwork {
    /// Sticky offline mode: only interpreters already installed.
    Offline,
    /// uv may download a managed interpreter into the install directory.
    Online,
}

/// Whether `p` is a plain interpreter request such as `3.12`, `^3.12` or
/// `>=3.11,<3.13`: short, and never an option for uv. Everything the
/// `VersionReq` def of the plugin-manifest schema accepts without whitespace
/// passes.
pub(crate) fn is_python_request(p: &str) -> bool {
    !p.is_empty()
        && p.len() <= 64
        && !p.starts_with('-')
        && p.bytes().all(|b| {
            b.is_ascii_alphanumeric()
                || matches!(
                    b,
                    b'.' | b'@'
                        | b'-'
                        | b'+'
                        | b'='
                        | b'<'
                        | b'>'
                        | b','
                        | b'~'
                        | b'!'
                        | b'^'
                        | b'*'
                )
        })
}

/// How to run uv.
#[derive(Debug, Clone)]
pub struct Installer {
    /// Absolute path of the `uv` binary. Never looked up on `PATH` here.
    pub uv: PathBuf,
    /// Where uv keeps managed interpreters (`UV_PYTHON_INSTALL_DIR`).
    pub python_install_dir: PathBuf,
    /// The interpreter request, for example `3.12`.
    pub python: String,
    /// Network mode.
    pub network: InstallNetwork,
}

impl Installer {
    fn check(&self) -> Result<(), PyEnvError> {
        let refuse = |why: String| Err(PyEnvError::Installer(why));
        if !self.uv.is_absolute() {
            return refuse(not_absolute(&self.uv));
        }
        if !self.python_install_dir.is_absolute() {
            return refuse(not_absolute(&self.python_install_dir));
        }
        if !is_python_request(&self.python) {
            return refuse(
                PyenvText::NotARequest {
                    request: self.python.clone(),
                }
                .to_string(),
            );
        }
        Ok(())
    }

    /// A command for uv with a scrubbed environment (Y3).
    fn uv(&self, cwd: &Path) -> Command {
        let mut cmd = Command::new(&self.uv);
        cmd.env_clear()
            .env("UV_PYTHON_INSTALL_DIR", &self.python_install_dir)
            .current_dir(cwd);
        windows_env(&mut cmd);
        cmd
    }
}

#[cfg(windows)]
fn windows_env(cmd: &mut Command) {
    if let Some(root) = std::env::var_os("SystemRoot") {
        cmd.env("SystemRoot", root);
    }
}

#[cfg(not(windows))]
fn windows_env(_: &mut Command) {}

/// One file that makes up the interpreter.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct InterpFile {
    path: String,
    size: u64,
    mtime: (i64, u32),
    sha256: String,
}

/// What the probe reported, plus the executable files.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Interpreter {
    files: Vec<InterpFile>,
    version: String,
    hexversion: u64,
    implementation: String,
    cache_tag: Option<String>,
    platform: String,
    machine: String,
}

#[derive(Debug, Deserialize)]
struct Probe {
    version: String,
    hexversion: u64,
    implementation: String,
    cache_tag: Option<String>,
    base_executable: String,
    platform: String,
    machine: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct EnvRecord {
    schema_version: u32,
    tree: String,
    python: String,
    lock: String,
    interpreter: Interpreter,
    entries: Vec<Entry>,
}

/// A built environment and its record.
#[derive(Debug, Clone)]
pub struct ManagedEnv {
    root: PathBuf,
    record: EnvRecord,
}

/// The interpreter inside an environment root, as uv lays it out.
fn env_python(root: &Path) -> PathBuf {
    if cfg!(windows) {
        root.join("Scripts").join("python.exe")
    } else {
        root.join("bin").join("python")
    }
}

impl ManagedEnv {
    /// The environment directory.
    #[must_use]
    pub fn root(&self) -> &Path {
        &self.root
    }

    /// The absolute path a plugin spec must use as its program.
    #[must_use]
    pub fn python(&self) -> PathBuf {
        env_python(&self.root)
    }

    /// [`PYTHON_FLAGS`] followed by `rest`: the argument list of a plugin spec.
    #[must_use]
    pub fn args(&self, rest: &[String]) -> Vec<String> {
        PYTHON_FLAGS
            .iter()
            .map(|s| (*s).to_owned())
            .chain(rest.iter().cloned())
            .collect()
    }

    /// The interpreter identity for the trust hash: version, build and the
    /// path, size and sha256 of each executable, as canonical JSON.
    ///
    /// # Panics
    /// Never: canonical JSON is UTF-8.
    #[must_use]
    pub fn interpreter_identity(&self) -> String {
        let i = &self.record.interpreter;
        let files: Vec<_> = i
            .files
            .iter()
            .map(|f| json!([f.path, f.size, f.sha256]))
            .collect();
        let doc = json!({
            "files": files,
            "version": i.version,
            "hexversion": i.hexversion,
            "implementation": i.implementation,
            "cache_tag": i.cache_tag,
            "platform": i.platform,
            "machine": i.machine,
        });
        String::from_utf8(canonical_json(&doc)).expect("canonical JSON is UTF-8")
    }

    /// The digest of the lock, the interpreter request and the content
    /// listing of the environment, for the trust hash.
    #[must_use]
    pub fn environment_digest(&self) -> Digest {
        Digest::of(&canonical_json(&json!({
            "lock": self.record.lock,
            "python": self.record.python,
            "listing": digest_input(&self.record.entries),
        })))
    }

    /// The Y5 spawn check: metadata only, no hashing.
    ///
    /// # Errors
    /// [`PyEnvError::Changed`] for an added, removed or changed entry or
    /// interpreter, [`PyEnvError::Refused`] or [`PyEnvError::Io`] when the
    /// environment cannot be read.
    pub fn check_quick(&self) -> Result<(), PyEnvError> {
        supported_platform()?;
        self.check_interpreter(false)?;
        compare(
            &self.record.entries,
            &scan(&self.root, false, WalkBounds::default())?,
            false,
        )
    }

    /// The full check for `plugins trust`, `plugins status` and `doctor`:
    /// everything the quick check does, plus the sha256 of every file and of
    /// the interpreter.
    ///
    /// # Errors
    /// As [`Self::check_quick`].
    pub fn verify_full(&self) -> Result<(), PyEnvError> {
        supported_platform()?;
        self.check_interpreter(true)?;
        compare(
            &self.record.entries,
            &scan(&self.root, true, WalkBounds::default())?,
            true,
        )
    }

    fn check_interpreter(&self, full: bool) -> Result<(), PyEnvError> {
        let files = &self.record.interpreter.files;
        let resolved = fs::canonicalize(self.python()).map_err(PyEnvError::io(
            PyenvPhrase::ResolvingEnvInterpreter.as_static(),
        ))?;
        if files.first().map(|f| Path::new(&f.path)) != Some(resolved.as_path()) {
            return Err(PyEnvError::Changed {
                path: resolved.display().to_string(),
                why: PyenvPhrase::NotRecordedInterpreter.as_static().into(),
            });
        }
        for f in files {
            let changed = |why: &str| PyEnvError::Changed {
                path: f.path.clone(),
                why: why.to_owned(),
            };
            let meta =
                fs::metadata(&f.path).map_err(|_| changed(PyenvPhrase::IsMissing.as_static()))?;
            let mtime = mtime_of(&meta)
                .map_err(|_| changed(PyenvPhrase::NoModificationTime.as_static()))?;
            if meta.len() != f.size || mtime != f.mtime {
                return Err(changed(PyenvPhrase::ChangedSizeOrTime.as_static()));
            }
            if full {
                let sha = sha256_file(Path::new(&f.path))?;
                if sha != f.sha256 {
                    return Err(changed(PyenvPhrase::ChangedContent.as_static()));
                }
            }
        }
        Ok(())
    }
}

/// An environment in the store, for `doctor` listings (Y7).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EnvSummary {
    /// Store key.
    pub key: String,
    /// Environment directory.
    pub path: PathBuf,
    /// The plugin tree it was built for.
    pub tree: String,
    /// Bytes of its files.
    pub bytes: u64,
}

/// The per-user store of managed environments.
#[derive(Debug, Clone)]
pub struct EnvStore {
    root: PathBuf,
    fail_record_writes: bool,
    limits: Limits,
}

/// The walk bounds and the per-run deadline of a build.
#[derive(Debug, Clone, Copy)]
struct Limits {
    walk: WalkBounds,
    step: Duration,
}

impl EnvStore {
    /// A store in `root`. Nothing is created until a build.
    #[must_use]
    pub fn open(root: impl Into<PathBuf>) -> Self {
        Self {
            root: root.into(),
            fail_record_writes: false,
            limits: Limits {
                walk: WalkBounds::default(),
                step: STEP_DEADLINE,
            },
        }
    }

    /// Test seam: make every record write fail, as a full disk would.
    #[doc(hidden)]
    #[must_use]
    pub fn failing_record_writes(mut self) -> Self {
        self.fail_record_writes = true;
        self
    }

    /// Test seam: smaller environment bounds (entries, directory levels,
    /// file bytes) and a shorter deadline for each uv or interpreter run.
    /// Each value is clamped to the production limit, so the seam can only
    /// tighten them.
    #[doc(hidden)]
    #[must_use]
    pub fn with_test_bounds(
        mut self,
        entries: usize,
        depth: usize,
        bytes: u64,
        step: Duration,
    ) -> Self {
        let max = WalkBounds::default();
        self.limits.walk = WalkBounds {
            nodes: entries.min(max.nodes),
            depth: depth.min(max.depth),
            bytes: bytes.min(max.bytes),
        };
        self.limits.step = step.min(STEP_DEADLINE);
        self
    }

    /// The store key of the environment for `tree` and an interpreter request.
    #[must_use]
    pub fn key(tree: &TreeHash, python: &str) -> String {
        Digest::of(&canonical_json(
            &json!({"tree": tree.as_str(), "python": python}),
        ))
        .hex()
        .to_owned()
    }

    fn record_path(&self, key: &str) -> PathBuf {
        self.root.join(format!("{key}.json"))
    }

    /// The recorded environment for `tree`, if one exists. It is not checked.
    ///
    /// # Errors
    /// [`PyEnvError::Record`] for a damaged or mismatched record.
    pub fn load(&self, tree: &TreeHash, python: &str) -> Result<Option<ManagedEnv>, PyEnvError> {
        supported_platform()?;
        let key = Self::key(tree, python);
        let path = self.record_path(&key);
        let Some(record) = read_record(&path)? else {
            return Ok(None);
        };
        if record.tree != tree.as_str() || record.python != python {
            return Err(PyEnvError::Record {
                path,
                why: PyenvPhrase::NamesAnotherTree.as_static().into(),
            });
        }
        Ok(Some(ManagedEnv {
            root: self.root.join(&key),
            record,
        }))
    }

    /// The recorded environment if it passes the quick check, else a new build.
    ///
    /// # Errors
    /// As [`Self::build`].
    pub fn ensure(
        &self,
        installer: &Installer,
        plugin_root: &Path,
        tree: &TreeHash,
    ) -> Result<ManagedEnv, PyEnvError> {
        if let Ok(Some(env)) = self.load(tree, &installer.python)
            && env.check_quick().is_ok()
        {
            return Ok(env);
        }
        self.build(installer, plugin_root, tree)
    }

    /// Build the environment for the verified plugin tree at `plugin_root`,
    /// replacing any earlier one for the same tree and interpreter request.
    ///
    /// # Errors
    /// [`PyEnvError::SourceOnly`], [`PyEnvError::Lock`] or
    /// [`PyEnvError::Wheel`] before anything runs, [`PyEnvError::Tree`] when
    /// the tree does not verify, [`PyEnvError::OfflinePythonMissing`],
    /// [`PyEnvError::Step`] when uv or the probe fails, plus I/O failures.
    pub fn build(
        &self,
        installer: &Installer,
        plugin_root: &Path,
        tree: &TreeHash,
    ) -> Result<ManagedEnv, PyEnvError> {
        supported_platform()?;
        installer.check()?;
        verify_tree(plugin_root, tree)?;
        let lock = PyLock::read(&plugin_root.join(LOCK_FILE))?;
        lock.verify_wheels(plugin_root)?;

        create_private_dir(&self.root)?;
        let key = Self::key(tree, &installer.python);
        let guard = OpenOptions::new()
            .create(true)
            .truncate(false)
            .write(true)
            .open(self.root.join(format!("{key}.lock")))
            .map_err(PyEnvError::io(PyenvPhrase::OpeningEnvLock.as_static()))?;
        guard
            .lock()
            .map_err(PyEnvError::io(PyenvPhrase::LockingEnv.as_static()))?;
        let staging_parent = self.root.join(".staging");
        create_private_dir(&staging_parent)?;
        let staging = Staging(
            tempfile::Builder::new()
                .prefix(&format!("{}-", &key[..16]))
                .tempdir_in(&staging_parent)
                .map_err(PyEnvError::io(PyenvPhrase::CreatingStaging.as_static()))?
                .keep(),
            true,
        );
        let env = staging.0.join("env");

        let final_root = self.root.join(&key);
        let (python, pin) = install(
            installer,
            plugin_root,
            &lock,
            &staging.0,
            &env,
            &final_root,
            self.limits,
        )?;
        pin.verify(&env)?;
        let probe = probe(&python, &staging.0, self.limits.step)?;
        make_read_only(&env, &scan(&env, false, self.limits.walk)?)?;
        let entries = scan(&env, true, self.limits.walk)?;

        let record_path = self.record_path(&key);
        remove_file_if_exists(&record_path)?;
        if fs::symlink_metadata(&final_root).is_ok() {
            evict(&final_root)?;
        }
        fs::rename(&env, &final_root)
            .map_err(PyEnvError::io(PyenvPhrase::MovingEnv.as_static()))?;
        // Until the record exists, nothing can load the environment: remove it on failure.
        let mut placed = Staging(final_root.clone(), true);
        listing::set_read_only(&final_root, true)?;
        let interpreter = interpreter(&env_python(&final_root), probe)?;
        let record = EnvRecord {
            schema_version: RECORD_SCHEMA,
            tree: tree.as_str().to_owned(),
            python: installer.python.clone(),
            lock: lock.digest.to_string(),
            interpreter,
            entries,
        };
        if self.fail_record_writes {
            return Err(PyEnvError::Io {
                what: PyenvPhrase::WritingRecord.as_static().into(),
                source: io::Error::other("injected failure"),
            });
        }
        write_record(&self.root, &record_path, &record)?;
        placed.1 = false;
        drop(staging);
        drop(guard);
        Ok(ManagedEnv {
            root: final_root,
            record,
        })
    }

    /// Every recorded environment, for `doctor` (Y7).
    ///
    /// # Errors
    /// [`PyEnvError::Record`] for a damaged record, plus read failures.
    pub fn list(&self) -> Result<Vec<EnvSummary>, PyEnvError> {
        let mut out = Vec::new();
        let rd = match fs::read_dir(&self.root) {
            Ok(rd) => rd,
            Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(out),
            Err(e) => return Err(PyEnvError::io(PyenvPhrase::ReadingStore.as_static())(e)),
        };
        for e in rd {
            let e = e.map_err(PyEnvError::io(PyenvPhrase::ReadingStore.as_static()))?;
            let name = e.file_name().to_string_lossy().into_owned();
            let Some(key) = name.strip_suffix(".json") else {
                continue;
            };
            if let Some(r) = read_record(&e.path())? {
                out.push(EnvSummary {
                    key: key.to_owned(),
                    path: self.root.join(key),
                    tree: r.tree,
                    bytes: r.entries.iter().map(|e| e.size).sum(),
                });
            }
        }
        out.sort_by(|a, b| a.key.cmp(&b.key));
        Ok(out)
    }

    /// Remove an environment and its record. An environment past the walk
    /// bounds is renamed aside instead ([`Evicted::Quarantined`]), and the
    /// caller reports the path it kept.
    ///
    /// # Errors
    /// Removal failures.
    pub fn remove(&self, key: &str) -> Result<Evicted, PyEnvError> {
        if key.len() != 64 || !key.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
            return Err(PyEnvError::Refused(
                PyenvText::NotStoreKey {
                    key: key.to_owned(),
                }
                .to_string(),
            ));
        }
        remove_file_if_exists(&self.record_path(key))?;
        Ok(evict(&self.root.join(key))?)
    }
}

/// Create the environment at `env` and install the lock into it: the uv runs
/// and the bytecode compilation of [`EnvStore::build`]. Bytecode is hash-checked
/// and names the files at `final_root`, so a rebuild of the same content
/// writes the same bytes. Returns the environment's interpreter.
fn install(
    installer: &Installer,
    plugin_root: &Path,
    lock: &PyLock,
    scratch: &Path,
    env: &Path,
    final_root: &Path,
    limits: Limits,
) -> Result<(PathBuf, Pin), PyEnvError> {
    let Limits { walk, step } = limits;
    if installer.network == InstallNetwork::Offline {
        let mut find = installer.uv(scratch);
        find.args([
            "python",
            "find",
            "--no-config",
            "--no-project",
            "--managed-python",
        ])
        .args(["--offline", "--no-python-downloads", "--quiet"])
        .arg(&installer.python);
        if run(find, scratch, PyenvPhrase::StepFind.as_static(), step).is_err() {
            return Err(PyEnvError::OfflinePythonMissing(installer.python.clone()));
        }
    }
    let mut venv = installer.uv(scratch);
    venv.args(["venv", "--no-config", "--no-project", "--managed-python"])
        .args(["--relocatable", "--no-cache", "--quiet", "--python"])
        .arg(&installer.python);
    if installer.network == InstallNetwork::Offline {
        venv.args(["--offline", "--no-python-downloads"]);
    }
    venv.arg(env);
    run(venv, scratch, PyenvPhrase::StepVenv.as_static(), step)?;
    // Taken before any wheel is installed: a wheel must not replace what the build runs.
    let pin = Pin::take(env)?;

    let python = env_python(env);
    if !lock.packages.is_empty() {
        let req = scratch.join("requirements.txt");
        fs::write(&req, lock.requirements())
            .map_err(PyEnvError::io(PyenvPhrase::WritingRequirements.as_static()))?;
        let mut pip = installer.uv(scratch);
        pip.args(["pip", "install", "--no-config", "--offline", "--no-index"])
            .args(["--no-cache", "--managed-python", "--no-python-downloads"])
            .args(["--no-build", "--no-deps", "--require-hashes"])
            .args(["--link-mode", "copy", "--quiet"])
            .arg("--python")
            .arg(&python);
        for dir in lock.wheel_dirs(plugin_root) {
            pip.arg("--find-links").arg(dir);
        }
        pip.arg("-r").arg(&req);
        run(pip, scratch, PyenvPhrase::StepPipInstall.as_static(), step)?;
    }

    // Bound the tree uv wrote before anything walks it again.
    scan(env, false, walk)?;
    let mut compile = Command::new(&python);
    compile
        .env_clear()
        .current_dir(scratch)
        .args(["-I", "-S", "-B", "-m", "compileall", "-q"])
        .args(["--invalidation-mode", "checked-hash", "-s"])
        .arg(env)
        .arg("-p")
        .arg(final_root)
        .arg(env);
    windows_env(&mut compile);
    pin.verify(env)?;
    run(compile, scratch, PyenvPhrase::StepCompile.as_static(), step)?;
    Ok((python, pin))
}

/// The interpreter and its configuration as `uv venv` made them, before any
/// wheel is installed. The build checks them before every interpreter run.
struct Pin {
    interpreter: PathBuf,
    interpreter_sha256: String,
    config_sha256: String,
}

impl Pin {
    fn take(env: &Path) -> Result<Self, PyEnvError> {
        let interpreter = fs::canonicalize(env_python(env)).map_err(PyEnvError::io(
            PyenvPhrase::ResolvingNewInterpreter.as_static(),
        ))?;
        let interpreter_sha256 = sha256_file(&interpreter)?;
        let config_sha256 = sha256_file(&env.join("pyvenv.cfg"))?;
        Ok(Self {
            interpreter,
            interpreter_sha256,
            config_sha256,
        })
    }

    fn verify(&self, env: &Path) -> Result<(), PyEnvError> {
        let now = Self::take(env)?;
        let changed = |path: &Path, why: &str| PyEnvError::Changed {
            path: path.display().to_string(),
            why: PyenvText::DuringBuild {
                why: why.to_owned(),
            }
            .to_string(),
        };
        if now.interpreter != self.interpreter || now.interpreter_sha256 != self.interpreter_sha256
        {
            return Err(changed(
                &env_python(env),
                PyenvPhrase::WasReplaced.as_static(),
            ));
        }
        if now.config_sha256 != self.config_sha256 {
            return Err(changed(
                &env.join("pyvenv.cfg"),
                PyenvPhrase::WasRewritten.as_static(),
            ));
        }
        Ok(())
    }
}

/// Removes a directory on every exit path while armed.
struct Staging(PathBuf, bool);

impl Drop for Staging {
    fn drop(&mut self) {
        if self.1 {
            let _ = evict(&self.0);
        }
    }
}

/// Run `cmd` to completion under the step deadline, its output in files.
fn run(
    mut cmd: Command,
    scratch: &Path,
    step: &str,
    limit: Duration,
) -> Result<PathBuf, PyEnvError> {
    let tag: String = step
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
        .collect();
    let out_path = scratch.join(format!("{tag}.out"));
    let err_path = scratch.join(format!("{tag}.err"));
    let out = File::create(&out_path)
        .map_err(PyEnvError::io(PyenvPhrase::CreatingOutputFile.as_static()))?;
    let err = File::create(&err_path)
        .map_err(PyEnvError::io(PyenvPhrase::CreatingOutputFile.as_static()))?;
    let mut child = cmd
        .stdin(Stdio::null())
        .stdout(out)
        .stderr(err)
        .spawn()
        .map_err(|e| PyEnvError::Step {
            step: step.to_owned(),
            status: PyenvPhrase::DidNotStart.as_static().into(),
            output: e.to_string(),
        })?;
    let deadline = Instant::now() + limit;
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break Some(status),
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(20)),
            _ => break None,
        }
    };
    let Some(status) = status else {
        let _ = child.kill();
        let _ = child.wait();
        return Err(PyEnvError::Step {
            step: step.to_owned(),
            status: PyenvPhrase::TimedOut.as_static().into(),
            output: String::new(),
        });
    };
    if status.success() {
        return Ok(out_path);
    }
    Err(PyEnvError::Step {
        step: step.to_owned(),
        status: status.to_string(),
        output: tail(&err_path),
    })
}

/// The last 4 KiB of a file, raw. [`PyEnvError`]'s `Display` escapes it.
fn tail(path: &Path) -> String {
    let Ok(bytes) = fs::read(path) else {
        return String::new();
    };
    let start = bytes.len().saturating_sub(4096);
    String::from_utf8_lossy(&bytes[start..]).into_owned()
}

fn probe(python: &Path, scratch: &Path, limit: Duration) -> Result<Probe, PyEnvError> {
    let mut cmd = Command::new(python);
    cmd.env_clear()
        .current_dir(scratch)
        .args(["-I", "-S", "-B", "-c", PROBE]);
    windows_env(&mut cmd);
    let out = run(cmd, scratch, PyenvPhrase::StepProbe.as_static(), limit)?;
    let mut raw = Vec::new();
    File::open(&out)
        .and_then(|f| f.take(MAX_PROBE_BYTES).read_to_end(&mut raw))
        .map_err(PyEnvError::io(PyenvPhrase::ReadingProbe.as_static()))?;
    serde_json::from_slice(&raw).map_err(|e| PyEnvError::Step {
        step: PyenvPhrase::StepProbe.as_static().into(),
        status: PyenvPhrase::UnreadableOutput.as_static().into(),
        output: e.to_string(),
    })
}

fn interpreter(python: &Path, p: Probe) -> Result<Interpreter, PyEnvError> {
    let mut paths = vec![fs::canonicalize(python).map_err(PyEnvError::io(
        PyenvPhrase::ResolvingInterpreter.as_static(),
    ))?];
    let base = fs::canonicalize(&p.base_executable)
        .map_err(PyEnvError::io(PyenvPhrase::ResolvingBase.as_static()))?;
    if !paths.contains(&base) {
        paths.push(base);
    }
    let mut files = Vec::new();
    for path in paths {
        let text = path
            .to_str()
            .ok_or_else(|| {
                PyEnvError::Refused(PyenvPhrase::InterpreterPathNotUtf8.as_static().into())
            })?
            .to_owned();
        let meta = fs::metadata(&path).map_err(PyEnvError::io(
            PyenvPhrase::InspectingInterpreter.as_static(),
        ))?;
        let sha256 = sha256_file(&path)?;
        files.push(InterpFile {
            path: text,
            size: meta.len(),
            mtime: mtime_of(&meta).map_err(PyEnvError::io(
                PyenvPhrase::InspectingInterpreter.as_static(),
            ))?,
            sha256,
        });
    }
    Ok(Interpreter {
        files,
        version: p.version,
        hexversion: p.hexversion,
        implementation: p.implementation,
        cache_tag: p.cache_tag,
        platform: p.platform,
        machine: p.machine,
    })
}

fn read_record(path: &Path) -> Result<Option<EnvRecord>, PyEnvError> {
    let damaged = |why: String| PyEnvError::Record {
        path: path.to_owned(),
        why,
    };
    let f = match File::open(path) {
        Ok(f) => f,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(damaged(e.to_string())),
    };
    let mut raw = Vec::new();
    f.take(MAX_RECORD_BYTES + 1)
        .read_to_end(&mut raw)
        .map_err(|e| damaged(e.to_string()))?;
    if raw.len() as u64 > MAX_RECORD_BYTES {
        return Err(damaged(PyenvPhrase::RecordTooLarge.as_static().into()));
    }
    let r: EnvRecord = serde_json::from_slice(&raw).map_err(|e| damaged(e.to_string()))?;
    if r.schema_version != RECORD_SCHEMA {
        return Err(damaged(PyenvPhrase::RecordSchema.as_static().into()));
    }
    Ok(Some(r))
}

fn write_record(dir: &Path, path: &Path, r: &EnvRecord) -> Result<(), PyEnvError> {
    let bytes = serde_json::to_vec(r).map_err(|e| PyEnvError::Record {
        path: path.to_owned(),
        why: e.to_string(),
    })?;
    let mut tmp = tempfile::Builder::new()
        .prefix(".record-")
        .tempfile_in(dir)
        .map_err(PyEnvError::io(PyenvPhrase::CreatingRecordFile.as_static()))?;
    tmp.write_all(&bytes)
        .and_then(|()| tmp.as_file().sync_all())
        .map_err(PyEnvError::io(PyenvPhrase::WritingRecord.as_static()))?;
    tmp.persist(path).map_err(|e| PyEnvError::Io {
        what: PyenvPhrase::ReplacingRecord.as_static().into(),
        source: e.error,
    })?;
    Ok(())
}

fn remove_file_if_exists(path: &Path) -> Result<(), PyEnvError> {
    match fs::remove_file(path) {
        Err(e) if e.kind() != io::ErrorKind::NotFound => {
            Err(PyEnvError::io(messages::removing(path))(e))
        }
        _ => Ok(()),
    }
}

#[cfg(unix)]
fn create_private_dir(dir: &Path) -> Result<(), PyEnvError> {
    use std::os::unix::fs::{DirBuilderExt, PermissionsExt};
    fs::DirBuilder::new()
        .recursive(true)
        .mode(0o700)
        .create(dir)
        .map_err(PyEnvError::io(messages::creating(dir)))?;
    fs::set_permissions(dir, fs::Permissions::from_mode(0o700))
        .map_err(PyEnvError::io(messages::securing(dir)))
}

#[cfg(not(unix))]
fn create_private_dir(dir: &Path) -> Result<(), PyEnvError> {
    fs::create_dir_all(dir).map_err(PyEnvError::io(messages::creating(dir)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bounds_only_tighten_the_production_limits() {
        let loose = EnvStore::open("/nonexistent").with_test_bounds(
            usize::MAX,
            usize::MAX,
            u64::MAX,
            Duration::MAX,
        );
        let l = loose.limits;
        assert_eq!(
            (l.walk.nodes, l.walk.depth, l.walk.bytes, l.step),
            (20_000, 32, 1 << 30, Duration::from_secs(600))
        );
        let tight =
            EnvStore::open("/nonexistent").with_test_bounds(5, 3, 7, Duration::from_millis(9));
        let t = tight.limits;
        assert_eq!(
            (t.walk.nodes, t.walk.depth, t.walk.bytes, t.step),
            (5, 3, 7, Duration::from_millis(9))
        );
    }
}
