import json
import os
import pathlib

import yaml

RULES = pathlib.Path(os.environ.get("SLOPVAC_CHECKOUT", pathlib.Path(__file__).resolve().parents[6])) / "packages/slopvac-lint/src/slopvac/rules"
out = {}
for p in sorted(RULES.glob("*.yml")):
    for doc in yaml.safe_load_all(p.read_text()):
        if not doc:
            continue
        for r in doc.get("rules", []):
            if r.get("kind") != "judgement":
                continue
            out.setdefault(doc["id"], {"weight": doc.get("weight", 1.0), "recommended_for": doc.get("recommended_for"), "rules": []})
            out[doc["id"]]["rules"].append({"id": r["id"], "scope": r.get("scope"), "severity": r.get("severity"), "tiers": r.get("tiers")})
print(json.dumps(out, indent=1))
