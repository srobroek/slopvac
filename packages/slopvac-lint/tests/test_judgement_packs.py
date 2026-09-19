from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from slopvac.judgement.packs import (
    Pack,
    build_packs,
    canonical_bytes,
    instrument_id,
    judgement_cache_key,
    pack_id,
    render_pack,
    rubric_revision,
)
from slopvac.judgement.types import EvidenceSpec, JudgementContract
from slopvac.rules import load_ruleset


def _contract(scope: str = "local") -> JudgementContract:
    return JudgementContract(
        dims={"fit": "ask", "harm": "ask", "repair": "ask", "warrant": "ask"},
        protects=("quoted_specimen",),
        evidence=EvidenceSpec(1, ("defect",)),
        warrant_min=2,
        judgement_ceiling="suggestion",
        scope_class=scope,
    )


def test_local_rules_are_sorted_and_chunked() -> None:
    ids = [f"cat.rule-{n}" for n in range(5)]

    class Rule:
        def __init__(self, qualified_id: str) -> None:
            self.qualified_id = qualified_id
            self.judgement = _contract()

    packs = build_packs([Rule(rid) for rid in reversed(ids)])
    local = [pack for pack in packs if pack.scope_class == "local"]
    assert [pack.rules for pack in local] == [tuple(sorted(ids)[:4]), (ids[-1],)]
    assert all(len(pack.rules) <= 4 for pack in local)


def test_jcs_vectors() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert canonical_bytes({"text": "Zürich"}) == b'{"text":"Z\xc3\xbcrich"}'
    assert canonical_bytes({"n": 1.0, "small": 1e-7}) == b'{"n":1,"small":1e-7}'


def test_pack_hash_excludes_unlisted_rule_fields() -> None:
    one = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({"id": "cat.rule", "judgement_question": "A?", "name": "One"},))
    two = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({"id": "cat.rule", "judgement_question": "A?", "name": "Two"},))
    changed = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({"id": "cat.rule", "judgement_question": "B?"},))
    assert pack_id(one) == pack_id(two)
    assert pack_id(one) != pack_id(changed)

def test_span_pack_id_matches_contract_record_bytes() -> None:
    root = Path(__file__).parents[1]
    contract = json.loads((root / "docs/research/rubric-2026-09-15/rubric-contract.json").read_text())
    ruleset = load_ruleset(verify=False)
    generated = next(pack for pack in build_packs(ruleset.judgement_rules()) if pack.id == "SPAN-ai-tells-structure-1")
    expected_ids = next(pack["rules"] for pack in contract["composition"]["span_packs"] if pack["id"] == generated.id)
    records = tuple(record for rule_id in expected_ids for record in contract["rule_records"] if record["id"] == rule_id)
    expected = Pack(generated.id, generated.categories, generated.chunk, generated.scope_class, generated.protects, tuple(expected_ids), records, shots=generated.shots)
    assert pack_id(generated) == pack_id(expected)


def test_cache_key_changes_for_each_field() -> None:
    values = dict(
        instrument_id="i", unit_id="u", context_hash="c", provider="p",
        model_id_and_revision="m", full_rendered_request_digest="r", system_prompt="s",
        decoding_config={"temperature": 0}, seed=1, repeat_index=0,
        evaluator_runner_revision="e",
    )
    base = judgement_cache_key(**values)
    for key in values:
        changed = dict(values)
        changed[key] = "changed" if isinstance(changed[key], str) else 9
        assert judgement_cache_key(**changed) != base


def test_rendering_hides_policy_vocabulary() -> None:
    pack = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({"id": "cat.rule", "judgement_question": "Is the shape present?"},))
    rendered = render_pack(pack, "Judge the unit.")
    assert all(word not in rendered.lower() for word in ("severity", "threshold", "weight", "warning", "error"))
    assert rubric_revision("spine") != rubric_revision("spine ")


def test_rendering_includes_paired_exemplars() -> None:
    pack = Pack(
        "SPAN-cat-1",
        ("cat",),
        1,
        "local",
        (),
        ("cat.rule",),
        (
            {
                "id": "cat.rule",
                "judgement_question": "Is the shape present?",
                "examples": [{"bad": "The claim repeats.", "good": "The claim advances."}],
            },
        ),
    )
    rendered = render_pack(pack, "Judge the unit.")
    assert "exemplar: The claim repeats. -> The claim advances." in rendered

def test_shipped_absolute_assertion_pack_has_criteria() -> None:
    ruleset = load_ruleset(verify=False)
    rules = ruleset.judgement_rules()
    packs = build_packs(rules)
    pack = next(pack for pack in packs if any("absolute-assertion" in rule_id for rule_id in pack.rules))
    rendered = render_pack(pack, "Judge the unit.")
    assert any(line.startswith("- ") for line in rendered.splitlines())
    assert any("absolute-assertion" in line for line in rendered.splitlines())


def test_every_shipped_judgement_question_and_example_is_rendered() -> None:
    ruleset = load_ruleset(verify=False)
    rules = {rule.qualified_id: rule for rule in ruleset.judgement_rules()}
    packs = build_packs(tuple(rules.values()))
    for pack in packs:
        rendered = render_pack(pack, "Judge the unit.")
        for record in pack.rule_records:
            rule = rules[record["id"]]
            assert rule.judgement_question in rendered
            for example in rule.examples:
                bad = str(example.bad).strip()
                assert bad in rendered
                if example.good:
                    assert str(example.good).strip() in rendered
                elif example.note:
                    assert str(example.note).strip() in rendered


def test_criteria_words_are_not_removed_by_forbidden_filter() -> None:
    pack = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({
        "id": "cat.rule",
        "judgement_question": "Does the warning threshold carry severity weight?",
    },))
    rendered = render_pack(pack, "Judge the unit.")
    assert "warning threshold carry severity weight" in rendered


def test_contract_builder_rejects_missing_judgement_question(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = Path(__file__).parents[1] / "docs/research/rubric-2026-09-15/measurements/build_contract.py"
    text = source.read_text(encoding="utf-8")
    helper = text[text.index("def _enrich_rule_records"):text.index("def rule_records")]
    namespace: dict[str, object] = {}
    exec(helper, namespace)
    with pytest.raises(AssertionError, match="missing judgement questions"):
        namespace["_enrich_rule_records"]([{"id": "cat.rule"}], {"cat.rule": SimpleNamespace(judgement_question=None, examples=[])})


def test_question_changes_pack_and_instrument_hash() -> None:
    one = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({"id": "cat.rule", "judgement_question": "A?"},))
    two = Pack("SPAN-cat-1", ("cat",), 1, "local", (), ("cat.rule",), ({"id": "cat.rule", "judgement_question": "B?"},))
    revision = rubric_revision("spine")
    assert pack_id(one) != pack_id(two)
    assert instrument_id(revision, [pack_id(one)]) != instrument_id(revision, [pack_id(two)])