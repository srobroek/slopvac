r"""The native execution path: what Vale cannot run, plus what Vale cannot own.

VALE IS THE EXECUTION ENGINE. `compile_vale` routes 132 of the 148 mechanical
rules to it, so this module is no longer the main checker. What remains is of two
kinds, and the second is why the lexical and metric paths still exist:

  ALWAYS OURS -- severity precedence (`severity_for`), rule selection per profile
  and config layer (`_active`), and the suppression annotation contract. Vale has
  no notion of any of them; the compiler asks THIS class what level a rule
  resolves to before it writes the ini.

  OURS ONLY BECAUSE VALE REFUSED IT -- 16 rules at the shipped profiles. Two are
  `kind: pattern` whose regex Go will not compile (`\U`-escaped emoji ranges), so
  `_run_lexical` stays for exactly those. Four are `kind: vocabulary`, five are
  metrics with no Vale expression, and five are structure rules needing
  cross-block comparison. `compile_ruleset` names each one and its reason.

The routing is not a static list: `slopvac compile` prints it, and a rule
moves here the moment Vale rejects its pattern, which is tested by execution on
every compile.

A METRIC WITH NO IMPLEMENTATION IS REPORTED, NOT SKIPPED. Nine metric names in
the shipped ruleset have no native branch, so those rules used to load, match
nothing, and report every document clean. `unimplemented_metrics` names them so
the caller can surface them as `unchecked`.

SUPPRESSION IS AN ANNOTATION CONTRACT, not a comment convention. A suppression
must name an exception from the rule's own closed list:

    <!-- slopvac-allow: rule=<qualified-id> reason=<exception-name> -->

An annotation whose reason is absent from the rule's `exceptions` is reported as
`invalid-suppression` rather than honoured. "Reads better" is deliberately not on
any list: an unnamed override collapses the ruleset, which is the failure mode
Orwell's own sixth rule has in an automated pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    coordinated_items,
    count_words,
    longest_noun_stack,
    stdev,
    syllables,
)
from .config import ResolvedConfig, Severity
from .model import Finding, Rule, RuleKind, Scope, TextType, Tier

SUPPRESSION = re.compile(
    r"<!--\s*slopvac-allow:\s*rule=(?P<rule>[\w.-]+)(?:\s+reason=(?P<reason>[\w-]+))?\s*-->"
)
DISABLE_LINE = re.compile(r"<!--\s*slopvac-disable-next-line\s*-->")
DISABLE_START = re.compile(r"<!--\s*slopvac-disable\s*-->")
DISABLE_END = re.compile(r"<!--\s*slopvac-enable\s*-->")

# STE 5.1 / 6.3 / 5.5: the cap depends on what kind of text the sentence is.
WORD_CAPS = {
    TextType.PROCEDURAL: 20,
    TextType.SAFETY: 20,
    TextType.DESCRIPTIVE: 25,
    TextType.ANY: 25,
}


@dataclass
class Suppression:
    rule: str
    reason: str | None
    line: int


# A substitution key is a REGEX, not a literal, matching Vale's `swap` semantics:
# `\bblind spots?\b`, `(?:and|or) higher`, and `\ba HTML\b` are all real keys in the
# shipped ruleset. Escaping them would make each one match only its own literal
# text and never fire -- which is how 16 rules failed their own examples.
#
# A key that carries no regex metacharacter still needs boundaries, because a bare
# word must not match inside a longer one. A key that carries its own `\b` or
# lookaround must be left alone, since wrapping it would double the boundary and
# break the match.
_HAS_OWN_BOUNDARY = re.compile(r"\\b|\\B|\(\?<|\(\?=|\(\?!|^\^|\$$")
_METACHARACTER = re.compile(r"[\\(){}\[\]|?*+^$]")


# A clause boundary is where a reader has to start holding a second idea. Counted
# rather than word-counted, because sentence length and idea count are different
# defects: "Read the file, parse it, and emit the report" is 9 words and one idea.
#
# Excluded on purpose: a comma before a restrictive clause, a comma in a list of
# nouns, and a subordinating conjunction that opens the sentence (the
# condition-before-command form the STE rules require).
_CLAUSE_JOIN = re.compile(
    r"""
      ;                                   # a semicolon always joins clauses
    | \s+(?:--|—|–)\s+                    # a dash used as a clause join
    | ,\s*(?:and|but|or|so|yet|then|while|whereas|although)\s+(?=\w+\s+\w)
    | ,\s*which\b                         # non-restrictive relative clause
    | ,\s*(?:however|therefore|meanwhile|nevertheless|consequently)\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def count_clause_boundaries(text: str) -> int:
    """How many times this sentence starts a new independent idea."""
    return len(_CLAUSE_JOIN.findall(text))


# Two capitals minimum, and at least one letter, so a single capital and an
# ordinary sentence-initial word are NOT exempt. Digits, underscores, hyphens, and
# dots ride along, which is what makes `DATABASE_URL`, `RFC 2119`, and `TLS1.3`
# count as all-caps while `Ensure` does not.
# A quotation opens at a word boundary and closes against a non-space. The
# boundary guards are load-bearing, not defensive:
#   `Set width to 30" and height to 12"` paired the two INCH marks into a span,
#   which would have silenced every finding between them.
# There is deliberately NO straight-single branch. `'` is the apostrophe, so
# "Don't use it; the team's build" parses as the quotation `'t use it; the team'`
# — a rule-silencing span in ordinary English. A single-quoted phrase is rare in
# technical prose and not worth that trade.
_QUOTED_SPAN = re.compile(
    r"""
      (?<![\w"”])  "  [^"\n]{1,200}  (?<!\s)  "  (?![\w])   # straight double
    | (?<![\w“])    “  [^”\n]{1,200}                   ”
    | (?<![\w‘])    ‘  [^’\n]{1,200}                   ’
    """,
    re.VERBOSE,
)


def _inside_quotation(text: str, start: int, end: int) -> bool:
    """Is this match wholly inside a quoted span on the same line?

    A document that BANS a phrase has to print the phrase. Without this, every
    style guide fails its own gate: `write-docs.context.md` drew 7 errors, all of
    them the phrase it was forbidding ("Experts agree", "world-class", "perform an
    analysis"). The rules already declare `quotation` in their exception lists; the
    engine simply never detected one.

    Line-scoped and length-capped on purpose. A quote mark is also an apostrophe, a
    unit of inches, and a shell quote, so an unbounded scan pairs marks that were
    never a quotation and silences half a document.
    """
    return any(
        span.start() < start and end <= span.end() - 1
        for span in _QUOTED_SPAN.finditer(text)
    )


def drop_quoted_illustrations(
    findings: list[Finding], document: Document, ruleset: Any
) -> list[Finding]:
    """Apply the `quotation` exception to findings the native engine did not raise.

    Vale never sees a rule's exception list, so without this the exception holds for
    only the half of the ruleset the native engine runs, and which half a rule lands
    in is an implementation detail no author can predict.

    A finding survives unless its own rule declares `quotation` AND its matched text
    sits inside a quoted span on its line. A finding carrying no `matched_text`
    cannot be located, so it survives.
    """
    kept: list[Finding] = []
    for finding in findings:
        rule = ruleset.by_id(finding.rule_id)
        index = finding.line - 1
        if (
            rule is not None
            and "quotation" in rule.exceptions
            and finding.matched_text
            and 0 <= index < len(document.raw_lines)
        ):
            line = document.raw_lines[index]
            start = line.find(finding.matched_text)
            if start != -1 and _inside_quotation(
                line, start, start + len(finding.matched_text)
            ):
                continue
        kept.append(finding)
    return kept


_ALL_CAPS = re.compile(r"^[^a-z]*[A-Z][^a-z]*[A-Z][^a-z]*$")


def _is_all_caps(matched: str) -> bool:
    """Is this match written entirely in capitals?

    WHY A MATCH LIKE THIS IS EXEMPT BY DEFAULT. An all-caps token in technical
    prose is nearly always one of four things, and no prose rule is about any of
    them:

      - a normative keyword    RFC 2119 MUST / SHOULD / MAY
      - an identifier          DATABASE_URL, MAX_RETRY_COUNT
      - an initialism          JSON, TLS, HTTP
      - a safety marker        WARNING, CAUTION

    Two live false positives motivated this, both found by the independent eval
    corpus rather than by a fixture: `ENSURE` drew a substitution telling the
    author to write "make sure", and `is IMPORTANT` was reported as passive voice.
    Neither is a prose defect; both are the capitals doing their job.

    A rule that IS about the capitals themselves sets `match_all_caps: true`.

    A MULTI-WORD MATCH IS EXEMPT WHEN ITS CAPITALISED WORD CARRIES THE RULE. A
    pattern often captures a neighbour for context: passive voice matched
    "is IMPORTANT" and a conjunction rule matched "ENSURE the". The capitalised
    word is the one being judged and the lowercase neighbour is only scaffolding,
    so the whole-span test is too strict. Requiring EVERY alphabetic word in the
    span to be either all-caps or a short function word keeps that exemption from
    swallowing a real sentence, which would be all-caps only if it were shouting.
    """
    if _ALL_CAPS.match(matched):
        return True
    words = re.findall(r"[A-Za-z][A-Za-z0-9_.-]*", matched)
    if not words or len(words) > 4:
        return False
    capitalised = [w for w in words if _ALL_CAPS.match(w)]
    if not capitalised:
        return False
    return all(w in _SCAFFOLD_WORDS or _ALL_CAPS.match(w) for w in words)


# Function words a pattern picks up as context around the word it judges. Short and
# closed on purpose: a longer list starts exempting real prose.
_SCAFFOLD_WORDS = frozenset(
    {
        "is", "are", "was", "were", "be", "been", "being", "am",
        "the", "a", "an", "this", "that", "these", "those",
        "and", "or", "not", "to", "of", "in", "on", "for", "with", "as", "at",
        "it", "its", "if", "then", "by", "from",
    }
)


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



def format_message(template: str, **fields: object) -> str:
    """Interpolate a rule message without dying on an unknown placeholder.

    Rule messages are DATA, written by whoever added the rule, and the vocabulary
    of placeholders drifted: some rules say `{value}` and `{limit}`, others
    `{match}` and `{replacement}`. A KeyError here kills the whole run over a
    cosmetic mismatch, so unknown placeholders are left as literal text and the
    known aliases are all supplied.
    """
    aliases = dict(fields)
    # Metric rules describe a measurement and its ceiling; lexical rules describe
    # a match and its replacement. Accept either vocabulary for both.
    if "match" in fields:
        aliases.setdefault("value", fields["match"])
        aliases.setdefault("count", fields["match"])
        aliases.setdefault("actual", fields["match"])
    if "replacement" in fields:
        aliases.setdefault("limit", fields["replacement"])
        aliases.setdefault("max", fields["replacement"])
        aliases.setdefault("threshold", fields["replacement"])

    class _Lenient(dict):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        return template.format_map(_Lenient(aliases))
    except (IndexError, ValueError):
        # A stray brace in the message text. Return it verbatim rather than
        # failing the run.
        return template


def build_substitution_pattern(substitutions: dict[str, str]) -> str:
    """One alternation over every key, longest first.

    Longest-first matters: with `in order to` and `order` both present, the shorter
    key would otherwise win and report the wrong replacement.
    """
    parts: list[str] = []
    for key in sorted(substitutions, key=len, reverse=True):
        if _HAS_OWN_BOUNDARY.search(key):
            parts.append(f"(?:{key})")
        elif _METACHARACTER.search(key):
            # Regex, but unanchored. Bound it without assuming a word edge, since
            # a key may begin or end with punctuation.
            parts.append(rf"(?<![\w-])(?:{key})(?![\w-])")
        else:
            parts.append(rf"(?<![\w-])(?:{re.escape(key)})(?![\w-])")
    return "|".join(parts)


# A trailing lookahead cannot be satisfied by the matched span alone: the key
# `\b(?:e\.g\.)(?=[\s,])` matches "e.g." inside a sentence, but re-testing it
# against the bare string "e.g." fails, because the space it looks ahead for is
# outside the span. Stripping the assertions is what makes the reverse lookup work.
_TRAILING_ASSERTION = re.compile(r"\((?:\?=|\?!|\?<=|\?<!)[^)]*\)$")
_LEADING_ASSERTION = re.compile(r"^\((?:\?=|\?!|\?<=|\?<!)[^)]*\)")


def match_substitution(substitutions: dict[str, str], matched: str) -> str | None:
    """Find the replacement for a matched span.

    A direct dict lookup fails whenever the key was a regex, so fall back to
    re-testing each key against the matched text, longest key first. Every
    substitution rule must be able to name the fix for anything it matched: a
    finding that reports no replacement tells the writer nothing.
    """
    direct = {k.lower(): v for k, v in substitutions.items()}
    replacement = direct.get(matched.lower())
    if replacement is not None:
        return replacement

    ordered = sorted(substitutions, key=len, reverse=True)
    for strip_assertions in (False, True):
        for key in ordered:
            probe = key
            if strip_assertions:
                probe = _TRAILING_ASSERTION.sub("", probe)
                probe = _LEADING_ASSERTION.sub("", probe)
                if probe == key:
                    continue
            try:
                if re.fullmatch(probe, matched, re.IGNORECASE):
                    return substitutions[key]
            except re.error:
                continue

    # Last resort: a key that matches somewhere inside the span. Only reached for
    # keys whose alternation is wider than the span the engine reported.
    for key in ordered:
        probe = _LEADING_ASSERTION.sub("", _TRAILING_ASSERTION.sub("", key))
        try:
            if re.search(probe, matched, re.IGNORECASE):
                return substitutions[key]
        except re.error:
            continue
    return None


class Engine:
    """Runs one ruleset against one document."""

    def __init__(
        self,
        rules: list[Rule],
        config: ResolvedConfig,
        only: set[str] | None = None,
    ) -> None:
        """`only` restricts execution to the named qualified ids.

        The caller passes the rules Vale did NOT take, so the two engines partition
        the ruleset instead of both running everything -- which reported every
        finding twice. Left as None the engine runs everything it selects, which is
        what `severity_for` callers and the tests want.
        """
        self.config = config
        self.rules = [r for r in rules if self._active(r)]
        if only is not None:
            self.rules = [r for r in self.rules if r.qualified_id in only]
        self._compiled: dict[str, re.Pattern[str]] = {}

    # --- rule selection -------------------------------------------------------

    def _active(self, rule: Rule) -> bool:
        """A rule runs when its tier admits it and no config layer turned it off.

        `severity = "off"` is the ONE way to disable, at either level. There used to
        be a second, a category `enabled = false`, and it was not a synonym: it was
        checked before the severity and could not be undone by a later layer. The
        profiles set it on 15 categories, so at `relaxed` a project writing

            [categories]
            ste-nouns = "warning"

        was silently ignored -- the value parsed, validated, resolved, and changed
        nothing. `severity_for` calls that failure mode out by name for the promotion
        case: the project wrote what it wanted and the gate ignored it, which is
        worse than either honouring or rejecting it. Collapsing the two makes the
        profile's own disabling a normal layer that a project can override.
        """
        profile = self.config.profile.value
        if rule.tier_for(profile) is Tier.EXCLUDED:
            return False
        if rule.kind is RuleKind.JUDGEMENT:
            return False  # carried for the reviewer; never fires mechanically

        category = self.config.categories.get(rule.category)
        if category is not None and category.severity is Severity.OFF:
            return False

        override = self.config.rules.get(rule.qualified_id)
        if override is not None and override.severity is Severity.OFF:
            return False
        return True

    def _authored(self, setting: str) -> bool:
        """Did a human write this setting, or did the profile supply it?

        Reads `ResolvedConfig.provenance`, which names the layer whose value
        survived for each setting some layer touched. A profile default is recorded
        as `profile default (...)`; anything a config file or an override set is
        recorded as `config` or `overrides[i] (...)`. Absent means untouched.

        Conservative on purpose: an unrecognised label counts as authored, so a new
        layer added to `resolve_for` errs toward honouring what somebody wrote rather
        than silently discarding it.
        """
        where = self.config.provenance.get(setting)
        return where is not None and not where.startswith("profile default")

    def severity_for(self, rule: Rule) -> Severity:
        """Resolve the level this rule reports at.

        Precedence, narrowest wins: rule override > AUTHORED category severity >
        tier disposition > the rule's shipped severity. An authored severity SETS
        the level in both directions, so `severity = "error"` promotes and
        `severity = "warning"` demotes.

        AUTHORED is the load-bearing word, and getting it wrong made the advisory
        tier almost meaningless. `ResolvedConfig.categories` is SEEDED from the
        profile's own defaults, so a category severity is not evidence that anybody
        asked for it -- and letting it override the advisory demotion below meant
        the profile overrode itself. `ai-tells-structure` at `normal` marks
        `emphasis-paragraph-metric` advisory and sets the category to `error` in the
        same breath; the category won, and a rule the profile does not stand behind
        failed the gate as an ERROR. Measured across the three profiles: of 64
        advisory-and-active rules only 11 were still suggestions, and 12 had been
        promoted to ERROR by their own profile.

        `provenance` is what tells the two apart -- it records the layer that set
        each surviving value, and a profile default is never credited to `config` or
        to an override. So the promotion is honoured when a human wrote it and
        ignored when it is just the profile's own coarser dial.
        """
        severity = rule.severity

        # Read from the TIER, not from whether the demotion below changed anything. A
        # rule that already ships at `suggestion` never enters that branch, and
        # deriving the flag there let the profile promote exactly those rules -- the
        # quietest ones -- straight to ERROR.
        advisory = rule.tier_for(self.config.profile.value) is Tier.ADVISORY

        if advisory:
            # SUGGESTION, not WARNING. An advisory rule is one the profile does not
            # stand behind, so it must not be able to fail the run on its own -- and
            # capping at WARNING let it do exactly that through the density budget,
            # which counts by severity weight rather than by tier. Measured: the
            # controlled-vocabulary rule is advisory at `normal` and still drove all
            # 8 independent-corpus documents to score 0.0, contributing 78 of 154
            # findings on a correct specification. "Advisory" that fails the gate is
            # just "enforced" with a quieter label.
            if severity.rank > Severity.SUGGESTION.rank:
                severity = Severity.SUGGESTION

        # Set, not cap. Capping downward only made `[categories.x] severity =
        # "error"` silently do nothing: the project wrote the promotion it wanted and
        # the gate ignored it, which is worse than either honouring or rejecting it.
        #
        # It overrides the advisory demotion above only when a HUMAN wrote it. Naming
        # a category and asking for `error` says the profile's judgement about that
        # category does not apply here; a value the profile itself supplied says
        # nothing of the kind, and honouring it let the profile contradict its own
        # tiers.
        category = self.config.categories.get(rule.category)
        if category is not None and category.severity is not None:
            if not advisory or self._authored(f"categories.{rule.category}"):
                severity = category.severity

        override = self.config.rules.get(rule.qualified_id)
        if override is not None and override.severity is not None:
            severity = override.severity
        return severity

    # --- suppressions ---------------------------------------------------------

    def _scan_suppressions(
        self, document: Document
    ) -> tuple[dict[int, list[Suppression]], set[int], list[Finding]]:
        """Collect annotations from the RAW lines.

        Raw, not prose: the parser blanks HTML comments so they are not linted,
        which means the annotations are only visible here.
        """
        by_line: dict[int, list[Suppression]] = {}
        disabled: set[int] = set()
        invalid: list[Finding] = []
        block_disabled = False

        known = {r.qualified_id: r for r in self.rules}

        for index, line in enumerate(document.raw_lines):
            number = index + 1
            if DISABLE_START.search(line):
                block_disabled = True
            if DISABLE_END.search(line):
                block_disabled = False
            if block_disabled:
                disabled.add(number)
            if DISABLE_LINE.search(line):
                disabled.add(number + 1)

            for match in SUPPRESSION.finditer(line):
                rule_id = match.group("rule")
                reason = match.group("reason")
                # An annotation applies to the following line, matching the
                # disable-next-line convention readers already expect.
                target = number + 1
                by_line.setdefault(target, []).append(
                    Suppression(rule=rule_id, reason=reason, line=number)
                )

                rule = known.get(rule_id)
                if rule is None:
                    continue  # rule not active here; nothing to validate against
                if reason is None:
                    invalid.append(
                        Finding(
                            path=document.path,
                            line=number,
                            rule_id="meta.invalid-suppression",
                            category="meta",
                            severity=Severity.ERROR,
                            message=(
                                f"suppression of {rule_id} names no reason. "
                                f"Add reason=<one of: {', '.join(rule.exceptions) or 'none defined'}>."
                            ),
                        )
                    )
                elif rule.exceptions and reason not in rule.exceptions:
                    invalid.append(
                        Finding(
                            path=document.path,
                            line=number,
                            rule_id="meta.invalid-suppression",
                            category="meta",
                            severity=Severity.ERROR,
                            message=(
                                f'reason "{reason}" is not an exception of {rule_id}. '
                                f"Valid: {', '.join(rule.exceptions)}."
                            ),
                        )
                    )
        return by_line, disabled, invalid

    def _suppressed(
        self,
        rule: Rule,
        line: int,
        suppressions: dict[int, list[Suppression]],
        disabled: set[int],
    ) -> bool:
        if line in disabled:
            return True
        for entry in suppressions.get(line, []):
            if entry.rule != rule.qualified_id:
                continue
            if entry.reason is None:
                continue  # malformed; already reported, does not suppress
            if rule.exceptions and entry.reason not in rule.exceptions:
                continue  # invalid; already reported, does not suppress
            return True
        return False

    # --- pattern compilation --------------------------------------------------

    def _pattern_for(self, rule: Rule) -> re.Pattern[str] | None:
        cached = self._compiled.get(rule.qualified_id)
        if cached is not None:
            return cached

        flags = re.IGNORECASE if rule.ignore_case else 0
        if rule.kind is RuleKind.TOKENS and rule.tokens:
            # Sort longest-first so "in order to" wins over "order".
            alternatives = "|".join(
                re.escape(t) for t in sorted(rule.tokens, key=len, reverse=True)
            )
            # Boundaries that tolerate a leading/trailing non-word character,
            # because many tokens are multi-word phrases with punctuation.
            source = rf"(?<![\w-])(?:{alternatives})(?![\w-])"
        elif rule.kind is RuleKind.SUBSTITUTION and rule.substitutions:
            source = build_substitution_pattern(rule.substitutions)
        elif rule.kind is RuleKind.PATTERN and rule.pattern:
            source = rule.pattern
        else:
            return None

        try:
            compiled = re.compile(source, flags)
        except re.error:
            # A rule that cannot compile must be loud. Returning None here would
            # make it silently match nothing, which reads as a clean document --
            # the exact failure this project already documents for Vale.
            raise
        self._compiled[rule.qualified_id] = compiled
        return compiled

    # --- execution ------------------------------------------------------------

    def unimplemented_metrics(self) -> list[str]:
        """Active metric rules this engine cannot measure.

        Such a rule loads, validates, runs, and matches nothing, so the document
        reports clean whether or not it complies -- the failure mode this project
        exists to prevent. The caller reports these as `unchecked`; they are not
        silently dropped and they are not a load error, because the rule is
        well-formed and a future Vale plan may pick it up.
        """
        return sorted(
            rule.qualified_id
            for rule in self.rules
            if rule.kind is RuleKind.METRIC and (rule.metric or "") not in NATIVE_METRICS
        )

    def run(self, document: Document) -> list[Finding]:
        suppressions, disabled, findings = self._scan_suppressions(document)

        for rule in self.rules:
            if rule.kind in (RuleKind.TOKENS, RuleKind.PATTERN, RuleKind.SUBSTITUTION):
                findings.extend(
                    self._run_lexical(rule, document, suppressions, disabled)
                )
            elif rule.kind is RuleKind.METRIC:
                findings.extend(
                    self._run_metric(rule, document, suppressions, disabled)
                )
            elif rule.kind is RuleKind.STRUCTURE:
                findings.extend(
                    self._run_structure(rule, document, suppressions, disabled)
                )

        findings.sort(key=lambda f: (f.line, f.column, f.rule_id))
        return findings

    def _lines_for_scope(self, rule: Rule, document: Document) -> list[tuple[int, str]]:
        if rule.scope is Scope.RAW:
            return [(i + 1, line) for i, line in enumerate(document.raw_lines)]
        if rule.scope is Scope.HEADING:
            return [
                (b.lines[0], b.text)
                for b in document.blocks
                if b.kind is BlockKind.HEADING
            ]
        return [(i + 1, line) for i, line in enumerate(document.prose_lines) if line]

    def _run_lexical(
        self,
        rule: Rule,
        document: Document,
        suppressions: dict[int, list[Suppression]],
        disabled: set[int],
    ) -> list[Finding]:
        pattern = self._pattern_for(rule)
        if pattern is None:
            return []
        severity = self.severity_for(rule)
        allowed = {a.lower() for a in rule.allowlist}
        results: list[Finding] = []

        for number, text in self._lines_for_scope(rule, document):
            if self._suppressed(rule, number, suppressions, disabled):
                continue
            for match in pattern.finditer(text):
                matched = match.group(0)
                if matched.lower() in allowed:
                    continue
                # An allowlist entry may be a longer phrase containing the match,
                # e.g. "iron resolution" allowing "iron".
                window = text[max(0, match.start() - 30) : match.end() + 30].lower()
                if any(entry in window for entry in allowed if " " in entry):
                    continue
                if not rule.match_all_caps and _is_all_caps(matched):
                    continue
                if "quotation" in rule.exceptions and _inside_quotation(
                    text, match.start(), match.end()
                ):
                    continue

                replacement = None
                if rule.kind is RuleKind.SUBSTITUTION and rule.substitutions:
                    replacement = match_substitution(rule.substitutions, matched)

                message = format_message(
                    rule.message, match=matched, replacement=replacement or ""
                )
                results.append(
                    Finding(
                        path=document.path,
                        line=number,
                        column=match.start() + 1,
                        end_column=match.end() + 1,
                        rule_id=rule.qualified_id,
                        category=rule.category,
                        severity=severity,
                        message=message,
                        matched_text=matched,
                        replacement=replacement,
                        ste_ref=rule.provenance.ste_ref,
                        orwell_ref=rule.provenance.orwell_ref,
                    )
                )
        return results

    def _run_metric(
        self,
        rule: Rule,
        document: Document,
        suppressions: dict[int, list[Suppression]],
        disabled: set[int],
    ) -> list[Finding]:
        severity = self.severity_for(rule)
        results: list[Finding] = []

        def exceeds(value: float, threshold: float) -> bool:
            return {
                "gt": value > threshold,
                "gte": value >= threshold,
                "lt": value < threshold,
                "lte": value <= threshold,
            }[rule.comparison]

        metric = rule.metric or ""
        threshold = rule.threshold or 0

        if metric == "sentence_words":
            for sentence in document.sentences:
                if rule.text_type is not TextType.ANY and sentence.text_type is not rule.text_type:
                    continue
                # An explicit threshold on the rule wins; otherwise the cap comes
                # from the sentence's own text type, so one rule covers 20/25.
                cap = threshold or WORD_CAPS[sentence.text_type]
                if not exceeds(sentence.word_count, cap):
                    continue
                if self._suppressed(rule, sentence.line, suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, sentence.line, severity,
                        format_message(rule.message, 
                            match=str(sentence.word_count), replacement=str(int(cap))
                        ),
                    )
                )

        elif metric == "clause_boundaries":
            # Counts IDEAS, not words. A 24-word sentence can carry four ideas and
            # a 30-word one can be a single clean list, so the word cap and this
            # are separate checks.
            for sentence in document.sentences:
                count = count_clause_boundaries(sentence.text)
                if not exceeds(count, threshold):
                    continue
                if self._suppressed(rule, sentence.line, suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, sentence.line, severity,
                        format_message(rule.message, 
                            match=str(count + 1), replacement=str(int(threshold) + 1)
                        ),
                    )
                )

        elif metric == "lead_in_words":
            # STE 6.4 counts the text before a list's colon as a sentence of its own.
            # The measurement is therefore "words BEFORE the colon", and it applies
            # only to a sentence that HAS one.
            #
            # It had no native branch and reached Vale through `METRIC_TOKENS`, mapped
            # to the plain word token. Vale's occurrence counter has no notion of a
            # colon, so the compiled rule counted every word in the sentence and fired
            # on any sentence over 20 words whether or not a colon appeared in it. On
            # this project's own README that was 27 findings, all of them ERROR, on
            # lines whose text contains no colon at all -- the rule reported the
            # sentence cap it already has, under a message telling the author to fix a
            # list lead-in they never wrote.
            # Iterating SENTENCES, not lines, because the rule declares
            # `scope: sentence` and a lead-in is a sentence. A first attempt walked
            # `_lines_for_scope` and inherited markdown's hard wrapping: the colon
            # sits on a later physical line than the words it follows, so a wrapped
            # sentence was measured as the part before the wrap and a colon two lines
            # down was credited to text it does not terminate.
            for sentence in document.sentences:
                head, separator, _ = sentence.text.partition(":")
                if not separator:
                    continue
                line_number = sentence.line
                count = count_words(head)
                if not exceeds(count, threshold):
                    continue
                if self._suppressed(rule, line_number, suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, line_number, severity,
                        format_message(
                            rule.message,
                            match=str(count),
                            replacement=str(int(threshold)),
                        ),
                    )
                )

        elif metric == "paragraph_words":
            # Native because Vale reported a different number here. An inline code
            # span is ONE word to `count_words` and zero to Vale, whose markdown
            # scoping drops the span before its token counter sees it -- measured on
            # this project's own README, paragraph line 37: 8 by Vale against 10 by
            # `count_words`. At an 8-word bound that gap decides the finding, and the
            # compiled rule fired on four blocks that are not emphasis paragraphs.
            stems = _list_stem_lines(document)
            for block in document.paragraphs:
                count = count_words(block.text)
                if not exceeds(count, threshold):
                    continue
                # A LIST STEM IS NOT AN EMPHASIS PARAGRAPH, and excluding it is not a
                # courtesy: `ste-sentences.complex-text-not-in-vertical-list` orders
                # the author to turn a series into a vertical list, every list needs a
                # stem to say what it enumerates, and a stem is short by construction.
                # Without this the two shipped rules contradict each other, and an
                # author who obeys the first is reported by the second with no move
                # left that satisfies both. Measured while rewriting this project's
                # own README against the ruleset: obeying the list rule 15 times took
                # this rule from 1 finding to 7, all of them stems.
                if block.lines[0] in stems:
                    continue
                # A paragraph nobody wrote as prose is not an emphasis paragraph. A
                # heading, a list item, and a table cell are already separate blocks,
                # so what is left to exclude is the degenerate case: a block whose
                # entire content is one opaque unit -- a lone code span, a bare
                # version string. `Apache-2.0.` under a `## License` heading is the
                # canonical one, and telling an author to rejoin it to the paragraph
                # before it is advice they cannot take.
                if count <= 1:
                    continue
                if self._suppressed(rule, block.lines[0], suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, block.lines[0], severity,
                        format_message(
                            rule.message,
                            match=str(count),
                            replacement=str(int(threshold)),
                        ),
                    )
                )

        elif metric == "paragraph_sentences":
            for block in document.paragraphs:
                # STE 6.6 counts sentences per paragraph. A bulleted block does
                # not contribute one sentence per bullet here -- list items are
                # their own blocks, so they never reach this count.
                if not exceeds(len(block.sentences), threshold):
                    continue
                if self._suppressed(rule, block.lines[0], suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, block.lines[0], severity,
                        format_message(rule.message, 
                            match=str(len(block.sentences)),
                            replacement=str(int(threshold)),
                        ),
                    )
                )

        elif metric == "multiword_noun_words":
            for sentence in document.sentences:
                count = longest_noun_stack(sentence.text)
                if not exceeds(count, threshold):
                    continue
                if self._suppressed(rule, sentence.line, suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, sentence.line, severity,
                        format_message(
                            rule.message,
                            match=str(count),
                            replacement=str(int(threshold)),
                        ),
                    )
                )

        elif metric == "coordinated_items":
            for sentence in document.sentences:
                count = coordinated_items(sentence.text)
                if not exceeds(count, threshold):
                    continue
                if self._suppressed(rule, sentence.line, suppressions, disabled):
                    continue
                results.append(
                    self._metric_finding(
                        rule, document, sentence.line, severity,
                        format_message(
                            rule.message,
                            match=str(count),
                            replacement=str(int(threshold)),
                        ),
                    )
                )

        elif metric in {
            "syllables_per_word",
            "passive_ratio",
            "hedge_per_100_words",
            "abstraction_density",
            "concrete_referents_per_paragraph",
            "paragraph_words_stdev",
            "adjectives_per_noun",
            "consecutive_bold_colon_bullets",
            "bold_spans_per_1000_words",
            "dash_per_1000_words",
        }:
            value = self.document_metric(metric, document)
            if exceeds(value, threshold):
                results.append(
                    self._metric_finding(
                        rule, document, 1, severity,
                        format_message(rule.message, 
                            match=f"{value:.2f}", replacement=f"{threshold:.2f}"
                        ),
                    )
                )
        return results

    def _metric_finding(
        self,
        rule: Rule,
        document: Document,
        line: int,
        severity: Severity,
        message: str,
    ) -> Finding:
        return Finding(
            path=document.path,
            line=line,
            rule_id=rule.qualified_id,
            category=rule.category,
            severity=severity,
            message=message,
            ste_ref=rule.provenance.ste_ref,
            orwell_ref=rule.provenance.orwell_ref,
        )

    def _run_structure(
        self,
        rule: Rule,
        document: Document,
        suppressions: dict[int, list[Suppression]],
        disabled: set[int],
    ) -> list[Finding]:
        """Block-shape rules. Currently the paragraph-that-should-be-a-list
        heuristic and heading-hierarchy skips; both need block context that the
        lexical path does not have."""
        severity = self.severity_for(rule)
        results: list[Finding] = []

        if rule.id == "heading-level-skip":
            previous = 0
            for block in document.blocks:
                if block.kind is not BlockKind.HEADING:
                    continue
                if previous and block.level > previous + 1:
                    if not self._suppressed(rule, block.lines[0], suppressions, disabled):
                        results.append(
                            self._metric_finding(
                                rule, document, block.lines[0], severity,
                                format_message(rule.message, 
                                    match=f"h{block.level}", replacement=f"h{previous + 1}"
                                ),
                            )
                        )
                previous = block.level
        return results

    # --- document metrics -----------------------------------------------------

    def document_metric(self, name: str, document: Document) -> float:
        """Counted measures used by document-scope rules and by the report.

        Each traces to a source: syllables-per-word and concrete referents to
        Orwell's own arithmetic on the Ecclesiastes pair (1.22 good, 2.37 bad);
        passive ratio to his complaint about passive *preference* rather than use.
        """
        sentences = document.sentences
        text = document.prose_text()
        words = [w for w in re.findall(r"[A-Za-z']+", text)]

        if name == "syllables_per_word":
            if not words:
                return 0.0
            return sum(syllables(w) for w in words) / len(words)

        if name == "passive_ratio":
            if not sentences:
                return 0.0
            passive = re.compile(
                r"\b(?:am|is|are|was|were|be|been|being|get|gets|got)\s+"
                r"(?:\w+ly\s+)?(?:\w+(?:ed|en)|born|built|done|found|given|held|"
                r"kept|known|made|put|read|run|seen|sent|set|shown|told|written)\b",
                re.I,
            )
            hits = sum(1 for s in sentences if passive.search(s.text))
            return hits / len(sentences)

        if name == "hedge_per_100_words":
            if not words:
                return 0.0
            return len(HEDGE.findall(text)) / len(words) * 100

        if name == "abstraction_density":
            if not words:
                return 0.0
            return len(ABSTRACTION_SUFFIX.findall(text)) / len(words) * 100

        if name == "concrete_referents_per_paragraph":
            paragraphs = document.paragraphs
            if not paragraphs:
                return 0.0
            total = sum(len(CONCRETE_REFERENT.findall(p.text)) for p in paragraphs)
            return total / len(paragraphs)

        if name == "paragraph_words_stdev":
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

        if name in {"bold_spans_per_1000_words", "dash_per_1000_words"}:
            # Both measure the MARKUP, so both read `markup_text` rather than the
            # prose projection, which strips the very characters they count. Both
            # denominators are the prose word count, not a count of the markup text,
            # so a document does not dilute its own density by adding code blocks.
            if not words:
                return 0.0
            pattern = (
                BOLD_SPAN if name == "bold_spans_per_1000_words" else DASH_AS_ASIDE
            )
            return len(pattern.findall(document.markup_text())) / len(words) * 1000

        if name == "adjectives_per_noun":
            # Suffix heuristics, not a tagger. See ADJECTIVE_SUFFIX for why, and
            # read the number as a signal rather than a measurement: the rule ships
            # advisory outside strict and its own threshold is marked INFERRED.
            nouns = len(NOUN_SUFFIX.findall(text))
            if not nouns:
                return 0.0
            return len(ADJECTIVE_SUFFIX.findall(text)) / nouns

        if name == "consecutive_bold_colon_bullets":
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

        return 0.0
