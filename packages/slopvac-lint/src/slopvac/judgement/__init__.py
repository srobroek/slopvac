"""Judgement layer: rule contracts, prompt packs, rewrite checking, evaluation."""

from .adjudicate import EvidenceSpan, FindingRecord, adjudicate
from .checker import CheckerResult, Violation, check_rewrite
from .packs import (
    Pack,
    build_packs,
    canonical_bytes,
    instrument_id,
    judgement_cache_key,
    pack_id,
    pack_object,
    render_pack,
    rubric_revision,
)
from .schema import normalize_result_set, validate_model_output
from .types import (
    DimMask,
    EvidenceRole,
    EvidenceSpec,
    HostPredicate,
    JudgementContract,
    PreservationClass,
    Severity,
    Transition,
    TransitionTable,
)

__all__ = [
    "CheckerResult",
    "DimMask",
    "EvidenceRole",
    "EvidenceSpan",
    "EvidenceSpec",
    "FindingRecord",
    "HostPredicate",
    "JudgementContract",
    "Pack",
    "PreservationClass",
    "Severity",
    "Transition",
    "TransitionTable",
    "Violation",
    "adjudicate",
    "build_packs",
    "canonical_bytes",
    "check_rewrite",
    "instrument_id",
    "judgement_cache_key",
    "normalize_result_set",
    "pack_id",
    "pack_object",
    "render_pack",
    "rubric_revision",
    "validate_model_output",
]
