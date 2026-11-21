//! Genre registry behaviour through the public API.
#![allow(clippy::assert_is_empty)]

use slopvac_context::{
    Budget, Error, GenreAssignment, GenreRegistry, GenreSource, NoBudget, PlainDocument, Profile,
    ResolveOptions, RuleLevel, builtin_genres, parse_genres,
};

fn resolve(path: &str, src: &str) -> slopvac_context::GenreResult {
    builtin_genres()
        .unwrap()
        .resolve(
            &PlainDocument::from_markdown(path, src),
            &ResolveOptions::default(),
        )
        .unwrap()
}

#[test]
fn path_signal_detects_change_comms() {
    let r = resolve("docs/CHANGELOG.md", "# Project\n\nText here.\n");
    assert_eq!(r.id, "change-comms");
    assert_eq!(r.source, GenreSource::Detected);
    assert_eq!(r.reasons.len(), 1);
    assert_eq!(r.reasons[0].signal, "path");
    assert_eq!(r.reasons[0].detail, "path `docs/CHANGELOG.md` (+3)");
}

#[test]
fn heading_signal_reaches_the_threshold_exactly() {
    let r = resolve("x.md", "# Notes\n\n## Release notes\n\nText here.\n");
    assert_eq!(
        (r.id.as_str(), r.source),
        ("change-comms", GenreSource::Detected)
    );
    assert_eq!(r.reasons[0].detail, "heading `Release notes` (+3)");
}

#[test]
fn a_signal_counts_once_however_many_headings_match() {
    let r = resolve("x.md", "# T\n\n## Context\n\nA.\n\n## Decision\n\nB.\n");
    assert_eq!(
        (r.id.as_str(), r.source),
        ("consumer", GenreSource::Default)
    );
    let internal = r.scores.iter().find(|(id, _)| id == "internal").unwrap();
    assert!((internal.1 - 1.5).abs() < f64::EPSILON);
}

#[test]
fn signals_add_up_across_definitions() {
    let r = resolve("CONTRIBUTING.md", "# T\n\n## Context\n\nA.\n");
    assert_eq!(
        (r.id.as_str(), r.source),
        ("internal", GenreSource::Detected)
    );
    assert_eq!(r.reasons.len(), 2);
}

#[test]
fn below_threshold_falls_back_to_the_default() {
    let r = resolve("README.md", "# T\n\nBody.\n");
    assert_eq!(
        (r.id.as_str(), r.source),
        ("consumer", GenreSource::Default)
    );
    assert_eq!(r.reasons[0].signal, "default");
    let consumer = r.scores.iter().find(|(id, _)| id == "consumer").unwrap();
    assert!((consumer.1 - 2.0).abs() < f64::EPSILON);
}

#[test]
fn adr_path_detects_internal() {
    assert_eq!(
        resolve("docs/adr/0001-choice.md", "# T\n\nBody.\n").id,
        "internal"
    );
}

#[test]
fn front_matter_beats_detection() {
    let r = resolve(
        "CHANGELOG.md",
        "---\nslopvac:\n  v: 3\n  genre: reference\n---\n# T\n\nBody.\n",
    );
    assert_eq!(
        (r.id.as_str(), r.source),
        ("reference", GenreSource::Explicit)
    );
    assert_eq!(r.reasons[0].signal, "front-matter");
}

#[test]
fn assignments_apply_in_file_order_and_the_last_match_wins() {
    let reg = builtin_genres().unwrap();
    let doc = PlainDocument::from_markdown("docs/api/a.md", "# T\n\nBody.\n");
    let assignments = [
        GenreAssignment {
            files: vec!["docs/**".into()],
            genre: "consumer".into(),
        },
        GenreAssignment {
            files: vec!["docs/api/*.md".into()],
            genre: "reference".into(),
        },
        GenreAssignment {
            files: vec!["other/**".into()],
            genre: "informal".into(),
        },
    ];
    let r = reg
        .resolve(
            &doc,
            &ResolveOptions {
                assignments: &assignments,
                relative_path: None,
                ..Default::default()
            },
        )
        .unwrap();
    assert_eq!(
        (r.id.as_str(), r.source),
        ("reference", GenreSource::Explicit)
    );
    assert_eq!(r.reasons[0].signal, "path-glob");
    assert_eq!(
        r.reasons[0].detail,
        "`[[genres]]` block 1 matches `docs/api/a.md`"
    );
}

#[test]
fn assignments_use_the_relative_path() {
    let reg = builtin_genres().unwrap();
    let doc = PlainDocument::from_markdown("/abs/proj/docs/a.md", "# T\n\nBody.\n");
    let assignments = [GenreAssignment {
        files: vec!["docs/*.md".into()],
        genre: "internal".into(),
    }];
    let r = reg
        .resolve(
            &doc,
            &ResolveOptions {
                assignments: &assignments,
                relative_path: Some("docs/a.md"),
                ..Default::default()
            },
        )
        .unwrap();
    assert_eq!(r.id, "internal");
}

#[test]
fn unknown_genre_is_an_error() {
    let reg = builtin_genres().unwrap();
    let doc = PlainDocument::from_markdown(
        "a.md",
        "---\nslopvac:\n  v: 3\n  genre: nope\n---\n# T\n\nBody.\n",
    );
    assert!(matches!(
        reg.resolve(&doc, &ResolveOptions::default()),
        Err(Error::UnknownGenre(id)) if id == "nope"
    ));
}

const CHAIN: &str = "
- schema_version: 3
  id: base
  profile: strict
  rules: { prose-craft.future-tense: warning, prose-craft.hedging: error }
  categories: { prose-craft: warning, prose-scope: { severity: error, max_per_100_words: 2 } }
- schema_version: 3
  id: child
  extends: [base]
  rules: { prose-craft.future-tense: off }
  categories: { prose-scope: { max_per_100_words: none } }
";

fn chain() -> GenreRegistry {
    GenreRegistry::new(parse_genres(CHAIN).unwrap(), "child")
        .unwrap()
        .with_contexts("base", &["security"])
        .unwrap()
        .with_contexts("child", &["security", "example"])
        .unwrap()
}

#[test]
fn extends_merges_rules_contexts_and_profile() {
    let reg = chain();
    let rules = reg.rules("child").unwrap();
    assert_eq!(rules["prose-craft.future-tense"], RuleLevel::Off);
    assert_eq!(rules["prose-craft.hedging"], RuleLevel::Error);
    assert_eq!(reg.contexts("child").unwrap(), vec!["security", "example"]);
    assert_eq!(reg.profile("child").unwrap(), Some(Profile::Strict));
}

#[test]
fn a_child_category_entry_patches_the_parent_entry_field_by_field() {
    let cats = chain().categories("child").unwrap();
    // The parent set only a bare level: it stays as the severity.
    assert_eq!(cats["prose-craft"].severity, Some(RuleLevel::Warning));
    // The child cleared the budget and left the parent's severity alone.
    let scope = &cats["prose-scope"];
    assert_eq!(scope.severity, Some(RuleLevel::Error));
    assert_eq!(scope.max_per_100_words, Some(Budget::None(NoBudget::None)));
}

#[test]
fn a_child_category_dial_replaces_only_that_dial() {
    let y = "
- {schema_version: 3, id: p, categories: {c: {severity: error, minimum_severity: warning, max_per_100_words: 2, weight: 3}}}
- {schema_version: 3, id: k, extends: [p], categories: {c: {max_per_100_words: 5}}}
";
    let reg = GenreRegistry::new(parse_genres(y).unwrap(), "k").unwrap();
    let c = &reg.categories("k").unwrap()["c"];
    assert_eq!(c.severity, Some(RuleLevel::Error));
    assert_eq!(c.minimum_severity, Some(RuleLevel::Warning));
    assert_eq!(c.max_per_100_words, Some(Budget::Limit(5.0)));
    assert_eq!(c.weight, Some(3.0));
}

#[test]
fn a_text_signal_that_could_match_part_of_a_character_is_rejected_at_load() {
    // `\C` matches one byte, so a match could end inside the two bytes of `é` and break
    // any caller that slices the text. The context crate never needs byte matching, so the
    // pattern layer refuses `\C` and the genre fails to load with a pattern error.
    let y = "
- {schema_version: 3, id: base}
- schema_version: 3
  id: a
  detect:
    signals:
      - { kind: text, pattern: '\\C' }
";
    let result = parse_genres(y).and_then(|specs| GenreRegistry::new(specs, "base"));
    assert!(
        matches!(result, Err(slopvac_context::Error::Pattern { .. })),
        "{:?}",
        result.err()
    );
}

#[test]
fn a_text_signal_with_a_match_reset_resolves_on_character_boundaries() {
    // `\K` moves the match start; the span must still be slice-safe on multi-byte text.
    let y = "
- {schema_version: 3, id: base}
- schema_version: 3
  id: a
  detect:
    signals:
      - { kind: text, pattern: 't\\K\u{e9}' }
";
    let reg = GenreRegistry::new(parse_genres(y).unwrap(), "base").unwrap();
    let doc = PlainDocument::from_markdown("a.md", "\u{e9}t\u{e9}\n");
    let r = reg.resolve(&doc, &ResolveOptions::default()).unwrap();
    assert_eq!(r.id, "a");
}

#[test]
fn present_null_fields_are_errors() {
    let bad = [
        "- {schema_version: 3, id: a, title: null}\n",
        "- {schema_version: 3, id: a, description: null}\n",
        "- {schema_version: 3, id: a, surfaces: null}\n",
        "- {schema_version: 3, id: a, profile: null}\n",
        "- {schema_version: 3, id: a, detect: null}\n",
        "- {schema_version: 3, id: a, extends: null}\n",
        "- {schema_version: 3, id: a, categories: {c: {severity: null}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {minimum_severity: null}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {max_per_100_words: null}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {weight: null}}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path, glob: null}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: front-matter, key: null}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: front-matter, key: k, equals: null}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: text, pattern: null}]}}\n",
    ];
    for y in bad {
        assert!(parse_genres(y).is_err(), "{y}");
    }
}

#[test]
fn extends_lists_apply_lowest_first_and_a_shared_parent_counts_once() {
    let reg = GenreRegistry::new(
        parse_genres(
            "
- {schema_version: 3, id: root, rules: {r.a: error, r.b: error}}
- {schema_version: 3, id: left, extends: [root], rules: {r.a: warning}}
- {schema_version: 3, id: right, extends: [root], rules: {r.a: suggestion, r.b: off}}
- {schema_version: 3, id: top, extends: [left, right]}
",
        )
        .unwrap(),
        "top",
    )
    .unwrap();
    let ids: Vec<&str> = reg
        .chain("top")
        .unwrap()
        .iter()
        .map(|s| s.id.as_str())
        .collect();
    assert_eq!(ids, ["root", "left", "right", "top"]);
    let rules = reg.rules("top").unwrap();
    assert_eq!(rules["r.a"], RuleLevel::Suggestion);
    assert_eq!(rules["r.b"], RuleLevel::Off);
}

#[test]
fn a_genre_without_detect_is_never_detected() {
    let reg = chain();
    let doc = PlainDocument::from_markdown("secret.md", "# T\n\nBody.\n");
    let r = reg.resolve(&doc, &ResolveOptions::default()).unwrap();
    assert_eq!((r.id.as_str(), r.source), ("child", GenreSource::Default));
    assert!(r.scores.is_empty());
}

#[test]
fn invalid_definitions_are_errors() {
    let bad = [
        "- {schema_version: 3, id: a}\n- {schema_version: 3, id: a}\n",
        "- {id: a}\n",
        "- {schema_version: 2, id: a}\n",
        "- {schema_version: 3, id: A}\n",
        "- {schema_version: 3, id: a, bogus: 1}\n",
        "- {schema_version: 3, id: a, extends: [ghost]}\n",
        "- {schema_version: 3, id: a, extends: b}\n",
        "- {schema_version: 3, id: a, extends: [b]}\n- {schema_version: 3, id: b, extends: [a]}\n",
        "- {schema_version: 3, id: a, profile: loud}\n",
        "- {schema_version: 3, id: a, rules: {r.x: loud}}\n",
        "- {schema_version: 3, id: a, categories: {c: {severity: loud}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {colour: red}}}\n",
        "- {schema_version: 3, id: a, detect: {signals: []}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: glob, glob: x}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path, glob: x, pattern: y}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path, glob: x, weight: 0}]}}\n",
        "- {schema_version: 3, id: a, detect: {min_score: 0, signals: [{kind: path, glob: x}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path, glob: '['}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: heading, pattern: '('}]}}\n",
    ];
    for y in bad {
        let r = parse_genres(y).and_then(|s| GenreRegistry::new(s, "a"));
        assert!(r.is_err(), "{y}");
    }
}

#[test]
fn x_keys_are_ignored_at_every_level() {
    let y = "
- schema_version: 3
  id: a
  x-owner: docs
  detect:
    x-note: [1, 2]
    signals:
      - { kind: text, pattern: hello, x-why: because }
";
    assert!(GenreRegistry::new(parse_genres(y).unwrap(), "a").is_ok());
}

#[test]
fn front_matter_signals_compare_the_exact_value() {
    let y = "
- {schema_version: 3, id: base}
- schema_version: 3
  id: a
  detect:
    signals:
      - { kind: front-matter, key: type, equals: guide }
      - { kind: front-matter, key: draft, equals: true }
      - { kind: front-matter, key: owner }
";
    let reg = GenreRegistry::new(parse_genres(y).unwrap(), "base").unwrap();
    let score = |fm: &str| {
        let doc = PlainDocument::from_markdown("a.md", &format!("---\n{fm}---\n# T\n\nBody.\n"));
        let r = reg.resolve(&doc, &ResolveOptions::default()).unwrap();
        r.scores[0].1
    };
    assert!((score("type: guide\n") - 1.0).abs() < f64::EPSILON);
    assert!(score("type: guides\n").abs() < f64::EPSILON);
    assert!((score("draft: true\nowner: me\n") - 2.0).abs() < f64::EPSILON);
}

#[test]
fn text_signals_read_the_body() {
    let y = "
- {schema_version: 3, id: base}
- schema_version: 3
  id: a
  detect:
    signals:
      - { kind: text, pattern: 'two\\s+words' }
";
    let reg = GenreRegistry::new(parse_genres(y).unwrap(), "base").unwrap();
    let pick = |src: &str| {
        reg.resolve(
            &PlainDocument::from_markdown("a.md", src),
            &ResolveOptions::default(),
        )
        .unwrap()
        .id
    };
    assert_eq!(pick("# T\n\nText.\n\nSee Two Words here.\n"), "a");
    assert_eq!(pick("# T\n\nText.\n"), "base");
}

#[test]
fn render_lists_reasons_and_scores() {
    let r = resolve("docs/CHANGELOG.md", "# Project\n\nText here.\n");
    let text = slopvac_context::render("docs/CHANGELOG.md", &r);
    assert!(text.starts_with("docs/CHANGELOG.md: change-comms (detected)\n  path: path `docs/CHANGELOG.md` (+3)\n  scores: change-comms 3,"), "{text}");
}

#[test]
fn genre_command_parses_files_and_assignments() {
    let m = slopvac_context::command()
        .try_get_matches_from(["genre", "a.md", "b.md", "--assign", "docs/**=reference"])
        .unwrap();
    assert_eq!(m.get_many::<String>("files").unwrap().count(), 2);
    assert!(
        slopvac_context::command()
            .try_get_matches_from(["genre"])
            .is_err()
    );
}

#[test]
fn a_canceled_path_component_does_not_signal_a_genre() {
    // `reference\..` cancels out, so the path is `proj/docs/a.md` and nothing detects.
    let r = resolve("C:\\proj\\reference\\..\\docs\\a.md", "# T\n\nBody.\n");
    assert_eq!(
        (r.id.as_str(), r.source),
        ("consumer", GenreSource::Default)
    );
}

#[test]
fn a_genre_file_declares_contexts_that_extending_genres_inherit() {
    let reg = GenreRegistry::new(
        parse_genres(
            "- schema_version: 3\n  id: base\n  contexts: [security]\n\
             - schema_version: 3\n  id: child\n  extends: [base]\n  contexts: [example, security]\n",
        )
        .unwrap(),
        "base",
    )
    .unwrap();
    assert_eq!(reg.contexts("base").unwrap(), ["security"]);
    assert_eq!(reg.contexts("child").unwrap(), ["security", "example"]);
}

#[test]
fn the_built_in_security_genre_declares_the_security_context() {
    let reg = slopvac_context::builtin_genres().unwrap();
    assert_eq!(reg.contexts("security").unwrap(), ["security"]);
    assert!(reg.contexts("consumer").unwrap().is_empty());
}

#[test]
fn a_tie_goes_to_the_genre_defined_last_in_either_order() {
    let genre = |id: &str| {
        format!(
            "- {{schema_version: 3, id: {id}, detect: {{signals: [{{kind: text, pattern: tie}}]}}}}\n"
        )
    };
    let base = "- {schema_version: 3, id: base}\n";
    let doc = PlainDocument::from_markdown("a.md", "tie\n");
    for (first, last) in [("alpha", "beta"), ("beta", "alpha")] {
        let y = format!("{base}{}{}", genre(first), genre(last));
        let reg = GenreRegistry::new(parse_genres(&y).unwrap(), "base").unwrap();
        let r = reg.resolve(&doc, &ResolveOptions::default()).unwrap();
        assert_eq!(r.id, last, "defined order {first}, {last}");
        assert_eq!(r.source, GenreSource::Detected);
    }
}

#[test]
fn a_tiny_min_score_does_not_make_every_genre_a_candidate() {
    // 1e-50 is above 0, so the schema allows it. Narrowed to f32 it would be 0 and every
    // genre would reach it, so a document with no match must still get the default.
    let y = "
- {schema_version: 3, id: base}
- {schema_version: 3, id: a, detect: {min_score: 1e-50, signals: [{kind: text, pattern: zzz}]}}
";
    let reg = GenreRegistry::new(parse_genres(y).unwrap(), "base").unwrap();
    let doc = PlainDocument::from_markdown("a.md", "nothing here\n");
    let r = reg.resolve(&doc, &ResolveOptions::default()).unwrap();
    assert_eq!((r.id.as_str(), r.source), ("base", GenreSource::Default));
}

#[test]
fn non_finite_numbers_are_errors_everywhere() {
    let bad = [
        "- {schema_version: 3, id: a, detect: {min_score: .nan, signals: [{kind: path, glob: x}]}}\n",
        "- {schema_version: 3, id: a, detect: {min_score: .inf, signals: [{kind: path, glob: x}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path, glob: x, weight: .nan}]}}\n",
        "- {schema_version: 3, id: a, detect: {signals: [{kind: path, glob: x, weight: .inf}]}}\n",
        "- {schema_version: 3, id: a, categories: {c: {weight: .nan}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {weight: .inf}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {max_per_100_words: .nan}}}\n",
        "- {schema_version: 3, id: a, categories: {c: {max_per_100_words: .inf}}}\n",
    ];
    for y in bad {
        let r = parse_genres(y).and_then(|s| GenreRegistry::new(s, "a"));
        assert!(r.is_err(), "{y}");
    }
}

const HOSTILE: &str = "a\u{1b}[31m\u{202e}b.md";
const HOSTILE_ESCAPED: &str = "a\\u{1b}[31m\\u{202e}b.md";

#[test]
fn render_escapes_control_and_bidi_characters() {
    let r = slopvac_context::GenreResult {
        id: "g".to_string(),
        source: GenreSource::Detected,
        reasons: vec![slopvac_context::Reason {
            signal: "heading".to_string(),
            detail: format!("heading `{HOSTILE}`"),
        }],
        scores: vec![(HOSTILE.to_string(), 1.0)],
        assigned: None,
    };
    let text = slopvac_context::render(HOSTILE, &r);
    assert_eq!(
        text,
        format!(
            "{HOSTILE_ESCAPED}: g (detected)\n  heading: heading `{HOSTILE_ESCAPED}`\n  scores: {HOSTILE_ESCAPED} 1\n"
        )
    );
}

#[test]
fn a_read_error_escapes_the_path() {
    let m = slopvac_context::command()
        .try_get_matches_from(["genre", "no\u{1b}]8;;\u{202e}/such.md"])
        .unwrap();
    let msg = slopvac_context::run(&m, &mut |_, _| None)
        .unwrap_err()
        .to_string();
    assert!(msg.starts_with("no\\u{1b}]8;;\\u{202e}/such.md: "), "{msg}");
    assert!(!msg.contains(['\u{1b}', '\u{202e}']), "{msg:?}");
}

#[test]
fn an_assign_error_escapes_the_argument() {
    let m = slopvac_context::command()
        .try_get_matches_from(["genre", "a.md", "--assign", "x\u{1b}\u{202e}"])
        .unwrap();
    let msg = slopvac_context::run(&m, &mut |_, _| None)
        .unwrap_err()
        .to_string();
    assert!(!msg.contains(['\u{1b}', '\u{202e}']), "{msg:?}");
}

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

mod error_sources {
    use std::error::Error as _;

    use slopvac_context::{Error, GenreSpec, Pattern, TaggerSpec, parse_genres};

    use super::files_match;

    const BAD_YAML: &str = "{ unclosed";
    const BAD_GLOB_GENRE: &str = "- schema_version: 3\n  id: a\n  detect:\n    signals:\n      - { kind: path, glob: '[' }\n";

    fn has_source(e: &Error) -> bool {
        e.source().is_some()
    }

    #[test]
    fn yaml_errors_keep_their_source() {
        assert!(has_source(&GenreSpec::from_yaml(BAD_YAML).unwrap_err()));
        assert!(has_source(&parse_genres(BAD_YAML).unwrap_err()));
        assert!(has_source(&TaggerSpec::from_yaml(BAD_YAML).unwrap_err()));
        assert!(has_source(
            &TaggerSpec::list_from_yaml(BAD_YAML).unwrap_err()
        ));
    }

    #[test]
    fn glob_errors_keep_their_source() {
        let config = files_match(&["{a".to_string()], "a.md");
        let config = config.unwrap_err();
        assert!(has_source(&config), "{config:?}");
        let signal =
            slopvac_context::GenreRegistry::new(parse_genres(BAD_GLOB_GENRE).unwrap(), "a")
                .err()
                .unwrap();
        assert!(has_source(&signal), "{signal:?}");
    }

    #[test]
    fn a_glob_set_that_fails_to_build_keeps_its_source() {
        // Each pattern parses, but the combined matcher is too large to build.
        let huge = "?".repeat(3_000_000);
        let err = files_match(&[huge], "a.md").unwrap_err();
        assert!(matches!(err, Error::GlobSet(_)), "{err:?}");
        assert!(has_source(&err));
    }

    #[test]
    fn pattern_errors_keep_their_source() {
        assert!(has_source(&Pattern::new("(").unwrap_err()));
        let p = Pattern::new("^(a+)+$").unwrap();
        let text = format!("{}b", "a".repeat(64));
        assert!(has_source(&p.is_match(&text).unwrap_err()));
        assert!(has_source(&p.find(&text).unwrap_err()));
    }

    #[test]
    fn a_read_error_keeps_the_io_source() {
        let m = slopvac_context::command()
            .try_get_matches_from(["genre", "no-such-file.md"])
            .unwrap();
        let err = slopvac_context::run(&m, &mut |_, _| None).unwrap_err();
        assert!(has_source(&err), "{err:?}");
        assert!(err.to_string().starts_with("no-such-file.md: "), "{err}");
    }
}

mod display_escaping {
    use slopvac_context::{
        Error, GenreAssignment, GenreRegistry, GenreSpec, Pattern, PlainDocument, ResolveOptions,
        parse_genres,
    };

    use super::files_match;

    const BAD: &str = "x\u{1b}[31m\u{202e}y";

    fn clean(e: &Error) {
        let msg = e.to_string();
        assert!(msg.contains("x\\u{1b}[31m\\u{202e}y"), "{msg}");
        assert!(!msg.contains(['\u{1b}', '\u{202e}']), "{msg:?}");
    }

    #[test]
    fn an_unknown_assigned_genre_is_escaped() {
        let reg = GenreRegistry::new(
            parse_genres("- {schema_version: 3, id: base}\n").unwrap(),
            "base",
        )
        .unwrap();
        let assignments = [GenreAssignment {
            files: vec!["*".to_string()],
            genre: BAD.to_string(),
        }];
        let opts = ResolveOptions {
            assignments: &assignments,
            relative_path: None,
            ..Default::default()
        };
        let err = reg
            .resolve(&PlainDocument::from_markdown("a.md", "t\n"), &opts)
            .unwrap_err();
        assert!(matches!(err, Error::UnknownGenre(_)));
        clean(&err);
    }

    #[test]
    fn an_unknown_default_genre_is_escaped() {
        let err = GenreRegistry::new(Vec::new(), BAD).err().unwrap();
        clean(&err);
    }

    #[test]
    fn pattern_errors_are_escaped() {
        clean(&Pattern::new(&format!("(?#{BAD}")).unwrap_err());
        let p = Pattern::new(&format!("(?#{BAD})^(a+)+$")).unwrap();
        let text = format!("{}b", "a".repeat(64));
        clean(&p.is_match(&text).unwrap_err());
    }

    #[test]
    fn parse_errors_are_escaped() {
        let spec = GenreSpec::from_yaml("schema_version: 3\nid: \"x\\e[31m\\u202ey\"\n").unwrap();
        clean(&spec.validate().unwrap_err());
    }

    #[test]
    fn a_duplicate_tagger_id_is_escaped() {
        struct Named;
        impl slopvac_context::Tagger for Named {
            fn id(&self) -> &str {
                BAD
            }
            fn tag(
                &self,
                _: &dyn slopvac_context::DocumentView,
            ) -> Result<Vec<slopvac_context::Tag>, Error> {
                Ok(Vec::new())
            }
        }
        let mut reg = slopvac_context::TagRegistry::new();
        reg.register(Box::new(Named)).unwrap();
        let err = reg.register(Box::new(Named)).unwrap_err();
        assert!(matches!(err, Error::DuplicateTagger(_)));
        clean(&err);
    }

    #[test]
    fn a_yaml_error_that_echoes_input_is_escaped() {
        let y = "schema_version: 3\nid: a\nprofile: \"x\\e[31m\\u202ey\"\n";
        let err = GenreSpec::from_yaml(y).unwrap_err();
        assert!(matches!(err, Error::Yaml(_)));
        // The parser prints its own escapes next to raw input text, so only the absence of
        // raw characters is stable.
        assert!(
            !err.to_string().contains(['\u{1b}', '\u{202e}']),
            "{:?}",
            err.to_string()
        );
    }

    #[test]
    fn a_path_signal_glob_error_is_escaped() {
        let y = "- schema_version: 3\n  id: a\n  detect:\n    signals:\n      - { kind: path, glob: \"{x\\e[31m\\u202ey\" }\n";
        let err = GenreRegistry::new(parse_genres(y).unwrap(), "a")
            .err()
            .unwrap();
        assert!(matches!(err, Error::SignalGlob { .. }), "{err:?}");
        clean(&err);
    }

    #[test]
    fn glob_errors_are_escaped() {
        clean(&files_match(&[format!("{BAD}\\")], "a.md").unwrap_err());
    }
}
