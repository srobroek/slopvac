# Write a `tool` plugin

A `tool` plugin adds lifecycle behavior through an entrypoint and up to three hooks.

## Create the plugin directory

Create one directory containing the manifest and entrypoint:

```text
session-check/
├── plugin.toml
└── session-check
```

Add `plugin.toml` at the plugin directory root:

```toml
name = "session-check"
version = "0.1.0"
entrypoint = "session-check"
```

Configure all three manifest fields:

| Name | Type | Default | Effect |
| --- | --- | --- | --- |
| `name` | string | Required | Identifies the plugin during discovery and name-clash resolution. |
| `version` | string | Required | Identifies the plugin version. |
| `entrypoint` | string | Required | Identifies the plugin implementation. |

Add the implementation named by `entrypoint` to the plugin directory.

## Implement hooks

The entrypoint can implement any subset of these hooks:

| Hook | Invocation |
| --- | --- |
| `pre-run` | Before a run starts. |
| `post-run` | After a run completes. |
| `on-error` | When a run produces an error. |

Use `pre-run` for behavior that must occur before the run.

Use `post-run` for behavior that must occur after the run completes.

Use `on-error` for behavior that must occur when the run produces an error.

## Test the plugin

Run the plugin against a recorded session:

```console
tool plugin test ./session-check
```

After changing `plugin.toml`, the entrypoint, or a hook, rerun `tool plugin test <dir>`.

## Install the plugin

Install the complete plugin directory under one discovery path:

| Scope | Discovery path |
| --- | --- |
| User | `~/.tool/plugins` |
| Project | `./.tool/plugins` |

For user discovery, install `session-check` at:

```text
~/.tool/plugins/session-check/
```

For project discovery, install `session-check` at:

```text
./.tool/plugins/session-check/
```

If both paths contain the same plugin name, `tool` uses the plugin from `./.tool/plugins`.
