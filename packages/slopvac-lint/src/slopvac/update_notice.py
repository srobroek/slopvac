"""Non-blocking, best-effort PyPI release notices for interactive CLI runs."""

from __future__ import annotations

import fcntl
import json
import os
import re
import sys
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

from . import __version__
from .vale_cache import cache_root

_CHECK_INTERVAL = timedelta(hours=24)
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
    request = Request(_PYPI_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=2) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise TypeError("PyPI response is not an object")
    return _latest_stable_version(payload.get("releases"))


def _cache_path() -> Path:
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


def _refresh_cache(path: Path) -> None:
    """Fetch under a non-blocking cross-process lock; all errors stay silent."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with (path.parent / ".update-check.lock").open("a+") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return

            now = datetime.now(UTC)
            cache = _read_cache(path)
            if _is_fresh(cache, now):
                return
            previous = cache.get("latest_version") if cache else None
            previous = previous if isinstance(previous, str) else None
            # Record the attempt first: if the process exits mid-request, the next
            # run waits a full interval instead of retrying on every command.
            _write_cache(path, {"checked_at": now.isoformat(), "latest_version": previous})
            try:
                latest = _fetch_latest_version()
            except Exception:
                return
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


def start_refresh(*, stderr_isatty: bool | None = None) -> threading.Thread | None:
    """Refresh a stale cache in a daemon thread that runs alongside the command.

    Started before the command so a slow network overlaps with its work instead
    of delaying exit; `show_update_notice` waits for it only briefly.
    """
    try:
        if not _enabled(stderr_isatty):
            return None
        path = _cache_path()
        if _is_fresh(_read_cache(path), datetime.now(UTC)):
            return None
        thread = threading.Thread(
            target=_refresh_cache, args=(path,), name="slopvac-update-check", daemon=True
        )
        thread.start()
        return thread
    except Exception:
        return None


def show_update_notice(
    refresh: threading.Thread | None = None,
    *,
    stderr_isatty: bool | None = None,
    command: str | None = None,
    output_format: str | None = None,
    output_to_file: bool = False,
    wait_seconds: float = 1.0,
) -> None:
    """Print one stderr line when the cached latest release is newer."""
    try:
        if refresh is not None:
            refresh.join(timeout=wait_seconds)
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
