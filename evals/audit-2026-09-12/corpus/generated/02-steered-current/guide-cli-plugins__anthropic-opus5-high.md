# Writing a `tool` Plugin

A plugin extends the `tool` CLI by running code at three points in a command's lifecycle. This guide takes you from an empty directory to a plugin verified by `tool plugin test`.

## Plugin layout

A plugin is a directory containing a `plugin.toml` manifest and the file that manifest names as its entrypoint.

```
my-plugin/
├── plugin.toml
└── main.py
```

## Write the manifest

`plugin.toml` requires three keys:

| Key | Type | Effect |
| --- | --- | --- |
| `name` | string | Identifies the plugin during discovery and in log output |
| `version` | string | Reported by `tool plugin list` |
| `entrypoint` | string | Path to the executable file, relative to the plugin directory |

```toml
name = "timer"
version = "0.1.0"
entrypoint = "main.py"
```

The entrypoint must be executable. Make it so before the first run:

```console
$ chmod +x my-plugin/main.py
```

## Install the plugin

`tool` discovers plugins from two directories:

| Directory | Scope |
| --- | --- |
| `~/.tool/plugins` | Every project run by this user |
| `./.tool/plugins` | The current project directory only |

If both directories hold a plugin whose manifest declares the same `name`, `tool` loads the one under `./.tool/plugins` and ignores the one under `~/.tool/plugins`. Use this to override a user-wide plugin for a single project.

Install the example as a project plugin:

```console
$ mkdir -p .tool/plugins
$ cp -r my-plugin .tool/plugins/
$ tool plugin list
timer 0.1.0  ./.tool/plugins/my-plugin
```

## Implement the hooks

A plugin implements one, two, or three hooks. `tool` calls the entrypoint once per hook, passing the hook name as the first argument.

| Hook | Called when |
| --- | --- |
| `pre-run` | Before `tool` executes the command |
| `post-run` | After the command finishes with exit code 0 |
| `on-error` | After the command finishes with a non-zero exit code |

`post-run` and `on-error` are mutually exclusive: a single command triggers one or the other, never both.

Dispatch on the first argument and exit 0 for any hook you do not implement:

```python
#!/usr/bin/env python3
import sys

hook = sys.argv[1]

if hook == "pre-run":
    print("timer: starting", file=sys.stderr)
elif hook == "on-error":
    print("timer: command failed", file=sys.stderr)

sys.exit(0)
```

Write diagnostics to stderr. `tool` reserves stdout for the command's own output.

A non-zero exit from `pre-run` cancels the command. A non-zero exit from `post-run` or `on-error` sets the exit code of the `tool` invocation.

## Test against a recorded session

`tool plugin test <dir>` runs a plugin against a recorded session, so you do not need to reproduce a failing command to exercise `on-error`. The command invokes each hook the session recorded and reports the exit code and stderr of each call.

```console
$ tool plugin test .tool/plugins/my-plugin
pre-run   exit 0   timer: starting
post-run  exit 0
2 hooks, 0 failures
```

Run it after every manifest or entrypoint change. A missing `entrypoint`, a manifest key with the wrong type, and a non-executable entrypoint all surface here rather than during a real command.

## Read the invocation context

`tool` passes the command's context in environment variables:

| Variable | Set for | Contents |
| --- | --- | --- |
| `TOOL_COMMAND` | All hooks | The subcommand name |
| `TOOL_ARGS` | All hooks | The subcommand arguments, newline-separated |
| `TOOL_CWD` | All hooks | Absolute path of the directory `tool` ran in |
| `TOOL_EXIT_CODE` | `post-run`, `on-error` | Exit code of the command, as a decimal string |

An `on-error` hook that reports the failing command reads two of them:

```python
#!/usr/bin/env python3
import os
import sys

if sys.argv[1] == "on-error":
    command = os.environ["TOOL_COMMAND"]
    code = os.environ["TOOL_EXIT_CODE"]
    print(f"timer: {command} exited {code}", file=sys.stderr)

sys.exit(0)
```

## Promote to a user-wide plugin

Once `tool plugin test` reports 0 failures, move the directory to `~/.tool/plugins` to load it in every project:

```console
$ mkdir -p ~/.tool/plugins
$ mv .tool/plugins/my-plugin ~/.tool/plugins/
$ tool plugin list
timer 0.1.0  ~/.tool/plugins/my-plugin
```
