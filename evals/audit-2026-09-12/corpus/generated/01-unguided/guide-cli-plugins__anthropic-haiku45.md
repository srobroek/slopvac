# Plugin Development Guide for `tool` CLI

## Introduction

Plugins for the `tool` CLI let you extend functionality with custom logic that runs before commands, after commands complete, or when errors occur. This guide walks you through creating your first plugin.

## What Are Plugins?

Plugins are directories containing a manifest and scripts that hook into the `tool` CLI execution lifecycle. They let you:

- Validate or prepare the environment before running commands
- Process or log command output after execution
- Handle errors gracefully with custom recovery logic
- Share reusable extensions across projects and machines

## Plugin Structure

A plugin is a directory with the following structure:

```
my-plugin/
├── plugin.toml          # Plugin manifest (required)
├── pre-run.sh           # Optional: runs before the command
├── post-run.sh          # Optional: runs after the command succeeds
└── on-error.sh          # Optional: runs when the command fails
```

Each hook script (`.sh` files) is optional—only implement the hooks your plugin needs.

## Plugin Manifest: `plugin.toml`

The `plugin.toml` file is required and defines your plugin's metadata:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "pre-run.sh"
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier for your plugin (alphanumeric, hyphens allowed). Used when discovering and testing plugins. |
| `version` | Yes | Semantic version of your plugin (e.g., `0.1.0`, `1.0.0`). No version constraint matching—this is informational. |
| `entrypoint` | Yes | Path to the primary script, relative to the plugin directory. Typically `pre-run.sh`, `post-run.sh`, or `on-error.sh`. |

## Plugin Discovery

Plugins are discovered from two locations, with the project directory taking precedence:

1. **Project plugins** (highest priority): `./.tool/plugins/` (in your project root)
2. **User plugins** (fallback): `~/.tool/plugins/` (in your home directory)

When two plugins have the same `name`, the one in `./.tool/plugins/` is used.

Example directory layout:

```
~/.tool/plugins/          # User plugins (globally available)
├── audit-logs/
└── env-setup/

my-project/
├── .tool/plugins/        # Project plugins (override user plugins)
│   └── audit-logs/       # This version takes precedence
└── tool.toml
```

## Plugin Hooks

### `pre-run` Hook

Runs **before** the command executes.

**Use cases:**
- Validate environment variables
- Create temporary directories or setup files
- Log command invocation details
- Check prerequisites

**Example: `pre-run.sh`**

```bash
#!/bin/bash
set -e

echo "[pre-run] Starting environment setup..."

# Validate required environment variable
if [ -z "$API_KEY" ]; then
  echo "[pre-run] ERROR: API_KEY is not set"
  exit 1
fi

# Create a temporary working directory
export PLUGIN_TEMP=$(mktemp -d)
echo "[pre-run] Created temporary directory: $PLUGIN_TEMP"

# Export for the command to use
export PLUGIN_TEMP
```

**Environment:**
- All parent shell environment variables are available
- Exit with status `0` to continue; non-zero to abort the command

### `post-run` Hook

Runs **after** the command completes successfully.

**Use cases:**
- Archive or backup command output
- Upload logs to a service
- Trigger dependent tasks
- Clean up temporary files

**Example: `post-run.sh`**

```bash
#!/bin/bash
set -e

echo "[post-run] Command completed successfully"

# Archive the temporary directory
if [ -n "$PLUGIN_TEMP" ] && [ -d "$PLUGIN_TEMP" ]; then
  tar -czf "$HOME/backups/plugin-run-$(date +%s).tar.gz" "$PLUGIN_TEMP"
  rm -rf "$PLUGIN_TEMP"
  echo "[post-run] Archived and cleaned up temporary files"
fi

# Log successful run
echo "[post-run] Run logged at $(date)"
```

**Environment:**
- All parent shell environment variables
- Command exit code available (typically `0`)
- Exit status of `post-run` does not affect overall success

### `on-error` Hook

Runs when the command **fails** (exits with non-zero status).

**Use cases:**
- Log error details with context
- Attempt automatic recovery
- Notify monitoring systems
- Clean up partial state

**Example: `on-error.sh`**

```bash
#!/bin/bash

# Do NOT use set -e; we need to handle errors gracefully

COMMAND_EXIT_CODE=$1  # First argument: command's exit code

echo "[on-error] Command failed with exit code: $COMMAND_EXIT_CODE"

# Attempt recovery
if [ "$COMMAND_EXIT_CODE" -eq 127 ]; then
  echo "[on-error] Command not found. Installing dependencies..."
  # Installation logic here
  exit 0  # Recovered
fi

# Log error for analysis
mkdir -p "$HOME/.tool/error-logs"
cat > "$HOME/.tool/error-logs/error-$(date +%s).log" <<EOF
Command failed at: $(date)
Exit code: $COMMAND_EXIT_CODE
Working directory: $(pwd)
User: $(whoami)
EOF

echo "[on-error] Error logged and handled"
exit 0
```

**Environment:**
- All parent shell environment variables
- **First argument (`$1`)**: exit code of the failed command
- Exit status of `on-error` does not affect the overall command's reported failure

## Testing Your Plugin

Use `tool plugin test <dir>` to run your plugin against a recorded session.

```bash
# Test a plugin in the current project
tool plugin test ./.tool/plugins/my-plugin

# Test a user plugin
tool plugin test ~/.tool/plugins/my-plugin

# Test with verbose output (if supported)
tool plugin test --verbose ./.tool/plugins/my-plugin
```

The test command replays a pre-recorded execution scenario and verifies your hooks run correctly.

## Best Practices

### 1. Always Start with `set -e`

Unless you need to handle errors manually (like in `on-error`), begin scripts with `set -e` to fail fast:

```bash
#!/bin/bash
set -e
```

### 2. Use Meaningful Logging

Prefix log messages with your plugin name and hook type for clarity:

```bash
echo "[my-plugin:pre-run] Starting setup..."
```

### 3. Make Scripts Idempotent

Plugins may run multiple times. Design them to safely re-run:

```bash
# Bad: creates files every time
mkdir "$PLUGIN_TEMP"

# Good: checks if it exists first
mkdir -p "$PLUGIN_TEMP"
```

### 4. Clean Up Resources

Temporary files, processes, and environment changes should be cleaned up:

```bash
# In on-error or post-run:
trap 'rm -rf "$PLUGIN_TEMP"' EXIT
```

### 5. Use Environment Variables for Configuration

Avoid hardcoding paths or settings. Let users configure via environment:

```bash
# Read from environment with a sensible default
LOG_LEVEL="${PLUGIN_LOG_LEVEL:-info}"
TEMP_DIR="${PLUGIN_TEMP_DIR:-/tmp/plugin}"
```

### 6. Document Your Plugin

Add a `README.md` in your plugin directory explaining:

- What the plugin does
- Required environment variables
- Example usage
- Troubleshooting

Example `README.md`:

```markdown
# My Plugin

Validates environment setup and logs command execution.

## Requirements

- `API_KEY` environment variable must be set
- Bash 4.0+

## Configuration

- `PLUGIN_LOG_LEVEL`: Set to `debug` for verbose output (default: `info`)
- `PLUGIN_TEMP_DIR`: Override temporary directory location

## Example

```bash
export API_KEY="my-secret-key"
tool plugin install ~/.tool/plugins/my-plugin
```
```

### 7. Handle Versions Carefully

Update your plugin version in `plugin.toml` when making changes. Users may rely on plugin version for compatibility decisions.

## Example: A Complete Plugin

Here's a simple audit plugin that logs all commands executed in a project:

**`.tool/plugins/audit/plugin.toml`**

```toml
name = "audit"
version = "1.0.0"
entrypoint = "pre-run.sh"
```

**`.tool/plugins/audit/pre-run.sh`**

```bash
#!/bin/bash
set -e

# Create audit directory if it doesn't exist
AUDIT_DIR=".tool/audit-logs"
mkdir -p "$AUDIT_DIR"

# Log the command being executed
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$TIMESTAMP | Command: $@" >> "$AUDIT_DIR/commands.log"

echo "[audit:pre-run] Logged command execution"
```

**`.tool/plugins/audit/on-error.sh`**

```bash
#!/bin/bash

EXIT_CODE=$1
AUDIT_DIR=".tool/audit-logs"
mkdir -p "$AUDIT_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$TIMESTAMP | ERROR: exit code $EXIT_CODE" >> "$AUDIT_DIR/errors.log"

echo "[audit:on-error] Logged error"
exit 0
```

Test your plugin:

```bash
tool plugin test ./.tool/plugins/audit
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not discovered | Verify plugin is in `./.tool/plugins/` or `~/.tool/plugins/` and `plugin.toml` exists. |
| Script permission denied | Ensure scripts are executable: `chmod +x pre-run.sh` |
| Environment variables not accessible | Verify they're exported in the parent shell or set via `export` in a parent script. |
| `on-error` hook didn't run | Check that your command actually failed (exit code non-zero). |
| Changes not taking effect | If using project plugins, ensure `./.tool/plugins/` takes precedence over user plugins. |

## Next Steps

- Explore existing plugins in `~/.tool/plugins/` for inspiration
- Share your plugin: add it to your project or publish for team use
- Join the community: contribute plugins back or discuss plugin ideas

---

**Version:** 1.0  
**Last Updated:** 2026-09-12
