# Migrating a config file from v1 to v2

v2 renames three keys, removes one, and replaces the flat `plugin_*` namespace with nested `[plugin.<name>]` tables.

`appctl migrate-config` performs the renames and the removal. It does not perform the nesting. Do that part by hand using the mapping below.

v2 rejects a v1 config with an error naming the first unmigrated key. There is no compatibility mode.

## 1. Back up the file

```bash
cp appctl.toml appctl.toml.v1.bak
```

## 2. Run the converter

```bash
appctl migrate-config appctl.toml
```

The converter writes in place and prints each change:

```
appctl.toml: renamed timeout -> request_timeout_seconds
appctl.toml: renamed max_conn -> max_connections
appctl.toml: renamed log -> log_level
appctl.toml: removed legacy_auth (no v2 equivalent)
appctl.toml: 3 plugin_* keys need manual nesting, see below
appctl.toml: version = 2
```

Preview without writing:

```bash
appctl migrate-config --dry-run appctl.toml
```

## 3. Renamed keys

The converter handles these. The table is here so you can verify its output and update any script that reads the file.

| v1 key | v2 key | Note |
| --- | --- | --- |
| `timeout` | `request_timeout_seconds` | Value unchanged. Still an integer in seconds. |
| `max_conn` | `max_connections` | Value unchanged. |
| `log` | `log_level` | Value unchanged. Accepts `debug`, `info`, `warn`, `error`. |

## 4. Removed key

`legacy_auth` is removed. v2 fails to load a config that still contains it.

`legacy_auth = true` in v1 sent credentials in the query string. v2 sends them in the `Authorization` header, which is what `legacy_auth = false` did. Set your credentials with `auth_token` and remove nothing else:

```toml
auth_token = "${APPCTL_TOKEN}"
```

A server that only accepts query-string credentials cannot be reached by v2.

## 5. Nest the plugin keys by hand

v1 held plugin settings in a flat namespace, one key per setting, with the plugin name inside the key:

```toml
plugin_cache_enabled = true
plugin_cache_ttl = 300
plugin_cache_backend = "redis"
plugin_metrics_enabled = true
plugin_metrics_port = 9090
plugin_tracing_enabled = false
```

v2 holds one table per plugin:

```toml
[plugin.cache]
enabled = true
ttl = 300
backend = "redis"

[plugin.metrics]
enabled = true
port = 9090

[plugin.tracing]
enabled = false
```

The rule: `plugin_<name>_<setting>` becomes key `<setting>` under table `[plugin.<name>]`. Setting names and values are unchanged.

Plugin names containing an underscore are the one case the rule does not resolve on its own. `plugin_rate_limit_enabled` splits either as plugin `rate` setting `limit_enabled` or plugin `rate_limit` setting `enabled`. Check the plugin's own name with `appctl plugin list` and nest accordingly:

```toml
[plugin.rate_limit]
enabled = true
```

This ambiguity is why the converter leaves the nesting alone.

## 6. Validate

```bash
appctl config validate
```

Output on success:

```
appctl.toml: valid (version 2, 3 plugins configured)
```

Errors name the key and the line:

```
appctl.toml:14: unknown key 'plugin_cache_ttl' (v2 expects [plugin.cache] ttl)
appctl.toml:3: key 'legacy_auth' was removed in v2
```

Print the loaded configuration to confirm the plugin tables resolved:

```bash
appctl config show --resolved
```

## Full example

v1:

```toml
version = 1
endpoint = "https://api.example.com"
timeout = 30
max_conn = 10
log = "info"
legacy_auth = false
auth_token = "${APPCTL_TOKEN}"

plugin_cache_enabled = true
plugin_cache_ttl = 300
plugin_metrics_enabled = true
plugin_metrics_port = 9090
```

v2:

```toml
version = 2
endpoint = "https://api.example.com"
request_timeout_seconds = 30
max_connections = 10
log_level = "info"
auth_token = "${APPCTL_TOKEN}"

[plugin.cache]
enabled = true
ttl = 300

[plugin.metrics]
enabled = true
port = 9090
```

## Rolling back

v1 binaries read the backup unchanged:

```bash
mv appctl.toml.v1.bak appctl.toml
```

A v1 binary rejects a v2 file on the `version = 2` line, so a partial rollout needs the pinned config alongside the pinned binary.
