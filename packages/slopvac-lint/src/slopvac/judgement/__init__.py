"""Judgement layer: rule contracts, prompt packs, rewrite checking, evaluation."""

from .adjudicate import EvidenceSpan, FindingRecord, adjudicate
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
from .schema import validate_model_output
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
    "adjudicate",
    "build_packs",
    "canonical_bytes",
    "instrument_id",
    "judgement_cache_key",
    "pack_id",
    "pack_object",
    "render_pack",
    "rubric_revision",
    "validate_model_output",
]
