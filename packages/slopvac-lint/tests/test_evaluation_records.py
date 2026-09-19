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

    command = [sys.executable, str(SCRIPT), "--allow-partial", str(records)]
    subprocess.run([sys.executable, str(SCRIPT), "--allow-partial", str(records)], check=True, cwd=ROOT)
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


def test_normalized_measurements_use_authoritative_counters(tmp_path: Path) -> None:
    records = tmp_path / "evaluation"
    records.mkdir()
    for name in TARGETS:
        shutil.copy2(EVALUATION / name, records / name)
    subprocess.run([sys.executable, str(SCRIPT), "--allow-partial", str(records)], check=True, cwd=ROOT)

    def load(name: str) -> dict:
        return json.loads((records / f"{name}.normalized.json").read_text(encoding="utf-8"))

    local = load("local-corpus-run")
    assert local["denominators"]["precision"]["value"] == 37
    assert local["metrics"]["strict_precision"] == 9 / 37
    assert local["metrics"]["lenient_precision"] == 17 / 37

    sibling = load("sibling-full-run")
    assert sibling["denominators"]["precision"]["value"] == 95
    assert sibling["metrics"]["strict_precision"] == 5 / 95
    assert sibling["metrics"]["lenient_precision"] == 13 / 95
    assert sibling["denominators"]["evidence_validity"]["value"] == 1969
    assert sibling["metrics"]["evidence_validity"] == 95 / 1969

    for name in ("heldout-baseline", "heldout-v2"):
        heldout = load(name)
        assert heldout["metrics"]["evidence_validity"] is None
        assert "metrics.evidence_validity" in heldout["not_derivable"]


def test_incomplete_record_fails_default_validation(tmp_path: Path) -> None:
    record = tmp_path / "incomplete.json"
    record.write_text(json.dumps({"precision_strict": 0.5}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(record)],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "metrics.lenient_precision" in result.stderr
