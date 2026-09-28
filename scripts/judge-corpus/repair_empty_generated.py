"""Repair generated texts that were overwritten with empty strings.

collect_all uploaded parse_output(line) for every raw line whose recordId was
accepted, including stale error lines from a failed first batch run for the same
recordId. Where an error line came last, the stored text became empty. This
re-writes each empty text from the record's successful output line.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
from judge_corpus.batch import parse_output  # noqa: E402
from judge_corpus.bedrock import upload_text  # noqa: E402

root = Path(".").resolve()
manifest = {}
for line in open("generated/manifest.jsonl"):
    row = json.loads(line)
    manifest[row.get("record_id", row["id"])] = row

fixed = 0
for raw in sorted(Path("generated/raw").glob("*.jsonl")):
    for line in open(raw):
        rec = json.loads(line)
        if "modelOutput" not in rec:
            continue
        row = manifest.get(rec.get("recordId"))
        if not row:
            continue
        local = root / ".cache" / row["s3_key"]
        if local.exists() and local.stat().st_size > 0:
            continue
        text = parse_output(rec)
        if not text:
            continue
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
        upload_text(root, text, row["s3_key"])
        fixed += 1
empty = sum(
    1 for r in manifest.values() if (root / ".cache" / r["s3_key"]).stat().st_size == 0
)
print("repaired", fixed, "still empty", empty)
