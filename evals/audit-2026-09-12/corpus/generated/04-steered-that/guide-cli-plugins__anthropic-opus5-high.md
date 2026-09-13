# Writing a `tool` Plugin

A plugin extends the `tool` CLI by running code at three points in a command's lifecycle. This guide covers the manifest, the hooks, discovery, and the test command.

## Plugin layout

A plugin is a directory containing a `plugin.toml` manifest and the file named by its entrypoint:

```
my-plugin/
├── plugin.toml
└── main.py
```

## The manifest

`plugin.toml` requires three keys:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "main.py"
```

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `name` | string | none | Identifies the plugin during discovery and in `tool plugin` output. |
| `version` | string | none | Reported by `tool plugin list`. |
| `entrypoint` | string | none | Path to the executed file, relative to the plugin directory. |

All three keys are required. `tool` rejects a manifest that omits any of them.

## Discovery

`tool` reads plugins from two directories:

1. `~/.tool/plugins` — available to every project for the current user.
2. `./.tool/plugins` — relative to the working directory.

When both directories hold a plugin with the same `name`, the copy under `./.tool/plugins` runs and the copy under `~/.tool/plugins` is ignored. Rename one of them if you want both to run.

## Hooks

A plugin implements up to three hooks. Each hook is optional. Declare a hook by defining a function of that name in the entrypoint file.

| Hook | Runs when | Receives |
| --- | --- | --- |
| `pre-run` | Before `tool` executes the command. | The parsed command and its arguments. |
| `post-run` | After the command exits with status 0. | The command and its output. |
| `on-error` | After the command exits with a non-zero status. | The command and the error. |

`post-run` and `on-error` are mutually exclusive for a single command: `tool` calls exactly one of them.

## Write the first hook

Create the directory, the manifest, and the entrypoint:

```bash
mkdir -p .tool/plugins/timer
cd .tool/plugins/timer
```

Write `plugin.toml`:

```toml
name = "timer"
version = "0.1.0"
entrypoint = "main.py"
```

Write `main.py`:

```python
import time

_start = {}


def pre_run(command):
    _start[command.id] = time.monotonic()


def post_run(command, output):
    elapsed = time.monotonic() - _start.pop(command.id)
    print(f"{command.name} took {elapsed:.3f}s")


def on_error(command, error):
    _start.pop(command.id, None)
    print(f"{command.name} failed: {error}")
```

Hook names use underscores in Python: `pre_run` implements the `pre-run` hook.

## Test the plugin

`tool plugin test` runs a plugin against a recorded session, so you do not need to reproduce the original command:

```bash
tool plugin test .tool/plugins/timer
```

The command loads the manifest, calls each declared hook against the recorded session, and prints the return value of each hook. A manifest error or a raised exception makes `tool plugin test` exit with a non-zero status.

To confirm that discovery picks the plugin up, list what `tool` found:

```bash
tool plugin list
```

The output names each plugin, its version, and the directory it was loaded from.

## Errors in a hook

An exception raised in `pre-run` stops the command before it executes. An exception raised in `post-run` or `on-error` is reported after the command has already run, and it does not change the command's exit status.

## License

MIT
