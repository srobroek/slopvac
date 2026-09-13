# confparse v3.0 release notes

v3.0 changes the public entry point and drops YAML anchor support. Every v2 caller needs edits before it runs on v3.

## Breaking changes

### `load()` renamed to `parse()`

`load()` is gone. Call `parse()` with the same arguments and return type.

```python
# v2
config = confparse.load("app.yaml")

# v3
config = confparse.parse("app.yaml")
```

There is no `load()` alias, so an unedited v2 call raises `AttributeError`.

### YAML anchors and aliases removed

confparse no longer resolves `&name` anchors, `*name` aliases, or `<<:` merge keys. A file containing any of them fails with a parse error that names the line of the anchor or alias.

Expand the shared block by hand before you upgrade:

```yaml
# v2
defaults: &defaults
  timeout: 30
staging:
  <<: *defaults

# v3
staging:
  timeout: 30
```

To find affected files, grep your config tree for `&`, `*`, and `<<:` at the start of a YAML value.

## New features

### Schema validation from a JSON Schema file

Pass `schema` to `parse()` to validate the parsed document against a JSON Schema draft 2020-12 file:

```python
config = confparse.parse("app.yaml", schema="app.schema.json")
```

Validation runs after parsing and after environment-variable interpolation. A document that violates the schema raises an error naming the failing key path and the constraint it broke. Omit `schema` to skip validation, which matches v2 behavior.

### `${VAR}` environment-variable interpolation

`parse()` replaces `${VAR}` in string values with the value of the environment variable `VAR`:

```yaml
database:
  url: ${DATABASE_URL}
  pool_size: 8
```

Interpolation applies to string values only, not to keys. An unset variable raises rather than substituting an empty string. Audit existing configs for literal `${` sequences, because v2 passed them through unchanged and v3 treats them as references.

## Fixes

- Parsing an empty file returns an empty mapping. v2 crashed.
- A duplicate key raises an error naming the key and both line numbers. v2 kept the last value silently. This rejects files that v2 accepted, so check configs that were assembled by concatenation or templating.

## Upgrade checklist

1. Replace every `confparse.load(` call with `confparse.parse(`.
2. Expand anchors, aliases, and merge keys in every config file.
3. Escape or remove literal `${` sequences that are not environment references.
4. Remove duplicate keys from every config file.
5. Parse each config file once in a test to surface the errors from steps 2 through 4.
