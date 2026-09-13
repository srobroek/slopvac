# Plugin User Guide

A plugin extends the `tool` CLI by running custom code before a command, after it completes, or when it fails. Plugins sit in directories under `~/.tool/plugins` or `./.tool/plugins`, discovered and loaded automatically.

## Create your first plugin

Create a directory to hold your plugin code and configuration.

```bash
mkdir my-plugin
cd my-plugin
```

Add a `plugin.toml` manifest at the root of the directory.

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "plugin.sh"
```

Create the entrypoint script at `plugin.sh`.

```bash
#!/bin/bash
set -e

HOOK="$1"

case "$HOOK" in
  pre-run)
    echo "Running before the command"
    ;;
  post-run)
    echo "Running after the command succeeded"
    ;;
  on-error)
    echo "Running after the command failed"
    ;;
esac
```

Make the script executable.

```bash
chmod +x plugin.sh
```

Test the plugin from the repository root where you intend to use it.

```bash
tool plugin test ./my-plugin
```

The `test` command runs the plugin against a recorded session and reports any failures.

## Plugin manifest

The `plugin.toml` file declares the plugin's identity and entry point.

| Field | Type | Purpose |
|-------|------|---------|
| `name` | string | Unique identifier for the plugin. Used to resolve conflicts when multiple plugins have the same name. |
| `version` | string | Semantic version of the plugin. Report this version in logs to help users debug. |
| `entrypoint` | string | Relative path to the executable the `tool` CLI invokes. Must exist and be executable. |

## Plugin hooks

The `tool` CLI passes the hook name as the first argument to your entrypoint.

### pre-run

Runs before a `tool` command executes. Use it to validate preconditions, set up temporary resources, or modify the environment.

The exit code is ignored; the command runs regardless. Write errors to stderr so they appear in logs.

```bash
#!/bin/bash
HOOK="$1"

if [ "$HOOK" = "pre-run" ]; then
  if ! command -v required-tool &> /dev/null; then
    echo "Error: required-tool not found" >&2
  fi
fi
```

### post-run

Runs after the `tool` command completes successfully. Use it to clean up resources, upload logs, or trigger dependent actions.

The exit code is ignored. The command has already finished.

```bash
#!/bin/bash
HOOK="$1"

if [ "$HOOK" = "post-run" ]; then
  echo "Command completed at $(date)"
fi
```

### on-error

Runs when the `tool` command exits with a non-zero status. Use it to collect diagnostics, notify observers, or roll back side effects.

The exit code is ignored. The original command's failure is already reported.

```bash
#!/bin/bash
HOOK="$1"

if [ "$HOOK" = "on-error" ]; then
  echo "Command failed at $(date)" >&2
  # Collect diagnostic data
fi
```

## Access the command environment

The `tool` CLI sets environment variables your plugin can read. The exact set depends on the recorded session; check the test output to see what is available.

Write your entrypoint to handle missing variables gracefully.

```bash
#!/bin/bash
HOOK="$1"

if [ "$HOOK" = "pre-run" ]; then
  if [ -n "$TOOL_COMMAND" ]; then
    echo "About to run: $TOOL_COMMAND"
  fi
fi
```

## Plugin discovery

Plugins are discovered from two locations in order of precedence:

1. `./.tool/plugins` — the project-local directory, winning on name clash
2. `~/.tool/plugins` — the user's global plugin directory

Create a project-local plugin to override a global plugin of the same name. Name the directory after the plugin's `name` field in `plugin.toml`.

```
my-project/
├── .tool/
│   └── plugins/
│       └── my-plugin/
│           ├── plugin.toml
│           └── plugin.sh
└── ...
```

## Test a plugin

The `tool plugin test` command validates the plugin against a recorded session.

```bash
tool plugin test ./my-plugin
```

The command loads the `plugin.toml` manifest, executes the entrypoint with each hook, and reports success or failure.

Add the `--verbose` flag to see the hooks as they run.

```bash
tool plugin test --verbose ./my-plugin
```

Recorded sessions are stored in the `.tool/sessions` directory within the project. Each session file captures the command, arguments, environment, and output from a previous `tool` invocation. The `tool plugin test` command replays the recorded session and checks that your plugin hooks execute without errors.

If your plugin needs to be tested against a new or custom scenario, record a fresh session by running the command normally, then pass the session to `tool plugin test`.

```bash
tool plugin test ./my-plugin --session ./path/to/session
```
