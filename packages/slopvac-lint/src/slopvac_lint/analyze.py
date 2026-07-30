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

Markdown handling: code fences, inline code, URLs, link targets, front matter, and
HTML comments are stripped before prose analysis but their LINES are preserved, so
a reported line number opens the right place in the real file. That is the same
line-preserving shadow technique the JSX extractor already uses.
"""

from __future__ import annotations

import regex as re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator

from .model import TextType

# --- Markdown structure ------------------------------------------------------

FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
FRONT_MATTER = re.compile(r"^---\s*$")
ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SETEXT_UNDERLINE = re.compile(r"^\s*(=+|-{2,})\s*$")
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
BLOCKQUOTE = re.compile(r"^\s*>\s?(.*)$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
AUTOLINK = re.compile(r"<https?://[^>\s]+>|https?://\S+")
BOLD_ITALIC = re.compile(r"(\*{1,3}|_{1,3})(?=\S)(.+?)(?<=\S)\1")

# --- Word counting per STE 8.4-8.7 -------------------------------------------

# A number, optionally signed, with decimals, thousands separators, ranges, or a
# version-like dotted form. One word.
NUMBER = r"[+-]?\d+(?:[.,]\d+)*(?:\.\d+)*"
# A unit glued to or following a number. Kept deliberately broad: the rule counts
# "number together with a unit of measurement" as one word regardless of unit.
UNIT = r"(?:°?[A-Za-zµΩ%/]{1,12}(?:\^?-?\d)?)"
NUMBER_UNIT = re.compile(rf"^{NUMBER}\s*{UNIT}?$")
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
IDENTIFIER = re.compile(r"^(?=.*[A-Za-z])(?=.*\d)[\w.:/-]+$|^\w+(?:_\w+)+$")
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


def strip_inline(text: str) -> str:
    """Remove inline constructs whose contents are not prose.

    Order matters: images before links (an image is a link with a bang), links
    before autolinks, and code before everything so that a URL inside backticks is
    already gone.
    """
    text = INLINE_CODE.sub(" ", text)
    text = MD_IMAGE.sub(r"\1", text)
    text = MD_LINK.sub(r"\1", text)
    text = AUTOLINK.sub(" ", text)
    text = BOLD_ITALIC.sub(r"\2", text)
    return text


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


def parse(path: str, raw: str) -> Document:
    """Parse markdown into blocks and a line-aligned prose projection."""
    raw_lines = raw.split("\n")
    prose_lines = [""] * len(raw_lines)
    blocks: list[Block] = []
    front_matter: dict[str, str] = {}

    index = 0
    total = len(raw_lines)

    # Front matter, only when the very first line opens it.
    if total and FRONT_MATTER.match(raw_lines[0]):
        index = 1
        while index < total and not FRONT_MATTER.match(raw_lines[index]):
            if ":" in raw_lines[index]:
                key, _, value = raw_lines[index].partition(":")
                front_matter[key.strip()] = value.strip().strip("\"'")
            index += 1
        blocks.append(
            Block(kind=BlockKind.FRONT_MATTER, lines=(1, index + 1), text="")
        )
        index += 1

    paragraph: list[tuple[int, str]] = []

    def flush_paragraph() -> None:
        if not paragraph:
            return
        first = paragraph[0][0]
        last = paragraph[-1][0]
        text = " ".join(t for _, t in paragraph).strip()
        if text:
            block = Block(
                kind=BlockKind.PARAGRAPH, lines=(first, last), text=text
            )
            block.sentences = split_sentences(text, first)
            blocks.append(block)
        paragraph.clear()

    while index < total:
        line = raw_lines[index]
        number = index + 1

        fence = FENCE.match(line)
        if fence:
            flush_paragraph()
            marker = fence.group(2)
            start = number
            index += 1
            while index < total:
                closing = FENCE.match(raw_lines[index])
                if closing and closing.group(2)[0] == marker[0] and len(
                    closing.group(2)
                ) >= len(marker):
                    index += 1
                    break
                index += 1
            blocks.append(
                Block(kind=BlockKind.CODE, lines=(start, index), text="")
            )
            continue

        if not line.strip():
            flush_paragraph()
            index += 1
            continue

        heading = ATX_HEADING.match(line)
        if heading:
            flush_paragraph()
            text = strip_inline(heading.group(2)).strip()
            prose_lines[index] = text
            block = Block(
                kind=BlockKind.HEADING,
                lines=(number, number),
                text=text,
                level=len(heading.group(1)),
            )
            block.sentences = split_sentences(text, number)
            blocks.append(block)
            index += 1
            continue

        if TABLE_ROW.match(line):
            flush_paragraph()
            start = number
            cells: list[str] = []
            while index < total and TABLE_ROW.match(raw_lines[index]):
                row = raw_lines[index]
                if not re.fullmatch(r"\s*\|[\s|:-]+\|\s*", row):
                    text = strip_inline(row.strip().strip("|"))
                    parts = [c.strip() for c in text.split("|")]
                    prose_lines[index] = " ".join(parts)
                    cells.extend(p for p in parts if p)
                index += 1
            block = Block(
                kind=BlockKind.TABLE, lines=(start, index), text=" ".join(cells)
            )
            # Each cell is its own span: a table cell is not a sentence in a
            # paragraph, and counting it as one inflates every density metric.
            for offset, cell in enumerate(cells):
                if WORDLIKE.search(cell):
                    block.sentences.append(
                        Sentence(
                            text=cell,
                            line=start,
                            column=1,
                            word_count=count_words(cell),
                            text_type=classify_text_type(cell),
                        )
                    )
            blocks.append(block)
            continue

        item = LIST_ITEM.match(line)
        if item:
            flush_paragraph()
            text = strip_inline(item.group(2)).strip()
            prose_lines[index] = text
            block = Block(
                kind=BlockKind.LIST_ITEM, lines=(number, number), text=text
            )
            block.sentences = split_sentences(text, number)
            blocks.append(block)
            index += 1
            continue

        quote = BLOCKQUOTE.match(line)
        if quote:
            flush_paragraph()
            text = strip_inline(quote.group(1)).strip()
            prose_lines[index] = text
            block = Block(kind=BlockKind.QUOTE, lines=(number, number), text=text)
            block.sentences = split_sentences(text, number)
            blocks.append(block)
            index += 1
            continue

        cleaned = strip_inline(line).strip()
        prose_lines[index] = cleaned
        paragraph.append((number, cleaned))
        index += 1

    flush_paragraph()

    # HTML comments can span lines; blank them after block assignment so a
    # suppression comment does not itself get linted.
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
