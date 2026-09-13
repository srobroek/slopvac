# confparse v3.0 Release Notes

## Breaking Changes

**YAML anchors are no longer supported.**
Remove anchor definitions (e.g., `&default_values`) and anchor references (e.g., `*default_values`) from your YAML files.
Merge mapping keys explicitly in your configuration instead.

**`load()` was renamed to `parse()`.**
Update all calls from `confparse.load(file)` to `confparse.parse(file)`.

## New Features

**Schema validation with JSON Schema.**
Pass a schema file path to `parse(..., schema="schema.json")` to validate configuration against your JSON Schema.
Validation errors name the field and the constraint violation.

**Environment-variable interpolation.**
Use `${VAR_NAME}` syntax in configuration files to insert environment variables at parse time.
If the variable is not set, parsing raises an error and names the missing variable.

## Fixed

**Empty configuration files no longer crash the parser.**
An empty file now returns an empty configuration object.

**Duplicate keys now raise an error.**
Previously, a duplicate key silently took the last value in the file.
Parsing now halts and reports the key name and line number of the first duplicate.

## Upgrade

1. Replace all `load()` calls with `parse()`.
2. Remove YAML anchors from your configuration files.
3. Test your configuration files with v3.0 to catch any duplicate keys or missing environment variables.
