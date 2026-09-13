# confparse v3.0

Version 3.0 contains breaking API and parsing changes for existing users.

## Breaking changes

- YAML anchor support was removed. Replace anchors and aliases with explicit YAML values before upgrading.
- The `load()` function was renamed to `parse()`. Replace every `load()` call with `parse()`.
- Duplicate keys now raise an error instead of retaining the last value. Remove duplicate keys from each configuration file.

```python
# Before
config = confparse.load("config.yaml")

# Version 3.0
config = confparse.parse("config.yaml")
```

## New features

- `confparse` can validate configuration values against a JSON Schema file.
- Configuration files can interpolate environment variables with `${VAR}` expressions.

## Fixes

- Parsing an empty configuration file no longer crashes.
- Parsing duplicate keys now raises an error instead of silently retaining the last value.

## Upgrade checklist

1. Replace `load()` calls with `parse()`.
2. Replace YAML anchors and aliases with explicit values.
3. Remove duplicate keys from configuration files.
4. Define every environment variable referenced by a `${VAR}` expression.
5. Add a JSON Schema file if the application requires schema validation.
