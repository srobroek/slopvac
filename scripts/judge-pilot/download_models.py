"""Download every pilot checkpoint at its pinned Hub revision into the Hugging Face cache.

Run with any interpreter that has huggingface_hub (the Kev venv has it):
    .cache/src/kev/.venv/bin/python download_models.py [arm ...]
Weights land in ~/.cache/huggingface (outside the repository); nothing here is committed.
"""

import sys

from huggingface_hub import snapshot_download

from arms import ARMS


def main(names):
    for name in names or ARMS:
        arm = ARMS[name]
        for repo, rev in arm["downloads"]:
            path = snapshot_download(repo, revision=rev)
            print(f"{name}: {repo}@{rev} -> {path}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
