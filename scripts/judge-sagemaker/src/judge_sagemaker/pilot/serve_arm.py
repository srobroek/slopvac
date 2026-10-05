"""Launch one arm's Jev-compatible server in the foreground.

    python3 serve_arm.py <arm> <port>

Verbatim judge-pilot serve_arm.py; the paths come from arms.py. Starts the project's own server as
a child process, records its pid and wall-clock start in runs/<arm>/server.json, polls the health
route every 0.1 s, and adds `ready_at` and `load_time_s` (process start -> first HTTP 200) once it
answers. SIGTERM/SIGINT are forwarded to the child; the launcher exits with the child's status.
Laya: laya.serve.create_app over a single-checkpoint Router (laya_server.py).
Kev: `python -m kev.serve --run <repo>@<revision>` (or the local fine-tuned run) from the pinned checkout.
Clef: the release's joint_schema_model.systemone behind FastAPI (clef_server.py).
"""

import json
import signal
import subprocess
import sys
import time
import urllib.request

from arms import ARMS, CLEF_PY, KEV_PY, KEV_SRC, LAYA_PY, PILOT, RUNS


def main():
    name, port = sys.argv[1], sys.argv[2]
    arm = ARMS[name]
    out = RUNS / name
    out.mkdir(parents=True, exist_ok=True)
    if arm["family"] == "laya":
        argv = [str(LAYA_PY), str(PILOT / "laya_server.py"), name, port]
        cwd, health = PILOT, "/health"
    elif arm["family"] == "clef":
        argv = [str(CLEF_PY), str(PILOT / "clef_server.py"), name, port]
        cwd, health = PILOT, "/v1/models"
    else:
        run = arm["local"] or f"{arm['repo']}@{arm['revision']}"
        argv = [str(KEV_PY), "-m", "kev.serve", "--run", run, "--port", port]
        cwd, health = KEV_SRC, "/v1/models"
    record = {"arm": name, "started_at": time.time(), "argv": argv, "port": int(port)}
    child = subprocess.Popen(argv, cwd=cwd)
    record["pid"] = child.pid
    (out / "server.json").write_text(json.dumps(record, indent=2))
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, _f: child.send_signal(s))
    while child.poll() is None:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}{health}", timeout=5
            ) as r:
                if r.status == 200:
                    record["ready_at"] = time.time()
                    record["load_time_s"] = round(
                        record["ready_at"] - record["started_at"], 2
                    )
                    (out / "server.json").write_text(json.dumps(record, indent=2))
                    print(
                        f"serve_arm: {name} ready in {record['load_time_s']} s",
                        flush=True,
                    )
                    break
        except OSError:
            time.sleep(0.1)
    sys.exit(child.wait())


if __name__ == "__main__":
    main()
