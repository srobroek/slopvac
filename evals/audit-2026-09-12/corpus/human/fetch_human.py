#!/usr/bin/env python3
"""Fetch the human control corpus at its pinned sources.

The files are third-party prose at pinned tags and are not committed (see
SOURCES.md). Run from anywhere; writes next to this script.
"""

from __future__ import annotations

import email
import glob
import shutil
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]

URLS = {
    "ripgrep-guide-2021.md": "https://raw.githubusercontent.com/BurntSushi/ripgrep/13.0.0/GUIDE.md",
    "ripgrep-readme-2021.md": "https://raw.githubusercontent.com/BurntSushi/ripgrep/13.0.0/README.md",
    "redis-readme-2021.md": "https://raw.githubusercontent.com/redis/redis/6.2.0/README.md",
    "requests-readme-2020.md": "https://raw.githubusercontent.com/psf/requests/v2.25.1/README.md",
    "fzf-readme-2021.md": "https://raw.githubusercontent.com/junegunn/fzf/0.27.0/README.md",
    "git-contributing-2021.md": (
        "https://raw.githubusercontent.com/git/git/v2.33.0/Documentation/SubmittingPatches"
    ),
    "black-readme-2021.md": "https://raw.githubusercontent.com/psf/black/21.9b0/README.md",
}

PACKAGES = {
    "rich-readme-2020.md": "rich",
    "annotated-types-readme-2022.md": "annotated_types",
    "markdown-it-py-readme-2020.md": "markdown_it_py",
}


def fetch(url: str) -> str:
    error: Exception | None = None
    for attempt in range(5):
        try:
            return urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 -- retried, then reported
            error = exc
            time.sleep(3 + 3 * attempt)
    raise SystemExit(f"could not fetch {url}: {error}")


def main() -> int:
    for name, url in URLS.items():
        target = HERE / name
        if target.exists():
            continue
        target.write_text(fetch(url), encoding="utf-8")
        print("fetched", name)
    site = glob.glob(str(REPO / "packages/slopvac-lint/.venv/lib/python*/site-packages"))
    for name, package in PACKAGES.items():
        target = HERE / name
        if target.exists() or not site:
            continue
        metadata = glob.glob(f"{site[0]}/{package}-*.dist-info/METADATA")
        if not metadata:
            print("missing package metadata for", package, file=sys.stderr)
            continue
        body = email.message_from_string(
            Path(metadata[0]).read_text(errors="ignore")
        ).get_payload()
        target.write_text(body, encoding="utf-8")
        print("extracted", name)
    dogfood = REPO / ".dogfood-cleanroom" / "README.human.md"
    if dogfood.exists() and not (HERE / "dogfood-readme-human.md").exists():
        shutil.copy(dogfood, HERE / "dogfood-readme-human.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
