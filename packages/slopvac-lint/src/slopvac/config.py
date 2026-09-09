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

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any

import pathspec
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

CONFIG_NAMES = ("slopvac.toml", ".slopvac.toml")
PYPROJECT = "pyproject.toml"


class Severity(str, Enum):
    """A finding's weight. `off` is a level rather than a deletion so that a
    disabled rule still resolves, and `slopvac rules` can report it as off."""

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
    without restating the others.

    A bare severity string stands in for the whole table, as it does for a rule:

        [categories]
        prose-scope = "warning"
    """

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _accept_bare_severity(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"severity": data}
        return data

    severity: Severity | None = Field(
        default=None,
        description="The level every rule in this category reports at. Promotes as "
        "well as demotes: `severity = 'error'` makes a suggestion blocking, and "
        "`severity = 'warning'` takes an error off the gate. A per-rule "
        '[rules."cat.rule"] entry still wins over this.',
    )
    minimum_severity: Severity | None = Field(
        default=None,
        description="Lowest level inherited rules in this category may report at. "
        "A per-rule override remains the narrowest setting.",
    )
    minimum_severity: Severity | None = Field(
        default=None,
        description="Lowest level inherited rules in this category may report at. "
        "A per-rule override remains the narrowest setting.",
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


class RuleSettings(BaseModel):
    """Per-rule override. `severity = "off"` is the documented way to disable.

    SEVERITY IS THE ONLY FIELD, so a bare string is accepted in its place:

        [rules]
        "prose-format.no-unicode-dash" = "off"

    which is the same thing as the two-line table form. The shorthand exists
    because setting one rule's severity is the dominant edit anyone makes to this
    file, and the table form costs a quoted header plus a key plus a blank line
    for one decision -- 90 lines for 30 tuned rules.

    There is deliberately NO per-rule `weight`. It used to be declared here,
    validated, and merged through all three config layers while never being read
    by the scorer: `weight` reaches the score only from `CategorySettings`. A knob
    that accepts a number and discards it is worse than no knob, and per-rule
    weight cannot be calibrated anyway without stating whether it subdivides its
    category's share or adds to the global pool.
    """

    model_config = ConfigDict(extra="forbid")

    severity: Severity | None = None

    @model_validator(mode="before")
    @classmethod
    def _accept_bare_severity(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"severity": data}
        return data


class Thresholds(BaseModel):
    """Document-level gates, evaluated after every finding is collected.

    These are the numbers the CI action reports on. `max_total_per_100_words` is
    the headline severity-weighted density budget; the others catch a document
    that passes on density while failing on a single unacceptable finding.
    """

    model_config = ConfigDict(extra="forbid")

    max_total_per_100_words: float | None = Field(
        default=None,
        ge=0,
        description="Severity-weighted error and warning density per 100 words; "
        "errors count 1.0 and warnings 0.5.",
    )
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


class VocabularySettings(BaseModel):
    """The word blocklist. OFF unless a project points at a file.

    No default wordlist, and the absence is the design. This package used to ship
    an extracted ASD-STE100 dictionary and enforce it as an ALLOWLIST, which made
    every word outside 859 approved ones a finding: 51% of all findings at
    `strict` on an 8-document corpus, driving documents with zero errors to a score
    of 0.0. Half those hits were words with no dictionary entry at all, so no
    override could reach them.

    A wordlist is a project's editorial position, so it comes from the project. The
    only sound default is nothing -- see `vocabulary.py` for the full measurement,
    and `examples/blocklist.toml` for a starting file.
    """

    model_config = ConfigDict(extra="forbid")

    path: Path | None = Field(
        default=None,
        description="Path to a blocklist of words this project refuses, relative "
        "to the config file. TOML, YAML, or JSON; every entry needs a `word`, a "
        "`pos`, and a `reason`. Unset means the vocabulary rules do not run.",
    )


class ValeSettings(BaseModel):
    """The Vale sub-gate. Vale owns the regex layer for the styles already
    published from this repo; slopvac owns scoring, tiers, and the rules Vale
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

    WHY AN ARRAY OF BLOCKS rather than one table keyed by glob. A table
    (`[overrides."docs/**"]`) reads better, and TOML would reject a duplicate key
    for free. It cannot express the case this list exists for: a scope is often
    several patterns, at least one of them a negation, and `docs/**` plus
    `!docs/generated/**` is one scope with one set of settings, not two scopes.
    Keying by glob would force that into two blocks whose settings must be kept
    in agreement by hand.

    So the block is the unit and `files` is a list. What TOML would have given
    for free is done in `Config._reject_duplicate_scopes` instead.
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
    #: A blocklist is an editorial position, and a vendored subtree does not share
    #: the project's. Overridable for that reason: without it the only options are
    #: one wordlist for the whole repository or none.
    vocabulary: VocabularySettings | None = None
    _spec: pathspec.PathSpec = PrivateAttr()

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
        spec: pathspec.PathSpec = self._spec
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
    vocabulary: VocabularySettings = Field(default_factory=VocabularySettings)
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
    _exclude_spec: pathspec.PathSpec = PrivateAttr()

    @model_validator(mode="after")
    def _compile_exclude(self) -> Config:
        object.__setattr__(
            self,
            "_exclude_spec",
            pathspec.PathSpec.from_lines("gitwildmatch", self.exclude),
        )
        return self

    @model_validator(mode="after")
    def _reject_duplicate_scopes(self) -> Config:
        """Two blocks with the same `files` are an error.

        Because `[[overrides]]` is an array of tables, TOML cannot reject this the
        way it rejects a duplicate table key -- and duplicating a scope is never
        what an author means. It reads as two independent decisions, and resolves
        as one: the later block wins field by field, so a setting present in the
        first and absent in the second survives while a setting present in both
        does not. Somebody editing the first block then sees no effect on the
        settings that collide, and an effect on the ones that do not.

        Compared as a SET, so reordering the patterns inside a block is the same
        scope. Patterns are normalised only by stripping surrounding whitespace:
        `docs/**` and `docs/**/` are different globs to pathspec, and claiming
        otherwise here would be a second, quieter guess.
        """
        seen: dict[frozenset[str], int] = {}
        for index, override in enumerate(self.overrides):
            key = frozenset(pattern.strip() for pattern in override.files)
            if key in seen:
                raise ValueError(
                    f"overrides[{index}] repeats the scope of "
                    f"overrides[{seen[key]}] ({', '.join(sorted(key))}). Merge "
                    f"them into one block: two blocks with the same scope resolve "
                    f"field by field, so the earlier one silently loses only the "
                    f"settings they share."
                )
            seen[key] = index
        return self

    def is_excluded(self, relative_path: str) -> bool:
        spec: pathspec.PathSpec = self._exclude_spec
        return spec.match_file(relative_path)

    def blocklist_path(self) -> Path | None:
        """The project-wide blocklist. See `resolve_blocklist_path`."""
        return resolve_blocklist_path(self.vocabulary, self.root)


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
    vocabulary: VocabularySettings = Field(default_factory=VocabularySettings)
    applied_overrides: list[str] = Field(
        default_factory=list,
        description="Which override globs matched, in order. Reported by "
        "`--explain-config` so a surprising result is traceable.",
    )
    provenance: dict[str, str] = Field(
        default_factory=dict,
        description="For each setting that any layer touched, WHICH layer set the "
        "value that survived. See `resolve_for`.",
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


def resolve_blocklist_path(
    vocabulary: VocabularySettings, root: Path | None
) -> Path | None:
    """A configured blocklist, resolved against the config file's directory.

    Relative to the CONFIG, not to the working directory: `path =
    "docs/blocklist.toml"` has to mean the same file whether the linter runs from
    the repo root or from a subdirectory, or a CI run and a local run disagree
    about what the gate is. An `[[overrides]]` block resolves against the same
    root, since the override lives in the same file.
    """
    configured = vocabulary.path
    if configured is None:
        return None
    if configured.is_absolute():
        return configured
    return ((root or Path.cwd()) / configured).resolve()


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

    A CASCADE IN FILE ORDER, NOT STRICTEST-WINS AND NOT MOST-SPECIFIC-WINS. Every
    matching block applies, in the order it appears, and the last one to set a
    field owns that field. So `files = ["x.*"]` after `files = ["x.md"]` wins for
    `x.md` even though it is the broader pattern, and reordering the two blocks
    changes the result.

    That is the intended design, and specificity ranking was the alternative. It
    was rejected because there is no ordering on globs that a reader can predict:
    `docs/**` against `**/*.md` is not more or less specific, it is differently
    specific, and any rule that picks a winner there has to be memorised. File
    order is the one rule that needs no explanation and is visible in the file
    being read.

    STRICTEST-WINS was rejected separately, and more firmly. Under it a project
    could not RELAX anything -- a vendored subtree or a generated `docs/api/`
    could never be dialled down, because the stricter parent always won. Relaxing
    a subtree is the main reason overrides exist.

    What file order costs is discoverability, so this function records WHERE each
    surviving value came from in `provenance`. `--explain-config` prints it, which
    turns "why is this rule still on" into a lookup instead of an inference over
    every block in the file. `Config._reject_duplicate_scopes` covers the case
    where two blocks share a scope outright; overlap between DIFFERENT globs is
    legitimate and stays legal.

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

    # Names the layer in `provenance`, so the label a reader sees is the same
    # string `--explain-config` prints and the same index the duplicate-scope and
    # unknown-name errors use.
    def label(index: int | None, override: Override | None = None) -> str:
        if index is None or override is None:
            return "config"
        return f"overrides[{index}] ({', '.join(override.files)})"

    provenance: dict[str, str] = {}

    # Layer 1: the profile.
    profile = config.profile
    provenance["profile"] = f"profile default ({profile.value})"
    matching = [(i, o) for i, o in enumerate(config.overrides) if o.matches(relative)]
    for index, override in matching:
        if override.profile is not None:
            profile = override.profile
            provenance["profile"] = label(index, override)

    defaults = profile_defaults(profile)
    categories = {name: settings.model_copy() for name, settings in defaults.items()}
    rules: dict[str, RuleSettings] = {}
    thresholds = _merge_thresholds(profile_thresholds(profile), config.thresholds)
    vale = config.vale.model_copy()
    locale = config.locale.model_copy()
    vocabulary = config.vocabulary.model_copy()

    # Layer 2: the top-level tables.
    for name, patch in config.categories.items():
        categories[name] = _merge_category(categories.get(name), patch)
        provenance[f"categories.{name}"] = label(None)
    for name, patch in config.rules.items():
        rules[name] = _merge_rule(rules.get(name), patch)
        provenance[f"rules.{name}"] = label(None)
    # Compared against a DEFAULT `Thresholds`, not against emptiness: the model has
    # non-None field defaults, so a truthiness test credited the config file for
    # thresholds it never mentioned and the profile actually set.
    if config.thresholds.model_dump(exclude_none=True) != Thresholds().model_dump(
        exclude_none=True
    ):
        provenance["thresholds"] = label(None)
    if config.vocabulary.path is not None:
        provenance["vocabulary"] = label(None)

    # Layer 3: every matching override, in file order. Each assignment to
    # `provenance` overwrites the previous one, which is exactly the precedence
    # being recorded: the last writer is the winner.
    applied: list[str] = []
    for index, override in matching:
        applied.extend(override.files)
        where = label(index, override)
        for name, patch in override.categories.items():
            categories[name] = _merge_category(categories.get(name), patch)
            provenance[f"categories.{name}"] = where
        for name, patch in override.rules.items():
            rules[name] = _merge_rule(rules.get(name), patch)
            provenance[f"rules.{name}"] = where
        if override.thresholds is not None:
            thresholds = _merge_thresholds(thresholds, override.thresholds)
            provenance["thresholds"] = where
        if override.locale is not None:
            merged_locale = locale.model_dump()
            for key, value in override.locale.model_dump().items():
                if value:
                    merged_locale[key] = value
            locale = LocaleSettings.model_validate(merged_locale)
            provenance["locale"] = where
        if override.vale is not None:
            merged = vale.model_dump()
            for key, value in override.vale.model_dump().items():
                if value is not None:
                    merged[key] = value
            vale = ValeSettings.model_validate(merged)
            provenance["vale"] = where
        if override.vocabulary is not None and override.vocabulary.path is not None:
            vocabulary = override.vocabulary.model_copy()
            provenance["vocabulary"] = where

    return ResolvedConfig(
        path=file_path,
        profile=profile,
        categories=categories,
        rules=rules,
        thresholds=thresholds,
        vale=vale,
        locale=locale,
        vocabulary=vocabulary,
        applied_overrides=applied,
        provenance=provenance,
    )


def profile_thresholds(profile: Profile) -> Thresholds:
    """Document gates per tier.

    Density budgets, not zero-tolerance: a long document earns proportionally
    more findings. `min_score` is deliberately absent at relaxed, where the score
    is reported for information and gates nothing.
    """
    if profile is Profile.STRICT:
        return Thresholds(max_total_per_100_words=1.5, max_errors=0, min_score=85.0)
    if profile is Profile.NORMAL:
        return Thresholds(max_total_per_100_words=3.0, max_errors=0, min_score=70.0)
    return Thresholds(max_total_per_100_words=8.0, max_errors=None, min_score=None)
