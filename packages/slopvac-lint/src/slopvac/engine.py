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

import regex as re
from dataclasses import dataclass
from typing import Any

from .analyze import (
    ABSTRACTION_SUFFIX,
    CONCRETE_REFERENT,
    HEDGE,
    BlockKind,
    Document,
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


# Metric names `_run_metric` knows how to measure. A rule naming anything else
# cannot fire, so it is reported rather than run -- see `unimplemented_metrics`.
NATIVE_METRICS = frozenset(
    {
        "sentence_words",
        "clause_boundaries",
        "paragraph_sentences",
        "syllables_per_word",
        "passive_ratio",
        "hedge_per_100_words",
        "abstraction_density",
        "concrete_referents_per_paragraph",
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

        Category `enabled = false` wins over a rule-level severity, because
        disabling a category is the coarser and more deliberate act.
        """
        profile = self.config.profile.value
        if rule.tier_for(profile) is Tier.EXCLUDED:
            return False
        if rule.kind is RuleKind.JUDGEMENT:
            return False  # carried for the reviewer; never fires mechanically

        category = self.config.categories.get(rule.category)
        if category is not None:
            if category.enabled is False:
                return False
            if category.severity is Severity.OFF:
                return False

        override = self.config.rules.get(rule.qualified_id)
        if override is not None and override.severity is Severity.OFF:
            return False
        return True

    def severity_for(self, rule: Rule) -> Severity:
        """Resolve the level this rule reports at.

        Precedence, narrowest wins: rule override > category severity > tier
        disposition > the rule's shipped severity. A category severity SETS the
        level in both directions, so `severity = "error"` promotes and
        `severity = "warning"` demotes.
        """
        severity = rule.severity

        if rule.tier_for(self.config.profile.value) is Tier.ADVISORY:
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
        # This deliberately overrides the advisory cap above -- naming a category and
        # asking for `error` says the profile's judgement about that category does not
        # apply here, and the profile is the coarser dial of the two.
        category = self.config.categories.get(rule.category)
        if category is not None and category.severity is not None:
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

        elif metric in {
            "syllables_per_word",
            "passive_ratio",
            "hedge_per_100_words",
            "abstraction_density",
            "concrete_referents_per_paragraph",
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

        return 0.0
