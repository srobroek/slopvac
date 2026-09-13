# confparse v3.0

Version 3.0 changes configuration parsing behavior and requires updates for existing users.

## Breaking changes

- Replace every `load()` call with `parse()`.
- Replace YAML anchors with explicit configuration values because version 3.0 does not support anchors.
- Remove duplicate keys because version 3.0 raises an error instead of retaining the last value.

## New features

- `confparse` can validate configuration against a JSON Schema file.
- `confparse` interpolates environment variables referenced with `${VAR}` syntax.

## Fixes

- Parsing an empty configuration file no longer crashes.
- Duplicate keys now raise an error instead of silently taking the last value.

## Upgrade checklist

1. Replace `load()` calls with `parse()`.
2. Expand YAML anchors into explicit values.
3. Remove duplicate keys from every configuration file.
4. Define each environment variable referenced by `${VAR}`.
