# Writing Plugins for `tool`

This guide walks a developer through building their first `tool` plugin: what a plugin looks like on disk, how `tool` finds it, which hooks it can implement, and how to test it before you rely on it.

## What a Plugin Is

A `tool` plugin is a directory containing a manifest file named `plugin.toml`. The manifest declares the plugin's identity and tells `tool` where to find its code. At minimum, a manifest needs three fields:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "main.js"
```

- **`name`** — a unique identifier for the plugin. This is how `tool` refers to it in logs, error messages, and the plugin-clash resolution described below.
- **`version`** — a version string for your own tracking and for diagnostics when something behaves unexpectedly after an upgrade.
- **`entrypoint`** — the file `tool` loads and executes when it runs your plugin's hooks. The path is relative to the plugin directory.

A minimal plugin, then, is just two files:

```
my-plugin/
├── plugin.toml
└── main.js
```

## Where Plugins Live

`tool` looks for plugins in two locations:

1. **`~/.tool/plugins`** — the user-level directory. Plugins here are available in every project on the machine.
2. **`./.tool/plugins`** — the project-level directory, relative to the current working directory. Plugins here are scoped to the project.

Each location can contain multiple plugin directories, one per plugin.

### Name Clashes

If a plugin with the same `name` exists in both locations, **the project directory wins**. This lets a project override or pin a specific version of a plugin without affecting the user's other projects, and without needing to touch the user-level installation.

In practice: if you're developing a plugin, put a working copy in `./.tool/plugins` in the project you're testing it against. That copy takes precedence over anything installed globally, so you can iterate without disturbing your other projects.

## Hooks

A plugin participates in `tool`'s execution by implementing one or more hooks. All hooks are optional — implement only the ones your plugin needs. `tool` calls whichever hooks your entrypoint exports; you don't need to declare them in `plugin.toml`.

| Hook | When it runs |
|---|---|
| `pre-run` | Before `tool` executes the requested command. |
| `post-run` | After the command completes successfully. |
| `on-error` | When the command fails or exits with an error. |

A few things to keep in mind as you write hooks:

- **`pre-run`** is your chance to validate inputs, set up state, or short-circuit a run before it starts.
- **`post-run`** only fires on success — use it for cleanup, notifications, or reporting that should happen after a normal completion.
- **`on-error`** fires instead of `post-run` when something goes wrong, not in addition to it. If you need logic that always runs regardless of outcome, implement both `post-run` and `on-error` rather than relying on one to catch both cases.

Keep hooks fast and side-effect-aware: they run inline with the command, so a slow or failing hook affects every `tool` invocation that triggers it.

## Testing Your Plugin

Before trusting a plugin against real work, test it against a recorded session:

```
tool plugin test <dir>
```

Replace `<dir>` with the path to your plugin directory (the one containing `plugin.toml`). This command runs your plugin's hooks against a recorded session rather than a live command, so you can verify behavior — including `on-error` paths — without needing to reproduce a real failure.

Use this as your standard loop while developing:

1. Edit your entrypoint.
2. Run `tool plugin test <dir>`.
3. Check that each hook you implemented behaved as expected, including the error path if you implemented `on-error`.

## Putting It Together

A typical first-plugin workflow looks like this:

1. Create a directory under `./.tool/plugins` in the project you're working in.
2. Add a `plugin.toml` with `name`, `version`, and `entrypoint`.
3. Write your entrypoint file, implementing whichever of `pre-run`, `post-run`, or `on-error` your plugin needs.
4. Run `tool plugin test <dir>` and iterate until the recorded session behaves as expected.
5. Once you're satisfied, move (or copy) the plugin directory into `~/.tool/plugins` if you want it available across all your projects — remembering that a project-local copy, if left in place, will continue to take precedence for that project.
