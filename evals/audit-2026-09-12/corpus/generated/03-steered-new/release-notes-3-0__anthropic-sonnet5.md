# confparse v3.0 Release Notes

## Breaking changes

- `load()` is renamed to `parse()`. Update all call sites: `confparse.load(path)` becomes `confparse.parse(path)`.
- YAML anchor support is removed. Files using `&anchor` and `*alias` syntax fail to parse; expand anchors into literal values before upgrading.

## New features

- Schema validation: pass a JSON Schema file path to `parse(path, schema=schema_path)` to validate config structure and types at load time.
- Environment-variable interpolation: `${VAR}` in a config value is replaced with the value of the `VAR` environment variable at parse time.

## Fixes

- Parsing an empty file no longer crashes; it returns an empty config object.
- Duplicate keys in a config file now raise `DuplicateKeyError` instead of silently keeping the last value. Remove duplicate keys from existing config files before upgrading.

## Upgrade steps

1. Replace every `confparse.load(...)` call with `confparse.parse(...)`.
2. Search config files for `&` and `*` YAML anchor syntax and inline the referenced values.
3. Search config files for duplicate keys within the same mapping and remove the duplicates.
4. Re-run your test suite against the parsed output to confirm behavior after the upgrade.
