import json
from pathlib import Path

from slopvac.judgement.eval import judgement_cache_key, validate_result_set
from slopvac.judgement.eval.__main__ import main


def test_validate_result_set_checks_occurrence_shapes() -> None:
    units = [
        {"unit_id": "probe", "kind": "PASSAGE_PROBE"},
        {"unit_id": "span", "kind": "SPAN"},
    ]
    assert validate_result_set(units, [{"unit_id": "probe", "occurrences": []}, {"unit_id": "span", "occurrences": None}]) is None
    assert validate_result_set(units, [{"unit_id": "probe", "occurrences": None}, {"unit_id": "span", "occurrences": None}]) == "probe result row occurrences is not a list"
    assert validate_result_set(units, [{"unit_id": "probe", "occurrences": []}, {"unit_id": "span", "occurrences": []}]) == "span result row occurrences is not null"


def test_cache_key_keeps_context_as_a_distinct_contract_field() -> None:
    kwargs = dict(
        instrument_id="instrument",
        unit_id="unit",
        provider="provider",
        model_id_and_revision="model",
        full_rendered_request_digest="request",
        system_prompt="system",
        decoding_config={"temperature": 0},
        seed=1,
        repeat_index=0,
        evaluator_runner_revision="revision",
    )
    first = judgement_cache_key(context_hash="a", **kwargs)
    second = judgement_cache_key(context_hash="b", **kwargs)
    assert first != second


def test_run_flattens_replay_payload(tmp_path: Path, capsys) -> None:
    replay = tmp_path / "replay.jsonl"
    replay.write_text(json.dumps({"response": {"results": [{"unit_id": "u1"}]}}) + "\n")
    assert main(["run", "--replay", str(replay)]) == 0
    assert json.loads(capsys.readouterr().out) == {"results": [{"unit_id": "u1"}]}


def test_report_decodes_records_and_prints_coverage(tmp_path: Path, capsys) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"records": [{
        "instrument_id": "instrument",
        "unit_id": "u1",
        "repeat_index": 0,
        "judgement_cache_key": "cache",
        "model_output": {"verdict": "accept"},
        "status": "confirmed",
        "frozen_fields": {"pack_id": "pack"},
    }]}))
    assert main(["report", str(report)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["coverage"]["confirmed"] == 1
    assert output["coverage"]["attempted"] == 1


def test_aggregate_counts_finding_backed_outcomes() -> None:
    from slopvac.judgement.adjudicate import FindingRecord
    from slopvac.judgement.eval.runner import EvalRecord, aggregate

    def finding(outcome: str, *, reason: str | None = None) -> FindingRecord:
        return FindingRecord(
            unit_id=f"u-{outcome}", rule_id="ai-tells-structure.heading-echo", kind="SPAN_CANDIDATE",
            outcome=outcome, severity="suggestion" if outcome == "CONFIRM" else None, scores=None,
            evidence=(), preservation_reason=None, abstain_reason=reason, rewrite=None,
            rewrite_status="not_applicable", core_fired=False, component_id=None,
            source_sha256="s", path="doc.md", instrument_id="i", judgement_cache_key="k",
            occurrence_index=None,
        )

    frozen = {"pack_id": "p"}
    rows = [EvalRecord(finding=finding(o), frozen_fields=frozen) for o in ("CONFIRM", "REJECT", "PRESERVE", "DROP")]
    rows.append(EvalRecord(finding=finding("ABSTAIN", reason="no_exact_evidence"), frozen_fields=frozen))
    report = aggregate(rows)
    coverage = report["coverage"]
    assert (coverage["confirmed"], coverage["rejected"], coverage["preserved"]) == (1, 1, 1)
    assert (coverage["abstained"], coverage["not_run"], coverage["attempted"]) == (1, 1, 4)
    assert report["abstentions"] == {"no_exact_evidence": 1}
