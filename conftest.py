"""Fail the session when the Vale on PATH is not the version mise pins.

CI installs the pinned Vale from `mise.toml`. A developer whose shell resolves
another `vale` first (for example a Homebrew install) gets failures that look
like rule bugs but come from Vale output drift. Refusing to run is safer than
skipping: a skip would hide real failures, and CI keeps the exit code non-zero.
The fix is to run the suite through the pinned toolchain.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
_VERSION = re.compile(r"vale version (\S+)")


def pinned_vale_version() -> str:
    data = tomllib.loads((ROOT / "mise.toml").read_text(encoding="utf-8"))
    return str(data["tools"]["vale"])


def installed_vale_version() -> str | None:
    binary = shutil.which("vale")
    if binary is None:
        return None
    result = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, check=False
    )
    match = _VERSION.search(result.stdout)
    return match.group(1) if match else None


def pytest_sessionstart(session: pytest.Session) -> None:
    installed = installed_vale_version()
    pinned = pinned_vale_version()
    if installed is None or installed == pinned:
        return
    pytest.exit(
        f"vale {installed} is on PATH but mise.toml pins {pinned}. "
        "Run the suite with `mise exec -- uv run pytest` so the pinned Vale "
        "is used.",
        returncode=1,
    )
