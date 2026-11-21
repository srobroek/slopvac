//! Process groups, descendants and the environment allowlist.
//!
//! Each plugin has one teardown owner, a `Group`. A kill takes the group's
//! lock and runs only while the leader is unreaped. An unreaped leader, even a
//! zombie, keeps its process id, and a process group id stays in use while its
//! leader's id does, so neither number can name an unrelated process at kill
//! time. Only the waiter reaps the leader. It observes the exit without
//! reaping, tears the group down under the same lock, and reaps last.
//!
//! The host signals a process only when it knows which process the signal
//! reaches. That holds for the group and for the leader, which is signalled
//! by its own id too, since it may have moved to another group of its
//! session. No other group is ever signalled. A descendant outside the group
//! is signalled only through a Linux pidfd. Without one, a process id can
//! pass to an unrelated process between the snapshot and the signal, so the
//! host reports such a descendant in the [`Teardown`] and leaves it running.
//!
//! A teardown on Unix runs in three steps under that lock (threat model P5):
//!
//! 1. Stop the group and the leader with `SIGSTOP`. Nothing a helper does
//!    can delay or redirect these signals. A stopped process cannot fork,
//!    reap a child or exit on its own.
//! 2. Walk the process table for descendants that left the group: a process
//!    outside the group whose parent is stopped and is the leader, a member
//!    of the group or a descendant already held. On Linux the walk opens a
//!    pidfd for it, checks its parent through `/proc`, stops it and looks
//!    again, until a round finds nothing new. Once a held process shows as
//!    stopped in `/proc` and its pidfd shows no exit, the walk binds its
//!    children from the same table without another read, since a stopped
//!    process cannot fork. A tree that was static when the table was read
//!    thus costs two reads at any depth, and the deadline stays the bound.
//!    A process whose parent `/proc`
//!    does not confirm counts as gone only if its pidfd shows an exit, and
//!    one that a pidfd call fails on only if the call fails with `ESRCH`.
//!    The walk records every other one as escaped. Elsewhere it records
//!    every such descendant as escaped. The table comes from `/bin/ps`,
//!    never from `PATH`, run with a scrubbed environment, a deadline and an
//!    output limit, and parsed strictly. A well-formed row for a process
//!    that the kernel is releasing (state `X`) is left out: it can no longer
//!    fork or be signalled. A helper that fails, hangs or
//!    prints anything unexpected ends the walk, as do the deadline and a
//!    cap on held descendants, and the walk is then reported incomplete.
//! 3. Kill the held descendants, deepest first, then the group and the
//!    leader, whatever the walk found. A held descendant that the kill does
//!    not reach is recorded as escaped.
//!
//! No snapshot outlives the lock, and descendants are found only at kill time.
//! A stopped parent cannot fork, so a process that a pidfd names and that
//! still has the parent from the snapshot is the process from the snapshot.
//!
//! Residual risk R2: on macOS and any Unix without pidfds, a descendant that
//! left the group survives the teardown and is only reported. On Linux the
//! group leader is the launcher, a child subreaper (see
//! [`launch`](crate::launch)), so a descendant whose parent exited before the
//! walk is reparented to it and found. Elsewhere such a descendant is
//! reparented to init and not found at all.

use std::ffi::OsString;
use std::path::PathBuf;
use std::process::{Child, ExitStatus};
use std::sync::{Arc, Condvar, Mutex, MutexGuard, PoisonError, TryLockError};
use std::time::{Duration, Instant};

use crate::messages::host::HostText;

static LIVE: Mutex<Vec<Arc<Group>>> = Mutex::new(Vec::new());

/// How long one teardown may spend reading the process table.
const WALK_DEADLINE: Duration = Duration::from_secs(2);

fn lock<T>(m: &Mutex<T>) -> MutexGuard<'_, T> {
    m.lock().unwrap_or_else(PoisonError::into_inner)
}

/// Kill every plugin process group that is still running.
///
/// The binary's interrupt handling calls this, so no plugin outlives the host
/// (plugin-protocol.md section 3). It stops every group first, then tears
/// each one down through its `Group`, so it waits for a teardown in flight
/// and never signals a reaped leader's id.
///
/// Returns what the teardowns of those plugins left undone, for a
/// diagnostic: an empty [`Teardown`] means every process the walks found is
/// dead or dying.
///
/// This function is not async-signal-safe (CWE-479): it takes locks, waits on
/// a condition variable, allocates and starts `/bin/ps`. Never call it from a
/// raw signal handler. The handler should only set an atomic flag or write a
/// byte to a self-pipe, and an ordinary thread that watches for it calls this
/// function. A signal crate that runs handlers on its own thread does the same.
#[must_use = "report what the teardowns left running"]
pub fn kill_all_live() -> Teardown {
    let groups: Vec<Arc<Group>> = lock(&LIVE).clone();
    for g in &groups {
        g.freeze();
    }
    let mut left = Teardown::default();
    for g in &groups {
        g.kill();
        left.merge(g.teardown());
    }
    left
}

/// What the teardowns of a plugin left undone (threat model P5, residual R2).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Teardown {
    /// Ids of descendants outside the plugin's process group that the walk
    /// found but did not signal, because nothing binds them to their ids: on
    /// a Unix without pidfds every one of them; on Linux one whose pidfd did
    /// not open or could not signal it, or whose parent `/proc` did not
    /// confirm while the pidfd showed no exit. They, and anything they
    /// started, may still run.
    pub escaped: Vec<u32>,
    /// A walk ended early: the process table could not be read, or the
    /// deadline or the cap on held descendants was reached. On Linux, also
    /// a launcher that a signal ended before any kill from the host, or
    /// during the walk: its cleanup missed something, or the plugin or a
    /// descendant killed it. On Windows,
    /// `taskkill` did not exit with status 0; it does not run after the
    /// plugin answered `shutdown` and exited with status 0 without a kill.
    /// Descendants it did not reach may still run.
    pub incomplete: bool,
}

impl Teardown {
    /// Whether every walk finished and found nothing it had to leave running.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.escaped.is_empty() && !self.incomplete
    }

    fn merge(&mut self, other: Self) {
        for p in other.escaped {
            if !self.escaped.contains(&p) {
                self.escaped.push(p);
            }
        }
        self.incomplete |= other.incomplete;
    }
}

/// Where a teardown reads the process table. A test seam only.
///
/// `None` in [`HostConfig`](crate::HostConfig) means `/bin/ps` with a two
/// second deadline, which is what production uses; no lookup ever goes
/// through `PATH`. Tests point this at a script. The program runs exactly as
/// `/bin/ps` would: an environment of only `LC_ALL=C` and
/// `PATH=/usr/bin:/bin`, no input, the deadline and the output limit. It must
/// print what `ps -A -o pid=,ppid=,pgid=,stat=,lstart=` prints.
#[doc(hidden)]
#[derive(Debug, Clone)]
pub struct TableSource {
    /// Absolute path of the program.
    pub program: PathBuf,
    /// Its arguments.
    pub args: Vec<OsString>,
    /// How long one teardown may spend on the walk.
    pub deadline: Duration,
    /// Most descendants outside the group that one walk holds. Production
    /// holds up to 1,024.
    pub max_held: usize,
    /// Stands in for the pidfd of every descendant outside the group: each
    /// one is held and signalled through this hook, and none is opened, so
    /// the walk's handling of failed signals runs on any Unix. `None` in
    /// production.
    pub signals: Option<SignalHook>,
}

/// Which signal a [`SignalHook`] is asked to send.
#[doc(hidden)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HookSignal {
    /// `SIGSTOP`.
    Stop,
    /// `SIGKILL`.
    Kill,
}

/// Sends a signal to a process id and returns the raw `errno` on failure.
#[doc(hidden)]
#[derive(Clone)]
pub struct SignalHook(pub Arc<dyn Fn(u32, HookSignal) -> Result<(), i32> + Send + Sync>);

impl std::fmt::Debug for SignalHook {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("SignalHook")
    }
}

#[derive(Default)]
#[expect(
    clippy::struct_excessive_bools,
    reason = "independent facts about one teardown, not a state machine"
)]
struct State {
    /// How the reap of the leader went: its exit status, or why the wait
    /// failed. No kill runs once this is set.
    reaped: Option<Result<ExitStatus, String>>,
    /// A kill ran before the leader was reaped.
    forced: bool,
    /// The kill teardown ran. It runs once: what it found is killed and
    /// cannot fork, so another walk would find nothing new.
    killed: bool,
    /// What the teardowns so far left undone.
    left: Teardown,
    /// The plugin answered `shutdown` with `null`. Only Windows reads it.
    acknowledged: bool,
    /// The leader is reaped and the group unregistered.
    done: bool,
}

/// What a teardown does to the group after the descendants that left it.
#[derive(Clone, Copy)]
enum Then {
    Kill,
    Resume,
}

/// The single teardown owner of one plugin's process group.
pub(crate) struct Group {
    pid: u32,
    table: Option<TableSource>,
    state: Mutex<State>,
    done: Condvar,
}

impl Group {
    /// Track the group a new leader heads, and register it for [`kill_all_live`].
    pub(crate) fn register(pid: u32, table: Option<TableSource>) -> Arc<Self> {
        let g = Arc::new(Self {
            pid,
            table,
            state: Mutex::new(State::default()),
            done: Condvar::new(),
        });
        lock(&LIVE).push(Arc::clone(&g));
        g
    }

    /// Stop the group and the leader now, unless the leader is reaped or a
    /// teardown already holds the lock (that teardown stops them itself).
    fn freeze(&self) {
        let st = match self.state.try_lock() {
            Ok(st) => st,
            Err(TryLockError::Poisoned(p)) => p.into_inner(),
            Err(TryLockError::WouldBlock) => return,
        };
        if st.reaped.is_none() {
            stop_group(self.pid);
        }
    }

    /// Kill the group and the descendants that left it, unless the leader is
    /// reaped or a kill already ran.
    ///
    /// Blocks while another teardown or the reap is in flight.
    pub(crate) fn kill(&self) {
        let mut st = lock(&self.state);
        if st.reaped.is_none() {
            st.forced = true;
            self.kill_once(&mut st);
        }
    }

    /// Run the kill teardown unless it already ran. The caller holds the
    /// lock and keeps the leader unreaped.
    fn kill_once(&self, st: &mut State) {
        if !st.killed {
            st.killed = true;
            let left = tear_down(self.pid, self.table.as_ref(), Then::Kill);
            st.left.merge(left);
        }
    }

    /// Kill the descendants that left the group and let the group run on.
    ///
    /// `shutdown` calls this before the protocol exchange: a descendant that
    /// left the group is reparented when its parent exits, and the walk at
    /// the final kill no longer finds it.
    pub(crate) fn kill_strays(&self) {
        let mut st = lock(&self.state);
        if st.reaped.is_none() && !st.killed {
            let left = tear_down(self.pid, self.table.as_ref(), Then::Resume);
            st.left.merge(left);
        }
    }

    /// Whether a kill ran before the leader was reaped.
    pub(crate) fn forced(&self) -> bool {
        lock(&self.state).forced
    }

    /// What the teardowns so far left undone.
    pub(crate) fn teardown(&self) -> Teardown {
        lock(&self.state).left.clone()
    }

    /// The leader's exit status as text, once it is reaped.
    pub(crate) fn status(&self) -> Option<String> {
        lock(&self.state).reaped.as_ref().map(|r| match r {
            Ok(s) => s.to_string(),
            Err(e) => HostText::WaitFailed { error: e.clone() }.to_string(),
        })
    }

    /// The leader's exit status, once it is reaped, unless the wait failed.
    pub(crate) fn exit_status(&self) -> Option<ExitStatus> {
        lock(&self.state)
            .reaped
            .as_ref()
            .and_then(|r| r.as_ref().ok().copied())
    }

    /// Record that the plugin answered `shutdown` with `null`. Called
    /// before `exit` goes out, so before the leader exits on its own.
    pub(crate) fn acknowledge(&self) {
        lock(&self.state).acknowledged = true;
    }

    /// End the group after its leader exited: kill everything still in it
    /// while the leader holds its ids, reap the leader, then unregister.
    ///
    /// Called by the waiter only. A leader that has not exited yet is
    /// killed and then reaped. On Windows a graceful exit, an answered
    /// `shutdown` and then status 0 without a kill, skips the tree kill.
    pub(crate) fn finish(&self, leader: Leader) {
        {
            let mut st = lock(&self.state);
            #[cfg(unix)]
            self.kill_once(&mut st);
            #[cfg(not(unix))]
            if !st.killed {
                st.killed = true;
                let spare = graceful(st.acknowledged, st.forced, leader.exited_zero());
                let left = windows_teardown(spare, || taskkill(self.pid));
                st.left.merge(left);
            }
            st.reaped = Some(leader.reap());
        }
        lock(&LIVE).retain(|g| !std::ptr::eq(Arc::as_ptr(g), self));
        lock(&self.state).done = true;
        self.done.notify_all();
    }

    /// Wait up to `timeout` until the leader is reaped and the group unregistered.
    pub(crate) fn wait_done(&self, timeout: Duration) -> bool {
        let end = Instant::now() + timeout;
        let mut st = lock(&self.state);
        while !st.done {
            let left = end.saturating_duration_since(Instant::now());
            if left.is_zero() {
                return false;
            }
            st = self
                .done
                .wait_timeout(st, left)
                .unwrap_or_else(PoisonError::into_inner)
                .0;
        }
        true
    }
}

/// The plugin's top process, owned by the waiter: the launcher on Linux, the
/// plugin itself elsewhere.
pub(crate) struct Leader {
    child: Child,
    exited: Option<std::io::Result<ExitStatus>>,
}

impl Leader {
    pub(crate) fn new(child: Child) -> Self {
        Self {
            child,
            exited: None,
        }
    }

    /// Take the three standard pipes.
    pub(crate) fn take_pipes(
        &mut self,
    ) -> (
        Option<std::process::ChildStdin>,
        Option<std::process::ChildStdout>,
        Option<std::process::ChildStderr>,
    ) {
        (
            self.child.stdin.take(),
            self.child.stdout.take(),
            self.child.stderr.take(),
        )
    }

    /// Block until the leader exits, but leave it unreaped so its ids stay reserved.
    #[cfg(unix)]
    pub(crate) fn wait_exit(&mut self) {
        use rustix::io::Errno;
        use rustix::process::{WaitId, WaitIdOptions, waitid};
        let Some(pid) = unix::pid(self.child.id()) else {
            return;
        };
        let opts = WaitIdOptions::EXITED | WaitIdOptions::NOWAIT;
        loop {
            match waitid(WaitId::Pid(pid), opts) {
                Ok(Some(s)) if s.exited() || s.killed() || s.dumped() => return,
                Err(Errno::INTR) => {}
                // macOS also reports a stop under WEXITED (golang/go#19314).
                Ok(_) => std::thread::sleep(Duration::from_millis(20)),
                // Not waitable: `finish` then kills the still unreaped leader.
                Err(_) => return,
            }
        }
    }

    /// Block until the leader exits. The open process handle keeps its id reserved.
    #[cfg(not(unix))]
    pub(crate) fn wait_exit(&mut self) {
        self.exited = Some(self.child.wait());
    }

    /// Whether the leader has exited with status 0.
    #[cfg(not(unix))]
    fn exited_zero(&self) -> bool {
        matches!(&self.exited, Some(Ok(s)) if s.success())
    }

    /// Reap the leader and release its ids. Returns the exit status, or why
    /// the wait failed.
    fn reap(mut self) -> Result<ExitStatus, String> {
        let status = match self.exited.take() {
            Some(s) => s,
            None => self.child.wait(),
        };
        drop(self.child);
        status.map_err(|e| e.to_string())
    }
}

#[cfg(unix)]
fn stop_group(leader: u32) {
    use rustix::process::{Signal, kill_process, kill_process_group};
    if let Some(pid) = unix::pid(leader) {
        // An error means the group is already gone, or the leader left it.
        let _ = kill_process_group(pid, Signal::STOP);
        let _ = kill_process(pid, Signal::STOP);
    }
}

/// Tear down the group led by `leader`, which the caller keeps unreaped, and
/// return what it left undone.
///
/// The leader is signalled by its own id as well as through its group, since
/// it may have moved to another group of its session. No other group is
/// ever signalled.
#[cfg(unix)]
fn tear_down(leader: u32, table: Option<&TableSource>, then: Then) -> Teardown {
    use rustix::process::{Signal, kill_process, kill_process_group};

    /// Signals the group and the leader last, even if the walk unwinds.
    struct Last(rustix::process::Pid, Signal);
    impl Drop for Last {
        fn drop(&mut self) {
            let _ = kill_process_group(self.0, self.1);
            let _ = kill_process(self.0, self.1);
        }
    }

    let Some(pid) = unix::pid(leader) else {
        // Nothing was signalled, so nothing is known to be dead.
        return Teardown {
            escaped: Vec::new(),
            incomplete: true,
        };
    };
    stop_group(leader);
    let _last = Last(
        pid,
        match then {
            Then::Kill => Signal::KILL,
            Then::Resume => Signal::CONT,
        },
    );
    let within = table.map_or(WALK_DEADLINE, |t| t.deadline);
    #[cfg_attr(
        not(target_os = "linux"),
        expect(unused_mut, reason = "only the launcher's end is checked")
    )]
    let mut left = unix::walk(leader, table, Instant::now() + within).kill();
    // The host has sent the leader nothing but SIGSTOP and SIGCONT so far.
    // On Linux the leader is the launcher, which confirms its cleanup only by
    // exiting. A launcher that a signal ended, before this teardown or during
    // its walk, may have lost its orphans to init.
    #[cfg(target_os = "linux")]
    if unix::ended_by_signal(leader) {
        left.incomplete = true;
    }
    left
}

#[cfg(not(unix))]
fn stop_group(_leader: u32) {}

/// `taskkill /T /F` on the leader's tree. The leader's open handle keeps its
/// id reserved; the tree walk itself is `taskkill`'s (job objects:
/// `slopvac-8l4.18.8`).
#[cfg(not(unix))]
fn tear_down(pid: u32, _table: Option<&TableSource>, then: Then) -> Teardown {
    if matches!(then, Then::Resume) {
        return Teardown::default();
    }
    windows_teardown(false, || taskkill(pid))
}

/// Run `taskkill /T /F` on `pid` and return its exit code, or `None` if it
/// did not start, could not be watched or passed the deadline.
#[cfg(not(unix))]
fn taskkill(pid: u32) -> Option<i32> {
    use std::process::{Command, Stdio};
    let root = std::env::var_os("SystemRoot").unwrap_or_else(|| r"C:\Windows".into());
    let program = std::path::Path::new(&root)
        .join("System32")
        .join("taskkill.exe");
    let mut child = Command::new(program)
        .args(["/T", "/F", "/PID", &pid.to_string()])
        .env_clear()
        .env("SystemRoot", &root)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()?;
    let deadline = Instant::now() + WALK_DEADLINE;
    loop {
        match child.try_wait() {
            Ok(Some(status)) => return status.code(),
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(10)),
            // A wait error or the deadline.
            _ => break,
        }
    }
    let _ = child.kill();
    let _ = child.wait();
    None
}

/// Whether a leader's exit is graceful: the plugin answered `shutdown` with
/// `null` and the leader then exited with status 0 with no kill before it.
#[cfg(any(not(unix), test))]
fn graceful(acknowledged: bool, forced: bool, exited_zero: bool) -> bool {
    acknowledged && !forced && exited_zero
}

/// What a Windows teardown leaves; `taskkill` runs `taskkill /T /F` and
/// returns its exit code (`None`: it did not start, could not be watched or
/// passed the deadline).
///
/// After a `graceful` exit `taskkill` does not run and the teardown is
/// complete. Once the leader has exited, `taskkill` finds no tree, and
/// containing the leader's descendants then is the work of job objects
/// (residual risk, native Windows support: `slopvac-8l4.18.8`).
///
/// Any other teardown, a kill on a timeout, a failure, a drop or an
/// interrupt, is complete only if `taskkill` exits with status 0. Status
/// 128, "process not found", means the leader had exited, and its
/// descendants, if any, were out of `taskkill`'s reach.
#[cfg(any(not(unix), test))]
fn windows_teardown(graceful: bool, taskkill: impl FnOnce() -> Option<i32>) -> Teardown {
    Teardown {
        escaped: Vec::new(),
        incomplete: !graceful && taskkill() != Some(0),
    }
}

#[cfg(unix)]
mod unix {
    //! The descendant walk and its process-table helper.

    use std::collections::{HashMap, HashSet};
    use std::ffi::OsStr;
    use std::io::Read;
    use std::path::Path;
    use std::process::{Child, Command, Stdio};
    use std::time::{Duration, Instant};

    use rustix::process::{Pid, Signal};

    use super::{HookSignal, SignalHook, TableSource, Teardown};

    /// The only program production runs to read the process table.
    const PS: &str = "/bin/ps";
    const PS_ARGS: [&str; 3] = ["-A", "-o", "pid=,ppid=,pgid=,stat=,lstart="];
    /// Largest process table the host reads.
    pub(super) const TABLE_MAX_BYTES: usize = 4 << 20;
    /// Most descendants outside the group that one walk holds, unless the
    /// seam sets another cap.
    const MAX_HELD: usize = 1024;

    pub(super) fn pid(raw: u32) -> Option<Pid> {
        i32::try_from(raw).ok().and_then(Pid::from_raw)
    }

    /// Whether the unreaped `leader` has ended by a signal, observed without
    /// reaping it. A leader still running, or one that exited, has not.
    #[cfg(target_os = "linux")]
    pub(super) fn ended_by_signal(leader: u32) -> bool {
        use rustix::process::{WaitId, WaitIdOptions, waitid};
        let Some(p) = pid(leader) else {
            return false;
        };
        let opts = WaitIdOptions::EXITED | WaitIdOptions::NOWAIT | WaitIdOptions::NOHANG;
        matches!(
            waitid(WaitId::Pid(p), opts),
            Ok(Some(s)) if s.terminating_signal().is_some()
        )
    }

    /// One row of the process table.
    #[derive(Debug, PartialEq, Eq)]
    pub(super) struct Entry {
        pub(super) pid: u32,
        pub(super) ppid: u32,
        pub(super) pgid: u32,
        pub(super) stat: String,
        /// Start time as `ps` prints it, to tell two holders of one id apart.
        pub(super) start: String,
    }

    impl Entry {
        fn stopped(&self) -> bool {
            self.stat.starts_with('T')
        }

        fn zombie(&self) -> bool {
            self.stat.starts_with('Z')
        }
    }

    /// What binds a held descendant to its id: a pidfd, or the test hook.
    enum Link {
        /// A Linux pidfd.
        #[cfg(target_os = "linux")]
        Fd(rustix::fd::OwnedFd),
        /// The test seam's stand-in.
        Hook(SignalHook),
    }

    /// A descendant outside the group that this teardown holds and stopped.
    pub(super) struct Stray {
        pid: u32,
        ppid: u32,
        start: String,
        link: Link,
    }

    /// What the walk does with a descendant outside the group.
    pub(super) enum Reach {
        /// Bound to its id: stopped now, killed with the group.
        Held(Stray),
        /// Gone: its id names no process, or its pidfd shows an exit.
        #[cfg_attr(
            not(target_os = "linux"),
            expect(dead_code, reason = "nothing is skipped without pidfds")
        )]
        Skip,
        /// Running, but nothing binds it to its id: reported, never signalled.
        Escaped,
    }

    impl Stray {
        /// Bind the process in `e`, whose parent is stopped, to its id.
        ///
        /// The pidfd names whatever held the id when it was opened. A stopped
        /// parent cannot fork, so if that process still has the parent from
        /// the snapshot, it is the process from the snapshot. With a `hook`
        /// the process is held without a pidfd.
        pub(super) fn reach(e: &Entry, hook: Option<&SignalHook>) -> Reach {
            if let Some(h) = hook {
                return Reach::Held(Self::new(e, Link::Hook(h.clone())));
            }
            Self::open(e)
        }

        fn new(e: &Entry, link: Link) -> Self {
            Self {
                pid: e.pid,
                ppid: e.ppid,
                start: e.start.clone(),
                link,
            }
        }

        #[cfg(target_os = "linux")]
        fn open(e: &Entry) -> Reach {
            use rustix::process::{PidfdFlags, pidfd_open};
            let Some(p) = pid(e.pid) else {
                return Reach::Escaped;
            };
            let fd = match pidfd_open(p, PidfdFlags::empty()) {
                Ok(fd) => fd,
                Err(err) if gone(err) => return Reach::Skip,
                Err(_) => return Reach::Escaped,
            };
            match revalidated(e.ppid, proc_ppid(e.pid).ok(), || exited(&fd)) {
                Verdict::Bound => Reach::Held(Self::new(e, Link::Fd(fd))),
                Verdict::Gone => Reach::Skip,
                Verdict::Escaped => Reach::Escaped,
            }
        }

        /// Without pidfds no process outside the group is bound to its id:
        /// a stopped parent that ignores `SIGCHLD` still has its exited
        /// children reaped, and their ids reused.
        ///
        /// Best-effort macOS descendant tracking follows in slopvac-8l4.9.39;
        /// until then escaped descendants are reported and never signalled.
        #[cfg(not(target_os = "linux"))]
        fn open(_e: &Entry) -> Reach {
            Reach::Escaped
        }

        /// Whether `e` still shows this process: same id, parent and start time.
        fn is(&self, e: &Entry) -> bool {
            e.pid == self.pid && e.ppid == self.ppid && e.start == self.start
        }

        /// Send `sig` through the pidfd, or the hook.
        pub(super) fn signal(&self, sig: Signal) -> rustix::io::Result<()> {
            match &self.link {
                #[cfg(target_os = "linux")]
                Link::Fd(fd) => rustix::process::pidfd_send_signal(fd, sig),
                Link::Hook(h) => {
                    let which = if sig == Signal::KILL {
                        HookSignal::Kill
                    } else {
                        HookSignal::Stop
                    };
                    (h.0)(self.pid, which).map_err(rustix::io::Errno::from_raw_os_error)
                }
            }
        }
    }

    /// Whether a failed pidfd call shows that the process is gone. Only
    /// `ESRCH` does; any other error (`ENOSYS` before Linux 5.3, `EMFILE`,
    /// `EPERM`) leaves it running and out of reach.
    pub(super) fn gone(err: rustix::io::Errno) -> bool {
        err == rustix::io::Errno::SRCH
    }

    /// What revalidating a descendant through its open pidfd showed.
    #[cfg(any(target_os = "linux", test))]
    #[derive(Debug, PartialEq, Eq)]
    pub(super) enum Verdict {
        /// The pidfd names the process from the snapshot.
        Bound,
        /// The pidfd shows that its process exited.
        Gone,
        /// It may still run, and nothing binds it to its id.
        Escaped,
    }

    /// Judge a descendant whose parent in the snapshot was `want`, from the
    /// parent that `/proc` shows for it now, or `None` if `/proc` could not
    /// be read.
    ///
    /// Only that parent binds the pidfd to the process from the snapshot. A
    /// failed read (`/proc` hides other users' processes under `hidepid`,
    /// and a set-user-id program may run as one) or another parent (it was
    /// reparented, or its id was reused) proves no exit. Only the pidfd can,
    /// so `exited` asks it; otherwise the process escaped.
    #[cfg(any(target_os = "linux", test))]
    pub(super) fn revalidated(
        want: u32,
        seen: Option<u32>,
        exited: impl FnOnce() -> bool,
    ) -> Verdict {
        match seen {
            Some(parent) if parent == want => Verdict::Bound,
            _ if exited() => Verdict::Gone,
            _ => Verdict::Escaped,
        }
    }

    /// Whether the process a pidfd names has exited: the pidfd polls
    /// readable then. A poll that fails shows no exit.
    #[cfg(target_os = "linux")]
    pub(super) fn exited(fd: &rustix::fd::OwnedFd) -> bool {
        use rustix::event::{PollFd, PollFlags, Timespec, poll};
        let mut fds = [PollFd::new(fd, PollFlags::IN)];
        let now = Timespec {
            tv_sec: 0,
            tv_nsec: 0,
        };
        matches!(poll(&mut fds, Some(&now)), Ok(n) if n > 0)
            && fds[0].revents().intersects(PollFlags::IN | PollFlags::HUP)
    }

    /// The parent of `pid` from `/proc/<pid>/stat`.
    #[cfg(target_os = "linux")]
    pub(crate) fn proc_ppid(pid: u32) -> std::io::Result<u32> {
        // Bytes, not text: a process may give itself a name that is not UTF-8.
        let stat = std::fs::read(format!("/proc/{pid}/stat"))?;
        let bad = || std::io::Error::from(std::io::ErrorKind::InvalidData);
        // The command name may hold spaces and parentheses; it ends at the last `)`.
        let end = stat.iter().rposition(|&b| b == b')').ok_or_else(bad)?;
        let rest = std::str::from_utf8(&stat[end + 1..]).map_err(|_| bad())?;
        rest.split_ascii_whitespace()
            .nth(1)
            .and_then(|s| s.parse().ok())
            .ok_or_else(bad)
    }

    /// The outcome of one walk.
    pub(super) struct Walk {
        /// Held descendants, parents before children.
        pub(super) held: Vec<Stray>,
        /// What the walk left undone.
        pub(super) left: Teardown,
    }

    impl Walk {
        /// Kill the held descendants, deepest first, and return what the
        /// walk left undone, with any that the kill did not reach.
        pub(super) fn kill(self) -> Teardown {
            let mut left = self.left;
            for s in self.held.iter().rev() {
                if s.signal(Signal::KILL).is_err_and(|err| !gone(err)) {
                    left.escaped.push(s.pid);
                }
            }
            left
        }
    }

    /// Find the descendants of the stopped `leader` and its group that left
    /// the group: hold and stop each one that can be bound to its id, report
    /// the rest. Runs until a round finds nothing new, the table cannot be
    /// read, `deadline` passes or the cap on held descendants is reached; all but the first
    /// leave the walk incomplete.
    pub(super) fn walk(leader: u32, source: Option<&TableSource>, deadline: Instant) -> Walk {
        let me = std::process::id();
        let mut held: Vec<Stray> = Vec::new();
        let mut left = Teardown::default();
        let cap = source.map_or(MAX_HELD, |s| s.max_held);
        'rounds: loop {
            if Instant::now() >= deadline {
                left.incomplete = true;
                break;
            }
            // A table without the leader is not this system's.
            let Some(table) = snapshot(source, deadline).filter(|t| t.contains_key(&leader)) else {
                left.incomplete = true;
                break;
            };
            // The leader counts whatever its group, a held process only while
            // its row still shows it.
            let ours =
                |e: &Entry| e.pid == leader || e.pgid == leader || held.iter().any(|s| s.is(e));
            let stopped: HashSet<u32> = table
                .values()
                .filter(|e| ours(e) && e.stopped())
                .map(|e| e.pid)
                .collect();
            // Signals reach a process asynchronously; look again once all have stopped.
            let settling = table
                .values()
                .any(|e| ours(e) && !e.stopped() && !e.zombie());
            let mut grew = false;
            let mut parents = stopped;
            // Descendants of a process held in this round that the same table
            // already shows are bound at once, once the parent is confirmed
            // stopped, so a static tree costs two reads at any depth.
            loop {
                let first = held.len();
                let Some(added) = bind_children(
                    &table,
                    &parents,
                    leader,
                    me,
                    cap,
                    source.and_then(|s| s.signals.as_ref()),
                    deadline,
                    &mut held,
                    &mut left,
                ) else {
                    left.incomplete = true;
                    break 'rounds;
                };
                grew |= added;
                parents = confirmed_stopped(&held[first..], deadline);
                // Past the deadline no stop counts, so nothing widens the
                // walk: it ends incomplete and kills what it holds.
                if Instant::now() >= deadline {
                    left.incomplete = true;
                    break 'rounds;
                }
                if parents.is_empty() {
                    break;
                }
            }
            // Children forked before the stop landed show only in the next table.
            if !grew && !settling {
                break;
            }
            if settling {
                std::thread::sleep(Duration::from_millis(5));
            }
        }
        Walk { held, left }
    }

    /// Hold and stop each row of `table` outside the group whose parent is in
    /// `parents` and not held yet. Returns whether it held any, or `None` when
    /// the cap on held descendants is reached or `deadline` has passed, before
    /// the first row or between two.
    #[expect(
        clippy::too_many_arguments,
        reason = "one walk step, split out of `walk`"
    )]
    pub(super) fn bind_children(
        table: &HashMap<u32, Entry>,
        parents: &HashSet<u32>,
        leader: u32,
        me: u32,
        cap: usize,
        hook: Option<&SignalHook>,
        deadline: Instant,
        held: &mut Vec<Stray>,
        left: &mut Teardown,
    ) -> Option<bool> {
        // The deadline bounds the scan of a large table too, not only the binding.
        if Instant::now() >= deadline {
            return None;
        }
        let mut found: Vec<&Entry> = Vec::new();
        for e in table.values() {
            if Instant::now() >= deadline {
                return None;
            }
            if e.pgid != leader
                && e.pid != leader
                && parents.contains(&e.ppid)
                && e.pid > 1
                && e.pid != me
                && !held.iter().any(|s| s.pid == e.pid)
                && !left.escaped.contains(&e.pid)
            {
                found.push(e);
            }
        }
        found.sort_by_key(|e| e.pid);
        let mut grew = false;
        for e in found {
            if Instant::now() >= deadline {
                return None;
            }
            match Stray::reach(e, hook) {
                Reach::Held(s) if held.len() < cap => match s.signal(Signal::STOP) {
                    Ok(()) => {
                        held.push(s);
                        grew = true;
                    }
                    Err(err) if gone(err) => {}
                    // For example `EPERM`: it runs as another user.
                    Err(_) => left.escaped.push(e.pid),
                },
                Reach::Held(_) => return None,
                Reach::Skip => {}
                Reach::Escaped => left.escaped.push(e.pid),
            }
        }
        Some(grew)
    }

    /// The strays among `strays` that are stopped now and have not exited.
    ///
    /// A stray was just sent `SIGSTOP`, which lands asynchronously. This waits
    /// for each one to show as stopped in `/proc`. Once `deadline` has passed
    /// it confirms nothing, so a late stop cannot widen the walk. A stopped
    /// parent cannot fork, so confirming it allows binding the children the
    /// table already shows. A fork between the table read and the stop is
    /// possible, and the next snapshot finds that child. Without a pidfd (the
    /// test hook, or off Linux) nothing is confirmed and the next table read
    /// does the work.
    #[cfg(target_os = "linux")]
    pub(super) fn confirmed_stopped(strays: &[Stray], deadline: Instant) -> HashSet<u32> {
        let mut out = HashSet::new();
        for s in strays {
            let Link::Fd(fd) = &s.link else { continue };
            loop {
                if Instant::now() >= deadline {
                    return HashSet::new();
                }
                match proc_state(s.pid) {
                    Some(b'T' | b't') if !exited(fd) => {
                        out.insert(s.pid);
                        break;
                    }
                    Some(b'R' | b'S' | b'D' | b'I' | b'W' | b'P') if !exited(fd) => {
                        std::thread::sleep(Duration::from_millis(1));
                    }
                    _ => break,
                }
            }
        }
        out
    }

    #[cfg(not(target_os = "linux"))]
    fn confirmed_stopped(_strays: &[Stray], _deadline: Instant) -> HashSet<u32> {
        HashSet::new()
    }

    /// The state letter of `pid` from `/proc/<pid>/stat`.
    #[cfg(target_os = "linux")]
    fn proc_state(pid: u32) -> Option<u8> {
        let stat = std::fs::read(format!("/proc/{pid}/stat")).ok()?;
        let end = stat.iter().rposition(|&b| b == b')')?;
        stat.get(end + 2).copied()
    }

    fn snapshot(source: Option<&TableSource>, deadline: Instant) -> Option<HashMap<u32, Entry>> {
        let out = match source {
            Some(s) => run_bounded(&s.program, &s.args, deadline)?,
            None => run_bounded(Path::new(PS), &PS_ARGS, deadline)?,
        };
        parse_table(&out)
    }

    /// Run a helper and return its standard output, or `None` if it failed,
    /// passed `deadline` or printed more than [`TABLE_MAX_BYTES`].
    ///
    /// The helper gets an empty environment apart from `LC_ALL=C` and
    /// `PATH=/usr/bin:/bin`, no input, and a process group of its own, which
    /// is killed before the helper is reaped.
    pub(super) fn run_bounded<S: AsRef<OsStr>>(
        program: &Path,
        args: &[S],
        deadline: Instant,
    ) -> Option<Vec<u8>> {
        use std::os::unix::process::CommandExt;
        let mut child = Command::new(program)
            .args(args)
            .env_clear()
            .env("LC_ALL", "C")
            .env("PATH", "/usr/bin:/bin")
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .process_group(0)
            .spawn()
            .ok()?;
        let out = read_bounded(child.stdout.take(), deadline);
        let exited = out.is_some() && exited_by(&child, deadline);
        // Still unreaped, so the helper's ids are its own. The helper itself
        // is killed too, in case it moved to another group.
        let _ = child.kill();
        if let Some(g) = pid(child.id()) {
            let _ = rustix::process::kill_process_group(g, Signal::KILL);
        }
        let ok = child.wait().is_ok_and(|s| s.success());
        out.filter(|_| exited && ok)
    }

    /// Read to end of stream on a thread, up to the limit and the deadline.
    fn read_bounded(pipe: Option<std::process::ChildStdout>, deadline: Instant) -> Option<Vec<u8>> {
        let mut pipe = pipe?;
        let (tx, rx) = crossbeam_channel::bounded(1);
        std::thread::spawn(move || {
            let mut buf = Vec::new();
            let limit = TABLE_MAX_BYTES as u64 + 1;
            let read = (&mut pipe).take(limit).read_to_end(&mut buf);
            let _ = tx.send(read.ok().map(|_| buf));
        });
        rx.recv_deadline(deadline)
            .ok()
            .flatten()
            .filter(|b| b.len() <= TABLE_MAX_BYTES)
    }

    /// Whether the helper exits by `deadline`, observed without reaping it.
    fn exited_by(child: &Child, deadline: Instant) -> bool {
        use rustix::io::Errno;
        use rustix::process::{WaitId, WaitIdOptions, waitid};
        let Some(p) = pid(child.id()) else {
            return false;
        };
        let opts = WaitIdOptions::EXITED | WaitIdOptions::NOWAIT | WaitIdOptions::NOHANG;
        loop {
            match waitid(WaitId::Pid(p), opts) {
                Ok(Some(s)) if s.exited() || s.killed() || s.dumped() => return true,
                Err(Errno::INTR) => {}
                Ok(_) if Instant::now() < deadline => {
                    std::thread::sleep(Duration::from_millis(1));
                }
                _ => return false,
            }
        }
    }

    /// Parse `ps -A -o pid=,ppid=,pgid=,stat=,lstart=` output, all or nothing.
    /// A well-formed row for a process that is being released is left out.
    pub(super) fn parse_table(out: &[u8]) -> Option<HashMap<u32, Entry>> {
        let text = std::str::from_utf8(out).ok()?;
        let mut table = HashMap::new();
        for line in text.lines() {
            let Row::Live(entry) = parse_row(line)? else {
                continue;
            };
            if table.insert(entry.pid, entry).is_some() {
                return None;
            }
        }
        (!table.is_empty()).then_some(table)
    }

    /// What one well-formed row shows.
    enum Row {
        Live(Entry),
        /// State `X`: the process has exited and the kernel is releasing it,
        /// so it can no longer fork, reap or be signalled. procps shows its
        /// parent as 0 and its group as -1, printed as 4294967295.
        Exiting,
    }

    /// One row: three ids, a state and a C-locale `lstart` such as `Sat Nov 14 23:00:07 2026`.
    fn parse_row(line: &str) -> Option<Row> {
        let fields: Vec<&str> = line.split_ascii_whitespace().collect();
        let [own, parent, group, state, lstart @ ..] = &fields[..] else {
            return None;
        };
        let [wday, month, day, clock, year] = lstart[..] else {
            return None;
        };
        let word = |s: &str| s.len() == 3 && s.bytes().all(|b| b.is_ascii_alphabetic());
        let digits = |s: &str, n: std::ops::RangeInclusive<usize>| {
            n.contains(&s.len()) && s.bytes().all(|b| b.is_ascii_digit())
        };
        let clock_ok = clock.len() == 8
            && clock.bytes().enumerate().all(|(i, b)| {
                if i % 3 == 2 {
                    b == b':'
                } else {
                    b.is_ascii_digit()
                }
            });
        let state_ok =
            (1..=8).contains(&state.len()) && state.bytes().all(|b| b.is_ascii_graphic());
        let when_ok =
            word(wday) && word(month) && digits(day, 1..=2) && clock_ok && digits(year, 4..=4);
        if !(state_ok && when_ok) {
            return None;
        }
        let pid = id(own).filter(|&p| p > 0)?;
        if state.starts_with('X') {
            let released = |s: &str| id(s).is_some() || s == "4294967295";
            return (released(parent) && released(group)).then_some(Row::Exiting);
        }
        Some(Row::Live(Entry {
            pid,
            ppid: id(parent)?,
            pgid: id(group)?,
            stat: (*state).to_owned(),
            start: lstart.join(" "),
        }))
    }

    /// A process id in decimal digits only, within the range of `pid_t`.
    fn id(s: &str) -> Option<u32> {
        if s.is_empty() || s.len() > 10 || !s.bytes().all(|b| b.is_ascii_digit()) {
            return None;
        }
        s.parse::<u32>().ok().filter(|&v| i32::try_from(v).is_ok())
    }
}

#[cfg(target_os = "linux")]
pub(crate) use unix::proc_ppid;

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(unix)]
    #[test]
    fn only_esrch_from_a_pidfd_call_means_the_process_is_gone() {
        use super::unix::gone;
        use rustix::io::Errno;
        assert!(gone(Errno::SRCH));
        for err in [
            Errno::NOSYS,
            Errno::MFILE,
            Errno::NFILE,
            Errno::PERM,
            Errno::NOMEM,
        ] {
            assert!(!gone(err), "{err:?}");
        }
    }

    /// A pidfd names whatever held the id when it opened. Only the parent
    /// from the snapshot binds it; anything else is gone only if the pidfd
    /// itself shows an exit (`/proc` hides processes under `hidepid`).
    #[cfg(unix)]
    #[test]
    fn a_descendant_whose_parent_is_not_confirmed_escapes_unless_its_pidfd_shows_an_exit() {
        use super::unix::{Verdict, revalidated};
        let parent = 7;
        // (parent that `/proc` shows, or none if unreadable; the pidfd shows
        // an exit; verdict)
        let cases = [
            (Some(7), false, Verdict::Bound),
            (Some(7), true, Verdict::Bound),
            (None, false, Verdict::Escaped),
            (None, true, Verdict::Gone),
            // Reparented after its parent was killed, or the id was reused.
            (Some(1), false, Verdict::Escaped),
            (Some(1), true, Verdict::Gone),
        ];
        for (seen, exited, want) in cases {
            let got = revalidated(parent, seen, || exited);
            assert_eq!(got, want, "{seen:?}, exited {exited}");
        }
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn a_pidfd_shows_an_exit_only_once_the_process_has_exited() {
        use rustix::process::{Pid, PidfdFlags, pidfd_open};
        let mut child = std::process::Command::new("/bin/sleep")
            .arg("300")
            .spawn()
            .unwrap();
        let pid = Pid::from_raw(i32::try_from(child.id()).unwrap()).unwrap();
        let fd = pidfd_open(pid, PidfdFlags::empty()).unwrap();
        let before = super::unix::exited(&fd);
        child.kill().unwrap();
        // The child stays unreaped, so only the exit can make the pidfd readable.
        let end = Instant::now() + Duration::from_secs(10);
        while !super::unix::exited(&fd) && Instant::now() < end {
            std::thread::sleep(Duration::from_millis(10));
        }
        let after = super::unix::exited(&fd);
        child.wait().unwrap();
        assert!(!before, "a running process showed an exit");
        assert!(after, "an exited process showed no exit");
    }

    /// A stop confirmed after the deadline must not widen the walk, so the
    /// confirmation yields nothing once the deadline has passed. The deadline
    /// is already past, so no timing decides the outcome.
    #[cfg(target_os = "linux")]
    #[test]
    fn a_stop_is_not_confirmed_after_the_deadline() {
        use super::unix::{Entry, Reach, Stray, confirmed_stopped};
        use rustix::process::Signal;
        use std::collections::HashSet;
        let mut child = std::process::Command::new("/bin/sleep")
            .arg("300")
            .spawn()
            .unwrap();
        let e = Entry {
            pid: child.id(),
            ppid: std::process::id(),
            pgid: 0,
            stat: "S".into(),
            start: String::new(),
        };
        let Reach::Held(s) = Stray::reach(&e, None) else {
            panic!("a live child of this process is not held");
        };
        s.signal(Signal::STOP).unwrap();
        let live = Instant::now() + Duration::from_secs(30);
        let confirmed = confirmed_stopped(std::slice::from_ref(&s), live);
        let late = confirmed_stopped(std::slice::from_ref(&s), Instant::now());
        child.kill().unwrap();
        child.wait().unwrap();
        assert_eq!(
            confirmed,
            HashSet::from([e.pid]),
            "control: a live deadline"
        );
        assert!(late.is_empty(), "confirmed after the deadline: {late:?}");
    }

    /// Signals a hook recorded, in order.
    #[cfg(unix)]
    type Sent = Vec<(u32, HookSignal)>;

    /// Two children of one stopped parent, bound through a recording hook.
    /// `stall` makes each stop outlast the deadline, which `bind_children`
    /// then meets between two rows. Returns the result, the recorded
    /// signals and what teardown signals afterwards.
    #[cfg(unix)]
    fn bind_two(deadline: Instant, stall: bool) -> (Option<bool>, Sent, Sent) {
        use super::unix::{Entry, Walk, bind_children};
        use std::collections::{HashMap, HashSet};
        use std::sync::{Arc, Mutex};
        let sent = Arc::new(Mutex::new(Vec::new()));
        let log = Arc::clone(&sent);
        let hook = SignalHook(Arc::new(move |pid, sig| {
            log.lock().unwrap().push((pid, sig));
            if stall && sig == HookSignal::Stop {
                while Instant::now() < deadline {
                    std::thread::sleep(Duration::from_millis(1));
                }
            }
            Ok(())
        }));
        let row = |pid| Entry {
            pid,
            ppid: 4_000_000,
            pgid: 4_000_100,
            stat: "S".into(),
            start: String::new(),
        };
        let table = HashMap::from([(4_000_001, row(4_000_001)), (4_000_002, row(4_000_002))]);
        let parents = HashSet::from([4_000_000]);
        let (mut held, mut left) = (Vec::new(), Teardown::default());
        let bound = bind_children(
            &table,
            &parents,
            1,
            2,
            8,
            Some(&hook),
            deadline,
            &mut held,
            &mut left,
        );
        let binding = sent.lock().unwrap().clone();
        sent.lock().unwrap().clear();
        Walk { held, left }.kill();
        let killing = sent.lock().unwrap().clone();
        (bound, binding, killing)
    }

    /// Control for the deadline tests: with a live deadline both children are
    /// bound, and teardown kills both, deepest first.
    #[cfg(unix)]
    #[test]
    fn children_are_bound_and_killed_while_the_deadline_is_live() {
        let (bound, binding, killing) = bind_two(Instant::now() + Duration::from_secs(60), false);
        assert_eq!(bound, Some(true));
        assert_eq!(
            binding,
            [(4_000_001, HookSignal::Stop), (4_000_002, HookSignal::Stop)]
        );
        assert_eq!(
            killing,
            [(4_000_002, HookSignal::Kill), (4_000_001, HookSignal::Kill)]
        );
    }

    /// The deadline passes while the first child is stopped: the second is
    /// never bound, the walk reports no further growth, and teardown still
    /// kills the first.
    #[cfg(unix)]
    #[test]
    fn expiry_during_expansion_stops_the_next_binding_and_still_kills_what_is_held() {
        let (bound, binding, killing) = bind_two(Instant::now() + Duration::from_millis(100), true);
        assert_eq!(bound, None);
        // Under load the deadline may pass before even the first row, so the
        // first child may be unbound. The second never is.
        assert!(
            binding.iter().all(|&(pid, _)| pid == 4_000_001),
            "{binding:?}"
        );
        assert_eq!(killing.len(), binding.len(), "{killing:?}");
        assert!(killing.iter().all(|&(_, sig)| sig == HookSignal::Kill));
    }

    /// Off the graceful path `taskkill` runs, and it exits 128 when the
    /// leader is already gone; it then finds no tree, so the leader's
    /// descendants are out of its reach.
    #[test]
    fn off_the_graceful_path_only_a_taskkill_that_exits_0_completes_the_teardown() {
        assert_eq!(windows_teardown(false, || Some(0)), Teardown::default());
        // A failing exit, "process not found", or no exit status at all.
        for code in [Some(1), Some(128), Some(255), None] {
            let left = windows_teardown(false, || code);
            assert!(left.incomplete && left.escaped.is_empty(), "{code:?}");
        }
    }

    #[test]
    fn a_graceful_exit_completes_the_windows_teardown_without_taskkill() {
        let left = windows_teardown(true, || panic!("taskkill ran"));
        assert_eq!(left, Teardown::default());
    }

    #[test]
    fn only_an_acknowledged_exit_0_without_a_kill_is_graceful() {
        // (acknowledged, forced, exited 0)
        for acknowledged in [false, true] {
            for forced in [false, true] {
                for zero in [false, true] {
                    let want = (acknowledged, forced, zero) == (true, false, true);
                    assert_eq!(
                        graceful(acknowledged, forced, zero),
                        want,
                        "acknowledged {acknowledged}, forced {forced}, exited 0 {zero}"
                    );
                }
            }
        }
    }

    #[cfg(unix)]
    #[test]
    fn a_teardown_that_cannot_name_its_leader_is_incomplete() {
        let left = tear_down(u32::MAX, None, Then::Kill);
        assert!(left.incomplete, "{left:?}");
    }

    #[cfg(unix)]
    mod helper {
        use std::path::Path;
        use std::time::{Duration, Instant};

        use super::super::unix::{Entry, TABLE_MAX_BYTES, parse_table, run_bounded};

        fn sh(script: &str, within: Duration) -> Option<Vec<u8>> {
            run_bounded(
                Path::new("/bin/sh"),
                &["-c", script],
                Instant::now() + within,
            )
        }

        #[test]
        fn the_helper_sees_only_the_fixed_environment() {
            let out = run_bounded(
                Path::new("/usr/bin/env"),
                &[] as &[&str],
                Instant::now() + Duration::from_secs(10),
            )
            .unwrap();
            let mut lines: Vec<&str> = std::str::from_utf8(&out).unwrap().lines().collect();
            lines.sort_unstable();
            assert_eq!(lines, ["LC_ALL=C", "PATH=/usr/bin:/bin"]);
        }

        #[test]
        fn output_up_to_the_limit_is_kept_and_one_byte_more_is_refused() {
            let at = sh(
                &format!("head -c {TABLE_MAX_BYTES} /dev/zero"),
                Duration::from_secs(20),
            );
            let over = sh(
                &format!("head -c {} /dev/zero", TABLE_MAX_BYTES + 1),
                Duration::from_secs(20),
            );
            assert_eq!(at.map(|b| b.len()), Some(TABLE_MAX_BYTES));
            assert_eq!(over, None);
        }

        #[test]
        fn endless_output_is_cut_off_at_the_limit_before_the_deadline() {
            let started = Instant::now();
            let got = sh("exec yes", Duration::from_secs(60));
            assert_eq!(got, None);
            assert!(
                started.elapsed() < Duration::from_secs(30),
                "{:?}",
                started.elapsed()
            );
        }

        #[test]
        fn a_helper_that_fails_yields_nothing() {
            assert_eq!(sh("echo partial; exit 3", Duration::from_secs(10)), None);
        }

        /// Whether `pid` still runs: a killed process may stay a zombie
        /// until its new parent reaps it, so poll for up to ten seconds.
        fn still_running(pid: &str) -> bool {
            let end = Instant::now() + Duration::from_secs(10);
            loop {
                let out = std::process::Command::new("/bin/ps")
                    .args(["-o", "stat=", "-p", pid])
                    .output()
                    .unwrap();
                let stat = String::from_utf8_lossy(&out.stdout).trim().to_owned();
                if stat.is_empty() || stat.starts_with('Z') {
                    return false;
                }
                if Instant::now() > end {
                    return true;
                }
                std::thread::sleep(Duration::from_millis(20));
            }
        }

        /// Run `script` with a 500 ms deadline; it writes a pid to the file
        /// named by `$0`. Returns the output, the time taken and that pid.
        fn hung(script: &str) -> (Option<Vec<u8>>, Duration, String) {
            let dir = std::env::temp_dir().join(format!(
                "slopvac-hung-{}-{}",
                std::process::id(),
                script.len()
            ));
            std::fs::create_dir_all(&dir).unwrap();
            let pidfile = dir.join("pid");
            let started = Instant::now();
            let got = run_bounded(
                Path::new("/bin/sh"),
                &[
                    std::ffi::OsStr::new("-c"),
                    script.as_ref(),
                    pidfile.as_os_str(),
                ],
                started + Duration::from_millis(500),
            );
            let took = started.elapsed();
            let pid = std::fs::read_to_string(&pidfile).unwrap().trim().to_owned();
            std::fs::remove_dir_all(&dir).unwrap();
            (got, took, pid)
        }

        #[test]
        fn a_hung_helper_and_its_children_are_killed_at_the_deadline() {
            let (got, took, child) = hung(r#"sleep 60 & echo $! > "$0"; wait"#);
            assert_eq!(got, None);
            assert!(took < Duration::from_secs(30), "{took:?}");
            assert!(
                !still_running(&child),
                "the helper's child {child} survived"
            );
        }

        #[test]
        fn a_hung_helper_that_left_its_group_is_killed_at_the_deadline() {
            // The helper leads its own group, so it moves into the host's.
            let script = r#"echo $$ > "$0"; exec /usr/bin/perl -e 'setpgrp(0, getpgrp(getppid())) or die; sleep 60'"#;
            let (got, took, helper) = hung(script);
            assert_eq!(got, None);
            assert!(took < Duration::from_secs(30), "{took:?}");
            assert!(!still_running(&helper), "the helper {helper} survived");
        }

        const ROW: &str = "Sat Nov 14 23:00:07 2026";

        #[test]
        fn a_well_formed_table_parses() {
            let text = format!(
                "    1     0     1 Ss   {ROW}\n  42     1    40 T    Sat Nov  4 01:02:03 2026\n"
            );
            let t = parse_table(text.as_bytes()).unwrap();
            assert_eq!(
                t[&42],
                Entry {
                    pid: 42,
                    ppid: 1,
                    pgid: 40,
                    stat: "T".into(),
                    start: "Sat Nov 4 01:02:03 2026".into(),
                }
            );
            assert_eq!(t.len(), 2);
        }

        #[test]
        fn a_table_with_any_malformed_row_is_refused() {
            let good = format!("1 0 1 Ss {ROW}");
            for bad in [
                format!("+5 1 1 S {ROW}"),
                format!("-5 1 1 S {ROW}"),
                format!("0 1 1 S {ROW}"),
                format!("5 1 1 S {ROW} extra"),
                "5 1 1 S Sat Nov 14 23:00:07".to_owned(),
                "5 1 1 S Sat Nov 14 23-00-07 2026".to_owned(),
                format!("4294967296 1 1 S {ROW}"),
                format!("2147483648 1 1 S {ROW}"),
                format!("1 0 1 S {ROW}"),
                String::new(),
            ] {
                let text = format!("{good}\n{bad}\n");
                assert!(parse_table(text.as_bytes()).is_none(), "{bad:?}");
            }
            assert!(parse_table(b"").is_none());
            assert!(parse_table(b"1 0 1 S Sat Nov 14 23:00:07 2026\n\xff\n").is_none());
        }

        /// procps shows a process that is being released (state `X`) with
        /// parent 0 and group -1 printed unsigned, as seen under load on
        /// Linux: `1661612 0 4294967295 XN+ ...`. It can no longer fork or be
        /// signalled, so the table leaves it out instead of failing.
        #[test]
        fn a_process_mid_exit_is_left_out_of_the_table() {
            let text = format!("1 0 1 Ss {ROW}\n1661612       0 4294967295 XN+  {ROW}\n");
            let t = parse_table(text.as_bytes()).unwrap();
            assert_eq!(t.keys().copied().collect::<Vec<_>>(), [1]);
        }

        #[test]
        fn a_malformed_row_mid_exit_is_still_refused() {
            let good = format!("1 0 1 Ss {ROW}");
            for bad in [
                format!("4294967295 0 4294967295 X {ROW}"),
                format!("0 0 4294967295 X {ROW}"),
                format!("5 0 -1 X {ROW}"),
                format!("5 0 4294967296 X {ROW}"),
                format!("5 4294967294 1 X {ROW}"),
                "5 0 4294967295 X Sat Nov 14 23:00:07".to_owned(),
            ] {
                let text = format!("{good}\n{bad}\n");
                assert!(parse_table(text.as_bytes()).is_none(), "{bad:?}");
            }
            // Left out, the rows leave an empty table, which is refused.
            assert!(parse_table(format!("5 0 4294967295 X {ROW}\n").as_bytes()).is_none());
        }
    }
}
