from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rc_version.py"
SPEC = importlib.util.spec_from_file_location("rc_version", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
rc_version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rc_version)


@pytest.fixture
def release_map() -> dict[str, list[dict[str, object]]]:
    return {
        "2.16.2": [{"filename": "slopvac-2.16.2.whl", "yanked": False}],
    }


def test_first_rc(release_map):
    assert rc_version.next_rc_version("2.17.0", release_map) == "2.17.0rc1"


def test_next_rc_after_existing_rc1_and_rc2(release_map):
    release_map["2.17.0rc1"] = [{"yanked": False}]
    release_map["2.17.0rc2"] = [{"yanked": False}]

    assert rc_version.next_rc_version("2.17.0", release_map) == "2.17.0rc3"


def test_yanked_rc_still_counts(release_map):
    release_map["2.17.0rc1"] = [{"yanked": True}]

    assert rc_version.next_rc_version("2.17.0", release_map) == "2.17.0rc2"


def test_final_version_already_on_pypi_is_an_error(release_map):
    release_map["2.17.0"] = [{"yanked": True}]

    with pytest.raises(ValueError, match="final version 2.17.0 already exists"):
        rc_version.next_rc_version("2.17.0", release_map)


def test_pending_version_not_newer_than_pypi_max_is_an_error(release_map):
    with pytest.raises(ValueError, match="not newer than the highest PyPI version"):
        rc_version.next_rc_version("2.16.1", release_map)


def test_rewrites_every_configured_version_file(tmp_path):
    config = {
        "packages": {
            ".": {
                "extra-files": [
                    "packages/slopvac-lint/pyproject.toml",
                    "packages/slopvac-lint/src/slopvac/__init__.py",
                    ".pre-commit-hooks.yaml",
                    "README.md",
                ]
            }
        }
    }
    (tmp_path / "release-please-config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    files = {
        "packages/slopvac-lint/pyproject.toml": (
            'version = "2.17.0" # x-release-please-version\n'
        ),
        "packages/slopvac-lint/src/slopvac/__init__.py": (
            '__version__ = "2.17.0"  # x-release-please-version\n'
        ),
        ".pre-commit-hooks.yaml": (
            'additional_dependencies: ["slopvac==2.17.0"] # x-release-please-version\n'
        ),
        "README.md": (
            'rev: v2.17.0 # x-release-please-version\n'
            'uses: srobroek/slopvac@v2.17.0 # x-release-please-version\n'
        ),
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    rc_version.rewrite_version_files(tmp_path, "2.17.0rc1")

    for relative in files:
        text = (tmp_path / relative).read_text(encoding="utf-8")
        assert "2.17.0rc1" in text
        assert "2.17.0" not in text.replace("2.17.0rc1", "")
