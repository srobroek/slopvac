//! Declared contexts: security comes from a genre, never from vocabulary.
#![allow(clippy::assert_is_empty)]

use slopvac_context::{
    DeclaredContextTagger, DocumentView, GenreAssignment, PlainDocument, ResolveOptions,
    TagRegistry, builtin_genres, builtin_registry, context_hint,
};

const SECURITY_TEXT: &str = "# Policy\n\nTokens grant credentials. The sandbox denies secrets and approval escalates privileges.\n";

fn tags_for(doc: &PlainDocument, assignments: &[GenreAssignment]) -> (String, Vec<String>) {
    let genres = builtin_genres().unwrap();
    let result = genres
        .resolve(
            doc,
            &ResolveOptions {
                assignments,
                relative_path: None,
                ..Default::default()
            },
        )
        .unwrap();
    let mut reg: TagRegistry = builtin_registry().unwrap();
    if let Some(t) = DeclaredContextTagger::for_genre(&genres, &result).unwrap() {
        reg.register(Box::new(t)).unwrap();
    }
    let idx = reg.tag_document(doc).unwrap();
    let kinds = idx.kinds_seen().into_iter().map(String::from).collect();
    (result.id, kinds)
}

#[test]
fn front_matter_genre_declares_security() {
    let src = format!("---\nslopvac:\n  v: 3\n  genre: security\n---\n{SECURITY_TEXT}");
    let (genre, kinds) = tags_for(&PlainDocument::from_markdown("a.md", &src), &[]);
    assert_eq!(genre, "security");
    assert!(kinds.contains(&"security".to_string()), "{kinds:?}");
}

#[test]
fn per_path_assignment_declares_security() {
    let a = [GenreAssignment {
        files: vec!["policies/**".into()],
        genre: "security".into(),
    }];
    let doc = PlainDocument::from_markdown("policies/access.md", SECURITY_TEXT);
    let (genre, kinds) = tags_for(&doc, &a);
    assert_eq!(genre, "security");
    assert!(kinds.contains(&"security".to_string()));
    let elsewhere = PlainDocument::from_markdown("docs/access.md", SECURITY_TEXT);
    assert!(!tags_for(&elsewhere, &a).1.contains(&"security".to_string()));
}

#[test]
fn security_vocabulary_alone_never_declares_security() {
    let doc = PlainDocument::from_markdown("docs/security/trust.md", SECURITY_TEXT);
    let (genre, kinds) = tags_for(&doc, &[]);
    assert_eq!(genre, "consumer");
    assert!(!kinds.contains(&"security".to_string()), "{kinds:?}");
}

#[test]
fn a_genre_without_contexts_adds_no_tagger() {
    let genres = builtin_genres().unwrap();
    let doc = PlainDocument::from_markdown("a.md", "# T\n\nBody.\n");
    let result = genres.resolve(&doc, &ResolveOptions::default()).unwrap();
    assert!(
        DeclaredContextTagger::for_genre(&genres, &result)
            .unwrap()
            .is_none()
    );
}

#[test]
fn security_context_carries_the_name_the_enforcement_hint() {
    let hint = context_hint("security").unwrap();
    assert!(hint.contains("Name the enforcement"));
    assert_eq!(context_hint("requirement"), None);
}

#[test]
fn security_span_covers_every_original_byte_including_front_matter() {
    let src = "---\nslopvac:\n  v: 3\n  genre: security\n---\n# Überblick\n\nDer Zugriff ist nur über Token erlaubt.\n";
    let doc = PlainDocument::from_markdown("a.md", src);
    let genres = builtin_genres().unwrap();
    let result = genres.resolve(&doc, &ResolveOptions::default()).unwrap();
    let mut reg = TagRegistry::new();
    reg.register(Box::new(
        DeclaredContextTagger::for_genre(&genres, &result)
            .unwrap()
            .unwrap(),
    ))
    .unwrap();
    let idx = reg.tag_document(&doc).unwrap();
    assert_eq!(idx.tags().len(), 1);
    assert_eq!(idx.tags()[0].kind, "security");
    assert_eq!(idx.tags()[0].span, 0..src.len());
    assert_eq!(idx.tags()[0].evidence, "declared by genre `security`");
    let last_char = src.len() - 1..src.len();
    assert_eq!(idx.kinds_at(&(0..1)), vec!["security"]);
    assert_eq!(idx.kinds_at(&last_char), vec!["security"]);
    assert_eq!(idx.kinds_at(&(src.len()..src.len())), vec!["security"]);
    assert!(idx.kinds_at(&(0..src.len() + 1)).is_empty());
}

fn security_policy() -> [GenreAssignment; 1] {
    [GenreAssignment {
        files: vec!["policies/**".into()],
        genre: "security".into(),
    }]
}

#[test]
fn a_path_assigned_context_survives_a_front_matter_genre() {
    let src = format!("---\nslopvac:\n  v: 3\n  genre: consumer\n---\n{SECURITY_TEXT}");
    let doc = PlainDocument::from_markdown("policies/access.md", &src);
    let (genre, kinds) = tags_for(&doc, &security_policy());
    assert_eq!(genre, "consumer");
    assert!(kinds.contains(&"security".to_string()), "{kinds:?}");
}

/// The document is in the assigned directory and names the assigned genre itself, so the
/// assignment adds no second source: one tag, declared by that genre.
#[test]
fn a_front_matter_genre_equal_to_the_assignment_declares_its_context_once() {
    let src = format!("---\nslopvac:\n  v: 3\n  genre: security\n---\n{SECURITY_TEXT}");
    let doc = PlainDocument::from_markdown("policies/access.md", &src);
    let genres = builtin_genres().unwrap();
    let opts = ResolveOptions {
        assignments: &security_policy(),
        ..Default::default()
    };
    let result = genres.resolve(&doc, &opts).unwrap();
    assert_eq!(result.id, "security");
    assert_eq!(result.assigned, None);
    let tagger = DeclaredContextTagger::for_genre(&genres, &result)
        .unwrap()
        .unwrap();
    let tags = slopvac_context::Tagger::tag(&tagger, &doc).unwrap();
    assert_eq!(tags.len(), 1);
    assert_eq!(tags[0].evidence, "declared by genre `security`");
}

#[test]
fn a_path_assigned_context_names_the_genre_that_declares_it() {
    let src = format!("---\nslopvac:\n  v: 3\n  genre: consumer\n---\n{SECURITY_TEXT}");
    let doc = PlainDocument::from_markdown("policies/access.md", &src);
    let genres = builtin_genres().unwrap();
    let opts = ResolveOptions {
        assignments: &security_policy(),
        ..Default::default()
    };
    let result = genres.resolve(&doc, &opts).unwrap();
    assert_eq!(result.assigned.as_deref(), Some("security"));
    let tagger = DeclaredContextTagger::for_genre(&genres, &result)
        .unwrap()
        .unwrap();
    let tags = slopvac_context::Tagger::tag(&tagger, &doc).unwrap();
    assert_eq!(tags.len(), 1);
    assert_eq!(tags[0].kind, "security");
    assert_eq!(tags[0].evidence, "declared by genre `security`");
}

/// What a document's front matter declares, worked out from the contract: only a valid,
/// versioned `slopvac:` block with a string `genre` declares one.
#[rstest::rstest]
#[case::top_level_key("---\ngenre: security\n---\n", false)]
#[case::unversioned_block("---\nslopvac:\n  genre: security\n---\n", false)]
#[case::numeric_version("---\nslopvac:\n  v: 3\n  genre: security\n---\n", true)]
#[case::string_version("---\nslopvac:\n  v: \"3\"\n  genre: security\n---\n", false)]
#[case::wrong_version("---\nslopvac:\n  v: 2\n  genre: security\n---\n", false)]
#[case::non_string_genre("---\nslopvac:\n  v: 3\n  genre: 5\n---\n", false)]
#[case::unknown_field(
    "---\nslopvac:\n  v: 3\n  genre: security\n  colour: red\n---\n",
    false
)]
#[case::nested_collision("---\nslopvac:\n  v: 3\n  rules:\n    genre: security\n---\n", false)]
#[case::flow_mapping("---\nslopvac: {v: 3, genre: security}\n---\n", true)]
#[case::crlf_lines("---\r\nslopvac:\r\n  v: 3\r\n  genre: security\r\n---\r\n", true)]
#[case::byte_order_mark("\u{feff}---\nslopvac:\n  v: 3\n  genre: security\n---\n", true)]
#[case::dots_closer("---\nslopvac:\n  v: 3\n  genre: security\n...\n", true)]
#[case::toml("+++\n[slopvac]\nv = 3\ngenre = \"security\"\n+++\n", true)]
#[case::toml_wrong_version("+++\n[slopvac]\nv = 2\ngenre = \"security\"\n+++\n", false)]
#[case::json("{\"slopvac\": {\"v\": 3, \"genre\": \"security\"}}\n", true)]
#[case::unclosed("---\nslopvac:\n  v: 3\n  genre: security\n", false)]
#[case::block_beside_top_level(
    "---\ngenre: consumer\nslopvac:\n  v: 3\n  genre: security\n---\n",
    true
)]
fn only_a_valid_versioned_block_declares_a_genre(#[case] front: &str, #[case] declared: bool) {
    let doc = PlainDocument::from_markdown("docs/a.md", &format!("{front}{SECURITY_TEXT}"));
    let (genre, kinds) = tags_for(&doc, &[]);
    assert_eq!(genre == "security", declared, "{genre}");
    assert_eq!(
        kinds.contains(&"security".to_string()),
        declared,
        "{kinds:?}"
    );
}

#[rstest::rstest]
#[case::yaml("---\ntitle: Notes\n---\n")]
#[case::yaml_crlf("---\r\ntitle: Notes\r\n---\r\n")]
#[case::toml("+++\ntitle = \"Notes\"\n+++\n")]
#[case::json("{\"title\": \"Notes\"}\n")]
fn top_level_front_matter_reads_in_every_format(#[case] front: &str) {
    let doc = PlainDocument::from_markdown("a.md", &format!("{front}# Body\n\nText.\n"));
    assert_eq!(doc.front_matter("title"), Some("Notes"));
}
