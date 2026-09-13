# confparse v3.0

Released 2026-09-13.

## Breaking changes

### `load()` renamed to `parse()`

`load()` no longer exists. Rename every call site to `parse()`. The signature and return type are unchanged.

```python
# v2.x
config = confparse.load("app.yaml")

# v3.0
config = confparse.parse("app.yaml")
```

### YAML anchor support removed

`parse()` raises `UnsupportedSyntaxError` on a document containing `&anchor` or `*alias`. Expand the anchors in your configuration files before upgrading.

```yaml
# Rejected in v3.0
defaults: &defaults
  timeout: 30
service:
  <<: *defaults

# Accepted
service:
  timeout: 30
```

### Duplicate keys now raise

A mapping with the same key twice raises `DuplicateKeyError`, which names the key and the line of the second occurrence. v2.x kept the last value silently. Delete the earlier occurrence to restore the v2.x result.

## New features

### Schema validation from a JSON Schema file

Pass `schema=` to `parse()` to validate the parsed document against a JSON Schema draft 2020-12 file. A document that fails validation raises `ValidationError` with the failing instance path.

```python
config = confparse.parse("app.yaml", schema="app.schema.json")
```

Without `schema=`, `parse()` performs no validation.

### `${VAR}` environment-variable interpolation

`parse()` replaces `${VAR}` in string values with the value of the environment variable `VAR`. An unset variable raises `UnsetVariableError`. Write `$${VAR}` for a literal `${VAR}`.

```yaml
database:
  url: postgres://${DB_HOST}:5432/app
```

Pass `interpolate=False` to keep v2.x behavior, where `${VAR}` stays literal.

## Fixes

- `parse()` returns `{}` for a zero-byte file. v2.x raised `AttributeError` on `NoneType`.
- Duplicate keys raise `DuplicateKeyError` instead of resolving to the last value. See [Duplicate keys now raise](#duplicate-keys-now-raise).

## Upgrade checklist

1. Replace `confparse.load(` with `confparse.parse(`.
2. Search your configuration files for `&` and `*` at the start of a YAML node, and expand those anchors.
3. Run `parse()` over every configuration file and fix each `DuplicateKeyError`.
4. Set `interpolate=False` if any string value contains a literal `${`.
