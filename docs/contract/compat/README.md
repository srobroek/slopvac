# 2.x compatibility matrix

`matrix.md` and `matrix.json` list every 2.x command, option, Action input and output, pre-commit hook ID, and hand-listed behaviour. Each row has a disposition, a 3.0 note, and an owning bead.

The generator reads the click tree (`slopvac.cli:main`), `action.yml`, and `.pre-commit-hooks.yaml`. It merges `dispositions.toml`, which is the only file to edit by hand. Behaviour rows exist only in that file, under `behavior:` keys.

Row IDs use these prefixes: `cmd:`, `opt:<command>:<flag>`, `action:input:`, `action:output:`, `hook:`, and `behavior:`.

Regenerate after changing the CLI, the Action, the hooks, or the dispositions:

```sh
uv run python scripts/contract/compat_matrix.py
```

`--check` exits 1 when the committed files are stale. `tests/contract/test_compat_matrix.py` makes the same comparison. It also fails on rows without a disposition or owner, and on keys with no matching source row. Rows owned by `TBD` must appear in the test's allow list, which can only shrink.

Dispositions are `preserve`, `migrate`, and `remove-with-deprecation`. The `test` column reads `pending` for preserve rows. Installed-binary tests against the 3.0 binary replace it later.
