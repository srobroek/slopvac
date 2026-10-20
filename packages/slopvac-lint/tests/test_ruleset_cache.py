"""The cached ruleset load. A hit must be indistinguishable from a fresh load.

The cache skips the example proof. Each way it could serve something a fresh load
would not -- an edited rule file, a damaged entry, a document JSON cannot hold
exactly -- has a test here that compares against a fresh load.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import pytest

from slopvac import rules as rules_module
from slopvac.analyze import parse
from slopvac.config import Config, resolve_for
from slopvac.engine import Engine
from slopvac.rules import RuleLoadError, load_ruleset
from slopvac.ruleset_cache import entry_path, read, write
from slopvac.vale_cache import cache_root

HOUSE = """\
id: house
title: House rules
description: A project's own category.
rules:
  - id: no-widget
    name: Name the part
    kind: pattern
    message: name the part instead
    pattern: '\\bwidget\\b'
    examples:
      - bad: The widget broke.
        good: The parser broke.
    provenance:
      source: test
"""

# Fires the house rule and shipped word rules, so equal findings mean something.
SAMPLE = "We leverage the widget to utilize a seamless, robust synergy.\n"


@pytest.fixture
def house(tmp_path: Path) -> Path:
    directory = tmp_path / "house"
    directory.mkdir()
    (directory / "house.yml").write_text(HOUSE, encoding="utf-8")
    return directory


@pytest.fixture
def proved(monkeypatch) -> list[str]:
    """The origin of every rule group the example proof ran over, in order."""
    seen: list[str] = []
    real = rules_module._verify_examples

    def spy(rules, origin):
        seen.append(origin)
        return real(rules, origin)

    monkeypatch.setattr(rules_module, "_verify_examples", spy)
    return seen


def _findings(ruleset) -> list[dict]:
    engine = Engine(ruleset.rules, resolve_for(Config(), Path("/repo/a.md")))
    return [finding.model_dump() for finding in engine.run(parse("a.md", SAMPLE))]


def _entries() -> list[Path]:
    return sorted((cache_root() / "rulesets").glob("*.json"))


def test_a_hit_loads_the_same_rules_and_findings_without_the_proof(house, proved):
    fresh = load_ruleset([house])
    assert str(house / "house.yml") in proved
    proved.clear()

    cached = load_ruleset([house])
    assert proved == []
    assert list(cached.categories) == list(fresh.categories)
    assert cached.categories == fresh.categories
    findings = _findings(fresh)
    assert "house.no-widget" in {finding["rule_id"] for finding in findings}
    assert _findings(cached) == findings


def test_user_rules_are_proved_once(house, proved):
    for _ in range(3):
        load_ruleset([house])
    assert proved.count(str(house / "house.yml")) == 1


def test_editing_a_rule_file_invalidates_the_entry(house, proved):
    load_ruleset([house])
    edited_text = HOUSE.replace("\\bwidget\\b", "\\bgadget\\b").replace(
        "The widget broke.", "The gadget broke."
    )
    (house / "house.yml").write_text(edited_text, encoding="utf-8")
    proved.clear()

    edited = load_ruleset([house])
    rule = edited.by_id("house.no-widget")
    assert rule is not None
    assert rule.pattern == r"\bgadget\b"
    assert str(house / "house.yml") in proved
    # The edit overwrote its slot rather than adding an entry.
    assert len(_entries()) == 1


def test_an_edit_that_breaks_an_example_fails_after_a_hit(house):
    load_ruleset([house])
    load_ruleset([house])
    broken = HOUSE.replace("bad: The widget broke.", "bad: The parser broke.")
    (house / "house.yml").write_text(broken, encoding="utf-8")
    with pytest.raises(RuleLoadError, match="does not match its own pattern"):
        load_ruleset([house])


def test_each_rule_directory_set_has_its_own_slot(house, proved):
    load_ruleset()
    load_ruleset([house])
    proved.clear()
    load_ruleset()
    load_ruleset([house])
    assert proved == []
    assert len(_entries()) == 2


def _forge(entry: Path, body: bytes) -> bytes:
    """`body` under the entry's real key and a matching checksum."""
    key = json.loads(entry.read_bytes().partition(b"\n")[0])["key"]
    header = json.dumps({"key": key, "sha256": hashlib.sha256(body).hexdigest()})
    return header.encode() + b"\n" + body


@pytest.mark.parametrize(
    "damage",
    [
        "empty",
        "garbage",
        "truncated",
        "edited-body",
        "foreign-key",
        "wrong-shape",
        "invalid-rules",
    ],
)
def test_a_damaged_entry_falls_back_to_a_fresh_load(house, proved, damage):
    fresh = load_ruleset([house])
    [entry] = _entries()
    raw = entry.read_bytes()
    header, _, body = raw.partition(b"\n")
    damaged = {
        "empty": lambda: b"",
        "garbage": lambda: b"\x00\xffnot json at all",
        "truncated": lambda: raw[: len(raw) // 2],
        # Still valid JSON, but its rules differ from the proved ones.
        "edited-body": lambda: header + b"\n" + body.replace(b"widget", b"widgex", 1),
        "foreign-key": lambda: raw.replace(b'"key": "', b'"key": "0', 1),
        "wrong-shape": lambda: _forge(entry, b'{"not": "a list"}'),
        "invalid-rules": lambda: _forge(entry, b'[["forged.yml", [{"id": "Not An Id"}]]]'),
    }[damage]()
    assert damaged != raw
    entry.write_bytes(damaged)
    proved.clear()

    reloaded = load_ruleset([house])
    assert reloaded.categories == fresh.categories
    assert _findings(reloaded) == _findings(fresh)
    assert str(house / "house.yml") in proved

    # The fresh load rewrote the entry, so the next load is a hit again.
    proved.clear()
    load_ruleset([house])
    assert proved == []


def test_an_unwritable_cache_still_loads(house, tmp_path, monkeypatch):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("SLOPVAC_CACHE_DIR", str(blocker))
    assert load_ruleset([house]).by_id("house.no-widget") is not None
    assert load_ruleset([house]).by_id("house.no-widget") is not None


def test_an_unproved_load_neither_reads_nor_writes_the_cache(house, proved):
    load_ruleset([house], verify=False)
    assert _entries() == []
    load_ruleset([house])
    proved.clear()
    load_ruleset([house], verify=False)
    assert proved == []
    assert len(_entries()) == 1


@pytest.mark.parametrize(
    "document",
    [
        {"when": datetime.date(2026, 1, 1)},
        {"tokens": {"a", "b"}},
        {1: "a non-string key JSON would turn into a string"},
        {"threshold": float("nan")},
    ],
)
def test_documents_json_cannot_hold_exactly_are_not_stored(tmp_path, document):
    path = tmp_path / "entry.json"
    write(path, "key", [("probe.yml", [document])])
    assert not path.exists()


def test_a_written_entry_reads_back_only_under_its_key(tmp_path):
    path = tmp_path / "entry.json"
    documents = [("probe.yml", [{"id": "probe", "weight": 1.5, "rules": []}])]
    write(path, "key", documents)
    assert read(path, "key") == documents
    assert read(path, "other") is None
    assert not list(tmp_path.glob(".*.tmp"))


def test_slots_depend_on_the_directories_not_their_spelling(house, monkeypatch):
    monkeypatch.chdir(house.parent)
    assert entry_path([Path("house")]) == entry_path([house])
    assert entry_path([house]) != entry_path([])
