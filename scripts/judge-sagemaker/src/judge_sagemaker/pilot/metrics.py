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
        return np.array([1 - p, p])  # [false, true]
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
    for v in np.unique(allv):  # average ranks over ties
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
        s = summarize(P[pick], y[pick], kind)
        for k in fn_keys:
            samples[k].append(s[k])
    return {
        k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
        for k, v in samples.items()
    }


def by_source(P, y, sources):
    pred = P.argmax(axis=1)
    return {
        s: {
            "n": int((sources == s).sum()),
            "accuracy": float((pred[sources == s] == y[sources == s]).mean()),
        }
        for s in np.unique(sources)
    }


def score_kind(records, kind):
    fwd = {r["id"]: r for r in records if r["kind"] == kind and r["order"] == "forward"}
    ok = {i: r for i, r in fwd.items() if r["status"] == 200 and r["answer"]}
    res = {"errors": {i: r["error"] for i, r in fwd.items() if i not in ok}}

    def arrays(split):
        rs = [r for r in ok.values() if r["split"] == split]
        return (
            np.array([dist_of(r) for r in rs]),
            np.array([label_index(r) for r in rs]),
            np.array([r["state_rule"] for r in rs]),
            np.array([r["source"] for r in rs]),
            rs,
        )

    Pc, yc, _, _, _ = arrays("calibration")
    Pt, yt, ct, st, rt = arrays("test")
    T = fit_temperature(Pc, yc)
    Ptc = scale(Pt, T)
    res["temperature_fit_on_calibration"] = T
    res["calibration_raw"] = summarize(Pc, yc, kind)
    res["test_raw"] = summarize(Pt, yt, kind)
    res["test_cal"] = summarize(Ptc, yt, kind)
    res["test_raw_ci95"] = bootstrap(Pt, yt, ct, kind)
    res["test_cal_ci95"] = bootstrap(Ptc, yt, ct, kind, fn_keys=("ece_15",))
    res["test_accuracy_by_source"] = by_source(Pt, yt, st)
    if kind == "choice":
        rev = {
            r["id"]: r
            for r in records
            if r["kind"] == kind
            and r["order"] == "reversed"
            and r["status"] == 200
            and r["answer"]
        }
        agree = [
            ok[i]["answer"]["choice"] == rev[i]["answer"]["choice"]
            for i in ok
            if i in rev and ok[i]["split"] == "test"
        ]
        res["test_order_swap_agreement"] = float(np.mean(agree))
        res["test_order_swap_n"] = len(agree)
        mean_shift = [
            abs(
                ok[i]["answer"]["probabilities"]["real-defect"]
                - rev[i]["answer"]["probabilities"]["real-defect"]
            )
            for i in ok
            if i in rev and ok[i]["split"] == "test"
        ]
        res["test_order_swap_mean_abs_shift_real_defect"] = float(np.mean(mean_shift))
    res["_test_ids"] = [r["id"] for r in rt]
    return res


def latency(records):
    test = [r for r in records if r["split"] == "test" and r["status"] == 200]
    lat = np.array([r["latency_ms"] for r in test])
    noul = np.array([r["latency_ms"] for r in test if r["kind"] == "noul"])
    return {
        "single_request_all_test_ms": {
            "n": int(len(lat)),
            "p50": float(np.percentile(lat, 50)),
            "p95": float(np.percentile(lat, 95)),
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
            lat = json.loads(remeasured.read_text())
            extra["latency_evaluation_run"] = latency(records)
            extra["latency_remeasured_at"] = lat["measured_at"]
            extra["host_contention"]["latency_remeasure"] = lat["host_contention"]
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
                {r["model"] for r in records if r["model"]}
            ),
            "served_checkpoint_routed": sorted(
                {r["routed_to"] for r in records if r.get("routed_to")}
            ),
            "runtime": runtime_versions(arm["family"]),
            "device": (run.get("health") or {}).get("device")
            or "/".join(
                str(((run.get("health") or {}).get("models") or [{}])[0].get(k))
                for k in ("device", "backend", "dtype")
            ),
            "health": run.get("health"),
            "hardware": hardware(arm["family"]),
            "dataset": {
                k: {"sha256": v["sha256"], "items": v["items"]}
                for k, v in manifest["files"].items()
            },
            "inventory": inventory.get(name),
            "load_time_s": run["load_time_s"],
            "warmup_latency_ms": run.get("warmup_latency_ms"),
            "memory": run["memory"],
            "latency": latency(lat["requests"] if remeasured.exists() else records),
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
            f"{name}: noul acc={n['accuracy']:.3f} bal={n['balanced_accuracy']:.3f} auroc={n['auroc']} "
            f"ece raw={n['ece_15']:.3f} cal={noul['test_cal']['ece_15']:.3f} T={noul['temperature_fit_on_calibration']:.2f}"
            f" | choice acc={c['accuracy']:.3f} bal={c['balanced_accuracy']:.3f} swap={choice['test_order_swap_agreement']:.3f}"
            f" abstain={c['abstain_rate']:.3f} | p50={result['latency']['single_request_all_test_ms']['p50']:.1f}ms"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
