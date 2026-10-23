"""slopvac: lint prose and source comments with deterministic rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

__version__ = "2.18.1"  # x-release-please-version

if TYPE_CHECKING:
    from .config import Config, load_config, resolve_for
    from .enums import Profile, RuleKind, Severity
    from .model import Category, DocumentScore, Finding, Rule
    from .rules import RuleSet, load_ruleset

# The public names, and the submodule each comes from. They resolve on first
# access (PEP 562) rather than when the package loads: every `slopvac` command
# imports this package, and most of them, `--version` first, need none of the
# models or the ruleset loader.
_EXPORTS = {
    "Category": "model",
    "Config": "config",
    "DocumentScore": "model",
    "Finding": "model",
    "Profile": "enums",
    "Rule": "model",
    "RuleKind": "enums",
    "RuleSet": "rules",
    "Severity": "enums",
    "load_config": "config",
    "load_ruleset": "rules",
    "resolve_for": "config",
}

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


def __getattr__(name: str) -> object:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(f".{module}", __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_EXPORTS})
