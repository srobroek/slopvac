"""Document-level metric measurements the native engine can actually compute.

A metric name with no function here cannot fire, so it is reported rather than
run -- see `NATIVE_METRICS` and `Engine.unimplemented_metrics`. This module is
separate from the engine because the measurements are pure functions over a
parsed document: the engine only decides whether a value exceeds a rule's
threshold. Sentence-scope counts stay on the engine; only document-scope
arithmetic and the helpers those measurements share live here.
"""

from __future__ import annotations

import regex as re

from .analyze import (
    ABSTRACTION_SUFFIX,
    ADJECTIVE_SUFFIX,
    BOLD_COLON_BULLET,
    BOLD_SPAN,
    CONCRETE_REFERENT,
    DASH_AS_ASIDE,
    HEDGE,
    NOUN_SUFFIX,
    BlockKind,
    Document,
    count_words,
    stdev,
    syllables,
)
from .model import TextType

# STE 5.1 / 6.3 / 5.5: the cap depends on what kind of text the sentence is.
WORD_CAPS = {
    TextType.PROCEDURAL: 20,
    TextType.SAFETY: 20,
    TextType.DESCRIPTIVE: 25,
    TextType.ANY: 25,
}


def _list_stem_lines(document: Document) -> set[int]:
    """First lines of the paragraphs that introduce a list.

    A stem is a paragraph that ends in a colon and is followed immediately by a list
    item, with nothing between them. Both halves are required. The colon alone would
    exclude any short paragraph an author happened to end that way, and adjacency
    alone would exclude the sentence before every list whether it introduces one or
    not.
    """
    stems: set[int] = set()
    blocks = document.blocks
    for index, block in enumerate(blocks):
        if block.kind is not BlockKind.PARAGRAPH or not block.text.rstrip().endswith(":"):
            continue
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        if following is not None and following.kind is BlockKind.LIST_ITEM and block.lines:
            stems.add(block.lines[0])
    return stems


# Metric names `_run_metric` knows how to measure. A rule naming anything else
# cannot fire, so it is reported rather than run -- see `unimplemented_metrics`.
NATIVE_METRICS = frozenset(
    {
        "sentence_words",
        "clause_boundaries",
        "paragraph_words",
        "lead_in_words",
        "paragraph_sentences",
        "syllables_per_word",
        "passive_ratio",
        "hedge_per_100_words",
        "abstraction_density",
        "concrete_referents_per_paragraph",
        "paragraph_words_stdev",
        "adjectives_per_noun",
        "consecutive_bold_colon_bullets",
        "multiword_noun_words",
        "coordinated_items",
        "bold_spans_per_1000_words",
        "dash_per_1000_words",
    }
)

_PASSIVE = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being|get|gets|got)\s+"
    r"(?:\w+ly\s+)?(?:\w+(?:ed|en)|born|built|done|found|given|held|"
    r"kept|known|made|put|read|run|seen|sent|set|shown|told|written)\b",
    re.I,
)


def _prose_words(document: Document) -> tuple[str, list[str]]:
    text = document.prose_text()
    words = [w for w in re.findall(r"[A-Za-z']+", text)]
    return text, words


def syllables_per_word(document: Document) -> float:
    _, words = _prose_words(document)
    if not words:
        return 0.0
    return sum(syllables(w) for w in words) / len(words)


def passive_ratio(document: Document) -> float:
    sentences = document.sentences
    if not sentences:
        return 0.0
    hits = sum(1 for s in sentences if _PASSIVE.search(s.text))
    return hits / len(sentences)


def hedge_per_100_words(document: Document) -> float:
    text, words = _prose_words(document)
    if not words:
        return 0.0
    return len(HEDGE.findall(text)) / len(words) * 100


def abstraction_density(document: Document) -> float:
    text, words = _prose_words(document)
    if not words:
        return 0.0
    return len(ABSTRACTION_SUFFIX.findall(text)) / len(words) * 100


def concrete_referents_per_paragraph(document: Document) -> float:
    paragraphs = document.paragraphs
    if not paragraphs:
        return 0.0
    total = sum(len(CONCRETE_REFERENT.findall(p.text)) for p in paragraphs)
    return total / len(paragraphs)


def paragraph_words_stdev(document: Document) -> float:
    # The burstiness counter-signal. A model writes paragraphs of uniform
    # mass, so LOW dispersion is the finding -- note the rule compares with
    # `lt`, unlike every other metric here.
    #
    # Guarded at fewer than three paragraphs. Two paragraphs have a
    # dispersion but it means nothing, and a one-paragraph document would
    # score 0.0 and fire on every short file. `stdev` already returns 0.0
    # below two values, which is exactly the wrong answer for a rule whose
    # comparison is `lt`, so the guard has to live here rather than there.
    counts = [float(count_words(p.text)) for p in document.paragraphs]
    if len(counts) < 3:
        return float("inf")
    return stdev(counts)


def adjectives_per_noun(document: Document) -> float:
    # Suffix heuristics, not a tagger. See ADJECTIVE_SUFFIX for why, and
    # read the number as a signal rather than a measurement: the rule ships
    # advisory outside strict and its own threshold is marked INFERRED.
    text, _ = _prose_words(document)
    nouns = len(NOUN_SUFFIX.findall(text))
    if not nouns:
        return 0.0
    return len(ADJECTIVE_SUFFIX.findall(text)) / nouns


def consecutive_bold_colon_bullets(document: Document) -> float:
    # The LONGEST run, not the total. Four scattered bold-colon bullets
    # across a long document are a formatting choice; four in a row are the
    # tell, because that shape is what a model reaches for instead of prose
    # or a table.
    #
    # Reads `raw_lines`, since the prose projection strips the emphasis
    # markers this measures. A blank line does not break a run: markdown
    # allows a loose list, and the run is about consecutive ITEMS.
    longest = 0
    run = 0
    for line in document.raw_lines:
        if BOLD_COLON_BULLET.match(line):
            run += 1
            longest = max(longest, run)
        elif line.strip():
            run = 0
    return float(longest)


def bold_spans_per_1000_words(document: Document) -> float:
    return _markup_per_1000_words(document, BOLD_SPAN)


def dash_per_1000_words(document: Document) -> float:
    return _markup_per_1000_words(document, DASH_AS_ASIDE)


def _markup_per_1000_words(document: Document, pattern: re.Pattern[str]) -> float:
    # Both measure the MARKUP, so both read `markup_text` rather than the
    # prose projection, which strips the very characters they count. Both
    # denominators are the prose word count, not a count of the markup text,
    # so a document does not dilute its own density by adding code blocks.
    _, words = _prose_words(document)
    if not words:
        return 0.0
    return len(pattern.findall(document.markup_text())) / len(words) * 1000


_DOCUMENT_METRICS = {
    "syllables_per_word": syllables_per_word,
    "passive_ratio": passive_ratio,
    "hedge_per_100_words": hedge_per_100_words,
    "abstraction_density": abstraction_density,
    "concrete_referents_per_paragraph": concrete_referents_per_paragraph,
    "paragraph_words_stdev": paragraph_words_stdev,
    "adjectives_per_noun": adjectives_per_noun,
    "consecutive_bold_colon_bullets": consecutive_bold_colon_bullets,
    "bold_spans_per_1000_words": bold_spans_per_1000_words,
    "dash_per_1000_words": dash_per_1000_words,
}


def document_metric(name: str, document: Document) -> float:
    """Counted measures used by document-scope rules and by the report.

    Each traces to a source: syllables-per-word and concrete referents to
    Orwell's own arithmetic on the Ecclesiastes pair (1.22 good, 2.37 bad);
    passive ratio to his complaint about passive *preference* rather than use.
    """
    compute = _DOCUMENT_METRICS.get(name)
    if compute is None:
        return 0.0
    return compute(document)
