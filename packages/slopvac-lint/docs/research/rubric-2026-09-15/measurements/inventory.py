"""Rule inventory (design doc §0/§8 re-measurement) and top co-occurring rule pairs."""
import json
import os
import pathlib
import statistics
from collections import Counter

import yaml

CHECKOUT = pathlib.Path(os.environ.get("SLOPVAC_CHECKOUT", pathlib.Path(__file__).resolve().parents[6]))
RULES = CHECKOUT / "packages/slopvac-lint/src/slopvac/rules"

rules = []
files = sorted(RULES.glob("*.yml"))
for p in files:
    for doc in yaml.safe_load_all(p.read_text()):
        if not doc:
            continue
        for r in doc.get("rules", []):
            rules.append((p.name, doc["id"], r))

cats = {c for _, c, _ in rules}
print("files", len(files), "rules", len(rules), "categories", len(cats))
judgement = [(f, c, r) for f, c, r in rules if r.get("kind") == "judgement"]
jq = [(f, c, r) for f, c, r in rules if r.get("judgement_question")]
print("kind=judgement", len(judgement), "| with judgement_question", len(jq))
print("judgement categories", len({c for _, c, _ in judgement}), "zero-judgement categories", sorted(cats - {c for _, c, _ in judgement}))
print("per category", Counter(c for _, c, _ in judgement).most_common())
print("per scope", Counter(r.get("scope") for _, _, r in judgement).most_common())
print("severity", Counter(r.get("severity") for _, _, r in judgement).most_common())
print("tiers", Counter(json.dumps(r.get("tiers"), sort_keys=True) for _, _, r in judgement).most_common(5))
def selected(profile_key):
    return sum(1 for _, _, r in judgement if (r.get("tiers") or {}).get(profile_key) in ("enforced", "advisory"))
print("selected strict/normal/relaxed", selected("strict"), selected("normal"), selected("relaxed"))
crit = [(r.get("name", "") + " " + (r.get("judgement_question") or "") + " " + (r.get("fix") or "") + " " + (r.get("message") or "")) for _, _, r in judgement]
lens = [len(c) for c in crit]
print("criterion chars (name+question+fix+message) mean/max/sum", round(statistics.mean(lens)), max(lens), sum(lens))
ql = [len(r.get("judgement_question") or "") for _, _, r in judgement]
print("judgement_question chars mean/max", round(statistics.mean(ql)), max(ql))
print("keys on judgement rules", Counter(k for _, _, r in judgement for k in r).most_common(40))
print("local vs probe (scope in paragraph/sentence = local)", Counter("probe" if r.get("scope") in ("document", "prose") else "local" for _, _, r in judgement))
print("per category local/probe:")
for c in sorted({c for _, c, _ in judgement}):
    loc = sum(1 for _, cc, r in judgement if cc == c and r.get("scope") not in ("document", "prose"))
    pro = sum(1 for _, cc, r in judgement if cc == c and r.get("scope") in ("document", "prose"))
    print(f"  {c}: local={loc} probe={pro}")
print("recommended_for per category:", {doc_id: None for doc_id in []})
