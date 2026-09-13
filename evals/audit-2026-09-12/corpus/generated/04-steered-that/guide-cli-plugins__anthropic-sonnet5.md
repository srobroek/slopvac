# Writing a Plugin for `tool`

A plugin extends `tool` with custom behavior at defined points in a run. This guide covers the plugin directory layout, the manifest format, the available hooks, and testing a plugin before you install it.

## Install

Place your plugin directory under one of two locations:

- `~/.tool/plugins/<plugin-name>` — available to every project on the machine.
- `./.tool/plugins/<plugin-name>` — available to the current project only.

If a plugin name exists in both locations, `tool` loads the project-directory version.

## Usage

Create a directory containing a `plugin.toml` manifest and an entrypoint file:

```
.tool/plugins/my-plugin/
├── plugin.toml
└── main.sh
```

`plugin.toml`:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "main.sh"
```

`tool` discovers the plugin on its next run and invokes the entrypoint at each hook the entrypoint implements.

## Examples

### Log every run

```toml
name = "run-logger"
version = "1.0.0"
entrypoint = "logger.sh"
```

`logger.sh`:

```sh
#!/bin/sh
case "$TOOL_HOOK" in
  pre-run)
    echo "starting run $TOOL_RUN_ID" >> run.log
    ;;
esac
```

### Report errors to a webhook

```toml
name = "error-reporter"
version = "1.0.0"
entrypoint = "report.sh"
```

`report.sh`:

```sh
#!/bin/sh
case "$TOOL_HOOK" in
  on-error)
    curl -X POST -d "run $TOOL_RUN_ID failed" "$WEBHOOK_URL"
    ;;
esac
```

## Hooks

A plugin implements any of three hooks. `tool` calls the entrypoint once per hook, passing the hook name so the entrypoint can dispatch on it.

| Hook | Called when |
|---|---|
| `pre-run` | Before `tool` starts the run. |
| `post-run` | After the run finishes successfully. |
| `on-error` | After the run exits with a non-zero status. |

## Configuration

`plugin.toml` fields:

| Name | Type | Default | Effect |
|---|---|---|---|
| `name` | string | none, required | Identifies the plugin. Used to resolve name clashes between the two plugin directories. |
| `version` | string | none, required | Identifies the plugin release. |
| `entrypoint` | string | none, required | Path, relative to the plugin directory, to the executable `tool` runs for each hook. |

## Testing a plugin

Run `tool plugin test <dir>` against a recorded session to exercise the plugin's hooks without a live run:

```sh
tool plugin test .tool/plugins/my-plugin
```

The command loads the manifest at `<dir>/plugin.toml`, replays the recorded session's `pre-run`, `post-run`, and `on-error` events in order, and invokes the entrypoint for each hook the entrypoint implements.

## License

See `LICENSE` in the `tool` repository.
