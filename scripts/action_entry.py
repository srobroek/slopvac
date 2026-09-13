#!/usr/bin/env python3
"""Python entry points for the slopvac composite GitHub Action."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any


OUTPUT_NAMES = (
    "list",
    "score",
    "findings",
    "errors",
    "warnings",
    "suggestions",
    "documents",
    "words",
    "per-100-words",
    "passed",
    "json",
    "sarif",
)


class ActionError(RuntimeError):
    """Raised for an action failure that should produce exit code 2."""


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _write_output(values: dict[str, object]) -> None:
    output = _env("GITHUB_OUTPUT")
    if not output:
        return
    try:
        with Path(output).open("a", encoding="utf-8") as handle:
            for name in OUTPUT_NAMES:
                if name in values:
                    handle.write(f"{name}={values[name]}\n")
    except OSError as exc:
        raise ActionError(f"could not write GitHub outputs: {exc}") from exc


def _write_paths(paths_file: Path, paths: list[str]) -> None:
    paths_file.parent.mkdir(parents=True, exist_ok=True)
    paths_file.write_bytes(b"".join(path.encode() + b"\0" for path in paths))


def _read_paths(paths_file: Path) -> list[str]:
    try:
        content = paths_file.read_bytes()
    except OSError as exc:
        raise ActionError(f"could not read target path list {paths_file}: {exc}") from exc
    if not content:
        return []
    if not content.endswith(b"\0"):
        raise ActionError(f"target path list is not NUL-terminated: {paths_file}")
    return [path.decode() for path in content.rstrip(b"\0").split(b"\0") if path]


def parse_input_paths(value: str) -> list[str]:
    """Parse the action's space-separated input with shell-style quoting.

    Quoting is required for a path containing spaces (for example,
    ``"docs/release notes.md"``); shlex keeps that path as one argv item.
    """
    try:
        return shlex.split(value, comments=False, posix=True)
    except ValueError as exc:
        raise ActionError(f"invalid paths input: {exc}") from exc


def _fallback_paths(paths: list[str], *, message: str | None = None) -> list[str]:
    if message:
        print(f"::warning title=slopvac::{message}")
    return paths


def resolve_targets() -> int:
    paths_file = Path(_env("RUNNER_TEMP", tempfile.gettempdir())) / "slopvac-paths"
    changed_only = _env("CHANGED_ONLY") == "true"
    input_paths = parse_input_paths(_env("INPUT_PATHS", "."))
    base_sha = _env("BASE_SHA")

    if not changed_only:
        paths = input_paths
    elif not base_sha:
        paths = _fallback_paths(
            input_paths,
            message=(
                f"changed-files-only needs a pull_request event; linting "
                f"{_env('INPUT_PATHS')} instead"
            ),
        )
    else:
        check = subprocess.run(
            ["git", "cat-file", "-e", f"{base_sha}^{{commit}}"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if check.returncode != 0:
            print(
                "::error title=slopvac::the merge base is not in this clone. "
                "Set fetch-depth: 0 on actions/checkout, or set "
                "changed-files-only: false."
            )
            return 1
        diff = subprocess.run(
            [
                "git",
                "diff",
                "-z",
                "--name-only",
                "--diff-filter=d",
                f"{base_sha}...HEAD",
                "--",
                "*.md",
                "*.mdx",
                "*.markdown",
                "*.txt",
                "*.rst",
                "*.html",
            ],
            check=False,
            capture_output=True,
        )
        if diff.returncode != 0:
            print("::error title=slopvac::could not determine changed prose files")
            if diff.stderr:
                print(diff.stderr.decode(errors="replace"), end="")
            return 1
        paths = [path.decode() for path in diff.stdout.split(b"\0") if path]
        if not paths:
            print("::notice title=slopvac::no prose files changed")

    _write_paths(paths_file, paths)
    _write_output({"list": paths_file})
    print(*paths, sep="\n")
    return 0


def _runner_temp() -> Path | None:
    value = _env("RUNNER_TEMP")
    return Path(value) if value else None


def _temporary_path(*, suffix: str) -> Path:
    directory = _runner_temp()
    if directory:
        directory.mkdir(parents=True, exist_ok=True)
    descriptor, path = tempfile.mkstemp(
        prefix="slopvac-action-", suffix=suffix, dir=str(directory) if directory else None
    )
    os.close(descriptor)
    return Path(path)


def _command(targets: list[str]) -> list[str]:
    source = _env("SOURCE")
    version = _env("VERSION")
    command = ["uvx"]
    if source:
        spec = source
        command.append("--no-cache")
    else:
        spec = f"slopvac{version}" if version else "slopvac"
        if version and version[0].isdigit():
            spec = f"slopvac=={version}"
    command += ["--from", spec, "slopvac", "lint"]
    options = (
        ("PROFILE", "--profile"),
        ("CONFIG", "--config"),
        ("MIN_SCORE", "--min-score"),
        ("MAX_PER_100", "--max-per-100-words"),
        ("RULES_DIR", "--rules-dir"),
    )
    for variable, option in options:
        value = _env(variable)
        if value:
            command.extend((option, value))
    if _env("VALE") != "true":
        command.append("--no-vale")
    command += ["--format", "json", *targets]
    return command


def _render(command: list[str], output_format: str, destination: Path) -> int:
    # `_command` always ends with `--format json` plus targets; replace the format
    # value without rebuilding the target argv, preserving paths verbatim.
    format_command = command.copy()
    format_index = format_command.index("--format")
    format_command[format_index + 1] = output_format
    try:
        with destination.open("w", encoding="utf-8") as output:
            result = subprocess.run(
                format_command,
                check=False,
                stdout=output,
                stderr=subprocess.PIPE,
                text=True,
            )
    except OSError as exc:
        print(
            f"::error title=slopvac::the {output_format} report could not be produced: {exc}"
        )
        raise ActionError(f"{output_format} report failed") from exc
    if result.returncode >= 2 or destination.stat().st_size == 0:
        print(
            f"::error title=slopvac::the {output_format} report could not be produced "
            f"(exit {result.returncode})."
        )
        if result.stderr:
            print(result.stderr, end="")
        raise ActionError(f"{output_format} report failed")
    return result.returncode



def _summary_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    verdict = "PASS" if summary["passed"] else "FAIL"
    lines = [f"## slopvac: {verdict} - score {summary['score']}/100", ""]
    lines.append(
        f"{summary['findings']} finding(s) across {summary['documents']} file(s), "
        f"{summary['words']} words = {summary['per_100_words']:.2f} per 100 words"
    )
    lines.append("")
    rows = [category for category in summary["categories"] if category["findings"]]
    if rows:
        lines.extend(
            [
                "| category | findings | errors | warnings | per 100 words | score |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| {row['category']} | {row['findings']} | {row['errors']} | "
            f"{row['warnings']} | {row['per_100_words']:.2f} | {row['score']:.0f} |"
            for row in rows
        )
        lines.append("")
    for document in data["documents"]:
        lines.extend(
            f"- `{document['path']}`: {reason}"
            for reason in document.get("failure_reasons", [])
        )
        lines.extend(
            f"- UNCHECKED `{document['path']}`: {note}"
            for note in document.get("unchecked", [])
        )
    return "\n".join(lines) + "\n"


def lint() -> int:
    paths_file = Path(_env("PATH_LIST"))
    targets = _read_paths(paths_file)
    if not targets:
        _write_output(
            {
                "score": 100,
                "findings": 0,
                "errors": 0,
                "warnings": 0,
                "suggestions": 0,
                "documents": 0,
                "words": 0,
                "per-100-words": 0,
                "passed": "true",
                "json": "",
                "sarif": "",
            }
        )
        return 0

    command = _command(targets)
    json_path = _temporary_path(suffix=".json")
    status = _render(command, "json", json_path)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        summary = data["summary"]
        values: dict[str, object] = {
            "score": summary["score"],
            "findings": summary["findings"],
            "errors": summary["errors"],
            "warnings": summary["warnings"],
            "suggestions": summary["suggestions"],
            "documents": summary["documents"],
            "words": summary["words"],
            "per-100-words": summary["per_100_words"],
            "passed": "true" if summary["passed"] else "false",
            "json": json_path,
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print("::error title=slopvac::the JSON report could not be read. Prose was NOT checked.")
        raise ActionError("invalid JSON report") from exc

    _write_output(values)
    try:
        with Path(_env("GITHUB_STEP_SUMMARY", os.devnull)).open(
            "a", encoding="utf-8"
        ) as summary_file:
            summary_file.write(_summary_markdown(data))
    except OSError as exc:
        print("::error title=slopvac::the step summary could not be written from the report.")
        raise ActionError("could not write GitHub step summary") from exc

    if _env("ANNOTATE") == "true":
        github_path = _temporary_path(suffix=".github")
        try:
            _render(command, "github", github_path)
            print(github_path.read_text(encoding="utf-8"), end="")
        finally:
            github_path.unlink(missing_ok=True)

    if _env("SARIF") == "true":
        sarif_path = Path(_env("SARIF_FILE", "slopvac.sarif"))
        _render(command, "sarif", sarif_path)
        print(f"wrote {sarif_path}")
        _write_output({"sarif": sarif_path})
    else:
        _write_output({"sarif": ""})

    return status if _env("FAIL_ON_FINDINGS") == "true" else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("resolve-targets", help="resolve action target paths")
    subparsers.add_parser("lint", help="run slopvac and publish action outputs")
    args = parser.parse_args(argv)
    try:
        return resolve_targets() if args.command == "resolve-targets" else lint()
    except ActionError as exc:
        print(f"::error title=slopvac::{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
