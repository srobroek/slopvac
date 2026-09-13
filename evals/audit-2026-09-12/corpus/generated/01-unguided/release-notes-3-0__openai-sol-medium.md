# confparse v3.0

Version 3.0 introduces schema validation and environment-variable interpolation. It also includes breaking API and YAML behavior changes.

## Breaking changes

### `load()` renamed to `parse()`

Replace calls to `load()` with `parse()`:

```python
# Before
config = confparse.load("config.yaml")

# v3.0
config = confparse.parse("config.yaml")
```

### YAML anchors removed

YAML anchors and aliases are no longer supported. Expand anchored values directly in your configuration before upgrading.

```yaml
# No longer supported
defaults: &defaults
  timeout: 30

service:
  <<: *defaults
```

```yaml
# Supported
service:
  timeout: 30
```

## New features

### JSON Schema validation

Configurations can now be validated against a schema loaded from a JSON Schema file. Invalid configurations raise a validation error during parsing.

### Environment-variable interpolation

String values containing `${VAR}` now interpolate variables from the environment:

```yaml
database:
  host: ${DATABASE_HOST}
  password: ${DATABASE_PASSWORD}
```

Ensure every required variable is present in the runtime environment before parsing the file.

## Fixes

- Empty configuration files no longer cause a crash.
- Duplicate keys now raise an error instead of silently retaining the last value.

The duplicate-key change may expose previously unnoticed configuration errors. Check existing files for repeated keys before deploying v3.0.

## Upgrade checklist

1. Rename every `load()` call to `parse()`.
2. Replace YAML anchors and aliases with explicit values.
3. Remove duplicate keys from configuration files.
4. Define environment variables referenced through `${VAR}`.
5. Add a JSON Schema file where configuration validation is required.
6. Test empty-file handling if your application accepts optional or generated configuration files.
