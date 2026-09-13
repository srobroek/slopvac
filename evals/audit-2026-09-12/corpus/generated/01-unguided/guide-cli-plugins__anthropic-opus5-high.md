# Writing a `tool` Plugin

A plugin extends `tool` with your own behavior at three points in a run: before the command executes, after it finishes, and when it fails. This guide walks through building your first plugin, from an empty directory to a tested hook.

## What a plugin is

A plugin is a directory containing a `plugin.toml` manifest and an executable entrypoint. There is no registry, no build step, and no compilation. If the directory is in a place `tool` looks, and the manifest parses, the plugin loads.

## Create the directory

Start in your project. Create the plugin directory and the manifest:

```
mkdir -p .tool/plugins/timer
cd .tool/plugins/timer
```

Write `plugin.toml`:

```toml
name = "timer"
version = "0.1.0"
entrypoint = "./timer.sh"
```

All three fields are required.

`name` identifies the plugin. It is the name `tool` prints in logs and errors, and the name used to resolve clashes between plugin directories. Keep it identical to the directory name unless you have a reason not to; a mismatch is legal but makes the plugin harder to find when something goes wrong.

`version` is your own version string. `tool` records it but does not interpret it.

`entrypoint` is the path to the program `tool` runs, relative to the plugin directory. It must be executable. A shell script, a Python file with a shebang, a compiled binary — anything the operating system can execute directly.

## Write the entrypoint

`tool` invokes the entrypoint once per hook, passing the hook name as the first argument. A single entrypoint therefore handles all three hooks, and dispatches on that argument.

Create `timer.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

hook="$1"

case "$hook" in
  pre-run)
    date +%s > /tmp/tool-timer-start
    ;;
  post-run)
    start=$(cat /tmp/tool-timer-start)
    echo "elapsed: $(( $(date +%s) - start ))s"
    ;;
  on-error)
    echo "run failed; timing discarded"
    ;;
esac
```

Make it executable:

```
chmod +x timer.sh
```

A plugin only needs to handle the hooks it cares about. Exiting cleanly on an unrecognized hook name — as the `case` above does — is the simplest way to opt out of the rest.

## The three hooks

**`pre-run`** fires before the command executes. Use it to check preconditions, warm a cache, record a start time, or refuse the run outright. This is the only hook that runs before any real work happens, so it is the only place where declining to proceed is cheap.

**`post-run`** fires after the command finishes successfully. Use it to report results, clean up scratch state, or trigger something downstream.

**`on-error`** fires when the command fails. Use it to capture diagnostics, roll back partial state, or annotate the failure with context `tool` does not have. `post-run` does not fire on a failed run, so cleanup that must happen either way belongs in both hooks — or, better, in a helper both call.

## Where `tool` looks for plugins

`tool` discovers plugins from two directories:

- `~/.tool/plugins` — your user plugins, active in every project.
- `./.tool/plugins` — the current project's plugins, active only here.

Every subdirectory of those paths containing a valid `plugin.toml` is loaded.

When a plugin in the project directory has the same `name` as one in your home directory, **the project directory wins**. The user-level plugin is not loaded at all; it is replaced, not merged or chained. This lets a project pin a specific version or behavior of a plugin without asking every contributor to change their own configuration — and it means a project can shadow a plugin you rely on. If a personal plugin stops firing in one repository, check that repository's `.tool/plugins` for a directory declaring the same `name`.

Commit project plugins alongside the code they serve. A plugin in `./.tool/plugins` that is not in version control works for you and nobody else.

## Test the plugin

Run the plugin against a recorded session:

```
tool plugin test .tool/plugins/timer
```

This exercises your hooks against captured session data rather than a live command, so you can iterate without side effects on real work. Run it after every change to the entrypoint. It is the fastest way to catch the two failures that dominate a first plugin: a manifest field that does not parse, and an entrypoint that is not executable.

Test the failure path too, not just the happy one. `on-error` is the hook most likely to be written once and never exercised, and a broken `on-error` surfaces at the worst possible moment — while you are already debugging something else.

## Checklist

Before you consider the plugin finished:

- `plugin.toml` declares `name`, `version`, and `entrypoint`.
- The entrypoint file exists at the declared relative path and is executable.
- Each hook you implement is dispatched on the first argument.
- Unimplemented hooks exit cleanly.
- Cleanup that must happen on both success and failure is reachable from `post-run` and `on-error`.
- `tool plugin test <dir>` passes.
- A project plugin is committed to version control.
