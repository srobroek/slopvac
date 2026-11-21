//! Contexts that a document declares instead of having them inferred.
//!
//! Security context comes only from a genre (chosen by front matter, a `[[genres]]`
//! assignment or the genre's own signals) and never from vocabulary. The detector prototype
//! (`slopvac-8l4.2.14`) tagged 40% of security-doc sentences with a lexical tagger, which is
//! too broad to infer from.

use crate::{DocumentView, Error, GenreRegistry, GenreResult, Tag, Tagger};

/// Tags the whole document with the contexts its genre declares.
#[derive(Debug, Clone)]
pub struct DeclaredContextTagger {
    genre: String,
    contexts: Vec<String>,
}

impl DeclaredContextTagger {
    /// Build the tagger for a resolved genre. `None` when the genre declares no context.
    pub fn for_genre(registry: &GenreRegistry, genre: &GenreResult) -> Result<Option<Self>, Error> {
        Self::for_genre_id(registry, &genre.id)
    }

    /// Like [`Self::for_genre`], for a caller that holds only the genre id.
    pub fn for_genre_id(registry: &GenreRegistry, id: &str) -> Result<Option<Self>, Error> {
        let contexts = registry.contexts(id)?;
        if contexts.is_empty() {
            return Ok(None);
        }
        Ok(Some(Self {
            genre: id.to_owned(),
            contexts,
        }))
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
            .map(|kind| Tag {
                kind: kind.clone(),
                span: 0..doc.source_len(),
                confidence: 1.0,
                evidence: format!("declared by genre `{}`", self.genre),
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
