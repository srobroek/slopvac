# Writing a Plugin for the `tool` CLI

A `tool` plugin is a directory containing a `plugin.toml` manifest and an entrypoint program. Plugins can run before a command, after a successful command, or when a command fails.

## Create the plugin directory

Create a directory for your plugin:

```text
my-plugin/
├── plugin.toml
└── my-plugin
```

The entrypoint can be a script or program appropriate for your environment.

## Add the manifest

Every plugin requires a `plugin.toml` file with three fields:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "my-plugin"
```

| Field | Description |
|---|---|
| `name` | The plugin's unique name. |
| `version` | The plugin version. |
| `entrypoint` | The plugin's entrypoint program within the plugin directory. |

Keep the entrypoint inside the plugin directory so the plugin remains portable. If it is a script, include the appropriate interpreter declaration and make it runnable:

```sh
chmod +x my-plugin/my-plugin
```

## Implement hooks

A plugin can implement any combination of these hooks:

| Hook | When it runs | Typical uses |
|---|---|---|
| `pre-run` | Before a command runs | Validation, setup, logging, or policy checks |
| `post-run` | After a command completes successfully | Reporting, cleanup, or notifications |
| `on-error` | When a command fails | Diagnostics, failure logging, or alerts |

You do not need to implement all three hooks. Start with the hook required by your use case, then add others as needed.

Keep each hook focused:

- Avoid expensive work in `pre-run`, because it delays the command.
- Use `post-run` only for behavior that depends on successful completion.
- Make `on-error` preserve the original failure information.
- Write diagnostics to help users identify which plugin produced them.

## Test the plugin

Run the plugin against a recorded session before installing it:

```sh
tool plugin test ./my-plugin
```

The argument is the directory containing `plugin.toml`, not the manifest file itself.

Testing exercises the plugin using recorded command activity, allowing you to check its hooks without installing it in a discovery directory. Repeat the test after changing the manifest, entrypoint, or hook behavior.

## Install the plugin

`tool` discovers plugins from two locations:

- User plugins: `~/.tool/plugins`
- Project plugins: `./.tool/plugins`

### Install for your user account

Use the user directory when the plugin should be available across projects:

```sh
mkdir -p ~/.tool/plugins
cp -R ./my-plugin ~/.tool/plugins/
```

The resulting layout is:

```text
~/.tool/plugins/
└── my-plugin/
    ├── plugin.toml
    └── my-plugin
```

### Install for one project

Use the project directory when the plugin belongs to a particular repository:

```sh
mkdir -p ./.tool/plugins
cp -R ./my-plugin ./.tool/plugins/
```

The resulting layout is:

```text
.tool/plugins/
└── my-plugin/
    ├── plugin.toml
    └── my-plugin
```

Consider committing a project plugin when every contributor should use the same behavior. Do not commit secrets, credentials, or machine-specific configuration with it.

## Understand name clashes

Plugins are matched by the `name` in `plugin.toml`.

If a user plugin and a project plugin have the same name, the project plugin wins. For example:

```text
~/.tool/plugins/my-plugin/plugin.toml
./.tool/plugins/my-plugin/plugin.toml
```

If both manifests contain:

```toml
name = "my-plugin"
```

`tool` uses the plugin from `./.tool/plugins`.

This precedence lets a project replace or pin behavior without modifying the user's global installation. Use distinct names when two plugins should coexist.

## Troubleshooting

### The plugin is not discovered

Check that:

1. The plugin is directly inside `~/.tool/plugins` or `./.tool/plugins`.
2. The manifest is named exactly `plugin.toml`.
3. The manifest contains `name`, `version`, and `entrypoint`.
4. The entrypoint named by the manifest exists in the plugin directory.
5. The entrypoint can run on the current platform.

Test the directory directly to separate discovery problems from plugin problems:

```sh
tool plugin test /path/to/my-plugin
```

### The wrong plugin runs

Look for another plugin with the same manifest `name` in both discovery locations. A project plugin overrides a user plugin with the same name.

### A hook does not run

Confirm that the plugin implements the hook matching the command outcome:

- Use `pre-run` for work before execution.
- Use `post-run` for successful execution.
- Use `on-error` for failed execution.

Then run `tool plugin test <dir>` again and inspect the plugin's diagnostics.

## Release checklist

Before sharing a plugin:

- [ ] `plugin.toml` contains `name`, `version`, and `entrypoint`.
- [ ] The entrypoint is present and runnable.
- [ ] Only the required hooks are implemented.
- [ ] Failure diagnostics identify the plugin and hook.
- [ ] No credentials or local-only configuration are included.
- [ ] `tool plugin test <dir>` completes with the expected behavior.
- [ ] The manifest version has been updated for the release.
