# Migrating from v1 to v2

## Introduction

We're excited to announce that v2 of the config format is here! This release represents a significant improvement in how configuration is structured, and while it does introduce some breaking changes, we think you'll find the migration well worth the effort.

In this guide, we'll walk you through everything you need to know.

## What's Changed

The v2 format brings three main categories of change:

1. **Renamed keys** — three keys have new names
2. **Removed key** — one key is no longer supported
3. **Nested tables** — the flat namespace has been replaced with proper nesting

Let's dive into each of these.

## Renamed Keys

| v1 | v2 |
|---|---|
| `cache_dir` | `cache.directory` |
| `max_conn` | `pool.max` |
| `log_lvl` | `logging.level` |

The good news is that these are handled automatically by our converter (see below).

## Removed Key

The `legacy_mode` key has been removed entirely. If you were relying on it, you'll unfortunately need to restructure your configuration. In most cases this simply means moving to the equivalent v2 behavior, which is now the default.

## Nested Tables

This is the big one. Previously, all configuration lived in a single flat namespace:

```toml
cache_dir = "/tmp/cache"
cache_ttl = 3600
pool_max = 10
```

In v2, related settings are grouped into nested tables:

```toml
[cache]
directory = "/tmp/cache"
ttl = 3600

[pool]
max = 10
```

Unfortunately, the converter can't handle this transformation automatically — the nesting requires semantic understanding that a mechanical tool simply can't provide. You'll need to restructure these by hand.

## Using the Converter

For the renames, we've provided an automated converter:

```bash
myapp config migrate --in config.v1.toml --out config.v2.toml
```

This will handle the three key renames for you. It won't touch the nesting, so you'll still have some manual work to do afterward.

## Verifying Your Migration

Once you've made your changes, validate the result:

```bash
myapp config validate
```

## Wrapping Up

And that's it! Migration should be straightforward for most users. If you run into any issues, don't hesitate to open an issue — we're here to help.

Happy migrating! 🎉
