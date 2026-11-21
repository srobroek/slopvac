//! Contexts that a document declares instead of having them inferred.
//!
//! Security context comes only from a genre (chosen by front matter, a `[[genres]]`
//! assignment or the genre's own signals) and never from vocabulary. The detector prototype
//! (`slopvac-8l4.2.14`) tagged 40% of security-doc sentences with a lexical tagger, which is
//! too broad to infer from.

use crate::{DocumentView, Error, GenreRegistry, GenreResult, Tag, Tagger};

/// Tags the whole document with the contexts its genre declares.
pub struct DeclaredContextTagger {
    /// Each context with the genre that declares it.
    contexts: Vec<(String, String)>,
}

impl DeclaredContextTagger {
    /// Build the tagger for a resolved genre. `None` when the genre declares no context.
    pub fn for_genre(registry: &GenreRegistry, genre: &GenreResult) -> Result<Option<Self>, Error> {
        let mut contexts: Vec<(String, String)> = registry
            .contexts(&genre.id)?
            .into_iter()
            .map(|c| (c, genre.id.clone()))
            .collect();
        // Contexts from a path or config assignment are additive: a front matter genre
        // changes the genre but never removes them.
        if let Some(assigned) = &genre.assigned {
            for c in registry.contexts(assigned)? {
                if !contexts.iter().any(|(known, _)| *known == c) {
                    contexts.push((c, assigned.clone()));
                }
            }
        }
        if contexts.is_empty() {
            return Ok(None);
        }
        Ok(Some(Self { contexts }))
    }
}

impl Tagger for DeclaredContextTagger {
    fn id(&self) -> &'static str {
        "declared-contexts"
    }

    fn tag(&self, doc: &dyn DocumentView) -> Result<Vec<Tag>, Error> {
        Ok(self
            .contexts
            .iter()
            .map(|(kind, genre)| Tag {
                kind: kind.clone(),
                span: 0..doc.source_len(),
                confidence: 1.0,
                evidence: format!("declared by genre `{genre}`"),
            })
            .collect())
    }
}

/// Reviewer hint for findings in a context, or `None`. The review checklist and the
/// judgement remainder print it next to the rule.
#[must_use]
pub fn context_hint(kind: &str) -> Option<&'static str> {
    match kind {
        "security" => Some(
            "Security context: a negative guarantee needs the mechanism that enforces it. \
             Name the enforcement, or drop the claim.",
        ),
        _ => None,
    }
}
