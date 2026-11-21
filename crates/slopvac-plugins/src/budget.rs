//! Whole-run output budget shared by every plugin of one run (threat model
//! P3 and section 5.5).
//!
//! [`RunCaps`](crate::RunCaps) bound one plugin. Many plugins could still add
//! up to unbounded work, so one [`RunBudget`] counts what all of them send.
//! The first charge past a cap trips the budget for good: the plugin that
//! made the charge is killed, and no later plugin starts.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, PoisonError};

use crate::messages::host::{self as messages, HostPhrase};

/// The aggregate caps for one run.
#[derive(Debug, Clone, Copy)]
pub struct BudgetCaps {
    /// Bytes read from the standard output of all plugins.
    pub stdout_bytes: u64,
    /// Bytes read from the standard error of all plugins.
    pub stderr_bytes: u64,
    /// Unsolicited messages and unmatched responses from all plugins.
    pub unsolicited_messages: u64,
}

impl Default for BudgetCaps {
    fn default() -> Self {
        Self {
            stdout_bytes: 2 << 30,
            stderr_bytes: 512 << 20,
            unsolicited_messages: 4000,
        }
    }
}

/// Thread-safe counters with the first breach recorded.
#[derive(Debug)]
pub struct RunBudget {
    caps: BudgetCaps,
    stdout: AtomicU64,
    stderr: AtomicU64,
    unsolicited: AtomicU64,
    breach: Mutex<Option<String>>,
}

impl Default for RunBudget {
    fn default() -> Self {
        Self::new(BudgetCaps::default())
    }
}

impl RunBudget {
    /// A fresh budget with `caps`.
    #[must_use]
    pub fn new(caps: BudgetCaps) -> Self {
        Self {
            caps,
            stdout: AtomicU64::new(0),
            stderr: AtomicU64::new(0),
            unsolicited: AtomicU64::new(0),
            breach: Mutex::new(None),
        }
    }

    /// A shareable budget with `caps`.
    #[must_use]
    pub fn shared(caps: BudgetCaps) -> Arc<Self> {
        Arc::new(Self::new(caps))
    }

    /// Count `n` bytes read from a plugin's standard output.
    ///
    /// # Errors
    /// The breach message when the run is over budget, now or earlier.
    pub fn charge_stdout(&self, n: u64) -> Result<(), String> {
        self.charge(
            &self.stdout,
            n,
            self.caps.stdout_bytes,
            HostPhrase::BudgetStdoutBytes.as_static(),
        )
    }

    /// Count `n` bytes read from a plugin's standard error.
    ///
    /// # Errors
    /// The breach message when the run is over budget, now or earlier.
    pub fn charge_stderr(&self, n: u64) -> Result<(), String> {
        self.charge(
            &self.stderr,
            n,
            self.caps.stderr_bytes,
            HostPhrase::BudgetStderrBytes.as_static(),
        )
    }

    /// Count one unsolicited message.
    ///
    /// # Errors
    /// The breach message when the run is over budget, now or earlier.
    pub fn charge_unsolicited(&self) -> Result<(), String> {
        self.charge(
            &self.unsolicited,
            1,
            self.caps.unsolicited_messages,
            HostPhrase::BudgetUnsolicited.as_static(),
        )
    }

    /// The first breach, if the budget has tripped.
    #[must_use]
    pub fn breach(&self) -> Option<String> {
        self.breach
            .lock()
            .unwrap_or_else(PoisonError::into_inner)
            .clone()
    }

    /// Run `start` only while the budget is intact.
    ///
    /// A breach is published under the same lock, so a start either runs
    /// before the breach exists or does not run at all. Keep `start` short.
    ///
    /// # Errors
    /// The breach message when the budget has tripped.
    pub fn admit<T>(&self, start: impl FnOnce() -> T) -> Result<T, String> {
        let breach = self.breach.lock().unwrap_or_else(PoisonError::into_inner);
        match breach.as_ref() {
            Some(m) => Err(m.clone()),
            None => Ok(start()),
        }
    }

    fn charge(&self, counter: &AtomicU64, n: u64, cap: u64, what: &str) -> Result<(), String> {
        let total = counter.fetch_add(n, Ordering::SeqCst).saturating_add(n);
        let mut breach = self.breach.lock().unwrap_or_else(PoisonError::into_inner);
        if total > cap {
            breach.get_or_insert_with(|| messages::budget_exceeded(cap, what));
        }
        breach.clone().map_or(Ok(()), Err)
    }
}
