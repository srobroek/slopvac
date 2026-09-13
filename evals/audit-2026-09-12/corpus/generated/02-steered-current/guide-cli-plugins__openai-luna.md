# Write a plugin for `tool`

A `tool` plugin is a directory containing a `plugin.toml` manifest and an entrypoint. Plugins can run before commands, after successful commands, and when commands fail.

## Plugin structure

Create one directory for each plugin:

```text
my-plugin/
├── plugin.toml
└── plugin
```

The `plugin.toml` file must define these fields:

```toml
name = "my-plugin"
version = "1.0.0"
entrypoint = "./plugin"
```

| Field | Type | Description |
|---|---|---|
| `name` | String | The plugin name used during discovery. |
| `version` | String | The plugin version. |
| `entrypoint` | String | The path to the executable that implements the plugin. |

The `entrypoint` path is relative to the plugin directory.

## Choose a plugin location

`tool` searches these directories:

```text
~/.tool/plugins
./.tool/plugins
```

Place a user-wide plugin under `~/.tool/plugins`:

```text
~/.tool/plugins/my-plugin/
├── plugin.toml
└── plugin
```

Place a project plugin under `.tool/plugins`:

```text
project/
└── .tool/
    └── plugins/
        └── my-plugin/
            ├── plugin.toml
            └── plugin
```

When both locations contain a plugin with the same `name`, the project plugin takes precedence.

## Create the manifest

Create a directory for the plugin:

```sh
mkdir -p .tool/plugins/my-plugin
```

Create `.tool/plugins/my-plugin/plugin.toml`:

```toml
name = "my-plugin"
version = "1.0.0"
entrypoint = "./plugin"
```

The manifest name must match the plugin directory name when you want the directory to identify the plugin clearly.

## Implement the entrypoint

Create an executable entrypoint at the path declared by `entrypoint`:

```sh
touch .tool/plugins/my-plugin/plugin
chmod +x .tool/plugins/my-plugin/plugin
```

The entrypoint implements the plugin hooks supported by `tool`:

- `pre-run`
- `post-run`
- `on-error`

Keep each hook focused on one task. Use `pre-run` for work before a command runs. Use `post-run` for work after a successful command. Use `on-error` for work after a command fails.

The plugin protocol determines how `tool` passes hook events to the entrypoint. Follow the protocol required by the `tool` version installed in your environment.

## Use the `pre-run` hook

Use `pre-run` to inspect or prepare a command before `tool` runs it.

Typical tasks include:

- Checking required configuration.
- Preparing local resources.
- Recording command metadata.
- Rejecting commands that violate a project rule.

Keep preparation idempotent when `tool` can invoke the hook more than once for the same command.

## Use the `post-run` hook

Use `post-run` to process a command after it completes successfully.

Typical tasks include:

- Recording successful command metadata.
- Updating a local index.
- Removing temporary resources.
- Emitting a completion event.

Do not use `post-run` for failure handling. Use `on-error` for failed commands.

## Use the `on-error` hook

Use `on-error` to process a command that fails.

Typical tasks include:

- Capturing diagnostic information.
- Saving logs.
- Creating a failure report.
- Cleaning up resources created by `pre-run`.

Make failure handling resilient. The hook should preserve the original command failure instead of hiding it.

## Test a plugin

Test a plugin against a recorded session with:

```sh
tool plugin test ./.tool/plugins/my-plugin
```

Replace the directory argument with the path to your plugin:

```sh
tool plugin test "$HOME/.tool/plugins/my-plugin"
```

The test command runs the plugin against the recorded session rather than a live command.

Run the test after changing any of these files:

```text
plugin.toml
plugin entrypoint
hook handling
```

## Resolve name clashes

Suppose both plugin locations contain a plugin named `my-plugin`:

```text
~/.tool/plugins/my-plugin/
./.tool/plugins/my-plugin/
```

`tool` uses:

```text
./.tool/plugins/my-plugin/
```

The project directory wins because project plugins take precedence over user-wide plugins.

Change the plugin `name` when you need both plugins to remain independently selectable.

## Version a plugin

Update the `version` field when you publish a new plugin version:

```toml
name = "my-plugin"
version = "1.1.0"
entrypoint = "./plugin"
```

Keep the manifest in the plugin directory so `tool` can discover the plugin and read its metadata.
