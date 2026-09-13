# Write a `tool` CLI Plugin

A `tool` plugin is a directory containing a manifest and an entrypoint. Plugins can react before or after a run and when a run fails.

## Plugin structure

Create a directory for your plugin:

```text
my-plugin/
├── plugin.toml
└── bin/
    └── my-plugin
```

The directory must contain a `plugin.toml` manifest with these fields:

- `name`: The plugin’s unique name.
- `version`: The plugin version.
- `entrypoint`: The executable that implements the plugin.

For example:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "bin/my-plugin"
```

Treat the entrypoint as relative to the plugin directory. Ensure that it exists and is executable:

```sh
chmod +x bin/my-plugin
```

## Implement hooks

A plugin can implement any combination of these hooks:

| Hook | When it runs | Common uses |
|---|---|---|
| `pre-run` | Before a run starts | Validate inputs, prepare resources, or record metadata |
| `post-run` | After a successful run | Publish results, clean up resources, or emit notifications |
| `on-error` | When a run fails | Collect diagnostics, report failures, or perform recovery |

You do not need to implement all three hooks. Start with the hook required by your use case, then add others as needed.

Keep hook behavior focused:

- Make `pre-run` fast so it does not delay every run.
- Avoid changing successful results in `post-run`.
- Preserve the original failure when handling `on-error`.
- Write diagnostic messages that identify the plugin and hook.
- Do not assume that another hook has already run successfully.

## Test the plugin

Before installing the plugin, run it against a recorded session:

```sh
tool plugin test ./my-plugin
```

The command loads the plugin from the specified directory and exercises it using the recorded session. Use it to verify:

- The manifest parses correctly.
- The entrypoint can be found and executed.
- Each implemented hook handles the session data.
- Successful and failed runs produce the expected behavior.
- Diagnostics are clear when the plugin encounters invalid input.

Run the test again whenever you change the manifest, entrypoint, or hook behavior.

## Install the plugin

Plugins are discovered from two locations:

| Location | Scope |
|---|---|
| `~/.tool/plugins` | Available to all of your projects |
| `./.tool/plugins` | Available only in the current project |

### User-level installation

Install a plugin for your user account by copying its directory into `~/.tool/plugins`:

```sh
mkdir -p ~/.tool/plugins
cp -R ./my-plugin ~/.tool/plugins/my-plugin
```

The resulting layout should resemble:

```text
~/.tool/plugins/
└── my-plugin/
    ├── plugin.toml
    └── bin/
        └── my-plugin
```

### Project-level installation

Install a plugin for one project by copying it into that project’s `.tool/plugins` directory:

```sh
mkdir -p .tool/plugins
cp -R ./my-plugin .tool/plugins/my-plugin
```

Project-level plugins can be committed with the project when all contributors should use the same plugin.

## Understand name clashes

Plugin identity comes from the manifest’s `name` field, not only from its directory name.

If a user-level plugin and a project-level plugin have the same name, the project-level plugin wins. For example, given these manifests:

```text
~/.tool/plugins/logger/plugin.toml
./.tool/plugins/custom-logger/plugin.toml
```

If both declare:

```toml
name = "logger"
```

`tool` uses the plugin from `./.tool/plugins/custom-logger`.

This precedence lets a project replace or pin a plugin without modifying the user-level installation. To avoid accidental overrides, choose a distinctive name and check both plugin locations when troubleshooting discovery.

## Recommended development workflow

1. Create the plugin directory and `plugin.toml`.
2. Implement one hook in the entrypoint.
3. Make the entrypoint executable.
4. Test the plugin:

   ```sh
   tool plugin test ./my-plugin
   ```

5. Add the remaining hooks required by the plugin.
6. Test successful and failed recorded sessions.
7. Copy the plugin into `~/.tool/plugins` or `./.tool/plugins`.
8. Run a normal `tool` workflow and confirm the installed plugin behaves as expected.

## Troubleshooting

### The plugin is not discovered

Check that:

- The plugin is directly under `~/.tool/plugins` or `./.tool/plugins`.
- Its directory contains `plugin.toml`.
- The manifest defines `name`, `version`, and `entrypoint`.
- You are running `tool` from the expected project directory.

### The wrong plugin is running

Look for another plugin with the same manifest name. A plugin under `./.tool/plugins` takes precedence over one under `~/.tool/plugins`.

Change one plugin’s `name` if both should remain independently available.

### The entrypoint does not run

Check that:

- The `entrypoint` value points to the intended file.
- The file exists inside the plugin directory.
- The file is executable.
- Its interpreter or runtime is installed.
- Running `tool plugin test <dir>` reports no manifest or startup errors.

### A hook fails intermittently

Test each relevant recorded session and avoid relying on state left by an earlier hook. In particular, `on-error` should remain useful even if `pre-run` failed before setup completed.
