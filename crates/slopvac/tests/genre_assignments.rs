//! `[[genres]]` assignments in `slopvac.toml` reach the engine: each document gets the genre
//! its path selects, and the genre sets the level of `docs-discipline.history-internal-reference`
//! (`docs/contract/config.md`, `docs/contract/packs.md` section 4).

use std::fs;

use assert_cmd::Command;
use serde_json::Value;

mod support;

const HISTORY: &str = "# Notes\n\nWe refactored the parser.\n";

const CONFIG: &str = r#"schema_version = 3

[[genres]]
files = ["guide/**"]
genre = "consumer"

[[genres]]
files = ["notes/**"]
genre = "internal"

[[genres]]
files = ["log/**", "!log/keep/**"]
genre = "change-comms"
"#;

fn slopvac() -> Command {
    let mut cmd = Command::cargo_bin("slopvac").expect("binary builds");
    cmd.current_dir(support::neutral_dir());
    for var in [
        "SLOPVAC_OFFLINE",
        "SLOPVAC_LOG",
        "FORCE_COLOR",
        "CLICOLOR_FORCE",
    ] {
        cmd.env_remove(var);
    }
    cmd.env("NO_COLOR", "1");
    cmd
}

fn document<'a>(report: &'a Value, suffix: &str) -> &'a Value {
    report["documents"]
        .as_array()
        .expect("documents")
        .iter()
        .find(|d| d["path"].as_str().is_some_and(|p| p.ends_with(suffix)))
        .unwrap_or_else(|| panic!("no document ends with {suffix}: {report}"))
}

fn history_levels(document: &Value) -> Vec<String> {
    document["findings"]
        .as_array()
        .expect("findings")
        .iter()
        .filter(|f| f["rule_id"] == "core:docs-discipline.history-internal-reference")
        .map(|f| f["severity"].as_str().expect("severity").to_owned())
        .collect()
}

#[test]
fn genres_blocks_choose_the_genre_and_level_of_each_document() {
    let dir = tempfile::tempdir().expect("tempdir");
    fs::write(dir.path().join("slopvac.toml"), CONFIG).expect("write config");
    for rel in [
        "guide/a.md",
        "notes/b.md",
        "log/c.md",
        "log/keep/d.md",
        "reference/e.md",
    ] {
        let path = dir.path().join(rel);
        fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        fs::write(path, HISTORY).expect("write document");
    }
    let out = slopvac()
        .args(["lint", "--format", "json"])
        .arg(dir.path())
        .output()
        .expect("run");
    let report: Value = serde_json::from_slice(&out.stdout).expect("a JSON report");

    // (document, genre, source, the path-glob evidence that names the matching block)
    let assigned: [(&str, &str, &str, &[&str]); 3] = [
        (
            "a.md",
            "consumer",
            "`[[genres]]` block 0 matches `guide/a.md`",
            &["warning"],
        ),
        (
            "b.md",
            "internal",
            "`[[genres]]` block 1 matches `notes/b.md`",
            &["suggestion"],
        ),
        (
            "c.md",
            "change-comms",
            "`[[genres]]` block 2 matches `log/c.md`",
            &[],
        ),
    ];
    for (suffix, genre, detail, levels) in assigned {
        let doc = document(&report, suffix);
        assert_eq!(doc["genre"]["id"], genre, "{suffix}: {doc}");
        assert_eq!(doc["genre"]["source"], "explicit", "{suffix}: {doc}");
        assert_eq!(doc["genre"]["reasons"][0]["signal"], "path-glob", "{doc}");
        assert_eq!(doc["genre"]["reasons"][0]["detail"], detail, "{doc}");
        assert_eq!(history_levels(doc), levels, "{suffix}: {doc}");
    }
    // The negated pattern frees this file from block 2, so no assignment names it and no
    // genre reaches its threshold: the registry default applies.
    let freed = document(&report, "d.md");
    assert_eq!(freed["genre"]["id"], "consumer", "{freed}");
    assert_eq!(freed["genre"]["source"], "default", "{freed}");
    // No block selects this file, so its path is detected as a reference page.
    let unassigned = document(&report, "e.md");
    assert_eq!(unassigned["genre"]["id"], "reference", "{unassigned}");
    assert_eq!(unassigned["genre"]["source"], "detected", "{unassigned}");
}

/// Lint a project with `config` and one document `notes/n.md`, which `CONFIG`-style blocks
/// assign to `internal`. Returns the exit code and the report.
fn lint_note(config: &str, text: &str) -> (Option<i32>, Value) {
    let dir = tempfile::tempdir().expect("tempdir");
    fs::write(dir.path().join("slopvac.toml"), config).expect("write config");
    let path = dir.path().join("notes/n.md");
    fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    fs::write(path, text).expect("write document");
    let out = slopvac()
        .args(["lint", "--format", "json"])
        .arg(dir.path())
        .output()
        .expect("run");
    let report = serde_json::from_slice(&out.stdout).expect("a JSON report");
    (out.status.code(), report)
}

const ASSIGNED: &str =
    "schema_version = 3\n\n[[genres]]\nfiles = [\"notes/**\"]\ngenre = \"internal\"\n";

#[test]
fn a_top_level_genre_key_never_overrides_the_assignment() {
    let text = format!("---\ngenre: reference\n---\n{HISTORY}");
    let (_, report) = lint_note(ASSIGNED, &text);
    let doc = document(&report, "n.md");
    assert_eq!(doc["genre"]["id"], "internal", "{doc}");
    assert_eq!(doc["genre"]["source"], "explicit", "{doc}");
    assert_eq!(history_levels(doc), ["suggestion"], "{doc}");
}

#[test]
fn an_unknown_top_level_genre_key_does_not_fail_the_run() {
    let text = format!("---\ngenre: no-such-genre\n---\n{HISTORY}");
    let (code, report) = lint_note(ASSIGNED, &text);
    assert_ne!(code, Some(2), "{report}");
    assert_eq!(document(&report, "n.md")["genre"]["id"], "internal");
}

#[test]
fn a_disabled_front_matter_block_is_ignored() {
    let config = format!("{ASSIGNED}\n[frontmatter]\nenabled = false\n");
    let text = format!("---\nslopvac:\n  v: 3\n  genre: reference\n---\n{HISTORY}");
    let (_, report) = lint_note(&config, &text);
    let doc = document(&report, "n.md");
    assert_eq!(doc["genre"]["id"], "internal", "{doc}");
}

#[test]
fn an_allowed_slopvac_block_genre_wins_over_the_assignment() {
    let text = format!("---\nslopvac:\n  v: 3\n  genre: reference\n---\n{HISTORY}");
    let (_, report) = lint_note(ASSIGNED, &text);
    let doc = document(&report, "n.md");
    assert_eq!(doc["genre"]["id"], "reference", "{doc}");
    assert_eq!(doc["genre"]["source"], "explicit", "{doc}");
    assert_eq!(
        doc["genre"]["reasons"][0]["signal"], "front-matter",
        "{doc}"
    );
    assert_eq!(history_levels(doc), ["warning"], "{doc}");
}

/// The notices of a report whose code is `code`.
fn notices<'a>(report: &'a Value, code: &str) -> Vec<&'a Value> {
    report["notices"].as_array().map_or_else(Vec::new, |all| {
        all.iter().filter(|n| n["code"] == code).collect()
    })
}

#[test]
fn a_denied_genre_keeps_the_assignment_and_is_reported() {
    let config = format!("{ASSIGNED}\n[frontmatter]\nallow = [\"locale\"]\n");
    let text = format!("---\nslopvac:\n  v: 3\n  genre: reference\n---\n{HISTORY}");
    let (code, report) = lint_note(&config, &text);
    let doc = document(&report, "n.md");
    assert_eq!(doc["genre"]["id"], "internal", "{doc}");
    assert_eq!(doc["genre"]["reasons"][0]["signal"], "path-glob", "{doc}");
    assert_eq!(history_levels(doc), ["suggestion"], "{doc}");
    // The denied field is an error every time, and an error leaves the run incomplete.
    assert_eq!(code, Some(2), "{report}");
    let found = notices(&report, "config-frontmatter-field-denied");
    assert_eq!(found.len(), 1, "{report}");
    assert!(
        found[0]["path"]
            .as_str()
            .is_some_and(|p| p.ends_with("n.md"))
    );
    assert!(
        found[0]["message"]
            .as_str()
            .is_some_and(|m| m.contains("genre"))
    );
}

#[rstest::rstest]
#[case::missing_version("slopvac:\n  genre: reference\n", "config-missing-key")]
#[case::wrong_version("slopvac:\n  v: 2\n  genre: reference\n", "config-invalid-value")]
fn a_block_without_a_valid_version_keeps_the_assignment_and_is_reported(
    #[case] block: &str,
    #[case] error: &str,
) {
    let text = format!("---\n{block}---\n{HISTORY}");
    let (code, report) = lint_note(ASSIGNED, &text);
    assert_eq!(
        document(&report, "n.md")["genre"]["id"],
        "internal",
        "{report}"
    );
    assert_eq!(code, Some(2), "{report}");
    assert_eq!(notices(&report, error).len(), 1, "{report}");
}

#[test]
fn a_front_matter_genre_records_the_assignment_it_displaced() {
    let text = format!("---\nslopvac:\n  v: 3\n  genre: reference\n---\n{HISTORY}");
    let (_, report) = lint_note(ASSIGNED, &text);
    let reasons = &document(&report, "n.md")["genre"]["reasons"];
    assert_eq!(reasons[0]["signal"], "front-matter", "{reasons}");
    assert_eq!(reasons[1]["signal"], "path-glob", "{reasons}");
    assert_eq!(
        reasons[1]["detail"], "`[[genres]]` block 0 matches `notes/n.md`",
        "{reasons}"
    );
}

/// Lint a project with `config` and the document `notes/<name>` and return the raw output of
/// the run with `format`.
fn run_named_note(config: &str, name: &str, text: &str, format: &str) -> std::process::Output {
    let dir = tempfile::tempdir().expect("tempdir");
    fs::write(dir.path().join("slopvac.toml"), config).expect("write config");
    let path = dir.path().join("notes").join(name);
    fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    fs::write(path, text).expect("write document");
    slopvac()
        .args(["lint", "--format", format])
        .arg(dir.path())
        .output()
        .expect("run")
}

#[rstest::rstest]
#[case::plain_value("PRIVATE_SENTINEL")]
#[case::absolute_path("/Users/private-user/secret-project/notes")]
fn block_errors_never_echo_a_document_value(#[case] value: &str) {
    let config = format!("{ASSIGNED}\n[frontmatter]\nallow = [\"locale\"]\n");
    let text = format!("---\nslopvac:\n  v: 3\n  locale: {value}\n---\n{HISTORY}");
    for format in ["text", "json"] {
        let out = run_named_note(&config, "n.md", &text, format);
        assert_eq!(out.status.code(), Some(2), "{format}");
        let all = format!(
            "{}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        );
        assert!(
            all.contains("config-"),
            "{format}: a code is reported: {all}"
        );
        assert!(!all.contains(value), "{format}: {all}");
        assert!(!all.contains("private-user"), "{format}: {all}");
    }
}

#[test]
fn a_hostile_file_name_is_escaped_in_the_block_error() {
    let config = format!("{ASSIGNED}\n[frontmatter]\nallow = [\"locale\"]\n");
    let text = format!("---\nslopvac:\n  v: 3\n  genre: reference\n---\n{HISTORY}");
    let out = run_named_note(&config, "bad\u{1b}[2Jname.md", &text, "json");
    assert_eq!(out.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("config-frontmatter-field-denied"),
        "{stderr}"
    );
    assert!(!stderr.contains('\u{1b}'), "{stderr:?}");
}

/// A key, map key or array index that the document wrote is its own data: the error shows the
/// schema-owned part of the key path and stops there.
#[rstest::rstest]
#[case::unknown_top_level_key("  PRIVATE_SENTINEL: true\n", "/slopvac")]
#[case::unknown_key_under_a_table(
    "  thresholds:\n    PRIVATE_SENTINEL: 1\n",
    "/slopvac/thresholds"
)]
#[case::map_key("  rules:\n    PRIVATE_SENTINEL: not-a-level\n", "/slopvac/rules")]
#[case::array_index(
    "  terms:\n    allow:\n      - fine\n      - PRIVATE_SENTINEL: 1\n",
    "/slopvac/terms/allow"
)]
#[case::key_the_schema_does_not_own_under_terms("  terms:\n    files: true\n", "/slopvac/terms")]
fn block_errors_show_only_the_schema_owned_key_path(#[case] body: &str, #[case] pointer: &str) {
    let config = format!(
        "{ASSIGNED}\n[frontmatter]\nallow = [\"genre\", \"locale\", \"thresholds\", \"rules\", \"terms\"]\n"
    );
    let text = format!("---\nslopvac:\n  v: 3\n{body}---\n{HISTORY}");
    for format in ["text", "json"] {
        let out = run_named_note(&config, "n.md", &text, format);
        assert_eq!(out.status.code(), Some(2), "{format}");
        let stderr = String::from_utf8_lossy(&out.stderr);
        let all = format!("{}{stderr}", String::from_utf8_lossy(&out.stdout));
        assert!(!all.contains("PRIVATE_SENTINEL"), "{format}: {all}");
        assert!(
            stderr.lines().any(|l| l.ends_with(&format!(": {pointer}"))),
            "{format}: want a line ending in {pointer}: {stderr}"
        );
        assert!(
            !stderr.lines().any(|l| l.contains("files")),
            "{format}: the key `files` leaked: {stderr}"
        );
        if format == "json" {
            let report: Value = serde_json::from_slice(&out.stdout).expect("json report");
            let messages = report.to_string();
            assert!(!messages.contains("files"), "json: {messages}");
            assert!(
                messages.contains(&format!("{pointer}\"")),
                "json: want a message ending in {pointer}: {messages}"
            );
        }
    }
}
