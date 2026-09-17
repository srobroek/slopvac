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


def validate_model_output(obj: Any) -> list[str]:
    """Return deterministic validation messages; an empty list means valid."""
    return [error.message for error in sorted(_VALIDATOR.iter_errors(obj), key=lambda e: list(e.path))]


__all__ = ["validate_model_output"]
