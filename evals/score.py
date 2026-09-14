#!/usr/bin/env python3
"""Score every eval document with both gates and write the comparison.

Two gates, because the question is whether the new ruleset is better than the old
one and not merely whether it fires:

  OLD  Vale with the seven styles this repo published before the split, which is
       what `slop-lint.sh` ran. Reported as a finding count only: it had no score.
  NEW  slopvac, which reports a density and a 0-100 score per category.

Usage:
    ./score.py                      score every run under runs/
    ./score.py --topic readme-cache score one topic
    ./score.py --report             print the stored scores as a markdown table

Every number in REPORT.md comes from a scores.json written here, so the report
cannot drift from the measurement. The raw counts are published beside the
densities: a density alone hides that a 40-word document earned its one finding.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
LINT = ROOT.parent / "packages" / "slopvac-lint"

# The four generation conditions, in the order they are reported.
CONDITIONS = ("01-unguided", "02-current-writedocs", "03-new-writedocs", "04-regenerated")

# Profile per topic. A runbook and reference documentation earn `strict`; an error
# message is short-form product copy and takes `normal`.
PROFILES = {
    "readme-cache": "normal",
    "readme-parser": "normal",
    "api-docs-webhook": "strict",
    "runbook-failover": "strict",
    "pr-description": "normal",
    "adr-queue": "normal",
    "error-message": "normal",
    "guide-migration": "normal",
}

# The styles the old gate ran. Kept as a list so the old measurement stays
# reproducible after the styles are no longer wired into anything.
OLD_STYLES = (
    "ai-residue", "prose-agency", "prose-inflation", "prose-scope",
    "docs-discipline", "prose-format", "ai-tells",
)


def words(text: str) -> int:
    """Word count for reporting only. Deliberately a plain split: the report has
    to be checkable by hand, and slopvac's own STE-compliant count is
    reported separately in its JSON."""
    return len(text.split())


def run_new_gate(path: Path, profile: str) -> dict:
    """slopvac, from the working tree rather than PyPI."""
    # The venv's own interpreter, so the installed package and its dependencies
    # resolve without a PYTHONPATH or a stripped environment.
    python = LINT / ".venv" / "bin" / "python"
    result = subprocess.run(
        [
            str(python if python.is_file() else sys.executable),
            "-m", "slopvac.cli", "lint", str(path),
            "--profile", profile, "--no-vale", "--format", "json",
        ],
        capture_output=True, text=True, cwd=LINT, check=False,
    )
    if result.returncode >= 2:
        return {"error": result.stderr.strip() or result.stdout.strip()}
    payload = json.loads(result.stdout)
    document = payload["documents"][0]
    return {
        "score": payload["summary"]["score"],
        "findings": payload["summary"]["findings"],
        "errors": payload["summary"]["errors"],
        "warnings": payload["summary"]["warnings"],
        "suggestions": payload["summary"]["suggestions"],
        "per_100_words": payload["summary"]["per_100_words"],
        "words": document["words"],
        "passed": payload["summary"]["passed"],
        "failure_reasons": document["failure_reasons"],
        "categories": {
            entry["category"]: {
                "findings": entry["findings"],
                "errors": entry["errors"],
                "score": entry["score"],
            }
            for entry in document["categories"]
            if entry["findings"]
        },
        "rules": _rule_histogram(document["findings"]),
    }


def _rule_histogram(findings: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["rule_id"]] = counts.get(finding["rule_id"], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def run_old_gate(path: Path, config: Path) -> dict:
    """Vale with the pre-split style set.

    Returns `unavailable` rather than zero when vale is absent or the styles are
    unsynced: an unsynced style makes Vale report every file clean, and recording
    that as a passing score would invent a result.
    """
    if shutil.which("vale") is None:
        return {"unavailable": "vale is not on PATH"}
    styles_dir = config.parent / "styles"
    missing = [s for s in OLD_STYLES if not (styles_dir / s).is_dir()]
    if missing:
        return {"unavailable": f"styles not synced: {' '.join(missing)}"}

    result = subprocess.run(
        ["vale", f"--config={config}", "--output=JSON", "--no-exit", str(path)],
        capture_output=True, text=True, check=False,
    )
    # `--no-exit` makes findings exit 0, so a non-zero status is Vale itself
    # failing. Empty or unparsable output is the same failure: neither is a clean
    # file, and recording zero findings would invent a result.
    if result.returncode != 0:
        return {"error": result.stderr.strip() or f"vale exited {result.returncode}"}
    raw = result.stdout.strip()
    try:
        data = json.loads(raw) if raw else None
    except json.JSONDecodeError as exc:
        return {"error": f"vale output is not JSON: {exc}"}
    if not isinstance(data, dict):
        return {"error": "vale produced no JSON report"}
    alerts = [a for entries in data.values() for a in entries]
    counts: dict[str, int] = {}
    for alert in alerts:
        check = alert.get("Check", "?")
        counts[check] = counts.get(check, 0) + 1
    return {
        "findings": len(alerts),
        "errors": sum(1 for a in alerts if a.get("Severity") == "error"),
        "warnings": sum(1 for a in alerts if a.get("Severity") == "warning"),
        "rules": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def score_topic(topic: str, old_config: Path | None) -> dict:
    directory = RUNS / topic
    profile = PROFILES.get(topic, "normal")
    result = {"topic": topic, "profile": profile, "conditions": {}}

    for condition in CONDITIONS:
        path = directory / f"{condition}.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        entry = {
            "raw_words": words(text),
            "new": run_new_gate(path, profile),
        }
        if old_config is not None:
            entry["old"] = run_old_gate(path, old_config)
        result["conditions"][condition] = entry

    (directory / "scores.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def diff_conditions(topic: str) -> None:
    """Write a patch between each adjacent pair, so a reader can see what the
    rules actually changed rather than trusting the numbers."""
    directory = RUNS / topic
    out = directory / "diffs"
    out.mkdir(exist_ok=True)
    pairs = [
        ("01-unguided", "02-current-writedocs"),
        ("02-current-writedocs", "03-new-writedocs"),
        ("03-new-writedocs", "04-regenerated"),
        ("01-unguided", "04-regenerated"),
    ]
    for left, right in pairs:
        a, b = directory / f"{left}.md", directory / f"{right}.md"
        if not (a.is_file() and b.is_file()):
            continue
        patch = subprocess.run(
            ["diff", "-u", "--label", left, "--label", right, str(a), str(b)],
            capture_output=True, text=True, check=False,
        )
        (out / f"{left}__{right}.patch").write_text(patch.stdout, encoding="utf-8")


def render_report(results: list[dict]) -> str:
    """A markdown table of the stored scores, one row per topic and condition."""
    lines = ["| topic | condition | old findings | new score | new findings |", "| --- | --- | --- | --- | --- |"]
    for topic in results:
        for condition in CONDITIONS:
            entry = topic.get("conditions", {}).get(condition)
            if entry is None:
                continue
            old = entry.get("old", {})
            new = entry.get("new", {})
            old_cell = old.get("unavailable") or old.get("error") or old.get("findings", "")
            new_cell = new.get("error") or new.get("score", "")
            lines.append(
                f"| {topic.get('topic', '')} | {condition} | {old_cell} | {new_cell} | "
                f"{new.get('findings', '') if 'error' not in new else ''} |"
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic")
    parser.add_argument(
        "--old-config",
        type=Path,
        help="A .vale.ini carrying the seven pre-split styles, for the old gate.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print the stored scores.json as a markdown table instead of re-scoring.",
    )
    args = parser.parse_args()

    if args.report:
        print(render_report(json.loads((ROOT / "scores.json").read_text(encoding="utf-8"))))
        return 0

    topics = [args.topic] if args.topic else sorted(
        p.name for p in RUNS.iterdir() if p.is_dir()
    )
    results = []
    for topic in topics:
        results.append(score_topic(topic, args.old_config))
        diff_conditions(topic)
        print(f"scored {topic}")

    (ROOT / "scores.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
