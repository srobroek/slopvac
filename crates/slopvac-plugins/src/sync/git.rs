//! Pinned-commit git sources (threat model F5, K11, N10, E8).
//!
//! # Why a `git` subprocess
//!
//! The fetch needs a git smart-HTTP client with TLS, shallow fetch of one
//! commit by id, and proxy and certificate handling that match what the user's
//! own `git` does. The Rust option is `gix`: at 0.90 it is pre-1.0, pulls in
//! about thirty `gix-*` crates and, for HTTPS, a second HTTP and TLS stack next
//! to `ureq` and rustls (the programme picked one TLS stack). A `git` process
//! costs nothing in the build, is the client every forge tests against, and
//! runs under the same containment as credential helpers ([`Contained`]).
//! Its risks are the ones the threat model lists as N10, and the controls
//! below answer each of them.
//!
//! # What runs, and what cannot
//!
//! - `git` is found on `PATH` among trusted directories only (CWE-427). A
//!   relative entry such as `.` is skipped. So is an absolute entry that, after
//!   links resolve, lies inside the project (a hostile checkout could plant its
//!   own `git` there). The program is the link-resolved file, and that file,
//!   its directory and every ancestor must belong to root or the current user
//!   and be closed to group and others (a sticky, root-owned ancestor such as
//!   `/tmp` is allowed). The resolved path is what runs.
//! - The environment is cleared. Only proxy and certificate variables and the
//!   Windows system variables pass through. `HOME` and the config files point
//!   at an empty scratch directory (`GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM`
//!   at the null device), so no user or system config, credential helper,
//!   `GIT_*` variable or askpass program applies, and `GIT_TERMINAL_PROMPT=0`
//!   rules out a prompt.
//! - Only `https` is an allowed transport (`GIT_ALLOW_PROTOCOL`,
//!   `protocol.allow=never`, `protocol.https.allow=always`), which stops
//!   `ext::` and `file::`. Redirects are not followed at all
//!   (`http.followRedirects=false`): git's HTTP client would otherwise follow an
//!   initial redirect, to an internal host included (CWE-918). Hooks point at an empty
//!   directory, `core.fsmonitor` is off and the scratch repository is made
//!   with no templates.
//! - The repository is fresh and bare, so nothing the remote serves can become
//!   local config, and `fsckObjects` is on.
//! - **No checkout happens.** The commit is read with `ls-tree` and
//!   `cat-file`, so attributes, filters, smudge programs, LFS, `.gitmodules`
//!   and `export-subst` have no effect. Symbolic links and submodule entries
//!   are refused, as are modes other than regular and executable files.
//! - The fetch is shallow (`--depth=1`) for exactly the pinned commit, with
//!   `--no-tags` and no submodule recursion. A deadline covers every command and
//!   the whole process group is killed at the deadline, and a watcher kills the
//!   fetch when the objects on disk pass the compressed size limit.
//!   `transfer.unpackLimit=1` keeps received objects in the pack, so a pack of
//!   highly compressed objects is not expanded to loose files, and the watcher
//!   sees every byte that lands on disk.
//! - Nothing is read from an object before its size is known. `ls-tree -l`
//!   lists every blob size, and the sum is checked against the expanded-size
//!   limit before `cat-file` runs, so a small pack of huge blobs is refused
//!   without materialising one.
//!
//! # Residual risks
//!
//! `git` has no option to cap the memory of `index-pack`, so every `git`
//! command runs through the plugin launcher ([`crate::launch`]) with a data
//! memory limit of 2 GiB, a CPU limit, an open-file limit and a file-size limit.
//! The launcher sets `RLIMIT_DATA` on Linux only; macOS enforces no memory limit,
//! so there a delta chain is bounded by the deadline and
//! `core.deltaBaseCacheLimit` alone. The binary that runs the sync must call
//! [`crate::launch::intercept`] first thing in `main`.
//!
//! The caller compares the resulting tree hash with the lock before anything
//! reaches the store.

use std::io::{self, BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{ChildStdin, ChildStdout, Command, ExitStatus, Stdio};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU8, Ordering};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use crate::extract::{ExtractError, Limits, StagedTree};
use crate::messages::sync as messages;
use crate::oci::Contained;
use crate::trusted_path::find_trusted;

/// Longest `git` error text kept for a message.
const MAX_STDERR_BYTES: u64 = 4 * 1024;
/// Longest `cat-file --batch` header line.
const MAX_HEADER_BYTES: u64 = 256;
/// How long a `git` process may take to exit after it closed its output.
const POLL: Duration = Duration::from_millis(10);
/// Variables that pass through to `git`. Proxies and certificate stores are the
/// user's network configuration; the rest are what Windows needs to start a process.
const PASS_THROUGH: &[&str] = &[
    "HTTPS_PROXY",
    "https_proxy",
    "NO_PROXY",
    "no_proxy",
    "ALL_PROXY",
    "all_proxy",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "SystemRoot",
    "windir",
    "TEMP",
    "TMP",
];

/// Why a git fetch or export failed.
#[derive(Debug)]
pub(super) enum GitError {
    /// `git` failed, or the commit is not acceptable. The text is raw.
    Failed(String),
    /// A limit was passed: the download, the number of files, or the expanded size.
    Limit(String),
    /// Writing the tree was refused.
    Extract(ExtractError),
}

impl From<ExtractError> for GitError {
    fn from(e: ExtractError) -> Self {
        Self::Extract(e)
    }
}

fn failed(msg: impl Into<String>) -> GitError {
    GitError::Failed(msg.into())
}

fn limit(msg: impl Into<String>) -> GitError {
    GitError::Limit(msg.into())
}

fn download_limit(max: u64) -> GitError {
    limit(messages::git_download_limit(max))
}

/// What to fetch and how far to trust the transport.
pub(super) struct Request<'a> {
    pub(super) git: &'a Path,
    pub(super) url: &'a str,
    pub(super) commit: &'a str,
    /// Test seam: also allow `file://` and loopback `http://` repositories.
    pub(super) allow_local: bool,
    pub(super) timeout: Duration,
    pub(super) limits: Limits,
    /// Production always sets this. Only the unit tests that inspect the
    /// command line leave it `None`.
    pub(super) confinement: Option<Confinement<'a>>,
}

/// The `git` program: the first in a trusted `PATH` directory (see the module
/// documentation). `project_root` anchors the check that it is not in the project.
pub(super) fn find_git(project_root: &Path) -> Option<PathBuf> {
    find_trusted("git", None, project_root)
}

/// Most data memory a `git` process may use (CWE-409, threat model E4).
/// `index-pack` rebuilds delta chains in memory, and `git` has no setting that
/// caps it.
pub(super) const GIT_MEMORY_BYTES: u64 = 2 << 30;
/// Open files for one `git` process.
const GIT_OPEN_FILES: u64 = 1024;

/// How `git` is started: through the plugin launcher, which sets the resource
/// limits (memory, CPU time, open files, file size) before `git` runs and
/// kills the whole process tree when `git` ends. `unsafe` is forbidden here, so
/// there is no `pre_exec`; the launcher is the one place that sets limits.
#[derive(Clone, Copy)]
pub(super) struct Confinement<'a> {
    /// The launcher program (see [`crate::launch`]).
    pub(super) launcher: &'a Path,
    /// Data-memory limit in bytes. Enforced on Linux; macOS has none (R2).
    pub(super) memory: u64,
}

/// `cmd` run through the launcher under the limits for `request`. The launcher
/// starts with an empty environment and hands `git` exactly the variables of
/// `cmd`; the working directory and the arguments carry over.
#[cfg(unix)]
fn confine(cmd: &Command, request: &Request<'_>, how: Confinement<'_>) -> Command {
    let secs = request.timeout.as_secs().saturating_add(5);
    let limits = crate::launch::Limits {
        cpu_secs: secs,
        open_files: GIT_OPEN_FILES,
        file_size: request
            .limits
            .compressed_bytes
            .saturating_mul(2)
            .saturating_add(1 << 20),
        memory: how.memory,
    };
    let args: Vec<String> = cmd
        .get_args()
        .map(|a| a.to_string_lossy().into_owned())
        .collect();
    let envs: Vec<(String, String)> = cmd
        .get_envs()
        .filter_map(|(k, v)| {
            Some((
                k.to_string_lossy().into_owned(),
                v?.to_string_lossy().into_owned(),
            ))
        })
        .collect();
    let mut out = crate::launch::command(
        how.launcher,
        limits,
        Duration::from_secs(2),
        &PathBuf::from(cmd.get_program()),
        &args,
        envs.iter().map(|(k, v)| (k.as_str(), v.as_str())),
    );
    if let Some(dir) = cmd.get_current_dir() {
        out.current_dir(dir);
    }
    out
}

#[cfg(not(unix))]
fn confine(cmd: &Command, _: &Request<'_>, _: Confinement<'_>) -> Command {
    // Not a supported platform for 3.0: no launcher exists here.
    let mut out = Command::new(cmd.get_program());
    out.args(cmd.get_args());
    out
}

/// Fetch exactly `request.commit` into a scratch repository under `scratch`
/// and write its files into `staged`.
pub(super) fn export_commit(
    request: &Request<'_>,
    scratch: &Path,
    staged: &mut StagedTree,
) -> Result<(), GitError> {
    let https = request.url.starts_with("https://");
    let local = request.allow_local
        && ["file://", "http://127.0.0.1:"]
            .iter()
            .any(|p| request.url.starts_with(p));
    if !(https || local) || request.url.starts_with('-') {
        return Err(failed(messages::SyncPhrase::GitHttpsOnly.as_static()));
    }
    if request.commit.len() != 40 || !request.commit.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(failed(messages::SyncPhrase::GitCommitShort.as_static()));
    }
    let git = Git::prepare(request, scratch)?;
    git.fetch()?;
    git.check_commit()?;
    let entries = git.list_tree()?;
    git.export(&entries, staged)
}

struct Git<'a> {
    request: &'a Request<'a>,
    work: PathBuf,
    repo: PathBuf,
    deadline: Instant,
}

impl<'a> Git<'a> {
    fn prepare(request: &'a Request<'a>, scratch: &Path) -> Result<Self, GitError> {
        let work = scratch.to_path_buf();
        for dir in ["home", "nohooks"] {
            std::fs::create_dir(work.join(dir)).map_err(|e| failed(messages::scratch_dir(&e)))?;
        }
        let git = Self {
            request,
            repo: work.join("repo"),
            work,
            deadline: Instant::now() + request.timeout,
        };
        let mut init = git.command();
        init.args(["init", "--quiet", "--bare", "--template="])
            .arg("--")
            .arg(&git.repo);
        git.run(init, "init", None, 4096)?;
        Ok(git)
    }

    /// A `git` command with the scrubbed environment and the fixed config.
    fn command(&self) -> Command {
        let null = if cfg!(windows) { "NUL" } else { "/dev/null" };
        let home = self.work.join("home");
        let mut cmd = Command::new(self.request.git);
        cmd.env_clear().current_dir(&self.work);
        for name in PASS_THROUGH {
            if let Some(value) = std::env::var_os(name) {
                cmd.env(name, value);
            }
        }
        let allowed = if self.request.allow_local {
            "https:file:http"
        } else {
            "https"
        };
        cmd.env("HOME", &home)
            .env("XDG_CONFIG_HOME", &home)
            .env("USERPROFILE", &home)
            .env("GIT_CONFIG_GLOBAL", null)
            .env("GIT_CONFIG_SYSTEM", null)
            .env("GIT_CONFIG_NOSYSTEM", "1")
            .env("GIT_TERMINAL_PROMPT", "0")
            .env("GIT_ALLOW_PROTOCOL", allowed)
            .env("GIT_NO_REPLACE_OBJECTS", "1")
            .env("GIT_OPTIONAL_LOCKS", "0")
            .env("LC_ALL", "C");
        let hooks = format!("core.hooksPath={}", self.work.join("nohooks").display());
        let mut config = vec![
            "protocol.allow=never",
            "protocol.https.allow=always",
            "protocol.version=2",
            "core.fsmonitor=false",
            "core.askPass=",
            "credential.helper=",
            "http.sslVerify=true",
            "transfer.fsckObjects=true",
            "fetch.recurseSubmodules=false",
            "http.followRedirects=false",
            "transfer.unpackLimit=1",
            "fetch.unpackLimit=1",
            "core.deltaBaseCacheLimit=16m",
            "gc.auto=0",
            "maintenance.auto=false",
            "fetch.writeCommitGraph=false",
            &hooks,
        ];
        if self.request.allow_local {
            config.push("protocol.file.allow=always");
            config.push("protocol.http.allow=always");
        }
        for entry in config {
            cmd.arg("-c").arg(entry);
        }
        match self.request.confinement {
            Some(how) => confine(&cmd, self.request, how),
            None => cmd,
        }
    }

    /// A command that works on the scratch repository.
    fn in_repo(&self) -> Command {
        let mut cmd = self.command();
        cmd.arg("--git-dir").arg(&self.repo);
        cmd
    }

    fn run(
        &self,
        cmd: Command,
        what: &str,
        watch: Option<Watch>,
        stdout_cap: usize,
    ) -> Result<Vec<u8>, GitError> {
        let mut job = Supervised::spawn(cmd, self.deadline, watch)?;
        drop(job.stdin.take());
        let mut out = Vec::new();
        if let Some(stdout) = job.stdout.take() {
            stdout
                .take(stdout_cap as u64 + 1)
                .read_to_end(&mut out)
                .map_err(|e| failed(messages::git_reading(what, &e)))?;
        }
        if out.len() > stdout_cap {
            return Err(failed(messages::git_output_cap(what, stdout_cap)));
        }
        job.finish(what)?;
        Ok(out)
    }

    fn fetch(&self) -> Result<(), GitError> {
        let mut cmd = self.in_repo();
        cmd.args([
            "fetch",
            "--quiet",
            "--depth=1",
            "--no-tags",
            "--no-recurse-submodules",
            "--",
        ])
        .arg(self.request.url)
        .arg(self.request.commit);
        let objects = self.repo.join("objects");
        let max = self.request.limits.compressed_bytes;
        let watch = Watch {
            dir: objects.clone(),
            max,
        };
        self.run(cmd, "fetch", Some(watch), 4096)?;
        if dir_size(&objects) > max {
            return Err(download_limit(max));
        }
        Ok(())
    }

    fn check_commit(&self) -> Result<(), GitError> {
        let mut cmd = self.in_repo();
        cmd.args(["rev-parse", "--verify", "--quiet", "--end-of-options"])
            .arg(format!("{}^{{commit}}", self.request.commit));
        let out = self.run(cmd, "rev-parse", None, 256)?;
        if String::from_utf8_lossy(&out).trim() != self.request.commit {
            return Err(failed(messages::SyncPhrase::GitCommitDiffers.as_static()));
        }
        Ok(())
    }

    fn list_tree(&self) -> Result<Vec<Entry>, GitError> {
        let mut cmd = self.in_repo();
        cmd.args([
            "ls-tree",
            "-r",
            "-z",
            "-l",
            "--full-tree",
            "--end-of-options",
        ])
        .arg(self.request.commit);
        let cap = self.request.limits.entries.saturating_mul(1200) + 1024;
        let out = self.run(cmd, "ls-tree", None, cap)?;
        parse_tree(&out, self.request.limits)
    }

    fn export(&self, entries: &[Entry], staged: &mut StagedTree) -> Result<(), GitError> {
        let mut cmd = self.in_repo();
        cmd.args(["cat-file", "--batch"]);
        let mut job = Supervised::spawn(cmd, self.deadline, None)?;
        let mut stdin = job.stdin.take();
        let request = entries.iter().fold(String::new(), |mut acc, e| {
            acc.push_str(&e.oid);
            acc.push('\n');
            acc
        });
        // The writer runs apart from the reader, or both could block on a full pipe.
        let feeder = thread::spawn(move || {
            if let Some(pipe) = stdin.as_mut() {
                let _ = pipe.write_all(request.as_bytes());
            }
        });
        let stdout = job
            .stdout
            .take()
            .ok_or_else(|| failed(messages::SyncPhrase::GitNoOutput.as_static()))?;
        let mut reader = BufReader::new(stdout);
        let mut remaining = self.request.limits.expanded_bytes;
        let mut result = Ok(());
        for entry in entries {
            result = copy_blob(&mut reader, entry, &mut remaining, staged);
            if result.is_err() {
                break;
            }
        }
        drop(reader);
        let _ = feeder.join();
        result?;
        job.finish("cat-file")
    }
}

/// One file of the commit.
struct Entry {
    path: String,
    oid: String,
    size: u64,
    executable: bool,
}

/// Read the `ls-tree -r -z -l` listing. Sizes are summed here, so the commit is
/// refused for expanding past the limit before a single blob is read.
fn parse_tree(out: &[u8], limits: Limits) -> Result<Vec<Entry>, GitError> {
    let max_entries = limits.entries;
    let mut total = 0u64;
    let mut entries = Vec::new();
    for record in out.split(|&b| b == 0).filter(|r| !r.is_empty()) {
        if entries.len() >= max_entries {
            return Err(limit(messages::git_too_many_files(max_entries)));
        }
        let tab = record
            .iter()
            .position(|&b| b == b'\t')
            .ok_or_else(|| failed(messages::SyncPhrase::GitLsTreeLine.as_static()))?;
        let path = String::from_utf8(record[tab + 1..].to_vec())
            .map_err(|_| failed(messages::SyncPhrase::GitPathNotUtf8.as_static()))?;
        let meta = std::str::from_utf8(&record[..tab])
            .map_err(|_| failed(messages::SyncPhrase::GitLsTreeLine.as_static()))?;
        // The size column is padded with spaces; a submodule shows `-`.
        let mut fields = meta.split_whitespace();
        let (Some(mode), Some(kind), Some(oid), Some(size), None) = (
            fields.next(),
            fields.next(),
            fields.next(),
            fields.next(),
            fields.next(),
        ) else {
            return Err(failed(messages::SyncPhrase::GitLsTreeLine.as_static()));
        };
        let shown = &path;
        let executable = match (mode, kind) {
            ("100644", "blob") => false,
            ("100755", "blob") => true,
            ("120000", _) => return Err(failed(messages::git_symlink(shown))),
            ("160000", _) => return Err(failed(messages::git_submodule(shown))),
            _ => return Err(failed(messages::git_mode(shown, mode))),
        };
        if oid.len() != 40 || !oid.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
            return Err(failed(messages::SyncPhrase::GitLsTreeOid.as_static()));
        }
        let size: u64 = size
            .parse()
            .map_err(|_| failed(messages::SyncPhrase::GitLsTreeSize.as_static()))?;
        total = total.saturating_add(size);
        if total > limits.expanded_bytes {
            return Err(limit(messages::git_expands(limits.expanded_bytes)));
        }
        entries.push(Entry {
            path,
            oid: oid.to_owned(),
            size,
            executable,
        });
    }
    Ok(entries)
}

/// Read one `cat-file --batch` reply and write the blob into the staged tree.
fn copy_blob(
    reader: &mut impl BufRead,
    entry: &Entry,
    remaining: &mut u64,
    staged: &mut StagedTree,
) -> Result<(), GitError> {
    let mut header = Vec::new();
    reader
        .by_ref()
        .take(MAX_HEADER_BYTES)
        .read_until(b'\n', &mut header)
        .map_err(|e| failed(messages::git_cat_file_read(&e)))?;
    let header = header
        .strip_suffix(b"\n")
        .and_then(|h| std::str::from_utf8(h).ok())
        .ok_or_else(|| failed(messages::SyncPhrase::GitCatFileHeader.as_static()))?;
    let mut fields = header.split(' ');
    let (Some(oid), Some("blob"), Some(size), None) =
        (fields.next(), fields.next(), fields.next(), fields.next())
    else {
        return Err(failed(messages::git_object_missing(&entry.oid)));
    };
    let size: u64 = size
        .parse()
        .map_err(|_| failed(messages::SyncPhrase::GitCatFileSize.as_static()))?;
    if oid != entry.oid {
        return Err(failed(messages::SyncPhrase::GitCatFileObject.as_static()));
    }
    if size != entry.size || size > *remaining {
        return Err(failed(messages::SyncPhrase::GitSizeDiffers.as_static()));
    }
    *remaining -= size;
    let mut body = reader.by_ref().take(size);
    staged.write_file(&entry.path, &mut body, entry.executable)?;
    let mut newline = [0u8; 1];
    if body.limit() != 0 || reader.read_exact(&mut newline).is_err() || newline != *b"\n" {
        return Err(failed(messages::SyncPhrase::GitEndedEarly.as_static()));
    }
    Ok(())
}

/// A directory whose size is watched while a command runs.
struct Watch {
    dir: PathBuf,
    max: u64,
}

/// Bytes in the files under `dir`, counting at most `MAX_WATCHED_NODES` entries.
fn dir_size(dir: &Path) -> u64 {
    const MAX_WATCHED_NODES: usize = 100_000;
    let mut total = 0u64;
    let mut seen = 0usize;
    let mut stack = vec![dir.to_path_buf()];
    while let Some(path) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(&path) else {
            continue;
        };
        for entry in entries.flatten() {
            seen += 1;
            if seen > MAX_WATCHED_NODES {
                return u64::MAX;
            }
            let Ok(meta) = entry.metadata() else { continue };
            if meta.is_dir() {
                stack.push(entry.path());
            } else {
                total = total.saturating_add(meta.len());
            }
        }
    }
    total
}

const KILLED_TIME: u8 = 1;
const KILLED_SIZE: u8 = 2;

/// A running `git` with a watchdog. The watchdog kills the whole process group
/// at the deadline or when the watched directory passes its limit.
struct Supervised {
    stdin: Option<ChildStdin>,
    stdout: Option<ChildStdout>,
    stderr: Option<JoinHandle<Vec<u8>>>,
    watchdog: Option<JoinHandle<Option<Contained>>>,
    done: Arc<AtomicBool>,
    killed: Arc<AtomicU8>,
    deadline: Instant,
    /// The size limit of the watched directory, for the error text.
    watched_max: u64,
}

impl Supervised {
    fn spawn(mut cmd: Command, deadline: Instant, watch: Option<Watch>) -> Result<Self, GitError> {
        cmd.stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        let mut child = Contained::spawn(&mut cmd).map_err(|e| failed(messages::git_spawn(&e)))?;
        let watched_max = watch.as_ref().map_or(0, |w| w.max);
        let stdin = child.child_mut().stdin.take();
        let stdout = child.child_mut().stdout.take();
        let stderr = child.child_mut().stderr.take();
        let done = Arc::new(AtomicBool::new(false));
        let killed = Arc::new(AtomicU8::new(0));
        let (flag, why) = (Arc::clone(&done), Arc::clone(&killed));
        let watchdog = thread::spawn(move || {
            let mut tick = 0u32;
            loop {
                if flag.load(Ordering::SeqCst) {
                    return Some(child);
                }
                let reason = if Instant::now() >= deadline {
                    KILLED_TIME
                } else if tick.is_multiple_of(4)
                    && watch.as_ref().is_some_and(|w| dir_size(&w.dir) > w.max)
                {
                    KILLED_SIZE
                } else {
                    0
                };
                if reason != 0 {
                    why.store(reason, Ordering::SeqCst);
                    child.kill_tree();
                    return None;
                }
                tick = tick.wrapping_add(1);
                thread::sleep(Duration::from_millis(25));
            }
        });
        let stderr = thread::spawn(move || {
            let mut kept = Vec::new();
            if let Some(mut pipe) = stderr {
                let _ = (&mut pipe).take(MAX_STDERR_BYTES).read_to_end(&mut kept);
                // Keep reading so a chatty child never blocks on a full pipe.
                let _ = io::copy(&mut pipe, &mut io::sink());
            }
            kept
        });
        Ok(Self {
            stdin,
            stdout,
            stderr: Some(stderr),
            watchdog: Some(watchdog),
            done,
            killed,
            deadline,
            watched_max,
        })
    }

    /// Stop the watchdog and take the process back, if it was not killed.
    fn stop_watchdog(&mut self) -> Option<Contained> {
        self.done.store(true, Ordering::SeqCst);
        self.watchdog.take()?.join().ok().flatten()
    }

    /// Wait for a normal exit and turn failure into an error that names `what`.
    fn finish(mut self, what: &str) -> Result<(), GitError> {
        drop(self.stdin.take());
        drop(self.stdout.take());
        let child = self.stop_watchdog();
        let why = match self.killed.load(Ordering::SeqCst) {
            KILLED_TIME => Some(messages::git_timed_out(what)),
            KILLED_SIZE => return Err(download_limit(self.watched_max)),
            _ => None,
        };
        if let Some(why) = why {
            return Err(failed(why));
        }
        let mut child = child.ok_or_else(|| failed(messages::git_stopped(what)))?;
        let status = loop {
            match child.has_exited() {
                Ok(true) => {
                    break child
                        .reap()
                        .map_err(|e| failed(messages::git_waiting(what, &e)))?;
                }
                Ok(false) if Instant::now() < self.deadline => thread::sleep(POLL),
                Ok(false) => {
                    child.kill_tree();
                    return Err(failed(messages::git_timed_out(what)));
                }
                Err(e) => {
                    child.kill_tree();
                    return Err(failed(messages::git_waiting(what, &e)));
                }
            }
        };
        let text = self
            .stderr
            .take()
            .and_then(|h| h.join().ok())
            .unwrap_or_default();
        check_status(what, status, &text)
    }
}

impl Drop for Supervised {
    fn drop(&mut self) {
        drop(self.stdin.take());
        drop(self.stdout.take());
        if let Some(child) = self.stop_watchdog() {
            child.kill_tree();
        }
    }
}

fn check_status(what: &str, status: ExitStatus, stderr: &[u8]) -> Result<(), GitError> {
    if status.success() {
        return Ok(());
    }
    let text = String::from_utf8_lossy(stderr).trim().to_owned();
    Err(failed(messages::git_exit(what, &status, &text)))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Removes the file it names when dropped, even if the test panics.
    #[cfg(unix)]
    struct RemoveOnDrop(PathBuf);

    #[cfg(unix)]
    impl Drop for RemoveOnDrop {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }

    #[cfg(unix)]
    #[test]
    fn when_every_path_entry_is_rejected_git_is_not_taken_from_the_working_directory() {
        use std::os::unix::fs::PermissionsExt;
        // The working directory is outside the project. `.` and a missing
        // directory are both rejected, which leaves nothing to search.
        let cwd = std::env::current_dir().unwrap();
        let planted = cwd.join("git");
        assert!(!planted.exists(), "a file named git is already here");
        std::fs::write(&planted, b"#!/bin/sh\n").unwrap();
        let _cleanup = RemoveOnDrop(planted.clone());
        std::fs::set_permissions(&planted, std::fs::Permissions::from_mode(0o755)).unwrap();
        let project = tempfile::tempdir().unwrap();
        let path = std::env::join_paths([Path::new("."), Path::new("/no/such/dir")]).unwrap();
        assert_eq!(find_trusted("git", Some(&path), project.path()), None);
    }

    #[test]
    fn tree_listing_refuses_links_and_submodules() {
        let oid = "a".repeat(40);
        for (mode, kind, word) in [
            ("120000", "blob", "symbolic link"),
            ("160000", "commit", "submodule"),
            ("100664", "blob", "unsupported mode"),
        ] {
            let record = format!("{mode} {kind} {oid}      0\tx/y\0");
            let Err(GitError::Failed(msg)) = parse_tree(record.as_bytes(), Limits::default())
            else {
                panic!("{mode} was accepted");
            };
            assert!(msg.contains(word), "{msg}");
        }
    }

    #[test]
    fn tree_listing_reads_modes_and_sizes_and_stops_at_the_entry_limit() {
        let oid = "b".repeat(40);
        let two = format!("100644 blob {oid}      7\ta.txt\0100755 blob {oid}     12\tbin/run\0");
        let few = |entries| Limits {
            entries,
            ..Limits::default()
        };
        let entries = parse_tree(two.as_bytes(), few(2)).unwrap();
        let got: Vec<(&str, bool, u64)> = entries
            .iter()
            .map(|e| (e.path.as_str(), e.executable, e.size))
            .collect();
        assert_eq!(got, vec![("a.txt", false, 7), ("bin/run", true, 12)]);
        assert!(matches!(
            parse_tree(two.as_bytes(), few(1)),
            Err(GitError::Limit(_))
        ));
    }

    #[test]
    fn tree_listing_adds_sizes_before_any_blob_is_read() {
        let oid = "c".repeat(40);
        let two = format!("100644 blob {oid}    600\ta\0100644 blob {oid}    600\tb\0");
        let limits = Limits {
            expanded_bytes: 1000,
            ..Limits::default()
        };
        assert!(matches!(
            parse_tree(two.as_bytes(), limits),
            Err(GitError::Limit(_))
        ));
    }

    /// What a stand-in `git` sees: its environment lines, then its arguments.
    #[cfg(unix)]
    fn probe() -> (Vec<String>, Vec<String>) {
        use std::os::unix::fs::PermissionsExt;
        let dir = tempfile::tempdir().unwrap();
        let script = dir.path().join("git");
        std::fs::write(
            &script,
            "#!/bin/sh\nenv\necho --ARGS--\nfor a in \"$@\"; do echo \"$a\"; done\n",
        )
        .unwrap();
        std::fs::set_permissions(&script, std::fs::Permissions::from_mode(0o755)).unwrap();
        let work = dir.path().join("work");
        std::fs::create_dir_all(work.join("home")).unwrap();
        let request = Request {
            git: &script,
            url: "https://git.test/repo",
            commit: &"a".repeat(40),
            allow_local: false,
            timeout: Duration::from_secs(30),
            limits: Limits::default(),
            confinement: None,
        };
        let git = Git {
            request: &request,
            repo: work.join("repo"),
            work,
            deadline: Instant::now() + Duration::from_secs(30),
        };
        let out = git.run(git.in_repo(), "probe", None, 1 << 16).unwrap();
        let text = String::from_utf8(out).unwrap();
        let (env, args) = text.split_once("--ARGS--\n").unwrap();
        let lines = |s: &str| s.lines().map(str::to_owned).collect();
        (lines(env), lines(args))
    }

    #[cfg(unix)]
    #[test]
    fn git_runs_with_a_cleared_environment_and_no_user_config() {
        let (env, _) = probe();
        let names: Vec<&str> = env
            .iter()
            .filter_map(|l| l.split_once('=').map(|(k, _)| k))
            .collect();
        let allowed = [
            "HOME",
            "XDG_CONFIG_HOME",
            "USERPROFILE",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_SYSTEM",
            "GIT_CONFIG_NOSYSTEM",
            "GIT_TERMINAL_PROMPT",
            "GIT_ALLOW_PROTOCOL",
            "GIT_NO_REPLACE_OBJECTS",
            "GIT_OPTIONAL_LOCKS",
            "LC_ALL",
            // The shell adds these itself.
            "PWD",
            "SHLVL",
            "_",
            "OLDPWD",
        ];
        let extra: Vec<&&str> = names
            .iter()
            .filter(|n| !allowed.contains(n) && !PASS_THROUGH.contains(n))
            .collect();
        assert!(extra.is_empty(), "unexpected variables: {extra:?}");
        for line in [
            "GIT_TERMINAL_PROMPT=0",
            "GIT_CONFIG_GLOBAL=/dev/null",
            "GIT_ALLOW_PROTOCOL=https",
        ] {
            assert!(env.iter().any(|l| l == line), "{line} missing in {env:?}");
        }
    }

    #[cfg(unix)]
    #[test]
    fn git_gets_only_https_and_no_hooks_helpers_or_submodules() {
        let (_, args) = probe();
        for want in [
            "protocol.allow=never",
            "protocol.https.allow=always",
            "credential.helper=",
            "core.fsmonitor=false",
            "fetch.recurseSubmodules=false",
            "http.followRedirects=false",
            "transfer.unpackLimit=1",
            "transfer.fsckObjects=true",
        ] {
            assert!(args.iter().any(|a| a == want), "{want} missing in {args:?}");
        }
        assert!(
            args.iter()
                .any(|a| a.starts_with("core.hooksPath=") && a.ends_with("/nohooks")),
            "{args:?}"
        );
        assert!(
            !args.iter().any(|a| a.starts_with("protocol.file")),
            "{args:?}"
        );
    }

    #[cfg(unix)]
    #[test]
    fn a_command_past_its_deadline_is_killed() {
        let mut cmd = Command::new("/bin/sleep");
        cmd.arg("30");
        let started = Instant::now();
        let mut job =
            Supervised::spawn(cmd, Instant::now() + Duration::from_millis(200), None).unwrap();
        drop(job.stdin.take());
        let err = job.finish("sleep").unwrap_err();
        assert!(
            matches!(&err, GitError::Failed(m) if m.contains("timed out")),
            "{err:?}"
        );
        assert!(started.elapsed() < Duration::from_secs(10));
    }
}
