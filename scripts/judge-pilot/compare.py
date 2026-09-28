"""Post-training comparison: paired bootstrap tests and seed summaries over recorded test predictions.

    uv run --no-project --with-requirements requirements-harness.txt python compare.py

For every fine-tuned arm whose results/<arm>.json exists (arms.FT_BASES x arms.FT_SEEDS), compares
its forward-order test noul predictions with (a) its own base arm and (b) base kev-4b, paired on
item id. One bootstrap replicate resamples the 39 test rules (state_rule clusters) with
replacement, seed 17, and computes both arms' balanced accuracy (threshold 0.5) and AUROC on the
same resampled items; the reported interval is the 2.5/97.5 percentile of the difference (A - B)
and p is the two-sided bootstrap p-value 2 * min(P(diff <= 0), P(diff >= 0)). Both statistics
are invariant to the harness's calibration temperature, so raw served probabilities are used.
Also summarizes each fine-tuned configuration over its seeds (mean, min, max) from the result
JSONs. Writes results/post-training.json.
"""

import json

import numpy as np

from arms import ARMS, FT_BASES, FT_SEEDS
from metrics import RESULTS, SEED, auroc, balanced_accuracy, dist_of, label_index

REPS = 10000


def noul_test(name):
    path = RESULTS / "predictions" / f"{name}.jsonl"
    recs = [json.loads(line) for line in path.read_text().splitlines()]
    return {
        r["id"]: (dist_of(r)[1], label_index(r), r["state_rule"])
        for r in recs
        if r["kind"] == "noul"
        and r["order"] == "forward"
        and r["split"] == "test"
        and r["status"] == 200
        and r["answer"]
    }


def stats(p, y):
    return balanced_accuracy((p >= 0.5).astype(int), y, [0, 1]), auroc(p, y == 1)


def paired(a, b):
    A, B = noul_test(a), noul_test(b)
    ids = sorted(set(A) & set(B))
    pa = np.array([A[i][0] for i in ids])
    pb = np.array([B[i][0] for i in ids])
    y = np.array([A[i][1] for i in ids])
    assert all(A[i][1] == B[i][1] for i in ids)
    rules = np.array([A[i][2] for i in ids])
    uniq = np.unique(rules)
    index = {c: np.flatnonzero(rules == c) for c in uniq}
    rng = np.random.default_rng(SEED)
    diffs = {"balanced_accuracy": [], "auroc": []}
    for _ in range(REPS):
        pick = np.concatenate([index[c] for c in rng.choice(uniq, size=len(uniq))])
        (ba, aa), (bb, ab) = stats(pa[pick], y[pick]), stats(pb[pick], y[pick])
        diffs["balanced_accuracy"].append(ba - bb)
        if aa is not None and ab is not None:
            diffs["auroc"].append(aa - ab)
    point_a, point_b = stats(pa, y), stats(pb, y)
    out = {"a": a, "b": b, "n_items": len(ids), "n_rules": len(uniq), "reps": REPS}
    for k, i in (("balanced_accuracy", 0), ("auroc", 1)):
        d = np.array(diffs[k])
        out[k] = {
            "a": point_a[i],
            "b": point_b[i],
            "diff": point_a[i] - point_b[i],
            "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "p_two_sided": float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean()))),
            "valid_reps": int(len(d)),
        }
    return out


def headline(r):
    n, c = r["metrics"]["noul"], r["metrics"]["choice"]
    src = n["test_accuracy_by_source"]
    out = {
        "noul_accuracy": n["test_raw"]["accuracy"],
        "noul_balanced_accuracy": n["test_raw"]["balanced_accuracy"],
        "noul_auroc": n["test_raw"]["auroc"],
        "noul_brier": n["test_raw"]["brier"],
        "noul_ece_raw": n["test_raw"]["ece_15"],
        "noul_ece_cal": n["test_cal"]["ece_15"],
        "choice_accuracy": c["test_raw"]["accuracy"],
        "choice_ece_raw": c["test_raw"]["ece_15"],
        "choice_ece_cal": c["test_cal"]["ece_15"],
        "order_swap_agreement": c["test_order_swap_agreement"],
        "abstain_rate": c["test_raw"]["abstain_rate"],
        "latency_p50_ms": r["latency"]["single_request_all_test_ms"]["p50"],
        "latency_p95_ms": r["latency"]["single_request_all_test_ms"]["p95"],
        "peak_footprint_bytes": r["memory"]["lifetime_max_phys_footprint_bytes"],
    }
    # build_dataset.py sources: bad (label true), good (same-rule clean), cross (hard negative)
    for s in ("bad", "good", "cross"):
        out[f"noul_accuracy_{s}"] = src[s]["accuracy"]
    for s in ("bad", "good"):
        out[f"choice_accuracy_{s}"] = c["test_accuracy_by_source"][s]["accuracy"]
    return out


def main():
    report = {"paired": [], "seeds": {}}
    for base in FT_BASES:
        rows = {}
        for seed in FT_SEEDS:
            name = f"{base}-ft-s{seed}"
            if not (RESULTS / f"{name}.json").exists():
                continue
            rows[seed] = headline(json.loads((RESULTS / f"{name}.json").read_text()))
            for ref in dict.fromkeys([base, "kev-4b"]):
                report["paired"].append(paired(name, ref))
        if rows:
            report["seeds"][base] = {
                "seeds": sorted(rows),
                "per_seed": rows,
                "summary": {
                    k: {
                        "mean": float(np.mean([v[k] for v in rows.values()])),
                        "min": float(min(v[k] for v in rows.values())),
                        "max": float(max(v[k] for v in rows.values())),
                    }
                    for k in next(iter(rows.values()))
                },
            }
    (RESULTS / "post-training.json").write_text(json.dumps(report, indent=2) + "\n")
    for p in report["paired"]:
        b, a = p["balanced_accuracy"], p["auroc"]
        print(
            f"{p['a']} vs {p['b']}: bal {b['diff']:+.3f} {b['ci95']} p={b['p_two_sided']:.3f}"
            f" | auroc {a['diff']:+.3f} {a['ci95']} p={a['p_two_sided']:.3f}"
        )


if __name__ == "__main__":
    assert set(ARMS) >= {f"{b}-ft-s{s}" for b in FT_BASES for s in FT_SEEDS}
    main()
