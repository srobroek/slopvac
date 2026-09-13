# confparse 3.0

Version 3.0 removes two existing interfaces and adds schema validation and environment-variable interpolation.

## Breaking changes

### Replace `load()` with `parse()`

The `load()` function was renamed to `parse()`.

```python
# Before
config = confparse.load(source)

# Version 3.0
config = confparse.parse(source)
```

Replace every `load()` call before upgrading to version 3.0.

### Remove YAML anchors

Version 3.0 does not support YAML anchors.

If a configuration file uses YAML anchors, expand the shared values before parsing the file.

### Reject duplicate keys

The parser previously kept the last value when a mapping contained duplicate keys. Version 3.0 raises an error instead.

Remove duplicate keys from each configuration file before upgrading.

## New features

- Validate configuration data against a JSON Schema file.
- Interpolate environment variables referenced with `${VAR}` syntax.

Set each referenced environment variable before parsing its configuration file.

## Fixes

- Parsing an empty file no longer crashes.

## Upgrade checklist

1. Replace `load()` calls with `parse()`.
2. Expand YAML anchors into explicit values.
3. Remove duplicate keys from configuration mappings.
4. Set environment variables referenced through `${VAR}`.
5. Add a JSON Schema file when schema validation is required.
