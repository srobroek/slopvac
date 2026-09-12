# Human control corpus

Pre-2022 technical prose, written before language models wrote documentation at scale. The files are not committed: some carry licences (git's `SubmittingPatches` is GPL-2.0) that do not belong in this repository's tree. `fetch_human.py` downloads them at the pinned tags; three come from installed package metadata and one from the repository's own dogfood fixture.

| File | Source |
|---|---|
| `black-readme-2021.md` | https://raw.githubusercontent.com/psf/black/21.9b0/README.md |
| `fzf-readme-2021.md` | https://raw.githubusercontent.com/junegunn/fzf/0.27.0/README.md |
| `git-contributing-2021.md` | https://raw.githubusercontent.com/git/git/v2.33.0/Documentation/SubmittingPatches |
| `redis-readme-2021.md` | https://raw.githubusercontent.com/redis/redis/6.2.0/README.md |
| `requests-readme-2020.md` | https://raw.githubusercontent.com/psf/requests/v2.25.1/README.md |
| `ripgrep-guide-2021.md` | https://raw.githubusercontent.com/BurntSushi/ripgrep/13.0.0/GUIDE.md |
| `ripgrep-readme-2021.md` | https://raw.githubusercontent.com/BurntSushi/ripgrep/13.0.0/README.md |
| `rich-readme-2020.md` | `rich` 15.0.0 wheel METADATA long description (installed package) |
| `annotated-types-readme-2022.md` | `annotated-types` 0.8.0 wheel METADATA long description |
| `markdown-it-py-readme-2020.md` | `markdown-it-py` 4.2.0 wheel METADATA long description |
| `dogfood-readme-human.md` | `.dogfood-cleanroom/README.human.md` in this repository |
