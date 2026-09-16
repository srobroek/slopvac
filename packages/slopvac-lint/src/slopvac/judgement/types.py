from dataclasses import dataclass
from typing import Literal

DimMask = Literal["ask", "inapplicable"]
EvidenceRole = Literal["antecedent", "contrast", "defect", "invariant", "referent"]
PreservationClass = Literal[
    "accessibility_consistency",
    "authoritative_domain_term",
    "controlled_language_clarity",
    "factual_polarity_or_contrast",
    "normative_obligation",
    "quoted_specimen",
    "source_locked_legal_text",
]
Severity = Literal["error", "warning", "suggestion"]
TokenClass = Literal[
    "code_and_identifiers",
    "cross_reference_target",
    "defined_terms",
    "modality",
    "named_entities",
    "negation_polarity",
    "numerals_units_versions_dates",
    "procedure_dependency",
]


@dataclass(frozen=True)
class EvidenceSpec:
    min_arity: int
    roles: tuple[EvidenceRole, ...]


@dataclass(frozen=True)
class Transition:
    token_class: TokenClass
    src: str
    dst: str


@dataclass(frozen=True)
class TransitionTable:
    status: Literal["provisional", "calibrated"]
    rows: tuple[Transition, ...]
    requires: str


@dataclass(frozen=True)
class HostPredicate:
    id: str
    definition: str


@dataclass(frozen=True)
class JudgementContract:
    dims: dict[str, DimMask]
    evidence: EvidenceSpec
    warrant_min: int
    protects: tuple[PreservationClass, ...]
    judgement_ceiling: Severity
    adjudicates: PreservationClass | None = None
    allowed_transitions: TransitionTable | None = None
    host_predicates: tuple[HostPredicate, ...] = ()
    scope_class: Literal["local", "probe"] = "local"
