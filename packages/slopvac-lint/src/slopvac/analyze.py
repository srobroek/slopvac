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
SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”’)\]]*\s+(?=[\"'“(\[]*[A-Z0-9])")

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
    already handled by the parser that understands them. An inline code span
    becomes a space: it is one token to the word counter but not a word.
    """
    parts: list[str] = []
    skip_link_text = False
    for child in token.children or []:
        if child.type == "text":
            if not skip_link_text:
                parts.append(child.content)
        elif child.type == "code_inline":
            parts.append(" ")
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
