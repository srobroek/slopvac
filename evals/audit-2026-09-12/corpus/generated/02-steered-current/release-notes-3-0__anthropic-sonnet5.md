# confparse v3.0 release notes

## Breaking changes

- `load()` is renamed to `parse()`. Update every call site: `confparse.load(path)` becomes `confparse.parse(path)`.
- YAML anchor and alias support (`&anchor`, `*alias`) is removed. Replace anchors with explicit, repeated values in your config files.

## New features

- Schema validation: pass a JSON Schema file path to `parse(path, schema=schema_path)` to validate config against it. Validation raises `confparse.SchemaError` on mismatch.
- Environment-variable interpolation: a value containing `${VAR}` resolves to the value of the `VAR` environment variable at parse time. An unset `VAR` raises `confparse.InterpolationError`.

## Fixes

- `parse()` no longer crashes on an empty file; it returns an empty config object.
- Duplicate keys in a config file raise `confparse.DuplicateKeyError` instead of silently keeping the last value. Remove duplicate keys from existing config files before upgrading.

## Upgrade steps

1. Replace `load(` with `parse(` throughout your codebase.
2. Remove YAML anchors and aliases from config files; inline the repeated values.
3. Run your config files through `parse()` once before deploying, to surface any duplicate-key errors.
4. Add a schema file and pass it via `schema=` where you want validation.
