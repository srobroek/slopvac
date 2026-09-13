# Writing a `tool` Plugin

A plugin extends the `tool` CLI with code that runs before a command, after a command, or when a command fails.

## Plugin layout

A plugin is a directory containing a `plugin.toml` manifest and the executable named by the manifest's `entrypoint` field.

```
my-plugin/
├── plugin.toml
└── main.py
```

## Write the manifest

`plugin.toml` requires three fields.

```toml
name = "timing"
version = "0.1.0"
entrypoint = "main.py"
```

| Field | Type | Effect |
| --- | --- | --- |
| `name` | string | Identifies the plugin. Two plugins with the same name collide during discovery. |
| `version` | string | Reported by `tool plugin list`. |
| `entrypoint` | string | Path to the executable, relative to the plugin directory. |

`tool` reads no other keys from `plugin.toml`.

## Discovery order

`tool` searches two directories for plugin subdirectories:

1. `~/.tool/plugins` — available to every project for the current user.
2. `./.tool/plugins` — available inside the current project directory.

When both directories hold a plugin with the same `name`, `tool` loads the one under `./.tool/plugins` and ignores the one under `~/.tool/plugins`. Copy a user-level plugin into `./.tool/plugins` to override it for one project.

## Implement a hook

A plugin implements one, two, or all three of these hooks:

| Hook | Runs |
| --- | --- |
| `pre-run` | Before `tool` executes the command. |
| `post-run` | After the command exits successfully. |
| `on-error` | After the command exits with a failure. |

`tool` invokes the entrypoint once per hook and passes the hook name as the first argument. Dispatch on that argument.

```python
#!/usr/bin/env python3
import sys

hook = sys.argv[1]

if hook == "pre-run":
    print("starting")
elif hook == "post-run":
    print("finished")
elif hook == "on-error":
    print("failed")
```

Make the entrypoint executable before `tool` runs it:

```console
$ chmod +x my-plugin/main.py
```

A hook that exits non-zero on `pre-run` cancels the command. A non-zero exit from `post-run` or `on-error` does not change the command's own exit status.

## Test the plugin

`tool plugin test` runs a plugin against a recorded session, so you do not have to reproduce a failing command to exercise `on-error`.

```console
$ tool plugin test ./my-plugin
pre-run   ok  (4 ms)
post-run  ok  (3 ms)
on-error  ok  (3 ms)
```

The command reports one line per hook the plugin implements, with the exit status and the wall-clock duration. A hook that exits non-zero is reported as `fail`, and `tool plugin test` exits 1.

Pass a directory path, not a plugin name. The directory does not need to sit under a discovery path, so you can test a plugin from a checkout before you install it.

## Install the plugin

Copy or symlink the plugin directory into a discovery path:

```console
$ mkdir -p ~/.tool/plugins
$ ln -s "$PWD/my-plugin" ~/.tool/plugins/my-plugin
```

Confirm `tool` found it:

```console
$ tool plugin list
timing  0.1.0  ~/.tool/plugins/my-plugin
```
