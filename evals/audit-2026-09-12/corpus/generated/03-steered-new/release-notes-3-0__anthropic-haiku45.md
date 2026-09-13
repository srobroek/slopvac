# confparse v3.0 Release Notes

## Breaking changes

**`load()` renamed to `parse()`**

Replace all calls to `load()` with `parse()`. The function signature and behavior remain unchanged.

**YAML anchor support removed**

YAML anchors (`&` and `*`) are no longer recognized. Remove anchors from your YAML configuration files. If you used anchors to avoid duplication, use environment-variable interpolation (see New features) or repeat the values.

## New features

**Schema validation from JSON Schema**

Pass a JSON Schema file path to `parse()` via the `schema` parameter. The parser validates the configuration against the schema and raises an exception if validation fails.

**Environment-variable interpolation**

The parser expands `${VAR}` tokens with the value of the environment variable `VAR`. If `VAR` is not set, the parser raises an exception.

## Fixes

**Parser no longer crashes on an empty file**

An empty configuration file now returns an empty result instead of crashing.

**Duplicate keys now raise an exception**

Previous versions silently used the last value when a key appeared twice. The parser now raises an exception to help you find configuration errors.
