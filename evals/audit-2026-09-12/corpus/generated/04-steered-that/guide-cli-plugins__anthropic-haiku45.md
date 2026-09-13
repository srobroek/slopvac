# Writing a `tool` CLI Plugin

A plugin extends `tool` by running code before execution (`pre-run`), after execution (`post-run`), or when execution fails (`on-error`).

## Create a plugin

A plugin is a directory containing a `plugin.toml` manifest file.

Create a directory for your plugin:

```bash
mkdir my-plugin
cd my-plugin
```

Create `plugin.toml` with a name, version, and the path to your executable:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "./plugin.sh"
```

Create the executable that `entrypoint` names. Your executable receives the hook name as the first argument:

```bash
#!/bin/bash
hook=$1
case "$hook" in
  pre-run)
    echo "Running before tool execution"
    ;;
  post-run)
    echo "Running after tool execution"
    ;;
  on-error)
    echo "Tool execution failed"
    ;;
esac
```

Make the executable:

```bash
chmod +x plugin.sh
```

## Install a plugin

Place your plugin directory in `~/.tool/plugins` to make it available to all projects:

```bash
cp -r my-plugin ~/.tool/plugins/
```

Place your plugin directory in `./.tool/plugins` at the repository root to make it available only to that project:

```bash
cp -r my-plugin ./.tool/plugins/
```

When a plugin name appears in both locations, the project directory version takes precedence.

## Hook reference

Your executable receives the hook name as the first argument. Each hook runs in sequence before or after the command completes.

### pre-run

The `pre-run` hook executes before `tool` runs your command. Use it for setup tasks, validation, or logging.

Your entrypoint receives `pre-run` as argument `$1`.

```bash
#!/bin/bash
if [ "$1" = "pre-run" ]; then
  echo "Preparing environment"
  export MY_VAR="value"
fi
```

### post-run

The `post-run` hook executes after `tool` runs your command and the command exits with code 0. Use it for cleanup, logging, or result processing.

Your entrypoint receives `post-run` as argument `$1`.

```bash
#!/bin/bash
if [ "$1" = "post-run" ]; then
  echo "Command completed successfully"
fi
```

### on-error

The `on-error` hook executes after `tool` runs your command and the command exits with a non-zero code. Use it for error reporting, rollback, or diagnostics.

Your entrypoint receives `on-error` as argument `$1`.

```bash
#!/bin/bash
if [ "$1" = "on-error" ]; then
  echo "Command failed with error code: $?"
fi
```

## Test a plugin

Use `tool plugin test <dir>` to run your plugin against a recorded session:

```bash
tool plugin test ./my-plugin
```

The test command loads your plugin and runs all three hooks in sequence. It verifies that your entrypoint executes without error.

## Plugin manifest reference

The `plugin.toml` file declares your plugin's identity and entry point.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | string | yes | Plugin identifier; used to resolve conflicts when the same name appears in both `~/.tool/plugins` and `./.tool/plugins` |
| `version` | string | yes | Semantic version; no specific validation |
| `entrypoint` | string | yes | Path to the executable; relative to the `plugin.toml` file location |

## Examples

### Example: Log command execution

Create a logging plugin that records every command run.

```toml
# plugin.toml
name = "logger"
version = "1.0.0"
entrypoint = "./log.sh"
```

```bash
#!/bin/bash
# log.sh
hook=$1
log_file="$HOME/.tool/commands.log"

case "$hook" in
  pre-run)
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Command started: $@" >> "$log_file"
    ;;
  post-run)
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Command completed" >> "$log_file"
    ;;
  on-error)
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Command failed" >> "$log_file"
    ;;
esac
```

### Example: Health check before execution

Create a plugin that verifies required services are healthy.

```toml
# plugin.toml
name = "health-check"
version = "1.0.0"
entrypoint = "./check.sh"
```

```bash
#!/bin/bash
# check.sh
hook=$1

if [ "$hook" = "pre-run" ]; then
  if ! command -v curl &> /dev/null; then
    echo "Error: curl is required" >&2
    exit 1
  fi
  
  if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "Error: health service unavailable" >&2
    exit 1
  fi
  
  echo "Health check passed"
fi
```

### Example: Cleanup on failure

Create a plugin that removes temporary files when a command fails.

```toml
# plugin.toml
name = "cleanup"
version = "1.0.0"
entrypoint = "./cleanup.sh"
```

```bash
#!/bin/bash
# cleanup.sh
hook=$1
tmp_dir="/tmp/tool-work"

if [ "$hook" = "on-error" ]; then
  if [ -d "$tmp_dir" ]; then
    rm -rf "$tmp_dir"
    echo "Cleanup completed"
  fi
fi
```
