#!/usr/bin/env python3
"""Choose and optionally write the next release-candidate version."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_PYPI_URL = "https://pypi.org/pypi/slopvac/json"
_PACKAGE_PYPROJECT = Path("packages/slopvac-lint/pyproject.toml")
_RELEASE_CONFIG = Path("release-please-config.json")
_VERSION_RE = re.compile(r"v?([0-9]+(?:\.[0-9]+)*)(?:(a|b|rc)([0-9]*))?", re.IGNORECASE)
_STABLE_VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_MARKED_VERSION_RE = re.compile(r"(?P<prefix>[vV]?)[0-9]+\.[0-9]+\.[0-9]+")
_RELEASE_MARKER = "x-release-please-version"


def parse_version(version: str) -> tuple[tuple[int, ...], int, int] | None:
    """Parse numeric release and alpha/beta/RC parts for tuple ordering.

    This deliberately copies update_notice._parse_release's small parser instead
    of importing the package: this CI script remains standard-library only.
    """
    match = _VERSION_RE.fullmatch(version)
    if match is None:
        return None

    try:
        release = [int(part) for part in match.group(1).split(".")]
        pre_number = int(match.group(3) or 0)
    except ValueError:
        return None
    while len(release) > 1 and release[-1] == 0:
        release.pop()

    pre = match.group(2)
    pre_rank = {"a": 0, "b": 1, "rc": 2}.get(pre.lower(), 3) if pre else 3
    return tuple(release), pre_rank, pre_number


def next_rc_version(pending_version: str, releases: object) -> str:
    """Return the next RC, rejecting final or stale pending versions."""
    if not isinstance(releases, dict):
        raise TypeError("PyPI response has no release map")
    if _STABLE_VERSION_RE.fullmatch(pending_version) is None:
        raise ValueError(f"pending version must be X.Y.Z, got {pending_version!r}")

    pending = parse_version(pending_version)
    if pending is None or pending[1] != 3:
        raise ValueError(f"pending version is not a stable X.Y.Z version: {pending_version}")

    parsed_releases = [
        parsed
        for version in releases
        if isinstance(version, str)
        if (parsed := parse_version(version)) is not None
    ]
    if any(parsed == pending for parsed in parsed_releases):
        raise ValueError(f"final version {pending_version} already exists on PyPI")

    if parsed_releases:
        highest = max(parsed_releases)
        if pending <= highest:
            raise ValueError(
                f"pending version {pending_version} is not newer than the highest "
                f"PyPI version ({_format_version(highest)})"
            )

    rc_numbers = [
        parsed[2]
        for version in releases
        if isinstance(version, str)
        if (parsed := parse_version(version)) is not None
        and parsed[0] == pending[0]
        and parsed[1] == 2
    ]
    next_number = max(rc_numbers, default=0) + 1
    return f"{pending_version}rc{next_number}"


def _format_version(parsed: tuple[tuple[int, ...], int, int]) -> str:
    release, pre_rank, pre_number = parsed
    suffix = {0: "a", 1: "b", 2: "rc"}.get(pre_rank, "")
    return ".".join(map(str, release)) + suffix + (str(pre_number) if suffix else "")


def rewrite_marked_versions(text: str, version: str) -> str:
    """Replace version tokens on release-please marker lines, purely."""
    if _STABLE_VERSION_RE.fullmatch(version) is None and re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+", version
    ) is None:
        raise ValueError(f"replacement must be X.Y.Z or X.Y.ZrcN, got {version!r}")

    rewritten: list[str] = []
    replacements = 0
    for line in text.splitlines(keepends=True):
        if _RELEASE_MARKER not in line:
            rewritten.append(line)
            continue
        line, count = _MARKED_VERSION_RE.subn(
            lambda match: f"{match.group('prefix')}{version}", line
        )
        if count == 0:
            raise ValueError("release-please marker line has no version token")
        replacements += count
        rewritten.append(line)

    if replacements == 0:
        raise ValueError("file has no x-release-please-version marker")
    return "".join(rewritten)


def release_version_files(root: Path) -> tuple[Path, ...]:
    """Return configured release-please extra-files plus the package metadata."""
    config_path = root / _RELEASE_CONFIG
    config = json.loads(config_path.read_text(encoding="utf-8"))
    packages = config.get("packages") if isinstance(config, dict) else None
    package = packages.get(".") if isinstance(packages, dict) else None
    extra_files = package.get("extra-files") if isinstance(package, dict) else None
    if not isinstance(extra_files, list) or not all(
        isinstance(path, str) for path in extra_files
    ):
        raise TypeError(
            "release-please-config.json packages['.'].extra-files must be a string list"
        )

    root = root.resolve()
    files: list[Path] = []
    for relative in (_PACKAGE_PYPROJECT.as_posix(), *extra_files):
        path = Path(relative)
        if path.is_absolute():
            raise ValueError(f"release-please extra-file must be relative: {relative}")
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"release-please extra-file escapes workspace: {relative}")
        if resolved not in files:
            files.append(resolved)
    return tuple(files)


def rewrite_version_files(root: Path, version: str) -> None:
    """Rewrite every version-carrying release file in the CI workspace."""
    updates: list[tuple[Path, str]] = []
    for path in release_version_files(root):
        current = path.read_text(encoding="utf-8")
        updates.append((path, rewrite_marked_versions(current, version)))
    for path, content in updates:
        path.write_text(content, encoding="utf-8")


def pending_version(root: Path) -> str:
    """Read and validate the package's stable version from its pyproject."""
    path = root / _PACKAGE_PYPROJECT
    metadata = tomllib.loads(path.read_text(encoding="utf-8"))
    project = metadata.get("project")
    version = project.get("version") if isinstance(project, dict) else None
    if not isinstance(version, str) or _STABLE_VERSION_RE.fullmatch(version) is None:
        raise ValueError(f"{path} must declare a pending stable X.Y.Z version")
    return version


def fetch_pypi_releases() -> dict[str, object]:
    request = Request(_PYPI_URL, headers={"Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("releases"), dict):
        raise TypeError("PyPI response has no release map")
    return payload["releases"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rewrite",
        action="store_true",
        help="rewrite release-please version files in the workspace to the selected RC",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)

    try:
        stable_version = pending_version(args.root)
        version = next_rc_version(stable_version, fetch_pypi_releases())
        if args.rewrite:
            rewrite_version_files(args.root, version)
    except (HTTPError, URLError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        parser.exit(1, f"rc_version.py: error: {exc}\n")

    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
