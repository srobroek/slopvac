# confparse v3.0

Version 3.0 introduces JSON Schema validation and environment-variable interpolation. It also includes breaking parser changes that may require updates before upgrading.

## Breaking changes

### `load()` renamed to `parse()`

Replace calls to `load()` with `parse()`:

```python
# Before
config = confparse.load("config.yaml")

# v3.0
config = confparse.parse("config.yaml")
```

Search your application, tests, scripts, and documentation for remaining `load()` calls.

### YAML anchors are no longer supported

Configuration files must not use YAML anchors or aliases. Replace shared anchored values with explicit values or another configuration-generation mechanism before parsing.

```yaml
# No longer supported
defaults: &defaults
  timeout: 30

service:
  <<: *defaults
```

## New features

### JSON Schema validation

Configurations can now be validated against a schema stored in a JSON Schema file. Use schema validation to enforce required fields, accepted types, and other configuration constraints.

Review existing configuration files before enabling validation: values previously accepted without checks may now fail when they do not conform to the schema.

### Environment-variable interpolation

String values can reference environment variables with `${VAR}` syntax:

```yaml
database:
  host: ${DATABASE_HOST}
  password: ${DATABASE_PASSWORD}
```

Ensure each required variable is set in the environment where the configuration is parsed.

## Fixes and stricter parsing

- Empty configuration files no longer crash the parser.
- Duplicate mapping keys now raise an error instead of silently keeping the last value.

A file such as the following must be corrected before upgrading:

```yaml
port: 8080
port: 9090
```

Earlier versions used `9090`; v3.0 rejects the duplicate key.

## Upgrade checklist

1. Replace `load()` calls with `parse()`.
2. Remove YAML anchors and aliases from configuration files.
3. Find and resolve duplicate keys.
4. Add any environment variables referenced through `${VAR}`.
5. Add JSON Schema validation where appropriate.
6. Test empty, generated, and environment-specific configuration files before deployment.
