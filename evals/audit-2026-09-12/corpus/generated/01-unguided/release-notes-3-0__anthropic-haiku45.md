# confparse v3.0 Release Notes

## Overview

confparse v3.0 introduces schema validation, environment-variable interpolation, and critical bug fixes. This release includes breaking changes—please review the migration guide before upgrading.

## Breaking Changes

### `load()` renamed to `parse()`

The `load()` function has been renamed to `parse()` to better reflect its behavior.

**Migration:**
```python
# Old
config = confparse.load("config.yaml")

# New
config = confparse.parse("config.yaml")
```

All existing code using `load()` must be updated. The function will be removed in a future release.

### YAML anchor support removed

YAML anchors (`&anchor` and `*anchor`) are no longer supported. This simplifies the parser and removes ambiguity in configuration resolution.

**Migration:**
If your configurations use anchors for reuse, flatten the repeated values or use environment-variable interpolation (see New Features).

```yaml
# Old
defaults: &defaults
  timeout: 30
  retries: 3

service_a:
  <<: *defaults

# New (use interpolation instead)
defaults_timeout: ${DEFAULT_TIMEOUT:-30}
defaults_retries: ${DEFAULT_RETRIES:-3}

service_a:
  timeout: ${defaults_timeout}
  retries: ${defaults_retries}
```

## New Features

### Schema Validation

Validate your configuration against a JSON Schema file to catch errors early.

```python
config = confparse.parse("config.yaml", schema="config.schema.json")
```

If validation fails, a `confparse.ValidationError` is raised with details about the mismatch. This is useful for CI/CD pipelines and development environments.

### Environment-Variable Interpolation

Use `${VAR_NAME}` or `${VAR_NAME:-default_value}` syntax to inject environment variables into your configuration.

```yaml
database:
  host: ${DB_HOST}
  port: ${DB_PORT:-5432}
  password: ${DB_PASSWORD}
```

Environment variables are interpolated at parse time. If a required variable is missing, a `confparse.InterpolationError` is raised.

## Bug Fixes

### Fixed: Crash on empty file

Parsing an empty configuration file no longer crashes. An empty file now returns an empty configuration object.

```python
config = confparse.parse("empty.yaml")
# config is now {}
```

### Fixed: Duplicate keys now raise an error

Previously, duplicate keys silently accepted the last value. This silent failure could hide configuration errors.

```yaml
database:
  host: primary.db
  host: secondary.db  # Now raises DuplicateKeyError
```

Update your configuration files to remove duplicate keys. Specify defaults or use environment-variable interpolation for conditional values.

## Migration Checklist

- [ ] Rename all `confparse.load()` calls to `confparse.parse()`
- [ ] Remove YAML anchors from your configuration files
- [ ] Run your configurations through the parser to catch duplicate keys
- [ ] (Optional) Add schema validation for enhanced validation
- [ ] Test thoroughly before deploying to production

## Installation

```bash
pip install --upgrade confparse==3.0
```

## Support

For questions or issues, please visit the [confparse repository](https://github.com/your-org/confparse) or file an issue.
