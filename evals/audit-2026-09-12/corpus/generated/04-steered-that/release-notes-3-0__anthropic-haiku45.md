# confparse v3.0.0

## Breaking Changes

### `load()` renamed to `parse()`

The `load()` function is now `parse()`. This change aligns the API with functions that read from strings and files uniformly: `parse()` accepts a file path or file object, and `parse_string()` accepts raw configuration text.

**Migration:** Replace `load(path)` with `parse(path)` in your code.

### YAML anchor support removed

confparse no longer processes YAML anchors (`&` and `*`). The library now focuses on portable configuration idioms and drops this YAML-specific feature to reduce parsing complexity and avoid subtle resolution bugs.

**Migration:** Expand anchors in your YAML files before passing them to confparse, or switch to environment-variable interpolation (see below).

## New Features

### Schema validation with JSON Schema

Pass a JSON Schema file to validate configuration structure on load. Mismatches raise an error with the first violation.

```python
conf = confparse.parse("config.yaml", schema="schema.json")
```

### Environment-variable interpolation

Reference environment variables in configuration files using `${VAR}` syntax. The parser expands each reference to the variable's value at parse time. If the variable is not set, parsing raises an error.

```yaml
database_url: ${DATABASE_URL}
api_key: ${API_KEY}
```

## Fixes

### Crash on empty file

confparse no longer crashes when parsing an empty configuration file. Empty files now return an empty configuration object.

### Duplicate-key detection

Duplicate keys now raise an error instead of silently using the last value. This catches typos and configuration mistakes early.
