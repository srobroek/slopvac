//! Git sources in `plugins sync` (bead 8l4.9.27; threat model F5, K11, N10, E8,
//! TM-40, TM-46). Repositories are local and reach the syncer through the
//! test-only rewrite seam, since a lock accepts `git+https://` alone.

mod oci_server;
mod revocations;
mod support;

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use oci_server::{Response, Server};
use revocations::{ListServer, Root, Signed, list_json};
use slopvac_plugins::PluginError;
use slopvac_plugins::extract::{Limits, tree_hash};
use slopvac_plugins::launch::Launcher;
use slopvac_plugins::lock::Lockfile;
use slopvac_plugins::oci::{Anonymous, Client};
use slopvac_plugins::revoke::Revocations;
use slopvac_plugins::sign::KeyPolicy;
use slopvac_plugins::sync::{Change, Network, Store, SyncError, SyncReport, Syncer, status};

const NOW: &str = "2026-11-14T00:00:00Z";
/// The locked URL of every test repository; the seam maps it to a directory.
const LOCKED_HOST: &str = "https://git.test/";

const FILES: &[(&str, &[u8])] = &[
    ("pack.toml", b"id = \"style\"\n"),
    ("rules/a.yml", b"rule: a\n"),
];

/// A scratch `git` run with no user or system config.
fn git(dir: &Path, args: &[&str]) -> String {
    let out = Command::new("git")
        .current_dir(dir)
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_AUTHOR_NAME", "t")
        .env("GIT_AUTHOR_EMAIL", "t@example.invalid")
        .env("GIT_COMMITTER_NAME", "t")
        .env("GIT_COMMITTER_EMAIL", "t@example.invalid")
        .env("GIT_AUTHOR_DATE", "2026-11-01T00:00:00Z")
        .env("GIT_COMMITTER_DATE", "2026-11-01T00:00:00Z")
        .args(args)
        .output()
        .expect("git runs");
    assert!(
        out.status.success(),
        "git {args:?}: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8(out.stdout).unwrap().trim().to_owned()
}

/// A source repository with one commit.
struct Remote {
    dir: support::Scratch,
    commit: String,
}

impl Remote {
    fn path(&self) -> PathBuf {
        self.dir.path().join("repo")
    }

    /// Commit `files` (mode 100644, or 100755 when the name is in `executable`).
    fn with_files(files: &[(&str, &[u8])], executable: &[&str]) -> Self {
        Self::build(|work| {
            for (name, data) in files {
                let path = work.join(name);
                fs::create_dir_all(path.parent().unwrap()).unwrap();
                fs::write(&path, data).unwrap();
                git(work, &["add", "--", name]);
                if executable.contains(name) {
                    git(work, &["update-index", "--chmod=+x", "--", name]);
                }
            }
        })
    }

    fn build(fill: impl FnOnce(&Path)) -> Self {
        let dir = support::scratch();
        let work = dir.path().join("repo");
        fs::create_dir(&work).unwrap();
        git(&work, &["init", "--quiet"]);
        fill(&work);
        git(&work, &["commit", "--quiet", "--allow-empty", "-m", "pack"]);
        let commit = git(&work, &["rev-parse", "HEAD"]);
        Self { dir, commit }
    }

    /// A repository whose history is `first`, then `second` (which replaces the
    /// files). Returns the repository and the commit of `first`.
    fn history(first: &[(&str, &[u8])], second: &[(&str, &[u8])]) -> (Self, String) {
        let remote = Self::with_files(first, &[]);
        let earlier = remote.commit.clone();
        let work = remote.path();
        git(&work, &["rm", "-r", "-q", "--", "."]);
        for (name, data) in second {
            let path = work.join(name);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(&path, data).unwrap();
            git(&work, &["add", "--", name]);
        }
        git(&work, &["commit", "--quiet", "-m", "second"]);
        let head = git(&work, &["rev-parse", "HEAD"]);
        assert_ne!(head, earlier);
        (
            Self {
                commit: head,
                ..remote
            },
            earlier,
        )
    }

    fn lock(&self, digest: &str) -> Lockfile {
        Self::lock_at(&self.commit, digest)
    }

    fn lock_at(commit: &str, digest: &str) -> Lockfile {
        let text = format!(
            "schema_version = 3\n\n[[plugins]]\nid = \"style\"\nkind = \"data\"\nversion = \"1.0.0\"\n\
             slopvac_api = 1\nsource = \"git+{LOCKED_HOST}repo@{commit}\"\ndigest = \"{digest}\"\n",
        );
        Lockfile::parse(&text).unwrap()
    }

    /// The `file://` prefix that stands in for the locked host.
    fn served_from(&self) -> String {
        format!("file://{}/", self.dir.path().display())
    }
}

/// The tree hash of `files`, computed on a plain directory, not through git.
fn expected_digest(files: &[(&str, &[u8])]) -> String {
    let dir = support::scratch();
    for (name, data) in files {
        let path = dir.path().join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, data).unwrap();
    }
    tree_hash(dir.path()).unwrap().to_string()
}

struct Env {
    data: support::Scratch,
    project: support::Scratch,
    root: Root,
    list: ListServer,
}

impl Env {
    fn new() -> Self {
        let root = Root::new();
        let empty = Signed::by(
            &root,
            list_json("2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z", &[], &[]),
        );
        Self {
            data: support::scratch(),
            project: support::scratch(),
            root,
            list: ListServer::start(Some(empty)),
        }
    }

    fn store(&self) -> Store {
        Store::new(self.data.path().join("slopvac"))
    }

    fn sync(
        &self,
        network: Network<'_>,
        remote: &Remote,
        lock: &Lockfile,
    ) -> Result<SyncReport, SyncError> {
        self.sync_with(network, remote, lock, Limits::default())
    }

    fn sync_with(
        &self,
        network: Network<'_>,
        remote: &Remote,
        lock: &Lockfile,
        limits: Limits,
    ) -> Result<SyncReport, SyncError> {
        self.sync_from(network, &remote.served_from(), lock, limits)
    }

    /// Sync with the locked host standing in for `served_from`.
    fn sync_from(
        &self,
        network: Network<'_>,
        served_from: &str,
        lock: &Lockfile,
        limits: Limits,
    ) -> Result<SyncReport, SyncError> {
        self.sync_capped(network, served_from, lock, limits, None)
    }

    /// Like `sync_from`, with a memory limit for `git` in place of the default.
    fn sync_capped(
        &self,
        network: Network<'_>,
        served_from: &str,
        lock: &Lockfile,
        limits: Limits,
        memory: Option<u64>,
    ) -> Result<SyncReport, SyncError> {
        let launcher = Launcher::Program(launcher().into());
        self.sync_through(launcher, network, served_from, lock, limits, memory)
    }

    /// Like `sync_capped`, with `launcher` as the program that runs `git`.
    fn sync_through(
        &self,
        launcher: Launcher,
        network: Network<'_>,
        served_from: &str,
        lock: &Lockfile,
        limits: Limits,
        memory: Option<u64>,
    ) -> Result<SyncReport, SyncError> {
        let store = self.store();
        let revocations = Revocations::new(
            self.data.path().join("state"),
            vec![self.root.public()],
            self.list.source(),
            NOW,
        )
        .unwrap();
        let policy = KeyPolicy::default();
        let syncer = Syncer::new(&store, network, &policy, self.project.path(), &revocations)
            .with_limits(limits)
            .with_launcher(launcher)
            .with_git_rewrite_for_tests(LOCKED_HOST, served_from);
        match memory {
            Some(bytes) => syncer.with_git_memory_for_tests(bytes),
            None => syncer,
        }
        .sync(lock)
    }

    fn trees(&self) -> Vec<PathBuf> {
        fs::read_dir(self.data.path().join("slopvac/trees"))
            .map(|rd| {
                rd.flatten()
                    .map(|e| e.path())
                    .filter(|p| {
                        p.file_name()
                            .is_some_and(|n| n.to_string_lossy().starts_with("tree-"))
                    })
                    .collect()
            })
            .unwrap_or_default()
    }

    fn assert_no_trees(&self) {
        let trees = self.trees();
        assert!(trees.is_empty(), "unexpected trees: {trees:?}");
    }
}

/// The package's launcher binary, which runs `git` under resource limits.
fn launcher() -> &'static str {
    env!("CARGO_BIN_EXE_slopvac-plugin-launcher")
}

fn client() -> Client {
    Client::with_loopback_http_for_tests(Box::new(Anonymous))
}

fn git_error(err: &SyncError) -> &str {
    match err {
        SyncError::Git { why, .. } => why,
        other => panic!("not a git error: {other:?}"),
    }
}

#[test]
fn a_commit_whose_tree_matches_the_lock_is_installed_without_git_metadata() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));

    let report = env.sync(Network::Online(&c), &remote, &lock).unwrap();

    assert_eq!(report.packs[0].change, Change::Installed);
    let tree = &report.packs[0].tree;
    assert_eq!(fs::read(tree.join("rules/a.yml")).unwrap(), b"rule: a\n");
    assert_eq!(
        fs::read(tree.join("pack.toml")).unwrap(),
        b"id = \"style\"\n"
    );
    assert!(!tree.join(".git").exists());
    let mut names: Vec<String> = fs::read_dir(tree)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().into_owned())
        .collect();
    names.sort();
    assert_eq!(names, ["pack.toml", "rules"]);
    let states = status(&env.store(), env.project.path(), &lock).unwrap();
    assert!(states[0].is_recorded(), "{states:?}");
}

#[test]
fn a_second_online_sync_uses_the_stored_tree() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));
    env.sync(Network::Online(&c), &remote, &lock).unwrap();
    // The repository is gone; only the stored tree can satisfy the sync now.
    fs::remove_dir_all(remote.path()).unwrap();

    let again = env.sync(Network::Online(&c), &remote, &lock).unwrap();

    assert_eq!(again.packs[0].change, Change::Unchanged);
}

/// This test binary never calls `launch::intercept`, so the current
/// executable is not a launcher.
#[test]
fn a_program_without_the_launcher_entry_point_syncs_no_git_source() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));

    let err = env
        .sync_through(
            Launcher::CurrentExe,
            Network::Online(&c),
            &remote.served_from(),
            &lock,
            Limits::default(),
            None,
        )
        .unwrap_err();

    let SyncError::Launcher { source, .. } = &err else {
        panic!("{err:?}");
    };
    assert_eq!(*source, PluginError::LauncherNotInstalled);
    assert_eq!(err.code(), "launcher-not-installed");
    assert_eq!(err.exit_code(), 2);
    assert_eq!(
        err.to_string(),
        "plugin `style`: the running program did not install the slopvac plugin launcher, \
         so plugins and git plugin sources cannot start"
    );
    env.assert_no_trees();
    // A refused sync has no side effects: no revocation fetch, no store, no
    // state directory.
    assert_eq!(env.list.fetches(), 0);
    let left: Vec<_> = fs::read_dir(env.data.path()).unwrap().collect();
    assert!(left.is_empty(), "unexpected entries: {left:?}");
}

#[test]
fn tm31_a_pinned_commit_whose_tree_differs_from_the_lock_exits_2_and_installs_nothing() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let other = expected_digest(&[("pack.toml", b"id = \"other\"\n")]);
    let lock = remote.lock(&other);

    let err = env.sync(Network::Online(&c), &remote, &lock).unwrap_err();

    let SyncError::DigestMismatch {
        expected, actual, ..
    } = &err
    else {
        panic!("{err:?}");
    };
    assert_eq!(expected, &other);
    assert_eq!(actual, &expected_digest(FILES));
    assert_eq!(err.code(), "digest-mismatch");
    assert_eq!(err.exit_code(), 2);
    env.assert_no_trees();
}

#[test]
fn offline_with_a_cold_cache_names_the_pack_and_digest() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let digest = expected_digest(FILES);
    let lock = remote.lock(&digest);

    let err = env.sync(Network::Offline, &remote, &lock).unwrap_err();

    assert_eq!(err.code(), "offline-plugin-missing");
    assert!(err.to_string().contains(&digest), "{err}");
    env.assert_no_trees();
}

#[test]
fn offline_with_a_warm_cache_installs_nothing_new_and_needs_no_git() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));
    let first = env.sync(Network::Online(&c), &remote, &lock).unwrap();
    fs::remove_dir_all(remote.path()).unwrap();

    let offline = env.sync(Network::Offline, &remote, &lock).unwrap();

    assert_eq!(offline.packs[0].change, Change::Unchanged);
    assert_eq!(offline.packs[0].tree, first.packs[0].tree);
}

#[cfg(unix)]
fn edit_stored_file(tree: &Path) {
    let file = tree.join("rules/a.yml");
    let mut perms = fs::metadata(&file).unwrap().permissions();
    #[allow(clippy::permissions_set_readonly_false)]
    perms.set_readonly(false);
    fs::set_permissions(&file, perms).unwrap();
    fs::write(&file, b"rule: evil\n").unwrap();
}

#[cfg(unix)]
#[test]
fn e8_a_modified_stored_tree_is_refused_offline_and_repaired_online() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));
    let first = env.sync(Network::Online(&c), &remote, &lock).unwrap();
    let tree = first.packs[0].tree.clone();

    edit_stored_file(&tree);
    let err = env.sync(Network::Offline, &remote, &lock).unwrap_err();
    assert!(matches!(err, SyncError::CacheTampered { .. }), "{err:?}");
    env.assert_no_trees();

    let again = env.sync(Network::Online(&c), &remote, &lock).unwrap();
    assert_eq!(again.packs[0].change, Change::Installed);
    assert_eq!(fs::read(tree.join("rules/a.yml")).unwrap(), b"rule: a\n");

    edit_stored_file(&tree);
    let repaired = env.sync(Network::Online(&c), &remote, &lock).unwrap();
    assert_eq!(repaired.packs[0].change, Change::Reinstalled);
    assert_eq!(fs::read(tree.join("rules/a.yml")).unwrap(), b"rule: a\n");
}

#[cfg(unix)]
#[test]
fn an_executable_file_keeps_its_bit_when_the_commit_lists_it() {
    use std::os::unix::fs::PermissionsExt;
    let files: &[(&str, &[u8])] = &[("bin/run", b"#!/bin/sh\n"), (".slopvac-exec", b"bin/run\n")];
    let remote = Remote::with_files(files, &["bin/run"]);
    // The expected digest comes from a plain directory with the same mode.
    let dir = support::scratch();
    fs::create_dir(dir.path().join("bin")).unwrap();
    fs::write(dir.path().join("bin/run"), b"#!/bin/sh\n").unwrap();
    fs::set_permissions(
        dir.path().join("bin/run"),
        fs::Permissions::from_mode(0o755),
    )
    .unwrap();
    fs::write(dir.path().join(".slopvac-exec"), b"bin/run\n").unwrap();
    let digest = tree_hash(dir.path()).unwrap().to_string();
    let env = Env::new();
    let c = client();

    let report = env
        .sync(Network::Online(&c), &remote, &remote.lock(&digest))
        .unwrap();

    let mode = fs::metadata(report.packs[0].tree.join("bin/run"))
        .unwrap()
        .permissions()
        .mode();
    assert_ne!(mode & 0o100, 0, "mode {mode:o}");
}

/// Commit a tree entry of `mode` named `name` that points at `target`.
fn add_special(work: &Path, mode: &str, name: &str, target: &str) {
    let blob = if mode == "160000" {
        target.to_owned()
    } else {
        fs::write(work.join(".blob"), target).unwrap();
        let id = git(work, &["hash-object", "-w", ".blob"]);
        fs::remove_file(work.join(".blob")).unwrap();
        id
    };
    git(
        work,
        &[
            "update-index",
            "--add",
            "--cacheinfo",
            &format!("{mode},{blob},{name}"),
        ],
    );
}

#[test]
fn n10_a_symlink_or_a_submodule_in_the_commit_is_refused() {
    let cases = [
        ("120000", "link", "../../etc/passwd", "symbolic link"),
        (
            "160000",
            "vendor",
            "1111111111111111111111111111111111111111",
            "submodule",
        ),
    ];
    for (mode, name, target, word) in cases {
        let remote = Remote::build(|work| {
            fs::write(work.join("pack.toml"), b"id = \"style\"\n").unwrap();
            git(work, &["add", "pack.toml"]);
            add_special(work, mode, name, target);
        });
        let env = Env::new();
        let c = client();
        let lock = remote.lock(&expected_digest(&[("pack.toml", b"id = \"style\"\n")]));

        let err = env.sync(Network::Online(&c), &remote, &lock).unwrap_err();

        assert!(git_error(&err).contains(word), "{err}");
        assert!(git_error(&err).contains(name), "{err}");
        assert_eq!(err.exit_code(), 2);
        env.assert_no_trees();
    }
}

#[cfg(unix)]
#[test]
fn tm40_hooks_filters_and_attributes_in_the_repository_do_nothing() {
    use std::os::unix::fs::PermissionsExt;
    let marker_dir = support::scratch();
    let marker = marker_dir.path().join("ran");
    let marker_text = marker.display().to_string();
    let script = format!("#!/bin/sh\ntouch '{marker_text}'\n");
    let remote = Remote::build(|work| {
        fs::write(work.join("pack.toml"), b"id = \"style\"\n").unwrap();
        fs::write(work.join("stamp.txt"), b"$Format:%H$\n").unwrap();
        fs::write(
            work.join(".gitattributes"),
            b"* filter=evil\nstamp.txt export-subst\n",
        )
        .unwrap();
        fs::write(
            work.join(".gitmodules"),
            b"[submodule \"m\"]\n\tpath = m\n\turl = file:///nonexistent\n",
        )
        .unwrap();
        git(work, &["add", "--all"]);
    });
    // Armed after the commit, so only a later git run could trigger them.
    let work = remote.path();
    let hooks = work.join(".git/hooks");
    for hook in [
        "post-checkout",
        "post-merge",
        "post-commit",
        "reference-transaction",
        "pre-auto-gc",
        "fsmonitor-watchman",
    ] {
        let path = hooks.join(hook);
        fs::write(&path, &script).unwrap();
        fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).unwrap();
    }
    for (key, value) in [
        ("filter.evil.smudge", format!("touch '{marker_text}'; cat")),
        ("filter.evil.clean", format!("touch '{marker_text}'; cat")),
        ("filter.evil.process", format!("touch '{marker_text}'")),
        ("core.fsmonitor", format!("touch '{marker_text}'")),
        ("core.hooksPath", hooks.display().to_string()),
    ] {
        git(&work, &["config", key, &value]);
    }
    let files: &[(&str, &[u8])] = &[
        ("pack.toml", b"id = \"style\"\n"),
        ("stamp.txt", b"$Format:%H$\n"),
        (".gitattributes", b"* filter=evil\nstamp.txt export-subst\n"),
        (
            ".gitmodules",
            b"[submodule \"m\"]\n\tpath = m\n\turl = file:///nonexistent\n",
        ),
    ];
    let env = Env::new();
    let c = client();

    let report = env
        .sync(
            Network::Online(&c),
            &remote,
            &remote.lock(&expected_digest(files)),
        )
        .unwrap();

    assert!(!marker.exists(), "repository content ran code");
    // The substitution did not happen: the committed bytes are what installs.
    assert_eq!(
        fs::read(report.packs[0].tree.join("stamp.txt")).unwrap(),
        b"$Format:%H$\n"
    );
}

#[test]
fn a_transport_other_than_https_is_refused_before_git_starts() {
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));
    let marker = env.project.path().join("ran");
    let store = env.store();
    let revocations = Revocations::new(
        env.data.path().join("state"),
        vec![env.root.public()],
        env.list.source(),
        NOW,
    )
    .unwrap();
    let policy = KeyPolicy::default();
    let hostile = format!("ext::sh -c 'touch {}' #", marker.display());

    let err = Syncer::new(
        &store,
        Network::Online(&c),
        &policy,
        env.project.path(),
        &revocations,
    )
    .with_launcher(Launcher::Program(launcher().into()))
    .with_git_rewrite_for_tests(LOCKED_HOST, &hostile)
    .sync(&lock)
    .unwrap_err();

    assert!(git_error(&err).contains("https"), "{err}");
    assert!(!marker.exists());
    env.assert_no_trees();
}

#[test]
fn a_repository_larger_than_the_download_limit_is_refused() {
    // Incompressible bytes from a fixed generator.
    let mut state = 0x9E37_79B9_7F4A_7C15_u64;
    let noise: Vec<u8> = (0..64 * 1024)
        .map(|_| {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            state.to_le_bytes()[0]
        })
        .collect();
    let remote = Remote::with_files(&[("big.bin", &noise)], &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(&[("big.bin", &noise)]));
    let limits = Limits {
        compressed_bytes: 1024,
        ..Limits::default()
    };

    let err = env
        .sync_with(Network::Online(&c), &remote, &lock, limits)
        .unwrap_err();

    // The watcher and the check after the fetch report the same kind.
    assert!(matches!(err, SyncError::GitLimit { .. }), "{err:?}");
    assert!(err.to_string().contains("download exceeds 1024"), "{err}");
    // A git source over its limits keeps the catch-all code.
    assert_eq!(err.code(), "sync-failed");
    env.assert_no_trees();
}
#[test]
fn a_small_pack_of_a_huge_blob_is_refused_before_the_blob_is_read() {
    // 8 MiB of zeros packs to a few KiB, far below the download limit, and
    // expands past the 1 MiB expanded-size limit.
    let zeros = vec![0u8; 8 << 20];
    let remote = Remote::with_files(&[("zeros.bin", &zeros)], &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(&[("zeros.bin", &zeros)]));
    let limits = Limits {
        expanded_bytes: 1 << 20,
        ..Limits::default()
    };

    let err = env
        .sync_with(Network::Online(&c), &remote, &lock, limits)
        .unwrap_err();

    assert!(matches!(err, SyncError::GitLimit { .. }), "{err:?}");
    assert!(err.to_string().contains("size limit"), "{err}");
    env.assert_no_trees();
}

#[test]
fn a_commit_with_more_files_than_the_entry_limit_is_refused() {
    let files: &[(&str, &[u8])] = &[("a", b"1"), ("b", b"2"), ("c", b"3")];
    let remote = Remote::with_files(files, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(files));
    let limits = Limits {
        entries: 2,
        ..Limits::default()
    };

    let err = env
        .sync_with(Network::Online(&c), &remote, &lock, limits)
        .unwrap_err();

    assert!(matches!(err, SyncError::GitLimit { .. }), "{err:?}");
    env.assert_no_trees();
}

#[test]
fn a_commit_with_more_nodes_than_the_limit_installs_nothing() {
    let files: &[(&str, &[u8])] = &[("a/b/one.txt", b"1"), ("a/b/two.txt", b"2")];
    let remote = Remote::with_files(files, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(files));
    // `a`, `a/b` and two files are four nodes.
    let limits = Limits {
        nodes: 3,
        ..Limits::default()
    };

    let err = env
        .sync_with(Network::Online(&c), &remote, &lock, limits)
        .unwrap_err();

    assert!(
        matches!(err, SyncError::Extract { .. }) && err.to_string().contains("more than 3"),
        "{err:?}"
    );
    env.assert_no_trees();
}

#[test]
fn the_pinned_commit_is_installed_even_when_the_branch_moved_on() {
    let first: &[(&str, &[u8])] = &[("pack.toml", b"id = \"old\"\n")];
    let second: &[(&str, &[u8])] = &[("pack.toml", b"id = \"new\"\n"), ("extra.yml", b"x\n")];
    let (remote, earlier) = Remote::history(first, second);
    let env = Env::new();
    let c = client();
    let lock = Remote::lock_at(&earlier, &expected_digest(first));

    let report = env.sync(Network::Online(&c), &remote, &lock).unwrap();

    let tree = &report.packs[0].tree;
    assert_eq!(fs::read(tree.join("pack.toml")).unwrap(), b"id = \"old\"\n");
    assert!(!tree.join("extra.yml").exists());
}

#[test]
fn a_redirect_from_the_remote_is_not_followed() {
    // CWE-918: the remote answers its first request with a redirect to an
    // internal endpoint. Git must stop there instead of calling the target.
    let target = Server::start(|_| Response::new(200));
    let target_url = format!("http://{}/internal", target.registry());
    let redirector = Server::start(move |_| Response::new(302).header("Location", &target_url));
    let remote = Remote::with_files(FILES, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(FILES));
    let served_from = format!("http://{}/", redirector.registry());

    let err = env
        .sync_from(Network::Online(&c), &served_from, &lock, Limits::default())
        .unwrap_err();

    assert!(matches!(err, SyncError::Git { .. }), "{err:?}");
    assert!(
        !redirector.requests().is_empty(),
        "the remote was not asked"
    );
    assert!(
        target.requests().is_empty(),
        "git followed the redirect: {:?}",
        target.requests()
    );
    env.assert_no_trees();
}
/// Hostile text: an escape sequence, a literal backslash, a bidi override and a newline.
const HOSTILE: &str = "a\u{1b}[31m\\b\u{202e}c\nd";
/// What a reader must see: each unsafe character as a visible escape, the
/// backslash doubled, and nothing escaped twice.
const HOSTILE_SHOWN: &str = "a\\u{1b}[31m\\\\b\\u{202e}c\\u{a}d";

#[test]
fn git_error_text_is_escaped_once_with_a_doubled_backslash() {
    let id: slopvac_plugins::lock::PackId = "style".parse().unwrap();
    let git = SyncError::Git {
        id: id.clone(),
        why: HOSTILE.into(),
    };
    let limit = SyncError::GitLimit {
        id,
        why: HOSTILE.into(),
    };

    assert_eq!(
        git.to_string(),
        format!("plugin `style`: git source: {HOSTILE_SHOWN}")
    );
    assert_eq!(
        limit.to_string(),
        format!("plugin `style`: git source passes a limit: {HOSTILE_SHOWN}")
    );
}

#[test]
fn a_hostile_path_in_a_refused_commit_is_escaped_exactly_once() {
    // A symbolic link whose name is hostile: the refusal names it.
    let name = "a\u{1b}[31m\\b";
    let remote = Remote::build(|work| {
        fs::write(work.join("pack.toml"), b"id = \"style\"\n").unwrap();
        git(work, &["add", "pack.toml"]);
        add_special(work, "120000", name, "target");
    });
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(&[("pack.toml", b"id = \"style\"\n")]));

    let err = env.sync(Network::Online(&c), &remote, &lock).unwrap_err();

    assert_eq!(
        err.to_string(),
        "plugin `style`: git source: `a\\u{1b}[31m\\\\b` is a symbolic link"
    );
}

/// 100 MiB of a repeating pattern, with the last byte set to `last`.
#[cfg(target_os = "linux")]
fn huge(last: u8) -> Vec<u8> {
    let mut data: Vec<u8> = (0..100usize << 20)
        .map(|i| u8::try_from(i % 251).unwrap())
        .collect();
    *data.last_mut().unwrap() = last;
    data
}

// Regression for the delta-memory residual of CWE-409 (threat model E4): two
// near-identical large blobs are sent as one base and one delta, and
// `index-pack` rebuilds the delta in memory. Run through the launcher with a
// 64 MiB data limit, git must fail. Without the limit the sync succeeds (the
// digest below is the real one), so `unwrap_err` panics: that is the
// revert-check. Linux only: macOS enforces no memory limit (residual R2).
#[cfg(target_os = "linux")]
#[test]
fn a_deep_delta_chain_to_a_huge_object_is_stopped_by_the_memory_cap() {
    let (a, b) = (huge(1), huge(2));
    let files: &[(&str, &[u8])] = &[("a.bin", &a), ("b.bin", &b)];
    let remote = Remote::with_files(files, &[]);
    let env = Env::new();
    let c = client();
    let lock = remote.lock(&expected_digest(files));

    let err = env
        .sync_capped(
            Network::Online(&c),
            &remote.served_from(),
            &lock,
            Limits::default(),
            Some(64 << 20),
        )
        .unwrap_err();

    assert!(matches!(err, SyncError::Git { .. }), "{err:?}");
    env.assert_no_trees();
}
