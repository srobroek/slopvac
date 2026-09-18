from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from slopvac.analyze import Unit, parse
from slopvac.judgement.driver import prepare

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "packages" / "slopvac-lint"
CONFIG = ROOT / "slopvac.toml"
# These are the only fields intentionally canonicalised when comparing subprocess
# artefacts.  The shipped prepare output currently has no timestamps; absolute paths
# may differ when the same corpus is copied to another checkout or temp directory.
LEGITIMATE_VARIATION_FIELDS = frozenset({"path", "document", "config", "timestamp", "created_at"})
_VARIATION_VALUE = re.compile(
    rb'((?:"path"|"document"|"config"|"timestamp"|"created_at")\s*:\s*)'
    rb'("(?:\\.|[^"\\])*"|null|true|false|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)'
)


def _scrub_emitted_bytes(raw: bytes) -> bytes:
    """Replace only documented environment-dependent JSON values in-place."""

    def replace(match: re.Match[bytes]) -> bytes:
        value = match.group(2)
        replacement = b'"<environment-dependent>"' if value.startswith(b'"') else b"0"
        return match.group(1) + replacement

    return _VARIATION_VALUE.sub(replace, raw)


def _json_bytes(path: Path) -> bytes:
    return _scrub_emitted_bytes(path.read_bytes())


def _jsonl_bytes(path: Path) -> bytes:
    return _scrub_emitted_bytes(path.read_bytes())




def _fixture_corpus(root: Path) -> tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    first = root / "first.md"
    second = root / "second.html"
    first.write_text(
        "# Fixture\n\nA paragraph with NFC: café.\n\n"
        "```python\nunterminated fence\n\n| stray | pipe\n",
        encoding="utf-8",
    )
    second.write_text(
        '<p title="a &quot;quoted&quot; attribute">HTML &amp; entities.</p>\r\n'
        "<p>Second line.</p>\r\n",
        encoding="utf-8",
    )
    return first, second


def _prepare_subprocess(paths: tuple[Path, ...], out: Path, *, seed: str, locale: str) -> None:
    env = os.environ.copy()
    env.update({"PYTHONHASHSEED": seed, "LC_ALL": locale, "LANG": locale})
    subprocess.run(
        [
            sys.executable,
            "-m",
            "slopvac.cli",
            "judgement",
            "prepare",
            "--config",
            str(CONFIG),
            "--out",
            str(out),
            "--yes",
            "--packs",
            "SPAN-ai-tells-structure-1",
            *(str(path) for path in paths),
        ],
        cwd=PACKAGE,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
def _artefacts(out: Path) -> tuple[bytes, dict[str, bytes]]:
    units = _jsonl_bytes(out / "units.jsonl")
    documents = {
        path.name: _json_bytes(path)
        for path in sorted((out / "documents").glob("*.json"))
    }
    return units, documents


def _units_by_document(path: Path) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        unit = json.loads(line)
        grouped.setdefault(str(unit["document"]), []).append(unit)
    for entries in grouped.values():
        entries.sort(key=lambda unit: (str(unit["unit_id"]), str(unit.get("rule_id", ""))))
    return grouped


def test_parse_twice_has_identical_identity_ranges_and_evidence_addresses() -> None:
    raw = "# Heading\n\nA café paragraph with `code`.\n\n> Quoted text.\n"
    first = parse("fixture.md", raw)
    second = parse("fixture.md", raw)

    def snapshot(document: object) -> list[tuple[object, ...]]:
        rows: list[tuple[object, ...]] = []
        for block in document.blocks:  # type: ignore[attr-defined]
            rows.append((block.text, block.range, block.doc_range, block.source_sha256))
            for sentence in block.sentences:
                rows.append((sentence.text, sentence.line, sentence.column, sentence.word_count))
            if block.projection is not None:
                unit = Unit(
                    kind="SPAN_CANDIDATE",
                    rule_id="determinism.rule",
                    path=document.path,
                    text=block.text,
                    range=block.range,
                    doc_range=block.doc_range,
                    projection=block.projection,
                    origin=block.origin,
                    region_class=block.region_class,
                    source_sha256=block.source_sha256,
                )
                rows.append((unit.unit_id, unit.range, unit.doc_range, unit.projection.segments))
        return rows

    assert snapshot(first) == snapshot(second)
    assert first.source_sha256 == second.source_sha256

def test_prepare_is_identical_across_hash_seeds_and_locales(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    first, second = _fixture_corpus(corpus)
    runs: list[tuple[bytes, dict[str, bytes]]] = []
    for index, (seed, locale) in enumerate((("0", "C"), ("1", "en_US.UTF-8"), ("random", "C"))):
        out = tmp_path / f"run-{index}"
        _prepare_subprocess((first, second), out, seed=seed, locale=locale)
        runs.append(_artefacts(out))

    assert runs[0] == runs[1] == runs[2]
    assert LEGITIMATE_VARIATION_FIELDS == {"path", "document", "config", "timestamp", "created_at"}


def test_prepare_document_artefacts_do_not_depend_on_input_order(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    first, second = _fixture_corpus(corpus)
    ordered = tmp_path / "ordered"
    reversed_order = tmp_path / "reversed"
    _prepare_subprocess((first, second), ordered, seed="0", locale="C")
    _prepare_subprocess((second, first), reversed_order, seed="0", locale="C")

    _, ordered_docs = _artefacts(ordered)
    _, reversed_docs = _artefacts(reversed_order)
    assert ordered_docs == reversed_docs
    assert _units_by_document(ordered / "units.jsonl") == _units_by_document(reversed_order / "units.jsonl")


@pytest.mark.parametrize(
    ("name", "raw"),
    [
        ("unclosed-fence.md", "Before.\n\n```\ncode\n"),
        ("stray-pipes.md", "| stray | pipe\nplain text\n"),
        ("nfc.md", "café\n"),
        ("nfd.md", "cafe\u0301\n"),
        ("entities.html", '<p title="a &quot;title&quot;">A &amp; B.</p>\n'),
        ("crlf.md", "First.\r\n\r\nSecond.\r\n"),
    ],
)
def test_edge_fixture_prepare_has_stable_units_and_ranges(tmp_path: Path, name: str, raw: str) -> None:
    fixture = tmp_path / name
    fixture.write_text(raw, encoding="utf-8", newline="")
    first = tmp_path / "first"
    second = tmp_path / "second"
    prepare(config=CONFIG, out=first, paths=(fixture,), packs="SPAN-ai-tells-structure-1", yes=True)
    prepare(config=CONFIG, out=second, paths=(fixture,), packs="SPAN-ai-tells-structure-1", yes=True)
    assert _artefacts(first) == _artefacts(second)

    document = parse(str(fixture), raw)
    if name == "unclosed-fence.md":
        assert [(block.kind.value, block.lines) for block in document.blocks] == [
            ("paragraph", (1, 1)),
            ("code", (3, 4)),
        ]
        assert document.blocks[1].doc_range == (7, 7)
    elif name == "nfd.md":
        block = document.blocks[0]
        assert [sentence.text for sentence in block.sentences] == ["cafe\u0301"]
        assert block.projection is not None
        assert block.projection.slice_raw(*block.range) == raw.rstrip("\n").encode("utf-8")
    elif name == "crlf.md":
        assert [(sentence.text, sentence.line, sentence.column) for block in document.blocks for sentence in block.sentences] == [
            ("First.", 1, 1),
            ("Second.", 3, 1),
        ]
        assert all("\r" not in sentence.text for block in document.blocks for sentence in block.sentences)
    elif name == "entities.html":
        block = document.blocks[0]
        assert [sentence.text for sentence in block.sentences] == ["A & B."]
        assert block.projection is not None
        assert block.projection.slice_raw(*block.range) == b"A &amp; B."
    elif name == "stray-pipes.md":
        assert [block.kind.value for block in document.blocks] == ["paragraph"]


def test_nfc_and_nfd_identity_is_source_sensitive_and_deterministic(tmp_path: Path) -> None:
    nfc = tmp_path / "nfc.md"
    nfd = tmp_path / "nfd.md"
    nfc.write_text("café\n", encoding="utf-8")
    nfd.write_text("cafe\u0301\n", encoding="utf-8")
    assert parse(str(nfc), nfc.read_text(encoding="utf-8")).source_sha256 != parse(
        str(nfd), nfd.read_text(encoding="utf-8")
    ).source_sha256
