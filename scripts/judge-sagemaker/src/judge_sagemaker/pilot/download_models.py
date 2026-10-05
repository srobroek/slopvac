"""Download one arm's checkpoints at their pinned Hub revisions into HF_HOME.

    $FAMILY_PY download_models.py <arm>

Verbatim judge-pilot download_models.py. Every entry of arms.py `downloads` is a (repo, full commit
SHA) pair; a fine-tuned Kev arm downloads only its Qwen base, a fine-tuned Laya arm nothing.
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
