"""Parse a document into the spans the rule engine measures.

WHY THIS IS NOT A WHITESPACE SPLIT. ASD-STE100 rules 8.4 through 8.7 redefine what
"one word" means, and the 20/25-word sentence caps are meaningless without them:

  - a number counts as one word                       (`13`, `twenty-one`)
  - a number with its unit counts as one word         (`10 ms`, `512 MiB`)
  - an abbreviation counts as one word
  - a quoted span counts as one word
  - parenthesized text counts as one word             (rule 8.5)
  - a hyphenated word counts as one word              (rule 8.7)
  - numbers identifying a step or paragraph are NOT counted at all (rule 8.6)

A naive tokenizer over-counts every one of those and reports a compliant sentence
as too long. False positives are worse than misses here: they get the rule turned
off, which is how a gate stops gating.

MARKDOWN BLOCK STRUCTURE IS markdown-it-py's, not ours. The CommonMark reference
implementation reports a source line map per block token, so code fences, inline
code, URLs, link targets, and emphasis are identified by a parser that knows the
grammar instead of by line regexes that approximated it. Front matter is not
CommonMark, so it is stripped before parsing and its lines are held back to keep
every later line number correct; HTML comments are blanked after block assignment
so a suppression annotation is not itself linted.

The LINES ARE PRESERVED either way: `prose_lines` is index-aligned with the source,
so a reported line number opens the right place in the real file.

WHAT IS STILL OURS is everything CommonMark has no opinion on -- the word count
above, the sentence segmentation with its rule 8.4 colon case, the
procedural/descriptive split, and the document-level measures at the bottom.

`count_words` is ALSO THE TEST ORACLE for the compiled Vale word-count rule: the
generated alternation is asserted against it sentence by sentence, which is what
stops the two drifting apart. See `docs/metrics.md` for the contract itself.
"""

from __future__ import annotations

import regex as re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from markdown_it import MarkdownIt

from .model import TextType

# --- Markdown structure ------------------------------------------------------

FRONT_MATTER = re.compile(r"^---\s*$")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
INLINE_CODE = re.compile(r"`[^`\n]+`")

# `**x**` and `__x__`, non-greedy and single-line. A bold span does not straddle a
# blank line, and the greedy form fused every span on a line into one match, which
# undercounted exactly the documents the density rule is aimed at.
BOLD_SPAN = re.compile(r"(?<!\*)\*\*(?!\s)[^*\n]+?(?<!\s)\*\*(?!\*)|__(?!\s)[^_\n]+?(?<!\s)__")

# The em dash and the double hyphen that stands in for it. The en dash is excluded:
# in a numeric range it is correct typography, and the rule is about the aside.
DASH_AS_ASIDE = re.compile(r"—|(?<![-\w])--(?![-\w>])")

# --- Word counting per STE 8.4-8.7 -------------------------------------------

# A number, optionally signed, with decimals, thousands separators, ranges, or a
# version-like dotted form. One word.
NUMBER = r"[+-]?\d+(?:[.,]\d+)*(?:\.\d+)*"
# A unit that follows a number. This list is CLOSED on purpose. An open pattern
# like `[A-Za-z]{1,12}` treats any short word as a unit, so "13 thru 16" collapsed
# "thru" into "13" and the specification's own worked example came out at 8 words
# instead of 10. A missed exotic unit over-counts by one; a permissive pattern
# under-counts every sentence that has a number in it.
UNIT = (
    r"(?:"
    r"°[CF]?|K|"
    r"[numkKMGTP]?(?:m|g|s|A|V|W|J|N|Pa|Hz|B|bps|bit|byte|bytes|"
    r"[bB]|[iI]?B)|"
    r"ms|us|ns|ps|min|mins|h|hr|hrs|d|days?|wk|wks|mo|yr|yrs|"
    r"%|px|em|rem|pt|dpi|rpm|"
    r"KiB|MiB|GiB|TiB|PiB|kB|MB|GB|TB|PB|"
    r"mm|cm|km|in|ft|yd|mi|"
    r"mg|kg|lb|lbs|oz|"
    r"mL|L|gal|"
    r"deg|degC|degF|rad|"
    r"req/s|ops/s|qps|rps|"
    r"USD|EUR|GBP"
    r")(?:\^?-?\d)?"
)
SPELLED_COMPOUND_NUMBER = re.compile(
    r"^(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|"
    r"billion)(?:[- ](?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|hundred|thousand|million|billion))*$",
    re.I,
)
# An abbreviation: all-caps run, or dotted form. One word.
ABBREVIATION = re.compile(r"^(?:[A-Z]{2,}(?:s)?|(?:[A-Za-z]\.){2,})$")
HYPHENATED = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+$")
# Alphanumeric identifier: mixes letters and digits, or carries _ / : / .
WORDLIKE = re.compile(r"[A-Za-z0-9]")

QUOTED_SPAN = re.compile(r"\"[^\"\n]{1,200}\"|'[^'\n]{2,200}'|“[^”\n]{1,200}”")
PAREN_SPAN = re.compile(r"\([^()\n]{1,200}\)")
# Rule 8.6 carve-out: a leading step or paragraph number is not counted.
STEP_NUMBER = re.compile(r"^\s*(?:\d+(?:\.\d+)*[.)]?|[a-z][.)])\s+")

# --- Sentence segmentation ---------------------------------------------------

# Abbreviations that must not end a sentence.
NON_TERMINAL = {
    "e.g", "i.e", "etc", "vs", "cf", "al", "approx", "no", "fig", "eq", "ref",
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "inc", "ltd", "co",
    "vol", "ch", "sec", "min", "max", "avg", "std", "resp",
}
# The `\x00` in the lookahead is the code-span sentinel. A sentence that OPENS with
# an inline code span -- "`reason` is required." -- has no capital at its start, so
# without it the split never fires and the span fuses onto the sentence before. That
# is not cosmetic: it made the list-lead-in metric measure a colon against text from
# a preceding sentence, reporting a 26-word lead-in for a 5-word one.
SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+(?=[\"'“(\[]*[A-Z0-9\x00])")

IMPERATIVE_MARKERS = re.compile(
    r"^(?:please\s+)?(?:do|run|set|add|remove|delete|install|configure|open|close|"
    r"start|stop|restart|enable|disable|check|make|create|build|push|pull|commit|"
    r"copy|move|rename|edit|write|read|send|call|invoke|apply|use|select|click|"
    r"press|type|enter|choose|navigate|go|see|note|ensure|verify|confirm|update|"
    r"upgrade|downgrade|revert|reset|clear|flush|export|import|deploy|release|"
    r"tag|merge|rebase|clone|fetch|init|login|logout|grant|revoke|attach|detach|"
    r"mount|unmount|connect|disconnect|replace|insert|append|prepend|split|join|"
    r"wait|retry|skip|ignore|avoid|prevent|obey|put|get|give|take|keep|let|find|"
    r"list|show|print|log|test|try|fix|save|load|store|read)\b",
    re.I,
)
SAFETY_MARKER = re.compile(
    r"^\s*(?:\*{0,2}|>?\s*)(?:WARNING|CAUTION|DANGER|NOTICE|IMPORTANT)\b[:!]?",
    re.I,
)
NOTE_MARKER = re.compile(r"^\s*(?:\*{0,2}|>?\s*)(?:NOTE|TIP|HINT|INFO)\b[:!]?", re.I)


class BlockKind(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    CODE = "code"
    TABLE = "table"
    QUOTE = "quote"
    FRONT_MATTER = "front_matter"


@dataclass
class Sentence:
    text: str
    line: int
    column: int
    word_count: int
    text_type: TextType


@dataclass
class Block:
    kind: BlockKind
    lines: tuple[int, int]
    text: str
    sentences: list[Sentence] = field(default_factory=list)
    level: int = 0


@dataclass
class Document:
    """A parsed document.

    `prose_lines` is line-aligned with the source: index i holds line i+1's prose
    with code, links, and markup removed, or "" for a non-prose line. Rules match
    against this, so every finding's line number is the real one.
    """

    path: str
    raw: str
    raw_lines: list[str]
    prose_lines: list[str]
    blocks: list[Block]
    front_matter: dict[str, str] = field(default_factory=dict)

    @property
    def words(self) -> int:
        return sum(s.word_count for b in self.blocks for s in b.sentences)

    @property
    def sentences(self) -> list[Sentence]:
        return [s for b in self.blocks for s in b.sentences]

    @property
    def paragraphs(self) -> list[Block]:
        return [b for b in self.blocks if b.kind is BlockKind.PARAGRAPH]

    def prose_text(self) -> str:
        return "\n".join(self.prose_lines)

    def markup_text(self) -> str:
        """Prose lines with their markup intact, for rules that measure the markup.

        `prose_text` cannot serve: it strips the emphasis markers and dashes that a
        formatting rule counts. This keeps the raw line but drops code blocks, front
        matter, and inline code spans, so `**kwargs` in a snippet is not a bold span
        and a `--flag` in a command is not a dash.
        """
        skip: set[int] = set()
        for block in self.blocks:
            if block.kind in {BlockKind.CODE, BlockKind.FRONT_MATTER}:
                skip.update(range(block.lines[0], block.lines[1] + 1))
        kept = [
            line
            for number, line in enumerate(self.raw_lines, start=1)
            if number not in skip
        ]
        return INLINE_CODE.sub(" ", "\n".join(kept))


def count_words(text: str) -> int:
    """Count words the way ASD-STE100 rules 8.4-8.7 define a word.

    Collapses each multi-token unit to 1 before splitting, so the arithmetic
    matches the spec's own worked examples rather than a whitespace count.
    """
    # Rule 8.6 carve-out: a step or paragraph number is not counted.
    text = STEP_NUMBER.sub("", text)
    # Rule 8.5 and the quoted-span rule: collapse to a single placeholder token.
    text = QUOTED_SPAN.sub(" \x00 ", text)
    text = PAREN_SPAN.sub(" \x00 ", text)

    count = 0
    for token in text.split():
        token = token.strip(",;:!?.—–")
        if not token:
            continue
        if token == "\x00":
            count += 1
            continue
        if not WORDLIKE.search(token):
            continue  # bare punctuation
        count += 1

    # A number followed by a unit was counted twice above; correct it.
    tokens = [t for t in text.split() if WORDLIKE.search(t) or t == "\x00"]
    for first, second in zip(tokens, tokens[1:]):
        if re.fullmatch(NUMBER, first.strip(",;:!?.")) and re.fullmatch(
            UNIT, second.strip(",;:!?.")
        ):
            count -= 1
    return max(count, 0)


def classify_text_type(text: str) -> TextType:
    """Decide which word cap applies.

    The spec gives no mechanical test, so this is the practical discriminator it
    describes in prose: a safety block is SAFETY (20-word cap), a note is
    DESCRIPTIVE (25) even inside a procedure, an imperative is PROCEDURAL (20),
    and everything else is DESCRIPTIVE (25).

    Order is load-bearing: a warning is often phrased descriptively but still
    takes the procedural cap, and a note inside a procedure takes the descriptive
    cap despite its surroundings.
    """
    stripped = text.strip()
    if SAFETY_MARKER.match(stripped):
        return TextType.SAFETY
    if NOTE_MARKER.match(stripped):
        return TextType.DESCRIPTIVE
    body = STEP_NUMBER.sub("", stripped)
    if IMPERATIVE_MARKERS.match(body):
        return TextType.PROCEDURAL
    return TextType.DESCRIPTIVE


def split_sentences(text: str, start_line: int) -> list[Sentence]:
    """Segment into sentences, honouring rule 8.4.

    Rule 8.4: a colon that introduces a vertical list ends the sentence, and each
    list item is then counted as its own sentence for the word-length check. The
    caller passes list items in as their own blocks, so here the colon rule means
    a trailing `:` terminates rather than continues.
    """
    pieces: list[Sentence] = []
    # Protect non-terminal abbreviations from the splitter.
    guarded = text
    for abbr in NON_TERMINAL:
        guarded = re.sub(
            rf"(?<![A-Za-z]){re.escape(abbr)}\.", f"{abbr}\x01", guarded, flags=re.I
        )

    for chunk in SENTENCE_END.split(guarded):
        chunk = chunk.replace("\x01", ".").strip()
        if not chunk:
            continue
        # Rule 8.4: split a list lead-in at its colon.
        for part in re.split(r"(?<=:)\s+", chunk):
            part = part.strip()
            if not part or not WORDLIKE.search(part):
                continue
            pieces.append(
                Sentence(
                    text=part,
                    line=start_line,
                    column=1,
                    word_count=count_words(part),
                    text_type=classify_text_type(part),
                )
            )
    return pieces


def _inline_prose(token) -> str:
    """Prose text of an inline token, with non-prose spans removed.

    Walks markdown-it's inline token tree rather than running regexes over the
    raw line, so a URL inside backticks or a bracket inside a code span is
    already handled by the parser that understands them.

    An inline code span becomes `\\x00`, the count-as-one sentinel `count_words`
    already uses for a quoted or parenthesized span. It is ONE word, not zero: no
    rule should match inside a code span, but it occupies a slot in the sentence, and
    dropping it to whitespace made it vanish from every word count. That undercounted
    every length cap, and it surfaced first as a false positive rather than as a
    missed finding -- a wrapped sentence whose visible words are mostly code counted
    as a bare fragment, so the rejoin-a-one-fragment-paragraph rule fired on a whole
    sentence.

    The sentinel is non-word to `re`, so it reads as a boundary to the lexical rules
    that match over this text, which is what a code span should look like to them.
    """
    parts: list[str] = []
    skip_link_text = False
    for child in token.children or []:
        if child.type == "text":
            if not skip_link_text:
                parts.append(child.content)
        elif child.type == "code_inline":
            parts.append(" \x00 ")
        elif child.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif child.type == "image":
            # Alt text is prose; the src is not.
            parts.append(child.attrGet("alt") or "")
        elif child.type == "autolink_open":
            # A bare URL is not prose. Its text child repeats the target.
            skip_link_text = True
        elif child.type == "link_close":
            skip_link_text = False
    return "".join(parts).strip()


def _is_autolink(token) -> bool:
    return token.markup == "autolink"


def parse(path: str, raw: str) -> Document:
    """Parse markdown into blocks and a line-aligned prose projection.

    BLOCK STRUCTURE COMES FROM markdown-it-py, the CommonMark reference
    implementation, rather than from our own line matchers. It reports a
    `map` per block token, which is what keeps `prose_lines` aligned with the
    source so a finding's line number opens the right place in the real file.

    What stays ours is everything downstream: the STE word count, the sentence
    segmentation with its rule 8.4 colon case, and the procedural/descriptive
    split. CommonMark has no opinion on any of them.
    """
    raw_lines = raw.split("\n")
    prose_lines = [""] * len(raw_lines)
    blocks: list[Block] = []
    front_matter: dict[str, str] = {}

    body = raw
    offset = 0
    # Front matter is not CommonMark, so it is stripped before parsing and its
    # lines are held back to keep every later line number correct.
    if raw_lines and FRONT_MATTER.match(raw_lines[0]):
        for index in range(1, len(raw_lines)):
            if FRONT_MATTER.match(raw_lines[index]):
                offset = index + 1
                break
            if ":" in raw_lines[index]:
                key, _, value = raw_lines[index].partition(":")
                front_matter[key.strip()] = value.strip().strip("\"'")
        else:
            offset = len(raw_lines)
        blocks.append(Block(kind=BlockKind.FRONT_MATTER, lines=(1, offset), text=""))
        body = "\n".join(raw_lines[offset:])

    parser = MarkdownIt("commonmark", {"html": True}).enable("table")
    tokens = parser.parse(body)

    # A table cell is its own span: it is not a sentence in a paragraph, and
    # counting it as one inflates every density metric.
    table_cells: list[str] | None = None
    table_start = 0
    kind_stack: list[BlockKind] = []
    heading_level = 0

    def record(kind: BlockKind, first: int, last: int, text: str, level: int = 0) -> None:
        block = Block(kind=kind, lines=(first, last), text=text, level=level)
        block.sentences = split_sentences(text, first)
        blocks.append(block)

    for token in tokens:
        if token.type == "front_matter":
            continue

        if token.type == "table_open":
            table_cells = []
            table_start = token.map[0] + 1 + offset
            kind_stack.append(BlockKind.TABLE)
            continue
        if token.type == "table_close":
            block = Block(
                kind=BlockKind.TABLE,
                lines=(table_start, table_start),
                text=" ".join(table_cells or []),
            )
            for cell in table_cells or []:
                if WORDLIKE.search(cell):
                    block.sentences.append(
                        Sentence(
                            text=cell,
                            line=table_start,
                            column=1,
                            word_count=count_words(cell),
                            text_type=classify_text_type(cell),
                        )
                    )
            blocks.append(block)
            table_cells = None
            kind_stack.pop()
            continue

        if token.type == "fence" or token.type == "code_block":
            first = token.map[0] + 1 + offset
            last = token.map[1] + offset
            blocks.append(Block(kind=BlockKind.CODE, lines=(first, last), text=""))
            continue

        if token.type == "heading_open":
            heading_level = int(token.tag[1:])
            kind_stack.append(BlockKind.HEADING)
            continue
        if token.type == "paragraph_open":
            kind_stack.append(BlockKind.PARAGRAPH)
            continue
        if token.type == "blockquote_open":
            kind_stack.append(BlockKind.QUOTE)
            continue
        if token.type == "list_item_open":
            kind_stack.append(BlockKind.LIST_ITEM)
            continue
        if token.type in ("heading_close", "blockquote_close", "list_item_close"):
            if kind_stack:
                kind_stack.pop()
            continue
        if token.type == "paragraph_close":
            if kind_stack and kind_stack[-1] is BlockKind.PARAGRAPH:
                kind_stack.pop()
            continue

        if token.type != "inline" or token.map is None:
            continue

        text = _inline_prose(token)
        first = token.map[0] + 1 + offset
        last = token.map[1] + offset

        if table_cells is not None:
            table_cells.append(text)
            if 0 < first <= len(prose_lines):
                existing = prose_lines[first - 1]
                prose_lines[first - 1] = f"{existing} {text}".strip()
            continue

        # A multi-line paragraph is one block, and its prose is projected onto the
        # line each source line came from so a finding points at the right one.
        source = raw_lines[first - 1 : last]
        pieces = text.split("\n") if "\n" in text else None
        if pieces and len(pieces) == len(source):
            for index, piece in enumerate(pieces):
                prose_lines[first - 1 + index] = piece.strip()
            text = " ".join(p.strip() for p in pieces)
        else:
            for index in range(first - 1, min(last, len(prose_lines))):
                prose_lines[index] = ""
            if 0 < first <= len(prose_lines):
                prose_lines[first - 1] = text

        # A list item holding a paragraph reports as the ITEM, not the paragraph:
        # markdown-it wraps every item body in a paragraph, and STE 8.4 counts the
        # item. So the innermost non-paragraph container wins, and a bare
        # paragraph falls back to PARAGRAPH.
        kind = BlockKind.PARAGRAPH
        for candidate in reversed(kind_stack):
            if candidate is BlockKind.PARAGRAPH:
                continue
            if candidate in (BlockKind.HEADING, BlockKind.LIST_ITEM, BlockKind.QUOTE):
                kind = candidate
                break
        record(kind, first, last, text, heading_level if kind is BlockKind.HEADING else 0)

    # HTML comments can span lines; blank them after block assignment so a
    # suppression annotation is not itself linted.
    joined = HTML_COMMENT.sub(
        lambda m: re.sub(r"[^\n]", " ", m.group(0)), "\n".join(prose_lines)
    )
    prose_lines = joined.split("\n")

    return Document(
        path=path,
        raw=raw,
        raw_lines=raw_lines,
        prose_lines=prose_lines,
        blocks=blocks,
        front_matter=front_matter,
    )



# --- Document-level metrics --------------------------------------------------

VOWEL_GROUP = re.compile(r"[aeiouy]+", re.I)


def syllables(word: str) -> int:
    """Approximate syllable count. Orwell's own metric on the Ecclesiastes pair
    was 1.22 syllables per word for the good sentence and 2.37 for the bad one, so
    the measure only needs to be consistent, not phonetically exact."""
    word = re.sub(r"[^A-Za-z]", "", word).lower()
    if not word:
        return 0
    groups = VOWEL_GROUP.findall(word)
    count = len(groups)
    if word.endswith("e") and count > 1 and not word.endswith(("le", "ee", "ye")):
        count -= 1
    return max(count, 1)


CONCRETE_REFERENT = re.compile(
    r"\d|`[^`]+`|(?:/[\w.-]+)+|\b[a-z]+[A-Z]\w*|\b[A-Z]{2,}\b|--?[a-z][\w-]*"
)
ABSTRACTION_SUFFIX = re.compile(
    r"\b\w{4,}(?:tion|sion|ment|ness|ity|ance|ence|ism|ology)\b", re.I
)
HEDGE = re.compile(
    r"\b(?:may|might|could|can|possibly|potentially|somewhat|relatively|arguably|"
    r"generally|typically|often|usually|sometimes|perhaps|likely|seems?|appears?|"
    r"tends? to|suggests?)\b",
    re.I,
)

# A bullet whose visible content opens with a bold run and a colon:
# `- **Thing:** explanation`. The marker may be `-`, `*`, `+`, or `1.`, and the
# emphasis may be `**` or `__`.
#
# The colon may fall INSIDE or OUTSIDE the emphasis. Both forms render the same and
# both are the tell; a first version required it outside, which matched none of the
# four bullets in the probe file because `**Thing:**` is the form people write.
#
# Matched against the RAW line rather than the prose projection, because the
# projection strips the emphasis markers that are the whole signal here.
# The colon is REQUIRED. Making it optional matched `- **just bold** no colon`,
# which is emphasis rather than a pseudo-heading, and the rule is about the
# heading-shaped bullet specifically.
BOLD_COLON_BULLET = re.compile(
    r"^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*|__)[^*_]+?"
    r"(?::(?:\*\*|__)|(?:\*\*|__)\s*:)"
)

# A coordinated series: the commas that separate items, plus the conjunction
# before the last one. Counting SEPARATORS rather than parsing the noun phrases,
# because the rule's threshold is a count of items and a separator count converts
# to it by adding one.
COORDINATING_CONJUNCTION = re.compile(r",?\s+\b(?:and|or)\b\s+", re.I)

# Words that never carry a noun stack even though they sit between nouns. A
# preposition or an article ends the stack -- "the number of open pull requests"
# is not a five-word stack, it is two short ones.
STACK_BREAKER = frozenset(
    {
        "a", "an", "the", "of", "in", "on", "at", "to", "for", "from", "by",
        "with", "without", "into", "onto", "over", "under", "between", "through",
        "and", "or", "but", "nor", "as", "than", "that", "which", "who", "whom",
        "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
        "not", "no", "if", "when", "while", "after", "before", "during",
        # Subordinators. A clause boundary is exactly where a noun stack ends.
        # `because` was missing and produced `Specificity ranking loses because`
        # as a 4-word stack on this project's own README.
        "because", "since", "although", "though", "unless", "until", "whether",
        "whereas", "once", "where", "why", "how",
        # Determiners and pronouns. A possessive opens a noun phrase rather than
        # continuing a stack, so `keeps its shipped severity` is not a 4-word stack.
        "its", "their", "his", "her", "our", "your", "my", "this", "that",
        "these", "those", "it", "they", "them", "we", "us", "you", "he", "she",
        "each", "every", "any", "some", "all", "both", "either", "neither",
        "what", "whose", "there", "here", "then", "so", "such", "same", "other",
        "one", "two", "three", "four", "five",
        # Common verbs a suffix test cannot separate from nouns. `-er` and `-ing`
        # are in NOUN_SUFFIX, so without these `keeps ... reach` style runs counted.
        "keeps", "keep", "sets", "set", "gets", "get", "makes", "make", "does",
        "do", "reads", "read", "reach", "reaches", "gives", "give", "takes",
        "take", "uses", "use", "runs", "run", "names", "name", "says", "say",
        "counts", "count", "holds", "hold", "needs", "need", "puts", "put",
        "means", "mean", "resolve", "resolves", "clear", "clears", "switches",
        "switch", "subtracts", "subtract", "tracks", "track", "carry", "carries",
        "report", "reports", "lint", "linting", "asked", "ask", "folding",
        "overlapping",
        # `shows` and `loses` end in `-s` like a plural noun and carry no noun
        # suffix, so nothing else separates them: `blanket suppression shows up`
        # counted 4 and `Specificity ranking loses` counted 3.
        "shows", "show", "loses", "lose", "adds", "add", "drops", "drop",
        "applies", "apply", "wins", "win", "owns", "own", "picks", "pick",
        "stays", "stay", "sits", "sit", "sets",
        # Modals. A modal always introduces a verb, so it cannot sit inside a noun
        # stack: `the gates the whole document must clear` is not a 4-word stack.
        "must", "can", "will", "would", "should", "shall", "may", "might",
        "could", "cannot",
    }
)

# A capitalised or lowercase word that can sit in a noun stack. Excludes anything
# holding a digit, a hyphen, or an underscore: those are identifiers, and a
# `--flag` or a `snake_case` name is one unit rather than a stack of English
# nouns.
STACK_WORD = re.compile(r"^[A-Za-z]+$")

# Adjective and noun suffixes, for the ratio in `adjectives_per_noun`.
#
# THIS IS SUFFIX HEURISTICS, NOT A PART-OF-SPEECH TAGGER. The rule's own
# provenance says it needs one and that the engine does not have one. A tagger is
# a dependency this package does not carry, so the measurement is deliberately
# conservative: it counts only words whose suffix is a reliable signal, and it
# reports a ratio over those alone rather than over every word. An untagged word
# lands in neither count.
ADJECTIVE_SUFFIX = re.compile(
    r"\b\w{4,}(?:able|ible|ical|ful|less|ous|ive|istic|ary|" r"ish|like)\b", re.I
)
NOUN_SUFFIX = re.compile(
    r"\b\w{4,}(?:tion|sion|ment|ness|ity|ance|ence|ism|ology|er|or|ist|"
    r"ure|age|ing)\b",
    re.I,
)


def stdev(values: list[float]) -> float:
    """Population standard deviation. 0.0 for fewer than two values.

    Population rather than sample, because the paragraphs of a document are the
    whole population being described rather than a draw from a larger one.
    """
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


def longest_noun_stack(text: str) -> int:
    """Longest run of consecutive stackable words in a sentence.

    A run ends at a `STACK_BREAKER`, at an `-ly` adverb, at punctuation, or at any
    token that is not plain letters.

    A run counts ONLY IF at least one of its words carries a noun suffix. That
    condition is what makes the measure usable without a part-of-speech tagger.
    Adjacency alone counts far too much: measured on this project's own README,
    the bare adjacency version produced 73 findings, including 5 for
    `Score prose against three rulesets` and 7 for
    `This is a very good simple test case here today` -- runs of verbs, adjectives,
    and adverbs that no reader would call a noun stack. Requiring a noun-suffix
    anchor took both to 0 while still reporting 5 for
    `container orchestration platform migration strategy`.

    Under-reports on purpose. A stack of short Germanic nouns carries no suffix
    signal, so `disk cache size limit` is missed. A missed finding on a rule that
    ships advisory outside strict is the cheaper error here; a wall of false
    positives teaches people to disable the category.
    """
    longest = 0
    run: list[str] = []

    def close(longest: int) -> int:
        if len(run) > longest and any(NOUN_SUFFIX.match(w) for w in run):
            return len(run)
        return longest

    # Walks tokens and inspects the GAP between them, rather than splitting. A
    # split discards the separator, which made punctuation invisible: the comma in
    # a table cell reading `reference, specs, API docs, runbooks` disappeared and
    # the four separate items counted as one 5-word stack. A stack cannot span a
    # comma, a colon, or a bracket.
    previous_end = 0
    for match in re.finditer(r"[\w'\x00-]+", text):
        gap = text[previous_end : match.start()]
        previous_end = match.end()
        token = match.group().strip("'")
        broken = bool(gap) and not gap.isspace()
        if (
            broken
            or not token
            or not STACK_WORD.match(token)
            or token.lower() in STACK_BREAKER
            or token.lower().endswith("ly")
        ):
            longest = close(longest)
            run = []
            if broken and token and STACK_WORD.match(token) and (
                token.lower() not in STACK_BREAKER
                and not token.lower().endswith("ly")
            ):
                # The separator ended the previous run, but this token still opens
                # the next one. Dropping it here lost the first word of every stack
                # that followed any punctuation.
                run.append(token)
            continue
        run.append(token)
    return close(longest)


def coordinated_items(text: str) -> int:
    """Items in the longest coordinated series in a sentence.

    Counts separators and adds one. A series needs a conjunction: two clauses
    joined by a comma alone are not a list, and counting bare commas made every
    parenthetical read as a series.
    """
    if not COORDINATING_CONJUNCTION.search(text):
        return 0
    # Only the commas BEFORE the conjunction belong to the series. A trailing
    # subordinate clause after it would otherwise inflate the count.
    head = COORDINATING_CONJUNCTION.split(text)[0]
    return head.count(",") + 2
