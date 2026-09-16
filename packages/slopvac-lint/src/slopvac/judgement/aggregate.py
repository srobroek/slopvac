"""Aggregate host judgement records into components, coverage, and score data."""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

LOGGER = logging.getLogger(__name__)

COVERAGE_COUNTERS = (
    "eligible",
    "attempted",
    "confirmed",
    "rejected",
    "preserved",
    "abstained",
    "failed",
    "truncated",
    "not_run",
)
Outcome = Literal["DROP", "PRESERVE", "ABSTAIN", "REJECT", "CONFIRM"]


@runtime_checkable
class EvidenceLike(Protocol):
    quote: str
    start: int
    end: int
    role: str
    source: str
    source_ref: str | None
    doc_start: int | None
    doc_end: int | None


@runtime_checkable
class FindingLike(Protocol):
    """The shared FindingRecord shape, kept local to avoid a B2 import."""

    unit_id: str
    rule_id: str
    kind: Literal["SPAN_CANDIDATE", "PASSAGE_PROBE"]
    outcome: Outcome
    severity: Literal["error", "warning", "suggestion"] | None
    scores: dict | None
    evidence: tuple[EvidenceLike, ...]
    preservation_reason: str | None
    abstain_reason: str | None
    rewrite: str | None
    rewrite_status: Literal[
        "not_applicable", "proposed", "withheld_needs_fact", "withheld_checker_veto"
    ]
    core_fired: bool
    component_id: str | None
    source_sha256: str
    path: str
    instrument_id: str
    judgement_cache_key: str
    occurrence_index: int | None


@dataclass(frozen=True)
class DependenceTable:
    """A frozen same-phenomenon relation between rule ids."""

    dependence_table_sha: str
    pairs: tuple[tuple[str, str], ...] = ()
    status: Literal["calibrated", "uncalibrated"] = "calibrated"
    def related(self, left: str, right: str) -> bool:
        pair = tuple(sorted((left, right)))
        return pair in self.pairs

    def __getitem__(self, key: str) -> Any:
        if key == "dependence_table_sha":
            return self.dependence_table_sha
        if key == "pairs":
            return [list(pair) for pair in self.pairs]
        if key == "status":
            return self.status
        raise KeyError(key)
    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


@dataclass(frozen=True)
class _Paragraph:
    key: str
    start: int | None
    end: int | None


@dataclass
class Component:
    """A transitive closure of confirmed findings in one paragraph."""

    component_id: str
    findings: tuple[FindingLike, ...]
    paragraph: str
    primary_spans: tuple[tuple[int, int], ...]
    severity: str | None = None

    @property
    def primary_span(self) -> tuple[int, int] | None:
        if not self.primary_spans:
            return None
        return (
            min(start for start, _ in self.primary_spans),
            max(end for _, end in self.primary_spans),
        )

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(finding.rule_id for finding in self.findings)


@dataclass
class CoverageBucket:
    """Coverage counters for one document, pack, or rule."""

    eligible: int = 0
    attempted: int = 0
    confirmed: int = 0
    rejected: int = 0
    preserved: int = 0
    abstained: int = 0
    failed: int = 0
    truncated: int = 0
    not_run: int = 0
    abstention_reasons: dict[str, int] = field(default_factory=dict)
    status: Literal["CLEAN", "PARTIAL"] = "CLEAN"

    @property
    def completed(self) -> int:
        return self.attempted - self.failed - self.truncated

    @property
    def coverage(self) -> float:
        return self.completed / self.eligible if self.eligible else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            key: getattr(self, key) for key in COVERAGE_COUNTERS
        } | {
            "abstention_reasons": dict(self.abstention_reasons),
            "coverage": self.coverage,
            "status": self.status,
        }

    def __getitem__(self, key: str) -> Any:
        if key == "abstention_reasons":
            return self.abstention_reasons
        if key == "coverage":
            return self.coverage
        if key == "status":
            return self.status
        if key in COVERAGE_COUNTERS:
            return getattr(self, key)
        raise KeyError(key)


@dataclass
class Coverage:
    """Coverage broken down by document, pack, and rule."""

    documents: dict[str, CoverageBucket]
    packs: dict[str, CoverageBucket]
    rules: dict[str, CoverageBucket]
    status: Literal["CLEAN", "PARTIAL"]
    abstention_reasons: dict[str, int] = field(default_factory=dict)

    @property
    def by_document(self) -> dict[str, CoverageBucket]:
        return self.documents

    @property
    def by_pack(self) -> dict[str, CoverageBucket]:
        return self.packs

    @property
    def by_rule(self) -> dict[str, CoverageBucket]:
        return self.rules

    def as_dict(self) -> dict[str, Any]:
        return {
            "documents": {key: value.as_dict() for key, value in self.documents.items()},
            "packs": {key: value.as_dict() for key, value in self.packs.items()},
            "rules": {key: value.as_dict() for key, value in self.rules.items()},
            "abstention_reasons": dict(self.abstention_reasons),
            "status": self.status,
        }

    def __getitem__(self, key: str) -> Any:
        if key in {"documents", "packs", "rules", "status", "abstention_reasons"}:
            return getattr(self, key)
        raise KeyError(key)


def _canonical_table_bytes(pairs: Sequence[Sequence[str]]) -> bytes:
    return json.dumps(
        {"pairs": [list(pair) for pair in pairs]},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_dependence_table(path: str | Path) -> DependenceTable:
    """Load and verify a dependence table's content-addressed identity."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid dependence table {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("dependence table must be an object")
    digest = payload.get("dependence_table_sha")
    pairs = payload.get("pairs")
    status = payload.get("status", "uncalibrated")
    if not isinstance(digest, str) or not isinstance(pairs, list):
        raise ValueError("dependence table requires dependence_table_sha and pairs")
    if status not in {"calibrated", "uncalibrated"}:
        raise ValueError("dependence table status must be calibrated or uncalibrated")
    normalized: list[tuple[str, str]] = []
    for pair in pairs:
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or not all(isinstance(item, str) and item for item in pair)
        ):
            raise ValueError("dependence table pairs must contain two rule ids")
        normalized.append(tuple(sorted(pair)))
    expected = hashlib.sha256(_canonical_table_bytes(normalized)).hexdigest()
    if digest != expected:
        raise ValueError(
            f"dependence table sha mismatch: expected {expected}, got {digest}"
        )
    return DependenceTable(digest, tuple(normalized), status)


def _table_pairs(table: Any) -> set[tuple[str, str]]:
    if isinstance(table, (str, Path)):
        table = load_dependence_table(table)
    if isinstance(table, DependenceTable):
        return set(table.pairs)
    if isinstance(table, Mapping):
        table = table.get("pairs", ())
    pairs: set[tuple[str, str]] = set()
    for pair in table or ():
        if isinstance(pair, Sequence) and len(pair) == 2:
            pairs.add(tuple(sorted((str(pair[0]), str(pair[1])))))
    return pairs


def _table_status(table: Any) -> str:
    if isinstance(table, (str, Path)):
        table = load_dependence_table(table)
    if isinstance(table, DependenceTable):
        return table.status
    if isinstance(table, Mapping):
        status = table.get("status")
        if status is not None:
            return str(status)
        return "calibrated" if table.get("pairs") else "uncalibrated"
    return "calibrated" if table else "uncalibrated"


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _paragraphs(value: Any) -> list[_Paragraph]:
    if isinstance(value, Mapping):
        items = value.items()
    else:
        items = ((str(index), item) for index, item in enumerate(value or ()))
    result: list[_Paragraph] = []
    for key, item in items:
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            if len(item) >= 2 and all(isinstance(part, int) for part in item[:2]):
                result.append(_Paragraph(str(key), item[0], item[1]))
                continue
        start = _value(item, "doc_start", _value(item, "start"))
        end = _value(item, "doc_end", _value(item, "end"))
        doc_range = _value(item, "doc_range", _value(item, "range"))
        if doc_range is not None and len(doc_range) >= 2:
            start, end = doc_range[0], doc_range[1]
        result.append(_Paragraph(str(_value(item, "paragraph_id", key)), start, end))
    return result


def _defect_span(finding: FindingLike) -> tuple[int, int] | None:
    spans = []
    for evidence in _value(finding, "evidence", ()) or ():
        if _value(evidence, "role") != "defect":
            continue
        start = _value(evidence, "doc_start")
        end = _value(evidence, "doc_end")
        if isinstance(start, int) and isinstance(end, int) and end > start:
            spans.append((start, end))
    if not spans:
        return None
    return min(start for start, _ in spans), max(end for _, end in spans)


def _paragraph_for(finding: FindingLike, paragraphs: list[_Paragraph]) -> str:
    span = _defect_span(finding)
    if span is not None:
        for paragraph in paragraphs:
            if paragraph.start is None or paragraph.end is None:
                continue
            if span[0] < paragraph.end and paragraph.start < span[1]:
                return paragraph.key
    explicit = _value(finding, "paragraph_id")
    if explicit is not None:
        return str(explicit)
    return str(_value(finding, "path", "<unknown>"))


def _overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _harm(finding: FindingLike) -> Any:
    scores = _value(finding, "scores") or {}
    if not isinstance(scores, Mapping):
        return None
    for source in (scores, scores.get("dimensions", {}), scores.get("scores", {})):
        if isinstance(source, Mapping) and "harm" in source:
            harm = source["harm"]
            if isinstance(harm, Mapping):
                return harm.get("id", harm.get("value"))
            return harm
    return None


def _is_unsafe(finding: FindingLike) -> bool:
    if _value(finding, "outcome") != "CONFIRM":
        return False
    harm = _harm(finding)
    return harm in {"unsafe_or_normative", "unsafe", 3, "3"}


def _with_component_id(finding: FindingLike, component_id: str) -> FindingLike:
    """Return the host record with its immutable component assignment."""
    if isinstance(finding, Mapping):
        return {**finding, "component_id": component_id}  # type: ignore[return-value]
    return replace(finding, component_id=component_id)


def components(
    findings: Iterable[FindingLike], paragraphs: Any, table: Any
) -> list[Component]:
    """Build transitive overlap/dependence components for confirmed findings."""
    records = [finding for finding in findings if _value(finding, "outcome") == "CONFIRM"]
    paragraph_ranges = _paragraphs(paragraphs)
    by_paragraph: dict[str, list[tuple[FindingLike, tuple[int, int]]]] = defaultdict(list)
    for finding in records:
        span = _defect_span(finding)
        if span is not None:
            by_paragraph[_paragraph_for(finding, paragraph_ranges)].append((finding, span))
    status = _table_status(table)
    if status == "uncalibrated":
        LOGGER.info(
            "dependence table status=uncalibrated; cluster components use span overlap only"
        )
        pairs: set[tuple[str, str]] = set()
    else:
        pairs = _table_pairs(table)
    result: list[Component] = []
    component_number = 0
    for paragraph, entries in by_paragraph.items():
        parent = list(range(len(entries)))

        def root(index: int, parent: list[int] = parent) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int, parent: list[int] = parent) -> None:
            left_root, right_root = root(left), root(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left, (left_finding, left_span) in enumerate(entries):
            for right in range(left):
                right_finding, right_span = entries[right]
                related = _overlap(left_span, right_span)
                related |= tuple(
                    sorted((_value(left_finding, "rule_id"), _value(right_finding, "rule_id")))
                ) in pairs
                if related:
                    union(left, right)
        groups: dict[int, list[tuple[FindingLike, tuple[int, int]]]] = defaultdict(list)
        for index, entry in enumerate(entries):
            groups[root(index)].append(entry)
        for group in groups.values():
            component_number += 1
            component_id = f"component-{component_number}"
            severity_order = {"suggestion": 0, "warning": 1, "error": 2}
            severity = max(
                (_value(finding, "severity") for finding, _ in group),
                key=lambda value: severity_order.get(value, -1),
                default=None,
            )
            result.append(
                Component(
                    component_id=component_id,
                    findings=tuple(
                        _with_component_id(finding, component_id) for finding, _ in group
                    ),
                    paragraph=paragraph,
                    primary_spans=tuple(span for _, span in group),
                    severity=severity,
                )
            )
    return result


def _cfg_value(cfg: Any, name: str, default: Any) -> Any:
    settings = _value(cfg, "judgement", cfg)
    return _value(settings, name, default)


def cluster_gate(
    grouped: Iterable[Component], findings: Iterable[FindingLike], cfg: Any
) -> Literal["REVISE", None]:
    """Return the distinct cluster gate result without changing the score."""
    if any(_is_unsafe(finding) for finding in findings):
        return "REVISE"
    by_paragraph: dict[str, list[Component]] = defaultdict(list)
    for component in grouped:
        if component.primary_span is not None:
            by_paragraph[component.paragraph].append(component)
    minimum = int(_cfg_value(cfg, "cluster_min_components", 0))
    for entries in by_paragraph.values():
        if len(entries) < minimum:
            continue
        if all(
            not any(
                _overlap(left_span, right_span)
                for left_span in left.primary_spans
                for right_span in right.primary_spans
            )
            for index, left in enumerate(entries)
            for right in entries[index + 1 :]
        ):
            return "REVISE"
    return None


def _unit_key(item: Any) -> str:
    return str(_value(item, "unit_id", _value(item, "id", "")))


def _dimensions(item: Any) -> tuple[str, str, str]:
    return (
        str(_value(item, "path", _value(item, "document", "<unknown>"))),
        str(_value(item, "pack_id", _value(item, "pack", "<unknown>"))),
        str(_value(item, "rule_id", "<unknown>")),
    )


_COVERAGE_OUTCOME_RANK = {
    "confirm": 4,
    "confirmed": 4,
    "reject": 3,
    "rejected": 3,
    "preserve": 2,
    "preserved": 2,
    "abstain": 1,
    "abstained": 1,
    "failed": 0,
    "failure": 0,
    "error": 0,
    "not_run": -1,
    "not-run": -1,
    "missing": -1,
    "": -1,
}


def _coverage_status(record: Any) -> str:
    return str(_value(record, "status", _value(record, "outcome", ""))).lower()


def _group_coverage_records(findings: Iterable[FindingLike]) -> dict[str, list[FindingLike]]:
    grouped: dict[str, list[FindingLike]] = defaultdict(list)
    for finding in findings:
        unit_id = _unit_key(finding)
        if unit_id:
            grouped[unit_id].append(finding)
    return grouped


def _representative_coverage_record(records: list[FindingLike]) -> FindingLike:
    return max(records, key=lambda record: _COVERAGE_OUTCOME_RANK.get(_coverage_status(record), 0))


def coverage(findings: Iterable[FindingLike], eligible_units: Iterable[Any]) -> Coverage:
    """Count judgement coverage at document, pack, and rule granularity."""
    eligible_by_id: dict[str, Any] = {}
    for unit in eligible_units:
        unit_id = _unit_key(unit)
        if unit_id not in eligible_by_id:
            eligible_by_id[unit_id] = unit
    eligible = list(eligible_by_id.values())
    records = _group_coverage_records(findings)
    buckets: dict[str, dict[str, CoverageBucket]] = {
        "documents": {},
        "packs": {},
        "rules": {},
    }
    reasons: dict[str, int] = {}
    partial = False

    def bucket(kind: str, key: str) -> CoverageBucket:
        return buckets[kind].setdefault(key, CoverageBucket())

    for unit in eligible:
        unit_id = _unit_key(unit)
        path, pack, rule = _dimensions(unit)
        target = [bucket("documents", path), bucket("packs", pack), bucket("rules", rule)]
        for current in target:
            current.eligible += 1
        record_group = records.get(unit_id, [])
        finding = _representative_coverage_record(record_group) if record_group else None
        status = str(_value(unit, "status", "" if finding else "not_run")).lower()
        truncated = bool(_value(unit, "truncated", False))
        truncated |= any(
            bool(_value(record, "occurrences_truncated", False))
            for record in record_group
        )
        if finding is not None:
            status = _coverage_status(finding)
        if status in {"not_run", "not-run", "missing", ""}:
            for current in target:
                current.not_run += 1
            partial = True
            continue
        if status in {"failed", "failure", "error"}:
            for current in target:
                current.failed += 1
            partial = True
        else:
            for current in target:
                current.attempted += 1
            counter = {
                "confirm": "confirmed",
                "confirmed": "confirmed",
                "reject": "rejected",
                "rejected": "rejected",
                "preserve": "preserved",
                "preserved": "preserved",
                "abstain": "abstained",
                "abstained": "abstained",
            }.get(status)
            if counter is not None:
                for current in target:
                    setattr(current, counter, getattr(current, counter) + 1)
            if status in {"abstain", "abstained"}:
                reason = _value(finding, "abstain_reason", None) or "unknown"
                reasons[str(reason)] = reasons.get(str(reason), 0) + 1
                for current in target:
                    current.abstention_reasons[str(reason)] = (
                        current.abstention_reasons.get(str(reason), 0) + 1
                    )
        if truncated:
            for current in target:
                current.truncated += 1
                current.not_run += 1
            partial = True

    for group in buckets.values():
        for current in group.values():
            current.status = "PARTIAL" if current.failed or current.truncated or current.not_run else "CLEAN"
    return Coverage(
        documents=buckets["documents"],
        packs=buckets["packs"],
        rules=buckets["rules"],
        status="PARTIAL" if partial else "CLEAN",
        abstention_reasons=reasons,
    )


def _weight_for(finding: FindingLike, weights: Any) -> float:
    rule_id = str(_value(finding, "rule_id", ""))
    category = rule_id.rsplit(".", 1)[0]
    if isinstance(weights, Mapping):
        for key in (rule_id, category, "default"):
            if key in weights and isinstance(weights[key], (int, float)):
                return float(weights[key])
        categories = weights.get("categories")
        if isinstance(categories, Mapping) and category in categories:
            return float(categories[category])
    for key in (rule_id, category):
        value = _value(weights, key, None)
        if isinstance(value, (int, float)):
            return float(value)
    return 1.0


def _severity_weight(finding: FindingLike) -> float:
    from ..config import Severity
    from ..score import SEVERITY_WEIGHT

    severity = _value(finding, "severity")
    try:
        return float(SEVERITY_WEIGHT[Severity(severity)])
    except (KeyError, TypeError, ValueError):
        return 0.0


def judgement_penalty(
    findings: Iterable[FindingLike], weights: Any, max_penalty: float | None = None
) -> float:
    """Return the bounded reporting deduction for confirmed judgement findings."""
    records = [finding for finding in findings if _value(finding, "outcome") == "CONFIRM"]
    uncapped = sum(_severity_weight(finding) * _weight_for(finding, weights) for finding in records)
    if max_penalty is None:
        max_penalty = _value(weights, "max_penalty", None)
        if max_penalty is None and isinstance(weights, Mapping):
            max_penalty = weights.get("max_penalty")
    if max_penalty is None:
        from ..config import JudgementSettings

        max_penalty = JudgementSettings().max_penalty
    return min(float(max_penalty), max(0.0, uncapped))


def judgement_penalty_uncapped(findings: Iterable[FindingLike], weights: Any) -> float:
    """Return the uncapped deduction used alongside the bounded report value."""
    return sum(
        _severity_weight(finding) * _weight_for(finding, weights)
        for finding in findings
        if _value(finding, "outcome") == "CONFIRM"
    )


def preserve_rates(findings: Iterable[FindingLike]) -> dict[str, dict[str, Any]]:
    """Report exposure-normalised preserve rates by rule and reason."""
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"attempted": 0, "preserved": 0, "reasons": {}}
    )
    for finding in findings:
        outcome = str(_value(finding, "outcome", "")).lower()
        if outcome in {"drop", "not_run", "failed", ""}:
            continue
        rule = str(_value(finding, "rule_id", "<unknown>"))
        entry = grouped[rule]
        entry["attempted"] += 1
        if outcome == "preserve":
            entry["preserved"] += 1
            reason = str(_value(finding, "preservation_reason", None) or "unknown")
            entry["reasons"][reason] = entry["reasons"].get(reason, 0) + 1
    for entry in grouped.values():
        entry["rate"] = entry["preserved"] / entry["attempted"] if entry["attempted"] else 0.0
    return dict(grouped)


__all__ = [
    "COVERAGE_COUNTERS",
    "Component",
    "Coverage",
    "CoverageBucket",
    "DependenceTable",
    "FindingLike",
    "cluster_gate",
    "components",
    "coverage",
    "judgement_penalty",
    "judgement_penalty_uncapped",
    "load_dependence_table",
    "preserve_rates",
]
