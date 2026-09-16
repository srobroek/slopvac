"""Command line entry point for judgement evaluation artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .runner import (
    HostRecord,
    ReplayProvider,
    aggregate,
    parse_provider_response,
    validate_result_set,
)


def _decode_records(rows: list[dict[str, Any]]) -> list[HostRecord]:
    return [HostRecord(**row) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m slopvac.judgement.eval")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "validate", "report"):
        command = sub.add_parser(name)
        command.add_argument("--instrument")
        command.add_argument("--arm")
        command.add_argument("--partition")
        command.add_argument("--unit")
        command.add_argument("--repeats", type=int)
        command.add_argument("--replay", type=Path)
        command.add_argument("input", nargs="?")
    args = parser.parse_args(argv)
    if args.command == "run":
        if not args.replay:
            parser.error("run requires --replay for deterministic execution")
        provider = ReplayProvider(args.replay)
        outputs = []
        for _ in range(args.repeats or 1):
            outputs.extend(row for payload in parse_provider_response(provider.request()) for row in payload["results"])
        print(json.dumps({"results": outputs}, sort_keys=True))
        return 0
    payload = json.loads(Path(args.input).read_text()) if args.input else json.load(__import__("sys").stdin)
    if args.command == "validate":
        error = validate_result_set(payload.get("units", []), payload.get("results"))
        if error:
            print(error)
            return 2
        print("valid")
        return 0
    records = payload.get("records", [])
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        parser.error("report input records must be a list of objects")
    print(json.dumps(aggregate(_decode_records(records)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
