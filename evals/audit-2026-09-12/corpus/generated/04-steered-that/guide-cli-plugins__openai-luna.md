# Write a Plugin for `tool`

A `tool` plugin is a directory that contains a `plugin.toml` manifest and an entrypoint.  
Plugins can run at three hook points: `pre-run`, `post-run`, and `on-error`.

## Plugin structure

Create one directory for each plugin:

```text
my-plugin/
├── plugin.toml
└── entrypoint
```

The `plugin.toml` manifest must define these fields:

| Field | Type | Description |
|---|---|---|
| `name` | string | The plugin name |
| `version` | string | The plugin version |
| `entrypoint` | string | The path to the plugin entrypoint |

Example:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "entrypoint"
```

The `entrypoint` path is relative to the plugin directory.

## Choose a plugin location

`tool` discovers plugins from these directories:

```text
~/.tool/plugins
./.tool/plugins
```

Place a user-wide plugin under `~/.tool/plugins`:

```text
~/.tool/plugins/my-plugin/
├── plugin.toml
└── entrypoint
```

Place a project plugin under `./.tool/plugins`:

```text
project/
└── .tool/
    └── plugins/
        └── my-plugin/
            ├── plugin.toml
            └── entrypoint
```

The project plugin wins when both locations contain plugins with the same name.

Use a project plugin when the plugin belongs to one repository.  
Use a user-wide plugin when you want the plugin available across projects.

## Implement the entrypoint

Create the file named by `entrypoint` in `plugin.toml`:

```text
my-plugin/
├── plugin.toml
└── entrypoint
```

Implement the plugin behavior in that entrypoint.  
The entrypoint can implement these hooks:

- `pre-run`
- `post-run`
- `on-error`

Use `pre-run` for behavior that runs before the CLI command.  
Use `post-run` for behavior that runs after the CLI command completes.  
Use `on-error` for behavior that runs when the CLI command fails.

A plugin can implement one hook or multiple hooks.  
Keep each hook's behavior separate so that you can test each lifecycle case.

## Test a plugin

Run a plugin against a recorded session with:

```sh
tool plugin test ./path/to/my-plugin
```

For the example layout, run:

```sh
tool plugin test ./my-plugin
```

The command uses the recorded session to exercise the plugin.  
Use this command after each hook change so that you verify the plugin behavior before discovery.

## Test project precedence

Create two plugins with the same name:

```text
~/.tool/plugins/my-plugin/
└── plugin.toml
```

```text
project/.tool/plugins/my-plugin/
└── plugin.toml
```

Run `tool` from `project`.  
The plugin under `project/.tool/plugins` takes precedence over the plugin under `~/.tool/plugins`.

## Complete manifest example

```toml
name = "session-check"
version = "0.1.0"
entrypoint = "entrypoint"
```

Store the manifest and entrypoint together:

```text
session-check/
├── plugin.toml
└── entrypoint
```

Test the directory directly:

```sh
tool plugin test ./session-check
```

## Troubleshoot discovery

Check the plugin directory layout:

```text
<plugin-directory>/
├── plugin.toml
└── <entrypoint-path>
```

Check that `plugin.toml` contains `name`, `version`, and `entrypoint`.  
Check that the `entrypoint` value names the entrypoint inside the plugin directory.  
Check that the plugin directory sits under `~/.tool/plugins` or `./.tool/plugins`.  
If two plugins share a name, check the project copy under `./.tool/plugins` first.
