"""Peak memory of a server process on Linux: sampled RSS (psutil), VmHWM, and sampled GPU memory.

Port of judge-pilot memory.py. The pilot read macOS lifetime max phys_footprint, which counts
Metal/MLX buffers in unified memory. On a CUDA host the equivalents are split: host memory peaks
are the kernel's VmHWM (resident-set high-water mark, /proc/<pid>/status) summed over the server
process tree, and device memory is sampled per process from nvidia-smi. The pilot's field names
are kept for its consumers (compare.py reads `lifetime_max_phys_footprint_bytes`); on Linux that
field carries the VmHWM sum and `footprint_source` says so.
"""

import subprocess
import threading
import time

import psutil

FOOTPRINT_SOURCE = (
    "linux: lifetime_max_phys_footprint_bytes and phys_footprint_bytes are the sums of VmHWM and "
    "VmRSS (/proc/<pid>/status) over the server process tree; GPU memory is "
    "peak_gpu_memory_bytes_sampled (nvidia-smi per-process used memory, summed over the tree)"
)


def _status_bytes(pid, key):
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith(key + ":"):
                    return int(line.split()[1]) * 1024  # the kernel reports kB
    except OSError:
        return None
    return None


def _tree(pid):
    try:
        proc = psutil.Process(pid)
        return [proc] + proc.children(recursive=True)
    except psutil.Error:
        return []


def rusage_footprint(pid):
    """VmRSS and VmHWM summed over the process tree, under the pilot's field names."""
    procs = _tree(pid)
    if not procs:
        return None
    rss = [_status_bytes(p.pid, "VmRSS") for p in procs]
    hwm = [_status_bytes(p.pid, "VmHWM") for p in procs]
    return {
        "phys_footprint_bytes": sum(v for v in rss if v),
        "lifetime_max_phys_footprint_bytes": sum(v for v in hwm if v),
        "footprint_source": FOOTPRINT_SOURCE,
    }


def gpu_process_bytes():
    """{pid: used GPU memory bytes} from nvidia-smi; empty when it is unavailable."""
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_memory",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    used = {}
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            used[int(parts[0])] = (
                used.get(int(parts[0]), 0) + int(parts[1]) * 1024 * 1024
            )
    return used


CONTENTION_MIN_FOOTPRINT = 1 << 30


def host_contention(exclude_pids=()):
    """Snapshot of what else holds memory on the host: swap in use and every other process whose
    resident set is at least 1 GiB (pid, name, command line, footprint)."""
    swap = psutil.swap_memory()
    others = []
    for p in psutil.process_iter(["pid", "name"]):
        if p.pid in exclude_pids:
            continue
        rss = _status_bytes(p.pid, "VmRSS")
        if not rss or rss < CONTENTION_MIN_FOOTPRINT:
            continue
        try:
            cmd = " ".join(p.cmdline())[:300]
        except psutil.Error:
            cmd = None
        others.append(
            {
                "pid": p.pid,
                "name": p.info["name"],
                "cmdline": cmd,
                "phys_footprint_bytes": rss,
            }
        )
    return {
        "at": time.time(),
        "swap_used_bytes": swap.used,
        "swap_total_bytes": swap.total,
        "memory_available_bytes": psutil.virtual_memory().available,
        "other_processes_over_1gib": sorted(
            others, key=lambda o: -o["phys_footprint_bytes"]
        ),
    }


class Sampler(threading.Thread):
    GPU_EVERY = 5  # nvidia-smi once per second at the default interval

    def __init__(self, pid, interval=0.2):
        super().__init__(daemon=True)
        self.proc = psutil.Process(pid)
        self.interval = interval
        self.peak_rss = 0
        self.peak_gpu = 0
        self._stop_evt = threading.Event()

    def run(self):
        n = 0
        while not self._stop_evt.is_set():
            try:
                tree = [self.proc] + self.proc.children(recursive=True)
                rss = sum(p.memory_info().rss for p in tree)
            except psutil.Error:
                break
            self.peak_rss = max(self.peak_rss, rss)
            if n % self.GPU_EVERY == 0:
                used = gpu_process_bytes()
                self.peak_gpu = max(
                    self.peak_gpu, sum(used.get(p.pid, 0) for p in tree)
                )
            n += 1
            time.sleep(self.interval)

    def stop(self):
        self._stop_evt.set()
        self.join()
        out = {
            "peak_rss_bytes_sampled": self.peak_rss,
            "peak_gpu_memory_bytes_sampled": self.peak_gpu,
        }
        out.update(rusage_footprint(self.proc.pid) or {})
        return out
