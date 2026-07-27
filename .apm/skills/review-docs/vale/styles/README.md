# Vale styles

This directory is a sync target. Every style in it is fetched by `vale sync` from
the `Packages` URLs in `../.vale.ini`, and none of it is committed.

```sh
vale --config=../.vale.ini sync
```

`scripts/slop-lint.sh` exits 2 with this command when the directory is empty, so
a missing sync stops the run instead of linting against half a config.

## What gets fetched

| Style | Source | Licence |
|---|---|---|
| `ai-residue`, `prose-agency`, `prose-inflation`, `docs-discipline`, `prose-format` | `vale-styles/` in this repo, published as release assets | Apache-2.0 |
| `ai-tells` | [tbhb/vale-ai-tells](https://github.com/tbhb/vale-ai-tells) | MIT, (c) the vale-ai-tells authors |

The ai-tells release zip ships no LICENSE file, so its attribution lives here.

## Editing rules

Do not edit anything a sync writes here; a sync overwrites each style directory
wholesale. Rule levels and disables belong in `../.vale.ini`, which survives a
sync. Four ai-tells rules are disabled and four demoted there, each with the
measured reason -- read those comments before re-enabling anything.

Our own rules are authored in `vale-styles/` at the repo root, one directory per
published package. Change a rule there, run `vale-styles/build.sh` to rebuild the
zips, and re-run the corpus calibration.

## Upstream version

Every `Packages` URL uses GitHub's `releases/latest/download/` redirect, so a
sync takes the newest release of each style. When an ai-tells sync changes
behavior, re-run the corpus calibration (`apm run slop-lint`) and re-check the
disable list in `../.vale.ini` against the new rule set.
