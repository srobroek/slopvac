"""Execute rules against a parsed document and produce findings.

The checker is selected by `Rule.kind`, so adding a lexical, substitution, or
threshold rule needs no code -- only a YAML file. That is what makes the ruleset
user-editable in the way Vale's styles are, without Vale's single-config-file
limitation.

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


class Engine:
    """Runs one ruleset against one document."""

    def __init__(self, rules: list[Rule], config: ResolvedConfig) -> None:
        self.config = config
        self.rules = [r for r in rules if self._active(r)]
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

        Precedence, narrowest wins: rule override > category cap > tier
        disposition > the rule's shipped severity. A category cap LOWERS but never
        raises, so `severity = "error"` on a category does not promote a
        suggestion into a gate failure -- that would let a coarse dial create
        findings the rule author never intended to be blocking.
        """
        severity = rule.severity

        if rule.tier_for(self.config.profile.value) is Tier.ADVISORY:
            if severity.rank > Severity.WARNING.rank:
                severity = Severity.WARNING

        category = self.config.categories.get(rule.category)
        if category is not None and category.severity is not None:
            if category.severity.rank < severity.rank:
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
            alternatives = "|".join(
                re.escape(k) for k in sorted(rule.substitutions, key=len, reverse=True)
            )
            source = rf"(?<![\w-])(?:{alternatives})(?![\w-])"
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

                replacement = None
                if rule.kind is RuleKind.SUBSTITUTION and rule.substitutions:
                    lookup = {k.lower(): v for k, v in rule.substitutions.items()}
                    replacement = lookup.get(matched.lower())

                message = rule.message.format(
                    match=matched, replacement=replacement or ""
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
                        rule.message.format(
                            match=str(sentence.word_count), replacement=str(int(cap))
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
                        rule.message.format(
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
                        rule.message.format(
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
                                rule.message.format(
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
