"""Collect a fine-tuning sweep and pick its configuration on the calibration split only.

    python3 sweep.py <base-arm>        # e.g. laya-typed-decisions, kev-0.8b

Reads .cache/runs/sweep-<base-arm>/*/finetune.json (every candidate trained with seed 17 on the
train split) and writes results/sweep-<base-arm>.json with each candidate's hyperparameters,
training cost and `calibration_eval`. The chosen candidate has the highest calibration noul
balanced accuracy; ties (within 0.005) go to the higher calibration noul AUROC, then to the
earlier (cheaper) candidate in the order they were trained. No test-split number is read here.
"""

import json
import sys

from arms import RUNS
from metrics import RESULTS

TIE = 0.005


def main():
    base = sys.argv[1]
    runs = []
    for meta_path in sorted((RUNS / f"sweep-{base}").glob("*/finetune.json")):
        meta = json.loads(meta_path.read_text())
        cal = meta["calibration_eval"]
        runs.append(
            {
                "tag": meta_path.parent.name,
                "trained_at": meta_path.stat().st_mtime,
                "hyperparameters": meta["hyperparameters"],
                "train_wall_time_s": meta.get(
                    "wall_time_s", meta.get("train_wall_time_s")
                ),
                "temperature_fit_on_calibration": meta.get(
                    "temperatures_fit_on_calibration",
                    meta.get("temperature_fit_on_calibration"),
                ),
                "calibration_eval": cal,
            }
        )
    runs.sort(key=lambda r: r["trained_at"])
    best = runs[0]
    for r in runs[1:]:
        rb, bb = (
            r["calibration_eval"]["noul"]["balanced_accuracy"],
            best["calibration_eval"]["noul"]["balanced_accuracy"],
        )
        if rb > bb + TIE or (
            abs(rb - bb) <= TIE
            and r["calibration_eval"]["noul"]["auroc"]
            > best["calibration_eval"]["noul"]["auroc"]
        ):
            best = r
    out = {
        "base": base,
        "rule": __doc__.split("\n\n")[2].replace("\n", " ").strip(),
        "candidates": runs,
        "chosen": best["tag"],
    }
    (RESULTS / f"sweep-{base}.json").write_text(json.dumps(out, indent=2) + "\n")
    for r in runs:
        n, c = r["calibration_eval"]["noul"], r["calibration_eval"]["choice"]
        print(
            f"{r['tag']}: cal noul bal={n['balanced_accuracy']:.3f} auroc={n['auroc']:.3f}"
            f" ece={n['ece_15']:.3f} | choice acc={c['accuracy']:.3f} | {r['train_wall_time_s']} s"
        )
    print("chosen:", best["tag"])


if __name__ == "__main__":
    main()
