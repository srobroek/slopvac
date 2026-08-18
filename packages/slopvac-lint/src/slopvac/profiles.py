"""Per-profile category defaults.

The tiers are NOT a monotonic ordering, and two inversions are deliberate:

  1. `orwell` passive-voice checking is ADVISORY at strict and ENFORCED at normal.
     Agentless passive is correct in a specification -- "the request is rejected
     with 400" holds for every conforming implementation, while "the server
     rejects the request" over-specifies and "you will receive a 400" mis-assigns
     the actor. Enforcing it in reference documentation manufactures noise, so the
     strictest profile is the one that relaxes it.

  2. `meta` (suppression validity) and the actor-attribution rules are enforced at
     EVERY profile including relaxed. The first is the contract that makes the rest
     auditable; the second guards attribution, which is the failure Orwell treats
     as most serious and which hides in exactly the informal registers `relaxed`
     covers.

Budgets are densities per 100 words, not counts, so a long document earns
proportionally more findings. A category with no budget entry is scored but never
gates on density alone.
"""

from __future__ import annotations

from .config import CategorySettings, Profile, Severity

# Every category the shipped ruleset defines. Kept here rather than derived from
# the YAML so that a profile is a complete, reviewable statement of policy: a new
# category that nobody assigned a budget to is visible as an omission.
_STRICT: dict[str, CategorySettings] = {
    # --- AI-slop layer: unchanged across strict and normal --------------------
    "ai-residue": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.5),
    "ai-tells-structure": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.3, weight=1.5),
    "ai-tells-register": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.3, weight=1.5),
    "ai-tells-formatting": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.5, weight=0.8),
    "ai-tells-content-shape": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.2, weight=1.5),
    # A figurative verb has a literal alternative in any register, but the
    # budget is looser than the other ai-tells bands: these are single-word
    # matches, so one metaphor-heavy paragraph spends a tight budget outright.
    "ai-tells-figurative": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.4, weight=1.0),
    "prose-inflation": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.3, weight=1.5),
    "prose-promotion": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.2, weight=1.2),
    "prose-agency": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.2),
    "prose-scope": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.3, weight=1.0),
    "prose-format": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.2, weight=0.8),
    "prose-craft": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.8, weight=1.0),
    "prose-density": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.5, weight=0.8),
    "prose-inclusive": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.0),
    "docs-discipline": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.2, weight=1.2),
    # --- Simplified Technical English: the strict profile is what STE is for ---
    "ste-words": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.5, weight=1.2),
    "ste-nouns": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.3, weight=1.0),
    "ste-verbs": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.2),
    "ste-sentences": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.5, weight=1.5),
    "ste-procedural": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.2),
    "ste-descriptive": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.0),
    "ste-safety": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.5),
    "ste-punctuation": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.5, weight=0.8),
    "ste-practices": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.5, weight=0.8),
    "ste-vocabulary": CategorySettings(severity=Severity.WARNING, max_per_100_words=2.0, weight=0.8),
    # --- Orwell ---------------------------------------------------------------
    "orwell": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.5),
    # Inversion 1: see the module docstring.
    "orwell-voice": CategorySettings(severity=Severity.WARNING, max_per_100_words=None, weight=0.5),
    # --- Referential consistency, sentence load, frozen verbs, register -------
    "prose-discipline": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.5),
    # Inversion 2: the audit contract, enforced everywhere.
    "meta": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.0),
}

_NORMAL: dict[str, CategorySettings] = {
    "ai-residue": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.5),
    "ai-tells-structure": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.6, weight=1.5),
    "ai-tells-register": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.6, weight=1.5),
    "ai-tells-formatting": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=0.8),
    "ai-tells-content-shape": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.5),
    "ai-tells-figurative": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.8, weight=1.0),
    "prose-inflation": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.6, weight=1.5),
    "prose-promotion": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=1.2),
    "prose-agency": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.8, weight=1.0),
    "prose-scope": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.6, weight=1.0),
    "prose-format": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.4, weight=0.8),
    "prose-craft": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=0.8),
    "prose-density": CategorySettings(severity=Severity.SUGGESTION, max_per_100_words=1.0, weight=0.5),
    "prose-inclusive": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.0),
    "docs-discipline": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.5, weight=1.0),
    # STE at normal keeps the readability rules and drops the dictionary
    # lockdown: the length, voice, and one-idea-per-sentence discipline is what
    # transfers to general prose, while a ~800-word approved vocabulary does not.
    "ste-words": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=0.8),
    "ste-nouns": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=0.8),
    "ste-verbs": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=0.8),
    "ste-sentences": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=1.0),
    "ste-procedural": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=0.8),
    "ste-descriptive": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=0.8),
    "ste-safety": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.2),
    "ste-punctuation": CategorySettings(severity=Severity.SUGGESTION, max_per_100_words=1.5, weight=0.5),
    "ste-practices": CategorySettings(severity=Severity.SUGGESTION, max_per_100_words=1.5, weight=0.5),
    # The approved-word check is off by default at normal. It is the single
    # noisiest rule against ordinary software prose and belongs to strict.
    "ste-vocabulary": CategorySettings(severity=Severity.OFF),
    "orwell": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.8, weight=1.5),
    "orwell-voice": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.5, weight=1.0),
    "prose-discipline": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.8, weight=1.5),
    "meta": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.0),
}

_RELAXED: dict[str, CategorySettings] = {
    # Only what harms a reader in loose prose. Everything else is off, not
    # demoted: a suggestion nobody acts on is noise that trains people to ignore
    # the tool.
    "ai-residue": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.5),
    "ai-tells-structure": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=1.0),
    "ai-tells-register": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=1.0),
    "ai-tells-formatting": CategorySettings(severity=Severity.OFF),
    "ai-tells-content-shape": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=1.0),
    # OFF, and every rule in it is `relaxed: excluded` anyway: a metaphor is a
    # register choice, and relaxed is the profile that grants register latitude.
    "ai-tells-figurative": CategorySettings(severity=Severity.OFF),
    "prose-inflation": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.5, weight=1.0),
    # Survives at relaxed, unlike the figurative band: the two rules kept here
    # are `relaxed: enforced` because puffery and strategy-deck vocabulary make
    # an unbacked claim, which is a defect in any register.
    "prose-promotion": CategorySettings(severity=Severity.WARNING, max_per_100_words=1.0, weight=1.0),
    "prose-agency": CategorySettings(severity=Severity.SUGGESTION, max_per_100_words=2.0, weight=0.5),
    "prose-scope": CategorySettings(severity=Severity.OFF),
    "prose-format": CategorySettings(severity=Severity.SUGGESTION, max_per_100_words=2.0, weight=0.3),
    "prose-craft": CategorySettings(severity=Severity.OFF),
    "prose-density": CategorySettings(severity=Severity.OFF),
    "prose-inclusive": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.0),
    "docs-discipline": CategorySettings(severity=Severity.OFF),
    "ste-words": CategorySettings(severity=Severity.OFF),
    "ste-nouns": CategorySettings(severity=Severity.OFF),
    "ste-verbs": CategorySettings(severity=Severity.OFF),
    # Sentence length survives at relaxed: an unreadable sentence is unreadable
    # in any register, and the cap is the cheapest comprehension win there is.
    "ste-sentences": CategorySettings(severity=Severity.SUGGESTION, max_per_100_words=2.5, weight=0.8),
    "ste-procedural": CategorySettings(severity=Severity.OFF),
    "ste-descriptive": CategorySettings(severity=Severity.OFF),
    "ste-safety": CategorySettings(severity=Severity.WARNING, max_per_100_words=0.0, weight=1.0),
    "ste-punctuation": CategorySettings(severity=Severity.OFF),
    "ste-practices": CategorySettings(severity=Severity.OFF),
    "ste-vocabulary": CategorySettings(severity=Severity.OFF),
    "orwell": CategorySettings(severity=Severity.WARNING, max_per_100_words=2.0, weight=1.0),
    "orwell-voice": CategorySettings(severity=Severity.OFF),
    "prose-discipline": CategorySettings(severity=Severity.WARNING, max_per_100_words=2.0, weight=1.0),
    "meta": CategorySettings(severity=Severity.ERROR, max_per_100_words=0.0, weight=1.0),
}

_PROFILES = {
    Profile.STRICT: _STRICT,
    Profile.NORMAL: _NORMAL,
    Profile.RELAXED: _RELAXED,
}


def profile_defaults(profile: Profile) -> dict[str, CategorySettings]:
    """Category settings for a profile. Copied, so a caller's merge cannot
    mutate the shipped table."""
    return {
        name: settings.model_copy()
        for name, settings in _PROFILES[profile].items()
    }


def genre_recommendation(genre: str) -> Profile:
    """Map a document genre to the profile that suits it.

    Used by the skill to recommend rather than ask: a runbook wants strict, a
    README wants normal, an issue comment wants relaxed.
    """
    strict = {"reference", "api-docs", "runbook", "spec", "procedure", "safety"}
    relaxed = {"issue", "comment", "note", "draft", "chat", "scratch"}
    if genre in strict:
        return Profile.STRICT
    if genre in relaxed:
        return Profile.RELAXED
    return Profile.NORMAL
