"""Serve one Laya checkpoint through Laya's own Jev-compatible app (laya.serve.create_app).

    .cache/laya-venv/bin/python laya_server.py <arm> <port>

The Router holds exactly the arm's checkpoint at its pinned revision (or the local fine-tuned
directory) and routes every request to it. LAYA_DEVICE selects the torch device (default: auto).
"""

import os
import sys

import uvicorn
from laya.router import Router
from laya.serve import create_app

from arms import ARMS


def main():
    name, port = sys.argv[1], int(sys.argv[2])
    arm = ARMS[name]
    ck = arm["checkpoint"]
    spec = arm["local"] or arm["repo"]
    router = Router(
        models={ck: spec},
        standalone_repos=True,
        revisions={ck: None if arm["local"] else arm["revision"]},
        max_loaded=1,
        default=ck,
        device=os.environ.get("LAYA_DEVICE") or None,
    )
    router.preload([ck])
    uvicorn.run(create_app(router), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
