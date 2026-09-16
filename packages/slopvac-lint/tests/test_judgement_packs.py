from slopvac.judgement.packs import (
    Pack,
    build_packs,
    canonical_bytes,
    judgement_cache_key,
    pack_id,
    render_pack,
    rubric_revision,
)
from slopvac.judgement.types import EvidenceSpec, JudgementContract


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
