//! The dependency lock a Python plugin ships: a PEP 751 `pylock.toml` whose
//! every package is a hash-pinned wheel inside the signed artifact (Y1, Y2).

use std::fmt::Write as _;
use std::fs::File;
use std::io::{Read as _, Seek as _, SeekFrom};
use std::path::{Path, PathBuf};

use sha2::{Digest as _, Sha256};

use super::PyEnvError;
use super::listing::{MAX_BYTES, MAX_NODES};
use crate::hooks::check_relative_path;
use crate::messages::pyenv::{self as messages, PyenvPhrase, PyenvText};
use crate::oci::Digest;

/// Largest lock file read.
const MAX_LOCK_BYTES: u64 = 4 << 20;
/// Most packages in one lock.
const MAX_PACKAGES: usize = 2_000;
/// Package keys that name something other than a vendored wheel. Each needs a
/// build backend, a download or a local project, so each is refused (Y1).
const NOT_A_WHEEL: [&str; 4] = ["sdist", "vcs", "directory", "archive"];

/// One wheel of a locked package.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LockedWheel {
    /// Path relative to the plugin tree, with `/` separators.
    pub path: String,
    /// Lowercase hex sha256 from the lock.
    pub sha256: String,
}

/// One locked package.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LockedPackage {
    /// Distribution name as written in the lock.
    pub name: String,
    /// Exact version.
    pub version: String,
    /// Environment marker, passed to the installer unchanged.
    pub marker: Option<String>,
    /// The wheels the installer may pick from, one per platform.
    pub wheels: Vec<LockedWheel>,
}

/// A parsed and checked `pylock.toml`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PyLock {
    /// The packages in lock order.
    pub packages: Vec<LockedPackage>,
    /// sha256 of the lock file bytes.
    pub digest: Digest,
}

impl PyLock {
    /// Read and check the lock at `path`.
    ///
    /// # Errors
    /// [`PyEnvError::Io`] for a read failure, otherwise as [`Self::parse`].
    pub fn read(path: &Path) -> Result<Self, PyEnvError> {
        let mut raw = Vec::new();
        File::open(path)
            .and_then(|f| f.take(MAX_LOCK_BYTES + 1).read_to_end(&mut raw))
            .map_err(PyEnvError::io(messages::reading(path)))?;
        if raw.len() as u64 > MAX_LOCK_BYTES {
            return Err(PyEnvError::Lock(
                PyenvPhrase::LockTooLarge.as_static().into(),
            ));
        }
        let text = String::from_utf8(raw)
            .map_err(|_| PyEnvError::Lock(PyenvPhrase::LockNotUtf8.as_static().into()))?;
        Self::parse(&text)
    }

    /// Parse and check lock text.
    ///
    /// Every package must have an exact version and at least one wheel, and each
    /// wheel a relative `path` inside the tree and a sha256. A package with an
    /// `sdist`, `vcs`, `directory` or `archive` source is refused, as is a wheel
    /// with only a `url`: the build runs no backend and fetches nothing. Other
    /// PEP 751 keys are ignored.
    ///
    /// # Errors
    /// [`PyEnvError::SourceOnly`] for a package that is not a vendored wheel,
    /// [`PyEnvError::Lock`] or [`PyEnvError::Wheel`] for anything else.
    pub fn parse(text: &str) -> Result<Self, PyEnvError> {
        let bad = |why: &str| PyEnvError::Lock(why.to_owned());
        let doc: toml::Table = text.parse().map_err(|e| PyEnvError::Lock(format!("{e}")))?;
        let version = doc
            .get("lock-version")
            .and_then(toml::Value::as_str)
            .ok_or_else(|| bad(PyenvPhrase::LockVersionMissing.as_static()))?;
        if version.split('.').next() != Some("1") {
            return Err(PyEnvError::Lock(
                PyenvText::LockVersionUnsupported {
                    version: version.to_owned(),
                }
                .to_string(),
            ));
        }
        let packages = match doc.get("packages") {
            None => &[][..],
            Some(v) => v
                .as_array()
                .ok_or_else(|| bad(PyenvPhrase::PackagesNotArray.as_static()))?
                .as_slice(),
        };
        if packages.len() > MAX_PACKAGES {
            return Err(bad(PyenvPhrase::TooManyPackages.as_static()));
        }
        let packages = packages
            .iter()
            .map(package)
            .collect::<Result<Vec<_>, _>>()?;
        Ok(Self {
            packages,
            digest: Digest::of(text.as_bytes()),
        })
    }

    /// Check every wheel against the plugin tree at `root`: a regular `.whl`
    /// file named for its package whose sha256 matches the lock, and a plain
    /// (not ZIP64) archive. Runs before the installer, which checks the hashes
    /// again.
    ///
    /// No entry may land where the build or the interpreter runs it before
    /// trust (Y1, Y4, Y6): an interpreter or activation script in `bin`, the
    /// environment's `pyvenv.cfg`, or a startup hook (`.pth`, `sitecustomize`,
    /// `usercustomize`), and data in the interpreter's own directories.
    ///
    /// The sizes and entry counts the archives declare must fit the
    /// environment bounds (threat model section 5.5), counting the largest
    /// wheel of each package, so a decompression bomb is refused before it is
    /// expanded.
    ///
    /// # Errors
    /// [`PyEnvError::Wheel`] naming the package and the problem,
    /// [`PyEnvError::Refused`] when the wheels would expand past the bounds.
    pub fn verify_wheels(&self, root: &Path) -> Result<(), PyEnvError> {
        let (mut entries, mut bytes) = (0u64, 0u64);
        for p in &self.packages {
            let (mut pkg_entries, mut pkg_bytes) = (0u64, 0u64);
            for w in &p.wheels {
                let file = root.join(&w.path);
                let wrong = |why: String| PyEnvError::Wheel {
                    package: p.name.clone(),
                    why,
                };
                let meta = std::fs::symlink_metadata(&file)
                    .map_err(|e| wrong(path_problem(&w.path, &e)))?;
                if !meta.is_file() {
                    return Err(wrong(
                        PyenvText::WheelNotRegular {
                            path: w.path.clone(),
                        }
                        .to_string(),
                    ));
                }
                let mut h = Sha256::new();
                let mut f = File::open(&file).map_err(|e| wrong(path_problem(&w.path, &e)))?;
                std::io::copy(&mut f, &mut h).map_err(|e| wrong(path_problem(&w.path, &e)))?;
                let actual = hex(&h.finalize());
                if actual != w.sha256 {
                    return Err(wrong(
                        PyenvText::WheelHashMismatch {
                            path: w.path.clone(),
                            actual,
                            pinned: w.sha256.clone(),
                        }
                        .to_string(),
                    ));
                }
                let (n, size, names) =
                    zip_listing(&file).map_err(|why| wrong(path_problem(&w.path, &why)))?;
                if let Some((name, why)) =
                    names.iter().find_map(|n| refused_entry(n).map(|w| (n, w)))
                {
                    return Err(wrong(
                        PyenvText::WheelHolds {
                            path: w.path.clone(),
                            name: name.clone(),
                            why: why.to_owned(),
                        }
                        .to_string(),
                    ));
                }
                pkg_entries = pkg_entries.max(n);
                pkg_bytes = pkg_bytes.max(size);
            }
            entries += pkg_entries;
            bytes += pkg_bytes;
        }
        if entries > MAX_NODES as u64 || bytes > MAX_BYTES {
            return Err(PyEnvError::Refused(
                PyenvText::WheelsTooBig {
                    entries,
                    bytes,
                    max_entries: MAX_NODES,
                }
                .to_string(),
            ));
        }
        Ok(())
    }

    /// The directories, inside `root`, that hold the locked wheels. The
    /// installer searches only these (`--find-links`, `--no-index`).
    #[must_use]
    pub fn wheel_dirs(&self, root: &Path) -> Vec<PathBuf> {
        let mut dirs: Vec<PathBuf> = self
            .packages
            .iter()
            .flat_map(|p| &p.wheels)
            .map(|w| {
                let parent = w.path.rsplit_once('/').map_or("", |(d, _)| d);
                root.join(parent)
            })
            .collect();
        dirs.sort();
        dirs.dedup();
        dirs
    }

    /// The lock as a hash-checking requirements file: one `name==version`
    /// line per package with every locked wheel hash, so the installer may
    /// install only those exact files.
    #[must_use]
    pub fn requirements(&self) -> String {
        let mut out = String::new();
        for p in &self.packages {
            let _ = write!(out, "{}=={}", p.name, p.version);
            if let Some(m) = &p.marker {
                let _ = write!(out, " ; {m}");
            }
            for w in &p.wheels {
                let _ = write!(out, " --hash=sha256:{}", w.sha256);
            }
            out.push('\n');
        }
        out
    }
}

/// `PathProblem` for a wheel path and what is wrong with it.
fn path_problem(path: &str, reason: &dyn std::fmt::Display) -> String {
    PyenvText::PathProblem {
        path: path.to_owned(),
        reason: reason.to_string(),
    }
    .to_string()
}

fn package(v: &toml::Value) -> Result<LockedPackage, PyEnvError> {
    let t = v
        .as_table()
        .ok_or_else(|| PyEnvError::Lock(PyenvPhrase::PackageNotTable.as_static().into()))?;
    let name = t
        .get("name")
        .and_then(toml::Value::as_str)
        .ok_or_else(|| PyEnvError::Lock(PyenvPhrase::PackageNoName.as_static().into()))?;
    if name.is_empty()
        || name.len() > 200
        || !name
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-'))
    {
        return Err(PyEnvError::Lock(
            PyenvText::BadPackageName {
                name: name.to_owned(),
            }
            .to_string(),
        ));
    }
    let wrong = |why: String| PyEnvError::Wheel {
        package: name.to_owned(),
        why,
    };
    if let Some(key) = NOT_A_WHEEL.iter().find(|k| t.contains_key(**k)) {
        return Err(PyEnvError::SourceOnly {
            package: name.to_owned(),
            source_kind: (*key).to_owned(),
        });
    }
    let version = t
        .get("version")
        .and_then(toml::Value::as_str)
        .ok_or_else(|| wrong(PyenvPhrase::NoExactVersion.as_static().into()))?;
    if version.is_empty()
        || version.len() > 100
        || !version
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-' | b'+' | b'!'))
    {
        return Err(wrong(
            PyenvText::VersionNotExact {
                version: version.to_owned(),
            }
            .to_string(),
        ));
    }
    let marker = match t.get("marker") {
        None => None,
        Some(m) => {
            let m = m
                .as_str()
                .ok_or_else(|| wrong(PyenvPhrase::MarkerNotString.as_static().into()))?;
            if let Err(why) = check_marker(m) {
                return Err(wrong(
                    PyenvText::MarkerRefused {
                        marker: m.to_owned(),
                        why: why.to_owned(),
                    }
                    .to_string(),
                ));
            }
            Some(m.to_owned())
        }
    };
    let wheels = t
        .get("wheels")
        .and_then(toml::Value::as_array)
        .filter(|w| !w.is_empty())
        .ok_or_else(|| PyEnvError::SourceOnly {
            package: name.to_owned(),
            source_kind: PyenvPhrase::NoWheels.as_static().into(),
        })?
        .iter()
        .map(|w| wheel(name, version, w))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(LockedPackage {
        name: name.to_owned(),
        version: version.to_owned(),
        marker,
        wheels,
    })
}

fn wheel(package: &str, version: &str, v: &toml::Value) -> Result<LockedWheel, PyEnvError> {
    let wrong = |why: String| PyEnvError::Wheel {
        package: package.to_owned(),
        why,
    };
    let t = v
        .as_table()
        .ok_or_else(|| wrong(PyenvPhrase::WheelNotTable.as_static().into()))?;
    let path = t
        .get("path")
        .and_then(toml::Value::as_str)
        .ok_or_else(|| wrong(PyenvPhrase::WheelNoPath.as_static().into()))?;
    check_relative_path(path).map_err(|e| wrong(path_problem(path, &e)))?;
    let file = path.rsplit('/').next().unwrap_or(path);
    let Some(stem) = file.strip_suffix(".whl") else {
        return Err(wrong(
            PyenvText::NotAWheel {
                path: path.to_owned(),
            }
            .to_string(),
        ));
    };
    // {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
    let parts: Vec<&str> = stem.split('-').collect();
    if !(5..=6).contains(&parts.len())
        || normalise(parts[0]) != normalise(package)
        || parts[1] != version.replace('-', "_")
    {
        return Err(wrong(
            PyenvText::NotWheelOfPackage {
                path: path.to_owned(),
                package: package.to_owned(),
                version: version.to_owned(),
            }
            .to_string(),
        ));
    }
    let sha = t
        .get("hashes")
        .and_then(toml::Value::as_table)
        .and_then(|h| h.get("sha256"))
        .and_then(toml::Value::as_str)
        .ok_or_else(|| {
            wrong(
                PyenvText::NoSha256 {
                    path: path.to_owned(),
                }
                .to_string(),
            )
        })?;
    if sha.len() != 64 || !sha.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
        return Err(wrong(
            PyenvText::BadSha256 {
                path: path.to_owned(),
            }
            .to_string(),
        ));
    }
    Ok(LockedWheel {
        path: path.to_owned(),
        sha256: sha.to_owned(),
    })
}

/// PEP 503 normalisation.
fn normalise(name: &str) -> String {
    let mut out = String::with_capacity(name.len());
    let mut sep = false;
    for c in name.chars() {
        if matches!(c, '-' | '_' | '.') {
            sep = true;
        } else {
            if sep && !out.is_empty() {
                out.push('-');
            }
            sep = false;
            out.push(c.to_ascii_lowercase());
        }
    }
    out
}

/// Check a PEP 508 environment marker as the requirements line will carry it.
///
/// Outside quotes only marker grammar is allowed: names, comparison
/// operators, parentheses and spaces. Inside quotes any printable ASCII is
/// allowed except the closing quote, a backslash and `#`, so a value such as
/// `'5.15.0-91-generic'` passes. Nothing may start an option (a space then
/// `-`), a comment or a new line, and every quote must close.
fn check_marker(m: &str) -> Result<(), &'static str> {
    if m.is_empty() || m.len() > 1_000 {
        return Err(PyenvPhrase::MarkerEmptyOrLong.as_static());
    }
    let mut quote: Option<u8> = None;
    let mut prev = b' ';
    for b in m.bytes() {
        if !(b == b' ' || b.is_ascii_graphic()) {
            return Err(PyenvPhrase::MarkerControl.as_static());
        }
        if matches!(b, b'#' | b'\\') {
            return Err(PyenvPhrase::MarkerComment.as_static());
        }
        if b == b'-' && prev == b' ' {
            return Err(PyenvPhrase::MarkerOption.as_static());
        }
        match quote {
            Some(q) if b == q => quote = None,
            Some(_) => {}
            None if matches!(b, b'\'' | b'"') => quote = Some(b),
            None if b.is_ascii_alphanumeric()
                || matches!(
                    b,
                    b' ' | b'_' | b'.' | b'<' | b'>' | b'=' | b'!' | b'~' | b'(' | b')'
                ) => {}
            None => return Err(PyenvPhrase::MarkerGrammar.as_static()),
        }
        prev = b;
    }
    if quote.is_some() {
        return Err(PyenvPhrase::MarkerQuote.as_static());
    }
    Ok(())
}

/// Why a wheel entry may not be installed, if it may not.
///
/// The install schemes map `<name>.data/scripts` to the environment's `bin`,
/// `<name>.data/data` to the environment root and `<name>.data/purelib` or
/// `platlib`, like the wheel root, to `site-packages`. Refused:
///
/// - a script named `python*`, `activate*`, `deactivate*` or `pyvenv.cfg`,
///   which would replace the interpreter or its configuration;
/// - data under `bin`, `Scripts`, `lib`, `Lib`, `lib64` or `include`, or a
///   root `pyvenv.cfg`;
/// - in `site-packages`, any `.pth` file and any top-level `sitecustomize` or
///   `usercustomize` module or package;
/// - an unknown scheme, and any name that is absolute, has `..` or `.`
///   segments, or uses a backslash.
fn refused_entry(name: &str) -> Option<&'static str> {
    if name.starts_with('/')
        || name.contains('\\')
        || name.split('/').any(|seg| seg == ".." || seg == ".")
    {
        return Some(PyenvPhrase::EntryOutsideScheme.as_static());
    }
    let mut parts = name.splitn(3, '/');
    let first = parts.next().unwrap_or("");
    let (scheme, rest) = if Path::new(first)
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("data"))
    {
        let scheme = parts.next().unwrap_or("");
        (scheme, parts.next().unwrap_or(""))
    } else {
        ("purelib", name)
    };
    let top = rest.split('/').next().unwrap_or("").to_ascii_lowercase();
    let base = rest.rsplit('/').next().unwrap_or("").to_ascii_lowercase();
    match scheme.to_ascii_lowercase().as_str() {
        "scripts" => {
            let interp = ["python", "activate", "deactivate"]
                .iter()
                .any(|p| base.starts_with(p))
                || base == "pyvenv.cfg";
            interp.then_some(PyenvPhrase::EntryReplacesInterpreter.as_static())
        }
        "data" => (["bin", "scripts", "lib", "lib64", "include", "pyvenv.cfg"]
            .contains(&top.as_str()))
        .then_some(PyenvPhrase::EntryWritesInterpreterDirs.as_static()),
        "purelib" | "platlib" => {
            let stem = top.split('.').next().unwrap_or("").to_ascii_lowercase();
            (Path::new(&base).extension().is_some_and(|e| e == "pth")
                || stem == "sitecustomize"
                || stem == "usercustomize")
                .then_some(PyenvPhrase::EntryStartupHook.as_static())
        }
        "headers" => None,
        _ => Some(PyenvPhrase::EntryUnknownScheme.as_static()),
    }
}

/// Entries, declared uncompressed bytes and entry names of a ZIP archive,
/// read from its central directory. ZIP64 archives are refused: no wheel
/// within the bounds needs one.
fn zip_listing(path: &Path) -> Result<(u64, u64, Vec<String>), String> {
    const EOCD: [u8; 4] = [0x50, 0x4b, 0x05, 0x06];
    const CDH: [u8; 4] = [0x50, 0x4b, 0x01, 0x02];
    const LOC64: [u8; 4] = [0x50, 0x4b, 0x06, 0x07];
    let u16_at = |b: &[u8], i: usize| u64::from(u16::from_le_bytes([b[i], b[i + 1]]));
    let u32_at =
        |b: &[u8], i: usize| u64::from(u32::from_le_bytes([b[i], b[i + 1], b[i + 2], b[i + 3]]));
    let mut f = File::open(path).map_err(|e| e.to_string())?;
    let len = f.metadata().map_err(|e| e.to_string())?.len();
    let tail_len = len.min(22 + 65_535 + 20);
    f.seek(SeekFrom::Start(len - tail_len))
        .map_err(|e| e.to_string())?;
    let mut tail = vec![0; usize::try_from(tail_len).map_err(|e| e.to_string())?];
    f.read_exact(&mut tail).map_err(|e| e.to_string())?;
    let at = (0..tail.len().saturating_sub(21))
        .rev()
        .find(|&i| tail[i..i + 4] == EOCD)
        .ok_or(PyenvPhrase::NotZip.as_static())?;
    let e = &tail[at..];
    if at >= 20 && tail[at - 20..at - 16] == LOC64 {
        return Err(PyenvPhrase::Zip64.as_static().into());
    }
    let (count, cd_size, cd_off) = (u16_at(e, 10), u32_at(e, 12), u32_at(e, 16));
    if count == 0xffff || cd_size == 0xffff_ffff || cd_off == 0xffff_ffff {
        return Err(PyenvPhrase::Zip64.as_static().into());
    }
    if cd_off + cd_size > len {
        return Err(PyenvPhrase::ZipDirectoryOutside.as_static().into());
    }
    f.seek(SeekFrom::Start(cd_off)).map_err(|e| e.to_string())?;
    let mut cd = vec![0; usize::try_from(cd_size).map_err(|e| e.to_string())?];
    f.read_exact(&mut cd).map_err(|e| e.to_string())?;
    let (mut i, mut n, mut bytes) = (0usize, 0u64, 0u64);
    let mut names = Vec::new();
    while n < count {
        if i + 46 > cd.len() || cd[i..i + 4] != CDH {
            return Err(PyenvPhrase::ZipDirectoryDamaged.as_static().into());
        }
        let size = u32_at(&cd, i + 24);
        if size == 0xffff_ffff {
            return Err(PyenvPhrase::Zip64Entry.as_static().into());
        }
        bytes += size;
        n += 1;
        let name_len = usize::try_from(u16_at(&cd, i + 28)).map_err(|e| e.to_string())?;
        let name = cd
            .get(i + 46..i + 46 + name_len)
            .ok_or(PyenvPhrase::ZipDirectoryDamaged.as_static())?;
        names.push(
            String::from_utf8(name.to_vec())
                .map_err(|_| PyenvPhrase::ZipNameNotUtf8.as_static())?,
        );
        let skip = 46 + u16_at(&cd, i + 28) + u16_at(&cd, i + 30) + u16_at(&cd, i + 32);
        i += usize::try_from(skip).map_err(|e| e.to_string())?;
    }
    Ok((n, bytes, names))
}

pub(super) fn hex(bytes: &[u8]) -> String {
    bytes.iter().fold(String::with_capacity(64), |mut s, b| {
        let _ = write!(s, "{b:02x}");
        s
    })
}
