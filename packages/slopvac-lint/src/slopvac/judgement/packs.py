"""Build, hash, and render judgement-layer prompt packs."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any

_PROBE_PACKS = (
    (1, ("ai-tells-structure",), ("ai-tells-structure.invented-concept-label", "ai-tells-structure.listicle-in-a-trench-coat", "ai-tells-structure.summary-closer-remainder", "ai-tells-structure.tricolon-abuse-remainder"), ("accessibility_consistency", "factual_polarity_or_contrast", "normative_obligation", "quoted_specimen")),
    (2, ("ai-tells-content-shape",), ("ai-tells-content-shape.fabricated-citations-remainder", "ai-tells-content-shape.one-point-dilution", "ai-tells-content-shape.padded-symmetry", "ai-tells-content-shape.vaporware-description"), ("normative_obligation", "quoted_specimen")),
    (3, ("ai-tells-content-shape", "prose-discipline"), ("ai-tells-content-shape.elegant-variation", "prose-discipline.bare-quantifier-with-figure-available", "prose-discipline.competing-actor-terms", "prose-discipline.hedged-into-uselessness"), ("authoritative_domain_term", "normative_obligation", "quoted_specimen")),
    (4, ("ai-tells-formatting", "ai-tells-register", "ai-tells-structure", "ste-nouns"), ("ai-tells-formatting.table-wrapping-one-sentence", "ai-tells-register.over-formatting-reflex", "ai-tells-structure.audience-straddle-remainder", "ste-nouns.long-domain-term-without-short-form"), ("accessibility_consistency", "authoritative_domain_term", "controlled_language_clarity", "factual_polarity_or_contrast", "normative_obligation", "quoted_specimen", "source_locked_legal_text")),
    (5, ("orwell", "prose-scope", "ste-words"), ("orwell.concrete-floor", "prose-scope.code-change-prose-scope", "ste-words.domain-noun-not-organization-approved"), ("authoritative_domain_term", "controlled_language_clarity", "normative_obligation")),
)


@dataclass(frozen=True)
class Pack:
    id: str
    categories: tuple[str, ...]
    chunk: int
    scope_class: str
    protects: tuple[str, ...]
    rules: tuple[str, ...]
    rule_records: tuple[Mapping[str, Any], ...] = ()
    units_max: int = 5
    template_revision: str = "2"
    shots: tuple[Mapping[str, str], ...] = ()


_SHOTS = ({"label": "worked-example-1", "message": "<<<SHOT worked-example-1>>>\nEvidence: quote the exact unit text.\nScores: provide fit, harm, repair, and warrant level ids.\nVerdict: choose one documented outcome.\n<<<END SHOT>>>"},)


def _value(rule: Any, name: str, default: Any = None) -> Any:
    if isinstance(rule, Mapping):
        return rule.get(name, default)
    return getattr(rule, name, default)


def _rule_id(rule: Any) -> str:
    return str(_value(rule, "qualified_id", _value(rule, "id")))


def _judgement_value(rule: Any, name: str, default: Any = None) -> Any:
    contract = _value(rule, "judgement")
    if contract is None:
        return default
    return _value(contract, name, default)


def build_packs(rules: Sequence[Any]) -> list[Pack]:
    """Partition loaded judgement rules into local and contract probe packs."""
    by_id = {_rule_id(rule): rule for rule in rules}
    local: dict[str, list[str]] = {}
    for rid, rule in by_id.items():
        if _judgement_value(rule, "scope_class") == "local":
            category = rid.rsplit(".", 1)[0]
            local.setdefault(category, []).append(rid)
    result: list[Pack] = []
    for category in sorted(local):
        ids = sorted(local[category])
        for index in range(0, len(ids), 4):
            chunk = index // 4 + 1
            selected = tuple(ids[index : index + 4])
            records = tuple(_merged_record(rid, by_id[rid]) for rid in selected)
            protects = tuple(sorted({p for record in records for p in record.get("protects", ())}))
            result.append(Pack(f"SPAN-{category}-{chunk}", (category,), chunk, "local", protects, selected, records, shots=_SHOTS))
    for chunk, categories, ids, protects in _PROBE_PACKS:
        records = tuple(_merged_record(rid, by_id[rid]) for rid in ids if rid in by_id)
        selected = tuple(record["id"] for record in records)
        result.append(Pack(f"PROBE-{chunk}", categories, chunk, "probe", protects, selected, records, shots=_SHOTS))
    return result


def _plain(value: Any) -> Any:
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return value.value
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump())
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


_RECORD_FIELDS = ("category", "dims", "evidence", "examples", "id", "judgement_ceiling", "judgement_question", "protects", "scope_class", "warrant_min")
_OPTIONAL_RECORD_FIELDS = ("adjudicates", "allowed_transitions", "host_predicates", "scope_class_derivation", "added_in", "status")


def _plain_examples(value: Any) -> list[dict[str, Any]]:
    """Keep only the model-visible example contract fields."""
    examples: list[dict[str, Any]] = []
    for item in _plain(value) or ():
        if not isinstance(item, Mapping):
            continue
        example = {key: item[key] for key in ("bad", "good", "note") if item.get(key) is not None}
        if example:
            examples.append(example)
    return examples


def _merged_record(rid: str, rule: Any) -> dict[str, Any]:
    """Render the contract record without dataclass defaults or dropped fields.

    Questions and examples are model-visible, so pack_object includes them and a
    change to either changes the pack and instrument ids.
    """
    contract = _value(rule, "judgement", {})
    plain = _plain(contract)
    if not isinstance(plain, Mapping):
        plain = {}
    result: dict[str, Any] = {}
    category = _value(rule, "category", rid.rsplit(".", 1)[0])
    result["category"] = _plain(category)
    for key in _RECORD_FIELDS[1:]:
        if key == "id":
            value = rid
        elif key == "examples":
            raw = _value(rule, key)
            if raw is None:
                raw = plain.get(key)
            value = _plain_examples(raw)
        elif key == "judgement_question":
            value = _value(rule, key)
            if value is None:
                value = plain.get(key)
        else:
            value = plain.get(key, _value(rule, key))
        if value not in (None, (), [], {}):
            result[key] = _plain(value)
    for key in _OPTIONAL_RECORD_FIELDS:
        value = plain.get(key, _value(rule, key))
        if value not in (None, (), [], {}):
            result[key] = _plain(value)
    return result



def pack_object(pack: Pack) -> dict[str, Any]:
    return {
        "categories": list(pack.categories),
        "chunk": pack.chunk,
        "scope_class": pack.scope_class,
        "protects": list(pack.protects),
        "rules": [{key: value for key, value in dict(record).items() if key != "name"} for record in pack.rule_records] if pack.rule_records else list(pack.rules),
        "template_revision": pack.template_revision,
        "shots": [dict(shot) for shot in pack.shots],
    }


def _number(value: int | float) -> str:
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer() and abs(value) < 1e21):
        return str(int(value))
    if not math.isfinite(value):
        raise ValueError("JCS cannot encode non-finite numbers")
    text = repr(value).lower()
    if "e" not in text:
        return text
    mantissa, exponent = text.split("e")
    exponent_int = int(exponent)
    if 1e-6 <= abs(value) < 1e21:
        from decimal import Decimal
        return format(Decimal(text), "f").rstrip("0").rstrip(".")
    mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}e{'+' if exponent_int >= 0 else ''}{exponent_int}"


def _utf16_key(value: str) -> bytes:
    return value.encode("utf-16-be", "surrogatepass")


def canonical_bytes(obj: Any) -> bytes:
    """Return RFC 8785-style canonical JSON for values emitted by this package."""
    def encode(value: Any) -> str:
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _number(value)
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if isinstance(value, Mapping):
            return "{" + ",".join(encode(str(k)) + ":" + encode(v) for k, v in sorted(value.items(), key=lambda item: _utf16_key(str(item[0])))) + "}"
        if isinstance(value, (list, tuple)):
            return "[" + ",".join(encode(v) for v in value) + "]"
        raise TypeError(f"unsupported JCS value: {type(value).__name__}")
    return encode(obj).encode("utf-8")


def pack_id(pack: Pack) -> str:
    return hashlib.sha256(canonical_bytes(pack_object(pack))).hexdigest()


def rubric_revision(spine_text: str) -> str:
    return hashlib.sha256(spine_text.encode("utf-8")).hexdigest()


def instrument_id(rubric_revision: str, pack_ids: Sequence[str]) -> str:
    return hashlib.sha256(canonical_bytes([rubric_revision, list(pack_ids)])).hexdigest()


def judgement_cache_key(
    *,
    instrument_id: str,
    unit_id: str,
    context_hash: str,
    provider: str,
    model_id_and_revision: str,
    full_rendered_request_digest: str,
    system_prompt: str,
    decoding_config: Any,
    seed: int | None,
    repeat_index: int,
    evaluator_runner_revision: str,
) -> str:
    values = locals()
    fields = ("instrument_id", "unit_id", "context_hash", "provider", "model_id_and_revision", "full_rendered_request_digest", "system_prompt", "decoding_config", "seed", "repeat_index", "evaluator_runner_revision")
    return hashlib.sha256(canonical_bytes({field: values[field] for field in fields})).hexdigest()


def render_pack(pack: Pack, spine: str) -> str:
    """Render only model-visible rubric instructions and criteria."""
    records = pack.rule_records or tuple({"id": rid} for rid in pack.rules)
    criteria: list[str] = []
    for record in records:
        question = record.get("judgement_question", "")
        if question:
            evidence = record.get("evidence", {})
            roles = ", ".join(evidence.get("roles", ()))
            arity = evidence.get("min_arity", 1)
            criteria.append(f"- {record['id']}: {question} (evidence roles: {roles}; minimum quotes: {arity})")
            for example in record.get("examples", ()):
                if not isinstance(example, Mapping):
                    continue
                bad = str(example.get("bad", "")).strip()
                if not bad:
                    continue
                good = example.get("good")
                note = str(example.get("note", "")).strip()
                if good:
                    criteria.append(f"  exemplar: {bad} -> {str(good).strip()}")
                elif note:
                    criteria.append(f"  exemplar: {bad} [{note}]")
                else:
                    criteria.append(f"  exemplar: {bad}")
    forbidden = re.compile(r"\b(?:error|warning|suggestion|threshold|weight|severity)\b", re.I)
    newline = chr(10)
    text = forbidden.sub("", spine.rstrip()) + newline * 2 + "PACK " + pack.id + newline + newline.join(criteria)
    text += newline * 2 + "Protected classes: " + ", ".join(pack.protects)
    text += newline + "Output: return the documented judgement output schema; emit evidence before dimension values and verdict."
    for shot in pack.shots:
        text += newline * 2 + shot["message"]
    return text
