# Write a `tool` CLI plugin

A `tool` plugin uses one entrypoint to handle up to three CLI lifecycle hooks.

## Create the plugin directory

Create a directory for the plugin:

```sh
mkdir my-plugin
cd my-plugin
```

Add the entrypoint and `plugin.toml` manifest at the plugin directory root:

```text
my-plugin/
├── plugin.toml
└── plugin
```

## Define the manifest

Create `plugin.toml` with the plugin name, version, and entrypoint:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "plugin"
```

| Name | Type | Required | Effect |
| --- | --- | --- | --- |
| `name` | string | Yes | Identifies the plugin during discovery and name-clash resolution. |
| `version` | string | Yes | Identifies the plugin version. |
| `entrypoint` | string | Yes | Identifies the plugin entrypoint. |

## Implement hooks

Implement any combination of the three supported hooks in the entrypoint.

| Hook | Event |
| --- | --- |
| `pre-run` | Runs before a CLI run. |
| `post-run` | Runs after a CLI run. |
| `on-error` | Runs when a CLI run reports an error. |

## Test the plugin

Run the plugin against a recorded session before installing it:

```sh
tool plugin test ./my-plugin
```

Replace `./my-plugin` with the path to the directory containing `plugin.toml`.

## Install the plugin

Install a user plugin under `~/.tool/plugins`:

```sh
mkdir -p ~/.tool/plugins
cp -R ./my-plugin ~/.tool/plugins/my-plugin
```

Install a project plugin under `./.tool/plugins`:

```sh
mkdir -p ./.tool/plugins
cp -R ./my-plugin ./.tool/plugins/my-plugin
```

The CLI discovers plugins from both locations:

| Location | Scope | Precedence |
| --- | --- | --- |
| `~/.tool/plugins` | User | Lower |
| `./.tool/plugins` | Project | Higher |

If both locations contain the same manifest `name`, the CLI loads the project plugin.
