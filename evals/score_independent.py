#!/usr/bin/env python3
"""Score the independent corpus: one document per genre, no ruleset given to the writer.

WHY THIS EXISTS SEPARATELY FROM `score.py`. That script measures a delta across
three generation conditions on the same topic, so it needs a per-topic directory
and a condition axis. This one measures a single unguided document per genre and
asks a different question: does a rule fire on prose that is CORRECT for its
register? A marketing page is supposed to sell, a blog post is supposed to have a
voice, and a legal notice is supposed to be impersonal and passive. A finding
there is evidence about the rule, not about the document.

The genre profiles follow the write-docs genre table: a procedure and reference
material take `strict`, everything else takes `normal`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "independent"
LINT = HERE.parent / "packages" / "slopvac-lint"

# Genre, register, and the profile the write-docs table assigns.
DOCUMENTS = {
    "issue-comment-pgbouncer": ("issue comment", "informal", "normal"),
    "blog-skip-locked": ("blog post", "informal", "normal"),
    "spec-resumable-upload": ("specification", "formal", "strict"),
    "legal-dpa-notice": ("legal notice", "formal", "normal"),
    "marketing-feature-flags": ("landing copy", "promotional", "normal"),
    "tutorial-mtls": ("tutorial", "instructional", "strict"),
    "release-notes-4-0": ("release notes", "mixed", "normal"),
    "design-doc-outbox": ("design doc", "internal", "normal"),
}


def run_gate(path: Path, profile: str) -> dict:
    """slopvac-lint from the working tree, with every finding kept.

    `--no-vale` because the compiled Vale styles are mid-rework; the Python rules
    are the stable measurement. Findings are returned in full rather than as
    counts: the point of this corpus is reading individual hits.
    """
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
        "words": payload["summary"]["words"],
        "categories": payload["summary"].get("categories", {}),
        "hits": [
            {
                "rule": f["rule_id"],
                "line": f["line"],
                "severity": f["severity"],
                "message": f["message"],
                "match": f.get("matched_text", ""),
            }
            for f in document["findings"]
        ],
    }


def main() -> int:
    out: dict[str, dict] = {}
    for stem, (genre, register, profile) in DOCUMENTS.items():
        path = CORPUS / f"{stem}.md"
        if not path.is_file():
            print(f"missing: {path.name}", file=sys.stderr)
            continue
        entry = run_gate(path, profile)
        entry.update(genre=genre, register=register, profile=profile)
        out[stem] = entry
        if "error" in entry:
            print(f"{stem}: ERROR {entry['error']}", file=sys.stderr)
            continue
        print(
            f"{stem:32} {profile:7} {entry['words']:5}w "
            f"{entry['findings']:4} findings  {entry['per_100_words']:6.2f}/100w  "
            f"score {entry['score']}"
        )

    (CORPUS / "scores.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Per-rule totals across the corpus. A rule at the top of this list either
    # catches something every genre does, or is miscalibrated for a register the
    # rule was never tested against. Reading it is the whole point.
    tally: dict[str, int] = {}
    for entry in out.values():
        for hit in entry.get("hits", []):
            tally[hit["rule"]] = tally.get(hit["rule"], 0) + 1
    print("\nper-rule totals:")
    for rule, count in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:4}  {rule}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
