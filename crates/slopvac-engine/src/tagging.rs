//! Context tags for a parsed document.
//!
//! `slopvac-context` reads a document through its `DocumentView` trait. This module adapts
//! a `slopvac-parse` document to it. Block text is the projected prose and block spans are
//! source bytes, so a tag span is a source range that a finding span can sit inside.

use std::cell::{Cell, RefCell};
use std::collections::{BTreeMap, HashMap};
use std::ops::Range;

use frontmatter_spans::{FrontMatter, Value};
use slopvac_context::{
    BlockKind as ViewKind, BlockView, DeclaredContextTagger, DocumentView, Error as ContextError,
    GenreRegistry, GenreResult, ResolveOptions, Scalar, SentenceView, Tag, TagIndex, TagRegistry,
    TagSink, Tagger,
};
use slopvac_parse::{BlockKind, ByteMapper, Container, Document};

mod entry;

use entry::{Context, Entry};

/// The source ranges of one entry, sorted by start, for finding those a tag meets.
struct Extents {
    /// The ranges, sorted by start.
    runs: Vec<Range<usize>>,
    /// For each run, the largest end among it and the runs before it.
    reach: Vec<usize>,
}

impl Extents {
    fn new(mut runs: Vec<Range<usize>>) -> Self {
        runs.sort_by_key(|r| (r.start, r.end));
        let reach = runs
            .iter()
            .scan(0, |top, r| {
                *top = (*top).max(r.end);
                Some(*top)
            })
            .collect();
        Self { runs, reach }
    }

    /// The runs that overlap `span`, found without visiting the runs that end before it or
    /// start after it. `visit` is called for each run looked at.
    fn overlapping<'e>(
        &'e self,
        span: &'e Range<usize>,
        mut visit: impl FnMut() + 'e,
    ) -> impl Iterator<Item = Range<usize>> + 'e {
        let first = self.reach.partition_point(|&end| end <= span.start);
        self.runs[first..]
            .iter()
            .take_while(|r| r.start < span.end)
            .inspect(move |_| visit())
            .filter_map(|r| {
                let from = r.start.max(span.start);
                let to = r.end.min(span.end);
                (from < to).then_some(from..to)
            })
    }
}

/// The text of each top-level non-string scalar, rendered by `Scalar::to_text`, the one
/// formatter that genre signals use for their expected value: `true`, `42`, `1.5`. A datetime
/// keeps its source text.
/// The last occurrence of a key decides: a later null, sequence or table removes the text of
/// an earlier scalar, as `get` returns the last occurrence.
fn scalar_text<'a>(front: &'a FrontMatter<'a>) -> HashMap<&'a str, String> {
    let Value::Table(entries) = &front.root.value else {
        return HashMap::new();
    };
    let mut texts = HashMap::new();
    for e in entries {
        let scalar = match &e.value.value {
            Value::Bool(b) => Scalar::Bool(*b),
            Value::Integer(i) => Scalar::Int(*i),
            Value::Float(f) => Scalar::Float(*f),
            Value::Datetime(d) => Scalar::Str(d.clone()),
            Value::Null | Value::String(_) | Value::Array(_) | Value::Table(_) => {
                texts.remove(e.key.as_str());
                continue;
            }
        };
        texts.insert(e.key.as_str(), scalar.to_text());
    }
    texts
}

/// A parsed document as the taggers read it.
struct View<'a> {
    path: &'a str,
    /// The entry that produced each span handed to a tagger as a block or a sentence.
    owners: RefCell<HashMap<(usize, usize), usize>>,
    source_len: usize,
    title: Option<&'a str>,
    front_matter: Option<&'a FrontMatter<'a>>,
    /// Top-level front matter keys whose value is not a string, rendered as text.
    scalars: HashMap<&'a str, String>,
    entries: Vec<Entry<'a>>,
    /// The blocks as taggers read them, built once.
    views: Vec<BlockView<'a>>,
    /// The entry that reads each non-empty text, by the address and length of the text.
    by_text: HashMap<(usize, usize), usize>,
    /// Set when a sentence offset did not lie on the text of its block.
    unmapped: Cell<bool>,
}

impl<'a> View<'a> {
    fn new(
        path: &'a str,
        source: &'a str,
        doc: &'a Document,
        front_matter: Option<&'a FrontMatter<'a>>,
    ) -> Self {
        let mut entries: Vec<Entry<'a>> = Vec::new();
        let mut headings: Vec<(u8, &'a str)> = Vec::new();
        let mut title = None;
        // Open admonitions as (end of span, title).
        let mut admonitions: Vec<(usize, Option<&'a str>)> = Vec::new();
        for block in &doc.blocks {
            while admonitions
                .last()
                .is_some_and(|(end, _)| block.span.start() >= *end)
            {
                admonitions.pop();
            }
            if let BlockKind::Admonition(a) = &block.kind {
                admonitions.push((block.span.end(), a.title.as_deref()));
                continue;
            }
            let (mut kind, text, projection) = match (&block.kind, &block.projection) {
                (BlockKind::CodeBlock { body, .. }, _) => {
                    (ViewKind::CodeBlock, &source[body.start()..body.end()], None)
                }
                (BlockKind::Heading { .. }, Some(p)) => (ViewKind::Heading, p.text(), Some(p)),
                (BlockKind::Paragraph, Some(p)) => (ViewKind::Paragraph, p.text(), Some(p)),
                (BlockKind::TableCell { .. }, Some(p)) => (ViewKind::TableRow, p.text(), Some(p)),
                _ => continue,
            };
            // The innermost list or quote decides what a paragraph is to a tagger.
            if kind == ViewKind::Paragraph {
                match block.containers.last() {
                    Some(Container::ListItem { .. }) => kind = ViewKind::ListItem,
                    Some(Container::BlockQuote) => kind = ViewKind::Quote,
                    _ => {}
                }
            }
            let mut level = None;
            if let BlockKind::Heading { level: l } = &block.kind {
                while headings.last().is_some_and(|(top, _)| top >= l) {
                    headings.pop();
                }
                headings.push((*l, text));
                level = Some(*l);
                title.get_or_insert(text);
            }
            let span = match &block.kind {
                BlockKind::CodeBlock { body, .. } => body.start()..body.end(),
                _ => block.span.start()..block.span.end(),
            };
            entries.push(Entry::new(
                kind,
                span,
                text,
                Context {
                    heading_path: headings.iter().map(|(_, t)| *t).collect(),
                    heading_level: level,
                    admonition_title: admonitions.iter().rev().find_map(|(_, t)| *t),
                    projection,
                },
            ));
        }
        let by_text = entries
            .iter()
            .enumerate()
            .filter(|(_, e)| !e.text.is_empty())
            .map(|(i, e)| ((e.text.as_ptr().addr(), e.text.len()), i))
            .collect();
        let views = entries.iter().map(Entry::view).collect();
        // A later entry with the same span owns it.
        let owners = entries
            .iter()
            .enumerate()
            .map(|(i, e)| ((e.span.start, e.span.end), i))
            .collect();
        Self {
            path,
            owners: RefCell::new(owners),
            views,
            source_len: source.len(),
            title,
            front_matter,
            scalars: front_matter.map(scalar_text).unwrap_or_default(),
            entries,
            by_text,
            unmapped: Cell::new(false),
        }
    }
}

impl View<'_> {
    /// Replace the tags that sit on interleaved text by tags on the text that contributed.
    ///
    /// The cells of a table whose left cell wraps over several lines read cell by cell, so
    /// the extent of the left cell contains the right cell. A tag on a sentence or a block
    /// of the left cell has that extent, and a match in the right cell would inherit the tag.
    /// Such a tag becomes one tag for each line of the cell's own text. A tag that covers
    /// several blocks, or that no sentence or block of an entry produced, is left alone.
    ///
    /// The work is `O(n log n)` in the number of entries and `O(1)` for each tag: a sweep
    /// over the entries sorted by start finds those that overlap another, and the owner of a
    /// tag is the entry whose sentence or block produced its span.
    /// Count one step of `split_interleaved`.
    #[cfg(feature = "test-counters")]
    #[expect(
        clippy::unused_self,
        reason = "matches the variant without counters, which has no use for the view"
    )]
    fn visit(&self) {
        counted::visit();
    }

    #[cfg(not(feature = "test-counters"))]
    #[expect(
        clippy::unused_self,
        reason = "matches the variant with counters, which the tests build"
    )]
    #[inline(always)]
    fn visit(&self) {}

    fn split_interleaved(&self, tags: Vec<Tag>, max_tags: usize) -> Result<TagIndex, TagError> {
        let mut order: Vec<usize> = (0..self.entries.len())
            .filter(|&i| self.entries[i].projection.is_some())
            .collect();
        order.sort_by_key(|&i| self.entries[i].span.start);
        // An entry overlaps another when an earlier one ends after it starts, or the next
        // one starts before it ends. Sorted by start, those two checks see every overlap.
        let mut marked = vec![false; self.entries.len()];
        let mut latest_end = 0;
        for (k, &i) in order.iter().enumerate() {
            self.visit();
            let span = &self.entries[i].span;
            if span.start < span.end {
                let earlier = latest_end > span.start;
                let later = order
                    .get(k + 1)
                    .is_some_and(|&n| self.entries[n].span.start < span.end);
                marked[i] = earlier || later;
            }
            latest_end = latest_end.max(span.end);
        }
        if !marked.contains(&true) {
            return Ok(TagIndex::from_tags(tags));
        }
        let owners = self.owners.borrow();
        let mut extents: BTreeMap<usize, Extents> = BTreeMap::new();
        // Each piece is charged against the ceiling before it is built, so the split never
        // holds more pieces than the document may. The groups are one number per piece.
        let mut sink = TagSink::new(max_tags);
        let mut groups: Vec<usize> = Vec::new();
        for (group, tag) in tags.into_iter().enumerate() {
            self.visit();
            let owner = owners
                .get(&(tag.span.start, tag.span.end))
                .copied()
                .filter(|&i| marked[i]);
            let extents = owner.map(|i| {
                extents.entry(i).or_insert_with(|| {
                    Extents::new(
                        self.entries[i]
                            .projection
                            .map(|p| p.extents().iter().map(|s| s.start()..s.end()).collect())
                            .unwrap_or_default(),
                    )
                })
            });
            let before = sink.len();
            for span in extents
                .into_iter()
                .flat_map(|e| e.overlapping(&tag.span, || self.visit()))
            {
                sink.push_with(|| Tag {
                    span,
                    ..tag.clone()
                })?;
                groups.push(group);
            }
            if sink.len() == before {
                sink.push_with(|| tag)?;
                groups.push(group);
            }
        }
        let pieces = sink.into_tags().into_iter().zip(groups).collect();
        Ok(TagIndex::from_pieces(pieces))
    }
}

impl DocumentView for View<'_> {
    fn path(&self) -> &str {
        self.path
    }

    fn title(&self) -> Option<&str> {
        self.front_matter
            .and_then(|f| f.get("title"))
            .and_then(|n| n.as_str())
            .or(self.title)
    }

    fn front_matter(&self, key: &str) -> Option<&str> {
        let node = self.front_matter?.get(key)?;
        node.as_str()
            .or_else(|| self.scalars.get(key).map(String::as_str))
    }

    fn source_len(&self) -> usize {
        self.source_len
    }

    fn blocks(&self) -> Vec<BlockView<'_>> {
        self.views.clone()
    }

    fn sentences<'a>(&self, block: &BlockView<'a>) -> Vec<SentenceView<'a>> {
        let split = slopvac_context::split_sentences(block);
        // The entry is found by the text it reads, not by its span: cells that fell back to
        // line precision share the span of their row.
        let Some((owner, projection)) = self
            .by_text
            .get(&(block.text.as_ptr().addr(), block.text.len()))
            .and_then(|&i| self.entries[i].projection.map(|p| (i, p)))
        else {
            return split;
        };
        let mapper = self.entries[owner]
            .mapper
            .get_or_init(|| ByteMapper::new(projection));
        let mut owners = self.owners.borrow_mut();
        // The splitter assumes the text sits at the block span. Map each sentence through
        // the projection so its span is a source range.
        let mut located = Vec::with_capacity(split.len());
        for s in &split {
            let from = s.span.start - block.span.start;
            let Some(span) = mapper.span(from, from + s.text.len()) else {
                self.unmapped.set(true);
                return split;
            };
            owners.insert((span.start(), span.end()), owner);
            located.push(SentenceView {
                span: span.start()..span.end(),
                text: s.text,
            });
        }
        located
    }
}

/// Why tagging a document stopped.
#[derive(Debug, thiserror::Error)]
pub(crate) enum TagError {
    /// A tagger failed.
    #[error(transparent)]
    Tagger(ContextError),
    /// The document has more tags than its size allows, so no index was built.
    #[error("the document has more than {limit} context tags")]
    Budget {
        /// The most tags, or pieces of tags, the document was allowed.
        limit: usize,
    },
    /// The sentences of a block do not lie on the text the block was projected from.
    #[error("the sentences of a block do not map onto its projected text")]
    Unmapped,
}

impl From<ContextError> for TagError {
    fn from(e: ContextError) -> Self {
        match e {
            ContextError::TagLimit { limit } => Self::Budget { limit },
            other => Self::Tagger(other),
        }
    }
}

/// Tags that context lookups may look at for each byte of the document.
///
/// A lookup for a match that crosses the lines of a wrapped table cell looks at each tag
/// that sits on the cell. A document with a few kinds of tag on a few cells looks at a few
/// tags for each match, so a match is far under one look for each byte. A pack that puts many
/// kinds of tag on one cell, and rules that match across its lines, make each match look at
/// every kind, and the looks grow with kinds times matches.
const LOOKUPS_PER_BYTE: usize = 8;

/// Looks allowed whatever the size of the document, so a small document with a few cells
/// is never cut short.
const LOOKUP_HEADROOM: usize = 16_384;

/// The looks that context lookups may make on a document of `source_len` bytes.
pub(crate) fn lookup_budget(source_len: usize) -> usize {
    source_len
        .saturating_mul(LOOKUPS_PER_BYTE)
        .saturating_add(LOOKUP_HEADROOM)
}

/// Bytes of the document for each tag it may hold.
///
/// Prose holds a sentence tag every few dozen bytes at most, and a tag costs index memory
/// whatever its size. One tag for every 64 bytes sits above what prose needs, and keeps a
/// document of very short sentences from building an index of gigabytes. The value is in
/// `docs/contract/policies.md`, section 1.9.
const BYTES_PER_TAG: usize = 64;

/// Tags allowed whatever the size of the document.
const TAG_HEADROOM: usize = 65_536;

/// The tags, and pieces of tags, that a document of `source_len` bytes may hold.
pub(crate) fn tag_budget(source_len: usize) -> usize {
    (source_len / BYTES_PER_TAG).saturating_add(TAG_HEADROOM)
}

/// Run every tagger over `doc`, then add the contexts its genre declares.
pub(crate) fn tag(
    registry: &TagRegistry,
    path: &str,
    source: &str,
    doc: &Document,
    front_matter: Option<&FrontMatter<'_>>,
    declared: Option<&DeclaredContextTagger>,
) -> Result<TagIndex, TagError> {
    let view = View::new(path, source, doc, front_matter);
    let max_tags = tag_budget(source.len());
    let mut tags = registry.collect_tags(&view, max_tags)?;
    if let Some(declared) = declared {
        // One tag for each declared context, so the budget cannot be crossed by more than
        // the length of the genre's list.
        tags.extend(declared.tag(&view)?);
        slopvac_context::normalize_tags(&mut tags);
    }
    if view.unmapped.get() {
        return Err(TagError::Unmapped);
    }
    Ok(view
        .split_interleaved(tags, max_tags)?
        .with_lookup_budget(lookup_budget(source.len())))
}

/// Choose the genre of `doc`: front matter, then an assignment from `opts`, then detection.
pub(crate) fn genre(
    registry: &GenreRegistry,
    opts: &ResolveOptions<'_>,
    path: &str,
    source: &str,
    doc: &Document,
    front_matter: Option<&FrontMatter<'_>>,
) -> Result<GenreResult, ContextError> {
    registry.resolve(&View::new(path, source, doc, front_matter), opts)
}

/// Steps `split_interleaved` takes on this thread, for the tests that bound its work.
#[cfg(feature = "test-counters")]
mod counted {
    use std::cell::Cell;

    thread_local! {
        static VISITS: Cell<usize> = const { Cell::new(0) };
    }

    pub(super) fn visit() {
        VISITS.with(|c| c.set(c.get() + 1));
    }

    pub(super) fn take() -> usize {
        VISITS.with(|c| c.replace(0))
    }
}

/// The steps taken on this thread to split tags over the extents of their blocks since the
/// last call. A test that lints tables of growing size and reads the count shows whether the
/// split does work in proportion to the table.
#[cfg(feature = "test-counters")]
#[doc(hidden)]
#[must_use]
pub fn take_split_visits() -> usize {
    counted::take()
}

#[cfg(test)]
mod tests {
    use proptest::prelude::*;
    use slopvac_parse::{Block, Projection, TokenKind};

    use super::*;

    /// `count` cells that fell back to line precision, so each has the span of the whole row.
    fn row_of_fallback_cells(count: usize) -> Document {
        let row = slopvac_model::Span::new(0, 1000).unwrap();
        let blocks = (0..count)
            .map(|_| {
                let mut projection = Projection::new();
                projection.push(TokenKind::Opaque, "cell", row);
                Block {
                    kind: BlockKind::TableCell { row: 0, column: 0 },
                    span: row,
                    projection: Some(projection),
                    containers: Vec::new(),
                }
            })
            .collect();
        Document {
            blocks,
            code_spans: Vec::new(),
            html_blocks: Vec::new(),
        }
    }

    #[test]
    fn every_tagger_reads_blocks_built_once() {
        let count = 50;
        let doc = row_of_fallback_cells(count);
        let registry = slopvac_context::builtin_registry().unwrap();
        let _ = entry::counted::take_built();
        tag(&registry, "t.rst", "", &doc, None, None).unwrap();
        // The built-in taggers each ask for the blocks. A rebuild per tagger would multiply
        // the count by the number of taggers.
        assert_eq!(entry::counted::take_built(), count);
    }

    /// Spans of the sentences of `block`, each mapped by the old per-sentence scan.
    fn oracle_sentence_spans(view: &View<'_>, block: &BlockView<'_>) -> Vec<Range<usize>> {
        let projection = view.entries
            [view.by_text[&(block.text.as_ptr().addr(), block.text.len())]]
            .projection
            .unwrap();
        slopvac_context::split_sentences(block)
            .into_iter()
            .map(|s| {
                let from = s.span.start - block.span.start;
                let span = projection.span_for_bytes(from, from + s.text.len());
                span.start()..span.end()
            })
            .collect()
    }

    fn token_kind() -> impl Strategy<Value = TokenKind> {
        prop_oneof![
            Just(TokenKind::Identity),
            Just(TokenKind::Entity),
            Just(TokenKind::Opaque),
            Just(TokenKind::Collapse),
            Just(TokenKind::Masked),
            Just(TokenKind::Wrap),
        ]
    }

    /// A projection of prose pieces whose source ranges ascend, with bridges between some.
    fn prose_projection() -> impl Strategy<Value = Projection> {
        let piece = (
            token_kind(),
            prop_oneof![
                Just("Go on. "),
                Just("é. "),
                Just("Hi! "),
                Just("x "),
                Just("😀 ok? ")
            ],
            0usize..6,
            any::<bool>(),
        );
        (0usize..50, prop::collection::vec(piece, 1..10)).prop_map(|(base, pieces)| {
            let mut p = Projection::new();
            let mut at = base;
            for (kind, text, len, bridge) in pieces {
                let src = slopvac_model::Span::new(at, at + len).unwrap();
                at += len;
                if bridge {
                    p.push_bridge(kind, text, src);
                } else {
                    p.push(kind, text, src);
                }
            }
            p
        })
    }

    fn cells(projections: Vec<Projection>, spans: &[(usize, usize)]) -> Document {
        let blocks = projections
            .into_iter()
            .zip(spans.iter().cycle())
            .enumerate()
            // Each block starts at its own offset, so no two share a span: a shared span
            // names the last block that has it, which is a different case.
            .map(|(i, (projection, &(_, len)))| Block {
                kind: BlockKind::TableCell { row: 0, column: 0 },
                span: slopvac_model::Span::new(i, i + len).unwrap(),
                projection: Some(projection),
                containers: Vec::new(),
            })
            .collect();
        Document {
            blocks,
            code_spans: Vec::new(),
            html_blocks: Vec::new(),
        }
    }

    proptest! {
        #[test]
        fn sentences_map_to_the_spans_the_per_sentence_scan_gave(
            projections in prop::collection::vec(prose_projection(), 1..4),
            spans in prop::collection::vec((0usize..40, 100usize..200), 1..4),
        ) {
            let doc = cells(projections, &spans);
            let view = View::new("t.rst", "", &doc, None);
            for block in view.blocks() {
                let got: Vec<_> = view.sentences(&block).into_iter().map(|s| s.span).collect();
                prop_assert_eq!(got, oracle_sentence_spans(&view, &block));
            }
        }

        #[test]
        fn the_extents_a_span_meets_are_those_the_scan_over_every_extent_found(
            runs in prop::collection::vec((0usize..60, 0usize..20), 0..30),
            span in (0usize..80, 0usize..80),
        ) {
            let runs: Vec<Range<usize>> = runs.into_iter().map(|(a, len)| a..a + len).collect();
            let span = span.0.min(span.1)..span.0.max(span.1);
            // The scan the sorted extents replaced: clip every run to the span.
            let mut want: Vec<Range<usize>> = runs
                .iter()
                .filter_map(|run| {
                    let from = run.start.max(span.start);
                    let to = run.end.min(span.end);
                    (from < to).then_some(from..to)
                })
                .collect();
            want.sort_by_key(|r| (r.start, r.end));
            let extents = Extents::new(runs);
            let mut got: Vec<Range<usize>> = extents.overlapping(&span, || {}).collect();
            got.sort_by_key(|r| (r.start, r.end));
            prop_assert_eq!(got, want);
        }
    }
}
