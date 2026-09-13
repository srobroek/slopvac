#!/usr/bin/env python3
"""Download and install a pinned Vale release without external Unix tools."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen


RELEASE_BASE = "https://github.com/vale-cli/vale/releases/download"


class InstallError(RuntimeError):
    """Raised when a Vale release cannot be installed safely."""


def _asset_name(version: str) -> str:
    system = platform.system()
    machine = platform.machine().lower()
    systems = {"Linux": "Linux", "Darwin": "macOS"}
    system_name = systems.get(system)
    if system_name is None:
        raise InstallError(f"unsupported platform: {system}")

    if machine in {"x86_64", "amd64"}:
        architecture = "64-bit"
    elif machine in {"arm64", "aarch64"}:
        architecture = "arm64"
    else:
        raise InstallError(f"unsupported architecture: {platform.machine()}")
    return f"vale_{version}_{system_name}_{architecture}.tar.gz"


def _download(url: str, destination: Path) -> None:
    try:
        with urlopen(url, timeout=60) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
    except OSError as exc:
        raise InstallError(f"download failed for {url}: {exc}") from exc


def _checksum(checksums: Path, archive_name: str) -> str:
    for line in checksums.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[-1].lstrip("*") == archive_name:
            return fields[0]
    raise InstallError(f"checksum file has no entry for {archive_name}")


def _verify_checksum(archive: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with archive.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise InstallError(
            f"checksum mismatch for {archive.name}: expected {expected}, got {actual}"
        )


def _install_binary(archive: Path, prefix: Path) -> Path:
    target = prefix / "vale"
    prefix.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, mode="r:gz") as package:
        try:
            member = package.getmember("vale")
        except KeyError as exc:
            raise InstallError("release archive has no vale member") from exc
        if not member.isfile() or member.name != "vale":
            raise InstallError("release archive's vale member is not a regular file")
        source = package.extractfile(member)
        if source is None:  # pragma: no cover - tarfile contract guard
            raise InstallError("could not read vale member from release archive")
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            with source, temporary.open("wb") as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    output.write(chunk)
            temporary.chmod(0o755)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def _verify_version(binary: Path) -> str:
    try:
        result = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise InstallError(f"could not execute {binary}: {exc}") from exc
    output = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        raise InstallError(f"{binary} --version failed ({result.returncode}): {output}")
    if not output:
        raise InstallError(f"{binary} --version produced no output")
    return output


def install(version: str, prefix: Path) -> tuple[Path, str]:
    archive_name = _asset_name(version)
    base = f"{RELEASE_BASE}/v{version}"
    with tempfile.TemporaryDirectory(prefix="slopvac-vale-") as temporary:
        directory = Path(temporary)
        archive = directory / archive_name
        checksums = directory / f"vale_{version}_checksums.txt"
        _download(f"{base}/{archive_name}", archive)
        _download(f"{base}/{checksums.name}", checksums)
        _verify_checksum(archive, _checksum(checksums, archive_name))
        binary = _install_binary(archive, prefix)
    return binary, _verify_version(binary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Vale release version, for example 3.15.2")
    parser.add_argument(
        "--prefix",
        type=Path,
        default=Path("/usr/local/bin"),
        help="directory in which to install vale (default: /usr/local/bin)",
    )
    args = parser.parse_args()
    try:
        binary, version = install(args.version, args.prefix.expanduser())
    except InstallError as exc:
        parser.error(str(exc))
    print(f"installed {binary}")
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
