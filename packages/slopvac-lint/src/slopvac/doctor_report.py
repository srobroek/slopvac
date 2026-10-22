"""Build the machine-readable environment report emitted by ``doctor``."""

from __future__ import annotations

import platform
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from . import __version__

if TYPE_CHECKING:
    from .config import Config


_PATH_RE = re.compile(
    r"(?<![\w:/\\\\])"
    r"(?:[A-Z]:[\\\\/][^\s'\"`<>,;)}]+|"
    r"\\\\[^\s'\"`<>,;)}]+|"
    r"~[\\\\/][^\s'\"`<>,;)}]+|"
    r"/(?!/)[^\s'\"`<>,;)}]+|"
    r"\.\.?[\\\\/][\w.@+-]+(?:[\\\\/][\w.@+-]+)*|"
    r"[\w.@+-]+(?:[\\\\/][\w.@+-]+){2,}|"
    r"(?:[\w.@+-]+[\\\\/])?[\w.@+-]+\.(?:toml|py|json|ya?ml|txt|md|ini|cfg|conf|sh|exe|dll|dylib))",
    re.IGNORECASE,
)
_QUOTED_PATH_RE = re.compile(
    r"""(?ix)(['"`])((?:[A-Z]:[\\/]|\\\\|/(?!/)|~[\\/]|\.{1,2}[\\/])[^'"`]*)\1"""
)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_PYDANTIC_INPUT_VALUE_RE = re.compile(r"(input_value=).*?(?=,\s*input_type=)", re.DOTALL)


def _redact_error(
    value: str,
    *,
    paths: tuple[Path | str | None, ...] = (),
    names: tuple[str, ...] = (),
) -> str:
    """Remove filesystem paths and user values echoed by validation errors."""
    urls: list[str] = []
    for match in _URL_RE.finditer(value):
        urls.append(match.group())
    url_map = {url: f"\x00{index}\x00" for index, url in enumerate(urls)}
    value = _URL_RE.sub(lambda match: url_map[match.group()], value)
    for path in sorted(
        (str(path) for path in paths if path is not None and str(path)),
        key=len,
        reverse=True,
    ):
        value = value.replace(path, "<path>")
    for name in sorted((name for name in names if name), key=len, reverse=True):
        value = value.replace(name, "<path>")
    value = _QUOTED_PATH_RE.sub("<path>", value)
    value = _PYDANTIC_INPUT_VALUE_RE.sub(r"\1<redacted>", value)
    value = _PATH_RE.sub("<path>", value)
    for index, url in enumerate(urls):
        value = value.replace(f"\x00{index}\x00", url)
    return value


def _is_path(value: str) -> bool:
    """Whether a binary selection is a path rather than a bare command name."""
    return "/" in value or "\\" in value or re.match(r"^[A-Za-z]:", value) is not None


def _steering_report(root: Path, *, skill_wanted: bool) -> list[dict[str, object]]:
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
                    "block": managed_block_state(block_path),
                    "skill": (
                        skill_state(skill_file, wanted=skill_wanted)
                        if skill_file is not None
                        else None
                    ),
                }
            )
        except (SteeringError, OSError) as exc:
            entries.append(
                {
                    "harness": harness,
                    "error": _redact_error(
                        str(exc),
                        paths=(root, root.resolve(), Path.home(), Path.home().resolve()),
                    ),
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
    from .config import CONFIG_NAMES, PYPROJECT
    from .vale_probe import (
        MIN_VALE_VERSION,
        ValeUnavailable,
        require_vale,
        vale_version,
    )

    try:
        executable = require_vale(binary)
    except ValeUnavailable as exc:
        executable = shutil.which(binary)
        version = vale_version(executable) if executable is not None else None
        vale_error = _redact_error(
            str(exc),
            paths=(
                binary if _is_path(binary) else None,
                Path(binary).resolve() if _is_path(binary) else None,
                Path.home(),
                Path.home().resolve(),
            ),
            names=(Path(binary).name,) if _is_path(binary) else (),
        )
    else:
        version = vale_version(executable)
        vale_error = (
            f"`{Path(binary).name if _is_path(binary) else binary}` did not report "
            "a usable version."
            if version is None
            else None
        )

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
        config_file = None
    elif config_path.name in (*CONFIG_NAMES, PYPROJECT):
        config_file = config_path.name
    else:
        config_file = "<custom>"
    config_data: dict[str, object] = {
        "file": config_file,
        "error": (
            _redact_error(
                config_error,
                paths=(config_path, Path.home(), Path.home().resolve()),
                names=(
                    config_path.name
                    if config_path is not None and config_file == "<custom>"
                    else "",
                ),
            )
            if config_error is not None
            else None
        ),
        "profile": config.profile.value if config is not None else None,
        "mode": config.mode.value if config is not None else None,
        "guidance": config.guidance.model_dump() if config is not None else None,
    }

    return {
        "schema_version": 1,
        "ok": config is not None and vale_error is None,
        "slopvac": {
            "version": __version__,
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
            "binary": "<path>" if _is_path(binary) else binary,
            "found": executable is not None,
            "version": ".".join(map(str, version)) if version is not None else None,
            "minimum": ".".join(map(str, MIN_VALE_VERSION)),
            "supported": vale_error is None,
            "error": vale_error,
        },
        "config": config_data,
        "steering": _steering_report(
            root,
            skill_wanted=config.guidance.enabled if config is not None else True,
        ),
    }
