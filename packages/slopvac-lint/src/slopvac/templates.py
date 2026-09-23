"""The project configuration written by ``slopvac init``."""

STARTER_CONFIG = """\
# Inspect a file's settings: slopvac lint --explain-config README.md
# Inspect a rule: slopvac explain <category>.<rule>
# Agent workflow: slopvac prime
# Matching path overrides apply in order, one field at a time.
profile = "{profile}"

# These paths do not participate in ordinary directory scans.
# Keep top-level settings above the first TOML table header.
exclude = [
  "**/node_modules/**",
  "**/apm_modules/**",
  "**/.venv/**",
  "**/dist/**",
  "**/build/**",
  "**/CHANGELOG.md",
]

[thresholds]
max_errors = 0
# max_warnings = 10
# max_total_per_100_words = 3.0
# min_score = 70

[locale]
default = "en-US"        # en-US | en-GB | und (no spelling check)
# allow = ["Colour", "OrganisationId"]

# Optional project word blocklist, relative to this configuration file.
# Entries need word, pos, and reason. TOML, YAML, and JSON are supported.
# Without a blocklist, other word-choice and spelling rules still run.
# [vocabulary]
# path = "docs/blocklist.toml"

# A category setting applies to its rules; a per-rule setting is narrower.
# [categories.prose-promotion]
# severity = "warning"
# [rules."prose-craft.relative-date"]
# severity = "error"

# Each matching override changes only the fields it supplies.
# [[overrides]]
# files = ["docs/reference/**/*.md", "runbooks/**/*.md"]
# profile = "strict"

# Consumer-document history rules do not apply to decision records.
# [[overrides]]
# files = ["specs/**/*.md", "docs/adr/**/*.md", "**/CONTRIBUTING.md"]
# [overrides.categories.prose-scope]
# severity = "off"
# [overrides.categories.docs-discipline]
# severity = "off"

# Vale executes most deterministic rules compiled from Slopvac's catalog.
# Install Vale 3.15 or later and put it on PATH for a complete check.
# Missing Vale leaves selected Vale-backed rules UNCHECKED and returns exit 2.
[vale]
enabled = true
# binary = "vale"
"""
