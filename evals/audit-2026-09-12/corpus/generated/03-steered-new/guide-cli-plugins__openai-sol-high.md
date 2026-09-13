# Write a `tool` CLI plugin

A `tool` plugin uses an entrypoint to handle run events from the `tool` CLI.

## Create the plugin directory

Create one directory for the plugin:

```text
my-plugin/
├── plugin.toml
└── plugin-entrypoint
```

Set `entrypoint` to the entrypoint file’s path:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "plugin-entrypoint"
```

The `plugin.toml` manifest contains these fields:

| Field | Type | Effect |
|---|---|---|
| `name` | String | Identifies the plugin during discovery and name-clash resolution. |
| `version` | String | Identifies the plugin version. |
| `entrypoint` | String | Identifies the plugin entrypoint. |

## Implement hooks

The entrypoint can implement one or more of these hooks:

| Hook | Event |
|---|---|
| `pre-run` | Runs before a command run. |
| `post-run` | Runs after a command run. |
| `on-error` | Runs when a command run produces an error. |

Omit hooks that the plugin does not handle.

## Test the plugin

Run the plugin against a recorded session:

```sh
tool plugin test ./my-plugin
```

Replace `./my-plugin` with the directory that contains the plugin’s `plugin.toml` manifest.

## Install the plugin

Install the plugin for your user account under `~/.tool/plugins`:

```sh
mkdir -p ~/.tool/plugins
cp -R ./my-plugin ~/.tool/plugins/my-plugin
```

Install the plugin for one project under `./.tool/plugins`:

```sh
mkdir -p ./.tool/plugins
cp -R ./my-plugin ./.tool/plugins/my-plugin
```

The `tool` CLI discovers plugins from both directories:

| Directory | Scope |
|---|---|
| `~/.tool/plugins` | User account |
| `./.tool/plugins` | Project directory |

When both directories contain the same plugin `name`, the CLI uses the plugin from `./.tool/plugins`.
