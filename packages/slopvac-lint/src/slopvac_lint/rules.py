"""Load and validate the shipped ruleset.

Rules live in `rules/<category>.yml` inside the package, so a wheel carries them
and no network fetch is needed at lint time. A user-supplied directory is layered
on top via `--rules-dir`, which is how a project adds a house rule without
forking.

VALIDATION IS EAGER AND LOUD. Every rule is validated at load, every regex is
compiled, and every `examples[].bad` is asserted to match while `examples[].good`
is asserted not to. A rule whose pattern no longer fires is a rule that silently
passes every document, which is indistinguishable from clean prose -- the failure
mode this project already documented for unsynced Vale styles.
"""

from __future__ import annotations

import regex as re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

from .model import Category, Rule, RuleKind

# Resolved as a SUBDIRECTORY of the package, not as a package itself: this module
# is `slopvac_lint.rules`, so `resources.files("slopvac_lint.rules")` returns this
# module's own parent package and silently yields no rule files.
RULES_DIRNAME = "rules"
RULES_PACKAGE = "slopvac_lint"


class RuleLoadError(Exception):
    """A ruleset that cannot be trusted. Never downgraded to a warning."""


@dataclass
class RuleSet:
    categories: dict[str, Category] = field(default_factory=dict)

    @property
    def rules(self) -> list[Rule]:
        return [r for c in self.categories.values() for r in c.rules]

    @property
    def weights(self) -> dict[str, float]:
        return {name: c.weight for name, c in self.categories.items()}

    def by_id(self, qualified_id: str) -> Rule | None:
        for rule in self.rules:
            if rule.qualified_id == qualified_id:
                return rule
        return None

    def judgement_rules(self) -> list[Rule]:
        """Rules the linter cannot check, carried so the agentic reviewer reads
        one source of truth rather than a parallel prose catalog."""
        return [r for r in self.rules if r.kind is RuleKind.JUDGEMENT]


def _load_documents(text: str, origin: str) -> list[dict]:
    try:
        loaded = list(yaml.safe_load_all(text))
    except yaml.YAMLError as exc:
        raise RuleLoadError(f"{origin}: invalid YAML: {exc}") from exc
    return [d for d in loaded if isinstance(d, dict)]


def _build_category(data: dict, origin: str) -> Category:
    try:
        category = Category.model_validate(data)
    except Exception as exc:
        raise RuleLoadError(f"{origin}: {exc}") from exc

    seen: set[str] = set()
    for rule in category.rules:
        if rule.id in seen:
            raise RuleLoadError(
                f"{origin}: duplicate rule id '{rule.id}' in category '{category.id}'"
            )
        seen.add(rule.id)
        object.__setattr__(rule, "category", category.id)
    return category


def _verify_examples(category: Category, origin: str) -> list[str]:
    """Prove every pattern still fires. Returns problems rather than raising, so
    one broken rule reports alongside the others instead of masking them."""
    problems: list[str] = []

    for rule in category.rules:
        if rule.kind not in (RuleKind.TOKENS, RuleKind.PATTERN, RuleKind.SUBSTITUTION):
            continue
        flags = re.IGNORECASE if rule.ignore_case else 0

        if rule.kind is RuleKind.PATTERN and rule.pattern:
            source = rule.pattern
        elif rule.kind is RuleKind.TOKENS and rule.tokens:
            joined = "|".join(re.escape(t) for t in sorted(rule.tokens, key=len, reverse=True))
            source = rf"(?<![\w-])(?:{joined})(?![\w-])"
        elif rule.kind is RuleKind.SUBSTITUTION and rule.substitutions:
            joined = "|".join(
                re.escape(k) for k in sorted(rule.substitutions, key=len, reverse=True)
            )
            source = rf"(?<![\w-])(?:{joined})(?![\w-])"
        else:
            problems.append(f"{origin}: {rule.qualified_id} has no payload to compile")
            continue

        try:
            pattern = re.compile(source, flags)
        except re.error as exc:
            problems.append(f"{origin}: {rule.qualified_id} regex does not compile: {exc}")
            continue

        for index, example in enumerate(rule.examples):
            if not pattern.search(example.bad):
                problems.append(
                    f"{origin}: {rule.qualified_id} example {index} 'bad' text does "
                    f"not match its own pattern: {example.bad!r}"
                )
            if example.good is not None and pattern.search(example.good):
                problems.append(
                    f"{origin}: {rule.qualified_id} example {index} 'good' text "
                    f"matches the pattern, so the rule fires on its own fix: "
                    f"{example.good!r}"
                )
    return problems


def load_ruleset(
    extra_dirs: list[Path] | None = None, verify: bool = True
) -> RuleSet:
    """Load the packaged ruleset, then layer any extra directories over it.

    A later category with the same id REPLACES the earlier one wholesale rather
    than merging: a project that redefines a category means to own it, and a
    silent per-rule merge across files would make the effective ruleset
    unreadable.
    """
    ruleset = RuleSet()
    problems: list[str] = []

    try:
        root = resources.files(RULES_PACKAGE) / RULES_DIRNAME
    except ModuleNotFoundError:
        root = None

    sources: list[tuple[str, str]] = []
    if root is not None and root.is_dir():
        for entry in sorted(root.iterdir(), key=lambda p: p.name):
            if entry.name.endswith((".yml", ".yaml")):
                sources.append((entry.name, entry.read_text(encoding="utf-8")))

    for directory in extra_dirs or []:
        if not directory.is_dir():
            raise RuleLoadError(f"rules directory not found: {directory}")
        for path in sorted(directory.glob("*.y*ml")):
            sources.append((str(path), path.read_text(encoding="utf-8")))

    if not sources:
        raise RuleLoadError(
            "no rule files found. The package ships rules under "
            f"{RULES_PACKAGE}; a broken install is the usual cause."
        )

    for origin, text in sources:
        for data in _load_documents(text, origin):
            category = _build_category(data, origin)
            if verify:
                problems.extend(_verify_examples(category, origin))
            ruleset.categories[category.id] = category

    if problems:
        raise RuleLoadError(
            "the ruleset failed self-verification:\n  " + "\n  ".join(problems)
        )
    return ruleset
