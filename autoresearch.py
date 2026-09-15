#!/usr/bin/env python3
"""Dispatch the offline benchmark by default and the retained online one explicitly."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--online":
        from bench.runner import main as online_main

        return online_main(args[1:])

    from deterministic_runner import main as offline_main

    return offline_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
