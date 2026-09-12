# confparse v3.0 Release Notes

This release includes two breaking changes, two new features, and two bug fixes. Read the migration steps below before upgrading.

## Breaking Changes

### `load()` renamed to `parse()`

The primary entry point has been renamed from `load()` to `parse()` for clarity. `load()` no longer exists.

**Before:**

```python
config = confparse.load("config.yaml")
```

**After:**

```python
config = confparse.parse("config.yaml")
```

Update every call site in your codebase before upgrading.

### YAML anchor support removed

YAML anchors and aliases (`&anchor` / `*anchor`) are no longer resolved. Files that rely on anchors will now either raise a parse error or load with the alias left as a literal string, depending on your YAML backend's behavior.

If you use anchors to avoid duplicating config values, replace them with one of:

- Explicit duplication of the values.
- The new environment-variable interpolation (see below), if the shared value is better expressed as an env var.
- A pre-processing step in your build pipeline that expands anchors before confparse reads the file.

Search your config files for `&` and `*` markers and rewrite them before upgrading.

## New Features

### Schema validation from a JSON Schema file

You can now validate a parsed config against a JSON Schema file:

```python
config = confparse.parse("config.yaml", schema="config.schema.json")
```

If the config does not conform to the schema, `parse()` raises a validation error describing the failing field and constraint. Schema validation is optional; omit the `schema` argument to skip it.

### `${VAR}` environment-variable interpolation

String values may now reference environment variables using `${VAR}` syntax:

```yaml
database:
  host: ${DB_HOST}
  password: ${DB_PASSWORD}
```

At parse time, each `${VAR}` reference is replaced with the value of the corresponding environment variable. Referencing an unset environment variable raises an error rather than silently substituting an empty string.

## Fixes

- **Empty file crash**: Parsing an empty config file previously raised an unhandled exception. It now returns an empty configuration object.
- **Duplicate keys**: Duplicate keys in a config file previously failed silently, with the last occurrence overwriting earlier ones. `parse()` now raises an error identifying the duplicated key and its locations, so silent misconfiguration can no longer slip through.

## Upgrade Checklist

1. Replace all `confparse.load()` calls with `confparse.parse()`.
2. Remove or rewrite any YAML anchors/aliases in your config files.
3. Check your config files for duplicate keys; `parse()` will now reject them.
4. Optionally, add a JSON Schema file and pass it via the `schema` argument to validate configs going forward.
5. Optionally, replace duplicated literal values with `${VAR}` interpolation where an environment variable is a better fit.
