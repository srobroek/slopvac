from __future__ import annotations

import fcntl
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from slopvac import update_notice


@pytest.fixture(autouse=True)
def _clear_update_suppression(monkeypatch):
    for name in ("CI", "NO_UPDATE_NOTIFIER", "SLOPVAC_NO_UPDATE_CHECK", "DO_NOT_TRACK"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def spawned(monkeypatch):
    """Every detached refresh `start_refresh` launches, without launching one."""
    calls: list[tuple[list[str], dict]] = []
    monkeypatch.setattr(
        subprocess, "Popen", lambda args, **kwargs: calls.append((args, kwargs))
    )
    return calls


@pytest.fixture
def offline(monkeypatch):
    """The command's own process must never ask PyPI."""
    monkeypatch.setattr(
        update_notice, "_fetch_latest_version", lambda: pytest.fail("network call")
    )


def _cache(path, *, age: timedelta, latest: str | None) -> None:
    checked_at = (datetime.now(UTC) - age).isoformat()
    path.write_text(
        json.dumps({"checked_at": checked_at, "latest_version": latest}), encoding="utf-8"
    )


def test_version_comparison_handles_release_boundaries():
    assert update_notice.is_newer_release("2.13.0", "2.12.9")
    assert update_notice.is_newer_release("2.12.1", "2.12")
    assert not update_notice.is_newer_release("2.12.0", "2.12")
    assert not update_notice.is_newer_release("2.12.0rc1", "2.12.0")
    assert not update_notice.is_newer_release("2.13", "not-a-version")
    assert not update_notice.is_newer_release("2.12+local", "2.11")


def test_fresh_cache_skips_refresh(tmp_path, monkeypatch, spawned, offline):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(0), latest="2.12.0")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)

    assert update_notice.start_refresh(stderr_isatty=True) is False
    assert spawned == []


def test_cached_newer_release_prints_one_notice(monkeypatch, tmp_path, capsys):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(0), latest="2.13.0")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(update_notice, "__version__", "2.12.0")
    monkeypatch.setattr(update_notice, "upgrade_hint", lambda: "uv tool upgrade slopvac")

    update_notice.show_update_notice(stderr_isatty=True)

    assert capsys.readouterr().err == (
        "slopvac 2.13.0 is available (you have 2.12.0). "
        "Upgrade: uv tool upgrade slopvac\n"
    )


def test_stale_cache_spawns_one_detached_refresh(
    tmp_path, monkeypatch, capsys, spawned, offline
):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(hours=25), latest="2.13.0")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(update_notice, "__version__", "2.12.0")
    monkeypatch.setattr(update_notice, "upgrade_hint", lambda: "uv tool upgrade slopvac")

    assert update_notice.start_refresh(stderr_isatty=True) is True
    # The claim made the cache fresh, so a second run in the interval spawns nothing.
    assert update_notice.start_refresh(stderr_isatty=True) is False
    update_notice.show_update_notice(
        stderr_isatty=True, command="lint", output_format="text"
    )

    [(args, kwargs)] = spawned
    assert args == [sys.executable, "-P", "-m", "slopvac.update_notice", str(path)]
    assert kwargs["start_new_session"] is True
    assert {kwargs[stream] for stream in ("stdin", "stdout", "stderr")} == {
        subprocess.DEVNULL
    }
    cache = json.loads(path.read_text(encoding="utf-8"))
    assert cache["latest_version"] == "2.13.0"
    assert datetime.fromisoformat(cache["checked_at"]) > datetime.now(UTC) - timedelta(
        minutes=1
    )
    # The notice reads what the cache already knew; the refresh feeds a later run.
    assert capsys.readouterr().err == (
        "slopvac 2.13.0 is available (you have 2.12.0). "
        "Upgrade: uv tool upgrade slopvac\n"
    )


def test_claim_held_elsewhere_spawns_nothing(tmp_path, monkeypatch, spawned):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(hours=25), latest="2.12.0")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)

    with (tmp_path / ".update-check.lock").open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert update_notice.start_refresh(stderr_isatty=True) is False

    assert spawned == []


def test_no_fcntl_spawns_nothing(tmp_path, monkeypatch, spawned):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(hours=25), latest="2.12.0")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    # Windows: `import fcntl` raises ImportError.
    monkeypatch.setitem(sys.modules, "fcntl", None)

    assert update_notice.start_refresh(stderr_isatty=True) is False
    assert spawned == []


def test_refresh_writes_the_latest_release(tmp_path, monkeypatch):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(minutes=5), latest="2.12.0")
    monkeypatch.setattr(update_notice, "_fetch_latest_version", lambda: "2.13.0")

    update_notice.refresh_cache(path)

    cache = json.loads(path.read_text(encoding="utf-8"))
    assert cache["latest_version"] == "2.13.0"
    assert [entry.name for entry in tmp_path.iterdir()] == ["update-check.json"]


def test_fetch_failure_keeps_the_recorded_attempt(tmp_path, monkeypatch, capsys, spawned):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(hours=25), latest="2.11.0")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: path)
    monkeypatch.setattr(
        update_notice,
        "_fetch_latest_version",
        lambda: (_ for _ in ()).throw(OSError("offline")),
    )

    assert update_notice.start_refresh(stderr_isatty=True) is True
    claimed = path.read_text(encoding="utf-8")
    update_notice.refresh_cache(path)
    update_notice.show_update_notice(
        stderr_isatty=True, command="lint", output_format="text"
    )

    assert path.read_text(encoding="utf-8") == claimed
    cache = json.loads(claimed)
    assert cache["latest_version"] == "2.11.0"
    assert datetime.fromisoformat(cache["checked_at"]) > datetime.now(UTC) - timedelta(
        minutes=1
    )
    assert capsys.readouterr().err == ""


def test_interrupted_write_keeps_the_old_cache(tmp_path, monkeypatch):
    path = tmp_path / "update-check.json"
    _cache(path, age=timedelta(minutes=5), latest="2.12.0")
    before = path.read_text(encoding="utf-8")

    def interrupted(source, destination):
        raise OSError("disk full")

    monkeypatch.setattr(update_notice.os, "replace", interrupted)
    with pytest.raises(OSError, match="disk full"):
        update_notice._write_cache(path, {"latest_version": "2.13.0"})

    assert path.read_text(encoding="utf-8") == before
    assert [entry.name for entry in tmp_path.iterdir()] == ["update-check.json"]


@pytest.mark.parametrize(
    "name", ["NO_UPDATE_NOTIFIER", "SLOPVAC_NO_UPDATE_CHECK", "DO_NOT_TRACK", "CI"]
)
def test_environment_suppression_prevents_refresh_and_notice(
    name, monkeypatch, capsys, spawned
):
    monkeypatch.setenv(name, "1")
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    assert update_notice.start_refresh(stderr_isatty=True) is False
    update_notice.show_update_notice(stderr_isatty=True)

    assert spawned == []
    assert capsys.readouterr().err == ""


def test_non_tty_suppression_prevents_refresh(monkeypatch, spawned):
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    assert update_notice.start_refresh(stderr_isatty=False) is False
    assert spawned == []


@pytest.mark.parametrize("output_format", ["json", "sarif", "github", "html"])
def test_machine_format_suppression(monkeypatch, output_format):
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    update_notice.show_update_notice(stderr_isatty=True, output_format=output_format)


def test_prime_and_report_files_skip_notice(monkeypatch):
    monkeypatch.setattr(update_notice, "_cache_path", lambda: pytest.fail("cache"))

    update_notice.show_update_notice(stderr_isatty=True, command="prime")
    update_notice.show_update_notice(stderr_isatty=True, output_to_file=True)
