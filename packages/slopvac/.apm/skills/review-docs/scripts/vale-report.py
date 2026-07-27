#!/usr/bin/env python3
"""Map Vale's JSON report onto slop-lint's exit contract. stdlib only.

Reads a Vale `--output=JSON` document on stdin.
Exit: 0 clean or warnings only · 1 any error · 2 unparseable input.

Vale exits non-zero for any alert at or above MinAlertLevel, which would fail a
run that only produced warnings. The retired slop-lint.py kept warnings at 0, and
callers depend on that, so severity mapping lives here rather than in Vale.

Optional `shadow=source` argv pairs rewrite a reported path back to the file the
prose came from. JSX text nodes are linted through a shadow .txt (see
extract-prose.sh), and a finding must name the .tsx a reader can open.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    shadows = dict(
        arg.split("=", 1) for arg in sys.argv[1:] if "=" in arg
    )

    raw = sys.stdin.read().strip()
    if not raw:
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print("slop-lint: could not parse vale output", file=sys.stderr)
        return 2

    errors = 0
    for path, alerts in sorted(data.items()):
        path = shadows.get(path, path)
        for alert in sorted(alerts, key=lambda a: (a.get("Line", 0), a.get("Check", ""))):
            severity = alert.get("Severity", "error")
            if severity == "error":
                errors += 1
            label = "ERROR" if severity == "error" else severity.upper()
            check = alert.get("Check", "?")
            line = alert.get("Line", "?")
            message = alert.get("Message", "").strip()
            print(f"{path} {label} {check} line {line}: {message}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
