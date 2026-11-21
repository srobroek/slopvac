//! The plugin launcher: resource limits and, on Linux, a child subreaper
//! (threat model P5, P6 and NEW-3).
//!
//! A limit for a child process has to be set between `fork` and `exec`, and
//! the standard library offers that step only through the `unsafe`
//! `pre_exec`, which this workspace forbids. So on Unix the host starts the
//! launcher, a mode of the `slopvac` binary itself, and the launcher sets the
//! limits on itself with `setrlimit` before the plugin starts. The plugin
//! inherits them and cannot raise them: each hard limit is set too.
//!
//! - CPU time: SIGXCPU at the soft limit, SIGKILL one second later.
//! - Open files, and file size.
//! - Core files: none.
//! - Memory, on Linux only: the data limit, which covers every private
//!   writable mapping. macOS enforces no memory limit (residual R2).
//!
//! No process limit is set. `RLIMIT_NPROC` counts every process of the user,
//! not the plugin's, so any value either does nothing or breaks the plugin on
//! a busy machine. The process group kill and the wall-clock cap end a fork
//! loop (R2).
//!
//! On Linux the launcher also marks itself a child subreaper and stays as the
//! parent of the plugin. A descendant whose parent exits is reparented to the
//! launcher rather than to init, so the host's walk still finds it below the
//! stopped group leader. When the plugin exits, the launcher kills and reaps
//! what is left below it, then exits with the plugin's status: a descendant
//! reparented to init after that would be out of every walk's reach.
//!
//! Only an exit of the launcher confirms that cleanup. The launcher relays a
//! plugin that a signal ended as exit code 128 plus the signal number, and
//! refuses tracing, so no other process of the user can make it exit. If the
//! cleanup cannot account for every child within its time (two seconds), the
//! launcher kills itself with SIGKILL. The host reports a teardown incomplete
//! whenever it finds the launcher ended by a signal it did not send, before
//! or during its walk: a plugin that kills its launcher, with any signal,
//! gets the same report. Elsewhere the launcher replaces itself with the
//! plugin, which keeps its process id.
//!
//! The launcher runs with an empty environment. The plugin's variables reach
//! it under a prefix and it passes them on without the prefix, so a variable
//! such as `LD_PRELOAD` that a manifest names applies to the plugin and never
//! runs code in the launcher before the limits are set.

use std::ffi::{OsStr, OsString};
#[cfg(unix)]
use std::path::Path;
use std::path::PathBuf;
#[cfg(unix)]
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

use crate::messages::host::{self as messages, HostPhrase, HostText};

/// The first argument that selects launcher mode.
pub const FLAG: &str = "--slopvac-plugin-launcher";
/// Prefix of the variables that carry the plugin's environment.
#[cfg(unix)]
const ENV_PREFIX: &str = "SLOPVAC_PLUGIN_ENV_";

/// Whether [`intercept`] has run in this process.
static INSTALLED: AtomicBool = AtomicBool::new(false);

/// Why the host cannot name its launcher.
#[derive(Debug, thiserror::Error)]
pub(crate) enum LaunchError {
    /// The running program never called [`intercept`], so a child started
    /// through it would be the program itself, not the launcher.
    #[error("{}", HostPhrase::NotInstalled.as_static())]
    NotInstalled,
    /// The OS cannot name the running executable.
    #[error("{}", messages::current_exe_failed(.0))]
    CurrentExe(#[source] std::io::Error),
}

/// A launcher result; the error defaults to [`LaunchError`].
pub(crate) type Result<T, E = LaunchError> = std::result::Result<T, E>;

/// Which program the host starts as the launcher.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub enum Launcher {
    /// The running executable, which must call [`intercept`] first thing in
    /// `main`. Production uses this. A process that never called
    /// [`intercept`] gets [`PluginError::LauncherNotInstalled`](crate::PluginError::LauncherNotInstalled)
    /// and nothing starts.
    // STUB(slopvac-8l4.9.24): the `slopvac` binary does not call `intercept`
    // yet, so a plugin it starts this way fails closed with
    // `launcher-not-installed`.
    #[default]
    CurrentExe,
    /// Another program that calls [`intercept`], such as this package's
    /// `slopvac-plugin-launcher`.
    Program(PathBuf),
}

impl Launcher {
    /// The absolute path of the program.
    ///
    /// # Errors
    ///
    /// [`LaunchError::NotInstalled`] for [`Launcher::CurrentExe`] when the
    /// process never called [`intercept`]; nothing is spawned then.
    pub(crate) fn path(&self) -> Result<PathBuf> {
        match self {
            Self::CurrentExe if !INSTALLED.load(Ordering::Acquire) => {
                Err(LaunchError::NotInstalled)
            }
            Self::CurrentExe => std::env::current_exe().map_err(LaunchError::CurrentExe),
            Self::Program(p) => Ok(p.clone()),
        }
    }
}

/// The limits the launcher sets, from the host's [`RunCaps`](crate::RunCaps).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) struct Limits {
    /// CPU time in whole seconds, rounded up.
    pub(crate) cpu_secs: u64,
    /// Open files.
    pub(crate) open_files: u64,
    /// Largest file the plugin may write, in bytes.
    pub(crate) file_size: u64,
    /// Data limit in bytes, set on Linux only.
    pub(crate) memory: u64,
}

/// What a launcher invocation asks for.
#[derive(Debug, PartialEq, Eq)]
struct Plan {
    limits: Limits,
    /// How long the Linux launcher may spend clearing what the plugin left.
    sweep: Duration,
    program: PathBuf,
    args: Vec<OsString>,
}

/// The host's command that starts `program` through the launcher at
/// `launcher` under `limits`, with `env` as the plugin's whole environment.
/// On Linux the launcher gets `sweep` to clear what the plugin leaves behind.
#[cfg(unix)]
pub(crate) fn command<'a>(
    launcher: &Path,
    limits: Limits,
    sweep: Duration,
    program: &Path,
    args: &[String],
    env: impl IntoIterator<Item = (&'a str, &'a str)>,
) -> Command {
    let mut cmd = Command::new(launcher);
    cmd.arg(FLAG)
        .arg(format!("cpu={}", limits.cpu_secs))
        .arg(format!("nofile={}", limits.open_files))
        .arg(format!("fsize={}", limits.file_size))
        .arg(format!("data={}", limits.memory))
        .arg(format!("sweep={}", sweep.as_millis()))
        .arg("--")
        .arg(program)
        .args(args)
        .env_clear();
    for (k, v) in env {
        cmd.env(format!("{ENV_PREFIX}{k}"), v);
    }
    cmd
}

/// Run as the plugin launcher if the first argument is [`FLAG`], and never
/// return then. Otherwise return at once.
///
/// A binary that hosts plugins calls this first thing in `main`, before it
/// reads its arguments, its environment or any configuration. On a setup
/// failure the launcher prints one line to standard error and exits with
/// status 127, so the plugin fails to start.
pub fn intercept() {
    INSTALLED.store(true, Ordering::Release);
    let mut argv = std::env::args_os();
    let _ = argv.next();
    if argv.next().as_deref() != Some(OsStr::new(FLAG)) {
        return;
    }
    let rest: Vec<OsString> = argv.collect();
    match parse(&rest) {
        Ok(plan) => run(&plan),
        Err(m) => fail(&m),
    }
}

/// The usage line of the launcher program, which the plugin host alone starts.
#[doc(hidden)]
#[must_use]
pub fn usage() -> String {
    HostText::LaunchUsage {
        flag: FLAG.to_owned(),
    }
    .to_string()
}

fn fail(msg: &str) -> ! {
    eprintln!(
        "{}",
        HostText::LaunchFailure {
            message: msg.to_owned()
        }
    );
    std::process::exit(127)
}

/// Parse `cpu=N nofile=N fsize=N data=N sweep=MS -- PROGRAM ARGS...`, all or
/// nothing.
fn parse(args: &[OsString]) -> Result<Plan, String> {
    let [cpu, nofile, fsize, data, sweep, sep, program, rest @ ..] = args else {
        return Err(HostPhrase::MalformedArgs.as_static().into());
    };
    let num = |a: &OsString, key: &str| {
        a.to_str()
            .and_then(|s| s.strip_prefix(key))
            .and_then(|s| s.strip_prefix('='))
            .filter(|s| !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()))
            .and_then(|s| s.parse::<u64>().ok())
            .ok_or_else(|| {
                HostText::MalformedArg {
                    key: key.to_owned(),
                }
                .to_string()
            })
    };
    let limits = Limits {
        cpu_secs: num(cpu, "cpu")?,
        open_files: num(nofile, "nofile")?,
        file_size: num(fsize, "fsize")?,
        memory: num(data, "data")?,
    };
    let sweep = Duration::from_millis(num(sweep, "sweep")?);
    if sep != "--" {
        return Err(HostPhrase::MalformedArgs.as_static().into());
    }
    let program = PathBuf::from(program);
    // An absolute path is never looked up through `PATH`.
    if !program.is_absolute() {
        return Err(HostPhrase::ProgramNotAbsolute.as_static().into());
    }
    Ok(Plan {
        limits,
        sweep,
        program,
        args: rest.to_vec(),
    })
}

#[cfg(not(unix))]
fn run(_plan: &Plan) -> ! {
    fail(HostPhrase::UnixOnly.as_static())
}

#[cfg(unix)]
fn run(plan: &Plan) -> ! {
    if let Err(m) = apply(&plan.limits) {
        fail(&m);
    }
    let mut cmd = Command::new(&plan.program);
    cmd.args(&plan.args).env_clear();
    for (k, v) in std::env::vars_os() {
        if let Some(name) = k.to_str().and_then(|k| k.strip_prefix(ENV_PREFIX)) {
            cmd.env(name, v);
        }
    }
    start(cmd, plan.sweep)
}

/// Set the limits on this process, soft and hard, never above a hard limit
/// already in place.
#[cfg(unix)]
fn apply(l: &Limits) -> Result<(), String> {
    use rustix::process::{Resource, Rlimit, getrlimit, setrlimit};
    let set = |resource: Resource, name: &str, soft: u64, hard: u64| {
        let (soft, hard) = capped(soft, hard, getrlimit(resource).maximum);
        let new = Rlimit {
            current: Some(soft),
            maximum: Some(hard),
        };
        setrlimit(resource, new).map_err(|e| {
            HostText::SetLimit {
                name: name.to_owned(),
                error: e.to_string(),
            }
            .to_string()
        })
    };
    set(Resource::Core, HostPhrase::LimitCore.as_static(), 0, 0)?;
    set(
        Resource::Cpu,
        HostPhrase::LimitCpu.as_static(),
        l.cpu_secs,
        l.cpu_secs.saturating_add(1),
    )?;
    set(
        Resource::Nofile,
        HostPhrase::LimitOpenFile.as_static(),
        l.open_files,
        l.open_files,
    )?;
    set(
        Resource::Fsize,
        HostPhrase::LimitFileSize.as_static(),
        l.file_size,
        l.file_size,
    )?;
    #[cfg(target_os = "linux")]
    set(
        Resource::Data,
        HostPhrase::LimitMemory.as_static(),
        l.memory,
        l.memory,
    )?;
    Ok(())
}

/// The soft and hard values to set: the wanted ones, lowered to the hard
/// limit already in place (`None`: unlimited), which no process can raise.
#[cfg(unix)]
fn capped(soft: u64, hard: u64, ceiling: Option<u64>) -> (u64, u64) {
    let cap = |v: u64| ceiling.map_or(v, |c| v.min(c));
    (cap(soft), cap(hard))
}

/// Become the plugin; its process id and group stay the launcher's.
#[cfg(all(unix, not(target_os = "linux")))]
fn start(mut cmd: Command, _sweep: Duration) -> ! {
    use std::os::unix::process::CommandExt;
    let err = cmd.exec();
    fail(
        &HostText::RunFailed {
            error: err.to_string(),
        }
        .to_string(),
    )
}

/// Start the plugin as a child, reap until it exits, clear what is left
/// below the launcher within `sweep`, then exit with the plugin's status.
#[cfg(target_os = "linux")]
fn start(mut cmd: Command, sweep: Duration) -> ! {
    use rustix::process::{DumpableBehavior, getpid, set_child_subreaper, set_dumpable_behavior};
    if let Err(e) = set_child_subreaper(Some(getpid())) {
        fail(
            &HostText::Subreaper {
                error: e.to_string(),
            }
            .to_string(),
        );
    }
    // No process of the same user may attach to the launcher and fake its
    // exit; the plugin regains the default with its own `exec`.
    if let Err(e) = set_dumpable_behavior(DumpableBehavior::NotDumpable) {
        fail(
            &HostText::RefuseTracing {
                error: e.to_string(),
            }
            .to_string(),
        );
    }
    let child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => fail(
            &HostText::RunFailed {
                error: e.to_string(),
            }
            .to_string(),
        ),
    };
    let plugin = rustix::process::Pid::from_child(&child);
    // The launcher reaps through `wait`; dropping the handle neither waits nor kills.
    drop(child);
    linux::release_stdio();
    let status = linux::reap(plugin);
    if !linux::sweep(sweep) {
        // Something below the launcher survived the cleanup, or could not be
        // seen. Only an exit confirms a cleanup, so the host reports a
        // launcher that a signal ended as an incomplete teardown.
        let _ = rustix::process::kill_process(getpid(), rustix::process::Signal::KILL);
    }
    linux::relay(status)
}

#[cfg(target_os = "linux")]
mod linux {
    //! The supervising launcher.
    //!
    //! The launcher is single-threaded, and only it reaps its children: it
    //! never ignores `SIGCHLD`, so the kernel reaps none of them on its
    //! behalf. A process that a scan shows as its child therefore keeps its
    //! id until the launcher reaps it, and the launcher signals such a
    //! process by id only between the scan and its next `wait`.

    use std::time::{Duration, Instant};

    use rustix::io::Errno;

    use crate::messages::host::HostText;
    use rustix::process::{Pid, Signal, WaitOptions, WaitStatus, getpid, kill_process, wait};

    use super::fail;

    /// Point the launcher's own standard streams at `/dev/null`, so that
    /// only the plugin and its descendants hold the host's pipes.
    pub(super) fn release_stdio() {
        let Ok(null) = std::fs::File::options()
            .read(true)
            .write(true)
            .open("/dev/null")
        else {
            return;
        };
        let _ = rustix::stdio::dup2_stdin(&null);
        let _ = rustix::stdio::dup2_stdout(&null);
        let _ = rustix::stdio::dup2_stderr(&null);
    }

    /// Reap children until the plugin exits, and return its status.
    /// Descendants reparented to the launcher that exit first are reaped too.
    pub(super) fn reap(plugin: Pid) -> WaitStatus {
        loop {
            match wait(WaitOptions::empty()) {
                Ok(Some((pid, status))) if pid == plugin => return status,
                Ok(_) | Err(Errno::INTR) => {}
                Err(e) => fail(
                    &HostText::LostPlugin {
                        error: e.to_string(),
                    }
                    .to_string(),
                ),
            }
        }
    }

    /// Kill and reap every child of the launcher until none is left, and
    /// return whether that happened within `within`. Each killed child's own
    /// children are reparented to the launcher, so the next round reaches
    /// them. Only `ECHILD` ends the sweep early: a child that the scan cannot
    /// read or the kill cannot reach keeps it going until the deadline.
    pub(super) fn sweep(within: Duration) -> bool {
        let me = getpid();
        let end = Instant::now() + within;
        loop {
            loop {
                match wait(WaitOptions::NOHANG) {
                    Ok(Some(_)) | Err(Errno::INTR) => {}
                    Ok(None) => break,
                    Err(Errno::CHILD) => return true,
                    Err(_) => return false,
                }
            }
            if Instant::now() >= end {
                return false;
            }
            // No `wait` runs between the scan and the kills.
            for pid in children(me) {
                let _ = kill_process(pid, Signal::KILL);
            }
            std::thread::sleep(Duration::from_millis(5));
        }
    }

    /// The children of `me`, from the parent ids in `/proc`.
    fn children(me: Pid) -> Vec<Pid> {
        let me = me.as_raw_nonzero().get().unsigned_abs();
        let Ok(dir) = std::fs::read_dir("/proc") else {
            return Vec::new();
        };
        dir.filter_map(|e| e.ok()?.file_name().to_str()?.parse::<u32>().ok())
            .filter(|&p| crate::process::proc_ppid(p).is_ok_and(|parent| parent == me))
            .filter_map(|p| i32::try_from(p).ok().and_then(Pid::from_raw))
            .collect()
    }

    /// Exit with the plugin's status: its exit code, or 128 plus the number
    /// of the signal that ended it. The launcher always exits, because only
    /// an exit tells the host that the cleanup finished.
    pub(super) fn relay(status: WaitStatus) -> ! {
        if let Some(code) = status.exit_status() {
            std::process::exit(code);
        }
        if let Some(sig) = status.terminating_signal() {
            std::process::exit(128 + sig);
        }
        std::process::exit(127)
    }
}
