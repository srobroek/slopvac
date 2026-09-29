"""Score one arm's recorded predictions and write results/<arm>.json.

    $HARNESS_PY metrics.py <arm> [...]

Port of judge-pilot metrics.py for a SageMaker evaluation job. The metrics are unchanged; the
paths come from arms.py, `hardware` reads Linux and the CUDA device instead of sysctl, Kev's
runtime versions report a package that is not installed (mlx on Linux) as null, and a fine-tuned
arm's run record is read from finetune.json as the pilot does.

Primary predictions are the forward-order requests; reversed-order choice requests only feed the
order-swap agreement. "raw" is the distribution exactly as served (each project applies its own
shipped temperature). "cal" applies one temperature per question type fitted by NLL on the
calibration split: noul as sigmoid(logit(p)/T), choice as softmax(log(p)/T).
ECE is top-label confidence vs correctness over 15 equal-width bins on [0, 1].
Confidence intervals: 1,000 bootstrap resamples of test rules (state_rule clusters), seed 17.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import psutil

from arms import ARMS, KEV_PY, LAYA_PY, RESULTS, RUNS

CHOICE_ORDER = ["real-defect", "no-defect", "insufficient-context"]
EPS = 1e-6
BINS = 15
SEED = 17
TEMPS = np.exp(np.linspace(np.log(0.02), np.log(50.0), 1201))

VERSION_SNIPPETS = {
    "laya": "import json,laya,torch,transformers,fastapi,uvicorn;print(json.dumps({'laya':laya.__version__,"
    "'torch':torch.__version__,'transformers':transformers.__version__,'fastapi':fastapi.__version__,"
    "'uvicorn':uvicorn.__version__,'python':__import__('sys').version.split()[0]}))",
    "kev": "import json,importlib.metadata as m\n"
    "def v(p):\n"
    "    try:\n"
    "        return m.version(p)\n"
    "    except m.PackageNotFoundError:\n"
    "        return None\n"
    "print(json.dumps({p:v(p) for p in "
    "['torch','transformers','peft','mlx','mlx-lm','fastapi','uvicorn','numpy','fla-core']}|"
    "{'python':__import__('sys').version.split()[0]}))",
}
GPU_SNIPPET = (
    "import json,torch;p=torch.cuda.get_device_properties(0);print(json.dumps({"
    "'gpu':torch.cuda.get_device_name(0),'gpu_memory_bytes':p.total_memory,"
    "'gpu_count':torch.cuda.device_count(),'compute_capability':f'{p.major}.{p.minor}',"
    "'torch_cuda':torch.version.cuda}))"
)


def family_python(family):
    return LAYA_PY if family == "laya" else KEV_PY


def runtime_versions(family):
    return json.loads(
        subprocess.check_output(
            [str(family_python(family)), "-c", VERSION_SNIPPETS[family]], text=True
        )
    )


def hardware(family):
    """CPU, host memory and OS from Linux; the GPU as the arm's own torch sees it."""
    cpu = None
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            cpu = line.split(":", 1)[1].strip()
            break
    gpu = json.loads(
        subprocess.check_output(
            [str(family_python(family)), "-c", GPU_SNIPPET], text=True
        )
    )
    try:
        driver = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            text=True,
        ).split()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        driver = None
    return {
        "cpu": cpu,
        "cpu_count": os.cpu_count(),
        "memory_bytes": psutil.virtual_memory().total,
        "linux": platform.release(),
        "machine": platform.machine(),
        **gpu,
        "nvidia_driver": driver,
        "instance_type": os.environ.get("JUDGE_INSTANCE_TYPE"),
    }


# ---------- distributions ----------


def dist_of(rec):
    a = rec["answer"]
    if rec["kind"] == "noul":
        p = float(a["noul"])
        return np.array([1 - p, p])
    probs = a["probabilities"]
    return np.array([float(probs[k]) for k in CHOICE_ORDER])


def label_index(rec):
    if rec["kind"] == "noul":
        return int(bool(rec["label"]))
    return CHOICE_ORDER.index(rec["label"])


def scale(P, T):
    logits = np.log(np.clip(P, EPS, 1.0)) / T
    logits -= logits.max(axis=1, keepdims=True)
    e = np.exp(logits)
    return e / e.sum(axis=1, keepdims=True)


def nll(P, y):
    return float(-np.mean(np.log(np.clip(P[np.arange(len(y)), y], EPS, 1.0))))


def fit_temperature(P, y):
    losses = [nll(scale(P, t), y) for t in TEMPS]
    return float(TEMPS[int(np.argmin(losses))])


# ---------- metrics ----------


def auroc(scores, positives):
    pos, neg = scores[positives], scores[~positives]
    if len(pos) == 0 or len(neg) == 0:
        return None
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    ranks[order] = np.arange(1, len(allv) + 1)
    for v in np.unique(allv):
        m = allv == v
        ranks[m] = ranks[m].mean()
    return float(
        (ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2)
        / (len(pos) * len(neg))
    )


def ece(P, y):
    conf = P.max(axis=1)
    correct = (P.argmax(axis=1) == y).astype(float)
    edges = np.linspace(0, 1, BINS + 1)
    total = 0.0
    for i in range(BINS):
        m = (
            (conf > edges[i]) & (conf <= edges[i + 1])
            if i
            else (conf >= 0) & (conf <= edges[1])
        )
        if m.any():
            total += m.mean() * abs(conf[m].mean() - correct[m].mean())
    return float(total)


def balanced_accuracy(pred, y, classes):
    recalls = [float((pred[y == c] == c).mean()) for c in classes if (y == c).any()]
    return float(np.mean(recalls))


def summarize(P, y, kind):
    pred = P.argmax(axis=1)
    onehot = np.eye(P.shape[1])[y]
    positive_col, positive_cls, classes = (
        (1, 1, [0, 1]) if kind == "noul" else (0, 0, [0, 1])
    )
    out = {
        "n": int(len(y)),
        "accuracy": float((pred == y).mean()),
        "balanced_accuracy": balanced_accuracy(pred, y, classes),
        "auroc": auroc(P[:, positive_col], y == positive_cls),
        "brier": float(((P - onehot) ** 2).sum(axis=1).mean())
        if kind == "choice"
        else float(((P[:, 1] - y) ** 2).mean()),
        "nll": nll(P, y),
        "ece_15": ece(P, y),
    }
    if kind == "choice":
        out["abstain_rate"] = float((pred == 2).mean())
    return out


def bootstrap(P, y, clusters, kind, fn_keys=("balanced_accuracy", "ece_15"), reps=1000):
    rng = np.random.default_rng(SEED)
    ids = np.unique(clusters)
    index = {c: np.flatnonzero(clusters == c) for c in ids}
    samples = {k: [] for k in fn_keys}
    for _ in range(reps):
        pick = np.concatenate(
            [index[c] for c in rng.choice(ids, size=len(ids), replace=True)]
        )
        score = summarize(P[pick], y[pick], kind)
        for key in fn_keys:
            samples[key].append(score[key])
    return {
        key: [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
        for key, values in samples.items()
    }


def by_source(P, y, sources):
    pred = P.argmax(axis=1)
    return {
        source: {
            "n": int((sources == source).sum()),
            "accuracy": float((pred[sources == source] == y[sources == source]).mean()),
        }
        for source in np.unique(sources)
    }


def score_kind(records, kind):
    fwd = {r["id"]: r for r in records if r["kind"] == kind and r["order"] == "forward"}
    ok = {
        item_id: row
        for item_id, row in fwd.items()
        if row["status"] == 200 and row["answer"]
    }
    res = {
        "errors": {
            item_id: row["error"] for item_id, row in fwd.items() if item_id not in ok
        }
    }

    def arrays(split):
        rows = [row for row in ok.values() if row["split"] == split]
        return (
            np.array([dist_of(row) for row in rows]),
            np.array([label_index(row) for row in rows]),
            np.array([row["state_rule"] for row in rows]),
            np.array([row["source"] for row in rows]),
            rows,
        )

    Pc, yc, _, _, _ = arrays("calibration")
    Pt, yt, ct, sources, test_rows = arrays("test")
    temperature = fit_temperature(Pc, yc)
    Ptc = scale(Pt, temperature)
    res["temperature_fit_on_calibration"] = temperature
    res["calibration_raw"] = summarize(Pc, yc, kind)
    res["test_raw"] = summarize(Pt, yt, kind)
    res["test_cal"] = summarize(Ptc, yt, kind)
    res["test_raw_ci95"] = bootstrap(Pt, yt, ct, kind)
    res["test_cal_ci95"] = bootstrap(Ptc, yt, ct, kind, fn_keys=("ece_15",))
    if kind == "noul":
        pred = Pt.argmax(axis=1)
        res["test_bad_recall"] = (
            float((pred[yt == 1] == 1).mean()) if (yt == 1).any() else None
        )
        res["test_good_recall"] = (
            float((pred[yt == 0] == 0).mean()) if (yt == 0).any() else None
        )
    slices = {}
    for field in ("role", "rule_held_out", "granularity", "provenance"):
        groups = {}
        for value in sorted({str(row.get(field, "unknown")) for row in test_rows}):
            mask = np.array(
                [str(row.get(field, "unknown")) == value for row in test_rows]
            )
            truth, predictions = yt[mask], Pt.argmax(axis=1)[mask]
            groups[value] = {
                "n": int(mask.sum()),
                "accuracy": float((predictions == truth).mean()),
                "balanced_accuracy": balanced_accuracy(
                    predictions, truth, list(range(Pt.shape[1]))
                ),
                "ece_15": ece(Pt[mask], truth),
                "bad_recall": float((predictions[truth == 1] == 1).mean())
                if (truth == 1).any()
                else None,
                "good_recall": float((predictions[truth == 0] == 0).mean())
                if (truth == 0).any()
                else None,
            }
        slices[field] = groups
    res["test_slices"] = slices
    res["test_accuracy_by_source"] = by_source(Pt, yt, sources)
    if kind == "choice":
        reversed_rows = {
            row["id"]: row
            for row in records
            if row["kind"] == kind
            and row["order"] == "reversed"
            and row["status"] == 200
            and row["answer"]
        }
        agree = [
            ok[item_id]["answer"]["choice"]
            == reversed_rows[item_id]["answer"]["choice"]
            for item_id in ok
            if item_id in reversed_rows and ok[item_id]["split"] == "test"
        ]
        res["test_order_swap_agreement"] = float(np.mean(agree))
        res["test_order_swap_n"] = len(agree)
        shift = [
            abs(
                ok[item_id]["answer"]["probabilities"]["real-defect"]
                - reversed_rows[item_id]["answer"]["probabilities"]["real-defect"]
            )
            for item_id in ok
            if item_id in reversed_rows and ok[item_id]["split"] == "test"
        ]
        res["test_order_swap_mean_abs_shift_real_defect"] = float(np.mean(shift))
    res["_test_ids"] = [row["id"] for row in test_rows]
    return res


def latency(records):
    test = [row for row in records if row["split"] == "test" and row["status"] == 200]
    latencies = np.array([row["latency_ms"] for row in test])
    noul = np.array([row["latency_ms"] for row in test if row["kind"] == "noul"])
    return {
        "single_request_all_test_ms": {
            "n": int(len(latencies)),
            "p50": float(np.percentile(latencies, 50)),
            "p95": float(np.percentile(latencies, 95)),
        },
        "single_request_noul_test_ms": {
            "n": int(len(noul)),
            "p50": float(np.percentile(noul, 50)),
            "p95": float(np.percentile(noul, 95)),
        },
    }


def main(names):
    manifest = json.loads((RESULTS / "dataset-manifest.json").read_text())
    inventory = json.loads((RESULTS / "inventory.json").read_text())
    for name in names:
        arm = ARMS[name]
        run = json.loads((RUNS / name / "run.json").read_text())
        records = [
            json.loads(line)
            for line in (RESULTS / "predictions" / f"{name}.jsonl")
            .read_text()
            .splitlines()
        ]
        noul, choice = score_kind(records, "noul"), score_kind(records, "choice")
        noul.pop("_test_ids")
        choice.pop("_test_ids")
        extra = {}
        if arm.get("ft_run"):
            extra["finetune"] = json.loads(
                (Path(arm["ft_run"]) / "finetune.json").read_text()
            )
        extra["host_contention"] = {"evaluation_run": run.get("host_contention")}
        remeasured = RUNS / name / "latency.json"
        if remeasured.exists():
            remeasure = json.loads(remeasured.read_text())
            extra["latency_evaluation_run"] = latency(records)
            extra["latency_remeasured_at"] = remeasure["measured_at"]
            extra["host_contention"]["latency_remeasure"] = remeasure["host_contention"]
        result = {
            "arm": name,
            "family": arm["family"],
            "model_repo": arm["repo"],
            "model_revision": arm["revision"],
            "base_model": arm.get("base"),
            "base_revision": arm.get("base_revision"),
            "local_weights": arm["local"],
            "upstream_repo_commit": arm["upstream_commit"],
            "served_model_field_sent": arm["model"],
            "served_model_field_returned": sorted(
                {row["model"] for row in records if row["model"]}
            ),
            "served_checkpoint_routed": sorted(
                {row["routed_to"] for row in records if row.get("routed_to")}
            ),
            "runtime": runtime_versions(arm["family"]),
            "device": (run.get("health") or {}).get("device")
            or "/".join(
                str(((run.get("health") or {}).get("models") or [{}])[0].get(key))
                for key in ("device", "backend", "dtype")
            ),
            "health": run.get("health"),
            "hardware": hardware(arm["family"]),
            "dataset": {
                key: {"sha256": value["sha256"], "items": value["items"]}
                for key, value in manifest["files"].items()
            },
            "inventory": inventory.get(name),
            "load_time_s": run["load_time_s"],
            "warmup_latency_ms": run.get("warmup_latency_ms"),
            "memory": run["memory"],
            "latency": latency(records),
            "throughput": run["throughput"],
            "metrics": {"noul": noul, "choice": choice},
            "compat": run["compat"],
            **extra,
        }
        (RESULTS / f"{name}.json").write_text(
            json.dumps(result, indent=2, default=str) + "\n"
        )
        n, c = noul["test_raw"], choice["test_raw"]
        print(
            f"{name}: noul acc={n['accuracy']:.3f} bal={n['balanced_accuracy']:.3f} auroc={n['auroc']} ece raw={n['ece_15']:.3f} cal={noul['test_cal']['ece_15']:.3f} T={noul['temperature_fit_on_calibration']:.2f} | choice acc={c['accuracy']:.3f} bal={c['balanced_accuracy']:.3f} swap={choice['test_order_swap_agreement']:.3f} abstain={c['abstain_rate']:.3f} | p50={result['latency']['single_request_all_test_ms']['p50']:.1f}ms"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
