//! A genre's declared contexts tag the whole document, so rules gated on a context see them.

#![allow(missing_docs)]

mod common;

use common::{category, ruleset, settings};
use rstest::rstest;
use serde_json::json;
use slopvac_context::GenreAssignment;
use slopvac_engine::{Engine, Input, Settings};

const BODY: &str = "We refactored the parser.\n";

/// A rule that fires on `refactored` only in a document with the `security` context.
fn gated_engine(settings: Settings) -> Engine {
    let only = json!({"contexts": {"only": ["security"]}});
    let rules = [common::tokens("gated", "refactored", &only)];
    Engine::new(vec![ruleset(vec![category("cat", &rules)])], settings).unwrap()
}

fn per_document() -> Settings {
    let mut s = settings();
    s.genre_assignments = Some(Vec::<GenreAssignment>::new());
    s
}

fn lint(engine: &Engine, genre: &str) -> slopvac_model::Document {
    let source = format!("---\ngenre: {genre}\n---\n{BODY}");
    engine
        .lint(&Input::markdown("a.md", &source).with_declared_genre(genre))
        .unwrap()
}

#[rstest]
#[case::declaring_genre("security", true)]
#[case::other_genre("reference", false)]
fn a_gated_rule_fires_only_when_the_genre_declares_the_context(
    #[case] genre: &str,
    #[case] fires: bool,
) {
    let doc = lint(&gated_engine(per_document()), genre);
    assert_eq!(
        doc.findings
            .iter()
            .any(|f| f.rule_id.as_str().ends_with("gated")),
        fires
    );
}

#[rstest]
#[case::declaring_genre("security", &["security"])]
#[case::other_genre("reference", &[])]
fn contexts_seen_lists_the_declared_context(#[case] genre: &str, #[case] seen: &[&str]) {
    let doc = lint(&gated_engine(per_document()), genre);
    let got: Vec<&str> = doc
        .contexts_seen
        .iter()
        .map(slopvac_model::ContextTag::as_str)
        .collect();
    assert_eq!(got, seen);
}

#[test]
fn the_genre_of_a_whole_run_declares_its_contexts_too() {
    let mut run = settings();
    run.genre.id = slopvac_model::GenreId::new("security").unwrap();
    let engine = gated_engine(run);
    let doc = engine.lint(&Input::markdown("a.md", BODY)).unwrap();
    assert!(
        doc.findings
            .iter()
            .any(|f| f.rule_id.as_str().ends_with("gated"))
    );
}
