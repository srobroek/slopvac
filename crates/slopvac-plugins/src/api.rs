//! Typed hook calls: batching, request building and result validation.

use std::ops::Range;

use serde::Serialize;
use serde_json::{Value, json};

use crate::error::{PluginError, RpcError};
use crate::hooks::{
    CompleteItem, Completion, Document, FindingsDocument, FixEdit, RecipeFile, Rendered, Segment,
    Tag, match_entries, parse_completions, parse_edits, parse_error_object, parse_recipe,
    parse_rendered, parse_score, parse_segments, parse_tags,
};
use crate::host::Plugin;
use crate::messages::host::HostText;
use crate::protocol::HookKind;

/// The outcome for one document of a batch.
#[derive(Debug, Clone, PartialEq)]
pub struct DocOutcome<T> {
    /// Document id as sent.
    pub id: String,
    /// The validated result, or why this document failed.
    pub outcome: Result<T, PluginError>,
}

/// Anything that carries a [`Document`].
pub trait HasDocument: Serialize + Clone {
    /// The document.
    fn document(&self) -> &Document;
    /// Drop the path, for plugins that were not granted `document-path`.
    fn strip_path(&mut self);
}

impl HasDocument for Document {
    fn document(&self) -> &Document {
        self
    }
    fn strip_path(&mut self) {
        self.path = None;
    }
}

impl HasDocument for FindingsDocument {
    fn document(&self) -> &Document {
        &self.document
    }
    fn strip_path(&mut self) {
        self.document.path = None;
    }
}

/// Split items into batches under both limits.
///
/// `sizes` holds each item's encoded size and `overhead` the size of a request
/// with no items. Returns the batches and the indexes of items that cannot fit
/// a message even alone.
#[must_use]
pub fn plan_batches(
    sizes: &[usize],
    overhead: usize,
    max_items: usize,
    max_bytes: usize,
) -> (Vec<Range<usize>>, Vec<usize>) {
    let mut batches = Vec::new();
    let mut oversize = Vec::new();
    let mut start = 0;
    let mut bytes = overhead;
    let mut count = 0;
    for (i, &size) in sizes.iter().enumerate() {
        if overhead.saturating_add(size) > max_bytes {
            if count > 0 {
                batches.push(start..i);
            }
            oversize.push(i);
            start = i + 1;
            bytes = overhead;
            count = 0;
            continue;
        }
        let with_comma = size + usize::from(count > 0);
        if count == max_items || bytes + with_comma > max_bytes {
            batches.push(start..i);
            start = i;
            bytes = overhead;
            count = 0;
        }
        bytes += size + usize::from(count > 0);
        count += 1;
    }
    if count > 0 {
        batches.push(start..sizes.len());
    }
    (batches, oversize)
}

impl Plugin {
    fn documents_call<D, T>(
        &self,
        kind: HookKind,
        hook_id: &str,
        key: &str,
        docs: &[D],
        parse: &dyn Fn(&Value, &D) -> Result<T, PluginError>,
    ) -> Result<Vec<DocOutcome<T>>, PluginError>
    where
        D: HasDocument,
    {
        let n = self.negotiated();
        let mut docs = docs.to_vec();
        if !n.document_path {
            docs.iter_mut().for_each(HasDocument::strip_path);
        }
        let encoded: Vec<usize> = docs
            .iter()
            .map(|d| serde_json::to_vec(d).map(|v| v.len()))
            .collect::<Result<_, _>>()
            .map_err(|e| {
                PluginError::Usage(
                    HostText::EncodeDocument {
                        error: e.to_string(),
                    }
                    .to_string(),
                )
            })?;
        let empty = json!({"jsonrpc": "2.0", "id": 9_007_199_254_740_991u64, "method": kind.method(),
            "params": {key: hook_id, "documents": []}});
        let overhead = serde_json::to_vec(&empty).map_or(0, |v| v.len());
        let (batches, oversize) = plan_batches(
            &encoded,
            overhead,
            n.max_batch_documents,
            n.max_message_bytes,
        );
        let mut out: Vec<Option<DocOutcome<T>>> = (0..docs.len()).map(|_| None).collect();
        for &i in &oversize {
            out[i] = Some(DocOutcome {
                id: docs[i].document().id.clone(),
                outcome: Err(PluginError::MessageTooLarge(
                    HostText::DocumentTooLarge {
                        id: docs[i].document().id.clone(),
                    }
                    .to_string(),
                )),
            });
        }
        for range in batches {
            let batch = &docs[range.clone()];
            let params = json!({key: hook_id, "documents": batch});
            let result = self.call(kind, hook_id, params)?;
            let ids: Vec<&str> = batch.iter().map(|d| d.document().id.as_str()).collect();
            let entries = match_entries(&result, "document", &ids)?;
            for ((slot, entry), doc) in out[range].iter_mut().zip(entries).zip(batch) {
                let outcome = match entry.get("error") {
                    Some(e) => Err(parse_error_object(e).map_or_else(|e| e, PluginError::Rpc)),
                    None => parse(entry, doc),
                };
                *slot = Some(DocOutcome {
                    id: doc.document().id.clone(),
                    outcome,
                });
            }
        }
        Ok(out.into_iter().flatten().collect())
    }

    /// Tag documents.
    ///
    /// # Errors
    /// A request-level failure. Per-document failures sit in the outcomes.
    pub fn tag(
        &self,
        hook: &str,
        docs: &[Document],
    ) -> Result<Vec<DocOutcome<Vec<Tag>>>, PluginError> {
        self.documents_call(HookKind::Tagger, hook, "tagger", docs, &|e, d| {
            parse_tags(e, &d.text)
        })
    }

    /// Split documents into prose segments.
    ///
    /// # Errors
    /// A request-level failure.
    pub fn extract(
        &self,
        hook: &str,
        docs: &[Document],
    ) -> Result<Vec<DocOutcome<Vec<Segment>>>, PluginError> {
        self.documents_call(HookKind::Extractor, hook, "extractor", docs, &|e, d| {
            parse_segments(e, &d.text)
        })
    }

    /// Ask a fixer for edits. Edits are checked against the sent findings.
    ///
    /// # Errors
    /// A request-level failure.
    pub fn fix(
        &self,
        hook: &str,
        docs: &[FindingsDocument],
    ) -> Result<Vec<DocOutcome<Vec<FixEdit>>>, PluginError> {
        self.documents_call(HookKind::Fixer, hook, "fixer", docs, &|e, d| {
            parse_edits(e, &d.document.text, &d.findings)
        })
    }

    /// Score documents. A document the scorer skips has `None`.
    ///
    /// # Errors
    /// A request-level failure.
    pub fn score(
        &self,
        hook: &str,
        docs: &[FindingsDocument],
    ) -> Result<Vec<DocOutcome<Option<f64>>>, PluginError> {
        self.documents_call(HookKind::Scorer, hook, "scorer", docs, &|e, _| {
            parse_score(e)
        })
    }

    /// Render one report.
    ///
    /// # Errors
    /// Any failure. The returned text is untrusted: sanitise it for a terminal.
    pub fn render(
        &self,
        hook: &str,
        report: &Value,
        options: &Value,
    ) -> Result<Rendered, PluginError> {
        let params = json!({"reporter": hook, "report": report, "options": options});
        parse_rendered(&self.call(HookKind::Reporter, hook, params)?)
    }

    /// Ask a provider. Output is untrusted model text and has no route to a
    /// fixer or recipe.
    ///
    /// # Errors
    /// A request-level failure.
    pub fn complete(
        &self,
        hook: &str,
        task: &str,
        model: &str,
        items: &[CompleteItem],
    ) -> Result<Vec<Result<Completion, RpcError>>, PluginError> {
        let params = json!({"provider": hook, "task": task, "model": model, "items": items});
        let result = self.call(HookKind::Provider, hook, params)?;
        let ids: Vec<&str> = items.iter().map(|i| i.id.as_str()).collect();
        parse_completions(&result, &ids)
    }

    /// Ask a recipe for a plan. The plan writes nothing.
    ///
    /// # Errors
    /// Any failure, including a path that escapes the root.
    pub fn recipe(
        &self,
        hook: &str,
        harness: &str,
        options: &Value,
    ) -> Result<Vec<RecipeFile>, PluginError> {
        let params = json!({"recipe": hook, "harness": harness, "options": options});
        parse_recipe(&self.call(HookKind::Recipe, hook, params)?)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn small_items_split_by_count() {
        let (b, o) = plan_batches(&[10; 5], 100, 2, 10_000);
        assert_eq!(b, vec![0..2, 2..4, 4..5]);
        assert_eq!(o, Vec::<usize>::new());
    }

    #[test]
    fn items_split_by_bytes_including_commas() {
        // overhead 100 + 40 + ',' + 40 = 181 fits; a third item would make 222.
        let (b, _) = plan_batches(&[40, 40, 40], 100, 64, 181);
        assert_eq!(b, vec![0..2, 2..3]);
    }

    #[test]
    fn an_item_that_cannot_fit_alone_is_reported_and_skipped() {
        let (b, o) = plan_batches(&[10, 500, 10], 100, 64, 200);
        assert_eq!(b, vec![0..1, 2..3]);
        assert_eq!(o, vec![1]);
    }
}
