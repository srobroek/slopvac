"""Vale sub-gate.

Vale stays in the pipeline for one reason: the upstream `tbhb/vale-ai-tells`
package is 76 maintained rules we do not want to fork, and Vale's syntax-aware
parsers lint comments and docstrings in source files while skipping identifiers
and string literals -- which this project measured and depends on.

Our own styles are converted to the native ruleset, so a rule is not run twice.
This module runs only the styles Vale still owns.

MISSING TOOLS ARE LOUD. An absent binary, an unsynced style, or a config that
resolves nothing all make Vale report a clean file and exit 0, which is
indistinguishable from a pass. Every such case returns an `unchecked` note that
the caller surfaces in the report rather than swallowing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config, Severity
from .model import Finding

# Styles Vale keeps. Ours moved to the native engine.
VALE_OWNED = ("ai-tells",)

SEVERITY_MAP = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "suggestion": Severity.SUGGESTION,
}


@dataclass
class ValeResult:
    by_path: dict[str, list[Finding]] = field(default_factory=dict)
    unchecked: list[str] = field(default_factory=list)

    def findings_for(self, path: str) -> list[Finding]:
        # Vale normalizes paths; try the exact string then the resolved form.
        if path in self.by_path:
            return self.by_path[path]
        resolved = str(Path(path).resolve())
        return self.by_path.get(resolved, [])


def _styles_synced(config_path: Path, styles: list[str]) -> list[str]:
    """Which requested styles are missing from the resolved StylesPath.

    Checked per style rather than by directory existence: a sync that fails
    partway leaves what it already fetched, and Vale reports every file clean for
    a style it cannot resolve, so a partial sync looks exactly like a pass.
    """
    styles_path = Path("styles")
    for line in config_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("StylesPath"):
            _, _, value = line.partition("=")
            styles_path = Path(value.strip())
            break
    if not styles_path.is_absolute():
        styles_path = config_path.parent / styles_path
    return [s for s in styles if not (styles_path / s).is_dir()]


def run_vale(paths: list[Path], config: Config) -> ValeResult:
    """Run Vale over `paths` and map its JSON onto our Finding type."""
    result = ValeResult()
    settings = config.vale

    binary = shutil.which(settings.binary)
    if binary is None:
        result.unchecked.append(
            f"`{settings.binary}` is not on PATH, so the upstream ai-tells rules "
            f"did NOT run. Install it (`mise use -g vale` or `brew install vale`) "
            f"or set `vale.enabled = false` to silence this."
        )
        return result

    config_path = settings.config
    if config_path is None:
        # Prefer a project .vale.ini; fall back to the packaged one.
        root = config.root or Path.cwd()
        candidate = root / ".vale.ini"
        if candidate.is_file():
            config_path = candidate
        else:
            from importlib import resources

            try:
                packaged = resources.files("slopvac_lint") / "vale" / ".vale.ini"
                config_path = Path(str(packaged))
            except (ModuleNotFoundError, FileNotFoundError):
                config_path = None

    if config_path is None or not Path(config_path).is_file():
        result.unchecked.append(
            "no .vale.ini was found, so the upstream ai-tells rules did NOT run. "
            "Run `slopvac-lint init --vale` or point `vale.config` at one."
        )
        return result

    config_path = Path(config_path)
    styles = settings.styles or list(VALE_OWNED)
    missing = _styles_synced(config_path, styles)
    if missing:
        result.unchecked.append(
            f"Vale styles are not synced ({' '.join(missing)}), so those rules did "
            f"NOT run -- an unsynced style reports every file as clean. "
            f"Run: vale --config='{config_path}' sync"
        )
        return result

    try:
        completed = subprocess.run(
            [
                binary,
                f"--config={config_path}",
                "--output=JSON",
                "--no-exit",
                *[str(p) for p in paths],
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        result.unchecked.append("Vale timed out after 120s; those rules did NOT run.")
        return result
    except OSError as exc:
        result.unchecked.append(f"Vale could not be run ({exc}); those rules did NOT run.")
        return result

    raw = completed.stdout.strip()
    if not raw:
        return result
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        result.unchecked.append(
            "Vale output could not be parsed; its rules did NOT contribute findings."
        )
        return result

    for path, alerts in data.items():
        for alert in alerts:
            check = alert.get("Check", "?")
            style = check.split(".", 1)[0]
            # Only keep what Vale still owns; ours run natively and would double.
            if style not in styles:
                continue
            result.by_path.setdefault(path, []).append(
                Finding(
                    path=path,
                    line=alert.get("Line", 1),
                    column=(alert.get("Span") or [1])[0],
                    rule_id=check,
                    category=f"vale-{style}",
                    severity=SEVERITY_MAP.get(
                        alert.get("Severity", "error"), Severity.ERROR
                    ),
                    message=alert.get("Message", "").strip(),
                    matched_text=alert.get("Match", ""),
                )
            )
    return result
