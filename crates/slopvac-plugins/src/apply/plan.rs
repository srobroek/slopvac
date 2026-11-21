//! Applying a recipe plan.
//!
//! A plan is checked as a whole before anything is written. If any entry is
//! refused, no entry is written. After that the entries apply one by one. This
//! is not a transaction: a failure part-way (a race, a full disk) stops the run,
//! leaves the rest as [`EntryStatus::NotAttempted`], and keeps the files already
//! written. The report says which is which.
//!
//! Each entry keeps the parent directory handle it was checked through, and
//! writes only through it. A component swapped for a symlink after the check
//! cannot redirect the write.
//!
//! On Windows the plan is checked but never applied. `cap-std` implements
//! rename, delete and create-directory there through absolute paths rebuilt from
//! the handle, which a junction swapped in meanwhile can redirect. Every
//! mutating entry is refused with [`ApplyError::UnsupportedOnWindows`].

use std::collections::HashSet;
use std::path::Path;

use crate::hooks::{RecipeAction, RecipeFile};

use super::fs::{
    Current, Expect, Located, Stage, case_twin, locate, read_current, remove, replace,
};
use super::sensitive::{HarnessWarning, deny_reason, harness_warnings};
use super::{ApplyError, WriteOutcome};

/// Settings the caller passes in. Nothing here is read from a plugin.
#[derive(Debug, Clone, Default)]
pub struct PlanOptions {
    /// Check and report, and write nothing.
    pub dry_run: bool,
    /// Paths approved for writing although they are on the deny list
    /// (`--allow-sensitive <path>`). Compared case-insensitively against the
    /// path as the plan names it, and against the path after symlinked parents
    /// resolve when that differs.
    pub allow_sensitive: Vec<String>,
}

/// What happened to one plan entry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EntryStatus {
    /// Checked and acceptable. Not written because of a dry run or because
    /// another entry was refused.
    Planned,
    /// Applied.
    Done(WriteOutcome),
    /// Refused before anything was written.
    Refused(ApplyError),
    /// Failed while applying. Entries before it stay written.
    Failed(ApplyError),
    /// Not tried because an earlier entry failed.
    NotAttempted,
}

/// The report line for one plan entry.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanEntry {
    /// Path as the plan names it.
    pub path: String,
    /// Requested action.
    pub action: RecipeAction,
    /// Root-relative path after symlinked parents resolve, when it could be
    /// worked out.
    pub resolved: Option<String>,
    /// Why the path is on the deny list, if it is.
    pub sensitive: Option<&'static str>,
    /// Whether the caller approved the sensitive path.
    pub approved: bool,
    /// Agent-harness marks (O8) for the path as written and for the resolved
    /// path. Show them with the plan.
    pub warnings: Vec<HarnessWarning>,
    /// What happened.
    pub status: EntryStatus,
}

/// The outcome of [`apply_plan`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanReport {
    /// One entry per plan file, in plan order.
    pub entries: Vec<PlanEntry>,
    /// Whether any file was created, replaced or removed.
    pub wrote: bool,
}

impl PlanReport {
    /// Whether any entry was refused or failed.
    #[must_use]
    pub fn has_problems(&self) -> bool {
        self.entries.iter().any(|e| {
            matches!(
                e.status,
                EntryStatus::Refused(_) | EntryStatus::Failed(_) | EntryStatus::NotAttempted
            )
        })
    }
}

/// An entry that passed the checks, with the state and directory it was
/// checked against.
struct Checked {
    at: Located,
    expect: Current,
}

fn merge_warnings(into: &mut Vec<HarnessWarning>, more: Vec<HarnessWarning>) {
    for w in more {
        if !into.contains(&w) {
            into.push(w);
        }
    }
}

fn check(
    root: &Path,
    file: &RecipeFile,
    options: &PlanOptions,
    windows: bool,
    seen: &mut HashSet<String>,
    entry: &mut PlanEntry,
) -> Result<Checked, ApplyError> {
    let at = locate(root, &file.path, windows)?;
    entry.resolved = Some(at.resolved.clone());
    if at.resolved != file.path {
        let content = file.content.as_deref();
        merge_warnings(&mut entry.warnings, harness_warnings(&at.resolved, content));
    }
    if !seen.insert(at.resolved.to_lowercase()) {
        return Err(ApplyError::DuplicatePath(file.path.clone()));
    }
    let mut needs = Vec::new();
    for p in [file.path.as_str(), at.resolved.as_str()] {
        if let Some(why) = deny_reason(p) {
            entry.sensitive.get_or_insert(why);
            if !needs.iter().any(|n: &String| n.eq_ignore_ascii_case(p)) {
                needs.push(p.to_owned());
            }
        }
    }
    if !needs.is_empty() {
        let approved = |n: &String| {
            options
                .allow_sensitive
                .iter()
                .any(|a| a.eq_ignore_ascii_case(n))
        };
        entry.approved = needs.iter().all(approved);
        if !entry.approved {
            return Err(ApplyError::Sensitive {
                path: file.path.clone(),
                needs,
            });
        }
    }
    let needs_content = matches!(file.action, RecipeAction::Write | RecipeAction::Merge);
    if needs_content && file.content.is_none() {
        return Err(ApplyError::InvalidPlan(
            crate::messages::transport::TransportText::ApplyContentMissing {
                path: file.path.clone(),
            }
            .to_string(),
        ));
    }
    let current = match at.parent(false)? {
        None => Current::Absent,
        Some(parent) => {
            if let Some(existing) = case_twin(&parent, &at.name) {
                return Err(ApplyError::CaseCollision {
                    path: file.path.clone(),
                    existing,
                });
            }
            read_current(&parent, &at.name, &file.path)?
        }
    };
    if file.action == RecipeAction::Merge && current != Current::Absent {
        return Err(ApplyError::MergeUnsupported(file.path.clone()));
    }
    if windows {
        return Err(ApplyError::UnsupportedOnWindows(file.path.clone()));
    }
    Ok(Checked {
        at,
        expect: current,
    })
}

fn apply_one(
    file: &RecipeFile,
    checked: &Checked,
    hook: &mut dyn FnMut(Stage),
) -> Result<WriteOutcome, ApplyError> {
    let at = &checked.at;
    let expect = match &checked.expect {
        Current::File(bytes) => Expect::Bytes(bytes),
        Current::Absent => Expect::Absent,
    };
    match file.action {
        RecipeAction::Remove => match at.parent(false)? {
            Some(parent) => remove(&parent, &at.name, &file.path, &expect, hook),
            // The directory was absent when checked, so there is nothing to delete.
            None => Ok(WriteOutcome::Absent),
        },
        RecipeAction::Write | RecipeAction::Merge => {
            let parent = at.parent(true)?.ok_or_else(|| {
                ApplyError::Io(
                    crate::messages::transport::TransportText::ApplyNoDirectory {
                        path: at.resolved.clone(),
                    }
                    .to_string(),
                )
            })?;
            let content = file.content.as_deref().unwrap_or_default();
            replace(
                &parent,
                &at.name,
                &file.path,
                &expect,
                content.as_bytes(),
                hook,
            )
        }
    }
}

/// Check a plan and, unless `options.dry_run` is set, apply it under `root`.
///
/// `files` is a validated plan from [`parse_recipe`](crate::hooks::parse_recipe).
/// The checks repeat the path rules, so a plan built another way is safe too.
/// Merge into an existing file is refused until the contract defines block
/// markers; a merge into a missing file creates it. `remove` deletes the file.
/// On Windows every mutating entry is refused (see the module documentation).
#[must_use]
pub fn apply_plan(root: &Path, files: &[RecipeFile], options: &PlanOptions) -> PlanReport {
    run(root, files, options, cfg!(windows), &mut |_, _| {})
}

/// Test seam for [`apply_plan`]: pretend to run on `windows` (or not), and call
/// `between(index, stage)` at each point where a concurrent process could
/// change the file system. `index` is the plan entry being applied. Not part of
/// the supported API.
#[doc(hidden)]
#[must_use]
pub fn apply_plan_seam(
    root: &Path,
    files: &[RecipeFile],
    options: &PlanOptions,
    windows: bool,
    between: &mut dyn FnMut(usize, SeamStage),
) -> PlanReport {
    run(root, files, options, windows, &mut |i, s| {
        between(
            i,
            match s {
                Stage::Start => SeamStage::Start,
                Stage::BeforeOpen => SeamStage::BeforeOpen,
                Stage::TempWritten => SeamStage::TempWritten,
                Stage::BeforeCommit => SeamStage::BeforeCommit,
            },
        );
    })
}

/// Where [`apply_plan_seam`] lets a test act.
#[doc(hidden)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SeamStage {
    /// The whole plan was checked and this entry is about to be applied.
    Start,
    /// The target is about to be opened for its first read.
    BeforeOpen,
    /// The temporary file holds the new bytes.
    TempWritten,
    /// Just before the second source check and the rename or delete.
    BeforeCommit,
}

fn run(
    root: &Path,
    files: &[RecipeFile],
    options: &PlanOptions,
    windows: bool,
    between: &mut dyn FnMut(usize, Stage),
) -> PlanReport {
    let mut seen = HashSet::new();
    let mut entries = Vec::with_capacity(files.len());
    let mut checked = Vec::with_capacity(files.len());
    for file in files {
        let mut entry = PlanEntry {
            path: file.path.clone(),
            action: file.action,
            resolved: None,
            sensitive: None,
            approved: false,
            warnings: harness_warnings(&file.path, file.content.as_deref()),
            status: EntryStatus::Planned,
        };
        match check(root, file, options, windows, &mut seen, &mut entry) {
            Ok(c) => checked.push(Some(c)),
            Err(e) => {
                entry.status = EntryStatus::Refused(e);
                checked.push(None);
            }
        }
        entries.push(entry);
    }
    let mut report = PlanReport {
        entries,
        wrote: false,
    };
    if options.dry_run || report.has_problems() {
        return report;
    }
    let mut failed = false;
    for (i, ((file, entry), checked)) in files
        .iter()
        .zip(&mut report.entries)
        .zip(&checked)
        .enumerate()
    {
        let Some(checked) = checked else { continue };
        if failed {
            entry.status = EntryStatus::NotAttempted;
            continue;
        }
        between(i, Stage::Start);
        match apply_one(file, checked, &mut |s| between(i, s)) {
            Ok(outcome) => {
                report.wrote |= matches!(
                    outcome,
                    WriteOutcome::Created | WriteOutcome::Replaced | WriteOutcome::Removed
                );
                entry.status = EntryStatus::Done(outcome);
            }
            Err(e) => {
                entry.status = EntryStatus::Failed(e);
                failed = true;
            }
        }
    }
    report
}
