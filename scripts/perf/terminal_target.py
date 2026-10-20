"""Give the notifier scenario a terminal even when the profiler captures output."""

import os
import pty
import sys

if __name__ == "__main__":
    status = pty.spawn(sys.argv[1:])
    raise SystemExit(os.waitstatus_to_exitcode(status))
