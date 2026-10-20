"""Ask the `vale` binary what it accepts and what it resolved.

Vale's own compiler is the authority on its rule syntax, so a compiled payload is
validated by handing it to Vale rather than by inspecting it. This module owns
every subprocess call the compiler makes, and `ValeUnavailable`, the one error
that means the binary itself cannot be used. Separate from `compile_vale` so the
payload translation stays a pure function of the ruleset.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from functools import cache
from pathlib import Path

from packaging.version import Version


class ValeUnavailable(Exception):
    """Vale is needed to validate a compiled rule and is not usable."""


# The oldest Vale the compiled styles are known to load and match under. The
# README documents it; before this probe nothing checked it, so a 3.14 binary
# reused a tree compiled under 3.21 and reported findings with no unchecked note.
# 3.18 is the floor because it is the first release that parses MDX natively;
# earlier ones fail every MDX file unless the external mdx2vast is installed,
# which slopvac does not support. In code-comment mode 3.15 also reported every
# line after an empty comment line one line late, so a finding could land inside
# a suppression and be lost.
MIN_VALE_VERSION = (3, 18, 0)


def require_vale(binary: str = "vale") -> str:
    """Resolve a supported Vale executable, with actionable prerequisite errors."""
    resolved = shutil.which(binary)
    floor = Version(".".join(map(str, MIN_VALE_VERSION)))
    if resolved is None:
        raise ValeUnavailable(
            f"`{binary}` is not on PATH. Vale {floor} or later is required; "
            "install Vale (https://vale.sh) and rerun `slopvac doctor`."
        )
    version = vale_version(resolved)
    if version is None:
        raise ValeUnavailable(
            f"`{binary}` exists at {resolved} but did not report a usable "
            f"version. Vale {floor} or later is required. Check that the "
            "executable works with `--version`."
        )
    found = Version(".".join(map(str, version)))
    if found < floor:
        raise ValeUnavailable(
            f"`{binary}` reports {found}; Vale {floor} or later is required. "
            "Upgrade Vale and rerun `slopvac doctor`."
        )
    return resolved


def vale_version(binary: str = "vale") -> tuple[int, int, int] | None:
    """The installed Vale's semantic version, or None when it cannot be read.

    `vale --version` prints `vale version 3.21.0`; only the first three integers
    are read, so a pre-release suffix does not break the parse.

    One answer per binary per process. The compiler keys its tree on the version
    and the runner compares it with the floor, so one Vale lint needs it twice.
    The memo key is the binary's path, inode, size, and mtime, so a binary that
    changes mid-process gets a fresh `vale --version`.
    """
    resolved = shutil.which(binary)
    if resolved is None:
        return None
    try:
        stat = os.stat(resolved)
    except OSError:
        return _read_version(resolved)
    return _version_of(resolved, stat.st_ino, stat.st_size, stat.st_mtime_ns)


@cache
def _version_of(
    resolved: str, inode: int, size: int, mtime_ns: int
) -> tuple[int, int, int] | None:
    """`_read_version`, memoised. The identity arguments exist only as the key."""
    return _read_version(resolved)


def _read_version(resolved: str) -> tuple[int, int, int] | None:
    try:
        completed = subprocess.run(
            [resolved, "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
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


def rule_yaml(payload: dict) -> str:
    """One Vale rule file's text.

    The probe and the compiler both write through here, so the probe validates the
    same text the compiled tree holds. libyaml's emitter when PyYAML has it: it is
    about eight times faster over the shipped rules, and it differs from the pure
    emitter only in quoting, such as escaping astral-plane characters inside a
    double-quoted scalar, so every rule loads to the same values.
    """
    import yaml

    dumper = getattr(yaml, "CSafeDumper", yaml.SafeDumper)
    return yaml.dump(
        payload, Dumper=dumper, sort_keys=False, allow_unicode=True, width=10**6
    )


def probe_payloads(payloads: dict[str, dict], binary: str) -> dict[str, str]:
    """Which payloads Vale refuses, mapped to the reason it gave.

    Vale's own compiler is the authority on what Vale accepts, so each payload is
    handed to it rather than inspected for constructs a table thinks are
    unsupported. That inspection was wrong twice: RE2's documented lack of
    lookbehind does not apply, because Vale rewrites the pattern before RE2 sees
    it, and `(?<=the )gizmo` fires.

    ALL AT ONCE, THEN SPLIT. One bad rule in a style directory makes Vale abort
    the whole run, so a batch tells whether every rule loaded but not which ones
    failed. The probe therefore runs the whole set once and splits only a failing
    batch, down to single rules. Vale reads the files in name order and names the
    first one it refused, so the split puts that rule alone, between the rules
    before and after it. When Vale names no file of the batch, the split is in
    halves. Either way, the probe judges a single rule exactly as it judged every
    rule when it ran them one by one, and it runs the parts in payload order. The
    verdicts, the reasons, and their order are therefore the same. Only the number
    of runs changes. An accepted set costs one Vale run instead of one per rule:
    the per-rule runs took 2.4 s of a 3.5 s cold README lint. Each refused rule
    adds about three runs.

    That relies on one property: a batch passes only when every rule in it would
    pass alone. Each rule file loads on its own, and a refusal, a crash, or any
    stderr output from one rule fails the batch the same way. A run that cannot
    start or times out is a broken binary, not a verdict, so it raises at once
    rather than splitting into more slow runs.
    """
    rejected: dict[str, str] = {}
    if not payloads:
        return rejected
    with tempfile.TemporaryDirectory(prefix="slopvac-probe-") as temp:
        root = Path(temp)
        style = root / "styles" / "probe"
        style.mkdir(parents=True)
        config = root / ".vale.ini"
        config.write_text(
            "StylesPath = styles\nMinAlertLevel = suggestion\n[*.md]\nBasedOnStyles = probe\n",
            encoding="utf-8",
        )
        target = root / "probe.md"
        target.write_text("Probe text for rule validation.\n", encoding="utf-8")

        def run(batch: list[tuple[str, str]]) -> subprocess.CompletedProcess[str]:
            for stale in style.iterdir():
                stale.unlink()
            # A single rule keeps the name it had when every rule ran alone, so a
            # reason that quotes the file reads exactly as it did. A batch pads
            # its numbers so that Vale's name order is the payload order.
            width = len(str(len(batch) - 1))
            names = (
                ["R.yml"]
                if len(batch) == 1
                else [f"R{index:0{width}d}.yml" for index in range(len(batch))]
            )
            for name, (_, text) in zip(names, batch, strict=True):
                (style / name).write_text(text, encoding="utf-8")
            try:
                return subprocess.run(
                    [binary, f"--config={config}", "--no-exit", str(target)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ValeUnavailable(str(exc)) from exc

        # Depth first, in payload order: the batches still to run, next one last.
        pending = [[(rule_id, rule_yaml(payload)) for rule_id, payload in payloads.items()]]
        while pending:
            batch = pending.pop()
            completed = run(batch)
            if len(batch) == 1:
                reason = _refusal(completed)
                if reason is not None:
                    rejected[batch[0][0]] = reason
                continue
            try:
                if _refusal(completed) is None:
                    continue
            except ValeUnavailable:
                pass  # The batch splits below. Only a single rule can raise.
            named = _BATCH_FILE.search(completed.stderr)
            blamed = int(named.group(1)) if named else len(batch)
            if blamed < len(batch):
                parts = [batch[:blamed], batch[blamed : blamed + 1], batch[blamed + 1 :]]
            else:
                parts = [batch[: len(batch) // 2], batch[len(batch) // 2 :]]
            pending.extend(part for part in reversed(parts) if part)
    return rejected


# The file a batch run names in its error, as `.../probe/R07.yml:5:3`.
_BATCH_FILE = re.compile(r"probe[/\\]R(\d+)\.yml")


def _refusal(completed: subprocess.CompletedProcess[str]) -> str | None:
    """Why Vale refused the probed rules, or None when it loaded every one.

    Raises `ValeUnavailable` when Vale failed without refusing a rule.
    """
    output = completed.stdout + completed.stderr
    if "E201" in output or "error parsing regexp" in output:
        for line in output.splitlines():
            if "error parsing regexp" in line:
                return line.strip()
        return "Vale rejected the pattern"
    if completed.returncode != 0 or completed.stderr.strip():
        raise ValeUnavailable(
            f"Vale validation failed ({completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    return None


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
