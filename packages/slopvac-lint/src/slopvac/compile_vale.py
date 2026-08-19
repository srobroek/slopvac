r"""Compile our YAML ruleset into a Vale style directory and a `.vale.ini`.

Vale is the execution engine. Every mechanical rule this project ships is
emitted as a Vale rule, because Vale already owns the four things a prose linter
needs: regex matching, a part-of-speech tagger, syntax-aware parsing that skips
identifiers and string literals, and a scripting extension point that sees the
whole document. What stays in Python is what Vale has no opinion about --
scoring, config layering, tiers, and the suppression contract.

THE ID MAPPING IS THE IDENTITY. A Vale rule name is its `.yml` filename and a
Vale finding's `Check` is `<style>.<RuleName>`, so writing rule `<id>.yml` into
style directory `<category>/` makes Vale's `Check` equal our `qualified_id`
character for character. Verified: `prose-inflation.slop-lexicon` round-trips,
hyphens and all. No translation table exists, therefore none can drift.

CONFIG LAYERING REACHES VALE THROUGH THE GENERATED INI, and only there. Vale
layers nothing itself: it has one config file and a rule line binds to the
section above it. So the compiler resolves severity through
`Engine.severity_for` -- the same precedence chain the native path uses -- and
writes the answer as a literal level per rule. A rule that resolves to `off` is
omitted from the ini entirely rather than written as `= NO`, because the ini is
generated per resolved config and an absent line cannot be misread.

WHY A RULE STILL STAYS NATIVE. Three reasons, each measured against vale 3.15.2
rather than assumed:

  1. The pattern is not RE2. Go's regexp rejects `\U`-escaped code points, which
     is what both emoji rules use. Detected by handing the pattern to Vale and
     reading E201, not by pattern-matching the pattern -- Vale's own compiler is
     the only authority on what Vale accepts. RE2's documented lack of
     lookbehind and backreferences turned out NOT to apply to Vale: `(?<=the )`
     and `\b(\w+) \1\b` both compile and fire, because Vale rewrites patterns
     through a wrapper before RE2 sees them.
  2. The metric has no Vale expression. Measured per metric; see METRIC_PLANS.
  3. The rule is `kind: judgement`, which never executes anywhere.

ONE BAD RULE FAILS THE WHOLE RUN, WHICH IS WHY ROUTING IS CONSERVATIVE. A Vale
style directory holding a single rule with an unparseable regex makes Vale abort
with E201 and lint NOTHING -- every file reports clean and the exit code is the
one a caller reads as "checked". That is the exact failure this project exists to
prevent, so a pattern Vale will not accept is kept native instead of emitted and
hoped for.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import ResolvedConfig, Severity
from .model import Rule, RuleKind, Scope, TextType

# Our scope vocabulary to Vale's. Vale has no document scope: a whole-document
# rule is a `script` with `scope: raw`, which is the only extension point that
# sees more than one block at a time.
SCOPE_MAP = {
    Scope.PROSE: "text",
    Scope.SENTENCE: "sentence",
    Scope.PARAGRAPH: "paragraph",
    Scope.HEADING: "heading",
    Scope.RAW: "raw",
}

# Every scope Vale accepts, confirmed by firing a rule at each against a document
# holding the token in a heading, a paragraph, a table, a list, a blockquote, and
# a code span.
#
# THIS LIST EXISTS BECAUSE VALE WILL NOT VALIDATE FOR US. An unknown scope does
# not raise: the rule loads, Vale exits 0, and the file reports clean, which is
# indistinguishable from a pass. Only the *deprecated* scopes report E201.
#
# The specific near-miss this guards: `prose` is not a Vale scope, and it is the
# DEFAULT value of `scope` in our own rule model. Emitting our scope name verbatim
# would silently disable every rule that never sets one -- the majority -- while
# every fixture reported clean. That is the exact failure mode this project exists
# to prevent, so SCOPE_MAP's output is asserted against this list rather than
# trusted.
VALE_SCOPES = frozenset(
    {
        "text", "summary", "heading", "table", "table.header", "table.cell",
        "list", "paragraph", "sentence", "raw", "alt",
    }
    | {f"heading.h{level}" for level in range(1, 7)}
)


def validate_scope(scope: str) -> str:
    """Return `scope` if Vale accepts it, else raise.

    Loud on the way out is the point: a silently-disabled rule is the one defect a
    linter must never have.
    """
    if scope not in VALE_SCOPES:
        raise ValueError(
            f"{scope!r} is not a Vale scope. Vale accepts it silently and the "
            f"rule then never fires. Valid: {', '.join(sorted(VALE_SCOPES))}"
        )
    return scope


# Penn Treebank tags per our Pos, for the vocabulary `sequence` rules. Vale's
# tagger emits Penn tags, so this is the join between our dictionary and its
# part-of-speech evidence.
PENN_TAGS = {
    "noun": "NN|NNS|NNP|NNPS",
    "verb": "VB|VBD|VBG|VBN|VBP|VBZ",
    "adjective": "JJ|JJR|JJS",
    "adverb": "RB|RBR|RBS",
}

# The ASD-STE100 8.4-8.7 word token, as ONE ordered alternation. Regex
# alternation is greedy left to right, so an earlier branch consumes its span
# before a later branch can split it: the quoted-span branch takes a whole
# quotation as one token, and the number+unit branch takes "30 s" as one.
# BRANCH ORDER IS THE ALGORITHM. Reordering this silently changes the arithmetic.
#
# The unit list is CLOSED, and that is not fussiness. An open unit branch
# (`[A-Za-z]{1,6}` after a number) reads any short word as a unit, so
# "13 thru 16" collapsed "thru" into "13" and the specification's own worked
# example measured 8 instead of 10. Under-counting is the dangerous direction: it
# lets an over-long sentence pass the cap silently.
#
# Agreement with `analyze.count_words` is 17/17 on the oracle corpus, including
# the specification's worked example. `test_compile_vale.py` re-proves that by
# execution, which is what stops this regex drifting from the contract in
# `docs/metrics.md`.
STE_WORD_TOKEN = (
    r'"[^"]+"'
    r"|“[^”]+”"
    r"|\([^)]+\)"
    r"|[+-]?\d+(?:[.,]\d+)*\s*(?:"
    r"°[CF]?|%|ms|us|ns|ps|min|mins|hrs?|days?|wks?|yrs?"
    r"|KiB|MiB|GiB|TiB|PiB|kB|MB|GB|TB|PB|px|em|rem|pt|dpi|rpm"
    r"|deg[CF]?|mm|cm|km|kg|mg|lbs?|oz|mL|gal"
    r"|[numkKMGTP]?(?:m|g|s|A|V|W|J|N|Pa|Hz|B)"
    r")\b"
    r"|--?[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*"
    r"|[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+"
    r"|[A-Za-z]+\d[A-Za-z0-9]*(?:\.[A-Za-z0-9]+)*"
    r"|\d+[A-Za-z]+[A-Za-z0-9]*"
    r"|[+-]?\d+(?:[.,]\d+)*"
    r"|[A-Z]{2,}s?"
    r"|[A-Za-z]+(?:\.[A-Za-z]+)+"
    r"|[A-Za-z]+(?:'[A-Za-z]+)?"
)

# A sentence terminator, for counting sentences per paragraph (STE 6.6).
SENTENCE_TERMINATOR = r"[.!?](?:\s|$)"

# A clause join, for the run-on metric. Same alternation the native engine used.
CLAUSE_JOIN_TOKEN = (
    r";"
    r"|\s+(?:--|—|–)\s+"
    r"|,\s*(?:and|but|or|so|yet|then|while|whereas|although)\s+"
    r"|,\s*which\b"
    r"|,\s*(?:however|therefore|meanwhile|nevertheless|consequently)\b"
)


@dataclass
class NativeRule:
    """A rule the compiler refused to hand to Vale, and the reason a reader needs.

    The reason is a sentence, not a code, because it is printed by
    `slopvac compile` and `--explain-config` and read by somebody deciding
    whether the routing is a bug.
    """

    rule_id: str
    kind: str
    reason: str


@dataclass
class CompileResult:
    """What went where. `slopvac compile` prints this as the routing table."""

    outdir: Path
    config_path: Path
    vale_rules: list[str] = field(default_factory=list)
    native_rules: list[NativeRule] = field(default_factory=list)
    judgement_rules: list[str] = field(default_factory=list)
    disabled_rules: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # A generated rule's Vale check mapped to the ruleset rule that owns it. The
    # vocabulary rules are one YAML rule compiled into four Vale rules (one per
    # part of speech), so a finding has to be attributed back or it would carry a
    # rule id that `slopvac explain` cannot resolve.
    aliases: dict[str, str] = field(default_factory=dict)
    # Cache trees this run deleted. Not persisted in the manifest: it describes the
    # run, not the tree, and a cache hit prunes nothing.
    pruned: list[Path] = field(default_factory=list)

    @property
    def vale_count(self) -> int:
        return len(self.vale_rules)

    @property
    def native_count(self) -> int:
        return len(self.native_rules)

    def native_reasons(self) -> dict[str, str]:
        return {n.rule_id: n.reason for n in self.native_rules}


# --- metric plans -------------------------------------------------------------
#
# Each entry says how one metric name reaches Vale. `occurrence` is a counted
# token against a bound; `script` is Tengo over the whole document. A metric
# absent from this table stays native, and `MISSING_METRIC_REASON` says so.
#
# `min` versus `max` is the comparison: Vale's `occurrence` fires above `max` or
# below `min`, which covers our gt/gte and lt/lte respectively.
#
# TRAP, and it cost an hour: `max: 0` is indistinguishable from unset in Vale and
# the rule silently never fires. `_occurrence_bound` raises rather than emit one.

METRIC_TOKENS = {
    "sentence_words": STE_WORD_TOKEN,
    "paragraph_words": STE_WORD_TOKEN,
    "paragraph_sentences": SENTENCE_TERMINATOR,
    "clause_boundaries": CLAUSE_JOIN_TOKEN,
}

MISSING_METRIC_REASON = (
    "metric '{metric}' is beyond Vale's occurrence counter and Tengo"
)

# A metric that only applies to one KIND of sentence cannot go to Vale, however
# countable the metric itself is.
#
# `occurrence` counts a sentence's words perfectly well. What it cannot do is ask
# `classify_text_type` whether this sentence is an instruction or an explanation, so
# a compiled `text_type: procedural` rule applies its 20-word cap to EVERY sentence.
# Measured: on `design-doc-outbox.md` line 16, a 35-word descriptive sentence drew
# both `sentence-too-long-descriptive` (native, cap 25, correct) and
# `sentence-too-long-procedural` (Vale, cap 20, wrong) -- two findings on one
# sentence for mutually exclusive reasons, telling the author to cut to 20 words for
# being an instruction it is not. Across the 8-document corpus this rule alone was
# 80 findings on 8 of 8 documents, the largest single contributor to the
# all-profiles 0.0 score.
# Metrics whose native evaluation branches on `Sentence.text_type`. Held back from
# Vale for the reason in TEXT_TYPE_REASON.
TEXT_TYPE_AWARE_METRICS = frozenset({"sentence_words"})

# Metrics whose count Vale reports differently from `count_words`, held back for a
# reason unrelated to text type: `STE_WORD_TOKEN` reproduces STE word counting over
# PROSE, but an inline code span is one word to `count_words` and zero to Vale, whose
# markdown scoping drops the span before the token counter sees it. Measured on this
# project's own README, paragraph line 37: Vale 8 words against `count_words` 10.
#
# Scoped to `paragraph_words` and deliberately NOT to `sentence_words`. The
# sentence-scoped rules were moved to Vale on a measured finding that one ordered
# alternation reproduces the count, and the tests carry that finding; a code span
# shifts a paragraph across the 8-word bound far more readily than it shifts a
# sentence across 20 or 25, and widening this set on reasoning alone would reverse a
# tested decision without evidence for it. If a sentence-scoped disagreement is ever
# measured, that is the point to widen it.
WORD_COUNTING_METRICS = frozenset({"paragraph_words"})

WORD_COUNT_REASON = (
    "Vale counts an inline code span as zero words, ASD-STE100 8.4-8.7 as one"
)

TEXT_TYPE_REASON = (
    "Vale cannot tell an instruction from an explanation (text_type={text_type})"
)


def _occurrence_bound(rule: Rule) -> tuple[str, int]:
    """Which Vale bound this rule's comparison means, as (`max`|`min`, value).

    Vale counts token matches per scope and fires above `max` or below `min`, so
    a gt/gte rule is a `max` and an lt/lte rule is a `min`. The off-by-one is
    Vale's: `max: n` fires at n+1, so `gte n` is `max: n-1`.

    Raises on a bound of 0, which Vale treats as unset -- the rule would load,
    resolve, report nothing, and read exactly like a clean document.
    """
    threshold = int(rule.threshold or 0)
    if rule.comparison == "gt":
        bound, value = "max", threshold
    elif rule.comparison == "gte":
        bound, value = "max", threshold - 1
    elif rule.comparison == "lt":
        bound, value = "min", threshold
    else:  # lte
        bound, value = "min", threshold + 1
    if value <= 0:
        raise ValueError(
            f"{rule.qualified_id}: a Vale occurrence bound of {value} is treated "
            f"as unset and the rule would never fire"
        )
    return bound, value


# --- Tengo scripts ------------------------------------------------------------
#
# One script per document-scope metric. Every one is validated by execution
# against a positive and a negative fixture in `test_compile_vale.py`, for the
# same reason `rules.py` validates every regex against its own examples: a script
# that compiles but never matches reports every file clean.
#
# TENGO CONSTRAINTS, each one found the hard way:
#   - `scope` is the injected document text. Redeclaring it is a compile error
#     that Vale reports as E201.
#   - `matches` is the output. Each entry is `{begin: <byte offset>, end: ...}`.
#   - `text.re_find(pattern, s, -1)` returns `undefined` for no match, never an
#     empty array, so every call needs the `!= undefined` guard.
#   - AN OPTIONAL CAPTURING GROUP CRASHES VALE. `(\w+ly\s+)?` in a Tengo
#     `re_find` panics the process with "slice bounds out of range [:-1]" and
#     prints a Go stack trace. Non-capturing `(?:...)?` is fine. Every optional
#     group below is non-capturing for that reason.
#   - Tengo has integer division only, so a ratio is scaled (x100, x1000)
#     rather than expressed as a float.

def _ratio_script(pattern: str, scale: int, bound: int, min_words: int = 40) -> str:
    """A `count(pattern) / count(words) * scale > bound` script.

    Built by concatenation rather than `str.format`, because Tengo's block braces
    collide with format placeholders and every brace would need doubling -- which
    is how the first version of this raised KeyError on its own script body.

    `min_words` is a floor, not a tuning knob: a ratio over a handful of words is
    noise, and firing a density rule on a two-line file trains a reader to
    disable it.
    """
    literal = json.dumps(pattern)  # Tengo string literal, escapes included
    return (
        'text := import("text")\n'
        "matches := []\n"
        'words := text.re_find("[A-Za-z]+", scope, -1)\n'
        "nwords := 0\n"
        "if words != undefined { nwords = len(words) }\n"
        f"hits := text.re_find({literal}, scope, -1)\n"
        "nhits := 0\n"
        "if hits != undefined { nhits = len(hits) }\n"
        f"if nwords >= {min_words} && (nhits * {scale}) / nwords > {bound} "
        "{\n  matches = append(matches, {begin: 0, end: 1})\n}\n"
    )

_HEADING_HIERARCHY_SCRIPT = """\
text := import("text")
matches := []
prev := 0
lines := text.split(scope, "\\n")
offset := 0
for line in lines {
  m := text.re_find("^(#+)[ ]", line, 1)
  if m != undefined {
    lvl := len(m[0][1].text)
    if prev > 0 && lvl > prev + 1 {
      matches = append(matches, {begin: offset, end: offset + len(line)})
    }
    prev = lvl
  }
  offset = offset + len(line) + 1
}
"""

_SYLLABLE_SCRIPT = """\
text := import("text")
matches := []
words := text.re_find("[A-Za-z]+", scope, -1)
if words != undefined && len(words) >= 20 {
  total := 0
  for grp in words {
    v := text.re_find("[aeiouyAEIOUY]+", grp[0].text, -1)
    n := 1
    if v != undefined { n = len(v) }
    total = total + n
  }
  if (total * 100) / len(words) > 200 {
    matches = append(matches, {begin: 0, end: 1})
  }
}
"""

# Per-metric token class and scale for the ratio scripts. The bound comes from
# the rule's own threshold, scaled to the script's integer arithmetic.
_RATIO_METRICS: dict[str, tuple[str, int]] = {
    "hedge_per_100_words": (
        r"(?i)\b(?:may|might|could|possibly|potentially|somewhat|relatively"
        r"|arguably|generally|typically|often|usually|sometimes|perhaps|likely"
        r"|seems|appears|tends to|suggests)\b",
        100,
    ),
    "abstraction_density": (
        r"(?i)\b\w{4,}(?:tion|sion|ment|ness|ity|ance|ence|ism|ology)\b",
        100,
    ),
}

# Ratio metrics held back from the Tengo path because their message must state the
# measured density and no Vale extension point can supply it.
#
# The ratio script decides a comparison and returns a match, so `_message` strips
# `{match}` to nothing rather than emit a Go format error. That is correct for a
# rule whose wording survives without the number. It is wrong for these two, whose
# entire message IS the number: `bold spray: bold spans per 1000 words` tells a
# reader nothing they can act on, which the project's own actionability rule
# forbids. Both now have a native branch that carries the count.
#
# Keep this in step with NATIVE_METRICS. A metric here with no native branch is
# reported as UNCHECKED, which is loud, but it is still a rule that stopped firing.
DENSITY_MESSAGE_METRICS = frozenset(
    {"dash_per_1000_words", "bold_spans_per_1000_words"}
)

DENSITY_MESSAGE_REASON = (
    "the message quotes the measured '{metric}', and a Vale script returns a match, "
    "not a number"
)


def _script_for(rule: Rule) -> str | None:
    """The Tengo body for a document-scope rule, with its threshold folded in.

    A ratio script multiplies before dividing, so the threshold is scaled the same
    way the script is or the comparison lands three orders of magnitude off.
    """
    if rule.kind is RuleKind.STRUCTURE:
        if rule.id in ("heading-hierarchy", "heading-level-skip"):
            return _HEADING_HIERARCHY_SCRIPT
        return None

    metric = rule.metric or ""
    if metric == "syllables_per_word":
        return _SYLLABLE_SCRIPT
    plan = _RATIO_METRICS.get(metric)
    if plan is None:
        return None
    pattern, scale = plan
    # A per-100 threshold of 3.0 becomes 3; a per-1000 of 6.0 becomes 6. The rule
    # states the threshold in the metric's own units, which already match `scale`.
    return _ratio_script(pattern, scale, int(rule.threshold or 0))


# --- Vale payload construction ------------------------------------------------

# Placeholders our messages use for a COUNT rather than a matched string. Both
# spellings occur in the shipped ruleset.
_COUNT_PLACEHOLDERS = ("{match}", "{value}")


# Placeholders no Vale extension point can supply. They come from the native
# vocabulary path (which part of speech was found, which are listed) and from
# structure rules that compare two spans. Replaced with literal wording rather
# than a format verb, because an unfilled `%s` renders as `%!s(MISSING)`.
_UNSUPPLIED_PLACEHOLDERS = {
    "{lemma}": "the word",
    "{allowed_pos}": "its listed part of speech",
    "{found_pos}": "this part of speech",
    "{detail}": "the rule",
    "{other}": "the other wording",
}


def _message(rule: Rule) -> str:
    """Our message template in Vale's printf form.

    Vale passes the matched text for `existence`, and for `substitution` passes
    the REPLACEMENT FIRST and the match second -- verified by execution, and the
    reverse of what the field order suggests.

    `occurrence` interpolates ONE INTEGER, so a count placeholder becomes `%d`:
    `%s` renders it as `%!s(int=26)`, a finding whose message is a Go format
    error rather than a sentence.

    `script` interpolates NOTHING. Its `matches` entries carry byte offsets only,
    so any verb in a script message is fed the matched text -- `%d` came out as
    `%!d(string=#### Four)`. Script messages therefore carry no verb at all and
    state the threshold literally.
    """
    text = rule.message
    for placeholder, literal in _UNSUPPLIED_PLACEHOLDERS.items():
        text = text.replace(placeholder, literal)

    threshold = str(int(rule.threshold or 0))

    if rule.kind is RuleKind.SUBSTITUTION:
        # Vale supplies (replacement, match) in that order and fills `%s` left to
        # right, so a template naming both is only correct when `{replacement}`
        # comes first. When our wording puts `{match}` first, drop to the
        # single-argument form -- naming the fix is the point of a substitution
        # message, and a swapped pair prints the two backwards.
        if "{match}" in text and "{replacement}" in text:
            if text.index("{replacement}") < text.index("{match}"):
                return text.replace("{replacement}", "%s").replace("{match}", "%s")
            return text.replace("{match}", "the match").replace("{replacement}", "%s")
        return text.replace("{match}", "%s").replace("{replacement}", "%s")

    if rule.kind is RuleKind.METRIC or rule.kind is RuleKind.STRUCTURE:
        text = text.replace("{replacement}", threshold)
        if _script_for(rule) is not None:
            # A script rule: no argument is supplied. Drop the placeholder and the
            # filler around it rather than substituting a word, because the
            # placeholder stands for different things across these rules (a count
            # in a density rule, the offending heading in the hierarchy rule) and
            # one replacement cannot read correctly in both.
            for placeholder in _COUNT_PLACEHOLDERS:
                text = text.replace(f"{placeholder} ", "").replace(placeholder, "")
            return " ".join(text.split())
        for placeholder in _COUNT_PLACEHOLDERS:
            text = text.replace(placeholder, "%d")
        return text

    return text.replace("{match}", "%s").replace("{replacement}", "%s")


def _needs_existence_fallback(substitutions: dict[str, str]) -> bool:
    """Whether a substitution rule has a key Vale's `substitution` cannot match.

    Vale wraps every swap key in `\\b...\\b`. A key ending in a non-word
    character therefore can never match: `\\be\\.g\\.\\b` requires a word
    boundary after the final period, and there is none. Measured -- `e\\.g\\.`
    reports nothing as a substitution and fires correctly as an `existence`.

    Such a rule is emitted as `existence` instead, which costs the replacement in
    the message and keeps the finding.
    """
    return any(not key[-1:].isalnum() and key[-1:] not in ")]}" for key in substitutions)


def _payload_for(rule: Rule, level: str) -> dict | None:
    """One Vale rule as a dict, or None when no extension point fits."""
    scope = validate_scope(SCOPE_MAP.get(rule.scope, "text"))

    if rule.kind is RuleKind.TOKENS and rule.tokens:
        payload = {
            "extends": "existence",
            "message": _message(rule),
            "level": level,
            "scope": scope,
            "ignorecase": rule.ignore_case,
            "tokens": list(rule.tokens),
        }
    elif rule.kind is RuleKind.PATTERN and rule.pattern:
        payload = {
            "extends": "existence",
            "message": _message(rule),
            "level": level,
            "scope": scope,
            "ignorecase": rule.ignore_case,
            "raw": [rule.pattern],
        }
    elif rule.kind is RuleKind.SUBSTITUTION and rule.substitutions:
        if _needs_existence_fallback(rule.substitutions):
            # Keep the finding, lose the named replacement. An alternation over
            # the keys is what `existence` needs, longest first so the widest key
            # wins the span.
            keys = sorted(rule.substitutions, key=len, reverse=True)
            # `existence` supplies ONE argument (the match), so a two-verb message
            # would render the second as `%!s(MISSING)`. Drop the replacement verb
            # and keep the match, which is the argument Vale actually passes.
            text = _message(rule)
            if text.count("%s") > 1:
                head, _, tail = text.partition("%s")
                text = head + "a simpler word" + tail
            # BOUNDARIES MUST BE RESTORED BY HAND. Vale's `substitution` wraps each
            # key in `\b...\b`; a bare alternation has no such wrapper, so `e.g.`
            # -- whose dots are unescaped regex -- matched "ice" inside "service".
            # A leading boundary plus a non-word-character trailing guard keeps a
            # key that legitimately ends in punctuation working.
            alternation = "|".join(f"(?:{k})" for k in keys)
            payload = {
                "extends": "existence",
                "message": text,
                "level": level,
                "scope": scope,
                "ignorecase": rule.ignore_case,
                # A lookbehind, not a consuming character class, so the reported
                # span is the match itself rather than the character before it.
                # Vale accepts lookbehind -- verified, despite RE2's documented
                # lack of it, because Vale rewrites the pattern before RE2 sees it.
                "raw": [rf"(?<![\w-])(?:{alternation})(?![\w-])"],
            }
        else:
            payload = {
                "extends": "substitution",
                "message": _message(rule),
                "level": level,
                "ignorecase": rule.ignore_case,
                "swap": dict(rule.substitutions),
            }
    elif rule.kind is RuleKind.METRIC:
        # Checked BEFORE the token lookup: a text-type-scoped metric must stay
        # native even when its metric is one Vale counts happily. See
        # TEXT_TYPE_REASON -- compiling it applied one text type's cap to every
        # sentence and double-reported the ones the native engine already had right.
        #
        # Restricted to the metrics whose NATIVE branch actually reads `text_type`.
        # A first attempt guarded on `text_type` alone and pulled three more rules
        # out of Vale for nothing: `paragraph_sentences` and the other block metrics
        # declare a `text_type` that `_run_metric` never consults, so Vale and the
        # native engine already agreed. Keep the two lists in step -- if a metric
        # starts honouring `text_type` natively, it belongs here too.
        if rule.metric in TEXT_TYPE_AWARE_METRICS and rule.text_type is not TextType.ANY:
            raise ValueError(TEXT_TYPE_REASON.format(text_type=rule.text_type.value))
        if rule.metric in DENSITY_MESSAGE_METRICS:
            raise ValueError(DENSITY_MESSAGE_REASON.format(metric=rule.metric))
        # Unconditional, unlike the check above: the word definition applies to every
        # word-counting metric regardless of how the rule is scoped.
        if rule.metric in WORD_COUNTING_METRICS:
            raise ValueError(WORD_COUNT_REASON)
        token = METRIC_TOKENS.get(rule.metric or "")
        if token is not None:
            bound, value = _occurrence_bound(rule)
            payload = {
                "extends": "occurrence",
                "message": _message(rule),
                "level": level,
                "scope": scope,
                bound: value,
                "token": token,
            }
        else:
            script = _script_for(rule)
            if script is None:
                return None
            payload = {
                "extends": "script",
                "message": _message(rule),
                "level": level,
                "scope": "raw",
                "script": script,
            }
    elif rule.kind is RuleKind.STRUCTURE:
        script = _script_for(rule)
        if script is None:
            return None
        payload = {
            "extends": "script",
            "message": _message(rule),
            "level": level,
            "scope": "raw",
            "script": script,
        }
    else:
        return None

    # Vale's `exceptions` is a list of literals that never fire. Our allowlist is
    # the same idea, and both `existence` and `substitution` support it.
    if rule.allowlist and payload["extends"] in ("existence", "substitution"):
        payload["exceptions"] = list(rule.allowlist)
    return payload


# --- RE2 acceptance -----------------------------------------------------------


class ValeUnavailable(Exception):
    """Vale is needed to validate a compiled rule and is not usable."""


def _probe_payloads(payloads: dict[str, dict], binary: str) -> dict[str, str]:
    """Which payloads Vale refuses, mapped to the reason it gave.

    Vale's own compiler is the authority on what Vale accepts, so each payload is
    handed to it rather than inspected for constructs a table thinks are
    unsupported. That inspection was wrong twice: RE2's documented lack of
    lookbehind does not apply, because Vale rewrites the pattern before RE2 sees
    it, and `(?<=the )gizmo` fires.

    One rule at a time, because a style directory holding one bad rule makes Vale
    abort the whole run -- so a batch probe reports every rule as broken.
    """
    rejected: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="slopvac-probe-") as temp:
        root = Path(temp)
        style = root / "styles" / "probe"
        style.mkdir(parents=True)
        (root / ".vale.ini").write_text(
            "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = probe\n",
            encoding="utf-8",
        )
        target = root / "probe.md"
        target.write_text("Probe text for rule validation.\n", encoding="utf-8")

        for rule_id, payload in payloads.items():
            for stale in style.iterdir():
                stale.unlink()
            (style / "R.yml").write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=10**6),
                encoding="utf-8",
            )
            try:
                completed = subprocess.run(
                    [binary, f"--config={root / '.vale.ini'}", "--no-exit", str(target)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValeUnavailable(str(exc)) from exc
            output = completed.stdout + completed.stderr
            if "E201" in output or "error parsing regexp" in output:
                reason = "Vale rejected the pattern"
                for line in output.splitlines():
                    if "error parsing regexp" in line:
                        reason = line.strip()
                        break
                rejected[rule_id] = reason
    return rejected


# --- vocabulary ---------------------------------------------------------------


def vocabulary_sequence_rules(
    vocabulary,
    level: str = "warning",
    limit: int | None = None,
    owner: str = "ste-words.word-used-in-wrong-part-of-speech",
) -> dict[str, dict]:
    """Vale `sequence` rules for the project's word blocklist.

    GROUPED BY PART OF SPEECH, not one rule per word: a rule file per word would
    be unreadable and slow, while one rule per part of speech is at most four
    files whose pattern is an alternation. That holds whether the blocklist has
    eleven entries or eleven hundred.

    Vale's tagger is what makes the grouping sound. It emits Penn Treebank tags, so
    a blocklist entry scoped to `verb` flags `close` as a verb and leaves "close to
    the limit" alone -- verified by execution. A hand-rolled tagger lived here once
    and returned UNKNOWN whenever the evidence was thin, which on real prose was
    most of the time.
    """
    from .vocabulary import Pos

    grouped: dict[Pos, list[str]] = {}
    for entry in vocabulary.blocked():
        if entry.pos.value not in PENN_TAGS:
            continue
        # A non-alphabetic or two-letter entry cannot be tagged reliably and
        # would widen the alternation for no gain.
        if not entry.word.isalpha() or len(entry.word) < 3:
            continue
        grouped.setdefault(entry.pos, []).append(entry.word)

    payloads: dict[str, dict] = {}
    for pos, words in grouped.items():
        selected = sorted(set(words))
        if limit is not None:
            selected = selected[:limit]
        if not selected:
            continue
        alternation = "|".join(selected)
        # Named after the OWNING rule plus the part of speech, so a finding maps
        # back to a real rule id in our ruleset rather than to an invented one.
        owner_name = owner.split(".", 1)[1]
        # "an adjective", not "a adjective". Two of the eight parts of speech start
        # with a vowel, so the article has to be chosen rather than hardcoded.
        article = "an" if pos.value[0] in "aeiou" else "a"
        payloads[f"{owner_name}--{pos.value}"] = {
            "extends": "sequence",
            "message": f"'%s' is on this project's blocklist as {article} {pos.value}",
            "level": level,
            "ignorecase": True,
            "tokens": [{"pattern": f"(?:{alternation})", "tag": PENN_TAGS[pos.value]}],
        }
    return payloads


# STE 1.1 is the clause the dictionary actually answers: whether the word is in
# the controlled vocabulary as used. Preferred as the owner when present.
_VOCABULARY_OWNER_PREFERENCE = (
    "ste-words.word-outside-controlled-vocabulary",
    "ste-words.word-used-in-wrong-part-of-speech",
)


def _elect_vocabulary_owner(
    owners: list[Rule], result: CompileResult
) -> list[Rule]:
    """Keep one dictionary-backed rule; route the rest native with the reason.

    Every `kind: vocabulary` rule would compile to the same sweep over the same
    wordlist, so emitting all of them reports one word four times. The others are
    not dropped: they are reported as native, which is honest -- their distinctions
    (which FORM of a listed verb, which part of speech was expected) need evidence
    the flat dictionary does not carry.
    """
    if len(owners) <= 1:
        return owners

    by_id = {rule.qualified_id: rule for rule in owners}
    chosen = next(
        (by_id[rule_id] for rule_id in _VOCABULARY_OWNER_PREFERENCE if rule_id in by_id),
        owners[0],
    )
    for rule in owners:
        if rule is chosen:
            continue
        result.native_rules.append(
            NativeRule(
                rule.qualified_id,
                rule.kind.value,
                f"the vocabulary sweep is compiled once, under "
                f"{chosen.qualified_id}",
            )
        )
    return [chosen]


# --- cache --------------------------------------------------------------------


def _compiler_source_digest() -> str:
    """Hash this module's own source, for the cache key.

    Read from `__file__` rather than tracked as a hand-bumped version constant,
    because a constant only invalidates when someone REMEMBERS to bump it, and the
    failure it guards against is silent. Falls back to the package version if the
    source is unreadable (a zipimport or a frozen build), which is weaker but never
    worse than the input-only key it replaces.
    """
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    except OSError:
        from . import __version__

        return f"v{__version__}"


_COMPILER_SOURCE_DIGEST = _compiler_source_digest()


def cache_root() -> Path:
    """Where compiled styles live.

    Overridable through `SLOPVAC_CACHE_DIR`, then `XDG_CACHE_HOME`, then the
    platform temp dir. A user-writable location matters because the compile runs
    on every lint and a read-only cache would recompile every time.
    """
    override = os.environ.get("SLOPVAC_CACHE_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "slopvac"
    return Path(tempfile.gettempdir()) / "slopvac-cache"


# How many compiled trees to keep. Each is ~400KB, so 16 is a few megabytes and
# covers the profiles and locales one project alternates between, plus a handful of
# other checkouts, without a second compile. The number that matters is not the
# disk: it is that every ruleset edit, severity change, and blocklist edit mints a
# new key, so an unpruned cache grows with development activity rather than use.
# One developer machine reached 209 trees and 83MB.
CACHE_KEEP = 16


def prune_cache(root: Path | None = None, keep: int = CACHE_KEEP) -> list[Path]:
    """Delete all but the `keep` most recently used compiled trees.

    Returns what it removed. Never raises: a cache that cannot be pruned is a
    disk-space problem, and failing a lint over one would be worse than the leak.

    Recency is the directory's own mtime, refreshed on every cache hit, so the tree
    a project keeps hitting survives no matter how long ago it was compiled. Sorted
    by name as a tiebreak, because two trees written in the same mtime granule must
    still order deterministically or the survivor set varies between runs.
    """
    root = cache_root() if root is None else root
    removed: list[Path] = []
    try:
        entries = [p for p in root.iterdir() if (p / "manifest.json").is_file()]
    except OSError:
        return removed
    if len(entries) <= keep:
        return removed

    def recency(path: Path) -> tuple[float, str]:
        try:
            return (path.stat().st_mtime, path.name)
        except OSError:
            return (0.0, path.name)

    for stale in sorted(entries, key=recency, reverse=True)[keep:]:
        try:
            shutil.rmtree(stale)
        except OSError:
            continue
        removed.append(stale)
    return removed


def _fingerprint(
    rules: list[Rule],
    config: ResolvedConfig,
    levels: dict[str, str],
    vocabulary=None,
) -> str:
    """Hash of everything that changes the output.

    Keyed on the resolved LEVELS rather than the raw config, because that is what
    reaches the ini: two configs that resolve every rule to the same severity
    produce identical output and should share a cache entry.
    """
    digest = hashlib.sha256()
    # THE COMPILER'S OWN SOURCE IS PART OF THE KEY. Rules, levels, and profile are
    # the compiler's INPUT; the generated style also depends on the code that
    # translates them, so keying on input alone serves a stale style after every
    # compiler change. This cost real debugging time: the fix that stops a
    # text-type-scoped metric from reaching Vale appeared to do NOTHING -- three
    # rescores of the whole corpus came back byte-identical, including counts that
    # had to change -- because the fingerprint was unchanged and the cached style
    # still held the rule. A silently stale cache is indistinguishable from a fix
    # that does not work, which is the more expensive failure of the two.
    digest.update(_COMPILER_SOURCE_DIGEST.encode())
    for rule in sorted(rules, key=lambda r: r.qualified_id):
        digest.update(rule.qualified_id.encode())
        digest.update(rule.model_dump_json(exclude={"category"}).encode())
    for rule_id in sorted(levels):
        digest.update(f"{rule_id}={levels[rule_id]}".encode())
    digest.update(config.profile.value.encode())
    # THE BLOCKLIST IS PART OF THE KEY TOO, and for the same reason: its words are
    # baked into the generated `sequence` rules, so adding one and re-running would
    # otherwise hit a cache entry compiled without it. The failure mode is the one
    # documented above -- an edit that appears to do nothing -- and it would land on
    # a USER editing their own wordlist rather than on us editing the compiler,
    # which makes it harder to diagnose, not easier.
    #
    # Hashed from the entries rather than the file bytes, so reformatting the file
    # or moving it between TOML and YAML does not invalidate a still-correct style.
    if vocabulary is not None:
        for entry in sorted(vocabulary.blocked(), key=lambda e: (e.word, e.pos.value)):
            digest.update(f"{entry.word}:{entry.pos.value}".encode())
    return digest.hexdigest()[:16]


# --- the compiler -------------------------------------------------------------


def compile_ruleset(
    ruleset,
    resolved_config: ResolvedConfig,
    outdir: Path | None = None,
    *,
    binary: str = "vale",
    validate: bool = True,
    vocabulary=None,
    force: bool = False,
) -> CompileResult:
    """Compile `ruleset` into a Vale style tree plus a `.vale.ini`.

    `validate` hands every payload to Vale and keeps the rejected ones native.
    Turning it off makes the compile fast and the output unverified, which is
    only correct in a test that already knows the answer.
    """
    from .engine import Engine

    engine = Engine(ruleset.rules, resolved_config)
    active = {r.qualified_id for r in engine.rules}

    levels: dict[str, str] = {}
    for rule in ruleset.rules:
        if rule.qualified_id not in active:
            continue
        severity = engine.severity_for(rule)
        if severity is Severity.OFF:
            continue
        levels[rule.qualified_id] = severity.value

    fingerprint = _fingerprint(ruleset.rules, resolved_config, levels, vocabulary)
    cached_here = outdir is None
    if outdir is None:
        if not validate:
            # AN UNVALIDATED TREE MUST NEVER REACH THE SHARED CACHE. Without the
            # probe, every payload is written, including the ones Vale refuses to
            # compile. A later run whose config fingerprints the same way finds the
            # manifest, trusts it, and hands Vale a style directory holding an
            # unloadable rule -- the E201 failure in the module docstring.
            #
            # That is not hypothetical: it is how this project's own README came to
            # report 90.7 and 91.5 when the real figure was 82.6. The entry was
            # written by the test suite, which compiles unvalidated on purpose and
            # used to inherit the developer's real cache directory.
            raise ValueError(
                "an unvalidated compile cannot be cached: pass an explicit outdir, "
                "because a tree that was never probed may contain a rule Vale "
                "refuses to load, and one such rule makes Vale lint nothing at all"
            )
        outdir = cache_root() / fingerprint
    outdir = Path(outdir)
    manifest_path = outdir / "manifest.json"

    if not force and manifest_path.is_file():
        try:
            cached = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = None
        if cached and cached.get("fingerprint") == fingerprint:
            # Mark the hit, so pruning keeps what is in use rather than what was
            # compiled most recently. A project that alternates two profiles would
            # otherwise lose whichever it compiled first, however often it runs.
            with suppress(OSError):
                os.utime(outdir)
            return CompileResult(
                outdir=outdir,
                config_path=outdir / ".vale.ini",
                vale_rules=cached.get("vale_rules", []),
                native_rules=[NativeRule(**n) for n in cached.get("native_rules", [])],
                judgement_rules=cached.get("judgement_rules", []),
                disabled_rules=cached.get("disabled_rules", []),
                notes=cached.get("notes", []),
                aliases=cached.get("aliases", {}),
            )

    result = CompileResult(outdir=outdir, config_path=outdir / ".vale.ini")

    payloads: dict[str, dict] = {}
    categories: dict[str, str] = {}
    vocabulary_owners: list[Rule] = []

    for rule in ruleset.rules:
        if rule.kind is RuleKind.JUDGEMENT:
            result.judgement_rules.append(rule.qualified_id)
            continue
        if rule.qualified_id not in levels:
            result.disabled_rules.append(rule.qualified_id)
            continue

        level = levels[rule.qualified_id]
        try:
            payload = _payload_for(rule, level)
        except ValueError as exc:
            result.native_rules.append(
                NativeRule(rule.qualified_id, rule.kind.value, str(exc))
            )
            continue

        if payload is None:
            if rule.kind is RuleKind.VOCABULARY:
                # Compiled below, from the dictionary rather than from the rule's
                # own payload: one YAML rule becomes one Vale rule per part of
                # speech.
                vocabulary_owners.append(rule)
                continue
            reason = (
                MISSING_METRIC_REASON.format(metric=rule.metric)
                if rule.kind is RuleKind.METRIC
                else f"no Vale extension point for a {rule.kind.value} rule"
            )
            result.native_rules.append(NativeRule(rule.qualified_id, rule.kind.value, reason))
            continue

        payloads[rule.qualified_id] = payload
        categories[rule.qualified_id] = rule.category

    # A `kind: vocabulary` rule becomes one Vale `sequence` rule per part of
    # speech, keyed to the project's blocklist. With no blocklist configured there
    # is nothing to generate and nothing to check, which is the DEFAULT state, not
    # a degraded one -- see `config.VocabularySettings`.
    #
    # ONLY ONE RULE OWNS THE BLOCKLIST SWEEP. The vocabulary rules cite different
    # STE clauses (1.1 not-in-vocabulary, 1.2 wrong part of speech, 1.4 and 3.1
    # disallowed forms) but a `(word, pos)` blocklist answers exactly one question:
    # is this word refused as the part of speech it is used as. Compiling all of
    # them produced a finding each on every word. The others stay native and say
    # why, so the distinction is recorded rather than lost.
    vocabulary_owners = _elect_vocabulary_owner(vocabulary_owners, result)

    for rule in vocabulary_owners:
        if not vocabulary:
            # `not vocabulary` covers both None and empty, because they mean the
            # same thing to a reader: no word is refused, so the rule has nothing
            # to say. Distinguishing them here would report a configuration detail
            # as a rule outcome.
            result.native_rules.append(
                NativeRule(
                    rule.qualified_id,
                    rule.kind.value,
                    # No square brackets in this string: the CLI renders native
                    # reasons through rich, which reads `[vocabulary]` as a style tag
                    # and silently deletes it, so the message named no setting at all.
                    "no word blocklist, so nothing to check; set vocabulary.path "
                    "-- see examples/blocklist.toml",
                )
            )
            continue
        generated = vocabulary_sequence_rules(
            vocabulary, level=levels[rule.qualified_id], owner=rule.qualified_id
        )
        if not generated:
            result.native_rules.append(
                NativeRule(
                    rule.qualified_id,
                    rule.kind.value,
                    "the blocklist holds no entry with a taggable part of speech, "
                    "so there is nothing to compile",
                )
            )
            continue
        for name, payload in generated.items():
            check = f"{rule.category}.{name}"
            payloads[check] = payload
            categories[check] = rule.category
            levels[check] = levels[rule.qualified_id]
            result.aliases[check] = rule.qualified_id

    if validate:
        resolved_binary = shutil.which(binary)
        if resolved_binary is None:
            raise ValeUnavailable(f"`{binary}` is not on PATH")
        rejected = _probe_payloads(payloads, resolved_binary)
        for rule_id, reason in rejected.items():
            payloads.pop(rule_id, None)
            kind = "pattern"
            rule = ruleset.by_id(rule_id)
            if rule is not None:
                kind = rule.kind.value
            result.native_rules.append(
                NativeRule(
                    rule_id,
                    kind,
                    f"Vale rejected the pattern: {reason}",
                )
            )

    # Write the tree only once the routing is settled, so a rejected rule never
    # reaches disk where a later run could pick it up from the cache.
    #
    # Build in a private sibling directory and rename it into place, rather than
    # clearing `outdir` and writing into it. Two costs paid for that:
    #
    # A reader is never shown a half-built tree. Clearing first left a window --
    # ~200 rule files wide -- in which a concurrent run resolved a config whose
    # rules were partly absent, which is the E201 failure in the module docstring.
    # It cost a session's worth of trust in this project's own README score.
    #
    # And a crash leaves no cache entry at all. The manifest is the last thing
    # written, so a run killed mid-write used to leave a directory that looked
    # cached to the fingerprint check; now the manifest lands inside the temporary
    # tree and becomes visible only with the rename, which is atomic.
    staging = outdir.parent / f".{outdir.name}.building-{os.getpid()}"
    outdir.parent.mkdir(parents=True, exist_ok=True)
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "styles").mkdir(parents=True)

    for rule_id, payload in sorted(payloads.items()):
        category = categories[rule_id]
        name = rule_id.split(".", 1)[1]
        directory = staging / "styles" / category
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.yml").write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=10**6),
            encoding="utf-8",
        )
        result.vale_rules.append(rule_id)

    (staging / ".vale.ini").write_text(
        _render_ini(sorted(payloads), levels), encoding="utf-8"
    )
    (staging / "manifest.json").write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "vale_rules": result.vale_rules,
                "native_rules": [n.__dict__ for n in result.native_rules],
                "judgement_rules": result.judgement_rules,
                "disabled_rules": result.disabled_rules,
                "notes": result.notes,
                "aliases": result.aliases,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # `os.replace` is atomic for a directory only when the target does not exist,
    # so the old tree moves aside first and is removed after the swap. A loser in a
    # race finds its own rename failing because the winner already published an
    # identical tree -- the fingerprint says so -- so it keeps the winner's.
    previous = outdir.parent / f".{outdir.name}.replaced-{os.getpid()}"
    try:
        if outdir.exists():
            os.replace(outdir, previous)
        try:
            os.replace(staging, outdir)
        except OSError:
            if not (outdir / "manifest.json").is_file():
                raise
            shutil.rmtree(staging, ignore_errors=True)
    finally:
        shutil.rmtree(previous, ignore_errors=True)

    # Prune only when this run owns the shared cache. A caller who named its own
    # outdir gets no housekeeping: that directory is theirs, and deleting siblings
    # of a path the user chose would be a surprise.
    if cached_here:
        result.pruned = prune_cache(outdir.parent)
    return result


def _render_ini(rule_ids: list[str], levels: dict[str, str]) -> str:
    """The generated `.vale.ini`.

    Rules are ENUMERATED rather than enabled by `BasedOnStyles`, because a style
    directory holds every rule we compiled and a config that names each one is
    the only way an `off` rule is provably absent. `vale ls-config` then reports
    exactly this list, which is what the runner compares against to detect a rule
    that failed to resolve.
    """
    lines = [
        "# GENERATED by slopvac. Do not edit: regenerated on every run from",
        "# the resolved config, and any hand edit is overwritten.",
        "#",
        "# Severity per rule comes from slopvac's own precedence chain (rule",
        "# override > category cap > tier > shipped severity). A rule that",
        "# resolved to `off` is absent from this file entirely.",
        "",
        "StylesPath = styles",
        # Every rule carries the level we resolved for it, so the floor must admit
        # the lowest of them or Vale filters out findings we asked for.
        "MinAlertLevel = suggestion",
        "",
        "[*.{md,mdx,markdown,txt,rst,html}]",
    ]
    for rule_id in rule_ids:
        lines.append(f"{rule_id} = {levels.get(rule_id, 'warning')}")
    return "\n".join(lines) + "\n"


def resolved_checks(config_path: Path, binary: str = "vale") -> set[str] | None:
    """The rules Vale actually resolved, from `vale ls-config`.

    Used to detect the silent case the brief names: the compiler wrote N rules
    and Vale resolved fewer. Returns None when Vale cannot be asked, which the
    caller reports as unchecked rather than treating as agreement.
    """
    resolved = shutil.which(binary)
    if resolved is None:
        return None
    try:
        completed = subprocess.run(
            [resolved, f"--config={config_path}", "ls-config"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    checks = data.get("Checks")
    return set(checks) if isinstance(checks, list) else None
