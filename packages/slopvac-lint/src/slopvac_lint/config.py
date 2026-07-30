"""Configuration model and resolution.

THE RESOLUTION CHAIN, outermost to innermost. Each layer patches the one above
rather than replacing it, which is the whole reason this exists instead of Vale's
single-file model: a project that wants one rule off should change one line, not
author 200.

    1. the built-in profile named by `profile`  (strict | normal | relaxed)
    2. the top-level `[categories]` / `[rules]` tables in slopvac.toml
    3. every `[[overrides]]` block whose `files` glob matches, in file order

A later layer wins per FIELD, not per table, so an override that sets only
`severity` keeps the profile's threshold. Vale merges sections the same way; the
difference is that a Vale rule line binds to the section ABOVE it, which is a
documented footgun in this repo's own vale.ini. Here the binding is explicit:
a rule setting lives inside the block it applies to.

Config discovery walks up from each target file, so a monorepo package can carry
its own slopvac.toml and a file outside any package still resolves at the root.
"""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

import pathspec
from pydantic import BaseModel, ConfigDict, Field, model_validator

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - requires-python is >=3.11
    import tomli as tomllib

CONFIG_NAMES = ("slopvac.toml", ".slopvac.toml")
PYPROJECT = "pyproject.toml"


class Severity(str, Enum):
    """A finding's weight. `off` is a level rather than a deletion so that a
    disabled rule still appears in `slopvac-lint rules --show-disabled`."""

    OFF = "off"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"

    @property
    def rank(self) -> int:
        return {"off": 0, "suggestion": 1, "warning": 2, "error": 3}[self.value]

    def at_least(self, floor: Severity) -> bool:
        return self.rank >= floor.rank


class Profile(str, Enum):
    """Strictness tier.

    STRICT is technical documentation: reference, specs, API docs, runbooks.
    NORMAL is general writing held to a high bar: README, guides, ADRs, essays.
    RELAXED keeps only high-level readability rules: notes, comments, drafts.

    The tiers are NOT a simple ordering. Two rules invert deliberately -- see
    profiles.py -- because agentless passive is correct in a spec and wrong in a
    README, so passive voice is advisory at strict and enforced at normal.
    """

    STRICT = "strict"
    NORMAL = "normal"
    RELAXED = "relaxed"


class CategorySettings(BaseModel):
    """Per-category dials. Every field is optional so a patch layer can set one
    without restating the others."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity | None = Field(
        default=None,
        description="Cap for every rule in this category. Lowers a rule's own "
        "severity but never raises it: a rule shipped as `suggestion` stays a "
        "suggestion under `severity = 'error'`.",
    )
    max_per_100_words: float | None = Field(
        default=None,
        ge=0,
        description="Density budget. Above this the category fails even when no "
        "single finding is an error.",
    )
    weight: float | None = Field(
        default=None,
        ge=0,
        description="Multiplier on this category's contribution to the overall "
        "score. 0 scores the category as informational.",
    )
    enabled: bool | None = None


class RuleSettings(BaseModel):
    """Per-rule override. `severity = "off"` is the documented way to disable."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity | None = None
    weight: float | None = Field(default=None, ge=0)


class Thresholds(BaseModel):
    """Document-level gates, evaluated after every finding is collected.

    These are the numbers the CI action reports on. `max_total_per_100_words` is
    the headline score budget; the others catch a document that passes on density
    while failing on a single unacceptable finding.
    """

    model_config = ConfigDict(extra="forbid")

    max_total_per_100_words: float | None = Field(default=None, ge=0)
    max_errors: int | None = Field(default=0, ge=0)
    max_warnings: int | None = Field(default=None, ge=0)
    min_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Floor on the 0-100 quality score. Fails the run when the "
        "document scores below it.",
    )


class LocaleSettings(BaseModel):
    """Spelling target.

    Separate from the rules because the correct spelling depends on the project,
    not the prose: `colour` is a defect in a `en-US` document and correct in a
    `en-GB` one. The spelling rule is generated per run from this setting, so one
    variant table serves every direction.

    `und` disables the spelling check without disabling the rest of its category.
    """

    model_config = ConfigDict(extra="forbid")

    default: str = Field(
        default="en-US",
        description="Locale tag: en-US, en-GB, or und to disable. ASD-STE100 "
        "rule 1.14 asks for American spelling, which is why en-US is the "
        "default rather than a rule a British English project cannot turn off.",
    )
    allow: list[str] = Field(
        default_factory=list,
        description="Words this project spells its own way regardless of locale. "
        "Added to the identifier allowlist.",
    )


class ValeSettings(BaseModel):
    """The Vale sub-gate. Vale owns the regex layer for the styles already
    published from this repo; slopvac-lint owns scoring, tiers, and the rules Vale
    cannot express.

    `binary` stays configurable because Vale is a Go binary installed
    out-of-band. When it is absent the run reports the styles as UNCHECKED rather
    than passing them silently -- an unsynced style makes Vale report every file
    clean, which is indistinguishable from a pass.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    binary: str = "vale"
    config: Path | None = Field(
        default=None,
        description="Path to a .vale.ini. Defaults to the packaged config for "
        "the resolved profile.",
    )
    styles: list[str] | None = None


class Override(BaseModel):
    """A glob-scoped patch. Matched with gitignore semantics via pathspec, so
    `docs/**` and `!docs/generated/**` behave the way a reader expects.
    """

    model_config = ConfigDict(extra="forbid")

    files: list[str] = Field(
        min_length=1,
        description="gitignore-style patterns. A leading `!` negates.",
    )
    profile: Profile | None = None
    categories: dict[str, CategorySettings] = Field(default_factory=dict)
    rules: dict[str, RuleSettings] = Field(default_factory=dict)
    thresholds: Thresholds | None = None
    vale: ValeSettings | None = None
    locale: LocaleSettings | None = None

    @model_validator(mode="after")
    def _compile_spec(self) -> Override:
        # Compiled once at load; matching runs per file.
        object.__setattr__(
            self,
            "_spec",
            pathspec.PathSpec.from_lines("gitwildmatch", self.files),
        )
        return self

    def matches(self, relative_path: str) -> bool:
        spec: pathspec.PathSpec = getattr(self, "_spec")
        return spec.match_file(relative_path)


class Config(BaseModel):
    """A loaded slopvac.toml, before per-file resolution."""

    model_config = ConfigDict(extra="forbid")

    profile: Profile = Field(
        default=Profile.NORMAL,
        description="Tier applied where no override matches. `normal` is the "
        "default because `strict` on an existing repo produces a wall of "
        "findings and invites disabling the gate outright.",
    )
    categories: dict[str, CategorySettings] = Field(default_factory=dict)
    rules: dict[str, RuleSettings] = Field(default_factory=dict)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    vale: ValeSettings = Field(default_factory=ValeSettings)
    locale: LocaleSettings = Field(default_factory=LocaleSettings)
    overrides: list[Override] = Field(default_factory=list)

    exclude: list[str] = Field(
        default_factory=lambda: [
            "**/node_modules/**",
            "**/apm_modules/**",
            "**/.venv/**",
            "**/dist/**",
            "**/build/**",
            "**/CHANGELOG.md",
            "**/.git/**",
        ],
        description="Never linted. CHANGELOG.md is here because release-please "
        "generates it from commit subjects, so its prose is not authored.",
    )

    # Set by the loader, not by the file.
    source: Path | None = Field(default=None, exclude=True)
    root: Path | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _compile_exclude(self) -> Config:
        object.__setattr__(
            self,
            "_exclude_spec",
            pathspec.PathSpec.from_lines("gitwildmatch", self.exclude),
        )
        return self

    def is_excluded(self, relative_path: str) -> bool:
        spec: pathspec.PathSpec = getattr(self, "_exclude_spec")
        return spec.match_file(relative_path)


class ResolvedConfig(BaseModel):
    """The settings that apply to ONE file, after the profile and every matching
    override are folded together. The engine reads only this.
    """

    model_config = ConfigDict(extra="forbid")

    path: Path
    profile: Profile
    categories: dict[str, CategorySettings]
    rules: dict[str, RuleSettings]
    thresholds: Thresholds
    vale: ValeSettings
    locale: LocaleSettings
    applied_overrides: list[str] = Field(
        default_factory=list,
        description="Which override globs matched, in order. Reported by "
        "`--explain-config` so a surprising result is traceable.",
    )


def _merge_category(
    base: CategorySettings | None, patch: CategorySettings | None
) -> CategorySettings:
    """Field-level merge. A patch field of None leaves the base value alone."""
    if base is None:
        base = CategorySettings()
    if patch is None:
        return base.model_copy()
    merged = base.model_dump()
    for key, value in patch.model_dump().items():
        if value is not None:
            merged[key] = value
    return CategorySettings.model_validate(merged)


def _merge_rule(base: RuleSettings | None, patch: RuleSettings | None) -> RuleSettings:
    if base is None:
        base = RuleSettings()
    if patch is None:
        return base.model_copy()
    merged = base.model_dump()
    for key, value in patch.model_dump().items():
        if value is not None:
            merged[key] = value
    return RuleSettings.model_validate(merged)


def _merge_thresholds(base: Thresholds, patch: Thresholds | None) -> Thresholds:
    if patch is None:
        return base.model_copy()
    merged = base.model_dump()
    for key, value in patch.model_dump().items():
        if value is not None:
            merged[key] = value
    return Thresholds.model_validate(merged)


def find_config(start: Path) -> Path | None:
    """Walk up from `start` looking for a config file.

    Checks the dedicated names first, then a `[tool.slopvac]` table in
    pyproject.toml, so a Python project can keep one config file. Stops at a
    filesystem or repository root.
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for directory in [current, *current.parents]:
        for name in CONFIG_NAMES:
            candidate = directory / name
            if candidate.is_file():
                return candidate
        pyproject = directory / PYPROJECT
        if pyproject.is_file():
            try:
                with pyproject.open("rb") as handle:
                    data = tomllib.load(handle)
            except (OSError, tomllib.TOMLDecodeError):
                data = {}
            if isinstance(data.get("tool"), dict) and "slopvac" in data["tool"]:
                return pyproject
        # A .git directory marks the outer bound of one project.
        if (directory / ".git").exists():
            break
    return None


class ConfigError(Exception):
    """A config file that exists but cannot be used.

    Raised rather than swallowed: silently falling back to defaults on a typo'd
    config means the project believes it configured a gate that is not running.
    """


def load_config(path: Path | None, root: Path | None = None) -> Config:
    """Load and validate a config file. `None` yields the defaults."""
    if path is None:
        config = Config()
        object.__setattr__(config, "root", root)
        return config

    try:
        with path.open("rb") as handle:
            raw: dict[str, Any] = tomllib.load(handle)
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc

    if path.name == PYPROJECT:
        raw = raw.get("tool", {}).get("slopvac", {})

    try:
        config = Config.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError
        raise ConfigError(f"{path}: {exc}") from exc

    object.__setattr__(config, "source", path)
    object.__setattr__(config, "root", root or path.parent)
    return config


def resolve_for(config: Config, file_path: Path) -> ResolvedConfig:
    """Fold the profile and every matching override into one settings object.

    Import is local to avoid a cycle: profiles describes rule defaults in terms
    of the enums above.
    """
    from .profiles import profile_defaults

    root = config.root or Path.cwd()
    try:
        relative = str(file_path.resolve().relative_to(root.resolve()))
    except ValueError:
        # Outside the config root -- match on the name alone rather than
        # silently applying no overrides.
        relative = file_path.name

    # Layer 1: the profile.
    profile = config.profile
    matching = [o for o in config.overrides if o.matches(relative)]
    for override in matching:
        if override.profile is not None:
            profile = override.profile

    defaults = profile_defaults(profile)
    categories = {name: settings.model_copy() for name, settings in defaults.items()}
    rules: dict[str, RuleSettings] = {}
    thresholds = _merge_thresholds(profile_thresholds(profile), config.thresholds)
    vale = config.vale.model_copy()
    locale = config.locale.model_copy()

    # Layer 2: the top-level tables.
    for name, patch in config.categories.items():
        categories[name] = _merge_category(categories.get(name), patch)
    for name, patch in config.rules.items():
        rules[name] = _merge_rule(rules.get(name), patch)

    # Layer 3: every matching override, in file order.
    applied: list[str] = []
    for override in matching:
        applied.extend(override.files)
        for name, patch in override.categories.items():
            categories[name] = _merge_category(categories.get(name), patch)
        for name, patch in override.rules.items():
            rules[name] = _merge_rule(rules.get(name), patch)
        thresholds = _merge_thresholds(thresholds, override.thresholds)
        if override.locale is not None:
            merged_locale = locale.model_dump()
            for key, value in override.locale.model_dump().items():
                if value:
                    merged_locale[key] = value
            locale = LocaleSettings.model_validate(merged_locale)
        if override.vale is not None:
            merged = vale.model_dump()
            for key, value in override.vale.model_dump().items():
                if value is not None:
                    merged[key] = value
            vale = ValeSettings.model_validate(merged)

    return ResolvedConfig(
        path=file_path,
        profile=profile,
        categories=categories,
        rules=rules,
        thresholds=thresholds,
        vale=vale,
        locale=locale,
        applied_overrides=applied,
    )


def profile_thresholds(profile: Profile) -> Thresholds:
    """Document gates per tier.

    Density budgets, not zero-tolerance: a long document earns proportionally
    more findings. `min_score` is deliberately absent at relaxed, where the score
    is reported for information and gates nothing.
    """
    if profile is Profile.STRICT:
        return Thresholds(
            max_total_per_100_words=1.5, max_errors=0, min_score=85.0
        )
    if profile is Profile.NORMAL:
        return Thresholds(
            max_total_per_100_words=3.0, max_errors=0, min_score=70.0
        )
    return Thresholds(max_total_per_100_words=8.0, max_errors=None, min_score=None)
