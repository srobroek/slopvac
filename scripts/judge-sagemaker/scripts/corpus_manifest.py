"""Build the compact manifest required by the pilot harness from corpus JSONL splits."""

import hashlib
import json
import sys
from pathlib import Path


def manifest_for(root: Path) -> dict:
    files = {}
    for split in ("train", "calibration", "test"):
        path = root / f"{split}.jsonl"
        raw = path.read_bytes()
        items = [json.loads(line) for line in raw.splitlines() if line.strip()]
        files[split] = {
            "path": f"data/{split}.jsonl",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "items": len(items),
            "rules": len({item["rule_id"] for item in items}),
        }
    return {
        "builder": "corpus-20260929-s17-v2",
        "seed": 17,
        "files": files,
        "slicing_fields": [
            "role",
            "rule_held_out",
            "granularity",
            "provenance",
            "genre",
            "label_origin",
        ],
    }


if __name__ == "__main__":
    root = Path(sys.argv[1])
    print(json.dumps(manifest_for(root), indent=2))
