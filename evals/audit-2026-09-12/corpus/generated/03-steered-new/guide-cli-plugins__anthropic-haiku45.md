# Plugin Guide for the tool CLI

A plugin extends the `tool` CLI with custom behavior at three points: before a command runs, after it completes, and when it fails. Build your first plugin by creating a manifest, writing a script, and testing against recorded sessions.

## Plugin structure

A plugin is a directory containing two files:

- `plugin.toml`: a manifest that declares the plugin name, version, and entry point.
- A script or executable at the path named in `entrypoint`.

Place your plugin directory in `~/.tool/plugins` or `./.tool/plugins`. When both directories define a plugin with the same name, the project directory plugin loads.

## Create a plugin

Create a new directory for your plugin.

```bash
mkdir ~/.tool/plugins/my-plugin
```

Write a `plugin.toml` manifest in the plugin directory.

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "plugin.sh"
```

Create the entrypoint script at `plugin.sh` in the same directory.

```bash
#!/bin/bash
set -e

HOOK="$1"
EXIT_CODE="${2:-0}"

case "$HOOK" in
  pre-run)
    echo "Running command: $3"
    ;;
  post-run)
    echo "Command completed with code $EXIT_CODE"
    ;;
  on-error)
    echo "Command failed with code $EXIT_CODE"
    ;;
esac
```

Make the script executable.

```bash
chmod +x ~/.tool/plugins/my-plugin/plugin.sh
```

## Hooks

The `tool` CLI invokes your entrypoint with a hook name as the first argument. Implement the hooks you need; omit the others.

### pre-run

The CLI invokes `pre-run` before running the command. Use this hook to set up dependencies, validate input, or log the start of an operation.

Your entrypoint receives three arguments:

- `$1`: the string `pre-run`
- `$2`: the full command line that will run (as a single string)
- `$3`: the working directory

Exit with code 0 to allow the command to proceed. Exit with a nonzero code to stop the command before it starts.

### post-run

The CLI invokes `post-run` after the command exits successfully. Use this hook to clean up resources, publish results, or record metrics.

Your entrypoint receives two arguments:

- `$1`: the string `post-run`
- `$2`: the exit code of the command (always 0 for this hook)

Your hook's exit code does not affect the command's result.

### on-error

The CLI invokes `on-error` when the command exits with a nonzero code. Use this hook to retry the command, alert a service, or capture diagnostics.

Your entrypoint receives two arguments:

- `$1`: the string `on-error`
- `$2`: the nonzero exit code of the command

Your hook's exit code does not affect the command's result.

## Test your plugin

Record a session that the plugin will replay during testing.

```bash
tool session record --output session.json -- some-command arg1 arg2
```

Test the plugin against the session.

```bash
tool plugin test ./my-plugin --session session.json
```

The test harness calls your entrypoint with each hook in sequence and verifies that your script runs without error. Fix any issues and test again.

## Example: log command timing

This plugin logs the time when each command starts and stops.

Create the plugin directory.

```bash
mkdir ~/.tool/plugins/timer
```

Write `plugin.toml`.

```toml
name = "timer"
version = "0.1.0"
entrypoint = "timer.sh"
```

Write `timer.sh`.

```bash
#!/bin/bash

HOOK="$1"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
LOGFILE="$HOME/.tool/timer.log"

case "$HOOK" in
  pre-run)
    echo "[$TIMESTAMP] START: $2" >> "$LOGFILE"
    ;;
  post-run)
    echo "[$TIMESTAMP] END: exit code $2" >> "$LOGFILE"
    ;;
  on-error)
    echo "[$TIMESTAMP] ERROR: exit code $2" >> "$LOGFILE"
    ;;
esac
```

Make it executable.

```bash
chmod +x ~/.tool/plugins/timer/timer.sh
```

Test it.

```bash
tool plugin test ~/.tool/plugins/timer --session /path/to/session.json
```

## Plugin manifest reference

The `plugin.toml` file must include these fields.

| Field | Type | Effect |
|-------|------|--------|
| `name` | string | The plugin identifier. Must be unique within your plugin directories. |
| `version` | string | The semantic version of the plugin (format: `major.minor.patch`). |
| `entrypoint` | string | The relative path to the executable file in the plugin directory. |
