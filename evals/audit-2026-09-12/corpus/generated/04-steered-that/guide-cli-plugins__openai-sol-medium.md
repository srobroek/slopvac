# Write a `tool` CLI plugin

A `tool` plugin adds hook behavior through an entrypoint declared in a `plugin.toml` manifest.

## Create the plugin directory

Create one directory for the manifest and entrypoint:

```text
my-plugin/
├── plugin.toml
└── plugin.sh
```

Add `plugin.toml` at the plugin directory root:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "plugin.sh"
```

The `name` field identifies the plugin when `tool` discovers it.

The `version` field records the plugin version.

The `entrypoint` field identifies the plugin entrypoint.

## Implement hooks

The entrypoint can implement three hooks:

| Hook | Event |
|---|---|
| `pre-run` | Before `tool` runs a command |
| `post-run` | After `tool` runs a command |
| `on-error` | When a command produces an error |

Implement only the hooks that the plugin needs.

Use `pre-run` to prepare command-specific state or validate required inputs.

Use `post-run` to process command results or remove temporary state.

Use `on-error` to record failure details or remove state left by a failed command.

## Test the plugin

When a recorded session is available, run the plugin test command:

```sh
tool plugin test ./my-plugin
```

The command loads the plugin from `./my-plugin` and runs it against the recorded session.

Test each implemented hook with a session containing its corresponding event.

## Install the plugin

### Install for one user

Place the plugin directory under `~/.tool/plugins`:

```sh
mkdir -p ~/.tool/plugins
cp -R ./my-plugin ~/.tool/plugins/
```

`tool` discovers user plugins from `~/.tool/plugins`.

### Install for one project

Place the plugin directory under the project’s `./.tool/plugins` directory:

```sh
mkdir -p ./.tool/plugins
cp -R ./my-plugin ./.tool/plugins/
```

`tool` discovers project plugins from `./.tool/plugins`.

When both locations contain the same manifest `name`, `tool` uses the plugin from `./.tool/plugins`.

## Verify discovery precedence

Create user and project plugins with the same `name` only when the project must override user-level behavior.

Give plugins different `name` values when both plugins must remain available.
