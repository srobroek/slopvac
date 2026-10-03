"""Small deterministic helpers shared by source and batch stages."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Iterator

WORD_RE = re.compile(r"[\w]+(?:['’\-][\w]+)?", re.UNICODE)


def normalise(text: str) -> str:
    """Normalize source text before hashing, counting, or leak checks."""
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def words(text: str) -> list[str]:
    return [m.group(0).casefold() for m in WORD_RE.finditer(text)]


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def token_estimate(text: str) -> int:
    """Conservative approximate token count used before a paid batch job."""
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def ngrams(tokens: list[str], n: int = 8) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(max(0, len(tokens) - n + 1))}


def leak_scores(source: str, candidate: str) -> tuple[float, float]:
    """Return (8-gram overlap, max sentence token overlap)."""
    source_tokens = words(source)
    candidate_tokens = words(candidate)
    source_grams = ngrams(source_tokens)
    candidate_grams = ngrams(candidate_tokens)
    gram_score = len(source_grams & candidate_grams) / max(1, len(candidate_grams))
    max_sentence = 0.0
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", candidate):
        sentence_tokens = set(words(sentence))
        if sentence_tokens:
            max_sentence = max(
                max_sentence,
                len(sentence_tokens & set(source_tokens)) / len(sentence_tokens),
            )
    return round(gram_score, 6), round(max_sentence, 6)


def shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    return ngrams(words(text), n)


def jaccard(left: set[tuple[str, ...]], right: set[tuple[str, ...]]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / max(1, len(left | right))


def read_jsonl(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
