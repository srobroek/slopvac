"""Query one running arm over its Jev-compatible HTTP API and record raw answers and performance.

    $HARNESS_PY run_arm.py <arm> --port P --skip-throughput

Port of judge-pilot run_arm.py for a SageMaker evaluation job; only the paths differ (arms.py:
DATA, RESULTS, RUNS under JUDGE_EVAL_OUT). Needs the arm's server running (serve_arm.py). Steps:
  1. wait for readiness and record load time (process start -> first 200 on the health route);
  2. Jev wire-compatibility probe (compat.py);
  3. sequential single-question requests over calibration + test, in seeded shuffled order:
     every noul item once, every choice item twice (options forward and reversed);
  4. batched throughput: the test requests again with 16 concurrent clients (the job skips it);
  5. peak memory of the server process (sampled RSS, VmHWM and sampled GPU memory).
Writes runs/<arm>/run.json and results/predictions/<arm>.jsonl.
"""

import argparse
import http.client
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import psutil

import compat
import memory
from arms import ARMS, DATA, RESULTS, RUNS

PRED_DIR = RESULTS / "predictions"
CHOICE_ORDER = ["real-defect", "no-defect", "insufficient-context"]
SEED = 17
CONCURRENCY = 16


class Client:
    """One keep-alive HTTP connection per thread."""

    def __init__(self, port, timeout=300):
        self.port, self.timeout = port, timeout
        self.local = threading.local()

    def _conn(self):
        c = getattr(self.local, "conn", None)
        if c is None:
            c = self.local.conn = http.client.HTTPConnection(
                "127.0.0.1", self.port, timeout=self.timeout
            )
        return c

    def request(self, method, path, body=None, headers=None):
        data = (
            None
            if body is None
            else (body if isinstance(body, bytes) else json.dumps(body).encode())
        )
        hdrs = {"content-type": "application/json", **(headers or {})}
        for attempt in range(2):
            try:
                c = self._conn()
                t0 = time.perf_counter()
                c.request(method, path, body=data, headers=hdrs)
                r = c.getresponse()
                raw = r.read()
                dt = (time.perf_counter() - t0) * 1000
                try:
                    payload = json.loads(raw) if raw else None
                except ValueError:
                    payload = {"_non_json": raw[:500].decode("utf-8", "replace")}
                return r.status, payload, dict(r.getheaders()), dt
            except (http.client.HTTPException, ConnectionError, OSError):
                self.local.conn = None
                if attempt:
                    raise
        raise RuntimeError("unreachable")


def wait_ready(server_json, client, family, timeout=3600):
    """Wait until serve_arm.py has recorded readiness; return its record and the health payload."""
    path = "/health" if family == "laya" else "/v1/models"
    t0 = time.time()
    while time.time() - t0 < timeout:
        server = json.loads(server_json.read_text())
        if "load_time_s" in server:
            return server, client.request("GET", path)[1]
        time.sleep(0.5)
    raise TimeoutError("server not ready")


def load_items(splits):
    items = []
    for split in splits:
        items += [
            json.loads(line)
            for line in (DATA / f"{split}.jsonl").read_text().splitlines()
        ]
    return items


def body_for(arm, item, order):
    q = {
        "type": item["question"]["type"],
        "instructions": item["question"]["instructions"],
    }
    if item["kind"] == "choice":
        keys = CHOICE_ORDER if order == "forward" else list(reversed(CHOICE_ORDER))
        q["criteria"] = {k: item["question"]["criteria"][k] for k in keys}
    return {"state": item["state"], "model": arm["model"], "questions": {"q": q}}


def request_plan(items):
    plan = []
    for it in items:
        plan.append((it, "forward"))
        if it["kind"] == "choice":
            plan.append((it, "reversed"))
    random.Random(SEED).shuffle(plan)
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument(
        "--skip-throughput",
        action="store_true",
        help="skip step 4 (16 concurrent clients); only single-client sequential requests",
    )
    ap.add_argument(
        "--latency-only",
        action="store_true",
        help="re-measure step 3's single-client latency only (answers discarded); writes "
        ".cache/runs/<arm>/latency.json and leaves run.json and the predictions untouched",
    )
    a = ap.parse_args()
    arm = ARMS[a.arm]
    out = RUNS / a.arm
    client = Client(a.port)
    server, health = wait_ready(out / "server.json", client, arm["family"])
    load_time_s = server["load_time_s"]
    print(f"{a.arm}: ready after {load_time_s:.1f}s", flush=True)

    sampler = memory.Sampler(server["pid"])
    sampler.start()
    exclude = {os.getpid(), server["pid"]} | {
        c.pid for c in psutil.Process(server["pid"]).children(recursive=True)
    }
    if os.getppid() > 1:
        exclude.add(os.getppid())
    host = [memory.host_contention(exclude)]

    items = load_items(["calibration", "test"])
    # Warm-up, excluded from latency: the first request after load pays one-off compilation.
    warmup_ms = [
        round(client.request("POST", "/v1/systemone", body_for(arm, it, order))[3], 1)
        for it, order in request_plan(items)[:3]
    ]

    if a.latency_only:
        timings = []
        t_seq = time.perf_counter()
        for it, order in request_plan(items):
            status, _p, _h, dt = client.request(
                "POST", "/v1/systemone", body_for(arm, it, order)
            )
            timings.append(
                {
                    "split": it["split"],
                    "kind": it["kind"],
                    "order": order,
                    "status": status,
                    "latency_ms": round(dt, 3),
                }
            )
        host.append(memory.host_contention(exclude))
        (out / "latency.json").write_text(
            json.dumps(
                {
                    "arm": a.arm,
                    "measured_at": time.time(),
                    "wall_s": round(time.perf_counter() - t_seq, 2),
                    "warmup_latency_ms": warmup_ms,
                    "memory": sampler.stop(),
                    "host_contention": host,
                    "requests": timings,
                },
                indent=2,
            )
        )
        print(f"{a.arm}: latency re-measured, {len(timings)} requests", flush=True)
        return

    probe = compat.probe(client, arm)
    print(f"{a.arm}: compat probe done", flush=True)
    records = []
    t_seq = time.perf_counter()
    for n, (it, order) in enumerate(request_plan(items)):
        status, payload, _headers, dt = client.request(
            "POST", "/v1/systemone", body_for(arm, it, order)
        )
        if not isinstance(payload, dict):
            payload = {"_payload": payload}
        answer = payload.get("answers", {}).get("q") if status == 200 else None
        records.append(
            {
                "id": it["id"],
                "split": it["split"],
                "kind": it["kind"],
                "order": order,
                "label": it["label"],
                "state_rule": it["state_rule"],
                "asked_rule": it["asked_rule"],
                "source": it["source"],
                "status": status,
                "latency_ms": round(dt, 3),
                "server_latency_ms": payload.get("latency_ms")
                if status == 200
                else None,
                "model": payload.get("model") if status == 200 else None,
                "routed_to": (payload.get("routing") or {}).get("model")
                if status == 200
                else None,
                "answer": answer,
                "error": None if status == 200 else payload,
            }
        )
        if n % 100 == 0:
            print(f"{a.arm}: {n} requests", flush=True)
    seq_wall = time.perf_counter() - t_seq
    host.append(memory.host_contention(exclude))

    throughput = None
    if not a.skip_throughput:
        test_plan = [p for p in request_plan(items) if p[0]["split"] == "test"]
        t_batch = time.perf_counter()
        with ThreadPoolExecutor(CONCURRENCY) as pool:
            statuses = list(
                pool.map(
                    lambda p: client.request(
                        "POST", "/v1/systemone", body_for(arm, *p)
                    )[0],
                    test_plan,
                )
            )
        batch_wall = time.perf_counter() - t_batch
        throughput = {
            "concurrency": CONCURRENCY,
            "requests": len(test_plan),
            "wall_s": round(batch_wall, 2),
            "questions_per_s": round(len(test_plan) / batch_wall, 2),
            "non_200": sum(1 for s in statuses if s != 200),
        }

    peak = sampler.stop()
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    (PRED_DIR / f"{a.arm}.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
    )
    proc = psutil.Process(server["pid"])
    run = {
        "arm": a.arm,
        "arm_config": {k: v for k, v in arm.items() if k != "downloads"},
        "server": server,
        "health": health,
        "load_time_s": round(load_time_s, 2),
        "warmup_latency_ms": warmup_ms,
        "sequential": {"requests": len(records), "wall_s": round(seq_wall, 2)},
        "throughput": throughput,
        "memory": peak,
        "server_cmdline": proc.cmdline(),
        "compat": probe,
        "host_contention": host,
    }
    (out / "run.json").write_text(json.dumps(run, indent=2, default=str))
    print(
        json.dumps(
            {k: run[k] for k in ("load_time_s", "sequential", "throughput", "memory")},
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
