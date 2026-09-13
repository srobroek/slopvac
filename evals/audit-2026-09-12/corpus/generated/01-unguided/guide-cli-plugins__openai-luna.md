# Writing a Plugin for the `tool` CLI

Plugins extend the `tool` CLI with custom behavior that runs before or after a command, or when a command fails.

A plugin is a directory containing a `plugin.toml` manifest and an entrypoint. Plugins are discovered from:

- `~/.tool/plugins` — user-wide plugins
- `./.tool/plugins` — plugins in the current project

When both locations contain a plugin with the same name, the project plugin takes precedence.

This guide walks through creating, structuring, and testing your first plugin.

## Plugin structure

A minimal plugin looks like this:

```text
my-plugin/
├── plugin.toml
└── plugin
```

The `plugin.toml` file describes the plugin:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "./plugin"
```

The manifest must define:

| Field | Description |
|---|---|
| `name` | The plugin's unique name |
| `version` | The plugin version |
| `entrypoint` | The program that `tool` runs for the plugin |

The entrypoint should be executable:

```sh
chmod +x plugin
```

## Choose where to install the plugin

### Install a user-wide plugin

Place the plugin under:

```text
~/.tool/plugins/
```

For example:

```text
~/.tool/plugins/my-plugin/
├── plugin.toml
└── plugin
```

A user-wide plugin is available from projects that use the same user account.

### Install a project plugin

Place the plugin under the project's root directory:

```text
./.tool/plugins/
```

For example:

```text
my-project/
└── .tool/
    └── plugins/
        └── my-plugin/
            ├── plugin.toml
            └── plugin
```

Project plugins are useful when the plugin is specific to one repository or needs to be versioned with the project.

### Understand name precedence

Plugin names identify plugins. If a user-wide plugin and a project plugin have the same `name`, the project plugin wins:

```text
~/.tool/plugins/my-plugin/       # ignored for this project
./.tool/plugins/my-plugin/       # selected
```

Use distinct names when you want both plugins to be available without one replacing the other.

## Define the manifest

Create `plugin.toml` in the plugin directory:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "./plugin"
```

The `entrypoint` path is relative to the plugin directory. Keeping the entrypoint inside the plugin directory makes the plugin self-contained and easier to move or commit.

## Implement plugin hooks

A plugin can implement three hooks:

- `pre-run`
- `post-run`
- `on-error`

The hooks represent stages in a command's lifecycle.

### `pre-run`

The `pre-run` hook runs before the requested `tool` command executes.

Typical uses include:

- Validating local configuration
- Checking that required files exist
- Preparing temporary resources
- Printing context before a command starts

Use this hook for checks or setup that should happen before the command.

### `post-run`

The `post-run` hook runs after a command completes successfully.

Typical uses include:

- Recording results
- Cleaning up temporary resources
- Updating generated metadata
- Sending a notification

Use this hook for work that should happen only after a successful run.

### `on-error`

The `on-error` hook runs when a command fails.

Typical uses include:

- Capturing diagnostic information
- Collecting logs
- Sending failure notifications
- Printing troubleshooting guidance

Use this hook for failure-specific behavior. Keep error handling itself reliable: a diagnostic plugin should not hide or replace the original command failure.

## Route hooks from the entrypoint

The `entrypoint` is the program that implements the plugin. It must distinguish which hook is being requested and run the appropriate logic.

The exact hook input and output contract is defined by the `tool` CLI. Structure your entrypoint around that contract rather than assuming that every hook receives the same data.

Conceptually, an entrypoint might dispatch like this:

```text
when the CLI requests "pre-run":
    validate the environment

when the CLI requests "post-run":
    record the successful run

when the CLI requests "on-error":
    collect diagnostics
```

Keep hook-specific logic separate in your implementation. This makes the plugin easier to test and prevents behavior for one lifecycle stage from affecting another.

A typical implementation layout is:

```text
my-plugin/
├── plugin.toml
├── plugin
├── pre_run
├── post_run
└── on_error
```

The `plugin` entrypoint can dispatch to the helper for the requested hook.

## Example plugin design

Suppose you want a plugin that checks for a required project file before a command runs and reports a helpful message when a command fails.

Its directory could be:

```text
project-check/
├── plugin.toml
└── plugin
```

Its manifest:

```toml
name = "project-check"
version = "0.1.0"
entrypoint = "./plugin"
```

The plugin's behavior:

```text
pre-run:
    check that the project's configuration file exists
    stop or report the problem according to the CLI hook contract

post-run:
    do nothing

on-error:
    print the location of the configuration file and relevant diagnostics
```

Start with one hook whenever possible. Once that hook works, add the others incrementally.

## Make the entrypoint dependable

A plugin runs as part of another command, so small reliability issues can make the entire workflow confusing.

Follow these practices:

1. **Use a stable entrypoint path.**  
   Reference the entrypoint from `plugin.toml` with a relative path.

2. **Make the entrypoint executable.**

   ```sh
   chmod +x plugin
   ```

3. **Keep startup fast.**  
   Hooks may run for many commands. Avoid unnecessary network calls or expensive setup.

4. **Write useful diagnostics.**  
   Explain what failed and how the user can fix it.

5. **Preserve the original command result.**  
   Especially in `on-error`, do not obscure the command's original failure.

6. **Handle missing context gracefully.**  
   A hook may not have all the information you expect. Fail with a clear message rather than an obscure stack trace.

7. **Keep side effects deliberate.**  
   A `pre-run` hook should not unexpectedly modify project files, and an error hook should not perform destructive cleanup without a clear reason.

## Test a plugin

Use `tool plugin test` to run a plugin against a recorded session:

```sh
tool plugin test <dir>
```

For example:

```sh
tool plugin test ./project-check
```

The recorded session gives the plugin a repeatable scenario without requiring you to run the real command every time.

Before testing, verify the plugin directory contains the manifest and entrypoint:

```text
project-check/
├── plugin.toml
└── plugin
```

Then run:

```sh
tool plugin test ./project-check
```

Use the test command while developing to check:

- The manifest is valid
- The entrypoint can be found
- The entrypoint is executable
- Each implemented hook is dispatched correctly
- Successful runs invoke `post-run`
- Failed runs invoke `on-error`
- Diagnostics are understandable

## Test each lifecycle path

A plugin with multiple hooks should be tested against each relevant outcome.

### Successful run

Confirm that:

1. `pre-run` executes before the command.
2. The command completes.
3. `post-run` executes after a successful command.
4. `on-error` does not run.

### Failed run

Confirm that:

1. `pre-run` executes before the command.
2. The command fails.
3. `on-error` executes.
4. `post-run` does not run for the failed command, unless the CLI's hook contract explicitly specifies otherwise.
5. The original failure remains visible.

### Pre-run failure

If your plugin can reject a run during `pre-run`, verify what the CLI does with that result and ensure the user receives a clear explanation.

## Troubleshoot discovery

If `tool` does not find your plugin, check the following:

### Confirm the directory location

For a user-wide plugin:

```text
~/.tool/plugins/<plugin-name>/
```

For a project plugin:

```text
./.tool/plugins/<plugin-name>/
```

The project location is relative to the current project directory.

### Confirm the manifest name

The `name` in `plugin.toml` should match the plugin you intend to use:

```toml
name = "my-plugin"
```

If a project plugin and a user-wide plugin share this name, the project plugin is selected.

### Confirm the manifest fields

Ensure that all required fields are present:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "./plugin"
```

### Confirm the entrypoint

Check that the path is correct and that the file is executable:

```sh
ls -l plugin
chmod +x plugin
```

### Test the directory directly

Run:

```sh
tool plugin test ./my-plugin
```

Testing the directory directly helps separate plugin implementation problems from discovery problems.

## Recommended development workflow

Use this workflow for a first plugin:

1. Create a directory under `./.tool/plugins` or `~/.tool/plugins`.
2. Add `plugin.toml`.
3. Add a small executable entrypoint.
4. Implement one hook, usually `pre-run`.
5. Run `tool plugin test <dir>`.
6. Fix manifest, permission, and dispatch errors.
7. Add `post-run` or `on-error` if needed.
8. Test both successful and failed sessions.
9. Move the plugin to `~/.tool/plugins` only when it is ready to use across projects.

A complete starter layout is:

```text
my-plugin/
├── plugin.toml
└── plugin
```

With:

```toml
name = "my-plugin"
version = "0.1.0"
entrypoint = "./plugin"
```

Then test it with:

```sh
tool plugin test ./my-plugin
```

Start small, keep each hook focused, and use recorded-session tests to verify the plugin's behavior before relying on it in normal command runs.
