# confparse 3.0

Version 3.0 changes the parsing API and removes YAML anchor support.

## Upgrade steps

1. Replace each `load()` call with `parse()`.

   ```python
   # Before
   config = confparse.load("config.yaml")

   # Version 3.0
   config = confparse.parse("config.yaml")
   ```

2. If a YAML file defines anchors, replace each anchor and alias with explicit values.
3. Remove duplicate keys from configuration files before parsing them with version 3.0.

## Breaking changes

- Removed YAML anchor and alias support.
- Renamed `load()` to `parse()`.
- Changed duplicate-key handling to raise an error instead of retaining the last value.

## Added

- Added configuration validation from a JSON Schema file.
- Added `${VAR}` interpolation from environment variables.

## Fixed

- Parsing an empty file no longer crashes.
