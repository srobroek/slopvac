//! Installed-binary smoke tests for the commands whose logic lives in owner crates:
//! `terms`, `genre`, `validate`, `setup` and `prime`. Each gets its help and one real
//! behaviour, plus path redaction where the command prints a user path.

use assert_cmd::Command;
use predicates::prelude::*;
use std::fs;
use std::path::Path;

fn slopvac(dir: &Path) -> Command {
    let mut cmd = Command::cargo_bin("slopvac").expect("binary builds");
    for var in [
        "SLOPVAC_OFFLINE",
        "SLOPVAC_LOG",
        "FORCE_COLOR",
        "CLICOLOR_FORCE",
    ] {
        cmd.env_remove(var);
    }
    cmd.env("NO_COLOR", "1").current_dir(dir);
    cmd
}

#[test]
fn every_wired_command_has_help() {
    let dir = tempfile::tempdir().unwrap();
    for (name, about) in [
        ("terms", "Manage project terms"),
        ("genre", "Print the genre of each file"),
        (
            "validate",
            "Check config, front matter and inline directives",
        ),
        ("setup", "Install or remove project-local steering"),
        ("prime", "Print guidance for agents"),
    ] {
        slopvac(dir.path())
            .args([name, "--help"])
            .assert()
            .code(0)
            .stdout(predicate::str::contains(about));
    }
}

#[test]
fn terms_lists_the_built_in_terms() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .args(["terms", "list", "--builtin"])
        .assert()
        .code(0)
        .stdout(predicate::str::contains("Python\tlanguage\tbuiltin\n"));
}

#[test]
fn terms_add_writes_the_project_terms_file() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .args(["terms", "add", "Foo"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("added Foo"));
    assert!(dir.path().join(".slopvac/terms.toml").is_file());
}

#[test]
fn terms_error_names_an_external_file_without_its_directories() {
    let dir = tempfile::tempdir().unwrap();
    let outside = tempfile::Builder::new()
        .prefix("SENTINEL ext")
        .tempdir()
        .unwrap();
    let file = outside.path().join("t.toml");
    fs::write(&file, "not = [valid").unwrap();
    let out = slopvac(dir.path())
        .args(["terms", "list", "--files"])
        .arg(&file)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[terms-parse]: cannot parse <external>/t.toml"),
        "{err}"
    );
    assert!(!err.contains("SENTINEL"), "{err}");
}

#[test]
fn genre_prints_the_genre_and_its_scores() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("a.md"), "# Title\n\nWord.\n").unwrap();
    slopvac(dir.path())
        .args(["genre", "a.md"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("a.md: consumer (default)\n"));
}

const TUTORIAL_BLOCK: &str = "---\nslopvac:\n  v: 3\n  genre: tutorial\n---\n# Title\n";

/// `genre` reads the declared genre under the project's front matter policy, as `lint` does.
#[rstest::rstest]
#[case::default_policy(None, "a.md: tutorial (explicit)\n")]
#[case::explicitly_allowed(
    Some("[frontmatter]\nallow = [\"genre\"]\n"),
    "a.md: tutorial (explicit)\n"
)]
#[case::front_matter_disabled(
    Some("[frontmatter]\nenabled = false\n"),
    "a.md: consumer (default)\n"
)]
fn genre_reads_the_block_under_the_project_policy(
    #[case] policy: Option<&str>,
    #[case] first_line: &str,
) {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("a.md"), TUTORIAL_BLOCK).unwrap();
    if let Some(policy) = policy {
        fs::write(
            dir.path().join("slopvac.toml"),
            format!("schema_version = 3\n\n{policy}"),
        )
        .unwrap();
    }
    slopvac(dir.path())
        .args(["genre", "a.md"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with(first_line));
}

#[test]
fn genre_reports_block_errors_with_a_code_and_exit_2() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(
        dir.path().join("a.md"),
        "---\nslopvac:\n  v: 3\n  genre: tutorial\n  locale: PRIVATE_SENTINEL\n---\n# Title\n",
    )
    .unwrap();
    fs::write(
        dir.path().join("slopvac.toml"),
        "schema_version = 3\n\n[frontmatter]\nallow = [\"locale\"]\n",
    )
    .unwrap();
    slopvac(dir.path())
        .args(["genre", "a.md"])
        .assert()
        .code(2)
        .stdout(predicate::str::starts_with("a.md: consumer (default)\n"))
        .stderr(predicate::str::contains(
            "error[config-frontmatter-field-denied]",
        ))
        .stderr(
            predicate::str::contains("a.md:")
                .and(predicate::str::contains("PRIVATE_SENTINEL").not()),
        );
}

/// A link resolves to the file that the config search starts from, as `lint` resolves it.
#[rstest::rstest]
#[case::nested_target("sub/real.md", "sub")]
#[case::external_target("../outside/real.md", "../outside")]
fn genre_finds_the_config_of_the_resolved_file(#[case] target: &str, #[case] config_dir: &str) {
    let root = tempfile::tempdir().unwrap();
    let project = root.path().join("project");
    for dir in ["project/sub", "outside"] {
        fs::create_dir_all(root.path().join(dir)).unwrap();
    }
    let real = project.join(target);
    fs::write(&real, TUTORIAL_BLOCK).unwrap();
    // The config next to the real file turns front matter off. The link's own directory has none.
    fs::write(
        project.join(config_dir).join("slopvac.toml"),
        "schema_version = 3\n\n[frontmatter]\nenabled = false\n",
    )
    .unwrap();
    std::os::unix::fs::symlink(&real, project.join("link.md")).unwrap();
    slopvac(&project)
        .args(["genre", "link.md"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("link.md: consumer (default)\n"));
}

#[test]
fn genre_refuses_an_unreadable_project_config() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("a.md"), TUTORIAL_BLOCK).unwrap();
    fs::write(
        dir.path().join("slopvac.toml"),
        "schema_version = 3\nnonsense = 1\n",
    )
    .unwrap();
    slopvac(dir.path())
        .args(["genre", "a.md"])
        .assert()
        .code(2)
        .stdout("")
        .stderr(predicate::str::contains("error[config-unknown-key]"));
}

#[test]
fn genre_assign_makes_the_choice_explicit() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("a.md"), "# Title\n").unwrap();
    slopvac(dir.path())
        .args(["genre", "a.md", "--assign", "*.md=tutorial"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("a.md: tutorial (explicit)\n"));
}

#[test]
fn validate_passes_a_good_config_and_names_the_count() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(dir.path().join("slopvac.toml"), "schema_version = 3\n").unwrap();
    slopvac(dir.path())
        .arg("validate")
        .assert()
        .code(0)
        .stdout("checked 1 file(s): 0 problem(s)\n");
}

#[test]
fn validate_exits_2_with_a_stable_code_for_a_bad_config() {
    let dir = tempfile::tempdir().unwrap();
    fs::write(
        dir.path().join("slopvac.toml"),
        "schema_version = 3\nlocale = \"klingon\"\n",
    )
    .unwrap();
    slopvac(dir.path())
        .arg("validate")
        .assert()
        .code(2)
        .stdout(predicate::str::starts_with("error[config-invalid-value]: "))
        .stdout(predicate::str::contains("1 problem(s)"));
}

#[test]
fn validate_prints_a_schema_for_editors() {
    let dir = tempfile::tempdir().unwrap();
    let out = slopvac(dir.path())
        .args(["validate", "--schema", "config"])
        .assert()
        .code(0)
        .get_output()
        .stdout
        .clone();
    let value: serde_json::Value = serde_json::from_slice(&out).unwrap();
    assert!(
        value["$id"]
            .as_str()
            .unwrap()
            .ends_with("config.schema.json")
    );
}

#[test]
fn setup_list_names_every_harness() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .args(["setup", "--list"])
        .assert()
        .code(0)
        .stdout(predicate::str::contains("agents ").and(predicate::str::contains("claude ")));
}

#[test]
fn setup_writes_steering_and_check_then_passes() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .args(["setup", "agents"])
        .assert()
        .code(0);
    assert!(dir.path().join("AGENTS.md").is_file());
    slopvac(dir.path())
        .args(["setup", "agents", "--check"])
        .assert()
        .code(0);
}

#[test]
fn setup_check_exits_1_when_steering_is_missing() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .args(["setup", "agents", "--check"])
        .assert()
        .code(1);
}

#[test]
fn setup_under_an_external_root_prints_no_absolute_path() {
    let work = tempfile::tempdir().unwrap();
    let outside = tempfile::Builder::new()
        .prefix("SENTINEL ext")
        .tempdir()
        .unwrap();
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root"])
        .arg(outside.path())
        .output()
        .unwrap();
    let text = String::from_utf8_lossy(&out.stdout);
    assert_eq!(out.status.code(), Some(0));
    assert!(text.contains("<external>/AGENTS.md"), "{text}");
    assert!(!text.contains("SENTINEL"), "{text}");
}

#[test]
fn prime_prints_the_base_guide_and_topics() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .arg("prime")
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("# Slopvac agent guidance"));
    slopvac(dir.path())
        .args(["prime", "write"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("# Prime: write"));
}

#[test]
fn prime_refuses_an_unknown_topic_as_a_usage_error() {
    let dir = tempfile::tempdir().unwrap();
    slopvac(dir.path())
        .args(["prime", "nonsense"])
        .assert()
        .code(2)
        .stderr(predicate::str::starts_with("error[usage]: "));
}

/// A directory whose absolute path holds a space and a sentinel.
fn external() -> tempfile::TempDir {
    tempfile::Builder::new()
        .prefix("SENTINEL ext")
        .tempdir()
        .unwrap()
}

fn assert_clean(text: &str, outside: &tempfile::TempDir) {
    for leaked in ["SENTINEL", &outside.path().display().to_string()] {
        assert!(!text.contains(leaked), "{leaked} leaked: {text}");
    }
}

#[test]
fn setup_error_under_an_external_root_names_the_file_without_its_directories() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    // A lone begin marker makes the steering file malformed.
    fs::write(outside.path().join("AGENTS.md"), "<!-- slopvac:begin -->\n").unwrap();
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root"])
        .arg(outside.path())
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[steering-malformed]: malformed or ambiguous slopvac markers in <external>/AGENTS.md;"),
        "{err}"
    );
    assert_clean(&err, &outside);
}

#[test]
fn setup_error_under_a_relative_external_root_hides_the_parent_directories() {
    let base = tempfile::tempdir().unwrap();
    let work = base.path().join("work");
    fs::create_dir(&work).unwrap();
    let private = base.path().join("private-project");
    fs::create_dir(&private).unwrap();
    fs::write(private.join("AGENTS.md"), "<!-- slopvac:begin -->\n").unwrap();
    let out = slopvac(&work)
        .args(["setup", "agents", "--root", "../private-project"])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[steering-malformed]: malformed or ambiguous slopvac markers in <external>/AGENTS.md;"),
        "{err}"
    );
    assert!(!err.contains("private-project"), "{err}");
}

#[test]
fn setup_with_a_missing_relative_root_shows_the_root_once() {
    let work = tempfile::tempdir().unwrap();
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root", "missing"])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(!err.contains("missing/missing"), "{err}");
}

/// A run directory whose project root is a directory named `AGENTS.md`, so the root and the
/// project-relative steering path share their leading component.
fn root_named_like_the_steering_file(content: &[u8]) -> tempfile::TempDir {
    let work = tempfile::tempdir().unwrap();
    let root = work.path().join("AGENTS.md");
    fs::create_dir(&root).unwrap();
    fs::write(root.join("AGENTS.md"), content).unwrap();
    work
}

#[test]
fn setup_error_for_a_root_named_like_the_steering_file_keeps_both_components() {
    let work = root_named_like_the_steering_file(b"\xff\xfe");
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root", "AGENTS.md"])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[steering-not-utf8]: steering must be UTF-8: AGENTS.md/AGENTS.md"),
        "{err}"
    );
}

#[test]
fn setup_unclosed_fence_for_a_root_named_like_the_steering_file_keeps_both_components() {
    let work = root_named_like_the_steering_file(b"```sh\nno closing fence\n");
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root", "AGENTS.md"])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with(
            "error[steering-malformed]: AGENTS.md/AGENTS.md has an unterminated code fence"
        ),
        "{err}"
    );
}

#[test]
fn setup_malformed_markers_for_a_root_named_like_the_steering_file_keep_both_components() {
    let work = root_named_like_the_steering_file(b"<!-- slopvac:begin -->\n");
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root", "AGENTS.md"])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(err.contains("markers in AGENTS.md/AGENTS.md;"), "{err}");
}

#[cfg(unix)]
#[test]
fn setup_error_under_a_symlinked_root_that_points_outside_is_external() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    fs::write(outside.path().join("AGENTS.md"), "<!-- slopvac:begin -->\n").unwrap();
    std::os::unix::fs::symlink(outside.path(), work.path().join("link")).unwrap();
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root", "link"])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(err.contains("markers in <external>/AGENTS.md;"), "{err}");
    assert_clean(&err, &outside);
    assert!(!err.contains("link"), "{err}");
}

#[test]
fn genre_error_for_an_unreadable_external_file_hides_its_directories() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    let missing = outside.path().join("gone.md");
    let out = slopvac(work.path())
        .arg("genre")
        .arg(&missing)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[genre-failed]: <external>/gone.md: "),
        "{err}"
    );
    assert_clean(&err, &outside);
}

/// The document size cap, 64 MiB (policies 1.9).
const DOCUMENT_CAP: u64 = 64 * 1024 * 1024;

fn sparse(path: &Path, len: u64) {
    fs::File::create(path)
        .and_then(|f| f.set_len(len))
        .expect("sparse file");
}

#[test]
fn genre_refuses_a_file_one_byte_over_the_document_cap() {
    let work = tempfile::tempdir().unwrap();
    sparse(&work.path().join("big.md"), DOCUMENT_CAP + 1);
    slopvac(work.path())
        .args(["genre", "big.md"])
        .assert()
        .code(2)
        .stderr(predicate::str::starts_with(
            "error[document-too-large]: big.md: larger than the 64 MiB document limit",
        ));
}

#[test]
fn genre_reads_a_file_exactly_at_the_document_cap() {
    let work = tempfile::tempdir().unwrap();
    sparse(&work.path().join("edge.md"), DOCUMENT_CAP);
    slopvac(work.path())
        .args(["genre", "edge.md"])
        .assert()
        .code(0)
        .stdout(predicate::str::starts_with("edge.md: "));
}

#[cfg(unix)]
#[test]
fn genre_refuses_a_fifo_without_blocking() {
    let work = tempfile::tempdir().unwrap();
    let made = std::process::Command::new("mkfifo")
        .arg(work.path().join("trap.md"))
        .status()
        .expect("mkfifo runs");
    assert!(made.success());
    slopvac(work.path())
        .timeout(std::time::Duration::from_secs(20))
        .args(["genre", "trap.md"])
        .assert()
        .code(2)
        .stderr(predicate::str::starts_with(
            "error[input-unreadable]: trap.md: cannot read",
        ));
}

/// Hostile file names and how a diagnostic must show them: each control or bidi character as
/// a `\u{..}` escape, so the name cannot move the cursor, start a line or reorder text.
const HOSTILE_NAMES: [(&str, &str); 3] = [
    ("x\u{1b}[2Jy.md", "x\\u{1b}[2Jy.md"),
    ("x\ny.md", "x\\u{a}y.md"),
    ("x\u{202e}y.md", "x\\u{202e}y.md"),
];

fn assert_one_clean_line(err: &str) {
    assert_eq!(err.lines().count(), 1, "{err:?}");
    assert!(
        !err.chars().any(|c| c.is_control() && c != '\n') && !err.contains('\u{202e}'),
        "{err:?}"
    );
}

#[rstest::rstest]
#[case::escape(0)]
#[case::newline(1)]
#[case::bidi(2)]
fn genre_escapes_a_hostile_name_in_the_too_large_refusal(#[case] which: usize) {
    let (name, shown) = HOSTILE_NAMES[which];
    let work = tempfile::tempdir().unwrap();
    sparse(&work.path().join(name), DOCUMENT_CAP + 1);
    let out = slopvac(work.path()).args(["genre", name]).output().unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(
        err,
        format!("error[document-too-large]: {shown}: larger than the 64 MiB document limit\n")
    );
    assert_one_clean_line(&err);
}

#[cfg(unix)]
#[rstest::rstest]
#[case::escape(0)]
#[case::newline(1)]
#[case::bidi(2)]
fn genre_escapes_a_hostile_name_in_the_unreadable_refusal(#[case] which: usize) {
    let (name, shown) = HOSTILE_NAMES[which];
    let work = tempfile::tempdir().unwrap();
    let made = std::process::Command::new("mkfifo")
        .arg(work.path().join(name))
        .status()
        .expect("mkfifo runs");
    assert!(made.success());
    let out = slopvac(work.path())
        .timeout(std::time::Duration::from_secs(20))
        .args(["genre", name])
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert_eq!(
        err,
        format!("error[input-unreadable]: {shown}: cannot read\n")
    );
    assert_one_clean_line(&err);
}

#[test]
fn validate_names_a_missing_external_document_without_its_directories() {
    let work = tempfile::tempdir().unwrap();
    fs::write(work.path().join("slopvac.toml"), "schema_version = 3\n").unwrap();
    let outside = external();
    let out = slopvac(work.path())
        .arg("validate")
        .arg(outside.path().join("gone.md"))
        .output()
        .unwrap();
    let text = String::from_utf8_lossy(&out.stdout);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        text.contains("error[config-io]: cannot read <external>/gone.md: no such file"),
        "{text}"
    );
    assert_clean(&text, &outside);
}

#[test]
fn validate_names_an_external_directory_entry_without_its_directories() {
    let work = tempfile::tempdir().unwrap();
    fs::write(work.path().join("slopvac.toml"), "schema_version = 3\n").unwrap();
    let outside = external();
    fs::write(
        outside.path().join("doc.md"),
        "---\nslopvac:\n  locale: klingon\n---\n\nText.\n",
    )
    .unwrap();
    let out = slopvac(work.path())
        .arg("validate")
        .arg(outside.path())
        .output()
        .unwrap();
    let text = String::from_utf8_lossy(&out.stdout);
    assert_eq!(out.status.code(), Some(1), "{text}");
    assert!(text.contains(" --> <external>/doc.md:3:3"), "{text}");
    assert_clean(&text, &outside);
}

#[test]
fn prime_with_a_missing_absolute_config_hides_its_directories_and_prefix_repeat() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    let out = slopvac(work.path())
        .args(["prime", "--config"])
        .arg(outside.path().join("nope.toml"))
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[config-io]: cannot read <external>/nope.toml: no such file"),
        "{err}"
    );
    assert_clean(&err, &outside);
}

#[test]
fn prime_with_a_missing_config_under_the_working_directory_shows_it_relative() {
    let work = tempfile::Builder::new()
        .prefix("SENTINEL cwd")
        .tempdir()
        .unwrap();
    let out = slopvac(work.path())
        .args(["prime", "--config"])
        .arg(
            work.path()
                .canonicalize()
                .unwrap()
                .join("sub dir")
                .join("nope.toml"),
        )
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.contains("cannot read sub dir/nope.toml: no such file"),
        "{err}"
    );
    assert_clean(&err, &work);
}

#[test]
fn setup_with_a_nonexistent_absolute_root_hides_its_directories() {
    let work = tempfile::Builder::new()
        .prefix("SENTINEL cwd")
        .tempdir()
        .unwrap();
    // The working directory as the process reports it, so the root sits under it.
    let root = work
        .path()
        .canonicalize()
        .unwrap()
        .join("no dir")
        .join("deeper");
    let out = slopvac(work.path())
        .args(["setup", "agents", "--root"])
        .arg(&root)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(err.contains("no dir/deeper"), "{err}");
    assert_clean(&err, &work);
}

#[test]
fn prime_with_a_bad_guidance_level_never_prints_url_credentials() {
    let dir = tempfile::tempdir().unwrap();
    let config = dir.path().join("slopvac.toml");
    fs::write(
        &config,
        "schema_version = 3\n\n[guidance]\nlevel = \"https://user:secret@example.com\"\n",
    )
    .unwrap();
    let out = slopvac(dir.path())
        .args(["prime", "--config"])
        .arg(&config)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(err.starts_with("error[config-invalid-value]: "), "{err}");
    assert!(!err.contains("secret"), "credentials leaked: {err}");
    assert!(err.contains("https://example.com"), "the host stays: {err}");
}

#[test]
fn a_quote_inside_an_unquoted_path_does_not_end_it() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    let missing = outside
        .path()
        .join("a\"b")
        .join("private dir")
        .join("nope.toml");
    let out = slopvac(work.path())
        .args(["prime", "--config"])
        .arg(&missing)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[config-io]: cannot read <external>/nope.toml: no such file"),
        "{err}"
    );
    for leaked in ["private", "a\"b", "SENTINEL"] {
        assert!(!err.contains(leaked), "{leaked} leaked: {err}");
    }
}

#[test]
fn a_config_path_that_contains_a_colon_and_space_is_redacted_whole() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    let missing = outside
        .path()
        .join("a: b")
        .join("private dir")
        .join("nope.toml");
    let out = slopvac(work.path())
        .args(["prime", "--config"])
        .arg(&missing)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with("error[config-io]: cannot read <external>/nope.toml: no such file"),
        "{err}"
    );
    for leaked in ["private", "a: b", "SENTINEL"] {
        assert!(!err.contains(leaked), "{leaked} leaked: {err}");
    }
}

#[test]
fn prime_with_an_oversize_config_names_the_file_and_the_cap_without_its_directories() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    let big = outside.path().join("big dir").join("slopvac.toml");
    fs::create_dir_all(big.parent().unwrap()).unwrap();
    fs::write(
        &big,
        format!("schema_version = 3\n# {}\n", "x".repeat(1024 * 1024 + 1)),
    )
    .unwrap();
    let out = slopvac(work.path())
        .args(["prime", "--config"])
        .arg(&big)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(
        err.starts_with(
            "error[config-too-large]: <external>/slopvac.toml is larger than 1048576 bytes"
        ),
        "{err}"
    );
    assert_clean(&err, &outside);
    assert!(!err.contains("big dir"), "{err}");
}

#[test]
fn terms_with_an_oversize_file_names_it_without_its_directories() {
    let work = tempfile::tempdir().unwrap();
    let outside = external();
    let big = outside.path().join("big dir").join("terms.toml");
    fs::create_dir_all(big.parent().unwrap()).unwrap();
    fs::write(
        &big,
        format!("schema_version = 3\n# {}\n", "x".repeat(1024 * 1024 + 1)),
    )
    .unwrap();
    let out = slopvac(work.path())
        .args(["terms", "list", "--files"])
        .arg(&big)
        .output()
        .unwrap();
    let err = String::from_utf8_lossy(&out.stderr);
    assert_eq!(out.status.code(), Some(2));
    assert!(err.starts_with("error[terms-file-too-large]: "), "{err}");
    assert!(
        err.contains("<external>/terms.toml is larger than"),
        "{err}"
    );
    assert_clean(&err, &outside);
    assert!(!err.contains("big dir"), "{err}");
}
