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

from bisect import bisect_right
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser

import regex as re
from markdown_it import MarkdownIt

from .model import TextType

# --- Markdown structure ------------------------------------------------------

FRONT_MATTER = re.compile(r"^---\s*$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
# CommonMark closes a code span with a backtick run exactly as long as its
# opener. Equal-length runs may contain shorter runs, so a single-backtick
# expression leaks valid ``code ` — here`` spans into markup metrics.
INLINE_CODE = re.compile(
    r"(?<!`)(?P<ticks>`+)(?P<body>.*?)(?<!`)(?P=ticks)(?!`)", re.S
)


# Not prose: machinery, and code, which the markdown side already leaves alone as
# fences. The block is recorded as CODE so its lines count as code, not text.
_SKIP_HTML_TAGS = frozenset({"script", "style", "noscript", "head", "template", "pre", "code", "kbd", "samp"})

# `**x**` and `__x__`, non-greedy and single-line. A bold span does not straddle a
# blank line, and the greedy form fused every span on a line into one match, which
# undercounted exactly the documents the density rule is aimed at.
BOLD_SPAN = re.compile(r"(?<!\*)\*\*(?!\s)[^*\n]+?(?<!\s)\*\*(?!\*)|__(?!\s)[^_\n]+?(?<!\s)__")

# The em dash and the double hyphen that stands in for it. The en dash is excluded:
# in a numeric range it is correct typography, and the rule is about the aside.
DASH_AS_ASIDE = re.compile(r"—|(?<![-\w])--(?![-\w>])")

# --- Word counting per STE 8.4-8.7 -------------------------------------------

SENTINEL = "\x00"

# The regular expressions below only identify spans whose *interior* must not be
# counted again. They deliberately do not decide sentence boundaries; the
# segmenter keeps a separate protected-span map so punctuation outside a span is
# still visible. A NUL is used as the replacement because markdown-it already
# uses it for inline code and it cannot occur in normal prose.
NUMBER = r"[+-]?\d+(?:[.,]\d+)*(?:\.\d+)*"
UNIT = (
    r"(?:"
    r"°[CF]?|K|"
    r"[numkKMGTP]?(?:m|g|s|V|W|J|N|Pa|Hz|B|bps|bit|byte|bytes|"
    r"[bB]|[iI]?B)|"
    r"ms|us|ns|ps|min|mins|second|seconds|minute|minutes|h|hr|hrs|hour|hours|"
    r"d|day|days|wk|wks|week|weeks|mo|month|months|yr|yrs|year|years|"
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
WORDLIKE = re.compile(r"[A-Za-z0-9]")

CODE_SPAN = re.compile(r"(?<!`)`{1,}(?P<body>[^`\n]*?)`{1,}(?!`)")
URL_OR_PATH = re.compile(
    r"(?:https?://|ftp://)[^\s<>]+|(?<!\w)/(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
)
FLAG_OR_ENV = re.compile(r"--[A-Za-z][A-Za-z0-9-]*|\$[A-Z][A-Z0-9_]*")
IDENTIFIER = re.compile(
    r"(?<!\w)(?=[A-Za-z0-9_]*[A-Za-z])(?=[A-Za-z0-9_]*\d)"
    r"[A-Za-z_][A-Za-z0-9_]*(?:(?:[.:])[A-Za-z0-9_]+)+(?!\w)"
)
MIXED_IDENTIFIER = re.compile(
    r"(?<!\w)(?=[A-Za-z0-9_]*[A-Za-z])(?=[A-Za-z0-9_]*\d)"
    r"[A-Za-z][A-Za-z0-9_]*\d[A-Za-z0-9_]*(?!\w)"
)

QUOTED_SPAN = re.compile(
    r'(?<![\w\'])"[^"\n]{1,200}"(?!\w)|'
    r"(?<![\w'])'[^'\n]{2,200}'(?!\w)|"
    r"(?<!\w)“[^”\n]{1,200}”(?!\w)|(?<!\w)‘[^’\n]{1,200}’(?!\w)"
)
PAREN_SPAN = re.compile(r"\([^()\n]{1,200}\)")

# Rule 8.6 carve-out: a leading step or paragraph number is not counted. Keep
# the marker in the sentence text for matching, but remove it from counting and
# classification. The documented forms include decimal section numbers,
# parenthesized markers, Roman markers, and the literal ``Step N`` label.
STEP_NUMBER = re.compile(
    r"^\s*(?:(?:step\s+\d+(?:\.\d+)*[.:)]?)|"
    r"(?:\([A-Za-z0-9ivxIVX]+\)|(?:[A-Za-z]|[ivxIVX]+|\d+)[.)])|"
    r"(?:\d+(?:\.\d+)+\.?)\s*)(?=\s|$)",
    re.I,
)

# --- Sentence segmentation ---------------------------------------------------

NON_TERMINAL = {
    "e.g", "i.e", "etc", "vs", "cf", "al", "approx", "no", "fig", "eq", "ref",
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "inc", "ltd", "co",
    "vol", "ch", "sec", "min", "max", "avg", "std", "resp",
}

# A closed vocabulary is safer than treating every sentence-initial word as an
# imperative. It covers the base forms in the runbook corpus and keeps ordinary
# descriptive openings such as ``The`` and ``This`` out of procedural rules.
IMPERATIVE_VERBS = frozenset(
    "add apply attach backup build call check choose clear clone close confirm "
    "connect configure copy create delete deploy detach disable disconnect do "
    "drain edit enable ensure enter export fence fetch find fix flush follow get give "
    "go grant identify import init install invoke keep list load log login logout make "
    "merge monitor mount move navigate notify open perform point prepend print "
    "promote pull push put read record release reload remove rename replace report "
    "reset restart retry revoke roll run save select send set show skip split start "
    "stop store tag take test type unmount update upgrade use verify wait write "
    "rotate schedule stage downgrade execute inspect hold leave remember consider"
    .split()
)
IMPERATIVE_MARKERS = re.compile(
    rf"^(?:please\s+)?(?:do\s+not\s+|do\s+)?(?:{'|'.join(sorted(IMPERATIVE_VERBS, key=len, reverse=True))})\b",
    re.I,
)
TO_VERB = re.compile(
    rf"^to\s+(?:{'|'.join(sorted(IMPERATIVE_VERBS, key=len, reverse=True))})\b",
    re.I,
)
REMEMBER_TO = re.compile(
    rf"^(?:remember|make\s+sure)\s+to\s+(?:{'|'.join(sorted(IMPERATIVE_VERBS, key=len, reverse=True))})\b",
    re.I,
)
SAFETY_MARKER = re.compile(
    r"^\s*(?:>\s*)?(?:\*{0,2})?(?:WARNING|CAUTION|DANGER|NOTICE|ATTENTION|IMPORTANT)\b"
    r"(?:\*{0,2})?\s*[:.!]?",
    re.I,
)
NOTE_MARKER = re.compile(
    r"^\s*(?:>\s*)?(?:\*{0,2})?(?:NOTE|TIP|HINT|INFO|IMPORTANT)\b"
    r"(?:\*{0,2})?\s*[:.!]?",
    re.I,
)


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
    # Each entry is (offset in normalized text, source line). Wrapped pieces
    # are joined with one space for matching, while their starts remain mapped
    # to the physical lines that supplied them.
    line_starts: list[tuple[int, int]] = field(default_factory=list)

    def position(self, offset: int) -> tuple[int, int]:
        """Map a normalized text offset to its physical source line/column."""
        if not self.line_starts:
            return self.lines[0], offset + 1
        index = max(0, bisect_right(self.line_starts, (offset, float("inf"))) - 1)
        start, line = self.line_starts[index]
        return line, offset - start + 1


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
        """Prose lines with their markup intact, for rules that measure the markup."""
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


_NUMBER_WITH_UNIT = re.compile(
    rf"(?<!\w){NUMBER}(?:\s+(?:degrees?\s+(?:Celsius|Fahrenheit)|degrees?))?"
    rf"(?:\s+(?:{UNIT}))?(?!\w)"
)

_ABBREVIATION_NUMBER = re.compile(
    r"(?<!\w)(?:no|number|fig|figure|sec|section|ref)\.\s+\d+(?!\w)", re.I
)
_PROPER_NAME = re.compile(
    r"(?<!\w)(?:[A-Z][A-Za-z0-9'’’-]*|of|and|for|the)"
    r"(?:\s+(?:[A-Z][A-Za-z0-9'’’-]*|of|and|for|the)){1,}(?!\w)"
)


def _collapse(text: str, patterns: tuple[re.Pattern[str], ...]) -> str:
    """Replace each matched span with the one-token sentinel."""
    for pattern in patterns:
        text = pattern.sub(f" {SENTINEL} ", text)
    return text


def _collapse_proper_names(text: str) -> str:
    """Phase 4: a run of two or more capitalised tokens is one word.

    The first word of a sentence is capitalised for a reason that has nothing to
    do with names, so a two-token run at the start of the text ("The API
    returned...") is not a name; it collapsed as one before this guard and the
    Vale oracle (7 words) disagreed with the counter (6). A run of three or more
    at the start ("Amazon Web Services announced...") still collapses, as does
    any run after the first word.
    """

    def replace(match: re.Match[str]) -> str:
        first = match.group().split(maxsplit=1)[0].lower()
        if first in IMPERATIVE_VERBS:
            return match.group()
        capitalised = re.findall(r"\b[A-Z][A-Za-z0-9'’’-]*", match.group())
        if len(capitalised) < 2:
            return match.group()
        if len(capitalised) == 2 and not text[: match.start()].strip():
            return match.group()
        return f" {SENTINEL} "

    return _PROPER_NAME.sub(replace, text)


def count_words(text: str) -> int:
    """Count words according to the ordered phases in ``docs/metrics.md``.

    The measured audit probes exposed three different over-counting paths in the
    old whitespace counter: numbered steps added one, identifiers and units were
    split apart, and an apostrophe in a contraction could pair with a later one as
    a quotation. The phase order is therefore explicit rather than a collection of
    independent substitutions.
    """
    # Phase 0: delete the uncounted step or paragraph marker.
    text = STEP_NUMBER.sub("", text)

    # Phases 1-3: collapse code, identifiers, quoted spans, and quoted titles.
    text = _collapse(
        text,
        (CODE_SPAN, URL_OR_PATH, FLAG_OR_ENV, IDENTIFIER, MIXED_IDENTIFIER),
    )
    text = _collapse(text, (_ABBREVIATION_NUMBER, QUOTED_SPAN))

    # Phase 4: collapse proper names. Phase 5 makes a parenthetical one token.
    text = _collapse_proper_names(text)
    text = _collapse(text, (PAREN_SPAN,))

    # Phases 6-7: number/unit pairs and abbreviations. A bare number is also
    # replaced: it still counts once, but cannot split from a following unit.
    text = _collapse(text, (_NUMBER_WITH_UNIT,))

    count = 0

    for token in text.split():
        token = token.strip(",;:!? .—–")
        if not token:
            continue
        if token == SENTINEL or WORDLIKE.search(token):
            count += 1
    return count


def classify_text_type(text: str) -> TextType:
    """Select the sentence cap, conservatively distinguishing instructions.

    The audit's runbook probe contained imperative steps beginning with verbs not
    present in the original closed list (``record``, ``reload``, ``remember`` and
    ``notify``). The vocabulary below is intentionally finite: an unknown opening
    remains descriptive, which is safer than applying the 20-word cap to prose.
    """
    stripped = text.strip()
    if SAFETY_MARKER.match(stripped):
        return TextType.SAFETY
    if NOTE_MARKER.match(stripped):
        return TextType.DESCRIPTIVE
    body = STEP_NUMBER.sub("", stripped).lstrip(" -*+")
    if (
        IMPERATIVE_MARKERS.match(body)
        or TO_VERB.match(body)
        or REMEMBER_TO.match(body)
        or re.match(r"^you\s+(?:should|must|need\s+to)\b", body, re.I)
    ):
        return TextType.PROCEDURAL
    return TextType.DESCRIPTIVE


def _protected_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for pattern in (CODE_SPAN, QUOTED_SPAN, PAREN_SPAN, URL_OR_PATH, IDENTIFIER):
        ranges.extend((match.start(), match.end()) for match in pattern.finditer(text))
    return sorted(ranges)


def _inside(index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in ranges)


def _is_non_terminal_period(text: str, index: int) -> bool:
    prefix = text[: index + 1]
    for abbreviation in NON_TERMINAL:
        if re.search(rf"(?<![A-Za-z]){re.escape(abbreviation)}\.$", prefix, re.I):
            return True
    # A leading ordered marker such as ``A. Restart`` is not a sentence.
    line_prefix = prefix.rsplit("\n", 1)[-1].strip()
    if re.fullmatch(r"(?:\(?[A-Za-z0-9ivxIVX]+\)?|Step\s+\d+(?:\.\d+)*)\.", line_prefix, re.I):
        return True
    return False


def _split_vertical_list(text: str) -> list[str]:
    """Split a lead-in and its items only when the colon introduces a list."""
    lines = text.splitlines()
    if len(lines) < 2:
        return [text]
    for index, line in enumerate(lines):
        if not re.search(r":\s*$", line):
            continue
        tail = [part.strip() for part in lines[index + 1 :] if part.strip()]
        if not tail or not all(
            re.match(r"^(?:[-*+]|\d+[.)]|[A-Za-z][.)])\s+", part) for part in tail
        ):
            continue
        head = "\n".join(lines[: index + 1]).strip()
        return [head, *tail]
    return [text]


def split_sentences(text: str, start_line: int) -> list[Sentence]:
    """Split at real sentence boundaries and vertical-list lead-in colons."""
    if not text.strip():
        return []
    protected = _protected_ranges(text)
    cuts: list[int] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in ".!?" and not _inside(index, protected):
            if char == "." and _is_non_terminal_period(text, index):
                index += 1
                continue
            end = index + 1
            while end < len(text) and text[end] in "\"'”’)]":
                end += 1
            cursor = end
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            if cursor == len(text) or text[cursor].isupper() or text[cursor].isdigit():
                cuts.append(end)
                index = cursor
                continue
        index += 1

    pieces: list[Sentence] = []
    start = 0
    for end in [*cuts, len(text)]:
        chunk = text[start:end].strip()
        start = end
        if not chunk:
            continue
        for part in _split_vertical_list(chunk):
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
            # Keep the physical boundary in the rendered block. The parser later
            # joins pieces with one matching space and records each piece's line.
            parts.append("\n")
        elif child.type == "image":
            # Alt text is prose; the src is not.
            parts.append(child.attrGet("alt") or "")
        elif child.type == "autolink_open":
            # A bare URL is not prose. Its text child repeats the target.
            skip_link_text = True
        elif child.type == "link_close":
            skip_link_text = False
    return "".join(parts).strip()


class _HtmlTextExtractor(HTMLParser):
    """Visible text of an HTML document, aligned to source lines."""

    def __init__(self, line_count: int) -> None:
        super().__init__(convert_charrefs=True)
        self.prose_lines = [""] * line_count
        self._skip = 0
        self._boundary = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._boundary = True
        if tag in _SKIP_HTML_TAGS:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        self._boundary = True
        if tag in _SKIP_HTML_TAGS and self._skip:
            self._skip -= 1

    def handle_comment(self, data: str) -> None:
        self._boundary = True

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        line, _column = self.getpos()
        for offset, part in enumerate(data.split("\n")):
            index = line - 1 + offset
            if 0 <= index < len(self.prose_lines):
                previous = self.prose_lines[index]
                if (
                    self._boundary
                    and previous
                    and not previous[-1].isspace()
                    and not part[:1].isspace()
                ):
                    part = " " + part
                self.prose_lines[index] += part
        self._boundary = False


_FENCE_START = re.compile(r"^\s{0,3}(?P<marker>(?P<char>`|~){3,})")


def _html_fence_lines(content: str) -> set[int]:
    """Return local lines occupied by Markdown fences embedded in HTML.

    markdown-it deliberately hands a complete HTML block to the HTML renderer, so
    a fenced example inside a ``<div>`` is otherwise indistinguishable from visible
    text. Treating the fence and its body as code preserves the same non-prose
    contract as a native Markdown fence.
    """
    skipped: set[int] = set()
    opening: tuple[str, int, int] | None = None
    lines = content.splitlines()
    for index, line in enumerate(lines):
        match = _FENCE_START.match(line)
        if opening is None:
            if match:
                opening = (match.group("char"), len(match.group("marker")), index)
            continue
        skipped.add(index)
        if match and match.group("char") == opening[0]:
            if len(match.group("marker")) >= opening[1]:
                skipped.update(range(opening[2], index + 1))
                opening = None
    if opening is not None:
        skipped.update(range(opening[2], len(lines)))
    return skipped


def _project_html_block(
    content: str, first: int, last: int, prose_lines: list[str]
) -> tuple[str, list[tuple[int, int]], tuple[int, int] | None, list[tuple[int, int]]]:
    """Extract visible HTML-block text while retaining source-line starts."""
    line_count = max(last - first + 1, 1)
    extractor = _HtmlTextExtractor(line_count)
    extractor.feed(content)
    extractor.close()
    fence_lines = _html_fence_lines(content)

    pieces: list[str] = []
    line_starts: list[tuple[int, int]] = []
    text_offset = 0
    visible_lines: list[int] = []
    for local, piece in enumerate(extractor.prose_lines):
        source_line = first + local
        clean = "" if local in fence_lines else piece.strip()
        if 0 < source_line <= len(prose_lines):
            prose_lines[source_line - 1] = clean
        if not clean:
            continue
        visible_lines.append(source_line)
        if pieces:
            text_offset += 1
        line_starts.append((text_offset, source_line))
        pieces.append(clean)
        text_offset += len(clean)

    text = "".join(piece if index == 0 else " " + piece for index, piece in enumerate(pieces))
    paragraph_lines = (
        (visible_lines[0], visible_lines[-1]) if visible_lines else None
    )
    code_blocks: list[tuple[int, int]] = []
    if fence_lines:
        start = previous = min(fence_lines)
        for line in sorted(fence_lines)[1:]:
            if line != previous + 1:
                code_blocks.append((first + start, first + previous))
                start = line
            previous = line
        code_blocks.append((first + start, first + previous))
    return text, line_starts, paragraph_lines, code_blocks


def _parse_html(path: str, raw: str) -> Document:
    """Project an HTML file onto line-aligned prose so native rules can run.

    CommonMark treats a `.html` file as `html_block` tokens and the markdown
    walker skips those, which left every HTML document at zero words.
    `html.py` is the report renderer, not a source projection, so this uses
    stdlib `html.parser` and keeps `prose_lines` index-aligned with the source.
    """
    raw_lines = raw.split("\n")
    extractor = _HtmlTextExtractor(len(raw_lines))
    extractor.feed(raw)
    extractor.close()
    prose_lines = [line.strip() for line in extractor.prose_lines]
    joined = HTML_COMMENT.sub(
        lambda m: re.sub(r"[^\n]", " ", m.group(0)), "\n".join(prose_lines)
    )
    prose_lines = joined.split("\n")

    blocks: list[Block] = []
    for index, text in enumerate(prose_lines):
        if not text:
            continue
        number = index + 1
        block = Block(kind=BlockKind.PARAGRAPH, lines=(number, number), text=text)
        block.sentences = split_sentences(text, number)
        blocks.append(block)

    return Document(
        path=path,
        raw=raw,
        raw_lines=raw_lines,
        prose_lines=prose_lines,
        blocks=blocks,
    )


def parse(path: str, raw: str) -> Document:
    """Parse markdown or HTML into blocks and a line-aligned prose projection.

    BLOCK STRUCTURE COMES FROM markdown-it-py, the CommonMark reference
    implementation, rather than from our own line matchers. It reports a
    `map` per block token, which is what keeps `prose_lines` aligned with the
    source so a finding's line number opens the right place in the real file.

    A `.html` file is not CommonMark: the whole document is one `html_block`,
    so those inputs take a visible-text projection instead.

    What stays ours is everything downstream: the STE word count, the sentence
    segmentation with its rule 8.4 colon case, and the procedural/descriptive
    split. CommonMark has no opinion on any of them.
    """
    if path.lower().endswith((".html", ".htm")):
        return _parse_html(path, raw)
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
    def record(
        kind: BlockKind,
        first: int,
        last: int,
        text: str,
        line_starts: list[tuple[int, int]],
        level: int = 0,
    ) -> None:
        block = Block(
            kind=kind,
            lines=(first, last),
            text=text,
            level=level,
            line_starts=line_starts,
        )
        block.sentences = split_sentences(text, first)
        blocks.append(block)

    for token in tokens:
        if token.type == "front_matter":
            continue

        if token.type == "html_block" and token.map is not None:
            first = token.map[0] + 1 + offset
            last = token.map[1] + offset
            text, line_starts, paragraph_lines, code_blocks = _project_html_block(
                token.content, first, last, prose_lines
            )
            if paragraph_lines is not None:
                record(
                    BlockKind.PARAGRAPH,
                    paragraph_lines[0],
                    paragraph_lines[1],
                    text,
                    line_starts,
                )
            for code_first, code_last in code_blocks:
                blocks.append(Block(kind=BlockKind.CODE, lines=(code_first, code_last), text=""))
            continue

        if token.type == "table_open" and token.map is not None:
            table_cells = []
            table_start = token.map[0] + 1 + offset
            kind_stack.append(BlockKind.TABLE)
            continue
        if token.type == "table_close":
            block = Block(
                kind=BlockKind.TABLE,
                lines=(table_start, table_start),
                text=" ".join(table_cells or []),
                line_starts=[(0, table_start)],
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

        if (token.type == "fence" or token.type == "code_block") and token.map is not None:
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

        rendered = _inline_prose(token)
        first = token.map[0] + 1 + offset
        last = token.map[1] + offset

        if table_cells is not None:
            table_cells.append(rendered.replace("\n", " "))
            if 0 < first <= len(prose_lines):
                existing = prose_lines[first - 1]
                prose_lines[first - 1] = f"{existing} {rendered}".strip()
            continue

        # Keep one normalized block for matching, but retain the source line for
        # every non-empty piece. This makes paragraph/sentence patterns span soft
        # breaks without flattening their findings onto the first line.
        source = raw_lines[first - 1 : last]
        pieces = rendered.split("\n")
        if len(pieces) < len(source):
            pieces.extend([""] * (len(source) - len(pieces)))
        normalized: list[str] = []
        line_starts: list[tuple[int, int]] = []
        for index, piece in enumerate(pieces[: len(source)]):
            clean = piece.strip()
            if clean:
                if normalized:
                    normalized.append(" ")
                line_starts.append((sum(len(part) for part in normalized), first + index))
                normalized.append(clean)
            if 0 < first + index <= len(prose_lines):
                prose_lines[first + index - 1] = clean
        text = "".join(normalized)
        # A list item holding a paragraph reports as the ITEM, not the paragraph:
        # markdown-it wraps every item body in a paragraph, and STE 8.4 counts
        # the item. The innermost non-paragraph container wins.
        kind = BlockKind.PARAGRAPH
        for candidate in reversed(kind_stack):
            if candidate is BlockKind.PARAGRAPH:
                continue
            if candidate in (BlockKind.HEADING, BlockKind.LIST_ITEM, BlockKind.QUOTE):
                kind = candidate
                break
        record(
            kind,
            first,
            last,
            text,
            line_starts,
            heading_level if kind is BlockKind.HEADING else 0,
        )

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
        "including", "and", "or", "but", "nor", "as", "than", "that", "which", "who", "whom",
        "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
        "not", "no", "if", "when", "while", "after", "before", "during",
        # Subordinators. A clause boundary is exactly where a noun stack ends.
        # `because` was missing and produced `Specificity ranking loses because`
        # as a 4-word stack on this project's own README.
        "because", "since", "although", "though", "unless", "until", "whether",
        "whereas", "once", "where", "why", "how",
        # Determiners and pronouns. A possessive opens a noun phrase rather than
        # continuing a stack, so `keeps its shipped severity` is not a 4-word stack.
        "its", "their", "his", "her", "our", "your", "my", "this", "these", "those", "it", "they", "them", "we", "us", "you", "he", "she",
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
        "stays", "stay", "sits", "sit",
        # Found while fixing the participle-head false positive: each of these ends
        # a clause the same way, carries no noun suffix, and nothing else separated
        # it. `A failing document opens expanded` counted 4.
        "opens", "open", "starts", "start", "appears", "appear", "exits", "exit",
        "fires", "fire", "loads", "load", "lands", "land", "passes", "pass",
        "fails", "fail", "ends", "end", "begins", "begin", "returns", "return",
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

# A past participle, which cannot be the HEAD of a noun stack. It can sit inside
# one attributively (`distributed cache invalidation strategy`), so this is not a
# STACK_BREAKER: a run is trimmed at the tail instead.
PARTICIPLE = re.compile(r"^[A-Za-z]{5,}ed$")

# The `-ed` words that are ordinary nouns, which PARTICIPLE would otherwise trim
# out of a real stack. Kept short on purpose: the pattern needs five letters, so
# `bed`, `red`, and `led` never reach it.
PARTICIPLE_NOUNS = frozenset(
    {"speed", "breed", "creed", "steed", "tweed", "thread", "spread", "bread",
     "ahead", "embed", "shred", "sacred", "hundred"}
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
    Adjacency alone counts far too much: on this project's own README it produced
    73 findings, mostly runs of verbs, adjectives, and adverbs. The suffix anchor
    took those to 0 and still reported
    `container orchestration platform migration strategy`.

    Under-reports on purpose. A stack of short Germanic nouns carries no suffix
    signal, so `disk cache size limit` is missed. A missed finding on a rule that
    ships advisory outside strict is the cheaper error here; a wall of false
    positives teaches people to disable the category.
    """
    longest = 0
    run: list[str] = []

    def close(longest: int) -> int:
        # A stack is named by its head, and a past participle cannot be one. Trimming
        # the tail rather than breaking the run keeps the attributive use, where the
        # participle sits inside a real stack: `distributed cache invalidation
        # strategy` still counts 4. Measured on this project's own README:
        # `A failing document opens expanded` counted 4 with no noun stack in it.
        trimmed = list(run)
        while (
            trimmed
            and PARTICIPLE.match(trimmed[-1])
            and trimmed[-1].lower() not in PARTICIPLE_NOUNS
        ):
            trimmed.pop()
        if len(trimmed) > longest and any(NOUN_SUFFIX.match(w) for w in trimmed):
            return len(trimmed)
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
