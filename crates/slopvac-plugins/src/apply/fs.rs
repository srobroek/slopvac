//! File-system steps shared by edits and plans. All access goes through a
//! `cap-std` directory handle for the project root.

use std::ffi::{OsStr, OsString};
use std::io::{ErrorKind, Read, Write};
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};

use cap_fs_ext::{DirExt, FollowSymlinks, OpenOptionsFollowExt};
use cap_std::ambient_authority;
use cap_std::fs::{Dir, OpenOptions, Permissions};

use crate::hooks::resolve_in_root;

use super::{ApplyError, WriteOutcome};

/// Points inside an application where a test can change the file system.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Stage {
    /// A plan entry is about to be applied, after the whole plan was checked.
    Start,
    /// The target was checked and is about to be opened.
    BeforeOpen,
    /// The temporary file holds the new bytes. Its mode is still the private one.
    TempWritten,
    /// The temporary file is final. The target is about to be checked again.
    BeforeCommit,
}

/// A target split into the directory that holds it and its file name.
///
/// The directory handle is opened once, at check time, and every later write
/// goes through it. Swapping a path component afterwards cannot redirect the
/// write, because the handle names the directory that was checked.
pub(crate) struct Located {
    /// Deepest directory of the resolved parent chain that exists.
    anchor: Dir,
    /// Directories below `anchor` that do not exist yet.
    missing: Vec<OsString>,
    /// File name.
    pub name: OsString,
    /// Root-relative path with `/` separators and symlinked parents resolved.
    pub resolved: String,
}

/// Characters and forms that Windows reads as something other than a name.
fn windows_unsafe(seg: &str) -> bool {
    seg.contains([':', '<', '>', '"', '|', '?', '*'])
}

/// Whether a name has the shape of a Windows 8.3 short-name alias, a `~`
/// followed by digits such as `GITHUB~1` or `WORKFL~1`.
pub(crate) fn short_name_alias(seg: &str) -> bool {
    seg.match_indices('~')
        .any(|(i, _)| seg[i + 1..].starts_with(|c: char| c.is_ascii_digit()))
}

/// Locate `rel` under `root` and check the route stays inside the root.
///
/// The final component is not followed here. The host checks in
/// [`resolve_in_root`] refuse a link that leaves the root, anywhere in the path.
/// With `windows` set, names that look like 8.3 aliases are refused too, since
/// they can reach a denied directory under another name.
pub(crate) fn locate(root: &Path, rel: &str, windows: bool) -> Result<Located, ApplyError> {
    if rel.split('/').any(windows_unsafe) {
        return Err(ApplyError::PathRefused(
            crate::messages::transport::TransportText::ApplyReservedCharacter {
                path: rel.to_owned(),
            }
            .to_string(),
        ));
    }
    if windows && rel.split('/').any(short_name_alias) {
        return Err(ApplyError::PathRefused(
            crate::messages::transport::TransportText::ApplyShortName {
                path: rel.to_owned(),
            }
            .to_string(),
        ));
    }
    resolve_in_root(root, rel).map_err(ApplyError::PathRefused)?;
    let canon = root
        .canonicalize()
        .map_err(|e| ApplyError::io(root.display(), &e))?;
    let (parent_str, name) = rel.rsplit_once('/').unwrap_or(("", rel));
    let parent_abs = if parent_str.is_empty() {
        canon.clone()
    } else {
        resolve_in_root(root, parent_str).map_err(ApplyError::PathRefused)?
    };
    let parent_rel = parent_abs
        .strip_prefix(&canon)
        .map_err(|_| {
            ApplyError::PathRefused(
                crate::messages::transport::TransportText::ApplyOutsideRoot {
                    path: rel.to_owned(),
                }
                .to_string(),
            )
        })?
        .to_owned();
    let comps: Vec<OsString> = parent_rel
        .components()
        .map(|c| c.as_os_str().to_owned())
        .collect();
    let mut resolved: Vec<String> = comps
        .iter()
        .map(|c| c.to_string_lossy().into_owned())
        .collect();
    resolved.push(name.to_owned());
    let mut anchor = Dir::open_ambient_dir(&canon, ambient_authority())
        .map_err(|e| ApplyError::io(canon.display(), &e))?;
    let mut depth = 0;
    for c in &comps {
        match anchor.open_dir_nofollow(c) {
            Ok(d) => anchor = d,
            Err(e) if e.kind() == ErrorKind::NotFound => break,
            Err(e) => {
                return Err(ApplyError::PathRefused(
                    crate::messages::transport::TransportText::ApplyParentType {
                        path: rel.to_owned(),
                        component: c.to_string_lossy().into_owned(),
                        detail: e.to_string(),
                    }
                    .to_string(),
                ));
            }
        }
        depth += 1;
    }
    Ok(Located {
        anchor,
        missing: comps[depth..].to_vec(),
        name: OsString::from(name),
        resolved: resolved.join("/"),
    })
}

impl Located {
    /// The parent directory, creating the missing levels when asked.
    ///
    /// Each level is made and opened relative to the previous handle, without
    /// following a link that appeared in the meantime. Without `create`, a
    /// missing directory gives `Ok(None)`.
    pub(crate) fn parent(&self, create: bool) -> Result<Option<Dir>, ApplyError> {
        let fail = |e: std::io::Error| ApplyError::io(&self.resolved, &e);
        let mut dir = self.anchor.try_clone().map_err(fail)?;
        for c in &self.missing {
            if !create {
                return Ok(None);
            }
            match dir.create_dir(c) {
                Ok(()) => {}
                Err(e) if e.kind() == ErrorKind::AlreadyExists => {}
                Err(e) => return Err(fail(e)),
            }
            dir = dir.open_dir_nofollow(c).map_err(fail)?;
        }
        Ok(Some(dir))
    }

    /// The parent directory, which must exist.
    pub(crate) fn open_parent(&self) -> Result<Dir, ApplyError> {
        self.parent(false)?.ok_or_else(|| {
            ApplyError::Io(
                crate::messages::transport::TransportText::ApplyDirectoryMissing {
                    path: self.resolved.clone(),
                }
                .to_string(),
            )
        })
    }
}

/// What a target holds right now.
#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Current {
    Absent,
    File(Vec<u8>),
}

#[cfg(unix)]
#[allow(clippy::unnecessary_wraps)]
fn link_count(_: &cap_std::fs::File, m: &cap_std::fs::Metadata) -> std::io::Result<u64> {
    use cap_std::fs::MetadataExt;
    Ok(m.nlink())
}

#[cfg(windows)]
fn link_count(f: &cap_std::fs::File, _: &cap_std::fs::Metadata) -> std::io::Result<u64> {
    let std_file = f.try_clone()?.into_std();
    Ok(winapi_util::file::information(&std_file)?.number_of_links())
}

/// Read the target without following a final symlink.
///
/// Refuses a symlink, a non-regular file and a file with several hard links.
pub(crate) fn read_current(parent: &Dir, name: &OsStr, shown: &str) -> Result<Current, ApplyError> {
    read_current_at(parent, name, shown, None, &mut |_| {}).map(|(current, _)| current)
}

/// Like [`read_current`], but reads at most `max` bytes: a longer file is an
/// error, and no more than `max + 1` bytes are ever held.
pub(crate) fn read_current_limited(
    parent: &Dir,
    name: &OsStr,
    shown: &str,
    max: u64,
) -> Result<Current, ApplyError> {
    read_current_at(parent, name, shown, Some(max), &mut |_| {}).map(|(current, _)| current)
}

/// Make the open return at once for a pipe or device that was swapped in.
#[cfg(unix)]
pub(crate) fn nonblocking(opts: &mut OpenOptions) -> Result<(), ApplyError> {
    use cap_std::fs::OpenOptionsExt;
    let flag = i32::try_from(rustix::fs::OFlags::NONBLOCK.bits()).map_err(|_| {
        ApplyError::Io(
            crate::messages::transport::TransportPhrase::ApplyNonblock
                .as_static()
                .into(),
        )
    })?;
    opts.custom_flags(flag);
    Ok(())
}

#[cfg(not(unix))]
#[allow(clippy::unnecessary_wraps)]
pub(crate) fn nonblocking(_: &mut OpenOptions) -> Result<(), ApplyError> {
    Ok(())
}

/// Read the target and, from the same open handle, its permissions.
fn read_current_at(
    parent: &Dir,
    name: &OsStr,
    shown: &str,
    max: Option<u64>,
    hook: &mut dyn FnMut(Stage),
) -> Result<(Current, Option<Permissions>), ApplyError> {
    // A cheap look first, so that a pipe or device is never opened for reading.
    match parent.symlink_metadata(name) {
        Ok(m) if m.file_type().is_symlink() => return Err(ApplyError::Symlink(shown.into())),
        Ok(m) if !m.is_file() => return Err(ApplyError::NotRegularFile(shown.into())),
        Ok(_) => {}
        Err(e) if e.kind() == ErrorKind::NotFound => return Ok((Current::Absent, None)),
        Err(e) => return Err(ApplyError::io(shown, &e)),
    }
    hook(Stage::BeforeOpen);
    let mut opts = OpenOptions::new();
    opts.read(true).follow(FollowSymlinks::No);
    nonblocking(&mut opts)?;
    let mut file = match parent.open_with(name, &opts) {
        Ok(f) => f,
        Err(e) => {
            // The name may have become a symlink after the look above.
            let swapped = parent
                .symlink_metadata(name)
                .is_ok_and(|m| m.file_type().is_symlink());
            return Err(if swapped {
                ApplyError::Symlink(shown.into())
            } else {
                ApplyError::io(shown, &e)
            });
        }
    };
    let meta = file.metadata().map_err(|e| ApplyError::io(shown, &e))?;
    if meta.file_type().is_symlink() {
        // Windows opens the reparse point itself.
        return Err(ApplyError::Symlink(shown.into()));
    }
    if !meta.is_file() {
        return Err(ApplyError::NotRegularFile(shown.into()));
    }
    let links = link_count(&file, &meta).map_err(|e| ApplyError::io(shown, &e))?;
    if links > 1 {
        return Err(ApplyError::Hardlinked(shown.into()));
    }
    let mut bytes = Vec::new();
    let mut reader = (&mut file).take(max.map_or(u64::MAX, |m| m.saturating_add(1)));
    reader
        .read_to_end(&mut bytes)
        .map_err(|e| ApplyError::io(shown, &e))?;
    if max.is_some_and(|m| bytes.len() as u64 > m) {
        return Err(ApplyError::TooLarge(shown.into()));
    }
    Ok((Current::File(bytes), Some(meta.permissions())))
}

/// What the target must hold for a write or delete to go ahead.
pub(crate) enum Expect<'a> {
    /// These exact bytes.
    Bytes(&'a [u8]),
    /// No file.
    Absent,
}

impl Expect<'_> {
    /// The most bytes the target may hold for the expectation to hold. A
    /// longer file is not read: reads stop one byte past this.
    fn limit(&self) -> u64 {
        match self {
            Self::Bytes(want) => want.len() as u64,
            Self::Absent => 0,
        }
    }

    fn holds(&self, now: &Current) -> bool {
        match (self, now) {
            (Self::Bytes(want), Current::File(have)) => have == want,
            (Self::Absent, Current::Absent) => true,
            _ => false,
        }
    }
}

static TEMP_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Create a fresh temporary file next to the target.
///
/// On Unix it starts private (0600), so the new bytes are never readable by
/// others while the file is being filled.
fn create_temp(parent: &Dir, shown: &str) -> Result<(OsString, cap_std::fs::File), ApplyError> {
    let mut opts = OpenOptions::new();
    opts.write(true).create_new(true);
    #[cfg(unix)]
    {
        use cap_std::fs::OpenOptionsExt;
        opts.mode(0o600);
    }
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_or(0, |d| d.subsec_nanos());
    for _ in 0..100 {
        let n = TEMP_COUNTER.fetch_add(1, Ordering::Relaxed);
        let name = OsString::from(format!(".slopvac-{}-{stamp}-{n}.tmp", std::process::id()));
        match parent.open_with(&name, &opts) {
            Ok(f) => return Ok((name, f)),
            Err(e) if e.kind() == ErrorKind::AlreadyExists => {}
            Err(e) => return Err(ApplyError::io(shown, &e)),
        }
    }
    Err(ApplyError::Io(
        crate::messages::transport::TransportText::ApplyTemporaryName {
            path: shown.to_owned(),
        }
        .to_string(),
    ))
}

/// Replace or create the target with `new`, atomically.
///
/// Steps: read the target (no-follow, regular, one link), compare it with
/// `expect`, write a private temporary file, give it the original mode, sync
/// it, read the target again, and rename over it only if it is unchanged.
/// Ownership is not copied: the replacement belongs to the user who applies it.
///
/// A target longer than `expect` is not read whole: it counts as changed.
pub(crate) fn replace(
    parent: &Dir,
    name: &OsStr,
    shown: &str,
    expect: &Expect<'_>,
    new: &[u8],
    hook: &mut dyn FnMut(Stage),
) -> Result<WriteOutcome, ApplyError> {
    replace_bounded(parent, name, shown, expect, new, hook).map_err(|e| match e {
        ApplyError::TooLarge(shown) => ApplyError::SourceChanged(shown),
        other => other,
    })
}

/// [`replace`], but a target longer than `expect` fails with
/// [`ApplyError::TooLarge`] instead of [`ApplyError::SourceChanged`].
pub(crate) fn replace_bounded(
    parent: &Dir,
    name: &OsStr,
    shown: &str,
    expect: &Expect<'_>,
    new: &[u8],
    hook: &mut dyn FnMut(Stage),
) -> Result<WriteOutcome, ApplyError> {
    let limit = expect.limit();
    let (first, perms) = read_current_at(parent, name, shown, Some(limit), hook)?;
    let changed = || ApplyError::SourceChanged(shown.into());
    if !expect.holds(&first) {
        return Err(changed());
    }
    if matches!(&first, Current::File(have) if have == new) {
        return Ok(WriteOutcome::Unchanged);
    }
    let (tmp, file) = create_temp(parent, shown)?;
    let finish = |mut file: cap_std::fs::File| -> Result<WriteOutcome, ApplyError> {
        let io = |e: std::io::Error| ApplyError::io(shown, &e);
        file.write_all(new).map_err(io)?;
        hook(Stage::TempWritten);
        // The mode comes from the handle that was validated, never from a
        // second lookup of the name.
        if let Some(perms) = perms {
            file.set_permissions(perms).map_err(io)?;
        }
        file.sync_all().map_err(io)?;
        // Windows cannot rename a file while a handle to it is open.
        drop(file);
        hook(Stage::BeforeCommit);
        if read_current_limited(parent, name, shown, limit)? != first {
            return Err(changed());
        }
        parent.rename(&tmp, parent, name).map_err(io)?;
        Ok(match first {
            Current::Absent => WriteOutcome::Created,
            Current::File(_) => WriteOutcome::Replaced,
        })
    };
    let result = finish(file);
    if result.is_err() {
        let _ = parent.remove_file(&tmp);
    }
    result
}

/// Delete the target if it still matches `expect` and is a regular file with
/// one link.
///
/// An absent target stays absent: a file that appeared after the check is
/// reported as changed and not deleted.
pub(crate) fn remove(
    parent: &Dir,
    name: &OsStr,
    shown: &str,
    expect: &Expect<'_>,
    hook: &mut dyn FnMut(Stage),
) -> Result<WriteOutcome, ApplyError> {
    let changed = || ApplyError::SourceChanged(shown.into());
    let (first, _) = read_current_at(parent, name, shown, None, hook)?;
    if !expect.holds(&first) {
        return Err(changed());
    }
    if first == Current::Absent {
        return Ok(WriteOutcome::Absent);
    }
    hook(Stage::BeforeCommit);
    if read_current(parent, name, shown)? != first {
        return Err(changed());
    }
    parent
        .remove_file(name)
        .map_err(|e| ApplyError::io(shown, &e))?;
    Ok(WriteOutcome::Removed)
}

/// An entry of `parent` whose name equals `name` except for case.
pub(crate) fn case_twin(parent: &Dir, name: &OsStr) -> Option<String> {
    let want = name.to_string_lossy().to_lowercase();
    parent.entries().ok()?.flatten().find_map(|entry| {
        let have = entry.file_name();
        (have != name && have.to_string_lossy().to_lowercase() == want)
            .then(|| have.to_string_lossy().into_owned())
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dir(path: &Path) -> Dir {
        Dir::open_ambient_dir(path, ambient_authority()).unwrap()
    }

    fn noop(_: Stage) {}

    #[test]
    fn tm15_a_rename_race_before_the_commit_loses_nothing_and_leaves_no_temporary_file() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("a.md");
        std::fs::write(&target, "original").unwrap();
        let parent = dir(tmp.path());
        let got = replace(
            &parent,
            OsStr::new("a.md"),
            "a.md",
            &Expect::Bytes(b"original"),
            b"ours",
            &mut |s| {
                if s == Stage::BeforeCommit {
                    std::fs::write(&target, "racer").unwrap();
                }
            },
        );
        assert_eq!(got, Err(ApplyError::SourceChanged("a.md".into())));
        assert_eq!(std::fs::read_to_string(&target).unwrap(), "racer");
        assert_eq!(std::fs::read_dir(tmp.path()).unwrap().count(), 1);
    }

    #[test]
    fn tm15_a_file_created_by_a_racer_is_not_overwritten_by_a_create() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("new.md");
        let parent = dir(tmp.path());
        let got = replace(
            &parent,
            OsStr::new("new.md"),
            "new.md",
            &Expect::Absent,
            b"ours",
            &mut |s| {
                if s == Stage::BeforeCommit {
                    std::fs::write(&target, "racer").unwrap();
                }
            },
        );
        assert_eq!(got, Err(ApplyError::SourceChanged("new.md".into())));
        assert_eq!(std::fs::read_to_string(&target).unwrap(), "racer");
    }

    #[test]
    fn tm15_a_hardlink_made_before_the_commit_stops_the_rename() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("a.md");
        std::fs::write(&target, "original").unwrap();
        let parent = dir(tmp.path());
        let got = replace(
            &parent,
            OsStr::new("a.md"),
            "a.md",
            &Expect::Bytes(b"original"),
            b"ours",
            &mut |s| {
                if s == Stage::BeforeCommit {
                    std::fs::hard_link(&target, tmp.path().join("alias.md")).unwrap();
                }
            },
        );
        assert_eq!(got, Err(ApplyError::Hardlinked("a.md".into())));
        assert_eq!(std::fs::read_to_string(&target).unwrap(), "original");
        assert_eq!(
            std::fs::read_to_string(tmp.path().join("alias.md")).unwrap(),
            "original"
        );
        assert_eq!(std::fs::read_dir(tmp.path()).unwrap().count(), 2);
    }

    #[test]
    fn tm15_a_delete_of_an_absent_target_refuses_a_file_that_appeared() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("late.md"), "precious").unwrap();
        let parent = dir(tmp.path());
        let got = remove(
            &parent,
            OsStr::new("late.md"),
            "late.md",
            &Expect::Absent,
            &mut noop,
        );
        assert_eq!(got, Err(ApplyError::SourceChanged("late.md".into())));
        assert_eq!(
            std::fs::read_to_string(tmp.path().join("late.md")).unwrap(),
            "precious"
        );
    }

    #[test]
    fn tm15_a_delete_refuses_a_file_that_changed_since_the_check() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("a.md");
        std::fs::write(&target, "checked").unwrap();
        let parent = dir(tmp.path());
        let got = remove(
            &parent,
            OsStr::new("a.md"),
            "a.md",
            &Expect::Bytes(b"checked"),
            &mut |s| {
                if s == Stage::BeforeCommit {
                    std::fs::write(&target, "new work").unwrap();
                }
            },
        );
        assert_eq!(got, Err(ApplyError::SourceChanged("a.md".into())));
        assert_eq!(std::fs::read_to_string(&target).unwrap(), "new work");
    }

    #[cfg(unix)]
    #[test]
    fn tm15_a_target_swapped_for_a_symlink_before_the_commit_is_not_replaced_through() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("a.md");
        std::fs::write(&target, "original").unwrap();
        std::fs::write(tmp.path().join("other"), "other").unwrap();
        let parent = dir(tmp.path());
        let got = replace(
            &parent,
            OsStr::new("a.md"),
            "a.md",
            &Expect::Bytes(b"original"),
            b"ours",
            &mut |s| {
                if s == Stage::BeforeCommit {
                    std::fs::remove_file(&target).unwrap();
                    std::os::unix::fs::symlink("other", &target).unwrap();
                }
            },
        );
        assert_eq!(got, Err(ApplyError::Symlink("a.md".into())));
        assert_eq!(
            std::fs::read_to_string(tmp.path().join("other")).unwrap(),
            "other"
        );
    }

    #[cfg(unix)]
    #[test]
    fn tm15_a_symlink_swapped_in_between_the_look_and_the_open_is_not_followed() {
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("a.md");
        std::fs::write(&target, "original").unwrap();
        std::fs::write(tmp.path().join("other"), "other").unwrap();
        let parent = dir(tmp.path());
        let got = read_current_at(&parent, OsStr::new("a.md"), "a.md", None, &mut |s| {
            if s == Stage::BeforeOpen {
                std::fs::remove_file(&target).unwrap();
                std::os::unix::fs::symlink("other", &target).unwrap();
            }
        })
        .map(|(c, _)| c);
        assert_eq!(got, Err(ApplyError::Symlink("a.md".into())));
    }

    #[cfg(unix)]
    #[test]
    fn the_temporary_file_is_private_while_it_is_filled_and_gets_the_original_mode_before_the_rename()
     {
        use std::os::unix::fs::PermissionsExt;
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("a.md");
        std::fs::write(&target, "original").unwrap();
        std::fs::set_permissions(&target, std::fs::Permissions::from_mode(0o644)).unwrap();
        let parent = dir(tmp.path());
        let temp_mode = || {
            let t = std::fs::read_dir(tmp.path())
                .unwrap()
                .map(|e| e.unwrap().path())
                .find(|p| p.extension().is_some_and(|e| e == "tmp"))
                .unwrap();
            std::fs::metadata(t).unwrap().permissions().mode() & 0o777
        };
        let mut seen = Vec::new();
        replace(
            &parent,
            OsStr::new("a.md"),
            "a.md",
            &Expect::Bytes(b"original"),
            b"ours",
            &mut |s| {
                if matches!(s, Stage::TempWritten | Stage::BeforeCommit) {
                    seen.push((s, temp_mode()));
                }
            },
        )
        .unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(
            seen,
            [(Stage::TempWritten, 0o600), (Stage::BeforeCommit, 0o644)]
        );
    }

    #[cfg(unix)]
    #[test]
    fn the_mode_comes_from_the_validated_handle_not_from_a_second_lookup_of_the_name() {
        use std::os::unix::fs::PermissionsExt;
        let tmp = tempfile::tempdir().unwrap();
        let target = tmp.path().join("secret.md");
        std::fs::write(&target, "same").unwrap();
        std::fs::set_permissions(&target, std::fs::Permissions::from_mode(0o600)).unwrap();
        let parent = dir(tmp.path());
        // After the temporary file is filled, the name is replaced by a
        // world-readable file with the same bytes, which passes the second check.
        let got = replace(
            &parent,
            OsStr::new("secret.md"),
            "secret.md",
            &Expect::Bytes(b"same"),
            b"edited",
            &mut |s| {
                if s == Stage::TempWritten {
                    std::fs::remove_file(&target).unwrap();
                    std::fs::write(&target, "same").unwrap();
                    std::fs::set_permissions(&target, std::fs::Permissions::from_mode(0o644))
                        .unwrap();
                }
            },
        );
        assert_eq!(got, Ok(WriteOutcome::Replaced));
        let mode = std::fs::metadata(&target).unwrap().permissions().mode() & 0o777;
        assert_eq!(mode, 0o600);
        assert_eq!(std::fs::read_to_string(&target).unwrap(), "edited");
    }

    #[cfg(unix)]
    #[test]
    fn a_fifo_swapped_in_before_the_open_is_refused_and_never_blocks() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("a.md"), "original").unwrap();
        let (tx, rx) = std::sync::mpsc::channel();
        let path = tmp.path().to_owned();
        std::thread::spawn(move || {
            let parent = dir(&path);
            let target = path.join("a.md");
            let got = read_current_at(&parent, OsStr::new("a.md"), "a.md", None, &mut |s| {
                if s == Stage::BeforeOpen {
                    std::fs::remove_file(&target).unwrap();
                    let made = std::process::Command::new("mkfifo")
                        .arg(&target)
                        .status()
                        .unwrap();
                    assert!(made.success());
                }
            })
            .map(|(c, _)| c);
            let _ = tx.send(got);
        });
        let got = rx
            .recv_timeout(std::time::Duration::from_secs(10))
            .expect("the open blocked on a FIFO");
        assert_eq!(got, Err(ApplyError::NotRegularFile("a.md".into())));
    }

    #[test]
    fn short_name_aliases_are_recognised_by_their_tilde_and_digits() {
        for alias in ["GITHUB~1", "WORKFL~1", "progra~12", "a~1.md", "x~9.yml"] {
            assert!(short_name_alias(alias), "{alias}");
        }
        for plain in ["a~b", "~", "~x1", "notes", "a~", "tilde~.md"] {
            assert!(!short_name_alias(plain), "{plain}");
        }
    }
}
