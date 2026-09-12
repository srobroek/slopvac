# confparse v3.0

This release contains two breaking changes that require code edits in every project using confparse. Read the upgrade steps before bumping the version.

## Breaking changes

### `load()` is now `parse()`

The entry point has been renamed. `load()` no longer exists and calling it raises `AttributeError`.

```python
# Before
config = confparse.load("app.yaml")

# After
config = confparse.parse("app.yaml")
```

The signature and return value are unchanged, so a search-and-replace across your codebase is sufficient. For a large codebase:

```console
$ grep -rl 'confparse.load' . | xargs sed -i '' 's/confparse\.load/confparse.parse/g'
```

### YAML anchor support removed

Anchors (`&name`), aliases (`*name`), and merge keys (`<<:`) are no longer resolved. A file containing them raises `UnsupportedSyntaxError` with the line number of the first anchor.

Anchors were most often used to share a block of settings between environments:

```yaml
# No longer supported
defaults: &defaults
  timeout: 30
  retries: 3

production:
  <<: *defaults
  host: prod.example.com
```

Rewrite these files with the shared values spelled out, or move the sharing into your application code by parsing a base file and a per-environment file and merging the two dictionaries. Environment-variable interpolation, described below, covers the case where anchors were used to avoid repeating a single literal value.

## New features

### Schema validation

`parse()` accepts a `schema` argument pointing at a JSON Schema file (draft 2020-12). The parsed configuration is validated against it before being returned, and a failure raises `ValidationError` carrying the offending key path and the schema rule that rejected it.

```python
config = confparse.parse("app.yaml", schema="app.schema.json")
```

Validation covers required keys, types, enums, numeric bounds, and `additionalProperties`. Because it runs before your code touches the values, a typo in a key name surfaces at startup instead of as a `KeyError` deep in a request handler. The argument is optional; omitting it preserves v2 behavior.

### Environment-variable interpolation

Any string value may contain `${VAR}`, which is replaced with the value of that environment variable:

```yaml
database:
  url: ${DATABASE_URL}
  pool_size: 10
  log_path: /var/log/${SERVICE_NAME}/db.log
```

Interpolation applies to string values only, not to keys, and a variable may appear more than once in a value. An unset variable raises `InterpolationError` naming the variable and the key that referenced it; use `${VAR:-default}` to supply a fallback instead. Write `$${VAR}` to produce a literal `${VAR}`.

This is a behavioral change for existing files: a value that happens to contain `${` is now interpreted rather than passed through. If your configuration includes shell templates or similar literals, escape them with `$$`.

## Fixes

**Empty files no longer crash.** Parsing a zero-byte file, or one containing only comments and whitespace, raised an uncaught `IndexError` in v2. It now returns an empty mapping.

**Duplicate keys raise.** When a mapping contained the same key twice, v2 silently kept the last occurrence. `parse()` now raises `DuplicateKeyError` with both line numbers. This surfaces real bugs in configurations that appeared to work — check your files for accidental duplicates before deploying, since a file that parsed cleanly under v2 may now be rejected.

## Upgrading

1. Rename `load()` to `parse()` at every call site.
2. Search your configuration files for `&`, `*`, and `<<:` and rewrite any anchors.
3. Search for literal `${` in string values and escape the occurrences you do not want interpolated.
4. Parse each configuration file once under v3 to surface duplicate keys before the change reaches production.
5. Optionally add a schema file and pass it to `parse()`.

Steps 1 through 4 are required. Nothing else in the v2 API has changed.
