# confparse v3.0

## Breaking changes

- Replace `load()` calls with `parse()`.
- Remove YAML anchors from configuration files.
- Rewrite configurations that use YAML anchors before upgrading to v3.0.

## New features

- Validate configuration data against a JSON Schema file.
- Interpolate environment variables written as `${VAR}`.

## Fixes

- Parse empty files without crashing.
- Raise an error when a configuration contains duplicate keys.
- Update configurations that relied on the last duplicate value taking precedence.

## Upgrade checklist

1. Replace every `load()` call with `parse()`.
2. Remove YAML anchors from every configuration file.
3. Add JSON Schema validation where configuration validation is required.
4. Set each referenced environment variable before parsing.
5. Remove duplicate keys from every configuration file.
