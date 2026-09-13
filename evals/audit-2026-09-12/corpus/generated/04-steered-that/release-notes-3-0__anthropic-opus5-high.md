# confparse v3.0.0

Released 2026-09-13.

## Breaking changes

### `load()` renamed to `parse()`

`load()` is removed. Rename every call site to `parse()`. The signature and return value are unchanged.

```python
# v2.x
config = confparse.load("app.yaml")

# v3.0
config = confparse.parse("app.yaml")
```

### YAML anchor support removed

`parse()` raises `UnsupportedFeatureError` on a document containing an anchor (`&name`) or an alias (`*name`). Expand each alias into a literal value before upgrading.

```yaml
# Rejected in v3.0
defaults: &defaults
  timeout: 30
staging:
  <<: *defaults

# Accepted
staging:
  timeout: 30
```

### Duplicate keys raise

A mapping with a repeated key raises `DuplicateKeyError`, naming the key and its line number. v2.x kept the last value silently. Audit configuration files that relied on a later key overriding an earlier one.

## New features

### Schema validation from a JSON Schema file

Pass `schema=` to `parse()` to validate the parsed document against a JSON Schema file. A document that fails validation raises `ValidationError` with the failing JSON Pointer.

```python
config = confparse.parse("app.yaml", schema="app.schema.json")
```

### Environment-variable interpolation

`parse()` substitutes `${VAR}` in string values with the value of the environment variable `VAR`. An unset variable raises `InterpolationError`. Write `$${VAR}` for a literal `${VAR}`.

```yaml
database_url: ${DATABASE_URL}
prefix: $${NOT_A_VARIABLE}
```

## Fixes

- `parse()` returns an empty mapping for a zero-byte file. v2.x raised `IndexError`.

## Upgrade steps

1. Replace each `load()` call with `parse()`.
2. Expand YAML anchors and aliases into literal values.
3. Remove duplicate keys from every mapping.
4. Escape any literal `${` in a string value as `$${`.
5. Run your configuration files through `parse()` before deploying.
