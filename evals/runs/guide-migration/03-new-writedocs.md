# Migrate a config file from v1 to v2

v2 reads only v2 config files. A v1 file makes the tool exit 1 with `unsupported config version: 1`.

Three changes separate the formats:

1. Three keys are renamed.
2. One key is removed.
3. Nested tables replace the flat `server_*` and `log_*` namespaces.

The converter `appctl config migrate` applies the renames and the removal. It does not build the nested tables; you write those by hand.

## Run the converter

```bash
appctl config migrate --in config.toml --out config.v2.toml
```

The converter writes `version = 2`, applies the renames from the table below, drops the removed key, and copies every other key unchanged. It leaves the flat keys flat and prints one line per key you still have to move:

```
renamed: retry_count -> retries
renamed: timeout -> request_timeout_seconds
renamed: db_url -> database.url
removed: legacy_mode (no v2 equivalent)
manual: server_host, server_port, server_tls -> [server]
manual: log_level, log_format, log_file -> [logging]
```

Add `--in-place` to overwrite the input file. Keep a copy first: the converter does not write a backup.

## Renamed keys

| v1 key | v2 key | Note |
| --- | --- | --- |
| `retry_count` | `retries` | Same integer, same meaning. |
| `timeout` | `request_timeout_seconds` | v1 accepted `30` or `"30s"`. v2 accepts an integer of seconds only. The converter turns `"30s"` into `30`. |
| `db_url` | `database.url` | Moves into the `[database]` table. The converter creates that table. |

## Removed key

`legacy_mode` is gone. v2 has no equivalent and no replacement flag.

`legacy_mode = true` in v1 disabled request signing. v2 always signs. If your receiver rejected signed requests, configure it to verify the `X-Signature` header before you upgrade.

The converter drops `legacy_mode` whatever its value, so a v1 file with `legacy_mode = true` converts into a config that signs.

## Nested tables you write yourself

v1 kept these keys at the top level with a prefix. v2 groups them into `[server]` and `[logging]`. The key names lose the prefix.

| v1 key | v2 location |
| --- | --- |
| `server_host` | `[server] host` |
| `server_port` | `[server] port` |
| `server_tls` | `[server] tls` |
| `log_level` | `[logging] level` |
| `log_format` | `[logging] format` |
| `log_file` | `[logging] file` |

v2 rejects the flat keys with `unknown key: server_host (did you mean [server] host?)`.

## Full example

v1 `config.toml`:

```toml
retry_count = 3
timeout = "30s"
db_url = "postgres://localhost/app"
legacy_mode = true

server_host = "0.0.0.0"
server_port = 8080
server_tls = true

log_level = "info"
log_format = "json"
log_file = "/var/log/app.log"

[features]
beta_ui = false
```

v2 `config.toml`:

```toml
version = 2

retries = 3
request_timeout_seconds = 30

[database]
url = "postgres://localhost/app"

[server]
host = "0.0.0.0"
port = 8080
tls = true

[logging]
level = "info"
format = "json"
file = "/var/log/app.log"

[features]
beta_ui = false
```

`[features]` was already a table in v1 and carries over unchanged.

## Check the result

```bash
appctl config validate --file config.v2.toml
```

The command prints `ok` and exits 0 when the file parses as v2 and every key is known. It prints one line per problem and exits 1 otherwise.

Print the values the tool resolved, including defaults:

```bash
appctl config show --file config.v2.toml
```

Compare that output against `appctl config show --file config.toml` run under v1.x to confirm no value changed except `request_timeout_seconds` and the signing behavior.

## Environment variable overrides

Nesting changes the override names. Each level is one underscore, and the prefix stays `APPCTL_`.

| v1 variable | v2 variable |
| --- | --- |
| `APPCTL_SERVER_HOST` | `APPCTL_SERVER_HOST` |
| `APPCTL_LOG_LEVEL` | `APPCTL_LOGGING_LEVEL` |
| `APPCTL_TIMEOUT` | `APPCTL_REQUEST_TIMEOUT_SECONDS` |
| `APPCTL_DB_URL` | `APPCTL_DATABASE_URL` |

`APPCTL_SERVER_HOST` keeps its name because `server_host` and `[server] host` produce the same variable. v2 ignores an unrecognized `APPCTL_` variable without warning, so check these before you deploy.
