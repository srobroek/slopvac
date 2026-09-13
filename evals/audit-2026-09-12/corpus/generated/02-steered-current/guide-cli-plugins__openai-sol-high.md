# Write a `tool` CLI plugin

A `tool` plugin adds lifecycle hooks to command runs through an entrypoint defined in `plugin.toml`.

## Create the plugin directory

Create one directory for the plugin in either supported location:

| Location | Scope |
|---|---|
| `~/.tool/plugins/<name>` | User |
| `./.tool/plugins/<name>` | Project |

A plugin directory contains the manifest and its entrypoint:

```text
.tool/plugins/session-audit/
├── plugin.toml
└── plugin
```

## Add the manifest

Create `plugin.toml` in the plugin directory:

```toml
name = "session-audit"
version = "1.0.0"
entrypoint = "./plugin"
```

The manifest requires three fields:

| Name | Type | Default | Effect |
|---|---|---|---|
| `name` | String | None | Identifies the plugin during discovery and name-clash resolution. |
| `version` | String | None | Identifies the plugin version. |
| `entrypoint` | String | None | Specifies the plugin entrypoint. |

Create the file or command referenced by `entrypoint` inside the plugin directory.

## Implement hooks

The entrypoint can implement three hooks:

| Hook | Invocation |
|---|---|
| `pre-run` | Before a command runs |
| `post-run` | After a command runs |
| `on-error` | When a command run ends with an error |

Implement only the hooks that the plugin needs.

## Test the plugin

Run `tool plugin test` with the plugin directory:

```sh
tool plugin test .tool/plugins/session-audit
```

The command loads the plugin from `.tool/plugins/session-audit` and runs it against a recorded session.

Test the plugin after changing its manifest, entrypoint, or hook implementation.

## Install the plugin

Place a user plugin under `~/.tool/plugins`:

```text
~/.tool/plugins/session-audit/
├── plugin.toml
└── plugin
```

Place a project plugin under `./.tool/plugins`:

```text
.tool/plugins/session-audit/
├── plugin.toml
└── plugin
```

The `tool` CLI discovers plugins from both directories.

If both directories contain the same plugin name, `tool` loads the plugin from `./.tool/plugins`.
