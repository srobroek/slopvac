# confparse 3.0

## Breaking changes

- `load()` was renamed to `parse()`. Replace every `load()` call with `parse()`.
- confparse no longer supports YAML anchors. Replace anchors with explicit configuration values before upgrading.

## New features

- confparse validates configuration against a JSON Schema file.
- confparse interpolates `${VAR}` references with values from the environment.

## Fixes

- confparse no longer crashes when parsing an empty file.
- confparse raises an error for duplicate keys. Version 2.x silently retained the last value.

## Upgrade checklist

1. Replace every `load()` call with `parse()`.
2. Remove YAML anchors from configuration files.
3. Remove duplicate keys from configuration files.
4. Test `${VAR}` references with the required environment variables.
5. Validate configuration files against their JSON Schema files.
