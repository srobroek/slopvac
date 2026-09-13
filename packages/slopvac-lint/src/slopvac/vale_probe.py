"""Ask the `vale` binary what it accepts and what it resolved.

Vale's own compiler is the authority on its rule syntax, so a compiled payload is
validated by handing it to Vale rather than by inspecting it. This module owns
every subprocess call the compiler makes, and `ValeUnavailable`, the one error
that means the binary itself cannot be used. Separate from `compile_vale` so the
payload translation stays a pure function of the ruleset.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml


class ValeUnavailable(Exception):
    """Vale is needed to validate a compiled rule and is not usable."""


# The oldest Vale the compiled styles are known to load and match under. The
# README documents it; before this probe nothing checked it, so a 3.14 binary
# reused a tree compiled under 3.21 and reported findings with no unchecked note.
MIN_VALE_VERSION = (3, 15, 0)


def vale_version(binary: str = "vale") -> tuple[int, int, int] | None:
    """The installed Vale's semantic version, or None when it cannot be read.

    `vale --version` prints `vale version 3.21.0`; only the first three integers
    are read, so a pre-release suffix does not break the parse.
    """
    resolved = shutil.which(binary)
    if resolved is None:
        return None
    try:
        completed = subprocess.run(
            [resolved, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", completed.stdout + completed.stderr)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def rst_converter(
    binary_names: tuple[str, ...] = ("rst2html", "rst2html.py"),
) -> str | None:
    """Return the first docutils RST converter on PATH, if one is usable."""
    for name in binary_names:
        resolved = shutil.which(name)
        if resolved is not None:
            return resolved
    return None


def probe_payloads(payloads: dict[str, dict], binary: str) -> dict[str, str]:
    """Which payloads Vale refuses, mapped to the reason it gave.

    Vale's own compiler is the authority on what Vale accepts, so each payload is
    handed to it rather than inspected for constructs a table thinks are
    unsupported. That inspection was wrong twice: RE2's documented lack of
    lookbehind does not apply, because Vale rewrites the pattern before RE2 sees
    it, and `(?<=the )gizmo` fires.

    One rule at a time, because a style directory holding one bad rule makes Vale
    abort the whole run -- so a batch probe reports every rule as broken.
    """
    rejected: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="slopvac-probe-") as temp:
        root = Path(temp)
        style = root / "styles" / "probe"
        style.mkdir(parents=True)
        (root / ".vale.ini").write_text(
            "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = probe\n",
            encoding="utf-8",
        )
        target = root / "probe.md"
        target.write_text("Probe text for rule validation.\n", encoding="utf-8")

        for rule_id, payload in payloads.items():
            for stale in style.iterdir():
                stale.unlink()
            (style / "R.yml").write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=10**6),
                encoding="utf-8",
            )
            try:
                completed = subprocess.run(
                    [binary, f"--config={root / '.vale.ini'}", "--no-exit", str(target)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValeUnavailable(str(exc)) from exc
            output = completed.stdout + completed.stderr
            if "E201" in output or "error parsing regexp" in output:
                reason = "Vale rejected the pattern"
                for line in output.splitlines():
                    if "error parsing regexp" in line:
                        reason = line.strip()
                        break
                rejected[rule_id] = reason
            elif completed.returncode != 0 or completed.stderr.strip():
                raise ValeUnavailable(
                    f"Vale validation failed ({completed.returncode}): "
                    f"{completed.stderr.strip()}"
                )
    return rejected


def resolved_checks(config_path: Path, binary: str = "vale") -> set[str] | None:
    """The rules Vale actually resolved, from `vale ls-config`.

    Used to detect the silent case the brief names: the compiler wrote N rules
    and Vale resolved fewer. Returns None when Vale cannot be asked, which the
    caller reports as unchecked rather than treating as agreement.
    """
    resolved = shutil.which(binary)
    if resolved is None:
        return None
    try:
        completed = subprocess.run(
            [resolved, f"--config={config_path}", "ls-config"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0 or completed.stderr.strip():
        return None
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    checks = data.get("Checks") if isinstance(data, dict) else None
    if not isinstance(checks, list) or any(
        not isinstance(check, str) for check in checks
    ):
        return None
    return set(checks)
