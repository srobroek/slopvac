# Write a `tool` CLI plugin

A `tool` plugin extends command execution through hooks that run before, after, or when a command fails.

## Create the plugin directory

Create one directory for the plugin:

```sh
mkdir my-plugin
```

Add `plugin.toml` at the directory root:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "./my-plugin"
```

The manifest requires these three fields:

| Field | Type | Effect |
|---|---|---|
| `name` | string | Identifies the plugin during discovery and name-clash resolution. |
| `version` | string | Declares the plugin version. |
| `entrypoint` | string | Identifies the plugin entrypoint. |

Add the entrypoint referenced by `entrypoint` to the plugin directory.

## Implement hooks

The entrypoint can implement three hooks:

| Hook | Invocation stage |
|---|---|
| `pre-run` | Before `tool` runs a command. |
| `post-run` | After `tool` runs a command. |
| `on-error` | When command execution produces an error. |

Implement only the hooks that the plugin needs.

## Test the plugin

Run the plugin against a recorded session before installing it:

```sh
tool plugin test ./my-plugin
```

The command reads the plugin from the directory passed as `<dir>`.

## Install the plugin

Install the plugin for your user account:

```sh
mkdir -p ~/.tool/plugins
cp -R ./my-plugin ~/.tool/plugins/my-plugin
```

Install the plugin for one project:

```sh
mkdir -p ./.tool/plugins
cp -R ./my-plugin ./.tool/plugins/my-plugin
```

`tool` discovers plugins from these directories:

| Directory | Scope |
|---|---|
| `~/.tool/plugins` | User account |
| `./.tool/plugins` | Project directory |

When both directories contain the same plugin name, `tool` uses the plugin from `./.tool/plugins`.
