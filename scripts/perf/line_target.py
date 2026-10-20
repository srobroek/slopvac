"""Run the slopvac CLI under line_profiler, timing the functions named in PERF_LINE_FUNCS.

Each name is `module:qualname`, for example `slopvac.analyze:_align_block_text` or
`slopvac.engine:Engine.run`. line_profiler traces code objects, so a function is timed
wherever it is called from, and the source needs no `@profile` decorator.

Writes PERF_LINE_OUT (text, milliseconds) and PERF_LINE_OUT with `.lprof` (raw stats
for `python -m line_profiler`), then exits with the CLI's own exit code.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def resolve(spec: str):
    module_name, sep, qualname = spec.partition(":")
    if not sep or not qualname:
        raise SystemExit(f"perf-lines: {spec!r} is not module:qualname")
    target = importlib.import_module(module_name)
    for part in qualname.split("."):
        try:
            target = getattr(target, part)
        except AttributeError:
            raise SystemExit(f"perf-lines: {module_name} has no {qualname}") from None
    target = getattr(target, "__func__", target)
    if not hasattr(target, "__code__"):
        raise SystemExit(f"perf-lines: {spec} is not a Python function")
    return target


def main() -> int:
    specs = os.environ.get("PERF_LINE_FUNCS", "").split()
    if not specs:
        raise SystemExit("perf-lines: set FUNCS to one or more module:qualname names")
    out = Path(os.environ["PERF_LINE_OUT"])
    from line_profiler import LineProfiler

    profiler = LineProfiler()
    for spec in specs:
        profiler.add_function(resolve(spec))
    from slopvac.cli import main as cli_main

    sys.argv = ["slopvac", *sys.argv[1:]]
    code = 0
    profiler.enable()
    try:
        cli_main()
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else 1
    finally:
        profiler.disable()
        profiler.dump_stats(str(out.with_suffix(".lprof")))
        with out.open("w", encoding="utf-8") as handle:
            profiler.print_stats(stream=handle, output_unit=1e-3, stripzeros=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
