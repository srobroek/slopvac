"""The starter config `slopvac-lint init` writes.

Written as a template rather than generated from the model so the comments carry
the reasoning. A config a reader cannot understand gets deleted wholesale the
first time it produces an unwanted finding.
"""

STARTER_CONFIG = '''\
# slopvac prose gate. Yours to edit; commit it.
#
# Resolution order, each layer patching the one above it PER FIELD:
#   1. the built-in profile below
#   2. the [categories] and [rules] tables in this file
#   3. every [[overrides]] block whose `files` glob matches, in order
#
# An override that sets only `severity` keeps the profile's threshold. Unlike a
# Vale rule line, a setting here belongs to the block it is written in, so
# appending to the end of this file cannot silently re-target it.
#
# Inspect what actually applies:  slopvac-lint lint --explain-config <file>
# Understand one rule:            slopvac-lint explain <category>.<rule>
# List everything:                slopvac-lint rules --profile {profile}

# strict  = technical documentation: reference, specs, API docs, runbooks
# normal  = general writing at a high bar: README, guides, ADRs
# relaxed = loose writing: notes, comments, drafts
profile = "{profile}"

[thresholds]
# Density budgets, not counts, so a long document earns proportionally more
# findings. Documents under 60 words are scored on absolute counts instead:
# one finding in a 20-word error message is 5.0 per 100 words and would fail
# every budget.
max_errors = 0
# max_total_per_100_words = 3.0
# min_score = 70

# --- Spelling ----------------------------------------------------------------
# The spelling check is generated from this setting, so one variant table serves
# every direction and en-US -> en-GB cannot disagree with en-GB -> en-US.
#
# ASD-STE100 asks for American spelling, which is why en-US is the default rather
# than a rule a British English project cannot turn off. `und` disables the
# spelling check and leaves the rest of its category running.
[locale]
default = "en-US"        # en-US | en-GB | und
# Words this project spells its own way whatever the locale. CSS and web platform
# identifiers are already protected, so this is for your own API surface.
# allow = ["Colour", "OrganisationId"]

# A locale can be set per path, which is what a translated docs tree needs.
# [[overrides]]
# files = ["docs/en-gb/**/*.md"]
# [overrides.locale]
# default = "en-GB"

# --- Categories --------------------------------------------------------------
# Turn one off, or demote it to advisory. A category cap LOWERS a rule's
# severity and never raises it, so setting `severity = "error"` here will not
# promote a suggestion into a gate failure.
#
# [categories.ste-vocabulary]
# enabled = false            # the approved-word check; off by default at normal
#
# [categories.prose-scope]
# severity = "warning"       # worth seeing, not worth blocking
#
# [categories.ai-tells-formatting]
# max_per_100_words = 2.0    # this project uses tables heavily

# --- Single rules ------------------------------------------------------------
# Give every override a reason. The next reader needs to know whether it holds.
#
# [rules."prose-format.no-unicode-dash"]
# severity = "off"           # house style uses real em dashes

# --- Path overrides ----------------------------------------------------------
# gitignore-style globs. First match does not win: every matching block applies
# in file order, so put the general case first and the specific case after.

# Reference material and runbooks earn the strict tier.
# [[overrides]]
# files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
# profile = "strict"

# A decision record exists to hold a decision and the measurement behind it, so
# the rules that ban that content elsewhere invert here.
# [[overrides]]
# files = ["specs/**/*.md", "docs/adr/**/*.md", "**/CONTRIBUTING.md"]
# profile = "normal"
# [overrides.categories.prose-scope]
# enabled = false
# [overrides.categories.docs-discipline]
# enabled = false

# Generated and vendored trees are not authored prose.
# [[overrides]]
# files = ["**/generated/**", "vendor/**"]
# [overrides.categories.ai-residue]
# enabled = false

# --- Vale sub-gate -----------------------------------------------------------
# Vale runs the upstream tbhb/vale-ai-tells package, which we do not fork. Our
# own rules run natively, so nothing is checked twice. When `vale` is absent the
# run reports those rules as UNCHECKED rather than passing them silently.
[vale]
enabled = true
# binary = "vale"
# config = ".vale.ini"

# Never linted.
exclude = [
  "**/node_modules/**",
  "**/apm_modules/**",
  "**/.venv/**",
  "**/dist/**",
  "**/build/**",
  # release-please generates this from commit subjects; its prose is not authored.
  "**/CHANGELOG.md",
]
'''
