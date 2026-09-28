"""Peak memory of a server process: sampled RSS (psutil) and macOS lifetime max phys_footprint.

phys_footprint is what Activity Monitor calls "Memory"; unlike RSS it includes Metal/MLX buffers in
unified memory, so it is the honest peak for GPU-backed arms on Apple Silicon.
"""

import ctypes
import struct
import threading
import time

import psutil

_RUSAGE_INFO_V4 = 4
# struct rusage_info_v4: 16-byte uuid, then uint64 fields. ri_phys_footprint is field 7,
# ri_lifetime_max_phys_footprint is field 28 (v0:10 + v1:6 + v2:2 + v3:9 + ri_logical_writes).
_OFF_FOOTPRINT = 16 + 7 * 8
_OFF_LIFETIME_MAX = 16 + 28 * 8


def rusage_footprint(pid):
    libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    buf = ctypes.create_string_buffer(512)
    if libc.proc_pid_rusage(ctypes.c_int(pid), ctypes.c_int(_RUSAGE_INFO_V4), buf) != 0:
        return None
    return {
        "phys_footprint_bytes": struct.unpack_from("<Q", buf.raw, _OFF_FOOTPRINT)[0],
        "lifetime_max_phys_footprint_bytes": struct.unpack_from(
            "<Q", buf.raw, _OFF_LIFETIME_MAX
        )[0],
    }


class Sampler(threading.Thread):
    def __init__(self, pid, interval=0.2):
        super().__init__(daemon=True)
        self.proc = psutil.Process(pid)
        self.interval = interval
        self.peak_rss = 0
        self._stop_evt = threading.Event()

    def run(self):
        while not self._stop_evt.is_set():
            try:
                rss = self.proc.memory_info().rss + sum(
                    c.memory_info().rss for c in self.proc.children(recursive=True)
                )
            except psutil.Error:
                break
            self.peak_rss = max(self.peak_rss, rss)
            time.sleep(self.interval)

    def stop(self):
        self._stop_evt.set()
        self.join()
        out = {"peak_rss_bytes_sampled": self.peak_rss}
        out.update(rusage_footprint(self.proc.pid) or {})
        return out
