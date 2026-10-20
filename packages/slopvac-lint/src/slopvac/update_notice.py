"""Best-effort PyPI release notices for interactive CLI runs.

The notice reads one cached file and never touches the network. When that file is
older than the check interval, `start_refresh` spawns a detached process that asks
PyPI and rewrites it, so a newer release shows on a later run. The command never
waits for PyPI, and never imports an HTTP client.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import __version__

_CHECK_INTERVAL = timedelta(hours=24)
# Nobody waits for the detached refresh, so it bounds itself. `urlopen`'s timeout
# covers each socket operation but not name resolution.
_REFRESH_TIMEOUT_SECONDS = 10
_CACHE_NAME = "update-check.json"
_PYPI_URL = "https://pypi.org/pypi/slopvac/json"
_VERSION_RE = re.compile(r"v?([0-9]+(?:\.[0-9]+)*)(?:(a|b|rc)([0-9]*))?", re.IGNORECASE)


def _parse_release(version: str) -> tuple[tuple[int, ...], int, int] | None:
    """Parse the release and optional a/b/rc segment used for ordering."""
    match = _VERSION_RE.fullmatch(version)
    if match is None:
        return None

    try:
        release = [int(part) for part in match.group(1).split(".")]
    except ValueError:
        return None
    while len(release) > 1 and release[-1] == 0:
        release.pop()

    pre = match.group(2)
    pre_rank = {"a": 0, "b": 1, "rc": 2}.get(pre.lower(), 3) if pre else 3
    try:
        pre_number = int(match.group(3) or 0)
    except ValueError:
        return None
    return tuple(release), pre_rank, pre_number


def is_newer_release(candidate: str, current: str) -> bool:
    """Return true only when both versions parse and candidate sorts later."""
    candidate_version = _parse_release(candidate)
    current_version = _parse_release(current)
    return (
        candidate_version is not None
        and current_version is not None
        and candidate_version > current_version
    )


def _latest_stable_version(releases: object) -> str:
    if not isinstance(releases, dict):
        raise TypeError("PyPI response has no release map")

    versions: list[tuple[tuple[tuple[int, ...], int, int], str]] = []
    for version, files in releases.items():
        parsed = _parse_release(version) if isinstance(version, str) else None
        if parsed is None or parsed[1] != 3:
            continue
        if isinstance(files, list) and files and all(
            isinstance(file, dict) and file.get("yanked", False) for file in files
        ):
            continue
        versions.append((parsed, version))

    if not versions:
        raise ValueError("PyPI response has no stable release")
    return max(versions)[1]


def _fetch_latest_version() -> str:
    from urllib.request import Request, urlopen

    request = Request(_PYPI_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=2) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise TypeError("PyPI response is not an object")
    return _latest_stable_version(payload.get("releases"))


def _cache_path() -> Path:
    from .vale_cache import cache_root

    return cache_root() / _CACHE_NAME


def _read_cache(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _checked_at(cache: dict[str, object] | None) -> datetime | None:
    checked_at_raw = cache.get("checked_at") if cache else None
    if not isinstance(checked_at_raw, str):
        return None
    try:
        checked_at = datetime.fromisoformat(checked_at_raw)
    except ValueError:
        return None
    if checked_at.tzinfo is None:
        return None
    return checked_at.astimezone(UTC)


def _is_fresh(cache: dict[str, object] | None, now: datetime) -> bool:
    checked_at = _checked_at(cache)
    if checked_at is None:
        return False
    age = now - checked_at
    return timedelta(0) <= age < _CHECK_INTERVAL


def _write_cache(path: Path, cache: dict[str, object]) -> None:
    """Replace the cache in one step, so a reader sees the old file or the new one."""
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".slopvac-update-",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            json.dump(cache, temporary, separators=(",", ":"))
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass


def _claim_refresh(path: Path, now: datetime) -> bool:
    """Record this interval's check once, however many invocations start together.

    The claim moves `checked_at` to now and keeps the last known version, so every
    later invocation finds a fresh cache and spawns nothing, and a refresh that
    dies mid-request waits a full interval instead of retrying on every command.
    The lock makes the read and the record one step, so concurrent invocations
    spawn one refresh between them. Windows has no `fcntl`: there the notice keeps
    reading the cache and no refresh is spawned.
    """
    try:
        import fcntl
    except ImportError:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    with (path.parent / ".update-check.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        cache = _read_cache(path)
        if _is_fresh(cache, now):
            return False
        previous = cache.get("latest_version") if cache else None
        _write_cache(
            path,
            {
                "checked_at": now.isoformat(),
                "latest_version": previous if isinstance(previous, str) else None,
            },
        )
    return True


def _spawn_refresh(path: Path) -> None:
    """Start `refresh_cache` in a process of its own session that outlives this one.

    `-P` keeps the working directory off its `sys.path`, so a `slopvac` directory
    in the project being linted is never imported in place of the installed one.
    """
    import subprocess

    subprocess.Popen(
        [sys.executable, "-P", "-m", "slopvac.update_notice", str(path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def refresh_cache(path: Path) -> None:
    """Ask PyPI for the latest release and cache it; all errors stay silent.

    Runs in the detached process. A failed fetch leaves the attempt that
    `_claim_refresh` recorded, so the next check waits a full interval.
    """
    try:
        latest = _fetch_latest_version()
        _write_cache(
            path,
            {"checked_at": datetime.now(UTC).isoformat(), "latest_version": latest},
        )
    except Exception:
        return


def upgrade_hint(prefix: str | Path | None = None) -> str:
    """Choose an upgrade command when the environment path identifies an installer."""
    parts = tuple(part.casefold() for part in Path(prefix or sys.prefix).parts)
    if any(
        parts[index : index + 3] == ("uv", "tools", "slopvac")
        for index in range(len(parts) - 2)
    ):
        return "uv tool upgrade slopvac"
    if any(
        parts[index : index + 3] == ("pipx", "venvs", "slopvac")
        for index in range(len(parts) - 2)
    ):
        return "pipx upgrade slopvac"
    if "archive-v0" in parts:
        return "uvx slopvac@latest"
    return "pip install -U slopvac"


def _disabled_by_environment() -> bool:
    return "CI" in os.environ or any(
        os.environ.get(name)
        for name in ("NO_UPDATE_NOTIFIER", "SLOPVAC_NO_UPDATE_CHECK", "DO_NOT_TRACK")
    )


def _enabled(stderr_isatty: bool | None) -> bool:
    if stderr_isatty is None:
        stderr_isatty = sys.stderr.isatty()
    return bool(stderr_isatty) and not _disabled_by_environment()


def start_refresh(*, stderr_isatty: bool | None = None) -> bool:
    """Spawn a detached PyPI check when the cached one is stale; return whether it did.

    Never raises and never waits: the command runs and exits at its own pace.
    """
    try:
        if not _enabled(stderr_isatty) or not sys.executable:
            return False
        path = _cache_path()
        now = datetime.now(UTC)
        if _is_fresh(_read_cache(path), now) or not _claim_refresh(path, now):
            return False
        _spawn_refresh(path)
        return True
    except Exception:
        return False


def show_update_notice(
    *,
    stderr_isatty: bool | None = None,
    command: str | None = None,
    output_format: str | None = None,
    output_to_file: bool = False,
) -> None:
    """Print one stderr line when the cached latest release is newer."""
    try:
        if (
            not _enabled(stderr_isatty)
            or command == "prime"
            or (output_format is not None and output_format != "text")
            or output_to_file
        ):
            return
        cache = _read_cache(_cache_path())
        latest = cache.get("latest_version") if cache else None
        if isinstance(latest, str) and is_newer_release(latest, __version__):
            print(
                f"slopvac {latest} is available (you have {__version__}). "
                f"Upgrade: {upgrade_hint()}",
                file=sys.stderr,
            )
    except Exception:
        return


if __name__ == "__main__":
    import signal

    signal.alarm(_REFRESH_TIMEOUT_SECONDS)
    refresh_cache(Path(sys.argv[1]))
