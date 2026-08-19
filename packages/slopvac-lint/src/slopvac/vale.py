"""Run Vale over the compiled styles and map its findings onto our types.

Vale is THE execution engine for every mechanical rule. `compile_vale` writes our
ruleset into a Vale style tree whose rule names are our own qualified ids, so a
Vale finding's `Check` is our `rule_id` with no translation step. This module
runs it and adopts the results.

OUR SEVERITY IS AUTHORITATIVE even though Vale's agrees. The generated ini
carries the level our precedence chain resolved, so Vale reports what we asked
for; re-resolving here rather than trusting the echo means a future ini bug shows
up as a mismatch in one place instead of silently changing what a gate blocks on.

MISSING TOOLS ARE LOUD, and the list of ways Vale can quietly check nothing is
the reason this module is longer than a subprocess call:

  - the binary is absent
  - the compiled config is missing
  - Vale times out
  - the output does not parse
  - Vale resolves FEWER rules than we compiled, which happens when a rule fails
    to load; Vale then reports every file clean and exits 0

Every one produces an `unchecked` note. None produces a pass.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import Severity
from .model import Finding

TIMEOUT_SECONDS = 120

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
        # Vale echoes the path it was given, which may be relative; try that
        # first, then the resolved form.
        if path in self.by_path:
            return self.by_path[path]
        return self.by_path.get(str(Path(path).resolve()), [])


def run_compiled_vale(
    paths: list[Path],
    compiled,
    severities: dict[str, Severity],
    categories: dict[str, str],
    binary: str = "vale",
) -> ValeResult:
    """Lint `paths` with the compiled styles.

    `severities` and `categories` are keyed by qualified rule id and come from
    the same resolution the compiler used, so a finding carries our level and our
    category rather than Vale's echo of them.
    """
    result = ValeResult()

    resolved_binary = shutil.which(binary)
    if resolved_binary is None:
        result.unchecked.append(
            f"`{binary}` is not on PATH, so the {len(compiled.vale_rules)} rules "
            f"compiled for it did NOT run. Install it (`mise use -g vale` or "
            f"`brew install vale`), or pass --no-vale to acknowledge the gap."
        )
        return result

    config_path = Path(compiled.config_path)
    if not config_path.is_file():
        result.unchecked.append(
            f"the compiled Vale config is missing ({config_path}), so "
            f"{len(compiled.vale_rules)} rules did NOT run."
        )
        return result

    # A rule that fails to load is absent from `ls-config` while Vale still exits
    # 0 on every file. Comparing the resolved set against what we wrote is the
    # only way that reads as a gap rather than as clean prose.
    from .compile_vale import resolved_checks

    expected = set(compiled.vale_rules)
    actual = resolved_checks(config_path, binary)
    if actual is None:
        result.unchecked.append(
            "Vale could not report its resolved configuration, so the rules it "
            "actually loaded is unknown. Findings below may be incomplete."
        )
    elif expected - actual:
        missing = sorted(expected - actual)
        result.unchecked.append(
            f"Vale resolved {len(actual)} rules but {len(expected)} were compiled "
            f"for it; these did NOT run and their absence is indistinguishable "
            f"from a clean file: {', '.join(missing[:8])}"
            + (f" (+{len(missing) - 8} more)" if len(missing) > 8 else "")
        )

    try:
        completed = subprocess.run(
            [
                resolved_binary,
                f"--config={config_path}",
                "--output=JSON",
                "--no-exit",
                *[str(p) for p in paths],
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        result.unchecked.append(
            f"Vale timed out after {TIMEOUT_SECONDS}s; its rules did NOT run."
        )
        return result
    except OSError as exc:
        result.unchecked.append(f"Vale could not be run ({exc}); its rules did NOT run.")
        return result

    # E201 means a rule file was rejected, and Vale then lints nothing at all.
    # The compiler probes for this, so reaching it here means a rule broke after
    # compilation -- loud, because the alternative is a silent all-clean run.
    #
    # STDERR ONLY, and this cost a whole Vale layer to learn: Vale reports a rule
    # error on stderr, but its JSON findings on STDOUT quote the matched source text
    # back. Scanning both meant any document that mentions E201 or an "error parsing
    # regexp" tripped the guard on itself, lost every Vale finding, and scored HIGHER
    # for it. Measured on this package's own extracted comments: 769 findings dropped,
    # score 65.7 -> 71.4.
    if "E201" in completed.stderr or "error parsing regexp" in completed.stderr:
        result.unchecked.append(
            "Vale rejected a compiled rule (E201) and therefore linted NOTHING. "
            "Run `slopvac compile --outdir <dir>` and check that directory."
        )
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

    if not isinstance(data, dict):
        result.unchecked.append(
            "Vale returned an unexpected JSON shape; its rules did NOT contribute "
            "findings."
        )
        return result

    for path, alerts in data.items():
        for alert in alerts:
            check = alert.get("Check", "")
            span = alert.get("Span") or [1]
            severity = severities.get(check)
            if severity is None:
                # Vale reported a rule we did not compile. Keep it at the level
                # Vale chose rather than dropping it: a finding nobody claims is
                # still a finding, and silently discarding it would hide a
                # stray style on the StylesPath.
                severity = SEVERITY_MAP.get(alert.get("Severity", "warning"), Severity.WARNING)
            result.by_path.setdefault(path, []).append(
                Finding(
                    path=path,
                    line=alert.get("Line", 1),
                    column=span[0] if span else 1,
                    end_column=span[1] if len(span) > 1 else None,
                    rule_id=check,
                    category=categories.get(check, check.split(".", 1)[0]),
                    severity=severity,
                    message=(alert.get("Message") or "").strip(),
                    matched_text=alert.get("Match", ""),
                )
            )
    return result


def unchecked_for_skipped(compiled) -> list[str]:
    """The note that `--no-vale` produces.

    Skipping Vale now skips most of the ruleset, so the rules that would have run
    are reported as unchecked rather than dropped. A gate that silently stops
    checking most of its rules while still printing a score is the exact failure
    mode this project refuses to ship.
    """
    if not compiled.vale_rules:
        return []
    return [
        f"--no-vale skipped the Vale engine, so {len(compiled.vale_rules)} of the "
        f"{len(compiled.vale_rules) + len(compiled.native_rules)} mechanical rules "
        f"did NOT run. The score below reflects only the "
        f"{len(compiled.native_rules)} rules that stayed native."
    ]
