from slopvac.judgement.eval.runner import validate_result_set


def test_probe_row_requires_nested_occurrences_list() -> None:
    units = [{"unit_id": "probe", "kind": "PASSAGE_PROBE"}]
    assert validate_result_set(units, [{"unit_id": "probe", "occurrences": []}]) is None
    assert validate_result_set(units, [{"unit_id": "probe", "occurrences": None}]) == "probe result row occurrences is not a list"


def test_span_row_requires_null_occurrences() -> None:
    units = [{"unit_id": "span", "kind": "SPAN_CANDIDATE"}]
    assert validate_result_set(units, [{"unit_id": "span", "occurrences": None}]) is None
    assert validate_result_set(units, [{"unit_id": "span", "occurrences": []}]) == "span result row occurrences is not null"
