"""Spelling locales.

WHY THIS IS DATA AND NOT A RULE. Spelling is the one check whose correct answer
depends entirely on the project, not on the prose: `colour` is a defect in a
`en-US` document and correct in a `en-GB` one. A rule file cannot express that,
because a rule's `substitutions` map has one direction.

So locales live here as a table of VARIANT SETS -- each row is one word with its
spelling in every locale we know -- and the check is generated per run from the
project's `locale` setting. Adding `en-AU` or `en-CA` means adding a column, not
writing a second rule.

    [locale]
    default = "en-GB"

    [[overrides]]
    files = ["docs/api/**"]
    [overrides.locale]
    default = "en-US"

DIRECTION IS DERIVED, NOT DECLARED. Given a target locale, every OTHER locale's
spelling of the same word becomes a finding with the target's spelling as the
replacement. One table serves every direction, so `en-GB` -> `en-US` and
`en-US` -> `en-GB` cannot disagree.

ASD-STE100 rule 1.14 asks for American spelling. That is expressed as
`locale = "en-US"`, which is the `strict` profile's default rather than a rule
nobody can turn off: a British English project running the STE tier is a
legitimate configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Known locales. `und` is the escape hatch: it disables the spelling check without
# disabling the rest of the category.
LOCALES = ("en-US", "en-GB", "und")
DEFAULT_LOCALE = "en-US"

# Every row is one word in each locale. A locale absent from a row shares the
# spelling of the row's first entry, which keeps the table short.
#
# Suffix families are generated below rather than enumerated, because an inflected
# form missing from a hand-written map is the exact bug that shipped in the first
# revision of this rule: `initialise` was caught and `initialises` was not.
_VARIANTS: list[dict[str, str]] = [
    # -ise / -ize family. Base forms only; inflections are generated.
    {"en-US": "organize", "en-GB": "organise"},
    {"en-US": "recognize", "en-GB": "recognise"},
    {"en-US": "initialize", "en-GB": "initialise"},
    {"en-US": "serialize", "en-GB": "serialise"},
    {"en-US": "deserialize", "en-GB": "deserialise"},
    {"en-US": "normalize", "en-GB": "normalise"},
    {"en-US": "authorize", "en-GB": "authorise"},
    {"en-US": "customize", "en-GB": "customise"},
    {"en-US": "optimize", "en-GB": "optimise"},
    {"en-US": "synchronize", "en-GB": "synchronise"},
    {"en-US": "prioritize", "en-GB": "prioritise"},
    {"en-US": "summarize", "en-GB": "summarise"},
    {"en-US": "categorize", "en-GB": "categorise"},
    {"en-US": "minimize", "en-GB": "minimise"},
    {"en-US": "maximize", "en-GB": "maximise"},
    {"en-US": "sanitize", "en-GB": "sanitise"},
    {"en-US": "parameterize", "en-GB": "parameterise"},
    {"en-US": "containerize", "en-GB": "containerise"},
    {"en-US": "virtualize", "en-GB": "virtualise"},
    {"en-US": "tokenize", "en-GB": "tokenise"},
    {"en-US": "randomize", "en-GB": "randomise"},
    {"en-US": "finalize", "en-GB": "finalise"},
    {"en-US": "specialize", "en-GB": "specialise"},
    {"en-US": "standardize", "en-GB": "standardise"},
    {"en-US": "utilize", "en-GB": "utilise"},
    {"en-US": "apologize", "en-GB": "apologise"},
    {"en-US": "emphasize", "en-GB": "emphasise"},
    {"en-US": "analyze", "en-GB": "analyse"},
    {"en-US": "paralyze", "en-GB": "paralyse"},
    {"en-US": "catalyze", "en-GB": "catalyse"},
    # -ization / -isation nouns.
    {"en-US": "organization", "en-GB": "organisation"},
    {"en-US": "authorization", "en-GB": "authorisation"},
    {"en-US": "initialization", "en-GB": "initialisation"},
    {"en-US": "serialization", "en-GB": "serialisation"},
    {"en-US": "normalization", "en-GB": "normalisation"},
    {"en-US": "optimization", "en-GB": "optimisation"},
    {"en-US": "synchronization", "en-GB": "synchronisation"},
    {"en-US": "customization", "en-GB": "customisation"},
    {"en-US": "sanitization", "en-GB": "sanitisation"},
    {"en-US": "tokenization", "en-GB": "tokenisation"},
    {"en-US": "virtualization", "en-GB": "virtualisation"},
    {"en-US": "containerization", "en-GB": "containerisation"},
    {"en-US": "parameterization", "en-GB": "parameterisation"},
    {"en-US": "standardization", "en-GB": "standardisation"},
    {"en-US": "specialization", "en-GB": "specialisation"},
    {"en-US": "prioritization", "en-GB": "prioritisation"},
    {"en-US": "categorization", "en-GB": "categorisation"},
    # -or / -our.
    {"en-US": "color", "en-GB": "colour"},
    {"en-US": "behavior", "en-GB": "behaviour"},
    {"en-US": "favor", "en-GB": "favour"},
    {"en-US": "flavor", "en-GB": "flavour"},
    {"en-US": "honor", "en-GB": "honour"},
    {"en-US": "labor", "en-GB": "labour"},
    {"en-US": "neighbor", "en-GB": "neighbour"},
    {"en-US": "rumor", "en-GB": "rumour"},
    {"en-US": "endeavor", "en-GB": "endeavour"},
    # -er / -re.
    {"en-US": "center", "en-GB": "centre"},
    {"en-US": "meter", "en-GB": "metre"},
    {"en-US": "liter", "en-GB": "litre"},
    {"en-US": "fiber", "en-GB": "fibre"},
    {"en-US": "theater", "en-GB": "theatre"},
    # -se / -ce nouns.
    {"en-US": "license", "en-GB": "licence"},
    {"en-US": "defense", "en-GB": "defence"},
    {"en-US": "offense", "en-GB": "offence"},
    {"en-US": "pretense", "en-GB": "pretence"},
    # -og / -ogue.
    {"en-US": "catalog", "en-GB": "catalogue"},
    {"en-US": "dialog", "en-GB": "dialogue"},
    {"en-US": "analog", "en-GB": "analogue"},
    # Doubled consonants before a suffix.
    {"en-US": "canceled", "en-GB": "cancelled"},
    {"en-US": "canceling", "en-GB": "cancelling"},
    {"en-US": "labeled", "en-GB": "labelled"},
    {"en-US": "labeling", "en-GB": "labelling"},
    {"en-US": "modeled", "en-GB": "modelled"},
    {"en-US": "modeling", "en-GB": "modelling"},
    {"en-US": "traveled", "en-GB": "travelled"},
    {"en-US": "traveling", "en-GB": "travelling"},
    {"en-US": "signaled", "en-GB": "signalled"},
    {"en-US": "signaling", "en-GB": "signalling"},
    {"en-US": "totaled", "en-GB": "totalled"},
    {"en-US": "fueled", "en-GB": "fuelled"},
    {"en-US": "marveled", "en-GB": "marvelled"},
    # Miscellaneous.
    {"en-US": "artifact", "en-GB": "artefact"},
    {"en-US": "gray", "en-GB": "grey"},
    {"en-US": "aging", "en-GB": "ageing"},
    {"en-US": "acknowledgment", "en-GB": "acknowledgement"},
    {"en-US": "judgment", "en-GB": "judgement"},
    {"en-US": "fulfill", "en-GB": "fulfil"},
    {"en-US": "installment", "en-GB": "instalment"},
    {"en-US": "skillful", "en-GB": "skilful"},
    {"en-US": "enrollment", "en-GB": "enrolment"},
    # `program` and `disk` are NOT locale variants in this domain: the computing
    # sense is `program` and `disk` in every locale, and `programme` / `disc` mean
    # a schedule and an optical medium. Listing them made the en-GB direction
    # rewrite correct technical prose.
    #
    # `check` / `cheque` is the same trap and worse: `cheque` is only the banking
    # sense, so the pair rewrote "the build checks" into "the build cheques". It
    # failed the generated rule's own example, which is how it was caught.
    {"en-US": "toward", "en-GB": "towards"},
    {"en-US": "backward", "en-GB": "backwards"},
    {"en-US": "forward", "en-GB": "forwards"},
    # `whilst`, `amongst`, and `amidst` are DELETED, not moved. They are archaic
    # register rather than locale: `while`, `among`, and `amid` are all standard in
    # British English and are the forms British technical writing actually uses.
    # Listed as variants, the en-GB direction demanded `whilst` for every `while`,
    # which added findings to correct prose -- 3 on this project's own README -- and
    # pushed a document's score DOWN for being written plainly.
]

# Words that must never be rewritten regardless of locale, because the string is
# an identifier rather than prose. Doing this here rather than per-rule keeps the
# list in one place: every one of these is a real API surface.
#
# `program` and `disk` are absent from the variant table's practical effect for
# the same reason -- see IDENTIFIER_ALLOWLIST usage in build_spelling_rule.
IDENTIFIER_ALLOWLIST = (
    # CSS, DOM, and web platform APIs are American by specification.
    "color", "background-color", "border-color", "text-color", "currentColor",
    "colorScheme", "grayscale", "dialog", "analogWrite",
    # Common library and flag names.
    "normalize.css", "serializer", "deserializer", "normalizer", "tokenizer",
    "Analyzer", "analyzer", "optimizer", "sanitizer", "organization",
    "--color", "--no-color", "--optimize", "--normalize",
    # Programme/program: the computing sense is `program` in every locale.
    "program", "programs", "programming", "programmer", "programmatic",
)

# Suffixes generated for a base form. `-ise` verbs inflect regularly in both
# locales, so enumerating them by hand is what let `initialises` slip through.
_VERB_SUFFIXES = (("", ""), ("s", "s"), ("d", "d"), ("rs", "rs"))
_IZE_INFLECTIONS = ("", "s", "d", "rs")


@dataclass
class Locale:
    """One resolved spelling target."""

    tag: str
    substitutions: dict[str, str] = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return self.tag != "und" and bool(self.substitutions)


def _inflect(word: str) -> list[str]:
    """Generate the inflected forms of a base word.

    Only the regular patterns, and only where the result is unambiguous. A form
    this misses is a miss; a form it invents wrongly is a false finding on correct
    prose, so the rules are conservative.
    """
    forms = [word]
    if word.endswith("ize") or word.endswith("ise"):
        stem = word[:-1]  # organiz / organis
        forms += [f"{stem}es", f"{stem}ed", f"{stem}ing", f"{stem}er", f"{stem}ers"]
    elif word.endswith("yze") or word.endswith("yse"):
        stem = word[:-1]
        forms += [f"{stem}es", f"{stem}ed", f"{stem}ing", f"{stem}er", f"{stem}ers"]
    elif word.endswith(("or", "our", "er", "re", "og", "ogue")):
        forms += [f"{word}s"]
    elif word.endswith(("ion", "ment", "ance", "ence")):
        forms += [f"{word}s"]
    return forms


def resolve(tag: str) -> Locale:
    """Build the substitution map that rewrites every other locale into `tag`.

    Unknown tags return a disabled locale rather than raising: a typo in
    `locale.default` should not stop the other 200 rules from running, and the
    caller reports the tag as unchecked.
    """
    if tag not in LOCALES:
        return Locale(tag="und")
    if tag == "und":
        return Locale(tag="und")

    allowed = {w.lower() for w in IDENTIFIER_ALLOWLIST}
    substitutions: dict[str, str] = {}

    for row in _VARIANTS:
        target = row.get(tag)
        if target is None:
            continue
        for other_tag, other in row.items():
            if other_tag == tag or other == target:
                continue
            # `strict=False` on purpose. `_inflect` branches on the suffix, so two
            # words in the same row can return different numbers of forms
            # (`organise` takes the -ise branch, `program` the doubling one). The
            # short list is the one both share, and truncating to it pairs like with
            # like. `strict=True` would raise on a legitimate row.
            for source_form, target_form in zip(
                _inflect(other), _inflect(target), strict=False
            ):
                if source_form.lower() in allowed:
                    continue
                if source_form.lower() == target_form.lower():
                    continue
                substitutions[source_form] = target_form

    return Locale(tag=tag, substitutions=substitutions)


def build_spelling_rule(tag: str) -> dict | None:
    """A rule dictionary for the resolved locale, or None when disabled.

    Returned as data rather than a `Rule` so the loader validates it on the same
    path as a YAML rule: a generated rule that skips validation is a rule nobody
    checked.
    """
    locale = resolve(tag)
    if not locale.enabled:
        return None

    return {
        "id": "spelling",
        "name": f"Use {tag} spelling",
        "kind": "substitution",
        "severity": "warning",
        "message": f'Use the {tag} spelling "{{replacement}}".',
        "scope": "prose",
        "text_type": "any",
        "tiers": {"strict": "enforced", "normal": "enforced", "relaxed": "excluded"},
        "substitutions": locale.substitutions,
        "ignore_case": True,
        "exceptions": [
            "identifier-fidelity",
            "quotation",
            "code-span",
            "proper-noun",
            "api-name",
        ],
        "allowlist": list(IDENTIFIER_ALLOWLIST),
        "examples": _examples_for(tag),
        "provenance": {
            "source": "ASD-STE100",
            "ste_ref": "9:1.14",
            "note": (
                "Generated from the locale table rather than written as a rule, "
                "because the correct spelling depends on the project and a rule's "
                "substitution map has only one direction. Rule 1.14 asks for "
                "American spelling; that is `locale = \"en-US\"`, the default, "
                "rather than a rule a British English project cannot turn off."
            ),
        },
        "fix": f"Use the {tag} spelling.",
    }


def _examples_for(tag: str) -> list[dict[str, str]]:
    """Examples in the right direction for the target locale.

    Required, not decorative: the loader asserts every `bad` matches and every
    `good` does not, so a generated rule whose direction inverted would fail to
    load rather than silently rewrite prose backwards.
    """
    if tag == "en-US":
        return [
            {"bad": "The parser normalises the colour value.",
             "good": "The parser normalizes the color value."},
            {"bad": "The build cancelled the licence check.",
             "good": "The build canceled the license check."},
        ]
    if tag == "en-GB":
        return [
            {"bad": "The parser normalizes the color value.",
             "good": "The parser normalises the colour value."},
            {"bad": "The build canceled the license check.",
             "good": "The build cancelled the licence check."},
        ]
    return []
