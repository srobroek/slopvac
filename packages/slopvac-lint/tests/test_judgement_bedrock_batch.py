import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

SPEC = importlib.util.spec_from_file_location("runner", Path(__file__).parents[1] / "scripts/judgement_bedrock_batch.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def row(cid="a"):
    return {"call_id": cid, "prompt": {"system": "sys", "user": "user"}, "response_schema": {"type": "object"}}


def test_todo_matches_template_semantics(tmp_path):
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text("\n".join(json.dumps(row(x)) for x in ("ok", "bad", "missing")) + "\n")
    responses = tmp_path / "responses.jsonl"
    responses.write_text(json.dumps({"call_id": "ok", "response": {}}) + "\n" + json.dumps({"call_id": "bad", "error": "x"}) + "\n" + json.dumps({"error": "missing call id"}) + "\n")
    out = tmp_path / "todo.jsonl"
    runner.todo(SimpleNamespace(prompts=str(prompts), responses=[str(responses)], out=str(out)))
    assert [x["call_id"] for x in runner.read_jsonl(out)] == ["bad", "missing"]


def test_make_prompt_is_template_byte_identical():
    assert runner.make_prompt(row()) == 'user\n\nRespond with ONLY one JSON object (no prose, no code fence) that validates against this JSON Schema:\n{"type": "object"}'


def test_parse_json_fenced_unfenced_and_garbage():
    assert runner.parse_json('```json\n{"x": 1}\n```') == {"x": 1}
    assert runner.parse_json('prefix prose {"x": 1} trailing') == {"x": 1}


def test_collect_maps_records(monkeypatch, tmp_path):
    class Body:
        def read(self):
            return b'{"recordId":"a","modelOutput":{"stopReason":"end_turn","output":{"message":{"content":[{"text":"{\\"ok\\":true}"}]}}}}\n'
    class S3:
        def list_objects_v2(self, **kwargs): return {"Contents": [{"Key": "job/output/part.jsonl.out"}]}
        def get_object(self, **kwargs): return {"Body": Body()}
    class Bedrock:
        def get_model_invocation_job(self, **kwargs): return {"status": "Completed"}
    monkeypatch.setattr(runner, "load_boto3", lambda: SimpleNamespace(client=lambda name: Bedrock() if name == "bedrock" else S3()))
    d = tmp_path / "job"; d.mkdir()
    (d / "job.json").write_text(json.dumps({"job_arn": "arn", "bucket": "b", "output_prefix": "job/output/"}))
    out = tmp_path / "responses.jsonl"
    runner.collect(SimpleNamespace(job_dir=str(d), out=str(out), todo=None, poll_seconds=0))
    assert json.loads(out.read_text())["call_id"] == "a"
    assert json.loads(out.read_text())["response"] == {"ok": True}


def test_invoke_preserves_raw_and_stop_reason_on_parse_error(monkeypatch, tmp_path):
    class Client:
        def converse(self, **kwargs):
            return {"stopReason": "max_tokens", "output": {"message": {"content": [{"text": '{"broken":'}]}}}
    monkeypatch.setattr(runner, "load_boto3", lambda: SimpleNamespace(client=lambda *a, **k: Client()))
    todo = tmp_path / "todo.jsonl"; todo.write_text(json.dumps(row()) + "\n")
    out = tmp_path / "out.jsonl"
    runner.invoke(SimpleNamespace(todo=str(todo), out=str(out), model_id="m", max_tokens=8192, temperature=None, concurrency=1))
    result = json.loads(out.read_text())
    assert result["error"] == "stop_reason=max_tokens"
    assert result["raw"] == '{"broken":'
    assert result["stop_reason"] == "max_tokens"
