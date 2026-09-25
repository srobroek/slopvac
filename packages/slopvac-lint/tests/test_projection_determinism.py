from __future__ import annotations

from pathlib import Path

import pytest

from slopvac.analyze import parse


def _snapshot(raw: str, path: str = "fixture.md") -> list[tuple[object, ...]]:
    document = parse(path, raw)
    rows: list[tuple[object, ...]] = [
        (document.path, document.source_sha256),
    ]
    for block in document.blocks:
        rows.append(
            (
                block.kind.value,
                block.text,
                block.range,
                block.doc_range,
                block.source_sha256,
                block.projection.segments if block.projection is not None else (),
            )
        )
        for sentence in block.sentences:
            rows.append(
                (
                    sentence.text,
                    sentence.line,
                    sentence.column,
                    sentence.word_count,
                    sentence.range if hasattr(sentence, "range") else (sentence.start, sentence.end),
                    sentence.source_spans,
                )
            )
    return rows


def test_parse_twice_has_identical_identity_ranges_and_source_maps() -> None:
    raw = "# Heading\n\nA café paragraph with `code`.\n\n> Quoted text.\n"
    assert _snapshot(raw) == _snapshot(raw)


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
def test_edge_fixture_parse_is_deterministic(name: str, raw: str) -> None:
    assert _snapshot(raw, name) == _snapshot(raw, name)


def test_projection_preserves_source_ranges_for_edge_cases(tmp_path: Path) -> None:
    cases = {
        "nfd.md": "cafe\u0301\n",
        "entities.html": '<p title="a &quot;title&quot;">A &amp; B.</p>\n',
        "crlf.md": "First.\r\n\r\nSecond.\r\n",
    }
    for name, raw in cases.items():
        path = tmp_path / name
        path.write_text(raw, encoding="utf-8", newline="")
        document = parse(str(path), raw)
        assert document.source_sha256

        if name == "nfd.md":
            block = document.blocks[0]
            assert block.projection is not None
            assert block.projection.slice_raw(*block.range) == raw.rstrip("\n").encode("utf-8")
        elif name == "entities.html":
            block = document.blocks[0]
            assert [sentence.text for sentence in block.sentences] == ["A & B."]
            assert block.projection is not None
            assert block.projection.slice_raw(*block.range) == b"A &amp; B."
        elif name == "crlf.md":
            assert [
                (sentence.text, sentence.line, sentence.column)
                for block in document.blocks
                for sentence in block.sentences
            ] == [("First.", 1, 1), ("Second.", 3, 1)]


def test_nfc_and_nfd_identity_is_source_sensitive_and_deterministic(tmp_path: Path) -> None:
    nfc = tmp_path / "nfc.md"
    nfd = tmp_path / "nfd.md"
    nfc.write_text("café\n", encoding="utf-8")
    nfd.write_text("cafe\u0301\n", encoding="utf-8")

    first = parse(str(nfc), nfc.read_text(encoding="utf-8"))
    second = parse(str(nfd), nfd.read_text(encoding="utf-8"))
    assert first.source_sha256 != second.source_sha256
