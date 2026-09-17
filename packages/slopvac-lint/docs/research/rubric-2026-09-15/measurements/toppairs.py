"""Top co-occurring rule pairs (paragraph units) on the session corpus; reuses cooccurrence.py helpers."""
import itertools
import math
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cooccurrence import WORK, bucket, lint, paragraphs

files = sorted(map(str, (WORK / "sessions").glob("*.md")))
res = lint(files, WORK)
presence = defaultdict(set)
N = 0
counts = defaultdict(int)
for d in res["documents"]:
    p = pathlib.Path(d["path"])
    p = p if p.is_absolute() else WORK / p
    spans = paragraphs(p.read_text(encoding="utf-8", errors="replace"))
    N += len(spans)
    fs = [f for f in d["findings"] if not (f["line"] == 1 and not f["matched_text"])]
    for key, group in bucket(fs, spans, None).items():
        for f in group:
            presence[f["rule_id"]].add((str(p), key))
            counts[f["rule_id"]] += 1
rows = []
for a, b in itertools.combinations(sorted(r for r in presence if len(presence[r]) >= 10), 2):
    ua, ub = presence[a], presence[b]
    inter = len(ua & ub)
    union = len(ua | ub)
    n11, n10, n01 = inter, len(ua) - inter, len(ub) - inter
    n00 = N - union
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    phi = ((n11 * n00) - (n10 * n01)) / den if den else 0
    rows.append((phi, inter / union, inter, len(ua), len(ub), a, b, a.split(".")[0] == b.split(".")[0]))
rows.sort(reverse=True)
print("units", N)
print("top 15 pairs by phi (phi, jaccard, both, |a|, |b|, a, b, same_category):")
for r in rows[:15]:
    print(f"  {r[0]:.3f} {r[1]:.3f} {r[2]:4d} {r[3]:4d} {r[4]:4d} {r[5]} {r[6]} same={r[7]}")
print("top 8 within-category pairs:")
for r in [x for x in rows if x[7]][:8]:
    print(f"  {r[0]:.3f} {r[1]:.3f} {r[2]:4d} {r[3]:4d} {r[4]:4d} {r[5]} {r[6]}")
print("most frequent rules:", sorted(counts.items(), key=lambda kv: -kv[1])[:12])
