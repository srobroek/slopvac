"""The text-type classifier must not depend on hash seed or process locale."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


FIXTURES = (
    ("Run the migration before you deploy.", "procedural"),
    ("The parser reads the manifest at startup.", "descriptive"),
    ("WARNING: delete the old replica.", "procedural"),
    ("NOTE: naïve users expect café support.", "descriptive"),
    ("Deploy scripts live in /opt/café.", "descriptive"),
    ("U.S. users should read the docs.", "descriptive"),
    ("Don't overwrite the résumé.", "procedural"),
    ("To configure the API, follow these steps.", "procedural"),
    ("Step 2.3: rotate credentials safely.", "procedural"),
    ("A descriptive sentence with Ελληνικά boundaries.", "descriptive"),
)

_CHILD = """
import json
from slopvac.analyze import classify_text_type
texts = json.loads({fixture!r})
print(json.dumps([classify_text_type(text).value for text in texts]))
"""


def _locales() -> list[str]:
    installed = set()
    try:
        installed.update(
            line.strip()
            for line in subprocess.check_output(
                ["locale", "-a"], text=True
            ).splitlines()
            if line.strip()
        )
    except (OSError, subprocess.SubprocessError):
        pass
    candidates = ["C"]
    if "en_US.UTF-8" in installed:
        candidates.append("en_US.UTF-8")
    extras = sorted(
        name for name in installed if name not in {"C", "POSIX", "en_US.UTF-8"}
    )
    if extras:
        candidates.append(extras[0])
    return candidates


@pytest.mark.parametrize("hash_seed", ["0", "1", "random"])
def test_text_type_is_hash_and_locale_deterministic(hash_seed: str) -> None:
    expected = [label for _, label in FIXTURES]
    package_root = Path(__file__).resolve().parents[1]
    outputs: list[list[str]] = []
    for language in _locales():
        env = {
            **os.environ,
            "PYTHONHASHSEED": hash_seed,
            "LC_ALL": language,
            "LANG": language,
            "PYTHONPATH": str(package_root / "src"),
        }
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                _CHILD.format(fixture=json.dumps([text for text, _ in FIXTURES])),
            ],
            cwd=package_root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        labels = json.loads(result.stdout)
        outputs.append(labels)
        assert labels == expected
    assert outputs and all(labels == outputs[0] for labels in outputs)
