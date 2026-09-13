# confparse v3.0

confparse v3.0 introduces schema validation and environment-variable interpolation, along with stricter handling of duplicate keys. This release also includes two breaking changes.

## Breaking changes

### YAML anchors are no longer supported

YAML anchors and aliases were removed in v3.0. Configurations that use them must be rewritten without anchors before upgrading.

### Rename `load()` to `parse()`

The `load()` function was renamed to `parse()`.

Before:

```python
config = confparse.load("config.yaml")
```

After:

```python
config = confparse.parse("config.yaml")
```

Update all calls to `load()` during the upgrade. Code that still calls `load()` will need to be changed for v3.0.

## New features

### JSON Schema validation

You can now validate a configuration against a JSON Schema file while parsing it. Add a schema file to your configuration-loading workflow to catch invalid structure and values early.

### Environment-variable interpolation

Configuration values can now reference environment variables using `${VAR}` syntax.

```yaml
database:
  host: ${DB_HOST}
  port: ${DB_PORT}
```

Set the referenced environment variables before parsing the configuration.

## Fixes and behavior changes

- Empty configuration files no longer cause a crash.
- Duplicate keys now raise an error instead of silently using the last value.

## Upgrade checklist

- Replace every `confparse.load()` call with `confparse.parse()`.
- Remove YAML anchors and aliases from configuration files.
- Check configurations for duplicate keys; they now fail explicitly.
- Add JSON Schema files where configuration validation is needed.
- Use `${VAR}` references for values that should come from the environment.
