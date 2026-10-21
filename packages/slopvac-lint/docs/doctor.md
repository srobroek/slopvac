<!-- slopvac-disable -->
# `slopvac doctor`
<!-- slopvac-enable -->

Run `slopvac doctor --format json` to print local config and system data. JSON prints to stdout on failure. Exit 0 means that slopvac loads config and finds supported Vale. Exit 2 indicates a config error or an unsupported Vale. Text output is the default.

The command reads only the release cache. A missing or unreadable cache gives `latest_release: null`. The command replaces every absolute home path with `~`. This includes paths reached through a symlink and paths in errors. The command prints path fields inside the current directory as relative paths. The steering skill state is `disabled` when both `write` and `review` guidance are off. When config loading fails, the command still wants the skill.

## Schema version 1

Each entry names a field, its type, and what it means. `null` means that the field has no value in this report.

<!-- slopvac-disable-next-line -->
```yaml
schema_version: integer - Version of the report schema.
ok: boolean - True only when the config loads and Vale meets its minimum version.
slopvac: object - Package and Python installation data.
slopvac.version: string - Installed slopvac version.
slopvac.location: string - Installed package directory.
slopvac.python_prefix: string - Prefix of the Python running slopvac.
slopvac.upgrade_command: string - Upgrade command for this Python.
latest_release: object or null - Release data from the cache, or null when no valid cache exists.
latest_release.version: string - Cached stable release version.
latest_release.checked_at: string - Cached ISO 8601 check time, including its timezone.
latest_release.newer: boolean - True when `is_newer_release` says the cached version is newer.
python: object - Python runtime data.
python.version: string - Python version.
python.implementation: string - Python implementation name.
platform: object - Host operating system data.
platform.system: string - Operating-system name.
platform.release: string - Operating-system release.
platform.machine: string - Machine architecture.
vale: object - Selected Vale binary and its support status.
vale.binary: string - Requested Vale name or path. Home paths use `~`.
vale.path: string or null - Resolved executable path, or null when no executable was found.
vale.version: string or null - Version reported by the executable, including when it is too old.
vale.minimum: string - Minimum version from `MIN_VALE_VERSION`.
vale.supported: boolean - True when Vale meets the minimum version.
vale.error: string or null - Vale prerequisite error, or null when supported.
config: object - Config path, load error, and loaded settings.
config.path: string or null - Path relative to cwd when inside it; otherwise home-relative or absolute. Null when no config is found.
config.error: string or null - Config loading error. When set, profile, mode, and guidance are null.
config.profile: string or null - Configured profile, or null when config loading fails.
config.mode: string or null - Configured mode, or null when config loading fails.
config.guidance: object or null - Full `GuidanceSettings.model_dump()` result, or null when config loading fails.
steering: array - One state entry for every supported harness. The root is the config directory or cwd.
steering[].harness: string - Harness identifier.
steering[].path: string - Steering file path relative to the project root.
steering[].block: string - Managed-block state: `missing`, `current`, `stale`, or `malformed`.
steering[].skill: string or null - Skill state from `skill_state`, or null when the harness has no skill directory.
steering[].error: string - Per-harness inspection error. Error entries omit path, block, and skill.
cache: object - slopvac cache data.
cache.root: string - Cache directory path.
```
<!-- slopvac-enable -->
