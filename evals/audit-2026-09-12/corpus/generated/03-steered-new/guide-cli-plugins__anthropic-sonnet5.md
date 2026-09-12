```markdown
# Writing a `tool` plugin

A plugin is a directory containing a `plugin.toml` manifest and an entrypoint
script. `tool` loads plugins at startup and runs their hooks around each
command execution.

## Install

Create the plugin directory in one of two locations:

- `~/.tool/plugins/<plugin-name>/` — available to every project.
- `./.tool/plugins/<plugin-name>/` — available to the current project only.

If a plugin with the same name exists in both locations, `tool` loads the
project directory's copy and ignores the user directory's copy.

## Usage

Create `plugin.toml` in the plugin directory with three fields:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "main.sh"
```

- `name` — the plugin's identifier, used for the clash rule above.
- `version` — the plugin's version string.
- `entrypoint` — the path to the executable `tool` runs, relative to the
  plugin directory.

Make the entrypoint executable:

```sh
chmod +x main.sh
```

`tool` discovers the plugin on its next invocation. No registration step is
required beyond placing the directory under one of the two plugin paths.

## Hooks

An entrypoint implements any of three hooks. `tool` invokes the entrypoint
once per hook, passing the hook name as the first argument.

| Hook | Invoked | 
|---|---|
| `pre-run` | Before `tool` runs the command. |
| `post-run` | After the command finishes successfully. |
| `on-error` | After the command exits with a non-zero status. |

An entrypoint that ignores an argument it does not handle exits `0` for that
hook.

### Example: `pre-run` hook

```sh
#!/usr/bin/env bash
case "$1" in
  pre-run)
    echo "starting run"
    ;;
esac
```

## Testing a plugin

Run the plugin against a recorded session with:

```sh
tool plugin test <dir>
```

`<dir>` is the path to the plugin directory. The command replays the recorded
session's hook invocations against the plugin's entrypoint and reports the
exit status and output of each hook.

## Configuration

| Field | Type | Default | Effect |
|---|---|---|---|
| `name` | string | none, required | Identifies the plugin; determines the winner on a directory-name clash. |
| `version` | string | none, required | Records the plugin's version. |
| `entrypoint` | string | none, required | Path, relative to the plugin directory, to the executable `tool` invokes. |

## License

See the `tool` project's `LICENSE` file.
```
