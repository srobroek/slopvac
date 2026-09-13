# confparse v3.0 Release Notes

## Breaking changes

- YAML anchor support is removed. Files using `&anchor` and `*alias` fail to parse; inline the referenced values instead.
- `load()` is renamed to `parse()`. Update every call site before upgrading.

## New features

- Schema validation loads a JSON Schema file and validates the parsed configuration against it.
- `${VAR}` syntax in a config value interpolates the value of the named environment variable.

## Fixes

- Parsing an empty file no longer crashes; it returns an empty configuration object.
- A duplicate key in a config file now raises an error instead of silently keeping the last value. Remove the duplicate key from the file to parse it.

## Upgrade steps

1. Replace every `load()` call with `parse()`.
2. Remove YAML anchors and aliases from your config files; replace each alias with the value it referenced.
3. Search your config files for duplicate keys and remove the extras; `parse()` raises on the first duplicate it finds.
