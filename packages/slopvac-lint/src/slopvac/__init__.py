"""slopvac: lint prose and source comments with deterministic rules."""

__version__ = "2.11.0"  # x-release-please-version

from .config import Config, Profile, Severity, load_config, resolve_for
from .model import Category, DocumentScore, Finding, Rule, RuleKind
from .rules import RuleSet, load_ruleset

__all__ = [
    "Category",
    "Config",
    "DocumentScore",
    "Finding",
    "Profile",
    "Rule",
    "RuleKind",
    "RuleSet",
    "Severity",
    "__version__",
    "load_config",
    "load_ruleset",
    "resolve_for",
]
