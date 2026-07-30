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
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import ResolvedConfig, Severity
from .model import Rule, RuleKind, Scope

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
    `slopvac-lint compile` and `--explain-config` and read by somebody deciding
    whether the routing is a bug.
    """

    rule_id: str
    kind: str
    reason: str


@dataclass
class CompileResult:
    """What went where. `slopvac-lint compile` prints this as the routing table."""

    outdir: Path
    config_path: Path
    vale_rules: list[str] = field(default_factory=list)
    native_rules: list[NativeRule] = field(default_factory=list)
    judgement_rules: list[str] = field(default_factory=list)
    disabled_rules: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

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
    "lead_in_words": STE_WORD_TOKEN,
    "paragraph_sentences": SENTENCE_TERMINATOR,
    "clause_boundaries": CLAUSE_JOIN_TOKEN,
}

MISSING_METRIC_REASON = (
    "no Vale expression for metric '{metric}': it needs a measurement Vale's "
    "occurrence counter and Tengo scripting do not reach, so it stays native"
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
    "dash_per_1000_words": ("—", 1000),
    "bold_spans_per_1000_words": (r"\*\*[^*]+\*\*", 1000),
}


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
    scope = SCOPE_MAP.get(rule.scope, "text")

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
            payload = {
                "extends": "existence",
                "message": _message(rule).replace("%s", "%s", 1),
                "level": level,
                "scope": scope,
                "ignorecase": rule.ignore_case,
                "raw": ["|".join(f"(?:{k})" for k in keys)],
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
    vocabulary, level: str = "warning", limit: int | None = None
) -> dict[str, dict]:
    """Vale `sequence` rules for the unapproved controlled vocabulary.

    GROUPED BY PART OF SPEECH, not one rule per word. The dictionary holds ~2,000
    unapproved entries and a rule file each would be unreadable and slow; one
    rule per part of speech is four files whose pattern is an alternation.

    This is what replaces the hand-rolled tagger that used to live in
    `vocabulary.py`. That tagger resolved a part of speech from neighbouring
    tokens and returned UNKNOWN whenever the evidence was thin, which meant it
    stayed silent on most real prose. Vale's tagger emits Penn Treebank tags, so
    `close` as a verb is flagged and `close to the limit` is not -- verified by
    execution, and the reason 2,087 dictionary entries now cost four rules.
    """
    from .vocabulary import Pos

    grouped: dict[Pos, list[str]] = {}
    for (word, pos), entry in vocabulary._entries.items():
        if entry.approved:
            continue
        if pos.value not in PENN_TAGS:
            continue
        if not word.isalpha() or len(word) < 3:
            continue
        grouped.setdefault(pos, []).append(word)

    payloads: dict[str, dict] = {}
    for pos, words in grouped.items():
        selected = sorted(set(words))
        if limit is not None:
            selected = selected[:limit]
        if not selected:
            continue
        alternation = "|".join(selected)
        payloads[f"vocab-{pos.value}"] = {
            "extends": "sequence",
            "message": f"'%s' is not approved as a {pos.value}; use the approved term",
            "level": level,
            "ignorecase": True,
            "tokens": [{"pattern": f"(?:{alternation})", "tag": PENN_TAGS[pos.value]}],
        }
    return payloads


# --- cache --------------------------------------------------------------------


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


def _fingerprint(rules: list[Rule], config: ResolvedConfig, levels: dict[str, str]) -> str:
    """Hash of everything that changes the output.

    Keyed on the resolved LEVELS rather than the raw config, because that is what
    reaches the ini: two configs that resolve every rule to the same severity
    produce identical output and should share a cache entry.
    """
    digest = hashlib.sha256()
    for rule in sorted(rules, key=lambda r: r.qualified_id):
        digest.update(rule.qualified_id.encode())
        digest.update(rule.model_dump_json(exclude={"category"}).encode())
    for rule_id in sorted(levels):
        digest.update(f"{rule_id}={levels[rule_id]}".encode())
    digest.update(config.profile.value.encode())
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

    fingerprint = _fingerprint(ruleset.rules, resolved_config, levels)
    if outdir is None:
        outdir = cache_root() / fingerprint
    outdir = Path(outdir)
    manifest_path = outdir / "manifest.json"

    if not force and manifest_path.is_file():
        try:
            cached = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = None
        if cached and cached.get("fingerprint") == fingerprint:
            return CompileResult(
                outdir=outdir,
                config_path=outdir / ".vale.ini",
                vale_rules=cached.get("vale_rules", []),
                native_rules=[NativeRule(**n) for n in cached.get("native_rules", [])],
                judgement_rules=cached.get("judgement_rules", []),
                disabled_rules=cached.get("disabled_rules", []),
                notes=cached.get("notes", []),
            )

    result = CompileResult(outdir=outdir, config_path=outdir / ".vale.ini")

    payloads: dict[str, dict] = {}
    categories: dict[str, str] = {}

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
            reason = (
                MISSING_METRIC_REASON.format(metric=rule.metric)
                if rule.kind is RuleKind.METRIC
                else f"no Vale extension point expresses kind={rule.kind.value} "
                f"rule '{rule.id}'"
            )
            result.native_rules.append(NativeRule(rule.qualified_id, rule.kind.value, reason))
            continue

        payloads[rule.qualified_id] = payload
        categories[rule.qualified_id] = rule.category

    if vocabulary is not None:
        for name, payload in vocabulary_sequence_rules(vocabulary).items():
            payloads[f"ste-words.{name}"] = payload
            categories[f"ste-words.{name}"] = "ste-words"
            levels[f"ste-words.{name}"] = "warning"

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
                    f"Vale will not compile this pattern, and one unloadable rule "
                    f"aborts the whole run: {reason}",
                )
            )

    # Write the tree only once the routing is settled, so a rejected rule never
    # reaches disk where a later run could pick it up from the cache.
    if outdir.exists():
        shutil.rmtree(outdir)
    (outdir / "styles").mkdir(parents=True)

    for rule_id, payload in sorted(payloads.items()):
        category = categories[rule_id]
        name = rule_id.split(".", 1)[1]
        directory = outdir / "styles" / category
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.yml").write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=10**6),
            encoding="utf-8",
        )
        result.vale_rules.append(rule_id)

    result.config_path.write_text(_render_ini(sorted(payloads), levels), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "fingerprint": fingerprint,
                "vale_rules": result.vale_rules,
                "native_rules": [n.__dict__ for n in result.native_rules],
                "judgement_rules": result.judgement_rules,
                "disabled_rules": result.disabled_rules,
                "notes": result.notes,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
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
        "# GENERATED by slopvac-lint. Do not edit: regenerated on every run from",
        "# the resolved config, and any hand edit is overwritten.",
        "#",
        "# Severity per rule comes from slopvac-lint's own precedence chain (rule",
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
