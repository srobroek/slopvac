//! `[[genres]]` file matching and the `genre` command path.
#![allow(clippy::assert_is_empty)]

use std::path::PathBuf;

use slopvac_context::{
    GenreAssignment, PlainDocument, ResolveOptions, builtin_genres, command, run,
};

/// Whether a `[[genres]]` block with `patterns` assigns its genre to `path`.
fn files_match(patterns: &[String], path: &str) -> Result<bool, slopvac_context::Error> {
    let reg = slopvac_context::GenreRegistry::new(
        slopvac_context::parse_genres(
            "- {schema_version: 3, id: base}\n- {schema_version: 3, id: hit}\n",
        )
        .unwrap(),
        "base",
    )
    .unwrap();
    let assignments = [slopvac_context::GenreAssignment {
        files: patterns.to_vec(),
        genre: "hit".into(),
    }];
    let doc = slopvac_context::PlainDocument::from_markdown(path, "t\n");
    let opts = slopvac_context::ResolveOptions {
        assignments: &assignments,
        relative_path: None,
        ..Default::default()
    };
    Ok(reg.resolve(&doc, &opts)?.id == "hit")
}

fn pats(p: &[&str]) -> Vec<String> {
    p.iter().map(|s| (*s).to_string()).collect()
}

#[test]
fn negation_excludes_and_a_later_pattern_re_includes() {
    let cases = [
        (&["docs/**"][..], "docs/a.md", true),
        (&["docs/**", "!docs/internal/**"][..], "docs/a.md", true),
        (
            &["docs/**", "!docs/internal/**"][..],
            "docs/internal/x.md",
            false,
        ),
        (
            &["docs/**", "!docs/internal/**", "docs/internal/keep.md"][..],
            "docs/internal/keep.md",
            true,
        ),
        (&["docs/**", "!docs/internal/**"][..], "src/a.md", false),
        (&["*.md"][..], "a/b/c.md", true),
        (&["/*.md"][..], "a/b.md", false),
        (&[][..], "a.md", false),
    ];
    for (p, path, want) in cases {
        assert_eq!(
            files_match(&pats(p), path).unwrap(),
            want,
            "{p:?} on {path}"
        );
    }
}

#[test]
fn an_excluded_file_falls_through_to_the_earlier_block() {
    let reg = builtin_genres().unwrap();
    let a = [
        GenreAssignment {
            files: pats(&["docs/**"]),
            genre: "consumer".into(),
        },
        GenreAssignment {
            files: pats(&["docs/**", "!docs/api/**"]),
            genre: "internal".into(),
        },
    ];
    let genre_of = |path: &str| {
        reg.resolve(
            &PlainDocument::from_markdown(path, "# T\n\nBody.\n"),
            &ResolveOptions {
                assignments: &a,
                relative_path: None,
                ..Default::default()
            },
        )
        .unwrap()
        .id
    };
    assert_eq!(genre_of("docs/a.md"), "internal");
    assert_eq!(genre_of("docs/api/a.md"), "consumer");
}

fn scratch(name: &str, body: &str) -> PathBuf {
    let dir = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join("genre-run");
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join(name);
    std::fs::write(&path, body).unwrap();
    path
}

fn run_args(args: &[&str]) -> Result<String, slopvac_context::Error> {
    let m = command()
        .try_get_matches_from(std::iter::once("genre").chain(args.iter().copied()))
        .unwrap();
    run(&m, &mut |_, _| None)
}

#[test]
fn run_prints_one_block_per_file() {
    let a = scratch("CHANGELOG.md", "# Log\n\nText.\n");
    let b = scratch("plain.md", "# T\n\nBody.\n");
    let out = run_args(&[a.to_str().unwrap(), b.to_str().unwrap()]).unwrap();
    let (first, second) = out.split_once("plain.md").expect("both files in output");
    assert!(
        first.contains("CHANGELOG.md: change-comms (detected)"),
        "{out}"
    );
    assert!(second.starts_with(": consumer (default)"), "{out}");
}

#[test]
fn run_applies_assignments_in_order() {
    let a = scratch("assigned.md", "# T\n\nBody.\n");
    let p = a.to_str().unwrap();
    let out = run_args(&[
        p,
        "--assign",
        "*.md=internal",
        "--assign",
        "assigned.md=reference",
    ])
    .unwrap();
    assert!(out.contains(": reference (explicit)"), "{out}");
    assert!(
        out.contains("path-glob: `[[genres]]` block 1 matches"),
        "{out}"
    );
}

#[test]
fn run_reports_unreadable_input_unknown_genre_and_bad_assignment() {
    let missing = run_args(&["no/such/file.md"]).unwrap_err().to_string();
    assert!(missing.contains("no/such/file.md"), "{missing}");
    let f = scratch("ok.md", "# T\n\nBody.\n");
    let p = f.to_str().unwrap();
    let unknown = run_args(&[p, "--assign", "*.md=nope"])
        .unwrap_err()
        .to_string();
    assert!(unknown.contains("unknown genre `nope`"), "{unknown}");
    let bad = run_args(&[p, "--assign", "no-equals-sign"])
        .unwrap_err()
        .to_string();
    assert!(bad.contains("needs GLOB=GENRE"), "{bad}");
}

#[test]
fn run_assignments_match_absolute_paths_without_panicking() {
    let f = scratch("abs.md", "# T\n\nBody.\n");
    let out = run_args(&[f.to_str().unwrap(), "--assign", "**/abs.md=informal"]).unwrap();
    assert!(out.contains(": informal (explicit)"), "{out}");
}

#[test]
fn assignments_match_the_path_as_given_and_never_a_path_outside_the_root() {
    let cases = [
        (&["docs/**"][..], r"docs\a.md", false),
        (&["**/a.md"][..], "/proj/docs/a.md", false),
        (&["**/a.md"][..], "../docs/a.md", false),
        (&["**/a.md"][..], "docs/a.md", true),
        // A directory literally named `guide\branch` is one component, not two.
        (&["guide\\\\branch/**"][..], "guide\\branch/a.md", true),
        (&["guide/branch/**"][..], "guide\\branch/a.md", false),
    ];
    for (p, path, want) in cases {
        assert_eq!(
            files_match(&pats(p), path).unwrap(),
            want,
            "{p:?} on {path}"
        );
    }
}

#[test]
fn path_signals_see_windows_separators() {
    let reg = builtin_genres().unwrap();
    let doc = PlainDocument::from_markdown(r"C:\proj\docs\CHANGELOG.md", "# Log\n\nText.\n");
    let r = reg.resolve(&doc, &ResolveOptions::default()).unwrap();
    assert_eq!(r.id, "change-comms");
}
