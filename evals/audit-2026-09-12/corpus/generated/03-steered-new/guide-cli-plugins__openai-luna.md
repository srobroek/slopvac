# Write a Plugin for `tool`

A `tool` plugin is a directory that contains a `plugin.toml` manifest and an entrypoint. The plugin can run code before a command, after a command, or when a command fails.

## Plugin structure

Create one directory for each plugin.

```text
my-plugin/
├── plugin.toml
└── plugin-entrypoint
```

The `plugin.toml` file must define these fields:

| Field | Purpose |
|---|---|
| `name` | Identifies the plugin |
| `version` | Identifies the plugin version |
| `entrypoint` | Identifies the program that runs the plugin |

Example manifest:

```toml
name = "my-plugin"
version = "1.0.0"
entrypoint = "plugin-entrypoint"
```

The `entrypoint` value identifies a file inside the plugin directory. Give that file execute permission before you test the plugin.

```sh
chmod +x plugin-entrypoint
```

## Choose a plugin directory

`tool` discovers plugins from two directories:

```text
~/.tool/plugins
./.tool/plugins
```

Place a user-wide plugin under `~/.tool/plugins`.

```text
~/.tool/plugins/my-plugin/
├── plugin.toml
└── plugin-entrypoint
```

Place a project plugin under `./.tool/plugins`.

```text
project/
└── .tool/
    └── plugins/
        └── my-plugin/
            ├── plugin.toml
            └── plugin-entrypoint
```

The project directory wins when both directories contain plugins with the same `name`.

## Define the plugin manifest

Set `name` to a unique plugin name.

```toml
name = "session-audit"
version = "1.0.0"
entrypoint = "plugin-entrypoint"
```

Set `version` to the version that your plugin reports.

Set `entrypoint` to the program that implements the plugin.

Keep the manifest at the top level of the plugin directory.

## Implement hooks

A plugin can implement these hooks:

| Hook | Runs when |
|---|---|
| `pre-run` | Before `tool` runs a command |
| `post-run` | After `tool` completes a command |
| `on-error` | When `tool` reports an error |

Use `pre-run` for checks that must happen before execution.

Use `post-run` for work that depends on a completed command.

Use `on-error` for failure handling.

The plugin entrypoint must follow the hook interface provided by the `tool` CLI. Keep each hook implementation separate so that one hook does not depend on another hook running.

## Create a first plugin

Create the plugin directory inside a project:

```sh
mkdir -p .tool/plugins/session-audit
```

Create `plugin.toml` with this content:

```toml
name = "session-audit"
version = "1.0.0"
entrypoint = "plugin-entrypoint"
```

Create the entrypoint file:

```text
.tool/plugins/session-audit/plugin-entrypoint
```

Implement the `pre-run`, `post-run`, and `on-error` behavior in that file according to the hook interface supported by your `tool` installation.

Make the entrypoint executable:

```sh
chmod +x .tool/plugins/session-audit/plugin-entrypoint
```

Your project should now contain:

```text
.tool/
└── plugins/
    └── session-audit/
        ├── plugin.toml
        └── plugin-entrypoint
```

## Test a plugin

Run the plugin against a recorded session:

```sh
tool plugin test .tool/plugins/session-audit
```

Replace the directory argument with the path to your plugin.

```sh
tool plugin test ~/ .tool/plugins/session-audit
```

Use the project-relative form when the plugin is under `./.tool/plugins`.

The test command runs the plugin against a recorded session. Use the result to verify each implemented hook.

## Avoid name clashes

Give each plugin a distinct `name`.

If `~/.tool/plugins/session-audit` and `./.tool/plugins/session-audit` both exist, `tool` uses the project plugin.

The project plugin applies only when you run `tool` from that project directory.

## Version a project plugin

Commit the complete plugin directory when the plugin belongs to a project.

```text
.tool/plugins/session-audit/plugin.toml
.tool/plugins/session-audit/plugin-entrypoint
```

Keep the `version` value in `plugin.toml` synchronized with the plugin release you distribute.

## Troubleshoot a plugin

Check that the plugin directory contains `plugin.toml`.

Check that `plugin.toml` defines `name`, `version`, and `entrypoint`.

Check that the entrypoint path matches the file in the plugin directory.

Check that the entrypoint has execute permission.

Check that the plugin uses the intended discovery directory.

Run the plugin test command against the exact directory you want to inspect:

```sh
tool plugin test ./.tool/plugins/session-audit
```

If two plugins share a `name`, inspect both discovery directories and use the project copy when you need project-specific behavior.
