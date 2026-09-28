"""Deterministic JSONL conversion to Kev's labelled request schema.

Standard library only: the training container imports this module before any
dependency is installed, so it must not import boto3 or Kev.

Two input formats are accepted, one per file:

- ``source``: the judge-pilot item format (``build_dataset.py``), one item per line with
  ``id``, ``kind``, ``state``, ``label`` and ``question``. Each item becomes one Kev
  request through ``to_kev``, the pilot's conversion from ``finetune_kev.py``.
- ``kev``: rows already in Kev's schema (``state`` and a ``questions`` object). They pass
  through unchanged apart from being re-serialized.

Output rows are written with ``json.dumps`` defaults in input order, as the pilot writes
them, so a source file converts to the same bytes the pilot's ``write_kev_data`` produces.
"""

import hashlib
import json
from pathlib import Path

CHOICE_ORDER = ["real-defect", "no-defect", "insufficient-context"]
SOURCE_KINDS = ("noul", "choice")


class ConversionError(ValueError):
    pass


def to_kev(item):
    """The pilot's conversion (judge-pilot finetune_kev.py), unchanged."""
    q = {
        "type": item["question"]["type"],
        "instructions": item["question"]["instructions"],
        "label": item["label"],
    }
    if item["kind"] == "choice":
        q["criteria"] = {k: item["question"]["criteria"][k] for k in CHOICE_ORDER}
    return {"state": item["state"], "questions": {"q": q}, "id": item["id"]}


def row_format(row):
    if not isinstance(row, dict):
        return None
    if "question" in row and "kind" in row:
        return "source"
    if isinstance(row.get("questions"), dict) and "state" in row:
        return "kev"
    return None


def _check_source(row, where):
    missing = [k for k in ("id", "kind", "state", "label", "question") if k not in row]
    if missing:
        raise ConversionError(f"{where}: source item lacks {', '.join(missing)}")
    if row["kind"] not in SOURCE_KINDS:
        raise ConversionError(
            f"{where}: kind {row['kind']!r} is not one of {SOURCE_KINDS}"
        )
    question = row["question"]
    if (
        not isinstance(question, dict)
        or not {"type", "instructions"} <= question.keys()
    ):
        raise ConversionError(f"{where}: question needs type and instructions")
    if row["kind"] == "choice":
        criteria = question.get("criteria")
        absent = [
            k
            for k in CHOICE_ORDER
            if not isinstance(criteria, dict) or k not in criteria
        ]
        if absent:
            raise ConversionError(f"{where}: choice criteria lack {', '.join(absent)}")


def convert_lines(lines, name="<input>"):
    """-> (kev_text, report). Raises ConversionError on an unknown, mixed or malformed row."""
    out, formats, count = [], set(), 0
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = f"{name}:{number}"
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise ConversionError(f"{where}: not JSON ({e.msg})") from None
        fmt = row_format(row)
        if fmt is None:
            raise ConversionError(f"{where}: neither a source item nor a Kev request")
        formats.add(fmt)
        if len(formats) > 1:
            raise ConversionError(f"{where}: file mixes source items and Kev requests")
        if fmt == "source":
            _check_source(row, where)
            row = to_kev(row)
        out.append(json.dumps(row) + "\n")
        count += 1
    if not count:
        raise ConversionError(f"{name}: no rows")
    text = "".join(out)
    return text, {
        "format": formats.pop(),
        "rows": count,
        "sha256": sha256_bytes(text.encode("utf-8")),
    }


def convert_file(src, dst):
    """Convert src to dst; -> report with the input and output digests."""
    src, dst = Path(src), Path(dst)
    raw = src.read_bytes()
    text, report = convert_lines(raw.decode("utf-8").splitlines(), src.name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return {
        "input": {"name": src.name, "sha256": sha256_bytes(raw), "bytes": len(raw)},
        "output": report,
    }


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
