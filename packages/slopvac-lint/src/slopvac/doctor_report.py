"""Build the machine-readable environment report emitted by ``doctor``."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__

if TYPE_CHECKING:
    from .config import Config


def _display_path(path: Path, *, cwd: Path, home: Path) -> str:
    """Redact home-directory paths, otherwise prefer project-relative paths."""
    absolute = path.expanduser().resolve()
    try:
        return (Path("~") / absolute.relative_to(home)).as_posix()
    except ValueError:
        pass
    try:
        return absolute.relative_to(cwd).as_posix()
    except ValueError:
        return str(absolute)



def _redact_home(value: str, home: Path) -> str:
    """Replace home paths embedded in error messages as well as path fields."""
    home_text = str(home)
    if value == home_text:
        return "~"
    if value.startswith(home_text + "/"):
        return "~" + value[len(home_text) :]
    return value.replace(home_text + "/", "~/")


def _steering_report(root: Path, home: Path) -> list[dict[str, object]]:
    from .steering import (
        SteeringError,
        harness_path,
        harnesses,
        managed_block_state,
        skill_path,
        skill_state,
    )

    entries: list[dict[str, object]] = []
    for harness in harnesses():
        try:
            block_path = harness_path(root, harness)
            skill_file = skill_path(root, harness)
            entries.append(
                {
                    "harness": harness,
                    "path": block_path.relative_to(root).as_posix(),
                    "block": managed_block_state(block_path),
                    "skill": skill_state(skill_file) if skill_file is not None else None,
                }
            )
        except (SteeringError, OSError) as exc:
            entries.append(
                {
                    "harness": harness,
                    "error": _redact_home(str(exc), home),
                }
            )
    return entries


def build_report(
    config_path: Path | None,
    *,
    config: Config | None,
    config_error: str | None,
    binary: str,
    root: Path,
) -> dict[str, object]:
    """Collect local system/configuration status without making network calls."""
    from . import update_notice
    from .vale_cache import cache_root
    from .vale_probe import MIN_VALE_VERSION, ValeUnavailable, require_vale, vale_version

    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    try:
        executable = require_vale(binary)
    except ValeUnavailable as exc:
        vale_path = None
        version = None
        vale_error = _redact_home(str(exc), home)
    else:
        vale_path = _display_path(Path(executable), cwd=cwd, home=home)
        version = vale_version(executable)
        if version is None:
            vale_error = f"`{binary}` did not report a usable version."
            vale_path = None
        else:
            vale_error = None

    cached_release = update_notice.cached_latest_release()
    latest_release = (
        {
            "version": cached_release[0],
            "checked_at": cached_release[1],
            "newer": update_notice.is_newer_release(cached_release[0], __version__),
        }
        if cached_release is not None
        else None
    )

    if config_path is None:
        config_display_path = None
    else:
        try:
            config_display_path = config_path.resolve().relative_to(cwd).as_posix()
        except ValueError:
            config_display_path = _display_path(config_path, cwd=cwd, home=home)
    config_data: dict[str, object] = {
        "path": config_display_path,
        "error": _redact_home(config_error, home) if config_error is not None else None,
        "profile": config.profile.value if config is not None else None,
        "mode": config.mode.value if config is not None else None,
        "guidance": config.guidance.model_dump() if config is not None else None,
    }

    return {
        "schema_version": 1,
        "ok": config is not None and vale_error is None,
        "slopvac": {
            "version": __version__,
            "location": _display_path(Path(__file__).parent, cwd=cwd, home=home),
            "python_prefix": _display_path(Path(sys.prefix), cwd=cwd, home=home),
            "upgrade_command": update_notice.upgrade_hint(),
        },
        "latest_release": latest_release,
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "vale": {
            "binary": (
                _display_path(Path(binary), cwd=cwd, home=home)
                if Path(binary).is_absolute()
                else binary
            ),
            "path": vale_path,
            "version": ".".join(map(str, version)) if version is not None else None,
            "minimum": ".".join(map(str, MIN_VALE_VERSION)),
            "supported": vale_error is None,
            "error": vale_error,
        },
        "config": config_data,
        "steering": _steering_report(root, home),
        "cache": {"root": _display_path(cache_root(), cwd=cwd, home=home)},
    }
