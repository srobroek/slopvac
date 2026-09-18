from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVALUATION = ROOT / "packages/slopvac-lint/docs/research/rubric-2026-09-15/evaluation"
SCRIPT = ROOT / "packages/slopvac-lint/docs/research/rubric-2026-09-15/measurements/normalize_records.py"
TARGETS = {
    "local-corpus-run.json",
    "sibling-full-run.json",
    "sibling-full-run-adjudication.json",
    "heldout-baseline.json",
    "heldout-baseline-adjudication.json",
    "heldout-v2.json",
    "heldout-v2-adjudication.json",
}


def test_real_records_normalize_deterministically_and_declare_nulls(tmp_path: Path) -> None:
    records = tmp_path / "evaluation"
    records.mkdir()
    for name in TARGETS:
        shutil.copy2(EVALUATION / name, records / name)

    command = [sys.executable, str(SCRIPT), str(records)]
    subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
    first = {path.name: path.read_bytes() for path in records.glob("*.normalized.json")}
    subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
    second = {path.name: path.read_bytes() for path in records.glob("*.normalized.json")}

    assert first == second
    assert set(first) == {name.removesuffix(".json") + ".normalized.json" for name in TARGETS}
    required = {"schema_version", "raw_outcomes", "raw_adjudication", "metrics", "denominators", "per_rule", "not_derivable"}
    for path in sorted(records.glob("*.normalized.json")):
        normalized = json.loads(path.read_text(encoding="utf-8"))
        assert required <= normalized.keys()
        for metric, value in normalized["metrics"].items():
            if value is None:
                assert any(entry.startswith(f"metrics.{metric}") for entry in normalized["not_derivable"])
