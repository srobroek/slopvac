"""Validation for the model-visible judgement output contract."""
from __future__ import annotations

import json
from importlib import resources
from typing import Any

from jsonschema import Draft202012Validator

_SCHEMA = json.loads(
    resources.files("slopvac.judgement").joinpath("model_output_schema.json").read_text(
        encoding="utf-8"
    )
)
_VALIDATOR = Draft202012Validator(_SCHEMA)
_SCHEMA_KEYS = frozenset(_SCHEMA.get("properties", {}))
_ANNOTATION_SUFFIXES = ("_note", "_ignored", "_ref")


def _is_model_annotation(key: str) -> bool:
    if key in _SCHEMA_KEYS:
        return False
    return key.endswith(_ANNOTATION_SUFFIXES) or (key != key.strip() and key.strip() in _SCHEMA_KEYS)


def normalize_result_set(rows: Any) -> Any:
    """Move benign model annotations aside before schema validation.

    Rows retain annotations under ``model_annotations`` for reporting, while
    ``validate_model_output`` validates a copy without that host-side field.
    Unknown fields that do not match the narrow annotation rules remain intact
    and therefore continue to fail the response schema.
    """
    if not isinstance(rows, list):
        return rows
    for row in rows:
        if not isinstance(row, dict):
            continue
        annotations = {
            key: row.pop(key)
            for key in sorted(tuple(row))
            if isinstance(key, str) and _is_model_annotation(key)
        }
        if annotations:
            row.setdefault("model_annotations", {}).update(annotations)
    return rows


def validate_model_output(obj: Any) -> list[str]:
    """Return deterministic validation messages; an empty list means valid."""
    if isinstance(obj, dict) and "model_annotations" in obj:
        obj = {key: value for key, value in obj.items() if key != "model_annotations"}
    return [error.message for error in sorted(_VALIDATOR.iter_errors(obj), key=lambda e: list(e.path))]


__all__ = ["normalize_result_set", "validate_model_output"]
