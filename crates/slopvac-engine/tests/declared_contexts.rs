//! A genre's declared contexts tag the whole document, so rules gated on a context see them.

mod common;

use common::{category, ruleset, settings};
use rstest::rstest;
use serde_json::json;
use slopvac_context::GenreAssignment;
use slopvac_context::{DocumentView, Tag, TagRegistry, Tagger};
use slopvac_diagrams::Format;
use slopvac_engine::{Engine, EngineError, Input, Settings};
use slopvac_model::GenreId;

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

const LONG_LABEL_FILE: &str =
    "flowchart TD\n  A[This label has far too many words in it] --> B[End]\n";

fn security_run() -> Settings {
    let mut run = settings();
    run.genre.id = GenreId::new("security").unwrap();
    run
}

fn diagram_engine(settings: Settings) -> Engine {
    let only = json!({"contexts": {"only": ["security"]}});
    let rule = common::rule(
        "label-run-on",
        &json!({"kind": "structure", "check": "diagram-label-run-on"}),
        &only,
    );
    Engine::new(vec![ruleset(vec![category("diagram", &[rule])])], settings).unwrap()
}

#[rstest]
#[case::run_genre(security_run())]
#[case::per_document({
    let mut s = security_run();
    s.genre_assignments = Some(Vec::<GenreAssignment>::new());
    s
})]
fn a_standalone_diagram_sees_the_contexts_its_genre_declares(#[case] genre: Settings) {
    let doc = diagram_engine(genre)
        .lint(&Input::diagram(
            "flow.mmd",
            LONG_LABEL_FILE,
            Format::Mermaid,
        ))
        .unwrap();
    let seen: Vec<&str> = doc
        .contexts_seen
        .iter()
        .map(slopvac_model::ContextTag::as_str)
        .collect();
    assert_eq!(seen, ["diagram-label", "security"]);
    assert_eq!(doc.findings.len(), 1);
}

#[test]
fn a_standalone_diagram_of_another_genre_stays_silent_for_a_gated_rule() {
    let doc = diagram_engine(settings())
        .lint(&Input::diagram(
            "flow.mmd",
            LONG_LABEL_FILE,
            Format::Mermaid,
        ))
        .unwrap();
    assert_eq!(doc.findings.len(), 0);
}

/// Tags `count` structural tags of distinct kinds over the first byte.
struct Many(usize);

impl Tagger for Many {
    fn id(&self) -> &'static str {
        "many"
    }

    fn tag(&self, _: &dyn DocumentView) -> Result<Vec<Tag>, slopvac_context::Error> {
        Ok((0..self.0)
            .map(|i| Tag {
                kind: format!("k{i}"),
                span: 0..1,
                confidence: 1.0,
                evidence: String::new(),
            })
            .collect())
    }
}

/// The ceiling in `docs/contract/policies.md`: one tag for every 64 bytes plus 65,536.
fn ceiling(source_len: usize) -> usize {
    source_len / 64 + 65_536
}

#[rstest]
#[case::at_the_ceiling(0, true)]
#[case::one_over(1, false)]
fn declared_tags_count_against_the_tag_ceiling(#[case] structural_over: usize, #[case] fits: bool) {
    let limit = ceiling(BODY.len());
    // One declared tag (`security`) joins the structural ones.
    let structural = limit - 1 + structural_over;
    let mut registry = TagRegistry::new();
    registry.register(Box::new(Many(structural))).unwrap();
    let engine = gated_engine(security_run()).with_taggers(registry);
    let result = engine.lint(&Input::markdown("a.md", BODY));
    if fits {
        assert!(result.is_ok());
    } else {
        assert_eq!(
            result.map(|d| d.findings.len()),
            Err(EngineError::TagBuildBudget { limit })
        );
    }
}
