from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from slopvac import update_notice


@pytest.fixture(autouse=True)
def _clear_update_suppression(monkeypatch):
    for name in ("CI", "NO_UPDATE_NOTIFIER", "SLOPVAC_NO_UPDATE_CHECK", "DO_NOT_TRACK"):
        monkeypatch.delenv(name, raising=False)


def test_version_comparison_handles_release_boundaries():
    assert update_notice.is_newer_release("2.13.0", "2.12.9")
    assert update_notice.is_newer_release("2.12.1", "2.12")
    assert not update_notice.is_newer_release("2.12.0", "2.12")
    assert not update_notice.is_newer_release("2.12.0rc1", "2.12.0")
    assert not update_notice.is_newer_release("2.13", "not-a-version")
    assert not update_notice.is_newer_release("2.12+local", "2.11")


def test_fresh_cache_skips_refresh(tmp_path, monkeypatch):
    path = tmp_path / "update-check.json"
    path.write_text(
        json.dumps({"checked_at": datetime.now(UTC).isoformat(), "latest_version": "2.12.0"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(update_notice, "_fetch_latest_version", lambda: pytest.fail("fetch"))

    assert update_notice.start_refresh(stderr_isatty=True) is None


def test_cached_newer_release_prints_one_notice(monkeypatch, tmp_path, capsys):
    path = tmp_path / "update-check.json"
    path.write_text(
        json.dumps({"checked_at": datetime.now(UTC).isoformat(), "latest_version": "2.13.0"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(update_notice, "__version__", "2.12.0")
    monkeypatch.setattr(update_notice, "upgrade_hint", lambda: "uv tool upgrade slopvac")

    update_notice.show_update_notice(stderr_isatty=True)

    assert capsys.readouterr().err == (
        "slopvac 2.13.0 is available (you have 2.12.0). "
        "Upgrade: uv tool upgrade slopvac\n"
    )


def test_start_refresh_runs_concurrently_and_show_joins(tmp_path, monkeypatch, capsys):
    path = tmp_path / "update-check.json"
    path.write_text(
        json.dumps(
            {
                "checked_at": (datetime.now(UTC) - timedelta(hours=25)).isoformat(),
                "latest_version": "2.12.0",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(update_notice, "_fetch_latest_version", lambda: "2.13.0")
    monkeypatch.setattr(update_notice, "__version__", "2.12.0")
    monkeypatch.setattr(update_notice, "upgrade_hint", lambda: "uv tool upgrade slopvac")

    refresh = update_notice.start_refresh(stderr_isatty=True)
    assert refresh is not None
    update_notice.show_update_notice(
        refresh,
        stderr_isatty=True,
        command="lint",
        output_format="text",
        wait_seconds=2,
    )

    assert not refresh.is_alive()
    assert json.loads(path.read_text(encoding="utf-8"))["latest_version"] == "2.13.0"
    assert capsys.readouterr().err == (
        "slopvac 2.13.0 is available (you have 2.12.0). "
        "Upgrade: uv tool upgrade slopvac\n"
    )


def test_fetch_failure_records_attempt_without_notice(tmp_path, monkeypatch, capsys):
    path = tmp_path / "update-check.json"
    path.write_text(
        json.dumps(
            {
                "checked_at": (datetime.now(UTC) - timedelta(hours=25)).isoformat(),
                "latest_version": "2.11.0",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(
        update_notice,
        "_fetch_latest_version",
        lambda: (_ for _ in ()).throw(OSError("offline")),
    )

    refresh = update_notice.start_refresh(stderr_isatty=True)
    assert refresh is not None
    update_notice.show_update_notice(
        refresh,
        stderr_isatty=True,
        command="lint",
        output_format="text",
        wait_seconds=2,
    )

    cache = json.loads(path.read_text(encoding="utf-8"))
    assert cache["latest_version"] == "2.11.0"
    assert datetime.fromisoformat(cache["checked_at"]) > datetime.now(UTC) - timedelta(minutes=1)
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "name", ["NO_UPDATE_NOTIFIER", "SLOPVAC_NO_UPDATE_CHECK", "DO_NOT_TRACK", "CI"]
)
def test_environment_suppression_prevents_refresh(name, monkeypatch):
    monkeypatch.setenv(name, "1")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    assert update_notice.start_refresh(stderr_isatty=True) is None


def test_non_tty_suppression_prevents_refresh(monkeypatch):
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    assert update_notice.start_refresh(stderr_isatty=False) is None


@pytest.mark.parametrize("output_format", ["json", "sarif", "github", "html"])
def test_machine_format_suppression(monkeypatch, output_format):
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    update_notice.show_update_notice(stderr_isatty=True, output_format=output_format)


def test_prime_and_report_files_skip_notice(monkeypatch):
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    update_notice.show_update_notice(stderr_isatty=True, command="prime")
    update_notice.show_update_notice(stderr_isatty=True, output_to_file=True)
