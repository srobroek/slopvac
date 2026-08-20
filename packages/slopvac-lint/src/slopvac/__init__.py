"""slopvac: score prose against AI-slop, Simplified Technical English, and
Orwell rulesets.

Two layers, because half of this resists mechanization. The deterministic layer
is here. The judgement layer lives in the `slopvac` agent package, which reads
this package's `kind: judgement` rules as its source of truth rather than
carrying a parallel prose catalog.
"""

__version__ = "0.1.0"  # x-release-please-version

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
