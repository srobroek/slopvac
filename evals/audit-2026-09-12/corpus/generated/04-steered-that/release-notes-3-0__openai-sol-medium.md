# confparse v3.0

## Breaking changes

- YAML anchors are no longer supported. Replace anchors and aliases with explicit YAML values before upgrading.
- The `load()` function is now `parse()`. Replace each `load()` call with `parse()`.

```python
# Before
config = confparse.load(source)

# v3.0
config = confparse.parse(source)
```

- Duplicate keys now raise an error instead of selecting the last value. Remove duplicate keys from each configuration file.

## New features

- `confparse` can validate configuration data against a JSON Schema file.
- `${VAR}` expressions in configuration values can interpolate environment variables.

## Fixes

- Parsing an empty file no longer crashes.

## Upgrade checklist

1. Replace every `load()` call with `parse()`.
2. Replace every YAML anchor and alias with explicit values.
3. Remove duplicate keys from each configuration file.
4. Test `${VAR}` interpolation with the environment variables used by your application.
5. Validate representative configuration files against your JSON Schema file.
