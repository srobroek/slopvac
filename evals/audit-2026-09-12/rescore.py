#!/usr/bin/env python3
"""Rescore the audit corpora with two checkouts of the lint package.

Writes `runs/<tag>__<corpus>__normal.json` (the full finding dumps, not committed) and
`runs/summary_old_new.json` plus `runs/per_rule_old_new.json` (committed). The report
reads only the summaries, so re-running this is how a number in it is checked.

    uv run python rescore.py --baseline /tmp/slopvac-baseline/packages/slopvac-lint \\
        --new ../../packages/slopvac-lint

The baseline is a checkout of `packages/slopvac-lint` at the commit the audit started
from; `git archive origin/main packages/slopvac-lint | tar -x -C /tmp/slopvac-baseline`
produces one. Both checkouts must have been synced (`uv sync`) so `uv run` resolves.
The human corpus must be fetched first (`corpus/human/fetch_human.py`).
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPORA = {
    "human": HERE / "corpus/human",
    "slopvacced": HERE / "corpus/slopvacced",
    "ai-existing": HERE / "corpus/ai-existing",
    "gen-unguided": HERE / "corpus/generated/01-unguided",
    "gen-steered-current": HERE / "corpus/generated/02-steered-current",
    "gen-steered-new": HERE / "corpus/generated/03-steered-new",
}
PER_RULE_CORPORA = ("human", "slopvacced", "ai-existing", "gen-unguided")


def lint(project: Path, files: list[Path]) -> dict:
    command = [
        "uv", "run", "slopvac", "lint", *map(str, files),
        "--profile", "normal", "--format", "json", "--config", "/dev/null",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, cwd=project)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{project}: {completed.stderr[-1000:]}") from exc


def passed(run: dict) -> int:
    return sum(1 for document in run["documents"] if document["passed"])


def per_rule(run: dict) -> tuple[collections.Counter, dict[str, str]]:
    counts: collections.Counter = collections.Counter()
    severity: dict[str, str] = {}
    for document in run["documents"]:
        for finding in document["findings"]:
            counts[finding["rule_id"]] += 1
            severity[finding["rule_id"]] = finding["severity"]
    return counts, severity


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    args = parser.parse_args()
    runs_dir = HERE / "runs"
    runs_dir.mkdir(exist_ok=True)

    runs: dict[tuple[str, str], dict] = {}
    for tag, project in (("baseline", args.baseline), ("new", args.new)):
        for corpus, folder in CORPORA.items():
            files = sorted(p for p in folder.glob("*.md") if p.name != "SOURCES.md")
            if not files:
                continue
            run = lint(project.resolve(), files)
            runs[(tag, corpus)] = run
            (runs_dir / f"{tag}__{corpus}__normal.json").write_text(json.dumps(run))

    summary = []
    for corpus in CORPORA:
        if ("new", corpus) not in runs:
            continue
        base, new = runs[("baseline", corpus)]["summary"], runs[("new", corpus)]["summary"]
        summary.append(
            {
                "corpus": corpus,
                "docs": new["documents"],
                "words": new["words"],
                **{f"b_{k}": base[v] for k, v in (("err", "errors"), ("warn", "warnings"), ("sugg", "suggestions"), ("density", "per_100_words"), ("score", "score"))},
                **{f"n_{k}": new[v] for k, v in (("err", "errors"), ("warn", "warnings"), ("sugg", "suggestions"), ("density", "per_100_words"), ("score", "score"))},
                "b_pass": passed(runs[("baseline", corpus)]),
                "n_pass": passed(runs[("new", corpus)]),
            }
        )
    (runs_dir / "summary_old_new.json").write_text(json.dumps(summary, indent=1))

    tables = {(tag, corpus): per_rule(runs[(tag, corpus)]) for tag in ("baseline", "new") for corpus in PER_RULE_CORPORA}
    rules = set()
    for counts, _ in tables.values():
        rules |= set(counts)
    rows = []
    for rule in sorted(rules):
        row = {"rule": rule}
        for corpus in PER_RULE_CORPORA:
            base_counts, base_severity = tables[("baseline", corpus)]
            new_counts, new_severity = tables[("new", corpus)]
            row[corpus] = (
                base_counts[rule], new_counts[rule], base_severity.get(rule, ""), new_severity.get(rule, "")
            )
        rows.append(row)
    (runs_dir / "per_rule_old_new.json").write_text(json.dumps(rows, indent=1))
    for entry in summary:
        print(
            f"{entry['corpus']:20} err {entry['b_err']:4}->{entry['n_err']:4} "
            f"score {entry['b_score']:5.1f}->{entry['n_score']:5.1f} "
            f"pass {entry['b_pass']:2}->{entry['n_pass']:2}/{entry['docs']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
