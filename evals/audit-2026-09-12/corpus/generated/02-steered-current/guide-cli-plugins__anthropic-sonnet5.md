# Writing a plugin for `tool`

A plugin is a directory containing a `plugin.toml` manifest and an entrypoint script. `tool` loads plugins at startup and runs their hooks around each command.

## Install

Create a plugin directory in one of two locations:

- `~/.tool/plugins/<plugin-name>/` — available to every project.
- `./.tool/plugins/<plugin-name>/` — available to the current project.

If a plugin name exists in both locations, `tool` loads the project directory's version.

## Usage

Create a directory and add a `plugin.toml` manifest:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "main.sh"
```

Place `main.sh` (or your entrypoint file) in the same directory. `tool` invokes the entrypoint for each hook the plugin implements.

Test the plugin against a recorded session before installing it:

```sh
tool plugin test ./my-plugin
```

## Manifest fields

| Field | Type | Default | Effect |
|---|---|---|---|
| `name` | string | none, required | Identifies the plugin; used to resolve name clashes between the two plugin directories. |
| `version` | string | none, required | Identifies the plugin's version. |
| `entrypoint` | string | none, required | Path, relative to the plugin directory, to the script `tool` executes for each hook. |

## Hooks

A plugin implements zero or more of these hooks. `tool` calls the entrypoint with a hook name argument; the entrypoint decides what to run for each one.

- `pre-run` — runs before `tool` executes the command.
- `post-run` — runs after the command completes successfully.
- `on-error` — runs after the command exits with an error.

## Examples

### Log every command before it runs

`plugin.toml`:

```toml
name = "logger"
version = "0.1.0"
entrypoint = "logger.sh"
```

`logger.sh`:

```sh
#!/bin/sh
case "$1" in
  pre-run)
    echo "running: $TOOL_COMMAND" >> ./logger.log
    ;;
esac
```

### Send an alert on failure

`plugin.toml`:

```toml
name = "alerter"
version = "0.1.0"
entrypoint = "alerter.sh"
```

`alerter.sh`:

```sh
#!/bin/sh
case "$1" in
  on-error)
    echo "command failed: $TOOL_COMMAND (exit $TOOL_EXIT_CODE)" >&2
    ;;
esac
```

## Testing a plugin

Run `tool plugin test <dir>` to execute a plugin's hooks against a recorded session:

```sh
tool plugin test ./my-plugin
```

The command loads the manifest at `<dir>/plugin.toml`, runs each hook the plugin implements, and reports the entrypoint's exit code and output for each hook.

## License

MIT
